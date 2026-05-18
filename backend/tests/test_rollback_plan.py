import importlib
import sys
from pathlib import Path

from backend.zhifei_autoplan.rollback_plan import (
    CURRENT_STAGE_EMITTABLE_ROLLBACK_PLAN_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_ROLLBACK_PLAN_FIELDS,
    ROLLBACK_OPERATION_TYPES,
    ROLLBACK_PLAN_STATUSES,
    ROLLBACK_SCOPES,
    ROLLBACK_STRATEGIES,
    ROLLBACK_TARGET_TYPES,
    build_rollback_plan,
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


def build_safe_rollback_plan(**overrides):
    payload = {
        "request_id": "req-rollback-plan-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_scope": "single_section",
        "rollback_strategy": "restore_source_snapshot",
        "rollback_operation_type": "restore",
        "rollback_target_type": "source_section",
        "rollback_summary_preview": "Preview-only rollback summary, not executable rollback.",
        "rollback_operations_preview": [{"op": "restore", "anchor_ref": "section:anchor:1"}],
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
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
        "human_approval_required": True,
        "human_approval_received": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "source_section_hash_match": True,
        "rollback_base_hash_match": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
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
    return build_rollback_plan(**payload)


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


def assert_formal_flags_false(rollback_plan):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert rollback_plan[flag] is False


def test_rollback_plan_contains_required_fields():
    rollback_plan = build_safe_rollback_plan()

    assert REQUIRED_ROLLBACK_PLAN_FIELDS.issubset(rollback_plan)
    assert rollback_plan["contract_version"] == "0.1"
    assert rollback_plan["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(rollback_plan)


def test_rollback_status_scope_strategy_operation_and_target_enums_are_locked():
    assert ROLLBACK_PLAN_STATUSES == {
        "not_created",
        "blocked",
        "draft_rollback_shadow_only",
        "ready_for_human_review",
        "approved_rollback_shadow_only",
        "rejected",
        "stale_source_hash",
    }
    assert ROLLBACK_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert ROLLBACK_STRATEGIES == {
        "restore_before_text_hash",
        "reverse_patch_preview",
        "restore_source_snapshot",
        "metadata_only",
        "no_op",
    }
    assert ROLLBACK_OPERATION_TYPES == {
        "no_op",
        "restore",
        "reverse_replace",
        "reverse_insert",
        "reverse_delete",
        "reverse_reorder",
        "mixed",
    }
    assert ROLLBACK_TARGET_TYPES == {
        "source_section",
        "patch_preview",
        "diff_preview",
        "metadata_only",
    }


def test_helper_only_emits_blocked_not_created_or_stale_source_hash():
    rollback_plan = build_safe_rollback_plan()

    assert rollback_plan["rollback_plan_status"] in CURRENT_STAGE_EMITTABLE_ROLLBACK_PLAN_STATUSES
    assert rollback_plan["rollback_plan_status"] not in {
        "draft_rollback_shadow_only",
        "ready_for_human_review",
        "approved_rollback_shadow_only",
    }
    assert "real_rollback_not_implemented_current_stage" in rollback_plan["blocked_reasons"]


def test_approved_rollback_shadow_only_is_not_formal_writeback_permission():
    rollback_plan = build_safe_rollback_plan(
        rollback_plan_status="approved_rollback_shadow_only"
    )

    assert rollback_plan["rollback_plan_status"] in {"blocked", "not_created", "stale_source_hash"}
    assert "rollback_plan_is_not_formal_writeback_permission" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_missing_shadow_patch_approval_or_diff_id_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
        "approval_id": ("", "missing_approval_id"),
        "diff_preview_id": ("", "missing_diff_preview_id"),
    }
    for field, (value, reason) in cases.items():
        rollback_plan = build_safe_rollback_plan(**{field: value})

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_blocked_shadow_patch_approval_or_diff_status_is_blocked():
    cases = [
        ({"shadow_candidate_status": "blocked"}, "shadow_candidate_not_ready"),
        ({"shadow_candidate_status": "not_created"}, "shadow_candidate_not_ready"),
        ({"patch_status": "blocked"}, "patch_not_ready"),
        ({"patch_status": "not_created"}, "patch_not_ready"),
        ({"approval_status": "pending_human_review"}, "approval_not_received"),
        ({"diff_preview_status": "blocked"}, "diff_preview_not_ready"),
        ({"diff_preview_status": "not_created"}, "diff_preview_not_ready"),
        ({"diff_preview_status": "stale_source_hash"}, "diff_preview_not_ready"),
    ]

    for overrides, reason in cases:
        rollback_plan = build_safe_rollback_plan(**overrides)

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_thinking_only_fallback_is_blocked():
    rollback_plan = build_safe_rollback_plan(response_mode="thinking_only_fallback")

    assert rollback_plan["rollback_plan_status"] == "blocked"
    assert "thinking_only_fallback_not_rollback_capable" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_missing_evidence_anchor_is_blocked():
    rollback_plan = build_safe_rollback_plan(evidence_anchor_status="missing")

    assert rollback_plan["rollback_plan_status"] == "blocked"
    assert "missing_evidence_anchor" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_empty_evidence_refs_are_blocked():
    rollback_plan = build_safe_rollback_plan(evidence_anchor_refs=[])

    assert rollback_plan["rollback_plan_status"] == "blocked"
    assert "missing_evidence_anchor" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_advisory_shadow_patch_diff_and_rollback_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        rollback_plan = build_safe_rollback_plan(evidence_binding_status=binding_status)

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_missing_or_stale_source_hash_is_blocked():
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
            {"source_section_hash_match": False},
            "stale_source_hash",
            "stale_source_hash",
        ),
        (
            {"rollback_base_hash_match": False},
            "rollback_base_hash_mismatch",
            "stale_source_hash",
        ),
    ]
    for overrides, reason, expected_status in cases:
        rollback_plan = build_safe_rollback_plan(**overrides)

        assert rollback_plan["rollback_plan_status"] == expected_status
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_missing_required_rollback_hashes_are_blocked():
    cases = {
        "source_snapshot_hash": ("", "missing_source_snapshot_hash"),
        "before_text_hash": ("", "missing_before_text_hash"),
        "after_text_preview_hash": ("", "missing_after_text_preview_hash"),
        "patch_operations_preview_hash": ("", "missing_patch_operations_preview_hash"),
        "diff_preview_hash": ("", "missing_diff_preview_hash"),
    }
    for field, (value, reason) in cases.items():
        rollback_plan = build_safe_rollback_plan(**{field: value})

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_missing_human_approval_or_diff_readiness_is_blocked():
    cases = [
        (
            {"human_approval_required": True, "human_approval_received": False},
            "human_approval_missing",
        ),
        (
            {"diff_preview_required": True, "diff_preview_ready": False},
            "diff_preview_missing",
        ),
    ]

    for overrides, reason in cases:
        rollback_plan = build_safe_rollback_plan(**overrides)

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_missing_formal_writeback_guard_is_blocked():
    rollback_plan = build_safe_rollback_plan(
        formal_writeback_guard_required=True,
        formal_writeback_guard_ready=False,
    )

    assert rollback_plan["rollback_plan_status"] == "blocked"
    assert "formal_writeback_guard_missing" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
    }

    for field, reason in cases.items():
        rollback_plan = build_safe_rollback_plan(**{field: True})

        assert rollback_plan["rollback_plan_status"] == "blocked"
        assert reason in rollback_plan["blocked_reasons"]
        assert_formal_flags_false(rollback_plan)


def test_preview_fields_are_not_evidence():
    rollback_summary = "rollback summary is not evidence"
    rollback_ops = [{"op": "restore", "text": "rollback op is not evidence"}]
    rollback_plan = build_safe_rollback_plan(
        rollback_summary_preview=rollback_summary,
        rollback_operations_preview=rollback_ops,
        evidence_anchor_refs=[rollback_summary, str(rollback_ops)],
    )

    assert rollback_plan["rollback_plan_status"] == "blocked"
    assert "rollback_plan_cannot_be_evidence" in rollback_plan["blocked_reasons"]
    assert_formal_flags_false(rollback_plan)


def test_formal_flags_are_always_false():
    rollback_plan = build_safe_rollback_plan(
        docx_export_requested=True,
        zbid_writeback_requested=True,
        output_write_requested=True,
        formal_generation_requested=True,
        review_apply_requested=True,
    )

    assert rollback_plan["formal_writeback_allowed"] is False
    assert rollback_plan["docx_export_allowed"] is False
    assert rollback_plan["zbid_writeback_allowed"] is False
    assert rollback_plan["output_write_allowed"] is False


def test_generated_at_is_caller_supplied_and_deterministic():
    rollback_plan = build_safe_rollback_plan(generated_at=FIXED_GENERATED_AT)

    assert rollback_plan["generated_at"] == FIXED_GENERATED_AT
    assert "now" not in rollback_plan["generated_at"].lower()


def test_rollback_plan_id_is_deterministic():
    first = build_safe_rollback_plan()
    second = build_safe_rollback_plan()
    different = build_safe_rollback_plan(source_snapshot_hash="sha256:other-source-snapshot")

    assert first["rollback_plan_id"] == second["rollback_plan_id"]
    assert first["rollback_plan_id"].startswith("rollback-plan-")
    assert first["rollback_plan_id"] != different["rollback_plan_id"]


def test_importing_helper_does_not_pull_main_chain_modules():
    for module in MAIN_CHAIN_MODULES:
        sys.modules.pop(module, None)

    importlib.import_module("backend.zhifei_autoplan.rollback_plan")

    for module in MAIN_CHAIN_MODULES:
        assert module not in sys.modules


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    build_safe_rollback_plan(
        output_write_requested=True,
        review_apply_requested=True,
    )

    after = output_job_export_snapshot()
    assert after == before
