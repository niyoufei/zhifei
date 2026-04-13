from __future__ import annotations

from backend.app.core import actions_recent_view


def test_build_recent_job_item_merges_contract_and_quality_views():
    item = actions_recent_view.build_recent_job_item(
        {
            "job_id": "job-1",
            "status": "done",
            "payload": {
                "topic": "稳定交付最近任务探针",
                "project_id": "recent-metadata-case",
                "project_type": "房建",
                "generation_mode": "stable_delivery",
                "_mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "planned_total_pages": 12,
                },
            },
            "result": {
                "generation_mode_summary": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                },
                "reference_quality_summary": {
                    "has_reference_risks": True,
                    "reference_risk_count": 1,
                    "case_copy_risk_count": 1,
                    "affected_case_ids": ["case-1"],
                    "top_reference_risks": [{"title": "施工部署", "type": "case_reference_copy_risk"}],
                },
                "reference_enhancements": {
                    "case_library": {
                        "enabled": True,
                        "selected_case_ids": ["case-1"],
                        "matched_project_type": "房建",
                        "matched_chapters": ["施工部署"],
                        "match_reasons": ["selected_case_ids"],
                        "hit_count": 1,
                        "warning_list": [],
                        "variant_ids": ["1"],
                    },
                    "image_library": {
                        "enabled": True,
                        "selected_image_ids": ["image-1"],
                        "matched_project_type": "房建",
                        "matched_chapters": ["施工部署"],
                        "match_reasons": ["selected_image_ids"],
                        "hit_count": 1,
                        "warning_list": [],
                        "variant_ids": ["1"],
                    },
                },
                "latest_review_apply_summary": {
                    "variant": 1,
                    "applied_count": 2,
                    "template_applied_count": 2,
                    "replacement_count": 0,
                    "reference_case_ids": ["case-1"],
                    "has_reference_case": True,
                    "issue_types": ["case_reference_copy_risk"],
                },
                "review_apply_history": [
                    {
                        "variant": 1,
                        "applied_count": 1,
                        "template_applied_count": 1,
                        "replacement_count": 0,
                        "reference_case_ids": [],
                        "has_reference_case": False,
                        "issue_types": ["engineering_gap"],
                        "titles": ["工程概况"],
                        "applied_at": "2026-04-12T00:00:00Z",
                    },
                    {
                        "variant": 1,
                        "applied_count": 2,
                        "template_applied_count": 2,
                        "replacement_count": 0,
                        "reference_case_ids": ["case-1"],
                        "has_reference_case": True,
                        "issue_types": ["case_reference_copy_risk"],
                        "titles": ["施工部署"],
                        "applied_at": "2026-04-12T00:00:30Z",
                    },
                ],
                "quality_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "variant_id": 1,
                        "logic_template_id": "A",
                        "logic_template_name": "交付清单驱动",
                        "quality_score": 98,
                        "quality_gate_ok": False,
                        "quality_gate_failed_count": 1,
                        "blocking_issue_summary": {
                            "has_blocking_issues": True,
                            "blocking_issue_count": 1,
                            "failed_gate_metric_count": 1,
                            "top_blocking_issues": [{"title": "施工部署", "type": "engineering_gap"}],
                        },
                    }
                },
            },
            "progress": {"stage": "done", "percent": 100},
        },
        result_available=False,
        download_kind_specs={
            "docx": {
                "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "filename_pattern": "autoplan_{job_id}_v{variant}.docx",
            }
        },
    )
    assert item["job_id"] == "job-1"
    assert item["generation_mode"] == "stable_delivery"
    assert item["mode_effective"] == "stable_delivery"
    assert item["logic_template_id"] == "A"
    assert item["logic_template_name"] == "交付清单驱动"
    assert item["quality_score"] == 98
    assert item["has_blocking_issues"] is True
    assert item["blocking_issue_count"] == 1
    assert item["top_blocking_issue_type"] == "engineering_gap"
    assert item["has_reference_risks"] is True
    assert item["reference_risk_count"] == 1
    assert item["case_copy_risk_count"] == 1
    assert item["affected_case_ids"] == ["case-1"]
    assert item["top_reference_risk_type"] == "case_reference_copy_risk"
    assert item["case_library_enabled"] is True
    assert item["case_library_selected_ids"] == ["case-1"]
    assert item["image_library_enabled"] is True
    assert item["image_library_selected_ids"] == ["image-1"]
    assert item["review_apply_applied_count"] == 2
    assert item["review_apply_reference_case_ids"] == ["case-1"]
    assert item["review_apply_issue_types"] == ["case_reference_copy_risk"]
    assert item["review_apply_history_count"] == 2
    assert item["review_apply_last_applied_at"] == "2026-04-12T00:00:30Z"
    assert item["result_available"] is False
    assert item["automation_summary"] == {}
