from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_contains_foreign_text_detects_latin_letters():
    from backend.zhifei_autoplan.semantic_image_enhancer import contains_foreign_text

    assert contains_foreign_text("安全标识 A 区域") is True
    assert contains_foreign_text("安全标识 甲 区域") is False


def test_build_semantic_image_item_falls_back_to_deterministic_visual(tmp_path: Path):
    from backend.zhifei_autoplan.semantic_image_enhancer import build_semantic_image_item

    png_path = tmp_path / "section-visual.png"
    png_path.write_bytes(b"fake-image")

    with patch(
        "backend.zhifei_autoplan.media.generate_section_visuals",
        return_value=[{"path": str(png_path), "caption": "施工部署控制要点图（含量化指标）"}],
    ):
        item = build_semantic_image_item(
            title="施工部署",
            content="本章重点控制塔吊交叉作业、脚手架搭设和临时用电管理。",
            topic="房建厂房项目",
            image_slots=[],
            workspace_dir=str(tmp_path),
        )

    assert isinstance(item, dict)
    assert item["source_mode"] == "deterministic_section_visual"
    assert item["source_path"] == str(png_path)
    assert item["caption"] == "施工部署控制要点图（含量化指标）"
    assert item["tags"]
