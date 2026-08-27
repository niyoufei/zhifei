"""Unit tests for backend/zhifei_autoplan/ocr_runtime.py

These tests are best-effort because OCR depends on system tesseract availability.
"""

from __future__ import annotations

import shutil
import sys
from types import SimpleNamespace

import pytest


def test_is_text_probably_scanned():
    from backend.zhifei_autoplan.ocr_runtime import is_text_probably_scanned

    assert is_text_probably_scanned("") is True
    assert is_text_probably_scanned("这是一些中文内容" * 50) is False
    assert is_text_probably_scanned("ALNUM123 " * 200) is False


def test_ocr_pdf_path_preserves_empty_and_failed_page_ordinals(monkeypatch, tmp_path):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "three-pages.pdf"
    pdf_path.write_bytes(b"stub")

    class _Image:
        mode = "L"
        size = (2, 2)

        def convert(self, _mode):
            return self

        def tobytes(self):
            return b"\xff" * 4

        def histogram(self):
            return [0] * 255 + [4]

    class _Bitmap:
        def __init__(self, index):
            self.index = index

        def to_pil(self):
            return _Image()

    class _Page:
        def __init__(self, index):
            self.index = index

        def render(self, *, scale):
            del scale
            if self.index == 1:
                raise RuntimeError("synthetic page failure")
            return _Bitmap(self.index)

    class _Document:
        def __init__(self, _path):
            self.pages = [_Page(0), _Page(1), _Page(2)]

        def __len__(self):
            return len(self.pages)

        def __getitem__(self, index):
            return self.pages[index]

        def close(self):
            return None

    extracted = iter(("FIRST", "THIRD"))
    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda _image, *, lang: next(extracted)),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=3,
        lang="eng",
        stop_on_catalog=False,
    )

    assert result.error == "page_ocr_incomplete"
    assert result.pages == 3
    assert result.source_pages == 3
    assert result.page_texts == ("FIRST", "", "THIRD")
    assert result.page_statuses == ("text", "failed", "text")
    assert len(result.page_image_sha256[0]) == 64
    assert result.page_image_sha256[1] == ""
    assert len(result.page_image_sha256[2]) == 64
    assert result.text.count("\f") == 2


def test_ocr_pdf_path_emits_explicit_blank_page_proof(monkeypatch, tmp_path):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(b"stub")

    class _Image:
        mode = "L"
        size = (4, 4)

        def convert(self, _mode):
            return self

        def tobytes(self):
            return b"\xff" * 16

        def histogram(self):
            return [0] * 255 + [16]

    class _Page:
        def render(self, *, scale):
            del scale
            return SimpleNamespace(to_pil=_Image)

    class _Document:
        def __init__(self, _path):
            self.pages = [_Page()]

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return self.pages[index]

        def close(self):
            return None

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda _image, *, lang: ""),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        lang="eng",
        stop_on_catalog=False,
    )

    assert result.error is None
    assert result.source_pages == 1
    assert result.page_texts == ("",)
    assert result.page_statuses == ("blank",)
    assert len(result.page_image_sha256[0]) == 64


def test_ocr_pdf_path_marks_nonblank_empty_ocr_as_unreadable(monkeypatch, tmp_path):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "unreadable.pdf"
    pdf_path.write_bytes(b"stub")

    class _NonblankImage:
        mode = "L"
        size = (4, 4)

        def convert(self, _mode):
            return self

        def tobytes(self):
            return b"\x00" * 16

        def histogram(self):
            return [16] + ([0] * 255)

    class _Page:
        def render(self, *, scale):
            del scale
            return SimpleNamespace(to_pil=_NonblankImage)

    class _Document:
        def __init__(self, _path):
            self.pages = [_Page()]

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return self.pages[index]

        def close(self):
            return None

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda _image, *, lang: ""),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        lang="eng",
        stop_on_catalog=False,
    )

    assert result.error == "page_ocr_incomplete"
    assert result.source_pages == 1
    assert result.page_texts == ("",)
    assert result.page_statuses == ("unreadable",)
    assert len(result.page_image_sha256[0]) == 64


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_ocr_pdf_path_can_read_simple_scanned_pdf(tmp_path):
    # Optional deps
    pytest.importorskip("pypdfium2")
    pytest.importorskip("pytesseract")

    from PIL import Image, ImageDraw

    from backend.zhifei_autoplan.ocr_runtime import ocr_pdf_path

    im = Image.new("RGB", (900, 220), color="white")
    draw = ImageDraw.Draw(im)
    draw.text((30, 60), "HELLO 123", fill="black")

    pdf_path = tmp_path / "scan.pdf"
    im.save(str(pdf_path), "PDF")

    res = ocr_pdf_path(str(pdf_path), max_pages=1, scale=2.0, lang="eng", stop_on_catalog=False)
    assert res.error is None
    assert res.pages >= 1
    assert res.source_pages == 1
    assert len(res.page_texts) == res.pages
    assert res.text.count("\f") == res.pages - 1
    assert "HELLO" in (res.text or "").upper()
