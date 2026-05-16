from __future__ import annotations

import copy

import pytest

import backend.zhifei_autoplan.preview_advisory_quality_gate as quality_gate_module
from backend.zhifei_autoplan.preview_advisory_quality_gate import (
    attach_preview_advisory_quality_gate,
    evaluate_preview_advisory_quality_gate,
)


def _quality_context() -> dict:
    return {
        "section_title": "质量保证措施",
        "section_text": "质量控制措施：责任到人，按节点验收。",
    }


def _preview_response(**overrides) -> dict:
    response = {
        "ok": True,
        "status": "ok",
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "source": "quality_gate_unit_fake",
        "model": "qwen3:0.6b",
        "calls_ollama": True,
        "preview_mode": "text_fallback",
        "content_source": "response",
        "advisory": (
            "质量保证措施应补充检验批验收频次、责任岗位、整改闭环和资料归档要求，"
            "明确每周检查一次并形成验收记录。"
        ),
        "suggestions": ["补充检验批验收频次。", "明确责任岗位。"],
        "risk_notes": ["需资料核验。"],
        "calls_generate_route": False,
        "calls_export_docx_route": False,
        "calls_review_apply_route": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "triggers_zbid_writeback": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
    }
    response.update(overrides)
    return response


def _assert_formal_chain_blocked(gate: dict) -> None:
    assert gate["formal_ineligible"] is True
    assert gate["formal_generation_allowed"] is False
    assert gate["shadow_candidate_allowed"] is False
    assert gate["writeback_allowed"] is False
    assert gate["export_allowed"] is False
    assert gate["zbid_writeback_allowed"] is False


def test_quality_gate_high_quality_advisory_preview_ok_but_formal_ineligible() -> None:
    gate = evaluate_preview_advisory_quality_gate(_preview_response(), context=_quality_context())

    assert gate["quality_status"] == "preview_ok"
    assert gate["quality_score"] >= 70
    assert gate["blockers"] == []
    assert gate["review_reasons"] == []
    assert gate["advisory_length"] > 0
    assert gate["suggestions_count"] == 2
    assert gate["risk_notes_count"] == 1
    assert "preview_only_guard" in gate["passed_checks"]
    assert "formal_replacement_guard" in gate["passed_checks"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_empty_advisory_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(_preview_response(advisory=""), context=_quality_context())

    assert gate["quality_status"] == "blocked"
    assert "empty_advisory" in gate["blockers"]
    assert "advisory_present" in gate["failed_checks"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_vague_template_advisory_requires_review() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(advisory="加强管理，严格控制，确保质量。", suggestions=[]),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "review_required"
    assert "vague_advisory" in gate["review_reasons"]
    assert "specificity_guard" in gate["failed_checks"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_thinking_only_fallback_is_review_required_and_not_shadow_candidate() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            preview_mode="thinking_only_fallback",
            content_source="thinking",
            advisory="模型仅返回推理预览内容，以下为截断摘要：需补充质量检查记录。",
            risk_notes=["thinking_only_fallback"],
        ),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "review_required"
    assert "thinking_only_fallback_review_required" in gate["review_reasons"]
    assert "thinking_only_fallback" in gate["warnings"]
    assert gate["shadow_candidate_allowed"] is False
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize(
    "advisory",
    [
        "招标文件第3.2条明确要求本章必须写入该措施。",
        "应按 GB 50010-9999 条文执行并承诺工期 120 日历天。",
        "本项目工程量为 10000 平方米，费用为 500 万元。",
    ],
)
def test_quality_gate_hallucinated_clause_or_engineering_parameter_blocked(advisory: str) -> None:
    gate = evaluate_preview_advisory_quality_gate(_preview_response(advisory=advisory), context=_quality_context())

    assert gate["quality_status"] == "blocked"
    assert "hallucination_risk" in gate["blockers"]
    assert "evidence_safety_guard" in gate["failed_checks"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_long_advisory_warns_and_requires_review() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(advisory="质量验收记录。" * 500),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["advisory_length"] > 1200
    assert "advisory_over_limit" in gate["warnings"]
    assert "advisory_length_review_required" in gate["review_reasons"]
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("no_write", False, "no_write_unsafe"),
        ("affects_generation", True, "affects_generation_unsafe"),
        ("affects_export", True, "affects_export_unsafe"),
        ("preview_only", False, "preview_only_unsafe"),
    ],
)
def test_quality_gate_p0_safety_field_anomaly_blocked(field: str, value: bool, blocker: str) -> None:
    gate = evaluate_preview_advisory_quality_gate(_preview_response(**{field: value}), context=_quality_context())

    assert gate["quality_status"] == "blocked"
    assert blocker in gate["blockers"]
    assert gate["gate_level"] == "P0"
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize("missing_field", ["source", "model", "preview_mode", "content_source"])
def test_quality_gate_missing_trace_field_requires_review(missing_field: str) -> None:
    response = _preview_response()
    response.pop(missing_field)

    gate = evaluate_preview_advisory_quality_gate(response, context=_quality_context())

    assert gate["quality_status"] == "review_required"
    expected = "missing_response_source" if missing_field == "content_source" else f"missing_{missing_field}"
    assert expected in gate["review_reasons"]
    assert gate["shadow_candidate_allowed"] is False
    _assert_formal_chain_blocked(gate)


def test_quality_gate_suggestions_over_limit_truncates_count_and_warns() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(suggestions=["一", "二", "三", "四"]),
        context=_quality_context(),
    )

    assert gate["suggestions_count"] == 3
    assert "suggestions_truncated" in gate["warnings"]
    assert "suggestions_count_limit" in gate["failed_checks"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_risk_notes_over_limit_truncates_count_and_warns() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(risk_notes=["一", "二", "三", "四"]),
        context=_quality_context(),
    )

    assert gate["risk_notes_count"] == 3
    assert "risk_notes_truncated" in gate["warnings"]
    assert "risk_notes_count_limit" in gate["failed_checks"]
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize(
    "unsafe_override",
    [
        {"writes_output": True},
        {"writes_job": True},
        {"writes_export": True},
        {"calls_generate_route": True},
        {"calls_export_docx_route": True},
        {"calls_review_apply_route": True},
        {"called_routes": ["/generate"]},
        {"route_triggers": {"path": "/review/apply"}},
    ],
)
def test_quality_gate_output_write_or_forbidden_route_trace_blocked(unsafe_override: dict) -> None:
    gate = evaluate_preview_advisory_quality_gate(_preview_response(**unsafe_override), context=_quality_context())

    assert gate["quality_status"] == "blocked"
    assert gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_formal_result_field_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(content="正式正文内容"),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "blocked"
    assert "formal_result_field:content" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_status_ok_does_not_override_blocked_quality() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(status="ok", no_write=False),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "blocked"
    assert "no_write_unsafe" in gate["blockers"]
    assert gate["formal_generation_allowed"] is False


def test_quality_gate_system_error_for_non_object_input() -> None:
    gate = evaluate_preview_advisory_quality_gate(None)

    assert gate["quality_status"] == "system_error"
    assert "quality_gate_input_must_be_object" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_system_error_for_internal_exception(monkeypatch) -> None:
    def fail_evaluate(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(quality_gate_module, "_evaluate_preview_advisory_quality_gate", fail_evaluate)

    gate = quality_gate_module.evaluate_preview_advisory_quality_gate(_preview_response())

    assert gate["quality_status"] == "system_error"
    assert "quality_gate_exception" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_attach_quality_gate_adds_metadata_without_mutating_preview() -> None:
    response = _preview_response()
    original = copy.deepcopy(response)

    enriched = attach_preview_advisory_quality_gate(response, context=_quality_context())

    assert response == original
    assert enriched["quality_gate"]["quality_status"] == "preview_ok"
    assert enriched["quality_status"] == "preview_ok"
    assert enriched["quality_score"] == enriched["quality_gate"]["quality_score"]
    assert enriched["formal_generation_allowed"] is False
    assert enriched["shadow_candidate_allowed"] is False
    assert enriched["writeback_allowed"] is False
    assert enriched["export_allowed"] is False
    assert enriched["zbid_writeback_allowed"] is False
