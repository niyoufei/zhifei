import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "writeback_guard_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "shadow_candidate_id",
    "patch_id",
    "approval_id",
    "diff_preview_id",
    "rollback_plan_id",
    "writeback_guard_status",
    "writeback_decision",
    "writeback_scope",
    "writeback_mode",
    "writeback_target_type",
    "writeback_candidate_hash",
    "source_snapshot_hash",
    "before_text_hash",
    "after_text_preview_hash",
    "patch_operations_preview_hash",
    "diff_preview_hash",
    "rollback_plan_hash",
    "affected_anchor_refs",
    "evidence_anchor_status",
    "evidence_anchor_refs",
    "evidence_binding_status",
    "response_mode",
    "input_risk_level",
    "advisory_quality_gate_status",
    "readiness_status",
    "shadow_candidate_status",
    "patch_status",
    "approval_status",
    "diff_preview_status",
    "rollback_plan_status",
    "source_hash_revalidation_required",
    "source_hash_revalidation_ready",
    "source_hash_revalidation_status",
    "human_approval_required",
    "human_approval_received",
    "diff_preview_required",
    "diff_preview_ready",
    "rollback_required",
    "rollback_plan_ready",
    "review_apply_isolation_required",
    "review_apply_isolation_ready",
    "docx_isolation_required",
    "docx_isolation_ready",
    "zbid_isolation_required",
    "zbid_isolation_ready",
    "generated_at",
    "model_provider",
    "model_name",
    "formal_writeback_allowed",
    "review_apply_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
}

WRITEBACK_GUARD_STATUSES = {
    "not_created",
    "blocked",
    "draft_guard_shadow_only",
    "ready_for_final_review",
    "approved_guard_shadow_only",
    "rejected",
    "stale_source_hash",
}

WRITEBACK_DECISIONS = {
    "none",
    "block",
    "allow_shadow_only",
    "require_revision",
    "reject",
}

WRITEBACK_SCOPES = {
    "single_section",
    "paragraph_range",
    "anchor_range",
    "metadata_only",
}

WRITEBACK_MODES = {
    "disabled_current_stage",
    "dry_run_only",
    "future_manual_apply",
    "future_guarded_apply",
}

WRITEBACK_TARGET_TYPES = {
    "source_section",
    "section_draft",
    "patch_preview",
    "metadata_only",
}

SOURCE_HASH_REVALIDATION_STATUSES = {
    "not_checked",
    "missing",
    "matched",
    "mismatched",
    "stale_source_hash",
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

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def deterministic_writeback_guard_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"writeback-guard-{digest[:16]}"


def make_fake_writeback_guard_contract(**overrides):
    seed = {
        "request_id": "req-writeback-guard-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "writeback_candidate_hash": "sha256:writeback-candidate",
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
        "rollback_plan_hash": "sha256:rollback-plan",
    }
    contract = {
        "contract_version": "0.1",
        "writeback_guard_id": deterministic_writeback_guard_id(seed),
        "request_id": seed["request_id"],
        "source_document_id": seed["source_document_id"],
        "source_section_id": seed["source_section_id"],
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "patch_id": seed["patch_id"],
        "approval_id": seed["approval_id"],
        "diff_preview_id": seed["diff_preview_id"],
        "rollback_plan_id": seed["rollback_plan_id"],
        "writeback_guard_status": "draft_guard_shadow_only",
        "writeback_decision": "none",
        "writeback_scope": "single_section",
        "writeback_mode": "disabled_current_stage",
        "writeback_target_type": "metadata_only",
        "writeback_candidate_hash": seed["writeback_candidate_hash"],
        "source_snapshot_hash": seed["source_snapshot_hash"],
        "before_text_hash": seed["before_text_hash"],
        "after_text_preview_hash": seed["after_text_preview_hash"],
        "patch_operations_preview_hash": seed["patch_operations_preview_hash"],
        "diff_preview_hash": seed["diff_preview_hash"],
        "rollback_plan_hash": seed["rollback_plan_hash"],
        "affected_anchor_refs": ["section:anchor:1"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "shadow_candidate_status": "draft_shadow_only",
        "patch_status": "draft_patch_shadow_only",
        "approval_status": "approved_shadow_only",
        "diff_preview_status": "approved_diff_shadow_only",
        "rollback_plan_status": "approved_rollback_shadow_only",
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "source_hash_revalidation_status": "matched",
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "review_apply_isolation_required": True,
        "review_apply_isolation_ready": True,
        "docx_isolation_required": True,
        "docx_isolation_ready": True,
        "zbid_isolation_required": True,
        "zbid_isolation_ready": True,
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "formal_writeback_allowed": False,
        "review_apply_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "fake_metadata": {
            "source_section_hash_match": True,
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
            "formal_artifact_generated": False,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    if "writeback_guard_id" not in overrides:
        contract["writeback_guard_id"] = deterministic_writeback_guard_id(
            {
                "request_id": contract.get("request_id"),
                "source_document_id": contract.get("source_document_id"),
                "source_section_id": contract.get("source_section_id"),
                "source_section_hash": contract.get("source_section_hash"),
                "source_section_version": contract.get("source_section_version"),
                "shadow_candidate_id": contract.get("shadow_candidate_id"),
                "patch_id": contract.get("patch_id"),
                "approval_id": contract.get("approval_id"),
                "diff_preview_id": contract.get("diff_preview_id"),
                "rollback_plan_id": contract.get("rollback_plan_id"),
                "writeback_candidate_hash": contract.get("writeback_candidate_hash"),
                "source_snapshot_hash": contract.get("source_snapshot_hash"),
                "before_text_hash": contract.get("before_text_hash"),
                "after_text_preview_hash": contract.get("after_text_preview_hash"),
                "patch_operations_preview_hash": contract.get("patch_operations_preview_hash"),
                "diff_preview_hash": contract.get("diff_preview_hash"),
                "rollback_plan_hash": contract.get("rollback_plan_hash"),
            }
        )
    return contract


def validate_fake_writeback_guard_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("writeback_guard_status")
    metadata = contract.get("fake_metadata", {})

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_writeback_guard_contract_fields")
        status = "blocked"

    enum_checks = {
        "writeback_guard_status": (WRITEBACK_GUARD_STATUSES, "invalid_writeback_guard_status"),
        "writeback_decision": (WRITEBACK_DECISIONS, "invalid_writeback_decision"),
        "writeback_scope": (WRITEBACK_SCOPES, "invalid_writeback_scope"),
        "writeback_mode": (WRITEBACK_MODES, "invalid_writeback_mode"),
        "writeback_target_type": (WRITEBACK_TARGET_TYPES, "invalid_writeback_target_type"),
        "source_hash_revalidation_status": (
            SOURCE_HASH_REVALIDATION_STATUSES,
            "invalid_source_hash_revalidation_status",
        ),
        "evidence_binding_status": (EVIDENCE_BINDING_STATUSES, "invalid_evidence_binding_status"),
    }
    for field, (allowed, reason) in enum_checks.items():
        if contract.get(field) not in allowed:
            reasons.append(reason)
            status = "blocked"

    if contract.get("generated_at") != DETERMINISTIC_GENERATED_AT:
        reasons.append("generated_at_must_be_deterministic")
        status = "blocked"

    if (
        contract.get("writeback_guard_status") == "approved_guard_shadow_only"
        or contract.get("writeback_decision") == "allow_shadow_only"
    ):
        reasons.append("guard_is_not_formal_writeback_permission")
        status = "blocked"

    missing_metadata_fields = {
        "shadow_candidate_id": "missing_shadow_candidate_id",
        "patch_id": "missing_patch_id",
        "approval_id": "missing_approval_id",
        "diff_preview_id": "missing_diff_preview_id",
        "rollback_plan_id": "missing_rollback_plan_id",
    }
    for field, reason in missing_metadata_fields.items():
        if not contract.get(field):
            reasons.append(reason)
            status = "blocked"

    if contract.get("shadow_candidate_status") in {"blocked", "not_created"}:
        reasons.append("shadow_candidate_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("patch_status") in {"blocked", "not_created"}:
        reasons.append("patch_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("approval_status") != "approved_shadow_only":
        reasons.append("human_approval_not_received")
        status = "blocked"

    if contract.get("diff_preview_status") in {"blocked", "not_created", "stale_source_hash"}:
        reasons.append("diff_preview_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("rollback_plan_status") in {"blocked", "not_created", "stale_source_hash"}:
        reasons.append("rollback_plan_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_enter_writeback_guard")
        status = "blocked"
    elif contract.get("response_mode") in {"unsupported", "blocked"}:
        reasons.append("unsupported_response_mode")
        status = "blocked"

    evidence_refs = contract.get("evidence_anchor_refs") or []
    if contract.get("evidence_anchor_status") == "missing" or not evidence_refs:
        reasons.append("missing_evidence_anchor")
        status = "blocked"

    binding_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }
    binding_status = contract.get("evidence_binding_status")
    if binding_status in binding_block_reasons:
        reasons.append(binding_block_reasons[binding_status])
        status = "blocked"

    if not contract.get("source_section_hash"):
        reasons.append("missing_source_section_hash")
        status = "blocked"

    if metadata.get("source_section_hash_match") is False:
        reasons.append("source_section_hash_mismatch")
        status = "stale_source_hash"

    if contract.get("source_hash_revalidation_required") and not contract.get(
        "source_hash_revalidation_ready"
    ):
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"

    source_hash_status = contract.get("source_hash_revalidation_status")
    if source_hash_status == "missing":
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"
    elif source_hash_status == "mismatched":
        reasons.append("source_hash_revalidation_mismatch")
        status = "stale_source_hash"
    elif source_hash_status == "stale_source_hash":
        reasons.append("stale_source_hash")
        status = "stale_source_hash"

    required_hashes = {
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }
    for field, reason in required_hashes.items():
        if not contract.get(field):
            reasons.append(reason)
            status = "blocked"

    if contract.get("human_approval_required") and not contract.get("human_approval_received"):
        reasons.append("missing_human_approval")
        status = "blocked"

    if contract.get("diff_preview_required") and not contract.get("diff_preview_ready"):
        reasons.append("diff_preview_missing")
        status = "blocked"

    if contract.get("rollback_required") and not contract.get("rollback_plan_ready"):
        reasons.append("rollback_plan_missing")
        status = "blocked"

    if contract.get("review_apply_isolation_required") and not contract.get(
        "review_apply_isolation_ready"
    ):
        reasons.append("review_apply_isolation_missing")
        status = "blocked"

    if contract.get("docx_isolation_required") and not contract.get("docx_isolation_ready"):
        reasons.append("docx_isolation_missing")

    if contract.get("zbid_isolation_required") and not contract.get("zbid_isolation_ready"):
        reasons.append("zbid_isolation_missing")

    blocked_request_types = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
    }
    request_type = metadata.get("request_type")
    if request_type in blocked_request_types:
        reasons.append(blocked_request_types[request_type])
        status = "blocked"

    validated = dict(contract)
    validated["writeback_guard_status"] = status
    validated["blocked_reasons"] = reasons
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


def test_formal_writeback_guard_contract_required_fields_are_explicit():
    contract = make_fake_writeback_guard_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_writeback_guard_status_enums_are_locked():
    assert WRITEBACK_GUARD_STATUSES == {
        "not_created",
        "blocked",
        "draft_guard_shadow_only",
        "ready_for_final_review",
        "approved_guard_shadow_only",
        "rejected",
        "stale_source_hash",
    }


def test_writeback_decision_scope_mode_target_and_source_hash_status_enums_are_locked():
    assert WRITEBACK_DECISIONS == {
        "none",
        "block",
        "allow_shadow_only",
        "require_revision",
        "reject",
    }
    assert WRITEBACK_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert WRITEBACK_MODES == {
        "disabled_current_stage",
        "dry_run_only",
        "future_manual_apply",
        "future_guarded_apply",
    }
    assert WRITEBACK_TARGET_TYPES == {
        "source_section",
        "section_draft",
        "patch_preview",
        "metadata_only",
    }
    assert SOURCE_HASH_REVALIDATION_STATUSES == {
        "not_checked",
        "missing",
        "matched",
        "mismatched",
        "stale_source_hash",
    }


def test_approved_guard_shadow_only_is_not_formal_writeback_permission():
    cases = [
        {"writeback_guard_status": "approved_guard_shadow_only"},
        {"writeback_decision": "allow_shadow_only"},
    ]

    for overrides in cases:
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**overrides)
        )

        assert validated["formal_writeback_allowed"] is False
        assert validated["review_apply_allowed"] is False
        assert validated["docx_export_allowed"] is False
        assert validated["zbid_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert "guard_is_not_formal_writeback_permission" in validated["blocked_reasons"]


def test_missing_shadow_patch_approval_diff_or_rollback_metadata_blocks_guard():
    cases = [
        ({"shadow_candidate_id": ""}, "missing_shadow_candidate_id"),
        ({"patch_id": ""}, "missing_patch_id"),
        ({"approval_id": ""}, "missing_approval_id"),
        ({"diff_preview_id": ""}, "missing_diff_preview_id"),
        ({"rollback_plan_id": ""}, "missing_rollback_plan_id"),
        ({"shadow_candidate_status": "blocked"}, "shadow_candidate_prerequisite_not_satisfied"),
        ({"shadow_candidate_status": "not_created"}, "shadow_candidate_prerequisite_not_satisfied"),
        ({"patch_status": "blocked"}, "patch_prerequisite_not_satisfied"),
        ({"patch_status": "not_created"}, "patch_prerequisite_not_satisfied"),
        ({"approval_status": "pending_human_review"}, "human_approval_not_received"),
        ({"diff_preview_status": "blocked"}, "diff_preview_prerequisite_not_satisfied"),
        ({"diff_preview_status": "not_created"}, "diff_preview_prerequisite_not_satisfied"),
        ({"diff_preview_status": "stale_source_hash"}, "diff_preview_prerequisite_not_satisfied"),
        ({"rollback_plan_status": "blocked"}, "rollback_plan_prerequisite_not_satisfied"),
        ({"rollback_plan_status": "not_created"}, "rollback_plan_prerequisite_not_satisfied"),
        ({"rollback_plan_status": "stale_source_hash"}, "rollback_plan_prerequisite_not_satisfied"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**overrides)
        )

        assert validated["writeback_guard_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_thinking_only_fallback_blocks_writeback_guard():
    validated = validate_fake_writeback_guard_contract(
        make_fake_writeback_guard_contract(response_mode="thinking_only_fallback")
    )

    assert validated["writeback_guard_status"] in {"blocked", "not_created"}
    assert validated["formal_writeback_allowed"] is False
    assert validated["review_apply_allowed"] is False
    assert "thinking_only_fallback_cannot_enter_writeback_guard" in validated["blocked_reasons"]


def test_missing_evidence_anchor_blocks_writeback_guard():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]

    for overrides in cases:
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**overrides)
        )

        assert validated["writeback_guard_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert "missing_evidence_anchor" in validated["blocked_reasons"]


def test_generated_shadow_patch_diff_and_rollback_sources_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
        "rollback_plan_only_blocked": "rollback_plan_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(evidence_binding_status=binding_status)
        )

        assert validated["writeback_guard_status"] != "ready_for_final_review"
        assert validated["writeback_guard_status"] != "approved_guard_shadow_only"
        assert validated["formal_writeback_allowed"] is False
        assert validated["review_apply_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_or_stale_source_hash_revalidation_blocks_guard():
    cases = [
        (
            {"source_section_hash": ""},
            "missing_source_section_hash",
            "blocked",
        ),
        (
            {"source_hash_revalidation_required": True, "source_hash_revalidation_ready": False},
            "source_hash_revalidation_missing",
            "blocked",
        ),
        (
            {"source_hash_revalidation_status": "missing"},
            "source_hash_revalidation_missing",
            "blocked",
        ),
        (
            {"source_hash_revalidation_status": "mismatched"},
            "source_hash_revalidation_mismatch",
            "stale_source_hash",
        ),
        (
            {"source_hash_revalidation_status": "stale_source_hash"},
            "stale_source_hash",
            "stale_source_hash",
        ),
        (
            {"fake_metadata": {"source_section_hash_match": False}},
            "source_section_hash_mismatch",
            "stale_source_hash",
        ),
    ]

    for overrides, reason, expected_status in cases:
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**overrides)
        )

        assert validated["writeback_guard_status"] == expected_status
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_writeback_hashes_block_guard():
    cases = {
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }

    for field, reason in cases.items():
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**{field: ""})
        )

        assert validated["writeback_guard_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_human_approval_blocks_guard():
    validated = validate_fake_writeback_guard_contract(
        make_fake_writeback_guard_contract(
            human_approval_required=True,
            human_approval_received=False,
        )
    )

    assert validated["writeback_guard_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "missing_human_approval" in validated["blocked_reasons"]


def test_missing_diff_preview_blocks_guard():
    validated = validate_fake_writeback_guard_contract(
        make_fake_writeback_guard_contract(
            diff_preview_required=True,
            diff_preview_ready=False,
        )
    )

    assert validated["writeback_guard_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "diff_preview_missing" in validated["blocked_reasons"]


def test_missing_rollback_plan_blocks_guard():
    validated = validate_fake_writeback_guard_contract(
        make_fake_writeback_guard_contract(
            rollback_required=True,
            rollback_plan_ready=False,
        )
    )

    assert validated["writeback_guard_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "rollback_plan_missing" in validated["blocked_reasons"]


def test_missing_review_apply_isolation_blocks_guard():
    validated = validate_fake_writeback_guard_contract(
        make_fake_writeback_guard_contract(
            review_apply_isolation_required=True,
            review_apply_isolation_ready=False,
        )
    )

    assert validated["writeback_guard_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert validated["review_apply_allowed"] is False
    assert "review_apply_isolation_missing" in validated["blocked_reasons"]


def test_docx_and_zbid_isolation_do_not_open_exports_current_stage():
    cases = [
        (
            {"docx_isolation_required": True, "docx_isolation_ready": False},
            "docx_isolation_missing",
        ),
        (
            {"zbid_isolation_required": True, "zbid_isolation_ready": False},
            "zbid_isolation_missing",
        ),
        (
            {"docx_isolation_required": True, "docx_isolation_ready": True},
            None,
        ),
        (
            {"zbid_isolation_required": True, "zbid_isolation_ready": True},
            None,
        ),
    ]

    for overrides, reason in cases:
        validated = validate_fake_writeback_guard_contract(
            make_fake_writeback_guard_contract(**overrides)
        )

        assert validated["docx_export_allowed"] is False
        assert validated["zbid_writeback_allowed"] is False
        if reason:
            assert reason in validated["blocked_reasons"]


def test_docx_zbid_export_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
    }

    for request_type, reason in cases.items():
        contract = make_fake_writeback_guard_contract(
            fake_metadata={"request_type": request_type}
        )
        validated = validate_fake_writeback_guard_contract(contract)

        assert validated["writeback_guard_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_current_stage_formal_flags_are_always_false():
    for status in WRITEBACK_GUARD_STATUSES:
        contract = make_fake_writeback_guard_contract(writeback_guard_status=status)
        validated = validate_fake_writeback_guard_contract(contract)

        assert_formal_flags_false(validated)


def test_formal_writeback_guard_is_not_source_write():
    contract = make_fake_writeback_guard_contract(
        writeback_guard_status="approved_guard_shadow_only",
        writeback_decision="allow_shadow_only",
        affected_anchor_refs=["section:anchor:1"],
        evidence_anchor_refs=["tender:section:1"],
    )
    validated = validate_fake_writeback_guard_contract(contract)

    assert validated["fake_metadata"]["source_write_performed"] is False
    assert validated["fake_metadata"]["review_apply_performed"] is False
    assert validated["fake_metadata"]["output_write_performed"] is False
    assert validated["writeback_decision"] != "review_apply"
    assert validated["affected_anchor_refs"] != validated["evidence_anchor_refs"]
    assert "guard_is_not_formal_writeback_permission" in validated["blocked_reasons"]
    assert_formal_flags_false(validated)


def test_fake_writeback_guard_contract_uses_deterministic_generated_at_and_id():
    first = make_fake_writeback_guard_contract()
    second = make_fake_writeback_guard_contract()
    changed = make_fake_writeback_guard_contract(source_section_hash="sha256:changed-source")
    source = read_this_test_source()
    called_names = called_names_from_source(source)

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["writeback_guard_id"] == second["writeback_guard_id"]
    assert first["writeback_guard_id"] != changed["writeback_guard_id"]
    assert "now" not in called_names
    assert "time" not in called_names
    assert "uuid4" not in called_names


def test_fake_writeback_guard_contract_does_not_write_output_job_export():
    contract = make_fake_writeback_guard_contract()
    validated = validate_fake_writeback_guard_contract(contract)
    source = read_this_test_source()
    called_names = called_names_from_source(source)

    assert validated["fake_metadata"]["output_write_performed"] is False
    assert validated["fake_metadata"]["formal_artifact_generated"] is False
    assert validated["output_write_allowed"] is False
    assert "write_text" not in called_names
    assert "write_bytes" not in called_names
    assert "mkdir" not in called_names
    assert "unlink" not in called_names
    assert "rename" not in called_names


def test_formal_writeback_guard_contract_schema_imports_do_not_pull_main_chain_modules():
    imported = imported_modules_from_source(read_this_test_source())
    forbidden_modules = {
        "backend.zhifei_autoplan.orchestrator",
        "backend.zhifei_autoplan.llm_client",
        "backend.zhifei_autoplan.provider",
        "backend.zhifei_autoplan.generation",
        "backend.zhifei_autoplan.export",
        "backend.zhifei_autoplan.review",
        "backend.app.routers.actions_bridge",
        "backend.app.routers.export",
        "backend.app.routers.review",
        "backend.zhifei_autoplan.zbid_snapshot_mapper",
        "fastapi",
        "requests",
        "httpx",
        "ollama",
    }

    assert imported.isdisjoint(forbidden_modules)
