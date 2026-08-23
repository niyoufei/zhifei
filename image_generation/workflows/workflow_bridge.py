"""Static workflow bridge from prompt templates to ComfyUI workflow plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from image_generation.workflows.workflow_input_binding import (
    WorkflowInputBindingPlan,
    build_input_binding_plan,
)
from image_generation.workflows.workflow_output_policy import get_output_policy
from image_generation.workflows.workflow_path_resolver import WorkflowPathResolver


@dataclass(frozen=True)
class WorkflowBridgePlan:
    """Static binding plan for a later runtime gate."""

    workflow_id: str
    workflow_contract_id: str
    prompt_template_key: str
    intended_model: str
    model_family: str
    workflow_json_ref: str | None
    workflow_json_status: str
    runtime_enabled: bool
    no_video_generation: bool
    input_binding: WorkflowInputBindingPlan
    output_policy: dict
    path_resolution: dict

    def as_dict(self) -> dict:
        """Return a serializable static plan."""

        data = asdict(self)
        data["input_binding"] = asdict(self.input_binding)
        return data


class WorkflowBridge:
    """Create static workflow binding plans without calling ComfyUI."""

    def __init__(
        self,
        workflow_registry: dict,
        workflow_manifest: dict,
        prompt_templates: dict,
        path_resolver: WorkflowPathResolver | None = None,
    ):
        self._registry = workflow_registry.get("workflows", workflow_registry)
        self._manifest = workflow_manifest.get("workflows", workflow_manifest)
        self._templates = prompt_templates.get("templates", prompt_templates)
        self._path_resolver = path_resolver or WorkflowPathResolver()

    def workflow_id_for_template(self, template_key: str) -> str:
        """Return the explicit workflow contract id attached to a template."""

        template = self._get_template(template_key)
        workflow_id = template.get("workflow_contract_id")
        if not workflow_id:
            raise ValueError(f"Prompt template {template_key} has no workflow_contract_id")
        if workflow_id not in self._registry:
            raise ValueError(f"Prompt template {template_key} references unknown workflow {workflow_id}")
        return workflow_id

    def build_plan(
        self,
        workflow_id: str,
        prompt_template_key: str,
        generation_options: dict | None = None,
        source_image_ref: str | None = None,
    ) -> WorkflowBridgePlan:
        """Build a static workflow plan; do not start services or read model files."""

        registry_entry = self._get_registry_entry(workflow_id)
        manifest_entry = self._get_manifest_entry(workflow_id)
        template = self._get_template(prompt_template_key)

        if template.get("workflow_contract_id") != registry_entry["workflow_contract_id"]:
            raise ValueError(
                f"Prompt template {prompt_template_key} is not mapped to workflow {workflow_id}"
            )
        if registry_entry.get("runtime_enabled") is not False:
            raise ValueError(f"Workflow {workflow_id} runtime_enabled must be false in R4B")
        if registry_entry.get("no_video_generation") is not True:
            raise ValueError(f"Workflow {workflow_id} no_video_generation must be true in R4B")

        prompt_field = registry_entry["prompt_field"]
        negative_prompt_field = registry_entry["negative_prompt_field"]
        prompt_payload = {
            "prompt": template[prompt_field],
            "negative_prompt": template[negative_prompt_field],
        }
        input_binding = build_input_binding_plan(
            workflow_id=workflow_id,
            input_binding_profile=registry_entry["input_binding_profile"],
            prompt_payload=prompt_payload,
            generation_options=generation_options,
            source_image_ref=source_image_ref,
        )
        output_policy = get_output_policy(registry_entry["output_policy_id"])
        path_resolution = self._path_resolver.resolve(
            workflow_id=workflow_id,
            workflow_json_ref=manifest_entry.get("workflow_json_ref"),
            workflow_json_status=manifest_entry["workflow_json_status"],
        )

        return WorkflowBridgePlan(
            workflow_id=workflow_id,
            workflow_contract_id=registry_entry["workflow_contract_id"],
            prompt_template_key=prompt_template_key,
            intended_model=registry_entry["intended_model"],
            model_family=registry_entry["model_family"],
            workflow_json_ref=manifest_entry.get("workflow_json_ref"),
            workflow_json_status=manifest_entry["workflow_json_status"],
            runtime_enabled=registry_entry["runtime_enabled"],
            no_video_generation=registry_entry["no_video_generation"],
            input_binding=input_binding,
            output_policy=output_policy,
            path_resolution=asdict(path_resolution),
        )

    def _get_registry_entry(self, workflow_id: str) -> dict:
        if workflow_id not in self._registry:
            raise ValueError(f"Unknown workflow registry entry: {workflow_id}")
        return self._registry[workflow_id]

    def _get_manifest_entry(self, workflow_id: str) -> dict:
        if workflow_id not in self._manifest:
            raise ValueError(f"Unknown workflow manifest entry: {workflow_id}")
        return self._manifest[workflow_id]

    def _get_template(self, template_key: str) -> dict:
        if not isinstance(self._templates, dict) or template_key not in self._templates:
            raise ValueError(f"Unknown prompt template: {template_key}")
        return self._templates[template_key]
