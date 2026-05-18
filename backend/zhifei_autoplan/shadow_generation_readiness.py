from __future__ import annotations

from typing import Any


SHADOW_READINESS_NOT_READY = "not_ready"
SHADOW_READINESS_REVIEW_REQUIRED = "review_required"
SHADOW_READINESS_BLOCKED = "blocked"
SHADOW_READINESS_CANDIDATE_FORBIDDEN = "shadow_candidate_forbidden"
SHADOW_READINESS_SYSTEM_ERROR = "system_error"

FORMAL_GENERATION_ALLOWED = False
SHADOW_CANDIDATE_ALLOWED = False
CANDIDATE_PATCH_ALLOWED = False
WRITEBACK_ALLOWED = False
EXPORT_ALLOWED = False
ZBID_WRITEBACK_ALLOWED = False

_BLOCKING_QUALITY_STATUSES = {"blocked", "system_error"}
_REVIEW_QUALITY_STATUSES = {"review_required"}
_BLOCKING_INPUT_RISK_STATUSES = {"blocked", "system_error"}
_REVIEW_INPUT_RISK_STATUSES = {"review_required"}
_BLOCKING_EVIDENCE_STATUSES = {"invalid_anchor", "conflicting", "system_error"}
_FORBIDDEN_EVIDENCE_STATUSES = {"missing", "unverified"}
_STABLE_RESPONSE_MODES = {"response_advisory", "json_advisory", "text_fallback"}
_UNSTABLE_RESPONSE_MODES = {
    "",
    "unknown",
    "thinking_only_fallback",
    "empty_response",
    "malformed_response",
    "normalization_failure",
    "system_error",
}
_FORMAL_TRUE_FLAGS = {
    "formal_generation_allowed": "formal_generation_allowed_unsafe",
    "shadow_candidate_allowed": "shadow_candidate_allowed_unsafe",
    "writeback_allowed": "writeback_allowed_unsafe",
    "export_allowed": "export_allowed_unsafe",
    "zbid_writeback_allowed": "zbid_writeback_allowed_unsafe",
}
_CANDIDATE_INTENT_FIELDS = {
    "candidate_id",
    "candidate_type",
    "candidate_patch_requested",
    "candidate_patch_attempted",
    "shadow_candidate_requested",
    "proposed_text",
    "patch_type",
    "patch_scope",
}
_VALID_APPROVAL_STATUSES = {"pending", "approved", "rejected", "revised", "hold"}

SHADOW_READINESS_PUBLIC_FIELDS = (
    "shadow_readiness_status",
    "shadow_readiness_level",
    "shadow_readiness_reasons",
    "shadow_readiness_blockers",
    "shadow_readiness_warnings",
    "shadow_candidate_allowed",
    "shadow_candidate_forbidden",
    "shadow_candidate_reason",
    "candidate_patch_allowed",
    "candidate_patch_blockers",
    "human_review_required",
    "approval_required",
    "approval_status",
    "diff_required",
    "diff_available",
    "rollback_required",
    "rollback_available",
    "rollback_token",
    "evidence_trace_required",
    "evidence_trace_status",
    "formal_generation_allowed",
    "writeback_allowed",
    "export_allowed",
    "zbid_writeback_allowed",
    "no_write",
    "preview_only",
    "trace_id",
)


def _text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _bool_value(payload: dict[str, Any], field: str, *, default: bool) -> bool:
    value = payload.get(field, default)
    if isinstance(value, bool):
        return value
    return bool(value)


def _candidate_intent(payload: dict[str, Any]) -> bool:
    return any(bool(payload.get(field)) for field in _CANDIDATE_INTENT_FIELDS)


def _diff_available(payload: dict[str, Any]) -> bool:
    return bool(_text(payload.get("diff_summary"), limit=400) or _text(payload.get("diff_scope"), limit=120))


def _rollback_available(payload: dict[str, Any]) -> bool:
    if payload.get("rollback_available") is False:
        return False
    return bool(_text(payload.get("rollback_token"), limit=240))


def _approval_status(payload: dict[str, Any]) -> str:
    status = _text(payload.get("approval_status"), limit=80).lower()
    return status if status in _VALID_APPROVAL_STATUSES else "pending"


def _level_for(status: str, blockers: list[str], warnings: list[str]) -> str:
    if status == SHADOW_READINESS_SYSTEM_ERROR:
        return "system_error"
    if any(item.endswith("_unsafe") or item.startswith("formal_flag:") for item in blockers):
        return "P0"
    if status == SHADOW_READINESS_BLOCKED:
        return "P1"
    if status == SHADOW_READINESS_CANDIDATE_FORBIDDEN:
        return "P2"
    if status == SHADOW_READINESS_REVIEW_REQUIRED or warnings:
        return "P3"
    return "P4"


def _result(
    *,
    payload: dict[str, Any],
    status: str,
    reasons: list[str] | None = None,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    candidate_patch_blockers: list[str] | None = None,
    trace_id: str = "",
) -> dict[str, Any]:
    reason_list = list(reasons or [])
    blocker_list = list(blockers or [])
    warning_list = list(warnings or [])
    candidate_blocker_list = list(candidate_patch_blockers or [])
    if not reason_list and blocker_list:
        reason_list = [blocker_list[0]]
    if not reason_list:
        reason_list = ["shadow_readiness_not_enabled"]
    approval_status = _approval_status(payload)
    diff_available = _diff_available(payload)
    rollback_available = _rollback_available(payload)
    rollback_token = _text(payload.get("rollback_token"), limit=240)
    no_write = _bool_value(payload, "no_write", default=True)
    preview_only = _bool_value(payload, "preview_only", default=True)
    evidence_status = _text(payload.get("evidence_anchor_status"), limit=80) or "not_required"
    shadow_forbidden = status in {
        SHADOW_READINESS_BLOCKED,
        SHADOW_READINESS_CANDIDATE_FORBIDDEN,
        SHADOW_READINESS_SYSTEM_ERROR,
    }
    return {
        "shadow_readiness_status": status,
        "shadow_readiness_level": _level_for(status, blocker_list, warning_list),
        "shadow_readiness_reasons": reason_list,
        "shadow_readiness_blockers": blocker_list,
        "shadow_readiness_warnings": warning_list,
        "shadow_candidate_allowed": SHADOW_CANDIDATE_ALLOWED,
        "shadow_candidate_forbidden": bool(shadow_forbidden),
        "shadow_candidate_reason": blocker_list[0] if blocker_list else reason_list[0],
        "candidate_patch_allowed": CANDIDATE_PATCH_ALLOWED,
        "candidate_patch_blockers": candidate_blocker_list,
        "human_review_required": True,
        "approval_required": True,
        "approval_status": approval_status,
        "diff_required": True,
        "diff_available": diff_available,
        "rollback_required": True,
        "rollback_available": rollback_available,
        "rollback_token": rollback_token,
        "evidence_trace_required": bool(
            payload.get("evidence_anchor_required")
            or _candidate_intent(payload)
            or evidence_status not in {"not_required", ""}
        ),
        "evidence_trace_status": evidence_status,
        "formal_generation_allowed": FORMAL_GENERATION_ALLOWED,
        "writeback_allowed": WRITEBACK_ALLOWED,
        "export_allowed": EXPORT_ALLOWED,
        "zbid_writeback_allowed": ZBID_WRITEBACK_ALLOWED,
        "no_write": no_write,
        "preview_only": preview_only,
        "trace_id": trace_id,
    }


def evaluate_shadow_generation_readiness(
    readiness_input: Any,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(readiness_input, dict):
            return _result(
                payload={},
                status=SHADOW_READINESS_SYSTEM_ERROR,
                blockers=["shadow_readiness_input_must_be_object"],
                trace_id="",
            )
        payload = dict(readiness_input)
        context = dict(context or {})
        trace_id = _text(payload.get("trace_id") or payload.get("request_id") or context.get("request_id"), limit=120)
        blockers: list[str] = []
        warnings: list[str] = []
        reasons: list[str] = []
        candidate_patch_blockers: list[str] = []
        forbidden = False

        if _bool_value(payload, "no_write", default=True) is False:
            _append_unique(blockers, "no_write_unsafe")
        if _bool_value(payload, "preview_only", default=True) is False:
            _append_unique(blockers, "preview_only_unsafe")
        if _bool_value(payload, "affects_generation", default=False) is True:
            _append_unique(blockers, "affects_generation_unsafe")
        if _bool_value(payload, "affects_export", default=False) is True:
            _append_unique(blockers, "affects_export_unsafe")

        for field, blocker in _FORMAL_TRUE_FLAGS.items():
            if payload.get(field) is True:
                _append_unique(blockers, blocker)
                _append_unique(candidate_patch_blockers, blocker)

        quality_status = _text(payload.get("quality_status"), limit=80)
        if quality_status in _BLOCKING_QUALITY_STATUSES:
            _append_unique(blockers, f"quality_status:{quality_status}")
            _append_unique(candidate_patch_blockers, "quality_blocked")
        elif quality_status in _REVIEW_QUALITY_STATUSES:
            _append_unique(warnings, f"quality_status:{quality_status}")
            _append_unique(reasons, "quality_review_required")

        input_risk_status = _text(payload.get("input_risk_status"), limit=80)
        if input_risk_status in _BLOCKING_INPUT_RISK_STATUSES:
            _append_unique(blockers, f"input_risk_status:{input_risk_status}")
            _append_unique(candidate_patch_blockers, "input_risk_blocked")
        elif input_risk_status in _REVIEW_INPUT_RISK_STATUSES:
            _append_unique(warnings, f"input_risk_status:{input_risk_status}")
            _append_unique(reasons, "input_risk_review_required")

        evidence_status = _text(payload.get("evidence_anchor_status"), limit=80) or "not_required"
        if evidence_status in _BLOCKING_EVIDENCE_STATUSES:
            _append_unique(blockers, f"evidence_anchor_status:{evidence_status}")
            _append_unique(candidate_patch_blockers, f"evidence_{evidence_status}")
        elif evidence_status in _FORBIDDEN_EVIDENCE_STATUSES:
            forbidden = True
            _append_unique(warnings, f"evidence_anchor_status:{evidence_status}")
            _append_unique(reasons, f"evidence_{evidence_status}_not_shadow_candidate")
            _append_unique(candidate_patch_blockers, f"evidence_{evidence_status}")

        if payload.get("generated_preview_as_evidence_detected") is True:
            _append_unique(blockers, "generated_preview_as_evidence")
            _append_unique(candidate_patch_blockers, "generated_preview_as_evidence")

        response_mode = _text(payload.get("response_mode") or payload.get("preview_mode"), limit=80)
        thinking_fallback = bool(payload.get("thinking_fallback_detected")) or response_mode == "thinking_only_fallback"
        if thinking_fallback:
            forbidden = True
            _append_unique(warnings, "thinking_only_fallback")
            _append_unique(reasons, "thinking_only_fallback_not_shadow_candidate")
            _append_unique(candidate_patch_blockers, "thinking_only_fallback")
        elif response_mode in _UNSTABLE_RESPONSE_MODES:
            _append_unique(warnings, "response_mode_unstable_or_unknown")
            _append_unique(reasons, "response_mode_unstable_or_unknown")
        elif response_mode and response_mode not in _STABLE_RESPONSE_MODES:
            _append_unique(warnings, "response_mode_unrecognized")
            _append_unique(reasons, "response_mode_unstable_or_unknown")

        candidate_intent = _candidate_intent(payload)
        diff_available = _diff_available(payload)
        rollback_available = _rollback_available(payload)
        approval_status = _approval_status(payload)
        has_evidence = evidence_status == "anchored" and bool(_list_value(payload.get("evidence_sources")))
        if candidate_intent:
            if not has_evidence:
                _append_unique(blockers, "candidate_patch_without_evidence")
                _append_unique(candidate_patch_blockers, "candidate_patch_without_evidence")
            if not diff_available:
                _append_unique(blockers, "candidate_patch_without_diff")
                _append_unique(candidate_patch_blockers, "diff_summary_missing")
            if not rollback_available:
                _append_unique(blockers, "candidate_patch_without_rollback")
                _append_unique(candidate_patch_blockers, "rollback_token_missing")
            if approval_status != "approved":
                _append_unique(reasons, "human_approval_required")
                _append_unique(candidate_patch_blockers, f"approval_{approval_status}")

        if approval_status == "rejected":
            _append_unique(candidate_patch_blockers, "approval_rejected")
            _append_unique(reasons, "approval_rejected")
        elif approval_status == "hold":
            _append_unique(candidate_patch_blockers, "approval_hold")
            _append_unique(reasons, "approval_hold")
        elif approval_status == "revised":
            _append_unique(candidate_patch_blockers, "approval_revised_requires_new_candidate")
            _append_unique(reasons, "approval_revised_requires_new_candidate")
        elif approval_status == "approved":
            if not trace_id:
                _append_unique(warnings, "approved_candidate_missing_trace_id")
                _append_unique(reasons, "approved_candidate_missing_trace_id")
            if not diff_available:
                _append_unique(blockers, "approved_candidate_missing_diff")
                _append_unique(candidate_patch_blockers, "approved_candidate_missing_diff")
            if not has_evidence:
                _append_unique(warnings, "approved_candidate_missing_evidence_anchor")
                _append_unique(reasons, "approved_candidate_missing_evidence_anchor")

        if payload.get("docx_export_requested") or payload.get("calls_export_docx_route"):
            _append_unique(blockers, "docx_export_from_shadow_candidate_blocked")
            _append_unique(candidate_patch_blockers, "docx_export_blocked")
        if payload.get("zbid_writeback_requested") or payload.get("calls_zbid_writeback"):
            _append_unique(blockers, "zbid_writeback_from_shadow_candidate_blocked")
            _append_unique(candidate_patch_blockers, "zbid_writeback_blocked")

        if blockers:
            status = SHADOW_READINESS_BLOCKED
        elif forbidden:
            status = SHADOW_READINESS_CANDIDATE_FORBIDDEN
        elif reasons or warnings:
            status = SHADOW_READINESS_REVIEW_REQUIRED
        else:
            status = SHADOW_READINESS_NOT_READY
            _append_unique(reasons, "shadow_candidate_not_enabled")

        return _result(
            payload=payload,
            status=status,
            reasons=reasons,
            blockers=blockers,
            warnings=warnings,
            candidate_patch_blockers=candidate_patch_blockers,
            trace_id=trace_id,
        )
    except Exception:
        return _result(
            payload={},
            status=SHADOW_READINESS_SYSTEM_ERROR,
            blockers=["shadow_readiness_exception"],
            trace_id="",
        )
