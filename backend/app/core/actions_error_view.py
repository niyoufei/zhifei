from __future__ import annotations

from typing import Any


def build_actions_error_detail(
    code: str,
    message: str,
    *,
    stage: str,
    log_anchor: str,
    job_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    next_action: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "ok": False,
        "code": str(code or "").strip() or "actions_error",
        "message": str(message or "").strip() or "actions error",
        "stage": str(stage or "").strip() or "unknown",
        "log_anchor": str(log_anchor or "").strip(),
    }
    if job_id:
        detail["job_id"] = str(job_id)
    if request_id:
        detail["request_id"] = str(request_id)
    if trace_id:
        detail["trace_id"] = str(trace_id)
    if next_action:
        detail["next_action"] = str(next_action)
    if isinstance(extra, dict) and extra:
        detail["extra"] = extra
    return detail
