from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class DownloadRequestFailure(Exception):
    code: str
    message: str
    next_action: str
    extra: dict[str, Any]


def resolve_download_request(
    *,
    job_id: str,
    job: dict[str, Any],
    result: dict[str, Any],
    kind: str,
    variant: int,
    build_download_resolution_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    requested_variant = max(1, int(variant or 1))
    status = str(job.get("status") or "").strip()
    if status != "done":
        raise DownloadRequestFailure(
            code="job_not_done",
            message=f"job not done: {status}",
            next_action="poll /actions/job_status until status=done",
            extra={"status": status, "kind": kind, "variant": requested_variant},
        )

    resolution = build_download_resolution_fn(
        job_id=job_id,
        result=result,
        kind=kind,
        variant=requested_variant,
    )
    if not resolution["valid_kind"]:
        raise DownloadRequestFailure(
            code="invalid_artifact_kind",
            message="invalid artifact kind",
            next_action="use one of the allowed download kinds",
            extra={
                "kind": kind,
                "variant": requested_variant,
                "allowed_kinds": resolution["allowed_kinds"],
            },
        )
    if not resolution["path_exists"]:
        raise DownloadRequestFailure(
            code="artifact_not_found",
            message="file not found",
            next_action="check result artifacts or rerun generation",
            extra={
                "kind": kind,
                "variant": requested_variant,
                "path": str(resolution.get("path") or ""),
                "download_index": resolution["download_index"],
            },
        )
    return resolution
