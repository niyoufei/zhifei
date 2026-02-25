from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple


Point = Tuple[float, float]


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _pt(x: Any, y: Any, precision: int) -> Point:
    return (round(_f(x), precision), round(_f(y), precision))


def _line_seg(ent: Any) -> tuple[Point, Point, float]:
    sx = _f(getattr(ent.dxf.start, "x", 0.0))
    sy = _f(getattr(ent.dxf.start, "y", 0.0))
    ex = _f(getattr(ent.dxf.end, "x", 0.0))
    ey = _f(getattr(ent.dxf.end, "y", 0.0))
    length = math.hypot(ex - sx, ey - sy)
    return (sx, sy), (ex, ey), length


def _lwpolyline_segs(ent: Any) -> tuple[List[tuple[Point, Point, float]], bool]:
    pts: List[Point] = []
    try:
        for p in ent.get_points("xy"):
            pts.append((_f(p[0]), _f(p[1])))
    except Exception:
        pts = []
    out: List[tuple[Point, Point, float]] = []
    if len(pts) >= 2:
        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]
            out.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
    closed = bool(getattr(ent, "closed", False))
    if closed and len(pts) >= 3:
        a = pts[-1]
        b = pts[0]
        out.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
    return out, closed


def _polyline_segs(ent: Any) -> tuple[List[tuple[Point, Point, float]], bool]:
    pts: List[Point] = []
    try:
        for v in ent.vertices:
            loc = v.dxf.location
            pts.append((_f(getattr(loc, "x", 0.0)), _f(getattr(loc, "y", 0.0))))
    except Exception:
        pts = []
    out: List[tuple[Point, Point, float]] = []
    if len(pts) >= 2:
        for i in range(len(pts) - 1):
            a = pts[i]
            b = pts[i + 1]
            out.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
    closed = bool(getattr(ent, "is_closed", False))
    if closed and len(pts) >= 3:
        a = pts[-1]
        b = pts[0]
        out.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
    return out, closed


def _arc_seg(ent: Any) -> tuple[Point, Point, float]:
    cx = _f(getattr(ent.dxf.center, "x", 0.0))
    cy = _f(getattr(ent.dxf.center, "y", 0.0))
    r = abs(_f(getattr(ent.dxf, "radius", 0.0)))
    sa = _f(getattr(ent.dxf, "start_angle", 0.0))
    ea = _f(getattr(ent.dxf, "end_angle", 0.0))
    sweep = (ea - sa) % 360.0
    if sweep <= 0:
        sweep += 360.0
    sr = math.radians(sa)
    er = math.radians(sa + sweep)
    s = (cx + r * math.cos(sr), cy + r * math.sin(sr))
    e = (cx + r * math.cos(er), cy + r * math.sin(er))
    length = abs(math.radians(sweep) * r)
    return s, e, length


def _iter_segments(entities: Iterable[Any]) -> tuple[List[tuple[Point, Point, float]], Dict[str, int], Dict[str, float]]:
    segs: List[tuple[Point, Point, float]] = []
    counts: Dict[str, int] = defaultdict(int)
    extras: Dict[str, float] = {"circle_count": 0.0, "circle_length": 0.0, "closed_polyline_count": 0.0}
    for ent in entities:
        t = str(ent.dxftype() or "").upper()
        counts[t] += 1
        try:
            if t == "LINE":
                segs.append(_line_seg(ent))
            elif t == "LWPOLYLINE":
                parts, closed = _lwpolyline_segs(ent)
                segs.extend(parts)
                if closed:
                    extras["closed_polyline_count"] += 1.0
            elif t == "POLYLINE":
                parts, closed = _polyline_segs(ent)
                segs.extend(parts)
                if closed:
                    extras["closed_polyline_count"] += 1.0
            elif t == "ARC":
                segs.append(_arc_seg(ent))
            elif t == "CIRCLE":
                r = abs(_f(getattr(ent.dxf, "radius", 0.0)))
                extras["circle_count"] += 1.0
                extras["circle_length"] += 2.0 * math.pi * r
        except Exception:
            continue
    return segs, dict(counts), extras


def build_topology_from_entities(
    entities: Iterable[Any],
    *,
    node_precision: int = 2,
    max_segments: int = 200000,
) -> Dict[str, Any]:
    """
    Build deterministic 2D topology summary for DXF modelspace.
    This is geometry-level parsing (not OCR text summary).
    """
    segs, entity_breakdown, extras = _iter_segments(entities)
    if max_segments > 0 and len(segs) > max_segments:
        segs = segs[:max_segments]

    if not segs and extras.get("circle_count", 0) <= 0:
        return {
            "ok": False,
            "reason": "no_geometric_segments",
            "nodes_count": 0,
            "edges_count": 0,
            "components_count": 0,
            "endpoint_count": 0,
            "branch_node_count": 0,
            "total_length": 0.0,
            "trunk_length": 0.0,
            "suggested_flow_segments": 0,
            "closed_loops": 0,
            "entity_breakdown": entity_breakdown,
        }

    deg: Dict[Point, int] = defaultdict(int)
    graph: Dict[Point, set[Point]] = defaultdict(set)
    edge_lengths: List[tuple[Point, Point, float]] = []
    total_length = float(extras.get("circle_length", 0.0))
    for a_raw, b_raw, ln in segs:
        a = _pt(a_raw[0], a_raw[1], node_precision)
        b = _pt(b_raw[0], b_raw[1], node_precision)
        if a == b:
            continue
        deg[a] += 1
        deg[b] += 1
        graph[a].add(b)
        graph[b].add(a)
        length = max(0.0, _f(ln))
        edge_lengths.append((a, b, length))
        total_length += length

    nodes = set(graph.keys())
    if not nodes:
        return {
            "ok": True,
            "reason": "closed_loops_only",
            "nodes_count": 0,
            "edges_count": 0,
            "components_count": int(extras.get("circle_count", 0)),
            "endpoint_count": 0,
            "branch_node_count": 0,
            "total_length": round(total_length, 2),
            "trunk_length": round(total_length, 2),
            "suggested_flow_segments": int(max(1, extras.get("circle_count", 0))),
            "closed_loops": int(extras.get("circle_count", 0) + extras.get("closed_polyline_count", 0)),
            "entity_breakdown": entity_breakdown,
        }

    comp_id: Dict[Point, int] = {}
    comp_nodes: Dict[int, int] = defaultdict(int)
    cid = 0
    for n in nodes:
        if n in comp_id:
            continue
        cid += 1
        stack = [n]
        comp_id[n] = cid
        while stack:
            x = stack.pop()
            comp_nodes[cid] += 1
            for y in graph.get(x) or []:
                if y in comp_id:
                    continue
                comp_id[y] = cid
                stack.append(y)

    comp_lengths: Dict[int, float] = defaultdict(float)
    for a, b, ln in edge_lengths:
        c = comp_id.get(a)
        if c is None:
            continue
        comp_lengths[c] += max(0.0, _f(ln))

    endpoints = [n for n, d in deg.items() if d == 1]
    branches = [n for n, d in deg.items() if d >= 3]
    components_count = int(max(comp_nodes.keys()) if comp_nodes else 0)
    largest_comp_len = max(comp_lengths.values()) if comp_lengths else 0.0
    suggested_segments = int(
        max(
            components_count,
            math.ceil(len(endpoints) / 2.0),
            1 if total_length > 0 else 0,
        )
    )
    loops = int(extras.get("circle_count", 0) + extras.get("closed_polyline_count", 0))

    confidence = "low"
    if len(nodes) >= 12 and len(edge_lengths) >= 16:
        confidence = "high"
    elif len(nodes) >= 4 and len(edge_lengths) >= 4:
        confidence = "medium"

    return {
        "ok": True,
        "node_precision": int(node_precision),
        "nodes_count": int(len(nodes)),
        "edges_count": int(len(edge_lengths)),
        "components_count": int(components_count),
        "endpoint_count": int(len(endpoints)),
        "branch_node_count": int(len(branches)),
        "total_length": round(float(total_length), 2),
        "trunk_length": round(float(largest_comp_len), 2),
        "suggested_flow_segments": int(suggested_segments),
        "closed_loops": int(loops),
        "max_component_nodes": int(max(comp_nodes.values()) if comp_nodes else 0),
        "topology_confidence": confidence,
        "entity_breakdown": entity_breakdown,
    }


def topology_summary_text(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return ""
    if not meta.get("ok"):
        return ""
    return (
        f"拓扑节点: {meta.get('nodes_count')} | "
        f"拓扑边: {meta.get('edges_count')} | "
        f"连通分量: {meta.get('components_count')} | "
        f"端点: {meta.get('endpoint_count')} | "
        f"主干长度: {meta.get('trunk_length')} | "
        f"建议流水段: {meta.get('suggested_flow_segments')}"
    )
