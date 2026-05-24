"""Minimal draft adapter for KG read-only preview payloads.

This module is intentionally isolated from ZDoc runtime chains. It provides
pure functions only: no file IO, no route registration, no service calls, no
model calls, no retrieval, and no writeback.
"""

from typing import Any, Mapping, Optional


BLOCKED_STATUS = "blocked"
INVALID_STATUS = "invalid"
PREVIEW_STATUS = "preview_only"

CONTRACT_SOURCE = "kg_runtime_28_29_adapter_contract_mapping_design"
CONTRACT_SCOPE = "top-level plus first/second structural levels only"
REAL_KG_ROUTE_READ_ONLY_SOURCE = "kg_runtime_39_real_kg_route_read_only_draft"
REAL_KG_ROUTE_READ_ONLY_CONTRACT_SCOPE = (
    "route-level real-KG metadata-only read-only contract"
)
AUTHORIZED_REAL_KG_TARGET = "知识图谱/ZF-KG-12-Municipal-Bridge.json"
REAL_KG_TARGET_POLICY = "single_authorized_target_identifier_metadata_only_no_io"
REAL_KG_READ_POLICY = "no_file_io_no_content_read_no_json_parse"
MODULE_CONTRACT_COUNT = 44
ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT = 69
TOTAL_STRUCTURAL_PATH_COUNT = 180
BLOCKED_STRUCTURAL_PATH_COUNT = (
    TOTAL_STRUCTURAL_PATH_COUNT - ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT
)
VALUE_OUTPUT_POLICY = (
    "contract_metadata_only_no_entity_knowledge_prompt_instruction_"
    "evidence_scoring_generation_or_rag_text"
)

OUTPUT_FIELD_WHITELIST = (
    "ok",
    "enabled",
    "status",
    "reason",
    "source",
    "contract_scope",
    "authorized_target",
    "target_policy",
    "read_policy",
    "module_contract_count",
    "adapter_structural_path_whitelist_count",
    "allowed_path_count",
    "blocked_path_count",
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
)

ALLOWED_STRUCTURAL_PATH_POLICY = (
    "top_level_structure",
    "first_level_structure",
    "second_level_structure",
    "path_presence",
    "type_summary",
    "count_summary",
    "field_type_set_summary",
)

BLOCKED_STRUCTURAL_PATH_POLICY = (
    "unknown_paths",
    "real_business_body_values",
    "entity_body_content",
    "knowledge_entry_body_content",
    "prompt_content",
    "system_instruction_content",
    "evidence_content",
    "scoring_content",
    "generated_document_body_content",
    "generate_ready_content",
    "rag_ready_text_blocks",
    "prompt_registry_content",
    "system_instruction_registry_content",
)

RUNTIME_BOUNDARY_FLAGS = {
    "default_off": True,
    "manual_trigger_required": True,
    "read_only": True,
    "no_write": True,
    "no_evidence": True,
    "no_scoring": True,
    "no_rag": True,
    "no_generation": True,
    "no_export": True,
    "no_zbid_writeback": True,
    "no_ollama": True,
    "no_model_upgrade": True,
    "no_service_auto_run": True,
    "no_ci_auto_run": True,
}


def build_kg_read_only_preview(
    manifest_entity: Mapping[str, Any],
    registry_entity: Mapping[str, Any],
    manual_trigger: bool = False,
    *,
    real_kg_read_only: bool = False,
    real_kg_target: Optional[str] = None,
) -> dict[str, Any]:
    """Build a disabled KG read-only preview payload from supplied dictionaries."""

    if manual_trigger is not True:
        return _blocked_response(
            reason="manual_trigger_required",
        )

    if real_kg_read_only is True:
        return _real_kg_route_read_only_response(real_kg_target)

    manifest_check = _validate_disabled_entity(
        manifest_entity,
        required_false_fields=(
            "enabled",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ),
        entity_name="manifest_entity",
    )
    registry_check = _validate_disabled_entity(
        registry_entity,
        required_false_fields=(
            "enabled",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ),
        entity_name="registry_entity",
    )

    if not manifest_check["ok"] or not registry_check["ok"]:
        return _invalid_response(
            reason="disabled_entity_validation_failed",
        )

    return _contract_mapping_response(
        status=PREVIEW_STATUS,
        reason="adapter_contract_mapping_draft_static_only",
        ok=True,
    )


def _validate_disabled_entity(
    entity: Mapping[str, Any],
    required_false_fields: tuple[str, ...],
    entity_name: str,
) -> dict[str, Any]:
    missing_fields = _missing_fields(
        entity,
        required_false_fields + ("registration_status",),
    )
    non_disabled_fields = tuple(
        field for field in required_false_fields if entity.get(field) is not False
    )
    registration_status = entity.get("registration_status")

    if missing_fields or non_disabled_fields or registration_status != "not_registered":
        return {
            "ok": False,
            "entity": entity_name,
            "missing_fields": missing_fields,
            "non_disabled_fields": non_disabled_fields,
            "registration_status": registration_status,
            "required_registration_status": "not_registered",
        }

    return {
        "ok": True,
        "entity": entity_name,
        "detail": "disabled_state_valid",
    }


def _missing_fields(
    entity: Mapping[str, Any],
    field_names: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(field for field in field_names if field not in entity)


def _blocked_response(reason: str) -> dict[str, Any]:
    return _contract_mapping_response(
        status=BLOCKED_STATUS,
        reason=reason,
        ok=False,
    )


def _invalid_response(reason: str) -> dict[str, Any]:
    return _contract_mapping_response(
        status=INVALID_STATUS,
        reason=reason,
        ok=False,
    )


def _real_kg_route_read_only_response(
    real_kg_target: Optional[str],
) -> dict[str, Any]:
    target = str(real_kg_target or "").strip()
    if target != AUTHORIZED_REAL_KG_TARGET:
        reason = "authorized_real_kg_target_required"
        if target:
            reason = "unauthorized_real_kg_target"
        return _real_kg_contract_response(
            status=BLOCKED_STATUS,
            reason=reason,
            ok=False,
        )

    return _real_kg_contract_response(
        status=PREVIEW_STATUS,
        reason="real_kg_route_read_only_metadata_only",
        ok=True,
    )


def _real_kg_contract_response(
    status: str,
    reason: str,
    ok: bool,
) -> dict[str, Any]:
    response = _contract_mapping_response(
        status=status,
        reason=reason,
        ok=ok,
    )
    response.update(
        {
            "source": REAL_KG_ROUTE_READ_ONLY_SOURCE,
            "contract_scope": REAL_KG_ROUTE_READ_ONLY_CONTRACT_SCOPE,
            "authorized_target": AUTHORIZED_REAL_KG_TARGET,
            "target_policy": REAL_KG_TARGET_POLICY,
            "read_policy": REAL_KG_READ_POLICY,
            "value_output_policy": VALUE_OUTPUT_POLICY,
            "content_read_performed": False,
            "json_parse_performed": False,
            "no_write": RUNTIME_BOUNDARY_FLAGS["no_write"],
            "no_evidence": RUNTIME_BOUNDARY_FLAGS["no_evidence"],
            "no_scoring": RUNTIME_BOUNDARY_FLAGS["no_scoring"],
            "no_rag": RUNTIME_BOUNDARY_FLAGS["no_rag"],
            "no_generation": RUNTIME_BOUNDARY_FLAGS["no_generation"],
            "no_export": RUNTIME_BOUNDARY_FLAGS["no_export"],
            "no_zbid_writeback": RUNTIME_BOUNDARY_FLAGS["no_zbid_writeback"],
        }
    )
    return _whitelisted_response(response)


def _contract_mapping_response(
    status: str,
    reason: str,
    ok: bool,
) -> dict[str, Any]:
    response = {
        "ok": ok,
        "enabled": False,
        "status": status,
        "reason": reason,
        "source": CONTRACT_SOURCE,
        "contract_scope": CONTRACT_SCOPE,
        "module_contract_count": MODULE_CONTRACT_COUNT,
        "adapter_structural_path_whitelist_count": (
            ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT
        ),
        "allowed_path_count": ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT,
        "blocked_path_count": BLOCKED_STRUCTURAL_PATH_COUNT,
        "value_output_policy": VALUE_OUTPUT_POLICY,
        "no_write": RUNTIME_BOUNDARY_FLAGS["no_write"],
        "no_evidence": RUNTIME_BOUNDARY_FLAGS["no_evidence"],
        "no_scoring": RUNTIME_BOUNDARY_FLAGS["no_scoring"],
        "no_rag": RUNTIME_BOUNDARY_FLAGS["no_rag"],
        "no_generation": RUNTIME_BOUNDARY_FLAGS["no_generation"],
        "no_export": RUNTIME_BOUNDARY_FLAGS["no_export"],
        "no_zbid_writeback": RUNTIME_BOUNDARY_FLAGS["no_zbid_writeback"],
    }
    return _whitelisted_response(response)


def _whitelisted_response(response: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field_name: response[field_name]
        for field_name in OUTPUT_FIELD_WHITELIST
        if field_name in response
    }
