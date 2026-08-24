"""Immutable C1 project-material canonical value objects."""

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
    DiagnosticV1,
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


_HANDLE_RE: Final = re.compile(r"^[0-9A-F]+$")


def _freeze(value: Any, *, human_text: bool = False) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return normalize_text(value, human_text=human_text)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = normalize_text(raw_key)
            if key in frozen:
                raise CanonicalError("UNI_NORMALIZED_KEY_COLLISION", "duplicate payload key after NFC")
            frozen[key] = _freeze(raw_value)
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return tuple(_freeze(item) for item in value)
    raise CanonicalError("SCHEMA_VIOLATION", "payload contains a forbidden value type")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _nonempty(value: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _range(start: Any, end: Any, name: str) -> tuple[int, int]:
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or start >= end
    ):
        raise CanonicalError("SCHEMA_VIOLATION", f"{name} must be a non-empty zero-based half-open range")
    return start, end


@dataclass(frozen=True, slots=True)
class SourceLocatorV1:
    kind: str
    source_asset_id: str
    source_revision_id: str
    source_content_sha256: str | None
    attributes: tuple[tuple[str, Any], ...]

    VARIANT_FIELDS: ClassVar[dict[str, frozenset[str]]] = {
        "document_text_span": frozenset({"page_index", "start_scalar_offset", "end_scalar_offset", "quote_sha256"}),
        "document_page_region": frozenset({"page_index", "x0", "y0", "x1", "y1", "coordinate_space"}),
        "table_cell_range": frozenset({"table_id", "row_start", "row_end", "column_start", "column_end"}),
        "drawing_entity_set": frozenset({"layout_name", "entity_handles", "bounding_box", "drawing_units"}),
        "byte_range": frozenset({"byte_start", "byte_end"}),
        "unavailable": frozenset({"reason_code", "attempted_locator_kind", "adapter_id", "detail_code"}),
    }

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        source_asset_id: str,
        source_revision_id: str,
        source_content_sha256: str | None = None,
        **attributes: Any,
    ) -> "SourceLocatorV1":
        kind = normalize_text(kind)
        if kind not in cls.VARIANT_FIELDS:
            raise CanonicalError("SRC_LOCATOR_KIND_UNKNOWN", "unknown source locator kind")
        expected = cls.VARIANT_FIELDS[kind]
        if frozenset(attributes) != expected:
            raise CanonicalError("SCHEMA_VIOLATION", "locator fields do not exactly match the selected variant")
        source_asset_id = _nonempty(source_asset_id, "source_asset_id")
        source_revision_id = _nonempty(source_revision_id, "source_revision_id")
        if kind != "unavailable" and source_content_sha256 is None:
            raise CanonicalError("SCHEMA_VIOLATION", "available locator requires source_content_sha256")
        digest = validate_digest(source_content_sha256) if source_content_sha256 is not None else None

        checked = dict(attributes)
        if kind in {"document_text_span", "document_page_region"}:
            page = checked["page_index"]
            if not isinstance(page, int) or isinstance(page, bool) or page < 0:
                raise CanonicalError("SCHEMA_VIOLATION", "page_index must be a non-negative integer")
        if kind == "document_text_span":
            _range(checked["start_scalar_offset"], checked["end_scalar_offset"], "scalar offsets")
            checked["quote_sha256"] = validate_digest(checked["quote_sha256"])
        elif kind == "document_page_region":
            for name in ("x0", "y0", "x1", "y1"):
                checked[name] = validate_canonical_decimal(checked[name])
            if Decimal(checked["x0"]) >= Decimal(checked["x1"]) or Decimal(checked["y0"]) >= Decimal(checked["y1"]):
                raise CanonicalError("SCHEMA_VIOLATION", "page region must have positive width and height")
            checked["coordinate_space"] = _nonempty(checked["coordinate_space"], "coordinate_space")
        elif kind == "table_cell_range":
            checked["table_id"] = _nonempty(checked["table_id"], "table_id")
            _range(checked["row_start"], checked["row_end"], "row range")
            _range(checked["column_start"], checked["column_end"], "column range")
        elif kind == "drawing_entity_set":
            checked["layout_name"] = _nonempty(checked["layout_name"], "layout_name")
            handles = tuple(normalize_text(item) for item in checked["entity_handles"])
            if not handles or any(not _HANDLE_RE.fullmatch(item) for item in handles):
                raise CanonicalError("SCHEMA_VIOLATION", "entity handles must be non-empty uppercase ASCII hexadecimal strings")
            handles = tuple(sorted(handles, key=lambda item: item.encode("utf-8")))
            if len(set(handles)) != len(handles):
                raise CanonicalError("SCHEMA_VIOLATION", "entity handles must be unique")
            box = tuple(validate_canonical_decimal(item) for item in checked["bounding_box"])
            if len(box) != 4 or Decimal(box[0]) >= Decimal(box[2]) or Decimal(box[1]) >= Decimal(box[3]):
                raise CanonicalError("SCHEMA_VIOLATION", "invalid drawing bounding box")
            checked["entity_handles"] = handles
            checked["bounding_box"] = box
            checked["drawing_units"] = _nonempty(checked["drawing_units"], "drawing_units")
        elif kind == "byte_range":
            _range(checked["byte_start"], checked["byte_end"], "byte range")
        else:
            for name in ("reason_code", "attempted_locator_kind", "adapter_id", "detail_code"):
                checked[name] = _nonempty(checked[name], name)

        frozen_attributes = tuple(
            sorted(((normalize_text(key), _freeze(value)) for key, value in checked.items()), key=lambda item: item[0].encode("utf-8"))
        )
        return cls(kind, source_asset_id, source_revision_id, digest, frozen_attributes)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "kind": self.kind,
            "source_asset_id": self.source_asset_id,
            "source_revision_id": self.source_revision_id,
        }
        if self.source_content_sha256 is not None:
            value["source_content_sha256"] = self.source_content_sha256
        value.update({key: _thaw(item) for key, item in self.attributes})
        return value


@dataclass(frozen=True, slots=True)
class ParserIdentityV1:
    parser_id: str
    parser_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "parser_id", _nonempty(self.parser_id, "parser_id"))
        object.__setattr__(self, "parser_version", _nonempty(self.parser_version, "parser_version"))

    def to_dict(self) -> dict[str, str]:
        return {"parser_id": self.parser_id, "parser_version": self.parser_version}


@dataclass(frozen=True, slots=True)
class ProjectMaterialProvenanceV1:
    source_mode_set: tuple[str, ...]
    source_locators: tuple[SourceLocatorV1, ...]
    source_asset_content_digests: tuple[str, ...]
    parser_identity: ParserIdentityV1
    transformation_chain: tuple[str, ...]
    transformation_diagnostics: tuple[DiagnosticV1, ...]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        source_locators: Sequence[SourceLocatorV1],
        source_asset_content_digests: Sequence[str],
        parser_identity: ParserIdentityV1,
        transformation_chain: Sequence[str] = (),
        transformation_diagnostics: Sequence[DiagnosticV1] = (),
    ) -> "ProjectMaterialProvenanceV1":
        modes = normalize_source_modes(source_mode_set)
        locators = tuple(source_locators)
        if not locators:
            raise CanonicalError("SCHEMA_VIOLATION", "material provenance requires at least one source locator")
        digests = tuple(sorted({validate_digest(item) for item in source_asset_content_digests}))
        if not digests:
            raise CanonicalError("SCHEMA_VIOLATION", "material provenance requires a source content digest")
        chain = tuple(_nonempty(item, "transformation_chain item") for item in transformation_chain)
        diagnostics = tuple(transformation_diagnostics)
        return cls(modes, locators, digests, parser_identity, chain, diagnostics)

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "effective_source_mode": self.effective_source_mode,
            "parser_identity": self.parser_identity.to_dict(),
            "source_asset_content_digests": list(self.source_asset_content_digests),
            "source_locators": [item.to_dict() for item in self.source_locators],
            "source_mode_set": list(self.source_mode_set),
            "transformation_chain": list(self.transformation_chain),
            "transformation_diagnostics": [item.to_dict() for item in self.transformation_diagnostics],
        }


@dataclass(frozen=True, slots=True)
class ProjectMaterialInputV1:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    material_kind: str
    payload: Mapping[str, Any]
    provenance: ProjectMaterialProvenanceV1
    parent_revision_id: str | None = None

    def __post_init__(self) -> None:
        namespace = _nonempty(self.origin_namespace, "origin_namespace")
        key = _nonempty(self.origin_key, "origin_key")
        mode = normalize_source_modes((self.origin_source_mode,))[0]
        kind = _nonempty(self.material_kind, "material_kind")
        payload = _freeze(self.payload)
        require_no_source_mode_promotion((mode,), self.provenance.source_mode_set)
        parent = normalize_text(self.parent_revision_id) if self.parent_revision_id is not None else None
        if parent == "":
            raise CanonicalError("ID_PARENT_INVALID", "parent_revision_id must be null or non-empty")
        object.__setattr__(self, "origin_namespace", namespace)
        object.__setattr__(self, "origin_key", key)
        object.__setattr__(self, "origin_source_mode", mode)
        object.__setattr__(self, "material_kind", kind)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "parent_revision_id", parent)


@dataclass(frozen=True, slots=True)
class ProjectMaterialBundleV1:
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
    material_kind: str
    payload: Mapping[str, Any]
    provenance: ProjectMaterialProvenanceV1
    review_state: str
    accepted_for_response_use: bool

    ARTIFACT_TYPE: ClassVar[str] = "project-material"
    SCHEMA_VERSION: ClassVar[str] = "1"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(cls, source: ProjectMaterialInputV1) -> "ProjectMaterialBundleV1":
        content = {"material_kind": source.material_kind, "payload": _thaw(source.payload)}
        provenance = source.provenance.to_projection()
        stable_projection = {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": source.origin_key,
            "origin_namespace": source.origin_namespace,
            "origin_source_mode": source.origin_source_mode,
            "schema_version": cls.SCHEMA_VERSION,
        }
        content_sha = profile_digest("content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content)
        provenance_sha = profile_digest("provenance-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, provenance)
        stable_id = derive_stable_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, stable_projection)
        revision_projection = {
            "content_sha256": content_sha,
            "parent_revision_id": source.parent_revision_id,
            "provenance_sha256": provenance_sha,
            "stable_id": stable_id,
        }
        revision_id = derive_revision_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, revision_projection)
        record_projection = cls._record_projection(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            parent_revision_id=source.parent_revision_id,
            content_sha256=content_sha,
            provenance_sha256=provenance_sha,
            material_kind=source.material_kind,
            payload=_thaw(source.payload),
            provenance=provenance,
        )
        record_sha = profile_digest("record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection)
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            source.origin_namespace,
            source.origin_key,
            source.origin_source_mode,
            stable_id,
            revision_id,
            source.parent_revision_id,
            content_sha,
            provenance_sha,
            record_sha,
            source.material_kind,
            source.payload,
            source.provenance,
            "UNREVIEWED",
            False,
        )

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "accepted_for_response_use": False,
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "material_kind": values["material_kind"],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": values["parent_revision_id"],
            "payload": values["payload"],
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "review_state": "UNREVIEWED",
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        rebuilt = type(self).build(
            ProjectMaterialInputV1(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                material_kind=self.material_kind,
                payload=self.payload,
                provenance=self.provenance,
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
            material_kind=self.material_kind,
            payload=_thaw(self.payload),
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
