"""Local-only HTTP transport for the three ComfyUI coordinator ports."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Protocol
from urllib import request

from image_generation.runtime.single_shot_submission_authorization import (
    _strict_json_bytes,
)


LOCAL_COMFYUI_BASE_URL = "http://127.0.0.1:8188"
HTTP_TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_RESPONSE_READ_CHUNK_BYTES = 64 * 1024


class _OpenerPort(Protocol):
    def open(self, request_value: request.Request, *, timeout: float) -> Any: ...


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _build_default_opener() -> _OpenerPort:
    return request.build_opener(
        request.ProxyHandler({}),
        _NoRedirectHandler(),
    )


def _read_limited_body(response: Any) -> bytes:
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        read_size = min(
            _RESPONSE_READ_CHUNK_BYTES,
            MAX_RESPONSE_BYTES + 1 - total_bytes,
        )
        chunk = response.read(read_size)
        if not isinstance(chunk, bytes):
            raise ValueError("ComfyUI response body must be bytes")
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total_bytes += len(chunk)
        if total_bytes > MAX_RESPONSE_BYTES:
            raise ValueError("ComfyUI response exceeded the maximum size")


def _reject_nonstandard_json_constant(_value: str) -> None:
    raise ValueError("non-standard JSON constant")


class LocalComfyUITransport:
    """Expose only health, queue-state, and one-prompt submission operations."""

    def __init__(
        self,
        base_url: str = LOCAL_COMFYUI_BASE_URL,
        *,
        opener: _OpenerPort | None = None,
    ) -> None:
        if base_url not in {LOCAL_COMFYUI_BASE_URL, f"{LOCAL_COMFYUI_BASE_URL}/"}:
            raise ValueError(f"base_url must be exactly {LOCAL_COMFYUI_BASE_URL}")
        self._base_url = LOCAL_COMFYUI_BASE_URL
        self._opener = _build_default_opener() if opener is None else opener

    def check(self) -> bool:
        """Return whether the fixed local ComfyUI service has the expected shape."""

        request_value = request.Request(
            f"{self._base_url}/system_stats",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            response_data = self._load_json(request_value)
        except ValueError:
            return False
        return (
            isinstance(response_data, dict)
            and "system" in response_data
            and "devices" in response_data
        )

    def get_state(self) -> dict:
        """Return only the coordinator queue fields in normalized form."""

        request_value = request.Request(
            f"{self._base_url}/queue",
            headers={"Accept": "application/json"},
            method="GET",
        )
        response_data = self._load_json(request_value)
        if not isinstance(response_data, dict):
            raise ValueError("queue response must be a JSON object")
        running = response_data.get("queue_running")
        pending = response_data.get("queue_pending")
        if not isinstance(running, list) or not isinstance(pending, list):
            raise ValueError(
                "queue response must contain queue_running and queue_pending lists"
            )
        return {
            "running": deepcopy(running),
            "pending": deepcopy(pending),
        }

    def submit(self, api_prompt: dict) -> dict:
        """Submit one deep-copied API prompt and return only its prompt id."""

        if not isinstance(api_prompt, dict):
            raise ValueError("api_prompt must be a dict")
        try:
            request_body = _strict_json_bytes(
                {"prompt": deepcopy(api_prompt)},
                "api_prompt",
            )
        except Exception:
            raise ValueError("api_prompt must be JSON serializable") from None

        request_value = request.Request(
            f"{self._base_url}/prompt",
            data=request_body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        response_data = self._load_json(request_value)
        if not isinstance(response_data, dict):
            raise ValueError("submit response must be a JSON object")
        prompt_id = response_data.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ValueError(
                "submit response prompt_id must be a non-empty string"
            )
        return {"prompt_id": prompt_id}

    def _load_json(self, request_value: request.Request) -> object:
        try:
            with self._opener.open(
                request_value,
                timeout=HTTP_TIMEOUT_SECONDS,
            ) as response:
                status = getattr(response, "status", None)
                if type(status) is not int or not 200 <= status < 300:
                    raise ValueError("ComfyUI HTTP request failed")

                content_type = response.headers.get("Content-Type", "")
                if content_type.split(";", 1)[0].strip().lower() != "application/json":
                    raise ValueError(
                        "ComfyUI response must use application/json"
                    )

                raw_body = _read_limited_body(response)
                try:
                    return json.loads(
                        raw_body.decode("utf-8"),
                        parse_constant=_reject_nonstandard_json_constant,
                    )
                except (UnicodeDecodeError, ValueError):
                    raise ValueError(
                        "ComfyUI response must be valid UTF-8 JSON"
                    ) from None
        except ValueError:
            raise
        except Exception:
            raise ValueError("ComfyUI HTTP request failed") from None


__all__ = [
    "LocalComfyUITransport",
]
