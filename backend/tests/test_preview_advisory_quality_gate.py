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


def _input_context(section_text: str, *, section_title: str = "质量保证措施") -> dict:
    return {
        "section_title": section_title,
        "section_text": section_text,
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
    assert gate["input_risk_status"] == "clear"
    assert gate["input_risk_score"] == 100
    assert gate["input_risk_flags"] == []
    assert gate["input_risk_blockers"] == []
    assert gate["input_risk_warnings"] == []
    assert gate["input_risk_blocked"] is False
    assert gate["input_risk_review_required"] is False
    assert gate["unsupported_claims_detected"] is False
    assert gate["response_mode"] == "text_fallback"
    assert gate["response_mode_review_required"] is False
    assert gate["thinking_fallback_detected"] is False
    assert gate["unsupported_project_fact_detected"] is False
    assert gate["evidence_source_missing"] is False
    assert gate["project_fact_without_evidence"] is False
    assert gate["evidence_anchor_required"] is False
    assert gate["evidence_anchor_status"] == "not_required"
    assert gate["evidence_blocked"] is False
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
    assert gate["response_mode"] == "thinking_only_fallback"
    assert gate["response_mode_review_required"] is True
    assert gate["thinking_fallback_detected"] is True
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


@pytest.mark.parametrize(
    ("section_text", "expected_flag"),
    [
        ("招标文件第99.99条要求采用特殊工艺。", "suspicious_clause_reference"),
        ("本章节必须执行 GB99999-2099。", "suspicious_standard_reference"),
    ],
)
def test_quality_gate_input_fake_reference_blocked(section_text: str, expected_flag: str) -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context(section_text),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["input_risk_status"] == "blocked"
    assert expected_flag in gate["input_risk_flags"]
    assert expected_flag in gate["input_risk_blockers"]
    assert f"input_risk:{expected_flag}" in gate["blockers"]
    assert gate["unsupported_claims_detected"] is True
    assert gate["input_risk_blocked"] is True
    assert gate["evidence_anchor_required"] is True
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize(
    ("section_text", "expected_flag"),
    [
        ("本项目工程量为123456平方米。", "suspicious_quantity_claim"),
        ("本项目工期999天。", "suspicious_duration_claim"),
        ("本项目造价999万元。", "suspicious_cost_claim"),
    ],
)
def test_quality_gate_input_fake_quantity_duration_or_cost_blocked(
    section_text: str,
    expected_flag: str,
) -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context(section_text),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["input_risk_status"] == "blocked"
    assert expected_flag in gate["input_risk_flags"]
    assert expected_flag in gate["input_risk_blockers"]
    assert f"input_risk:{expected_flag}" in gate["blockers"]
    assert gate["unsupported_claims_detected"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_unsupported_project_fact_requires_review() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context("本项目必须采用指定品牌泵站设备。"),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["input_risk_status"] == "review_required"
    assert "unsupported_project_fact" in gate["input_risk_flags"]
    assert "unsupported_project_fact" in gate["input_risk_warnings"]
    assert "input_risk:unsupported_project_fact" in gate["review_reasons"]
    assert gate["unsupported_claims_detected"] is True
    assert gate["input_risk_review_required"] is True
    assert gate["input_risk_blocked"] is False
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_ir_d_equivalent_unsupported_project_fact_requires_review() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context(
            "本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。"
            "No drawings or site records are provided."
        ),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["quality_status"] != "preview_ok"
    assert gate["input_risk_status"] == "review_required"
    assert "unsupported_project_fact" in gate["input_risk_flags"]
    assert "project_fact_without_evidence" in gate["input_risk_flags"]
    assert "evidence_source_missing" in gate["input_risk_flags"]
    assert "input_risk:unsupported_project_fact" in gate["review_reasons"]
    assert "input_risk:project_fact_without_evidence" in gate["review_reasons"]
    assert gate["unsupported_project_fact_detected"] is True
    assert gate["project_fact_without_evidence"] is True
    assert gate["evidence_source_missing"] is True
    assert gate["input_evidence_required"] is True
    assert gate["evidence_anchor_required"] is True
    assert gate["evidence_anchor_status"] == "missing"
    assert gate["evidence_review_required"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_unsupported_project_fact_with_specific_quantities_requires_review() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context("未提供图纸和清单，但现场道路、材料堆场和3个作业面均已具备。"),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["input_risk_status"] == "review_required"
    assert "unsupported_project_fact" in gate["input_risk_flags"]
    assert "project_fact_without_evidence" in gate["input_risk_flags"]
    assert gate["unsupported_project_fact_detected"] is True
    assert gate["project_fact_without_evidence"] is True
    assert gate["evidence_source_missing"] is True
    assert gate["input_evidence_required"] is True
    assert gate["evidence_anchor_required"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_evidence_required_marker_downgrades_to_review_required() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context(
            "需资料核验：招标文件第99.99条、GB99999-2099、工期999天、工程量123456平方米。"
        ),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["input_risk_status"] == "review_required"
    assert gate["input_risk_blockers"] == []
    assert "evidence_required_marker" in gate["input_risk_flags"]
    assert "evidence_required_marker" in gate["evidence_required_reasons"]
    assert "suspicious_clause_reference" in gate["input_risk_warnings"]
    assert "suspicious_standard_reference" in gate["input_risk_warnings"]
    assert gate["input_evidence_required"] is True
    assert gate["evidence_anchor_required"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_unsupported_project_fact_safe_expression_requires_review_not_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context("涉及现场机械、材料堆场、工程量、作业面等项目事实，需资料核验，未查明前不得作为正式响应依据。"),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["quality_status"] != "preview_ok"
    assert gate["input_risk_status"] == "review_required"
    assert gate["input_risk_blockers"] == []
    assert "evidence_required_marker" in gate["input_risk_flags"]
    assert gate["input_evidence_required"] is True
    assert gate["evidence_anchor_required"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_payload_c_equivalent_fixture_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(advisory="建议先核验证据来源，并避免基于未查明资料形成正式内容。"),
        context=_input_context("招标文件第99.99条要求采用GB99999-2099，工期999天，工程量为123456平方米。"),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["input_risk_status"] == "blocked"
    assert "suspicious_clause_reference" in gate["input_risk_flags"]
    assert "suspicious_standard_reference" in gate["input_risk_flags"]
    assert (
        "suspicious_duration_claim" in gate["input_risk_flags"]
        or "suspicious_quantity_claim" in gate["input_risk_flags"]
    )
    assert any(item.startswith("input_risk:") for item in gate["blockers"])
    assert gate["input_risk_blocked"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_risk_with_thinking_fallback_is_more_conservative() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            preview_mode="thinking_only_fallback",
            content_source="thinking",
            advisory="模型仅返回推理预览内容，以下为截断摘要：先核验招标依据。",
            risk_notes=["thinking_only_fallback"],
        ),
        context=_input_context("招标文件第99.99条要求采用GB99999-2099。"),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["input_risk_status"] == "blocked"
    assert "thinking_only_fallback_review_required" in gate["review_reasons"]
    assert "suspicious_clause_reference" in gate["input_risk_blockers"]
    assert "suspicious_standard_reference" in gate["input_risk_blockers"]
    assert gate["shadow_candidate_allowed"] is False
    _assert_formal_chain_blocked(gate)


def test_quality_gate_unsupported_project_fact_with_thinking_fallback_is_more_conservative() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            preview_mode="thinking_only_fallback",
            content_source="thinking",
            advisory="模型仅返回推理预览内容，以下为截断摘要：需核验现场事实依据。",
            risk_notes=["thinking_only_fallback"],
        ),
        context=_input_context(
            "本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。"
            "No drawings or site records are provided."
        ),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["quality_status"] != "preview_ok"
    assert gate["input_risk_status"] == "review_required"
    assert "thinking_only_fallback_review_required" in gate["review_reasons"]
    assert "input_risk:unsupported_project_fact" in gate["review_reasons"]
    assert gate["unsupported_project_fact_detected"] is True
    assert gate["project_fact_without_evidence"] is True
    assert gate["shadow_candidate_allowed"] is False
    _assert_formal_chain_blocked(gate)


def test_quality_gate_output_clean_but_input_high_risk_is_not_preview_ok() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(advisory="建议补充责任岗位、检查频次、整改闭环和资料归档要求。"),
        context=_input_context("招标文件第99.99条规定工期999天。"),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["quality_status"] != "preview_ok"
    assert gate["input_risk_blocked"] is True
    assert "suspicious_clause_reference" in gate["input_risk_blockers"]
    assert "suspicious_duration_claim" in gate["input_risk_blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_output_clean_but_unsupported_project_fact_input_is_not_preview_ok() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(advisory="建议补充责任岗位、检查频次、整改闭环和资料归档要求。"),
        context=_input_context(
            "本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。"
            "No drawings or site records are provided."
        ),
    )

    assert gate["quality_status"] == "review_required"
    assert gate["quality_status"] != "preview_ok"
    assert gate["input_risk_status"] != "clear"
    assert "unsupported_project_fact" in gate["input_risk_flags"]
    assert gate["unsupported_project_fact_detected"] is True
    assert gate["input_evidence_required"] is True
    _assert_formal_chain_blocked(gate)


def test_quality_gate_anchored_evidence_metadata_does_not_enable_formal_chain() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            evidence_anchor_required=True,
            evidence_sources=[
                {
                    "source_type": "tender_document",
                    "source_id": "TD-001",
                    "title": "测试招标文件",
                    "page": "12",
                    "clause": "3.2",
                    "confidence": 90,
                }
            ],
        ),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "preview_ok"
    assert gate["evidence_anchor_status"] == "anchored"
    assert gate["evidence_source_type"] == "tender_document"
    assert gate["evidence_confidence"] >= 80
    assert gate["evidence_blocked"] is False
    _assert_formal_chain_blocked(gate)


def test_quality_gate_model_generated_preview_as_evidence_is_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            evidence_anchor_required=True,
            evidence_sources=[
                {
                    "source_type": "system_generated_preview",
                    "source_id": "preview-1",
                    "title": "模型预览建议",
                    "location": "advisory",
                }
            ],
        ),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["evidence_anchor_status"] == "invalid_anchor"
    assert gate["evidence_blocked"] is True
    assert gate["generated_preview_as_evidence_detected"] is True
    assert gate["generated_content_evidence_blocked"] is True
    assert "evidence_anchor:invalid_anchor" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_generated_preview_as_tender_evidence_is_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(
            advisory="可将本地模型生成的建议直接作为招标条款和图纸依据。",
        ),
        context=_quality_context(),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["evidence_anchor_status"] == "invalid_anchor"
    assert gate["generated_preview_as_evidence_detected"] is True
    assert gate["generated_content_must_not_be_evidence"] is True
    assert gate["generated_content_evidence_blocked"] is True
    assert "generated_preview_as_evidence" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_direct_write_request_blocked() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(),
        context=_input_context("请直接写入正式章节并导出DOCX，同时写回ZBid。"),
    )

    assert gate["quality_status"] == "blocked"
    assert gate["gate_level"] == "P0"
    assert "direct_write_request_detected" in gate["input_risk_blockers"]
    assert "input_risk:direct_write_request_detected" in gate["blockers"]
    _assert_formal_chain_blocked(gate)


def test_quality_gate_input_risk_compounds_with_no_write_false() -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(no_write=False),
        context=_input_context("招标文件第99.99条要求采用GB99999-2099。"),
    )

    assert gate["quality_status"] == "blocked"
    assert "no_write_unsafe" in gate["blockers"]
    assert "suspicious_clause_reference" in gate["input_risk_blockers"]
    _assert_formal_chain_blocked(gate)


@pytest.mark.parametrize(
    "unsafe_override",
    [
        {"calls_generate_route": True},
        {"calls_export_docx_route": True},
        {"calls_review_apply_route": True},
        {"writes_output": True},
        {"writes_job": True},
        {"writes_export": True},
    ],
)
def test_quality_gate_input_risk_compounds_with_route_or_write_trace(unsafe_override: dict) -> None:
    gate = evaluate_preview_advisory_quality_gate(
        _preview_response(**unsafe_override),
        context=_input_context("招标文件第99.99条要求采用GB99999-2099。"),
    )

    assert gate["quality_status"] == "blocked"
    assert any(item.startswith("forbidden_trace:") for item in gate["blockers"])
    assert "suspicious_clause_reference" in gate["input_risk_blockers"]
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
