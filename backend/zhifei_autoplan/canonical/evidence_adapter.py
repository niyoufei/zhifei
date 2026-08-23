"""Explicit-input C3 assembly boundary with no generation or runtime work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import (
    ResponseEvidenceItemV2,
    ResponseEvidenceSetInputV2,
    ResponseEvidenceSetV2,
    TechnicalBidEvidenceMatrixInputV2,
    TechnicalBidEvidenceMatrixV2,
    TechnicalBidEvidenceRequirementV2,
)
from .scoring import ScoringRuleSetV2, SourceProvenanceReferenceV1


@dataclass(frozen=True, slots=True)
class EvidenceRequirementCandidateV2:
    requirement_id: str
    rule_id: str
    evidence_kind: str
    description: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]


@dataclass(frozen=True, slots=True)
class ResponseEvidenceCandidateV2:
    evidence_id: str
    requirement_id: str
    evidence_kind: str
    statement: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]


@dataclass(frozen=True, slots=True)
class EvidenceAssemblyInputV2:
    matrix_origin_namespace: str
    matrix_origin_key: str
    response_origin_namespace: str
    response_origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    scoring_rule_set: ScoringRuleSetV2
    requirements: tuple[EvidenceRequirementCandidateV2, ...]
    response_evidence: tuple[ResponseEvidenceCandidateV2, ...]
    matrix_parent_revision_id: str | None = None
    response_parent_revision_id: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceAssemblyResultV2:
    evidence_matrix: TechnicalBidEvidenceMatrixV2
    response_evidence_set: ResponseEvidenceSetV2

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_matrix": self.evidence_matrix.to_dict(),
            "response_evidence_set": self.response_evidence_set.to_dict(),
        }


def assemble_evidence_artifacts(source: EvidenceAssemblyInputV2) -> EvidenceAssemblyResultV2:
    """Canonicalize explicit C3 values and fail closed on the first invalid link."""

    requirements = tuple(
        TechnicalBidEvidenceRequirementV2.create(
            requirement_id=item.requirement_id,
            rule_id=item.rule_id,
            evidence_kind=item.evidence_kind,
            description=item.description,
            source_references=item.source_references,
        )
        for item in source.requirements
    )
    matrix = TechnicalBidEvidenceMatrixV2.build(
        TechnicalBidEvidenceMatrixInputV2(
            origin_namespace=source.matrix_origin_namespace,
            origin_key=source.matrix_origin_key,
            origin_source_mode=source.origin_source_mode,
            source_mode_set=source.source_mode_set,
            scoring_rule_set=source.scoring_rule_set,
            requirements=requirements,
            parent_revision_id=source.matrix_parent_revision_id,
        )
    )
    response_items = tuple(
        ResponseEvidenceItemV2.create(
            evidence_id=item.evidence_id,
            requirement_id=item.requirement_id,
            evidence_kind=item.evidence_kind,
            statement=item.statement,
            source_references=item.source_references,
        )
        for item in source.response_evidence
    )
    response_set = ResponseEvidenceSetV2.build(
        ResponseEvidenceSetInputV2(
            origin_namespace=source.response_origin_namespace,
            origin_key=source.response_origin_key,
            origin_source_mode=source.origin_source_mode,
            source_mode_set=source.source_mode_set,
            evidence_matrix=matrix,
            evidence_items=response_items,
            parent_revision_id=source.response_parent_revision_id,
        )
    )
    return EvidenceAssemblyResultV2(matrix, response_set)
