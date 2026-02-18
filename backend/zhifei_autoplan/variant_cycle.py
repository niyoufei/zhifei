from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path("backend/data/autoplan")
PROJECTS_DIR = BASE_DIR / "projects"
GLOBAL_STATE_PATH = BASE_DIR / "variant_cycle_global.json"


def _safe_project_id(pid: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_\-\.\u4e00-\u9fff]+", "_", (pid or "").strip())
    out = out.strip("._")
    return out or "default"


def _state_path(project_id: str | None) -> Path:
    pid = (project_id or "").strip()
    if pid:
        p = PROJECTS_DIR / _safe_project_id(pid) / "variant_cycle.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    GLOBAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return GLOBAL_STATE_PATH


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"next_variant_id": 1}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {"next_variant_id": 1}


def _save_state(path: Path, st: Dict[str, Any]) -> None:
    st = dict(st or {})
    st["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_int(v: Any) -> int | None:
    try:
        n = int(v)
        return n
    except Exception:
        return None


def reserve_variant_ids(
    *,
    project_id: str | None,
    count: int,
    explicit_variant_id: int | None = None,
    explicit_template_id: str | None = None,
) -> List[int]:
    """
    Reserve variant ids for one generation request.

    Behavior:
    - If explicit variant/template is provided, do not consume cycle state.
    - Otherwise consume project-scoped cycle state and return sequential ids
      so template selection follows A->B->C across runs.
    """
    n = max(1, int(count or 1))
    ev = _to_int(explicit_variant_id)
    et = str(explicit_template_id or "").strip()

    if et:
        base = ev if (ev and ev > 0) else 1
        return [base + i for i in range(n)]

    if ev and ev > 0:
        return [ev + i for i in range(n)]

    path = _state_path(project_id)
    st = _load_state(path)
    start = _to_int(st.get("next_variant_id")) or 1
    if start <= 0:
        start = 1
    ids = [start + i for i in range(n)]
    st["next_variant_id"] = start + n
    st["project_id"] = (project_id or "").strip() or None
    _save_state(path, st)
    return ids


def peek_next_variant_id(project_id: str | None) -> int:
    path = _state_path(project_id)
    st = _load_state(path)
    n = _to_int(st.get("next_variant_id")) or 1
    return n if n > 0 else 1
