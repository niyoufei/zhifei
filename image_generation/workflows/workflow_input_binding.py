"""Static input binding plans for image workflow contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_GENERATION_OPTIONS = {
    "width": 1024,
    "height": 1024,
    "seed": 2704,
    "steps": 30,
    "cfg": 4.0,
    "sampler": "pending_r5_selection",
    "scheduler": "pending_r5_selection",
}

DEFAULT_INPUT_BINDING_PROFILES: dict[str, dict] = {
    "qwen_image_text_to_image_inputs": {
        "profile_id": "qwen_image_text_to_image_inputs",
        "source_image_required": False,
        "prompt_binding": "qwen_prompt_zh",
    },
    "qwen_image_edit_image_to_image_inputs": {
        "profile_id": "qwen_image_edit_image_to_image_inputs",
        "source_image_required": True,
        "prompt_binding": "qwen_prompt_zh",
    },
    "flux_realistic_text_to_image_inputs": {
        "profile_id": "flux_realistic_text_to_image_inputs",
        "source_image_required": False,
        "prompt_binding": "flux_prompt_en",
    },
}


@dataclass(frozen=True)
class WorkflowInputBindingPlan:
    """Static binding payload for a later ComfyUI workflow."""

    workflow_id: str
    input_binding_profile: str
    bindings: dict[str, Any]
    source_image_required: bool
    source_image_read_in_r4b: bool = False


def build_input_binding_plan(
    workflow_id: str,
    input_binding_profile: str,
    prompt_payload: dict,
    generation_options: dict | None = None,
    source_image_ref: str | None = None,
) -> WorkflowInputBindingPlan:
    """Create a static binding plan without reading images or running inference."""

    if input_binding_profile not in DEFAULT_INPUT_BINDING_PROFILES:
        raise ValueError(f"Unknown input binding profile: {input_binding_profile}")

    profile = DEFAULT_INPUT_BINDING_PROFILES[input_binding_profile]
    options = {**DEFAULT_GENERATION_OPTIONS, **(generation_options or {})}
    prompt = prompt_payload.get("prompt") or prompt_payload.get("positive_prompt")
    negative_prompt = prompt_payload.get("negative_prompt")
    if not prompt:
        raise ValueError("prompt payload must include prompt or positive_prompt")
    if negative_prompt is None:
        raise ValueError("prompt payload must include negative_prompt")

    source_image_required = bool(profile["source_image_required"])
    if source_image_required and not source_image_ref:
        raise ValueError("source_image_ref is required for image-edit workflow binding")

    bindings = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": options["width"],
        "height": options["height"],
        "seed": options["seed"],
        "steps": options["steps"],
        "cfg": options["cfg"],
        "sampler": options["sampler"],
        "scheduler": options["scheduler"],
        "source_image": {
            "required": source_image_required,
            "ref": source_image_ref if source_image_required else None,
            "read_file_in_r4b": False,
        },
    }

    return WorkflowInputBindingPlan(
        workflow_id=workflow_id,
        input_binding_profile=input_binding_profile,
        bindings=bindings,
        source_image_required=source_image_required,
    )
