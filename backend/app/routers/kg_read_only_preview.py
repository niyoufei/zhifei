from __future__ import annotations

import os
from typing import Any, Mapping

from fastapi import APIRouter, Body

from backend.kg_read_only_preview_adapter import build_kg_read_only_preview


KG_READ_ONLY_PREVIEW_PATH = "/kg/read-only-preview"
KG_READ_ONLY_PREVIEW_ROUTE_NAME = "kg_read_only_preview"
KG_READ_ONLY_PREVIEW_FLAG = "ZDOC_KG_READ_ONLY_PREVIEW_ROUTE_ENABLED"
KG_READ_ONLY_PREVIEW_SOURCE = "zdoc_kg_read_only_preview_route_draft"
KG_READ_ONLY_PREVIEW_SOURCE_CODE = 1
KG_READ_ONLY_PREVIEW_ROUTE_CODE = 1
KG_READ_ONLY_PREVIEW_PATH_CODE = 1
KG_READ_ONLY_PREVIEW_FLAG_CODE = 1
ROUTE_STATUS_CODES = {
    "blocked": 0,
    "invalid": 1,
    "preview_only": 2,
    "disabled": 3,
}
KG_READ_ONLY_PREVIEW_ALLOWED_FIELDS = frozenset(
    {
        "manifest_entity",
        "registry_entity",
        "manual_trigger",
        "request_id",
        "real_kg_read_only",
        "authorized_target",
        "structure_read",
        "structural_profile",
        "structural_profile_only",
    }
)
KG_READ_ONLY_PREVIEW_REAL_KG_METADATA_FIELDS = (
    "contract_scope",
    "authorized_target",
    "target_policy",
    "read_policy",
    "value_output_policy",
    "content_read_performed",
    "json_parse_performed",
    "no_write",
    "no_evidence",
    "no_scoring",
    "no_rag",
    "no_generation",
    "no_export",
    "no_zbid_writeback",
    "allowlist_status",
    "exists",
    "is_file",
    "size_bytes",
    "mtime",
    "mode",
    "permission",
    "structure_read",
    "structure_read_only",
    "structure_summary",
    "structure_contract",
    "structural_profile",
    "structural_profile_only",
    "structural_profile_summary",
    "structural_profile_contract",
    "preview_only_response",
    "zdoc_preview_only_integration",
)
ROUTE_REASON_CODES = {
    "feature_flag_disabled": 10,
    "payload_required": 11,
    "illegal_field": 12,
    "manual_trigger_required": 13,
    "real_kg_read_only_required_for_authorized_target": 14,
    "real_kg_read_only_true_required": 15,
    "structure_read_true_required": 16,
    "structural_profile_true_required": 17,
    "structural_profile_only_true_required": 18,
    "structural_profile_required_for_structural_profile_only": 19,
    "real_kg_read_only_required_for_structural_profile": 20,
    "structure_read_required_for_structural_profile": 21,
    "authorized_target_required_for_structural_profile": 22,
    "real_kg_read_only_required_for_structure_read": 23,
    "authorized_target_required_for_structure_read": 24,
    "adapter_preview_ready": 25,
    "adapter_preview_blocked": 26,
    "manifest_and_registry_entity_dicts_required": 27,
}

router = APIRouter(tags=["KG Read Only Preview"])


def _feature_flag_enabled() -> bool:
    raw = str(os.environ.get(KG_READ_ONLY_PREVIEW_FLAG) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _base_response(
    *,
    ok: bool,
    enabled: bool,
    status: Any,
    reason: str,
    request_id: Any = None,
    detail: Any = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "ok": bool(ok),
        "enabled": bool(enabled),
        "status": _route_status_code(status),
        "reason": _route_reason_code(reason),
        "request_id": str(request_id or "").strip(),
        "source": KG_READ_ONLY_PREVIEW_SOURCE_CODE,
        "route_name": KG_READ_ONLY_PREVIEW_ROUTE_CODE,
        "endpoint_path": KG_READ_ONLY_PREVIEW_PATH_CODE,
        "feature_flag": KG_READ_ONLY_PREVIEW_FLAG_CODE,
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


def _route_reason_code(reason: str) -> int:
    return ROUTE_REASON_CODES.get(reason, 0)


def _route_status_code(status: Any) -> int:
    if isinstance(status, int):
        return status
    return ROUTE_STATUS_CODES.get(str(status), 0)


def _adapter_response_status(adapter_result: Mapping[str, Any]) -> Any:
    if "status" in adapter_result:
        return adapter_result["status"]
    return "invalid"


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
            reason="illegal_field",
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

    if (
        "authorized_target" in request
        and request.get("real_kg_read_only") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="real_kg_read_only_required_for_authorized_target",
            request_id=request_id,
        )

    if (
        "real_kg_read_only" in request
        and request.get("real_kg_read_only") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="real_kg_read_only_true_required",
            request_id=request_id,
        )

    if "structure_read" in request and request.get("structure_read") is not True:
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="structure_read_true_required",
            request_id=request_id,
        )

    if (
        "structural_profile" in request
        and request.get("structural_profile") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="structural_profile_true_required",
            request_id=request_id,
        )

    if (
        "structural_profile_only" in request
        and request.get("structural_profile_only") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="structural_profile_only_true_required",
            request_id=request_id,
        )

    if (
        request.get("structural_profile_only") is True
        and request.get("structural_profile") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="structural_profile_required_for_structural_profile_only",
            request_id=request_id,
        )

    if (
        request.get("structural_profile") is True
        and request.get("real_kg_read_only") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="real_kg_read_only_required_for_structural_profile",
            request_id=request_id,
        )

    if (
        request.get("structural_profile") is True
        and request.get("structure_read") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="structure_read_required_for_structural_profile",
            request_id=request_id,
        )

    if (
        request.get("structural_profile") is True
        and "authorized_target" not in request
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="authorized_target_required_for_structural_profile",
            request_id=request_id,
        )

    if (
        request.get("structure_read") is True
        and request.get("real_kg_read_only") is not True
    ):
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="real_kg_read_only_required_for_structure_read",
            request_id=request_id,
        )

    if request.get("structure_read") is True and "authorized_target" not in request:
        return _base_response(
            ok=False,
            enabled=True,
            status="blocked",
            reason="authorized_target_required_for_structure_read",
            request_id=request_id,
        )

    if request.get("real_kg_read_only") is True:
        adapter_result = build_kg_read_only_preview(
            {},
            {},
            manual_trigger=True,
            real_kg_read_only=True,
            real_kg_target=request.get("authorized_target"),
            feature_flag_enabled=True,
            structure_read=request.get("structure_read") is True,
            structural_profile=request.get("structural_profile") is True,
        )
        status = _adapter_response_status(adapter_result)
        ok = adapter_result.get("ok") is True
        response = _base_response(
            ok=ok,
            enabled=True,
            status=status,
            reason="adapter_preview_ready" if ok else "adapter_preview_blocked",
            request_id=request_id,
            detail=adapter_result,
        )
        response["adapter_status"] = status
        for field_name in KG_READ_ONLY_PREVIEW_REAL_KG_METADATA_FIELDS:
            if field_name in adapter_result:
                response[field_name] = adapter_result[field_name]
        return response

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
    status = _adapter_response_status(adapter_result)
    ok = adapter_result.get("ok") is True
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
