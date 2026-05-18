import importlib
import sys
from pathlib import Path

from backend.zhifei_autoplan.shadow_candidate_envelope import (
    CURRENT_STAGE_EMITTABLE_STATUSES,
    CURRENT_STAGE_FORMAL_FLAGS,
    REQUIRED_FIELDS,
    build_shadow_candidate_envelope,
)


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
MAIN_CHAIN_MODULES = {
    "backend.zhifei_autoplan.orchestrator",
    "backend.zhifei_autoplan.llm_client",
    "backend.zhifei_autoplan.provider",
    "backend.app.routers.actions_bridge",
    "backend.app.routers.export",
    "backend.app.routers.review",
    "backend.zhifei_autoplan.zbid_snapshot_mapper",
}


def build_safe_envelope(**overrides):
    payload = {
        "request_id": "req-shadow-envelope-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "candidate_kind": "section_patch_preview",
        "candidate_scope": "section",
        "model_provider": "fake",
        "model_name": "fake-model",
        "generated_at": FIXED_GENERATED_AT,
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_required": True,
        "rollback_required": True,
        "diff_ready": True,
        "rollback_ready": True,
        "docx_export_requested": False,
        "zbid_writeback_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "candidate_text_preview": "",
        "candidate_patch_preview": "",
    }
    payload.update(overrides)
    return build_shadow_candidate_envelope(**payload)


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


def assert_formal_flags_false(envelope):
    for flag in CURRENT_STAGE_FORMAL_FLAGS:
        assert envelope[flag] is False


def test_shadow_candidate_envelope_contains_required_fields():
    envelope = build_safe_envelope()

    assert REQUIRED_FIELDS.issubset(envelope)
    assert envelope["contract_version"] == "0.1"
    assert envelope["generated_at"] == FIXED_GENERATED_AT
    assert_formal_flags_false(envelope)


def test_helper_only_emits_blocked_or_not_created_in_current_stage():
    envelope = build_safe_envelope()

    assert envelope["shadow_candidate_status"] in CURRENT_STAGE_EMITTABLE_STATUSES
    assert envelope["shadow_candidate_status"] not in {
        "draft_shadow_only",
        "ready_for_human_review",
        "approved_shadow_only",
    }
    assert "shadow_generation_not_implemented_current_stage" in envelope["blocked_reasons"]


def test_thinking_only_fallback_is_blocked():
    envelope = build_safe_envelope(response_mode="thinking_only_fallback")

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "thinking_only_fallback_not_candidate_capable" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_generated_advisory_cannot_be_evidence():
    envelope = build_safe_envelope(evidence_anchor_status="generated_advisory_only_blocked")

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "generated_advisory_cannot_be_evidence" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_missing_evidence_anchor_is_blocked():
    envelope = build_safe_envelope(evidence_anchor_status="missing")

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "missing_evidence_anchor" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_empty_evidence_refs_are_blocked():
    envelope = build_safe_envelope(evidence_anchor_refs=[])

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "missing_evidence_anchor" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_missing_human_approval_is_blocked():
    envelope = build_safe_envelope(human_approval_required=True, human_approval_received=False)

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "human_approval_missing" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_missing_diff_or_rollback_readiness_is_blocked():
    envelope = build_safe_envelope(diff_ready=False, rollback_ready=False)

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "diff_not_ready" in envelope["blocked_reasons"]
    assert "rollback_not_ready" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_docx_zbid_output_and_formal_requests_are_blocked():
    cases = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
    }
    for field, reason in cases.items():
        envelope = build_safe_envelope(**{field: True})

        assert envelope["shadow_candidate_status"] == "blocked"
        assert reason in envelope["blocked_reasons"]
        assert_formal_flags_false(envelope)


def test_preview_fields_are_not_evidence():
    text_preview = "preview text is not evidence"
    patch_preview = "preview patch is not evidence"
    envelope = build_safe_envelope(
        candidate_text_preview=text_preview,
        candidate_patch_preview=patch_preview,
        evidence_anchor_refs=[text_preview, patch_preview],
    )

    assert envelope["shadow_candidate_status"] == "blocked"
    assert "shadow_candidate_preview_cannot_be_evidence" in envelope["blocked_reasons"]
    assert_formal_flags_false(envelope)


def test_formal_flags_are_always_false():
    unsafe_envelope = build_safe_envelope(
        docx_export_requested=True,
        zbid_writeback_requested=True,
        output_write_requested=True,
        formal_generation_requested=True,
    )

    assert unsafe_envelope["formal_writeback_allowed"] is False
    assert unsafe_envelope["docx_export_allowed"] is False
    assert unsafe_envelope["zbid_writeback_allowed"] is False
    assert unsafe_envelope["output_write_allowed"] is False


def test_generated_at_is_caller_supplied_and_deterministic():
    envelope = build_safe_envelope(generated_at=FIXED_GENERATED_AT)

    assert envelope["generated_at"] == FIXED_GENERATED_AT
    assert "now" not in envelope["generated_at"].lower()


def test_shadow_candidate_id_is_deterministic():
    first = build_safe_envelope()
    second = build_safe_envelope()
    different = build_safe_envelope(source_section_hash="sha256:other-source-section")

    assert first["shadow_candidate_id"] == second["shadow_candidate_id"]
    assert first["shadow_candidate_id"].startswith("shadow-candidate-")
    assert first["shadow_candidate_id"] != different["shadow_candidate_id"]


def test_importing_helper_does_not_pull_main_chain_modules():
    for module in MAIN_CHAIN_MODULES:
        sys.modules.pop(module, None)

    importlib.import_module("backend.zhifei_autoplan.shadow_candidate_envelope")

    for module in MAIN_CHAIN_MODULES:
        assert module not in sys.modules


def test_helper_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    build_safe_envelope(
        response_mode="thinking_only_fallback",
        docx_export_requested=True,
        output_write_requested=True,
    )

    after = output_job_export_snapshot()
    assert after == before
