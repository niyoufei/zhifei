from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.v2.data_graph_ingestion import search_graph_index

DEFAULT_DATASET_PATH = Path("backend/data/autoplan/v2/kg_retrieval_benchmark.seed.json")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_dataset(path: Path | str) -> Dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"version": "v1", "cases": []}
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": "v1", "cases": []}
    cases = payload.get("cases")
    if not isinstance(cases, list):
        cases = []
    payload["cases"] = cases
    return payload


def _hit_match_score(hit: Dict[str, Any], case: Dict[str, Any]) -> float:
    expected_keywords = [str(x).strip() for x in (case.get("expected_keywords") or []) if str(x).strip()]
    expected_domain = str(case.get("expected_domain") or "").strip().lower()

    title = str(hit.get("title") or "")
    snippet = str(hit.get("snippet") or "")
    merged = f"{title} {snippet}".lower()
    score = 0.0
    if expected_keywords:
        score += sum(1.0 for kw in expected_keywords if kw.lower() in merged)
    if expected_domain:
        domains = [str(x).strip().lower() for x in (hit.get("professional_domain_matches") or []) if str(x).strip()]
        if expected_domain in domains:
            score += 1.0
    return score


def run_retrieval_benchmark(
    *,
    db_path: Path | str,
    dataset_path: Path | str = DEFAULT_DATASET_PATH,
    top_k: int = 5,
    min_pass_rate: float = 0.75,
    min_avg_mrr: float = 0.55,
) -> Dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    cases = dataset.get("cases") or []
    rows: List[Dict[str, Any]] = []
    passed = 0
    mrr_sum = 0.0

    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            continue
        query = str(case.get("query") or "").strip()
        if not query:
            continue
        result = search_graph_index(
            query=query,
            top_k=max(1, int(top_k)),
            db_path=db_path,
            resolve_authority=True,
        )
        hits = result.get("results") or []
        rank = 0
        score = 0.0
        for i, hit in enumerate(hits, start=1):
            if not isinstance(hit, dict):
                continue
            s = _hit_match_score(hit, case)
            if s <= 0:
                continue
            rank = i
            score = s
            break
        ok = rank > 0
        if ok:
            passed += 1
            mrr_sum += 1.0 / rank
        rows.append(
            {
                "case_id": str(case.get("case_id") or f"case-{idx:03d}"),
                "query": query,
                "expected_keywords": case.get("expected_keywords") or [],
                "expected_domain": case.get("expected_domain"),
                "ok": ok,
                "rank": rank,
                "mrr": round((1.0 / rank) if rank > 0 else 0.0, 6),
                "match_score": round(score, 4),
                "top_total": len(hits),
                "top_node_id": (hits[rank - 1].get("node_id") if rank > 0 and rank - 1 < len(hits) else None),
            }
        )

    total = len(rows)
    pass_rate = round((passed / total), 6) if total > 0 else 0.0
    avg_mrr = round((mrr_sum / total), 6) if total > 0 else 0.0
    ok = bool(total > 0 and pass_rate >= float(min_pass_rate) and avg_mrr >= float(min_avg_mrr))
    return {
        "ok": ok,
        "dataset_path": str(Path(dataset_path).expanduser().resolve()),
        "db_path": str(Path(db_path).expanduser().resolve()),
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": max(total - passed, 0),
        "pass_rate": pass_rate,
        "avg_mrr": avg_mrr,
        "thresholds": {"min_pass_rate": _safe_float(min_pass_rate), "min_avg_mrr": _safe_float(min_avg_mrr)},
        "rows": rows,
    }
