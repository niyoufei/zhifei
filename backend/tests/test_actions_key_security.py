from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.app.routers import actions_bridge


def test_actions_auth_has_no_shared_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZF_ACTIONS_KEY", raising=False)

    with pytest.raises(HTTPException) as caught:
        actions_bridge._auth_actions_key("zf-webui-key")

    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "SYSTEM_ACTIONS_KEY_NOT_CONFIGURED"


def test_actions_auth_returns_stable_chinese_error_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZF_ACTIONS_KEY", "super-secret-actions-key")

    with pytest.raises(HTTPException) as caught:
        actions_bridge._auth_actions_key("wrong")

    assert caught.value.status_code == 401
    assert caught.value.detail["code"] == "SYSTEM_ACTIONS_KEY_INVALID"
    serialized = json.dumps(caught.value.detail, ensure_ascii=False)
    assert "super-secret-actions-key" not in serialized
    assert "系统内部操作凭据" in serialized


def test_frontend_and_dev_launcher_contain_no_shared_default_key() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sources = [
        (root / "app.py").read_text(encoding="utf-8"),
        (root / "scripts" / "run_web_ui.sh").read_text(encoding="utf-8"),
        (root / "backend" / "app" / "routers" / "actions_bridge.py").read_text(
            encoding="utf-8"
        ),
    ]
    assert all("zf-webui-key" not in source for source in sources)
