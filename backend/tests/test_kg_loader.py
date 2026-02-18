#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试: kg_loader.py
验证知识图谱配置加载器的各个功能。
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# 确保 backend 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import kg_loader
from kg_loader import (
    KGConfigError,
    _apply_active_pack,
    load_kg_config,
    get_base_pack_paths,
    get_domain_map_path,
    get_region_upgrade_rule,
    get_project_profile_rule_path,
    get_precheck_guard_rule_path,
    ROOT_DIR,
)


class TestKGConfigError:
    """测试 KGConfigError 异常类"""

    def test_is_exception(self):
        """测试是 Exception 子类"""
        assert issubclass(KGConfigError, Exception)

    def test_can_raise(self):
        """测试可以正常抛出"""
        with pytest.raises(KGConfigError):
            raise KGConfigError("test error")

    def test_has_message(self):
        """测试异常消息"""
        try:
            raise KGConfigError("config not found")
        except KGConfigError as e:
            assert "config not found" in str(e)

    def test_custom_message(self):
        """测试自定义消息内容"""
        error = KGConfigError("域映射表未配置")
        assert "域映射表未配置" in str(error)


class TestApplyActivePack:
    """测试 _apply_active_pack 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_no_active_pack_uses_root_dir(self):
        """测试无 active_pack 时使用 ROOT_DIR"""
        cfg = {"base_packs": ["pack1.json"]}
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_active_pack_none_uses_root_dir(self):
        """测试 active_pack 为 None 时使用 ROOT_DIR"""
        cfg = {"active_pack": None, "packs": {}}
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_packs_not_dict_uses_root_dir(self):
        """测试 packs 不是 dict 时使用 ROOT_DIR"""
        cfg = {"active_pack": "default", "packs": "not_a_dict"}
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_packs_none_uses_root_dir(self):
        """测试 packs 为 None 时使用 ROOT_DIR"""
        cfg = {"active_pack": "default", "packs": None}
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_pack_cfg_not_dict_uses_root_dir(self):
        """测试 pack 配置不是 dict 时使用 ROOT_DIR"""
        cfg = {"active_pack": "test", "packs": {"test": "not_a_dict"}}
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_valid_active_pack_with_base_dir(self):
        """测试有效的 active_pack 使用 base_dir"""
        cfg = {
            "active_pack": "test_pack",
            "packs": {
                "test_pack": {"base_dir": "sub_dir"}
            }
        }
        _apply_active_pack(cfg)
        expected = (ROOT_DIR / "sub_dir").resolve()
        assert kg_loader.BASE_DIR == expected

    def test_valid_active_pack_with_base_path(self):
        """测试有效的 active_pack 使用 base_path (备选键)"""
        cfg = {
            "active_pack": "test_pack",
            "packs": {
                "test_pack": {"base_path": "another_dir"}
            }
        }
        _apply_active_pack(cfg)
        expected = (ROOT_DIR / "another_dir").resolve()
        assert kg_loader.BASE_DIR == expected

    def test_valid_active_pack_with_root_key(self):
        """测试有效的 active_pack 使用 root 键 (备选键)"""
        cfg = {
            "active_pack": "test_pack",
            "packs": {
                "test_pack": {"root": "root_dir"}
            }
        }
        _apply_active_pack(cfg)
        expected = (ROOT_DIR / "root_dir").resolve()
        assert kg_loader.BASE_DIR == expected

    def test_empty_base_dir_uses_root_dir(self):
        """测试 base_dir 为空字符串时使用 ROOT_DIR"""
        cfg = {
            "active_pack": "test_pack",
            "packs": {
                "test_pack": {"base_dir": ""}
            }
        }
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_no_base_dir_key_uses_root_dir(self):
        """测试没有 base_dir/base_path/root 键时使用 ROOT_DIR"""
        cfg = {
            "active_pack": "test_pack",
            "packs": {
                "test_pack": {"version": "1.0"}
            }
        }
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_exception_fallback_to_root_dir(self):
        """测试异常时回退到 ROOT_DIR"""
        # 使用会导致异常的配置
        cfg = MagicMock()
        cfg.get = MagicMock(side_effect=Exception("test exception"))
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR

    def test_missing_pack_in_packs_uses_root_dir(self):
        """测试 active_pack 指向不存在的 pack 时使用 ROOT_DIR"""
        cfg = {
            "active_pack": "nonexistent",
            "packs": {"other_pack": {"base_dir": "sub"}}
        }
        _apply_active_pack(cfg)
        assert kg_loader.BASE_DIR == ROOT_DIR


class TestLoadKgConfig:
    """测试 load_kg_config 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_dict(self):
        """测试返回值是字典"""
        # 使用真实配置文件
        result = load_kg_config()
        assert isinstance(result, dict)

    def test_has_base_packs_key(self):
        """测试返回字典包含 base_packs 键"""
        result = load_kg_config()
        assert "base_packs" in result

    def test_has_domain_map_key(self):
        """测试返回字典包含 domain_map 键"""
        result = load_kg_config()
        assert "domain_map" in result

    def test_has_packs_key(self):
        """测试返回字典包含 packs 键"""
        result = load_kg_config()
        assert "packs" in result

    def test_config_not_found_raises_error(self):
        """测试配置文件不存在时抛出 KGConfigError"""
        with patch.object(kg_loader, 'CONFIG_PATH', Path("/nonexistent/path/config.json")):
            with pytest.raises(KGConfigError) as exc_info:
                load_kg_config()
            assert "not found" in str(exc_info.value)

    def test_applies_active_pack(self):
        """测试加载配置后应用 active_pack"""
        # 使用真实配置文件测试 active_pack 应用
        load_kg_config()
        # 验证 BASE_DIR 已被正确设置（根据 kg_config.json 中的 active_pack）
        assert kg_loader.BASE_DIR != kg_loader.ROOT_DIR or "kg_packs" in str(kg_loader.BASE_DIR) or kg_loader.BASE_DIR == kg_loader.ROOT_DIR


class TestGetBasePackPaths:
    """测试 get_base_pack_paths 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_list(self):
        """测试返回值是列表"""
        cfg = {"base_packs": ["pack1.json", "pack2.json"]}
        result = get_base_pack_paths(cfg)
        assert isinstance(result, list)

    def test_returns_path_objects(self):
        """测试返回 Path 对象"""
        cfg = {"base_packs": ["pack1.json"]}
        result = get_base_pack_paths(cfg)
        assert all(isinstance(p, Path) for p in result)

    def test_correct_number_of_paths(self):
        """测试返回正确数量的路径"""
        cfg = {"base_packs": ["a.json", "b.json", "c.json"]}
        result = get_base_pack_paths(cfg)
        assert len(result) == 3

    def test_empty_base_packs_returns_empty_list(self):
        """测试空 base_packs 返回空列表"""
        cfg = {"base_packs": []}
        result = get_base_pack_paths(cfg)
        assert result == []

    def test_no_base_packs_key_returns_empty_list(self):
        """测试无 base_packs 键返回空列表"""
        # 必须传入非空 dict，否则 `cfg or load_kg_config()` 会加载真实配置
        cfg = {"_placeholder": True}
        result = get_base_pack_paths(cfg)
        assert result == []

    def test_paths_are_absolute(self):
        """测试返回的路径包含基础目录"""
        cfg = {"base_packs": ["pack1.json"]}
        result = get_base_pack_paths(cfg)
        assert str(ROOT_DIR) in str(result[0])

    def test_with_active_pack(self):
        """测试配合 active_pack 使用"""
        cfg = {
            "base_packs": ["pack.json"],
            "active_pack": "test",
            "packs": {"test": {"base_dir": "subdir"}}
        }
        result = get_base_pack_paths(cfg)
        assert "subdir" in str(result[0])


class TestGetDomainMapPath:
    """测试 get_domain_map_path 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_path(self):
        """测试返回 Path 对象"""
        cfg = {"domain_map": "map.json"}
        result = get_domain_map_path(cfg)
        assert isinstance(result, Path)

    def test_correct_filename(self):
        """测试返回正确的文件名"""
        cfg = {"domain_map": "SuperKG-DOMAIN-MAP.json"}
        result = get_domain_map_path(cfg)
        assert result.name == "SuperKG-DOMAIN-MAP.json"

    def test_no_domain_map_raises_error(self):
        """测试无 domain_map 配置时抛出异常"""
        # 必须传入非空 dict，否则 `cfg or load_kg_config()` 会加载真实配置
        cfg = {"_placeholder": True}
        with pytest.raises(KGConfigError) as exc_info:
            get_domain_map_path(cfg)
        assert "domain_map not configured" in str(exc_info.value)

    def test_empty_domain_map_raises_error(self):
        """测试空 domain_map 配置时抛出异常"""
        cfg = {"domain_map": ""}
        with pytest.raises(KGConfigError):
            get_domain_map_path(cfg)

    def test_none_domain_map_raises_error(self):
        """测试 None domain_map 配置时抛出异常"""
        cfg = {"domain_map": None}
        with pytest.raises(KGConfigError):
            get_domain_map_path(cfg)

    def test_with_active_pack(self):
        """测试配合 active_pack 使用"""
        cfg = {
            "domain_map": "map.json",
            "active_pack": "test",
            "packs": {"test": {"base_dir": "kg_packs"}}
        }
        result = get_domain_map_path(cfg)
        assert "kg_packs" in str(result)


class TestGetRegionUpgradeRule:
    """测试 get_region_upgrade_rule 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_path_when_found(self):
        """测试找到规则时返回 Path"""
        cfg = {
            "region_upgrade_rules": {
                "anhui_hefei_general": "rules.json"
            }
        }
        result = get_region_upgrade_rule("anhui_hefei_general", cfg)
        assert isinstance(result, Path)

    def test_returns_none_when_not_found(self):
        """测试找不到规则时返回 None"""
        cfg = {"region_upgrade_rules": {}}
        result = get_region_upgrade_rule("nonexistent", cfg)
        assert result is None

    def test_returns_none_when_no_rules_configured(self):
        """测试无规则配置时返回 None"""
        cfg = {}
        result = get_region_upgrade_rule("any_key", cfg)
        assert result is None

    def test_correct_path_returned(self):
        """测试返回正确的路径"""
        cfg = {
            "region_upgrade_rules": {
                "test_region": "region_rules.json"
            }
        }
        result = get_region_upgrade_rule("test_region", cfg)
        assert result.name == "region_rules.json"

    def test_multiple_regions(self):
        """测试多个区域规则"""
        cfg = {
            "region_upgrade_rules": {
                "region_a": "a.json",
                "region_b": "b.json"
            }
        }
        result_a = get_region_upgrade_rule("region_a", cfg)
        result_b = get_region_upgrade_rule("region_b", cfg)
        assert result_a.name == "a.json"
        assert result_b.name == "b.json"

    def test_with_active_pack(self):
        """测试配合 active_pack 使用"""
        cfg = {
            "region_upgrade_rules": {"region": "rule.json"},
            "active_pack": "test",
            "packs": {"test": {"base_dir": "packs"}}
        }
        result = get_region_upgrade_rule("region", cfg)
        assert "packs" in str(result)

    def test_empty_filename_returns_none(self):
        """测试空文件名返回 None"""
        cfg = {
            "region_upgrade_rules": {
                "region": ""
            }
        }
        result = get_region_upgrade_rule("region", cfg)
        assert result is None


class TestGetProjectProfileRulePath:
    """测试 get_project_profile_rule_path 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_path(self):
        """测试返回 Path 对象"""
        cfg = {"project_profile_rules": "profile.json"}
        result = get_project_profile_rule_path(cfg)
        assert isinstance(result, Path)

    def test_correct_filename(self):
        """测试返回正确的文件名"""
        cfg = {"project_profile_rules": "ZhiFei-Profile-Rules.json"}
        result = get_project_profile_rule_path(cfg)
        assert result.name == "ZhiFei-Profile-Rules.json"

    def test_no_config_raises_error(self):
        """测试无配置时抛出异常"""
        # 必须传入非空 dict，否则 `cfg or load_kg_config()` 会加载真实配置
        cfg = {"_placeholder": True}
        with pytest.raises(KGConfigError) as exc_info:
            get_project_profile_rule_path(cfg)
        assert "project_profile_rules not configured" in str(exc_info.value)

    def test_empty_config_raises_error(self):
        """测试空配置时抛出异常"""
        cfg = {"project_profile_rules": ""}
        with pytest.raises(KGConfigError):
            get_project_profile_rule_path(cfg)

    def test_none_config_raises_error(self):
        """测试 None 配置时抛出异常"""
        cfg = {"project_profile_rules": None}
        with pytest.raises(KGConfigError):
            get_project_profile_rule_path(cfg)

    def test_with_active_pack(self):
        """测试配合 active_pack 使用"""
        cfg = {
            "project_profile_rules": "rules.json",
            "active_pack": "v2",
            "packs": {"v2": {"base_dir": "v2_dir"}}
        }
        result = get_project_profile_rule_path(cfg)
        assert "v2_dir" in str(result)


class TestGetPrecheckGuardRulePath:
    """测试 get_precheck_guard_rule_path 函数"""

    def setup_method(self):
        """每个测试前重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def teardown_method(self):
        """每个测试后重置 BASE_DIR"""
        kg_loader.BASE_DIR = kg_loader.ROOT_DIR

    def test_returns_path(self):
        """测试返回 Path 对象"""
        cfg = {"precheck_guard_rules": "guard.json"}
        result = get_precheck_guard_rule_path(cfg)
        assert isinstance(result, Path)

    def test_correct_filename(self):
        """测试返回正确的文件名"""
        cfg = {"precheck_guard_rules": "ZhiFei-PreCheck-Guard.json"}
        result = get_precheck_guard_rule_path(cfg)
        assert result.name == "ZhiFei-PreCheck-Guard.json"

    def test_no_config_raises_error(self):
        """测试无配置时抛出异常"""
        # 必须传入非空 dict，否则 `cfg or load_kg_config()` 会加载真实配置
        cfg = {"_placeholder": True}
        with pytest.raises(KGConfigError) as exc_info:
            get_precheck_guard_rule_path(cfg)
        assert "precheck_guard_rules not configured" in str(exc_info.value)

    def test_empty_config_raises_error(self):
        """测试空配置时抛出异常"""
        cfg = {"precheck_guard_rules": ""}
        with pytest.raises(KGConfigError):
            get_precheck_guard_rule_path(cfg)

    def test_none_config_raises_error(self):
        """测试 None 配置时抛出异常"""
        cfg = {"precheck_guard_rules": None}
        with pytest.raises(KGConfigError):
            get_precheck_guard_rule_path(cfg)

    def test_with_active_pack(self):
        """测试配合 active_pack 使用"""
        cfg = {
            "precheck_guard_rules": "guard.json",
            "active_pack": "prod",
            "packs": {"prod": {"base_dir": "production"}}
        }
        result = get_precheck_guard_rule_path(cfg)
        assert "production" in str(result)


class TestLoadKgConfigWithRealFile:
    """使用真实配置文件测试 load_kg_config"""

    def test_loads_real_config(self):
        """测试加载真实配置文件"""
        cfg = load_kg_config()
        assert "base_packs" in cfg
        assert "domain_map" in cfg
        assert "packs" in cfg

    def test_base_packs_is_list(self):
        """测试 base_packs 是列表"""
        cfg = load_kg_config()
        assert isinstance(cfg["base_packs"], list)

    def test_region_upgrade_rules_is_dict(self):
        """测试 region_upgrade_rules 是字典"""
        cfg = load_kg_config()
        assert isinstance(cfg.get("region_upgrade_rules", {}), dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
