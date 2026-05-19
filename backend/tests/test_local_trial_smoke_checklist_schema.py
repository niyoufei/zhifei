import ast
from pathlib import Path


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"

REQUIRED_SECTIONS = {
    "scope",
    "trial_positioning",
    "pre_run_manual_checklist",
    "backend_smoke_checklist",
    "frontend_smoke_checklist",
    "ollama_smoke_checklist",
    "zdoc_preview_packet_smoke_checklist",
    "zbid_preview_input_validator_smoke_checklist",
    "docx_review_apply_zbid_formal_writeback_block_checklist",
    "evidence_and_scoring_smoke_checklist",
    "audit_fields_checklist",
    "failure_handling_checklist",
    "smoke_test_pass_criteria",
    "smoke_test_stop_criteria",
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


def make_fake_local_trial_smoke_checklist(**overrides):
    checklist = {
        "contract_version": "0.1",
        "generated_at": FIXED_GENERATED_AT,
        "scope": {
            "docs_only": True,
            "execute_smoke_test": False,
            "start_backend_service": False,
            "start_frontend_service": False,
            "run_ollama": False,
            "call_zbid": False,
            "write_output_job_export": False,
            "enter_50_person_deployment_design": False,
        },
        "trial_positioning": {
            "docs_only": True,
            "execute_smoke_test": False,
            "start_services": False,
            "run_ollama": False,
            "call_zbid": False,
            "write_output_job_export": False,
            "enter_50_person_deployment_design": False,
            "verify_high_concurrency": False,
            "verify_formal_writeback": False,
            "verify_docx_formal_export": False,
            "verify_zbid_formal_writeback": False,
        },
        "pre_run_manual_checklist": {
            "check_current_directory": True,
            "check_current_branch": True,
            "check_worktree_clean": True,
            "check_current_tag": True,
            "env_or_local_config_exists_but_not_committed": True,
            "python_environment_rebuildable": True,
            "node_pnpm_environment_rebuildable": True,
            "ollama_optional_service_check_only": True,
            "project_materials_directory_declared": True,
            "log_directory_declared": True,
            "output_job_export_isolated": True,
            "no_write_flag_default_on": True,
            "preview_only_flag_default_on": True,
            "docx_export_flag_default_off": True,
            "zbid_writeback_flag_default_off": True,
            "review_apply_flag_default_off": True,
            "formal_writeback_flag_default_off": True,
        },
        "backend_smoke_checklist": {
            "backend_can_start_check": True,
            "health_check_readable": True,
            "config_load_readable": True,
            "no_write_status_readable": True,
            "preview_only_status_readable": True,
            "zbid_writeback_default_blocked": True,
            "docx_export_default_blocked": True,
            "review_apply_default_blocked": True,
            "formal_writeback_default_blocked": True,
            "errors_include_blocked_reasons": True,
            "logs_include_request_id": True,
            "start_backend_now": False,
        },
        "frontend_smoke_checklist": {
            "frontend_can_start_check": True,
            "page_accessible_check": True,
            "local_model_status_read_only": True,
            "preview_only_result_displayed_as_preview": True,
            "blocked_reasons_readable": True,
            "formal_buttons_disabled_or_unavailable": True,
            "user_must_not_think_preview_wrote_back": True,
            "user_must_not_think_advisory_is_evidence": True,
            "start_frontend_now": False,
        },
        "ollama_smoke_checklist": {
            "ollama_optional_service_check": True,
            "local_model_list_readable_check": True,
            "model_unavailable_fallback": True,
            "thinking_only_fallback_not_formal_body_capability": True,
            "model_failure_must_not_writeback": True,
            "model_failure_must_not_trigger_docx_zbid_review_apply": True,
            "model_output_must_not_be_evidence": True,
            "run_ollama_now": False,
        },
        "zdoc_preview_packet_smoke_checklist": {
            "integration_request_id": True,
            "project_id": True,
            "document_id": True,
            "section_id": True,
            "section_hash": True,
            "section_version": True,
            "tender_file_refs": True,
            "scoring_clause_refs": True,
            "evidence_anchor_refs": True,
            "response_mode": True,
            "input_risk_level": True,
            "advisory_quality_gate_status": True,
            "blocked_reasons": True,
            **CURRENT_STAGE_FORMAL_FLAGS,
        },
        "zbid_preview_input_validator_smoke_checklist": {
            "accepts_fake_dict_only": True,
            "non_dict_input_must_block": True,
            "missing_required_fields_must_block": True,
            "missing_evidence_anchor_must_block": True,
            "missing_scoring_clause_refs_must_block": True,
            "generated_advisory_as_evidence_must_block": True,
            "preview_advisory_as_evidence_must_block": True,
            "shadow_candidate_as_evidence_must_block": True,
            "patch_as_evidence_must_block": True,
            "diff_as_evidence_must_block": True,
            "rollback_as_evidence_must_block": True,
            "dry_run_as_evidence_must_block": True,
            "thinking_only_fallback_must_block": True,
            "high_input_risk_without_validation_must_block": True,
            "zbid_writeback_requested_true_must_block": True,
            "accepted_preview_only_must_not_open_writeback": True,
            "zbid_writeback_allowed": False,
        },
        "docx_review_apply_zbid_formal_writeback_block_checklist": {
            "export_docx_request_must_block": True,
            "docx_file_must_not_be_generated": True,
            "review_apply_request_must_block": True,
            "zbid_writeback_request_must_block": True,
            "zbid_api_db_writeback_must_not_be_called": True,
            "formal_writeback_request_must_block": True,
            "output_job_export_write_must_block": True,
            "dry_run_passed_must_not_open_formal_writeback": True,
            "source_hash_matched_must_not_open_formal_writeback": True,
            "docx_isolation_passed_must_not_open_zbid": True,
            "zbid_isolation_passed_must_not_open_zbid_writeback": True,
        },
        "evidence_and_scoring_smoke_checklist": {
            "evidence_anchor_refs_must_be_verifiable": True,
            "scoring_clause_refs_must_be_verifiable": True,
            "tender_file_refs_are_not_automatic_evidence": True,
            "preview_advisory_must_not_be_evidence": True,
            "zbid_scoring_preview_must_not_be_evidence": True,
            "ai_suggestion_must_not_be_evidence": True,
            "missing_evidence_or_scoring_must_require_review_or_block": True,
            "scoring_clause_must_not_be_fabricated": True,
        },
        "audit_fields_checklist": {
            "request_id",
            "integration_request_id",
            "project_id",
            "document_id",
            "section_id",
            "section_hash",
            "section_version",
            "tender_file_refs",
            "scoring_clause_refs",
            "evidence_anchor_refs",
            "response_mode",
            "input_risk_level",
            "advisory_quality_gate_status",
            "shadow_candidate_id",
            "patch_id",
            "diff_preview_id",
            "rollback_plan_id",
            "dry_run_id",
            "blocked_reasons",
            "generated_at",
            "formal_writeback_allowed",
            "review_apply_allowed",
            "docx_export_allowed",
            "zbid_writeback_allowed",
            "output_write_allowed",
        },
        "failure_handling_checklist": {
            "backend_start_failed_stop_and_record": True,
            "frontend_start_failed_stop_and_record": True,
            "ollama_unavailable_fallback_no_writeback": True,
            "missing_evidence_blocks": True,
            "missing_scoring_refs_blocks_or_requires_human_review": True,
            "docx_request_blocks": True,
            "zbid_writeback_request_blocks": True,
            "review_apply_request_blocks": True,
            "unexpected_output_job_export_write_stop_immediately": True,
            "source_hash_mismatch_stale_source_hash": True,
            "source_version_mismatch_stale_source_version": True,
            "full_backend_tests_collection_order_issue_must_not_drive_production_fixes": True,
        },
        "smoke_test_pass_criteria": {
            "backend_can_start_and_health_status_readable": True,
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
        "smoke_test_stop_criteria": {
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
        },
        "next_step_recommendation": {
            "step": "ZDoc Step 149",
            "tests_only": True,
            "must_not_start_services": True,
            "must_not_run_ollama": True,
            "must_not_execute_smoke_test": True,
            "must_not_call_zbid": True,
            "must_not_write_output_job_export": True,
        },
        "safety_conclusion": {
            "local_deployment_executed": False,
            "zdoc_zbid_actual_integration_executed": False,
            "formal_writeback_implemented": False,
            "docx_export_implemented": False,
            "zbid_writeback_implemented": False,
            "enter_50_person_deployment_design": False,
        },
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
        },
        "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
    }
    checklist.update(overrides)
    return checklist


def validate_fake_local_trial_smoke_checklist(checklist):
    reasons = []

    if not isinstance(checklist, dict):
        return {
            "status": "blocked",
            "blocked_reasons": ["invalid_fake_smoke_checklist"],
            "formal_flags": dict(CURRENT_STAGE_FORMAL_FLAGS),
        }

    missing_sections = REQUIRED_SECTIONS - set(checklist)
    if missing_sections:
        reasons.append("missing_required_smoke_checklist_sections")

    for flag, expected in CURRENT_STAGE_FORMAL_FLAGS.items():
        if checklist.get("formal_flags", {}).get(flag) is not expected:
            reasons.append(f"{flag}_must_be_false")

    if any(checklist.get("execution_side_effects", {}).values()):
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


def test_local_trial_smoke_checklist_sections_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert REQUIRED_SECTIONS.issubset(checklist)
    assert validate_fake_local_trial_smoke_checklist(checklist) == {
        "status": "accepted_fake_schema_only",
        "blocked_reasons": [],
        "formal_flags": CURRENT_STAGE_FORMAL_FLAGS,
    }


def test_trial_positioning_blocks_execution_and_deployment():
    checklist = make_fake_local_trial_smoke_checklist()
    positioning = checklist["trial_positioning"]

    assert positioning["docs_only"] is True
    assert positioning["execute_smoke_test"] is False
    assert positioning["start_services"] is False
    assert positioning["run_ollama"] is False
    assert positioning["call_zbid"] is False
    assert positioning["write_output_job_export"] is False
    assert positioning["enter_50_person_deployment_design"] is False
    assert positioning["verify_high_concurrency"] is False
    assert positioning["verify_formal_writeback"] is False
    assert positioning["verify_docx_formal_export"] is False
    assert positioning["verify_zbid_formal_writeback"] is False


def test_pre_run_manual_checklist_contains_required_items():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["pre_run_manual_checklist"],
        {
            "check_current_directory",
            "check_current_branch",
            "check_worktree_clean",
            "check_current_tag",
            "env_or_local_config_exists_but_not_committed",
            "python_environment_rebuildable",
            "node_pnpm_environment_rebuildable",
            "ollama_optional_service_check_only",
            "project_materials_directory_declared",
            "log_directory_declared",
            "output_job_export_isolated",
            "no_write_flag_default_on",
            "preview_only_flag_default_on",
            "docx_export_flag_default_off",
            "zbid_writeback_flag_default_off",
            "review_apply_flag_default_off",
            "formal_writeback_flag_default_off",
        },
    )


def test_backend_smoke_checklist_is_defined_without_starting_backend():
    checklist = make_fake_local_trial_smoke_checklist()
    backend = checklist["backend_smoke_checklist"]

    assert_required_items(
        backend,
        {
            "backend_can_start_check",
            "health_check_readable",
            "config_load_readable",
            "no_write_status_readable",
            "preview_only_status_readable",
            "zbid_writeback_default_blocked",
            "docx_export_default_blocked",
            "review_apply_default_blocked",
            "formal_writeback_default_blocked",
            "errors_include_blocked_reasons",
            "logs_include_request_id",
        },
    )
    assert backend["start_backend_now"] is False


def test_frontend_smoke_checklist_is_defined_without_starting_frontend():
    checklist = make_fake_local_trial_smoke_checklist()
    frontend = checklist["frontend_smoke_checklist"]

    assert_required_items(
        frontend,
        {
            "frontend_can_start_check",
            "page_accessible_check",
            "local_model_status_read_only",
            "preview_only_result_displayed_as_preview",
            "blocked_reasons_readable",
            "formal_buttons_disabled_or_unavailable",
            "user_must_not_think_preview_wrote_back",
            "user_must_not_think_advisory_is_evidence",
        },
    )
    assert frontend["start_frontend_now"] is False


def test_ollama_smoke_checklist_is_defined_without_running_ollama():
    checklist = make_fake_local_trial_smoke_checklist()
    ollama = checklist["ollama_smoke_checklist"]

    assert_required_items(
        ollama,
        {
            "ollama_optional_service_check",
            "local_model_list_readable_check",
            "model_unavailable_fallback",
            "thinking_only_fallback_not_formal_body_capability",
            "model_failure_must_not_writeback",
            "model_failure_must_not_trigger_docx_zbid_review_apply",
            "model_output_must_not_be_evidence",
        },
    )
    assert ollama["run_ollama_now"] is False


def test_zdoc_preview_packet_smoke_checklist_contains_required_metadata():
    checklist = make_fake_local_trial_smoke_checklist()
    preview_packet = checklist["zdoc_preview_packet_smoke_checklist"]

    assert_required_items(
        preview_packet,
        {
            "integration_request_id",
            "project_id",
            "document_id",
            "section_id",
            "section_hash",
            "section_version",
            "tender_file_refs",
            "scoring_clause_refs",
            "evidence_anchor_refs",
            "response_mode",
            "input_risk_level",
            "advisory_quality_gate_status",
            "blocked_reasons",
        },
    )
    assert_formal_flags_false(
        {flag: preview_packet[flag] for flag in CURRENT_STAGE_FORMAL_FLAGS}
    )


def test_zbid_preview_input_validator_checklist_blocks_unsafe_input():
    checklist = make_fake_local_trial_smoke_checklist()
    validator = checklist["zbid_preview_input_validator_smoke_checklist"]

    assert_required_items(
        validator,
        {
            "accepts_fake_dict_only",
            "non_dict_input_must_block",
            "missing_required_fields_must_block",
            "missing_evidence_anchor_must_block",
            "missing_scoring_clause_refs_must_block",
            "generated_advisory_as_evidence_must_block",
            "preview_advisory_as_evidence_must_block",
            "shadow_candidate_as_evidence_must_block",
            "patch_as_evidence_must_block",
            "diff_as_evidence_must_block",
            "rollback_as_evidence_must_block",
            "dry_run_as_evidence_must_block",
            "thinking_only_fallback_must_block",
            "high_input_risk_without_validation_must_block",
            "zbid_writeback_requested_true_must_block",
            "accepted_preview_only_must_not_open_writeback",
        },
    )
    assert validator["zbid_writeback_allowed"] is False


def test_docx_review_apply_zbid_and_formal_writeback_blocks_are_defined():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["docx_review_apply_zbid_formal_writeback_block_checklist"],
        {
            "export_docx_request_must_block",
            "docx_file_must_not_be_generated",
            "review_apply_request_must_block",
            "zbid_writeback_request_must_block",
            "zbid_api_db_writeback_must_not_be_called",
            "formal_writeback_request_must_block",
            "output_job_export_write_must_block",
            "dry_run_passed_must_not_open_formal_writeback",
            "source_hash_matched_must_not_open_formal_writeback",
            "docx_isolation_passed_must_not_open_zbid",
            "zbid_isolation_passed_must_not_open_zbid_writeback",
        },
    )


def test_evidence_and_scoring_boundaries_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["evidence_and_scoring_smoke_checklist"],
        {
            "evidence_anchor_refs_must_be_verifiable",
            "scoring_clause_refs_must_be_verifiable",
            "tender_file_refs_are_not_automatic_evidence",
            "preview_advisory_must_not_be_evidence",
            "zbid_scoring_preview_must_not_be_evidence",
            "ai_suggestion_must_not_be_evidence",
            "missing_evidence_or_scoring_must_require_review_or_block",
            "scoring_clause_must_not_be_fabricated",
        },
    )


def test_audit_fields_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert {
        "request_id",
        "integration_request_id",
        "project_id",
        "document_id",
        "section_id",
        "section_hash",
        "section_version",
        "tender_file_refs",
        "scoring_clause_refs",
        "evidence_anchor_refs",
        "response_mode",
        "input_risk_level",
        "advisory_quality_gate_status",
        "shadow_candidate_id",
        "patch_id",
        "diff_preview_id",
        "rollback_plan_id",
        "dry_run_id",
        "blocked_reasons",
        "generated_at",
        "formal_writeback_allowed",
        "review_apply_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
    }.issubset(checklist["audit_fields_checklist"])


def test_failure_handling_rules_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["failure_handling_checklist"],
        {
            "backend_start_failed_stop_and_record",
            "frontend_start_failed_stop_and_record",
            "ollama_unavailable_fallback_no_writeback",
            "missing_evidence_blocks",
            "missing_scoring_refs_blocks_or_requires_human_review",
            "docx_request_blocks",
            "zbid_writeback_request_blocks",
            "review_apply_request_blocks",
            "unexpected_output_job_export_write_stop_immediately",
            "source_hash_mismatch_stale_source_hash",
            "source_version_mismatch_stale_source_version",
            "full_backend_tests_collection_order_issue_must_not_drive_production_fixes",
        },
    )


def test_smoke_pass_criteria_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["smoke_test_pass_criteria"],
        {
            "backend_can_start_and_health_status_readable",
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


def test_smoke_stop_criteria_are_explicit():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_required_items(
        checklist["smoke_test_stop_criteria"],
        {
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
        },
    )


def test_formal_flags_are_always_false():
    checklist = make_fake_local_trial_smoke_checklist()

    assert_formal_flags_false(checklist["formal_flags"])
    for section in (
        "zdoc_preview_packet_smoke_checklist",
        "zbid_preview_input_validator_smoke_checklist",
    ):
        flags = {
            flag: checklist[section][flag]
            for flag in CURRENT_STAGE_FORMAL_FLAGS
            if flag in checklist[section]
        }
        for value in flags.values():
            assert value is False

    broken = make_fake_local_trial_smoke_checklist(
        formal_flags={**CURRENT_STAGE_FORMAL_FLAGS, "zbid_writeback_allowed": True}
    )
    result = validate_fake_local_trial_smoke_checklist(broken)

    assert result["status"] == "blocked"
    assert "zbid_writeback_allowed_must_be_false" in result["blocked_reasons"]


def test_local_trial_smoke_schema_has_no_execution_side_effects():
    checklist = make_fake_local_trial_smoke_checklist()

    assert checklist["execution_side_effects"] == {
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
    }
    result = validate_fake_local_trial_smoke_checklist(
        make_fake_local_trial_smoke_checklist(
            execution_side_effects={
                **checklist["execution_side_effects"],
                "local_port_accessed": True,
            }
        )
    )

    assert result["status"] == "blocked"
    assert "execution_side_effects_must_not_be_performed" in result["blocked_reasons"]


def test_local_trial_smoke_schema_imports_do_not_pull_main_chain_or_service_modules():
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0].lower())

    assert not (imported_roots & FORBIDDEN_IMPORTS)
