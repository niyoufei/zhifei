from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.zhifei_autoplan.project_namespace import project_storage_key


BOQ_DIR = Path("backend/data/autoplan")
BOQ_DIR.mkdir(parents=True, exist_ok=True)
BOQ_DATA = BOQ_DIR / "boq_data.json"
PROJECTS_DIR = BOQ_DIR / "projects"


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    return project_storage_key(project_id, limit=limit)


def boq_data_path(project_id: str | None = None) -> Path:
    """
    Resolve storage path.
    - project_id is None/blank: legacy global path backend/data/autoplan/boq_data.json
    - project_id provided: backend/data/autoplan/projects/<project_id>/boq_data.json
    """
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if not pid:
        return BOQ_DATA
    safe = _safe_project_id(pid)
    return PROJECTS_DIR / safe / "boq_data.json"


def save_boq_data(payload: Dict[str, Any], project_id: str | None = None) -> str:
    path = boq_data_path(project_id=project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_boq_data(project_id: str | None = None) -> Optional[Dict[str, Any]]:
    path = boq_data_path(project_id=project_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
