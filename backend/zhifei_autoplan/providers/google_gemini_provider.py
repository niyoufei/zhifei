from __future__ import annotations

from typing import Dict, Any
from google import genai

from backend.zhifei_autoplan.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "google"

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        text = resp.text if hasattr(resp, "text") else ""
        return {"provider": self.name, "model": self.model_name, "text": text}
