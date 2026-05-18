from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_DIFF_PREVIEW_FIELDS = frozenset(
    {
        "contract_version",
        "diff_preview_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "shadow_candidate_id",
        "patch_id",
        "approval_id",
        "diff_preview_status",
        "diff_scope",
        "diff_format",
        "diff_operation_type",
        "diff_summary_preview",
        "diff_operations_preview",
        "before_text_hash",
        "after_text_preview_hash",
        "patch_operations_preview_hash",
        "affected_anchor_refs",
        "evidence_anchor_status",
        "evidence_anchor_refs",
        "evidence_binding_status",
        "response_mode",
        "input_risk_level",
        "advisory_quality_gate_status",
        "readiness_status",
        "shadow_candidate_status",
        "patch_status",
        "approval_status",
        "human_approval_required",
        "human_approval_received",
        "source_hash_revalidation_required",
        "source_hash_revalidation_ready",
        "rollback_required",
        "rollback_plan_ready",
        "formal_writeback_guard_required",
        "formal_writeback_guard_ready",
        "generated_at",
        "model_provider",
        "model_name",
        "formal_writeback_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
        "blocked_reasons",
    }
)

DIFF_PREVIEW_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_diff_shadow_only",
        "ready_for_human_review",
        "approved_diff_shadow_only",
        "rejected",
        "stale_source_hash",
    }
)

CURRENT_STAGE_EMITTABLE_DIFF_PREVIEW_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "stale_source_hash",
    }
)

DIFF_SCOPES = frozenset(
    {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
)

DIFF_FORMATS = frozenset(
    {
        "text_diff_preview",
        "structured_diff_preview",
        "metadata_only",
    }
)

DIFF_OPERATION_TYPES = frozenset(
    {
        "no_op",
        "replace",
        "insert",
        "delete",
        "reorder",
        "mixed",
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
        "diff_preview_only_blocked",
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


def _diff_preview_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"diff-preview-{digest[:16]}"


def build_diff_preview(
    *,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    source_section_version: str,
    shadow_candidate_id: str,
    patch_id: str,
    approval_id: str,
    diff_scope: str = "",
    diff_format: str = "metadata_only",
    diff_operation_type: str = "no_op",
    diff_summary_preview: str = "",
    diff_operations_preview: list[Any] | tuple[Any, ...] | None = None,
    before_text_hash: str = "",
    after_text_preview_hash: str = "",
    patch_operations_preview_hash: str = "",
    affected_anchor_refs: list[Any] | tuple[Any, ...] | None = None,
    evidence_anchor_status: str = "",
    evidence_anchor_refs: list[Any] | tuple[Any, ...] | None = None,
    evidence_binding_status: str = "",
    response_mode: str = "",
    input_risk_level: str = "",
    advisory_quality_gate_status: str = "",
    readiness_status: str = "",
    shadow_candidate_status: str = "",
    patch_status: str = "",
    approval_status: str = "",
    human_approval_required: bool = True,
    human_approval_received: bool = False,
    source_hash_revalidation_required: bool = True,
    source_hash_revalidation_ready: bool = False,
    source_section_hash_match: bool = True,
    diff_base_hash_match: bool = True,
    rollback_required: bool = True,
    rollback_plan_ready: bool = False,
    formal_writeback_guard_required: bool = True,
    formal_writeback_guard_ready: bool = False,
    generated_at: str,
    model_provider: str = "",
    model_name: str = "",
    docx_export_requested: bool = False,
    zbid_writeback_requested: bool = False,
    output_write_requested: bool = False,
    formal_generation_requested: bool = False,
    review_apply_requested: bool = False,
    diff_preview_status: str = "not_created",
    diff_preview_id: str = "",
) -> dict[str, Any]:
    request_id = _text(request_id, limit=240)
    source_document_id = _text(source_document_id, limit=240)
    source_section_id = _text(source_section_id, limit=240)
    source_section_hash = _text(source_section_hash, limit=240)
    source_section_version = _text(source_section_version, limit=120)
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    patch_id = _text(patch_id, limit=240)
    approval_id = _text(approval_id, limit=240)
    diff_scope = _text(diff_scope, limit=120)
    diff_format = _text(diff_format, limit=120)
    diff_operation_type = _text(diff_operation_type, limit=120)
    diff_summary_preview = _text(diff_summary_preview)
    before_text_hash = _text(before_text_hash, limit=240)
    after_text_preview_hash = _text(after_text_preview_hash, limit=240)
    patch_operations_preview_hash = _text(patch_operations_preview_hash, limit=240)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    evidence_binding_status = _text(evidence_binding_status, limit=120)
    response_mode = _text(response_mode, limit=120)
    input_risk_level = _text(input_risk_level, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120)
    readiness_status = _text(readiness_status, limit=120)
    shadow_candidate_status = _text(shadow_candidate_status, limit=120)
    patch_status = _text(patch_status, limit=120)
    approval_status = _text(approval_status, limit=120)
    generated_at = _text(generated_at, limit=120)
    model_provider = _text(model_provider, limit=120)
    model_name = _text(model_name, limit=120)
    requested_status = _text(diff_preview_status, limit=120)
    diff_operations = _list(diff_operations_preview)
    affected_refs = _list(affected_anchor_refs)
    evidence_refs = _list(evidence_anchor_refs)
    source_section_hash_match = _bool(source_section_hash_match)
    diff_base_hash_match = _bool(diff_base_hash_match)
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
        "approval_id": approval_id,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
    }
    diff_preview_id = _text(diff_preview_id, limit=240) or _diff_preview_id(id_seed)

    if requested_status == "approved_diff_shadow_only":
        _append_unique(blocked_reasons, "diff_preview_is_not_formal_writeback_permission")
    elif requested_status not in DIFF_PREVIEW_STATUSES:
        _append_unique(blocked_reasons, "invalid_diff_preview_status")

    if diff_scope not in DIFF_SCOPES:
        _append_unique(blocked_reasons, "invalid_diff_scope")

    if diff_format not in DIFF_FORMATS:
        _append_unique(blocked_reasons, "invalid_diff_format")

    if diff_operation_type not in DIFF_OPERATION_TYPES:
        _append_unique(blocked_reasons, "invalid_diff_operation_type")

    if not shadow_candidate_id:
        _append_unique(blocked_reasons, "missing_shadow_candidate_id")

    if not patch_id:
        _append_unique(blocked_reasons, "missing_patch_id")

    if not approval_id:
        _append_unique(blocked_reasons, "missing_approval_id")

    if shadow_candidate_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")
    elif shadow_candidate_status not in _SHADOW_CANDIDATE_STATUSES:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")

    if patch_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "patch_not_ready")
    elif patch_status not in _PATCH_STATUSES:
        _append_unique(blocked_reasons, "patch_not_ready")

    if approval_status != "approved_shadow_only":
        _append_unique(blocked_reasons, "approval_not_received")

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_diff_capable")
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
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
    }
    if evidence_binding_status in evidence_block_reasons:
        _append_unique(blocked_reasons, evidence_block_reasons[evidence_binding_status])
    elif evidence_binding_status not in _EVIDENCE_BINDING_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    preview_values = {diff_summary_preview, str(diff_operations)} - {""}
    if preview_values and any(str(ref) in preview_values for ref in evidence_refs):
        _append_unique(blocked_reasons, "diff_preview_cannot_be_evidence")

    if not source_section_hash:
        _append_unique(blocked_reasons, "missing_source_section_hash")

    stale_source_hash = False
    if not source_section_hash_match:
        _append_unique(blocked_reasons, "stale_source_hash")
        stale_source_hash = True

    if not diff_base_hash_match:
        _append_unique(blocked_reasons, "diff_base_hash_mismatch")
        stale_source_hash = True

    if _bool(source_hash_revalidation_required) and not _bool(source_hash_revalidation_ready):
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")

    if not before_text_hash:
        _append_unique(blocked_reasons, "missing_before_text_hash")

    if not after_text_preview_hash:
        _append_unique(blocked_reasons, "missing_after_text_preview_hash")

    if not patch_operations_preview_hash:
        _append_unique(blocked_reasons, "missing_patch_operations_preview_hash")

    if _bool(human_approval_required) and not _bool(human_approval_received):
        _append_unique(blocked_reasons, "human_approval_missing")

    if _bool(rollback_required) and not _bool(rollback_plan_ready):
        _append_unique(blocked_reasons, "rollback_plan_missing")

    if _bool(formal_writeback_guard_required) and not _bool(formal_writeback_guard_ready):
        _append_unique(blocked_reasons, "formal_writeback_guard_missing")

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

    _append_unique(blocked_reasons, "real_diff_not_implemented_current_stage")

    status = "not_created"
    if blocked_reasons:
        status = "stale_source_hash" if stale_source_hash else "blocked"

    return {
        "contract_version": CONTRACT_VERSION,
        "diff_preview_id": diff_preview_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "approval_id": approval_id,
        "diff_preview_status": status,
        "diff_scope": diff_scope,
        "diff_format": diff_format,
        "diff_operation_type": diff_operation_type,
        "diff_summary_preview": diff_summary_preview,
        "diff_operations_preview": diff_operations,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "affected_anchor_refs": affected_refs,
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_anchor_refs": evidence_refs,
        "evidence_binding_status": evidence_binding_status,
        "response_mode": response_mode,
        "input_risk_level": input_risk_level,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "readiness_status": readiness_status,
        "shadow_candidate_status": shadow_candidate_status,
        "patch_status": patch_status,
        "approval_status": approval_status,
        "human_approval_required": _bool(human_approval_required),
        "human_approval_received": _bool(human_approval_received),
        "source_hash_revalidation_required": _bool(source_hash_revalidation_required),
        "source_hash_revalidation_ready": _bool(source_hash_revalidation_ready),
        "rollback_required": _bool(rollback_required),
        "rollback_plan_ready": _bool(rollback_plan_ready),
        "formal_writeback_guard_required": _bool(formal_writeback_guard_required),
        "formal_writeback_guard_ready": _bool(formal_writeback_guard_ready),
        "generated_at": generated_at,
        "model_provider": model_provider,
        "model_name": model_name,
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "source_section_hash_match": source_section_hash_match,
        "diff_base_hash_match": diff_base_hash_match,
        "docx_export_requested": _bool(docx_export_requested),
        "zbid_writeback_requested": _bool(zbid_writeback_requested),
        "output_write_requested": _bool(output_write_requested),
        "formal_generation_requested": _bool(formal_generation_requested),
        "review_apply_requested": _bool(review_apply_requested),
    }
