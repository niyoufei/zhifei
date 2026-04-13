from __future__ import annotations

from backend.zhifei_autoplan.result_variant_summary_builder import build_variant_summary_row


def test_build_variant_summary_row_keeps_base_shape():
    row = build_variant_summary_row(
        item={
            "variant_id": 1,
            "topic": "共享 summary row",
            "generation_mode": "stable_delivery",
            "generation_trace": {
                "generation_mode": "stable_delivery",
                "mode_effective": "stable_delivery",
                "stable_output": True,
                "deterministic_variant_forced": True,
                "deterministic_logic_template_id": "A",
                "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
                "retrieval_cache": {"hits": 1},
                "self_evolution": {"enabled": False},
            },
            "quality_checks": {"score": 95},
            "quality_gate": {"ok": False, "failed": [{"metric": "engineering_ok_rate"}]},
            "resource_usage_summary": {"call_count": 1},
        },
        variant_index=1,
        logic_template_id="A",
        logic_template_name="交付清单驱动",
        section_count=4,
        section_runtime_budget_preview=[{"title": "施工部署"}],
        remediation_strategy_audit={"audit_version": "v1"},
        remediation_execution_audit={"trace_count": 1},
        extra_fields={"section_titles": ["施工部署", "质量目标"]},
    )

    assert row["variant_index"] == 1
    assert row["variant_id"] == 1
    assert row["topic"] == "共享 summary row"
    assert row["generation_mode"] == "stable_delivery"
    assert row["mode_effective"] == "stable_delivery"
    assert row["stable_output"] is True
    assert row["deterministic_variant_forced"] is True
    assert row["deterministic_logic_template_id"] == "A"
    assert row["logic_template_id"] == "A"
    assert row["logic_template_name"] == "交付清单驱动"
    assert row["section_count"] == 4
    assert row["quality_score"] == 95
    assert row["quality_gate_ok"] is False
    assert row["quality_gate_failed_count"] == 1
    assert row["pipeline_stages"][0]["stage"] == "draft_generation"
    assert row["retrieval_cache"]["hits"] == 1
    assert row["self_evolution"]["enabled"] is False
    assert row["remediation_strategy_audit"]["audit_version"] == "v1"
    assert row["remediation_execution_audit"]["trace_count"] == 1
    assert row["section_runtime_budget_preview"][0]["title"] == "施工部署"
    assert row["resource_usage_summary"]["call_count"] == 1
    assert row["section_titles"] == ["施工部署", "质量目标"]
