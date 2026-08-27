from __future__ import annotations

import os
from pathlib import Path

from backend.zhifei_autoplan import (
    generation_checkpoint,
    job_store,
    local_job_queue,
    runtime_events,
)


def _write_marker(marker_path: str) -> None:
    Path(marker_path).write_text("isolated", encoding="utf-8")


def _crash_worker() -> None:
    os._exit(17)


def _return_without_transition() -> None:
    return None


def _configure_runtime_roots(monkeypatch, tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    job_dir = tmp_path / "jobs"
    monkeypatch.setenv("ZF_AUTOPLAN_EVENT_DIR", str(event_dir))
    monkeypatch.setenv("ZF_AUTOPLAN_JOB_DIR", str(job_dir))
    monkeypatch.setattr(runtime_events, "EVENT_DIR", event_dir)
    monkeypatch.setattr(job_store, "JOB_DIR", job_dir)


def test_isolated_worker_runs_in_a_different_process(monkeypatch, tmp_path: Path) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    marker = tmp_path / "marker.txt"
    item = local_job_queue._WorkItem(
        job_id="a" * 32,
        callback=_write_marker,
        args=(str(marker),),
        kwargs={},
        isolated=True,
    )

    local_job_queue._run_isolated(item)

    assert marker.read_text(encoding="utf-8") == "isolated"


def test_isolated_worker_crash_preserves_api_job_as_recoverable(
    monkeypatch, tmp_path: Path
) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"project_id": "test"})
    job_store.merge_job(
        job_id,
        status="running",
        progress={"percent": 15, "phase": "generation"},
    )
    item = local_job_queue._WorkItem(
        job_id=job_id,
        callback=_crash_worker,
        args=(),
        kwargs={},
        isolated=True,
    )

    local_job_queue._run_isolated(item)

    result = job_store.get_job(job_id)
    assert result is not None
    assert result["status"] == "interrupted_recoverable"
    assert result["error"]["code"] == "JOB_WORKER_PROCESS_EXITED"
    assert result["progress"]["percent"] == 15


def test_clean_child_exit_without_terminal_transition_fails_closed(
    monkeypatch, tmp_path: Path
) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"project_id": "test"})
    job_store.transition_job(job_id, allowed_from={"queued"}, status="running")
    item = local_job_queue._WorkItem(
        job_id=job_id,
        callback=_return_without_transition,
        args=(),
        kwargs={},
        isolated=True,
    )

    local_job_queue._run_isolated(item)

    result = job_store.get_job(job_id)
    assert result is not None
    assert result["status"] == "interrupted_recoverable"
    assert result["error"]["code"] == "JOB_WORKER_RETURNED_WITHOUT_TERMINAL_STATE"


def test_isolated_terminal_revokes_lease_before_checkpoint_seal_and_cas_projects(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"project_id": "test"})
    lease = job_store.acquire_job_lease(job_id, owner_instance_id="worker-a")
    assert lease is not None
    observed: dict[str, object] = {}

    def _seal(current_job_id: str) -> list[dict[str, object]]:
        record = job_store.get_job(current_job_id) or {}
        observed["status"] = record.get("status")
        observed["attempt_id"] = record.get("attempt_id")
        observed["owner_instance_id"] = record.get("owner_instance_id")
        return [{"scope": "variant-1", "saved_chapter_count": 1}]

    monkeypatch.setattr(
        generation_checkpoint,
        "mark_checkpoint_namespace_interrupted",
        _seal,
    )

    local_job_queue._ensure_isolated_process_terminal(job_id, 17)

    record = job_store.get_job(job_id) or {}
    assert observed == {
        "status": "interrupted_recoverable",
        "attempt_id": None,
        "owner_instance_id": None,
    }
    assert record["last_attempt_id"] == lease["attempt_id"]
    assert record["progress"]["checkpoint"] == {
        "status": "interrupted_recoverable",
        "saved_chapter_count": 1,
        "scopes": [{"scope": "variant-1", "saved_chapter_count": 1}],
    }


def test_isolated_terminal_checkpoint_projection_cannot_overwrite_newer_revision(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"project_id": "test"})
    assert job_store.acquire_job_lease(job_id, owner_instance_id="worker-a") is not None

    def _seal(current_job_id: str) -> list[dict[str, object]]:
        terminal = job_store.get_job(current_job_id) or {}
        updated = job_store.transition_job(
            current_job_id,
            allowed_from={"interrupted_recoverable"},
            status="interrupted_recoverable",
            expected_revision=int(terminal["revision"]),
            progress={"newer_admin_projection": True},
        )
        assert updated is not None
        return [{"scope": "variant-1", "saved_chapter_count": 1}]

    monkeypatch.setattr(
        generation_checkpoint,
        "mark_checkpoint_namespace_interrupted",
        _seal,
    )

    local_job_queue._ensure_isolated_process_terminal(job_id, 17)

    record = job_store.get_job(job_id) or {}
    assert record["progress"]["newer_admin_projection"] is True
    assert record["progress"]["checkpoint"] == {
        "status": "interruption_seal_pending",
        "saved_chapter_count": 0,
    }


def test_isolated_terminal_checkpoint_seal_failure_is_public(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_runtime_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"project_id": "test"})
    assert job_store.acquire_job_lease(job_id, owner_instance_id="worker-a") is not None
    monkeypatch.setattr(
        generation_checkpoint,
        "mark_checkpoint_namespace_interrupted",
        lambda _job_id: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    local_job_queue._ensure_isolated_process_terminal(job_id, 17)

    record = job_store.get_job(job_id) or {}
    assert record["progress"]["checkpoint"] == {
        "status": "interruption_seal_failed",
        "saved_chapter_count": 0,
        "error_code": "CHECKPOINT_INTERRUPTION_SEAL_FAILED",
        "error_type": "OSError",
    }
