from __future__ import annotations

from typing import Any, Dict, List

from backend.zhifei_autoplan.local_acceptance_hook import run_acceptance as _run_acceptance
from backend.zhifei_autoplan.local_acceptance_hook import validate_before_export as _validate_before_export
from backend.zhifei_autoplan.local_adapter_contract import (
    ensure_output_envelope,
    make_issue,
    normalize_input_envelope,
)
from backend.zhifei_autoplan.local_evidence_hook import build_evidence_summary as _build_evidence_summary


def normalize_input(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    return normalize_input_envelope(payload or {})


def map_output(raw_result: Dict[str, Any] | None) -> Dict[str, Any]:
    envelope = ensure_output_envelope(raw_result or {})
    acceptance = _run_acceptance(envelope)
    evidence_summary = acceptance.get("evidence_summary") or _build_evidence_summary(envelope)
    issues: List[Dict[str, Any]] = []
    issues.extend(envelope.get("issues") or [])
    issues.extend(acceptance.get("issues") or [])
    envelope["evidence_summary"] = evidence_summary
    envelope["hard_gates"] = acceptance.get("hard_gates") or []
    envelope["validator_report"] = {
        "adapter_acceptance": {
            "pass": acceptance.get("pass"),
            "export_allowed": acceptance.get("export_allowed"),
        }
    }
    envelope["issues"] = issues
    envelope["export_allowed"] = bool(acceptance.get("export_allowed")) and not issues
    envelope["status"] = "pass" if envelope["export_allowed"] else "fail_closed"
    return envelope


def run_acceptance(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    return _run_acceptance(envelope or {})


def build_evidence_summary(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    return _build_evidence_summary(envelope or {})


def validate_before_export(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    data = dict(envelope or {})
    if data.get("local_adapter") and isinstance(data["local_adapter"], dict):
        adapter = data["local_adapter"]
        issues = adapter.get("issues") or []
        if issues or adapter.get("export_allowed") is False:
            return {
                "status": "fail",
                "export_allowed": False,
                "issues": issues or [make_issue("LOCAL_ADAPTER_EXPORT_BLOCKED", "local adapter blocked export")],
                "hard_gates": adapter.get("hard_gates") or [],
                "evidence_summary": adapter.get("evidence_summary") or {},
            }
    return _validate_before_export(data)


def block_export_response(issues: Any) -> Dict[str, Any]:
    normalized = []
    for issue in issues or []:
        if isinstance(issue, dict):
            normalized.append(issue)
        else:
            normalized.append(make_issue("LOCAL_ADAPTER_EXPORT_BLOCKED", str(issue)))
    if not normalized:
        normalized.append(make_issue("LOCAL_ADAPTER_EXPORT_BLOCKED", "export blocked by local adapter"))
    return {
        "ok": False,
        "status": "blocked",
        "export_allowed": False,
        "issues": normalized,
    }
