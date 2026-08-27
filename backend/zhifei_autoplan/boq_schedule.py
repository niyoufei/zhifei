from __future__ import annotations

import math
import copy
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

# Scheduling must never turn a malformed spreadsheet identifier into an
# unbounded calendar.  The source value remains available in the stored BoQ;
# only the derived schedule excludes values outside this defensive envelope.
MAX_SCHEDULE_QUANTITY = 1_000_000_000_000.0
MAX_ACTIVITY_DURATION_DAYS = 36_500.0
# A BoQ-only CPM is an estimate, not an awarded contract fact. Durations above
# ten years remain visible for diagnostics but must not enter immutable project
# facts or prompts as an agreed construction period.
MAX_DERIVED_SCHEDULE_FACT_DAYS = 3_650.0


def _f(v: Any, default: float = 0.0) -> float:
    try:
        value = float(v)
        return value if math.isfinite(value) else float(default)
    except Exception:
        return float(default)


def _schedule_quantity(v: Any) -> float | None:
    try:
        value = float(v)
    except Exception:
        return None
    if not math.isfinite(value) or value <= 0 or value > MAX_SCHEDULE_QUANTITY:
        return None
    return value


def _quantity_is_anomalous(v: Any) -> bool:
    if v is None or (isinstance(v, str) and not v.strip()):
        return False
    try:
        value = float(v)
    except Exception:
        return True
    if value == 0:
        return False
    return not math.isfinite(value) or value < 0 or value > MAX_SCHEDULE_QUANTITY


def sanitize_boq_for_generation(boq_data: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return a generation-safe copy while retaining non-numeric source facts.

    Uploaded source files and the persisted parse receipt are never rewritten.
    Only the in-memory generation view excludes malformed quantities so they
    cannot leak into prompts, charts, quantitative indexes, or derived facts.
    """

    source = boq_data if isinstance(boq_data, dict) else {}
    if not source:
        return {}
    result = copy.deepcopy(source)
    rows = result.get("items") if isinstance(result.get("items"), list) else []
    valid_quantities: list[float] = []
    excluded = 0
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        quantity = raw.get("quantity")
        if _quantity_is_anomalous(quantity):
            raw["quantity"] = None
            raw["quantity_validation"] = {
                "status": "excluded",
                "code": "BOQ_QUANTITY_OUTLIER_EXCLUDED",
            }
            excluded += 1
            continue
        value = _schedule_quantity(quantity)
        if value is not None:
            valid_quantities.append(value)

    stats = dict(result.get("stats") or {})
    if excluded:
        total = sum(valid_quantities)
        stats["total_quantity"] = round(total, 6)
        stats["quantity_scale_index"] = round(
            min(1.0, math.log10(max(1.0, total) + 1.0) / 6.0), 4
        )
        stats["construction_density_index"] = round(
            min(1.0, (total / max(1, len(rows))) / 1500.0), 4
        )
        top_rows = sorted(
            (row for row in rows if isinstance(row, dict) and row.get("quantity") is not None),
            key=lambda row: float(row.get("quantity") or 0.0),
            reverse=True,
        )[:8]
        stats["top_quantity_items"] = [
            {
                key: row.get(key)
                for key in ("boq_code", "name", "quantity", "unit", "unit_price", "total_price")
            }
            for row in top_rows
        ]
    result["stats"] = stats
    result["runtime_validation"] = {
        "schema_version": "boq-runtime-validation-v1",
        "excluded_quantity_count": excluded,
        "generation_safe": True,
    }
    return result


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
                "excluded_quantity_count": 0,
            },
        )
        qty = _schedule_quantity(it.get("quantity"))
        total_price = _f(it.get("total_price"), 0.0)
        grp["item_count"] += 1
        if qty is None:
            if _quantity_is_anomalous(it.get("quantity")):
                grp["excluded_quantity_count"] += 1
        else:
            grp["quantity"] += qty
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
        raw_duration = max(1.0, q_for_calc / speed)
        duration_basis = "validated_quantity"
        if qty <= 0 or raw_duration > MAX_ACTIVITY_DURATION_DAYS:
            q_for_calc = float(g.get("item_count") or 1)
            raw_duration = max(1.0, q_for_calc / speed)
            duration_basis = "item_count_fallback"
        duration = min(MAX_ACTIVITY_DURATION_DAYS, raw_duration)
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
                "excluded_quantity_count": int(g.get("excluded_quantity_count") or 0),
                "duration_basis": duration_basis,
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
                "schedule_fact_eligible": False,
                "schedule_fact_reasons": ["boq_items_empty"],
            },
        }

    wbs_rows = _group_to_wbs(items, profile)
    activities = _build_activity_graph(wbs_rows)
    cpm = run_cpm(activities)
    total_quantity = sum(_f(x.get("quantity"), 0.0) for x in wbs_rows)
    total_price = sum(_f(x.get("total_price"), 0.0) for x in wbs_rows)
    duration_days = _f(cpm.get("project_duration_days"), 0.0)
    excluded_quantity_count = sum(
        int(row.get("excluded_quantity_count") or 0) for row in wbs_rows
    )

    critical_names = []
    cp_ids = cpm.get("critical_path") if isinstance(cpm.get("critical_path"), list) else []
    by_id = {str(a.get("id") or ""): a for a in activities}
    for aid in cp_ids:
        nm = str((by_id.get(str(aid)) or {}).get("name") or "").strip()
        if nm:
            critical_names.append(nm)

    schedule_fact_reasons: List[str] = []
    if duration_days <= 0:
        schedule_fact_reasons.append("derived_duration_missing")
    elif duration_days > MAX_DERIVED_SCHEDULE_FACT_DAYS:
        schedule_fact_reasons.append("derived_duration_implausible")

    summary = {
        "process_count": int(len(wbs_rows)),
        "total_quantity": round(total_quantity, 3),
        "total_price": round(total_price, 2),
        "estimated_duration_days": round(duration_days, 3),
        "resource_peak": _f(cpm.get("resource_peak"), 0.0),
        "critical_interval_days": _f(cpm.get("critical_interval_days"), 0.0),
        "critical_path_names": critical_names,
        "excluded_quantity_count": excluded_quantity_count,
        "schedule_fact_eligible": not schedule_fact_reasons,
        "schedule_fact_reasons": schedule_fact_reasons,
    }

    # Add a simple deterministic WBS tree path for downstream exports.
    for i, row in enumerate(wbs_rows):
        row["wbs_id"] = f"1.{i + 1}"
        row["wbs_path"] = f"施工组织设计/{row.get('process')}"

    warnings = []
    if excluded_quantity_count:
        warnings.append(
            {
                "code": "BOQ_QUANTITY_OUTLIER_EXCLUDED",
                "count": excluded_quantity_count,
            }
        )
    if "derived_duration_implausible" in schedule_fact_reasons:
        warnings.append(
            {
                "code": "BOQ_DERIVED_SCHEDULE_IMPLAUSIBLE",
                "estimated_duration_days": round(duration_days, 3),
                "fact_limit_days": MAX_DERIVED_SCHEDULE_FACT_DAYS,
            }
        )

    return {
        "ok": True,
        "wbs": wbs_rows,
        "activities": activities,
        "cpm": cpm,
        "summary": summary,
        "schedule_input_warnings": warnings,
    }
