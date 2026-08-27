from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger,
    build_project_fact_ledger_from_inputs,
    project_fact_prompt_requirements,
    validate_project_fact_ledger,
)
from backend.zhifei_autoplan.project_parameter_evidence import (
    build_project_parameter_evidence,
)

_TEST_DOCUMENT_SHA256 = "a" * 64
_TEST_PROJECT_ID = "P-FORMAL-001"


def _digest(value) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _wall_parameter_evidence(tmp_path: Path) -> dict:
    workspace = tmp_path / "parameter-evidence"
    uploads = workspace / "uploads"
    extracts = workspace / "extracts"
    audit = workspace / "audit" / "ingest.jsonl"
    uploads.mkdir(parents=True)
    extracts.mkdir(parents=True)
    audit.parent.mkdir(parents=True)
    filename = "3 围墙.pdf"
    source_bytes = b"reviewed-wall-drawing"
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    text = "基础开挖至标高后，对下部土层进行压实处理，压实系数不小于0.97。"
    extract_bytes = text.encode("utf-8")
    extract_sha256 = hashlib.sha256(extract_bytes).hexdigest()
    source_path = uploads / f"{source_sha256}_{filename}"
    extract_path = extracts / f"{source_sha256}_{extract_sha256}.txt"
    source_path.write_bytes(source_bytes)
    extract_path.write_bytes(extract_bytes)
    record = {
        "project_id": _TEST_PROJECT_ID,
        "workspace_dir": str(workspace),
        "filename": filename,
        "sha256": source_sha256,
        "file_id": source_sha256,
        "pages": 1,
        "source_hint": "drawing",
        "tags": ["drawing"],
        "saved_as": str(source_path),
        "extract_saved_as": str(extract_path),
        "extract_text_sha256": extract_sha256,
        "usable": True,
        "enabled": True,
    }
    audit.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    return build_project_parameter_evidence(
        project_id=_TEST_PROJECT_ID,
        tender={},
        audit_path=audit,
    )


def _approved_file_fact(field, value, *, unit: str = "", file_name: str, anchor: str):
    return {
        "value": value,
        "unit": unit,
        "evidence": {
            "file_name": file_name,
            "document_sha256": _TEST_DOCUMENT_SHA256,
            "locator": f"{file_name}#{anchor}",
        },
        "approval_receipt": {
            "receipt_id": f"APR-{field}",
            "status": "approved",
            "project_id": _TEST_PROJECT_ID,
            "field": field,
            "value_digest": _digest(
                {"field": field, "value": value, "unit": unit}
            ),
            "summary": f"批准 {field} 的项目正式值",
            "approved_by": "项目负责人",
            "approved_at": "2026-08-27T09:30:00+08:00",
        },
    }


def _process_bound_quality_threshold():
    return {
        "mode": "process_bound",
        "items": [
            {
                "id": "pool-concrete",
                "process": "车辆消毒池结构",
                "metric": "混凝土强度等级",
                "operator": "≥",
                "value": "C25",
                "unit": "",
                "status": "verified",
                "source": "reviewed_design",
                "locator": f"车辆消毒池.pdf#p6_{'b' * 64}@2003",
                "document_sha256": "b" * 64,
                "extract_text_sha256": "c" * 64,
                "page": 6,
                "page_text_sha256": "d" * 64,
                "offset": 2003,
                "end": 2020,
                "page_start_offset": 1800,
                "page_end_offset": 2400,
                "page_match_start": 203,
                "page_match_end": 220,
                "match_text_sha256": "e" * 64,
            },
            {
                "id": "wall-compaction",
                "process": "围墙基础回填",
                "metric": "压实系数",
                "operator": "≥",
                "value": 0.97,
                "unit": "",
                "status": "verified",
                "source": "reviewed_design",
                "locator": f"3 围墙.pdf#p1_{'f' * 64}@530",
                "document_sha256": "f" * 64,
                "extract_text_sha256": "1" * 64,
                "page": 1,
                "page_text_sha256": "2" * 64,
                "offset": 530,
                "end": 545,
                "page_start_offset": 0,
                "page_end_offset": 900,
                "page_match_start": 530,
                "page_match_end": 545,
                "match_text_sha256": "3" * 64,
            },
        ],
    }


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


def test_tender_project_fact_preserves_procedural_deadline_evidence():
    page_text_sha256 = "b" * 64
    locator = (
        "招标文件.pdf#document_sha256="
        f"{_TEST_DOCUMENT_SHA256}&page=92"
        f"&page_text_sha256={page_text_sha256}&offset=67018"
    )
    ledger = build_project_fact_ledger_from_inputs(
        payload={},
        tender={
            "extraction_meta": {
                "project_facts": {
                    "deviation_action_deadline": {
                        "value": "在监理人规定时间内按要求完成整改",
                        "unit": "",
                        "status": "verified",
                        "evidence": {
                            "file_name": "招标文件.pdf",
                            "page": 92,
                            "document_sha256": _TEST_DOCUMENT_SHA256,
                            "page_text_sha256": page_text_sha256,
                            "start": 67018,
                            "end": 67036,
                            "page_start": 212,
                            "page_end": 230,
                            "locator": locator,
                            "snippet": "必须在监理人规定时间内按要求完成整改",
                        },
                    }
                }
            }
        },
        boq_wbs_cpm={},
    )

    fact = ledger["facts"]["deviation_action_deadline"]
    assert fact["value"] == "在监理人规定时间内按要求完成整改"
    assert fact["status"] == "verified"
    assert fact["evidence"]["page"] == 92
    assert fact["evidence"]["document_sha256"] == _TEST_DOCUMENT_SHA256
    assert fact["evidence"]["page_text_sha256"] == page_text_sha256
    assert fact["evidence"]["locator"] == locator
    assert "snippet" not in fact["evidence"]
    assert len(fact["evidence"]["snippet_sha256"]) == 64


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


def test_process_bound_quality_threshold_is_normalized_without_global_scope():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "reviewed-drawings",
                "source_type": "reviewed_design",
                "facts": {"quality_threshold": _process_bound_quality_threshold()},
            }
        ]
    )

    fact = ledger["facts"]["quality_threshold"]
    assert fact["status"] == "verified"
    assert fact["value"]["mode"] == "process_bound"
    assert [item["process"] for item in fact["value"]["items"]] == [
        "车辆消毒池结构",
        "围墙基础回填",
    ]
    assert {item["operator"] for item in fact["value"]["items"]} == {"≥"}
    assert all(item["process"] != "全局" for item in fact["value"]["items"])
    prompt_lines = project_fact_prompt_requirements(ledger)
    assert any(
        "工序=围墙基础回填；指标=压实系数；判定=≥0.97" in line
        for line in prompt_lines
    )
    assert any(
        "工序=车辆消毒池结构；指标=混凝土强度等级；判定=≥C25" in line
        for line in prompt_lines
    )
    assert not any("项目事实：质量阈值=" in line for line in prompt_lines)


def test_deterministic_project_parameter_evidence_enters_ledger_as_reviewed_design(
    tmp_path: Path,
):
    evidence = _wall_parameter_evidence(tmp_path)
    ledger = build_project_fact_ledger_from_inputs(
        payload={"project_id": _TEST_PROJECT_ID},
        tender={},
        boq_wbs_cpm={},
        project_parameter_evidence=evidence,
    )

    fact = ledger["facts"]["quality_threshold"]
    assert fact["source_id"] == "project-parameter-evidence"
    assert fact["source_type"] == "reviewed_design"
    assert fact["status"] == "verified"
    assert len(fact["value"]["items"]) == 1
    assert fact["evidence"]["evidence_set_receipt_digest"] == evidence[
        "evidence_set_receipt_digest"
    ]
    assert "quality_threshold" in ledger["formal_parameter_readiness"][
        "ready_fields"
    ]


def test_global_scalar_quality_threshold_is_not_admitted_as_project_fact():
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {"quality_threshold": "偏差≤5mm"},
            }
        ]
    )

    assert "quality_threshold" not in ledger["facts"]
    assert "quality_threshold" in ledger["formal_parameter_readiness"]["missing_fields"]


def test_quality_bundle_with_unlocated_item_remains_provisional():
    bundle = _process_bound_quality_threshold()
    bundle["items"][0]["locator"] = ""
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {"quality_threshold": bundle},
            }
        ]
    )

    assert ledger["facts"]["quality_threshold"]["status"] == "provisional"
    assert "quality_threshold" in ledger["formal_parameter_readiness"][
        "provisional_fields"
    ]


def test_unlocated_sensitive_approved_values_are_downgraded_and_hold():
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "approved_project_fact_resolutions": {
                "resource_peak": {
                    "value": 80,
                    "unit": "人",
                    "evidence": {
                        "document_sha256": _TEST_DOCUMENT_SHA256,
                        "locator": (
                            "payload.approved_project_fact_resolutions.resource_peak"
                        ),
                    },
                },
                "critical_interval_days": {"value": 3, "unit": "天"},
                "risk_inspection_frequency": "2次/日",
            }
        },
        tender={},
        boq_wbs_cpm={},
    )

    for field in (
        "resource_peak",
        "critical_interval_days",
        "risk_inspection_frequency",
    ):
        assert ledger["facts"][field]["status"] == "provisional"
        assert field in ledger["formal_parameter_readiness"]["provisional_fields"]
    assert ledger["formal_parameter_readiness"]["ready"] is False


def test_plain_payload_formal_facts_remain_provisional_but_identity_is_approved():
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": _TEST_PROJECT_ID,
            "project_facts": {
                "project_name": "养殖场建设项目",
                "project_code": "AF-001",
                "planned_duration_days": {"value": 150, "unit": "天"},
                "resource_peak": {"value": 80, "unit": "人"},
                "critical_interval_days": {"value": 3, "unit": "天"},
                "risk_inspection_frequency": "2次/日",
                "quality_threshold": _process_bound_quality_threshold(),
                "deviation_action_deadline": "4小时",
            },
        },
        tender={},
        boq_wbs_cpm={},
    )

    assert ledger["facts"]["project_name"]["status"] == "approved"
    assert ledger["facts"]["project_code"]["status"] == "approved"
    assert set(ledger["formal_parameter_readiness"]["provisional_fields"]) == {
        "planned_duration_days",
        "resource_peak",
        "critical_interval_days",
        "risk_inspection_frequency",
        "quality_threshold",
        "deviation_action_deadline",
    }
    assert ledger["formal_parameter_readiness"]["ready"] is False


def test_payload_formal_fact_can_only_advance_with_file_and_confirmation_receipt():
    resource_peak = _approved_file_fact(
        "resource_peak",
        80,
        unit="人",
        file_name="批准资源计划.xlsx",
        anchor="sheet=资源计划&cell=B12",
    )
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": _TEST_PROJECT_ID,
            "project_facts": {"resource_peak": resource_peak},
        },
        tender={},
        boq_wbs_cpm={},
    )

    fact = ledger["facts"]["resource_peak"]
    assert fact["source_type"] == "user_input"
    assert fact["status"] == "approved"
    assert fact["approval_receipt"]["field"] == "resource_peak"
    assert len(fact["approval_receipt"]["receipt_digest"]) == 64


def test_approved_resolution_requires_value_bound_receipt_and_file_evidence():
    valid = _approved_file_fact(
        "resource_peak",
        80,
        unit="人",
        file_name="批准资源计划.xlsx",
        anchor="sheet=资源计划&cell=B12",
    )
    missing_receipt = copy.deepcopy(valid)
    missing_receipt.pop("approval_receipt")
    generic_locator = copy.deepcopy(valid)
    generic_locator["evidence"]["locator"] = (
        "payload.approved_project_fact_resolutions.resource_peak"
    )
    stale_value_receipt = copy.deepcopy(valid)
    stale_value_receipt["value"] = 81
    cross_project_receipt = copy.deepcopy(valid)
    cross_project_receipt["approval_receipt"]["project_id"] = "P-OTHER"

    for raw in (
        missing_receipt,
        generic_locator,
        stale_value_receipt,
        cross_project_receipt,
    ):
        ledger = build_project_fact_ledger_from_inputs(
            payload={
                "project_id": _TEST_PROJECT_ID,
                "approved_project_fact_resolutions": {"resource_peak": raw},
            },
            tender={},
            boq_wbs_cpm={},
        )
        assert ledger["facts"]["resource_peak"]["status"] == "provisional"
        assert "resource_peak" in ledger["formal_parameter_readiness"][
            "provisional_fields"
        ]

    unidentified = build_project_fact_ledger_from_inputs(
        payload={"approved_project_fact_resolutions": {"resource_peak": valid}},
        tender={},
        boq_wbs_cpm={},
    )
    assert unidentified["project_id"] is None
    assert unidentified["facts"]["resource_peak"]["status"] == "provisional"


def test_project_parameter_evidence_hold_or_digest_mismatch_never_enters_ledger(
    tmp_path: Path,
):
    report = _wall_parameter_evidence(tmp_path)
    required_ids = report["required_item_ids"]

    for mutation in ("hold", "digest"):
        candidate = copy.deepcopy(report)
        if mutation == "hold":
            candidate["status"] = "HOLD_PROJECT_PARAMETER_EVIDENCE_CONFLICT"
            candidate["ready"] = False
            candidate["conflicts"] = [{"id": required_ids[0]}]
        else:
            candidate["quality_threshold_bundle_digest"] = "f" * 64
        ledger = build_project_fact_ledger_from_inputs(
            payload={"project_id": _TEST_PROJECT_ID},
            tender={},
            boq_wbs_cpm={},
            project_parameter_evidence=candidate,
        )
        assert "quality_threshold" not in ledger["facts"]
        assert "quality_threshold" in ledger["formal_parameter_readiness"][
            "missing_fields"
        ]


def test_quality_bundle_preserves_reversible_evidence_and_rejects_mismatch():
    bundle = _process_bound_quality_threshold()
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "reviewed-drawings",
                "source_type": "reviewed_design",
                "facts": {"quality_threshold": bundle},
            }
        ]
    )
    item = ledger["facts"]["quality_threshold"]["value"]["items"][0]
    for key in (
        "document_sha256",
        "extract_text_sha256",
        "page",
        "page_text_sha256",
        "offset",
        "end",
        "page_start_offset",
        "page_end_offset",
        "page_match_start",
        "page_match_end",
        "match_text_sha256",
    ):
        assert item[key] == bundle["items"][0][key]

    mismatched = copy.deepcopy(bundle)
    mismatched["items"][0]["document_sha256"] = "9" * 64
    rejected = build_project_fact_ledger(
        [
            {
                "source_id": "reviewed-drawings",
                "source_type": "reviewed_design",
                "facts": {"quality_threshold": mismatched},
            }
        ]
    )
    assert rejected["facts"]["quality_threshold"]["status"] == "provisional"


def test_all_confirmed_formal_parameters_are_ready():
    approved = {
        "planned_duration_days": _approved_file_fact(
            "planned_duration_days",
            150,
            unit="天",
            file_name="批准总控计划.pdf",
            anchor="page=3&item=合同工期",
        ),
        "resource_peak": _approved_file_fact(
            "resource_peak",
            80,
            unit="人",
            file_name="批准资源计划.xlsx",
            anchor="sheet=资源计划&cell=B12",
        ),
        "critical_interval_days": _approved_file_fact(
            "critical_interval_days",
            3,
            unit="天",
            file_name="批准网络计划.pdf",
            anchor="page=12&item=关键线路",
        ),
        "risk_inspection_frequency": _approved_file_fact(
            "risk_inspection_frequency",
            "2次/日",
            file_name="批准风险制度.docx",
            anchor="section=5.2",
        ),
        "quality_threshold": _approved_file_fact(
            "quality_threshold",
            _process_bound_quality_threshold(),
            file_name="批准质量标准.pdf",
            anchor="page=8&item=工序验收标准",
        ),
        "deviation_action_deadline": _approved_file_fact(
            "deviation_action_deadline",
            "4小时",
            file_name="批准质量制度.docx",
            anchor="section=7.4",
        ),
    }
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": _TEST_PROJECT_ID,
            "approved_project_fact_resolutions": approved,
        },
        tender={},
        boq_wbs_cpm={},
    )

    readiness = ledger["formal_parameter_readiness"]
    assert readiness["ready"] is True
    assert readiness["missing_fields"] == []
    assert readiness["provisional_fields"] == []
    assert all(row["status"] == "approved" for row in ledger["facts"].values())
