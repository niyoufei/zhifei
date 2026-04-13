from __future__ import annotations

from backend.app.core import actions_review_view


def test_review_items_for_variant_deduplicates_auto_suggestions_and_sorts():
    rows = actions_review_view.review_items_for_variant(
        {
            "sections": [
                {"title": "主要施工方法", "content": "内容A"},
                {"title": "安全措施", "content": "内容B"},
            ],
            "quality_checks": {
                "issue_list": [
                    {
                        "title": "主要施工方法",
                        "type": "quantitative_gap",
                        "severity": "high",
                        "problem": "量化不足",
                        "suggestion": "补齐量化指标",
                    }
                ],
                "auto_revision_suggestions": [
                    {
                        "title": "主要施工方法",
                        "type": "quantitative_gap",
                        "suggestion": "补齐量化指标",
                    },
                    {
                        "title": "安全措施",
                        "type": "risk_triplet_gap",
                        "suggestion": "补齐风险控制验证",
                    },
                ],
            },
        }
    )
    assert len(rows) == 2
    assert rows[0]["issue_id"].startswith("I")
    assert rows[0]["severity"] == "high"
    assert rows[1]["issue_id"].startswith("R")
    assert rows[1]["section_excerpt"] == "内容B"


def test_review_items_for_variant_keeps_reference_case_context():
    rows = actions_review_view.review_items_for_variant(
        {
            "sections": [
                {
                    "title": "施工部署",
                    "content": "内容A",
                    "case_reference_pack": {
                        "match_reason": "selected_case_ids",
                        "non_fact_reference_notice": "案例仅用于结构与表达参考",
                        "hits": [
                            {
                                "case_id": "case-1",
                                "title": "养老院改造样板",
                            }
                        ],
                    },
                },
            ],
            "quality_checks": {
                "issue_list": [
                    {
                        "title": "施工部署",
                        "type": "case_reference_copy_risk",
                        "severity": "high",
                        "problem": "与案例相似度过高",
                        "suggestion": "重写本章",
                        "reference_case_id": "case-1",
                    }
                ],
                "auto_revision_suggestions": [],
            },
        }
    )
    assert len(rows) == 1
    assert rows[0]["type"] == "case_reference_copy_risk"
    assert rows[0]["reference_case_id"] == "case-1"
    assert rows[0]["reference_context"] == {
        "reference_case_id": "case-1",
        "reference_case_title": "养老院改造样板",
        "match_reason": "selected_case_ids",
        "non_fact_reference_notice": "案例仅用于结构与表达参考",
    }


def test_select_review_variant_falls_back_to_first_when_requested_out_of_range():
    variant, record = actions_review_view.select_review_variant(
        [{"variant_id": 1}, {"variant_id": 2}],
        9,
    )
    assert variant == 1
    assert record == {"variant_id": 1}


def test_build_review_issues_response_uses_selected_variant_and_count():
    out = actions_review_view.build_review_issues_response(
        job_id="job-1",
        requested_variant=2,
        variants=[{"variant_id": 1}, {"variant_id": 2}],
        review_items_fn=lambda record: [{"issue_id": f"for-{record['variant_id']}"}],
    )
    assert out == {
        "ok": True,
        "job_id": "job-1",
        "variant": 2,
        "count": 1,
        "items": [{"issue_id": "for-2"}],
    }
