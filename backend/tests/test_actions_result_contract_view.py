from __future__ import annotations

import json

from backend.app.core.actions_result_view import result_contract_view
from backend.zhifei_autoplan.run_contract import build_result_bundle


DOWNLOAD_KIND_SPECS = {
    "docx": {
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename_pattern": "autoplan_{job_id}_v{variant}.docx",
    },
    "result_bundle_json": {
        "media_type": "application/json",
        "filename_pattern": "autoplan_{job_id}_result_bundle.json",
    },
    "json": {
        "media_type": "application/json",
        "filename_pattern": "autoplan_{job_id}.json",
    },
}


def test_result_contract_view_reports_complete_bundle_and_downloads(tmp_path):
    result_json = tmp_path / "result.json"
    docx_path = tmp_path / "result.docx"
    result_json.write_text("{}", encoding="utf-8")
    docx_path.write_bytes(b"docx")
    bundle_path = tmp_path / "result_bundle.json"
    bundle_path.write_text(
        json.dumps(
            build_result_bundle(
                job_id="job-1",
                payload={"project_id": "P-1", "topic": "契约视图"},
                outputs={"json": str(result_json), "docx": [str(docx_path)]},
                result_metadata={},
                resource_usage_summary={},
                variant_summary={"variant_count": 1},
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = {
        "json": str(result_json),
        "docx": [str(docx_path)],
        "result_bundle_json": str(bundle_path),
        "blocking_issue_summary": {
            "has_blocking_issues": True,
            "blocking_issue_count": 1,
            "failed_gate_metric_count": 1,
            "failed_gate_metrics": ["engineering_ok_rate"],
            "top_blocking_issues": [{"title": "施工部署", "type": "engineering_gap"}],
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
    }

    out = result_contract_view("job-1", payload, download_kind_specs=DOWNLOAD_KIND_SPECS, variant=1)

    assert out["result_bundle_json"] == str(bundle_path)
    assert out["result_bundle_available"] is True
    assert out["result_bundle_loaded"] is True
    assert out["result_bundle_complete"] is True
    assert out["result_bundle_request"]["project_id"] == "P-1"
    assert out["result_bundle_artifact_count"] == 2
    assert out["download_ready_kinds"] == ["docx", "result_bundle_json", "json"]
    assert out["primary_download_kind"] == "docx"
    assert out["has_blocking_issues"] is True
    assert out["top_blocking_issue_type"] == "engineering_gap"
    assert out["has_reference_risks"] is True
    assert out["case_copy_risk_count"] == 1
    assert out["affected_case_ids"] == ["case-1"]
    assert out["top_reference_risk_type"] == "case_reference_copy_risk"
    assert out["case_library_enabled"] is True
    assert out["case_library_selected_ids"] == ["case-1"]
    assert out["case_library_match_reasons"] == ["selected_case_ids"]
    assert out["image_library_enabled"] is True
    assert out["image_library_selected_ids"] == ["image-1"]
    assert out["image_library_match_reasons"] == ["selected_image_ids"]
    assert out["review_apply_variant"] == 1
    assert out["review_apply_applied_count"] == 2
    assert out["review_apply_reference_case_ids"] == ["case-1"]
    assert out["review_apply_issue_types"] == ["case_reference_copy_risk"]
    assert out["review_apply_history_count"] == 2
    assert out["review_apply_last_applied_at"] == "2026-04-12T00:00:30Z"
    assert out["review_apply_history"][-1]["reference_case_ids"] == ["case-1"]


def test_result_contract_view_handles_missing_bundle_gracefully():
    out = result_contract_view(
        "job-2",
        {"blocking_issue_summary": {"has_blocking_issues": False, "blocking_issue_count": 0}},
        download_kind_specs=DOWNLOAD_KIND_SPECS,
        variant=1,
    )

    assert out["download_ready_count"] == 0
    assert out["download_ready_kinds"] == []
    assert out["primary_download_kind"] is None
    assert out["has_blocking_issues"] is False
    assert "result_bundle_json" not in out
    assert "result_bundle_summary" not in out


def test_result_contract_view_prefers_variant_level_blocking_summary(tmp_path):
    bundle_path = tmp_path / "result_bundle.json"
    bundle_path.write_text(
        json.dumps(
            {
                "_bundle": {"schema": "zhifei.result_bundle", "schema_version": "actions-result-bundle-v1"},
                "request": {},
                "artifacts": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    out = result_contract_view(
        "job-3",
        {
            "result_bundle_json": str(bundle_path),
            "blocking_issue_summary": {
                "has_blocking_issues": False,
                "blocking_issue_count": 0,
                "failed_gate_metric_count": 0,
                "top_blocking_issues": [],
            },
            "blocking_issue_summary_by_variant": {
                "2": {
                    "has_blocking_issues": True,
                    "blocking_issue_count": 1,
                    "failed_gate_metric_count": 0,
                    "top_blocking_issues": [{"title": "关键章节", "type": "evidence_gap"}],
                }
            },
            "reference_quality_summary": {
                "has_reference_risks": False,
                "reference_risk_count": 0,
                "case_copy_risk_count": 0,
                "affected_case_ids": [],
                "top_reference_risks": [],
            },
            "reference_quality_summary_by_variant": {
                "2": {
                    "has_reference_risks": True,
                    "reference_risk_count": 1,
                    "case_copy_risk_count": 1,
                    "affected_case_ids": ["case-2"],
                    "top_reference_risks": [{"title": "关键章节", "type": "case_reference_copy_risk"}],
                }
            },
            "reference_enhancements": {
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": ["case-1", "case-2"],
                    "matched_project_type": "房建",
                    "matched_chapters": ["工程概况", "关键章节"],
                    "match_reasons": ["selected_case_ids"],
                    "hit_count": 2,
                    "warning_list": [],
                    "variant_ids": ["1", "2"],
                },
                "image_library": {
                    "enabled": True,
                    "selected_image_ids": ["image-1", "image-2"],
                    "matched_project_type": "房建",
                    "matched_chapters": ["工程概况", "关键章节"],
                    "match_reasons": ["project_type_chapter_tags"],
                    "hit_count": 2,
                    "warning_list": [],
                    "variant_ids": ["1", "2"],
                },
            },
            "reference_enhancements_by_variant": {
                "2": {
                    "case_library": {
                        "enabled": True,
                        "selected_case_ids": ["case-2"],
                        "matched_project_type": "房建",
                        "matched_chapter": "关键章节",
                        "match_reason": "selected_case_ids",
                        "hit_count": 1,
                        "warning_list": [],
                    },
                    "image_library": {
                        "enabled": True,
                        "selected_image_ids": ["image-2"],
                        "matched_project_type": "房建",
                        "matched_chapter": "关键章节",
                        "match_reason": "project_type_chapter_tags",
                        "hit_count": 1,
                        "warning_list": [],
                    },
                }
            },
            "latest_review_apply_summary": {
                "variant": 1,
                "applied_count": 9,
                "template_applied_count": 9,
                "replacement_count": 0,
                "reference_case_ids": [],
                "has_reference_case": False,
                "issue_types": ["engineering_gap"],
            },
            "quality_by_variant": {
                "2": {
                    "latest_review_apply_summary": {
                        "variant": 2,
                        "applied_count": 1,
                        "template_applied_count": 0,
                        "replacement_count": 1,
                        "reference_case_ids": ["case-2"],
                        "has_reference_case": True,
                        "issue_types": ["case_reference_copy_risk"],
                    }
                }
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
                    "variant": 2,
                    "applied_count": 1,
                    "template_applied_count": 0,
                    "replacement_count": 1,
                    "reference_case_ids": ["case-2"],
                    "has_reference_case": True,
                    "issue_types": ["case_reference_copy_risk"],
                    "titles": ["关键章节"],
                    "applied_at": "2026-04-12T00:00:10Z",
                },
            ],
        },
        download_kind_specs=DOWNLOAD_KIND_SPECS,
        variant=2,
    )

    assert out["result_bundle_available"] is True
    assert out["result_bundle_loaded"] is True
    assert out["result_bundle_complete"] is False
    assert out["has_blocking_issues"] is True
    assert out["blocking_issue_count"] == 1
    assert out["top_blocking_issue_type"] == "evidence_gap"
    assert out["has_reference_risks"] is True
    assert out["affected_case_ids"] == ["case-2"]
    assert out["top_reference_risk_type"] == "case_reference_copy_risk"
    assert out["case_library_selected_ids"] == ["case-2"]
    assert out["image_library_selected_ids"] == ["image-2"]
    assert out["review_apply_variant"] == 2
    assert out["review_apply_applied_count"] == 1
    assert out["review_apply_reference_case_ids"] == ["case-2"]
    assert out["review_apply_history_count"] == 1
    assert out["review_apply_last_applied_at"] == "2026-04-12T00:00:10Z"
    assert out["review_apply_history"][0]["variant"] == 2
