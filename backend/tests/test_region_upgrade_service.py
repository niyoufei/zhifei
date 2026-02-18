# -*- coding: utf-8 -*-
"""
Test suite for backend/region_upgrade_service.py
"""
import json
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from backend import region_upgrade_service


# =============================================================================
# _sha256_file
# =============================================================================
class TestSha256File:
    def test_empty_file(self, tmp_path):
        """空文件返回空内容的 sha256"""
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        result = region_upgrade_service._sha256_file(f)
        # sha256 of empty bytes
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_simple_content(self, tmp_path):
        """简单内容的 sha256"""
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        result = region_upgrade_service._sha256_file(f)
        # sha256 of "hello world"
        assert result == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_large_file(self, tmp_path):
        """大文件（超过 8192 字节）能正常处理"""
        f = tmp_path / "large.txt"
        content = b"x" * 20000
        f.write_bytes(content)
        result = region_upgrade_service._sha256_file(f)
        assert isinstance(result, str)
        assert len(result) == 64  # sha256 hex length

    def test_binary_file(self, tmp_path):
        """二进制文件能正常处理"""
        f = tmp_path / "binary.bin"
        f.write_bytes(bytes(range(256)))
        result = region_upgrade_service._sha256_file(f)
        assert isinstance(result, str)
        assert len(result) == 64


# =============================================================================
# _pick_default_region_key
# =============================================================================
class TestPickDefaultRegionKey:
    def test_empty_config_returns_none(self):
        """空 config 返回 None"""
        assert region_upgrade_service._pick_default_region_key({}) is None

    def test_none_rules_returns_none(self):
        """region_upgrade_rules 为 None 返回 None"""
        cfg = {"region_upgrade_rules": None}
        assert region_upgrade_service._pick_default_region_key(cfg) is None

    def test_empty_rules_returns_none(self):
        """region_upgrade_rules 为空 dict 返回 None"""
        cfg = {"region_upgrade_rules": {}}
        assert region_upgrade_service._pick_default_region_key(cfg) is None

    def test_rules_not_dict_returns_none(self):
        """region_upgrade_rules 非 dict 返回 None"""
        cfg = {"region_upgrade_rules": ["item1"]}
        assert region_upgrade_service._pick_default_region_key(cfg) is None

    def test_prefers_anhui_hefei_general(self):
        """优先返回 anhui_hefei_general"""
        cfg = {
            "region_upgrade_rules": {
                "zz_region": "/path/zz",
                "anhui_hefei_general": "/path/anhui",
                "aa_region": "/path/aa",
            }
        }
        assert region_upgrade_service._pick_default_region_key(cfg) == "anhui_hefei_general"

    def test_sorted_first_key_when_no_anhui(self):
        """无 anhui_hefei_general 时返回排序后第一个 key"""
        cfg = {
            "region_upgrade_rules": {
                "zz_region": "/path/zz",
                "bb_region": "/path/bb",
                "aa_region": "/path/aa",
            }
        }
        assert region_upgrade_service._pick_default_region_key(cfg) == "aa_region"

    def test_single_key(self):
        """只有一个 key 时返回它"""
        cfg = {"region_upgrade_rules": {"only_one": "/path/only"}}
        assert region_upgrade_service._pick_default_region_key(cfg) == "only_one"


# =============================================================================
# _extract_region_key
# =============================================================================
class TestExtractRegionKey:
    @pytest.fixture
    def mock_cfg(self):
        return {
            "region_upgrade_rules": {
                "default_region": "/path/default",
                "anhui_hefei_general": "/path/anhui",
            }
        }

    def test_from_payload_region_key(self, mock_cfg):
        """从 payload.region_key 提取"""
        payload = {"region_key": "my_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "my_region"

    def test_from_payload_region_upgrade_key(self, mock_cfg):
        """从 payload.region_upgrade_key 提取"""
        payload = {"region_upgrade_key": "upgrade_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "upgrade_region"

    def test_from_payload_region(self, mock_cfg):
        """从 payload.region 提取"""
        payload = {"region": "simple_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "simple_region"

    def test_from_payload_region_code(self, mock_cfg):
        """从 payload.region_code 提取"""
        payload = {"region_code": "code_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "code_region"

    def test_from_payload_regionCode(self, mock_cfg):
        """从 payload.regionCode 提取（驼峰命名）"""
        payload = {"regionCode": "camel_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "camel_region"

    def test_from_payload_nested_dict_with_key(self, mock_cfg):
        """从 payload.region_key.key 嵌套提取"""
        payload = {"region_key": {"key": "nested_key_region"}}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "nested_key_region"

    def test_from_payload_region_as_dict_with_key(self, mock_cfg):
        """从 payload.region.key 嵌套提取"""
        payload = {"region": {"key": "dict_region"}}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "dict_region"

    def test_strips_whitespace(self, mock_cfg):
        """提取时去除空格"""
        payload = {"region_key": "  whitespace_region  "}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "whitespace_region"

    def test_ignores_empty_string(self, mock_cfg):
        """空字符串跳过"""
        payload = {"region_key": "", "region": "fallback_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "fallback_region"

    def test_ignores_whitespace_only(self, mock_cfg):
        """纯空格字符串跳过"""
        payload = {"region_key": "   ", "region": "real_region"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "real_region"

    def test_from_project_profile_region_key(self, mock_cfg):
        """从 project_profile.region_key 提取"""
        profile = {"region_key": "profile_region"}
        result = region_upgrade_service._extract_region_key({}, profile, mock_cfg)
        assert result == "profile_region"

    def test_from_project_profile_nested_region_key(self, mock_cfg):
        """从 project_profile.region.key 提取"""
        profile = {"region": {"key": "nested_profile_region"}}
        result = region_upgrade_service._extract_region_key({}, profile, mock_cfg)
        assert result == "nested_profile_region"

    def test_from_project_profile_region_region_key(self, mock_cfg):
        """从 project_profile.region.region_key 提取"""
        profile = {"region": {"region_key": "region_region_key"}}
        result = region_upgrade_service._extract_region_key({}, profile, mock_cfg)
        assert result == "region_region_key"

    def test_from_project_profile_output_profile_region_key(self, mock_cfg):
        """从 project_profile.output_profile.region_key 提取"""
        profile = {"output_profile": {"region_key": "output_profile_region"}}
        result = region_upgrade_service._extract_region_key({}, profile, mock_cfg)
        assert result == "output_profile_region"

    def test_from_project_profile_output_profile_region_key_nested(self, mock_cfg):
        """从 project_profile.output_profile.region.key 提取"""
        profile = {"output_profile": {"region": {"key": "deeply_nested_region"}}}
        result = region_upgrade_service._extract_region_key({}, profile, mock_cfg)
        assert result == "deeply_nested_region"

    def test_payload_takes_priority_over_profile(self, mock_cfg):
        """payload 优先于 project_profile"""
        payload = {"region_key": "payload_region"}
        profile = {"region_key": "profile_region"}
        result = region_upgrade_service._extract_region_key(payload, profile, mock_cfg)
        assert result == "payload_region"

    def test_fallback_to_default(self, mock_cfg):
        """无法提取时回退到默认"""
        result = region_upgrade_service._extract_region_key({}, {}, mock_cfg)
        assert result == "anhui_hefei_general"  # default in mock_cfg

    def test_handles_none_payload(self, mock_cfg):
        """payload 为 None 时不崩溃"""
        profile = {"region_key": "profile_region"}
        result = region_upgrade_service._extract_region_key(None, profile, mock_cfg)
        assert result == "profile_region"

    def test_handles_none_profile(self, mock_cfg):
        """project_profile 为 None 时不崩溃"""
        payload = {"region_key": "payload_region"}
        result = region_upgrade_service._extract_region_key(payload, None, mock_cfg)
        assert result == "payload_region"

    def test_handles_both_none(self, mock_cfg):
        """payload 和 profile 都为 None 时回退默认"""
        result = region_upgrade_service._extract_region_key(None, None, mock_cfg)
        assert result == "anhui_hefei_general"

    def test_nested_dict_missing_key_field(self, mock_cfg):
        """嵌套 dict 没有 key 字段时跳过"""
        payload = {"region_key": {"other": "value"}, "region": "fallback"}
        result = region_upgrade_service._extract_region_key(payload, {}, mock_cfg)
        assert result == "fallback"


# =============================================================================
# resolve_region_upgrade
# =============================================================================
class TestResolveRegionUpgrade:
    @pytest.fixture
    def rule_file(self, tmp_path):
        """创建临时规则文件"""
        rule = tmp_path / "rule.json"
        rule.write_text(json.dumps({
            "name": "Test Rule",
            "version": "1.0",
            "section_a": {"key": "value"},
            "section_b": {"key": "value"},
        }), encoding="utf-8")
        return rule

    @pytest.fixture
    def mock_kg_loader(self, rule_file):
        """Mock kg_loader"""
        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {
                    "test_region": str(rule_file),
                    "anhui_hefei_general": str(rule_file),
                }
            }
            m.get_region_upgrade_rule.return_value = rule_file
            yield m

    def test_basic_success(self, mock_kg_loader, rule_file):
        """基本成功场景"""
        payload = {"region_key": "test_region"}
        result = region_upgrade_service.resolve_region_upgrade(payload, {})

        assert result["applied"] is True
        assert result["region_key"] == "test_region"
        assert result["rule_path"] == str(rule_file)
        assert len(result["rule_sha256"]) == 64
        assert "name" in result["top_level_keys"]
        assert "version" in result["top_level_keys"]
        assert result["errors"] == []
        assert result["name"] == "Test Rule"
        assert result["version"] == "1.0"

    def test_returns_timestamp(self, mock_kg_loader):
        """返回时间戳"""
        before = int(time.time())
        result = region_upgrade_service.resolve_region_upgrade({"region_key": "test"}, {})
        after = int(time.time())

        assert "ts" in result
        assert before <= result["ts"] <= after

    def test_no_region_key_and_no_default(self):
        """无 region_key 且无默认配置时返回错误"""
        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {}
            result = region_upgrade_service.resolve_region_upgrade({}, {})

        assert result["applied"] is False
        assert result["region_key"] is None
        assert "region_key not provided" in result["errors"][0]

    def test_region_key_not_in_config(self):
        """region_key 不在配置中"""
        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"other_region": "/path/other"}
            }
            m.get_region_upgrade_rule.return_value = None

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "unknown_region"}, {}
            )

        assert result["applied"] is False
        assert result["region_key"] == "unknown_region"
        assert "no region_upgrade_rule configured" in result["errors"][0]

    def test_rule_file_not_exists(self, tmp_path):
        """规则文件不存在"""
        nonexistent = tmp_path / "nonexistent.json"

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(nonexistent)}
            }
            m.get_region_upgrade_rule.return_value = nonexistent

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["applied"] is False
        assert result["rule_path"] == str(nonexistent)
        assert "rule file not found" in result["errors"][0]

    def test_rule_file_invalid_json(self, tmp_path):
        """规则文件 JSON 格式错误"""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ invalid json }", encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(bad_json)}
            }
            m.get_region_upgrade_rule.return_value = bad_json

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["applied"] is False
        assert "json parse error" in result["errors"][0]

    def test_rule_file_is_array(self, tmp_path):
        """规则文件是数组而非对象"""
        array_json = tmp_path / "array.json"
        array_json.write_text('["item1", "item2"]', encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(array_json)}
            }
            m.get_region_upgrade_rule.return_value = array_json

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        # 数组时 top_level_keys 为空，但不报错
        assert result["applied"] is True
        assert result["top_level_keys"] == []

    def test_extracts_metadata_fields(self, tmp_path):
        """提取规则文件中的元数据字段"""
        rule = tmp_path / "meta.json"
        rule.write_text(json.dumps({
            "id": "rule-001",
            "name": "Rule Name",
            "version": "2.0",
            "rule_version": "3.0",
            "upgrade_version": "4.0",
        }), encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(rule)}
            }
            m.get_region_upgrade_rule.return_value = rule

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["id"] == "rule-001"
        assert result["name"] == "Rule Name"
        assert result["version"] == "2.0"
        assert result["rule_version"] == "3.0"
        assert result["upgrade_version"] == "4.0"

    def test_limits_top_level_keys_to_50(self, tmp_path):
        """top_level_keys 最多 50 个"""
        rule = tmp_path / "large.json"
        data = {f"key_{i:03d}": i for i in range(100)}
        rule.write_text(json.dumps(data), encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(rule)}
            }
            m.get_region_upgrade_rule.return_value = rule

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert len(result["top_level_keys"]) == 50

    def test_includes_project_profile_decision(self, mock_kg_loader):
        """包含 project_profile 的 decision"""
        profile = {"decision": "approved", "input_sha256": "abc123"}
        result = region_upgrade_service.resolve_region_upgrade({}, profile)

        assert result["project_profile_decision"] == "approved"
        assert result["input_sha256"] == "abc123"

    def test_handles_none_inputs(self, mock_kg_loader):
        """处理 None 输入"""
        result = region_upgrade_service.resolve_region_upgrade(None, None)
        # 应该使用默认 region_key（anhui_hefei_general）
        assert result["region_key"] == "anhui_hefei_general"

    def test_top_level_keys_sorted(self, tmp_path):
        """top_level_keys 是排序的"""
        rule = tmp_path / "sorted.json"
        rule.write_text(json.dumps({
            "zebra": 1,
            "apple": 2,
            "mango": 3,
        }), encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(rule)}
            }
            m.get_region_upgrade_rule.return_value = rule

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["top_level_keys"] == ["apple", "mango", "zebra"]


# =============================================================================
# Edge cases and integration
# =============================================================================
class TestEdgeCases:
    def test_unicode_in_rule_file(self, tmp_path):
        """规则文件包含 Unicode 字符"""
        rule = tmp_path / "unicode.json"
        rule.write_text(json.dumps({
            "名称": "中文规则",
            "版本": "1.0",
        }), encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(rule)}
            }
            m.get_region_upgrade_rule.return_value = rule

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["applied"] is True
        assert "名称" in result["top_level_keys"]

    def test_special_characters_in_region_key(self):
        """region_key 包含特殊字符"""
        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {}
            m.get_region_upgrade_rule.return_value = None

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "region/with:special@chars"}, {}
            )

        assert result["region_key"] == "region/with:special@chars"

    def test_empty_rule_file(self, tmp_path):
        """空的规则文件（有效空对象）"""
        rule = tmp_path / "empty.json"
        rule.write_text("{}", encoding="utf-8")

        with mock.patch.object(region_upgrade_service, "kg_loader") as m:
            m.load_kg_config.return_value = {
                "region_upgrade_rules": {"test_region": str(rule)}
            }
            m.get_region_upgrade_rule.return_value = rule

            result = region_upgrade_service.resolve_region_upgrade(
                {"region_key": "test_region"}, {}
            )

        assert result["applied"] is True
        assert result["top_level_keys"] == []
