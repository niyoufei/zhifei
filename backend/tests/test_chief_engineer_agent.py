from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan import chief_engineer_agent as cea


def test_to_int_default():
    assert cea._to_int("12", 3) == 12
    assert cea._to_int("x", 3) == 3


def test_write_state(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cea, "_state_file", lambda: tmp_path / "state.json")
    cea._write_state(
        backend_listener=1,
        web_listener=0,
        backend_health=1,
        web_health=0,
        action="restart_web_ui",
        maintenance={"job_housekeep": {"stale_fixed": 1}},
        recent=[{"timestamp": "2026-03-19 16:10:00", "kind": "restart_web_ui", "summary": "web unhealthy -> restart"}],
    )
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data["backend_listener"] == 1
    assert data["web_listener"] == 0
    assert data["last_action"] == "restart_web_ui"
    assert data["maintenance"]["job_housekeep"]["stale_fixed"] == 1
    assert data["recent"][0]["kind"] == "restart_web_ui"


def test_run_job_housekeeping(monkeypatch):
    from backend.zhifei_autoplan import job_store

    monkeypatch.setattr(job_store, "mark_stale_running_jobs", lambda lease_seconds=0, limit=0: 2)
    monkeypatch.setattr(job_store, "cleanup_jobs", lambda older_than_seconds=0, archive=True: 3)

    out = cea._run_job_housekeeping()
    assert out["stale_fixed"] == 2
    assert out["removed"] == 3
    assert out["changed"] is True


def test_run_self_evolution_maintenance(monkeypatch):
    from backend.zhifei_autoplan import self_evolution

    monkeypatch.setattr(
        self_evolution,
        "run_self_evolution_maintenance",
        lambda: {
            "enabled": True,
            "runtime_budget_profile": {"changed": True, "entry_count": 5, "maintenance": {"pruned_entry_count": 1}},
            "task_parallelism_profile": {"changed": False, "entry_count": 2, "maintenance": {"pruned_entry_count": 0}},
        },
    )

    out = cea._run_self_evolution_maintenance()
    assert out["enabled"] is True
    assert out["runtime_budget_profile"]["changed"] is True
    assert out["runtime_budget_profile"]["entry_count"] == 5
    assert out["task_parallelism_profile"]["changed"] is False


def test_load_chief_engineer_state(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cea, "_state_file", lambda: tmp_path / "state.json")
    (tmp_path / "state.json").write_text(
        json.dumps({"timestamp": "2026-03-19 11:03:49", "last_action": "noop"}, ensure_ascii=False),
        encoding="utf-8",
    )
    data = cea.load_chief_engineer_state()
    assert data["timestamp"] == "2026-03-19 11:03:49"
    assert data["last_action"] == "noop"


def test_try_acquire_process_lock(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cea, "_lock_file", lambda: tmp_path / "chief.lock")
    monkeypatch.setattr(cea, "_PROCESS_LOCK_FH", None)
    assert cea._try_acquire_process_lock() is True
    assert cea._PROCESS_LOCK_FH is not None


def test_start_chief_engineer_agent_skips_when_process_lock_held(monkeypatch):
    monkeypatch.setattr(cea, "_AGENT_THREAD", None)
    monkeypatch.setattr(cea, "_try_acquire_process_lock", lambda: False)
    seen: list[str] = []
    monkeypatch.setattr(cea, "_append_log", lambda msg: seen.append(str(msg)))
    cea.start_chief_engineer_agent()
    assert any("process lock already held" in item for item in seen)


def test_push_recent_event_keeps_recent_limit():
    events = cea._coerce_recent_items([])
    for idx in range(10):
        cea._push_recent_event(events, kind="job_housekeep", summary=f"event-{idx}")
    assert len(events) == 6
    assert events[0]["summary"] == "event-4"
    assert events[-1]["summary"] == "event-9"


def test_web_http_ok_uses_streamlit_health_endpoint(monkeypatch):
    seen: list[str] = []

    def _fake_http_ok(url: str, timeout: float = 3.0) -> bool:
        seen.append(url)
        return True

    monkeypatch.setattr(cea, "_http_ok", _fake_http_ok)
    assert cea._web_http_ok("127.0.0.1", 8501) is True
    assert seen == ["http://127.0.0.1:8501/_stcore/health"]


def test_web_start_grace_active_uses_streamlit_pid_mtime(monkeypatch, tmp_path: Path):
    runtime_dir = tmp_path / ".runtime" / "docgen"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    pid_file = runtime_dir / "streamlit.pid"
    pid_file.write_text("12345", encoding="utf-8")
    monkeypatch.setattr(cea, "_runtime_dir", lambda: runtime_dir)
    monkeypatch.setattr(cea.time, "time", lambda: float(pid_file.stat().st_mtime) + 5.0)
    assert cea._web_start_grace_active(20) is True
    monkeypatch.setattr(cea.time, "time", lambda: float(pid_file.stat().st_mtime) + 25.0)
    assert cea._web_start_grace_active(20) is False


def test_start_streamlit_writes_runtime_pid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cea, "_project_root", lambda: tmp_path)
    runtime_dir = tmp_path / ".runtime" / "docgen"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cea, "_runtime_dir", lambda: runtime_dir)

    class _DummyProc:
        pid = 12345

    seen: dict[str, object] = {}

    def _fake_popen(args, cwd=None, env=None, stdout=None, stderr=None, start_new_session=None):
        seen["args"] = args
        return _DummyProc()

    monkeypatch.setattr(cea.subprocess, "Popen", _fake_popen)
    monkeypatch.setenv("PYTHON", "/usr/bin/python3")

    cea._start_streamlit()

    pid_file = runtime_dir / "streamlit.pid"
    assert pid_file.read_text(encoding="utf-8") == "12345"
