from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .kg_online_learning_writeback import writeback_online_learning_profile

DEFAULT_FEEDBACK_PATH = Path("build/kg_project_feedback_memory.json")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_feedback(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": "v1", "projects_total": 0, "nodes": {}, "updated_at": ""}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "v1", "projects_total": 0, "nodes": {}, "updated_at": ""}
    if not isinstance(payload, dict):
        return {"version": "v1", "projects_total": 0, "nodes": {}, "updated_at": ""}
    payload.setdefault("version", "v1")
    payload.setdefault("projects_total", 0)
    payload.setdefault("nodes", {})
    return payload


def _node_id_from_section(section: Dict[str, Any]) -> str:
    trace = section.get("source_trace") if isinstance(section.get("source_trace"), dict) else {}
    kg_node_ref = str(trace.get("kg_node_ref") or "").strip()
    if kg_node_ref:
        return kg_node_ref
    payload = trace.get("payload") if isinstance(trace.get("payload"), dict) else {}
    payload_node_id = str(payload.get("node_id") or "").strip()
    if payload_node_id:
        return payload_node_id
    hit = section.get("graph_hit") if isinstance(section.get("graph_hit"), dict) else {}
    hit_payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
    hit_payload_node_id = str(hit_payload.get("node_id") or "").strip()
    if hit_payload_node_id:
        return hit_payload_node_id
    node_id = str(trace.get("node_id") or "").strip()
    if node_id:
        return node_id
    return str(hit.get("node_id") or "").strip()


def _normalize_decision(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"accept", "accepted", "approve", "approved", "采纳", "通过"}:
        return "accept"
    if text in {"reject", "rejected", "deny", "驳回", "否决"}:
        return "reject"
    if text in {"modify", "modified", "edit", "更新", "修订"}:
        return "modify"
    return ""


def update_feedback_memory(
    *,
    result_payload: Dict[str, Any],
    output_path: Path | str = DEFAULT_FEEDBACK_PATH,
    writeback_graph: bool = False,
    graph_root: Path | str | None = None,
) -> Dict[str, Any]:
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    memory = _load_feedback(out)
    nodes = memory.get("nodes")
    if not isinstance(nodes, dict):
        nodes = {}
        memory["nodes"] = nodes

    sections = result_payload.get("sections") if isinstance(result_payload.get("sections"), list) else []
    evidence_stats = result_payload.get("sentence_evidence_stats") if isinstance(result_payload.get("sentence_evidence_stats"), dict) else {}
    coverage = _safe_float(evidence_stats.get("trace_coverage_ratio"), 0.0)
    project_ok = not bool(result_payload.get("intercepted"))
    project_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    node_updates = 0
    touched_node_ids = set()
    for section in sections:
        if not isinstance(section, dict):
            continue
        node_id = _node_id_from_section(section)
        if not node_id:
            continue
        rec = nodes.get(node_id)
        if not isinstance(rec, dict):
            rec = {
                "hit_count": 0,
                "pass_count": 0,
                "trace_coverage_sum": 0.0,
                "trace_coverage_avg": 0.0,
                "last_seen_at": "",
                "domains": {},
            }
        rec["hit_count"] = int(rec.get("hit_count") or 0) + 1
        if project_ok:
            rec["pass_count"] = int(rec.get("pass_count") or 0) + 1
        rec["trace_coverage_sum"] = round(_safe_float(rec.get("trace_coverage_sum"), 0.0) + coverage, 6)
        rec["trace_coverage_avg"] = round(
            _safe_float(rec.get("trace_coverage_sum"), 0.0) / max(int(rec.get("hit_count") or 1), 1),
            6,
        )
        rec["pass_rate"] = round(int(rec.get("pass_count") or 0) / max(int(rec.get("hit_count") or 1), 1), 6)
        rec["last_seen_at"] = project_ts
        domain = str(section.get("specialist_domain") or "general")
        domains = rec.get("domains")
        if not isinstance(domains, dict):
            domains = {}
        domains[domain] = int(domains.get(domain) or 0) + 1
        rec["domains"] = domains

        segment_perf = rec.get("segment_performance")
        if not isinstance(segment_perf, dict):
            segment_perf = {}
        seg_key = f"domain:{domain}"
        seg_row = segment_perf.get(seg_key)
        if not isinstance(seg_row, dict):
            seg_row = {"hit_count": 0, "pass_count": 0}
        seg_row["hit_count"] = int(seg_row.get("hit_count") or 0) + 1
        if project_ok:
            seg_row["pass_count"] = int(seg_row.get("pass_count") or 0) + 1
        seg_row["pass_rate"] = round(
            int(seg_row.get("pass_count") or 0) / max(int(seg_row.get("hit_count") or 1), 1),
            6,
        )
        segment_perf[seg_key] = seg_row
        rec["segment_performance"] = segment_perf

        segment_overrides = rec.get("segment_overrides")
        if not isinstance(segment_overrides, list):
            segment_overrides = []
        dom_pass = float(seg_row.get("pass_rate") or 0.0)
        dom_weight = 1.06 if dom_pass >= 0.85 else 0.95 if dom_pass < 0.55 else 1.0
        updated = False
        for row in segment_overrides:
            if not isinstance(row, dict):
                continue
            if str(row.get("segment_type") or "") == "domain" and str(row.get("segment_key") or "") == domain:
                row["min_hit_count"] = 3
                row["weight_adjustments"] = {"domain_weight": round(dom_weight, 6)}
                updated = True
                break
        if not updated:
            segment_overrides.append(
                {
                    "segment_type": "domain",
                    "segment_key": domain,
                    "min_hit_count": 3,
                    "weight_adjustments": {"domain_weight": round(dom_weight, 6)},
                }
            )
        rec["segment_overrides"] = segment_overrides[:24]

        # Rolling recommended baseline from section text hints.
        text = str(section.get("content") or "")
        recommended = rec.get("recommended_defaults")
        if not isinstance(recommended, dict):
            recommended = {}
        if "每班次检查2次" in text:
            recommended["inspection_frequency_per_shift"] = 2
        if "偏差处置时限=4h" in text or "偏差处置时限4h" in text:
            recommended["deviation_response_hours"] = 4
        if "阈值=95%" in text:
            recommended["quality_threshold_percent"] = 95
        rec["recommended_defaults"] = recommended

        nodes[node_id] = rec
        node_updates += 1
        touched_node_ids.add(node_id)

    decision_updates = 0
    decisions = result_payload.get("review_decisions") if isinstance(result_payload.get("review_decisions"), list) else []
    for row in decisions:
        if not isinstance(row, dict):
            continue
        node_id = str(row.get("kg_node_ref") or row.get("node_id") or row.get("source_node_id") or "").strip()
        if not node_id:
            continue
        decision = _normalize_decision(row.get("decision"))
        if not decision:
            continue
        rec = nodes.get(node_id)
        if not isinstance(rec, dict):
            rec = {
                "hit_count": 0,
                "pass_count": 0,
                "trace_coverage_sum": 0.0,
                "trace_coverage_avg": 0.0,
                "last_seen_at": project_ts,
                "domains": {},
            }
        rec["accepted_count"] = int(rec.get("accepted_count") or 0)
        rec["rejected_count"] = int(rec.get("rejected_count") or 0)
        rec["modified_count"] = int(rec.get("modified_count") or 0)
        if decision == "accept":
            rec["accepted_count"] += 1
        elif decision == "reject":
            rec["rejected_count"] += 1
        elif decision == "modify":
            rec["modified_count"] += 1
        rec["decision_total"] = int(rec.get("decision_total") or 0) + 1
        rec["last_decision"] = decision
        rec["last_decision_at"] = project_ts
        note = str(row.get("note") or "").strip()
        if note:
            rec["last_decision_note"] = note[:200]

        adjustments = rec.get("weight_adjustments")
        if not isinstance(adjustments, dict):
            adjustments = {
                "keyword_exact_weight": 1.0,
                "query_token_weight": 1.0,
                "fts_rank_weight": 1.0,
                "domain_weight": 1.0,
                "timeline_weight": 1.0,
                "region_weight": 1.0,
            }
        if decision == "accept":
            adjustments["keyword_exact_weight"] = round(min(1.8, _safe_float(adjustments.get("keyword_exact_weight"), 1.0) + 0.03), 6)
            adjustments["domain_weight"] = round(min(1.8, _safe_float(adjustments.get("domain_weight"), 1.0) + 0.02), 6)
        elif decision == "reject":
            adjustments["keyword_exact_weight"] = round(max(0.6, _safe_float(adjustments.get("keyword_exact_weight"), 1.0) - 0.05), 6)
            adjustments["fts_rank_weight"] = round(max(0.6, _safe_float(adjustments.get("fts_rank_weight"), 1.0) - 0.03), 6)
        else:
            adjustments["keyword_fuzzy_weight"] = round(min(1.8, _safe_float(adjustments.get("keyword_fuzzy_weight"), 1.0) + 0.02), 6)
            adjustments["query_token_weight"] = round(min(1.8, _safe_float(adjustments.get("query_token_weight"), 1.0) + 0.01), 6)
        rec["weight_adjustments"] = adjustments

        corrected = row.get("corrected_values")
        if isinstance(corrected, dict) and corrected:
            defaults = rec.get("recommended_defaults")
            if not isinstance(defaults, dict):
                defaults = {}
            for k, v in corrected.items():
                key = str(k).strip()
                if key:
                    defaults[key] = v
            rec["recommended_defaults"] = defaults

        rec["last_seen_at"] = project_ts
        nodes[node_id] = rec
        touched_node_ids.add(node_id)
        decision_updates += 1

    memory["projects_total"] = int(memory.get("projects_total") or 0) + 1
    memory["updated_at"] = project_ts
    out.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

    writeback_report: Dict[str, Any] = {"triggered": False}
    if writeback_graph:
        node_feedback: Dict[str, Any] = {}
        for node_id in sorted(touched_node_ids):
            row = nodes.get(node_id)
            if isinstance(row, dict):
                node_feedback[node_id] = row
        if graph_root in (None, ""):
            writeback_report = {"triggered": True, "ok": False, "error": "graph_root_missing"}
        else:
            writeback_report = {
                "triggered": True,
                **writeback_online_learning_profile(
                    graph_root=graph_root,
                    node_feedback=node_feedback,
                    timestamp=project_ts,
                ),
            }

    return {
        "ok": True,
        "saved_at": str(out),
        "projects_total": int(memory.get("projects_total") or 0),
        "nodes_total": len(nodes),
        "node_updates": node_updates,
        "decision_updates": decision_updates,
        "writeback": writeback_report,
    }
