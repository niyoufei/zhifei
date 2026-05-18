import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "approval_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "shadow_candidate_id",
    "patch_id",
    "approval_status",
    "approval_scope",
    "approval_decision",
    "approval_mode",
    "approver_role",
    "approver_id_placeholder",
    "approved_at",
    "approval_reason",
    "approval_comment",
    "approval_expires_at",
    "approval_audit_required",
    "approval_audit_ready",
    "evidence_anchor_status",
    "evidence_anchor_refs",
    "evidence_binding_status",
    "response_mode",
    "input_risk_level",
    "advisory_quality_gate_status",
    "readiness_status",
    "shadow_candidate_status",
    "patch_status",
    "diff_preview_required",
    "diff_preview_ready",
    "rollback_required",
    "rollback_plan_ready",
    "source_hash_revalidation_required",
    "source_hash_revalidation_ready",
    "formal_writeback_guard_required",
    "formal_writeback_guard_ready",
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
}

APPROVAL_STATUSES = {
    "not_requested",
    "blocked",
    "pending_human_review",
    "approved_shadow_only",
    "rejected",
    "expired",
    "revoked",
}

APPROVAL_DECISIONS = {
    "none",
    "approve_shadow_only",
    "reject",
    "request_revision",
    "revoke",
}

APPROVAL_SCOPES = {
    "shadow_candidate_only",
    "patch_preview_only",
    "single_section_candidate",
    "metadata_only",
}

APPROVAL_MODES = {
    "manual_required",
    "manual_received",
    "disabled_current_stage",
}

CURRENT_STAGE_FALSE_FLAGS = {
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

DETERMINISTIC_APPROVED_AT = "2026-01-01T00:00:00Z"
DETERMINISTIC_APPROVAL_EXPIRES_AT = "2026-01-02T00:00:00Z"
FAKE_APPROVER_PLACEHOLDER = "manual-reviewer-placeholder"


def deterministic_approval_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"approval-{digest[:16]}"


def make_fake_human_approval_contract(**overrides):
    seed = {
        "request_id": "req-human-approval-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
    }
    contract = {
        "contract_version": "0.1",
        "approval_id": deterministic_approval_id(seed),
        "request_id": seed["request_id"],
        "source_document_id": seed["source_document_id"],
        "source_section_id": seed["source_section_id"],
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "patch_id": seed["patch_id"],
        "approval_status": "approved_shadow_only",
        "approval_scope": "patch_preview_only",
        "approval_decision": "approve_shadow_only",
        "approval_mode": "manual_received",
        "approver_role": "reviewer",
        "approver_id_placeholder": FAKE_APPROVER_PLACEHOLDER,
        "approved_at": DETERMINISTIC_APPROVED_AT,
        "approval_reason": "fake approval metadata for contract tests",
        "approval_comment": "approval is not writeback permission",
        "approval_expires_at": DETERMINISTIC_APPROVAL_EXPIRES_AT,
        "approval_audit_required": True,
        "approval_audit_ready": True,
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "future_ready_for_shadow_candidate",
        "shadow_candidate_status": "draft_shadow_only",
        "patch_status": "draft_patch_shadow_only",
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
        "formal_writeback_guard_required": True,
        "formal_writeback_guard_ready": True,
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "fake_metadata": {
            "request_type": "preview_only",
            "source_section_hash_match": True,
            "output_write_performed": False,
        },
    }
    contract.update(overrides)
    if "approval_id" not in overrides:
        contract["approval_id"] = deterministic_approval_id(
            {
                "request_id": contract.get("request_id"),
                "source_document_id": contract.get("source_document_id"),
                "source_section_id": contract.get("source_section_id"),
                "source_section_hash": contract.get("source_section_hash"),
                "source_section_version": contract.get("source_section_version"),
                "shadow_candidate_id": contract.get("shadow_candidate_id"),
                "patch_id": contract.get("patch_id"),
            }
        )
    return contract


def validate_fake_human_approval_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("approval_status")

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_approval_contract_fields")
        status = "blocked"

    if contract.get("approval_status") not in APPROVAL_STATUSES:
        reasons.append("invalid_approval_status")
        status = "blocked"

    if contract.get("approval_decision") not in APPROVAL_DECISIONS:
        reasons.append("invalid_approval_decision")
        status = "blocked"

    if contract.get("approval_scope") not in APPROVAL_SCOPES:
        reasons.append("invalid_approval_scope")
        status = "blocked"

    if contract.get("approval_mode") not in APPROVAL_MODES:
        reasons.append("invalid_approval_mode")
        status = "blocked"

    if contract.get("approval_status") == "approved_shadow_only":
        reasons.append("approval_is_not_formal_writeback_permission")
    elif contract.get("approval_status") in {"not_requested", "blocked", "pending_human_review", "rejected"}:
        reasons.append(f"approval_status_{contract.get('approval_status')}_not_writeback_allowed")
        status = "blocked"
    elif contract.get("approval_status") in {"expired", "revoked"}:
        reasons.append(f"approval_{contract.get('approval_status')}_not_writeback_allowed")
        status = "blocked"

    if contract.get("evidence_anchor_status") == "missing":
        reasons.append("missing_evidence_anchor")
        status = "blocked"

    if not contract.get("evidence_anchor_refs"):
        reasons.append("missing_evidence_anchor")
        status = "blocked"

    evidence_block_reasons = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }
    binding_status = contract.get("evidence_binding_status")
    if binding_status in evidence_block_reasons:
        reasons.append(evidence_block_reasons[binding_status])
        status = "blocked"

    if not contract.get("source_section_hash"):
        reasons.append("missing_source_section_hash")
        status = "blocked"

    metadata = contract.get("fake_metadata", {})
    if metadata.get("source_section_hash_match") is False:
        reasons.append("source_section_hash_mismatch")
        status = "blocked"

    if contract.get("source_hash_revalidation_required") and not contract.get("source_hash_revalidation_ready"):
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"

    if contract.get("diff_preview_required") and not contract.get("diff_preview_ready"):
        reasons.append("diff_preview_missing")
        status = "blocked"

    if contract.get("rollback_required") and not contract.get("rollback_plan_ready"):
        reasons.append("rollback_plan_missing")
        status = "blocked"

    if contract.get("formal_writeback_guard_required") and not contract.get("formal_writeback_guard_ready"):
        reasons.append("formal_writeback_guard_missing")
        status = "blocked"

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_not_writeback_capable")
        status = "blocked"

    if contract.get("shadow_candidate_status") in {"blocked", "not_created"}:
        reasons.append("shadow_candidate_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("patch_status") in {"blocked", "not_created"}:
        reasons.append("patch_prerequisite_not_satisfied")
        status = "blocked"

    if contract.get("approval_audit_required"):
        audit_fields = {
            "approval_id",
            "request_id",
            "source_document_id",
            "source_section_id",
            "source_section_hash",
            "source_section_version",
            "shadow_candidate_id",
            "patch_id",
            "approval_status",
            "approval_decision",
            "approval_scope",
            "approver_role",
        }
        if any(not contract.get(field) for field in audit_fields) or not contract.get("approval_audit_ready"):
            reasons.append("approval_audit_fields_missing")
            status = "blocked"

    if not is_fake_approver_placeholder(contract.get("approver_id_placeholder")):
        reasons.append("real_personal_identity_not_allowed")
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
    validated["approval_status"] = status
    validated["blocked_reasons"] = reasons
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        validated[flag] = False
    return validated


def is_fake_approver_placeholder(value):
    return value in {"", FAKE_APPROVER_PLACEHOLDER, "reviewer-placeholder"}


def output_job_export_snapshot():
    repo_root = Path(__file__).resolve().parents[2]
    snapshot = {}
    for dirname in ("output", "job", "export"):
        path = repo_root / dirname
        if path.exists():
            snapshot[dirname] = sorted(child.name for child in path.iterdir())
        else:
            snapshot[dirname] = None
    return snapshot


def assert_formal_flags_false(contract):
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        assert contract[flag] is False


def test_human_approval_contract_required_fields_are_explicit():
    contract = make_fake_human_approval_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_human_approval_status_enums_are_locked():
    assert APPROVAL_STATUSES == {
        "not_requested",
        "blocked",
        "pending_human_review",
        "approved_shadow_only",
        "rejected",
        "expired",
        "revoked",
    }


def test_approval_decision_scope_and_mode_enums_are_locked():
    assert APPROVAL_DECISIONS == {
        "none",
        "approve_shadow_only",
        "reject",
        "request_revision",
        "revoke",
    }
    assert APPROVAL_SCOPES == {
        "shadow_candidate_only",
        "patch_preview_only",
        "single_section_candidate",
        "metadata_only",
    }
    assert APPROVAL_MODES == {
        "manual_required",
        "manual_received",
        "disabled_current_stage",
    }


def test_approval_is_not_formal_writeback_permission():
    contract = make_fake_human_approval_contract(
        approval_status="approved_shadow_only",
        approval_decision="approve_shadow_only",
    )

    validated = validate_fake_human_approval_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "approval_is_not_formal_writeback_permission" in validated["blocked_reasons"]


def test_missing_or_nonapproved_approval_blocks_writeback():
    for status in {"not_requested", "blocked", "pending_human_review", "rejected", "expired", "revoked"}:
        contract = make_fake_human_approval_contract(approval_status=status)
        validated = validate_fake_human_approval_contract(contract)

        assert_formal_flags_false(validated)


def test_approval_cannot_replace_evidence_anchor():
    cases = [
        (
            make_fake_human_approval_contract(evidence_anchor_status="missing"),
            "missing_evidence_anchor",
        ),
        (
            make_fake_human_approval_contract(evidence_anchor_refs=[]),
            "missing_evidence_anchor",
        ),
        (
            make_fake_human_approval_contract(evidence_binding_status="generated_advisory_only_blocked"),
            "generated_advisory_cannot_be_evidence",
        ),
        (
            make_fake_human_approval_contract(evidence_binding_status="shadow_candidate_only_blocked"),
            "shadow_candidate_cannot_be_evidence",
        ),
        (
            make_fake_human_approval_contract(evidence_binding_status="patch_preview_only_blocked"),
            "patch_preview_cannot_be_evidence",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_human_approval_contract(contract)

        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_approval_cannot_replace_source_hash_revalidation():
    cases = [
        (
            make_fake_human_approval_contract(source_section_hash=""),
            "missing_source_section_hash",
        ),
        (
            make_fake_human_approval_contract(
                source_hash_revalidation_required=True,
                source_hash_revalidation_ready=False,
            ),
            "source_hash_revalidation_missing",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_human_approval_contract(contract)

        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_approval_cannot_replace_diff_preview():
    contract = make_fake_human_approval_contract(
        diff_preview_required=True,
        diff_preview_ready=False,
    )

    validated = validate_fake_human_approval_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "diff_preview_missing" in validated["blocked_reasons"]


def test_approval_cannot_replace_rollback_plan():
    contract = make_fake_human_approval_contract(
        rollback_required=True,
        rollback_plan_ready=False,
    )

    validated = validate_fake_human_approval_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "rollback_plan_missing" in validated["blocked_reasons"]


def test_approval_cannot_replace_formal_writeback_guard():
    contract = make_fake_human_approval_contract(
        formal_writeback_guard_required=True,
        formal_writeback_guard_ready=False,
    )

    validated = validate_fake_human_approval_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "formal_writeback_guard_missing" in validated["blocked_reasons"]


def test_thinking_only_fallback_blocks_approval_writeback():
    contract = make_fake_human_approval_contract(response_mode="thinking_only_fallback")

    validated = validate_fake_human_approval_contract(contract)

    assert validated["approval_status"] != "formal_writeback_allowed"
    assert validated["formal_writeback_allowed"] is False
    assert "thinking_only_fallback_not_writeback_capable" in validated["blocked_reasons"]


def test_blocked_shadow_candidate_or_patch_blocks_approval_writeback():
    cases = [
        (
            make_fake_human_approval_contract(shadow_candidate_status="blocked"),
            "shadow_candidate_prerequisite_not_satisfied",
        ),
        (
            make_fake_human_approval_contract(shadow_candidate_status="not_created"),
            "shadow_candidate_prerequisite_not_satisfied",
        ),
        (
            make_fake_human_approval_contract(patch_status="blocked"),
            "patch_prerequisite_not_satisfied",
        ),
        (
            make_fake_human_approval_contract(patch_status="not_created"),
            "patch_prerequisite_not_satisfied",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_human_approval_contract(contract)

        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_expired_or_revoked_approval_blocks_writeback():
    cases = {
        "expired": "approval_expired_not_writeback_allowed",
        "revoked": "approval_revoked_not_writeback_allowed",
    }
    for status, reason in cases.items():
        contract = make_fake_human_approval_contract(approval_status=status)
        validated = validate_fake_human_approval_contract(contract)

        assert_formal_flags_false(validated)
        assert reason in validated["blocked_reasons"]


def test_missing_approval_audit_fields_blocks_contract():
    required_audit_fields = [
        "approval_id",
        "request_id",
        "source_document_id",
        "source_section_id",
        "source_section_hash",
        "source_section_version",
        "shadow_candidate_id",
        "patch_id",
        "approval_status",
        "approval_decision",
        "approval_scope",
        "approver_role",
    ]

    for field in required_audit_fields:
        contract = make_fake_human_approval_contract(**{field: ""})
        validated = validate_fake_human_approval_contract(contract)

        assert validated["approval_status"] == "blocked"
        assert "approval_audit_fields_missing" in validated["blocked_reasons"]


def test_approver_placeholder_does_not_store_real_identity():
    assert is_fake_approver_placeholder(FAKE_APPROVER_PLACEHOLDER)
    for value in {"person@example.com", "13812345678", "110101199003078888", "Zhang San"}:
        contract = make_fake_human_approval_contract(approver_id_placeholder=value)
        validated = validate_fake_human_approval_contract(contract)

        assert validated["approval_status"] == "blocked"
        assert "real_personal_identity_not_allowed" in validated["blocked_reasons"]


def test_docx_zbid_export_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
    }

    for request_type, reason in cases.items():
        contract = make_fake_human_approval_contract(
            fake_metadata={
                "request_type": request_type,
                "source_section_hash_match": True,
                "output_write_performed": False,
            }
        )
        validated = validate_fake_human_approval_contract(contract)

        assert validated["approval_status"] == "blocked"
        assert_formal_flags_false(validated)
        assert reason in validated["blocked_reasons"]


def test_current_stage_formal_flags_are_always_false():
    for status in APPROVAL_STATUSES:
        contract = make_fake_human_approval_contract(
            approval_status=status,
            formal_writeback_allowed=True,
            docx_export_allowed=True,
            zbid_writeback_allowed=True,
            output_write_allowed=True,
        )

        validated = validate_fake_human_approval_contract(contract)

        assert_formal_flags_false(validated)


def test_fake_approval_contract_uses_deterministic_timestamps_and_id():
    first = make_fake_human_approval_contract()
    second = make_fake_human_approval_contract()
    different = make_fake_human_approval_contract(source_section_hash="sha256:other")

    assert first["approved_at"] == DETERMINISTIC_APPROVED_AT
    assert first["approval_expires_at"] == DETERMINISTIC_APPROVAL_EXPIRES_AT
    assert first["approval_id"] == second["approval_id"]
    assert first["approval_id"].startswith("approval-")
    assert first["approval_id"] != different["approval_id"]


def test_fake_approval_contract_does_not_write_output_job_export():
    before = output_job_export_snapshot()

    contract = make_fake_human_approval_contract(
        fake_metadata={
            "request_type": "output_write",
            "source_section_hash_match": True,
            "output_write_performed": False,
        }
    )
    validate_fake_human_approval_contract(contract)

    after = output_job_export_snapshot()
    assert after == before


def test_approval_contract_schema_imports_do_not_pull_main_chain_modules():
    forbidden_import_roots = {
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
    }
    forbidden_source_tokens = {
        ".".join(("datetime", "now")),
        ".".join(("time", "time")),
        ".".join(("uuid", "uuid4")),
        ".".join(("random", "")),
    }
    source = Path(__file__).read_text()
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module)

    for forbidden in forbidden_import_roots:
        assert forbidden not in imported_roots
    for forbidden in forbidden_source_tokens:
        assert forbidden not in source
