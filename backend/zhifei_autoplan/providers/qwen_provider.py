from __future__ import annotations

from typing import Dict, Any
import dashscope

from backend.zhifei_autoplan.providers.base import BaseProvider


class QwenProvider(BaseProvider):
    name = "qwen"

    def __init__(self, api_key: str, model: str):
        dashscope.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        resp = dashscope.Generation.call(
            model=self.model,
            prompt=prompt,
        )
        text = resp.output.get("text", "") if resp and resp.output else ""
        return {"provider": self.name, "model": self.model, "text": text}
