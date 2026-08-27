from __future__ import annotations

import asyncio
import hashlib
import json

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.app.routers import actions_bridge
from backend.app.routers import ingest as ingest_router


@pytest.fixture(autouse=True)
def _configure_actions_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZF_ACTIONS_KEY", "zf-webui-key")


def test_public_runtime_error_unwraps_model_chain_without_repr_leakage() -> None:
    payload = {
        "code": "MODEL_CHAIN_EXHAUSTED",
        "message": "模型链不可用",
        "failures": [
            {
                "title": "第一章",
                "provider": "anthropic",
                "model": "m",
                "error": "timeout",
            }
        ],
    }
    result = actions_bridge._public_runtime_error(RuntimeError(json.dumps(payload, ensure_ascii=False)))

    assert result["code"] == "MODEL_CHAIN_EXHAUSTED"
    assert result["message"] == "模型链不可用"
    assert result["failures"][0]["error"] == "timeout"
    assert "RuntimeError" not in json.dumps(result, ensure_ascii=False)


def test_public_runtime_error_preserves_execution_budget_exhaustion() -> None:
    payload = {
        "code": "EXECUTION_BUDGET_EXCEEDED",
        "message": "本次任务的模型调用安全预算已用尽，正文生成已停止。",
        "failures": [
            {
                "title": "第一章",
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "failure_kind": "execution_control",
                "code": "EXECUTION_BUDGET_EXCEEDED",
                "error": "EXECUTION_BUDGET_EXCEEDED",
            }
        ],
    }

    result = actions_bridge._public_runtime_error(
        RuntimeError(json.dumps(payload, ensure_ascii=False))
    )

    assert result["code"] == "EXECUTION_BUDGET_EXCEEDED"
    assert result["failures"][0]["code"] == "EXECUTION_BUDGET_EXCEEDED"
    assert "预算" in result["message"]
    assert "预算" in result["action"]
    assert "模型健康" not in result["action"]


def test_public_runtime_error_keeps_requirement_gate_out_of_provider_classifier() -> None:
    payload = {
        "code": "REQUIREMENT_EVIDENCE_CHAPTER_BLOCKED",
        "message": "章节要求证据未通过成功检查点前校验；不合格章节未保存为成功。",
        "failures": [
            {
                "title": "确保工期与质量的保障体系与措施",
                "provider": "anthropic",
                "model": "claude-opus-5",
                "failure_kind": "quality_gate",
                "code": "requirement_evidence_failed",
                "blocking_requirement_ids": ["REQ-CR-E1AF505EF062"],
                "error": (
                    "requirement_evidence_precheckpoint_blocked:"
                    "REQ-CR-E1AF505EF062"
                ),
            },
            {
                "title": "确保安全文明生产的管理体系与措施",
                "provider": "anthropic",
                "model": "claude-opus-5",
                "error": "requirement_evidence_precheckpoint_blocked:REQ-SAFETY-A1",
            },
            {
                "title": "施工总平面布置",
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "failure_kind": "provider",
                "code": "timeout",
                "error": "timeout",
            },
        ],
    }

    result = actions_bridge._public_runtime_error(
        RuntimeError(json.dumps(payload, ensure_ascii=False))
    )

    assert result["code"] == "REQUIREMENT_EVIDENCE_CHAPTER_BLOCKED"
    assert "模型健康" not in result["action"]
    assert [row["code"] for row in result["failures"]] == [
        "requirement_evidence_failed",
        "requirement_evidence_failed",
        "timeout",
    ]
    assert result["failures"][0]["blocking_requirement_ids"] == [
        "REQ-CR-E1AF505EF062"
    ]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "provider_unavailable" not in serialized
    assert "content_filtered" not in serialized


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("项目适用规范核验未通过，已停止生成：A", "STANDARD_COMPLIANCE_BLOCKED"),
        (
            "招标要求—证据生成前准入失败，未调用模型；阻断要求：A",
            "REQUIREMENT_EVIDENCE_PREFLIGHT_BLOCKED",
        ),
        ("招标要求—证据矩阵完整性校验失败：A", "REQUIREMENT_EVIDENCE_INVALID"),
        ("招标要求—证据交付硬门未通过，已停止交付；A", "REQUIREMENT_EVIDENCE_BLOCKED"),
        ("最终专业交付质量门未通过，已停止交付：A", "DELIVERY_QUALITY_BLOCKED"),
    ],
)
def test_public_runtime_error_classifies_quality_gates(raw: str, code: str) -> None:
    result = actions_bridge._public_runtime_error(ValueError(raw))

    assert result["code"] == code
    assert "模型调用失败" not in result["message"]
    assert raw not in json.dumps(result, ensure_ascii=False)


def test_complete_draft_quality_failure_preserves_recoverable_section_count() -> None:
    prior = {
        "progress": {
            "percent": 75,
            "phase": "generation",
            "chapters": {"started": 6, "succeeded": 6, "failed": 0, "total": 6},
            "checkpoint": {"status": "draft_complete", "saved_chapter_count": 6},
        },
        "result": {},
    }

    error, progress, result = actions_bridge._runtime_failure_transition(
        ValueError("unexpected post-generation gate"),
        prior,
    )

    assert error["code"] == "POST_GENERATION_QUALITY_BLOCKED"
    assert progress["phase"] == "quality_review"
    assert progress["stage"] == "quality_review_failed"
    assert progress["percent"] == 75
    assert result == {
        "section_count": 6,
        "checkpoint_status": "draft_complete",
        "recoverable": True,
        "delivery_ready": False,
    }


def test_failed_run_checkpoint_projection_never_retains_draft_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    scopes = [
        {
            "status": "failed_partial",
            "saved_chapter_count": 6,
            "saved_chapter_indexes": list(range(6)),
        }
    ]
    monkeypatch.setattr(
        actions_bridge,
        "mark_failed_checkpoint_namespace",
        lambda _job_id: scopes,
    )
    monkeypatch.setattr(
        actions_bridge,
        "append_runtime_event",
        lambda job_id, event, **fields: events.append((job_id, event, fields)),
    )

    projection = actions_bridge._seal_failed_run_checkpoints("a" * 32)

    assert projection == {
        "status": "failed_partial",
        "saved_chapter_count": 6,
        "scopes": scopes,
    }
    assert events == [
        (
            "a" * 32,
            "checkpoint_terminal_updated",
            {"checkpoint_status": "failed_partial", "saved_chapter_count": 6},
        )
    ]


def test_unified_run_routes_are_registered() -> None:
    paths = {route.path for route in actions_bridge.router.routes}
    assert "/actions/runs" in paths
    assert "/actions/runs/{run_id}" in paths
    assert "/actions/runs/{run_id}/cancel" in paths


@pytest.mark.parametrize("path", ["/actions/tender/parse", "/actions/boq/parse"])
def test_file_id_is_a_repeated_query_parameter(path: str) -> None:
    route = next(item for item in actions_bridge.router.routes if item.path == path)
    query_names = {item.name for item in route.dependant.query_params}

    assert "file_id" in query_names


def test_tender_file_id_reuses_current_parser_cache_without_reparsing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(ingest_router, "FILE_ID_SEARCH_ROOTS", (upload_root,))
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", cache_root)

    sources = [
        (b"pdf-source", "tender.pdf", "工程概况\n质量标准要求"),
        (b"docx-source", "clarification.docx", "答疑：质量要求修正"),
    ]
    file_ids = []
    for content, filename, extracted_text in sources:
        digest = hashlib.sha256(content).hexdigest()
        file_ids.append(digest)
        (upload_root / f"{digest[:8]}_{filename}").write_bytes(content)
        ingest_router._save_parse_cache(
            digest,
            {
                "base": {
                    "doc_type": filename.rsplit(".", 1)[-1],
                    "extract_text": extracted_text,
                },
                "parsed_type": None,
                "parsed_meta": None,
            },
        )

    pdf_calls = []
    unified_calls = []
    from modules.parser.parser_unify import UnifiedParser

    monkeypatch.setattr(
        actions_bridge.TenderParser,
        "_read_pdf",
        lambda self, path: pdf_calls.append(path) or (path, "unexpected"),
    )
    monkeypatch.setattr(
        UnifiedParser,
        "parse",
        lambda self: unified_calls.append(self) or {"text": "unexpected"},
    )
    monkeypatch.setattr(
        actions_bridge,
        "save_tender_matrix",
        lambda _matrix, project_id=None: "/tmp/tender-matrix.json",
    )

    result = asyncio.run(
        actions_bridge.actions_tender_parse(
            files=None,
            file_id=file_ids,
            project_id="cache-test",
            x_actions_key="zf-webui-key",
        )
    )

    assert result["ok"] is True
    assert pdf_calls == []
    assert unified_calls == []


def test_tender_source_rejects_cache_from_other_parser_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(ingest_router, "FILE_ID_SEARCH_ROOTS", (upload_root,))
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", cache_root)
    content = b"versioned-source"
    digest = hashlib.sha256(content).hexdigest()
    (upload_root / f"{digest[:8]}_tender.pdf").write_bytes(content)
    ingest_router._save_parse_cache(
        digest,
        {
            "base": {"doc_type": "pdf", "extract_text": "旧版缓存正文"},
            "parsed_type": None,
            "parsed_meta": None,
        },
    )
    metadata_path = ingest_router._parse_cache_path(digest)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["parser_version"] = "obsolete-parser"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    sources = ingest_router.resolve_ingested_tender_sources([digest])

    assert sources == [
        {
            "path": str(upload_root / f"{digest[:8]}_tender.pdf"),
            "cached_text": None,
        }
    ]


def test_job_status_exposes_unified_progress(monkeypatch) -> None:
    job_id = "a" * 32
    monkeypatch.setattr(
        actions_bridge,
        "get_job",
        lambda _job_id: {
            "job_id": job_id,
            "status": "running",
            "created_at": 1.0,
            "updated_at": 2.0,
            "progress": {
                "phase": "generation",
                "work_state": "waiting_provider",
                "heartbeat_at": 2.0,
                "chapters": {"started": 2, "succeeded": 1, "failed": 0, "total": 2},
                "provider": {"name": "openai", "model": "m"},
            },
            "agent_runtime": {},
            "result": {},
            "error": None,
        },
    )

    response = asyncio.run(actions_bridge.actions_job_status(job_id, "zf-webui-key"))
    job = response["job"]
    assert job["run_id"] == job_id
    assert job["phase"] == "generation"
    assert job["work_state"] == "waiting_provider"
    assert job["chapters"]["succeeded"] == 1
    assert job["provider"]["name"] == "openai"


def test_job_status_redacts_nested_provider_diagnostics(monkeypatch) -> None:
    job_id = "b" * 32
    raw_message = "You have no credits remaining. See https://provider.example/billing"
    provider = {
        "name": "openai",
        "model": "m",
        "circuits": {
            "openai::m": {
                "open": True,
                "last_error": {
                    "code": "provider_error",
                    "message": raw_message,
                    "provider": "openai",
                    "model": "m",
                    "retryable": False,
                },
            }
        },
    }
    monkeypatch.setattr(
        actions_bridge,
        "get_job",
        lambda _job_id: {
            "job_id": job_id,
            "status": "running",
            "progress": {"phase": "generation", "provider": provider},
            "agent_runtime": {"provider": provider},
            "result": {},
            "error": None,
        },
    )

    response = asyncio.run(actions_bridge.actions_job_status(job_id, "zf-webui-key"))
    serialized = json.dumps(response, ensure_ascii=False)
    error = response["job"]["provider"]["circuits"]["openai::m"]["last_error"]

    assert raw_message not in serialized
    assert "provider.example" not in serialized
    assert error == {
        "code": "provider_error",
        "message": "模型调用失败。",
        "action": "请查看安全诊断码，并确认模型、网络和供应商状态。",
        "retryable": False,
        "severity": "error",
    }
    assert response["job"]["progress"]["provider"] == response["job"]["provider"]
    assert response["job"]["agent_runtime"]["provider"] == response["job"]["provider"]


def test_public_runtime_error_redacts_structured_provider_failure() -> None:
    raw_message = "billing details at https://provider.example/billing"
    result = actions_bridge._public_runtime_error(
        json.dumps(
            {
                "code": "MODEL_CHAIN_EXHAUSTED",
                "message": "模型链不可用。",
                "failures": [
                    {
                        "title": "第一章",
                        "provider": "openai",
                        "model": "m",
                        "error": raw_message,
                    }
                ],
            },
            ensure_ascii=False,
        )
    )

    serialized = json.dumps(result, ensure_ascii=False)
    assert raw_message not in serialized
    assert "provider.example" not in serialized
    assert result["failures"][0]["message"] == "模型调用失败。"


def test_generation_blocks_when_mandatory_sources_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda project_id=None: None)
    monkeypatch.setattr(actions_bridge, "load_boq_data", lambda project_id=None: None)
    request = actions_bridge.ActionsGenerateRequest(
        topic="脱敏项目",
        project_id="missing-inputs",
        outline=["第一章"],
        dry_run=False,
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            actions_bridge.actions_generate_async(
                request,
                BackgroundTasks(),
                "zf-webui-key",
            )
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "MANDATORY_SOURCE_NOT_READY"
    assert error.value.detail["missing"] == ["tender", "boq"]


def test_generation_worker_is_spawn_picklable_module_level_callable() -> None:
    assert actions_bridge.run_actions_generation_job.__module__ == (
        "backend.app.routers.actions_bridge"
    )
    assert "<locals>" not in actions_bridge.run_actions_generation_job.__qualname__
