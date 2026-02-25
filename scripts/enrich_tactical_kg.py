#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"


def _tokenize_keywords(text: str) -> List[str]:
    chunks = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_-]{2,}", str(text or ""))
    out: List[str] = []
    seen = set()
    for c in chunks:
        t = str(c).strip()
        if len(t) < 2:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if value is None:
        return []
    return [value]


def _as_string_list(value: Any) -> List[str]:
    arr = _safe_list(value)
    out: List[str] = []
    for item in arr:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _ensure_dict(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    val = parent.get(key)
    if isinstance(val, dict):
        return val
    parent[key] = {}
    return parent[key]


def _detect_safety_level(name: str, desc: str) -> str:
    text = f"{name} {desc}"
    if any(k in text for k in ("爆", "火", "高空", "吊装", "深基坑", "临电", "轨道", "铁路", "危", "应急", "防护")):
        return "high"
    if any(k in text for k in ("质量", "验收", "结构", "环保", "巡检")):
        return "medium"
    return "low"


def _build_reference_standards(name: str) -> List[str]:
    text = str(name or "")
    standards = [
        "GB 50300-2013 建筑工程施工质量验收统一标准",
        "JGJ 59-2011 建筑施工安全检查标准",
        "GB/T 50326-2017 建设工程项目管理规范",
    ]
    if any(k in text for k in ("铁路", "轨道", "高铁", "Rail", "Railway")):
        standards.append("TB 10424-2018 铁路混凝土工程施工质量验收标准")
    if any(k in text for k in ("医院", "医疗", "病房", "Hospital")):
        standards.append("GB 51039-2014 综合医院建筑设计规范")
    if any(k in text for k in ("水利", "河道", "Hydro", "Water")):
        standards.append("SL 631-2012 水利水电工程单元工程施工质量验收评定标准")
    return standards


def _build_default_conditions() -> Dict[str, Any]:
    return {
        "climate": "常规施工气候（-10~35℃，风力<=6级）",
        "geology": "按勘察报告执行，异常地层专项复核",
        "site_constraints": "临边临电与交叉作业需审批后实施",
        "construction_window": "按总控计划与作业票执行",
    }


def _build_default_resources(safety_level: str) -> Dict[str, Any]:
    checker = "安全员" if safety_level == "high" else "质量员"
    return {
        "manpower": {
            "crew_size": "8-12人/班",
            "checker_role": checker,
        },
        "equipment": {
            "primary": ["标准施工机械1套"],
            "backup": ["应急设备1套"],
        },
        "material": {
            "acceptance_rule": "100%批次进场验收",
        },
        "inspection_frequency": "2次/班",
    }


def _build_default_strategy(name: str, desc: str, file_stem: str) -> Dict[str, Any]:
    kws = _tokenize_keywords(name)[:2] or _tokenize_keywords(file_stem)[:2] or ["关键工序"]
    return {
        "trigger_keywords": kws,
        "response_template": (
            f"围绕“{name}”执行参数化闭环控制：明确动作、阈值、频次与责任岗位；"
            "异常偏差在4h内完成纠偏并留痕。"
        ),
    }


def _build_default_shield(name: str) -> Dict[str, Any]:
    return {
        "target_rival": "Competitor_Generic",
        "argument": (
            f"传统方案在“{name}”环节易出现参数失控与证据链断点。"
            "本方案通过量化阈值和岗位复核实现可审计闭环。"
        ),
        "trap_logic": "核查对方是否提供“动作+参数+检查岗位+闭环证据”的完整链路。",
    }


def _build_default_booster(safety_level: str) -> Dict[str, Any]:
    return {
        "policy_alignment": ["质量安全", "数字建造", "绿色施工"],
        "score_weight": "+5_Points" if safety_level == "high" else "+3_Points",
    }


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp_01(value: Any, default: float = 0.5) -> float:
    val = _safe_float(value, default)
    return max(0.0, min(1.0, val))


def _extract_numeric_terms(text: str) -> List[Dict[str, Any]]:
    pattern = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|‰|dB|MPa|kPa|mm|cm|m|km|天|h|小时|min|分钟|次/日|次/班|次|人|台|套|m3|m²|m2|t|kg|ug/m3|μg/m3)",
        flags=re.IGNORECASE,
    )
    out: List[Dict[str, Any]] = []
    for m in pattern.finditer(str(text or "")):
        left = str(text[max(0, m.start() - 14) : m.start()] or "").strip()
        parameter = re.sub(r"[\s:：，,。；;、\[\]（）(){}]+", "", left[-10:]) or "parameter"
        out.append(
            {
                "parameter": parameter,
                "value": m.group("value"),
                "unit": m.group("unit"),
                "source_text": str(text[max(0, m.start() - 24) : min(len(text), m.end() + 12)] or "").strip(),
            }
        )
        if len(out) >= 8:
            break
    return out


def _build_default_numeric_sources(
    *,
    node_name: str,
    desc: str,
    formula_expression: str,
    safety_level: str,
) -> List[Dict[str, Any]]:
    out = _extract_numeric_terms(desc)
    if formula_expression:
        out.append(
            {
                "parameter": "formula_result",
                "formula": formula_expression,
                "source_text": "formula_expression",
            }
        )

    if not out:
        out.append(
            {
                "parameter": "inspection_frequency",
                "value": "2",
                "unit": "次/班",
                "source_text": f"{node_name} 默认巡检基线",
            }
        )
    if safety_level in {"high", "critical"}:
        out.append(
            {
                "parameter": "response_time_limit",
                "value": "30",
                "unit": "min",
                "source_text": "高风险工序默认应急时限",
            }
        )
    return out[:12]


def _build_default_quantitative_indices(safety_level: str, resource_req: Dict[str, Any]) -> Dict[str, Any]:
    risk_base = {
        "critical": 0.9,
        "high": 0.78,
        "medium": 0.58,
        "low": 0.38,
    }.get(str(safety_level), 0.5)

    crew_size = 0.0
    manpower = resource_req.get("manpower") if isinstance(resource_req, dict) else {}
    if isinstance(manpower, dict):
        vals = re.findall(r"\d+(?:\.\d+)?", str(manpower.get("crew_size") or ""))
        if vals:
            nums = [float(x) for x in vals]
            crew_size = sum(nums) / max(1, len(nums))

    resource_density = _clamp_01(crew_size / 12.0 if crew_size > 0 else 0.5)
    duration_index = _clamp_01(0.65 if risk_base >= 0.75 else 0.5)
    complexity = _clamp_01(duration_index * 0.35 + risk_base * 0.35 + resource_density * 0.30)

    return {
        "duration_index": round(duration_index, 4),
        "risk_index": round(_clamp_01(risk_base), 4),
        "resource_density_index": round(resource_density, 4),
        "complexity_index": round(complexity, 4),
    }


def _build_default_schedule_constraints(
    *,
    node_id: str,
    prev_id: str | None,
    next_id: str | None,
) -> Dict[str, Any]:
    critical_path_hint: List[str] = [node_id]
    if prev_id:
        critical_path_hint.insert(0, prev_id)
    if next_id:
        critical_path_hint.append(next_id)
    return {
        "critical_path_hint": critical_path_hint[:3],
        "min_process_interval_days": 1,
        "inference_method": "default_cpm_anchor",
    }


def _ensure_formula(node: Dict[str, Any], premium: Dict[str, Any]) -> bool:
    if str(node.get("formula_expression") or "").strip():
        if not _safe_list(node.get("formula_variables")):
            node["formula_variables"] = ["quantity", "productivity_per_day"]
        return False

    math_proof = str(premium.get("math_proof") or "").strip()
    if math_proof:
        m = re.search(r"<=\s*(\d+)\s*h", math_proof, flags=re.IGNORECASE)
        if m:
            hours = int(m.group(1))
            node["formula_expression"] = f"max({hours} - conversion_time_h, 0)"
            node["formula_variables"] = ["conversion_time_h"]
            node["formula_note"] = "由math_proof自动结构化生成"
            return True

    node["formula_expression"] = "quantity / max(productivity_per_day, 1)"
    node["formula_variables"] = ["quantity", "productivity_per_day"]
    return True


def _iter_nodes(root: Dict[str, Any]) -> Iterable[Tuple[str, List[Dict[str, Any]]]]:
    kg = root.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    out: List[Tuple[str, List[Dict[str, Any]]]] = []
    for sec_name, sec_body in kg.items():
        if not isinstance(sec_body, dict):
            continue
        nodes = sec_body.get("nodes")
        if not isinstance(nodes, list):
            continue
        norm_nodes = [n for n in nodes if isinstance(n, dict)]
        out.append((str(sec_name), norm_nodes))
    return out


def enrich_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = 0
    node_count = 0
    quant_ready_count = 0
    numeric_sources_count = 0
    indices_count = 0
    schedule_constraints_count = 0
    sec_nodes = list(_iter_nodes(raw))
    flat_nodes: List[Dict[str, Any]] = []
    for _, nodes in sec_nodes:
        flat_nodes.extend(nodes)

    node_ids = [str(n.get("node_id") or n.get("name") or f"N-{i+1}") for i, n in enumerate(flat_nodes)]

    for i, node in enumerate(flat_nodes):
            node_count += 1
            node_id = str(node.get("node_id") or f"{path.stem}-N-{i+1}")
            node_name = str(node.get("name") or node_id)
            content = _ensure_dict(node, "content")
            env = _ensure_dict(content, "environment_sensing")
            premium = _ensure_dict(content, "operation_desc_premium")

            if not str(env.get("activation_signal") or "").strip():
                env["activation_signal"] = "Context CONTAINS '智飞工程'"
                changed += 1

            mediocre = str(content.get("operation_desc_mediocre") or "").strip()
            if not mediocre:
                content["operation_desc_mediocre"] = (
                    f"采用常规工艺执行{node_name}，按既有验收条款与班组检查机制落地。"
                )
                mediocre = str(content["operation_desc_mediocre"])
                changed += 1

            desc = str(premium.get("desc") or "").strip()
            if not desc:
                premium["desc"] = f"针对{node_name}执行参数化控制与过程留痕。"
                desc = str(premium["desc"])
                changed += 1

            safety_level = str(node.get("safety_level") or "").strip().lower()
            if safety_level not in {"critical", "high", "medium", "low"}:
                node["safety_level"] = _detect_safety_level(node_name, f"{desc} {mediocre}")
                changed += 1
            safety_level = str(node.get("safety_level") or "medium").lower()

            if not isinstance(node.get("applicable_conditions"), dict) or not node.get("applicable_conditions"):
                node["applicable_conditions"] = _build_default_conditions()
                changed += 1

            if not isinstance(node.get("resource_requirements"), dict) or not node.get("resource_requirements"):
                node["resource_requirements"] = _build_default_resources(safety_level)
                changed += 1

            if str(node.get("source_hierarchy") or "").strip() not in {"答疑文件", "设计图纸", "国标", "行标", "企标"}:
                node["source_hierarchy"] = "企标"
                changed += 1

            if not isinstance(node.get("reference_standard"), list) or not node.get("reference_standard"):
                node["reference_standard"] = _build_reference_standards(node_name)
                changed += 1

            if node.get("is_auto_generated") is not True:
                node["is_auto_generated"] = True
                changed += 1

            strategy = premium.get("bid_response_strategy")
            if not isinstance(strategy, dict) or not strategy:
                premium["bid_response_strategy"] = _build_default_strategy(node_name, desc or mediocre, path.stem)
                changed += 1
            else:
                if not _safe_list(strategy.get("trigger_keywords")):
                    strategy["trigger_keywords"] = _build_default_strategy(node_name, desc or mediocre, path.stem)["trigger_keywords"]
                    changed += 1
                if not str(strategy.get("response_template") or "").strip():
                    strategy["response_template"] = _build_default_strategy(node_name, desc or mediocre, path.stem)["response_template"]
                    changed += 1

            shield = premium.get("competitor_shield")
            if not isinstance(shield, dict) or not shield:
                premium["competitor_shield"] = _build_default_shield(node_name)
                changed += 1
            else:
                defaults = _build_default_shield(node_name)
                for key, value in defaults.items():
                    if not str(shield.get(key) or "").strip():
                        shield[key] = value
                        changed += 1

            booster = premium.get("qt_score_booster")
            if not isinstance(booster, dict) or not booster:
                premium["qt_score_booster"] = _build_default_booster(safety_level)
                changed += 1
            else:
                if not _safe_list(booster.get("policy_alignment")):
                    booster["policy_alignment"] = _build_default_booster(safety_level)["policy_alignment"]
                    changed += 1
                if not str(booster.get("score_weight") or "").strip():
                    booster["score_weight"] = _build_default_booster(safety_level)["score_weight"]
                    changed += 1

            if _ensure_formula(node, premium):
                changed += 1

            # Build relation hints/edges with neighboring nodes across the whole file.
            prev_id = node_ids[i - 1] if i > 0 else None
            next_id = node_ids[i + 1] if i + 1 < len(node_ids) else None

            formula_expression = str(node.get("formula_expression") or "").strip()
            numeric_sources = node.get("numeric_sources")
            if not isinstance(numeric_sources, list) or not numeric_sources:
                node["numeric_sources"] = _build_default_numeric_sources(
                    node_name=node_name,
                    desc=f"{desc} {mediocre}",
                    formula_expression=formula_expression,
                    safety_level=safety_level,
                )
                changed += 1
            elif not any(isinstance(it, dict) and any(v not in (None, "", [], {}) for v in it.values()) for it in numeric_sources):
                node["numeric_sources"] = _build_default_numeric_sources(
                    node_name=node_name,
                    desc=f"{desc} {mediocre}",
                    formula_expression=formula_expression,
                    safety_level=safety_level,
                )
                changed += 1

            quant_indices = node.get("quantitative_indices")
            if not isinstance(quant_indices, dict) or not quant_indices:
                node["quantitative_indices"] = _build_default_quantitative_indices(safety_level, node.get("resource_requirements") or {})
                changed += 1
            else:
                defaults = _build_default_quantitative_indices(safety_level, node.get("resource_requirements") or {})
                for key, val in defaults.items():
                    if key not in quant_indices:
                        quant_indices[key] = val
                        changed += 1
                    else:
                        quant_indices[key] = round(_clamp_01(quant_indices.get(key), val), 4)

            schedule_constraints = node.get("schedule_constraints")
            if not isinstance(schedule_constraints, dict) or not schedule_constraints:
                node["schedule_constraints"] = _build_default_schedule_constraints(
                    node_id=node_id,
                    prev_id=prev_id,
                    next_id=next_id,
                )
                changed += 1
            else:
                if not isinstance(schedule_constraints.get("critical_path_hint"), list) or not schedule_constraints.get("critical_path_hint"):
                    schedule_constraints["critical_path_hint"] = _build_default_schedule_constraints(
                        node_id=node_id,
                        prev_id=prev_id,
                        next_id=next_id,
                    )["critical_path_hint"]
                    changed += 1
                if not str(schedule_constraints.get("min_process_interval_days") or "").strip():
                    schedule_constraints["min_process_interval_days"] = 1
                    changed += 1

            if len(node_ids) > 1:
                current_requires = _as_string_list(node.get("requires"))
                if (not current_requires) or current_requires == ["通用前置条件"]:
                    node["requires"] = [prev_id] if prev_id else []
                    changed += 1

                current_mitigates = _as_string_list(node.get("mitigates"))
                if (not current_mitigates) or current_mitigates == ["关键风险事件"]:
                    node["mitigates"] = [next_id] if next_id else ([prev_id] if prev_id else [])
                    changed += 1

                current_conflicts = _as_string_list(node.get("conflicts_with"))
                if (not current_conflicts) or current_conflicts == ["不兼容工艺方案"]:
                    if next_id:
                        node["conflicts_with"] = [next_id]
                    elif prev_id:
                        node["conflicts_with"] = [prev_id]
                    else:
                        node["conflicts_with"] = []
                    changed += 1
            else:
                if "requires" not in node:
                    node["requires"] = ["通用前置条件"]
                    changed += 1
                if "mitigates" not in node:
                    node["mitigates"] = ["关键风险事件"]
                    changed += 1
                if "conflicts_with" not in node:
                    node["conflicts_with"] = ["不兼容工艺方案"]
                    changed += 1

            if node.get("node_id") != node_id:
                node["node_id"] = node_id
                changed += 1

            if isinstance(node.get("numeric_sources"), list) and node.get("numeric_sources"):
                numeric_sources_count += 1
            if isinstance(node.get("quantitative_indices"), dict) and node.get("quantitative_indices"):
                indices_count += 1
            if isinstance(node.get("schedule_constraints"), dict) and node.get("schedule_constraints"):
                schedule_constraints_count += 1
            if (
                isinstance(node.get("numeric_sources"), list)
                and node.get("numeric_sources")
                and isinstance(node.get("quantitative_indices"), dict)
                and node.get("quantitative_indices")
                and isinstance(node.get("schedule_constraints"), dict)
                and node.get("schedule_constraints")
            ):
                quant_ready_count += 1

    if changed > 0:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "nodes": node_count,
        "changes": changed,
        "updated": bool(changed > 0),
        "quant_ready_nodes": quant_ready_count,
        "numeric_sources_nodes": numeric_sources_count,
        "indices_nodes": indices_count,
        "schedule_constraints_nodes": schedule_constraints_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch enrich tactical knowledge graph JSON files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="Glob pattern for KG json files")
    parser.add_argument("--no-backup", action="store_true", help="Disable backup before overwrite")
    parser.add_argument("--summary-out", default="", help="Optional summary markdown output path")
    args = parser.parse_args()

    kg_root = Path(args.kg_root).expanduser().resolve()
    if not kg_root.exists():
        raise FileNotFoundError(f"KG root not found: {kg_root}")

    files = sorted(kg_root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {kg_root}/{args.pattern}")

    backup_dir: Path | None = None
    if not args.no_backup:
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        backup_dir = Path.cwd() / "build" / f"kg_enrich_backup_{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, backup_dir / f.name)

    rows: List[Dict[str, Any]] = []
    for f in files:
        rows.append(enrich_file(f))

    updated = [r for r in rows if r["updated"]]
    total_nodes = sum(int(r["nodes"]) for r in rows)
    total_changes = sum(int(r["changes"]) for r in rows)
    total_quant_ready = sum(int(r.get("quant_ready_nodes") or 0) for r in rows)
    total_numeric_sources = sum(int(r.get("numeric_sources_nodes") or 0) for r in rows)
    total_indices = sum(int(r.get("indices_nodes") or 0) for r in rows)
    total_schedule_constraints = sum(int(r.get("schedule_constraints_nodes") or 0) for r in rows)

    print(f"files_total={len(files)}")
    print(f"files_updated={len(updated)}")
    print(f"nodes_total={total_nodes}")
    print(f"changes_total={total_changes}")
    print(f"quant_ready_nodes={total_quant_ready}")
    print(f"numeric_sources_nodes={total_numeric_sources}")
    print(f"indices_nodes={total_indices}")
    print(f"schedule_constraints_nodes={total_schedule_constraints}")
    if backup_dir:
        print(f"backup_dir={backup_dir}")

    summary_out = Path(args.summary_out).expanduser().resolve() if args.summary_out else (Path.cwd() / "build" / "KG_Enrichment_Summary.md")
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# KG Enrichment Summary")
    lines.append("")
    lines.append(f"- KG Root: {kg_root}")
    lines.append(f"- Files Total: {len(files)}")
    lines.append(f"- Files Updated: {len(updated)}")
    lines.append(f"- Nodes Total: {total_nodes}")
    lines.append(f"- Changes Total: {total_changes}")
    lines.append(f"- Quant Ready Nodes: {total_quant_ready}/{total_nodes}")
    lines.append(f"- Numeric Sources Coverage: {total_numeric_sources}/{total_nodes}")
    lines.append(f"- Quantitative Indices Coverage: {total_indices}/{total_nodes}")
    lines.append(f"- Schedule Constraints Coverage: {total_schedule_constraints}/{total_nodes}")
    if backup_dir:
        lines.append(f"- Backup Dir: {backup_dir}")
    lines.append("")
    lines.append("| File | Nodes | Changes | Quant Ready | Numeric Sources | Indices | Schedule Constraints | Updated |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        lines.append(
            f"| {r['file']} | {r['nodes']} | {r['changes']} | {r.get('quant_ready_nodes', 0)} "
            f"| {r.get('numeric_sources_nodes', 0)} | {r.get('indices_nodes', 0)} "
            f"| {r.get('schedule_constraints_nodes', 0)} | {r['updated']} |"
        )
    summary_out.write_text("\n".join(lines), encoding="utf-8")
    print(f"summary_out={summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
