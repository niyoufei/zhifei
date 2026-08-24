"""Pure explicit-input extraction boundary for C2 scoring rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic, normalize_text
from .scoring import (
    ScoringExtractorIdentityV1,
    ScoringRuleSetInputV2,
    ScoringRuleSetV2,
    ScoringRuleV2,
    SourceProvenanceReferenceV1,
)


@dataclass(frozen=True, slots=True)
class ScoringExtractorRegistrationV1:
    extractor_id: str
    extractor_version: str
    supported_rule_kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        extractor_id = normalize_text(self.extractor_id)
        extractor_version = normalize_text(self.extractor_version)
        kinds = tuple(
            sorted(
                {normalize_text(item) for item in self.supported_rule_kinds},
                key=lambda item: item.encode("utf-8"),
            )
        )
        if not extractor_id or not extractor_version or not kinds or any(not item for item in kinds):
            raise CanonicalError("SCHEMA_VIOLATION", "scoring extractor registration must be non-empty")
        object.__setattr__(self, "extractor_id", extractor_id)
        object.__setattr__(self, "extractor_version", extractor_version)
        object.__setattr__(self, "supported_rule_kinds", kinds)


@dataclass(frozen=True, slots=True)
class DeterministicScoringExtractorRegistryV1:
    registrations: tuple[ScoringExtractorRegistrationV1, ...]

    @classmethod
    def create(
        cls,
        registrations: Sequence[ScoringExtractorRegistrationV1],
    ) -> "DeterministicScoringExtractorRegistryV1":
        ordered = tuple(
            sorted(
                registrations,
                key=lambda item: (
                    item.extractor_id.encode("utf-8"),
                    item.extractor_version.encode("utf-8"),
                ),
            )
        )
        keys = [(item.extractor_id, item.extractor_version) for item in ordered]
        if len(set(keys)) != len(keys):
            raise CanonicalError("SCHEMA_VIOLATION", "duplicate scoring extractor identity")
        return cls(ordered)

    def find(self, extractor_id: str, extractor_version: str) -> ScoringExtractorRegistrationV1 | None:
        key = (normalize_text(extractor_id), normalize_text(extractor_version))
        return next(
            (
                item
                for item in self.registrations
                if (item.extractor_id, item.extractor_version) == key
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class ScoringRuleCandidateV1:
    rule_id: str
    rule_kind: str
    title: str
    description: str
    maximum_score: str
    parameters: Mapping[str, Any]
    source_references: tuple[SourceProvenanceReferenceV1, ...]


@dataclass(frozen=True, slots=True)
class ScoringExtractionInputV1:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    extractor_id: str
    extractor_version: str
    rules: tuple[ScoringRuleCandidateV1, ...]
    parent_revision_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringExtractionResultV1:
    rule_set: ScoringRuleSetV2 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _schema_diagnostic(
    detail_code: str,
    pointer: str,
    message: str,
    *,
    source_index: int = 0,
) -> DiagnosticV1:
    return DiagnosticV1(
        code="SCHEMA_VIOLATION",
        phase="30_SCHEMA",
        json_pointer=pointer,
        source_index=source_index,
        detail_code=detail_code,
        message=message,
    )


def extract_scoring_rules(
    source: ScoringExtractionInputV1,
    registry: DeterministicScoringExtractorRegistryV1,
) -> ScoringExtractionResultV1:
    """Normalize explicit candidates only; no source read or downstream C3 work occurs."""

    registration = registry.find(source.extractor_id, source.extractor_version)
    if registration is None:
        diagnostic = _schema_diagnostic(
            "SCORING_EXTRACTOR_NOT_REGISTERED",
            "/extractor_id",
            "scoring extractor identity is not registered",
        )
        return ScoringExtractionResultV1(None, (diagnostic,))

    unsupported = tuple(
        _schema_diagnostic(
            "SCORING_RULE_UNSUPPORTED",
            f"/rules/{index}/rule_kind",
            "scoring rule kind is unsupported by the extractor",
            source_index=index,
        )
        for index, candidate in enumerate(source.rules)
        if normalize_text(candidate.rule_kind) not in registration.supported_rule_kinds
    )
    if unsupported:
        return ScoringExtractionResultV1(None, unsupported)

    normalized_rules: list[ScoringRuleV2] = []
    for index, candidate in enumerate(source.rules):
        try:
            normalized_rules.append(
                ScoringRuleV2.create(
                    rule_id=candidate.rule_id,
                    rule_kind=candidate.rule_kind,
                    title=candidate.title,
                    description=candidate.description,
                    maximum_score=candidate.maximum_score,
                    parameters=candidate.parameters,
                    source_references=candidate.source_references,
                )
            )
        except CanonicalError as exc:
            diagnostic = _schema_diagnostic(
                exc.code,
                exc.json_pointer or f"/rules/{index}",
                str(exc),
                source_index=index,
            )
            return ScoringExtractionResultV1(None, (diagnostic,))

    try:
        rule_set = ScoringRuleSetV2.build(
            ScoringRuleSetInputV2(
                origin_namespace=source.origin_namespace,
                origin_key=source.origin_key,
                origin_source_mode=source.origin_source_mode,
                source_mode_set=source.source_mode_set,
                extractor_identity=ScoringExtractorIdentityV1(
                    source.extractor_id,
                    source.extractor_version,
                ),
                rules=tuple(normalized_rules),
                parent_revision_id=source.parent_revision_id,
            )
        )
    except CanonicalError as exc:
        phase = "40_SOURCE_MODE" if exc.code.startswith("SRC_MODE_") else "30_SCHEMA"
        code = exc.code if phase == "40_SOURCE_MODE" else "SCHEMA_VIOLATION"
        diagnostic = DiagnosticV1(
            code=code,
            phase=phase,
            json_pointer=exc.json_pointer,
            detail_code=exc.code,
            message=str(exc),
        )
        return ScoringExtractionResultV1(None, (diagnostic,))
    return ScoringExtractionResultV1(rule_set, ())
