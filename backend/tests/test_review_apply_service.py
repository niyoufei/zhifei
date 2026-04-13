from __future__ import annotations

from backend.zhifei_autoplan import review_apply_service


def test_select_review_variant_falls_back_to_first_for_requested_variant_out_of_range():
    idx, target = review_apply_service.select_review_variant(
        [{"variant_id": 1}, {"variant_id": 2}],
        requested_variant=8,
    )
    assert idx == 0
    assert target == {"variant_id": 1}


def test_apply_review_decisions_returns_no_selected_items_without_side_effects():
    called: list[str] = []
    out = review_apply_service.apply_review_decisions(
        job_id="job-1",
        requested_variant=1,
        workspace_dir="/tmp/ws",
        job={"payload": {}},
        data={"variants": [{}]},
        variants=[{"sections": []}],
        apply_all=False,
        decisions=[],
        review_items_for_variant_fn=lambda variant: [],
        save_outputs_fn=lambda *args, **kwargs: called.append("save_outputs") or {},
        rebuild_postprocessed_fn=lambda *args, **kwargs: called.append("rebuild"),
        review_result_metadata_fn=lambda *args, **kwargs: {},
        review_variant_result_summary_fn=lambda *args, **kwargs: {},
        write_review_result_bundle_fn=lambda *args, **kwargs: "",
        result_contract_view_fn=lambda *args, **kwargs: {},
    )
    assert out == {
        "ok": True,
        "job_id": "job-1",
        "variant": 1,
        "applied_count": 0,
        "message": "no selected items",
    }
    assert called == []


def test_apply_review_decisions_builds_review_items_from_requested_variant_fallback():
    out = review_apply_service.apply_review_decisions(
        job_id="job-2",
        requested_variant=9,
        workspace_dir="/tmp/ws",
        job={"payload": {}},
        data={"variants": [{}, {}]},
        variants=[
            {"sections": [], "marker": "first"},
            {"sections": [], "marker": "second"},
        ],
        apply_all=False,
        decisions=[],
        review_items_for_variant_fn=lambda variant: [{"issue_id": variant["marker"]}],
        save_outputs_fn=lambda *args, **kwargs: {},
        rebuild_postprocessed_fn=lambda *args, **kwargs: None,
        review_result_metadata_fn=lambda *args, **kwargs: {},
        review_variant_result_summary_fn=lambda *args, **kwargs: {},
        write_review_result_bundle_fn=lambda *args, **kwargs: "",
        result_contract_view_fn=lambda *args, **kwargs: {},
    )
    assert out == {
        "ok": True,
        "job_id": "job-2",
        "variant": 1,
        "applied_count": 0,
        "message": "no selected items",
    }


def test_apply_review_decisions_returns_applied_items_summary_for_reference_risk(monkeypatch):
    monkeypatch.setattr(review_apply_service, "_utc_now_iso", lambda: "2026-04-12T00:00:00Z")
    monkeypatch.setattr(review_apply_service, "update_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(review_apply_service, "apply_remediation", lambda *args, **kwargs: None)
    audit_events: list[dict] = []
    out = review_apply_service.apply_review_decisions(
        job_id="job-3",
        requested_variant=1,
        workspace_dir="/tmp/ws",
        job={"payload": {"session_id": "sess-1", "request_id": "req-1", "trace_id": "trace-1", "topic": "复核主题"}},
        data={"variants": [{"sections": [{"title": "施工部署", "content": "原始内容"}]}]},
        variants=[
            {
                "sections": [{"title": "施工部署", "content": "原始内容"}],
            }
        ],
        apply_all=True,
        decisions=None,
        review_items=[
            {
                "issue_id": "I0001",
                "source": "issue_list",
                "title": "施工部署",
                "type": "case_reference_copy_risk",
                "suggestion": "重写本章",
                "reference_case_id": "case-1",
                "reference_context": {
                    "reference_case_id": "case-1",
                    "reference_case_title": "养老院改造样板",
                },
            }
        ],
        save_outputs_fn=lambda *args, **kwargs: {"json": "/tmp/review.json", "docx": ["/tmp/review.docx"]},
        rebuild_postprocessed_fn=lambda *args, **kwargs: None,
        review_result_metadata_fn=lambda *args, **kwargs: {},
        review_variant_result_summary_fn=lambda *args, **kwargs: {},
        write_review_result_bundle_fn=lambda *args, **kwargs: "/tmp/review_bundle.json",
        result_contract_view_fn=lambda *args, **kwargs: {"result_bundle_json": "/tmp/review_bundle.json"},
        append_resource_event_fn=lambda event, **fields: audit_events.append({"event": event, **fields}) or "/tmp/audit.jsonl",
    )
    assert out["applied_count"] == 1
    assert out["applied_reference_case_ids"] == ["case-1"]
    assert out["review_apply_history_count"] == 1
    assert out["review_apply_last_applied_at"] == "2026-04-12T00:00:00Z"
    assert out["review_apply_history"] == [
        {
            "variant": 1,
            "applied_count": 1,
            "template_applied_count": 1,
            "replacement_count": 0,
            "titles": ["施工部署"],
            "issue_types": ["case_reference_copy_risk"],
            "reference_case_ids": ["case-1"],
            "has_reference_case": True,
            "applied_at": "2026-04-12T00:00:00Z",
        }
    ]
    assert out["applied_items_summary"] == [
        {
            "issue_id": "I0001",
            "source": "issue_list",
            "title": "施工部署",
            "type": "case_reference_copy_risk",
            "apply_mode": "remediation",
            "reference_case_id": "case-1",
            "reference_context": {
                "reference_case_id": "case-1",
                "reference_case_title": "养老院改造样板",
            },
        }
    ]
    assert audit_events == [
        {
            "event": "review_apply",
            "workspace_dir": "/tmp/ws",
            "session_id": "sess-1",
            "user_id": None,
            "job_id": "job-3",
            "request_id": "req-1",
            "trace_id": "trace-1",
            "project_id": None,
            "topic": "复核主题",
            "variant_id": 1,
            "applied_count": 1,
            "template_applied_count": 1,
            "replacement_count": 0,
            "applied_reference_case_ids": ["case-1"],
            "applied_titles": ["施工部署"],
            "applied_types": ["case_reference_copy_risk"],
        }
    ]


def test_apply_review_decisions_appends_and_bounds_review_apply_history(monkeypatch):
    timestamps = iter(
        [
            "2026-04-12T00:00:01Z",
            "2026-04-12T00:00:02Z",
        ]
    )
    monkeypatch.setattr(review_apply_service, "_utc_now_iso", lambda: next(timestamps))
    monkeypatch.setattr(review_apply_service, "update_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(review_apply_service, "apply_remediation", lambda *args, **kwargs: None)

    base_job = {
        "payload": {},
        "result": {
            "review_apply_history": [
                {
                    "variant": 1,
                    "applied_count": idx,
                    "template_applied_count": idx,
                    "replacement_count": 0,
                    "titles": [f"章节{idx}"],
                    "issue_types": ["engineering_gap"],
                    "reference_case_ids": [],
                    "has_reference_case": False,
                    "applied_at": f"2026-04-11T00:00:0{idx}Z",
                }
                for idx in range(1, 6)
            ]
        },
    }

    out = review_apply_service.apply_review_decisions(
        job_id="job-4",
        requested_variant=1,
        workspace_dir="/tmp/ws",
        job=base_job,
        data={"variants": [{"sections": [{"title": "施工部署", "content": "原始内容"}]}]},
        variants=[{"sections": [{"title": "施工部署", "content": "原始内容"}]}],
        apply_all=True,
        decisions=None,
        review_items=[
            {
                "issue_id": "I0002",
                "source": "issue_list",
                "title": "施工部署",
                "type": "engineering_gap",
                "suggestion": "补齐责任人",
            }
        ],
        save_outputs_fn=lambda *args, **kwargs: {"json": "/tmp/review2.json", "docx": ["/tmp/review2.docx"]},
        rebuild_postprocessed_fn=lambda *args, **kwargs: None,
        review_result_metadata_fn=lambda *args, **kwargs: {},
        review_variant_result_summary_fn=lambda *args, **kwargs: {},
        write_review_result_bundle_fn=lambda *args, **kwargs: "/tmp/review_bundle2.json",
        result_contract_view_fn=lambda *args, **kwargs: {},
    )

    assert out["review_apply_history_count"] == 5
    assert out["review_apply_history"][0]["applied_count"] == 2
    assert out["review_apply_history"][-1]["applied_at"] == "2026-04-12T00:00:01Z"
    assert out["review_apply_history"][-1]["issue_types"] == ["engineering_gap"]
