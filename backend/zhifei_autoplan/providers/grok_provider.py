from __future__ import annotations

import asyncio
from typing import Dict, Any

from openai import OpenAI

from backend.zhifei_autoplan.providers.base import BaseProvider


class GrokProvider(BaseProvider):
    name = "grok"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.x.ai/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))

        def _call() -> Dict[str, Any]:
            resp = self.client.responses.create(model=self.model, input=prompt)
            text = resp.output_text if hasattr(resp, "output_text") else str(resp)
            return {"provider": self.name, "model": self.model, "text": text}

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
