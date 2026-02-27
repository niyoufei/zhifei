from __future__ import annotations

import asyncio
from typing import Dict, Any
import dashscope

from backend.zhifei_autoplan.providers.base import BaseProvider


class QwenProvider(BaseProvider):
    name = "qwen"

    def __init__(self, api_key: str, model: str):
        dashscope.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))

        def _call() -> Dict[str, Any]:
            resp = dashscope.Generation.call(
                model=self.model,
                prompt=prompt,
            )
            text = resp.output.get("text", "") if resp and resp.output else ""
            return {"provider": self.name, "model": self.model, "text": text}

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
