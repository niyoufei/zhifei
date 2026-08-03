from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_ACTIONS_EXPORT_DOCX_RUNTIME_BINDINGS = {
    "actions_bridge": ("backend.app.routers.actions_bridge", None),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_actions_export_docx_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _ACTIONS_EXPORT_DOCX_RUNTIME_BINDINGS,
    ):
        yield


@pytest.mark.asyncio
async def test_actions_export_docx_delegates_to_service():
    from backend.app.routers import actions_bridge

    seen: dict[str, object] = {}

    def _fake_execute_export_docx_request(*, raw_request, workspace_dir, save_outputs_fn):
        seen["raw_request"] = raw_request
        seen["workspace_dir"] = workspace_dir
        seen["save_outputs_fn"] = save_outputs_fn
        return {"ok": True, "job_id": "job-export-router", "files": {"json": "/tmp/router-export.json"}}

    req = actions_bridge.ActionsExportRequest(
        topic="router-export",
        sections=[actions_bridge.ActionsSection(title="工程概况", content="内容")],
        generate_images=False,
    )

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False), patch.object(
        actions_bridge.export_docx_core,
        "execute_export_docx_request",
        side_effect=_fake_execute_export_docx_request,
    ):
        response = await actions_bridge.actions_export_docx(
            req,
            workspace_dir="/tmp/router-export-workspace",
            x_actions_key="test-actions-key",
        )

    assert response == {"ok": True, "job_id": "job-export-router", "files": {"json": "/tmp/router-export.json"}}
    assert seen["raw_request"]["topic"] == "router-export"
    assert seen["raw_request"]["sections"] == [{"title": "工程概况", "content": "内容", "agent_role": None}]
    assert seen["workspace_dir"] == "/tmp/router-export-workspace"
    assert callable(seen["save_outputs_fn"])


@pytest.mark.asyncio
async def test_actions_export_docx_preserves_reference_library_media_fields():
    from backend.app.routers import actions_bridge

    seen: dict[str, object] = {}

    def _fake_execute_export_docx_request(*, raw_request, workspace_dir, save_outputs_fn):
        seen["raw_request"] = raw_request
        seen["workspace_dir"] = workspace_dir
        return {"ok": True, "job_id": "job-export-router-2", "files": {"json": "/tmp/router-export-2.json"}}

    req = actions_bridge.ActionsExportRequest(
        topic="router-export-refs",
        sections=[actions_bridge.ActionsSection(title="施工总平面", content="内容")],
        generate_images=False,
        media=[{"path": "/tmp/preselected.png", "caption": "预选图片"}],
        image_selection_pack={
            "images": [
                {"source_path": "/tmp/site-plan.png", "caption": "现场平面示意"},
            ]
        },
        case_reference_pack={"selected_case_ids": ["case-1"]},
    )

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False), patch.object(
        actions_bridge.export_docx_core,
        "execute_export_docx_request",
        side_effect=_fake_execute_export_docx_request,
    ):
        response = await actions_bridge.actions_export_docx(req, x_actions_key="test-actions-key")

    assert response["ok"] is True
    assert seen["workspace_dir"] == "."
    assert seen["raw_request"]["media"] == [{"path": "/tmp/preselected.png", "caption": "预选图片"}]
    assert seen["raw_request"]["image_selection_pack"]["images"][0]["source_path"] == "/tmp/site-plan.png"
    assert seen["raw_request"]["case_reference_pack"]["selected_case_ids"] == ["case-1"]
