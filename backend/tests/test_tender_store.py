"""Unit tests for backend/zhifei_autoplan/tender_store.py"""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from backend.zhifei_autoplan import tender_store
from backend.zhifei_autoplan.tender_store import (
    save_tender_matrix,
    load_tender_matrix,
    TENDER_DIR,
    TENDER_MATRIX,
)


class TestModuleConstants:
    """Test module-level constants."""

    def test_tender_dir_is_path(self):
        """TENDER_DIR should be a Path instance."""
        assert isinstance(TENDER_DIR, Path)

    def test_tender_matrix_is_path(self):
        """TENDER_MATRIX should be a Path instance."""
        assert isinstance(TENDER_MATRIX, Path)

    def test_tender_matrix_in_tender_dir(self):
        """TENDER_MATRIX should be inside TENDER_DIR."""
        assert TENDER_MATRIX.parent == TENDER_DIR

    def test_tender_matrix_filename(self):
        """TENDER_MATRIX filename should be tender_matrix.json."""
        assert TENDER_MATRIX.name == "tender_matrix.json"


class TestSaveTenderMatrix:
    """Tests for save_tender_matrix function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_save_returns_path_string(self, temp_dir):
        """save_tender_matrix should return the file path as string."""
        temp_file = temp_dir / "tender_matrix.json"
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = save_tender_matrix({"key": "value"})
            assert isinstance(result, str)
            assert result == str(temp_file)

    def test_save_creates_file(self, temp_dir):
        """save_tender_matrix should create the JSON file."""
        temp_file = temp_dir / "tender_matrix.json"
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix({"test": "data"})
            assert temp_file.exists()

    def test_save_writes_valid_json(self, temp_dir):
        """save_tender_matrix should write valid JSON content."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {"items": [1, 2, 3], "nested": {"a": "b"}}
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = json.loads(temp_file.read_text(encoding="utf-8"))
            assert loaded == matrix

    def test_save_empty_dict(self, temp_dir):
        """save_tender_matrix should handle empty dictionary."""
        temp_file = temp_dir / "tender_matrix.json"
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix({})
            loaded = json.loads(temp_file.read_text(encoding="utf-8"))
            assert loaded == {}

    def test_save_chinese_characters(self, temp_dir):
        """save_tender_matrix should preserve Chinese characters."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {"项目名称": "招标文件", "描述": "中文测试"}
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            content = temp_file.read_text(encoding="utf-8")
            assert "招标文件" in content
            assert "中文测试" in content

    def test_save_overwrites_existing(self, temp_dir):
        """save_tender_matrix should overwrite existing file."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text('{"old": "data"}', encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix({"new": "data"})
            loaded = json.loads(temp_file.read_text(encoding="utf-8"))
            assert loaded == {"new": "data"}
            assert "old" not in loaded

    def test_save_complex_nested_structure(self, temp_dir):
        """save_tender_matrix should handle complex nested structures."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"]
                }
            },
            "array": [{"x": 1}, {"y": 2}]
        }
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = json.loads(temp_file.read_text(encoding="utf-8"))
            assert loaded == matrix

    def test_save_with_special_characters(self, temp_dir):
        """save_tender_matrix should handle special characters."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {"special": "quotes\"and\\backslash", "newline": "line1\nline2"}
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = json.loads(temp_file.read_text(encoding="utf-8"))
            assert loaded == matrix


class TestLoadTenderMatrix:
    """Tests for load_tender_matrix function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_load_returns_dict_when_exists(self, temp_dir):
        """load_tender_matrix should return dict when file exists."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text('{"key": "value"}', encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert isinstance(result, dict)
            assert result == {"key": "value"}

    def test_load_returns_none_when_not_exists(self, temp_dir):
        """load_tender_matrix should return None when file doesn't exist."""
        temp_file = temp_dir / "nonexistent.json"
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result is None

    def test_load_returns_none_on_invalid_json(self, temp_dir):
        """load_tender_matrix should return None on invalid JSON."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text("this is not valid json", encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result is None

    def test_load_returns_none_on_empty_file(self, temp_dir):
        """load_tender_matrix should return None on empty file."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text("", encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result is None

    def test_load_empty_dict(self, temp_dir):
        """load_tender_matrix should load empty dictionary."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text("{}", encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result == {}

    def test_load_chinese_characters(self, temp_dir):
        """load_tender_matrix should correctly load Chinese characters."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {"项目": "测试", "内容": "中文"}
        temp_file.write_text(json.dumps(matrix, ensure_ascii=False), encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result == matrix

    def test_load_complex_structure(self, temp_dir):
        """load_tender_matrix should load complex nested structures."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {
            "items": [1, 2, 3],
            "nested": {"deep": {"value": True}},
            "mixed": [{"a": 1}, "string", 123]
        }
        temp_file.write_text(json.dumps(matrix), encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result == matrix

    def test_load_handles_truncated_json(self, temp_dir):
        """load_tender_matrix should return None on truncated JSON."""
        temp_file = temp_dir / "tender_matrix.json"
        temp_file.write_text('{"key": "incomplete', encoding="utf-8")
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            result = load_tender_matrix()
            assert result is None


class TestRoundtrip:
    """Tests for save/load roundtrip operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_roundtrip_simple(self, temp_dir):
        """Data should survive save/load roundtrip."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {"test": "data", "number": 42}
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = load_tender_matrix()
            assert loaded == matrix

    def test_roundtrip_chinese(self, temp_dir):
        """Chinese characters should survive save/load roundtrip."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {
            "招标文件": "标书内容",
            "项目列表": ["子项1", "子项2"],
            "详细信息": {"单位": "平方米", "数量": 100}
        }
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = load_tender_matrix()
            assert loaded == matrix

    def test_roundtrip_complex(self, temp_dir):
        """Complex nested structures should survive roundtrip."""
        temp_file = temp_dir / "tender_matrix.json"
        matrix = {
            "sections": [
                {"id": 1, "name": "Section A", "items": [{"x": 1}, {"x": 2}]},
                {"id": 2, "name": "Section B", "items": [{"y": 3}]}
            ],
            "metadata": {
                "version": "1.0",
                "encoding": "utf-8",
                "flags": {"draft": True, "reviewed": False}
            }
        }
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix(matrix)
            loaded = load_tender_matrix()
            assert loaded == matrix

    def test_multiple_saves_overwrite(self, temp_dir):
        """Multiple saves should overwrite previous content."""
        temp_file = temp_dir / "tender_matrix.json"
        with patch.object(tender_store, "TENDER_MATRIX", temp_file):
            save_tender_matrix({"version": 1})
            save_tender_matrix({"version": 2})
            save_tender_matrix({"version": 3})
            loaded = load_tender_matrix()
            assert loaded == {"version": 3}
