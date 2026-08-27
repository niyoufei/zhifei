from __future__ import annotations

import copy

from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger,
    build_project_fact_ledger_from_inputs,
    project_fact_prompt_requirements,
    validate_project_fact_ledger,
)


def test_higher_priority_fact_wins_and_records_override():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "boq",
                "source_type": "boq",
                "facts": {"planned_duration_days": {"value": 140, "unit": "天"}},
            },
            {
                "source_id": "tender",
                "source_type": "tender",
                "facts": {"planned_duration_days": {"value": 120, "unit": "天"}},
            },
        ]
    )

    assert ledger["status"] == "PASS_PROJECT_FACTS_RESOLVED"
    assert ledger["facts"]["planned_duration_days"]["value"] == 120
    assert ledger["facts"]["planned_duration_days"]["source_type"] == "tender"
    assert ledger["overridden_candidates"][0]["overridden_source_id"] == "boq"
    assert validate_project_fact_ledger(ledger)["ok"] is True


def test_same_priority_conflict_holds_without_selecting_fact():
    ledger = build_project_fact_ledger(
        [
            {"source_id": "tender-a", "source_type": "tender", "facts": {"project_code": "A-01"}},
            {"source_id": "tender-b", "source_type": "tender", "facts": {"project_code": "B-02"}},
        ]
    )

    assert ledger["status"] == "HOLD_PROJECT_FACT_CONFLICT"
    assert ledger["unresolved_fields"] == ["project_code"]
    assert "project_code" not in ledger["facts"]
    assert validate_project_fact_ledger(ledger)["errors"] == ["project_fact_conflict"]


def test_approved_resolution_replaces_conflicting_tender_values():
    ledger = build_project_fact_ledger_from_inputs(
        payload={"approved_project_fact_resolutions": {"project_code": "FINAL-03"}},
        tender={
            "project_code": "A-01",
            "project_facts": {"project_code": "B-02"},
        },
        boq_wbs_cpm={},
    )

    assert ledger["status"] == "PASS_PROJECT_FACTS_RESOLVED"
    assert ledger["facts"]["project_code"]["value"] == "FINAL-03"
    assert ledger["facts"]["project_code"]["source_type"] == "approved_resolution"


def test_input_builder_does_not_hide_conflicting_tender_extractions():
    ledger = build_project_fact_ledger_from_inputs(
        payload={},
        tender={
            "project_code": "HEADER-01",
            "project_facts": {"project_code": "BODY-02"},
        },
        boq_wbs_cpm={},
    )

    assert ledger["status"] == "HOLD_PROJECT_FACT_CONFLICT"
    assert ledger["unresolved_fields"] == ["project_code"]
    assert "project_code" not in ledger["facts"]


def test_ledger_is_stable_and_does_not_mutate_sources():
    sources = [
        {
            "source_id": "tender",
            "source_type": "tender",
            "facts": {"project_name": "  某 项目  ", "project_code": "P-001"},
            "evidence": {"file_name": "招标.pdf", "page": 2, "snippet": "敏感正文"},
        }
    ]
    before = copy.deepcopy(sources)
    first = build_project_fact_ledger(sources)
    second = build_project_fact_ledger(sources)

    assert sources == before
    assert first["ledger_digest"] == second["ledger_digest"]
    assert first["facts"]["project_name"]["value"] == "某 项目"
    evidence = first["facts"]["project_name"]["evidence"]
    assert "snippet" not in evidence
    assert len(evidence["snippet_sha256"]) == 64


def test_prompt_requirements_carry_digest_source_and_evidence():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "tender",
                "source_type": "tender",
                "facts": {"project_name": "示例工程"},
                "evidence": {"locator": "tender#p1@20"},
            }
        ]
    )

    lines = project_fact_prompt_requirements(ledger)
    assert ledger["ledger_digest"] in lines[0]
    assert any("项目名称=示例工程" in line for line in lines)
    assert any("证据:tender#p1@20" in line for line in lines)


def test_digest_detects_tampering():
    ledger = build_project_fact_ledger(
        [{"source_id": "tender", "source_type": "tender", "facts": {"project_code": "P-001"}}]
    )
    ledger["facts"]["project_code"]["value"] = "P-999"
    assert validate_project_fact_ledger(ledger)["errors"] == ["ledger_digest_mismatch"]


def test_implausible_boq_schedule_is_not_promoted_to_project_facts():
    ledger = build_project_fact_ledger_from_inputs(
        payload={"topic": "示例项目"},
        tender={},
        boq_wbs_cpm={
            "summary": {
                "estimated_duration_days": 27907.648,
                "resource_peak": 569,
                "critical_interval_days": 1,
                "critical_path_names": ["土方回填"],
                "schedule_fact_eligible": False,
                "schedule_fact_reasons": ["derived_duration_implausible"],
            }
        },
    )

    assert "planned_duration_days" not in ledger["facts"]
    assert "resource_peak" not in ledger["facts"]
    assert "critical_path_names" not in ledger["facts"]


def test_eligible_boq_schedule_remains_available_as_lower_priority_fact():
    ledger = build_project_fact_ledger_from_inputs(
        payload={},
        tender={},
        boq_wbs_cpm={
            "summary": {
                "estimated_duration_days": 180,
                "resource_peak": 42,
                "critical_interval_days": 3,
                "critical_path_names": ["土方开挖", "结构施工"],
                "schedule_fact_eligible": True,
                "schedule_fact_reasons": [],
            }
        },
    )

    assert ledger["facts"]["planned_duration_days"]["value"] == 180
    assert ledger["facts"]["planned_duration_days"]["source_type"] == "boq"
    assert ledger["facts"]["planned_duration_days"]["status"] == "derived"


def test_tender_source_span_restores_verified_150_day_duration_with_locator():
    ledger = build_project_fact_ledger_from_inputs(
        payload={"system_default_project_facts": {"planned_duration_days": 120}},
        tender={
            "items": [
                {
                    "dimension": "进度节点",
                    "source_spans": [
                        {
                            "file_name": "招标文件.pdf",
                            "page": 0,
                            "start": 5207,
                            "end": 5209,
                            "snippet": "2.7 合同估算价：约 2234.62 万元\n2.8 计划工期：150 日历天",
                        }
                    ],
                }
            ]
        },
        boq_wbs_cpm={
            "summary": {
                "estimated_duration_days": 180,
                "schedule_fact_eligible": True,
            }
        },
    )

    fact = ledger["facts"]["planned_duration_days"]
    assert fact["value"] == 150
    assert fact["unit"] == "天"
    assert fact["status"] == "verified"
    assert fact["source_type"] == "tender"
    assert fact["evidence"]["locator"] == "tender_matrix.items[0].source_spans[0]"
    assert fact["evidence"]["page"] == 0
    assert "snippet" not in fact["evidence"]
    assert len(fact["evidence"]["snippet_sha256"]) == 64
    assert {row["overridden_source_id"] for row in ledger["overridden_candidates"]} == {
        "boq-deterministic-schedule",
        "system-project-fact-defaults",
    }


def test_system_defaults_are_provisional_and_never_enter_prompt_requirements():
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "system_default_project_facts": {
                "planned_duration_days": {"value": 120, "unit": "天", "status": "approved"},
                "resource_peak": {"value": 80, "unit": "人"},
            }
        },
        tender={},
        boq_wbs_cpm={},
    )

    assert ledger["facts"]["planned_duration_days"]["status"] == "provisional"
    assert ledger["facts"]["resource_peak"]["status"] == "provisional"
    assert ledger["formal_parameter_readiness"]["ready"] is False
    assert "planned_duration_days" in ledger["formal_parameter_readiness"]["provisional_fields"]
    assert all("总工期=120" not in line for line in project_fact_prompt_requirements(ledger))


def test_all_confirmed_formal_parameters_are_ready():
    approved = {
        "planned_duration_days": {"value": 150, "unit": "天"},
        "resource_peak": {"value": 80, "unit": "人"},
        "critical_interval_days": {"value": 3, "unit": "天"},
        "risk_inspection_frequency": "2次/日",
        "quality_threshold": "按工序图纸及规范",
        "deviation_action_deadline": "4小时",
    }
    ledger = build_project_fact_ledger_from_inputs(
        payload={"approved_project_fact_resolutions": approved},
        tender={},
        boq_wbs_cpm={},
    )

    readiness = ledger["formal_parameter_readiness"]
    assert readiness["ready"] is True
    assert readiness["missing_fields"] == []
    assert readiness["provisional_fields"] == []
    assert all(row["status"] == "approved" for row in ledger["facts"].values())
