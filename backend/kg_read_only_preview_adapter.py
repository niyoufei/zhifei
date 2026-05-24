"""Minimal draft adapter for KG read-only preview payloads.

This module is intentionally isolated from ZDoc runtime chains. It provides
pure functions only: no file IO, no route registration, no service calls, no
model calls, no retrieval, and no writeback.
"""

from typing import Any, Mapping


BLOCKED_STATUS = "blocked"
INVALID_STATUS = "invalid"
PREVIEW_STATUS = "preview_only"


def build_kg_read_only_preview(
    manifest_entity: Mapping[str, Any],
    registry_entity: Mapping[str, Any],
    manual_trigger: bool = False,
) -> dict[str, Any]:
    """Build a disabled KG read-only preview payload from supplied dictionaries."""

    if manual_trigger is not True:
        return _blocked_response(
            reason="manual_trigger_required",
            detail="manual_trigger must be True for preview draft creation.",
        )

    manifest_check = _validate_disabled_entity(
        manifest_entity,
        required_false_fields=(
            "enabled",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ),
        entity_name="manifest_entity",
    )
    registry_check = _validate_disabled_entity(
        registry_entity,
        required_false_fields=(
            "enabled",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ),
        entity_name="registry_entity",
    )

    if not manifest_check["ok"] or not registry_check["ok"]:
        return _invalid_response(
            reason="disabled_entity_validation_failed",
            detail={
                "manifest_entity": manifest_check,
                "registry_entity": registry_check,
            },
        )

    return {
        "status": PREVIEW_STATUS,
        "adapter": "kg_read_only_preview_adapter_draft",
        "default_off": True,
        "manual_trigger": True,
        "runtime_access": False,
        "route_registered": False,
        "writeback_allowed": False,
        "output_write_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
        "rag_allowed": False,
        "prompt_registry_allowed": False,
        "system_instruction_registry_allowed": False,
        "knowledge_pack_load_allowed": False,
        "preview_payload": {
            "pilot_name": _safe_get(manifest_entity, "pilot_name"),
            "pilot_direction": _safe_get(manifest_entity, "pilot_direction"),
            "domain_tags": _safe_get(manifest_entity, "domain_tags", []),
            "risk_level": _safe_get(manifest_entity, "risk_level"),
            "manifest_registration_status": _safe_get(
                manifest_entity,
                "registration_status",
            ),
            "registry_registration_status": _safe_get(
                registry_entity,
                "registration_status",
            ),
            "message": "Read-only preview payload draft; not evidence or scoring basis.",
        },
        "blocked_actions": (
            "read_source_file",
            "write_file",
            "write_document_body",
            "write_output_job_export",
            "call_service",
            "call_port",
            "call_ollama",
            "call_endpoint",
            "register_route",
            "trigger_generate",
            "trigger_export_docx",
            "trigger_review_apply",
            "connect_rag",
            "connect_prompt_registry",
            "connect_system_instruction_registry",
            "use_as_evidence",
            "use_as_scoring_basis",
            "load_knowledge_pack",
        ),
    }


def _validate_disabled_entity(
    entity: Mapping[str, Any],
    required_false_fields: tuple[str, ...],
    entity_name: str,
) -> dict[str, Any]:
    missing_fields = _missing_fields(
        entity,
        required_false_fields + ("registration_status",),
    )
    non_disabled_fields = tuple(
        field for field in required_false_fields if entity.get(field) is not False
    )
    registration_status = entity.get("registration_status")

    if missing_fields or non_disabled_fields or registration_status != "not_registered":
        return {
            "ok": False,
            "entity": entity_name,
            "missing_fields": missing_fields,
            "non_disabled_fields": non_disabled_fields,
            "registration_status": registration_status,
            "required_registration_status": "not_registered",
        }

    return {
        "ok": True,
        "entity": entity_name,
        "detail": "disabled_state_valid",
    }


def _missing_fields(
    entity: Mapping[str, Any],
    field_names: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(field for field in field_names if field not in entity)


def _blocked_response(reason: str, detail: str) -> dict[str, Any]:
    return {
        "status": BLOCKED_STATUS,
        "reason": reason,
        "detail": detail,
        "runtime_access": False,
        "route_registered": False,
        "writeback_allowed": False,
        "output_write_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
    }


def _invalid_response(reason: str, detail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": INVALID_STATUS,
        "reason": reason,
        "detail": detail,
        "runtime_access": False,
        "route_registered": False,
        "writeback_allowed": False,
        "output_write_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
    }


def _safe_get(
    entity: Mapping[str, Any],
    field_name: str,
    default_value: Any = None,
) -> Any:
    return entity.get(field_name, default_value)
