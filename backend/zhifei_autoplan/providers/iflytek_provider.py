from __future__ import annotations

import asyncio
from typing import Dict, Any
import requests

from backend.zhifei_autoplan.providers.base import BaseProvider


class IflytekProvider(BaseProvider):
    name = "iflytek"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))
        request_timeout = min(60.0, timeout_sec)

        def _call() -> Dict[str, Any]:
            payload = {"model": self.model, "prompt": prompt}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=request_timeout)
            data = resp.json()
            text = data.get("text", "")
            return {"provider": self.name, "model": self.model, "text": text}

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
