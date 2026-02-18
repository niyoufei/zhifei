from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


PROJECTS_DIR = Path("backend/data/autoplan/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    pid = (project_id or "").strip()
    out = re.sub(r"[^A-Za-z0-9_\\-\\.\\u4e00-\\u9fff]+", "_", pid)
    out = out.strip("_")
    return (out[:limit] or "project").strip("_")


def project_dir(project_id: str) -> Path:
    safe = _safe_project_id(project_id)
    p = PROJECTS_DIR / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def branding_path(project_id: str) -> Path:
    return project_dir(project_id) / "branding.json"


def load_branding(project_id: str) -> Optional[Dict[str, Any]]:
    pid = str(project_id or "").strip()
    if not pid:
        return None
    p = branding_path(pid)
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def save_branding(project_id: str, branding: Dict[str, Any]) -> str:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("missing project_id")
    p = branding_path(pid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(branding or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def update_branding(project_id: str, update: Dict[str, Any], merge: bool = True) -> str:
    pid = str(project_id or "").strip()
    if not pid:
        raise ValueError("missing project_id")
    base = load_branding(pid) or {}
    out = dict(base) if merge else {}
    for k, v in (update or {}).items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        out[k] = v
    return save_branding(pid, out)

