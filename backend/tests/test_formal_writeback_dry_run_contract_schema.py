import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "dry_run_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "current_source_section_hash",
    "current_source_section_version",
    "shadow_candidate_id",
    "patch_id",
    "approval_id",
    "diff_preview_id",
    "rollback_plan_id",
    "writeback_guard_id",
    "source_hash_guard_id",
    "review_apply_guard_id",
    "docx_isolation_guard_id",
    "zbid_isolation_guard_id",
    "dry_run_status",
    "dry_run_decision",
    "dry_run_scope",
    "dry_run_mode",
    "dry_run_target_type",
    "dry_run_request_status",
    "dry_run_requested",
    "dry_run_payload_hash",
    "dry_run_candidate_hash",
    "dry_run_source_snapshot_hash",
    "writeback_candidate_hash",
    "docx_candidate_hash",
    "zbid_candidate_hash",
    "zbid_target_mapping_hash",
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
    "writeback_guard_status",
    "source_hash_guard_status",
    "review_apply_isolation_status",
    "docx_isolation_status",
    "zbid_isolation_status",
    "source_hash_revalidation_status",
    "source_version_revalidation_status",
    "source_hash_match",
    "source_version_match",
    "human_approval_required",
    "human_approval_received",
    "diff_preview_required",
    "diff_preview_ready",
    "rollback_required",
    "rollback_plan_ready",
    "formal_writeback_guard_required",
    "formal_writeback_guard_ready",
    "source_hash_revalidation_required",
    "source_hash_revalidation_ready",
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

DRY_RUN_STATUSES = {
    "not_created",
    "blocked",
    "draft_dry_run_shadow_only",
    "simulated_shadow_only",
    "passed_shadow_only",
    "failed_shadow_only",
    "rejected",
    "stale_source_hash",
    "stale_source_version",
}

DRY_RUN_DECISIONS = {
    "none",
    "block",
    "simulate_shadow_only",
    "pass_shadow_only",
    "require_revision",
    "reject",
}

DRY_RUN_SCOPES = {
    "single_section",
    "selected_sections",
    "full_document",
    "metadata_only",
}

DRY_RUN_MODES = {
    "disabled_current_stage",
    "metadata_only",
    "future_dry_run_only",
    "future_guarded_dry_run",
}

DRY_RUN_TARGET_TYPES = {
    "source_section",
    "section_draft",
    "docx_document",
    "zbid_section",
    "metadata_only",
}

DRY_RUN_REQUEST_STATUSES = {
    "not_requested",
    "requested_blocked",
    "payload_blocked",
    "future_dry_run_only",
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


def deterministic_dry_run_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"formal-writeback-dry-run-{digest[:16]}"


def make_fake_dry_run_contract(**overrides):
    seed = {
        "request_id": "req-formal-writeback-dry-run-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "current_source_section_hash": "sha256:source-section",
        "current_source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "rollback_plan_id": "rollback-plan-preview-only",
        "writeback_guard_id": "writeback-guard-preview-only",
        "source_hash_guard_id": "source-hash-guard-preview-only",
        "review_apply_guard_id": "review-apply-guard-preview-only",
        "docx_isolation_guard_id": "docx-isolation-guard-preview-only",
        "zbid_isolation_guard_id": "zbid-isolation-guard-preview-only",
        "dry_run_payload_hash": "sha256:dry-run-payload-preview",
        "dry_run_candidate_hash": "sha256:dry-run-candidate-preview",
        "dry_run_source_snapshot_hash": "sha256:dry-run-source-snapshot",
        "writeback_candidate_hash": "sha256:writeback-candidate",
        "docx_candidate_hash": "sha256:docx-candidate-preview",
        "zbid_candidate_hash": "sha256:zbid-candidate-preview",
        "zbid_target_mapping_hash": "sha256:zbid-target-mapping-preview",
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
        "rollback_plan_hash": "sha256:rollback-plan",
    }
    contract = {
        "contract_version": "0.1",
        "dry_run_id": deterministic_dry_run_id(seed),
        "request_id": seed["request_id"],
        "source_document_id": seed["source_document_id"],
        "source_section_id": seed["source_section_id"],
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "current_source_section_hash": seed["current_source_section_hash"],
        "current_source_section_version": seed["current_source_section_version"],
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "patch_id": seed["patch_id"],
        "approval_id": seed["approval_id"],
        "diff_preview_id": seed["diff_preview_id"],
        "rollback_plan_id": seed["rollback_plan_id"],
        "writeback_guard_id": seed["writeback_guard_id"],
        "source_hash_guard_id": seed["source_hash_guard_id"],
        "review_apply_guard_id": seed["review_apply_guard_id"],
        "docx_isolation_guard_id": seed["docx_isolation_guard_id"],
        "zbid_isolation_guard_id": seed["zbid_isolation_guard_id"],
        "dry_run_status": "passed_shadow_only",
        "dry_run_decision": "none",
        "dry_run_scope": "single_section",
        "dry_run_mode": "disabled_current_stage",
        "dry_run_target_type": "metadata_only",
        "dry_run_request_status": "not_requested",
        "dry_run_requested": False,
        "dry_run_payload_hash": seed["dry_run_payload_hash"],
        "dry_run_candidate_hash": seed["dry_run_candidate_hash"],
        "dry_run_source_snapshot_hash": seed["dry_run_source_snapshot_hash"],
        "writeback_candidate_hash": seed["writeback_candidate_hash"],
        "docx_candidate_hash": seed["docx_candidate_hash"],
        "zbid_candidate_hash": seed["zbid_candidate_hash"],
        "zbid_target_mapping_hash": seed["zbid_target_mapping_hash"],
        "source_snapshot_hash": seed["source_snapshot_hash"],
        "before_text_hash": seed["before_text_hash"],
        "after_text_preview_hash": seed["after_text_preview_hash"],
        "patch_operations_preview_hash": seed["patch_operations_preview_hash"],
        "diff_preview_hash": seed["diff_preview_hash"],
        "rollback_plan_hash": seed["rollback_plan_hash"],
        "affected_anchor_refs": ["section:anchor:affected"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:evidence"],
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
        "writeback_guard_status": "approved_guard_shadow_only",
        "source_hash_guard_status": "source_hash_matched_shadow_only",
        "review_apply_isolation_status": "isolated_shadow_only",
        "docx_isolation_status": "isolated_shadow_only",
        "zbid_isolation_status": "isolated_shadow_only",
        "source_hash_revalidation_status": "matched",
        "source_version_revalidation_status": "matched",
        "source_hash_match": True,
        "source_version_match": True,
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
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
        "docx_export_requested": False,
        "zbid_writeback_requested": False,
        "output_write_requested": False,
        "formal_generation_requested": False,
        "review_apply_requested": False,
        "export_docx_request_triggered": False,
        "dry_run_writeback_performed": False,
        "fake_metadata": {
            "dry_run_payload_source": "caller_supplied_fake_metadata",
            "dry_run_payload_file_read_performed": False,
            "dry_run_candidate_source": "caller_supplied_fake_metadata",
            "real_source_body_read_performed": False,
            "real_docx_read_performed": False,
            "real_zbid_data_read_performed": False,
            "source_hash_calculated_from_real_body": False,
            "source_section_compared": False,
            "source_write_performed": False,
            "formal_writeback_performed": False,
            "review_apply_performed": False,
            "export_docx_performed": False,
            "zbid_api_called": False,
            "zbid_db_called": False,
            "zbid_writeback_interface_called": False,
            "zbid_writeback_performed": False,
            "docx_file_generated": False,
            "json_artifact_generated": False,
            "markdown_artifact_generated": False,
            "output_write_performed": False,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    if "dry_run_id" not in overrides:
        contract["dry_run_id"] = deterministic_dry_run_id(
            {
                "request_id": contract.get("request_id"),
                "source_document_id": contract.get("source_document_id"),
                "source_section_id": contract.get("source_section_id"),
                "source_section_hash": contract.get("source_section_hash"),
                "source_section_version": contract.get("source_section_version"),
                "current_source_section_hash": contract.get("current_source_section_hash"),
                "current_source_section_version": contract.get(
                    "current_source_section_version"
                ),
                "shadow_candidate_id": contract.get("shadow_candidate_id"),
                "patch_id": contract.get("patch_id"),
                "approval_id": contract.get("approval_id"),
                "diff_preview_id": contract.get("diff_preview_id"),
                "rollback_plan_id": contract.get("rollback_plan_id"),
                "writeback_guard_id": contract.get("writeback_guard_id"),
                "source_hash_guard_id": contract.get("source_hash_guard_id"),
                "review_apply_guard_id": contract.get("review_apply_guard_id"),
                "docx_isolation_guard_id": contract.get("docx_isolation_guard_id"),
                "zbid_isolation_guard_id": contract.get("zbid_isolation_guard_id"),
                "dry_run_payload_hash": contract.get("dry_run_payload_hash"),
                "dry_run_candidate_hash": contract.get("dry_run_candidate_hash"),
                "dry_run_source_snapshot_hash": contract.get(
                    "dry_run_source_snapshot_hash"
                ),
                "writeback_candidate_hash": contract.get("writeback_candidate_hash"),
                "docx_candidate_hash": contract.get("docx_candidate_hash"),
                "zbid_candidate_hash": contract.get("zbid_candidate_hash"),
                "zbid_target_mapping_hash": contract.get("zbid_target_mapping_hash"),
                "source_snapshot_hash": contract.get("source_snapshot_hash"),
                "before_text_hash": contract.get("before_text_hash"),
                "after_text_preview_hash": contract.get("after_text_preview_hash"),
                "patch_operations_preview_hash": contract.get(
                    "patch_operations_preview_hash"
                ),
                "diff_preview_hash": contract.get("diff_preview_hash"),
                "rollback_plan_hash": contract.get("rollback_plan_hash"),
            }
        )
    return contract


def validate_fake_dry_run_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("dry_run_status")

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_formal_writeback_dry_run_contract_fields")
        status = "blocked"

    enum_checks = {
        "dry_run_status": (DRY_RUN_STATUSES, "invalid_dry_run_status"),
        "dry_run_decision": (DRY_RUN_DECISIONS, "invalid_dry_run_decision"),
        "dry_run_scope": (DRY_RUN_SCOPES, "invalid_dry_run_scope"),
        "dry_run_mode": (DRY_RUN_MODES, "invalid_dry_run_mode"),
        "dry_run_target_type": (DRY_RUN_TARGET_TYPES, "invalid_dry_run_target_type"),
        "dry_run_request_status": (
            DRY_RUN_REQUEST_STATUSES,
            "invalid_dry_run_request_status",
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
        contract.get("dry_run_status") == "passed_shadow_only"
        or contract.get("dry_run_decision") == "pass_shadow_only"
    ):
        reasons.append("dry_run_passed_is_not_actual_writeback_permission")

    missing_metadata_fields = {
        "shadow_candidate_id": "missing_shadow_candidate_id",
        "patch_id": "missing_patch_id",
        "approval_id": "missing_approval_id",
        "diff_preview_id": "missing_diff_preview_id",
        "rollback_plan_id": "missing_rollback_plan_id",
        "writeback_guard_id": "missing_writeback_guard_id",
        "source_hash_guard_id": "missing_source_hash_guard_id",
        "review_apply_guard_id": "missing_review_apply_guard_id",
        "docx_isolation_guard_id": "missing_docx_isolation_guard_id",
        "zbid_isolation_guard_id": "missing_zbid_isolation_guard_id",
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

    if contract.get("writeback_guard_status") in {"blocked", "not_created", "stale_source_hash"}:
        reasons.append("formal_writeback_guard_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("source_hash_guard_status") in {
        "blocked",
        "not_created",
        "stale_source_hash",
        "stale_source_version",
    }:
        reasons.append("source_hash_guard_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("review_apply_isolation_status") in {
        "blocked",
        "not_created",
        "stale_source_hash",
        "stale_source_version",
    }:
        reasons.append("review_apply_isolation_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("docx_isolation_status") in {
        "blocked",
        "not_created",
        "stale_source_hash",
        "stale_source_version",
    }:
        reasons.append("docx_isolation_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("zbid_isolation_status") in {
        "blocked",
        "not_created",
        "stale_source_hash",
        "stale_source_version",
    }:
        reasons.append("zbid_isolation_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_enter_dry_run")
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

    if not contract.get("source_section_version"):
        reasons.append("missing_source_section_version")
        status = "blocked"

    if not contract.get("current_source_section_hash"):
        reasons.append("missing_current_source_section_hash")
        status = "blocked"

    hash_status = contract.get("source_hash_revalidation_status")
    if hash_status == "mismatched":
        reasons.append("source_hash_mismatch")
        status = "stale_source_hash"
    elif hash_status == "stale_source_hash":
        reasons.append("stale_source_hash")
        status = "stale_source_hash"

    if contract.get("source_hash_match") is False:
        reasons.append("source_hash_mismatch")
        status = "stale_source_hash"

    if not contract.get("current_source_section_version"):
        reasons.append("missing_current_source_section_version")
        status = "blocked"

    version_status = contract.get("source_version_revalidation_status")
    if version_status == "mismatched":
        reasons.append("source_version_mismatch")
        status = "stale_source_version"
    elif version_status == "stale_source_version":
        reasons.append("stale_source_version")
        status = "stale_source_version"

    if contract.get("source_version_match") is False:
        reasons.append("source_version_mismatch")
        status = "stale_source_version"

    request_status_reasons = {
        "requested_blocked": "dry_run_request_blocked",
        "payload_blocked": "dry_run_payload_blocked",
    }
    request_status = contract.get("dry_run_request_status")
    if request_status in request_status_reasons:
        reasons.append(request_status_reasons[request_status])
        status = "blocked"

    if contract.get("dry_run_requested"):
        reasons.append("dry_run_request_blocked")
        status = "blocked"

    if not contract.get("dry_run_payload_hash"):
        reasons.append("dry_run_payload_blocked")
        status = "blocked"

    required_hashes = {
        "dry_run_candidate_hash": "missing_dry_run_candidate_hash",
        "dry_run_source_snapshot_hash": "missing_dry_run_source_snapshot_hash",
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "docx_candidate_hash": "missing_docx_candidate_hash",
        "zbid_candidate_hash": "missing_zbid_candidate_hash",
        "zbid_target_mapping_hash": "missing_zbid_target_mapping_hash",
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

    if contract.get("formal_writeback_guard_required") and not contract.get(
        "formal_writeback_guard_ready"
    ):
        reasons.append("formal_writeback_guard_missing")
        status = "blocked"

    if contract.get("source_hash_revalidation_required") and not contract.get(
        "source_hash_revalidation_ready"
    ):
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"

    if contract.get("review_apply_isolation_required") and not contract.get(
        "review_apply_isolation_ready"
    ):
        reasons.append("review_apply_isolation_missing")
        status = "blocked"

    if contract.get("docx_isolation_required") and not contract.get("docx_isolation_ready"):
        reasons.append("docx_isolation_missing")
        status = "blocked"

    if contract.get("zbid_isolation_required") and not contract.get("zbid_isolation_ready"):
        reasons.append("zbid_isolation_missing")
        status = "blocked"

    request_flags = {
        "docx_export_requested": "docx_export_request_blocked",
        "zbid_writeback_requested": "zbid_writeback_request_blocked",
        "output_write_requested": "output_write_request_blocked",
        "formal_generation_requested": "formal_generation_request_blocked",
        "review_apply_requested": "review_apply_request_blocked",
        "export_docx_request_triggered": "export_docx_request_blocked",
    }
    for field, reason in request_flags.items():
        if contract.get(field):
            reasons.append(reason)
            status = "blocked"

    blocked_request_types = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
        "dry_run": "dry_run_request_blocked",
    }
    request_type = contract.get("fake_metadata", {}).get("request_type")
    if request_type in blocked_request_types:
        reasons.append(blocked_request_types[request_type])
        status = "blocked"

    validated = dict(contract)
    validated["dry_run_status"] = status
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


def test_formal_writeback_dry_run_contract_required_fields_are_explicit():
    contract = make_fake_dry_run_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_dry_run_status_enums_are_locked():
    assert DRY_RUN_STATUSES == {
        "not_created",
        "blocked",
        "draft_dry_run_shadow_only",
        "simulated_shadow_only",
        "passed_shadow_only",
        "failed_shadow_only",
        "rejected",
        "stale_source_hash",
        "stale_source_version",
    }


def test_dry_run_decision_scope_mode_target_and_request_status_enums_are_locked():
    assert DRY_RUN_DECISIONS == {
        "none",
        "block",
        "simulate_shadow_only",
        "pass_shadow_only",
        "require_revision",
        "reject",
    }
    assert DRY_RUN_SCOPES == {
        "single_section",
        "selected_sections",
        "full_document",
        "metadata_only",
    }
    assert DRY_RUN_MODES == {
        "disabled_current_stage",
        "metadata_only",
        "future_dry_run_only",
        "future_guarded_dry_run",
    }
    assert DRY_RUN_TARGET_TYPES == {
        "source_section",
        "section_draft",
        "docx_document",
        "zbid_section",
        "metadata_only",
    }
    assert DRY_RUN_REQUEST_STATUSES == {
        "not_requested",
        "requested_blocked",
        "payload_blocked",
        "future_dry_run_only",
    }


def test_dry_run_passed_is_not_writeback_permission():
    cases = [
        {"dry_run_status": "passed_shadow_only"},
        {"dry_run_decision": "pass_shadow_only"},
    ]

    for overrides in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert_formal_flags_false(validated)
        assert "dry_run_passed_is_not_actual_writeback_permission" in validated[
            "blocked_reasons"
        ]


def test_dry_run_request_payload_and_candidate_are_blocked():
    cases = [
        ({"dry_run_requested": True}, "dry_run_request_blocked"),
        ({"dry_run_request_status": "requested_blocked"}, "dry_run_request_blocked"),
        ({"dry_run_request_status": "payload_blocked"}, "dry_run_payload_blocked"),
        ({"dry_run_payload_hash": ""}, "dry_run_payload_blocked"),
        ({"dry_run_candidate_hash": ""}, "missing_dry_run_candidate_hash"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_upstream_metadata_blocks_dry_run():
    cases = [
        ({"shadow_candidate_id": ""}, "missing_shadow_candidate_id"),
        ({"patch_id": ""}, "missing_patch_id"),
        ({"approval_id": ""}, "missing_approval_id"),
        ({"diff_preview_id": ""}, "missing_diff_preview_id"),
        ({"rollback_plan_id": ""}, "missing_rollback_plan_id"),
        ({"writeback_guard_id": ""}, "missing_writeback_guard_id"),
        ({"source_hash_guard_id": ""}, "missing_source_hash_guard_id"),
        ({"review_apply_guard_id": ""}, "missing_review_apply_guard_id"),
        ({"docx_isolation_guard_id": ""}, "missing_docx_isolation_guard_id"),
        ({"zbid_isolation_guard_id": ""}, "missing_zbid_isolation_guard_id"),
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
        (
            {"writeback_guard_status": "blocked"},
            "formal_writeback_guard_prerequisite_not_satisfied",
        ),
        (
            {"writeback_guard_status": "not_created"},
            "formal_writeback_guard_prerequisite_not_satisfied",
        ),
        (
            {"writeback_guard_status": "stale_source_hash"},
            "formal_writeback_guard_prerequisite_not_satisfied",
        ),
        (
            {"source_hash_guard_status": "blocked"},
            "source_hash_guard_prerequisite_not_satisfied",
        ),
        (
            {"source_hash_guard_status": "not_created"},
            "source_hash_guard_prerequisite_not_satisfied",
        ),
        (
            {"source_hash_guard_status": "stale_source_hash"},
            "source_hash_guard_prerequisite_not_satisfied",
        ),
        (
            {"source_hash_guard_status": "stale_source_version"},
            "source_hash_guard_prerequisite_not_satisfied",
        ),
        (
            {"review_apply_isolation_status": "blocked"},
            "review_apply_isolation_prerequisite_not_satisfied",
        ),
        (
            {"review_apply_isolation_status": "not_created"},
            "review_apply_isolation_prerequisite_not_satisfied",
        ),
        (
            {"review_apply_isolation_status": "stale_source_hash"},
            "review_apply_isolation_prerequisite_not_satisfied",
        ),
        (
            {"review_apply_isolation_status": "stale_source_version"},
            "review_apply_isolation_prerequisite_not_satisfied",
        ),
        (
            {"docx_isolation_status": "blocked"},
            "docx_isolation_prerequisite_not_satisfied",
        ),
        (
            {"docx_isolation_status": "not_created"},
            "docx_isolation_prerequisite_not_satisfied",
        ),
        (
            {"docx_isolation_status": "stale_source_hash"},
            "docx_isolation_prerequisite_not_satisfied",
        ),
        (
            {"docx_isolation_status": "stale_source_version"},
            "docx_isolation_prerequisite_not_satisfied",
        ),
        (
            {"zbid_isolation_status": "blocked"},
            "zbid_isolation_prerequisite_not_satisfied",
        ),
        (
            {"zbid_isolation_status": "not_created"},
            "zbid_isolation_prerequisite_not_satisfied",
        ),
        (
            {"zbid_isolation_status": "stale_source_hash"},
            "zbid_isolation_prerequisite_not_satisfied",
        ),
        (
            {"zbid_isolation_status": "stale_source_version"},
            "zbid_isolation_prerequisite_not_satisfied",
        ),
    ]

    for overrides, reason in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_thinking_only_fallback_blocks_dry_run():
    validated = validate_fake_dry_run_contract(
        make_fake_dry_run_contract(response_mode="thinking_only_fallback")
    )

    assert validated["dry_run_status"] in {"blocked", "not_created"}
    assert validated["formal_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "thinking_only_fallback_cannot_enter_dry_run" in validated["blocked_reasons"]


def test_missing_evidence_anchor_blocks_dry_run():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]

    for overrides in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
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
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(evidence_binding_status=binding_status)
        )

        assert validated["dry_run_status"] != "passed_shadow_only"
        assert validated["formal_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_source_hash_or_version_mismatch_blocks_dry_run():
    cases = [
        ({"source_hash_match": False}, "source_hash_mismatch"),
        ({"source_version_match": False}, "source_version_mismatch"),
        ({"source_hash_revalidation_status": "mismatched"}, "source_hash_mismatch"),
        ({"source_hash_revalidation_status": "stale_source_hash"}, "stale_source_hash"),
        (
            {"source_version_revalidation_status": "mismatched"},
            "source_version_mismatch",
        ),
        (
            {"source_version_revalidation_status": "stale_source_version"},
            "stale_source_version",
        ),
        ({"current_source_section_hash": ""}, "missing_current_source_section_hash"),
        ({"current_source_section_version": ""}, "missing_current_source_section_version"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] in {
            "stale_source_hash",
            "stale_source_version",
            "blocked",
        }
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_required_hashes_block_dry_run():
    cases = {
        "dry_run_candidate_hash": "missing_dry_run_candidate_hash",
        "dry_run_source_snapshot_hash": "missing_dry_run_source_snapshot_hash",
        "writeback_candidate_hash": "missing_writeback_candidate_hash",
        "docx_candidate_hash": "missing_docx_candidate_hash",
        "zbid_candidate_hash": "missing_zbid_candidate_hash",
        "zbid_target_mapping_hash": "missing_zbid_target_mapping_hash",
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
        "rollback_plan_hash": "missing_rollback_plan_hash",
    }

    for field, reason in cases.items():
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**{field: ""})
        )

        assert validated["dry_run_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_approval_diff_rollback_formal_source_hash_review_apply_docx_or_zbid_blocks_dry_run():
    cases = [
        (
            {"human_approval_required": True, "human_approval_received": False},
            "missing_human_approval",
        ),
        ({"diff_preview_required": True, "diff_preview_ready": False}, "diff_preview_missing"),
        ({"rollback_required": True, "rollback_plan_ready": False}, "rollback_plan_missing"),
        (
            {"formal_writeback_guard_required": True, "formal_writeback_guard_ready": False},
            "formal_writeback_guard_missing",
        ),
        (
            {"source_hash_revalidation_required": True, "source_hash_revalidation_ready": False},
            "source_hash_revalidation_missing",
        ),
        (
            {"review_apply_isolation_required": True, "review_apply_isolation_ready": False},
            "review_apply_isolation_missing",
        ),
        ({"docx_isolation_required": True, "docx_isolation_ready": False}, "docx_isolation_missing"),
        ({"zbid_isolation_required": True, "zbid_isolation_ready": False}, "zbid_isolation_missing"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_docx_zbid_export_formal_review_apply_and_dry_run_requests_are_blocked():
    cases = [
        ({"docx_export_requested": True}, "docx_export_request_blocked"),
        ({"zbid_writeback_requested": True}, "zbid_writeback_request_blocked"),
        ({"output_write_requested": True}, "output_write_request_blocked"),
        ({"formal_generation_requested": True}, "formal_generation_request_blocked"),
        ({"review_apply_requested": True}, "review_apply_request_blocked"),
        ({"export_docx_request_triggered": True}, "export_docx_request_blocked"),
        ({"dry_run_requested": True}, "dry_run_request_blocked"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(**overrides)
        )

        assert validated["dry_run_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_current_stage_formal_flags_are_always_false():
    for status in DRY_RUN_STATUSES:
        validated = validate_fake_dry_run_contract(
            make_fake_dry_run_contract(dry_run_status=status)
        )

        assert_formal_flags_false(validated)


def test_dry_run_guard_is_not_writeback_read_or_write():
    contract = make_fake_dry_run_contract()
    metadata = contract["fake_metadata"]

    assert metadata["dry_run_payload_source"] == "caller_supplied_fake_metadata"
    assert metadata["dry_run_payload_file_read_performed"] is False
    assert metadata["dry_run_candidate_source"] == "caller_supplied_fake_metadata"
    assert metadata["real_source_body_read_performed"] is False
    assert metadata["real_docx_read_performed"] is False
    assert metadata["real_zbid_data_read_performed"] is False
    assert metadata["source_hash_calculated_from_real_body"] is False
    assert metadata["source_section_compared"] is False
    assert metadata["source_write_performed"] is False
    assert metadata["formal_writeback_performed"] is False
    assert metadata["review_apply_performed"] is False
    assert metadata["export_docx_performed"] is False
    assert metadata["zbid_api_called"] is False
    assert metadata["zbid_db_called"] is False
    assert metadata["zbid_writeback_interface_called"] is False
    assert metadata["zbid_writeback_performed"] is False
    assert contract["affected_anchor_refs"] != contract["evidence_anchor_refs"]

    validated = validate_fake_dry_run_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False


def test_fake_dry_run_contract_uses_deterministic_generated_at_and_id():
    first = make_fake_dry_run_contract()
    second = make_fake_dry_run_contract()
    changed = make_fake_dry_run_contract(dry_run_payload_hash="sha256:changed")

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert second["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["dry_run_id"] == second["dry_run_id"]
    assert first["dry_run_id"] != changed["dry_run_id"]

    source = read_this_test_source()
    imported = imported_modules_from_source(source)
    called = called_names_from_source(source)

    assert "datetime" not in imported
    assert "time" not in imported
    assert "uuid" not in imported
    assert "random" not in imported
    assert "now" not in called
    assert "time" not in called
    assert "uuid4" not in called
    assert "random" not in called


def test_fake_dry_run_contract_does_not_write_output_job_export_or_perform_writeback():
    contract = make_fake_dry_run_contract()
    validated = validate_fake_dry_run_contract(contract)
    source = read_this_test_source()
    imported = imported_modules_from_source(source)
    called = called_names_from_source(source)

    assert validated["output_write_allowed"] is False
    assert validated["formal_writeback_allowed"] is False
    assert contract["fake_metadata"]["output_write_performed"] is False
    assert contract["fake_metadata"]["docx_file_generated"] is False
    assert contract["fake_metadata"]["json_artifact_generated"] is False
    assert contract["fake_metadata"]["markdown_artifact_generated"] is False
    assert contract["fake_metadata"]["formal_writeback_performed"] is False
    assert contract["fake_metadata"]["review_apply_performed"] is False
    assert contract["fake_metadata"]["export_docx_performed"] is False
    assert contract["fake_metadata"]["zbid_writeback_performed"] is False
    assert "write_text" not in called
    assert "write_bytes" not in called
    assert "mkdir" not in called
    assert "unlink" not in called
    assert "rmdir" not in called
    assert "rename" not in called
    assert "replace" not in called
    assert "open" not in called
    assert imported.isdisjoint({"requests", "httpx", "zbid"})


def test_formal_writeback_dry_run_contract_schema_imports_do_not_pull_main_chain_or_zbid_modules():
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
        "docx",
        "backend.zhifei_autoplan.orchestrator",
        "backend.zhifei_autoplan.llm_client",
        "backend.zhifei_autoplan.provider",
        "backend.zhifei_autoplan.generation",
        "backend.zhifei_autoplan.export",
        "backend.zhifei_autoplan.review",
        "backend.zhifei_autoplan.zbid",
        "backend.app.routers.actions_bridge",
        "backend.app.routers.export",
        "backend.app.routers.review",
    }

    assert imported.isdisjoint(forbidden_imports)
    assert all(not module.startswith("backend.zhifei_autoplan") for module in imported)
    assert all(not module.startswith("backend.app") for module in imported)
