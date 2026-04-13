from __future__ import annotations

import pytest
from unittest.mock import patch

from backend.zhifei_autoplan import generate_request_service
from backend.zhifei_autoplan.generate_admission_service import GenerateAdmissionResolution
from backend.zhifei_autoplan.generate_queue_service import GenerateWorkerSpawnFailure


class _Prepared:
    def __init__(self, payload, request_signature):
        self.payload = payload
        self.request_signature = request_signature


def test_execute_generate_request_returns_reused_response_without_queue():
    called: list[str] = []

    out = generate_request_service.execute_generate_request(
        raw_payload={"topic": "t-1"},
        session_id="sess-1",
        workspace_dir="/tmp/ws",
        prepare_payload_fn=lambda raw: _Prepared({"topic": raw["topic"]}, "sig-1"),
        resolve_admission_fn=lambda **kwargs: GenerateAdmissionResolution(
            reusable_response={"ok": True, "reused": True},
            admission=None,
        ),
        queue_generate_job_fn=lambda **kwargs: called.append("queue") or {},
        build_payload_prepare_error_fn=lambda reason: {"code": "payload_prepare_failed", "reason": reason},
        build_worker_spawn_error_fn=lambda **kwargs: {"code": "worker_spawn_failed", **kwargs},
    )

    assert out == {"ok": True, "reused": True}
    assert called == []


def test_execute_generate_request_raises_payload_prepare_failure():
    with pytest.raises(generate_request_service.GenerateRequestPayloadPrepareFailure) as exc:
        generate_request_service.execute_generate_request(
            raw_payload={"topic": "t-2"},
            session_id="sess-2",
            workspace_dir="/tmp/ws",
            prepare_payload_fn=lambda raw: (_ for _ in ()).throw(RuntimeError("text_provider_not_configured:openai")),
            resolve_admission_fn=lambda **kwargs: None,
            queue_generate_job_fn=lambda **kwargs: {},
            build_payload_prepare_error_fn=lambda reason: {"code": "provider_not_configured", "reason": reason},
            build_worker_spawn_error_fn=lambda **kwargs: {"code": "worker_spawn_failed", **kwargs},
        )

    assert exc.value.error_spec == {
        "code": "provider_not_configured",
        "reason": "text_provider_not_configured:openai",
    }


def test_execute_generate_request_raises_worker_spawn_failure():
    with pytest.raises(generate_request_service.GenerateRequestWorkerSpawnFailure) as exc:
        generate_request_service.execute_generate_request(
            raw_payload={"topic": "t-3"},
            session_id="sess-3",
            workspace_dir="/tmp/ws",
            prepare_payload_fn=lambda raw: _Prepared({"topic": raw["topic"]}, "sig-3"),
            resolve_admission_fn=lambda **kwargs: GenerateAdmissionResolution(
                reusable_response=None,
                admission={"allowed": True},
            ),
            queue_generate_job_fn=lambda **kwargs: (_ for _ in ()).throw(
                GenerateWorkerSpawnFailure(
                    job_id="job-3",
                    request_id="req-3",
                    trace_id="trace-3",
                    worker_log_path="/tmp/worker.log",
                    cause=RuntimeError("boom"),
                )
            ),
            build_payload_prepare_error_fn=lambda reason: {"code": "payload_prepare_failed", "reason": reason},
            build_worker_spawn_error_fn=lambda **kwargs: {"code": "worker_spawn_failed", **kwargs},
        )

    assert exc.value.error_spec == {
        "code": "worker_spawn_failed",
        "job_id": "job-3",
        "request_id": "req-3",
        "trace_id": "trace-3",
        "worker_log_path": "/tmp/worker.log",
    }


def test_execute_generate_request_queues_when_admission_allows():
    out = generate_request_service.execute_generate_request(
        raw_payload={"topic": "t-4"},
        session_id="sess-4",
        workspace_dir="/tmp/ws",
        prepare_payload_fn=lambda raw: _Prepared({"topic": raw["topic"]}, "sig-4"),
        resolve_admission_fn=lambda **kwargs: GenerateAdmissionResolution(
            reusable_response=None,
            admission={"allowed": True, "warning_level": "none"},
        ),
        queue_generate_job_fn=lambda **kwargs: {
            "ok": True,
            "request_signature": kwargs["request_signature"],
            "topic": kwargs["payload"]["topic"],
        },
        build_payload_prepare_error_fn=lambda reason: {"code": "payload_prepare_failed", "reason": reason},
        build_worker_spawn_error_fn=lambda **kwargs: {"code": "worker_spawn_failed", **kwargs},
    )

    assert out == {"ok": True, "request_signature": "sig-4", "topic": "t-4"}


def test_translate_generate_request_failure_maps_payload_prepare():
    exc = generate_request_service.GenerateRequestPayloadPrepareFailure(
        error_spec={
            "status_code": 503,
            "code": "provider_not_configured",
            "message": "provider missing",
            "stage": "payload_prepare",
        },
        cause=RuntimeError("boom"),
    )

    out = generate_request_service.translate_generate_request_failure(exc)

    assert out == generate_request_service.GenerateRequestFailurePlan(
        status_code=503,
        error_spec={
            "status_code": 503,
            "code": "provider_not_configured",
            "message": "provider missing",
            "stage": "payload_prepare",
        },
        cause=exc.cause,
    )


def test_translate_generate_request_failure_maps_admission_rejected():
    exc = generate_request_service.generate_admission_core.GenerateAdmissionRejected(
        {
            "log_anchor": "actions.admission.1",
            "code": "job_limit_reached",
            "message": "too many jobs",
        }
    )

    out = generate_request_service.translate_generate_request_failure(exc)

    assert out == generate_request_service.GenerateRequestFailurePlan(
        status_code=429,
        detail={
            "log_anchor": "actions.admission.1",
            "code": "job_limit_reached",
            "message": "too many jobs",
        },
        warning_log={
            "log_anchor": "actions.admission.1",
            "code": "job_limit_reached",
            "detail": {
                "log_anchor": "actions.admission.1",
                "code": "job_limit_reached",
                "message": "too many jobs",
            },
        },
    )


def test_translate_generate_request_failure_maps_worker_spawn():
    exc = generate_request_service.GenerateRequestWorkerSpawnFailure(
        error_spec={
            "status_code": 500,
            "code": "worker_spawn_failed",
            "message": "spawn failed",
            "stage": "worker_spawn",
            "job_id": "job-1",
        },
        cause=RuntimeError("boom"),
    )

    out = generate_request_service.translate_generate_request_failure(exc)

    assert out == generate_request_service.GenerateRequestFailurePlan(
        status_code=500,
        error_spec={
            "status_code": 500,
            "code": "worker_spawn_failed",
            "message": "spawn failed",
            "stage": "worker_spawn",
            "job_id": "job-1",
        },
        cause=exc.cause,
    )


def test_execute_generate_request_from_runtime_wires_prepare_admission_and_queue():
    seen: dict[str, object] = {}

    with patch(
        "backend.zhifei_autoplan.generate_request_service.generate_admission_core.resolve_generate_admission"
    ) as mock_resolve, patch(
        "backend.zhifei_autoplan.generate_request_service.generate_queue_core.queue_generate_job"
    ) as mock_queue, patch(
        "backend.zhifei_autoplan.generate_payload_service.prepare_generate_payload"
    ) as mock_prepare:
        mock_prepare.return_value = _Prepared({"topic": "wired"}, "sig-wired")
        mock_resolve.return_value = GenerateAdmissionResolution(
            reusable_response=None,
            admission={"allowed": True, "warning_level": "none"},
        )
        mock_queue.return_value = {"ok": True, "job_id": "job-wired"}

        out = generate_request_service.execute_generate_request_from_runtime(
            raw_payload={"topic": "wired"},
            session_id="sess-wired",
            workspace_dir="/tmp/ws-wired",
            prepare_runtime_payload_fn=lambda payload: seen.setdefault("prepare_runtime_payload", payload) or payload,
            attach_contract_stamp_fn=lambda payload: seen.setdefault("attach_contract_stamp", payload),
            compute_job_signature_fn=lambda payload: "sig",
            find_reusable_job_fn=lambda **kwargs: None,
            evaluate_job_admission_fn=lambda **kwargs: {"allowed": True},
            admission_http_detail_fn=lambda admission: {"admission": admission},
            append_resource_event_fn=lambda *args, **kwargs: None,
            build_reused_response_fn=lambda **kwargs: {"ok": True},
            build_rejection_event_fn=lambda **kwargs: {"event": "reject"},
            build_rejected_detail_fn=lambda **kwargs: {"detail": "reject"},
            apply_admission_degrade_fn=lambda admission, payload: admission,
            new_log_anchor_fn=lambda stage: f"log:{stage}",
            create_job_fn=lambda *args, **kwargs: "job-id",
            spawn_generate_worker_fn=lambda *args, **kwargs: {"pid": 1},
            update_job_fn=lambda *args, **kwargs: None,
            append_worker_log_fn=lambda *args, **kwargs: None,
            build_variant_plan_fn=lambda payload: [{"variant_id": 1}],
            build_queued_response_fn=lambda **kwargs: {"ok": True, "queued": True},
            build_payload_prepare_error_fn=lambda reason: {"code": "payload_prepare_failed", "reason": reason},
            build_worker_spawn_error_fn=lambda **kwargs: {"code": "worker_spawn_failed", **kwargs},
        )

    assert out == {"ok": True, "job_id": "job-wired"}
    mock_prepare.assert_called_once()
    prepare_kwargs = mock_prepare.call_args.kwargs
    assert prepare_kwargs["raw_payload"] == {"topic": "wired"}
    mock_resolve.assert_called_once()
    assert mock_resolve.call_args.kwargs["payload"] == {"topic": "wired"}
    assert mock_resolve.call_args.kwargs["session_id"] == "sess-wired"
    assert mock_resolve.call_args.kwargs["workspace_dir"] == "/tmp/ws-wired"
    mock_queue.assert_called_once()
    assert mock_queue.call_args.kwargs["payload"] == {"topic": "wired"}
    assert mock_queue.call_args.kwargs["request_signature"] == "sig-wired"
