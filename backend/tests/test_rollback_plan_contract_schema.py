import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "rollback_plan_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "shadow_candidate_id",
    "patch_id",
    "approval_id",
    "diff_preview_id",
    "rollback_plan_status",
    "rollback_scope",
    "rollback_strategy",
    "rollback_operation_type",
    "rollback_target_type",
    "rollback_summary_preview",
    "rollback_operations_preview",
    "source_snapshot_hash",
    "before_text_hash",
    "after_text_preview_hash",
    "patch_operations_preview_hash",
    "diff_preview_hash",
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
    "human_approval_required",
    "human_approval_received",
    "source_hash_revalidation_required",
    "source_hash_revalidation_ready",
    "diff_preview_required",
    "diff_preview_ready",
    "rollback_required",
    "rollback_plan_ready",
    "formal_writeback_guard_required",
    "formal_writeback_guard_ready",
    "generated_at",
    "model_provider",
    "model_name",
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
}

ROLLBACK_PLAN_STATUSES = {
    "not_created",
    "blocked",
    "draft_rollback_shadow_only",
    "ready_for_human_review",
    "approved_rollback_shadow_only",
    "rejected",
    "stale_source_hash",
}

ROLLBACK_SCOPES = {
    "single_section",
    "paragraph_range",
    "anchor_range",
    "metadata_only",
}

ROLLBACK_STRATEGIES = {
    "restore_before_text_hash",
    "reverse_patch_preview",
    "restore_source_snapshot",
    "metadata_only",
    "no_op",
}

ROLLBACK_OPERATION_TYPES = {
    "no_op",
    "restore",
    "reverse_replace",
    "reverse_insert",
    "reverse_delete",
    "reverse_reorder",
    "mixed",
}

ROLLBACK_TARGET_TYPES = {
    "source_section",
    "patch_preview",
    "diff_preview",
    "metadata_only",
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
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def deterministic_rollback_plan_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"rollback-plan-{digest[:16]}"


def make_fake_rollback_plan_contract(**overrides):
    seed = {
        "request_id": "req-rollback-plan-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "diff_preview_id": "diff-preview-only",
        "source_snapshot_hash": "sha256:source-snapshot",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
        "diff_preview_hash": "sha256:diff-preview",
    }
    contract = {
        "contract_version": "0.1",
        "rollback_plan_id": deterministic_rollback_plan_id(seed),
        "request_id": seed["request_id"],
        "source_document_id": seed["source_document_id"],
        "source_section_id": seed["source_section_id"],
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "patch_id": seed["patch_id"],
        "approval_id": seed["approval_id"],
        "diff_preview_id": seed["diff_preview_id"],
        "rollback_plan_status": "approved_rollback_shadow_only",
        "rollback_scope": "single_section",
        "rollback_strategy": "restore_source_snapshot",
        "rollback_operation_type": "restore",
        "rollback_target_type": "source_section",
        "rollback_summary_preview": "Preview-only rollback summary, not an executable rollback.",
        "rollback_operations_preview": [{"op": "restore", "anchor_ref": "section:anchor:1"}],
        "source_snapshot_hash": seed["source_snapshot_hash"],
        "before_text_hash": seed["before_text_hash"],
        "after_text_preview_hash": seed["after_text_preview_hash"],
        "patch_operations_preview_hash": seed["patch_operations_preview_hash"],
        "diff_preview_hash": seed["diff_preview_hash"],
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
        "human_approval_required": True,
        "human_approval_received": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "fake_metadata": {
            "source_section_hash_match": True,
            "rollback_base_hash_match": True,
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    if "rollback_plan_id" not in overrides:
        contract["rollback_plan_id"] = deterministic_rollback_plan_id(
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
                "source_snapshot_hash": contract.get("source_snapshot_hash"),
                "before_text_hash": contract.get("before_text_hash"),
                "after_text_preview_hash": contract.get("after_text_preview_hash"),
                "patch_operations_preview_hash": contract.get("patch_operations_preview_hash"),
                "diff_preview_hash": contract.get("diff_preview_hash"),
            }
        )
    return contract


def validate_fake_rollback_plan_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("rollback_plan_status")
    metadata = contract.get("fake_metadata", {})

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_rollback_plan_contract_fields")
        status = "blocked"

    if contract.get("rollback_plan_status") not in ROLLBACK_PLAN_STATUSES:
        reasons.append("invalid_rollback_plan_status")
        status = "blocked"

    if contract.get("rollback_scope") not in ROLLBACK_SCOPES:
        reasons.append("invalid_rollback_scope")
        status = "blocked"

    if contract.get("rollback_strategy") not in ROLLBACK_STRATEGIES:
        reasons.append("invalid_rollback_strategy")
        status = "blocked"

    if contract.get("rollback_operation_type") not in ROLLBACK_OPERATION_TYPES:
        reasons.append("invalid_rollback_operation_type")
        status = "blocked"

    if contract.get("rollback_target_type") not in ROLLBACK_TARGET_TYPES:
        reasons.append("invalid_rollback_target_type")
        status = "blocked"

    if contract.get("evidence_binding_status") not in EVIDENCE_BINDING_STATUSES:
        reasons.append("invalid_evidence_binding_status")
        status = "blocked"

    if contract.get("generated_at") != DETERMINISTIC_GENERATED_AT:
        reasons.append("generated_at_must_be_deterministic")
        status = "blocked"

    if contract.get("rollback_plan_status") == "approved_rollback_shadow_only":
        reasons.append("rollback_plan_is_not_formal_writeback_permission")

    missing_metadata_fields = {
        "shadow_candidate_id": "missing_shadow_candidate_id",
        "patch_id": "missing_patch_id",
        "approval_id": "missing_approval_id",
        "diff_preview_id": "missing_diff_preview_id",
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

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_create_rollback_plan")
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

    preview_values = {
        str(contract.get("rollback_summary_preview")),
        str(contract.get("rollback_operations_preview")),
    } - {""}
    if preview_values and any(str(ref) in preview_values for ref in evidence_refs):
        reasons.append("rollback_plan_cannot_be_evidence")
        status = "blocked"

    if not contract.get("source_section_hash"):
        reasons.append("missing_source_section_hash")
        status = "blocked"

    if metadata.get("source_section_hash_match") is False:
        reasons.append("source_section_hash_mismatch")
        status = "stale_source_hash"

    if metadata.get("rollback_base_hash_match") is False:
        reasons.append("rollback_base_hash_mismatch")
        status = "stale_source_hash"

    if contract.get("source_hash_revalidation_required") and not contract.get("source_hash_revalidation_ready"):
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"

    required_hashes = {
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
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

    if contract.get("formal_writeback_guard_required") and not contract.get("formal_writeback_guard_ready"):
        reasons.append("formal_writeback_guard_missing")
        status = "blocked"

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
    validated["rollback_plan_status"] = status
    validated["blocked_reasons"] = reasons
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        validated[flag] = False
    return validated


def assert_formal_flags_false(contract):
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        assert contract[flag] is False


def read_this_test_source():
    return Path(__file__).read_text(encoding="utf-8")


def test_rollback_plan_contract_required_fields_are_explicit():
    contract = make_fake_rollback_plan_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_rollback_plan_status_enums_are_locked():
    assert ROLLBACK_PLAN_STATUSES == {
        "not_created",
        "blocked",
        "draft_rollback_shadow_only",
        "ready_for_human_review",
        "approved_rollback_shadow_only",
        "rejected",
        "stale_source_hash",
    }


def test_rollback_scope_strategy_operation_and_target_enums_are_locked():
    assert ROLLBACK_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert ROLLBACK_STRATEGIES == {
        "restore_before_text_hash",
        "reverse_patch_preview",
        "restore_source_snapshot",
        "metadata_only",
        "no_op",
    }
    assert ROLLBACK_OPERATION_TYPES == {
        "no_op",
        "restore",
        "reverse_replace",
        "reverse_insert",
        "reverse_delete",
        "reverse_reorder",
        "mixed",
    }
    assert ROLLBACK_TARGET_TYPES == {
        "source_section",
        "patch_preview",
        "diff_preview",
        "metadata_only",
    }


def test_approved_rollback_shadow_only_is_not_formal_writeback_permission():
    contract = make_fake_rollback_plan_contract(
        rollback_plan_status="approved_rollback_shadow_only",
    )

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "rollback_plan_is_not_formal_writeback_permission" in validated["blocked_reasons"]


def test_rollback_plan_cannot_be_evidence():
    rollback_summary = "rollback summary is not evidence"
    rollback_ops = [{"op": "restore", "text": "rollback op is not evidence"}]
    cases = [
        (
            {"evidence_binding_status": "rollback_plan_only_blocked"},
            "rollback_plan_cannot_be_evidence",
        ),
        (
            {
                "rollback_summary_preview": rollback_summary,
                "evidence_anchor_refs": [rollback_summary],
            },
            "rollback_plan_cannot_be_evidence",
        ),
        (
            {
                "rollback_operations_preview": rollback_ops,
                "evidence_anchor_refs": [str(rollback_ops)],
            },
            "rollback_plan_cannot_be_evidence",
        ),
    ]

    for overrides, reason in cases:
        validated = validate_fake_rollback_plan_contract(make_fake_rollback_plan_contract(**overrides))

        assert validated["formal_writeback_allowed"] is False
        assert validated["rollback_plan_status"] != "ready_for_human_review"
        assert validated["rollback_plan_status"] != "approved_rollback_shadow_only"
        assert reason in validated["blocked_reasons"]


def test_missing_shadow_patch_approval_or_diff_metadata_blocks_rollback_plan():
    cases = [
        ({"shadow_candidate_id": ""}, "missing_shadow_candidate_id"),
        ({"patch_id": ""}, "missing_patch_id"),
        ({"approval_id": ""}, "missing_approval_id"),
        ({"diff_preview_id": ""}, "missing_diff_preview_id"),
        ({"shadow_candidate_status": "blocked"}, "shadow_candidate_prerequisite_not_satisfied"),
        ({"shadow_candidate_status": "not_created"}, "shadow_candidate_prerequisite_not_satisfied"),
        ({"patch_status": "blocked"}, "patch_prerequisite_not_satisfied"),
        ({"patch_status": "not_created"}, "patch_prerequisite_not_satisfied"),
        ({"approval_status": "pending_human_review"}, "human_approval_not_received"),
        ({"diff_preview_status": "blocked"}, "diff_preview_prerequisite_not_satisfied"),
        ({"diff_preview_status": "not_created"}, "diff_preview_prerequisite_not_satisfied"),
        ({"diff_preview_status": "stale_source_hash"}, "diff_preview_prerequisite_not_satisfied"),
    ]

    for overrides, reason in cases:
        validated = validate_fake_rollback_plan_contract(make_fake_rollback_plan_contract(**overrides))

        assert validated["rollback_plan_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_thinking_only_fallback_blocks_rollback_plan():
    contract = make_fake_rollback_plan_contract(response_mode="thinking_only_fallback")

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["rollback_plan_status"] in {"blocked", "not_created"}
    assert "thinking_only_fallback_cannot_create_rollback_plan" in validated["blocked_reasons"]
    assert_formal_flags_false(validated)


def test_missing_evidence_anchor_blocks_rollback_plan():
    cases = [
        {"evidence_anchor_status": "missing"},
        {"evidence_anchor_refs": []},
    ]

    for overrides in cases:
        validated = validate_fake_rollback_plan_contract(make_fake_rollback_plan_contract(**overrides))

        assert validated["rollback_plan_status"] == "blocked"
        assert "missing_evidence_anchor" in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_advisory_shadow_patch_and_diff_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
        "diff_preview_only_blocked": "diff_preview_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        validated = validate_fake_rollback_plan_contract(
            make_fake_rollback_plan_contract(evidence_binding_status=binding_status)
        )

        assert validated["rollback_plan_status"] != "ready_for_human_review"
        assert validated["rollback_plan_status"] != "approved_rollback_shadow_only"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_or_stale_source_hash_blocks_rollback_plan():
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
            {"fake_metadata": {"source_section_hash_match": False}},
            "source_section_hash_mismatch",
            "stale_source_hash",
        ),
        (
            {"fake_metadata": {"rollback_base_hash_match": False}},
            "rollback_base_hash_mismatch",
            "stale_source_hash",
        ),
    ]

    for overrides, reason, expected_status in cases:
        validated = validate_fake_rollback_plan_contract(make_fake_rollback_plan_contract(**overrides))

        assert validated["rollback_plan_status"] == expected_status
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_missing_required_rollback_hashes_block_rollback_plan():
    cases = {
        "source_snapshot_hash": "missing_source_snapshot_hash",
        "before_text_hash": "missing_before_text_hash",
        "after_text_preview_hash": "missing_after_text_preview_hash",
        "patch_operations_preview_hash": "missing_patch_operations_preview_hash",
        "diff_preview_hash": "missing_diff_preview_hash",
    }

    for field, reason in cases.items():
        validated = validate_fake_rollback_plan_contract(
            make_fake_rollback_plan_contract(**{field: ""})
        )

        assert validated["rollback_plan_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_missing_human_approval_blocks_rollback_plan():
    contract = make_fake_rollback_plan_contract(
        human_approval_required=True,
        human_approval_received=False,
    )

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["rollback_plan_status"] == "blocked"
    assert "missing_human_approval" in validated["blocked_reasons"]
    assert_formal_flags_false(validated)


def test_missing_diff_preview_readiness_blocks_rollback_plan():
    contract = make_fake_rollback_plan_contract(
        diff_preview_required=True,
        diff_preview_ready=False,
    )

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["rollback_plan_status"] == "blocked"
    assert "diff_preview_missing" in validated["blocked_reasons"]
    assert_formal_flags_false(validated)


def test_missing_formal_writeback_guard_blocks_rollback_plan():
    contract = make_fake_rollback_plan_contract(
        formal_writeback_guard_required=True,
        formal_writeback_guard_ready=False,
    )

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "formal_writeback_guard_missing" in validated["blocked_reasons"]


def test_docx_zbid_export_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
    }

    for request_type, reason in cases.items():
        contract = make_fake_rollback_plan_contract(
            fake_metadata={"request_type": request_type}
        )
        validated = validate_fake_rollback_plan_contract(contract)

        assert validated["rollback_plan_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_current_stage_formal_flags_are_always_false():
    for status in ROLLBACK_PLAN_STATUSES:
        contract = make_fake_rollback_plan_contract(rollback_plan_status=status)

        validated = validate_fake_rollback_plan_contract(contract)

        assert_formal_flags_false(validated)


def test_rollback_plan_is_not_source_write():
    contract = make_fake_rollback_plan_contract(
        affected_anchor_refs=["section:anchor:1"],
        evidence_anchor_refs=["tender:section:1"],
        fake_metadata={
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
        },
    )

    validated = validate_fake_rollback_plan_contract(contract)

    assert validated["rollback_summary_preview"] != validated["source_section_hash"]
    assert validated["rollback_operations_preview"] != validated["source_section_hash"]
    assert validated["affected_anchor_refs"] != validated["evidence_anchor_refs"]
    assert validated["fake_metadata"]["source_write_performed"] is False
    assert validated["fake_metadata"]["review_apply_performed"] is False
    assert validated["fake_metadata"]["output_write_performed"] is False
    assert_formal_flags_false(validated)


def test_fake_rollback_plan_contract_uses_deterministic_generated_at_and_id():
    first = make_fake_rollback_plan_contract()
    second = make_fake_rollback_plan_contract()
    different = make_fake_rollback_plan_contract(source_snapshot_hash="sha256:other-snapshot")

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["rollback_plan_id"] == second["rollback_plan_id"]
    assert first["rollback_plan_id"].startswith("rollback-plan-")
    assert first["rollback_plan_id"] != different["rollback_plan_id"]

    tree = ast.parse(read_this_test_source())
    forbidden_calls = {
        ("datetime", "now"),
        ("time", "time"),
        ("uuid", "uuid4"),
        ("random", "random"),
        ("random", "randint"),
        ("random", "choice"),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                assert (node.func.value.id, node.func.attr) not in forbidden_calls


def test_fake_rollback_plan_contract_does_not_write_output_job_export():
    contract = make_fake_rollback_plan_contract(
        fake_metadata={
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
            "request_type": "output_write",
        },
    )

    validated = validate_fake_rollback_plan_contract(contract)
    tree = ast.parse(read_this_test_source())
    write_calls = {"write_text", "write_bytes", "open", "mkdir", "touch"}

    assert validated["fake_metadata"]["output_write_performed"] is False
    assert "output_write_request_blocked" in validated["blocked_reasons"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in write_calls
            elif isinstance(node.func, ast.Name):
                assert node.func.id not in write_calls


def test_rollback_plan_contract_schema_imports_do_not_pull_main_chain_modules():
    source = read_this_test_source()
    tree = ast.parse(source)
    imported_modules = set()
    forbidden_modules = {
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
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.lower())
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add((node.module or "").lower())

    assert imported_modules.isdisjoint(forbidden_modules)
