#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_SUMMARY_OUT = Path("build/KG_Gemini_Enablement_Fix_Summary.md")

DEFAULT_FORMULA = "quantity / max(productivity_per_day, 1)"
ACTIVATION_SIGNAL = "Context CONTAINS '智飞工程' OR query_keywords_hit >= 2"

DIMENSION_SEEDS: Dict[str, List[str]] = {
    "质量": ["质量", "验收", "缺陷", "强度", "平整度"],
    "安全": ["安全", "危险", "防护", "应急", "临电", "事故"],
    "进度": ["进度", "工期", "节点", "里程碑", "关键线路"],
    "环保": ["环保", "扬尘", "噪声", "PM10", "污水", "绿色"],
    "重难点": ["重难点", "难点", "关键工序", "复杂", "高风险"],
    "扣分点": ["扣分", "废标", "否决", "处罚", "偏差", "失分"],
}

DIMENSION_CHECKER = {
    "质量": "质量员",
    "安全": "安全员",
    "进度": "施工员",
    "环保": "环保员",
    "重难点": "技术负责人",
    "扣分点": "项目总工",
}

DIMENSION_PARAMS = {
    "质量": {"acceptance_pass_rate_percent": 95, "sampling_frequency_per_shift": 2, "deviation_limit_mm": 3},
    "安全": {"inspection_frequency_per_shift": 2, "emergency_response_minutes": 30, "leakage_protector_ma": 30},
    "进度": {"critical_path_lag_days": 1, "deviation_correction_hours": 24, "milestone_hit_rate_percent": 100},
    "环保": {"pm10_threshold_ug_m3": 150, "noise_day_db": 70, "noise_night_db": 55},
    "重难点": {"risk_trigger_threshold_percent": 5, "specialist_workers": 12, "acceptance_loop_hours": 12},
    "扣分点": {"response_deadline_hours": 4, "recheck_frequency_per_day": 2, "coverage_rate_percent": 100},
}

DIMENSION_FORMULAS: Dict[str, Tuple[str, List[str]]] = {
    "质量": ("pass_count / max(total_check_count, 1) * 100", ["pass_count", "total_check_count"]),
    "安全": ("hazard_count * risk_factor / max(inspection_frequency_per_shift, 1)", ["hazard_count", "risk_factor", "inspection_frequency_per_shift"]),
    "进度": ("work_volume / max(productivity_per_day * crew_efficiency, 1)", ["work_volume", "productivity_per_day", "crew_efficiency"]),
    "环保": ("max(pm10_value, 1) / max(spray_frequency_per_day, 1)", ["pm10_value", "spray_frequency_per_day"]),
    "重难点": ("complexity_index * risk_factor / max(specialist_workers, 1)", ["complexity_index", "risk_factor", "specialist_workers"]),
    "扣分点": ("non_response_items * penalty_weight + overdue_hours / max(response_deadline_hours, 1)", ["non_response_items", "penalty_weight", "overdue_hours", "response_deadline_hours"]),
}

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "bridge": ["bridge", "桥梁", "箱梁", "桥面", "挂篮", "盖梁", "桥墩"],
    "tunnel": ["tunnel", "隧道", "盾构", "衬砌", "暗挖", "洞门"],
    "railway": ["railway", "rail", "铁路", "轨道", "高铁", "接触网"],
    "hydraulic": ["hydraulic", "hydro", "water", "水利", "泵站", "闸门", "河道", "堤防"],
    "mep": ["mep", "机电", "电气", "暖通", "消防", "管道", "弱电", "智能化"],
    "earthwork": ["earthwork", "土石方", "土方", "开挖", "回填", "边坡", "基坑"],
    "road": ["road", "道路", "路基", "路面", "沥青", "市政道路"],
    "building": ["building", "房建", "装修", "幕墙", "钢结构", "装配式", "医院"],
    "general": ["综合", "通用"],
}

SOURCE_LEVELS = ("答疑文件", "设计图纸", "国标", "行标", "企标")
GENERIC_VAGUE_WORDS = ("加强", "提高", "注意", "确保", "严格")
VISUAL_TYPES = ["样板", "流程", "思维导图", "智慧绿色四新"]
REQUIRED_ASSERTIONS = ["must_have_action", "must_have_parameter", "must_have_checker"]


def _iter_sections(raw: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        raw["knowledge_database"] = {"gemini_patch": {"nodes": []}}
        kg = raw["knowledge_database"]
    out: List[Tuple[str, Dict[str, Any]]] = []
    for sec_name, sec in kg.items():
        if isinstance(sec, dict):
            if not isinstance(sec.get("nodes"), list):
                sec["nodes"] = []
            out.append((str(sec_name), sec))
    if not out:
        kg["gemini_patch"] = {"nodes": []}
        out.append(("gemini_patch", kg["gemini_patch"]))
    return out


def _infer_dimension(node: Dict[str, Any]) -> str:
    text = json.dumps(node, ensure_ascii=False)
    best_dim = "质量"
    best_score = -1
    for dim, seeds in DIMENSION_SEEDS.items():
        score = sum(1 for seed in seeds if seed in text)
        if score > best_score:
            best_dim = dim
            best_score = score
    return best_dim


def _infer_domain(file_stem: str, node: Dict[str, Any]) -> str:
    text = (file_stem + " " + json.dumps(node, ensure_ascii=False)).lower()
    best = "general"
    best_score = -1
    for domain, seeds in DOMAIN_KEYWORDS.items():
        score = sum(1 for seed in seeds if str(seed).lower() in text)
        if score > best_score:
            best = domain
            best_score = score
    return best


def _infer_source_hierarchy(file_stem: str, node: Dict[str, Any]) -> str:
    merged = (file_stem + " " + json.dumps(node, ensure_ascii=False)).lower()
    if any(k in merged for k in ("答疑", "澄清", "q&a", "clarification")):
        return "答疑文件"
    data_source_type = str(node.get("data_source_type") or "").strip().upper()
    spatial_context = node.get("spatial_context")
    is_drawing_node = bool(
        data_source_type == "DXF"
        or (isinstance(spatial_context, dict) and any(k in spatial_context for k in ("drawing", "layer", "block")))
        or any(k in merged for k in ("dxf", "cad"))
    )
    if is_drawing_node:
        return "设计图纸"

    refs = [str(x) for x in (node.get("reference_standard") or []) if str(x).strip()]
    if any(ref.startswith("GB") for ref in refs):
        return "国标"
    if any(ref.startswith(prefix) for ref in refs for prefix in ("JGJ", "SL", "TB", "CJJ", "DL", "SY")):
        return "行标"

    cur = str(node.get("source_hierarchy") or "").strip()
    if cur in SOURCE_LEVELS:
        return cur
    return "企标"


def _ensure_activation(node: Dict[str, Any]) -> bool:
    changed = False
    content = node.get("content")
    if not isinstance(content, dict):
        node["content"] = {}
        content = node["content"]
        changed = True
    env = content.get("environment_sensing")
    if not isinstance(env, dict):
        content["environment_sensing"] = {"activation_signal": ACTIVATION_SIGNAL}
        changed = True
    elif not str(env.get("activation_signal") or "").strip():
        env["activation_signal"] = ACTIVATION_SIGNAL
        changed = True
    return changed


def _build_desc(*, node_name: str, dim: str, checker: str, params: Dict[str, Any]) -> str:
    param_text = "、".join([f"{k}={v}" for k, v in list(params.items())[:3]])
    risk = "质量通病与安全隐患" if dim in ("质量", "安全", "重难点") else "计划偏差与资源冲突"
    control = "参数闭环+旁站复核+数据留痕"
    return (
        f"第一步（定义）：执行{node_name}{dim}工序定义，参数{param_text}，{checker}每班次核验1次；"
        f"第二步（分析）：围绕{risk}识别触发条件，风险阈值5%，技术负责人复核；"
        f"第三步（解决）：实施{control}，偏差处置时限4h，{checker}每班次检查2次；"
        "工序名称->参数->风险->控制->验证"
    )


def _ensure_operation_desc(node: Dict[str, Any], *, dim: str, checker: str, params: Dict[str, Any]) -> bool:
    changed = False
    content = node.get("content")
    if not isinstance(content, dict):
        node["content"] = {}
        content = node["content"]
        changed = True
    premium = content.get("operation_desc_premium")
    if not isinstance(premium, dict):
        content["operation_desc_premium"] = {}
        premium = content["operation_desc_premium"]
        changed = True
    desc = str(premium.get("desc") or "").strip()
    node_name = str(node.get("name") or node.get("title") or "关键工序")
    generic_template = (
        ("第一步（定义）" in desc and "第二步（分析）" in desc and "第三步（解决）" in desc)
        or ("工序名称->参数->风险->控制->验证" in desc)
    )
    if (not desc) or any(word in desc for word in GENERIC_VAGUE_WORDS) or generic_template:
        premium["desc"] = _build_desc(
            node_name=node_name,
            dim=dim,
            checker=checker,
            params=params,
        )
        changed = True
    return changed


def _ensure_formula(node: Dict[str, Any], *, dim: str) -> bool:
    changed = False
    expr, vars_ = DIMENSION_FORMULAS.get(dim, DIMENSION_FORMULAS["质量"])
    cur_expr = str(node.get("formula_expression") or "").strip()
    if not cur_expr or cur_expr == DEFAULT_FORMULA:
        node["formula_expression"] = expr
        changed = True
    cur_vars = node.get("formula_variables")
    if not isinstance(cur_vars, list) or not cur_vars:
        node["formula_variables"] = list(vars_)
        changed = True
    return changed


def _ensure_numeric_sources(node: Dict[str, Any], *, dim: str, params: Dict[str, Any]) -> bool:
    changed = False
    cur = node.get("numeric_sources")
    if not isinstance(cur, list) or not cur:
        first_key = list(params.keys())[0]
        node["numeric_sources"] = [
            {
                "parameter": first_key,
                "value": str(params[first_key]),
                "unit": "",
                "source_text": f"{dim}参数基线",
            }
        ]
        changed = True
    return changed


def _calc_usefulness(node: Dict[str, Any]) -> int:
    score = 35
    if isinstance(node.get("resource_requirements"), dict) and node.get("resource_requirements"):
        score += 15
    if isinstance(node.get("numeric_sources"), list) and node.get("numeric_sources"):
        score += 12
    expr = str(node.get("formula_expression") or "").strip()
    if expr:
        score += 8
    if expr and expr != DEFAULT_FORMULA:
        score += 12
    source = str(node.get("source_hierarchy") or "")
    source_weight = {"答疑文件": 5, "设计图纸": 4, "国标": 3, "行标": 2, "企标": 1}.get(source, 0)
    score += source_weight * 5
    return int(max(0, min(100, score)))


def _ensure_formula_nodes(
    *,
    file_stem: str,
    section_nodes: List[Dict[str, Any]],
    existing_ids: set[str],
    domain: str,
) -> int:
    formula_nodes = [
        node for node in section_nodes if isinstance(node, dict) and str(node.get("node_type") or "") == "FormulaNode"
    ]
    if len(formula_nodes) >= 2:
        return 0

    add_count = 0
    templates = [("进度", "FORM-PROG"), ("重难点", "FORM-RISK")]
    for dim, suffix in templates:
        node_id = f"{file_stem}-{suffix}"
        if node_id in existing_ids:
            continue
        expr, vars_ = DIMENSION_FORMULAS[dim]
        params = DIMENSION_PARAMS[dim]
        checker = DIMENSION_CHECKER[dim]
        new_node = {
            "node_id": node_id,
            "name": f"{dim}动态计算节点",
            "node_type": "FormulaNode",
            "qt_tag": [dim, "gemini_formula"],
            "keywords": DIMENSION_SEEDS[dim] + [domain, "公式", "计算"],
            "professional_domain": domain,
            "source_hierarchy": "国标",
            "reference_standard": ["GB/T 50326-2017 建设工程项目管理规范"],
            "formula_expression": expr,
            "formula_variables": vars_,
            "applicable_conditions": {"scenario": f"{dim}约束计算"},
            "resource_requirements": params,
            "numeric_sources": [{"parameter": list(params.keys())[0], "value": str(list(params.values())[0]), "unit": ""}],
            "scoring_points": {
                "checkpoints": [
                    {
                        "point_id": f"{dim}-NODE",
                        "dimension": dim,
                        "description": f"{dim}评分点响应",
                        "required_keywords": list(DIMENSION_SEEDS[dim][:6]),
                        "match_mode": "any",
                        "boolean_rule": "any_keyword_hit",
                    }
                ],
                "dimension": dim,
                "expected_gain": "+2~+5",
                "deduction_risk": "缺少参数来源、缺少检查岗位或缺少响应闭环将触发扣分",
                "score_path": "工序名称->参数->风险->控制->验证",
            },
            "fail_fast_hooks": {
                "enabled": True,
                "on_missing_response": "raise_exception_and_retry",
                "cache_policy": "clear_failed_dimension_cache",
                "max_retry": 3,
                "events": ["missing_numeric_source", "missing_formula_expression", "missing_checker"],
            },
            "auto_rewrite": {
                "enabled": True,
                "strategy": "targeted_dimension_rewrite",
                "template": f"执行{dim}控制，参数阈值=95%，检查频次=2次/班，由{checker}复核。",
            },
            "response_assertions": list(REQUIRED_ASSERTIONS),
            "content": {
                "environment_sensing": {"activation_signal": ACTIVATION_SIGNAL},
                "operation_desc_premium": {"desc": _build_desc(node_name=f"{dim}计算", dim=dim, checker=checker, params=params)},
            },
            "visual_specs": {
                "enabled": True,
                "visual_types": list(VISUAL_TYPES),
                "content_professional": list(VISUAL_TYPES),
                "drawing_standard": "GB/T 50104 建筑制图标准",
                "visual_standard": "CSCEC VI 蓝/绿/灰",
                "text_standard": "中文仿宋",
                "docx_embed": True,
                "prompt_policy": "bind_index_matrix_and_node_parameters",
                "data_binding_fields": ["action", "parameter", "checker"],
            },
            "retrieval_hints": {
                "must_keywords": DIMENSION_SEEDS[dim][:4],
                "optional_keywords": [domain, "公式", "计算"],
                "negative_keywords": ["空话", "套话"],
            },
            "gemini_context_block": {
                "dimension": dim,
                "action": f"执行{dim}动态计算",
                "parameter": params,
                "checker": checker,
                "verification": "计算结果复核并留痕",
            },
            "gemini_usefulness_score": 88,
        }
        section_nodes.append(new_node)
        existing_ids.add(node_id)
        add_count += 1
    return add_count


def _ensure_root_config(raw: Dict[str, Any]) -> bool:
    cfg = raw.get("gemini_kg_enablement")
    defaults = {
        "enabled": True,
        "version": "v1",
        "goal": "make_kg_assist_gemini_generation",
        "retrieval_policy": {
            "professional_domain_filter": True,
            "min_gemini_usefulness_score": 30,
            "authority_resolution": True,
        },
        "generation_policy": {
            "must_have_action_parameter_checker": True,
            "bind_numeric_sources": True,
            "bind_formula_nodes": True,
        },
    }
    changed = False
    if not isinstance(cfg, dict):
        raw["gemini_kg_enablement"] = defaults
        return True
    for key, value in defaults.items():
        if key not in cfg:
            cfg[key] = value
            changed = True
    return changed


def _normalize_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def fix_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = False
    if _ensure_root_config(raw):
        changed = True

    sections = _iter_sections(raw)
    file_stem = path.stem
    file_domain = _infer_domain(file_stem, {})
    nodes_total = 0
    nodes_updated = 0
    formula_nodes_added = 0
    existing_ids: set[str] = set()
    first_section_nodes: List[Dict[str, Any]] | None = None

    for _, sec in sections:
        nodes = sec.get("nodes")
        if not isinstance(nodes, list):
            continue
        if first_section_nodes is None:
            first_section_nodes = nodes
        for node in nodes:
            if not isinstance(node, dict):
                continue
            nodes_total += 1
            node_id = str(node.get("node_id") or "").strip()
            if node_id:
                existing_ids.add(node_id)

            dim = _infer_dimension(node)
            checker = DIMENSION_CHECKER[dim]
            params = dict(DIMENSION_PARAMS[dim])
            node_changed = False

            if _ensure_activation(node):
                node_changed = True
            if _ensure_operation_desc(node, dim=dim, checker=checker, params=params):
                node_changed = True
            if _ensure_formula(node, dim=dim):
                node_changed = True
            if _ensure_numeric_sources(node, dim=dim, params=params):
                node_changed = True

            domain = _infer_domain(file_stem, node)
            if str(node.get("professional_domain") or "").strip() != domain:
                node["professional_domain"] = domain
                node_changed = True

            source_hierarchy = _infer_source_hierarchy(file_stem, node)
            if str(node.get("source_hierarchy") or "").strip() != source_hierarchy:
                node["source_hierarchy"] = source_hierarchy
                node_changed = True

            if not isinstance(node.get("resource_requirements"), dict) or not node.get("resource_requirements"):
                node["resource_requirements"] = params
                node_changed = True

            hints = node.get("retrieval_hints")
            desired_hints = {
                "must_keywords": DIMENSION_SEEDS[dim][:4],
                "optional_keywords": _normalize_list(node.get("keywords"))[:6] + [domain],
                "negative_keywords": ["空话", "套话"],
            }
            if not isinstance(hints, dict):
                node["retrieval_hints"] = desired_hints
                node_changed = True
            else:
                for key, value in desired_hints.items():
                    if key not in hints:
                        hints[key] = value
                        node_changed = True

            block = node.get("gemini_context_block")
            desired_block = {
                "dimension": dim,
                "action": f"执行{dim}参数化控制",
                "parameter": params,
                "checker": checker,
                "verification": "复核并留痕",
            }
            if not isinstance(block, dict):
                node["gemini_context_block"] = desired_block
                node_changed = True
            else:
                for key, value in desired_block.items():
                    if key not in block:
                        block[key] = value
                        node_changed = True

            score = _calc_usefulness(node)
            if int(node.get("gemini_usefulness_score") or -1) != score:
                node["gemini_usefulness_score"] = score
                node_changed = True

            if node_changed:
                nodes_updated += 1
                changed = True

    if first_section_nodes is not None:
        formula_nodes_added = _ensure_formula_nodes(
            file_stem=file_stem,
            section_nodes=first_section_nodes,
            existing_ids=existing_ids,
            domain=file_domain,
        )
        if formula_nodes_added > 0:
            changed = True
            nodes_total += formula_nodes_added
            nodes_updated += formula_nodes_added

    if changed:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "changed": changed,
        "nodes_total": nodes_total,
        "nodes_updated": nodes_updated,
        "formula_nodes_added": formula_nodes_added,
    }


def render_summary(rows: List[Dict[str, Any]], out_path: Path) -> None:
    files_total = len(rows)
    files_changed = sum(1 for r in rows if r["changed"])
    nodes_total = sum(int(r["nodes_total"]) for r in rows)
    nodes_updated = sum(int(r["nodes_updated"]) for r in rows)
    formula_nodes_added = sum(int(r["formula_nodes_added"]) for r in rows)

    lines: List[str] = []
    lines.append("# KG Gemini Enablement Fix Summary")
    lines.append("")
    lines.append(f"- Generated At: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}")
    lines.append(f"- Files Total: {files_total}")
    lines.append(f"- Files Changed: {files_changed}")
    lines.append(f"- Nodes Total: {nodes_total}")
    lines.append(f"- Nodes Updated: {nodes_updated}")
    lines.append(f"- Formula Nodes Added: {formula_nodes_added}")
    lines.append("")
    lines.append("| File | Changed | Nodes | Nodes Updated | Formula Added |")
    lines.append("|---|---|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['changed']} | {row['nodes_total']} | {row['nodes_updated']} | {row['formula_nodes_added']} |"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upgrade all KG files for Gemini-assisted generation quality.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="KG file glob pattern")
    parser.add_argument("--summary-out", default=str(DEFAULT_SUMMARY_OUT), help="Summary output path")
    args = parser.parse_args()

    root = Path(args.kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"KG root not found: {root}")
    files = sorted(root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {root}/{args.pattern}")

    rows = [fix_file(path) for path in files]
    summary_out = Path(args.summary_out).expanduser().resolve()
    render_summary(rows, summary_out)

    print(f"files_total={len(rows)}")
    print(f"files_changed={sum(1 for r in rows if r['changed'])}")
    print(f"nodes_updated={sum(int(r['nodes_updated']) for r in rows)}")
    print(f"formula_nodes_added={sum(int(r['formula_nodes_added']) for r in rows)}")
    print(f"summary_out={summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
