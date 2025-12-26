import json
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "kg_config.json"


class KGConfigError(Exception):
    """知识图谱配置异常。"""
    pass


def load_kg_config() -> Dict:
    """读取 kg_config.json 并返回字典。"""
    if not CONFIG_PATH.exists():
        raise KGConfigError(f"KG config not found: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_base_pack_paths(cfg: Optional[Dict] = None) -> List[Path]:
    """返回所有基础包的绝对路径列表。"""
    cfg = cfg or load_kg_config()
    packs = cfg.get("base_packs", [])
    return [BASE_DIR / p for p in packs]


def get_domain_map_path(cfg: Optional[Dict] = None) -> Path:
    """返回 SuperKG 域映射表路径。"""
    cfg = cfg or load_kg_config()
    filename = cfg.get("domain_map")
    if not filename:
        raise KGConfigError("domain_map not configured in kg_config.json")
    return BASE_DIR / filename


def get_region_upgrade_rule(region_key: str, cfg: Optional[Dict] = None) -> Optional[Path]:
    """
    根据区域 key 返回对应的升级规则文件路径。
    例如：region_key = "anhui_hefei_general"。
    """
    cfg = cfg or load_kg_config()
    mapping = cfg.get("region_upgrade_rules", {})
    filename = mapping.get(region_key)
    if not filename:
        return None
    return BASE_DIR / filename


def get_project_profile_rule_path(cfg: Optional[Dict] = None) -> Path:
    """返回项目画像规则文件路径。"""
    cfg = cfg or load_kg_config()
    filename = cfg.get("project_profile_rules")
    if not filename:
        raise KGConfigError("project_profile_rules not configured in kg_config.json")
    return BASE_DIR / filename


def get_precheck_guard_rule_path(cfg: Optional[Dict] = None) -> Path:
    """返回生成前预检查 Guard 规则文件路径。"""
    cfg = cfg or load_kg_config()
    filename = cfg.get("precheck_guard_rules")
    if not filename:
        raise KGConfigError("precheck_guard_rules not configured in kg_config.json")
    return BASE_DIR / filename
