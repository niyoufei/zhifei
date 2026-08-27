from __future__ import annotations

import base64
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from openai import OpenAI


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _validated_image_payload(data: bytes) -> tuple[bool, dict[str, Any]]:
    try:
        from backend.zhifei_autoplan.media_quality import validate_image_bytes

        receipt = validate_image_bytes(data)
        return bool(receipt.get("ok")), receipt
    except Exception as exc:
        return False, {"ok": False, "errors": ["image_validation_unavailable"], "error": type(exc).__name__}


def normalize_gemini_image_model(model: str | None) -> str:
    """
    User may call it "banana"/"nano-banana". We map to official model ids.
    """
    m = (model or "").strip()
    if not m:
        return "gemini-3-pro-image"
    low = m.lower()
    if low in {"banana", "nano-banana", "nanobanana", "nano_banana"}:
        return "gemini-3-pro-image"
    if "pro" in low and "image" in low:
        return m
    if low in {"banana-pro", "banana_pro"}:
        return "gemini-3-pro-image"
    return m


def normalize_openai_image_model(model: str | None) -> str:
    value = str(model or "").strip()
    if not value or value.lower() in {"latest", "gpt-5.6", "gpt-5.6-sol", "chatgpt-5.6"}:
        return "gpt-image-2"
    return value


def _openai_image_size(aspect_ratio: str | None) -> str:
    ratio = str(aspect_ratio or "16:9").strip().lower()
    if ratio in {"9:16", "3:4", "2:3", "portrait"}:
        return "1024x1536"
    if ratio in {"1:1", "square"}:
        return "1024x1024"
    return "1536x1024"


def _extract_openai_image_bytes(response: Any) -> List[bytes]:
    images: List[bytes] = []
    for item in getattr(response, "data", None) or []:
        encoded = getattr(item, "b64_json", None)
        if not encoded:
            continue
        try:
            images.append(base64.b64decode(encoded))
        except Exception:
            continue
    return images


def generate_image_openai(
    prompt: str,
    api_key: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    input_image_paths: Optional[List[str]] = None,
    out_dir: str | None = None,
) -> Dict[str, Any]:
    """Generate or edit an image with OpenAI's dedicated image model."""
    if not api_key:
        return {"ok": False, "paths": [], "text": "", "error": "missing_api_key"}

    model_id = normalize_openai_image_model(model)
    out_base = Path(out_dir or "backend/data/autoplan/media")
    out_base.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)
    handles: List[Any] = []
    try:
        for raw_path in input_image_paths or []:
            path = Path(str(raw_path or ""))
            if path.exists() and path.is_file():
                handles.append(path.open("rb"))
        common = {
            "model": model_id,
            "prompt": str(prompt or "").strip(),
            "size": _openai_image_size(aspect_ratio),
            "quality": "high",
            "output_format": "png",
            "response_format": "b64_json",
        }
        if handles:
            response = client.images.edit(image=handles, input_fidelity="high", **common)
        else:
            response = client.images.generate(n=1, **common)
    except Exception:
        return {
            "ok": False,
            "paths": [],
            "text": "",
            "error": "IMAGE_PROVIDER_REQUEST_FAILED",
            "model": model_id,
            "provider": "openai",
        }
    finally:
        for handle in handles:
            try:
                handle.close()
            except Exception:
                pass
        try:
            client.close()
        except Exception:
            pass

    paths: List[str] = []
    rejected_payloads: List[Dict[str, Any]] = []
    for data in _extract_openai_image_bytes(response)[:3]:
        valid, receipt = _validated_image_payload(data)
        if not valid:
            rejected_payloads.append(receipt)
            continue
        digest = _sha256(data)[:10]
        out = out_base / f"gen_{int(time.time())}_{digest}.png"
        try:
            out.write_bytes(data)
            paths.append(str(out))
        except Exception:
            continue
    result = {"ok": bool(paths), "paths": paths, "text": "", "model": model_id, "provider": "openai"}
    if rejected_payloads:
        result["rejected_payloads"] = rejected_payloads
    if not paths:
        result["error"] = "invalid_image_payload" if rejected_payloads else "no_image_payload"
    return result


def generate_image(
    *,
    provider: str,
    prompt: str,
    api_key: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    input_image_paths: Optional[List[str]] = None,
    out_dir: str | None = None,
) -> Dict[str, Any]:
    normalized = str(provider or "").strip().lower()
    if normalized == "openai":
        return generate_image_openai(prompt, api_key, model, aspect_ratio, input_image_paths, out_dir)
    if normalized == "google":
        return generate_image_gemini(prompt, api_key, model, aspect_ratio, input_image_paths, out_dir)
    return {
        "ok": False,
        "paths": [],
        "text": "",
        "error": "IMAGE_PROVIDER_UNSUPPORTED",
    }


def _guess_mime(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".png":
        return "image/png"
    if suf in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suf == ".webp":
        return "image/webp"
    if suf == ".gif":
        return "image/gif"
    if suf == ".svg":
        return "image/svg+xml"
    return "application/octet-stream"


def _extract_image_parts(resp) -> Tuple[List[Tuple[bytes, str]], str]:
    images: List[Tuple[bytes, str]] = []
    texts: List[str] = []
    try:
        candidates = getattr(resp, "candidates", None) or []
        if candidates:
            parts = getattr(candidates[0].content, "parts", None) or []
        else:
            parts = getattr(resp, "parts", None) or []
    except Exception:
        parts = []
    for p in parts:
        try:
            if getattr(p, "inline_data", None) is not None:
                inline = p.inline_data
                data = getattr(inline, "data", None)
                mime = getattr(inline, "mime_type", None) or "image/png"
                if isinstance(data, (bytes, bytearray)):
                    images.append((bytes(data), str(mime)))
            if getattr(p, "text", None):
                texts.append(str(p.text))
        except Exception:
            continue
    return images, "\n".join(texts).strip()


class _NoopAsyncCloser:
    async def aclose(self) -> None:
        return None


def _close_gemini_client_safely(client: Any) -> None:
    if client is None:
        return
    try:
        aio_client = getattr(client, "_aio", None)
        api_client = getattr(aio_client, "_api_client", None)
        if api_client is not None and not hasattr(api_client, "_async_httpx_client"):
            setattr(api_client, "_async_httpx_client", _NoopAsyncCloser())
    except Exception:
        pass
    try:
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            close_fn()
    except Exception:
        pass


def generate_image_gemini(
    prompt: str,
    api_key: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    input_image_paths: Optional[List[str]] = None,
    out_dir: str | None = None,
) -> Dict[str, Any]:
    """
    Generate an image using Gemini native image generation models.
    Returns {"ok": bool, "paths": [..], "text": "...", "error": "..."}.
    """
    if not api_key:
        return {"ok": False, "paths": [], "text": "", "error": "missing_api_key"}

    model_id = normalize_gemini_image_model(model)
    out_base = Path(out_dir or "backend/data/autoplan/media")
    out_base.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)

    contents: List[Any] = [str(prompt or "").strip()]
    for p in input_image_paths or []:
        try:
            path = Path(p)
            if not path.exists() or not path.is_file():
                continue
            b = path.read_bytes()
            contents.append(types.Part.from_bytes(data=b, mime_type=_guess_mime(path)))
        except Exception:
            continue

    try:
        resp = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=str(aspect_ratio or "16:9")),
            ),
        )
    except Exception:
        return {
            "ok": False,
            "paths": [],
            "text": "",
            "error": "IMAGE_PROVIDER_REQUEST_FAILED",
            "model": model_id,
        }
    finally:
        _close_gemini_client_safely(client)

    images, text = _extract_image_parts(resp)
    paths: List[str] = []
    rejected_payloads: List[Dict[str, Any]] = []
    for data, mime in images[:3]:
        valid, receipt = _validated_image_payload(data)
        if not valid:
            rejected_payloads.append(receipt)
            continue
        ext = "png"
        if "jpeg" in mime:
            ext = "jpg"
        elif "webp" in mime:
            ext = "webp"
        elif "gif" in mime:
            ext = "gif"
        digest = _sha256(data)[:10]
        fname = f"gen_{int(time.time())}_{digest}.{ext}"
        out = out_base / fname
        try:
            out.write_bytes(data)
            paths.append(str(out))
        except Exception:
            continue

    result = {"ok": bool(paths), "paths": paths, "text": text, "model": model_id, "provider": "google"}
    if rejected_payloads:
        result["rejected_payloads"] = rejected_payloads
    if not paths:
        result["error"] = "invalid_image_payload" if rejected_payloads else "no_image_payload"
    return result
