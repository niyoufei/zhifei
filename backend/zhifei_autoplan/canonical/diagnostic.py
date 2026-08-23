"""Immutable C5 diagnostic-result foundation for Route C.

This module is a deterministic data boundary only.  It canonicalizes explicit
diagnostics and reference-only source identities; it does not execute a
diagnostic engine, perform human review, or create recommendations/events.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final
import re

from .common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    PHASE_RANK,
    CanonicalError,
    DiagnosticV1,
    canonical_json_bytes,
    derive_revision_id,
    derive_stable_id,
    effective_source_mode,
    first_error_diagnostic,
    identities_equal,
    normalize_source_modes,
    normalize_text,
    profile_digest,
    require_no_source_mode_promotion,
    validate_digest,
)


_ARTIFACT_TYPE_RE: Final = re.compile(r"^[a-z][a-z0-9-]*$")
_DIAGNOSTIC_ARTIFACT_TYPE: Final = "diagnostic-result-set"


def _nonempty(value: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _diagnostic_order_key(item: DiagnosticV1) -> tuple[int, bytes, bytes, int]:
    """Use the frozen Route C first-error ordering for the whole result set."""

    return (
        PHASE_RANK[item.phase],
        item.json_pointer.encode("utf-8"),
        item.code.encode("utf-8"),
        item.source_index,
    )


@dataclass(frozen=True, slots=True)
class DiagnosticSourceReferenceV1:
    """Reference-only identity for a source examined before C5."""

    source_index: int
    artifact_type: str
    stable_id: str
    revision_id: str
    record_sha256: str

    @classmethod
    def create(
        cls,
        *,
        source_index: int,
        artifact_type: str,
        stable_id: str,
        revision_id: str,
        record_sha256: str,
    ) -> "DiagnosticSourceReferenceV1":
        if not isinstance(source_index, int) or isinstance(source_index, bool) or source_index < 0:
            raise CanonicalError("SCHEMA_VIOLATION", "source_index must be a non-negative integer")
        artifact_type = normalize_text(artifact_type)
        if not _ARTIFACT_TYPE_RE.fullmatch(artifact_type):
            raise CanonicalError("SCHEMA_VIOLATION", "artifact_type must be a lowercase token")
        if artifact_type == _DIAGNOSTIC_ARTIFACT_TYPE:
            raise CanonicalError(
                "BOOTSTRAP_CYCLE_FORBIDDEN",
                "initial diagnostic results cannot reference a diagnostic result set",
            )
        stable_id = normalize_text(stable_id)
        revision_id = normalize_text(revision_id)
        stable_prefix = f"ocrc:{artifact_type}:"
        revision_prefix = f"ocrc-rev:{artifact_type}:"
        if not stable_id.startswith(stable_prefix) or not revision_id.startswith(revision_prefix):
            raise CanonicalError("REF_TARGET_MISSING", "source identities do not match artifact_type")
        validate_digest(stable_id[len(stable_prefix) :])
        validate_digest(revision_id[len(revision_prefix) :])
        return cls(
            source_index,
            artifact_type,
            stable_id,
            revision_id,
            validate_digest(record_sha256),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "source_index": self.source_index,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticResultSetProvenanceV1:
    """C5 provenance with a non-circular, reference-only source boundary."""

    bootstrap_rule_id: str
    canonical_profile_id: str
    canonical_json_algorithm: str
    source_mode_set: tuple[str, ...]
    source_references: tuple[DiagnosticSourceReferenceV1, ...]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        source_references: Sequence[DiagnosticSourceReferenceV1],
    ) -> "DiagnosticResultSetProvenanceV1":
        modes = normalize_source_modes(source_mode_set)
        references = tuple(sorted(source_references, key=lambda item: item.source_index))
        if not references or any(not isinstance(item, DiagnosticSourceReferenceV1) for item in references):
            raise CanonicalError("REF_TARGET_MISSING", "source_references must be non-empty canonical references")
        indices = tuple(item.source_index for item in references)
        encoded = tuple(canonical_json_bytes(item.to_dict()) for item in references)
        if len(set(indices)) != len(indices) or len(set(encoded)) != len(encoded):
            raise CanonicalError("SCHEMA_VIOLATION", "source_references must be unique")
        return cls(
            BOOTSTRAP_RULE_ID,
            CANONICAL_PROFILE_ID,
            CANONICAL_JSON_ALGORITHM,
            modes,
            references,
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
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True, slots=True)
class DiagnosticResultSetV1:
    """Canonical, deterministic collection of explicit diagnostic results."""

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
    diagnostics: tuple[DiagnosticV1, ...]
    provenance: DiagnosticResultSetProvenanceV1

    ARTIFACT_TYPE: ClassVar[str] = _DIAGNOSTIC_ARTIFACT_TYPE
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
        source_references: Sequence[DiagnosticSourceReferenceV1],
        diagnostics: Sequence[DiagnosticV1],
    ) -> "DiagnosticResultSetV1":
        namespace = _nonempty(origin_namespace, "origin_namespace")
        key = _nonempty(origin_key, "origin_key")
        origin_mode = normalize_source_modes((origin_source_mode,))[0]
        provenance = DiagnosticResultSetProvenanceV1.create(
            source_mode_set=source_mode_set,
            source_references=source_references,
        )
        require_no_source_mode_promotion((origin_mode,), provenance.source_mode_set)

        ordered = tuple(sorted(diagnostics, key=_diagnostic_order_key))
        if any(not isinstance(item, DiagnosticV1) for item in ordered):
            raise CanonicalError("SCHEMA_VIOLATION", "diagnostics must contain canonical diagnostic values")
        encoded = tuple(canonical_json_bytes(item.to_dict()) for item in ordered)
        if len(set(encoded)) != len(encoded):
            raise CanonicalError("SCHEMA_VIOLATION", "diagnostics must be unique")
        source_indices = {item.source_index for item in provenance.source_references}
        if any(item.source_index not in source_indices for item in ordered):
            raise CanonicalError(
                "REF_TARGET_MISSING",
                "each diagnostic source_index must resolve inside source_references",
            )

        content = cls._content_projection(ordered)
        provenance_projection = provenance.to_projection()
        stable_projection = cls._stable_projection(namespace, key, origin_mode)
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
                "parent_revision_id": None,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_projection = cls._record_projection(
            origin_namespace=namespace,
            origin_key=key,
            origin_source_mode=origin_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            content_sha256=content_sha256,
            provenance_sha256=provenance_sha256,
            diagnostics=ordered,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection
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
            ordered,
            provenance,
        )

    @property
    def first_error(self) -> DiagnosticV1 | None:
        return first_error_diagnostic(self.diagnostics)

    @property
    def first_error_code(self) -> str:
        item = self.first_error
        return item.code if item is not None else "NONE"

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
    def _content_projection(diagnostics: Sequence[DiagnosticV1]) -> dict[str, Any]:
        first_error = first_error_diagnostic(diagnostics)
        return {
            "diagnostics": [item.to_dict() for item in diagnostics],
            "first_error": first_error.to_dict() if first_error is not None else None,
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "diagnostics": [item.to_dict() for item in values["diagnostics"]],
            "first_error": cls._content_projection(values["diagnostics"])["first_error"],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": None,
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        content = self._content_projection(self.diagnostics)
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
                diagnostics=self.diagnostics,
                provenance=provenance,
            ),
        )
        return all(
            (
                self.artifact_type == self.ARTIFACT_TYPE,
                self.schema_version == self.SCHEMA_VERSION,
                self.parent_revision_id is None,
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
            diagnostics=self.diagnostics,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
