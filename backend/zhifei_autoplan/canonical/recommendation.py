"""Pure RecommendationV1 boundary for Route C.

The record is a canonical, reference-only projection of exactly one verified
ReviewInputV2.  It does not emit review events or perform workflow, approval,
feedback, or state-transition work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from .common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    derive_revision_id,
    derive_stable_id,
    identities_equal,
    normalize_text,
    profile_digest,
    validate_digest,
)
from .review import DiagnosticResultSetReferenceV1, ReviewTargetReferenceV1
from .review_v2 import ReviewInputV2


def _nonempty(value: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


@dataclass(frozen=True, slots=True)
class SourceReviewInputReferenceV2:
    """Complete identity reference to the one verified ReviewInputV2 source."""

    artifact_type: str
    schema_version: str
    stable_id: str
    revision_id: str
    record_sha256: str

    def __post_init__(self) -> None:
        if self.artifact_type != ReviewInputV2.ARTIFACT_TYPE:
            raise CanonicalError("SCHEMA_VIOLATION", "source artifact_type must be review-input")
        if self.schema_version != ReviewInputV2.SCHEMA_VERSION:
            raise CanonicalError("SCHEMA_VIOLATION", "source schema_version must be 2")
        stable_id = normalize_text(self.stable_id)
        revision_id = normalize_text(self.revision_id)
        stable_prefix = f"ocrc:{ReviewInputV2.ARTIFACT_TYPE}:"
        revision_prefix = f"ocrc-rev:{ReviewInputV2.ARTIFACT_TYPE}:"
        if not stable_id.startswith(stable_prefix) or not revision_id.startswith(revision_prefix):
            raise CanonicalError("REVIEW_IDENTITY_INVALID", "source review identity prefix mismatch")
        validate_digest(stable_id[len(stable_prefix) :])
        validate_digest(revision_id[len(revision_prefix) :])
        object.__setattr__(self, "stable_id", stable_id)
        object.__setattr__(self, "revision_id", revision_id)
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))

    @classmethod
    def from_verified_review_input(
        cls, source: ReviewInputV2
    ) -> "SourceReviewInputReferenceV2":
        return cls(
            source.artifact_type,
            source.schema_version,
            source.stable_id,
            source.revision_id,
            source.record_sha256,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_type": self.artifact_type,
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "schema_version": self.schema_version,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class RecommendationProvenanceV1:
    """Canonical provenance that binds RecommendationV1 to its only source."""

    bootstrap_rule_id: str
    canonical_profile_id: str
    canonical_json_algorithm: str
    source_review_input: SourceReviewInputReferenceV2

    def __post_init__(self) -> None:
        if self.bootstrap_rule_id != BOOTSTRAP_RULE_ID:
            raise CanonicalError("SCHEMA_VIOLATION", "bootstrap_rule_id mismatch")
        if self.canonical_profile_id != CANONICAL_PROFILE_ID:
            raise CanonicalError("SCHEMA_VIOLATION", "canonical_profile_id mismatch")
        if self.canonical_json_algorithm != CANONICAL_JSON_ALGORITHM:
            raise CanonicalError("SCHEMA_VIOLATION", "canonical_json_algorithm mismatch")
        if type(self.source_review_input) is not SourceReviewInputReferenceV2:
            raise CanonicalError("SCHEMA_VIOLATION", "source_review_input reference is invalid")

    @classmethod
    def from_source(
        cls, source_review_input: SourceReviewInputReferenceV2
    ) -> "RecommendationProvenanceV1":
        return cls(
            BOOTSTRAP_RULE_ID,
            CANONICAL_PROFILE_ID,
            CANONICAL_JSON_ALGORITHM,
            source_review_input,
        )

    def to_projection(self) -> dict[str, Any]:
        return {
            "bootstrap_rule_id": self.bootstrap_rule_id,
            "canonical_json_algorithm": self.canonical_json_algorithm,
            "canonical_profile_id": self.canonical_profile_id,
            "source_review_input": self.source_review_input.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RecommendationV1:
    """Canonical recommendation boundary derived only from verified ReviewInputV2."""

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
    provenance: RecommendationProvenanceV1
    source_review_input: SourceReviewInputReferenceV2

    ARTIFACT_TYPE: ClassVar[str] = "recommendation"
    SCHEMA_VERSION: ClassVar[str] = "1"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def from_verified_review_input(cls, source: ReviewInputV2) -> "RecommendationV1":
        """Construct without accepting caller-controlled source or field overrides."""

        if type(source) is not ReviewInputV2 or not source.verify_identity():
            raise CanonicalError("REVIEW_IDENTITY_INVALID", "source ReviewInputV2 identity is invalid")
        if source.target.artifact_type == cls.ARTIFACT_TYPE:
            raise CanonicalError(
                "BOOTSTRAP_CYCLE_FORBIDDEN",
                "RecommendationV1 source chain must be non-circular",
            )
        namespace = _nonempty(source.origin_namespace, "origin_namespace")
        key = _nonempty(source.origin_key, "origin_key")
        origin_mode = _nonempty(source.origin_source_mode, "origin_source_mode")
        source_reference = SourceReviewInputReferenceV2.from_verified_review_input(source)
        provenance = RecommendationProvenanceV1.from_source(source_reference)

        content_projection = cls._content_projection(
            source.target,
            source.diagnostic_result_set,
            source_reference,
        )
        content_sha256 = profile_digest(
            "content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content_projection
        )
        provenance_projection = provenance.to_projection()
        provenance_sha256 = profile_digest(
            "provenance-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            provenance_projection,
        )
        stable_id = derive_stable_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            cls._stable_projection(namespace, key, origin_mode),
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
                target=source.target,
                diagnostic_result_set=source.diagnostic_result_set,
                provenance=provenance_projection,
                source_review_input=source_reference,
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
            source.target,
            source.diagnostic_result_set,
            provenance,
            source_reference,
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
        source_review_input: SourceReviewInputReferenceV2,
    ) -> dict[str, Any]:
        return {
            "diagnostic_result_set": diagnostic_result_set.to_dict(),
            "source_review_input": source_review_input.to_dict(),
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
            "source_review_input": values["source_review_input"].to_dict(),
            "stable_id": values["stable_id"],
            "target": values["target"].to_dict(),
        }

    def verify_identity(self) -> bool:
        try:
            content_projection = self._content_projection(
                self.target,
                self.diagnostic_result_set,
                self.source_review_input,
            )
            content_sha256 = profile_digest(
                "content-sha256",
                self.ARTIFACT_TYPE,
                self.SCHEMA_VERSION,
                content_projection,
            )
            provenance_projection = self.provenance.to_projection()
            provenance_sha256 = profile_digest(
                "provenance-sha256",
                self.ARTIFACT_TYPE,
                self.SCHEMA_VERSION,
                provenance_projection,
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
                    provenance=provenance_projection,
                    source_review_input=self.source_review_input,
                ),
            )
        except (CanonicalError, AttributeError, TypeError, ValueError):
            return False
        return all(
            (
                self.artifact_type == self.ARTIFACT_TYPE,
                self.schema_version == self.SCHEMA_VERSION,
                self.parent_revision_id is None,
                self.target.artifact_type != self.ARTIFACT_TYPE,
                self.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID,
                self.provenance.canonical_profile_id == CANONICAL_PROFILE_ID,
                self.provenance.canonical_json_algorithm == CANONICAL_JSON_ALGORITHM,
                self.provenance.source_review_input == self.source_review_input,
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
            source_review_input=self.source_review_input,
        )
        value["record_sha256"] = self.record_sha256
        return value
