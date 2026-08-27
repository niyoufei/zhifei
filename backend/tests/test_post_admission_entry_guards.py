from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import BackgroundTasks, HTTPException


def _forbidden_call(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} must not be called")

    return fail


def test_compose_never_implicitly_starts_autoplan_or_a_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy auto flags and default credentials cannot turn /compose into AI."""

    from backend.app import main
    from backend import (
        compose_engine_service,
        kg_context_service,
        precheck_guard_service,
        project_profile_service,
        region_upgrade_service,
    )
    from backend.app.routers import actions_bridge, zhifei_autoplan
    from backend.zhifei_autoplan import orchestrator
    from backend.zhifei_autoplan.utils.llm_client import LLMClient

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZF_AUTOPLAN_AUTO", "1")
    monkeypatch.setenv("ZF_DEFAULT_PROVIDER", "openai")
    monkeypatch.setenv("ZF_DEFAULT_MODEL", "server-default-model")
    monkeypatch.setenv("OPENAI_API_KEY", "compose-default-key-must-not-run")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "compose-doc-key-must-not-run")

    async def forbidden_complete(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("LLMClient.complete must not be called by /compose")

    forbidden_autoplan = _forbidden_call("run_autoplan")
    monkeypatch.setattr(orchestrator, "run_autoplan", forbidden_autoplan)
    monkeypatch.setattr(zhifei_autoplan, "run_autoplan", forbidden_autoplan)
    monkeypatch.setattr(actions_bridge, "run_autoplan", forbidden_autoplan)
    monkeypatch.setattr(LLMClient, "complete", forbidden_complete)

    monkeypatch.setattr(
        project_profile_service,
        "generate_project_profile",
        lambda payload: {"topic": payload.get("topic")},
    )
    monkeypatch.setattr(
        compose_engine_service,
        "build_sections_from_kg",
        lambda **_kwargs: [{"title": "第一章", "content": "仅本地合成正文"}],
    )
    monkeypatch.setattr(
        region_upgrade_service,
        "resolve_region_upgrade",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        kg_context_service,
        "build_kg_context",
        lambda *_args, **_kwargs: {"selected_packs": []},
    )
    monkeypatch.setattr(
        precheck_guard_service,
        "run_precheck_guard",
        lambda *_args, **_kwargs: {"passed": True},
    )
    monkeypatch.setattr(
        main.composer,
        "compose",
        lambda **_kwargs: {"sections": [{"title": "第一章", "content": "本地正文"}]},
    )
    monkeypatch.setattr(
        main,
        "write_compose_to_docx",
        lambda *_args, **_kwargs: str(tmp_path / "build" / "compose_output.docx"),
    )

    background_tasks = BackgroundTasks()
    response = main.compose(
        main.ComposeRequest(topic="离线项目", outline=["第一章"]),
        background_tasks,
    )

    assert response["status"] == "ok"
    assert response["sections"] == [{"title": "第一章", "content": "仅本地合成正文"}]
    assert background_tasks.tasks == []
    persisted = (tmp_path / "build" / "compose.json").read_text(encoding="utf-8")
    assert "compose-default-key-must-not-run" not in persisted
    assert "compose-doc-key-must-not-run" not in persisted


@pytest.mark.parametrize(
    "client_fields",
    [
        {},
        {
            "provider": "client-provider",
            "model": "client-model",
            "api_key": "client-api-key-must-never-run",
            "base_url": "https://client.invalid/v1",
            "secret_key": "client-secret-key-must-never-run",
            "token_url": "https://client.invalid/token",
        },
    ],
    ids=["client-defaults-omitted", "malicious-client-overrides"],
)
@pytest.mark.asyncio
async def test_optimize_requires_fresh_server_admission_and_only_uses_exact_admitted_key(
    client_fields: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import zhifei_autoplan as legacy
    from backend.zhifei_autoplan import provider_runtime

    monkeypatch.chdir(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    source = {
        "variants": [
            {
                "sections": [
                    {"title": "质量管理", "content": "原始正文【证据:合成资料#p1】"}
                ]
            }
        ]
    }
    source_path = build / "autoplan_generated.json"
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    server_route_key = "server-route-key-must-not-serialize"
    admitted_key = "exact-admitted-key-must-not-serialize"
    document_key = "document-key-must-not-serialize"
    server_text = provider_runtime.ProviderSlot(
        slot="text_main",
        role="text_main",
        provider="openai",
        model="server-approved-model",
        api_key=server_route_key,
        key_alias="OPENAI_API_KEY",
    )
    document_slot = provider_runtime.ProviderSlot(
        slot="document_render",
        role="document_render",
        provider="anthropic",
        model="server-document-model",
        api_key=document_key,
        key_alias="ANTHROPIC_API_KEY",
    )
    monkeypatch.setattr(provider_runtime, "build_server_text_slots", lambda **_kwargs: [server_text])
    monkeypatch.setattr(provider_runtime, "resolve_document_render_slot", lambda: document_slot)
    monkeypatch.setattr(provider_runtime, "resolve_automation_slot", lambda: None)
    monkeypatch.setattr(provider_runtime, "resolve_image_slots", lambda: [])

    monkeypatch.setattr(legacy, "_auth_user", lambda _authorization: {"id": "offline-user"})
    monkeypatch.setattr(legacy, "_charge", lambda *_args, **_kwargs: None)
    admission_calls: list[dict[str, Any]] = []

    async def fake_fresh_admission(routed: dict[str, Any]):
        admission_calls.append(dict(routed))
        return object(), [
            {
                "slot": "text_main",
                "role": "text_main",
                "provider": "openai",
                "model": "server-approved-model",
                "api_key": admitted_key,
            }
        ]

    monkeypatch.setattr(legacy, "_admit_server_provider_chain", fake_fresh_admission)
    optimizer_requests: list[dict[str, Any]] = []

    async def fake_optimize(data: dict[str, Any], request: dict[str, Any]):
        optimizer_requests.append(request)
        return data

    monkeypatch.setattr(legacy, "optimize_sections", fake_optimize)
    monkeypatch.setattr(legacy, "export_autoplan_docx", lambda *_args, **_kwargs: None)
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        legacy,
        "_audit",
        lambda action, **kwargs: audits.append({"action": action, **kwargs}),
    )

    request = legacy.OptimizeRequest(
        titles=["质量管理"],
        instruction="保持证据并优化表达",
        **client_fields,
    )
    response = await legacy.optimize_content(request, authorization="Bearer offline")

    assert response["ok"] is True
    assert len(admission_calls) == 1
    routed = admission_calls[0]
    assert routed["provider"] == "openai"
    assert routed["model"] == "server-approved-model"
    for forbidden in ("api_key", "api_keys", "base_url", "secret_key", "token_url"):
        assert forbidden not in routed

    assert optimizer_requests == [
        {
            "titles": ["质量管理"],
            "instruction": "保持证据并优化表达",
            "_admitted_provider_chain": [
                {
                    "slot": "text_main",
                    "role": "text_main",
                    "provider": "openai",
                    "model": "server-approved-model",
                    "api_key": admitted_key,
                }
            ],
        }
    ]

    public_material = json.dumps(response, ensure_ascii=False) + source_path.read_text(
        encoding="utf-8"
    ) + json.dumps(audits, ensure_ascii=False)
    for secret in (
        server_route_key,
        admitted_key,
        document_key,
        "client-api-key-must-never-run",
        "client-secret-key-must-never-run",
        "https://client.invalid/v1",
        "https://client.invalid/token",
    ):
        assert secret not in public_material


class _OfflineCoordinator:
    def __init__(self, candidates: list[Any]):
        self.bound_candidates = list(candidates)
        self._by_role = {candidate.role: candidate for candidate in candidates}

    def admitted_candidate(self, role: str):
        return self._by_role.get(role)


@pytest.mark.asyncio
async def test_review_apply_two_ai_rounds_share_one_fresh_admission_and_render_slot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import provider_runtime, review_revision
    from backend.zhifei_autoplan.provider_admission import ProviderCandidate

    client_key = "review-client-key-must-never-run"
    admitted_review_key = "review-exact-admitted-key-must-not-serialize"
    admitted_document_key = "review-document-key-must-not-serialize"
    target = {
        "project_id": "P-REVIEW-ADMISSION",
        "sections": [{"title": "施工进度计划", "content": "第一版正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "施工进度计划",
                    "type": "consistency",
                    "severity": "high",
                    "problem": "工期冲突",
                    "suggestion": "统一工期口径",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    job = {
        "payload": {
            "project_id": "P-REVIEW-ADMISSION",
            "provider": "client-provider",
            "model": "client-model",
            "api_key": client_key,
            "base_url": "https://review-client.invalid/v1",
        }
    }
    review_candidate = ProviderCandidate(
        slot="text_review",
        role="text_review",
        provider="anthropic",
        model="server-review-model",
        credential=admitted_review_key,
        key_alias="ANTHROPIC_API_KEY",
        stream_required=True,
    )
    draft_candidate = ProviderCandidate(
        slot="text_draft",
        role="text_draft",
        provider="anthropic",
        model="server-draft-model",
        credential="draft-admitted-key-must-not-serialize",
        key_alias="ANTHROPIC_API_KEY",
        stream_required=True,
    )
    document_candidate = ProviderCandidate(
        slot="document_render",
        role="document_render",
        provider="anthropic",
        model="server-document-model",
        credential=admitted_document_key,
        key_alias="ANTHROPIC_API_KEY",
    )
    coordinator = _OfflineCoordinator(
        [draft_candidate, review_candidate, document_candidate]
    )

    server_slots = [
        provider_runtime.ProviderSlot(
            slot=candidate.slot,
            role=candidate.role,
            provider=candidate.provider,
            model=candidate.model,
            api_key=candidate.credential,
            key_alias="ANTHROPIC_API_KEY",
        )
        for candidate in (draft_candidate, review_candidate)
    ]
    monkeypatch.setattr(provider_runtime, "build_server_text_slots", lambda **_kwargs: server_slots)
    monkeypatch.setattr(
        provider_runtime,
        "resolve_document_render_slot",
        lambda: provider_runtime.ProviderSlot(
            slot=document_candidate.slot,
            role=document_candidate.role,
            provider=document_candidate.provider,
            model=document_candidate.model,
            api_key=document_candidate.credential,
            key_alias="ANTHROPIC_API_KEY",
        ),
    )
    monkeypatch.setattr(provider_runtime, "resolve_automation_slot", lambda: None)
    monkeypatch.setattr(provider_runtime, "resolve_image_slots", lambda: [])

    admission_calls: list[object] = []

    async def fake_admit_once(**_kwargs: Any):
        admission_calls.append(object())
        return coordinator

    monkeypatch.setattr(
        actions_bridge,
        "_admit_current_server_chain_for_existing_evidence",
        fake_admit_once,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_require_formal_document_mutation",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_capture_promotion_revision",
        lambda _job: ("succeeded", 7),
    )
    monkeypatch.setattr(actions_bridge, "strip_nonconcrete_language", lambda value: value)
    monkeypatch.setattr(actions_bridge, "load_params", lambda: {})

    rebuild_calls: list[int] = []

    def fake_rebuild(results: list[dict[str, Any]], **_kwargs: Any) -> None:
        rebuild_calls.append(len(rebuild_calls) + 1)
        if len(rebuild_calls) == 1:
            results[0]["quality_checks"] = {
                "issue_list": [
                    {
                        "title": "施工进度计划",
                        "type": "consistency",
                        "severity": "high",
                        "problem": "复核仍发现工期冲突",
                        "suggestion": "再次统一工期口径",
                    }
                ],
                "auto_revision_suggestions": [],
            }
        else:
            results[0]["quality_checks"] = {
                "issue_list": [],
                "auto_revision_suggestions": [],
            }

    monkeypatch.setattr(actions_bridge, "_rebuild_postprocessed_artifacts", fake_rebuild)

    llm_initializations: list[dict[str, Any]] = []
    llm_calls: list[dict[str, Any]] = []

    class OfflineLLMClient:
        def __init__(self, provider: str, model: str, **kwargs: Any):
            self.provider = provider
            self.model = model
            self.kwargs = kwargs
            llm_initializations.append(
                {"provider": provider, "model": model, **kwargs}
            )

        async def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            llm_calls.append(
                {
                    "provider": self.provider,
                    "model": self.model,
                    "api_key": self.kwargs.get("api_key"),
                    "prompt": prompt,
                    **kwargs,
                }
            )
            round_number = 2 if "第2轮" in prompt else 1
            return {"text": f"第{round_number}轮已准入正文"}

        def close(self) -> None:
            return None

    monkeypatch.setattr(actions_bridge, "LLMClient", OfflineLLMClient)
    coordinator_seen_by_round: list[Any] = []
    original_rewrite = actions_bridge._rewrite_review_section

    async def rewrite_spy(**kwargs: Any):
        coordinator_seen_by_round.append(
            kwargs["payload"].get("_provider_admission_run_coordinator")
        )
        return await original_rewrite(**kwargs)

    monkeypatch.setattr(actions_bridge, "_rewrite_review_section", rewrite_spy)

    output_json = tmp_path / "review-candidate.json"

    def fake_save(_name: str, variants: list[dict[str, Any]]) -> dict[str, Any]:
        output_json.write_text(
            json.dumps({"variants": variants}, ensure_ascii=False),
            encoding="utf-8",
        )
        return {"json": str(output_json)}

    monkeypatch.setattr(actions_bridge, "_save_outputs", fake_save)
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(
        actions_bridge,
        "create_revision_snapshot",
        review_revision.create_revision_snapshot,
    )
    slot_coordinator_calls: list[Any] = []
    original_admitted_slot = actions_bridge._admitted_document_render_slot

    def slot_spy(value: Any):
        slot_coordinator_calls.append(value)
        return original_admitted_slot(value)

    monkeypatch.setattr(actions_bridge, "_admitted_document_render_slot", slot_spy)
    render_calls: list[dict[str, Any]] = []

    async def fake_render(**kwargs: Any) -> dict[str, Any]:
        render_calls.append(kwargs)
        return dict(kwargs["outputs"])

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", fake_render)
    promotions: list[dict[str, Any]] = []
    monkeypatch.setattr(
        actions_bridge,
        "_promote_review_candidate_two_phase",
        lambda **kwargs: promotions.append(kwargs)
        or ({"status": "succeeded", "revision": 8}, {"promotion": {"state": "committed"}}),
    )

    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-review-shared-admission",
        variant=1,
        apply_all=True,
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    with monkeypatch.context() as auth_patch:
        auth_patch.setenv("ZF_ACTIONS_KEY", "test-actions-key")
        response = await actions_bridge.actions_review_apply(
            request,
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert response["ai_rewritten_chapter_count"] == 1
    assert response["round_2_rewritten_chapter_count"] == 1
    assert len(admission_calls) == 1
    assert coordinator_seen_by_round == [coordinator, coordinator]
    assert slot_coordinator_calls == [coordinator]
    assert len(llm_initializations) == 2
    assert len(llm_calls) == 2
    assert {call["api_key"] for call in llm_calls} == {admitted_review_key}
    assert all(call["provider"] == "anthropic" for call in llm_calls)
    assert all(call["model"] == "server-review-model" for call in llm_calls)
    assert len(render_calls) == 1
    render_slot = render_calls[0]["slot_override"]
    assert render_slot.slot == "document_render"
    assert render_slot.api_key == admitted_document_key

    public_material = (
        json.dumps(response, ensure_ascii=False, default=str)
        + output_json.read_text(encoding="utf-8")
        + json.dumps(promotions, ensure_ascii=False, default=str)
        + "".join(
            path.read_text(encoding="utf-8")
            for path in (tmp_path / "revisions").rglob("*.json")
        )
    )
    for secret in (
        client_key,
        admitted_review_key,
        admitted_document_key,
        "draft-admitted-key-must-not-serialize",
        "https://review-client.invalid/v1",
    ):
        assert secret not in public_material


@pytest.mark.asyncio
async def test_review_apply_admission_failure_is_stable_503_before_any_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision
    from backend.zhifei_autoplan.professional_document_renderer import ProfessionalRenderError

    raw_failure_secret = "sk-ant-review-raw-failure-secret-123456789"
    target = {
        "sections": [{"title": "安全管理", "content": "待修订正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "安全管理",
                    "type": "core_conclusion",
                    "severity": "high",
                    "problem": "闭环不足",
                    "suggestion": "补齐闭环",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: ({"payload": {}}, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_require_formal_document_mutation",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_capture_promotion_revision",
        lambda _job: ("succeeded", 7),
    )
    monkeypatch.setattr(
        actions_bridge,
        "apply_server_provider_routing",
        lambda payload: dict(payload),
    )
    admission_calls: list[object] = []

    async def fail_admission(**_kwargs: Any):
        admission_calls.append(object())
        raise ProfessionalRenderError(f"upstream rejected {raw_failure_secret}")

    monkeypatch.setattr(
        actions_bridge,
        "_admit_current_server_chain_for_existing_evidence",
        fail_admission,
    )
    monkeypatch.setattr(actions_bridge, "LLMClient", _forbidden_call("LLMClient"))
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        _forbidden_call("candidate persistence"),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_render_professional_outputs_for_job",
        _forbidden_call("professional render"),
    )
    monkeypatch.setattr(actions_bridge, "update_job", _forbidden_call("job promotion"))
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(
        actions_bridge,
        "create_revision_snapshot",
        review_revision.create_revision_snapshot,
    )

    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-review-admission-blocked",
        apply_all=True,
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    monkeypatch.setenv("ZF_ACTIONS_KEY", "test-actions-key")
    with pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_review_apply(
            request,
            x_actions_key="test-actions-key",
        )

    assert admission_calls and len(admission_calls) == 1
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "MODEL_PROVIDER_ADMISSION_BLOCKED"
    assert "模型供应商准入未通过" in exc_info.value.detail["message"]
    assert raw_failure_secret not in json.dumps(exc_info.value.detail, ensure_ascii=False)
