"""Static authorization contracts for later image-generation runtimes."""

from image_generation.runtime.local_comfyui_transport import LocalComfyUITransport
from image_generation.runtime.single_shot_submission_authorization import (
    build_single_shot_submission_authorization_envelope,
    validate_single_shot_submission_authorization_envelope,
)
from image_generation.runtime.single_shot_submission_coordinator import (
    dispatch_single_shot_submission,
)

__all__ = [
    "build_single_shot_submission_authorization_envelope",
    "dispatch_single_shot_submission",
    "LocalComfyUITransport",
    "validate_single_shot_submission_authorization_envelope",
]
