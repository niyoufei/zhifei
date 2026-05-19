import sys
from pathlib import Path

from backend.zhifei_autoplan import zbid_isolation_guard as zbid_guard_module
from backend.zhifei_autoplan.zbid_isolation_guard import (
    CURRENT_STAGE_EMITTABLE_ZBID_ISOLATION_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_ZBID_ISOLATION_GUARD_FIELDS,
    ZBID_ISOLATION_STATUSES,
    ZBID_TARGET_TYPES,
    ZBID_WRITEBACK_DECISIONS,
    ZBID_WRITEBACK_MODES,
    ZBID_WRITEBACK_REQUEST_STATUSES,
    ZBID_WRITEBACK_SCOPES,
    build_zbid_isolation_guard,
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


def build_safe_zbid_guard(**overrides):
    payload = {
        "request_id": "req-zbid-isolation-guard-001",
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
        "zbid_writeback_decision": "none",
        "zbid_writeback_scope": "single_section",
        "zbid_writeback_mode": "disabled_current_stage",
        "zbid_target_type": "metadata_only",
        "zbid_writeback_request_status": "not_requested",
        "zbid_writeback_requested": False,
        "zbid_writeback_route": "",
        "zbid_writeback_payload_hash": "sha256:zbid-writeback-payload-preview",
        "zbid_candidate_hash": "sha256:zbid-candidate-preview",
        "zbid_target_mapping_hash": "sha256:zbid-target-mapping-preview",
        "zbid_source_snapshot_hash": "sha256:zbid-source-snapshot",
        "docx_candidate_hash": "sha256:docx-candidate-preview",
        "writeback_candidate_hash": "sha256:writeback-candidate",
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
        "generated_at": FIXED_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "docx_export_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "review_apply_request_triggered": False,
        "export_docx_request_triggered": False,
        "zbid_writeback_request_triggered": False,
    }
    payload.update(overrides)
    return build_zbid_isolation_guard(**payload)


def helper_source():
    return Path(zbid_guard_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(zbid_guard):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert zbid_guard[flag] is False


def test_zbid_isolation_guard_contains_required_fields():
    zbid_guard = build_safe_zbid_guard()

    assert REQUIRED_ZBID_ISOLATION_GUARD_FIELDS.issubset(zbid_guard)
    assert zbid_guard["contract_version"] == "0.1"
    assert zbid_guard["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(zbid_guard)


def test_zbid_status_decision_scope_mode_target_and_request_enums_are_locked():
    assert ZBID_ISOLATION_STATUSES == {
        "not_created",
        "blocked",
        "draft_isolation_shadow_only",
        "isolated_shadow_only",
        "ready_for_future_manual_writeback",
        "rejected",
        "stale_source_hash",
        "stale_source_version",
    }
    assert ZBID_WRITEBACK_DECISIONS == {
        "none",
        "block",
        "isolate_shadow_only",
        "require_revision",
        "reject",
    }
    assert ZBID_WRITEBACK_SCOPES == {
        "single_section",
        "selected_sections",
        "full_document",
        "metadata_only",
    }
    assert ZBID_WRITEBACK_MODES == {
        "disabled_current_stage",
        "dry_run_only",
        "future_manual_writeback",
        "future_guarded_writeback",
    }
    assert ZBID_TARGET_TYPES == {
        "zbid_section",
        "zbid_document",
        "zbid_scoring_matrix",
        "zbid_metadata",
        "metadata_only",
    }
    assert ZBID_WRITEBACK_REQUEST_STATUSES == {
        "not_requested",
        "requested_blocked",
        "route_blocked",
        "payload_blocked",
        "mapping_blocked",
        "future_dry_run_only",
    }


def test_helper_only_emits_blocked_not_created_stale_hash_or_stale_version():
    cases = [
        {},
        {"request_id": ""},
        {"source_hash_match": False},
        {"source_version_match": False},
        {"zbid_isolation_status": "isolated_shadow_only"},
    ]

    for overrides in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] in (
            CURRENT_STAGE_EMITTABLE_ZBID_ISOLATION_STATUSES
        )
        assert zbid_guard["zbid_isolation_status"] not in {
            "draft_isolation_shadow_only",
            "isolated_shadow_only",
            "ready_for_future_manual_writeback",
        }
        assert "real_zbid_isolation_not_implemented_current_stage" in zbid_guard[
            "blocked_reasons"
        ]


def test_isolated_shadow_only_is_not_zbid_writeback_permission():
    cases = [
        {"zbid_isolation_status": "isolated_shadow_only"},
        {"zbid_writeback_decision": "isolate_shadow_only"},
    ]
    for overrides in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] in {
            "blocked",
            "not_created",
            "stale_source_hash",
            "stale_source_version",
        }
        assert "zbid_isolation_is_not_writeback_permission" in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_missing_upstream_metadata_is_blocked():
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
    }

    for field, reason in cases.items():
        zbid_guard = build_safe_zbid_guard(**{field: ""})

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


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
        ({"source_hash_guard_status": "stale_source_version"}, "source_hash_guard_not_ready"),
        ({"review_apply_isolation_status": "blocked"}, "review_apply_guard_not_ready"),
        ({"review_apply_isolation_status": "not_created"}, "review_apply_guard_not_ready"),
        ({"review_apply_isolation_status": "stale_source_hash"}, "review_apply_guard_not_ready"),
        (
            {"review_apply_isolation_status": "stale_source_version"},
            "review_apply_guard_not_ready",
        ),
        ({"docx_isolation_status": "blocked"}, "docx_isolation_guard_not_ready"),
        ({"docx_isolation_status": "not_created"}, "docx_isolation_guard_not_ready"),
        ({"docx_isolation_status": "stale_source_hash"}, "docx_isolation_guard_not_ready"),
        ({"docx_isolation_status": "stale_source_version"}, "docx_isolation_guard_not_ready"),
    ]

    for overrides, reason in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_thinking_only_fallback_is_blocked():
    zbid_guard = build_safe_zbid_guard(response_mode="thinking_only_fallback")

    assert zbid_guard["zbid_isolation_status"] == "blocked"
    assert "thinking_only_fallback_not_zbid_writeback_capable" in zbid_guard[
        "blocked_reasons"
    ]
    assert_formal_flags_false(zbid_guard)


def test_missing_evidence_anchor_is_blocked():
    zbid_guard = build_safe_zbid_guard(evidence_anchor_status="missing")

    assert zbid_guard["zbid_isolation_status"] == "blocked"
    assert "missing_evidence_anchor" in zbid_guard["blocked_reasons"]
    assert_formal_flags_false(zbid_guard)


def test_empty_evidence_refs_are_blocked():
    zbid_guard = build_safe_zbid_guard(evidence_anchor_refs=[])

    assert zbid_guard["zbid_isolation_status"] == "blocked"
    assert "missing_evidence_anchor" in zbid_guard["blocked_reasons"]
    assert_formal_flags_false(zbid_guard)


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        zbid_guard = build_safe_zbid_guard(evidence_binding_status=binding_status)

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


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
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] == expected_status
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_zbid_writeback_request_route_payload_candidate_and_mapping_are_blocked():
    cases = [
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        (
            {"zbid_writeback_route": "/actions/zbid/official/writeback"},
            "zbid_writeback_route_blocked",
        ),
        (
            {"zbid_writeback_request_status": "requested_blocked"},
            "zbid_writeback_request_blocked",
        ),
        ({"zbid_writeback_request_status": "route_blocked"}, "zbid_writeback_route_blocked"),
        (
            {"zbid_writeback_request_status": "payload_blocked"},
            "zbid_writeback_payload_blocked",
        ),
        (
            {"zbid_writeback_request_status": "mapping_blocked"},
            "zbid_target_mapping_blocked",
        ),
        ({"zbid_writeback_payload_hash": ""}, "zbid_writeback_payload_blocked"),
        ({"zbid_candidate_hash": ""}, "missing_zbid_candidate_hash"),
        ({"zbid_target_mapping_hash": ""}, "missing_zbid_target_mapping_hash"),
    ]

    for overrides, reason in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_missing_required_hashes_are_blocked():
    cases = {
        "zbid_source_snapshot_hash": "missing_zbid_source_snapshot_hash",
        "docx_candidate_hash": "missing_docx_candidate_hash",
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }

    for field, reason in cases.items():
        zbid_guard = build_safe_zbid_guard(**{field: ""})

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_missing_approval_diff_rollback_formal_source_hash_review_apply_or_docx_is_blocked():
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
    ]

    for overrides, reason in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_docx_output_formal_review_apply_and_zbid_requests_are_blocked():
    cases = [
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
        ({"formal_generation_requested": True}, "formal_generation_request_blocked"),
        ({"review_apply_request_triggered": True}, "review_apply_request_blocked"),
        ({"export_docx_request_triggered": True}, "export_docx_request_blocked"),
        ({"zbid_writeback_request_triggered": True}, "zbid_writeback_request_blocked"),
    ]

    for overrides, reason in cases:
        zbid_guard = build_safe_zbid_guard(**overrides)

        assert zbid_guard["zbid_isolation_status"] == "blocked"
        assert reason in zbid_guard["blocked_reasons"]
        assert_formal_flags_false(zbid_guard)


def test_formal_flags_are_always_false():
    for status in ZBID_ISOLATION_STATUSES:
        zbid_guard = build_safe_zbid_guard(zbid_isolation_status=status)

        assert_formal_flags_false(zbid_guard)


def test_guard_does_not_trigger_zbid_or_call_zbid_interfaces():
    source = helper_source()
    zbid_guard = build_safe_zbid_guard(
        zbid_writeback_route="/fake/zbid-writeback-preview",
        zbid_writeback_payload_hash="sha256:caller-supplied-zbid-payload",
        zbid_candidate_hash="sha256:caller-supplied-zbid-candidate",
        zbid_target_mapping_hash="sha256:caller-supplied-zbid-mapping",
    )

    assert zbid_guard["zbid_writeback_route"] == "/fake/zbid-writeback-preview"
    assert zbid_guard["zbid_writeback_payload_hash"] == (
        "sha256:caller-supplied-zbid-payload"
    )
    assert zbid_guard["zbid_candidate_hash"] == "sha256:caller-supplied-zbid-candidate"
    assert zbid_guard["zbid_target_mapping_hash"] == "sha256:caller-supplied-zbid-mapping"
    assert zbid_guard["zbid_writeback_allowed"] is False
    assert zbid_guard["output_write_allowed"] is False
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
    zbid_guard = build_safe_zbid_guard(generated_at=fixed)
    source = helper_source()

    assert zbid_guard["generated_at"] == fixed
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_zbid_isolation_guard_id_is_deterministic():
    first = build_safe_zbid_guard()
    second = build_safe_zbid_guard()
    changed = build_safe_zbid_guard(zbid_writeback_payload_hash="sha256:changed")
    explicit = build_safe_zbid_guard(zbid_isolation_guard_id="fixed-zbid-isolation-guard-id")

    assert first["zbid_isolation_guard_id"] == second["zbid_isolation_guard_id"]
    assert first["zbid_isolation_guard_id"] != changed["zbid_isolation_guard_id"]
    assert explicit["zbid_isolation_guard_id"] == "fixed-zbid-isolation-guard-id"


def test_importing_helper_does_not_pull_main_chain_or_zbid_modules():
    leaked_modules = MAIN_CHAIN_OR_ZBID_MODULES.intersection(sys.modules)
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
