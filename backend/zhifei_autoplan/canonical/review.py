"""Pure C6 review-input foundation for Route C.

This module creates an immutable, reference-only handoff for later review
stages.  It verifies prior canonical identities and their diagnostic linkage,
but deliberately performs no human workflow, approval, recommendation, state
transition, or review-event work.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final

from .chapter import ChapterSetV1
from .common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
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
from .diagnostic import DiagnosticResultSetV1, DiagnosticSourceReferenceV1
from .evidence import (
    ResponseEvidenceSetV2,
    TechnicalBidEvidenceMatrixV2,
)
from .material import ProjectMaterialBundleV1
from .scoring import ScoringRuleSetV2


_REVIEWABLE_TYPES: Final = (
    ProjectMaterialBundleV1,
    ScoringRuleSetV2,
    TechnicalBidEvidenceMatrixV2,
    ResponseEvidenceSetV2,
    ChapterSetV1,
)
_INITIAL_REVIEW_STATES: Final = frozenset({"PROVISIONAL", "UNREVIEWED"})


def _nonempty(value: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _require_reviewable_artifact(value: Any) -> None:
    if not isinstance(value, _REVIEWABLE_TYPES) or not value.verify_identity():
        raise CanonicalError(
            "REVIEW_IDENTITY_INVALID",
            "review target must be an identity-verified canonical artifact",
        )
    if value.review_state not in _INITIAL_REVIEW_STATES:
        raise CanonicalError(
            "REVIEW_STATE_INVALID",
            "review target must be in its canonical initial review state",
        )
    if value.accepted_for_response_use is not False:
        raise CanonicalError(
            "REVIEW_STATE_INVALID",
            "review input cannot target an artifact already accepted for response use",
        )


def _matching_diagnostic_source(
    target: Any,
    diagnostics: DiagnosticResultSetV1,
) -> DiagnosticSourceReferenceV1:
    matches = tuple(
        item
        for item in diagnostics.provenance.source_references
        if item.artifact_type == target.artifact_type
        and identities_equal(item.stable_id, target.stable_id)
        and identities_equal(item.revision_id, target.revision_id)
        and identities_equal(item.record_sha256, target.record_sha256)
    )
    if len(matches) != 1:
        raise CanonicalError(
            "REF_TARGET_MISSING",
            "diagnostic result set must contain exactly one reference to the review target",
        )
    return matches[0]


@dataclass(frozen=True, slots=True)
class ReviewTargetReferenceV1:
    """Identity and initial state of one canonical artifact under review."""

    source_index: int
    artifact_type: str
    schema_version: str
    stable_id: str
    revision_id: str
    record_sha256: str
    review_state: str
    accepted_for_response_use: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_index, int)
            or isinstance(self.source_index, bool)
            or self.source_index < 0
        ):
            raise CanonicalError("SCHEMA_VIOLATION", "source_index must be non-negative")
        artifact_type = _nonempty(self.artifact_type, "artifact_type")
        schema_version = _nonempty(self.schema_version, "schema_version")
        stable_id = normalize_text(self.stable_id)
        revision_id = normalize_text(self.revision_id)
        stable_prefix = f"ocrc:{artifact_type}:"
        revision_prefix = f"ocrc-rev:{artifact_type}:"
        if not stable_id.startswith(stable_prefix) or not revision_id.startswith(revision_prefix):
            raise CanonicalError("REVIEW_IDENTITY_INVALID", "review target identity prefix mismatch")
        validate_digest(stable_id[len(stable_prefix) :])
        validate_digest(revision_id[len(revision_prefix) :])
        review_state = normalize_text(self.review_state)
        if review_state not in _INITIAL_REVIEW_STATES or self.accepted_for_response_use is not False:
            raise CanonicalError("REVIEW_STATE_INVALID", "review target is not in an initial state")
        object.__setattr__(self, "artifact_type", artifact_type)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "stable_id", stable_id)
        object.__setattr__(self, "revision_id", revision_id)
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))
        object.__setattr__(self, "review_state", review_state)

    @classmethod
    def from_artifact(
        cls,
        value: Any,
        source_reference: DiagnosticSourceReferenceV1,
    ) -> "ReviewTargetReferenceV1":
        _require_reviewable_artifact(value)
        return cls(
            source_reference.source_index,
            value.artifact_type,
            value.schema_version,
            value.stable_id,
            value.revision_id,
            value.record_sha256,
            value.review_state,
            value.accepted_for_response_use,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_for_response_use": self.accepted_for_response_use,
            "artifact_type": self.artifact_type,
            "record_sha256": self.record_sha256,
            "review_state": self.review_state,
            "revision_id": self.revision_id,
            "schema_version": self.schema_version,
            "source_index": self.source_index,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticResultSetReferenceV1:
    stable_id: str
    revision_id: str
    record_sha256: str
    diagnostic_count: int
    first_error_code: str

    def __post_init__(self) -> None:
        stable_prefix = "ocrc:diagnostic-result-set:"
        revision_prefix = "ocrc-rev:diagnostic-result-set:"
        stable_id = normalize_text(self.stable_id)
        revision_id = normalize_text(self.revision_id)
        if not stable_id.startswith(stable_prefix) or not revision_id.startswith(revision_prefix):
            raise CanonicalError("REVIEW_IDENTITY_INVALID", "diagnostic identity prefix mismatch")
        validate_digest(stable_id[len(stable_prefix) :])
        validate_digest(revision_id[len(revision_prefix) :])
        if (
            not isinstance(self.diagnostic_count, int)
            or isinstance(self.diagnostic_count, bool)
            or self.diagnostic_count < 0
        ):
            raise CanonicalError("SCHEMA_VIOLATION", "diagnostic_count must be non-negative")
        object.__setattr__(self, "stable_id", stable_id)
        object.__setattr__(self, "revision_id", revision_id)
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))
        object.__setattr__(self, "first_error_code", _nonempty(self.first_error_code, "first_error_code"))

    @classmethod
    def from_result_set(cls, value: DiagnosticResultSetV1) -> "DiagnosticResultSetReferenceV1":
        if not isinstance(value, DiagnosticResultSetV1) or not value.verify_identity():
            raise CanonicalError(
                "REVIEW_IDENTITY_INVALID",
                "diagnostic result set must have a valid canonical identity",
            )
        return cls(
            value.stable_id,
            value.revision_id,
            value.record_sha256,
            len(value.diagnostics),
            value.first_error_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_count": self.diagnostic_count,
            "first_error_code": self.first_error_code,
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class ReviewInputProvenanceV1:
    bootstrap_rule_id: str
    canonical_profile_id: str
    canonical_json_algorithm: str
    source_mode_set: tuple[str, ...]

    @classmethod
    def create(cls, source_mode_set: Sequence[str]) -> "ReviewInputProvenanceV1":
        return cls(
            BOOTSTRAP_RULE_ID,
            CANONICAL_PROFILE_ID,
            CANONICAL_JSON_ALGORITHM,
            normalize_source_modes(source_mode_set),
        )

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "bootstrap_rule_id": self.bootstrap_rule_id,
            "canonical_json_algorithm": self.canonical_json_algorithm,
            "canonical_profile_id": self.canonical_profile_id,
            "effective_source_mode": self.effective_source_mode,
            "source_mode_set": list(self.source_mode_set),
        }


@dataclass(frozen=True, slots=True)
class ReviewInputV1:
    """Canonical reference-only input for a later, separately scoped review."""

    artifact_type: str
    schema_version: str
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    stable_id: str
    revision_id: str
    parent_revision_id: None
    content_sha256: str
    provenance_sha256: str
    record_sha256: str
    target: ReviewTargetReferenceV1
    diagnostic_result_set: DiagnosticResultSetReferenceV1
    provenance: ReviewInputProvenanceV1

    ARTIFACT_TYPE: ClassVar[str] = "review-input"
    SCHEMA_VERSION: ClassVar[str] = "1"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(
        cls,
        *,
        origin_namespace: str,
        origin_key: str,
        origin_source_mode: str,
        source_mode_set: Sequence[str],
        target: Any,
        diagnostic_result_set: DiagnosticResultSetV1,
    ) -> "ReviewInputV1":
        namespace = _nonempty(origin_namespace, "origin_namespace")
        key = _nonempty(origin_key, "origin_key")
        origin_mode = normalize_source_modes((origin_source_mode,))[0]
        _require_reviewable_artifact(target)
        diagnostic_reference = DiagnosticResultSetReferenceV1.from_result_set(
            diagnostic_result_set
        )
        source_reference = _matching_diagnostic_source(target, diagnostic_result_set)
        target_reference = ReviewTargetReferenceV1.from_artifact(target, source_reference)
        provenance = ReviewInputProvenanceV1.create(source_mode_set)
        require_no_source_mode_promotion((origin_mode,), provenance.source_mode_set)
        require_no_source_mode_promotion(
            target.provenance.source_mode_set,
            provenance.source_mode_set,
        )
        require_no_source_mode_promotion(
            diagnostic_result_set.provenance.source_mode_set,
            provenance.source_mode_set,
        )

        content = cls._content_projection(target_reference, diagnostic_reference)
        provenance_projection = provenance.to_projection()
        stable_id = derive_stable_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            cls._stable_projection(namespace, key, origin_mode),
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
        revision_id = derive_revision_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": None,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_sha256 = profile_digest(
            "record-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            cls._record_projection(
                origin_namespace=namespace,
                origin_key=key,
                origin_source_mode=origin_mode,
                stable_id=stable_id,
                revision_id=revision_id,
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                target=target_reference,
                diagnostic_result_set=diagnostic_reference,
                provenance=provenance_projection,
            ),
        )
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            namespace,
            key,
            origin_mode,
            stable_id,
            revision_id,
            None,
            content_sha256,
            provenance_sha256,
            record_sha256,
            target_reference,
            diagnostic_reference,
            provenance,
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

    @staticmethod
    def _content_projection(
        target: ReviewTargetReferenceV1,
        diagnostic_result_set: DiagnosticResultSetReferenceV1,
    ) -> dict[str, Any]:
        return {
            "diagnostic_result_set": diagnostic_result_set.to_dict(),
            "target": target.to_dict(),
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "diagnostic_result_set": values["diagnostic_result_set"].to_dict(),
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": None,
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
            "target": values["target"].to_dict(),
        }

    @property
    def first_error_code(self) -> str:
        return self.diagnostic_result_set.first_error_code

    def verify_identity(self) -> bool:
        content = self._content_projection(self.target, self.diagnostic_result_set)
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
                "parent_revision_id": None,
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
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                target=self.target,
                diagnostic_result_set=self.diagnostic_result_set,
                provenance=provenance,
            ),
        )
        return all(
            (
                self.artifact_type == self.ARTIFACT_TYPE,
                self.schema_version == self.SCHEMA_VERSION,
                self.parent_revision_id is None,
                self.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID,
                self.provenance.canonical_profile_id == CANONICAL_PROFILE_ID,
                self.provenance.canonical_json_algorithm == CANONICAL_JSON_ALGORITHM,
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
            content_sha256=self.content_sha256,
            provenance_sha256=self.provenance_sha256,
            target=self.target,
            diagnostic_result_set=self.diagnostic_result_set,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
