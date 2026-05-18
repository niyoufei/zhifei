from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_APPROVAL_FIELDS = frozenset(
    {
        "contract_version",
        "approval_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "shadow_candidate_id",
        "patch_id",
        "approval_status",
        "approval_scope",
        "approval_decision",
        "approval_mode",
        "approver_role",
        "approver_id_placeholder",
        "approved_at",
        "approval_reason",
        "approval_comment",
        "approval_expires_at",
        "approval_audit_required",
        "approval_audit_ready",
        "evidence_anchor_status",
        "evidence_anchor_refs",
        "evidence_binding_status",
        "response_mode",
        "input_risk_level",
        "advisory_quality_gate_status",
        "readiness_status",
        "shadow_candidate_status",
        "patch_status",
        "diff_preview_required",
        "diff_preview_ready",
        "rollback_required",
        "rollback_plan_ready",
        "source_hash_revalidation_required",
        "source_hash_revalidation_ready",
        "formal_writeback_guard_required",
        "formal_writeback_guard_ready",
        "formal_writeback_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
        "blocked_reasons",
    }
)

APPROVAL_STATUSES = frozenset(
    {
        "not_requested",
        "blocked",
        "pending_human_review",
        "approved_shadow_only",
        "rejected",
        "expired",
        "revoked",
    }
)

APPROVAL_DECISIONS = frozenset(
    {
        "none",
        "approve_shadow_only",
        "reject",
        "request_revision",
        "revoke",
    }
)

APPROVAL_SCOPES = frozenset(
    {
        "shadow_candidate_only",
        "patch_preview_only",
        "single_section_candidate",
        "metadata_only",
    }
)

APPROVAL_MODES = frozenset(
    {
        "manual_required",
        "manual_received",
        "disabled_current_stage",
    }
)

CURRENT_STAGE_FORMAL_FLAGS = frozenset(
    {
        "formal_writeback_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
    }
)

_EVIDENCE_ANCHOR_STATUSES = frozenset(
    {
        "missing",
        "user_provided",
        "source_verified",
        "generated_advisory_only_blocked",
    }
)

_EVIDENCE_BINDING_STATUSES = frozenset(
    {
        "missing",
        "bound_to_user_provided_evidence",
        "bound_to_source_verified_evidence",
        "generated_advisory_only_blocked",
        "shadow_candidate_only_blocked",
        "patch_preview_only_blocked",
    }
)

_RESPONSE_MODES = frozenset(
    {
        "preview_advisory",
        "thinking_only_fallback",
        "unsupported",
        "blocked",
    }
)

_SHADOW_CANDIDATE_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_shadow_only",
        "ready_for_human_review",
        "approved_shadow_only",
        "rejected",
    }
)

_PATCH_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_patch_shadow_only",
        "ready_for_human_review",
        "approved_patch_shadow_only",
        "rejected",
    }
)

_APPROVER_PLACEHOLDERS = frozenset(
    {
        "",
        "manual-reviewer-placeholder",
        "reviewer-placeholder",
        "fake-reviewer-placeholder",
    }
)


def _text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value)


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _approval_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"approval-{digest[:16]}"


def _is_fake_approver_placeholder(value: str) -> bool:
    return value in _APPROVER_PLACEHOLDERS


def build_human_approval_gate(
    *,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    source_section_version: str,
    shadow_candidate_id: str,
    patch_id: str,
    approval_status: str,
    approval_scope: str,
    approval_decision: str,
    approval_mode: str,
    approver_role: str = "",
    approver_id_placeholder: str = "",
    approved_at: str = "",
    approval_reason: str = "",
    approval_comment: str = "",
    approval_expires_at: str = "",
    approval_audit_required: bool = True,
    approval_audit_ready: bool = False,
    evidence_anchor_status: str = "",
    evidence_anchor_refs: list[Any] | tuple[Any, ...] | None = None,
    evidence_binding_status: str = "",
    response_mode: str = "",
    input_risk_level: str = "",
    advisory_quality_gate_status: str = "",
    readiness_status: str = "",
    shadow_candidate_status: str = "",
    patch_status: str = "",
    diff_preview_required: bool = True,
    diff_preview_ready: bool = False,
    rollback_required: bool = True,
    rollback_plan_ready: bool = False,
    source_hash_revalidation_required: bool = True,
    source_hash_revalidation_ready: bool = False,
    formal_writeback_guard_required: bool = True,
    formal_writeback_guard_ready: bool = False,
    docx_export_requested: bool = False,
    zbid_writeback_requested: bool = False,
    output_write_requested: bool = False,
    formal_generation_requested: bool = False,
    review_apply_requested: bool = False,
    approval_id: str = "",
) -> dict[str, Any]:
    request_id = _text(request_id, limit=240)
    source_document_id = _text(source_document_id, limit=240)
    source_section_id = _text(source_section_id, limit=240)
    source_section_hash = _text(source_section_hash, limit=240)
    source_section_version = _text(source_section_version, limit=120)
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    patch_id = _text(patch_id, limit=240)
    approval_status = _text(approval_status, limit=120)
    approval_scope = _text(approval_scope, limit=120)
    approval_decision = _text(approval_decision, limit=120)
    approval_mode = _text(approval_mode, limit=120)
    approver_role = _text(approver_role, limit=120)
    approver_id_placeholder = _text(approver_id_placeholder, limit=240)
    approved_at = _text(approved_at, limit=120)
    approval_reason = _text(approval_reason)
    approval_comment = _text(approval_comment)
    approval_expires_at = _text(approval_expires_at, limit=120)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    evidence_binding_status = _text(evidence_binding_status, limit=120)
    response_mode = _text(response_mode, limit=120)
    input_risk_level = _text(input_risk_level, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120)
    readiness_status = _text(readiness_status, limit=120)
    shadow_candidate_status = _text(shadow_candidate_status, limit=120)
    patch_status = _text(patch_status, limit=120)
    evidence_refs = _list(evidence_anchor_refs)
    blocked_reasons: list[str] = []

    id_seed = {
        "contract_version": CONTRACT_VERSION,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
    }
    approval_id = _text(approval_id, limit=240) or _approval_id(id_seed)

    if not shadow_candidate_id:
        _append_unique(blocked_reasons, "missing_shadow_candidate_id")

    if not patch_id:
        _append_unique(blocked_reasons, "missing_patch_id")

    if shadow_candidate_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")
    elif shadow_candidate_status not in _SHADOW_CANDIDATE_STATUSES:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")

    if patch_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "patch_not_ready")
    elif patch_status not in _PATCH_STATUSES:
        _append_unique(blocked_reasons, "patch_not_ready")

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_approvable")
    elif response_mode in {"unsupported", "blocked"} or response_mode not in _RESPONSE_MODES:
        _append_unique(blocked_reasons, "unsupported_response_mode")

    if evidence_anchor_status == "missing":
        _append_unique(blocked_reasons, "missing_evidence_anchor")
    elif evidence_anchor_status not in _EVIDENCE_ANCHOR_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    if not evidence_refs:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    evidence_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }
    if evidence_binding_status in evidence_block_reasons:
        _append_unique(blocked_reasons, evidence_block_reasons[evidence_binding_status])
    elif evidence_binding_status not in _EVIDENCE_BINDING_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    if not source_section_hash:
        _append_unique(blocked_reasons, "missing_source_section_hash")

    if _bool(source_hash_revalidation_required) and not _bool(source_hash_revalidation_ready):
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")

    if _bool(diff_preview_required) and not _bool(diff_preview_ready):
        _append_unique(blocked_reasons, "diff_preview_missing")

    if _bool(rollback_required) and not _bool(rollback_plan_ready):
        _append_unique(blocked_reasons, "rollback_plan_missing")

    if _bool(formal_writeback_guard_required) and not _bool(formal_writeback_guard_ready):
        _append_unique(blocked_reasons, "formal_writeback_guard_missing")

    if approval_status == "approved_shadow_only":
        _append_unique(blocked_reasons, "approval_is_not_formal_writeback_permission")
    elif approval_status == "not_requested":
        _append_unique(blocked_reasons, "approval_not_requested")
    elif approval_status == "pending_human_review":
        _append_unique(blocked_reasons, "approval_pending_human_review")
    elif approval_status == "rejected":
        _append_unique(blocked_reasons, "approval_rejected")
    elif approval_status == "expired":
        _append_unique(blocked_reasons, "approval_expired")
    elif approval_status == "revoked":
        _append_unique(blocked_reasons, "approval_revoked")
    elif approval_status == "blocked":
        _append_unique(blocked_reasons, "approval_blocked")
    elif approval_status not in APPROVAL_STATUSES:
        _append_unique(blocked_reasons, "approval_blocked")

    if approval_decision not in APPROVAL_DECISIONS:
        _append_unique(blocked_reasons, "approval_audit_missing")

    if approval_scope not in APPROVAL_SCOPES:
        _append_unique(blocked_reasons, "approval_audit_missing")

    if approval_mode not in APPROVAL_MODES:
        _append_unique(blocked_reasons, "approval_audit_missing")

    if _bool(approval_audit_required):
        audit_values = {
            "approval_id": approval_id,
            "request_id": request_id,
            "source_document_id": source_document_id,
            "source_section_id": source_section_id,
            "source_section_hash": source_section_hash,
            "source_section_version": source_section_version,
            "shadow_candidate_id": shadow_candidate_id,
            "patch_id": patch_id,
            "approval_status": approval_status,
            "approval_decision": approval_decision,
            "approval_scope": approval_scope,
            "approver_role": approver_role,
        }
        if any(not value for value in audit_values.values()) or not _bool(approval_audit_ready):
            _append_unique(blocked_reasons, "approval_audit_missing")

    if not _is_fake_approver_placeholder(approver_id_placeholder):
        _append_unique(blocked_reasons, "real_personal_identity_not_allowed")

    if _bool(docx_export_requested):
        _append_unique(blocked_reasons, "docx_export_request_blocked")

    if _bool(zbid_writeback_requested):
        _append_unique(blocked_reasons, "zbid_writeback_request_blocked")

    if _bool(output_write_requested):
        _append_unique(blocked_reasons, "output_write_request_blocked")

    if _bool(formal_generation_requested):
        _append_unique(blocked_reasons, "formal_generation_request_blocked")

    if _bool(review_apply_requested):
        _append_unique(blocked_reasons, "review_apply_request_blocked")

    hard_reasons = [reason for reason in blocked_reasons if reason != "approval_is_not_formal_writeback_permission"]
    resolved_status = "blocked" if hard_reasons else approval_status

    return {
        "contract_version": CONTRACT_VERSION,
        "approval_id": approval_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "approval_status": resolved_status,
        "approval_scope": approval_scope,
        "approval_decision": approval_decision,
        "approval_mode": approval_mode,
        "approver_role": approver_role,
        "approver_id_placeholder": approver_id_placeholder,
        "approved_at": approved_at,
        "approval_reason": approval_reason,
        "approval_comment": approval_comment,
        "approval_expires_at": approval_expires_at,
        "approval_audit_required": _bool(approval_audit_required),
        "approval_audit_ready": _bool(approval_audit_ready),
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_anchor_refs": evidence_refs,
        "evidence_binding_status": evidence_binding_status,
        "response_mode": response_mode,
        "input_risk_level": input_risk_level,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "readiness_status": readiness_status,
        "shadow_candidate_status": shadow_candidate_status,
        "patch_status": patch_status,
        "diff_preview_required": _bool(diff_preview_required),
        "diff_preview_ready": _bool(diff_preview_ready),
        "rollback_required": _bool(rollback_required),
        "rollback_plan_ready": _bool(rollback_plan_ready),
        "source_hash_revalidation_required": _bool(source_hash_revalidation_required),
        "source_hash_revalidation_ready": _bool(source_hash_revalidation_ready),
        "formal_writeback_guard_required": _bool(formal_writeback_guard_required),
        "formal_writeback_guard_ready": _bool(formal_writeback_guard_ready),
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "docx_export_requested": _bool(docx_export_requested),
        "zbid_writeback_requested": _bool(zbid_writeback_requested),
        "output_write_requested": _bool(output_write_requested),
        "formal_generation_requested": _bool(formal_generation_requested),
        "review_apply_requested": _bool(review_apply_requested),
    }
