from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def normalize_gemini_image_model(model: str | None) -> str:
    """
    User may call it "banana"/"nano-banana". We map to official model ids.
    """
    m = (model or "").strip()
    if not m:
        return "gemini-2.5-flash-image"
    low = m.lower()
    if low in {"banana", "nano-banana", "nanobanana", "nano_banana"}:
        return "gemini-2.5-flash-image"
    if "pro" in low and "image" in low:
        return m
    if low in {"banana-pro", "banana_pro"}:
        return "gemini-3-pro-image-preview"
    return m


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
    except Exception as e:
        return {"ok": False, "paths": [], "text": "", "error": repr(e), "model": model_id}
    finally:
        _close_gemini_client_safely(client)

    images, text = _extract_image_parts(resp)
    paths: List[str] = []
    for data, mime in images[:3]:
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

    return {"ok": bool(paths), "paths": paths, "text": text, "model": model_id, "provider": "google"}
