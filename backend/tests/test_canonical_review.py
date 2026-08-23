from dataclasses import FrozenInstanceError, replace

import pytest

from backend.zhifei_autoplan.canonical.common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    DiagnosticV1,
    canonical_json_bytes,
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
from backend.zhifei_autoplan.canonical.review import ReviewInputV1
from backend.zhifei_autoplan.canonical.review_adapter import (
    ReviewInputAdapterInputV1,
    assemble_review_input,
)


def _material(source_modes: tuple[str, ...] = ("automatic",)) -> ProjectMaterialBundleV1:
    locator = SourceLocatorV1.create(
        kind="byte_range",
        source_asset_id="asset-review-1",
        source_revision_id="asset-review-rev-1",
        source_content_sha256="a" * 64,
        byte_start=0,
        byte_end=16,
    )
    provenance = ProjectMaterialProvenanceV1.create(
        source_mode_set=source_modes,
        source_locators=(locator,),
        source_asset_content_digests=("a" * 64,),
        parser_identity=ParserIdentityV1("review-fixture-parser", "1"),
        transformation_chain=("decode-utf8",),
        transformation_diagnostics=(),
    )
    return ProjectMaterialBundleV1.build(
        ProjectMaterialInputV1(
            origin_namespace="technical-bid",
            origin_key="asset-review-1",
            origin_source_mode=source_modes[0],
            material_kind="tender-document",
            payload={"title": "Review target"},
            provenance=provenance,
        )
    )


def _diagnostic_result(
    target: ProjectMaterialBundleV1,
    *,
    match_target: bool = True,
    diagnostics: tuple[DiagnosticV1, ...] = (),
) -> DiagnosticResultSetV1:
    marker = target.record_sha256 if match_target else "b" * 64
    reference = DiagnosticSourceReferenceV1.create(
        source_index=3,
        artifact_type=target.artifact_type,
        stable_id=target.stable_id,
        revision_id=target.revision_id,
        record_sha256=marker,
    )
    return DiagnosticResultSetV1.build(
        origin_namespace="technical-bid",
        origin_key="asset-review-1-diagnostics",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        source_references=(reference,),
        diagnostics=diagnostics,
    )


def _review_input(
    target: ProjectMaterialBundleV1 | None = None,
    diagnostics: DiagnosticResultSetV1 | None = None,
) -> ReviewInputV1:
    target = target or _material()
    diagnostics = diagnostics or _diagnostic_result(target)
    return ReviewInputV1.build(
        origin_namespace="technical-bid-review",
        origin_key="asset-review-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        target=target,
        diagnostic_result_set=diagnostics,
    )


def test_review_input_is_deterministic_immutable_and_identity_verified():
    target = _material()
    diagnostics = _diagnostic_result(target)
    first = _review_input(target, diagnostics)
    second = _review_input(target, diagnostics)

    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "review-input"
    assert first.schema_version == "1"
    assert first.parent_revision_id is None
    assert first.target.source_index == 3
    assert first.target.review_state == "UNREVIEWED"
    assert first.target.accepted_for_response_use is False
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())
    with pytest.raises(FrozenInstanceError):
        first.revision_id = "changed"


def test_review_input_preserves_route_c_profiles_without_deciding_review():
    value = _review_input()
    record = value.to_dict()

    assert value.provenance.canonical_profile_id == CANONICAL_PROFILE_ID
    assert value.provenance.canonical_json_algorithm == CANONICAL_JSON_ALGORITHM
    assert value.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID
    assert CANONICAL_PROFILE_ID == "OC_ROUTE_C_CANONICAL_V1"
    assert CANONICAL_JSON_ALGORITHM == "OC_CANONICAL_JSON_V1"
    assert BOOTSTRAP_RULE_ID == "OC_NON_CIRCULAR_INITIAL_GENERATION_V1"
    assert "recommendation" not in record
    assert "review_event" not in record
    assert "approval" not in record


def test_diagnostic_reference_and_first_error_are_bound_to_the_target():
    target = _material()
    diagnostic = DiagnosticV1(
        code="SCHEMA_VIOLATION",
        phase="30_SCHEMA",
        json_pointer="/payload/title",
        source_index=3,
        detail_code="TITLE_INVALID",
    )
    diagnostics = _diagnostic_result(target, diagnostics=(diagnostic,))
    value = _review_input(target, diagnostics)

    assert value.first_error_code == "SCHEMA_VIOLATION"
    assert value.diagnostic_result_set.diagnostic_count == 1
    assert value.diagnostic_result_set.record_sha256 == diagnostics.record_sha256
    assert value.target.record_sha256 == target.record_sha256


def test_missing_or_ambiguous_diagnostic_target_fails_closed():
    target = _material()
    unrelated = _diagnostic_result(target, match_target=False)

    with pytest.raises(CanonicalError) as exc:
        _review_input(target, unrelated)
    assert exc.value.code == "REF_TARGET_MISSING"

    result = assemble_review_input(
        ReviewInputAdapterInputV1(
            origin_namespace="technical-bid-review",
            origin_key="asset-review-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            target=target,
            diagnostic_result_set=unrelated,
        )
    )
    assert result.review_input is None
    assert result.first_error == "REF_TARGET_MISSING"
    assert result.diagnostics[0].phase == "70_REFERENCE"


def test_invalid_identity_and_non_initial_state_fail_closed():
    target = _material()
    diagnostics = _diagnostic_result(target)
    invalid_identity = replace(target, record_sha256="c" * 64)
    invalid_state = replace(target, review_state="APPROVED", accepted_for_response_use=True)

    identity_result = assemble_review_input(
        ReviewInputAdapterInputV1(
            "technical-bid-review",
            "asset-review-1",
            "automatic",
            ("automatic",),
            invalid_identity,
            diagnostics,
        )
    )
    state_result = assemble_review_input(
        ReviewInputAdapterInputV1(
            "technical-bid-review",
            "asset-review-1",
            "automatic",
            ("automatic",),
            invalid_state,
            diagnostics,
        )
    )

    assert identity_result.review_input is None
    assert identity_result.first_error == "REVIEW_IDENTITY_INVALID"
    assert state_result.review_input is None
    assert state_result.first_error == "REVIEW_STATE_INVALID"
    assert identity_result.diagnostics[0].phase == "80_REVIEW"
    assert state_result.diagnostics[0].phase == "80_REVIEW"


def test_source_mode_promotion_is_rejected_and_adapter_success_is_explicit():
    target = _material()
    diagnostics = _diagnostic_result(target)
    invalid = assemble_review_input(
        ReviewInputAdapterInputV1(
            "technical-bid-review",
            "asset-review-1",
            "manual",
            ("manual",),
            target,
            diagnostics,
        )
    )
    valid = assemble_review_input(
        ReviewInputAdapterInputV1(
            "technical-bid-review",
            "asset-review-1",
            "automatic",
            ("automatic",),
            target,
            diagnostics,
        )
    )

    assert invalid.review_input is None
    assert invalid.first_error == "SRC_MODE_PROMOTION_FORBIDDEN"
    assert invalid.diagnostics[0].phase == "40_SOURCE_MODE"
    assert valid.diagnostics == ()
    assert valid.first_error == "NONE"
    assert valid.review_input is not None
    assert valid.review_input.verify_identity()
