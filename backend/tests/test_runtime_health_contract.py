from __future__ import annotations

import json


def test_livez_is_constant_time_and_does_not_touch_diagnostics(monkeypatch) -> None:
    import asyncio

    from backend.app import main
    from backend.zhifei_autoplan import job_store, local_job_queue

    monkeypatch.setattr(
        main,
        "_RELEASE_IDENTITY_AT_START",
        {
            "release_id": "release-livez",
            "manifest_digest": "a" * 64,
            "source_digest": "b" * 64,
            "runtime_digest": "c" * 64,
        },
    )
    monkeypatch.setattr(
        main,
        "_offline_provider_admission_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("livez touched provider diagnostics")
        ),
    )
    monkeypatch.setattr(
        job_store,
        "job_runtime_counts",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("livez scanned jobs")
        ),
    )
    monkeypatch.setattr(
        local_job_queue,
        "local_queue_snapshot",
        lambda: (_ for _ in ()).throw(AssertionError("livez read the queue")),
    )

    result = asyncio.run(main.livez())

    assert result["ok"] is True
    assert result["release_id"] == "release-livez"
    assert result["manifest_digest"] == "a" * 64
    assert result["source_digest"] == "b" * 64
    assert result["runtime_digest"] == "c" * 64


def test_health_exposes_build_queue_and_job_telemetry(monkeypatch) -> None:
    from backend.app import main
    from backend.zhifei_autoplan import job_store, local_job_queue

    monkeypatch.setattr(
        main,
        "_RUNTIME_IDENTITY_AT_START",
        {"build_sha": "a" * 40, "dirty": True},
    )
    monkeypatch.setattr(
        main,
        "_offline_provider_admission_status",
        lambda detailed=False: {
            "configured": True,
            "admitted": False,
            "state": "configured_not_admitted",
            "generation_allowed": False,
            "degraded": False,
        },
    )
    monkeypatch.setattr(
        job_store,
        "job_runtime_counts",
        lambda stale_after_seconds=60: {
            "active": 1,
            "queued": 0,
            "running": 1,
            "stale": 0,
            "total": 2,
        },
    )
    monkeypatch.setattr(
        local_job_queue,
        "local_queue_snapshot",
        lambda: {"queue_depth": 0, "worker_alive": True},
    )

    result = main.health()

    assert result["ok"] is True
    assert result["build_sha"] == "a" * 40
    assert result["dirty"] is True
    assert result["jobs"]["active"] == 1
    assert result["queue"]["worker_alive"] is True
    assert result["self_heal"]["mode"] == "opt_in"
    assert result["provider_admission"]["state"] == "configured_not_admitted"


def test_capabilities_are_project_scoped(monkeypatch) -> None:
    from backend.app import main
    from backend.zhifei_autoplan import boq_store, tender_store

    monkeypatch.setattr(
        tender_store,
        "load_tender_matrix",
        lambda project_id=None: {"project_id": project_id} if project_id == "p1" else None,
    )
    monkeypatch.setattr(
        boq_store,
        "load_boq_data",
        lambda project_id=None: {"project_id": project_id} if project_id == "p1" else None,
    )

    result = main.capabilities(project_id="p1")

    assert result["project_id"] == "p1"
    assert result["tender_matrix_loaded"] is True
    assert result["boq_loaded"] is True


def test_health_exposes_frozen_sealed_release_identity(monkeypatch) -> None:
    from backend.app import main

    monkeypatch.setattr(
        main,
        "_RELEASE_IDENTITY_AT_START",
        {
            "release_id": "release-abc123",
            "manifest_digest": "a" * 64,
            "source_digest": "b" * 64,
            "runtime_digest": "c" * 64,
            "release_root": "/tmp/sealed-release",
            "managed": True,
            "mode": "sealed_release",
        },
    )
    monkeypatch.setattr(main, "_SUPERVISOR_STATE_FILE_AT_START", "")

    result = main.health()

    assert result["release_id"] == "release-abc123"
    assert result["manifest_digest"] == "a" * 64
    assert result["source_digest"] == "b" * 64
    assert result["runtime_digest"] == "c" * 64
    assert result["release_root"] == "/tmp/sealed-release"
    assert result["runtime_mode"] == "sealed_release"
    assert result["release_managed"] is True
    assert result["supervisor"] == {
        "managed": True,
        "available": False,
        "status": "unmanaged",
    }


def test_health_projects_only_safe_supervisor_state(monkeypatch, tmp_path) -> None:
    from backend.app import main

    state_file = tmp_path / "supervisor.json"
    state_file.write_text(
        json.dumps(
            {
                "status": "degraded",
                "release_id": "release-1",
                "backend_pid": 123,
                "ui_pid": 456,
                "restart_count_window": 0,
                "last_error_code": None,
                "health_degraded": True,
                "consecutive_health_failures": 2,
                "first_health_failure_at": 1200.0,
                "last_probe_error_code": "SUPERVISOR_BACKEND_HEALTH_TIMEOUT",
                "updated_at": 1234.5,
                "api_key": "must-never-be-returned",
                "environment": {"ANTHROPIC_API_KEY": "must-never-be-returned"},
                "command": "must-never-be-returned",
            }
        ),
        encoding="utf-8",
    )
    state_file.chmod(0o600)
    monkeypatch.setattr(main, "_SUPERVISOR_STATE_FILE_AT_START", str(state_file))
    monkeypatch.setattr(
        main,
        "_RELEASE_IDENTITY_AT_START",
        {"managed": True, "mode": "sealed_release"},
    )

    result = main.health()["supervisor"]

    assert result["available"] is True
    assert result["status"] == "degraded"
    assert result["release_id"] == "release-1"
    assert result["health_degraded"] is True
    assert result["consecutive_health_failures"] == 2
    assert result["last_probe_error_code"] == "SUPERVISOR_BACKEND_HEALTH_TIMEOUT"
    serialized = json.dumps(result)
    assert "api_key" not in serialized.lower()
    assert "ANTHROPIC" not in serialized
    assert "must-never-be-returned" not in serialized


def test_health_rejects_overpermissive_supervisor_state(monkeypatch, tmp_path) -> None:
    from backend.app import main

    state_file = tmp_path / "supervisor.json"
    state_file.write_text('{"status":"healthy"}', encoding="utf-8")
    state_file.chmod(0o644)
    monkeypatch.setattr(main, "_SUPERVISOR_STATE_FILE_AT_START", str(state_file))

    result = main.health()["supervisor"]

    assert result["available"] is False
    assert result["status"] == "state_untrusted"
