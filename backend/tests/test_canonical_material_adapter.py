from backend.zhifei_autoplan.canonical.material import SourceLocatorV1
from backend.zhifei_autoplan.canonical.material_adapter import (
    DeterministicParserRegistryV1,
    MaterialAdapterInputV1,
    ParserRegistrationV1,
    adapt_project_material,
)


DIGEST = "c" * 64


def _registry():
    return DeterministicParserRegistryV1.create(
        (
            ParserRegistrationV1("parser-z", "1", ("drawing",)),
            ParserRegistrationV1("parser-a", "2", ("tender-document", "boq")),
        )
    )


def _available_locator():
    return SourceLocatorV1.create(
        kind="byte_range",
        source_asset_id="asset-9",
        source_revision_id="asset-rev-9",
        source_content_sha256=DIGEST,
        byte_start=0,
        byte_end=4,
    )


def _input(**changes):
    values = {
        "origin_namespace": "project-source",
        "origin_key": "asset-9",
        "origin_source_mode": "automatic",
        "material_kind": "tender-document",
        "payload": {"text": "正文", "meta": {"pages": 1}},
        "source_locators": (_available_locator(),),
        "source_asset_content_digests": (DIGEST,),
        "parser_id": "parser-a",
        "parser_version": "2",
        "transformation_chain": ("explicit-parser-output",),
    }
    values.update(changes)
    return MaterialAdapterInputV1(**values)


def test_registry_order_and_lossless_pure_adapter_are_deterministic():
    registry = _registry()
    assert [(item.parser_id, item.parser_version) for item in registry.registrations] == [
        ("parser-a", "2"),
        ("parser-z", "1"),
    ]
    first = adapt_project_material(_input(), registry)
    second = adapt_project_material(_input(), registry)
    assert first.first_error == "NONE"
    assert first.bundle == second.bundle
    assert first.bundle is not None
    assert first.bundle.to_dict()["payload"] == {"text": "正文", "meta": {"pages": 1}}
    assert first.bundle.verify_identity()


def test_unsupported_material_is_fail_closed_with_explicit_detail():
    result = adapt_project_material(_input(material_kind="native-dwg"), _registry())
    assert result.bundle is None
    assert result.first_error == "SCHEMA_VIOLATION"
    assert result.diagnostics[0].detail_code == "MATERIAL_UNSUPPORTED"


def test_unknown_parser_is_fail_closed():
    result = adapt_project_material(_input(parser_id="missing"), _registry())
    assert result.bundle is None
    assert result.first_error == "SCHEMA_VIOLATION"
    assert result.diagnostics[0].detail_code == "PARSER_NOT_REGISTERED"


def test_unavailable_locator_returns_registered_error_and_no_bundle():
    unavailable = SourceLocatorV1.create(
        kind="unavailable",
        source_asset_id="asset-9",
        source_revision_id="asset-rev-9",
        reason_code="NO_MAPPING",
        attempted_locator_kind="document_text_span",
        adapter_id="parser-a",
        detail_code="OFFSETS_ABSENT",
    )
    result = adapt_project_material(_input(source_locators=(unavailable,)), _registry())
    assert result.bundle is None
    assert result.first_error == "SRC_LOCATOR_UNAVAILABLE"
    assert result.diagnostics[0].severity == "ERROR"
