from __future__ import annotations

import json

import pytest


def test_runtime_event_journal_is_append_only_and_redacted(monkeypatch, tmp_path) -> None:
    from backend.zhifei_autoplan import runtime_events

    monkeypatch.setattr(runtime_events, "EVENT_DIR", tmp_path / "events")
    job_id = "a" * 32
    runtime_events.append_runtime_event(
        job_id,
        "provider_attempt_started",
        provider="openai",
        api_key="sk-proj-should-never-persist",
        prompt="private project text",
    )
    runtime_events.append_runtime_event(job_id, "provider_attempt_finished", ok=False)

    path = runtime_events.event_journal_path(job_id)
    assert path is not None
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == [
        "provider_attempt_started",
        "provider_attempt_finished",
    ]
    raw = path.read_text(encoding="utf-8")
    assert "should-never-persist" not in raw
    assert "private project text" not in raw


def test_runtime_event_persistence_failure_is_non_fatal_and_redacted(
    monkeypatch, tmp_path
) -> None:
    from backend.zhifei_autoplan import runtime_events

    unusable_event_dir = tmp_path / "events-is-a-file"
    unusable_event_dir.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(runtime_events, "EVENT_DIR", unusable_event_dir)

    record = runtime_events.append_runtime_event(
        "b" * 32,
        "provider_attempt_finished",
        api_key="sk-proj-must-remain-redacted",
    )

    assert record["persisted"] is False
    assert record["persistence_error"] == "FileExistsError"
    assert record["api_key"] == "[REDACTED]"


def test_runtime_event_still_rejects_invalid_job_id_when_storage_is_unavailable(
    monkeypatch, tmp_path
) -> None:
    from backend.zhifei_autoplan import runtime_events

    unusable_event_dir = tmp_path / "events-is-a-file"
    unusable_event_dir.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(runtime_events, "EVENT_DIR", unusable_event_dir)

    with pytest.raises(ValueError, match="invalid job_id"):
        runtime_events.append_runtime_event("../not-a-job", "invalid")
