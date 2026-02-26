from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def _extract_ascii_tokens(data: bytes, limit: int = 120) -> List[str]:
    text = data.decode("latin-1", errors="ignore")
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_./-]{3,}", text)
    out: List[str] = []
    seen = set()
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
        if len(out) >= limit:
            break
    return out


def _load_companion_exports(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    stem = path.stem
    parent = path.parent
    candidates = sorted(
        [
            p
            for p in parent.glob(f"{stem}*")
            if p.is_file() and p != path and p.suffix.lower() in {".json", ".csv", ".txt", ".md"}
        ],
        key=lambda p: p.name,
    )[:20]
    for p in candidates:
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            raw = ""
        if not raw:
            continue
        rec: Dict[str, Any] = {"file": p.name, "suffix": p.suffix.lower(), "size": p.stat().st_size}
        if p.suffix.lower() == ".json":
            try:
                payload = json.loads(raw)
                rec["json_keys"] = list(payload.keys())[:20] if isinstance(payload, dict) else []
            except Exception:
                rec["json_keys"] = []
        rec["snippet"] = raw[:280]
        out.append(rec)
    return out


def parse_revit_payload(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    tokens = _extract_ascii_tokens(data)
    companion_exports = _load_companion_exports(path)
    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha,
        "native_supported": False,
        "parse_mode": "metadata_and_companion_exports",
        "model_tokens": tokens[:80],
        "companion_exports": companion_exports,
        "revit_version_hint": next((t for t in tokens if "Revit" in t), ""),
    }

