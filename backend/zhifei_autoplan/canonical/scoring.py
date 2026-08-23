"""Immutable C2 scoring-rule canonical values for Route C.

The module is deliberately pure: it normalizes explicit values, derives
canonical identities, and keeps source provenance as references.  It does not
read source material, construct an evidence matrix, or perform review/runtime
work.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
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
    validate_canonical_decimal,
    validate_digest,
)


_RULE_KIND_RE: Final = re.compile(r"^[a-z][a-z0-9-]*$")
_MATERIAL_STABLE_PREFIX: Final = "ocrc:project-material:"
_MATERIAL_REVISION_PREFIX: Final = "ocrc-rev:project-material:"


def _nonempty(value: str, field_name: str, *, human_text: bool = False) -> str:
    value = normalize_text(value, human_text=human_text)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = normalize_text(raw_key)
            if key in frozen:
                raise CanonicalError("UNI_NORMALIZED_KEY_COLLISION", "duplicate scoring parameter key after NFC")
            frozen[key] = _freeze(raw_value)
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return tuple(_freeze(item) for item in value)
    raise CanonicalError("SCHEMA_VIOLATION", "scoring parameters contain a forbidden value type")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _validate_material_identity(value: str, prefix: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value.startswith(prefix):
        raise CanonicalError("REF_TARGET_MISSING", f"{field_name} is not a project-material identity")
    validate_digest(value[len(prefix) :])
    return value


@dataclass(frozen=True, slots=True)
class SourceProvenanceReferenceV1:
    """Reference-only boundary from a rule to C1 source provenance."""

    material_stable_id: str
    material_revision_id: str
    material_content_sha256: str
    source_locator_indices: tuple[int, ...]

    @classmethod
    def create(
        cls,
        *,
        material_stable_id: str,
        material_revision_id: str,
        material_content_sha256: str,
        source_locator_indices: Sequence[int],
    ) -> "SourceProvenanceReferenceV1":
        stable_id = _validate_material_identity(
            material_stable_id,
            _MATERIAL_STABLE_PREFIX,
            "material_stable_id",
        )
        revision_id = _validate_material_identity(
            material_revision_id,
            _MATERIAL_REVISION_PREFIX,
            "material_revision_id",
        )
        content_sha256 = validate_digest(material_content_sha256)
        indices = tuple(source_locator_indices)
        if (
            not indices
            or any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in indices)
            or len(set(indices)) != len(indices)
        ):
            raise CanonicalError(
                "SCHEMA_VIOLATION",
                "source_locator_indices must contain unique non-negative integers",
            )
        return cls(stable_id, revision_id, content_sha256, tuple(sorted(indices)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_content_sha256": self.material_content_sha256,
            "material_revision_id": self.material_revision_id,
            "material_stable_id": self.material_stable_id,
            "source_locator_indices": list(self.source_locator_indices),
        }


@dataclass(frozen=True, slots=True)
class ScoringRuleV2:
    rule_id: str
    rule_kind: str
    title: str
    description: str
    maximum_score: str
    parameters: Mapping[str, Any]
    source_references: tuple[SourceProvenanceReferenceV1, ...]

    @classmethod
    def create(
        cls,
        *,
        rule_id: str,
        rule_kind: str,
        title: str,
        description: str,
        maximum_score: str,
        parameters: Mapping[str, Any],
        source_references: Sequence[SourceProvenanceReferenceV1],
    ) -> "ScoringRuleV2":
        rule_id = _nonempty(rule_id, "rule_id")
        rule_kind = normalize_text(rule_kind)
        if not _RULE_KIND_RE.fullmatch(rule_kind):
            raise CanonicalError("SCHEMA_VIOLATION", "rule_kind must be a lowercase token")
        title = _nonempty(title, "title", human_text=True)
        description = _nonempty(description, "description", human_text=True)
        maximum_score = validate_canonical_decimal(maximum_score)
        if Decimal(maximum_score) < 0:
            raise CanonicalError("SCHEMA_VIOLATION", "maximum_score must be non-negative")
        frozen_parameters = _freeze(parameters)
        references = tuple(
            sorted(
                source_references,
                key=lambda item: canonical_json_bytes(item.to_dict()),
            )
        )
        reference_bytes = [canonical_json_bytes(item.to_dict()) for item in references]
        if not references or len(set(reference_bytes)) != len(reference_bytes):
            raise CanonicalError("SCHEMA_VIOLATION", "source_references must be non-empty and unique")
        return cls(
            rule_id,
            rule_kind,
            title,
            description,
            maximum_score,
            frozen_parameters,
            references,
        )

    def to_content_projection(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "maximum_score": self.maximum_score,
            "parameters": _thaw(self.parameters),
            "rule_id": self.rule_id,
            "rule_kind": self.rule_kind,
            "title": self.title,
        }

    def to_dict(self) -> dict[str, Any]:
        value = self.to_content_projection()
        value["source_references"] = [item.to_dict() for item in self.source_references]
        return value


@dataclass(frozen=True, slots=True)
class ScoringExtractorIdentityV1:
    extractor_id: str
    extractor_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "extractor_id", _nonempty(self.extractor_id, "extractor_id"))
        object.__setattr__(self, "extractor_version", _nonempty(self.extractor_version, "extractor_version"))

    def to_dict(self) -> dict[str, str]:
        return {
            "extractor_id": self.extractor_id,
            "extractor_version": self.extractor_version,
        }


@dataclass(frozen=True, slots=True)
class ScoringRuleSetProvenanceV2:
    source_mode_set: tuple[str, ...]
    extractor_identity: ScoringExtractorIdentityV1
    rule_source_references: tuple[tuple[str, tuple[SourceProvenanceReferenceV1, ...]], ...]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        extractor_identity: ScoringExtractorIdentityV1,
        rules: Sequence[ScoringRuleV2],
    ) -> "ScoringRuleSetProvenanceV2":
        modes = normalize_source_modes(source_mode_set)
        rule_references = tuple((rule.rule_id, rule.source_references) for rule in rules)
        return cls(modes, extractor_identity, rule_references)

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "effective_source_mode": self.effective_source_mode,
            "extractor_identity": self.extractor_identity.to_dict(),
            "rule_source_references": [
                {
                    "rule_id": rule_id,
                    "source_references": [item.to_dict() for item in references],
                }
                for rule_id, references in self.rule_source_references
            ],
            "source_mode_set": list(self.source_mode_set),
        }


@dataclass(frozen=True, slots=True)
class ScoringRuleSetInputV2:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    source_mode_set: tuple[str, ...]
    extractor_identity: ScoringExtractorIdentityV1
    rules: tuple[ScoringRuleV2, ...]
    parent_revision_id: str | None = None

    def __post_init__(self) -> None:
        namespace = _nonempty(self.origin_namespace, "origin_namespace")
        key = _nonempty(self.origin_key, "origin_key")
        origin_mode = normalize_source_modes((self.origin_source_mode,))[0]
        modes = normalize_source_modes(self.source_mode_set)
        require_no_source_mode_promotion((origin_mode,), modes)
        rules = tuple(sorted(self.rules, key=lambda item: item.rule_id.encode("utf-8")))
        if not rules or len({item.rule_id for item in rules}) != len(rules):
            raise CanonicalError("SCHEMA_VIOLATION", "rules must be non-empty with unique rule_id values")
        parent = normalize_text(self.parent_revision_id) if self.parent_revision_id is not None else None
        if parent == "":
            raise CanonicalError("ID_PARENT_INVALID", "parent_revision_id must be null or non-empty")
        object.__setattr__(self, "origin_namespace", namespace)
        object.__setattr__(self, "origin_key", key)
        object.__setattr__(self, "origin_source_mode", origin_mode)
        object.__setattr__(self, "source_mode_set", modes)
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "parent_revision_id", parent)


@dataclass(frozen=True, slots=True)
class ScoringRuleSetV2:
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
    rules: tuple[ScoringRuleV2, ...]
    provenance: ScoringRuleSetProvenanceV2
    review_state: str
    accepted_for_response_use: bool

    ARTIFACT_TYPE: ClassVar[str] = "scoring-rule-set"
    SCHEMA_VERSION: ClassVar[str] = "2"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(cls, source: ScoringRuleSetInputV2) -> "ScoringRuleSetV2":
        content = {"rules": [item.to_content_projection() for item in source.rules]}
        provenance = ScoringRuleSetProvenanceV2.create(
            source_mode_set=source.source_mode_set,
            extractor_identity=source.extractor_identity,
            rules=source.rules,
        )
        provenance_projection = provenance.to_projection()
        stable_projection = {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": source.origin_key,
            "origin_namespace": source.origin_namespace,
            "origin_source_mode": source.origin_source_mode,
            "schema_version": cls.SCHEMA_VERSION,
        }
        content_sha256 = profile_digest(
            "content-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            content,
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
            rules=source.rules,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            record_projection,
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
            source.rules,
            provenance,
            "UNREVIEWED",
            False,
        )

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
            "review_state": "UNREVIEWED",
            "revision_id": values["revision_id"],
            "rules": [item.to_dict() for item in values["rules"]],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        rebuilt = type(self).build(
            ScoringRuleSetInputV2(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                source_mode_set=self.provenance.source_mode_set,
                extractor_identity=self.provenance.extractor_identity,
                rules=self.rules,
                parent_revision_id=self.parent_revision_id,
            )
        )
        return all(
            (
                identities_equal(self.content_sha256, rebuilt.content_sha256),
                identities_equal(self.provenance_sha256, rebuilt.provenance_sha256),
                identities_equal(self.stable_id, rebuilt.stable_id),
                identities_equal(self.revision_id, rebuilt.revision_id),
                identities_equal(self.record_sha256, rebuilt.record_sha256),
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
            rules=self.rules,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
