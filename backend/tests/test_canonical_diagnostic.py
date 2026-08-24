from dataclasses import FrozenInstanceError

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
from backend.zhifei_autoplan.canonical.diagnostic_adapter import (
    DiagnosticCandidateV1,
    DiagnosticResultSetInputV1,
    assemble_diagnostic_result_set,
)


def _reference(source_index: int, marker: str = "a") -> DiagnosticSourceReferenceV1:
    return DiagnosticSourceReferenceV1.create(
        source_index=source_index,
        artifact_type="chapter-set",
        stable_id=f"ocrc:chapter-set:{marker * 64}",
        revision_id=f"ocrc-rev:chapter-set:{marker * 64}",
        record_sha256=marker * 64,
    )


def _diagnostics() -> tuple[DiagnosticV1, ...]:
    return (
        DiagnosticV1(
            code="REF_TARGET_MISSING",
            phase="70_REFERENCE",
            json_pointer="/chapters/1/source",
            source_index=1,
            detail_code="CHAPTER_SOURCE_ABSENT",
            message="Referenced source is absent.",
        ),
        DiagnosticV1(
            code="SER_DECODE_INVALID",
            phase="10_DECODE",
            json_pointer="/chapters/0",
            source_index=0,
            message="Input cannot be decoded.",
        ),
        DiagnosticV1(
            code="SCHEMA_VIOLATION",
            phase="30_SCHEMA",
            json_pointer="/chapters/0/title",
            source_index=0,
            detail_code="TITLE_REQUIRED",
        ),
    )


def _result(diagnostics: tuple[DiagnosticV1, ...] | None = None) -> DiagnosticResultSetV1:
    return DiagnosticResultSetV1.build(
        origin_namespace="technical-bid",
        origin_key="chapter-set-1",
        origin_source_mode="automatic",
        source_mode_set=("automatic",),
        source_references=(_reference(1, "b"), _reference(0, "a")),
        diagnostics=_diagnostics() if diagnostics is None else diagnostics,
    )


def test_result_set_is_deterministic_immutable_and_identity_verified():
    first = _result()
    second = _result(tuple(reversed(_diagnostics())))

    assert CANONICAL_PROFILE_ID == "OC_ROUTE_C_CANONICAL_V1"
    assert CANONICAL_JSON_ALGORITHM == "OC_CANONICAL_JSON_V1"
    assert BOOTSTRAP_RULE_ID == "OC_NON_CIRCULAR_INITIAL_GENERATION_V1"
    assert first == second
    assert first.verify_identity()
    assert first.artifact_type == "diagnostic-result-set"
    assert first.parent_revision_id is None
    assert first.provenance.bootstrap_rule_id == BOOTSTRAP_RULE_ID
    assert [item.source_index for item in first.provenance.source_references] == [0, 1]
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())
    with pytest.raises(FrozenInstanceError):
        first.revision_id = "changed"


def test_diagnostic_code_severity_and_first_error_order_are_preserved():
    result = _result()

    assert [item.code for item in result.diagnostics] == [
        "SER_DECODE_INVALID",
        "SCHEMA_VIOLATION",
        "REF_TARGET_MISSING",
    ]
    assert [item.severity for item in result.diagnostics] == ["FATAL", "ERROR", "ERROR"]
    assert result.first_error is result.diagnostics[0]
    assert result.first_error_code == "SER_DECODE_INVALID"
    assert result.to_dict()["first_error"] == result.diagnostics[0].to_dict()


def test_source_reference_boundary_rejects_missing_or_circular_targets():
    with pytest.raises(CanonicalError) as missing:
        DiagnosticResultSetV1.build(
            origin_namespace="technical-bid",
            origin_key="chapter-set-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            source_references=(_reference(0),),
            diagnostics=(
                DiagnosticV1(
                    code="SCHEMA_VIOLATION",
                    phase="30_SCHEMA",
                    source_index=1,
                ),
            ),
        )
    assert missing.value.code == "REF_TARGET_MISSING"

    with pytest.raises(CanonicalError) as circular:
        DiagnosticSourceReferenceV1.create(
            source_index=0,
            artifact_type="diagnostic-result-set",
            stable_id=f"ocrc:diagnostic-result-set:{'c' * 64}",
            revision_id=f"ocrc-rev:diagnostic-result-set:{'c' * 64}",
            record_sha256="c" * 64,
        )
    assert circular.value.code == "BOOTSTRAP_CYCLE_FORBIDDEN"


def test_empty_result_boundary_has_no_first_error():
    result = _result(())

    assert result.diagnostics == ()
    assert result.first_error is None
    assert result.first_error_code == "NONE"
    assert result.verify_identity()


def test_adapter_only_canonicalizes_explicit_candidates_and_fails_closed():
    valid = assemble_diagnostic_result_set(
        DiagnosticResultSetInputV1(
            origin_namespace="technical-bid",
            origin_key="chapter-set-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            source_references=(_reference(0),),
            diagnostics=(
                DiagnosticCandidateV1(
                    code="SCHEMA_VIOLATION",
                    phase="30_SCHEMA",
                    source_index=0,
                    json_pointer="/chapters/0",
                    detail_code="CHAPTER_INVALID",
                ),
            ),
        )
    )
    assert valid.diagnostics == ()
    assert valid.result_set is not None
    assert valid.result_set.verify_identity()

    invalid = assemble_diagnostic_result_set(
        DiagnosticResultSetInputV1(
            origin_namespace="technical-bid",
            origin_key="chapter-set-1",
            origin_source_mode="automatic",
            source_mode_set=("automatic",),
            source_references=(_reference(0),),
            diagnostics=(DiagnosticCandidateV1("UNKNOWN_CODE", "30_SCHEMA", 0),),
        )
    )
    assert invalid.result_set is None
    assert invalid.first_error == "SCHEMA_VIOLATION"
    assert invalid.diagnostics[0].detail_code == "SCHEMA_VIOLATION"
