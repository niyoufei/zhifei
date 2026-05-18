import importlib
import sys
from pathlib import Path

from backend.zhifei_autoplan.diff_preview import (
    CURRENT_STAGE_EMITTABLE_DIFF_PREVIEW_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    DIFF_FORMATS,
    DIFF_OPERATION_TYPES,
    DIFF_PREVIEW_STATUSES,
    DIFF_SCOPES,
    REQUIRED_DIFF_PREVIEW_FIELDS,
    build_diff_preview,
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


def build_safe_diff_preview(**overrides):
    payload = {
        "request_id": "req-diff-preview-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_scope": "single_section",
        "diff_format": "structured_diff_preview",
        "diff_operation_type": "replace",
        "diff_summary_preview": "Preview-only diff summary, not formal content.",
        "diff_operations_preview": [{"op": "replace", "anchor_ref": "section:anchor:1"}],
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
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
        "human_approval_required": True,
        "human_approval_received": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "source_section_hash_match": True,
        "diff_base_hash_match": True,
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
    return build_diff_preview(**payload)


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


def assert_formal_flags_false(diff_preview):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert diff_preview[flag] is False


def test_diff_preview_contains_required_fields():
    diff_preview = build_safe_diff_preview()

    assert REQUIRED_DIFF_PREVIEW_FIELDS.issubset(diff_preview)
    assert diff_preview["contract_version"] == "0.1"
    assert diff_preview["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(diff_preview)


def test_diff_preview_status_scope_format_and_operation_enums_are_locked():
    assert DIFF_PREVIEW_STATUSES == {
        "not_created",
        "blocked",
        "draft_diff_shadow_only",
        "ready_for_human_review",
        "approved_diff_shadow_only",
        "rejected",
        "stale_source_hash",
    }
    assert DIFF_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert DIFF_FORMATS == {
        "text_diff_preview",
        "structured_diff_preview",
        "metadata_only",
    }
    assert DIFF_OPERATION_TYPES == {
        "no_op",
        "replace",
        "insert",
        "delete",
        "reorder",
        "mixed",
    }


def test_helper_only_emits_blocked_not_created_or_stale_source_hash():
    diff_preview = build_safe_diff_preview()

    assert diff_preview["diff_preview_status"] in CURRENT_STAGE_EMITTABLE_DIFF_PREVIEW_STATUSES
    assert diff_preview["diff_preview_status"] not in {
        "draft_diff_shadow_only",
        "ready_for_human_review",
        "approved_diff_shadow_only",
    }
    assert "real_diff_not_implemented_current_stage" in diff_preview["blocked_reasons"]


def test_approved_diff_shadow_only_is_not_formal_writeback_permission():
    diff_preview = build_safe_diff_preview(diff_preview_status="approved_diff_shadow_only")

    assert diff_preview["diff_preview_status"] in {"blocked", "not_created", "stale_source_hash"}
    assert "diff_preview_is_not_formal_writeback_permission" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_missing_shadow_patch_or_approval_id_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
        "approval_id": ("", "missing_approval_id"),
    }
    for field, (value, reason) in cases.items():
        diff_preview = build_safe_diff_preview(**{field: value})

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_blocked_shadow_patch_or_unapproved_approval_status_is_blocked():
    cases = [
        (
            {"shadow_candidate_status": "blocked"},
            "shadow_candidate_not_ready",
        ),
        (
            {"shadow_candidate_status": "not_created"},
            "shadow_candidate_not_ready",
        ),
        (
            {"patch_status": "blocked"},
            "patch_not_ready",
        ),
        (
            {"patch_status": "not_created"},
            "patch_not_ready",
        ),
        (
            {"approval_status": "pending_human_review"},
            "approval_not_received",
        ),
    ]

    for overrides, reason in cases:
        diff_preview = build_safe_diff_preview(**overrides)

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_thinking_only_fallback_is_blocked():
    diff_preview = build_safe_diff_preview(response_mode="thinking_only_fallback")

    assert diff_preview["diff_preview_status"] == "blocked"
    assert "thinking_only_fallback_not_diff_capable" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_missing_evidence_anchor_is_blocked():
    diff_preview = build_safe_diff_preview(evidence_anchor_status="missing")

    assert diff_preview["diff_preview_status"] == "blocked"
    assert "missing_evidence_anchor" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_empty_evidence_refs_are_blocked():
    diff_preview = build_safe_diff_preview(evidence_anchor_refs=[])

    assert diff_preview["diff_preview_status"] == "blocked"
    assert "missing_evidence_anchor" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_advisory_shadow_patch_and_diff_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        diff_preview = build_safe_diff_preview(evidence_binding_status=binding_status)

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


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
            {"diff_base_hash_match": False},
            "diff_base_hash_mismatch",
            "stale_source_hash",
        ),
    ]
    for overrides, reason, expected_status in cases:
        diff_preview = build_safe_diff_preview(**overrides)

        assert diff_preview["diff_preview_status"] == expected_status
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_missing_before_after_or_patch_hash_is_blocked():
    cases = {
        "before_text_hash": ("", "missing_before_text_hash"),
        "after_text_preview_hash": ("", "missing_after_text_preview_hash"),
        "patch_operations_preview_hash": ("", "missing_patch_operations_preview_hash"),
    }
    for field, (value, reason) in cases.items():
        diff_preview = build_safe_diff_preview(**{field: value})

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_missing_human_approval_is_blocked():
    diff_preview = build_safe_diff_preview(
        human_approval_required=True,
        human_approval_received=False,
    )

    assert diff_preview["diff_preview_status"] == "blocked"
    assert "human_approval_missing" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_missing_rollback_or_formal_guard_is_blocked():
    cases = [
        (
            {"rollback_required": True, "rollback_plan_ready": False},
            "rollback_plan_missing",
        ),
        (
            {"formal_writeback_guard_required": True, "formal_writeback_guard_ready": False},
            "formal_writeback_guard_missing",
        ),
    ]

    for overrides, reason in cases:
        diff_preview = build_safe_diff_preview(**overrides)

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
    }

    for field, reason in cases.items():
        diff_preview = build_safe_diff_preview(**{field: True})

        assert diff_preview["diff_preview_status"] == "blocked"
        assert reason in diff_preview["blocked_reasons"]
        assert_formal_flags_false(diff_preview)


def test_preview_fields_are_not_evidence():
    diff_summary = "preview summary is not evidence"
    diff_ops = [{"op": "replace", "text": "preview op is not evidence"}]
    diff_preview = build_safe_diff_preview(
        diff_summary_preview=diff_summary,
        diff_operations_preview=diff_ops,
        evidence_anchor_refs=[diff_summary, str(diff_ops)],
    )

    assert diff_preview["diff_preview_status"] == "blocked"
    assert "diff_preview_cannot_be_evidence" in diff_preview["blocked_reasons"]
    assert_formal_flags_false(diff_preview)


def test_formal_flags_are_always_false():
    diff_preview = build_safe_diff_preview(
        docx_export_requested=True,
        zbid_writeback_requested=True,
        output_write_requested=True,
        formal_generation_requested=True,
        review_apply_requested=True,
    )

    assert diff_preview["formal_writeback_allowed"] is False
    assert diff_preview["docx_export_allowed"] is False
    assert diff_preview["zbid_writeback_allowed"] is False
    assert diff_preview["output_write_allowed"] is False


def test_generated_at_is_caller_supplied_and_deterministic():
    diff_preview = build_safe_diff_preview(generated_at=FIXED_GENERATED_AT)

    assert diff_preview["generated_at"] == FIXED_GENERATED_AT
    assert "now" not in diff_preview["generated_at"].lower()


def test_diff_preview_id_is_deterministic():
    first = build_safe_diff_preview()
    second = build_safe_diff_preview()
    different = build_safe_diff_preview(source_section_hash="sha256:other-source-section")

    assert first["diff_preview_id"] == second["diff_preview_id"]
    assert first["diff_preview_id"].startswith("diff-preview-")
    assert first["diff_preview_id"] != different["diff_preview_id"]


def test_importing_helper_does_not_pull_main_chain_modules():
    for module in MAIN_CHAIN_MODULES:
        sys.modules.pop(module, None)

    importlib.import_module("backend.zhifei_autoplan.diff_preview")

    for module in MAIN_CHAIN_MODULES:
        assert module not in sys.modules


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    build_safe_diff_preview(
        output_write_requested=True,
        review_apply_requested=True,
    )

    after = output_job_export_snapshot()
    assert after == before
