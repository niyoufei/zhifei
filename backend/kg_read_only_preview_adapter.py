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


BLOCKED_STATUS = "blocked"
INVALID_STATUS = "invalid"
PREVIEW_STATUS = "preview_only"

CONTRACT_SOURCE = "kg_runtime_28_29_adapter_contract_mapping_design"
CONTRACT_SCOPE = "top-level plus first/second structural levels only"
REAL_KG_ROUTE_READ_ONLY_SOURCE = "kg_runtime_39_real_kg_route_read_only_draft"
REAL_KG_ROUTE_READ_ONLY_CONTRACT_SCOPE = (
    "route-level real-KG metadata-only read-only contract"
)
REAL_KG_STRUCTURE_CONTRACT_SCOPE = (
    "single authorized target structure-only JSON summary draft"
)
REAL_KG_STRUCTURAL_PROFILE_CONTRACT_SCOPE = (
    "single authorized target content-safe structural profile draft"
)
AUTHORIZED_REAL_KG_TARGET = "知识图谱/ZF-KG-12-Municipal-Bridge.json"
AUTHORIZED_REAL_KG_TARGET_PATH = (
    Path(__file__).parent.parent / AUTHORIZED_REAL_KG_TARGET
)
AUTHORIZED_REAL_KG_FILE_STAT_ALLOWLIST_STATUS = "authorized_single_target"
AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS = (
    "authorized_single_target_structure_only"
)
AUTHORIZED_REAL_KG_STRUCTURAL_PROFILE_ALLOWLIST_STATUS = (
    "authorized_single_target_structural_profile_only"
)
REAL_KG_TARGET_POLICY = "single_authorized_target_file_stat_metadata_only"
REAL_KG_STRUCTURE_TARGET_POLICY = "single_authorized_target_structure_only"
REAL_KG_STRUCTURAL_PROFILE_TARGET_POLICY = (
    "single_authorized_target_content_safe_structural_profile_only"
)
REAL_KG_READ_POLICY = "file_stat_metadata_only_no_content_read_no_json_parse"
REAL_KG_STRUCTURE_READ_POLICY = "structure_only_json_read_no_value_output"
REAL_KG_STRUCTURAL_PROFILE_READ_POLICY = (
    "reuse_structure_read_summary_no_scalar_value_output"
)
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
STRUCTURE_VALUE_OUTPUT_POLICY = (
    "structure_only_key_type_count_length_summary_no_scalar_or_value_output"
)
STRUCTURE_SUMMARY_MAX_DEPTH = 4
STRUCTURE_SUMMARY_MAX_PATHS = 80
STRUCTURAL_PROFILE_MAX_MODULE_CANDIDATES = 40
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
STRUCTURAL_PROFILE_SCOPE = (
    "paths_field_names_types_counts_hierarchy_module_name_candidates_only"
)
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
STRUCTURAL_PROFILE_REDACTION_POLICY = {
    "scalar": "type_and_count_only_no_scalar_value_output",
    "list": "length_bucket_and_type_summary_only_no_item_content",
    "dict": "key_name_key_count_and_type_set_only_no_value_content",
    "module_name_candidates": "field_or_path_name_only_no_value_source",
}
JSON_STRUCTURE_TYPE_NAMES = frozenset(
    {
        "dict",
        "list",
        "null",
        "bool",
        "str",
        "int",
        "float",
    }
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
            return _real_kg_contract_response(
                status=PREVIEW_STATUS,
                reason="real_kg_structural_profile_route_draft",
                ok=True,
                target_policy=REAL_KG_STRUCTURAL_PROFILE_TARGET_POLICY,
                read_policy=REAL_KG_STRUCTURAL_PROFILE_READ_POLICY,
                structure_metadata={
                    "structure_read": True,
                    "structure_read_only": True,
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
    target_policy: Optional[str] = None,
    read_policy: Optional[str] = None,
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
            "target_policy": target_policy or REAL_KG_TARGET_POLICY,
            "read_policy": read_policy or REAL_KG_READ_POLICY,
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
            "authorized_target": AUTHORIZED_REAL_KG_TARGET,
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
        "authorized_target": AUTHORIZED_REAL_KG_TARGET,
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
        "authorized_target": AUTHORIZED_REAL_KG_TARGET,
        "allowlist_status": AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS,
        "target_policy": REAL_KG_STRUCTURE_TARGET_POLICY,
        "feature_flag_required": True,
        "manual_trigger_required": True,
        "real_kg_read_only_required": True,
        "structure_read_required": True,
        "summary_field_whitelist": STRUCTURE_SUMMARY_FIELD_WHITELIST,
        "value_output_policy": STRUCTURE_VALUE_OUTPUT_POLICY,
        "scalar_policy": "type_only_no_value_output",
        "list_policy": "length_and_element_type_summary_only",
        "dict_policy": "key_names_key_count_and_field_type_sets_only",
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
        "authorized_target": AUTHORIZED_REAL_KG_TARGET,
        "allowlist_status": AUTHORIZED_REAL_KG_STRUCTURAL_PROFILE_ALLOWLIST_STATUS,
        "target_policy": REAL_KG_STRUCTURAL_PROFILE_TARGET_POLICY,
        "feature_flag_required": True,
        "manual_trigger_required": True,
        "real_kg_read_only_required": True,
        "structure_read_required": True,
        "structural_profile_required": True,
        "summary_field_whitelist": STRUCTURAL_PROFILE_SUMMARY_FIELD_WHITELIST,
        "profile_scope": STRUCTURAL_PROFILE_SCOPE,
        "redaction_policy": STRUCTURAL_PROFILE_REDACTION_POLICY,
        "scalar_policy": "type_and_count_only_no_value_output",
        "list_policy": "length_bucket_and_type_summary_only_no_item_content",
        "dict_policy": "key_name_key_count_and_type_set_only_no_value_content",
        "module_name_policy": "field_or_path_name_only_no_value_source",
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
            allowlist_status="structure_read_gate_blocked",
        )

    try:
        with AUTHORIZED_REAL_KG_TARGET_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return _empty_structure_summary(
            allowlist_status="authorized_single_target_structure_unavailable",
        )

    return _build_structure_summary(
        payload,
        authorized_target=authorized_target,
        allowlist_status=AUTHORIZED_REAL_KG_STRUCTURE_ALLOWLIST_STATUS,
    )


def _empty_structure_summary(*, allowlist_status: str) -> dict[str, Any]:
    return {
        "top_level_type": "unavailable",
        "top_level_key_names": (),
        "top_level_key_count": 0,
        "dict_count": 0,
        "list_count": 0,
        "null_count": 0,
        "scalar_type_counts": {},
        "selected_structure_paths": (),
        "list_lengths": {},
        "field_type_sets": {},
        "max_depth_limited": False,
        "authorized_target": AUTHORIZED_REAL_KG_TARGET,
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
        else "authorized_single_target_structural_profile_unavailable"
    )

    return {
        "authorized_target": authorized_target,
        "allowlist_status": allowlist_status,
        "profile_enabled": profile_enabled,
        "profile_scope": STRUCTURAL_PROFILE_SCOPE,
        "max_depth_limited": bool(structure_summary.get("max_depth_limited")),
        "path_count": len(selected_paths),
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
) -> tuple[dict[str, str], ...]:
    raw_paths = structure_summary.get("selected_structure_paths")
    if not isinstance(raw_paths, (list, tuple)):
        return ()

    selected_paths: list[dict[str, str]] = []
    for item in raw_paths:
        if not isinstance(item, Mapping):
            continue
        path = item.get("path")
        type_name = item.get("type")
        if not isinstance(path, str) or not isinstance(type_name, str):
            continue
        selected_paths.append(
            {
                "path": path,
                "type": _structural_profile_type_name(type_name),
            }
        )
    return tuple(selected_paths)


def _structural_profile_field_type_sets(
    structure_summary: Mapping[str, Any],
) -> dict[str, dict[str, tuple[str, ...]]]:
    raw_field_type_sets = structure_summary.get("field_type_sets")
    if not isinstance(raw_field_type_sets, Mapping):
        return {}

    profile_field_type_sets: dict[str, dict[str, tuple[str, ...]]] = {}
    for path, fields in raw_field_type_sets.items():
        if not isinstance(path, str) or not isinstance(fields, Mapping):
            continue
        safe_fields: dict[str, tuple[str, ...]] = {}
        for field_name, type_names in fields.items():
            if not isinstance(field_name, str) or not isinstance(
                type_names,
                (list, tuple, set),
            ):
                continue
            safe_fields[field_name] = tuple(
                sorted(
                    {
                        _structural_profile_type_name(type_name)
                        for type_name in type_names
                        if isinstance(type_name, str)
                    }
                )
            )
        profile_field_type_sets[path] = safe_fields
    return _limited_mapping(profile_field_type_sets)


def _structural_profile_type_name(type_name: str) -> str:
    if type_name in JSON_STRUCTURE_TYPE_NAMES:
        return type_name
    return "other"


def _structural_profile_path_type_counts(
    selected_paths: tuple[dict[str, str], ...],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in selected_paths:
        type_name = item["type"]
        counts[type_name] = counts.get(type_name, 0) + 1
    return dict(sorted(counts.items()))


def _structural_profile_depth_histogram(
    selected_paths: tuple[dict[str, str], ...],
) -> dict[str, int]:
    histogram: dict[str, int] = {}
    for item in selected_paths:
        depth = str(_structural_profile_path_depth(item["path"]))
        histogram[depth] = histogram.get(depth, 0) + 1
    return dict(sorted(histogram.items()))


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
    field_type_sets: Mapping[str, Mapping[str, tuple[str, ...]]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fields in field_type_sets.values():
        for field_name in fields:
            counts[field_name] = counts.get(field_name, 0) + 1
    return dict(sorted(counts.items()))


def _structural_profile_list_length_buckets(
    structure_summary: Mapping[str, Any],
) -> dict[str, int]:
    raw_list_lengths = structure_summary.get("list_lengths")
    if not isinstance(raw_list_lengths, Mapping):
        return {}

    buckets: dict[str, int] = {}
    for detail in raw_list_lengths.values():
        if not isinstance(detail, Mapping):
            continue
        length = detail.get("length")
        if not isinstance(length, int) or length < 0:
            continue
        bucket = _structural_profile_count_bucket(length)
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return dict(sorted(buckets.items()))


def _structural_profile_dict_key_count_buckets(
    field_type_sets: Mapping[str, Mapping[str, tuple[str, ...]]],
) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for fields in field_type_sets.values():
        bucket = _structural_profile_count_bucket(len(fields))
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return dict(sorted(buckets.items()))


def _structural_profile_count_bucket(count: int) -> str:
    if count == 0:
        return "0"
    if count <= 2:
        return "1-2"
    if count <= 5:
        return "3-5"
    if count <= 10:
        return "6-10"
    if count <= 50:
        return "11-50"
    return "51+"


def _structural_profile_module_name_candidates(
    selected_paths: tuple[dict[str, str], ...],
    field_name_counts: Mapping[str, int],
) -> tuple[str, ...]:
    candidates = {
        field_name
        for field_name in field_name_counts
        if _looks_like_module_name_candidate(field_name)
    }
    for item in selected_paths:
        for segment in _structural_profile_path_segments(item["path"]):
            if _looks_like_module_name_candidate(segment):
                candidates.add(segment)
    return tuple(sorted(candidates)[:STRUCTURAL_PROFILE_MAX_MODULE_CANDIDATES])


def _structural_profile_path_segments(path: str) -> tuple[str, ...]:
    segments: list[str] = []
    for raw_segment in path.split("."):
        segment = raw_segment.replace("[]", "").strip()
        if segment and segment != "$":
            segments.append(segment)
    return tuple(segments)


def _looks_like_module_name_candidate(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "module",
            "section",
            "chapter",
            "part",
            "category",
            "模块",
            "章节",
            "目录",
            "分部",
            "分项",
        )
    )


def _build_structure_summary(
    payload: Any,
    *,
    authorized_target: str,
    allowlist_status: str,
) -> dict[str, Any]:
    counters = {
        "dict_count": 0,
        "list_count": 0,
        "null_count": 0,
    }
    scalar_type_counts: dict[str, int] = {}
    selected_structure_paths: list[dict[str, str]] = []
    list_lengths: dict[str, dict[str, Any]] = {}
    field_type_sets: dict[str, dict[str, tuple[str, ...]]] = {}
    max_depth_limited = False

    def remember_path(path: str, type_name: str) -> None:
        if len(selected_structure_paths) < STRUCTURE_SUMMARY_MAX_PATHS:
            selected_structure_paths.append({"path": path, "type": type_name})

    def walk(value: Any, path: str, depth: int) -> None:
        nonlocal max_depth_limited
        type_name = _json_structure_type(value)
        remember_path(path, type_name)

        if depth > STRUCTURE_SUMMARY_MAX_DEPTH:
            max_depth_limited = True
            return

        if isinstance(value, dict):
            counters["dict_count"] += 1
            _merge_field_type_sets(field_type_sets, path, value)
            for key, child in value.items():
                walk(child, _child_structure_path(path, key), depth + 1)
            return

        if isinstance(value, list):
            counters["list_count"] += 1
            list_lengths[path] = {
                "length": len(value),
                "element_type_counts": _list_element_type_counts(value),
            }
            for child in value:
                walk(child, f"{path}[]", depth + 1)
            return

        if value is None:
            counters["null_count"] += 1
            return

        scalar_type_counts[type_name] = scalar_type_counts.get(type_name, 0) + 1

    walk(payload, "$", 0)

    top_level_key_names: tuple[str, ...] = ()
    if isinstance(payload, dict):
        top_level_key_names = tuple(str(key) for key in payload.keys())

    return {
        "top_level_type": _json_structure_type(payload),
        "top_level_key_names": top_level_key_names,
        "top_level_key_count": len(top_level_key_names),
        "dict_count": counters["dict_count"],
        "list_count": counters["list_count"],
        "null_count": counters["null_count"],
        "scalar_type_counts": dict(sorted(scalar_type_counts.items())),
        "selected_structure_paths": tuple(selected_structure_paths),
        "list_lengths": _limited_mapping(list_lengths),
        "field_type_sets": _limited_mapping(field_type_sets),
        "max_depth_limited": max_depth_limited,
        "authorized_target": authorized_target,
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


def _child_structure_path(parent: str, key: Any) -> str:
    return f"{parent}.{str(key)}"


def _list_element_type_counts(items: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        type_name = _json_structure_type(item)
        counts[type_name] = counts.get(type_name, 0) + 1
    return dict(sorted(counts.items()))


def _merge_field_type_sets(
    field_type_sets: dict[str, dict[str, tuple[str, ...]]],
    path: str,
    value: Mapping[str, Any],
) -> None:
    existing = {
        field_name: set(type_names)
        for field_name, type_names in field_type_sets.get(path, {}).items()
    }
    for key, child in value.items():
        field_name = str(key)
        existing.setdefault(field_name, set()).add(_json_structure_type(child))
    field_type_sets[path] = {
        field_name: tuple(sorted(type_names))
        for field_name, type_names in sorted(existing.items())
    }


def _limited_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: mapping[key]
        for key in sorted(mapping.keys())[:STRUCTURE_SUMMARY_MAX_PATHS]
    }


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
