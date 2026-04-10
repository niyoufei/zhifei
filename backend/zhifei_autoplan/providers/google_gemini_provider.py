from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, Any
import httpx
from google import genai
from google.genai.types import HttpOptions

from backend.zhifei_autoplan.providers.base import BaseProvider


def _provider_trust_env() -> bool:
    return str(os.environ.get("ZF_PROVIDER_TRUST_ENV") or "0").strip().lower() in {"1", "true", "yes", "on"}


class GeminiProvider(BaseProvider):
    name = "google"

    def __init__(self, api_key: str, model: str):
        self._http_client = httpx.Client(trust_env=_provider_trust_env())
        self._http_async_client = httpx.AsyncClient(trust_env=_provider_trust_env())
        self.client = genai.Client(
            api_key=api_key,
            http_options=HttpOptions(
                httpxClient=self._http_client,
                httpxAsyncClient=self._http_async_client,
            ),
        )
        self.model_name = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))
        max_output_tokens = kwargs.get("max_output_tokens")
        temperature = kwargs.get("temperature")
        client_request_id = str(kwargs.get("client_request_id") or "").strip()
        used_key_alias = str(kwargs.get("used_key_alias") or "").strip()

        def _call() -> Any:
            started = time.perf_counter()
            cfg: Dict[str, Any] = {}
            try:
                mot = int(max_output_tokens)
                if mot > 0:
                    cfg["max_output_tokens"] = mot
            except Exception:
                pass
            try:
                if temperature is not None:
                    cfg["temperature"] = float(temperature)
            except Exception:
                pass
            if cfg:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=cfg,
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                return resp, latency_ms
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            return resp, latency_ms

        try:
            resp, latency_ms = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
            text = resp.text if hasattr(resp, "text") else ""
            usage = getattr(resp, "usage_metadata", None)
            usage_dict = {}
            if usage is not None:
                try:
                    usage_dict = {
                        "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
                        "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
                        "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
                    }
                except Exception:
                    usage_dict = {}
            return {
                "provider": self.name,
                "model": self.model_name,
                "text": text,
                "client_request_id": client_request_id or None,
                "used_key_alias": used_key_alias or None,
                "latency_ms": latency_ms,
                "token_usage": usage_dict or None,
            }
        except asyncio.TimeoutError:
            return {
                "provider": self.name,
                "model": self.model_name,
                "text": "",
                "used_key_alias": used_key_alias or None,
                "error": "timeout",
            }
        except Exception as e:
            return {
                "provider": self.name,
                "model": self.model_name,
                "text": "",
                "used_key_alias": used_key_alias or None,
                "error": repr(e),
            }
