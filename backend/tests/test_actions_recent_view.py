from __future__ import annotations

from backend.app.core import actions_recent_view


def test_recent_job_sla_summary_uses_injected_clock_for_running_stage():
    out = actions_recent_view.recent_job_sla_summary(
        {
            "total_seconds": 48.3,
            "stages": [
                {
                    "name": "agent_ready",
                    "started_at": 100.0,
                    "ended_at": 120.0,
                    "duration_sec": 20.0,
                    "detail": "多Agent已就绪",
                },
                {
                    "name": "variant_running",
                    "started_at": 130.0,
                    "ended_at": None,
                    "duration_sec": None,
                    "detail": "方案完成进度：1/3",
                },
            ],
        },
        now_ts=150.0,
    )
    assert out["current_stage"] == "variant_running"
    assert out["current_stage_detail"] == "方案完成进度：1/3"
    assert out["current_stage_seconds"] == 20.0


def test_normalize_recent_rows_prioritizes_signal_then_recency():
    rows = actions_recent_view.normalize_recent_rows(
        [
            {"timestamp": "2026-04-12 10:00:00", "kind": "startup", "summary": "startup"},
            {"timestamp": "2026-04-12 10:05:00", "kind": "processed", "summary": "processed project=A"},
            {"timestamp": "2026-04-12 10:03:00", "kind": "error", "summary": "error project=A"},
        ]
    )
    assert [item["kind"] for item in rows] == ["error", "processed", "startup"]
