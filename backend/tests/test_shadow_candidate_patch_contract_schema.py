import ast
import hashlib
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "patch_id",
    "shadow_candidate_id",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "source_section_version",
    "patch_status",
    "patch_kind",
    "patch_scope",
    "patch_format",
    "patch_operation_type",
    "patch_operations_preview",
    "before_text_hash",
    "after_text_preview",
    "affected_anchor_refs",
    "evidence_anchor_status",
    "evidence_anchor_refs",
    "evidence_binding_status",
    "response_mode",
    "input_risk_level",
    "advisory_quality_gate_status",
    "readiness_status",
    "shadow_candidate_status",
    "generated_at",
    "model_provider",
    "model_name",
    "human_approval_required",
    "human_approval_received",
    "diff_preview_required",
    "diff_preview_ready",
    "rollback_required",
    "rollback_plan_ready",
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
}

PATCH_STATUSES = {
    "not_created",
    "blocked",
    "draft_patch_shadow_only",
    "ready_for_human_review",
    "approved_patch_shadow_only",
    "rejected",
}

PATCH_KINDS = {
    "section_rewrite",
    "paragraph_rewrite",
    "insert_after_anchor",
    "replace_anchor_range",
    "delete_anchor_range",
    "metadata_only",
}

PATCH_OPERATION_TYPES = {
    "no_op",
    "replace",
    "insert",
    "delete",
    "reorder",
    "mixed",
}

PATCH_FORMATS = {
    "text_preview",
    "structured_patch_preview",
    "metadata_only",
}

EVIDENCE_BINDING_STATUSES = {
    "missing",
    "bound_to_user_provided_evidence",
    "bound_to_source_verified_evidence",
    "generated_advisory_only_blocked",
    "shadow_candidate_only_blocked",
    "patch_preview_only_blocked",
}

CURRENT_STAGE_FALSE_FLAGS = {
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def deterministic_patch_id(seed):
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"patch-{digest[:16]}"


def make_fake_shadow_candidate_patch_contract(**overrides):
    seed = {
        "request_id": "req-shadow-patch-001",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "source_section_hash": "sha256:source-section",
        "source_section_version": "v1",
        "patch_kind": "paragraph_rewrite",
        "patch_scope": "paragraph",
    }
    contract = {
        "contract_version": "0.1",
        "patch_id": deterministic_patch_id(seed),
        "shadow_candidate_id": seed["shadow_candidate_id"],
        "request_id": seed["request_id"],
        "source_document_id": "doc-safe-preview",
        "source_section_id": "section-safe-preview",
        "source_section_hash": seed["source_section_hash"],
        "source_section_version": seed["source_section_version"],
        "patch_status": "draft_patch_shadow_only",
        "patch_kind": seed["patch_kind"],
        "patch_scope": seed["patch_scope"],
        "patch_format": "structured_patch_preview",
        "patch_operation_type": "replace",
        "patch_operations_preview": [{"op": "replace", "anchor_ref": "tender:section:1"}],
        "before_text_hash": "sha256:before-text",
        "after_text_preview": "Preview-only replacement text, not formal content.",
        "affected_anchor_refs": ["section:anchor:1"],
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "fake_ready_metadata_only",
        "shadow_candidate_status": "draft_shadow_only",
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "human_approval_required": True,
        "human_approval_received": True,
        "diff_preview_required": True,
        "diff_preview_ready": True,
        "rollback_required": True,
        "rollback_plan_ready": True,
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "fake_metadata": {
            "source_section_hash_match": True,
            "source_write_performed": False,
            "output_write_performed": False,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    if "patch_id" not in overrides:
        contract["patch_id"] = deterministic_patch_id(
            {
                "request_id": contract["request_id"],
                "shadow_candidate_id": contract["shadow_candidate_id"],
                "source_section_hash": contract["source_section_hash"],
                "source_section_version": contract["source_section_version"],
                "patch_kind": contract["patch_kind"],
                "patch_scope": contract["patch_scope"],
            }
        )
    return contract


def validate_fake_shadow_candidate_patch_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("patch_status")

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_patch_contract_fields")
        status = "blocked"

    if contract.get("patch_status") not in PATCH_STATUSES:
        reasons.append("invalid_patch_status")
        status = "blocked"

    if contract.get("patch_kind") not in PATCH_KINDS:
        reasons.append("invalid_patch_kind")
        status = "blocked"

    if contract.get("patch_operation_type") not in PATCH_OPERATION_TYPES:
        reasons.append("invalid_patch_operation_type")
        status = "blocked"

    if contract.get("patch_format") not in PATCH_FORMATS:
        reasons.append("invalid_patch_format")
        status = "blocked"

    if contract.get("evidence_binding_status") not in EVIDENCE_BINDING_STATUSES:
        reasons.append("invalid_evidence_binding_status")
        status = "blocked"

    if contract.get("generated_at") != DETERMINISTIC_GENERATED_AT:
        reasons.append("generated_at_must_be_deterministic")
        status = "blocked"

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_create_patch")
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
        "shadow_candidate_only_blocked": "shadow_candidate_envelope_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }
    binding_status = contract.get("evidence_binding_status")
    if binding_status in binding_block_reasons:
        reasons.append(binding_block_reasons[binding_status])
        status = "blocked"

    if contract.get("shadow_candidate_status") in {"blocked", "not_created"}:
        reasons.append("shadow_candidate_prerequisite_not_satisfied")
        status = "blocked"

    metadata = contract.get("fake_metadata", {})
    if not contract.get("source_section_hash"):
        reasons.append("missing_source_section_hash")
        status = "blocked"

    if metadata.get("source_section_hash_match") is False:
        reasons.append("source_section_hash_mismatch")
        status = "blocked"

    if not contract.get("before_text_hash"):
        reasons.append("missing_before_text_hash")
        status = "blocked"

    if contract.get("human_approval_required") and not contract.get("human_approval_received"):
        reasons.append("missing_human_approval")
        status = "blocked"

    if contract.get("diff_preview_required") and not contract.get("diff_preview_ready"):
        reasons.append("missing_diff_preview")
        status = "blocked"

    if contract.get("rollback_required") and not contract.get("rollback_plan_ready"):
        reasons.append("missing_rollback_plan")
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

    preview_values = {
        str(contract.get("patch_operations_preview")),
        str(contract.get("after_text_preview")),
    } - {""}
    if preview_values and any(str(ref) in preview_values for ref in evidence_refs):
        reasons.append("patch_preview_cannot_be_evidence")
        status = "blocked"

    validated = dict(contract)
    validated["patch_status"] = status
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


def test_shadow_candidate_patch_contract_required_fields_are_explicit():
    contract = make_fake_shadow_candidate_patch_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_shadow_candidate_patch_status_enums_are_locked():
    assert PATCH_STATUSES == {
        "not_created",
        "blocked",
        "draft_patch_shadow_only",
        "ready_for_human_review",
        "approved_patch_shadow_only",
        "rejected",
    }


def test_patch_kind_operation_and_format_enums_are_locked():
    assert PATCH_KINDS == {
        "section_rewrite",
        "paragraph_rewrite",
        "insert_after_anchor",
        "replace_anchor_range",
        "delete_anchor_range",
        "metadata_only",
    }
    assert PATCH_OPERATION_TYPES == {
        "no_op",
        "replace",
        "insert",
        "delete",
        "reorder",
        "mixed",
    }
    assert PATCH_FORMATS == {
        "text_preview",
        "structured_patch_preview",
        "metadata_only",
    }


def test_evidence_binding_status_enums_are_locked():
    assert EVIDENCE_BINDING_STATUSES == {
        "missing",
        "bound_to_user_provided_evidence",
        "bound_to_source_verified_evidence",
        "generated_advisory_only_blocked",
        "shadow_candidate_only_blocked",
        "patch_preview_only_blocked",
    }


def test_thinking_only_fallback_blocks_patch():
    contract = make_fake_shadow_candidate_patch_contract(
        response_mode="thinking_only_fallback",
        patch_status="ready_for_human_review",
    )

    validated = validate_fake_shadow_candidate_patch_contract(contract)

    assert validated["patch_status"] in {"blocked", "not_created"}
    assert_formal_flags_false(validated)
    assert "thinking_only_fallback_cannot_create_patch" in validated["blocked_reasons"]


def test_missing_evidence_anchor_blocks_patch_review_and_writeback():
    cases = [
        make_fake_shadow_candidate_patch_contract(evidence_anchor_status="missing"),
        make_fake_shadow_candidate_patch_contract(evidence_anchor_refs=[]),
    ]

    for contract in cases:
        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert validated["patch_status"] == "blocked"
        assert validated["patch_status"] != "ready_for_human_review"
        assert validated["formal_writeback_allowed"] is False
        assert "missing_evidence_anchor" in validated["blocked_reasons"]


def test_advisory_envelope_and_patch_preview_cannot_be_evidence():
    cases = {
        "generated_advisory_only_blocked": "generated_advisory_cannot_be_evidence",
        "shadow_candidate_only_blocked": "shadow_candidate_envelope_cannot_be_evidence",
        "patch_preview_only_blocked": "patch_preview_cannot_be_evidence",
    }

    for binding_status, reason in cases.items():
        contract = make_fake_shadow_candidate_patch_contract(
            evidence_binding_status=binding_status,
            patch_status="ready_for_human_review",
        )
        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert validated["patch_status"] != "ready_for_human_review"
        assert validated["patch_status"] != "approved_patch_shadow_only"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_blocked_shadow_candidate_blocks_patch():
    for shadow_status in {"blocked", "not_created"}:
        contract = make_fake_shadow_candidate_patch_contract(
            shadow_candidate_status=shadow_status,
            patch_status="ready_for_human_review",
        )

        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert validated["patch_status"] in {"blocked", "not_created"}
        assert validated["patch_status"] != "ready_for_human_review"
        assert validated["formal_writeback_allowed"] is False
        assert "shadow_candidate_prerequisite_not_satisfied" in validated["blocked_reasons"]


def test_missing_or_mismatched_source_hash_blocks_writeback():
    cases = [
        (
            make_fake_shadow_candidate_patch_contract(source_section_hash=""),
            "missing_source_section_hash",
        ),
        (
            make_fake_shadow_candidate_patch_contract(
                fake_metadata={
                    "source_section_hash_match": False,
                    "source_write_performed": False,
                    "output_write_performed": False,
                    "request_type": "preview_only",
                }
            ),
            "source_section_hash_mismatch",
        ),
        (
            make_fake_shadow_candidate_patch_contract(before_text_hash=""),
            "missing_before_text_hash",
        ),
    ]

    for contract, reason in cases:
        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert validated["patch_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert reason in validated["blocked_reasons"]


def test_missing_human_approval_blocks_patch_writeback():
    contract = make_fake_shadow_candidate_patch_contract(
        human_approval_required=True,
        human_approval_received=False,
    )

    validated = validate_fake_shadow_candidate_patch_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "missing_human_approval" in validated["blocked_reasons"]


def test_missing_diff_preview_blocks_patch_writeback():
    contract = make_fake_shadow_candidate_patch_contract(
        diff_preview_required=True,
        diff_preview_ready=False,
    )

    validated = validate_fake_shadow_candidate_patch_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "missing_diff_preview" in validated["blocked_reasons"]


def test_missing_rollback_plan_blocks_patch_writeback():
    contract = make_fake_shadow_candidate_patch_contract(
        rollback_required=True,
        rollback_plan_ready=False,
    )

    validated = validate_fake_shadow_candidate_patch_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert "missing_rollback_plan" in validated["blocked_reasons"]


def test_current_stage_formal_flags_are_always_false():
    for status in PATCH_STATUSES:
        contract = make_fake_shadow_candidate_patch_contract(
            patch_status=status,
            formal_writeback_allowed=True,
            docx_export_allowed=True,
            zbid_writeback_allowed=True,
            output_write_allowed=True,
        )

        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert_formal_flags_false(validated)


def test_patch_preview_is_not_source_write():
    before = output_job_export_snapshot()
    contract = make_fake_shadow_candidate_patch_contract(
        patch_operations_preview=[{"op": "replace", "text": "preview-only"}],
        after_text_preview="preview-only after text",
        affected_anchor_refs=["section:anchor:preview"],
        evidence_anchor_refs=["tender:section:1"],
    )

    validated = validate_fake_shadow_candidate_patch_contract(contract)
    after = output_job_export_snapshot()

    assert contract["fake_metadata"]["source_write_performed"] is False
    assert contract["fake_metadata"]["output_write_performed"] is False
    assert contract["patch_operations_preview"] != "source_section_write"
    assert contract["after_text_preview"] != "formal_section_text"
    assert contract["affected_anchor_refs"] != contract["evidence_anchor_refs"]
    assert validated["output_write_allowed"] is False
    assert after == before


def test_docx_zbid_export_formal_and_review_apply_requests_are_blocked():
    cases = {
        "docx_export": "docx_export_request_blocked",
        "zbid_writeback": "zbid_writeback_request_blocked",
        "output_write": "output_write_request_blocked",
        "formal_generation": "formal_generation_request_blocked",
        "review_apply": "review_apply_request_blocked",
    }

    for request_type, reason in cases.items():
        contract = make_fake_shadow_candidate_patch_contract(
            fake_metadata={
                "source_section_hash_match": True,
                "source_write_performed": False,
                "output_write_performed": False,
                "request_type": request_type,
            }
        )
        validated = validate_fake_shadow_candidate_patch_contract(contract)

        assert validated["patch_status"] == "blocked"
        assert_formal_flags_false(validated)
        assert reason in validated["blocked_reasons"]


def test_fake_patch_contract_uses_deterministic_generated_at_and_patch_id():
    first = make_fake_shadow_candidate_patch_contract()
    second = make_fake_shadow_candidate_patch_contract()
    different = make_fake_shadow_candidate_patch_contract(source_section_hash="sha256:other")

    assert first["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert first["patch_id"] == second["patch_id"]
    assert first["patch_id"].startswith("patch-")
    assert first["patch_id"] != different["patch_id"]


def test_fake_patch_contract_does_not_write_output_job_export():
    before = output_job_export_snapshot()

    contract = make_fake_shadow_candidate_patch_contract(
        response_mode="thinking_only_fallback",
        fake_metadata={
            "source_section_hash_match": True,
            "source_write_performed": False,
            "output_write_performed": False,
            "request_type": "output_write",
        },
    )
    validate_fake_shadow_candidate_patch_contract(contract)

    after = output_job_export_snapshot()
    assert after == before


def test_patch_contract_schema_imports_do_not_pull_main_chain_modules():
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
    tree = ast.parse(Path(__file__).read_text())
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module)

    for forbidden in forbidden_import_roots:
        assert forbidden not in imported_roots
