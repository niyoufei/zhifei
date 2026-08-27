from __future__ import annotations

from backend.app.routers.ingest import _classify_tags


def test_site_photo_hint_not_marked_as_drawing() -> None:
    tags = _classify_tags("施工现场图01.jpg", "jpg", None, source_hint="site_photo")
    assert "site_photo" in tags
    assert "drawing" not in tags


def test_tender_qa_hint_adds_tender_tags() -> None:
    tags = _classify_tags("招标文件答疑.pdf", "pdf", None, source_hint="tender_qa")
    assert "tender" in tags
    assert "qa" in tags


def test_drawing_standard_hint_keeps_drawing_by_filename() -> None:
    tags = _classify_tags("结构施工图.dxf", "dxf", "cad", source_hint="drawing_standard")
    assert "drawing" in tags


def test_drawing_standard_hint_keeps_standard_by_filename() -> None:
    tags = _classify_tags("企业标准-模板工程.pdf", "pdf", None, source_hint="drawing_standard")
    assert "standard" in tags
    assert "drawing" not in tags


def test_drawing_standard_hint_defaults_unambiguous_pdf_to_drawing() -> None:
    tags = _classify_tags("1 挤奶厅.pdf", "pdf", None, source_hint="drawing_standard")
    assert "drawing" in tags
