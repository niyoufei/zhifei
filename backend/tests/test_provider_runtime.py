from __future__ import annotations

import pytest

from backend.zhifei_autoplan.provider_runtime import (
    apply_server_provider_routing,
    resolve_automation_credentials,
    resolve_document_render_slot,
    resolve_image_slots,
    resolve_provider_slot_credentials,
    resolve_text_slots,
)


@pytest.fixture(autouse=True)
def _isolate_provider_environment(monkeypatch) -> None:
    for name in (
        "ZF_LLM_MAIN_PROVIDER",
        "ZF_LLM_MAIN_MODEL",
        "ZF_LLM_MAIN_API_KEY",
        "ZF_LLM_FALLBACK1_PROVIDER",
        "ZF_LLM_FALLBACK1_MODEL",
        "ZF_LLM_FALLBACK1_API_KEY",
        "ANTHROPIC_TEXT_MODEL_MAIN",
        "ANTHROPIC_TEXT_MODEL_DRAFT",
        "ANTHROPIC_TEXT_MODEL_REVIEW",
        "ANTHROPIC_TEXT_MODEL_ESCALATION",
        "ANTHROPIC_DOCUMENT_RENDER_MODEL",
        "ZF_ANTHROPIC_DOCUMENT_RENDER_MODEL",
        "ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ZF_ANTHROPIC_DOCUMENT_RENDER_API_KEY",
        "ANTHROPIC_API_KEY",
        "ZF_ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ZF_OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


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
        "image_api_key": "client-image-secret",
        "base_url": "https://unreviewed.example.invalid/v1",
        "secret_key": "client-secret-key",
        "token_url": "https://unreviewed.example.invalid/token",
    }

    prepared = apply_server_provider_routing(payload)

    assert "api_key" not in prepared
    assert "api_keys" not in prepared
    assert "image_api_key" not in prepared
    assert "base_url" not in prepared
    assert "secret_key" not in prepared
    assert "token_url" not in prepared
    assert prepared["_server_provider_routing_enforced"] is True
    assert prepared["_provider_admission_required"] is True
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
    assert prepared["_server_provider_roles"]["routing_mode"] == "server_allowlist"
    assert prepared["_provider_admission_required_roles"] == [
        "text_draft",
        "document_render",
    ]
    assert prepared["_provider_admission_extra_slots"] == []


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


def test_chapter_validation_does_not_admit_unused_document_renderer(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    prepared = apply_server_provider_routing(
        {
            "topic": "章节真实模型验证",
            "delivery_scope": "chapter_validation",
        }
    )

    assert prepared["delivery_scope"] == "chapter_validation"
    assert prepared["_provider_admission_extra_slots"] == []
    assert prepared["_provider_admission_required_roles"] == [
        "text_draft",
        "text_review",
    ]
    assert "document_render" not in prepared["_provider_admission_required_roles"]


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
    assert prepared["_provider_admission_required"] is False


def test_resolve_text_slots_optional_google_text_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "main-secret")
    monkeypatch.setenv("ZF_ENABLE_GEMINI_TEXT_FALLBACK", "1")
    monkeypatch.setenv("GEMINI_API_KEY_A", "gemini-secret")

    slots = resolve_text_slots()
    providers = [slot.provider for slot in slots]
    aliases = [slot.key_alias for slot in slots]

    assert providers == ["openai", "google"]
    assert aliases == ["OPENAI_API_KEY_TEXT_MAIN", "GEMINI_API_KEY_A"]


def test_resolve_text_slots_supports_google_main_without_enabling_exhausted_openai(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "google")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("GOOGLE_API_KEY", "gemini-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.delenv("ZF_LLM_FALLBACK1_PROVIDER", raising=False)

    slots = resolve_text_slots()

    assert [(slot.slot, slot.provider, slot.model) for slot in slots] == [
        ("text_main", "google", "gemini-2.5-pro")
    ]


def test_resolve_text_slots_uses_anthropic_main_and_openai_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "anthropic")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", "claude-opus-5")
    monkeypatch.setenv("ANTHROPIC_TEXT_MODEL_DRAFT", "claude-sonnet-5")
    monkeypatch.setenv("ANTHROPIC_TEXT_MODEL_REVIEW", "claude-opus-5")
    monkeypatch.setenv("ANTHROPIC_TEXT_MODEL_ESCALATION", "claude-fable-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("ZF_LLM_FALLBACK1_PROVIDER", "openai")
    monkeypatch.setenv("ZF_LLM_FALLBACK1_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    slots = resolve_text_slots()

    assert [(slot.slot, slot.provider, slot.model, slot.key_alias) for slot in slots] == [
        ("text_draft", "anthropic", "claude-sonnet-5", "ANTHROPIC_API_KEY"),
        ("text_review", "anthropic", "claude-opus-5", "ANTHROPIC_API_KEY"),
        ("text_escalation", "anthropic", "claude-fable-5", "ANTHROPIC_API_KEY"),
        ("text_backup", "openai", "gpt-5.6-sol", "OPENAI_API_KEY"),
    ]


def test_resolve_text_slots_keeps_openai_fallback_when_anthropic_key_missing(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "anthropic")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", "claude-opus-5")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ZF_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ZF_LLM_MAIN_API_KEY", raising=False)
    monkeypatch.setenv("ZF_LLM_FALLBACK1_PROVIDER", "openai")
    monkeypatch.setenv("ZF_LLM_FALLBACK1_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    slots = resolve_text_slots()

    assert [(slot.slot, slot.provider) for slot in slots] == [("text_backup", "openai")]


def test_resolve_document_render_slot_isolated_sonnet_model(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("ANTHROPIC_DOCUMENT_RENDER_MODEL", "claude-sonnet-5")
    monkeypatch.setenv("ANTHROPIC_TEXT_MODEL_MAIN", "claude-opus-5")

    slot = resolve_document_render_slot()

    assert slot is not None
    assert (slot.slot, slot.role, slot.provider, slot.model) == (
        "document_render",
        "document_render",
        "anthropic",
        "claude-sonnet-5",
    )
    assert slot.api_key == "anthropic-secret"


def test_resolve_document_render_slot_has_no_cross_provider_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    assert resolve_document_render_slot() is None


def test_operation_specific_admission_does_not_require_unused_renderer(monkeypatch) -> None:
    from backend.zhifei_autoplan.provider_runtime import (
        build_server_provider_admission_candidates,
        server_provider_admission_required_roles,
    )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "server-anthropic-key")
    candidates = build_server_provider_admission_candidates()

    roles = server_provider_admission_required_roles(
        candidates,
        require_document_render=False,
    )

    assert "text_draft" in roles
    assert "document_render" not in roles


def test_apply_server_provider_routing_orders_anthropic_tiered_chain(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "anthropic")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", "claude-opus-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("ZF_LLM_FALLBACK1_PROVIDER", "openai")
    monkeypatch.setenv("ZF_LLM_FALLBACK1_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    prepared = apply_server_provider_routing({"topic": "分级模型路由"})

    assert prepared["provider"] == "anthropic"
    assert prepared["model"] == "claude-sonnet-5"
    assert [item["slot"] for item in prepared["provider_chain"]] == [
        "text_draft",
        "text_review",
        "text_backup",
        "text_escalation",
    ]
    assert prepared["_provider_admission_extra_slots"] == [
        {
            "slot": "document_render",
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "key_alias": "ANTHROPIC_API_KEY",
        }
    ]
    assert prepared["_provider_admission_required_roles"] == [
        "text_draft",
        "text_review",
        "document_render",
    ]


def test_resolve_provider_slot_credentials_keeps_secret_server_side(monkeypatch) -> None:
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("OPENAI_API_KEY_TEXT_BACKUP", "backup-secret")

    text_key, text_alias = resolve_provider_slot_credentials("text_draft", "anthropic")
    render_key, render_alias = resolve_provider_slot_credentials("document_render", "anthropic")

    assert (text_key, text_alias) == ("anthropic-secret", "ANTHROPIC_API_KEY")
    assert (render_key, render_alias) == ("anthropic-secret", "ANTHROPIC_API_KEY")


def test_resolve_image_slots_uses_openai_then_google(monkeypatch) -> None:
    monkeypatch.setenv("ZF_IMAGE_MAIN_PROVIDER", "openai")
    monkeypatch.setenv("ZF_IMAGE_MAIN_MODEL", "gpt-image-2")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ZF_IMAGE_FALLBACK1_PROVIDER", "google")
    monkeypatch.setenv("ZF_IMAGE_FALLBACK1_MODEL", "gemini-3-pro-image")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret")

    slots = resolve_image_slots()

    assert [(slot.slot, slot.provider, slot.model) for slot in slots] == [
        ("image_main", "openai", "gpt-image-2"),
        ("image_backup", "google", "gemini-3-pro-image"),
    ]


def test_resolve_automation_credentials(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY_AUTOMATION", "automation-secret")
    monkeypatch.setenv("OPENAI_AUTOMATION_MODEL", "gpt-5.4")

    provider, model, api_key = resolve_automation_credentials()

    assert provider == "openai"
    assert model == "gpt-5.4"
    assert api_key == "automation-secret"
