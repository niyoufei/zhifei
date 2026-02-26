#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_OUT_MD = Path("build/KG_Advanced_Audit_latest.md")
DEFAULT_OUT_JSON = Path("build/KG_Advanced_Audit_latest.json")

VIRTUAL_RELATION_TARGETS = {"通用前置条件", "关键风险事件", "不兼容工艺方案"}
REQUIRED_ASSERTIONS = {"must_have_action", "must_have_parameter", "must_have_checker"}
AUTHORITY_CHAIN = ["答疑文件", "设计图纸", "国标", "行标", "企标"]


def _iter_nodes(raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
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


def _formula_vars(expr: str) -> List[str] | None:
    try:
        tree = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError):
        return None
    return sorted(
        {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in {"max", "min", "abs", "round"}
        }
    )


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and any(str(x).strip() for x in value)


def _check_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes = list(_iter_nodes(raw))
    node_ids = [str(node.get("node_id") or "").strip() for node in nodes if str(node.get("node_id") or "").strip()]
    node_id_set = set(node_ids)

    issues = {
        "duplicate_node_ids": 0,
        "unresolved_relations": 0,
        "missing_reference_standard": 0,
        "missing_activation_signal": 0,
        "formula_parse_errors": 0,
        "formula_var_mismatch": 0,
        "missing_visual_specs": 0,
        "missing_failfast_enabled": 0,
        "missing_assertions": 0,
        "missing_authority_resolution": 0,
        "missing_reference_standard_codes": 0,
        "invalid_authority_rank": 0,
    }
    samples: Dict[str, List[Dict[str, Any]]] = {k: [] for k in issues}

    if len(node_ids) != len(node_id_set):
        issues["duplicate_node_ids"] += len(node_ids) - len(node_id_set)
        seen: set[str] = set()
        for node_id in node_ids:
            if node_id in seen:
                samples["duplicate_node_ids"].append({"node_id": node_id})
                if len(samples["duplicate_node_ids"]) >= 5:
                    break
            seen.add(node_id)

    for node in nodes:
        node_id = str(node.get("node_id") or "").strip()

        # relation closure check
        for rel_key in ("requires", "mitigates", "conflicts_with"):
            rels = node.get(rel_key)
            if not isinstance(rels, list):
                continue
            for rel in rels:
                ref = str(rel or "").strip()
                if not ref:
                    continue
                if ref in node_id_set or ref in VIRTUAL_RELATION_TARGETS:
                    continue
                if ref.startswith(f"{path.stem}-M1-"):
                    continue
                issues["unresolved_relations"] += 1
                if len(samples["unresolved_relations"]) < 8:
                    samples["unresolved_relations"].append({"node_id": node_id, "relation": rel_key, "target": ref})

        refs = node.get("reference_standard")
        if not _is_non_empty_list(refs):
            issues["missing_reference_standard"] += 1
            if len(samples["missing_reference_standard"]) < 8:
                samples["missing_reference_standard"].append({"node_id": node_id})
        codes = node.get("reference_standard_codes")
        if not _is_non_empty_list(codes):
            issues["missing_reference_standard_codes"] += 1
            if len(samples["missing_reference_standard_codes"]) < 8:
                samples["missing_reference_standard_codes"].append({"node_id": node_id})

        content = node.get("content")
        env = content.get("environment_sensing") if isinstance(content, dict) else None
        signal = env.get("activation_signal") if isinstance(env, dict) else ""
        if not str(signal or "").strip():
            issues["missing_activation_signal"] += 1
            if len(samples["missing_activation_signal"]) < 8:
                samples["missing_activation_signal"].append({"node_id": node_id})

        expr = str(node.get("formula_expression") or "").strip()
        if expr:
            parsed_vars = _formula_vars(expr)
            if parsed_vars is None:
                issues["formula_parse_errors"] += 1
                if len(samples["formula_parse_errors"]) < 8:
                    samples["formula_parse_errors"].append({"node_id": node_id, "expr": expr})
            else:
                var_list = sorted([str(v).strip() for v in (node.get("formula_variables") or []) if str(v).strip()])
                if parsed_vars != var_list:
                    issues["formula_var_mismatch"] += 1
                    if len(samples["formula_var_mismatch"]) < 8:
                        samples["formula_var_mismatch"].append(
                            {"node_id": node_id, "formula_vars": parsed_vars, "node_vars": var_list}
                        )

        if str(node.get("node_type") or "").strip() == "FormulaNode":
            visual = node.get("visual_specs")
            if not isinstance(visual, dict) or not bool(visual.get("enabled")):
                issues["missing_visual_specs"] += 1
                if len(samples["missing_visual_specs"]) < 8:
                    samples["missing_visual_specs"].append({"node_id": node_id})

        hooks = node.get("fail_fast_hooks")
        hooks_enabled = False
        if isinstance(hooks, dict):
            hooks_enabled = bool(hooks.get("enabled"))
        elif isinstance(hooks, list):
            hooks_enabled = any(str(item).strip() for item in hooks)
        if not hooks_enabled:
            issues["missing_failfast_enabled"] += 1
            if len(samples["missing_failfast_enabled"]) < 8:
                samples["missing_failfast_enabled"].append({"node_id": node_id})

        assertions = set(str(x).strip() for x in (node.get("response_assertions") or []) if str(x).strip())
        if not REQUIRED_ASSERTIONS.issubset(assertions):
            issues["missing_assertions"] += 1
            if len(samples["missing_assertions"]) < 8:
                samples["missing_assertions"].append({"node_id": node_id})

        authority = node.get("authority_resolution")
        if not isinstance(authority, dict) or not str(authority.get("selected_source_hierarchy") or "").strip():
            issues["missing_authority_resolution"] += 1
            if len(samples["missing_authority_resolution"]) < 8:
                samples["missing_authority_resolution"].append({"node_id": node_id})
        rank = int(node.get("authority_rank") or 0)
        if rank < 1 or rank > len(AUTHORITY_CHAIN):
            issues["invalid_authority_rank"] += 1
            if len(samples["invalid_authority_rank"]) < 8:
                samples["invalid_authority_rank"].append({"node_id": node_id, "authority_rank": rank})

    total_issues = int(sum(issues.values()))
    ready = total_issues == 0
    return {
        "file": path.name,
        "path": str(path),
        "node_total": len(nodes),
        "issues": issues,
        "total_issues": total_issues,
        "ready": ready,
        "samples": samples,
    }


def _render_md(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# KG Advanced Audit Report")
    lines.append("")
    lines.append(f"- Generated At: {report['generated_at']}")
    lines.append(f"- KG Root: {report['kg_root']}")
    lines.append(f"- Files Total: {report['summary']['files_total']}")
    lines.append(f"- Ready Files: {report['summary']['ready_files']}")
    lines.append(f"- Total Issues: {report['summary']['total_issues']}")
    lines.append("")
    lines.append("| File | Nodes | Total Issues | Ready |")
    lines.append("|---|---:|---:|---|")
    for row in report["files"]:
        lines.append(f"| {row['file']} | {row['node_total']} | {row['total_issues']} | {row['ready']} |")

    lines.append("")
    lines.append("## Issue Summary")
    lines.append("")
    lines.append("| Issue | Count |")
    lines.append("|---|---:|")
    for key, value in report["summary"]["issue_totals"].items():
        lines.append(f"| {key} | {value} |")

    worst = sorted(report["files"], key=lambda x: int(x.get("total_issues") or 0), reverse=True)[:10]
    lines.append("")
    lines.append("## Top Files")
    lines.append("")
    lines.append("| File | Issues |")
    lines.append("|---|---|")
    for row in worst:
        active = [k for k, v in row["issues"].items() if int(v) > 0]
        lines.append(f"| {row['file']} | {'、'.join(active) if active else '-'} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Advanced KG audit across all tactical graph files.")
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

    rows = [_check_file(path) for path in files]
    issue_keys = list(rows[0]["issues"].keys()) if rows else []
    issue_totals = {
        key: int(sum(int(row["issues"].get(key) or 0) for row in rows))
        for key in issue_keys
    }
    total_issues = int(sum(issue_totals.values()))
    ready_files = int(sum(1 for row in rows if row["ready"]))

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "kg_root": str(root),
        "summary": {
            "files_total": len(rows),
            "ready_files": ready_files,
            "total_issues": total_issues,
            "issue_totals": issue_totals,
        },
        "files": rows,
    }

    out_json = Path(args.out_json).expanduser().resolve()
    out_md = Path(args.out_md).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_md(report, out_md)

    print(f"files_total={len(rows)}")
    print(f"ready_files={ready_files}")
    print(f"total_issues={total_issues}")
    print(f"report_json={out_json}")
    print(f"report_md={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
