from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional


JOB_DIR = Path("backend/data/autoplan/jobs")
_JOB_LOCK = threading.RLock()
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_REDACTED = "[REDACTED]"
_SECRET_KEYS = {
    "api_key",
    "api_keys",
    "image_api_key",
    "secret",
    "client_secret",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "credential",
    "credentials",
    "authorization",
    "x_actions_key",
}


def _valid_job_id(job_id: Any) -> str | None:
    value = str(job_id or "").strip().lower()
    return value if _JOB_ID_RE.fullmatch(value) else None


def _redact_for_disk(value: Any, *, key: str = "") -> Any:
    """Return a JSON-safe copy with credential material removed recursively."""

    normalized_key = str(key or "").strip().lower().replace("-", "_")
    if normalized_key in _SECRET_KEYS or normalized_key.endswith("_api_key"):
        if value in (None, "", {}, []):
            return value
        return _REDACTED
    if isinstance(value, dict):
        return {
            str(child_key): _redact_for_disk(child_value, key=str(child_key))
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_for_disk(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_for_disk(item) for item in value]
    return value


def _ensure_private_job_dir() -> None:
    JOB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(JOB_DIR, 0o700)
    except OSError:
        pass


def create_job(payload: Dict[str, Any], user_id: int | None = None) -> str:
    job_id = uuid.uuid4().hex
    rec = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "queued",
        "created_at": time.time(),
        "updated_at": time.time(),
        "payload": payload,
        "result": {},
        "error": None,
    }
    _write_job(rec)
    return job_id


def update_job(job_id: str, **kwargs: Any) -> Dict[str, Any]:
    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise ValueError("invalid job_id")
    with _JOB_LOCK:
        rec = get_job(valid_job_id) or {"job_id": valid_job_id}
        rec.update(kwargs)
        rec["updated_at"] = time.time()
        _write_job(rec)
        return rec


def heartbeat_job(
    job_id: str,
    *,
    activity: str | None = None,
    progress_updates: Dict[str, Any] | None = None,
    agent_runtime_updates: Dict[str, Any] | None = None,
) -> Optional[Dict[str, Any]]:
    """Merge a liveness heartbeat without reviving a terminal job.

    Heartbeats intentionally preserve the latest business progress.  They only
    add liveness/activity metadata and therefore can safely run while a long
    model request is in flight.
    """

    with _JOB_LOCK:
        rec = get_job(job_id)
        if not rec:
            return None
        if str(rec.get("status") or "").strip().lower() not in {"queued", "running"}:
            return rec

        now = time.time()
        progress = dict(rec.get("progress") or {})
        progress.update(dict(progress_updates or {}))
        progress["heartbeat_at"] = now
        progress["elapsed_seconds"] = max(0, int(now - float(rec.get("created_at") or now)))
        progress["heartbeat_seq"] = int(progress.get("heartbeat_seq") or 0) + 1
        if activity is not None:
            progress["activity"] = str(activity)
        rec["progress"] = progress

        if agent_runtime_updates:
            runtime = dict(rec.get("agent_runtime") or {})
            runtime.update(dict(agent_runtime_updates))
            rec["agent_runtime"] = runtime

        rec["updated_at"] = now
        _write_job(rec)
        return rec


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        return None
    with _JOB_LOCK:
        path = JOB_DIR / f"{valid_job_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None


def list_jobs(limit: int = 50, user_id: int | None = None) -> list[dict]:
    jobs = []
    for p in sorted(JOB_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
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


def cleanup_jobs(older_than_seconds: int = 7 * 24 * 3600) -> int:
    removed = 0
    now = time.time()
    for p in JOB_DIR.glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            ts = rec.get("updated_at") or rec.get("created_at") or 0
            if now - float(ts) > older_than_seconds:
                # 删除关联产物
                result = rec.get("result") or {}
                for k in (
                    "json",
                    "docx",
                    "compare_docx",
                    "focus_xlsx",
                    "score_overview_xlsx",
                    "expert_review_docx",
                    "source_docx",
                    "professional_docx",
                    "professional_json",
                    "professional_render_receipt",
                    "delivery_receipt",
                ):
                    f = result.get(k)
                    if isinstance(f, list):
                        for pi in f:
                            try:
                                Path(pi).unlink(missing_ok=True)
                            except Exception:
                                pass
                    elif f:
                        try:
                            Path(f).unlink(missing_ok=True)
                        except Exception:
                            pass
                p.unlink(missing_ok=True)
                try:
                    from backend.zhifei_autoplan.generation_checkpoint import (
                        cleanup_checkpoint_namespace,
                    )

                    cleanup_checkpoint_namespace(str(rec.get("job_id") or ""))
                except Exception:
                    # Job retention cleanup remains best-effort; a malformed or
                    # tampered checkpoint is never loaded by the generator.
                    pass
                removed += 1
        except Exception:
            continue
    return removed


def _write_job(rec: Dict[str, Any]) -> None:
    with _JOB_LOCK:
        if not rec.get("job_id"):
            return
        job_id = _valid_job_id(rec.get("job_id"))
        if job_id is None:
            raise ValueError("invalid job_id")
        _ensure_private_job_dir()
        path = JOB_DIR / f"{job_id}.json"
        temp_path = JOB_DIR / f".{job_id}.{uuid.uuid4().hex}.tmp"
        try:
            persisted = _redact_for_disk(rec)
            encoded = json.dumps(persisted, ensure_ascii=False, indent=2).encode("utf-8")
            descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(descriptor, "wb", closefd=True) as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            os.replace(temp_path, path)
            try:
                os.chmod(path, 0o600)
                directory_fd = os.open(JOB_DIR, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
        finally:
            temp_path.unlink(missing_ok=True)
