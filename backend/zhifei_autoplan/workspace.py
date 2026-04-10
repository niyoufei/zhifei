from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict


WORKSPACE_ROOT = Path("backend/data/workspaces")
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
WORKSPACE_META_FILE = ".workspace_meta.json"
GC_STATE_FILE = ".gc_last_run"
DEFAULT_WORKSPACE_TTL_SECONDS = max(
    1800,
    int(float(os.getenv("ZF_WORKSPACE_TTL_SECONDS") or 12 * 3600)),
)
DEFAULT_WORKSPACE_GC_INTERVAL_SECONDS = max(
    60,
    int(float(os.getenv("ZF_WORKSPACE_GC_INTERVAL_SECONDS") or 300)),
)
_SESSION_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def sanitize_session_id(session_id: str | None, *, limit: int = 96) -> str:
    raw = str(session_id or "").strip()
    safe = _SESSION_ID_RE.sub("_", raw).strip("_")
    safe = safe[: max(16, int(limit or 96))]
    return safe or "session"


def workspace_root() -> Path:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_ROOT


def workspace_dir_for_session(session_id: str, *, create: bool = True) -> Path:
    root = workspace_root()
    path = root / sanitize_session_id(session_id)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _workspace_meta_path(workspace_dir: str | Path) -> Path:
    return Path(workspace_dir) / WORKSPACE_META_FILE


def _gc_state_path() -> Path:
    return workspace_root() / GC_STATE_FILE


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def touch_workspace(workspace_dir: str | Path, *, session_id: str | None = None) -> Path:
    path = Path(workspace_dir)
    path.mkdir(parents=True, exist_ok=True)
    now = time.time()
    meta_path = _workspace_meta_path(path)
    meta = _load_json_file(meta_path)
    if "created_at" not in meta:
        meta["created_at"] = now
    meta["last_seen_at"] = now
    meta["session_id"] = sanitize_session_id(session_id or meta.get("session_id") or path.name)
    meta["workspace_dir"] = str(path)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.utime(path, (now, now))
    except Exception:
        pass
    return path


def resolve_workspace_dir(
    *,
    session_id: str | None = None,
    workspace_dir: str | Path | None = None,
    create: bool = True,
) -> Path:
    sid = sanitize_session_id(session_id or Path(str(workspace_dir or "session")).name)
    expected = workspace_dir_for_session(sid, create=create)
    if workspace_dir is not None:
        supplied = Path(workspace_dir)
        if supplied.is_absolute():
            normalized = supplied.resolve()
        else:
            normalized = (Path.cwd() / supplied).resolve()
        if normalized != expected.resolve():
            raise ValueError("workspace_dir must match backend/data/workspaces/{session_id}")
    if create:
        touch_workspace(expected, session_id=sid)
    return expected


def workspace_paths(
    workspace_dir: str | Path,
    *,
    session_id: str | None = None,
    create: bool = True,
) -> Dict[str, Path]:
    root = resolve_workspace_dir(session_id=session_id, workspace_dir=workspace_dir, create=create)
    paths = {
        "root": root,
        "uploads": root / "uploads",
        "extracts": root / "extracts",
        "previews": root / "previews",
        "audit_dir": root / "audit",
        "ingest_audit": root / "audit" / "ingest.jsonl",
        "export_audit": root / "audit" / "export.jsonl",
        "resource_usage_audit": root / "audit" / "resource_usage.jsonl",
        "projects": root / "projects",
        "jobs": root / "jobs",
        "jobs_archive": root / "archive" / "jobs",
        "build": root / "build",
        "stage_runs": root / "build" / "_stage_runs",
        "worker_logs": root / "logs" / "job_workers",
        "media": root / "media",
        "assets": root / "assets",
        "kg_dir": root / "kg",
        "kg_index": root / "kg" / "kg_index.jsonl",
        "active_kg": root / "kg" / "active_kg.json",
        "cache": root / "cache",
        "section_cache": root / "cache" / "sections",
    }
    if create:
        for key, path in paths.items():
            if key.endswith("_audit"):
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir(parents=True, exist_ok=True)
        touch_workspace(root, session_id=session_id)
    return paths


def current_workspace_age_seconds(workspace_dir: str | Path) -> float:
    path = Path(workspace_dir)
    meta = _load_json_file(_workspace_meta_path(path))
    try:
        last_seen = float(meta.get("last_seen_at") or path.stat().st_mtime)
    except Exception:
        last_seen = time.time()
    return max(0.0, time.time() - last_seen)


def cleanup_expired_workspaces(
    *,
    max_age_seconds: int | None = None,
    exclude_workspace: str | Path | None = None,
) -> Dict[str, Any]:
    ttl = max(60, int(max_age_seconds or DEFAULT_WORKSPACE_TTL_SECONDS))
    root = workspace_root()
    now = time.time()
    excluded = Path(exclude_workspace).resolve() if exclude_workspace else None
    removed: list[str] = []
    failed: list[str] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if excluded is not None and child.resolve() == excluded:
            continue
        meta = _load_json_file(_workspace_meta_path(child))
        try:
            last_seen = float(meta.get("last_seen_at") or child.stat().st_mtime)
        except Exception:
            last_seen = now
        age = max(0.0, now - last_seen)
        if age <= ttl:
            continue
        try:
            shutil.rmtree(child)
            removed.append(str(child))
        except Exception:
            failed.append(str(child))
    return {
        "ok": not failed,
        "ttl_seconds": ttl,
        "removed_count": len(removed),
        "removed": removed,
        "failed_count": len(failed),
        "failed": failed,
    }


def maybe_cleanup_expired_workspaces(
    *,
    force: bool = False,
    max_age_seconds: int | None = None,
    min_interval_seconds: int | None = None,
    exclude_workspace: str | Path | None = None,
) -> Dict[str, Any]:
    interval = max(30, int(min_interval_seconds or DEFAULT_WORKSPACE_GC_INTERVAL_SECONDS))
    state_path = _gc_state_path()
    now = time.time()
    if not force:
        state = _load_json_file(state_path)
        try:
            last_run = float(state.get("last_run_at") or 0.0)
        except Exception:
            last_run = 0.0
        if now - last_run < interval:
            return {
                "ok": True,
                "skipped": True,
                "last_run_at": last_run,
                "min_interval_seconds": interval,
            }
    report = cleanup_expired_workspaces(
        max_age_seconds=max_age_seconds,
        exclude_workspace=exclude_workspace,
    )
    state_path.write_text(
        json.dumps(
            {
                "last_run_at": now,
                "report": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    report["skipped"] = False
    report["last_run_at"] = now
    report["min_interval_seconds"] = interval
    return report
