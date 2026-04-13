from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def build_actions_download_resolution(
    *,
    job_id: str,
    result: dict[str, Any],
    kind: str,
    variant: int,
    download_kind_specs: dict[str, dict[str, str]],
    download_artifact_path_fn: Callable[[dict[str, Any], str, int], str | None],
    download_filename_fn: Callable[[str, str, int], str],
    build_download_index_fn: Callable[[str, dict[str, Any], int], dict[str, Any]],
) -> dict[str, Any]:
    requested_variant = max(1, int(variant or 1))
    if kind not in download_kind_specs:
        return {
            "requested_variant": requested_variant,
            "valid_kind": False,
            "allowed_kinds": sorted(download_kind_specs.keys()),
        }
    path = download_artifact_path_fn(result, kind, requested_variant)
    spec = download_kind_specs.get(kind) or download_kind_specs["docx"]
    path_exists = bool(path and Path(path).exists())
    return {
        "requested_variant": requested_variant,
        "valid_kind": True,
        "path": path,
        "path_exists": path_exists,
        "media_type": spec["media_type"],
        "filename": download_filename_fn(job_id, kind, requested_variant),
        "download_index": None if path_exists else build_download_index_fn(job_id, result, requested_variant),
    }


def build_actions_download_event_fields(
    *,
    job: dict[str, Any],
    job_id: str,
    kind: str,
    variant: int,
    file_path: str,
    file_size_bytes: int,
) -> dict[str, Any]:
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    return {
        "job_id": job_id,
        "kind": kind,
        "variant": max(1, int(variant or 1)),
        "file_path": str(file_path),
        "file_size_bytes": int(file_size_bytes),
        "project_id": payload.get("project_id"),
        "topic": payload.get("topic"),
        "request_id": payload.get("request_id"),
        "trace_id": payload.get("trace_id"),
    }
