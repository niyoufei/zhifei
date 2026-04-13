from __future__ import annotations

from backend.zhifei_autoplan import generate_queue_service


def test_queue_generate_job_builds_variant_plan_and_returns_queued_response():
    calls: list[tuple[str, object]] = []

    def fake_create_job(payload, **kwargs):
        calls.append(("create_job", dict(payload)))
        return "job-1"

    def fake_append_resource_event(event, **fields):
        calls.append((event, dict(fields)))
        return "resource.jsonl"

    def fake_spawn(job_id, *, workspace_dir=None):
        calls.append(("spawn", {"job_id": job_id, "workspace_dir": workspace_dir}))
        return 99999, "/tmp/worker.log"

    def fake_update_job(job_id, **kwargs):
        calls.append(("update_job", {"job_id": job_id, **kwargs}))
        return None

    out = generate_queue_service.queue_generate_job(
        payload={"topic": "测试", "request_id": "req-1", "trace_id": "trace-1", "variants": 9},
        workspace_dir="/tmp/ws",
        session_id="sess-1",
        request_signature="sig-1",
        admission={"warning_level": "none", "warnings": [], "degrade_plan": {"applied": False}},
        create_job_fn=fake_create_job,
        append_resource_event_fn=fake_append_resource_event,
        spawn_generate_worker_fn=fake_spawn,
        update_job_fn=fake_update_job,
        append_worker_log_fn=lambda *args, **kwargs: None,
        build_variant_plan_fn=lambda payload: [{"variant_id": 1}, {"variant_id": 2}],
        admission_http_detail_fn=lambda admission: {"scope": "session", "warning_level": admission.get("warning_level")},
        build_queued_response_fn=lambda **kwargs: {"ok": True, **kwargs},
    )

    assert out["ok"] is True
    assert out["job_id"] == "job-1"
    assert out["workspace_dir"] == "/tmp/ws"
    created_payload = calls[0][1]
    assert created_payload["_variant_ids"] == [1, 2]
    assert created_payload["variants"] == 2
    assert calls[1][0] == "job_queued"
    assert calls[2][0] == "spawn"
    assert calls[3][0] == "update_job"
