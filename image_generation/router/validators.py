"""Static validators for image routing and prompt template configs."""

from __future__ import annotations


def validate_routing_config(config: dict) -> list[str]:
    """Return configuration problems, or an empty list when valid."""

    errors: list[str] = []
    if config.get("video_generation_enabled") is not False:
        errors.append("video_generation_enabled must be false")

    models = config.get("models")
    if not isinstance(models, dict):
        return errors + ["models must be an object"]

    required_models = {
        "qwen_image_primary": "Qwen/Qwen-Image",
        "qwen_image_edit": "Qwen/Qwen-Image-Edit",
        "flux_realistic": "black-forest-labs/FLUX.1-dev",
    }
    for role, repo_id in required_models.items():
        model = models.get(role)
        if not isinstance(model, dict):
            errors.append(f"missing model role: {role}")
            continue
        if model.get("repo_id") != repo_id:
            errors.append(f"{role} repo_id must be {repo_id}")

    candidate = models.get("qwen_image_edit_latest_candidate")
    if not isinstance(candidate, dict):
        errors.append("missing planned model role: qwen_image_edit_latest_candidate")
    elif candidate.get("status") == "active" or candidate.get("is_active") is True:
        errors.append("qwen_image_edit_latest_candidate must not be active")
    elif candidate.get("status") != "planned_download_not_active":
        errors.append("qwen_image_edit_latest_candidate status must be planned_download_not_active")

    routing_rules = config.get("routing_rules")
    if not isinstance(routing_rules, dict) or not routing_rules:
        errors.append("routing_rules must be a non-empty object")

    return errors


def validate_prompt_templates(templates: dict) -> list[str]:
    """Return prompt-template problems, or an empty list when valid."""

    errors: list[str] = []
    template_map = templates.get("templates", templates)
    if not isinstance(template_map, dict):
        return ["templates must be an object"]

    if len(template_map) < 10:
        errors.append("prompt template count must be at least 10")

    required_fields = {
        "task_type",
        "recommended_model_role",
        "qwen_prompt_zh",
        "flux_prompt_en",
        "negative_prompt",
        "style_tags",
        "quality_constraints",
        "construction_constraints",
    }
    for key, template in template_map.items():
        if "video" in key:
            errors.append(f"{key} must not be a video generation template")
        if not isinstance(template, dict):
            errors.append(f"{key} must be an object")
            continue
        missing = sorted(required_fields - set(template.keys()))
        if missing:
            errors.append(f"{key} missing fields: {missing}")
        if not template.get("qwen_prompt_zh"):
            errors.append(f"{key} missing qwen_prompt_zh")
        if not template.get("flux_prompt_en"):
            errors.append(f"{key} missing flux_prompt_en")
        if "video" in str(template.get("task_type", "")):
            errors.append(f"{key} task_type must not be video-related")

    return errors
