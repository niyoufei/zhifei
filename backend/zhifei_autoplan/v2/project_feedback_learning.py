from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

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
    node_id = str(trace.get("node_id") or "").strip()
    if node_id:
        return node_id
    hit = section.get("graph_hit") if isinstance(section.get("graph_hit"), dict) else {}
    return str(hit.get("node_id") or "").strip()


def update_feedback_memory(
    *,
    result_payload: Dict[str, Any],
    output_path: Path | str = DEFAULT_FEEDBACK_PATH,
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

    memory["projects_total"] = int(memory.get("projects_total") or 0) + 1
    memory["updated_at"] = project_ts
    out.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "saved_at": str(out),
        "projects_total": int(memory.get("projects_total") or 0),
        "nodes_total": len(nodes),
        "node_updates": node_updates,
    }

