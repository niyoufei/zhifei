from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Callable, Dict

from backend.zhifei_autoplan.providers.base import BaseProvider


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_TIMEOUT_SECONDS = 60.0

Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]


def _clean_base_url(value: str | None) -> str:
    text = str(value or DEFAULT_BASE_URL).strip().rstrip("/")
    if text in {DEFAULT_BASE_URL, "http://localhost:11434"}:
        return DEFAULT_BASE_URL
    raise ValueError("LOCAL_OLLAMA_LOOPBACK_REQUIRED")


def _clean_timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS
    return max(1.0, min(300.0, timeout))


def build_ollama_chat_payload(
    prompt: str,
    *,
    system_prompt: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    clean_system_prompt = str(system_prompt or "").strip()
    if clean_system_prompt:
        messages.append({"role": "system", "content": clean_system_prompt})
    messages.append({"role": "user", "content": str(prompt or "")})

    payload: dict[str, Any] = {
        "messages": messages,
        "stream": False,
        "think": False,
    }
    if options:
        payload["options"] = dict(options)
    return payload


def parse_ollama_chat_response(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    message = data.get("message")
    if isinstance(message, dict):
        content = str(message.get("content") or "").strip()
        if content:
            return content
    return str(data.get("response") or data.get("content") or "").strip()


def _default_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8", errors="replace"))


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        base_url: str | None = None,
        timeout: float | int | str | None = None,
        transport: Transport | None = None,
    ):
        self.model = str(model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.base_url = _clean_base_url(base_url)
        self.timeout = _clean_timeout(timeout)
        self.transport = transport or _default_transport

    def _fallback(self, error: str) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "text": "",
            "ok": False,
            "error": error,
        }

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        payload = build_ollama_chat_payload(
            prompt,
            system_prompt=kwargs.get("system_prompt"),
            options=kwargs.get("options"),
        )
        payload["model"] = str(kwargs.get("model") or self.model)
        url = f"{self.base_url}/api/chat"
        timeout = _clean_timeout(kwargs.get("timeout", self.timeout))

        try:
            data = self.transport(url, payload, timeout)
        except (TimeoutError, socket.timeout):
            return self._fallback("ollama_timeout")
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            return self._fallback(f"ollama_error:{type(exc).__name__}")
        except Exception as exc:
            return self._fallback(f"ollama_error:{type(exc).__name__}")

        text = parse_ollama_chat_response(data)
        if not text:
            return self._fallback("ollama_empty_response")

        return {
            "provider": self.name,
            "model": str(data.get("model") or payload["model"]) if isinstance(data, dict) else payload["model"],
            "text": text,
            "ok": True,
        }
