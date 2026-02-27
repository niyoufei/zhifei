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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


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
        "missing_standard_timeline": 0,
        "missing_regional_policy": 0,
        "missing_regional_redlines": 0,
        "missing_unit_dimension_model": 0,
        "missing_evidence_anchors": 0,
        "missing_cross_constraints": 0,
        "missing_process_parameter_pack": 0,
        "missing_resource_productivity_model": 0,
        "missing_risk_trigger_matrix": 0,
        "missing_clause_locator": 0,
        "missing_clause_locator_pointer": 0,
        "missing_interface_contract": 0,
        "missing_optimization_objectives_ext": 0,
        "missing_online_learning_profile": 0,
        "missing_online_learning_segment_overrides": 0,
        "missing_long_tail_profile": 0,
        "missing_uncertainty_profile": 0,
        "low_uncertainty_confidence": 0,
        "missing_retrieval_benchmark": 0,
        "low_retrieval_quality_score": 0,
        "auto_generated_unapproved": 0,
        "missing_formula_sensitivity": 0,
        "missing_bim_ifc_context": 0,
        "missing_incremental_fingerprint": 0,
        "missing_entity_alignment": 0,
        "missing_entity_master_key": 0,
        "missing_regional_standard_timeline": 0,
        "missing_abnormal_scenario_playbook": 0,
        "missing_deduction_counterexample_library": 0,
        "missing_formula_safety_profile": 0,
        "unsafe_formula_safety_profile": 0,
        "missing_evidence_completeness": 0,
        "low_evidence_completeness_ratio": 0,
        "missing_numeric_source_evidence": 0,
        "open_interface_conflict": 0,
        "missing_source_provenance": 0,
        "low_evidence_verification_ratio": 0,
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

        timeline = node.get("standard_validity_timeline")
        if not isinstance(timeline, dict) or not isinstance(timeline.get("records"), list) or not timeline.get("records"):
            issues["missing_standard_timeline"] += 1
            if len(samples["missing_standard_timeline"]) < 8:
                samples["missing_standard_timeline"].append({"node_id": node_id})

        regional = node.get("regional_policy_layers")
        if not isinstance(regional, dict) or not isinstance(regional.get("layers"), list) or not regional.get("layers"):
            issues["missing_regional_policy"] += 1
            if len(samples["missing_regional_policy"]) < 8:
                samples["missing_regional_policy"].append({"node_id": node_id})
        redlines = regional.get("numeric_redlines") if isinstance(regional, dict) else {}
        if not isinstance(redlines, dict) or not bool(redlines.get("enabled")):
            issues["missing_regional_redlines"] += 1
            if len(samples["missing_regional_redlines"]) < 8:
                samples["missing_regional_redlines"].append({"node_id": node_id})

        unit_model = node.get("unit_dimension_model")
        if not isinstance(unit_model, dict) or not isinstance(unit_model.get("parameters"), list):
            issues["missing_unit_dimension_model"] += 1
            if len(samples["missing_unit_dimension_model"]) < 8:
                samples["missing_unit_dimension_model"].append({"node_id": node_id})

        anchors = node.get("evidence_anchors")
        if not isinstance(anchors, list) or not anchors:
            issues["missing_evidence_anchors"] += 1
            if len(samples["missing_evidence_anchors"]) < 8:
                samples["missing_evidence_anchors"].append({"node_id": node_id})

        constraints = node.get("cross_discipline_constraints")
        if not isinstance(constraints, dict) or not bool(constraints.get("enabled")):
            issues["missing_cross_constraints"] += 1
            if len(samples["missing_cross_constraints"]) < 8:
                samples["missing_cross_constraints"].append({"node_id": node_id})

        process_pack = node.get("process_parameter_pack")
        if not isinstance(process_pack, dict) or not bool(process_pack.get("enabled")) or not isinstance(process_pack.get("steps"), list):
            issues["missing_process_parameter_pack"] += 1
            if len(samples["missing_process_parameter_pack"]) < 8:
                samples["missing_process_parameter_pack"].append({"node_id": node_id})

        resource_model = node.get("resource_productivity_model")
        if not isinstance(resource_model, dict) or not bool(resource_model.get("enabled")):
            issues["missing_resource_productivity_model"] += 1
            if len(samples["missing_resource_productivity_model"]) < 8:
                samples["missing_resource_productivity_model"].append({"node_id": node_id})

        risk_matrix = node.get("risk_trigger_matrix")
        if not isinstance(risk_matrix, dict) or not bool(risk_matrix.get("enabled")) or not isinstance(risk_matrix.get("items"), list):
            issues["missing_risk_trigger_matrix"] += 1
            if len(samples["missing_risk_trigger_matrix"]) < 8:
                samples["missing_risk_trigger_matrix"].append({"node_id": node_id})

        clause_locator = node.get("clause_locator")
        if not isinstance(clause_locator, dict) or not bool(clause_locator.get("enabled")) or not isinstance(clause_locator.get("anchors"), list):
            issues["missing_clause_locator"] += 1
            if len(samples["missing_clause_locator"]) < 8:
                samples["missing_clause_locator"].append({"node_id": node_id})
        else:
            anchors = clause_locator.get("anchors")
            pointer_ok = False
            if isinstance(anchors, list):
                for anchor in anchors:
                    if not isinstance(anchor, dict):
                        continue
                    has_hash = bool(str(anchor.get("anchor_hash") or "").strip())
                    has_excerpt = bool(str(anchor.get("source_excerpt") or "").strip())
                    has_path = bool(str(anchor.get("clause_path") or "").strip())
                    if has_hash and (has_excerpt or has_path):
                        pointer_ok = True
                        break
            if not pointer_ok:
                issues["missing_clause_locator_pointer"] += 1
                if len(samples["missing_clause_locator_pointer"]) < 8:
                    samples["missing_clause_locator_pointer"].append({"node_id": node_id})

        interface_contract = node.get("cross_discipline_interface_contract")
        if not isinstance(interface_contract, dict) or not bool(interface_contract.get("enabled")) or not isinstance(interface_contract.get("interfaces"), list):
            issues["missing_interface_contract"] += 1
            if len(samples["missing_interface_contract"]) < 8:
                samples["missing_interface_contract"].append({"node_id": node_id})
        else:
            unresolved_edges = []
            for edge in interface_contract.get("conflict_graph") or []:
                if not isinstance(edge, dict):
                    continue
                if str(edge.get("status") or "").strip().lower() in {"conflict", "open"}:
                    unresolved_edges.append(edge)
            if unresolved_edges:
                issues["open_interface_conflict"] += len(unresolved_edges)
                if len(samples["open_interface_conflict"]) < 8:
                    samples["open_interface_conflict"].append(
                        {"node_id": node_id, "unresolved": unresolved_edges[:3]}
                    )

        optimization_ext = node.get("optimization_objectives_ext")
        if not isinstance(optimization_ext, dict) or not bool(optimization_ext.get("enabled")) or not isinstance(optimization_ext.get("objectives"), dict):
            issues["missing_optimization_objectives_ext"] += 1
            if len(samples["missing_optimization_objectives_ext"]) < 8:
                samples["missing_optimization_objectives_ext"].append({"node_id": node_id})

        learning = node.get("online_learning_profile")
        if not isinstance(learning, dict) or not bool(learning.get("enabled")):
            issues["missing_online_learning_profile"] += 1
            if len(samples["missing_online_learning_profile"]) < 8:
                samples["missing_online_learning_profile"].append({"node_id": node_id})
        else:
            seg = learning.get("segment_overrides")
            if not isinstance(seg, list) or not seg:
                issues["missing_online_learning_segment_overrides"] += 1
                if len(samples["missing_online_learning_segment_overrides"]) < 8:
                    samples["missing_online_learning_segment_overrides"].append({"node_id": node_id})

        long_tail = node.get("long_tail_profile")
        if not isinstance(long_tail, dict) or not bool(long_tail.get("enabled")):
            issues["missing_long_tail_profile"] += 1
            if len(samples["missing_long_tail_profile"]) < 8:
                samples["missing_long_tail_profile"].append({"node_id": node_id})

        uncertainty = node.get("uncertainty_profile")
        if str(node.get("formula_expression") or "").strip():
            if not isinstance(uncertainty, dict) or not bool(uncertainty.get("enabled")):
                issues["missing_uncertainty_profile"] += 1
                if len(samples["missing_uncertainty_profile"]) < 8:
                    samples["missing_uncertainty_profile"].append({"node_id": node_id})
            else:
                confidence = _safe_float(uncertainty.get("confidence_level"), 0.0)
                if confidence < 0.5:
                    issues["low_uncertainty_confidence"] += 1
                    if len(samples["low_uncertainty_confidence"]) < 8:
                        samples["low_uncertainty_confidence"].append({"node_id": node_id, "confidence_level": confidence})

        benchmark = node.get("retrieval_benchmark")
        if not isinstance(benchmark, dict) or benchmark.get("quality_score") in (None, ""):
            issues["missing_retrieval_benchmark"] += 1
            if len(samples["missing_retrieval_benchmark"]) < 8:
                samples["missing_retrieval_benchmark"].append({"node_id": node_id})
        else:
            score = float(benchmark.get("quality_score") or 0.0)
            minimum = float(benchmark.get("minimum_quality_score") or 0.0)
            if score < minimum:
                issues["low_retrieval_quality_score"] += 1
                if len(samples["low_retrieval_quality_score"]) < 8:
                    samples["low_retrieval_quality_score"].append({"node_id": node_id, "quality_score": score, "minimum": minimum})

        workflow = node.get("approval_workflow")
        if bool(node.get("is_auto_generated")):
            status = ""
            if isinstance(workflow, dict):
                status = str(workflow.get("status") or "").strip().lower()
            if status != "approved":
                issues["auto_generated_unapproved"] += 1
                if len(samples["auto_generated_unapproved"]) < 8:
                    samples["auto_generated_unapproved"].append({"node_id": node_id, "status": status})

        sensitivity = node.get("formula_sensitivity")
        if str(node.get("formula_expression") or "").strip():
            if not isinstance(sensitivity, dict) or sensitivity.get("enabled") not in (True, False):
                issues["missing_formula_sensitivity"] += 1
                if len(samples["missing_formula_sensitivity"]) < 8:
                    samples["missing_formula_sensitivity"].append({"node_id": node_id})

        ifc_ctx = node.get("bim_ifc_context")
        if not isinstance(ifc_ctx, dict) or not isinstance(ifc_ctx.get("ifc_entities"), list):
            issues["missing_bim_ifc_context"] += 1
            if len(samples["missing_bim_ifc_context"]) < 8:
                samples["missing_bim_ifc_context"].append({"node_id": node_id})

        if not str(node.get("incremental_fingerprint") or "").strip():
            issues["missing_incremental_fingerprint"] += 1
            if len(samples["missing_incremental_fingerprint"]) < 8:
                samples["missing_incremental_fingerprint"].append({"node_id": node_id})
        provenance = node.get("source_provenance")
        if not isinstance(provenance, dict) or not str(provenance.get("resolved_source_hierarchy") or "").strip():
            issues["missing_source_provenance"] += 1
            if len(samples["missing_source_provenance"]) < 8:
                samples["missing_source_provenance"].append({"node_id": node_id})

        entity_alignment = node.get("entity_alignment")
        if not isinstance(entity_alignment, dict) or not bool(entity_alignment.get("enabled")):
            issues["missing_entity_alignment"] += 1
            if len(samples["missing_entity_alignment"]) < 8:
                samples["missing_entity_alignment"].append({"node_id": node_id})
        master_key = str(
            node.get("entity_master_key")
            or ((entity_alignment or {}).get("entity_master_key") if isinstance(entity_alignment, dict) else "")
            or ""
        ).strip()
        if not master_key:
            issues["missing_entity_master_key"] += 1
            if len(samples["missing_entity_master_key"]) < 8:
                samples["missing_entity_master_key"].append({"node_id": node_id})

        regional_timeline = node.get("regional_standard_timeline")
        if (
            not isinstance(regional_timeline, dict)
            or not bool(regional_timeline.get("enabled"))
            or not isinstance(regional_timeline.get("records"), list)
            or not regional_timeline.get("records")
        ):
            issues["missing_regional_standard_timeline"] += 1
            if len(samples["missing_regional_standard_timeline"]) < 8:
                samples["missing_regional_standard_timeline"].append({"node_id": node_id})

        abnormal_playbook = node.get("abnormal_scenario_playbook")
        if (
            not isinstance(abnormal_playbook, dict)
            or not bool(abnormal_playbook.get("enabled"))
            or not isinstance(abnormal_playbook.get("items"), list)
            or not abnormal_playbook.get("items")
        ):
            issues["missing_abnormal_scenario_playbook"] += 1
            if len(samples["missing_abnormal_scenario_playbook"]) < 8:
                samples["missing_abnormal_scenario_playbook"].append({"node_id": node_id})

        deduction_library = node.get("deduction_counterexample_library")
        if (
            not isinstance(deduction_library, dict)
            or not bool(deduction_library.get("enabled"))
            or not isinstance(deduction_library.get("items"), list)
            or not deduction_library.get("items")
        ):
            issues["missing_deduction_counterexample_library"] += 1
            if len(samples["missing_deduction_counterexample_library"]) < 8:
                samples["missing_deduction_counterexample_library"].append({"node_id": node_id})

        formula_expr = str(node.get("formula_expression") or "").strip()
        if formula_expr:
            safety = node.get("formula_safety_profile")
            if (
                not isinstance(safety, dict)
                or not bool(safety.get("enabled"))
                or safety.get("safe") not in (True, False)
            ):
                issues["missing_formula_safety_profile"] += 1
                if len(samples["missing_formula_safety_profile"]) < 8:
                    samples["missing_formula_safety_profile"].append({"node_id": node_id})
            elif not bool(safety.get("safe")):
                issues["unsafe_formula_safety_profile"] += 1
                if len(samples["unsafe_formula_safety_profile"]) < 8:
                    samples["unsafe_formula_safety_profile"].append({"node_id": node_id})

        numeric_sources = node.get("numeric_sources")
        if isinstance(numeric_sources, list) and numeric_sources:
            evidence = node.get("evidence_completeness")
            if (
                not isinstance(evidence, dict)
                or not bool(evidence.get("enabled"))
                or evidence.get("completeness_ratio") in (None, "")
            ):
                issues["missing_evidence_completeness"] += 1
                if len(samples["missing_evidence_completeness"]) < 8:
                    samples["missing_evidence_completeness"].append({"node_id": node_id})
            else:
                ratio = _safe_float(evidence.get("completeness_ratio"), 0.0)
                has_anchor = bool(evidence.get("has_clause_anchor"))
                effective_date = str(evidence.get("effective_date") or "").strip()
                source_hierarchy = str(evidence.get("source_hierarchy") or "").strip()
                if ratio < 0.8:
                    issues["low_evidence_completeness_ratio"] += 1
                    if len(samples["low_evidence_completeness_ratio"]) < 8:
                        samples["low_evidence_completeness_ratio"].append({"node_id": node_id, "ratio": ratio})
                verify_ratio = _safe_float(evidence.get("verification_ratio"), 0.0)
                if verify_ratio < 0.2:
                    issues["low_evidence_verification_ratio"] += 1
                    if len(samples["low_evidence_verification_ratio"]) < 8:
                        samples["low_evidence_verification_ratio"].append(
                            {"node_id": node_id, "verification_ratio": verify_ratio}
                        )
                if not (has_anchor and effective_date and source_hierarchy):
                    issues["missing_numeric_source_evidence"] += 1
                    if len(samples["missing_numeric_source_evidence"]) < 8:
                        samples["missing_numeric_source_evidence"].append(
                            {
                                "node_id": node_id,
                                "has_clause_anchor": has_anchor,
                                "effective_date": effective_date,
                                "source_hierarchy": source_hierarchy,
                            }
                        )

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
