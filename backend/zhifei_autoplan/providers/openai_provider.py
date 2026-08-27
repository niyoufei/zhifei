from __future__ import annotations

import asyncio
from typing import Dict, Any
import httpx
from openai import OpenAI

from backend.zhifei_autoplan.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = max(5.0, float(kwargs.get("timeout", 180.0) or 180.0))
        max_tokens = kwargs.get("max_tokens")
        use_stream = bool(kwargs.get("stream", False))

        def _request():
            request = {"model": self.model, "input": prompt}
            if max_tokens is not None:
                # The Responses API rejects values below 16.  Admission uses a
                # deliberately tiny probe, so clamping at the API minimum is
                # essential or a healthy backup route is falsely quarantined.
                request["max_output_tokens"] = max(16, min(16384, int(max_tokens)))
            stream_factory = getattr(self.client.responses, "stream", None)
            if use_stream and callable(stream_factory):
                stream_timeout = httpx.Timeout(
                    timeout_sec,
                    connect=min(15.0, timeout_sec),
                    read=min(45.0, timeout_sec),
                    write=min(45.0, timeout_sec),
                )
                chunks: list[str] = []
                with stream_factory(**request, timeout=stream_timeout) as stream:
                    for event in stream:
                        if str(getattr(event, "type", "")) == "response.output_text.delta":
                            delta = getattr(event, "delta", None)
                            if isinstance(delta, str) and delta:
                                chunks.append(delta)
                    get_final_response = getattr(stream, "get_final_response", None)
                    final_response = (
                        get_final_response() if callable(get_final_response) else None
                    )
                return {"stream_text": "".join(chunks), "response": final_response}
            return self.client.responses.create(**request, timeout=timeout_sec)

        # The OpenAI SDK call is synchronous. Do not block the API event loop.
        resp = await asyncio.wait_for(asyncio.to_thread(_request), timeout=timeout_sec + 5.0)
        if isinstance(resp, dict) and "stream_text" in resp:
            final_response = resp.get("response")
            text = str(resp.get("stream_text") or "")
        else:
            final_response = resp
            text = resp.output_text if hasattr(resp, "output_text") else str(resp)
        incomplete = getattr(final_response, "incomplete_details", None)
        incomplete_reason = str(
            getattr(incomplete, "reason", None)
            or (incomplete.get("reason") if isinstance(incomplete, dict) else "")
            or ""
        ).strip()
        response_status = str(getattr(final_response, "status", None) or "").strip()
        normalized_status = response_status.lower()
        normalized_reason = incomplete_reason.lower()
        terminal_error = None
        if normalized_reason in {"max_output_tokens", "max_tokens"}:
            stop_reason = "max_tokens"
        elif normalized_reason in {"content_filter", "content_filtered", "refusal", "safety"}:
            stop_reason = normalized_reason
            terminal_error = "content_filtered"
        elif normalized_status in {"failed", "cancelled", "canceled", "incomplete"}:
            stop_reason = normalized_reason or normalized_status
            terminal_error = "provider_error"
        elif normalized_status == "completed":
            stop_reason = "end_turn"
        else:
            stop_reason = normalized_reason or normalized_status or None
        result = {
            "provider": self.name,
            "model": self.model,
            "text": text,
            "streamed": bool(use_stream),
            "stop_reason": stop_reason,
        }
        if terminal_error:
            # Partial text from an incomplete/refused response is not a
            # successful chapter and must never cross the checkpoint gate.
            result["error"] = terminal_error
        elif not str(text or "").strip():
            result["error"] = "no_visible_text"
        return result
