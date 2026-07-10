"""Pure static adapter from a project prompt plan to a ComfyUI API prompt."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any


PAYLOAD_TYPE = "comfyui_api_prompt_payload"
PAYLOAD_VERSION = "027n-r12-a"
PLAN_TYPE = "project_template_prompt_plan"
PLAN_VERSION = "027n-r11-a"
WORKFLOW_ID = "qwen_image_text_to_image"
INPUT_BINDING_PROFILE = "qwen_image_text_to_image_inputs"

_REQUIRED_BINDINGS = {
    "positive_prompt",
    "negative_prompt",
    "candidate_seed",
    "width",
    "height",
    "batch_size",
    "steps",
    "cfg",
    "sampler",
    "scheduler",
    "output_prefix",
}
_VIDEO_MARKERS = ("video", "svd", "wanvideo", "animatediff")
_IMAGE_EDIT_INPUTS = {
    "source_image",
    "input_image",
    "reference_image",
    "edit_image",
    "image_path",
    "upload",
    "upload_file",
}
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def build_comfyui_prompt_payload(
    prompt_plan: dict,
    workflow_document: dict,
    workflow_registry: dict,
    binding_contract: dict,
) -> dict:
    """Bind one Qwen text-to-image plan into an injected API-format workflow."""

    _validate_prompt_plan(prompt_plan)
    _validate_workflow_registry(workflow_registry)
    bindings = _validate_binding_contract(binding_contract)
    api_prompt = _validate_and_copy_api_prompt(workflow_document)

    fixed = prompt_plan["fixed_parameters"]
    output_prefix = (
        f"{prompt_plan['project_id']}__{prompt_plan['template_id']}"
        f"__seed-{prompt_plan['candidate_seed']}"
    )
    values = {
        "positive_prompt": prompt_plan["positive_prompt"],
        "negative_prompt": prompt_plan["negative_prompt"],
        "candidate_seed": prompt_plan["candidate_seed"],
        "width": fixed["width"],
        "height": fixed["height"],
        "batch_size": fixed["batch_size"],
        "steps": fixed["steps"],
        "cfg": fixed["cfg"],
        "sampler": fixed["sampler"],
        "scheduler": fixed["scheduler"],
        "output_prefix": output_prefix,
    }
    for field, value in values.items():
        target = bindings[field]
        node_id = str(target["node_id"])
        input_name = target["input_name"]
        if node_id not in api_prompt:
            raise ValueError(f"binding target node is missing for {field}: {node_id}")
        node_inputs = api_prompt[node_id].get("inputs")
        if not isinstance(node_inputs, dict) or input_name not in node_inputs:
            raise ValueError(f"binding target input is missing for {field}: {node_id}.{input_name}")
        node_inputs[input_name] = value

    payload = {
        "payload_type": PAYLOAD_TYPE,
        "payload_version": PAYLOAD_VERSION,
        "project_id": prompt_plan["project_id"],
        "template_id": prompt_plan["template_id"],
        "workflow_id": WORKFLOW_ID,
        "api_prompt": api_prompt,
        "candidate_seed": prompt_plan["candidate_seed"],
        "expected_output_count": 1,
        "output_prefix": output_prefix,
        "runtime_execution_authorized": False,
        "submission_authorized": False,
    }
    _validate_safe_serializable_payload(payload)
    return payload


def _validate_prompt_plan(plan: object) -> None:
    if not isinstance(plan, dict):
        raise ValueError("prompt_plan must be an object")
    if plan.get("plan_type") != PLAN_TYPE:
        raise ValueError(f"prompt_plan.plan_type must be {PLAN_TYPE}")
    if plan.get("plan_version") != PLAN_VERSION:
        raise ValueError(f"prompt_plan.plan_version must be {PLAN_VERSION}")
    if plan.get("runtime_execution_authorized") is not False:
        raise ValueError("runtime_execution_authorized must be false")
    if plan.get("workflow_id") != WORKFLOW_ID:
        raise ValueError(f"workflow_id must be {WORKFLOW_ID}")
    for field in ("project_id", "template_id", "positive_prompt", "negative_prompt"):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            raise ValueError(f"prompt_plan.{field} must be a non-empty string")
    if type(plan.get("candidate_seed")) is not int or plan["candidate_seed"] < 0:
        raise ValueError("candidate_seed must be a non-negative integer")

    fixed = plan.get("fixed_parameters")
    if not isinstance(fixed, dict):
        raise ValueError("fixed_parameters must be an object")
    for field in ("width", "height", "steps"):
        if type(fixed.get(field)) is not int or fixed[field] <= 0:
            raise ValueError(f"fixed_parameters.{field} must be a positive integer")
    if type(fixed.get("batch_size")) is not int or fixed["batch_size"] != 1:
        raise ValueError("fixed_parameters.batch_size must be 1")
    if type(fixed.get("cfg")) not in (int, float) or fixed["cfg"] <= 0:
        raise ValueError("fixed_parameters.cfg must be a positive number")
    for field in ("sampler", "scheduler"):
        if not isinstance(fixed.get(field), str) or not fixed[field].strip():
            raise ValueError(f"fixed_parameters.{field} must be a non-empty string")

    policy = plan.get("generation_policy")
    if not isinstance(policy, dict):
        raise ValueError("generation_policy must be an object")
    for field in ("batch_generation_enabled", "video_generation_enabled", "auto_publish_enabled"):
        if policy.get(field) is not False:
            raise ValueError(f"generation_policy.{field} must be false")
    if policy.get("candidate_generation_mode") != "serial_single_image":
        raise ValueError("generation_policy.candidate_generation_mode must be serial_single_image")


def _validate_workflow_registry(registry: object) -> None:
    if not isinstance(registry, dict):
        raise ValueError("workflow_registry must be an object")
    workflows = registry.get("workflows", registry)
    if not isinstance(workflows, dict) or WORKFLOW_ID not in workflows:
        raise ValueError(f"workflow_registry must contain {WORKFLOW_ID}")
    entry = workflows[WORKFLOW_ID]
    expected = {
        "workflow_id": WORKFLOW_ID,
        "workflow_contract_id": WORKFLOW_ID,
        "task_type": "text_to_image",
        "input_type": "text_prompt",
        "input_binding_profile": INPUT_BINDING_PROFILE,
        "no_video_generation": True,
    }
    if not isinstance(entry, dict) or any(entry.get(key) != value for key, value in expected.items()):
        raise ValueError(f"workflow_registry entry does not match {WORKFLOW_ID}")


def _validate_binding_contract(contract: object) -> dict:
    if not isinstance(contract, dict):
        raise ValueError("binding_contract must be an object")
    if contract.get("workflow_id") != WORKFLOW_ID:
        raise ValueError(f"binding_contract.workflow_id must be {WORKFLOW_ID}")
    if contract.get("input_binding_profile") != INPUT_BINDING_PROFILE:
        raise ValueError(f"binding_contract.input_binding_profile must be {INPUT_BINDING_PROFILE}")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != _REQUIRED_BINDINGS:
        raise ValueError("binding_contract.bindings must contain exactly the allowed binding fields")
    for field, target in bindings.items():
        if not isinstance(target, dict) or set(target) != {"node_id", "input_name"}:
            raise ValueError(f"binding_contract target for {field} must define node_id and input_name")
        if not isinstance(target["node_id"], (str, int)) or isinstance(target["node_id"], bool):
            raise ValueError(f"binding_contract node_id for {field} is invalid")
        if not isinstance(target["input_name"], str) or not target["input_name"]:
            raise ValueError(f"binding_contract input_name for {field} is invalid")
    return bindings


def _validate_and_copy_api_prompt(document: object) -> dict:
    if not isinstance(document, dict) or not document:
        raise ValueError("workflow_document must be a non-empty ComfyUI API prompt object")
    copied = deepcopy(document)
    for node_id, node in copied.items():
        if not isinstance(node_id, str) or not isinstance(node, dict):
            raise ValueError("workflow_document must use API prompt node objects keyed by string ids")
        class_type = node.get("class_type")
        inputs = node.get("inputs")
        if not isinstance(class_type, str) or not isinstance(inputs, dict):
            raise ValueError("workflow_document nodes must contain class_type and inputs")
        normalized_class = class_type.lower()
        if any(marker in normalized_class for marker in _VIDEO_MARKERS):
            raise ValueError("workflow_document must not contain video nodes")
        if normalized_class in {"loadimage", "loadimageoutput", "imageedit"}:
            raise ValueError("workflow_document must not contain image-edit input nodes")
        if any(str(input_name).lower() in _IMAGE_EDIT_INPUTS for input_name in inputs):
            raise ValueError("workflow_document must not contain image-edit inputs")
    return copied


def _validate_safe_serializable_payload(payload: dict) -> None:
    def visit(value: Any, key: str = "") -> None:
        normalized_key = key.lower()
        if "token" in normalized_key or "secret" in normalized_key or "endpoint" in normalized_key:
            raise ValueError("payload must not contain token, secret, or endpoint fields")
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, str(child_key))
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child, key)
        elif isinstance(value, str):
            lowered = value.lower()
            if "localhost" in lowered or ".env" in lowered:
                raise ValueError("payload must not contain localhost or .env references")
            if value.startswith(("/", "~/", "file://")) or _WINDOWS_ABSOLUTE_PATH.match(value):
                raise ValueError("payload must not contain absolute paths")

    visit(payload)
    try:
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be JSON serializable") from exc
