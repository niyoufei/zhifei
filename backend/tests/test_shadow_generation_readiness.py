from __future__ import annotations

import pytest

from backend.zhifei_autoplan.preview_advisory_quality_gate import evaluate_preview_advisory_quality_gate
from backend.zhifei_autoplan.shadow_generation_readiness import evaluate_shadow_generation_readiness


def _anchored_source() -> dict:
    return {
        "source_type": "tender_document",
        "source_id": "TD-001",
        "title": "测试招标文件",
        "page": "12",
        "clause": "3.2",
        "confidence": 90,
    }


def _base_readiness(**overrides) -> dict:
    payload = {
        "quality_status": "preview_ok",
        "input_risk_status": "clear",
        "evidence_anchor_required": False,
        "evidence_anchor_status": "not_required",
        "evidence_sources": [],
        "generated_preview_as_evidence_detected": False,
        "response_mode": "response_advisory",
        "thinking_fallback_detected": False,
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "formal_generation_allowed": False,
        "shadow_candidate_allowed": False,
        "writeback_allowed": False,
        "export_allowed": False,
        "zbid_writeback_allowed": False,
        "approval_status": "pending",
        "trace_id": "trace-shadow-001",
    }
    payload.update(overrides)
    return payload


def _candidate_ready_base(**overrides) -> dict:
    payload = _base_readiness(
        candidate_id="cand-001",
        candidate_type="section_patch",
        proposed_text="候选建议仅用于 fake-only readiness guard 测试。",
        patch_type="replace_sentence",
        patch_scope="sentence",
        evidence_anchor_required=True,
        evidence_anchor_status="anchored",
        evidence_sources=[_anchored_source()],
        diff_summary="original -> proposed",
        rollback_token="rollback-001",
        rollback_available=True,
        approval_status="approved",
    )
    payload.update(overrides)
    return payload


def _assert_all_formal_flags_false(result: dict) -> None:
    assert result["formal_generation_allowed"] is False
    assert result["shadow_candidate_allowed"] is False
    assert result["candidate_patch_allowed"] is False
    assert result["writeback_allowed"] is False
    assert result["export_allowed"] is False
    assert result["zbid_writeback_allowed"] is False


def test_shadow_readiness_default_is_not_ready_and_formal_ineligible() -> None:
    result = evaluate_shadow_generation_readiness(_base_readiness())

    assert result["shadow_readiness_status"] == "not_ready"
    assert result["shadow_candidate_forbidden"] is False
    assert result["shadow_candidate_reason"] == "shadow_candidate_not_enabled"
    assert result["human_review_required"] is True
    assert result["approval_required"] is True
    assert result["diff_required"] is True
    assert result["rollback_required"] is True
    assert result["evidence_trace_status"] == "not_required"
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize(
    ("field", "value", "expected_blocker"),
    [
        ("quality_status", "blocked", "quality_status:blocked"),
        ("input_risk_status", "blocked", "input_risk_status:blocked"),
    ],
)
def test_shadow_readiness_quality_or_input_risk_blocked_forbids_shadow_candidate(
    field: str,
    value: str,
    expected_blocker: str,
) -> None:
    result = evaluate_shadow_generation_readiness(_base_readiness(**{field: value}))

    assert result["shadow_readiness_status"] == "blocked"
    assert expected_blocker in result["shadow_readiness_blockers"]
    assert result["shadow_candidate_allowed"] is False
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize(
    ("status", "expected_status", "expected_reason"),
    [
        ("missing", "shadow_candidate_forbidden", "evidence_missing_not_shadow_candidate"),
        ("invalid_anchor", "blocked", "evidence_anchor_status:invalid_anchor"),
        ("conflicting", "blocked", "evidence_anchor_status:conflicting"),
        ("system_error", "blocked", "evidence_anchor_status:system_error"),
    ],
)
def test_shadow_readiness_evidence_anchor_statuses_do_not_allow_shadow_candidate(
    status: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    result = evaluate_shadow_generation_readiness(
        _base_readiness(evidence_anchor_required=True, evidence_anchor_status=status)
    )

    assert result["shadow_readiness_status"] == expected_status
    assert expected_reason in result["shadow_readiness_reasons"] + result["shadow_readiness_blockers"]
    assert result["shadow_candidate_allowed"] is False
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_generated_preview_as_evidence_is_blocked() -> None:
    result = evaluate_shadow_generation_readiness(
        _base_readiness(
            evidence_anchor_required=True,
            evidence_anchor_status="invalid_anchor",
            generated_preview_as_evidence_detected=True,
        )
    )

    assert result["shadow_readiness_status"] == "blocked"
    assert "generated_preview_as_evidence" in result["shadow_readiness_blockers"]
    assert "generated_preview_as_evidence" in result["candidate_patch_blockers"]
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize(
    "override",
    [
        {"response_mode": "thinking_only_fallback"},
        {"thinking_fallback_detected": True},
    ],
)
def test_shadow_readiness_thinking_only_fallback_forbids_shadow_candidate(override: dict) -> None:
    result = evaluate_shadow_generation_readiness(_base_readiness(**override))

    assert result["shadow_readiness_status"] == "shadow_candidate_forbidden"
    assert "thinking_only_fallback_not_shadow_candidate" in result["shadow_readiness_reasons"]
    assert "thinking_only_fallback" in result["candidate_patch_blockers"]
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_response_advisory_with_missing_evidence_not_shadow_candidate() -> None:
    result = evaluate_shadow_generation_readiness(
        _base_readiness(
            response_mode="response_advisory",
            evidence_anchor_required=True,
            evidence_anchor_status="missing",
        )
    )

    assert result["shadow_readiness_status"] == "shadow_candidate_forbidden"
    assert "evidence_missing" in result["candidate_patch_blockers"]
    assert result["shadow_candidate_allowed"] is False
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_json_advisory_without_human_approval_has_no_writeback() -> None:
    result = evaluate_shadow_generation_readiness(
        _candidate_ready_base(response_mode="json_advisory", approval_status="pending")
    )

    assert result["shadow_readiness_status"] == "review_required"
    assert "human_approval_required" in result["shadow_readiness_reasons"]
    assert "approval_pending" in result["candidate_patch_blockers"]
    assert result["writeback_allowed"] is False
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_text_fallback_without_rollback_is_blocked() -> None:
    result = evaluate_shadow_generation_readiness(
        _candidate_ready_base(response_mode="text_fallback", rollback_token="", rollback_available=False)
    )

    assert result["shadow_readiness_status"] == "blocked"
    assert "candidate_patch_without_rollback" in result["shadow_readiness_blockers"]
    assert "rollback_token_missing" in result["candidate_patch_blockers"]
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_candidate_patch_without_diff_is_blocked() -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base(diff_summary="", diff_scope=""))

    assert result["shadow_readiness_status"] == "blocked"
    assert "candidate_patch_without_diff" in result["shadow_readiness_blockers"]
    assert "diff_summary_missing" in result["candidate_patch_blockers"]
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_candidate_patch_without_rollback_token_is_blocked() -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base(rollback_token="", rollback_available=False))

    assert result["shadow_readiness_status"] == "blocked"
    assert "candidate_patch_without_rollback" in result["shadow_readiness_blockers"]
    assert result["rollback_available"] is False
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize("approval_status", ["pending", "rejected", "hold"])
def test_shadow_readiness_candidate_patch_without_usable_human_approval_has_no_writeback(
    approval_status: str,
) -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base(approval_status=approval_status))

    assert result["writeback_allowed"] is False
    assert result["candidate_patch_allowed"] is False
    assert f"approval_{approval_status}" in result["candidate_patch_blockers"]
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_revised_approval_requires_new_candidate() -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base(approval_status="revised"))

    assert "approval_revised_requires_new_candidate" in result["candidate_patch_blockers"]
    assert result["writeback_allowed"] is False
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_approved_candidate_still_cannot_export_or_writeback() -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base())

    assert result["approval_status"] == "approved"
    assert result["diff_available"] is True
    assert result["rollback_available"] is True
    assert result["shadow_readiness_status"] == "not_ready"
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_approved_candidate_missing_trace_or_evidence_requires_review() -> None:
    result = evaluate_shadow_generation_readiness(
        _candidate_ready_base(trace_id="", evidence_anchor_status="not_required", evidence_sources=[])
    )

    assert "approved_candidate_missing_trace_id" in result["shadow_readiness_reasons"]
    assert "approved_candidate_missing_evidence_anchor" in result["shadow_readiness_reasons"]
    assert result["writeback_allowed"] is False
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize(
    ("field", "expected_blocker"),
    [
        ("docx_export_requested", "docx_export_from_shadow_candidate_blocked"),
        ("zbid_writeback_requested", "zbid_writeback_from_shadow_candidate_blocked"),
    ],
)
def test_shadow_readiness_docx_or_zbid_attempt_from_shadow_candidate_is_blocked(
    field: str,
    expected_blocker: str,
) -> None:
    result = evaluate_shadow_generation_readiness(_candidate_ready_base(**{field: True}))

    assert result["shadow_readiness_status"] == "blocked"
    assert expected_blocker in result["shadow_readiness_blockers"]
    _assert_all_formal_flags_false(result)


@pytest.mark.parametrize(
    ("field", "value", "expected_blocker"),
    [
        ("no_write", False, "no_write_unsafe"),
        ("preview_only", False, "preview_only_unsafe"),
        ("affects_generation", True, "affects_generation_unsafe"),
        ("affects_export", True, "affects_export_unsafe"),
        ("formal_generation_allowed", True, "formal_generation_allowed_unsafe"),
        ("writeback_allowed", True, "writeback_allowed_unsafe"),
        ("export_allowed", True, "export_allowed_unsafe"),
        ("zbid_writeback_allowed", True, "zbid_writeback_allowed_unsafe"),
    ],
)
def test_shadow_readiness_unsafe_flags_are_blocked(field: str, value: bool, expected_blocker: str) -> None:
    result = evaluate_shadow_generation_readiness(_base_readiness(**{field: value}))

    assert result["shadow_readiness_status"] == "blocked"
    assert expected_blocker in result["shadow_readiness_blockers"]
    _assert_all_formal_flags_false(result)


def test_shadow_readiness_system_error_for_non_object_input() -> None:
    result = evaluate_shadow_generation_readiness(None)

    assert result["shadow_readiness_status"] == "system_error"
    assert "shadow_readiness_input_must_be_object" in result["shadow_readiness_blockers"]
    _assert_all_formal_flags_false(result)


def test_quality_gate_attaches_shadow_readiness_metadata_without_enabling_shadow_candidate() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        {
            "ok": True,
            "status": "ok",
            "preview_only": True,
            "no_write": True,
            "affects_generation": False,
            "affects_export": False,
            "affects_zbid_writeback": False,
            "source": "shadow_readiness_quality_gate_fake",
            "model": "qwen3:0.6b",
            "calls_ollama": False,
            "preview_mode": "text_fallback",
            "content_source": "response",
            "advisory": "建议补充责任岗位、检查频次、整改闭环和资料归档要求。",
            "suggestions": [],
            "risk_notes": ["需资料核验。"],
        },
        context={"section_title": "质量保证措施", "section_text": "质量控制措施：责任到人，按节点验收。"},
    )

    assert gate["quality_status"] in {"preview_ok", "review_required"}
    assert gate["shadow_readiness_status"] in {"not_ready", "review_required", "shadow_candidate_forbidden"}
    assert gate["shadow_readiness"]["shadow_candidate_allowed"] is False
    assert gate["shadow_candidate_allowed"] is False
    assert gate["candidate_patch_allowed"] is False
    assert gate["approval_required"] is True
    assert gate["diff_required"] is True
    assert gate["rollback_required"] is True
    _assert_all_formal_flags_false(gate)
