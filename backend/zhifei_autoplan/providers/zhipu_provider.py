from __future__ import annotations

import asyncio
from typing import Dict, Any
from zhipuai import ZhipuAI

from backend.zhifei_autoplan.providers.base import BaseProvider


class ZhipuProvider(BaseProvider):
    name = "zhipu"

    def __init__(self, api_key: str, model: str):
        self.client = ZhipuAI(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))

        def _call() -> Dict[str, Any]:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content if resp and resp.choices else ""
            return {"provider": self.name, "model": self.model, "text": text}

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
