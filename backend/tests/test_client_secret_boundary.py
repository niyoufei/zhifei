from __future__ import annotations

import pytest

from scripts import run_actions_pipeline, watch_projects_autoplan


class _Response:
    status_code = 200
    text = "ok"

    @staticmethod
    def json() -> dict:
        return {"ok": True}


@pytest.mark.parametrize(
    "module", [run_actions_pipeline, watch_projects_autoplan]
)
def test_generation_client_never_serializes_provider_routes_or_secrets(
    monkeypatch, module
):
    calls: list[dict] = []

    def _post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return _Response()

    monkeypatch.setattr(module.requests, "post", _post)
    payload = {
        "topic": "合成项目",
        "provider": "client-choice",
        "model": "client-model",
        "api_key": "must-not-leave-process",
        "base_url": "https://attacker.example",
        "secret_key": "secret",
        "token_url": "https://attacker.example/token",
        "image_provider": "client-image",
        "image_model": "client-image-model",
        "image_api_key": "image-secret",
    }

    result = module._post_json(
        "http://127.0.0.1:8010",
        "/actions/generate_async",
        "local-actions-key",
        payload,
        timeout=1,
    )

    assert result == {"ok": True}
    assert calls[0]["url"] == "http://127.0.0.1:8010/actions/generate_async"
    assert calls[0]["json"] == {"topic": "合成项目"}


@pytest.mark.parametrize(
    "module", [run_actions_pipeline, watch_projects_autoplan]
)
@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com",
        "http://localhost:8010",
        "http://127.0.0.1:8010@attacker.example",
        "http://127.0.0.1:8010/path",
    ],
)
def test_non_loopback_backend_is_rejected_before_any_request(
    monkeypatch, module, base_url
):
    calls: list[object] = []
    monkeypatch.setattr(
        module.requests, "post", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    with pytest.raises(ValueError, match="LOCAL_BACKEND_LOOPBACK_REQUIRED"):
        module._post_json(
            base_url,
            "/actions/generate_async",
            "must-not-leave-process",
            {"topic": "合成项目"},
            timeout=1,
        )

    assert calls == []
