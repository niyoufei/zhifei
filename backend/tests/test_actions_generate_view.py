from __future__ import annotations

from backend.app.core import actions_generate_view


def test_build_generate_payload_prepare_error_maps_provider_not_configured():
    out = actions_generate_view.build_generate_payload_prepare_error("text_provider_not_configured:openai")
    assert out == {
        "status_code": 503,
        "code": "provider_not_configured",
        "message": "text provider not configured",
        "stage": "payload_prepare",
        "next_action": "configure text provider env keys or use dry_run=true",
        "extra": {"reason": "text_provider_not_configured:openai"},
    }


def test_build_generate_payload_prepare_error_maps_generic_failure():
    out = actions_generate_view.build_generate_payload_prepare_error("boom")
    assert out == {
        "status_code": 500,
        "code": "payload_prepare_failed",
        "message": "failed to prepare runtime payload",
        "stage": "payload_prepare",
        "next_action": "check server logs for payload preparation failure",
        "extra": {"reason": "boom"},
    }


def test_build_generate_worker_spawn_error_keeps_trace_fields():
    out = actions_generate_view.build_generate_worker_spawn_error(
        job_id="job-9",
        request_id="req-9",
        trace_id="trace-9",
        worker_log_path="/tmp/worker.log",
    )
    assert out == {
        "status_code": 500,
        "code": "worker_spawn_failed",
        "message": "worker spawn failed",
        "stage": "worker_spawn",
        "job_id": "job-9",
        "request_id": "req-9",
        "trace_id": "trace-9",
        "next_action": "check worker log and subprocess spawn permissions",
        "extra": {"worker_log_path": "/tmp/worker.log"},
    }


def test_build_generate_async_rejection_event_preserves_admission_fields():
    out = actions_generate_view.build_generate_async_rejection_event(
        payload={"request_id": "req-3", "trace_id": "trace-3", "project_id": "p-1", "topic": "限制测试", "variants": 2},
        admission={"code": "session_running_capacity_exceeded", "scope": "session", "next_action": "wait", "usage": {"queued": 1}, "limits": {"running": 1}},
        request_signature="sig-1",
    )
    assert out["request_signature"] == "sig-1"
    assert out["request_id"] == "req-3"
    assert out["trace_id"] == "trace-3"
    assert out["project_id"] == "p-1"
    assert out["topic"] == "限制测试"
    assert out["variants"] == 2
    assert out["rejection_code"] == "session_running_capacity_exceeded"
    assert out["rejection_scope"] == "session"


def test_build_generate_async_rejected_detail_sets_actions_error_shape():
    out = actions_generate_view.build_generate_async_rejected_detail(
        admission_detail={"code": "session_running_capacity_exceeded", "scope": "session"},
        request_id="req-4",
        trace_id="trace-4",
        log_anchor="actions.admission.1",
    )
    assert out["ok"] is False
    assert out["message"] == "job admission rejected"
    assert out["stage"] == "admission"
    assert out["log_anchor"] == "actions.admission.1"
    assert out["request_id"] == "req-4"
    assert out["trace_id"] == "trace-4"


def test_build_generate_async_reused_response_keeps_existing_ids():
    out = actions_generate_view.build_generate_async_reused_response(
        {
            "job_id": "job-1",
            "status": "done",
            "payload": {"request_id": "req-1", "trace_id": "trace-1"},
        },
        {"scope": "session", "allowed": True},
    )
    assert out["ok"] is True
    assert out["job_id"] == "job-1"
    assert out["status"] == "done"
    assert out["reused"] is True
    assert out["reuse_reason"] == "same_payload"
    assert out["request_id"] == "req-1"
    assert out["trace_id"] == "trace-1"


def test_build_generate_async_queued_response_keeps_workspace_and_admission():
    out = actions_generate_view.build_generate_async_queued_response(
        job_id="job-2",
        workspace_dir="/tmp/ws",
        session_id="sess-1",
        admission_detail={"scope": "session", "allowed": True},
        request_id="req-2",
        trace_id="trace-2",
    )
    assert out["ok"] is True
    assert out["status"] == "queued"
    assert out["workspace_dir"] == "/tmp/ws"
    assert out["session_id"] == "sess-1"
    assert out["admission"]["scope"] == "session"
    assert out["request_id"] == "req-2"
    assert out["trace_id"] == "trace-2"
