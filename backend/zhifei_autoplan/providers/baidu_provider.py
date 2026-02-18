from __future__ import annotations

from typing import Dict, Any
import requests

from backend.zhifei_autoplan.providers.base import BaseProvider


class BaiduProvider(BaseProvider):
    name = "baidu"

    def __init__(self, api_key: str, secret_key: str, model: str, token_url: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.model = model
        self.token_url = token_url

    def _get_token(self) -> str:
        resp = requests.post(
            self.token_url,
            params={"grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key},
            timeout=30,
        )
        return resp.json().get("access_token", "")

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        token = self._get_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{self.model}?access_token={token}"
        payload = {"messages": [{"role": "user", "content": prompt}]}
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        text = data.get("result", "")
        return {"provider": self.name, "model": self.model, "text": text}
