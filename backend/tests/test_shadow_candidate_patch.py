import importlib
import sys
from pathlib import Path

from backend.zhifei_autoplan.shadow_candidate_patch import (
    CURRENT_STAGE_EMITTABLE_PATCH_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_PATCH_FIELDS,
    build_shadow_candidate_patch,
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


def build_safe_patch(**overrides):
    payload = {
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "request_id": "req-shadow-patch-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "patch_kind": "paragraph_rewrite",
        "patch_scope": "paragraph",
        "patch_format": "structured_patch_preview",
        "patch_operation_type": "replace",
        "patch_operations_preview": [{"op": "replace", "anchor_ref": "tender:section:1"}],
        "before_text_hash": "sha256:before-text",
        "after_text_preview": "Preview-only after text, not formal content.",
        "affected_anchor_refs": ["section:anchor:1"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "shadow_candidate_status": "draft_shadow_only",
        "generated_at": FIXED_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "source_section_hash_match": True,
        "docx_export_requested": False,
        "zbid_writeback_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "review_apply_requested": False,
    }
    payload.update(overrides)
    return build_shadow_candidate_patch(**payload)


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


def assert_formal_flags_false(patch):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert patch[flag] is False


def test_shadow_candidate_patch_contains_required_fields():
    patch = build_safe_patch()

    assert REQUIRED_PATCH_FIELDS.issubset(patch)
    assert patch["contract_version"] == "0.1"
    assert patch["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(patch)


def test_helper_only_emits_blocked_or_not_created_in_current_stage():
    patch = build_safe_patch()

    assert patch["patch_status"] in CURRENT_STAGE_EMITTABLE_PATCH_STATUSES
    assert patch["patch_status"] not in {
        "draft_patch_shadow_only",
        "ready_for_human_review",
        "approved_patch_shadow_only",
    }
    assert "real_candidate_patch_not_implemented_current_stage" in patch["blocked_reasons"]


def test_missing_shadow_candidate_id_is_blocked():
    patch = build_safe_patch(shadow_candidate_id="")

    assert patch["patch_status"] == "blocked"
    assert "missing_shadow_candidate_id" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_blocked_or_not_created_shadow_candidate_blocks_patch():
    for status in {"blocked", "not_created"}:
        patch = build_safe_patch(shadow_candidate_status=status)

        assert patch["patch_status"] == "blocked"
        assert "shadow_candidate_not_ready" in patch["blocked_reasons"]
        assert_formal_flags_false(patch)


def test_thinking_only_fallback_is_blocked():
    patch = build_safe_patch(response_mode="thinking_only_fallback")

    assert patch["patch_status"] == "blocked"
    assert "thinking_only_fallback_not_patch_capable" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_missing_evidence_anchor_is_blocked():
    patch = build_safe_patch(evidence_anchor_status="missing")

    assert patch["patch_status"] == "blocked"
    assert "missing_evidence_anchor" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_empty_evidence_refs_are_blocked():
    patch = build_safe_patch(evidence_anchor_refs=[])

    assert patch["patch_status"] == "blocked"
    assert "missing_evidence_anchor" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_advisory_shadow_candidate_and_patch_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        patch = build_safe_patch(evidence_binding_status=binding_status)

        assert patch["patch_status"] == "blocked"
        assert reason in patch["blocked_reasons"]
        assert_formal_flags_false(patch)


def test_missing_or_mismatched_source_hash_is_blocked():
    cases = {
        "source_section_hash": ("", "missing_source_section_hash"),
        "source_section_hash_match": (False, "source_section_hash_mismatch"),
    }
    for field, (value, reason) in cases.items():
        patch = build_safe_patch(**{field: value})

        assert patch["patch_status"] == "blocked"
        assert reason in patch["blocked_reasons"]
        assert_formal_flags_false(patch)


def test_missing_before_text_hash_is_blocked():
    patch = build_safe_patch(before_text_hash="")

    assert patch["patch_status"] == "blocked"
    assert "missing_before_text_hash" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_missing_human_approval_is_blocked():
    patch = build_safe_patch(human_approval_required=True, human_approval_received=False)

    assert patch["patch_status"] == "blocked"
    assert "human_approval_missing" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_missing_diff_or_rollback_readiness_is_blocked():
    patch = build_safe_patch(diff_preview_ready=False, rollback_plan_ready=False)

    assert patch["patch_status"] == "blocked"
    assert "diff_preview_missing" in patch["blocked_reasons"]
    assert "rollback_plan_missing" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
    }

    for field, reason in cases.items():
        patch = build_safe_patch(**{field: True})

        assert patch["patch_status"] == "blocked"
        assert reason in patch["blocked_reasons"]
        assert_formal_flags_false(patch)


def test_preview_fields_are_not_evidence():
    patch_preview = [{"op": "replace", "text": "preview-only"}]
    after_preview = "preview-only after text"
    patch = build_safe_patch(
        patch_operations_preview=patch_preview,
        after_text_preview=after_preview,
        evidence_anchor_refs=[str(patch_preview), after_preview],
    )

    assert patch["patch_status"] == "blocked"
    assert "patch_preview_cannot_be_evidence" in patch["blocked_reasons"]
    assert_formal_flags_false(patch)


def test_formal_flags_are_always_false():
    patch = build_safe_patch(
        docx_export_requested=True,
        zbid_writeback_requested=True,
        output_write_requested=True,
        formal_generation_requested=True,
        review_apply_requested=True,
    )

    assert patch["formal_writeback_allowed"] is False
    assert patch["docx_export_allowed"] is False
    assert patch["zbid_writeback_allowed"] is False
    assert patch["output_write_allowed"] is False


def test_generated_at_is_caller_supplied_and_deterministic():
    patch = build_safe_patch(generated_at=FIXED_GENERATED_AT)

    assert patch["generated_at"] == FIXED_GENERATED_AT
    assert "now" not in patch["generated_at"].lower()


def test_patch_id_is_deterministic():
    first = build_safe_patch()
    second = build_safe_patch()
    different = build_safe_patch(source_section_hash="sha256:other-source-section")

    assert first["patch_id"] == second["patch_id"]
    assert first["patch_id"].startswith("patch-")
    assert first["patch_id"] != different["patch_id"]


def test_importing_helper_does_not_pull_main_chain_modules():
    for module in MAIN_CHAIN_MODULES:
        sys.modules.pop(module, None)

    importlib.import_module("backend.zhifei_autoplan.shadow_candidate_patch")

    for module in MAIN_CHAIN_MODULES:
        assert module not in sys.modules


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    build_safe_patch(
        response_mode="thinking_only_fallback",
        docx_export_requested=True,
        output_write_requested=True,
    )

    after = output_job_export_snapshot()
    assert after == before
