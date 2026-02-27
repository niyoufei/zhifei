from __future__ import annotations

from backend.zhifei_autoplan.orchestrator import _resolve_provider_api_key


def test_resolve_provider_api_key_explicit_wins() -> None:
    payload = {
        "provider": "google",
        "api_key": "generic-key",
        "api_keys": {"google": "google-key"},
    }
    got = _resolve_provider_api_key(payload, "google", explicit_key="explicit-key")
    assert got == "explicit-key"


def test_resolve_provider_api_key_slot_then_provider() -> None:
    payload = {
        "provider": "google",
        "api_keys": {
            "slot_a": "slot-key",
            "google": "google-key",
        },
    }
    got_slot = _resolve_provider_api_key(payload, "google", slot_id="slot_a")
    got_provider = _resolve_provider_api_key(payload, "google", slot_id="slot_b")
    assert got_slot == "slot-key"
    assert got_provider == "google-key"


def test_resolve_provider_api_key_generic_only_when_provider_matches() -> None:
    payload = {
        "provider": "google",
        "api_key": "generic-google-key",
    }
    ok = _resolve_provider_api_key(payload, "google")
    mismatch = _resolve_provider_api_key(payload, "openai")
    assert ok == "generic-google-key"
    assert mismatch is None


def test_resolve_provider_api_key_generic_when_default_provider_missing() -> None:
    payload = {
        "api_key": "generic-key",
    }
    got = _resolve_provider_api_key(payload, "openai")
    assert got == "generic-key"
