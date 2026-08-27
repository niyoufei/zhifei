from __future__ import annotations

import json

from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger


def _quality_threshold_bundle():
    return {
        "mode": "process_bound",
        "items": [
            {
                "id": "wall-compaction",
                "process": "围墙基础回填",
                "metric": "压实系数",
                "operator": ">=",
                "value": 0.97,
                "unit": "",
                "status": "verified",
                "source": "施工图",
                "locator": f"3 围墙.pdf#p1_{'a' * 64}@530",
                "document_sha256": "a" * 64,
                "extract_text_sha256": "b" * 64,
                "page": 1,
                "page_text_sha256": "c" * 64,
                "offset": 530,
                "end": 545,
                "page_start_offset": 0,
                "page_end_offset": 900,
                "page_match_start": 530,
                "page_match_end": 545,
                "match_text_sha256": "d" * 64,
            }
        ],
    }


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


def test_enterprise_defaults_are_not_exposed_or_auto_filled():
    result = _probe(build_project_fact_ledger([]))

    assert result["auto_fill"] == {}
    assert result["formal_ready"] is False
    assert result["provisional"] == []
    assert all(row["status"] == "missing" for row in result["missing"])
    assert all(row["source"] == "none" for row in result["missing"])
    assert all(row["proposed_value"] is None for row in result["missing"])
    assert all(
        row["usable_for_formal_delivery"] is False
        for row in result["missing"]
    )
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    for forbidden in ("80人", "3天", "2次/日", "120天", "≤5mm", "≤4h"):
        assert forbidden not in serialized


def test_unstructured_values_do_not_bypass_fact_status_gate():
    result = _probe(
        build_project_fact_ledger([]),
        requirements=["资源峰值80人，关键线路间隔3天，风险检查频次2次/日"],
    )

    by_field = {row["field"]: row for row in result["missing"]}
    assert by_field["resource_peak"]["detected_unstructured"] is True
    assert by_field["critical_interval_days"]["detected_unstructured"] is True
    assert by_field["risk_inspection_frequency"]["detected_unstructured"] is True
    assert all(row["proposed_value"] is None for row in result["missing"])
    assert result["provisional"] == []
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
                    "quality_threshold": _quality_threshold_bundle(),
                    "deviation_action_deadline": "在监理人规定时间内按要求完成整改",
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


def test_structured_quality_threshold_and_procedural_deadline_are_resolved():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "tender-and-drawings",
                "source_type": "tender",
                "facts": {
                    "quality_threshold": _quality_threshold_bundle(),
                    "deviation_action_deadline": (
                        "在监理人规定时间内按要求完成整改"
                    ),
                },
                "evidence": {"locator": "招标文件.pdf#p92_sha@67018"},
            }
        ]
    )

    result = _probe(ledger)
    resolved = {row["field"]: row for row in result["resolved"]}
    assert resolved["quality_threshold"]["value"]["mode"] == "process_bound"
    assert resolved["quality_threshold"]["value"]["items"][0]["process"] == (
        "围墙基础回填"
    )
    assert resolved["deviation_action_deadline"]["value"] == (
        "在监理人规定时间内按要求完成整改"
    )
    assert "deviation_action_deadline" not in result["blocked_fields"]


def test_global_quality_scalar_cannot_resolve_formal_parameter():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {"quality_threshold": "偏差≤5mm"},
            }
        ]
    )

    result = _probe(ledger)

    assert not any(
        row["field"] == "quality_threshold" for row in result["resolved"]
    )
    assert "quality_threshold" in result["blocked_fields"]
