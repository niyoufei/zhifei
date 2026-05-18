from pathlib import Path


REQUIRED_FIELDS = {
    "contract_version",
    "request_id",
    "source_document_id",
    "source_section_id",
    "source_section_hash",
    "response_mode",
    "input_risk_level",
    "evidence_anchor_status",
    "evidence_anchor_refs",
    "advisory_quality_gate_status",
    "readiness_status",
    "shadow_candidate_status",
    "shadow_candidate_id",
    "candidate_kind",
    "candidate_scope",
    "candidate_text_preview",
    "candidate_patch_preview",
    "model_provider",
    "model_name",
    "generated_at",
    "human_approval_required",
    "human_approval_received",
    "diff_required",
    "rollback_required",
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
    "blocked_reasons",
}

SHADOW_CANDIDATE_STATUSES = {
    "not_created",
    "blocked",
    "draft_shadow_only",
    "ready_for_human_review",
    "approved_shadow_only",
    "rejected",
}

EVIDENCE_ANCHOR_STATUSES = {
    "missing",
    "user_provided",
    "source_verified",
    "generated_advisory_only_blocked",
}

RESPONSE_MODES = {
    "preview_advisory",
    "thinking_only_fallback",
    "unsupported",
    "blocked",
}

READINESS_STATUSES = {
    "blocked",
    "fake_ready_metadata_only",
    "future_ready_for_shadow_candidate",
}

CURRENT_STAGE_FALSE_FLAGS = {
    "formal_writeback_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}

DETERMINISTIC_GENERATED_AT = "2026-01-01T00:00:00Z"


def make_fake_shadow_candidate_contract(**overrides):
    contract = {
        "contract_version": "0.1",
        "request_id": "req-shadow-contract-001",
        "source_document_id": "doc-safe-preview",
        "source_section_id": "section-safe-preview",
        "source_section_hash": "sha256:source-section",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "evidence_anchor_status": "source_verified",
        "evidence_anchor_refs": ["tender:section:1"],
        "advisory_quality_gate_status": "preview_ok",
        "readiness_status": "fake_ready_metadata_only",
        "shadow_candidate_status": "draft_shadow_only",
        "shadow_candidate_id": "shadow-candidate-preview-only",
        "candidate_kind": "section_patch_preview",
        "candidate_scope": "section",
        "candidate_text_preview": "Preview-only candidate text, not formal text.",
        "candidate_patch_preview": "Preview-only patch, not a real patch.",
        "model_provider": "fake",
        "model_name": "fake-model",
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "human_approval_required": True,
        "human_approval_received": False,
        "diff_required": True,
        "rollback_required": True,
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": [],
        "fake_metadata": {
            "diff_ready": True,
            "rollback_ready": True,
            "request_type": "preview_only",
        },
    }
    contract.update(overrides)
    return contract


def validate_fake_shadow_candidate_contract(contract):
    reasons = list(contract.get("blocked_reasons", []))
    status = contract.get("shadow_candidate_status")

    if not REQUIRED_FIELDS.issubset(contract):
        reasons.append("missing_required_contract_fields")
        status = "blocked"

    if contract.get("shadow_candidate_status") not in SHADOW_CANDIDATE_STATUSES:
        reasons.append("invalid_shadow_candidate_status")
        status = "blocked"

    if contract.get("evidence_anchor_status") not in EVIDENCE_ANCHOR_STATUSES:
        reasons.append("invalid_evidence_anchor_status")
        status = "blocked"

    if contract.get("response_mode") not in RESPONSE_MODES:
        reasons.append("invalid_response_mode")
        status = "blocked"

    if contract.get("readiness_status") not in READINESS_STATUSES:
        reasons.append("invalid_readiness_status")
        status = "blocked"

    if contract.get("generated_at") != DETERMINISTIC_GENERATED_AT:
        reasons.append("generated_at_must_be_deterministic")
        status = "blocked"

    if contract.get("response_mode") == "thinking_only_fallback":
        reasons.append("thinking_only_fallback_cannot_create_shadow_candidate")
        status = "blocked"

    evidence_status = contract.get("evidence_anchor_status")
    evidence_refs = contract.get("evidence_anchor_refs") or []
    if evidence_status == "generated_advisory_only_blocked":
        reasons.append("model_generated_advisory_cannot_be_evidence")
        status = "blocked"

    if evidence_status == "missing" or not evidence_refs:
        reasons.append("missing_evidence_anchor")
        status = "blocked"

    if any(ref in {contract.get("candidate_text_preview"), contract.get("candidate_patch_preview")} for ref in evidence_refs):
        reasons.append("shadow_candidate_preview_fields_cannot_be_evidence")
        status = "blocked"

    if contract.get("evidence_anchor_status") == "source_verified" and any(
        str(ref).startswith("shadow_candidate:") or str(ref).startswith("model_advisory:")
        for ref in evidence_refs
    ):
        reasons.append("shadow_candidate_cannot_be_source_verified_evidence")
        status = "blocked"

    if contract.get("human_approval_required") and not contract.get("human_approval_received"):
        reasons.append("missing_human_approval")

    metadata = contract.get("fake_metadata", {})
    if contract.get("diff_required") and not metadata.get("diff_ready", False):
        reasons.append("diff_preview_required_before_writeback")
        status = "blocked"

    if contract.get("rollback_required") and not metadata.get("rollback_ready", False):
        reasons.append("rollback_plan_required_before_writeback")
        status = "blocked"

    blocked_request_types = {
        "docx_export",
        "zbid_writeback",
        "output_write",
        "formal_generation",
    }
    if metadata.get("request_type") in blocked_request_types:
        reasons.append(f"{metadata['request_type']}_request_blocked")
        status = "blocked"

    validated = dict(contract)
    validated["shadow_candidate_status"] = status
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


def test_shadow_candidate_contract_required_fields_are_explicit():
    contract = make_fake_shadow_candidate_contract()

    assert REQUIRED_FIELDS.issubset(contract)
    assert set(contract).issuperset(REQUIRED_FIELDS)


def test_shadow_candidate_status_enums_are_locked():
    assert SHADOW_CANDIDATE_STATUSES == {
        "not_created",
        "blocked",
        "draft_shadow_only",
        "ready_for_human_review",
        "approved_shadow_only",
        "rejected",
    }
    assert EVIDENCE_ANCHOR_STATUSES == {
        "missing",
        "user_provided",
        "source_verified",
        "generated_advisory_only_blocked",
    }
    assert RESPONSE_MODES == {
        "preview_advisory",
        "thinking_only_fallback",
        "unsupported",
        "blocked",
    }
    assert READINESS_STATUSES == {
        "blocked",
        "fake_ready_metadata_only",
        "future_ready_for_shadow_candidate",
    }


def test_thinking_only_fallback_blocks_shadow_candidate():
    contract = make_fake_shadow_candidate_contract(
        response_mode="thinking_only_fallback",
        shadow_candidate_status="ready_for_human_review",
        human_approval_received=True,
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["shadow_candidate_status"] in {"blocked", "not_created"}
    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "thinking_only_fallback_cannot_create_shadow_candidate" in validated["blocked_reasons"]


def test_generated_advisory_only_cannot_be_evidence():
    contract = make_fake_shadow_candidate_contract(
        evidence_anchor_status="generated_advisory_only_blocked",
        shadow_candidate_status="ready_for_human_review",
        human_approval_received=True,
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["shadow_candidate_status"] not in {"ready_for_human_review", "approved_shadow_only"}
    assert validated["formal_writeback_allowed"] is False
    assert "model_generated_advisory_cannot_be_evidence" in validated["blocked_reasons"]


def test_missing_evidence_anchor_blocks_review_and_writeback():
    contract = make_fake_shadow_candidate_contract(
        evidence_anchor_status="missing",
        evidence_anchor_refs=[],
        shadow_candidate_status="ready_for_human_review",
        human_approval_received=True,
        formal_writeback_allowed=True,
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["shadow_candidate_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "missing_evidence_anchor" in validated["blocked_reasons"]


def test_missing_human_approval_blocks_formal_writeback():
    contract = make_fake_shadow_candidate_contract(
        human_approval_required=True,
        human_approval_received=False,
        formal_writeback_allowed=True,
        docx_export_allowed=True,
        zbid_writeback_allowed=True,
        output_write_allowed=True,
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["formal_writeback_allowed"] is False
    assert validated["docx_export_allowed"] is False
    assert validated["zbid_writeback_allowed"] is False
    assert validated["output_write_allowed"] is False
    assert "missing_human_approval" in validated["blocked_reasons"]


def test_missing_diff_or_rollback_blocks_formal_writeback():
    contract = make_fake_shadow_candidate_contract(
        human_approval_received=True,
        formal_writeback_allowed=True,
        fake_metadata={
            "diff_ready": False,
            "rollback_ready": False,
            "request_type": "preview_only",
        },
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["shadow_candidate_status"] == "blocked"
    assert validated["formal_writeback_allowed"] is False
    assert "diff_preview_required_before_writeback" in validated["blocked_reasons"]
    assert "rollback_plan_required_before_writeback" in validated["blocked_reasons"]


def test_current_stage_formal_flags_are_always_false():
    for status in SHADOW_CANDIDATE_STATUSES:
        contract = make_fake_shadow_candidate_contract(
            shadow_candidate_status=status,
            human_approval_received=True,
            formal_writeback_allowed=True,
            docx_export_allowed=True,
            zbid_writeback_allowed=True,
            output_write_allowed=True,
        )

        validated = validate_fake_shadow_candidate_contract(contract)

        assert validated["formal_writeback_allowed"] is False
        assert validated["docx_export_allowed"] is False
        assert validated["zbid_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False


def test_shadow_candidate_preview_fields_are_not_evidence():
    candidate_text = "Preview-only candidate text, not evidence."
    candidate_patch = "Preview-only candidate patch, not evidence."
    contract = make_fake_shadow_candidate_contract(
        candidate_text_preview=candidate_text,
        candidate_patch_preview=candidate_patch,
        evidence_anchor_status="source_verified",
        evidence_anchor_refs=[candidate_text, candidate_patch, "shadow_candidate:preview-only"],
        shadow_candidate_status="ready_for_human_review",
        human_approval_received=True,
    )

    validated = validate_fake_shadow_candidate_contract(contract)

    assert validated["shadow_candidate_status"] == "blocked"
    assert "shadow_candidate_preview_fields_cannot_be_evidence" in validated["blocked_reasons"]
    assert "shadow_candidate_cannot_be_source_verified_evidence" in validated["blocked_reasons"]
    assert validated["formal_writeback_allowed"] is False


def test_docx_zbid_export_and_formal_generation_requests_are_blocked():
    for request_type in ("docx_export", "zbid_writeback", "output_write", "formal_generation"):
        contract = make_fake_shadow_candidate_contract(
            human_approval_received=True,
            formal_writeback_allowed=True,
            docx_export_allowed=True,
            zbid_writeback_allowed=True,
            output_write_allowed=True,
            fake_metadata={
                "diff_ready": True,
                "rollback_ready": True,
                "request_type": request_type,
            },
        )

        validated = validate_fake_shadow_candidate_contract(contract)

        assert validated["shadow_candidate_status"] == "blocked"
        assert validated["formal_writeback_allowed"] is False
        assert validated["docx_export_allowed"] is False
        assert validated["zbid_writeback_allowed"] is False
        assert validated["output_write_allowed"] is False
        assert f"{request_type}_request_blocked" in validated["blocked_reasons"]


def test_fake_contract_uses_deterministic_generated_at():
    contract = make_fake_shadow_candidate_contract()

    assert contract["generated_at"] == DETERMINISTIC_GENERATED_AT
    assert "now" not in contract["generated_at"].lower()


def test_fake_contract_validation_does_not_write_output_job_or_export():
    before = output_job_export_snapshot()

    contract = make_fake_shadow_candidate_contract(
        response_mode="thinking_only_fallback",
        evidence_anchor_status="generated_advisory_only_blocked",
        evidence_anchor_refs=[],
    )
    validate_fake_shadow_candidate_contract(contract)

    after = output_job_export_snapshot()
    assert after == before
