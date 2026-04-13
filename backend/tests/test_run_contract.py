from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.run_contract import (
    build_contract_stamp,
    build_stage_artifact_envelope,
    build_result_bundle,
    contract_fingerprint,
    extract_outputs_from_result_bundle,
    load_result_bundle,
    resolve_contract_stamp,
    result_bundle_artifacts_complete,
)


def test_build_contract_stamp_tracks_rules_digest(tmp_path, monkeypatch):
    rules_path = tmp_path / "rules.json"
    rules_path.write_text('{"建筑法定术语词典": {}, "劳动力排班算法矩阵": {}, "法定工种白名单": []}', encoding="utf-8")
    monkeypatch.setenv("ZF_ENGINEERING_RULES_PATH", str(rules_path))

    contract = build_contract_stamp({"quality_gate_retry_rounds": 2})

    assert contract["request_contract_version"] == "actions-generate-contract-v1"
    assert contract["engineering_rules"]["path"] == str(rules_path)
    assert contract["engineering_rules"]["sha1"]
    assert contract["quality_gate"]["retry_rounds"] == 2
    assert contract["quality_gate"]["thresholds_sha1"]


def test_resolve_contract_stamp_merges_existing_values(tmp_path, monkeypatch):
    rules_path = tmp_path / "rules.json"
    rules_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ZF_ENGINEERING_RULES_PATH", str(rules_path))

    payload = {
        "_contract_stamp": {
            "result_bundle_version": "actions-result-bundle-v9",
            "quality_gate": {"retry_rounds": 7},
        }
    }
    contract = resolve_contract_stamp(payload)

    assert contract["result_bundle_version"] == "actions-result-bundle-v9"
    assert contract["quality_gate"]["retry_rounds"] == 7
    assert contract["engineering_rules"]["path"] == str(rules_path)


def test_build_stage_artifact_envelope_preserves_payload_and_attaches_metadata():
    contract = {"request_contract_version": "actions-generate-contract-v1"}

    envelope = build_stage_artifact_envelope(
        filename="03_variant_results_summary.json",
        job_id="job-123",
        request_signature="sig-1",
        contract_stamp=contract,
        payload={"job_id": "job-123", "result_summary": {"done": 1}},
    )

    assert envelope["job_id"] == "job-123"
    assert envelope["result_summary"]["done"] == 1
    assert envelope["_artifact"]["stage"] == "variant_results_summary"
    assert envelope["_artifact"]["request_signature"] == "sig-1"
    assert envelope["_artifact"]["contract"]["request_contract_version"] == "actions-generate-contract-v1"
    assert contract_fingerprint(contract)


def test_result_bundle_roundtrip_and_artifact_completion(tmp_path):
    output_json = tmp_path / "actions_job-1.json"
    output_docx = tmp_path / "actions_job-1_v1.docx"
    output_json.write_text("{}", encoding="utf-8")
    output_docx.write_text("docx", encoding="utf-8")
    bundle_path = tmp_path / "actions_job-1_result_bundle.json"

    bundle = build_result_bundle(
        job_id="job-1",
        payload={"project_id": "P-1", "topic": "测试"},
        outputs={"json": str(output_json), "docx": [str(output_docx)], "focus_xlsx": [None]},
        result_metadata={"logic_template_id": "A"},
        resource_usage_summary={"call_count": 1},
        variant_summary={"variant_count": 1},
    )
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = load_result_bundle(bundle_path)
    assert loaded is not None
    outputs = extract_outputs_from_result_bundle(loaded)
    assert outputs["json"] == str(output_json)
    assert outputs["docx"] == [str(output_docx)]
    assert result_bundle_artifacts_complete(loaded) is True
    artifact = next(item for item in loaded["artifacts"] if item["kind"] == "json")
    assert artifact["sha256"]
    assert loaded["request"]["case_library"] == {}
    assert loaded["request"]["image_library"] == {}


def test_result_bundle_preserves_reference_library_request_contract(tmp_path):
    output_json = tmp_path / "actions_job-3.json"
    output_json.write_text("{}", encoding="utf-8")

    bundle = build_result_bundle(
        job_id="job-3",
        payload={
            "project_id": "P-3",
            "topic": "增强源测试",
            "case_library": {"enabled": True, "selected_case_ids": ["case-1"]},
            "image_library": {"enabled": True, "selected_image_ids": ["image-1"]},
        },
        outputs={"json": str(output_json)},
        result_metadata={"reference_enhancements_by_variant": {"1": {"case_library": {"enabled": True}}}},
        resource_usage_summary={},
        variant_summary={"variant_count": 1},
    )

    assert bundle["request"]["case_library"]["enabled"] is True
    assert bundle["request"]["case_library"]["selected_case_ids"] == ["case-1"]
    assert bundle["request"]["image_library"]["enabled"] is True
    assert bundle["request"]["image_library"]["selected_image_ids"] == ["image-1"]


def test_result_bundle_artifact_completion_fails_when_file_tampered(tmp_path):
    output_json = tmp_path / "actions_job-2.json"
    output_json.write_text("{}", encoding="utf-8")
    bundle = build_result_bundle(
        job_id="job-2",
        payload={"project_id": "P-2", "topic": "篡改校验"},
        outputs={"json": str(output_json)},
        result_metadata={},
        resource_usage_summary={},
        variant_summary={"variant_count": 1},
    )

    assert result_bundle_artifacts_complete(bundle) is True
    output_json.write_text('{"tampered": true}', encoding="utf-8")
    assert result_bundle_artifacts_complete(bundle) is False
