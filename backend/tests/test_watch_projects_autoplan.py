from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "watch_projects_autoplan.py"
    spec = importlib.util.spec_from_file_location("watch_projects_autoplan_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_write_state_records_queue_counts(tmp_path: Path, monkeypatch):
    watcher = _load_module()
    state_path = tmp_path / "watcher_state.json"
    monkeypatch.setattr(watcher, "_state_file", lambda: state_path)
    watch_root = tmp_path / "projects"
    inbox = watch_root / "inbox"
    work = watch_root / "work"
    done = watch_root / "done"
    failed = watch_root / "failed"
    for folder in (inbox, work, done, failed):
        folder.mkdir(parents=True, exist_ok=True)
    (inbox / "alpha").mkdir()
    (work / "beta").mkdir()
    (done / "gamma").mkdir()
    (failed / "delta").mkdir()
    (inbox / ".ignored").mkdir()

    watcher._write_state(
        watch_root=watch_root,
        inbox_dir=inbox,
        work_dir=work,
        done_dir=done,
        failed_dir=failed,
        status="running",
        last_action="processing",
        last_project_id="p-001",
        last_project_name="示例项目",
        last_error="",
        record_event=True,
        event_kind="processing",
    )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["status"] == "running"
    assert data["last_action"] == "processing"
    assert data["last_project_id"] == "p-001"
    assert data["last_project_name"] == "示例项目"
    assert data["watch_root"] == str(watch_root)
    assert data["inbox_count"] == 1
    assert data["work_count"] == 1
    assert data["done_count"] == 1
    assert data["failed_count"] == 1
    assert data["recent"][0]["kind"] == "processing"
    assert "示例项目" in data["recent"][0]["summary"]


def test_write_state_deduplicates_same_recent_event(tmp_path: Path, monkeypatch):
    watcher = _load_module()
    state_path = tmp_path / "watcher_state.json"
    monkeypatch.setattr(watcher, "_state_file", lambda: state_path)
    watch_root = tmp_path / "projects"
    inbox = watch_root / "inbox"
    work = watch_root / "work"
    done = watch_root / "done"
    failed = watch_root / "failed"
    for folder in (inbox, work, done, failed):
        folder.mkdir(parents=True, exist_ok=True)

    for _ in range(2):
        watcher._write_state(
            watch_root=watch_root,
            inbox_dir=inbox,
            work_dir=work,
            done_dir=done,
            failed_dir=failed,
            status="idle",
            last_action="startup",
            record_event=True,
            event_kind="startup",
        )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(data["recent"]) == 1
    assert data["recent"][0]["kind"] == "startup"


def test_try_acquire_process_lock(tmp_path: Path, monkeypatch):
    watcher = _load_module()
    monkeypatch.setattr(watcher, "_lock_file", lambda: tmp_path / "watcher.lock")
    monkeypatch.setattr(watcher, "_PROCESS_LOCK_FH", None)
    assert watcher._try_acquire_process_lock() is True
    assert watcher._PROCESS_LOCK_FH is not None


def test_main_skips_when_process_lock_held(monkeypatch):
    watcher = _load_module()
    monkeypatch.setattr(watcher, "_try_acquire_process_lock", lambda: False)
    seen: list[str] = []
    monkeypatch.setattr(watcher, "_log", lambda msg: seen.append(str(msg)))
    monkeypatch.setattr(sys, "argv", ["watch_projects_autoplan.py"])
    assert watcher.main() == 0
    assert any("process lock already held" in item for item in seen)
