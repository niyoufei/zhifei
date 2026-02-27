from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_ELEV_RE = re.compile(r"(?:标高|高程|EL|RL)?\s*([+-]?\d+(?:\.\d+)?)\s*(?:m|米)?", re.IGNORECASE)
_DIM_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mm|cm|m|MPa|kN|dB)\b", re.IGNORECASE)


def summarize_spatial_anchors(parsed_meta: Dict[str, Any] | None, *, limit: int = 6) -> Dict[str, Any]:
    meta = parsed_meta if isinstance(parsed_meta, dict) else {}
    topology = meta.get("topology") if isinstance(meta.get("topology"), dict) else {}
    sem = meta.get("semantics") if isinstance(meta.get("semantics"), dict) else {}

    component = sem.get("component_anchors") if isinstance(sem.get("component_anchors"), list) else []
    dims = sem.get("dimension_anchors") if isinstance(sem.get("dimension_anchors"), list) else []
    elevs = sem.get("elevation_anchors") if isinstance(sem.get("elevation_anchors"), list) else []

    # fallback if semantics are absent
    if not component and isinstance(meta.get("insert_blocks"), dict):
        for k, v in list((meta.get("insert_blocks") or {}).items())[:limit]:
            component.append({"label": f"块:{k}", "count": v})

    comp_out: List[Dict[str, Any]] = []
    for c in component[:limit]:
        if not isinstance(c, dict):
            continue
        comp_out.append(
            {
                "label": str(c.get("label") or c.get("name") or c.get("text") or "构件锚点"),
                "x": c.get("x"),
                "y": c.get("y"),
                "layer": c.get("layer"),
            }
        )

    dim_out: List[Dict[str, Any]] = []
    for d in dims[:limit]:
        if not isinstance(d, dict):
            continue
        txt = str(d.get("text") or d.get("value") or "").strip()
        if txt and not _DIM_RE.search(txt):
            m = _DIM_RE.search(txt)
            if m:
                txt = m.group(0)
        dim_out.append(
            {
                "text": txt or str(d.get("value") or "尺寸锚点"),
                "x": d.get("x"),
                "y": d.get("y"),
            }
        )

    elev_out: List[Dict[str, Any]] = []
    for e in elevs[:limit]:
        if not isinstance(e, dict):
            continue
        raw = str(e.get("text") or e.get("value") or "").strip()
        if raw:
            mm = _ELEV_RE.search(raw)
            if mm:
                raw = mm.group(0)
        elev_out.append({"text": raw or "标高锚点", "x": e.get("x"), "y": e.get("y")})

    return {
        "topology": {
            "nodes_count": topology.get("nodes_count"),
            "edges_count": topology.get("edges_count"),
            "suggested_flow_segments": topology.get("suggested_flow_segments"),
            "topology_confidence": topology.get("topology_confidence"),
        },
        "component_anchors": comp_out,
        "dimension_anchors": dim_out,
        "elevation_anchors": elev_out,
    }


def pick_chapter_anchor(
    chapter_title: str,
    drawings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    title = str(chapter_title or "").strip()
    if not drawings:
        return {}

    # naive score by keyword overlap with anchor labels/keywords
    best: Tuple[float, Dict[str, Any], Dict[str, Any] | None, Dict[str, Any] | None] | None = None
    for d in drawings:
        anchors = d.get("spatial_anchors") if isinstance(d.get("spatial_anchors"), list) else []
        dims = d.get("dimension_anchors") if isinstance(d.get("dimension_anchors"), list) else []
        kws = d.get("keywords") if isinstance(d.get("keywords"), list) else []
        score = 0.0
        for kw in kws[:12]:
            sk = str(kw).strip()
            if sk and sk in title:
                score += 1.4
        if not anchors and dims:
            score += 0.5
        if anchors:
            score += 0.8
        if dims:
            score += 0.8
        if best is None or score > best[0]:
            best = (score, d, anchors[0] if anchors else None, dims[0] if dims else None)

    if best is None:
        return {}
    _, d, sp, dm = best
    out = {
        "filename": d.get("filename"),
        "sha256": d.get("sha256"),
        "spatial_anchor": sp,
        "dimension_anchor": dm,
        "topology": d.get("topology") if isinstance(d.get("topology"), dict) else {},
    }
    return out
