#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: compose_engine.py
验证 Composer 类的基础功能。
"""

import sys
from pathlib import Path

# 确保 backend 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from compose_engine import Composer


class TestComposer:
    """测试 Composer 类"""

    def test_compose_returns_dict(self):
        """测试 compose 方法返回字典"""
        composer = Composer()
        result = composer.compose(topic="测试主题", outline=["章节1", "章节2"])
        assert isinstance(result, dict)

    def test_compose_has_required_keys(self):
        """测试 compose 返回结果包含必要字段"""
        composer = Composer()
        result = composer.compose(topic="测试主题", outline=["章节1"])
        required_keys = {"topic", "outline", "sections", "style", "saved_at"}
        assert required_keys.issubset(result.keys())

    def test_compose_topic_matches_input(self):
        """测试 topic 字段与输入一致"""
        composer = Composer()
        topic = "建筑工程施工组织设计"
        result = composer.compose(topic=topic, outline=["工程概况"])
        assert result["topic"] == topic

    def test_compose_outline_matches_input(self):
        """测试 outline 字段与输入一致"""
        composer = Composer()
        outline = ["工程概况", "施工准备", "质量管理"]
        result = composer.compose(topic="测试", outline=outline)
        assert result["outline"] == outline

    def test_compose_sections_is_list(self):
        """测试 sections 是列表"""
        composer = Composer()
        result = composer.compose(topic="测试", outline=["章节1"])
        assert isinstance(result["sections"], list)

    def test_compose_sections_have_title_and_content(self):
        """测试每个 section 包含 title 和 content"""
        composer = Composer()
        result = composer.compose(topic="测试", outline=["章节1"])
        for section in result["sections"]:
            assert "title" in section
            assert "content" in section

    def test_compose_style_has_font(self):
        """测试 style 包含 font 字段"""
        composer = Composer()
        result = composer.compose(topic="测试", outline=["章节1"])
        assert "font" in result["style"]

    def test_compose_saved_at_is_build_path(self):
        """测试 saved_at 指向 build 目录"""
        composer = Composer()
        result = composer.compose(topic="测试", outline=["章节1"])
        assert result["saved_at"].startswith("build/")

    def test_compose_max_pages_param_accepted(self):
        """测试 max_pages 参数被接受"""
        composer = Composer()
        # 只验证不抛出异常
        result = composer.compose(topic="测试", outline=["章节1"], max_pages=100)
        assert result is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
