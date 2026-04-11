from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException


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
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="result-mode"))
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
            result={"json": str(result_json)},
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
