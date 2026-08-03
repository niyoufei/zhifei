from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_ACTIONS_OLLAMA_PREVIEW_RUNTIME_BINDINGS = {
    "actions_bridge": ("backend.app.routers.actions_bridge", None),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_actions_ollama_preview_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _ACTIONS_OLLAMA_PREVIEW_RUNTIME_BINDINGS,
    ):
        yield


def _file_count(path: str) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file())


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


@pytest.mark.asyncio
async def test_actions_ollama_main_chain_smoke_disabled_does_not_call_orchestrator(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.delenv("ZDOC_OLLAMA_MAIN_CHAIN_SMOKE_ENABLED", raising=False)
    req = actions_bridge.ActionsOllamaMainChainSmokeRequest(
        topic="Ollama smoke",
        outline=["章节1"],
        model="qwen3:0.6b",
    )

    with (
        patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False),
        patch.object(actions_bridge, "run_autoplan", side_effect=AssertionError("orchestrator must not be called")) as run_mock,
    ):
        result = await actions_bridge.actions_ollama_main_chain_smoke(req, x_actions_key="test-actions-key")

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_main_chain_smoke_disabled"
    assert result["smoke_type"] == "ollama_main_chain_no_write"
    assert result["section_count"] == 0
    assert result["sections_preview"] == []
    run_mock.assert_not_called()


@pytest.mark.asyncio
async def test_actions_ollama_main_chain_smoke_enabled_mock_success_forces_no_write_and_avoids_writes() -> None:
    from backend.app.routers import actions_bridge

    before_counts = {
        "jobs": _file_count("backend/data/autoplan/jobs"),
        "build": _file_count("build"),
        "output": _file_count("output"),
    }
    req = actions_bridge.ActionsOllamaMainChainSmokeRequest(
        topic="Ollama smoke",
        outline=["章节1", "章节2"],
        requirements=["只做烟测。"],
        model="qwen3:0.6b",
        base_url="http://127.0.0.1:11434",
    )
    run_mock = AsyncMock(
        return_value={
            "sections": [
                {
                    "title": "章节1",
                    "provider": "ollama",
                    "model": "qwen3:0.6b",
                    "content": "Ollama no-write smoke content.",
                    "error": None,
                }
            ]
        }
    )

    with (
        patch.dict(
            os.environ,
            {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_MAIN_CHAIN_SMOKE_ENABLED": "1"},
            clear=False,
        ),
        patch.object(actions_bridge, "run_autoplan", run_mock),
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")) as create_job_mock,
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")) as update_job_mock,
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")) as save_mock,
        patch.object(actions_bridge, "save_output_artifacts", side_effect=AssertionError("output artifacts must not be written")) as artifacts_mock,
        patch.object(actions_bridge.export_docx_core, "execute_export_docx_request", side_effect=AssertionError("export must not run")) as export_mock,
    ):
        result = await actions_bridge.actions_ollama_main_chain_smoke(req, x_actions_key="test-actions-key")

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["provider"] == "ollama"
    assert result["model"] == "qwen3:0.6b"
    assert result["base_url"] == "http://127.0.0.1:11434"
    assert result["smoke_type"] == "ollama_main_chain_no_write"
    assert result["section_count"] == 1
    assert result["sections_preview"] == [
        {
            "title": "章节1",
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "error": None,
            "content_preview": "Ollama no-write smoke content.",
        }
    ]

    run_mock.assert_awaited_once()
    payload = run_mock.await_args.args[0]
    assert payload["provider"] == "ollama"
    assert payload["model"] == "qwen3:0.6b"
    assert payload["base_url"] == "http://127.0.0.1:11434"
    assert payload["no_write"] is True
    assert payload["preview_only"] is True
    assert payload["generate_images"] is False
    assert payload["auto_remediate"] is False
    assert payload["quality_strict"] is False
    assert payload["agent_parallelism"] == 1
    assert payload["variant_parallelism"] == 1
    assert payload["outline"] == ["章节1"]

    create_job_mock.assert_not_called()
    update_job_mock.assert_not_called()
    save_mock.assert_not_called()
    artifacts_mock.assert_not_called()
    export_mock.assert_not_called()
    assert {
        "jobs": _file_count("backend/data/autoplan/jobs"),
        "build": _file_count("build"),
        "output": _file_count("output"),
    } == before_counts


@pytest.mark.asyncio
async def test_actions_ollama_main_chain_smoke_run_autoplan_error_returns_fallback() -> None:
    from backend.app.routers import actions_bridge

    req = actions_bridge.ActionsOllamaMainChainSmokeRequest(model="not-exist-model")
    run_mock = AsyncMock(side_effect=RuntimeError("mock failure"))

    with (
        patch.dict(
            os.environ,
            {"ZF_ACTIONS_KEY": "test-actions-key", "ZDOC_OLLAMA_MAIN_CHAIN_SMOKE_ENABLED": "1"},
            clear=False,
        ),
        patch.object(actions_bridge, "run_autoplan", run_mock),
        patch.object(actions_bridge, "create_job", side_effect=AssertionError("job must not be created")) as create_job_mock,
        patch.object(actions_bridge, "update_job", side_effect=AssertionError("job must not be updated")) as update_job_mock,
        patch.object(actions_bridge, "_save_outputs", side_effect=AssertionError("result bundle must not be written")) as save_mock,
        patch.object(actions_bridge, "save_output_artifacts", side_effect=AssertionError("output artifacts must not be written")) as artifacts_mock,
    ):
        result = await actions_bridge.actions_ollama_main_chain_smoke(req, x_actions_key="test-actions-key")

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "fallback"
    assert result["model"] == "not-exist-model"
    assert result["section_count"] == 0
    assert result["sections_preview"] == []
    assert result["error"] == "ollama_main_chain_smoke_error:RuntimeError"
    assert result["smoke_type"] == "ollama_main_chain_no_write"
    run_mock.assert_awaited_once()
    create_job_mock.assert_not_called()
    update_job_mock.assert_not_called()
    save_mock.assert_not_called()
    artifacts_mock.assert_not_called()
