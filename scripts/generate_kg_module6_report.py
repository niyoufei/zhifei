#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_OUT_MD = Path("build/KG_Module6_Readiness_Report.md")
DEFAULT_OUT_JSON = Path("build/KG_Module6_Readiness_Report.json")

VISUAL_TYPES = ["样板", "流程", "思维导图", "智慧绿色四新"]
DRAWING_STANDARD = "GB/T 50104"
VISUAL_STANDARD = "CSCEC VI"
TEXT_STANDARD = "仿宋"


def _iter_nodes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    out: List[Dict[str, Any]] = []
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


def _root_ready(raw: Dict[str, Any]) -> bool:
    root = raw.get("module6_visual_generation")
    if not isinstance(root, dict):
        return False
    if not bool(root.get("enabled")):
        return False
    if str(root.get("provider_policy") or "").strip() == "":
        return False
    if not bool(root.get("auto_embed_to_docx")):
        return False
    visual_types = [str(x) for x in (root.get("content_professional") or [])]
    if not all(v in visual_types for v in VISUAL_TYPES):
        return False
    if DRAWING_STANDARD not in str(root.get("drawing_standard") or ""):
        return False
    if VISUAL_STANDARD not in str(root.get("visual_standard") or ""):
        return False
    if TEXT_STANDARD not in str(root.get("text_standard") or ""):
        return False
    return True


def _node_ready(node: Dict[str, Any]) -> bool:
    spec = node.get("visual_specs")
    if not isinstance(spec, dict):
        return False
    if not bool(spec.get("enabled")):
        return False
    visual_types = [str(x) for x in (spec.get("visual_types") or [])]
    if not all(v in visual_types for v in VISUAL_TYPES):
        return False
    if DRAWING_STANDARD not in str(spec.get("drawing_standard") or ""):
        return False
    if VISUAL_STANDARD not in str(spec.get("visual_standard") or ""):
        return False
    if TEXT_STANDARD not in str(spec.get("text_standard") or ""):
        return False
    if not bool(spec.get("docx_embed")):
        return False
    fields = [str(x) for x in (spec.get("data_binding_fields") or [])]
    if not all(k in fields for k in ("action", "parameter", "checker")):
        return False
    return True


def analyze_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes = _iter_nodes(raw)
    root_ok = _root_ready(raw)
    node_total = len(nodes)
    node_ready = sum(1 for node in nodes if _node_ready(node))
    node_coverage = node_ready / max(1, node_total)
    score = (0.4 if root_ok else 0.0) + (0.6 * node_coverage)
    return {
        "file": path.name,
        "path": str(path),
        "root_ready": root_ok,
        "node_ready": node_ready,
        "node_total": node_total,
        "node_coverage": round(node_coverage, 4),
        "overall_ready": bool(root_ok and node_ready == node_total),
        "overall_score": round(score, 4),
    }


def render_markdown(report: Dict[str, Any], out_path: Path) -> None:
    rows = report["files"]
    lines: List[str] = []
    lines.append("# KG Module6 Readiness Report")
    lines.append("")
    lines.append(f"- Generated At: {report['generated_at']}")
    lines.append(f"- KG Root: {report['kg_root']}")
    lines.append(f"- Files Total: {report['summary']['files_total']}")
    lines.append(f"- Fully Ready Files: {report['summary']['full_ready_files']}")
    lines.append(f"- Avg Score: {report['summary']['avg_score']}")
    lines.append(f"- Avg Node Coverage: {report['summary']['avg_node_coverage']}")
    lines.append("")
    lines.append("| File | Root Ready | Node Coverage | Overall Ready | Score |")
    lines.append("|---|---|---:|---|---:|")
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['root_ready']} | {row['node_ready']}/{row['node_total']} ({row['node_coverage']:.2f}) "
            f"| {row['overall_ready']} | {row['overall_score']:.2f} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate module6 readiness report for all KG files.")
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
