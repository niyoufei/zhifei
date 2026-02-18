from __future__ import annotations

from typing import Dict, Any
import requests

from backend.zhifei_autoplan.providers.base import BaseProvider


class TencentProvider(BaseProvider):
    name = "tencent"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"model": self.model, "prompt": prompt}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=60)
        data = resp.json()
        text = data.get("text", "")
        return {"provider": self.name, "model": self.model, "text": text}
