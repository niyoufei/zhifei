from __future__ import annotations

import math
from typing import Any, Dict, List

from backend.zhifei_autoplan.enterprise_params import pick_productivity
from backend.zhifei_autoplan.schedule_cpm import run_cpm


DEFAULT_PROCESS_ORDER = [
    "土方开挖",
    "土方回填",
    "钢筋绑扎",
    "模板安装",
    "混凝土浇筑",
    "防水施工",
    "砌体砌筑",
    "抹灰工程",
    "管道安装",
    "电气安装",
    "沥青路面施工",
    "路基施工",
    "通用施工工序",
]


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _norm_process_name(item: Dict[str, Any]) -> str:
    p = item.get("process") if isinstance(item.get("process"), dict) else {}
    name = str(p.get("name") or "").strip()
    if name:
        return name
    n = str(item.get("name") or "").strip()
    mapping = [
        ("混凝土", "混凝土浇筑"),
        ("钢筋", "钢筋绑扎"),
        ("模板", "模板安装"),
        ("回填", "土方回填"),
        ("开挖", "土方开挖"),
        ("管", "管道安装"),
        ("电缆", "电气安装"),
        ("防水", "防水施工"),
        ("抹灰", "抹灰工程"),
        ("砌", "砌体砌筑"),
        ("沥青", "沥青路面施工"),
        ("路基", "路基施工"),
    ]
    for kw, pn in mapping:
        if kw in n:
            return pn
    return "通用施工工序"


def _extract_resource_count(item: Dict[str, Any]) -> float:
    resources = item.get("resources") if isinstance(item.get("resources"), list) else []
    if not resources:
        return 1.0
    return float(max(1, len(resources)))


def _group_to_wbs(items: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for it in items:
        pname = _norm_process_name(it)
        grp = groups.setdefault(
            pname,
            {
                "process": pname,
                "item_count": 0,
                "quantity": 0.0,
                "total_price": 0.0,
                "resource_units": 0.0,
                "resource_names": set(),
                "samples": [],
            },
        )
        qty = _f(it.get("quantity"), 0.0)
        total_price = _f(it.get("total_price"), 0.0)
        grp["item_count"] += 1
        grp["quantity"] += max(0.0, qty)
        grp["total_price"] += max(0.0, total_price)
        grp["resource_units"] += _extract_resource_count(it)
        for r in (it.get("resources") or []):
            if isinstance(r, dict):
                rn = str(r.get("name") or "").strip()
                if rn:
                    grp["resource_names"].add(rn)
        if len(grp["samples"]) < 3:
            name = str(it.get("name") or "").strip()
            if name:
                grp["samples"].append(name)

    rows: List[Dict[str, Any]] = []
    order_map = {name: i for i, name in enumerate(DEFAULT_PROCESS_ORDER)}
    for pname, g in groups.items():
        prod = pick_productivity(profile, pname)
        speed = max(0.01, _f(prod.get("value"), 1.0))
        qty = float(g.get("quantity") or 0.0)
        # If quantity is unavailable, use item count as conservative quantity proxy.
        q_for_calc = qty if qty > 0 else float(g.get("item_count") or 1)
        duration = max(1.0, q_for_calc / speed)
        rows.append(
            {
                "process": pname,
                "order": int(order_map.get(pname, 999)),
                "item_count": int(g.get("item_count") or 0),
                "quantity": round(qty, 3),
                "total_price": round(float(g.get("total_price") or 0.0), 2),
                "resource_units": round(float(g.get("resource_units") or 0.0), 3),
                "resource_names": sorted(list(g.get("resource_names") or [])),
                "samples": list(g.get("samples") or []),
                "productivity": {
                    "value": round(speed, 4),
                    "unit": str(prod.get("unit") or "项/天"),
                },
                "duration_days": round(float(duration), 3),
            }
        )
    rows.sort(key=lambda x: (int(x.get("order") or 999), -float(x.get("total_price") or 0.0), str(x.get("process") or "")))
    return rows


def _build_activity_graph(wbs_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    activities: List[Dict[str, Any]] = []
    for i, row in enumerate(wbs_rows):
        aid = f"WBS-{i + 1:03d}"
        deps: List[str] = []
        if i > 0:
            deps.append(f"WBS-{i:03d}")
        activities.append(
            {
                "id": aid,
                "name": str(row.get("process") or aid),
                "duration_days": max(0.1, _f(row.get("duration_days"), 1.0)),
                "resource_units": max(1.0, _f(row.get("resource_units"), 1.0)),
                "deps": deps,
                "source_text": " ".join([str(x) for x in (row.get("samples") or [])]),
                "source": {
                    "quantity": row.get("quantity"),
                    "productivity": row.get("productivity"),
                    "total_price": row.get("total_price"),
                },
            }
        )
    return activities


def build_boq_wbs_cpm(
    boq_data: Dict[str, Any] | None,
    *,
    enterprise_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Deterministic chain:
    清单 -> 工序聚类 -> WBS -> 资源估算 -> CPM/关键线路.
    """
    profile = enterprise_profile if isinstance(enterprise_profile, dict) else {}
    boq = boq_data if isinstance(boq_data, dict) else {}
    raw_items = boq.get("items") if isinstance(boq.get("items"), list) else []
    items = [it for it in raw_items if isinstance(it, dict)]
    if not items:
        return {
            "ok": False,
            "reason": "boq_items_empty",
            "wbs": [],
            "activities": [],
            "cpm": run_cpm([]),
            "summary": {
                "process_count": 0,
                "total_quantity": 0.0,
                "total_price": 0.0,
                "estimated_duration_days": 0.0,
            },
        }

    wbs_rows = _group_to_wbs(items, profile)
    activities = _build_activity_graph(wbs_rows)
    cpm = run_cpm(activities)
    total_quantity = sum(_f(x.get("quantity"), 0.0) for x in wbs_rows)
    total_price = sum(_f(x.get("total_price"), 0.0) for x in wbs_rows)
    duration_days = _f(cpm.get("project_duration_days"), 0.0)

    critical_names = []
    cp_ids = cpm.get("critical_path") if isinstance(cpm.get("critical_path"), list) else []
    by_id = {str(a.get("id") or ""): a for a in activities}
    for aid in cp_ids:
        nm = str((by_id.get(str(aid)) or {}).get("name") or "").strip()
        if nm:
            critical_names.append(nm)

    summary = {
        "process_count": int(len(wbs_rows)),
        "total_quantity": round(total_quantity, 3),
        "total_price": round(total_price, 2),
        "estimated_duration_days": round(duration_days, 3),
        "resource_peak": _f(cpm.get("resource_peak"), 0.0),
        "critical_interval_days": _f(cpm.get("critical_interval_days"), 0.0),
        "critical_path_names": critical_names,
    }

    # Add a simple deterministic WBS tree path for downstream exports.
    for i, row in enumerate(wbs_rows):
        row["wbs_id"] = f"1.{i + 1}"
        row["wbs_path"] = f"施工组织设计/{row.get('process')}"

    return {
        "ok": True,
        "wbs": wbs_rows,
        "activities": activities,
        "cpm": cpm,
        "summary": summary,
    }
