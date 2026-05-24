from __future__ import annotations

import os
from typing import Any, Mapping

from fastapi import APIRouter, Body

from backend.kg_read_only_preview_adapter import build_kg_read_only_preview


KG_READ_ONLY_PREVIEW_PATH = "/kg/read-only-preview"
KG_READ_ONLY_PREVIEW_ROUTE_NAME = "kg_read_only_preview"
KG_READ_ONLY_PREVIEW_FLAG = "ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED"
KG_READ_ONLY_PREVIEW_SOURCE = "zdoc_kg_read_only_preview_route_draft"
KG_READ_ONLY_PREVIEW_ALLOWED_FIELDS = frozenset(
    {
        "manifest_entity",
        "registry_entity",
        "manual_trigger",
        "request_id",
    }
)

router = APIRouter(tags=["KG Read Only Preview"])


def _feature_flag_enabled() -> bool:
    raw = str(os.environ.get(KG_READ_ONLY_PREVIEW_FLAG) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _base_response(
    *,
    ok: bool,
    enabled: bool,
    status: str,
    reason: str,
    request_id: Any = None,
    detail: Any = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "ok": bool(ok),
        "enabled": bool(enabled),
        "status": status,
        "reason": reason,
        "request_id": str(request_id or "").strip(),
        "source": KG_READ_ONLY_PREVIEW_SOURCE,
        "route_name": KG_READ_ONLY_PREVIEW_ROUTE_NAME,
        "endpoint_path": KG_READ_ONLY_PREVIEW_PATH,
        "feature_flag": KG_READ_ONLY_PREVIEW_FLAG,
        "default_off": True,
        "manual_trigger_required": True,
        "preview_only": True,
        "read_only": True,
        "no_write": True,
        "runtime_access": False,
        "route_registered": True,
        "kg_runtime_registered": False,
        "writeback_allowed": False,
        "output_write_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
        "rag_allowed": False,
        "prompt_registry_allowed": False,
        "system_instruction_registry_allowed": False,
        "knowledge_pack_load_allowed": False,
        "calls_generate_route": False,
        "calls_export_docx_route": False,
        "calls_review_apply_route": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "writes_document_body": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
        "calls_ollama": False,
        "calls_external_endpoint": False,
        "downloads_models": False,
        "pulls_models": False,
        "loads_knowledge_pack": False,
        "registers_manifest": False,
        "creates_registry": False,
    }
    if detail is not None:
        response["detail"] = detail
    return response


def _request_id(payload: Mapping[str, Any] | None) -> Any:
    if not isinstance(payload, Mapping):
        return None
    return payload.get("request_id")


@router.post(KG_READ_ONLY_PREVIEW_PATH)
async def kg_read_only_preview_route(
    request: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    request_id = _request_id(request)

    if not _feature_flag_enabled():
        return _base_response(
            ok=False,
            enabled=False,
            status="disabled",
            reason="feature_flag_disabled",
            request_id=request_id,
        )

    if not isinstance(request, dict):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="payload_required",
        )

    extra_fields = sorted(set(request) - KG_READ_ONLY_PREVIEW_ALLOWED_FIELDS)
    if extra_fields:
        return _base_response(
            ok=False,
            enabled=True,
            status="invalid",
            reason=f"illegal_field:{extra_fields[0]}",
            request_id=request_id,
        )

    if request.get("manual_trigger") is not True:
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="manual_trigger_required",
            request_id=request_id,
        )

    manifest_entity = request.get("manifest_entity")
    registry_entity = request.get("registry_entity")
    if not isinstance(manifest_entity, dict) or not isinstance(registry_entity, dict):
        return _base_response(
            ok=False,
            enabled=True,
            status="invalid",
            reason="manifest_and_registry_entity_dicts_required",
            request_id=request_id,
        )

    adapter_result = build_kg_read_only_preview(
        manifest_entity,
        registry_entity,
        manual_trigger=True,
    )
    status = str(adapter_result.get("status") or "invalid")
    ok = status == "preview_only"
    response = _base_response(
        ok=ok,
        enabled=True,
        status=status,
        reason="adapter_preview_ready" if ok else "adapter_preview_blocked",
        request_id=request_id,
        detail=adapter_result,
    )
    response["adapter_status"] = status
    return response
