"""Unit tests for backend/zhifei_autoplan/ocr_runtime.py

These tests are best-effort because OCR depends on system tesseract availability.
"""

from __future__ import annotations

import shutil

import pytest


def test_is_text_probably_scanned():
    from backend.zhifei_autoplan.ocr_runtime import is_text_probably_scanned

    assert is_text_probably_scanned("") is True
    assert is_text_probably_scanned("这是一些中文内容" * 50) is False
    assert is_text_probably_scanned("ALNUM123 " * 200) is False


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
    assert "HELLO" in (res.text or "").upper()

