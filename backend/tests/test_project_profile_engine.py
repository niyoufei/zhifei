#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: project_profile_engine.py
验证 ProjectProfileEngine 类的基础功能。
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 确保 backend 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_profile_engine import ProjectProfileEngine


class TestProjectProfileEngine:
    """测试 ProjectProfileEngine 类"""

    def test_init_loads_rules(self):
        """测试初始化成功加载规则"""
        engine = ProjectProfileEngine()
        assert engine.rules is not None

    def test_rules_is_dict(self):
        """测试 rules 是字典类型"""
        engine = ProjectProfileEngine()
        assert isinstance(engine.rules, dict)

    def test_rule_path_is_path_object(self):
        """测试 rule_path 是 Path 对象"""
        engine = ProjectProfileEngine()
        assert isinstance(engine.rule_path, Path)

    def test_rule_path_exists(self):
        """测试规则文件确实存在"""
        engine = ProjectProfileEngine()
        assert engine.rule_path.exists()

    def test_debug_summary_returns_dict(self):
        """测试 debug_summary 返回字典"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        assert isinstance(summary, dict)

    def test_debug_summary_has_required_keys(self):
        """测试 debug_summary 包含必要字段"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        required_keys = {"rule_path", "meta", "strategy_keys", "strategy_source", "rule_top_keys"}
        assert required_keys.issubset(summary.keys())

    def test_debug_summary_rule_path_is_string(self):
        """测试 debug_summary 中 rule_path 是字符串"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        assert isinstance(summary["rule_path"], str)

    def test_debug_summary_meta_is_dict(self):
        """测试 debug_summary 中 meta 是字典"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        assert isinstance(summary["meta"], dict)

    def test_debug_summary_strategy_keys_is_list(self):
        """测试 debug_summary 中 strategy_keys 是列表"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        assert isinstance(summary["strategy_keys"], list)

    def test_debug_summary_rule_top_keys_is_list(self):
        """测试 debug_summary 中 rule_top_keys 是列表"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        assert isinstance(summary["rule_top_keys"], list)

    def test_debug_summary_strategy_keys_sorted(self):
        """测试 strategy_keys 是排序后的列表"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        keys = summary["strategy_keys"]
        assert keys == sorted(keys)

    def test_debug_summary_rule_top_keys_sorted(self):
        """测试 rule_top_keys 是排序后的列表"""
        engine = ProjectProfileEngine()
        summary = engine.debug_summary()
        keys = summary["rule_top_keys"]
        assert keys == sorted(keys)


class TestProjectProfileEngineEdgeCases:
    """测试 ProjectProfileEngine 边界情况"""

    def test_load_rules_file_not_found(self, tmp_path):
        """测试当规则文件不存在时抛出 FileNotFoundError"""
        non_existent_path = tmp_path / "non_existent.json"
        
        with patch("project_profile_engine.get_project_profile_rule_path", return_value=non_existent_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                ProjectProfileEngine()
            assert "Project profile rule file not found" in str(exc_info.value)
            assert str(non_existent_path) in str(exc_info.value)

    def test_debug_summary_no_strategy_key(self, tmp_path):
        """测试规则文件没有 strategy 字段时使用 fallback"""
        rule_file = tmp_path / "test_rules.json"
        rule_file.write_text('{"meta": {"version": "1.0"}, "key1": "value1", "key2": "value2"}', encoding="utf-8")
        
        with patch("project_profile_engine.get_project_profile_rule_path", return_value=rule_file):
            engine = ProjectProfileEngine()
            summary = engine.debug_summary()
            
            assert summary["strategy_source"] == "top_level_keys_fallback"
            assert "key1" in summary["strategy_keys"]
            assert "key2" in summary["strategy_keys"]
            assert "meta" not in summary["strategy_keys"]  # meta 应该被排除

    def test_debug_summary_empty_strategy(self, tmp_path):
        """测试规则文件 strategy 为空字典时使用 fallback"""
        rule_file = tmp_path / "test_rules.json"
        rule_file.write_text('{"meta": {}, "strategy": {}, "other_key": "value"}', encoding="utf-8")
        
        with patch("project_profile_engine.get_project_profile_rule_path", return_value=rule_file):
            engine = ProjectProfileEngine()
            summary = engine.debug_summary()
            
            assert summary["strategy_source"] == "top_level_keys_fallback"
            assert "other_key" in summary["strategy_keys"]
            assert "strategy" in summary["strategy_keys"]

    def test_debug_summary_strategy_is_not_dict(self, tmp_path):
        """测试规则文件 strategy 不是字典类型时使用 fallback"""
        rule_file = tmp_path / "test_rules.json"
        rule_file.write_text('{"meta": {}, "strategy": ["item1", "item2"], "key3": "v3"}', encoding="utf-8")
        
        with patch("project_profile_engine.get_project_profile_rule_path", return_value=rule_file):
            engine = ProjectProfileEngine()
            summary = engine.debug_summary()
            
            assert summary["strategy_source"] == "top_level_keys_fallback"
            assert "key3" in summary["strategy_keys"]
            assert "strategy" in summary["strategy_keys"]

    def test_debug_summary_with_valid_strategy(self, tmp_path):
        """测试规则文件有有效 strategy 字典时正常使用"""
        rule_file = tmp_path / "test_rules.json"
        rule_file.write_text('{"meta": {}, "strategy": {"plan_a": {}, "plan_b": {}}}', encoding="utf-8")
        
        with patch("project_profile_engine.get_project_profile_rule_path", return_value=rule_file):
            engine = ProjectProfileEngine()
            summary = engine.debug_summary()
            
            assert summary["strategy_source"] == "rules.strategy"
            assert summary["strategy_keys"] == ["plan_a", "plan_b"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
