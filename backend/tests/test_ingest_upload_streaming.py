from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.routers import ingest as ingest_router
from backend.zhifei_autoplan import ocr_runtime


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


def test_pdf_ocr_overlay_preserves_declared_page_ordinals() -> None:
    base = "首页文字\f\f第三页文字\f"

    merged, mapped = ingest_router._merge_pdf_ocr_pages(
        base,
        ("首页OCR", "第二页OCR", "", "第四页OCR"),
        4,
    )

    assert mapped is True
    assert merged.count("\f") == 3
    pages = merged.split("\f")
    assert "首页文字" in pages[0] and "首页OCR" in pages[0]
    assert "第二页OCR" in pages[1]
    assert "第三页文字" in pages[2]
    assert "第四页OCR" in pages[3]


def test_pdf_ocr_overlay_rejects_unreliable_base_page_boundaries() -> None:
    base = "第一页\f第二页"

    merged, mapped = ingest_router._merge_pdf_ocr_pages(
        base,
        ("第一页OCR", "第二页OCR"),
        3,
    )

    assert mapped is False
    assert merged == base


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

    async def _no_ocr(
        path: Path,
        ext: str,
        base_text: str | None,
        **_kwargs: object,
    ) -> None:
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

    async def _no_ocr(
        path: Path,
        ext: str,
        base_text: str | None,
        **_kwargs: object,
    ) -> None:
        return None

    monkeypatch.setattr(ingest_router, "_try_ocr", _no_ocr)
    return workspace_root


def test_drawing_pdf_ocr_uses_all_declared_pages_without_catalog_stop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    source = tmp_path / "drawing.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "is_text_probably_scanned",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(ocr_runtime, "guess_ocr_lang", lambda **_kwargs: "chi_sim+eng")

    def _ocr_pdf_path(pdf_path: str, **kwargs: object) -> ocr_runtime.OcrResult:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return ocr_runtime.OcrResult(
            text="图纸 OCR",
            pages=27,
            lang="chi_sim+eng",
            page_texts=tuple("页" for _ in range(27)),
            page_statuses=tuple("text" for _ in range(27)),
            page_image_sha256=tuple(
                hashlib.sha256(f"drawing-page-{page}".encode()).hexdigest()
                for page in range(1, 28)
            ),
            source_pages=27,
        )

    monkeypatch.setattr(ocr_runtime, "ocr_pdf_path", _ocr_pdf_path)

    result = asyncio.run(
        ingest_router._try_ocr(
            source,
            "pdf",
            "乱码嵌入字体" * 100,
            source_hint="drawing",
            declared_pages=27,
        )
    )

    assert result is not None
    assert calls == [
        {
            "pdf_path": str(source),
            "max_pages": 27,
            "scale": 2.2,
            "lang": "chi_sim+eng",
            "stop_on_catalog": False,
            "allow_graphics_only": True,
        }
    ]


def test_ordinary_pdf_ocr_keeps_ten_page_catalog_bounded_policy(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    source = tmp_path / "tender.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "is_text_probably_scanned",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(ocr_runtime, "guess_ocr_lang", lambda **_kwargs: "chi_sim+eng")

    def _ocr_pdf_path(pdf_path: str, **kwargs: object) -> ocr_runtime.OcrResult:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return ocr_runtime.OcrResult(
            text="招标文件 OCR",
            pages=2,
            lang="chi_sim+eng",
            page_texts=("第一页", "目录"),
        )

    monkeypatch.setattr(ocr_runtime, "ocr_pdf_path", _ocr_pdf_path)

    result = asyncio.run(
        ingest_router._try_ocr(
            source,
            "pdf",
            "",
            source_hint="tender_qa",
            declared_pages=99,
        )
    )

    assert result is not None
    assert calls == [
        {
            "pdf_path": str(source),
            "max_pages": 10,
            "scale": 2.2,
            "lang": "chi_sim+eng",
            "stop_on_catalog": True,
            "allow_graphics_only": False,
        }
    ]


def test_drawing_pdf_ocr_rejects_short_page_text_sequence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "drawing-short.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "guess_ocr_lang", lambda **_kwargs: "chi_sim+eng")
    monkeypatch.setattr(
        ocr_runtime,
        "ocr_pdf_path",
        lambda *_args, **_kwargs: ocr_runtime.OcrResult(
            text="第一页\f第二页",
            pages=3,
            lang="chi_sim+eng",
            page_texts=("第一页", "第二页"),
        ),
    )

    result = asyncio.run(
        ingest_router._try_ocr(
            source,
            "pdf",
            "乱码嵌入字体" * 100,
            source_hint="drawing_standard",
            declared_pages=3,
        )
    )

    assert isinstance(result, ocr_runtime.OcrResult)
    assert result.pages == 3
    assert len(result.page_texts) == 2
    assert (
        ingest_router._full_page_ocr_result_proof(
            result,
            3,
            expected_policy=ingest_router.OCR_POLICY_DRAWING,
        )
        is None
    )


def test_drawing_pdf_ocr_rejects_failed_page_even_when_page_count_matches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "drawing-failed-page.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "guess_ocr_lang", lambda **_kwargs: "chi_sim+eng")
    monkeypatch.setattr(
        ocr_runtime,
        "ocr_pdf_path",
        lambda *_args, **_kwargs: ocr_runtime.OcrResult(
            text="\f第二页",
            pages=2,
            lang="chi_sim+eng",
            error="page_ocr_incomplete",
            page_texts=("", "第二页"),
            page_statuses=("failed", "text"),
            page_image_sha256=(
                "",
                hashlib.sha256(b"drawing-page-2").hexdigest(),
            ),
            source_pages=2,
        ),
    )

    result = asyncio.run(
        ingest_router._try_ocr(
            source,
            "pdf",
            "乱码嵌入字体" * 100,
            source_hint="drawing",
            declared_pages=2,
        )
    )

    assert isinstance(result, ocr_runtime.OcrResult)
    assert result.error == "page_ocr_incomplete"
    assert result.page_statuses == ("failed", "text")
    assert (
        ingest_router._full_page_ocr_result_proof(
            result,
            2,
            expected_policy=ingest_router.OCR_POLICY_DRAWING,
        )
        is None
    )


@pytest.mark.parametrize("declared_pages", [None, 0, True])
def test_drawing_pdf_ocr_rejects_invalid_declared_page_count(
    monkeypatch,
    tmp_path: Path,
    declared_pages: int | None,
) -> None:
    source = tmp_path / "drawing-invalid-pages.pdf"
    source.write_bytes(b"%PDF-test")
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)

    def _must_not_ocr(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalid declared page count must stop before OCR")

    monkeypatch.setattr(ocr_runtime, "ocr_pdf_path", _must_not_ocr)

    result = asyncio.run(
        ingest_router._try_ocr(
            source,
            "pdf",
            "乱码嵌入字体" * 100,
            source_hint="drawing_standard",
            declared_pages=declared_pages,
        )
    )

    assert result is None


def test_handle_upload_preserves_chinese_name_and_rejects_duplicate(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    payload = "第一项目施工组织设计验收资料".encode()
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
