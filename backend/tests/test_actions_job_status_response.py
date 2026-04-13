from __future__ import annotations

from backend.app.core import actions_job_status_response


def test_build_actions_job_status_response_prefers_result_metadata_when_present():
    response = actions_job_status_response.build_actions_job_status_response(
        job_id="job-1",
        job={
            "job_id": "job-1",
            "status": "done",
            "payload": {
                "generation_mode": "stable_delivery",
                "logic_template_id": "A",
                "_mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
            },
            "result": {
                "generation_mode_summary": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
                "logic_template_id": "A",
                "logic_template_name": "交付清单驱动",
                "resource_usage_summary": {"call_count": 0},
                "runtime_by_variant": {"1": {"variant_index": 1, "pipeline_stages": [{"stage": "draft_generation"}]}},
                "quality_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "quality_gate_ok": True,
                        "quality_score": 98,
                        "reference_quality_summary": {
                            "has_reference_risks": True,
                            "reference_risk_count": 1,
                            "case_copy_risk_count": 1,
                        },
                    }
                },
                "blocking_issue_summary_by_variant": {"1": {"has_blocking_issues": False}},
                "reference_quality_summary_by_variant": {
                    "1": {
                        "has_reference_risks": True,
                        "reference_risk_count": 1,
                        "case_copy_risk_count": 1,
                    }
                },
                "reference_quality_summary": {
                    "has_reference_risks": True,
                    "reference_risk_count": 1,
                    "case_copy_risk_count": 1,
                    "affected_case_ids": ["case-1"],
                },
                "review_apply_history": [
                    {
                        "variant": 1,
                        "applied_count": 1,
                        "template_applied_count": 1,
                        "replacement_count": 0,
                        "reference_case_ids": ["case-1"],
                        "has_reference_case": True,
                        "issue_types": ["case_reference_copy_risk"],
                        "titles": ["施工部署"],
                        "applied_at": "2026-04-12T00:00:00Z",
                    }
                ],
            },
        },
        trace_meta={"request_id": "req-1", "trace_id": "trace-1"},
        result_contract_view_fn=lambda *args, **kwargs: {
            "download_ready_count": 2,
            "result_bundle_complete": True,
            "case_library_enabled": True,
            "case_library_selected_ids": ["case-1"],
            "image_library_enabled": True,
            "image_library_selected_ids": ["image-1"],
            "review_apply_history_count": 1,
            "review_apply_last_applied_at": "2026-04-12T00:00:00Z",
        },
    )
    job = response["job"]
    assert response["ok"] is True
    assert job["logic_template_id"] == "A"
    assert job["logic_template_name"] == "交付清单驱动"
    assert job["generation_mode_summary"]["stable_output"] is True
    assert job["runtime_by_variant"]["1"]["pipeline_stages"][0]["stage"] == "draft_generation"
    assert job["quality_ok"] == [True]
    assert job["download_ready_count"] == 2
    assert job["result_bundle_complete"] is True
    assert job["reference_quality_summary"]["case_copy_risk_count"] == 1
    assert job["reference_quality_summary_by_variant"]["1"]["has_reference_risks"] is True
    assert job["case_library_enabled"] is True
    assert job["case_library_selected_ids"] == ["case-1"]
    assert job["image_library_enabled"] is True
    assert job["image_library_selected_ids"] == ["image-1"]
    assert job["review_apply_history_count"] == 1
    assert job["review_apply_last_applied_at"] == "2026-04-12T00:00:00Z"
