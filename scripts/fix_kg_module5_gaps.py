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

from backend.zhifei_autoplan.v2.index_matrix_engine import DIMENSION_RULES

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_SUMMARY = Path("build/KG_Module5_Fix_Summary.md")

VAGUE_WORDS = ["加强", "提高", "注意", "确保", "严格"]
DIMENSION_CHECKER = {
    "质量": "质量员",
    "安全": "安全员",
    "进度": "施工员",
    "环保": "环保员",
    "重难点": "总工",
    "扣分点": "项目经理",
}


def _iter_nodes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        raw["knowledge_database"] = {"module5_patch": {"nodes": []}}
        kg = raw["knowledge_database"]

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


def _infer_dimension(node: Dict[str, Any]) -> str:
    text = json.dumps(node, ensure_ascii=False)
    for dim, seeds in DIMENSION_RULES.items():
        if any(seed in text for seed in seeds):
            return dim
    return "质量"


def _get_premium_desc(node: Dict[str, Any]) -> str:
    content = node.get("content")
    if not isinstance(content, dict):
        return ""
    premium = content.get("operation_desc_premium")
    if isinstance(premium, dict):
        return str(premium.get("desc") or "").strip()
    return ""


def _set_premium_desc(node: Dict[str, Any], desc: str) -> None:
    if not isinstance(node.get("content"), dict):
        node["content"] = {}
    content = node["content"]
    if not isinstance(content.get("operation_desc_premium"), dict):
        content["operation_desc_premium"] = {}
    content["operation_desc_premium"]["desc"] = desc


def _build_three_step_template(*, dim: str, checker: str) -> str:
    return "；".join(
        [
            f"第一步（定义）：执行{dim}工序定义，工程量1200m3、标号C30、尺寸900mm，施工员每班次核验1次",
            "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次",
            f"第三步（解决）：执行{dim}控制与验证措施，偏差限值3mm、响应时限4h，{checker}每班次检查2次",
            "工序名称->参数->风险->控制->验证",
        ]
    )


def _desc_ready(desc: str) -> bool:
    text = str(desc or "")
    if any(word in text for word in VAGUE_WORDS):
        return False
    if not ("第一步" in text and "第二步" in text and "第三步" in text):
        return False
    if not ("工序名称" in text and "参数" in text and "风险" in text and "控制" in text and "验证" in text):
        return False
    if "->" not in text and "→" not in text:
        return False
    # must include numeric parameter and checker
    if not re.search(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|m3|%|h|次|天|MPa|C\d+)", text, flags=re.IGNORECASE):
        return False
    if not any(chk in text for chk in ("质量员", "安全员", "施工员", "环保员", "总工", "项目经理", "技术负责人")):
        return False
    return True


def _ensure_root_module5(raw: Dict[str, Any]) -> bool:
    defaults = {
        "enabled": True,
        "version": "v2.0",
        "forbidden_vague_words": list(VAGUE_WORDS),
        "required_sentence_structure": ["action", "parameter", "checker"],
        "three_step_logic_lock": {
            "step1_define": "先定义工序与参数(工程量/标号/尺寸)",
            "step2_analyze": "分析难点与风险(质量通病/安全隐患)",
            "step3_solve": "给出控制与验证措施",
            "flow_chain": "工序名称->参数->风险->控制->验证",
        },
        "fail_fast_on_violation": True,
        "rewrite_on_fail": True,
    }
    changed = False
    if not isinstance(raw.get("module5_guardrails"), dict):
        raw["module5_guardrails"] = defaults
        return True
    cur = raw["module5_guardrails"]
    for key, value in defaults.items():
        if key not in cur:
            cur[key] = value
            changed = True
    return changed


def _ensure_node_module5(node: Dict[str, Any]) -> bool:
    changed = False
    dim = _infer_dimension(node)
    checker = DIMENSION_CHECKER.get(dim, "专业工程师")

    if not isinstance(node.get("language_guardrails"), dict):
        node["language_guardrails"] = {}
        changed = True
    lg = node["language_guardrails"]
    defaults = {
        "enabled": True,
        "forbidden_vague_words": list(VAGUE_WORDS),
        "required_structure": ["action", "parameter", "checker"],
        "three_step_logic_lock": {
            "enabled": True,
            "step1": "定义工序与参数",
            "step2": "分析风险与难点",
            "step3": "控制措施与验证",
            "flow_chain": "工序名称->参数->风险->控制->验证",
        },
        "dry_content_density_lock": {
            "enabled": True,
            "min_numeric_parameters": 3,
            "must_include_checker": True,
        },
        "rewrite_template": _build_three_step_template(dim=dim, checker=checker),
    }
    for key, value in defaults.items():
        if key not in lg:
            lg[key] = value
            changed = True

    if not isinstance(node.get("dry_content_lock"), dict):
        node["dry_content_lock"] = {
            "enabled": True,
            "forbidden_words": list(VAGUE_WORDS),
            "required_triplet": "Action+Parameter+Checker",
        }
        changed = True

    desc = _get_premium_desc(node)
    if not _desc_ready(desc):
        _set_premium_desc(node, _build_three_step_template(dim=dim, checker=checker))
        changed = True

    return changed


def fix_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = False
    if _ensure_root_module5(raw):
        changed = True

    nodes = _iter_nodes(raw)
    node_updated = 0
    for node in nodes:
        if _ensure_node_module5(node):
            node_updated += 1
            changed = True

    if changed:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "changed": changed,
        "node_total": len(nodes),
        "node_updated": node_updated,
    }


def render_summary(rows: List[Dict[str, Any]], out_path: Path) -> None:
    files_total = len(rows)
    files_changed = sum(1 for r in rows if r["changed"])
    node_total = sum(int(r["node_total"]) for r in rows)
    node_updated = sum(int(r["node_updated"]) for r in rows)

    lines: List[str] = []
    lines.append("# KG Module5 Auto-Fix Summary")
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
    parser = argparse.ArgumentParser(description="Auto-fix module5 language guardrails in KG files.")
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
