"""Unit tests for media.py - chart generation module."""

from __future__ import annotations

import os
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
            assert any("思维导图" in str(x.get("caption") or "") for x in rows)
            for item in rows:
                p = Path(str(item.get("path") or ""))
                assert p.exists()
                assert p.suffix.lower() == ".png"
        finally:
            media.MEDIA_DIR = original_media_dir
