from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import ezdxf

from modules.parser.drawing_topology import build_topology_from_entities


_DIM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|MPa|kN|dB)", re.IGNORECASE)
_ELEV_RE = re.compile(r"(?:标高|高程|EL|RL)?\s*([+-]?\d+(?:\.\d+)?)\s*(?:m|米)?", re.IGNORECASE)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _read_text_anchor(ent: Any) -> Dict[str, Any] | None:
    t = str(ent.dxftype() or "").upper()
    if t not in {"TEXT", "MTEXT"}:
        return None
    raw = ""
    x = 0.0
    y = 0.0
    try:
        if t == "TEXT":
            raw = str(getattr(ent.dxf, "text", "") or "")
            ins = getattr(ent.dxf, "insert", None)
            x = _f(getattr(ins, "x", 0.0))
            y = _f(getattr(ins, "y", 0.0))
        else:
            raw = str(getattr(ent, "plain_text", lambda: "")() or "")
            ins = getattr(ent.dxf, "insert", None)
            x = _f(getattr(ins, "x", 0.0))
            y = _f(getattr(ins, "y", 0.0))
    except Exception:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return {
        "label": raw[:80],
        "text": raw[:120],
        "x": round(x, 3),
        "y": round(y, 3),
        "layer": str(getattr(ent.dxf, "layer", "") or ""),
    }


def _read_insert_anchor(ent: Any) -> Dict[str, Any] | None:
    if str(ent.dxftype() or "").upper() != "INSERT":
        return None
    try:
        ins = getattr(ent.dxf, "insert", None)
        name = str(getattr(ent.dxf, "name", "") or "").strip()
        return {
            "label": f"块:{name}" if name else "块锚点",
            "name": name,
            "x": round(_f(getattr(ins, "x", 0.0)), 3),
            "y": round(_f(getattr(ins, "y", 0.0)), 3),
            "layer": str(getattr(ent.dxf, "layer", "") or ""),
        }
    except Exception:
        return None


def _read_dimension_anchor(ent: Any) -> Dict[str, Any] | None:
    if str(ent.dxftype() or "").upper() != "DIMENSION":
        return None
    try:
        txt = str(getattr(ent.dxf, "text", "") or "").strip()
        if txt in {"", "<>"}:
            txt = "尺寸标注"
        dlp = getattr(ent.dxf, "defpoint", None)
        return {
            "text": txt[:80],
            "x": round(_f(getattr(dlp, "x", 0.0)), 3),
            "y": round(_f(getattr(dlp, "y", 0.0)), 3),
            "layer": str(getattr(ent.dxf, "layer", "") or ""),
        }
    except Exception:
        return None


def _collect_bbox_points(ent: Any, points: list[tuple[float, float]]) -> None:
    t = str(ent.dxftype() or "").upper()
    try:
        if t == "LINE":
            s = getattr(ent.dxf, "start", None)
            e = getattr(ent.dxf, "end", None)
            points.append((_f(getattr(s, "x", 0.0)), _f(getattr(s, "y", 0.0))))
            points.append((_f(getattr(e, "x", 0.0)), _f(getattr(e, "y", 0.0))))
        elif t == "LWPOLYLINE":
            for p in ent.get_points("xy"):
                points.append((_f(p[0]), _f(p[1])))
        elif t == "POLYLINE":
            for v in ent.vertices:
                loc = getattr(v.dxf, "location", None)
                points.append((_f(getattr(loc, "x", 0.0)), _f(getattr(loc, "y", 0.0))))
        elif t in {"TEXT", "MTEXT", "INSERT", "DIMENSION"}:
            if t == "DIMENSION":
                pt = getattr(ent.dxf, "defpoint", None)
            else:
                pt = getattr(ent.dxf, "insert", None)
            points.append((_f(getattr(pt, "x", 0.0)), _f(getattr(pt, "y", 0.0))))
    except Exception:
        return


def _build_semantics(
    entities: list[Any],
    *,
    topology: Dict[str, Any],
    max_anchors: int = 24,
) -> Dict[str, Any]:
    component_anchors = []
    dimension_anchors = []
    elevation_anchors = []
    points: list[tuple[float, float]] = []

    for ent in entities:
        _collect_bbox_points(ent, points)
        a = _read_insert_anchor(ent)
        if a and len(component_anchors) < max_anchors:
            component_anchors.append(a)
        ta = _read_text_anchor(ent)
        if ta:
            if len(component_anchors) < max_anchors:
                component_anchors.append(ta)
            if _DIM_RE.search(str(ta.get("text") or "")) and len(dimension_anchors) < max_anchors:
                dimension_anchors.append(
                    {
                        "text": str(ta.get("text") or "")[:80],
                        "x": ta.get("x"),
                        "y": ta.get("y"),
                        "layer": ta.get("layer"),
                    }
                )
            if _ELEV_RE.search(str(ta.get("text") or "")) and len(elevation_anchors) < max_anchors:
                elevation_anchors.append(
                    {
                        "text": str(ta.get("text") or "")[:80],
                        "x": ta.get("x"),
                        "y": ta.get("y"),
                        "layer": ta.get("layer"),
                    }
                )
        da = _read_dimension_anchor(ent)
        if da and len(dimension_anchors) < max_anchors:
            dimension_anchors.append(da)

    bbox = {}
    zones = []
    if points:
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        bbox = {
            "min_x": round(x0, 3),
            "max_x": round(x1, 3),
            "min_y": round(y0, 3),
            "max_y": round(y1, 3),
            "width": round(x1 - x0, 3),
            "height": round(y1 - y0, 3),
        }
        # split to flow-zones by topology suggested segments
        seg_n = int(topology.get("suggested_flow_segments") or 0)
        seg_n = max(1, min(8, seg_n))
        step = (x1 - x0) / max(1, seg_n)
        for i in range(seg_n):
            zs = round(x0 + i * step, 3)
            ze = round(x0 + (i + 1) * step, 3)
            zones.append({"zone_id": f"Z{i + 1}", "x_start": zs, "x_end": ze})

    return {
        "bbox": bbox,
        "component_anchors": component_anchors,
        "dimension_anchors": dimension_anchors,
        "elevation_anchors": elevation_anchors,
        "zones": zones,
    }


def parse_cad_from_dxf(dxf_path: str) -> Dict[str, Any]:
    """解析 DXF 文件并返回图层/实体统计 + 拓扑摘要（用于施工流水段判定）。"""
    p = Path(dxf_path)
    if not p.exists():
        return {"error": f"文件不存在：{dxf_path}"}

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        layers = [str(layer.dxf.name) for layer in doc.layers]
        entities = list(msp)

        # 统计 INSERT 块引用
        insert_blocks = {}
        entity_types = {}
        for e in entities:
            et = str(e.dxftype() or "").upper()
            entity_types[et] = entity_types.get(et, 0) + 1
            if et == "INSERT":
                blk = e.dxf.name
                insert_blocks[blk] = insert_blocks.get(blk, 0) + 1

        topology = build_topology_from_entities(entities, node_precision=2, max_segments=200000)
        semantics = _build_semantics(entities, topology=topology, max_anchors=24)

        return {
            "layers_count": len(layers),
            "layers": layers,
            "entities_count": len(entities),
            "insert_blocks": insert_blocks,
            "entity_types": entity_types,
            "topology": topology,
            "semantics": semantics,
        }

    except Exception as e:
        return {"error": str(e)}
