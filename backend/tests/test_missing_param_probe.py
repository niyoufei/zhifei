from __future__ import annotations

from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger


def _probe(ledger, *, requirements=None):
    return probe_missing_parameters(
        topic="示例项目",
        outline=["进度计划"],
        requirements=list(requirements or []),
        tender={},
        boq={},
        enterprise_profile={
            "risk_defaults": {
                "frequency": "2次/日",
                "threshold": "偏差≤5mm",
                "deviation_action": "偏差处置时限≤4h",
            }
        },
        project_fact_ledger=ledger,
    )


def test_verified_duration_resolves_without_reintroducing_120_day_default():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "tender-duration",
                "source_type": "tender",
                "facts": {"planned_duration_days": {"value": 150, "unit": "天"}},
                "evidence": {"locator": "tender#p1@5207"},
            }
        ]
    )

    result = _probe(ledger)

    assert result["formal_ready"] is False
    assert result["auto_fill"] == {}
    assert result["resolved"] == [
        {
            "field": "planned_duration_days",
            "key": "总工期",
            "value": 150,
            "unit": "天",
            "status": "verified",
            "source": "tender",
            "locator": "tender#p1@5207",
        }
    ]
    duration_missing = [row for row in result["missing"] if row["field"] == "planned_duration_days"]
    assert duration_missing == []
    assert all(row.get("proposed_value") != "120天" for row in result["missing"])
    assert set(result["blocked_fields"]) == {
        "resource_peak",
        "critical_interval_days",
        "risk_inspection_frequency",
        "quality_threshold",
        "deviation_action_deadline",
    }


def test_enterprise_defaults_are_provisional_and_not_auto_filled():
    result = _probe(build_project_fact_ledger([]))

    assert result["auto_fill"] == {}
    assert result["formal_ready"] is False
    by_field = {row["field"]: row for row in result["provisional"]}
    assert by_field["resource_peak"]["proposed_value"] == "80人"
    assert by_field["risk_inspection_frequency"]["proposed_value"] == "2次/日"
    assert by_field["quality_threshold"]["proposed_value"] == "偏差≤5mm"
    assert by_field["deviation_action_deadline"]["proposed_value"] == "偏差处置时限≤4h"
    assert all(row["usable_for_formal_delivery"] is False for row in result["provisional"])
    assert not any(row["field"] == "planned_duration_days" for row in result["provisional"])


def test_unstructured_values_do_not_bypass_fact_status_gate():
    result = _probe(
        build_project_fact_ledger([]),
        requirements=["资源峰值80人，关键线路间隔3天，风险检查频次2次/日"],
    )

    by_field = {row["field"]: row for row in result["missing"]}
    assert by_field["resource_peak"]["detected_unstructured"] is True
    assert by_field["critical_interval_days"]["detected_unstructured"] is True
    assert by_field["risk_inspection_frequency"]["detected_unstructured"] is True
    assert result["resolved"] == []
    assert result["formal_ready"] is False


def test_approved_complete_ledger_is_formal_ready():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {
                    "planned_duration_days": {"value": 150, "unit": "天"},
                    "resource_peak": {"value": 80, "unit": "人"},
                    "critical_interval_days": {"value": 3, "unit": "天"},
                    "risk_inspection_frequency": "2次/日",
                    "quality_threshold": "按工序图纸及规范",
                    "deviation_action_deadline": "4小时",
                },
            }
        ]
    )

    result = _probe(ledger)

    assert result["ok"] is True
    assert result["formal_ready"] is True
    assert result["missing"] == []
    assert result["provisional"] == []
    assert len(result["resolved"]) == 6
