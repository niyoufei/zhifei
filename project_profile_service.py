# -*- coding: utf-8 -*-
"""
ProjectProfile 生成服务（V1）
- 规则文件来源：kg_config.json -> project_profile_rules
- 输出：可追溯、可复核的 ProjectProfile dict
- 说明：当前为“保守型”规则/关键词推断：宁可低置信度也不冒进；低于阈值将标记 require_manual_confirm/block_and_review
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import kg_loader


def _stable_sha256(obj: Any) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8", "replace")
    return hashlib.sha256(data).hexdigest()


def _extract_text(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    # 常见字段兜底：只要是字符串就拼接，避免漏信息
    for k in (
        "project_name", "project_title",
        "topic", "outline", "description",
        "content", "text",
        "工程名称", "项目名称", "工点名称",
    ):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return "\n".join(parts)


def _infer_project_type(payload: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    # 1) 显式输入优先（不推断）
    for k in ("project_type", "工程类型", "project_category", "domain_cn"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return {
                "value": v.strip(),
                "confidence": 1.0,
                "source": f"explicit:{k}",
                "evidence": [f"payload.{k}"],
            }

    # 2) 关键词推断（低风险：仅作为候选，默认不直接 auto_accept）
    text = _extract_text(payload)
    if not text:
        return {"value": None, "confidence": 0.0, "source": "none", "evidence": []}

    # 规则文件可能给了 base_confidence，但对“关键词推断”要做上限约束，防止误判高置信
    pti = rules.get("project_type_inference") if isinstance(rules.get("project_type_inference"), dict) else {}
    base_conf = float(pti.get("base_confidence", 0.75)) if isinstance(pti, dict) else 0.75
    # 对 keyword 推断，强制不超过 0.80
    base_conf = min(base_conf, 0.80)

    mapping: List[Tuple[str, List[str]]] = [
        ("幕墙工程", ["幕墙", "玻璃幕墙", "石材幕墙", "铝板幕墙", "单元式幕墙"]),
        ("装饰装修", ["装修", "装饰", "精装", "室内装饰", "吊顶", "墙面", "地面", "涂料", "石材", "木饰面"]),
        ("市政排水", ["排水", "雨水", "污水", "雨污", "管网", "管道", "顶管", "检查井", "泵站", "污水处理"]),
        ("市政道路", ["市政道路", "道路", "路面", "沥青", "水稳", "路基", "人行道", "交通导改", "标线", "标志"]),
        ("房建", ["房建", "住宅", "楼", "主体结构", "钢筋", "混凝土", "基础", "桩基", "结构施工"]),
        ("机电安装", ["机电", "暖通", "空调", "电气", "消防", "给排水", "弱电", "桥架", "风管", "管线"]),
        ("园林景观", ["园林", "绿化", "景观", "铺装", "广场", "乔木", "灌木", "草坪", "园建"]),
    ]

    hits: List[Tuple[str, int, List[str]]] = []
    for ptype, kws in mapping:
        found = [kw for kw in kws if kw in text]
        if found:
            hits.append((ptype, len(found), found))

    if not hits:
        return {"value": None, "confidence": 0.0, "source": "keyword:none", "evidence": []}

    hits.sort(key=lambda x: x[1], reverse=True)
    ptype, n, found = hits[0]

    conf = min(0.85, base_conf + 0.03 * max(0, n - 1))
    # 仍然保守：最多 0.85，不直接超过 auto_accept
    conf = round(conf, 2)

    return {"value": ptype, "confidence": conf, "source": "keyword", "evidence": found}


def _infer_mandatory_dimensions(project_type: Optional[str], rules: Dict[str, Any]) -> List[str]:
    mdi = rules.get("mandatory_dimension_inference", {})
    if not isinstance(mdi, dict):
        return []
    base_rules = mdi.get("base_rules", [])
    if not isinstance(base_rules, list):
        return []
    if not project_type:
        return []
    for r in base_rules:
        if not isinstance(r, dict):
            continue
        if r.get("if_project_type") == project_type:
            dims = r.get("mandatory_dimensions", [])
            return dims if isinstance(dims, list) else []
    return []


def generate_project_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = kg_loader.load_kg_config()
    rule_path: Path = kg_loader.get_project_profile_rule_path(cfg)
    rules = json.loads(rule_path.read_text(encoding="utf-8", errors="replace"))

    thresholds = rules.get("confidence_thresholds", {}) if isinstance(rules.get("confidence_thresholds"), dict) else {}
    auto_accept = float(thresholds.get("auto_accept", 0.85))
    require_manual = float(thresholds.get("require_manual_confirm", 0.70))

    project_type_info = _infer_project_type(payload, rules)
    ptype = project_type_info.get("value")
    conf = float(project_type_info.get("confidence", 0.0) or 0.0)

    if conf >= auto_accept:
        decision = "auto_accept"
    elif conf >= require_manual:
        decision = "require_manual_confirm"
    else:
        decision = "block_and_review"

    mandatory_dims = _infer_mandatory_dimensions(ptype, rules)

    profile = {
        "profile_rule_version": rules.get("profile_rule_version"),
        "rule_path": str(rule_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": _stable_sha256(payload),

        "project_type": project_type_info,
        "mandatory_dimensions": mandatory_dims,

        # 直接透传配置，供后续 PreCheck/Upgrade 使用
        "technology_tolerance_inference": rules.get("technology_tolerance_inference", {}),
        "logic_chain_policy": rules.get("logic_chain_policy", {}),
        "confidence_thresholds": thresholds,

        "decision": decision,

        "audit": {
            "engine": "project_profile_service.v1",
            "note": "keyword inference is conservative; below threshold requires manual confirm/review",
        },
    }
    return profile


__all__ = ["generate_project_profile"]
# ==============================
# [PATCH] project_profile_rule_meta
# Add rule file path + sha256 into ProjectProfile for traceability
# ==============================
from pathlib import Path as _PP_Path
import hashlib as _PP_hashlib

def _pp_sha256_file(_p: _PP_Path) -> str:
    _h = _PP_hashlib.sha256()
    with open(_p, "rb") as _f:
        for _chunk in iter(lambda: _f.read(1024 * 1024), b""):
            _h.update(_chunk)
    return _h.hexdigest()

try:
    _pp_old_generate_project_profile = generate_project_profile  # noqa: F821
except Exception:
    _pp_old_generate_project_profile = None

def generate_project_profile(payload: dict):
    if _pp_old_generate_project_profile is None:
        raise RuntimeError("generate_project_profile not defined before patch block")
    profile = _pp_old_generate_project_profile(payload)
    try:
        import kg_loader as _pp_kg_loader
        _rp = _pp_kg_loader.get_project_profile_rule_path()
        profile["rule_path"] = str(_rp)
        profile["rule_sha256"] = _pp_sha256_file(_rp)
    except Exception as _e:
        profile.setdefault("errors", [])
        profile["errors"].append({"stage": "project_profile_rule_meta", "error": repr(_e)})
    return profile
