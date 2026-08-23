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
