from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def test_resolve_workspace_dir_creates_session_scoped_tree(tmp_path: Path):
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", root):
        resolved = ws.resolve_workspace_dir(session_id="sess-001")
        assert resolved == root / "sess-001"
        paths = ws.workspace_paths(resolved, session_id="sess-001")
        assert paths["uploads"].is_dir()
        assert paths["build"].is_dir()
        assert paths["media"].is_dir()
        assert paths["kg_dir"].is_dir()
        assert (resolved / ws.WORKSPACE_META_FILE).exists()


def test_resolve_workspace_dir_rejects_cross_workspace_path(tmp_path: Path):
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    bad_path = tmp_path / "other-root" / "sess-002"
    with patch.object(ws, "WORKSPACE_ROOT", root):
        with pytest.raises(ValueError):
            ws.resolve_workspace_dir(session_id="sess-002", workspace_dir=bad_path)


def test_cleanup_expired_workspaces_removes_stale_workspace(tmp_path: Path):
    from backend.zhifei_autoplan import workspace as ws

    root = tmp_path / "workspaces"
    old_ts = time.time() - 13 * 3600
    with patch.object(ws, "WORKSPACE_ROOT", root):
        stale = ws.resolve_workspace_dir(session_id="stale-session")
        active = ws.resolve_workspace_dir(session_id="active-session")
        meta_path = stale / ws.WORKSPACE_META_FILE
        meta_path.write_text(
            json.dumps(
                {
                    "created_at": old_ts,
                    "last_seen_at": old_ts,
                    "session_id": "stale-session",
                    "workspace_dir": str(stale),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        report = ws.cleanup_expired_workspaces(max_age_seconds=12 * 3600, exclude_workspace=active)
        assert report["removed_count"] == 1
        assert str(stale) in report["removed"]
        assert not stale.exists()
        assert active.exists()
