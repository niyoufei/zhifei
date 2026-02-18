"""
Unit tests for backend/zhifei_autoplan/boq_store.py
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSaveBoqData:
    """Tests for save_boq_data function."""

    def test_save_simple_dict(self, tmp_path):
        """Test saving a simple dictionary."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {"key": "value", "count": 123}
            result = boq_store.save_boq_data(payload)
            
            assert result == str(test_file)
            assert test_file.exists()
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_nested_dict(self, tmp_path):
        """Test saving a nested dictionary."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {
                "project": "test",
                "items": [
                    {"name": "item1", "qty": 10},
                    {"name": "item2", "qty": 20}
                ],
                "meta": {"version": 1}
            }
            boq_store.save_boq_data(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_chinese_content(self, tmp_path):
        """Test saving Chinese characters (ensure_ascii=False)."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {
                "项目名称": "施工组织设计",
                "工程量清单": [
                    {"名称": "混凝土浇筑", "单位": "立方米", "数量": 100}
                ]
            }
            boq_store.save_boq_data(payload)
            
            content = test_file.read_text(encoding="utf-8")
            # Chinese characters should NOT be escaped
            assert "项目名称" in content
            assert "\\u" not in content  # No unicode escapes

    def test_save_empty_dict(self, tmp_path):
        """Test saving an empty dictionary."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            boq_store.save_boq_data({})
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == {}

    def test_save_overwrites_existing(self, tmp_path):
        """Test that save overwrites existing file."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        test_file.write_text('{"old": "data"}', encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            boq_store.save_boq_data({"new": "data"})
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == {"new": "data"}
            assert "old" not in saved

    def test_save_with_special_chars(self, tmp_path):
        """Test saving content with special characters."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {
                "quotes": 'He said "hello"',
                "newlines": "line1\nline2",
                "tabs": "col1\tcol2",
                "backslash": "path\\to\\file"
            }
            boq_store.save_boq_data(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_with_numbers(self, tmp_path):
        """Test saving various number types."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {
                "integer": 42,
                "float": 3.14159,
                "negative": -100,
                "zero": 0,
                "scientific": 1.5e10
            }
            boq_store.save_boq_data(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved["integer"] == 42
            assert saved["float"] == pytest.approx(3.14159)
            assert saved["negative"] == -100

    def test_save_with_boolean_null(self, tmp_path):
        """Test saving boolean and null values."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            payload = {
                "active": True,
                "deleted": False,
                "value": None
            }
            boq_store.save_boq_data(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved["active"] is True
            assert saved["deleted"] is False
            assert saved["value"] is None


class TestLoadBoqData:
    """Tests for load_boq_data function."""

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        expected = {"key": "value", "count": 123}
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result == expected

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file returns None."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "nonexistent.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result is None

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        test_file.write_text("not valid json {", encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result is None

    def test_load_empty_file(self, tmp_path):
        """Test loading empty file returns None."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        test_file.write_text("", encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result is None

    def test_load_chinese_content(self, tmp_path):
        """Test loading Chinese content."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        expected = {"项目": "测试", "描述": "中文内容"}
        test_file.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result == expected
            assert result["项目"] == "测试"

    def test_load_nested_structure(self, tmp_path):
        """Test loading nested data structure."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        expected = {
            "project": "test",
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"}
            ],
            "config": {"nested": {"deep": True}}
        }
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result == expected
            assert result["items"][0]["id"] == 1
            assert result["config"]["nested"]["deep"] is True

    def test_load_array_json(self, tmp_path):
        """Test loading JSON array (not dict)."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        expected = [1, 2, 3, "test"]
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result == expected

    def test_load_empty_dict(self, tmp_path):
        """Test loading empty dictionary."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        test_file.write_text("{}", encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result == {}

    def test_load_json_null(self, tmp_path):
        """Test loading JSON null."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        test_file.write_text("null", encoding="utf-8")
        
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            result = boq_store.load_boq_data()
            assert result is None


class TestSaveAndLoad:
    """Integration tests for save then load."""

    def test_roundtrip_simple(self, tmp_path):
        """Test save then load returns same data."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            original = {"key": "value", "number": 42}
            boq_store.save_boq_data(original)
            loaded = boq_store.load_boq_data()
            assert loaded == original

    def test_roundtrip_complex(self, tmp_path):
        """Test roundtrip with complex structure."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            original = {
                "project": "施工组织设计",
                "items": [
                    {"name": "混凝土", "qty": 100.5, "unit": "m³"},
                    {"name": "钢筋", "qty": 50, "unit": "t"}
                ],
                "flags": {"urgent": True, "reviewed": False},
                "notes": None
            }
            boq_store.save_boq_data(original)
            loaded = boq_store.load_boq_data()
            assert loaded == original

    def test_multiple_saves(self, tmp_path):
        """Test multiple saves keep only last data."""
        from backend.zhifei_autoplan import boq_store
        
        test_file = tmp_path / "boq_data.json"
        with patch.object(boq_store, 'BOQ_DATA', test_file):
            boq_store.save_boq_data({"version": 1})
            boq_store.save_boq_data({"version": 2})
            boq_store.save_boq_data({"version": 3})
            
            loaded = boq_store.load_boq_data()
            assert loaded == {"version": 3}


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_boq_dir_is_path(self):
        """Test BOQ_DIR is a Path object."""
        from backend.zhifei_autoplan import boq_store
        assert isinstance(boq_store.BOQ_DIR, Path)

    def test_boq_data_is_path(self):
        """Test BOQ_DATA is a Path object."""
        from backend.zhifei_autoplan import boq_store
        assert isinstance(boq_store.BOQ_DATA, Path)

    def test_boq_data_is_in_boq_dir(self):
        """Test BOQ_DATA is inside BOQ_DIR."""
        from backend.zhifei_autoplan import boq_store
        assert boq_store.BOQ_DATA.parent == boq_store.BOQ_DIR

    def test_boq_data_filename(self):
        """Test BOQ_DATA has correct filename."""
        from backend.zhifei_autoplan import boq_store
        assert boq_store.BOQ_DATA.name == "boq_data.json"
