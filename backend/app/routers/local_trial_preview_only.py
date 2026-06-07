from __future__ import annotations

import json
import re
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
ANSI_TERMINAL_CONTROL_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
TRACE_MARKERS = (
    "thinking",
    "...done thinking",
    "done thinking",
    "self-check",
    "self check",
    "思考过程",
    "自检",
    "reasoning trace",
)


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


def _strip_trace_lines(text: str) -> tuple[str, bool]:
    kept_lines: list[str] = []
    removed = False
    for line in text.splitlines():
        normalized = line.strip().lower()
        if any(marker in normalized for marker in TRACE_MARKERS):
            removed = True
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip(), removed


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()
    return ""


def _extract_markdown_block(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    first_marker = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lstrip().startswith(("#", "-", "*", "1.", "```", "|"))
        ),
        None,
    )
    if first_marker is None:
        return ""
    return "\n".join(lines[first_marker:]).strip()


def _post_process_preview_output(
    value: Any,
    *,
    target_format: str = "text",
    enabled: bool = True,
) -> dict[str, Any]:
    raw_text = _text(value)
    target = _text(target_format, default="text", limit=40).lower()
    result: dict[str, Any] = {
        "raw_text": raw_text,
        "cleaned_text": raw_text,
        "extracted_payload": None,
        "cleaning_applied": {
            "ansi_terminal_control_sequences": False,
            "thinking_self_check_traces": False,
            "target_structure_extracted": False,
            "disabled": not enabled,
        },
        "warnings": [],
        "blocked_reasons": [],
        "post_processing_blocked": False,
    }

    if not enabled:
        result["extracted_payload"] = raw_text
        result["warnings"].append("post_processing_disabled")
        return result

    without_controls = ANSI_TERMINAL_CONTROL_RE.sub("", raw_text)
    result["cleaning_applied"]["ansi_terminal_control_sequences"] = without_controls != raw_text
    cleaned_text, traces_removed = _strip_trace_lines(without_controls)
    result["cleaning_applied"]["thinking_self_check_traces"] = traces_removed
    result["cleaned_text"] = cleaned_text

    if target == "json":
        candidate = _extract_json_object(cleaned_text)
        if not candidate:
            result["blocked_reasons"].append("target_structure_not_found")
        else:
            result["cleaned_text"] = candidate
            result["cleaning_applied"]["target_structure_extracted"] = True
            try:
                result["extracted_payload"] = json.loads(candidate)
            except json.JSONDecodeError:
                result["extracted_payload"] = candidate
                result["blocked_reasons"].append("json_parse_failed")
    elif target == "markdown":
        candidate = _extract_markdown_block(cleaned_text)
        if not candidate:
            result["blocked_reasons"].append("target_structure_not_found")
        else:
            result["cleaned_text"] = candidate
            result["extracted_payload"] = candidate
            result["cleaning_applied"]["target_structure_extracted"] = True
    elif target in {"text", "plain", "plain_text"}:
        if not cleaned_text:
            result["blocked_reasons"].append("target_structure_not_found")
        else:
            result["extracted_payload"] = cleaned_text
            result["cleaning_applied"]["target_structure_extracted"] = True
    else:
        result["warnings"].append("unsupported_target_format")
        result["blocked_reasons"].append("target_format_not_supported")

    if result["blocked_reasons"]:
        result["post_processing_blocked"] = True
        result["warnings"].append("post_processing_failed")
    return result


def _post_processed_preview_metadata(
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_preview_output = metadata.get(
        "preview_output_raw_text",
        metadata.get("preview_advisory_summary"),
    )
    post_processing_result = _post_process_preview_output(
        raw_preview_output,
        target_format=_text(metadata.get("preview_output_target_format"), default="text", limit=40),
        enabled=_bool(metadata.get("preview_output_post_processing_enabled", True)),
    )
    post_processed_metadata = dict(metadata)
    if not post_processing_result["blocked_reasons"]:
        post_processed_metadata["preview_advisory_summary"] = _text(
            post_processing_result.get("cleaned_text"),
            limit=12000,
        )
    return post_processed_metadata, post_processing_result


def _combined_blocked_reasons(
    preview_packet: dict[str, Any],
    validator_result: dict[str, Any],
    output_post_processing: dict[str, Any] | None = None,
) -> list[str]:
    reasons: list[str] = []
    for source in (preview_packet, validator_result):
        for reason in _list(source.get("blocked_reasons")):
            _append_unique(reasons, reason)
    for reason in _list((output_post_processing or {}).get("blocked_reasons")):
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
    post_processed_metadata, output_post_processing = _post_processed_preview_metadata(metadata)
    preview_packet = build_zdoc_zbid_preview_packet(**_packet_payload(post_processed_metadata))
    validator_result = validate_zbid_preview_input(preview_packet)
    blocked_reasons = _combined_blocked_reasons(
        preview_packet,
        validator_result,
        output_post_processing,
    )

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
        "output_post_processing": output_post_processing,
        "cleaning_applied": output_post_processing["cleaning_applied"],
        "warnings": output_post_processing["warnings"],
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
