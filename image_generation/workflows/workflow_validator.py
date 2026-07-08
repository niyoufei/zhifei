"""Static validators for 027N-R4B workflow bridge configuration."""

from __future__ import annotations


REQUIRED_WORKFLOW_IDS = {
    "qwen_image_text_to_image",
    "qwen_image_edit_image_to_image",
    "flux_realistic_text_to_image",
}

ALLOWED_WORKFLOW_JSON_STATUSES = {
    "pending_real_workflow",
    "mapped_static_unverified",
}

ALLOWED_MAPPING_CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}

MODEL_WEIGHT_EXTENSIONS = (
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".gguf",
    ".bin",
    ".onnx",
)

REGISTRY_REQUIRED_FIELDS = {
    "workflow_id",
    "workflow_contract_id",
    "intended_model",
    "model_family",
    "task_type",
    "prompt_field",
    "negative_prompt_field",
    "input_type",
    "output_type",
    "workflow_json_ref",
    "workflow_json_status",
    "runtime_enabled",
    "r5_precheck_required",
    "r6_single_image_required",
    "no_video_generation",
    "enabled",
}

MANIFEST_REQUIRED_FIELDS = {
    "workflow_id",
    "workflow_json_ref",
    "workflow_json_status",
    "node_type_summary",
    "model_reference_id",
    "custom_nodes_required",
    "input_binding_profile",
    "output_policy_id",
    "runtime_enabled",
    "r5_precheck_required",
}

TEMPLATE_MAPPING_REQUIRED_FIELDS = {
    "template_id",
    "workflow_contract_id",
    "model_family",
    "generator",
    "renderer",
    "qwen_prompt_zh",
    "flux_prompt_en",
}

R7B_POLICY_TEMPLATE_ID = "qwen_image_tender_municipal_trench_lifting_v1"

R7B_POLICY_REQUIRED_FIELDS = {
    "max_candidates_per_task",
    "recommended_candidates_per_task",
    "candidate_generation_mode",
    "seed_required",
    "manual_review_required",
    "auto_publish_enabled",
    "video_generation_enabled",
    "batch_generation_enabled",
    "cross_model_comparison_enabled",
    "output_naming_pattern",
    "review_status_enum",
    "retention_policy",
    "duplicate_model_cleanup_policy",
}

R7B_REQUIRED_RETENTION_POLICY = {
    "keep_original_outputs": True,
    "keep_selected_outputs": True,
    "allow_cleanup_rejected_candidates": True,
    "cleanup_requires_manifest": True,
    "auto_delete_enabled": False,
    "never_clear_output_dir": True,
    "never_delete_model_files": True,
}

R7B_REQUIRED_DUPLICATE_MODEL_CLEANUP_POLICY = {
    "keep_current_workflow_target_models": True,
    "keep_hf_cache_symlink_shards_by_default": True,
    "delete_uncertain_assets": False,
    "cleanup_requires_separate_gate": True,
    "forbid_wildcard_rm": True,
    "verify_required_models_after_cleanup": True,
}

R8B_REVIEW_POLICY_REQUIRED_FIELDS = {
    "required",
    "manual_review_required",
    "review_status_enum",
    "checklist",
    "approval_required_before_bid",
}


def validate_workflow_registry(registry: dict) -> list[str]:
    """Return static registry errors; do not inspect runtime state."""

    errors: list[str] = []
    if registry.get("video_generation_enabled") is not False:
        errors.append("registry video_generation_enabled must be false")

    workflows = registry.get("workflows")
    if not isinstance(workflows, dict):
        return errors + ["registry workflows must be an object"]

    missing_ids = sorted(REQUIRED_WORKFLOW_IDS - set(workflows.keys()))
    if missing_ids:
        errors.append(f"registry missing required workflows: {missing_ids}")

    for workflow_id, entry in workflows.items():
        if not isinstance(entry, dict):
            errors.append(f"{workflow_id} registry entry must be an object")
            continue
        missing = sorted(REGISTRY_REQUIRED_FIELDS - set(entry.keys()))
        if missing:
            errors.append(f"{workflow_id} registry missing fields: {missing}")
        if entry.get("workflow_id") != workflow_id:
            errors.append(f"{workflow_id} workflow_id must match registry key")
        if entry.get("workflow_json_status") not in ALLOWED_WORKFLOW_JSON_STATUSES:
            errors.append(
                f"{workflow_id} workflow_json_status must be pending_real_workflow or mapped_static_unverified"
            )
        if entry.get("runtime_enabled") is not False:
            errors.append(f"{workflow_id} runtime_enabled must be false")
        if entry.get("no_video_generation") is not True:
            errors.append(f"{workflow_id} no_video_generation must be true")
        if _looks_environment_specific_path(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not be environment-specific")
        if _looks_model_weight_ref(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not point to a model weight")

    return errors


def validate_workflow_manifest(manifest: dict) -> list[str]:
    """Return static manifest errors; do not check ComfyUI or files."""

    errors: list[str] = []
    if manifest.get("video_generation_enabled") is not False:
        errors.append("manifest video_generation_enabled must be false")

    workflows = manifest.get("workflows")
    if not isinstance(workflows, dict):
        return errors + ["manifest workflows must be an object"]

    missing_ids = sorted(REQUIRED_WORKFLOW_IDS - set(workflows.keys()))
    if missing_ids:
        errors.append(f"manifest missing required workflows: {missing_ids}")

    for workflow_id, entry in workflows.items():
        if not isinstance(entry, dict):
            errors.append(f"{workflow_id} manifest entry must be an object")
            continue
        missing = sorted(MANIFEST_REQUIRED_FIELDS - set(entry.keys()))
        if missing:
            errors.append(f"{workflow_id} manifest missing fields: {missing}")
        if entry.get("workflow_id") != workflow_id:
            errors.append(f"{workflow_id} workflow_id must match manifest key")
        if entry.get("workflow_json_status") not in ALLOWED_WORKFLOW_JSON_STATUSES:
            errors.append(
                f"{workflow_id} manifest workflow_json_status must be pending_real_workflow or mapped_static_unverified"
            )
        if entry.get("runtime_enabled") is not False:
            errors.append(f"{workflow_id} manifest runtime_enabled must be false")
        if entry.get("no_video_generation") is not True:
            errors.append(f"{workflow_id} manifest no_video_generation must be true")
        if _looks_environment_specific_path(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not be environment-specific")
        if _looks_model_weight_ref(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not point to a model weight")
        errors.extend(_validate_static_mapping_metadata(workflow_id, entry))

    return errors


def validate_prompt_template_workflow_mapping(
    prompt_templates: dict,
    registry: dict,
) -> list[str]:
    """Validate prompt-template-to-workflow mappings are explicit."""

    errors: list[str] = []
    template_map = prompt_templates.get("templates")
    if not isinstance(template_map, dict):
        return ["prompt templates must use templates object"]

    if len(template_map) < 14:
        errors.append("prompt template count must be at least 14")

    workflows = registry.get("workflows", {})
    contract_ids = {
        entry.get("workflow_contract_id")
        for entry in workflows.values()
        if isinstance(entry, dict)
    }

    for template_key, template in template_map.items():
        if not isinstance(template, dict):
            errors.append(f"{template_key} template must be an object")
            continue
        missing = sorted(TEMPLATE_MAPPING_REQUIRED_FIELDS - set(template.keys()))
        if missing:
            errors.append(f"{template_key} mapping missing fields: {missing}")
        if template.get("template_id") != template_key:
            errors.append(f"{template_key} template_id must match template key")
        if template.get("workflow_contract_id") not in contract_ids:
            errors.append(f"{template_key} workflow_contract_id must exist in registry")
        if not template.get("qwen_prompt_zh"):
            errors.append(f"{template_key} missing qwen_prompt_zh")
        if not template.get("flux_prompt_en"):
            errors.append(f"{template_key} missing flux_prompt_en")

    r7b_template = template_map.get(R7B_POLICY_TEMPLATE_ID)
    if not isinstance(r7b_template, dict):
        errors.append(f"{R7B_POLICY_TEMPLATE_ID} missing R7B minimal production policy template")
    else:
        errors.extend(_validate_r7b_minimal_production_policy(r7b_template))

    return errors


def validate_r4b_static_configs(
    registry: dict,
    manifest: dict,
    prompt_templates: dict,
) -> list[str]:
    """Validate all R4B static workflow bridge config surfaces."""

    return (
        validate_workflow_registry(registry)
        + validate_workflow_manifest(manifest)
        + validate_prompt_template_workflow_mapping(prompt_templates, registry)
    )


def _looks_environment_specific_path(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return value.startswith(("/", "~", "file://")) or "/Users/" in value or "\\Users\\" in value


def _looks_model_weight_ref(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    return value.lower().endswith(MODEL_WEIGHT_EXTENSIONS)


def _validate_static_mapping_metadata(workflow_id: str, entry: dict) -> list[str]:
    errors: list[str] = []
    alternative_refs = entry.get("alternative_workflow_json_refs")
    if alternative_refs is not None:
        if not isinstance(alternative_refs, list) or not all(
            isinstance(item, str) for item in alternative_refs
        ):
            errors.append(f"{workflow_id} alternative_workflow_json_refs must be a string array")
        else:
            for ref in alternative_refs:
                if _looks_environment_specific_path(ref):
                    errors.append(
                        f"{workflow_id} alternative_workflow_json_refs must not be environment-specific"
                    )
                if _looks_model_weight_ref(ref):
                    errors.append(
                        f"{workflow_id} alternative_workflow_json_refs must not point to a model weight"
                    )

    mapping_confidence = entry.get("mapping_confidence")
    if mapping_confidence is not None and mapping_confidence not in ALLOWED_MAPPING_CONFIDENCES:
        errors.append(f"{workflow_id} mapping_confidence must be HIGH, MEDIUM, or LOW")

    manual_confirmation_required = entry.get("manual_confirmation_required")
    if (
        manual_confirmation_required is not None
        and not isinstance(manual_confirmation_required, bool)
    ):
        errors.append(f"{workflow_id} manual_confirmation_required must be boolean")

    model_reference_hint = entry.get("model_reference_hint")
    if model_reference_hint is not None and not isinstance(model_reference_hint, str):
        errors.append(f"{workflow_id} model_reference_hint must be a string")

    return errors


def _validate_r7b_minimal_production_policy(template: dict) -> list[str]:
    template_id = template.get("template_id", R7B_POLICY_TEMPLATE_ID)
    errors: list[str] = []
    review_policy_errors = _validate_r8b_review_policy(
        template_id,
        template.get("review_policy"),
    )

    policy = template.get("generation_policy")
    if not isinstance(policy, dict):
        return [
            f"{template_id} generation_policy must be an object"
        ] + review_policy_errors

    missing = sorted(R7B_POLICY_REQUIRED_FIELDS - set(policy.keys()))
    if missing:
        errors.append(f"{template_id} generation_policy missing fields: {missing}")

    max_candidates = policy.get("max_candidates_per_task")
    recommended_candidates = policy.get("recommended_candidates_per_task")
    if not isinstance(max_candidates, int):
        errors.append(f"{template_id} max_candidates_per_task must be integer")
    elif max_candidates > 3:
        errors.append(f"{template_id} max_candidates_per_task must be <= 3")
    if not isinstance(recommended_candidates, int):
        errors.append(f"{template_id} recommended_candidates_per_task must be integer")
    elif isinstance(max_candidates, int) and recommended_candidates > max_candidates:
        errors.append(
            f"{template_id} recommended_candidates_per_task must be <= max_candidates_per_task"
        )

    if policy.get("candidate_generation_mode") != "serial_single_image":
        errors.append(f"{template_id} candidate_generation_mode must be serial_single_image")
    if policy.get("seed_required") is not True:
        errors.append(f"{template_id} seed_required must be true")
    if policy.get("manual_review_required") is not True:
        errors.append(f"{template_id} manual_review_required must be true")
    if policy.get("auto_publish_enabled") is not False:
        errors.append(f"{template_id} auto_publish_enabled must be false")
    if policy.get("batch_generation_enabled") is not False:
        errors.append(f"{template_id} batch_generation_enabled must be false")
    if policy.get("video_generation_enabled") is not False:
        errors.append(f"{template_id} video_generation_enabled must be false")
    if policy.get("cross_model_comparison_enabled") is not False:
        errors.append(f"{template_id} cross_model_comparison_enabled must be false")

    review_status_enum = policy.get("review_status_enum")
    if not isinstance(review_status_enum, list) or not all(
        isinstance(item, str) for item in review_status_enum
    ):
        errors.append(f"{template_id} review_status_enum must be a string array")
    elif "approved_for_bid" not in review_status_enum:
        errors.append(f"{template_id} review_status_enum must include approved_for_bid")

    output_naming_pattern = policy.get("output_naming_pattern")
    if not isinstance(output_naming_pattern, str):
        errors.append(f"{template_id} output_naming_pattern must be a string")
    elif (
        _looks_environment_specific_path(output_naming_pattern)
        or "/" in output_naming_pattern
        or "\\" in output_naming_pattern
    ):
        errors.append(f"{template_id} output_naming_pattern must be a filename pattern")
    else:
        required_tokens = (
            "{seed}",
            "{width}",
            "{height}",
            "{timestamp}",
            "{review_status}",
        )
        for token in required_tokens:
            if token not in output_naming_pattern:
                errors.append(f"{template_id} output_naming_pattern missing {token}")

    errors.extend(
        _validate_expected_policy_object(
            template_id,
            "retention_policy",
            policy.get("retention_policy"),
            R7B_REQUIRED_RETENTION_POLICY,
        )
    )
    errors.extend(
        _validate_expected_policy_object(
            template_id,
            "duplicate_model_cleanup_policy",
            policy.get("duplicate_model_cleanup_policy"),
            R7B_REQUIRED_DUPLICATE_MODEL_CLEANUP_POLICY,
        )
    )

    if (
        template.get("model_family") == "flux"
        or template.get("workflow_contract_id") == "flux_realistic_text_to_image"
    ):
        errors.append(f"{template_id} must not enable FLUX")
    if (
        template.get("workflow_contract_id") == "qwen_image_edit_image_to_image"
        or template.get("task_type") == "site_photo_edit"
    ):
        errors.append(f"{template_id} must not enable image edit")

    errors.extend(review_policy_errors)

    return errors


def _validate_r8b_review_policy(template_id: str, value: object) -> list[str]:
    if not isinstance(value, dict):
        return [f"{template_id} review_policy must be an object"]

    errors: list[str] = []
    missing = sorted(R8B_REVIEW_POLICY_REQUIRED_FIELDS - set(value.keys()))
    if missing:
        errors.append(f"{template_id} review_policy missing fields: {missing}")
    if value.get("required") is not True:
        errors.append(f"{template_id} review_policy.required must be true")
    if value.get("manual_review_required") is not True:
        errors.append(f"{template_id} review_policy.manual_review_required must be true")

    review_status_enum = value.get("review_status_enum")
    if not isinstance(review_status_enum, list) or not review_status_enum or not all(
        isinstance(item, str) for item in review_status_enum
    ):
        errors.append(
            f"{template_id} review_policy.review_status_enum must be a non-empty string array"
        )

    checklist = value.get("checklist")
    if not isinstance(checklist, list) or not checklist or not all(
        isinstance(item, str) for item in checklist
    ):
        errors.append(f"{template_id} review_policy.checklist must be a non-empty string array")

    if value.get("approval_required_before_bid") is not True:
        errors.append(f"{template_id} review_policy.approval_required_before_bid must be true")

    return errors


def _validate_expected_policy_object(
    template_id: str,
    policy_name: str,
    value: object,
    expected_values: dict[str, bool],
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{template_id} {policy_name} must be an object"]

    errors: list[str] = []
    for key, expected_value in expected_values.items():
        if value.get(key) is not expected_value:
            errors.append(
                f"{template_id} {policy_name}.{key} must be {str(expected_value).lower()}"
            )

    return errors
