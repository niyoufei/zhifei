import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "scope",
    "authorization_principle",
    "runtime_action_categories",
    "authorization_request_template",
    "authorized_command_allowlist_design",
    "runtime_hard_block_list",
    "no_write_runtime_assertion_design",
    "service_startup_authorization_boundary",
    "ollama_authorization_boundary",
    "zdoc_zbid_preview_only_authorization_boundary",
    "stop_conditions",
    "required_runtime_report_template",
    "future_implementation_acceptance_criteria",
    "migration_path",
    "safety_conclusion",
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


def make_fake_local_trial_runtime_authorization_gate(**overrides):
    gate = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "scope": {
            "docs_only": True,
            "execute_authorization": False,
            "start_service": False,
            "run_ollama": False,
            "access_port": False,
            "call_zbid": False,
            "write_output_job_export": False,
            "execute_smoke_test": False,
            "enter_50_person_deployment_design": False,
        },
        "authorization_principle": {
            "default_deny_all_runtime_actions": True,
            "runtime_actions_require_explicit_user_authorization": True,
            "authorization_names_action_directory_command_scope_stop_report": True,
            "unauthorized_must_not_be_inferred_allowed": True,
            "partial_authorization_must_not_expand": True,
            "document_check_is_not_command_execution": True,
            "smoke_plan_design_is_not_smoke_test_execution": True,
            "preview_only_is_not_writeback_allowed": True,
        },
        "runtime_action_categories": {
            "always_forbidden_without_higher_authorization": {
                "formal_writeback",
                "review_apply_route",
                "export_docx_route",
                "docx_formal_export",
                "zbid_formal_writeback",
                "zbid_api_db_writeback",
                "output_job_export_write",
                "source_section_mutation",
                "enter_50_person_formal_deployment",
                "production_main_chain_modification",
                "existing_tests_full_suite_order_fix",
            },
            "requires_explicit_smoke_test_authorization": {
                "start_backend_service",
                "start_frontend_service",
                "access_local_service_port",
                "access_127_0_0_1_11434",
                "check_ollama_reachability",
                "execute_preview_only_test_request",
                "generate_smoke_report",
                "check_output_job_export_diff",
                "stop_local_services",
            },
            "docs_only_allowed_current_stage": {
                "write_design_doc",
                "write_fake_schema_tests",
                "write_fake_helper",
                "design_command_placeholders",
                "design_report_template",
                "design_stop_conditions",
            },
        },
        "authorization_request_template": {
            "planned_actions": None,
            "current_directory": None,
            "current_branch": None,
            "current_head": None,
            "will_start_service": None,
            "will_access_local_port": None,
            "will_run_ollama": None,
            "will_read_local_config": None,
            "will_write_output_job_export": None,
            "will_trigger_generate": None,
            "will_trigger_export_docx": None,
            "will_trigger_review_apply": None,
            "will_trigger_zbid_writeback": None,
            "planned_command_list": [],
            "stop_conditions": [],
            "report_format": None,
            "explicit_user_authorization_confirmation": None,
            "must_not_execute_without_explicit_user_authorization": True,
        },
        "authorized_command_allowlist_design": {
            "pwd": True,
            "git_branch_show_current": True,
            "git_rev_parse_head": True,
            "git_status_short": True,
            "python_node_pnpm_version_checks": True,
            "backend_start_command_placeholder": True,
            "backend_health_check_command_placeholder": True,
            "frontend_start_command_placeholder": True,
            "frontend_page_access_check_placeholder": True,
            "ollama_optional_check_command_placeholder": True,
            "output_job_export_diff_check_placeholder": True,
            "stop_service_command_placeholder": True,
            "future_authorization_scope_only": True,
            "not_allowed_to_execute_in_current_step": True,
        },
        "runtime_hard_block_list": {
            "generate_formal_generation",
            "export_docx_route",
            "review_apply_route",
            "zbid_writeback",
            "zbid_api_db_writeback",
            "output_job_export_write",
            "docx_file_generation",
            "formal_writeback_allowed_true",
            "review_apply_allowed_true",
            "docx_export_allowed_true",
            "zbid_writeback_allowed_true",
            "output_write_allowed_true",
            "advisory_used_as_evidence",
            "preview_used_as_formal_body",
            "source_hash_mismatch_not_blocked",
            "blocked_reasons_missing",
        },
        "no_write_runtime_assertion_design": {
            "record_output_job_export_before_smoke": True,
            "compare_output_job_export_after_smoke": True,
            "any_new_file_requires_stop": True,
            "any_docx_json_markdown_formal_artifact_requires_stop": True,
            "any_job_export_state_file_requires_stop": True,
            "any_formal_flag_true_requires_stop": True,
            "any_writeback_request_not_blocked_requires_stop": True,
        },
        "service_startup_authorization_boundary": {
            "backend_start_requires_separate_authorization": True,
            "frontend_start_requires_separate_authorization": True,
            "startup_requires_stop_command": True,
            "startup_failure_requires_stop": True,
            "must_not_leave_unknown_background_process": True,
            "must_not_start_unauthorized_service": True,
            "must_not_start_zbid_formal_service": True,
            "must_not_start_formal_writeback_worker": True,
        },
        "ollama_authorization_boundary": {
            "ollama_check_is_optional": True,
            "ollama_serve_requires_separate_authorization": True,
            "access_127_0_0_1_11434_requires_separate_authorization": True,
            "model_unavailable_must_not_auto_download": True,
            "model_unavailable_must_not_writeback": True,
            "model_output_must_not_be_evidence": True,
            "thinking_only_fallback_must_not_be_formal_body_capability": True,
        },
        "zdoc_zbid_preview_only_authorization_boundary": {
            "may_test_zdoc_preview_packet": True,
            "may_test_zbid_preview_validator": True,
            "must_not_call_real_zbid_api": True,
            "must_not_access_zbid_db": True,
            "must_not_writeback_zbid": True,
            "zbid_scoring_preview_must_not_be_evidence": True,
            "accepted_preview_only_must_not_be_writeback_permission": True,
            "zbid_writeback_allowed": False,
        },
        "stop_conditions": {
            "current_directory_wrong": True,
            "branch_wrong": True,
            "head_mismatch": True,
            "git_status_not_clean": True,
            "unauthorized_action_seen": True,
            "any_formal_flag_true": True,
            "output_job_export_write_seen": True,
            "docx_file_generated": True,
            "generate_triggered": True,
            "export_docx_triggered": True,
            "review_apply_triggered": True,
            "zbid_writeback_triggered": True,
            "zbid_api_db_writeback_called": True,
            "local_service_cannot_stop": True,
            "unknown_process_keeps_running": True,
            "blocked_reasons_missing": True,
            "advisory_used_as_evidence": True,
            "preview_shown_as_formal_body": True,
            "source_hash_or_version_mismatch_not_blocked": True,
        },
        "required_runtime_report_template": {
            "authorization_scope": None,
            "actual_commands_executed": [],
            "current_directory": None,
            "current_branch": None,
            "starting_head": None,
            "ending_head": None,
            "git_status": None,
            "backend_started": None,
            "backend_pid_or_stop_status": None,
            "frontend_started": None,
            "frontend_pid_or_stop_status": None,
            "ollama_run": None,
            "accessed_127_0_0_1_11434": None,
            "accessed_other_local_port": None,
            "external_api_called": None,
            "generate_triggered": None,
            "export_docx_triggered": None,
            "docx_generated": None,
            "review_apply_triggered": None,
            "zbid_writeback_triggered": None,
            "zbid_api_db_writeback_called": None,
            "output_job_export_written": None,
            "formal_flags_all_false": None,
            "blocked_reasons_readable": None,
            "all_started_processes_stopped": None,
            "risk_notes": [],
            "next_step_recommendation": None,
        },
        "future_implementation_acceptance_criteria": {
            "deterministic_fake_schema_tests",
            "authorization_categories_tests",
            "command_allowlist_tests",
            "hard_block_list_tests",
            "no_write_assertion_tests",
            "service_startup_authorization_tests",
            "ollama_boundary_tests",
            "zdoc_zbid_preview_only_authorization_tests",
            "stop_conditions_tests",
            "report_template_tests",
            "import_isolation_tests",
            "no_output_job_export_write_tests",
        },
        "migration_path": {
            "step_155_local_trial_runtime_authorization_gate_fake_schema_tests": True,
            "step_156_runtime_authorization_gate_stage_review": True,
            "step_157_local_trial_authorized_smoke_dry_run_command_plan": True,
            "step_158_first_real_smoke_authorization_request": True,
            "real_local_smoke_requires_explicit_user_authorization": True,
            "small_trial_stabilizes_before_50_person_deployment_design": True,
        },
        "safety_conclusion": {
            "runtime_action_authorized": False,
            "smoke_test_executed": False,
            "local_deployment_executed": False,
            "zdoc_zbid_actual_integration_executed": False,
            "formal_writeback_implemented": False,
            "docx_export_implemented": False,
            "zbid_writeback_implemented": False,
            "enter_50_person_deployment_design": False,
        },
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        "execution_side_effects": {
            "backend_started": False,
            "frontend_started": False,
            "ollama_run": False,
            "local_port_accessed": False,
            "network_called": False,
            "output_job_export_written": False,
            "docx_json_markdown_generated": False,
            "zbid_called": False,
            "generate_triggered": False,
            "export_docx_triggered": False,
            "review_apply_triggered": False,
            "smoke_test_executed": False,
            "local_deployment_executed": False,
            "entered_50_person_deployment_design": False,
            "authorization_scope_expanded": False,
        },
    }
    gate.update(overrides)
    return gate


def validate_fake_local_trial_runtime_authorization_gate(gate):
    reasons = []

    if not isinstance(gate, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_runtime_authorization_gate"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(gate)
    if missing_sections:
        reasons.append("missing_required_runtime_authorization_gate_sections")

    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        if gate.get("formal_flags", {}).get(flag) is not expected:
            reasons.append(f"{flag}_must_be_false")

    if any(gate.get("execution_side_effects", {}).values()):
        reasons.append("execution_side_effects_must_not_be_performed")

    return {
        "status": "blocked" if reasons else "accepted_fake_schema_only",
        "blocked_reasons": reasons,
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
    }


def assert_required_items(section, expected_items):
    assert expected_items.issubset(section)


def assert_formal_flags_false(flags):
    assert flags == CURRENT_STAGE_FORMAL_FLAGS


def test_runtime_authorization_gate_sections_are_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert REQUIRED_SECTIONS.issubset(gate)
    assert validate_fake_local_trial_runtime_authorization_gate(gate) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_scope_blocks_runtime_execution_and_deployment():
    gate = make_fake_local_trial_runtime_authorization_gate()
    scope = gate["scope"]

    assert scope["docs_only"] is True
    assert scope["execute_authorization"] is False
    assert scope["start_service"] is False
    assert scope["run_ollama"] is False
    assert scope["access_port"] is False
    assert scope["call_zbid"] is False
    assert scope["write_output_job_export"] is False
    assert scope["execute_smoke_test"] is False
    assert scope["enter_50_person_deployment_design"] is False


def test_authorization_principle_requires_explicit_user_authorization():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["authorization_principle"],
        {
            "default_deny_all_runtime_actions",
            "runtime_actions_require_explicit_user_authorization",
            "authorization_names_action_directory_command_scope_stop_report",
            "unauthorized_must_not_be_inferred_allowed",
            "partial_authorization_must_not_expand",
            "document_check_is_not_command_execution",
            "smoke_plan_design_is_not_smoke_test_execution",
            "preview_only_is_not_writeback_allowed",
        },
    )


def test_runtime_action_categories_are_locked():
    gate = make_fake_local_trial_runtime_authorization_gate()
    categories = gate["runtime_action_categories"]

    assert_required_items(
        categories,
        {
            "always_forbidden_without_higher_authorization",
            "requires_explicit_smoke_test_authorization",
            "docs_only_allowed_current_stage",
        },
    )
    assert_required_items(
        categories["always_forbidden_without_higher_authorization"],
        {
            "formal_writeback",
            "review_apply_route",
            "export_docx_route",
            "docx_formal_export",
            "zbid_formal_writeback",
            "zbid_api_db_writeback",
            "output_job_export_write",
            "source_section_mutation",
            "enter_50_person_formal_deployment",
            "production_main_chain_modification",
            "existing_tests_full_suite_order_fix",
        },
    )
    assert_required_items(
        categories["requires_explicit_smoke_test_authorization"],
        {
            "start_backend_service",
            "start_frontend_service",
            "access_local_service_port",
            "access_127_0_0_1_11434",
            "check_ollama_reachability",
            "execute_preview_only_test_request",
            "generate_smoke_report",
            "check_output_job_export_diff",
            "stop_local_services",
        },
    )
    assert_required_items(
        categories["docs_only_allowed_current_stage"],
        {
            "write_design_doc",
            "write_fake_schema_tests",
            "write_fake_helper",
            "design_command_placeholders",
            "design_report_template",
            "design_stop_conditions",
        },
    )


def test_authorization_request_template_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["authorization_request_template"],
        {
            "planned_actions",
            "current_directory",
            "current_branch",
            "current_head",
            "will_start_service",
            "will_access_local_port",
            "will_run_ollama",
            "will_read_local_config",
            "will_write_output_job_export",
            "will_trigger_generate",
            "will_trigger_export_docx",
            "will_trigger_review_apply",
            "will_trigger_zbid_writeback",
            "planned_command_list",
            "stop_conditions",
            "report_format",
            "explicit_user_authorization_confirmation",
            "must_not_execute_without_explicit_user_authorization",
        },
    )
    assert (
        gate["authorization_request_template"][
            "must_not_execute_without_explicit_user_authorization"
        ]
        is True
    )


def test_authorized_command_allowlist_is_declared_without_execution():
    gate = make_fake_local_trial_runtime_authorization_gate()
    allowlist = gate["authorized_command_allowlist_design"]

    assert_required_items(
        allowlist,
        {
            "pwd",
            "git_branch_show_current",
            "git_rev_parse_head",
            "git_status_short",
            "python_node_pnpm_version_checks",
            "backend_start_command_placeholder",
            "backend_health_check_command_placeholder",
            "frontend_start_command_placeholder",
            "frontend_page_access_check_placeholder",
            "ollama_optional_check_command_placeholder",
            "output_job_export_diff_check_placeholder",
            "stop_service_command_placeholder",
        },
    )
    assert allowlist["future_authorization_scope_only"] is True
    assert allowlist["not_allowed_to_execute_in_current_step"] is True


def test_runtime_hard_block_list_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["runtime_hard_block_list"],
        {
            "generate_formal_generation",
            "export_docx_route",
            "review_apply_route",
            "zbid_writeback",
            "zbid_api_db_writeback",
            "output_job_export_write",
            "docx_file_generation",
            "formal_writeback_allowed_true",
            "review_apply_allowed_true",
            "docx_export_allowed_true",
            "zbid_writeback_allowed_true",
            "output_write_allowed_true",
            "advisory_used_as_evidence",
            "preview_used_as_formal_body",
            "source_hash_mismatch_not_blocked",
            "blocked_reasons_missing",
        },
    )


def test_no_write_runtime_assertion_design_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["no_write_runtime_assertion_design"],
        {
            "record_output_job_export_before_smoke",
            "compare_output_job_export_after_smoke",
            "any_new_file_requires_stop",
            "any_docx_json_markdown_formal_artifact_requires_stop",
            "any_job_export_state_file_requires_stop",
            "any_formal_flag_true_requires_stop",
            "any_writeback_request_not_blocked_requires_stop",
        },
    )


def test_service_startup_authorization_boundary_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["service_startup_authorization_boundary"],
        {
            "backend_start_requires_separate_authorization",
            "frontend_start_requires_separate_authorization",
            "startup_requires_stop_command",
            "startup_failure_requires_stop",
            "must_not_leave_unknown_background_process",
            "must_not_start_unauthorized_service",
            "must_not_start_zbid_formal_service",
            "must_not_start_formal_writeback_worker",
        },
    )


def test_ollama_authorization_boundary_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["ollama_authorization_boundary"],
        {
            "ollama_check_is_optional",
            "ollama_serve_requires_separate_authorization",
            "access_127_0_0_1_11434_requires_separate_authorization",
            "model_unavailable_must_not_auto_download",
            "model_unavailable_must_not_writeback",
            "model_output_must_not_be_evidence",
            "thinking_only_fallback_must_not_be_formal_body_capability",
        },
    )


def test_zdoc_zbid_preview_only_authorization_boundary_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()
    preview_boundary = gate["zdoc_zbid_preview_only_authorization_boundary"]

    assert_required_items(
        preview_boundary,
        {
            "may_test_zdoc_preview_packet",
            "may_test_zbid_preview_validator",
            "must_not_call_real_zbid_api",
            "must_not_access_zbid_db",
            "must_not_writeback_zbid",
            "zbid_scoring_preview_must_not_be_evidence",
            "accepted_preview_only_must_not_be_writeback_permission",
            "zbid_writeback_allowed",
        },
    )
    assert preview_boundary["zbid_writeback_allowed"] is False


def test_stop_conditions_are_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["stop_conditions"],
        {
            "current_directory_wrong",
            "branch_wrong",
            "head_mismatch",
            "git_status_not_clean",
            "unauthorized_action_seen",
            "any_formal_flag_true",
            "output_job_export_write_seen",
            "docx_file_generated",
            "generate_triggered",
            "export_docx_triggered",
            "review_apply_triggered",
            "zbid_writeback_triggered",
            "zbid_api_db_writeback_called",
            "local_service_cannot_stop",
            "unknown_process_keeps_running",
            "blocked_reasons_missing",
            "advisory_used_as_evidence",
            "preview_shown_as_formal_body",
            "source_hash_or_version_mismatch_not_blocked",
        },
    )


def test_runtime_report_template_is_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["required_runtime_report_template"],
        {
            "authorization_scope",
            "actual_commands_executed",
            "current_directory",
            "current_branch",
            "starting_head",
            "ending_head",
            "git_status",
            "backend_started",
            "backend_pid_or_stop_status",
            "frontend_started",
            "frontend_pid_or_stop_status",
            "ollama_run",
            "accessed_127_0_0_1_11434",
            "accessed_other_local_port",
            "external_api_called",
            "generate_triggered",
            "export_docx_triggered",
            "docx_generated",
            "review_apply_triggered",
            "zbid_writeback_triggered",
            "zbid_api_db_writeback_called",
            "output_job_export_written",
            "formal_flags_all_false",
            "blocked_reasons_readable",
            "all_started_processes_stopped",
            "risk_notes",
            "next_step_recommendation",
        },
    )


def test_future_acceptance_criteria_are_explicit():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["future_implementation_acceptance_criteria"],
        {
            "deterministic_fake_schema_tests",
            "authorization_categories_tests",
            "command_allowlist_tests",
            "hard_block_list_tests",
            "no_write_assertion_tests",
            "service_startup_authorization_tests",
            "ollama_boundary_tests",
            "zdoc_zbid_preview_only_authorization_tests",
            "stop_conditions_tests",
            "report_template_tests",
            "import_isolation_tests",
            "no_output_job_export_write_tests",
        },
    )


def test_migration_path_requires_later_authorization_before_real_smoke():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_required_items(
        gate["migration_path"],
        {
            "step_155_local_trial_runtime_authorization_gate_fake_schema_tests",
            "step_156_runtime_authorization_gate_stage_review",
            "step_157_local_trial_authorized_smoke_dry_run_command_plan",
            "step_158_first_real_smoke_authorization_request",
            "real_local_smoke_requires_explicit_user_authorization",
            "small_trial_stabilizes_before_50_person_deployment_design",
        },
    )


def test_formal_flags_are_always_false():
    gate = make_fake_local_trial_runtime_authorization_gate()

    assert_formal_flags_false(gate["formal_flags"])
    assert validate_fake_local_trial_runtime_authorization_gate(gate)[
        "formal_flags"
    ] == CURRENT_STAGE_FORMAL_FLAGS

    unsafe_gate = make_fake_local_trial_runtime_authorization_gate(
        formal_flags={**CURRENT_STAGE_FORMAL_FLAGS, "zbid_writeback_allowed": True}
    )
    result = validate_fake_local_trial_runtime_authorization_gate(unsafe_gate)

    assert result["status"] == "blocked"
    assert "zbid_writeback_allowed_must_be_false" in result["blocked_reasons"]


def test_runtime_authorization_gate_schema_has_no_execution_side_effects():
    gate = make_fake_local_trial_runtime_authorization_gate()
    result = validate_fake_local_trial_runtime_authorization_gate(gate)

    assert result["status"] == "accepted_fake_schema_only"
    assert all(value is False for value in gate["execution_side_effects"].values())

    side_effect_gate = make_fake_local_trial_runtime_authorization_gate(
        execution_side_effects={
            **gate["execution_side_effects"],
            "authorization_scope_expanded": True,
        }
    )
    side_effect_result = validate_fake_local_trial_runtime_authorization_gate(
        side_effect_gate
    )

    assert side_effect_result["status"] == "blocked"
    assert (
        "execution_side_effects_must_not_be_performed"
        in side_effect_result["blocked_reasons"]
    )


def test_runtime_authorization_gate_schema_imports_do_not_pull_main_chain_or_service_modules():
    source = Path(__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    imported_roots = set()

    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0].lower())

    assert imported_roots.isdisjoint(FORBIDDEN_IMPORTS)
