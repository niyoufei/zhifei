from __future__ import annotations

from backend.app.core import actions_result_response


def test_build_actions_result_not_done_response_preserves_trace_meta():
    out = actions_result_response.build_actions_result_not_done_response(
        job_id="job-pending",
        status="running",
        error="still-working",
        trace_meta={"request_id": "req-pending", "trace_id": "trace-pending"},
    )
    assert out == {
        "ok": False,
        "code": "job_not_done",
        "message": "job not done",
        "job_id": "job-pending",
        "status": "running",
        "error": "still-working",
        "request_id": "req-pending",
        "trace_id": "trace-pending",
        "next_action": "poll /actions/job_status until status=done",
    }


def test_build_actions_result_response_trims_sections_and_preserves_contract_fields():
    out = actions_result_response.build_actions_result_response(
        job_id="job-1",
        trace_meta={"request_id": "req-1", "trace_id": "trace-1"},
        result={"json": "/tmp/result.json", "resource_usage_summary": {"call_count": 1}},
        variants=[
            {
                "variant_id": 1,
                "topic": "测试主题",
                "outline": ["工程概况"],
                "boq_focus": {"items": []},
                "quality_checks": {"score": 98},
                "logic_template_id": "A",
                "logic_template_name": "交付清单驱动",
                "generation_mode": "stable_delivery",
                "mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
                "sections": [{"title": "工程概况", "content": "x" * 500, "agent_role": "planner"}],
                "resource_usage_summary": {"variant_calls": 1},
            }
        ],
        variant=1,
        include_sections=True,
        max_chars=200,
        result_contract_view_fn=lambda *args, **kwargs: {"result_bundle_complete": True},
        download_artifact_path_fn=lambda result, kind, variant: f"/tmp/{kind}-{variant}",
    )
    assert out["ok"] is True
    assert out["variant_id"] == 1
    assert out["logic_template_id"] == "A"
    assert out["generation_mode_summary"]["profile"] == "stable_delivery"
    assert out["files"]["docx"] == "/tmp/docx-1"
    assert out["result_bundle_complete"] is True
    assert out["sections"][0]["content"].endswith("...")
    assert len(out["sections"][0]["content"]) == 203
