"""Static authorization contracts for later image-generation runtimes."""

from image_generation.runtime.single_shot_submission_authorization import (
    build_single_shot_submission_authorization_envelope,
    validate_single_shot_submission_authorization_envelope,
)

__all__ = [
    "build_single_shot_submission_authorization_envelope",
    "validate_single_shot_submission_authorization_envelope",
]
