from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_CATALOG: Dict[str, Dict[str, Any]] = {
    "GB50300": {"latest_code": "GB 50300-2024", "latest_year": 2024, "tier": "国标"},
    "GB50204": {"latest_code": "GB 50204-2015", "latest_year": 2015, "tier": "国标"},
    "GB50202": {"latest_code": "GB 50202-2018", "latest_year": 2018, "tier": "国标"},
    "GB50303": {"latest_code": "GB 50303-2015", "latest_year": 2015, "tier": "国标"},
    "GB50242": {"latest_code": "GB 50242-2002", "latest_year": 2002, "tier": "国标"},
    "GBT50326": {"latest_code": "GB/T 50326-2017", "latest_year": 2017, "tier": "国标"},
    "JGJ59": {"latest_code": "JGJ 59-2011", "latest_year": 2011, "tier": "行标"},
    "JGJ120": {"latest_code": "JGJ 120-2012", "latest_year": 2012, "tier": "行标"},
    "SL176": {"latest_code": "SL 176-2007", "latest_year": 2007, "tier": "行标"},
    "SL398": {"latest_code": "SL 398-2007", "latest_year": 2007, "tier": "行标"},
    "TB10302": {"latest_code": "TB 10302-2020", "latest_year": 2020, "tier": "行标"},
    "TB10424": {"latest_code": "TB 10424-2018", "latest_year": 2018, "tier": "行标"},
    "JTGT3650": {"latest_code": "JTG/T 3650-2020", "latest_year": 2020, "tier": "行标"},
    "JTGT3660": {"latest_code": "JTG/T 3660-2020", "latest_year": 2020, "tier": "行标"},
}


def _normalize_code_key(code: str) -> str:
    text = re.sub(r"\s+", "", str(code or "").upper())
    m = re.search(r"([A-Z]+(?:/[A-Z])?)(\d{3,6})", text)
    if not m:
        return ""
    prefix = m.group(1).replace("/", "")
    digits = m.group(2)
    return f"{prefix}{digits}"


def _extract_year(code: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(code or ""))
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _iter_nodes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    kg = payload.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    out: List[Dict[str, Any]] = []
    for section in kg.values():
        if not isinstance(section, dict):
            continue
        nodes = section.get("nodes")
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if isinstance(node, dict):
                out.append(node)
    return out


def load_standard_catalog(catalog_path: Path | str | None = None) -> Dict[str, Dict[str, Any]]:
    if not catalog_path:
        return dict(DEFAULT_CATALOG)
    p = Path(catalog_path).expanduser().resolve()
    if not p.exists():
        return dict(DEFAULT_CATALOG)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_CATALOG)
    if not isinstance(raw, dict):
        return dict(DEFAULT_CATALOG)
    merged = dict(DEFAULT_CATALOG)
    for key, value in raw.items():
        k = str(key).strip()
        if not k or not isinstance(value, dict):
            continue
        merged[k] = dict(value)
    return merged


def refresh_node_standard_state(
    node: Dict[str, Any],
    *,
    catalog: Dict[str, Dict[str, Any]],
    now_year: int | None = None,
) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    year_now = int(now_year or time.strftime("%Y", time.localtime()))

    ref_codes = [str(x).strip() for x in _as_list(node.get("reference_standard_codes")) if str(x).strip()]
    if not ref_codes:
        ref_codes = [str(x).strip() for x in _as_list(node.get("reference_standard")) if str(x).strip()]
    if not ref_codes:
        return False, {"updated": 0, "superseded": 0}

    rows: List[Dict[str, Any]] = []
    superseded_count = 0
    updated_count = 0
    normalized_codes: List[str] = []
    for code in ref_codes:
        key = _normalize_code_key(code)
        cur_year = _extract_year(code)
        item = catalog.get(key, {})
        latest_code = str(item.get("latest_code") or code).strip() or code
        latest_year = int(item.get("latest_year") or (cur_year or year_now))
        tier = str(item.get("tier") or "").strip() or str(node.get("source_hierarchy") or "未知")
        status = "active"
        replacement = ""
        if cur_year is not None and latest_year > cur_year:
            status = "superseded"
            replacement = latest_code
            superseded_count += 1
            normalized_codes.append(latest_code)
            if latest_code != code:
                updated_count += 1
        else:
            normalized_codes.append(code)

        rows.append(
            {
                "code": code,
                "key": key,
                "current_year": cur_year,
                "latest_code": latest_code,
                "latest_year": latest_year,
                "tier": tier,
                "status": status,
                "replacement": replacement,
            }
        )

    dedup: List[str] = []
    seen = set()
    for code in normalized_codes:
        k = code.strip()
        if not k:
            continue
        low = k.lower()
        if low in seen:
            continue
        seen.add(low)
        dedup.append(k)
    if node.get("reference_standard_codes") != dedup:
        node["reference_standard_codes"] = dedup
        changed = True

    timeline = node.get("standard_validity_timeline")
    timeline_dict = dict(timeline) if isinstance(timeline, dict) else {}
    recs = timeline_dict.get("records")
    if not isinstance(recs, list):
        recs = []
    record_map = {
        _normalize_code_key(str(rec.get("standard_code") or "")): rec
        for rec in recs
        if isinstance(rec, dict)
    }
    timeline_rows: List[Dict[str, Any]] = []
    for row in rows:
        key = row.get("key") or ""
        old = record_map.get(key, {})
        latest_year = int(row.get("latest_year") or year_now)
        cycle = int(old.get("review_cycle_years") or (10 if row.get("tier") == "国标" else 8))
        effective_year = int(old.get("effective_date", f"{latest_year}-01-01")[:4]) if old else latest_year
        expiry_year = effective_year + cycle
        status = str(row.get("status") or "active")
        if status == "active" and expiry_year < year_now:
            status = "review_required"
        timeline_row = {
            "standard_code": str(row.get("latest_code") or row.get("code") or ""),
            "tier": str(row.get("tier") or old.get("tier") or ""),
            "effective_date": f"{effective_year}-01-01",
            "expiry_date": f"{expiry_year}-12-31",
            "review_cycle_years": cycle,
            "status": status,
        }
        if row.get("replacement"):
            timeline_row["superseded_by"] = str(row.get("replacement"))
        timeline_rows.append(timeline_row)

    timeline_status = "active" if all(str(x.get("status") or "") == "active" for x in timeline_rows) else "review_required"
    state = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "catalog_version": "v1",
        "checked_codes": len(rows),
        "superseded_count": superseded_count,
        "updated_count": updated_count,
        "status": "updated" if updated_count > 0 else "up_to_date",
        "details": rows,
    }
    if node.get("standard_update_state") != state:
        node["standard_update_state"] = state
        changed = True

    if timeline_rows:
        timeline_dict["records"] = timeline_rows
        timeline_dict["timeline_status"] = timeline_status
        if node.get("standard_validity_timeline") != timeline_dict:
            node["standard_validity_timeline"] = timeline_dict
            changed = True

    return changed, {"updated": updated_count, "superseded": superseded_count}


def refresh_kg_standards(
    *,
    kg_root: Path | str,
    pattern: str = "ZF-KG-*.json",
    catalog_path: Path | str | None = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    root = Path(kg_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"kg root not found: {root}")
    catalog = load_standard_catalog(catalog_path)
    files = sorted(root.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no files matched: {root}/{pattern}")

    files_changed = 0
    nodes_checked = 0
    nodes_updated = 0
    superseded_total = 0
    file_rows: List[Dict[str, Any]] = []

    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        changed = False
        file_nodes = 0
        file_updated = 0
        file_superseded = 0
        for node in _iter_nodes(raw):
            file_nodes += 1
            nodes_checked += 1
            node_changed, stat = refresh_node_standard_state(node, catalog=catalog)
            if node_changed:
                changed = True
                nodes_updated += 1
                file_updated += 1
            file_superseded += int(stat.get("superseded") or 0)
            superseded_total += int(stat.get("superseded") or 0)

        if changed:
            files_changed += 1
            if not dry_run:
                path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        file_rows.append(
            {
                "file": path.name,
                "changed": changed,
                "nodes": file_nodes,
                "nodes_updated": file_updated,
                "superseded": file_superseded,
            }
        )

    return {
        "ok": True,
        "kg_root": str(root),
        "files_total": len(files),
        "files_changed": files_changed,
        "nodes_checked": nodes_checked,
        "nodes_updated": nodes_updated,
        "superseded_total": superseded_total,
        "catalog_size": len(catalog),
        "files": file_rows,
    }

