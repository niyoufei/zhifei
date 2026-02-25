from __future__ import annotations

import math
import re
from statistics import median
from typing import Any, Dict, List, Tuple

import networkx as nx


_DUR_RE = re.compile(r"工期[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|月|h|小时)", re.IGNORECASE)
_PEAK_RE = re.compile(r"(?:资源峰值|高峰投入|投入人员|投入设备|人数)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(人|台|套)", re.IGNORECASE)
_CP_RE = re.compile(r"关键线路(?:间隔|步距)?[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|h|小时)", re.IGNORECASE)
_DEP_RE = re.compile(r"(?:前置|依赖|需在|在)[：:\s]*([^。；;\n]{2,80})(?:后|完成后|之后)")


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _to_days(val: float, unit: str) -> float:
    u = str(unit or "").strip().lower()
    if u in {"天", "日", "d"}:
        return float(val)
    if u in {"月"}:
        return float(val) * 30.0
    if u in {"h", "小时"}:
        return float(val) / 24.0
    return float(val)


def _fmt_days(v: float) -> str:
    fv = float(v)
    if abs(fv - round(fv)) < 1e-9:
        return f"{int(round(fv))}天"
    return f"{round(fv, 2)}天"


def _extract_first_duration_days(text: str) -> float | None:
    m = _DUR_RE.search(text or "")
    if not m:
        return None
    return max(0.01, _to_days(_f(m.group(1)), m.group(2)))


def _extract_first_resource(text: str) -> float | None:
    m = _PEAK_RE.search(text or "")
    if not m:
        return None
    return max(0.0, _f(m.group(1)))


def _pick_most_common_metric(sections: List[Dict[str, Any]], regex: re.Pattern[str], to_days: bool = False) -> Dict[str, Any] | None:
    bucket: Dict[str, Dict[str, Any]] = {}
    for sec in sections or []:
        title = str(sec.get("title") or "").strip() or "章节"
        text = str(sec.get("content") or "")
        for m in regex.finditer(text):
            raw_num = _f(m.group(1))
            unit = str(m.group(2) or "")
            val = _to_days(raw_num, unit) if to_days else raw_num
            k = f"{round(val, 6)}::{unit}"
            rec = bucket.setdefault(k, {"value": val, "unit": unit, "count": 0, "titles": []})
            rec["count"] += 1
            rec["titles"].append(title)
    if not bucket:
        return None
    best = max(
        bucket.values(),
        key=lambda x: (
            int(x.get("count") or 0),
            1 if any(k in " ".join(x.get("titles") or []) for k in ("进度", "工期", "计划", "资源", "关键线路")) else 0,
        ),
    )
    return best


def _title_aliases(name: str) -> List[str]:
    t = str(name or "").strip()
    if not t:
        return []
    out = [t]
    for r in ("施工", "工序", "作业", "计划", "方案", "措施", "章", "第"):
        out.append(t.replace(r, ""))
    return [x for x in out if x]


def _infer_dependencies(activities: List[Dict[str, Any]]) -> None:
    id_by_name: Dict[str, str] = {}
    for a in activities:
        aid = str(a.get("id") or "")
        name = str(a.get("name") or "")
        if aid and name:
            id_by_name[name] = aid

    for idx, a in enumerate(activities):
        deps = set()
        text = str(a.get("source_text") or "")
        for m in _DEP_RE.finditer(text):
            raw = str(m.group(1) or "")
            parts = re.split(r"[、,，/→\-\s]+", raw)
            for p in parts:
                token = str(p or "").strip()
                if len(token) < 2:
                    continue
                for prev in activities[:idx]:
                    pid = str(prev.get("id") or "")
                    pname = str(prev.get("name") or "")
                    if not pid or not pname:
                        continue
                    aliases = _title_aliases(pname)
                    if any(token in alias or alias in token for alias in aliases if alias):
                        deps.add(pid)
        if not deps and idx > 0:
            deps.add(str(activities[idx - 1].get("id") or ""))
        a["deps"] = [d for d in deps if d and d != str(a.get("id") or "")]


def build_activities_from_sections(
    sections: List[Dict[str, Any]],
    *,
    mentioned_total_days: float | None = None,
    mentioned_peak: float | None = None,
) -> List[Dict[str, Any]]:
    activities: List[Dict[str, Any]] = []
    for i, sec in enumerate(sections or []):
        title = str(sec.get("title") or "").strip()
        text = str(sec.get("content") or "")
        if not title:
            continue
        dur_local = _extract_first_duration_days(text)
        res_local = _extract_first_resource(text)
        activities.append(
            {
                "id": f"A{i + 1:03d}",
                "name": title,
                "duration_days": dur_local,
                "resource_units": res_local,
                "source_text": text[:4000],
                "duration_source": "section_metric" if dur_local is not None else "derived",
                "resource_source": "section_metric" if res_local is not None else "derived",
                "deps": [],
            }
        )

    if not activities:
        return []

    known_duration = [float(a["duration_days"]) for a in activities if a.get("duration_days") is not None]
    missing_idx = [i for i, a in enumerate(activities) if a.get("duration_days") is None]
    known_sum = sum(known_duration)
    if missing_idx:
        if mentioned_total_days is not None and mentioned_total_days > known_sum:
            rem = max(0.01, float(mentioned_total_days) - known_sum)
            share = max(0.1, rem / max(1, len(missing_idx)))
        else:
            share = max(0.5, (known_sum / max(1, len(known_duration))) if known_duration else 1.0)
        for idx in missing_idx:
            activities[idx]["duration_days"] = round(share, 3)
            activities[idx]["duration_source"] = "distributed"

    known_resource = [float(a["resource_units"]) for a in activities if a.get("resource_units") is not None]
    fill_resource = float(mentioned_peak) if (mentioned_peak is not None and mentioned_peak > 0) else (median(known_resource) if known_resource else 0.0)
    for a in activities:
        if a.get("resource_units") is None:
            a["resource_units"] = round(float(fill_resource), 3)
            a["resource_source"] = "distributed"

    _infer_dependencies(activities)
    return activities


def _build_graph(activities: List[Dict[str, Any]]) -> Tuple[nx.DiGraph, List[Tuple[str, str]]]:
    g = nx.DiGraph()
    ids = {str(a.get("id") or "") for a in activities}
    for a in activities:
        aid = str(a.get("id") or "")
        if not aid:
            continue
        g.add_node(aid)
    for a in activities:
        aid = str(a.get("id") or "")
        if not aid:
            continue
        for dep in a.get("deps") or []:
            d = str(dep or "")
            if d and d in ids and d != aid:
                g.add_edge(d, aid)

    removed: List[Tuple[str, str]] = []
    if nx.is_directed_acyclic_graph(g):
        return g, removed

    h = g.copy()
    guard = 0
    while not nx.is_directed_acyclic_graph(h) and guard < 5000:
        guard += 1
        cyc = nx.find_cycle(h, orientation="original")
        if not cyc:
            break
        u, v, *_ = cyc[-1]
        if h.has_edge(u, v):
            h.remove_edge(u, v)
            removed.append((str(u), str(v)))
    return h, removed


def run_cpm(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not activities:
        return {
            "ok": False,
            "reason": "no_activities",
            "activities": [],
            "critical_path": [],
            "project_duration_days": 0.0,
            "resource_peak": 0.0,
            "critical_interval_days": 0.0,
            "graph": {"node_count": 0, "edge_count": 0, "cycle_edges_removed": []},
        }

    g, cycle_removed = _build_graph(activities)
    order = list(nx.topological_sort(g))
    by_id = {str(a.get("id") or ""): a for a in activities}
    dur = {aid: max(0.01, _f((by_id.get(aid) or {}).get("duration_days"), 1.0)) for aid in order}

    es: Dict[str, float] = {}
    ef: Dict[str, float] = {}
    for n in order:
        preds = list(g.predecessors(n))
        es[n] = max((ef.get(p, 0.0) for p in preds), default=0.0)
        ef[n] = es[n] + dur[n]

    project_duration = max(ef.values()) if ef else 0.0
    ls: Dict[str, float] = {}
    lf: Dict[str, float] = {}
    for n in reversed(order):
        succ = list(g.successors(n))
        lf[n] = min((ls[s] for s in succ), default=project_duration)
        ls[n] = lf[n] - dur[n]

    # Longest path by node durations
    best_end = max(order, key=lambda n: ef.get(n, 0.0))
    best_pred: Dict[str, str | None] = {}
    best_len: Dict[str, float] = {}
    for n in order:
        preds = list(g.predecessors(n))
        if not preds:
            best_pred[n] = None
            best_len[n] = dur[n]
        else:
            p = max(preds, key=lambda x: best_len.get(x, 0.0))
            best_pred[n] = p
            best_len[n] = best_len.get(p, 0.0) + dur[n]
    cp: List[str] = []
    cur: str | None = best_end
    while cur:
        cp.append(cur)
        cur = best_pred.get(cur)
    cp.reverse()

    timeline: Dict[int, float] = {}
    for n in order:
        rs = max(0.0, _f((by_id.get(n) or {}).get("resource_units"), 0.0))
        if rs <= 0:
            continue
        s = es.get(n, 0.0)
        e = ef.get(n, s)
        lo = int(math.floor(s))
        hi = int(math.ceil(e))
        for t in range(lo, max(lo + 1, hi)):
            timeline[t] = timeline.get(t, 0.0) + rs
    resource_peak = max(timeline.values()) if timeline else 0.0

    cp_starts = [es.get(n, 0.0) for n in cp]
    cp_diffs = [cp_starts[i + 1] - cp_starts[i] for i in range(len(cp_starts) - 1) if (cp_starts[i + 1] - cp_starts[i]) > 0]
    critical_interval = min(cp_diffs) if cp_diffs else 0.0

    activity_rows = []
    for n in order:
        a = by_id.get(n) or {}
        tf = (ls.get(n, 0.0) - es.get(n, 0.0))
        activity_rows.append(
            {
                "id": n,
                "name": a.get("name"),
                "deps": list(g.predecessors(n)),
                "duration_days": round(dur.get(n, 0.0), 3),
                "resource_units": round(_f(a.get("resource_units"), 0.0), 3),
                "es": round(es.get(n, 0.0), 3),
                "ef": round(ef.get(n, 0.0), 3),
                "ls": round(ls.get(n, 0.0), 3),
                "lf": round(lf.get(n, 0.0), 3),
                "total_float": round(tf, 3),
                "critical": abs(tf) <= 1e-6,
            }
        )

    return {
        "ok": True,
        "activities": activity_rows,
        "critical_path": cp,
        "project_duration_days": round(project_duration, 3),
        "resource_peak": round(resource_peak, 3),
        "critical_interval_days": round(critical_interval, 3),
        "graph": {
            "node_count": int(g.number_of_nodes()),
            "edge_count": int(g.number_of_edges()),
            "cycle_edges_removed": cycle_removed,
        },
    }


def _to_metric_days(s: str | None) -> float | None:
    txt = str(s or "").strip()
    if not txt:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(天|日|月|h|小时)?", txt, flags=re.IGNORECASE)
    if not m:
        return None
    return _to_days(_f(m.group(1)), m.group(2) or "天")


def _to_metric_num(s: str | None) -> float | None:
    txt = str(s or "").strip()
    if not txt:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", txt)
    if not m:
        return None
    return _f(m.group(1))


def _compare_metric(metric: str, mentioned: float | None, computed: float, tolerance: float) -> Dict[str, Any] | None:
    if mentioned is None:
        return None
    if abs(float(computed) - float(mentioned)) <= float(tolerance):
        return None
    return {
        "metric": metric,
        "mentioned": round(float(mentioned), 3),
        "computed": round(float(computed), 3),
        "tolerance": round(float(tolerance), 3),
        "delta": round(float(computed) - float(mentioned), 3),
    }


def build_cpm_receipt(sections: List[Dict[str, Any]], canonical: Dict[str, str] | None = None) -> Dict[str, Any]:
    canonical = canonical or {}
    dur_m = _pick_most_common_metric(sections, _DUR_RE, to_days=True)
    peak_m = _pick_most_common_metric(sections, _PEAK_RE, to_days=False)
    cp_m = _pick_most_common_metric(sections, _CP_RE, to_days=True)

    mentioned_duration_days = _to_metric_days(canonical.get("工期")) if canonical.get("工期") else (float(dur_m.get("value")) if dur_m else None)
    mentioned_peak = _to_metric_num(canonical.get("资源峰值")) if canonical.get("资源峰值") else (float(peak_m.get("value")) if peak_m else None)
    mentioned_cp_interval = _to_metric_days(canonical.get("关键线路间隔")) if canonical.get("关键线路间隔") else (float(cp_m.get("value")) if cp_m else None)

    activities = build_activities_from_sections(
        sections,
        mentioned_total_days=mentioned_duration_days,
        mentioned_peak=mentioned_peak,
    )
    cpm = run_cpm(activities)
    if not cpm.get("ok"):
        return {
            "ok": False,
            "algorithm": "networkx_cpm_v1",
            "reason": cpm.get("reason") or "cpm_failed",
            "mentioned": {
                "工期": canonical.get("工期") or (_fmt_days(float(dur_m.get("value"))) if dur_m else None),
                "资源峰值": canonical.get("资源峰值") or (f"{round(float(peak_m.get('value')), 3)}人/台/套" if peak_m else None),
                "关键线路间隔": canonical.get("关键线路间隔") or (_fmt_days(float(cp_m.get("value"))) if cp_m else None),
            },
            "computed": {},
            "conflicts": [],
            "graph": cpm.get("graph") or {},
            "activities": [],
            "critical_path": [],
        }

    computed_duration = float(cpm.get("project_duration_days") or 0.0)
    computed_peak = float(cpm.get("resource_peak") or 0.0)
    computed_interval = float(cpm.get("critical_interval_days") or 0.0)
    conflicts: List[Dict[str, Any]] = []
    c1 = _compare_metric("工期", mentioned_duration_days, computed_duration, tolerance=max(1.0, (mentioned_duration_days or 0.0) * 0.10))
    c2 = _compare_metric("资源峰值", mentioned_peak, computed_peak, tolerance=max(1.0, (mentioned_peak or 0.0) * 0.15))
    c3 = _compare_metric("关键线路间隔", mentioned_cp_interval, computed_interval, tolerance=max(0.5, (mentioned_cp_interval or 0.0) * 0.25))
    for x in (c1, c2, c3):
        if x:
            conflicts.append(x)

    critical_names = []
    by_id = {str(a.get("id") or ""): a for a in cpm.get("activities") or []}
    for aid in cpm.get("critical_path") or []:
        name = str((by_id.get(str(aid)) or {}).get("name") or str(aid)).strip()
        if name:
            critical_names.append(name)

    return {
        "ok": len(conflicts) == 0,
        "algorithm": "networkx_cpm_v1",
        "mentioned": {
            "工期": canonical.get("工期") or (_fmt_days(float(dur_m.get("value"))) if dur_m else None),
            "资源峰值": canonical.get("资源峰值") or (f"{round(float(peak_m.get('value')), 3)}人/台/套" if peak_m else None),
            "关键线路间隔": canonical.get("关键线路间隔") or (_fmt_days(float(cp_m.get("value"))) if cp_m else None),
        },
        "computed": {
            "project_duration_days": round(computed_duration, 3),
            "resource_peak": round(computed_peak, 3),
            "critical_interval_days": round(computed_interval, 3),
        },
        "conflicts": conflicts,
        "graph": cpm.get("graph") or {},
        "activities": cpm.get("activities") or [],
        "critical_path": critical_names,
    }
