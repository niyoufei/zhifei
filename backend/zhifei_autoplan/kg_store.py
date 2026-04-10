from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.zhifei_autoplan.workspace import workspace_paths


KG_DIR = Path("backend/data/kg")
KG_INDEX = KG_DIR / "kg_index.jsonl"
KG_ACTIVE = KG_DIR / "active_kg.json"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _kg_paths(workspace_dir: str | None = None) -> Dict[str, Path]:
    if workspace_dir:
        return {
            "dir": workspace_paths(workspace_dir)["kg_dir"],
            "index": workspace_paths(workspace_dir)["kg_index"],
            "active": workspace_paths(workspace_dir)["active_kg"],
        }
    KG_DIR.mkdir(parents=True, exist_ok=True)
    KG_INDEX.parent.mkdir(parents=True, exist_ok=True)
    KG_ACTIVE.parent.mkdir(parents=True, exist_ok=True)
    return {"dir": KG_DIR, "index": KG_INDEX, "active": KG_ACTIVE}


def save_kg_bytes(content: bytes, original_name: str, *, workspace_dir: str | None = None) -> Dict[str, Any]:
    paths = _kg_paths(workspace_dir)
    sha = _sha256_bytes(content)
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    safe_name = original_name.replace("/", "_")
    fname = f"kg_{ts}_{sha[:8]}_{safe_name}"
    path = paths["dir"] / fname
    path.write_bytes(content)

    meta = {
        "kg_id": sha,
        "file_name": original_name,
        "stored_as": str(path),
        "size_bytes": len(content),
        "sha256": sha,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }
    with paths["index"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return meta


def list_kg(*, workspace_dir: str | None = None) -> List[Dict[str, Any]]:
    index_path = _kg_paths(workspace_dir)["index"]
    if not index_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in index_path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def set_active_kg(kg_id: str, *, workspace_dir: str | None = None) -> Dict[str, Any]:
    rec = None
    for it in list_kg(workspace_dir=workspace_dir)[::-1]:
        if it.get("kg_id") == kg_id:
            rec = it
            break
    if rec is None:
        raise ValueError("kg_id not found")
    _kg_paths(workspace_dir)["active"].write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def get_active_kg(*, workspace_dir: str | None = None) -> Optional[Dict[str, Any]]:
    active_path = _kg_paths(workspace_dir)["active"]
    if not active_path.exists():
        return None
    try:
        return json.loads(active_path.read_text(encoding="utf-8"))
    except Exception:
        return None
