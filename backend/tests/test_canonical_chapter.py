from dataclasses import FrozenInstanceError

import pytest

from backend.zhifei_autoplan.canonical.chapter import ChapterGenerationRequestV1
from backend.zhifei_autoplan.canonical.chapter_adapter import (
    ChapterCandidateV1,
    create_grounded_chapter_request,
    create_initial_chapter_request,
    handoff_generated_chapters,
)
from backend.zhifei_autoplan.canonical.common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    canonical_json_bytes,
)
from backend.zhifei_autoplan.canonical.evidence import (
    ResponseEvidenceItemV2,
    ResponseEvidenceSetInputV2,
    ResponseEvidenceSetV2,
    TechnicalBidEvidenceMatrixInputV2,
    TechnicalBidEvidenceMatrixV2,
    TechnicalBidEvidenceRequirementV2,
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


def _initial_request():
    return create_initial_chapter_request(
        origin_namespace="technical-bid",
        origin_key="chapter-set-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        source_references=(_reference("b", (2,)), _reference("a")),
    )


def _initial_chapter_set():
    request = _initial_request()
    return handoff_generated_chapters(
        request=request,
        candidates=(
            ChapterCandidateV1(
                "compliance",
                "Compliance",
                "The response follows the verified requirement.",
                (_reference("b", (2,)),),
            ),
            ChapterCandidateV1(
                "method",
                "Cafe\u0301 Method",
                "Verified method\r\nwith programme.",
                (_reference("a"),),
            ),
        ),
    )


def _unaccepted_response_evidence_set():
    reference = _reference("a")
    rule = ScoringRuleV2.create(
        rule_id="rule-a",
        rule_kind="points",
        title="Method",
        description="Method statement",
        maximum_score="20",
        parameters={"weight": "2"},
        source_references=(reference,),
    )
    rule_set = ScoringRuleSetV2.build(
        ScoringRuleSetInputV2(
            origin_namespace="tender-scoring",
            origin_key="schedule-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            extractor_identity=ScoringExtractorIdentityV1("scoring-parser", "1"),
            rules=(rule,),
        )
    )
    requirement = TechnicalBidEvidenceRequirementV2.create(
        requirement_id="req-a",
        rule_id="rule-a",
        evidence_kind="method-statement",
        description="Method evidence",
        source_references=(reference,),
    )
    matrix = TechnicalBidEvidenceMatrixV2.build(
        TechnicalBidEvidenceMatrixInputV2(
            origin_namespace="technical-bid",
            origin_key="matrix-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            scoring_rule_set=rule_set,
            requirements=(requirement,),
        )
    )
    item = ResponseEvidenceItemV2.create(
        evidence_id="evidence-a",
        requirement_id="req-a",
        evidence_kind="method-statement",
        statement="Verified method evidence.",
        source_references=(reference,),
    )
    return ResponseEvidenceSetV2.build(
        ResponseEvidenceSetInputV2(
            origin_namespace="technical-bid",
            origin_key="response-evidence-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            evidence_matrix=matrix,
            evidence_items=(item,),
        )
    )


def test_initial_request_is_non_circular_deterministic_and_identity_verified():
    first = _initial_request()
    second = ChapterGenerationRequestV1.build(
        origin_namespace="technical-bid",
        origin_key="chapter-set-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        source_references=(_reference("a"), _reference("b", (2,))),
        generation_index=0,
        generation_phase="INITIAL",
    )

    assert CANONICAL_PROFILE_ID == "OC_ROUTE_C_CANONICAL_V1"
    assert CANONICAL_JSON_ALGORITHM == "OC_CANONICAL_JSON_V1"
    assert BOOTSTRAP_RULE_ID == "OC_NON_CIRCULAR_INITIAL_GENERATION_V1"
    assert first == second
    assert first.verify_identity()
    assert first.generation_index == 0
    assert first.generation_phase == "INITIAL"
    assert first.parent_chapter_revision_id is None
    assert first.response_evidence_refs == ()
    assert first.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())


def test_chapter_handoff_is_pure_immutable_deterministic_and_provisional():
    first = _initial_chapter_set()
    request = _initial_request()
    second = handoff_generated_chapters(
        request=request,
        candidates=tuple(
            reversed(
                (
                    ChapterCandidateV1(
                        "compliance",
                        "Compliance",
                        "The response follows the verified requirement.",
                        (_reference("b", (2,)),),
                    ),
                    ChapterCandidateV1(
                        "method",
                        "Café Method",
                        "Verified method\nwith programme.",
                        (_reference("a"),),
                    ),
                )
            )
        ),
    )

    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "chapter-set"
    assert first.review_state == "PROVISIONAL"
    assert first.accepted_for_response_use is False
    assert [item.chapter_key for item in first.chapters] == ["compliance", "method"]
    assert first.chapters[1].title == "Café Method"
    assert first.chapters[1].body == "Verified method\nwith programme."
    assert first.provenance.generation_request.revision_id == request.revision_id
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())
    with pytest.raises(FrozenInstanceError):
        first.review_state = "ACCEPTED"


def test_initial_request_rejects_parent_or_response_evidence():
    with pytest.raises(CanonicalError) as invalid:
        ChapterGenerationRequestV1.build(
            origin_namespace="technical-bid",
            origin_key="chapter-set-2",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            source_references=(_reference("a"),),
            generation_index=0,
            generation_phase="INITIAL",
            parent_chapter_set=_initial_chapter_set(),
        )
    assert invalid.value.code == "BOOTSTRAP_CYCLE_FORBIDDEN"


def test_grounded_request_rejects_unaccepted_response_evidence():
    response_evidence = _unaccepted_response_evidence_set()
    assert response_evidence.verify_identity()
    assert response_evidence.accepted_for_response_use is False

    with pytest.raises(CanonicalError) as unaccepted:
        create_grounded_chapter_request(
            origin_namespace="technical-bid",
            origin_key="chapter-set-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            source_references=(_reference("a"),),
            generation_index=1,
            parent_chapter_set=_initial_chapter_set(),
            response_evidence_sets=(response_evidence,),
        )
    assert unaccepted.value.code == "REVIEW_ACCEPTANCE_REQUIRED"


def test_generated_chapter_cannot_add_a_new_source_evidence_reference():
    request = _initial_request()
    with pytest.raises(CanonicalError) as new_source:
        handoff_generated_chapters(
            request=request,
            candidates=(
                ChapterCandidateV1(
                    "method",
                    "Method",
                    "Generated text.",
                    (_reference("c", (3,)),),
                ),
            ),
        )
    assert new_source.value.code == "REF_TARGET_MISSING"


def test_project_material_reference_type_rejects_generated_chapter_identity():
    with pytest.raises(CanonicalError) as generated_source:
        SourceProvenanceReferenceV1.create(
            material_stable_id=f"ocrc:chapter-set:{'d' * 64}",
            material_revision_id=f"ocrc-rev:chapter-set:{'d' * 64}",
            material_content_sha256="d" * 64,
            source_locator_indices=(0,),
        )
    assert generated_source.value.code == "REF_TARGET_MISSING"
