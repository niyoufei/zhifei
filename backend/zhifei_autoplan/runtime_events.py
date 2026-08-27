from __future__ import annotations

"""Append-only, redacted runtime event journal for local Autoplan jobs."""

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Mapping


EVENT_DIR = Path(
    os.environ.get("ZF_AUTOPLAN_EVENT_DIR", "backend/data/autoplan/events")
)
MAX_EVENT_BYTES = max(
    1_048_576,
    int(os.environ.get("ZF_AUTOPLAN_EVENT_MAX_BYTES", str(8 * 1024 * 1024))),
)
_LOCK = threading.RLock()
_SAFE_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_SECRET_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "credential",
    "prompt",
)
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{8,}\b", re.IGNORECASE),
)


def _safe_value(value: Any, *, key: str = "") -> Any:
    lowered = str(key or "").strip().lower().replace("-", "_")
    if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
        return "[REDACTED]" if value not in (None, "", [], {}) else value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value.replace("\x00", " ")
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text[:2000]
    if isinstance(value, Mapping):
        return {str(k): _safe_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in list(value)[:100]]
    return _safe_value(str(value), key=key)


def append_runtime_event(job_id: str, event: str, **fields: Any) -> dict[str, Any]:
    safe_job_id = str(job_id or "").strip().lower()
    if not _SAFE_JOB_ID.fullmatch(safe_job_id):
        raise ValueError("invalid job_id")
    record = {
        "ts": time.time(),
        "job_id": safe_job_id,
        "event": str(event or "runtime_event")[:120],
        **{str(k): _safe_value(v, key=str(k)) for k, v in fields.items()},
    }
    try:
        with _LOCK:
            EVENT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                EVENT_DIR.chmod(0o700)
            except OSError:
                pass
            path = EVENT_DIR / f"{safe_job_id}.jsonl"
            if path.exists() and path.stat().st_size >= MAX_EVENT_BYTES:
                rotated = EVENT_DIR / f"{safe_job_id}.{int(time.time())}.jsonl"
                path.replace(rotated)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            try:
                path.chmod(0o600)
            except OSError:
                pass
    except OSError as exc:
        # The journal is diagnostic evidence, not the source of truth for the
        # job state machine.  A read-only disk, transient fsync failure, or a
        # full volume must not turn a successful generation step into a job
        # failure.  Return only the exception class; never include paths or
        # project content in the fallback signal.
        record["persisted"] = False
        record["persistence_error"] = type(exc).__name__
        return record
    record["persisted"] = True
    return record


def event_journal_path(job_id: str) -> Path | None:
    safe_job_id = str(job_id or "").strip().lower()
    if not _SAFE_JOB_ID.fullmatch(safe_job_id):
        return None
    path = EVENT_DIR / f"{safe_job_id}.jsonl"
    return path if path.exists() else None
