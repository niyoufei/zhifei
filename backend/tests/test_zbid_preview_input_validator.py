import sys
from pathlib import Path

from backend.zhifei_autoplan import zbid_preview_input_validator as validator_module
from backend.zhifei_autoplan.zbid_preview_input_validator import (
    CURRENT_STAGE_FORMAL_FLAGS,
    EVIDENCE_BLOCKED_SOURCES,
    REQUIRED_PREVIEW_PACKET_FIELDS,
    ZBID_PREVIEW_VALIDATION_DECISIONS,
    ZBID_PREVIEW_VALIDATION_STATUSES,
    validate_zbid_preview_input,
)
from backend.zhifei_autoplan.zdoc_zbid_preview_packet import build_zdoc_zbid_preview_packet


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
VALIDATION_REQUIRED_FIELDS = {
    "contract_version",
    "integration_request_id",
    "source_system",
    "target_system",
    "project_id",
    "document_id",
    "section_id",
    "section_hash",
    "section_version",
    "zbid_preview_validation_status",
    "zbid_preview_validation_decision",
    "zbid_preview_mode",
    "zbid_input_status",
    "zbid_mapping_status",
    "zbid_scoring_matrix_status",
    "tender_file_refs",
    "scoring_clause_refs",
    "evidence_anchor_refs",
    "evidence_anchor_status",
    "evidence_binding_status",
    "response_mode",
    "input_risk_level",
    "advisory_quality_gate_status",
    "formal_writeback_allowed",
    "review_apply_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
    "validation_notes",
}
MAIN_CHAIN_OR_ZBID_MODULES = {
    "backend.zhifei_autoplan.orchestrator",
    "backend.zhifei_autoplan.llm_client",
    "backend.zhifei_autoplan.provider",
    "backend.zhifei_autoplan.generation",
    "backend.zhifei_autoplan.export",
    "backend.zhifei_autoplan.review",
    "backend.app.routers.actions_bridge",
    "backend.app.routers.export",
    "backend.app.routers.review",
    "backend.zhifei_autoplan.zbid_snapshot_mapper",
    "docx",
}


def build_safe_preview_packet(**overrides):
    payload = {
        "source_system": "zdoc",
        "target_system": "zbid",
        "project_id": "project-preview-only",
        "document_id": "doc-preview-only",
        "section_id": "section-preview-only",
        "section_title": "Preview Only Section",
        "section_hash": "sha256:section-preview",
        "section_version": "v1",
        "tender_file_refs": ["tender:file:001"],
        "scoring_clause_refs": ["tender:scoring-clause:001"],
        "evidence_anchor_refs": ["tender:evidence-anchor:001"],
        "evidence_anchor_status": "source_verified",
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "preview_advisory_summary": "Fake preview-only advisory summary.",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "dry_run_id": "dry-run-preview-only",
        "generated_at": FIXED_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "generated_advisory_used_as_evidence": False,
        "preview_advisory_used_as_evidence": False,
        "shadow_candidate_used_as_evidence": False,
        "patch_preview_used_as_evidence": False,
        "diff_preview_used_as_evidence": False,
        "rollback_plan_used_as_evidence": False,
        "dry_run_used_as_evidence": False,
        "scoring_clause_unverifiable": False,
        "high_risk_validation_ready": False,
        "zbid_writeback_requested": False,
        "docx_export_requested": False,
        "review_apply_requested": False,
        "formal_writeback_requested": False,
        "output_write_requested": False,
    }
    payload.update(overrides)
    return build_zdoc_zbid_preview_packet(**payload)


def validator_source():
    return Path(validator_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(result):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert result[flag] is False


def test_zbid_preview_validator_returns_required_fields():
    packet = build_safe_preview_packet()
    result = validate_zbid_preview_input(packet)

    assert REQUIRED_PREVIEW_PACKET_FIELDS.issubset(packet)
    assert VALIDATION_REQUIRED_FIELDS.issubset(result)
    assert result["contract_version"] == "0.1"
    assert result["integration_request_id"] == packet["integration_request_id"]
    assert result["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(result)


def test_zbid_preview_validator_status_and_decision_enums_are_locked():
    assert ZBID_PREVIEW_VALIDATION_STATUSES == {
        "not_validated",
        "blocked",
        "accepted_metadata_only",
        "accepted_preview_only",
        "requires_human_review",
        "rejected",
        "stale_source_hash",
    }
    assert ZBID_PREVIEW_VALIDATION_DECISIONS == {
        "none",
        "block",
        "accept_metadata_only",
        "accept_preview_only",
        "require_human_review",
        "reject",
    }
    assert EVIDENCE_BLOCKED_SOURCES == {
        "generated_advisory",
        "preview_advisory_summary",
        "shadow_candidate",
        "patch_preview",
        "diff_preview",
        "rollback_plan",
        "dry_run_result",
        "zbid_preview_scoring",
    }


def test_safe_metadata_only_input_is_accepted_but_not_writeback_permission():
    packet = build_safe_preview_packet(zbid_preview_mode="metadata_only")
    result = validate_zbid_preview_input(packet)

    assert result["zbid_preview_validation_status"] == "accepted_metadata_only"
    assert result["zbid_preview_validation_decision"] == "accept_metadata_only"
    assert "preview_only_is_not_writeback_permission" in result["blocked_reasons"]
    assert "preview_only_is_not_evidence" in result["blocked_reasons"]
    assert "zbid_preview_scoring_is_not_evidence" in result["blocked_reasons"]
    assert_formal_flags_false(result)


def test_safe_preview_only_input_is_accepted_but_not_writeback_permission():
    packet = build_safe_preview_packet()
    result = validate_zbid_preview_input(packet)

    assert result["zbid_preview_validation_status"] == "accepted_preview_only"
    assert result["zbid_preview_validation_decision"] == "accept_preview_only"
    assert result["zbid_input_status"] == "accepted_preview_only"
    assert "preview_only_is_not_writeback_permission" in result["blocked_reasons"]
    assert "accepted_preview_input_does_not_grant_writeback_permission" in result[
        "validation_notes"
    ]
    assert_formal_flags_false(result)


def test_invalid_packet_or_missing_core_ids_is_blocked():
    invalid = validate_zbid_preview_input(None)
    assert invalid["zbid_preview_validation_status"] == "blocked"
    assert "invalid_preview_packet" in invalid["blocked_reasons"]
    assert_formal_flags_false(invalid)

    cases = {
        "integration_request_id": "missing_integration_request_id",
        "project_id": "missing_project_id",
        "document_id": "missing_document_id",
        "section_id": "missing_section_id",
        "section_hash": "missing_section_hash",
        "section_version": "missing_section_version",
    }
    for field, reason in cases.items():
        packet = build_safe_preview_packet()
        packet[field] = ""
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert result["zbid_preview_validation_decision"] == "block"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_missing_tender_or_scoring_refs_is_blocked():
    cases = [
        ({"tender_file_refs": []}, "missing_tender_file_refs"),
        ({"scoring_clause_refs": []}, "missing_scoring_clause_refs"),
    ]
    for overrides, reason in cases:
        packet = build_safe_preview_packet(**overrides)
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_missing_evidence_anchor_is_blocked():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]
    for overrides in cases:
        packet = build_safe_preview_packet(**overrides)
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert "missing_evidence_anchor" in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_generated_advisory_preview_shadow_patch_diff_rollback_and_dry_run_cannot_be_evidence():
    cases = [
        ("generated_advisory_used_as_evidence", "generated_advisory_cannot_be_evidence"),
        ("preview_advisory_used_as_evidence", "preview_advisory_cannot_be_evidence"),
        ("shadow_candidate_used_as_evidence", "shadow_candidate_cannot_be_evidence"),
        ("patch_preview_used_as_evidence", "patch_preview_cannot_be_evidence"),
        ("diff_preview_used_as_evidence", "diff_preview_cannot_be_evidence"),
        ("rollback_plan_used_as_evidence", "rollback_plan_cannot_be_evidence"),
        ("dry_run_used_as_evidence", "dry_run_result_cannot_be_evidence"),
        ("zbid_preview_scoring_used_as_evidence", "zbid_preview_scoring_is_not_evidence"),
    ]
    for field, reason in cases:
        packet = build_safe_preview_packet()
        packet[field] = True
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)

    binding_cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    for binding_status, reason in binding_cases.items():
        packet = build_safe_preview_packet(evidence_binding_status=binding_status)
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_thinking_only_fallback_or_unsupported_response_mode_is_blocked():
    cases = [
        ("thinking_only_fallback", "thinking_only_fallback_not_integratable"),
        ("unsupported", "unsupported_response_mode"),
        ("blocked", "unsupported_response_mode"),
    ]
    for response_mode, reason in cases:
        packet = build_safe_preview_packet(response_mode=response_mode)
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_high_input_risk_without_validation_is_blocked():
    packet = build_safe_preview_packet(
        input_risk_level="high",
        high_risk_validation_ready=False,
    )
    result = validate_zbid_preview_input(packet)

    assert result["zbid_preview_validation_status"] == "blocked"
    assert "high_input_risk_not_validated" in result["blocked_reasons"]
    assert_formal_flags_false(result)


def test_failed_quality_gate_is_blocked():
    packet = build_safe_preview_packet(advisory_quality_gate_status="failed")
    result = validate_zbid_preview_input(packet)

    assert result["zbid_preview_validation_status"] == "blocked"
    assert "advisory_quality_gate_not_passed" in result["blocked_reasons"]
    assert_formal_flags_false(result)


def test_future_guarded_writeback_is_blocked_current_stage():
    packet = build_safe_preview_packet(zbid_preview_mode="future_guarded_writeback")
    result = validate_zbid_preview_input(packet)

    assert result["zbid_preview_validation_status"] == "blocked"
    assert "future_guarded_writeback_not_enabled" in result["blocked_reasons"]
    assert_formal_flags_false(result)


def test_zbid_docx_review_apply_formal_and_output_requests_are_blocked():
    cases = [
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"review_apply_requested": True}, "review_apply_request_blocked"),
        ({"formal_writeback_requested": True}, "formal_writeback_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
    ]
    for overrides, reason in cases:
        packet = build_safe_preview_packet(**overrides)
        result = validate_zbid_preview_input(packet)

        assert result["zbid_preview_validation_status"] == "blocked"
        assert reason in result["blocked_reasons"]
        assert_formal_flags_false(result)


def test_formal_flags_are_always_false():
    statuses = [
        "accepted_metadata_only",
        "accepted_preview_only",
        "blocked",
        "rejected",
        "stale_source_hash",
    ]
    for status in statuses:
        packet = build_safe_preview_packet(zbid_input_status=status)
        result = validate_zbid_preview_input(packet)

        assert_formal_flags_false(result)


def test_validator_does_not_call_zbid_start_services_or_write_files():
    source = validator_source()
    packet = build_safe_preview_packet()
    result = validate_zbid_preview_input(packet)

    assert result["zbid_writeback_allowed"] is False
    assert result["docx_export_allowed"] is False
    assert result["review_apply_allowed"] is False
    assert result["formal_writeback_allowed"] is False
    assert result["output_write_allowed"] is False
    assert "write_text" not in source
    assert "write_bytes" not in source
    assert "mkdir(" not in source
    assert "open(" not in source
    assert "subprocess" not in source
    assert "urlopen" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "fastapi" not in source.lower()
    assert "ollama" not in source.lower()
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_importing_validator_does_not_pull_main_chain_or_zbid_modules(assert_clean_import):
    assert_clean_import(
        "backend.zhifei_autoplan.zbid_preview_input_validator",
        MAIN_CHAIN_OR_ZBID_MODULES,
    )
    source = validator_source()

    assert "from docx" not in source
    assert "import docx" not in source
    assert "python_docx" not in source
    assert "zbid_snapshot_mapper" not in source
    assert "zdoc_zbid_preview_packet" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "from fastapi" not in source.lower()
    assert "import fastapi" not in source.lower()
    assert "ollama" not in source.lower()
