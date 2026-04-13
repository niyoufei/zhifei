from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.zhifei_autoplan import generate_admission_service as generate_admission_core
from backend.zhifei_autoplan import generate_queue_service as generate_queue_core


@dataclass
class GenerateRequestPayloadPrepareFailure(Exception):
    error_spec: dict[str, Any]
    cause: Exception


@dataclass
class GenerateRequestWorkerSpawnFailure(Exception):
    error_spec: dict[str, Any]
    cause: Exception


@dataclass
class GenerateRequestFailurePlan:
    status_code: int
    detail: dict[str, Any] | None = None
    error_spec: dict[str, Any] | None = None
    cause: Exception | None = None
    warning_log: dict[str, Any] | None = None


def execute_generate_request(
    *,
    raw_payload: dict[str, Any],
    session_id: str,
    workspace_dir: str,
    prepare_payload_fn: Callable[[dict[str, Any]], Any],
    resolve_admission_fn: Callable[..., Any],
    queue_generate_job_fn: Callable[..., dict[str, Any]],
    build_payload_prepare_error_fn: Callable[[str], dict[str, Any]],
    build_worker_spawn_error_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        prepared = prepare_payload_fn(raw_payload)
    except RuntimeError as exc:
        raise GenerateRequestPayloadPrepareFailure(
            error_spec=build_payload_prepare_error_fn(str(exc or "")),
            cause=exc,
        ) from exc
    except Exception as exc:
        raise GenerateRequestPayloadPrepareFailure(
            error_spec=build_payload_prepare_error_fn(""),
            cause=exc,
        ) from exc

    payload = prepared.payload
    request_signature = prepared.request_signature
    admission_resolution = resolve_admission_fn(
        payload=payload,
        session_id=session_id,
        workspace_dir=workspace_dir,
        request_signature=request_signature,
    )
    if admission_resolution.reusable_response is not None:
        return admission_resolution.reusable_response
    try:
        return queue_generate_job_fn(
            payload=payload,
            workspace_dir=workspace_dir,
            session_id=session_id,
            request_signature=request_signature,
            admission=admission_resolution.admission or {},
        )
    except generate_queue_core.GenerateWorkerSpawnFailure as exc:
        raise GenerateRequestWorkerSpawnFailure(
            error_spec=build_worker_spawn_error_fn(
                job_id=exc.job_id,
                request_id=exc.request_id,
                trace_id=exc.trace_id,
                worker_log_path=exc.worker_log_path,
            ),
            cause=exc.cause,
        ) from exc


def execute_generate_request_from_runtime(
    *,
    raw_payload: dict[str, Any],
    session_id: str,
    workspace_dir: str,
    prepare_runtime_payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    attach_contract_stamp_fn: Callable[[dict[str, Any]], Any],
    compute_job_signature_fn: Callable[[dict[str, Any]], str],
    find_reusable_job_fn: Callable[..., Any],
    evaluate_job_admission_fn: Callable[..., Any],
    admission_http_detail_fn: Callable[..., Any],
    append_resource_event_fn: Callable[..., Any],
    build_reused_response_fn: Callable[..., dict[str, Any]],
    build_rejection_event_fn: Callable[..., dict[str, Any]],
    build_rejected_detail_fn: Callable[..., dict[str, Any]],
    apply_admission_degrade_fn: Callable[..., Any],
    new_log_anchor_fn: Callable[[str], str],
    create_job_fn: Callable[..., str],
    spawn_generate_worker_fn: Callable[..., Any],
    update_job_fn: Callable[..., Any],
    append_worker_log_fn: Callable[..., Any],
    build_variant_plan_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    build_queued_response_fn: Callable[..., dict[str, Any]],
    build_payload_prepare_error_fn: Callable[[str], dict[str, Any]],
    build_worker_spawn_error_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    return execute_generate_request(
        raw_payload=raw_payload,
        session_id=session_id,
        workspace_dir=workspace_dir,
        prepare_payload_fn=lambda payload: __import__(
            "backend.zhifei_autoplan.generate_payload_service", fromlist=["prepare_generate_payload"]
        ).prepare_generate_payload(
            raw_payload=payload,
            prepare_runtime_payload_fn=prepare_runtime_payload_fn,
            attach_contract_stamp_fn=attach_contract_stamp_fn,
            compute_job_signature_fn=compute_job_signature_fn,
        ),
        resolve_admission_fn=lambda **kwargs: generate_admission_core.resolve_generate_admission(
            payload=kwargs["payload"],
            session_id=kwargs["session_id"],
            workspace_dir=kwargs["workspace_dir"],
            request_signature=kwargs["request_signature"],
            find_reusable_job_fn=find_reusable_job_fn,
            evaluate_job_admission_fn=evaluate_job_admission_fn,
            admission_http_detail_fn=admission_http_detail_fn,
            append_resource_event_fn=append_resource_event_fn,
            build_reused_response_fn=build_reused_response_fn,
            build_rejection_event_fn=build_rejection_event_fn,
            build_rejected_detail_fn=build_rejected_detail_fn,
            apply_admission_degrade_fn=apply_admission_degrade_fn,
            new_log_anchor_fn=new_log_anchor_fn,
        ),
        queue_generate_job_fn=lambda **kwargs: generate_queue_core.queue_generate_job(
            payload=kwargs["payload"],
            workspace_dir=kwargs["workspace_dir"],
            session_id=kwargs["session_id"],
            request_signature=kwargs["request_signature"],
            admission=kwargs["admission"],
            create_job_fn=create_job_fn,
            append_resource_event_fn=append_resource_event_fn,
            spawn_generate_worker_fn=spawn_generate_worker_fn,
            update_job_fn=update_job_fn,
            append_worker_log_fn=append_worker_log_fn,
            build_variant_plan_fn=build_variant_plan_fn,
            admission_http_detail_fn=admission_http_detail_fn,
            build_queued_response_fn=build_queued_response_fn,
        ),
        build_payload_prepare_error_fn=build_payload_prepare_error_fn,
        build_worker_spawn_error_fn=build_worker_spawn_error_fn,
    )


def translate_generate_request_failure(exc: Exception) -> GenerateRequestFailurePlan | None:
    if isinstance(exc, GenerateRequestPayloadPrepareFailure):
        return GenerateRequestFailurePlan(
            status_code=int(exc.error_spec["status_code"]),
            error_spec=exc.error_spec,
            cause=exc.cause,
        )
    if isinstance(exc, generate_admission_core.GenerateAdmissionRejected):
        rejected = exc.detail
        return GenerateRequestFailurePlan(
            status_code=429,
            detail=rejected,
            warning_log={
                "log_anchor": rejected["log_anchor"],
                "code": rejected.get("code"),
                "detail": rejected,
            },
        )
    if isinstance(exc, GenerateRequestWorkerSpawnFailure):
        return GenerateRequestFailurePlan(
            status_code=int(exc.error_spec["status_code"]),
            error_spec=exc.error_spec,
            cause=exc.cause,
        )
    return None
