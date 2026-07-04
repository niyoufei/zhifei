"""ComfyUI workflow contracts without runtime creation or execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComfyWorkflowContract:
    """Static contract expected by a later ComfyUI runtime gate."""

    workflow_key: str
    model_role: str
    expected_repo_id: str
    input_type: str
    output_type: str
    runtime_required: bool
    local_only: bool
    notes: str


def get_default_workflow_contracts() -> dict[str, ComfyWorkflowContract]:
    """Return known workflow contracts; this does not create workflows."""

    return {
        "qwen_image_text_to_image": ComfyWorkflowContract(
            workflow_key="qwen_image_text_to_image",
            model_role="qwen_image_primary",
            expected_repo_id="Qwen/Qwen-Image",
            input_type="text_prompt",
            output_type="image",
            runtime_required=True,
            local_only=True,
            notes="For later text-to-image runtime verification only.",
        ),
        "qwen_image_edit_image_to_image": ComfyWorkflowContract(
            workflow_key="qwen_image_edit_image_to_image",
            model_role="qwen_image_edit",
            expected_repo_id="Qwen/Qwen-Image-Edit",
            input_type="image_plus_text_prompt",
            output_type="edited_image",
            runtime_required=True,
            local_only=True,
            notes="For later image-to-image edit verification only.",
        ),
        "flux_realistic_text_to_image": ComfyWorkflowContract(
            workflow_key="flux_realistic_text_to_image",
            model_role="flux_realistic",
            expected_repo_id="black-forest-labs/FLUX.1-dev",
            input_type="text_prompt",
            output_type="image",
            runtime_required=True,
            local_only=True,
            notes="For later realistic rendering verification only.",
        ),
    }
