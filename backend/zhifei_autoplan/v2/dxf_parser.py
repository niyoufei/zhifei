from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _point_to_dict(value: Any) -> Dict[str, float]:
    if value is None:
        return {}
    try:
        x = float(getattr(value, "x", value[0]))
        y = float(getattr(value, "y", value[1]))
        z = float(getattr(value, "z", value[2] if len(value) > 2 else 0.0))
    except Exception:
        return {}
    return {"x": round(x, 6), "y": round(y, 6), "z": round(z, 6)}


def infer_professional_domain(layer_name: str) -> str:
    text = str(layer_name or "").strip().upper()
    if not text:
        return "unknown"
    if any(k in text for k in ("STR", "STRUCT", "REBAR", "COLUMN", "BEAM", "SLAB", "钢筋", "结构")):
        return "structure"
    if any(k in text for k in ("ARCH", "WALL", "DOOR", "WINDOW", "ROOM", "建筑", "墙", "门窗")):
        return "architecture"
    if any(k in text for k in ("MEP", "PIPE", "HVAC", "ELEC", "WATER", "DRAIN", "消防", "电气", "暖通", "给排水")):
        return "mep"
    if any(k in text for k in ("CIVIL", "ROAD", "BRIDGE", "市政", "道路", "桥梁")):
        return "civil"
    return "general"


def _extract_title_block_info(text_items: List[Dict[str, Any]]) -> Dict[str, str]:
    project_name = ""
    drawing_scale = ""

    for item in text_items:
        text = str(item.get("text") or "").strip()
        if not text:
            continue

        if not project_name:
            for pattern in (
                r"(?:项目名称|工程名称|PROJECT\s*NAME)\s*[:：]?\s*([^\n\r]+)",
                r"(?:项目|工程)\s*[:：]?\s*([^\n\r]+)",
            ):
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    project_name = str(match.group(1)).strip()
                    break

        if not drawing_scale:
            for pattern in (
                r"(?:出图比例|比例|SCALE)\s*[:：]?\s*([0-9]+\s*[:/]\s*[0-9]+)",
                r"([0-9]+\s*[:/]\s*[0-9]+)\s*(?:比例|SCALE)",
            ):
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    drawing_scale = str(match.group(1)).replace(" ", "")
                    break

        if project_name and drawing_scale:
            break

    return {"project_name": project_name, "drawing_scale": drawing_scale}


def _classify_text(text: str, entity_type: str) -> str:
    normalized = str(text or "").strip().upper()
    if not normalized:
        return "drawing_text"
    if entity_type in {"LEADER", "MULTILEADER"}:
        return "leader_annotation"
    if "总说明" in text or "GENERAL NOTES" in normalized:
        return "design_general_notes"
    if "技术要求" in text or "TECHNICAL REQUIRE" in normalized:
        return "technical_requirement"
    if any(k in text for k in ("项目名称", "工程名称", "出图比例", "比例")) or "SCALE" in normalized:
        return "title_block_info"
    return "drawing_text"


def _extract_mleader_text(entity: Any) -> str:
    for attr in ("text", "plain_text"):
        try:
            value = getattr(entity, attr, "")
            if callable(value):
                value = value()
            value = str(value or "").strip()
            if value:
                return value
        except Exception:
            continue

    try:
        context = getattr(entity, "context", None)
        if context is not None and getattr(context, "mtext", None) is not None:
            text = str(getattr(context.mtext, "default_content", "") or "").strip()
            if text:
                return text
    except Exception:
        pass
    return ""


def _extract_leader_text(entity: Any, doc: Any) -> str:
    annotation_handle = ""
    try:
        annotation_handle = str(getattr(entity.dxf, "annotation_handle", "") or "").strip()
    except Exception:
        annotation_handle = ""
    if not annotation_handle:
        return ""
    try:
        annotation = doc.entitydb.get(annotation_handle)
    except Exception:
        return ""
    if annotation is None:
        return ""
    etype = str(annotation.dxftype() or "").upper()
    try:
        if etype == "TEXT":
            return str(annotation.dxf.text or "").strip()
        if etype == "MTEXT":
            return str(annotation.plain_text() or "").strip()
    except Exception:
        return ""
    return ""


def _extract_text_items(doc: Any, modelspace: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entity in modelspace:
        etype = str(entity.dxftype() or "").upper()
        if etype not in {"TEXT", "MTEXT", "LEADER", "MULTILEADER"}:
            continue
        text = ""
        if etype == "TEXT":
            text = str(entity.dxf.text or "").strip()
        elif etype == "MTEXT":
            try:
                text = str(entity.plain_text() or "").strip()
            except Exception:
                text = str(getattr(entity, "text", "") or "").strip()
        elif etype == "LEADER":
            text = _extract_leader_text(entity, doc)
        elif etype == "MULTILEADER":
            text = _extract_mleader_text(entity)

        if not text:
            continue

        layer_name = str(getattr(entity.dxf, "layer", "") or "0")
        position = {}
        for attr in ("insert", "location", "center"):
            try:
                if entity.dxf.hasattr(attr):
                    position = _point_to_dict(getattr(entity.dxf, attr))
                    if position:
                        break
            except Exception:
                continue

        if not position and etype == "LEADER":
            try:
                vertices = list(entity.vertices)
                if vertices:
                    position = _point_to_dict(vertices[0])
            except Exception:
                pass

        items.append(
            {
                "entity_type": etype,
                "text": text,
                "layer": layer_name,
                "professional_domain": infer_professional_domain(layer_name),
                "category": _classify_text(text, etype),
                "position": position,
                "handle": str(getattr(entity.dxf, "handle", "") or ""),
            }
        )
    return items


def _extract_blocks(modelspace: Any) -> List[Dict[str, Any]]:
    stats: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for entity in modelspace:
        if str(entity.dxftype() or "").upper() != "INSERT":
            continue
        name = str(getattr(entity.dxf, "name", "") or "").strip()
        if not name:
            continue
        layer_name = str(getattr(entity.dxf, "layer", "") or "0")
        key = (name, layer_name)
        entry = stats.setdefault(
            key,
            {
                "block_name": name,
                "layer": layer_name,
                "professional_domain": infer_professional_domain(layer_name),
                "count": 0,
                "scale_x": float(getattr(entity.dxf, "xscale", 1.0) or 1.0),
                "scale_y": float(getattr(entity.dxf, "yscale", 1.0) or 1.0),
                "scale_z": float(getattr(entity.dxf, "zscale", 1.0) or 1.0),
                "rotation": float(getattr(entity.dxf, "rotation", 0.0) or 0.0),
                "sample_inserts": [],
            },
        )
        entry["count"] = int(entry["count"]) + 1
        if len(entry["sample_inserts"]) < 8:
            entry["sample_inserts"].append(_point_to_dict(getattr(entity.dxf, "insert", None)))
    return list(stats.values())


def _extract_dimensions(modelspace: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entity in modelspace:
        if str(entity.dxftype() or "").upper() != "DIMENSION":
            continue
        layer_name = str(getattr(entity.dxf, "layer", "") or "0")
        measurement = None
        try:
            measurement = float(entity.get_measurement())
        except Exception:
            measurement = None
        text = str(getattr(entity.dxf, "text", "") or "").strip()
        items.append(
            {
                "layer": layer_name,
                "professional_domain": infer_professional_domain(layer_name),
                "measurement": measurement,
                "text": text,
                "defpoint": _point_to_dict(getattr(entity.dxf, "defpoint", None)),
                "defpoint2": _point_to_dict(getattr(entity.dxf, "defpoint2", None)),
                "defpoint3": _point_to_dict(getattr(entity.dxf, "defpoint3", None)),
            }
        )
    return items


def _extract_geometry_features(modelspace: Any, *, max_items: int = 120) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for entity in modelspace:
        if len(items) >= max_items:
            break
        etype = str(entity.dxftype() or "").upper()
        layer_name = str(getattr(entity.dxf, "layer", "") or "0")
        feature: Dict[str, Any] = {"entity_type": etype, "layer": layer_name}

        try:
            if etype == "LINE":
                start = _point_to_dict(getattr(entity.dxf, "start", None))
                end = _point_to_dict(getattr(entity.dxf, "end", None))
                if start and end:
                    length = math.dist(
                        (start["x"], start["y"], start["z"]),
                        (end["x"], end["y"], end["z"]),
                    )
                    feature.update({"start": start, "end": end, "length": round(length, 6)})
                    items.append(feature)
            elif etype == "CIRCLE":
                center = _point_to_dict(getattr(entity.dxf, "center", None))
                radius = float(getattr(entity.dxf, "radius", 0.0) or 0.0)
                feature.update({"center": center, "radius": round(radius, 6)})
                items.append(feature)
            elif etype in {"LWPOLYLINE", "POLYLINE"}:
                vertex_count = 0
                closed = False
                if etype == "LWPOLYLINE":
                    try:
                        vertex_count = len(list(entity.get_points("xy")))
                    except Exception:
                        vertex_count = 0
                    closed = bool(getattr(entity, "closed", False))
                else:
                    try:
                        vertex_count = len(list(entity.points()))
                    except Exception:
                        vertex_count = 0
                    closed = bool(getattr(entity, "is_closed", False))
                feature.update({"vertex_count": int(vertex_count), "closed": closed})
                items.append(feature)
        except Exception:
            continue
    return items


def parse_dxf_payload(path: Path | str) -> Dict[str, Any]:
    dxf_path = Path(path)
    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    try:
        import ezdxf
    except Exception as exc:
        raise RuntimeError("DXF parser dependency missing: ezdxf") from exc

    doc = ezdxf.readfile(str(dxf_path))
    modelspace = doc.modelspace()

    layer_counter: Counter[str] = Counter()
    for entity in modelspace:
        layer_counter[str(getattr(entity.dxf, "layer", "") or "0")] += 1

    layer_names = set(layer_counter.keys())
    for layer in doc.layers:
        layer_names.add(str(layer.dxf.name or "0"))

    layers = []
    for name in sorted(layer_names):
        layers.append(
            {
                "layer_name": name,
                "entity_count": int(layer_counter.get(name, 0)),
                "professional_domain": infer_professional_domain(name),
            }
        )

    text_items = _extract_text_items(doc, modelspace)
    title_block = _extract_title_block_info(text_items)
    blocks = _extract_blocks(modelspace)
    dimensions = _extract_dimensions(modelspace)
    geometry_features = _extract_geometry_features(modelspace)

    return {
        "file_name": dxf_path.name,
        "file_path": str(dxf_path),
        "layers": layers,
        "texts": text_items,
        "title_block": title_block,
        "blocks": blocks,
        "dimensions": dimensions,
        "geometry_features": geometry_features,
        "summary": {
            "layer_count": len(layers),
            "text_count": len(text_items),
            "block_count": len(blocks),
            "dimension_count": len(dimensions),
            "geometry_feature_count": len(geometry_features),
        },
    }
