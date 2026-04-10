from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks, HTTPException


def test_evaluate_job_admission_counts_user_jobs_across_workspaces(tmp_path: Path):
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.job_admission import evaluate_job_admission

    root = tmp_path / "workspaces"
    legacy_jobs = tmp_path / "legacy-jobs"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.object(job_store, "JOB_DIR", legacy_jobs), patch.dict(
        os.environ,
        {
            "ZF_USER_RUNNING_JOB_LIMIT": "2",
            "ZF_USER_QUEUED_JOB_LIMIT": "2",
            "ZF_USER_ACTIVE_JOB_LIMIT": "2",
        },
        clear=False,
    ):
        workspace_a = str(ws.resolve_workspace_dir(session_id="user-7-a"))
        workspace_b = str(ws.resolve_workspace_dir(session_id="user-7-b"))
        job_a = job_store.create_job({"topic": "A", "workspace_dir": workspace_a}, user_id=7, workspace_dir=workspace_a)
        job_store.update_job(job_a, workspace_dir=workspace_a, status="running")
        job_b = job_store.create_job({"topic": "B", "workspace_dir": workspace_b}, user_id=7, workspace_dir=workspace_b)
        job_store.update_job(job_b, workspace_dir=workspace_b, status="queued")

        decision = evaluate_job_admission(
            scope="user",
            tenant_id="user-7",
            workspace_dir=workspace_b,
            user_id=7,
            requested_jobs=1,
        )

    assert decision["allowed"] is False
    assert decision["code"] == "user_active_capacity_exceeded"
    assert decision["usage"]["running_count"] == 1
    assert decision["usage"]["queued_count"] == 1
    assert decision["usage"]["workspace_count"] == 2


def test_evaluate_job_admission_includes_usage_profile_and_soft_warning(tmp_path: Path):
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.job_admission import evaluate_job_admission
    from backend.zhifei_autoplan.resource_audit import append_resource_event

    root = tmp_path / "workspaces"
    legacy_jobs = tmp_path / "legacy-jobs"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.object(job_store, "JOB_DIR", legacy_jobs), patch.dict(
        os.environ,
        {
            "ZF_SESSION_RUNNING_JOB_LIMIT": "3",
            "ZF_SESSION_QUEUED_JOB_LIMIT": "5",
            "ZF_SESSION_ACTIVE_JOB_LIMIT": "5",
            "ZF_SESSION_WARNING_RATIO": "0.8",
            "ZF_SESSION_TOKENS_LAST_HOUR_WARNING": "100",
        },
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-soft"))
        job_id = job_store.create_job({"topic": "A", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="running")
        append_resource_event(
            "llm_section_generation",
            workspace_dir=workspace_dir,
            session_id="sess-soft",
            token_usage={"input_tokens": 60, "output_tokens": 30, "total_tokens": 90},
            latency_ms=320,
            provider="openai",
            model="gpt-5.4",
        )

        decision = evaluate_job_admission(
            scope="session",
            tenant_id="sess-soft",
            workspace_dir=workspace_dir,
            requested_jobs=3,
        )

    assert decision["allowed"] is True
    assert decision["warning_level"] in {"notice", "warning"}
    assert decision["usage"]["usage_profile"]["windows"]["last_hour"]["total_tokens_total"] == 90
    warning_codes = {item["code"] for item in decision["warnings"]}
    assert "session_active_capacity_near_limit" in warning_codes
    assert "session_tokens_last_hour_near_limit" in warning_codes


def test_recommend_admission_degrade_reduces_parallelism_on_soft_warning(tmp_path: Path):
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.job_admission import apply_admission_degrade, evaluate_job_admission

    root = tmp_path / "workspaces"
    legacy_jobs = tmp_path / "legacy-jobs"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.object(job_store, "JOB_DIR", legacy_jobs), patch.dict(
        os.environ,
        {
            "ZF_SESSION_RUNNING_JOB_LIMIT": "3",
            "ZF_SESSION_QUEUED_JOB_LIMIT": "2",
            "ZF_SESSION_ACTIVE_JOB_LIMIT": "3",
            "ZF_SESSION_WARNING_RATIO": "0.8",
        },
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-degrade"))
        job_id = job_store.create_job({"topic": "A", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="queued")
        payload = {
            "topic": "软降级测试",
            "workspace_dir": workspace_dir,
            "agent_parallelism": 8,
            "variant_parallelism": 3,
            "generate_images": True,
            "compare_max_chars": 1600,
        }
        decision = evaluate_job_admission(
            scope="session",
            tenant_id="sess-degrade",
            workspace_dir=workspace_dir,
            requested_jobs=1,
        )
        degrade_plan = apply_admission_degrade(payload, decision)

    assert decision["allowed"] is True
    assert degrade_plan["applied"] is True
    assert degrade_plan["agent_parallelism_before"] == 8
    assert degrade_plan["agent_parallelism_after"] < 8
    assert degrade_plan["variant_parallelism_before"] == 3
    assert degrade_plan["variant_parallelism_after"] == 1
    assert degrade_plan["generate_images_before"] is True
    assert degrade_plan["generate_images_after"] is False
    assert degrade_plan["compare_max_chars_before"] == 1600
    assert degrade_plan["compare_max_chars_after"] == 800
    assert degrade_plan["text_chain_profile_before"] == "default"
    assert degrade_plan["text_chain_profile_after"] == "cost_guard"
    assert payload["agent_parallelism"] == degrade_plan["agent_parallelism_after"]
    assert payload["variant_parallelism"] == 1
    assert payload["generate_images"] is False
    assert payload["compare_max_chars"] == 800
    assert payload["text_chain_profile"] == "cost_guard"
    assert payload["_admission_degrade_plan"]["applied"] is True


@pytest.mark.asyncio
async def test_actions_generate_async_rejects_when_session_running_limit_hit(tmp_path: Path):
    from backend.app.routers.actions_bridge import ActionsGenerateRequest, actions_generate_async
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    audit_events: list[dict] = []

    def fake_append_resource_event(event: str, **fields):
        audit_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(
        os.environ,
        {
            "ZF_ACTIONS_KEY": "test-actions-key",
            "ZF_SESSION_RUNNING_JOB_LIMIT": "1",
            "ZF_SESSION_QUEUED_JOB_LIMIT": "2",
            "ZF_SESSION_ACTIVE_JOB_LIMIT": "3",
        },
        clear=False,
    ), patch("backend.app.routers.actions_bridge._run_background_housekeeping", return_value=None), patch(
        "backend.app.routers.actions_bridge.apply_server_provider_routing",
        side_effect=lambda payload: payload,
    ), patch(
        "backend.app.routers.actions_bridge.append_resource_event",
        side_effect=fake_append_resource_event,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-limit"))
        job_id = job_store.create_job({"topic": "已占用", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="running")

        req = ActionsGenerateRequest(
            topic="并发保护测试",
            project_id="limit-check",
            outline=["工程概况"],
            generation_mode="quality_200",
            dry_run=True,
            generate_images=False,
        )

        with pytest.raises(HTTPException) as exc:
            await actions_generate_async(
                req,
                session_id="sess-limit",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "session_running_capacity_exceeded"
    assert exc.value.detail["next_action"] == "wait_for_running_jobs"
    assert audit_events[-1]["event"] == "job_rejected"
    assert audit_events[-1]["rejection_code"] == "session_running_capacity_exceeded"


@pytest.mark.asyncio
async def test_actions_generate_async_applies_degrade_plan_when_session_near_limit(tmp_path: Path):
    from backend.app.routers.actions_bridge import ActionsGenerateRequest, actions_generate_async
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    worker_log = tmp_path / "worker.log"
    audit_events: list[dict] = []

    def fake_append_resource_event(event: str, **fields):
        audit_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(
        os.environ,
        {
            "ZF_ACTIONS_KEY": "test-actions-key",
            "ZF_SESSION_RUNNING_JOB_LIMIT": "3",
            "ZF_SESSION_QUEUED_JOB_LIMIT": "2",
            "ZF_SESSION_ACTIVE_JOB_LIMIT": "3",
            "ZF_SESSION_WARNING_RATIO": "0.8",
        },
        clear=False,
    ), patch("backend.app.routers.actions_bridge._spawn_generate_worker", return_value=(99999, str(worker_log))), patch(
        "backend.app.routers.actions_bridge._run_background_housekeeping",
        return_value=None,
    ), patch(
        "backend.app.routers.actions_bridge.append_resource_event",
        side_effect=fake_append_resource_event,
    ), patch(
        "backend.app.routers.actions_bridge.apply_server_provider_routing",
        side_effect=lambda payload: payload,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-near-limit"))
        job_id = job_store.create_job({"topic": "已排队", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="queued")

        req = ActionsGenerateRequest(
            topic="软降级",
            project_id="degrade-check",
            outline=["工程概况"],
            generation_mode="hq_speed_500",
            dry_run=True,
            generate_images=True,
            agent_parallelism=8,
            variant_parallelism=3,
            compare_max_chars=1600,
        )
        out = await actions_generate_async(
            req,
            session_id="sess-near-limit",
            workspace_dir=workspace_dir,
            x_actions_key="test-actions-key",
        )
        stored = job_store.get_job(out["job_id"], workspace_dir=workspace_dir)

    assert out["ok"] is True
    assert out["admission"]["warning_level"] in {"notice", "warning"}
    assert out["admission"]["degrade_plan"]["applied"] is True
    assert out["admission"]["degrade_plan"]["agent_parallelism_before"] == 8
    assert out["admission"]["degrade_plan"]["variant_parallelism_before"] == 3
    assert out["admission"]["degrade_plan"]["variant_parallelism_after"] == 1
    assert out["admission"]["degrade_plan"]["generate_images_before"] is True
    assert out["admission"]["degrade_plan"]["generate_images_after"] is False
    assert out["admission"]["degrade_plan"]["compare_max_chars_before"] == 1600
    assert out["admission"]["degrade_plan"]["compare_max_chars_after"] == 800
    assert out["admission"]["degrade_plan"]["text_chain_profile_before"] == "default"
    assert out["admission"]["degrade_plan"]["text_chain_profile_after"] == "cost_guard"
    assert stored["payload"]["agent_parallelism"] == out["admission"]["degrade_plan"]["agent_parallelism_after"]
    assert stored["payload"]["variant_parallelism"] == 1
    assert stored["payload"]["generate_images"] is False
    assert stored["payload"]["compare_max_chars"] == 800
    assert stored["payload"]["text_chain_profile"] == "cost_guard"
    assert stored["payload"]["_admission_degrade_plan"]["applied"] is True
    assert audit_events[-1]["event"] == "job_queued"
    assert audit_events[-1]["degrade_plan"]["applied"] is True


@pytest.mark.asyncio
async def test_actions_usage_status_returns_usage_profile(tmp_path: Path):
    from backend.app.routers.actions_bridge import actions_usage_status
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.resource_audit import append_resource_event

    root = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-usage"))
        append_resource_event(
            "job_queued",
            workspace_dir=workspace_dir,
            session_id="sess-usage",
        )
        append_resource_event(
            "llm_section_generation",
            workspace_dir=workspace_dir,
            session_id="sess-usage",
            token_usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            latency_ms=120,
            provider="openai",
            model="gpt-5.4",
        )
        out = await actions_usage_status(
            requested_jobs=0,
            session_id="sess-usage",
            workspace_dir=workspace_dir,
            x_actions_key="test-actions-key",
        )

    assert out["ok"] is True
    assert out["admission"]["requested_jobs"] == 0
    assert out["admission"]["usage"]["usage_profile"]["windows"]["last_hour"]["queued_jobs"] == 1
    assert out["admission"]["usage"]["usage_profile"]["windows"]["last_hour"]["total_tokens_total"] == 15
    assert str(out["admission"]["limits"].get("config_version") or "").strip()
    assert str(out["admission"]["limits"].get("policy_source") or "").strip()


@pytest.mark.asyncio
async def test_actions_usage_report_returns_usage_profile(tmp_path: Path):
    from backend.app.routers.actions_bridge import actions_usage_report
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.resource_audit import append_resource_event

    root = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-report"))
        append_resource_event(
            "llm_section_generation",
            workspace_dir=workspace_dir,
            session_id="sess-report",
            token_usage={"input_tokens": 11, "output_tokens": 4, "total_tokens": 15},
            latency_ms=88,
            provider="openai",
            model="gpt-5.4",
        )
        out = await actions_usage_report(
            session_id="sess-report",
            workspace_dir=workspace_dir,
            x_actions_key="test-actions-key",
        )

    assert out["ok"] is True
    assert out["scope"] == "session"
    assert out["usage_profile"]["windows"]["last_hour"]["total_tokens_total"] == 15
    assert str(out["limits"].get("config_version") or "").strip()
    assert str(out["limits"].get("policy_source") or "").strip()


@pytest.mark.asyncio
async def test_generate_plan_async_rejects_before_charge_when_user_limit_hit(tmp_path: Path):
    from backend.app.routers.zhifei_autoplan import GenerateRequest, generate_plan_async
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    charge_calls: list[tuple] = []
    audit_calls: list[dict] = []
    resource_events: list[dict] = []

    def fake_charge(*args, **kwargs):
        charge_calls.append((args, kwargs))

    def fake_audit(action: str, user_id=None, detail=None, **kwargs):
        audit_calls.append({"action": action, "user_id": user_id, "detail": detail or {}, **kwargs})

    def fake_append_resource_event(event: str, **fields):
        resource_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    user = {"id": 7, "balance": 99, "daily_limit": 50}

    legacy_jobs = tmp_path / "legacy-jobs"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.object(job_store, "JOB_DIR", legacy_jobs), patch.dict(
        os.environ,
        {
            "ZF_USER_RUNNING_JOB_LIMIT": "1",
            "ZF_USER_QUEUED_JOB_LIMIT": "2",
            "ZF_USER_ACTIVE_JOB_LIMIT": "3",
        },
        clear=False,
    ), patch("backend.app.routers.zhifei_autoplan._auth_user", return_value=user), patch(
        "backend.app.routers.zhifei_autoplan._charge",
        side_effect=fake_charge,
    ), patch(
        "backend.app.routers.zhifei_autoplan._audit",
        side_effect=fake_audit,
    ), patch(
        "backend.app.routers.zhifei_autoplan.append_resource_event",
        side_effect=fake_append_resource_event,
    ):
        existing_workspace = str(ws.resolve_workspace_dir(session_id="existing-session"))
        new_workspace = str(ws.resolve_workspace_dir(session_id="new-session"))
        existing_job = job_store.create_job(
            {"topic": "已有任务", "workspace_dir": existing_workspace},
            user_id=7,
            workspace_dir=existing_workspace,
        )
        job_store.update_job(existing_job, workspace_dir=existing_workspace, status="running")

        req = GenerateRequest(topic="用户并发保护", outline=["工程概况"], dry_run=True, generate_images=False)
        with pytest.raises(HTTPException) as exc:
            await generate_plan_async(
                req,
                background_tasks=BackgroundTasks(),
                session_id="new-session",
                workspace_dir=new_workspace,
                authorization="Bearer mock-token",
            )

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "user_running_capacity_exceeded"
    assert charge_calls == []
    assert audit_calls[-1]["action"] == "generate_async_rejected"
    assert resource_events[-1]["event"] == "job_rejected"
    assert resource_events[-1]["rejection_scope"] == "user"


@pytest.mark.asyncio
async def test_generate_plan_async_applies_degrade_plan_when_user_near_limit(tmp_path: Path):
    from backend.app.routers.zhifei_autoplan import GenerateRequest, generate_plan_async
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    charge_calls: list[tuple] = []
    audit_calls: list[dict] = []
    resource_events: list[dict] = []
    user = {"id": 8, "balance": 99, "daily_limit": 50}
    worker_log = tmp_path / "worker.log"

    def fake_charge(*args, **kwargs):
        charge_calls.append((args, kwargs))

    def fake_audit(action: str, user_id=None, detail=None, **kwargs):
        audit_calls.append({"action": action, "user_id": user_id, "detail": detail or {}, **kwargs})

    def fake_append_resource_event(event: str, **fields):
        resource_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    legacy_jobs = tmp_path / "legacy-jobs"
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.object(job_store, "JOB_DIR", legacy_jobs), patch.dict(
        os.environ,
        {
            "ZF_USER_RUNNING_JOB_LIMIT": "3",
            "ZF_USER_QUEUED_JOB_LIMIT": "2",
            "ZF_USER_ACTIVE_JOB_LIMIT": "3",
            "ZF_USER_WARNING_RATIO": "0.8",
        },
        clear=False,
    ), patch("backend.app.routers.zhifei_autoplan._auth_user", return_value=user), patch(
        "backend.app.routers.zhifei_autoplan._charge",
        side_effect=fake_charge,
    ), patch(
        "backend.app.routers.zhifei_autoplan._audit",
        side_effect=fake_audit,
    ), patch(
        "backend.app.routers.zhifei_autoplan.append_resource_event",
        side_effect=fake_append_resource_event,
    ), patch(
        "backend.app.routers.zhifei_autoplan.apply_server_provider_routing",
        side_effect=lambda payload: payload,
    ):
        existing_workspace = str(ws.resolve_workspace_dir(session_id="existing-user-soft"))
        new_workspace = str(ws.resolve_workspace_dir(session_id="new-user-soft"))
        existing_job = job_store.create_job(
            {"topic": "已有排队", "workspace_dir": existing_workspace},
            user_id=8,
            workspace_dir=existing_workspace,
        )
        job_store.update_job(existing_job, workspace_dir=existing_workspace, status="queued")

        req = GenerateRequest(
            topic="兼容链软降级",
            outline=["工程概况"],
            dry_run=True,
            generate_images=True,
            compare_max_chars=1600,
        )
        out = await generate_plan_async(
            req,
            background_tasks=BackgroundTasks(),
            session_id="new-user-soft",
            workspace_dir=new_workspace,
            authorization="Bearer mock-token",
        )
        stored = job_store.get_job(out["job_id"], workspace_dir=new_workspace)

    assert out["ok"] is True
    assert charge_calls != []
    assert out["admission"]["degrade_plan"]["applied"] is True
    assert out["admission"]["degrade_plan"]["agent_parallelism_before"] == 4
    assert out["admission"]["degrade_plan"]["agent_parallelism_after"] < 4
    assert out["admission"]["degrade_plan"]["generate_images_before"] is True
    assert out["admission"]["degrade_plan"]["generate_images_after"] is False
    assert out["admission"]["degrade_plan"]["compare_max_chars_before"] == 1600
    assert out["admission"]["degrade_plan"]["compare_max_chars_after"] == 800
    assert out["admission"]["degrade_plan"]["text_chain_profile_before"] == "default"
    assert out["admission"]["degrade_plan"]["text_chain_profile_after"] == "cost_guard"
    assert stored["payload"]["agent_parallelism"] == out["admission"]["degrade_plan"]["agent_parallelism_after"]
    assert stored["payload"]["generate_images"] is False
    assert stored["payload"]["compare_max_chars"] == 800
    assert stored["payload"]["text_chain_profile"] == "cost_guard"
    assert stored["payload"]["_admission_degrade_plan"]["applied"] is True
    assert audit_calls[-1]["action"] == "generate_async"
    assert audit_calls[-1]["detail"]["degrade_plan"]["applied"] is True
    assert resource_events[-1]["event"] == "job_queued"
    assert resource_events[-1]["degrade_plan"]["applied"] is True


@pytest.mark.asyncio
async def test_autoplan_usage_status_returns_user_usage_profile(tmp_path: Path):
    from backend.app.routers.zhifei_autoplan import usage_status
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.resource_audit import append_resource_event

    root = tmp_path / "workspaces"
    user = {"id": 9, "balance": 99, "daily_limit": 50}
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(os.environ, {}, clear=False), patch(
        "backend.app.routers.zhifei_autoplan._auth_user",
        return_value=user,
    ):
        workspace_a = str(ws.resolve_workspace_dir(session_id="user-9-a"))
        workspace_b = str(ws.resolve_workspace_dir(session_id="user-9-b"))
        append_resource_event(
            "llm_section_generation",
            workspace_dir=workspace_a,
            session_id="user-9-a",
            user_id=9,
            token_usage={"input_tokens": 20, "output_tokens": 8, "total_tokens": 28},
            latency_ms=200,
            provider="openai",
            model="gpt-5.4",
        )
        append_resource_event(
            "job_completed",
            workspace_dir=workspace_b,
            session_id="user-9-b",
            user_id=9,
        )
        out = await usage_status(
            requested_jobs=0,
            session_id="user-9-b",
            workspace_dir=workspace_b,
            authorization="Bearer mock-token",
        )

    assert out["ok"] is True
    assert out["admission"]["scope"] == "user"
    assert out["admission"]["requested_jobs"] == 0
    profile = out["admission"]["usage"]["usage_profile"]["windows"]["last_hour"]
    assert profile["total_tokens_total"] == 28
    assert profile["completed_jobs"] == 1


@pytest.mark.asyncio
async def test_autoplan_usage_report_returns_user_usage_profile(tmp_path: Path):
    from backend.app.routers.zhifei_autoplan import usage_report
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan.resource_audit import append_resource_event

    root = tmp_path / "workspaces"
    user = {"id": 9, "balance": 99, "daily_limit": 50}
    with patch.object(ws, "WORKSPACE_ROOT", root), patch.dict(os.environ, {}, clear=False), patch(
        "backend.app.routers.zhifei_autoplan._auth_user",
        return_value=user,
    ):
        workspace_a = str(ws.resolve_workspace_dir(session_id="user-9-r-a"))
        workspace_b = str(ws.resolve_workspace_dir(session_id="user-9-r-b"))
        append_resource_event(
            "llm_section_generation",
            workspace_dir=workspace_a,
            session_id="user-9-r-a",
            user_id=9,
            token_usage={"input_tokens": 12, "output_tokens": 6, "total_tokens": 18},
            latency_ms=120,
            provider="openai",
            model="gpt-5.4",
        )
        append_resource_event(
            "job_completed",
            workspace_dir=workspace_b,
            session_id="user-9-r-b",
            user_id=9,
        )
        out = await usage_report(
            session_id="user-9-r-b",
            workspace_dir=workspace_b,
            authorization="Bearer mock-token",
        )

    assert out["ok"] is True
    assert out["scope"] == "user"
    assert out["usage_profile"]["windows"]["last_hour"]["total_tokens_total"] == 18
    assert out["usage_profile"]["windows"]["last_hour"]["completed_jobs"] == 1
    assert str(out["limits"].get("config_version") or "").strip()
