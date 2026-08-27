from __future__ import annotations

from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger

_FORMAL_FIELDS = (
    "planned_duration_days",
    "resource_peak",
    "critical_interval_days",
    "risk_inspection_frequency",
    "quality_threshold",
    "deviation_action_deadline",
)


def _formal_parameter_receipts() -> tuple[dict, dict]:
    statuses = ("verified", "derived", "approved", "verified", "derived", "approved")
    values = (180, 80, 3, "2次/日", "偏差≤5mm", "4h")
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "test-project-facts",
                "source_type": "user_input",
                "facts": {
                    field: {
                        "value": value,
                        "unit": "",
                        "status": status,
                        "evidence": {"locator": f"test.{field}"},
                    }
                    for field, value, status in zip(_FORMAL_FIELDS, values, statuses)
                },
                "evidence": {"locator": "test.project_facts"},
            }
        ]
    )
    resolved = []
    for field in _FORMAL_FIELDS:
        fact = ledger["facts"][field]
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
    report = {
        "schema_version": "missing-parameter-probe-v2",
        "ok": True,
        "formal_ready": True,
        "accepted_statuses": ["approved", "derived", "verified"],
        "resolved": resolved,
        "missing": [],
        "provisional": [],
        "blocked_fields": [],
        "auto_fill": {},
        "project_fact_ledger_digest": ledger["ledger_digest"],
    }
    return report, ledger


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
        lines.append(
            f"{labels[field]}={fact['value']}{fact['unit']}【证据:{locator}】"
        )
    return [{"title": "项目参数", "content": "\n".join(lines)}]


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
        "standard_audit": {"ok": True, "violations": []},
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
    assert len(gate["decision_digest"]) == 64


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


def test_professional_delivery_gate_rejects_unbound_parameter_body_statement():
    kwargs = _base_kwargs()
    kwargs["sections"][0]["content"] = kwargs["sections"][0]["content"].replace(
        "【证据:test.planned_duration_days】", "", 1
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
        "quality_threshold": ("按工序允许偏差表", ""),
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
