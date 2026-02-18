#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: precheck_guard_service.py
验证 PreCheck Guard 服务的各个功能。
"""

import sys
from pathlib import Path

# 确保 backend 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from precheck_guard_service import (
    run_precheck_guard,
    _sha256_bytes,
    _stable_sha256,
    _is_empty,
    _humanize,
)


class TestSha256Bytes:
    """测试 _sha256_bytes 函数"""

    def test_returns_string(self):
        """测试返回值是字符串"""
        result = _sha256_bytes(b"test")
        assert isinstance(result, str)

    def test_returns_64_char_hex(self):
        """测试返回 64 字符的十六进制字符串"""
        result = _sha256_bytes(b"test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_consistent_output(self):
        """测试相同输入产生相同输出"""
        result1 = _sha256_bytes(b"hello")
        result2 = _sha256_bytes(b"hello")
        assert result1 == result2

    def test_different_input_different_output(self):
        """测试不同输入产生不同输出"""
        result1 = _sha256_bytes(b"hello")
        result2 = _sha256_bytes(b"world")
        assert result1 != result2

    def test_empty_bytes(self):
        """测试空字节输入"""
        result = _sha256_bytes(b"")
        assert isinstance(result, str)
        assert len(result) == 64


class TestStableSha256:
    """测试 _stable_sha256 函数"""

    def test_returns_string(self):
        """测试返回值是字符串"""
        result = _stable_sha256({"key": "value"})
        assert isinstance(result, str)

    def test_returns_64_char_hex(self):
        """测试返回 64 字符的十六进制字符串"""
        result = _stable_sha256({"key": "value"})
        assert len(result) == 64

    def test_order_independent(self):
        """测试字典键顺序不影响结果"""
        result1 = _stable_sha256({"a": 1, "b": 2})
        result2 = _stable_sha256({"b": 2, "a": 1})
        assert result1 == result2

    def test_handles_nested_dict(self):
        """测试嵌套字典"""
        result = _stable_sha256({"outer": {"inner": "value"}})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_handles_list(self):
        """测试列表输入"""
        result = _stable_sha256([1, 2, 3])
        assert isinstance(result, str)
        assert len(result) == 64

    def test_handles_chinese(self):
        """测试中文内容"""
        result = _stable_sha256({"项目": "排水工程"})
        assert isinstance(result, str)
        assert len(result) == 64


class TestIsEmpty:
    """测试 _is_empty 函数"""

    def test_none_is_empty(self):
        """测试 None 是空"""
        assert _is_empty(None) is True

    def test_empty_string_is_empty(self):
        """测试空字符串是空"""
        assert _is_empty("") is True

    def test_whitespace_string_is_empty(self):
        """测试纯空白字符串是空"""
        assert _is_empty("   ") is True
        assert _is_empty("\t\n") is True

    def test_non_empty_string_not_empty(self):
        """测试非空字符串不是空"""
        assert _is_empty("hello") is False

    def test_empty_list_is_empty(self):
        """测试空列表是空"""
        assert _is_empty([]) is True

    def test_non_empty_list_not_empty(self):
        """测试非空列表不是空"""
        assert _is_empty([1, 2]) is False

    def test_empty_dict_is_empty(self):
        """测试空字典是空"""
        assert _is_empty({}) is True

    def test_non_empty_dict_not_empty(self):
        """测试非空字典不是空"""
        assert _is_empty({"key": "value"}) is False

    def test_empty_tuple_is_empty(self):
        """测试空元组是空"""
        assert _is_empty(()) is True

    def test_empty_set_is_empty(self):
        """测试空集合是空"""
        assert _is_empty(set()) is True

    def test_number_not_empty(self):
        """测试数字不是空"""
        assert _is_empty(0) is False
        assert _is_empty(1) is False


class TestHumanize:
    """测试 _humanize 函数"""

    def test_returns_string(self):
        """测试返回值是字符串"""
        evaluation = {
            "passed": True,
            "rule_path": "/path/to/rules.json",
            "rule_sha256": "abc123",
            "project_profile_decision": "allow",
            "reasons": [],
            "suggested_actions": []
        }
        result = _humanize(evaluation)
        assert isinstance(result, str)

    def test_passed_shows_tong_guo(self):
        """测试通过时显示'通过'"""
        evaluation = {"passed": True, "reasons": [], "suggested_actions": []}
        result = _humanize(evaluation)
        assert "通过" in result

    def test_failed_shows_zu_duan(self):
        """测试失败时显示'阻断'"""
        evaluation = {"passed": False, "reasons": [], "suggested_actions": []}
        result = _humanize(evaluation)
        assert "阻断" in result

    def test_shows_reasons(self):
        """测试显示问题原因"""
        evaluation = {
            "passed": False,
            "reasons": [{"code": "TEST_CODE", "severity": "ERROR", "message": "测试消息"}],
            "suggested_actions": []
        }
        result = _humanize(evaluation)
        assert "TEST_CODE" in result
        assert "测试消息" in result
        assert "ERROR" in result

    def test_shows_suggested_actions(self):
        """测试显示建议动作"""
        evaluation = {
            "passed": False,
            "reasons": [],
            "suggested_actions": ["建议1", "建议2"]
        }
        result = _humanize(evaluation)
        assert "建议1" in result
        assert "建议2" in result


class TestRunPrecheckGuard:
    """测试 run_precheck_guard 主函数"""

    def test_returns_dict(self):
        """测试返回值是字典"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """测试返回字典包含必要字段"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        required_keys = {
            "passed", "generated_at_utc", "rule_path", "rule_sha256",
            "input_sha256", "project_profile_decision", "reasons",
            "suggested_actions", "details", "human_readable"
        }
        assert required_keys.issubset(result.keys())

    def test_valid_input_passes(self):
        """测试有效输入通过检查"""
        result = run_precheck_guard(
            {"topic": "合肥市政排水工程施工组织设计", "outline": ["工程概况", "施工准备"]},
            {"decision": "allow"}
        )
        assert result["passed"] is True

    def test_empty_topic_fails(self):
        """测试空 topic 导致检查失败"""
        result = run_precheck_guard(
            {"topic": "", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        assert result["passed"] is False
        assert any(r["code"] == "TOPIC_EMPTY" for r in result["reasons"])

    def test_none_topic_fails(self):
        """测试 None topic 导致检查失败"""
        result = run_precheck_guard(
            {"topic": None, "outline": ["章节1"]},
            {"decision": "allow"}
        )
        assert result["passed"] is False

    def test_empty_outline_fails(self):
        """测试空 outline 导致检查失败"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": []},
            {"decision": "allow"}
        )
        assert result["passed"] is False
        assert any(r["code"] == "OUTLINE_EMPTY" for r in result["reasons"])

    def test_non_list_outline_fails(self):
        """测试非列表 outline 导致检查失败"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": "不是列表"},
            {"decision": "allow"}
        )
        assert result["passed"] is False

    def test_block_and_review_decision_fails(self):
        """测试 block_and_review 决策导致检查失败"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "block_and_review"}
        )
        assert result["passed"] is False
        assert any(r["code"] == "LOW_CONFIDENCE_PROFILE" for r in result["reasons"])

    def test_details_is_list(self):
        """测试 details 是列表"""
        result = run_precheck_guard(
            {"topic": "测试", "outline": ["章节"]},
            {"decision": "allow"}
        )
        assert isinstance(result["details"], list)

    def test_details_have_check_ids(self):
        """测试 details 中每项有 check_id"""
        result = run_precheck_guard(
            {"topic": "测试", "outline": ["章节"]},
            {"decision": "allow"}
        )
        for detail in result["details"]:
            assert "check_id" in detail

    def test_human_readable_is_string(self):
        """测试 human_readable 是字符串"""
        result = run_precheck_guard(
            {"topic": "测试", "outline": ["章节"]},
            {"decision": "allow"}
        )
        assert isinstance(result["human_readable"], str)

    def test_input_sha256_is_stable(self):
        """测试相同输入产生相同 input_sha256"""
        payload = {"topic": "测试项目", "outline": ["章节1"]}
        profile = {"decision": "allow"}
        result1 = run_precheck_guard(payload, profile)
        result2 = run_precheck_guard(payload, profile)
        assert result1["input_sha256"] == result2["input_sha256"]

    def test_empty_project_profile_handled(self):
        """测试空项目画像能正常处理"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {}
        )
        assert isinstance(result, dict)
        assert result["project_profile_decision"] is None

    def test_none_project_profile_handled(self):
        """测试 None 项目画像能正常处理"""
        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            None
        )
        assert isinstance(result, dict)


class TestRequiredFieldsFromRule:
    """测试规则文件中 required_fields 的检查逻辑"""

    def test_required_fields_all_present(self, tmp_path, monkeypatch):
        """测试 required_fields 全部存在时通过"""
        import backend.kg_loader as kg_loader_mod

        # 创建包含 required_fields 的规则文件
        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_text('{"required_fields": ["topic", "outline"]}', encoding="utf-8")

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        assert result["passed"] is True
        # 确保 required_fields 检查被执行
        rf_detail = [d for d in result["details"] if d["check_id"] == "REQUIRED_FIELDS_FROM_RULE"]
        assert len(rf_detail) == 1
        assert rf_detail[0]["passed"] is True

    def test_required_fields_missing(self, tmp_path, monkeypatch):
        """测试 required_fields 缺失时失败"""
        import backend.kg_loader as kg_loader_mod

        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_text('{"required_fields": ["topic", "outline", "project_name", "project_type"]}', encoding="utf-8")

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},  # 缺少 project_name, project_type
            {"decision": "allow"}
        )
        assert result["passed"] is False
        assert any(r["code"] == "MISSING_REQUIRED_FIELDS" for r in result["reasons"])
        assert any("project_name" in a for a in result["suggested_actions"])

    def test_required_fields_non_string_items_ignored(self, tmp_path, monkeypatch):
        """测试 required_fields 中非字符串项被忽略"""
        import backend.kg_loader as kg_loader_mod

        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_text('{"required_fields": ["topic", 123, null, "outline"]}', encoding="utf-8")

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        # 非字符串项被跳过，只检查 topic 和 outline
        assert result["passed"] is True

    def test_required_fields_empty_list(self, tmp_path, monkeypatch):
        """测试 required_fields 为空列表时不执行额外检查"""
        import backend.kg_loader as kg_loader_mod

        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_text('{"required_fields": []}', encoding="utf-8")

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        # 空列表不会添加 REQUIRED_FIELDS_FROM_RULE 检查
        rf_detail = [d for d in result["details"] if d["check_id"] == "REQUIRED_FIELDS_FROM_RULE"]
        assert len(rf_detail) == 0


class TestRuleFileJsonParseError:
    """测试规则文件 JSON 解析失败的分支"""

    def test_invalid_json_rule_file(self, tmp_path, monkeypatch):
        """测试规则文件包含无效 JSON 时不崩溃"""
        import backend.kg_loader as kg_loader_mod

        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_text('{ invalid json content without quotes }', encoding="utf-8")

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        # 解析失败后仍能正常返回结果
        assert isinstance(result, dict)
        assert result["passed"] is True  # 基础检查仍然通过
        assert result["rule_sha256"] is not None  # SHA256 仍然被计算

    def test_binary_rule_file(self, tmp_path, monkeypatch):
        """测试规则文件包含二进制内容时不崩溃"""
        import backend.kg_loader as kg_loader_mod

        rule_file = tmp_path / "guard_rules.json"
        rule_file.write_bytes(b'\x80\x81\x82\x83 not valid utf-8 or json')

        def mock_get_path(cfg):
            return rule_file

        monkeypatch.setattr(kg_loader_mod, "get_precheck_guard_rule_path", mock_get_path)

        result = run_precheck_guard(
            {"topic": "测试项目", "outline": ["章节1"]},
            {"decision": "allow"}
        )
        assert isinstance(result, dict)
        assert result["passed"] is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
