from __future__ import annotations

from typing import Dict, Any
from openai import OpenAI

from backend.zhifei_autoplan.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        resp = self.client.responses.create(model=self.model, input=prompt)
        text = resp.output_text if hasattr(resp, "output_text") else str(resp)
        return {"provider": self.name, "model": self.model, "text": text}
