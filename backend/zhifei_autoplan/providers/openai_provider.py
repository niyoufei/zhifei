from __future__ import annotations

import asyncio
from typing import Dict, Any
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

        def _request():
            request = {"model": self.model, "input": prompt, "timeout": timeout_sec}
            if max_tokens is not None:
                request["max_output_tokens"] = max(8, min(16384, int(max_tokens)))
            return self.client.responses.create(**request)

        # The OpenAI SDK call is synchronous. Do not block the API event loop.
        resp = await asyncio.wait_for(asyncio.to_thread(_request), timeout=timeout_sec + 5.0)
        text = resp.output_text if hasattr(resp, "output_text") else str(resp)
        result = {"provider": self.name, "model": self.model, "text": text}
        if not str(text or "").strip():
            result["error"] = "no_visible_text"
        return result
