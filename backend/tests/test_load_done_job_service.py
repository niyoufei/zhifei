from __future__ import annotations

import pytest

from backend.zhifei_autoplan import load_done_job_service
from backend.zhifei_autoplan.result_read_service import ResultReadBundle


def test_load_done_job_variants_rejects_missing_job():
    with pytest.raises(load_done_job_service.LoadDoneJobFailure) as exc:
        load_done_job_service.load_done_job_variants(
            job_id="job-missing",
            workspace_dir="/tmp/ws",
            get_job_fn=lambda *args, **kwargs: None,
            result_loader_fn=lambda result: None,
        )

    assert exc.value.code == "job_not_found"
    assert exc.value.message == "job not found"
    assert exc.value.next_action == "check job_id or workspace scope"
    assert exc.value.extra is None


def test_load_done_job_variants_rejects_not_done_job():
    with pytest.raises(load_done_job_service.LoadDoneJobFailure) as exc:
        load_done_job_service.load_done_job_variants(
            job_id="job-running",
            workspace_dir="/tmp/ws",
            get_job_fn=lambda *args, **kwargs: {"status": "running"},
            result_loader_fn=lambda result: None,
        )

    assert exc.value.code == "job_not_done"
    assert exc.value.message == "job not done: running"
    assert exc.value.extra == {"status": "running"}


def test_load_done_job_variants_returns_loaded_bundle():
    out = load_done_job_service.load_done_job_variants(
        job_id="job-done",
        workspace_dir="/tmp/ws",
        get_job_fn=lambda *args, **kwargs: {"status": "done", "result": {"json": "/tmp/result.json"}},
        result_loader_fn=lambda result: ResultReadBundle(
            json_path="/tmp/result.json",
            data={"variants": [{"variant_id": 1}]},
            variants=[{"variant_id": 1}],
        ),
    )

    assert out.job["status"] == "done"
    assert out.result == {"json": "/tmp/result.json"}
    assert out.data == {"variants": [{"variant_id": 1}]}
    assert out.variants == [{"variant_id": 1}]
