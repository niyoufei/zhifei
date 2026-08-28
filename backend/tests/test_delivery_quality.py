from __future__ import annotations

import copy
import hashlib
import json

import pytest

from backend.zhifei_autoplan import delivery_quality as delivery_quality_module
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger,
    build_project_fact_ledger_from_inputs,
)

_FORMAL_FIELDS = (
    "planned_duration_days",
    "resource_peak",
    "critical_interval_days",
    "risk_inspection_frequency",
    "quality_threshold",
    "deviation_action_deadline",
)
_PROJECT_ID = "P-FORMAL-GATE"


def _digest(value) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reseal_ledger(ledger: dict) -> None:
    payload = {key: value for key, value in ledger.items() if key != "ledger_digest"}
    ledger["ledger_digest"] = _digest(payload)


def _reseal_evidence(evidence: dict) -> None:
    payload = {key: value for key, value in evidence.items() if key != "evidence_digest"}
    evidence["evidence_digest"] = _digest(payload)


def _quality_item() -> dict:
    return {
        "id": "wall-foundation-compaction",
        "process": "围墙基础持力层压实",
        "metric": "压实系数",
        "operator": "≥",
        "value": 0.97,
        "unit": "",
        "status": "verified",
        "source": "reviewed_design",
        "locator": f"围墙图.pdf#p1_{'a' * 64}@42",
        "document_sha256": "a" * 64,
        "extract_text_sha256": "b" * 64,
        "page": 1,
        "page_text_sha256": "c" * 64,
        "offset": 42,
        "end": 58,
        "page_start_offset": 0,
        "page_end_offset": 500,
        "page_match_start": 42,
        "page_match_end": 58,
        "match_text_sha256": "d" * 64,
    }


def _approved_fact(field: str, value, unit: str = "") -> dict:
    file_name = f"批准参数-{field}.pdf"
    document_sha256 = hashlib.sha256(field.encode("utf-8")).hexdigest()
    return {
        "value": value,
        "unit": unit,
        "evidence": {
            "file_name": file_name,
            "document_sha256": document_sha256,
            "locator": f"{file_name}#p1_{document_sha256}@10",
        },
        "approval_receipt": {
            "receipt_id": f"APR-{field}",
            "status": "approved",
            "project_id": _PROJECT_ID,
            "field": field,
            "value_digest": _digest(
                {"field": field, "value": value, "unit": unit}
            ),
            "summary": f"批准 {field} 的正式项目值",
            "approved_by": "项目负责人",
            "approved_at": "2026-08-27T10:00:00+08:00",
        },
    }


def _formal_parameter_receipts() -> tuple[dict, dict]:
    quality_bundle = {
        "mode": "process_bound",
        "items": [_quality_item()],
    }
    values = (180, 80, 3, "2次/日", quality_bundle, "4h")
    approved = {
        field: _approved_fact(field, value)
        for field, value in zip(_FORMAL_FIELDS, values)
    }
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": _PROJECT_ID,
            "approved_project_fact_resolutions": approved,
        },
        tender={},
        boq_wbs_cpm={},
    )
    return _parameter_report(ledger), ledger


def _parameter_report(ledger: dict) -> dict:
    resolved = []
    missing = []
    for field in _FORMAL_FIELDS:
        fact = ledger.get("facts", {}).get(field)
        if not isinstance(fact, dict):
            missing.append({"field": field, "key": field})
            continue
        resolved.append(
            {
                "field": field,
                "key": field,
                "value": fact["value"],
                "unit": fact["unit"],
                "status": fact["status"],
                "source": fact["source_type"],
                "locator": fact["evidence"]["locator"],
            }
        )
    return {
        "schema_version": "missing-parameter-probe-v2",
        "ok": not missing,
        "formal_ready": not missing,
        "accepted_statuses": ["approved", "derived", "verified"],
        "resolved": resolved,
        "missing": missing,
        "provisional": [],
        "blocked_fields": [],
        "auto_fill": {},
        "project_fact_ledger_digest": ledger["ledger_digest"],
    }


def _bound_sections(ledger: dict) -> list[dict]:
    labels = {
        "planned_duration_days": "总工期",
        "resource_peak": "资源峰值",
        "critical_interval_days": "关键线路间隔",
        "risk_inspection_frequency": "风险检查频次",
        "quality_threshold": "质量阈值",
        "deviation_action_deadline": "偏差处置时限",
    }
    lines = []
    for field in _FORMAL_FIELDS:
        fact = ledger["facts"][field]
        locator = fact["evidence"]["locator"]
        if field == "quality_threshold":
            for item in fact["value"]["items"]:
                lines.append(
                    f"质量阈值 {item['process']}：{item['metric']}"
                    f"{item['operator']}{item['value']}{item['unit']}"
                    f"【证据:{item['locator']}】"
                )
        else:
            lines.append(
                f"{labels[field]}={fact['value']}{fact['unit']}【证据:{locator}】"
            )
    return [{"title": "项目参数", "content": "\n".join(lines)}]


def _verified_standard_index() -> dict:
    return {
        "ok": True,
        "project_id": _PROJECT_ID,
        "audit_path": "/trusted/workspace/audit/ingest.jsonl",
        "official_registry_path": "/trusted/compliance/_official_registry.json",
        "official_registry_sha256": "9" * 64,
        "standards": [
            {
                "filename": "施工标准.pdf",
                "sha256": "e" * 64,
                "extract_text_sha256": "f" * 64,
                "standard_code": "GB 50000-2020",
                "standard_codes": ["GB 50000-2020"],
                "primary_identity_status": "identified",
                "primary_identity_proof_basis": "filename_and_cover",
                "primary_identity_cover_code": "GB 50000-2020",
                "cover_identity_text_sha256": "1" * 64,
                "cover_page_text_sha256": "1" * 64,
                "cover_name_status": "verified",
                "official_registry_status": "verified_clause_source",
                "official_registry": {
                    "status": "verified_clause_source",
                    "standard_code": "GB 50000-2020",
                },
                "text_status": "indexed",
                "source_integrity_status": "verified",
                "clause_evidence_eligible": True,
                "clause_evidence_source": "ingested_standard_text",
                "registry_metadata_used_as_clause_evidence": False,
                "page_anchors": [
                    {
                        "page": 1,
                        "text_sha256": "1" * 64,
                        "evidence_eligible": True,
                    }
                ],
            }
        ],
        "chapter_bindings": [],
        "chapter_binding_status": "no_chapter_specific_evidence",
        "indexed_standard_count": 1,
        "official_registry_verified_count": 1,
        "integrity_rejection_count": 0,
        "invalid_identity_count": 0,
        "missing_text_or_ocr_count": 0,
        "locator_unavailable_count": 0,
        "text_index_status": "complete",
        "clause_evidence_policy": (
            "ingested_page_anchor_required; "
            "registry_metadata_alone_is_not_clause_evidence"
        ),
    }


@pytest.fixture(autouse=True)
def _trusted_standard_rebuild(monkeypatch):
    monkeypatch.setattr(
        delivery_quality_module,
        "_rebuild_current_standard_index",
        lambda **_kwargs: copy.deepcopy(_verified_standard_index()),
    )


def _base_kwargs() -> dict:
    project_parameters, project_fact_ledger = _formal_parameter_receipts()
    return {
        "strict": True,
        "content_review": {"quality_gate": {"pass": True, "blocking_issues": []}},
        "plan_consistency": {"ok": True, "canonical": {"duration_days": 180}},
        "model_review_audit": {
            "failed_chapters": [],
            "consistency_review": {
                "ok": True,
                "summary": "未发现实质性冲突。",
            },
        },
        "requirement_matrix": {
            "summary": {"strict_delivery_allowed": True, "blocking_requirement_ids": []}
        },
        "standard_audit": {
            "ok": True,
            "verified_standard_count": 1,
            "verified_standard_codes": ["GB_50000_2020"],
            "violation_count": 0,
            "violations": [],
        },
        "standard_index": _verified_standard_index(),
        "standard_workspace_dir": "/trusted/workspace",
        "standard_compliance_root": "/trusted/compliance",
        "cross_index": {
            "ok": True,
            "focus_count": 1,
            "mentioned_count": 1,
            "closed_ok_count": 1,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [{"name": "钢筋"}],
        },
        "model_review_required": True,
        "formal_delivery_required": True,
        "project_parameters": project_parameters,
        "project_fact_ledger": project_fact_ledger,
        "sections": _bound_sections(project_fact_ledger),
    }


def test_professional_delivery_gate_passes_complete_evidence_chain():
    gate = build_delivery_quality_gate(**_base_kwargs())
    assert gate["delivery_allowed"] is True
    assert gate["blocker_count"] == 0
    assert gate["formal_contract_version"] == "formal-evidence-v2"
    assert len(gate["decision_digest"]) == 64


def test_formal_delivery_fails_closed_without_independent_standard_evidence():
    kwargs = _base_kwargs()
    kwargs["standard_index"] = {
        "ok": False,
        "project_id": _PROJECT_ID,
        "standards": [],
        "indexed_standard_count": 0,
        "official_registry_verified_count": 0,
        "integrity_rejection_count": 0,
        "invalid_identity_count": 0,
        "missing_text_or_ocr_count": 0,
        "locator_unavailable_count": 0,
        "text_index_status": "no_standards",
    }

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "independent_standard_evidence_missing" in check["reasons"]
    assert "DELIVERY_STANDARD_EVIDENCE_BLOCKED" in {
        row["code"] for row in gate["blockers"]
    }


def test_formal_delivery_rejects_standard_index_from_another_project():
    kwargs = _base_kwargs()
    kwargs["standard_index"]["project_id"] = "P-OTHER"

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "standard_index_project_mismatch" in check["reasons"]


def test_formal_delivery_binds_standard_index_digest_and_rejects_missing_anchor():
    kwargs = _base_kwargs()
    first = build_delivery_quality_gate(**kwargs)
    kwargs["standard_index"]["standards"][0]["page_anchors"][0][
        "text_sha256"
    ] = "2" * 64
    kwargs["standard_index"]["standards"][0]["cover_identity_text_sha256"] = (
        "2" * 64
    )
    kwargs["standard_index"]["standards"][0]["cover_page_text_sha256"] = (
        "2" * 64
    )

    changed = build_delivery_quality_gate(**kwargs)

    assert first["delivery_allowed"] is True
    assert changed["delivery_allowed"] is False
    assert first["decision_digest"] != changed["decision_digest"]
    changed_check = next(
        row for row in changed["checks"] if row["name"] == "verified_standards"
    )
    assert "standard_index_trusted_rebuild_mismatch" in changed_check["reasons"]

    kwargs["standard_index"]["standards"][0]["page_anchors"] = []
    blocked = build_delivery_quality_gate(**kwargs)
    check = next(
        row for row in blocked["checks"] if row["name"] == "verified_standards"
    )
    assert blocked["delivery_allowed"] is False
    assert check["row_errors"][0]["errors"] == [
        "cover_page_identity_proof_invalid",
        "page_anchor_evidence_missing",
    ]


def test_formal_delivery_rejects_fully_self_consistent_forged_standard_payload():
    kwargs = _base_kwargs()
    forged = kwargs["standard_index"]
    row = forged["standards"][0]
    row.update(
        {
            "filename": "伪造标准.pdf",
            "sha256": "2" * 64,
            "extract_text_sha256": "3" * 64,
            "cover_identity_text_sha256": "4" * 64,
            "cover_page_text_sha256": "4" * 64,
        }
    )
    row["page_anchors"] = [
        {"page": 1, "text_sha256": "4" * 64, "evidence_eligible": True}
    ]
    forged["audit_path"] = "/forged/workspace/audit/ingest.jsonl"
    forged["official_registry_path"] = "/forged/registry.json"
    forged["official_registry_sha256"] = "5" * 64
    forged["chapter_bindings"] = [
        {
            "chapter": "项目参数",
            "standard_code": "GB 50000-2020",
            "sha256": "2" * 64,
            "page": 1,
            "page_text_sha256": "4" * 64,
        }
    ]
    forged["chapter_binding_status"] = "complete"

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "standard_index_trusted_rebuild_mismatch" in check["reasons"]


def test_formal_delivery_reaudits_current_sections_against_trusted_index():
    kwargs = _base_kwargs()
    kwargs["sections"][0]["content"] += "\n消防执行 GB 99999-2099。"
    forged_clean_audit = copy.deepcopy(kwargs["standard_audit"])

    blocked = build_delivery_quality_gate(**kwargs)
    check = next(
        row for row in blocked["checks"] if row["name"] == "verified_standards"
    )
    assert blocked["delivery_allowed"] is False
    assert kwargs["standard_audit"] == forged_clean_audit
    assert "trusted_standard_citation_violations_present" in check["reasons"]
    assert {
        (row["standard_code"], row["reason"])
        for row in check["trusted_citation_violations"]
    } == {
        ("GB 99999-2099", "standard_not_in_verified_project_manifest")
    }

    kwargs = _base_kwargs()
    kwargs["sections"][0]["content"] += "\n消防执行 GB 50000-2020。"
    accepted = build_delivery_quality_gate(**kwargs)
    assert accepted["delivery_allowed"] is True


def test_formal_delivery_requires_trusted_standard_workspace_and_rebuild(monkeypatch):
    kwargs = _base_kwargs()
    kwargs["standard_workspace_dir"] = None
    missing = build_delivery_quality_gate(**kwargs)
    missing_check = next(
        row for row in missing["checks"] if row["name"] == "verified_standards"
    )
    assert "trusted_standard_workspace_missing" in missing_check["reasons"]

    kwargs["standard_workspace_dir"] = "/trusted/workspace"
    monkeypatch.setattr(
        delivery_quality_module,
        "_rebuild_current_standard_index",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("unreadable")),
    )
    failed = build_delivery_quality_gate(**kwargs)
    failed_check = next(
        row for row in failed["checks"] if row["name"] == "verified_standards"
    )
    assert "standard_index_trusted_rebuild_failed" in failed_check["reasons"]


def test_formal_delivery_accepts_only_exact_official_preface_pin(monkeypatch):
    kwargs = _base_kwargs()
    kwargs["standard_audit"]["verified_standard_codes"] = ["GB_55032_2022"]
    index = kwargs["standard_index"]
    row = index["standards"][0]
    row.update(
        {
            "filename": "GB55032-2022 建筑与市政工程施工质量控制通用规范.pdf",
            "standard_code": "GB 55032-2022",
            "standard_codes": ["GB55032-2022"],
            "primary_identity_proof_basis": "official_page_and_content_sha256",
            "primary_identity_cover_code": None,
            "cover_name_status": "verified_official_pin",
            "sha256": "e" * 64,
            "source_hash_proof_status": "verified",
            "source_hash_proof": {
                "status": "verified",
                "basis": "official_content_sha256",
                "expected_sha256": "e" * 64,
                "actual_sha256": "e" * 64,
                "official_document_url": "https://example.gov.cn/gb55032.pdf",
            },
            "official_identity_proof": {
                "official_source": "https://example.gov.cn/gb55032",
                "official_document_url": "https://example.gov.cn/gb55032.pdf",
                "official_content_sha256": "e" * 64,
                "standard_code": "GB 55032-2022",
                "standard_name": "建筑与市政工程施工质量控制通用规范",
                "current_version": "GB 55032-2022",
            },
            "official_registry_status": "verified_metadata_only",
            "official_registry": {
                "status": "verified_metadata_only",
                "standard_code": "GB 55032-2022",
                "standard_name": "建筑与市政工程施工质量控制通用规范",
                "official_source": "https://example.gov.cn/gb55032",
                "official_document_url": "https://example.gov.cn/gb55032.pdf",
                "official_content_sha256": "e" * 64,
                "source_hash_proof_status": "verified",
                "current_version": "GB 55032-2022",
            },
        }
    )
    monkeypatch.setattr(
        delivery_quality_module,
        "_rebuild_current_standard_index",
        lambda **_kwargs: copy.deepcopy(index),
    )

    passed = build_delivery_quality_gate(**kwargs)
    assert passed["delivery_allowed"] is True

    row["official_identity_proof"]["official_content_sha256"] = "f" * 64
    monkeypatch.setattr(
        delivery_quality_module,
        "_rebuild_current_standard_index",
        lambda **_kwargs: copy.deepcopy(index),
    )
    blocked = build_delivery_quality_gate(**kwargs)
    check = next(
        row for row in blocked["checks"] if row["name"] == "verified_standards"
    )
    assert blocked["delivery_allowed"] is False
    assert "primary_identity_official_pin_mismatch" in check["row_errors"][0][
        "errors"
    ]


def test_gb_55037_formal_gate_requires_registry_and_pdf_clause_evidence(
    monkeypatch,
):
    kwargs = _base_kwargs()
    kwargs["standard_audit"].update(
        {
            "verified_standard_count": 1,
            "verified_standard_codes": ["GB_55037_2022"],
        }
    )
    row = kwargs["standard_index"]["standards"][0]
    row.update(
        {
            "filename": "GB 55037-2022 建筑防火通用规范.pdf",
            "standard_code": "GB 55037-2022",
            "standard_codes": ["GB 55037-2022"],
            "primary_identity_proof_basis": "filename_and_cover",
            "primary_identity_cover_code": "GB 55037-2022",
            "cover_identity_text_sha256": "1" * 64,
            "cover_page_text_sha256": "1" * 64,
            "cover_name_status": "verified",
            "source_hash_proof_status": "verified",
            "source_hash_proof": {
                "status": "verified",
                "basis": "official_content_sha256",
                "expected_sha256": "e" * 64,
                "actual_sha256": "e" * 64,
                "official_document_url": "https://official.example/gb55037.pdf",
            },
            "official_registry_status": "verified_metadata_only",
            "official_registry": {
                "status": "verified_metadata_only",
                "standard_code": "GB 55037-2022",
                "metadata_only": True,
                "clause_evidence_eligible": False,
                "official_content_sha256": "e" * 64,
                "source_hash_proof_status": "verified",
            },
            "clause_evidence_eligible": True,
            "clause_evidence_source": "ingested_standard_text",
            "registry_metadata_used_as_clause_evidence": False,
        }
    )

    monkeypatch.setattr(
        delivery_quality_module,
        "_rebuild_current_standard_index",
        lambda **_ignored: copy.deepcopy(kwargs["standard_index"]),
    )
    accepted = build_delivery_quality_gate(**kwargs)
    assert accepted["delivery_allowed"] is True

    row["source_hash_proof_status"] = "mismatch"
    row["source_hash_proof"]["status"] = "mismatch"
    row["source_hash_proof"]["actual_sha256"] = "d" * 64
    hash_mismatch = build_delivery_quality_gate(**kwargs)
    hash_check = next(
        check
        for check in hash_mismatch["checks"]
        if check["name"] == "verified_standards"
    )
    assert hash_mismatch["delivery_allowed"] is False
    assert "official_content_sha256_unverified" in hash_check["row_errors"][0][
        "errors"
    ]
    row["source_hash_proof_status"] = "verified"
    row["source_hash_proof"]["status"] = "verified"
    row["source_hash_proof"]["actual_sha256"] = "e" * 64

    row["official_registry_status"] = "not_verified"
    row["official_registry"]["status"] = "not_verified"
    kwargs["standard_index"]["official_registry_verified_count"] = 0
    missing_metadata = build_delivery_quality_gate(**kwargs)
    metadata_check = next(
        check
        for check in missing_metadata["checks"]
        if check["name"] == "verified_standards"
    )
    assert missing_metadata["delivery_allowed"] is False
    assert "official_registry_unverified" in metadata_check["row_errors"][0][
        "errors"
    ]
    assert "GB_55037_2022" in metadata_check[
        "missing_verified_standard_codes"
    ]
    assert "DELIVERY_STANDARD_EVIDENCE_BLOCKED" in {
        blocker["code"] for blocker in missing_metadata["blockers"]
    }

    row["official_registry_status"] = "verified_metadata_only"
    row["official_registry"]["status"] = "verified_metadata_only"
    kwargs["standard_index"]["official_registry_verified_count"] = 1
    row["page_anchors"] = []
    row["clause_evidence_eligible"] = False
    row["clause_evidence_source"] = None
    row["registry_metadata_used_as_clause_evidence"] = True
    metadata_only = build_delivery_quality_gate(**kwargs)
    evidence_check = next(
        check
        for check in metadata_only["checks"]
        if check["name"] == "verified_standards"
    )
    assert metadata_only["delivery_allowed"] is False
    assert "page_anchor_evidence_missing" in evidence_check["row_errors"][0][
        "errors"
    ]
    assert "registry_metadata_clause_evidence_invalid" in evidence_check[
        "row_errors"
    ][0]["errors"]
    assert "DELIVERY_STANDARD_EVIDENCE_BLOCKED" in {
        blocker["code"] for blocker in metadata_only["blockers"]
    }


def test_formal_delivery_rejects_unrelated_or_registry_unverified_standard():
    kwargs = _base_kwargs()
    row = kwargs["standard_index"]["standards"][0]
    row["standard_code"] = "CJJ 1-2008"
    row["standard_codes"] = ["CJJ 1-2008"]
    row["official_registry_status"] = "not_verified"
    kwargs["standard_index"]["official_registry_verified_count"] = 0

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "standard_rows_untrusted" in check["reasons"]
    assert "standard_citation_codes_absent_from_index" in check["reasons"]
    assert check["missing_verified_standard_codes"] == ["GB_50000_2020"]
    assert "official_registry_unverified" in check["row_errors"][0]["errors"]


def test_referenced_code_does_not_become_verified_primary_standard_identity():
    kwargs = _base_kwargs()
    kwargs["standard_audit"]["verified_standard_codes"] = ["CJJ_1_2008"]
    kwargs["standard_index"]["standards"][0]["standard_codes"].append(
        "CJJ 1-2008"
    )

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert check["index_verified_standard_codes"] == ["GB_50000_2020"]
    assert check["missing_verified_standard_codes"] == ["CJJ_1_2008"]


def test_formal_delivery_rejects_missing_or_boolean_standard_counters():
    kwargs = _base_kwargs()
    kwargs["standard_index"].pop("official_registry_verified_count")
    kwargs["standard_index"]["indexed_standard_count"] = True

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "official_registry_verified_count_missing" in check["reasons"]
    assert "indexed_standard_count_invalid" in check["reasons"]


def test_formal_delivery_malformed_standard_audit_fails_closed_without_exception():
    kwargs = _base_kwargs()
    kwargs["standard_audit"] = {
        "ok": True,
        "verified_standard_count": 1,
        "verified_standard_codes": 1,
        "violation_count": 0,
        "violations": 1,
    }

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "standard_citation_violations_invalid" in check["reasons"]
    assert "verified_standard_codes_invalid" in check["reasons"]


def test_formal_delivery_malformed_standard_rows_fail_closed_without_exception():
    kwargs = _base_kwargs()
    kwargs["standard_index"]["standards"] = 1

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "verified_standards")
    assert gate["delivery_allowed"] is False
    assert "standard_rows_invalid" in check["reasons"]


def test_professional_delivery_gate_rejects_scalar_project_wide_quality_threshold():
    _, original = _formal_parameter_receipts()
    facts = {
        field: {
            "value": original["facts"][field]["value"],
            "unit": original["facts"][field]["unit"],
        }
        for field in _FORMAL_FIELDS
    }
    facts["quality_threshold"] = {"value": "偏差≤5mm", "unit": ""}
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved-facts",
                "source_type": "approved_resolution",
                "facts": facts,
                "evidence": {"locator": "approved.parameters"},
            }
        ]
    )
    kwargs = _base_kwargs()
    kwargs["project_fact_ledger"] = ledger
    kwargs["project_parameters"] = _parameter_report(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    assert gate["delivery_allowed"] is False
    assert check["structured_quality_validation"]["errors"] == [
        {
            "item_id": "quality_threshold",
            "reason": "process_bound_bundle_required",
        }
    ]


def test_professional_delivery_gate_rejects_duplicate_or_untraceable_quality_items():
    _, original = _formal_parameter_receipts()
    valid_item = dict(
        original["facts"]["quality_threshold"]["value"]["items"][0]
    )
    invalid_item = dict(valid_item)
    invalid_item["process"] = "车辆消毒池防水混凝土"
    invalid_item["metric"] = "强度等级"
    invalid_item["value"] = "C25"
    invalid_item["locator"] = "图纸.pdf#p1_deadbeef@1"
    facts = {
        field: {
            "value": original["facts"][field]["value"],
            "unit": original["facts"][field]["unit"],
        }
        for field in _FORMAL_FIELDS
    }
    facts["quality_threshold"] = {
        "value": {
            "mode": "process_bound",
            "items": [valid_item, invalid_item],
        },
        "unit": "",
    }
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved-facts",
                "source_type": "approved_resolution",
                "facts": facts,
                "evidence": {"locator": "approved.parameters"},
            }
        ]
    )
    kwargs = _base_kwargs()
    kwargs["project_fact_ledger"] = ledger
    kwargs["project_parameters"] = _parameter_report(ledger)
    kwargs["sections"] = _bound_sections(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    reasons = {
        row["reason"]
        for row in check["structured_quality_validation"]["errors"]
    }
    assert gate["delivery_allowed"] is False
    assert reasons == {
        "id_duplicate",
        "locator_invalid",
        "locator_evidence_mismatch",
    }


def test_professional_delivery_gate_fails_closed_without_parameter_receipts():
    kwargs = _base_kwargs()
    kwargs["project_parameters"] = {}
    kwargs["project_fact_ledger"] = {}

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    assert "DELIVERY_PROJECT_PARAMETERS_UNRESOLVED" in {
        row["code"] for row in gate["blockers"]
    }
    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert check["available"] is False


def test_professional_delivery_gate_rejects_forged_ledger_digest():
    kwargs = _base_kwargs()
    kwargs["project_fact_ledger"]["ledger_digest"] = "f" * 64
    kwargs["project_parameters"]["project_fact_ledger_digest"] = "f" * 64

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert gate["delivery_allowed"] is False
    assert check["ledger_validation_ok"] is False
    assert "ledger_digest_mismatch" in check["ledger_validation_errors"]


def test_professional_delivery_gate_rejects_stale_parameter_receipt():
    kwargs = _base_kwargs()
    kwargs["project_parameters"]["resolved"][0]["value"] = 120

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert gate["delivery_allowed"] is False
    assert check["receipt_mismatches"] == [
        {"field": "planned_duration_days", "reason": "value"}
    ]


def test_professional_delivery_gate_rejects_receipt_locator_mismatch():
    kwargs = _base_kwargs()
    kwargs["project_parameters"]["resolved"][2]["locator"] = "stale.receipt"

    gate = build_delivery_quality_gate(**kwargs)

    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert gate["delivery_allowed"] is False
    assert check["receipt_mismatches"] == [
        {"field": "critical_interval_days", "reason": "locator"}
    ]


def test_formal_gate_rejects_user_input_without_confirmation_receipt():
    kwargs = _base_kwargs()
    ledger = kwargs["project_fact_ledger"]
    fact = ledger["facts"]["resource_peak"]
    fact["source_type"] = "user_input"
    fact["source_id"] = "run-project-input"
    fact.pop("approval_receipt", None)
    _reseal_ledger(ledger)
    kwargs["project_parameters"] = _parameter_report(ledger)
    kwargs["sections"] = _bound_sections(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    by_field = {row["field"]: row["reasons"] for row in check["source_evidence_errors"]}
    assert gate["delivery_allowed"] is False
    assert "approval_receipt_incomplete" in by_field["resource_peak"]


def test_formal_gate_rejects_unbound_project_identity():
    kwargs = _base_kwargs()
    ledger = kwargs["project_fact_ledger"]
    ledger["project_id"] = None
    _reseal_ledger(ledger)
    kwargs["project_parameters"] = _parameter_report(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    assert gate["delivery_allowed"] is False
    assert check["project_identity_bound"] is False
    assert {
        row["field"] for row in check["source_evidence_errors"]
    } == set(_FORMAL_FIELDS)


def test_formal_gate_rejects_generic_payload_locator_even_with_approval_receipt():
    kwargs = _base_kwargs()
    ledger = kwargs["project_fact_ledger"]
    fact = ledger["facts"]["critical_interval_days"]
    fact["evidence"]["locator"] = (
        "payload.approved_project_fact_resolutions.critical_interval_days"
    )
    _reseal_evidence(fact["evidence"])
    _reseal_ledger(ledger)
    kwargs["project_parameters"] = _parameter_report(ledger)
    kwargs["sections"] = _bound_sections(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    by_field = {row["field"]: row["reasons"] for row in check["source_evidence_errors"]}
    assert gate["delivery_allowed"] is False
    assert "file_locator_invalid" in by_field["critical_interval_days"]


def test_formal_gate_rejects_derived_schedule_fact_without_derivation_receipt():
    kwargs = _base_kwargs()
    ledger = kwargs["project_fact_ledger"]
    fact = ledger["facts"]["resource_peak"]
    fact["status"] = "derived"
    fact["source_type"] = "boq"
    fact["source_id"] = "boq-deterministic-schedule"
    fact.pop("approval_receipt", None)
    fact["evidence"] = {"locator": "boq_wbs_cpm.summary"}
    _reseal_evidence(fact["evidence"])
    readiness = ledger["formal_parameter_readiness"]
    readiness["ready_fields"] = list(_FORMAL_FIELDS)
    readiness["ready"] = True
    _reseal_ledger(ledger)
    kwargs["project_parameters"] = _parameter_report(ledger)
    kwargs["sections"] = _bound_sections(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    by_field = {row["field"]: row["reasons"] for row in check["source_evidence_errors"]}
    assert gate["delivery_allowed"] is False
    assert "derivation_receipt_not_ready" in by_field["resource_peak"]
    assert "derivation_receipt_digest_invalid" in by_field["resource_peak"]


def test_formal_gate_accepts_digest_bound_schedule_derivation_receipt():
    kwargs = _base_kwargs()
    derived = build_project_fact_ledger_from_inputs(
        payload={"project_id": _PROJECT_ID},
        tender={},
        boq_wbs_cpm={
            "summary": {
                "estimated_duration_days": 180,
                "resource_peak": 80,
                "critical_interval_days": 3,
                "schedule_fact_eligible": True,
                "schedule_fact_reasons": [],
                "schedule_input_readiness": {
                    "ready": True,
                    "status": "approved",
                    "locator": "approved:schedule-inputs/receipt-001",
                    "checks": {
                        "productivity_units_verified": True,
                        "resource_allocations_verified": True,
                        "dependencies_verified": True,
                    },
                    "reasons": [],
                },
            }
        },
    )
    ledger = kwargs["project_fact_ledger"]
    for field in ("resource_peak", "critical_interval_days"):
        ledger["facts"][field] = derived["facts"][field]
    _reseal_ledger(ledger)
    kwargs["project_parameters"] = _parameter_report(ledger)
    kwargs["sections"] = _bound_sections(ledger)

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_project_parameters"
    )
    assert check["source_evidence_errors"] == []
    assert gate["delivery_allowed"] is True


def test_professional_delivery_gate_rejects_unbound_parameter_body_statement():
    kwargs = _base_kwargs()
    locator = kwargs["project_fact_ledger"]["facts"]["planned_duration_days"][
        "evidence"
    ]["locator"]
    kwargs["sections"][0]["content"] = kwargs["sections"][0]["content"].replace(
        f"【证据:{locator}】", "", 1
    )

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_parameter_body_binding"
    )
    assert gate["delivery_allowed"] is False
    assert "planned_duration_days" in check["missing_bindings"]
    assert "planned_duration_days" in check["unlocated_statements"]


def test_professional_delivery_gate_rejects_stale_defaults_conflicting_with_ledger():
    report, _ = _formal_parameter_receipts()
    replacements = {
        "planned_duration_days": (150, "天"),
        "resource_peak": (96, "人"),
        "critical_interval_days": (6, "天"),
        "risk_inspection_frequency": ("逐班", ""),
        "quality_threshold": (
            {
                "mode": "process_bound",
                "items": [
                    {
                        "id": "wall-foundation-compaction",
                        "process": "围墙基础持力层压实",
                        "metric": "压实系数",
                        "operator": ">=",
                        "value": 0.98,
                        "unit": "",
                        "status": "approved",
                        "source": "approved_resolution",
                        "locator": f"批准图.pdf#p2_{'b' * 64}@80",
                    }
                ],
            },
            "",
        ),
        "deviation_action_deadline": ("6小时", ""),
    }
    rebuilt = build_project_fact_ledger(
        [
            {
                "source_id": "approved-facts",
                "source_type": "approved_resolution",
                "facts": {
                    field: {"value": value, "unit": unit}
                    for field, (value, unit) in replacements.items()
                },
                "evidence": {"locator": "approved.parameters"},
            }
        ]
    )
    report["project_fact_ledger_digest"] = rebuilt["ledger_digest"]
    report["resolved"] = [
        {
            "field": field,
            "key": field,
            "value": rebuilt["facts"][field]["value"],
            "unit": rebuilt["facts"][field]["unit"],
            "status": rebuilt["facts"][field]["status"],
            "source": rebuilt["facts"][field]["source_type"],
            "locator": rebuilt["facts"][field]["evidence"]["locator"],
        }
        for field in _FORMAL_FIELDS
    ]
    kwargs = _base_kwargs()
    kwargs["project_parameters"] = report
    kwargs["project_fact_ledger"] = rebuilt
    kwargs["sections"] = _bound_sections(rebuilt)
    kwargs["sections"][0]["content"] += (
        "\n旧口径：120天、80人、3天、巡检2次/日、偏差≤5mm、偏差处置时限≤4h。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_parameter_body_binding"
    )
    assert gate["delivery_allowed"] is False
    assert {row["field"] for row in check["conflicting_defaults"]} == set(_FORMAL_FIELDS)


def test_professional_delivery_gate_rejects_unverified_registry_defaults():
    kwargs = _base_kwargs()
    kwargs["sections"][0]["content"] += (
        "\n模板配置：劳动力8人/班，配置20t挖机（1台），作业时长4h/作业段。"
        "【证据:工程量清单(解析统计)】"
    )

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_parameter_body_binding"
    )
    assert gate["delivery_allowed"] is False
    assert {row["name"] for row in check["unverified_registry_defaults"]} == {
        "crew_size",
        "excavator_allocation",
        "work_segment_duration",
    }


def test_three_day_process_duration_is_not_misread_as_critical_interval_default():
    kwargs = _base_kwargs()
    kwargs["sections"][0]["content"] += "\n混凝土养护3天后进入下一道工序。"

    gate = build_delivery_quality_gate(**kwargs)

    check = next(
        row for row in gate["checks"] if row["name"] == "formal_parameter_body_binding"
    )
    assert gate["delivery_allowed"] is True
    assert check["conflicting_defaults"] == []


def test_professional_delivery_gate_rejects_provisional_parameter_even_if_ready_is_claimed():
    kwargs = _base_kwargs()
    field = "risk_inspection_frequency"
    kwargs["project_parameters"]["resolved"][3]["status"] = "provisional"
    kwargs["project_fact_ledger"]["facts"][field]["status"] = "provisional"

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert {row["field"] for row in check["invalid_statuses"]} == {field}
    assert set(check["accepted_statuses"]) == {"verified", "derived", "approved"}


def test_nonformal_preview_does_not_require_formal_parameter_receipts():
    kwargs = _base_kwargs()
    kwargs["formal_delivery_required"] = False
    kwargs["project_parameters"] = {}
    kwargs["project_fact_ledger"] = {}
    kwargs.pop("standard_index")

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is True
    check = next(row for row in gate["checks"] if row["name"] == "formal_project_parameters")
    assert check == {
        "name": "formal_project_parameters",
        "pass": True,
        "required": False,
        "accepted_statuses": ["approved", "derived", "verified"],
    }


def test_professional_delivery_gate_blocks_model_conflict():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"] = {
        "failed_chapters": [],
        "consistency_review": {"ok": True, "summary": "发现工期与资源峰值存在明显冲突。"},
    }
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is False
    assert "DELIVERY_MODEL_REVIEW_BLOCKED" in {
        row["code"] for row in gate["blockers"]
    }


def test_model_review_accepts_machine_readable_pass_decision():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"]["consistency_review"]["summary"] = (
        "DECISION: PASS\n未发现实质性冲突。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is True


def test_machine_pass_is_not_overridden_by_warning_level_inconsistency_text():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"]["consistency_review"]["summary"] = (
        "DECISION: PASS\n环境监测频次前后不一致，列为警告级整改项。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is True
    model_check = next(
        row
        for row in gate["checks"]
        if row["name"] == "independent_model_review"
    )
    assert model_check["machine_decision"] == "PASS"


def test_model_review_machine_readable_block_overrides_pass_phrase():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"]["consistency_review"]["summary"] = (
        "DECISION: BLOCK\n虽然某些项目未发现实质性冲突，但工期口径不一致。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False


def test_professional_delivery_gate_blocks_incomplete_boq_cross_index():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {
        "ok": True,
        "focus_count": 3,
        "mentioned_count": 3,
        "closed_ok_count": 2,
        "missing_drawing_locator_count": 1,
        "missing_standard_locator_count": 0,
        "focus_items": [
            {"name": "钢筋"},
            {"name": "模板"},
            {"name": "混凝土"},
        ],
    }
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_BLOCKED" in {
        row["code"] for row in gate["blockers"]
    }


def test_professional_delivery_gate_fails_closed_when_cross_index_is_unavailable():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {
        "ok": False,
        "build_failed": True,
        "focus_count": 3,
        "mentioned_count": 0,
        "closed_ok_count": 0,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
        "focus_items": [],
    }

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_UNAVAILABLE" in {
        row["code"] for row in gate["blockers"]
    }


def test_professional_delivery_gate_fails_closed_on_empty_cross_index_result():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {}

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_UNAVAILABLE" in {
        row["code"] for row in gate["blockers"]
    }


def test_model_review_is_informational_when_not_required():
    kwargs = _base_kwargs()
    kwargs["model_review_required"] = False
    kwargs["model_review_audit"] = {}
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is True
    assert gate["warning_count"] == 1
