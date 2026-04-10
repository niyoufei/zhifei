from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from backend.zhifei_autoplan.workspace import workspace_paths

PLAN_DIR = Path("backend/data/autoplan")
PLAN_DIR.mkdir(parents=True, exist_ok=True)
PLAN_PATH = PLAN_DIR / "plan.json"
PROJECTS_DIR = PLAN_DIR / "projects"


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    pid = (project_id or "").strip()
    out = re.sub(r"[^A-Za-z0-9_\\-\\.\\u4e00-\\u9fff]+", "_", pid)
    out = out.strip("_")
    return (out[:limit] or "project").strip("_")


def _workspace_projects_dir(workspace_dir: str | None) -> Path | None:
    if not workspace_dir:
        return None
    return workspace_paths(workspace_dir)["projects"]


def plan_path(project_id: str | None = None, workspace_dir: str | None = None) -> Path:
    """
    Resolve storage path.
    - project_id is None/blank: legacy global path backend/data/autoplan/plan.json
    - project_id provided: backend/data/autoplan/projects/<project_id>/plan.json
    """
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    projects_dir = _workspace_projects_dir(workspace_dir)
    if not pid:
        if projects_dir is not None:
            return projects_dir / "global" / "plan.json"
        return PLAN_PATH
    safe = _safe_project_id(pid)
    return (projects_dir or PROJECTS_DIR) / safe / "plan.json"


def save_plan(
    plan: Dict[str, Any],
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> str:
    path = plan_path(project_id=project_id, workspace_dir=workspace_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_plan(
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> Optional[Dict[str, Any]]:
    path = plan_path(project_id=project_id, workspace_dir=workspace_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
