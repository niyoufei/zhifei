"""Static validators for 027N-R4B workflow bridge configuration."""

from __future__ import annotations


REQUIRED_WORKFLOW_IDS = {
    "qwen_image_text_to_image",
    "qwen_image_edit_image_to_image",
    "flux_realistic_text_to_image",
}

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
        if entry.get("runtime_enabled") is not False:
            errors.append(f"{workflow_id} runtime_enabled must be false")
        if entry.get("no_video_generation") is not True:
            errors.append(f"{workflow_id} no_video_generation must be true")
        if _looks_environment_specific_path(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not be environment-specific")

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
        if entry.get("runtime_enabled") is not False:
            errors.append(f"{workflow_id} manifest runtime_enabled must be false")
        if entry.get("no_video_generation") is not True:
            errors.append(f"{workflow_id} manifest no_video_generation must be true")
        if _looks_environment_specific_path(entry.get("workflow_json_ref")):
            errors.append(f"{workflow_id} workflow_json_ref must not be environment-specific")

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

    if len(template_map) != 13:
        errors.append("prompt template count must remain 13")

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
