import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "integration_request_id",
    "source_system",
    "target_system",
    "project_id",
    "document_id",
    "section_id",
    "section_title",
    "section_hash",
    "section_version",
    "tender_file_refs",
    "scoring_clause_refs",
    "evidence_anchor_refs",
    "evidence_anchor_status",
    "evidence_binding_status",
    "response_mode",
    "input_risk_level",
    "advisory_quality_gate_status",
    "preview_advisory_summary",
    "shadow_candidate_id",
    "patch_id",
    "diff_preview_id",
    "rollback_plan_id",
    "dry_run_id",
    "zbid_preview_mode",
    "zbid_input_status",
    "zbid_mapping_status",
    "zbid_scoring_matrix_status",
    "zbid_writeback_requested",
    "zbid_writeback_allowed",
    "docx_export_allowed",
    "formal_writeback_allowed",
    "review_apply_allowed",
    "output_write_allowed",
    "blocked_reasons",
    "generated_at",
}

AUDIT_FIELDS = {
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
    "zbid_preview_mode",
    "zbid_input_status",
    "zbid_mapping_status",
    "zbid_scoring_matrix_status",
    "blocked_reasons",
    "generated_at",
}

ZBID_PREVIEW_MODES = {
    "disabled_current_stage",
    "metadata_only",
    "preview_only",
    "future_scoring_preview",
    "future_guarded_writeback",
}

ZBID_INPUT_STATUSES = {
    "not_created",
    "blocked",
    "accepted_metadata_only",
    "accepted_preview_only",
    "rejected",
    "stale_source_hash",
}

ZBID_MAPPING_STATUSES = {
    "not_mapped",
    "mapping_placeholder_only",
    "mapped_preview_only",
    "mapping_blocked",
}

ZBID_SCORING_MATRIX_STATUSES = {
    "not_created",
    "preview_only",
    "blocked",
    "requires_human_review",
}

EVIDENCE_BINDING_STATUSES = {
    "missing",
    "bound_to_user_provided_evidence",
    "bound_to_source_verified_evidence",
    "generated_advisory_only_blocked",
    "shadow_candidate_only_blocked",
    "patch_preview_only_blocked",
    "diff_preview_only_blocked",
    "rollback_plan_only_blocked",
}

CURRENT_STAGE_FALSE_FLAGS = {
    "formal_writeback_allowed",
    "review_apply_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

QUALITY_GATE_ALLOWED_STATUSES = {
    "pass",
    "ok",
    "allowed",
    "preview_ok",
    "quality_gate_passed",
}

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def deterministic_integration_request_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"zdoc-zbid-preview-integration-{digest[:16]}"


def make_fake_preview_integration_contract(**overrides):
    seed = {
        "source_system": "zdoc",
        "target_system": "zbid",
        "project_id": "project-preview-only",
        "document_id": "doc-preview-only",
        "section_id": "section-preview-only",
        "section_hash": "sha256:section-preview",
        "section_version": "v1",
        "tender_file_refs": ("tender:file:001",),
        "scoring_clause_refs": ("tender:scoring-clause:001",),
        "evidence_anchor_refs": ("tender:evidence-anchor:001",),
    }
    contract = {
        "contract_version": "0.1",
        "integration_request_id": deterministic_integration_request_id(seed),
        "source_system": seed["source_system"],
        "target_system": seed["target_system"],
        "project_id": seed["project_id"],
        "document_id": seed["document_id"],
        "section_id": seed["section_id"],
        "section_title": "Preview Only Section",
        "section_hash": seed["section_hash"],
        "section_version": seed["section_version"],
        "tender_file_refs": list(seed["tender_file_refs"]),
        "scoring_clause_refs": list(seed["scoring_clause_refs"]),
        "evidence_anchor_refs": list(seed["evidence_anchor_refs"]),
        "evidence_anchor_status": "source_verified",
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "preview_advisory_summary": "Fake preview-only advisory summary.",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "dry_run_id": "dry-run-preview-only",
        "zbid_preview_mode": "preview_only",
        "zbid_input_status": "accepted_preview_only",
        "zbid_mapping_status": "mapped_preview_only",
        "zbid_scoring_matrix_status": "preview_only",
        "zbid_writeback_requested": False,
        "zbid_writeback_allowed": False,
        "docx_export_allowed": False,
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "fake_request_metadata": {
            "docx_export_requested": False,
            "review_apply_requested": False,
            "formal_writeback_requested": False,
            "output_write_requested": False,
            "generate_requested": False,
            "export_docx_requested": False,
            "review_apply_route_triggered": False,
            "zbid_api_called": False,
            "zbid_db_called": False,
            "zbid_writeback_interface_called": False,
            "service_started": False,
            "network_called": False,
            "output_write_performed": False,
            "docx_file_generated": False,
            "json_artifact_generated": False,
            "markdown_artifact_generated": False,
            "evidence_source_type": "verified_anchor",
            "scoring_clause_source": "verified_tender_clause",
            "input_validation_status": "validated",
            "unsafe_input": False,
        },
    }
    contract.update(overrides)
    if "integration_request_id" not in overrides:
        contract["integration_request_id"] = deterministic_integration_request_id(
            {
                "source_system": contract.get("source_system"),
                "target_system": contract.get("target_system"),
                "project_id": contract.get("project_id"),
                "document_id": contract.get("document_id"),
                "section_id": contract.get("section_id"),
                "section_hash": contract.get("section_hash"),
                "section_version": contract.get("section_version"),
                "tender_file_refs": contract.get("tender_file_refs"),
                "scoring_clause_refs": contract.get("scoring_clause_refs"),
                "evidence_anchor_refs": contract.get("evidence_anchor_refs"),
            }
        )
    return contract


def validate_fake_preview_integration_contract(contract):
    validated = dict(contract)
    metadata = dict(validated.get("fake_request_metadata") or {})
    reasons = list(validated.get("blocked_reasons", []))
    input_status = validated.get("zbid_input_status")
    scoring_status = validated.get("zbid_scoring_matrix_status")

    if not REQUIRED_FIELDS.issubset(validated):
        reasons.append("missing_required_zdoc_zbid_preview_integration_fields")
        input_status = "blocked"
        scoring_status = "blocked"

    enum_checks = {
        "zbid_preview_mode": (ZBID_PREVIEW_MODES, "invalid_zbid_preview_mode"),
        "zbid_input_status": (ZBID_INPUT_STATUSES, "invalid_zbid_input_status"),
        "zbid_mapping_status": (ZBID_MAPPING_STATUSES, "invalid_zbid_mapping_status"),
        "zbid_scoring_matrix_status": (
            ZBID_SCORING_MATRIX_STATUSES,
            "invalid_zbid_scoring_matrix_status",
        ),
        "evidence_binding_status": (
            EVIDENCE_BINDING_STATUSES,
            "invalid_evidence_binding_status",
        ),
    }
    for field, (allowed, reason) in enum_checks.items():
        if validated.get(field) not in allowed:
            reasons.append(reason)
            input_status = "blocked"
            scoring_status = "blocked"

    preview_only_conditions = (
        validated.get("zbid_preview_mode") == "preview_only"
        or validated.get("zbid_input_status") == "accepted_preview_only"
        or validated.get("zbid_mapping_status") == "mapped_preview_only"
        or validated.get("zbid_scoring_matrix_status") == "preview_only"
    )
    if preview_only_conditions:
        reasons.append("preview_only_is_not_writeback_export_or_zbid_permission")

    evidence_refs = validated.get("evidence_anchor_refs") or []
    if validated.get("evidence_anchor_status") == "missing" or not evidence_refs:
        reasons.append("missing_evidence_anchor")
        input_status = "blocked"
        scoring_status = "requires_human_review"

    binding_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    binding_status = validated.get("evidence_binding_status")
    if binding_status in binding_block_reasons:
        reasons.append(binding_block_reasons[binding_status])
        input_status = "blocked"
        scoring_status = "requires_human_review"

    evidence_source_reasons = {
        "generated_advisory": "generated_advisory_cannot_be_evidence",
        "preview_advisory_summary": "preview_advisory_summary_cannot_be_evidence",
        "shadow_candidate": "shadow_candidate_cannot_be_evidence",
        "patch_preview": "patch_preview_cannot_be_evidence",
        "diff_preview": "diff_preview_cannot_be_evidence",
        "rollback_plan": "rollback_plan_cannot_be_evidence",
        "dry_run": "dry_run_result_cannot_be_evidence",
    }
    evidence_source = metadata.get("evidence_source_type")
    if evidence_source in evidence_source_reasons:
        reasons.append(evidence_source_reasons[evidence_source])
        input_status = "blocked"
        scoring_status = "requires_human_review"

    scoring_clause_refs = validated.get("scoring_clause_refs") or []
    tender_file_refs = validated.get("tender_file_refs") or []
    if not scoring_clause_refs:
        reasons.append("missing_scoring_clause_refs")
        input_status = "blocked"
        scoring_status = "requires_human_review"
    if not tender_file_refs:
        reasons.append("missing_tender_file_refs")
        input_status = "blocked"
        scoring_status = "requires_human_review"
    scoring_clause_source = metadata.get("scoring_clause_source")
    if scoring_clause_source in {"generated_advisory", "preview_advisory"}:
        reasons.append("scoring_clause_refs_cannot_be_generated_or_advisory")
        input_status = "blocked"
        scoring_status = "requires_human_review"
    if scoring_clause_source == "unverifiable":
        reasons.append("unverifiable_scoring_clause_refs")
        input_status = "blocked"
        scoring_status = "requires_human_review"

    if validated.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_be_final_content")
        input_status = "blocked"
        scoring_status = "blocked"
    if (
        validated.get("input_risk_level") == "high"
        and metadata.get("input_validation_status") != "validated"
    ):
        reasons.append("high_input_risk_without_validation")
        input_status = "blocked"
        scoring_status = "blocked"
    if validated.get("advisory_quality_gate_status") not in QUALITY_GATE_ALLOWED_STATUSES:
        reasons.append("advisory_quality_gate_not_passed")
        input_status = "blocked"
        scoring_status = "blocked"

    request_blocks = {
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "docx_export_requested": "docx_export_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
        "formal_writeback_requested": "formal_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
    }
    if validated.get("zbid_writeback_requested"):
        reasons.append(request_blocks["zbid_writeback_requested"])
        input_status = "blocked"
        scoring_status = "blocked"
    for field, reason in request_blocks.items():
        if field == "zbid_writeback_requested":
            continue
        if metadata.get(field):
            reasons.append(reason)
            input_status = "blocked"
            scoring_status = "blocked"

    if metadata.get("unsafe_input") and not reasons:
        reasons.append("missing_blocked_reasons_on_unsafe_input")
        input_status = "blocked"
        scoring_status = "blocked"

    validated["zbid_input_status"] = input_status
    validated["zbid_scoring_matrix_status"] = scoring_status
    validated["blocked_reasons"] = list(dict.fromkeys(reasons))
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        validated[flag] = False
    return validated


def assert_formal_flags_false(contract):
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        assert contract[flag] is False


def read_this_test_source():
    return Path(__file__).read_text(encoding="utf-8")


def imported_modules_from_source(source):
    imported = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def called_names_from_source(source):
    names = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_zdoc_zbid_preview_integration_contract_required_fields_are_explicit():
    contract = make_fake_preview_integration_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)
    assert contract["contract_version"] == "0.1"
    assert contract["source_system"] == "zdoc"
    assert contract["target_system"] == "zbid"


def test_zbid_preview_mode_and_status_enums_are_locked():
    assert ZBID_PREVIEW_MODES == {
        "disabled_current_stage",
        "metadata_only",
        "preview_only",
        "future_scoring_preview",
        "future_guarded_writeback",
    }
    assert ZBID_INPUT_STATUSES == {
        "not_created",
        "blocked",
        "accepted_metadata_only",
        "accepted_preview_only",
        "rejected",
        "stale_source_hash",
    }
    assert ZBID_MAPPING_STATUSES == {
        "not_mapped",
        "mapping_placeholder_only",
        "mapped_preview_only",
        "mapping_blocked",
    }
    assert ZBID_SCORING_MATRIX_STATUSES == {
        "not_created",
        "preview_only",
        "blocked",
        "requires_human_review",
    }


def test_preview_only_is_not_writeback_or_export_permission():
    contract = validate_fake_preview_integration_contract(
        make_fake_preview_integration_contract(
            zbid_preview_mode="preview_only",
            zbid_input_status="accepted_preview_only",
            zbid_mapping_status="mapped_preview_only",
            zbid_scoring_matrix_status="preview_only",
        )
    )

    assert "preview_only_is_not_writeback_export_or_zbid_permission" in contract[
        "blocked_reasons"
    ]
    assert_formal_flags_false(contract)


def test_missing_evidence_anchor_blocks_zbid_preview_input():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]

    for overrides in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert contract["zbid_input_status"] != "accepted_preview_only"
        assert contract["zbid_scoring_matrix_status"] != "preview_only"
        assert "missing_evidence_anchor" in contract["blocked_reasons"]
        assert_formal_flags_false(contract)


def test_generated_advisory_shadow_patch_diff_rollback_and_dry_run_cannot_be_evidence():
    cases = [
        (
            {"fake_request_metadata": {"evidence_source_type": "generated_advisory"}},
            "generated_advisory_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "preview_advisory_summary"}},
            "preview_advisory_summary_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "shadow_candidate"}},
            "shadow_candidate_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "patch_preview"}},
            "patch_preview_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "diff_preview"}},
            "diff_preview_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "rollback_plan"}},
            "rollback_plan_cannot_be_evidence",
        ),
        (
            {"fake_request_metadata": {"evidence_source_type": "dry_run"}},
            "dry_run_result_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "generated_advisory_only_blocked"},
            "generated_advisory_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "shadow_candidate_only_blocked"},
            "shadow_candidate_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "patch_preview_only_blocked"},
            "patch_preview_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "diff_preview_only_blocked"},
            "diff_preview_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "rollback_plan_only_blocked"},
            "rollback_plan_cannot_be_evidence",
        ),
    ]

    for overrides, reason in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert contract["zbid_input_status"] != "accepted_preview_only"
        assert contract["zbid_scoring_matrix_status"] != "preview_only"
        assert reason in contract["blocked_reasons"]
        assert_formal_flags_false(contract)


def test_missing_or_unverifiable_scoring_clause_blocks_zbid_preview_input():
    cases = [
        ({"scoring_clause_refs": []}, "missing_scoring_clause_refs"),
        (
            {"fake_request_metadata": {"scoring_clause_source": "generated_advisory"}},
            "scoring_clause_refs_cannot_be_generated_or_advisory",
        ),
        (
            {"fake_request_metadata": {"scoring_clause_source": "preview_advisory"}},
            "scoring_clause_refs_cannot_be_generated_or_advisory",
        ),
        (
            {"fake_request_metadata": {"scoring_clause_source": "unverifiable"}},
            "unverifiable_scoring_clause_refs",
        ),
        ({"tender_file_refs": []}, "missing_tender_file_refs"),
    ]

    for overrides, reason in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert contract["zbid_input_status"] == "blocked" or contract[
            "zbid_scoring_matrix_status"
        ] == "requires_human_review"
        assert contract["zbid_writeback_allowed"] is False
        assert reason in contract["blocked_reasons"]


def test_thinking_only_fallback_high_risk_or_failed_quality_gate_blocks_preview_input():
    cases = [
        (
            {"response_mode": "thinking_only_fallback"},
            "thinking_only_fallback_cannot_be_final_content",
        ),
        (
            {
                "input_risk_level": "high",
                "fake_request_metadata": {"input_validation_status": "missing"},
            },
            "high_input_risk_without_validation",
        ),
        ({"advisory_quality_gate_status": "failed"}, "advisory_quality_gate_not_passed"),
        (
            {"evidence_binding_status": "generated_advisory_only_blocked"},
            "generated_advisory_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "shadow_candidate_only_blocked"},
            "shadow_candidate_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "patch_preview_only_blocked"},
            "patch_preview_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "diff_preview_only_blocked"},
            "diff_preview_cannot_be_evidence",
        ),
        (
            {"evidence_binding_status": "rollback_plan_only_blocked"},
            "rollback_plan_cannot_be_evidence",
        ),
    ]

    for overrides, reason in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert contract["zbid_input_status"] == "blocked"
        assert reason in contract["blocked_reasons"]
        assert_formal_flags_false(contract)


def test_zbid_docx_review_apply_formal_and_output_requests_are_blocked():
    cases = [
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        (
            {"fake_request_metadata": {"docx_export_requested": True}},
            "docx_export_request_blocked",
        ),
        (
            {"fake_request_metadata": {"review_apply_requested": True}},
            "review_apply_request_blocked",
        ),
        (
            {"fake_request_metadata": {"formal_writeback_requested": True}},
            "formal_writeback_request_blocked",
        ),
        (
            {"fake_request_metadata": {"output_write_requested": True}},
            "output_write_request_blocked",
        ),
    ]

    for overrides, reason in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert contract["zbid_input_status"] == "blocked"
        assert reason in contract["blocked_reasons"]
        assert_formal_flags_false(contract)


def test_current_stage_formal_flags_are_always_false():
    cases = []
    cases.extend({"zbid_input_status": status} for status in ZBID_INPUT_STATUSES)
    cases.extend({"zbid_scoring_matrix_status": status} for status in ZBID_SCORING_MATRIX_STATUSES)

    for overrides in cases:
        contract = validate_fake_preview_integration_contract(
            make_fake_preview_integration_contract(**overrides)
        )

        assert_formal_flags_false(contract)


def test_preview_integration_audit_fields_are_explicit():
    contract = make_fake_preview_integration_contract()

    assert AUDIT_FIELDS.issubset(contract)
    for field in AUDIT_FIELDS - {"blocked_reasons"}:
        assert contract[field] not in (None, "")
    assert isinstance(contract["blocked_reasons"], list)


def test_fake_preview_integration_contract_uses_deterministic_generated_at_and_id():
    first = make_fake_preview_integration_contract()
    second = make_fake_preview_integration_contract()
    changed = make_fake_preview_integration_contract(section_hash="sha256:changed")
    explicit = make_fake_preview_integration_contract(
        integration_request_id="fixed-preview-integration-id"
    )
    source = read_this_test_source()
    imported = imported_modules_from_source(source)
    called = called_names_from_source(source)

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["integration_request_id"] == second["integration_request_id"]
    assert first["integration_request_id"] != changed["integration_request_id"]
    assert explicit["integration_request_id"] == "fixed-preview-integration-id"
    assert "datetime" not in imported
    assert "time" not in imported
    assert "uuid" not in imported
    assert "random" not in imported
    assert {"now", "time", "uuid4", "random"}.isdisjoint(called)


def test_preview_integration_contract_does_not_write_files_start_services_or_call_zbid():
    contract = validate_fake_preview_integration_contract(
        make_fake_preview_integration_contract()
    )
    source = read_this_test_source()
    called = called_names_from_source(source)
    metadata = contract["fake_request_metadata"]

    assert metadata["zbid_api_called"] is False
    assert metadata["zbid_db_called"] is False
    assert metadata["zbid_writeback_interface_called"] is False
    assert metadata["service_started"] is False
    assert metadata["network_called"] is False
    assert metadata["output_write_performed"] is False
    assert metadata["docx_file_generated"] is False
    assert metadata["json_artifact_generated"] is False
    assert metadata["markdown_artifact_generated"] is False
    assert {"open", "write_text", "write_bytes", "mkdir", "touch", "unlink"}.isdisjoint(called)
    assert {"run", "Popen", "check_call", "check_output", "urlopen"}.isdisjoint(called)


def test_preview_integration_contract_schema_imports_do_not_pull_main_chain_or_zbid_modules():
    source = read_this_test_source()
    imported = imported_modules_from_source(source)
    forbidden_imports = {
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
        "backend.zhifei_autoplan",
        "backend.app",
    }

    assert imported == {"ast", "hashlib", "json", "pathlib"}
    for module in imported:
        assert not any(forbidden in module.lower() for forbidden in forbidden_imports)
