#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_OUT_MD = Path("build/KG_Module5_Readiness_Report.md")
DEFAULT_OUT_JSON = Path("build/KG_Module5_Readiness_Report.json")
VAGUE_WORDS = ["加强", "提高", "注意", "确保", "严格"]


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


def _get_desc(node: Dict[str, Any]) -> str:
    content = node.get("content")
    if not isinstance(content, dict):
        return ""
    premium = content.get("operation_desc_premium")
    if isinstance(premium, dict):
        return str(premium.get("desc") or "")
    return ""


def _desc_ready(text: str) -> bool:
    raw = str(text or "")
    if any(word in raw for word in VAGUE_WORDS):
        return False
    if not ("第一步" in raw and "第二步" in raw and "第三步" in raw):
        return False
    if not ("工序名称" in raw and "参数" in raw and "风险" in raw and "控制" in raw and "验证" in raw):
        return False
    if "->" not in raw and "→" not in raw:
        return False
    if not re.search(r"(?:\d+(?:\.\d+)?\s*(?:mm|cm|m|m3|%|h|次|天|MPa)|C\d{2,3}|HRB\d{3,4})", raw, flags=re.IGNORECASE):
        return False
    if not any(chk in raw for chk in ("质量员", "安全员", "施工员", "环保员", "总工", "项目经理", "技术负责人", "专业工程师")):
        return False
    return True


def _root_ready(raw: Dict[str, Any]) -> bool:
    m5 = raw.get("module5_guardrails")
    if not isinstance(m5, dict):
        return False
    if not bool(m5.get("enabled")):
        return False
    if not isinstance(m5.get("forbidden_vague_words"), list):
        return False
    if not isinstance(m5.get("required_sentence_structure"), list):
        return False
    logic = m5.get("three_step_logic_lock")
    if not isinstance(logic, dict):
        return False
    if not all(key in logic for key in ("step1_define", "step2_analyze", "step3_solve", "flow_chain")):
        return False
    return True


def _node_ready(node: Dict[str, Any]) -> bool:
    lg = node.get("language_guardrails")
    if not isinstance(lg, dict):
        return False
    if not bool(lg.get("enabled")):
        return False
    if not isinstance(lg.get("required_structure"), list):
        return False
    logic = lg.get("three_step_logic_lock")
    if not isinstance(logic, dict) or not bool(logic.get("enabled")):
        return False
    if not all(k in logic for k in ("step1", "step2", "step3", "flow_chain")):
        return False
    if not isinstance(node.get("dry_content_lock"), dict):
        return False
    desc = _get_desc(node)
    return _desc_ready(desc)


def analyze_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes = _iter_nodes(raw)
    node_total = len(nodes)
    node_ready = sum(1 for node in nodes if _node_ready(node))
    root_ok = _root_ready(raw)
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
    lines.append("# KG Module5 Readiness Report")
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
    parser = argparse.ArgumentParser(description="Generate module5 readiness report for all KG files.")
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
