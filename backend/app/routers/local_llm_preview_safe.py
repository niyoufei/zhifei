from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Body

from backend.zhifei_autoplan.ollama_preview import (
    LOCAL_LLM_PREVIEW_FLAG,
    run_zdoc_local_llm_preview_safe_service_entry,
)


SAFE_ENDPOINT_PATH = "/local-llm/preview-safe"
SAFE_ENDPOINT_SOURCE = "zdoc_local_llm_preview_isolated_safe_endpoint_fake"
SAFE_ENDPOINT_ALLOWED_FIELDS = frozenset(
    {
        "context_summary",
        "request_id",
        "section_text",
        "section_title",
    }
)
SAFE_ENDPOINT_FORMAL_OUTPUT_FIELDS = frozenset(
    {
        "content",
        "docx",
        "docx_path",
        "download_url",
        "export_path",
        "generated_sections",
        "job",
        "job_id",
        "json",
        "json_path",
        "markdown",
        "markdown_path",
        "output",
        "output_path",
        "result_path",
    }
)


router = APIRouter(tags=["Local LLM Preview Safe"])


def _safe_endpoint_flag_enabled() -> bool:
    raw = str(os.environ.get(LOCAL_LLM_PREVIEW_FLAG) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _safe_endpoint_safety() -> dict[str, bool]:
    return {
        "isolated_safe_endpoint": True,
        "safe_endpoint_registered": True,
        "service_started": False,
        "fake_only": True,
        "default_off": True,
        "manual_trigger": True,
        "preview_only": True,
        "no_write": True,
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
        "listens_on_0_0_0_0": False,
    }


def _safe_endpoint_base_response(
    *,
    ok: bool,
    enabled: bool,
    status: str,
    advisory: str = "",
    suggestions: list[str] | None = None,
    warning: str | None = None,
    error_type: str | None = None,
    reason: str | None = None,
    request_id: Any = None,
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "enabled": bool(enabled),
        "status": status,
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "source": SAFE_ENDPOINT_SOURCE,
        "entry_type": "isolated_safe_endpoint",
        "entry_source": SAFE_ENDPOINT_SOURCE,
        "endpoint_path": SAFE_ENDPOINT_PATH,
        "safe_endpoint_registered": True,
        "service_started": False,
        "fake_only": True,
        "advisory": advisory,
        "suggestions": list(suggestions or []),
        "warning": warning,
        "error_type": error_type,
        "reason": reason,
        "request_id": str(request_id or "").strip(),
        "calls_generate_route": False,
        "calls_export_docx_route": False,
        "calls_review_apply_route": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
        "calls_ollama": False,
        "calls_external_model_api": False,
        "safety": _safe_endpoint_safety(),
    }


def _safe_endpoint_failure(
    *,
    enabled: bool,
    error_type: str,
    reason: str,
    request_id: Any = None,
) -> dict[str, Any]:
    return _safe_endpoint_base_response(
        ok=False,
        enabled=enabled,
        status="failure",
        error_type=error_type,
        reason=reason,
        request_id=request_id,
    )


def _clean_endpoint_text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _build_safe_helper_payload(request: dict[str, Any]) -> dict[str, Any]:
    context_summary = _clean_endpoint_text(request.get("context_summary"), limit=1000)
    request_id = _clean_endpoint_text(request.get("request_id"), limit=120)
    source_context: dict[str, Any] = {}
    if context_summary:
        source_context["context_summary"] = context_summary
    if request_id:
        source_context["request_id"] = request_id
    return {
        "section_title": _clean_endpoint_text(request.get("section_title"), limit=200),
        "section_text": _clean_endpoint_text(request.get("section_text")),
        "review_focus": context_summary,
        "preview_type": "safe_endpoint_preview",
        "source_context": source_context,
        "trigger": "manual",
        "caller": "isolated_safe_endpoint",
    }


def _with_safe_endpoint_metadata(result: dict[str, Any], *, request_id: Any = None) -> dict[str, Any]:
    out = dict(result)
    out["source"] = SAFE_ENDPOINT_SOURCE
    out["entry_type"] = "isolated_safe_endpoint"
    out["entry_source"] = SAFE_ENDPOINT_SOURCE
    out["endpoint_path"] = SAFE_ENDPOINT_PATH
    out["safe_endpoint_registered"] = True
    out["service_started"] = False
    out["fake_only"] = True
    out["preview_only"] = True
    out["no_write"] = True
    out["affects_generation"] = False
    out["affects_export"] = False
    out["affects_zbid_writeback"] = False
    out["request_id"] = _clean_endpoint_text(request_id, limit=120)
    out["calls_generate_route"] = False
    out["calls_export_docx_route"] = False
    out["calls_review_apply_route"] = False
    out["triggers_generation_chain"] = False
    out["triggers_export_chain"] = False
    out["writes_output"] = False
    out["writes_job"] = False
    out["writes_export"] = False
    out["calls_ollama"] = False
    out["calls_external_model_api"] = False
    safety = dict(out.get("safety") if isinstance(out.get("safety"), dict) else {})
    safety.update(_safe_endpoint_safety())
    out["safety"] = safety
    for field in SAFE_ENDPOINT_FORMAL_OUTPUT_FIELDS:
        out.pop(field, None)
    return out


@router.post(SAFE_ENDPOINT_PATH)
async def local_llm_preview_safe_endpoint(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    if not _safe_endpoint_flag_enabled():
        request_id = request.get("request_id") if isinstance(request, dict) else None
        return _safe_endpoint_base_response(
            ok=False,
            enabled=False,
            status="disabled",
            warning="local_llm_preview_safe_endpoint_disabled",
            reason="feature_flag_disabled",
            request_id=request_id,
        )

    if not isinstance(request, dict):
        return _safe_endpoint_failure(
            enabled=True,
            error_type="missing_input",
            reason="payload_required",
        )

    extra_fields = sorted(set(request) - SAFE_ENDPOINT_ALLOWED_FIELDS)
    if extra_fields:
        return _safe_endpoint_failure(
            enabled=True,
            error_type="illegal_field",
            reason=f"illegal_field:{extra_fields[0]}",
            request_id=request.get("request_id"),
        )

    if "section_text" not in request:
        return _safe_endpoint_failure(
            enabled=True,
            error_type="missing_field",
            reason="missing_field:section_text",
            request_id=request.get("request_id"),
        )

    if not _clean_endpoint_text(request.get("section_text")):
        return _safe_endpoint_failure(
            enabled=True,
            error_type="empty_text",
            reason="section_text_required",
            request_id=request.get("request_id"),
        )

    payload = _build_safe_helper_payload(request)
    result = run_zdoc_local_llm_preview_safe_service_entry(payload)
    if not isinstance(result, dict):
        return _safe_endpoint_failure(
            enabled=True,
            error_type="invalid_safe_helper_response",
            reason="safe_helper_response_must_be_dict",
            request_id=request.get("request_id"),
        )

    forbidden_fields = sorted(set(result) & SAFE_ENDPOINT_FORMAL_OUTPUT_FIELDS)
    if forbidden_fields:
        return _safe_endpoint_failure(
            enabled=True,
            error_type="forbidden_safe_helper_field",
            reason=f"forbidden_field:{forbidden_fields[0]}",
            request_id=request.get("request_id"),
        )

    return _with_safe_endpoint_metadata(result, request_id=request.get("request_id"))
