import pytest

from backend.zhifei_autoplan.canonical.common import CanonicalError, DiagnosticV1
from backend.zhifei_autoplan.canonical.material import (
    ParserIdentityV1,
    ProjectMaterialBundleV1,
    ProjectMaterialInputV1,
    ProjectMaterialProvenanceV1,
    SourceLocatorV1,
)


DIGEST = "a" * 64


def _locators():
    return (
        SourceLocatorV1.create(
            kind="document_text_span",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            page_index=0,
            start_scalar_offset=1,
            end_scalar_offset=4,
            quote_sha256="b" * 64,
        ),
        SourceLocatorV1.create(
            kind="document_page_region",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            page_index=0,
            x0="0",
            y0="1.5",
            x1="10",
            y1="20",
            coordinate_space="page-point",
        ),
        SourceLocatorV1.create(
            kind="table_cell_range",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            table_id="T1",
            row_start=0,
            row_end=2,
            column_start=1,
            column_end=3,
        ),
        SourceLocatorV1.create(
            kind="drawing_entity_set",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            layout_name="Model",
            entity_handles=("FF", "0A"),
            bounding_box=("0", "0", "10", "20"),
            drawing_units="mm",
        ),
        SourceLocatorV1.create(
            kind="byte_range",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            byte_start=0,
            byte_end=10,
        ),
    )


def test_every_available_source_locator_variant_is_validated():
    locators = _locators()
    assert [item.kind for item in locators] == [
        "document_text_span",
        "document_page_region",
        "table_cell_range",
        "drawing_entity_set",
        "byte_range",
    ]
    drawing = locators[3].to_dict()
    assert drawing["entity_handles"] == ["0A", "FF"]
    with pytest.raises(CanonicalError):
        SourceLocatorV1.create(
            kind="byte_range",
            source_asset_id="asset-1",
            source_revision_id="asset-rev-1",
            source_content_sha256=DIGEST,
            byte_start=2,
            byte_end=2,
        )


def test_unavailable_locator_is_explicit_and_never_invents_coordinates():
    locator = SourceLocatorV1.create(
        kind="unavailable",
        source_asset_id="asset-1",
        source_revision_id="asset-rev-1",
        reason_code="NO_PHYSICAL_MAPPING",
        attempted_locator_kind="document_text_span",
        adapter_id="adapter-1",
        detail_code="UPSTREAM_OFFSETS_ABSENT",
    )
    assert locator.source_content_sha256 is None
    assert set(locator.to_dict()) == {
        "kind",
        "source_asset_id",
        "source_revision_id",
        "reason_code",
        "attempted_locator_kind",
        "adapter_id",
        "detail_code",
    }


def test_project_material_bundle_is_immutable_deterministic_and_identity_verified():
    provenance = ProjectMaterialProvenanceV1.create(
        source_mode_set=("automatic",),
        source_locators=(_locators()[0],),
        source_asset_content_digests=(DIGEST,),
        parser_identity=ParserIdentityV1("tender-parser", "1"),
        transformation_chain=("decode-utf8",),
        transformation_diagnostics=(),
    )
    source = ProjectMaterialInputV1(
        origin_namespace="project-source",
        origin_key="asset-1",
        origin_source_mode="automatic",
        material_kind="tender-document",
        payload={"title": "Cafe\u0301", "pages": [1, 2]},
        provenance=provenance,
    )
    first = ProjectMaterialBundleV1.build(source)
    second = ProjectMaterialBundleV1.build(source)
    assert first == second
    assert first.verify_identity()
    assert first.accepted_for_response_use is False
    assert first.review_state == "UNREVIEWED"
    assert first.to_dict()["payload"]["title"] == "Café"
    with pytest.raises(TypeError):
        first.payload["new"] = "forbidden"


def test_error_diagnostic_is_included_in_provenance_hash_but_never_accepted():
    diagnostic = DiagnosticV1("SCHEMA_VIOLATION", "30_SCHEMA", "/payload")
    provenance = ProjectMaterialProvenanceV1.create(
        source_mode_set=("fixture",),
        source_locators=(_locators()[0],),
        source_asset_content_digests=(DIGEST,),
        parser_identity=ParserIdentityV1("fixture-parser", "1"),
        transformation_diagnostics=(diagnostic,),
    )
    bundle = ProjectMaterialBundleV1.build(
        ProjectMaterialInputV1("fixture", "case-1", "fixture", "test-material", {"x": 1}, provenance)
    )
    assert bundle.provenance.effective_source_mode == "fixture"
    assert bundle.accepted_for_response_use is False
