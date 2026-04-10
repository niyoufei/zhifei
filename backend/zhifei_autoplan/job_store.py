from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

from backend.zhifei_autoplan.workspace import workspace_paths, workspace_root

JOB_DIR = Path("backend/data/autoplan/jobs")
JOB_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR = Path("backend/data/autoplan/archive/jobs")


def _job_dir(workspace_dir: str | None = None) -> Path:
    if workspace_dir:
        return workspace_paths(workspace_dir)["jobs"]
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    return JOB_DIR


def _archive_dir(workspace_dir: str | None = None) -> Path:
    if workspace_dir:
        return workspace_paths(workspace_dir)["jobs_archive"]
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    return ARCHIVE_DIR


def _strip_archived_suffixes(stem: str) -> str:
    value = str(stem or "").strip()
    while value.endswith(".archived"):
        value = value[: -len(".archived")]
    return value


def _is_archived_tombstone_path(path: Path) -> bool:
    return ".archived" in str(path.stem or "")


def _tombstone_path(job_dir: Path, job_id: str) -> Path:
    return job_dir / f"{job_id}.archived.json"


def normalize_archived_tombstones(*, workspace_dir: str | None = None) -> int:
    job_dir = _job_dir(workspace_dir)
    if not job_dir.exists():
        return 0
    grouped: dict[str, list[Path]] = {}
    for path in job_dir.glob("*.json"):
        if not _is_archived_tombstone_path(path):
            continue
        job_id = _strip_archived_suffixes(path.stem)
        if not job_id:
            continue
        grouped.setdefault(job_id, []).append(path)

    changed = 0
    for job_id, candidates in grouped.items():
        canonical = _tombstone_path(job_dir, job_id)
        if len(candidates) == 1 and candidates[0] == canonical:
            continue
        try:
            preferred = max(
                candidates,
                key=lambda p: (
                    float(p.stat().st_mtime),
                    1 if p == canonical else 0,
                ),
            )
        except Exception:
            preferred = candidates[0]

        if preferred != canonical:
            try:
                canonical.write_text(preferred.read_text(encoding="utf-8"), encoding="utf-8")
                changed += 1
            except Exception:
                continue

        for path in candidates:
            if path == canonical:
                continue
            try:
                path.unlink(missing_ok=True)
                changed += 1
            except Exception:
                continue
    return changed


def _scrub_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, raw in value.items():
            skey = str(key)
            if skey in {"api_key", "api_keys", "image_api_key"}:
                continue
            if skey == "provider_chain" and isinstance(raw, list):
                cleaned_chain = []
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    cleaned_item = {
                        k: v
                        for k, v in item.items()
                        if str(k) not in {"api_key"}
                    }
                    cleaned_chain.append(_scrub_sensitive_payload(cleaned_item))
                out[skey] = cleaned_chain
                continue
            out[skey] = _scrub_sensitive_payload(raw)
        return out
    if isinstance(value, list):
        return [_scrub_sensitive_payload(v) for v in value]
    return value


def create_job(
    payload: Dict[str, Any],
    user_id: int | None = None,
    request_signature: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> str:
    now = time.time()
    job_id = uuid.uuid4().hex
    resolved_workspace = str(workspace_dir or (payload or {}).get("workspace_dir") or "").strip() or None
    rec = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "heartbeat_at": now,
        "payload": _scrub_sensitive_payload(payload if isinstance(payload, dict) else {}),
        "request_signature": str(request_signature or "").strip() or None,
        "workspace_dir": resolved_workspace,
        "result": {},
        "error": None,
    }
    _write_job(rec, workspace_dir=resolved_workspace)
    return job_id


def update_job(job_id: str, workspace_dir: str | None = None, **kwargs: Any) -> Dict[str, Any]:
    rec = get_job(job_id, workspace_dir=workspace_dir) or {"job_id": job_id}
    rec.update(kwargs)
    rec["updated_at"] = time.time()
    if str(rec.get("status") or "").strip().lower() in {"queued", "running"}:
        rec["heartbeat_at"] = rec.get("heartbeat_at") or rec["updated_at"]
    if "heartbeat_at" in kwargs:
        rec["heartbeat_at"] = kwargs.get("heartbeat_at")
    resolved_workspace = str(
        kwargs.get("workspace_dir") or rec.get("workspace_dir") or workspace_dir or ""
    ).strip() or None
    rec["workspace_dir"] = resolved_workspace
    _write_job(rec, workspace_dir=resolved_workspace)
    return rec


def get_job(job_id: str, workspace_dir: str | None = None) -> Optional[Dict[str, Any]]:
    path = _job_dir(workspace_dir) / f"{job_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _candidate_job_dirs(*, workspace_dir: str | None = None, include_all_workspaces: bool = False) -> list[Path]:
    if workspace_dir:
        return [_job_dir(workspace_dir)]

    dirs: list[Path] = [_job_dir(None)]
    if include_all_workspaces:
        try:
            for child in workspace_root().iterdir():
                if not child.is_dir():
                    continue
                dirs.append(child / "jobs")
        except Exception:
            pass

    unique: list[Path] = []
    seen: set[str] = set()
    for path in dirs:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def list_jobs(
    limit: int = 50,
    user_id: int | None = None,
    workspace_dir: str | None = None,
    *,
    include_all_workspaces: bool = False,
) -> list[dict]:
    jobs = []
    files: list[Path] = []
    for job_dir in _candidate_job_dirs(workspace_dir=workspace_dir, include_all_workspaces=include_all_workspaces):
        if not job_dir.exists():
            continue
        files.extend(job_dir.glob("*.json"))
    files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    for p in files:
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if user_id is not None and rec.get("user_id") != user_id:
                continue
            jobs.append(rec)
        except Exception:
            continue
        if len(jobs) >= limit:
            break
    return jobs


def _signature_scrub(value: Any) -> Any:
    volatile_keys = {
        "api_key",
        "api_keys",
        "image_api_key",
        "_variant_plan",
        "_variant_ids",
        "request_id",
        "trace_id",
    }
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k in sorted(value.keys()):
            key = str(k)
            if key in volatile_keys:
                continue
            out[key] = _signature_scrub(value.get(k))
        return out
    if isinstance(value, list):
        return [_signature_scrub(v) for v in value]
    return value


def compute_job_signature(payload: Dict[str, Any] | None) -> str:
    cleaned = _signature_scrub(payload if isinstance(payload, dict) else {})
    raw = json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def find_reusable_job(
    request_signature: str,
    *,
    statuses: tuple[str, ...] = ("queued", "running", "done"),
    max_age_seconds: int = 12 * 3600,
    user_id: int | None = None,
    workspace_dir: str | None = None,
) -> Optional[Dict[str, Any]]:
    wanted = str(request_signature or "").strip()
    if not wanted:
        return None
    allowed = {str(x or "").strip().lower() for x in statuses if str(x or "").strip()}
    now = time.time()
    for rec in list_jobs(limit=2000, user_id=user_id, workspace_dir=workspace_dir):
        status = str(rec.get("status") or "").strip().lower()
        if status not in allowed:
            continue
        ts = rec.get("updated_at") or rec.get("created_at") or 0
        try:
            age = max(0.0, now - float(ts))
        except Exception:
            age = float(max_age_seconds + 1)
        if max_age_seconds > 0 and age > max_age_seconds:
            continue
        sig = str(rec.get("request_signature") or "").strip()
        if not sig:
            sig = compute_job_signature(rec.get("payload") if isinstance(rec.get("payload"), dict) else {})
        if sig != wanted:
            continue
        if status == "done":
            paths = [p for p in _iter_result_paths(rec.get("result") if isinstance(rec.get("result"), dict) else {}) if p]
            if paths and not any(Path(p).exists() for p in paths):
                continue
        return rec
    return None


def has_result_artifacts(result: Dict[str, Any] | None) -> bool:
    paths = [p for p in _iter_result_paths(result if isinstance(result, dict) else {}) if p]
    return bool(paths) and any(Path(p).exists() for p in paths)


def discover_recent_jobs(
    *,
    limit: int = 8,
    statuses: tuple[str, ...] = ("queued", "running", "done"),
    max_age_seconds: int = 24 * 3600,
    user_id: int | None = None,
    lease_seconds: int = 15 * 60,
    workspace_dir: str | None = None,
) -> list[dict]:
    wanted_limit = max(1, int(limit or 1))
    allowed = {str(x or "").strip().lower() for x in statuses if str(x or "").strip()}
    if not allowed:
        return []
    now = time.time()
    fetch_limit = max(wanted_limit * 12, 50)
    rows: list[dict] = []
    for raw in list_jobs(limit=min(fetch_limit, 2000), user_id=user_id, workspace_dir=workspace_dir):
        rec = raw
        job_id = str(rec.get("job_id") or "").strip()
        status = str(rec.get("status") or "").strip().lower()
        if status == "running" and job_id:
            rec = reconcile_job_runtime(
                job_id,
                lease_seconds=lease_seconds,
                workspace_dir=workspace_dir,
            ) or rec
            status = str(rec.get("status") or "").strip().lower()
        if status not in allowed:
            continue
        ts = rec.get("updated_at") or rec.get("created_at") or 0
        try:
            age = max(0.0, now - float(ts))
        except Exception:
            age = float(max_age_seconds + 1)
        if max_age_seconds > 0 and age > max_age_seconds:
            continue
        if status == "done" and not has_result_artifacts(rec.get("result") if isinstance(rec.get("result"), dict) else {}):
            continue
        rows.append(rec)
        if len(rows) >= wanted_limit:
            break
    return rows


def _iter_result_paths(result: Dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not isinstance(result, dict):
        return out
    for k in (
        "json",
        "docx",
        "compare_docx",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    ):
        f = result.get(k)
        if isinstance(f, list):
            out.extend([str(x).strip() for x in f if str(x).strip()])
        elif f:
            out.append(str(f).strip())
    return out


def _safe_pid(value: Any) -> int | None:
    try:
        n = int(value)
        return n if n > 0 else None
    except Exception:
        return None


def _is_process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except Exception:
        return False
    try:
        proc = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=0.5,
            check=False,
        )
        stat = str(proc.stdout or "").strip().upper()
        if proc.returncode == 0 and stat and "Z" in stat:
            return False
    except Exception:
        pass
    try:
        proc = subprocess.run(
            ["ps", "-o", "command=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=0.5,
            check=False,
        )
        command = str(proc.stdout or "").strip().lower()
        if proc.returncode == 0 and "<defunct>" in command:
            return False
    except Exception:
        pass
    return True


def _resolve_worker_pid(rec: Dict[str, Any]) -> int | None:
    worker = rec.get("worker") if isinstance(rec.get("worker"), dict) else {}
    pid = _safe_pid(worker.get("pid"))
    if pid:
        return pid
    runtime = rec.get("agent_runtime") if isinstance(rec.get("agent_runtime"), dict) else {}
    return _safe_pid(runtime.get("worker_pid"))


def _archive_job_bundle(
    rec: Dict[str, Any],
    archive_dir: Path | None = None,
    *,
    workspace_dir: str | None = None,
) -> str | None:
    job_id = str(rec.get("job_id") or "").strip()
    if not job_id:
        return None
    archive_root = archive_dir or _archive_dir(workspace_dir or str(rec.get("workspace_dir") or "").strip() or None)
    archive_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d")
    out = archive_root / f"{stamp}_{job_id}.zip"
    try:
        with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("job.json", json.dumps(rec, ensure_ascii=False, indent=2))
            added: set[str] = set()
            for raw in _iter_result_paths(rec.get("result") if isinstance(rec.get("result"), dict) else {}):
                p = Path(raw)
                if not p.exists() or not p.is_file():
                    continue
                arc = f"artifacts/{p.name}"
                if arc in added:
                    arc = f"artifacts/{p.stem}_{len(added)}{p.suffix}"
                added.add(arc)
                zf.write(p, arcname=arc)
        return str(out)
    except Exception:
        return None


def _remove_downloaded_actions_run(job_id: str) -> None:
    job_key = str(job_id or "").strip()
    if not job_key:
        return
    target = Path("build") / "actions_runs" / job_key
    if not target.exists():
        return
    try:
        shutil.rmtree(target, ignore_errors=True)
    except Exception:
        pass


def reconcile_job_runtime(
    job_id: str,
    lease_seconds: int = 15 * 60,
    now_ts: float | None = None,
    *,
    workspace_dir: str | None = None,
) -> Optional[Dict[str, Any]]:
    rec = get_job(job_id, workspace_dir=workspace_dir)
    if not rec:
        return None
    status = str(rec.get("status") or "").strip().lower()
    if status != "running":
        return rec
    now = float(now_ts or time.time())
    lease = max(60, int(lease_seconds or 0))
    heartbeat = rec.get("heartbeat_at") or rec.get("updated_at") or rec.get("created_at") or now
    try:
        heartbeat_ts = float(heartbeat)
    except Exception:
        heartbeat_ts = now
    age = max(0.0, now - heartbeat_ts)
    pid = _resolve_worker_pid(rec)
    alive = _is_process_alive(pid)
    if age > lease and not alive:
        worker = dict(rec.get("worker") or {}) if isinstance(rec.get("worker"), dict) else {}
        worker["alive"] = False
        worker["lease_seconds"] = lease
        worker["heartbeat_age_seconds"] = int(age)
        return update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="failed",
            error=f"stale_worker_timeout(lease={lease}s, heartbeat_age={int(age)}s)",
            worker=worker,
            progress={
                "percent": int((rec.get("progress") or {}).get("percent") or 0),
                "stage": "failed",
                "detail": "worker stale timeout",
            },
        )
    worker = dict(rec.get("worker") or {}) if isinstance(rec.get("worker"), dict) else {}
    if worker:
        worker["alive"] = bool(alive)
        worker["lease_seconds"] = lease
        worker["heartbeat_age_seconds"] = int(age)
        return update_job(job_id, workspace_dir=workspace_dir, worker=worker)
    return rec


def mark_stale_running_jobs(
    lease_seconds: int = 15 * 60,
    limit: int = 2000,
    *,
    workspace_dir: str | None = None,
) -> int:
    now = time.time()
    fixed = 0
    cnt = 0
    for p in sorted(_job_dir(workspace_dir).glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if cnt >= max(1, int(limit)):
            break
        cnt += 1
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(rec.get("status") or "").strip().lower() != "running":
            continue
        before = str(rec.get("status") or "")
        after = reconcile_job_runtime(
            str(rec.get("job_id") or ""),
            lease_seconds=lease_seconds,
            now_ts=now,
            workspace_dir=workspace_dir,
        ) or {}
        if before == "running" and str(after.get("status") or "").strip().lower() == "failed":
            fixed += 1
    return fixed


def cleanup_jobs(
    older_than_seconds: int = 7 * 24 * 3600,
    *,
    archive: bool = False,
    archive_dir: Path | None = None,
    workspace_dir: str | None = None,
) -> int:
    removed = 0
    now = time.time()
    normalize_archived_tombstones(workspace_dir=workspace_dir)
    for p in _job_dir(workspace_dir).glob("*.json"):
        if _is_archived_tombstone_path(p):
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            ts = rec.get("updated_at") or rec.get("created_at") or 0
            if now - float(ts) > older_than_seconds:
                archived_at = None
                if archive:
                    archived_at = _archive_job_bundle(
                        rec,
                        archive_dir=archive_dir,
                        workspace_dir=workspace_dir,
                    )
                # 删除关联产物
                for raw in _iter_result_paths(rec.get("result") if isinstance(rec.get("result"), dict) else {}):
                    try:
                        Path(raw).unlink(missing_ok=True)
                    except Exception:
                        pass
                _remove_downloaded_actions_run(str(rec.get("job_id") or ""))
                if archived_at:
                    # keep a tiny tombstone for traceability
                    job_id = _strip_archived_suffixes(str(rec.get("job_id") or "").strip())
                    if not job_id:
                        job_id = str(rec.get("job_id") or "").strip()
                    tomb = {
                        "job_id": job_id,
                        "status": rec.get("status"),
                        "created_at": rec.get("created_at"),
                        "updated_at": rec.get("updated_at"),
                        "archived_at": archived_at,
                    }
                    try:
                        _tombstone_path(p.parent, job_id).write_text(
                            json.dumps(tomb, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                    except Exception:
                        pass
                p.unlink(missing_ok=True)
                removed += 1
        except Exception:
            continue
    return removed


def _write_job(rec: Dict[str, Any], workspace_dir: str | None = None) -> None:
    job_id = rec.get("job_id")
    if not job_id:
        return
    resolved_workspace = str(workspace_dir or rec.get("workspace_dir") or "").strip() or None
    path = _job_dir(resolved_workspace) / f"{job_id}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
