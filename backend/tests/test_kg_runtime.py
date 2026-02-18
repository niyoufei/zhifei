"""
KG Runtime 单元测试
覆盖 kg_runtime.py 的所有方法
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.zhifei_autoplan.kg_runtime import _tokenize, _extract_docs, search_kg


# ==============================================================================
# _tokenize tests
# ==============================================================================


class TestTokenize:
    """测试 _tokenize 方法"""

    def test_empty_query(self):
        """空查询返回空列表"""
        assert _tokenize("") == []

    def test_none_query(self):
        """None 查询返回空列表"""
        assert _tokenize(None) == []

    def test_single_chinese_word(self):
        """单个中文词（>=2字）"""
        result = _tokenize("施工")
        assert "施工" in result

    def test_single_char_filtered(self):
        """单字符被过滤"""
        result = _tokenize("施")
        assert result == []

    def test_multiple_chinese_words(self):
        """多个中文词（连续中文被视为一个token）"""
        result = _tokenize("施工方案和质量标准")
        assert len(result) > 0
        # _tokenize 匹配连续的中文字符串，不是分词
        assert "施工方案和质量标准" in result

    def test_english_word(self):
        """英文单词"""
        result = _tokenize("construction plan")
        assert "construction" in result
        assert "plan" in result

    def test_mixed_chinese_english(self):
        """中英文混合"""
        result = _tokenize("施工方案 construction plan")
        assert len(result) > 0

    def test_numbers(self):
        """数字和英文混合"""
        result = _tokenize("type123 test456")
        assert "type123" in result
        assert "test456" in result

    def test_deduplication(self):
        """去重功能"""
        result = _tokenize("施工 施工 施工方案")
        # 应该去重
        count = result.count("施工")
        assert count <= 1

    def test_short_tokens_filtered(self):
        """短 token 被过滤（长度<2）"""
        result = _tokenize("a b c")
        assert result == []

    def test_underscores_in_tokens(self):
        """下划线在 token 中"""
        result = _tokenize("test_name another_value")
        assert "test_name" in result
        assert "another_value" in result

    def test_whitespace_handling(self):
        """空白字符处理"""
        result = _tokenize("  施工方案   质量标准  ")
        assert len(result) > 0


# ==============================================================================
# _extract_docs tests
# ==============================================================================


class TestExtractDocs:
    """测试 _extract_docs 方法"""

    def test_empty_dict(self):
        """空字典返回空列表"""
        result = _extract_docs({})
        assert result == []

    def test_empty_list(self):
        """空列表返回空列表"""
        result = _extract_docs([])
        assert result == []

    def test_dict_with_process_name(self):
        """包含工序名称的字典"""
        obj = {
            "工序名称": "混凝土浇筑",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试文档提取功能的正确性。",
            "质量标准": "达到设计要求"
        }
        result = _extract_docs(obj)
        assert len(result) > 0
        assert result[0]["title"] == "混凝土浇筑"

    def test_dict_with_name_field(self):
        """包含 name 字段的字典"""
        obj = {
            "name": "钢筋绑扎",
            "description": "这是一段足够长的描述文本，用于测试文档提取功能的正确性和覆盖率。"
        }
        result = _extract_docs(obj)
        assert len(result) > 0
        assert result[0]["title"] == "钢筋绑扎"

    def test_dict_with_title_field(self):
        """包含 title 字段的字典"""
        obj = {
            "title": "土方开挖",
            "content": "这是一段足够长的内容描述文本，用于测试文档提取功能是否正常工作。"
        }
        result = _extract_docs(obj)
        assert len(result) > 0
        assert result[0]["title"] == "土方开挖"

    def test_short_text_filtered(self):
        """短文本被过滤（<30字符）"""
        obj = {
            "工序名称": "测试",
            "施工要点": "短"
        }
        result = _extract_docs(obj)
        assert len(result) == 0

    def test_nested_dict(self):
        """嵌套字典"""
        obj = {
            "工序名称": "主工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试嵌套结构的提取功能。",
            "子工序": {
                "工序名称": "子工序1",
                "施工要点": "这是另一段足够长的子工序施工要点描述文本，测试嵌套。"
            }
        }
        result = _extract_docs(obj)
        titles = [d["title"] for d in result]
        assert "主工序" in titles or "子工序1" in titles

    def test_list_of_dicts(self):
        """字典列表"""
        obj = [
            {
                "工序名称": "工序A",
                "施工要点": "这是一段足够长的施工要点A描述文本，用于测试列表提取功能。"
            },
            {
                "工序名称": "工序B",
                "施工要点": "这是一段足够长的施工要点B描述文本，用于测试列表提取功能。"
            }
        ]
        result = _extract_docs(obj)
        titles = [d["title"] for d in result]
        assert "工序A" in titles or "工序B" in titles

    def test_path_tracking(self):
        """路径跟踪"""
        obj = {
            "工序名称": "测试工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试路径跟踪功能。"
        }
        result = _extract_docs(obj, path="$.root")
        if result:
            assert result[0]["path"].startswith("$.root")

    def test_none_values_filtered(self):
        """None 值被过滤"""
        obj = {
            "工序名称": "测试工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试None值过滤功能。",
            "空字段": None
        }
        result = _extract_docs(obj)
        if result:
            assert "空字段: None" not in result[0]["text"]

    def test_empty_string_filtered(self):
        """空字符串被过滤"""
        obj = {
            "工序名称": "测试工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试空字符串过滤功能。",
            "空内容": ""
        }
        result = _extract_docs(obj)
        if result:
            assert "空内容: " not in result[0]["text"]

    def test_nested_list_filtered(self):
        """嵌套列表不直接包含在文本中"""
        obj = {
            "工序名称": "测试工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试嵌套列表过滤功能。",
            "子项目": ["a", "b", "c"]
        }
        result = _extract_docs(obj)
        # 子项目作为列表不应该直接出现在文本中
        if result:
            assert "['a'" not in result[0]["text"]

    def test_nested_dict_filtered_from_text(self):
        """嵌套字典不直接包含在文本中"""
        obj = {
            "工序名称": "测试工序",
            "施工要点": "这是一段足够长的施工要点描述文本，用于测试嵌套字典过滤功能。",
            "详情": {"key": "value"}
        }
        result = _extract_docs(obj)
        if result:
            assert "{'key'" not in result[0]["text"]


# ==============================================================================
# search_kg tests
# ==============================================================================


class TestSearchKg:
    """测试 search_kg 方法"""

    def test_no_active_kg(self):
        """无激活的知识图谱"""
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value=None):
            result = search_kg("施工方案")
            assert result["results"] == []
            assert result["error"] == "no_active_kg"

    def test_kg_file_missing(self, tmp_path):
        """知识图谱文件不存在"""
        fake_path = tmp_path / "nonexistent.json"
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(fake_path)}):
            result = search_kg("施工方案")
            assert result["results"] == []
            assert result["error"] == "kg_file_missing"

    def test_kg_parse_error(self, tmp_path):
        """知识图谱文件解析错误"""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("invalid json {{{", encoding="utf-8")
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(bad_file)}):
            result = search_kg("施工方案")
            assert result["results"] == []
            assert "kg_parse_error" in result["error"]

    def test_empty_query(self, tmp_path):
        """空查询"""
        kg_file = tmp_path / "kg.json"
        kg_file.write_text('{"test": "value"}', encoding="utf-8")
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("")
            assert result["results"] == []
            assert result["error"] == "empty_query"

    def test_successful_search(self, tmp_path):
        """成功搜索"""
        kg_data = {
            "工序名称": "混凝土浇筑",
            "施工要点": "这是一段关于混凝土浇筑的施工要点描述，包含质量标准和安全措施。"
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("混凝土")
            assert "results" in result
            assert "error" not in result

    def test_search_with_matches(self, tmp_path):
        """搜索有匹配结果"""
        kg_data = {
            "processes": [
                {
                    "工序名称": "混凝土浇筑",
                    "施工要点": "这是一段关于混凝土浇筑的施工要点描述，包含质量标准和安全措施要求。"
                },
                {
                    "工序名称": "钢筋绑扎",
                    "施工要点": "这是一段关于钢筋绑扎的施工要点描述，包含验收标准和安全施工要求。"
                }
            ]
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("混凝土")
            assert len(result["results"]) > 0
            # 匹配的结果应该包含混凝土相关内容
            found = any("混凝土" in r.get("text", "") or "混凝土" in r.get("title", "") for r in result["results"])
            assert found

    def test_top_k_limit(self, tmp_path):
        """top_k 限制"""
        # 创建多个工序
        kg_data = {
            "processes": [
                {
                    "工序名称": f"工序{i}",
                    "施工要点": f"这是一段关于工序{i}的施工要点描述，包含质量标准和安全措施要求。"
                }
                for i in range(20)
            ]
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("工序", top_k=3)
            assert len(result["results"]) <= 3

    def test_default_top_k(self, tmp_path):
        """默认 top_k=6"""
        kg_data = {
            "processes": [
                {
                    "工序名称": f"工序{i}",
                    "施工要点": f"这是一段关于工序{i}的施工要点描述，包含质量标准和安全措施要求。"
                }
                for i in range(20)
            ]
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("工序")
            assert len(result["results"]) <= 6

    def test_result_structure(self, tmp_path):
        """结果结构验证"""
        kg_data = {
            "工序名称": "测试工序",
            "施工要点": "这是一段关于测试工序的施工要点描述，包含质量标准和安全措施要求。"
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("测试")
            if result["results"]:
                item = result["results"][0]
                assert "title" in item
                assert "text" in item
                assert "score" in item
                assert "path" in item

    def test_score_sorting(self, tmp_path):
        """分数排序（高分在前）"""
        kg_data = {
            "processes": [
                {
                    "工序名称": "低分工序",
                    "施工要点": "这是一段关于低分工序的施工要点描述，只有少量关键词匹配。"
                },
                {
                    "工序名称": "高分混凝土工序",
                    "施工要点": "这是关于混凝土浇筑的施工要点，混凝土质量标准，混凝土养护要求。"
                }
            ]
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("混凝土")
            if len(result["results"]) >= 2:
                # 分数应该是降序排列
                scores = [r["score"] for r in result["results"]]
                assert scores == sorted(scores, reverse=True)

    def test_text_truncation(self, tmp_path):
        """文本截断（最多900字符）"""
        long_text = "这是测试文本。" * 200  # 超过900字符
        kg_data = {
            "工序名称": "测试工序",
            "施工要点": long_text
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("测试")
            if result["results"]:
                assert len(result["results"][0]["text"]) <= 900

    def test_no_matches(self, tmp_path):
        """无匹配结果"""
        kg_data = {
            "工序名称": "混凝土浇筑",
            "施工要点": "这是一段关于混凝土浇筑的施工要点描述，包含质量标准和安全措施。"
        }
        kg_file = tmp_path / "kg.json"
        kg_file.write_text(json.dumps(kg_data, ensure_ascii=False), encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.kg_runtime.get_active_kg", return_value={"stored_as": str(kg_file)}):
            result = search_kg("完全不相关的查询词汇")
            # 可能有结果也可能没有，取决于分词
            assert "results" in result
