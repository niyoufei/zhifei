from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict

from backend.zhifei_autoplan.prompt_registry import PROMPT_PREFIX_VERSION
from backend.zhifei_autoplan.terminology_guard import resolve_engineering_rules_path


REQUEST_CONTRACT_VERSION = "actions-generate-contract-v1"
STAGE_ARTIFACT_SCHEMA_VERSION = "stage-artifact-envelope-v1"
SECTION_CACHE_SCOPE_VERSION = "section-cache-scope-v2"
QUALITY_GATE_CONTRACT_VERSION = "hard-quality-gate-v1"
RESULT_BUNDLE_VERSION = "actions-result-bundle-v1"
SOURCE_PRIORITY_POLICY_VERSION = "source-priority-policy-v1"


def _json_digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except Exception:
        return None


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def _quality_gate_contract(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    thresholds = data.get("quality_gate_thresholds") if isinstance(data.get("quality_gate_thresholds"), dict) else {}
    return {
        "contract_version": QUALITY_GATE_CONTRACT_VERSION,
        "retry_rounds": int(data.get("quality_gate_retry_rounds") or 0),
        "auto_remediate": bool(data.get("auto_remediate", True)),
        "thresholds_sha1": _json_digest(thresholds),
    }


def build_contract_stamp(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    rules_path = resolve_engineering_rules_path()
    return {
        "request_contract_version": REQUEST_CONTRACT_VERSION,
        "stage_artifact_schema_version": STAGE_ARTIFACT_SCHEMA_VERSION,
        "section_cache_scope_version": SECTION_CACHE_SCOPE_VERSION,
        "result_bundle_version": RESULT_BUNDLE_VERSION,
        "source_priority_policy_version": SOURCE_PRIORITY_POLICY_VERSION,
        "prompt_prefix_version": PROMPT_PREFIX_VERSION,
        "engineering_rules": {
            "path": str(rules_path),
            "sha1": _file_digest(rules_path),
        },
        "quality_gate": _quality_gate_contract(data),
    }


def resolve_contract_stamp(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    base = build_contract_stamp(payload)
    if not isinstance(payload, dict):
        return base
    current = payload.get("_contract_stamp")
    if not isinstance(current, dict):
        return base
    merged = dict(base)
    for key, value in current.items():
        if key == "engineering_rules" and isinstance(value, dict):
            merged[key] = {**base.get(key, {}), **value}
            continue
        if key == "quality_gate" and isinstance(value, dict):
            merged[key] = {**base.get(key, {}), **value}
            continue
        merged[key] = value
    return merged


def attach_contract_stamp(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    payload["_contract_stamp"] = resolve_contract_stamp(payload)
    return payload


def contract_fingerprint(contract: Dict[str, Any] | None) -> str:
    return _json_digest(contract if isinstance(contract, dict) else {})


def infer_stage_name(filename: str | None) -> str:
    stem = Path(str(filename or "artifact.json")).stem
    parts = stem.split("_", 1)
    return parts[1] if len(parts) == 2 and parts[1].strip() else stem


def build_stage_artifact_envelope(
    *,
    filename: str,
    job_id: str,
    payload: Dict[str, Any] | Any,
    request_signature: str | None = None,
    contract_stamp: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    out = payload if isinstance(payload, dict) else {"payload": payload}
    out = dict(out)
    out["_artifact"] = {
        "schema": "zhifei.stage_artifact",
        "schema_version": STAGE_ARTIFACT_SCHEMA_VERSION,
        "stage": infer_stage_name(filename),
        "filename": str(filename or "artifact.json"),
        "job_id": str(job_id or "").strip(),
        "request_signature": str(request_signature or "").strip() or None,
        "contract": contract_stamp if isinstance(contract_stamp, dict) else {},
    }
    return out


def _artifact_entry(kind: str, path_value: Any) -> Dict[str, Any]:
    raw = str(path_value or "").strip()
    path = Path(raw) if raw else None
    exists = bool(path and path.exists())
    size_bytes = None
    if exists and path is not None:
        try:
            size_bytes = int(path.stat().st_size)
        except Exception:
            size_bytes = None
    return {
        "kind": str(kind or "").strip() or "artifact",
        "path": raw or None,
        "exists": exists,
        "size_bytes": size_bytes,
        "sha256": _file_sha256(path) if exists and path is not None else None,
    }


def build_result_bundle(
    *,
    job_id: str,
    payload: Dict[str, Any] | None,
    outputs: Dict[str, Any] | None,
    result_metadata: Dict[str, Any] | None,
    resource_usage_summary: Dict[str, Any] | None,
    variant_summary: Dict[str, Any] | None,
) -> Dict[str, Any]:
    contract = resolve_contract_stamp(payload)
    out = outputs if isinstance(outputs, dict) else {}
    artifacts = []
    for key, value in out.items():
        if isinstance(value, list):
            for item in value:
                artifacts.append(_artifact_entry(key, item))
            continue
        artifacts.append(_artifact_entry(key, value))
    return {
        "_bundle": {
            "schema": "zhifei.result_bundle",
            "schema_version": contract.get("result_bundle_version") or RESULT_BUNDLE_VERSION,
            "job_id": str(job_id or "").strip(),
            "generated_at": int(time.time()),
            "contract": contract,
        },
        "request": {
            "project_id": str((payload or {}).get("project_id") or "").strip() or None,
            "topic": str((payload or {}).get("topic") or "").strip() or None,
            "session_id": str((payload or {}).get("session_id") or "").strip() or None,
            "trace_id": str((payload or {}).get("trace_id") or "").strip() or None,
            "request_id": str((payload or {}).get("request_id") or "").strip() or None,
            "case_library": (payload or {}).get("case_library") if isinstance((payload or {}).get("case_library"), dict) else {},
            "image_library": (payload or {}).get("image_library") if isinstance((payload or {}).get("image_library"), dict) else {},
        },
        "outputs": out,
        "artifacts": artifacts,
        "variant_summary": variant_summary if isinstance(variant_summary, dict) else {},
        "result_metadata": result_metadata if isinstance(result_metadata, dict) else {},
        "resource_usage_summary": resource_usage_summary if isinstance(resource_usage_summary, dict) else {},
    }


def load_result_bundle(path: str | Path | None) -> Dict[str, Any] | None:
    raw = str(path or "").strip()
    if not raw:
        return None
    target = Path(raw)
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    bundle_meta = data.get("_bundle") if isinstance(data.get("_bundle"), dict) else {}
    if str(bundle_meta.get("schema") or "").strip() != "zhifei.result_bundle":
        return None
    return data


def extract_outputs_from_result_bundle(bundle: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(bundle, dict):
        return {}
    outputs = bundle.get("outputs")
    if isinstance(outputs, dict):
        return dict(outputs)
    grouped: Dict[str, Any] = {}
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), list) else []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        path = str(item.get("path") or "").strip()
        if not kind:
            continue
        if kind in {"docx", "compare_docx", "focus_xlsx", "score_overview_xlsx", "expert_review_docx"}:
            rows = grouped.setdefault(kind, [])
            if path:
                rows.append(path)
            continue
        grouped[kind] = path or None
    return grouped


def result_bundle_artifacts_complete(bundle: Dict[str, Any] | None) -> bool:
    if not isinstance(bundle, dict):
        return False
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), list) else []
    seen = 0
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("path") or "").strip()
        if not raw:
            continue
        seen += 1
        path = Path(raw)
        if not path.exists():
            return False
        expected_sha256 = str(item.get("sha256") or "").strip()
        if expected_sha256:
            actual_sha256 = _file_sha256(path)
            if not actual_sha256 or actual_sha256 != expected_sha256:
                return False
    return seen > 0
