from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from backend.zhifei_autoplan.zbid_preview_input_validator import validate_zbid_preview_input
from backend.zhifei_autoplan.zdoc_zbid_preview_packet import build_zdoc_zbid_preview_packet


LOCAL_TRIAL_PREVIEW_ONLY_PATH = "/local-trial/preview-only"
LOCAL_TRIAL_PREVIEW_ONLY_ROUTE_NAME = "local_trial_preview_only"
FIXED_DEFAULT_GENERATED_AT = "2026-01-01T00:00:00Z"
FORMAL_FLAGS_FALSE = {
    "formal_writeback_allowed": False,
    "review_apply_allowed": False,
    "docx_export_allowed": False,
    "zbid_writeback_allowed": False,
    "output_write_allowed": False,
}


router = APIRouter(tags=["Local Trial Preview Only"])


def _text(value: Any, *, default: str = "", limit: int = 12000) -> str:
    text = str(value if value is not None else default).strip()
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


def _append_unique(items: list[str], value: Any) -> None:
    item = _text(value, limit=240)
    if item and item not in items:
        items.append(item)


def _combined_blocked_reasons(
    preview_packet: dict[str, Any],
    validator_result: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for source in (preview_packet, validator_result):
        for reason in _list(source.get("blocked_reasons")):
            _append_unique(reasons, reason)
    return reasons


def _packet_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_system": _text(request.get("source_system"), default="zdoc", limit=120),
        "target_system": _text(request.get("target_system"), default="zbid", limit=120),
        "project_id": _text(request.get("project_id"), limit=240),
        "document_id": _text(request.get("document_id"), limit=240),
        "section_id": _text(request.get("section_id"), limit=240),
        "section_title": _text(request.get("section_title"), limit=500),
        "section_hash": _text(request.get("section_hash"), limit=240),
        "section_version": _text(request.get("section_version"), limit=120),
        "tender_file_refs": _list(request.get("tender_file_refs")),
        "scoring_clause_refs": _list(request.get("scoring_clause_refs")),
        "evidence_anchor_refs": _list(request.get("evidence_anchor_refs")),
        "evidence_anchor_status": _text(
            request.get("evidence_anchor_status"),
            default="missing",
            limit=120,
        ),
        "evidence_binding_status": _text(
            request.get("evidence_binding_status"),
            default="missing",
            limit=120,
        ),
        "response_mode": _text(
            request.get("response_mode"),
            default="preview_advisory",
            limit=120,
        ),
        "input_risk_level": _text(request.get("input_risk_level"), default="low", limit=120),
        "advisory_quality_gate_status": _text(
            request.get("advisory_quality_gate_status"),
            default="preview_ok",
            limit=120,
        ),
        "preview_advisory_summary": _text(request.get("preview_advisory_summary")),
        "shadow_candidate_id": _text(request.get("shadow_candidate_id"), limit=240),
        "patch_id": _text(request.get("patch_id"), limit=240),
        "diff_preview_id": _text(request.get("diff_preview_id"), limit=240),
        "rollback_plan_id": _text(request.get("rollback_plan_id"), limit=240),
        "dry_run_id": _text(request.get("dry_run_id"), limit=240),
        "generated_at": _text(
            request.get("generated_at"),
            default=FIXED_DEFAULT_GENERATED_AT,
            limit=120,
        ),
        "model_provider": _text(request.get("model_provider"), default="fake", limit=120),
        "model_name": _text(request.get("model_name"), default="fake-local-trial", limit=120),
        "generated_advisory_used_as_evidence": _bool(
            request.get("generated_advisory_used_as_evidence")
        ),
        "preview_advisory_used_as_evidence": _bool(
            request.get("preview_advisory_used_as_evidence")
        ),
        "shadow_candidate_used_as_evidence": _bool(
            request.get("shadow_candidate_used_as_evidence")
        ),
        "patch_preview_used_as_evidence": _bool(request.get("patch_preview_used_as_evidence")),
        "diff_preview_used_as_evidence": _bool(request.get("diff_preview_used_as_evidence")),
        "rollback_plan_used_as_evidence": _bool(
            request.get("rollback_plan_used_as_evidence")
        ),
        "dry_run_used_as_evidence": _bool(request.get("dry_run_used_as_evidence")),
        "scoring_clause_unverifiable": _bool(request.get("scoring_clause_unverifiable")),
        "high_risk_validation_ready": _bool(request.get("high_risk_validation_ready")),
        "zbid_writeback_requested": _bool(request.get("zbid_writeback_requested")),
        "docx_export_requested": _bool(request.get("docx_export_requested")),
        "review_apply_requested": _bool(request.get("review_apply_requested")),
        "formal_writeback_requested": _bool(request.get("formal_writeback_requested")),
        "output_write_requested": _bool(request.get("output_write_requested")),
        "zbid_preview_mode": _text(
            request.get("zbid_preview_mode"),
            default="preview_only",
            limit=120,
        ),
        "zbid_input_status": _text(request.get("zbid_input_status"), limit=120),
        "zbid_mapping_status": _text(request.get("zbid_mapping_status"), limit=120),
        "zbid_scoring_matrix_status": _text(
            request.get("zbid_scoring_matrix_status"),
            limit=120,
        ),
        "integration_request_id": _text(request.get("integration_request_id"), limit=240),
    }


@router.post(LOCAL_TRIAL_PREVIEW_ONLY_PATH)
async def local_trial_preview_only_route(
    request: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    metadata = request if isinstance(request, dict) else {}
    preview_packet = build_zdoc_zbid_preview_packet(**_packet_payload(metadata))
    validator_result = validate_zbid_preview_input(preview_packet)
    blocked_reasons = _combined_blocked_reasons(preview_packet, validator_result)

    return {
        "ok": True,
        "route_name": LOCAL_TRIAL_PREVIEW_ONLY_ROUTE_NAME,
        "endpoint_path": LOCAL_TRIAL_PREVIEW_ONLY_PATH,
        "preview_only": True,
        "no_write": True,
        "no_evidence": True,
        "metadata_only": True,
        "preview_packet": preview_packet,
        "validator_result": validator_result,
        "blocked_reasons": blocked_reasons,
        **FORMAL_FLAGS_FALSE,
        "calls_generate_route": False,
        "calls_export_docx_route": False,
        "calls_review_apply_route": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
        "calls_ollama": False,
        "calls_external_model_api": False,
        "downloads_models": False,
        "pulls_models": False,
    }
