from __future__ import annotations

import asyncio
import json

import pytest

from backend.zhifei_autoplan.provider_admission import (
    SCHEMA_VERSION,
    ProbeOutcome,
    ProviderAdmissionManager,
    ProviderCandidate,
    canonical_digest,
    decide_required_roles,
    evaluate_latest_snapshot,
    load_latest_snapshot,
    public_snapshot,
)


def _candidate(**overrides):
    value = {
        "slot": "text_main",
        "role": "text_draft",
        "provider": "openai",
        "model": "gpt-test",
        "key_alias": "OPENAI_API_KEY",
        "credential": "ephemeral-test-credential",
    }
    value.update(overrides)
    return value


@pytest.mark.asyncio
async def test_success_snapshot_is_redacted_persisted_and_digest_bound(tmp_path) -> None:
    secret = "sk-proj-never-persist-this-value"
    seen: list[ProviderCandidate] = []

    async def probe(candidate: ProviderCandidate):
        seen.append(candidate)
        assert candidate.credential == secret
        return {
            "ok": True,
            "code": "probe_passed",
            # Untrusted diagnostic fields are not part of the allowlist.
            "raw_error": f"Bearer {secret}",
            "prompt": "do not persist this probe prompt",
        }

    manager = ProviderAdmissionManager(root=tmp_path, ttl_seconds=60, clock=lambda: 100.0)
    snapshot = await manager.admit_chain(
        candidates=[_candidate(credential=secret, prompt="caller prompt")],
        probe=probe,
        required_roles=["text_draft"],
    )

    assert len(seen) == 1
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert snapshot["generation_allowed"] is True
    assert snapshot["degraded"] is False
    assert len(snapshot["admitted_chain"]) == 1
    assert snapshot["slots"][0]["admitted"] is True
    assert snapshot["slots"][0]["layers"]["quota"]["status"] == "pass"

    serialized = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    assert secret not in serialized
    assert "OPENAI_API_KEY" not in serialized
    assert "do not persist this probe prompt" not in serialized
    assert "raw_error" not in serialized
    assert "prompt" not in serialized

    digest = snapshot["admission_digest"]
    material = dict(snapshot)
    material.pop("admission_digest")
    assert digest == canonical_digest(material)
    assert load_latest_snapshot(tmp_path, strict=True) == snapshot

    public = public_snapshot(snapshot)
    public_json = json.dumps(public, ensure_ascii=False, sort_keys=True)
    assert "credential_fingerprint" not in public_json
    assert "identity_digest" not in public_json
    assert "cache_hit" not in public_json
    assert public["generation_allowed"] is True

    current = evaluate_latest_snapshot(
        [_candidate(credential=secret)],
        ["text_draft"],
        root=tmp_path,
        now=120.0,
    )
    assert current["status"] == "admitted"
    assert current["generation_allowed"] is True


@pytest.mark.asyncio
async def test_offline_latest_evaluation_rejects_expired_or_changed_identity(tmp_path) -> None:
    manager = ProviderAdmissionManager(root=tmp_path, ttl_seconds=10, clock=lambda: 50.0)
    await manager.admit_chain(
        candidates=[_candidate(credential="original-credential")],
        probe=lambda _candidate: ProbeOutcome.success(),
        required_roles=["text_draft"],
    )

    expired = evaluate_latest_snapshot(
        [_candidate(credential="original-credential")],
        ["text_draft"],
        root=tmp_path,
        now=60.0,
    )
    changed = evaluate_latest_snapshot(
        [_candidate(credential="replacement-credential")],
        ["text_draft"],
        root=tmp_path,
        now=55.0,
    )

    assert expired["status"] == "expired"
    assert expired["generation_allowed"] is False
    assert changed["status"] == "stale_route"
    assert changed["generation_allowed"] is False
    assert "original-credential" not in json.dumps(expired)
    assert "replacement-credential" not in json.dumps(changed)


@pytest.mark.asyncio
async def test_quota_exhausted_fails_quota_layer_without_raw_provider_error(tmp_path) -> None:
    async def probe(_candidate):
        return {
            "ok": False,
            "code": "quota_exhausted",
            "quota": {"status": "fail", "code": "quota_exhausted"},
            "raw_error": "429 billing details at https://provider.invalid",
        }

    snapshot = await ProviderAdmissionManager(root=tmp_path).admit_chain(
        candidates=[_candidate()],
        probe=probe,
        required_roles=["text_draft"],
    )

    slot = snapshot["slots"][0]
    assert slot["admitted"] is False
    assert slot["layers"]["quota"] == {
        "status": "fail",
        "code": "quota_exhausted",
    }
    assert snapshot["admitted_chain"] == []
    assert snapshot["generation_allowed"] is False
    serialized = json.dumps(snapshot, ensure_ascii=False)
    assert "billing details" not in serialized
    assert "provider.invalid" not in serialized


@pytest.mark.asyncio
async def test_no_credits_exception_is_classified_as_quota_exhausted(tmp_path) -> None:
    async def probe(_candidate):
        raise RuntimeError("429 no credits remaining; add credits in provider console")

    admission = await ProviderAdmissionManager(root=tmp_path).admit(
        _candidate(),
        probe=probe,
    )

    assert admission.admitted is False
    assert admission.layers["quota"].code == "quota_exhausted"
    assert "credits" not in json.dumps(admission.as_dict())


@pytest.mark.asyncio
async def test_machine_credit_balance_code_is_classified_as_quota_exhausted(tmp_path) -> None:
    class CreditBalanceError(RuntimeError):
        status_code = 429
        code = "credit_balance_exhausted"

    async def probe(_candidate):
        raise CreditBalanceError("request rejected")

    admission = await ProviderAdmissionManager(root=tmp_path).admit(
        _candidate(),
        probe=probe,
    )

    assert admission.admitted is False
    assert admission.layers["quota"].code == "quota_exhausted"
    assert "request rejected" not in json.dumps(admission.as_dict())


@pytest.mark.asyncio
async def test_same_slot_provider_and_model_with_different_credentials_are_isolated(tmp_path) -> None:
    calls: list[str] = []

    async def probe(candidate: ProviderCandidate):
        calls.append(candidate.credential)
        return ProbeOutcome.success()

    manager = ProviderAdmissionManager(root=tmp_path, ttl_seconds=60)
    first, second = await asyncio.gather(
        manager.admit(_candidate(credential="credential-a"), probe=probe),
        manager.admit(_candidate(credential="credential-b"), probe=probe),
    )

    assert sorted(calls) == ["credential-a", "credential-b"]
    assert first.identity_digest != second.identity_digest
    assert first.credential_fingerprint != second.credential_fingerprint


@pytest.mark.asyncio
async def test_ttl_cache_hits_before_expiry_and_reprobes_at_expiry(tmp_path) -> None:
    now = [10.0]
    calls = 0

    async def probe(_candidate):
        nonlocal calls
        calls += 1
        return {"ok": True}

    manager = ProviderAdmissionManager(
        root=tmp_path,
        ttl_seconds=5,
        clock=lambda: now[0],
    )
    first = await manager.admit(_candidate(), probe=probe)
    now[0] = 14.999
    cached = await manager.admit(_candidate(), probe=probe)
    now[0] = 15.0
    refreshed = await manager.admit(_candidate(), probe=probe)

    assert calls == 2
    assert first.cache_hit is False
    assert cached.cache_hit is True
    assert refreshed.cache_hit is False
    assert refreshed.checked_at == 15.0


@pytest.mark.asyncio
async def test_text_backup_is_degraded_fallback_and_all_failed_chain_blocks(tmp_path) -> None:
    async def fallback_probe(candidate: ProviderCandidate):
        if candidate.slot == "text_main":
            return ProbeOutcome.failure("quota", "quota_exhausted")
        return ProbeOutcome.success()

    candidates = [
        _candidate(slot="text_main", role="text_main", credential="main-credential"),
        _candidate(slot="text_backup", role="text_backup", credential="backup-credential"),
    ]
    snapshot = await ProviderAdmissionManager(root=tmp_path / "fallback").admit_chain(
        candidates=candidates,
        probe=fallback_probe,
        required_roles=["text_draft"],
    )

    assert snapshot["generation_allowed"] is True
    assert snapshot["degraded"] is True
    assert snapshot["fallback_configured"] is True
    assert snapshot["fallback_ready"] is True
    assert snapshot["resilience_degraded"] is False
    assert [item["slot"] for item in snapshot["admitted_chain"]] == ["text_backup"]
    assert snapshot["role_decision"]["text_draft"]["selected"]["slot"] == "text_backup"

    async def fail_probe(_candidate):
        return ProbeOutcome.failure("quota", "quota_exhausted")

    failed = await ProviderAdmissionManager(root=tmp_path / "failed").admit_chain(
        candidates=candidates,
        probe=fail_probe,
        required_roles=["text_draft"],
    )
    assert failed["admitted_chain"] == []
    assert failed["generation_allowed"] is False
    assert failed["degraded"] is False
    assert failed["missing_roles"] == ["text_draft"]


@pytest.mark.asyncio
async def test_failed_configured_backup_marks_otherwise_healthy_route_degraded(
    tmp_path,
) -> None:
    candidates = [
        _candidate(slot="text_main", role="text_main", credential="main-credential"),
        _candidate(
            slot="text_backup",
            role="text_backup",
            provider="openai",
            model="backup-model",
            credential="backup-credential",
        ),
    ]

    async def probe(candidate):
        if candidate.slot == "text_backup":
            return ProbeOutcome.failure("request", "invalid_request")
        return ProbeOutcome.success()

    snapshot = await ProviderAdmissionManager(root=tmp_path).admit_chain(
        candidates=candidates,
        probe=probe,
        required_roles=["text_main"],
    )

    assert snapshot["generation_allowed"] is True
    assert snapshot["fallback_configured"] is True
    assert snapshot["fallback_ready"] is False
    assert snapshot["resilience_degraded"] is True
    assert snapshot["degraded"] is True


@pytest.mark.asyncio
async def test_google_compat_slot_can_satisfy_failed_primary_as_degraded_fallback(tmp_path) -> None:
    candidates = [
        _candidate(slot="text_main", role="text_main", credential="exhausted-main"),
        _candidate(
            slot="text_compat_google",
            role="text_compat_google",
            provider="google",
            model="gemini-test",
            credential="healthy-google",
        ),
    ]

    async def probe(candidate):
        if candidate.slot == "text_main":
            return ProbeOutcome.failure("quota", "quota_exhausted")
        return ProbeOutcome.success()

    snapshot = await ProviderAdmissionManager(root=tmp_path).admit_chain(
        candidates=candidates,
        probe=probe,
        required_roles=["text_draft"],
    )

    assert snapshot["generation_allowed"] is True
    assert snapshot["degraded"] is True
    assert [row["slot"] for row in snapshot["admitted_chain"]] == [
        "text_compat_google"
    ]


def test_document_render_role_never_uses_text_fallback() -> None:
    admitted_text = {
        "slot": "text_backup",
        "role": "text_backup",
        "provider": "openai",
        "model": "gpt-test",
        "credential_fingerprint": "a" * 64,
        "identity_digest": "b" * 64,
        "admitted": True,
        "layers": {
            name: {"status": "pass", "code": "probe_passed"}
            for name in ("configuration", "credentials", "model", "quota", "stream", "circuit")
        },
        "reason_codes": [],
        "checked_at": 1,
        "expires_at": 2,
    }

    decision = decide_required_roles([admitted_text], ["document_render"])

    assert decision["generation_allowed"] is False
    assert decision["missing_roles"] == ["document_render"]


@pytest.mark.asyncio
async def test_open_circuit_fails_locally_without_invoking_probe(tmp_path) -> None:
    calls = 0

    async def probe(_candidate):
        nonlocal calls
        calls += 1
        return {"ok": True}

    admission = await ProviderAdmissionManager(root=tmp_path).admit(
        _candidate(circuit_open=True),
        probe=probe,
    )

    assert calls == 0
    assert admission.admitted is False
    assert admission.layers["circuit"].code == "circuit_open"


@pytest.mark.asyncio
async def test_concurrent_identical_admissions_share_one_inflight_probe(tmp_path) -> None:
    calls = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def probe(_candidate):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return {"ok": True}

    manager = ProviderAdmissionManager(root=tmp_path, ttl_seconds=60)
    tasks = [
        asyncio.create_task(manager.admit(_candidate(), probe=probe))
        for _ in range(24)
    ]
    await asyncio.wait_for(started.wait(), timeout=1)
    await asyncio.sleep(0)
    release.set()
    results = await asyncio.gather(*tasks)

    assert calls == 1
    assert all(result.admitted for result in results)
    assert len({result.identity_digest for result in results}) == 1


def test_import_does_not_load_provider_sdks(assert_clean_import) -> None:
    assert_clean_import(
        "backend.zhifei_autoplan.provider_admission",
        {"openai", "anthropic", "google.generativeai", "requests", "httpx"},
    )
