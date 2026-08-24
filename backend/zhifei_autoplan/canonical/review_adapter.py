"""Explicit-input adapter for the C6 ReviewInputV1 foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic
from .diagnostic import DiagnosticResultSetV1
from .review import ReviewInputV1


@dataclass(frozen=True, slots=True)
class ReviewInputAdapterInputV1:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    target: Any
    diagnostic_result_set: DiagnosticResultSetV1


@dataclass(frozen=True, slots=True)
class ReviewInputAdapterResultV1:
    review_input: ReviewInputV1 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _failure(exc: CanonicalError) -> ReviewInputAdapterResultV1:
    source_index = 0
    if exc.code.startswith("REVIEW_"):
        phase = "80_REVIEW"
        code = exc.code
    elif exc.code == "REF_TARGET_MISSING":
        phase = "70_REFERENCE"
        code = exc.code
    elif exc.code.startswith("SRC_MODE_"):
        phase = "40_SOURCE_MODE"
        code = exc.code
    elif exc.code == "BOOTSTRAP_CYCLE_FORBIDDEN":
        phase = "100_BOOTSTRAP"
        code = exc.code
    else:
        phase = "30_SCHEMA"
        code = "SCHEMA_VIOLATION"
    diagnostic = DiagnosticV1(
        code=code,
        phase=phase,
        json_pointer=exc.json_pointer,
        source_index=source_index,
        detail_code=exc.code,
        message=str(exc),
    )
    return ReviewInputAdapterResultV1(None, (diagnostic,))


def assemble_review_input(source: ReviewInputAdapterInputV1) -> ReviewInputAdapterResultV1:
    """Canonicalize explicit references only; never run or decide a review."""

    try:
        review_input = ReviewInputV1.build(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            source_mode_set=source.source_mode_set,
            target=source.target,
            diagnostic_result_set=source.diagnostic_result_set,
        )
    except CanonicalError as exc:
        return _failure(exc)
    return ReviewInputAdapterResultV1(review_input, ())
