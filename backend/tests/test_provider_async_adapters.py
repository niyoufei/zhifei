from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_anthropic_provider_forwards_timeout_and_large_revision_budget():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text="修订正文")],
            stop_reason="end_turn",
        )

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider.model = "review-model"

    result = await provider.complete("prompt", timeout=12, max_tokens=9000)

    assert result["text"] == "修订正文"
    assert seen["timeout"] == 12.0
    assert seen["max_tokens"] == 9000
    assert result["stop_reason"] == "end_turn"


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
async def test_anthropic_provider_rejects_thinking_only_response_as_no_visible_text(
    monkeypatch,
):
    from backend.zhifei_autoplan.providers import anthropic_provider

    AnthropicProvider = anthropic_provider.AnthropicProvider
    usage_event = {}

    def _record_usage(**kwargs):
        usage_event.update(kwargs)
        return {"log_persisted": False}

    monkeypatch.setattr(anthropic_provider, "record_claude_usage", _record_usage)

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
    assert usage_event["status"] == "error"
    assert usage_event["error_type"] == "no_visible_text"


@pytest.mark.asyncio
async def test_anthropic_provider_rejects_partial_refusal_response():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    def create(**_kwargs):
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="部分拒绝说明")],
            stop_reason="refusal",
            usage=None,
        )

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    provider.model = "review-model"

    result = await provider.complete("prompt")

    assert result["text"] == "部分拒绝说明"
    assert result["error"] == "content_filtered"


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
async def test_openai_provider_clamps_admission_probe_to_responses_api_minimum():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(output_text="OK")

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("Reply with exactly OK.", max_tokens=8)

    assert result["text"] == "OK"
    assert seen["max_output_tokens"] == 16


@pytest.mark.asyncio
async def test_openai_provider_exposes_max_output_token_stop_reason():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    def create(**_kwargs):
        return SimpleNamespace(
            output_text="部分正文",
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("prompt", max_tokens=1024)

    assert result["text"] == "部分正文"
    assert result["stop_reason"] == "max_tokens"


@pytest.mark.asyncio
async def test_openai_provider_rejects_partial_content_filter_response():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    def create(**_kwargs):
        return SimpleNamespace(
            output_text="不完整正文",
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="content_filter"),
        )

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("prompt", max_tokens=1024)

    assert result["text"] == "不完整正文"
    assert result["error"] == "content_filtered"


@pytest.mark.asyncio
async def test_openai_provider_rejects_partial_failed_response():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    def create(**_kwargs):
        return SimpleNamespace(
            output_text="失败前的部分正文",
            status="failed",
            incomplete_details=None,
        )

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider.model = "fallback-model"

    result = await provider.complete("prompt", max_tokens=1024)

    assert result["error"] == "provider_error"


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


@pytest.mark.asyncio
async def test_openai_provider_streams_visible_text_with_split_timeouts():
    from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider

    seen = {}

    class _Stream:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter(
                [
                    SimpleNamespace(type="response.output_text.delta", delta="第一段"),
                    SimpleNamespace(type="response.output_text.delta", delta="第二段"),
                ]
            )

        def get_final_response(self):
            return SimpleNamespace(
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            )

    def stream(**kwargs):
        seen.update(kwargs)
        return _Stream()

    provider = object.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(responses=SimpleNamespace(stream=stream))
    provider.model = "stream-model"

    result = await provider.complete("prompt", timeout=240, stream=True, max_tokens=1024)

    assert result["text"] == "第一段第二段"
    assert result["streamed"] is True
    assert result["stop_reason"] == "max_tokens"
    assert seen["timeout"].connect == 15.0
    assert seen["timeout"].read == 45.0
    assert seen["max_output_tokens"] == 1024


@pytest.mark.asyncio
async def test_anthropic_provider_streams_visible_text_with_split_timeouts():
    from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider

    seen = {}

    class _Stream:
        text_stream = ["甲", "乙"]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get_final_message(self):
            return SimpleNamespace(stop_reason="max_tokens", usage=None)

    def stream(**kwargs):
        seen.update(kwargs)
        return _Stream()

    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    provider.model = "stream-model"

    result = await provider.complete("prompt", timeout=240, stream=True, max_tokens=1024)

    assert result["text"] == "甲乙"
    assert result["streamed"] is True
    assert result["stop_reason"] == "max_tokens"
    assert seen["timeout"].connect == 15.0
    assert seen["timeout"].read == 45.0
