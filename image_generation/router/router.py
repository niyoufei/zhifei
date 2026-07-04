"""Pure in-memory router for local image generation task planning."""

from __future__ import annotations

from image_generation.prompts.construction_templates import (
    DEFAULT_TEMPLATE_BY_TASK_TYPE,
)
from image_generation.router.models import ImageModelConfig, ImageRouteDecision


DEFAULT_ROUTING_CONFIG: dict = {
    "schema_version": "027n-r3a",
    "deployment_mode": "local_only",
    "video_generation_enabled": False,
    "runtime_status": "configured_not_runtime_verified",
    "models": {
        "qwen_image_primary": {
            "repo_id": "Qwen/Qwen-Image",
            "status": "downloaded_not_runtime_verified",
            "primary_use": [
                "technical_bid_illustration",
                "construction_process_diagram",
                "temporary_facility_layout",
                "chinese_signage_scene",
            ],
            "supports_chinese_text": True,
            "supports_photo_edit": False,
            "supports_realistic_render": True,
            "supports_controlnet": False,
            "is_active": True,
        },
        "qwen_image_edit": {
            "repo_id": "Qwen/Qwen-Image-Edit",
            "status": "downloaded_not_runtime_verified",
            "primary_use": [
                "site_photo_edit",
                "chinese_signage_edit",
                "existing_scene_correction",
            ],
            "supports_chinese_text": True,
            "supports_photo_edit": True,
            "supports_realistic_render": True,
            "supports_controlnet": False,
            "is_active": True,
        },
        "flux_realistic": {
            "repo_id": "black-forest-labs/FLUX.1-dev",
            "status": "downloaded_not_runtime_verified",
            "primary_use": [
                "realistic_construction_scene",
                "birdseye_render",
                "cover_image",
                "machinery_operation_scene",
            ],
            "supports_chinese_text": False,
            "supports_photo_edit": False,
            "supports_realistic_render": True,
            "supports_controlnet": False,
            "is_active": True,
        },
    },
    "routing_rules": {
        "technical_bid_illustration": {
            "primary": "qwen_image_primary",
            "fallback": "flux_realistic",
        },
        "realistic_construction_scene": {
            "primary": "flux_realistic",
            "fallback": "qwen_image_primary",
        },
        "site_photo_edit": {
            "primary": "qwen_image_edit",
            "fallback": "qwen_image_primary",
        },
    },
}


class ImageGenerationRouter:
    """Decide model roles for image tasks without touching any runtime."""

    def __init__(
        self,
        routing_config: dict | None = None,
        prompt_templates: dict | None = None,
    ):
        self._routing_config = routing_config or DEFAULT_ROUTING_CONFIG
        self._prompt_templates = prompt_templates or {"templates": {}}
        self._models = self._routing_config.get("models", {})
        self._rules = self._routing_config.get("routing_rules", {})
        self._runtime_status = self._routing_config.get(
            "runtime_status",
            "configured_not_runtime_verified",
        )

    def decide(self, task_type: str) -> ImageRouteDecision:
        """Return the static route for a supported task type."""

        if task_type not in self._rules:
            supported = ", ".join(self.supported_task_types())
            raise ValueError(f"Unsupported image task type: {task_type}. Supported: {supported}")

        rule = self._rules[task_type]
        selected_role = rule["primary"]
        fallback_role = rule.get("fallback", "")
        model_config = self.get_model_config(selected_role)
        prompt_template_key = rule.get("prompt_template_key") or self._template_key_for_task(
            task_type
        )
        workflow_key = rule.get("workflow_key") or self._workflow_key_for_role(selected_role)

        warnings = [
            "runtime_status=configured_not_runtime_verified",
            "generation_requires_later_runtime_precheck",
        ]
        if not model_config.is_active:
            warnings.append("selected_model_role_is_not_active")

        return ImageRouteDecision(
            task_type=task_type,
            selected_role=selected_role,
            selected_repo_id=model_config.repo_id,
            fallback_role=fallback_role,
            prompt_template_key=prompt_template_key,
            workflow_key=workflow_key,
            reasons=[
                f"routing_rule_primary={selected_role}",
                f"model_primary_use={','.join(model_config.primary_use)}",
            ],
            warnings=warnings,
        )

    def supported_task_types(self) -> list[str]:
        """Return task types configured in the static routing table."""

        return sorted(self._rules.keys())

    def get_model_config(self, role: str) -> ImageModelConfig:
        """Return static model configuration for a role."""

        if role not in self._models:
            raise ValueError(f"Unknown image model role: {role}")
        data = self._models[role]
        status = data.get("local_cache_status") or data.get("status", "unknown")
        is_active = data.get(
            "is_active",
            status not in {"planned_download_not_active", "disabled_not_deployed", "disabled"},
        )
        return ImageModelConfig(
            role=role,
            repo_id=data.get("repo_id", ""),
            local_cache_status=status,
            runtime_status=data.get("runtime_status", self._runtime_status),
            primary_use=list(data.get("primary_use", [])),
            supports_chinese_text=bool(data.get("supports_chinese_text", False)),
            supports_photo_edit=bool(data.get("supports_photo_edit", False)),
            supports_realistic_render=bool(data.get("supports_realistic_render", False)),
            supports_controlnet=bool(data.get("supports_controlnet", False)),
            is_active=bool(is_active),
            notes=data.get("notes", ""),
        )

    def is_video_generation_enabled(self) -> bool:
        """Video generation is intentionally disabled in this scaffold."""

        return False

    def _template_key_for_task(self, task_type: str) -> str:
        templates = self._prompt_templates.get("templates", self._prompt_templates)
        if isinstance(templates, dict):
            for key, template in templates.items():
                if isinstance(template, dict) and template.get("task_type") == task_type:
                    return key
        return DEFAULT_TEMPLATE_BY_TASK_TYPE.get(task_type, task_type)

    @staticmethod
    def _workflow_key_for_role(role: str) -> str:
        if role == "qwen_image_edit":
            return "qwen_image_edit_image_to_image"
        if role == "flux_realistic":
            return "flux_realistic_text_to_image"
        return "qwen_image_text_to_image"
