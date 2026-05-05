"""Mock-only mapper from ZBid input snapshots to ZDoc draft-only input."""

from __future__ import annotations

import copy
from typing import Any


FORBIDDEN_KEYS = {
    "formal_apply",
    "apply",
    "export",
    "generate_async",
    "job",
    "result_bundle",
    "build_output",
    "ollama",
    "llm",
}

REQUIRED_TOP_LEVEL_FIELDS = (
    "snapshot_meta",
    "project",
    "tender",
    "section_tasks",
    "version_hashes",
    "safety_boundary",
)

REQUIRED_SECTION_FIELDS = ("section_id", "title", "draft_intent")

REQUIRED_SAFETY_FLAGS = {
    "draft_only": True,
    "allow_formal_apply": False,
    "allow_export": False,
    "allow_job_write": False,
    "allow_result_bundle_write": False,
    "allow_ollama": False,
}


def map_zbid_snapshot_to_zdoc_draft_input(snapshot: dict) -> dict:
    """Map a ZBid input snapshot into a pure ZDoc draft-only input structure."""

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a dict")

    _reject_forbidden_keys(snapshot)
    _require_top_level_fields(snapshot)

    snapshot_meta = _require_dict(snapshot, "snapshot_meta")
    project = _require_dict(snapshot, "project")
    tender = _require_dict(snapshot, "tender")
    version_hashes = _require_dict(snapshot, "version_hashes")
    safety_boundary = _require_dict(snapshot, "safety_boundary")
    section_tasks = snapshot.get("section_tasks")

    if not isinstance(section_tasks, list) or not section_tasks:
        raise ValueError("section_tasks must be a non-empty list")

    _validate_safety_boundary(safety_boundary)

    scoring_items = tender.get("scoring_items") or []
    if not isinstance(scoring_items, list):
        raise ValueError("tender.scoring_items must be a list when provided")
    scoring_by_id = {
        str(item.get("item_id")): item
        for item in scoring_items
        if isinstance(item, dict) and item.get("item_id") is not None
    }

    materials = snapshot.get("technical_materials") or []
    if not isinstance(materials, list):
        raise ValueError("technical_materials must be a list when provided")
    materials_by_id = {
        str(item.get("material_id")): item
        for item in materials
        if isinstance(item, dict) and item.get("material_id") is not None
    }

    return {
        "mode": "draft_only",
        "source_system": "zbid",
        "project_context": _build_project_context(project, snapshot.get("lot") or {}),
        "section_input": [
            _map_section_task(task, version_hashes, scoring_by_id, materials_by_id)
            for task in section_tasks
        ],
        "review_context": copy.deepcopy(snapshot.get("review_context") or {}),
        "version_hashes": copy.deepcopy(version_hashes),
        "safety_boundary": {
            "draft_only": True,
            "allow_formal_apply": False,
            "allow_export": False,
            "allow_job_write": False,
            "allow_result_bundle_write": False,
            "allow_ollama": False,
            "no_write": True,
            "requires_human_review": True,
        },
        "audit_context": {
            "snapshot_id": snapshot_meta.get("snapshot_id"),
            "source_system": snapshot_meta.get("source_system"),
            "schema_version": snapshot_meta.get("schema_version"),
            "snapshot_created_at": snapshot_meta.get("snapshot_created_at"),
            "requested_by": snapshot_meta.get("requested_by"),
            "snapshot_hash": version_hashes.get("snapshot_hash"),
            "prompt_input_hash": version_hashes.get("prompt_input_hash"),
        },
    }


def _reject_forbidden_keys(value: Any, path: str = "snapshot") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden field at {path}.{key}: {key}")
            _reject_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{path}[{index}]")


def _require_top_level_fields(snapshot: dict) -> None:
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in snapshot:
            raise ValueError(f"missing required top-level field: {field}")


def _require_dict(snapshot: dict, field: str) -> dict:
    value = snapshot.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a dict")
    return value


def _validate_safety_boundary(safety_boundary: dict) -> None:
    for field, expected in REQUIRED_SAFETY_FLAGS.items():
        if safety_boundary.get(field) is not expected:
            raise ValueError(f"safety_boundary.{field} must be {expected}")


def _build_project_context(project: dict, lot: Any) -> dict:
    lot_data = lot if isinstance(lot, dict) else {}
    return {
        "project_id": project.get("project_id"),
        "project_name": project.get("project_name"),
        "project_code": project.get("project_code"),
        "owner_name": project.get("owner_name"),
        "bidder_name": project.get("bidder_name"),
        "document_type": project.get("document_type"),
        "lot_id": lot_data.get("lot_id"),
        "lot_name": lot_data.get("lot_name"),
        "scope_summary": lot_data.get("scope_summary"),
        "planned_duration_days": lot_data.get("planned_duration_days"),
        "quality_target": lot_data.get("quality_target"),
        "safety_target": lot_data.get("safety_target"),
    }


def _map_section_task(
    task: Any,
    version_hashes: dict,
    scoring_by_id: dict[str, dict],
    materials_by_id: dict[str, dict],
) -> dict:
    if not isinstance(task, dict):
        raise ValueError("each section task must be a dict")

    for field in REQUIRED_SECTION_FIELDS:
        if not str(task.get(field) or "").strip():
            raise ValueError(f"section task missing required field: {field}")

    related_scoring_item_ids = task.get("related_scoring_item_ids") or []
    if not isinstance(related_scoring_item_ids, list):
        raise ValueError("related_scoring_item_ids must be a list when provided")

    related_material_ids = task.get("related_material_ids") or []
    if not isinstance(related_material_ids, list):
        raise ValueError("related_material_ids must be a list when provided")

    return {
        "section_id": task.get("section_id"),
        "title": task.get("title"),
        "draft_intent": task.get("draft_intent"),
        "original": task.get("original_text"),
        "requirements": copy.deepcopy(task.get("requirements") or []),
        "target_length": task.get("target_length"),
        "original_hash": version_hashes.get("section_original_hash"),
        "scoring_context": _select_scoring_context(related_scoring_item_ids, scoring_by_id),
        "material_context": _select_material_context(related_material_ids, materials_by_id),
    }


def _select_scoring_context(item_ids: list, scoring_by_id: dict[str, dict]) -> list[dict]:
    selected = []
    for item_id in item_ids:
        item = scoring_by_id.get(str(item_id))
        if item is not None:
            selected.append(copy.deepcopy(item))
    return selected


def _select_material_context(material_ids: list, materials_by_id: dict[str, dict]) -> list[dict]:
    selected = []
    for material_id in material_ids:
        material = materials_by_id.get(str(material_id))
        if not material:
            continue
        if material.get("usable_for_draft") is not True:
            continue
        if material.get("sensitive") is True:
            continue
        selected.append(
            {
                "material_id": material.get("material_id"),
                "material_type": material.get("material_type"),
                "title": material.get("title"),
                "content_excerpt": material.get("content_excerpt"),
                "source_ref": material.get("source_ref"),
                "source_version": material.get("source_version"),
                "confidence": material.get("confidence"),
            }
        )
    return selected


__all__ = ["FORBIDDEN_KEYS", "map_zbid_snapshot_to_zdoc_draft_input"]
