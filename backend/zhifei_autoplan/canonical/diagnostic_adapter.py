"""Pure explicit-input adapter for the C5 diagnostic-result foundation."""

from __future__ import annotations

from dataclasses import dataclass

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic
from .diagnostic import DiagnosticResultSetV1, DiagnosticSourceReferenceV1


@dataclass(frozen=True, slots=True)
class DiagnosticCandidateV1:
    code: str
    phase: str
    source_index: int
    json_pointer: str = ""
    detail_code: str | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticResultSetInputV1:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    source_references: tuple[DiagnosticSourceReferenceV1, ...]
    diagnostics: tuple[DiagnosticCandidateV1, ...]


@dataclass(frozen=True, slots=True)
class DiagnosticAssemblyResultV1:
    result_set: DiagnosticResultSetV1 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _failure(exc: CanonicalError, pointer: str, source_index: int = 0) -> DiagnosticAssemblyResultV1:
    if exc.code.startswith("SRC_MODE_"):
        phase = "40_SOURCE_MODE"
        code = exc.code
    elif exc.code == "BOOTSTRAP_CYCLE_FORBIDDEN":
        phase = "100_BOOTSTRAP"
        code = exc.code
    elif exc.code == "REF_TARGET_MISSING":
        phase = "70_REFERENCE"
        code = exc.code
    else:
        phase = "30_SCHEMA"
        code = "SCHEMA_VIOLATION"
    diagnostic = DiagnosticV1(
        code=code,
        phase=phase,
        json_pointer=exc.json_pointer or pointer,
        source_index=source_index,
        detail_code=exc.code,
        message=str(exc),
    )
    return DiagnosticAssemblyResultV1(None, (diagnostic,))


def assemble_diagnostic_result_set(source: DiagnosticResultSetInputV1) -> DiagnosticAssemblyResultV1:
    """Canonicalize explicit results only; no diagnostic or review workflow runs."""

    normalized: list[DiagnosticV1] = []
    for index, candidate in enumerate(source.diagnostics):
        try:
            normalized.append(
                DiagnosticV1(
                    code=candidate.code,
                    phase=candidate.phase,
                    json_pointer=candidate.json_pointer,
                    source_index=candidate.source_index,
                    detail_code=candidate.detail_code,
                    message=candidate.message,
                )
            )
        except CanonicalError as exc:
            return _failure(exc, f"/diagnostics/{index}", candidate.source_index)

    try:
        result_set = DiagnosticResultSetV1.build(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            source_mode_set=source.source_mode_set,
            source_references=source.source_references,
            diagnostics=normalized,
        )
    except CanonicalError as exc:
        return _failure(exc, "")
    return DiagnosticAssemblyResultV1(result_set, ())
