from __future__ import annotations

import copy
import os
import time
from dataclasses import dataclass
from typing import Any

from backend.zhifei_autoplan.model_aliases import latest_runtime_model_for


class ProviderRoutingConfigurationError(RuntimeError):
    code = "MODEL_PROVIDER_CONFIGURATION_BLOCKED"


@dataclass(frozen=True)
class ProviderSlot:
    slot: str
    role: str
    provider: str
    model: str
    api_key: str
    key_alias: str

    def as_payload(self) -> dict[str, str]:
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
        or "gpt-5.6-sol"
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


def _anthropic_text_model() -> str:
    return (
        _env_first("ANTHROPIC_TEXT_MODEL_MAIN", "ZF_ANTHROPIC_TEXT_MODEL_ID")
        or latest_runtime_model_for("anthropic")
        or "claude-opus-5"
    )


def _anthropic_draft_model() -> str:
    return _env_first("ANTHROPIC_TEXT_MODEL_DRAFT", "ZF_ANTHROPIC_DRAFT_MODEL") or "claude-sonnet-5"


def _anthropic_document_render_model() -> str:
    """Return the dedicated professional-document editor model.

    This is deliberately separate from the normal drafting/review chain.  A
    document may therefore be generated with one routing policy and later be
    professionally refined without silently changing the generation model.
    """

    return (
        _env_first(
            "ANTHROPIC_DOCUMENT_RENDER_MODEL",
            "ZF_ANTHROPIC_DOCUMENT_RENDER_MODEL",
            "ANTHROPIC_TEXT_MODEL_DRAFT",
            "ZF_ANTHROPIC_DRAFT_MODEL",
        )
        or "claude-sonnet-5"
    )


def _anthropic_review_model() -> str:
    return _env_first("ANTHROPIC_TEXT_MODEL_REVIEW", "ZF_ANTHROPIC_REVIEW_MODEL") or "claude-opus-5"


def _anthropic_escalation_model() -> str:
    return _env_first("ANTHROPIC_TEXT_MODEL_ESCALATION", "ZF_ANTHROPIC_ESCALATION_MODEL") or "claude-fable-5"


def _provider_text_model(provider: str, *, fallback: bool = False) -> str:
    normalized = str(provider or "").strip().lower()
    configured = _env_first("ZF_LLM_FALLBACK1_MODEL" if fallback else "ZF_LLM_MAIN_MODEL")
    if configured:
        return configured
    if normalized == "anthropic":
        return _anthropic_text_model()
    if normalized == "google":
        return _gemini_text_model()
    if normalized == "openai":
        return _text_model_backup() if fallback else _text_model_main()
    return latest_runtime_model_for(normalized)


def _provider_text_key(provider: str, *, fallback: bool = False) -> tuple[str, str]:
    normalized = str(provider or "").strip().lower()
    scoped = "ZF_LLM_FALLBACK1_API_KEY" if fallback else "ZF_LLM_MAIN_API_KEY"
    if normalized == "anthropic":
        return _env_first(scoped, "ANTHROPIC_API_KEY", "ZF_ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY"
    if normalized == "google":
        return (
            _env_first(scoped, "GEMINI_API_KEY_A", "ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
            "GOOGLE_API_KEY",
        )
    if normalized == "openai":
        aliases = (
            scoped,
            "OPENAI_API_KEY_TEXT_BACKUP" if fallback else "OPENAI_API_KEY_TEXT_MAIN",
            "OPENAI_API_KEY",
            "ZF_OPENAI_API_KEY",
        )
        return _env_first(*aliases), "OPENAI_API_KEY"
    upper = normalized.upper()
    return _env_first(scoped, f"{upper}_API_KEY", f"ZF_{upper}_API_KEY"), f"{upper}_API_KEY"


def _gemini_image_model() -> str:
    return _env_first("GEMINI_IMAGE_MODEL_A", "ZF_GEMINI_IMAGE_MODEL", "ZF_GOOGLE_IMAGE_MODEL") or "gemini-3-pro-image"


def _gemini_image_model_backup() -> str:
    return _env_first("GEMINI_IMAGE_MODEL_B", "GEMINI_IMAGE_MODEL_A", "ZF_GEMINI_IMAGE_MODEL", "ZF_GOOGLE_IMAGE_MODEL") or _gemini_image_model()


def resolve_text_slots() -> list[ProviderSlot]:
    slots: list[ProviderSlot] = []

    configured_main_provider = _env_first("ZF_LLM_MAIN_PROVIDER").lower()
    if configured_main_provider:
        main_key, main_alias = _provider_text_key(configured_main_provider)
        if configured_main_provider == "anthropic" and main_key:
            slots.append(
                ProviderSlot(
                    slot="text_draft",
                    role="text_draft",
                    provider="anthropic",
                    model=_anthropic_draft_model(),
                    api_key=main_key,
                    key_alias=main_alias,
                )
            )
            slots.append(
                ProviderSlot(
                    slot="text_review",
                    role="text_review",
                    provider="anthropic",
                    model=_anthropic_review_model(),
                    api_key=main_key,
                    key_alias=main_alias,
                )
            )
            slots.append(
                ProviderSlot(
                    slot="text_escalation",
                    role="text_escalation",
                    provider="anthropic",
                    model=_anthropic_escalation_model(),
                    api_key=main_key,
                    key_alias=main_alias,
                )
            )
        else:
            main_model = _provider_text_model(configured_main_provider)
            if main_key and main_model:
                slots.append(
                    ProviderSlot(
                        slot="text_main",
                        role="text_main",
                        provider=configured_main_provider,
                        model=main_model,
                        api_key=main_key,
                        key_alias=main_alias,
                    )
                )

        configured_backup_provider = _env_first("ZF_LLM_FALLBACK1_PROVIDER").lower()
        if configured_backup_provider:
            backup_key, backup_alias = _provider_text_key(configured_backup_provider, fallback=True)
            backup_model = _provider_text_model(configured_backup_provider, fallback=True)
            if backup_key and backup_model:
                slots.append(
                    ProviderSlot(
                        slot="text_backup",
                        role="text_backup",
                        provider=configured_backup_provider,
                        model=backup_model,
                        api_key=backup_key,
                        key_alias=backup_alias,
                    )
                )
        return slots

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


def resolve_document_render_slot() -> ProviderSlot | None:
    """Resolve the isolated Anthropic slot used for Word professionalization.

    There is intentionally no cross-provider or cross-model fallback here: a
    button labelled Sonnet 5 must either use the configured Anthropic model or
    fail with an actionable configuration error.
    """

    api_key = _env_first(
        "ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ZF_ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ANTHROPIC_API_KEY",
        "ZF_ANTHROPIC_API_KEY",
        "ZF_LLM_MAIN_API_KEY",
    )
    if not api_key:
        return None
    return ProviderSlot(
        slot="document_render",
        role="document_render",
        provider="anthropic",
        model=_anthropic_document_render_model(),
        api_key=api_key,
        key_alias="ANTHROPIC_API_KEY",
    )


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


def resolve_image_slots() -> list[ProviderSlot]:
    slots: list[ProviderSlot] = []
    configured_main = _env_first("ZF_IMAGE_MAIN_PROVIDER").lower()
    if configured_main:
        if configured_main == "openai":
            primary = _env_first("ZF_IMAGE_MAIN_API_KEY", "OPENAI_IMAGE_API_KEY", "OPENAI_API_KEY", "ZF_OPENAI_API_KEY")
            model = _env_first("ZF_IMAGE_MAIN_MODEL", "OPENAI_IMAGE_MODEL") or "gpt-image-2"
            alias = "OPENAI_API_KEY"
        elif configured_main == "google":
            primary = _env_first("ZF_IMAGE_MAIN_API_KEY", "GEMINI_API_KEY_A", "ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
            model = _env_first("ZF_IMAGE_MAIN_MODEL") or _gemini_image_model()
            alias = "GOOGLE_API_KEY"
        else:
            primary = ""
            model = ""
            alias = ""
        if primary and model:
            slots.append(ProviderSlot("image_main", "image_main", configured_main, model, primary, alias))

        configured_backup = _env_first("ZF_IMAGE_FALLBACK1_PROVIDER").lower()
        if configured_backup == "google":
            backup = _env_first("ZF_IMAGE_FALLBACK1_API_KEY", "GEMINI_API_KEY_B", "GEMINI_API_KEY_A", "ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
            backup_model = _env_first("ZF_IMAGE_FALLBACK1_MODEL") or _gemini_image_model_backup()
            backup_alias = "GOOGLE_API_KEY"
        elif configured_backup == "openai":
            backup = _env_first("ZF_IMAGE_FALLBACK1_API_KEY", "OPENAI_IMAGE_API_KEY", "OPENAI_API_KEY", "ZF_OPENAI_API_KEY")
            backup_model = _env_first("ZF_IMAGE_FALLBACK1_MODEL", "OPENAI_IMAGE_MODEL") or "gpt-image-2"
            backup_alias = "OPENAI_API_KEY"
        else:
            backup = ""
            backup_model = ""
            backup_alias = ""
        if backup and backup_model:
            slots.append(ProviderSlot("image_backup", "image_backup", configured_backup, backup_model, backup, backup_alias))
        return slots

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


def build_server_text_payload_chain() -> list[dict[str, str]]:
    return [slot.as_payload() for slot in build_server_text_slots()]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _load_quota_policy() -> dict[str, Any]:
    try:
        from backend.zhifei_autoplan.quota_policy import load_quota_policy
    except ImportError:
        return {}
    try:
        doc = load_quota_policy()
    # Quota policy is optional configuration.  Syntax, storage, or adapter
    # failures fall back to the built-in provider ordering.
    except Exception:  # noqa: BLE001
        return {}
    return doc if isinstance(doc, dict) else {}


def resolve_text_chain_profiles() -> dict[str, list[str]]:
    doc = _load_quota_policy()
    raw = doc.get("text_chain_profiles") if isinstance(doc.get("text_chain_profiles"), dict) else {}
    normalized: dict[str, list[str]] = {}
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
            "default": [
                "text_draft",
                "text_review",
                "text_main",
                "text_backup",
                "text_escalation",
                "text_compat_google",
            ],
            "cost_guard": [
                "text_draft",
                "text_backup",
                "text_compat_google",
                "text_review",
                "text_escalation",
                "text_main",
            ],
        }
    return normalized


def build_server_text_slots(*, profile: str | None = None) -> list[ProviderSlot]:
    slots = resolve_text_slots()
    if not slots:
        return []
    slot_map = {slot.slot: slot for slot in slots}
    profiles = resolve_text_chain_profiles()
    profile_name = _clean_text(profile) or "default"
    order = profiles.get(profile_name) or profiles.get("default") or []
    ordered: list[ProviderSlot] = []
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


def apply_server_provider_routing(payload: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(payload if isinstance(payload, dict) else {})
    text_chain_profile = _clean_text(out.get("text_chain_profile")) or "default"
    chain = [slot.as_payload() for slot in build_server_text_slots(profile=text_chain_profile)]
    out.pop("api_key", None)
    out.pop("api_keys", None)
    out.pop("image_api_key", None)
    out.pop("providers", None)
    out.pop("model_map", None)
    out.pop("provider_chain", None)
    # Provider endpoints and credentials are server-owned.  Client-controlled
    # overrides would bypass admission and could route requests to an unreviewed
    # endpoint.
    out.pop("base_url", None)
    out.pop("secret_key", None)
    out.pop("token_url", None)
    out.pop("_provider_admitted_image_slots", None)
    out["_server_provider_routing_enforced"] = True
    out["_provider_admission_required"] = not bool(out.get("dry_run", False))
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
        raise ProviderRoutingConfigurationError(
            "text_provider_not_configured: no configured credential for the server-side primary or fallback text chain"
        )
    unsupported = sorted(
        {
            str(item.get("provider") or "").strip().lower()
            for item in chain
            if str(item.get("provider") or "").strip().lower()
            not in {"openai", "anthropic", "google"}
        }
    )
    if unsupported:
        raise ProviderRoutingConfigurationError(
            "text_provider_not_admission_capable: " + ",".join(unsupported)
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
        "routing_mode": "server_allowlist",
    }
    require_document_render = (
        str(out.get("delivery_scope") or "document").strip().lower()
        != "chapter_validation"
    )
    document_slot = resolve_document_render_slot() if require_document_render else None
    out["_provider_admission_extra_slots"] = (
        [document_slot.as_payload()] if document_slot is not None else []
    )
    # Independent review is a required role, not an optional enhancement.
    # Leaving it in the required set when no slot is configured makes provider
    # admission fail closed instead of silently turning a drafting model into
    # its own reviewer.
    required_roles = ["text_draft", "text_review"]
    if require_document_render:
        required_roles.append("document_render")
    out["_provider_admission_required_roles"] = required_roles
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
    if normalized_provider == "anthropic":
        main = next((slot for slot in resolve_text_slots() if slot.provider == "anthropic"), None)
        if main:
            return main.api_key, main.key_alias
    return None, None


def resolve_provider_slot_credentials(
    slot_id: str | None,
    provider: str | None,
) -> tuple[str | None, str | None]:
    """Resolve a server-owned credential without exposing it in route payloads."""

    normalized_slot = _clean_text(slot_id).lower()
    if normalized_slot == "document_render":
        slot = resolve_document_render_slot()
        if slot is not None:
            return slot.api_key, slot.key_alias
        return None, None
    return resolve_text_slot_credentials(normalized_slot, provider)


def build_server_provider_admission_candidates(
    *,
    profile: str | None = None,
    allow_fable_escalation: bool = False,
) -> list[Any]:
    """Return the current credential-bound route for offline admission checks.

    Credentials remain only on ephemeral ``ProviderCandidate`` objects. Callers
    must use the provider-admission public projection before serialization.
    """

    from backend.zhifei_autoplan.provider_admission import ProviderCandidate

    slots = [
        slot
        for slot in build_server_text_slots(profile=profile)
        if allow_fable_escalation or slot.role != "text_escalation"
    ]
    document_slot = resolve_document_render_slot()
    if document_slot is not None:
        slots.append(document_slot)
    candidates: list[ProviderCandidate] = []
    for slot in slots:
        stream_required = str(slot.role).startswith("text_")
        candidates.append(
            ProviderCandidate(
                slot=slot.slot,
                role=slot.role,
                provider=slot.provider,
                model=slot.model,
                credential=slot.api_key,
                key_alias=slot.key_alias,
                stream_required=stream_required,
                stream_supported=(
                    slot.provider in {"openai", "anthropic", "google"}
                    if stream_required
                    else True
                ),
            )
        )
    return candidates


def server_provider_admission_required_roles(
    candidates: list[Any] | None = None,
    *,
    require_review: bool = True,
    require_document_render: bool = True,
) -> list[str]:
    # Candidate presence is evaluated later by ``decide_required_roles``; this
    # function declares the invariant roles even when a role is absent.
    _ = candidates
    required = ["text_draft"]
    if require_review:
        required.append("text_review")
    if require_document_render:
        required.append("document_render")
    return required


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


def iterate_image_failover_slots() -> list[ProviderSlot]:
    return resolve_image_slots()


def frontend_provider_status() -> dict[str, dict[str, Any]]:
    text_slots = resolve_text_slots()
    image_slots = resolve_image_slots()
    automation = resolve_automation_slot()
    text_main_slot = next(
        (slot for slot in text_slots if slot.role in {"text_review", "text_main"}),
        None,
    )
    return {
        "text_main": {
            "configured": text_main_slot is not None,
            "env": text_main_slot.key_alias if text_main_slot else "ZF_LLM_MAIN_API_KEY",
            "model": text_main_slot.model if text_main_slot else _provider_text_model(_env_first("ZF_LLM_MAIN_PROVIDER") or "openai"),
        },
        "text_draft": {
            "configured": any(slot.role == "text_draft" for slot in text_slots),
            "env": next((slot.key_alias for slot in text_slots if slot.role == "text_draft"), "ANTHROPIC_API_KEY"),
            "model": next((slot.model for slot in text_slots if slot.role == "text_draft"), _anthropic_draft_model()),
        },
        "text_review": {
            "configured": any(slot.role == "text_review" for slot in text_slots),
            "env": next((slot.key_alias for slot in text_slots if slot.role == "text_review"), "ANTHROPIC_API_KEY"),
            "model": next((slot.model for slot in text_slots if slot.role == "text_review"), _anthropic_review_model()),
        },
        "text_escalation": {
            "configured": any(slot.role == "text_escalation" for slot in text_slots),
            "env": next((slot.key_alias for slot in text_slots if slot.role == "text_escalation"), "ANTHROPIC_API_KEY"),
            "model": next((slot.model for slot in text_slots if slot.role == "text_escalation"), _anthropic_escalation_model()),
        },
        "text_backup": {
            "configured": any(slot.role == "text_backup" for slot in text_slots),
            "env": next((slot.key_alias for slot in text_slots if slot.role == "text_backup"), "ZF_LLM_FALLBACK1_API_KEY"),
            "model": next((slot.model for slot in text_slots if slot.role == "text_backup"), _provider_text_model(_env_first("ZF_LLM_FALLBACK1_PROVIDER") or "openai", fallback=True)),
        },
        "automation": {
            "configured": automation is not None,
            "env": "OPENAI_API_KEY_AUTOMATION",
            "model": _automation_model(),
        },
        "image_main": {
            "configured": any(slot.role == "image_main" for slot in image_slots),
            "env": next((slot.key_alias for slot in image_slots if slot.role == "image_main"), "ZF_IMAGE_MAIN_API_KEY"),
            "model": next((slot.model for slot in image_slots if slot.role == "image_main"), _env_first("ZF_IMAGE_MAIN_MODEL") or "gpt-image-2"),
        },
        "image_backup": {
            "configured": any(slot.role == "image_backup" for slot in image_slots),
            "env": next((slot.key_alias for slot in image_slots if slot.role == "image_backup"), "ZF_IMAGE_FALLBACK1_API_KEY"),
            "model": next((slot.model for slot in image_slots if slot.role == "image_backup"), _env_first("ZF_IMAGE_FALLBACK1_MODEL") or _gemini_image_model_backup()),
        },
    }
