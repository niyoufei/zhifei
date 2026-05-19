from __future__ import annotations

from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_PREVIEW_PACKET_FIELDS = frozenset(
    {
        "contract_version",
        "integration_request_id",
        "source_system",
        "target_system",
        "project_id",
        "document_id",
        "section_id",
        "section_title",
        "section_hash",
        "section_version",
        "tender_file_refs",
        "scoring_clause_refs",
        "evidence_anchor_refs",
        "evidence_anchor_status",
        "evidence_binding_status",
        "response_mode",
        "input_risk_level",
        "advisory_quality_gate_status",
        "preview_advisory_summary",
        "shadow_candidate_id",
        "patch_id",
        "diff_preview_id",
        "rollback_plan_id",
        "dry_run_id",
        "zbid_preview_mode",
        "zbid_input_status",
        "zbid_mapping_status",
        "zbid_scoring_matrix_status",
        "zbid_writeback_requested",
        "zbid_writeback_allowed",
        "docx_export_allowed",
        "formal_writeback_allowed",
        "review_apply_allowed",
        "output_write_allowed",
        "blocked_reasons",
        "generated_at",
    }
)

ZBID_PREVIEW_VALIDATION_STATUSES = frozenset(
    {
        "not_validated",
        "blocked",
        "accepted_metadata_only",
        "accepted_preview_only",
        "requires_human_review",
        "rejected",
        "stale_source_hash",
    }
)

ZBID_PREVIEW_VALIDATION_DECISIONS = frozenset(
    {
        "none",
        "block",
        "accept_metadata_only",
        "accept_preview_only",
        "require_human_review",
        "reject",
    }
)

EVIDENCE_BLOCKED_SOURCES = frozenset(
    {
        "generated_advisory",
        "preview_advisory_summary",
        "shadow_candidate",
        "patch_preview",
        "diff_preview",
        "rollback_plan",
        "dry_run_result",
        "zbid_preview_scoring",
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

_QUALITY_GATE_ALLOWED_STATUSES = frozenset(
    {
        "pass",
        "ok",
        "allowed",
        "preview_ok",
        "quality_gate_passed",
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


def validate_zbid_preview_input(preview_packet: dict[str, Any]) -> dict[str, Any]:
    is_packet = isinstance(preview_packet, dict)
    packet = preview_packet if is_packet else {}

    integration_request_id = _text(packet.get("integration_request_id"), limit=240)
    source_system = _text(packet.get("source_system"), limit=120)
    target_system = _text(packet.get("target_system"), limit=120)
    project_id = _text(packet.get("project_id"), limit=240)
    document_id = _text(packet.get("document_id"), limit=240)
    section_id = _text(packet.get("section_id"), limit=240)
    section_hash = _text(packet.get("section_hash"), limit=240)
    section_version = _text(packet.get("section_version"), limit=120)
    zbid_preview_mode = _text(packet.get("zbid_preview_mode"), limit=120)
    zbid_input_status = _text(packet.get("zbid_input_status"), limit=120)
    zbid_mapping_status = _text(packet.get("zbid_mapping_status"), limit=120)
    zbid_scoring_matrix_status = _text(packet.get("zbid_scoring_matrix_status"), limit=120)
    evidence_anchor_status = _text(packet.get("evidence_anchor_status"), limit=120)
    evidence_binding_status = _text(packet.get("evidence_binding_status"), limit=120)
    response_mode = _text(packet.get("response_mode"), limit=120)
    input_risk_level = _text(packet.get("input_risk_level"), limit=120)
    advisory_quality_gate_status = _text(
        packet.get("advisory_quality_gate_status"), limit=120
    )
    preview_advisory_summary = _text(packet.get("preview_advisory_summary"))
    shadow_candidate_id = _text(packet.get("shadow_candidate_id"), limit=240)
    patch_id = _text(packet.get("patch_id"), limit=240)
    diff_preview_id = _text(packet.get("diff_preview_id"), limit=240)
    rollback_plan_id = _text(packet.get("rollback_plan_id"), limit=240)
    dry_run_id = _text(packet.get("dry_run_id"), limit=240)
    generated_at = _text(packet.get("generated_at"), limit=120)

    tender_file_refs = _list(packet.get("tender_file_refs"))
    scoring_clause_refs = _list(packet.get("scoring_clause_refs"))
    evidence_anchor_refs = _list(packet.get("evidence_anchor_refs"))

    high_risk_validation_ready = _bool(packet.get("high_risk_validation_ready"))
    zbid_writeback_requested = _bool(packet.get("zbid_writeback_requested"))
    docx_export_requested = _bool(packet.get("docx_export_requested"))
    review_apply_requested = _bool(packet.get("review_apply_requested"))
    formal_writeback_requested = _bool(packet.get("formal_writeback_requested"))
    output_write_requested = _bool(packet.get("output_write_requested"))

    blocked_reasons: list[str] = []
    validation_notes: list[str] = [
        "fake_only_zbid_preview_input_validator",
        "accepted_preview_input_does_not_grant_writeback_permission",
    ]

    if not is_packet:
        _append_unique(blocked_reasons, "invalid_preview_packet")

    missing_required_values = {
        "missing_integration_request_id": integration_request_id,
        "missing_project_id": project_id,
        "missing_document_id": document_id,
        "missing_section_id": section_id,
        "missing_section_hash": section_hash,
        "missing_section_version": section_version,
    }
    for reason, value in missing_required_values.items():
        if not value:
            _append_unique(blocked_reasons, reason)

    if not tender_file_refs:
        _append_unique(blocked_reasons, "missing_tender_file_refs")
    if not scoring_clause_refs:
        _append_unique(blocked_reasons, "missing_scoring_clause_refs")
    if evidence_anchor_status == "missing" or not evidence_anchor_refs:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    evidence_source_blocks = (
        (
            _bool(packet.get("generated_advisory_used_as_evidence")),
            "generated_advisory_cannot_be_evidence",
        ),
        (
            _bool(packet.get("preview_advisory_used_as_evidence")),
            "preview_advisory_cannot_be_evidence",
        ),
        (
            _bool(packet.get("shadow_candidate_used_as_evidence")),
            "shadow_candidate_cannot_be_evidence",
        ),
        (
            _bool(packet.get("patch_preview_used_as_evidence")),
            "patch_preview_cannot_be_evidence",
        ),
        (
            _bool(packet.get("diff_preview_used_as_evidence")),
            "diff_preview_cannot_be_evidence",
        ),
        (
            _bool(packet.get("rollback_plan_used_as_evidence")),
            "rollback_plan_cannot_be_evidence",
        ),
        (
            _bool(packet.get("dry_run_used_as_evidence")),
            "dry_run_result_cannot_be_evidence",
        ),
        (
            _bool(packet.get("zbid_preview_scoring_used_as_evidence")),
            "zbid_preview_scoring_is_not_evidence",
        ),
    )
    for used_as_evidence, reason in evidence_source_blocks:
        if used_as_evidence:
            _append_unique(blocked_reasons, reason)

    binding_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    if evidence_binding_status in binding_block_reasons:
        _append_unique(blocked_reasons, binding_block_reasons[evidence_binding_status])

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_integratable")
    elif response_mode in {"unsupported", "blocked"}:
        _append_unique(blocked_reasons, "unsupported_response_mode")

    if input_risk_level == "high" and not high_risk_validation_ready:
        _append_unique(blocked_reasons, "high_input_risk_not_validated")

    if advisory_quality_gate_status not in _QUALITY_GATE_ALLOWED_STATUSES:
        _append_unique(blocked_reasons, "advisory_quality_gate_not_passed")

    if zbid_preview_mode == "future_guarded_writeback":
        _append_unique(blocked_reasons, "future_guarded_writeback_not_enabled")

    request_blocks = (
        (zbid_writeback_requested, "zbid_writeback_request_blocked"),
        (docx_export_requested, "docx_export_request_blocked"),
        (review_apply_requested, "review_apply_request_blocked"),
        (formal_writeback_requested, "formal_writeback_request_blocked"),
        (output_write_requested, "output_write_request_blocked"),
    )
    for requested, reason in request_blocks:
        if requested:
            _append_unique(blocked_reasons, reason)

    has_hard_blocks = bool(blocked_reasons)

    _append_unique(blocked_reasons, "preview_only_is_not_writeback_permission")
    _append_unique(blocked_reasons, "preview_only_is_not_evidence")
    _append_unique(blocked_reasons, "zbid_preview_scoring_is_not_evidence")

    if has_hard_blocks:
        validation_status = "blocked"
        validation_decision = "block"
    elif zbid_preview_mode == "metadata_only" or zbid_input_status == "accepted_metadata_only":
        validation_status = "accepted_metadata_only"
        validation_decision = "accept_metadata_only"
    else:
        validation_status = "accepted_preview_only"
        validation_decision = "accept_preview_only"

    if validation_status not in ZBID_PREVIEW_VALIDATION_STATUSES:
        validation_status = "blocked"
        validation_decision = "block"
    if validation_decision not in ZBID_PREVIEW_VALIDATION_DECISIONS:
        validation_status = "blocked"
        validation_decision = "block"

    return {
        "contract_version": CONTRACT_VERSION,
        "integration_request_id": integration_request_id,
        "source_system": source_system,
        "target_system": target_system,
        "project_id": project_id,
        "document_id": document_id,
        "section_id": section_id,
        "section_hash": section_hash,
        "section_version": section_version,
        "zbid_preview_validation_status": validation_status,
        "zbid_preview_validation_decision": validation_decision,
        "zbid_preview_mode": zbid_preview_mode,
        "zbid_input_status": zbid_input_status,
        "zbid_mapping_status": zbid_mapping_status,
        "zbid_scoring_matrix_status": zbid_scoring_matrix_status,
        "tender_file_refs": tender_file_refs,
        "scoring_clause_refs": scoring_clause_refs,
        "evidence_anchor_refs": evidence_anchor_refs,
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_binding_status": evidence_binding_status,
        "response_mode": response_mode,
        "input_risk_level": input_risk_level,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "validation_notes": validation_notes,
        "preview_advisory_summary": preview_advisory_summary,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "dry_run_id": dry_run_id,
        "generated_at": generated_at,
    }
