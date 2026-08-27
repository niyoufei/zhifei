from __future__ import annotations

import ast
import json
import mimetypes
import os
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests


class _FakeResponse:
    status_code = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeRequests:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, params: dict[str, Any], data: Any, headers: dict[str, str], timeout: int) -> _FakeResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "data_type": type(data).__name__,
                "content_type": headers.get("Content-Type"),
                "sample": data.read(256),
                "timeout": timeout,
            }
        )
        return _FakeResponse({"job_id": "a" * 32, "status": "queued"})

    def get(self, url: str, *, timeout: int) -> _FakeResponse:
        self.calls.append({"url": url, "timeout": timeout, "method": "GET"})
        return _FakeResponse(
            {
                "job": {
                    "status": "succeeded",
                    "progress": {"percent": 100},
                    "result": {"saved": [{"filename": "工程量清单.pdf"}]},
                }
            }
        )


class _StreamingUpload(BytesIO):
    def __init__(self, data: bytes, *, name: str) -> None:
        super().__init__(data)
        self.name = name
        self.size = len(data)

    def getvalue(self) -> bytes:  # pragma: no cover - called only on regression
        raise AssertionError("_ingest_docs should not copy large uploads via getvalue()")


def _load_helpers(fake_requests: _FakeRequests) -> dict[str, Any]:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {"_stable_http_error", "_uploaded_file_size", "_ingest_docs"}
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {
        "Any": Any,
        "BytesIO": BytesIO,
        "MultipartEncoder": MultipartEncoder,
        "mimetypes": mimetypes,
        "json": json,
        "os": os,
        "re": re,
        "time": time,
        "requests": fake_requests,
        "_workspace_context_params": lambda params: params,
    }
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace


def test_ingest_docs_uses_streaming_multipart_for_uploaded_files() -> None:
    fake_requests = _FakeRequests()
    helpers = _load_helpers(fake_requests)
    upload = _StreamingUpload(b"x" * 1024, name="工程量清单.pdf")

    result = helpers["_ingest_docs"](
        "http://127.0.0.1:8010",
        [upload],
        "project-upload-stream",
        source_hint="boq",
    )

    assert result == {
        "saved": [{"filename": "工程量清单.pdf"}],
        "job_id": "a" * 32,
    }
    assert len(fake_requests.calls) == 2
    call = fake_requests.calls[0]
    assert call["url"] == "http://127.0.0.1:8010/ingest/jobs"
    assert call["params"]["project_id"] == "project-upload-stream"
    assert call["params"]["source_hint"] == "boq"
    assert call["data_type"] == "MultipartEncoder"
    assert str(call["content_type"]).startswith("multipart/form-data; boundary=")
    assert call["sample"]
    assert fake_requests.calls[1]["url"].endswith("/ingest/jobs/" + "a" * 32)


def test_http_failure_uses_stable_projection_and_redacts_secret(monkeypatch) -> None:
    fake_requests = _FakeRequests()
    helpers = _load_helpers(fake_requests)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-provider-value")
    raw = json.dumps(
        {
            "detail": {
                "code": "MODEL_PROVIDER_ADMISSION_BLOCKED",
                "message": "模型不可用 secret-provider-value",
                "action": "检查配置 secret-provider-value",
                "traceback": "RuntimeError(raw stack)",
            }
        },
        ensure_ascii=False,
    )

    error = helpers["_stable_http_error"]("/actions/runs", 503, raw)
    rendered = str(error)

    assert "MODEL_PROVIDER_ADMISSION_BLOCKED" in rendered
    assert "模型不可用" in rendered
    assert "[已脱敏]" in rendered
    assert "secret-provider-value" not in rendered
    assert "RuntimeError" not in rendered


def test_connection_failure_is_rendered_as_stable_chinese_error() -> None:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_stable_ui_error"
    )
    namespace: dict[str, Any] = {"json": json, "requests": requests}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(app_path), "exec"), namespace)

    error = requests.exceptions.ConnectionError(
        "HTTPConnectionPool(host='127.0.0.1', port=8010): Connection refused"
    )
    public = namespace["_stable_ui_error"](error)

    assert public["code"] == "BACKEND_UNAVAILABLE"
    assert "后端服务暂不可用" in public["message"]
    assert "HTTPConnectionPool" not in json.dumps(public, ensure_ascii=False)
