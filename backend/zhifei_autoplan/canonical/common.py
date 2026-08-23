"""Pure canonical primitives for the Route C canonical model.

This module deliberately uses only deterministic, in-memory operations.  It
implements the frozen OC_ROUTE_C_CANONICAL_V1 serialization, hashing, source
mode, and diagnostic-ordering rules needed by C1.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Final


CANONICAL_PROFILE_ID: Final = "OC_ROUTE_C_CANONICAL_V1"
CANONICAL_JSON_ALGORITHM: Final = "OC_CANONICAL_JSON_V1"
BOOTSTRAP_RULE_ID: Final = "OC_NON_CIRCULAR_INITIAL_GENERATION_V1"
HASH_DOMAIN: Final = b"OPENCLAW-ZHIFEI-ROUTE-C"

HASH_PROFILES: Final = frozenset(
    {
        "content-sha256",
        "provenance-sha256",
        "stable-id",
        "revision-id",
        "record-sha256",
    }
)
SOURCE_MODES: Final = frozenset({"automatic", "manual", "fixture"})
_DECIMAL_RE: Final = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
_TOKEN_RE: Final = re.compile(r"^[a-z][a-z0-9-]*$")
_DIAGNOSTIC_CODE_RE: Final = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
_DIGEST_RE: Final = re.compile(r"^[0-9a-f]{64}$")

DIAGNOSTIC_REGISTRY: Final = {
    "SER_DECODE_INVALID": "FATAL",
    "SER_DUPLICATE_KEY": "ERROR",
    "UNI_INVALID_SCALAR": "ERROR",
    "UNI_NORMALIZED_KEY_COLLISION": "ERROR",
    "SCHEMA_VIOLATION": "ERROR",
    "SRC_MODE_INVALID": "ERROR",
    "SRC_MODE_PROMOTION_FORBIDDEN": "ERROR",
    "SRC_LOCATOR_KIND_UNKNOWN": "ERROR",
    "SRC_LOCATOR_UNAVAILABLE": "ERROR",
    "HASH_MISMATCH": "ERROR",
    "ID_STABLE_MISMATCH": "ERROR",
    "ID_REVISION_MISMATCH": "ERROR",
    "ID_PARENT_INVALID": "ERROR",
    "REF_TARGET_MISSING": "ERROR",
    "REVIEW_IDENTITY_INVALID": "ERROR",
    "REVIEW_STATE_INVALID": "ERROR",
    "REVIEW_ACCEPTANCE_REQUIRED": "ERROR",
    "CORE_SIDE_EFFECT_FORBIDDEN": "FATAL",
    "BOOTSTRAP_CYCLE_FORBIDDEN": "ERROR",
}

PHASE_RANK: Final = {
    "10_DECODE": 10,
    "20_UNICODE": 20,
    "30_SCHEMA": 30,
    "40_SOURCE_MODE": 40,
    "50_LOCATOR": 50,
    "60_IDENTITY_HASH": 60,
    "70_REFERENCE": 70,
    "80_REVIEW": 80,
    "90_CORE_BOUNDARY": 90,
    "100_BOOTSTRAP": 100,
}


class CanonicalError(ValueError):
    """A fail-closed canonical validation failure."""

    def __init__(self, code: str, message: str, json_pointer: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.json_pointer = json_pointer


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def normalize_text(value: str, *, human_text: bool = False) -> str:
    """Apply the single Route C Unicode boundary to a string."""

    if not isinstance(value, str):
        raise CanonicalError("SCHEMA_VIOLATION", "expected a Unicode string")
    if human_text:
        value = value.replace("\r\n", "\n").replace("\r", "\n")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CanonicalError("UNI_INVALID_SCALAR", "string contains a non-scalar value") from exc
    return unicodedata.normalize("NFC", value)


def validate_digest(value: str) -> str:
    value = normalize_text(value)
    if not _DIGEST_RE.fullmatch(value):
        raise CanonicalError("SCHEMA_VIOLATION", "digest must be 64 lowercase hexadecimal characters")
    return value


def validate_canonical_decimal(value: str) -> str:
    value = normalize_text(value)
    if not _DECIMAL_RE.fullmatch(value):
        raise CanonicalError("SCHEMA_VIOLATION", "invalid canonical decimal string")
    if "." in value and value.endswith("0"):
        raise CanonicalError("SCHEMA_VIOLATION", "canonical decimal has a trailing fractional zero")
    return value


def _normalize_value(value: Any, pointer: str, human_text_paths: frozenset[str]) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise CanonicalError("SCHEMA_VIOLATION", "floating-point JSON numbers are forbidden", pointer)
    if isinstance(value, str):
        return normalize_text(value, human_text=pointer in human_text_paths)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        original_by_key: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise CanonicalError("SCHEMA_VIOLATION", "object keys must be strings", pointer)
            key = normalize_text(raw_key)
            if key in normalized:
                code = "UNI_NORMALIZED_KEY_COLLISION" if original_by_key[key] != raw_key else "SER_DUPLICATE_KEY"
                raise CanonicalError(code, "duplicate object key after NFC normalization", pointer)
            child_pointer = f"{pointer}/{_pointer_token(key)}"
            normalized[key] = _normalize_value(raw_value, child_pointer, human_text_paths)
            original_by_key[key] = raw_key
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return [
            _normalize_value(item, f"{pointer}/{index}", human_text_paths)
            for index, item in enumerate(value)
        ]
    raise CanonicalError("SCHEMA_VIOLATION", f"unsupported canonical value type: {type(value).__name__}", pointer)


def _emit_string(value: str) -> bytes:
    parts = ['"']
    for character in value:
        codepoint = ord(character)
        if character == '"':
            parts.append('\\"')
        elif character == "\\":
            parts.append("\\\\")
        elif codepoint <= 0x1F:
            parts.append(f"\\u{codepoint:04x}")
        else:
            parts.append(character)
    parts.append('"')
    return "".join(parts).encode("utf-8")


def _emit_value(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, list):
        return b"[" + b",".join(_emit_value(item) for item in value) + b"]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda item: item.encode("utf-8"))
        members = (_emit_string(key) + b":" + _emit_value(value[key]) for key in keys)
        return b"{" + b",".join(members) + b"}"
    raise CanonicalError("SCHEMA_VIOLATION", "internal non-canonical value")


def canonical_json_bytes(value: Any, *, human_text_paths: frozenset[str] = frozenset()) -> bytes:
    """Serialize a value using OC_CANONICAL_JSON_V1 with no final newline."""

    normalized = _normalize_value(value, "", human_text_paths)
    return _emit_value(normalized)


def canonical_set_array(values: Sequence[Any]) -> list[Any]:
    """Canonicalize a schema-declared set array and reject duplicates."""

    pairs = sorted(
        ((canonical_json_bytes(value), value) for value in values),
        key=lambda item: item[0],
    )
    for index in range(1, len(pairs)):
        if pairs[index - 1][0] == pairs[index][0]:
            raise CanonicalError("SCHEMA_VIOLATION", "duplicate canonical set-array element")
    return [value for _, value in pairs]


def profile_digest(profile: str, artifact_type: str, schema_version: str, projection: Any) -> str:
    """Hash a canonical projection with the frozen Route C domain preimage."""

    if profile not in HASH_PROFILES:
        raise CanonicalError("SCHEMA_VIOLATION", "unknown hash profile")
    artifact_type = normalize_text(artifact_type)
    schema_version = normalize_text(schema_version)
    try:
        profile_bytes = profile.encode("ascii")
        schema_bytes = schema_version.encode("ascii")
    except UnicodeEncodeError as exc:
        raise CanonicalError("SCHEMA_VIOLATION", "profile and schema version must be ASCII") from exc
    preimage = b"\x00".join(
        (
            HASH_DOMAIN,
            profile_bytes,
            artifact_type.encode("utf-8"),
            schema_bytes,
            canonical_json_bytes(projection),
        )
    )
    return hashlib.sha256(preimage).hexdigest()


def derive_stable_id(artifact_type_token: str, schema_version: str, projection: Any) -> str:
    token = normalize_text(artifact_type_token)
    if not _TOKEN_RE.fullmatch(token):
        raise CanonicalError("SCHEMA_VIOLATION", "invalid artifact type token")
    digest = profile_digest("stable-id", token, schema_version, projection)
    return f"ocrc:{token}:{digest}"


def derive_revision_id(artifact_type_token: str, schema_version: str, projection: Any) -> str:
    token = normalize_text(artifact_type_token)
    if not _TOKEN_RE.fullmatch(token):
        raise CanonicalError("SCHEMA_VIOLATION", "invalid artifact type token")
    digest = profile_digest("revision-id", token, schema_version, projection)
    return f"ocrc-rev:{token}:{digest}"


def identities_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def normalize_source_modes(modes: Sequence[str]) -> tuple[str, ...]:
    normalized = {normalize_text(mode) for mode in modes}
    if not normalized or not normalized.issubset(SOURCE_MODES):
        raise CanonicalError("SRC_MODE_INVALID", "source mode set contains an invalid value")
    return tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))


def effective_source_mode(modes: Sequence[str]) -> str:
    normalized = normalize_source_modes(modes)
    if "fixture" in normalized:
        return "fixture"
    if "manual" in normalized:
        return "manual"
    return "automatic"


def require_no_source_mode_promotion(ancestor_modes: Sequence[str], derived_modes: Sequence[str]) -> None:
    ancestor = set(normalize_source_modes(ancestor_modes))
    derived = set(normalize_source_modes(derived_modes))
    if not ancestor.issubset(derived):
        raise CanonicalError("SRC_MODE_PROMOTION_FORBIDDEN", "derived artifact omitted an ancestor source mode")


@dataclass(frozen=True, slots=True)
class DiagnosticV1:
    code: str
    phase: str
    json_pointer: str = ""
    source_index: int = 0
    detail_code: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        code = normalize_text(self.code)
        phase = normalize_text(self.phase)
        pointer = normalize_text(self.json_pointer)
        if not _DIAGNOSTIC_CODE_RE.fullmatch(code) or code not in DIAGNOSTIC_REGISTRY:
            raise CanonicalError("SCHEMA_VIOLATION", "unknown diagnostic code")
        if phase not in PHASE_RANK:
            raise CanonicalError("SCHEMA_VIOLATION", "unknown diagnostic phase")
        if not isinstance(self.source_index, int) or isinstance(self.source_index, bool) or self.source_index < 0:
            raise CanonicalError("SCHEMA_VIOLATION", "source index must be a non-negative integer")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "json_pointer", pointer)
        if self.detail_code is not None:
            object.__setattr__(self, "detail_code", normalize_text(self.detail_code))
        if self.message is not None:
            object.__setattr__(self, "message", normalize_text(self.message, human_text=True))

    @property
    def severity(self) -> str:
        return DIAGNOSTIC_REGISTRY[self.code]

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "json_pointer": self.json_pointer,
            "phase": self.phase,
            "severity": self.severity,
            "source_index": self.source_index,
        }
        if self.detail_code is not None:
            value["detail_code"] = self.detail_code
        if self.message is not None:
            value["message"] = self.message
        return value


def first_error_diagnostic(diagnostics: Sequence[DiagnosticV1]) -> DiagnosticV1 | None:
    errors = [item for item in diagnostics if item.severity in {"ERROR", "FATAL"}]
    if not errors:
        return None
    return min(
        errors,
        key=lambda item: (
            PHASE_RANK[item.phase],
            item.json_pointer.encode("utf-8"),
            item.code.encode("utf-8"),
            item.source_index,
        ),
    )
