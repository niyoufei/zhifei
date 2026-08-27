from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from backend.zhifei_autoplan.provider_admission import ProviderCandidate


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "standard_ingestion_pipeline.py"


def _load_module():
    name = "standard_ingestion_provider_admission_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _kwargs(tmp_path: Path) -> dict[str, Any]:
    return {
        "input_dir": tmp_path / "input",
        "output_dir": tmp_path / "output",
        "max_workers": 1,
        "llm_workers": 1,
        "llm_provider": "client-controlled-provider",
        "llm_model": "client-controlled-model",
        "llm_retries": 99,
        "llm_min_interval": 0,
        "llm_max_tokens_per_minute": 120_000,
        "ocr_max_pages": 1,
        "limit": None,
        "sample_seed": 1,
        "max_chunks_per_file": 1,
        "force_reindex": False,
        "recursive": True,
    }


def _admitted_snapshot(candidate: ProviderCandidate) -> dict[str, Any]:
    layers = {
        "configuration": {"status": "pass", "code": "configuration_ready"},
        "credentials": {"status": "pass", "code": "credentials_ready"},
        "model": {"status": "pass", "code": "model_ready"},
        "quota": {"status": "pass", "code": "quota_ready"},
        "stream": {"status": "pass", "code": "stream_ready"},
        "circuit": {"status": "pass", "code": "circuit_closed"},
    }
    selected = {
        "slot": candidate.slot,
        "role": candidate.role,
        "provider": candidate.provider,
        "model": candidate.model,
        "credential_fingerprint": candidate.fingerprint,
        "identity_digest": candidate.identity_digest,
    }
    return {
        "schema_version": "provider-admission-v1",
        "required_roles": ["text_draft"],
        "slots": [
            {
                **selected,
                "admitted": True,
                "layers": layers,
                "reason_codes": [],
                "checked_at": 1.0,
                "expires_at": 9999999999.0,
                "stream_required": True,
                "cache_hit": False,
                "probe_duration_ms": 1,
            }
        ],
        "admitted_chain": [selected],
        "role_decision": {
            "text_draft": {
                "status": "pass",
                "selected": selected,
                "attempted_slots": [candidate.slot],
            }
        },
        "missing_roles": [],
        "generation_allowed": True,
        "degraded": False,
    }


class _Coordinator:
    def __init__(self, candidate: ProviderCandidate, snapshot: dict[str, Any]) -> None:
        self.bound_candidates = (candidate,)
        self.snapshot = snapshot
        self.call: dict[str, Any] | None = None

    async def admit_chain_once(self, **kwargs: Any) -> dict[str, Any]:
        self.call = kwargs
        return self.snapshot


def test_missing_admission_fails_before_model_client_construction(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "input" / "standard.txt"
    source.parent.mkdir()
    source.write_text("规范正文" * 200, encoding="utf-8")
    candidate = ProviderCandidate(
        slot="text_draft",
        role="text_draft",
        provider="openai",
        model="server-model",
        credential="server-bound-credential",
        stream_required=True,
    )
    coordinator = _Coordinator(
        candidate,
        {
            "required_roles": ["text_draft"],
            "slots": [],
            "admitted_chain": [],
            "role_decision": {},
            "missing_roles": ["text_draft"],
            "generation_allowed": False,
            "degraded": False,
        },
    )
    constructed = 0

    def _forbidden_client(**_kwargs: Any):
        nonlocal constructed
        constructed += 1
        raise AssertionError("model client must not be constructed")

    monkeypatch.setattr(module, "build_server_provider_admission_candidates", lambda: [candidate])
    monkeypatch.setattr(module, "server_provider_admission_required_roles", lambda rows: ["text_draft"])
    monkeypatch.setattr(module, "new_provider_admission_run_coordinator", lambda _payload: coordinator)
    monkeypatch.setattr(module, "LLMClient", _forbidden_client)

    with pytest.raises(module.IngestionProviderAdmissionError, match="MODEL_PROVIDER_ADMISSION_BLOCKED"):
        asyncio.run(module.run_pipeline(**_kwargs(tmp_path)))

    assert constructed == 0
    assert coordinator.call is not None
    assert coordinator.call["candidates"] == [candidate]
    assert coordinator.call["required_roles"] == ["text_draft"]
    assert coordinator.call["probe"] is module.probe_provider_candidate


def test_admitted_run_uses_exact_bound_candidate_and_closes_client(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "input" / "standard.txt"
    source.parent.mkdir()
    source.write_text("规范正文" * 200, encoding="utf-8")
    candidate = ProviderCandidate(
        slot="text_draft",
        role="text_draft",
        provider="openai",
        model="server-admitted-model",
        credential="server-bound-credential",
        stream_required=True,
    )
    coordinator = _Coordinator(candidate, _admitted_snapshot(candidate))
    captured: dict[str, Any] = {"closed": 0}

    class _Client:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self._impl = object()

        def close(self) -> None:
            captured["closed"] += 1

    async def _process(path: Path, **kwargs: Any):
        assert kwargs["llm_client"]._impl is not None
        assert kwargs["llm_retries"] == 2
        return module.FileResult(source_file=str(path), ok=True)

    monkeypatch.setattr(module, "build_server_provider_admission_candidates", lambda: [candidate])
    monkeypatch.setattr(module, "server_provider_admission_required_roles", lambda rows: ["text_draft"])
    monkeypatch.setattr(module, "new_provider_admission_run_coordinator", lambda _payload: coordinator)
    monkeypatch.setattr(module, "LLMClient", _Client)
    monkeypatch.setattr(module, "_process_one_file", _process)

    summary = asyncio.run(module.run_pipeline(**_kwargs(tmp_path)))

    assert captured["provider"] == candidate.provider
    assert captured["model"] == candidate.model
    assert captured["api_key"] == candidate.credential
    assert captured["reliability_identity"] == candidate.identity_digest
    assert captured["retry_attempts"] == 1
    assert captured["closed"] == 1
    assert summary["llm_provider"] == candidate.provider
    assert summary["llm_model"] == candidate.model
    assert summary["llm_invoked"] is True
    assert "server-bound-credential" not in str(summary)


def test_cached_or_empty_run_is_model_free_and_does_not_admit(monkeypatch, tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "input").mkdir()

    def _forbidden(*_args: Any, **_kwargs: Any):
        raise AssertionError("deterministic no-model path must not run admission or construct a client")

    monkeypatch.setattr(module, "build_server_provider_admission_candidates", _forbidden)
    monkeypatch.setattr(module, "LLMClient", _forbidden)

    summary = asyncio.run(module.run_pipeline(**_kwargs(tmp_path)))

    assert summary["ok"] is True
    assert summary["processed"] == 0
    assert summary["llm_invoked"] is False
    assert summary["llm_provider"] == ""
    assert summary["llm_model"] == ""
