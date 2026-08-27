from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.routers.actions_bridge import (
    ActionsGenerateRequest,
    _delivery_progress_for_run,
    _public_runtime_error,
)
from backend.zhifei_autoplan.orchestrator import (
    _build_chapter_validation_quality_gate,
    _normalize_delivery_scope,
    _validate_strict_outline_for_scope,
)


TENDER_OUTLINE = ["第一章", "第二章", "第三章"]


def test_delivery_scope_defaults_to_formal_document() -> None:
    request = ActionsGenerateRequest(topic="正式交付")

    assert request.delivery_scope == "document"
    assert _normalize_delivery_scope(None) == "document"


def test_delivery_scope_rejects_unknown_value_at_request_boundary() -> None:
    with pytest.raises(ValidationError):
        ActionsGenerateRequest(topic="非法范围", delivery_scope="preview")

    with pytest.raises(ValueError, match="delivery_scope"):
        _normalize_delivery_scope("preview")


def test_formal_document_requires_exact_tender_outline() -> None:
    _validate_strict_outline_for_scope(
        list(TENDER_OUTLINE),
        list(TENDER_OUTLINE),
        delivery_scope="document",
    )

    with pytest.raises(ValueError, match="TENDER_OUTLINE_MISMATCH"):
        _validate_strict_outline_for_scope(
            TENDER_OUTLINE[:2],
            list(TENDER_OUTLINE),
            delivery_scope="document",
        )


def test_chapter_validation_allows_only_tender_outline_subset() -> None:
    _validate_strict_outline_for_scope(
        TENDER_OUTLINE[:2],
        list(TENDER_OUTLINE),
        delivery_scope="chapter_validation",
    )

    with pytest.raises(ValueError, match="CHAPTER_VALIDATION_OUTLINE_INVALID"):
        _validate_strict_outline_for_scope(
            ["第一章", "目录外章节"],
            list(TENDER_OUTLINE),
            delivery_scope="chapter_validation",
        )


def test_chapter_validation_has_non_delivery_terminal_state() -> None:
    completion = _delivery_progress_for_run(
        dry_run=False,
        delivery_scope="chapter_validation",
    )

    assert completion["stage"] == "chapter_validation_done"
    assert completion["phase"] == "chapter_validation_done"
    assert "未生成" in completion["detail"]


def test_dry_run_precedes_chapter_validation_terminal_state() -> None:
    completion = _delivery_progress_for_run(
        dry_run=True,
        delivery_scope="chapter_validation",
    )

    assert completion["stage"] == "dry_run_done"


def test_outline_mismatch_is_projected_to_stable_public_error() -> None:
    result = _public_runtime_error(
        ValueError(
            "TENDER_OUTLINE_MISMATCH："
            "严格正式交付目录与招标目录不一致，已在模型调用前停止。"
        )
    )

    assert result["code"] == "TENDER_OUTLINE_MISMATCH"
    assert "chapter_validation" in result["action"]


def test_chapter_validation_quality_gate_uses_section_not_document_score() -> None:
    gate = _build_chapter_validation_quality_gate(
        quality={
            key: {"ok": True}
            for key in (
                "structure",
                "officialese",
                "risk_triplet",
                "logic_template_adherence",
                "quantitative",
                "required_topics_detail",
                "evidence_traceability",
                "standard_evidence",
            )
        }
        | {
            "independent_content_review": {
                "score": 68,
                "threshold": 75,
                "section_threshold": 60,
                "by_section": [
                    {"title": "第一章", "score": 72, "status": "pass"}
                ],
            }
        },
        contract_checks={"ok": True},
        delivery_quality_gate={
            "checks": [
                {"name": "independent_model_review", "pass": True}
            ]
        },
    )

    assert gate["pass"] is True


def test_chapter_validation_quality_gate_fails_low_section_or_model_review() -> None:
    gate = _build_chapter_validation_quality_gate(
        quality={
            key: {"ok": True}
            for key in (
                "structure",
                "officialese",
                "risk_triplet",
                "logic_template_adherence",
                "quantitative",
                "required_topics_detail",
                "evidence_traceability",
                "standard_evidence",
            )
        }
        | {
            "independent_content_review": {
                "section_threshold": 60,
                "by_section": [
                    {"title": "第一章", "score": 59, "status": "blocked"}
                ],
            }
        },
        contract_checks={"ok": True},
        delivery_quality_gate={
            "checks": [
                {"name": "independent_model_review", "pass": False}
            ]
        },
    )

    assert gate["pass"] is False
    assert "CHAPTER_SECTION_QUALITY_BLOCKED" in gate["blocker_codes"]
    assert "CHAPTER_MODEL_REVIEW_BLOCKED" in gate["blocker_codes"]
