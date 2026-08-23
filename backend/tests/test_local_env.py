from __future__ import annotations

import os


def test_load_local_env_loads_simple_values_without_overriding(monkeypatch, tmp_path):
    from backend.zhifei_autoplan.local_env import load_local_env

    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "# local only\nGOOGLE_API_KEY=google-test-value\nexport DEEPSEEK_API_KEY='deepseek-test-value'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "preexisting")

    assert load_local_env(env_path) == 1
    assert os.environ["GOOGLE_API_KEY"] == "google-test-value"
    assert os.environ["DEEPSEEK_API_KEY"] == "preexisting"


def test_load_local_env_ignores_invalid_lines(monkeypatch, tmp_path):
    from backend.zhifei_autoplan.local_env import load_local_env

    env_path = tmp_path / ".env.local"
    env_path.write_text("BAD NAME=value\nEMPTY=\nNO_EQUALS\n", encoding="utf-8")
    monkeypatch.delenv("EMPTY", raising=False)

    assert load_local_env(env_path) == 0
    assert "EMPTY" not in os.environ
