from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_ZDOC_ZBID_PREVIEW_PACKET_FIELDS = frozenset(
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

ZBID_PREVIEW_MODES = frozenset(
    {
        "disabled_current_stage",
        "metadata_only",
        "preview_only",
        "future_scoring_preview",
        "future_guarded_writeback",
    }
)

ZBID_INPUT_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "accepted_metadata_only",
        "accepted_preview_only",
        "rejected",
        "stale_source_hash",
    }
)

ZBID_MAPPING_STATUSES = frozenset(
    {
        "not_mapped",
        "mapping_placeholder_only",
        "mapped_preview_only",
        "mapping_blocked",
    }
)

ZBID_SCORING_MATRIX_STATUSES = frozenset(
    {
        "not_created",
        "preview_only",
        "blocked",
        "requires_human_review",
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

_QUALITY_GATE_ALLOWED_STATUSES = frozenset(
    {
        "pass",
        "ok",
        "allowed",
        "preview_ok",
        "quality_gate_passed",
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


def _preview_packet_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"zdoc-zbid-preview-packet-{digest[:16]}"


def build_zdoc_zbid_preview_packet(
    *,
    source_system: str,
    target_system: str,
    project_id: str,
    document_id: str,
    section_id: str,
    section_title: str,
    section_hash: str,
    section_version: str,
    tender_file_refs: list[Any] | tuple[Any, ...] | None,
    scoring_clause_refs: list[Any] | tuple[Any, ...] | None,
    evidence_anchor_refs: list[Any] | tuple[Any, ...] | None,
    evidence_anchor_status: str,
    evidence_binding_status: str,
    response_mode: str,
    input_risk_level: str,
    advisory_quality_gate_status: str,
    preview_advisory_summary: str,
    shadow_candidate_id: str = "",
    patch_id: str = "",
    diff_preview_id: str = "",
    rollback_plan_id: str = "",
    dry_run_id: str = "",
    generated_at: str,
    model_provider: str = "",
    model_name: str = "",
    generated_advisory_used_as_evidence: bool = False,
    preview_advisory_used_as_evidence: bool = False,
    shadow_candidate_used_as_evidence: bool = False,
    patch_preview_used_as_evidence: bool = False,
    diff_preview_used_as_evidence: bool = False,
    rollback_plan_used_as_evidence: bool = False,
    dry_run_used_as_evidence: bool = False,
    scoring_clause_unverifiable: bool = False,
    high_risk_validation_ready: bool = False,
    zbid_writeback_requested: bool = False,
    docx_export_requested: bool = False,
    review_apply_requested: bool = False,
    formal_writeback_requested: bool = False,
    output_write_requested: bool = False,
    zbid_preview_mode: str = "preview_only",
    zbid_input_status: str = "",
    zbid_mapping_status: str = "",
    zbid_scoring_matrix_status: str = "",
    integration_request_id: str = "",
) -> dict[str, Any]:
    source_system = _text(source_system, limit=120)
    target_system = _text(target_system, limit=120)
    project_id = _text(project_id, limit=240)
    document_id = _text(document_id, limit=240)
    section_id = _text(section_id, limit=240)
    section_title = _text(section_title, limit=500)
    section_hash = _text(section_hash, limit=240)
    section_version = _text(section_version, limit=120)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    evidence_binding_status = _text(evidence_binding_status, limit=120)
    response_mode = _text(response_mode, limit=120)
    input_risk_level = _text(input_risk_level, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120)
    preview_advisory_summary = _text(preview_advisory_summary)
    shadow_candidate_id = _text(shadow_candidate_id, limit=240)
    patch_id = _text(patch_id, limit=240)
    diff_preview_id = _text(diff_preview_id, limit=240)
    rollback_plan_id = _text(rollback_plan_id, limit=240)
    dry_run_id = _text(dry_run_id, limit=240)
    generated_at = _text(generated_at, limit=120)
    model_provider = _text(model_provider, limit=120)
    model_name = _text(model_name, limit=120)
    zbid_preview_mode = _text(zbid_preview_mode, limit=120)
    requested_input_status = _text(zbid_input_status, limit=120)
    requested_mapping_status = _text(zbid_mapping_status, limit=120)
    requested_scoring_status = _text(zbid_scoring_matrix_status, limit=120)
    integration_request_id = _text(integration_request_id, limit=240)

    tender_file_refs_list = _list(tender_file_refs)
    scoring_clause_refs_list = _list(scoring_clause_refs)
    evidence_anchor_refs_list = _list(evidence_anchor_refs)

    generated_advisory_used_as_evidence = _bool(generated_advisory_used_as_evidence)
    preview_advisory_used_as_evidence = _bool(preview_advisory_used_as_evidence)
    shadow_candidate_used_as_evidence = _bool(shadow_candidate_used_as_evidence)
    patch_preview_used_as_evidence = _bool(patch_preview_used_as_evidence)
    diff_preview_used_as_evidence = _bool(diff_preview_used_as_evidence)
    rollback_plan_used_as_evidence = _bool(rollback_plan_used_as_evidence)
    dry_run_used_as_evidence = _bool(dry_run_used_as_evidence)
    scoring_clause_unverifiable = _bool(scoring_clause_unverifiable)
    high_risk_validation_ready = _bool(high_risk_validation_ready)
    zbid_writeback_requested = _bool(zbid_writeback_requested)
    docx_export_requested = _bool(docx_export_requested)
    review_apply_requested = _bool(review_apply_requested)
    formal_writeback_requested = _bool(formal_writeback_requested)
    output_write_requested = _bool(output_write_requested)

    blocked_reasons: list[str] = []
    requires_human_review = False

    enum_checks = (
        (zbid_preview_mode, ZBID_PREVIEW_MODES, "invalid_zbid_preview_mode"),
        (requested_input_status, ZBID_INPUT_STATUSES, "invalid_zbid_input_status"),
        (requested_mapping_status, ZBID_MAPPING_STATUSES, "invalid_zbid_mapping_status"),
        (
            requested_scoring_status,
            ZBID_SCORING_MATRIX_STATUSES,
            "invalid_zbid_scoring_matrix_status",
        ),
        (
            evidence_binding_status,
            _EVIDENCE_BINDING_STATUSES,
            "invalid_evidence_binding_status",
        ),
    )
    for value, allowed, reason in enum_checks:
        if value and value not in allowed:
            _append_unique(blocked_reasons, reason)

    missing_required_values = {
        "missing_project_id": project_id,
        "missing_document_id": document_id,
        "missing_section_id": section_id,
        "missing_section_hash": section_hash,
        "missing_section_version": section_version,
    }
    for reason, value in missing_required_values.items():
        if not value:
            _append_unique(blocked_reasons, reason)

    if not tender_file_refs_list:
        _append_unique(blocked_reasons, "missing_tender_file_refs")
        requires_human_review = True
    if not scoring_clause_refs_list:
        _append_unique(blocked_reasons, "missing_scoring_clause_refs")
        requires_human_review = True
    if scoring_clause_unverifiable:
        _append_unique(blocked_reasons, "unverifiable_scoring_clause_refs")
        requires_human_review = True

    if evidence_anchor_status == "missing" or not evidence_anchor_refs_list:
        _append_unique(blocked_reasons, "missing_evidence_anchor")
        requires_human_review = True

    evidence_source_blocks = (
        (generated_advisory_used_as_evidence, "generated_advisory_cannot_be_evidence"),
        (preview_advisory_used_as_evidence, "preview_advisory_cannot_be_evidence"),
        (shadow_candidate_used_as_evidence, "shadow_candidate_cannot_be_evidence"),
        (patch_preview_used_as_evidence, "patch_preview_cannot_be_evidence"),
        (diff_preview_used_as_evidence, "diff_preview_cannot_be_evidence"),
        (rollback_plan_used_as_evidence, "rollback_plan_cannot_be_evidence"),
        (dry_run_used_as_evidence, "dry_run_result_cannot_be_evidence"),
    )
    for used_as_evidence, reason in evidence_source_blocks:
        if used_as_evidence:
            _append_unique(blocked_reasons, reason)
            requires_human_review = True

    binding_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    if evidence_binding_status in binding_block_reasons:
        _append_unique(blocked_reasons, binding_block_reasons[evidence_binding_status])
        requires_human_review = True

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_integratable")
    elif response_mode in {"unsupported", "blocked"}:
        _append_unique(blocked_reasons, "unsupported_response_mode")
    elif response_mode and response_mode not in _RESPONSE_MODES:
        _append_unique(blocked_reasons, "unsupported_response_mode")

    if input_risk_level == "high" and not high_risk_validation_ready:
        _append_unique(blocked_reasons, "high_input_risk_not_validated")

    if advisory_quality_gate_status not in _QUALITY_GATE_ALLOWED_STATUSES:
        _append_unique(blocked_reasons, "advisory_quality_gate_not_passed")

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

    _append_unique(blocked_reasons, "preview_only_is_not_writeback_permission")
    _append_unique(blocked_reasons, "preview_only_is_not_evidence")
    _append_unique(blocked_reasons, "zbid_preview_scoring_is_not_evidence")

    if blocked_reasons[: -3]:
        input_status = "blocked"
        mapping_status = "mapping_blocked"
        scoring_status = "requires_human_review" if requires_human_review else "blocked"
    elif zbid_preview_mode == "metadata_only":
        input_status = requested_input_status or "accepted_metadata_only"
        mapping_status = requested_mapping_status or "mapping_placeholder_only"
        scoring_status = requested_scoring_status or "requires_human_review"
    else:
        input_status = requested_input_status or "accepted_preview_only"
        mapping_status = requested_mapping_status or "mapped_preview_only"
        scoring_status = requested_scoring_status or "preview_only"

    if input_status not in ZBID_INPUT_STATUSES:
        input_status = "blocked"
    if mapping_status not in ZBID_MAPPING_STATUSES:
        mapping_status = "mapping_blocked"
    if scoring_status not in ZBID_SCORING_MATRIX_STATUSES:
        scoring_status = "blocked"

    if not integration_request_id:
        integration_request_id = _preview_packet_id(
            {
                "source_system": source_system,
                "target_system": target_system,
                "project_id": project_id,
                "document_id": document_id,
                "section_id": section_id,
                "section_hash": section_hash,
                "section_version": section_version,
                "tender_file_refs": tender_file_refs_list,
                "scoring_clause_refs": scoring_clause_refs_list,
                "evidence_anchor_refs": evidence_anchor_refs_list,
            }
        )

    return {
        "contract_version": CONTRACT_VERSION,
        "integration_request_id": integration_request_id,
        "source_system": source_system,
        "target_system": target_system,
        "project_id": project_id,
        "document_id": document_id,
        "section_id": section_id,
        "section_title": section_title,
        "section_hash": section_hash,
        "section_version": section_version,
        "tender_file_refs": tender_file_refs_list,
        "scoring_clause_refs": scoring_clause_refs_list,
        "evidence_anchor_refs": evidence_anchor_refs_list,
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_binding_status": evidence_binding_status,
        "response_mode": response_mode,
        "input_risk_level": input_risk_level,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "preview_advisory_summary": preview_advisory_summary,
        "shadow_candidate_id": shadow_candidate_id,
        "patch_id": patch_id,
        "diff_preview_id": diff_preview_id,
        "rollback_plan_id": rollback_plan_id,
        "dry_run_id": dry_run_id,
        "zbid_preview_mode": zbid_preview_mode,
        "zbid_input_status": input_status,
        "zbid_mapping_status": mapping_status,
        "zbid_scoring_matrix_status": scoring_status,
        "zbid_writeback_requested": zbid_writeback_requested,
        "zbid_writeback_allowed": False,
        "docx_export_allowed": False,
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "generated_at": generated_at,
        "model_provider": model_provider,
        "model_name": model_name,
        "generated_advisory_used_as_evidence": generated_advisory_used_as_evidence,
        "preview_advisory_used_as_evidence": preview_advisory_used_as_evidence,
        "shadow_candidate_used_as_evidence": shadow_candidate_used_as_evidence,
        "patch_preview_used_as_evidence": patch_preview_used_as_evidence,
        "diff_preview_used_as_evidence": diff_preview_used_as_evidence,
        "rollback_plan_used_as_evidence": rollback_plan_used_as_evidence,
        "dry_run_used_as_evidence": dry_run_used_as_evidence,
        "scoring_clause_unverifiable": scoring_clause_unverifiable,
        "high_risk_validation_ready": high_risk_validation_ready,
        "docx_export_requested": docx_export_requested,
        "review_apply_requested": review_apply_requested,
        "formal_writeback_requested": formal_writeback_requested,
        "output_write_requested": output_write_requested,
    }
