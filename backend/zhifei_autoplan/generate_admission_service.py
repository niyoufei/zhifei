from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class GenerateAdmissionRejected(Exception):
    detail: dict[str, Any]


@dataclass
class GenerateAdmissionResolution:
    reusable_response: dict[str, Any] | None
    admission: dict[str, Any] | None


def resolve_generate_admission(
    *,
    payload: dict[str, Any],
    session_id: str,
    workspace_dir: str,
    request_signature: str,
    find_reusable_job_fn: Callable[..., dict[str, Any] | None],
    evaluate_job_admission_fn: Callable[..., dict[str, Any]],
    admission_http_detail_fn: Callable[[dict[str, Any]], dict[str, Any]],
    append_resource_event_fn: Callable[..., Any],
    build_reused_response_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    build_rejection_event_fn: Callable[..., dict[str, Any]],
    build_rejected_detail_fn: Callable[..., dict[str, Any]],
    apply_admission_degrade_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None],
    new_log_anchor_fn: Callable[[str], str],
) -> GenerateAdmissionResolution:
    reusable = find_reusable_job_fn(
        request_signature,
        max_age_seconds=12 * 3600,
        workspace_dir=workspace_dir,
    )
    if reusable:
        reusable_admission = evaluate_job_admission_fn(
            scope="session",
            tenant_id=session_id,
            workspace_dir=workspace_dir,
            requested_jobs=0,
        )
        return GenerateAdmissionResolution(
            reusable_response=build_reused_response_fn(reusable, admission_http_detail_fn(reusable_admission)),
            admission=None,
        )

    admission = evaluate_job_admission_fn(
        scope="session",
        tenant_id=session_id,
        workspace_dir=workspace_dir,
        requested_jobs=1,
    )
    if not admission.get("allowed", False):
        append_resource_event_fn(
            "job_rejected",
            workspace_dir=workspace_dir,
            session_id=session_id,
            user_id=None,
            **build_rejection_event_fn(
                payload=payload,
                admission=admission,
                request_signature=request_signature,
            ),
        )
        raise GenerateAdmissionRejected(
            detail=build_rejected_detail_fn(
                admission_detail=admission_http_detail_fn(admission),
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
                log_anchor=new_log_anchor_fn("admission"),
            )
        )

    degrade_plan = apply_admission_degrade_fn(payload, admission)
    if degrade_plan:
        admission["degrade_plan"] = degrade_plan
    return GenerateAdmissionResolution(reusable_response=None, admission=admission)
