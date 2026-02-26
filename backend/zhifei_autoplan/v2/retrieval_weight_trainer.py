from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

DEFAULT_WEIGHT_PROFILE_PATH = Path("build/kg_retrieval_weight_profile.json")

DEFAULT_WEIGHT_PROFILE: Dict[str, float] = {
    "tag_weight": 1.0,
    "keyword_exact_weight": 1.0,
    "keyword_fuzzy_weight": 1.0,
    "query_token_weight": 1.0,
    "fts_rank_weight": 1.0,
    "domain_weight": 1.0,
    "gemini_weight_scale": 1.0,
    "retrieval_quality_weight_scale": 1.0,
    "approval_bonus_weight": 1.0,
    "timeline_weight": 1.0,
    "region_weight": 1.0,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_payload(payload_or_path: Dict[str, Any] | str | Path | None) -> Dict[str, Any]:
    if isinstance(payload_or_path, dict):
        return payload_or_path
    if payload_or_path in (None, ""):
        return {}
    path = Path(payload_or_path).expanduser().resolve()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _clip(value: float, lo: float = 0.6, hi: float = 2.0) -> float:
    return max(lo, min(hi, float(value)))


def train_retrieval_weight_profile(
    *,
    benchmark_report: Dict[str, Any] | str | Path | None = None,
    feedback_memory: Dict[str, Any] | str | Path | None = None,
    output_path: Path | str = DEFAULT_WEIGHT_PROFILE_PATH,
) -> Dict[str, Any]:
    benchmark = _load_payload(benchmark_report)
    feedback = _load_payload(feedback_memory)
    weights = dict(DEFAULT_WEIGHT_PROFILE)

    pass_rate = _safe_float(benchmark.get("pass_rate"), 0.0)
    avg_mrr = _safe_float(benchmark.get("avg_mrr"), 0.0)
    total_cases = int(benchmark.get("total_cases") or 0)
    failed_cases = int(benchmark.get("failed_cases") or max(total_cases - int(benchmark.get("passed_cases") or 0), 0))

    if total_cases > 0 and pass_rate < 0.80:
        gap = max(0.0, 0.80 - pass_rate)
        weights["keyword_exact_weight"] += min(0.40, gap * 1.8)
        weights["query_token_weight"] += min(0.35, gap * 1.5)
        weights["domain_weight"] += min(0.30, gap * 1.2)
        weights["tag_weight"] += min(0.25, gap * 0.8)
    if total_cases > 0 and avg_mrr < 0.60:
        gap = max(0.0, 0.60 - avg_mrr)
        weights["fts_rank_weight"] += min(0.45, gap * 2.0)
        weights["keyword_fuzzy_weight"] += min(0.30, gap * 1.3)
    if failed_cases > 0:
        weights["gemini_weight_scale"] += min(0.20, failed_cases * 0.01)
        weights["retrieval_quality_weight_scale"] += min(0.20, failed_cases * 0.01)

    nodes = feedback.get("nodes")
    if isinstance(nodes, dict) and nodes:
        pass_rates = [_safe_float((row or {}).get("pass_rate"), 0.0) for row in nodes.values() if isinstance(row, dict)]
        coverage = [_safe_float((row or {}).get("trace_coverage_avg"), 0.0) for row in nodes.values() if isinstance(row, dict)]
        avg_node_pass = sum(pass_rates) / max(len(pass_rates), 1) if pass_rates else 0.0
        avg_node_coverage = sum(coverage) / max(len(coverage), 1) if coverage else 0.0
        if avg_node_pass < 0.85:
            gap = max(0.0, 0.85 - avg_node_pass)
            weights["approval_bonus_weight"] += min(0.25, gap * 1.0)
            weights["timeline_weight"] += min(0.25, gap * 1.2)
        if avg_node_coverage < 0.80:
            gap = max(0.0, 0.80 - avg_node_coverage)
            weights["query_token_weight"] += min(0.20, gap * 1.0)
            weights["region_weight"] += min(0.15, gap * 0.8)

    for key in list(weights.keys()):
        weights[key] = round(_clip(weights[key]), 6)

    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "version": "v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "weights": weights,
        "signals": {
            "benchmark_total_cases": total_cases,
            "benchmark_pass_rate": round(pass_rate, 6),
            "benchmark_avg_mrr": round(avg_mrr, 6),
            "benchmark_failed_cases": failed_cases,
            "feedback_nodes": (len(nodes) if isinstance(nodes, dict) else 0),
        },
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**payload, "saved_at": str(out)}
