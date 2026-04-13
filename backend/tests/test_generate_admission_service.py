from __future__ import annotations

import pytest

from backend.zhifei_autoplan import generate_admission_service


def test_resolve_generate_admission_returns_reused_response():
    out = generate_admission_service.resolve_generate_admission(
        payload={"request_id": "req-1", "trace_id": "trace-1"},
        session_id="sess-1",
        workspace_dir="/tmp/ws",
        request_signature="sig-1",
        find_reusable_job_fn=lambda *args, **kwargs: {"job_id": "job-1", "status": "done", "payload": {"request_id": "req-1"}},
        evaluate_job_admission_fn=lambda **kwargs: {"scope": "session", "allowed": True, "requested_jobs": kwargs["requested_jobs"]},
        admission_http_detail_fn=lambda admission: dict(admission),
        append_resource_event_fn=lambda *args, **kwargs: None,
        build_reused_response_fn=lambda reusable, detail: {"job_id": reusable["job_id"], "admission": detail, "reused": True},
        build_rejection_event_fn=lambda **kwargs: {},
        build_rejected_detail_fn=lambda **kwargs: {},
        apply_admission_degrade_fn=lambda payload, admission: None,
        new_log_anchor_fn=lambda stage: f"actions.{stage}.1",
    )

    assert out.reusable_response == {
        "job_id": "job-1",
        "admission": {"scope": "session", "allowed": True, "requested_jobs": 0},
        "reused": True,
    }
    assert out.admission is None


def test_resolve_generate_admission_raises_structured_rejection_and_emits_event():
    events: list[tuple[tuple, dict]] = []

    with pytest.raises(generate_admission_service.GenerateAdmissionRejected) as exc:
        generate_admission_service.resolve_generate_admission(
            payload={"request_id": "req-2", "trace_id": "trace-2", "topic": "限流"},
            session_id="sess-2",
            workspace_dir="/tmp/ws",
            request_signature="sig-2",
            find_reusable_job_fn=lambda *args, **kwargs: None,
            evaluate_job_admission_fn=lambda **kwargs: {"allowed": False, "code": "session_running_capacity_exceeded", "scope": "session"},
            admission_http_detail_fn=lambda admission: {"code": admission["code"], "scope": admission["scope"]},
            append_resource_event_fn=lambda *args, **kwargs: events.append((args, kwargs)),
            build_reused_response_fn=lambda reusable, detail: {},
            build_rejection_event_fn=lambda **kwargs: {"rejection_code": kwargs["admission"]["code"]},
            build_rejected_detail_fn=lambda **kwargs: {"code": kwargs["admission_detail"]["code"], "log_anchor": kwargs["log_anchor"]},
            apply_admission_degrade_fn=lambda payload, admission: None,
            new_log_anchor_fn=lambda stage: f"actions.{stage}.2",
        )

    assert exc.value.detail == {"code": "session_running_capacity_exceeded", "log_anchor": "actions.admission.2"}
    assert events == [
        (
            ("job_rejected",),
            {
                "workspace_dir": "/tmp/ws",
                "session_id": "sess-2",
                "user_id": None,
                "rejection_code": "session_running_capacity_exceeded",
            },
        )
    ]


def test_resolve_generate_admission_applies_degrade_plan_to_admission():
    out = generate_admission_service.resolve_generate_admission(
        payload={"variants": 2},
        session_id="sess-3",
        workspace_dir="/tmp/ws",
        request_signature="sig-3",
        find_reusable_job_fn=lambda *args, **kwargs: None,
        evaluate_job_admission_fn=lambda **kwargs: {"allowed": True, "warning_level": "warning", "warnings": []},
        admission_http_detail_fn=lambda admission: dict(admission),
        append_resource_event_fn=lambda *args, **kwargs: None,
        build_reused_response_fn=lambda reusable, detail: {},
        build_rejection_event_fn=lambda **kwargs: {},
        build_rejected_detail_fn=lambda **kwargs: {},
        apply_admission_degrade_fn=lambda payload, admission: {"applied": True, "variant_parallelism_after": 1},
        new_log_anchor_fn=lambda stage: f"actions.{stage}.3",
    )

    assert out.reusable_response is None
    assert out.admission == {
        "allowed": True,
        "warning_level": "warning",
        "warnings": [],
        "degrade_plan": {"applied": True, "variant_parallelism_after": 1},
    }
