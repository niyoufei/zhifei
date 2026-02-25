#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.index_matrix_engine import DIMENSION_RULES

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_SUMMARY = Path("build/KG_Module4_Fix_Summary.md")

EN_TAG_TO_DIM = {
    "quality": "质量",
    "safety": "安全",
    "schedule": "进度",
    "progress": "进度",
    "environment": "环保",
    "env": "环保",
    "difficulty": "重难点",
    "hardpoint": "重难点",
    "penalty": "扣分点",
}

DIMENSION_CHECKER = {
    "质量": "质量员",
    "安全": "安全员",
    "进度": "施工员",
    "环保": "环保员",
    "重难点": "总工",
    "扣分点": "项目经理",
}


def _iter_nodes(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = root.get("knowledge_database")
    if not isinstance(kg, dict):
        root["knowledge_database"] = {"module4_patch": {"nodes": []}}
        kg = root["knowledge_database"]

    out: List[Dict[str, Any]] = []
    for sec in kg.values():
        if not isinstance(sec, dict):
            continue
        arr = sec.get("nodes")
        if not isinstance(arr, list):
            continue
        for node in arr:
            if isinstance(node, dict):
                out.append(node)
    return out


def _normalize_tag(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _node_text(node: Dict[str, Any]) -> str:
    return json.dumps(node, ensure_ascii=False)


def _detect_dimensions(node: Dict[str, Any]) -> List[str]:
    dims: List[str] = []
    tags = node.get("qt_tag")
    if isinstance(tags, list):
        for tag in tags:
            txt = str(tag).strip()
            if txt in DIMENSION_RULES and txt not in dims:
                dims.append(txt)
                continue
            mapped = EN_TAG_TO_DIM.get(_normalize_tag(txt))
            if mapped and mapped not in dims:
                dims.append(mapped)

    text = _node_text(node)
    for dim, seeds in DIMENSION_RULES.items():
        if dim in dims:
            continue
        if any(seed in text for seed in seeds):
            dims.append(dim)
    if not dims:
        dims.append("质量")
    return dims


def _build_root_module4() -> Dict[str, Any]:
    score_matrix: List[Dict[str, Any]] = []
    for idx, (dim, seeds) in enumerate(DIMENSION_RULES.items(), start=1):
        score_matrix.append(
            {
                "point_id": f"{dim}-SP-{idx:02d}",
                "dimension": dim,
                "description": f"{dim}评分点响应判定",
                "required_keywords": list(seeds[:8]),
                "match_mode": "any",
                "boolean_rule": "any_keyword_hit",
            }
        )
    return {
        "enabled": True,
        "version": "v2.0",
        "score_point_matrix": score_matrix,
        "fail_fast_policy": {
            "enabled": True,
            "trigger_condition": "any_score_point_false",
            "action": "raise_exception_and_abort_current_pass",
            "cache_policy": "clear_failed_dimension_cache",
            "max_retry": 3,
        },
        "auto_rewrite_policy": {
            "enabled": True,
            "strategy": "targeted_dimension_rewrite",
            "required_syntax": "Action + Parameter + Checker",
            "template": "执行{dimension}控制，参数阈值=95%，检查频次=2次/班，由{checker}复核。",
        },
    }


def _merge_root_module4(target: Dict[str, Any], defaults: Dict[str, Any]) -> bool:
    changed = False
    if not isinstance(target.get("module4_validation"), dict):
        target["module4_validation"] = defaults
        return True
    current = target["module4_validation"]
    for key in ("enabled", "version", "score_point_matrix", "fail_fast_policy", "auto_rewrite_policy"):
        if key not in current:
            current[key] = defaults[key]
            changed = True

    if not isinstance(current.get("score_point_matrix"), list) or len(current.get("score_point_matrix")) < len(DIMENSION_RULES):
        current["score_point_matrix"] = defaults["score_point_matrix"]
        changed = True
    if not isinstance(current.get("fail_fast_policy"), dict):
        current["fail_fast_policy"] = defaults["fail_fast_policy"]
        changed = True
    if not isinstance(current.get("auto_rewrite_policy"), dict):
        current["auto_rewrite_policy"] = defaults["auto_rewrite_policy"]
        changed = True
    return changed


def _ensure_node_module4(node: Dict[str, Any]) -> bool:
    changed = False
    dims = _detect_dimensions(node)

    scoring_points = node.get("scoring_points")
    if not isinstance(scoring_points, list):
        scoring_points = []
    existing_dim_points: Set[str] = set()
    for point in scoring_points:
        if not isinstance(point, dict):
            continue
        dim = str(point.get("dimension") or "").strip()
        if dim:
            existing_dim_points.add(dim)
        if "match_mode" not in point:
            point["match_mode"] = "any"
            changed = True
        if "boolean_rule" not in point:
            point["boolean_rule"] = "any_keyword_hit"
            changed = True
        if "required_keywords" not in point or not isinstance(point.get("required_keywords"), list):
            dim_infer = dim if dim in DIMENSION_RULES else "质量"
            point["required_keywords"] = list(DIMENSION_RULES[dim_infer][:6])
            changed = True

    for dim in dims:
        if dim in existing_dim_points:
            continue
        scoring_points.append(
            {
                "point_id": f"{dim}-NODE",
                "dimension": dim,
                "description": f"{dim}评分点响应",
                "required_keywords": list(DIMENSION_RULES[dim][:6]),
                "match_mode": "any",
                "boolean_rule": "any_keyword_hit",
            }
        )
        changed = True

    if node.get("scoring_points") != scoring_points:
        node["scoring_points"] = scoring_points
        changed = True

    if not isinstance(node.get("fail_fast_hooks"), dict):
        node["fail_fast_hooks"] = {
            "enabled": True,
            "on_missing_response": "raise_exception_and_retry",
            "cache_policy": "clear_failed_dimension_cache",
            "max_retry": 3,
        }
        changed = True
    else:
        hooks = node["fail_fast_hooks"]
        if "enabled" not in hooks:
            hooks["enabled"] = True
            changed = True
        if "on_missing_response" not in hooks:
            hooks["on_missing_response"] = "raise_exception_and_retry"
            changed = True
        if "cache_policy" not in hooks:
            hooks["cache_policy"] = "clear_failed_dimension_cache"
            changed = True
        if "max_retry" not in hooks:
            hooks["max_retry"] = 3
            changed = True

    if not isinstance(node.get("auto_rewrite"), dict):
        checker = DIMENSION_CHECKER.get(dims[0], "专业工程师")
        node["auto_rewrite"] = {
            "enabled": True,
            "strategy": "targeted_dimension_rewrite",
            "template": f"执行{dims[0]}控制，参数阈值=95%，检查频次=2次/班，由{checker}复核。",
        }
        changed = True
    else:
        rewrite = node["auto_rewrite"]
        if "enabled" not in rewrite:
            rewrite["enabled"] = True
            changed = True
        if "strategy" not in rewrite:
            rewrite["strategy"] = "targeted_dimension_rewrite"
            changed = True
        if "template" not in rewrite:
            checker = DIMENSION_CHECKER.get(dims[0], "专业工程师")
            rewrite["template"] = f"执行{dims[0]}控制，参数阈值=95%，检查频次=2次/班，由{checker}复核。"
            changed = True

    required_assertions = {"must_have_action", "must_have_parameter", "must_have_checker"}
    assertions = node.get("response_assertions")
    if not isinstance(assertions, list):
        node["response_assertions"] = sorted(required_assertions)
        changed = True
    else:
        normalized = {str(x).strip() for x in assertions if str(x).strip()}
        if not required_assertions.issubset(normalized):
            normalized.update(required_assertions)
            node["response_assertions"] = sorted(normalized)
            changed = True

    return changed


def fix_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = False

    if _merge_root_module4(raw, _build_root_module4()):
        changed = True

    nodes = _iter_nodes(raw)
    node_changed = 0
    for node in nodes:
        if _ensure_node_module4(node):
            node_changed += 1
            changed = True

    if changed:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "changed": changed,
        "node_total": len(nodes),
        "node_updated": node_changed,
    }


def render_summary(rows: List[Dict[str, Any]], out_path: Path) -> None:
    files_total = len(rows)
    files_changed = sum(1 for r in rows if r["changed"])
    node_total = sum(int(r["node_total"]) for r in rows)
    node_updated = sum(int(r["node_updated"]) for r in rows)

    lines: List[str] = []
    lines.append("# KG Module4 Auto-Fix Summary")
    lines.append("")
    lines.append(f"- Generated At: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}")
    lines.append(f"- Files Total: {files_total}")
    lines.append(f"- Files Changed: {files_changed}")
    lines.append(f"- Nodes Total: {node_total}")
    lines.append(f"- Nodes Updated: {node_updated}")
    lines.append("")
    lines.append("| File | Changed | Nodes | Nodes Updated |")
    lines.append("|---|---|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['changed']} | {row['node_total']} | {row['node_updated']} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-fix module4 fail-fast/rewrite metadata in KG files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="KG file glob pattern")
    parser.add_argument("--summary-out", default=str(DEFAULT_SUMMARY), help="Summary output path")
    args = parser.parse_args()

    root = Path(args.kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"KG root not found: {root}")
    files = sorted(root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {root}/{args.pattern}")

    rows = [fix_file(path) for path in files]
    summary_path = Path(args.summary_out).expanduser().resolve()
    render_summary(rows, summary_path)

    print(f"files_total={len(rows)}")
    print(f"files_changed={sum(1 for r in rows if r['changed'])}")
    print(f"summary_out={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
