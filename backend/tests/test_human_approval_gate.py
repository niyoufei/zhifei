import importlib
import sys
from pathlib import Path

from backend.zhifei_autoplan.human_approval_gate import (
    APPROVAL_DECISIONS,
    APPROVAL_MODES,
    APPROVAL_SCOPES,
    APPROVAL_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_APPROVAL_FIELDS,
    build_human_approval_gate,
)


FIXED_APPROVED_AT = "2026-01-01T00:00:00Z"
FIXED_APPROVAL_EXPIRES_AT = "2026-01-02T00:00:00Z"
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


def build_safe_approval(**overrides):
    payload = {
        "request_id": "req-human-approval-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_status": "approved_shadow_only",
        "approval_scope": "patch_preview_only",
        "approval_decision": "approve_shadow_only",
        "approval_mode": "manual_received",
        "approver_role": "reviewer",
        "approver_id_placeholder": "manual-reviewer-placeholder",
        "approved_at": FIXED_APPROVED_AT,
        "approval_reason": "fake approval metadata only",
        "approval_comment": "approval is not writeback permission",
        "approval_expires_at": FIXED_APPROVAL_EXPIRES_AT,
        "approval_audit_required": True,
        "approval_audit_ready": True,
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "shadow_candidate_status": "draft_shadow_only",
        "patch_status": "draft_patch_shadow_only",
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
        "docx_export_requested": False,
        "zbid_writeback_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "review_apply_requested": False,
    }
    payload.update(overrides)
    return build_human_approval_gate(**payload)


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


def assert_formal_flags_false(approval):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert approval[flag] is False


def test_human_approval_gate_contains_required_fields():
    approval = build_safe_approval()

    assert REQUIRED_APPROVAL_FIELDS.issubset(approval)
    assert approval["contract_version"] == "0.1"
    assert approval["approved_at"] == FIXED_APPROVED_AT
    assert approval["approval_expires_at"] == FIXED_APPROVAL_EXPIRES_AT
    assert_formal_flags_false(approval)


def test_approval_status_decision_scope_and_mode_enums_are_locked():
    assert APPROVAL_STATUSES == {
        "not_requested",
        "blocked",
        "pending_human_review",
        "approved_shadow_only",
        "rejected",
        "expired",
        "revoked",
    }
    assert APPROVAL_DECISIONS == {
        "none",
        "approve_shadow_only",
        "reject",
        "request_revision",
        "revoke",
    }
    assert APPROVAL_SCOPES == {
        "shadow_candidate_only",
        "patch_preview_only",
        "single_section_candidate",
        "metadata_only",
    }
    assert APPROVAL_MODES == {
        "manual_required",
        "manual_received",
        "disabled_current_stage",
    }


def test_approved_shadow_only_is_not_formal_writeback_permission():
    approval = build_safe_approval(
        approval_status="approved_shadow_only",
        approval_decision="approve_shadow_only",
    )

    assert approval["approval_status"] == "approved_shadow_only"
    assert "approval_is_not_formal_writeback_permission" in approval["blocked_reasons"]
    assert_formal_flags_false(approval)


def test_nonapproved_statuses_block_writeback():
    cases = {
        "not_requested": "approval_not_requested",
        "pending_human_review": "approval_pending_human_review",
        "rejected": "approval_rejected",
        "expired": "approval_expired",
        "revoked": "approval_revoked",
    }

    for status, reason in cases.items():
        approval = build_safe_approval(approval_status=status)

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_missing_shadow_candidate_or_patch_id_is_blocked():
    cases = {
        "shadow_candidate_id": ("", "missing_shadow_candidate_id"),
        "patch_id": ("", "missing_patch_id"),
    }
    for field, (value, reason) in cases.items():
        approval = build_safe_approval(**{field: value})

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_blocked_shadow_candidate_or_patch_status_is_blocked():
    cases = {
        "shadow_candidate_status": ("blocked", "shadow_candidate_not_ready"),
        "shadow_candidate_status_not_created": ("not_created", "shadow_candidate_not_ready"),
        "patch_status": ("blocked", "patch_not_ready"),
        "patch_status_not_created": ("not_created", "patch_not_ready"),
    }
    for key, (value, reason) in cases.items():
        field = "shadow_candidate_status" if key.startswith("shadow_candidate_status") else "patch_status"
        approval = build_safe_approval(**{field: value})

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_thinking_only_fallback_is_blocked():
    approval = build_safe_approval(response_mode="thinking_only_fallback")

    assert approval["approval_status"] == "blocked"
    assert "thinking_only_fallback_not_approvable" in approval["blocked_reasons"]
    assert_formal_flags_false(approval)


def test_missing_evidence_anchor_is_blocked():
    approval = build_safe_approval(evidence_anchor_status="missing")

    assert approval["approval_status"] == "blocked"
    assert "missing_evidence_anchor" in approval["blocked_reasons"]
    assert_formal_flags_false(approval)


def test_empty_evidence_refs_are_blocked():
    approval = build_safe_approval(evidence_anchor_refs=[])

    assert approval["approval_status"] == "blocked"
    assert "missing_evidence_anchor" in approval["blocked_reasons"]
    assert_formal_flags_false(approval)


def test_advisory_shadow_candidate_and_patch_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }
    for binding_status, reason in cases.items():
        approval = build_safe_approval(evidence_binding_status=binding_status)

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_missing_source_hash_or_revalidation_is_blocked():
    cases = [
        (
            {"source_section_hash": ""},
            "missing_source_section_hash",
        ),
        (
            {"source_hash_revalidation_required": True, "source_hash_revalidation_ready": False},
            "source_hash_revalidation_missing",
        ),
    ]

    for overrides, reason in cases:
        approval = build_safe_approval(**overrides)

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_missing_diff_rollback_or_formal_guard_is_blocked():
    cases = [
        (
            {"diff_preview_required": True, "diff_preview_ready": False},
            "diff_preview_missing",
        ),
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
        approval = build_safe_approval(**overrides)

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_missing_approval_audit_is_blocked():
    approval = build_safe_approval(approval_audit_required=True, approval_audit_ready=False)

    assert approval["approval_status"] == "blocked"
    assert "approval_audit_missing" in approval["blocked_reasons"]
    assert_formal_flags_false(approval)

    for field in {
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "shadow_candidate_id",
        "patch_id",
        "approval_decision",
        "approval_scope",
        "approver_role",
    }:
        approval = build_safe_approval(**{field: ""})

        assert approval["approval_status"] == "blocked"
        assert "approval_audit_missing" in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_approver_placeholder_rejects_real_identity():
    for value in {"person@example.com", "13812345678", "110101199003078888", "Zhang San"}:
        approval = build_safe_approval(approver_id_placeholder=value)

        assert approval["approval_status"] == "blocked"
        assert "real_personal_identity_not_allowed" in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_docx_zbid_output_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
    }

    for field, reason in cases.items():
        approval = build_safe_approval(**{field: True})

        assert approval["approval_status"] == "blocked"
        assert reason in approval["blocked_reasons"]
        assert_formal_flags_false(approval)


def test_formal_flags_are_always_false():
    approval = build_safe_approval(
        docx_export_requested=True,
        zbid_writeback_requested=True,
        output_write_requested=True,
        formal_generation_requested=True,
        review_apply_requested=True,
    )

    assert approval["formal_writeback_allowed"] is False
    assert approval["docx_export_allowed"] is False
    assert approval["zbid_writeback_allowed"] is False
    assert approval["output_write_allowed"] is False


def test_timestamps_are_caller_supplied_and_deterministic():
    approval = build_safe_approval(
        approved_at=FIXED_APPROVED_AT,
        approval_expires_at=FIXED_APPROVAL_EXPIRES_AT,
    )

    assert approval["approved_at"] == FIXED_APPROVED_AT
    assert approval["approval_expires_at"] == FIXED_APPROVAL_EXPIRES_AT
    assert "now" not in approval["approved_at"].lower()
    assert "now" not in approval["approval_expires_at"].lower()


def test_approval_id_is_deterministic():
    first = build_safe_approval()
    second = build_safe_approval()
    different = build_safe_approval(source_section_hash="sha256:other-source-section")

    assert first["approval_id"] == second["approval_id"]
    assert first["approval_id"].startswith("approval-")
    assert first["approval_id"] != different["approval_id"]


def test_importing_helper_does_not_pull_main_chain_modules():
    for module in MAIN_CHAIN_MODULES:
        sys.modules.pop(module, None)

    importlib.import_module("backend.zhifei_autoplan.human_approval_gate")

    for module in MAIN_CHAIN_MODULES:
        assert module not in sys.modules


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    build_safe_approval(
        approval_status="pending_human_review",
        output_write_requested=True,
        review_apply_requested=True,
    )

    after = output_job_export_snapshot()
    assert after == before
