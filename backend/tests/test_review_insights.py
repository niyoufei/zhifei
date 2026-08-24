from __future__ import annotations

from backend.zhifei_autoplan.review_insights import build_review_insight


def test_review_insight_ready_for_human_final_review() -> None:
    variant = {
        "quality_checks": {
            "score": 94,
            "structure": {"ok": True},
            "risk_triplet": {"ok": True},
            "evidence_traceability": {
                "ok": True,
                "by_section": [{"title": "施工方法", "ok": True}],
            },
            "consistency": {"ok": True},
            "issue_list": [],
        },
        "score_mapping": {
            "summary": {"item_count": 4, "estimated_ratio": 0.92, "high_risk_item_count": 0},
            "item_cards": [{"dimension": "施工方法", "coverage_ratio": 0.92, "deduction_risk": 0.08}],
            "high_risk_items": [],
        },
        "evidence_tracking": {
            "summary": {"paragraph_count": 10, "traceable_locator_rows": 9}
        },
        "agent_contract_checks": {"ok": True},
        "pipeline_stages": [{"stage": "quality", "ok": True}, {"stage": "evidence", "ok": True}],
    }

    insight = build_review_insight(variant)

    assert insight["readiness"] == "human_final_review"
    assert insight["quality_level"] in {"优秀", "良好"}
    assert insight["metrics"]["score_coverage_ratio"] == 0.92
    assert insight["metrics"]["evidence_traceability_ratio"] == 0.9
    assert insight["metrics"]["evidence_traceability_section_ratio"] == 1.0
    assert insight["metrics"]["evidence_paragraph_count"] == 10
    assert insight["metrics"]["evidence_traceable_paragraph_count"] == 9
    assert insight["metrics"]["evidence_section_count"] == 1
    assert insight["metrics"]["evidence_traceable_section_count"] == 1
    assert insight["top_risks"] == []
    assert insight["official_score_claim"] is False
    assert insight["advisory_only"] is True


def test_review_insight_blocks_when_risk_and_contract_fail() -> None:
    variant = {
        "quality_checks": {
            "score": 52,
            "structure": {"ok": False},
            "evidence_traceability": {"ok": False},
            "issue_list": [
                {"severity": "high"},
                {"severity": "严重"},
                {"severity": "高"},
            ],
        },
        "score_mapping": {
            "summary": {"item_count": 5, "estimated_ratio": 0.42, "high_risk_item_count": 3},
            "high_risk_items": [
                {
                    "dimension": "安全措施",
                    "coverage_ratio": 0.25,
                    "deduction_risk": 0.9,
                    "missing_keywords": ["应急预案", "演练频次"],
                }
            ],
        },
        "evidence_tracking": {"summary": {"paragraph_count": 10, "traceable_locator_rows": 2}},
        "agent_contract_checks": {"ok": False},
        "pipeline_stages": [{"stage": "quality", "ok": False}],
    }

    insight = build_review_insight(variant)

    assert insight["readiness"] == "not_ready"
    assert insight["metrics"]["high_issue_count"] == 3
    assert insight["metrics"]["high_risk_score_item_count"] == 3
    assert insight["top_risks"][0]["评分项"] == "安全措施"
    assert any("Agent 合同" in action for action in insight["priority_actions"])
    assert any("证据追溯" in action for action in insight["priority_actions"])


def test_review_insight_falls_back_to_dimension_ratio() -> None:
    insight = build_review_insight(
        {
            "quality_checks": {
                "structure": {"ok": True},
                "quantitative": {"ok": False},
            }
        }
    )

    assert insight["metrics"]["internal_quality_score"] == 50.0
    assert insight["metrics"]["dimension_pass_ratio"] == 0.5
    assert insight["readiness"] == "not_ready"


def test_review_insight_is_fail_closed_when_data_missing() -> None:
    first = build_review_insight({})
    second = build_review_insight(None)

    assert first == second
    assert first["readiness"] == "insufficient_data"
    assert first["composite_score"] is None
    assert first["metrics"]["internal_quality_score"] is None
    assert first["official_score_claim"] is False
    assert first["priority_actions"] == ["先完成招标文件解析和至少一版施组生成，再形成内部质量判断。"]
