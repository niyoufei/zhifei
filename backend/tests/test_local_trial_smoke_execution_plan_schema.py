import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "scope",
    "execution_strategy",
    "preflight_command_placeholders",
    "environment_preflight_placeholders",
    "backend_smoke_execution_placeholders",
    "frontend_smoke_execution_placeholders",
    "ollama_optional_smoke_execution_placeholders",
    "zdoc_preview_only_smoke_execution_placeholders",
    "zbid_preview_validator_smoke_execution_placeholders",
    "formal_chain_block_smoke_execution_placeholders",
    "output_job_export_write_detection_placeholder",
    "stop_conditions",
    "pass_criteria",
    "smoke_report_template",
    "future_implementation_boundary",
    "next_step_recommendation",
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


def make_fake_local_trial_smoke_execution_plan(**overrides):
    plan = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "scope": {
            "docs_only": True,
            "execute_smoke_test": False,
            "start_backend_service": False,
            "start_frontend_service": False,
            "run_ollama": False,
            "access_local_port": False,
            "call_zbid": False,
            "write_output_job_export": False,
            "enter_local_deployment_execution": False,
            "enter_50_person_deployment_design": False,
        },
        "execution_strategy": [
            "manual_git_status_preflight",
            "local_config_exists_but_not_committed_preflight",
            "output_job_export_before_snapshot",
            "backend_startup_check",
            "frontend_startup_check",
            "ollama_optional_reachability_check",
            "zdoc_preview_only_data_chain_check",
            "zbid_preview_input_validator_check",
            "formal_chain_block_check",
            "output_job_export_after_snapshot",
            "smoke_report",
            "stop_immediately_on_high_risk_failure",
        ],
        "preflight_command_placeholders": {
            "commands": [
                "pwd",
                "git branch --show-current",
                "git rev-parse HEAD",
                "git status --short",
            ],
            "future_checks": {
                "pwd_is_workspace": "/Users/youfeini/Desktop/文档生成系统",
                "branch_is_main": True,
                "worktree_clean": True,
                "current_tag_declared": True,
                "no_uncommitted_changes": True,
            },
            "execute_now": False,
        },
        "environment_preflight_placeholders": {
            "python_version_check_placeholder": "python --version",
            "node_version_check_placeholder": "node --version",
            "pnpm_version_check_placeholder": "pnpm --version",
            "env_local_config_check_placeholder": "git status --short -- .env",
            "do_not_print_sensitive_config": True,
            "do_not_commit_env": True,
            "do_not_modify_config_files": True,
            "local_materials_directory_check_placeholder": "<materials-dir-check>",
            "log_directory_check_placeholder": "<log-dir-check>",
            "output_job_export_isolation_check_placeholder": "<output-isolation-check>",
        },
        "backend_smoke_execution_placeholders": {
            "backend_start_command_placeholder": "<backend-start-command-placeholder>",
            "backend_health_check_command_placeholder": "<backend-health-check-command-placeholder>",
            "no_write_status_check_placeholder": "<no-write-status-check>",
            "preview_only_status_check_placeholder": "<preview-only-status-check>",
            "blocked_reasons_response_check_placeholder": "<blocked-reasons-check>",
            "request_id_log_check_placeholder": "<request-id-log-check>",
            "backend_stop_command_placeholder": "<backend-stop-command-placeholder>",
            "do_not_execute_in_current_step": True,
            "start_backend_now": False,
        },
        "frontend_smoke_execution_placeholders": {
            "frontend_dependency_check_placeholder": "<frontend-dependency-check>",
            "frontend_start_command_placeholder": "<frontend-start-command-placeholder>",
            "page_access_check_placeholder": "<frontend-access-check>",
            "preview_only_display_check_placeholder": "<preview-only-display-check>",
            "blocked_reasons_display_check_placeholder": "<blocked-reasons-display-check>",
            "formal_buttons_disabled_check_placeholder": (
                "DOCX / ZBid / review/apply / formal writeback disabled"
            ),
            "frontend_stop_command_placeholder": "<frontend-stop-command-placeholder>",
            "do_not_execute_in_current_step": True,
            "start_frontend_now": False,
        },
        "ollama_optional_smoke_execution_placeholders": {
            "ollama_installed_check_placeholder": "<ollama-installed-check>",
            "ollama_service_status_check_placeholder": "<ollama-service-status-check>",
            "ollama_11434_reachability_check_placeholder": "<127.0.0.1:11434-check>",
            "model_list_check_placeholder": "<ollama-model-list-check>",
            "model_unavailable_fallback_check_placeholder": "<fallback-check>",
            "thinking_only_fallback_no_writeback_check_placeholder": (
                "<thinking-only-fallback-no-writeback-check>"
            ),
            "ollama_is_optional_check": True,
            "model_unavailable_must_not_block_no_write_smoke": True,
            "model_unavailable_records_fallback": True,
            "run_ollama_now": False,
            "access_127_0_0_1_11434_now": False,
        },
        "zdoc_preview_only_smoke_execution_placeholders": {
            "preview_packet_generation_check_placeholder": "<preview-packet-check>",
            "integration_request_id_check": True,
            "project_document_section_id_check": True,
            "section_hash_version_check": True,
            "tender_file_refs_check": True,
            "scoring_clause_refs_check": True,
            "evidence_anchor_refs_check": True,
            "response_mode_check": True,
            "input_risk_level_check": True,
            "advisory_quality_gate_status_check": True,
            "formal_flags_false_check": True,
            "blocked_reasons_check": True,
            "must_not_trigger_generate_formal_generation": True,
        },
        "zbid_preview_validator_smoke_execution_placeholders": {
            "fake_preview_packet_input_check": True,
            "non_dict_blocked_check": True,
            "missing_evidence_anchor_blocked_check": True,
            "missing_scoring_clause_refs_blocked_check": True,
            "advisory_as_evidence_blocked_check": True,
            "thinking_only_fallback_blocked_check": True,
            "high_risk_without_validation_blocked_check": True,
            "accepted_preview_only_no_writeback_check": True,
            "zbid_writeback_allowed_false_check": True,
            "must_not_call_zbid_api_db_writeback": True,
        },
        "formal_chain_block_smoke_execution_placeholders": {
            "generate_formal_generation_blocked": True,
            "export_docx_blocked": True,
            "docx_file_must_not_be_generated": True,
            "review_apply_blocked": True,
            "zbid_writeback_blocked": True,
            "zbid_api_db_writeback_must_not_be_called": True,
            "formal_writeback_blocked": True,
            "formal_writeback_dry_run_must_not_open_writeback": True,
            "output_job_export_must_not_be_written": True,
            "formal_flags_always_false": True,
        },
        "output_job_export_write_detection_placeholder": {
            "before_output_job_export_snapshot": True,
            "after_output_job_export_snapshot": True,
            "new_file_requires_stop": True,
            "docx_json_markdown_artifact_requires_stop": True,
            "job_export_state_file_requires_stop": True,
            "diff_must_be_recorded": True,
        },
        "stop_conditions": {
            "git_status_not_clean": True,
            "backend_start_failed_without_readable_error": True,
            "frontend_start_failed_without_readable_error": True,
            "any_formal_flag_true": True,
            "output_job_export_write_seen": True,
            "docx_file_seen": True,
            "zbid_api_db_writeback_call_seen": True,
            "review_apply_call_seen": True,
            "generate_formal_generation_seen": True,
            "advisory_used_as_evidence": True,
            "preview_shown_as_formal_body": True,
            "source_hash_or_version_mismatch_without_block": True,
            "blocked_reasons_missing": True,
            "unknown_writeback_risk_seen": True,
        },
        "pass_criteria": {
            "backend_can_start": True,
            "backend_health_readable": True,
            "frontend_accessible": True,
            "preview_only_data_chain_can_be_produced": True,
            "validator_blocks_unsafe_input": True,
            "evidence_scoring_boundary_clear": True,
            "docx_zbid_review_apply_formal_writeback_default_blocked": True,
            "all_formal_flags_false": True,
            "blocked_reasons_readable": True,
            "no_output_job_export_write": True,
            "no_zbid_call": True,
            "no_docx_generated": True,
            "no_50_person_deployment_design": True,
        },
        "smoke_report_template": {
            "current_directory": None,
            "current_branch": None,
            "starting_head": None,
            "ending_head": None,
            "git_status": None,
            "backend_started": None,
            "frontend_started": None,
            "ollama_run": None,
            "accessed_127_0_0_1_11434": None,
            "accessed_local_port": None,
            "preview_packet_generated": None,
            "validator_executed": None,
            "generate_triggered": None,
            "export_docx_triggered": None,
            "docx_generated": None,
            "review_apply_triggered": None,
            "zbid_writeback_triggered": None,
            "zbid_api_db_writeback_called": None,
            "output_job_export_written": None,
            "formal_flags_all_false": None,
            "blocked_reasons_readable": None,
            "entered_local_deployment_execution": None,
            "entered_50_person_deployment_design": None,
            "failed_items": [],
            "risk_notes": [],
            "next_step_recommendation": None,
        },
        "future_implementation_boundary": {
            "requires_authorization_to_start_backend": True,
            "requires_authorization_to_start_frontend": True,
            "requires_authorization_to_access_local_port": True,
            "requires_authorization_to_check_ollama": True,
            "requires_authorization_to_read_local_config": True,
            "requires_authorization_to_execute_preview_only_test_request": True,
            "requires_authorization_to_generate_smoke_report": True,
            "requires_authorization_to_check_output_job_export_diff": True,
        },
        "next_step_recommendation": {
            "step": "ZDoc Step 153",
            "wait_for_chatgpt_review": True,
            "do_not_auto_advance": True,
        },
        "safety_conclusion": {
            "smoke_test_executed": False,
            "backend_started": False,
            "frontend_started": False,
            "ollama_run": False,
            "zdoc_zbid_actual_integration_executed": False,
            "local_deployment_executed": False,
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
        },
    }
    plan.update(overrides)
    return plan


def validate_fake_local_trial_smoke_execution_plan(plan):
    reasons = []

    if not isinstance(plan, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_execution_plan"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(plan)
    if missing_sections:
        reasons.append("missing_required_execution_plan_sections")

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


def assert_formal_flags_false(flags):
    assert flags == CURRENT_STAGE_FORMAL_FLAGS


def test_local_trial_smoke_execution_plan_sections_are_explicit():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert REQUIRED_SECTIONS.issubset(plan)
    assert validate_fake_local_trial_smoke_execution_plan(plan) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_scope_blocks_smoke_execution_and_deployment():
    plan = make_fake_local_trial_smoke_execution_plan()
    scope = plan["scope"]

    assert scope["docs_only"] is True
    assert scope["execute_smoke_test"] is False
    assert scope["start_backend_service"] is False
    assert scope["start_frontend_service"] is False
    assert scope["run_ollama"] is False
    assert scope["access_local_port"] is False
    assert scope["call_zbid"] is False
    assert scope["write_output_job_export"] is False
    assert scope["enter_local_deployment_execution"] is False
    assert scope["enter_50_person_deployment_design"] is False


def test_execution_strategy_order_is_explicit():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert plan["execution_strategy"] == [
        "manual_git_status_preflight",
        "local_config_exists_but_not_committed_preflight",
        "output_job_export_before_snapshot",
        "backend_startup_check",
        "frontend_startup_check",
        "ollama_optional_reachability_check",
        "zdoc_preview_only_data_chain_check",
        "zbid_preview_input_validator_check",
        "formal_chain_block_check",
        "output_job_export_after_snapshot",
        "smoke_report",
        "stop_immediately_on_high_risk_failure",
    ]


def test_preflight_command_placeholders_are_declared_without_execution():
    plan = make_fake_local_trial_smoke_execution_plan()
    preflight = plan["preflight_command_placeholders"]

    assert set(preflight["commands"]) == {
        "pwd",
        "git branch --show-current",
        "git rev-parse HEAD",
        "git status --short",
    }
    assert preflight["future_checks"] == {
        "pwd_is_workspace": "/Users/youfeini/Desktop/文档生成系统",
        "branch_is_main": True,
        "worktree_clean": True,
        "current_tag_declared": True,
        "no_uncommitted_changes": True,
    }
    assert preflight["execute_now"] is False


def test_environment_preflight_placeholders_are_declared():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["environment_preflight_placeholders"],
        {
            "python_version_check_placeholder",
            "node_version_check_placeholder",
            "pnpm_version_check_placeholder",
            "env_local_config_check_placeholder",
            "do_not_print_sensitive_config",
            "do_not_commit_env",
            "do_not_modify_config_files",
            "local_materials_directory_check_placeholder",
            "log_directory_check_placeholder",
            "output_job_export_isolation_check_placeholder",
        },
    )


def test_backend_smoke_placeholders_do_not_start_backend():
    plan = make_fake_local_trial_smoke_execution_plan()
    backend = plan["backend_smoke_execution_placeholders"]

    assert_required_items(
        backend,
        {
            "backend_start_command_placeholder",
            "backend_health_check_command_placeholder",
            "no_write_status_check_placeholder",
            "preview_only_status_check_placeholder",
            "blocked_reasons_response_check_placeholder",
            "request_id_log_check_placeholder",
            "backend_stop_command_placeholder",
            "do_not_execute_in_current_step",
        },
    )
    assert backend["start_backend_now"] is False


def test_frontend_smoke_placeholders_do_not_start_frontend():
    plan = make_fake_local_trial_smoke_execution_plan()
    frontend = plan["frontend_smoke_execution_placeholders"]

    assert_required_items(
        frontend,
        {
            "frontend_dependency_check_placeholder",
            "frontend_start_command_placeholder",
            "page_access_check_placeholder",
            "preview_only_display_check_placeholder",
            "blocked_reasons_display_check_placeholder",
            "formal_buttons_disabled_check_placeholder",
            "frontend_stop_command_placeholder",
            "do_not_execute_in_current_step",
        },
    )
    assert frontend["start_frontend_now"] is False


def test_ollama_smoke_placeholders_do_not_run_ollama():
    plan = make_fake_local_trial_smoke_execution_plan()
    ollama = plan["ollama_optional_smoke_execution_placeholders"]

    assert_required_items(
        ollama,
        {
            "ollama_installed_check_placeholder",
            "ollama_service_status_check_placeholder",
            "ollama_11434_reachability_check_placeholder",
            "model_list_check_placeholder",
            "model_unavailable_fallback_check_placeholder",
            "thinking_only_fallback_no_writeback_check_placeholder",
            "ollama_is_optional_check",
            "model_unavailable_must_not_block_no_write_smoke",
            "model_unavailable_records_fallback",
        },
    )
    assert ollama["run_ollama_now"] is False
    assert ollama["access_127_0_0_1_11434_now"] is False


def test_zdoc_preview_only_smoke_placeholders_are_declared():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["zdoc_preview_only_smoke_execution_placeholders"],
        {
            "preview_packet_generation_check_placeholder",
            "integration_request_id_check",
            "project_document_section_id_check",
            "section_hash_version_check",
            "tender_file_refs_check",
            "scoring_clause_refs_check",
            "evidence_anchor_refs_check",
            "response_mode_check",
            "input_risk_level_check",
            "advisory_quality_gate_status_check",
            "formal_flags_false_check",
            "blocked_reasons_check",
            "must_not_trigger_generate_formal_generation",
        },
    )


def test_zbid_preview_validator_smoke_placeholders_are_declared():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["zbid_preview_validator_smoke_execution_placeholders"],
        {
            "fake_preview_packet_input_check",
            "non_dict_blocked_check",
            "missing_evidence_anchor_blocked_check",
            "missing_scoring_clause_refs_blocked_check",
            "advisory_as_evidence_blocked_check",
            "thinking_only_fallback_blocked_check",
            "high_risk_without_validation_blocked_check",
            "accepted_preview_only_no_writeback_check",
            "zbid_writeback_allowed_false_check",
            "must_not_call_zbid_api_db_writeback",
        },
    )


def test_formal_chain_block_placeholders_are_declared():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["formal_chain_block_smoke_execution_placeholders"],
        {
            "generate_formal_generation_blocked",
            "export_docx_blocked",
            "docx_file_must_not_be_generated",
            "review_apply_blocked",
            "zbid_writeback_blocked",
            "zbid_api_db_writeback_must_not_be_called",
            "formal_writeback_blocked",
            "formal_writeback_dry_run_must_not_open_writeback",
            "output_job_export_must_not_be_written",
            "formal_flags_always_false",
        },
    )


def test_output_job_export_write_detection_placeholder_is_declared():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["output_job_export_write_detection_placeholder"],
        {
            "before_output_job_export_snapshot",
            "after_output_job_export_snapshot",
            "new_file_requires_stop",
            "docx_json_markdown_artifact_requires_stop",
            "job_export_state_file_requires_stop",
            "diff_must_be_recorded",
        },
    )


def test_stop_conditions_are_explicit():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["stop_conditions"],
        {
            "git_status_not_clean",
            "backend_start_failed_without_readable_error",
            "frontend_start_failed_without_readable_error",
            "any_formal_flag_true",
            "output_job_export_write_seen",
            "docx_file_seen",
            "zbid_api_db_writeback_call_seen",
            "review_apply_call_seen",
            "generate_formal_generation_seen",
            "advisory_used_as_evidence",
            "preview_shown_as_formal_body",
            "source_hash_or_version_mismatch_without_block",
            "blocked_reasons_missing",
            "unknown_writeback_risk_seen",
        },
    )


def test_pass_criteria_are_explicit():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["pass_criteria"],
        {
            "backend_can_start",
            "backend_health_readable",
            "frontend_accessible",
            "preview_only_data_chain_can_be_produced",
            "validator_blocks_unsafe_input",
            "evidence_scoring_boundary_clear",
            "docx_zbid_review_apply_formal_writeback_default_blocked",
            "all_formal_flags_false",
            "blocked_reasons_readable",
            "no_output_job_export_write",
            "no_zbid_call",
            "no_docx_generated",
            "no_50_person_deployment_design",
        },
    )


def test_smoke_report_template_is_explicit():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["smoke_report_template"],
        {
            "current_directory",
            "current_branch",
            "starting_head",
            "ending_head",
            "git_status",
            "backend_started",
            "frontend_started",
            "ollama_run",
            "accessed_127_0_0_1_11434",
            "accessed_local_port",
            "preview_packet_generated",
            "validator_executed",
            "generate_triggered",
            "export_docx_triggered",
            "docx_generated",
            "review_apply_triggered",
            "zbid_writeback_triggered",
            "zbid_api_db_writeback_called",
            "output_job_export_written",
            "formal_flags_all_false",
            "blocked_reasons_readable",
            "entered_local_deployment_execution",
            "entered_50_person_deployment_design",
            "failed_items",
            "risk_notes",
            "next_step_recommendation",
        },
    )


def test_future_implementation_boundary_requires_separate_authorization():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_required_items(
        plan["future_implementation_boundary"],
        {
            "requires_authorization_to_start_backend",
            "requires_authorization_to_start_frontend",
            "requires_authorization_to_access_local_port",
            "requires_authorization_to_check_ollama",
            "requires_authorization_to_read_local_config",
            "requires_authorization_to_execute_preview_only_test_request",
            "requires_authorization_to_generate_smoke_report",
            "requires_authorization_to_check_output_job_export_diff",
        },
    )


def test_formal_flags_are_always_false():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert_formal_flags_false(plan["formal_flags"])

    broken = make_fake_local_trial_smoke_execution_plan(
        formal_flags={**CURRENT_STAGE_FORMAL_FLAGS, "output_write_allowed": True}
    )
    result = validate_fake_local_trial_smoke_execution_plan(broken)

    assert result["status"] == "blocked"
    assert "output_write_allowed_must_be_false" in result["blocked_reasons"]


def test_execution_plan_schema_has_no_execution_side_effects():
    plan = make_fake_local_trial_smoke_execution_plan()

    assert plan["execution_side_effects"] == {
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
    }
    result = validate_fake_local_trial_smoke_execution_plan(
        make_fake_local_trial_smoke_execution_plan(
            execution_side_effects={
                **plan["execution_side_effects"],
                "smoke_test_executed": True,
            }
        )
    )

    assert result["status"] == "blocked"
    assert "execution_side_effects_must_not_be_performed" in result["blocked_reasons"]


def test_execution_plan_schema_imports_do_not_pull_main_chain_or_service_modules():
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0].lower())

    assert not (imported_roots & FORBIDDEN_IMPORTS)
