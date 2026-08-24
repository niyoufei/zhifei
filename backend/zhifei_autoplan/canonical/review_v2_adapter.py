"""Fail-closed ReviewInputV1 to ReviewInputV2 adapter."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic
from .review import ReviewInputV1
from .review_v2 import ReviewInputV2


_REVIEW_INPUT_V1_FIELDS = (
    "artifact_type",
    "schema_version",
    "origin_namespace",
    "origin_key",
    "origin_source_mode",
    "stable_id",
    "revision_id",
    "parent_revision_id",
    "content_sha256",
    "provenance_sha256",
    "record_sha256",
    "target",
    "diagnostic_result_set",
    "provenance",
)


@dataclass(frozen=True, slots=True)
class ReviewInputV2AdapterResultV1:
    review_input: ReviewInputV2 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _schema_error(message: str) -> CanonicalError:
    return CanonicalError("SCHEMA_VIOLATION", message)


def _validate_v1_schema(source: Any) -> ReviewInputV1:
    if type(source) is not ReviewInputV1:
        raise _schema_error("source_review_input must be exactly ReviewInputV1")
    field_names = tuple(item.name for item in fields(source))
    if field_names != _REVIEW_INPUT_V1_FIELDS:
        raise _schema_error("source_review_input contains missing or unknown fields")
    if source.artifact_type != "review-input":
        raise _schema_error("source artifact_type must be review-input")
    if source.schema_version != "1":
        raise _schema_error("source schema_version must be 1")
    required = (
        source.origin_namespace,
        source.origin_key,
        source.origin_source_mode,
        source.stable_id,
        source.revision_id,
        source.content_sha256,
        source.provenance_sha256,
        source.record_sha256,
        source.target,
        source.diagnostic_result_set,
        source.provenance,
    )
    if any(value is None for value in required):
        raise _schema_error("source_review_input is missing required fields")
    return source


def _verify_v1_identity(source: ReviewInputV1) -> None:
    try:
        valid = source.verify_identity()
    except (CanonicalError, TypeError, ValueError):
        valid = False
    if not valid:
        raise CanonicalError(
            "REVIEW_IDENTITY_INVALID",
            "source ReviewInputV1 identity is invalid",
        )


def _verify_non_circularity(source: ReviewInputV1) -> None:
    if source.parent_revision_id is not None or source.target.artifact_type == "review-input":
        raise CanonicalError(
            "BOOTSTRAP_CYCLE_FORBIDDEN",
            "ReviewInputV2 source chain must be non-circular",
        )


def _failure(exc: CanonicalError) -> ReviewInputV2AdapterResultV1:
    if exc.code == "REVIEW_IDENTITY_INVALID":
        phase = "80_REVIEW"
        code = "REVIEW_IDENTITY_INVALID"
    elif exc.code == "BOOTSTRAP_CYCLE_FORBIDDEN":
        phase = "100_BOOTSTRAP"
        code = "BOOTSTRAP_CYCLE_FORBIDDEN"
    else:
        phase = "30_SCHEMA"
        code = "SCHEMA_VIOLATION"
    diagnostic = DiagnosticV1(
        code=code,
        phase=phase,
        json_pointer=exc.json_pointer,
        source_index=0,
        detail_code=exc.code,
        message=str(exc),
    )
    return ReviewInputV2AdapterResultV1(None, (diagnostic,))


def adapt_review_input_v1(source_review_input: Any) -> ReviewInputV2AdapterResultV1:
    """Validate and adapt V1 without accepting origin or content overrides."""

    try:
        source = _validate_v1_schema(source_review_input)
        _verify_v1_identity(source)
        _verify_non_circularity(source)
        review_input = ReviewInputV2.from_verified_review_input(source)
        if not review_input.verify_identity():
            raise CanonicalError(
                "REVIEW_IDENTITY_INVALID",
                "constructed ReviewInputV2 identity is invalid",
            )
    except CanonicalError as exc:
        return _failure(exc)
    return ReviewInputV2AdapterResultV1(review_input, ())
