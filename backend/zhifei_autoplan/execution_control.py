from __future__ import annotations

import asyncio
import threading
import time
import weakref
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict


DEFAULT_ANTHROPIC_MAX_TOKENS = 8192


def model_request_input_chars(prompt: Any, request_kwargs: Dict[str, Any] | None = None) -> int:
    """Count every text block that the provider adapter will transmit."""

    kwargs = request_kwargs if isinstance(request_kwargs, dict) else {}
    stable = kwargs.get("stable_system_prompt")
    if stable in (None, ""):
        stable = kwargs.get("system_prompt")
    shared = kwargs.get("shared_context_prompt")
    return sum(len(str(value or "")) for value in (prompt, stable, shared))


def model_request_output_tokens(
    provider: Any,
    request_kwargs: Dict[str, Any] | None = None,
) -> int:
    """Return the output-token reservation used by the provider adapter.

    ``AnthropicProvider`` defaults to 8,192 output tokens. Reserving zero when
    a caller omits ``max_tokens`` would let a run bypass its output-token
    budget, so the execution controller mirrors that adapter default.
    """

    kwargs = request_kwargs if isinstance(request_kwargs, dict) else {}
    value = kwargs.get("max_tokens")
    if value in (None, ""):
        value = kwargs.get("max_output_tokens")
    if value in (None, ""):
        value = (
            DEFAULT_ANTHROPIC_MAX_TOKENS
            if str(provider or "").strip().lower() == "anthropic"
            else 0
        )
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


class ExecutionCancelledError(RuntimeError):
    """Raised before a provider call when the durable job is cancelled."""

    def __init__(self, stage: str = "model_call") -> None:
        self.stage = str(stage or "model_call")
        super().__init__(f"execution_cancelled:{self.stage}")


class ExecutionBudgetExceededError(RuntimeError):
    """Raised before a provider call would cross a run-level hard budget."""

    def __init__(self, *, dimension: str, limit: int, attempted: int) -> None:
        self.dimension = str(dimension)
        self.limit = int(limit)
        self.attempted = int(attempted)
        super().__init__(
            f"execution_budget_exceeded:{self.dimension}:"
            f"attempted={self.attempted}:limit={self.limit}"
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": "EXECUTION_BUDGET_EXCEEDED",
            "dimension": self.dimension,
            "limit": self.limit,
            "attempted": self.attempted,
            "message": "本次任务的模型调用安全预算已用尽，已停止继续调用。",
        }


def _positive_int(value: Any, default: int, *, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = int(default)
    return max(1, min(int(maximum), parsed))


class ExecutionControlRuntime:
    """One shared concurrency, budget and cancellation controller per job.

    The runtime intentionally counts provider *attempts*, rather than logical
    chapter calls.  Retries and fallback providers therefore consume the same
    finite budget and cannot multiply work invisibly.
    """

    def __init__(
        self,
        *,
        max_concurrency: int = 4,
        max_model_attempts: int = 256,
        max_input_chars: int = 24_000_000,
        max_requested_output_tokens: int = 3_000_000,
        cancel_callback: Callable[[], bool] | None = None,
    ) -> None:
        self.max_concurrency = _positive_int(max_concurrency, 4, maximum=32)
        self.max_model_attempts = _positive_int(max_model_attempts, 256, maximum=10_000)
        self.max_input_chars = _positive_int(max_input_chars, 24_000_000, maximum=2_000_000_000)
        self.max_requested_output_tokens = _positive_int(
            max_requested_output_tokens,
            3_000_000,
            maximum=200_000_000,
        )
        self._cancel_callback = cancel_callback
        # Background generation and professional rendering currently execute
        # in successive ``asyncio.run`` loops.  A semaphore is loop-bound once
        # it has waited, so keep one semaphore per event loop while sharing the
        # same counters/budgets across the whole job.
        self._semaphores: weakref.WeakKeyDictionary[
            asyncio.AbstractEventLoop, asyncio.Semaphore
        ] = weakref.WeakKeyDictionary()
        self._lock = threading.RLock()
        self._started_at = time.time()
        self._attempts = 0
        self._input_chars = 0
        self._requested_output_tokens = 0
        self._actual_input_tokens = 0
        self._actual_uncached_input_tokens = 0
        self._cache_creation_input_tokens = 0
        self._cache_read_input_tokens = 0
        self._actual_output_tokens = 0
        self._actual_output_chars = 0
        self._active = 0
        self._peak_active = 0
        self._provider_attempts: Dict[str, int] = {}

    def _is_cancelled(self) -> bool:
        callback = self._cancel_callback
        if callback is None:
            return False
        try:
            return bool(callback())
        except Exception:
            # An unavailable cancellation readback must not fabricate a cancel.
            return False

    def raise_if_cancelled(self, stage: str = "model_call") -> None:
        if self._is_cancelled():
            raise ExecutionCancelledError(stage)

    def _semaphore_for_running_loop(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        with self._lock:
            semaphore = self._semaphores.get(loop)
            if semaphore is None:
                semaphore = asyncio.Semaphore(self.max_concurrency)
                self._semaphores[loop] = semaphore
            return semaphore

    async def _acquire(self) -> asyncio.Semaphore:
        semaphore = self._semaphore_for_running_loop()
        while True:
            self.raise_if_cancelled("waiting_for_model_slot")
            try:
                await asyncio.wait_for(semaphore.acquire(), timeout=0.5)
                return semaphore
            except asyncio.TimeoutError:
                continue

    def _reserve_attempt(
        self,
        *,
        provider: str,
        prompt_chars: int,
        requested_output_tokens: int,
    ) -> Dict[str, Any]:
        prompt_chars = max(0, int(prompt_chars or 0))
        requested_output_tokens = max(0, int(requested_output_tokens or 0))
        with self._lock:
            checks = (
                ("model_attempts", self._attempts + 1, self.max_model_attempts),
                ("input_chars", self._input_chars + prompt_chars, self.max_input_chars),
                (
                    "requested_output_tokens",
                    self._requested_output_tokens + requested_output_tokens,
                    self.max_requested_output_tokens,
                ),
            )
            for dimension, attempted, limit in checks:
                if attempted > limit:
                    raise ExecutionBudgetExceededError(
                        dimension=dimension,
                        limit=limit,
                        attempted=attempted,
                    )

            self._attempts += 1
            self._input_chars += prompt_chars
            self._requested_output_tokens += requested_output_tokens
            self._active += 1
            self._peak_active = max(self._peak_active, self._active)
            provider_key = str(provider or "unknown").strip().lower() or "unknown"
            self._provider_attempts[provider_key] = self._provider_attempts.get(provider_key, 0) + 1
            return {
                "attempt_number": self._attempts,
                "provider": provider_key,
                "prompt_chars": prompt_chars,
                "requested_output_tokens": requested_output_tokens,
            }

    def _release_attempt(self, semaphore: asyncio.Semaphore) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
        semaphore.release()

    @asynccontextmanager
    async def model_attempt(
        self,
        *,
        provider: str,
        model: str,
        prompt_chars: int,
        requested_output_tokens: int = 0,
    ):
        semaphore = await self._acquire()
        reserved = False
        try:
            self.raise_if_cancelled("before_model_call")
            receipt = self._reserve_attempt(
                provider=provider,
                prompt_chars=prompt_chars,
                requested_output_tokens=requested_output_tokens,
            )
            reserved = True
            receipt["model"] = str(model or "")
            yield receipt
        except BaseException:
            raise
        finally:
            if reserved:
                self._release_attempt(semaphore)
            else:
                semaphore.release()

    def record_result(self, result: Dict[str, Any] | None) -> None:
        if not isinstance(result, dict):
            return
        usage = result.get("usage")
        if not isinstance(usage, dict):
            usage = result.get("usage_metadata")
        usage = usage if isinstance(usage, dict) else {}

        def _usage_int(*keys: str) -> int:
            for key in keys:
                try:
                    value = int(usage.get(key) or 0)
                except Exception:
                    value = 0
                if value > 0:
                    return value
            return 0

        uncached_input_tokens = _usage_int("input_tokens", "prompt_tokens", "prompt_token_count")
        cache_creation_input_tokens = _usage_int("cache_creation_input_tokens")
        cache_read_input_tokens = _usage_int("cache_read_input_tokens")
        input_tokens = (
            uncached_input_tokens
            + cache_creation_input_tokens
            + cache_read_input_tokens
        )
        output_tokens = _usage_int("output_tokens", "completion_tokens", "candidates_token_count")
        output_chars = len(str(result.get("text") or ""))
        with self._lock:
            self._actual_input_tokens += input_tokens
            self._actual_uncached_input_tokens += uncached_input_tokens
            self._cache_creation_input_tokens += cache_creation_input_tokens
            self._cache_read_input_tokens += cache_read_input_tokens
            self._actual_output_tokens += output_tokens
            self._actual_output_chars += output_chars

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "schema_version": "execution-control-v1",
                "limits": {
                    "max_concurrency": self.max_concurrency,
                    "max_model_attempts": self.max_model_attempts,
                    "max_input_chars": self.max_input_chars,
                    "max_requested_output_tokens": self.max_requested_output_tokens,
                },
                "usage": {
                    "model_attempts": self._attempts,
                    "input_chars": self._input_chars,
                    "requested_output_tokens": self._requested_output_tokens,
                    "actual_input_tokens": self._actual_input_tokens,
                    "actual_uncached_input_tokens": self._actual_uncached_input_tokens,
                    "cache_creation_input_tokens": self._cache_creation_input_tokens,
                    "cache_read_input_tokens": self._cache_read_input_tokens,
                    "cache_hit_ratio": round(
                        self._cache_read_input_tokens / self._actual_input_tokens,
                        6,
                    )
                    if self._actual_input_tokens
                    else 0.0,
                    "actual_output_tokens": self._actual_output_tokens,
                    "actual_output_chars": self._actual_output_chars,
                    "active": self._active,
                    "peak_active": self._peak_active,
                    "provider_attempts": dict(sorted(self._provider_attempts.items())),
                },
                "cancelled": self._is_cancelled(),
                "elapsed_seconds": max(0.0, round(time.time() - self._started_at, 3)),
            }
