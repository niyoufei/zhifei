from __future__ import annotations

from backend.app.core import actions_recent_view


def test_jobs_sla_summary_aggregates_terminal_rows_only():
    summary = actions_recent_view.jobs_sla_summary(
        [
            {
                "status": "done",
                "sla": {
                    "total_seconds": 10,
                    "stages": [
                        {"name": "variant_running", "duration_sec": 4},
                        {"name": "exporting", "duration_sec": 6},
                    ],
                },
            },
            {
                "status": "failed",
                "sla": {
                    "total_seconds": 30,
                    "stages": [
                        {"name": "variant_running", "duration_sec": 12},
                        {"name": "exporting", "duration_sec": 18},
                    ],
                },
            },
            {
                "status": "running",
                "sla": {
                    "total_seconds": 999,
                    "stages": [
                        {"name": "variant_running", "duration_sec": 999},
                    ],
                },
            },
        ],
        limit=200,
    )
    assert summary["window"] == {"limit": 200, "terminal_jobs": 2}
    assert summary["total_latency"]["count"] == 2
    assert summary["total_latency"]["p50_sec"] == 20.0
    assert summary["stage_latency"]["variant_running"]["count"] == 2
    assert summary["stage_latency"]["variant_running"]["p50_sec"] == 8.0
    assert summary["stage_latency"]["exporting"]["p95_sec"] == 17.4
