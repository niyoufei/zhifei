from __future__ import annotations

import sys
import urllib.error

import pytest

from backend.zhifei_autoplan.providers import ollama_provider
from backend.zhifei_autoplan.providers.ollama_provider import (
    OllamaProvider,
    build_ollama_chat_payload,
    parse_ollama_chat_response,
)


def test_ollama_provider_rejects_non_loopback_base_url() -> None:
    with pytest.raises(ValueError, match="LOCAL_OLLAMA_LOOPBACK_REQUIRED"):
        OllamaProvider(
            model="local-model",
            base_url="http://example.invalid:11434",
        )


def test_build_ollama_chat_payload_uses_chat_defaults() -> None:
    payload = build_ollama_chat_payload("检查施工部署", system_prompt="只输出建议", options={"temperature": 0})

    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {"temperature": 0}
    assert payload["messages"] == [
        {"role": "system", "content": "只输出建议"},
        {"role": "user", "content": "检查施工部署"},
    ]


def test_parse_ollama_chat_response_handles_message_content() -> None:
    assert parse_ollama_chat_response({"message": {"content": "复核建议"}}) == "复核建议"
    assert parse_ollama_chat_response({"message": {"content": "   "}}) == ""
    assert parse_ollama_chat_response({"unexpected": True}) == ""
    assert parse_ollama_chat_response(None) == ""


@pytest.mark.asyncio
async def test_complete_success_uses_mock_transport_and_api_chat() -> None:
    seen: dict = {}

    def fake_transport(url, payload, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"model": "qwen3:0.6b", "message": {"content": "缺项：需补充验收计划。"}}

    provider = OllamaProvider(model="qwen3:0.6b", base_url="http://127.0.0.1:11434/", transport=fake_transport)

    result = await provider.complete("质量保证措施", system_prompt="只做复核", options={"temperature": 0})

    assert result["ok"] is True
    assert result["provider"] == "ollama"
    assert result["model"] == "qwen3:0.6b"
    assert result["text"] == "缺项：需补充验收计划。"
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["timeout"] == 60.0
    assert seen["payload"]["model"] == "qwen3:0.6b"
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["think"] is False
    assert seen["payload"]["messages"][0]["role"] == "system"
    assert seen["payload"]["messages"][1] == {"role": "user", "content": "质量保证措施"}


@pytest.mark.asyncio
async def test_complete_does_not_require_api_key() -> None:
    def fake_transport(_url, _payload, _timeout):
        return {"message": {"content": "ok"}}

    provider = OllamaProvider(model="local-model", transport=fake_transport)

    result = await provider.complete("prompt")

    assert result["ok"] is True
    assert result["text"] == "ok"


@pytest.mark.asyncio
async def test_complete_timeout_returns_fallback() -> None:
    def timeout_transport(_url, _payload, _timeout):
        raise TimeoutError("timeout")

    provider = OllamaProvider(model="qwen3:0.6b", transport=timeout_transport)

    result = await provider.complete("进度计划")

    assert result == {
        "provider": "ollama",
        "model": "qwen3:0.6b",
        "text": "",
        "ok": False,
        "error": "ollama_timeout",
    }


@pytest.mark.asyncio
async def test_complete_http_error_returns_fallback() -> None:
    def error_transport(_url, _payload, _timeout):
        raise urllib.error.HTTPError("http://127.0.0.1:11434/api/chat", 404, "not found", None, None)

    provider = OllamaProvider(model="missing-model", transport=error_transport)

    result = await provider.complete("安全措施")

    assert result["ok"] is False
    assert result["provider"] == "ollama"
    assert result["model"] == "missing-model"
    assert result["text"] == ""
    assert result["error"] == "ollama_error:HTTPError"


@pytest.mark.asyncio
async def test_complete_empty_content_returns_fallback() -> None:
    def empty_transport(_url, _payload, _timeout):
        return {"model": "qwen3:0.6b", "message": {"content": ""}}

    provider = OllamaProvider(model="qwen3:0.6b", transport=empty_transport)

    result = await provider.complete("资源配置")

    assert result["ok"] is False
    assert result["text"] == ""
    assert result["error"] == "ollama_empty_response"


def test_adapter_import_does_not_pull_main_chain_modules(assert_clean_import) -> None:
    assert not hasattr(ollama_provider, "LLMClient")
    assert_clean_import(
        "backend.zhifei_autoplan.providers.ollama_provider",
        {"backend.zhifei_autoplan.orchestrator"},
    )
