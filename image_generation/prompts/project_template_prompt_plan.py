"""Build a static prompt plan from a validated project template instance."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from string import Formatter

from image_generation.workflows.workflow_validator import (
    TEMPLATE_ADMISSION_REQUIRED_VARIABLE_FIELDS,
    validate_project_template_instance,
    validate_prompt_template_workflow_mapping,
)


PLAN_TYPE = "project_template_prompt_plan"
PLAN_VERSION = "027n-r11-a"
_UNRESOLVED_PLACEHOLDER = re.compile(r"\{[^{}]+\}")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def build_project_template_prompt_plan(
    instance: dict,
    template_registry: dict,
    workflow_registry: dict,
    candidate_seed: int,
) -> dict:
    """Return a deterministic, JSON-serializable plan without runtime execution."""

    if type(candidate_seed) is not int or candidate_seed < 0:
        raise ValueError("candidate_seed must be a non-negative integer")

    registry_errors = validate_prompt_template_workflow_mapping(
        template_registry,
        workflow_registry,
    )
    if registry_errors:
        raise ValueError(f"invalid prompt template registry: {'; '.join(registry_errors)}")

    instance_errors = validate_project_template_instance(
        instance,
        template_registry,
        workflow_registry,
    )
    if instance_errors:
        raise ValueError(f"invalid project_template_instance: {'; '.join(instance_errors)}")

    template = template_registry["templates"][instance["template_id"]]
    variables = instance["variables"]
    declared_variables = set(template["variable_fields"])
    required_variables = set(TEMPLATE_ADMISSION_REQUIRED_VARIABLE_FIELDS)
    if declared_variables != required_variables or set(variables) != required_variables:
        raise ValueError("project template variables must match the six declared variable fields")

    positive_prompt = _render_prompt_template(
        template.get("positive_prompt_template"),
        variables,
        required_variables,
        require_all_variables=True,
        field_name="positive_prompt_template",
    )
    negative_prompt = _render_prompt_template(
        template.get("negative_prompt_template"),
        variables,
        required_variables,
        require_all_variables=False,
        field_name="negative_prompt_template",
    )

    fixed_parameters = template["fixed_parameters"]
    if (
        type(fixed_parameters.get("batch_size")) is not int
        or fixed_parameters["batch_size"] != 1
    ):
        raise ValueError("fixed_parameters.batch_size must be 1")

    generation_policy = template["generation_policy"]
    plan = {
        "plan_type": PLAN_TYPE,
        "plan_version": PLAN_VERSION,
        "project_id": instance["project_id"],
        "project_name": instance["project_name"],
        "template_id": instance["template_id"],
        "workflow_id": instance["workflow_id"],
        "candidate_seed": candidate_seed,
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "fixed_parameters": deepcopy(fixed_parameters),
        "generation_policy": deepcopy(generation_policy),
        "review_policy": deepcopy(template["review_policy"]),
        "retention_policy": deepcopy(generation_policy["retention_policy"]),
        "review_status": "candidate",
        "output_naming_pattern": generation_policy["output_naming_pattern"],
        "runtime_execution_authorized": False,
    }
    _validate_static_plan_payload(plan)
    return plan


def _render_prompt_template(
    value: object,
    variables: dict,
    allowed_variables: set[str],
    *,
    require_all_variables: bool,
    field_name: str,
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")

    try:
        template_variables = {
            variable_name
            for _, variable_name, _, _ in Formatter().parse(value)
            if variable_name is not None
        }
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid format template") from exc

    unexpected = sorted(template_variables - allowed_variables)
    if unexpected:
        raise ValueError(f"{field_name} contains undeclared variables: {unexpected}")
    if require_all_variables and template_variables != allowed_variables:
        missing = sorted(allowed_variables - template_variables)
        raise ValueError(f"{field_name} missing declared variables: {missing}")

    try:
        rendered = value.format_map(variables)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"{field_name} could not be rendered") from exc
    if _UNRESOLVED_PLACEHOLDER.search(rendered):
        raise ValueError(f"{field_name} contains unresolved placeholders after rendering")
    return rendered


def _validate_static_plan_payload(plan: dict) -> None:
    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = str(key).lower()
                if "token" in normalized_key:
                    raise ValueError("prompt plan must not contain token fields")
                if "path" in normalized_key and (
                    "model" in normalized_key or "output" in normalized_key
                ):
                    raise ValueError("prompt plan must not contain model or output path fields")
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
        elif isinstance(value, str) and (
            value.startswith(("/", "~/", "file://"))
            or _WINDOWS_ABSOLUTE_PATH.match(value)
        ):
            raise ValueError("prompt plan must not contain absolute paths")

    visit(plan)
    try:
        json.dumps(plan, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("prompt plan must be JSON serializable") from exc
