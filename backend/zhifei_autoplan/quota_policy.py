from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


QUOTA_POLICY_FILE = Path("backend/data/autoplan/quota_policy.json")
CONFIG_AUDIT_FILE = Path("backend/data/audit/config.jsonl")

DEFAULT_QUOTA_POLICY: Dict[str, Any] = {
    "config_version": "2026-04-02-saas-quota-v2",
    "defaults": {
        "session": {
            "running_limit": 1,
            "queued_limit": 2,
            "active_limit": 3,
            "warning_ratio": 0.8,
            "tokens_last_hour_warning": 120000,
            "scan_limit": 500,
            "lease_seconds": 900,
            "text_chain_profile": "default",
            "degrade_text_chain_profile": "cost_guard",
        },
        "user": {
            "running_limit": 2,
            "queued_limit": 4,
            "active_limit": 6,
            "warning_ratio": 0.8,
            "tokens_last_hour_warning": 240000,
            "scan_limit": 500,
            "lease_seconds": 900,
            "text_chain_profile": "default",
            "degrade_text_chain_profile": "cost_guard",
        },
    },
    "text_chain_profiles": {
        "default": {
            "slot_order": ["text_main", "text_backup", "text_compat_google"],
        },
        "cost_guard": {
            "slot_order": ["text_backup", "text_compat_google", "text_main"],
        },
    },
    "overrides": {
        "sessions": {},
        "users": {},
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged.get(key) or {}, value)
        else:
            merged[key] = value
    return merged


def _load_policy_doc(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_QUOTA_POLICY))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(DEFAULT_QUOTA_POLICY))
    if not isinstance(raw, dict):
        return json.loads(json.dumps(DEFAULT_QUOTA_POLICY))
    return _deep_merge(DEFAULT_QUOTA_POLICY, raw)


def _validate_scope_policy(raw: Any, *, scope: str) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{scope} quota policy must be object")
    out: Dict[str, Any] = {}
    for key in ("running_limit", "queued_limit", "active_limit", "tokens_last_hour_warning", "scan_limit", "lease_seconds"):
        if key not in raw:
            continue
        value = raw.get(key)
        if value is None:
            out[key] = None
            continue
        parsed = _safe_int(value, None)
        if parsed is None:
            raise ValueError(f"{scope}.{key} must be integer or null")
        if parsed <= 0:
            raise ValueError(f"{scope}.{key} must be positive or null")
        out[key] = parsed
    if "warning_ratio" in raw:
        parsed_ratio = _safe_float(raw.get("warning_ratio"), None)
        if parsed_ratio is None:
            raise ValueError(f"{scope}.warning_ratio must be float")
        if parsed_ratio < 0.5 or parsed_ratio > 0.99:
            raise ValueError(f"{scope}.warning_ratio must be between 0.5 and 0.99")
        out["warning_ratio"] = float(parsed_ratio)
    for key in ("text_chain_profile", "degrade_text_chain_profile"):
        if key not in raw:
            continue
        value = _clean_text(raw.get(key))
        if not value:
            raise ValueError(f"{scope}.{key} must be non-empty string")
        out[key] = value
    return out


def _validate_text_chain_profiles(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return json.loads(json.dumps(DEFAULT_QUOTA_POLICY["text_chain_profiles"]))
    if not isinstance(raw, dict):
        raise ValueError("text_chain_profiles must be object")
    normalized: Dict[str, Any] = {}
    for profile_name, profile in raw.items():
        key = _clean_text(profile_name)
        if not key:
            raise ValueError("text_chain_profiles contains empty key")
        if not isinstance(profile, dict):
            raise ValueError(f"text_chain_profiles.{key} must be object")
        slot_order_raw = profile.get("slot_order")
        if not isinstance(slot_order_raw, list) or not slot_order_raw:
            raise ValueError(f"text_chain_profiles.{key}.slot_order must be non-empty list")
        slot_order = []
        seen: set[str] = set()
        for item in slot_order_raw:
            slot = _clean_text(item)
            if not slot or slot in seen:
                continue
            seen.add(slot)
            slot_order.append(slot)
        if not slot_order:
            raise ValueError(f"text_chain_profiles.{key}.slot_order must contain non-empty slots")
        normalized[key] = {"slot_order": slot_order}
    return normalized


def validate_quota_policy(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("quota policy must be object")
    merged = json.loads(json.dumps(DEFAULT_QUOTA_POLICY))
    config_version = _clean_text(raw.get("config_version"))
    if config_version:
        merged["config_version"] = config_version

    defaults = raw.get("defaults")
    if defaults is not None:
        if not isinstance(defaults, dict):
            raise ValueError("defaults must be object")
        for scope in ("session", "user"):
            if scope in defaults:
                merged["defaults"][scope] = _deep_merge(
                    merged["defaults"][scope],
                    _validate_scope_policy(defaults.get(scope), scope=f"defaults.{scope}"),
                )

    if "text_chain_profiles" in raw:
        merged["text_chain_profiles"] = _validate_text_chain_profiles(raw.get("text_chain_profiles"))
    else:
        merged["text_chain_profiles"] = _validate_text_chain_profiles(merged.get("text_chain_profiles"))

    overrides = raw.get("overrides")
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("overrides must be object")
        normalized_overrides: Dict[str, Dict[str, Any]] = {"sessions": {}, "users": {}}
        for bucket_name, scope in (("sessions", "session"), ("users", "user")):
            bucket = overrides.get(bucket_name)
            if bucket is None:
                continue
            if not isinstance(bucket, dict):
                raise ValueError(f"overrides.{bucket_name} must be object")
            for key, policy in bucket.items():
                tenant_key = _clean_text(key)
                if not tenant_key:
                    raise ValueError(f"overrides.{bucket_name} contains empty key")
                normalized_overrides[bucket_name][tenant_key] = _validate_scope_policy(
                    policy,
                    scope=f"overrides.{bucket_name}.{tenant_key}",
                )
        merged["overrides"] = normalized_overrides

    allowed_profiles = set((merged.get("text_chain_profiles") or {}).keys())
    if not allowed_profiles:
        raise ValueError("text_chain_profiles must define at least one profile")
    for scope_name, scope_policy in (merged.get("defaults") or {}).items():
        if not isinstance(scope_policy, dict):
            continue
        for key in ("text_chain_profile", "degrade_text_chain_profile"):
            value = _clean_text(scope_policy.get(key))
            if value and value not in allowed_profiles:
                raise ValueError(f"defaults.{scope_name}.{key} references unknown text chain profile: {value}")
    for bucket_name, bucket in (merged.get("overrides") or {}).items():
        if not isinstance(bucket, dict):
            continue
        for tenant_key, scope_policy in bucket.items():
            if not isinstance(scope_policy, dict):
                continue
            for key in ("text_chain_profile", "degrade_text_chain_profile"):
                value = _clean_text(scope_policy.get(key))
                if value and value not in allowed_profiles:
                    raise ValueError(f"overrides.{bucket_name}.{tenant_key}.{key} references unknown text chain profile: {value}")

    return merged


def load_quota_policy() -> Dict[str, Any]:
    return _load_policy_doc(QUOTA_POLICY_FILE)


def append_quota_policy_audit(*, action: str, detail: Dict[str, Any] | None = None) -> str:
    CONFIG_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": _clean_text(action) or "quota_policy_update",
        "detail": detail or {},
    }
    with CONFIG_AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(CONFIG_AUDIT_FILE)


def save_quota_policy(raw: Any, *, actor: str | None = None) -> Dict[str, Any]:
    validated = validate_quota_policy(raw)
    QUOTA_POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_POLICY_FILE.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    append_quota_policy_audit(
        action="quota_policy_update",
        detail={
            "actor": _clean_text(actor) or "unknown",
            "config_version": validated.get("config_version"),
            "config_path": str(QUOTA_POLICY_FILE),
        },
    )
    return validated


def _env_limit(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    value = _safe_int(raw, default)
    if value is None:
        return default
    if value <= 0:
        return None
    return value


def _env_float(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return _safe_float(raw, default)


def resolve_quota_policy(
    *,
    scope: str,
    tenant_id: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> Dict[str, Any]:
    scope_name = "user" if _clean_text(scope).lower() == "user" else "session"
    policy_path = QUOTA_POLICY_FILE
    doc = _load_policy_doc(policy_path)
    defaults = doc.get("defaults") if isinstance(doc.get("defaults"), dict) else {}
    scope_defaults = defaults.get(scope_name) if isinstance(defaults.get(scope_name), dict) else {}
    merged = dict(scope_defaults or {})

    overrides = doc.get("overrides") if isinstance(doc.get("overrides"), dict) else {}
    override_scope = "none"
    override_key = ""
    override_bucket_key = "users" if scope_name == "user" else "sessions"
    override_bucket = overrides.get(override_bucket_key) if isinstance(overrides.get(override_bucket_key), dict) else {}
    lookup_keys: list[str] = []
    if scope_name == "user" and user_id is not None:
        lookup_keys.append(str(user_id))
    if scope_name == "session" and _clean_text(session_id):
        lookup_keys.append(_clean_text(session_id))
    if _clean_text(tenant_id):
        lookup_keys.append(_clean_text(tenant_id))
    for key in lookup_keys:
        if key in override_bucket and isinstance(override_bucket.get(key), dict):
            merged = _deep_merge(merged, override_bucket.get(key) or {})
            override_scope = scope_name
            override_key = key
            break

    env_overrides: list[str] = []
    running_limit = _env_limit(f"ZF_{scope_name.upper()}_RUNNING_JOB_LIMIT", _safe_int(merged.get("running_limit"), 1))
    if os.getenv(f"ZF_{scope_name.upper()}_RUNNING_JOB_LIMIT"):
        env_overrides.append(f"ZF_{scope_name.upper()}_RUNNING_JOB_LIMIT")
    queued_limit = _env_limit(f"ZF_{scope_name.upper()}_QUEUED_JOB_LIMIT", _safe_int(merged.get("queued_limit"), 1))
    if os.getenv(f"ZF_{scope_name.upper()}_QUEUED_JOB_LIMIT"):
        env_overrides.append(f"ZF_{scope_name.upper()}_QUEUED_JOB_LIMIT")
    active_default = _safe_int(merged.get("active_limit"), None)
    if active_default is None and running_limit is not None and queued_limit is not None:
        active_default = int(running_limit) + int(queued_limit)
    active_limit = _env_limit(f"ZF_{scope_name.upper()}_ACTIVE_JOB_LIMIT", active_default)
    if os.getenv(f"ZF_{scope_name.upper()}_ACTIVE_JOB_LIMIT"):
        env_overrides.append(f"ZF_{scope_name.upper()}_ACTIVE_JOB_LIMIT")

    warning_ratio = _env_float(
        f"ZF_{scope_name.upper()}_WARNING_RATIO",
        _env_float("ZF_JOB_WARNING_RATIO", _safe_float(merged.get("warning_ratio"), 0.8)),
    )
    if os.getenv(f"ZF_{scope_name.upper()}_WARNING_RATIO"):
        env_overrides.append(f"ZF_{scope_name.upper()}_WARNING_RATIO")
    elif os.getenv("ZF_JOB_WARNING_RATIO"):
        env_overrides.append("ZF_JOB_WARNING_RATIO")
    if warning_ratio is None:
        warning_ratio = 0.8
    warning_ratio = max(0.5, min(0.99, float(warning_ratio)))

    tokens_default = _safe_int(merged.get("tokens_last_hour_warning"), None)
    tokens_last_hour_warning = _env_limit(f"ZF_{scope_name.upper()}_TOKENS_LAST_HOUR_WARNING", tokens_default)
    if os.getenv(f"ZF_{scope_name.upper()}_TOKENS_LAST_HOUR_WARNING"):
        env_overrides.append(f"ZF_{scope_name.upper()}_TOKENS_LAST_HOUR_WARNING")

    scan_limit = max(
        20,
        int(
            _env_limit(
                "ZF_JOB_ADMISSION_SCAN_LIMIT",
                _safe_int(merged.get("scan_limit"), 500),
            )
            or 500
        ),
    )
    if os.getenv("ZF_JOB_ADMISSION_SCAN_LIMIT"):
        env_overrides.append("ZF_JOB_ADMISSION_SCAN_LIMIT")
    lease_seconds = max(
        60,
        int(
            _env_limit(
                "ZF_JOB_LEASE_SECONDS",
                _safe_int(merged.get("lease_seconds"), 900),
            )
            or 900
        ),
    )
    if os.getenv("ZF_JOB_LEASE_SECONDS"):
        env_overrides.append("ZF_JOB_LEASE_SECONDS")

    source_parts = ["config"]
    if override_scope != "none":
        source_parts.append(f"{override_scope}_override")
    if env_overrides:
        source_parts.append("env")

    return {
        "scope": scope_name,
        "tenant_id": _clean_text(tenant_id) or None,
        "session_id": _clean_text(session_id) or None,
        "user_id": user_id,
        "config_path": str(policy_path),
        "config_version": _clean_text(doc.get("config_version")) or DEFAULT_QUOTA_POLICY["config_version"],
        "policy_source": "+".join(source_parts),
        "override_scope": override_scope,
        "override_key": override_key or None,
        "env_overrides": env_overrides,
        "running_limit": running_limit,
        "queued_limit": queued_limit,
        "active_limit": active_limit,
        "warning_ratio": warning_ratio,
        "tokens_last_hour_warning": tokens_last_hour_warning,
        "scan_limit": scan_limit,
        "lease_seconds": lease_seconds,
        "text_chain_profile": _clean_text(merged.get("text_chain_profile")) or "default",
        "degrade_text_chain_profile": _clean_text(merged.get("degrade_text_chain_profile")) or _clean_text(merged.get("text_chain_profile")) or "default",
        "text_chain_profiles": json.loads(json.dumps(doc.get("text_chain_profiles") or DEFAULT_QUOTA_POLICY["text_chain_profiles"])),
    }
