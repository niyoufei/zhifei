from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_WRITEBACK_GUARD_FIELDS = frozenset(
    {
        "contract_version",
        "writeback_guard_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "shadow_candidate_id",
        "patch_id",
        "approval_id",
        "diff_preview_id",
        "rollback_plan_id",
        "writeback_guard_status",
        "writeback_decision",
        "writeback_scope",
        "writeback_mode",
        "writeback_target_type",
        "writeback_candidate_hash",
        "source_snapshot_hash",
        "before_text_hash",
        "after_text_preview_hash",
        "patch_operations_preview_hash",
        "diff_preview_hash",
        "rollback_plan_hash",
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
        "diff_preview_status",
        "rollback_plan_status",
        "source_hash_revalidation_required",
        "source_hash_revalidation_ready",
        "source_hash_revalidation_status",
        "human_approval_required",
        "human_approval_received",
        "diff_preview_required",
        "diff_preview_ready",
        "rollback_required",
        "rollback_plan_ready",
        "review_apply_isolation_required",
        "review_apply_isolation_ready",
        "docx_isolation_required",
        "docx_isolation_ready",
        "zbid_isolation_required",
        "zbid_isolation_ready",
        "generated_at",
        "model_provider",
        "model_name",
        "formal_writeback_allowed",
        "review_apply_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
        "blocked_reasons",
    }
)

WRITEBACK_GUARD_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_guard_shadow_only",
        "ready_for_final_review",
        "approved_guard_shadow_only",
        "rejected",
        "stale_source_hash",
    }
)

CURRENT_STAGE_EMITTABLE_WRITEBACK_GUARD_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "stale_source_hash",
    }
)

WRITEBACK_DECISIONS = frozenset(
    {
        "none",
        "block",
        "allow_shadow_only",
        "require_revision",
        "reject",
    }
)

WRITEBACK_SCOPES = frozenset(
    {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
)

WRITEBACK_MODES = frozenset(
    {
        "disabled_current_stage",
        "dry_run_only",
        "future_manual_apply",
        "future_guarded_apply",
    }
)

WRITEBACK_TARGET_TYPES = frozenset(
    {
        "source_section",
        "section_draft",
        "patch_preview",
        "metadata_only",
    }
)

SOURCE_HASH_REVALIDATION_STATUSES = frozenset(
    {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_hash",
    }
)

CURRENT_STAGE_FORMAL_FLAGS = frozenset(
    {
        "formal_writeback_allowed",
        "review_apply_allowed",
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
        "rollback_plan_only_blocked",
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

_DIFF_PREVIEW_STATUSES = frozenset(
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

_ROLLBACK_PLAN_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_rollback_shadow_only",
        "ready_for_human_review",
        "approved_rollback_shadow_only",
        "rejected",
        "stale_source_hash",
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


def _writeback_guard_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"writeback-guard-{digest[:16]}"


def build_formal_writeback_guard(
    *,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    source_section_version: str,
    shadow_candidate_id: str,
    patch_id: str,
    approval_id: str,
    diff_preview_id: str,
    rollback_plan_id: str,
    writeback_decision: str = "none",
    writeback_scope: str = "",
    writeback_mode: str = "disabled_current_stage",
    writeback_target_type: str = "metadata_only",
    writeback_candidate_hash: str = "",
    source_snapshot_hash: str = "",
    before_text_hash: str = "",
    after_text_preview_hash: str = "",
    patch_operations_preview_hash: str = "",
    diff_preview_hash: str = "",
    rollback_plan_hash: str = "",
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
    diff_preview_status: str = "",
    rollback_plan_status: str = "",
    source_hash_revalidation_required: bool = True,
    source_hash_revalidation_ready: bool = False,
    source_hash_revalidation_status: str = "not_checked",
    source_section_hash_match: bool = True,
    human_approval_required: bool = True,
    human_approval_received: bool = False,
    diff_preview_required: bool = True,
    diff_preview_ready: bool = False,
    rollback_required: bool = True,
    rollback_plan_ready: bool = False,
    review_apply_isolation_required: bool = True,
    review_apply_isolation_ready: bool = False,
    docx_isolation_required: bool = True,
    docx_isolation_ready: bool = False,
    zbid_isolation_required: bool = True,
    zbid_isolation_ready: bool = False,
    generated_at: str,
    model_provider: str = "",
    model_name: str = "",
    docx_export_requested: bool = False,
    zbid_writeback_requested: bool = False,
    output_write_requested: bool = False,
    formal_generation_requested: bool = False,
    review_apply_requested: bool = False,
    writeback_guard_status: str = "not_created",
    writeback_guard_id: str = "",
) -> dict[str, Any]:
    request_id = _text(request_id, limit=240)
    source_document_id = _text(source_document_id, limit=240)
    source_section_id = _text(source_section_id, limit=240)
    source_section_hash = _text(source_section_hash, limit=240)
    source_section_version = _text(source_section_version, limit=120)
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    patch_id = _text(patch_id, limit=240)
    approval_id = _text(approval_id, limit=240)
    diff_preview_id = _text(diff_preview_id, limit=240)
    rollback_plan_id = _text(rollback_plan_id, limit=240)
    writeback_decision = _text(writeback_decision, limit=120)
    writeback_scope = _text(writeback_scope, limit=120)
    writeback_mode = _text(writeback_mode, limit=120)
    writeback_target_type = _text(writeback_target_type, limit=120)
    writeback_candidate_hash = _text(writeback_candidate_hash, limit=240)
    source_snapshot_hash = _text(source_snapshot_hash, limit=240)
    before_text_hash = _text(before_text_hash, limit=240)
    after_text_preview_hash = _text(after_text_preview_hash, limit=240)
    patch_operations_preview_hash = _text(patch_operations_preview_hash, limit=240)
    diff_preview_hash = _text(diff_preview_hash, limit=240)
    rollback_plan_hash = _text(rollback_plan_hash, limit=240)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    evidence_binding_status = _text(evidence_binding_status, limit=120)
    response_mode = _text(response_mode, limit=120)
    input_risk_level = _text(input_risk_level, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120)
    readiness_status = _text(readiness_status, limit=120)
    shadow_candidate_status = _text(shadow_candidate_status, limit=120)
    patch_status = _text(patch_status, limit=120)
    approval_status = _text(approval_status, limit=120)
    diff_preview_status = _text(diff_preview_status, limit=120)
    rollback_plan_status = _text(rollback_plan_status, limit=120)
    source_hash_revalidation_status = _text(source_hash_revalidation_status, limit=120)
    generated_at = _text(generated_at, limit=120)
    model_provider = _text(model_provider, limit=120)
    model_name = _text(model_name, limit=120)
    requested_status = _text(writeback_guard_status, limit=120)
    affected_refs = _list(affected_anchor_refs)
    evidence_refs = _list(evidence_anchor_refs)
    source_section_hash_match = _bool(source_section_hash_match)
    blocked_reasons: list[str] = []
    stale_source_hash = False

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
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "writeback_candidate_hash": writeback_candidate_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "diff_preview_hash": diff_preview_hash,
        "rollback_plan_hash": rollback_plan_hash,
    }
    writeback_guard_id = _text(writeback_guard_id, limit=240) or _writeback_guard_id(id_seed)

    if requested_status == "approved_guard_shadow_only":
        _append_unique(blocked_reasons, "guard_is_not_formal_writeback_permission")
    elif requested_status not in WRITEBACK_GUARD_STATUSES:
        _append_unique(blocked_reasons, "invalid_writeback_guard_status")

    if writeback_decision == "allow_shadow_only":
        _append_unique(blocked_reasons, "guard_is_not_formal_writeback_permission")
    elif writeback_decision not in WRITEBACK_DECISIONS:
        _append_unique(blocked_reasons, "invalid_writeback_decision")

    if writeback_scope not in WRITEBACK_SCOPES:
        _append_unique(blocked_reasons, "invalid_writeback_scope")

    if writeback_mode not in WRITEBACK_MODES:
        _append_unique(blocked_reasons, "invalid_writeback_mode")

    if writeback_target_type not in WRITEBACK_TARGET_TYPES:
        _append_unique(blocked_reasons, "invalid_writeback_target_type")

    if not shadow_candidate_id:
        _append_unique(blocked_reasons, "missing_shadow_candidate_id")

    if not patch_id:
        _append_unique(blocked_reasons, "missing_patch_id")

    if not approval_id:
        _append_unique(blocked_reasons, "missing_approval_id")

    if not diff_preview_id:
        _append_unique(blocked_reasons, "missing_diff_preview_id")

    if not rollback_plan_id:
        _append_unique(blocked_reasons, "missing_rollback_plan_id")

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

    if diff_preview_status in {"blocked", "not_created", "stale_source_hash"}:
        _append_unique(blocked_reasons, "diff_preview_not_ready")
    elif diff_preview_status not in _DIFF_PREVIEW_STATUSES:
        _append_unique(blocked_reasons, "diff_preview_not_ready")

    if rollback_plan_status in {"blocked", "not_created", "stale_source_hash"}:
        _append_unique(blocked_reasons, "rollback_plan_not_ready")
    elif rollback_plan_status not in _ROLLBACK_PLAN_STATUSES:
        _append_unique(blocked_reasons, "rollback_plan_not_ready")

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_writeback_capable")
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
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    if evidence_binding_status in evidence_block_reasons:
        _append_unique(blocked_reasons, evidence_block_reasons[evidence_binding_status])
    elif evidence_binding_status not in _EVIDENCE_BINDING_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    if not source_section_hash:
        _append_unique(blocked_reasons, "missing_source_section_hash")

    if not source_section_hash_match:
        _append_unique(blocked_reasons, "stale_source_hash")
        stale_source_hash = True

    if source_hash_revalidation_required and not source_hash_revalidation_ready:
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")

    if source_hash_revalidation_status == "missing":
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")
    elif source_hash_revalidation_status == "mismatched":
        _append_unique(blocked_reasons, "source_hash_revalidation_mismatched")
        stale_source_hash = True
    elif source_hash_revalidation_status == "stale_source_hash":
        _append_unique(blocked_reasons, "stale_source_hash")
        stale_source_hash = True
    elif source_hash_revalidation_status not in SOURCE_HASH_REVALIDATION_STATUSES:
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")

    required_hashes = {
        "writeback_candidate_hash": (writeback_candidate_hash, "missing_writeback_candidate_hash"),
        "source_snapshot_hash": (source_snapshot_hash, "missing_source_snapshot_hash"),
        "before_text_hash": (before_text_hash, "missing_before_text_hash"),
        "after_text_preview_hash": (after_text_preview_hash, "missing_after_text_preview_hash"),
        "patch_operations_preview_hash": (
            patch_operations_preview_hash,
            "missing_patch_operations_preview_hash",
        ),
        "diff_preview_hash": (diff_preview_hash, "missing_diff_preview_hash"),
        "rollback_plan_hash": (rollback_plan_hash, "missing_rollback_plan_hash"),
    }
    for value, reason in required_hashes.values():
        if not value:
            _append_unique(blocked_reasons, reason)

    if human_approval_required and not human_approval_received:
        _append_unique(blocked_reasons, "human_approval_missing")

    if diff_preview_required and not diff_preview_ready:
        _append_unique(blocked_reasons, "diff_preview_missing")

    if rollback_required and not rollback_plan_ready:
        _append_unique(blocked_reasons, "rollback_plan_missing")

    if review_apply_isolation_required and not review_apply_isolation_ready:
        _append_unique(blocked_reasons, "review_apply_isolation_missing")

    if docx_isolation_required and not docx_isolation_ready:
        _append_unique(blocked_reasons, "docx_isolation_missing")

    if zbid_isolation_required and not zbid_isolation_ready:
        _append_unique(blocked_reasons, "zbid_isolation_missing")

    if docx_export_requested:
        _append_unique(blocked_reasons, "docx_export_request_blocked")

    if zbid_writeback_requested:
        _append_unique(blocked_reasons, "zbid_writeback_request_blocked")

    if output_write_requested:
        _append_unique(blocked_reasons, "output_write_request_blocked")

    if formal_generation_requested:
        _append_unique(blocked_reasons, "formal_generation_request_blocked")

    if review_apply_requested:
        _append_unique(blocked_reasons, "review_apply_request_blocked")

    _append_unique(blocked_reasons, "real_formal_writeback_not_implemented_current_stage")

    if stale_source_hash:
        emitted_status = "stale_source_hash"
    elif blocked_reasons:
        emitted_status = "blocked"
    elif requested_status in CURRENT_STAGE_EMITTABLE_WRITEBACK_GUARD_STATUSES:
        emitted_status = requested_status
    else:
        emitted_status = "blocked"

    return {
        "contract_version": CONTRACT_VERSION,
        "writeback_guard_id": writeback_guard_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "approval_id": approval_id,
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "writeback_guard_status": emitted_status,
        "writeback_decision": writeback_decision,
        "writeback_scope": writeback_scope,
        "writeback_mode": writeback_mode,
        "writeback_target_type": writeback_target_type,
        "writeback_candidate_hash": writeback_candidate_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "diff_preview_hash": diff_preview_hash,
        "rollback_plan_hash": rollback_plan_hash,
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
        "diff_preview_status": diff_preview_status,
        "rollback_plan_status": rollback_plan_status,
        "source_hash_revalidation_required": bool(source_hash_revalidation_required),
        "source_hash_revalidation_ready": bool(source_hash_revalidation_ready),
        "source_hash_revalidation_status": source_hash_revalidation_status,
        "human_approval_required": bool(human_approval_required),
        "human_approval_received": bool(human_approval_received),
        "diff_preview_required": bool(diff_preview_required),
        "diff_preview_ready": bool(diff_preview_ready),
        "rollback_required": bool(rollback_required),
        "rollback_plan_ready": bool(rollback_plan_ready),
        "review_apply_isolation_required": bool(review_apply_isolation_required),
        "review_apply_isolation_ready": bool(review_apply_isolation_ready),
        "docx_isolation_required": bool(docx_isolation_required),
        "docx_isolation_ready": bool(docx_isolation_ready),
        "zbid_isolation_required": bool(zbid_isolation_required),
        "zbid_isolation_ready": bool(zbid_isolation_ready),
        "generated_at": generated_at,
        "model_provider": model_provider,
        "model_name": model_name,
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "source_section_hash_match": source_section_hash_match,
        "docx_export_requested": bool(docx_export_requested),
        "zbid_writeback_requested": bool(zbid_writeback_requested),
        "output_write_requested": bool(output_write_requested),
        "formal_generation_requested": bool(formal_generation_requested),
        "review_apply_requested": bool(review_apply_requested),
    }
