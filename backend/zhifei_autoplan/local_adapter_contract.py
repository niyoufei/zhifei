from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

INPUT_FIELDS = (
    "project_id",
    "source_files",
    "tender_constraints",
    "scoring_items",
    "boq_items",
    "drawing_refs",
    "user_params",
    "missing_params",
    "evidence_refs",
)

OUTPUT_FIELDS = (
    "status",
    "sections",
    "score_matrix",
    "hard_gates",
    "evidence_summary",
    "validator_report",
    "export_allowed",
    "issues",
)

EVIDENCE_TYPES = {
    "file",
    "BOQ",
    "drawing",
    "user_param",
    "AI_inference",
    "missing_param",
    "quality",
}


def mark_missing_param(name: Any) -> str:
    label = str(name or "").strip() or "未命名参数"
    return f"需补充（缺：{label}）"


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value, key=lambda item: str(item))
    return [value]


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def make_issue(
    code: str,
    message: str,
    *,
    severity: str = "error",
    field: str | None = None,
    evidence_ref: str | None = None,
) -> Dict[str, Any]:
    issue: Dict[str, Any] = {
        "code": str(code or "local_adapter_issue"),
        "message": str(message or ""),
        "severity": str(severity or "error"),
    }
    if field:
        issue["field"] = str(field)
    if evidence_ref:
        issue["evidence_ref"] = str(evidence_ref)
    return issue


def normalize_input_envelope(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    source = dict(payload or {})
    envelope: Dict[str, Any] = {
        "project_id": str(source.get("project_id") or "").strip(),
        "source_files": _as_list(source.get("source_files") or source.get("files")),
        "tender_constraints": _as_dict(source.get("tender_constraints") or source.get("constraints")),
        "scoring_items": _as_list(source.get("scoring_items") or source.get("score_items")),
        "boq_items": _as_list(source.get("boq_items") or source.get("boq")),
        "drawing_refs": _as_list(source.get("drawing_refs") or source.get("drawings")),
        "user_params": _as_dict(source.get("user_params") or source.get("params")),
        "missing_params": _as_list(source.get("missing_params")),
        "evidence_refs": _as_list(source.get("evidence_refs") or source.get("evidence")),
    }
    envelope["_raw_keys"] = sorted(str(key) for key in source.keys())
    return envelope


def empty_output_envelope() -> Dict[str, Any]:
    return {
        "status": "pending",
        "sections": [],
        "score_matrix": {},
        "hard_gates": [],
        "evidence_summary": {},
        "validator_report": {},
        "export_allowed": False,
        "issues": [],
    }


def ensure_output_envelope(raw_result: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = dict(raw_result or {})
    envelope = empty_output_envelope()
    envelope["status"] = str(raw.get("status") or "generated")
    envelope["sections"] = _as_list(raw.get("sections"))
    envelope["score_matrix"] = deepcopy(
        raw.get("score_matrix") or raw.get("score_mapping") or raw.get("chapter_response_matrix") or {}
    )
    envelope["hard_gates"] = _as_list(raw.get("hard_gates"))
    envelope["evidence_summary"] = deepcopy(raw.get("evidence_summary") or raw.get("evidence_tracking") or {})
    envelope["validator_report"] = deepcopy(raw.get("validator_report") or raw.get("quality_checks") or {})
    envelope["export_allowed"] = bool(raw.get("export_allowed", False))
    envelope["issues"] = _as_list(raw.get("issues") or raw.get("issue_list"))
    envelope["_raw_result"] = raw
    return envelope


def merge_issues(*issue_groups: Iterable[Any]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for group in issue_groups:
        for item in group or []:
            if isinstance(item, dict):
                merged.append(dict(item))
            else:
                merged.append(make_issue("local_adapter_issue", str(item)))
    return merged
