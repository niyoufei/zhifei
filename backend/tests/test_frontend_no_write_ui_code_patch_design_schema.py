import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "current_ui_risks",
    "future_code_patch_scope",
    "word_button_patch_design",
    "status_notice_patch_design",
    "formal_chain_entry_control",
    "acceptance_criteria",
    "next_steps",
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


def make_fake_frontend_no_write_ui_code_patch_design(**overrides):
    design = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "current_ui_risks": {
            "word_document_entry_still_present": True,
            "preview_only_no_write_blocked_reasons_evidence_hints_missing": True,
            "preview_only_hint_missing": True,
            "no_write_hint_missing": True,
            "blocked_reasons_display_missing": True,
            "evidence_boundary_hint_missing": True,
            "user_may_misread_word_formal_generation_available": True,
            "user_may_misread_word_formal_export_available": True,
        },
        "future_code_patch_scope": {
            "locate_frontend_page_file": True,
            "locate_word_document_button": True,
            "locate_status_notice_area": True,
            "locate_blocked_reasons_display_area": True,
            "future_only_no_change_in_this_step": True,
            "must_not_touch_generation_chain": True,
            "must_not_touch_docx_export_chain": True,
            "must_not_touch_review_apply_chain": True,
            "must_not_touch_zbid_writeback_chain": True,
            "must_not_touch_formal_writeback_chain": True,
            "must_not_touch_output_job_export_write_chain": True,
        },
        "word_button_patch_design": {
            "disable_word_document_button_in_preview_only": True,
            "change_copy_to_formal_export_unavailable": True,
            "equivalent_unavailable_hint_allowed": True,
            "must_not_show_as_submittable_formal_generate_button": True,
            "must_not_trigger_generate": True,
            "must_not_trigger_export_docx": True,
            "must_not_generate_docx": True,
            "must_not_write_output_job_export": True,
        },
        "status_notice_patch_design": {
            "show_preview_only": True,
            "show_no_write": True,
            "show_blocked_reasons": True,
            "show_advisory_is_not_evidence": True,
            "show_preview_is_not_formal_body": True,
            "blocked_reasons_must_be_readable": True,
            "must_not_be_debug_only": True,
        },
        "formal_chain_entry_control": {
            "docx_export_disabled": True,
            "review_apply_disabled": True,
            "zbid_writeback_disabled": True,
            "formal_writeback_disabled": True,
            "output_write_disabled": True,
            "formal_entries_disabled_or_explicitly_unavailable": True,
            "must_not_trigger_generate": True,
            "must_not_trigger_export_docx": True,
            "must_not_trigger_review_apply": True,
            "must_not_trigger_zbid_writeback": True,
            "must_not_trigger_formal_writeback": True,
            "must_not_write_output_job_export": True,
        },
        "acceptance_criteria": {
            "page_shows_preview_only": True,
            "page_shows_no_write": True,
            "user_cannot_misread_word_formal_generation_available": True,
            "user_cannot_misread_word_formal_export_available": True,
            "user_cannot_misread_advisory_as_evidence": True,
            "preview_not_displayed_as_formal_body": True,
            "blocked_reasons_readable": True,
            "formal_chain_entries_disabled_or_unavailable": True,
            "formal_writeback_allowed": False,
            "review_apply_allowed": False,
            "docx_export_allowed": False,
            "zbid_writeback_allowed": False,
            "output_write_allowed": False,
            "must_not_write_output_job_export": True,
        },
        "next_steps": {
            "step_170_frontend_no_write_ui_code_patch_design_fake_schema_tests": True,
            "step_171_frontend_no_write_ui_code_patch_implementation": True,
            "implementation_requires_separate_authorization": True,
            "tests_only_current_step": True,
            "do_not_modify_frontend_current_step": True,
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
    design.update(overrides)
    return design


def validate_fake_frontend_no_write_ui_code_patch_design(design):
    reasons = []

    if not isinstance(design, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_frontend_no_write_ui_code_patch_design"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(design)
    if missing_sections:
        reasons.append("missing_required_frontend_no_write_ui_code_patch_sections")

    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        if design.get("formal_flags", {}).get(flag) is not expected:
            reasons.append(f"{flag}_must_be_false")

    if any(design.get("execution_side_effects", {}).values()):
        reasons.append("execution_side_effects_must_not_be_performed")

    return {
        "status": "blocked" if reasons else "accepted_fake_schema_only",
        "blocked_reasons": reasons,
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
    }


def assert_required_items(section, expected_items):
    assert expected_items.issubset(section)


def test_frontend_no_write_ui_code_patch_design_sections_are_explicit():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert REQUIRED_SECTIONS.issubset(design)
    assert validate_fake_frontend_no_write_ui_code_patch_design(design) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_current_ui_risks_are_locked():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert_required_items(
        design["current_ui_risks"],
        {
            "word_document_entry_still_present",
            "preview_only_no_write_blocked_reasons_evidence_hints_missing",
            "preview_only_hint_missing",
            "no_write_hint_missing",
            "blocked_reasons_display_missing",
            "evidence_boundary_hint_missing",
        },
    )
    assert all(design["current_ui_risks"].values())


def test_future_code_patch_scope_is_frontend_only_and_blocks_formal_chains():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert_required_items(
        design["future_code_patch_scope"],
        {
            "locate_frontend_page_file",
            "locate_word_document_button",
            "locate_status_notice_area",
            "locate_blocked_reasons_display_area",
            "must_not_touch_generation_chain",
            "must_not_touch_docx_export_chain",
            "must_not_touch_review_apply_chain",
            "must_not_touch_zbid_writeback_chain",
        },
    )


def test_word_button_patch_design_disables_formal_word_generation():
    design = make_fake_frontend_no_write_ui_code_patch_design()
    word_button = design["word_button_patch_design"]

    assert word_button["disable_word_document_button_in_preview_only"] is True
    assert word_button["change_copy_to_formal_export_unavailable"] is True
    assert word_button["equivalent_unavailable_hint_allowed"] is True
    assert word_button["must_not_show_as_submittable_formal_generate_button"] is True
    assert word_button["must_not_trigger_generate"] is True
    assert word_button["must_not_trigger_export_docx"] is True


def test_status_notice_patch_design_exposes_preview_no_write_and_evidence_boundary():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert_required_items(
        design["status_notice_patch_design"],
        {
            "show_preview_only",
            "show_no_write",
            "show_blocked_reasons",
            "show_advisory_is_not_evidence",
            "show_preview_is_not_formal_body",
        },
    )
    assert all(design["status_notice_patch_design"].values())


def test_formal_chain_entry_control_keeps_all_entries_blocked():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert_required_items(
        design["formal_chain_entry_control"],
        {
            "docx_export_disabled",
            "review_apply_disabled",
            "zbid_writeback_disabled",
            "formal_writeback_disabled",
            "output_write_disabled",
            "formal_entries_disabled_or_explicitly_unavailable",
            "must_not_trigger_generate",
            "must_not_trigger_export_docx",
            "must_not_trigger_review_apply",
            "must_not_trigger_zbid_writeback",
            "must_not_write_output_job_export",
        },
    )


def test_acceptance_criteria_keep_user_from_misreading_preview_as_formal_output():
    design = make_fake_frontend_no_write_ui_code_patch_design()
    acceptance = design["acceptance_criteria"]

    assert acceptance["page_shows_preview_only"] is True
    assert acceptance["page_shows_no_write"] is True
    assert acceptance["user_cannot_misread_word_formal_generation_available"] is True
    assert acceptance["user_cannot_misread_advisory_as_evidence"] is True
    assert acceptance["preview_not_displayed_as_formal_body"] is True
    assert acceptance["blocked_reasons_readable"] is True
    assert acceptance["formal_chain_entries_disabled_or_unavailable"] is True
    assert acceptance["must_not_write_output_job_export"] is True


def test_formal_flags_are_always_false():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert design["formal_flags"] == CURRENT_STAGE_FORMAL_FLAGS
    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        assert design["acceptance_criteria"][flag] is expected


def test_frontend_no_write_ui_code_patch_design_schema_has_no_execution_side_effects():
    design = make_fake_frontend_no_write_ui_code_patch_design()

    assert validate_fake_frontend_no_write_ui_code_patch_design(design) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }
    assert not any(design["execution_side_effects"].values())


def test_frontend_no_write_ui_code_patch_design_imports_do_not_pull_main_chain_or_service_modules():
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0].lower())
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0].lower())

    assert not (FORBIDDEN_IMPORTS & imported_roots)
