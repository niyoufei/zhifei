from __future__ import annotations

import os
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_actions_job_cancel_returns_terminal_status_without_mutation(tmp_path):
    from backend.app.routers.actions_bridge import ActionsJobCancelRequest, actions_job_cancel
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="cancel-terminal"))
        job_id = job_store.create_job({"topic": "cancel-terminal", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(job_id, workspace_dir=workspace_dir, status="done")

        response = await actions_job_cancel(
            ActionsJobCancelRequest(job_id=job_id),
            session_id="cancel-terminal",
            x_actions_key="test-actions-key",
        )
        stored = job_store.get_job(job_id, workspace_dir=workspace_dir)

    assert response == {"ok": True, "job_id": job_id, "status": "done"}
    assert stored["status"] == "done"


@pytest.mark.asyncio
async def test_actions_job_cancel_marks_running_job_cancelled(tmp_path):
    from backend.app.routers.actions_bridge import ActionsJobCancelRequest, actions_job_cancel
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), patch("backend.app.routers.actions_bridge.os.kill", return_value=None) as kill_mock:
        workspace_dir = str(ws.resolve_workspace_dir(session_id="cancel-running"))
        job_id = job_store.create_job({"topic": "cancel-running", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="running",
            worker={"pid": 12345},
        )

        response = await actions_job_cancel(
            ActionsJobCancelRequest(job_id=job_id),
            session_id="cancel-running",
            x_actions_key="test-actions-key",
        )
        stored = job_store.get_job(job_id, workspace_dir=workspace_dir)

    kill_mock.assert_called_once_with(12345, 15)
    assert response == {"ok": True, "job_id": job_id, "status": "cancelled"}
    assert stored["status"] == "cancelled"
    assert stored["error"] == "cancelled_by_user"


@pytest.mark.asyncio
async def test_actions_job_cancel_still_cancels_when_kill_fails(tmp_path):
    from backend.app.routers.actions_bridge import ActionsJobCancelRequest, actions_job_cancel
    from backend.zhifei_autoplan import job_store
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), patch("backend.app.routers.actions_bridge.os.kill", side_effect=ProcessLookupError("gone")) as kill_mock:
        workspace_dir = str(ws.resolve_workspace_dir(session_id="cancel-kill-fail"))
        job_id = job_store.create_job({"topic": "cancel-kill-fail", "workspace_dir": workspace_dir}, workspace_dir=workspace_dir)
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="running",
            worker={"pid": 22222},
        )

        response = await actions_job_cancel(
            ActionsJobCancelRequest(job_id=job_id),
            session_id="cancel-kill-fail",
            x_actions_key="test-actions-key",
        )
        stored = job_store.get_job(job_id, workspace_dir=workspace_dir)

    kill_mock.assert_called_once_with(22222, 15)
    assert response == {"ok": True, "job_id": job_id, "status": "cancelled"}
    assert stored["status"] == "cancelled"
    assert stored["error"] == "cancelled_by_user"
