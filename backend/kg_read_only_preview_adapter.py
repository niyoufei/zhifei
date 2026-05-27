"""Minimal draft adapter for KG read-only preview payloads.

This module is intentionally isolated from ZDoc runtime chains. It performs
only controlled single-target metadata or structure-only inspection when
explicitly gated: no import-time reads, no service-start reads, no route
registration, no service calls, no model calls, no retrieval, and no writeback.
"""

import json
from pathlib import Path
from stat import S_IMODE, S_ISREG
from typing import Any, Mapping, Optional

from backend.kg_content_safe_output_contract import (
    build_content_safe_output_contract_mapping,
    build_preview_only_payload,
    build_preview_only_response_integration_payload,
    build_zdoc_preview_only_payload,
    classify_content_safe_fields,
)


BLOCKED_STATUS = "blocked"
INVALID_STATUS = "invalid"
PREVIEW_STATUS = "preview_only"
ADAPTER_STATUS_CODES = {
    BLOCKED_STATUS: 0,
    INVALID_STATUS: 1,
    PREVIEW_STATUS: 2,
}

CONTRACT_SOURCE = "kg_runtime_28_29_adapter_contract_mapping_design"
CONTRACT_SOURCE_CODE = 1
CONTRACT_SCOPE = 0
REAL_KG_ROUTE_READ_ONLY_SOURCE = "kg_runtime_39_real_kg_route_read_only_draft"
REAL_KG_ROUTE_READ_ONLY_SOURCE_CODE = 2
REAL_KG_ROUTE_READ_ONLY_CONTRACT_SCOPE = 1
REAL_KG_STRUCTURE_CONTRACT_SCOPE = 2
REAL_KG_STRUCTURAL_PROFILE_CONTRACT_SCOPE = 3
AUTHORIZED_REAL_KG_TARGET = "知识图谱/ZF-KG-12-Municipal-Bridge.json"
AUTHORIZED_REAL_KG_TARGET_CODE = 1
AUTHORIZED_REAL_KG_TARGET_PATH = (
    Path(__file__).parent.parent / AUTHORIZED_REAL_KG_TARGET
)
AUTHORIZED_REAL_KG_FILE_STAT_ALLOWLIST_STATUS = 1
AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS = 2
AUTHORIZED_REAL_KG_STRUCTURAL_PROFILE_ALLOWLIST_STATUS = 3
BLOCKED_ALLOWLIST_STATUS = 0
UNAVAILABLE_ALLOWLIST_STATUS = 4
REAL_KG_TARGET_POLICY = 0
REAL_KG_STRUCTURE_TARGET_POLICY = 1
REAL_KG_STRUCTURAL_PROFILE_TARGET_POLICY = 2
REAL_KG_READ_POLICY = 0
REAL_KG_STRUCTURE_READ_POLICY = 1
REAL_KG_STRUCTURAL_PROFILE_READ_POLICY = 2
MODULE_CONTRACT_COUNT = 44
ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT = 69
TOTAL_STRUCTURAL_PATH_COUNT = 180
BLOCKED_STRUCTURAL_PATH_COUNT = (
    TOTAL_STRUCTURAL_PATH_COUNT - ADAPTER_STRUCTURAL_PATH_WHITELIST_COUNT
)
VALUE_OUTPUT_POLICY = 0
STRUCTURE_VALUE_OUTPUT_POLICY = 0
STRUCTURE_SUMMARY_MAX_DEPTH = 4
STRUCTURE_SUMMARY_MAX_PATHS = 80
STRUCTURAL_PROFILE_MAX_MODULE_CANDIDATES = 40
CONTENT_SAFE_OUTPUT_CONTRACT_MAPPING = build_content_safe_output_contract_mapping()
PREVIEW_ONLY_ADAPTER_MAPPING_CONTRACT = classify_content_safe_fields()
STRUCTURE_SUMMARY_FIELD_WHITELIST = (
    "top_level_type",
    "top_level_key_names",
    "top_level_key_count",
    "dict_count",
    "list_count",
    "null_count",
    "scalar_type_counts",
    "selected_structure_paths",
    "list_lengths",
    "field_type_sets",
    "max_depth_limited",
    "authorized_target",
    "allowlist_status",
)
STRUCTURE_SUMMARY_FIELD_CODES = tuple(
    range(1, len(STRUCTURE_SUMMARY_FIELD_WHITELIST) + 1)
)
STRUCTURAL_PROFILE_SCOPE = 0
STRUCTURAL_PROFILE_SUMMARY_FIELD_WHITELIST = (
    "authorized_target",
    "allowlist_status",
    "profile_enabled",
    "profile_scope",
    "max_depth_limited",
    "path_count",
    "path_type_counts",
    "depth_histogram",
    "field_name_counts",
    "field_type_sets",
    "list_length_buckets",
    "dict_key_count_buckets",
    "module_name_candidates",
    "redaction_policy",
)
STRUCTURAL_PROFILE_SUMMARY_FIELD_CODES = tuple(
    range(1, len(STRUCTURAL_PROFILE_SUMMARY_FIELD_WHITELIST) + 1)
)
STRUCTURAL_PROFILE_REDACTION_POLICY = 0
ADAPTER_REASON_CODES = {
    "manual_trigger_required": 10,
    "disabled_entity_validation_failed": 11,
    "adapter_contract_mapping_draft_static_only": 12,
    "authorized_real_kg_target_required": 20,
    "unauthorized_real_kg_target": 21,
    "feature_flag_required_for_structural_profile": 22,
    "manual_trigger_required_for_structural_profile": 23,
    "real_kg_read_only_required_for_structural_profile": 24,
    "structure_read_required_for_structural_profile": 25,
    "feature_flag_required_for_structure_read": 26,
    "real_kg_structural_profile_route_draft": 27,
    "real_kg_structure_read_route_draft": 28,
    "real_kg_route_read_only_metadata_only": 29,
}
JSON_STRUCTURE_TYPE_CODE_BY_NAME = {
    "dict": 1,
    "list": 2,
    "null": 3,
    "bool": 4,
    "str": 5,
    "int": 6,
    "float": 7,
    "other": 8,
}

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
    feature_flag_enabled: bool = False,
    structure_read: bool = False,
    structural_profile: bool = False,
) -> dict[str, Any]:
    """Build a disabled KG read-only preview payload from supplied dictionaries."""

    if manual_trigger is not True:
        return _blocked_response(
            reason="manual_trigger_required",
        )

    if real_kg_read_only is True:
        return _real_kg_route_read_only_response(
            real_kg_target,
            manual_trigger=manual_trigger,
            real_kg_read_only=real_kg_read_only,
            feature_flag_enabled=feature_flag_enabled,
            structure_read=structure_read,
            structural_profile=structural_profile,
        )

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


def build_preview_only_adapter_mapping(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a preview-only mapping from already content-safe adapter fields."""

    return build_preview_only_payload(content_safe_response)


def _build_preview_only_response_integration(
    content_safe_response: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    enriched_response = dict(content_safe_response)
    enriched_response.update(_preview_only_audit_fields(enriched_response, context))
    adapter_mapping = build_preview_only_adapter_mapping(enriched_response)
    enriched_response["overlap_check_result"] = _preview_only_overlap_check_result(
        adapter_mapping
    )
    return build_preview_only_response_integration_payload(enriched_response)


def build_zdoc_preview_only_adapter_payload(
    content_safe_response: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Prepare an already content-safe preview response for ZDoc internal use."""

    enriched_response = dict(content_safe_response)
    enriched_response.update(_preview_only_audit_fields(enriched_response, context))
    adapter_mapping = build_preview_only_adapter_mapping(enriched_response)
    enriched_response["overlap_check_result"] = _preview_only_overlap_check_result(
        adapter_mapping
    )
    return build_zdoc_preview_only_payload(enriched_response)


def _preview_only_audit_fields(
    content_safe_response: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, int]:
    feature_flag_enabled = context.get("feature_flag_enabled") is True
    manual_trigger = context.get("manual_trigger") is True
    real_kg_read_only = context.get("real_kg_read_only") is True
    structure_read = context.get("structure_read") is True
    structural_profile = context.get("structural_profile") is True
    authorized_target = context.get("authorized_target")
    authorized_target_hit = authorized_target == AUTHORIZED_REAL_KG_TARGET
    allowlist_status = _preview_only_allowlist_status(content_safe_response)
    validation_result = all(
        (
            feature_flag_enabled,
            manual_trigger,
            real_kg_read_only,
            structure_read,
            structural_profile,
            authorized_target_hit,
            allowlist_status > BLOCKED_ALLOWLIST_STATUS,
        )
    )

    adapter_contract_code = PREVIEW_ONLY_ADAPTER_MAPPING_CONTRACT.get("source")
    if not isinstance(adapter_contract_code, int) or isinstance(
        adapter_contract_code,
        bool,
    ):
        adapter_contract_code = 0

    return {
        "feature_flag_status": _preview_only_status_code(feature_flag_enabled),
        "manual_trigger_status": _preview_only_status_code(manual_trigger),
        "real_kg_read_only_status": _preview_only_status_code(real_kg_read_only),
        "authorized_target_hit_status": _preview_only_status_code(
            authorized_target_hit
        ),
        "allowlist_status": allowlist_status,
        "route_contract_code": REAL_KG_ROUTE_READ_ONLY_SOURCE_CODE,
        "adapter_contract_code": adapter_contract_code,
        "validation_result": _preview_only_status_code(validation_result),
    }


def _preview_only_allowlist_status(
    content_safe_response: Mapping[str, Any],
) -> int:
    for contract_field in (
        "structural_profile_contract",
        "structure_contract",
    ):
        contract = content_safe_response.get(contract_field)
        if not isinstance(contract, Mapping):
            continue
        allowlist_status = contract.get("allowlist_status")
        if (
            isinstance(allowlist_status, int)
            and not isinstance(allowlist_status, bool)
            and allowlist_status >= 0
        ):
            return allowlist_status
    return BLOCKED_ALLOWLIST_STATUS


def _preview_only_status_code(value: bool) -> int:
    return 1 if value is True else 0


def _preview_only_overlap_check_result(
    adapter_mapping: Mapping[str, Any],
) -> int:
    preview_only = adapter_mapping.get("preview_only")
    prohibited = adapter_mapping.get("prohibited")
    prohibited_fields: Any = ()
    if isinstance(prohibited, Mapping):
        prohibited_fields = prohibited.get("fields")

    preview_field_names = _collect_mapping_field_names(preview_only)
    prohibited_field_names = {
        field_name
        for field_name in prohibited_fields
        if isinstance(field_name, str)
    } if isinstance(prohibited_fields, (list, tuple)) else set()
    return 0 if preview_field_names & prohibited_field_names else 1


def _collect_mapping_field_names(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        field_names: set[str] = set()
        for key, child in value.items():
            if isinstance(key, str):
                field_names.add(key)
            field_names.update(_collect_mapping_field_names(child))
        return field_names

    if isinstance(value, (list, tuple)):
        field_names = set()
        for child in value:
            field_names.update(_collect_mapping_field_names(child))
        return field_names

    return set()


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
    *,
    manual_trigger: bool,
    real_kg_read_only: bool,
    feature_flag_enabled: bool,
    structure_read: bool,
    structural_profile: bool,
) -> dict[str, Any]:
    target = real_kg_target if isinstance(real_kg_target, str) else ""
    if target != AUTHORIZED_REAL_KG_TARGET:
        reason = "authorized_real_kg_target_required"
        if target:
            reason = "unauthorized_real_kg_target"
        return _real_kg_contract_response(
            status=BLOCKED_STATUS,
            reason=reason,
            ok=False,
        )

    if structural_profile is True:
        if feature_flag_enabled is not True:
            return _real_kg_contract_response(
                status=BLOCKED_STATUS,
                reason="feature_flag_required_for_structural_profile",
                ok=False,
            )
        if manual_trigger is not True:
            return _real_kg_contract_response(
                status=BLOCKED_STATUS,
                reason="manual_trigger_required_for_structural_profile",
                ok=False,
            )
        if real_kg_read_only is not True:
            return _real_kg_contract_response(
                status=BLOCKED_STATUS,
                reason="real_kg_read_only_required_for_structural_profile",
                ok=False,
            )
        if structure_read is not True:
            return _real_kg_contract_response(
                status=BLOCKED_STATUS,
                reason="structure_read_required_for_structural_profile",
                ok=False,
            )

    if structure_read is True:
        if feature_flag_enabled is not True:
            return _real_kg_contract_response(
                status=BLOCKED_STATUS,
                reason="feature_flag_required_for_structure_read",
                ok=False,
            )

        structure_summary = _authorized_real_kg_structure_summary(
            authorized_target=target,
            manual_trigger=manual_trigger,
            real_kg_read_only=real_kg_read_only,
            feature_flag_enabled=feature_flag_enabled,
            structure_read=structure_read,
        )
        if structural_profile is True:
            structure_metadata = {
                "structure_read": True,
                "structure_read_only": True,
                "structure_contract": _real_kg_structure_contract(),
                "structure_summary": structure_summary,
                "structural_profile": True,
                "structural_profile_only": True,
                "content_read_performed": True,
                "json_parse_performed": True,
                "structural_profile_contract": (
                    _real_kg_structural_profile_contract()
                ),
                "structural_profile_summary": (
                    _build_structural_profile_summary_from_structure_summary(
                        structure_summary,
                        authorized_target=target,
                    )
                ),
            }
            return _real_kg_contract_response(
                status=PREVIEW_STATUS,
                reason="real_kg_structural_profile_route_draft",
                ok=True,
                target_policy=REAL_KG_STRUCTURAL_PROFILE_TARGET_POLICY,
                read_policy=REAL_KG_STRUCTURAL_PROFILE_READ_POLICY,
                structure_metadata=structure_metadata,
                preview_only_response_context={
                    "feature_flag_enabled": feature_flag_enabled,
                    "manual_trigger": manual_trigger,
                    "real_kg_read_only": real_kg_read_only,
                    "authorized_target": target,
                    "structure_read": structure_read,
                    "structural_profile": structural_profile,
                },
            )

        return _real_kg_contract_response(
            status=PREVIEW_STATUS,
            reason="real_kg_structure_read_route_draft",
            ok=True,
            target_policy=REAL_KG_STRUCTURE_TARGET_POLICY,
            read_policy=REAL_KG_STRUCTURE_READ_POLICY,
            structure_metadata={
                "structure_read": True,
                "structure_read_only": True,
                "content_read_performed": True,
                "json_parse_performed": True,
                "structure_contract": _real_kg_structure_contract(),
                "structure_summary": structure_summary,
            },
        )

    return _real_kg_contract_response(
        status=PREVIEW_STATUS,
        reason="real_kg_route_read_only_metadata_only",
        ok=True,
        file_stat_metadata=_authorized_real_kg_file_stat_metadata(
            authorized_target=target,
            manual_trigger=manual_trigger,
            real_kg_read_only=real_kg_read_only,
            feature_flag_enabled=feature_flag_enabled,
        ),
    )


def _real_kg_contract_response(
    status: str,
    reason: str,
    ok: bool,
    file_stat_metadata: Optional[Mapping[str, Any]] = None,
    structure_metadata: Optional[Mapping[str, Any]] = None,
    target_policy: Optional[int] = None,
    read_policy: Optional[int] = None,
    preview_only_response_context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    response = _contract_mapping_response(
        status=status,
        reason=reason,
        ok=ok,
    )
    response.update(
        {
            "source": REAL_KG_ROUTE_READ_ONLY_SOURCE_CODE,
            "contract_scope": REAL_KG_ROUTE_READ_ONLY_CONTRACT_SCOPE,
            "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
            "target_policy": (
                REAL_KG_TARGET_POLICY if target_policy is None else target_policy
            ),
            "read_policy": REAL_KG_READ_POLICY if read_policy is None else read_policy,
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
    if file_stat_metadata:
        response.update(file_stat_metadata)
    if structure_metadata:
        response.update(structure_metadata)
    if preview_only_response_context:
        response["preview_only_response"] = _build_preview_only_response_integration(
            response,
            preview_only_response_context,
        )
        response["zdoc_preview_only_integration"] = (
            build_zdoc_preview_only_adapter_payload(
                response,
                preview_only_response_context,
            )
        )
    return _whitelisted_response(response)


def _authorized_real_kg_file_stat_metadata(
    *,
    authorized_target: str,
    manual_trigger: bool,
    real_kg_read_only: bool,
    feature_flag_enabled: bool,
) -> dict[str, Any]:
    if (
        feature_flag_enabled is not True
        or manual_trigger is not True
        or real_kg_read_only is not True
        or authorized_target != AUTHORIZED_REAL_KG_TARGET
    ):
        return {}

    try:
        stat_result = AUTHORIZED_REAL_KG_TARGET_PATH.stat()
    except OSError:
        return {
            "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
            "allowlist_status": AUTHORIZED_REAL_KG_FILE_STAT_ALLOWLIST_STATUS,
            "exists": False,
            "is_file": False,
            "size_bytes": None,
            "mtime": None,
            "mode": None,
            "permission": None,
        }

    mode = stat_result.st_mode
    return {
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": AUTHORIZED_REAL_KG_FILE_STAT_ALLOWLIST_STATUS,
        "exists": True,
        "is_file": S_ISREG(mode),
        "size_bytes": stat_result.st_size,
        "mtime": int(stat_result.st_mtime),
        "mode": format(mode, "o"),
        "permission": format(S_IMODE(mode), "03o"),
    }


def _real_kg_structure_contract() -> dict[str, Any]:
    return {
        "contract_scope": REAL_KG_STRUCTURE_CONTRACT_SCOPE,
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS,
        "target_policy": 0,
        "feature_flag_required": True,
        "manual_trigger_required": True,
        "real_kg_read_only_required": True,
        "structure_read_required": True,
        "summary_field_whitelist": STRUCTURE_SUMMARY_FIELD_CODES,
        "value_output_policy": 0,
        "scalar_policy": 0,
        "list_policy": 0,
        "dict_policy": 0,
        "no_evidence": RUNTIME_BOUNDARY_FLAGS["no_evidence"],
        "no_scoring": RUNTIME_BOUNDARY_FLAGS["no_scoring"],
        "no_rag": RUNTIME_BOUNDARY_FLAGS["no_rag"],
        "no_generation": RUNTIME_BOUNDARY_FLAGS["no_generation"],
        "no_export": RUNTIME_BOUNDARY_FLAGS["no_export"],
        "no_zbid_writeback": RUNTIME_BOUNDARY_FLAGS["no_zbid_writeback"],
    }


def _real_kg_structural_profile_contract() -> dict[str, Any]:
    return {
        "contract_scope": REAL_KG_STRUCTURAL_PROFILE_CONTRACT_SCOPE,
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": AUTHORIZED_REAL_KG_STRUCTURAL_PROFILE_ALLOWLIST_STATUS,
        "target_policy": 0,
        "feature_flag_required": True,
        "manual_trigger_required": True,
        "real_kg_read_only_required": True,
        "structure_read_required": True,
        "structural_profile_required": True,
        "summary_field_whitelist": STRUCTURAL_PROFILE_SUMMARY_FIELD_CODES,
        "profile_scope": STRUCTURAL_PROFILE_SCOPE,
        "redaction_policy": STRUCTURAL_PROFILE_REDACTION_POLICY,
        "scalar_policy": 0,
        "list_policy": 0,
        "dict_policy": 0,
        "module_name_policy": 0,
        "no_evidence": RUNTIME_BOUNDARY_FLAGS["no_evidence"],
        "no_scoring": RUNTIME_BOUNDARY_FLAGS["no_scoring"],
        "no_rag": RUNTIME_BOUNDARY_FLAGS["no_rag"],
        "no_generation": RUNTIME_BOUNDARY_FLAGS["no_generation"],
        "no_export": RUNTIME_BOUNDARY_FLAGS["no_export"],
        "no_zbid_writeback": RUNTIME_BOUNDARY_FLAGS["no_zbid_writeback"],
    }


def _authorized_real_kg_structure_summary(
    *,
    authorized_target: str,
    manual_trigger: bool,
    real_kg_read_only: bool,
    feature_flag_enabled: bool,
    structure_read: bool,
) -> dict[str, Any]:
    if (
        feature_flag_enabled is not True
        or manual_trigger is not True
        or real_kg_read_only is not True
        or structure_read is not True
        or authorized_target != AUTHORIZED_REAL_KG_TARGET
    ):
        return _empty_structure_summary(
            allowlist_status=BLOCKED_ALLOWLIST_STATUS,
        )

    try:
        with AUTHORIZED_REAL_KG_TARGET_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return _empty_structure_summary(
            allowlist_status=UNAVAILABLE_ALLOWLIST_STATUS,
        )

    return _build_structure_summary(
        payload,
        authorized_target=authorized_target,
        allowlist_status=AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS,
    )


def _empty_structure_summary(*, allowlist_status: int) -> dict[str, Any]:
    return {
        "top_level_type": 0,
        "top_level_key_names": (),
        "top_level_key_count": 0,
        "dict_count": 0,
        "list_count": 0,
        "null_count": 0,
        "scalar_type_counts": (),
        "selected_structure_paths": (0, (), ()),
        "list_lengths": (),
        "field_type_sets": (0, 0, (), ()),
        "max_depth_limited": False,
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": allowlist_status,
    }


def _build_structural_profile_summary_from_structure_summary(
    structure_summary: Mapping[str, Any],
    *,
    authorized_target: str,
) -> dict[str, Any]:
    selected_paths = _structural_profile_selected_paths(structure_summary)
    field_type_sets = _structural_profile_field_type_sets(structure_summary)
    field_name_counts = _structural_profile_field_name_counts(field_type_sets)
    source_allowlist_status = structure_summary.get("allowlist_status")
    profile_enabled = (
        source_allowlist_status == AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS
    )
    allowlist_status = (
        AUTHORIZED_REAL_KG_STRUCTURAL_PROFILE_ALLOWLIST_STATUS
        if profile_enabled
        else UNAVAILABLE_ALLOWLIST_STATUS
    )

    return {
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": allowlist_status,
        "profile_enabled": profile_enabled,
        "profile_scope": STRUCTURAL_PROFILE_SCOPE,
        "max_depth_limited": bool(structure_summary.get("max_depth_limited")),
        "path_count": _safe_count(selected_paths.get("path_count")),
        "path_type_counts": _structural_profile_path_type_counts(selected_paths),
        "depth_histogram": _structural_profile_depth_histogram(selected_paths),
        "field_name_counts": field_name_counts,
        "field_type_sets": field_type_sets,
        "list_length_buckets": _structural_profile_list_length_buckets(
            structure_summary,
        ),
        "dict_key_count_buckets": _structural_profile_dict_key_count_buckets(
            field_type_sets,
        ),
        "module_name_candidates": _structural_profile_module_name_candidates(
            selected_paths,
            field_name_counts,
        ),
        "redaction_policy": STRUCTURAL_PROFILE_REDACTION_POLICY,
    }


def _structural_profile_selected_paths(
    structure_summary: Mapping[str, Any],
) -> dict[str, Any]:
    raw_paths = structure_summary.get("selected_structure_paths")
    if not isinstance(raw_paths, (list, tuple)) or len(raw_paths) != 3:
        return {
            "path_count": 0,
            "depth_counts": (),
            "type_counts": (),
        }

    return {
        "path_count": _safe_count(raw_paths[0]),
        "depth_counts": _safe_pair_counts(raw_paths[1]),
        "type_counts": _safe_pair_counts(raw_paths[2]),
    }


def _structural_profile_field_type_sets(
    structure_summary: Mapping[str, Any],
) -> tuple[Any, ...]:
    raw_field_type_sets = structure_summary.get("field_type_sets")
    if not isinstance(raw_field_type_sets, (list, tuple)) or len(raw_field_type_sets) != 4:
        return (0, 0, (), ())

    return (
        _safe_count(raw_field_type_sets[0]),
        _safe_count(raw_field_type_sets[1]),
        _safe_pair_counts(raw_field_type_sets[2]),
        _safe_pair_counts(raw_field_type_sets[3]),
    )


def _structural_profile_path_type_counts(
    selected_paths: Mapping[str, Any],
) -> tuple[tuple[int, int], ...]:
    return _safe_pair_counts(selected_paths.get("type_counts"))


def _structural_profile_depth_histogram(
    selected_paths: Mapping[str, Any],
) -> tuple[tuple[int, int], ...]:
    return _safe_pair_counts(selected_paths.get("depth_counts"))


def _structural_profile_path_depth(path: str) -> int:
    if path == "$":
        return 0

    depth = 0
    for segment in path.split("."):
        if not segment or segment == "$":
            depth += segment.count("[]")
            continue
        depth += 1 + segment.count("[]")
    return depth


def _structural_profile_field_name_counts(
    field_type_sets: tuple[Any, ...],
) -> tuple[int, int, int, int]:
    field_group_count = _safe_count(field_type_sets[0] if field_type_sets else 0)
    field_slot_count = _safe_count(
        field_type_sets[1] if len(field_type_sets) > 1 else 0
    )
    return (
        field_group_count,
        _structural_profile_count_bucket_code(field_group_count),
        field_slot_count,
        _structural_profile_count_bucket_code(field_slot_count),
    )


def _structural_profile_list_length_buckets(
    structure_summary: Mapping[str, Any],
) -> tuple[tuple[int, int], ...]:
    raw_list_lengths = structure_summary.get("list_lengths")
    if not isinstance(raw_list_lengths, (list, tuple)):
        return ()

    buckets: dict[int, int] = {}
    for detail in raw_list_lengths:
        if not isinstance(detail, (list, tuple)) or len(detail) < 3:
            continue
        bucket_code = detail[2]
        if not isinstance(bucket_code, int) or bucket_code < 0:
            continue
        buckets[bucket_code] = buckets.get(bucket_code, 0) + 1
    return tuple((key, buckets[key]) for key in sorted(buckets))


def _structural_profile_dict_key_count_buckets(
    field_type_sets: tuple[Any, ...],
) -> tuple[tuple[int, int], ...]:
    if len(field_type_sets) < 4:
        return ()
    return _safe_pair_counts(field_type_sets[3])


def _structural_profile_count_bucket_code(count: int) -> int:
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 10:
        return 3
    if count <= 50:
        return 4
    return 5


def _safe_count(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _safe_pair_counts(value: Any) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, (list, tuple)):
        return ()

    pairs: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        key, count = item
        if not isinstance(key, int) or key < 0:
            continue
        if not isinstance(count, int) or count < 0:
            continue
        pairs.append((key, count))
    return tuple(sorted(pairs))


def _structural_profile_module_name_candidates(
    selected_paths: Mapping[str, Any],
    field_name_counts: tuple[int, int, int, int],
) -> list[str]:
    _ = selected_paths, field_name_counts
    return []


def _build_structure_summary(
    payload: Any,
    *,
    authorized_target: str,
    allowlist_status: int,
) -> dict[str, Any]:
    counters = {
        "dict_count": 0,
        "list_count": 0,
        "null_count": 0,
    }
    scalar_type_counts: dict[int, int] = {}
    selected_structure_paths: list[tuple[int, int]] = []
    list_lengths: list[tuple[int, int, int, tuple[tuple[int, int], ...]]] = []
    field_type_sets: list[tuple[int, ...]] = []
    max_depth_limited = False

    def remember_path(type_name: str, depth: int) -> None:
        if len(selected_structure_paths) < STRUCTURE_SUMMARY_MAX_PATHS:
            selected_structure_paths.append(
                (depth, _json_structure_type_code_from_name(type_name))
            )

    def walk(value: Any, depth: int) -> None:
        nonlocal max_depth_limited
        type_name = _json_structure_type(value)
        remember_path(type_name, depth)

        if depth > STRUCTURE_SUMMARY_MAX_DEPTH:
            max_depth_limited = True
            return

        if isinstance(value, dict):
            counters["dict_count"] += 1
            _merge_field_type_sets(field_type_sets, value)
            for child in value.values():
                walk(child, depth + 1)
            return

        if isinstance(value, list):
            counters["list_count"] += 1
            list_lengths.append(
                (
                    len(list_lengths) + 1,
                    len(value),
                    _structural_profile_count_bucket_code(len(value)),
                    _list_element_type_counts(value),
                )
            )
            for child in value:
                walk(child, depth + 1)
            return

        if value is None:
            counters["null_count"] += 1
            return

        type_code = _json_structure_type_code(value)
        scalar_type_counts[type_code] = scalar_type_counts.get(type_code, 0) + 1

    walk(payload, 0)

    top_level_key_count = 0
    if isinstance(payload, dict):
        top_level_key_count = len(payload)

    return {
        "top_level_type": _json_structure_type_code(payload),
        "top_level_key_names": (),
        "top_level_key_count": top_level_key_count,
        "dict_count": counters["dict_count"],
        "list_count": counters["list_count"],
        "null_count": counters["null_count"],
        "scalar_type_counts": tuple(
            (type_code, scalar_type_counts[type_code])
            for type_code in sorted(scalar_type_counts)
        ),
        "selected_structure_paths": _summarize_selected_structure_paths(
            selected_structure_paths
        ),
        "list_lengths": tuple(list_lengths[:STRUCTURE_SUMMARY_MAX_PATHS]),
        "field_type_sets": _summarize_field_type_sets(field_type_sets),
        "max_depth_limited": max_depth_limited,
        "authorized_target": AUTHORIZED_REAL_KG_TARGET_CODE,
        "allowlist_status": allowlist_status,
    }


def _json_structure_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    if isinstance(value, str):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return type(value).__name__


def _json_structure_type_code(value: Any) -> int:
    return _json_structure_type_code_from_name(_json_structure_type(value))


def _json_structure_type_code_from_name(type_name: str) -> int:
    if type_name in JSON_STRUCTURE_TYPE_CODE_BY_NAME:
        return JSON_STRUCTURE_TYPE_CODE_BY_NAME[type_name]
    return JSON_STRUCTURE_TYPE_CODE_BY_NAME["other"]


def _list_element_type_counts(items: list[Any]) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for item in items:
        type_code = _json_structure_type_code(item)
        counts[type_code] = counts.get(type_code, 0) + 1
    return tuple((type_code, counts[type_code]) for type_code in sorted(counts))


def _summarize_selected_structure_paths(
    selected_structure_paths: list[tuple[int, int]],
) -> tuple[int, tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    return (
        len(selected_structure_paths),
        _count_pairs(depth for depth, _type_code in selected_structure_paths),
        _count_pairs(type_code for _depth, type_code in selected_structure_paths),
    )


def _summarize_field_type_sets(
    field_type_sets: list[tuple[int, ...]],
) -> tuple[int, int, tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    return (
        len(field_type_sets),
        sum(len(type_codes) for type_codes in field_type_sets),
        _count_pairs(
            type_code
            for type_codes in field_type_sets
            for type_code in type_codes
        ),
        _count_pairs(
            _structural_profile_count_bucket_code(len(type_codes))
            for type_codes in field_type_sets
        ),
    )


def _count_pairs(items: Any) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for item in items:
        if not isinstance(item, int) or item < 0:
            continue
        counts[item] = counts.get(item, 0) + 1
    return tuple((key, counts[key]) for key in sorted(counts))


def _merge_field_type_sets(
    field_type_sets: list[tuple[int, ...]],
    value: Mapping[str, Any],
) -> None:
    field_type_sets.append(
        tuple(_json_structure_type_code(child) for child in value.values())
    )


def _contract_mapping_response(
    status: str,
    reason: str,
    ok: bool,
) -> dict[str, Any]:
    response = {
        "ok": ok,
        "enabled": False,
        "status": _adapter_status_code(status),
        "reason": _adapter_reason_code(reason),
        "source": CONTRACT_SOURCE_CODE,
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


def _adapter_reason_code(reason: str) -> int:
    return ADAPTER_REASON_CODES.get(reason, 0)


def _adapter_status_code(status: str) -> int:
    return ADAPTER_STATUS_CODES.get(status, 0)


def _whitelisted_response(response: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field_name: response[field_name]
        for field_name in OUTPUT_FIELD_WHITELIST
        if field_name in response
    }
