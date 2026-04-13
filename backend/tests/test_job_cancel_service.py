from __future__ import annotations

from backend.zhifei_autoplan import job_cancel_service


def test_cancel_job_returns_terminal_status_without_side_effects():
    kill_calls: list[tuple[int, int]] = []
    update_calls: list[tuple[tuple, dict]] = []

    out = job_cancel_service.cancel_job(
        job_id="job-1",
        workspace_dir="/tmp/ws",
        job={"status": "done"},
        kill_fn=lambda pid, sig: kill_calls.append((pid, sig)),
        update_job_fn=lambda *args, **kwargs: update_calls.append((args, kwargs)) or {},
        build_response_fn=lambda **kwargs: kwargs,
    )

    assert out == {"job_id": "job-1", "status": "done"}
    assert kill_calls == []
    assert update_calls == []


def test_cancel_job_kills_worker_and_updates_status():
    kill_calls: list[tuple[int, int]] = []
    update_calls: list[tuple[tuple, dict]] = []

    out = job_cancel_service.cancel_job(
        job_id="job-2",
        workspace_dir="/tmp/ws",
        job={"status": "running", "worker": {"pid": 23456}},
        kill_fn=lambda pid, sig: kill_calls.append((pid, sig)),
        update_job_fn=lambda *args, **kwargs: update_calls.append((args, kwargs)) or {},
        build_response_fn=lambda **kwargs: kwargs,
    )

    assert out == {"job_id": "job-2", "status": "cancelled"}
    assert kill_calls == [(23456, 15)]
    assert update_calls == [
        (("job-2",), {"workspace_dir": "/tmp/ws", "status": "cancelled", "error": "cancelled_by_user"})
    ]


def test_cancel_job_still_updates_when_kill_fails():
    update_calls: list[tuple[tuple, dict]] = []

    def _raise_kill(pid: int, sig: int):
        raise ProcessLookupError(f"{pid}:{sig}")

    out = job_cancel_service.cancel_job(
        job_id="job-3",
        workspace_dir="/tmp/ws",
        job={"status": "queued", "worker": {"pid": 34567}},
        kill_fn=_raise_kill,
        update_job_fn=lambda *args, **kwargs: update_calls.append((args, kwargs)) or {},
        build_response_fn=lambda **kwargs: kwargs,
    )

    assert out == {"job_id": "job-3", "status": "cancelled"}
    assert update_calls == [
        (("job-3",), {"workspace_dir": "/tmp/ws", "status": "cancelled", "error": "cancelled_by_user"})
    ]
