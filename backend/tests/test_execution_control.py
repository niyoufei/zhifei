from __future__ import annotations

import asyncio

import pytest

from backend.zhifei_autoplan.execution_control import (
    ExecutionBudgetExceededError,
    ExecutionCancelledError,
    ExecutionControlRuntime,
)


def test_execution_control_enforces_global_concurrency_and_counts_retries():
    async def _run():
        runtime = ExecutionControlRuntime(max_concurrency=2, max_model_attempts=8)
        active = 0
        peak = 0
        lock = asyncio.Lock()

        async def _attempt(provider: str):
            nonlocal active, peak
            async with runtime.model_attempt(
                provider=provider,
                model="model",
                prompt_chars=10,
                requested_output_tokens=5,
            ):
                async with lock:
                    active += 1
                    peak = max(peak, active)
                await asyncio.sleep(0.02)
                async with lock:
                    active -= 1

        await asyncio.gather(*[_attempt("anthropic") for _ in range(5)])
        snapshot = runtime.snapshot()
        assert peak == 2
        assert snapshot["usage"]["model_attempts"] == 5
        assert snapshot["usage"]["peak_active"] == 2
        assert snapshot["usage"]["input_chars"] == 50
        assert snapshot["usage"]["requested_output_tokens"] == 25

    asyncio.run(_run())


def test_execution_control_blocks_before_crossing_any_budget():
    async def _run():
        runtime = ExecutionControlRuntime(
            max_concurrency=1,
            max_model_attempts=1,
            max_input_chars=10,
            max_requested_output_tokens=5,
        )
        async with runtime.model_attempt(
            provider="openai",
            model="m",
            prompt_chars=10,
            requested_output_tokens=5,
        ):
            pass
        with pytest.raises(ExecutionBudgetExceededError) as exc:
            async with runtime.model_attempt(
                provider="openai",
                model="m",
                prompt_chars=1,
                requested_output_tokens=1,
            ):
                pass
        assert exc.value.dimension == "model_attempts"
        assert runtime.snapshot()["usage"]["model_attempts"] == 1

    asyncio.run(_run())


def test_execution_control_honours_durable_cancel_before_provider_call():
    async def _run():
        state = {"cancelled": True}
        runtime = ExecutionControlRuntime(cancel_callback=lambda: state["cancelled"])
        with pytest.raises(ExecutionCancelledError):
            async with runtime.model_attempt(
                provider="anthropic",
                model="m",
                prompt_chars=1,
            ):
                raise AssertionError("provider call must not start")
        assert runtime.snapshot()["usage"]["model_attempts"] == 0

    asyncio.run(_run())


def test_execution_control_records_provider_usage_without_prompts_or_secrets():
    runtime = ExecutionControlRuntime()
    runtime.record_result(
        {
            "text": "完成",
            "usage": {"input_tokens": 12, "output_tokens": 3},
        }
    )
    snapshot = runtime.snapshot()
    assert snapshot["usage"]["actual_input_tokens"] == 12
    assert snapshot["usage"]["actual_output_tokens"] == 3
    assert snapshot["usage"]["actual_output_chars"] == 2
    assert "text" not in str(snapshot)
