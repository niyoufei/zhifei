from dataclasses import FrozenInstanceError

import pytest

from backend.zhifei_autoplan.canonical.common import CanonicalError, canonical_json_bytes
from backend.zhifei_autoplan.canonical.evidence import (
    ResponseEvidenceItemV2,
    ResponseEvidenceSetInputV2,
    ResponseEvidenceSetV2,
    TechnicalBidEvidenceMatrixInputV2,
    TechnicalBidEvidenceMatrixV2,
    TechnicalBidEvidenceRequirementV2,
)
from backend.zhifei_autoplan.canonical.evidence_adapter import (
    EvidenceAssemblyInputV2,
    EvidenceRequirementCandidateV2,
    ResponseEvidenceCandidateV2,
    assemble_evidence_artifacts,
)
from backend.zhifei_autoplan.canonical.scoring import (
    ScoringExtractorIdentityV1,
    ScoringRuleSetInputV2,
    ScoringRuleSetV2,
    ScoringRuleV2,
    SourceProvenanceReferenceV1,
)


def _reference(seed: str, indices=(1, 0)):
    return SourceProvenanceReferenceV1.create(
        material_stable_id=f"ocrc:project-material:{seed * 64}",
        material_revision_id=f"ocrc-rev:project-material:{seed * 64}",
        material_content_sha256=seed * 64,
        source_locator_indices=indices,
    )


def _rule_set(source_mode_set=("automatic",)):
    first = ScoringRuleV2.create(
        rule_id="rule-a",
        rule_kind="points",
        title="Method",
        description="Method statement",
        maximum_score="20",
        parameters={"weight": "2"},
        source_references=(_reference("a"),),
    )
    second = ScoringRuleV2.create(
        rule_id="rule-b",
        rule_kind="pass-fail",
        title="Compliance",
        description="Mandatory compliance",
        maximum_score="0",
        parameters={"required": True},
        source_references=(_reference("b", (2,)),),
    )
    return ScoringRuleSetV2.build(
        ScoringRuleSetInputV2(
            origin_namespace="tender-scoring",
            origin_key="schedule-1",
            origin_source_mode=source_mode_set[0],
            source_mode_set=source_mode_set,
            extractor_identity=ScoringExtractorIdentityV1("scoring-parser", "1"),
            rules=(second, first),
        )
    )


def _requirements():
    return (
        TechnicalBidEvidenceRequirementV2.create(
            requirement_id="req-b",
            rule_id="rule-b",
            evidence_kind="compliance-statement",
            description="Confirm compliance",
            source_references=(_reference("b", (2,)),),
        ),
        TechnicalBidEvidenceRequirementV2.create(
            requirement_id="req-a",
            rule_id="rule-a",
            evidence_kind="method-statement",
            description="Cafe\u0301 method\r\nwith programme",
            source_references=(_reference("a"),),
        ),
    )


def _matrix(source_mode_set=("automatic",)):
    return TechnicalBidEvidenceMatrixV2.build(
        TechnicalBidEvidenceMatrixInputV2(
            origin_namespace="technical-bid",
            origin_key="matrix-1",
            origin_source_mode=source_mode_set[0],
            source_mode_set=source_mode_set,
            scoring_rule_set=_rule_set(source_mode_set),
            requirements=_requirements(),
        )
    )


def _response_items():
    return (
        ResponseEvidenceItemV2.create(
            evidence_id="evidence-b",
            requirement_id="req-b",
            evidence_kind="compliance-statement",
            statement="Complies with the stated requirement.",
            source_references=(_reference("b", (2,)),),
        ),
        ResponseEvidenceItemV2.create(
            evidence_id="evidence-a",
            requirement_id="req-a",
            evidence_kind="method-statement",
            statement="Cafe\u0301 method\r\nuses the verified programme.",
            source_references=(_reference("a"),),
        ),
    )


def test_evidence_matrix_is_complete_immutable_deterministic_and_identity_verified():
    first = _matrix()
    second = TechnicalBidEvidenceMatrixV2.build(
        TechnicalBidEvidenceMatrixInputV2(
            origin_namespace="technical-bid",
            origin_key="matrix-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            scoring_rule_set=_rule_set(),
            requirements=tuple(reversed(_requirements())),
        )
    )

    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "technical-bid-evidence-matrix"
    assert first.schema_version == "2"
    assert first.review_state == "UNREVIEWED"
    assert first.accepted_for_response_use is False
    assert [item.requirement_id for item in first.requirements] == ["req-a", "req-b"]
    assert first.requirements[0].description == "Café method\nwith programme"
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())
    with pytest.raises(FrozenInstanceError):
        first.review_state = "ACCEPTED"


def test_response_evidence_set_is_linked_immutable_deterministic_and_identity_verified():
    matrix = _matrix()
    first = ResponseEvidenceSetV2.build(
        ResponseEvidenceSetInputV2(
            origin_namespace="technical-bid",
            origin_key="response-evidence-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            evidence_matrix=matrix,
            evidence_items=_response_items(),
        )
    )
    second = ResponseEvidenceSetV2.build(
        ResponseEvidenceSetInputV2(
            origin_namespace="technical-bid",
            origin_key="response-evidence-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            evidence_matrix=matrix,
            evidence_items=tuple(reversed(_response_items())),
        )
    )

    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "response-evidence-set"
    assert first.review_state == "UNREVIEWED"
    assert first.accepted_for_response_use is False
    assert [item.evidence_id for item in first.evidence_items] == ["evidence-a", "evidence-b"]
    assert first.evidence_items[0].statement == "Café method\nuses the verified programme."
    assert first.provenance.evidence_matrix.revision_id == matrix.revision_id
    with pytest.raises(FrozenInstanceError):
        first.accepted_for_response_use = True


def test_explicit_adapter_builds_only_the_two_c3_artifacts():
    reference_a = _reference("a")
    reference_b = _reference("b", (2,))
    result = assemble_evidence_artifacts(
        EvidenceAssemblyInputV2(
            matrix_origin_namespace="technical-bid",
            matrix_origin_key="matrix-2",
            response_origin_namespace="technical-bid",
            response_origin_key="response-evidence-2",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            scoring_rule_set=_rule_set(),
            requirements=(
                EvidenceRequirementCandidateV2(
                    "req-a", "rule-a", "method-statement", "Method evidence", (reference_a,)
                ),
                EvidenceRequirementCandidateV2(
                    "req-b",
                    "rule-b",
                    "compliance-statement",
                    "Compliance evidence",
                    (reference_b,),
                ),
            ),
            response_evidence=(
                ResponseEvidenceCandidateV2(
                    "evidence-a",
                    "req-a",
                    "method-statement",
                    "Verified method evidence.",
                    (reference_a,),
                ),
                ResponseEvidenceCandidateV2(
                    "evidence-b",
                    "req-b",
                    "compliance-statement",
                    "Verified compliance evidence.",
                    (reference_b,),
                ),
            ),
        )
    )

    assert result.evidence_matrix.verify_identity()
    assert result.response_evidence_set.verify_identity()
    assert result.response_evidence_set.provenance.evidence_matrix.record_sha256 == (
        result.evidence_matrix.record_sha256
    )
    projection = result.to_dict()
    assert set(projection) == {"evidence_matrix", "response_evidence_set"}
    assert "chapter" not in canonical_json_bytes(projection).decode("utf-8")
    assert "diagnostic" not in canonical_json_bytes(projection).decode("utf-8")


def test_matrix_rejects_missing_unknown_and_duplicate_requirement_links():
    rule_set = _rule_set()
    req_a = _requirements()[1]
    with pytest.raises(CanonicalError) as missing:
        TechnicalBidEvidenceMatrixInputV2(
            "technical-bid", "matrix-3", "automatic", ("automatic",), rule_set, (req_a,)
        )
    assert missing.value.code == "REF_TARGET_MISSING"

    unknown = TechnicalBidEvidenceRequirementV2.create(
        requirement_id="req-unknown",
        rule_id="rule-unknown",
        evidence_kind="method-statement",
        description="Unknown rule",
        source_references=(_reference("c", (0,)),),
    )
    with pytest.raises(CanonicalError) as unknown_link:
        TechnicalBidEvidenceMatrixInputV2(
            "technical-bid",
            "matrix-3",
            "automatic",
            ("automatic",),
            rule_set,
            (_requirements()[0], req_a, unknown),
        )
    assert unknown_link.value.code == "REF_TARGET_MISSING"

    with pytest.raises(CanonicalError) as duplicate:
        TechnicalBidEvidenceMatrixInputV2(
            "technical-bid",
            "matrix-3",
            "automatic",
            ("automatic",),
            rule_set,
            (req_a, req_a, _requirements()[0]),
        )
    assert duplicate.value.code == "SCHEMA_VIOLATION"


def test_response_set_rejects_missing_unknown_or_kind_mismatched_evidence():
    matrix = _matrix()
    items = _response_items()
    with pytest.raises(CanonicalError) as missing:
        ResponseEvidenceSetInputV2(
            "technical-bid",
            "response-evidence-3",
            "automatic",
            ("automatic",),
            matrix,
            (items[0],),
        )
    assert missing.value.code == "REF_TARGET_MISSING"

    mismatched = ResponseEvidenceItemV2.create(
        evidence_id="evidence-mismatch",
        requirement_id="req-a",
        evidence_kind="compliance-statement",
        statement="Wrong evidence kind.",
        source_references=(_reference("a"),),
    )
    with pytest.raises(CanonicalError) as wrong_kind:
        ResponseEvidenceSetInputV2(
            "technical-bid",
            "response-evidence-3",
            "automatic",
            ("automatic",),
            matrix,
            (mismatched, items[0]),
        )
    assert wrong_kind.value.code == "REF_TARGET_MISSING"

    unknown = ResponseEvidenceItemV2.create(
        evidence_id="evidence-unknown",
        requirement_id="req-unknown",
        evidence_kind="method-statement",
        statement="Unknown requirement.",
        source_references=(_reference("c", (0,)),),
    )
    with pytest.raises(CanonicalError) as unknown_link:
        ResponseEvidenceSetInputV2(
            "technical-bid",
            "response-evidence-3",
            "automatic",
            ("automatic",),
            matrix,
            (items[0], items[1], unknown),
        )
    assert unknown_link.value.code == "REF_TARGET_MISSING"


def test_source_mode_cannot_be_promoted_and_fixture_taint_is_preserved():
    with pytest.raises(CanonicalError) as promotion:
        TechnicalBidEvidenceMatrixInputV2(
            origin_namespace="technical-bid",
            origin_key="matrix-4",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            scoring_rule_set=_rule_set(("fixture",)),
            requirements=_requirements(),
        )
    assert promotion.value.code == "SRC_MODE_PROMOTION_FORBIDDEN"

    matrix = _matrix(("fixture",))
    response = ResponseEvidenceSetV2.build(
        ResponseEvidenceSetInputV2(
            origin_namespace="technical-bid",
            origin_key="response-evidence-4",
            origin_source_mode="fixture",
            source_mode_set=("fixture",),
            evidence_matrix=matrix,
            evidence_items=_response_items(),
        )
    )
    assert matrix.provenance.effective_source_mode == "fixture"
    assert response.provenance.effective_source_mode == "fixture"
    assert response.accepted_for_response_use is False
