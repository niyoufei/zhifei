from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import ezdxf
except Exception:  # pragma: no cover - runtime fallback when ezdxf is missing
    ezdxf = None


_DOMAIN_SEEDS: Dict[str, Tuple[str, ...]] = {
    "bridge": ("bridge", "桥", "箱梁", "盖梁", "桥墩", "桥面", "预应力"),
    "tunnel": ("tunnel", "隧道", "洞门", "衬砌", "盾构", "暗挖"),
    "hydraulic": ("hydraulic", "水利", "泵站", "闸门", "河道", "堤防", "引水"),
    "mep": ("mep", "机电", "电气", "暖通", "消防", "给排水", "桥架"),
    "earthwork": ("earthwork", "土方", "土石方", "基坑", "边坡", "回填"),
    "road": ("road", "道路", "路基", "路面", "沥青", "排水"),
    "building": ("building", "房建", "主体", "砌体", "幕墙", "装修"),
}


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _safe_round(v: Any, n: int = 3) -> float:
    return round(_to_float(v), n)


def _infer_domain(*parts: str) -> str:
    text = " ".join([str(p or "") for p in parts]).lower()
    for domain, seeds in _DOMAIN_SEEDS.items():
        if any(seed.lower() in text for seed in seeds):
            return domain
    return "general"


def _entity_layer(ent: Any) -> str:
    layer = str(getattr(getattr(ent, "dxf", None), "layer", "") or "").strip()
    return layer or "0"


def _entity_handle(ent: Any) -> str:
    return str(getattr(getattr(ent, "dxf", None), "handle", "") or "").strip()


def _entity_type(ent: Any) -> str:
    try:
        return str(ent.dxftype() or "").upper()
    except Exception:
        return "UNKNOWN"


def _point_dict(x: Any, y: Any) -> Dict[str, float]:
    return {"x": _safe_round(x), "y": _safe_round(y)}


def _entity_position(ent: Any) -> Dict[str, float]:
    dxf = getattr(ent, "dxf", None)
    for key in ("insert", "location", "center", "defpoint"):
        pt = getattr(dxf, key, None)
        if pt is None:
            continue
        x = getattr(pt, "x", None)
        y = getattr(pt, "y", None)
        if x is None or y is None:
            continue
        return _point_dict(x, y)
    return {}


def _text_value(ent: Any) -> str:
    et = _entity_type(ent)
    if et == "TEXT":
        return str(getattr(getattr(ent, "dxf", None), "text", "") or "").strip()
    if et == "MTEXT":
        try:
            return str(ent.plain_text() or "").strip()
        except Exception:
            return str(getattr(ent, "text", "") or "").strip()
    if et == "ATTRIB":
        return str(getattr(getattr(ent, "dxf", None), "text", "") or "").strip()
    return ""


def _text_category(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return "drawing_text"
    if any(k in s for k in ("设计总说明", "总说明", "施工说明", "说明")):
        return "design_general_notes"
    if any(k in s for k in ("技术要求", "施工要求", "质量要求", "验收要求", "规范")):
        return "technical_requirement"
    if any(k in s for k in ("项目名称", "工程名称", "图名", "图号", "比例", "SCALE", "PROJECT")):
        return "title_block_info"
    if any(k in s for k in ("详图", "剖面", "节点", "大样", "立面", "平面")):
        return "leader_annotation"
    return "drawing_text"


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _parse_project_name(texts: List[str]) -> str:
    patterns = (
        r"(?:项目名称|工程名称|PROJECT\s*NAME)[：:\s]+(.{2,80})",
        r"^(.{2,80})(?:施工图|设计图)$",
    )
    for t in texts:
        line = _clean_text(t)
        for p in patterns:
            m = re.search(p, line, flags=re.IGNORECASE)
            if m:
                name = _clean_text(m.group(1))
                name = re.sub(r"[；;，,。]+$", "", name)
                if 2 <= len(name) <= 80:
                    return name
    return ""


def _parse_drawing_scale(texts: List[str]) -> str:
    for t in texts:
        line = _clean_text(t)
        m = re.search(r"(?:比例|SCALE)[：:\s]*([0-9]{1,3}\s*[:：]\s*[0-9]{1,6})", line, flags=re.IGNORECASE)
        if m:
            return m.group(1).replace(" ", "").replace("：", ":")
    return ""


def _parse_title_block(text_records: List[Dict[str, Any]], blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    texts = [str(r.get("text") or "") for r in text_records]
    project_name = _parse_project_name(texts)
    drawing_scale = _parse_drawing_scale(texts)

    drawing_no = ""
    for t in texts:
        line = _clean_text(t)
        m = re.search(r"(?:图号|DRAWING\s*NO\.?)[：:\s]*([A-Za-z0-9\-_./]+)", line, flags=re.IGNORECASE)
        if m:
            drawing_no = m.group(1).strip()
            break

    title_block_candidates = [b for b in blocks if any(k in str(b.get("block_name") or "").lower() for k in ("title", "图框"))]
    title_block_name = str(title_block_candidates[0].get("block_name") or "").strip() if title_block_candidates else ""

    out: Dict[str, Any] = {}
    if project_name:
        out["project_name"] = project_name
    if drawing_scale:
        out["drawing_scale"] = drawing_scale
    if drawing_no:
        out["drawing_no"] = drawing_no
    if title_block_name:
        out["title_block_name"] = title_block_name
    return out


def _line_feature(ent: Any, layer: str) -> Dict[str, Any]:
    s = getattr(getattr(ent, "dxf", None), "start", None)
    e = getattr(getattr(ent, "dxf", None), "end", None)
    sx = _to_float(getattr(s, "x", 0.0))
    sy = _to_float(getattr(s, "y", 0.0))
    ex = _to_float(getattr(e, "x", 0.0))
    ey = _to_float(getattr(e, "y", 0.0))
    return {
        "entity_type": "LINE",
        "layer": layer,
        "start": _point_dict(sx, sy),
        "end": _point_dict(ex, ey),
        "length": round(math.hypot(ex - sx, ey - sy), 3),
    }


def _polyline_feature(ent: Any, layer: str, etype: str) -> Dict[str, Any]:
    points: List[Tuple[float, float]] = []
    if etype == "LWPOLYLINE":
        try:
            for p in ent.get_points("xy"):
                points.append((_to_float(p[0]), _to_float(p[1])))
        except Exception:
            points = []
        closed = bool(getattr(ent, "closed", False))
    else:
        try:
            for v in ent.vertices:
                loc = v.dxf.location
                points.append((_to_float(getattr(loc, "x", 0.0)), _to_float(getattr(loc, "y", 0.0))))
        except Exception:
            points = []
        closed = bool(getattr(ent, "is_closed", False))
    length = 0.0
    if len(points) >= 2:
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            length += math.hypot(bx - ax, by - ay)
        if closed and len(points) >= 3:
            ax, ay = points[-1]
            bx, by = points[0]
            length += math.hypot(bx - ax, by - ay)
    return {
        "entity_type": etype,
        "layer": layer,
        "vertex_count": len(points),
        "closed": closed,
        "length": round(length, 3),
    }


def _circle_feature(ent: Any, layer: str) -> Dict[str, Any]:
    c = getattr(getattr(ent, "dxf", None), "center", None)
    r = abs(_to_float(getattr(getattr(ent, "dxf", None), "radius", 0.0)))
    return {
        "entity_type": "CIRCLE",
        "layer": layer,
        "center": _point_dict(getattr(c, "x", 0.0), getattr(c, "y", 0.0)),
        "radius": round(r, 3),
        "circumference": round(2.0 * math.pi * r, 3),
    }


def _arc_feature(ent: Any, layer: str) -> Dict[str, Any]:
    c = getattr(getattr(ent, "dxf", None), "center", None)
    r = abs(_to_float(getattr(getattr(ent, "dxf", None), "radius", 0.0)))
    sa = _to_float(getattr(getattr(ent, "dxf", None), "start_angle", 0.0))
    ea = _to_float(getattr(getattr(ent, "dxf", None), "end_angle", 0.0))
    sweep = (ea - sa) % 360.0
    if sweep <= 0:
        sweep += 360.0
    return {
        "entity_type": "ARC",
        "layer": layer,
        "center": _point_dict(getattr(c, "x", 0.0), getattr(c, "y", 0.0)),
        "radius": round(r, 3),
        "start_angle": round(sa, 3),
        "end_angle": round(ea, 3),
        "arc_length": round(abs(math.radians(sweep) * r), 3),
    }


def _safe_measurement(ent: Any) -> float | None:
    for key in ("actual_measurement", "measurement"):
        try:
            v = getattr(getattr(ent, "dxf", None), key, None)
            if v is not None:
                return round(_to_float(v), 3)
        except Exception:
            continue
    try:
        v2 = ent.get_measurement()
        if v2 is not None:
            return round(_to_float(v2), 3)
    except Exception:
        pass
    return None


def parse_dxf_payload(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    payload: Dict[str, Any] = {
        "ok": False,
        "source_file": str(p),
        "layers": [],
        "texts": [],
        "title_block": {},
        "blocks": [],
        "dimensions": [],
        "geometry_features": [],
    }
    if not p.exists():
        payload["error"] = f"file_not_found:{p}"
        return payload
    if ezdxf is None:
        payload["error"] = "ezdxf_not_installed"
        return payload

    try:
        doc = ezdxf.readfile(str(p))
        msp = doc.modelspace()
    except Exception as e:
        payload["error"] = f"dxf_open_failed:{e}"
        return payload

    layer_counter: Counter[str] = Counter()
    layer_domain_counter: Dict[str, Counter[str]] = defaultdict(Counter)
    text_records: List[Dict[str, Any]] = []
    dimension_records: List[Dict[str, Any]] = []
    geometry_features: List[Dict[str, Any]] = []

    block_agg: Dict[Tuple[str, str, str, float, float, float, float], Dict[str, Any]] = {}
    geometry_limit = 3000
    entity_total = 0

    for ent in msp:
        entity_total += 1
        et = _entity_type(ent)
        layer = _entity_layer(ent)
        domain = _infer_domain(layer, et)
        layer_counter[layer] += 1
        layer_domain_counter[layer][domain] += 1

        if et in {"TEXT", "MTEXT", "ATTRIB"}:
            txt = _clean_text(_text_value(ent))
            if txt:
                text_records.append(
                    {
                        "text": txt,
                        "layer": layer,
                        "category": _text_category(txt),
                        "professional_domain": domain,
                        "entity_type": et,
                        "position": _entity_position(ent),
                        "handle": _entity_handle(ent),
                    }
                )

        if et == "INSERT":
            name = str(getattr(getattr(ent, "dxf", None), "name", "") or "").strip() or "UNKNOWN_BLOCK"
            sx = round(_to_float(getattr(getattr(ent, "dxf", None), "xscale", 1.0), 1.0), 4)
            sy = round(_to_float(getattr(getattr(ent, "dxf", None), "yscale", 1.0), 1.0), 4)
            sz = round(_to_float(getattr(getattr(ent, "dxf", None), "zscale", 1.0), 1.0), 4)
            rt = round(_to_float(getattr(getattr(ent, "dxf", None), "rotation", 0.0), 0.0), 3)
            key = (name, layer, domain, sx, sy, sz, rt)
            rec = block_agg.setdefault(
                key,
                {
                    "block_name": name,
                    "layer": layer,
                    "professional_domain": domain,
                    "count": 0,
                    "scale_x": sx,
                    "scale_y": sy,
                    "scale_z": sz,
                    "rotation": rt,
                    "sample_inserts": [],
                },
            )
            rec["count"] += 1
            pos = _entity_position(ent)
            if pos and len(rec["sample_inserts"]) < 3:
                rec["sample_inserts"].append(pos)

            try:
                for a in list(getattr(ent, "attribs", []) or []):
                    at = _clean_text(str(getattr(getattr(a, "dxf", None), "text", "") or ""))
                    if at:
                        text_records.append(
                            {
                                "text": at,
                                "layer": layer,
                                "category": "title_block_info" if any(k in at for k in ("项目名称", "工程名称", "图号", "比例")) else "drawing_text",
                                "professional_domain": domain,
                                "entity_type": "ATTRIB",
                                "position": _entity_position(a),
                                "handle": _entity_handle(a),
                            }
                        )
            except Exception:
                pass

            if len(geometry_features) < geometry_limit:
                geometry_features.append({"entity_type": "INSERT", "layer": layer, "block_name": name})

        if et == "DIMENSION":
            dim_text = _clean_text(str(getattr(getattr(ent, "dxf", None), "text", "") or ""))
            if dim_text == "<>":
                dim_text = ""
            rec = {
                "layer": layer,
                "measurement": _safe_measurement(ent),
                "text": dim_text,
                "defpoint": _entity_position(ent),
                "defpoint2": {},
                "defpoint3": {},
                "handle": _entity_handle(ent),
            }
            dimension_records.append(rec)
            if len(geometry_features) < geometry_limit:
                geometry_features.append({"entity_type": "DIMENSION", "layer": layer, "measurement": rec.get("measurement"), "text": dim_text})

        if len(geometry_features) < geometry_limit:
            if et == "LINE":
                geometry_features.append(_line_feature(ent, layer))
            elif et == "LWPOLYLINE":
                geometry_features.append(_polyline_feature(ent, layer, "LWPOLYLINE"))
            elif et == "POLYLINE":
                geometry_features.append(_polyline_feature(ent, layer, "POLYLINE"))
            elif et == "CIRCLE":
                geometry_features.append(_circle_feature(ent, layer))
            elif et == "ARC":
                geometry_features.append(_arc_feature(ent, layer))
            elif et in {"ELLIPSE", "SPLINE", "HATCH"}:
                geometry_features.append({"entity_type": et, "layer": layer})

    layers: List[Dict[str, Any]] = []
    for layer_name, count in layer_counter.most_common():
        domain_counter = layer_domain_counter.get(layer_name) or Counter()
        major_domain = domain_counter.most_common(1)[0][0] if domain_counter else "general"
        layers.append(
            {
                "layer_name": layer_name,
                "entity_count": int(count),
                "professional_domain": major_domain,
            }
        )

    blocks = sorted(block_agg.values(), key=lambda x: (-int(x.get("count") or 0), str(x.get("block_name") or "")))
    title_block = _parse_title_block(text_records, blocks)

    payload.update(
        {
            "ok": True,
            "layers": layers[:500],
            "texts": text_records[:3000],
            "title_block": title_block,
            "blocks": blocks[:500],
            "dimensions": dimension_records[:1000],
            "geometry_features": geometry_features[:geometry_limit],
            "meta": {
                "entity_total": int(entity_total),
                "layer_total": int(len(layers)),
                "text_total": int(len(text_records)),
                "block_total": int(len(blocks)),
                "dimension_total": int(len(dimension_records)),
                "geometry_total": int(len(geometry_features)),
            },
        }
    )
    return payload

