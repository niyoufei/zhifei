from __future__ import annotations

import copy
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from backend.zhifei_autoplan.model_aliases import latest_runtime_model_for
from backend.zhifei_autoplan.quota_policy import load_quota_policy


@dataclass(frozen=True)
class ProviderSlot:
    slot: str
    role: str
    provider: str
    model: str
    api_key: str
    key_alias: str

    def as_payload(self) -> Dict[str, str]:
        return {
            "slot": self.slot,
            "provider": self.provider,
            "model": self.model,
            "key_alias": self.key_alias,
        }


def _env_first(*names: str) -> str:
    for name in names:
        raw = os.environ.get(str(name or "").strip())
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


def _text_model_main() -> str:
    return (
        _env_first("OPENAI_TEXT_MODEL_MAIN", "ZF_OPENAI_TEXT_MODEL_ID")
        or latest_runtime_model_for("openai")
        or "gpt-5.4"
    )


def _text_model_backup() -> str:
    return _env_first("OPENAI_TEXT_MODEL_BACKUP", "OPENAI_TEXT_MODEL_MAIN", "ZF_OPENAI_TEXT_MODEL_ID") or _text_model_main()


def _automation_model() -> str:
    return _env_first("OPENAI_AUTOMATION_MODEL", "OPENAI_TEXT_MODEL_MAIN", "ZF_OPENAI_TEXT_MODEL_ID") or _text_model_main()


def _gemini_text_model() -> str:
    return (
        _env_first("GEMINI_TEXT_MODEL", "ZF_GOOGLE_TEXT_MODEL_ID")
        or latest_runtime_model_for("google")
        or "gemini-3.1-pro-preview"
    )


def _gemini_image_model() -> str:
    return _env_first("GEMINI_IMAGE_MODEL_A", "ZF_GEMINI_IMAGE_MODEL", "ZF_GOOGLE_IMAGE_MODEL") or "gemini-2.5-flash-image"


def _gemini_image_model_backup() -> str:
    return _env_first("GEMINI_IMAGE_MODEL_B", "GEMINI_IMAGE_MODEL_A", "ZF_GEMINI_IMAGE_MODEL", "ZF_GOOGLE_IMAGE_MODEL") or _gemini_image_model()


def resolve_text_slots() -> List[ProviderSlot]:
    slots: List[ProviderSlot] = []

    main_key = _env_first(
        "OPENAI_API_KEY_TEXT_MAIN",
        "ZF_LLM_MAIN_API_KEY",
        "OPENAI_API_KEY",
        "ZF_OPENAI_API_KEY",
    )
    if main_key:
        slots.append(
            ProviderSlot(
                slot="text_main",
                role="text_main",
                provider="openai",
                model=_text_model_main(),
                api_key=main_key,
                key_alias="OPENAI_API_KEY_TEXT_MAIN",
            )
        )

    backup_key = _env_first("OPENAI_API_KEY_TEXT_BACKUP", "ZF_LLM_FALLBACK1_API_KEY")
    if backup_key:
        slots.append(
            ProviderSlot(
                slot="text_backup",
                role="text_backup",
                provider="openai",
                model=_text_model_backup(),
                api_key=backup_key,
                key_alias="OPENAI_API_KEY_TEXT_BACKUP",
            )
        )

    if _env_bool("ZF_ENABLE_GEMINI_TEXT_FALLBACK", default=False):
        gemini_key = _env_first("GEMINI_API_KEY_A", "ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
        if gemini_key:
            slots.append(
                ProviderSlot(
                    slot="text_compat_google",
                    role="text_compat_google",
                    provider="google",
                    model=_gemini_text_model(),
                    api_key=gemini_key,
                    key_alias="GEMINI_API_KEY_A",
                )
            )
    return slots


def resolve_automation_slot() -> ProviderSlot | None:
    api_key = _env_first("OPENAI_API_KEY_AUTOMATION")
    if not api_key:
        return None
    return ProviderSlot(
        slot="automation",
        role="automation",
        provider="openai",
        model=_automation_model(),
        api_key=api_key,
        key_alias="OPENAI_API_KEY_AUTOMATION",
    )


def resolve_image_slots() -> List[ProviderSlot]:
    slots: List[ProviderSlot] = []
    primary = _env_first("GEMINI_API_KEY_A", "ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
    if primary:
        slots.append(
            ProviderSlot(
                slot="image_main",
                role="image_main",
                provider="google",
                model=_gemini_image_model(),
                api_key=primary,
                key_alias="GEMINI_API_KEY_A",
            )
        )
    backup = _env_first("GEMINI_API_KEY_B")
    if backup:
        slots.append(
            ProviderSlot(
                slot="image_backup",
                role="image_backup",
                provider="google",
                model=_gemini_image_model_backup(),
                api_key=backup,
                key_alias="GEMINI_API_KEY_B",
            )
        )
    return slots


def build_server_text_payload_chain() -> List[Dict[str, str]]:
    return [slot.as_payload() for slot in build_server_text_slots()]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def resolve_text_chain_profiles() -> Dict[str, List[str]]:
    try:
        doc = load_quota_policy()
    except Exception:
        doc = {}
    raw = doc.get("text_chain_profiles") if isinstance(doc.get("text_chain_profiles"), dict) else {}
    normalized: Dict[str, List[str]] = {}
    for name, profile in raw.items():
        key = _clean_text(name)
        if not key or not isinstance(profile, dict):
            continue
        order_raw = profile.get("slot_order")
        if not isinstance(order_raw, list):
            continue
        order = []
        seen: set[str] = set()
        for item in order_raw:
            slot = _clean_text(item)
            if not slot or slot in seen:
                continue
            seen.add(slot)
            order.append(slot)
        if order:
            normalized[key] = order
    if not normalized:
        normalized = {
            "default": ["text_main", "text_backup", "text_compat_google"],
            "cost_guard": ["text_backup", "text_compat_google", "text_main"],
        }
    return normalized


def build_server_text_slots(*, profile: str | None = None) -> List[ProviderSlot]:
    slots = resolve_text_slots()
    if not slots:
        return []
    slot_map = {slot.slot: slot for slot in slots}
    profiles = resolve_text_chain_profiles()
    profile_name = _clean_text(profile) or "default"
    order = profiles.get(profile_name) or profiles.get("default") or []
    ordered: List[ProviderSlot] = []
    seen: set[str] = set()
    for slot_name in order:
        slot = slot_map.get(slot_name)
        if slot is None or slot.slot in seen:
            continue
        seen.add(slot.slot)
        ordered.append(slot)
    for slot in slots:
        if slot.slot in seen:
            continue
        seen.add(slot.slot)
        ordered.append(slot)
    return ordered


def apply_server_provider_routing(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(payload if isinstance(payload, dict) else {})
    text_chain_profile = _clean_text(out.get("text_chain_profile")) or "default"
    chain = [slot.as_payload() for slot in build_server_text_slots(profile=text_chain_profile)]
    out.pop("api_key", None)
    out.pop("api_keys", None)
    out.pop("image_api_key", None)
    out.pop("providers", None)
    out.pop("model_map", None)
    out.pop("provider_chain", None)
    if not chain:
        if bool(out.get("dry_run", False)):
            out["provider_chain"] = []
            out["text_chain_profile"] = text_chain_profile
            out["_server_provider_roles"] = {
                "text_chain": [],
                "text_chain_profile": text_chain_profile,
                "automation": bool(resolve_automation_slot()),
                "image_chain": [f"{item.slot}:{item.provider}/{item.model}" for item in resolve_image_slots()],
                "resolved_at": int(time.time()),
                "routing_mode": "dry_run_no_text_chain",
            }
            return out
        raise RuntimeError(
            "text_provider_not_configured: missing OPENAI_API_KEY_TEXT_MAIN/OPENAI_API_KEY or compatible environment variables"
        )
    out["provider_chain"] = chain
    out["provider"] = str(chain[0]["provider"])
    out["model"] = str(chain[0]["model"])
    out["text_chain_profile"] = text_chain_profile
    out["_server_provider_roles"] = {
        "text_chain": [f"{item['slot']}:{item['provider']}/{item['model']}" for item in chain],
        "text_chain_profile": text_chain_profile,
        "automation": bool(resolve_automation_slot()),
        "image_chain": [f"{item.slot}:{item.provider}/{item.model}" for item in resolve_image_slots()],
        "resolved_at": int(time.time()),
    }
    return out


def resolve_text_slot_credentials(slot_id: str | None, provider: str | None) -> tuple[str | None, str | None]:
    normalized_slot = str(slot_id or "").strip().lower()
    normalized_provider = str(provider or "").strip().lower()
    for slot in resolve_text_slots():
        if normalized_slot and slot.slot == normalized_slot:
            return slot.api_key, slot.key_alias
    if normalized_provider == "openai":
        main = next((slot for slot in resolve_text_slots() if slot.provider == "openai"), None)
        if main:
            return main.api_key, main.key_alias
    if normalized_provider == "google":
        compat = next((slot for slot in resolve_text_slots() if slot.provider == "google"), None)
        if compat:
            return compat.api_key, compat.key_alias
    return None, None


def resolve_automation_credentials() -> tuple[str | None, str | None, str | None]:
    slot = resolve_automation_slot()
    if not slot:
        return None, None, None
    return slot.provider, slot.model, slot.api_key


def resolve_image_slot_credentials(slot_id: str | None = None) -> tuple[str | None, str | None, str | None, str | None]:
    slots = resolve_image_slots()
    if not slots:
        return None, None, None, None
    normalized_slot = str(slot_id or "").strip().lower()
    if normalized_slot:
        for slot in slots:
            if slot.slot == normalized_slot:
                return slot.provider, slot.model, slot.api_key, slot.key_alias
    first = slots[0]
    return first.provider, first.model, first.api_key, first.key_alias


def iterate_image_failover_slots() -> List[ProviderSlot]:
    return resolve_image_slots()


def frontend_provider_status() -> Dict[str, Dict[str, Any]]:
    text_slots = resolve_text_slots()
    image_slots = resolve_image_slots()
    automation = resolve_automation_slot()
    return {
        "text_main": {
            "configured": any(slot.role == "text_main" for slot in text_slots),
            "env": "OPENAI_API_KEY_TEXT_MAIN",
            "model": _text_model_main(),
        },
        "text_backup": {
            "configured": any(slot.role == "text_backup" for slot in text_slots),
            "env": "OPENAI_API_KEY_TEXT_BACKUP",
            "model": _text_model_backup(),
        },
        "automation": {
            "configured": automation is not None,
            "env": "OPENAI_API_KEY_AUTOMATION",
            "model": _automation_model(),
        },
        "gemini_a": {
            "configured": any(slot.key_alias == "GEMINI_API_KEY_A" for slot in image_slots),
            "env": "GEMINI_API_KEY_A",
            "model": _gemini_image_model(),
        },
        "gemini_b": {
            "configured": any(slot.key_alias == "GEMINI_API_KEY_B" for slot in image_slots),
            "env": "GEMINI_API_KEY_B",
            "model": _gemini_image_model_backup(),
        },
    }
