import hashlib

import pytest

from backend.zhifei_autoplan.canonical.common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    DiagnosticV1,
    canonical_json_bytes,
    canonical_set_array,
    derive_revision_id,
    derive_stable_id,
    effective_source_mode,
    first_error_diagnostic,
    profile_digest,
    require_no_source_mode_promotion,
)


def test_frozen_profile_constants_and_canonical_json_golden_vector():
    assert CANONICAL_PROFILE_ID == "OC_ROUTE_C_CANONICAL_V1"
    assert CANONICAL_JSON_ALGORITHM == "OC_CANONICAL_JSON_V1"
    assert BOOTSTRAP_RULE_ID == "OC_NON_CIRCULAR_INITIAL_GENERATION_V1"
    value = {"z": 1, "control": "\n", "a": "e\u0301"}
    assert canonical_json_bytes(value) == b'{"a":"\xc3\xa9","control":"\\u000a","z":1}'


def test_unicode_line_boundary_collision_and_float_rejection():
    assert canonical_json_bytes({"body": "A\r\nB\rC"}, human_text_paths=frozenset({"/body"})) == b'{"body":"A\\u000aB\\u000aC"}'
    with pytest.raises(CanonicalError, match="duplicate object key") as collision:
        canonical_json_bytes({"é": 1, "e\u0301": 2})
    assert collision.value.code == "UNI_NORMALIZED_KEY_COLLISION"
    with pytest.raises(CanonicalError) as floating:
        canonical_json_bytes({"value": 1.5})
    assert floating.value.code == "SCHEMA_VIOLATION"


def test_all_five_hash_profiles_use_the_frozen_domain_preimage():
    projection = {"a": 1}
    canonical = b'{"a":1}'
    for profile in (
        "content-sha256",
        "provenance-sha256",
        "stable-id",
        "revision-id",
        "record-sha256",
    ):
        expected_preimage = b"\x00".join(
            (b"OPENCLAW-ZHIFEI-ROUTE-C", profile.encode("ascii"), b"project-material", b"1", canonical)
        )
        assert profile_digest(profile, "project-material", "1", projection) == hashlib.sha256(expected_preimage).hexdigest()


def test_stable_revision_set_array_source_modes_and_first_error_ordering():
    stable = derive_stable_id("project-material", "1", {"origin_key": "K"})
    revision = derive_revision_id("project-material", "1", {"stable_id": stable})
    assert stable.startswith("ocrc:project-material:")
    assert revision.startswith("ocrc-rev:project-material:")
    assert canonical_set_array(["z", "a"]) == ["a", "z"]
    with pytest.raises(CanonicalError):
        canonical_set_array(["é", "e\u0301"])
    assert effective_source_mode(("automatic", "manual")) == "manual"
    assert effective_source_mode(("automatic", "fixture")) == "fixture"
    with pytest.raises(CanonicalError) as promotion:
        require_no_source_mode_promotion(("automatic", "manual"), ("manual",))
    assert promotion.value.code == "SRC_MODE_PROMOTION_FORBIDDEN"
    diagnostics = (
        DiagnosticV1("HASH_MISMATCH", "60_IDENTITY_HASH", "/a", 0),
        DiagnosticV1("SCHEMA_VIOLATION", "30_SCHEMA", "/z", 1),
        DiagnosticV1("SCHEMA_VIOLATION", "30_SCHEMA", "/a", 2),
    )
    assert first_error_diagnostic(diagnostics) == diagnostics[2]
