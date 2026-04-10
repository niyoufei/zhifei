from __future__ import annotations

from backend.zhifei_autoplan.provider_runtime import (
    apply_server_provider_routing,
    resolve_automation_credentials,
    resolve_text_slots,
)


def test_apply_server_provider_routing_uses_env_text_chain(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "main-secret")
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_BACKUP", "backup-secret")
    monkeypatch.setenv("OPENAI_TEXT_MODEL_MAIN", "gpt-5.4")
    monkeypatch.setenv("OPENAI_TEXT_MODEL_BACKUP", "gpt-5.4-mini")

    payload = {
        "topic": "测试项目",
        "provider_chain": [
            {"slot": "main", "provider": "openai", "model": "client-model", "api_key": "client-secret"},
        ],
        "api_key": "client-secret",
        "api_keys": {"main": "client-secret"},
    }

    prepared = apply_server_provider_routing(payload)

    assert "api_key" not in prepared
    assert "api_keys" not in prepared
    assert prepared["provider"] == "openai"
    assert prepared["model"] == "gpt-5.4"
    assert prepared["provider_chain"] == [
        {
            "slot": "text_main",
            "provider": "openai",
            "model": "gpt-5.4",
            "key_alias": "OPENAI_API_KEY_TEXT_MAIN",
        },
        {
            "slot": "text_backup",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "key_alias": "OPENAI_API_KEY_TEXT_BACKUP",
        },
    ]
    assert prepared["text_chain_profile"] == "default"
    assert prepared["_server_provider_roles"]["text_chain_profile"] == "default"


def test_apply_server_provider_routing_uses_cost_guard_text_chain_profile(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "main-secret")
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_BACKUP", "backup-secret")
    monkeypatch.setenv("OPENAI_TEXT_MODEL_MAIN", "gpt-5.4")
    monkeypatch.setenv("OPENAI_TEXT_MODEL_BACKUP", "gpt-5.4-mini")

    prepared = apply_server_provider_routing(
        {
            "topic": "成本保护链",
            "text_chain_profile": "cost_guard",
        }
    )

    assert prepared["provider"] == "openai"
    assert prepared["model"] == "gpt-5.4-mini"
    assert prepared["text_chain_profile"] == "cost_guard"
    assert prepared["provider_chain"][0]["slot"] == "text_backup"
    assert prepared["provider_chain"][0]["model"] == "gpt-5.4-mini"
    assert prepared["provider_chain"][1]["slot"] == "text_main"


def test_apply_server_provider_routing_allows_dry_run_without_text_slots(monkeypatch) -> None:
    for key in (
        "OPENAI_API_KEY_TEXT_MAIN",
        "ZF_LLM_MAIN_API_KEY",
        "OPENAI_API_KEY",
        "ZF_OPENAI_API_KEY",
        "OPENAI_API_KEY_TEXT_BACKUP",
        "ZF_LLM_FALLBACK1_API_KEY",
        "GEMINI_API_KEY_A",
        "ZF_GOOGLE_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ZF_ENABLE_GEMINI_TEXT_FALLBACK", raising=False)

    prepared = apply_server_provider_routing(
        {
            "topic": "dry-run-providerless",
            "provider": "openai",
            "model": "gpt-5.4",
            "api_key": "client-secret",
            "dry_run": True,
        }
    )

    assert "api_key" not in prepared
    assert prepared["provider"] == "openai"
    assert prepared["model"] == "gpt-5.4"
    assert prepared["provider_chain"] == []
    assert prepared["text_chain_profile"] == "default"
    assert prepared["_server_provider_roles"]["routing_mode"] == "dry_run_no_text_chain"


def test_resolve_text_slots_optional_google_text_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "main-secret")
    monkeypatch.setenv("ZF_ENABLE_GEMINI_TEXT_FALLBACK", "1")
    monkeypatch.setenv("GEMINI_API_KEY_A", "gemini-secret")

    slots = resolve_text_slots()
    providers = [slot.provider for slot in slots]
    aliases = [slot.key_alias for slot in slots]

    assert providers == ["openai", "google"]
    assert aliases == ["OPENAI_API_KEY_TEXT_MAIN", "GEMINI_API_KEY_A"]


def test_resolve_automation_credentials(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_AUTOMATION", "automation-secret")
    monkeypatch.setenv("OPENAI_AUTOMATION_MODEL", "gpt-5.4")

    provider, model, api_key = resolve_automation_credentials()

    assert provider == "openai"
    assert model == "gpt-5.4"
    assert api_key == "automation-secret"
