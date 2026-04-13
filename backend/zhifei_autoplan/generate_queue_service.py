from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class GenerateWorkerSpawnFailure(Exception):
    job_id: str
    request_id: str | None
    trace_id: str | None
    worker_log_path: str
    cause: Exception


def queue_generate_job(
    *,
    payload: dict[str, Any],
    workspace_dir: str,
    session_id: str,
    request_signature: str,
    admission: dict[str, Any],
    create_job_fn: Callable[..., str],
    append_resource_event_fn: Callable[..., Any],
    spawn_generate_worker_fn: Callable[..., tuple[int, str]],
    update_job_fn: Callable[..., Any],
    append_worker_log_fn: Callable[..., Any],
    build_variant_plan_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    admission_http_detail_fn: Callable[[dict[str, Any]], dict[str, Any]],
    build_queued_response_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    variant_plan = build_variant_plan_fn(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(item.get("variant_id") or 1) for item in variant_plan]
    payload["variants"] = len(variant_plan) if variant_plan else int(payload.get("variants") or 1)

    job_id = create_job_fn(
        payload,
        user_id=None,
        request_signature=request_signature,
        workspace_dir=workspace_dir,
    )
    append_resource_event_fn(
        "job_queued",
        workspace_dir=workspace_dir,
        session_id=session_id,
        user_id=None,
        job_id=job_id,
        request_signature=request_signature,
        request_id=payload.get("request_id"),
        trace_id=payload.get("trace_id"),
        project_id=payload.get("project_id"),
        topic=payload.get("topic"),
        variants=int(payload.get("variants") or 1),
        warning_level=admission.get("warning_level"),
        warning_codes=[item.get("code") for item in admission.get("warnings") or [] if isinstance(item, dict) and item.get("code")],
        degrade_plan=admission.get("degrade_plan") or None,
    )
    try:
        worker_pid, worker_log_path = spawn_generate_worker_fn(job_id, workspace_dir=workspace_dir)
        update_job_fn(
            job_id,
            workspace_dir=workspace_dir,
            worker={
                "mode": "subprocess",
                "pid": int(worker_pid),
                "log_path": str(worker_log_path),
                "alive": True,
            },
            progress={"percent": 0, "stage": "queued", "detail": "任务已入队，等待Worker执行"},
        )
    except Exception as exc:
        worker_log_path = str(locals().get("worker_log_path") or "")
        try:
            append_worker_log_fn(job_id, f"worker_spawn_failed error={exc!r}", workspace_dir=workspace_dir)
        except Exception:
            pass
        update_job_fn(
            job_id,
            workspace_dir=workspace_dir,
            status="failed",
            error=f"worker_spawn_failed: {exc!r}",
            progress={"percent": 100, "stage": "failed", "detail": f"worker_spawn_failed: {exc!r}"},
        )
        raise GenerateWorkerSpawnFailure(
            job_id=job_id,
            request_id=str(payload.get("request_id") or "").strip() or None,
            trace_id=str(payload.get("trace_id") or "").strip() or None,
            worker_log_path=worker_log_path,
            cause=exc,
        ) from exc

    return build_queued_response_fn(
        job_id=job_id,
        workspace_dir=workspace_dir,
        session_id=session_id,
        admission_detail=admission_http_detail_fn(admission),
        request_id=payload.get("request_id"),
        trace_id=payload.get("trace_id"),
    )
