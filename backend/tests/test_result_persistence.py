from __future__ import annotations

import json

from backend.zhifei_autoplan.result_persistence import (
    build_job_result_payload,
    resolve_result_bundle_path,
    write_result_bundle_file,
)
from backend.zhifei_autoplan.run_contract import load_result_bundle


def test_resolve_result_bundle_path_prefers_json_neighbor(tmp_path):
    outputs = {"json": str(tmp_path / "actions_job-1.json")}

    path = resolve_result_bundle_path("job-1", outputs=outputs)

    assert path == tmp_path / "actions_job-1_result_bundle.json"


def test_write_result_bundle_file_and_build_job_result_payload(tmp_path):
    output_json = tmp_path / "actions_job-2.json"
    output_docx = tmp_path / "actions_job-2_v1.docx"
    output_json.write_text("{}", encoding="utf-8")
    output_docx.write_bytes(b"docx")
    outputs = {"json": str(output_json), "docx": [str(output_docx)]}

    bundle_path = write_result_bundle_file(
        "job-2",
        payload={"project_id": "P-2", "topic": "共享持久化"},
        outputs=outputs,
        result_metadata={"generation_mode_summary": {"profile": "stable_delivery"}},
        resource_usage_summary={"call_count": 1},
        variant_summary={"variant_count": 1},
    )
    bundle = load_result_bundle(bundle_path)
    job_result = build_job_result_payload(
        outputs=outputs,
        resource_usage_summary={"call_count": 1},
        result_bundle_json=bundle_path,
        result_metadata={"blocking_issue_summary": {"blocking_issue_count": 1}},
    )

    assert bundle is not None
    assert bundle["request"]["project_id"] == "P-2"
    assert bundle["outputs"]["docx"] == [str(output_docx)]
    assert bundle["resource_usage_summary"]["call_count"] == 1
    assert job_result["result_bundle_json"] == bundle_path
    assert job_result["resource_usage_summary"]["call_count"] == 1
    assert job_result["blocking_issue_summary"]["blocking_issue_count"] == 1


def test_write_result_bundle_file_supports_normalizer(tmp_path):
    output_json = tmp_path / "actions_job-3.json"
    output_json.write_text("{}", encoding="utf-8")

    bundle_path = write_result_bundle_file(
        "job-3",
        payload={"project_id": "P-3"},
        outputs={"json": str(output_json)},
        result_metadata={},
        resource_usage_summary={},
        variant_summary={"variant_count": 1},
        normalizer=lambda payload: {**payload, "_extra": {"normalized": True}},
    )

    raw = json.loads((tmp_path / "actions_job-3_result_bundle.json").read_text(encoding="utf-8"))
    assert bundle_path == str(tmp_path / "actions_job-3_result_bundle.json")
    assert raw["_extra"]["normalized"] is True
