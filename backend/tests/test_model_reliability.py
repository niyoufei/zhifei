from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.zhifei_autoplan.model_reliability import (
    ModelReliabilityRuntime,
    bounded_retry_delay,
    classify_provider_error,
    sanitize_provider_message,
)
from backend.zhifei_autoplan.utils.llm_client import LLMClient


@pytest.mark.parametrize(
    ("error", "code", "retryable"),
    [
        ("401 invalid api key", "authentication_failed", False),
        ("429 rate limit exceeded", "rate_limited", True),
        ("429 insufficient_quota: credit balance exhausted", "quota_exhausted", False),
        ("429 credit_balance_exhausted", "quota_exhausted", False),
        ("You have no credits remaining. Please add credits.", "quota_exhausted", False),
        ("404 model not found", "model_not_found", False),
        (TimeoutError(), "timeout", True),
        ("503 service unavailable", "provider_unavailable", True),
        ("400 bad request", "invalid_request", False),
        ("content blocked by safety policy", "content_filtered", False),
        ("output_truncated", "output_truncated", False),
        ("no_visible_text", "no_visible_text", True),
    ],
)
def test_classify_provider_error(error, code, retryable):
    result = classify_provider_error(error, provider="anthropic", model="claude-test")
    assert result["code"] == code
    assert result["retryable"] is retryable
    assert result["provider"] == "anthropic"
    assert result["model"] == "claude-test"
    assert result["user_message"]
    assert result["action"]
    assert result["severity"] in {"warning", "error"}


def test_machine_readable_credit_balance_code_is_normalized_without_retry():
    result = classify_provider_error(
        {"code": "credit_balance_exhausted", "message": "request rejected"},
        provider="openai",
        model="gpt-test",
    )

    assert result["code"] == "quota_exhausted"
    assert result["retryable"] is False


def test_sanitize_provider_message_removes_secret_shaped_values():
    message = sanitize_provider_message(
        "Bearer abcdefghijklmnopqrstuvwxyz and sk-proj-abcdefghijklmno"
    )
    assert "abcdefghijklmnopqrstuvwxyz" not in message
    assert "sk-proj-abcdefghijklmno" not in message
    assert message.count("[REDACTED]") == 2


def test_internal_requirement_gate_identifier_is_not_a_provider_status_or_filter():
    result = classify_provider_error(
        "requirement_evidence_precheckpoint_blocked:REQ-CR-E1AF505EF062",
        provider="anthropic",
        model="claude-opus-5",
    )

    assert result["code"] == "provider_error"
    assert result["retryable"] is False


def test_explicit_provider_unavailable_status_remains_retryable():
    result = classify_provider_error(
        "503 provider unavailable",
        provider="anthropic",
        model="claude-opus-5",
    )

    assert result["code"] == "provider_unavailable"
    assert result["retryable"] is True


def test_runtime_opens_after_retryable_threshold_and_resets_on_success():
    runtime = ModelReliabilityRuntime(failure_threshold=2)
    error = classify_provider_error("503 unavailable", provider="openai", model="m")
    runtime.record_failure("openai", "m", error)
    assert runtime.is_open("openai", "m") is False
    runtime.record_failure("openai", "m", error)
    assert runtime.is_open("openai", "m") is True
    runtime.record_success("openai", "m")
    assert runtime.is_open("openai", "m") is False


def test_runtime_requires_threshold_for_nonretryable_failure_too():
    runtime = ModelReliabilityRuntime(failure_threshold=2)
    error = classify_provider_error("401 invalid api key", provider="openai", model="m")
    runtime.record_failure("openai", "m", error)
    assert runtime.is_open("openai", "m") is False
    runtime.record_failure("openai", "m", error)
    assert runtime.is_open("openai", "m") is True


def test_runtime_isolates_circuits_by_credential_identity():
    runtime = ModelReliabilityRuntime(failure_threshold=2)
    error = classify_provider_error("429 rate limit exceeded", provider="openai", model="m")
    runtime.record_failure("openai", "m", error, "credential-a")
    runtime.record_failure("openai", "m", error, "credential-a")

    assert runtime.is_open("openai", "m", "credential-a") is True
    assert runtime.is_open("openai", "m", "credential-b") is False
    assert runtime.is_open("openai", "m") is True


@pytest.mark.asyncio
async def test_llm_client_retries_transient_failure_then_succeeds():
    impl = MagicMock()
    impl.complete = AsyncMock(
        side_effect=[
            {"text": "", "error": "503 service unavailable"},
            {"text": "专业正文"},
        ]
    )
    runtime = ModelReliabilityRuntime(failure_threshold=3)
    with patch.object(LLMClient, "_init_provider", return_value=impl):
        client = LLMClient(
            provider="openai",
            model="m",
            api_key="test-key",
            reliability_runtime=runtime,
            retry_attempts=2,
            retry_base_delay=0,
        )
        result = await client.complete("prompt")

    assert result["text"] == "专业正文"
    assert result["attempts"] == 2
    assert impl.complete.await_count == 2
    assert runtime.is_open("openai", "m") is False


@pytest.mark.asyncio
async def test_llm_client_skips_open_circuit_without_provider_call():
    impl = MagicMock()
    impl.complete = AsyncMock(return_value={"text": "should not run"})
    runtime = ModelReliabilityRuntime(failure_threshold=1)
    runtime.record_failure(
        "openai",
        "m",
        classify_provider_error("401 invalid api key", provider="openai", model="m"),
    )
    with patch.object(LLMClient, "_init_provider", return_value=impl):
        client = LLMClient(
            provider="openai",
            model="m",
            api_key="test-key",
            reliability_runtime=runtime,
        )
        result = await client.complete("prompt")

    assert result["error_info"]["code"] == "circuit_open"
    assert "备用模型" in result["error_info"]["action"]
    assert result["attempts"] == 0
    impl.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_bounded_retry_delay_applies_bounded_symmetric_jitter():
    sleeps: list[float] = []

    async def _sleep(value: float) -> None:
        sleeps.append(value)

    await bounded_retry_delay(
        2,
        base_delay=1.0,
        jitter_ratio=0.25,
        random_fn=lambda: 1.0,
        sleep=_sleep,
    )

    assert sleeps == [2.5]


@pytest.mark.asyncio
async def test_quota_exhaustion_does_not_retry():
    impl = MagicMock()
    impl.complete = AsyncMock(
        return_value={"text": "", "error": "429 insufficient_quota: credit balance exhausted"}
    )
    with patch.object(LLMClient, "_init_provider", return_value=impl):
        client = LLMClient(
            provider="openai",
            model="m",
            api_key="test-key",
            retry_attempts=3,
            retry_base_delay=0,
        )
        result = await client.complete("prompt")

    assert result["error_info"]["code"] == "quota_exhausted"
    assert result["attempts"] == 1
    assert impl.complete.await_count == 1


@pytest.mark.asyncio
async def test_exhausted_internal_retries_count_as_one_circuit_failure():
    impl = MagicMock()
    impl.complete = AsyncMock(
        return_value={"text": "", "error": "503 service unavailable"}
    )
    runtime = ModelReliabilityRuntime(failure_threshold=2)

    with patch.object(LLMClient, "_init_provider", return_value=impl):
        client = LLMClient(
            provider="openai",
            model="m",
            api_key="test-key",
            reliability_runtime=runtime,
            retry_attempts=3,
            retry_base_delay=0,
        )
        first = await client.complete("prompt")
        assert first["attempts"] == 2
        assert runtime.is_open("openai", "m") is False

        second = await client.complete("prompt")

    assert second["attempts"] == 2
    assert impl.complete.await_count == 4
    assert runtime.is_open("openai", "m") is True
