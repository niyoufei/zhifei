from __future__ import annotations

from typing import Any, Callable


def cancel_job(
    *,
    job_id: str,
    workspace_dir: str,
    job: dict[str, Any],
    kill_fn: Callable[[int, int], Any],
    update_job_fn: Callable[..., dict[str, Any]],
    build_response_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    status = str(job.get("status") or "").strip().lower()
    if status in {"done", "failed", "cancelled"}:
        return build_response_fn(job_id=job_id, status=status)

    worker = job.get("worker") if isinstance(job.get("worker"), dict) else {}
    pid = worker.get("pid")
    try:
        if pid:
            kill_fn(int(pid), 15)
    except Exception:
        pass

    update_job_fn(job_id, workspace_dir=workspace_dir, status="cancelled", error="cancelled_by_user")
    return build_response_fn(job_id=job_id, status="cancelled")
