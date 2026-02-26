#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.index_matrix_engine import DIMENSION_RULES

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_OUT_MD = Path("build/KG_Module4_Readiness_Report.md")
DEFAULT_OUT_JSON = Path("build/KG_Module4_Readiness_Report.json")

REQUIRED_ASSERTIONS = {"must_have_action", "must_have_parameter", "must_have_checker"}


def _iter_nodes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    out: List[Dict[str, Any]] = []
    for section in kg.values():
        if not isinstance(section, dict):
            continue
        nodes = section.get("nodes")
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if isinstance(node, dict):
                out.append(node)
    return out


def _check_root(raw: Dict[str, Any]) -> Dict[str, Any]:
    m4 = raw.get("module4_validation")
    if not isinstance(m4, dict):
        return {
            "ready": False,
            "missing": ["module4_validation"],
            "score_point_matrix_dims": [],
            "score_point_matrix_covered": 0,
        }

    missing: List[str] = []
    if not bool(m4.get("enabled")):
        missing.append("enabled")
    if not isinstance(m4.get("fail_fast_policy"), dict):
        missing.append("fail_fast_policy")
    if not isinstance(m4.get("auto_rewrite_policy"), dict):
        missing.append("auto_rewrite_policy")
    matrix = m4.get("score_point_matrix")
    if not isinstance(matrix, list) or not matrix:
        missing.append("score_point_matrix")
        dims: List[str] = []
    else:
        dims = []
        for item in matrix:
            if isinstance(item, dict):
                dim = str(item.get("dimension") or "").strip()
                if dim:
                    dims.append(dim)
    dims_uniq = sorted(set(dims))
    covered = sum(1 for dim in DIMENSION_RULES.keys() if dim in dims_uniq)
    if covered < len(DIMENSION_RULES):
        missing.append("score_point_matrix_dims")

    return {
        "ready": len(missing) == 0,
        "missing": missing,
        "score_point_matrix_dims": dims_uniq,
        "score_point_matrix_covered": covered,
    }


def _coerce_point(item: Any, *, index: int, fallback_dim: str = "质量") -> Dict[str, Any] | None:
    point = item
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                point = parsed
            else:
                point = {"description": text}
        else:
            point = {"description": text}

    if not isinstance(point, dict):
        return None

    dim = str(point.get("dimension") or fallback_dim).strip()
    if dim not in DIMENSION_RULES:
        dim = fallback_dim

    req = point.get("required_keywords")
    if not isinstance(req, list):
        req = point.get("keywords")
    req_keywords = [str(k).strip() for k in (req or []) if str(k).strip()]
    if not req_keywords:
        req_keywords = list(DIMENSION_RULES.get(dim, DIMENSION_RULES["质量"])[:6])

    return {
        "point_id": str(point.get("point_id") or f"{dim}-NODE-{index}"),
        "dimension": dim,
        "description": str(point.get("description") or f"{dim}评分点响应"),
        "required_keywords": req_keywords,
        "match_mode": str(point.get("match_mode") or "any"),
        "boolean_rule": str(point.get("boolean_rule") or "any_keyword_hit"),
    }


def _extract_scoring_points(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = node.get("scoring_points")
    fallback_dim = "质量"
    if isinstance(raw, dict):
        dim = str(raw.get("dimension") or "").strip()
        if dim in DIMENSION_RULES:
            fallback_dim = dim
        raw_points = raw.get("checkpoints")
        if not isinstance(raw_points, list):
            raw_points = raw.get("points")
    elif isinstance(raw, list):
        raw_points = raw
    else:
        raw_points = []

    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_points, start=1):
        point = _coerce_point(item, index=idx, fallback_dim=fallback_dim)
        if point is not None:
            out.append(point)
    return out


def _hooks_enabled(node: Dict[str, Any]) -> bool:
    hooks = node.get("fail_fast_hooks")
    if isinstance(hooks, dict):
        return bool(hooks.get("enabled"))
    if isinstance(hooks, list):
        return any(str(item or "").strip() for item in hooks)
    return False


def _check_node(node: Dict[str, Any]) -> bool:
    scoring_points = _extract_scoring_points(node)
    if not scoring_points:
        return False
    if not all(
        isinstance(p, dict) and isinstance(p.get("required_keywords"), list) and (p.get("required_keywords") or [])
        for p in scoring_points
    ):
        return False

    if not _hooks_enabled(node):
        return False

    rewrite = node.get("auto_rewrite")
    if not isinstance(rewrite, dict) or not bool(rewrite.get("enabled")):
        return False

    assertions = node.get("response_assertions")
    if not isinstance(assertions, list):
        return False
    actual = {str(x).strip() for x in assertions if str(x).strip()}
    if not REQUIRED_ASSERTIONS.issubset(actual):
        return False

    return True


def analyze_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    root_check = _check_root(raw)
    nodes = _iter_nodes(raw)
    node_ready = sum(1 for node in nodes if _check_node(node))
    node_total = len(nodes)

    node_coverage = (node_ready / max(1, node_total))
    overall_ready = bool(root_check["ready"] and node_ready == node_total)
    overall_score = (
        (1.0 if root_check["ready"] else 0.0) * 0.4
        + (root_check["score_point_matrix_covered"] / max(1, len(DIMENSION_RULES))) * 0.2
        + node_coverage * 0.4
    )
    return {
        "file": path.name,
        "path": str(path),
        "root_ready": bool(root_check["ready"]),
        "root_missing": root_check["missing"],
        "score_point_dims_covered": int(root_check["score_point_matrix_covered"]),
        "score_point_dims_total": len(DIMENSION_RULES),
        "node_ready": int(node_ready),
        "node_total": int(node_total),
        "node_coverage": round(node_coverage, 4),
        "overall_ready": overall_ready,
        "overall_score": round(overall_score, 4),
    }


def render_markdown(report: Dict[str, Any], out_path: Path) -> None:
    rows = report["files"]
    lines: List[str] = []
    lines.append("# KG Module4 Readiness Report")
    lines.append("")
    lines.append(f"- Generated At: {report['generated_at']}")
    lines.append(f"- KG Root: {report['kg_root']}")
    lines.append(f"- Files Total: {report['summary']['files_total']}")
    lines.append(f"- Fully Ready Files: {report['summary']['full_ready_files']}")
    lines.append(f"- Avg Score: {report['summary']['avg_score']}")
    lines.append(f"- Avg Node Coverage: {report['summary']['avg_node_coverage']}")
    lines.append("")
    lines.append("| File | Root Ready | Score Dims | Node Coverage | Overall Ready | Score |")
    lines.append("|---|---|---:|---:|---|---:|")
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['root_ready']} | {row['score_point_dims_covered']}/{row['score_point_dims_total']} "
            f"| {row['node_ready']}/{row['node_total']} ({row['node_coverage']:.2f}) "
            f"| {row['overall_ready']} | {row['overall_score']:.2f} |"
        )

    weakest = sorted(rows, key=lambda x: float(x.get("overall_score") or 0.0))[:10]
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    lines.append("| File | Root Missing |")
    lines.append("|---|---|")
    for row in weakest:
        missing = "、".join(row["root_missing"]) if row["root_missing"] else "-"
        lines.append(f"| {row['file']} | {missing} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate module4 readiness report for all KG files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="KG file glob pattern")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="Markdown report output")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="JSON report output")
    args = parser.parse_args()

    root = Path(args.kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"KG root not found: {root}")
    files = sorted(root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {root}/{args.pattern}")

    rows = [analyze_file(path) for path in files]
    files_total = len(rows)
    full_ready = sum(1 for row in rows if row["overall_ready"])
    avg_score = round(sum(float(row["overall_score"]) for row in rows) / max(1, files_total), 4)
    avg_node_coverage = round(sum(float(row["node_coverage"]) for row in rows) / max(1, files_total), 4)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "kg_root": str(root),
        "summary": {
            "files_total": files_total,
            "full_ready_files": full_ready,
            "avg_score": avg_score,
            "avg_node_coverage": avg_node_coverage,
        },
        "files": rows,
    }

    out_json = Path(args.out_json).expanduser().resolve()
    out_md = Path(args.out_md).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    render_markdown(report, out_md)

    print(f"files_total={files_total}")
    print(f"full_ready_files={full_ready}")
    print(f"avg_score={avg_score}")
    print(f"report_json={out_json}")
    print(f"report_md={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
