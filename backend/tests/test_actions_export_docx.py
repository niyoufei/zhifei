from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def _passing_delivery_gate(actions_bridge):
    core = {
        "schema_version": "delivery-quality-gate-v1",
        "strict": True,
        "delivery_allowed": True,
        "checks": [],
        "blocker_count": 0,
        "warning_count": 0,
        "blockers": [],
        "warnings": [],
    }
    return {
        **core,
        "decision_digest": actions_bridge.export_docx_core.canonical_export_digest(
            core
        ),
    }


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
        source_job_id="source-job-1",
        sections=[actions_bridge.ActionsSection(title="工程概况", content="内容")],
        generate_images=False,
    )

    source_variant = {
        "topic": "router-export",
        "project_id": "P1",
        "sections": [{"title": "工程概况", "content": "内容"}],
        "delivery_quality_gate": _passing_delivery_gate(actions_bridge),
    }

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False), patch.object(
        actions_bridge.export_docx_core,
        "execute_export_docx_request",
        side_effect=_fake_execute_export_docx_request,
    ), patch.object(
        actions_bridge,
        "_load_done_job_variants",
        return_value=({}, {}, {}, [source_variant]),
    ), patch.object(
        actions_bridge,
        "_require_formal_document_mutation",
    ):
        response = await actions_bridge.actions_export_docx(
            req,
            workspace_dir="/tmp/router-export-workspace",
            x_actions_key="test-actions-key",
        )

    assert response == {"ok": True, "job_id": "job-export-router", "files": {"json": "/tmp/router-export.json"}}
    assert seen["raw_request"]["topic"] == "router-export"
    assert seen["raw_request"]["sections"] == [{"title": "工程概况", "content": "内容"}]
    assert seen["raw_request"]["_formal_source_verified"] is True
    assert seen["raw_request"]["_formal_source_sections_digest"] == (
        actions_bridge.export_docx_core.canonical_sections_digest(
            source_variant["sections"]
        )
    )
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
        source_job_id="source-job-2",
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

    source_variant = {
        "topic": "router-export-refs",
        "project_id": "P2",
        "sections": [{"title": "施工总平面", "content": "内容"}],
        "media": [{"path": "/tmp/preselected.png", "caption": "预选图片"}],
        "image_selection_pack": {
            "images": [
                {"source_path": "/tmp/site-plan.png", "caption": "现场平面示意"},
            ]
        },
        "case_reference_pack": {"selected_case_ids": ["case-1"]},
        "delivery_quality_gate": _passing_delivery_gate(actions_bridge),
    }

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False), patch.object(
        actions_bridge.export_docx_core,
        "execute_export_docx_request",
        side_effect=_fake_execute_export_docx_request,
    ), patch.object(
        actions_bridge,
        "_load_done_job_variants",
        return_value=({}, {}, {}, [source_variant]),
    ), patch.object(
        actions_bridge,
        "_require_formal_document_mutation",
    ):
        response = await actions_bridge.actions_export_docx(req, x_actions_key="test-actions-key")

    assert response["ok"] is True
    assert seen["workspace_dir"] == "."
    assert seen["raw_request"]["media"] == [{"path": "/tmp/preselected.png", "caption": "预选图片"}]
    assert seen["raw_request"]["image_selection_pack"]["images"][0]["source_path"] == "/tmp/site-plan.png"
    assert seen["raw_request"]["case_reference_pack"]["selected_case_ids"] == ["case-1"]
    assert seen["raw_request"]["_formal_source_sections_digest"] == (
        actions_bridge.export_docx_core.canonical_sections_digest(
            source_variant["sections"]
        )
    )


@pytest.mark.asyncio
async def test_actions_export_docx_recomputes_source_delivery_gate_digest():
    from backend.app.routers import actions_bridge

    req = actions_bridge.ActionsExportRequest(
        topic="tampered-source",
        source_job_id="source-job-tampered",
        sections=[actions_bridge.ActionsSection(title="工程概况", content="内容")],
        generate_images=False,
    )
    source_variant = {
        "project_id": "P-TAMPERED",
        "sections": [{"title": "工程概况", "content": "内容"}],
        "delivery_quality_gate": {
            **_passing_delivery_gate(actions_bridge),
            "delivery_allowed": False,
        },
    }

    with patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), patch.object(
        actions_bridge,
        "_load_done_job_variants",
        return_value=({}, {}, {}, [source_variant]),
    ), patch.object(
        actions_bridge,
        "_require_formal_document_mutation",
    ), pytest.raises(actions_bridge.HTTPException) as exc_info:
        await actions_bridge.actions_export_docx(
            req,
            x_actions_key="test-actions-key",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "FORMAL_SOURCE_DECISION_INVALID"
