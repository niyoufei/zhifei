"""Fail-closed ReviewInputV2 to RecommendationV1 adapter."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic
from .recommendation import RecommendationV1
from .review_v2 import ReviewInputV2


_REVIEW_INPUT_V2_FIELDS = (
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
    "source_review_input",
)


@dataclass(frozen=True, slots=True)
class RecommendationV1AdapterResultV1:
    recommendation: RecommendationV1 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _schema_error(message: str) -> CanonicalError:
    return CanonicalError("SCHEMA_VIOLATION", message)


def _validate_v2_schema(source: Any) -> ReviewInputV2:
    if type(source) is not ReviewInputV2:
        raise _schema_error("source_review_input must be exactly ReviewInputV2")
    field_names = tuple(item.name for item in fields(source))
    if field_names != _REVIEW_INPUT_V2_FIELDS:
        raise _schema_error("source_review_input contains missing or unknown fields")
    if source.artifact_type != "review-input":
        raise _schema_error("source artifact_type must be review-input")
    if source.schema_version != "2":
        raise _schema_error("source schema_version must be 2")
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
        source.source_review_input,
    )
    if source.parent_revision_id is not None or any(value is None for value in required):
        raise _schema_error("source_review_input is missing or contains invalid required fields")
    return source


def _verify_v2_identity(source: ReviewInputV2) -> None:
    try:
        valid = source.verify_identity()
    except (CanonicalError, AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise CanonicalError(
            "REVIEW_IDENTITY_INVALID",
            "source ReviewInputV2 identity is invalid",
        )


def _verify_non_circularity(source: ReviewInputV2) -> None:
    if source.target.artifact_type == RecommendationV1.ARTIFACT_TYPE:
        raise CanonicalError(
            "BOOTSTRAP_CYCLE_FORBIDDEN",
            "RecommendationV1 source chain must be non-circular",
        )


def _failure(exc: CanonicalError) -> RecommendationV1AdapterResultV1:
    if exc.code == "REVIEW_IDENTITY_INVALID":
        phase = "80_REVIEW"
        code = "REVIEW_IDENTITY_INVALID"
    elif exc.code == "RECOMMENDATION_IDENTITY_INVALID":
        phase = "90_RECOMMENDATION"
        code = "RECOMMENDATION_IDENTITY_INVALID"
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
    return RecommendationV1AdapterResultV1(None, (diagnostic,))


def adapt_review_input_v2(source_review_input: Any) -> RecommendationV1AdapterResultV1:
    """Validate and adapt one V2 without accepting any caller overrides."""

    try:
        source = _validate_v2_schema(source_review_input)
        _verify_v2_identity(source)
        _verify_non_circularity(source)
        recommendation = RecommendationV1.from_verified_review_input(source)
        if not recommendation.verify_identity():
            raise CanonicalError(
                "RECOMMENDATION_IDENTITY_INVALID",
                "constructed RecommendationV1 identity is invalid",
            )
    except CanonicalError as exc:
        return _failure(exc)
    return RecommendationV1AdapterResultV1(recommendation, ())
