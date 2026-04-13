from __future__ import annotations

import json

from backend.app.core import actions_recent_view


def test_load_watcher_state_returns_empty_when_missing(tmp_path):
    missing = tmp_path / "missing.json"
    assert actions_recent_view.load_watcher_state(missing) == {}


def test_load_watcher_state_returns_dict_only(tmp_path):
    state_path = tmp_path / "watcher_state.json"
    state_path.write_text(json.dumps({"status": "idle", "watch_root": "/tmp/projects"}), encoding="utf-8")
    assert actions_recent_view.load_watcher_state(state_path)["status"] == "idle"

    state_path.write_text(json.dumps(["bad-shape"]), encoding="utf-8")
    assert actions_recent_view.load_watcher_state(state_path) == {}
