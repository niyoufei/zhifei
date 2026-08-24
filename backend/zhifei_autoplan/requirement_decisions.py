from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping


MATRIX_VERSION = 1
STYLE_POLICY = "approved_resolution > clarification > tender > user > system_default"


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def flatten_style_requirements(style: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Flatten a style payload into independently traceable requirement fields."""
    raw = dict(style or {})
    fields: Dict[str, Any] = {}
    for key in (
        "paper",
        "body_font",
        "title_font",
        "body_size",
        "title_size",
        "max_pages",
        "chapter_start_new_page",
        "enforce_chapter_pages",
    ):
        if key in raw and raw.get(key) is not None:
            fields[key] = deepcopy(raw.get(key))

    if raw.get("line_spacing_pt") is not None:
        fields["line_spacing"] = {
            "mode": "fixed_pt",
            "value": float(raw.get("line_spacing_pt")),
        }
    elif raw.get("line_spacing") is not None:
        fields["line_spacing"] = {
            "mode": "multiple",
            "value": float(raw.get("line_spacing")),
        }

    margins = raw.get("margins_cm")
    if isinstance(margins, Mapping):
        for side in ("top", "right", "bottom", "left"):
            if margins.get(side) is not None:
                fields[f"margins_cm.{side}"] = float(margins.get(side))
    return fields


def style_from_requirement_matrix(matrix: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Reconstruct the selected style without inventing values for unresolved fields."""
    out: Dict[str, Any] = {}
    fields = (matrix or {}).get("fields")
    if not isinstance(fields, Mapping):
        return out
    margins: Dict[str, float] = {}
    for field, decision in fields.items():
        if not isinstance(decision, Mapping) or decision.get("status") == "unresolved_conflict":
            continue
        selected = decision.get("selected")
        if not isinstance(selected, Mapping) or "value" not in selected:
            continue
        value = deepcopy(selected.get("value"))
        if field == "line_spacing" and isinstance(value, Mapping):
            if value.get("mode") == "fixed_pt":
                out["line_spacing_pt"] = float(value.get("value"))
            elif value.get("mode") == "multiple":
                out["line_spacing"] = float(value.get("value"))
        elif str(field).startswith("margins_cm."):
            margins[str(field).split(".", 1)[1]] = float(value)
        else:
            out[str(field)] = value
    if margins:
        out["margins_cm"] = margins
    return out


def build_requirement_decision_matrix(
    sources: Iterable[Mapping[str, Any]],
    *,
    scope: str = "document_style",
) -> Dict[str, Any]:
    """
    Resolve field-level candidates by explicit source priority.

    Equal-priority disagreement is deliberately left unresolved.  Callers may
    add an ``approved_resolution`` source at a higher priority, but must not
    silently choose between conflicting tender/clarification requirements.
    """
    candidates_by_field: Dict[str, List[Dict[str, Any]]] = {}
    source_receipts: List[Dict[str, Any]] = []
    for index, source in enumerate(sources):
        values = source.get("values")
        if not isinstance(values, Mapping):
            continue
        source_id = str(source.get("source_id") or f"source_{index + 1}")
        source_type = str(source.get("source_type") or "unknown")
        priority = int(source.get("priority") or 0)
        confidence = max(0.0, min(1.0, float(source.get("confidence") or 0.0)))
        evidence = source.get("evidence") if isinstance(source.get("evidence"), Mapping) else {}
        flat = flatten_style_requirements(values)
        source_receipts.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "priority": priority,
                "confidence": confidence,
                "evidence": dict(evidence),
                "fields": sorted(flat),
            }
        )
        for field, value in flat.items():
            candidates_by_field.setdefault(field, []).append(
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "priority": priority,
                    "confidence": confidence,
                    "value": deepcopy(value),
                    "evidence": dict(evidence),
                }
            )

    decisions: Dict[str, Any] = {}
    unresolved: List[str] = []
    for field in sorted(candidates_by_field):
        candidates = candidates_by_field[field]
        highest_priority = max(int(item.get("priority") or 0) for item in candidates)
        highest = [item for item in candidates if int(item.get("priority") or 0) == highest_priority]
        unique_highest: Dict[str, Dict[str, Any]] = {}
        for item in highest:
            unique_highest.setdefault(_json_key(item.get("value")), item)
        overridden = [item for item in candidates if int(item.get("priority") or 0) < highest_priority]
        if len(unique_highest) > 1:
            status = "unresolved_conflict"
            selected = None
            unresolved.append(field)
        else:
            selected = deepcopy(next(iter(unique_highest.values())))
            lower_differs = any(_json_key(item.get("value")) != _json_key(selected.get("value")) for item in overridden)
            status = "resolved_by_priority" if lower_differs else "resolved"
        decisions[field] = {
            "status": status,
            "selected": selected,
            "candidates": sorted(
                (deepcopy(item) for item in candidates),
                key=lambda item: (-int(item.get("priority") or 0), str(item.get("source_id") or "")),
            ),
            "highest_priority": highest_priority,
        }

    return {
        "version": MATRIX_VERSION,
        "scope": scope,
        "policy": STYLE_POLICY,
        "status": "unresolved_conflict" if unresolved else "resolved",
        "unresolved_fields": unresolved,
        "fields": decisions,
        "sources": source_receipts,
    }


def matrix_sources(matrix: Mapping[str, Any] | None) -> List[Dict[str, Any]]:
    """Recover source candidates from a persisted matrix for later layering."""
    by_source: Dict[str, Dict[str, Any]] = {}
    fields = (matrix or {}).get("fields")
    if not isinstance(fields, Mapping):
        return []
    for field, decision in fields.items():
        if not isinstance(decision, Mapping):
            continue
        for candidate in decision.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            source_id = str(candidate.get("source_id") or "unknown")
            source = by_source.setdefault(
                source_id,
                {
                    "source_id": source_id,
                    "source_type": str(candidate.get("source_type") or "unknown"),
                    "priority": int(candidate.get("priority") or 0),
                    "confidence": float(candidate.get("confidence") or 0.0),
                    "evidence": dict(candidate.get("evidence") or {}),
                    "values": {},
                },
            )
            value = deepcopy(candidate.get("value"))
            if field == "line_spacing" and isinstance(value, Mapping):
                if value.get("mode") == "fixed_pt":
                    source["values"]["line_spacing_pt"] = value.get("value")
                elif value.get("mode") == "multiple":
                    source["values"]["line_spacing"] = value.get("value")
            elif str(field).startswith("margins_cm."):
                source["values"].setdefault("margins_cm", {})[str(field).split(".", 1)[1]] = value
            else:
                source["values"][str(field)] = value
    return list(by_source.values())
