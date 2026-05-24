"""Draft-only skeleton for a ZDoc KG read-only preview adapter.

This file lives under docs and is not a runtime adapter. It must not be
executed, imported by ZDoc, registered as a route, added to CI, or compiled as
part of KG-RUNTIME-03.

The skeleton intentionally does not read files. Callers would have to provide
already-parsed disabled entity metadata in a separately authorized future step.
"""

from typing import Any, Mapping


BLOCKED_STATUS = "blocked"
INVALID_STATUS = "invalid"
PREVIEW_STATUS = "preview_only"


def build_read_only_preview_payload(
    disabled_manifest_entity_path: str,
    disabled_registry_entity_path: str,
    manual_trigger: Mapping[str, Any],
    disabled_manifest_entity: Mapping[str, Any],
    disabled_registry_entity: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a draft read-only preview payload without loading any files.

    Inputs are deliberately split into paths and already-supplied metadata. This
    skeleton does not open, read, write, register, or load anything.
    """

    trigger_result = _validate_manual_trigger(manual_trigger)
    if not trigger_result["ok"]:
        return _blocked_response(
            reason="manual_trigger_required",
            detail=trigger_result["detail"],
            disabled_manifest_entity_path=disabled_manifest_entity_path,
            disabled_registry_entity_path=disabled_registry_entity_path,
        )

    manifest_result = _validate_disabled_manifest_entity(disabled_manifest_entity)
    registry_result = _validate_disabled_registry_entity(disabled_registry_entity)

    if not manifest_result["ok"] or not registry_result["ok"]:
        return _invalid_response(
            reason="disabled_entity_state_invalid",
            detail={
                "manifest_entity": manifest_result,
                "registry_entity": registry_result,
            },
            disabled_manifest_entity_path=disabled_manifest_entity_path,
            disabled_registry_entity_path=disabled_registry_entity_path,
        )

    return {
        "status": PREVIEW_STATUS,
        "preview_type": "kg_read_only_preview_adapter_skeleton",
        "runtime_access": False,
        "registration_allowed": False,
        "writeback_allowed": False,
        "output_write_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
        "rag_allowed": False,
        "prompt_registry_allowed": False,
        "system_instruction_registry_allowed": False,
        "source_paths": {
            "disabled_manifest_entity_path": disabled_manifest_entity_path,
            "disabled_registry_entity_path": disabled_registry_entity_path,
        },
        "preview_payload": {
            "pilot_name": _safe_get(disabled_manifest_entity, "pilot_name"),
            "pilot_direction": _safe_get(disabled_manifest_entity, "pilot_direction"),
            "domain_tags": _safe_get(disabled_manifest_entity, "domain_tags", []),
            "risk_level": _safe_get(disabled_manifest_entity, "risk_level"),
            "registry_candidate_id": _safe_get(
                disabled_registry_entity,
                "registry_entity_id",
            ),
            "message": "Read-only preview draft only; no generation, evidence, or scoring use.",
        },
        "blocked_actions": [
            "write_document_body",
            "write_output_job_export",
            "use_as_evidence",
            "use_as_scoring_basis",
            "register_manifest",
            "load_runtime_registry",
            "connect_rag",
            "connect_prompt_registry",
            "connect_system_instruction_registry",
            "trigger_generate",
            "trigger_export_docx",
            "trigger_review_apply",
            "trigger_zbid_writeback",
        ],
    }


def _validate_manual_trigger(manual_trigger: Mapping[str, Any]) -> dict[str, Any]:
    if not manual_trigger:
        return {"ok": False, "detail": "manual_trigger_missing"}

    if manual_trigger.get("requested_by") != "human":
        return {"ok": False, "detail": "requested_by_must_be_human"}

    if manual_trigger.get("mode") != "read_only_preview":
        return {"ok": False, "detail": "mode_must_be_read_only_preview"}

    if manual_trigger.get("allow_writeback") is not False:
        return {"ok": False, "detail": "allow_writeback_must_be_false"}

    return {"ok": True, "detail": "manual_trigger_valid"}


def _validate_disabled_manifest_entity(entity: Mapping[str, Any]) -> dict[str, Any]:
    return _require_disabled_fields(
        entity,
        required_false_fields=[
            "enabled",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ],
        entity_type="manifest_entity",
    )


def _validate_disabled_registry_entity(entity: Mapping[str, Any]) -> dict[str, Any]:
    return _require_disabled_fields(
        entity,
        required_false_fields=[
            "enabled",
            "runtime_registered",
            "registry_loadable",
            "runtime_loadable",
            "evidence_allowed",
            "scoring_allowed",
        ],
        entity_type="registry_entity",
    )


def _require_disabled_fields(
    entity: Mapping[str, Any],
    required_false_fields: list[str],
    entity_type: str,
) -> dict[str, Any]:
    missing_fields = [field for field in required_false_fields if field not in entity]
    non_disabled_fields = [
        field for field in required_false_fields if entity.get(field) is not False
    ]

    registration_status = entity.get("registration_status")
    registration_invalid = registration_status != "not_registered"

    if missing_fields or non_disabled_fields or registration_invalid:
        return {
            "ok": False,
            "entity_type": entity_type,
            "missing_fields": missing_fields,
            "non_disabled_fields": non_disabled_fields,
            "registration_status": registration_status,
            "required_registration_status": "not_registered",
        }

    return {
        "ok": True,
        "entity_type": entity_type,
        "detail": "disabled_state_valid",
    }


def _blocked_response(
    reason: str,
    detail: Any,
    disabled_manifest_entity_path: str,
    disabled_registry_entity_path: str,
) -> dict[str, Any]:
    return {
        "status": BLOCKED_STATUS,
        "reason": reason,
        "detail": detail,
        "runtime_access": False,
        "writeback_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
        "source_paths": {
            "disabled_manifest_entity_path": disabled_manifest_entity_path,
            "disabled_registry_entity_path": disabled_registry_entity_path,
        },
    }


def _invalid_response(
    reason: str,
    detail: Any,
    disabled_manifest_entity_path: str,
    disabled_registry_entity_path: str,
) -> dict[str, Any]:
    return {
        "status": INVALID_STATUS,
        "reason": reason,
        "detail": detail,
        "runtime_access": False,
        "writeback_allowed": False,
        "evidence_allowed": False,
        "scoring_allowed": False,
        "source_paths": {
            "disabled_manifest_entity_path": disabled_manifest_entity_path,
            "disabled_registry_entity_path": disabled_registry_entity_path,
        },
    }


def _safe_get(
    entity: Mapping[str, Any],
    field_name: str,
    default_value: Any = None,
) -> Any:
    return entity.get(field_name, default_value)
