import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "current_baseline",
    "frontend_integration_goal",
    "frontend_state_display_design",
    "forbidden_behaviors",
    "future_code_scope",
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


def make_fake_preview_only_route_frontend_integration_plan(**overrides):
    plan = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "current_baseline": {
            "local_trial_preview_only_route_implemented": True,
            "runtime_smoke_passed": True,
            "preview_packet_readable": True,
            "validator_result_readable": True,
            "blocked_reasons_readable": True,
            "frontend_no_write_ui_fixed": True,
            "frontend_no_write_ui_passed_screenshot_visual_smoke": True,
            "frontend_calls_preview_only_route": False,
            "actual_zdoc_zbid_integration_done": False,
            "formal_generation_open": False,
            "docx_export_open": False,
            "review_apply_open": False,
            "zbid_writeback_open": False,
            "output_job_export_write_open": False,
        },
        "frontend_integration_goal": {
            "frontend_calls_only_local_trial_preview_only_route": True,
            "display_preview_only_metadata_only": True,
            "display_preview_packet": True,
            "display_validator_result": True,
            "display_blocked_reasons": True,
            "display_preview_only_status": True,
            "display_no_write_status": True,
            "display_advisory_is_not_evidence": True,
            "display_preview_is_not_formal_body": True,
            "must_not_trigger_formal_generation": True,
            "must_not_trigger_docx_export": True,
            "must_not_trigger_review_apply": True,
            "must_not_trigger_zbid_writeback": True,
        },
        "frontend_state_display_design": {
            "preview_only": {
                "state_visible": True,
                "metadata_only": True,
                "preview_is_not_formal_body": True,
                "preview_is_not_writeback_permission": True,
            },
            "no_write": {
                "state_visible": True,
                "does_not_write_formal_body": True,
                "does_not_write_output_job_export": True,
                "does_not_generate_docx": True,
            },
            "validator_states": {
                "accepted_preview_only_visible": True,
                "blocked_visible": True,
                "requires_human_review_visible": True,
                "accepted_preview_only_is_not_writeback_permission": True,
            },
            "blocked_reasons": {
                "list_visible": True,
                "readable": True,
                "explains_generation_blocked": True,
                "explains_docx_export_blocked": True,
                "explains_review_apply_blocked": True,
                "explains_zbid_writeback_blocked": True,
            },
            "evidence_boundary": {
                "advisory_is_not_evidence": True,
                "preview_advisory_is_not_evidence": True,
                "zbid_scoring_preview_is_not_evidence": True,
                "evidence_requires_verifiable_tender_anchor": True,
            },
            "reference_boundaries": {
                "scoring_refs_read_only": True,
                "tender_refs_read_only": True,
                "tender_file_refs_are_not_automatic_evidence": True,
                "scoring_clause_refs_require_verifiable_clause": True,
            },
            "formal_flags_display": dict(CURRENT_STAGE_FORMAL_FLAGS),
        },
        "forbidden_behaviors": {
            "must_not_call_generate": True,
            "must_not_call_export_docx": True,
            "must_not_call_review_apply": True,
            "must_not_call_zbid_api_db_writeback": True,
            "must_not_trigger_formal_writeback": True,
            "must_not_write_output_job_export": True,
            "must_not_generate_docx": True,
            "must_not_treat_advisory_as_evidence": True,
            "must_not_treat_preview_as_formal_body": True,
            "must_not_treat_accepted_preview_only_as_writeback_permission": True,
        },
        "future_code_scope": {
            "future_only_no_change_in_this_step": True,
            "may_touch_frontend_page_state_area_later": True,
            "may_add_preview_only_request_button_later": True,
            "may_add_blocked_reasons_display_component_later": True,
            "may_add_validator_result_display_component_later": True,
            "may_add_preview_packet_display_component_later": True,
            "may_add_formal_flags_display_later": True,
            "must_not_touch_backend_formal_generation_chain": True,
            "must_not_touch_docx_export_chain": True,
            "must_not_touch_review_apply_chain": True,
            "must_not_touch_zbid_writeback_chain": True,
            "must_not_touch_output_job_export": True,
        },
        "acceptance_criteria": {
            "frontend_can_display_local_trial_preview_only_result": True,
            "preview_packet_readable": True,
            "validator_result_readable": True,
            "blocked_reasons_readable": True,
            "preview_only_visible": True,
            "no_write_visible": True,
            "formal_flags_all_false": True,
            "page_does_not_generate_formal_document": True,
            "page_does_not_write_output_job_export": True,
            "page_does_not_trigger_generate": True,
            "page_does_not_trigger_export_docx": True,
            "page_does_not_trigger_review_apply": True,
            "page_does_not_trigger_zbid_writeback": True,
            "advisory_not_displayed_as_evidence": True,
            "preview_not_displayed_as_formal_body": True,
        },
        "next_steps": {
            "step_187_fake_schema_tests": True,
            "tests_only_current_step": True,
            "do_not_modify_frontend_code_current_step": True,
            "future_frontend_code_requires_separate_authorization": True,
            "must_not_enter_actual_zdoc_zbid_integration": True,
            "must_not_enter_50_person_deployment_design": True,
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
            "actual_zdoc_zbid_integration_entered": False,
            "entered_50_person_deployment_design": False,
        },
    }
    plan.update(overrides)
    return plan


def validate_fake_preview_only_route_frontend_integration_plan(plan):
    reasons = []

    if not isinstance(plan, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_frontend_integration_plan"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(plan)
    if missing_sections:
        reasons.append("missing_required_frontend_integration_plan_sections")

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


def test_preview_only_route_frontend_integration_plan_sections_are_explicit():
    plan = make_fake_preview_only_route_frontend_integration_plan()

    assert REQUIRED_SECTIONS.issubset(plan)
    assert validate_fake_preview_only_route_frontend_integration_plan(plan) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_current_baseline_records_route_smoke_and_frontend_no_write_ui():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    baseline = plan["current_baseline"]

    assert baseline["local_trial_preview_only_route_implemented"] is True
    assert baseline["runtime_smoke_passed"] is True
    assert baseline["preview_packet_readable"] is True
    assert baseline["validator_result_readable"] is True
    assert baseline["blocked_reasons_readable"] is True
    assert baseline["frontend_no_write_ui_fixed"] is True
    assert baseline["frontend_no_write_ui_passed_screenshot_visual_smoke"] is True
    assert baseline["frontend_calls_preview_only_route"] is False
    assert baseline["actual_zdoc_zbid_integration_done"] is False


def test_frontend_integration_goal_is_preview_only_display_without_formal_chains():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    goal = plan["frontend_integration_goal"]

    assert_required_items(
        goal,
        {
            "frontend_calls_only_local_trial_preview_only_route",
            "display_preview_only_metadata_only",
            "display_preview_packet",
            "display_validator_result",
            "display_blocked_reasons",
            "display_preview_only_status",
            "display_no_write_status",
            "display_advisory_is_not_evidence",
            "display_preview_is_not_formal_body",
            "must_not_trigger_formal_generation",
            "must_not_trigger_docx_export",
            "must_not_trigger_review_apply",
            "must_not_trigger_zbid_writeback",
        },
    )
    assert all(goal.values())


def test_frontend_state_display_design_covers_validator_blocked_and_evidence_boundaries():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    states = plan["frontend_state_display_design"]

    assert_required_items(
        states,
        {
            "preview_only",
            "no_write",
            "validator_states",
            "blocked_reasons",
            "evidence_boundary",
            "reference_boundaries",
            "formal_flags_display",
        },
    )
    assert states["preview_only"]["state_visible"] is True
    assert states["no_write"]["state_visible"] is True
    assert states["validator_states"]["accepted_preview_only_visible"] is True
    assert states["validator_states"]["blocked_visible"] is True
    assert states["validator_states"]["requires_human_review_visible"] is True
    assert states["blocked_reasons"]["list_visible"] is True
    assert states["blocked_reasons"]["readable"] is True
    assert states["evidence_boundary"]["advisory_is_not_evidence"] is True
    assert states["evidence_boundary"]["preview_advisory_is_not_evidence"] is True
    assert states["reference_boundaries"]["scoring_refs_read_only"] is True
    assert states["reference_boundaries"]["tender_refs_read_only"] is True
    assert states["formal_flags_display"] == CURRENT_STAGE_FORMAL_FLAGS


def test_forbidden_behaviors_block_formal_routes_writes_and_evidence_confusion():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    forbidden = plan["forbidden_behaviors"]

    assert_required_items(
        forbidden,
        {
            "must_not_call_generate",
            "must_not_call_export_docx",
            "must_not_call_review_apply",
            "must_not_call_zbid_api_db_writeback",
            "must_not_trigger_formal_writeback",
            "must_not_write_output_job_export",
            "must_not_generate_docx",
            "must_not_treat_advisory_as_evidence",
            "must_not_treat_preview_as_formal_body",
        },
    )
    assert all(forbidden.values())


def test_future_code_scope_is_frontend_only_and_blocks_backend_formal_chains():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    scope = plan["future_code_scope"]

    assert scope["future_only_no_change_in_this_step"] is True
    assert scope["may_touch_frontend_page_state_area_later"] is True
    assert scope["may_add_preview_only_request_button_later"] is True
    assert scope["may_add_blocked_reasons_display_component_later"] is True
    assert scope["may_add_validator_result_display_component_later"] is True
    assert scope["may_add_preview_packet_display_component_later"] is True
    assert scope["may_add_formal_flags_display_later"] is True
    assert scope["must_not_touch_backend_formal_generation_chain"] is True
    assert scope["must_not_touch_docx_export_chain"] is True
    assert scope["must_not_touch_review_apply_chain"] is True
    assert scope["must_not_touch_zbid_writeback_chain"] is True
    assert scope["must_not_touch_output_job_export"] is True


def test_acceptance_criteria_keep_frontend_preview_only_no_write():
    plan = make_fake_preview_only_route_frontend_integration_plan()
    acceptance = plan["acceptance_criteria"]

    assert_required_items(
        acceptance,
        {
            "frontend_can_display_local_trial_preview_only_result",
            "preview_packet_readable",
            "validator_result_readable",
            "blocked_reasons_readable",
            "formal_flags_all_false",
            "page_does_not_generate_formal_document",
            "page_does_not_write_output_job_export",
        },
    )
    assert acceptance["preview_only_visible"] is True
    assert acceptance["no_write_visible"] is True
    assert acceptance["advisory_not_displayed_as_evidence"] is True
    assert acceptance["preview_not_displayed_as_formal_body"] is True
    assert all(acceptance.values())


def test_next_steps_keep_current_step_tests_only():
    plan = make_fake_preview_only_route_frontend_integration_plan()

    assert plan["next_steps"] == {
        "step_187_fake_schema_tests": True,
        "tests_only_current_step": True,
        "do_not_modify_frontend_code_current_step": True,
        "future_frontend_code_requires_separate_authorization": True,
        "must_not_enter_actual_zdoc_zbid_integration": True,
        "must_not_enter_50_person_deployment_design": True,
    }


def test_formal_flags_are_always_false():
    plan = make_fake_preview_only_route_frontend_integration_plan()

    assert plan["formal_flags"] == CURRENT_STAGE_FORMAL_FLAGS
    assert plan["frontend_state_display_design"]["formal_flags_display"] == {
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
    }
    assert validate_fake_preview_only_route_frontend_integration_plan(plan)[
        "formal_flags"
    ] == CURRENT_STAGE_FORMAL_FLAGS


def test_preview_only_route_frontend_integration_plan_has_no_execution_side_effects():
    plan = make_fake_preview_only_route_frontend_integration_plan()

    assert plan["execution_side_effects"] == {
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
        "actual_zdoc_zbid_integration_entered": False,
        "entered_50_person_deployment_design": False,
    }
    assert validate_fake_preview_only_route_frontend_integration_plan(plan)[
        "blocked_reasons"
    ] == []


def test_preview_only_route_frontend_integration_plan_imports_do_not_pull_main_chain_or_service_modules():
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
