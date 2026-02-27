from __future__ import annotations

import asyncio
from typing import Dict, Any
import anthropic

from backend.zhifei_autoplan.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))

        def _call() -> Dict[str, Any]:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text if msg and msg.content else ""
            return {"provider": self.name, "model": self.model, "text": text}

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
