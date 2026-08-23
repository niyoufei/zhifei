from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from backend.zhifei_autoplan.canonical.common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    DiagnosticV1,
    canonical_json_bytes,
    derive_revision_id,
    profile_digest,
)
from backend.zhifei_autoplan.canonical.diagnostic import (
    DiagnosticResultSetV1,
    DiagnosticSourceReferenceV1,
)
from backend.zhifei_autoplan.canonical.material import (
    ParserIdentityV1,
    ProjectMaterialBundleV1,
    ProjectMaterialInputV1,
    ProjectMaterialProvenanceV1,
    SourceLocatorV1,
)
from backend.zhifei_autoplan.canonical.review import (
    ReviewInputV1,
    ReviewTargetReferenceV1,
)
from backend.zhifei_autoplan.canonical.review_v2 import ReviewInputV2
from backend.zhifei_autoplan.canonical.review_v2_adapter import adapt_review_input_v1


def _material() -> ProjectMaterialBundleV1:
    locator = SourceLocatorV1.create(
        kind="byte_range",
        source_asset_id="asset-review-v2-1",
        source_revision_id="asset-review-v2-rev-1",
        source_content_sha256="a" * 64,
        byte_start=0,
        byte_end=16,
    )
    provenance = ProjectMaterialProvenanceV1.create(
        source_mode_set=("automatic",),
        source_locators=(locator,),
        source_asset_content_digests=("a" * 64,),
        parser_identity=ParserIdentityV1("review-v2-fixture-parser", "1"),
        transformation_chain=("decode-utf8",),
        transformation_diagnostics=(),
    )
    return ProjectMaterialBundleV1.build(
        ProjectMaterialInputV1(
            origin_namespace="technical-bid",
            origin_key="asset-review-v2-1",
            origin_source_mode="automatic",
            material_kind="tender-document",
            payload={"title": "Review V2 target"},
            provenance=provenance,
        )
    )


def _review_input_v1() -> ReviewInputV1:
    target = _material()
    reference = DiagnosticSourceReferenceV1.create(
        source_index=4,
        artifact_type=target.artifact_type,
        stable_id=target.stable_id,
        revision_id=target.revision_id,
        record_sha256=target.record_sha256,
    )
    diagnostics = DiagnosticResultSetV1.build(
        origin_namespace="technical-bid",
        origin_key="asset-review-v2-1-diagnostics",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        source_references=(reference,),
        diagnostics=(),
    )
    return ReviewInputV1.build(
        origin_namespace="technical-bid-review",
        origin_key="asset-review-v2-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        target=target,
        diagnostic_result_set=diagnostics,
    )


def _valid_circular_v1(source: ReviewInputV1) -> ReviewInputV1:
    target = ReviewTargetReferenceV1(
        source_index=source.target.source_index,
        artifact_type="review-input",
        schema_version="1",
        stable_id="ocrc:review-input:" + source.target.stable_id.rsplit(":", 1)[1],
        revision_id="ocrc-rev:review-input:" + source.target.revision_id.rsplit(":", 1)[1],
        record_sha256=source.target.record_sha256,
        review_state=source.target.review_state,
        accepted_for_response_use=False,
    )
    content = ReviewInputV1._content_projection(target, source.diagnostic_result_set)
    content_sha256 = profile_digest("content-sha256", "review-input", "1", content)
    revision_id = derive_revision_id(
        "review-input",
        "1",
        {
            "content_sha256": content_sha256,
            "parent_revision_id": None,
            "provenance_sha256": source.provenance_sha256,
            "stable_id": source.stable_id,
        },
    )
    record_sha256 = profile_digest(
        "record-sha256",
        "review-input",
        "1",
        ReviewInputV1._record_projection(
            origin_namespace=source.origin_namespace,
            origin_key=source.origin_key,
            origin_source_mode=source.origin_source_mode,
            stable_id=source.stable_id,
            revision_id=revision_id,
            content_sha256=content_sha256,
            provenance_sha256=source.provenance_sha256,
            target=target,
            diagnostic_result_set=source.diagnostic_result_set,
            provenance=source.provenance.to_projection(),
        ),
    )
    value = replace(
        source,
        target=target,
        content_sha256=content_sha256,
        revision_id=revision_id,
        record_sha256=record_sha256,
    )
    assert value.verify_identity()
    return value


def test_review_input_v2_is_deterministic_immutable_and_complete():
    source = _review_input_v1()
    first = adapt_review_input_v1(source)
    second = adapt_review_input_v1(source)

    assert first.diagnostics == second.diagnostics == ()
    assert first.first_error == second.first_error == "NONE"
    assert first.review_input == second.review_input
    value = first.review_input
    assert isinstance(value, ReviewInputV2)
    assert value.verify_identity()
    assert value.artifact_type == "review-input"
    assert value.schema_version == "2"
    assert value.parent_revision_id is None
    assert tuple(value.to_dict()) == (
        "artifact_type",
        "content_sha256",
        "diagnostic_result_set",
        "origin_key",
        "origin_namespace",
        "origin_source_mode",
        "parent_revision_id",
        "provenance",
        "provenance_sha256",
        "revision_id",
        "schema_version",
        "source_review_input",
        "stable_id",
        "target",
        "record_sha256",
    )
    assert canonical_json_bytes(value.to_dict()) == canonical_json_bytes(
        second.review_input.to_dict()
    )
    with pytest.raises(FrozenInstanceError):
        value.revision_id = "changed"


def test_v2_rederives_identity_and_binds_the_verified_v1_reference():
    source = _review_input_v1()
    value = adapt_review_input_v1(source).review_input

    assert value is not None
    assert value.source_review_input.to_dict() == {
        "artifact_type": "review-input",
        "schema_version": "1",
        "stable_id": source.stable_id,
        "revision_id": source.revision_id,
        "record_sha256": source.record_sha256,
    }
    assert value.stable_id != source.stable_id
    assert value.revision_id != source.revision_id
    assert value.record_sha256 != source.record_sha256
    assert value.origin_namespace == source.origin_namespace
    assert value.origin_key == source.origin_key
    assert value.origin_source_mode == source.origin_source_mode
    assert value.target == source.target
    assert value.diagnostic_result_set == source.diagnostic_result_set


def test_content_provenance_and_record_identity_projections_fail_closed():
    value = adapt_review_input_v1(_review_input_v1()).review_input
    assert value is not None

    assert not replace(value, content_sha256="b" * 64).verify_identity()
    assert not replace(value, provenance_sha256="c" * 64).verify_identity()
    assert not replace(value, stable_id="ocrc:review-input:" + "d" * 64).verify_identity()
    assert not replace(value, revision_id="ocrc-rev:review-input:" + "e" * 64).verify_identity()
    assert not replace(value, record_sha256="f" * 64).verify_identity()


def test_provenance_profile_and_frozen_array_order_are_preserved():
    source = _review_input_v1()
    value = adapt_review_input_v1(source).review_input

    assert value is not None
    assert value.provenance.source_mode_set == source.provenance.source_mode_set
    assert value.provenance.to_projection()["source_mode_set"] == list(
        source.provenance.source_mode_set
    )
    assert value.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID
    assert value.provenance.canonical_profile_id == CANONICAL_PROFILE_ID
    assert value.provenance.canonical_json_algorithm == CANONICAL_JSON_ALGORITHM


def test_adapter_rejects_schema_unknown_fields_and_invalid_identity():
    source = _review_input_v1()
    wrong_schema = adapt_review_input_v1(replace(source, schema_version="0"))
    unknown = adapt_review_input_v1(
        SimpleNamespace(**source.to_dict(), future_override="forbidden")
    )
    invalid_identity = adapt_review_input_v1(replace(source, record_sha256="b" * 64))

    assert wrong_schema.review_input is None
    assert wrong_schema.first_error == "SCHEMA_VIOLATION"
    assert wrong_schema.diagnostics[0].phase == "30_SCHEMA"
    assert unknown.review_input is None
    assert unknown.first_error == "SCHEMA_VIOLATION"
    assert len(unknown.diagnostics) == 1
    assert invalid_identity.review_input is None
    assert invalid_identity.first_error == "REVIEW_IDENTITY_INVALID"
    assert invalid_identity.diagnostics[0].phase == "80_REVIEW"


def test_adapter_rejects_bootstrap_cycle_with_one_deterministic_diagnostic():
    circular = _valid_circular_v1(_review_input_v1())
    first = adapt_review_input_v1(circular)
    second = adapt_review_input_v1(circular)

    assert first == second
    assert first.review_input is None
    assert first.first_error == "BOOTSTRAP_CYCLE_FORBIDDEN"
    assert len(first.diagnostics) == 1
    assert first.diagnostics[0].phase == "100_BOOTSTRAP"
    assert first.diagnostics[0].code == "BOOTSTRAP_CYCLE_FORBIDDEN"


def test_v2_boundary_contains_no_later_review_stage_fields():
    record = adapt_review_input_v1(_review_input_v1()).review_input.to_dict()

    assert "recommendation" not in record
    assert "review_event" not in record
    assert "workflow" not in record
    assert "approval" not in record
    assert "feedback_loop" not in record
