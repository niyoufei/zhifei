from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_PATCH_FIELDS = frozenset(
    {
        "contract_version",
        "patch_id",
        "shadow_candidate_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "patch_status",
        "patch_kind",
        "patch_scope",
        "patch_format",
        "patch_operation_type",
        "patch_operations_preview",
        "before_text_hash",
        "after_text_preview",
        "affected_anchor_refs",
        "evidence_anchor_status",
        "evidence_anchor_refs",
        "evidence_binding_status",
        "response_mode",
        "input_risk_level",
        "advisory_quality_gate_status",
        "readiness_status",
        "shadow_candidate_status",
        "generated_at",
        "model_provider",
        "model_name",
        "human_approval_required",
        "human_approval_received",
        "diff_preview_required",
        "diff_preview_ready",
        "rollback_required",
        "rollback_plan_ready",
        "formal_writeback_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
        "blocked_reasons",
    }
)

PATCH_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_patch_shadow_only",
        "ready_for_human_review",
        "approved_patch_shadow_only",
        "rejected",
    }
)

CURRENT_STAGE_EMITTABLE_PATCH_STATUSES = frozenset({"not_created", "blocked"})

PATCH_KINDS = frozenset(
    {
        "section_rewrite",
        "paragraph_rewrite",
        "insert_after_anchor",
        "replace_anchor_range",
        "delete_anchor_range",
        "metadata_only",
    }
)

PATCH_OPERATION_TYPES = frozenset(
    {
        "no_op",
        "replace",
        "insert",
        "delete",
        "reorder",
        "mixed",
    }
)

PATCH_FORMATS = frozenset(
    {
        "text_preview",
        "structured_patch_preview",
        "metadata_only",
    }
)

EVIDENCE_BINDING_STATUSES = frozenset(
    {
        "missing",
        "bound_to_user_provided_evidence",
        "bound_to_source_verified_evidence",
        "generated_advisory_only_blocked",
        "shadow_candidate_only_blocked",
        "patch_preview_only_blocked",
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

_RESPONSE_MODES = frozenset(
    {
        "preview_advisory",
        "thinking_only_fallback",
        "unsupported",
        "blocked",
    }
)

_READINESS_STATUSES = frozenset(
    {
        "blocked",
        "fake_ready_metadata_only",
        "future_ready_for_shadow_candidate",
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

_QUALITY_GATE_ALLOWED_STATUSES = frozenset(
    {
        "ok",
        "pass",
        "passed",
        "allowed",
        "preview_ok",
        "quality_ok",
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


def _patch_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"patch-{digest[:16]}"


def build_shadow_candidate_patch(
    *,
    shadow_candidate_id: str,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    source_section_version: str,
    patch_kind: str = "",
    patch_scope: str = "",
    patch_format: str = "metadata_only",
    patch_operation_type: str = "no_op",
    patch_operations_preview: list[Any] | tuple[Any, ...] | None = None,
    before_text_hash: str = "",
    after_text_preview: str = "",
    affected_anchor_refs: list[Any] | tuple[Any, ...] | None = None,
    evidence_anchor_status: str = "",
    evidence_anchor_refs: list[Any] | tuple[Any, ...] | None = None,
    evidence_binding_status: str = "",
    response_mode: str = "",
    input_risk_level: str = "",
    advisory_quality_gate_status: str = "",
    readiness_status: str = "",
    shadow_candidate_status: str = "",
    generated_at: str,
    model_provider: str = "",
    model_name: str = "",
    human_approval_required: bool = True,
    human_approval_received: bool = False,
    diff_preview_required: bool = True,
    diff_preview_ready: bool = False,
    rollback_required: bool = True,
    rollback_plan_ready: bool = False,
    source_section_hash_match: bool = True,
    docx_export_requested: bool = False,
    zbid_writeback_requested: bool = False,
    output_write_requested: bool = False,
    formal_generation_requested: bool = False,
    review_apply_requested: bool = False,
) -> dict[str, Any]:
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    request_id = _text(request_id, limit=240)
    source_document_id = _text(source_document_id, limit=240)
    source_section_id = _text(source_section_id, limit=240)
    source_section_hash = _text(source_section_hash, limit=240)
    source_section_version = _text(source_section_version, limit=120)
    patch_kind = _text(patch_kind, limit=120)
    patch_scope = _text(patch_scope, limit=120)
    patch_format = _text(patch_format, limit=120)
    patch_operation_type = _text(patch_operation_type, limit=120)
    before_text_hash = _text(before_text_hash, limit=240)
    after_text_preview = _text(after_text_preview)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    evidence_binding_status = _text(evidence_binding_status, limit=120)
    response_mode = _text(response_mode, limit=120)
    input_risk_level = _text(input_risk_level, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120).lower()
    readiness_status = _text(readiness_status, limit=120)
    shadow_candidate_status = _text(shadow_candidate_status, limit=120)
    generated_at = _text(generated_at, limit=120)
    model_provider = _text(model_provider, limit=120)
    model_name = _text(model_name, limit=120)
    patch_operations = _list(patch_operations_preview)
    affected_refs = _list(affected_anchor_refs)
    evidence_refs = _list(evidence_anchor_refs)
    source_section_hash_match = _bool(source_section_hash_match)
    blocked_reasons: list[str] = []

    if not shadow_candidate_id:
        _append_unique(blocked_reasons, "missing_shadow_candidate_id")

    if shadow_candidate_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")
    elif shadow_candidate_status not in _SHADOW_CANDIDATE_STATUSES:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_patch_capable")
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
    elif evidence_binding_status not in EVIDENCE_BINDING_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    preview_values = {str(patch_operations), after_text_preview} - {""}
    if preview_values and any(str(ref) in preview_values for ref in evidence_refs):
        _append_unique(blocked_reasons, "patch_preview_cannot_be_evidence")

    if advisory_quality_gate_status not in _QUALITY_GATE_ALLOWED_STATUSES:
        _append_unique(blocked_reasons, "advisory_quality_gate_not_passed")

    if readiness_status == "blocked" or readiness_status not in _READINESS_STATUSES:
        _append_unique(blocked_reasons, "readiness_not_for_patch_generation")

    if not source_section_hash:
        _append_unique(blocked_reasons, "missing_source_section_hash")

    if not source_section_hash_match:
        _append_unique(blocked_reasons, "source_section_hash_mismatch")

    if not before_text_hash:
        _append_unique(blocked_reasons, "missing_before_text_hash")

    if _bool(human_approval_required) and not _bool(human_approval_received):
        _append_unique(blocked_reasons, "human_approval_missing")

    if _bool(diff_preview_required) and not _bool(diff_preview_ready):
        _append_unique(blocked_reasons, "diff_preview_missing")

    if _bool(rollback_required) and not _bool(rollback_plan_ready):
        _append_unique(blocked_reasons, "rollback_plan_missing")

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

    _append_unique(blocked_reasons, "real_candidate_patch_not_implemented_current_stage")

    id_seed = {
        "contract_version": CONTRACT_VERSION,
        "shadow_candidate_id": shadow_candidate_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "patch_kind": patch_kind,
        "patch_scope": patch_scope,
        "patch_format": patch_format,
        "patch_operation_type": patch_operation_type,
        "before_text_hash": before_text_hash,
        "generated_at": generated_at,
    }

    return {
        "contract_version": CONTRACT_VERSION,
        "patch_id": _patch_id(id_seed),
        "shadow_candidate_id": shadow_candidate_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "patch_status": "blocked" if blocked_reasons else "not_created",
        "patch_kind": patch_kind,
        "patch_scope": patch_scope,
        "patch_format": patch_format,
        "patch_operation_type": patch_operation_type,
        "patch_operations_preview": patch_operations,
        "before_text_hash": before_text_hash,
        "after_text_preview": after_text_preview,
        "affected_anchor_refs": affected_refs,
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_anchor_refs": evidence_refs,
        "evidence_binding_status": evidence_binding_status,
        "response_mode": response_mode,
        "input_risk_level": input_risk_level,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "readiness_status": readiness_status,
        "shadow_candidate_status": shadow_candidate_status,
        "generated_at": generated_at,
        "model_provider": model_provider,
        "model_name": model_name,
        "human_approval_required": _bool(human_approval_required),
        "human_approval_received": _bool(human_approval_received),
        "diff_preview_required": _bool(diff_preview_required),
        "diff_preview_ready": _bool(diff_preview_ready),
        "rollback_required": _bool(rollback_required),
        "rollback_plan_ready": _bool(rollback_plan_ready),
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "source_section_hash_match": source_section_hash_match,
        "docx_export_requested": _bool(docx_export_requested),
        "zbid_writeback_requested": _bool(zbid_writeback_requested),
        "output_write_requested": _bool(output_write_requested),
        "formal_generation_requested": _bool(formal_generation_requested),
        "review_apply_requested": _bool(review_apply_requested),
    }
