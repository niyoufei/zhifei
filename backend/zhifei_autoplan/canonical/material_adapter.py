"""Pure, explicit-input adapters for C1 project material."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .common import CanonicalError, DiagnosticV1, first_error_diagnostic, normalize_text
from .material import (
    ParserIdentityV1,
    ProjectMaterialBundleV1,
    ProjectMaterialInputV1,
    ProjectMaterialProvenanceV1,
    SourceLocatorV1,
)


@dataclass(frozen=True, slots=True)
class ParserRegistrationV1:
    parser_id: str
    parser_version: str
    material_kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        parser_id = normalize_text(self.parser_id)
        parser_version = normalize_text(self.parser_version)
        kinds = tuple(sorted({normalize_text(item) for item in self.material_kinds}, key=lambda item: item.encode("utf-8")))
        if not parser_id or not parser_version or not kinds or any(not item for item in kinds):
            raise CanonicalError("SCHEMA_VIOLATION", "parser registration fields must be non-empty")
        object.__setattr__(self, "parser_id", parser_id)
        object.__setattr__(self, "parser_version", parser_version)
        object.__setattr__(self, "material_kinds", kinds)


@dataclass(frozen=True, slots=True)
class DeterministicParserRegistryV1:
    registrations: tuple[ParserRegistrationV1, ...]

    @classmethod
    def create(cls, registrations: Sequence[ParserRegistrationV1]) -> "DeterministicParserRegistryV1":
        ordered = tuple(
            sorted(
                registrations,
                key=lambda item: (item.parser_id.encode("utf-8"), item.parser_version.encode("utf-8")),
            )
        )
        keys = [(item.parser_id, item.parser_version) for item in ordered]
        if len(set(keys)) != len(keys):
            raise CanonicalError("SCHEMA_VIOLATION", "duplicate parser registry identity")
        return cls(ordered)

    def find(self, parser_id: str, parser_version: str) -> ParserRegistrationV1 | None:
        key = (normalize_text(parser_id), normalize_text(parser_version))
        return next(
            (item for item in self.registrations if (item.parser_id, item.parser_version) == key),
            None,
        )


@dataclass(frozen=True, slots=True)
class MaterialAdapterInputV1:
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    material_kind: str
    payload: dict[str, Any]
    source_locators: tuple[SourceLocatorV1, ...]
    source_asset_content_digests: tuple[str, ...]
    parser_id: str
    parser_version: str
    transformation_chain: tuple[str, ...] = ()
    transformation_diagnostics: tuple[DiagnosticV1, ...] = ()
    parent_revision_id: str | None = None


@dataclass(frozen=True, slots=True)
class MaterialAdapterResultV1:
    bundle: ProjectMaterialBundleV1 | None
    diagnostics: tuple[DiagnosticV1, ...]

    @property
    def first_error(self) -> str:
        item = first_error_diagnostic(self.diagnostics)
        return item.code if item is not None else "NONE"


def _schema_diagnostic(detail_code: str, pointer: str, message: str) -> DiagnosticV1:
    return DiagnosticV1(
        code="SCHEMA_VIOLATION",
        phase="30_SCHEMA",
        json_pointer=pointer,
        detail_code=detail_code,
        message=message,
    )


def adapt_project_material(
    source: MaterialAdapterInputV1,
    registry: DeterministicParserRegistryV1,
) -> MaterialAdapterResultV1:
    """Transform explicit values only; no source read, runtime call, or write occurs."""

    registration = registry.find(source.parser_id, source.parser_version)
    if registration is None:
        diagnostic = _schema_diagnostic("PARSER_NOT_REGISTERED", "/parser_id", "parser identity is not registered")
        return MaterialAdapterResultV1(None, (diagnostic,))
    material_kind = normalize_text(source.material_kind)
    if material_kind not in registration.material_kinds:
        diagnostic = _schema_diagnostic("MATERIAL_UNSUPPORTED", "/material_kind", "material kind is unsupported by the parser")
        return MaterialAdapterResultV1(None, (diagnostic,))
    unavailable = [item for item in source.source_locators if item.kind == "unavailable"]
    if unavailable:
        diagnostic = DiagnosticV1(
            code="SRC_LOCATOR_UNAVAILABLE",
            phase="50_LOCATOR",
            json_pointer="/source_locators",
            detail_code=dict(unavailable[0].attributes)["detail_code"],
            message="source locator is unavailable; no canonical material was constructed",
        )
        return MaterialAdapterResultV1(None, (diagnostic,))
    if any(item.severity in {"ERROR", "FATAL"} for item in source.transformation_diagnostics):
        return MaterialAdapterResultV1(None, tuple(source.transformation_diagnostics))

    try:
        provenance = ProjectMaterialProvenanceV1.create(
            source_mode_set=(source.origin_source_mode,),
            source_locators=source.source_locators,
            source_asset_content_digests=source.source_asset_content_digests,
            parser_identity=ParserIdentityV1(source.parser_id, source.parser_version),
            transformation_chain=source.transformation_chain,
            transformation_diagnostics=source.transformation_diagnostics,
        )
        material_input = ProjectMaterialInputV1(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            material_kind=material_kind,
            payload=source.payload,
            provenance=provenance,
            parent_revision_id=source.parent_revision_id,
        )
        bundle = ProjectMaterialBundleV1.build(material_input)
    except CanonicalError as exc:
        code = exc.code if exc.code in {"SRC_MODE_INVALID", "SRC_MODE_PROMOTION_FORBIDDEN"} else "SCHEMA_VIOLATION"
        phase = "40_SOURCE_MODE" if code.startswith("SRC_MODE_") else "30_SCHEMA"
        diagnostic = DiagnosticV1(
            code=code,
            phase=phase,
            json_pointer=exc.json_pointer,
            detail_code=exc.code,
            message=str(exc),
        )
        return MaterialAdapterResultV1(None, (diagnostic,))
    return MaterialAdapterResultV1(bundle, tuple(source.transformation_diagnostics))
