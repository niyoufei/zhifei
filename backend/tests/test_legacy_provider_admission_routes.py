from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.app.routers import zhifei_autoplan as legacy
from backend.zhifei_autoplan import orchestrator


CLIENT_SECRET = "client-must-never-reach-orchestrator"
CLIENT_BASE_URL = "https://client-controlled.example.invalid/v1"
SERVER_MODEL = "server-admitted-model"


def _request(*, topic: str = "旧入口路由测试", variants: int = 3, dry_run: bool = False) -> legacy.GenerateRequest:
    return legacy.GenerateRequest(
        project_id="project-route-test",
        topic=topic,
        outline=["第一章"],
        variants=variants,
        provider="client-provider",
        model="client-model",
        provider_chain=[
            {
                "slot": "client-slot",
                "provider": "client-provider",
                "model": "client-model",
                "api_key": CLIENT_SECRET,
                "base_url": CLIENT_BASE_URL,
            }
        ],
        api_key=CLIENT_SECRET,
        base_url=CLIENT_BASE_URL,
        secret_key=CLIENT_SECRET,
        token_url=f"{CLIENT_BASE_URL}/token",
        dry_run=dry_run,
        generate_images=True,
    )


def _run_background_tasks(background_tasks: BackgroundTasks) -> None:
    """Execute Starlette's captured sync tasks after the endpoint loop closes."""

    for task in background_tasks.tasks:
        task.func(*task.args, **task.kwargs)


def _assert_server_routed_payload(payload: dict[str, Any]) -> None:
    serialized = json.dumps(
        {key: value for key, value in payload.items() if key != "_provider_admission_run_coordinator"},
        ensure_ascii=False,
        default=str,
    )
    assert CLIENT_SECRET not in serialized
    assert CLIENT_BASE_URL not in serialized
    assert "client-provider" not in serialized
    assert "client-model" not in serialized
    assert payload["provider"] == "openai"
    assert payload["model"] == SERVER_MODEL
    assert payload["provider_chain"] == [
        {
            "slot": "text_main",
            "provider": "openai",
            "model": SERVER_MODEL,
            "key_alias": "OPENAI_API_KEY",
        }
    ]
    for forbidden in ("api_key", "api_keys", "base_url", "secret_key", "token_url"):
        assert forbidden not in payload
    assert payload["_server_provider_routing_enforced"] is True


@pytest.fixture
def legacy_route_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Keep legacy route tests deterministic and entirely inside ``tmp_path``."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()

    # Pin a single server-owned route.  Client-supplied providers, endpoints,
    # and credentials must be discarded by the endpoint before orchestration.
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "openai")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", SERVER_MODEL)
    monkeypatch.setenv("ZF_LLM_MAIN_API_KEY", "server-side-only-secret")
    for name in (
        "ZF_LLM_FALLBACK1_PROVIDER",
        "ZF_LLM_FALLBACK1_MODEL",
        "ZF_LLM_FALLBACK1_API_KEY",
        "ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ZF_ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ANTHROPIC_API_KEY",
        "ZF_ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(legacy, "_auth_user", lambda _authorization: {"id": 17, "balance": 999})
    monkeypatch.setattr(legacy, "_charge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "load_plan", lambda **_kwargs: {})
    monkeypatch.setattr(
        legacy,
        "load_tender_matrix",
        lambda **_kwargs: {"outline": ["第一章"], "source": "parsed-tender"},
    )
    monkeypatch.setattr(
        legacy,
        "load_boq_data",
        lambda **_kwargs: {"items": [{"code": "001"}], "source": "parsed-boq"},
    )
    monkeypatch.setattr(
        legacy,
        "export_autoplan_docx",
        lambda _variant, path: Path(path).write_bytes(b"docx"),
    )
    monkeypatch.setattr(
        legacy,
        "export_autoplan_compare_docx",
        lambda _variant, path: Path(path).write_bytes(b"compare-docx"),
    )
    monkeypatch.setattr(
        legacy,
        "_local_adapter_gate_results",
        lambda results: {"export_allowed": True, "results": results, "issues": []},
    )

    events: list[tuple[str, str | None]] = []
    runs: list[dict[str, Any]] = []
    coordinators: list[Any] = []
    created_payloads: list[dict[str, Any]] = []
    submissions: list[str] = []
    coordinator_tokens: list[object] = []
    jobs: dict[str, dict[str, Any]] = {}

    original_source_gate = legacy._require_generation_sources
    original_server_route = legacy._route_generation_or_503

    def source_gate(payload: dict[str, Any], project_id: str | None) -> None:
        events.append(("source_gate", str(payload.get("topic") or "")))
        original_source_gate(payload, project_id)

    def server_route(payload: dict[str, Any]) -> dict[str, Any]:
        events.append(("server_route", str(payload.get("topic") or "")))
        return original_server_route(payload)

    def new_coordinator(payload: dict[str, Any]) -> object:
        events.append(("coordinator", str(payload.get("topic") or "")))
        token = object()
        coordinator_tokens.append(token)
        return token

    async def fake_run_autoplan(payload: dict[str, Any]) -> dict[str, Any]:
        events.append(("run_autoplan", str(payload.get("topic") or "")))
        _assert_server_routed_payload(payload)
        coordinators.append(payload.get("_provider_admission_run_coordinator"))
        runs.append(
            {
                key: value
                for key, value in payload.items()
                if key != "_provider_admission_run_coordinator"
            }
        )
        return {
            "topic": str(payload.get("topic") or ""),
            "variant_id": payload.get("variant_id"),
            "sections": [],
        }

    job_counter = 0

    def create_job(payload: dict[str, Any], *, user_id: int | None = None) -> str:
        nonlocal job_counter
        job_counter += 1
        created_payloads.append(dict(payload))
        job_id = f"job-{job_counter}"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "payload": dict(payload),
            "progress": {},
            "result": None,
            "error": None,
        }
        return job_id

    def get_job(job_id: str) -> dict[str, Any] | None:
        record = jobs.get(job_id)
        return dict(record) if record is not None else None

    def acquire_job_lease(job_id: str) -> dict[str, Any] | None:
        record = jobs.get(job_id)
        if record is None or record["status"] not in {"queued", "cancel_requested"}:
            return None
        record["attempt_id"] = f"attempt-{job_id}"
        record["owner_instance_id"] = "legacy-test-worker"
        if record["status"] == "queued":
            record["status"] = "running"
        return dict(record)

    def job_lease_active(
        job_id: str,
        *,
        attempt_id: str,
        owner_instance_id: str,
        **_kwargs: Any,
    ) -> bool:
        record = jobs.get(job_id) or {}
        return (
            record.get("status") in {"running", "cancel_requested"}
            and record.get("attempt_id") == attempt_id
            and record.get("owner_instance_id") == owner_instance_id
        )

    def run_with_job_lease(
        job_id: str,
        *,
        attempt_id: str,
        owner_instance_id: str,
        callback: Callable[..., Any],
        callback_args: tuple[Any, ...] = (),
        callback_kwargs: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> Any:
        assert job_lease_active(
            job_id,
            attempt_id=attempt_id,
            owner_instance_id=owner_instance_id,
        )
        return callback(*callback_args, **dict(callback_kwargs or {}))

    def transition_job(
        job_id: str,
        *,
        allowed_from: set[str],
        status: str,
        expected_attempt_id: str | None = None,
        expected_owner_instance_id: str | None = None,
        revoke_lease: bool = False,
        **updates: Any,
    ) -> dict[str, Any] | None:
        record = jobs.get(job_id)
        if record is None or record["status"] not in allowed_from:
            return None
        if expected_attempt_id is not None and not job_lease_active(
            job_id,
            attempt_id=expected_attempt_id,
            owner_instance_id=str(expected_owner_instance_id or ""),
        ):
            return None
        record.update(updates)
        record["status"] = status
        if revoke_lease:
            record["attempt_id"] = None
            record["owner_instance_id"] = None
        return dict(record)

    def submit_isolated_job(job_id: str, target: Callable[..., Any], *args: Any) -> None:
        submissions.append(job_id)
        assert target is legacy.run_legacy_generation_job
        errors: list[BaseException] = []

        def run() -> None:
            try:
                target(*args)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        worker = threading.Thread(target=run)
        worker.start()
        worker.join(timeout=10.0)
        assert not worker.is_alive()
        if errors:
            raise errors[0]

    def reserve_variant_ids(*, count: int, **_kwargs: Any) -> list[int]:
        return list(range(1, int(count) + 1))

    monkeypatch.setattr(legacy, "_require_generation_sources", source_gate)
    monkeypatch.setattr(legacy, "_route_generation_or_503", server_route)
    monkeypatch.setattr(legacy, "new_provider_admission_run_coordinator", new_coordinator)
    monkeypatch.setattr(legacy, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(legacy, "create_job", create_job)
    monkeypatch.setattr(legacy, "get_job", get_job)
    monkeypatch.setattr(legacy, "acquire_job_lease", acquire_job_lease)
    monkeypatch.setattr(legacy, "job_lease_active", job_lease_active)
    monkeypatch.setattr(legacy, "run_with_job_lease", run_with_job_lease)
    monkeypatch.setattr(legacy, "transition_job", transition_job)
    monkeypatch.setattr(legacy, "heartbeat_job", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "append_runtime_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(legacy, "submit_isolated_job", submit_isolated_job)
    monkeypatch.setattr(legacy, "reserve_variant_ids", reserve_variant_ids)

    return {
        "events": events,
        "runs": runs,
        "coordinators": coordinators,
        "coordinator_tokens": coordinator_tokens,
        "created_payloads": created_payloads,
        "submissions": submissions,
        "jobs": jobs,
    }


def _event_names(harness: dict[str, Any], topic: str) -> list[str]:
    return [name for name, event_topic in harness["events"] if event_topic == topic]


def test_generate_routes_after_sources_strips_client_secrets_and_shares_one_coordinator(
    legacy_route_harness: dict[str, Any],
) -> None:
    topic = "同步旧入口"

    response = asyncio.run(
        legacy.generate_plan(_request(topic=topic, variants=3), authorization="Bearer test")
    )

    assert response["ok"] is True
    assert len(legacy_route_harness["runs"]) == 3
    assert _event_names(legacy_route_harness, topic) == [
        "source_gate",
        "server_route",
        "coordinator",
        "run_autoplan",
        "run_autoplan",
        "run_autoplan",
    ]
    assert len(legacy_route_harness["coordinator_tokens"]) == 1
    token = legacy_route_harness["coordinator_tokens"][0]
    assert all(item is token for item in legacy_route_harness["coordinators"])


def test_generate_async_submits_isolated_worker_and_reuses_one_coordinator(
    legacy_route_harness: dict[str, Any],
) -> None:
    topic = "异步旧入口"
    background_tasks = BackgroundTasks()

    response = asyncio.run(
        legacy.generate_plan_async(
            _request(topic=topic, variants=3),
            background_tasks,
            authorization="Bearer test",
        )
    )

    assert response == {"ok": True, "job_id": "job-1"}
    assert background_tasks.tasks == []
    assert legacy_route_harness["submissions"] == ["job-1"]
    assert len(legacy_route_harness["created_payloads"]) == 1
    _assert_server_routed_payload(legacy_route_harness["created_payloads"][0])

    assert len(legacy_route_harness["runs"]) == 3
    assert _event_names(legacy_route_harness, topic) == [
        "source_gate",
        "server_route",
        "coordinator",
        "run_autoplan",
        "run_autoplan",
        "run_autoplan",
    ]
    assert len(legacy_route_harness["coordinator_tokens"]) == 1
    token = legacy_route_harness["coordinator_tokens"][0]
    assert all(item is token for item in legacy_route_harness["coordinators"])


def test_generate_async_batch_uses_one_coordinator_per_job_and_one_route_per_request(
    legacy_route_harness: dict[str, Any],
) -> None:
    topics = ["批量任务甲", "批量任务乙"]
    background_tasks = BackgroundTasks()

    response = asyncio.run(
        legacy.generate_async_batch(
            [_request(topic=topic, variants=2) for topic in topics],
            background_tasks,
            authorization="Bearer test",
        )
    )

    assert response == {"ok": True, "job_ids": ["job-1", "job-2"]}
    assert background_tasks.tasks == []
    assert legacy_route_harness["submissions"] == ["job-1", "job-2"]
    assert len(legacy_route_harness["created_payloads"]) == 2
    for payload in legacy_route_harness["created_payloads"]:
        _assert_server_routed_payload(payload)

    assert len(legacy_route_harness["runs"]) == 4
    assert len(legacy_route_harness["coordinator_tokens"]) == 2
    for topic in topics:
        assert _event_names(legacy_route_harness, topic) == [
            "source_gate",
            "server_route",
            "coordinator",
            "run_autoplan",
            "run_autoplan",
        ]
        topic_coordinators = [
            coordinator
            for coordinator, payload in zip(
                legacy_route_harness["coordinators"],
                legacy_route_harness["runs"],
                strict=True,
            )
            if payload["topic"] == topic
        ]
        assert len(topic_coordinators) == 2
        assert topic_coordinators[0] is topic_coordinators[1]
    assert legacy_route_harness["coordinator_tokens"][0] is not legacy_route_harness["coordinator_tokens"][1]


def test_isolated_worker_failure_is_classified_and_persisted_without_secondary_error(
    legacy_route_harness: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        legacy,
        "run_autoplan",
        AsyncMock(side_effect=RuntimeError("503 provider unavailable")),
    )

    response = asyncio.run(
        legacy.generate_plan_async(
            _request(topic="隔离任务异常", variants=1),
            BackgroundTasks(),
            authorization="Bearer test",
        )
    )

    assert response == {"ok": True, "job_id": "job-1"}
    record = legacy_route_harness["jobs"]["job-1"]
    assert record["status"] == "failed"
    error = json.loads(record["error"])
    assert error["code"] == "provider_unavailable"
    assert error["message"]
    assert error["action"]


@pytest.mark.parametrize("endpoint", ["generate", "generate_async", "generate_async_batch"])
def test_legacy_production_routes_stop_at_mandatory_source_gate_before_provider_routing(
    endpoint: str,
    legacy_route_harness: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(legacy, "load_boq_data", lambda **_kwargs: {})
    route = MagicMock(side_effect=AssertionError("server routing must not run before the source gate passes"))
    monkeypatch.setattr(legacy, "_route_generation_or_503", route)
    background_tasks = BackgroundTasks()
    request = _request(topic=f"资料缺失-{endpoint}", variants=2)

    with pytest.raises(HTTPException) as exc_info:
        if endpoint == "generate":
            asyncio.run(legacy.generate_plan(request, authorization="Bearer test"))
        elif endpoint == "generate_async":
            asyncio.run(
                legacy.generate_plan_async(
                    request,
                    background_tasks,
                    authorization="Bearer test",
                )
            )
        else:
            asyncio.run(
                legacy.generate_async_batch(
                    [request],
                    background_tasks,
                    authorization="Bearer test",
                )
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "MANDATORY_SOURCE_NOT_READY"
    assert exc_info.value.detail["missing"] == ["boq"]
    route.assert_not_called()
    assert background_tasks.tasks == []
    assert legacy_route_harness["runs"] == []
    assert legacy_route_harness["created_payloads"] == []


@pytest.mark.asyncio
async def test_dry_run_never_instantiates_model_or_calls_any_image_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the real orchestrator branch while every external AI hook fails loudly."""

    forbidden = MagicMock(side_effect=AssertionError("dry_run invoked a model or image provider"))
    monkeypatch.setattr(orchestrator, "LLMClient", forbidden)
    monkeypatch.setattr(orchestrator, "generate_boq_chart", forbidden)
    monkeypatch.setattr(orchestrator, "generate_ingested_previews", forbidden)
    monkeypatch.setattr(orchestrator, "generate_outline_mindmap", forbidden)

    writer = MagicMock()
    writer.write = AsyncMock(return_value={"title": "第一章", "content": "离线预览内容。"})
    monkeypatch.setattr(orchestrator, "SectionWriter", MagicMock(return_value=writer))
    monkeypatch.setattr(orchestrator, "load_tender_matrix", lambda **_kwargs: {})
    monkeypatch.setattr(orchestrator, "load_boq_data", lambda **_kwargs: {})
    monkeypatch.setattr(orchestrator, "search_kg", lambda *_args, **_kwargs: {"results": []})
    monkeypatch.setattr(orchestrator, "search_ingested_docs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        orchestrator,
        "get_compliance_registry_status",
        lambda: {"ready": True, "verified_count": 0, "warnings": []},
    )
    monkeypatch.setattr(
        orchestrator,
        "list_verified_standard_metadata",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        orchestrator,
        "run_quality_checks",
        lambda *_args, **_kwargs: {
            "score": 100,
            "remediation": [],
            "quality_gate": {"pass": True, "blocking_issue_count": 0},
            "independent_content_review": {"threshold": 0},
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "normalize_sections_terminology_async",
        AsyncMock(
            return_value={
                "ok": True,
                "terminology_loaded": False,
                "entry_count": 0,
                "changed_sections": 0,
                "replacement_count": 0,
            }
        ),
    )

    result = await orchestrator.run_autoplan(
        {
            "topic": "dry-run-no-provider-call",
            "outline": ["第一章"],
            "provider": "openai",
            "model": "must-not-run",
            "provider_chain": [
                {
                    "slot": "text_main",
                    "provider": "openai",
                    "model": "must-not-run",
                }
            ],
            "dry_run": True,
            "generate_images": True,
            "auto_remediate": False,
            "quality_strict": False,
            "no_write": True,
        }
    )

    assert result["topic"] == "dry-run-no-provider-call"
    forbidden.assert_not_called()
    writer.write.assert_awaited()
