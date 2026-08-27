from __future__ import annotations

import ast
import json
import socket
from pathlib import Path
from typing import Any

import pytest
import requests
from fastapi import HTTPException


_FORBIDDEN_PUBLIC_FIELDS = {
    "api_key",
    "api_keys",
    "secret",
    "token",
    "authorization",
    "prompt",
    "raw",
    "url",
    "headers",
    "fingerprint",
    "identity",
}


def _forbid_external_io(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("offline provider status endpoint attempted SDK or network I/O")


def _install_external_io_traps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "create_connection", _forbid_external_io)
    monkeypatch.setattr(socket.socket, "connect", _forbid_external_io)
    monkeypatch.setattr(requests.sessions.Session, "request", _forbid_external_io)

    from backend.zhifei_autoplan.provider_admission import ProviderAdmissionManager
    from backend.zhifei_autoplan.utils.llm_client import LLMClient

    monkeypatch.setattr(LLMClient, "__init__", _forbid_external_io)
    monkeypatch.setattr(ProviderAdmissionManager, "admit", _forbid_external_io)
    monkeypatch.setattr(ProviderAdmissionManager, "admit_chain", _forbid_external_io)


def _normalise_field_name(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _assert_public_payload_is_redacted(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = _normalise_field_name(raw_key)
            key_parts = set(key.split("_"))
            assert key not in _FORBIDDEN_PUBLIC_FIELDS, f"forbidden field at {path}.{raw_key}"
            assert not ({"api", "key"} <= key_parts), f"API key field at {path}.{raw_key}"
            assert not ({"api", "keys"} <= key_parts), f"API keys field at {path}.{raw_key}"
            for marker in _FORBIDDEN_PUBLIC_FIELDS - {"api_key", "api_keys"}:
                assert marker not in key_parts, f"forbidden field at {path}.{raw_key}"
            _assert_public_payload_is_redacted(child, path=f"{path}.{raw_key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_public_payload_is_redacted(child, path=f"{path}[{index}]")


def test_health_and_model_health_are_offline_and_do_not_create_admission_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from backend.app import main
    from backend.zhifei_autoplan import job_store, local_job_queue

    state_dir = tmp_path / "provider-admission"
    monkeypatch.setenv("ZF_PROVIDER_ADMISSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("ZF_LLM_MAIN_PROVIDER", "openai")
    monkeypatch.setenv("ZF_LLM_MAIN_MODEL", "gpt-contract-test")
    monkeypatch.setenv("ZF_LLM_MAIN_API_KEY", "contract-test-provider-credential")
    monkeypatch.setenv("ANTHROPIC_DOCUMENT_RENDER_API_KEY", "contract-test-render-credential")
    monkeypatch.setenv("ANTHROPIC_DOCUMENT_RENDER_MODEL", "claude-contract-test")
    monkeypatch.setattr(job_store, "job_runtime_counts", lambda stale_after_seconds=60: {})
    monkeypatch.setattr(local_job_queue, "local_queue_snapshot", lambda: {})
    _install_external_io_traps(monkeypatch)

    health = main.health()
    model_health = main.model_health()

    assert health["ok"] is True
    assert model_health["ok"] is True
    assert health["provider_admission"]["generation_allowed"] is False
    assert model_health["generation_allowed"] is False
    assert not state_dir.exists(), "read-only health checks must not create admission state"


def test_model_ping_is_permanently_retired_with_410_and_no_external_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app import main

    _install_external_io_traps(monkeypatch)

    with pytest.raises(HTTPException) as caught:
        main.model_ping()

    assert caught.value.status_code == 410
    assert caught.value.detail == {
        "code": "MODEL_PING_RETIRED",
        "message": "无上下文模型探测已停用；系统只在项目证据门通过后执行供应商准入。",
    }


def test_provider_admission_requires_actions_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.setenv("ZF_ACTIONS_KEY", "provider-admission-contract-key")

    for supplied in (None, "", "wrong-key"):
        with pytest.raises(HTTPException) as caught:
            actions_bridge.actions_provider_admission(supplied)
        assert caught.value.status_code == 401


def test_provider_admission_public_response_is_recursively_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import provider_admission, provider_runtime

    monkeypatch.setenv("ZF_ACTIONS_KEY", "provider-admission-contract-key")
    monkeypatch.setattr(provider_runtime, "build_server_provider_admission_candidates", lambda: [])
    monkeypatch.setattr(provider_runtime, "server_provider_admission_required_roles", lambda _items: ["text_draft"])
    monkeypatch.setattr(
        provider_admission,
        "evaluate_latest_snapshot",
        lambda *_args, **_kwargs: {
            "schema_version": "provider-admission-v1",
            "status": "admitted",
            "required_roles": ["text_draft"],
            "slots": [
                {
                    "slot": "text_main",
                    "role": "text_draft",
                    "provider": "openai",
                    "model": "gpt-contract-test",
                    "credential_fingerprint": "fingerprint-sentinel",
                    "identity_digest": "identity-sentinel",
                    "api_key": "api-key-sentinel",
                    "admitted": True,
                    "layers": {
                        name: {"status": "pass", "code": "probe_passed"}
                        for name in (
                            "configuration",
                            "credentials",
                            "model",
                            "quota",
                            "stream",
                            "circuit",
                        )
                    },
                    "reason_codes": [],
                    "checked_at": 1.0,
                    "expires_at": 2.0,
                }
            ],
            "admitted_chain": [
                {
                    "slot": "text_main",
                    "provider": "openai",
                    "model": "gpt-contract-test",
                    "credential_fingerprint": "fingerprint-sentinel",
                    "identity_digest": "identity-sentinel",
                }
            ],
            "generation_allowed": True,
            "degraded": False,
            "api_keys": {"main": "api-keys-sentinel"},
            "secret": "secret-sentinel",
            "token": "token-sentinel",
            "authorization": "authorization-sentinel",
            "prompt": "prompt-sentinel",
            "raw": "raw-sentinel",
            "url": "url-sentinel",
            "headers": {"x-secret": "headers-sentinel"},
        },
    )
    _install_external_io_traps(monkeypatch)

    response = actions_bridge.actions_provider_admission("provider-admission-contract-key")

    assert response["ok"] is True
    assert response["admission"]["generation_allowed"] is True
    _assert_public_payload_is_redacted(response)
    encoded = json.dumps(response, ensure_ascii=False, sort_keys=True)
    for sentinel in (
        "fingerprint-sentinel",
        "identity-sentinel",
        "api-key-sentinel",
        "api-keys-sentinel",
        "secret-sentinel",
        "token-sentinel",
        "authorization-sentinel",
        "prompt-sentinel",
        "raw-sentinel",
        "url-sentinel",
        "headers-sentinel",
    ):
        assert sentinel not in encoded


def test_streamlit_source_cannot_read_or_send_model_credentials_and_shows_admission() -> None:
    source_path = Path(__file__).resolve().parents[2] / "app.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    string_literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not any("API_KEY" in literal.upper() for literal in string_literals)
    assert string_literals.isdisjoint({"provider_chain", "api_key", "api_keys"})

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"text_input", "text_area"}:
            continue
        widget_literals = {
            child.value.lower()
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }
        widget_text = " ".join(widget_literals)
        assert "api_key" not in widget_text
        assert "api key" not in widget_text
        assert "模型密钥" not in widget_text
        assert "供应商密钥" not in widget_text
        assert not any(
            keyword.arg == "type" and isinstance(keyword.value, ast.Constant) and keyword.value.value == "password"
            for keyword in node.keywords
        )

    assert "/actions/provider_admission" in source
    assert "供应商准入" in source
    assert "前端不能覆盖" in source
    assert "页面不读取、显示或传输密钥" in source
    assert "IMAGE_PROVIDER_ADMISSION_REQUIRED" in source
    assert "文本/文档模型准入不代表图片模型已准入" in source
