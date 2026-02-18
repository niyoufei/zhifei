#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: kg_context_service.py
验证知识图谱上下文服务的各个功能。
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保 backend 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from kg_context_service import (
    _sha256_bytes,
    _sha256_file,
    _safe_load_json,
    _now_iso,
    _coerce_keywords,
    _collect_domain_map_entries,
    _fallback_domain_key,
    _extract_domain_key_from_map,
    _score_map_entry,
    _resolve_domain,
    _pack_name_map,
    _select_base_packs,
    build_kg_context,
)


class TestSha256Bytes:
    """测试 _sha256_bytes 函数"""

    def test_returns_string(self):
        """测试返回值是字符串"""
        result = _sha256_bytes(b"hello")
        assert isinstance(result, str)

    def test_returns_64_char_hex(self):
        """测试返回 64 字符的十六进制字符串"""
        result = _sha256_bytes(b"test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        """测试相同输入产生相同输出"""
        data = b"deterministic test"
        result1 = _sha256_bytes(data)
        result2 = _sha256_bytes(data)
        assert result1 == result2

    def test_different_input_different_output(self):
        """测试不同输入产生不同输出"""
        result1 = _sha256_bytes(b"input1")
        result2 = _sha256_bytes(b"input2")
        assert result1 != result2

    def test_empty_bytes(self):
        """测试空 bytes"""
        result = _sha256_bytes(b"")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_known_value(self):
        """测试已知 SHA256 值"""
        # SHA256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
        result = _sha256_bytes(b"hello")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_unicode_bytes(self):
        """测试 Unicode bytes"""
        result = _sha256_bytes("你好世界".encode("utf-8"))
        assert isinstance(result, str)
        assert len(result) == 64


class TestSha256File:
    """测试 _sha256_file 函数"""

    def test_returns_none_for_nonexistent_file(self):
        """测试不存在的文件返回 None"""
        result = _sha256_file(Path("/nonexistent/path/file.txt"))
        assert result is None

    def test_returns_string_for_existing_file(self, tmp_path):
        """测试存在的文件返回字符串"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")
        result = _sha256_file(test_file)
        assert isinstance(result, str)

    def test_returns_64_char_hex(self, tmp_path):
        """测试返回 64 字符的十六进制字符串"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"content")
        result = _sha256_file(test_file)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self, tmp_path):
        """测试相同文件产生相同输出"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"deterministic")
        result1 = _sha256_file(test_file)
        result2 = _sha256_file(test_file)
        assert result1 == result2

    def test_empty_file(self, tmp_path):
        """测试空文件"""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")
        result = _sha256_file(test_file)
        assert isinstance(result, str)
        assert len(result) == 64


class TestSafeLoadJson:
    """测试 _safe_load_json 函数"""

    def test_loads_valid_json(self, tmp_path):
        """测试加载有效 JSON"""
        test_file = tmp_path / "valid.json"
        test_file.write_text('{"key": "value"}', encoding="utf-8")
        obj, err = _safe_load_json(test_file)
        assert obj == {"key": "value"}
        assert err is None

    def test_returns_error_for_invalid_json(self, tmp_path):
        """测试无效 JSON 返回错误"""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not valid json {", encoding="utf-8")
        obj, err = _safe_load_json(test_file)
        assert obj is None
        assert err is not None

    def test_returns_error_for_nonexistent_file(self):
        """测试不存在文件返回错误"""
        obj, err = _safe_load_json(Path("/nonexistent/file.json"))
        assert obj is None
        assert err is not None

    def test_loads_array(self, tmp_path):
        """测试加载数组"""
        test_file = tmp_path / "array.json"
        test_file.write_text('[1, 2, 3]', encoding="utf-8")
        obj, err = _safe_load_json(test_file)
        assert obj == [1, 2, 3]
        assert err is None

    def test_loads_unicode(self, tmp_path):
        """测试加载 Unicode 内容"""
        test_file = tmp_path / "unicode.json"
        test_file.write_text('{"中文": "内容"}', encoding="utf-8")
        obj, err = _safe_load_json(test_file)
        assert obj == {"中文": "内容"}
        assert err is None


class TestNowIso:
    """测试 _now_iso 函数"""

    def test_returns_string(self):
        """测试返回值是字符串"""
        result = _now_iso()
        assert isinstance(result, str)

    def test_format_matches_iso(self):
        """测试格式匹配 ISO 格式"""
        result = _now_iso()
        # 格式: YYYY-MM-DDTHH:MM:SS
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[13] == ":"
        assert result[16] == ":"

    def test_year_is_reasonable(self):
        """测试年份合理"""
        result = _now_iso()
        year = int(result[:4])
        assert 2020 <= year <= 2100


class TestCoerceKeywords:
    """测试 _coerce_keywords 函数"""

    def test_none_returns_empty_list(self):
        """测试 None 返回空列表"""
        result = _coerce_keywords(None)
        assert result == []

    def test_empty_list_returns_empty_list(self):
        """测试空列表返回空列表"""
        result = _coerce_keywords([])
        assert result == []

    def test_list_of_strings(self):
        """测试字符串列表"""
        result = _coerce_keywords(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_strips_whitespace(self):
        """测试去除空白"""
        result = _coerce_keywords(["  a  ", "  b  "])
        assert result == ["a", "b"]

    def test_filters_empty_strings(self):
        """测试过滤空字符串"""
        result = _coerce_keywords(["a", "", "  ", "b"])
        assert result == ["a", "b"]

    def test_filters_non_strings(self):
        """测试过滤非字符串"""
        result = _coerce_keywords(["a", 123, None, "b"])
        assert result == ["a", "b"]

    def test_string_comma_separated(self):
        """测试逗号分隔的字符串"""
        result = _coerce_keywords("a,b,c")
        assert result == ["a", "b", "c"]

    def test_string_chinese_comma_separated(self):
        """测试中文逗号分隔的字符串"""
        result = _coerce_keywords("房建，市政，装饰")
        assert result == ["房建", "市政", "装饰"]

    def test_string_semicolon_separated(self):
        """测试分号分隔的字符串"""
        result = _coerce_keywords("a;b;c")
        assert result == ["a", "b", "c"]

    def test_string_space_separated(self):
        """测试空格分隔的字符串"""
        result = _coerce_keywords("a b c")
        assert result == ["a", "b", "c"]

    def test_mixed_separators(self):
        """测试混合分隔符"""
        result = _coerce_keywords("a,b;c d")
        assert result == ["a", "b", "c", "d"]

    def test_other_types_return_empty(self):
        """测试其他类型返回空列表"""
        assert _coerce_keywords(123) == []
        assert _coerce_keywords({"key": "value"}) == []


class TestCollectDomainMapEntries:
    """测试 _collect_domain_map_entries 函数"""

    def test_empty_object_returns_empty_list(self):
        """测试空对象返回空列表"""
        result = _collect_domain_map_entries({})
        assert result == []

    def test_none_returns_empty_list(self):
        """测试 None 返回空列表"""
        result = _collect_domain_map_entries(None)
        assert result == []

    def test_collects_from_maps_key(self):
        """测试从 maps 键收集"""
        obj = {"maps": [{"cn_name": "测试"}]}
        result = _collect_domain_map_entries(obj)
        assert len(result) == 1
        assert result[0]["cn_name"] == "测试"

    def test_nested_maps(self):
        """测试嵌套 maps"""
        obj = {
            "knowledge_graph_library": [
                {"maps": [{"cn_name": "a"}]},
                {"maps": [{"cn_name": "b"}]},
            ]
        }
        result = _collect_domain_map_entries(obj)
        assert len(result) == 2

    def test_deduplicates_by_signature(self):
        """测试按签名去重"""
        obj = {
            "maps": [
                {"cn_name": "测试", "en_name": "test", "domain_key": "key1"},
                {"cn_name": "测试", "en_name": "test", "domain_key": "key1"},
            ]
        }
        result = _collect_domain_map_entries(obj)
        assert len(result) == 1

    def test_different_signatures_kept(self):
        """测试不同签名保留"""
        obj = {
            "maps": [
                {"cn_name": "a", "en_name": "a", "domain_key": "k1"},
                {"cn_name": "b", "en_name": "b", "domain_key": "k2"},
            ]
        }
        result = _collect_domain_map_entries(obj)
        assert len(result) == 2


class TestFallbackDomainKey:
    """测试 _fallback_domain_key 函数"""

    def test_none_returns_none(self):
        """测试 None 返回 None"""
        result = _fallback_domain_key(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """测试空字符串返回 None"""
        result = _fallback_domain_key("")
        assert result is None

    def test_decoration_keywords(self):
        """测试装饰相关关键词"""
        assert _fallback_domain_key("装饰工程") == "decoration"
        assert _fallback_domain_key("装修改造") == "decoration"
        assert _fallback_domain_key("精装修") == "decoration"

    def test_building_keywords(self):
        """测试房建相关关键词"""
        assert _fallback_domain_key("房建工程") == "building"
        assert _fallback_domain_key("混凝土结构") == "building"
        assert _fallback_domain_key("钢筋工程") == "building"

    def test_municipal_road_keywords(self):
        """测试市政道路相关关键词"""
        assert _fallback_domain_key("市政道路工程") == "municipal_road"
        assert _fallback_domain_key("路面施工") == "municipal_road"
        assert _fallback_domain_key("沥青铺设") == "municipal_road"

    def test_municipal_drain_keywords(self):
        """测试排水相关关键词"""
        assert _fallback_domain_key("排水工程") == "municipal_drain"
        assert _fallback_domain_key("雨水管道") == "municipal_drain"
        assert _fallback_domain_key("污水处理") == "municipal_drain"

    def test_mep_keywords(self):
        """测试机电相关关键词"""
        assert _fallback_domain_key("机电安装") == "mep"
        assert _fallback_domain_key("暖通空调") == "mep"
        assert _fallback_domain_key("电气工程") == "mep"

    def test_highway_keywords(self):
        """测试公路相关关键词"""
        assert _fallback_domain_key("公路工程") == "highway"
        assert _fallback_domain_key("高速公路") == "highway"
        assert _fallback_domain_key("路基施工") == "highway"

    def test_water_resources_keywords(self):
        """测试水利相关关键词"""
        assert _fallback_domain_key("水利工程") == "water_resources"
        assert _fallback_domain_key("堤防工程") == "water_resources"

    def test_power_energy_keywords(self):
        """测试电力相关关键词"""
        assert _fallback_domain_key("电力工程") == "power_energy"
        assert _fallback_domain_key("光伏发电") == "power_energy"

    def test_unmatched_returns_none(self):
        """测试不匹配返回 None"""
        result = _fallback_domain_key("未知工程类型")
        assert result is None


class TestExtractDomainKeyFromMap:
    """测试 _extract_domain_key_from_map 函数"""

    def test_extracts_domain_key(self):
        """测试提取 domain_key"""
        m = {"domain_key": "building"}
        result = _extract_domain_key_from_map(m)
        assert result == "building"

    def test_extracts_domain(self):
        """测试提取 domain"""
        m = {"domain": "mep"}
        result = _extract_domain_key_from_map(m)
        assert result == "mep"

    def test_extracts_en_key(self):
        """测试提取 en_key"""
        m = {"en_key": "highway"}
        result = _extract_domain_key_from_map(m)
        assert result == "highway"

    def test_extracts_en_name(self):
        """测试提取 en_name"""
        m = {"en_name": "decoration"}
        result = _extract_domain_key_from_map(m)
        assert result == "decoration"

    def test_priority_order(self):
        """测试优先级顺序"""
        m = {"domain_key": "first", "domain": "second", "en_key": "third"}
        result = _extract_domain_key_from_map(m)
        assert result == "first"

    def test_nested_domain_dict(self):
        """测试嵌套的 domain 字典"""
        m = {"domain": {"domain_key": "nested_key"}}
        result = _extract_domain_key_from_map(m)
        assert result == "nested_key"

    def test_empty_map_returns_none(self):
        """测试空映射返回 None"""
        result = _extract_domain_key_from_map({})
        assert result is None

    def test_strips_whitespace(self):
        """测试去除空白"""
        m = {"domain_key": "  building  "}
        result = _extract_domain_key_from_map(m)
        assert result == "building"


class TestScoreMapEntry:
    """测试 _score_map_entry 函数"""

    def test_empty_query_returns_zero(self):
        """测试空查询返回 0"""
        m = {"cn_name": "测试"}
        result = _score_map_entry(m, "")
        assert result == 0

    def test_none_query_returns_zero(self):
        """测试 None 查询返回 0"""
        m = {"cn_name": "测试"}
        result = _score_map_entry(m, None)
        assert result == 0

    def test_exact_cn_name_match_high_score(self):
        """测试完全匹配中文名得高分"""
        m = {"cn_name": "房建工程"}
        result = _score_map_entry(m, "这是一个房建工程项目")
        assert result > 0

    def test_keyword_match_adds_score(self):
        """测试关键词匹配加分"""
        m = {"cn_name": "测试", "keywords": ["市政", "道路"]}
        result = _score_map_entry(m, "市政道路工程")
        assert result > 0

    def test_domain_word_match(self):
        """测试领域词匹配"""
        m = {"cn_name": "装饰工程", "desc": "装饰装修"}
        result = _score_map_entry(m, "装饰")
        assert result > 0

    def test_no_match_returns_low_score(self):
        """测试无匹配返回低分"""
        m = {"cn_name": "完全不相关"}
        result = _score_map_entry(m, "测试查询")
        assert result == 0


class TestResolveDomain:
    """测试 _resolve_domain 函数"""

    def test_returns_dict(self):
        """测试返回字典"""
        result = _resolve_domain(None, None, None)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """测试包含必需的键"""
        result = _resolve_domain(None, None, None)
        assert "domain_key" in result
        assert "method" in result
        assert "score" in result

    def test_no_input_returns_none_domain_key(self):
        """测试无输入返回 None 域键"""
        result = _resolve_domain(None, None, None)
        assert result["domain_key"] is None
        assert result["method"] == "none"

    def test_fallback_when_no_domain_map(self):
        """测试无域映射时使用回退"""
        result = _resolve_domain(None, "房建工程", None)
        assert result["domain_key"] == "building"
        assert result["method"] == "fallback"

    def test_domain_map_match(self):
        """测试域映射匹配"""
        domain_map = {
            "maps": [
                {"cn_name": "房建工程", "domain_key": "building"}
            ]
        }
        result = _resolve_domain(domain_map, "房建工程", None)
        assert result["domain_key"] is not None
        assert result["score"] > 0

    def test_topic_fallback(self):
        """测试 topic 回退"""
        result = _resolve_domain(None, None, "机电安装工程")
        assert result["domain_key"] == "mep"


class TestPackNameMap:
    """测试 _pack_name_map 函数"""

    def test_empty_list_returns_empty_dict(self):
        """测试空列表返回空字典"""
        result = _pack_name_map([])
        assert result == {}

    def test_creates_name_to_path_mapping(self):
        """测试创建名称到路径的映射"""
        paths = [Path("/a/b/pack1.json"), Path("/c/d/pack2.json")]
        result = _pack_name_map(paths)
        assert result["pack1.json"] == Path("/a/b/pack1.json")
        assert result["pack2.json"] == Path("/c/d/pack2.json")

    def test_uses_filename_as_key(self):
        """测试使用文件名作为键"""
        paths = [Path("/very/long/path/to/file.json")]
        result = _pack_name_map(paths)
        assert "file.json" in result


class TestSelectBasePacks:
    """测试 _select_base_packs 函数"""

    def test_returns_list(self):
        """测试返回列表"""
        result = _select_base_packs(None, [])
        assert isinstance(result, list)

    def test_always_includes_universal_pack(self):
        """测试始终包含 Universal 包"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Civil_Basic_Pack.json"),
        ]
        result = _select_base_packs(None, paths)
        pack_names = [p.name for p in result]
        assert "Universal_Base_Pack.json" in pack_names

    def test_always_includes_risk_pack(self):
        """测试始终包含 Risk 包"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Risk_Specialist_Pack.json"),
        ]
        result = _select_base_packs(None, paths)
        pack_names = [p.name for p in result]
        assert "Risk_Specialist_Pack.json" in pack_names

    def test_municipal_road_selects_transport_pack(self):
        """测试市政道路选择交通基础设施包"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Risk_Specialist_Pack.json"),
            Path("/packs/Transport_Infra_Pack.json"),
        ]
        result = _select_base_packs("municipal_road", paths)
        pack_names = [p.name for p in result]
        assert "Transport_Infra_Pack.json" in pack_names

    def test_mep_selects_energy_pack(self):
        """测试机电选择能源工业包"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Risk_Specialist_Pack.json"),
            Path("/packs/Energy_Industrial_Pack.json"),
        ]
        result = _select_base_packs("mep", paths)
        pack_names = [p.name for p in result]
        assert "Energy_Industrial_Pack.json" in pack_names

    def test_unknown_domain_selects_civil_pack(self):
        """测试未知域选择土木基础包"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Risk_Specialist_Pack.json"),
            Path("/packs/Civil_Basic_Pack.json"),
        ]
        result = _select_base_packs("unknown_domain", paths)
        pack_names = [p.name for p in result]
        assert "Civil_Basic_Pack.json" in pack_names

    def test_no_duplicates(self):
        """测试无重复"""
        paths = [
            Path("/packs/Universal_Base_Pack.json"),
            Path("/packs/Universal_Base_Pack.json"),  # 重复
        ]
        result = _select_base_packs(None, paths)
        assert len(result) <= len(set(str(p) for p in result))


class TestBuildKgContext:
    """测试 build_kg_context 函数"""

    def test_returns_dict(self):
        """测试返回字典"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            result = build_kg_context({})
            assert isinstance(result, dict)

    def test_has_required_keys(self):
        """测试包含必需的键"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            result = build_kg_context({})
            assert "generated_at" in result
            assert "input_sha256" in result
            assert "domain_resolution" in result

    def test_input_sha256_is_deterministic(self):
        """测试 input_sha256 是确定性的"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            payload = {"topic": "测试主题"}
            result1 = build_kg_context(payload)
            result2 = build_kg_context(payload)
            assert result1["input_sha256"] == result2["input_sha256"]

    def test_extracts_topic_from_payload(self):
        """测试从 payload 提取 topic"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            result = build_kg_context({"topic": "测试主题"})
            assert result["topic"] == "测试主题"

    def test_extracts_project_type_from_profile(self):
        """测试从 profile 提取 project_type"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            profile = {"project_type": {"value": "房建工程"}}
            result = build_kg_context({}, profile)
            assert result["project_type_cn"] == "房建工程"

    def test_handles_none_payload(self):
        """测试处理 None payload"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            result = build_kg_context(None)
            assert isinstance(result, dict)

    def test_saves_to_build_directory(self):
        """测试保存到 build 目录"""
        with patch("kg_context_service.kg_loader") as mock_loader:
            mock_loader.load_kg_config.return_value = {"base_packs": [], "domain_map": "map.json"}
            mock_loader.get_domain_map_path.return_value = Path("/fake/map.json")
            mock_loader.get_base_pack_paths.return_value = []
            result = build_kg_context({})
            assert "saved_at" in result
            assert "kg_context.json" in result["saved_at"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
