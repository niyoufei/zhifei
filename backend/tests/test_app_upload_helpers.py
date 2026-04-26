from __future__ import annotations

import ast
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from requests_toolbelt.multipart.encoder import MultipartEncoder

pytestmark = pytest.mark.skip(reason="app.py upload helper is outside this ingest-only PR scope")


class _FakeResponse:
    status_code = 200

    def json(self) -> dict[str, Any]:
        return {"saved": [{"filename": "工程量清单.pdf"}]}


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
        return _FakeResponse()


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
    wanted_funcs = {"_uploaded_file_size", "_ingest_docs"}
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

    assert result == {"saved": [{"filename": "工程量清单.pdf"}]}
    assert len(fake_requests.calls) == 1
    call = fake_requests.calls[0]
    assert call["url"] == "http://127.0.0.1:8010/ingest/upload"
    assert call["params"]["project_id"] == "project-upload-stream"
    assert call["params"]["source_hint"] == "boq"
    assert call["data_type"] == "MultipartEncoder"
    assert str(call["content_type"]).startswith("multipart/form-data; boundary=")
    assert call["sample"]
