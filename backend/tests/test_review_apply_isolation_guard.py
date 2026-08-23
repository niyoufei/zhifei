import sys
from pathlib import Path

from backend.zhifei_autoplan import review_apply_isolation_guard as review_apply_guard_module
from backend.zhifei_autoplan.review_apply_isolation_guard import (
    CURRENT_STAGE_EMITTABLE_REVIEW_APPLY_ISOLATION_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_REVIEW_APPLY_ISOLATION_GUARD_FIELDS,
    REVIEW_APPLY_DECISIONS,
    REVIEW_APPLY_ISOLATION_STATUSES,
    REVIEW_APPLY_MODES,
    REVIEW_APPLY_REQUEST_STATUSES,
    REVIEW_APPLY_SCOPES,
    REVIEW_APPLY_TARGET_TYPES,
    build_review_apply_isolation_guard,
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


def build_safe_review_apply_guard(**overrides):
    payload = {
        "request_id": "req-review-apply-guard-001",
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
        "review_apply_decision": "none",
        "review_apply_scope": "single_section",
        "review_apply_mode": "disabled_current_stage",
        "review_apply_target_type": "metadata_only",
        "review_apply_request_status": "not_requested",
        "review_apply_requested": False,
        "review_apply_route": "",
        "review_apply_payload_hash": "sha256:review-apply-payload-preview",
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
        "source_hash_guard_status": "source_hash_matched_shadow_only",
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
    }
    payload.update(overrides)
    return build_review_apply_isolation_guard(**payload)


def helper_source():
    return Path(review_apply_guard_module.__file__).read_text(encoding="utf-8")


def assert_formal_flags_false(review_apply_guard):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert review_apply_guard[flag] is False


def test_review_apply_isolation_guard_contains_required_fields():
    review_apply_guard = build_safe_review_apply_guard()

    assert REQUIRED_REVIEW_APPLY_ISOLATION_GUARD_FIELDS.issubset(review_apply_guard)
    assert review_apply_guard["contract_version"] == "0.1"
    assert review_apply_guard["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(review_apply_guard)


def test_review_apply_status_decision_scope_mode_target_and_request_enums_are_locked():
    assert REVIEW_APPLY_ISOLATION_STATUSES == {
        "not_created",
        "blocked",
        "draft_isolation_shadow_only",
        "isolated_shadow_only",
        "ready_for_future_manual_review",
        "rejected",
        "stale_source_hash",
        "stale_source_version",
    }
    assert REVIEW_APPLY_DECISIONS == {
        "none",
        "block",
        "isolate_shadow_only",
        "require_revision",
        "reject",
    }
    assert REVIEW_APPLY_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert REVIEW_APPLY_MODES == {
        "disabled_current_stage",
        "dry_run_only",
        "future_manual_review",
        "future_guarded_apply",
    }
    assert REVIEW_APPLY_TARGET_TYPES == {
        "source_section",
        "section_draft",
        "patch_preview",
        "metadata_only",
    }
    assert REVIEW_APPLY_REQUEST_STATUSES == {
        "not_requested",
        "requested_blocked",
        "route_blocked",
        "payload_blocked",
        "future_dry_run_only",
    }


def test_helper_only_emits_blocked_not_created_stale_hash_or_stale_version():
    cases = [
        {},
        {"request_id": ""},
        {"source_hash_match": False},
        {"source_version_match": False},
        {"review_apply_isolation_status": "isolated_shadow_only"},
    ]

    for overrides in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] in (
            CURRENT_STAGE_EMITTABLE_REVIEW_APPLY_ISOLATION_STATUSES
        )
        assert review_apply_guard["review_apply_isolation_status"] not in {
            "draft_isolation_shadow_only",
            "isolated_shadow_only",
            "ready_for_future_manual_review",
        }
        assert "real_review_apply_isolation_not_implemented_current_stage" in review_apply_guard[
            "blocked_reasons"
        ]


def test_isolated_shadow_only_is_not_review_apply_permission():
    cases = [
        {"review_apply_isolation_status": "isolated_shadow_only"},
        {"review_apply_decision": "isolate_shadow_only"},
    ]
    for overrides in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] in {
            "blocked",
            "not_created",
            "stale_source_hash",
            "stale_source_version",
        }
        assert "review_apply_isolation_is_not_writeback_permission" in review_apply_guard[
            "blocked_reasons"
        ]
        assert_formal_flags_false(review_apply_guard)


def test_missing_upstream_metadata_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
        "approval_id": ("", "missing_approval_id"),
        "diff_preview_id": ("", "missing_diff_preview_id"),
        "rollback_plan_id": ("", "missing_rollback_plan_id"),
        "writeback_guard_id": ("", "missing_writeback_guard_id"),
        "source_hash_guard_id": ("", "missing_source_hash_guard_id"),
    }
    for field, (value, reason) in cases.items():
        review_apply_guard = build_safe_review_apply_guard(**{field: value})

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


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
    ]

    for overrides, reason in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_thinking_only_fallback_is_blocked():
    review_apply_guard = build_safe_review_apply_guard(response_mode="thinking_only_fallback")

    assert review_apply_guard["review_apply_isolation_status"] == "blocked"
    assert "thinking_only_fallback_not_review_apply_capable" in review_apply_guard[
        "blocked_reasons"
    ]
    assert_formal_flags_false(review_apply_guard)


def test_missing_evidence_anchor_is_blocked():
    review_apply_guard = build_safe_review_apply_guard(evidence_anchor_status="missing")

    assert review_apply_guard["review_apply_isolation_status"] == "blocked"
    assert "missing_evidence_anchor" in review_apply_guard["blocked_reasons"]
    assert_formal_flags_false(review_apply_guard)


def test_empty_evidence_refs_are_blocked():
    review_apply_guard = build_safe_review_apply_guard(evidence_anchor_refs=[])

    assert review_apply_guard["review_apply_isolation_status"] == "blocked"
    assert "missing_evidence_anchor" in review_apply_guard["blocked_reasons"]
    assert_formal_flags_false(review_apply_guard)


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        review_apply_guard = build_safe_review_apply_guard(evidence_binding_status=binding_status)

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_source_hash_or_version_mismatch_is_blocked():
    cases = [
        ({"source_hash_match": False}, "source_hash_mismatch", "stale_source_hash"),
        ({"source_version_match": False}, "source_version_mismatch", "stale_source_version"),
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
        ({"current_source_section_hash": ""}, "missing_current_source_section_hash", "blocked"),
        (
            {"current_source_section_version": ""},
            "missing_current_source_section_version",
            "blocked",
        ),
    ]
    for overrides, reason, expected_status in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] == expected_status
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_missing_required_hashes_are_blocked():
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
        review_apply_guard = build_safe_review_apply_guard(**{field: value})

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_missing_approval_diff_rollback_formal_or_source_hash_guard_is_blocked():
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
    ]
    for overrides, reason in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_review_apply_request_route_or_payload_is_blocked():
    cases = [
        ({"review_apply_requested": True}, "review_apply_request_blocked"),
        ({"review_apply_route": "/review/apply"}, "review_apply_route_blocked"),
        ({"review_apply_request_status": "requested_blocked"}, "review_apply_request_blocked"),
        ({"review_apply_request_status": "route_blocked"}, "review_apply_route_blocked"),
        ({"review_apply_request_status": "payload_blocked"}, "review_apply_payload_blocked"),
        ({"review_apply_payload_hash": ""}, "review_apply_payload_blocked"),
    ]
    for overrides, reason in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_docx_and_zbid_isolation_do_not_open_exports_current_stage():
    cases = [
        ({"docx_isolation_required": True, "docx_isolation_ready": False}, "docx_isolation_missing"),
        ({"zbid_isolation_required": True, "zbid_isolation_ready": False}, "zbid_isolation_missing"),
        ({"docx_isolation_ready": True, "zbid_isolation_ready": True}, None),
    ]
    for overrides, reason in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["docx_export_allowed"] is False
        assert review_apply_guard["zbid_writeback_allowed"] is False
        if reason:
            assert reason in review_apply_guard["blocked_reasons"]


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = [
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
        ({"formal_generation_requested": True}, "formal_generation_request_blocked"),
        ({"review_apply_request_triggered": True}, "review_apply_request_blocked"),
    ]
    for overrides, reason in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert review_apply_guard["review_apply_isolation_status"] == "blocked"
        assert reason in review_apply_guard["blocked_reasons"]
        assert_formal_flags_false(review_apply_guard)


def test_formal_flags_are_always_false():
    cases = [
        {},
        {"request_id": ""},
        {"source_hash_revalidation_status": "stale_source_hash"},
        {"source_version_revalidation_status": "stale_source_version"},
        {"docx_isolation_ready": True, "zbid_isolation_ready": True},
        {"review_apply_decision": "isolate_shadow_only"},
        {"review_apply_isolation_status": "isolated_shadow_only"},
    ]
    for overrides in cases:
        review_apply_guard = build_safe_review_apply_guard(**overrides)

        assert_formal_flags_false(review_apply_guard)


def test_guard_does_not_trigger_review_apply_or_read_real_payload():
    caller_payload_hash = "sha256:caller-supplied-review-apply-payload"
    review_apply_guard = build_safe_review_apply_guard(
        review_apply_payload_hash=caller_payload_hash,
        review_apply_route="/fake/review-apply-preview",
    )
    source = helper_source()

    assert review_apply_guard["review_apply_payload_hash"] == caller_payload_hash
    assert review_apply_guard["review_apply_route"] == "/fake/review-apply-preview"
    assert review_apply_guard["review_apply_allowed"] is False
    assert "open(" not in source
    assert ".read(" not in source
    assert "read_text" not in source
    assert "read_bytes" not in source
    assert "Path(" not in source


def test_generated_at_is_caller_supplied_and_deterministic():
    fixed = "2026-02-02T00:00:00Z"
    review_apply_guard = build_safe_review_apply_guard(generated_at=fixed)
    source = helper_source()

    assert review_apply_guard["generated_at"] == fixed
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "uuid.uuid4" not in source
    assert "random" not in source


def test_review_apply_guard_id_is_deterministic():
    first = build_safe_review_apply_guard()
    second = build_safe_review_apply_guard()
    changed = build_safe_review_apply_guard(review_apply_payload_hash="sha256:changed")
    explicit = build_safe_review_apply_guard(review_apply_guard_id="fixed-review-apply-guard-id")

    assert first["review_apply_guard_id"] == second["review_apply_guard_id"]
    assert first["review_apply_guard_id"] != changed["review_apply_guard_id"]
    assert explicit["review_apply_guard_id"] == "fixed-review-apply-guard-id"


def test_importing_helper_does_not_pull_main_chain_modules(assert_clean_import):
    assert_clean_import(
        "backend.zhifei_autoplan.review_apply_isolation_guard",
        MAIN_CHAIN_MODULES,
    )
    source = helper_source()

    assert "orchestrator" not in source
    assert "llm_client" not in source
    assert "actions_bridge" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "ollama" not in source.lower()
