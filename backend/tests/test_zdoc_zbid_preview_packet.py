import sys
from pathlib import Path

from backend.zhifei_autoplan import zdoc_zbid_preview_packet as packet_module
from backend.zhifei_autoplan.zdoc_zbid_preview_packet import (
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_ZDOC_ZBID_PREVIEW_PACKET_FIELDS,
    ZBID_INPUT_STATUSES,
    ZBID_MAPPING_STATUSES,
    ZBID_PREVIEW_MODES,
    ZBID_SCORING_MATRIX_STATUSES,
    build_zdoc_zbid_preview_packet,
)


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
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


def helper_source():
    return Path(packet_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(packet):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert packet[flag] is False


def test_zdoc_zbid_preview_packet_contains_required_fields():
    packet = build_safe_preview_packet()

    assert REQUIRED_ZDOC_ZBID_PREVIEW_PACKET_FIELDS.issubset(packet)
    assert packet["contract_version"] == "0.1"
    assert packet["source_system"] == "zdoc"
    assert packet["target_system"] == "zbid"
    assert packet["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(packet)


def test_zdoc_zbid_preview_status_enums_are_locked():
    assert ZBID_PREVIEW_MODES == {
        "disabled_current_stage",
        "metadata_only",
        "preview_only",
        "future_scoring_preview",
        "future_guarded_writeback",
    }
    assert ZBID_INPUT_STATUSES == {
        "not_created",
        "blocked",
        "accepted_metadata_only",
        "accepted_preview_only",
        "rejected",
        "stale_source_hash",
    }
    assert ZBID_MAPPING_STATUSES == {
        "not_mapped",
        "mapping_placeholder_only",
        "mapped_preview_only",
        "mapping_blocked",
    }
    assert ZBID_SCORING_MATRIX_STATUSES == {
        "not_created",
        "preview_only",
        "blocked",
        "requires_human_review",
    }


def test_safe_preview_packet_is_preview_only_and_not_writeback_permission():
    packet = build_safe_preview_packet()
    metadata_packet = build_safe_preview_packet(zbid_preview_mode="metadata_only")

    assert packet["zbid_preview_mode"] == "preview_only"
    assert packet["zbid_input_status"] == "accepted_preview_only"
    assert packet["zbid_mapping_status"] == "mapped_preview_only"
    assert packet["zbid_scoring_matrix_status"] == "preview_only"
    assert metadata_packet["zbid_input_status"] == "accepted_metadata_only"
    assert "preview_only_is_not_writeback_permission" in packet["blocked_reasons"]
    assert "preview_only_is_not_evidence" in packet["blocked_reasons"]
    assert "zbid_preview_scoring_is_not_evidence" in packet["blocked_reasons"]
    assert_formal_flags_false(packet)
    assert_formal_flags_false(metadata_packet)


def test_missing_evidence_anchor_is_blocked():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]
    for overrides in cases:
        packet = build_safe_preview_packet(**overrides)

        assert packet["zbid_input_status"] == "blocked"
        assert packet["zbid_scoring_matrix_status"] != "preview_only"
        assert "missing_evidence_anchor" in packet["blocked_reasons"]
        assert_formal_flags_false(packet)


def test_missing_tender_or_scoring_clause_refs_is_blocked():
    cases = [
        ({"tender_file_refs": []}, "missing_tender_file_refs"),
        ({"scoring_clause_refs": []}, "missing_scoring_clause_refs"),
    ]
    for overrides, reason in cases:
        packet = build_safe_preview_packet(**overrides)

        assert packet["zbid_input_status"] == "blocked"
        assert packet["zbid_scoring_matrix_status"] == "requires_human_review"
        assert reason in packet["blocked_reasons"]
        assert_formal_flags_false(packet)


def test_unverifiable_scoring_clause_requires_block_or_human_review():
    packet = build_safe_preview_packet(scoring_clause_unverifiable=True)

    assert packet["zbid_input_status"] == "blocked" or packet[
        "zbid_scoring_matrix_status"
    ] == "requires_human_review"
    assert "unverifiable_scoring_clause_refs" in packet["blocked_reasons"]
    assert packet["zbid_writeback_allowed"] is False


def test_generated_advisory_preview_shadow_patch_diff_rollback_and_dry_run_cannot_be_evidence():
    cases = [
        ("generated_advisory_used_as_evidence", "generated_advisory_cannot_be_evidence"),
        ("preview_advisory_used_as_evidence", "preview_advisory_cannot_be_evidence"),
        ("shadow_candidate_used_as_evidence", "shadow_candidate_cannot_be_evidence"),
        ("patch_preview_used_as_evidence", "patch_preview_cannot_be_evidence"),
        ("diff_preview_used_as_evidence", "diff_preview_cannot_be_evidence"),
        ("rollback_plan_used_as_evidence", "rollback_plan_cannot_be_evidence"),
        ("dry_run_used_as_evidence", "dry_run_result_cannot_be_evidence"),
    ]

    for field, reason in cases:
        packet = build_safe_preview_packet(**{field: True})

        assert packet["zbid_input_status"] == "blocked"
        assert packet["zbid_scoring_matrix_status"] != "preview_only"
        assert reason in packet["blocked_reasons"]
        assert_formal_flags_false(packet)


def test_thinking_only_fallback_is_blocked():
    packet = build_safe_preview_packet(response_mode="thinking_only_fallback")

    assert packet["zbid_input_status"] == "blocked"
    assert packet["zbid_scoring_matrix_status"] == "blocked"
    assert "thinking_only_fallback_not_integratable" in packet["blocked_reasons"]
    assert_formal_flags_false(packet)


def test_high_input_risk_without_validation_is_blocked():
    packet = build_safe_preview_packet(
        input_risk_level="high",
        high_risk_validation_ready=False,
    )

    assert packet["zbid_input_status"] == "blocked"
    assert "high_input_risk_not_validated" in packet["blocked_reasons"]
    assert_formal_flags_false(packet)


def test_failed_quality_gate_is_blocked():
    packet = build_safe_preview_packet(advisory_quality_gate_status="failed")

    assert packet["zbid_input_status"] == "blocked"
    assert "advisory_quality_gate_not_passed" in packet["blocked_reasons"]
    assert_formal_flags_false(packet)


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

        assert packet["zbid_input_status"] == "blocked"
        assert reason in packet["blocked_reasons"]
        assert_formal_flags_false(packet)


def test_formal_flags_are_always_false():
    cases = []
    cases.extend({"zbid_preview_mode": mode} for mode in ZBID_PREVIEW_MODES)
    cases.extend({"zbid_input_status": status} for status in ZBID_INPUT_STATUSES)
    cases.extend({"zbid_mapping_status": status} for status in ZBID_MAPPING_STATUSES)
    cases.extend({"zbid_scoring_matrix_status": status} for status in ZBID_SCORING_MATRIX_STATUSES)

    for overrides in cases:
        packet = build_safe_preview_packet(**overrides)

        assert_formal_flags_false(packet)


def test_generated_at_is_caller_supplied_and_deterministic():
    fixed = "2026-01-01T00:00:00Z"
    packet = build_safe_preview_packet(generated_at=fixed)
    source = helper_source()

    assert packet["generated_at"] == fixed
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_integration_request_id_is_deterministic():
    first = build_safe_preview_packet()
    second = build_safe_preview_packet()
    changed = build_safe_preview_packet(section_hash="sha256:changed")
    explicit = build_safe_preview_packet(integration_request_id="fixed-preview-packet-id")

    assert first["integration_request_id"] == second["integration_request_id"]
    assert first["integration_request_id"] != changed["integration_request_id"]
    assert explicit["integration_request_id"] == "fixed-preview-packet-id"


def test_helper_does_not_call_zbid_start_services_or_write_files():
    source = helper_source()
    packet = build_safe_preview_packet(
        preview_advisory_summary="caller supplied preview summary",
        shadow_candidate_id="caller-supplied-shadow-id",
        dry_run_id="caller-supplied-dry-run-id",
    )

    assert packet["preview_advisory_summary"] == "caller supplied preview summary"
    assert packet["shadow_candidate_id"] == "caller-supplied-shadow-id"
    assert packet["dry_run_id"] == "caller-supplied-dry-run-id"
    assert packet["zbid_writeback_allowed"] is False
    assert packet["docx_export_allowed"] is False
    assert packet["review_apply_allowed"] is False
    assert packet["formal_writeback_allowed"] is False
    assert packet["output_write_allowed"] is False
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


def test_importing_helper_does_not_pull_main_chain_or_zbid_modules(assert_clean_import):
    assert_clean_import(
        "backend.zhifei_autoplan.zdoc_zbid_preview_packet",
        MAIN_CHAIN_OR_ZBID_MODULES,
    )
    source = helper_source()

    assert "from docx" not in source
    assert "import docx" not in source
    assert "python_docx" not in source
    assert "zbid_snapshot_mapper" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "from fastapi" not in source.lower()
    assert "import fastapi" not in source.lower()
    assert "ollama" not in source.lower()
