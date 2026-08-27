from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import os
import threading
import time
from typing import Dict, Any
import anthropic
import httpx

from backend.zhifei_autoplan.claude_usage import (
    estimate_claude_cost,
    normalize_claude_usage,
    record_claude_usage,
)
from backend.zhifei_autoplan.providers.base import BaseProvider


_CACHE_WARM_LOCK = threading.Lock()
_CACHE_WARM_FLIGHTS: dict[str, concurrent.futures.Future[bool]] = {}
_CACHE_READY_UNTIL: dict[str, float] = {}
_ALLOWED_CACHE_MODES = {"disabled", "automatic", "explicit_prefix", "section"}


def _cache_warm_key(model: str, stable: str, shared: str) -> str:
    payload = "\x00".join((model, stable, shared)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _claim_cache_warm(key: str) -> tuple[bool, concurrent.futures.Future[bool] | None]:
    now = time.monotonic()
    with _CACHE_WARM_LOCK:
        expired = [item for item, deadline in _CACHE_READY_UNTIL.items() if deadline <= now]
        for item in expired:
            _CACHE_READY_UNTIL.pop(item, None)
        if _CACHE_READY_UNTIL.get(key, 0.0) > now:
            return False, None
        pending = _CACHE_WARM_FLIGHTS.get(key)
        if pending is not None:
            return False, pending
        future: concurrent.futures.Future[bool] = concurrent.futures.Future()
        _CACHE_WARM_FLIGHTS[key] = future
        return True, future


def _finish_cache_warm(
    key: str,
    future: concurrent.futures.Future[bool] | None,
    *,
    ready: bool,
) -> None:
    if future is None:
        return
    with _CACHE_WARM_LOCK:
        if ready:
            _CACHE_READY_UNTIL[key] = time.monotonic() + 300.0
        if _CACHE_WARM_FLIGHTS.get(key) is future:
            _CACHE_WARM_FLIGHTS.pop(key, None)
        if not future.done():
            future.set_result(bool(ready))


def _extract_text_blocks(content: Any) -> str:
    """Return only user-visible text from an Anthropic content-block response.

    Extended-thinking models may return ``ThinkingBlock`` or
    ``RedactedThinkingBlock`` entries before one or more ``TextBlock`` entries.
    Those non-text blocks intentionally have no ``text`` attribute and must not
    be treated as generated document content.
    """

    if isinstance(content, str):
        return content.strip()
    if not content:
        return ""

    chunks: list[str] = []
    for block in content:
        if isinstance(block, str):
            value = block
        elif isinstance(block, dict):
            value = block.get("text")
        else:
            value = getattr(block, "text", None)
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())
    return "\n\n".join(chunks).strip()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        started = time.monotonic()
        timeout_sec = max(5.0, float(kwargs.get("timeout", 180.0) or 180.0))
        max_tokens = max(8, min(16384, int(kwargs.get("max_tokens", 8192) or 8192)))
        use_stream = bool(kwargs.get("stream", False))
        stable_system_prompt = str(
            kwargs.get("stable_system_prompt") or kwargs.get("system_prompt") or ""
        ).strip()
        shared_context_prompt = str(kwargs.get("shared_context_prompt") or "").strip()
        project_id = kwargs.get("project_id")
        task_type = kwargs.get("task_type")
        raw_cache_mode = kwargs.get("cache_mode")
        cache_mode = (
            "disabled"
            if raw_cache_mode in (None, "")
            else str(raw_cache_mode).strip().lower()
        )
        if cache_mode not in _ALLOWED_CACHE_MODES:
            raise ValueError("anthropic_cache_mode_invalid")
        cache_enabled = str(
            os.environ.get("ZHIFEI_ANTHROPIC_PROMPT_CACHE_ENABLED", "1")
        ).strip().lower() not in {"0", "false", "no", "off"}

        request: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
        }
        explicit_breakpoints = 0
        automatic_cache = False
        system_blocks: list[Dict[str, Any]] = []
        if stable_system_prompt:
            block: Dict[str, Any] = {"type": "text", "text": stable_system_prompt}
            if cache_enabled and cache_mode != "disabled":
                block["cache_control"] = {"type": "ephemeral"}
                explicit_breakpoints += 1
            system_blocks.append(block)
            request["system"] = system_blocks

        content_blocks: list[Dict[str, Any]] = []
        if shared_context_prompt:
            shared_block: Dict[str, Any] = {
                "type": "text",
                "text": shared_context_prompt,
            }
            # Section generation must leave the final chapter instruction after
            # the last breakpoint.  Its stable and medium-lived prefixes use
            # explicit 5-minute breakpoints; the chapter request itself remains
            # ordinary uncached input.
            if cache_enabled and cache_mode in {"explicit_prefix", "section"}:
                shared_block["cache_control"] = {"type": "ephemeral"}
                explicit_breakpoints += 1
            content_blocks.append(shared_block)
        content_blocks.append({"type": "text", "text": str(prompt or "")})
        request["messages"] = [{"role": "user", "content": content_blocks}]

        if cache_enabled and cache_mode == "automatic":
            # Generic/multi-turn caching is explicit opt-in. No ttl is supplied,
            # so Anthropic's 5-minute default is used.
            request["cache_control"] = {"type": "ephemeral"}
            automatic_cache = True
        if not cache_enabled or cache_mode == "disabled":
            cache_strategy = "disabled"
        elif cache_mode in {"explicit_prefix", "section"}:
            cache_strategy = "explicit_stable_and_context_5m"
        elif stable_system_prompt:
            cache_strategy = "explicit_stable_plus_automatic_5m"
        else:
            cache_strategy = "automatic_5m"

        # Automatic caching uses one of Anthropic's four slots.  This adapter
        # intentionally stays at <=3 even when both stable and shared prefixes
        # are present.
        breakpoint_slots = explicit_breakpoints + (1 if automatic_cache else 0)
        if breakpoint_slots > 3:
            raise ValueError("anthropic_cache_breakpoint_budget_exceeded")

        def _request():
            stream_factory = getattr(self.client.messages, "stream", None)
            if use_stream and callable(stream_factory):
                stream_timeout = httpx.Timeout(
                    timeout_sec,
                    connect=min(15.0, timeout_sec),
                    read=min(45.0, timeout_sec),
                    write=min(45.0, timeout_sec),
                )
                chunks: list[str] = []
                with stream_factory(
                    **request,
                    timeout=stream_timeout,
                ) as stream:
                    for text in stream.text_stream:
                        if isinstance(text, str) and text:
                            chunks.append(text)
                    get_final_message = getattr(stream, "get_final_message", None)
                    final_message = get_final_message() if callable(get_final_message) else None
                return {"stream_text": "".join(chunks), "message": final_message}
            return self.client.messages.create(
                **request,
                timeout=timeout_sec,
            )

        cache_warm_key = ""
        cache_warm_leader = False
        cache_warm_future: concurrent.futures.Future[bool] | None = None
        cache_warm_finished = False
        prewarm_performed = False
        prewarm_effective = False
        prewarm_usage = normalize_claude_usage(None)
        prewarm_error_type: str | None = None
        prewarm_duration_ms = 0
        if (
            cache_enabled
            and cache_mode in {"section", "explicit_prefix"}
            and (stable_system_prompt or shared_context_prompt)
        ):
            cache_warm_key = _cache_warm_key(
                self.model,
                stable_system_prompt,
                shared_context_prompt,
            )
            while True:
                cache_warm_leader, cache_warm_future = _claim_cache_warm(
                    cache_warm_key
                )
                if cache_warm_leader or cache_warm_future is None:
                    break
                try:
                    cache_ready = await asyncio.wait_for(
                        asyncio.shield(asyncio.wrap_future(cache_warm_future)),
                        timeout=timeout_sec + 5.0,
                    )
                except (asyncio.TimeoutError, TimeoutError):
                    break
                if cache_ready:
                    cache_warm_future = None
                    break
                # The leader failed or returned no cache usage evidence. Loop
                # so exactly one waiter becomes the next warm-up leader.

        if cache_warm_leader:
            # A normal chapter response can take several minutes. Waiting for
            # that full response before releasing identical-prefix followers
            # consumes their chapter deadlines and turns cache warm-up into a
            # reliability bottleneck. Anthropic supports max_tokens=0 cache
            # pre-warming: write the explicit prefix without generating text,
            # then let the real chapter requests proceed concurrently.
            prewarm_performed = True
            prewarm_started = time.monotonic()
            prewarm_content: list[Dict[str, Any]] = []
            if shared_context_prompt:
                prewarm_content.append(
                    {
                        "type": "text",
                        "text": shared_context_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                )
            # The placeholder is deliberately after the final explicit
            # breakpoint, so it is not part of the reusable prefix.
            prewarm_content.append({"type": "text", "text": "cache warmup"})
            prewarm_request: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": 0,
                "messages": [{"role": "user", "content": prewarm_content}],
            }
            if system_blocks:
                prewarm_request["system"] = system_blocks
            try:
                prewarm_message = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.messages.create,
                        **prewarm_request,
                        timeout=timeout_sec,
                    ),
                    timeout=timeout_sec + 5.0,
                )
                prewarm_usage = normalize_claude_usage(
                    getattr(prewarm_message, "usage", None)
                )
                prewarm_effective = bool(
                    prewarm_usage.get("cache_creation_input_tokens")
                    or prewarm_usage.get("cache_read_input_tokens")
                )
                prewarm_duration_ms = int(
                    (time.monotonic() - prewarm_started) * 1000
                )
                record_claude_usage(
                    model=self.model,
                    usage=prewarm_usage,
                    duration_ms=prewarm_duration_ms,
                    project_id=project_id,
                    task_type=f"{task_type or 'generic_completion'}_cache_prewarm",
                    status="success",
                    streamed=False,
                    cache_strategy="explicit_prefix_prewarm_5m",
                )
            except asyncio.CancelledError:
                _finish_cache_warm(
                    cache_warm_key,
                    cache_warm_future,
                    ready=False,
                )
                cache_warm_finished = True
                raise
            except BaseException as exc:
                prewarm_error_type = type(exc).__name__
                prewarm_duration_ms = int(
                    (time.monotonic() - prewarm_started) * 1000
                )
                record_claude_usage(
                    model=self.model,
                    usage={},
                    duration_ms=prewarm_duration_ms,
                    project_id=project_id,
                    task_type=f"{task_type or 'generic_completion'}_cache_prewarm",
                    status="error",
                    error_type=prewarm_error_type,
                    streamed=False,
                    cache_strategy="explicit_prefix_prewarm_5m",
                )
            finally:
                # A failed/too-short prewarm must not trigger one identical
                # prewarm per waiting chapter. The actual requests remain the
                # source of truth and can still create or read the cache.
                if not cache_warm_finished:
                    _finish_cache_warm(
                        cache_warm_key,
                        cache_warm_future,
                        ready=True,
                    )
                    cache_warm_finished = True

        api_started = time.monotonic()
        try:
            # The Anthropic SDK is synchronous. Keep it off the FastAPI event
            # loop so status endpoints remain responsive during generation.
            raw = await asyncio.wait_for(
                asyncio.to_thread(_request), timeout=timeout_sec + 5.0
            )
        except BaseException as exc:
            if cache_warm_leader and not cache_warm_finished:
                _finish_cache_warm(
                    cache_warm_key,
                    cache_warm_future,
                    ready=False,
                )
            record_claude_usage(
                model=self.model,
                usage={},
                duration_ms=int((time.monotonic() - api_started) * 1000),
                project_id=project_id,
                task_type=task_type,
                status="error",
                error_type=type(exc).__name__,
                streamed=use_stream,
                cache_strategy=cache_strategy,
            )
            raise

        if isinstance(raw, dict) and "stream_text" in raw:
            msg = raw.get("message")
            text = str(raw.get("stream_text") or "")
        else:
            msg = raw
            text = _extract_text_blocks(getattr(msg, "content", None)) if msg else ""
        stop_reason = str(getattr(msg, "stop_reason", None) or "").strip() or None
        terminal_error = None
        if stop_reason == "refusal":
            terminal_error = "content_filtered"
        elif stop_reason == "model_context_window_exceeded":
            terminal_error = "invalid_request"
        elif stop_reason in {"pause_turn", "tool_use"}:
            # This provider adapter is used for plain-text chapter generation;
            # an unfinished agent/tool turn is not a valid terminal chapter.
            terminal_error = "provider_error"
        elif not text:
            terminal_error = "no_visible_text"
        usage = normalize_claude_usage(getattr(msg, "usage", None) if msg else None)
        if cache_warm_leader and not cache_warm_finished:
            _finish_cache_warm(
                cache_warm_key,
                cache_warm_future,
                ready=bool(
                    usage.get("cache_creation_input_tokens")
                    or usage.get("cache_read_input_tokens")
                ),
            )
        cost = estimate_claude_cost(self.model, usage)
        duration_ms = int((time.monotonic() - api_started) * 1000)
        logical_duration_ms = int((time.monotonic() - started) * 1000)
        usage_event = record_claude_usage(
            model=self.model,
            usage=usage,
            duration_ms=duration_ms,
            project_id=project_id,
            task_type=task_type,
            status="error" if terminal_error else "success",
            error_type=terminal_error,
            streamed=use_stream,
            cache_strategy=cache_strategy,
        )
        cache_active = cache_enabled and cache_mode != "disabled"
        result = {
            "provider": self.name,
            "model": self.model,
            "text": text,
            "streamed": bool(use_stream),
            "stop_reason": stop_reason,
            "usage": usage,
            "request_duration_ms": duration_ms,
            "logical_duration_ms": logical_duration_ms,
            "estimated_cost_usd": cost["estimated_cost_usd"],
            "estimated_no_cache_cost_usd": cost["estimated_no_cache_cost_usd"],
            "estimated_savings_ratio": cost["estimated_savings_ratio"],
            "cache": {
                "enabled": cache_active,
                "strategy": cache_strategy,
                "ttl": "5m" if cache_active else None,
                "automatic": automatic_cache,
                "explicit_breakpoints": explicit_breakpoints,
                "breakpoint_slots": breakpoint_slots,
                "cache_hit_ratio": usage["cache_hit_ratio"],
                "prewarm_performed": prewarm_performed,
                "prewarm_effective": prewarm_effective,
                "prewarm_cache_creation_input_tokens": prewarm_usage[
                    "cache_creation_input_tokens"
                ],
                "prewarm_cache_read_input_tokens": prewarm_usage[
                    "cache_read_input_tokens"
                ],
                "prewarm_duration_ms": prewarm_duration_ms,
                "prewarm_error_type": prewarm_error_type,
                "log_persisted": bool(usage_event.get("log_persisted")),
            },
        }
        if terminal_error:
            result["error"] = terminal_error
        return result
