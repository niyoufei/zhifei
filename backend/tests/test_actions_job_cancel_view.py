from __future__ import annotations

from backend.app.core import actions_job_cancel_view


def test_build_actions_job_cancel_response_normalizes_status():
    out = actions_job_cancel_view.build_actions_job_cancel_response(job_id="job-1", status=" Cancelled ")
    assert out == {"ok": True, "job_id": "job-1", "status": "cancelled"}
