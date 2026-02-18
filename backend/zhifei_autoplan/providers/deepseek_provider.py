from __future__ import annotations

from typing import Dict, Any
import requests

from backend.zhifei_autoplan.providers.base import BaseProvider


class DeepSeekProvider(BaseProvider):
    name = "deepseek"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"provider": self.name, "model": self.model, "text": text}
