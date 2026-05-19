from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_SOURCE_HASH_REVALIDATION_GUARD_FIELDS = frozenset(
    {
        "contract_version",
        "source_hash_guard_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "current_source_section_hash",
        "current_source_section_version",
        "source_hash_revalidation_status",
        "source_version_revalidation_status",
        "source_hash_match",
        "source_version_match",
        "source_hash_revalidation_required",
        "source_hash_revalidation_ready",
        "source_hash_guard_status",
        "revalidation_decision",
        "revalidation_mode",
        "shadow_candidate_id",
        "patch_id",
        "approval_id",
        "diff_preview_id",
        "rollback_plan_id",
        "writeback_guard_id",
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
        "writeback_guard_status",
        "human_approval_required",
        "human_approval_received",
        "diff_preview_required",
        "diff_preview_ready",
        "rollback_required",
        "rollback_plan_ready",
        "formal_writeback_guard_required",
        "formal_writeback_guard_ready",
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

SOURCE_HASH_REVALIDATION_STATUSES = frozenset(
    {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_hash",
        "blocked",
    }
)

SOURCE_VERSION_REVALIDATION_STATUSES = frozenset(
    {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_version",
        "blocked",
    }
)

SOURCE_HASH_GUARD_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_guard_shadow_only",
        "source_hash_matched_shadow_only",
        "stale_source_hash",
        "stale_source_version",
        "rejected",
    }
)

CURRENT_STAGE_EMITTABLE_SOURCE_HASH_GUARD_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "stale_source_hash",
        "stale_source_version",
    }
)

REVALIDATION_DECISIONS = frozenset(
    {
        "none",
        "block",
        "allow_shadow_only",
        "require_refresh",
        "reject",
    }
)

REVALIDATION_MODES = frozenset(
    {
        "disabled_current_stage",
        "metadata_only",
        "future_hash_check",
        "future_guarded_check",
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


def _source_hash_guard_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"source-hash-guard-{digest[:16]}"


def build_source_hash_revalidation_guard(
    *,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    source_section_version: str,
    current_source_section_hash: str,
    current_source_section_version: str,
    source_hash_revalidation_status: str = "not_checked",
    source_version_revalidation_status: str = "not_checked",
    source_hash_match: bool = False,
    source_version_match: bool = False,
    source_hash_revalidation_required: bool = True,
    source_hash_revalidation_ready: bool = False,
    revalidation_decision: str = "none",
    revalidation_mode: str = "disabled_current_stage",
    shadow_candidate_id: str = "",
    patch_id: str = "",
    approval_id: str = "",
    diff_preview_id: str = "",
    rollback_plan_id: str = "",
    writeback_guard_id: str = "",
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
    writeback_guard_status: str = "",
    human_approval_required: bool = True,
    human_approval_received: bool = False,
    diff_preview_required: bool = True,
    diff_preview_ready: bool = False,
    rollback_required: bool = True,
    rollback_plan_ready: bool = False,
    formal_writeback_guard_required: bool = True,
    formal_writeback_guard_ready: bool = False,
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
    source_hash_guard_id: str = "",
) -> dict[str, Any]:
    request_id = _text(request_id, limit=240)
    source_document_id = _text(source_document_id, limit=240)
    source_section_id = _text(source_section_id, limit=240)
    source_section_hash = _text(source_section_hash, limit=240)
    source_section_version = _text(source_section_version, limit=120)
    current_source_section_hash = _text(current_source_section_hash, limit=240)
    current_source_section_version = _text(current_source_section_version, limit=120)
    source_hash_revalidation_status = _text(source_hash_revalidation_status, limit=120)
    source_version_revalidation_status = _text(source_version_revalidation_status, limit=120)
    revalidation_decision = _text(revalidation_decision, limit=120)
    revalidation_mode = _text(revalidation_mode, limit=120)
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    patch_id = _text(patch_id, limit=240)
    approval_id = _text(approval_id, limit=240)
    diff_preview_id = _text(diff_preview_id, limit=240)
    rollback_plan_id = _text(rollback_plan_id, limit=240)
    writeback_guard_id = _text(writeback_guard_id, limit=240)
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
    writeback_guard_status = _text(writeback_guard_status, limit=120)
    generated_at = _text(generated_at, limit=120)
    model_provider = _text(model_provider, limit=120)
    model_name = _text(model_name, limit=120)
    source_hash_guard_id = _text(source_hash_guard_id, limit=240)

    source_hash_match = _bool(source_hash_match)
    source_version_match = _bool(source_version_match)
    source_hash_revalidation_required = _bool(source_hash_revalidation_required)
    source_hash_revalidation_ready = _bool(source_hash_revalidation_ready)
    human_approval_required = _bool(human_approval_required)
    human_approval_received = _bool(human_approval_received)
    diff_preview_required = _bool(diff_preview_required)
    diff_preview_ready = _bool(diff_preview_ready)
    rollback_required = _bool(rollback_required)
    rollback_plan_ready = _bool(rollback_plan_ready)
    formal_writeback_guard_required = _bool(formal_writeback_guard_required)
    formal_writeback_guard_ready = _bool(formal_writeback_guard_ready)
    review_apply_isolation_required = _bool(review_apply_isolation_required)
    review_apply_isolation_ready = _bool(review_apply_isolation_ready)
    docx_isolation_required = _bool(docx_isolation_required)
    docx_isolation_ready = _bool(docx_isolation_ready)
    zbid_isolation_required = _bool(zbid_isolation_required)
    zbid_isolation_ready = _bool(zbid_isolation_ready)
    docx_export_requested = _bool(docx_export_requested)
    zbid_writeback_requested = _bool(zbid_writeback_requested)
    output_write_requested = _bool(output_write_requested)
    formal_generation_requested = _bool(formal_generation_requested)
    review_apply_requested = _bool(review_apply_requested)

    affected_anchor_refs_list = _list(affected_anchor_refs)
    evidence_anchor_refs_list = _list(evidence_anchor_refs)
    blocked_reasons: list[str] = []
    status = "blocked"

    enum_checks = (
        (source_hash_revalidation_status, SOURCE_HASH_REVALIDATION_STATUSES, "invalid_source_hash_revalidation_status"),
        (source_version_revalidation_status, SOURCE_VERSION_REVALIDATION_STATUSES, "invalid_source_version_revalidation_status"),
        (revalidation_decision, REVALIDATION_DECISIONS, "invalid_revalidation_decision"),
        (revalidation_mode, REVALIDATION_MODES, "invalid_revalidation_mode"),
        (evidence_binding_status, _EVIDENCE_BINDING_STATUSES, "invalid_evidence_binding_status"),
    )
    for value, allowed, reason in enum_checks:
        if value and value not in allowed:
            _append_unique(blocked_reasons, reason)

    if not request_id:
        _append_unique(blocked_reasons, "missing_request_id")
        status = "not_created"

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
    if not writeback_guard_id:
        _append_unique(blocked_reasons, "missing_writeback_guard_id")

    if shadow_candidate_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "shadow_candidate_not_ready")
    if patch_status in {"blocked", "not_created"}:
        _append_unique(blocked_reasons, "patch_not_ready")
    if approval_status != "approved_shadow_only":
        _append_unique(blocked_reasons, "approval_not_received")
    if diff_preview_status in {"blocked", "not_created", "stale_source_hash"}:
        _append_unique(blocked_reasons, "diff_preview_not_ready")
    if rollback_plan_status in {"blocked", "not_created", "stale_source_hash"}:
        _append_unique(blocked_reasons, "rollback_plan_not_ready")
    if writeback_guard_status in {"blocked", "not_created", "stale_source_hash"}:
        _append_unique(blocked_reasons, "writeback_guard_not_ready")

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_hash_revalidation_capable")
    elif response_mode in {"unsupported", "blocked"}:
        _append_unique(blocked_reasons, "unsupported_response_mode")
    elif response_mode and response_mode not in _RESPONSE_MODES:
        _append_unique(blocked_reasons, "unsupported_response_mode")

    if evidence_anchor_status == "missing" or not evidence_anchor_refs_list:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    binding_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    if evidence_binding_status in binding_block_reasons:
        _append_unique(blocked_reasons, binding_block_reasons[evidence_binding_status])

    if not source_section_hash:
        _append_unique(blocked_reasons, "missing_source_section_hash")
    if not current_source_section_hash:
        _append_unique(blocked_reasons, "missing_current_source_section_hash")
    if source_hash_revalidation_required and not source_hash_revalidation_ready:
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")

    if source_hash_revalidation_status == "missing":
        _append_unique(blocked_reasons, "source_hash_revalidation_missing")
    elif source_hash_revalidation_status == "mismatched":
        _append_unique(blocked_reasons, "source_hash_mismatch")
        status = "stale_source_hash"
    elif source_hash_revalidation_status == "stale_source_hash":
        _append_unique(blocked_reasons, "stale_source_hash")
        status = "stale_source_hash"

    if not source_hash_match:
        _append_unique(blocked_reasons, "source_hash_mismatch")
        status = "stale_source_hash"

    if source_section_hash and current_source_section_hash and source_section_hash != current_source_section_hash:
        _append_unique(blocked_reasons, "source_hash_mismatch")
        status = "stale_source_hash"

    if not source_section_version:
        _append_unique(blocked_reasons, "missing_source_section_version")
    if not current_source_section_version:
        _append_unique(blocked_reasons, "missing_current_source_section_version")

    if source_version_revalidation_status == "missing":
        _append_unique(blocked_reasons, "source_version_revalidation_missing")
    elif source_version_revalidation_status == "mismatched":
        _append_unique(blocked_reasons, "source_version_mismatch")
        if status != "stale_source_hash":
            status = "stale_source_version"
    elif source_version_revalidation_status == "stale_source_version":
        _append_unique(blocked_reasons, "stale_source_version")
        if status != "stale_source_hash":
            status = "stale_source_version"

    if not source_version_match:
        _append_unique(blocked_reasons, "source_version_mismatch")
        if status != "stale_source_hash":
            status = "stale_source_version"

    if source_section_version and current_source_section_version and source_section_version != current_source_section_version:
        _append_unique(blocked_reasons, "source_version_mismatch")
        if status != "stale_source_hash":
            status = "stale_source_version"

    required_hashes = {
        "writeback_candidate_hash": writeback_candidate_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "diff_preview_hash": diff_preview_hash,
        "rollback_plan_hash": rollback_plan_hash,
    }
    missing_hash_reasons = {
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }
    for field, value in required_hashes.items():
        if not value:
            _append_unique(blocked_reasons, missing_hash_reasons[field])

    if human_approval_required and not human_approval_received:
        _append_unique(blocked_reasons, "human_approval_missing")
    if diff_preview_required and not diff_preview_ready:
        _append_unique(blocked_reasons, "diff_preview_missing")
    if rollback_required and not rollback_plan_ready:
        _append_unique(blocked_reasons, "rollback_plan_missing")
    if formal_writeback_guard_required and not formal_writeback_guard_ready:
        _append_unique(blocked_reasons, "formal_writeback_guard_missing")
    if review_apply_isolation_required and not review_apply_isolation_ready:
        _append_unique(blocked_reasons, "review_apply_isolation_missing")
    if docx_isolation_required and not docx_isolation_ready:
        _append_unique(blocked_reasons, "docx_isolation_missing")
    if zbid_isolation_required and not zbid_isolation_ready:
        _append_unique(blocked_reasons, "zbid_isolation_missing")

    request_blocks = {
        "docx_export_request_blocked": docx_export_requested,
        "zbid_writeback_request_blocked": zbid_writeback_requested,
        "output_write_request_blocked": output_write_requested,
        "formal_generation_request_blocked": formal_generation_requested,
        "review_apply_request_blocked": review_apply_requested,
    }
    for reason, requested in request_blocks.items():
        if requested:
            _append_unique(blocked_reasons, reason)

    if (
        source_hash_revalidation_status == "matched"
        or source_version_revalidation_status == "matched"
        or source_hash_match
        or source_version_match
        or revalidation_decision == "allow_shadow_only"
    ):
        _append_unique(
            blocked_reasons,
            "source_hash_revalidation_is_not_formal_writeback_permission",
        )

    _append_unique(blocked_reasons, "real_source_hash_revalidation_not_implemented_current_stage")

    if status not in {"not_created", "stale_source_hash", "stale_source_version"}:
        status = "blocked"

    source_hash_guard_seed = {
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "current_source_section_hash": current_source_section_hash,
        "current_source_section_version": current_source_section_version,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "approval_id": approval_id,
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "writeback_guard_id": writeback_guard_id,
        "writeback_candidate_hash": writeback_candidate_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "diff_preview_hash": diff_preview_hash,
        "rollback_plan_hash": rollback_plan_hash,
    }
    if not source_hash_guard_id:
        source_hash_guard_id = _source_hash_guard_id(source_hash_guard_seed)

    return {
        "contract_version": CONTRACT_VERSION,
        "source_hash_guard_id": source_hash_guard_id,
        "request_id": request_id,
        "source_document_id": source_document_id,
        "source_section_id": source_section_id,
        "source_section_hash": source_section_hash,
        "source_section_version": source_section_version,
        "current_source_section_hash": current_source_section_hash,
        "current_source_section_version": current_source_section_version,
        "source_hash_revalidation_status": source_hash_revalidation_status,
        "source_version_revalidation_status": source_version_revalidation_status,
        "source_hash_match": source_hash_match,
        "source_version_match": source_version_match,
        "source_hash_revalidation_required": source_hash_revalidation_required,
        "source_hash_revalidation_ready": source_hash_revalidation_ready,
        "source_hash_guard_status": status,
        "revalidation_decision": revalidation_decision,
        "revalidation_mode": revalidation_mode,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "approval_id": approval_id,
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "writeback_guard_id": writeback_guard_id,
        "writeback_candidate_hash": writeback_candidate_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "before_text_hash": before_text_hash,
        "after_text_preview_hash": after_text_preview_hash,
        "patch_operations_preview_hash": patch_operations_preview_hash,
        "diff_preview_hash": diff_preview_hash,
        "rollback_plan_hash": rollback_plan_hash,
        "affected_anchor_refs": affected_anchor_refs_list,
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_anchor_refs": evidence_anchor_refs_list,
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
        "writeback_guard_status": writeback_guard_status,
        "human_approval_required": human_approval_required,
        "human_approval_received": human_approval_received,
        "diff_preview_required": diff_preview_required,
        "diff_preview_ready": diff_preview_ready,
        "rollback_required": rollback_required,
        "rollback_plan_ready": rollback_plan_ready,
        "formal_writeback_guard_required": formal_writeback_guard_required,
        "formal_writeback_guard_ready": formal_writeback_guard_ready,
        "review_apply_isolation_required": review_apply_isolation_required,
        "review_apply_isolation_ready": review_apply_isolation_ready,
        "docx_isolation_required": docx_isolation_required,
        "docx_isolation_ready": docx_isolation_ready,
        "zbid_isolation_required": zbid_isolation_required,
        "zbid_isolation_ready": zbid_isolation_ready,
        "generated_at": generated_at,
        "model_provider": model_provider,
        "model_name": model_name,
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "docx_export_requested": docx_export_requested,
        "zbid_writeback_requested": zbid_writeback_requested,
        "output_write_requested": output_write_requested,
        "formal_generation_requested": formal_generation_requested,
        "review_apply_requested": review_apply_requested,
    }
