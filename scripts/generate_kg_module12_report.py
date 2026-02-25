#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.v2.index_matrix_engine import DIMENSION_RULES
from backend.zhifei_autoplan.v2.quantitative_boq_engine import DEFAULT_RULE, PROCESS_RULES, QuantitativeBoQEngine

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_BOQ = Path("/Users/youfeini/Desktop/文档生成系统/01_真实项目测试/工程量清单/1.工程量清单汇总表.pdf")
DEFAULT_OUT_MD = Path("build/KG_Module12_Adaptation_Report.md")
DEFAULT_OUT_JSON = Path("build/KG_Module12_Adaptation_Report.json")
KG_GLOB = "ZF-KG-*.json"


def _extract_tokens(text: str) -> List[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,16}|[A-Za-z][A-Za-z0-9_\-./]{1,24}|\d+(?:\.\d+)?", str(text or ""))
    out: List[str] = []
    seen = set()
    for part in parts:
        term = str(part).strip().lower()
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _iter_nodes(raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    nodes: List[Dict[str, Any]] = []
    for section in kg.values():
        if not isinstance(section, dict):
            continue
        arr = section.get("nodes")
        if not isinstance(arr, list):
            continue
        for node in arr:
            if isinstance(node, dict):
                nodes.append(node)
    return nodes


def _node_text(node: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "node_id",
        "id",
        "name",
        "title",
        "domain",
        "category",
        "qt_tag",
        "keywords",
        "trigger_keywords",
        "formula_expression",
        "numeric_sources",
        "quantitative_indices",
        "schedule_constraints",
    ):
        value = node.get(key)
        if value is not None:
            parts.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
    content = node.get("content")
    if content is not None:
        parts.append(json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content))
    return "\n".join(parts)


def _split_code_hierarchy(code: str) -> Tuple[str, str]:
    raw = str(code or "").strip()
    if not raw:
        return "", ""
    if any(sep in raw for sep in (".", "-", "_", "/")):
        parts = [p for p in re.split(r"[.\-_/]+", raw) if p]
        if len(parts) == 1:
            return parts[0], parts[0]
        return parts[0], ".".join(parts[:2])
    compact = re.sub(r"[^0-9A-Za-z]+", "", raw)
    if compact.isdigit() and len(compact) >= 4:
        return compact[:2], compact[:4]
    if len(compact) >= 2:
        return compact[:2], compact[:4] if len(compact) >= 4 else compact[:2]
    return compact, compact


async def _build_boq_baseline(boq_path: Path) -> Dict[str, Any]:
    parser = BoQParser()
    items, _stats = await parser.parse(str(boq_path))
    item_dicts = [item.model_dump() for item in items]

    engine = QuantitativeBoQEngine()
    process_counts: Counter[str] = Counter()
    chapter_process: Dict[str, Counter[str]] = {}

    for item in item_dicts:
        name = str(item.get("name") or "")
        process = engine._pick_rule(name).process_name  # noqa: SLF001
        process_counts[process] += 1
        chapter_id, _ = _split_code_hierarchy(str(item.get("boq_code") or ""))
        chapter_id = chapter_id or "UNSPEC"
        if chapter_id not in chapter_process:
            chapter_process[chapter_id] = Counter()
        chapter_process[chapter_id][process] += 1

    chapter_dominant: Dict[str, str] = {}
    for chapter_id, counter in chapter_process.items():
        chapter_dominant[chapter_id] = counter.most_common(1)[0][0]

    return {
        "boq_path": str(boq_path),
        "total_items": len(item_dicts),
        "required_process_counts": dict(process_counts),
        "chapter_dominant_process": chapter_dominant,
        "chapter_count": len(chapter_dominant),
    }


def _analyze_file(path: Path, boq_baseline: Dict[str, Any]) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes = list(_iter_nodes(raw))

    combined_parts: List[str] = []
    dimension_hits: Dict[str, List[str]] = {dim: [] for dim in DIMENSION_RULES.keys()}
    resource_nodes = 0
    formula_nodes = 0
    schedule_nodes = 0

    for node in nodes:
        text = _node_text(node)
        combined_parts.append(text)
        if isinstance(node.get("resource_requirements"), dict) and node.get("resource_requirements"):
            resource_nodes += 1
        if str(node.get("formula_expression") or "").strip():
            formula_nodes += 1
        if isinstance(node.get("schedule_constraints"), dict) and node.get("schedule_constraints"):
            schedule_nodes += 1

        for dim, seeds in DIMENSION_RULES.items():
            for seed in seeds:
                if seed in text and seed not in dimension_hits[dim]:
                    dimension_hits[dim].append(seed)

    combined_text = "\n".join(combined_parts)
    supported_processes = set()
    for rule in PROCESS_RULES:
        if any(keyword in combined_text for keyword in rule.keywords):
            supported_processes.add(rule.process_name)
    if (DEFAULT_RULE.process_name in combined_text) or any(keyword in combined_text for keyword in DEFAULT_RULE.keywords):
        supported_processes.add(DEFAULT_RULE.process_name)
    if not supported_processes:
        supported_processes.add(DEFAULT_RULE.process_name)

    total_dims = len(DIMENSION_RULES)
    covered_dims = [dim for dim, vals in dimension_hits.items() if vals]
    missing_dims = [dim for dim in DIMENSION_RULES.keys() if dim not in covered_dims]
    module1_coverage_rate = (len(covered_dims) / max(1, total_dims))

    process_counts = boq_baseline["required_process_counts"]
    total_items = int(boq_baseline["total_items"] or 0)
    process_item_hits = sum(count for process, count in process_counts.items() if process in supported_processes)
    process_hit_rate = (process_item_hits / max(1, total_items))

    chapter_dominant = boq_baseline["chapter_dominant_process"]
    chapter_hit_count = sum(1 for _chapter, process in chapter_dominant.items() if process in supported_processes)
    chapter_total = max(1, int(boq_baseline["chapter_count"] or 0))
    chapter_hit_rate = chapter_hit_count / chapter_total

    module2_score = process_hit_rate * 0.65 + chapter_hit_rate * 0.35
    overall_score = module1_coverage_rate * 0.45 + module2_score * 0.55

    missing_processes = [process for process in process_counts.keys() if process not in supported_processes]
    return {
        "file": path.name,
        "path": str(path),
        "node_count": len(nodes),
        "module1": {
            "dimension_coverage_rate": round(module1_coverage_rate, 4),
            "covered_dimensions": covered_dims,
            "missing_dimensions": missing_dims,
            "dimension_hits": {k: v[:10] for k, v in dimension_hits.items()},
            "ready": len(missing_dims) == 0,
            "qa_override_policy": "engine_level_active",
        },
        "module2": {
            "supported_processes": sorted(supported_processes),
            "process_item_hit_rate": round(process_hit_rate, 4),
            "chapter_hit_rate": round(chapter_hit_rate, 4),
            "process_item_hits": int(process_item_hits),
            "process_item_total": int(total_items),
            "chapter_hits": int(chapter_hit_count),
            "chapter_total": int(chapter_total),
            "missing_processes": missing_processes,
            "resource_nodes": int(resource_nodes),
            "formula_nodes": int(formula_nodes),
            "schedule_nodes": int(schedule_nodes),
            "score": round(module2_score, 4),
        },
        "overall_score": round(overall_score, 4),
        "suggestions": [
            f"补充维度节点: {'、'.join(missing_dims[:6])}" if missing_dims else "维度覆盖完整",
            (
                f"补充工序映射关键词: {'、'.join(missing_processes[:4])}"
                if missing_processes
                else "工序映射覆盖完整"
            ),
        ],
    }


def _render_markdown(
    *,
    report: Dict[str, Any],
    out_path: Path,
) -> None:
    rows = report["files"]
    lines: List[str] = []
    lines.append("# KG Module1-2 Adaptation Report")
    lines.append("")
    lines.append(f"- Generated At: {report['generated_at']}")
    lines.append(f"- KG Root: {report['kg_root']}")
    lines.append(f"- BoQ Baseline: {report['boq_baseline']['boq_path']}")
    lines.append(f"- Files Total: {report['summary']['files_total']}")
    lines.append(f"- Module1 Avg Coverage: {report['summary']['module1_avg_coverage']}")
    lines.append(f"- Module1 Full-Coverage Files: {report['summary']['module1_full_coverage_files']}")
    lines.append(f"- Module2 Avg Process Hit: {report['summary']['module2_avg_process_hit_rate']}")
    lines.append(f"- Module2 Avg Chapter Hit: {report['summary']['module2_avg_chapter_hit_rate']}")
    lines.append(f"- Module2 Avg Score: {report['summary']['module2_avg_score']}")
    lines.append(f"- Overall Avg Score: {report['summary']['overall_avg_score']}")
    lines.append("")
    lines.append("| File | Nodes | M1 Coverage | Missing Dims | M2 Process Hit | M2 Chapter Hit | M2 Score | Overall |")
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|")
    for row in rows:
        missing = "、".join(row["module1"]["missing_dimensions"]) if row["module1"]["missing_dimensions"] else "-"
        lines.append(
            f"| {row['file']} | {row['node_count']} | {row['module1']['dimension_coverage_rate']:.2f} "
            f"| {missing} | {row['module2']['process_item_hit_rate']:.2f} | {row['module2']['chapter_hit_rate']:.2f} "
            f"| {row['module2']['score']:.2f} | {row['overall_score']:.2f} |"
        )

    weakest = sorted(rows, key=lambda r: float(r.get("overall_score", 0.0)))[:10]
    lines.append("")
    lines.append("## Priority Gaps")
    lines.append("")
    lines.append("| File | Overall | Key Suggestion 1 | Key Suggestion 2 |")
    lines.append("|---|---:|---|---|")
    for row in weakest:
        s1 = row["suggestions"][0] if row["suggestions"] else "-"
        s2 = row["suggestions"][1] if len(row["suggestions"]) > 1 else "-"
        lines.append(f"| {row['file']} | {row['overall_score']:.2f} | {s1} | {s2} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


async def _run(args: argparse.Namespace) -> int:
    kg_root = Path(args.kg_root).expanduser().resolve()
    boq_path = Path(args.boq).expanduser().resolve()
    out_md = Path(args.out_md).expanduser().resolve()
    out_json = Path(args.out_json).expanduser().resolve()

    if not kg_root.exists():
        raise FileNotFoundError(f"KG root not found: {kg_root}")
    if not boq_path.exists():
        raise FileNotFoundError(f"BoQ baseline file not found: {boq_path}")

    files = sorted(kg_root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {kg_root}/{args.pattern}")

    boq_baseline = await _build_boq_baseline(boq_path)
    rows = [_analyze_file(path, boq_baseline) for path in files]

    module1_avg = statistics.fmean(row["module1"]["dimension_coverage_rate"] for row in rows)
    module2_avg_process = statistics.fmean(row["module2"]["process_item_hit_rate"] for row in rows)
    module2_avg_chapter = statistics.fmean(row["module2"]["chapter_hit_rate"] for row in rows)
    module2_avg_score = statistics.fmean(row["module2"]["score"] for row in rows)
    overall_avg = statistics.fmean(float(row["overall_score"]) for row in rows)
    module1_full = sum(1 for row in rows if row["module1"]["ready"])

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "kg_root": str(kg_root),
        "pattern": args.pattern,
        "boq_baseline": boq_baseline,
        "summary": {
            "files_total": len(rows),
            "module1_avg_coverage": round(module1_avg, 4),
            "module1_full_coverage_files": int(module1_full),
            "module2_avg_process_hit_rate": round(module2_avg_process, 4),
            "module2_avg_chapter_hit_rate": round(module2_avg_chapter, 4),
            "module2_avg_score": round(module2_avg_score, 4),
            "overall_avg_score": round(overall_avg, 4),
        },
        "files": rows,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_markdown(report=report, out_path=out_md)

    print(f"kg_files={len(rows)}")
    print(f"boq_items={boq_baseline['total_items']}")
    print(f"module1_avg_coverage={report['summary']['module1_avg_coverage']}")
    print(f"module1_full_coverage_files={report['summary']['module1_full_coverage_files']}")
    print(f"module2_avg_process_hit_rate={report['summary']['module2_avg_process_hit_rate']}")
    print(f"module2_avg_chapter_hit_rate={report['summary']['module2_avg_chapter_hit_rate']}")
    print(f"overall_avg_score={report['summary']['overall_avg_score']}")
    print(f"report_json={out_json}")
    print(f"report_md={out_md}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Module1/2 adaptation report across all KG files.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--boq", default=str(DEFAULT_BOQ), help="BoQ baseline file path")
    parser.add_argument("--pattern", default=KG_GLOB, help="KG file glob pattern")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="Output markdown path")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output json path")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
