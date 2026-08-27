from __future__ import annotations

"""One local durable-dispatch worker for long-running Autoplan jobs.

The durable source of truth remains ``job_store``.  The in-memory queue is only
the execution transport; after a process restart stale queued/running jobs are
reconciled to ``interrupted_recoverable`` and are never replayed automatically.
"""

import queue
import multiprocessing
import threading
from dataclasses import dataclass
from typing import Any, Callable

from backend.zhifei_autoplan.runtime_events import append_runtime_event


@dataclass(frozen=True)
class _WorkItem:
    job_id: str
    callback: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    isolated: bool = False


_QUEUE: queue.Queue[_WorkItem] = queue.Queue()
_START_LOCK = threading.Lock()
_WORKER: threading.Thread | None = None
_PROCESS_CONTEXT = multiprocessing.get_context("spawn")
_ACTIVE_PROCESS_LOCK = threading.Lock()
_ACTIVE_PROCESS: multiprocessing.Process | None = None
_DISPATCH_LOCK = threading.Lock()
_DISPATCHED_JOB_IDS: set[str] = set()


def _safe_event(job_id: str, event: str, **data: Any) -> None:
    """Observability is best-effort and must never alter dispatch semantics."""

    try:
        append_runtime_event(job_id, event, **data)
    except Exception:
        return


def _safe_active_event(job_id: str, event: str, **data: Any) -> None:
    """Do not let a finished/reconciled worker append late lifecycle events."""

    try:
        from backend.zhifei_autoplan.job_store import get_job, run_with_job_lease

        record = get_job(job_id) or {}
        attempt_id = str(record.get("attempt_id") or "").strip()
        owner_instance_id = str(record.get("owner_instance_id") or "").strip()
        if not attempt_id or not owner_instance_id:
            return
        run_with_job_lease(
            job_id,
            attempt_id=attempt_id,
            owner_instance_id=owner_instance_id,
            callback=append_runtime_event,
            callback_args=(job_id, event),
            callback_kwargs=data,
        )
    except Exception:
        return


def _isolated_entrypoint(
    callback: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Spawn-safe entrypoint for a process-isolated durable job."""

    callback(*args, **kwargs)


def _ensure_isolated_process_terminal(job_id: str, exit_code: int | None) -> None:
    """Fail close when a child disappears without a durable transition."""

    try:
        from backend.zhifei_autoplan.generation_checkpoint import (
            mark_checkpoint_namespace_interrupted,
        )
        from backend.zhifei_autoplan.job_store import (
            ACTIVE_STATUSES,
            get_job,
            transition_job,
        )

        rec = get_job(job_id) or {}
        if str(rec.get("status") or "").strip().lower() not in ACTIVE_STATUSES:
            return
        prior_progress = rec.get("progress") if isinstance(rec.get("progress"), dict) else {}
        clean_exit = exit_code in {0, None}
        transition = transition_job(
            job_id,
            allowed_from=ACTIVE_STATUSES,
            status="interrupted_recoverable",
            revoke_lease=True,
            error={
                "code": (
                    "JOB_WORKER_RETURNED_WITHOUT_TERMINAL_STATE"
                    if clean_exit
                    else "JOB_WORKER_PROCESS_EXITED"
                ),
                "message": (
                    "隔离生成进程已返回但未写入可信终态；API 服务保持可用。"
                    if clean_exit
                    else "隔离生成进程异常退出；API 服务保持可用。"
                ),
                "action": "核对检查点后显式恢复任务。",
            },
            progress={
                "stage": "worker_process_exited",
                "phase": str(prior_progress.get("phase") or "generation"),
                "work_state": "idle",
                "detail": "隔离生成进程异常退出，未影响后台服务。",
                # Make an incomplete seal visible even if the subsequent
                # checkpoint write or CAS projection is interrupted.
                "checkpoint": {
                    "status": "interruption_seal_pending",
                    "saved_chapter_count": 0,
                },
            },
        )
        if transition is None:
            return
        terminal_revision = int(transition.get("revision") or 0)
        try:
            scopes = mark_checkpoint_namespace_interrupted(job_id)
            checkpoint_projection: dict[str, Any] = {
                "status": (
                    "interrupted_recoverable" if scopes else "interrupted_empty"
                ),
                "saved_chapter_count": sum(
                    int(item.get("saved_chapter_count") or 0) for item in scopes
                ),
                "scopes": scopes,
            }
        except Exception as checkpoint_error:
            checkpoint_projection = {
                "status": "interruption_seal_failed",
                "saved_chapter_count": 0,
                "error_code": "CHECKPOINT_INTERRUPTION_SEAL_FAILED",
                "error_type": type(checkpoint_error).__name__,
            }
        # Only the terminal revision created above may publish the seal result.
        # If another owner/admin update won the race, leave its evidence intact;
        # the already-persisted `interruption_seal_pending` remains fail-closed.
        projection = transition_job(
            job_id,
            allowed_from={"interrupted_recoverable"},
            status="interrupted_recoverable",
            expected_revision=terminal_revision,
            progress={"checkpoint": checkpoint_projection},
        )
        _safe_event(
            job_id,
            "worker_process_exited",
            exit_code=exit_code,
            status="interrupted_recoverable",
            checkpoint_status=str(checkpoint_projection.get("status") or "unknown"),
            checkpoint_projection_applied=projection is not None,
        )
    except Exception:
        pass


def _run_isolated(item: _WorkItem) -> None:
    global _ACTIVE_PROCESS
    process = _PROCESS_CONTEXT.Process(
        target=_isolated_entrypoint,
        args=(item.callback, item.args, item.kwargs),
        name=f"autoplan-job-{item.job_id[:8]}",
        daemon=False,
    )
    try:
        process.start()
        with _ACTIVE_PROCESS_LOCK:
            _ACTIVE_PROCESS = process
        # The child acquires the durable execution lease.  A parent-side
        # "started" event before that claim cannot be fenced and is therefore
        # intentionally omitted; callback-specific started events are the
        # authoritative lifecycle evidence.
        process.join()
        exit_code = process.exitcode
        _safe_active_event(
            item.job_id,
            "worker_process_finished",
            exit_code=exit_code,
        )
        _ensure_isolated_process_terminal(item.job_id, exit_code)
    except BaseException:
        _ensure_isolated_process_terminal(item.job_id, process.exitcode)
        raise
    finally:
        with _ACTIVE_PROCESS_LOCK:
            if _ACTIVE_PROCESS is process:
                _ACTIVE_PROCESS = None
        try:
            process.close()
        except (OSError, ValueError):
            pass


def _worker_loop() -> None:
    while True:
        item = _QUEUE.get()
        try:
            from backend.zhifei_autoplan.job_store import ACTIVE_STATUSES, get_job

            record = get_job(item.job_id) or {}
            if str(record.get("status") or "").strip().lower() not in ACTIVE_STATUSES:
                continue
            if item.isolated:
                _run_isolated(item)
            else:
                item.callback(*item.args, **item.kwargs)
        except BaseException as exc:
            # The callback owns the durable terminal transition.  This record
            # is a final safety diagnostic and deliberately contains no prompt.
            try:
                _safe_active_event(
                    item.job_id,
                    "worker_uncaught_exception",
                    error_type=type(exc).__name__,
                )
            except Exception:
                pass
        finally:
            with _DISPATCH_LOCK:
                _DISPATCHED_JOB_IDS.discard(item.job_id)
            _QUEUE.task_done()


def ensure_worker_started() -> threading.Thread:
    global _WORKER
    with _START_LOCK:
        if _WORKER is None or not _WORKER.is_alive():
            _WORKER = threading.Thread(
                target=_worker_loop,
                name="autoplan-local-job-worker",
                daemon=True,
            )
            _WORKER.start()
    return _WORKER


def submit_local_job(
    job_id: str,
    callback: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> int:
    ensure_worker_started()
    with _DISPATCH_LOCK:
        _DISPATCHED_JOB_IDS.add(str(job_id))
    _QUEUE.put(_WorkItem(str(job_id), callback, tuple(args), dict(kwargs), False))
    _safe_event(job_id, "worker_queued", queue_depth=_QUEUE.qsize())
    return _QUEUE.qsize()


def submit_isolated_job(
    job_id: str,
    callback: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> int:
    """Queue a spawn-isolated job while preserving the same durable FIFO."""

    if "<locals>" in str(getattr(callback, "__qualname__", "")):
        raise ValueError("isolated job callback must be a module-level callable")
    ensure_worker_started()
    with _DISPATCH_LOCK:
        _DISPATCHED_JOB_IDS.add(str(job_id))
    _QUEUE.put(_WorkItem(str(job_id), callback, tuple(args), dict(kwargs), True))
    _safe_event(
        job_id,
        "worker_queued",
        queue_depth=_QUEUE.qsize(),
        execution_mode="spawn_process",
    )
    return _QUEUE.qsize()


def local_dispatch_job_ids() -> set[str]:
    with _DISPATCH_LOCK:
        return set(_DISPATCHED_JOB_IDS)


def local_queue_snapshot() -> dict[str, Any]:
    worker = _WORKER
    with _ACTIVE_PROCESS_LOCK:
        active_process = _ACTIVE_PROCESS
    with _DISPATCH_LOCK:
        dispatched_count = len(_DISPATCHED_JOB_IDS)
    return {
        "queue_depth": int(_QUEUE.qsize()),
        "worker_started": worker is not None,
        "worker_alive": bool(worker and worker.is_alive()),
        "worker_name": worker.name if worker is not None else None,
        "active_process_pid": active_process.pid if active_process is not None else None,
        "active_process_alive": bool(active_process and active_process.is_alive()),
        "execution_isolation": "spawn_process_for_generation",
        "dispatched_jobs": dispatched_count,
    }
