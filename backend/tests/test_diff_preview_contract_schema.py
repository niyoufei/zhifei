import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "diff_preview_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "shadow_candidate_id",
    "patch_id",
    "approval_id",
    "diff_preview_status",
    "diff_scope",
    "diff_format",
    "diff_operation_type",
    "diff_summary_preview",
    "diff_operations_preview",
    "before_text_hash",
    "after_text_preview_hash",
    "patch_operations_preview_hash",
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
    "human_approval_required",
    "human_approval_received",
    "source_hash_revalidation_required",
    "source_hash_revalidation_ready",
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

DIFF_PREVIEW_STATUSES = {
    "not_created",
    "blocked",
    "draft_diff_shadow_only",
    "ready_for_human_review",
    "approved_diff_shadow_only",
    "rejected",
    "stale_source_hash",
}

DIFF_SCOPES = {
    "single_section",
    "paragraph_range",
    "anchor_range",
    "metadata_only",
}

DIFF_FORMATS = {
    "text_diff_preview",
    "structured_diff_preview",
    "metadata_only",
}

DIFF_OPERATION_TYPES = {
    "no_op",
    "replace",
    "insert",
    "delete",
    "reorder",
    "mixed",
}

EVIDENCE_BINDING_STATUSES = {
    "missing",
    "bound_to_user_provided_evidence",
    "bound_to_source_verified_evidence",
    "generated_advisory_only_blocked",
    "shadow_candidate_only_blocked",
    "patch_preview_only_blocked",
    "diff_preview_only_blocked",
}

CURRENT_STAGE_FALSE_FLAGS = {
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def deterministic_diff_preview_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"diff-preview-{digest[:16]}"


def make_fake_diff_preview_contract(**overrides):
    seed = {
        "request_id": "req-diff-preview-001",
        "source_document_id": "doc-preview-only",
        "source_section_id": "section-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "patch_id": "patch-preview-only",
        "approval_id": "approval-preview-only",
        "before_text_hash": "sha256:before-text",
        "after_text_preview_hash": "sha256:after-preview",
        "patch_operations_preview_hash": "sha256:patch-ops-preview",
    }
    contract = {
        "contract_version": "0.1",
        "diff_preview_id": deterministic_diff_preview_id(seed),
        "request_id": seed["request_id"],
        "source_document_id": seed["source_document_id"],
        "source_section_id": seed["source_section_id"],
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "patch_id": seed["patch_id"],
        "approval_id": seed["approval_id"],
        "diff_preview_status": "approved_diff_shadow_only",
        "diff_scope": "single_section",
        "diff_format": "structured_diff_preview",
        "diff_operation_type": "replace",
        "diff_summary_preview": "Preview-only diff summary, not formal content.",
        "diff_operations_preview": [{"op": "replace", "anchor_ref": "section:anchor:1"}],
        "before_text_hash": seed["before_text_hash"],
        "after_text_preview_hash": seed["after_text_preview_hash"],
        "patch_operations_preview_hash": seed["patch_operations_preview_hash"],
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
        "human_approval_required": True,
        "human_approval_received": True,
        "source_hash_revalidation_required": True,
        "source_hash_revalidation_ready": True,
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
            "diff_base_hash_match": True,
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    if "diff_preview_id" not in overrides:
        contract["diff_preview_id"] = deterministic_diff_preview_id(
            {
                "request_id": contract.get("request_id"),
                "source_document_id": contract.get("source_document_id"),
                "source_section_id": contract.get("source_section_id"),
                "source_section_hash": contract.get("source_section_hash"),
                "source_section_version": contract.get("source_section_version"),
                "shadow_candidate_id": contract.get("shadow_candidate_id"),
                "patch_id": contract.get("patch_id"),
                "approval_id": contract.get("approval_id"),
                "before_text_hash": contract.get("before_text_hash"),
                "after_text_preview_hash": contract.get("after_text_preview_hash"),
                "patch_operations_preview_hash": contract.get("patch_operations_preview_hash"),
            }
        )
    return contract


def validate_fake_diff_preview_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("diff_preview_status")
    metadata = contract.get("fake_metadata", {})

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_diff_preview_contract_fields")
        status = "blocked"

    if contract.get("diff_preview_status") not in DIFF_PREVIEW_STATUSES:
        reasons.append("invalid_diff_preview_status")
        status = "blocked"

    if contract.get("diff_scope") not in DIFF_SCOPES:
        reasons.append("invalid_diff_scope")
        status = "blocked"

    if contract.get("diff_format") not in DIFF_FORMATS:
        reasons.append("invalid_diff_format")
        status = "blocked"

    if contract.get("diff_operation_type") not in DIFF_OPERATION_TYPES:
        reasons.append("invalid_diff_operation_type")
        status = "blocked"

    if contract.get("evidence_binding_status") not in EVIDENCE_BINDING_STATUSES:
        reasons.append("invalid_evidence_binding_status")
        status = "blocked"

    if contract.get("generated_at") != DETERMINISTIC_GENERATED_AT:
        reasons.append("generated_at_must_be_deterministic")
        status = "blocked"

    if contract.get("diff_preview_status") == "approved_diff_shadow_only":
        reasons.append("diff_preview_is_not_formal_writeback_permission")

    if not contract.get("shadow_candidate_id"):
        reasons.append("missing_shadow_candidate_id")
        status = "blocked"

    if not contract.get("patch_id"):
        reasons.append("missing_patch_id")
        status = "blocked"

    if not contract.get("approval_id"):
        reasons.append("missing_approval_id")
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

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_create_diff_preview")
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
    }
    binding_status = contract.get("evidence_binding_status")
    if binding_status in binding_block_reasons:
        reasons.append(binding_block_reasons[binding_status])
        status = "blocked"

    preview_values = {
        str(contract.get("diff_summary_preview")),
        str(contract.get("diff_operations_preview")),
    } - {""}
    if preview_values and any(str(ref) in preview_values for ref in evidence_refs):
        reasons.append("diff_preview_cannot_be_evidence")
        status = "blocked"

    if not contract.get("source_section_hash"):
        reasons.append("missing_source_section_hash")
        status = "blocked"

    if metadata.get("source_section_hash_match") is False:
        reasons.append("source_section_hash_mismatch")
        status = "stale_source_hash"

    if metadata.get("diff_base_hash_match") is False:
        reasons.append("stale_source_hash")
        status = "stale_source_hash"

    if contract.get("source_hash_revalidation_required") and not contract.get("source_hash_revalidation_ready"):
        reasons.append("source_hash_revalidation_missing")
        status = "blocked"

    if not contract.get("before_text_hash"):
        reasons.append("missing_before_text_hash")
        status = "blocked"

    if not contract.get("after_text_preview_hash"):
        reasons.append("missing_after_text_preview_hash")
        status = "blocked"

    if not contract.get("patch_operations_preview_hash"):
        reasons.append("missing_patch_operations_preview_hash")
        status = "blocked"

    if contract.get("human_approval_required") and not contract.get("human_approval_received"):
        reasons.append("missing_human_approval")
        status = "blocked"

    if contract.get("rollback_required") and not contract.get("rollback_plan_ready"):
        reasons.append("rollback_plan_missing")
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
    validated["diff_preview_status"] = status
    validated["blocked_reasons"] = reasons
    for flag in CURRENT_STAGE_FALSE_FLAGS:
        validated[flag] = False
    return validated


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


def test_diff_preview_contract_required_fields_are_explicit():
    contract = make_fake_diff_preview_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_diff_preview_status_enums_are_locked():
    assert DIFF_PREVIEW_STATUSES == {
        "not_created",
        "blocked",
        "draft_diff_shadow_only",
        "ready_for_human_review",
        "approved_diff_shadow_only",
        "rejected",
        "stale_source_hash",
    }


def test_diff_scope_format_and_operation_enums_are_locked():
    assert DIFF_SCOPES == {
        "single_section",
        "paragraph_range",
        "anchor_range",
        "metadata_only",
    }
    assert DIFF_FORMATS == {
        "text_diff_preview",
        "structured_diff_preview",
        "metadata_only",
    }
    assert DIFF_OPERATION_TYPES == {
        "no_op",
        "replace",
        "insert",
        "delete",
        "reorder",
        "mixed",
    }


def test_approved_diff_shadow_only_is_not_formal_writeback_permission():
    contract = make_fake_diff_preview_contract(
        diff_preview_status="approved_diff_shadow_only",
    )

    validated = validate_fake_diff_preview_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "diff_preview_is_not_formal_writeback_permission" in validated["blocked_reasons"]


def test_diff_preview_cannot_be_evidence():
    diff_summary = "diff summary preview is not evidence"
    diff_ops = [{"op": "replace", "text": "diff ops preview is not evidence"}]
    cases = [
        (
            make_fake_diff_preview_contract(evidence_binding_status="diff_preview_only_blocked"),
            "diff_preview_cannot_be_evidence",
        ),
        (
            make_fake_diff_preview_contract(
                diff_summary_preview=diff_summary,
                evidence_anchor_refs=[diff_summary],
            ),
            "diff_preview_cannot_be_evidence",
        ),
        (
            make_fake_diff_preview_contract(
                diff_operations_preview=diff_ops,
                evidence_anchor_refs=[str(diff_ops)],
            ),
            "diff_preview_cannot_be_evidence",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["formal_writeback_allowed"] is False
        assert validated["diff_preview_status"] != "approved_diff_shadow_only"
        assert reason in validated["blocked_reasons"]


def test_missing_shadow_patch_or_approval_metadata_blocks_diff_preview():
    cases = [
        (
            make_fake_diff_preview_contract(shadow_candidate_id=""),
            "missing_shadow_candidate_id",
        ),
        (
            make_fake_diff_preview_contract(patch_id=""),
            "missing_patch_id",
        ),
        (
            make_fake_diff_preview_contract(approval_id=""),
            "missing_approval_id",
        ),
        (
            make_fake_diff_preview_contract(shadow_candidate_status="blocked"),
            "shadow_candidate_prerequisite_not_satisfied",
        ),
        (
            make_fake_diff_preview_contract(shadow_candidate_status="not_created"),
            "shadow_candidate_prerequisite_not_satisfied",
        ),
        (
            make_fake_diff_preview_contract(patch_status="blocked"),
            "patch_prerequisite_not_satisfied",
        ),
        (
            make_fake_diff_preview_contract(patch_status="not_created"),
            "patch_prerequisite_not_satisfied",
        ),
        (
            make_fake_diff_preview_contract(approval_status="pending_human_review"),
            "human_approval_not_received",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] == "blocked"
        assert reason in validated["blocked_reasons"]
        assert_formal_flags_false(validated)


def test_thinking_only_fallback_blocks_diff_preview():
    contract = make_fake_diff_preview_contract(response_mode="thinking_only_fallback")

    validated = validate_fake_diff_preview_contract(contract)

    assert validated["diff_preview_status"] in {"blocked", "not_created"}
    assert validated["formal_writeback_allowed"] is False
    assert "thinking_only_fallback_cannot_create_diff_preview" in validated["blocked_reasons"]


def test_missing_evidence_anchor_blocks_diff_preview():
    cases = [
        (
            make_fake_diff_preview_contract(evidence_anchor_status="missing"),
            "missing_evidence_anchor",
        ),
        (
            make_fake_diff_preview_contract(evidence_anchor_refs=[]),
            "missing_evidence_anchor",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_advisory_shadow_candidate_and_patch_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        contract = make_fake_diff_preview_contract(evidence_binding_status=binding_status)
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] != "ready_for_human_review"
        assert validated["diff_preview_status"] != "approved_diff_shadow_only"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_or_stale_source_hash_blocks_diff_preview():
    cases = [
        (
            make_fake_diff_preview_contract(source_section_hash=""),
            "missing_source_section_hash",
            "blocked",
        ),
        (
            make_fake_diff_preview_contract(
                source_hash_revalidation_required=True,
                source_hash_revalidation_ready=False,
            ),
            "source_hash_revalidation_missing",
            "blocked",
        ),
        (
            make_fake_diff_preview_contract(
                fake_metadata={
                    "source_section_hash_match": False,
                    "diff_base_hash_match": True,
                    "source_write_performed": False,
                    "review_apply_performed": False,
                    "output_write_performed": False,
                    "request_type": "preview_only",
                }
            ),
            "source_section_hash_mismatch",
            "stale_source_hash",
        ),
        (
            make_fake_diff_preview_contract(
                fake_metadata={
                    "source_section_hash_match": True,
                    "diff_base_hash_match": False,
                    "source_write_performed": False,
                    "review_apply_performed": False,
                    "output_write_performed": False,
                    "request_type": "preview_only",
                }
            ),
            "stale_source_hash",
            "stale_source_hash",
        ),
    ]

    for contract, reason, expected_status in cases:
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] == expected_status
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_before_after_or_patch_hash_blocks_diff_preview():
    cases = {
        "before_text_hash": ("", "missing_before_text_hash"),
        "after_text_preview_hash": ("", "missing_after_text_preview_hash"),
        "patch_operations_preview_hash": ("", "missing_patch_operations_preview_hash"),
    }

    for field, (value, reason) in cases.items():
        contract = make_fake_diff_preview_contract(**{field: value})
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_human_approval_blocks_diff_preview():
    contract = make_fake_diff_preview_contract(
        human_approval_required=True,
        human_approval_received=False,
    )

    validated = validate_fake_diff_preview_contract(contract)

    assert validated["diff_preview_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "missing_human_approval" in validated["blocked_reasons"]


def test_missing_rollback_plan_blocks_diff_preview():
    contract = make_fake_diff_preview_contract(
        rollback_required=True,
        rollback_plan_ready=False,
    )

    validated = validate_fake_diff_preview_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "rollback_plan_missing" in validated["blocked_reasons"]


def test_missing_formal_writeback_guard_blocks_diff_preview():
    contract = make_fake_diff_preview_contract(
        formal_writeback_guard_required=True,
        formal_writeback_guard_ready=False,
    )

    validated = validate_fake_diff_preview_contract(contract)

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
        contract = make_fake_diff_preview_contract(
            fake_metadata={
                "source_section_hash_match": True,
                "diff_base_hash_match": True,
                "source_write_performed": False,
                "review_apply_performed": False,
                "output_write_performed": False,
                "request_type": request_type,
            }
        )
        validated = validate_fake_diff_preview_contract(contract)

        assert validated["diff_preview_status"] == "blocked"
        assert_formal_flags_false(validated)
        assert reason in validated["blocked_reasons"]


def test_current_stage_formal_flags_are_always_false():
    for status in DIFF_PREVIEW_STATUSES:
        contract = make_fake_diff_preview_contract(
            diff_preview_status=status,
            formal_writeback_allowed=True,
            docx_export_allowed=True,
            zbid_writeback_allowed=True,
            output_write_allowed=True,
        )

        validated = validate_fake_diff_preview_contract(contract)

        assert_formal_flags_false(validated)


def test_diff_preview_is_not_source_write():
    contract = make_fake_diff_preview_contract()
    validated = validate_fake_diff_preview_contract(contract)

    assert contract["diff_summary_preview"] != contract["source_section_id"]
    assert contract["diff_operations_preview"] != "review/apply patch"
    assert contract["affected_anchor_refs"] != contract["evidence_anchor_refs"]
    assert contract["fake_metadata"]["source_write_performed"] is False
    assert contract["fake_metadata"]["review_apply_performed"] is False
    assert contract["fake_metadata"]["output_write_performed"] is False
    assert_formal_flags_false(validated)


def test_fake_diff_preview_contract_uses_deterministic_generated_at_and_id():
    first = make_fake_diff_preview_contract()
    second = make_fake_diff_preview_contract()
    different = make_fake_diff_preview_contract(source_section_hash="sha256:other-source-section")

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["diff_preview_id"] == second["diff_preview_id"]
    assert first["diff_preview_id"].startswith("diff-preview-")
    assert first["diff_preview_id"] != different["diff_preview_id"]


def test_fake_diff_preview_contract_does_not_write_output_job_export():
    before = output_job_export_snapshot()

    contract = make_fake_diff_preview_contract(
        fake_metadata={
            "source_section_hash_match": True,
            "diff_base_hash_match": True,
            "source_write_performed": False,
            "review_apply_performed": False,
            "output_write_performed": False,
            "request_type": "output_write",
        }
    )
    validate_fake_diff_preview_contract(contract)

    after = output_job_export_snapshot()
    assert after == before


def test_diff_preview_contract_schema_imports_do_not_pull_main_chain_modules():
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
