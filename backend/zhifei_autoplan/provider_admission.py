from __future__ import annotations

"""Credential-aware provider admission with redacted durable receipts.

The module deliberately has no provider SDK imports and never initiates network
traffic itself.  A caller may inject an async ``probe`` after its own evidence
and execution gates have passed.  Raw credentials are retained only by the
ephemeral :class:`ProviderCandidate` supplied to that callback; every public
snapshot is built from an explicit allowlist.
"""

import asyncio
import hashlib
import inspect
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "provider-admission-v1"
LATEST_SNAPSHOT_FILENAME = "provider-admission-v1.latest.json"
LAYER_NAMES = (
    "configuration",
    "credentials",
    "model",
    "quota",
    "stream",
    "circuit",
)

_PASS = "pass"
_FAIL = "fail"
_SKIPPED = "skipped"
_UNKNOWN = "unknown"
_VALID_STATUSES = {_PASS, _FAIL, _SKIPPED, _UNKNOWN}
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bAIza[A-Za-z0-9_-]{16,}\b"),
)
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "autoplan" / "provider_admission"
_UNSET = object()


def canonical_digest(value: Any) -> str:
    """Return the SHA-256 of compact, UTF-8, key-sorted canonical JSON."""

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def credential_fingerprint(credential: str | bytes | None) -> str:
    """Create a domain-separated, irreversible credential cache identity."""

    if isinstance(credential, bytes):
        raw = credential
    else:
        raw = str(credential or "").encode("utf-8")
    return hashlib.sha256(b"provider-admission-v1\x00credential\x00" + raw).hexdigest()


def _safe_code(value: Any, default: str) -> str:
    raw = str(value or "").strip()
    if any(pattern.search(raw) for pattern in _SECRET_VALUE_PATTERNS):
        return default
    candidate = raw.lower().replace("-", "_").replace(" ", "_")
    if candidate.startswith(("sk_", "aiza")) or "bearer_" in candidate:
        return default
    return candidate if _SAFE_CODE.fullmatch(candidate) else default


def _normalise_status(value: Any) -> str:
    if isinstance(value, bool):
        return _PASS if value else _FAIL
    if isinstance(value, Mapping):
        value = value.get("status")
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in _VALID_STATUSES:
        return text
    if text in {
        "ok",
        "ready",
        "available",
        "valid",
        "configured",
        "supported",
        "closed",
        "healthy",
        "success",
        "succeeded",
        "admitted",
    }:
        return _PASS
    if text in {
        "failed",
        "blocked",
        "unavailable",
        "invalid",
        "missing",
        "exhausted",
        "unsupported",
        "open",
        "error",
        "rejected",
    }:
        return _FAIL
    if text in {"skip", "not_required", "na", "n_a", "disabled"}:
        return _SKIPPED
    return _UNKNOWN


@dataclass(frozen=True)
class AdmissionLayer:
    status: str
    code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _normalise_status(self.status))
        object.__setattr__(self, "code", _safe_code(self.code, "status_unknown"))

    def as_dict(self) -> dict[str, str]:
        return {"status": self.status, "code": self.code}


def _layer(status: Any, code: Any, *, default_code: str) -> AdmissionLayer:
    return AdmissionLayer(_normalise_status(status), _safe_code(code, default_code))


@dataclass(frozen=True)
class ProviderCandidate:
    """Ephemeral provider material.

    ``credential`` and ``key_alias`` are excluded from repr/equality and from
    every serialization method.  They exist only so an injected probe can
    authenticate without re-reading environment state.
    """

    slot: str
    role: str
    provider: str
    model: str
    credential: str = field(default="", repr=False, compare=False)
    key_alias: str = field(default="", repr=False, compare=False)
    enabled: bool = True
    stream_required: bool = False
    stream_supported: bool = True
    circuit_open: bool = False

    def __post_init__(self) -> None:
        slot = str(self.slot or "").strip().lower()
        role = str(self.role or slot).strip().lower()
        provider = str(self.provider or "").strip().lower()
        object.__setattr__(self, "slot", slot)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", str(self.model or "").strip())
        object.__setattr__(self, "credential", str(self.credential or "").strip())
        object.__setattr__(self, "key_alias", str(self.key_alias or "").strip())

    @classmethod
    def from_value(cls, value: ProviderCandidate | Mapping[str, Any] | Any) -> ProviderCandidate:
        if isinstance(value, cls):
            return value

        def read(name: str, default: Any = None) -> Any:
            if isinstance(value, Mapping):
                return value.get(name, default)
            return getattr(value, name, default)

        credential = read("credential", None)
        if credential is None:
            # Compatibility with existing ProviderSlot.  The alias is accepted
            # only in memory and is never copied to an admission snapshot.
            credential = read("api_key", "")
        return cls(
            slot=read("slot", ""),
            role=read("role", "") or read("slot", ""),
            provider=read("provider", ""),
            model=read("model", ""),
            credential=credential,
            key_alias=read("key_alias", ""),
            enabled=bool(read("enabled", True)),
            stream_required=bool(read("stream_required", False)),
            stream_supported=bool(read("stream_supported", read("supports_stream", True))),
            circuit_open=bool(read("circuit_open", False)),
        )

    @property
    def fingerprint(self) -> str:
        return credential_fingerprint(self.credential)

    @property
    def identity_material(self) -> dict[str, str]:
        return {
            "slot": self.slot,
            "provider": self.provider,
            "model": self.model,
            "credential_fingerprint": self.fingerprint,
        }

    @property
    def identity_digest(self) -> str:
        return canonical_digest(self.identity_material)

    def public_identity(self) -> dict[str, str]:
        result = dict(self.identity_material)
        result["identity_digest"] = self.identity_digest
        return result


@dataclass(frozen=True)
class ProbeOutcome:
    """Safe probe result.  Values may be booleans or status strings."""

    configuration: Any = None
    credentials: Any = _PASS
    model: Any = _PASS
    quota: Any = _PASS
    stream: Any = _PASS
    circuit: Any = None
    code: str = "probe_passed"

    @classmethod
    def success(cls) -> ProbeOutcome:
        return cls()

    @classmethod
    def failure(cls, layer: str, code: str) -> ProbeOutcome:
        if layer not in LAYER_NAMES:
            layer = "configuration"
        values: dict[str, Any] = {name: None for name in LAYER_NAMES}
        values[layer] = _FAIL
        return cls(**values, code=code)


@dataclass(frozen=True)
class ProviderAdmission:
    slot: str
    role: str
    provider: str
    model: str
    credential_fingerprint: str
    identity_digest: str
    admitted: bool
    layers: Mapping[str, AdmissionLayer]
    reason_codes: tuple[str, ...]
    checked_at: float
    expires_at: float
    stream_required: bool = False
    cache_hit: bool = False
    probe_duration_ms: int = 0

    def chain_entry(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "credential_fingerprint": self.credential_fingerprint,
            "identity_digest": self.identity_digest,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.chain_entry(),
            "admitted": bool(self.admitted),
            "layers": {
                name: self.layers[name].as_dict()
                for name in LAYER_NAMES
            },
            "reason_codes": list(self.reason_codes),
            "checked_at": float(self.checked_at),
            "expires_at": float(self.expires_at),
            "stream_required": bool(self.stream_required),
            "cache_hit": bool(self.cache_hit),
            "probe_duration_ms": max(0, int(self.probe_duration_ms)),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ProviderAdmission:
        raw_layers = value.get("layers") if isinstance(value.get("layers"), Mapping) else {}
        layers = {
            name: _layer(
                raw_layers.get(name, {}).get("status")
                if isinstance(raw_layers.get(name), Mapping)
                else _UNKNOWN,
                raw_layers.get(name, {}).get("code")
                if isinstance(raw_layers.get(name), Mapping)
                else "status_unknown",
                default_code="status_unknown",
            )
            for name in LAYER_NAMES
        }
        return cls(
            slot=str(value.get("slot") or ""),
            role=str(value.get("role") or value.get("slot") or ""),
            provider=str(value.get("provider") or ""),
            model=str(value.get("model") or ""),
            credential_fingerprint=str(value.get("credential_fingerprint") or ""),
            identity_digest=str(value.get("identity_digest") or ""),
            admitted=bool(value.get("admitted")),
            layers=layers,
            reason_codes=tuple(
                _safe_code(item, "status_unknown")
                for item in value.get("reason_codes", [])
                if isinstance(item, str)
            ),
            checked_at=float(value.get("checked_at") or 0.0),
            expires_at=float(value.get("expires_at") or 0.0),
            stream_required=bool(value.get("stream_required", False)),
            cache_hit=bool(value.get("cache_hit", False)),
            probe_duration_ms=max(0, int(value.get("probe_duration_ms") or 0)),
        )


ProbeCallback = Callable[[ProviderCandidate], Awaitable[Any] | Any]


def _error_code_and_layer(error: BaseException) -> tuple[str, str]:
    """Classify ephemerally; the raw exception is never retained."""

    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None
    machine_codes: list[str] = []
    for candidate in (getattr(error, "code", None),):
        value = str(candidate or "").strip().lower()
        if value and re.fullmatch(r"[a-z0-9_.-]{1,80}", value):
            machine_codes.append(value)
    body = getattr(error, "body", None)
    if isinstance(body, Mapping):
        nested = body.get("error")
        for candidate in (
            body.get("code"),
            nested.get("code") if isinstance(nested, Mapping) else None,
        ):
            value = str(candidate or "").strip().lower()
            if value and re.fullmatch(r"[a-z0-9_.-]{1,80}", value):
                machine_codes.append(value)
    text = " ".join([str(error or "").lower(), *machine_codes])
    if status == 401 or "unauthorized" in text or "invalid api key" in text:
        return "authentication_failed", "credentials"
    if status == 403 or "forbidden" in text or "permission denied" in text:
        return "permission_denied", "credentials"
    if status == 404 or "model not found" in text or "model_not_found" in text:
        return "model_not_found", "model"
    if any(
        marker in text
        for marker in (
            "insufficient_quota",
            "credit_balance_exhausted",
            "quota exhausted",
            "billing_hard_limit_reached",
            "billing_limit_exceeded",
            "out of credits",
            "no credits remaining",
            "add credits",
            "credit balance",
            "billing hard limit",
            "余额不足",
            "额度不足",
        )
    ):
        return "quota_exhausted", "quota"
    if "stream" in text and any(marker in text for marker in ("unsupported", "not support", "disabled")):
        return "stream_unavailable", "stream"
    if "circuit" in text and "open" in text:
        return "circuit_open", "circuit"
    if status == 429 or "rate limit" in text:
        return "rate_limited", "quota"
    if status is not None and status >= 500:
        return "provider_unavailable", "configuration"
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)) or "timeout" in text:
        return "probe_timeout", "configuration"
    return "probe_failed", "configuration"


def _failure_layer_for_code(code: str) -> str:
    if code in {"authentication_failed", "permission_denied", "credential_missing"}:
        return "credentials"
    if code in {"model_not_found", "model_unavailable", "model_missing"}:
        return "model"
    if code in {"quota_exhausted", "rate_limited", "quota_unavailable"}:
        return "quota"
    if code in {"stream_unavailable", "stream_unsupported"}:
        return "stream"
    if code == "circuit_open":
        return "circuit"
    return "configuration"


def _probe_layers(value: Any, *, stream_required: bool) -> dict[str, AdmissionLayer]:
    if isinstance(value, ProbeOutcome):
        source: Mapping[str, Any] = {
            name: getattr(value, name) for name in LAYER_NAMES
        }
        global_ok: bool | None = None
        code = _safe_code(value.code, "probe_failed")
    elif isinstance(value, bool):
        source = {}
        global_ok = value
        code = "probe_passed" if value else "probe_failed"
    elif isinstance(value, Mapping):
        nested = value.get("layers") if isinstance(value.get("layers"), Mapping) else {}
        source_values: dict[str, Any] = dict(nested)
        aliases = {"credential": "credentials", "configured": "configuration"}
        for name in LAYER_NAMES:
            if name in value:
                source_values[name] = value[name]
        for alias, name in aliases.items():
            if alias in value and name not in source_values:
                source_values[name] = value[alias]
        source = source_values
        marker = value.get("ok", value.get("admitted", value.get("success", None)))
        status_marker = str(value.get("status") or "").strip().lower()
        if marker is None and status_marker:
            parsed = _normalise_status(status_marker)
            marker = parsed == _PASS if parsed in {_PASS, _FAIL} else None
        global_ok = bool(marker) if isinstance(marker, bool) else None
        code = _safe_code(value.get("code"), "probe_passed" if global_ok else "probe_failed")
    else:
        source = {}
        global_ok = False
        code = "invalid_probe_result"

    result: dict[str, AdmissionLayer] = {}
    for name, raw in source.items():
        if name not in LAYER_NAMES or raw is None:
            continue
        raw_code = raw.get("code") if isinstance(raw, Mapping) else code
        result[name] = _layer(raw, raw_code, default_code=code)

    if global_ok is True:
        for name in ("credentials", "model", "quota"):
            result.setdefault(name, AdmissionLayer(_PASS, "probe_passed"))
        if stream_required:
            result.setdefault("stream", AdmissionLayer(_PASS, "stream_ready"))
    elif global_ok is False and not any(layer.status == _FAIL for layer in result.values()):
        failed_layer = _failure_layer_for_code(code)
        result[failed_layer] = AdmissionLayer(_FAIL, code)

    return result


def _preflight_layers(candidate: ProviderCandidate) -> dict[str, AdmissionLayer]:
    configured = bool(candidate.enabled and candidate.slot and candidate.provider)
    layers = {
        "configuration": AdmissionLayer(
            _PASS if configured else _FAIL,
            "configured" if configured else "configuration_missing",
        ),
        "credentials": AdmissionLayer(
            _PASS if bool(candidate.credential) else _FAIL,
            "credential_present" if candidate.credential else "credential_missing",
        ),
        "model": AdmissionLayer(
            _PASS if bool(candidate.model) else _FAIL,
            "model_configured" if candidate.model else "model_missing",
        ),
        "quota": AdmissionLayer(_UNKNOWN, "quota_not_probed"),
        "stream": AdmissionLayer(
            _SKIPPED if not candidate.stream_required else (_PASS if candidate.stream_supported else _FAIL),
            "stream_not_required"
            if not candidate.stream_required
            else ("stream_supported" if candidate.stream_supported else "stream_unsupported"),
        ),
        "circuit": AdmissionLayer(
            _FAIL if candidate.circuit_open else _PASS,
            "circuit_open" if candidate.circuit_open else "circuit_closed",
        ),
    }
    return layers


def _admission_from_layers(
    candidate: ProviderCandidate,
    layers: Mapping[str, AdmissionLayer],
    *,
    now: float,
    ttl_seconds: float,
    probe_duration_ms: int = 0,
) -> ProviderAdmission:
    required = ("configuration", "credentials", "model", "quota", "circuit")
    admitted = all(layers[name].status == _PASS for name in required)
    if candidate.stream_required:
        admitted = admitted and layers["stream"].status == _PASS
    reason_codes = tuple(
        dict.fromkeys(
            layers[name].code
            for name in LAYER_NAMES
            if layers[name].status == _FAIL
            or (layers[name].status == _UNKNOWN and name in required)
        )
    )
    return ProviderAdmission(
        slot=candidate.slot,
        role=candidate.role,
        provider=candidate.provider,
        model=candidate.model,
        credential_fingerprint=candidate.fingerprint,
        identity_digest=candidate.identity_digest,
        admitted=admitted,
        layers=dict(layers),
        reason_codes=reason_codes,
        checked_at=now,
        expires_at=now + max(0.0, ttl_seconds),
        stream_required=candidate.stream_required,
        probe_duration_ms=max(0, int(probe_duration_ms)),
    )


def _record_from_value(value: ProviderAdmission | Mapping[str, Any]) -> ProviderAdmission:
    return value if isinstance(value, ProviderAdmission) else ProviderAdmission.from_dict(value)


def filter_admitted_chain(
    admissions: Iterable[ProviderAdmission | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return the original order with every non-admitted provider removed."""

    return [record.chain_entry() for record in map(_record_from_value, admissions) if record.admitted]


_ROLE_FALLBACKS: Mapping[str, tuple[str, ...]] = {
    "text": ("text", "text_draft", "text_main", "text_backup", "text_compat_google"),
    "text_draft": ("text_draft", "text_main", "text_backup", "text_compat_google"),
    "text_main": ("text_main", "text_backup", "text_compat_google"),
    "image_main": ("image_main", "image_backup"),
    # document_render intentionally has no cross-role fallback.
    "document_render": ("document_render",),
}


def decide_required_roles(
    admissions: Sequence[ProviderAdmission | Mapping[str, Any]],
    required_roles: Sequence[str],
) -> dict[str, Any]:
    """Select one admitted provider for each role and expose fallback state."""

    records = [_record_from_value(value) for value in admissions]
    roles = list(dict.fromkeys(str(role or "").strip().lower() for role in required_roles if str(role or "").strip()))
    decisions: dict[str, Any] = {}
    missing: list[str] = []
    degraded = False

    for role in roles:
        acceptable = _ROLE_FALLBACKS.get(role, (role,))
        ordered: list[tuple[int, ProviderAdmission]] = []
        for fallback_rank, candidate_role in enumerate(acceptable):
            ordered.extend(
                (fallback_rank, record)
                for record in records
                if record.role == candidate_role
            )
        chosen_index = next(
            (index for index, (_, record) in enumerate(ordered) if record.admitted),
            None,
        )
        if chosen_index is None:
            missing.append(role)
            decisions[role] = {
                "status": "fail",
                "selected": None,
                "attempted_slots": [record.slot for _, record in ordered],
            }
            continue
        fallback_rank, selected = ordered[chosen_index]
        used_fallback = bool(fallback_rank > 0 or chosen_index > 0)
        degraded = degraded or used_fallback
        decisions[role] = {
            "status": "degraded" if used_fallback else "pass",
            "selected": selected.chain_entry(),
            "attempted_slots": [record.slot for _, record in ordered[: chosen_index + 1]],
        }

    generation_allowed = bool(roles) and not missing
    fallback_roles: set[str] = set()
    if any(role in {"text", "text_draft", "text_main"} for role in roles):
        fallback_roles.update({"text_backup", "text_compat_google"})
    if "image_main" in roles:
        fallback_roles.add("image_backup")
    configured_fallbacks = [
        record for record in records if record.role in fallback_roles
    ]
    fallback_ready = any(record.admitted for record in configured_fallbacks)
    resilience_degraded = bool(
        generation_allowed and configured_fallbacks and not fallback_ready
    )
    return {
        "required_roles": roles,
        "roles": decisions,
        "missing_roles": missing,
        "generation_allowed": generation_allowed,
        "fallback_configured": bool(configured_fallbacks),
        "fallback_ready": fallback_ready,
        "resilience_degraded": resilience_degraded,
        "degraded": bool(generation_allowed and (degraded or resilience_degraded)),
    }


def _public_chain_entry(record: ProviderAdmission) -> dict[str, str]:
    return {
        "slot": record.slot,
        "role": record.role,
        "provider": record.provider,
        "model": record.model,
    }


def _public_slot(record: ProviderAdmission) -> dict[str, Any]:
    return {
        **_public_chain_entry(record),
        "admitted": bool(record.admitted),
        "layers": {
            name: record.layers[name].as_dict()
            for name in LAYER_NAMES
        },
        "reason_codes": list(record.reason_codes),
        "probe_duration_ms": max(0, int(record.probe_duration_ms)),
    }


def public_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Project an internal 0600 receipt to an API-safe allowlist.

    This strips credential fingerprints, internal identity digests, cache
    metadata, and receipt timestamps.  It is suitable immediately after an
    admission run; health endpoints should use :func:`evaluate_latest_snapshot`
    so TTL and the current credential-bound route are rechecked.
    """

    rows = snapshot.get("slots") if isinstance(snapshot.get("slots"), list) else []
    records = [
        ProviderAdmission.from_dict(row)
        for row in rows
        if isinstance(row, Mapping)
    ]
    required_roles = [
        str(role)
        for role in snapshot.get("required_roles", [])
        if isinstance(role, str)
    ]
    decision = decide_required_roles(records, required_roles)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "degraded"
            if decision["generation_allowed"] and decision["degraded"]
            else "admitted"
            if decision["generation_allowed"]
            else "configured_not_admitted"
        ),
        "required_roles": decision["required_roles"],
        "slots": [_public_slot(record) for record in records],
        "admitted_chain": [
            _public_chain_entry(record) for record in records if record.admitted
        ],
        "missing_roles": decision["missing_roles"],
        "generation_allowed": decision["generation_allowed"],
        "fallback_configured": decision["fallback_configured"],
        "fallback_ready": decision["fallback_ready"],
        "resilience_degraded": decision["resilience_degraded"],
        "degraded": decision["degraded"],
    }
    _assert_safe_snapshot(payload)
    payload["public_digest"] = canonical_digest(payload)
    return payload


def evaluate_latest_snapshot(
    candidates: Sequence[ProviderCandidate | Mapping[str, Any] | Any],
    required_roles: Sequence[str],
    *,
    root: str | os.PathLike[str] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Offline health evaluation against current credential-bound routing.

    A receipt is current only when the complete candidate identity set and
    stream requirements still match and every selected admission is inside its
    TTL.  No probe or provider SDK is invoked.
    """

    evaluated_at = float(time.time() if now is None else now)
    normalized = [ProviderCandidate.from_value(candidate) for candidate in candidates]
    roles = list(
        dict.fromkeys(
            str(role or "").strip().lower()
            for role in required_roles
            if str(role or "").strip()
        )
    )
    configured_slots = sum(
        1
        for candidate in normalized
        if candidate.enabled
        and candidate.slot
        and candidate.provider
        and candidate.model
        and candidate.credential
    )
    snapshot = load_latest_snapshot(root)
    if snapshot is None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "missing",
            "evaluated_at": evaluated_at,
            "configured_slots": configured_slots,
            "receipt_slots": 0,
            "required_roles": roles,
            "slots": [],
            "admitted_chain": [],
            "missing_roles": roles,
            "generation_allowed": False,
            "fallback_configured": False,
            "fallback_ready": False,
            "resilience_degraded": False,
            "degraded": False,
        }
        payload["public_digest"] = canonical_digest(payload)
        return payload

    rows = snapshot.get("slots") if isinstance(snapshot.get("slots"), list) else []
    receipt_records = [
        ProviderAdmission.from_dict(row)
        for row in rows
        if isinstance(row, Mapping)
    ]
    receipt_map = {
        (record.identity_digest, record.stream_required): record
        for record in receipt_records
    }
    current_keys = {
        (candidate.identity_digest, candidate.stream_required)
        for candidate in normalized
    }
    receipt_keys = set(receipt_map)
    route_matches = bool(normalized) and current_keys == receipt_keys
    valid: list[ProviderAdmission] = []
    expired = False
    for candidate in normalized:
        record = receipt_map.get((candidate.identity_digest, candidate.stream_required))
        if record is None:
            continue
        current_layers = _preflight_layers(candidate)
        if any(
            current_layers[name].status == _FAIL
            for name in ("configuration", "credentials", "model", "stream", "circuit")
        ):
            continue
        if evaluated_at >= record.expires_at:
            expired = True
            continue
        valid.append(replace(record, role=candidate.role, cache_hit=False))

    decision = decide_required_roles(valid, roles)
    generation_allowed = bool(route_matches and decision["generation_allowed"])
    degraded = bool(generation_allowed and decision["degraded"])
    if not route_matches:
        status = "stale_route"
    elif expired:
        status = "expired"
    elif generation_allowed and degraded:
        status = "degraded"
    elif generation_allowed:
        status = "admitted"
    else:
        status = "configured_not_admitted"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "evaluated_at": evaluated_at,
        "configured_slots": configured_slots,
        "receipt_slots": len(receipt_records),
        "required_roles": roles,
        "slots": [_public_slot(record) for record in valid],
        "admitted_chain": [
            _public_chain_entry(record) for record in valid if record.admitted
        ] if generation_allowed else [],
        "missing_roles": decision["missing_roles"] if route_matches else roles,
        "generation_allowed": generation_allowed,
        "fallback_configured": decision["fallback_configured"],
        "fallback_ready": bool(generation_allowed and decision["fallback_ready"]),
        "resilience_degraded": bool(
            generation_allowed and decision["resilience_degraded"]
        ),
        "degraded": degraded,
    }
    _assert_safe_snapshot(payload)
    payload["public_digest"] = canonical_digest(payload)
    return payload


def _snapshot_path(root: str | os.PathLike[str] | None) -> Path:
    path = _DEFAULT_ROOT if root is None else Path(root).expanduser().resolve()
    return path if path.suffix.lower() == ".json" else path / LATEST_SNAPSHOT_FILENAME


def _assert_safe_snapshot(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_name, child in value.items():
            name = str(raw_name).strip().lower().replace("-", "_")
            if (
                name in {"key", "api_key", "key_alias", "credential", "secret", "token", "raw_error", "error", "error_message", "prompt", "messages", "url"}
                or name.endswith("_api_key")
                or "raw_error" in name
                or "prompt" in name
            ):
                raise ValueError(f"unsafe provider admission snapshot field: {path}.{raw_name}")
            _assert_safe_snapshot(child, path=f"{path}.{raw_name}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_safe_snapshot(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            raise ValueError(f"credential-shaped value in provider admission snapshot: {path}")
        return
    if value is not None and not isinstance(value, (bool, int, float)):
        raise TypeError(f"non-JSON provider admission snapshot value: {path}")


def _seal_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.pop("admission_digest", None)
    _assert_safe_snapshot(result)
    result["admission_digest"] = canonical_digest(result)
    return result


def write_snapshot(
    snapshot: Mapping[str, Any],
    *,
    root: str | os.PathLike[str] | None = None,
) -> Path:
    """Atomically persist a validated redacted snapshot with mode 0600."""

    payload = dict(snapshot)
    supplied_digest = str(payload.pop("admission_digest", ""))
    _assert_safe_snapshot(payload)
    expected_digest = canonical_digest(payload)
    if supplied_digest != expected_digest:
        raise ValueError("provider admission snapshot digest mismatch")
    payload["admission_digest"] = supplied_digest
    target = _snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".provider-admission-",
        suffix=".tmp",
        dir=str(target.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def load_latest_snapshot(
    root: str | os.PathLike[str] | None = None,
    *,
    strict: bool = False,
) -> dict[str, Any] | None:
    """Read and verify the latest snapshot without creating any path."""

    target = _snapshot_path(root)
    try:
        raw = target.read_text(encoding="utf-8")
        if len(raw.encode("utf-8")) > 2_000_000:
            raise ValueError("provider admission snapshot exceeds size limit")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("provider admission snapshot schema mismatch")
        supplied_digest = str(payload.pop("admission_digest", ""))
        _assert_safe_snapshot(payload)
        expected_digest = canonical_digest(payload)
        if supplied_digest != expected_digest:
            raise ValueError("provider admission snapshot digest mismatch")
        payload["admission_digest"] = supplied_digest
        return payload
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        if strict:
            raise
        return None


class ProviderAdmissionManager:
    """TTL-cached admission coordinator with per-identity async single-flight."""

    def __init__(
        self,
        root: str | os.PathLike[str] | None = None,
        ttl_seconds: float = 300.0,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = _DEFAULT_ROOT if root is None else Path(root).expanduser().resolve()
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self._clock = clock
        self._cache: dict[tuple[str, bool], ProviderAdmission] = {}
        self._inflight: dict[tuple[str, bool], asyncio.Task[ProviderAdmission]] = {}
        self._guard = threading.RLock()
        self._disk_loaded = False

    @property
    def snapshot_path(self) -> Path:
        return _snapshot_path(self.root)

    def reset(
        self,
        *,
        root: str | os.PathLike[str] | None | object = _UNSET,
        remove_snapshot: bool = False,
    ) -> None:
        """Clear process cache; tests may also inject a new storage root."""

        with self._guard:
            for task in self._inflight.values():
                if not task.done():
                    task.cancel()
            self._cache.clear()
            self._inflight.clear()
            if root is not _UNSET:
                self.root = _DEFAULT_ROOT if root is None else Path(root).expanduser().resolve()
            self._disk_loaded = False
        if remove_snapshot:
            try:
                self.snapshot_path.unlink()
            except FileNotFoundError:
                pass

    def load_latest_snapshot(self, *, strict: bool = False) -> dict[str, Any] | None:
        return load_latest_snapshot(self.root, strict=strict)

    def _hydrate_cache(self) -> None:
        with self._guard:
            if self._disk_loaded:
                return
            self._disk_loaded = True
        snapshot = load_latest_snapshot(self.root)
        if not snapshot:
            return
        now = float(self._clock())
        rows = snapshot.get("slots") if isinstance(snapshot.get("slots"), list) else []
        hydrated: dict[tuple[str, bool], ProviderAdmission] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            try:
                record = ProviderAdmission.from_dict(row)
            except (TypeError, ValueError):
                continue
            if not record.identity_digest or now >= record.expires_at:
                continue
            hydrated[(record.identity_digest, record.stream_required)] = replace(record, cache_hit=False)
        with self._guard:
            for cache_key, record in hydrated.items():
                self._cache.setdefault(cache_key, record)

    async def _probe_and_cache(
        self,
        candidate: ProviderCandidate,
        probe: ProbeCallback,
        cache_key: tuple[str, bool],
    ) -> ProviderAdmission:
        layers = _preflight_layers(candidate)
        probe_started = time.monotonic()
        local_failure = any(
            layers[name].status == _FAIL
            for name in ("configuration", "credentials", "model", "stream", "circuit")
        )
        if not local_failure:
            try:
                raw_outcome = probe(candidate)
                if inspect.isawaitable(raw_outcome):
                    raw_outcome = await raw_outcome
                layers.update(_probe_layers(raw_outcome, stream_required=candidate.stream_required))
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 - arbitrary probe errors are classified into fail-closed layers.
                code, failed_layer = _error_code_and_layer(error)
                layers[failed_layer] = AdmissionLayer(_FAIL, code)
        if not candidate.stream_required:
            layers["stream"] = AdmissionLayer(_SKIPPED, "stream_not_required")
        now = float(self._clock())
        admission = _admission_from_layers(
            candidate,
            layers,
            now=now,
            ttl_seconds=self.ttl_seconds,
            probe_duration_ms=max(
                0,
                int((time.monotonic() - probe_started) * 1000),
            ),
        )
        with self._guard:
            self._cache[cache_key] = admission
            current = asyncio.current_task()
            if self._inflight.get(cache_key) is current:
                self._inflight.pop(cache_key, None)
        return admission

    async def admit(
        self,
        candidate: ProviderCandidate | Mapping[str, Any] | Any,
        *,
        probe: ProbeCallback,
        force: bool = False,
    ) -> ProviderAdmission:
        normalized = ProviderCandidate.from_value(candidate)
        cache_key = (normalized.identity_digest, normalized.stream_required)
        now = float(self._clock())
        loop = asyncio.get_running_loop()
        with self._guard:
            cached = self._cache.get(cache_key)
            if not force and cached is not None and now < cached.expires_at:
                return replace(cached, role=normalized.role, cache_hit=True)
            task = self._inflight.get(cache_key)
            if task is not None and (task.done() or task.get_loop() is not loop):
                self._inflight.pop(cache_key, None)
                task = None
            if task is None:
                task = loop.create_task(self._probe_and_cache(normalized, probe, cache_key))
                self._inflight[cache_key] = task
        result = await asyncio.shield(task)
        return replace(result, role=normalized.role)

    async def admit_chain(
        self,
        *,
        candidates: Sequence[ProviderCandidate | Mapping[str, Any] | Any],
        probe: ProbeCallback,
        required_roles: Sequence[str],
        force: bool = False,
    ) -> dict[str, Any]:
        """Probe/cache a chain, filter failures, decide roles, and persist it."""

        self._hydrate_cache()
        normalized = [ProviderCandidate.from_value(candidate) for candidate in candidates]
        admissions = list(
            await asyncio.gather(
                *(self.admit(candidate, probe=probe, force=force) for candidate in normalized)
            )
        )
        admitted_chain = filter_admitted_chain(admissions)
        decision = decide_required_roles(admissions, required_roles)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": float(self._clock()),
            "ttl_seconds": self.ttl_seconds,
            "required_roles": decision["required_roles"],
            "slots": [record.as_dict() for record in admissions],
            "admitted_chain": admitted_chain,
            "role_decision": decision["roles"],
            "missing_roles": decision["missing_roles"],
            "generation_allowed": decision["generation_allowed"],
            "fallback_configured": decision["fallback_configured"],
            "fallback_ready": decision["fallback_ready"],
            "resilience_degraded": decision["resilience_degraded"],
            "degraded": decision["degraded"],
        }
        snapshot = _seal_snapshot(payload)
        write_snapshot(snapshot, root=self.root)
        return snapshot


__all__ = [
    "LATEST_SNAPSHOT_FILENAME",
    "LAYER_NAMES",
    "SCHEMA_VERSION",
    "AdmissionLayer",
    "ProbeOutcome",
    "ProviderAdmission",
    "ProviderAdmissionManager",
    "ProviderCandidate",
    "canonical_digest",
    "credential_fingerprint",
    "decide_required_roles",
    "evaluate_latest_snapshot",
    "filter_admitted_chain",
    "load_latest_snapshot",
    "public_snapshot",
    "write_snapshot",
]
