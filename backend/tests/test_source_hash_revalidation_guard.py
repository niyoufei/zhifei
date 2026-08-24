import sys
from pathlib import Path

from backend.zhifei_autoplan import source_hash_revalidation_guard as source_hash_guard_module
from backend.zhifei_autoplan.source_hash_revalidation_guard import (
    CURRENT_STAGE_EMITTABLE_SOURCE_HASH_GUARD_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_SOURCE_HASH_REVALIDATION_GUARD_FIELDS,
    REVALIDATION_DECISIONS,
    REVALIDATION_MODES,
    SOURCE_HASH_GUARD_STATUSES,
    SOURCE_HASH_REVALIDATION_STATUSES,
    SOURCE_VERSION_REVALIDATION_STATUSES,
    build_source_hash_revalidation_guard,
)


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
MAIN_CHAIN_MODULES = {
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
}


def build_safe_source_hash_guard(**overrides):
    payload = {
        "request_id": "req-source-hash-guard-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "current_source_section_hash": "sha256:source-section",
        "current_source_section_version": "v1",
        "source_hash_revalidation_status": "matched",
        "source_version_revalidation_status": "matched",
        "source_hash_match": True,
        "source_version_match": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "revalidation_decision": "none",
        "revalidation_mode": "metadata_only",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "writeback_guard_id": "writeback-guard-preview-only",
        "writeback_candidate_hash": "sha256:writeback-candidate",
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
        "rollback_plan_hash": "sha256:rollback-plan",
        "affected_anchor_refs": ["section:anchor:1"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
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
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
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
        "review_apply_requested": False,
    }
    payload.update(overrides)
    return build_source_hash_revalidation_guard(**payload)


def helper_source():
    return Path(source_hash_guard_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(source_hash_guard):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert source_hash_guard[flag] is False


def test_source_hash_revalidation_guard_contains_required_fields():
    source_hash_guard = build_safe_source_hash_guard()

    assert REQUIRED_SOURCE_HASH_REVALIDATION_GUARD_FIELDS.issubset(source_hash_guard)
    assert source_hash_guard["contract_version"] == "0.1"
    assert source_hash_guard["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(source_hash_guard)


def test_source_hash_status_version_status_guard_status_decision_and_mode_enums_are_locked():
    assert SOURCE_HASH_REVALIDATION_STATUSES == {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_hash",
        "blocked",
    }
    assert SOURCE_VERSION_REVALIDATION_STATUSES == {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_version",
        "blocked",
    }
    assert SOURCE_HASH_GUARD_STATUSES == {
        "not_created",
        "blocked",
        "draft_guard_shadow_only",
        "source_hash_matched_shadow_only",
        "stale_source_hash",
        "stale_source_version",
        "rejected",
    }
    assert REVALIDATION_DECISIONS == {
        "none",
        "block",
        "allow_shadow_only",
        "require_refresh",
        "reject",
    }
    assert REVALIDATION_MODES == {
        "disabled_current_stage",
        "metadata_only",
        "future_hash_check",
        "future_guarded_check",
    }


def test_helper_only_emits_blocked_not_created_stale_hash_or_stale_version():
    source_hash_guard = build_safe_source_hash_guard()

    assert source_hash_guard["source_hash_guard_status"] in (
        CURRENT_STAGE_EMITTABLE_SOURCE_HASH_GUARD_STATUSES
    )
    assert source_hash_guard["source_hash_guard_status"] not in {
        "draft_guard_shadow_only",
        "source_hash_matched_shadow_only",
    }
    assert "real_source_hash_revalidation_not_implemented_current_stage" in source_hash_guard[
        "blocked_reasons"
    ]


def test_matched_source_hash_is_not_formal_writeback_permission():
    source_hash_guard = build_safe_source_hash_guard(
        source_hash_revalidation_status="matched",
        source_version_revalidation_status="matched",
        source_hash_match=True,
        source_version_match=True,
        revalidation_decision="allow_shadow_only",
    )

    assert source_hash_guard["source_hash_guard_status"] in {
        "blocked",
        "not_created",
        "stale_source_hash",
        "stale_source_version",
    }
    assert "source_hash_revalidation_is_not_formal_writeback_permission" in source_hash_guard[
        "blocked_reasons"
    ]
    assert_formal_flags_false(source_hash_guard)


def test_missing_upstream_metadata_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
        "approval_id": ("", "missing_approval_id"),
        "diff_preview_id": ("", "missing_diff_preview_id"),
        "rollback_plan_id": ("", "missing_rollback_plan_id"),
        "writeback_guard_id": ("", "missing_writeback_guard_id"),
    }
    for field, (value, reason) in cases.items():
        source_hash_guard = build_safe_source_hash_guard(**{field: value})

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


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
    ]

    for overrides, reason in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_thinking_only_fallback_is_blocked():
    source_hash_guard = build_safe_source_hash_guard(response_mode="thinking_only_fallback")

    assert source_hash_guard["source_hash_guard_status"] == "blocked"
    assert "thinking_only_fallback_not_hash_revalidation_capable" in source_hash_guard[
        "blocked_reasons"
    ]
    assert_formal_flags_false(source_hash_guard)


def test_missing_evidence_anchor_is_blocked():
    source_hash_guard = build_safe_source_hash_guard(evidence_anchor_status="missing")

    assert source_hash_guard["source_hash_guard_status"] == "blocked"
    assert "missing_evidence_anchor" in source_hash_guard["blocked_reasons"]
    assert_formal_flags_false(source_hash_guard)


def test_empty_evidence_refs_are_blocked():
    source_hash_guard = build_safe_source_hash_guard(evidence_anchor_refs=[])

    assert source_hash_guard["source_hash_guard_status"] == "blocked"
    assert "missing_evidence_anchor" in source_hash_guard["blocked_reasons"]
    assert_formal_flags_false(source_hash_guard)


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        source_hash_guard = build_safe_source_hash_guard(evidence_binding_status=binding_status)

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_missing_or_mismatched_source_hash_is_blocked():
    cases = [
        ({"source_section_hash": ""}, "missing_source_section_hash", "blocked"),
        ({"current_source_section_hash": ""}, "missing_current_source_section_hash", "blocked"),
        (
            {"source_hash_revalidation_required": True, "source_hash_revalidation_ready": False},
            "source_hash_revalidation_missing",
            "blocked",
        ),
        (
            {"source_hash_revalidation_status": "missing"},
            "source_hash_revalidation_missing",
            "blocked",
        ),
        (
            {"source_hash_revalidation_status": "mismatched"},
            "source_hash_mismatch",
            "stale_source_hash",
        ),
        (
            {"source_hash_revalidation_status": "stale_source_hash"},
            "stale_source_hash",
            "stale_source_hash",
        ),
        ({"source_hash_match": False}, "source_hash_mismatch", "stale_source_hash"),
        (
            {"current_source_section_hash": "sha256:changed-source-section"},
            "source_hash_mismatch",
            "stale_source_hash",
        ),
    ]

    for overrides, reason, expected_status in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["source_hash_guard_status"] == expected_status
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_missing_or_mismatched_source_version_is_blocked():
    cases = [
        ({"source_section_version": ""}, "missing_source_section_version", "blocked"),
        (
            {"current_source_section_version": ""},
            "missing_current_source_section_version",
            "blocked",
        ),
        (
            {"source_version_revalidation_status": "missing"},
            "source_version_revalidation_missing",
            "blocked",
        ),
        (
            {"source_version_revalidation_status": "mismatched"},
            "source_version_mismatch",
            "stale_source_version",
        ),
        (
            {"source_version_revalidation_status": "stale_source_version"},
            "stale_source_version",
            "stale_source_version",
        ),
        ({"source_version_match": False}, "source_version_mismatch", "stale_source_version"),
        ({"current_source_section_version": "v2"}, "source_version_mismatch", "stale_source_version"),
    ]

    for overrides, reason, expected_status in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["source_hash_guard_status"] == expected_status
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_missing_required_writeback_hashes_are_blocked():
    cases = {
        "writeback_candidate_hash": ("", "missing_writeback_candidate_hash"),
        "source_snapshot_hash": ("", "missing_source_snapshot_hash"),
        "before_text_hash": ("", "missing_before_text_hash"),
        "after_text_preview_hash": ("", "missing_after_text_preview_hash"),
        "patch_operations_preview_hash": ("", "missing_patch_operations_preview_hash"),
        "diff_preview_hash": ("", "missing_diff_preview_hash"),
        "rollback_plan_hash": ("", "missing_rollback_plan_hash"),
    }
    for field, (value, reason) in cases.items():
        source_hash_guard = build_safe_source_hash_guard(**{field: value})

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_missing_approval_diff_rollback_or_formal_guard_is_blocked():
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
    ]
    for overrides, reason in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_missing_review_apply_isolation_is_blocked():
    source_hash_guard = build_safe_source_hash_guard(
        review_apply_isolation_required=True,
        review_apply_isolation_ready=False,
    )

    assert source_hash_guard["source_hash_guard_status"] == "blocked"
    assert "review_apply_isolation_missing" in source_hash_guard["blocked_reasons"]
    assert_formal_flags_false(source_hash_guard)


def test_docx_and_zbid_isolation_do_not_open_exports_current_stage():
    cases = [
        ({"docx_isolation_required": True, "docx_isolation_ready": False}, "docx_isolation_missing"),
        ({"zbid_isolation_required": True, "zbid_isolation_ready": False}, "zbid_isolation_missing"),
        ({"docx_isolation_ready": True, "zbid_isolation_ready": True}, None),
    ]
    for overrides, reason in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["docx_export_allowed"] is False
        assert source_hash_guard["zbid_writeback_allowed"] is False
        if reason:
            assert reason in source_hash_guard["blocked_reasons"]


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = [
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
        ({"formal_generation_requested": True}, "formal_generation_request_blocked"),
        ({"review_apply_requested": True}, "review_apply_request_blocked"),
    ]
    for overrides, reason in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert source_hash_guard["source_hash_guard_status"] == "blocked"
        assert reason in source_hash_guard["blocked_reasons"]
        assert_formal_flags_false(source_hash_guard)


def test_formal_flags_are_always_false():
    cases = [
        {},
        {"request_id": ""},
        {"source_hash_revalidation_status": "stale_source_hash"},
        {"source_version_revalidation_status": "stale_source_version"},
        {"docx_isolation_ready": True, "zbid_isolation_ready": True},
        {"revalidation_decision": "allow_shadow_only"},
    ]
    for overrides in cases:
        source_hash_guard = build_safe_source_hash_guard(**overrides)

        assert_formal_flags_false(source_hash_guard)


def test_guard_does_not_read_real_source_or_compute_real_hash():
    caller_hash = "sha256:caller-supplied-current-section"
    caller_version = "caller-version-001"
    source_hash_guard = build_safe_source_hash_guard(
        current_source_section_hash=caller_hash,
        current_source_section_version=caller_version,
    )
    source = helper_source()

    assert source_hash_guard["current_source_section_hash"] == caller_hash
    assert source_hash_guard["current_source_section_version"] == caller_version
    assert "open(" not in source
    assert ".read(" not in source
    assert "read_text" not in source
    assert "read_bytes" not in source
    assert "Path(" not in source


def test_generated_at_is_caller_supplied_and_deterministic():
    fixed = "2026-02-02T00:00:00Z"
    source_hash_guard = build_safe_source_hash_guard(generated_at=fixed)
    source = helper_source()

    assert source_hash_guard["generated_at"] == fixed
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_source_hash_guard_id_is_deterministic():
    first = build_safe_source_hash_guard()
    second = build_safe_source_hash_guard()
    changed = build_safe_source_hash_guard(current_source_section_hash="sha256:changed")
    explicit = build_safe_source_hash_guard(source_hash_guard_id="fixed-source-hash-guard-id")

    assert first["source_hash_guard_id"] == second["source_hash_guard_id"]
    assert first["source_hash_guard_id"] != changed["source_hash_guard_id"]
    assert explicit["source_hash_guard_id"] == "fixed-source-hash-guard-id"


def test_importing_helper_does_not_pull_main_chain_modules(assert_clean_import):
    assert_clean_import(
        "backend.zhifei_autoplan.source_hash_revalidation_guard",
        MAIN_CHAIN_MODULES,
    )
    source = helper_source()

    assert "orchestrator" not in source
    assert "llm_client" not in source
    assert "actions_bridge" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "ollama" not in source.lower()
