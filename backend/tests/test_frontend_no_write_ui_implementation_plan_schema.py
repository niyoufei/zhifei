import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "confirmed_ui_risks",
    "implementation_goals",
    "future_change_scope",
    "ui_state_design",
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


def make_fake_frontend_no_write_ui_implementation_plan(**overrides):
    plan = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "confirmed_ui_risks": {
            "word_document_entry_present": True,
            "preview_only_hint_missing": True,
            "no_write_hint_missing": True,
            "blocked_reasons_display_missing": True,
            "evidence_boundary_hint_missing": True,
            "user_may_misread_word_formal_generation_available": True,
            "user_may_misread_word_formal_export_available": True,
        },
        "implementation_goals": {
            "page_must_show_preview_only": True,
            "page_must_show_no_write": True,
            "word_entry_disabled_hidden_or_formal_export_unavailable": True,
            "add_blocked_reasons_display": True,
            "add_advisory_evidence_boundary_copy": True,
            "prevent_generate_route_trigger": True,
            "prevent_export_docx_route_trigger": True,
            "prevent_review_apply_route_trigger": True,
            "prevent_zbid_writeback_trigger": True,
            "prevent_formal_writeback_trigger": True,
            "prevent_output_job_export_write": True,
            "all_formal_flags_false": True,
        },
        "future_change_scope": {
            "future_only_no_change_in_this_step": True,
            "may_touch_frontend_page_template_later": True,
            "may_touch_button_state_later": True,
            "may_touch_status_copy_later": True,
            "may_touch_blocked_reasons_component_later": True,
            "may_touch_evidence_boundary_copy_later": True,
            "must_not_touch_generation_chain": True,
            "must_not_touch_docx_export_chain": True,
            "must_not_touch_review_apply_chain": True,
            "must_not_touch_zbid_writeback_chain": True,
            "must_not_touch_formal_writeback_chain": True,
            "must_not_touch_output_job_export_write_chain": True,
        },
        "ui_state_design": {
            "preview_only": {
                "state_visible": True,
                "preview_is_not_formal_body": True,
                "preview_is_not_writeback_permission": True,
                "must_not_trigger_docx_export": True,
                "must_not_trigger_zbid_writeback": True,
            },
            "no_write": {
                "state_visible": True,
                "does_not_write_formal_body": True,
                "does_not_write_output_job_export": True,
                "does_not_update_deliverables": True,
                "does_not_trigger_review_apply": True,
                "does_not_trigger_zbid_writeback": True,
            },
            "blocked": {
                "blocked_reasons_visible": True,
                "explains_generation_blocked": True,
                "explains_docx_export_blocked": True,
                "explains_review_apply_blocked": True,
                "explains_zbid_writeback_blocked": True,
                "explains_output_write_blocked": True,
            },
            "evidence_missing": {
                "shows_blocked_or_requires_human_review": True,
                "ai_advisory_is_not_evidence": True,
                "preview_advisory_is_not_evidence": True,
                "candidate_patch_diff_rollback_dry_run_are_not_evidence": True,
                "evidence_must_have_verifiable_anchor": True,
                "scoring_clause_refs_must_be_verifiable": True,
            },
            "formal_export_disabled": {
                "word_document_entry_covered": True,
                "docx_export_entry_covered": True,
                "button_disabled_or_hidden": True,
                "formal_export_unavailable_copy_visible": True,
                "must_not_show_as_submittable_formal_generate_button": True,
            },
            "zbid_writeback_disabled": {
                "zbid_writeback_entry_covered": True,
                "zbid_preview_scoring_is_not_evidence": True,
                "accepted_preview_is_not_writeback_permission": True,
                "zbid_writeback_allowed": False,
            },
        },
        "acceptance_criteria": {
            "user_can_see_current_preview_only": True,
            "user_can_see_current_no_write": True,
            "user_cannot_misread_word_as_formal_generation_available": True,
            "advisory_must_not_display_as_evidence": True,
            "preview_must_not_display_as_formal_body": True,
            "blocked_reasons_must_be_readable": True,
            "formal_chain_entries_disabled_or_unavailable": True,
            "must_not_write_output_job_export": True,
            "must_not_trigger_generate": True,
            "must_not_trigger_export_docx": True,
            "must_not_trigger_review_apply": True,
            "must_not_trigger_zbid_writeback": True,
            "all_formal_flags_false": True,
        },
        "next_steps": {
            "step_168_frontend_no_write_ui_implementation_plan_fake_schema_tests": True,
            "step_169_frontend_no_write_ui_code_patch_design": True,
            "code_changes_require_separate_authorization": True,
            "tests_only_current_step": True,
            "do_not_modify_frontend_code_current_step": True,
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
    plan.update(overrides)
    return plan


def validate_fake_frontend_no_write_ui_implementation_plan(plan):
    reasons = []

    if not isinstance(plan, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_frontend_no_write_ui_implementation_plan"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(plan)
    if missing_sections:
        reasons.append("missing_required_frontend_no_write_ui_plan_sections")

    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        if plan.get("formal_flags", {}).get(flag) is not expected:
            reasons.append(f"{flag}_must_be_false")

    if any(plan.get("execution_side_effects", {}).values()):
        reasons.append("execution_side_effects_must_not_be_performed")

    return {
        "status": "blocked" if reasons else "accepted_fake_schema_only",
        "blocked_reasons": reasons,
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
    }


def assert_required_items(section, expected_items):
    assert expected_items.issubset(section)


def test_frontend_no_write_ui_implementation_plan_sections_are_explicit():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert REQUIRED_SECTIONS.issubset(plan)
    assert validate_fake_frontend_no_write_ui_implementation_plan(plan) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_confirmed_ui_risks_are_locked():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert_required_items(
        plan["confirmed_ui_risks"],
        {
            "word_document_entry_present",
            "preview_only_hint_missing",
            "no_write_hint_missing",
            "blocked_reasons_display_missing",
            "evidence_boundary_hint_missing",
            "user_may_misread_word_formal_generation_available",
            "user_may_misread_word_formal_export_available",
        },
    )
    assert all(plan["confirmed_ui_risks"].values())


def test_implementation_goals_keep_ui_preview_only_and_no_write():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert_required_items(
        plan["implementation_goals"],
        {
            "page_must_show_preview_only",
            "page_must_show_no_write",
            "word_entry_disabled_hidden_or_formal_export_unavailable",
            "add_blocked_reasons_display",
            "add_advisory_evidence_boundary_copy",
            "prevent_generate_route_trigger",
            "prevent_export_docx_route_trigger",
            "prevent_review_apply_route_trigger",
            "prevent_zbid_writeback_trigger",
            "all_formal_flags_false",
        },
    )
    assert all(plan["implementation_goals"].values())


def test_future_change_scope_is_frontend_ui_only_and_blocks_formal_chains():
    plan = make_fake_frontend_no_write_ui_implementation_plan()
    scope = plan["future_change_scope"]

    assert scope["future_only_no_change_in_this_step"] is True
    assert scope["may_touch_frontend_page_template_later"] is True
    assert scope["may_touch_button_state_later"] is True
    assert scope["may_touch_status_copy_later"] is True
    assert scope["may_touch_blocked_reasons_component_later"] is True
    assert scope["may_touch_evidence_boundary_copy_later"] is True
    assert scope["must_not_touch_generation_chain"] is True
    assert scope["must_not_touch_docx_export_chain"] is True
    assert scope["must_not_touch_review_apply_chain"] is True
    assert scope["must_not_touch_zbid_writeback_chain"] is True
    assert scope["must_not_touch_output_job_export_write_chain"] is True


def test_ui_state_design_declares_required_states():
    plan = make_fake_frontend_no_write_ui_implementation_plan()
    states = plan["ui_state_design"]

    assert_required_items(
        states,
        {
            "preview_only",
            "no_write",
            "blocked",
            "evidence_missing",
            "formal_export_disabled",
            "zbid_writeback_disabled",
        },
    )
    assert states["preview_only"]["state_visible"] is True
    assert states["no_write"]["state_visible"] is True
    assert states["blocked"]["blocked_reasons_visible"] is True
    assert states["evidence_missing"]["shows_blocked_or_requires_human_review"] is True
    assert states["formal_export_disabled"]["button_disabled_or_hidden"] is True
    assert states["zbid_writeback_disabled"]["zbid_writeback_allowed"] is False


def test_acceptance_criteria_prevent_formal_ui_misread_and_writes():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert_required_items(
        plan["acceptance_criteria"],
        {
            "user_can_see_current_preview_only",
            "user_can_see_current_no_write",
            "user_cannot_misread_word_as_formal_generation_available",
            "advisory_must_not_display_as_evidence",
            "preview_must_not_display_as_formal_body",
            "blocked_reasons_must_be_readable",
            "formal_chain_entries_disabled_or_unavailable",
            "must_not_write_output_job_export",
            "must_not_trigger_generate",
            "must_not_trigger_export_docx",
            "must_not_trigger_review_apply",
            "must_not_trigger_zbid_writeback",
            "all_formal_flags_false",
        },
    )
    assert all(plan["acceptance_criteria"].values())


def test_next_steps_require_tests_first_and_later_code_authorization():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert plan["next_steps"] == {
        "step_168_frontend_no_write_ui_implementation_plan_fake_schema_tests": True,
        "step_169_frontend_no_write_ui_code_patch_design": True,
        "code_changes_require_separate_authorization": True,
        "tests_only_current_step": True,
        "do_not_modify_frontend_code_current_step": True,
        "do_not_enter_50_person_deployment_design": True,
    }


def test_formal_flags_are_always_false():
    plan = make_fake_frontend_no_write_ui_implementation_plan()

    assert plan["formal_flags"] == CURRENT_STAGE_FORMAL_FLAGS
    assert validate_fake_frontend_no_write_ui_implementation_plan(plan)["formal_flags"] == {
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
    }


def test_frontend_no_write_ui_implementation_plan_has_no_execution_side_effects():
    plan = make_fake_frontend_no_write_ui_implementation_plan()
    side_effects = plan["execution_side_effects"]

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
    assert validate_fake_frontend_no_write_ui_implementation_plan(plan)["blocked_reasons"] == []


def test_frontend_no_write_ui_implementation_plan_imports_do_not_pull_main_chain_or_service_modules():
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
