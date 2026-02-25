#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.index_matrix_engine import DIMENSION_RULES
from backend.zhifei_autoplan.v2.quantitative_boq_engine import DEFAULT_RULE, PROCESS_RULES

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_SUMMARY = Path("build/KG_Module12_Fix_Summary.md")

DIMENSION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "质量": {"checker": "质量员", "param": "一次验收合格率≥95%", "safety": "medium"},
    "安全": {"checker": "安全员", "param": "隐患整改时限≤4h", "safety": "high"},
    "进度": {"checker": "施工员", "param": "关键工序日偏差≤1天", "safety": "medium"},
    "环保": {"checker": "环保员", "param": "PM10≤150ug/m3", "safety": "medium"},
    "重难点": {"checker": "总工", "param": "专项方案审批闭环100%", "safety": "high"},
    "扣分点": {"checker": "项目经理", "param": "评分项响应完整率100%", "safety": "medium"},
}


def _iter_nodes(root: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    kg = root.get("knowledge_database")
    if not isinstance(kg, dict):
        root["knowledge_database"] = {"module12_patch": {"nodes": []}}
        kg = root["knowledge_database"]

    for sec_name, sec_body in kg.items():
        if isinstance(sec_body, dict) and isinstance(sec_body.get("nodes"), list):
            return sec_body["nodes"], str(sec_name)

    kg["module12_patch"] = {"nodes": []}
    return kg["module12_patch"]["nodes"], "module12_patch"


def _node_text(node: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "node_id",
        "name",
        "title",
        "keywords",
        "qt_tag",
        "formula_expression",
        "numeric_sources",
        "quantitative_indices",
        "schedule_constraints",
        "process_catalog",
        "content",
    ):
        val = node.get(key)
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            parts.append(json.dumps(val, ensure_ascii=False))
        else:
            parts.append(str(val))
    return "\n".join(parts)


def _combined_text(nodes: Iterable[Dict[str, Any]]) -> str:
    return "\n".join(_node_text(node) for node in nodes if isinstance(node, dict))


def _existing_node_ids(nodes: List[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("node_id") or "").strip()
        if nid:
            out.add(nid)
    return out


def _detect_missing_dimensions(text: str) -> List[str]:
    missing: List[str] = []
    for dim, seeds in DIMENSION_RULES.items():
        if any(seed in text for seed in seeds):
            continue
        missing.append(dim)
    return missing


def _detect_missing_processes(text: str) -> List[Tuple[str, Tuple[str, ...]]]:
    missing: List[Tuple[str, Tuple[str, ...]]] = []
    for rule in PROCESS_RULES:
        if any(keyword in text for keyword in rule.keywords):
            continue
        missing.append((rule.process_name, rule.keywords))
    if (DEFAULT_RULE.process_name not in text) and (not any(keyword in text for keyword in DEFAULT_RULE.keywords)):
        missing.append((DEFAULT_RULE.process_name, DEFAULT_RULE.keywords))
    return missing


def _dimension_patch_node(*, file_stem: str, dim: str, seeds: List[str]) -> Dict[str, Any]:
    defaults = DIMENSION_DEFAULTS[dim]
    checker = str(defaults["checker"])
    param = str(defaults["param"])
    safety = str(defaults["safety"])
    node_id = f"{file_stem}-M1-{dim}"
    keywords = [dim] + list(seeds[:10])
    return {
        "node_id": node_id,
        "name": f"{dim}响应控制补强节点",
        "qt_tag": [dim, "module1_patch"],
        "keywords": keywords,
        "source_hierarchy": "企标",
        "is_auto_generated": True,
        "reference_standard": [
            "GB 50300-2013 建筑工程施工质量验收统一标准",
            "JGJ 59-2011 建筑施工安全检查标准",
            "GB/T 50326-2017 建设工程项目管理规范",
        ],
        "applicable_conditions": {
            "climate": "常规施工气候",
            "site_constraints": "按现场审批流程执行",
        },
        "resource_requirements": {
            "manpower": {"crew_size": "8-12人/班", "checker_role": checker},
            "inspection_frequency": "2次/班",
        },
        "safety_level": safety,
        "formula_expression": "quantity / max(productivity_per_day, 1)",
        "formula_variables": ["quantity", "productivity_per_day"],
        "numeric_sources": [
            {"parameter": "inspection_frequency", "value": "2", "unit": "次/班", "source_text": "module1_patch"},
            {"parameter": "response_limit", "value": "4", "unit": "h", "source_text": "module1_patch"},
        ],
        "quantitative_indices": {
            "duration_index": 0.6,
            "risk_index": 0.7 if dim in {"安全", "重难点"} else 0.55,
            "resource_density_index": 0.55,
            "complexity_index": 0.6,
        },
        "schedule_constraints": {
            "critical_path_hint": ["测量放线", "基础工程", "主体结构"],
            "min_process_interval_days": 1,
        },
        "content": {
            "operation_desc_mediocre": f"按常规流程执行{dim}控制。",
            "operation_desc_premium": {
                "desc": f"执行{dim}闭环控制，参数={param}，每班检查2次，由{checker}复核。"
            },
        },
    }


def _process_patch_node(
    *,
    file_stem: str,
    missing_processes: List[Tuple[str, Tuple[str, ...]]],
) -> Dict[str, Any]:
    node_id = f"{file_stem}-M2-PROC-MAP"
    catalog: List[Dict[str, Any]] = []
    keyword_union: List[str] = []
    for process_name, keywords in missing_processes:
        kws = [str(k) for k in keywords]
        catalog.append(
            {
                "process": process_name,
                "keywords": kws,
                "resources": ["专业班组", "关键机械"],
                "min_interval_days": 1,
            }
        )
        keyword_union.extend(kws)
        keyword_union.append(process_name)

    critical_path = [item["process"] for item in catalog][:8]
    return {
        "node_id": node_id,
        "name": "清单-工序-资源映射补强节点",
        "qt_tag": ["module2_patch", "process_mapping"],
        "keywords": list(dict.fromkeys(keyword_union))[:60],
        "process_catalog": catalog,
        "source_hierarchy": "企标",
        "is_auto_generated": True,
        "reference_standard": [
            "GB/T 50326-2017 建设工程项目管理规范",
            "GB 50202-2018 建筑地基基础工程施工质量验收标准",
        ],
        "applicable_conditions": {
            "construction_window": "按总控网络计划执行",
        },
        "resource_requirements": {
            "manpower": {"crew_size": "10人/班", "checker_role": "施工员"},
            "equipment": {"primary": ["主机械1套"], "backup": ["备用机械1套"]},
        },
        "safety_level": "medium",
        "formula_expression": "quantity / max(productivity_per_day, 1)",
        "formula_variables": ["quantity", "productivity_per_day"],
        "numeric_sources": [
            {"parameter": "min_process_interval_days", "value": "1", "unit": "天", "source_text": "module2_patch"},
            {"parameter": "inspection_frequency", "value": "2", "unit": "次/班", "source_text": "module2_patch"},
        ],
        "quantitative_indices": {
            "duration_index": 0.62,
            "risk_index": 0.56,
            "resource_density_index": 0.6,
            "complexity_index": 0.59,
        },
        "schedule_constraints": {
            "critical_path_hint": critical_path,
            "min_process_interval_days": 1,
        },
        "content": {
            "operation_desc_mediocre": "采用通用工序组织。",
            "operation_desc_premium": {
                "desc": "执行清单-工序-资源三维映射，最小工序间隔=1天，由施工员复核。"
            },
        },
    }


def _upsert_process_patch(
    *,
    nodes: List[Dict[str, Any]],
    file_stem: str,
    missing_processes: List[Tuple[str, Tuple[str, ...]]],
) -> bool:
    if not missing_processes:
        return False
    target_id = f"{file_stem}-M2-PROC-MAP"
    patch = _process_patch_node(file_stem=file_stem, missing_processes=missing_processes)

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        if str(node.get("node_id") or "").strip() == target_id:
            current_catalog = node.get("process_catalog")
            if isinstance(current_catalog, list):
                existing = {str(item.get("process") or "").strip() for item in current_catalog if isinstance(item, dict)}
            else:
                existing = set()
            missing_names = [name for name, _ in missing_processes if name not in existing]
            if not missing_names:
                return False
            node.update(patch)
            nodes[idx] = node
            return True

    nodes.append(patch)
    return True


def fix_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes, _section = _iter_nodes(raw)
    file_stem = path.stem
    node_ids = _existing_node_ids(nodes)

    text = _combined_text(nodes)
    missing_dims = _detect_missing_dimensions(text)
    missing_processes = _detect_missing_processes(text)

    added_dim_nodes = 0
    for dim in missing_dims:
        node_id = f"{file_stem}-M1-{dim}"
        if node_id in node_ids:
            continue
        patch = _dimension_patch_node(file_stem=file_stem, dim=dim, seeds=DIMENSION_RULES[dim])
        nodes.append(patch)
        node_ids.add(node_id)
        added_dim_nodes += 1

    process_patch_updated = _upsert_process_patch(nodes=nodes, file_stem=file_stem, missing_processes=missing_processes)
    changed = bool(added_dim_nodes > 0 or process_patch_updated)

    # second pass status
    new_text = _combined_text(nodes)
    remain_dims = _detect_missing_dimensions(new_text)
    remain_processes = _detect_missing_processes(new_text)

    if changed:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "changed": changed,
        "added_dim_nodes": added_dim_nodes,
        "process_patch_updated": bool(process_patch_updated),
        "remaining_missing_dims": remain_dims,
        "remaining_missing_processes": [name for name, _ in remain_processes],
    }


def _render_summary(rows: List[Dict[str, Any]], out_path: Path) -> None:
    files_total = len(rows)
    files_changed = sum(1 for r in rows if r["changed"])
    dim_nodes_total = sum(int(r.get("added_dim_nodes") or 0) for r in rows)
    process_patch_total = sum(1 for r in rows if r.get("process_patch_updated"))
    full_ready = sum(
        1
        for r in rows
        if len(r.get("remaining_missing_dims") or []) == 0 and len(r.get("remaining_missing_processes") or []) == 0
    )

    lines: List[str] = []
    lines.append("# KG Module1/2 Auto-Fix Summary")
    lines.append("")
    lines.append(f"- Generated At: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}")
    lines.append(f"- Files Total: {files_total}")
    lines.append(f"- Files Changed: {files_changed}")
    lines.append(f"- Added Dimension Patch Nodes: {dim_nodes_total}")
    lines.append(f"- Process Patch Updated Files: {process_patch_total}")
    lines.append(f"- Full Ready Files After Fix: {full_ready}/{files_total}")
    lines.append("")
    lines.append("| File | Changed | Added Dim Nodes | Process Patch | Remaining Missing Dims | Remaining Missing Processes |")
    lines.append("|---|---|---:|---|---|---|")
    for r in rows:
        miss_dims = "、".join(r["remaining_missing_dims"]) if r["remaining_missing_dims"] else "-"
        miss_proc = "、".join(r["remaining_missing_processes"]) if r["remaining_missing_processes"] else "-"
        lines.append(
            f"| {r['file']} | {r['changed']} | {r['added_dim_nodes']} | {r['process_patch_updated']} | {miss_dims} | {miss_proc} |"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-fix module1/2 gaps for all KG files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="KG file glob pattern")
    parser.add_argument("--summary-out", default=str(DEFAULT_SUMMARY), help="Summary markdown output path")
    args = parser.parse_args()

    root = Path(args.kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"KG root not found: {root}")

    files = sorted(root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {root}/{args.pattern}")

    rows = [fix_file(path) for path in files]

    summary_path = Path(args.summary_out).expanduser().resolve()
    _render_summary(rows, summary_path)

    files_changed = sum(1 for r in rows if r["changed"])
    print(f"files_total={len(rows)}")
    print(f"files_changed={files_changed}")
    print(f"summary_out={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
