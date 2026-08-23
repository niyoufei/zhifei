import pytest

from backend.zhifei_autoplan.canonical.common import CanonicalError, canonical_json_bytes
from backend.zhifei_autoplan.canonical.scoring import (
    ScoringExtractorIdentityV1,
    ScoringRuleSetInputV2,
    ScoringRuleSetV2,
    ScoringRuleV2,
    SourceProvenanceReferenceV1,
)
from backend.zhifei_autoplan.canonical.scoring_adapter import (
    DeterministicScoringExtractorRegistryV1,
    ScoringExtractionInputV1,
    ScoringExtractorRegistrationV1,
    ScoringRuleCandidateV1,
    extract_scoring_rules,
)


def _reference(seed: str, locator_indices=(1, 0)):
    return SourceProvenanceReferenceV1.create(
        material_stable_id=f"ocrc:project-material:{seed * 64}",
        material_revision_id=f"ocrc-rev:project-material:{seed * 64}",
        material_content_sha256=seed * 64,
        source_locator_indices=locator_indices,
    )


def _rule(rule_id, title, reference, *, kind="points", maximum_score="10"):
    return ScoringRuleV2.create(
        rule_id=rule_id,
        rule_kind=kind,
        title=title,
        description="Line one\r\nLine two",
        maximum_score=maximum_score,
        parameters={"threshold": "90", "bands": ["A", "B"]},
        source_references=(reference,),
    )


def test_scoring_rule_set_is_immutable_normalized_deterministic_and_identity_verified():
    first_reference = _reference("a")
    second_reference = _reference("b", (3,))
    rule_b = _rule("rule-b", "Quality", second_reference, maximum_score="20")
    rule_a = _rule("rule-a", "Cafe\u0301", first_reference)
    source = ScoringRuleSetInputV2(
        origin_namespace="tender-scoring",
        origin_key="schedule-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        extractor_identity=ScoringExtractorIdentityV1("scoring-parser", "1"),
        rules=(rule_b, rule_a),
    )
    first = ScoringRuleSetV2.build(source)
    second = ScoringRuleSetV2.build(
        ScoringRuleSetInputV2(
            origin_namespace="tender-scoring",
            origin_key="schedule-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            extractor_identity=ScoringExtractorIdentityV1("scoring-parser", "1"),
            rules=(rule_a, rule_b),
        )
    )

    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "scoring-rule-set"
    assert first.schema_version == "2"
    assert first.accepted_for_response_use is False
    assert first.review_state == "UNREVIEWED"
    assert [item.rule_id for item in first.rules] == ["rule-a", "rule-b"]
    assert first.rules[0].title == "Café"
    assert first.rules[0].description == "Line one\nLine two"
    assert first.rules[0].source_references[0].source_locator_indices == (0, 1)
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())
    with pytest.raises(TypeError):
        first.rules[0].parameters["new"] = "forbidden"


def test_extraction_boundary_normalizes_explicit_candidates_without_c3_artifacts():
    reference = _reference("c", (0,))
    registry = DeterministicScoringExtractorRegistryV1.create(
        (ScoringExtractorRegistrationV1("scoring-parser", "1", ("pass-fail", "points")),)
    )
    source = ScoringExtractionInputV1(
        origin_namespace="tender-scoring",
        origin_key="schedule-2",
        origin_source_mode="manual",
        source_mode_set=("manual",),
        extractor_id="scoring-parser",
        extractor_version="1",
        rules=(
            ScoringRuleCandidateV1(
                "rule-2",
                "pass-fail",
                "Compliance",
                "Mandatory compliance",
                "0",
                {"required": True},
                (reference,),
            ),
            ScoringRuleCandidateV1(
                "rule-1",
                "points",
                "Method",
                "Method statement",
                "30",
                {"scale": [0, 10, 20, 30]},
                (reference,),
            ),
        ),
    )

    result = extract_scoring_rules(source, registry)

    assert result.first_error == "NONE"
    assert result.diagnostics == ()
    assert result.rule_set is not None
    assert [item.rule_id for item in result.rule_set.rules] == ["rule-1", "rule-2"]
    projection = result.rule_set.to_dict()
    assert "evidence_matrix" not in projection
    assert "response_evidence_set" not in projection
    assert projection["provenance"]["rule_source_references"][0]["source_references"]


def test_unsupported_rule_kind_returns_deterministic_fail_closed_diagnostic():
    registry = DeterministicScoringExtractorRegistryV1.create(
        (ScoringExtractorRegistrationV1("scoring-parser", "1", ("points",)),)
    )
    source = ScoringExtractionInputV1(
        origin_namespace="tender-scoring",
        origin_key="schedule-3",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        extractor_id="scoring-parser",
        extractor_version="1",
        rules=(
            ScoringRuleCandidateV1(
                "rule-1",
                "formula",
                "Formula",
                "Unsupported expression",
                "10",
                {"expression": "x / y"},
                (_reference("d", (0,)),),
            ),
        ),
    )

    result = extract_scoring_rules(source, registry)

    assert result.rule_set is None
    assert result.first_error == "SCHEMA_VIOLATION"
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].detail_code == "SCORING_RULE_UNSUPPORTED"
    assert result.diagnostics[0].json_pointer == "/rules/0/rule_kind"


def test_source_reference_boundary_and_duplicate_rules_fail_closed():
    with pytest.raises(CanonicalError) as invalid_reference:
        SourceProvenanceReferenceV1.create(
            material_stable_id=f"ocrc:wrong:{'a' * 64}",
            material_revision_id=f"ocrc-rev:project-material:{'a' * 64}",
            material_content_sha256="a" * 64,
            source_locator_indices=(0,),
        )
    assert invalid_reference.value.code == "REF_TARGET_MISSING"

    reference = _reference("e", (0,))
    rule = _rule("duplicate", "Duplicate", reference)
    with pytest.raises(CanonicalError):
        ScoringRuleSetInputV2(
            origin_namespace="tender-scoring",
            origin_key="schedule-4",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            extractor_identity=ScoringExtractorIdentityV1("scoring-parser", "1"),
            rules=(rule, rule),
        )
