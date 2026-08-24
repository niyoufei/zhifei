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

from backend import kg_loader


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

    # 规则文件中的项目类型规则优先；内置规则仅补充规则文件未覆盖的类型。
    pti = rules.get("project_type_inference") if isinstance(rules.get("project_type_inference"), dict) else {}
    configured_rules = pti.get("rules", []) if isinstance(pti, dict) else []
    candidates: List[Tuple[str, List[str], float, str]] = []
    configured_types = set()
    for rule in configured_rules if isinstance(configured_rules, list) else []:
        if not isinstance(rule, dict):
            continue
        project_type = str(rule.get("then_project_type") or "").strip()
        keywords = [str(item).strip() for item in rule.get("if_keywords", []) if str(item).strip()]
        if not project_type or not keywords:
            continue
        try:
            confidence = float(rule.get("base_confidence", 0.75))
        except (TypeError, ValueError):
            confidence = 0.75
        candidates.append((project_type, keywords, confidence, "rule_keyword"))
        configured_types.add(project_type)

    built_in_rules: List[Tuple[str, List[str], float, str]] = [
        ("幕墙工程", ["幕墙", "玻璃幕墙", "石材幕墙", "铝板幕墙", "单元式幕墙"], 0.75, "keyword"),
        ("装饰装修", ["装修", "装饰", "精装", "室内装饰", "吊顶", "墙面", "地面", "涂料", "石材", "木饰面"], 0.75, "keyword"),
        ("市政排水", ["排水", "雨水", "污水", "雨污", "管网", "管道", "顶管", "检查井", "泵站", "污水处理"], 0.75, "keyword"),
        ("市政道路", ["市政道路", "道路", "路面", "沥青", "水稳", "路基", "人行道", "交通导改", "标线", "标志"], 0.75, "keyword"),
        ("房建", ["房建", "住宅", "楼", "主体结构", "钢筋", "混凝土", "基础", "桩基", "结构施工"], 0.75, "keyword"),
        ("机电安装", ["机电", "暖通", "空调", "电气", "消防", "给排水", "弱电", "桥架", "风管", "管线"], 0.75, "keyword"),
        ("园林景观", ["园林", "绿化", "景观", "铺装", "广场", "乔木", "灌木", "草坪", "园建"], 0.75, "keyword"),
    ]
    candidates.extend(rule for rule in built_in_rules if rule[0] not in configured_types)

    hits: List[Tuple[str, int, List[str], float, str]] = []
    for ptype, kws, base_confidence, source in candidates:
        found = [kw for kw in kws if kw in text]
        if found:
            hits.append((ptype, len(found), found, base_confidence, source))

    if not hits:
        fallback = pti.get("fallback", {}) if isinstance(pti, dict) else {}
        if isinstance(fallback, dict) and str(fallback.get("project_type") or "").strip():
            try:
                confidence = float(fallback.get("base_confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            return {
                "value": str(fallback["project_type"]).strip(),
                "confidence": round(max(0.0, min(confidence, 1.0)), 2),
                "source": "rule_fallback",
                "evidence": [],
            }
        return {"value": None, "confidence": 0.0, "source": "keyword:none", "evidence": []}

    hits.sort(key=lambda x: x[1], reverse=True)
    ptype, n, found, base_confidence, source = hits[0]

    # 单纯关键词命中不得凭规则声明直接跃升到自动接受。
    conf = min(0.85, min(max(base_confidence, 0.0), 0.80) + 0.03 * max(0, n - 1))
    # 仍然保守：最多 0.85，不直接超过 auto_accept
    conf = round(conf, 2)

    return {"value": ptype, "confidence": conf, "source": source, "evidence": found}


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
    rule_bytes = rule_path.read_bytes()
    rules = json.loads(rule_bytes.decode("utf-8", errors="replace"))

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
        "rule_sha256": hashlib.sha256(rule_bytes).hexdigest(),
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
