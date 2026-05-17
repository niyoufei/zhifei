from __future__ import annotations

import pytest

import backend.zhifei_autoplan.evidence_anchor as evidence_anchor_module
from backend.zhifei_autoplan.evidence_anchor import evaluate_evidence_anchor


def _assert_formal_chain_blocked(result: dict) -> None:
    assert result["formal_generation_allowed"] is False
    assert result["shadow_candidate_allowed"] is False
    assert result["writeback_allowed"] is False
    assert result["export_allowed"] is False
    assert result["zbid_writeback_allowed"] is False


def _strong_source(source_type: str = "tender_document") -> dict:
    return {
        "source_type": source_type,
        "source_id": f"{source_type}-001",
        "title": "测试招标资料",
        "page": "12",
        "clause": "3.2",
        "quote_excerpt": "质量目标按招标文件第三章执行。",
        "confidence": 88,
    }


@pytest.mark.parametrize(
    "source_type",
    [
        "tender_document",
        "tender_addendum",
        "scoring_criteria",
        "drawing",
        "boq",
        "site_survey",
        "photos",
        "contract_or_owner_requirement",
        "standard_or_code",
    ],
)
def test_evidence_anchor_strong_source_types_can_be_anchored(source_type: str) -> None:
    source = _strong_source(source_type)
    if source_type == "standard_or_code":
        source["source_id"] = "GB50010-2010"
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "claim_text": "招标文件第3.2条要求质量目标达标。",
            "evidence_sources": [source],
        }
    )

    assert result["evidence_anchor_status"] == "anchored"
    assert result["evidence_anchor_required"] is True
    assert result["evidence_source_type"] == source_type
    assert result["evidence_confidence"] >= 80
    assert result["evidence_blocked"] is False
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_anchored_drawing_and_boq_fixture() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "claim_text": "图纸和工程量清单显示本段需复核材料数量。",
            "evidence_sources": [
                {
                    "source_type": "drawing",
                    "source_id": "DWG-A-01",
                    "title": "总平面布置图",
                    "location": "图号 A-01",
                },
                {
                    "source_type": "boq",
                    "source_id": "BOQ-001",
                    "title": "工程量清单",
                    "page": "8",
                },
            ],
        }
    )

    assert result["evidence_anchor_status"] == "anchored"
    assert len(result["evidence_sources"]) == 2
    assert result["evidence_blocked"] is False
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_missing_evidence_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "claim_text": "招标文件第3.2条要求工期为120日历天。",
            "evidence_sources": [],
        }
    )

    assert result["evidence_anchor_required"] is True
    assert result["evidence_anchor_status"] == "missing"
    assert result["evidence_review_required"] is True
    assert "evidence_source_missing" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_invalid_source_type_is_blocked() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "evidence_sources": [{"source_type": "made_up_source", "source_id": "X-1"}],
        }
    )

    assert result["evidence_anchor_status"] == "invalid_anchor"
    assert result["evidence_blocked"] is True
    assert "invalid_evidence_source_type" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_model_generated_preview_as_evidence_is_blocked() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "evidence_sources": [
                {
                    "source_type": "system_generated_preview",
                    "source_id": "preview-1",
                    "title": "模型预览建议",
                    "location": "advisory",
                }
            ],
        }
    )

    assert result["evidence_anchor_status"] == "invalid_anchor"
    assert result["evidence_blocked"] is True
    assert "model_generated_preview_as_evidence" in result["evidence_missing_reasons"]
    assert result["generated_content_must_not_be_evidence"] is True
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_unknown_or_unverified_source_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "evidence_sources": [{"source_type": "unknown_or_unverified", "title": "未查明来源"}],
        }
    )

    assert result["evidence_anchor_status"] == "unverified"
    assert result["evidence_review_required"] is True
    assert "unknown_or_unverified_source" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_user_context_is_partial_not_strong_anchor() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "evidence_sources": [{"source_type": "user_provided_context", "title": "用户输入"}],
        }
    )

    assert result["evidence_anchor_status"] == "partially_anchored"
    assert result["evidence_review_required"] is True
    assert "user_context_requires_verification" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_standard_without_version_or_source_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "claim_text": "应执行相关规范标准。",
            "evidence_sources": [{"source_type": "standard_or_code", "title": "相关规范"}],
        }
    )

    assert result["evidence_anchor_status"] == "partially_anchored"
    assert result["evidence_review_required"] is True
    assert "standard_or_code_missing_version_or_source" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_unsupported_project_fact_with_missing_evidence_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "claim_text": "本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。",
            "unsupported_project_facts": ["现场已有3台塔吊"],
        }
    )

    assert result["evidence_anchor_required"] is True
    assert result["evidence_anchor_status"] == "missing"
    assert result["unsupported_project_facts"] == ["现场已有3台塔吊"]
    assert result["evidence_review_required"] is True
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_safe_expression_with_evidence_required_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "claim_text": "涉及工期、工程量、规范条款需资料核验，未查明前不得作为正式响应依据。",
            "unverified_parameters": ["需资料核验"],
        }
    )

    assert result["evidence_anchor_status"] == "missing"
    assert result["evidence_review_required"] is True
    assert result["unverified_parameters"] == ["需资料核验"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_conflicting_evidence_is_blocked() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "conflicting_evidence": True,
            "evidence_sources": [_strong_source("tender_document"), _strong_source("tender_addendum")],
        }
    )

    assert result["evidence_anchor_status"] == "conflicting"
    assert result["evidence_blocked"] is True
    assert "conflicting_evidence" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_anchored_advisory_keeps_formal_flags_false() -> None:
    result = evaluate_evidence_anchor(
        {
            "evidence_anchor_required": True,
            "claim_text": "招标文件第3.2条要求质量目标达标。",
            "evidence_sources": [_strong_source("tender_document")],
        }
    )

    assert result["evidence_anchor_status"] == "anchored"
    assert result["evidence_blocked"] is False
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_thinking_fallback_with_factual_claim_requires_review() -> None:
    result = evaluate_evidence_anchor(
        {
            "preview_mode": "thinking_only_fallback",
            "claim_text": "招标文件第3.2条要求本项目工期为120日历天。",
        }
    )

    assert result["evidence_anchor_required"] is True
    assert result["evidence_anchor_status"] == "missing"
    assert result["evidence_review_required"] is True
    assert "thinking_fallback_factual_claim" in result["unverified_parameters"]
    _assert_formal_chain_blocked(result)


@pytest.mark.parametrize(
    "field",
    ["zbid_writeback_attempted", "docx_export_attempted", "candidate_patch_attempted"],
)
def test_evidence_anchor_formal_chain_attempt_without_evidence_blocked(field: str) -> None:
    result = evaluate_evidence_anchor({field: True})

    assert result["evidence_anchor_status"] == "invalid_anchor"
    assert result["evidence_blocked"] is True
    assert "formal_chain_attempt_without_evidence" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_required_with_no_source_review_or_blocked() -> None:
    result = evaluate_evidence_anchor({"evidence_anchor_required": True})

    assert result["evidence_anchor_status"] in {"missing", "invalid_anchor"}
    assert result["evidence_anchor_required"] is True
    assert result["shadow_candidate_allowed"] is False
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_high_quality_advisory_without_facts_not_required() -> None:
    result = evaluate_evidence_anchor(
        {
            "advisory": "建议优化章节结构，补充资料核验提醒，并由人工确认后再采纳。",
        }
    )

    assert result["evidence_anchor_status"] == "not_required"
    assert result["evidence_anchor_required"] is False
    assert result["evidence_blocked"] is False
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_system_error_for_non_object_input() -> None:
    result = evaluate_evidence_anchor(None)

    assert result["evidence_anchor_status"] == "system_error"
    assert result["evidence_blocked"] is True
    assert "evidence_anchor_input_must_be_object" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)


def test_evidence_anchor_system_error_for_internal_exception(monkeypatch) -> None:
    def fail_normalize(_value):
        raise RuntimeError("boom")

    monkeypatch.setattr(evidence_anchor_module, "_normalize_sources", fail_normalize)

    result = evidence_anchor_module.evaluate_evidence_anchor({"evidence_anchor_required": True})

    assert result["evidence_anchor_status"] == "system_error"
    assert result["evidence_blocked"] is True
    assert "evidence_anchor_exception" in result["evidence_missing_reasons"]
    _assert_formal_chain_blocked(result)
