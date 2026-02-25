#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_OUT_MD = Path("build/KG_Gemini_Enablement_Report.md")
DEFAULT_OUT_JSON = Path("build/KG_Gemini_Enablement_Report.json")

DEFAULT_FORMULA = "quantity / max(productivity_per_day, 1)"


def _iter_nodes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        return out
    for sec in kg.values():
        if not isinstance(sec, dict):
            continue
        nodes = sec.get("nodes")
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if isinstance(node, dict):
                out.append(node)
    return out


def analyze_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes = _iter_nodes(raw)
    total = len(nodes)
    formula_nodes = 0
    non_default_formula = 0
    activation_ok = 0
    desc_values: List[str] = []
    source_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    score_values: List[float] = []

    for node in nodes:
        node_type = str(node.get("node_type") or "")
        if node_type == "FormulaNode":
            formula_nodes += 1
        expr = str(node.get("formula_expression") or "").strip()
        if expr and expr != DEFAULT_FORMULA:
            non_default_formula += 1

        content = node.get("content")
        env = content.get("environment_sensing") if isinstance(content, dict) else None
        if isinstance(env, dict) and str(env.get("activation_signal") or "").strip():
            activation_ok += 1

        desc = ""
        if isinstance(content, dict):
            premium = content.get("operation_desc_premium")
            if isinstance(premium, dict):
                desc = str(premium.get("desc") or "").strip()
        if desc:
            desc_values.append(desc)

        source_counter[str(node.get("source_hierarchy") or "missing")] += 1
        domain_counter[str(node.get("professional_domain") or "missing")] += 1
        score_values.append(float(node.get("gemini_usefulness_score") or 0.0))

    unique_desc = len(set(desc_values))
    activation_rate = activation_ok / max(1, total)
    formula_node_rate = formula_nodes / max(1, total)
    non_default_formula_rate = non_default_formula / max(1, total)
    avg_score = sum(score_values) / max(1, len(score_values))

    root_cfg = raw.get("gemini_kg_enablement")
    root_ready = bool(isinstance(root_cfg, dict) and root_cfg.get("enabled"))
    overall_ready = bool(
        root_ready
        and activation_rate >= 0.9
        and formula_node_rate >= 0.08
        and non_default_formula_rate >= 0.7
        and avg_score >= 55
    )
    overall_score = (
        (0.15 if root_ready else 0.0)
        + min(0.25, activation_rate * 0.25)
        + min(0.20, formula_node_rate * 2.0)
        + min(0.20, non_default_formula_rate * 0.25)
        + min(0.20, avg_score / 100.0 * 0.20)
    )

    return {
        "file": path.name,
        "path": str(path),
        "node_total": total,
        "formula_nodes": formula_nodes,
        "formula_node_rate": round(formula_node_rate, 4),
        "non_default_formula_rate": round(non_default_formula_rate, 4),
        "activation_rate": round(activation_rate, 4),
        "avg_gemini_usefulness_score": round(avg_score, 4),
        "unique_desc": unique_desc,
        "desc_total": len(desc_values),
        "source_distribution": dict(source_counter),
        "domain_distribution": dict(domain_counter),
        "root_ready": root_ready,
        "overall_ready": overall_ready,
        "overall_score": round(min(1.0, overall_score), 4),
    }


def render_markdown(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# KG Gemini Enablement Report")
    lines.append("")
    lines.append(f"- Generated At: {report['generated_at']}")
    lines.append(f"- KG Root: {report['kg_root']}")
    lines.append(f"- Files Total: {report['summary']['files_total']}")
    lines.append(f"- Ready Files: {report['summary']['ready_files']}")
    lines.append(f"- Avg Score: {report['summary']['avg_score']}")
    lines.append(f"- Avg Activation Rate: {report['summary']['avg_activation_rate']}")
    lines.append(f"- Avg Formula Node Rate: {report['summary']['avg_formula_node_rate']}")
    lines.append(f"- Avg Non-default Formula Rate: {report['summary']['avg_non_default_formula_rate']}")
    lines.append(f"- Avg Gemini Usefulness Score: {report['summary']['avg_gemini_usefulness_score']}")
    lines.append("")
    lines.append("| File | Nodes | Formula Rate | Non-default Formula | Activation | Avg Gemini Score | Ready | Score |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---:|")
    for row in report["files"]:
        lines.append(
            f"| {row['file']} | {row['node_total']} | {row['formula_node_rate']:.2f} | "
            f"{row['non_default_formula_rate']:.2f} | {row['activation_rate']:.2f} | "
            f"{row['avg_gemini_usefulness_score']:.1f} | {row['overall_ready']} | {row['overall_score']:.2f} |"
        )

    weakest = sorted(report["files"], key=lambda x: float(x.get("overall_score", 0.0)))[:10]
    lines.append("")
    lines.append("## Top Gaps")
    lines.append("")
    lines.append("| File | Key Gaps |")
    lines.append("|---|---|")
    for row in weakest:
        gaps: List[str] = []
        if row["activation_rate"] < 0.9:
            gaps.append("activation_signal覆盖不足")
        if row["formula_node_rate"] < 0.08:
            gaps.append("FormulaNode占比不足")
        if row["non_default_formula_rate"] < 0.7:
            gaps.append("公式仍偏模板化")
        if row["avg_gemini_usefulness_score"] < 55:
            gaps.append("Gemini可用性得分偏低")
        lines.append(f"| {row['file']} | {'；'.join(gaps) if gaps else '-'} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Gemini enablement quality report for all KG files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="KG file glob pattern")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="Markdown report output path")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="JSON report output path")
    args = parser.parse_args()

    root = Path(args.kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"KG root not found: {root}")
    files = sorted(root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {root}/{args.pattern}")

    rows = [analyze_file(path) for path in files]
    files_total = len(rows)
    ready_files = sum(1 for row in rows if row["overall_ready"])

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "kg_root": str(root),
        "summary": {
            "files_total": files_total,
            "ready_files": ready_files,
            "avg_score": round(sum(float(r["overall_score"]) for r in rows) / max(1, files_total), 4),
            "avg_activation_rate": round(sum(float(r["activation_rate"]) for r in rows) / max(1, files_total), 4),
            "avg_formula_node_rate": round(sum(float(r["formula_node_rate"]) for r in rows) / max(1, files_total), 4),
            "avg_non_default_formula_rate": round(
                sum(float(r["non_default_formula_rate"]) for r in rows) / max(1, files_total), 4
            ),
            "avg_gemini_usefulness_score": round(
                sum(float(r["avg_gemini_usefulness_score"]) for r in rows) / max(1, files_total), 4
            ),
            "median_gemini_usefulness_score": round(
                statistics.median([float(r["avg_gemini_usefulness_score"]) for r in rows]), 4
            ),
        },
        "files": rows,
    }

    out_json = Path(args.out_json).expanduser().resolve()
    out_md = Path(args.out_md).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    render_markdown(report, out_md)

    print(f"files_total={files_total}")
    print(f"ready_files={ready_files}")
    print(f"avg_score={report['summary']['avg_score']}")
    print(f"report_json={out_json}")
    print(f"report_md={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
