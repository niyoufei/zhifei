from __future__ import annotations

from backend.app.core import actions_usage_view


def test_build_actions_usage_status_response_wraps_admission_detail():
    out = actions_usage_view.build_actions_usage_status_response(
        {"scope": "session", "requested_jobs": 0, "allowed": True}
    )
    assert out == {
        "ok": True,
        "admission": {"scope": "session", "requested_jobs": 0, "allowed": True},
    }


def test_build_actions_usage_report_response_extracts_usage_profile_and_limits():
    out = actions_usage_view.build_actions_usage_report_response(
        session_id="sess-1",
        workspace_dir="/tmp/ws",
        decision={
            "usage": {"usage_profile": {"windows": {"last_hour": {"total_tokens_total": 15}}}},
            "limits": {"config_version": "v1"},
            "warning_level": "warning",
            "warnings": [{"code": "near_limit"}],
        },
    )
    assert out == {
        "ok": True,
        "scope": "session",
        "session_id": "sess-1",
        "workspace_dir": "/tmp/ws",
        "usage_profile": {"windows": {"last_hour": {"total_tokens_total": 15}}},
        "limits": {"config_version": "v1"},
        "warning_level": "warning",
        "warnings": [{"code": "near_limit"}],
    }
