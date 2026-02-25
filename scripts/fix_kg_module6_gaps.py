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
DEFAULT_SUMMARY = Path("build/KG_Module6_Fix_Summary.md")

VISUAL_TYPES = ["样板", "流程", "思维导图", "智慧绿色四新"]
DRAWING_STANDARD = "GB/T 50104 建筑制图标准"
VISUAL_STANDARD = "CSCEC VI 蓝/绿/灰"
TEXT_STANDARD = "中文仿宋"


def _iter_nodes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        raw["knowledge_database"] = {"module6_patch": {"nodes": []}}
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


def _ensure_root_module6(raw: Dict[str, Any]) -> bool:
    defaults = {
        "enabled": True,
        "version": "v2.0",
        "provider_policy": "gemini_imagen_preferred_with_local_fallback",
        "preferred_provider": "google",
        "preferred_model": "imagen-3.0-generate-002",
        "fallback_renderer": "pillow",
        "auto_embed_to_docx": True,
        "content_professional": list(VISUAL_TYPES),
        "drawing_standard": DRAWING_STANDARD,
        "visual_standard": VISUAL_STANDARD,
        "text_standard": TEXT_STANDARD,
        "required_graphics_min_count": 4,
        "quality_gate": {
            "must_include_visual_types": list(VISUAL_TYPES),
            "must_bind_index_matrix": True,
            "must_follow_action_parameter_checker": True,
        },
    }
    changed = False
    if not isinstance(raw.get("module6_visual_generation"), dict):
        raw["module6_visual_generation"] = defaults
        return True
    cur = raw["module6_visual_generation"]
    for key, value in defaults.items():
        if key not in cur:
            cur[key] = value
            changed = True
    return changed


def _ensure_node_module6(node: Dict[str, Any]) -> bool:
    changed = False
    defaults = {
        "enabled": True,
        "visual_types": list(VISUAL_TYPES),
        "content_professional": list(VISUAL_TYPES),
        "drawing_standard": DRAWING_STANDARD,
        "visual_standard": VISUAL_STANDARD,
        "text_standard": TEXT_STANDARD,
        "docx_embed": True,
        "prompt_policy": "bind_index_matrix_and_node_parameters",
        "data_binding_fields": ["action", "parameter", "checker"],
    }

    if not isinstance(node.get("visual_specs"), dict):
        node["visual_specs"] = {}
        changed = True
    visual_specs = node["visual_specs"]
    for key, value in defaults.items():
        if key not in visual_specs:
            visual_specs[key] = value
            changed = True
    return changed


def fix_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = False

    if _ensure_root_module6(raw):
        changed = True

    nodes = _iter_nodes(raw)
    node_updated = 0
    for node in nodes:
        if _ensure_node_module6(node):
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
    nodes_total = sum(int(r["node_total"]) for r in rows)
    nodes_updated = sum(int(r["node_updated"]) for r in rows)

    lines: List[str] = []
    lines.append("# KG Module6 Auto-Fix Summary")
    lines.append("")
    lines.append(f"- Generated At: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}")
    lines.append(f"- Files Total: {files_total}")
    lines.append(f"- Files Changed: {files_changed}")
    lines.append(f"- Nodes Total: {nodes_total}")
    lines.append(f"- Nodes Updated: {nodes_updated}")
    lines.append("")
    lines.append("| File | Changed | Nodes | Nodes Updated |")
    lines.append("|---|---|---:|---:|")
    for row in rows:
        lines.append(f"| {row['file']} | {row['changed']} | {row['node_total']} | {row['node_updated']} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-fix module6 visual generation fields in KG files.")
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
