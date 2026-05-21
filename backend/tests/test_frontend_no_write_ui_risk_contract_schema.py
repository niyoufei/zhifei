import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "risk_summary",
    "no_write_ui_principles",
    "word_button_risk_contract",
    "blocked_reasons_display_contract",
    "evidence_boundary_display_contract",
    "formal_chain_entry_control",
    "acceptance_criteria",
    "future_steps",
}

CURRENT_STAGE_FORMAL_FLAGS = {
    "formal_writeback_allowed": False,
    "review_apply_allowed": False,
    "docx_export_allowed": False,
    "zbid_writeback_allowed": False,
    "output_write_allowed": False,
}

FORBIDDEN_IMPORTS = {
    "orchestrator",
    "llm_client",
    "provider",
    "generation",
    "export",
    "review",
    "actions_bridge",
    "zbid",
    "fastapi",
    "requests",
    "httpx",
    "ollama",
    "docx",
}


def make_fake_frontend_no_write_ui_risk_contract(**overrides):
    contract = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "risk_summary": {
            "word_document_entry_present": True,
            "preview_only_hint_missing_currently": True,
            "no_write_hint_missing_currently": True,
            "blocked_reasons_missing_currently": True,
            "evidence_boundary_missing_currently": True,
            "user_may_misread_preview_as_formal_generation": True,
            "user_may_misread_advisory_as_evidence": True,
            "export_docx_route_seen": False,
            "review_apply_route_seen": False,
            "zbid_entry_seen": False,
        },
        "no_write_ui_principles": {
            "preview_only_must_be_explicit": True,
            "no_write_must_be_explicit": True,
            "ai_advisory_must_not_display_as_evidence": True,
            "preview_advisory_must_not_display_as_evidence": True,
            "preview_must_not_display_as_formal_body": True,
            "blocked_reasons_must_be_readable": True,
            "formal_chain_entries_disabled_hidden_or_unavailable": True,
            "formal_flags_must_remain_false": True,
        },
        "word_button_risk_contract": {
            "preview_only_stage_must_not_show_as_submittable_formal_generate_button": True,
            "if_kept_entry_must_be_disabled": True,
            "if_button_visible_must_label_formal_export_unavailable": True,
            "if_button_visible_must_label_no_formal_body_writeback": True,
            "if_button_visible_must_label_no_docx_generation": True,
            "if_button_visible_must_label_no_output_job_export_write": True,
            "must_not_trigger_generate": True,
            "must_not_trigger_export_docx": True,
            "must_not_write_output_job_export": True,
            "must_not_generate_docx": True,
        },
        "blocked_reasons_display_contract": {
            "blocked_reasons_must_be_readable": True,
            "must_match_preview_safe_no_write_status": True,
            "must_explain_why_generation_blocked": True,
            "must_explain_why_docx_export_blocked": True,
            "must_explain_why_review_apply_blocked": True,
            "must_explain_why_zbid_writeback_blocked": True,
            "must_explain_why_formal_writeback_blocked": True,
            "must_explain_why_output_write_blocked": True,
            "must_not_be_debug_only": True,
            "must_not_rely_only_on_color": True,
        },
        "evidence_boundary_display_contract": {
            "ai_advisory_must_not_be_evidence": True,
            "preview_advisory_must_not_be_evidence": True,
            "shadow_candidate_must_not_be_evidence": True,
            "patch_preview_must_not_be_evidence": True,
            "diff_preview_must_not_be_evidence": True,
            "rollback_plan_must_not_be_evidence": True,
            "dry_run_result_must_not_be_evidence": True,
            "zbid_preview_scoring_must_not_be_evidence": True,
            "evidence_must_come_from_verifiable_anchor": True,
            "preview_is_not_formal_body": True,
        },
        "formal_chain_entry_control": {
            "docx_export_blocked": True,
            "review_apply_blocked": True,
            "zbid_writeback_blocked": True,
            "formal_writeback_blocked": True,
            "output_write_blocked": True,
            "docx_export_entry_disabled_hidden_or_unavailable": True,
            "review_apply_entry_disabled_hidden_or_unavailable": True,
            "zbid_writeback_entry_disabled_hidden_or_unavailable": True,
            "formal_writeback_entry_disabled_hidden_or_unavailable": True,
            "disabled_entries_include_reason": True,
            "must_not_trigger_generate": True,
            "must_not_trigger_export_docx": True,
            "must_not_trigger_review_apply": True,
            "must_not_trigger_zbid_writeback": True,
            "must_not_trigger_formal_writeback": True,
            "must_not_write_output_job_export": True,
        },
        "acceptance_criteria": {
            "user_can_see_preview_only": True,
            "user_can_see_no_write": True,
            "user_cannot_misread_word_formal_generation_available": True,
            "user_cannot_misread_docx_export_available": True,
            "user_cannot_misread_zbid_writeback_available": True,
            "user_cannot_misread_review_apply_available": True,
            "user_cannot_misread_formal_writeback_available": True,
            "user_cannot_misread_advisory_as_evidence": True,
            "user_cannot_misread_preview_as_formal_body": True,
            "ui_cannot_trigger_formal_chain": True,
            "blocked_reasons_readable": True,
            "evidence_boundary_readable": True,
            "all_formal_flags_false": True,
            "no_output_job_export_write": True,
        },
        "future_steps": {
            "step_165_frontend_no_write_ui_risk_contract_fake_schema_tests": True,
            "tests_only": True,
            "frontend_code_must_not_change_in_this_step": True,
            "code_fix_requires_later_separate_authorization": True,
            "do_not_enter_50_person_deployment_design": True,
        },
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        "execution_side_effects": {
            "backend_started": False,
            "frontend_started": False,
            "ollama_run": False,
            "local_port_accessed": False,
            "network_called": False,
            "output_job_export_written": False,
            "docx_generated": False,
            "zbid_called": False,
            "generate_triggered": False,
            "export_docx_triggered": False,
            "review_apply_triggered": False,
            "local_deployment_executed": False,
            "entered_50_person_deployment_design": False,
        },
    }
    contract.update(overrides)
    return contract


def validate_fake_frontend_no_write_ui_risk_contract(contract):
    reasons = []

    if not isinstance(contract, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_frontend_no_write_ui_contract"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(contract)
    if missing_sections:
        reasons.append("missing_required_frontend_no_write_ui_sections")

    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        if contract.get("formal_flags", {}).get(flag) is not expected:
            reasons.append(f"{flag}_must_be_false")

    if any(contract.get("execution_side_effects", {}).values()):
        reasons.append("execution_side_effects_must_not_be_performed")

    return {
        "status": "blocked" if reasons else "accepted_fake_schema_only",
        "blocked_reasons": reasons,
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
    }


def assert_required_items(section, expected_items):
    assert expected_items.issubset(section)


def test_frontend_no_write_ui_contract_sections_are_explicit():
    contract = make_fake_frontend_no_write_ui_risk_contract()

    assert REQUIRED_SECTIONS.issubset(contract)
    assert validate_fake_frontend_no_write_ui_risk_contract(contract) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_word_document_entry_is_not_formal_generation_permission():
    contract = make_fake_frontend_no_write_ui_risk_contract()
    word_contract = contract["word_button_risk_contract"]

    assert word_contract[
        "preview_only_stage_must_not_show_as_submittable_formal_generate_button"
    ]
    assert word_contract["if_kept_entry_must_be_disabled"] is True
    assert word_contract["if_button_visible_must_label_formal_export_unavailable"] is True
    assert word_contract["must_not_trigger_generate"] is True
    assert word_contract["must_not_trigger_export_docx"] is True
    assert word_contract["must_not_write_output_job_export"] is True
    assert word_contract["must_not_generate_docx"] is True


def test_preview_only_no_write_blocked_reasons_and_evidence_copy_are_required():
    contract = make_fake_frontend_no_write_ui_risk_contract()
    principles = contract["no_write_ui_principles"]
    blocked = contract["blocked_reasons_display_contract"]
    evidence = contract["evidence_boundary_display_contract"]
    acceptance = contract["acceptance_criteria"]

    assert principles["preview_only_must_be_explicit"] is True
    assert principles["no_write_must_be_explicit"] is True
    assert blocked["blocked_reasons_must_be_readable"] is True
    assert evidence["ai_advisory_must_not_be_evidence"] is True
    assert evidence["preview_advisory_must_not_be_evidence"] is True
    assert evidence["preview_is_not_formal_body"] is True
    assert acceptance["user_can_see_preview_only"] is True
    assert acceptance["user_can_see_no_write"] is True
    assert acceptance["user_cannot_misread_advisory_as_evidence"] is True
    assert acceptance["user_cannot_misread_preview_as_formal_body"] is True


def test_formal_chain_entries_are_blocked():
    contract = make_fake_frontend_no_write_ui_risk_contract()

    assert_required_items(
        contract["formal_chain_entry_control"],
        {
            "docx_export_blocked",
            "review_apply_blocked",
            "zbid_writeback_blocked",
            "formal_writeback_blocked",
            "output_write_blocked",
            "docx_export_entry_disabled_hidden_or_unavailable",
            "review_apply_entry_disabled_hidden_or_unavailable",
            "zbid_writeback_entry_disabled_hidden_or_unavailable",
            "formal_writeback_entry_disabled_hidden_or_unavailable",
            "must_not_trigger_generate",
            "must_not_trigger_export_docx",
            "must_not_trigger_review_apply",
            "must_not_trigger_zbid_writeback",
            "must_not_trigger_formal_writeback",
            "must_not_write_output_job_export",
        },
    )
    assert all(contract["formal_chain_entry_control"].values())


def test_formal_flags_are_always_false():
    contract = make_fake_frontend_no_write_ui_risk_contract()

    assert contract["formal_flags"] == CURRENT_STAGE_FORMAL_FLAGS
    assert validate_fake_frontend_no_write_ui_risk_contract(contract)["formal_flags"] == {
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
    }


def test_acceptance_criteria_prevent_preview_and_advisory_misread():
    contract = make_fake_frontend_no_write_ui_risk_contract()

    assert_required_items(
        contract["acceptance_criteria"],
        {
            "user_can_see_preview_only",
            "user_can_see_no_write",
            "user_cannot_misread_word_formal_generation_available",
            "user_cannot_misread_docx_export_available",
            "user_cannot_misread_zbid_writeback_available",
            "user_cannot_misread_review_apply_available",
            "user_cannot_misread_formal_writeback_available",
            "user_cannot_misread_advisory_as_evidence",
            "user_cannot_misread_preview_as_formal_body",
            "ui_cannot_trigger_formal_chain",
            "blocked_reasons_readable",
            "evidence_boundary_readable",
            "all_formal_flags_false",
            "no_output_job_export_write",
        },
    )
    assert all(contract["acceptance_criteria"].values())


def test_frontend_no_write_ui_schema_has_no_execution_side_effects():
    contract = make_fake_frontend_no_write_ui_risk_contract()
    side_effects = contract["execution_side_effects"]

    assert side_effects == {
        "backend_started": False,
        "frontend_started": False,
        "ollama_run": False,
        "local_port_accessed": False,
        "network_called": False,
        "output_job_export_written": False,
        "docx_generated": False,
        "zbid_called": False,
        "generate_triggered": False,
        "export_docx_triggered": False,
        "review_apply_triggered": False,
        "local_deployment_executed": False,
        "entered_50_person_deployment_design": False,
    }
    assert validate_fake_frontend_no_write_ui_risk_contract(contract)["blocked_reasons"] == []


def test_frontend_no_write_ui_schema_imports_do_not_pull_main_chain_or_service_modules():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.lower())

    assert "pathlib" in imported_modules
    for module in imported_modules:
        module_parts = set(module.split("."))
        assert module not in FORBIDDEN_IMPORTS
        assert not (module_parts & FORBIDDEN_IMPORTS)
