from __future__ import annotations

from backend.zhifei_autoplan.requirement_decisions import (
    build_requirement_decision_matrix,
    style_from_requirement_matrix,
)
from backend.zhifei_autoplan.style_policy import resolve_style_with_decisions


def test_clarification_overrides_tender_with_traceable_receipt():
    matrix = build_requirement_decision_matrix(
        [
            {
                "source_id": "tender.pdf",
                "source_type": "tender",
                "priority": 300,
                "confidence": 0.95,
                "values": {"line_spacing_pt": 22.0},
            },
            {
                "source_id": "clarification.pdf",
                "source_type": "clarification",
                "priority": 400,
                "confidence": 0.95,
                "values": {"line_spacing": 1.5},
            },
        ]
    )

    assert matrix["status"] == "resolved"
    assert matrix["fields"]["line_spacing"]["status"] == "resolved_by_priority"
    assert matrix["fields"]["line_spacing"]["selected"]["source_type"] == "clarification"
    assert style_from_requirement_matrix(matrix)["line_spacing"] == 1.5


def test_equal_priority_conflict_is_not_silently_decided():
    matrix = build_requirement_decision_matrix(
        [
            {
                "source_id": "tender-a.pdf",
                "source_type": "tender",
                "priority": 300,
                "confidence": 0.95,
                "values": {"body_font": "宋体"},
            },
            {
                "source_id": "tender-b.pdf",
                "source_type": "tender",
                "priority": 300,
                "confidence": 0.95,
                "values": {"body_font": "仿宋体"},
            },
        ]
    )

    assert matrix["status"] == "unresolved_conflict"
    assert matrix["unresolved_fields"] == ["body_font"]
    assert matrix["fields"]["body_font"]["selected"] is None
    assert "body_font" not in style_from_requirement_matrix(matrix)


def test_approved_resolution_closes_a_tender_conflict():
    tender_matrix = build_requirement_decision_matrix(
        [
            {
                "source_id": "tender-a.pdf",
                "source_type": "tender",
                "priority": 300,
                "confidence": 0.95,
                "values": {"body_font": "宋体"},
            },
            {
                "source_id": "tender-b.pdf",
                "source_type": "tender",
                "priority": 300,
                "confidence": 0.95,
                "values": {"body_font": "仿宋体"},
            },
        ]
    )
    style, source, matrix = resolve_style_with_decisions(
        user_style={},
        tender_style={},
        tender_decision_matrix=tender_matrix,
        approved_resolutions={"body_font": "宋体"},
    )

    assert matrix["status"] == "resolved"
    assert matrix["fields"]["body_font"]["selected"]["source_type"] == "approved_resolution"
    assert style["body_font"] == "宋体"
    assert source == "tender_override"
