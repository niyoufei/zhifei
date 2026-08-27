from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.routers import ingest as ingest_router


@pytest.fixture(autouse=True)
def _isolate_parse_cache(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "ingest-cache")


class _ChunkOnlyUpload:
    def __init__(self, data: bytes, *, filename: str) -> None:
        self.filename = filename
        self._data = data
        self._offset = 0
        self.requested_sizes: list[int] = []
        self.seek_positions: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.requested_sizes.append(size)
        if size is None or size < 0:
            raise AssertionError("upload should be read in fixed-size chunks")
        if self._offset >= len(self._data):
            return b""
        end = min(self._offset + size, len(self._data))
        chunk = self._data[self._offset:end]
        self._offset = end
        return chunk

    async def seek(self, offset: int) -> None:
        self.seek_positions.append(offset)
        self._offset = max(0, offset)


def test_handle_upload_streams_large_files_to_disk(monkeypatch, tmp_path: Path) -> None:
    chunk_size = 1024 * 1024
    payload = b"A" * (chunk_size * 2 + 17)
    upload = _ChunkOnlyUpload(payload, filename="工程量清单.txt")
    workspace_root = tmp_path / "workspace"
    uploads_dir = workspace_root / "uploads"
    extracts_dir = workspace_root / "extracts"
    previews_dir = workspace_root / "previews"
    audit_path = workspace_root / "audit" / "ingest.jsonl"

    monkeypatch.setattr(
        ingest_router,
        "_resolve_workspace_context",
        lambda session_id=None, workspace_dir=None: {
            "session_id": "sess-large-upload",
            "workspace_dir": str(workspace_root),
        },
    )
    monkeypatch.setattr(
        ingest_router,
        "workspace_paths",
        lambda _workspace_dir: {
            "uploads": uploads_dir,
            "extracts": extracts_dir,
            "previews": previews_dir,
            "ingest_audit": audit_path,
        },
    )

    async def _no_ocr(path: Path, ext: str, base_text: str | None) -> None:
        return None

    monkeypatch.setattr(ingest_router, "_try_ocr", _no_ocr)

    result = asyncio.run(
        ingest_router._handle_upload(
            [upload],
            project_id="project-large-upload",
            source_hint="boq",
        )
    )

    assert len(result["saved"]) == 1
    saved = result["saved"][0]
    assert saved["filename"] == "工程量清单.txt"
    assert saved["project_id"] == "project-large-upload"
    assert saved["source_hint"] == "boq"
    assert saved["bytes"] == len(payload)
    assert saved["text_bytes"] == len(payload)
    assert Path(saved["saved_as"]).exists()
    assert Path(saved["saved_as"]).read_bytes() == payload
    assert Path(saved["extract_saved_as"]).exists()
    assert Path(saved["extract_saved_as"]).read_text(encoding="utf-8") == payload.decode("utf-8")
    assert upload.requested_sizes == [chunk_size, chunk_size, chunk_size, chunk_size]
    assert upload.seek_positions == [0, 0]

    audit_rows = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(audit_rows) == 1
    audit_record = json.loads(audit_rows[0])
    assert audit_record["bytes"] == len(payload)
    assert audit_record["saved_as"] == saved["saved_as"]


def _isolate_workspace(monkeypatch, tmp_path: Path) -> Path:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(
        ingest_router,
        "_resolve_workspace_context",
        lambda session_id=None, workspace_dir=None: {
            "session_id": "sess-abnormal-upload",
            "workspace_dir": str(workspace_root),
        },
    )

    async def _no_ocr(path: Path, ext: str, base_text: str | None) -> None:
        return None

    monkeypatch.setattr(ingest_router, "_try_ocr", _no_ocr)
    return workspace_root


def test_handle_upload_preserves_chinese_name_and_rejects_duplicate(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    payload = "第一项目施工组织设计验收资料".encode("utf-8")
    first = _ChunkOnlyUpload(payload, filename="中文资料文件.txt")
    duplicate = _ChunkOnlyUpload(payload, filename="重复资料文件.txt")

    result = asyncio.run(ingest_router._handle_upload([first, duplicate]))

    assert [item["filename"] for item in result["saved"]] == ["中文资料文件.txt"]
    assert result["rejected"] == [
        {
            "filename": "重复资料文件.txt",
            "code": "DUPLICATE_FILE",
            "sha256": result["saved"][0]["sha256"],
            "duplicate_of": result["saved"][0]["saved_as"],
        }
    ]


def test_handle_upload_rejects_empty_and_damaged_files(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as empty_error:
        asyncio.run(ingest_router._handle_upload([_ChunkOnlyUpload(b"", filename="空文件.txt")]))
    assert empty_error.value.status_code == 400
    assert empty_error.value.detail == "all files are empty"

    damaged = _ChunkOnlyUpload(b"%PDF-1.7\nthis is not a valid PDF", filename="损坏文件.pdf")
    with pytest.raises(HTTPException) as damaged_error:
        asyncio.run(ingest_router._handle_upload([damaged]))
    assert damaged_error.value.status_code == 422
    assert damaged_error.value.detail["code"] == "ALL_FILES_REJECTED"
    assert damaged_error.value.detail["rejected"][0]["code"] == "FILE_PARSE_FAILED"


def test_handle_upload_stops_when_stream_exceeds_size_limit(monkeypatch, tmp_path: Path) -> None:
    workspace_root = _isolate_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(ingest_router, "MAX_UPLOAD_BYTES", 10)
    oversized = _ChunkOnlyUpload(b"01234567890", filename="超大文件.txt")

    with pytest.raises(HTTPException) as error:
        asyncio.run(ingest_router._handle_upload([oversized]))

    assert error.value.status_code == 413
    assert error.value.detail == {
        "code": "UPLOAD_TOO_LARGE",
        "filename": "超大文件.txt",
        "max_bytes": 10,
    }
    assert not list((workspace_root / "uploads").rglob(".upload_*"))
