from __future__ import annotations

import json
import re
import time
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List

from backend.zhifei_autoplan.v2.data_graph_ingestion import search_graph_index

DEFAULT_DATASET_PATH = Path("backend/data/autoplan/v2/kg_retrieval_benchmark.seed.json")
DOMAIN_ALIASES = {
    "management": {"management", "general", "quality", "safety", "environment", "环保"},
    "building": {"building", "housing", "hospital", "decoration"},
    "road": {"road", "municipal", "traffic"},
    "mep": {"mep", "electrical", "hvac", "fire"},
}


def _iter_kg_nodes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    kb = payload.get("knowledge_database")
    if not isinstance(kb, dict):
        return out
    for section in kb.values():
        if not isinstance(section, dict):
            continue
        nodes = section.get("nodes")
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if isinstance(node, dict):
                out.append(node)
    return out


def _normalize_domain_hint(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "general"
    if any(tok in text for tok in ("bridge", "桥梁")):
        return "bridge"
    if any(tok in text for tok in ("tunnel", "隧道")):
        return "tunnel"
    if any(tok in text for tok in ("railway", "rail", "铁路")):
        return "railway"
    if any(tok in text for tok in ("hydraulic", "water", "水利", "泵站")):
        return "hydraulic"
    if any(tok in text for tok in ("mep", "机电", "电气", "hvac", "消防")):
        return "mep"
    if any(tok in text for tok in ("earthwork", "土方", "基坑", "边坡")):
        return "earthwork"
    if any(tok in text for tok in ("road", "道路", "市政")):
        return "road"
    if any(tok in text for tok in ("building", "房建", "主体", "装饰", "幕墙")):
        return "building"
    if any(tok in text for tok in ("management", "quality", "safety", "环保", "进度")):
        return "management"
    return text


def _extract_case_keywords(node: Dict[str, Any], *, max_count: int = 4) -> List[str]:
    values: List[str] = []
    for key in ("keywords", "qt_tag"):
        raw = node.get(key)
        if isinstance(raw, list):
            values.extend([str(x).strip() for x in raw if str(x).strip()])
    title = str(node.get("name") or node.get("title") or "").strip()
    values.extend([x for x in re.split(r"[^\w\u4e00-\u9fff]+", title) if x.strip()])
    out: List[str] = []
    seen = set()
    for item in values:
        term = str(item).strip()
        if not term or len(term) < 2:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", term):
            continue
        if "_" in term and not re.search(r"pm\d+|db|mpa", term.lower()):
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", term):
            continue
        low = term.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(term)
        if len(out) >= max_count:
            break
    return out


def _generate_cases_from_kg(
    *,
    kg_root: Path,
    max_cases: int,
    seed_offset: int = 0,
) -> List[Dict[str, Any]]:
    files = sorted(kg_root.glob("ZF-KG-*.json"))
    by_domain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    seq = int(seed_offset)
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        domain_hint = _normalize_domain_hint(payload.get("domain") or path.stem)
        for node in _iter_kg_nodes(payload):
            keywords = _extract_case_keywords(node)
            if not keywords:
                continue
            title = str(node.get("name") or node.get("title") or "").strip()
            query_candidates = [
                " ".join(keywords[:3]).strip(),
                " ".join(([title] if title else []) + keywords[:2]).strip(),
                " ".join((keywords[:1] + keywords[2:4])).strip(),
            ]
            dedup_local = set()
            for query in query_candidates:
                q = str(query or "").strip()
                if len(q) < 3:
                    continue
                q_key = q.lower()
                if q_key in dedup_local:
                    continue
                dedup_local.add(q_key)
                seq += 1
                case = {
                    "case_id": f"auto-{seq:04d}",
                    "query": q,
                    "expected_keywords": keywords[:2],
                    "expected_domain": "",
                    "domain_hint": domain_hint,
                    "source_file": path.name,
                    "auto_generated": True,
                }
                by_domain[domain_hint].append(case)

    domains = sorted(by_domain.keys())
    if not domains:
        return []
    out: List[Dict[str, Any]] = []
    cursor = {d: 0 for d in domains}
    while len(out) < max_cases:
        progressed = False
        for domain in domains:
            pool = by_domain.get(domain) or []
            idx = int(cursor.get(domain) or 0)
            if idx >= len(pool):
                continue
            out.append(pool[idx])
            cursor[domain] = idx + 1
            progressed = True
            if len(out) >= max_cases:
                break
        if not progressed:
            break
    return out


def _case_domain(case: Dict[str, Any]) -> str:
    hint = str(case.get("domain_hint") or case.get("expected_domain") or "").strip().lower()
    if hint:
        return hint
    source = str(case.get("source_file") or "").strip().lower()
    if not source:
        return "general"
    return _normalize_domain_hint(source)


def _summarize_case_coverage(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    domain_counts: Dict[str, int] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        domain = _case_domain(case)
        domain_counts[domain] = int(domain_counts.get(domain) or 0) + 1
    ranked = sorted(domain_counts.items(), key=lambda x: (-x[1], x[0]))
    return {
        "domains_total": len(domain_counts),
        "domain_counts": {k: v for k, v in ranked},
        "largest_domain": ranked[0][0] if ranked else "general",
        "largest_domain_cases": ranked[0][1] if ranked else 0,
    }


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


def ensure_benchmark_dataset(
    *,
    dataset_path: Path | str = DEFAULT_DATASET_PATH,
    kg_root: Path | str,
    min_cases: int = 120,
    max_cases: int = 360,
    output_path: Path | str | None = None,
) -> Dict[str, Any]:
    src = Path(dataset_path).expanduser().resolve()
    root = Path(kg_root).expanduser().resolve()
    payload = _load_dataset(src)
    existing = payload.get("cases") if isinstance(payload.get("cases"), list) else []
    dedup: Dict[str, Dict[str, Any]] = {}
    for case in existing:
        if not isinstance(case, dict):
            continue
        query = str(case.get("query") or "").strip()
        if not query:
            continue
        dedup[query.lower()] = case

    min_n = max(0, int(min_cases))
    max_n = max(min_n, int(max_cases))
    expanded = False
    if len(dedup) < min_n:
        generated = _generate_cases_from_kg(
            kg_root=root,
            max_cases=max_n,
            seed_offset=len(dedup),
        )
        for case in generated:
            query = str(case.get("query") or "").strip()
            if not query:
                continue
            key = query.lower()
            if key in dedup:
                continue
            dedup[key] = case
            if len(dedup) >= max_n:
                break
        expanded = True

    merged_cases = list(dedup.values())[:max_n]
    dst = Path(output_path).expanduser().resolve() if output_path not in (None, "") else src
    if expanded:
        out_payload = {
            "version": str(payload.get("version") or "v2"),
            "meta": {
                "auto_expanded": True,
                "source_dataset": str(src),
                "generated_at": int(time.time()),
                "cases_seed": len(existing),
                "cases_total": len(merged_cases),
                "kg_root": str(root),
            },
            "cases": merged_cases,
        }
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    effective_cases = merged_cases if expanded else [x for x in existing if isinstance(x, dict)]
    coverage = _summarize_case_coverage(effective_cases)
    return {
        "ok": True,
        "expanded": expanded,
        "dataset_path": str(dst if expanded else src),
        "cases_seed": len(existing),
        "cases_total": len(effective_cases),
        "coverage": coverage,
        "kg_root": str(root),
    }


def _hit_match_score(hit: Dict[str, Any], case: Dict[str, Any]) -> float:
    expected_keywords = [str(x).strip() for x in (case.get("expected_keywords") or []) if str(x).strip()]
    expected_domain = str(case.get("expected_domain") or "").strip().lower()

    title = str(hit.get("title") or "")
    snippet = str(hit.get("snippet") or "")
    keywords_blob = " ".join([str(x) for x in (hit.get("keywords") or []) if str(x).strip()])
    tags_blob = " ".join([str(x) for x in (hit.get("qt_tag") or []) if str(x).strip()])
    payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
    payload_blob = json.dumps(payload, ensure_ascii=False) if payload else ""
    merged = f"{title} {snippet} {keywords_blob} {tags_blob} {payload_blob}".lower()
    score = 0.0
    if expected_keywords:
        score += sum(1.0 for kw in expected_keywords if kw.lower() in merged)
    if expected_domain:
        domains = {str(x).strip().lower() for x in (hit.get("professional_domain_matches") or []) if str(x).strip()}
        dom_text = str(hit.get("professional_domain") or "").strip().lower()
        if dom_text:
            domains.add(dom_text)
        aliases = DOMAIN_ALIASES.get(expected_domain, {expected_domain})
        if domains.intersection(aliases):
            score += 1.0
    return score


def run_retrieval_benchmark(
    *,
    db_path: Path | str,
    dataset_path: Path | str = DEFAULT_DATASET_PATH,
    top_k: int = 5,
    min_pass_rate: float = 0.85,
    min_avg_mrr: float = 0.65,
) -> Dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    cases = dataset.get("cases") or []
    rows: List[Dict[str, Any]] = []
    passed = 0
    mrr_sum = 0.0
    domain_stats: Dict[str, Dict[str, Any]] = {}

    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            continue
        query = str(case.get("query") or "").strip()
        if not query:
            continue
        result = search_graph_index(
            query=query,
            top_k=max(3, int(top_k)),
            db_path=db_path,
            resolve_authority=True,
        )
        hits = result.get("results") or []
        rank = 0
        score = 0.0
        best_score = 0.0
        for i, hit in enumerate(hits, start=1):
            if not isinstance(hit, dict):
                continue
            s = _hit_match_score(hit, case)
            best_score = max(best_score, s)
            if s <= 0:
                continue
            rank = i
            score = s
            break
        ok = rank > 0
        if ok:
            passed += 1
            mrr_sum += 1.0 / rank
        domain = _case_domain(case)
        row = domain_stats.setdefault(
            domain,
            {"domain": domain, "total": 0, "passed": 0, "mrr_sum": 0.0},
        )
        row["total"] = int(row["total"]) + 1
        if ok:
            row["passed"] = int(row["passed"]) + 1
            row["mrr_sum"] = float(row["mrr_sum"]) + (1.0 / rank)
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
                "best_score": round(best_score, 4),
                "top_total": len(hits),
                "domain": domain,
                "top_node_id": (hits[rank - 1].get("node_id") if rank > 0 and rank - 1 < len(hits) else None),
            }
        )

    total = len(rows)
    pass_rate = round((passed / total), 6) if total > 0 else 0.0
    avg_mrr = round((mrr_sum / total), 6) if total > 0 else 0.0
    ok = bool(total > 0 and pass_rate >= float(min_pass_rate) and avg_mrr >= float(min_avg_mrr))
    domain_summary: List[Dict[str, Any]] = []
    for domain, row in sorted(domain_stats.items(), key=lambda x: (-int(x[1].get("total") or 0), x[0])):
        d_total = int(row.get("total") or 0)
        d_pass = int(row.get("passed") or 0)
        d_mrr = float(row.get("mrr_sum") or 0.0)
        domain_summary.append(
            {
                "domain": domain,
                "total_cases": d_total,
                "passed_cases": d_pass,
                "pass_rate": round(d_pass / max(d_total, 1), 6),
                "avg_mrr": round(d_mrr / max(d_total, 1), 6),
            }
        )
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
        "domain_summary": domain_summary,
        "rows": rows,
    }
