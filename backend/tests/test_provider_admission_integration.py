from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from backend.app.routers import actions_bridge
from backend.zhifei_autoplan import generation_checkpoint, orchestrator
from backend.zhifei_autoplan.orchestrator import (
    ProviderAdmissionRunCoordinator,
    run_autoplan,
)
from backend.zhifei_autoplan.provider_admission import ProviderAdmissionManager


@pytest.fixture(autouse=True)
def _configure_actions_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZF_ACTIONS_KEY", "zf-webui-key")


def _passing_quality_result() -> dict[str, Any]:
    return {
        "score": 100,
        "remediation": [],
        "quality_gate": {"pass": True, "blocking_issue_count": 0},
        "independent_content_review": {
            "threshold": 80,
            "quality_gate": {"pass": True, "blocking_issues": []},
            "issues": [],
        },
    }


def _server_admission_payload(
    *,
    secret: str,
    coordinator: ProviderAdmissionRunCoordinator,
    include_document_render: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "topic": "脱敏测试项目",
        "outline": ["项目概况"],
        "strict_tender_outline": True,
        "provider_chain": [
            {
                "slot": "text_draft",
                "role": "text_draft",
                "provider": "openai",
                "model": "gpt-admission-test",
                "api_key": secret,
                "key_alias": "TEST_TEXT_KEY",
            }
        ],
        "_provider_admission_required": True,
        "_provider_admission_required_roles": ["text_draft"],
        "_provider_admission_run_coordinator": coordinator,
        "quality_strict": False,
        "auto_remediate": False,
        "generate_images": False,
        "fail_on_model_exhaustion": True,
        "no_write": True,
    }
    if include_document_render:
        payload["_provider_admission_required_roles"].append("document_render")
        payload["_provider_admission_extra_slots"] = [
            {
                "slot": "document_render",
                "role": "document_render",
                "provider": "anthropic",
                "model": "claude-render-test",
                "api_key": secret,
                "key_alias": "TEST_RENDER_KEY",
            }
        ]
    return payload


@pytest.fixture
def isolated_generation_runtime(monkeypatch):
    counters: dict[str, Any] = {
        "llm_init": [],
        "llm_preflight": 0,
        "llm_complete": 0,
        "llm_close": 0,
        "writer_init": 0,
        "writer_write": 0,
        "writer_credentials": [],
        "chart": 0,
        "preview": 0,
        "mindmap": 0,
    }
    tender_box: dict[str, Any] = {"value": {}}
    boq_box: dict[str, Any] = {"value": {}}

    class FakeLLMClient:
        def __init__(self, *args, **kwargs) -> None:
            self.provider = kwargs.get("provider")
            self.model = kwargs.get("model")
            self.api_key = kwargs.get("api_key")
            counters["llm_init"].append(
                {
                    "provider": self.provider,
                    "model": self.model,
                    "api_key": self.api_key,
                }
            )

        async def preflight(self, *args, **kwargs):
            counters["llm_preflight"] += 1
            return {
                "ok": True,
                "provider": self.provider,
                "model": self.model,
                "streamed": True,
            }

        async def complete(self, *args, **kwargs):
            counters["llm_complete"] += 1
            return {"text": "模型复核正文"}

        def close(self) -> None:
            counters["llm_close"] += 1

    class FakeSectionWriter:
        def __init__(self, llm=None) -> None:
            counters["writer_init"] += 1
            self.llm = llm

        async def write(self, title: str, _context: dict[str, Any]):
            counters["writer_write"] += 1
            counters["writer_credentials"].append(
                getattr(self.llm, "api_key", None) if self.llm is not None else None
            )
            return {"title": title, "content": f"{title}脱敏正文，检查频次为1次/日。"}

    async def _terminology_passthrough(*args, **kwargs):
        return {
            "ok": True,
            "terminology_loaded": False,
            "entry_count": 0,
            "changed_sections": 0,
            "replacement_count": 0,
        }

    def _chart(*args, **kwargs):
        counters["chart"] += 1
        return []

    def _preview(*args, **kwargs):
        counters["preview"] += 1
        return []

    def _mindmap(*args, **kwargs):
        counters["mindmap"] += 1

    monkeypatch.setattr(
        orchestrator,
        "load_tender_matrix",
        lambda project_id=None: tender_box["value"],
    )
    monkeypatch.setattr(
        orchestrator,
        "load_boq_data",
        lambda project_id=None: boq_box["value"],
    )
    monkeypatch.setattr(orchestrator, "search_kg", lambda *args, **kwargs: {"results": []})
    monkeypatch.setattr(orchestrator, "search_ingested_docs", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestrator, "best_ingested_hit", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "query_compliance", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestrator, "LLMClient", FakeLLMClient)
    monkeypatch.setattr(orchestrator, "SectionWriter", FakeSectionWriter)
    monkeypatch.setattr(orchestrator, "generate_boq_chart", _chart)
    monkeypatch.setattr(orchestrator, "generate_ingested_previews", _preview)
    monkeypatch.setattr(orchestrator, "generate_outline_mindmap", _mindmap)
    monkeypatch.setattr(orchestrator, "run_quality_checks", lambda *args, **kwargs: _passing_quality_result())
    monkeypatch.setattr(orchestrator, "apply_remediation", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        orchestrator,
        "normalize_sections_terminology_async",
        _terminology_passthrough,
    )
    monkeypatch.setattr(
        orchestrator,
        "get_compliance_registry_status",
        lambda **_kwargs: {"ready": True, "verified_count": 1, "warnings": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "list_verified_standard_metadata",
        lambda **kwargs: [
            {
                "standard_code": "GB/T 50326-2017",
                "standard_name": "建设工程项目管理规范",
                "source_name": "建设工程项目管理规范",
                "current_version": "GB/T 50326-2017",
                "effective_status": "现行有效",
                "official_source": "https://official.example/GB-T-50326-2017",
                "domain_tags": ["通用工程"],
                "latest": True,
                "metadata_only": True,
                "verified": True,
                "official_registry_verified": True,
            }
        ],
    )
    monkeypatch.setattr(
        orchestrator,
        "build_project_applicable_standards_manifest",
        lambda _rows: {
            "verified_count": 1,
            "unverified_count": 0,
            "standards": [],
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "audit_standard_citations",
        lambda *args, **kwargs: {"ok": True, "violation_count": 0, "violations": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "build_delivery_quality_gate",
        lambda **kwargs: {
            "delivery_allowed": True,
            "decision_digest": "delivery-test-digest",
            "blocker_count": 0,
            "warning_count": 0,
            "blockers": [],
        },
    )

    return {
        "counters": counters,
        "tender": tender_box,
        "boq": boq_box,
    }


@pytest.mark.asyncio
async def test_evidence_readiness_failure_precedes_all_external_side_effects(
    monkeypatch,
    tmp_path,
    isolated_generation_runtime,
) -> None:
    counters = isolated_generation_runtime["counters"]
    malformed_tender = {
        "outline": ["质量管理"],
        "items": [
            {
                "dimension": "扣分项",
                "keywords": ["质量验收闭环"],
                "source_spans": [
                    {
                        "file_name": "招标文件.pdf",
                        "page": 1,
                        "start": None,
                        "end": None,
                        "snippet": "",
                    }
                ],
            }
        ]
    }
    isolated_generation_runtime["tender"]["value"] = malformed_tender
    isolated_generation_runtime["boq"]["value"] = {"items": [{"code": "001"}]}

    probe_calls: list[str] = []

    async def _probe(candidate, **kwargs):
        probe_calls.append(candidate.slot)
        return {"ok": True}

    monkeypatch.setattr(orchestrator, "probe_provider_candidate", _probe)

    from backend.zhifei_autoplan import logo_runtime

    logo_calls = {"resolve": 0, "prepare": 0}

    def _resolve_logo(*args, **kwargs):
        logo_calls["resolve"] += 1
        return tmp_path / "logo.png"

    def _prepare_logo(*args, **kwargs):
        logo_calls["prepare"] += 1
        return str(tmp_path / "logo-embed.png")

    monkeypatch.setattr(logo_runtime, "resolve_logo", _resolve_logo)
    monkeypatch.setattr(logo_runtime, "prepare_logo_for_embedding", _prepare_logo)

    renderer_calls = 0

    async def _renderer(**kwargs):
        nonlocal renderer_calls
        renderer_calls += 1
        return {}

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", _renderer)
    monkeypatch.setattr(actions_bridge, "load_plan", lambda project_id=None: {})
    monkeypatch.setattr(
        actions_bridge,
        "load_tender_matrix",
        lambda project_id=None: malformed_tender,
    )
    monkeypatch.setattr(
        actions_bridge,
        "load_boq_data",
        lambda project_id=None: {"items": [{"code": "001"}]},
    )
    monkeypatch.setattr(
        actions_bridge,
        "_build_variant_plan",
        lambda payload: [{"variant_id": 1}],
    )

    def _server_route(payload: dict[str, Any]) -> dict[str, Any]:
        manager = ProviderAdmissionManager(root=tmp_path / "admission")
        routed = dict(payload)
        routed.update(
            _server_admission_payload(
                secret="test-evidence-gate-secret",
                coordinator=ProviderAdmissionRunCoordinator(manager),
            )
        )
        routed["outline"] = ["质量管理"]
        routed["bidder_company"] = "脱敏投标人"
        routed["generate_images"] = True
        routed.pop("_provider_admission_run_coordinator", None)
        return routed

    monkeypatch.setattr(actions_bridge, "_apply_server_provider_routing_or_503", _server_route)

    request = actions_bridge.ActionsGenerateRequest(
        project_id="project-evidence-gate",
        topic="脱敏项目",
        outline=["质量管理"],
        strict_tender_outline=True,
        bidder_company="脱敏投标人",
        generate_images=True,
        quality_strict=True,
    )

    with pytest.raises(ValueError, match="证据生成前准入失败"):
        await actions_bridge.actions_generate(request, "zf-webui-key")

    assert probe_calls == []
    assert counters["llm_init"] == []
    assert counters["writer_init"] == 0
    assert counters["writer_write"] == 0
    assert logo_calls == {"resolve": 0, "prepare": 0}
    assert counters["chart"] == 0
    assert counters["preview"] == 0
    assert counters["mindmap"] == 0
    assert renderer_calls == 0


@pytest.mark.asyncio
async def test_multi_variant_run_probes_each_unique_candidate_once_and_emits_one_lifecycle(
    monkeypatch,
    tmp_path,
    isolated_generation_runtime,
) -> None:
    secret = "test-shared-run-secret"
    manager = ProviderAdmissionManager(root=tmp_path / "admission", ttl_seconds=120)
    coordinator = ProviderAdmissionRunCoordinator(manager)
    coordinator.configure_preflight_variants([1, 2])
    events: list[dict[str, Any]] = []
    probes: list[tuple[str, str, str]] = []

    async def _probe(candidate, **kwargs):
        probes.append((candidate.slot, candidate.provider, candidate.model))
        await asyncio.sleep(0)
        return {"ok": True}

    monkeypatch.setattr(orchestrator, "probe_provider_candidate", _probe)
    base = _server_admission_payload(secret=secret, coordinator=coordinator)
    base["_progress_callback"] = events.append
    first = {**base, "variant_id": 1}
    second = {**base, "variant_id": 2}

    results = await asyncio.gather(run_autoplan(first), run_autoplan(second))

    assert len(results) == 2
    assert sorted(probes) == [
        ("document_render", "anthropic", "claude-render-test"),
        ("text_draft", "openai", "gpt-admission-test"),
    ]
    event_names = [event.get("event") for event in events]
    assert event_names.count("provider_admission_started") == 1
    assert event_names.count("provider_admission_completed") == 1
    preflight_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "compliance_preflight"
    ]
    admission_index = event_names.index("provider_admission_started")
    assert {
        event.get("variant_id")
        for event in events
        if event.get("event") == "compliance_preflight"
    } == {1, 2}
    assert len(preflight_indexes) == 2
    assert max(preflight_indexes) < admission_index
    assert all(
        result["model_routing"]["provider_admission"]["generation_allowed"]
        for result in results
    )


@pytest.mark.asyncio
async def test_preflight_barrier_abort_never_leaves_variant_waiting(
    tmp_path,
) -> None:
    before_wait = ProviderAdmissionRunCoordinator(
        ProviderAdmissionManager(root=tmp_path / "before")
    )
    before_wait.configure_preflight_variants([1, 2])
    before_wait.abort_preflight_barrier()
    with pytest.raises(RuntimeError, match="provider_admission_preflight_aborted"):
        await asyncio.wait_for(before_wait.await_preflight_barrier(1), timeout=0.2)

    while_waiting = ProviderAdmissionRunCoordinator(
        ProviderAdmissionManager(root=tmp_path / "waiting")
    )
    while_waiting.configure_preflight_variants([1, 2])
    waiter = asyncio.create_task(while_waiting.await_preflight_barrier(1))
    await asyncio.sleep(0)
    while_waiting.abort_preflight_barrier()
    with pytest.raises(RuntimeError, match="provider_admission_preflight_aborted"):
        await asyncio.wait_for(waiter, timeout=0.2)


@pytest.mark.asyncio
async def test_server_admission_suppresses_legacy_model_preflight_even_when_requested(
    monkeypatch,
    tmp_path,
    isolated_generation_runtime,
) -> None:
    counters = isolated_generation_runtime["counters"]
    manager = ProviderAdmissionManager(root=tmp_path / "admission")
    coordinator = ProviderAdmissionRunCoordinator(manager)
    events: list[dict[str, Any]] = []
    probe_calls: list[str] = []

    async def _probe(candidate, **kwargs):
        probe_calls.append(candidate.slot)
        return {"ok": True}

    monkeypatch.setattr(orchestrator, "probe_provider_candidate", _probe)
    payload = _server_admission_payload(
        secret="test-preflight-secret",
        coordinator=coordinator,
        include_document_render=False,
    )
    payload["model_preflight"] = True
    payload["_progress_callback"] = events.append

    result = await run_autoplan(payload)

    assert probe_calls == ["text_draft"]
    assert counters["llm_preflight"] == 0
    assert "model_preflight_started" not in [event.get("event") for event in events]
    assert result["model_routing"]["reliability"]["preflight_enabled"] is False
    assert result["model_routing"]["reliability"]["preflight"] == []


@pytest.mark.asyncio
async def test_dry_run_makes_no_provider_image_or_professional_render_call(
    monkeypatch,
    isolated_generation_runtime,
) -> None:
    counters = isolated_generation_runtime["counters"]
    probe_calls = 0
    renderer_calls = 0

    async def _probe(candidate, **kwargs):
        nonlocal probe_calls
        probe_calls += 1
        return {"ok": True}

    async def _renderer(**kwargs):
        nonlocal renderer_calls
        renderer_calls += 1
        return {}

    monkeypatch.setattr(orchestrator, "probe_provider_candidate", _probe)
    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", _renderer)
    monkeypatch.setattr(actions_bridge, "load_plan", lambda project_id=None: {})
    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda project_id=None: {})
    monkeypatch.setattr(actions_bridge, "load_boq_data", lambda project_id=None: {})
    monkeypatch.setattr(
        actions_bridge,
        "_build_variant_plan",
        lambda payload: [{"variant_id": 1}],
    )
    monkeypatch.setattr(
        actions_bridge,
        "_apply_server_provider_routing_or_503",
        lambda payload: {
            **payload,
            "provider_chain": [
                {
                    "slot": "text_draft",
                    "role": "text_draft",
                    "provider": "openai",
                    "model": "gpt-dry-run-test",
                    "api_key": "dry-run-secret-must-not-be-used",
                }
            ],
            "_provider_admission_required": True,
            "_provider_admission_required_roles": ["text_draft"],
        },
    )
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda base_name, results, **_kwargs: {"json": ["dry-run.json"], "docx": []},
    )

    request = actions_bridge.ActionsGenerateRequest(
        topic="脱敏预览",
        outline=["项目概况"],
        dry_run=True,
        generate_images=True,
        model_preflight=True,
    )
    response = await actions_bridge.actions_generate(request, "zf-webui-key")

    assert response["ok"] is True
    assert response["files"]["delivery_profile"] == "dry_run_preview_no_provider_calls"
    assert response["files"]["delivery_ready"] is False
    assert probe_calls == 0
    assert counters["llm_init"] == []
    assert counters["llm_preflight"] == 0
    assert counters["llm_complete"] == 0
    assert counters["chart"] == 0
    assert counters["preview"] == 0
    assert counters["mindmap"] == 0
    assert renderer_calls == 0


@pytest.mark.asyncio
async def test_admitted_credential_is_reused_for_body_but_never_persisted(
    monkeypatch,
    tmp_path,
    isolated_generation_runtime,
) -> None:
    secret = "sk-proj-integration-secret-never-persist"
    counters = isolated_generation_runtime["counters"]
    manager = ProviderAdmissionManager(root=tmp_path / "admission")
    coordinator = ProviderAdmissionRunCoordinator(manager)
    probed_credentials: list[str] = []

    async def _probe(candidate, **kwargs):
        probed_credentials.append(candidate.credential)
        return {"ok": True}

    monkeypatch.setattr(orchestrator, "probe_provider_candidate", _probe)

    checkpoint_root = tmp_path / "checkpoints"
    monkeypatch.setattr(
        orchestrator,
        "load_section_checkpoint",
        lambda **kwargs: generation_checkpoint.load_section_checkpoint(
            **kwargs,
            root=checkpoint_root,
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "save_section_checkpoint",
        lambda **kwargs: generation_checkpoint.save_section_checkpoint(
            **kwargs,
            root=checkpoint_root,
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "finalize_generation_checkpoint",
        lambda **kwargs: generation_checkpoint.finalize_generation_checkpoint(
            **kwargs,
            root=checkpoint_root,
        ),
    )
    from backend.zhifei_autoplan import param_trace

    monkeypatch.setattr(param_trace, "save_latest_receipt", lambda *args, **kwargs: None)

    payload = _server_admission_payload(
        secret=secret,
        coordinator=coordinator,
        include_document_render=False,
    )
    payload.pop("no_write", None)
    payload["_checkpoint_namespace"] = "credential-integration-test"
    result = await run_autoplan(payload)

    assert probed_credentials == [secret]
    assert counters["writer_credentials"] == [secret]
    assert counters["llm_init"][0]["api_key"] == secret

    durable_files = [manager.snapshot_path, *checkpoint_root.rglob("*.json")]
    assert manager.snapshot_path.exists()
    assert list(checkpoint_root.rglob("*.json"))
    for path in durable_files:
        assert secret not in Path(path).read_text(encoding="utf-8")
    assert secret not in json.dumps(result, ensure_ascii=False, sort_keys=True)


@pytest.mark.asyncio
async def test_non_dry_internal_call_without_coordinator_fails_before_model(
    isolated_generation_runtime,
) -> None:
    counters = isolated_generation_runtime["counters"]
    payload = {
        "topic": "脱敏内部调用",
        "outline": ["项目概况"],
        "provider_chain": [
            {
                "slot": "legacy_direct",
                "provider": "openai",
                "model": "gpt-test",
                "api_key": "must-not-be-used",
            }
        ],
        "dry_run": False,
        "no_write": True,
        "generate_images": False,
        "quality_strict": False,
        "auto_remediate": False,
    }

    with pytest.raises(RuntimeError) as exc:
        await run_autoplan(payload)

    assert "MODEL_PROVIDER_ADMISSION_CONTEXT_MISSING" in str(exc.value)
    assert counters["llm_init"] == []
    assert counters["llm_preflight"] == 0
    assert counters["llm_complete"] == 0
