from __future__ import annotations

import os
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_actions_ollama_preview_disabled_returns_warning(monkeypatch) -> None:
    from backend.app.routers.actions_bridge import ActionsOllamaPreviewRequest, actions_ollama_preview

    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_ENABLED", raising=False)
    req = ActionsOllamaPreviewRequest(content="章节正文", section_title="工程概况")

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        result = await actions_ollama_preview(req, x_actions_key="test-actions-key")

    assert result["ok"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_preview_disabled"


@pytest.mark.asyncio
async def test_actions_ollama_preview_enabled_mock_success_does_not_touch_generation_chain() -> None:
    from backend.app.routers import actions_bridge

    req = actions_bridge.ActionsOllamaPreviewRequest(content="章节正文", section_title="施工部署")
    expected = {
        "ok": True,
        "enabled": True,
        "status": "ok",
        "provider": "ollama",
        "model": "qwen3:0.6b",
        "base_url": "http://localhost:11434",
        "content": "风险提示：需补齐验收记录。",
        "warning": None,
        "error": None,
        "fallback": None,
    }

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_PREVIEW_ENABLED": "1"}, clear=False),
        patch.object(actions_bridge, "run_ollama_preview", return_value=expected) as preview_mock,
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")) as run_mock,
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")) as create_job_mock,
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")) as update_job_mock,
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")) as save_mock,
    ):
        result = await actions_bridge.actions_ollama_preview(req, x_actions_key="test-actions-key")

    assert result == expected
    preview_mock.assert_called_once()
    run_mock.assert_not_called()
    create_job_mock.assert_not_called()
    update_job_mock.assert_not_called()
    save_mock.assert_not_called()


@pytest.mark.asyncio
async def test_actions_ollama_section_review_disabled_returns_warning(monkeypatch) -> None:
    from backend.app.routers.actions_bridge import ActionsOllamaSectionReviewRequest, actions_ollama_review_section

    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_ENABLED", raising=False)
    req = ActionsOllamaSectionReviewRequest(
        project_name="厂房项目",
        section_title="质量保证措施",
        section_content="质量控制措施：责任到人。",
    )

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        result = await actions_ollama_review_section(req, x_actions_key="test-actions-key")

    assert result["ok"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_preview_disabled"
    assert result["review_type"] == "section_review"


@pytest.mark.asyncio
async def test_actions_ollama_section_review_enabled_mock_success_does_not_touch_generation_chain() -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.utils.llm_client import LLMClient

    req = actions_bridge.ActionsOllamaSectionReviewRequest(
        project_name="厂房项目",
        section_title="施工部署",
        section_content="施工部署章节正文。",
        review_focus="缺项和风险",
    )
    expected = {
        "ok": True,
        "enabled": True,
        "status": "ok",
        "provider": "ollama",
        "model": "qwen3:0.6b",
        "base_url": "http://localhost:11434",
        "content": "风险点：需补齐验收记录。",
        "warning": None,
        "error": None,
        "fallback": None,
        "review_type": "section_review",
        "fallback_reason": None,
    }

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_PREVIEW_ENABLED": "1"}, clear=False),
        patch.object(actions_bridge, "run_ollama_section_review", return_value=expected) as review_mock,
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")) as run_mock,
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")) as create_job_mock,
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")) as update_job_mock,
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")) as save_mock,
        patch.object(LLMClient, "__init__", side_effect=AssertionError("LLMClient must not be called")) as llm_mock,
    ):
        result = await actions_bridge.actions_ollama_review_section(req, x_actions_key="test-actions-key")

    assert result == expected
    review_mock.assert_called_once()
    run_mock.assert_not_called()
    create_job_mock.assert_not_called()
    update_job_mock.assert_not_called()
    save_mock.assert_not_called()
    llm_mock.assert_not_called()
