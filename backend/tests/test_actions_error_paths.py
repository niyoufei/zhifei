from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse


@pytest.mark.asyncio
async def test_actions_generate_async_returns_structured_provider_error_when_text_provider_missing(tmp_path, monkeypatch):
    from backend.app.routers.actions_bridge import ActionsGenerateRequest, actions_generate_async
    from backend.zhifei_autoplan import workspace as ws

    for key in (
        "OPENAI_API_KEY_TEXT_MAIN",
        "ZF_LLM_MAIN_API_KEY",
        "OPENAI_API_KEY",
        "ZF_OPENAI_API_KEY",
        "OPENAI_API_KEY_TEXT_BACKUP",
        "ZF_LLM_FALLBACK1_API_KEY",
        "GEMINI_API_KEY_A",
        "ZF_GOOGLE_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ZF_ENABLE_GEMINI_TEXT_FALLBACK", raising=False)

    req = ActionsGenerateRequest(
        topic="provider-missing",
        project_id="provider_missing_case",
        outline=["工程概况"],
        generation_mode="quality_200",
        dry_run=False,
        generate_images=False,
        provider="openai",
        model="gpt-5.4",
    )

    with patch.object(ws, "WORKSPACE_ROOT", tmp_path / "workspaces"), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await actions_generate_async(req, session_id="provider-missing", x_actions_key="test-actions-key")

    assert exc.value.status_code == 503
    detail = exc.value.detail
    assert detail["code"] == "provider_not_configured"
    assert detail["stage"] == "payload_prepare"
    assert detail["next_action"] == "configure text provider env keys or use dry_run=true"
    assert detail["log_anchor"].startswith("actions.payload_prepare.")


@pytest.mark.asyncio
async def test_actions_result_returns_structured_job_not_done_response(tmp_path):
    from backend.app.routers.actions_bridge import actions_result
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="result-pending"))
        job_id = job_store.create_job(
            {
                "topic": "result-pending",
                "workspace_dir": workspace_dir,
                "request_id": "req-result-pending",
                "trace_id": "trace-result-pending",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="running", error="worker-started")

        response = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="result-pending",
            x_actions_key="test-actions-key",
        )

    assert response == {
        "ok": False,
        "code": "job_not_done",
        "message": "job not done",
        "job_id": job_id,
        "status": "running",
        "error": "worker-started",
        "request_id": "req-result-pending",
        "trace_id": "trace-result-pending",
        "next_action": "poll /actions/job_status until status=done",
    }


@pytest.mark.asyncio
async def test_actions_result_returns_structured_result_json_not_found(tmp_path):
    from backend.app.routers.actions_bridge import actions_result
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    missing_json = tmp_path / "missing-result.json"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="result-missing-json"))
        job_id = job_store.create_job(
            {
                "topic": "result-missing-json",
                "workspace_dir": workspace_dir,
                "request_id": "req-result-missing-json",
                "trace_id": "trace-result-missing-json",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(missing_json)},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_result(
                job_id=job_id,
                variant=1,
                session_id="result-missing-json",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 404
    detail = exc.value.detail
    assert detail["code"] == "result_json_not_found"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-result-missing-json"
    assert detail["trace_id"] == "trace-result-missing-json"
    assert detail["extra"] == {"json_path": str(missing_json)}


@pytest.mark.asyncio
async def test_actions_result_returns_structured_empty_result(tmp_path):
    from backend.app.routers.actions_bridge import actions_result
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    result_json = tmp_path / "empty-result.json"
    result_json.write_text(json.dumps({"variants": []}), encoding="utf-8")
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="result-empty"))
        job_id = job_store.create_job(
            {
                "topic": "result-empty",
                "workspace_dir": workspace_dir,
                "request_id": "req-result-empty",
                "trace_id": "trace-result-empty",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(result_json)},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_result(
                job_id=job_id,
                variant=1,
                session_id="result-empty",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 404
    detail = exc.value.detail
    assert detail["code"] == "empty_result"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-result-empty"
    assert detail["trace_id"] == "trace-result-empty"
    assert detail["extra"] == {"json_path": str(result_json)}


@pytest.mark.asyncio
async def test_actions_review_issues_returns_structured_empty_result_variants(tmp_path):
    from backend.app.routers.actions_bridge import actions_review_issues
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    result_json = tmp_path / "review-empty.json"
    result_json.write_text(json.dumps({"variants": []}), encoding="utf-8")
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-empty"))
        job_id = job_store.create_job(
            {
                "topic": "review-empty",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-empty",
                "trace_id": "trace-review-empty",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(result_json)},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_review_issues(
                job_id=job_id,
                variant=1,
                session_id="review-empty",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 404
    detail = exc.value.detail
    assert detail["code"] == "empty_result_variants"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-review-empty"
    assert detail["trace_id"] == "trace-review-empty"
    assert detail["extra"] == {"json_path": str(result_json)}


@pytest.mark.asyncio
async def test_actions_review_issues_returns_structured_job_not_done(tmp_path):
    from backend.app.routers.actions_bridge import actions_review_issues
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-pending"))
        job_id = job_store.create_job(
            {
                "topic": "review-pending",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-pending",
                "trace_id": "trace-review-pending",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="running")

        with pytest.raises(HTTPException) as exc:
            await actions_review_issues(
                job_id=job_id,
                variant=1,
                session_id="review-pending",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert detail["code"] == "job_not_done"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-review-pending"
    assert detail["trace_id"] == "trace-review-pending"
    assert detail["extra"] == {"status": "running"}


@pytest.mark.asyncio
async def test_actions_generate_async_returns_structured_worker_spawn_failed(tmp_path, monkeypatch):
    from backend.app.routers.actions_bridge import ActionsGenerateRequest, actions_generate_async
    from backend.zhifei_autoplan import workspace as ws

    req = ActionsGenerateRequest(
        topic="worker-spawn-fail",
        project_id="worker_spawn_case",
        outline=["工程概况"],
        generation_mode="quality_200",
        dry_run=False,
        generate_images=False,
        provider="openai",
        model="gpt-5.4",
    )

    monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "main-secret")

    with patch.object(ws, "WORKSPACE_ROOT", tmp_path / "workspaces"), \
         patch("backend.app.routers.actions_bridge._run_background_housekeeping", return_value=None), \
         patch("backend.app.routers.actions_bridge._spawn_generate_worker", side_effect=RuntimeError("spawn boom")), \
         patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(HTTPException) as exc:
            await actions_generate_async(req, session_id="worker-spawn", x_actions_key="test-actions-key")

    assert exc.value.status_code == 500
    detail = exc.value.detail
    assert detail["code"] == "worker_spawn_failed"
    assert detail["stage"] == "worker_spawn"
    assert detail["job_id"]
    assert detail["trace_id"]
    assert detail["log_anchor"].startswith("actions.worker_spawn.")


@pytest.mark.asyncio
async def test_actions_download_returns_structured_artifact_not_found(tmp_path):
    from backend.app.routers.actions_bridge import actions_download
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="download-missing"))
        job_id = job_store.create_job(
            {
                "topic": "download-missing",
                "workspace_dir": workspace_dir,
                "request_id": "req-download-missing",
                "trace_id": "trace-download-missing",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"docx": [str(tmp_path / "missing.docx")]},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_download(
                job_id=job_id,
                kind="docx",
                variant=1,
                session_id="download-missing",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 404
    detail = exc.value.detail
    assert detail["code"] == "artifact_not_found"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-download-missing"
    assert detail["trace_id"] == "trace-download-missing"
    assert detail["log_anchor"].startswith("actions.download.")
    assert detail["extra"]["kind"] == "docx"
    assert detail["extra"]["download_index"]["docx"]["exists"] is False
    assert detail["extra"]["download_index"]["result_bundle_json"]["filename"].endswith("_result_bundle.json")


@pytest.mark.asyncio
async def test_actions_download_returns_structured_job_not_done(tmp_path):
    from backend.app.routers.actions_bridge import actions_download
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="download-pending"))
        job_id = job_store.create_job(
            {
                "topic": "download-pending",
                "workspace_dir": workspace_dir,
                "request_id": "req-download-pending",
                "trace_id": "trace-download-pending",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="running",
        )

        with pytest.raises(HTTPException) as exc:
            await actions_download(
                job_id=job_id,
                kind="docx",
                variant=1,
                session_id="download-pending",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert detail["code"] == "job_not_done"
    assert detail["job_id"] == job_id
    assert detail["request_id"] == "req-download-pending"
    assert detail["trace_id"] == "trace-download-pending"
    assert detail["extra"] == {"status": "running", "kind": "docx", "variant": 1}


@pytest.mark.asyncio
async def test_actions_download_rejects_invalid_artifact_kind(tmp_path):
    from backend.app.routers.actions_bridge import actions_download
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="download-invalid-kind"))
        json_path = tmp_path / "result.json"
        json_path.write_text(json.dumps({"variants": []}, ensure_ascii=False), encoding="utf-8")
        job_id = job_store.create_job(
            {
                "topic": "download-invalid-kind",
                "workspace_dir": workspace_dir,
                "request_id": "req-download-invalid-kind",
                "trace_id": "trace-download-invalid-kind",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(json_path)},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_download(
                job_id=job_id,
                kind="pdf",
                variant=1,
                session_id="download-invalid-kind",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert detail["code"] == "invalid_artifact_kind"
    assert detail["request_id"] == "req-download-invalid-kind"
    assert detail["trace_id"] == "trace-download-invalid-kind"
    assert "result_bundle_json" in detail["extra"]["allowed_kinds"]


@pytest.mark.asyncio
async def test_actions_download_supports_result_bundle_json(tmp_path):
    from backend.app.routers.actions_bridge import actions_download
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.run_contract import build_result_bundle

    workspaces = tmp_path / "workspaces"
    resource_events: list[dict] = []

    def fake_append_resource_event(event: str, **fields):
        resource_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), patch("backend.app.routers.actions_bridge.append_resource_event", side_effect=fake_append_resource_event):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="download-bundle"))
        docx_path = tmp_path / "bundle-result.docx"
        docx_path.write_bytes(b"docx")
        bundle_path = tmp_path / "bundle-result.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-bundle",
                    payload={"topic": "bundle-download", "project_id": "bundle-case"},
                    outputs={"docx": [str(docx_path)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 0},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "download-bundle",
                "workspace_dir": workspace_dir,
                "request_id": "req-download-bundle",
                "trace_id": "trace-download-bundle",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"result_bundle_json": str(bundle_path), "docx": [str(docx_path)]},
        )

        response = await actions_download(
            job_id=job_id,
            kind="result_bundle_json",
            variant=1,
            session_id="download-bundle",
            x_actions_key="test-actions-key",
        )

    assert isinstance(response, FileResponse)
    assert response.path == str(bundle_path)
    assert response.media_type == "application/json"
    assert "result_bundle" in str(response.filename)
    assert resource_events[-1]["event"] == "artifact_download"
    assert resource_events[-1]["job_id"] == job_id
    assert resource_events[-1]["kind"] == "result_bundle_json"
    assert resource_events[-1]["variant"] == 1
    assert resource_events[-1]["file_path"] == str(bundle_path)
    assert resource_events[-1]["file_size_bytes"] == bundle_path.stat().st_size
    assert resource_events[-1]["project_id"] is None
    assert resource_events[-1]["topic"] == "download-bundle"
    assert resource_events[-1]["request_id"] == "req-download-bundle"
    assert resource_events[-1]["trace_id"] == "trace-download-bundle"


@pytest.mark.asyncio
async def test_search_kg_api_returns_structured_kg_not_active(tmp_path):
    from backend.app.routers.zhifei_autoplan import search_kg_api
    from backend.zhifei_autoplan import workspace as ws

    with patch.object(ws, "WORKSPACE_ROOT", tmp_path / "workspaces"):
        with pytest.raises(HTTPException) as exc:
            await search_kg_api("混凝土", top_k=3, session_id="kg-empty")

    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert detail["code"] == "kg_not_active"
    assert detail["stage"] == "kg_search"
    assert detail["log_anchor"].startswith("autoplan.kg_search.")


@pytest.mark.asyncio
async def test_actions_result_exposes_generation_mode_summary_and_logic_template(tmp_path):
    from backend.app.routers.actions_bridge import actions_result
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan.run_contract import build_result_bundle
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="result-mode"))
        docx_path = tmp_path / "result-mode.docx"
        docx_path.write_bytes(b"docx")
        bundle_path = tmp_path / "result-mode-bundle.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-result-mode",
                    payload={"topic": "稳定交付模式探针", "project_id": "result-mode-case"},
                    outputs={"docx": [str(docx_path)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 0},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result_json = tmp_path / "result.json"
        result_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "topic": "稳定交付模式探针",
                            "outline": ["工程概况"],
                            "quality_checks": {},
                            "logic_template_id": "A",
                            "logic_template_name": "交付清单驱动",
                            "generation_mode": "stable_delivery",
                            "mode_policy": {
                                "profile": "stable_delivery",
                                "mode_effective": "stable_delivery",
                                "stable_output": True,
                                "deterministic_variant_forced": True,
                                "deterministic_logic_template_id": "A",
                            },
                            "generation_trace": {
                                "generation_mode": "stable_delivery",
                                "mode_effective": "stable_delivery",
                                "stable_output": True,
                                "deterministic_variant_forced": True,
                                "deterministic_logic_template_id": "A",
                            },
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "稳定交付模式探针",
                "workspace_dir": workspace_dir,
                "request_id": "req-result-mode",
                "trace_id": "trace-result-mode",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={
                "json": str(result_json),
                "docx": [str(docx_path)],
                "result_bundle_json": str(bundle_path),
                "blocking_issue_summary": {
                    "has_blocking_issues": True,
                    "blocking_issue_count": 1,
                    "failed_gate_metric_count": 1,
                    "failed_gate_metrics": ["engineering_ok_rate"],
                    "top_blocking_issues": [
                        {
                            "title": "施工部署",
                            "type": "engineering_gap",
                            "severity": "high",
                            "problem": "缺少责任人与验收记录",
                            "suggestion": "补齐责任/频次/记录",
                        }
                    ],
                },
                "blocking_issue_summary_by_variant": {
                    "1": {
                        "has_blocking_issues": True,
                        "blocking_issue_count": 1,
                        "failed_gate_metric_count": 1,
                        "failed_gate_metrics": ["engineering_ok_rate"],
                        "top_blocking_issues": [
                            {
                                "title": "施工部署",
                                "type": "engineering_gap",
                                "severity": "high",
                                "problem": "缺少责任人与验收记录",
                                "suggestion": "补齐责任/频次/记录",
                            }
                        ],
                    }
                },
            },
        )

        response = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="result-mode",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert response["variant_id"] == 1
    assert response["logic_template_id"] == "A"
    assert response["logic_template_name"] == "交付清单驱动"
    assert response["generation_mode_summary"]["profile"] == "stable_delivery"
    assert response["generation_mode_summary"]["mode_effective"] == "stable_delivery"
    assert response["generation_mode_summary"]["stable_output"] is True
    assert response["generation_mode_summary"]["deterministic_variant_forced"] is True
    assert response["generation_mode_summary"]["deterministic_logic_template_id"] == "A"
    assert response["result_bundle_summary"]["path"] == str(bundle_path)
    assert response["result_bundle_summary"]["complete"] is True
    assert response["result_bundle_request"]["project_id"] == "result-mode-case"
    assert response["result_bundle_request"]["topic"] == "稳定交付模式探针"
    assert response["result_bundle_artifact_count"] == 1
    assert response["result_bundle_artifacts"][0]["kind"] == "docx"
    assert response["result_bundle_artifacts"][0]["exists"] is True
    assert response["files"]["result_bundle_json"] == str(bundle_path)
    assert response["download_index"]["docx"]["exists"] is True
    assert response["download_index"]["result_bundle_json"]["filename"].endswith("_result_bundle.json")
    assert response["has_blocking_issues"] is True
    assert response["blocking_issue_count"] == 1
    assert response["top_blocking_issue_type"] == "engineering_gap"


@pytest.mark.asyncio
async def test_actions_job_status_exposes_generation_mode_summary_and_logic_template(tmp_path):
    from backend.app.routers.actions_bridge import actions_job_status
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="status-mode"))
        result_json = tmp_path / "status-result.json"
        result_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "topic": "稳定交付模式状态探针",
                            "outline": ["工程概况"],
                            "quality_checks": {},
                            "logic_template_id": "A",
                            "logic_template_name": "交付清单驱动",
                            "generation_mode": "stable_delivery",
                            "mode_policy": {
                                "profile": "stable_delivery",
                                "mode_effective": "stable_delivery",
                                "stable_output": True,
                                "deterministic_variant_forced": True,
                                "deterministic_logic_template_id": "A",
                            },
                            "generation_trace": {
                                "generation_mode": "stable_delivery",
                                "mode_effective": "stable_delivery",
                                "stable_output": True,
                                "deterministic_variant_forced": True,
                                "deterministic_logic_template_id": "A",
                            },
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "稳定交付模式状态探针",
                "workspace_dir": workspace_dir,
                "request_id": "req-status-mode",
                "trace_id": "trace-status-mode",
                "generation_mode": "stable_delivery",
                "logic_template_id": "A",
                "_mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(result_json)},
        )

        response = await actions_job_status(
            job_id=job_id,
            session_id="status-mode",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    job = response["job"]
    assert job["status"] == "done"
    assert job["logic_template_id"] == "A"
    assert job["logic_template_name"] == "交付清单驱动"
    assert job["generation_mode_summary"]["profile"] == "stable_delivery"
    assert job["generation_mode_summary"]["mode_effective"] == "stable_delivery"
    assert job["generation_mode_summary"]["stable_output"] is True
    assert job["generation_mode_summary"]["deterministic_variant_forced"] is True
    assert job["generation_mode_summary"]["deterministic_logic_template_id"] == "A"


async def test_actions_job_status_uses_persisted_result_metadata_without_json(tmp_path):
    from backend.app.routers.actions_bridge import actions_job_status
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan.run_contract import build_result_bundle
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="status-result-metadata"))
        docx_path = tmp_path / "status-result-metadata.docx"
        docx_path.write_bytes(b"docx")
        bundle_path = tmp_path / "status-result-bundle.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-status-result-metadata",
                    payload={"topic": "稳定交付模式状态探针", "project_id": "status-result-metadata-case"},
                    outputs={"docx": [str(docx_path)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 0},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "稳定交付模式状态探针",
                "workspace_dir": workspace_dir,
                "request_id": "req-status-result-metadata",
                "trace_id": "trace-status-result-metadata",
                "generation_mode": "stable_delivery",
                "logic_template_id": "A",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={
                "docx": str(docx_path),
                "result_bundle_json": str(bundle_path),
                "resource_usage_summary": {"call_count": 0},
                "generation_mode_summary": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
                "logic_template_id": "A",
                "logic_template_name": "交付清单驱动",
                "runtime_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "variant_id": 1,
                        "generation_mode": "stable_delivery",
                        "mode_effective": "stable_delivery",
                        "section_count": 5,
                        "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
                    }
                },
                "quality_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "variant_id": 1,
                        "logic_template_id": "A",
                        "logic_template_name": "交付清单驱动",
                        "quality_score": 98,
                        "quality_gate_ok": True,
                        "quality_gate_failed_count": 0,
                        "blocking_issue_summary": {
                            "has_blocking_issues": True,
                            "blocking_issue_count": 1,
                            "failed_gate_metric_count": 0,
                            "failed_gate_metrics": [],
                            "top_blocking_issues": [
                                {
                                    "title": "施工部署",
                                    "type": "engineering_gap",
                                    "severity": "high",
                                    "problem": "缺少责任人与验收记录",
                                    "suggestion": "补齐责任/频次/记录",
                                }
                            ],
                        },
                    }
                },
                "blocking_issue_summary": {
                    "has_blocking_issues": True,
                    "blocking_issue_count": 1,
                    "failed_gate_metric_count": 0,
                    "failed_gate_metrics": [],
                    "top_blocking_issues": [
                        {
                            "title": "施工部署",
                            "type": "engineering_gap",
                            "severity": "high",
                            "problem": "缺少责任人与验收记录",
                            "suggestion": "补齐责任/频次/记录",
                        }
                    ],
                },
                "blocking_issue_summary_by_variant": {
                    "1": {
                        "has_blocking_issues": True,
                        "blocking_issue_count": 1,
                        "failed_gate_metric_count": 0,
                        "failed_gate_metrics": [],
                        "top_blocking_issues": [
                            {
                                "title": "施工部署",
                                "type": "engineering_gap",
                                "severity": "high",
                                "problem": "缺少责任人与验收记录",
                                "suggestion": "补齐责任/频次/记录",
                            }
                        ],
                    }
                },
            },
        )

        response = await actions_job_status(
            job_id=job_id,
            session_id="status-result-metadata",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    job = response["job"]
    assert job["status"] == "done"
    assert job["logic_template_id"] == "A"
    assert job["logic_template_name"] == "交付清单驱动"
    assert job["variants"] == 1
    assert job["quality_ok"] == [True]
    assert job["generation_mode_summary"]["profile"] == "stable_delivery"
    assert job["generation_mode_summary"]["mode_effective"] == "stable_delivery"
    assert job["generation_mode_summary"]["stable_output"] is True
    assert job["generation_mode_summary"]["deterministic_variant_forced"] is True
    assert job["generation_mode_summary"]["deterministic_logic_template_id"] == "A"
    assert job["runtime_by_variant"]["1"]["pipeline_stages"][0]["stage"] == "draft_generation"
    assert job["quality_by_variant"]["1"]["quality_score"] == 98
    assert job["result_bundle_json"] == str(bundle_path)
    assert job["result_bundle_available"] is True
    assert job["result_bundle_loaded"] is True
    assert job["result_bundle_complete"] is True
    assert job["result_bundle_summary"]["schema_version"] == "actions-result-bundle-v1"
    assert job["download_index"]["docx"]["exists"] is True
    assert job["download_index"]["result_bundle_json"]["exists"] is True
    assert job["download_ready_count"] == 2
    assert job["download_ready_kinds"] == ["docx", "result_bundle_json"]
    assert job["primary_download_kind"] == "docx"
    assert job["blocking_issue_summary"]["has_blocking_issues"] is True
    assert job["has_blocking_issues"] is True
    assert job["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert job["blocking_issue_count"] == 1
    assert job["failed_gate_metric_count"] == 0
    assert job["top_blocking_issue_type"] == "engineering_gap"
    assert job["blocking_issue_summary_by_variant"]["1"]["top_blocking_issues"][0]["type"] == "engineering_gap"


@pytest.mark.asyncio
async def test_actions_jobs_recent_exposes_persisted_generation_and_quality_metadata(tmp_path):
    from backend.app.routers.actions_bridge import actions_jobs_recent
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan.run_contract import build_result_bundle
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="recent-metadata"))
        docx_path = tmp_path / "recent-result.docx"
        docx_path.write_bytes(b"docx")
        bundle_path = tmp_path / "recent-result-bundle.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-recent-metadata",
                    payload={"topic": "稳定交付最近任务探针", "project_id": "recent-metadata-case"},
                    outputs={"docx": [str(docx_path)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 0},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "稳定交付最近任务探针",
                "workspace_dir": workspace_dir,
                "project_id": "recent-metadata-case",
                "project_type": "房建",
                "generation_mode": "stable_delivery",
                "logic_template_id": "A",
                "_mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={
                "docx": str(docx_path),
                "result_bundle_json": str(bundle_path),
                "generation_mode_summary": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
                "quality_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "variant_id": 1,
                        "logic_template_id": "A",
                        "logic_template_name": "交付清单驱动",
                        "quality_score": 98,
                        "quality_gate_ok": False,
                        "quality_gate_failed_count": 1,
                        "blocking_issue_summary": {
                            "has_blocking_issues": True,
                            "blocking_issue_count": 1,
                            "failed_gate_metric_count": 1,
                            "failed_gate_metrics": ["engineering_ok_rate"],
                            "top_blocking_issues": [
                                {
                                    "title": "施工部署",
                                    "type": "engineering_gap",
                                    "severity": "high",
                                    "problem": "缺少责任人与验收记录",
                                    "suggestion": "补齐责任/频次/记录",
                                }
                            ],
                        },
                    }
                },
                "blocking_issue_summary": {
                    "has_blocking_issues": True,
                    "blocking_issue_count": 1,
                    "failed_gate_metric_count": 1,
                    "failed_gate_metrics": ["engineering_ok_rate"],
                    "top_blocking_issues": [
                        {
                            "title": "施工部署",
                            "type": "engineering_gap",
                            "severity": "high",
                            "problem": "缺少责任人与验收记录",
                            "suggestion": "补齐责任/频次/记录",
                        }
                    ],
                },
            },
        )

        response = await actions_jobs_recent(
            limit=8,
            statuses="done",
            max_age_hours=24,
            session_id="recent-metadata",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    item = response["items"][0]
    assert item["job_id"] == job_id
    assert item["generation_mode"] == "stable_delivery"
    assert item["mode_effective"] == "stable_delivery"
    assert item["generation_mode_summary"]["profile"] == "stable_delivery"
    assert item["generation_mode_summary"]["stable_output"] is True
    assert item["logic_template_id"] == "A"
    assert item["logic_template_name"] == "交付清单驱动"
    assert item["quality_score"] == 98
    assert item["quality_gate_ok"] is False
    assert item["quality_gate_failed_count"] == 1
    assert item["result_bundle_json"] == str(bundle_path)
    assert item["result_bundle_available"] is True
    assert item["result_bundle_loaded"] is True
    assert item["result_bundle_complete"] is True
    assert item["result_bundle_schema_version"] == "actions-result-bundle-v1"
    assert item["download_ready_count"] == 2
    assert item["download_ready_kinds"] == ["docx", "result_bundle_json"]
    assert item["primary_download_kind"] == "docx"
    assert item["has_blocking_issues"] is True
    assert item["blocking_issue_count"] == 1
    assert item["failed_gate_metric_count"] == 1
    assert item["top_blocking_issue_type"] == "engineering_gap"
    assert item["blocking_issue_summary"]["failed_gate_metrics"] == ["engineering_ok_rate"]
