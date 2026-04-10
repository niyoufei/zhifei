from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from backend.zhifei_autoplan.workspace import workspace_paths

BOQ_DIR = Path("backend/data/autoplan")
BOQ_DIR.mkdir(parents=True, exist_ok=True)
BOQ_DATA = BOQ_DIR / "boq_data.json"
PROJECTS_DIR = BOQ_DIR / "projects"


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    pid = (project_id or "").strip()
    out = re.sub(r"[^A-Za-z0-9_\\-\\.\\u4e00-\\u9fff]+", "_", pid)
    out = out.strip("_")
    return (out[:limit] or "project").strip("_")


def _workspace_projects_dir(workspace_dir: str | None) -> Path | None:
    if not workspace_dir:
        return None
    return workspace_paths(workspace_dir)["projects"]


def boq_data_path(project_id: str | None = None, workspace_dir: str | None = None) -> Path:
    """
    Resolve storage path.
    - project_id is None/blank: legacy global path backend/data/autoplan/boq_data.json
    - project_id provided: backend/data/autoplan/projects/<project_id>/boq_data.json
    """
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    projects_dir = _workspace_projects_dir(workspace_dir)
    if not pid:
        if projects_dir is not None:
            return projects_dir / "global" / "boq_data.json"
        return BOQ_DATA
    safe = _safe_project_id(pid)
    return (projects_dir or PROJECTS_DIR) / safe / "boq_data.json"


def save_boq_data(
    payload: Dict[str, Any],
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> str:
    path = boq_data_path(project_id=project_id, workspace_dir=workspace_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_boq_data(
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> Optional[Dict[str, Any]]:
    path = boq_data_path(project_id=project_id, workspace_dir=workspace_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
