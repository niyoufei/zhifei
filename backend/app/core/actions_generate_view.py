from __future__ import annotations

from typing import Any


def build_generate_payload_prepare_error(raw_reason: str) -> dict[str, Any]:
    raw = str(raw_reason or "").strip()
    if raw.startswith("text_provider_not_configured"):
        return {
            "status_code": 503,
            "code": "provider_not_configured",
            "message": "text provider not configured",
            "stage": "payload_prepare",
            "next_action": "configure text provider env keys or use dry_run=true",
            "extra": {"reason": raw},
        }
    detail = {
        "status_code": 500,
        "code": "payload_prepare_failed",
        "message": "failed to prepare runtime payload",
        "stage": "payload_prepare",
        "next_action": "check server logs for payload preparation failure",
    }
    if raw:
        detail["extra"] = {"reason": raw}
    return detail


def build_generate_worker_spawn_error(
    *,
    job_id: str,
    request_id: Any,
    trace_id: Any,
    worker_log_path: str,
) -> dict[str, Any]:
    return {
        "status_code": 500,
        "code": "worker_spawn_failed",
        "message": "worker spawn failed",
        "stage": "worker_spawn",
        "job_id": job_id,
        "request_id": request_id,
        "trace_id": trace_id,
        "next_action": "check worker log and subprocess spawn permissions",
        "extra": {"worker_log_path": worker_log_path},
    }


def build_generate_async_rejection_event(
    *,
    payload: dict[str, Any],
    admission: dict[str, Any],
    request_signature: str,
) -> dict[str, Any]:
    return {
        "request_signature": request_signature,
        "request_id": payload.get("request_id"),
        "trace_id": payload.get("trace_id"),
        "project_id": payload.get("project_id"),
        "topic": payload.get("topic"),
        "variants": int(payload.get("variants") or 1),
        "rejection_code": admission.get("code"),
        "rejection_scope": admission.get("scope"),
        "next_action": admission.get("next_action"),
        "usage": admission.get("usage"),
        "limits": admission.get("limits"),
    }


def build_generate_async_rejected_detail(
    *,
    admission_detail: dict[str, Any],
    request_id: Any,
    trace_id: Any,
    log_anchor: str,
) -> dict[str, Any]:
    rejected = dict(admission_detail)
    rejected["ok"] = False
    rejected["message"] = "job admission rejected"
    rejected["stage"] = "admission"
    rejected["log_anchor"] = log_anchor
    rejected["request_id"] = request_id
    rejected["trace_id"] = trace_id
    return rejected


def build_generate_async_reused_response(reusable: dict[str, Any], admission_detail: dict[str, Any]) -> dict[str, Any]:
    payload = reusable.get("payload") if isinstance(reusable.get("payload"), dict) else {}
    return {
        "ok": True,
        "job_id": reusable.get("job_id"),
        "status": reusable.get("status"),
        "reused": True,
        "reuse_reason": "same_payload",
        "admission": dict(admission_detail),
        "request_id": payload.get("request_id"),
        "trace_id": payload.get("trace_id"),
    }


def build_generate_async_queued_response(
    *,
    job_id: str,
    workspace_dir: str,
    session_id: str,
    admission_detail: dict[str, Any],
    request_id: Any,
    trace_id: Any,
) -> dict[str, Any]:
    return {
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "workspace_dir": workspace_dir,
        "session_id": session_id,
        "admission": dict(admission_detail),
        "request_id": request_id,
        "trace_id": trace_id,
    }
