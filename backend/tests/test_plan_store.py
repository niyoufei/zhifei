"""
Unit tests for backend/zhifei_autoplan/plan_store.py
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSavePlan:
    """Tests for save_plan function."""

    def test_save_simple_dict(self, tmp_path):
        """Test saving a simple dictionary."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {"key": "value", "count": 123}
            result = plan_store.save_plan(payload)
            
            assert result == str(test_file)
            assert test_file.exists()
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_nested_dict(self, tmp_path):
        """Test saving a nested dictionary."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "project": "test",
                "phases": [
                    {"name": "phase1", "duration": 10},
                    {"name": "phase2", "duration": 20}
                ],
                "meta": {"version": 1}
            }
            plan_store.save_plan(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_chinese_content(self, tmp_path):
        """Test saving Chinese characters (ensure_ascii=False)."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "项目名称": "施工组织设计",
                "施工计划": [
                    {"阶段": "准备阶段", "工期": "30天"},
                    {"阶段": "施工阶段", "工期": "180天"}
                ]
            }
            plan_store.save_plan(payload)
            
            content = test_file.read_text(encoding="utf-8")
            # Chinese characters should NOT be escaped
            assert "项目名称" in content
            assert "施工组织设计" in content
            assert "\\u" not in content  # No unicode escapes

    def test_save_empty_dict(self, tmp_path):
        """Test saving an empty dictionary."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            plan_store.save_plan({})
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == {}

    def test_save_overwrites_existing(self, tmp_path):
        """Test that save overwrites existing file."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text('{"old": "data"}', encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            plan_store.save_plan({"new": "data"})
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == {"new": "data"}
            assert "old" not in saved

    def test_save_with_special_chars(self, tmp_path):
        """Test saving content with special characters."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "quotes": 'He said "hello"',
                "newlines": "line1\nline2",
                "tabs": "col1\tcol2",
                "backslash": "path\\to\\file"
            }
            plan_store.save_plan(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload

    def test_save_with_numbers(self, tmp_path):
        """Test saving various number types."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "integer": 42,
                "float": 3.14159,
                "negative": -100,
                "zero": 0,
                "scientific": 1.5e10
            }
            plan_store.save_plan(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved["integer"] == 42
            assert saved["float"] == pytest.approx(3.14159)
            assert saved["negative"] == -100

    def test_save_with_boolean_null(self, tmp_path):
        """Test saving boolean and null values."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "active": True,
                "deleted": False,
                "value": None
            }
            plan_store.save_plan(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved["active"] is True
            assert saved["deleted"] is False
            assert saved["value"] is None

    def test_save_plan_structure(self, tmp_path):
        """Test saving a realistic plan structure."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            payload = {
                "project_id": "PRJ-001",
                "name": "城市道路施工",
                "start_date": "2026-03-01",
                "end_date": "2026-12-31",
                "phases": [
                    {
                        "id": 1,
                        "name": "前期准备",
                        "duration_days": 30,
                        "tasks": ["场地清理", "测量放线", "临时设施"]
                    },
                    {
                        "id": 2,
                        "name": "主体施工",
                        "duration_days": 180,
                        "tasks": ["路基施工", "路面铺设", "排水系统"]
                    }
                ],
                "resources": {
                    "labor": 50,
                    "equipment": ["挖掘机", "压路机", "摊铺机"]
                }
            }
            plan_store.save_plan(payload)
            
            saved = json.loads(test_file.read_text(encoding="utf-8"))
            assert saved == payload
            assert len(saved["phases"]) == 2
            assert saved["resources"]["labor"] == 50


class TestLoadPlan:
    """Tests for load_plan function."""

    def test_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        expected = {"key": "value", "count": 123}
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result == expected

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file returns None."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "nonexistent.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result is None

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text("not valid json {", encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result is None

    def test_load_empty_file(self, tmp_path):
        """Test loading empty file returns None."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text("", encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result is None

    def test_load_chinese_content(self, tmp_path):
        """Test loading Chinese content."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        expected = {"项目": "测试", "描述": "中文施工计划"}
        test_file.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result == expected
            assert result["项目"] == "测试"

    def test_load_nested_structure(self, tmp_path):
        """Test loading nested data structure."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        expected = {
            "project": "test",
            "phases": [
                {"id": 1, "name": "phase1"},
                {"id": 2, "name": "phase2"}
            ],
            "config": {"nested": {"deep": True}}
        }
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result == expected
            assert result["phases"][0]["id"] == 1
            assert result["config"]["nested"]["deep"] is True

    def test_load_array_json(self, tmp_path):
        """Test loading JSON array (not dict)."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        expected = [1, 2, 3, "test"]
        test_file.write_text(json.dumps(expected), encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result == expected

    def test_load_empty_dict(self, tmp_path):
        """Test loading empty dictionary."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text("{}", encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result == {}

    def test_load_json_null(self, tmp_path):
        """Test loading JSON null."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text("null", encoding="utf-8")
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result is None

    def test_load_truncated_json(self, tmp_path):
        """Test loading truncated JSON returns None."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        test_file.write_text('{"key": "value"', encoding="utf-8")  # Missing closing brace
        
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            result = plan_store.load_plan()
            assert result is None


class TestSaveAndLoad:
    """Integration tests for save then load."""

    def test_roundtrip_simple(self, tmp_path):
        """Test save then load returns same data."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            original = {"key": "value", "number": 42}
            plan_store.save_plan(original)
            loaded = plan_store.load_plan()
            assert loaded == original

    def test_roundtrip_complex(self, tmp_path):
        """Test roundtrip with complex structure."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            original = {
                "project": "施工组织设计",
                "phases": [
                    {"name": "准备", "days": 30, "cost": 100000.50},
                    {"name": "施工", "days": 180, "cost": 5000000}
                ],
                "flags": {"urgent": True, "reviewed": False},
                "notes": None
            }
            plan_store.save_plan(original)
            loaded = plan_store.load_plan()
            assert loaded == original

    def test_multiple_saves(self, tmp_path):
        """Test multiple saves keep only last data."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            plan_store.save_plan({"version": 1})
            plan_store.save_plan({"version": 2})
            plan_store.save_plan({"version": 3})
            
            loaded = plan_store.load_plan()
            assert loaded == {"version": 3}

    def test_roundtrip_realistic_plan(self, tmp_path):
        """Test roundtrip with realistic plan data."""
        from backend.zhifei_autoplan import plan_store
        
        test_file = tmp_path / "plan.json"
        with patch.object(plan_store, 'PLAN_PATH', test_file):
            original = {
                "project_id": "PRJ-2026-001",
                "name": "谭岗路排水附属工程",
                "total_duration": 365,
                "phases": [
                    {
                        "id": 1,
                        "name": "施工准备",
                        "start": 0,
                        "end": 30,
                        "tasks": [
                            {"name": "场地清理", "days": 10},
                            {"name": "测量放线", "days": 5},
                            {"name": "临建搭设", "days": 15}
                        ]
                    },
                    {
                        "id": 2,
                        "name": "管道施工",
                        "start": 30,
                        "end": 200,
                        "tasks": [
                            {"name": "沟槽开挖", "days": 60},
                            {"name": "管道安装", "days": 80},
                            {"name": "回填夯实", "days": 30}
                        ]
                    }
                ],
                "milestones": ["开工", "管道贯通", "竣工"],
                "resources": {
                    "人员": 30,
                    "机械": ["挖掘机", "吊车", "压路机"],
                    "材料预算": 2500000
                }
            }
            plan_store.save_plan(original)
            loaded = plan_store.load_plan()
            assert loaded == original


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_plan_dir_is_path(self):
        """Test PLAN_DIR is a Path object."""
        from backend.zhifei_autoplan import plan_store
        assert isinstance(plan_store.PLAN_DIR, Path)

    def test_plan_path_is_path(self):
        """Test PLAN_PATH is a Path object."""
        from backend.zhifei_autoplan import plan_store
        assert isinstance(plan_store.PLAN_PATH, Path)

    def test_plan_path_is_in_plan_dir(self):
        """Test PLAN_PATH is inside PLAN_DIR."""
        from backend.zhifei_autoplan import plan_store
        assert plan_store.PLAN_PATH.parent == plan_store.PLAN_DIR

    def test_plan_path_filename(self):
        """Test PLAN_PATH has correct filename."""
        from backend.zhifei_autoplan import plan_store
        assert plan_store.PLAN_PATH.name == "plan.json"
