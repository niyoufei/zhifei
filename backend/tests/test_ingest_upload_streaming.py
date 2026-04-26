from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.app.routers import ingest as ingest_router


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
