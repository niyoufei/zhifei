from __future__ import annotations

import pytest

from backend.zhifei_autoplan.ollama_preview import run_ollama_preview


def test_ollama_preview_disabled_does_not_call_network(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_ENABLED", raising=False)

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("network should not be called when preview is disabled")

    result = run_ollama_preview(
        content="施工部署章节内容",
        transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_preview_disabled"


def test_ollama_preview_enabled_success_uses_api_chat(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")
    seen: dict = {}

    def fake_transport(url, payload, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"model": "qwen3:0.6b", "message": {"content": "缺项：需补充验收频次。"}}

    result = run_ollama_preview(
        content="质量控制措施：责任到人。",
        section_title="质量保证措施",
        instruction="只做缺项检查",
        transport=fake_transport,
    )

    assert result["ok"] is True
    assert result["content"] == "缺项：需补充验收频次。"
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["think"] is False
    assert seen["payload"]["messages"][0]["role"] == "user"
    assert seen["timeout"] == 60.0


def test_ollama_preview_enabled_timeout_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def timeout_transport(*_args, **_kwargs):
        raise TimeoutError("timeout")

    result = run_ollama_preview(
        content="安全文明施工章节",
        timeout=2,
        transport=timeout_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "fallback"
    assert result["error"] == "ollama_preview_timeout"
    assert result["fallback"]["available"] is True


def test_ollama_preview_enabled_exception_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def error_transport(*_args, **_kwargs):
        raise RuntimeError("model not found")

    result = run_ollama_preview(
        content="进度计划章节",
        transport=error_transport,
    )

    assert result["ok"] is False
    assert result["status"] == "fallback"
    assert result["error"] == "ollama_preview_error:RuntimeError"
