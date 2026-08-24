from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_anthropic_provider_forwards_timeout_and_large_revision_budget():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text="修订正文")])

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider.model = "review-model"

    result = await provider.complete("prompt", timeout=12, max_tokens=9000)

    assert result["text"] == "修订正文"
    assert seen["timeout"] == 12.0
    assert seen["max_tokens"] == 9000


@pytest.mark.asyncio
async def test_anthropic_provider_ignores_thinking_blocks_and_collects_all_text_blocks():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    def create(**kwargs):
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="internal reasoning"),
                SimpleNamespace(type="redacted_thinking", data="redacted"),
                SimpleNamespace(type="text", text="第一段专业正文"),
                {"type": "text", "text": "第二段专业正文"},
            ]
        )

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider.model = "extended-thinking-model"

    result = await provider.complete("prompt")

    assert result["text"] == "第一段专业正文\n\n第二段专业正文"
    assert "internal reasoning" not in result["text"]


@pytest.mark.asyncio
async def test_anthropic_provider_rejects_thinking_only_response_as_no_visible_text():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    def create(**kwargs):
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="internal reasoning"),
                SimpleNamespace(type="redacted_thinking", data="redacted"),
            ]
        )

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider.model = "extended-thinking-model"

    result = await provider.complete("prompt")

    assert result["text"] == ""
    assert result["error"] == "no_visible_text"


@pytest.mark.asyncio
async def test_openai_provider_forwards_timeout_without_blocking_contract():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(output_text="备用修订正文")

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("prompt", timeout=15)

    assert result["text"] == "备用修订正文"
    assert seen == {"model": "fallback-model", "input": "prompt", "timeout": 15.0}


@pytest.mark.asyncio
async def test_openai_provider_rejects_empty_output_as_no_visible_text():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    def create(**kwargs):
        return SimpleNamespace(output_text="")

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("prompt")

    assert result["text"] == ""
    assert result["error"] == "no_visible_text"
