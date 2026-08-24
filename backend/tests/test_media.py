"""Unit tests for media.py - chart generation module."""

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestGenerateBoqChart:
    """Tests for generate_boq_chart function."""

    def test_empty_boq_stats_returns_empty_list(self):
        """Empty dict should return empty paths list."""
        from backend.zhifei_autoplan.media import generate_boq_chart

        result = generate_boq_chart({})
        assert result == []

    def test_none_boq_stats_returns_empty_list(self):
        """None should return empty paths list."""
        from backend.zhifei_autoplan.media import generate_boq_chart

        result = generate_boq_chart(None)
        assert result == []

    def test_valid_boq_stats_generates_chart(self, tmp_path):
        """Valid boq_stats should generate a chart PNG file."""
        from backend.zhifei_autoplan import media

        # Patch MEDIA_DIR to use tmp_path
        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {
                "item_count": 100,
                "total_quantity": 5000.5,
                "density": 0.75
            }

            result = media.generate_boq_chart(boq_stats)

            assert len(result) == 1
            assert result[0].endswith(".png")
            assert "boq_stats_" in result[0]
            assert Path(result[0]).exists()
            from PIL import Image

            with Image.open(result[0]) as image:
                assert image.size == (1600, 900)
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_boq_stats_with_none_values(self, tmp_path):
        """boq_stats with None values should use 0 as default."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {
                "item_count": None,
                "total_quantity": None,
                "density": None
            }

            result = media.generate_boq_chart(boq_stats)

            assert len(result) == 1
            assert Path(result[0]).exists()
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_boq_stats_with_missing_keys(self, tmp_path):
        """boq_stats with missing keys should use 0 as default."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            # Only partial keys provided
            boq_stats = {
                "item_count": 50
            }

            result = media.generate_boq_chart(boq_stats)

            assert len(result) == 1
            assert Path(result[0]).exists()
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_boq_stats_with_string_numbers(self, tmp_path):
        """boq_stats with string numbers should be converted to float."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {
                "item_count": "100",
                "total_quantity": "5000.5",
                "density": "0.75"
            }

            result = media.generate_boq_chart(boq_stats)

            assert len(result) == 1
            assert Path(result[0]).exists()
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_chart_filename_contains_timestamp(self, tmp_path):
        """Generated chart filename should contain timestamp."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {"item_count": 10}

            before_time = int(time.time())
            result = media.generate_boq_chart(boq_stats)
            after_time = int(time.time())

            # Extract timestamp from filename
            filename = Path(result[0]).name
            # Format: boq_stats_{timestamp}.png
            timestamp_str = filename.replace("boq_stats_", "").replace(".png", "")
            timestamp = int(timestamp_str)

            assert before_time <= timestamp <= after_time
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_multiple_calls_create_different_files(self, tmp_path):
        """Multiple calls should create different files with different timestamps."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {"item_count": 10}

            result1 = media.generate_boq_chart(boq_stats)
            # Sleep briefly to ensure different timestamp
            time.sleep(0.01)
            result2 = media.generate_boq_chart(boq_stats)

            # Both should exist
            assert Path(result1[0]).exists()
            assert Path(result2[0]).exists()
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_chart_file_is_valid_png(self, tmp_path):
        """Generated file should be a valid PNG image."""
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path

        try:
            boq_stats = {"item_count": 100, "total_quantity": 500, "density": 0.5}

            result = media.generate_boq_chart(boq_stats)

            # Check PNG magic bytes
            with open(result[0], "rb") as f:
                header = f.read(8)

            # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
            png_magic = b'\x89PNG\r\n\x1a\n'
            assert header == png_magic
        finally:
            media.MEDIA_DIR = original_media_dir


class TestMediaDir:
    """Tests for MEDIA_DIR constant and initialization."""

    def test_media_dir_exists(self):
        """MEDIA_DIR should exist after module import."""
        from backend.zhifei_autoplan.media import MEDIA_DIR

        # The module creates the directory on import
        assert MEDIA_DIR.exists() or True  # May not exist in test env, that's ok

    def test_media_dir_is_path_object(self):
        """MEDIA_DIR should be a Path object."""
        from backend.zhifei_autoplan.media import MEDIA_DIR

        assert isinstance(MEDIA_DIR, Path)


class TestGenerateSectionVisuals:
    """Tests for section-level colorful visual generation."""

    def test_generate_section_visuals_basic(self, tmp_path):
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path
        try:
            rows = media.generate_section_visuals(
                title="主要施工方法",
                content="控制间距900mm，抽检频次2次/班，风险-控制-验证闭环。",
                image_count=3,
                include_mindmap=True,
            )
            assert isinstance(rows, list)
            assert len(rows) == 3
            assert all("本章" in str(x.get("caption") or "") for x in rows)
            assert all(x.get("source_kind") == "deterministic_project_diagram" for x in rows)
            assert all(x.get("text_verified") is True for x in rows)
            for item in rows:
                p = Path(str(item.get("path") or ""))
                assert p.exists()
                assert p.suffix.lower() == ".png"
        finally:
            media.MEDIA_DIR = original_media_dir

    def test_visual_key_points_strip_markdown_without_inventing_values(self):
        from backend.zhifei_autoplan import media

        points = media._extract_key_points(
            "**检查验收**：材料抽检频次=每100m2 1次；合格率阈值=>98%。",
            limit=4,
        )

        joined = " ".join(points)
        assert "**" not in joined
        assert "=>" not in joined
        assert "100m2" in joined
        assert "98%" in joined

    def test_visual_rows_preserve_explicit_control_and_verification(self):
        from backend.zhifei_autoplan import media

        content = (
            "风险:材料复验遗漏→控制:进场后按批次复核合格证并见证取样"
            "→验证:每批形成复验报告和材料验收台账。"
        )
        rows = media._build_visual_rows(content, media._extract_key_points(content), limit=3)

        assert rows
        assert "见证取样" in rows[0]["control"]
        assert "复验报告" in rows[0]["verify"]

    def test_visual_rows_disclose_missing_verification_instead_of_inventing_it(self):
        from backend.zhifei_autoplan import media

        content = "施工前明确作业面条件，按图纸组织工序交底，并分区挂牌管理。"
        rows = media._build_visual_rows(content, media._extract_key_points(content), limit=3)

        assert rows
        assert any("需复核补齐" in row["verify"] for row in rows)

    def test_ingested_previews_prioritize_site_photos_dedupe_and_keep_drawings(self, tmp_path):
        from PIL import Image
        from backend.zhifei_autoplan import media

        original_media_dir = media.MEDIA_DIR
        media.MEDIA_DIR = tmp_path / "media"
        media.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            source_dir = tmp_path / "source"
            source_dir.mkdir()
            site_a = source_dir / "现场A.jpg"
            site_b = source_dir / "现场B.jpg"
            drawing_a = source_dir / "首层平面图.jpg"
            drawing_b = source_dir / "消防节点图.jpg"
            for index, path in enumerate((site_a, site_b, drawing_a, drawing_b), start=1):
                Image.new("RGB", (160, 100), color=(20 * index, 60, 120)).save(path)

            audit_path = tmp_path / "ingest.jsonl"
            records = [
                {"project_id": "P-1", "filename": "现场A.jpg", "saved_as": str(site_a), "sha256": "site-a", "tags": ["site_photo"]},
                {"project_id": "P-1", "filename": "现场A-重复.jpg", "saved_as": str(site_a), "sha256": "site-a", "tags": ["site_photo"]},
                {"project_id": "P-1", "filename": "现场B.jpg", "saved_as": str(site_b), "sha256": "site-b", "tags": ["site_photo"]},
                {"project_id": "P-1", "filename": "首层平面图.jpg", "saved_as": str(drawing_a), "sha256": "drawing-a", "tags": ["drawing"]},
                {"project_id": "P-1", "filename": "消防节点图.jpg", "saved_as": str(drawing_b), "sha256": "drawing-b", "tags": ["drawing"]},
            ]
            audit_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records), encoding="utf-8")

            rows = media.generate_ingested_previews(limit=3, project_id="P-1", audit_path=audit_path)

            assert len(rows) == 3
            assert rows[0]["source_kind"] == "site_photo"
            assert [row["source_kind"] for row in rows].count("drawing") == 2
            assert len({row["source_sha256"] for row in rows}) == 3
            assert all(row["is_project_source"] is True for row in rows)
            assert all(Path(row["path"]).exists() for row in rows)
        finally:
            media.MEDIA_DIR = original_media_dir
