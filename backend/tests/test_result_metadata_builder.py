from __future__ import annotations

from backend.zhifei_autoplan.result_metadata_builder import (
    build_blocking_issue_summary,
    build_reference_quality_summary,
    build_result_metadata_from_rows,
    variant_result_key,
)


def test_variant_result_key_prefers_variant_id():
    assert variant_result_key({"variant_id": 3, "variant_index": 1}) == "3"
    assert variant_result_key({"variant_index": 2}) == "v2"


def test_build_blocking_issue_summary_filters_to_blocking_items():
    summary = build_blocking_issue_summary(
        quality_checks={
            "issue_list": [
                {
                    "title": "施工部署",
                    "type": "engineering_gap",
                    "severity": "high",
                    "problem": "缺少责任人与验收记录",
                    "suggestion": "补齐责任/频次/记录",
                },
                {
                    "title": "普通问题",
                    "type": "style_issue",
                    "severity": "low",
                    "problem": "措辞一般",
                    "suggestion": "优化措辞",
                },
            ]
        },
        quality_gate={"failed": [{"metric": "engineering_ok_rate"}]},
    )

    assert summary["has_blocking_issues"] is True
    assert summary["blocking_issue_count"] == 1
    assert summary["failed_gate_metric_count"] == 1
    assert summary["top_blocking_issues"][0]["type"] == "engineering_gap"


def test_build_reference_quality_summary_filters_case_reference_risks():
    summary = build_reference_quality_summary(
        quality_checks={
            "issue_list": [
                {
                    "title": "施工部署",
                    "type": "case_reference_copy_risk",
                    "severity": "high",
                    "problem": "与案例相似度过高",
                    "suggestion": "重写本章",
                    "reference_case_id": "case-1",
                },
                {
                    "title": "普通问题",
                    "type": "style_issue",
                    "severity": "low",
                    "problem": "措辞一般",
                    "suggestion": "优化措辞",
                },
            ]
        }
    )

    assert summary["has_reference_risks"] is True
    assert summary["reference_risk_count"] == 1
    assert summary["case_copy_risk_count"] == 1
    assert summary["affected_case_ids"] == ["case-1"]
    assert summary["top_reference_risks"][0]["type"] == "case_reference_copy_risk"


def test_build_result_metadata_from_rows_keeps_current_shape():
    rows = [
        {
            "variant_index": 1,
            "variant_id": 1,
            "generation_mode": "stable_delivery",
            "mode_effective": "stable_delivery",
            "stable_output": True,
            "deterministic_variant_forced": True,
            "deterministic_logic_template_id": "A",
            "logic_template_id": "A",
            "logic_template_name": "交付清单驱动",
            "section_count": 4,
            "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
            "retrieval_cache": {"hits": 1},
            "self_evolution": {"enabled": False},
            "section_runtime_budget_preview": [{"title": "施工部署"}],
            "resource_usage_summary": {"call_count": 1},
            "case_library_summary": {
                "enabled": True,
                "selected_case_ids": ["case-1"],
                "matched_project_type": "房建",
                "matched_chapter": "施工部署",
                "match_reason": "selected_case_ids",
                "hit_count": 1,
                "warning_list": [],
            },
            "image_library_summary": {
                "enabled": True,
                "selected_image_ids": ["image-1"],
                "matched_project_type": "房建",
                "matched_chapter": "施工部署",
                "match_reason": "selected_image_ids",
                "hit_count": 1,
                "warning_list": [],
            },
            "quality_score": 95,
            "quality_gate_ok": False,
            "quality_gate_failed_count": 1,
            "remediation_strategy_audit": {"audit_version": "v1"},
            "remediation_execution_audit": {"trace_count": 1},
        }
    ]
    results = [
        {
            "variant_id": 1,
            "quality_checks": {
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
                ]
            },
            "quality_gate": {"ok": False, "failed": [{"metric": "engineering_ok_rate"}]},
        }
    ]
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

    metadata = build_result_metadata_from_rows(
        results=results,
        payload=payload,
        rows=rows,
        blocking_summary_builder=lambda **kwargs: build_blocking_issue_summary(**kwargs),
    )

    assert metadata["generation_mode_summary"]["profile"] == "stable_delivery"
    assert metadata["runtime_by_variant"]["1"]["section_count"] == 4
    assert metadata["quality_by_variant"]["1"]["quality_score"] == 95
    assert metadata["quality_by_variant"]["1"]["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert metadata["quality_by_variant"]["1"]["reference_quality_summary"]["case_copy_risk_count"] == 1
    assert metadata["reference_quality_summary"]["affected_case_ids"] == ["case-1"]
    assert metadata["blocking_issue_summary"]["failed_gate_metric_count"] == 1
    assert metadata["logic_template_id"] == "A"
    assert metadata["logic_template_name"] == "交付清单驱动"
    assert metadata["reference_enhancements_by_variant"]["1"]["case_library"]["selected_case_ids"] == ["case-1"]
    assert metadata["reference_enhancements_by_variant"]["1"]["image_library"]["selected_image_ids"] == ["image-1"]
    assert metadata["reference_enhancements"]["case_library"]["selected_case_ids"] == ["case-1"]
    assert metadata["reference_enhancements"]["image_library"]["selected_image_ids"] == ["image-1"]
