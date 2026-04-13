from __future__ import annotations

from backend.app.core import actions_download_response


DOWNLOAD_KIND_SPECS = {
    "docx": {"media_type": "application/docx"},
    "result_bundle_json": {"media_type": "application/json"},
}


def test_build_actions_download_resolution_returns_ready_artifact(tmp_path):
    artifact = tmp_path / "ready.docx"
    artifact.write_bytes(b"docx")

    out = actions_download_response.build_actions_download_resolution(
        job_id="job-1",
        result={"docx": [str(artifact)]},
        kind="docx",
        variant=1,
        download_kind_specs=DOWNLOAD_KIND_SPECS,
        download_artifact_path_fn=lambda result, kind, variant: result[kind][variant - 1],
        download_filename_fn=lambda job_id, kind, variant: f"{job_id}-{kind}-{variant}",
        build_download_index_fn=lambda job_id, result, variant: {"unused": True},
    )

    assert out["requested_variant"] == 1
    assert out["valid_kind"] is True
    assert out["path"] == str(artifact)
    assert out["path_exists"] is True
    assert out["media_type"] == "application/docx"
    assert out["filename"] == "job-1-docx-1"
    assert out["download_index"] is None


def test_build_actions_download_resolution_reports_missing_artifact_context():
    out = actions_download_response.build_actions_download_resolution(
        job_id="job-2",
        result={"docx": ["/tmp/missing.docx"]},
        kind="docx",
        variant=0,
        download_kind_specs=DOWNLOAD_KIND_SPECS,
        download_artifact_path_fn=lambda result, kind, variant: result[kind][variant - 1],
        download_filename_fn=lambda job_id, kind, variant: f"{job_id}-{kind}-{variant}",
        build_download_index_fn=lambda job_id, result, variant: {"docx": {"exists": False}, "variant": variant},
    )

    assert out["requested_variant"] == 1
    assert out["valid_kind"] is True
    assert out["path"] == "/tmp/missing.docx"
    assert out["path_exists"] is False
    assert out["download_index"] == {"docx": {"exists": False}, "variant": 1}


def test_build_actions_download_resolution_rejects_invalid_kind():
    out = actions_download_response.build_actions_download_resolution(
        job_id="job-3",
        result={},
        kind="pdf",
        variant=2,
        download_kind_specs=DOWNLOAD_KIND_SPECS,
        download_artifact_path_fn=lambda result, kind, variant: None,
        download_filename_fn=lambda job_id, kind, variant: "",
        build_download_index_fn=lambda job_id, result, variant: {"unused": True},
    )

    assert out == {
        "requested_variant": 2,
        "valid_kind": False,
        "allowed_kinds": ["docx", "result_bundle_json"],
    }


def test_build_actions_download_event_fields_uses_job_payload_metadata():
    out = actions_download_response.build_actions_download_event_fields(
        job={
            "payload": {
                "project_id": "p-1",
                "topic": "下载测试",
                "request_id": "req-1",
                "trace_id": "trace-1",
            }
        },
        job_id="job-9",
        kind="result_bundle_json",
        variant=0,
        file_path="/tmp/result.json",
        file_size_bytes=128,
    )

    assert out == {
        "job_id": "job-9",
        "kind": "result_bundle_json",
        "variant": 1,
        "file_path": "/tmp/result.json",
        "file_size_bytes": 128,
        "project_id": "p-1",
        "topic": "下载测试",
        "request_id": "req-1",
        "trace_id": "trace-1",
    }
