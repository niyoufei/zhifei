"""Static KG content-safe output contract mapping draft.

This helper defines field classifications only. It performs no file IO, no KG
body read, no JSON parsing, no generation, no export, no writeback, no evidence
handling, no scoring, no RAG, and no registry access.
"""

from __future__ import annotations

from typing import Any, Mapping


CONTENT_SAFE_OUTPUT_CONTRACT_SOURCE_CODE = 97
CONTENT_SAFE_OUTPUT_CONTRACT_CLASSIFICATION_POLICY = 1
CONTENT_SAFE_OUTPUT_CONTRACT_DOWNSTREAM_POLICY = 0
PREVIEW_ONLY_ADAPTER_MAPPING_SOURCE_CODE = 100
PREVIEW_ONLY_ADAPTER_MAPPING_POLICY = 1
PREVIEW_ONLY_RESPONSE_INTEGRATION_SOURCE_CODE = 105
PREVIEW_ONLY_RESPONSE_INTEGRATION_POLICY = 1
ZDOC_PREVIEW_ONLY_INTEGRATION_SOURCE_CODE = 117
ZDOC_PREVIEW_ONLY_INTEGRATION_POLICY = 1
ZDOC_PREVIEW_ONLY_DEFAULT_OFF_POLICY = 1
ZDOC_PREVIEW_ONLY_MANUAL_TRIGGER_POLICY = 1
ZDOC_PREVIEW_ONLY_OUTPUT_CHAIN_POLICY = 0

PREVIEW_ONLY_TOP_LEVEL_FIELDS = (
    "structure_read_only",
    "structure_summary",
    "structural_profile_only",
    "structural_profile_summary",
)

STRUCTURE_CONTRACT_PREVIEW_ONLY_FIELDS = (
    "contract_scope",
    "authorized_target",
    "allowlist_status",
    "target_policy",
    "summary_field_whitelist",
    "value_output_policy",
    "scalar_policy",
    "list_policy",
    "dict_policy",
)

STRUCTURAL_PROFILE_CONTRACT_PREVIEW_ONLY_FIELDS = (
    "contract_scope",
    "authorized_target",
    "allowlist_status",
    "target_policy",
    "summary_field_whitelist",
    "profile_scope",
    "redaction_policy",
    "scalar_policy",
    "list_policy",
    "dict_policy",
    "module_name_policy",
)

AUDIT_ONLY_FIELDS = (
    "feature_flag_status",
    "manual_trigger_status",
    "real_kg_read_only_status",
    "authorized_target_hit_status",
    "allowlist_status",
    "route_contract_code",
    "adapter_contract_code",
    "validation_result",
    "overlap_check_result",
)

AUDIT_ONLY_RESPONSE_FIELDS = (
    "feature_flag_status",
    "manual_trigger_status",
    "real_kg_read_only_status",
    "authorized_target_hit_status",
    "allowlist_status",
    "route_contract_code",
    "adapter_contract_code",
    "validation_result",
    "overlap_check_result",
)

PROHIBITED_FIELDS = (
    "KG scalar value",
    "list item 内容",
    "dict value 内容",
    "业务正文",
    "实体正文",
    "知识条目正文",
    "prompt",
    "system instruction",
    "evidence",
    "scoring",
    "原始 KG 文本片段",
    "可反推 KG 正文的字符串",
)

DOWNSTREAM_PROHIBITIONS = {
    "generate": True,
    "export_docx": True,
    "review_apply": True,
    "output_write": True,
    "job_write": True,
    "export_write": True,
    "zbid_writeback": True,
    "rag": True,
    "prompt_registry": True,
    "system_instruction_registry": True,
    "evidence": True,
    "scoring": True,
}


def build_content_safe_output_contract_mapping() -> dict[str, Any]:
    """Return the static KG-RUNTIME-97 field classification mapping."""

    return {
        "source": CONTENT_SAFE_OUTPUT_CONTRACT_SOURCE_CODE,
        "classification_policy": CONTENT_SAFE_OUTPUT_CONTRACT_CLASSIFICATION_POLICY,
        "downstream_policy": CONTENT_SAFE_OUTPUT_CONTRACT_DOWNSTREAM_POLICY,
        "preview_only": {
            "top_level_fields": PREVIEW_ONLY_TOP_LEVEL_FIELDS,
            "structure_contract_fields": STRUCTURE_CONTRACT_PREVIEW_ONLY_FIELDS,
            "structural_profile_contract_fields": (
                STRUCTURAL_PROFILE_CONTRACT_PREVIEW_ONLY_FIELDS
            ),
        },
        "audit_only": AUDIT_ONLY_FIELDS,
        "prohibited": PROHIBITED_FIELDS,
        "downstream_prohibitions": dict(DOWNSTREAM_PROHIBITIONS),
    }


def classify_content_safe_fields() -> dict[str, Any]:
    """Return the static KG-RUNTIME-100 adapter field classes."""

    return {
        "source": PREVIEW_ONLY_ADAPTER_MAPPING_SOURCE_CODE,
        "mapping_policy": PREVIEW_ONLY_ADAPTER_MAPPING_POLICY,
        "preview_only": {
            "top_level_fields": PREVIEW_ONLY_TOP_LEVEL_FIELDS,
            "structure_contract_fields": STRUCTURE_CONTRACT_PREVIEW_ONLY_FIELDS,
            "structural_profile_contract_fields": (
                STRUCTURAL_PROFILE_CONTRACT_PREVIEW_ONLY_FIELDS
            ),
        },
        "audit_only": {
            "contract_fields": AUDIT_ONLY_FIELDS,
            "response_fields": AUDIT_ONLY_RESPONSE_FIELDS,
        },
        "prohibited": PROHIBITED_FIELDS,
        "downstream_prohibitions": dict(DOWNSTREAM_PROHIBITIONS),
    }


def filter_preview_only_fields(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep only preview-only fields from an already content-safe response."""

    preview_only = _filter_mapping_fields(
        content_safe_response,
        PREVIEW_ONLY_TOP_LEVEL_FIELDS,
    )

    structure_contract = _filter_safe_contract_fields(
        content_safe_response.get("structure_contract"),
        STRUCTURE_CONTRACT_PREVIEW_ONLY_FIELDS,
    )
    if structure_contract:
        preview_only["structure_contract"] = structure_contract

    structural_profile_contract = _filter_safe_contract_fields(
        content_safe_response.get("structural_profile_contract"),
        STRUCTURAL_PROFILE_CONTRACT_PREVIEW_ONLY_FIELDS,
    )
    if structural_profile_contract:
        preview_only["structural_profile_contract"] = structural_profile_contract

    return preview_only


def filter_audit_only_fields(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep only audit-only fields from an already content-safe response."""

    return _filter_mapping_fields(content_safe_response, AUDIT_ONLY_RESPONSE_FIELDS)


def build_preview_only_payload(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the KG-RUNTIME-100 preview-only adapter mapping draft payload."""

    return {
        "source": PREVIEW_ONLY_ADAPTER_MAPPING_SOURCE_CODE,
        "mapping_policy": PREVIEW_ONLY_ADAPTER_MAPPING_POLICY,
        "preview_only": filter_preview_only_fields(content_safe_response),
        "audit_only": filter_audit_only_fields(content_safe_response),
        "prohibited": {
            "fields": PROHIBITED_FIELDS,
            "values_output": False,
        },
        "downstream_prohibitions": dict(DOWNSTREAM_PROHIBITIONS),
    }


def build_preview_only_response_integration_payload(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the KG-RUNTIME-105 preview-only response integration draft."""

    adapter_mapping = build_preview_only_payload(content_safe_response)
    return {
        "preview_contract": {
            "integration_source": PREVIEW_ONLY_RESPONSE_INTEGRATION_SOURCE_CODE,
            "integration_policy": PREVIEW_ONLY_RESPONSE_INTEGRATION_POLICY,
            "mapping_source": adapter_mapping["source"],
            "mapping_policy": adapter_mapping["mapping_policy"],
        },
        "preview_only_mapping": adapter_mapping["preview_only"],
        "audit_only_mapping": adapter_mapping["audit_only"],
        "prohibited_mapping": tuple(adapter_mapping["prohibited"]["fields"]),
    }


def build_zdoc_preview_only_payload(
    content_safe_response: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the KG-RUNTIME-117 ZDoc preview-only integration draft."""

    adapter_mapping = build_preview_only_payload(content_safe_response)
    return {
        "preview_contract": {
            "integration_source": PREVIEW_ONLY_RESPONSE_INTEGRATION_SOURCE_CODE,
            "integration_policy": PREVIEW_ONLY_RESPONSE_INTEGRATION_POLICY,
            "zdoc_integration_source": ZDOC_PREVIEW_ONLY_INTEGRATION_SOURCE_CODE,
            "zdoc_integration_policy": ZDOC_PREVIEW_ONLY_INTEGRATION_POLICY,
            "default_off_policy": ZDOC_PREVIEW_ONLY_DEFAULT_OFF_POLICY,
            "manual_trigger_policy": ZDOC_PREVIEW_ONLY_MANUAL_TRIGGER_POLICY,
            "output_chain_policy": ZDOC_PREVIEW_ONLY_OUTPUT_CHAIN_POLICY,
            "mapping_source": adapter_mapping["source"],
            "mapping_policy": adapter_mapping["mapping_policy"],
        },
        "preview_only_mapping": adapter_mapping["preview_only"],
        "audit_only_mapping": adapter_mapping["audit_only"],
        "prohibited_mapping": tuple(adapter_mapping["prohibited"]["fields"]),
    }


def _filter_mapping_fields(
    source: Mapping[str, Any],
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    return {
        field_name: source[field_name]
        for field_name in field_names
        if field_name in source
    }


def _filter_safe_contract_fields(
    source: Any,
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}

    return {
        field_name: source[field_name]
        for field_name in field_names
        if field_name in source and _is_safe_contract_code(source[field_name])
    }


def _is_safe_contract_code(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    if isinstance(value, (list, tuple)):
        return all(
            isinstance(item, int) and not isinstance(item, bool) and item >= 0
            for item in value
        )
    return False
