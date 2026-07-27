from __future__ import annotations

import copy
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_ACTIONS_ZBID_RUNTIME_BINDINGS = {
    "FastAPI": ("fastapi", "FastAPI"),
    "HTTPException": ("fastapi", "HTTPException"),
    "TestClient": ("fastapi.testclient", "TestClient"),
    "FORBIDDEN_KEYS": (
        "backend.zhifei_autoplan.zbid_snapshot_mapper",
        "FORBIDDEN_KEYS",
    ),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_actions_zbid_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _ACTIONS_ZBID_RUNTIME_BINDINGS,
        module_prefixes=("fastapi", "starlette", "httpx"),
    ):
        yield


ZBID_PREVIEW_PATH = "/actions/zbid/snapshot_draft_input/preview"
TEST_ACTIONS_KEY = "test-actions-key"


def _file_count(path: str) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file())


def _artifact_counts() -> dict[str, int]:
    return {
        "jobs": _file_count("backend/data/autoplan/jobs"),
        "build": _file_count("build"),
        "output": _file_count("output"),
    }


def _valid_snapshot() -> dict:
    return {
        "snapshot_meta": {
            "snapshot_id": "snapshot-1",
            "source_system": "ZBid",
            "schema_version": "0.1",
            "snapshot_created_at": "2026-05-05T10:00:00+08:00",
            "requested_by": "reviewer@example.com",
        },
        "project": {
            "project_id": "project-1",
            "project_name": "技术标项目",
            "project_code": "BID-001",
            "owner_name": "建设单位",
            "bidder_name": "投标单位",
            "document_type": "technical_bid",
        },
        "lot": {
            "lot_id": "lot-1",
            "lot_name": "一标段",
            "scope_summary": "施工范围",
            "planned_duration_days": 180,
            "quality_target": "合格",
            "safety_target": "无重大事故",
        },
        "tender": {
            "scoring_items": [
                {
                    "item_id": "score-1",
                    "item_name": "施工组织",
                    "max_score": 10,
                    "requirement_text": "方案完整可行",
                    "evidence_needed": ["schedule"],
                }
            ]
        },
        "section_tasks": [
            {
                "section_id": "section-1",
                "title": "施工组织设计",
                "draft_intent": "生成只读草稿输入",
                "original_text": "原章节正文",
                "requirements": ["覆盖进度、资源和质量措施"],
                "target_length": "约1200字",
                "related_scoring_item_ids": ["score-1"],
                "related_material_ids": ["material-1"],
            }
        ],
        "technical_materials": [
            {
                "material_id": "material-1",
                "material_type": "schedule",
                "title": "进度控制素材",
                "content_excerpt": "采用周计划和节点跟踪。",
                "source_ref": "material-ref-1",
                "source_version": "v1",
                "confidence": "reviewed",
                "usable_for_draft": True,
                "sensitive": False,
            }
        ],
        "review_context": {
            "review_state": "pending_review",
            "review_note": "仅供草稿预览",
        },
        "version_hashes": {
            "snapshot_hash": "sha256:snapshot",
            "section_original_hash": "sha256:original",
            "prompt_input_hash": "sha256:prompt",
        },
        "safety_boundary": {
            "draft_only": True,
            "allow_formal_apply": False,
            "allow_export": False,
            "allow_job_write": False,
            "allow_result_bundle_write": False,
            "allow_ollama": False,
        },
    }


def _assert_no_forbidden_keys(value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert str(key).lower() not in FORBIDDEN_KEYS
            _assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child)


def _actions_test_client(actions_bridge) -> TestClient:
    app = FastAPI()
    app.include_router(actions_bridge.router)
    return TestClient(app)


def _actions_headers() -> dict[str, str]:
    return {"X-Actions-Key": TEST_ACTIONS_KEY}


def _no_write_chain_patches(actions_bridge):
    patches = [
        patch.object(actions_bridge, "run_ollama_preview", side_effect=AssertionError("Ollama preview must not be called")),
        patch.object(actions_bridge, "run_ollama_section_review", side_effect=AssertionError("Ollama review must not be called")),
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")),
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")),
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")),
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")),
        patch.object(actions_bridge, "save_output_artifacts", side_effect=AssertionError("output artifacts must not be written")),
        patch.object(actions_bridge, "build_section_draft", side_effect=AssertionError("section draft build must not be called")),
        patch.object(actions_bridge, "apply_section_draft", side_effect=AssertionError("section draft apply must not be called")),
        patch.object(actions_bridge, "reject_section_draft", side_effect=AssertionError("section draft reject must not be called")),
        patch.object(actions_bridge, "rollback_section_draft", side_effect=AssertionError("section draft rollback must not be called")),
        patch("backend.zhifei_autoplan.utils.llm_client.LLMClient.__init__", side_effect=AssertionError("LLMClient must not be called")),
    ]
    export_names = [
        name
        for name in dir(actions_bridge.export_docx_core)
        if ("export" in name.lower() or "docx" in name.lower() or "xlsx" in name.lower())
        and callable(getattr(actions_bridge.export_docx_core, name))
    ]
    patches.extend(
        patch.object(
            actions_bridge.export_docx_core,
            name,
            side_effect=AssertionError(f"export/docx/xlsx function must not be called: {name}"),
        )
        for name in export_names
    )
    return patches


def _start_patches(stack: ExitStack, patches):
    return [stack.enter_context(item) for item in patches]


@pytest.mark.asyncio
async def test_zbid_snapshot_preview_disabled_does_not_call_mapper(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.delenv("ZDOC_ZBID_MOCK_API_ENABLED", raising=False)
    req = actions_bridge.ActionsZBidSnapshotDraftInputPreviewRequest(snapshot=_valid_snapshot())

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False),
        patch.object(
            actions_bridge,
            "map_zbid_snapshot_to_zdoc_draft_input",
            side_effect=AssertionError("mapper must not be called when disabled"),
        ) as mapper_mock,
    ):
        result = await actions_bridge.actions_zbid_snapshot_draft_input_preview(req, x_actions_key="test-actions-key")

    assert result == {
        "ok": False,
        "status": "disabled",
        "mode": "mock_only",
        "draft_only": True,
        "no_write": True,
        "source_system": "zbid",
        "data": None,
        "error": "zbid_mock_api_disabled",
    }
    mapper_mock.assert_not_called()


@pytest.mark.asyncio
async def test_zbid_snapshot_preview_enabled_maps_valid_snapshot_without_writes() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    snapshot = _valid_snapshot()
    req = actions_bridge.ActionsZBidSnapshotDraftInputPreviewRequest(snapshot=snapshot)

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False))
        mapper_mock = stack.enter_context(
            patch.object(
                actions_bridge,
                "map_zbid_snapshot_to_zdoc_draft_input",
                wraps=actions_bridge.map_zbid_snapshot_to_zdoc_draft_input,
            )
        )

        result = await actions_bridge.actions_zbid_snapshot_draft_input_preview(req, x_actions_key="test-actions-key")

    assert result["ok"] is True
    assert result["status"] == "mapped"
    assert result["mode"] == "mock_only"
    assert result["draft_only"] is True
    assert result["no_write"] is True
    assert result["source_system"] == "zbid"
    assert result["data"]["mode"] == "draft_only"
    assert result["data"]["source_system"] == "zbid"
    assert result["data"]["safety_boundary"]["no_write"] is True
    assert result["data"]["safety_boundary"]["allow_ollama"] is False

    mapper_mock.assert_called_once_with(snapshot)
    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts


@pytest.mark.asyncio
async def test_zbid_snapshot_preview_invalid_snapshot_returns_controlled_400() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    snapshot = _valid_snapshot()
    snapshot.pop("snapshot_meta")
    req = actions_bridge.ActionsZBidSnapshotDraftInputPreviewRequest(snapshot=snapshot)

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False))

        with pytest.raises(HTTPException) as exc_info:
            await actions_bridge.actions_zbid_snapshot_draft_input_preview(req, x_actions_key="test-actions-key")

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["ok"] is False
    assert detail["status"] == "validation_error"
    assert detail["mode"] == "mock_only"
    assert detail["draft_only"] is True
    assert detail["no_write"] is True
    assert detail["source_system"] == "zbid"
    assert detail["data"] is None
    assert detail["error"] == "validation_error"
    assert detail["message"] == "missing required top-level field: snapshot_meta"
    assert "Traceback" not in detail["message"]

    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts


@pytest.mark.asyncio
async def test_zbid_snapshot_preview_forbidden_key_returns_controlled_400() -> None:
    from backend.app.routers import actions_bridge

    snapshot = _valid_snapshot()
    snapshot["project"]["nested"] = {"job": "must-not-pass"}
    req = actions_bridge.ActionsZBidSnapshotDraftInputPreviewRequest(snapshot=snapshot)

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False):
        with pytest.raises(HTTPException) as exc_info:
            await actions_bridge.actions_zbid_snapshot_draft_input_preview(req, x_actions_key="test-actions-key")

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["status"] == "validation_error"
    assert detail["error"] == "validation_error"
    assert "forbidden field" in detail["message"]
    assert "Traceback" not in detail["message"]


@pytest.mark.asyncio
async def test_zbid_snapshot_preview_response_does_not_contain_forbidden_keys() -> None:
    from backend.app.routers import actions_bridge

    req = actions_bridge.ActionsZBidSnapshotDraftInputPreviewRequest(snapshot=copy.deepcopy(_valid_snapshot()))

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False):
        result = await actions_bridge.actions_zbid_snapshot_draft_input_preview(req, x_actions_key="test-actions-key")

    _assert_no_forbidden_keys(result)


def test_zbid_snapshot_preview_http_smoke_disabled_does_not_call_mapper(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.delenv("ZDOC_ZBID_MOCK_API_ENABLED", raising=False)

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": TEST_ACTIONS_KEY}, clear=False),
        patch.object(
            actions_bridge,
            "map_zbid_snapshot_to_zdoc_draft_input",
            side_effect=AssertionError("mapper must not be called when disabled"),
        ) as mapper_mock,
    ):
        client = _actions_test_client(actions_bridge)
        response = client.post(ZBID_PREVIEW_PATH, json={"snapshot": _valid_snapshot()}, headers=_actions_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["status"] == "disabled"
    assert body["mode"] == "mock_only"
    assert body["draft_only"] is True
    assert body["no_write"] is True
    assert body["source_system"] == "zbid"
    assert body["data"] is None
    mapper_mock.assert_not_called()


def test_zbid_snapshot_preview_http_smoke_enabled_valid_snapshot_no_write() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    snapshot = _valid_snapshot()

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(patch.dict(os.environ, {"ZF_ACTIONS_KEY": TEST_ACTIONS_KEY, "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False))
        mapper_mock = stack.enter_context(
            patch.object(
                actions_bridge,
                "map_zbid_snapshot_to_zdoc_draft_input",
                wraps=actions_bridge.map_zbid_snapshot_to_zdoc_draft_input,
            )
        )

        client = _actions_test_client(actions_bridge)
        response = client.post(ZBID_PREVIEW_PATH, json={"snapshot": snapshot}, headers=_actions_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "mapped"
    assert body["mode"] == "mock_only"
    assert body["draft_only"] is True
    assert body["no_write"] is True
    assert body["source_system"] == "zbid"
    assert body["data"]["mode"] == "draft_only"
    assert body["data"]["source_system"] == "zbid"
    assert body["data"]["safety_boundary"]["no_write"] is True
    assert body["data"]["safety_boundary"]["allow_ollama"] is False

    _assert_no_forbidden_keys(body)
    mapper_mock.assert_called_once_with(snapshot)
    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts


def test_zbid_snapshot_preview_http_smoke_invalid_snapshot_returns_controlled_400() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    snapshot = _valid_snapshot()
    snapshot.pop("snapshot_meta")

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(patch.dict(os.environ, {"ZF_ACTIONS_KEY": TEST_ACTIONS_KEY, "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False))

        client = _actions_test_client(actions_bridge)
        response = client.post(ZBID_PREVIEW_PATH, json={"snapshot": snapshot}, headers=_actions_headers())

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["ok"] is False
    assert detail["status"] == "validation_error"
    assert detail["mode"] == "mock_only"
    assert detail["draft_only"] is True
    assert detail["no_write"] is True
    assert detail["source_system"] == "zbid"
    assert detail["data"] is None
    assert detail["error"] == "validation_error"
    assert detail["message"] == "missing required top-level field: snapshot_meta"
    assert "Traceback" not in detail["message"]

    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts


def test_zbid_snapshot_preview_http_smoke_forbidden_key_returns_controlled_400() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    snapshot = _valid_snapshot()
    snapshot["project"]["nested"] = {"job": "must-not-pass"}

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(patch.dict(os.environ, {"ZF_ACTIONS_KEY": TEST_ACTIONS_KEY, "ZDOC_ZBID_MOCK_API_ENABLED": "1"}, clear=False))

        client = _actions_test_client(actions_bridge)
        response = client.post(ZBID_PREVIEW_PATH, json={"snapshot": snapshot}, headers=_actions_headers())

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["status"] == "validation_error"
    assert detail["error"] == "validation_error"
    assert "forbidden field" in detail["message"]
    assert "Traceback" not in detail["message"]

    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts
