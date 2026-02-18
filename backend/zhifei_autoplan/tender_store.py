from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


TENDER_DIR = Path("backend/data/autoplan")
TENDER_DIR.mkdir(parents=True, exist_ok=True)
TENDER_MATRIX = TENDER_DIR / "tender_matrix.json"
PROJECTS_DIR = TENDER_DIR / "projects"


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    pid = (project_id or "").strip()
    # Allow han chars for readability, but strip odd path characters.
    out = re.sub(r"[^A-Za-z0-9_\\-\\.\\u4e00-\\u9fff]+", "_", pid)
    out = out.strip("_")
    return (out[:limit] or "project").strip("_")


def tender_matrix_path(project_id: str | None = None) -> Path:
    """
    Resolve storage path.
    - project_id is None/blank: legacy global path backend/data/autoplan/tender_matrix.json
    - project_id provided: backend/data/autoplan/projects/<project_id>/tender_matrix.json
    """
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if not pid:
        return TENDER_MATRIX
    safe = _safe_project_id(pid)
    return PROJECTS_DIR / safe / "tender_matrix.json"


def save_tender_matrix(matrix: Dict[str, Any], project_id: str | None = None) -> str:
    path = tender_matrix_path(project_id=project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_tender_matrix(project_id: str | None = None) -> Optional[Dict[str, Any]]:
    path = tender_matrix_path(project_id=project_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
