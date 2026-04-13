from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class LoadDoneJobFailure(Exception):
    code: str
    message: str
    next_action: str
    extra: dict[str, Any] | None = None


@dataclass
class LoadDoneJobBundle:
    job: dict[str, Any]
    result: dict[str, Any]
    data: dict[str, Any]
    variants: list[Any]


def load_done_job_variants(
    *,
    job_id: str,
    workspace_dir: str | None,
    get_job_fn: Callable[..., dict[str, Any] | None],
    result_loader_fn: Callable[[dict[str, Any]], Any],
) -> LoadDoneJobBundle:
    job = get_job_fn(job_id, workspace_dir=workspace_dir)
    if not job:
        raise LoadDoneJobFailure(
            code="job_not_found",
            message="job not found",
            next_action="check job_id or workspace scope",
        )

    status = str(job.get("status") or "").strip()
    if status != "done":
        raise LoadDoneJobFailure(
            code="job_not_done",
            message=f"job not done: {job.get('status')}",
            next_action="poll /actions/job_status until status=done",
            extra={"status": status},
        )

    result = job.get("result") or {}
    loaded = result_loader_fn(result)
    return LoadDoneJobBundle(
        job=job,
        result=result,
        data=loaded.data,
        variants=loaded.variants,
    )
