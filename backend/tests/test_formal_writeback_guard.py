import sys
from pathlib import Path

from backend.zhifei_autoplan.formal_writeback_guard import (
    CURRENT_STAGE_EMITTABLE_WRITEBACK_GUARD_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_WRITEBACK_GUARD_FIELDS,
    SOURCE_HASH_REVALIDATION_STATUSES,
    WRITEBACK_DECISIONS,
    WRITEBACK_GUARD_STATUSES,
    WRITEBACK_MODES,
    WRITEBACK_SCOPES,
    WRITEBACK_TARGET_TYPES,
    build_formal_writeback_guard,
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


def build_safe_writeback_guard(**overrides):
    payload = {
        "request_id": "req-writeback-guard-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "writeback_decision": "none",
        "writeback_scope": "single_section",
        "writeback_mode": "disabled_current_stage",
        "writeback_target_type": "metadata_only",
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
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "source_hash_revalidation_status": "matched",
        "source_section_hash_match": True,
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
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
    return build_formal_writeback_guard(**payload)


def output_job_export_snapshot():
    repo_root = Path(__file__).resolve().parents[2]
    snapshot = {}
    for dirname in ("output", "job", "export"):
        path = repo_root / dirname
        if path.exists():
            snapshot[dirname] = sorted(child.name for child in path.iterdir())
        else:
            snapshot[dirname] = None
    return snapshot


def assert_formal_flags_false(writeback_guard):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert writeback_guard[flag] is False


def test_formal_writeback_guard_contains_required_fields():
    writeback_guard = build_safe_writeback_guard()

    assert REQUIRED_WRITEBACK_GUARD_FIELDS.issubset(writeback_guard)
    assert writeback_guard["contract_version"] == "0.1"
    assert writeback_guard["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(writeback_guard)


def test_writeback_status_decision_scope_mode_target_and_source_hash_enums_are_locked():
    assert WRITEBACK_GUARD_STATUSES == {
        "not_created",
        "blocked",
        "draft_guard_shadow_only",
        "ready_for_final_review",
        "approved_guard_shadow_only",
        "rejected",
        "stale_source_hash",
    }
    assert WRITEBACK_DECISIONS == {
        "none",
        "block",
        "allow_shadow_only",
        "require_revision",
        "reject",
    }
    assert WRITEBACK_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert WRITEBACK_MODES == {
        "disabled_current_stage",
        "dry_run_only",
        "future_manual_apply",
        "future_guarded_apply",
    }
    assert WRITEBACK_TARGET_TYPES == {
        "source_section",
        "section_draft",
        "patch_preview",
        "metadata_only",
    }
    assert SOURCE_HASH_REVALIDATION_STATUSES == {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_hash",
    }


def test_helper_only_emits_blocked_not_created_or_stale_source_hash():
    writeback_guard = build_safe_writeback_guard()

    assert writeback_guard["writeback_guard_status"] in (
        CURRENT_STAGE_EMITTABLE_WRITEBACK_GUARD_STATUSES
    )
    assert writeback_guard["writeback_guard_status"] not in {
        "draft_guard_shadow_only",
        "ready_for_final_review",
        "approved_guard_shadow_only",
    }
    assert "real_formal_writeback_not_implemented_current_stage" in writeback_guard[
        "blocked_reasons"
    ]


def test_approved_guard_shadow_only_is_not_formal_writeback_permission():
    cases = [
        {"writeback_guard_status": "approved_guard_shadow_only"},
        {"writeback_decision": "allow_shadow_only"},
    ]
    for overrides in cases:
        writeback_guard = build_safe_writeback_guard(**overrides)

        assert writeback_guard["writeback_guard_status"] in {
            "blocked",
            "not_created",
            "stale_source_hash",
        }
        assert "guard_is_not_formal_writeback_permission" in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_missing_upstream_metadata_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
        "approval_id": ("", "missing_approval_id"),
        "diff_preview_id": ("", "missing_diff_preview_id"),
        "rollback_plan_id": ("", "missing_rollback_plan_id"),
    }
    for field, (value, reason) in cases.items():
        writeback_guard = build_safe_writeback_guard(**{field: value})

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


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
    ]

    for overrides, reason in cases:
        writeback_guard = build_safe_writeback_guard(**overrides)

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_thinking_only_fallback_is_blocked():
    writeback_guard = build_safe_writeback_guard(response_mode="thinking_only_fallback")

    assert writeback_guard["writeback_guard_status"] == "blocked"
    assert "thinking_only_fallback_not_writeback_capable" in writeback_guard[
        "blocked_reasons"
    ]
    assert_formal_flags_false(writeback_guard)


def test_missing_evidence_anchor_is_blocked():
    writeback_guard = build_safe_writeback_guard(evidence_anchor_status="missing")

    assert writeback_guard["writeback_guard_status"] == "blocked"
    assert "missing_evidence_anchor" in writeback_guard["blocked_reasons"]
    assert_formal_flags_false(writeback_guard)


def test_empty_evidence_refs_are_blocked():
    writeback_guard = build_safe_writeback_guard(evidence_anchor_refs=[])

    assert writeback_guard["writeback_guard_status"] == "blocked"
    assert "missing_evidence_anchor" in writeback_guard["blocked_reasons"]
    assert_formal_flags_false(writeback_guard)


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        writeback_guard = build_safe_writeback_guard(evidence_binding_status=binding_status)

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_missing_or_stale_source_hash_revalidation_is_blocked():
    cases = [
        (
            {"source_section_hash": ""},
            "missing_source_section_hash",
            "blocked",
        ),
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
            "source_hash_revalidation_mismatched",
            "stale_source_hash",
        ),
        (
            {"source_hash_revalidation_status": "stale_source_hash"},
            "stale_source_hash",
            "stale_source_hash",
        ),
        (
            {"source_section_hash_match": False},
            "stale_source_hash",
            "stale_source_hash",
        ),
    ]

    for overrides, reason, expected_status in cases:
        writeback_guard = build_safe_writeback_guard(**overrides)

        assert writeback_guard["writeback_guard_status"] == expected_status
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


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
        writeback_guard = build_safe_writeback_guard(**{field: value})

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_missing_human_approval_diff_rollback_or_review_apply_isolation_is_blocked():
    cases = [
        (
            {"human_approval_required": True, "human_approval_received": False},
            "human_approval_missing",
        ),
        (
            {"diff_preview_required": True, "diff_preview_ready": False},
            "diff_preview_missing",
        ),
        (
            {"rollback_required": True, "rollback_plan_ready": False},
            "rollback_plan_missing",
        ),
        (
            {"review_apply_isolation_required": True, "review_apply_isolation_ready": False},
            "review_apply_isolation_missing",
        ),
    ]

    for overrides, reason in cases:
        writeback_guard = build_safe_writeback_guard(**overrides)

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_docx_and_zbid_isolation_do_not_open_exports_current_stage():
    cases = [
        (
            {"docx_isolation_required": True, "docx_isolation_ready": False},
            "docx_isolation_missing",
        ),
        (
            {"zbid_isolation_required": True, "zbid_isolation_ready": False},
            "zbid_isolation_missing",
        ),
        (
            {"docx_isolation_required": True, "docx_isolation_ready": True},
            None,
        ),
        (
            {"zbid_isolation_required": True, "zbid_isolation_ready": True},
            None,
        ),
    ]

    for overrides, reason in cases:
        writeback_guard = build_safe_writeback_guard(**overrides)

        assert writeback_guard["docx_export_allowed"] is False
        assert writeback_guard["zbid_writeback_allowed"] is False
        if reason:
            assert reason in writeback_guard["blocked_reasons"]


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
    }

    for field, reason in cases.items():
        writeback_guard = build_safe_writeback_guard(**{field: True})

        assert writeback_guard["writeback_guard_status"] == "blocked"
        assert reason in writeback_guard["blocked_reasons"]
        assert_formal_flags_false(writeback_guard)


def test_formal_flags_are_always_false():
    for status in WRITEBACK_GUARD_STATUSES:
        writeback_guard = build_safe_writeback_guard(writeback_guard_status=status)

        assert_formal_flags_false(writeback_guard)


def test_guard_is_not_source_write():
    writeback_guard = build_safe_writeback_guard(
        writeback_guard_status="approved_guard_shadow_only",
        writeback_decision="allow_shadow_only",
        affected_anchor_refs=["section:anchor:1"],
        evidence_anchor_refs=["tender:section:1"],
    )

    assert writeback_guard["source_section_hash_match"] is True
    assert writeback_guard["writeback_decision"] != "review_apply"
    assert writeback_guard["affected_anchor_refs"] != writeback_guard["evidence_anchor_refs"]
    assert "guard_is_not_formal_writeback_permission" in writeback_guard["blocked_reasons"]
    assert_formal_flags_false(writeback_guard)


def test_generated_at_is_caller_supplied_and_deterministic():
    first = build_safe_writeback_guard()
    second = build_safe_writeback_guard()
    fixed_override = "2026-02-02T00:00:00Z"
    changed_time = build_safe_writeback_guard(generated_at=fixed_override)

    assert first["generated_at"] == FIXED_GENERATED_AT
    assert second["generated_at"] == FIXED_GENERATED_AT
    assert changed_time["generated_at"] == fixed_override


def test_writeback_guard_id_is_deterministic():
    first = build_safe_writeback_guard()
    second = build_safe_writeback_guard()
    changed = build_safe_writeback_guard(source_section_hash="sha256:changed-source")

    assert first["writeback_guard_id"] == second["writeback_guard_id"]
    assert first["writeback_guard_id"] != changed["writeback_guard_id"]


def test_importing_helper_does_not_pull_main_chain_modules(assert_clean_import):
    assert_clean_import(
        "backend.zhifei_autoplan.formal_writeback_guard",
        MAIN_CHAIN_MODULES,
    )


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()
    writeback_guard = build_safe_writeback_guard()
    after = output_job_export_snapshot()

    assert before == after
    assert writeback_guard["output_write_allowed"] is False
    assert writeback_guard["formal_writeback_allowed"] is False
