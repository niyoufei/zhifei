"""Static output policies for later single-image ComfyUI gates."""

from __future__ import annotations

from copy import deepcopy


DEFAULT_OUTPUT_POLICIES: dict[str, dict] = {
    "single_image_local_only": {
        "policy_id": "single_image_local_only",
        "max_images": 1,
        "output_dir_ref": "outputs/image_generation/r6_single_image",
        "filename_strategy": "workflow_id-template_id-seed",
        "record_seed": True,
        "record_provenance": True,
        "auto_upload": False,
        "batch_generation": False,
        "read_unrelated_files": False,
        "notes": "Static policy only; directories are not created in R4B.",
    }
}


def get_output_policy(policy_id: str) -> dict:
    """Return a copy of a static output policy."""

    if policy_id not in DEFAULT_OUTPUT_POLICIES:
        raise ValueError(f"Unknown workflow output policy: {policy_id}")
    return deepcopy(DEFAULT_OUTPUT_POLICIES[policy_id])
