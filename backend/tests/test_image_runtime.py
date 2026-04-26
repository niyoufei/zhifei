from __future__ import annotations

from types import SimpleNamespace


class _FakeAsyncApiClient:
    pass


class _FakeAsyncClient:
    def __init__(self) -> None:
        self._api_client = _FakeAsyncApiClient()


class _FakeModels:
    def __init__(self, response) -> None:
        self._response = response

    def generate_content(self, **_: object):
        return self._response


class _FakeInlineData:
    def __init__(self, data: bytes, mime_type: str) -> None:
        self.data = data
        self.mime_type = mime_type


class _FakePart:
    def __init__(self, data: bytes, mime_type: str) -> None:
        self.inline_data = _FakeInlineData(data, mime_type)
        self.text = None


class _FakeCandidate:
    def __init__(self, data: bytes, mime_type: str) -> None:
        self.content = SimpleNamespace(parts=[_FakePart(data, mime_type)])


class _FakeResponse:
    def __init__(self, data: bytes, mime_type: str = "image/png") -> None:
        self.candidates = [_FakeCandidate(data, mime_type)]


class _FakeClient:
    def __init__(self, response) -> None:
        self._aio = _FakeAsyncClient()
        self.models = _FakeModels(response)
        self.closed = False

    def close(self) -> None:
        self.closed = True


async def _exercise_async_close(fake_client: _FakeClient) -> None:
    await fake_client._aio._api_client._async_httpx_client.aclose()


def test_close_gemini_client_safely_installs_noop_async_closer():
    from backend.zhifei_autoplan.image_runtime import _close_gemini_client_safely

    fake_client = _FakeClient(_FakeResponse(b"png-bytes"))
    assert not hasattr(fake_client._aio._api_client, "_async_httpx_client")

    _close_gemini_client_safely(fake_client)

    assert fake_client.closed is True
    assert hasattr(fake_client._aio._api_client, "_async_httpx_client")


def test_generate_image_gemini_closes_sync_client_without_async_cleanup_error(monkeypatch, tmp_path):
    from backend.zhifei_autoplan import image_runtime

    fake_client = _FakeClient(_FakeResponse(b"fake-png-data"))
    monkeypatch.setattr(image_runtime.genai, "Client", lambda api_key: fake_client)

    result = image_runtime.generate_image_gemini(
        prompt="施工部署相关工程场景",
        api_key="test-key",
        out_dir=str(tmp_path),
    )

    assert result["ok"] is True
    assert fake_client.closed is True
    assert len(result["paths"]) == 1

    import asyncio

    asyncio.run(_exercise_async_close(fake_client))
