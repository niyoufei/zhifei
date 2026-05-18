from __future__ import annotations

import hashlib
import json
from typing import Any


CONTRACT_VERSION = "0.1"

REQUIRED_FIELDS = frozenset(
    {
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
)

SHADOW_CANDIDATE_STATUSES = frozenset(
    {
        "not_created",
        "blocked",
        "draft_shadow_only",
        "ready_for_human_review",
        "approved_shadow_only",
        "rejected",
    }
)

CURRENT_STAGE_EMITTABLE_STATUSES = frozenset({"not_created", "blocked"})

EVIDENCE_ANCHOR_STATUSES = frozenset(
    {
        "missing",
        "user_provided",
        "source_verified",
        "generated_advisory_only_blocked",
    }
)

RESPONSE_MODES = frozenset(
    {
        "preview_advisory",
        "thinking_only_fallback",
        "unsupported",
        "blocked",
    }
)

READINESS_STATUSES = frozenset(
    {
        "blocked",
        "fake_ready_metadata_only",
        "future_ready_for_shadow_candidate",
    }
)

CURRENT_STAGE_FORMAL_FLAGS = frozenset(
    {
        "formal_writeback_allowed",
        "docx_export_allowed",
        "zbid_writeback_allowed",
        "output_write_allowed",
    }
)

_QUALITY_GATE_ALLOWED_STATUSES = frozenset(
    {
        "ok",
        "pass",
        "passed",
        "allowed",
        "preview_ok",
        "quality_ok",
    }
)


def _text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value)


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _candidate_id(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"shadow-candidate-{digest[:16]}"


def build_shadow_candidate_envelope(
    *,
    request_id: str,
    source_document_id: str,
    source_section_id: str,
    source_section_hash: str,
    response_mode: str,
    input_risk_level: str,
    evidence_anchor_status: str,
    evidence_anchor_refs: list[Any] | tuple[Any, ...] | None,
    advisory_quality_gate_status: str,
    readiness_status: str,
    candidate_kind: str = "",
    candidate_scope: str = "",
    model_provider: str = "",
    model_name: str = "",
    generated_at: str,
    human_approval_required: bool = True,
    human_approval_received: bool = False,
    diff_required: bool = True,
    rollback_required: bool = True,
    diff_ready: bool = False,
    rollback_ready: bool = False,
    docx_export_requested: bool = False,
    zbid_writeback_requested: bool = False,
    output_write_requested: bool = False,
    formal_generation_requested: bool = False,
    candidate_text_preview: str = "",
    candidate_patch_preview: str = "",
) -> dict[str, Any]:
    response_mode = _text(response_mode, limit=120)
    evidence_anchor_status = _text(evidence_anchor_status, limit=120)
    advisory_quality_gate_status = _text(advisory_quality_gate_status, limit=120).lower()
    readiness_status = _text(readiness_status, limit=120)
    candidate_text_preview = _text(candidate_text_preview)
    candidate_patch_preview = _text(candidate_patch_preview)
    evidence_refs = _list(evidence_anchor_refs)
    blocked_reasons: list[str] = []

    if response_mode == "thinking_only_fallback":
        _append_unique(blocked_reasons, "thinking_only_fallback_not_candidate_capable")
    elif response_mode in {"unsupported", "blocked"} or response_mode not in RESPONSE_MODES:
        _append_unique(blocked_reasons, "unsupported_response_mode")

    if evidence_anchor_status == "missing":
        _append_unique(blocked_reasons, "missing_evidence_anchor")
    elif evidence_anchor_status == "generated_advisory_only_blocked":
        _append_unique(blocked_reasons, "generated_advisory_cannot_be_evidence")
    elif evidence_anchor_status not in EVIDENCE_ANCHOR_STATUSES:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    if not evidence_refs:
        _append_unique(blocked_reasons, "missing_evidence_anchor")

    preview_values = {candidate_text_preview, candidate_patch_preview} - {""}
    if preview_values and any(ref in preview_values for ref in evidence_refs):
        _append_unique(blocked_reasons, "shadow_candidate_preview_cannot_be_evidence")

    if advisory_quality_gate_status not in _QUALITY_GATE_ALLOWED_STATUSES:
        _append_unique(blocked_reasons, "advisory_quality_gate_not_passed")

    if readiness_status == "blocked" or readiness_status not in READINESS_STATUSES:
        _append_unique(blocked_reasons, "readiness_not_for_candidate_generation")
    elif readiness_status == "fake_ready_metadata_only":
        _append_unique(blocked_reasons, "readiness_not_for_candidate_generation")

    if _bool(human_approval_required) and not _bool(human_approval_received):
        _append_unique(blocked_reasons, "human_approval_missing")

    if _bool(diff_required) and not _bool(diff_ready):
        _append_unique(blocked_reasons, "diff_not_ready")

    if _bool(rollback_required) and not _bool(rollback_ready):
        _append_unique(blocked_reasons, "rollback_not_ready")

    if _bool(docx_export_requested):
        _append_unique(blocked_reasons, "docx_export_request_blocked")

    if _bool(zbid_writeback_requested):
        _append_unique(blocked_reasons, "zbid_writeback_request_blocked")

    if _bool(output_write_requested):
        _append_unique(blocked_reasons, "output_write_request_blocked")

    if _bool(formal_generation_requested):
        _append_unique(blocked_reasons, "formal_generation_request_blocked")

    _append_unique(blocked_reasons, "shadow_generation_not_implemented_current_stage")

    id_seed = {
        "contract_version": CONTRACT_VERSION,
        "request_id": _text(request_id, limit=240),
        "source_document_id": _text(source_document_id, limit=240),
        "source_section_id": _text(source_section_id, limit=240),
        "source_section_hash": _text(source_section_hash, limit=240),
        "response_mode": response_mode,
        "evidence_anchor_status": evidence_anchor_status,
        "candidate_kind": _text(candidate_kind, limit=120),
        "candidate_scope": _text(candidate_scope, limit=120),
        "generated_at": _text(generated_at, limit=120),
    }

    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": id_seed["request_id"],
        "source_document_id": id_seed["source_document_id"],
        "source_section_id": id_seed["source_section_id"],
        "source_section_hash": id_seed["source_section_hash"],
        "response_mode": response_mode,
        "input_risk_level": _text(input_risk_level, limit=120),
        "evidence_anchor_status": evidence_anchor_status,
        "evidence_anchor_refs": evidence_refs,
        "advisory_quality_gate_status": advisory_quality_gate_status,
        "readiness_status": readiness_status,
        "shadow_candidate_status": "blocked" if blocked_reasons else "not_created",
        "shadow_candidate_id": _candidate_id(id_seed),
        "candidate_kind": id_seed["candidate_kind"],
        "candidate_scope": id_seed["candidate_scope"],
        "candidate_text_preview": candidate_text_preview,
        "candidate_patch_preview": candidate_patch_preview,
        "model_provider": _text(model_provider, limit=120),
        "model_name": _text(model_name, limit=120),
        "generated_at": id_seed["generated_at"],
        "human_approval_required": _bool(human_approval_required),
        "human_approval_received": _bool(human_approval_received),
        "diff_required": _bool(diff_required),
        "rollback_required": _bool(rollback_required),
        "formal_writeback_allowed": False,
        "docx_export_allowed": False,
        "zbid_writeback_allowed": False,
        "output_write_allowed": False,
        "blocked_reasons": blocked_reasons,
        "diff_ready": _bool(diff_ready),
        "rollback_ready": _bool(rollback_ready),
        "docx_export_requested": _bool(docx_export_requested),
        "zbid_writeback_requested": _bool(zbid_writeback_requested),
        "output_write_requested": _bool(output_write_requested),
        "formal_generation_requested": _bool(formal_generation_requested),
    }
