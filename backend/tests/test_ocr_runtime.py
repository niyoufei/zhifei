"""Unit tests for backend/zhifei_autoplan/ocr_runtime.py

These tests are best-effort because OCR depends on system tesseract availability.
"""

from __future__ import annotations

import json
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
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(
            image_to_string=lambda _image, *, lang, config, timeout: next(extracted)
        ),
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
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda _image, *, lang, config, timeout: ""),
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
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda _image, *, lang, config, timeout: ""),
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

    graphics_result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        lang="eng",
        stop_on_catalog=False,
        allow_graphics_only=True,
    )

    assert graphics_result.error is None
    assert graphics_result.source_pages == 1
    assert graphics_result.page_texts == ("",)
    assert graphics_result.page_statuses == ("graphics_only",)
    assert graphics_result.page_image_sha256 == result.page_image_sha256
    assert graphics_result.diagnostics["status_counts"] == {"graphics_only": 1}
    assert graphics_result.diagnostics["graphics_only_pages"] == [1]
    assert (
        graphics_result.diagnostics["machine_code"]
        == "OCR_COMPLETE_WITH_GRAPHICS_ONLY"
    )


@pytest.mark.parametrize("primary_outcome", ["empty", "timeout"])
def test_ocr_pdf_path_recovers_sparse_cad_text_with_bounded_second_pass(
    monkeypatch,
    tmp_path,
    primary_outcome,
):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "sparse-cad.pdf"
    pdf_path.write_bytes(b"stub")
    render_scales: list[float] = []
    ocr_calls: list[dict[str, object]] = []
    resources: list[object] = []

    class _Image:
        mode = "L"
        size = (4, 4)

        def __init__(self):
            self.closed = False
            resources.append(self)

        def convert(self, _mode):
            return self

        def tobytes(self):
            return b"\x00" * 16

        def histogram(self):
            return [16] + ([0] * 255)

        def rotate(self, _degrees, *, expand, fillcolor):
            assert expand is True
            assert fillcolor == 255
            return _Image()

        def close(self):
            self.closed = True

    class _Bitmap:
        def __init__(self):
            self.closed = False
            self.image = _Image()
            resources.append(self)

        def to_pil(self):
            return self.image

        def close(self):
            self.closed = True

    class _Page:
        def __init__(self):
            self.closed = False
            resources.append(self)

        def render(self, *, scale):
            render_scales.append(scale)
            return _Bitmap()

        def close(self):
            self.closed = True

    class _Document:
        def __init__(self, _path):
            self.page = _Page()
            self.closed = False
            resources.append(self)

        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return self.page

        def close(self):
            self.closed = True

    def _image_to_string(_image, *, lang, config, timeout):
        ocr_calls.append(
            {
                "lang": lang,
                "config": config,
                "timeout": timeout,
            }
        )
        if config == "" and primary_outcome == "timeout":
            raise RuntimeError("Tesseract process timeout SECRET_RAW_STDERR")
        return "钢梁 GJ-01" if config == "--psm 11" else ""

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        scale=2.0,
        lang="eng",
        stop_on_catalog=False,
        page_timeout_seconds=2.0,
        attempt_timeout_seconds=0.5,
    )

    assert result.error is None
    assert result.page_texts == ("钢梁 GJ-01",)
    assert result.page_statuses == ("text",)
    assert render_scales == (
        [2.0, 3.0] if primary_outcome == "empty" else [2.0, 1.0]
    )
    assert [call["config"] for call in ocr_calls] == ["", "--psm 11"]
    assert all(0 < float(call["timeout"]) <= 0.5 for call in ocr_calls)
    assert result.diagnostics == {
        "schema_version": "ocr-diagnostics-v1",
        "engine": "tesseract",
        "lang": "eng",
        "declared_pages": 1,
        "attempted_pages": 1,
        "status_counts": {"text": 1},
        "unreadable_pages": [],
        "failed_pages": [],
        "timeout_pages": [],
        "graphics_only_pages": [],
        "recovered_pages": [1],
        "page_lists_truncated": False,
        "error_code": "none",
        "machine_code": "OCR_COMPLETE",
    }
    assert all(getattr(resource, "closed", False) for resource in resources)
    assert "钢梁" not in json.dumps(result.diagnostics, ensure_ascii=False)


def test_ocr_pdf_path_timeout_fails_closed_and_redacts_diagnostics(
    monkeypatch,
    tmp_path,
):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "timeout.pdf"
    pdf_path.write_bytes(b"stub")
    timeouts: list[float] = []
    closed = {"image": False, "bitmap": False, "page": False, "document": False}

    class _NonblankImage:
        mode = "L"
        size = (4, 4)

        def convert(self, _mode):
            return self

        def tobytes(self):
            return b"\x00" * 16

        def histogram(self):
            return [16] + ([0] * 255)

        def close(self):
            closed["image"] = True

    class _Bitmap:
        def to_pil(self):
            return _NonblankImage()

        def close(self):
            closed["bitmap"] = True

    class _Page:
        def render(self, *, scale):
            del scale
            return _Bitmap()

        def close(self):
            closed["page"] = True

    class _Document:
        def __init__(self, _path):
            self.page = _Page()

        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return self.page

        def close(self):
            closed["document"] = True

    def _timeout(_image, *, lang, config, timeout):
        del lang, config
        timeouts.append(timeout)
        raise RuntimeError("Tesseract process timeout SECRET_RAW_STDERR")

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=_timeout),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        lang="eng",
        stop_on_catalog=False,
        page_timeout_seconds=0.2,
        attempt_timeout_seconds=9.0,
    )

    assert result.error == "page_ocr_incomplete"
    assert result.page_texts == ("",)
    assert result.page_statuses == ("timeout",)
    assert timeouts and 0 < timeouts[0] <= 0.2
    assert result.diagnostics["status_counts"] == {"timeout": 1}
    assert result.diagnostics["timeout_pages"] == [1]
    assert result.diagnostics["failed_pages"] == []
    assert result.diagnostics["error_code"] == "ocr_page_timeout"
    assert result.diagnostics["machine_code"] == "OCR_PAGE_TIMEOUT"
    serialized = json.dumps(result.diagnostics, ensure_ascii=False)
    assert "SECRET_RAW_STDERR" not in serialized
    assert len(serialized) < 2048
    assert all(closed.values())


def test_ocr_pdf_path_engine_exception_fails_closed_without_raw_error(
    monkeypatch,
    tmp_path,
):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "engine-error.pdf"
    pdf_path.write_bytes(b"stub")

    class _Image:
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
            return SimpleNamespace(to_pil=_Image)

    class _Document:
        def __init__(self, _path):
            self.page = _Page()

        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return self.page

        def close(self):
            return None

    def _fail(_image, *, lang, config, timeout):
        del lang, config, timeout
        raise RuntimeError("SECRET_RAW_STDERR provider detail")

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setattr(ocr_runtime, "_preprocess_pil_for_ocr", lambda image: image)
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=_fail),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=1,
        lang="eng",
        stop_on_catalog=False,
    )

    assert result.error == "page_ocr_incomplete"
    assert result.page_statuses == ("failed",)
    assert result.diagnostics["failed_pages"] == [1]
    assert result.diagnostics["error_code"] == "ocr_engine_failed"
    assert result.diagnostics["machine_code"] == "OCR_ENGINE_FAILED"
    assert "SECRET_RAW_STDERR" not in json.dumps(result.diagnostics)
    assert "SECRET_RAW_STDERR" not in str(result.error)


def test_ocr_pdf_path_missing_language_pack_fails_before_ocr(
    monkeypatch,
    tmp_path,
):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "missing-language.pdf"
    pdf_path.write_bytes(b"stub")
    state = {"document_closed": False, "ocr_called": False}

    class _Document:
        def __init__(self, _path):
            return None

        def __len__(self):
            return 3

        def close(self):
            state["document_closed"] = True

    def _unexpected_ocr(*_args, **_kwargs):
        state["ocr_called"] = True
        raise AssertionError("OCR must not run with a missing language pack")

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: {"eng"},
    )
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=_unexpected_ocr),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=3,
        stop_on_catalog=False,
    )

    assert result.error == "ocr_language_unavailable"
    assert result.lang == "chi_sim+eng"
    assert result.pages == 0
    assert result.source_pages == 3
    assert result.page_statuses == ()
    assert result.diagnostics["declared_pages"] == 3
    assert result.diagnostics["attempted_pages"] == 0
    assert result.diagnostics["error_code"] == "ocr_language_unavailable"
    assert result.diagnostics["machine_code"] == "OCR_LANGUAGE_UNAVAILABLE"
    assert state == {"document_closed": True, "ocr_called": False}


def test_ocr_pdf_path_unverifiable_language_list_fails_before_ocr(
    monkeypatch,
    tmp_path,
):
    from backend.zhifei_autoplan import ocr_runtime

    pdf_path = tmp_path / "unverifiable-language.pdf"
    pdf_path.write_bytes(b"stub")
    state = {"document_closed": False, "ocr_called": False}

    class _Document:
        def __init__(self, _path):
            return None

        def __len__(self):
            return 2

        def close(self):
            state["document_closed"] = True

    def _unexpected_ocr(*_args, **_kwargs):
        state["ocr_called"] = True
        raise AssertionError("OCR must not run with an unverifiable language list")

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(
        ocr_runtime,
        "_available_tesseract_languages",
        lambda: None,
    )
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=_Document),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_string=_unexpected_ocr),
    )

    result = ocr_runtime.ocr_pdf_path(
        str(pdf_path),
        max_pages=2,
        lang="chi_sim+eng",
        stop_on_catalog=False,
    )

    assert result.error == "ocr_language_list_unavailable"
    assert result.pages == 0
    assert result.source_pages == 2
    assert result.diagnostics["error_code"] == "ocr_language_list_unavailable"
    assert result.diagnostics["machine_code"] == "OCR_LANGUAGE_LIST_UNAVAILABLE"
    assert state == {"document_closed": True, "ocr_called": False}


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

    res = ocr_pdf_path(
        str(pdf_path), max_pages=1, scale=2.0, lang="eng", stop_on_catalog=False
    )
    assert res.error is None
    assert res.pages >= 1
    assert res.source_pages == 1
    assert len(res.page_texts) == res.pages
    assert res.text.count("\f") == res.pages - 1
    assert "HELLO" in (res.text or "").upper()
