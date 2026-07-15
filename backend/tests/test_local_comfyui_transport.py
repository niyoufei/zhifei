from __future__ import annotations

import ast
import builtins
from copy import deepcopy
import inspect
import json
import socket
from typing import Any
import urllib.error
import urllib.request

import pytest

import image_generation.runtime.local_comfyui_transport as transport_module
from image_generation.runtime.local_comfyui_transport import (
    HTTP_TIMEOUT_SECONDS,
    LOCAL_COMFYUI_BASE_URL,
    MAX_RESPONSE_BYTES,
    LocalComfyUITransport,
)


@pytest.fixture(autouse=True)
def _forbid_real_socket_connections(monkeypatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("real socket connections are forbidden in focused tests")

    class _GuardedSocket(socket.socket):
        def connect(self, *_args: object, **_kwargs: object) -> None:
            blocked()

        def connect_ex(self, *_args: object, **_kwargs: object) -> int:
            blocked()
            return 1

    monkeypatch.setattr(socket, "socket", _GuardedSocket)
    monkeypatch.setattr(socket, "create_connection", blocked)


class _FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json; charset=utf-8",
        max_read_bytes: int | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.max_read_bytes = max_read_bytes
        self.read_sizes: list[int] = []
        self.closed = False
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.max_read_bytes is not None:
            size = min(size, self.max_read_bytes) if size >= 0 else self.max_read_bytes
        end = None if size < 0 else self._offset + size
        chunk = self.body[self._offset : end]
        self._offset += len(chunk)
        return chunk

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True


class _FakeOpener:
    def __init__(
        self,
        response: _FakeResponse | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[urllib.request.Request, float]] = []

    def open(
        self,
        request_value: urllib.request.Request,
        *,
        timeout: float,
    ) -> _FakeResponse:
        self.calls.append((request_value, timeout))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _json_response(
    value: object,
    *,
    status: int = 200,
    content_type: str = "application/json; charset=utf-8",
) -> _FakeResponse:
    return _FakeResponse(
        json.dumps(value, ensure_ascii=False).encode("utf-8"),
        status=status,
        content_type=content_type,
    )


def _health_payload() -> dict:
    return {
        "system": {"os": "darwin"},
        "devices": [{"name": "mps"}],
    }


@pytest.mark.parametrize(
    "base_url",
    [LOCAL_COMFYUI_BASE_URL, f"{LOCAL_COMFYUI_BASE_URL}/"],
)
def test_accepts_only_exact_local_base_url_and_normalizes_trailing_slash(
    base_url: str,
) -> None:
    opener = _FakeOpener(_json_response(_health_payload()))
    transport = LocalComfyUITransport(base_url, opener=opener)

    assert transport.check() is True
    assert opener.calls[0][0].full_url == f"{LOCAL_COMFYUI_BASE_URL}/system_stats"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:8188",
        "http://0.0.0.0:8188",
        "http://[::1]:8188",
        "http://127.0.0.2:8188",
        "http://192.0.2.1:8188",
        "http://example.com:8188",
        "http://127.0.0.1:8189",
        "https://127.0.0.1:8188",
        "http://user@127.0.0.1:8188",
        "http://user:password@127.0.0.1:8188",
        "http://127.0.0.1:8188?mode=queue",
        "http://127.0.0.1:8188#fragment",
        "http://127.0.0.1:8188/api",
        "http://127.0.0.1:8188/api/",
    ],
)
def test_rejects_every_noncanonical_base_url(base_url: str) -> None:
    opener = _FakeOpener(_json_response(_health_payload()))

    with pytest.raises(ValueError, match="base_url must be exactly"):
        LocalComfyUITransport(base_url, opener=opener)

    assert opener.calls == []


def test_default_opener_explicitly_disables_proxies_and_redirects(monkeypatch) -> None:
    captured_handlers: list[object] = []
    fake_opener = _FakeOpener(_json_response(_health_payload()))

    def fake_build_opener(*handlers: object) -> _FakeOpener:
        captured_handlers.extend(handlers)
        return fake_opener

    monkeypatch.setattr(transport_module.request, "build_opener", fake_build_opener)

    LocalComfyUITransport()

    proxy_handlers = [
        item for item in captured_handlers if isinstance(item, urllib.request.ProxyHandler)
    ]
    redirect_handlers = [
        item
        for item in captured_handlers
        if isinstance(item, transport_module._NoRedirectHandler)
    ]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}
    assert len(redirect_handlers) == 1
    assert (
        redirect_handlers[0].redirect_request(
            urllib.request.Request(LOCAL_COMFYUI_BASE_URL),
            None,
            302,
            "Found",
            {},
            "http://example.com",
        )
        is None
    )


def test_check_returns_true_for_expected_system_stats_object() -> None:
    response = _json_response({**_health_payload(), "extra": "ignored"})
    opener = _FakeOpener(response)

    assert LocalComfyUITransport(opener=opener).check() is True
    assert len(opener.calls) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"devices": []},
        {"system": {}},
        ["system", "devices"],
    ],
)
def test_check_returns_false_for_missing_fields_or_non_object(payload: object) -> None:
    opener = _FakeOpener(_json_response(payload))

    assert LocalComfyUITransport(opener=opener).check() is False
    assert len(opener.calls) == 1


def test_check_returns_false_for_invalid_json() -> None:
    opener = _FakeOpener(_FakeResponse(b"not-json"))

    assert LocalComfyUITransport(opener=opener).check() is False
    assert len(opener.calls) == 1


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_check_returns_false_for_nonstandard_json_constants(constant: bytes) -> None:
    body = b'{"system":' + constant + b',"devices":[]}'
    opener = _FakeOpener(_FakeResponse(body))

    assert LocalComfyUITransport(opener=opener).check() is False
    assert len(opener.calls) == 1


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(
            f"{LOCAL_COMFYUI_BASE_URL}/system_stats",
            503,
            "Unavailable",
            {},
            None,
        ),
        TimeoutError("timed out"),
    ],
)
def test_check_returns_false_for_http_error_or_timeout(error: Exception) -> None:
    opener = _FakeOpener(error=error)

    assert LocalComfyUITransport(opener=opener).check() is False
    assert len(opener.calls) == 1


def test_check_returns_false_when_response_exceeds_limit() -> None:
    response = _FakeResponse(
        b"{" + b" " * MAX_RESPONSE_BYTES + b"}",
        max_read_bytes=32 * 1024,
    )
    opener = _FakeOpener(response)

    assert LocalComfyUITransport(opener=opener).check() is False
    assert sum(response.read_sizes) >= MAX_RESPONSE_BYTES + 1
    assert max(response.read_sizes) <= transport_module._RESPONSE_READ_CHUNK_BYTES
    assert response.closed is True


@pytest.mark.parametrize(
    "response",
    [
        _json_response(_health_payload(), status=302),
        _json_response(_health_payload(), status=500),
        _json_response(_health_payload(), content_type="text/plain"),
    ],
)
def test_check_rejects_redirect_error_status_and_non_json_content_type(
    response: _FakeResponse,
) -> None:
    opener = _FakeOpener(response)

    assert LocalComfyUITransport(opener=opener).check() is False
    assert len(opener.calls) == 1


def test_check_uses_exact_get_request_timeout_and_bounded_read() -> None:
    response = _json_response(_health_payload())
    opener = _FakeOpener(response)

    assert LocalComfyUITransport(opener=opener).check() is True

    request_value, timeout = opener.calls[0]
    assert request_value.full_url == f"{LOCAL_COMFYUI_BASE_URL}/system_stats"
    assert request_value.get_method() == "GET"
    assert request_value.data is None
    assert request_value.get_header("Accept") == "application/json"
    assert timeout == HTTP_TIMEOUT_SECONDS
    assert response.read_sizes[0] == transport_module._RESPONSE_READ_CHUNK_BYTES


def test_get_state_maps_queue_fields_without_mutating_raw_response(monkeypatch) -> None:
    raw_response = {
        "queue_running": [["running-1", {"node": 1}]],
        "queue_pending": [["pending-1", {"node": 2}]],
        "queue_remaining": 7,
    }
    original = deepcopy(raw_response)
    opener = _FakeOpener(_json_response({}))
    monkeypatch.setattr(
        transport_module.json,
        "loads",
        lambda _value, **_kwargs: raw_response,
    )

    result = LocalComfyUITransport(opener=opener).get_state()

    assert result == {
        "running": [["running-1", {"node": 1}]],
        "pending": [["pending-1", {"node": 2}]],
    }
    assert set(result) == {"running", "pending"}
    assert raw_response == original
    assert result["running"] is not raw_response["queue_running"]
    assert result["pending"] is not raw_response["queue_pending"]


@pytest.mark.parametrize(
    "payload",
    [
        {"queue_running": {}, "queue_pending": []},
        {"queue_running": [], "queue_pending": {}},
        {"queue_pending": []},
        {"queue_running": []},
        [],
    ],
)
def test_get_state_rejects_bad_or_missing_queue_fields(payload: object) -> None:
    opener = _FakeOpener(_json_response(payload))

    with pytest.raises(ValueError):
        LocalComfyUITransport(opener=opener).get_state()

    assert len(opener.calls) == 1


def test_get_state_rejects_invalid_json() -> None:
    opener = _FakeOpener(_FakeResponse(b"not-json"))

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        LocalComfyUITransport(opener=opener).get_state()

    assert len(opener.calls) == 1


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(
            f"{LOCAL_COMFYUI_BASE_URL}/queue",
            500,
            "Error",
            {},
            None,
        ),
        TimeoutError("timed out"),
    ],
)
def test_get_state_fails_closed_for_http_error_or_timeout(error: Exception) -> None:
    opener = _FakeOpener(error=error)

    with pytest.raises(ValueError, match="HTTP request failed"):
        LocalComfyUITransport(opener=opener).get_state()

    assert len(opener.calls) == 1


def test_get_state_uses_exact_queue_get_request() -> None:
    opener = _FakeOpener(
        _json_response({"queue_running": [], "queue_pending": []})
    )

    assert LocalComfyUITransport(opener=opener).get_state() == {
        "running": [],
        "pending": [],
    }

    request_value, timeout = opener.calls[0]
    assert request_value.full_url == f"{LOCAL_COMFYUI_BASE_URL}/queue"
    assert request_value.get_method() == "GET"
    assert request_value.data is None
    assert request_value.get_header("Accept") == "application/json"
    assert timeout == HTTP_TIMEOUT_SECONDS


def test_submit_returns_only_prompt_id_and_ignores_extra_response_fields() -> None:
    opener = _FakeOpener(
        _json_response(
            {
                "prompt_id": "prompt-demo-001",
                "number": 7,
                "node_errors": {"1": "hidden"},
                "queue": ["hidden"],
                "endpoint": LOCAL_COMFYUI_BASE_URL,
            }
        )
    )

    result = LocalComfyUITransport(opener=opener).submit({"1": {"inputs": {}}})

    assert result == {"prompt_id": "prompt-demo-001"}
    assert set(result) == {"prompt_id"}
    assert len(opener.calls) == 1


def test_submit_does_not_modify_input_and_body_contains_only_deep_copied_prompt() -> None:
    api_prompt = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "施工现场"},
        }
    }
    original = deepcopy(api_prompt)
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    LocalComfyUITransport(opener=opener).submit(api_prompt)

    request_value = opener.calls[0][0]
    decoded_body = json.loads(request_value.data.decode("utf-8"))
    assert decoded_body == {"prompt": original}
    assert set(decoded_body) == {"prompt"}
    assert api_prompt == original
    assert decoded_body["prompt"] is not api_prompt


def test_submit_deep_copies_prompt_before_canonical_serialization(monkeypatch) -> None:
    api_prompt = {"1": {"inputs": {"text": "施工现场"}}}
    original = deepcopy(api_prompt)
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    def mutating_serializer(value: dict, _label: str) -> bytes:
        value["prompt"]["1"]["inputs"]["text"] = "mutated-copy"
        return b'{"prompt":{}}'

    monkeypatch.setattr(
        transport_module,
        "_strict_json_bytes",
        mutating_serializer,
    )

    LocalComfyUITransport(opener=opener).submit(api_prompt)

    assert api_prompt == original


def test_submit_uses_stable_compact_utf8_canonical_json() -> None:
    api_prompt = {
        "2": {"inputs": {"text": "施工"}},
        "1": {"class_type": "Node"},
    }
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    LocalComfyUITransport(opener=opener).submit(api_prompt)

    assert opener.calls[0][0].data == (
        '{"prompt":{"1":{"class_type":"Node"},'
        '"2":{"inputs":{"text":"施工"}}}}'
    ).encode("utf-8")


def test_submit_uses_exact_post_url_method_headers_and_timeout() -> None:
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    LocalComfyUITransport(opener=opener).submit({"1": {"inputs": {}}})

    request_value, timeout = opener.calls[0]
    assert request_value.full_url == f"{LOCAL_COMFYUI_BASE_URL}/prompt"
    assert request_value.get_method() == "POST"
    assert request_value.get_header("Content-type") == "application/json"
    assert request_value.get_header("Accept") == "application/json"
    assert timeout == HTTP_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"prompt_id": ""},
        {"prompt_id": "   "},
        {"prompt_id": None},
        {"prompt_id": 7},
    ],
)
def test_submit_rejects_missing_empty_or_non_string_prompt_id(payload: dict) -> None:
    opener = _FakeOpener(_json_response(payload))

    with pytest.raises(ValueError, match="prompt_id must be a non-empty string"):
        LocalComfyUITransport(opener=opener).submit({"1": {"inputs": {}}})

    assert len(opener.calls) == 1


@pytest.mark.parametrize("payload", [[], "prompt-demo-001", 7, None])
def test_submit_rejects_non_object_response(payload: object) -> None:
    opener = _FakeOpener(_json_response(payload))

    with pytest.raises(ValueError, match="submit response must be a JSON object"):
        LocalComfyUITransport(opener=opener).submit({"1": {"inputs": {}}})

    assert len(opener.calls) == 1


@pytest.mark.parametrize("api_prompt", [[], "prompt", 7, None])
def test_submit_rejects_non_dict_api_prompt_without_http_call(
    api_prompt: object,
) -> None:
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    with pytest.raises(ValueError, match="api_prompt must be a dict"):
        LocalComfyUITransport(opener=opener).submit(api_prompt)  # type: ignore[arg-type]

    assert opener.calls == []


@pytest.mark.parametrize(
    "api_prompt",
    [
        {"1": {"value": {1, 2}}},
        {"1": {"value": float("nan")}},
        {"1": {"value": object()}},
    ],
)
def test_submit_rejects_non_json_serializable_prompt_without_http_call(
    api_prompt: dict,
) -> None:
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    with pytest.raises(ValueError, match="api_prompt must be JSON serializable"):
        LocalComfyUITransport(opener=opener).submit(api_prompt)

    assert opener.calls == []


def test_submit_rejects_circular_prompt_without_http_call() -> None:
    api_prompt: dict[str, Any] = {"1": {}}
    api_prompt["1"]["self"] = api_prompt
    opener = _FakeOpener(_json_response({"prompt_id": "prompt-demo-001"}))

    with pytest.raises(ValueError, match="api_prompt must be JSON serializable"):
        LocalComfyUITransport(opener=opener).submit(api_prompt)

    assert opener.calls == []


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(
            f"{LOCAL_COMFYUI_BASE_URL}/prompt",
            500,
            "Error",
            {},
            None,
        ),
        TimeoutError("timed out"),
    ],
)
def test_submit_fails_closed_once_without_retry(error: Exception) -> None:
    opener = _FakeOpener(error=error)

    with pytest.raises(ValueError, match="HTTP request failed"):
        LocalComfyUITransport(opener=opener).submit({"1": {"inputs": {}}})

    assert len(opener.calls) == 1


def test_fake_opener_calls_do_not_touch_socket_environment_or_files(monkeypatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("forbidden implicit runtime access")

    monkeypatch.setattr(transport_module.request, "getproxies", blocked)
    monkeypatch.setattr(builtins, "open", blocked)

    health_opener = _FakeOpener(_json_response(_health_payload()))
    queue_opener = _FakeOpener(
        _json_response({"queue_running": [], "queue_pending": []})
    )
    submit_opener = _FakeOpener(
        _json_response({"prompt_id": "prompt-demo-001"})
    )

    assert LocalComfyUITransport(opener=health_opener).check() is True
    assert LocalComfyUITransport(opener=queue_opener).get_state() == {
        "running": [],
        "pending": [],
    }
    assert LocalComfyUITransport(opener=submit_opener).submit({"1": {}}) == {
        "prompt_id": "prompt-demo-001"
    }


def test_default_opener_construction_does_not_read_environment_proxies(
    monkeypatch,
) -> None:
    def blocked_getproxies() -> dict:
        raise AssertionError("environment proxies must not be read")

    monkeypatch.setattr(transport_module.request, "getproxies", blocked_getproxies)

    transport = LocalComfyUITransport()

    assert isinstance(transport, LocalComfyUITransport)


def test_module_has_only_three_public_operations_and_no_overreach_surfaces() -> None:
    source = inspect.getsource(transport_module)
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", 1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    public_operations = {
        name
        for name, value in vars(LocalComfyUITransport).items()
        if callable(value) and not name.startswith("_")
    }
    function_names = {
        node.name.lower()
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert public_operations == {"check", "get_state", "submit"}
    assert {
        "requests",
        "subprocess",
        "socket",
        "os",
        "pathlib",
        "io",
        "multiprocessing",
    }.isdisjoint(imported_roots)
    assert {
        "open",
        "Popen",
        "run",
        "system",
        "urlopen",
        "__import__",
        "eval",
        "exec",
    }.isdisjoint(called_names)
    assert all(
        marker not in function_name
        for function_name in function_names
        for marker in ("history", "view", "download", "model", "launch", "spawn")
    )
    for forbidden_text in (
        "/history",
        "/view",
        "snapshot_download",
        "huggingface",
        "model_download",
        "start_service",
        "stop_service",
        "start_comfyui",
        "stop_comfyui",
        "curl",
        ".env",
        "os.environ",
    ):
        assert forbidden_text not in source.lower()
