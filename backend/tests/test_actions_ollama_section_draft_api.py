from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest


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


def _sample_draft() -> dict:
    return {
        "draft_type": "section_draft",
        "section_title": "质量保证措施",
        "original_content": "原措施：责任到人。",
        "draft_content": "新措施：责任到人，并补充验收记录。",
        "original_hash": "original-hash",
        "draft_hash": "draft-hash",
        "status": "draft",
        "provider": "ollama",
        "model": "qwen3:0.6b",
        "base_url": "http://127.0.0.1:11434",
        "prompt_hash": "prompt-hash",
        "audit": [
            {
                "draft_type": "section_draft",
                "action_type": "created",
                "section_title": "质量保证措施",
                "original_hash": "original-hash",
                "draft_hash": "draft-hash",
                "provider": "ollama",
                "model": "qwen3:0.6b",
                "base_url": "http://127.0.0.1:11434",
                "prompt_hash": "prompt-hash",
                "confirmed_by": None,
                "confirmed_at": "2026-05-05T00:00:00+00:00",
            }
        ],
    }


def _no_write_chain_patches(actions_bridge):
    patches = [
        patch.object(actions_bridge, "run_ollama_preview", side_effect=AssertionError("Ollama preview must not be called")),
        patch.object(actions_bridge, "run_ollama_section_review", side_effect=AssertionError("Ollama review must not be called")),
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")),
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")),
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")),
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")),
        patch.object(actions_bridge, "save_output_artifacts", side_effect=AssertionError("output artifacts must not be written")),
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
    mocks = [stack.enter_context(item) for item in patches]
    return mocks


@pytest.mark.asyncio
async def test_actions_ollama_section_draft_build_disabled_does_not_call_helpers(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.delenv("ZDOC_OLLAMA_WRITE_BACK_ENABLED", raising=False)
    req = actions_bridge.ActionsOllamaSectionDraftBuildRequest(
        project_name="厂房项目",
        section_title="施工部署",
        original_content="原章节正文",
        draft_content="草稿章节正文",
        provider="ollama",
        model="qwen3:0.6b",
        base_url="http://127.0.0.1:11434",
    )

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False),
        patch.object(actions_bridge, "build_section_draft", side_effect=AssertionError("draft helper must not be called")) as build_mock,
        patch.object(actions_bridge, "compute_section_draft_diff", side_effect=AssertionError("diff helper must not be called")) as diff_mock,
    ):
        result = await actions_bridge.actions_ollama_section_draft_build(req, x_actions_key="test-actions-key")

    assert result == {
        "ok": False,
        "status": "disabled",
        "draft_type": "section_draft",
        "section_title": "施工部署",
        "draft": None,
        "diff_preview": "",
        "audit": [],
        "error": None,
        "warning": "ollama_write_back_disabled",
    }
    build_mock.assert_not_called()
    diff_mock.assert_not_called()


@pytest.mark.asyncio
async def test_actions_ollama_section_draft_build_enabled_returns_draft_diff_audit_without_writes() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    req = actions_bridge.ActionsOllamaSectionDraftBuildRequest(
        project_name="厂房项目",
        section_title="质量保证措施",
        original_content="原措施：责任到人。",
        draft_content="新措施：责任到人，并补充验收记录。",
        provider="ollama",
        model="qwen3:0.6b",
        base_url="http://127.0.0.1:11434",
        prompt="只生成 draft-only 章节草稿。",
        confirmed_by="reviewer",
    )

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_WRITE_BACK_ENABLED": "1"}, clear=False),
        patch.object(actions_bridge, "run_ollama_preview", side_effect=AssertionError("Ollama preview must not be called")) as preview_mock,
        patch.object(actions_bridge, "run_ollama_section_review", side_effect=AssertionError("Ollama review must not be called")) as review_mock,
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")) as run_mock,
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")) as create_job_mock,
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")) as update_job_mock,
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")) as save_mock,
        patch.object(actions_bridge, "save_output_artifacts", side_effect=AssertionError("output artifacts must not be written")) as artifacts_mock,
        patch.object(actions_bridge.export_docx_core, "execute_export_docx_request", side_effect=AssertionError("export must not run")) as export_mock,
        patch("backend.zhifei_autoplan.utils.llm_client.LLMClient.__init__", side_effect=AssertionError("LLMClient must not be called")) as llm_mock,
    ):
        result = await actions_bridge.actions_ollama_section_draft_build(req, x_actions_key="test-actions-key")

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["draft_type"] == "section_draft"
    assert result["section_title"] == "质量保证措施"
    assert result["error"] is None

    draft = result["draft"]
    assert draft["section_title"] == "质量保证措施"
    assert draft["original_content"] == "原措施：责任到人。"
    assert draft["draft_content"] == "新措施：责任到人，并补充验收记录。"
    assert draft["status"] == "draft"
    assert draft["provider"] == "ollama"
    assert draft["model"] == "qwen3:0.6b"
    assert draft["base_url"] == "http://127.0.0.1:11434"
    assert draft["original_hash"]
    assert draft["draft_hash"]
    assert draft["original_hash"] != draft["draft_hash"]

    assert "-原措施：责任到人。" in result["diff_preview"]
    assert "+新措施：责任到人，并补充验收记录。" in result["diff_preview"]
    assert result["audit"] == draft["audit"]
    assert result["audit"][0]["action_type"] == "created"
    assert result["audit"][0]["original_hash"] == draft["original_hash"]
    assert result["audit"][0]["draft_hash"] == draft["draft_hash"]

    preview_mock.assert_not_called()
    review_mock.assert_not_called()
    run_mock.assert_not_called()
    create_job_mock.assert_not_called()
    update_job_mock.assert_not_called()
    save_mock.assert_not_called()
    artifacts_mock.assert_not_called()
    export_mock.assert_not_called()
    llm_mock.assert_not_called()
    assert _artifact_counts() == before_counts


@pytest.mark.asyncio
async def test_actions_ollama_section_draft_decisions_disabled_do_not_call_helpers(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.delenv("ZDOC_OLLAMA_WRITE_BACK_ENABLED", raising=False)
    req = actions_bridge.ActionsOllamaSectionDraftDecisionRequest(draft=_sample_draft())

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False),
        patch.object(actions_bridge, "apply_section_draft", side_effect=AssertionError("apply helper must not be called")) as apply_mock,
        patch.object(actions_bridge, "reject_section_draft", side_effect=AssertionError("reject helper must not be called")) as reject_mock,
        patch.object(actions_bridge, "rollback_section_draft", side_effect=AssertionError("rollback helper must not be called")) as rollback_mock,
    ):
        apply_result = await actions_bridge.actions_ollama_section_draft_apply_preview(req, x_actions_key="test-actions-key")
        reject_result = await actions_bridge.actions_ollama_section_draft_reject(req, x_actions_key="test-actions-key")
        rollback_result = await actions_bridge.actions_ollama_section_draft_rollback(req, x_actions_key="test-actions-key")

    assert apply_result == {
        "ok": False,
        "status": "disabled",
        "draft_type": "section_draft",
        "action_type": "apply_preview",
        "draft": None,
        "audit": [],
        "error": None,
        "warning": "ollama_write_back_disabled",
    }
    assert reject_result == {
        "ok": False,
        "status": "disabled",
        "draft_type": "section_draft",
        "action_type": "reject",
        "draft": None,
        "audit": [],
        "error": None,
        "warning": "ollama_write_back_disabled",
    }
    assert rollback_result == {
        "ok": False,
        "status": "disabled",
        "draft_type": "section_draft",
        "action_type": "rollback",
        "draft": None,
        "audit": [],
        "error": None,
        "warning": "ollama_write_back_disabled",
    }
    apply_mock.assert_not_called()
    reject_mock.assert_not_called()
    rollback_mock.assert_not_called()


@pytest.mark.asyncio
async def test_actions_ollama_section_draft_decisions_enabled_return_audit_without_writes() -> None:
    from backend.app.routers import actions_bridge

    before_counts = _artifact_counts()
    base_draft = _sample_draft()
    req = actions_bridge.ActionsOllamaSectionDraftDecisionRequest(
        draft=base_draft,
        confirmed_by="reviewer",
        confirmed_at="2026-05-05T01:02:03+00:00",
    )

    with ExitStack() as stack:
        no_write_mocks = _start_patches(stack, _no_write_chain_patches(actions_bridge))
        stack.enter_context(
            patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_WRITE_BACK_ENABLED": "1"}, clear=False)
        )
        apply_mock = stack.enter_context(patch.object(actions_bridge, "apply_section_draft", wraps=actions_bridge.apply_section_draft))
        reject_mock = stack.enter_context(patch.object(actions_bridge, "reject_section_draft", wraps=actions_bridge.reject_section_draft))
        rollback_mock = stack.enter_context(patch.object(actions_bridge, "rollback_section_draft", wraps=actions_bridge.rollback_section_draft))

        apply_result = await actions_bridge.actions_ollama_section_draft_apply_preview(req, x_actions_key="test-actions-key")
        reject_result = await actions_bridge.actions_ollama_section_draft_reject(req, x_actions_key="test-actions-key")
        rollback_result = await actions_bridge.actions_ollama_section_draft_rollback(req, x_actions_key="test-actions-key")

    assert apply_result["ok"] is True
    assert apply_result["status"] == "applied"
    assert apply_result["draft_type"] == "section_draft"
    assert apply_result["action_type"] == "apply_preview"
    assert apply_result["error"] is None
    assert apply_result["draft"]["status"] == "applied"
    assert apply_result["draft"]["applied_content"] == base_draft["draft_content"]
    assert apply_result["draft"]["applied_hash"]
    assert apply_result["audit"] == apply_result["draft"]["audit"]
    assert apply_result["audit"][-1]["action_type"] == "applied"
    assert apply_result["audit"][-1]["confirmed_by"] == "reviewer"

    assert reject_result["ok"] is True
    assert reject_result["status"] == "rejected"
    assert reject_result["draft_type"] == "section_draft"
    assert reject_result["action_type"] == "reject"
    assert reject_result["error"] is None
    assert reject_result["draft"]["status"] == "rejected"
    assert reject_result["audit"] == reject_result["draft"]["audit"]
    assert reject_result["audit"][-1]["action_type"] == "rejected"

    assert rollback_result["ok"] is True
    assert rollback_result["status"] == "rolled_back"
    assert rollback_result["draft_type"] == "section_draft"
    assert rollback_result["action_type"] == "rollback"
    assert rollback_result["error"] is None
    assert rollback_result["draft"]["status"] == "rolled_back"
    assert rollback_result["draft"]["draft_content"] == base_draft["original_content"]
    assert rollback_result["draft"]["rolled_back_content"] == base_draft["original_content"]
    assert rollback_result["audit"] == rollback_result["draft"]["audit"]
    assert rollback_result["audit"][-1]["action_type"] == "rolled_back"

    apply_mock.assert_called_once_with(base_draft, confirmed_by="reviewer", confirmed_at="2026-05-05T01:02:03+00:00")
    reject_mock.assert_called_once_with(base_draft, confirmed_by="reviewer", confirmed_at="2026-05-05T01:02:03+00:00")
    rollback_mock.assert_called_once_with(base_draft, confirmed_by="reviewer", confirmed_at="2026-05-05T01:02:03+00:00")
    for mock in no_write_mocks:
        mock.assert_not_called()
    assert _artifact_counts() == before_counts
