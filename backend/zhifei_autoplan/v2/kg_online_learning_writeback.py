from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_KG_PATTERN = "ZF-KG-*.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


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


def _iter_kg_files(root: Path) -> List[Path]:
    if root.is_file() and root.suffix.lower() == ".json":
        return [root]
    if not root.exists() or not root.is_dir():
        return []
    files = sorted([p for p in root.glob(DEFAULT_KG_PATTERN) if p.is_file()])
    if files:
        return files
    return sorted([p for p in root.rglob("*.json") if p.is_file()])


def _merge_online_learning_profile(
    *,
    current: Any,
    feedback: Dict[str, Any],
    timestamp: str,
) -> Dict[str, Any]:
    profile = dict(current) if isinstance(current, dict) else {}
    hit_count = max(_safe_int(feedback.get("hit_count"), 0), 0)
    pass_count = max(_safe_int(feedback.get("pass_count"), 0), 0)
    if pass_count > hit_count:
        pass_count = hit_count
    trace_coverage_avg = round(max(0.0, min(1.0, _safe_float(feedback.get("trace_coverage_avg"), 0.0))), 6)
    pass_rate = round(max(0.0, min(1.0, _safe_float(feedback.get("pass_rate"), 0.0))), 6)
    if pass_rate <= 0.0 and hit_count > 0:
        pass_rate = round(pass_count / float(max(hit_count, 1)), 6)

    profile["enabled"] = True
    profile.setdefault("strategy", str(feedback.get("strategy") or "ema_feedback_v1"))
    profile["hit_count"] = hit_count
    profile["pass_count"] = pass_count
    profile["trace_coverage_avg"] = trace_coverage_avg
    profile["pass_rate"] = pass_rate
    profile["last_feedback_at"] = str(timestamp or profile.get("last_feedback_at") or "")
    profile["accepted_count"] = max(_safe_int(feedback.get("accepted_count"), _safe_int(profile.get("accepted_count"), 0)), 0)
    profile["rejected_count"] = max(_safe_int(feedback.get("rejected_count"), _safe_int(profile.get("rejected_count"), 0)), 0)
    profile["modified_count"] = max(_safe_int(feedback.get("modified_count"), _safe_int(profile.get("modified_count"), 0)), 0)
    profile["decision_total"] = max(_safe_int(feedback.get("decision_total"), _safe_int(profile.get("decision_total"), 0)), 0)
    if str(feedback.get("last_decision") or "").strip():
        profile["last_decision"] = str(feedback.get("last_decision"))
    if str(feedback.get("last_decision_at") or "").strip():
        profile["last_decision_at"] = str(feedback.get("last_decision_at"))
    if str(feedback.get("last_decision_note") or "").strip():
        profile["last_decision_note"] = str(feedback.get("last_decision_note"))[:200]

    domains = feedback.get("domains")
    if isinstance(domains, dict) and domains:
        profile["domains"] = {str(k): int(_safe_int(v, 0)) for k, v in domains.items() if str(k).strip()}
    recommended_defaults = feedback.get("recommended_defaults")
    if isinstance(recommended_defaults, dict) and recommended_defaults:
        profile["recommended_defaults"] = dict(recommended_defaults)
    adjustments = feedback.get("weight_adjustments")
    if isinstance(adjustments, dict) and adjustments:
        profile["weight_adjustments"] = {
            str(k): round(_safe_float(v, 1.0), 6)
            for k, v in adjustments.items()
            if str(k).strip()
        }
    return profile


def writeback_online_learning_profile(
    *,
    graph_root: Path | str,
    node_feedback: Dict[str, Any],
    timestamp: str | None = None,
) -> Dict[str, Any]:
    root = Path(graph_root).expanduser().resolve()
    if not root.exists():
        return {
            "ok": False,
            "graph_root": str(root),
            "error": "graph_root_not_found",
            "files_scanned": 0,
            "files_changed": 0,
            "nodes_updated": 0,
            "matched_nodes": 0,
            "unresolved_node_ids": sorted([str(k) for k in node_feedback.keys()])[:50],
        }
    if not isinstance(node_feedback, dict) or not node_feedback:
        return {
            "ok": True,
            "graph_root": str(root),
            "files_scanned": 0,
            "files_changed": 0,
            "nodes_updated": 0,
            "matched_nodes": 0,
            "unresolved_node_ids": [],
        }

    ts = str(timestamp or time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()))
    files = _iter_kg_files(root)
    unresolved = {str(k).strip() for k in node_feedback.keys() if str(k).strip()}
    parse_errors: List[Dict[str, str]] = []
    files_changed = 0
    nodes_updated = 0
    matched_nodes = 0

    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception as exc:
            parse_errors.append({"file": str(path), "error": str(exc)})
            continue
        changed = False
        for node in _iter_nodes(raw):
            node_id = str(node.get("node_id") or "").strip()
            if not node_id:
                continue
            feedback = node_feedback.get(node_id)
            if not isinstance(feedback, dict):
                continue
            matched_nodes += 1
            unresolved.discard(node_id)
            merged = _merge_online_learning_profile(
                current=node.get("online_learning_profile"),
                feedback=feedback,
                timestamp=ts,
            )
            before = json.dumps(node.get("online_learning_profile"), ensure_ascii=False, sort_keys=True)
            after = json.dumps(merged, ensure_ascii=False, sort_keys=True)
            if before != after:
                node["online_learning_profile"] = merged
                changed = True
                nodes_updated += 1
        if changed:
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            files_changed += 1

    return {
        "ok": True,
        "graph_root": str(root),
        "files_scanned": len(files),
        "files_changed": files_changed,
        "nodes_updated": nodes_updated,
        "matched_nodes": matched_nodes,
        "unresolved_node_ids": sorted(unresolved)[:50],
        "parse_errors": parse_errors[:20],
    }
