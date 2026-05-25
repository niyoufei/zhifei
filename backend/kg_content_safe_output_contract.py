"""Static KG content-safe output contract mapping draft.

This helper defines field classifications only. It performs no file IO, no KG
body read, no JSON parsing, no generation, no export, no writeback, no evidence
handling, no scoring, no RAG, and no registry access.
"""

from __future__ import annotations

from typing import Any


CONTENT_SAFE_OUTPUT_CONTRACT_SOURCE_CODE = 97
CONTENT_SAFE_OUTPUT_CONTRACT_CLASSIFICATION_POLICY = 1
CONTENT_SAFE_OUTPUT_CONTRACT_DOWNSTREAM_POLICY = 0

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
