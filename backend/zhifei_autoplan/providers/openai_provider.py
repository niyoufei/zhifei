from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, Any
import httpx
from openai import OpenAI

from backend.zhifei_autoplan.providers.base import BaseProvider


def _provider_trust_env() -> bool:
    return str(os.environ.get("ZF_PROVIDER_TRUST_ENV") or "0").strip().lower() in {"1", "true", "yes", "on"}


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self._http_client = httpx.Client(trust_env=_provider_trust_env())
        self.client = OpenAI(api_key=api_key, http_client=self._http_client)
        self.model = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))
        max_output_tokens = kwargs.get("max_output_tokens")
        temperature = kwargs.get("temperature")
        prompt_cache_key = str(kwargs.get("prompt_cache_key") or "").strip()
        prompt_cache_retention = str(kwargs.get("prompt_cache_retention") or "").strip()
        client_request_id = str(kwargs.get("client_request_id") or "").strip()
        used_key_alias = str(kwargs.get("used_key_alias") or "").strip()
        service_tier = str(kwargs.get("service_tier") or "").strip()

        def _call() -> Dict[str, Any]:
            started = time.perf_counter()
            req: Dict[str, Any] = {"model": self.model, "input": prompt}
            try:
                mot = int(max_output_tokens)
                if mot > 0:
                    req["max_output_tokens"] = mot
            except Exception:
                pass
            try:
                if temperature is not None:
                    req["temperature"] = float(temperature)
            except Exception:
                pass
            if prompt_cache_key:
                req["prompt_cache_key"] = prompt_cache_key
            if prompt_cache_retention:
                req["prompt_cache_retention"] = prompt_cache_retention
            if service_tier:
                req["service_tier"] = service_tier
            if client_request_id:
                req["extra_headers"] = {"X-Client-Request-Id": client_request_id}
            resp = self.client.responses.create(**req)
            text = resp.output_text if hasattr(resp, "output_text") else str(resp)
            usage = getattr(resp, "usage", None)
            usage_dict = {}
            if usage is not None:
                try:
                    usage_dict = {
                        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                    }
                except Exception:
                    usage_dict = {}
            cached_tokens = 0
            try:
                input_details = getattr(usage, "input_tokens_details", None)
                cached_tokens = int(getattr(input_details, "cached_tokens", 0) or 0)
            except Exception:
                cached_tokens = 0
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "provider": self.name,
                "model": self.model,
                "text": text,
                "request_id": str(getattr(resp, "_request_id", "") or "").strip() or None,
                "client_request_id": client_request_id or None,
                "service_tier": str(getattr(resp, "service_tier", "") or service_tier or "").strip() or None,
                "used_key_alias": used_key_alias or None,
                "latency_ms": latency_ms,
                "token_usage": usage_dict or None,
                "cache_key": prompt_cache_key or None,
                "cache_hit": bool(cached_tokens > 0),
                "cached_tokens": cached_tokens,
            }

        return await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
