from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .dxf_parser import parse_dxf_payload
from .ifc_parser import parse_ifc_payload
from .kg_paths import resolve_default_kg_root
from .regional_policy_plugins import resolve_regional_policy_plugin
from .revit_parser import parse_revit_payload

SUPPORTED_EXTENSIONS = {".json", ".md", ".markdown", ".xml", ".csv", ".dxf", ".ifc", ".ifcxml", ".rvt"}
DEFAULT_KG_ROOT = resolve_default_kg_root()
DEFAULT_DB_PATH = Path("backend/data/autoplan/v2/knowledge_graph.sqlite3")

EDGE_REQUIRES = "REQUIRES"
EDGE_MITIGATES = "MITIGATES"
EDGE_CONFLICTS_WITH = "CONFLICTS_WITH"
EDGE_BELONGS_TO = "BELONGS_TO"
EDGE_TYPES = (EDGE_REQUIRES, EDGE_MITIGATES, EDGE_CONFLICTS_WITH, EDGE_BELONGS_TO)

SOURCE_HIERARCHY_RULE = "答疑文件 > 设计图纸 > 国标 > 行标 > 企标"
SOURCE_HIERARCHY_WEIGHTS: Dict[str, int] = {
    "答疑文件": 5,
    "设计图纸": 4,
    "国标": 3,
    "行标": 2,
    "企标": 1,
    "未知": 0,
}

DEFAULT_RETRIEVAL_SCORE_WEIGHTS: Dict[str, float] = {
    "tag_weight": 1.0,
    "keyword_exact_weight": 1.0,
    "keyword_fuzzy_weight": 1.0,
    "query_token_weight": 1.0,
    "fts_rank_weight": 1.0,
    "domain_weight": 1.0,
    "gemini_weight_scale": 1.0,
    "retrieval_quality_weight_scale": 1.0,
    "approval_bonus_weight": 1.0,
    "timeline_weight": 1.0,
    "region_weight": 1.0,
}

DEFAULT_FORMULA_EXPRESSION = "quantity / max(productivity_per_day, 1)"

PROFESSIONAL_DOMAIN_SEEDS: Dict[str, Tuple[str, ...]] = {
    "bridge": ("bridge", "桥梁", "箱梁", "桥面", "挂篮", "盖梁", "桥墩"),
    "tunnel": ("tunnel", "隧道", "盾构", "衬砌", "洞门", "暗挖"),
    "railway": ("railway", "rail", "铁路", "轨道", "高铁", "接触网", "营业线"),
    "hydraulic": ("hydraulic", "hydro", "water", "水利", "泵站", "闸门", "河道", "堤防", "引水"),
    "mep": ("mep", "机电", "电气", "暖通", "消防", "管道", "桥架", "弱电", "智能化"),
    "earthwork": ("earthwork", "土石方", "土方", "开挖", "回填", "基坑", "边坡"),
    "road": ("road", "道路", "路基", "路面", "沥青", "交通导改", "市政道路"),
    "building": ("building", "房建", "主体结构", "砌体", "装修", "幕墙", "钢结构", "装配式"),
    "general": ("general", "综合", "通用"),
}

QUERY_DIMENSION_SEEDS: Dict[str, Tuple[str, ...]] = {
    "质量": ("质量", "验收", "偏差", "强度", "抽检"),
    "安全": ("安全", "隐患", "危大", "应急", "事故"),
    "进度": ("进度", "工期", "关键线路", "节点", "里程碑"),
    "环保": ("环保", "扬尘", "噪声", "pm10", "污水"),
    "重难点": ("重难点", "复杂", "接口", "高风险", "专项"),
    "扣分点": ("扣分", "否决", "处罚", "废标", "失分"),
}

LONG_TAIL_TRANSFER_DEFAULT: Dict[str, Dict[str, Any]] = {
    "airport": {"fallback_domains": ["road", "building", "mep"], "transfer_factor": 0.85},
    "petrochemical": {"fallback_domains": ["mep", "earthwork", "management"], "transfer_factor": 0.82},
    "offshorewind-marine": {"fallback_domains": ["hydraulic", "mep", "management"], "transfer_factor": 0.86},
    "port-harbor": {"fallback_domains": ["hydraulic", "road", "management"], "transfer_factor": 0.84},
    "data-center": {"fallback_domains": ["mep", "building", "digital"], "transfer_factor": 0.88},
}

DNA_CONTEXT_ENV_KEYS = ("ZHIFEI_DNA_CONTEXT", "ZF_DNA_CONTEXT", "TACTICAL_DNA_CONTEXT")

RELATION_KEYS: Dict[str, Tuple[str, ...]] = {
    EDGE_REQUIRES: (
        "requires",
        "requires_nodes",
        "predecessors",
        "depends_on",
        "前置",
        "前置工序",
        "前置约束",
    ),
    EDGE_MITIGATES: (
        "mitigates",
        "mitigates_nodes",
        "controls_risk_of",
        "risk_controls",
        "缓解",
        "控制风险",
    ),
    EDGE_CONFLICTS_WITH: (
        "conflicts_with",
        "mutually_exclusive_with",
        "exclusions",
        "互斥",
        "冲突工艺",
    ),
    EDGE_BELONGS_TO: (
        "belongs_to",
        "layer",
        "from_layer",
        "所属图层",
    ),
}

ALLOWED_FORMULA_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}

ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Call,
)


@dataclass
class ParsedEdgeDraft:
    from_ref: str
    to_ref: str
    edge_type: str
    edge_label: str = ""


@dataclass
class ParsedNode:
    uid: str
    title: str
    body: str
    tags: List[str]
    keywords: List[str]
    payload_json: str
    node_type: str = "EngineeringNode"
    object_key: str = ""
    applicable_conditions_json: str = "{}"
    resource_requirements_json: str = "{}"
    safety_level: str = "unknown"
    source_hierarchy: str = "企标"
    formula_expression: str = ""
    formula_variables_json: str = "[]"
    data_source_type: str = "FILE"
    spatial_context_json: str = "{}"
    activation_signal: str = ""
    dna_verified: int = 1
    tactical_mode: str = ""
    bid_response_strategy_json: str = "{}"
    competitor_shield_json: str = "{}"
    qt_score_booster_json: str = "{}"
    quantitative_indices_json: str = "{}"
    numeric_sources_json: str = "[]"
    schedule_constraints_json: str = "{}"
    standard_validity_timeline_json: str = "{}"
    regional_policy_layers_json: str = "{}"
    unit_dimension_model_json: str = "{}"
    evidence_anchors_json: str = "[]"
    cross_discipline_constraints_json: str = "{}"
    retrieval_benchmark_json: str = "{}"
    approval_workflow_json: str = "{}"
    formula_sensitivity_json: str = "{}"
    bim_ifc_context_json: str = "{}"
    incremental_fingerprint: str = ""
    incremental_update_json: str = "{}"
    reference_keys: List[str] = field(default_factory=list)
    edge_drafts: List[ParsedEdgeDraft] = field(default_factory=list)


def _sha256_bytes(content: bytes) -> str:
    h = hashlib.sha256()
    h.update(content)
    return h.hexdigest()


def _normalize_term(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _normalize_key(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "").strip().lower())


def _normalize_alias(value: str) -> str:
    return _normalize_key(value)


def _tokenize(text: str) -> List[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-/]{1,}|\d+(?:\.\d+)?", text or "")
    out: List[str] = []
    seen = set()
    for part in parts:
        term = _normalize_term(part)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_retrieval_score_weights(profile_path: Path | str | None) -> Dict[str, float]:
    out = dict(DEFAULT_RETRIEVAL_SCORE_WEIGHTS)
    if profile_path in (None, ""):
        return out
    p = Path(profile_path).expanduser().resolve()
    if not p.exists():
        return out
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return out
    weights = payload.get("weights") if isinstance(payload, dict) else {}
    if not isinstance(weights, dict):
        return out
    for key in out.keys():
        if key not in weights:
            continue
        value = _safe_float(weights.get(key), out[key])
        out[key] = max(0.2, min(3.0, value))
    return out


def _safe_date_key(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    m = re.search(r"((?:19|20)\d{2})[-/.年]?(\d{1,2})?[-/.月]?(\d{1,2})?", text)
    if not m:
        return 0
    year = int(m.group(1))
    month = int(m.group(2) or 1)
    day = int(m.group(3) or 1)
    if month < 1 or month > 12:
        month = 1
    if day < 1 or day > 31:
        day = 1
    return year * 10000 + month * 100 + day


def _timeline_match_for_bid(
    timeline: Dict[str, Any],
    *,
    bid_date_key: int,
    allow_superseded: bool,
) -> Dict[str, Any]:
    if bid_date_key <= 0:
        return {"allow": True, "state": "not_checked", "matched_record": {}}
    if not isinstance(timeline, dict):
        return {"allow": True, "state": "no_timeline", "matched_record": {}}
    records = timeline.get("records")
    if not isinstance(records, list) or not records:
        return {"allow": True, "state": "no_timeline_records", "matched_record": {}}

    parsed: List[Tuple[int, int, Dict[str, Any]]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        eff = _safe_date_key(rec.get("effective_date"))
        exp = _safe_date_key(rec.get("expiry_date"))
        if eff <= 0:
            eff = 19000101
        if exp <= 0:
            exp = 29991231
        parsed.append((eff, exp, rec))
    if not parsed:
        return {"allow": True, "state": "invalid_timeline_records", "matched_record": {}}

    parsed.sort(key=lambda x: (x[0], x[1]), reverse=True)
    matched = None
    for eff, exp, rec in parsed:
        if bid_date_key >= eff:
            matched = (eff, exp, rec)
            break
    if matched is None:
        matched = parsed[-1]

    eff, exp, rec = matched
    status = str(rec.get("status") or "").strip().lower()
    superseded = bool(str(rec.get("superseded_by") or "").strip() or status == "superseded")

    if bid_date_key < eff:
        return {
            "allow": False,
            "state": "pre_effective",
            "matched_record": rec,
            "effective_date": rec.get("effective_date"),
            "expiry_date": rec.get("expiry_date"),
        }
    if bid_date_key > exp:
        return {
            "allow": False,
            "state": "expired",
            "matched_record": rec,
            "effective_date": rec.get("effective_date"),
            "expiry_date": rec.get("expiry_date"),
        }
    if superseded and not allow_superseded:
        return {
            "allow": False,
            "state": "superseded",
            "matched_record": rec,
            "effective_date": rec.get("effective_date"),
            "expiry_date": rec.get("expiry_date"),
            "superseded_by": rec.get("superseded_by"),
        }
    return {
        "allow": True,
        "state": "active" if not superseded else "superseded_allowed",
        "matched_record": rec,
        "effective_date": rec.get("effective_date"),
        "expiry_date": rec.get("expiry_date"),
        "superseded_by": rec.get("superseded_by"),
    }


def _contains_any_token(blob: str, values: List[str]) -> bool:
    if not values:
        return False
    upper_blob = str(blob or "").upper()
    for val in values:
        token = str(val or "").strip().upper()
        if token and token in upper_blob:
            return True
    return False


def _evaluate_region_plugin(
    *,
    plugin: Dict[str, Any],
    regional_policy_layers: Dict[str, Any],
    payload: Dict[str, Any],
    source_hierarchy: str,
) -> Dict[str, Any]:
    if not isinstance(plugin, dict):
        return {"allow": True, "bonus": 0.0, "reasons": []}

    blob = json.dumps(regional_policy_layers, ensure_ascii=False).upper()
    refs = payload.get("reference_standard_codes")
    if not isinstance(refs, list):
        refs = payload.get("reference_standard")
    if isinstance(refs, list):
        refs_blob = " ".join(str(x) for x in refs)
    else:
        refs_blob = str(refs or "")
    policy_blob = f"{blob}\n{refs_blob.upper()}"

    require_codes = [str(x).strip() for x in (plugin.get("require_any_policy_codes") or []) if str(x).strip()]
    if require_codes and not _contains_any_token(policy_blob, require_codes):
        return {"allow": False, "bonus": 0.0, "reasons": ["missing_required_policy_code"]}

    exclude_codes = [str(x).strip() for x in (plugin.get("exclude_policy_codes") or []) if str(x).strip()]
    if exclude_codes and _contains_any_token(policy_blob, exclude_codes):
        return {"allow": False, "bonus": 0.0, "reasons": ["hit_excluded_policy_code"]}

    reasons: List[str] = []
    bonus = float(plugin.get("region_bonus") or 0.0)
    prefer_codes = [str(x).strip() for x in (plugin.get("prefer_policy_codes") or []) if str(x).strip()]
    if prefer_codes:
        hit_prefer = [code for code in prefer_codes if code.upper() in policy_blob]
        if hit_prefer:
            bonus += min(2.0, len(hit_prefer) * 0.3)
            reasons.append("prefer_policy_code_matched")

    min_source = str(plugin.get("source_hierarchy_min") or "").strip()
    if min_source:
        cur_w = int(SOURCE_HIERARCHY_WEIGHTS.get(str(source_hierarchy or "未知"), 0))
        min_w = int(SOURCE_HIERARCHY_WEIGHTS.get(min_source, 0))
        if cur_w < min_w:
            return {"allow": False, "bonus": 0.0, "reasons": ["source_hierarchy_below_min"]}
        reasons.append("source_hierarchy_meets_min")

    return {"allow": True, "bonus": round(bonus, 4), "reasons": reasons}


def _normalize_domain(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", str(value or "").strip().lower())


def _domain_match(
    *,
    professional_domains: List[str],
    title: str,
    body: str,
    tags: List[str],
    keywords: List[str],
    source_file: str,
) -> Tuple[float, List[str]]:
    if not professional_domains:
        return 0.0, []
    if "general" in professional_domains:
        return 0.0, ["general"]
    merged = " ".join(
        [str(title or ""), str(body or ""), str(source_file or "")]
        + [str(x) for x in tags]
        + [str(x) for x in keywords]
    ).lower()
    matched: List[str] = []
    for domain in professional_domains:
        norm = _normalize_domain(domain)
        seeds = PROFESSIONAL_DOMAIN_SEEDS.get(norm, tuple([norm]))
        if any(str(seed).lower() in merged for seed in seeds):
            matched.append(norm)
    return float(len(matched) * 9.0), matched


def _detect_query_dimensions(query: str, tags: List[str], keywords: List[str]) -> List[str]:
    merged = " ".join([str(query or "")] + [str(x) for x in tags] + [str(x) for x in keywords]).lower()
    dims: List[str] = []
    for dim, seeds in QUERY_DIMENSION_SEEDS.items():
        if any(str(seed).lower() in merged for seed in seeds):
            dims.append(dim)
    return dims


def _match_long_tail_profile(
    *,
    profile: Dict[str, Any],
    professional_domains: List[str],
    title: str,
    body: str,
    tags: List[str],
    keywords: List[str],
) -> Dict[str, Any]:
    if not isinstance(profile, dict) or not bool(profile.get("enabled")):
        return {"matched": False, "score": 0.0, "matches": []}
    if not professional_domains or "general" in professional_domains:
        return {"matched": False, "score": 0.0, "matches": []}

    long_tail_domains = [str(x).strip().lower() for x in (profile.get("long_tail_domains") or []) if str(x).strip()]
    specialty_tag = str(profile.get("specialty_tag") or "").strip().lower()
    if specialty_tag and specialty_tag not in long_tail_domains:
        long_tail_domains.append(specialty_tag)

    fallback_domains = [str(x).strip().lower() for x in (profile.get("fallback_domains") or []) if str(x).strip()]
    merged = " ".join([title, body] + [str(x) for x in tags] + [str(x) for x in keywords]).lower()
    matched_domains: List[str] = []
    for dom in professional_domains:
        token = str(dom or "").strip().lower()
        if not token:
            continue
        if token in long_tail_domains:
            matched_domains.append(token)
            continue
        transfer = LONG_TAIL_TRANSFER_DEFAULT.get(token)
        transfer_fallback = [str(x).strip().lower() for x in ((transfer or {}).get("fallback_domains") or []) if str(x).strip()]
        if fallback_domains and any(x in fallback_domains for x in transfer_fallback):
            matched_domains.append(token)
            continue
        if specialty_tag and specialty_tag in merged and token in LONG_TAIL_TRANSFER_DEFAULT:
            matched_domains.append(token)

    if not matched_domains:
        return {"matched": False, "score": 0.0, "matches": []}
    transfer_factor = _safe_float(profile.get("transfer_factor"), 0.85)
    transfer_factor = max(0.5, min(1.2, transfer_factor))
    score = round(6.0 * len(set(matched_domains)) * transfer_factor, 4)
    return {"matched": True, "score": score, "matches": sorted(set(matched_domains))}


def _build_uncertainty_interval(
    *,
    uncertainty_profile: Dict[str, Any],
    formula_sensitivity: Dict[str, Any],
    quantitative_indices: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(uncertainty_profile, dict) or not bool(uncertainty_profile.get("enabled")):
        return {}
    confidence = _safe_float(uncertainty_profile.get("confidence_level"), 0.0)
    relative = _safe_float(
        uncertainty_profile.get("relative_interval"),
        _safe_float(uncertainty_profile.get("interval_ratio"), 0.0),
    )
    relative = max(0.0, min(0.6, relative))

    baseline = _safe_float(
        uncertainty_profile.get("baseline_result"),
        _safe_float(formula_sensitivity.get("baseline_result"), 0.0),
    )
    if baseline <= 0:
        baseline = max(
            _safe_float(quantitative_indices.get("duration_index"), 0.0),
            _safe_float(quantitative_indices.get("risk_index"), 0.0),
            _safe_float(quantitative_indices.get("resource_density_index"), 0.0),
        )
    if baseline <= 0:
        baseline = 1.0
    lower = round(float(baseline) * (1.0 - relative), 6)
    upper = round(float(baseline) * (1.0 + relative), 6)
    return {
        "enabled": True,
        "confidence_level": round(confidence, 4),
        "relative_interval": round(relative, 4),
        "baseline": round(float(baseline), 6),
        "lower": lower,
        "upper": upper,
    }


def _apply_online_learning_weights(
    *,
    base_weights: Dict[str, float],
    profile: Dict[str, Any],
    region_context: str,
    professional_domains: List[str],
    query_dimensions: List[str],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    weights = dict(base_weights)
    if not isinstance(profile, dict) or not bool(profile.get("enabled")):
        return weights, {"applied": False, "segments": [], "weight_adjustments": {}}

    applied_segments: List[str] = []
    applied_weights: Dict[str, float] = {}

    direct = profile.get("weight_adjustments")
    if isinstance(direct, dict):
        for key, value in direct.items():
            k = str(key).strip()
            if not k or k not in weights:
                continue
            mul = max(0.2, min(3.0, _safe_float(value, 1.0)))
            weights[k] = round(max(0.2, min(3.0, weights[k] * mul)), 6)
            applied_weights[k] = round(mul, 6)
    if applied_weights:
        applied_segments.append("global")

    overrides = profile.get("segment_overrides")
    if isinstance(overrides, list):
        for item in overrides:
            if not isinstance(item, dict):
                continue
            seg_type = str(item.get("segment_type") or "").strip().lower()
            seg_key = str(item.get("segment_key") or "").strip()
            if not seg_type or not seg_key:
                continue
            min_hit_count = int(float(item.get("min_hit_count") or 0))
            hit_count = int(float(profile.get("hit_count") or 0))
            if min_hit_count > 0 and hit_count < min_hit_count and bool(profile.get("fallback_on_sparse_segments", True)):
                continue
            matched = False
            if seg_type == "region" and region_context:
                matched = seg_key.upper() == region_context.upper()
            elif seg_type == "domain":
                matched = seg_key.lower() in [str(x).lower() for x in professional_domains]
            elif seg_type == "dimension":
                matched = seg_key in query_dimensions
            if not matched:
                continue
            wadj = item.get("weight_adjustments")
            if not isinstance(wadj, dict):
                continue
            for key, value in wadj.items():
                k = str(key).strip()
                if not k or k not in weights:
                    continue
                mul = max(0.2, min(3.0, _safe_float(value, 1.0)))
                weights[k] = round(max(0.2, min(3.0, weights[k] * mul)), 6)
                applied_weights[k] = round(mul, 6)
            applied_segments.append(f"{seg_type}:{seg_key}")

    return weights, {
        "applied": bool(applied_segments),
        "segments": applied_segments,
        "weight_adjustments": applied_weights,
    }


def _estimate_gemini_usefulness(
    *,
    payload: Dict[str, Any],
    source_hierarchy: str,
    formula_expression: str,
    resource_requirements: Dict[str, Any],
    numeric_sources: List[Any],
    activation_signal: str,
    body: str,
    tags: List[str],
    keywords: List[str],
    evidence_completeness: Dict[str, Any] | None = None,
    formula_safety_profile: Dict[str, Any] | None = None,
) -> float:
    score = 35.0
    score += float(SOURCE_HIERARCHY_WEIGHTS.get(str(source_hierarchy or "未知"), 0) * 5.0)
    if resource_requirements:
        score += 15.0
    if numeric_sources:
        score += 12.0
    if formula_expression:
        score += 8.0
    if formula_expression and formula_expression != DEFAULT_FORMULA_EXPRESSION:
        score += 12.0
    if activation_signal:
        score += 8.0

    template_like = (
        ("第一步（定义）" in body and "第二步（分析）" in body and "第三步（解决）" in body)
        or ("工序名称->参数->风险->控制->验证" in body)
    )
    if template_like:
        score -= 12.0
    if formula_expression == DEFAULT_FORMULA_EXPRESSION:
        score -= 8.0
    if len(tags) + len(keywords) < 6:
        score -= 4.0

    evidence = evidence_completeness if isinstance(evidence_completeness, dict) else {}
    ratio = _safe_float(evidence.get("completeness_ratio"), -1.0)
    if ratio >= 0.9:
        score += 12.0
    elif ratio >= 0.75:
        score += 8.0
    elif ratio >= 0.55:
        score += 4.0
    elif 0.0 <= ratio < 0.35:
        score -= 10.0

    safety = formula_safety_profile if isinstance(formula_safety_profile, dict) else {}
    if bool(safety.get("enabled")):
        if bool(safety.get("safe")):
            score += 6.0
        else:
            score -= 10.0

    payload_score = _safe_float(payload.get("gemini_usefulness_score"), default=-1.0)
    if payload_score >= 0:
        score = max(score, payload_score)
    return round(max(0.0, min(100.0, score)), 4)


def _ensure_ascii_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return json.dumps({"error": "payload_not_serializable"}, ensure_ascii=False)


def _safe_json_load(s: Any, fallback: Any) -> Any:
    if not isinstance(s, str) or not s.strip():
        return fallback
    try:
        return json.loads(s)
    except Exception:
        return fallback


def _flatten_scalars(obj: Any, *, max_items: int = 180) -> List[str]:
    lines: List[str] = []

    def walk(node: Any, path: str) -> None:
        if len(lines) >= max_items:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if len(lines) >= max_items:
                    return
                next_path = f"{path}.{key}" if path else str(key)
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if len(lines) >= max_items:
                    return
                next_path = f"{path}[{idx}]" if path else f"[{idx}]"
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        else:
            text = str(node).strip()
            if text:
                lines.append(f"{path}: {text}" if path else text)

    walk(obj, "")
    return lines


def _extract_terms(raw: Any) -> List[str]:
    out: List[str] = []
    if isinstance(raw, str):
        out.extend(_tokenize(raw))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.extend(_tokenize(item))
            elif item is not None:
                out.extend(_tokenize(str(item)))
    elif isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, (str, list, dict)):
                out.extend(_extract_terms(value))
    elif raw is not None:
        out.extend(_tokenize(str(raw)))

    uniq: List[str] = []
    seen = set()
    for term in out:
        if term in seen:
            continue
        seen.add(term)
        uniq.append(term)
    return uniq[:60]


def _dedupe_terms(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        term = _normalize_term(value)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _safe_title(source_name: str, payload: Dict[str, Any], fallback: str) -> str:
    candidates = [
        payload.get("title"),
        payload.get("name"),
        payload.get("node_id"),
        payload.get("id"),
        payload.get("domain"),
        payload.get("category"),
        fallback,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return text[:120]
    return source_name


def _dict_get_case_insensitive(data: Dict[str, Any], candidates: Sequence[str]) -> Any:
    if not isinstance(data, dict):
        return None
    normalized = {_normalize_key(k): v for k, v in data.items()}
    for key in candidates:
        nk = _normalize_key(key)
        if nk in normalized:
            return normalized[nk]
    return None


def _split_targets(text: str) -> List[str]:
    parts = re.split(r"[;,，；、/|]+", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def _coerce_targets(raw: Any) -> List[str]:
    out: List[str] = []
    if raw is None:
        return out
    if isinstance(raw, str):
        out.extend(_split_targets(raw))
    elif isinstance(raw, list):
        for item in raw:
            out.extend(_coerce_targets(item))
    elif isinstance(raw, dict):
        target = _dict_get_case_insensitive(raw, ("target", "to", "node", "node_id", "id", "name", "object"))
        if target is not None:
            out.extend(_coerce_targets(target))
        else:
            for value in raw.values():
                out.extend(_coerce_targets(value))
    else:
        out.extend(_split_targets(str(raw)))
    uniq: List[str] = []
    seen = set()
    for item in out:
        norm = _normalize_alias(item)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        uniq.append(item)
    return uniq


def _extract_relation_targets(node: Dict[str, Any], edge_type: str) -> List[str]:
    keys = RELATION_KEYS.get(edge_type) or ()
    targets: List[str] = []
    for key in keys:
        val = _dict_get_case_insensitive(node, (key,))
        if val is not None:
            targets.extend(_coerce_targets(val))

    relations = _dict_get_case_insensitive(node, ("relations", "relationship", "edges"))
    if isinstance(relations, dict):
        for key in keys:
            val = _dict_get_case_insensitive(relations, (key,))
            if val is not None:
                targets.extend(_coerce_targets(val))
    elif isinstance(relations, list):
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            rtype = str(_dict_get_case_insensitive(rel, ("type", "edge_type", "relation")) or "").upper().strip()
            if rtype != edge_type:
                continue
            val = _dict_get_case_insensitive(rel, ("target", "to", "node", "node_id", "name", "object"))
            targets.extend(_coerce_targets(val))

    uniq: List[str] = []
    seen = set()
    for target in targets:
        norm = _normalize_alias(target)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        uniq.append(target)
    return uniq


def _infer_source_hierarchy_from_path(path_text: str) -> str:
    text = str(path_text or "")
    if any(k in text for k in ("答疑", "澄清", "补遗", "变更")):
        return "答疑文件"
    if any(k in text for k in ("图纸", "设计图", "施工图", "design")):
        return "设计图纸"
    if any(k in text for k in ("国标", "国家标准", "gb")):
        return "国标"
    if any(k in text for k in ("行标", "行业标准", "jgj", "tb")):
        return "行标"
    if any(k in text for k in ("企标", "企业标准", "q/", "q_")):
        return "企标"
    return "企标"


def _normalize_source_hierarchy(value: Any, *, source_path: str = "", inherited: str | None = None) -> str:
    if value is None or str(value).strip() == "":
        if inherited:
            return inherited
        return _infer_source_hierarchy_from_path(source_path)

    raw = str(value).strip().lower()
    if any(k in raw for k in ("答疑", "澄清", "补遗", "clarification", "qa")):
        return "答疑文件"
    if any(k in raw for k in ("设计图", "图纸", "drawing", "design")):
        return "设计图纸"
    if any(k in raw for k in ("国标", "国家", "gb")):
        return "国标"
    if any(k in raw for k in ("行标", "行业", "jgj", "tb")):
        return "行标"
    if any(k in raw for k in ("企标", "企业", "company", "enterprise")):
        return "企标"
    return "未知"


def _normalize_safety_level(value: Any, text: str = "") -> str:
    raw = str(value or "").strip().lower()
    merged = f"{raw} {text}".lower()
    if any(k in merged for k in ("critical", "极高", "特级")):
        return "critical"
    if any(k in merged for k in ("high", "高风险", "重大危险", "危大")):
        return "high"
    if any(k in merged for k in ("medium", "中风险", "较大风险")):
        return "medium"
    if any(k in merged for k in ("low", "低风险", "一般风险")):
        return "low"
    return "unknown"


def _extract_applicable_conditions(node: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(node, dict):
        return {}

    value = _dict_get_case_insensitive(
        node,
        (
            "applicable_conditions",
            "applicable_condition",
            "conditions",
            "condition",
            "适用条件",
            "环境条件",
        ),
    )
    if isinstance(value, dict):
        out = dict(value)
    elif value is not None:
        out = {"raw": value}
    else:
        out = {}

    climate = _dict_get_case_insensitive(node, ("climate", "气候", "temperature", "温度"))
    geology = _dict_get_case_insensitive(node, ("geology", "地质", "soil", "地层"))
    if climate is not None:
        out.setdefault("climate", climate)
    if geology is not None:
        out.setdefault("geology", geology)
    return out


def _extract_resource_requirements(node: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(node, dict):
        return {}
    value = _dict_get_case_insensitive(
        node,
        (
            "resource_requirements",
            "resource_requirement",
            "resources",
            "resource_model",
            "资源要求",
            "资源消耗模型",
        ),
    )
    if isinstance(value, dict):
        out = dict(value)
    elif isinstance(value, list):
        out = {"items": value}
    elif value is not None:
        out = {"raw": value}
    else:
        out = {}

    for key, alias in (("manpower", "人力"), ("material", "材料"), ("equipment", "机械")):
        v = _dict_get_case_insensitive(node, (key, alias))
        if v is not None:
            out.setdefault(key, v)
    return out


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _extract_numeric_sources(
    node: Dict[str, Any],
    *,
    body: str,
    formula_expression: str,
    resource_requirements: Dict[str, Any],
) -> List[Dict[str, Any]]:
    candidates = _dict_get_case_insensitive(
        node,
        (
            "numeric_sources",
            "numeric_source",
            "parameter_sources",
            "data_sources",
            "quantitative_evidence",
            "参数来源",
            "数值依据",
        ),
    )

    out: List[Dict[str, Any]] = []
    if isinstance(candidates, dict):
        candidates = [candidates]
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict):
                rec = {str(k): v for k, v in item.items() if str(k).strip() and v not in (None, "", [], {})}
                if rec:
                    out.append(rec)
            elif item not in (None, ""):
                out.append({"parameter": "raw", "value": str(item)})

    pattern = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|‰|dB|MPa|kPa|mm|cm|m|km|天|h|小时|min|分钟|次/日|次/班|次|人|台|套|m3|m²|m2|t|kg|ug/m3|μg/m3)",
        flags=re.IGNORECASE,
    )
    for m in pattern.finditer(body or ""):
        left = (body[max(0, m.start() - 16) : m.start()] or "").strip()
        parameter = re.sub(r"[\s:：，,。；;、\[\]（）(){}]+", "", left[-12:]) or "parameter"
        out.append(
            {
                "parameter": parameter,
                "value": m.group("value"),
                "unit": m.group("unit"),
                "source_text": (body[max(0, m.start() - 28) : min(len(body), m.end() + 18)] or "").strip(),
            }
        )
        if len(out) >= 12:
            break

    if formula_expression and not any(str(item.get("formula") or "").strip() for item in out if isinstance(item, dict)):
        out.append(
            {
                "parameter": "formula_result",
                "formula": formula_expression,
                "source_text": "formula_expression",
            }
        )

    if not out and isinstance(resource_requirements, dict):
        freq = _dict_get_case_insensitive(
            resource_requirements,
            ("inspection_frequency", "inspection_frequency_per_day", "巡检频次", "检查频次"),
        )
        if freq is not None:
            out.append(
                {
                    "parameter": "inspection_frequency",
                    "value": str(freq),
                    "unit": "次/日",
                    "source_text": "resource_requirements",
                }
            )

    if not out:
        out.append(
            {
                "parameter": "inspection_frequency",
                "value": "2",
                "unit": "次/班",
                "source_text": "default_quantitative_baseline",
            }
        )

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in out:
        if not isinstance(item, dict):
            continue
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:16]


def _extract_quantitative_indices(
    node: Dict[str, Any],
    *,
    safety_level: str,
    resource_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "quantitative_indices",
            "indices",
            "index_metrics",
            "量化指数",
            "量化指标",
        ),
    )
    out = _coerce_dict(raw)

    safety_score_map = {
        "critical": 0.92,
        "high": 0.78,
        "medium": 0.58,
        "low": 0.38,
        "unknown": 0.5,
    }
    risk_default = safety_score_map.get(str(safety_level or "unknown").lower(), 0.5)

    manpower = _dict_get_case_insensitive(resource_requirements, ("manpower", "人力"))
    crew_size = 0.0
    if isinstance(manpower, dict):
        raw_crew = _dict_get_case_insensitive(manpower, ("crew_size", "班组规模", "人数"))
        text = str(raw_crew or "")
        nums = re.findall(r"\d+(?:\.\d+)?", text)
        if nums:
            vals = [float(x) for x in nums]
            crew_size = sum(vals) / max(1, len(vals))

    resource_density_default = _clamp_01((crew_size / 12.0) if crew_size > 0 else 0.5)
    duration_default = _clamp_01(0.65 if risk_default >= 0.75 else 0.5)

    duration_index = float(_dict_get_case_insensitive(out, ("duration_index", "工期指数")) or duration_default)
    risk_index = float(_dict_get_case_insensitive(out, ("risk_index", "风险指数")) or risk_default)
    resource_density_index = float(
        _dict_get_case_insensitive(out, ("resource_density_index", "资源密度指数")) or resource_density_default
    )

    out["duration_index"] = round(_clamp_01(duration_index), 4)
    out["risk_index"] = round(_clamp_01(risk_index), 4)
    out["resource_density_index"] = round(_clamp_01(resource_density_index), 4)
    if "complexity_index" not in out:
        out["complexity_index"] = round(
            _clamp_01(out["duration_index"] * 0.35 + out["risk_index"] * 0.35 + out["resource_density_index"] * 0.30),
            4,
        )
    return out


def _extract_schedule_constraints(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "schedule_constraints",
            "schedule_constraint",
            "cpm_constraints",
            "schedule",
            "进度约束",
            "工序约束",
        ),
    )
    out = _coerce_dict(raw)

    min_interval = _dict_get_case_insensitive(
        out,
        ("min_process_interval_days", "minimum_interval_days", "min_lag_days", "最小工序间隔"),
    )
    if min_interval is None:
        min_interval = _dict_get_case_insensitive(
            node,
            ("min_process_interval_days", "minimum_interval_days", "最小工序间隔"),
        )
    try:
        min_interval_int = max(1, int(float(min_interval))) if min_interval is not None else 1
    except Exception:
        min_interval_int = 1

    critical_path = _dict_get_case_insensitive(
        out,
        ("critical_path_hint", "critical_path", "key_path", "关键线路"),
    )
    if critical_path is None:
        critical_path = _dict_get_case_insensitive(
            node,
            ("critical_path_hint", "critical_path", "key_path", "关键线路"),
        )
    if isinstance(critical_path, str):
        critical_path = [x.strip() for x in re.split(r"[;,，；、/|]+", critical_path) if x.strip()]
    if not isinstance(critical_path, list):
        critical_path = []

    out["min_process_interval_days"] = min_interval_int
    out["critical_path_hint"] = [str(x).strip() for x in critical_path if str(x).strip()][:12]
    return out


def _extract_standard_timeline(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "standard_validity_timeline",
            "standard_timeline",
            "reference_standard_timeline",
            "标准时效",
            "标准时效时间线",
        ),
    )
    out = _coerce_dict(raw)
    if "records" not in out or not isinstance(out.get("records"), list):
        out["records"] = []
    if "timeline_status" not in out:
        out["timeline_status"] = "unknown"
    return out


def _extract_regional_policy(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "regional_policy_layers",
            "regional_policy",
            "region_policy",
            "地域政策分层",
            "区域政策",
        ),
    )
    out = _coerce_dict(raw)
    if "layers" not in out or not isinstance(out.get("layers"), list):
        out["layers"] = []
    if "default_region" not in out:
        out["default_region"] = "CN"
    return out


def _extract_unit_dimension_model(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "unit_dimension_model",
            "unit_model",
            "量纲模型",
            "单位量纲",
        ),
    )
    out = _coerce_dict(raw)
    if "parameters" not in out or not isinstance(out.get("parameters"), list):
        out["parameters"] = []
    return out


def _extract_evidence_anchors(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "evidence_anchors",
            "evidence_anchor",
            "evidence_bindings",
            "证据锚点",
        ),
    )
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            rec = {str(k): v for k, v in item.items() if str(k).strip() and v not in (None, "", [], {})}
            if rec:
                out.append(rec)
    return out


def _extract_cross_constraints(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "cross_discipline_constraints",
            "cross_constraints",
            "跨专业约束",
            "跨专业约束求解",
        ),
    )
    out = _coerce_dict(raw)
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_retrieval_benchmark(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "retrieval_benchmark",
            "retrieval_metrics",
            "检索基准",
            "检索指标",
        ),
    )
    out = _coerce_dict(raw)
    if "quality_score" in out:
        out["quality_score"] = _safe_float(out.get("quality_score"), 0.0)
    return out


def _extract_approval_workflow(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "approval_workflow",
            "approval_flow",
            "审批流",
            "审核流程",
        ),
    )
    out = _coerce_dict(raw)
    if "required" not in out:
        out["required"] = False
    return out


def _extract_formula_sensitivity(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "formula_sensitivity",
            "sensitivity_analysis",
            "公式敏感性",
        ),
    )
    out = _coerce_dict(raw)
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_bim_ifc_context(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "bim_ifc_context",
            "ifc_context",
            "bim_context",
            "BIM_IFC",
        ),
    )
    out = _coerce_dict(raw)
    if "ifc_entities" not in out or not isinstance(out.get("ifc_entities"), list):
        out["ifc_entities"] = []
    return out


def _extract_incremental_state(node: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    fingerprint = str(
        _dict_get_case_insensitive(node, ("incremental_fingerprint", "fingerprint", "node_fingerprint")) or ""
    ).strip()
    update = _coerce_dict(
        _dict_get_case_insensitive(
            node,
            (
                "incremental_update",
                "incremental_state",
                "增量更新",
            ),
        )
    )
    if fingerprint and "fingerprint" not in update:
        update["fingerprint"] = fingerprint
    return fingerprint, update


def _extract_process_parameter_pack(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "process_parameter_pack",
            "parameter_pack",
            "process_parameters",
            "工序参数包",
        ),
    )
    out = _coerce_dict(raw)
    if "steps" not in out or not isinstance(out.get("steps"), list):
        out["steps"] = []
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_resource_productivity_model(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "resource_productivity_model",
            "productivity_model",
            "资源产能模型",
        ),
    )
    out = _coerce_dict(raw)
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_risk_trigger_matrix(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "risk_trigger_matrix",
            "risk_triggers",
            "risk_matrix",
            "风险触发矩阵",
        ),
    )
    out = _coerce_dict(raw)
    items = out.get("items")
    if not isinstance(items, list):
        out["items"] = []
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_clause_locator(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "clause_locator",
            "clause_trace",
            "clause_anchor",
            "条文定位",
            "条文溯源",
        ),
    )
    out = _coerce_dict(raw)
    anchors = out.get("anchors")
    normalized_anchors: List[Dict[str, Any]] = []
    if isinstance(anchors, list):
        for item in anchors:
            if not isinstance(item, dict):
                continue
            rec = {str(k): v for k, v in item.items() if str(k).strip() and v not in (None, "", [], {})}
            clause_ref = str(rec.get("clause_ref") or "").strip()
            standard_code = str(rec.get("standard_code") or "").strip()
            section_hint = str(rec.get("section_hint") or "").strip()
            paragraph_hint = str(rec.get("paragraph_hint") or "").strip()
            if not clause_ref and not standard_code:
                continue
            if clause_ref:
                rec["clause_ref"] = clause_ref
            if standard_code:
                rec["standard_code"] = standard_code
            if section_hint:
                rec["section_hint"] = section_hint
            if paragraph_hint:
                rec["paragraph_hint"] = paragraph_hint
            if not str(rec.get("clause_path") or "").strip():
                segs = [x for x in [standard_code, clause_ref] if x]
                if section_hint:
                    segs.append(f"S{section_hint}")
                if paragraph_hint:
                    segs.append(f"P{paragraph_hint}")
                rec["clause_path"] = "/".join(segs)[:160]
            if not str(rec.get("source_excerpt") or "").strip():
                source_excerpt = " ".join(x for x in [clause_ref, standard_code] if x).strip() or "条文定位锚点"
                rec["source_excerpt"] = source_excerpt[:140]
            if not str(rec.get("anchor_hash") or "").strip():
                hash_seed = "|".join(
                    [
                        clause_ref,
                        standard_code,
                        section_hint,
                        str(rec.get("page_hint") or ""),
                        paragraph_hint,
                        str(rec.get("evidence_anchor_id") or ""),
                    ]
                )
                rec["anchor_hash"] = hashlib.sha1(hash_seed.encode("utf-8", errors="ignore")).hexdigest()[:16]
            normalized_anchors.append(rec)
    out["anchors"] = normalized_anchors
    if "enabled" not in out:
        out["enabled"] = False
    if normalized_anchors and not str(out.get("pointer_mode") or "").strip():
        out["pointer_mode"] = "hash+excerpt"
    return out


def _extract_interface_contract(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "cross_discipline_interface_contract",
            "interface_contract",
            "cross_interface_contract",
            "跨专业接口合同",
        ),
    )
    out = _coerce_dict(raw)
    if "interfaces" not in out or not isinstance(out.get("interfaces"), list):
        out["interfaces"] = []
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_optimization_objectives_ext(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "optimization_objectives_ext",
            "optimization_objectives",
            "multi_objective",
            "多目标优化",
        ),
    )
    out = _coerce_dict(raw)
    if "objectives" not in out or not isinstance(out.get("objectives"), dict):
        out["objectives"] = {}
    if "enabled" not in out:
        out["enabled"] = False
    return out


def _extract_online_learning_profile(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "online_learning_profile",
            "learning_profile",
            "retrieval_learning_profile",
            "在线学习画像",
        ),
    )
    out = _coerce_dict(raw)
    if "enabled" not in out:
        out["enabled"] = False
    if bool(out.get("enabled")):
        out.setdefault("layered_strategy", "global+domain+region+dimension")
        out.setdefault("fallback_on_sparse_segments", True)
        if not isinstance(out.get("segment_overrides"), list):
            out["segment_overrides"] = []
        if not isinstance(out.get("weight_adjustments"), dict):
            out["weight_adjustments"] = {}
    return out


def _extract_long_tail_profile(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "long_tail_profile",
            "sparse_domain_profile",
            "long_tail_domain_profile",
            "长尾专业画像",
        ),
    )
    out = _coerce_dict(raw)
    long_tail_domains = out.get("long_tail_domains")
    if isinstance(long_tail_domains, str):
        long_tail_domains = [x.strip() for x in re.split(r"[;,，；、|]+", long_tail_domains) if x.strip()]
    if not isinstance(long_tail_domains, list):
        long_tail_domains = []
    fallback_domains = out.get("fallback_domains")
    if isinstance(fallback_domains, str):
        fallback_domains = [x.strip() for x in re.split(r"[;,，；、|]+", fallback_domains) if x.strip()]
    if not isinstance(fallback_domains, list):
        fallback_domains = []
    transfer_factor = _safe_float(out.get("transfer_factor"), 0.85)
    out["long_tail_domains"] = [str(x).strip().lower() for x in long_tail_domains if str(x).strip()][:12]
    out["fallback_domains"] = [str(x).strip().lower() for x in fallback_domains if str(x).strip()][:12]
    out["transfer_factor"] = round(max(0.5, min(1.2, transfer_factor)), 4)
    out["specialty_tag"] = str(out.get("specialty_tag") or "").strip().lower()
    if "enabled" not in out:
        out["enabled"] = bool(out["long_tail_domains"] or out["specialty_tag"])
    return out


def _extract_uncertainty_profile(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "uncertainty_profile",
            "uncertainty_model",
            "confidence_profile",
            "不确定性画像",
        ),
    )
    out = _coerce_dict(raw)
    confidence = _safe_float(out.get("confidence_level"), -1.0)
    if confidence < 0:
        confidence = _safe_float(out.get("confidence"), -1.0)
    interval = _safe_float(out.get("relative_interval"), -1.0)
    if interval < 0:
        interval = _safe_float(out.get("interval_ratio"), 0.0)
    out["confidence_level"] = round(max(0.0, min(1.0, confidence if confidence >= 0 else 0.0)), 4)
    out["relative_interval"] = round(max(0.0, min(0.6, interval)), 4)
    if "enabled" not in out:
        out["enabled"] = bool(out["confidence_level"] > 0.0 or out["relative_interval"] > 0.0)
    return out


def _extract_entity_alignment(
    node: Dict[str, Any],
    *,
    object_key: str,
    title: str,
    node_id: str,
) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "entity_alignment",
            "entity_master",
            "实体对齐",
        ),
    )
    out = _coerce_dict(raw)
    direct_master = _dict_get_case_insensitive(node, ("entity_master_key", "master_entity_key", "entity_key"))
    master_key = str(direct_master or out.get("entity_master_key") or "").strip()
    if not master_key:
        seed = _normalize_alias(object_key or title or node_id)
        if seed:
            master_key = f"EMK-{hashlib.sha1(seed.encode('utf-8', errors='ignore')).hexdigest()[:14]}"
    aliases = _coerce_targets(_dict_get_case_insensitive(node, ("aliases", "alias", "ref", "references")))
    aliases.extend([object_key, title, node_id])
    aliases_norm: List[str] = []
    seen = set()
    for item in aliases:
        val = str(item or "").strip()
        if not val:
            continue
        key = _normalize_alias(val)
        if not key or key in seen:
            continue
        seen.add(key)
        aliases_norm.append(val)
    out["enabled"] = True
    out["entity_master_key"] = master_key
    out.setdefault("entity_type", str(_dict_get_case_insensitive(node, ("entity_type", "node_type", "type")) or "engineering_object"))
    out["aliases"] = aliases_norm[:24]
    return out


def _extract_regional_standard_timeline(
    node: Dict[str, Any],
    *,
    standard_timeline: Dict[str, Any],
    regional_policy: Dict[str, Any],
) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "regional_standard_timeline",
            "region_standard_timeline",
            "地方标准时效",
        ),
    )
    out = _coerce_dict(raw)
    records = out.get("records")
    if not isinstance(records, list):
        records = []
    normalized: List[Dict[str, Any]] = []
    default_region = str(regional_policy.get("default_region") or "CN") if isinstance(regional_policy, dict) else "CN"
    layer_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(regional_policy, dict):
        for item in regional_policy.get("layers") or []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("policy_code") or "").strip()
            if code:
                layer_map[code] = item
    timeline_records = standard_timeline.get("records") if isinstance(standard_timeline, dict) else []
    if isinstance(timeline_records, list):
        for rec in timeline_records:
            if not isinstance(rec, dict):
                continue
            code = str(rec.get("standard_code") or "").strip()
            if not code:
                continue
            layer = layer_map.get(code) or {}
            region_code = str(layer.get("region_code") or layer.get("level") or default_region).strip() or default_region
            normalized.append(
                {
                    "region_code": region_code,
                    "policy_code": code,
                    "effective_date": str(rec.get("effective_date") or ""),
                    "expiry_date": str(rec.get("expiry_date") or ""),
                    "status": str(rec.get("status") or "active"),
                }
            )
    for rec in records:
        if not isinstance(rec, dict):
            continue
        code = str(rec.get("policy_code") or rec.get("standard_code") or "").strip()
        if not code:
            continue
        normalized.append(
            {
                "region_code": str(rec.get("region_code") or default_region).strip() or default_region,
                "policy_code": code,
                "effective_date": str(rec.get("effective_date") or ""),
                "expiry_date": str(rec.get("expiry_date") or ""),
                "status": str(rec.get("status") or "active"),
            }
        )
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for rec in normalized:
        key = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)
    out["records"] = deduped
    out["enabled"] = bool(deduped)
    out.setdefault("default_region", default_region)
    return out


def _extract_abnormal_scenario_playbook(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "abnormal_scenario_playbook",
            "scenario_playbook",
            "异常工况经验库",
        ),
    )
    out = _coerce_dict(raw)
    items = out.get("items")
    if not isinstance(items, list):
        items = []
    cleaned: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            rec = {str(k): v for k, v in item.items() if str(k).strip() and v not in (None, "", [], {})}
            if rec:
                cleaned.append(rec)
    out["items"] = cleaned
    out["enabled"] = bool(cleaned)
    return out


def _extract_deduction_counterexample_library(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = _dict_get_case_insensitive(
        node,
        (
            "deduction_counterexample_library",
            "counterexample_library",
            "扣分反例库",
        ),
    )
    out = _coerce_dict(raw)
    items = out.get("items")
    if not isinstance(items, list):
        items = []
    cleaned: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            rec = {str(k): v for k, v in item.items() if str(k).strip() and v not in (None, "", [], {})}
            if rec:
                cleaned.append(rec)
    out["items"] = cleaned
    out["enabled"] = bool(cleaned)
    return out


def _extract_formula_safety_profile(
    *,
    formula_expression: str,
    formula_variables: List[str],
    unit_dimension_model: Dict[str, Any],
) -> Dict[str, Any]:
    expr = str(formula_expression or "").strip()
    declared = [str(x).strip() for x in (formula_variables or []) if str(x).strip()]
    if not expr:
        return {"enabled": False, "reason": "no_formula"}

    parse_ok = True
    expr_vars: List[str] = []
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST_NODES):
                parse_ok = False
                break
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FORMULA_FUNCS:
                    parse_ok = False
                    break
        if parse_ok:
            expr_vars = sorted(
                {
                    n.id
                    for n in ast.walk(tree)
                    if isinstance(n, ast.Name) and n.id not in ALLOWED_FORMULA_FUNCS
                }
            )
    except Exception:
        parse_ok = False

    missing_declared = sorted([v for v in expr_vars if v not in declared])
    extra_declared = sorted([v for v in declared if v not in expr_vars])
    denominator_guard_ok = ("/" not in expr and "//" not in expr) or ("max(" in expr.lower())

    unit_params = set()
    params = unit_dimension_model.get("parameters") if isinstance(unit_dimension_model, dict) else []
    if isinstance(params, list):
        for item in params:
            if not isinstance(item, dict):
                continue
            p = str(item.get("parameter") or "").strip()
            if p:
                unit_params.add(p)
    missing_unit_bindings = sorted([v for v in expr_vars if v not in unit_params])

    executable_ok = False
    if parse_ok:
        vars_seed = {v: 1.0 for v in expr_vars}
        try:
            _safe_eval_formula(expr, vars_seed)
            executable_ok = True
        except Exception:
            executable_ok = False

    score = 100.0
    if not parse_ok:
        score -= 50.0
    if missing_declared:
        score -= min(25.0, 6.0 * len(missing_declared))
    if missing_unit_bindings:
        score -= min(15.0, 4.0 * len(missing_unit_bindings))
    if not denominator_guard_ok:
        score -= 12.0
    if not executable_ok:
        score -= 16.0
    score = max(0.0, min(100.0, score))

    safe = bool(
        parse_ok
        and executable_ok
        and not missing_declared
        and denominator_guard_ok
        and score >= 65.0
    )
    return {
        "enabled": True,
        "parse_ok": parse_ok,
        "executable_ok": executable_ok,
        "denominator_guard_ok": denominator_guard_ok,
        "expression_variables": expr_vars,
        "declared_variables": declared,
        "missing_declared_variables": missing_declared,
        "extra_declared_variables": extra_declared,
        "missing_unit_bindings": missing_unit_bindings,
        "safety_score": round(score, 4),
        "safe": safe,
    }


def _extract_evidence_completeness_profile(
    *,
    numeric_sources: List[Any],
    clause_locator: Dict[str, Any],
    source_hierarchy: str,
    standard_timeline: Dict[str, Any],
) -> Dict[str, Any]:
    required_fields = ["parameter", "value", "unit", "clause_anchor", "source_hierarchy", "effective_date"]
    anchors = clause_locator.get("anchors") if isinstance(clause_locator, dict) else []
    has_anchor = False
    if isinstance(anchors, list):
        for item in anchors:
            if not isinstance(item, dict):
                continue
            if str(item.get("anchor_hash") or "").strip() or str(item.get("clause_ref") or "").strip():
                has_anchor = True
                break
    records = standard_timeline.get("records") if isinstance(standard_timeline, dict) else []
    effective_dates = []
    if isinstance(records, list):
        for rec in records:
            if not isinstance(rec, dict):
                continue
            dt = str(rec.get("effective_date") or "").strip()
            if dt:
                effective_dates.append(dt)
    effective_date = effective_dates[0] if effective_dates else ""
    if not effective_date:
        for item in numeric_sources:
            if not isinstance(item, dict):
                continue
            dt = str(item.get("effective_date") or "").strip()
            if dt:
                effective_date = dt
                break
    items = [item for item in numeric_sources if isinstance(item, dict)]
    if not items:
        return {
            "enabled": False,
            "required_fields": required_fields,
            "total_parameters": 0,
            "complete_parameters": 0,
            "completeness_ratio": 0.0,
            "completeness_score": 0.0,
            "verifiable_parameters": 0,
            "verification_ratio": 0.0,
            "verification_status": "no_numeric_sources",
            "missing_field_totals": {field: 0 for field in required_fields},
            "status": "no_numeric_sources",
        }

    complete = 0
    verifiable = 0
    missing_totals = {field: 0 for field in required_fields}
    rows: List[Dict[str, Any]] = []
    for item in items:
        has_parameter = bool(str(item.get("parameter") or "").strip())
        formula_text = str(item.get("formula") or "").strip()
        has_formula = bool(formula_text)
        has_value = bool(str(item.get("value") or "").strip() or has_formula)
        has_unit = bool(str(item.get("unit") or "").strip()) or has_formula
        has_source = bool(str(source_hierarchy or "").strip())
        item_effective_date = str(item.get("effective_date") or "").strip()
        flags = {
            "parameter": has_parameter,
            "value": has_value,
            "unit": has_unit,
            "clause_anchor": has_anchor,
            "source_hierarchy": has_source,
            "effective_date": bool(item_effective_date or effective_date or has_formula),
        }
        origin = str(item.get("evidence_origin") or "").strip().lower()
        is_verifiable = bool(item.get("evidence_verified"))
        if not is_verifiable and origin not in {"synthetic_default", "derived_formula"}:
            is_verifiable = bool(
                str(item.get("anchor_hash") or "").strip()
                and str(item.get("clause_path") or "").strip()
                and (
                    str(item.get("source_page") or "").strip()
                    or str(item.get("clause_ref") or "").strip()
                )
            )
        missing_fields = [k for k, v in flags.items() if not bool(v)]
        for f in missing_fields:
            missing_totals[f] += 1
        is_complete = len(missing_fields) == 0
        if is_complete:
            complete += 1
        if is_verifiable:
            verifiable += 1
        rows.append(
            {
                "parameter": str(item.get("parameter") or ""),
                "complete": is_complete,
                "verifiable": is_verifiable,
                "evidence_origin": origin,
                "missing_fields": missing_fields,
            }
        )

    total = len(items)
    ratio = round(complete / max(total, 1), 4)
    score = round(ratio * 100.0, 4)
    verification_ratio = round(verifiable / max(total, 1), 4)
    verification_status = (
        "pass"
        if verification_ratio >= 0.6
        else "warn"
        if verification_ratio >= 0.2
        else "synthetic_only"
    )
    status = "pass" if ratio >= 0.8 else "warn" if ratio >= 0.5 else "fail"
    return {
        "enabled": True,
        "required_fields": required_fields,
        "total_parameters": total,
        "complete_parameters": complete,
        "completeness_ratio": ratio,
        "completeness_score": score,
        "verifiable_parameters": verifiable,
        "verification_ratio": verification_ratio,
        "verification_status": verification_status,
        "missing_field_totals": missing_totals,
        "source_hierarchy": source_hierarchy,
        "effective_date": effective_date,
        "has_clause_anchor": has_anchor,
        "status": status,
        "items": rows[:32],
    }


def _grade_evidence_strength(
    *,
    evidence_completeness: Dict[str, Any],
    source_hierarchy: str,
    numeric_sources: List[Any],
    clause_locator: Dict[str, Any],
) -> Dict[str, Any]:
    ratio = _safe_float((evidence_completeness or {}).get("completeness_ratio"), 0.0)
    verification_ratio = _safe_float((evidence_completeness or {}).get("verification_ratio"), 0.0)
    verification_status = str((evidence_completeness or {}).get("verification_status") or "").strip().lower()
    source_w = int(SOURCE_HIERARCHY_WEIGHTS.get(str(source_hierarchy or "未知"), 0))
    numeric_count = len(numeric_sources) if isinstance(numeric_sources, list) else 0
    has_anchor = bool((evidence_completeness or {}).get("has_clause_anchor"))
    if not has_anchor and isinstance(clause_locator, dict):
        anchors = clause_locator.get("anchors")
        if isinstance(anchors, list):
            for item in anchors:
                if not isinstance(item, dict):
                    continue
                if str(item.get("anchor_hash") or "").strip() or str(item.get("clause_ref") or "").strip():
                    has_anchor = True
                    break

    score = 0.0
    score += ratio * 0.45
    score += verification_ratio * 0.30
    score += min(1.0, numeric_count / 6.0) * 0.10
    score += min(1.0, source_w / 5.0) * 0.10
    score += 0.05 if has_anchor else 0.0
    if verification_status == "pass":
        score += 0.05
    elif verification_status in {"synthetic_only", "warn"}:
        score -= 0.05
    score = max(0.0, min(1.0, score))

    if score >= 0.85 and verification_ratio >= 0.75 and has_anchor:
        grade = "A"
    elif score >= 0.70 and ratio >= 0.55:
        grade = "B"
    elif score >= 0.50:
        grade = "C"
    else:
        grade = "D"
    return {
        "enabled": True,
        "grade": grade,
        "score": round(score, 6),
        "completeness_ratio": round(ratio, 6),
        "verification_ratio": round(verification_ratio, 6),
        "has_clause_anchor": bool(has_anchor),
        "source_hierarchy_weight": source_w,
        "numeric_source_count": int(numeric_count),
    }


def _extract_activation_terms(signal_text: str) -> List[str]:
    text = str(signal_text or "").strip()
    if not text:
        return []
    quoted = [str(x).strip() for x in re.findall(r"[\"']([^\"']+)[\"']", text) if str(x).strip()]
    if quoted:
        return quoted
    m = re.search(r"contains\s+(.+)$", text, flags=re.IGNORECASE)
    if m:
        tail = str(m.group(1) or "").strip()
        parts = [p.strip() for p in re.split(r"\s+and\s+|[;,，；、|]+", tail, flags=re.IGNORECASE) if p.strip()]
        return parts
    return [text]


def _resolve_activation_context(explicit_context: str | None, root_meta: Dict[str, Any]) -> str:
    if explicit_context is not None and str(explicit_context).strip():
        return str(explicit_context).strip()
    for env_key in DNA_CONTEXT_ENV_KEYS:
        env_val = os.getenv(env_key)
        if env_val and str(env_val).strip():
            return str(env_val).strip()
    activation_key = _dict_get_case_insensitive(root_meta, ("activation_key", "activationKey", "dna_key"))
    if activation_key is not None and str(activation_key).strip():
        return str(activation_key).strip()
    return ""


def _dna_verify_signal(signal_text: str, context_text: str) -> bool:
    signal = str(signal_text or "").strip()
    if not signal:
        return True
    terms = _extract_activation_terms(signal)
    if not terms:
        return False
    context = _normalize_term(context_text)
    if not context:
        return False
    return all(_normalize_term(term) in context for term in terms)


def _coerce_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    return {"raw": value}


def _extract_tactical_fields(
    node: Dict[str, Any],
    *,
    activation_context: str,
) -> Dict[str, Any]:
    content = _dict_get_case_insensitive(node, ("content",))
    if isinstance(content, dict):
        root = content
    else:
        root = node

    env_sensing = _dict_get_case_insensitive(root, ("environment_sensing",))
    activation_signal = ""
    if isinstance(env_sensing, dict):
        activation_signal = str(
            _dict_get_case_insensitive(env_sensing, ("activation_signal", "dna_signal", "signal")) or ""
        ).strip()
    else:
        activation_signal = str(_dict_get_case_insensitive(root, ("activation_signal", "dna_signal")) or "").strip()

    premium_raw = _dict_get_case_insensitive(root, ("operation_desc_premium", "premium"))
    premium = _coerce_dict(premium_raw)
    mediocre_desc = str(_dict_get_case_insensitive(root, ("operation_desc_mediocre", "mediocre")) or "").strip()

    strategy = _coerce_dict(_dict_get_case_insensitive(premium, ("bid_response_strategy", "response_strategy")))
    shield = _coerce_dict(_dict_get_case_insensitive(premium, ("competitor_shield", "rival_shield", "shield")))
    booster = _coerce_dict(_dict_get_case_insensitive(premium, ("qt_score_booster", "score_booster", "booster")))

    premium_desc = str(_dict_get_case_insensitive(premium, ("desc", "description", "operation")) or "").strip()
    has_tactical = bool(activation_signal or strategy or shield or booster or premium_desc or mediocre_desc)
    if not has_tactical:
        return {}

    dna_verified = _dna_verify_signal(activation_signal, activation_context)
    tactical_mode = "premium"
    selected_operation_desc = premium_desc or mediocre_desc
    if (not dna_verified) and mediocre_desc:
        tactical_mode = "mediocre"
        selected_operation_desc = mediocre_desc

    tags: List[str] = ["tactical_kg"]
    if _dict_get_case_insensitive(shield, ("trap_logic", "trap", "陷阱")):
        tags.append("trap_logic")
    if booster:
        tags.append("score_booster")

    keywords: List[str] = []
    keywords.extend(_extract_terms(strategy))
    keywords.extend(_extract_terms(shield))
    keywords.extend(_extract_terms(booster))
    keywords.extend(_extract_terms(selected_operation_desc))
    keywords.extend(_extract_terms(activation_signal))

    return {
        "activation_signal": activation_signal,
        "dna_verified": bool(dna_verified),
        "tactical_mode": tactical_mode,
        "selected_operation_desc": selected_operation_desc,
        "bid_response_strategy": strategy,
        "competitor_shield": shield,
        "qt_score_booster": booster,
        "tags": tags,
        "keywords": keywords,
    }


def _extract_formula_info(node: Dict[str, Any], body: str) -> Tuple[str, str, List[str]]:
    raw_type = str(_dict_get_case_insensitive(node, ("node_type", "type")) or "EngineeringNode").strip()
    expr = _dict_get_case_insensitive(node, ("formula_expression", "formula", "expression", "compute_formula"))
    if expr is None:
        content = _dict_get_case_insensitive(node, ("content",))
        if isinstance(content, dict):
            expr = _dict_get_case_insensitive(content, ("formula_expression", "formula", "expression", "compute_formula"))

    expression = str(expr or "").strip()
    node_type = "FormulaNode" if (raw_type.lower() == "formulanode" or bool(expression)) else "EngineeringNode"

    vars_raw = _dict_get_case_insensitive(node, ("formula_variables", "variables", "formula_vars"))
    variables: List[str] = []
    if isinstance(vars_raw, str):
        variables = [v.strip() for v in re.split(r"[;,，；、\s]+", vars_raw) if v.strip()]
    elif isinstance(vars_raw, list):
        variables = [str(v).strip() for v in vars_raw if str(v).strip()]

    if expression and not variables:
        guessed = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
        variables = [v for v in guessed if v not in ALLOWED_FORMULA_FUNCS]
    uniq_vars: List[str] = []
    seen = set()
    for item in variables:
        name = str(item).strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        uniq_vars.append(name)
    return node_type, expression, uniq_vars


def _build_object_key(node: Dict[str, Any], title: str, node_id: str) -> str:
    candidate = _dict_get_case_insensitive(node, ("object_key", "target_object", "object", "name", "title"))
    if candidate is None:
        candidate = title or node_id
    key = _normalize_alias(str(candidate))
    return key or _normalize_alias(str(title or node_id)) or _normalize_alias(node_id)


def _build_reference_keys(node: Dict[str, Any], *, uid: str, title: str, node_id: str, object_key: str) -> List[str]:
    refs: List[str] = [uid, title, node_id, object_key]
    refs.extend(_coerce_targets(_dict_get_case_insensitive(node, ("aliases", "alias", "ref", "references"))))
    if isinstance(node.get("name"), str):
        refs.append(str(node.get("name")))
    if isinstance(node.get("id"), str):
        refs.append(str(node.get("id")))

    out: List[str] = []
    seen = set()
    for ref in refs:
        norm = _normalize_alias(ref)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        out.append(ref)
    return out


def _build_parsed_node(
    *,
    path: Path,
    node_id: str,
    title: str,
    body: str,
    tags: List[str],
    keywords: List[str],
    payload: Dict[str, Any],
    node_type: str,
    object_key: str,
    applicable_conditions: Dict[str, Any],
    resource_requirements: Dict[str, Any],
    safety_level: str,
    source_hierarchy: str,
    formula_expression: str,
    formula_variables: List[str],
    reference_keys: List[str],
    edge_drafts: List[ParsedEdgeDraft],
    data_source_type: str = "FILE",
    spatial_context: Optional[Dict[str, Any]] = None,
    activation_signal: str = "",
    dna_verified: bool = True,
    tactical_mode: str = "",
    bid_response_strategy: Optional[Dict[str, Any]] = None,
    competitor_shield: Optional[Dict[str, Any]] = None,
    qt_score_booster: Optional[Dict[str, Any]] = None,
    quantitative_indices: Optional[Dict[str, Any]] = None,
    numeric_sources: Optional[List[Dict[str, Any]]] = None,
    schedule_constraints: Optional[Dict[str, Any]] = None,
    standard_validity_timeline: Optional[Dict[str, Any]] = None,
    regional_policy_layers: Optional[Dict[str, Any]] = None,
    unit_dimension_model: Optional[Dict[str, Any]] = None,
    evidence_anchors: Optional[List[Dict[str, Any]]] = None,
    cross_discipline_constraints: Optional[Dict[str, Any]] = None,
    retrieval_benchmark: Optional[Dict[str, Any]] = None,
    approval_workflow: Optional[Dict[str, Any]] = None,
    formula_sensitivity: Optional[Dict[str, Any]] = None,
    bim_ifc_context: Optional[Dict[str, Any]] = None,
    incremental_fingerprint: str = "",
    incremental_update: Optional[Dict[str, Any]] = None,
) -> ParsedNode:
    uid = hashlib.sha1(f"{path}::{node_id}".encode("utf-8")).hexdigest()[:20]
    return ParsedNode(
        uid=uid,
        title=title,
        body=body[:12000],
        tags=_dedupe_terms(tags)[:24],
        keywords=_dedupe_terms(keywords)[:32],
        payload_json=_ensure_ascii_json(payload),
        node_type=node_type,
        object_key=object_key,
        applicable_conditions_json=_ensure_ascii_json(applicable_conditions),
        resource_requirements_json=_ensure_ascii_json(resource_requirements),
        safety_level=safety_level,
        source_hierarchy=source_hierarchy,
        formula_expression=formula_expression,
        formula_variables_json=_ensure_ascii_json(formula_variables),
        data_source_type=str(data_source_type or "FILE"),
        spatial_context_json=_ensure_ascii_json(spatial_context or {}),
        activation_signal=str(activation_signal or ""),
        dna_verified=1 if bool(dna_verified) else 0,
        tactical_mode=str(tactical_mode or ""),
        bid_response_strategy_json=_ensure_ascii_json(bid_response_strategy or {}),
        competitor_shield_json=_ensure_ascii_json(competitor_shield or {}),
        qt_score_booster_json=_ensure_ascii_json(qt_score_booster or {}),
        quantitative_indices_json=_ensure_ascii_json(quantitative_indices or {}),
        numeric_sources_json=_ensure_ascii_json(numeric_sources or []),
        schedule_constraints_json=_ensure_ascii_json(schedule_constraints or {}),
        standard_validity_timeline_json=_ensure_ascii_json(standard_validity_timeline or {}),
        regional_policy_layers_json=_ensure_ascii_json(regional_policy_layers or {}),
        unit_dimension_model_json=_ensure_ascii_json(unit_dimension_model or {}),
        evidence_anchors_json=_ensure_ascii_json(evidence_anchors or []),
        cross_discipline_constraints_json=_ensure_ascii_json(cross_discipline_constraints or {}),
        retrieval_benchmark_json=_ensure_ascii_json(retrieval_benchmark or {}),
        approval_workflow_json=_ensure_ascii_json(approval_workflow or {}),
        formula_sensitivity_json=_ensure_ascii_json(formula_sensitivity or {}),
        bim_ifc_context_json=_ensure_ascii_json(bim_ifc_context or {}),
        incremental_fingerprint=str(incremental_fingerprint or ""),
        incremental_update_json=_ensure_ascii_json(incremental_update or {}),
        reference_keys=reference_keys,
        edge_drafts=edge_drafts,
    )


def _parse_markdown(path: Path) -> List[ParsedNode]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    nodes: List[ParsedNode] = []

    current_title = path.stem
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        body = "\n".join(current_lines).strip()
        if len(body) < 20:
            return
        title = current_title or path.stem
        node_id = f"{path.stem}:{title}"
        source_hierarchy = _normalize_source_hierarchy(None, source_path=str(path))
        safety_level = _normalize_safety_level(None, body)
        object_key = _normalize_alias(title)
        refs = [title, node_id, object_key]
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=_extract_terms([path.stem, "markdown"]),
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "markdown", "title": title},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level=safety_level,
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            reference_keys=refs,
            edge_drafts=[],
        )
        nodes.append(node)

    for line in lines:
        if line.lstrip().startswith("#"):
            flush()
            current_title = re.sub(r"^#+\s*", "", line).strip() or path.stem
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if not nodes and text.strip():
        current_title = path.stem
        current_lines = [text]
        flush()

    return nodes


def _parse_csv(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean = {k: v for k, v in row.items() if v not in (None, "")}
            if not clean:
                continue
            title = _safe_title(path.stem, clean, f"row_{idx}")
            node_id = str(clean.get("node_id") or clean.get("id") or f"{path.stem}:{idx}")
            body = "\n".join(f"{k}: {v}" for k, v in clean.items())
            source_hierarchy = _normalize_source_hierarchy(clean.get("source_hierarchy"), source_path=str(path))
            safety_level = _normalize_safety_level(clean.get("safety_level") or clean.get("risk_level"), body)
            object_key = _normalize_alias(str(clean.get("object_key") or title))
            refs = [title, node_id, object_key]

            node = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms([path.stem, "csv"]),
                keywords=_extract_terms(clean),
                payload={"type": "csv", "row": idx, "raw": clean},
                node_type="EngineeringNode",
                object_key=object_key,
                applicable_conditions={},
                resource_requirements={},
                safety_level=safety_level,
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=refs,
                edge_drafts=[],
            )
            nodes.append(node)

    return nodes


def _parse_xml(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    root = ET.parse(path).getroot()

    def walk(elem: ET.Element, x_path: str) -> None:
        text_parts: List[str] = []
        attrs: Dict[str, Any] = {}
        if elem.attrib:
            attrs.update(elem.attrib)
            for key, value in elem.attrib.items():
                if value is not None:
                    text_parts.append(f"@{key}: {value}")
        if elem.text and elem.text.strip():
            text_parts.append(elem.text.strip())
        for child in elem:
            if child.text and child.text.strip():
                text_parts.append(f"{child.tag}: {child.text.strip()}")

        body = "\n".join(text_parts).strip()
        if len(body) >= 20:
            title = str(elem.attrib.get("name") or elem.attrib.get("id") or elem.tag)
            node_id = str(elem.attrib.get("node_id") or elem.attrib.get("id") or x_path)
            source_hierarchy = _normalize_source_hierarchy(elem.attrib.get("source_hierarchy"), source_path=str(path))
            safety_level = _normalize_safety_level(elem.attrib.get("safety_level") or elem.attrib.get("risk_level"), body)
            object_key = _normalize_alias(str(elem.attrib.get("object_key") or title))
            refs = [title, node_id, object_key]

            node = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms([path.stem, elem.tag]),
                keywords=_tokenize(f"{title} {body}"),
                payload={"type": "xml", "path": x_path, "tag": elem.tag, "attrs": attrs},
                node_type="EngineeringNode",
                object_key=object_key,
                applicable_conditions={},
                resource_requirements={},
                safety_level=safety_level,
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=refs,
                edge_drafts=[],
            )
            nodes.append(node)

        for idx, child in enumerate(elem):
            walk(child, f"{x_path}/{child.tag}[{idx}]")

    walk(root, f"/{root.tag}")
    return nodes


def _parse_json(path: Path, *, activation_context: str | None = None) -> List[ParsedNode]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes: List[ParsedNode] = []
    root_meta = raw.get("meta") if isinstance(raw, dict) else {}
    activation_ctx = _resolve_activation_context(activation_context, root_meta if isinstance(root_meta, dict) else {})

    def walk(
        node: Any,
        pointer: str,
        inherited_tags: List[str],
        inherited_keywords: List[str],
        inherited_source: str,
    ) -> None:
        if isinstance(node, dict):
            local_tags = list(inherited_tags)
            local_keywords = list(inherited_keywords)

            for tag_key in ("domain", "category", "type", "scene", "qt_tag", "tags", "labels"):
                val = _dict_get_case_insensitive(node, (tag_key,))
                if val is not None:
                    local_tags.extend(_extract_terms(val))
            for kw_key in ("keywords", "keyword", "trigger_keywords", "name", "title"):
                val = _dict_get_case_insensitive(node, (kw_key,))
                if val is not None:
                    local_keywords.extend(_extract_terms(val))

            source_hierarchy = _normalize_source_hierarchy(
                _dict_get_case_insensitive(node, ("source_hierarchy", "source_level", "source")),
                source_path=str(path),
                inherited=inherited_source,
            )

            has_identity = any(
                _dict_get_case_insensitive(node, (k,)) is not None
                for k in ("node_id", "name", "title", "id")
            )
            if has_identity:
                title = _safe_title(path.stem, node, pointer)
                node_id = str(_dict_get_case_insensitive(node, ("node_id", "id")) or pointer)
                body_lines = _flatten_scalars(node, max_items=160)
                body = "\n".join(body_lines).strip()
                if len(body) >= 20:
                    node_type, formula_expression, formula_variables = _extract_formula_info(node, body)
                    applicable_conditions = _extract_applicable_conditions(node)
                    resource_requirements = _extract_resource_requirements(node)
                    safety_level = _normalize_safety_level(
                        _dict_get_case_insensitive(node, ("safety_level", "risk_level", "风险等级")),
                        body,
                    )
                    numeric_sources = _extract_numeric_sources(
                        node,
                        body=body,
                        formula_expression=formula_expression,
                        resource_requirements=resource_requirements,
                    )
                    quantitative_indices = _extract_quantitative_indices(
                        node,
                        safety_level=safety_level,
                        resource_requirements=resource_requirements,
                    )
                    schedule_constraints = _extract_schedule_constraints(node)
                    standard_timeline = _extract_standard_timeline(node)
                    regional_policy = _extract_regional_policy(node)
                    unit_dimension_model = _extract_unit_dimension_model(node)
                    evidence_anchors = _extract_evidence_anchors(node)
                    cross_constraints = _extract_cross_constraints(node)
                    retrieval_benchmark = _extract_retrieval_benchmark(node)
                    approval_workflow = _extract_approval_workflow(node)
                    formula_sensitivity = _extract_formula_sensitivity(node)
                    bim_ifc_context = _extract_bim_ifc_context(node)
                    process_parameter_pack = _extract_process_parameter_pack(node)
                    resource_productivity_model = _extract_resource_productivity_model(node)
                    risk_trigger_matrix = _extract_risk_trigger_matrix(node)
                    clause_locator = _extract_clause_locator(node)
                    interface_contract = _extract_interface_contract(node)
                    optimization_objectives_ext = _extract_optimization_objectives_ext(node)
                    online_learning_profile = _extract_online_learning_profile(node)
                    long_tail_profile = _extract_long_tail_profile(node)
                    incremental_fingerprint, incremental_update = _extract_incremental_state(node)
                    object_key = _build_object_key(node, title, node_id)
                    entity_alignment = _extract_entity_alignment(
                        node,
                        object_key=object_key,
                        title=title,
                        node_id=node_id,
                    )
                    regional_standard_timeline = _extract_regional_standard_timeline(
                        node,
                        standard_timeline=standard_timeline,
                        regional_policy=regional_policy,
                    )
                    abnormal_scenario_playbook = _extract_abnormal_scenario_playbook(node)
                    deduction_counterexample_library = _extract_deduction_counterexample_library(node)
                    formula_safety_profile = _extract_formula_safety_profile(
                        formula_expression=formula_expression,
                        formula_variables=formula_variables,
                        unit_dimension_model=unit_dimension_model,
                    )
                    evidence_completeness = _extract_evidence_completeness_profile(
                        numeric_sources=numeric_sources,
                        clause_locator=clause_locator,
                        source_hierarchy=source_hierarchy,
                        standard_timeline=standard_timeline,
                    )
                    uncertainty_profile = _extract_uncertainty_profile(node)
                    if not bool(uncertainty_profile.get("enabled")) and (
                        formula_expression or isinstance(evidence_completeness, dict)
                    ):
                        c_ratio = _safe_float(evidence_completeness.get("completeness_ratio"), 0.0)
                        v_ratio = _safe_float(evidence_completeness.get("verification_ratio"), 0.0)
                        safe_bonus = 0.08 if bool(formula_safety_profile.get("safe")) else -0.12
                        confidence = max(0.35, min(0.96, 0.42 + c_ratio * 0.30 + v_ratio * 0.20 + safe_bonus))
                        relative_interval = max(0.03, min(0.45, 1.0 - confidence))
                        uncertainty_profile = {
                            "enabled": True,
                            "method": "derived_from_evidence_v1",
                            "confidence_level": round(confidence, 4),
                            "relative_interval": round(relative_interval, 4),
                        }
                    refs = _build_reference_keys(
                        node,
                        uid="",
                        title=title,
                        node_id=node_id,
                        object_key=object_key,
                    )

                    primary_ref = str(_dict_get_case_insensitive(node, ("node_id", "id", "name", "title")) or title)
                    edge_drafts: List[ParsedEdgeDraft] = []
                    for edge_type in EDGE_TYPES:
                        targets = _extract_relation_targets(node, edge_type)
                        for target in targets:
                            edge_drafts.append(
                                ParsedEdgeDraft(
                                    from_ref=primary_ref,
                                    to_ref=target,
                                    edge_type=edge_type,
                                    edge_label="",
                                )
                            )

                    payload = {
                        "pointer": pointer,
                        "node_id": node_id,
                        "title": title,
                        "node_type": node_type,
                        "source_hierarchy": source_hierarchy,
                        "quantitative_indices": quantitative_indices,
                        "numeric_sources": numeric_sources,
                        "schedule_constraints": schedule_constraints,
                        "standard_validity_timeline": standard_timeline,
                        "regional_policy_layers": regional_policy,
                        "unit_dimension_model": unit_dimension_model,
                        "evidence_anchors": evidence_anchors,
                        "cross_discipline_constraints": cross_constraints,
                        "retrieval_benchmark": retrieval_benchmark,
                        "approval_workflow": approval_workflow,
                        "formula_sensitivity": formula_sensitivity,
                        "bim_ifc_context": bim_ifc_context,
                        "process_parameter_pack": process_parameter_pack,
                        "resource_productivity_model": resource_productivity_model,
                        "risk_trigger_matrix": risk_trigger_matrix,
                        "clause_locator": clause_locator,
                        "cross_discipline_interface_contract": interface_contract,
                        "optimization_objectives_ext": optimization_objectives_ext,
                        "online_learning_profile": online_learning_profile,
                        "long_tail_profile": long_tail_profile,
                        "entity_alignment": entity_alignment,
                        "entity_master_key": str(entity_alignment.get("entity_master_key") or ""),
                        "regional_standard_timeline": regional_standard_timeline,
                        "abnormal_scenario_playbook": abnormal_scenario_playbook,
                        "deduction_counterexample_library": deduction_counterexample_library,
                        "formula_safety_profile": formula_safety_profile,
                        "evidence_completeness": evidence_completeness,
                        "uncertainty_profile": uncertainty_profile,
                    }

                    tactical = _extract_tactical_fields(node, activation_context=activation_ctx)
                    tags = local_tags + _extract_terms(path.stem)
                    keywords = local_keywords + _tokenize(f"{title} {body}")
                    keywords.extend(_extract_terms(numeric_sources))
                    keywords.extend(_extract_terms(quantitative_indices))
                    keywords.extend(_extract_terms(schedule_constraints))
                    keywords.extend(_extract_terms(standard_timeline))
                    keywords.extend(_extract_terms(regional_policy))
                    keywords.extend(_extract_terms(unit_dimension_model))
                    keywords.extend(_extract_terms(evidence_anchors))
                    keywords.extend(_extract_terms(cross_constraints))
                    keywords.extend(_extract_terms(retrieval_benchmark))
                    keywords.extend(_extract_terms(approval_workflow))
                    keywords.extend(_extract_terms(formula_sensitivity))
                    keywords.extend(_extract_terms(bim_ifc_context))
                    keywords.extend(_extract_terms(process_parameter_pack))
                    keywords.extend(_extract_terms(resource_productivity_model))
                    keywords.extend(_extract_terms(risk_trigger_matrix))
                    keywords.extend(_extract_terms(clause_locator))
                    keywords.extend(_extract_terms(interface_contract))
                    keywords.extend(_extract_terms(optimization_objectives_ext))
                    keywords.extend(_extract_terms(online_learning_profile))
                    keywords.extend(_extract_terms(long_tail_profile))
                    keywords.extend(_extract_terms(entity_alignment))
                    keywords.extend(_extract_terms(regional_standard_timeline))
                    keywords.extend(_extract_terms(abnormal_scenario_playbook))
                    keywords.extend(_extract_terms(deduction_counterexample_library))
                    keywords.extend(_extract_terms(formula_safety_profile))
                    keywords.extend(_extract_terms(evidence_completeness))
                    keywords.extend(_extract_terms(uncertainty_profile))
                    activation_signal = ""
                    dna_verified = True
                    tactical_mode = ""
                    bid_response_strategy: Dict[str, Any] = {}
                    competitor_shield: Dict[str, Any] = {}
                    qt_score_booster: Dict[str, Any] = {}

                    if tactical:
                        activation_signal = str(tactical.get("activation_signal") or "")
                        dna_verified = bool(tactical.get("dna_verified"))
                        tactical_mode = str(tactical.get("tactical_mode") or "")
                        bid_response_strategy = _coerce_dict(tactical.get("bid_response_strategy"))
                        competitor_shield = _coerce_dict(tactical.get("competitor_shield"))
                        qt_score_booster = _coerce_dict(tactical.get("qt_score_booster"))
                        tags.extend([str(x) for x in (tactical.get("tags") or []) if str(x).strip()])
                        keywords.extend([str(x) for x in (tactical.get("keywords") or []) if str(x).strip()])
                        selected_operation_desc = str(tactical.get("selected_operation_desc") or "").strip()
                        response_template = str(
                            _dict_get_case_insensitive(bid_response_strategy, ("response_template", "template")) or ""
                        ).strip()
                        trap_logic = str(
                            _dict_get_case_insensitive(competitor_shield, ("trap_logic", "trap", "陷阱")) or ""
                        ).strip()
                        score_weight = str(
                            _dict_get_case_insensitive(qt_score_booster, ("score_weight", "weight", "加分权重")) or ""
                        ).strip()
                        tactical_lines: List[str] = [
                            f"DNA校验: {'PASS' if dna_verified else 'FAIL'}",
                            f"战术模式: {tactical_mode or 'default'}",
                        ]
                        if selected_operation_desc:
                            tactical_lines.append(f"执行说明: {selected_operation_desc}")
                        if response_template:
                            tactical_lines.append(f"响应策略: {response_template}")
                        if trap_logic:
                            tactical_lines.append(f"竞争护盾/陷阱: {trap_logic}")
                        if score_weight:
                            tactical_lines.append(f"加分权重: {score_weight}")
                        body = "\n".join(tactical_lines + [body]).strip()
                        payload["tactical"] = {
                            "activation_signal": activation_signal,
                            "dna_verified": dna_verified,
                            "tactical_mode": tactical_mode,
                            "bid_response_strategy": bid_response_strategy,
                            "competitor_shield": competitor_shield,
                            "qt_score_booster": qt_score_booster,
                        }

                    parsed = _build_parsed_node(
                        path=path,
                        node_id=node_id,
                        title=title,
                        body=body,
                        tags=tags,
                        keywords=keywords,
                        payload=payload,
                        node_type=node_type,
                        object_key=object_key,
                        applicable_conditions=applicable_conditions,
                        resource_requirements=resource_requirements,
                        safety_level=safety_level,
                        source_hierarchy=source_hierarchy,
                        formula_expression=formula_expression,
                        formula_variables=formula_variables,
                        reference_keys=refs,
                        edge_drafts=edge_drafts,
                        activation_signal=activation_signal,
                        dna_verified=dna_verified,
                        tactical_mode=tactical_mode,
                        bid_response_strategy=bid_response_strategy,
                        competitor_shield=competitor_shield,
                        qt_score_booster=qt_score_booster,
                        quantitative_indices=quantitative_indices,
                        numeric_sources=numeric_sources,
                        schedule_constraints=schedule_constraints,
                        standard_validity_timeline=standard_timeline,
                        regional_policy_layers=regional_policy,
                        unit_dimension_model=unit_dimension_model,
                        evidence_anchors=evidence_anchors,
                        cross_discipline_constraints=cross_constraints,
                        retrieval_benchmark=retrieval_benchmark,
                        approval_workflow=approval_workflow,
                        formula_sensitivity=formula_sensitivity,
                        bim_ifc_context=bim_ifc_context,
                        incremental_fingerprint=incremental_fingerprint,
                        incremental_update=incremental_update,
                    )
                    # inject uid reference after creation
                    parsed.reference_keys = _build_reference_keys(
                        node,
                        uid=parsed.uid,
                        title=title,
                        node_id=node_id,
                        object_key=object_key,
                    )
                    nodes.append(parsed)

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}.{key}", local_tags, local_keywords, source_hierarchy)

        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}[{idx}]", inherited_tags, inherited_keywords, inherited_source)

    walk(raw, "$", _extract_terms(path.stem), [], _infer_source_hierarchy_from_path(str(path)))

    if not nodes:
        body = "\n".join(_flatten_scalars(raw, max_items=200)).strip()
        if body:
            title = path.stem
            node_id = f"{path.stem}:root"
            source_hierarchy = _infer_source_hierarchy_from_path(str(path))
            parsed = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms(path.stem),
                keywords=_tokenize(body),
                payload={"pointer": "$", "node_id": node_id, "title": title},
                node_type="EngineeringNode",
                object_key=_normalize_alias(title),
                applicable_conditions={},
                resource_requirements={},
                safety_level=_normalize_safety_level(None, body),
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=[title, node_id],
                edge_drafts=[],
            )
            nodes.append(parsed)

    return nodes


def _parse_dxf(path: Path) -> List[ParsedNode]:
    payload = parse_dxf_payload(path)
    source_hierarchy = _normalize_source_hierarchy("设计图纸", source_path=str(path))
    nodes: List[ParsedNode] = []

    layer_ref_map: Dict[str, str] = {}
    layer_domain_map: Dict[str, str] = {}

    for layer in payload.get("layers") or []:
        layer_name = str(layer.get("layer_name") or "").strip() or "0"
        professional_domain = str(layer.get("professional_domain") or "general").strip() or "general"
        entity_count = int(layer.get("entity_count") or 0)
        node_id = f"{path.stem}:layer:{layer_name}"
        title = f"系统图层 {layer_name}"
        body = "\n".join(
            [
                f"图层名称: {layer_name}",
                f"专业属性: {professional_domain}",
                f"实体数量: {entity_count}",
            ]
        )
        object_key = _normalize_alias(layer_name) or _normalize_alias(node_id)
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "layer", professional_domain, layer_name],
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "dxf_layer", "raw": layer},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "layer": layer_name, "context_type": "layer"},
            reference_keys=[node_id, title, layer_name, object_key],
            edge_drafts=[],
        )
        nodes.append(node)
        layer_ref_map[layer_name] = node_id
        layer_domain_map[layer_name] = professional_domain

    text_title_map = {
        "design_general_notes": "设计总说明",
        "technical_requirement": "技术要求",
        "title_block_info": "图框信息",
        "leader_annotation": "引线标注文本",
        "drawing_text": "图纸文本",
    }

    for idx, item in enumerate(payload.get("texts") or [], start=1):
        text = str(item.get("text") or "").strip()
        if len(text) < 2:
            continue
        layer_name = str(item.get("layer") or "0")
        category = str(item.get("category") or "drawing_text")
        professional_domain = str(item.get("professional_domain") or layer_domain_map.get(layer_name) or "general")
        node_id = f"{path.stem}:text:{idx}"
        title = text_title_map.get(category, "图纸文本")
        object_key = _normalize_alias(f"{layer_name}-{category}-{idx}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="text_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=text,
            tags=["dxf", "text", category, layer_name, professional_domain],
            keywords=_tokenize(f"{title} {text} {layer_name}"),
            payload={"type": "dxf_text", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level=_normalize_safety_level(None, text),
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "entity_type": item.get("entity_type"),
                "position": item.get("position") or {},
                "handle": item.get("handle") or "",
                "context_type": category,
            },
            reference_keys=[node_id, title, layer_name, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    title_block = payload.get("title_block") or {}
    project_name = str(title_block.get("project_name") or "").strip()
    drawing_scale = str(title_block.get("drawing_scale") or "").strip()
    if project_name or drawing_scale:
        body_lines = ["图框信息提取"]
        if project_name:
            body_lines.append(f"项目名称: {project_name}")
        if drawing_scale:
            body_lines.append(f"出图比例: {drawing_scale}")
        node_id = f"{path.stem}:title_block"
        title = "图框信息"
        object_key = _normalize_alias(f"{path.stem}-title-block")
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body="\n".join(body_lines),
            tags=["dxf", "title_block"],
            keywords=_tokenize(" ".join(body_lines)),
            payload={"type": "dxf_title_block", "raw": title_block},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "context_type": "title_block"},
            reference_keys=[node_id, title, object_key],
            edge_drafts=[],
        )
        nodes.append(node)

    for idx, item in enumerate(payload.get("blocks") or [], start=1):
        block_name = str(item.get("block_name") or "").strip()
        if not block_name:
            continue
        layer_name = str(item.get("layer") or "0")
        professional_domain = str(item.get("professional_domain") or layer_domain_map.get(layer_name) or "general")
        count = int(item.get("count") or 0)
        node_id = f"{path.stem}:block:{idx}:{block_name}"
        title = f"块符号 {block_name}"
        body = "\n".join(
            [
                f"块名称: {block_name}",
                f"所在图层: {layer_name}",
                f"数量: {count}",
                f"缩放: ({item.get('scale_x', 1.0)}, {item.get('scale_y', 1.0)}, {item.get('scale_z', 1.0)})",
                f"旋转: {item.get('rotation', 0.0)}",
            ]
        )
        object_key = _normalize_alias(f"{block_name}-{layer_name}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="block_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "block", professional_domain, layer_name],
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "dxf_block", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={"symbol_count": count},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "context_type": "block",
                "sample_inserts": item.get("sample_inserts") or [],
            },
            reference_keys=[node_id, title, block_name, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    for idx, item in enumerate(payload.get("dimensions") or [], start=1):
        layer_name = str(item.get("layer") or "0")
        measurement = item.get("measurement")
        text = str(item.get("text") or "").strip()
        detail = text or (f"{measurement}" if measurement is not None else "")
        if not detail:
            continue
        node_id = f"{path.stem}:dimension:{idx}"
        title = "尺寸标注"
        body_lines = [f"所在图层: {layer_name}"]
        if measurement is not None:
            body_lines.append(f"量测值: {measurement}")
        if text:
            body_lines.append(f"标注文本: {text}")
        object_key = _normalize_alias(f"{layer_name}-dimension-{idx}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="dimension_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body="\n".join(body_lines),
            tags=["dxf", "dimension", layer_name],
            keywords=_tokenize(f"{title} {' '.join(body_lines)}"),
            payload={"type": "dxf_dimension", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "context_type": "dimension",
                "defpoint": item.get("defpoint") or {},
                "defpoint2": item.get("defpoint2") or {},
                "defpoint3": item.get("defpoint3") or {},
            },
            reference_keys=[node_id, title, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    geometry_features = payload.get("geometry_features") or []
    if geometry_features:
        counter: Dict[str, int] = {}
        for feature in geometry_features:
            ftype = str(feature.get("entity_type") or "UNKNOWN")
            counter[ftype] = int(counter.get(ftype, 0)) + 1
        summary = ", ".join(f"{key}:{value}" for key, value in sorted(counter.items()))
        node_id = f"{path.stem}:geometry_summary"
        title = "几何特征摘要"
        body = f"几何实体统计: {summary}"
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "geometry"],
            keywords=_tokenize(f"{title} {summary}"),
            payload={"type": "dxf_geometry_summary", "raw": geometry_features[:80]},
            node_type="EngineeringNode",
            object_key=_normalize_alias(f"{path.stem}-geometry-summary"),
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "context_type": "geometry_summary"},
            reference_keys=[node_id, title],
            edge_drafts=[],
        )
        nodes.append(node)

    return nodes


def _parse_ifc(path: Path) -> List[ParsedNode]:
    payload = parse_ifc_payload(path)
    source_hierarchy = _normalize_source_hierarchy("设计图纸", source_path=str(path))
    nodes: List[ParsedNode] = []

    model_id = f"{path.stem}:ifc:model"
    project_name = str(payload.get("project_name") or "").strip() or path.stem
    top_entities = payload.get("top_entities") if isinstance(payload.get("top_entities"), list) else []
    body_lines = [
        f"IFC模型: {path.name}",
        f"项目名称: {project_name}",
        f"实体类型数量: {len(payload.get('entity_counts') or {})}",
        "Top实体: " + ", ".join([f"{str(x.get('entity'))}:{int(x.get('count') or 0)}" for x in top_entities[:12]]),
    ]
    model_node = _build_parsed_node(
        path=path,
        node_id=model_id,
        title="IFC模型摘要",
        body="\n".join(body_lines),
        tags=["ifc", "bim", "model_summary"],
        keywords=_tokenize(" ".join(body_lines)),
        payload={"type": "ifc_model_summary", "raw": payload},
        node_type="EngineeringNode",
        object_key=_normalize_alias(f"{path.stem}-ifc-model"),
        applicable_conditions={},
        resource_requirements={},
        safety_level="unknown",
        source_hierarchy=source_hierarchy,
        formula_expression="",
        formula_variables=[],
        data_source_type="IFC",
        spatial_context={"model_file": path.name, "context_type": "ifc_model"},
        reference_keys=[model_id, project_name, path.name],
        edge_drafts=[],
    )
    nodes.append(model_node)

    for idx, item in enumerate(top_entities[:40], start=1):
        entity = str(item.get("entity") or "").strip()
        if not entity:
            continue
        count = int(item.get("count") or 0)
        node_id = f"{path.stem}:ifc:entity:{idx}:{entity}"
        edge_drafts = [
            ParsedEdgeDraft(from_ref=node_id, to_ref=model_id, edge_type=EDGE_BELONGS_TO, edge_label="ifc_entity_model")
        ]
        nodes.append(
            _build_parsed_node(
                path=path,
                node_id=node_id,
                title=f"IFC实体 {entity}",
                body=f"实体类型: {entity}\n数量: {count}",
                tags=["ifc", "entity", entity],
                keywords=_tokenize(f"{entity} {count}"),
                payload={"type": "ifc_entity_count", "entity": entity, "count": count},
                node_type="EngineeringNode",
                object_key=_normalize_alias(f"{entity}-{path.stem}"),
                applicable_conditions={},
                resource_requirements={"entity_count": count},
                safety_level="unknown",
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                data_source_type="IFC",
                spatial_context={"model_file": path.name, "ifc_entity": entity, "context_type": "ifc_entity"},
                reference_keys=[node_id, entity],
                edge_drafts=edge_drafts,
            )
        )

    properties = payload.get("properties") if isinstance(payload.get("properties"), list) else []
    for idx, item in enumerate(properties[:80], start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = str(item.get("value") or "").strip()
        if not name:
            continue
        node_id = f"{path.stem}:ifc:property:{idx}"
        edge_drafts = [
            ParsedEdgeDraft(
                from_ref=node_id,
                to_ref=model_id,
                edge_type=EDGE_BELONGS_TO,
                edge_label="ifc_property_model",
            )
        ]
        nodes.append(
            _build_parsed_node(
                path=path,
                node_id=node_id,
                title=f"IFC属性 {name}",
                body=f"属性名称: {name}\n属性值: {value}",
                tags=["ifc", "property", name],
                keywords=_tokenize(f"{name} {value}"),
                payload={"type": "ifc_property", "name": name, "value": value},
                node_type="EngineeringNode",
                object_key=_normalize_alias(f"{name}-{idx}-{path.stem}"),
                applicable_conditions={},
                resource_requirements={},
                safety_level="unknown",
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                data_source_type="IFC",
                spatial_context={"model_file": path.name, "context_type": "ifc_property"},
                reference_keys=[node_id, name],
                edge_drafts=edge_drafts,
            )
        )

    domain_distribution = payload.get("domain_distribution") if isinstance(payload.get("domain_distribution"), list) else []
    for idx, item in enumerate(domain_distribution[:16], start=1):
        if not isinstance(item, dict):
            continue
        domain = str(item.get("professional_domain") or "").strip()
        count = int(item.get("count") or 0)
        if not domain:
            continue
        node_id = f"{path.stem}:ifc:domain:{idx}:{domain}"
        edge_drafts = [
            ParsedEdgeDraft(
                from_ref=node_id,
                to_ref=model_id,
                edge_type=EDGE_BELONGS_TO,
                edge_label="ifc_domain_model",
            )
        ]
        nodes.append(
            _build_parsed_node(
                path=path,
                node_id=node_id,
                title=f"IFC专业语义 {domain}",
                body=f"专业域: {domain}\n实体命中数: {count}",
                tags=["ifc", "semantic", domain],
                keywords=_tokenize(f"ifc {domain} {count}"),
                payload={"type": "ifc_domain_distribution", "professional_domain": domain, "count": count},
                node_type="EngineeringNode",
                object_key=_normalize_alias(f"{path.stem}-ifc-domain-{domain}"),
                applicable_conditions={},
                resource_requirements={"entity_hit_count": count},
                safety_level="unknown",
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                data_source_type="IFC",
                spatial_context={"model_file": path.name, "context_type": "ifc_domain", "professional_domain": domain},
                reference_keys=[node_id, domain],
                edge_drafts=edge_drafts,
            )
        )
    return nodes


def _parse_rvt(path: Path) -> List[ParsedNode]:
    payload = parse_revit_payload(path)
    source_hierarchy = _normalize_source_hierarchy("设计图纸", source_path=str(path))
    nodes: List[ParsedNode] = []

    model_id = f"{path.stem}:rvt:model"
    body_lines = [
        f"Revit模型: {path.name}",
        f"原生解析支持: {bool(payload.get('native_supported'))}",
        f"解析模式: {payload.get('parse_mode')}",
        f"文件大小(bytes): {int(payload.get('size_bytes') or 0)}",
        f"SHA256: {payload.get('sha256')}",
    ]
    if payload.get("revit_version_hint"):
        body_lines.append(f"版本提示: {payload.get('revit_version_hint')}")

    nodes.append(
        _build_parsed_node(
            path=path,
            node_id=model_id,
            title="Revit模型摘要",
            body="\n".join(body_lines),
            tags=["revit", "bim", "model_summary"],
            keywords=_tokenize(" ".join(body_lines)),
            payload={"type": "revit_model_summary", "raw": payload},
            node_type="EngineeringNode",
            object_key=_normalize_alias(f"{path.stem}-rvt-model"),
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="RVT",
            spatial_context={"model_file": path.name, "context_type": "revit_model"},
            reference_keys=[model_id, path.name],
            edge_drafts=[],
        )
    )

    companions = payload.get("companion_exports") if isinstance(payload.get("companion_exports"), list) else []
    for idx, item in enumerate(companions[:40], start=1):
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file") or "").strip()
        if not file_name:
            continue
        snippet = str(item.get("snippet") or "").strip()
        node_id = f"{path.stem}:rvt:companion:{idx}"
        edge_drafts = [
            ParsedEdgeDraft(
                from_ref=node_id,
                to_ref=model_id,
                edge_type=EDGE_BELONGS_TO,
                edge_label="revit_companion_binding",
            )
        ]
        nodes.append(
            _build_parsed_node(
                path=path,
                node_id=node_id,
                title=f"Revit伴随数据 {file_name}",
                body=f"伴随文件: {file_name}\n摘要: {snippet}",
                tags=["revit", "companion", str(item.get("suffix") or "")],
                keywords=_tokenize(f"{file_name} {snippet}"),
                payload={"type": "revit_companion_export", "raw": item},
                node_type="EngineeringNode",
                object_key=_normalize_alias(f"{path.stem}-{file_name}-{idx}"),
                applicable_conditions={},
                resource_requirements={},
                safety_level="unknown",
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                data_source_type="RVT",
                spatial_context={"model_file": path.name, "context_type": "revit_companion"},
                reference_keys=[node_id, file_name],
                edge_drafts=edge_drafts,
            )
        )

    domain_distribution = payload.get("domain_distribution") if isinstance(payload.get("domain_distribution"), list) else []
    for idx, item in enumerate(domain_distribution[:16], start=1):
        if not isinstance(item, dict):
            continue
        domain = str(item.get("professional_domain") or "").strip()
        count = int(item.get("count") or 0)
        if not domain:
            continue
        node_id = f"{path.stem}:rvt:domain:{idx}:{domain}"
        edge_drafts = [
            ParsedEdgeDraft(
                from_ref=node_id,
                to_ref=model_id,
                edge_type=EDGE_BELONGS_TO,
                edge_label="revit_domain_model",
            )
        ]
        nodes.append(
            _build_parsed_node(
                path=path,
                node_id=node_id,
                title=f"Revit专业语义 {domain}",
                body=f"专业域: {domain}\n语义命中: {count}",
                tags=["revit", "semantic", domain],
                keywords=_tokenize(f"revit {domain} {count}"),
                payload={"type": "revit_domain_distribution", "professional_domain": domain, "count": count},
                node_type="EngineeringNode",
                object_key=_normalize_alias(f"{path.stem}-rvt-domain-{domain}"),
                applicable_conditions={},
                resource_requirements={"semantic_hit_count": count},
                safety_level="unknown",
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                data_source_type="RVT",
                spatial_context={"model_file": path.name, "context_type": "revit_domain", "professional_domain": domain},
                reference_keys=[node_id, domain],
                edge_drafts=edge_drafts,
            )
        )

    return nodes


def _safe_eval_formula(expression: str, variables: Dict[str, Any]) -> Any:
    text = str(expression or "").strip()
    if not text:
        raise ValueError("empty formula expression")
    tree = ast.parse(text, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            if node.func.id not in ALLOWED_FORMULA_FUNCS:
                raise ValueError(f"function not allowed: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in ALLOWED_FORMULA_FUNCS:
                raise ValueError(f"unknown variable: {node.id}")
    env = {**ALLOWED_FORMULA_FUNCS, **variables}
    return eval(compile(tree, "<FormulaNode>", "eval"), {"__builtins__": {}}, env)


class KnowledgeGraphIndex:
    """SQLite-backed unified knowledge graph index with structure/relations/formula/arbitration support."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH, *, activation_context: str | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_needs_reindex = False
        self.activation_context = activation_context
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column_def: str) -> None:
        col_name = column_def.split()[0].strip()
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(c[1]) for c in cols}
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    imported_at INTEGER NOT NULL,
                    node_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    node_uid TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    node_type TEXT NOT NULL DEFAULT 'EngineeringNode',
                    object_key TEXT NOT NULL DEFAULT '',
                    applicable_conditions_json TEXT NOT NULL DEFAULT '{}',
                    resource_requirements_json TEXT NOT NULL DEFAULT '{}',
                    safety_level TEXT NOT NULL DEFAULT 'unknown',
                    source_hierarchy TEXT NOT NULL DEFAULT '企标',
                    formula_expression TEXT NOT NULL DEFAULT '',
                    formula_variables_json TEXT NOT NULL DEFAULT '[]',
                    data_source_type TEXT NOT NULL DEFAULT 'FILE',
                    spatial_context_json TEXT NOT NULL DEFAULT '{}',
                    activation_signal TEXT NOT NULL DEFAULT '',
                    dna_verified INTEGER NOT NULL DEFAULT 1,
                    tactical_mode TEXT NOT NULL DEFAULT '',
                    bid_response_strategy_json TEXT NOT NULL DEFAULT '{}',
                    competitor_shield_json TEXT NOT NULL DEFAULT '{}',
                    qt_score_booster_json TEXT NOT NULL DEFAULT '{}',
                    quantitative_indices_json TEXT NOT NULL DEFAULT '{}',
                    numeric_sources_json TEXT NOT NULL DEFAULT '[]',
                    schedule_constraints_json TEXT NOT NULL DEFAULT '{}',
                    standard_validity_timeline_json TEXT NOT NULL DEFAULT '{}',
                    regional_policy_layers_json TEXT NOT NULL DEFAULT '{}',
                    unit_dimension_model_json TEXT NOT NULL DEFAULT '{}',
                    evidence_anchors_json TEXT NOT NULL DEFAULT '[]',
                    cross_discipline_constraints_json TEXT NOT NULL DEFAULT '{}',
                    retrieval_benchmark_json TEXT NOT NULL DEFAULT '{}',
                    approval_workflow_json TEXT NOT NULL DEFAULT '{}',
                    formula_sensitivity_json TEXT NOT NULL DEFAULT '{}',
                    bim_ifc_context_json TEXT NOT NULL DEFAULT '{}',
                    incremental_fingerprint TEXT NOT NULL DEFAULT '',
                    incremental_update_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, node_uid)
                );

                CREATE TABLE IF NOT EXISTS node_tags (
                    node_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(node_id, tag),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS node_keywords (
                    node_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    UNIQUE(node_id, keyword),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS node_aliases (
                    node_id INTEGER NOT NULL,
                    alias TEXT NOT NULL,
                    UNIQUE(node_id, alias),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node_id INTEGER NOT NULL,
                    to_node_id INTEGER NOT NULL,
                    edge_type TEXT NOT NULL,
                    edge_label TEXT NOT NULL DEFAULT '',
                    source_path TEXT NOT NULL DEFAULT '',
                    UNIQUE(from_node_id, to_node_id, edge_type),
                    FOREIGN KEY(from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY(to_node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_document_id ON nodes(document_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_object_key ON nodes(object_key);
                CREATE INDEX IF NOT EXISTS idx_nodes_source_hierarchy ON nodes(source_hierarchy);
                CREATE INDEX IF NOT EXISTS idx_nodes_data_source_type ON nodes(data_source_type);
                CREATE INDEX IF NOT EXISTS idx_node_tags_tag ON node_tags(tag);
                CREATE INDEX IF NOT EXISTS idx_node_keywords_keyword ON node_keywords(keyword);
                CREATE INDEX IF NOT EXISTS idx_node_aliases_alias ON node_aliases(alias);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type);
                """
            )

            # Migration for older databases.
            self._ensure_column(conn, "nodes", "node_type TEXT NOT NULL DEFAULT 'EngineeringNode'")
            self._ensure_column(conn, "nodes", "object_key TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "applicable_conditions_json TEXT NOT NULL DEFAULT '{}' ")
            self._ensure_column(conn, "nodes", "resource_requirements_json TEXT NOT NULL DEFAULT '{}' ")
            self._ensure_column(conn, "nodes", "safety_level TEXT NOT NULL DEFAULT 'unknown'")
            self._ensure_column(conn, "nodes", "source_hierarchy TEXT NOT NULL DEFAULT '企标'")
            self._ensure_column(conn, "nodes", "formula_expression TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "formula_variables_json TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "nodes", "data_source_type TEXT NOT NULL DEFAULT 'FILE'")
            self._ensure_column(conn, "nodes", "spatial_context_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "activation_signal TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "dna_verified INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "nodes", "tactical_mode TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "bid_response_strategy_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "competitor_shield_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "qt_score_booster_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "quantitative_indices_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "numeric_sources_json TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "nodes", "schedule_constraints_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "standard_validity_timeline_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "regional_policy_layers_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "unit_dimension_model_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "evidence_anchors_json TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "nodes", "cross_discipline_constraints_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "retrieval_benchmark_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "approval_workflow_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "formula_sensitivity_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "bim_ifc_context_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "nodes", "incremental_fingerprint TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "incremental_update_json TEXT NOT NULL DEFAULT '{}'")

            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        node_uid,
                        title,
                        body,
                        tags,
                        keywords
                    );
                    """
                )
            except sqlite3.OperationalError as exc:
                raise RuntimeError(
                    "sqlite build does not support FTS5; cannot provide millisecond indexed retrieval"
                ) from exc

            # Schema version tracking for reindex safety.
            vrow = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
            version = str(vrow[0]) if vrow else "0"
            if version != "6":
                self._schema_needs_reindex = True
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', '6')"
                )
            conn.commit()

    def _clear_document_rows(self, conn: sqlite3.Connection, document_id: int) -> None:
        rows = conn.execute("SELECT id FROM nodes WHERE document_id = ?", (document_id,)).fetchall()
        node_ids = [int(r[0]) for r in rows]
        if node_ids:
            marks = ",".join("?" for _ in node_ids)
            conn.execute(f"DELETE FROM graph_edges WHERE from_node_id IN ({marks}) OR to_node_id IN ({marks})", node_ids + node_ids)
            conn.execute(f"DELETE FROM node_aliases WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM node_tags WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM node_keywords WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM nodes_fts WHERE rowid IN ({marks})", node_ids)
        conn.execute("DELETE FROM nodes WHERE document_id = ?", (document_id,))

    def _parse_file(self, path: Path) -> List[ParsedNode]:
        ext = path.suffix.lower()
        if ext == ".json":
            return _parse_json(path, activation_context=self.activation_context)
        if ext in {".md", ".markdown"}:
            return _parse_markdown(path)
        if ext == ".xml":
            return _parse_xml(path)
        if ext == ".csv":
            return _parse_csv(path)
        if ext == ".dxf":
            return _parse_dxf(path)
        if ext in {".ifc", ".ifcxml"}:
            return _parse_ifc(path)
        if ext == ".rvt":
            return _parse_rvt(path)
        return []

    def _resolve_node_id(self, conn: sqlite3.Connection, ref: str, local_alias_map: Dict[str, int]) -> Optional[int]:
        alias = _normalize_alias(ref)
        if len(alias) < 2:
            return None
        if alias in local_alias_map:
            return int(local_alias_map[alias])

        row = conn.execute(
            "SELECT node_id FROM node_aliases WHERE alias = ? ORDER BY node_id DESC LIMIT 1",
            (alias,),
        ).fetchone()
        if row:
            return int(row[0])

        row = conn.execute(
            "SELECT id FROM nodes WHERE object_key = ? ORDER BY id DESC LIMIT 1",
            (alias,),
        ).fetchone()
        if row:
            return int(row[0])
        return None

    def ingest_directory(
        self,
        root_dir: Path | str = DEFAULT_KG_ROOT,
        *,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        root = Path(root_dir)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"knowledge graph root not found: {root}")

        if self._schema_needs_reindex and not force_reindex:
            force_reindex = True

        start = time.perf_counter()
        parsed_files = 0
        skipped_files = 0
        total_nodes = 0
        total_edges = 0

        files = [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        with self._connect() as conn:
            for path in files:
                data = path.read_bytes()
                sha = _sha256_bytes(data)
                rec = conn.execute(
                    "SELECT id, sha256 FROM documents WHERE source_path = ?",
                    (str(path),),
                ).fetchone()
                if rec and (str(rec["sha256"]) == sha) and not force_reindex:
                    skipped_files += 1
                    continue

                if rec:
                    doc_id = int(rec["id"])
                    self._clear_document_rows(conn, doc_id)
                else:
                    conn.execute(
                        """
                        INSERT INTO documents(source_path, file_name, ext, sha256, imported_at, node_count)
                        VALUES(?, ?, ?, ?, ?, 0)
                        """,
                        (str(path), path.name, path.suffix.lower(), sha, int(time.time())),
                    )
                    doc_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

                nodes = self._parse_file(path)
                inserted = 0
                edge_count = 0
                local_alias_map: Dict[str, int] = {}
                all_edge_drafts: List[ParsedEdgeDraft] = []

                for node in nodes:
                    cursor = conn.execute(
                        """
                        INSERT OR REPLACE INTO nodes(
                            document_id,
                            node_uid,
                            title,
                            body,
                            payload_json,
                            node_type,
                            object_key,
                            applicable_conditions_json,
                            resource_requirements_json,
                            safety_level,
                            source_hierarchy,
                            formula_expression,
                            formula_variables_json,
                            data_source_type,
                            spatial_context_json,
                            activation_signal,
                            dna_verified,
                            tactical_mode,
                            bid_response_strategy_json,
                            competitor_shield_json,
                            qt_score_booster_json,
                            quantitative_indices_json,
                            numeric_sources_json,
                            schedule_constraints_json,
                            standard_validity_timeline_json,
                            regional_policy_layers_json,
                            unit_dimension_model_json,
                            evidence_anchors_json,
                            cross_discipline_constraints_json,
                            retrieval_benchmark_json,
                            approval_workflow_json,
                            formula_sensitivity_json,
                            bim_ifc_context_json,
                            incremental_fingerprint,
                            incremental_update_json
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            node.uid,
                            node.title,
                            node.body,
                            node.payload_json,
                            node.node_type,
                            node.object_key,
                            node.applicable_conditions_json,
                            node.resource_requirements_json,
                            node.safety_level,
                            node.source_hierarchy,
                            node.formula_expression,
                            node.formula_variables_json,
                            node.data_source_type,
                            node.spatial_context_json,
                            node.activation_signal,
                            node.dna_verified,
                            node.tactical_mode,
                            node.bid_response_strategy_json,
                            node.competitor_shield_json,
                            node.qt_score_booster_json,
                            node.quantitative_indices_json,
                            node.numeric_sources_json,
                            node.schedule_constraints_json,
                            node.standard_validity_timeline_json,
                            node.regional_policy_layers_json,
                            node.unit_dimension_model_json,
                            node.evidence_anchors_json,
                            node.cross_discipline_constraints_json,
                            node.retrieval_benchmark_json,
                            node.approval_workflow_json,
                            node.formula_sensitivity_json,
                            node.bim_ifc_context_json,
                            node.incremental_fingerprint,
                            node.incremental_update_json,
                        ),
                    )
                    node_id = int(cursor.lastrowid)
                    if node_id <= 0:
                        row = conn.execute(
                            "SELECT id FROM nodes WHERE document_id = ? AND node_uid = ?",
                            (doc_id, node.uid),
                        ).fetchone()
                        if not row:
                            continue
                        node_id = int(row["id"])

                    tags = _dedupe_terms(node.tags)
                    keywords = _dedupe_terms(node.keywords)
                    for tag in tags:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_tags(node_id, tag) VALUES(?, ?)",
                            (node_id, tag),
                        )
                    for keyword in keywords:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_keywords(node_id, keyword) VALUES(?, ?)",
                            (node_id, keyword),
                        )
                    conn.execute(
                        "INSERT OR REPLACE INTO nodes_fts(rowid, node_uid, title, body, tags, keywords) VALUES(?, ?, ?, ?, ?, ?)",
                        (node_id, node.uid, node.title, node.body, " ".join(tags), " ".join(keywords)),
                    )

                    aliases = node.reference_keys + [node.uid, node.title, node.object_key]
                    for alias in aliases:
                        normalized = _normalize_alias(alias)
                        if len(normalized) < 2:
                            continue
                        conn.execute(
                            "INSERT OR IGNORE INTO node_aliases(node_id, alias) VALUES(?, ?)",
                            (node_id, normalized),
                        )
                        local_alias_map[normalized] = node_id

                    all_edge_drafts.extend(node.edge_drafts)
                    inserted += 1

                for edge in all_edge_drafts:
                    if edge.edge_type not in EDGE_TYPES:
                        continue
                    from_id = self._resolve_node_id(conn, edge.from_ref, local_alias_map)
                    to_id = self._resolve_node_id(conn, edge.to_ref, local_alias_map)
                    if not from_id or not to_id:
                        continue
                    if from_id == to_id:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO graph_edges(from_node_id, to_node_id, edge_type, edge_label, source_path)
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (from_id, to_id, edge.edge_type, edge.edge_label or "", str(path)),
                    )
                    edge_count += 1

                conn.execute(
                    """
                    UPDATE documents
                    SET sha256 = ?, imported_at = ?, node_count = ?
                    WHERE id = ?
                    """,
                    (sha, int(time.time()), inserted, doc_id),
                )

                parsed_files += 1
                total_nodes += inserted
                total_edges += edge_count

            conn.commit()

        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "root": str(root),
            "db_path": str(self.db_path),
            "files_total": len(files),
            "files_parsed": parsed_files,
            "files_skipped": skipped_files,
            "nodes_indexed": total_nodes,
            "edges_indexed": total_edges,
            "duration_ms": duration_ms,
        }

    def _candidate_ids_by_terms(
        self,
        conn: sqlite3.Connection,
        *,
        tags: List[str],
        keywords: List[str],
    ) -> Optional[set[int]]:
        candidate: Optional[set[int]] = None

        if tags:
            marks = ",".join("?" for _ in tags)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_tags WHERE tag IN ({marks})",
                tuple(tags),
            ).fetchall()
            tag_ids = {int(r[0]) for r in rows}
            candidate = tag_ids if candidate is None else candidate.intersection(tag_ids)

        if keywords:
            marks = ",".join("?" for _ in keywords)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_keywords WHERE keyword IN ({marks})",
                tuple(keywords),
            ).fetchall()
            kw_ids = {int(r[0]) for r in rows}
            candidate = kw_ids if candidate is None else candidate.intersection(kw_ids)

        return candidate

    def _fts_rank_map(
        self,
        conn: sqlite3.Connection,
        query: str,
        *,
        limit: int,
    ) -> Dict[int, float]:
        tokens = _tokenize(query)
        if not tokens:
            return {}
        fts_query = " OR ".join(tokens[:16])
        rows = conn.execute(
            """
            SELECT rowid, bm25(nodes_fts) AS rank
            FROM nodes_fts
            WHERE nodes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, int(limit)),
        ).fetchall()
        return {int(r[0]): float(r[1]) for r in rows}

    def _apply_authority_resolution(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in rows:
            entity_key = _normalize_alias(
                str(
                    item.get("entity_master_key")
                    or ((item.get("entity_alignment") or {}).get("entity_master_key") if isinstance(item.get("entity_alignment"), dict) else "")
                    or ""
                )
            )
            key = entity_key or _normalize_alias(str(item.get("object_key") or "")) or _normalize_alias(str(item.get("title") or ""))
            if not key:
                key = str(item.get("node_id"))
            weight = int(SOURCE_HIERARCHY_WEIGHTS.get(str(item.get("source_hierarchy") or "未知"), 0))
            current = grouped.get(key)
            if current is None:
                grouped[key] = {**item, "_source_weight": weight}
                continue
            cur_weight = int(current.get("_source_weight") or 0)
            cur_score = float(current.get("score") or 0.0)
            new_score = float(item.get("score") or 0.0)
            if (weight > cur_weight) or (weight == cur_weight and new_score > cur_score):
                grouped[key] = {**item, "_source_weight": weight}

        selected: List[Dict[str, Any]] = []
        for item in grouped.values():
            item.pop("_source_weight", None)
            item["authority_resolution"] = {
                "applied": True,
                "rule": SOURCE_HIERARCHY_RULE,
                "selected_source_hierarchy": item.get("source_hierarchy"),
            }
            selected.append(item)
        return selected

    def search(
        self,
        *,
        query: str = "",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 12,
        node_types: Optional[List[str]] = None,
        professional_domains: Optional[List[str]] = None,
        min_gemini_usefulness_score: float = 0.0,
        min_retrieval_quality_score: float = 0.0,
        region_context: str | None = None,
        bid_date: str | None = None,
        allow_superseded: bool = False,
        regional_plugin_dir: Path | str | None = None,
        retrieval_weight_profile_path: Path | str | None = None,
        require_approved_auto: bool = False,
        resolve_authority: bool = True,
    ) -> Dict[str, Any]:
        top_k = max(1, min(int(top_k or 12), 200))
        norm_tags = _dedupe_terms(tags or [])
        norm_keywords = _dedupe_terms(keywords or [])
        norm_node_types = [str(x).strip() for x in (node_types or []) if str(x).strip()]
        norm_domains = []
        for item in professional_domains or []:
            term = _normalize_domain(item)
            if term and term not in norm_domains:
                norm_domains.append(term)
        min_gemini_score = max(0.0, min(100.0, _safe_float(min_gemini_usefulness_score, 0.0)))
        min_retrieval_quality = max(0.0, min(100.0, _safe_float(min_retrieval_quality_score, 0.0)))
        norm_region = str(region_context or "").strip().upper()
        bid_date_text = str(bid_date or "").strip()
        bid_date_key = _safe_date_key(bid_date_text)
        score_weights = _load_retrieval_score_weights(retrieval_weight_profile_path)
        if regional_plugin_dir is None:
            region_plugin = resolve_regional_policy_plugin(norm_region)
        else:
            region_plugin = resolve_regional_policy_plugin(norm_region, plugin_dir=regional_plugin_dir)

        with self._connect() as conn:
            candidates = self._candidate_ids_by_terms(conn, tags=norm_tags, keywords=norm_keywords)
            rank_map = self._fts_rank_map(conn, query, limit=max(180, top_k * 8)) if query.strip() else {}

            if candidates is not None and rank_map:
                target_ids = candidates.intersection(set(rank_map.keys()))
                if not target_ids and candidates:
                    target_ids = candidates
            elif candidates is not None:
                target_ids = candidates
            elif rank_map:
                target_ids = set(rank_map.keys())
            else:
                target_ids = set()

            where_clauses: List[str] = []
            params: List[Any] = []
            if target_ids:
                marks = ",".join("?" for _ in target_ids)
                where_clauses.append(f"n.id IN ({marks})")
                params.extend(sorted(target_ids))
            if norm_node_types:
                marks = ",".join("?" for _ in norm_node_types)
                where_clauses.append(f"n.node_type IN ({marks})")
                params.extend(norm_node_types)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            rows = conn.execute(
                f"""
                SELECT
                    n.id,
                    n.node_uid,
                    n.title,
                    n.body,
                    n.payload_json,
                    n.node_type,
                    n.object_key,
                    n.applicable_conditions_json,
                    n.resource_requirements_json,
                    n.safety_level,
                    n.source_hierarchy,
                    n.formula_expression,
                    n.formula_variables_json,
                    n.data_source_type,
                    n.spatial_context_json,
                    n.activation_signal,
                    n.dna_verified,
                    n.tactical_mode,
                    n.bid_response_strategy_json,
                    n.competitor_shield_json,
                    n.qt_score_booster_json,
                    n.quantitative_indices_json,
                    n.numeric_sources_json,
                    n.schedule_constraints_json,
                    n.standard_validity_timeline_json,
                    n.regional_policy_layers_json,
                    n.unit_dimension_model_json,
                    n.evidence_anchors_json,
                    n.cross_discipline_constraints_json,
                    n.retrieval_benchmark_json,
                    n.approval_workflow_json,
                    n.formula_sensitivity_json,
                    n.bim_ifc_context_json,
                    n.incremental_fingerprint,
                    n.incremental_update_json,
                    d.file_name,
                    d.source_path,
                    COALESCE(GROUP_CONCAT(DISTINCT t.tag), '') AS tags_csv,
                    COALESCE(GROUP_CONCAT(DISTINCT k.keyword), '') AS keywords_csv
                FROM nodes n
                JOIN documents d ON d.id = n.document_id
                LEFT JOIN node_tags t ON t.node_id = n.id
                LEFT JOIN node_keywords k ON k.node_id = n.id
                {where_sql}
                GROUP BY n.id
                ORDER BY n.id DESC
                LIMIT ?
                """,
                tuple(params + [max(top_k * 18, 240)]),
            ).fetchall()

        query_tokens = _tokenize(query)
        query_dimensions = _detect_query_dimensions(query, norm_tags, norm_keywords)
        results: List[Dict[str, Any]] = []
        for row in rows:
            body = str(row["body"] or "")
            title = str(row["title"] or "")
            tags_row = [t for t in str(row["tags_csv"] or "").split(",") if t]
            keywords_row = [k for k in str(row["keywords_csv"] or "").split(",") if k]
            payload = _safe_json_load(row["payload_json"], {})
            numeric_sources = _safe_json_load(row["numeric_sources_json"], [])
            resource_requirements = _safe_json_load(row["resource_requirements_json"], {})
            formula_expression = str(row["formula_expression"] or "").strip()
            activation_signal = str(row["activation_signal"] or "").strip()
            standard_validity_timeline = _safe_json_load(row["standard_validity_timeline_json"], {})
            regional_policy_layers = _safe_json_load(row["regional_policy_layers_json"], {})
            unit_dimension_model = _safe_json_load(row["unit_dimension_model_json"], {})
            evidence_anchors = _safe_json_load(row["evidence_anchors_json"], [])
            cross_discipline_constraints = _safe_json_load(row["cross_discipline_constraints_json"], {})
            retrieval_benchmark = _safe_json_load(row["retrieval_benchmark_json"], {})
            approval_workflow = _safe_json_load(row["approval_workflow_json"], {})
            formula_sensitivity = _safe_json_load(row["formula_sensitivity_json"], {})
            bim_ifc_context = _safe_json_load(row["bim_ifc_context_json"], {})
            process_parameter_pack = _coerce_dict(payload.get("process_parameter_pack"))
            resource_productivity_model = _coerce_dict(payload.get("resource_productivity_model"))
            risk_trigger_matrix = _coerce_dict(payload.get("risk_trigger_matrix"))
            clause_locator = _coerce_dict(payload.get("clause_locator"))
            interface_contract = _coerce_dict(payload.get("cross_discipline_interface_contract"))
            optimization_objectives_ext = _coerce_dict(payload.get("optimization_objectives_ext"))
            online_learning_profile = _coerce_dict(payload.get("online_learning_profile"))
            long_tail_profile = _coerce_dict(payload.get("long_tail_profile"))
            uncertainty_profile = _coerce_dict(payload.get("uncertainty_profile"))
            entity_alignment = _coerce_dict(payload.get("entity_alignment"))
            entity_master_key = str(
                payload.get("entity_master_key")
                or entity_alignment.get("entity_master_key")
                or row["object_key"]
                or ""
            ).strip()
            regional_standard_timeline = _coerce_dict(payload.get("regional_standard_timeline"))
            abnormal_scenario_playbook = _coerce_dict(payload.get("abnormal_scenario_playbook"))
            deduction_counterexample_library = _coerce_dict(payload.get("deduction_counterexample_library"))
            formula_safety_profile = _coerce_dict(payload.get("formula_safety_profile"))
            evidence_completeness = _coerce_dict(payload.get("evidence_completeness"))
            evidence_strength = _grade_evidence_strength(
                evidence_completeness=evidence_completeness,
                source_hierarchy=str(row["source_hierarchy"] or ""),
                numeric_sources=numeric_sources if isinstance(numeric_sources, list) else [],
                clause_locator=clause_locator,
            )
            incremental_fingerprint = str(row["incremental_fingerprint"] or "").strip()
            incremental_update = _safe_json_load(row["incremental_update_json"], {})
            uncertainty_interval = _build_uncertainty_interval(
                uncertainty_profile=uncertainty_profile,
                formula_sensitivity=formula_sensitivity if isinstance(formula_sensitivity, dict) else {},
                quantitative_indices=_safe_json_load(row["quantitative_indices_json"], {}),
            )
            effective_weights, learning_apply = _apply_online_learning_weights(
                base_weights=score_weights,
                profile=online_learning_profile,
                region_context=norm_region,
                professional_domains=norm_domains,
                query_dimensions=query_dimensions,
            )

            score = 0.0
            title_norm = _normalize_term(title)
            body_norm = _normalize_term(body)
            tag_hit_count = sum(1 for tag in norm_tags if tag in tags_row)
            keyword_exact_hit_count = sum(1 for keyword in norm_keywords if keyword in keywords_row)
            keyword_fuzzy_hit_count = sum(
                1
                for keyword in norm_keywords
                if keyword not in keywords_row and (keyword in title_norm or keyword in body_norm)
            )
            merged = f"{title}\n{body}".lower()
            query_token_hit_count = sum(1 for token in query_tokens if token in merged) if query_tokens else 0

            tag_contrib = float(tag_hit_count) * 10.0 * float(effective_weights.get("tag_weight") or 1.0)
            keyword_exact_contrib = (
                float(keyword_exact_hit_count) * 8.0 * float(effective_weights.get("keyword_exact_weight") or 1.0)
            )
            keyword_fuzzy_contrib = (
                float(keyword_fuzzy_hit_count) * 5.0 * float(effective_weights.get("keyword_fuzzy_weight") or 1.0)
            )
            query_token_contrib = (
                float(query_token_hit_count) * 1.5 * float(effective_weights.get("query_token_weight") or 1.0)
            )

            score += tag_contrib
            score += keyword_exact_contrib
            score += keyword_fuzzy_contrib
            score += query_token_contrib

            row_id = int(row["id"])
            fts_contrib = 0.0
            if row_id in rank_map:
                fts_contrib = max(0.0, 20.0 - min(20.0, abs(rank_map[row_id]) * 4.0)) * float(
                    effective_weights.get("fts_rank_weight") or 1.0
                )
                score += fts_contrib

            domain_score, domain_matches = _domain_match(
                professional_domains=norm_domains,
                title=title,
                body=body,
                tags=tags_row,
                keywords=keywords_row,
                source_file=str(row["file_name"] or ""),
            )
            long_tail_match = _match_long_tail_profile(
                profile=long_tail_profile,
                professional_domains=norm_domains,
                title=title,
                body=body,
                tags=tags_row,
                keywords=keywords_row,
            )
            if norm_domains and not domain_matches and not bool(long_tail_match.get("matched")):
                continue
            domain_contrib = 0.0
            if domain_matches:
                domain_contrib = domain_score * float(effective_weights.get("domain_weight") or 1.0)
                score += domain_contrib
            elif bool(long_tail_match.get("matched")):
                domain_contrib = float(long_tail_match.get("score") or 0.0) * float(
                    effective_weights.get("domain_weight") or 1.0
                )
                score += domain_contrib

            gemini_usefulness_score = _estimate_gemini_usefulness(
                payload=payload,
                source_hierarchy=str(row["source_hierarchy"] or ""),
                formula_expression=formula_expression,
                resource_requirements=resource_requirements if isinstance(resource_requirements, dict) else {},
                numeric_sources=numeric_sources if isinstance(numeric_sources, list) else [],
                activation_signal=activation_signal,
                body=body,
                tags=tags_row,
                keywords=keywords_row,
                evidence_completeness=evidence_completeness,
                formula_safety_profile=formula_safety_profile,
            )
            if gemini_usefulness_score < min_gemini_score:
                continue
            gemini_contrib = min(8.0, gemini_usefulness_score * 0.08) * float(
                effective_weights.get("gemini_weight_scale") or 1.0
            )
            score += gemini_contrib

            retrieval_quality_score = _safe_float(
                retrieval_benchmark.get("quality_score") if isinstance(retrieval_benchmark, dict) else 0.0,
                0.0,
            )
            if retrieval_quality_score < min_retrieval_quality:
                continue
            retrieval_quality_contrib = min(6.0, retrieval_quality_score * 0.06) * float(
                effective_weights.get("retrieval_quality_weight_scale") or 1.0
            )
            score += retrieval_quality_contrib

            if isinstance(approval_workflow, dict):
                is_required = bool(approval_workflow.get("required"))
                wf_status = str(approval_workflow.get("status") or "").strip().lower()
                if require_approved_auto and is_required and wf_status != "approved":
                    continue
                approval_contrib = 0.0
                if wf_status == "approved":
                    approval_contrib = 1.5 * float(effective_weights.get("approval_bonus_weight") or 1.0)
                    score += approval_contrib
            else:
                approval_contrib = 0.0

            if isinstance(standard_validity_timeline, dict):
                status = str(standard_validity_timeline.get("timeline_status") or "").strip().lower()
                if status == "active":
                    score += 1.5 * float(effective_weights.get("timeline_weight") or 1.0)
                elif status == "review_required":
                    score -= 1.5 * float(effective_weights.get("timeline_weight") or 1.0)

            timeline_match = _timeline_match_for_bid(
                standard_validity_timeline if isinstance(standard_validity_timeline, dict) else {},
                bid_date_key=bid_date_key,
                allow_superseded=bool(allow_superseded),
            )
            if bid_date_key > 0 and not bool(timeline_match.get("allow")):
                continue
            t_state = str(timeline_match.get("state") or "")
            if t_state == "active":
                score += 0.9 * float(effective_weights.get("timeline_weight") or 1.0)
            elif t_state in {"superseded_allowed", "expired"}:
                score -= 0.6 * float(effective_weights.get("timeline_weight") or 1.0)

            if norm_region:
                region_blob = json.dumps(regional_policy_layers, ensure_ascii=False).upper()
                default_region = str(
                    regional_policy_layers.get("default_region")
                    if isinstance(regional_policy_layers, dict)
                    else ""
                ).upper()
                if norm_region not in region_blob and norm_region not in {default_region, "CN"}:
                    continue
                score += 1.0 * float(effective_weights.get("region_weight") or 1.0)

            region_plugin_match = _evaluate_region_plugin(
                plugin=region_plugin,
                regional_policy_layers=regional_policy_layers if isinstance(regional_policy_layers, dict) else {},
                payload=payload,
                source_hierarchy=str(row["source_hierarchy"] or ""),
            )
            if norm_region and region_plugin and not bool(region_plugin_match.get("allow")):
                continue
            region_plugin_contrib = float(region_plugin_match.get("bonus") or 0.0) * float(
                effective_weights.get("region_weight") or 1.0
            )
            score += region_plugin_contrib

            if isinstance(process_parameter_pack, dict) and bool(process_parameter_pack.get("enabled")):
                score += 0.8
            if isinstance(resource_productivity_model, dict) and bool(resource_productivity_model.get("enabled")):
                score += 0.8
            if isinstance(risk_trigger_matrix, dict) and bool(risk_trigger_matrix.get("enabled")):
                score += 0.8
            if isinstance(clause_locator, dict) and bool(clause_locator.get("enabled")):
                score += 0.8
            if isinstance(interface_contract, dict) and bool(interface_contract.get("enabled")):
                score += 0.6
            if isinstance(optimization_objectives_ext, dict) and bool(optimization_objectives_ext.get("enabled")):
                score += 0.5
            if isinstance(online_learning_profile, dict) and bool(online_learning_profile.get("enabled")):
                score += 0.4
            if bool(learning_apply.get("applied")):
                score += 0.25
            if isinstance(evidence_completeness, dict):
                ratio = _safe_float(evidence_completeness.get("completeness_ratio"), 0.0)
                if ratio >= 0.8:
                    score += 1.2
                elif ratio <= 0.3:
                    score -= 1.2
            if isinstance(uncertainty_profile, dict) and bool(uncertainty_profile.get("enabled")):
                confidence = _safe_float(uncertainty_profile.get("confidence_level"), 0.0)
                if confidence >= 0.75:
                    score += 0.9
                elif confidence >= 0.55:
                    score += 0.4
                elif confidence < 0.4:
                    score -= 0.9
            if isinstance(formula_safety_profile, dict) and bool(formula_safety_profile.get("enabled")):
                if bool(formula_safety_profile.get("safe")):
                    score += 1.0
                else:
                    score -= 1.4
            if isinstance(abnormal_scenario_playbook, dict) and bool(abnormal_scenario_playbook.get("enabled")):
                score += 0.4
            if isinstance(deduction_counterexample_library, dict) and bool(
                deduction_counterexample_library.get("enabled")
            ):
                score += 0.4

            if (norm_tags or norm_keywords or query_tokens) and score <= 0:
                continue

            merged_domain_matches = sorted(set([str(x) for x in (domain_matches or []) + (long_tail_match.get("matches") or []) if str(x)]))
            score_breakdown = {
                "tag_contrib": round(tag_contrib, 6),
                "keyword_exact_contrib": round(keyword_exact_contrib, 6),
                "keyword_fuzzy_contrib": round(keyword_fuzzy_contrib, 6),
                "query_token_contrib": round(query_token_contrib, 6),
                "fts_contrib": round(fts_contrib, 6),
                "domain_contrib": round(domain_contrib, 6),
                "gemini_contrib": round(gemini_contrib, 6),
                "retrieval_quality_contrib": round(retrieval_quality_contrib, 6),
                "approval_contrib": round(approval_contrib, 6),
                "region_plugin_contrib": round(region_plugin_contrib, 6),
            }
            retrieval_explainability = {
                "enabled": True,
                "query_tokens": query_tokens[:20],
                "matched_query_tokens": [token for token in query_tokens if token in merged][:20],
                "matched_tags": [tag for tag in norm_tags if tag in tags_row][:20],
                "matched_keywords_exact": [kw for kw in norm_keywords if kw in keywords_row][:20],
                "matched_keywords_fuzzy": [
                    kw for kw in norm_keywords if kw not in keywords_row and (kw in title_norm or kw in body_norm)
                ][:20],
                "domain_matches": merged_domain_matches,
                "long_tail_match": long_tail_match,
                "query_dimensions": query_dimensions,
                "timeline_match_state": timeline_match.get("state"),
                "regional_plugin_reasons": region_plugin_match.get("reasons") if isinstance(region_plugin_match, dict) else [],
                "score_breakdown": score_breakdown,
            }
            result_item = {
                "node_id": row["node_uid"],
                "title": title,
                "snippet": body[:260],
                "tags": tags_row[:12],
                "keywords": keywords_row[:18],
                "source_file": row["file_name"],
                "source_path": row["source_path"],
                "source_hierarchy": row["source_hierarchy"],
                "node_type": row["node_type"],
                "object_key": row["object_key"],
                "entity_master_key": entity_master_key,
                "applicable_conditions": _safe_json_load(row["applicable_conditions_json"], {}),
                "resource_requirements": resource_requirements,
                "safety_level": row["safety_level"],
                "formula_expression": formula_expression,
                "formula_variables": _safe_json_load(row["formula_variables_json"], []),
                "data_source_type": row["data_source_type"],
                "spatial_context": _safe_json_load(row["spatial_context_json"], {}),
                "activation_signal": activation_signal,
                "dna_verified": bool(int(row["dna_verified"] or 0)),
                "tactical_mode": row["tactical_mode"],
                "bid_response_strategy": _safe_json_load(row["bid_response_strategy_json"], {}),
                "competitor_shield": _safe_json_load(row["competitor_shield_json"], {}),
                "qt_score_booster": _safe_json_load(row["qt_score_booster_json"], {}),
                "quantitative_indices": _safe_json_load(row["quantitative_indices_json"], {}),
                "numeric_sources": numeric_sources,
                "schedule_constraints": _safe_json_load(row["schedule_constraints_json"], {}),
                "standard_validity_timeline": standard_validity_timeline,
                "timeline_match": timeline_match,
                "regional_policy_layers": regional_policy_layers,
                "regional_policy_plugin": region_plugin_match,
                "unit_dimension_model": unit_dimension_model,
                "evidence_anchors": evidence_anchors,
                "cross_discipline_constraints": cross_discipline_constraints,
                "retrieval_benchmark": retrieval_benchmark,
                "approval_workflow": approval_workflow,
                "formula_sensitivity": formula_sensitivity,
                "bim_ifc_context": bim_ifc_context,
                "process_parameter_pack": process_parameter_pack,
                "resource_productivity_model": resource_productivity_model,
                "risk_trigger_matrix": risk_trigger_matrix,
                "clause_locator": clause_locator,
                "cross_discipline_interface_contract": interface_contract,
                "optimization_objectives_ext": optimization_objectives_ext,
                "online_learning_profile": online_learning_profile,
                "retrieval_learning_adjustment": learning_apply,
                "long_tail_profile": long_tail_profile,
                "long_tail_match": long_tail_match,
                "entity_alignment": entity_alignment,
                "regional_standard_timeline": regional_standard_timeline,
                "abnormal_scenario_playbook": abnormal_scenario_playbook,
                "deduction_counterexample_library": deduction_counterexample_library,
                "formula_safety_profile": formula_safety_profile,
                "evidence_completeness": evidence_completeness,
                "evidence_strength": evidence_strength,
                "uncertainty_profile": uncertainty_profile,
                "uncertainty_interval": uncertainty_interval,
                "incremental_fingerprint": incremental_fingerprint,
                "incremental_update": incremental_update,
                "professional_domain_matches": merged_domain_matches,
                "retrieval_explainability": retrieval_explainability,
                "gemini_usefulness_score": gemini_usefulness_score,
                "retrieval_quality_score": retrieval_quality_score,
                "score": round(score, 4),
                "payload": payload,
                "source_provenance": {
                    "source_file": row["file_name"],
                    "source_path": row["source_path"],
                    "source_hierarchy": row["source_hierarchy"],
                    "timeline_status": standard_validity_timeline.get("timeline_status")
                    if isinstance(standard_validity_timeline, dict)
                    else "",
                    "timeline_match_state": timeline_match.get("state"),
                    "entity_master_key": entity_master_key,
                    "evidence_completeness_ratio": _safe_float(evidence_completeness.get("completeness_ratio"), 0.0),
                    "evidence_strength_grade": str(evidence_strength.get("grade") or ""),
                    "evidence_strength_score": _safe_float(evidence_strength.get("score"), 0.0),
                    "uncertainty_confidence_level": _safe_float(uncertainty_profile.get("confidence_level"), 0.0),
                    "long_tail_specialty_tag": str(long_tail_profile.get("specialty_tag") or ""),
                },
            }
            results.append(result_item)

        results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        before = len(results)
        if resolve_authority:
            results = self._apply_authority_resolution(results)
            results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)

        return {
            "ok": True,
            "query": query,
            "tags": norm_tags,
            "keywords": norm_keywords,
            "query_dimensions": query_dimensions,
            "node_types": norm_node_types,
            "professional_domains": norm_domains,
            "min_gemini_usefulness_score": min_gemini_score,
            "min_retrieval_quality_score": min_retrieval_quality,
            "region_context": norm_region,
            "bid_date": bid_date_text,
            "allow_superseded": bool(allow_superseded),
            "require_approved_auto": bool(require_approved_auto),
            "total": len(results),
            "results": results[:top_k],
            "db_path": str(self.db_path),
            "retrieval_score_weights": score_weights,
            "retrieval_weight_profile_path": (
                str(Path(retrieval_weight_profile_path).expanduser().resolve())
                if retrieval_weight_profile_path not in (None, "")
                else ""
            ),
            "regional_policy_plugin": {
                "applied": bool(norm_region and region_plugin),
                "region_code": region_plugin.get("region_code") if isinstance(region_plugin, dict) else "",
                "plugin_name": (
                    (region_plugin.get("metadata") or {}).get("plugin_name")
                    if isinstance(region_plugin, dict)
                    else ""
                ),
            },
            "authority_resolution": {
                "applied": bool(resolve_authority),
                "rule": SOURCE_HIERARCHY_RULE,
                "before": before,
                "after": len(results),
            },
            "explainability": {
                "enabled": True,
                "includes": [
                    "retrieval_explainability.score_breakdown",
                    "retrieval_explainability.matched_terms",
                    "source_provenance",
                    "evidence_strength",
                ],
            },
        }

    def evaluate_formula_nodes(
        self,
        *,
        variables: Dict[str, Any],
        query: str = "",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 12,
        professional_domains: Optional[List[str]] = None,
        min_gemini_usefulness_score: float = 0.0,
        resolve_authority: bool = True,
    ) -> Dict[str, Any]:
        search_result = self.search(
            query=query,
            tags=tags,
            keywords=keywords,
            top_k=top_k,
            node_types=["FormulaNode"],
            professional_domains=professional_domains,
            min_gemini_usefulness_score=min_gemini_usefulness_score,
            resolve_authority=resolve_authority,
        )

        computed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for item in search_result.get("results") or []:
            expr = str(item.get("formula_expression") or "").strip()
            if not expr:
                errors.append({"node_id": item.get("node_id"), "error": "empty_formula_expression"})
                continue
            try:
                value = _safe_eval_formula(expr, variables)
                computed.append({**item, "computed_result": value, "variables": dict(variables)})
            except Exception as exc:
                errors.append({"node_id": item.get("node_id"), "error": str(exc), "formula_expression": expr})

        return {
            "ok": len(computed) > 0 and len(errors) == 0,
            "query": query,
            "variables": dict(variables),
            "total": len(computed),
            "results": computed,
            "errors": errors,
            "authority_resolution": search_result.get("authority_resolution"),
            "db_path": str(self.db_path),
        }

    def get_edges(
        self,
        *,
        edge_type: str | None = None,
        node_ref: str | None = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        clauses: List[str] = []
        params: List[Any] = []
        if edge_type:
            clauses.append("e.edge_type = ?")
            params.append(str(edge_type).strip().upper())

        node_id: Optional[int] = None
        if node_ref:
            with self._connect() as conn:
                node_id = self._resolve_node_id(conn, str(node_ref), {})
            if node_id:
                clauses.append("(e.from_node_id = ? OR e.to_node_id = ?)")
                params.extend([node_id, node_id])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    e.id,
                    e.edge_type,
                    e.edge_label,
                    e.source_path,
                    fn.node_uid AS from_uid,
                    fn.title AS from_title,
                    tn.node_uid AS to_uid,
                    tn.title AS to_title
                FROM graph_edges e
                JOIN nodes fn ON fn.id = e.from_node_id
                JOIN nodes tn ON tn.id = e.to_node_id
                {where_sql}
                ORDER BY e.id ASC
                LIMIT ?
                """,
                tuple(params + [max(1, min(int(limit), 5000))]),
            ).fetchall()

        items = [
            {
                "edge_id": int(r["id"]),
                "edge_type": r["edge_type"],
                "edge_label": r["edge_label"],
                "source_path": r["source_path"],
                "from_node_id": r["from_uid"],
                "from_title": r["from_title"],
                "to_node_id": r["to_uid"],
                "to_title": r["to_title"],
            }
            for r in rows
        ]
        return {"ok": True, "total": len(items), "edges": items, "db_path": str(self.db_path)}

    def validate_requires_closure(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.from_node_id,
                    e.to_node_id,
                    fn.node_uid AS from_uid,
                    tn.node_uid AS to_uid
                FROM graph_edges e
                JOIN nodes fn ON fn.id = e.from_node_id
                JOIN nodes tn ON tn.id = e.to_node_id
                WHERE e.edge_type = ?
                """,
                (EDGE_REQUIRES,),
            ).fetchall()

        graph: Dict[int, List[int]] = {}
        id_to_uid: Dict[int, str] = {}
        for row in rows:
            f = int(row["from_node_id"])
            t = int(row["to_node_id"])
            graph.setdefault(f, []).append(t)
            graph.setdefault(t, [])
            id_to_uid[f] = str(row["from_uid"])
            id_to_uid[t] = str(row["to_uid"])

        visited: Dict[int, int] = {}  # 0=unseen,1=visiting,2=done
        stack: List[int] = []
        cycles: List[List[str]] = []

        def dfs(node: int) -> None:
            state = visited.get(node, 0)
            if state == 1:
                if node in stack:
                    idx = stack.index(node)
                    cyc = stack[idx:] + [node]
                    cycles.append([id_to_uid.get(x, str(x)) for x in cyc])
                return
            if state == 2:
                return

            visited[node] = 1
            stack.append(node)
            for nxt in graph.get(node, []):
                dfs(nxt)
            stack.pop()
            visited[node] = 2

        for node in list(graph.keys()):
            if visited.get(node, 0) == 0:
                dfs(node)

        return {
            "ok": len(cycles) == 0,
            "edge_type": EDGE_REQUIRES,
            "edge_count": len(rows),
            "cycle_count": len(cycles),
            "cycles": cycles,
            "db_path": str(self.db_path),
        }


def ingest_knowledge_graph(
    root_dir: Path | str = DEFAULT_KG_ROOT,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
    force_reindex: bool = False,
    activation_context: str | None = None,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path, activation_context=activation_context)
    return index.ingest_directory(root_dir=root_dir, force_reindex=force_reindex)


def search_graph_index(
    *,
    query: str = "",
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    top_k: int = 12,
    node_types: Optional[List[str]] = None,
    professional_domains: Optional[List[str]] = None,
    min_gemini_usefulness_score: float = 0.0,
    min_retrieval_quality_score: float = 0.0,
    region_context: str | None = None,
    bid_date: str | None = None,
    allow_superseded: bool = False,
    regional_plugin_dir: Path | str | None = None,
    retrieval_weight_profile_path: Path | str | None = None,
    require_approved_auto: bool = False,
    resolve_authority: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.search(
        query=query,
        tags=tags,
        keywords=keywords,
        top_k=top_k,
        node_types=node_types,
        professional_domains=professional_domains,
        min_gemini_usefulness_score=min_gemini_usefulness_score,
        min_retrieval_quality_score=min_retrieval_quality_score,
        region_context=region_context,
        bid_date=bid_date,
        allow_superseded=allow_superseded,
        regional_plugin_dir=regional_plugin_dir,
        retrieval_weight_profile_path=retrieval_weight_profile_path,
        require_approved_auto=require_approved_auto,
        resolve_authority=resolve_authority,
    )


def evaluate_formula_nodes_in_graph(
    *,
    variables: Dict[str, Any],
    query: str = "",
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    top_k: int = 12,
    professional_domains: Optional[List[str]] = None,
    min_gemini_usefulness_score: float = 0.0,
    resolve_authority: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.evaluate_formula_nodes(
        variables=variables,
        query=query,
        tags=tags,
        keywords=keywords,
        top_k=top_k,
        professional_domains=professional_domains,
        min_gemini_usefulness_score=min_gemini_usefulness_score,
        resolve_authority=resolve_authority,
    )


def get_graph_edges(
    *,
    edge_type: str | None = None,
    node_ref: str | None = None,
    limit: int = 500,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.get_edges(edge_type=edge_type, node_ref=node_ref, limit=limit)


def validate_requires_edges(
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.validate_requires_closure()
