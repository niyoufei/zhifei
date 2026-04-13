from __future__ import annotations

import pytest

from backend.zhifei_autoplan import download_request_service


def test_resolve_download_request_rejects_not_done_job():
    with pytest.raises(download_request_service.DownloadRequestFailure) as exc:
        download_request_service.resolve_download_request(
            job_id="job-1",
            job={"status": "running"},
            result={},
            kind="docx",
            variant=0,
            build_download_resolution_fn=lambda **kwargs: {},
        )

    assert exc.value.code == "job_not_done"
    assert exc.value.message == "job not done: running"
    assert exc.value.extra == {"status": "running", "kind": "docx", "variant": 1}


def test_resolve_download_request_rejects_invalid_kind():
    with pytest.raises(download_request_service.DownloadRequestFailure) as exc:
        download_request_service.resolve_download_request(
            job_id="job-2",
            job={"status": "done"},
            result={},
            kind="pdf",
            variant=2,
            build_download_resolution_fn=lambda **kwargs: {
                "requested_variant": 2,
                "valid_kind": False,
                "allowed_kinds": ["docx", "json"],
            },
        )

    assert exc.value.code == "invalid_artifact_kind"
    assert exc.value.extra == {"kind": "pdf", "variant": 2, "allowed_kinds": ["docx", "json"]}


def test_resolve_download_request_rejects_missing_artifact():
    with pytest.raises(download_request_service.DownloadRequestFailure) as exc:
        download_request_service.resolve_download_request(
            job_id="job-3",
            job={"status": "done"},
            result={},
            kind="docx",
            variant=1,
            build_download_resolution_fn=lambda **kwargs: {
                "requested_variant": 1,
                "valid_kind": True,
                "path_exists": False,
                "path": "/tmp/missing.docx",
                "download_index": {"docx": {"exists": False}},
            },
        )

    assert exc.value.code == "artifact_not_found"
    assert exc.value.extra == {
        "kind": "docx",
        "variant": 1,
        "path": "/tmp/missing.docx",
        "download_index": {"docx": {"exists": False}},
    }


def test_resolve_download_request_returns_ready_resolution():
    out = download_request_service.resolve_download_request(
        job_id="job-4",
        job={"status": "done"},
        result={},
        kind="docx",
        variant=1,
        build_download_resolution_fn=lambda **kwargs: {
            "requested_variant": 1,
            "valid_kind": True,
            "path_exists": True,
            "path": "/tmp/ready.docx",
            "media_type": "application/docx",
            "filename": "job-4-docx-1",
        },
    )

    assert out["path"] == "/tmp/ready.docx"
    assert out["filename"] == "job-4-docx-1"
