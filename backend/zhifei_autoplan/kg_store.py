from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


KG_DIR = Path("backend/data/kg")
KG_DIR.mkdir(parents=True, exist_ok=True)
KG_INDEX = KG_DIR / "kg_index.jsonl"
KG_ACTIVE = KG_DIR / "active_kg.json"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def save_kg_bytes(content: bytes, original_name: str) -> Dict[str, Any]:
    sha = _sha256_bytes(content)
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    safe_name = original_name.replace("/", "_")
    fname = f"kg_{ts}_{sha[:8]}_{safe_name}"
    path = KG_DIR / fname
    path.write_bytes(content)

    meta = {
        "kg_id": sha,
        "file_name": original_name,
        "stored_as": str(path),
        "size_bytes": len(content),
        "sha256": sha,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    with KG_INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return meta


def list_kg() -> List[Dict[str, Any]]:
    if not KG_INDEX.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in KG_INDEX.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def set_active_kg(kg_id: str) -> Dict[str, Any]:
    rec = None
    for it in list_kg()[::-1]:
        if it.get("kg_id") == kg_id:
            rec = it
            break
    if rec is None:
        raise ValueError("kg_id not found")
    KG_ACTIVE.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def get_active_kg() -> Optional[Dict[str, Any]]:
    if not KG_ACTIVE.exists():
        return None
    try:
        return json.loads(KG_ACTIVE.read_text(encoding="utf-8"))
    except Exception:
        return None
