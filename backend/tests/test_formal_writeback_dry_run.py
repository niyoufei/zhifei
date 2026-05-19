import sys
from pathlib import Path

from backend.zhifei_autoplan import formal_writeback_dry_run as dry_run_module
from backend.zhifei_autoplan.formal_writeback_dry_run import (
    CURRENT_STAGE_EMITTABLE_DRY_RUN_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    DRY_RUN_DECISIONS,
    DRY_RUN_MODES,
    DRY_RUN_REQUEST_STATUSES,
    DRY_RUN_SCOPES,
    DRY_RUN_STATUSES,
    DRY_RUN_TARGET_TYPES,
    REQUIRED_FORMAL_WRITEBACK_DRY_RUN_FIELDS,
    build_formal_writeback_dry_run,
)


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
MAIN_EXPORT_DOCX_OR_ZBID_MODULES = {
    "backend.zhifei_autoplan.orchestrator",
    "backend.zhifei_autoplan.llm_client",
    "backend.zhifei_autoplan.provider",
    "backend.zhifei_autoplan.generation",
    "backend.zhifei_autoplan.export",
    "backend.zhifei_autoplan.review",
    "backend.app.routers.actions_bridge",
    "backend.app.routers.export",
    "backend.app.routers.review",
    "docx",
}


def build_safe_dry_run(**overrides):
    payload = {
        "request_id": "req-formal-writeback-dry-run-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "current_source_section_hash": "sha256:source-section",
        "current_source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "writeback_guard_id": "writeback-guard-preview-only",
        "source_hash_guard_id": "source-hash-guard-preview-only",
        "review_apply_guard_id": "review-apply-guard-preview-only",
        "docx_isolation_guard_id": "docx-isolation-guard-preview-only",
        "zbid_isolation_guard_id": "zbid-isolation-guard-preview-only",
        "dry_run_decision": "none",
        "dry_run_scope": "single_section",
        "dry_run_mode": "disabled_current_stage",
        "dry_run_target_type": "metadata_only",
        "dry_run_request_status": "not_requested",
        "dry_run_requested": False,
        "dry_run_payload_hash": "sha256:dry-run-payload-preview",
        "dry_run_candidate_hash": "sha256:dry-run-candidate-preview",
        "dry_run_source_snapshot_hash": "sha256:dry-run-source-snapshot",
        "writeback_candidate_hash": "sha256:writeback-candidate",
        "docx_candidate_hash": "sha256:docx-candidate-preview",
        "zbid_candidate_hash": "sha256:zbid-candidate-preview",
        "zbid_target_mapping_hash": "sha256:zbid-target-mapping-preview",
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
        "rollback_plan_hash": "sha256:rollback-plan",
        "affected_anchor_refs": ["section:anchor:affected"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:evidence"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "shadow_candidate_status": "draft_shadow_only",
        "patch_status": "draft_patch_shadow_only",
        "approval_status": "approved_shadow_only",
        "diff_preview_status": "approved_diff_shadow_only",
        "rollback_plan_status": "approved_rollback_shadow_only",
        "writeback_guard_status": "approved_guard_shadow_only",
        "source_hash_guard_status": "source_hash_matched_shadow_only",
        "review_apply_isolation_status": "isolated_shadow_only",
        "docx_isolation_status": "isolated_shadow_only",
        "zbid_isolation_status": "isolated_shadow_only",
        "source_hash_revalidation_status": "matched",
        "source_version_revalidation_status": "matched",
        "source_hash_match": True,
        "source_version_match": True,
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "review_apply_isolation_required": True,
        "review_apply_isolation_ready": True,
        "docx_isolation_required": True,
        "docx_isolation_ready": True,
        "zbid_isolation_required": True,
        "zbid_isolation_ready": True,
        "generated_at": FIXED_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "docx_export_requested": False,
        "zbid_writeback_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "review_apply_request_triggered": False,
        "export_docx_request_triggered": False,
        "zbid_writeback_request_triggered": False,
        "dry_run_request_triggered": False,
    }
    payload.update(overrides)
    return build_formal_writeback_dry_run(**payload)


def helper_source():
    return Path(dry_run_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(dry_run):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert dry_run[flag] is False


def test_formal_writeback_dry_run_contains_required_fields():
    dry_run = build_safe_dry_run()

    assert REQUIRED_FORMAL_WRITEBACK_DRY_RUN_FIELDS.issubset(dry_run)
    assert dry_run["contract_version"] == "0.1"
    assert dry_run["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(dry_run)


def test_dry_run_status_decision_scope_mode_target_and_request_enums_are_locked():
    assert DRY_RUN_STATUSES == {
        "not_created",
        "blocked",
        "draft_dry_run_shadow_only",
        "simulated_shadow_only",
        "passed_shadow_only",
        "failed_shadow_only",
        "rejected",
        "stale_source_hash",
        "stale_source_version",
    }
    assert DRY_RUN_DECISIONS == {
        "none",
        "block",
        "simulate_shadow_only",
        "pass_shadow_only",
        "require_revision",
        "reject",
    }
    assert DRY_RUN_SCOPES == {
        "single_section",
        "selected_sections",
        "full_document",
        "metadata_only",
    }
    assert DRY_RUN_MODES == {
        "disabled_current_stage",
        "metadata_only",
        "future_dry_run_only",
        "future_guarded_dry_run",
    }
    assert DRY_RUN_TARGET_TYPES == {
        "source_section",
        "section_draft",
        "docx_document",
        "zbid_section",
        "metadata_only",
    }
    assert DRY_RUN_REQUEST_STATUSES == {
        "not_requested",
        "requested_blocked",
        "payload_blocked",
        "future_dry_run_only",
    }


def test_helper_only_emits_blocked_not_created_stale_hash_or_stale_version():
    cases = [
        {},
        {"request_id": ""},
        {"source_hash_match": False},
        {"source_version_match": False},
        {"dry_run_status": "passed_shadow_only"},
    ]

    for overrides in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] in CURRENT_STAGE_EMITTABLE_DRY_RUN_STATUSES
        assert dry_run["dry_run_status"] not in {
            "draft_dry_run_shadow_only",
            "simulated_shadow_only",
            "passed_shadow_only",
        }
        assert "real_formal_writeback_dry_run_not_implemented_current_stage" in dry_run[
            "blocked_reasons"
        ]


def test_passed_shadow_only_is_not_writeback_permission():
    cases = [
        {"dry_run_status": "passed_shadow_only"},
        {"dry_run_decision": "pass_shadow_only"},
    ]
    for overrides in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] in {
            "blocked",
            "not_created",
            "stale_source_hash",
            "stale_source_version",
        }
        assert "dry_run_is_not_formal_writeback_permission" in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_missing_upstream_ids_are_blocked():
    cases = {
        "shadow_candidate_id": "missing_shadow_candidate_id",
        "patch_id": "missing_patch_id",
        "approval_id": "missing_approval_id",
        "diff_preview_id": "missing_diff_preview_id",
        "rollback_plan_id": "missing_rollback_plan_id",
        "writeback_guard_id": "missing_writeback_guard_id",
        "source_hash_guard_id": "missing_source_hash_guard_id",
        "review_apply_guard_id": "missing_review_apply_guard_id",
        "docx_isolation_guard_id": "missing_docx_isolation_guard_id",
        "zbid_isolation_guard_id": "missing_zbid_isolation_guard_id",
    }

    for field, reason in cases.items():
        dry_run = build_safe_dry_run(**{field: ""})

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_blocked_upstream_statuses_are_blocked():
    cases = [
        ({"shadow_candidate_status": "blocked"}, "shadow_candidate_not_ready"),
        ({"shadow_candidate_status": "not_created"}, "shadow_candidate_not_ready"),
        ({"patch_status": "blocked"}, "patch_not_ready"),
        ({"patch_status": "not_created"}, "patch_not_ready"),
        ({"approval_status": "pending_human_review"}, "approval_not_received"),
        ({"diff_preview_status": "blocked"}, "diff_preview_not_ready"),
        ({"diff_preview_status": "not_created"}, "diff_preview_not_ready"),
        ({"diff_preview_status": "stale_source_hash"}, "diff_preview_not_ready"),
        ({"rollback_plan_status": "blocked"}, "rollback_plan_not_ready"),
        ({"rollback_plan_status": "not_created"}, "rollback_plan_not_ready"),
        ({"rollback_plan_status": "stale_source_hash"}, "rollback_plan_not_ready"),
        ({"writeback_guard_status": "blocked"}, "writeback_guard_not_ready"),
        ({"writeback_guard_status": "not_created"}, "writeback_guard_not_ready"),
        ({"writeback_guard_status": "stale_source_hash"}, "writeback_guard_not_ready"),
        ({"source_hash_guard_status": "blocked"}, "source_hash_guard_not_ready"),
        ({"source_hash_guard_status": "not_created"}, "source_hash_guard_not_ready"),
        ({"source_hash_guard_status": "stale_source_hash"}, "source_hash_guard_not_ready"),
        (
            {"source_hash_guard_status": "stale_source_version"},
            "source_hash_guard_not_ready",
        ),
        ({"review_apply_isolation_status": "blocked"}, "review_apply_guard_not_ready"),
        ({"review_apply_isolation_status": "not_created"}, "review_apply_guard_not_ready"),
        (
            {"review_apply_isolation_status": "stale_source_hash"},
            "review_apply_guard_not_ready",
        ),
        (
            {"review_apply_isolation_status": "stale_source_version"},
            "review_apply_guard_not_ready",
        ),
        ({"docx_isolation_status": "blocked"}, "docx_isolation_guard_not_ready"),
        ({"docx_isolation_status": "not_created"}, "docx_isolation_guard_not_ready"),
        ({"docx_isolation_status": "stale_source_hash"}, "docx_isolation_guard_not_ready"),
        (
            {"docx_isolation_status": "stale_source_version"},
            "docx_isolation_guard_not_ready",
        ),
        ({"zbid_isolation_status": "blocked"}, "zbid_isolation_guard_not_ready"),
        ({"zbid_isolation_status": "not_created"}, "zbid_isolation_guard_not_ready"),
        ({"zbid_isolation_status": "stale_source_hash"}, "zbid_isolation_guard_not_ready"),
        (
            {"zbid_isolation_status": "stale_source_version"},
            "zbid_isolation_guard_not_ready",
        ),
    ]

    for overrides, reason in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_thinking_only_fallback_is_blocked():
    dry_run = build_safe_dry_run(response_mode="thinking_only_fallback")

    assert dry_run["dry_run_status"] == "blocked"
    assert "thinking_only_fallback_not_dry_run_capable" in dry_run["blocked_reasons"]
    assert_formal_flags_false(dry_run)


def test_missing_evidence_anchor_is_blocked():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]
    for overrides in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == "blocked"
        assert "missing_evidence_anchor" in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        dry_run = build_safe_dry_run(evidence_binding_status=binding_status)

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_source_hash_or_version_mismatch_is_blocked():
    cases = [
        ({"source_hash_match": False}, "stale_source_hash", "source_hash_mismatch"),
        ({"source_version_match": False}, "stale_source_version", "source_version_mismatch"),
        (
            {"source_hash_revalidation_status": "mismatched"},
            "stale_source_hash",
            "source_hash_mismatch",
        ),
        (
            {"source_hash_revalidation_status": "stale_source_hash"},
            "stale_source_hash",
            "stale_source_hash",
        ),
        (
            {"source_version_revalidation_status": "mismatched"},
            "stale_source_version",
            "source_version_mismatch",
        ),
        (
            {"source_version_revalidation_status": "stale_source_version"},
            "stale_source_version",
            "stale_source_version",
        ),
        ({"current_source_section_hash": ""}, "blocked", "missing_current_source_section_hash"),
        (
            {"current_source_section_version": ""},
            "blocked",
            "missing_current_source_section_version",
        ),
    ]

    for overrides, expected_status, reason in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == expected_status
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_dry_run_request_payload_and_candidate_are_blocked():
    cases = [
        ({"dry_run_requested": True}, "dry_run_request_blocked"),
        ({"dry_run_request_status": "requested_blocked"}, "dry_run_request_blocked"),
        ({"dry_run_request_status": "payload_blocked"}, "dry_run_payload_blocked"),
        ({"dry_run_payload_hash": ""}, "dry_run_payload_blocked"),
        ({"dry_run_candidate_hash": ""}, "missing_dry_run_candidate_hash"),
    ]

    for overrides, reason in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_missing_required_hashes_are_blocked():
    cases = {
        "dry_run_source_snapshot_hash": "missing_dry_run_source_snapshot_hash",
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "docx_candidate_hash": "missing_docx_candidate_hash",
        "zbid_candidate_hash": "missing_zbid_candidate_hash",
        "zbid_target_mapping_hash": "missing_zbid_target_mapping_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }

    for field, reason in cases.items():
        dry_run = build_safe_dry_run(**{field: ""})

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_missing_required_guards_are_blocked():
    cases = [
        (
            {"human_approval_required": True, "human_approval_received": False},
            "human_approval_missing",
        ),
        ({"diff_preview_required": True, "diff_preview_ready": False}, "diff_preview_missing"),
        ({"rollback_required": True, "rollback_plan_ready": False}, "rollback_plan_missing"),
        (
            {"formal_writeback_guard_required": True, "formal_writeback_guard_ready": False},
            "formal_writeback_guard_missing",
        ),
        (
            {"source_hash_revalidation_required": True, "source_hash_revalidation_ready": False},
            "source_hash_revalidation_missing",
        ),
        (
            {"review_apply_isolation_required": True, "review_apply_isolation_ready": False},
            "review_apply_isolation_missing",
        ),
        ({"docx_isolation_required": True, "docx_isolation_ready": False}, "docx_isolation_missing"),
        ({"zbid_isolation_required": True, "zbid_isolation_ready": False}, "zbid_isolation_missing"),
    ]

    for overrides, reason in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_docx_zbid_output_formal_review_apply_and_dry_run_requests_are_blocked():
    cases = [
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
        ({"formal_generation_requested": True}, "formal_generation_request_blocked"),
        ({"review_apply_request_triggered": True}, "review_apply_request_blocked"),
        ({"export_docx_request_triggered": True}, "export_docx_request_blocked"),
        ({"zbid_writeback_request_triggered": True}, "zbid_writeback_request_blocked"),
        ({"dry_run_request_triggered": True}, "dry_run_request_triggered_blocked"),
    ]

    for overrides, reason in cases:
        dry_run = build_safe_dry_run(**overrides)

        assert dry_run["dry_run_status"] == "blocked"
        assert reason in dry_run["blocked_reasons"]
        assert_formal_flags_false(dry_run)


def test_formal_flags_are_always_false():
    for status in DRY_RUN_STATUSES:
        dry_run = build_safe_dry_run(dry_run_status=status)

        assert_formal_flags_false(dry_run)


def test_guard_does_not_perform_dry_run_or_writeback():
    source = helper_source()
    dry_run = build_safe_dry_run(
        dry_run_payload_hash="sha256:caller-supplied-dry-run-payload",
        dry_run_candidate_hash="sha256:caller-supplied-dry-run-candidate",
        zbid_candidate_hash="sha256:caller-supplied-zbid-candidate",
    )

    assert dry_run["dry_run_payload_hash"] == "sha256:caller-supplied-dry-run-payload"
    assert dry_run["dry_run_candidate_hash"] == "sha256:caller-supplied-dry-run-candidate"
    assert dry_run["zbid_candidate_hash"] == "sha256:caller-supplied-zbid-candidate"
    assert dry_run["formal_writeback_allowed"] is False
    assert dry_run["review_apply_allowed"] is False
    assert dry_run["docx_export_allowed"] is False
    assert dry_run["zbid_writeback_allowed"] is False
    assert dry_run["output_write_allowed"] is False
    assert dry_run["affected_anchor_refs"] != dry_run["evidence_anchor_refs"]
    assert "write_text" not in source
    assert "write_bytes" not in source
    assert "mkdir(" not in source
    assert "open(" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "fastapi" not in source.lower()
    assert "ollama" not in source.lower()


def test_generated_at_is_caller_supplied_and_deterministic():
    fixed = "2026-01-01T00:00:00Z"
    dry_run = build_safe_dry_run(generated_at=fixed)
    source = helper_source()

    assert dry_run["generated_at"] == fixed
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_dry_run_id_is_deterministic():
    first = build_safe_dry_run()
    second = build_safe_dry_run()
    changed = build_safe_dry_run(dry_run_payload_hash="sha256:changed")
    explicit = build_safe_dry_run(dry_run_id="fixed-formal-writeback-dry-run-id")

    assert first["dry_run_id"] == second["dry_run_id"]
    assert first["dry_run_id"] != changed["dry_run_id"]
    assert explicit["dry_run_id"] == "fixed-formal-writeback-dry-run-id"


def test_importing_helper_does_not_pull_main_export_docx_or_zbid_modules():
    leaked_modules = MAIN_EXPORT_DOCX_OR_ZBID_MODULES.intersection(sys.modules)
    source = helper_source()

    assert leaked_modules == set()
    assert "from docx" not in source
    assert "import docx" not in source
    assert "python_docx" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "from fastapi" not in source.lower()
    assert "import fastapi" not in source.lower()
    assert "ollama" not in source.lower()
    assert "zbid_snapshot_mapper" not in source
