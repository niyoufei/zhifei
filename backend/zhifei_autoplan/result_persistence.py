from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict

from backend.zhifei_autoplan.run_contract import build_result_bundle


def resolve_result_bundle_path(
    job_id: str,
    *,
    outputs: Dict[str, Any],
    fallback_build_dir: str | Path | None = None,
) -> Path:
    json_path = str(outputs.get("json") or "").strip()
    if json_path:
        return Path(json_path).with_name(f"{Path(json_path).stem}_result_bundle.json")
    build_dir = Path(fallback_build_dir) if fallback_build_dir else Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    return build_dir / f"actions_{str(job_id or '').strip() or 'unknown'}_result_bundle.json"


def write_result_bundle_file(
    job_id: str,
    *,
    payload: Dict[str, Any],
    outputs: Dict[str, Any],
    result_metadata: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    variant_summary: Dict[str, Any],
    fallback_build_dir: str | Path | None = None,
    normalizer: Callable[[Any], Any] | None = None,
) -> str:
    target = resolve_result_bundle_path(
        job_id,
        outputs=outputs,
        fallback_build_dir=fallback_build_dir,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_result_bundle(
        job_id=job_id,
        payload=payload,
        outputs=outputs,
        result_metadata=result_metadata,
        resource_usage_summary=resource_usage_summary,
        variant_summary=variant_summary,
    )
    payload_to_write = normalizer(bundle) if callable(normalizer) else bundle
    target.write_text(json.dumps(payload_to_write, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def build_job_result_payload(
    *,
    outputs: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    result_bundle_json: str,
    result_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        **outputs,
        "resource_usage_summary": resource_usage_summary,
        "result_bundle_json": result_bundle_json,
        **result_metadata,
    }
