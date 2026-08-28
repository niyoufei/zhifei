from __future__ import annotations

import asyncio
from typing import Dict, Any
from google import genai

from backend.zhifei_autoplan.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "google"

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        timeout_sec = float(kwargs.get("timeout_sec", kwargs.get("timeout", 180)))
        use_stream = bool(kwargs.get("stream", False))

        def _call() -> Any:
            stream_factory = getattr(self.client.models, "generate_content_stream", None)
            if use_stream and callable(stream_factory):
                chunks: list[str] = []
                for event in stream_factory(
                    model=self.model_name,
                    contents=prompt,
                ):
                    text = getattr(event, "text", None)
                    if isinstance(text, str) and text:
                        chunks.append(text)
                return "".join(chunks)
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

        try:
            resp = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout_sec)
            text = resp if isinstance(resp, str) else (resp.text if hasattr(resp, "text") else "")
            return {
                "provider": self.name,
                "model": self.model_name,
                "text": text,
                "streamed": bool(use_stream),
            }
        except asyncio.TimeoutError:
            return {"provider": self.name, "model": self.model_name, "text": "", "error": "timeout"}
        except Exception as e:
            return {"provider": self.name, "model": self.model_name, "text": "", "error": repr(e)}
