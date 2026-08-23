from __future__ import annotations

import asyncio
from typing import Dict, Any
import anthropic

from backend.zhifei_autoplan.providers.base import BaseProvider


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
        timeout_sec = max(5.0, float(kwargs.get("timeout", 180.0) or 180.0))
        max_tokens = max(8, min(16384, int(kwargs.get("max_tokens", 8192) or 8192)))

        def _request():
            return self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout_sec,
            )

        # The Anthropic SDK is synchronous. Keep it off the FastAPI event loop so
        # progress/status endpoints remain responsive while a chapter is revised.
        msg = await asyncio.wait_for(asyncio.to_thread(_request), timeout=timeout_sec + 5.0)
        text = _extract_text_blocks(getattr(msg, "content", None)) if msg else ""
        result = {"provider": self.name, "model": self.model, "text": text}
        if not text:
            result["error"] = "no_visible_text"
        return result
