from __future__ import annotations

import os
from typing import Tuple


_LATEST_RUNTIME_MODELS = {
    "google": str(os.environ.get("GEMINI_TEXT_MODEL") or os.environ.get("ZF_GOOGLE_TEXT_MODEL_ID") or "gemini-3.1-pro-preview").strip(),
    "openai": str(os.environ.get("OPENAI_TEXT_MODEL_MAIN") or os.environ.get("ZF_OPENAI_TEXT_MODEL_ID") or "gpt-5.6-sol").strip(),
    "anthropic": str(os.environ.get("ANTHROPIC_TEXT_MODEL_MAIN") or os.environ.get("ZF_ANTHROPIC_TEXT_MODEL_ID") or "claude-opus-5").strip(),
    "grok": str(os.environ.get("ZF_GROK_TEXT_MODEL_ID") or "grok-4-1-fast-reasoning").strip(),
}

_DISPLAY_MODEL_ALIASES = {
    ("google", "gemini3.1pro"): lambda: latest_runtime_model_for("google"),
    ("openai", "chatgpt-5.4"): lambda: latest_runtime_model_for("openai"),
    ("openai", "chatgpt-5.6"): lambda: latest_runtime_model_for("openai"),
    ("anthropic", "claude-latest"): lambda: latest_runtime_model_for("anthropic"),
}

_LEGACY_RUNTIME_ALIASES = {
    ("google", "gemini-3-pro-preview"): lambda: latest_runtime_model_for("google"),
    ("google", "gemini-2.5-flash"): lambda: latest_runtime_model_for("google"),
    ("google", "gemini-2.0-flash"): lambda: latest_runtime_model_for("google"),
    ("openai", "gpt-5.2-pro"): lambda: latest_runtime_model_for("openai"),
    ("openai", "gpt-5.4"): lambda: latest_runtime_model_for("openai"),
}


def latest_runtime_model_for(provider: str | None) -> str:
    return str(_LATEST_RUNTIME_MODELS.get(str(provider or "").strip().lower()) or "")


def normalize_provider_model_pair(
    provider: str | None,
    model: str | None,
    *,
    fallback: str = "",
) -> Tuple[str, str]:
    normalized_provider = str(provider or fallback or "").strip().lower()
    if not normalized_provider:
        return "", ""

    model_text = str(model or "").strip()
    latest = latest_runtime_model_for(normalized_provider)
    if not model_text:
        return normalized_provider, latest

    lowered = model_text.lower()
    alias_loader = _DISPLAY_MODEL_ALIASES.get((normalized_provider, lowered))
    if alias_loader is None:
        alias_loader = _LEGACY_RUNTIME_ALIASES.get((normalized_provider, lowered))
    if alias_loader is not None:
        resolved = str(alias_loader() or "").strip()
        if resolved:
            return normalized_provider, resolved

    if normalized_provider == "openai" and lowered.startswith("gemini"):
        return normalized_provider, latest
    if normalized_provider == "google" and (lowered.startswith("gpt") or lowered.startswith("chatgpt")):
        return normalized_provider, latest
    return normalized_provider, model_text
