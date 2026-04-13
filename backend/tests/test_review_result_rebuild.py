from __future__ import annotations

import json

from backend.zhifei_autoplan.review_result_rebuild import (
    build_review_job_result,
    build_review_result_metadata,
    build_review_variant_summary,
    write_review_result_bundle,
)
from backend.zhifei_autoplan.run_contract import load_result_bundle


def _sample_variant() -> dict:
    return {
        "variant_id": 1,
        "topic": "复核回写共享模块",
        "generation_mode": "stable_delivery",
        "generation_trace": {
            "generation_mode": "stable_delivery",
            "mode_effective": "stable_delivery",
            "stable_output": True,
            "deterministic_variant_forced": True,
            "deterministic_logic_template_id": "A",
            "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
            "self_evolution": {"enabled": False},
        },
        "logic_template_id": "A",
        "logic_template_name": "交付清单驱动",
        "sections": [{"title": "施工部署", "content": "正文内容"}],
        "quality_checks": {
            "score": 95,
            "issue_list": [
                {
                    "title": "施工部署",
                    "type": "engineering_gap",
                    "severity": "high",
                    "problem": "缺少责任人与验收记录",
                    "suggestion": "补齐责任/频次/记录",
                },
                {
                    "title": "施工部署",
                    "type": "case_reference_copy_risk",
                    "severity": "high",
                    "problem": "与案例相似度过高",
                    "suggestion": "重写本章",
                    "reference_case_id": "case-1",
                }
            ],
        },
        "quality_gate": {
            "ok": False,
            "failed": [{"metric": "engineering_ok_rate"}],
        },
        "resource_usage_summary": {"call_count": 1},
    }


def test_build_review_result_metadata_keeps_current_contract_shape():
    results = [_sample_variant()]
    payload = {
        "generation_mode": "stable_delivery",
        "logic_template_id": "A",
        "_mode_policy": {
            "profile": "stable_delivery",
            "mode_effective": "stable_delivery",
            "stable_output": True,
            "deterministic_variant_forced": True,
            "deterministic_logic_template_id": "A",
        },
    }

    variant_summary = build_review_variant_summary(results)
    metadata = build_review_result_metadata(results, payload)

    assert variant_summary["variant_count"] == 1
    assert variant_summary["variants"][0]["logic_template_id"] == "A"
    assert metadata["generation_mode_summary"]["profile"] == "stable_delivery"
    assert metadata["runtime_by_variant"]["1"]["mode_effective"] == "stable_delivery"
    assert metadata["quality_by_variant"]["1"]["quality_score"] == 95
    assert metadata["quality_by_variant"]["1"]["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert metadata["quality_by_variant"]["1"]["reference_quality_summary"]["case_copy_risk_count"] == 1
    assert metadata["reference_quality_summary"]["affected_case_ids"] == ["case-1"]
    assert metadata["blocking_issue_summary"]["failed_gate_metric_count"] == 1
    assert metadata["logic_template_id"] == "A"
    assert metadata["logic_template_name"] == "交付清单驱动"


def test_write_review_result_bundle_and_build_job_result(tmp_path):
    outputs = {
        "json": str(tmp_path / "review_result.json"),
        "docx": [str(tmp_path / "review_result.docx")],
    }
    results = [_sample_variant()]
    payload = {"project_id": "review-rebuild-case", "topic": "复核回写共享模块"}
    metadata = build_review_result_metadata(results, payload)
    variant_summary = build_review_variant_summary(results)

    output_json = tmp_path / "review_result.json"
    output_docx = tmp_path / "review_result.docx"
    output_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    output_docx.write_bytes(b"docx")

    bundle_path = write_review_result_bundle(
        "job-review-rebuild",
        payload=payload,
        outputs=outputs,
        result_metadata=metadata,
        resource_usage_summary={"call_count": 1},
        variant_summary=variant_summary,
    )
    bundle = load_result_bundle(bundle_path)
    job_result = build_review_job_result(
        outputs=outputs,
        resource_usage_summary={"call_count": 1},
        result_bundle_json=bundle_path,
        result_metadata=metadata,
    )

    assert bundle is not None
    assert bundle["request"]["project_id"] == "review-rebuild-case"
    assert bundle["result_metadata"]["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert bundle["result_metadata"]["reference_quality_summary"]["case_copy_risk_count"] == 1
    assert job_result["result_bundle_json"] == bundle_path
    assert job_result["resource_usage_summary"]["call_count"] == 1
    assert job_result["blocking_issue_summary"]["blocking_issue_count"] == 1
