import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "current_baseline",
    "preview_only_route_goal",
    "route_design_scope",
    "safety_boundary",
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


def make_fake_local_trial_preview_only_route_plan(**overrides):
    plan = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "current_baseline": {
            "frontend_no_write_ui_fixed": True,
            "frontend_no_write_ui_passed_screenshot_visual_smoke": True,
            "backend_preview_safe_readable": True,
            "fake_zdoc_zbid_preview_packet_helper_exists": True,
            "fake_zbid_preview_input_validator_exists": True,
            "real_preview_only_route_implemented": False,
            "actual_zdoc_zbid_integration_done": False,
            "formal_generation_open": False,
            "docx_export_open": False,
            "review_apply_open": False,
            "zbid_writeback_open": False,
            "output_job_export_write_open": False,
        },
        "preview_only_route_goal": {
            "generate_preview_packet_only": True,
            "run_metadata_only_validator_only": True,
            "return_preview_only": True,
            "return_no_write": True,
            "return_blocked_reasons": True,
            "return_formal_flags": True,
            "must_not_trigger_formal_generation": True,
            "must_not_trigger_docx_export": True,
            "must_not_trigger_review_apply": True,
            "must_not_trigger_zbid_writeback": True,
            "must_not_write_output_job_export": True,
        },
        "route_design_scope": {
            "local_trial_preview_only_route_only": True,
            "route_name_design_placeholder_only": True,
            "route_name_not_implemented_current_step": True,
            "input_fake_local_trial_metadata": True,
            "output_preview_packet_plus_validator_result": True,
            "formal_writeback_allowed": False,
            "review_apply_allowed": False,
            "docx_export_allowed": False,
            "zbid_writeback_allowed": False,
            "output_write_allowed": False,
        },
        "input_contract": {
            "requires_integration_request_id": True,
            "requires_project_id": True,
            "requires_document_id": True,
            "requires_section_id": True,
            "requires_section_hash": True,
            "requires_section_version": True,
            "requires_tender_file_refs": True,
            "requires_scoring_clause_refs": True,
            "requires_evidence_anchor_refs": True,
            "must_block_missing_required_fields": True,
            "must_block_formal_chain_requests": True,
        },
        "output_contract": {
            "returns_preview_packet": True,
            "returns_validator_result": True,
            "returns_preview_only_true": True,
            "returns_no_write_true": True,
            "returns_blocked_reasons": True,
            "returns_metadata_only_decision": True,
            "must_not_return_writeback_payload": True,
            "must_not_return_docx_artifact_path": True,
            "must_not_return_zbid_writeback_payload": True,
        },
        "safety_boundary": {
            "must_not_call_orchestrator_formal_generation_chain": True,
            "must_not_call_llm_client_formal_body_generation": True,
            "must_not_call_provider_generation": True,
            "must_not_call_generation_chain": True,
            "must_not_call_export_docx": True,
            "must_not_call_review_apply": True,
            "must_not_call_zbid_api_db_writeback": True,
            "must_not_write_output_job_export": True,
            "advisory_must_not_be_evidence": True,
            "preview_must_not_be_formal_body": True,
            "evidence_requires_verifiable_anchor": True,
            "scoring_refs_require_verifiable_clause": True,
        },
        "acceptance_criteria": {
            "route_design_covers_input": True,
            "route_design_covers_output": True,
            "route_design_covers_blocked_reasons": True,
            "route_design_covers_formal_flags": True,
            "no_write_explicit": True,
            "preview_only_explicit": True,
            "evidence_boundary_explicit": True,
            "zbid_metadata_only_explicit": True,
            "all_formal_chains_blocked": True,
            "formal_writeback_allowed": False,
            "review_apply_allowed": False,
            "docx_export_allowed": False,
            "zbid_writeback_allowed": False,
            "output_write_allowed": False,
        },
        "next_steps": {
            "step_180_fake_schema_tests": True,
            "step_181_code_implementation_requires_separate_authorization": True,
            "must_not_implement_route_current_step": True,
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
            "preview_only_route_implemented": False,
            "actual_zdoc_zbid_integration_entered": False,
            "entered_50_person_deployment_design": False,
        },
    }
    plan.update(overrides)
    return plan


def validate_fake_local_trial_preview_only_route_plan(plan):
    reasons = []

    if not isinstance(plan, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_preview_only_route_plan"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(plan)
    if missing_sections:
        reasons.append("missing_required_preview_only_route_plan_sections")

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


def test_local_trial_preview_only_route_plan_sections_are_explicit():
    plan = make_fake_local_trial_preview_only_route_plan()

    assert REQUIRED_SECTIONS.issubset(plan)
    assert validate_fake_local_trial_preview_only_route_plan(plan) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_current_baseline_preserves_fake_only_route_gap():
    plan = make_fake_local_trial_preview_only_route_plan()
    baseline = plan["current_baseline"]

    assert baseline["frontend_no_write_ui_fixed"] is True
    assert baseline["frontend_no_write_ui_passed_screenshot_visual_smoke"] is True
    assert baseline["backend_preview_safe_readable"] is True
    assert baseline["fake_zdoc_zbid_preview_packet_helper_exists"] is True
    assert baseline["fake_zbid_preview_input_validator_exists"] is True
    assert baseline["real_preview_only_route_implemented"] is False
    assert baseline["actual_zdoc_zbid_integration_done"] is False


def test_preview_only_route_goal_is_metadata_only_and_no_write():
    plan = make_fake_local_trial_preview_only_route_plan()
    goal = plan["preview_only_route_goal"]

    assert_required_items(
        goal,
        {
            "generate_preview_packet_only",
            "run_metadata_only_validator_only",
            "return_preview_only",
            "return_no_write",
            "return_blocked_reasons",
            "return_formal_flags",
            "must_not_trigger_formal_generation",
            "must_not_trigger_docx_export",
            "must_not_trigger_review_apply",
            "must_not_trigger_zbid_writeback",
            "must_not_write_output_job_export",
        },
    )
    assert all(goal.values())


def test_route_design_scope_is_local_trial_placeholder_with_false_flags():
    plan = make_fake_local_trial_preview_only_route_plan()
    scope = plan["route_design_scope"]

    assert scope["local_trial_preview_only_route_only"] is True
    assert scope["route_name_design_placeholder_only"] is True
    assert scope["route_name_not_implemented_current_step"] is True
    assert scope["input_fake_local_trial_metadata"] is True
    assert scope["output_preview_packet_plus_validator_result"] is True
    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        assert scope[flag] is expected


def test_input_and_output_contracts_cover_packet_validator_and_blocks():
    plan = make_fake_local_trial_preview_only_route_plan()

    assert_required_items(
        plan["input_contract"],
        {
            "requires_integration_request_id",
            "requires_project_id",
            "requires_document_id",
            "requires_section_id",
            "requires_section_hash",
            "requires_section_version",
            "requires_tender_file_refs",
            "requires_scoring_clause_refs",
            "requires_evidence_anchor_refs",
            "must_block_missing_required_fields",
            "must_block_formal_chain_requests",
        },
    )
    assert_required_items(
        plan["output_contract"],
        {
            "returns_preview_packet",
            "returns_validator_result",
            "returns_preview_only_true",
            "returns_no_write_true",
            "returns_blocked_reasons",
            "returns_metadata_only_decision",
            "must_not_return_writeback_payload",
            "must_not_return_docx_artifact_path",
            "must_not_return_zbid_writeback_payload",
        },
    )


def test_safety_boundary_blocks_formal_chain_and_evidence_confusion():
    plan = make_fake_local_trial_preview_only_route_plan()
    boundary = plan["safety_boundary"]

    assert_required_items(
        boundary,
        {
            "must_not_call_orchestrator_formal_generation_chain",
            "must_not_call_llm_client_formal_body_generation",
            "must_not_call_export_docx",
            "must_not_call_review_apply",
            "must_not_call_zbid_api_db_writeback",
            "must_not_write_output_job_export",
            "advisory_must_not_be_evidence",
            "preview_must_not_be_formal_body",
        },
    )
    assert all(boundary.values())


def test_acceptance_criteria_keep_preview_only_route_no_write():
    plan = make_fake_local_trial_preview_only_route_plan()
    acceptance = plan["acceptance_criteria"]

    assert acceptance["route_design_covers_input"] is True
    assert acceptance["route_design_covers_output"] is True
    assert acceptance["route_design_covers_blocked_reasons"] is True
    assert acceptance["route_design_covers_formal_flags"] is True
    assert acceptance["no_write_explicit"] is True
    assert acceptance["preview_only_explicit"] is True
    assert acceptance["evidence_boundary_explicit"] is True
    assert acceptance["zbid_metadata_only_explicit"] is True
    assert acceptance["all_formal_chains_blocked"] is True
    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        assert acceptance[flag] is expected


def test_next_steps_require_separate_authorization_before_route_implementation():
    plan = make_fake_local_trial_preview_only_route_plan()

    assert plan["next_steps"] == {
        "step_180_fake_schema_tests": True,
        "step_181_code_implementation_requires_separate_authorization": True,
        "must_not_implement_route_current_step": True,
        "must_not_enter_actual_zdoc_zbid_integration": True,
        "must_not_enter_50_person_deployment_design": True,
    }


def test_formal_flags_are_always_false():
    plan = make_fake_local_trial_preview_only_route_plan()

    assert plan["formal_flags"] == CURRENT_STAGE_FORMAL_FLAGS
    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        assert plan["route_design_scope"][flag] is expected
        assert plan["acceptance_criteria"][flag] is expected


def test_preview_only_route_plan_schema_has_no_execution_side_effects():
    plan = make_fake_local_trial_preview_only_route_plan()

    assert validate_fake_local_trial_preview_only_route_plan(plan) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }
    assert not any(plan["execution_side_effects"].values())


def test_preview_only_route_plan_imports_do_not_pull_main_chain_or_service_modules():
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
