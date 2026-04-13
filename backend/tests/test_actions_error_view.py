from __future__ import annotations

from backend.app.core import actions_error_view


def test_build_actions_error_detail_omits_empty_optional_fields():
    out = actions_error_view.build_actions_error_detail(
        "",
        "",
        stage="",
        log_anchor="anchor-1",
    )
    assert out == {
        "ok": False,
        "code": "actions_error",
        "message": "actions error",
        "stage": "unknown",
        "log_anchor": "anchor-1",
    }


def test_build_actions_error_detail_keeps_non_empty_fields():
    out = actions_error_view.build_actions_error_detail(
        "job_not_done",
        "job not done",
        stage="download",
        log_anchor="anchor-2",
        job_id="job-1",
        request_id="req-1",
        trace_id="trace-1",
        next_action="poll",
        extra={"kind": "docx"},
    )
    assert out == {
        "ok": False,
        "code": "job_not_done",
        "message": "job not done",
        "stage": "download",
        "log_anchor": "anchor-2",
        "job_id": "job-1",
        "request_id": "req-1",
        "trace_id": "trace-1",
        "next_action": "poll",
        "extra": {"kind": "docx"},
    }
