from backend.zhifei_autoplan.system_autonomy_evidence import (
    GATE_REPORT_REQUIRED_FIELDS,
    build_gate_report_template,
    validate_gate_report,
)


def test_gate_report_template_contains_required_fields():
    template = build_gate_report_template()

    assert set(GATE_REPORT_REQUIRED_FIELDS).issubset(template)


def test_missing_fields_block_evidence_chain():
    result = validate_gate_report({"node_name": "SYSTEM-AUTONOMY-006"})

    assert result.complete is False
    assert "completed" in result.missing_fields
    assert "gate_report_required_fields_missing" in result.blocked_reasons


def test_forbidden_confirmation_blocks_report():
    report = {
        field: "evidence" for field in GATE_REPORT_REQUIRED_FIELDS
    }
    report.update(
        {
            "completed": True,
            "new_codex_thread": True,
            "goal_mode_used": False,
            "git_status_short_clean": True,
            "changed_files_authorized_only": True,
            "runtime_script_body_read": True,
            "stopped_without_next_node": True,
        }
    )

    result = validate_gate_report(report)

    assert result.complete is False
    assert result.forbidden_confirmations_triggered == ("runtime_script_body_read",)
    assert "forbidden_confirmation_field_triggered" in result.blocked_reasons
