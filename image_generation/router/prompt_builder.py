"""Prompt builder for construction-organization image scenes."""

from __future__ import annotations


class ConstructionPromptBuilder:
    """Build prompt dictionaries from static templates and project context."""

    def __init__(self, prompt_templates: dict | None = None):
        self._prompt_templates = prompt_templates or {"templates": {}}

    def build_prompt(
        self,
        template_key: str,
        project_context: dict | None = None,
        model_role: str | None = None,
    ) -> dict:
        """Build a static prompt payload without calling any image model."""

        template = self._get_template(template_key)
        selected_model_role = model_role or template["recommended_model_role"]
        base_prompt = (
            template["flux_prompt_en"]
            if selected_model_role == "flux_realistic"
            else template["qwen_prompt_zh"]
        )
        positive_prompt = self._with_project_context(base_prompt, project_context or {})

        return {
            "positive_prompt": positive_prompt,
            "negative_prompt": template["negative_prompt"],
            "model_role": selected_model_role,
            "task_type": template["task_type"],
            "style_tags": list(template["style_tags"]),
            "quality_constraints": list(template["quality_constraints"]),
            "construction_constraints": list(template["construction_constraints"]),
        }

    def _get_template(self, template_key: str) -> dict:
        templates = self._prompt_templates.get("templates", self._prompt_templates)
        if not isinstance(templates, dict) or template_key not in templates:
            raise ValueError(f"Unknown construction prompt template: {template_key}")
        template = templates[template_key]
        required = {
            "task_type",
            "recommended_model_role",
            "qwen_prompt_zh",
            "flux_prompt_en",
            "negative_prompt",
            "style_tags",
            "quality_constraints",
            "construction_constraints",
        }
        missing = sorted(required - set(template.keys()))
        if missing:
            raise ValueError(f"Prompt template {template_key} missing fields: {missing}")
        return template

    @staticmethod
    def _with_project_context(base_prompt: str, project_context: dict) -> str:
        ordered_keys = [
            "project_type",
            "location",
            "work_stage",
            "key_equipment",
            "safety_focus",
            "visual_style",
        ]
        context_parts = [
            f"{key}={project_context[key]}"
            for key in ordered_keys
            if project_context.get(key)
        ]
        if not context_parts:
            return base_prompt
        return f"{base_prompt}; project_context: {'; '.join(context_parts)}"
