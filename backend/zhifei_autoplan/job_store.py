from __future__ import annotations

import ast
import fcntl
import json
import os
import re
import shutil
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, TypeVar

JOB_DIR = Path(os.environ.get("ZF_AUTOPLAN_JOB_DIR", "backend/data/autoplan/jobs"))
INGEST_SPOOL_DIR = Path(
    os.environ.get("ZF_AUTOPLAN_INGEST_SPOOL_DIR", "backend/data/autoplan/ingest_spool")
)
_JOB_LOCK = threading.RLock()
_INSTANCE_ID = uuid.uuid4().hex
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
ACTIVE_STATUSES = {"queued", "running", "cancel_requested"}
TERMINAL_STATUSES = {
    "done",  # one-cycle compatibility with the legacy API
    "succeeded",
    "failed",
    "cancelled",
    "interrupted_recoverable",
}
LEASE_ACTIVE_STATUSES = {"running", "cancel_requested"}
_LeaseResult = TypeVar("_LeaseResult")


class JobLeaseLostError(RuntimeError):
    """Raised before a stale worker can mutate durable job evidence."""


def _lease_matches(
    record: dict[str, Any],
    *,
    attempt_id: str | None,
    owner_instance_id: str | None,
    allowed_statuses: Iterable[str] = LEASE_ACTIVE_STATUSES,
) -> bool:
    expected_attempt = str(attempt_id or "").strip()
    expected_owner = str(owner_instance_id or "").strip()
    if not expected_attempt or not expected_owner:
        return False
    statuses = {str(value or "").strip().lower() for value in allowed_statuses}
    return (
        str(record.get("status") or "").strip().lower() in statuses
        and str(record.get("attempt_id") or "").strip() == expected_attempt
        and str(record.get("owner_instance_id") or "").strip() == expected_owner
    )


def _revoke_lease(record: dict[str, Any], *, reason: str) -> None:
    attempt_id = str(record.get("attempt_id") or "").strip()
    owner_instance_id = str(record.get("owner_instance_id") or "").strip()
    if attempt_id:
        record["last_attempt_id"] = attempt_id
    if owner_instance_id:
        record["last_owner_instance_id"] = owner_instance_id
    attempt_revision = record.get("attempt_revision")
    if isinstance(attempt_revision, int) and not isinstance(attempt_revision, bool):
        record["last_job_revision"] = attempt_revision
    record["attempt_id"] = None
    record["owner_instance_id"] = None
    record["attempt_revision"] = None
    record["lease_revoked_at"] = time.time()
    record["lease_revoke_reason"] = str(reason or "state_transition")[:120]


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


@contextmanager
def _exclusive_store_lock() -> Iterator[None]:
    """Serialize read-modify-write cycles across API and spawned workers."""

    with _JOB_LOCK:
        _ensure_private_job_dir()
        lock_path = JOB_DIR / ".job-store.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                os.chmod(lock_path, 0o600)
            except OSError:
                pass
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _read_job_unlocked(job_id: str) -> dict[str, Any] | None:
    path = JOB_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _merge_fields(record: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    for key, value in values.items():
        if key in {"progress", "agent_runtime", "result"} and isinstance(value, dict):
            merged = dict(record.get(key) or {})
            merged.update(value)
            record[key] = merged
        else:
            record[key] = value
    return record


def _bump_revision(record: dict[str, Any]) -> None:
    record["revision"] = max(0, int(record.get("revision") or 0)) + 1
    record["updated_at"] = time.time()


def create_job(payload: dict[str, Any], user_id: int | None = None) -> str:
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
        "revision": 1,
        # Queued work has no execution authority.  A worker must atomically
        # acquire a fresh, unpredictable fencing token before doing any work.
        "attempt_id": None,
        "owner_instance_id": None,
        "attempt_revision": None,
    }
    _write_job(rec)
    return job_id


def acquire_job_lease(
    job_id: str,
    *,
    owner_instance_id: str | None = None,
) -> dict[str, Any] | None:
    """Atomically claim queued work and mint a new worker fencing token.

    A queued cancellation is also claimable so the worker can seal any
    checkpoint namespace and acknowledge cancellation without starting model
    work.  Existing running work is never re-leased implicitly.
    """

    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise ValueError("invalid job_id")
    owner = str(owner_instance_id or _INSTANCE_ID).strip()
    if not owner:
        raise ValueError("missing owner_instance_id")
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if rec is None:
            return None
        current = str(rec.get("status") or "").strip().lower()
        if current not in {"queued", "cancel_requested"}:
            return None
        # A cancellation requested from an active worker retains that worker's
        # authority until it acknowledges the cancellation.  A duplicate queue
        # item must never mint a replacement token and create two live owners.
        if str(rec.get("attempt_id") or "").strip() or str(
            rec.get("owner_instance_id") or ""
        ).strip():
            return None
        rec["attempt_id"] = uuid.uuid4().hex
        rec["owner_instance_id"] = owner
        rec["attempt_revision"] = max(0, int(rec.get("revision") or 0)) + 1
        rec["lease_acquired_at"] = time.time()
        rec.pop("lease_revoked_at", None)
        rec.pop("lease_revoke_reason", None)
        if current == "queued":
            rec["status"] = "running"
        _bump_revision(rec)
        _write_job_unlocked(rec)
        return rec


def job_lease_active(
    job_id: str,
    *,
    attempt_id: str,
    owner_instance_id: str,
    allowed_statuses: Iterable[str] = LEASE_ACTIVE_STATUSES,
) -> bool:
    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        return False
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        return bool(
            rec
            and _lease_matches(
                rec,
                attempt_id=attempt_id,
                owner_instance_id=owner_instance_id,
                allowed_statuses=allowed_statuses,
            )
        )


def run_with_job_lease(
    job_id: str,
    *,
    attempt_id: str,
    owner_instance_id: str,
    callback: Callable[..., _LeaseResult],
    callback_args: tuple[Any, ...] = (),
    callback_kwargs: dict[str, Any] | None = None,
    allowed_statuses: Iterable[str] = LEASE_ACTIVE_STATUSES,
) -> _LeaseResult:
    """Run one durable side effect while holding the verified lease fence.

    Holding the job-store lock across the callback makes checkpoint/event
    writes mutually exclusive with reconciliation revocation: either the write
    completes first and reconciliation seals it, or revocation wins and the
    stale write never starts.
    """

    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise JobLeaseLostError("invalid_job_id")
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if not rec or not _lease_matches(
            rec,
            attempt_id=attempt_id,
            owner_instance_id=owner_instance_id,
            allowed_statuses=allowed_statuses,
        ):
            raise JobLeaseLostError("job_lease_lost")
        return callback(*(callback_args or ()), **dict(callback_kwargs or {}))


def update_job(job_id: str, **kwargs: Any) -> dict[str, Any] | None:
    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise ValueError("invalid job_id")
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if rec is None:
            return None
        rec.update(kwargs)
        _bump_revision(rec)
        _write_job_unlocked(rec)
        return rec


def merge_job(
    job_id: str,
    *,
    expected_attempt_id: str | None = None,
    expected_owner_instance_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Merge nested runtime fields without erasing prior progress evidence."""

    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise ValueError("invalid job_id")
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if rec is None:
            return None
        if (
            expected_attempt_id is not None
            or expected_owner_instance_id is not None
        ) and not _lease_matches(
                rec,
                attempt_id=expected_attempt_id,
                owner_instance_id=expected_owner_instance_id,
            ):
            return None
        _merge_fields(rec, kwargs)
        _bump_revision(rec)
        _write_job_unlocked(rec)
        return rec


def transition_job(
    job_id: str,
    *,
    allowed_from: Iterable[str],
    status: str,
    expected_revision: int | None = None,
    expected_attempt_id: str | None = None,
    expected_owner_instance_id: str | None = None,
    revoke_lease: bool = False,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Atomically apply an allowed transition without resurrecting a record."""

    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        raise ValueError("invalid job_id")
    allowed = {str(value or "").strip().lower() for value in allowed_from}
    target = str(status or "").strip().lower()
    if not target:
        raise ValueError("missing target status")
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if rec is None:
            return None
        current = str(rec.get("status") or "").strip().lower()
        if current not in allowed:
            return None
        if expected_revision is not None and int(rec.get("revision") or 0) != int(expected_revision):
            return None
        if (
            expected_attempt_id is not None
            or expected_owner_instance_id is not None
        ) and not _lease_matches(
                rec,
                attempt_id=expected_attempt_id,
                owner_instance_id=expected_owner_instance_id,
            ):
            return None
        _merge_fields(rec, kwargs)
        rec["status"] = target
        if revoke_lease:
            _revoke_lease(rec, reason=f"transition:{target}")
        _bump_revision(rec)
        _write_job_unlocked(rec)
        return rec


def heartbeat_job(
    job_id: str,
    *,
    activity: str | None = None,
    progress_updates: dict[str, Any] | None = None,
    agent_runtime_updates: dict[str, Any] | None = None,
    expected_attempt_id: str | None = None,
    expected_owner_instance_id: str | None = None,
    allowed_statuses: Iterable[str] = LEASE_ACTIVE_STATUSES,
) -> dict[str, Any] | None:
    """Merge a liveness heartbeat without reviving a terminal job.

    Heartbeats intentionally preserve the latest business progress.  They only
    add liveness/activity metadata and therefore can safely run while a long
    model request is in flight.
    """

    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        return None
    with _exclusive_store_lock():
        rec = _read_job_unlocked(valid_job_id)
        if not rec:
            return None
        if (
            expected_attempt_id is not None
            or expected_owner_instance_id is not None
        ) and not _lease_matches(
                rec,
                attempt_id=expected_attempt_id,
                owner_instance_id=expected_owner_instance_id,
                allowed_statuses=allowed_statuses,
            ):
            return None
        if str(rec.get("status") or "").strip().lower() not in ACTIVE_STATUSES:
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

        _bump_revision(rec)
        rec["updated_at"] = now
        _write_job_unlocked(rec)
        return rec


def reconcile_stale_jobs(
    *,
    stale_after_seconds: int = 60,
    now: float | None = None,
    protected_job_ids: Iterable[str] | None = None,
) -> list[str]:
    """Fail-close orphaned queued/running jobs after a process restart."""

    current = float(now if now is not None else time.time())
    stale_after = max(1, int(stale_after_seconds))
    reconciled: list[str] = []
    protected = {
        valid for value in (protected_job_ids or []) if (valid := _valid_job_id(value))
    }
    for rec in list_jobs(limit=100_000):
        status = str(rec.get("status") or "").strip().lower()
        if status not in ACTIVE_STATUSES:
            continue
        job_id = str(rec.get("job_id") or "")
        # A locally dispatched item that has not acquired a lease may still be
        # waiting behind another FIFO job, so protect that queued work.  Once a
        # worker owns a lease, however, dispatch membership must not suppress
        # stale-heartbeat recovery: a hung running/cancelling process remains
        # in the dispatch set until its callback returns.
        if job_id in protected and not str(rec.get("attempt_id") or "").strip():
            continue
        progress = rec.get("progress") if isinstance(rec.get("progress"), dict) else {}
        try:
            last_signal = float(
                progress.get("heartbeat_at")
                or rec.get("updated_at")
                or rec.get("created_at")
                or 0
            )
        except (TypeError, ValueError):
            last_signal = 0.0
        if current - last_signal <= stale_after:
            continue
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        is_ingest = str(payload.get("action") or "").strip().lower() == "ingest"
        if is_ingest:
            public_error = {
                "code": "INGEST_INTERRUPTED",
                "message": "资料导入因后端进程中断而停止；已保留成功写入的文件与解析缓存。",
                "action": "确认后端恢复后，保留页面已选文件并显式重试导入。",
            }
        else:
            public_error = {
                "code": "JOB_INTERRUPTED",
                "message": "服务重启或工作进程中断；已保留可信检查点，未自动重放模型调用。",
                "action": "核对检查点后由用户显式恢复任务。",
            }
        # Revoke the execution fence before touching checkpoint files.  A
        # lease-aware worker can no longer race a later checkpoint/final write
        # once this transition succeeds.
        transition = transition_job(
            job_id,
            allowed_from=ACTIVE_STATUSES,
            status="interrupted_recoverable",
            revoke_lease=True,
            error=public_error,
            progress={
                "phase": str(progress.get("phase") or progress.get("stage") or "unknown"),
                "work_state": "idle",
                "detail": "任务心跳已过期，已转为可恢复中断状态。",
            },
        )
        if transition is None:
            continue
        checkpoint_projection: dict[str, Any] | None = None
        try:
            from backend.zhifei_autoplan.generation_checkpoint import (
                mark_checkpoint_namespace_interrupted,
            )

            scopes = mark_checkpoint_namespace_interrupted(job_id)
            if scopes:
                checkpoint_projection = {
                    "status": "interrupted_recoverable",
                    "saved_chapter_count": sum(
                        int(item.get("saved_chapter_count") or 0) for item in scopes
                    ),
                    "scopes": scopes,
                }
        except Exception as checkpoint_error:  # noqa: BLE001 - seal failures become evidence.
            checkpoint_projection = {
                "status": "interruption_seal_failed",
                "saved_chapter_count": 0,
                "error_code": "CHECKPOINT_INTERRUPTION_SEAL_FAILED",
                "error_type": type(checkpoint_error).__name__,
            }
        if checkpoint_projection is not None:
            merge_job(job_id, progress={"checkpoint": checkpoint_projection})
        if is_ingest:
            shutil.rmtree(INGEST_SPOOL_DIR / job_id, ignore_errors=True)
        reconciled.append(job_id)
    return reconciled


def job_runtime_counts(*, stale_after_seconds: int = 60, now: float | None = None) -> dict[str, int]:
    current = float(now if now is not None else time.time())
    counts = {"active": 0, "queued": 0, "running": 0, "cancel_requested": 0, "stale": 0, "total": 0}
    for rec in list_jobs(limit=100_000):
        counts["total"] += 1
        status = str(rec.get("status") or "").strip().lower()
        if status in ACTIVE_STATUSES:
            counts["active"] += 1
            counts[status] = counts.get(status, 0) + 1
            progress = rec.get("progress") if isinstance(rec.get("progress"), dict) else {}
            try:
                last_signal = float(
                    progress.get("heartbeat_at")
                    or rec.get("updated_at")
                    or rec.get("created_at")
                    or 0
                )
            except (TypeError, ValueError):
                last_signal = 0.0
            if current - last_signal > max(1, int(stale_after_seconds)):
                counts["stale"] += 1
    return counts


def _legacy_public_error(value: Any) -> dict[str, Any]:
    raw = str(value or "").strip()
    candidates = [raw]
    if raw.startswith("RuntimeError(") and raw.endswith(")"):
        inner = raw[len("RuntimeError(") : -1].strip()
        try:
            decoded = ast.literal_eval(inner)
        except (SyntaxError, ValueError):
            decoded = None
        if decoded is not None:
            candidates.insert(0, str(decoded))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            failures = []
            for item in (parsed.get("failures") or [])[:50]:
                if not isinstance(item, dict):
                    continue
                failures.append(
                    {
                        "title": str(item.get("title") or "")[:200],
                        "provider": str(item.get("provider") or "")[:80],
                        "model": str(item.get("model") or "")[:120],
                        "error": str(item.get("error") or "provider_error")[:300],
                    }
                )
            return {
                "code": str(parsed.get("code") or "LEGACY_JOB_FAILED")[:80],
                "message": str(parsed.get("message") or "历史任务执行失败。")[:500],
                "action": "核对保存的检查点后显式恢复任务。",
                "failures": failures,
            }
    return {
        "code": "LEGACY_JOB_FAILED",
        "message": "历史任务执行失败；原始异常已封存，不再直接展示。",
        "action": "查看脱敏事件或重新执行任务。",
    }


def _failed_job_public_error(job: dict[str, Any]) -> dict[str, Any]:
    existing_error = job.get("error")
    if isinstance(existing_error, dict) and str(existing_error.get("code") or "").strip():
        public_error = {
            "code": str(existing_error.get("code") or "LEGACY_JOB_FAILED")[:80],
            "message": str(existing_error.get("message") or "历史任务执行失败。")[:500],
            "action": str(
                existing_error.get("action") or "核对保存的检查点后显式恢复任务。"
            )[:500],
        }
        if isinstance(existing_error.get("failures"), list):
            public_error["failures"] = list(existing_error.get("failures") or [])[:50]
        return public_error
    return _legacy_public_error(existing_error)


def _legacy_checkpoint_seal_failure(
    job_id: str,
    job: dict[str, Any],
    exc: BaseException,
) -> dict[str, Any] | None:
    """Persist fail-closed evidence for one legacy checkpoint seal failure."""

    reason_code = str(
        getattr(exc, "reason_code", "") or "checkpoint_seal_failed"
    ).strip()
    schema_incompatible = reason_code == "checkpoint_schema_mismatch"
    error_code = (
        "CHECKPOINT_SCHEMA_INCOMPATIBLE"
        if schema_incompatible
        else "CHECKPOINT_FAILURE_SEAL_FAILED"
    )
    stage = (
        "checkpoint_schema_incompatible"
        if schema_incompatible
        else "checkpoint_failure_seal_failed"
    )
    action = (
        "旧版检查点已拒绝复用且不会迁移；请从原始输入重新发起任务。"
        if schema_incompatible
        else "检查检查点存储后从原始输入重新发起任务；不要复用未封存的章节。"
    )
    detail = (
        "历史检查点版本与当前运行版本不兼容，已保持原文件不变并拒绝复用。"
        if schema_incompatible
        else "历史检查点终态封存失败，已按不可恢复证据处理。"
    )
    seal_failure = {
        "code": error_code,
        "reason_code": reason_code,
        "error_type": type(exc).__name__,
        "reuse_allowed": False,
        "migration_attempted": False,
    }
    if schema_incompatible:
        seal_failure["schema_compatible"] = False
    checkpoint_projection = {
        "status": "failure_seal_failed",
        "saved_chapter_count": 0,
        "scopes": [],
        "error_code": error_code,
        "error_type": type(exc).__name__,
        "reason_code": reason_code,
        "reuse_allowed": False,
        "migration_attempted": False,
    }
    if schema_incompatible:
        checkpoint_projection["schema_compatible"] = False

    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    try:
        percent = min(99, max(0, int(progress.get("percent") or 0)))
    except (TypeError, ValueError):
        percent = 0
    phase = str(progress.get("phase") or "generation")
    public_error = _failed_job_public_error(job)
    public_error["action"] = action
    public_error["checkpoint_seal_failure"] = seal_failure
    return merge_job(
        job_id,
        error=public_error,
        progress={
            "percent": percent,
            "phase": phase,
            "stage": stage,
            "work_state": "idle",
            "chapters": {
                "started": 0,
                "succeeded": 0,
                "failed": 0,
                "total": 0,
            },
            "chapters_done": 0,
            "chapters_succeeded": 0,
            "chapters_failed": 0,
            "chapters_total": 0,
            "checkpoint": checkpoint_projection,
            "detail": detail,
        },
        result={
            "section_count": 0,
            "checkpoint_status": "failure_seal_failed",
            "checkpoint_error_code": error_code,
            "checkpoint_reuse_allowed": False,
            "recoverable": False,
            "delivery_ready": False,
        },
    )


def reconcile_failed_job_evidence(job_id: str) -> dict[str, Any]:
    """Normalize one historical failed job without modifying saved sections."""

    job = get_job(job_id)
    if not job:
        raise ValueError("job not found")
    if str(job.get("status") or "").strip().lower() != "failed":
        raise ValueError("job is not failed")
    from backend.zhifei_autoplan.generation_checkpoint import (
        mark_failed_checkpoint_namespace,
    )

    try:
        checkpoints = mark_failed_checkpoint_namespace(job_id)
    except Exception as exc:
        failed = _legacy_checkpoint_seal_failure(job_id, job, exc)
        if failed is None:
            raise ValueError("job disappeared during checkpoint reconciliation") from exc
        return failed
    succeeded = sum(int(item.get("saved_chapter_count") or 0) for item in checkpoints)
    total = sum(int(item.get("chapters_total") or 0) for item in checkpoints)
    failed = max(0, total - succeeded)
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    public_error = _failed_job_public_error(job)
    percent = int(progress.get("percent") or 0)
    if total > 0:
        percent = min(99, 15 + int((succeeded / total) * 60))
    checkpoint_status = "failed_partial" if succeeded else "failed_empty"
    previous_phase = str(progress.get("phase") or "generation")
    phase = "quality_review" if previous_phase == "quality_review" else "generation"
    stage = "quality_review_failed" if phase == "quality_review" else "failed"
    return merge_job(
        job_id,
        error=public_error,
        progress={
            "percent": min(99, percent),
            "phase": phase,
            "stage": stage,
            "work_state": "idle",
            "chapters": {
                "started": total,
                "succeeded": succeeded,
                "failed": failed,
                "total": total,
            },
            "chapters_done": succeeded,
            "chapters_succeeded": succeeded,
            "chapters_failed": failed,
            "chapters_total": total,
            "checkpoint": {
                "status": checkpoint_status,
                "saved_chapter_count": succeeded,
                "scopes": checkpoints,
            },
            "detail": str(public_error.get("message") or "历史失败任务已按真实检查点重新归类。"),
        },
        result={
            "section_count": succeeded,
            "checkpoint_status": checkpoint_status,
            "recoverable": bool(succeeded),
            "delivery_ready": False,
        },
    )


def reconcile_legacy_failed_jobs(*, limit: int = 100_000) -> list[str]:
    """Repair failed records that still advertise completion evidence.

    Older workers could persist ``percent=100`` or a complete checkpoint before
    a later quality/render failure.  Both projections are misleading and must
    be rebuilt from verified section checkpoints.
    """

    reconciled: list[str] = []
    for job in list_jobs(limit=max(1, int(limit))):
        if str(job.get("status") or "").strip().lower() != "failed":
            continue
        progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        checkpoint = progress.get("checkpoint") if isinstance(progress.get("checkpoint"), dict) else {}
        advertised = {
            str(checkpoint.get("status") or "").strip().lower(),
            str(result.get("checkpoint_status") or "").strip().lower(),
        }
        try:
            advertised_percent = int(progress.get("percent") or 0)
        except (TypeError, ValueError):
            advertised_percent = 0
        if (
            not advertised.intersection({"complete", "draft_complete"})
            and advertised_percent < 100
        ):
            continue
        job_id = str(job.get("job_id") or "")
        if _valid_job_id(job_id) is None:
            continue
        try:
            repaired = reconcile_failed_job_evidence(job_id)
        except Exception as exc:  # noqa: BLE001 - isolate one malformed legacy job.
            # Startup repair is per-job.  A malformed namespace or a concurrent
            # record disappearance must never prevent the API from starting.
            try:
                repaired = _legacy_checkpoint_seal_failure(job_id, job, exc)
            except Exception:  # noqa: BLE001 - startup repair remains per-job.
                repaired = None
        if repaired is not None:
            reconciled.append(job_id)
    return reconciled


def get_job(job_id: str) -> dict[str, Any] | None:
    valid_job_id = _valid_job_id(job_id)
    if valid_job_id is None:
        return None
    with _JOB_LOCK:
        return _read_job_unlocked(valid_job_id)


def list_jobs(limit: int = 50, user_id: int | None = None) -> list[dict]:
    jobs = []
    candidates: list[tuple[float, Path]] = []
    for path in JOB_DIR.glob("*.json"):
        try:
            candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for _mtime, p in sorted(candidates, key=lambda item: item[0], reverse=True):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, TypeError, UnicodeError, json.JSONDecodeError):
            rec = None
        if not isinstance(rec, dict):
            continue
        if user_id is not None and rec.get("user_id") != user_id:
            continue
        jobs.append(rec)
        if len(jobs) >= limit:
            break
    return jobs


def cleanup_jobs(older_than_seconds: int = 7 * 24 * 3600) -> int:
    removed = 0
    now = time.time()
    for p in JOB_DIR.glob("*.json"):
        with suppress(OSError, TypeError, UnicodeError, ValueError):
            rec = json.loads(p.read_text(encoding="utf-8"))
            if str(rec.get("status") or "").strip().lower() in ACTIVE_STATUSES:
                continue
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
                            _unlink_managed_artifact(pi)
                    elif f:
                        _unlink_managed_artifact(f)
                p.unlink(missing_ok=True)
                with suppress(Exception):
                    from backend.zhifei_autoplan.generation_checkpoint import (
                        cleanup_checkpoint_namespace,
                    )

                    cleanup_checkpoint_namespace(str(rec.get("job_id") or ""))
                removed += 1
    return removed


def _managed_artifact_roots() -> list[Path]:
    roots = [JOB_DIR.parent.resolve(), Path("build").resolve()]
    raw = str(os.environ.get("ZF_AUTOPLAN_ARTIFACT_ROOTS") or "")
    roots.extend(
        Path(item).expanduser().resolve()
        for item in raw.split(os.pathsep)
        if item.strip()
    )
    return roots


def _unlink_managed_artifact(value: Any) -> bool:
    try:
        path = Path(str(value)).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    if not any(path == root or path.is_relative_to(root) for root in _managed_artifact_roots()):
        return False
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _write_job_unlocked(rec: dict[str, Any]) -> None:
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


def _write_job(rec: dict[str, Any]) -> None:
    with _exclusive_store_lock():
        _write_job_unlocked(rec)
