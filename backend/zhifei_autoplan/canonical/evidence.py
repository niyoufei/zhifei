"""Pure C3 evidence-matrix and response-evidence canonical values.

The module consumes already-canonical C2 scoring rules and explicit evidence
values.  It performs no parsing, generation, review, persistence, runtime, or
network work.  Every artifact is immutable, deterministically ordered, and
initially unavailable for response use pending a later controller decision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final
import re

from .common import (
    CANONICAL_PROFILE_ID,
    CanonicalError,
    canonical_json_bytes,
    derive_revision_id,
    derive_stable_id,
    effective_source_mode,
    identities_equal,
    normalize_source_modes,
    normalize_text,
    profile_digest,
    require_no_source_mode_promotion,
    validate_digest,
)
from .scoring import ScoringRuleSetV2, SourceProvenanceReferenceV1


_EVIDENCE_KIND_RE: Final = re.compile(r"^[a-z][a-z0-9-]*$")
_SCORING_STABLE_PREFIX: Final = "ocrc:scoring-rule-set:"
_SCORING_REVISION_PREFIX: Final = "ocrc-rev:scoring-rule-set:"
_MATRIX_STABLE_PREFIX: Final = "ocrc:technical-bid-evidence-matrix:"
_MATRIX_REVISION_PREFIX: Final = "ocrc-rev:technical-bid-evidence-matrix:"


def _nonempty(value: str, field_name: str, *, human_text: bool = False) -> str:
    value = normalize_text(value, human_text=human_text)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _prefixed_identity(value: str, prefix: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value.startswith(prefix):
        raise CanonicalError("REF_TARGET_MISSING", f"{field_name} has the wrong artifact type")
    validate_digest(value[len(prefix) :])
    return value


def _ordered_source_references(
    values: Sequence[SourceProvenanceReferenceV1],
) -> tuple[SourceProvenanceReferenceV1, ...]:
    references = tuple(values)
    if not references or any(not isinstance(item, SourceProvenanceReferenceV1) for item in references):
        raise CanonicalError(
            "REF_TARGET_MISSING",
            "source_references must contain canonical C2 source references",
        )
    ordered = tuple(sorted(references, key=lambda item: canonical_json_bytes(item.to_dict())))
    encoded = tuple(canonical_json_bytes(item.to_dict()) for item in ordered)
    if len(set(encoded)) != len(encoded):
        raise CanonicalError("SCHEMA_VIOLATION", "source_references must be unique")
    return ordered


@dataclass(frozen=True, slots=True)
class ScoringRuleSetReferenceV2:
    stable_id: str
    revision_id: str
    record_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stable_id",
            _prefixed_identity(self.stable_id, _SCORING_STABLE_PREFIX, "stable_id"),
        )
        object.__setattr__(
            self,
            "revision_id",
            _prefixed_identity(self.revision_id, _SCORING_REVISION_PREFIX, "revision_id"),
        )
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))

    @classmethod
    def from_rule_set(cls, value: ScoringRuleSetV2) -> "ScoringRuleSetReferenceV2":
        if not isinstance(value, ScoringRuleSetV2) or not value.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "scoring rule set identity is invalid")
        return cls(value.stable_id, value.revision_id, value.record_sha256)

    def to_dict(self) -> dict[str, str]:
        return {
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class EvidenceMatrixReferenceV2:
    stable_id: str
    revision_id: str
    record_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stable_id",
            _prefixed_identity(self.stable_id, _MATRIX_STABLE_PREFIX, "stable_id"),
        )
        object.__setattr__(
            self,
            "revision_id",
            _prefixed_identity(self.revision_id, _MATRIX_REVISION_PREFIX, "revision_id"),
        )
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))

    @classmethod
    def from_matrix(cls, value: "TechnicalBidEvidenceMatrixV2") -> "EvidenceMatrixReferenceV2":
        if not isinstance(value, TechnicalBidEvidenceMatrixV2) or not value.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "evidence matrix identity is invalid")
        return cls(value.stable_id, value.revision_id, value.record_sha256)

    def to_dict(self) -> dict[str, str]:
        return {
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class TechnicalBidEvidenceRequirementV2:
    requirement_id: str
    rule_id: str
    evidence_kind: str
    description: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]

    @classmethod
    def create(
        cls,
        *,
        requirement_id: str,
        rule_id: str,
        evidence_kind: str,
        description: str,
        source_references: Sequence[SourceProvenanceReferenceV1],
    ) -> "TechnicalBidEvidenceRequirementV2":
        requirement_id = _nonempty(requirement_id, "requirement_id")
        rule_id = _nonempty(rule_id, "rule_id")
        evidence_kind = normalize_text(evidence_kind)
        if not _EVIDENCE_KIND_RE.fullmatch(evidence_kind):
            raise CanonicalError("SCHEMA_VIOLATION", "evidence_kind must be a lowercase token")
        description = _nonempty(description, "description", human_text=True)
        references = _ordered_source_references(source_references)
        return cls(requirement_id, rule_id, evidence_kind, description, references)

    def to_content_projection(self) -> dict[str, str]:
        return {
            "description": self.description,
            "evidence_kind": self.evidence_kind,
            "requirement_id": self.requirement_id,
            "rule_id": self.rule_id,
        }

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = self.to_content_projection()
        value["source_references"] = [item.to_dict() for item in self.source_references]
        return value


@dataclass(frozen=True, slots=True)
class TechnicalBidEvidenceMatrixProvenanceV2:
    source_mode_set: tuple[str, ...]
    scoring_rule_set: ScoringRuleSetReferenceV2
    requirement_source_references: tuple[
        tuple[str, tuple[SourceProvenanceReferenceV1, ...]], ...
    ]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        scoring_rule_set: ScoringRuleSetV2,
        requirements: Sequence[TechnicalBidEvidenceRequirementV2],
    ) -> "TechnicalBidEvidenceMatrixProvenanceV2":
        modes = normalize_source_modes(source_mode_set)
        reference = ScoringRuleSetReferenceV2.from_rule_set(scoring_rule_set)
        sources = tuple((item.requirement_id, item.source_references) for item in requirements)
        return cls(modes, reference, sources)

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "effective_source_mode": self.effective_source_mode,
            "requirement_source_references": [
                {
                    "requirement_id": requirement_id,
                    "source_references": [item.to_dict() for item in references],
                }
                for requirement_id, references in self.requirement_source_references
            ],
            "scoring_rule_set": self.scoring_rule_set.to_dict(),
            "source_mode_set": list(self.source_mode_set),
        }


@dataclass(frozen=True, slots=True)
class TechnicalBidEvidenceMatrixInputV2:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    scoring_rule_set: ScoringRuleSetV2
    requirements: tuple[TechnicalBidEvidenceRequirementV2, ...]
    parent_revision_id: str | None = None

    def __post_init__(self) -> None:
        namespace = _nonempty(self.origin_namespace, "origin_namespace")
        key = _nonempty(self.origin_key, "origin_key")
        origin_mode = normalize_source_modes((self.origin_source_mode,))[0]
        modes = normalize_source_modes(self.source_mode_set)
        if not isinstance(self.scoring_rule_set, ScoringRuleSetV2) or not self.scoring_rule_set.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "scoring_rule_set must have a valid C2 identity")
        require_no_source_mode_promotion(self.scoring_rule_set.provenance.source_mode_set, modes)
        requirements = tuple(
            sorted(self.requirements, key=lambda item: item.requirement_id.encode("utf-8"))
        )
        if not requirements or any(
            not isinstance(item, TechnicalBidEvidenceRequirementV2) for item in requirements
        ):
            raise CanonicalError("SCHEMA_VIOLATION", "requirements must contain canonical values")
        requirement_ids = tuple(item.requirement_id for item in requirements)
        if len(set(requirement_ids)) != len(requirement_ids):
            raise CanonicalError("SCHEMA_VIOLATION", "requirement_id values must be unique")
        expected_rule_ids = {item.rule_id for item in self.scoring_rule_set.rules}
        actual_rule_ids = {item.rule_id for item in requirements}
        if actual_rule_ids != expected_rule_ids:
            raise CanonicalError(
                "REF_TARGET_MISSING",
                "requirements must cover every and only referenced scoring rule",
            )
        parent = normalize_text(self.parent_revision_id) if self.parent_revision_id is not None else None
        if parent == "":
            raise CanonicalError("ID_PARENT_INVALID", "parent_revision_id must be null or non-empty")
        object.__setattr__(self, "origin_namespace", namespace)
        object.__setattr__(self, "origin_key", key)
        object.__setattr__(self, "origin_source_mode", origin_mode)
        object.__setattr__(self, "source_mode_set", modes)
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "parent_revision_id", parent)


@dataclass(frozen=True, slots=True)
class TechnicalBidEvidenceMatrixV2:
    artifact_type: str
    schema_version: str
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    stable_id: str
    revision_id: str
    parent_revision_id: str | None
    content_sha256: str
    provenance_sha256: str
    record_sha256: str
    requirements: tuple[TechnicalBidEvidenceRequirementV2, ...]
    provenance: TechnicalBidEvidenceMatrixProvenanceV2
    review_state: str
    accepted_for_response_use: bool

    ARTIFACT_TYPE: ClassVar[str] = "technical-bid-evidence-matrix"
    SCHEMA_VERSION: ClassVar[str] = "2"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(cls, source: TechnicalBidEvidenceMatrixInputV2) -> "TechnicalBidEvidenceMatrixV2":
        content = {"requirements": [item.to_content_projection() for item in source.requirements]}
        provenance = TechnicalBidEvidenceMatrixProvenanceV2.create(
            source_mode_set=source.source_mode_set,
            scoring_rule_set=source.scoring_rule_set,
            requirements=source.requirements,
        )
        provenance_projection = provenance.to_projection()
        stable_projection = cls._stable_projection(
            source.origin_namespace,
            source.origin_key,
            source.origin_source_mode,
        )
        content_sha256 = profile_digest(
            "content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            provenance_projection,
        )
        stable_id = derive_stable_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, stable_projection)
        revision_id = derive_revision_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": source.parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_projection = cls._record_projection(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            parent_revision_id=source.parent_revision_id,
            content_sha256=content_sha256,
            provenance_sha256=provenance_sha256,
            requirements=source.requirements,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection
        )
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            source.origin_namespace,
            source.origin_key,
            source.origin_source_mode,
            stable_id,
            revision_id,
            source.parent_revision_id,
            content_sha256,
            provenance_sha256,
            record_sha256,
            source.requirements,
            provenance,
            "UNREVIEWED",
            False,
        )

    @classmethod
    def _stable_projection(cls, namespace: str, key: str, mode: str) -> dict[str, str]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": key,
            "origin_namespace": namespace,
            "origin_source_mode": mode,
            "schema_version": cls.SCHEMA_VERSION,
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "accepted_for_response_use": False,
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": values["parent_revision_id"],
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "requirements": [item.to_dict() for item in values["requirements"]],
            "review_state": "UNREVIEWED",
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        content = {"requirements": [item.to_content_projection() for item in self.requirements]}
        provenance = self.provenance.to_projection()
        content_sha256 = profile_digest(
            "content-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, provenance
        )
        stable_id = derive_stable_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._stable_projection(
                self.origin_namespace,
                self.origin_key,
                self.origin_source_mode,
            ),
        )
        revision_id = derive_revision_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": self.parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_sha256 = profile_digest(
            "record-sha256",
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._record_projection(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                stable_id=stable_id,
                revision_id=revision_id,
                parent_revision_id=self.parent_revision_id,
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                requirements=self.requirements,
                provenance=provenance,
            ),
        )
        return all(
            (
                identities_equal(self.content_sha256, content_sha256),
                identities_equal(self.provenance_sha256, provenance_sha256),
                identities_equal(self.stable_id, stable_id),
                identities_equal(self.revision_id, revision_id),
                identities_equal(self.record_sha256, record_sha256),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        value = self._record_projection(
            origin_namespace=self.origin_namespace,
            origin_key=self.origin_key,
            origin_source_mode=self.origin_source_mode,
            stable_id=self.stable_id,
            revision_id=self.revision_id,
            parent_revision_id=self.parent_revision_id,
            content_sha256=self.content_sha256,
            provenance_sha256=self.provenance_sha256,
            requirements=self.requirements,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value


@dataclass(frozen=True, slots=True)
class ResponseEvidenceItemV2:
    evidence_id: str
    requirement_id: str
    evidence_kind: str
    statement: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]

    @classmethod
    def create(
        cls,
        *,
        evidence_id: str,
        requirement_id: str,
        evidence_kind: str,
        statement: str,
        source_references: Sequence[SourceProvenanceReferenceV1],
    ) -> "ResponseEvidenceItemV2":
        evidence_id = _nonempty(evidence_id, "evidence_id")
        requirement_id = _nonempty(requirement_id, "requirement_id")
        evidence_kind = normalize_text(evidence_kind)
        if not _EVIDENCE_KIND_RE.fullmatch(evidence_kind):
            raise CanonicalError("SCHEMA_VIOLATION", "evidence_kind must be a lowercase token")
        statement = _nonempty(statement, "statement", human_text=True)
        references = _ordered_source_references(source_references)
        return cls(evidence_id, requirement_id, evidence_kind, statement, references)

    def to_content_projection(self) -> dict[str, str]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_kind": self.evidence_kind,
            "requirement_id": self.requirement_id,
            "statement": self.statement,
        }

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = self.to_content_projection()
        value["source_references"] = [item.to_dict() for item in self.source_references]
        return value


@dataclass(frozen=True, slots=True)
class ResponseEvidenceSetProvenanceV2:
    source_mode_set: tuple[str, ...]
    evidence_matrix: EvidenceMatrixReferenceV2
    evidence_source_references: tuple[
        tuple[str, tuple[SourceProvenanceReferenceV1, ...]], ...
    ]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        evidence_matrix: TechnicalBidEvidenceMatrixV2,
        evidence_items: Sequence[ResponseEvidenceItemV2],
    ) -> "ResponseEvidenceSetProvenanceV2":
        modes = normalize_source_modes(source_mode_set)
        reference = EvidenceMatrixReferenceV2.from_matrix(evidence_matrix)
        sources = tuple((item.evidence_id, item.source_references) for item in evidence_items)
        return cls(modes, reference, sources)

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "effective_source_mode": self.effective_source_mode,
            "evidence_matrix": self.evidence_matrix.to_dict(),
            "evidence_source_references": [
                {
                    "evidence_id": evidence_id,
                    "source_references": [item.to_dict() for item in references],
                }
                for evidence_id, references in self.evidence_source_references
            ],
            "source_mode_set": list(self.source_mode_set),
        }


@dataclass(frozen=True, slots=True)
class ResponseEvidenceSetInputV2:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    evidence_matrix: TechnicalBidEvidenceMatrixV2
    evidence_items: tuple[ResponseEvidenceItemV2, ...]
    parent_revision_id: str | None = None

    def __post_init__(self) -> None:
        namespace = _nonempty(self.origin_namespace, "origin_namespace")
        key = _nonempty(self.origin_key, "origin_key")
        origin_mode = normalize_source_modes((self.origin_source_mode,))[0]
        modes = normalize_source_modes(self.source_mode_set)
        if not isinstance(self.evidence_matrix, TechnicalBidEvidenceMatrixV2) or not self.evidence_matrix.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "evidence_matrix must have a valid C3 identity")
        require_no_source_mode_promotion(self.evidence_matrix.provenance.source_mode_set, modes)
        items = tuple(sorted(self.evidence_items, key=lambda item: item.evidence_id.encode("utf-8")))
        if not items or any(not isinstance(item, ResponseEvidenceItemV2) for item in items):
            raise CanonicalError("SCHEMA_VIOLATION", "evidence_items must contain canonical values")
        evidence_ids = tuple(item.evidence_id for item in items)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise CanonicalError("SCHEMA_VIOLATION", "evidence_id values must be unique")
        requirements = {
            item.requirement_id: item.evidence_kind for item in self.evidence_matrix.requirements
        }
        covered: set[str] = set()
        for item in items:
            expected_kind = requirements.get(item.requirement_id)
            if expected_kind is None:
                raise CanonicalError(
                    "REF_TARGET_MISSING", "response evidence references an unknown requirement"
                )
            if item.evidence_kind != expected_kind:
                raise CanonicalError(
                    "REF_TARGET_MISSING", "response evidence kind does not match its requirement"
                )
            covered.add(item.requirement_id)
        if covered != set(requirements):
            raise CanonicalError(
                "REF_TARGET_MISSING", "response evidence must cover every matrix requirement"
            )
        parent = normalize_text(self.parent_revision_id) if self.parent_revision_id is not None else None
        if parent == "":
            raise CanonicalError("ID_PARENT_INVALID", "parent_revision_id must be null or non-empty")
        object.__setattr__(self, "origin_namespace", namespace)
        object.__setattr__(self, "origin_key", key)
        object.__setattr__(self, "origin_source_mode", origin_mode)
        object.__setattr__(self, "source_mode_set", modes)
        object.__setattr__(self, "evidence_items", items)
        object.__setattr__(self, "parent_revision_id", parent)


@dataclass(frozen=True, slots=True)
class ResponseEvidenceSetV2:
    artifact_type: str
    schema_version: str
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    stable_id: str
    revision_id: str
    parent_revision_id: str | None
    content_sha256: str
    provenance_sha256: str
    record_sha256: str
    evidence_items: tuple[ResponseEvidenceItemV2, ...]
    provenance: ResponseEvidenceSetProvenanceV2
    review_state: str
    accepted_for_response_use: bool

    ARTIFACT_TYPE: ClassVar[str] = "response-evidence-set"
    SCHEMA_VERSION: ClassVar[str] = "2"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(cls, source: ResponseEvidenceSetInputV2) -> "ResponseEvidenceSetV2":
        content = {"evidence_items": [item.to_content_projection() for item in source.evidence_items]}
        provenance = ResponseEvidenceSetProvenanceV2.create(
            source_mode_set=source.source_mode_set,
            evidence_matrix=source.evidence_matrix,
            evidence_items=source.evidence_items,
        )
        provenance_projection = provenance.to_projection()
        stable_projection = cls._stable_projection(
            source.origin_namespace,
            source.origin_key,
            source.origin_source_mode,
        )
        content_sha256 = profile_digest(
            "content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            provenance_projection,
        )
        stable_id = derive_stable_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, stable_projection)
        revision_id = derive_revision_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": source.parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_projection = cls._record_projection(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            parent_revision_id=source.parent_revision_id,
            content_sha256=content_sha256,
            provenance_sha256=provenance_sha256,
            evidence_items=source.evidence_items,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection
        )
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            source.origin_namespace,
            source.origin_key,
            source.origin_source_mode,
            stable_id,
            revision_id,
            source.parent_revision_id,
            content_sha256,
            provenance_sha256,
            record_sha256,
            source.evidence_items,
            provenance,
            "UNREVIEWED",
            False,
        )

    @classmethod
    def _stable_projection(cls, namespace: str, key: str, mode: str) -> dict[str, str]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": key,
            "origin_namespace": namespace,
            "origin_source_mode": mode,
            "schema_version": cls.SCHEMA_VERSION,
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "accepted_for_response_use": False,
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "evidence_items": [item.to_dict() for item in values["evidence_items"]],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": values["parent_revision_id"],
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "review_state": "UNREVIEWED",
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        content = {"evidence_items": [item.to_content_projection() for item in self.evidence_items]}
        provenance = self.provenance.to_projection()
        content_sha256 = profile_digest(
            "content-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, provenance
        )
        stable_id = derive_stable_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._stable_projection(
                self.origin_namespace,
                self.origin_key,
                self.origin_source_mode,
            ),
        )
        revision_id = derive_revision_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": self.parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_sha256 = profile_digest(
            "record-sha256",
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._record_projection(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                stable_id=stable_id,
                revision_id=revision_id,
                parent_revision_id=self.parent_revision_id,
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                evidence_items=self.evidence_items,
                provenance=provenance,
            ),
        )
        return all(
            (
                identities_equal(self.content_sha256, content_sha256),
                identities_equal(self.provenance_sha256, provenance_sha256),
                identities_equal(self.stable_id, stable_id),
                identities_equal(self.revision_id, revision_id),
                identities_equal(self.record_sha256, record_sha256),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        value = self._record_projection(
            origin_namespace=self.origin_namespace,
            origin_key=self.origin_key,
            origin_source_mode=self.origin_source_mode,
            stable_id=self.stable_id,
            revision_id=self.revision_id,
            parent_revision_id=self.parent_revision_id,
            content_sha256=self.content_sha256,
            provenance_sha256=self.provenance_sha256,
            evidence_items=self.evidence_items,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
