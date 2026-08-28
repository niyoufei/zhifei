from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.compliance_runtime import (
    load_runtime_registry_authority,
)
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.image_library import image_selection_pack_media_entries
from backend.zhifei_autoplan.job_store import create_job, update_job
from backend.zhifei_autoplan.media import (
    generate_boq_chart,
    generate_ingested_previews,
    generate_outline_mindmap,
)
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.params_runtime import get_image_defaults, load_params
from backend.zhifei_autoplan.quality_check import (
    run_quality_checks,
    strip_nonconcrete_language,
)
from backend.zhifei_autoplan.tender_store import load_tender_matrix

_FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_DIRECT_EXPORT_REQUIRED_GATE_CHECKS = frozenset(
    {
        "independent_content_quality",
        "plan_consistency",
        "verified_standards",
        "requirement_evidence_matrix",
        "boq_cross_index_closure",
        "formal_project_parameters",
        "formal_parameter_body_binding",
        "independent_model_review",
    }
)


def canonical_export_digest(value: Any) -> str:
    """Return the canonical SHA-256 used to bind formal export receipts."""

    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_sections_digest(sections: Any) -> str:
    """Bind the complete final section objects, not only rendered text."""

    if not isinstance(sections, list) or any(
        not isinstance(section, dict) for section in sections
    ):
        raise TypeError("direct_export_sections_invalid")
    return canonical_export_digest(sections)


def delivery_gate_digest_is_valid(gate: Any) -> bool:
    """Validate both the shape and canonical digest of a delivery decision."""

    if not isinstance(gate, dict):
        return False
    supplied = str(gate.get("decision_digest") or "").strip().lower()
    if _FULL_SHA256_RE.fullmatch(supplied) is None:
        return False
    core = {key: value for key, value in gate.items() if key != "decision_digest"}
    return supplied == canonical_export_digest(core)


def _validate_source_input_receipt(
    receipt: Any,
    *,
    project_id: str,
    tender: dict[str, Any],
    boq: dict[str, Any],
) -> dict[str, Any]:
    """Bind a formal re-export to the exact current Tender and BoQ inputs."""

    if not isinstance(receipt, dict):
        raise TypeError("direct_export_source_input_receipt_required")
    required = {
        "schema_version",
        "project_id",
        "tender_digest",
        "boq_digest",
        "receipt_digest",
    }
    if set(receipt) != required:
        raise ValueError("direct_export_source_input_receipt_invalid")
    core = {key: receipt.get(key) for key in required if key != "receipt_digest"}
    claimed_receipt_digest = str(receipt.get("receipt_digest") or "").lower()
    tender_digest = str(receipt.get("tender_digest") or "").lower()
    boq_digest = str(receipt.get("boq_digest") or "").lower()
    if (
        receipt.get("schema_version") != "autoplan-source-input-v1"
        or not project_id
        or str(receipt.get("project_id") or "").strip() != project_id
        or _FULL_SHA256_RE.fullmatch(tender_digest) is None
        or _FULL_SHA256_RE.fullmatch(boq_digest) is None
        or _FULL_SHA256_RE.fullmatch(claimed_receipt_digest) is None
        or claimed_receipt_digest != canonical_export_digest(core)
    ):
        raise ValueError("direct_export_source_input_receipt_invalid")
    if tender_digest != canonical_export_digest(tender):
        raise ValueError("direct_export_tender_input_changed")
    if boq_digest != canonical_export_digest(boq):
        raise ValueError("direct_export_boq_input_changed")
    return dict(receipt)


def _no_admitted_image_slots() -> tuple[Any, ...]:
    """Default fail-closed policy for export-time external image providers."""

    return ()


def _accepts_keyword(fn: Callable[..., Any], keyword: str) -> bool:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == keyword and parameter.kind in {
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }:
            return True
    return False


def _call_with_optional_workspace(
    fn: Callable[..., Any],
    *args: Any,
    workspace_dir: str | None,
    **kwargs: Any,
) -> Any:
    call_kwargs = dict(kwargs)
    if workspace_dir and _accepts_keyword(fn, "workspace_dir"):
        call_kwargs["workspace_dir"] = workspace_dir
    return fn(*args, **call_kwargs)


def _normalize_metrics_in_sections(sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        from backend.zhifei_autoplan.plan_consistency import (
            normalize_metrics_in_sections,
        )

        return normalize_metrics_in_sections(sections)
    except Exception:  # noqa: BLE001
        return None


def build_export_indexes(
    *,
    topic: str,
    outline: list[str],
    project_id: str | None,
    workspace_dir: str,
    boq: dict[str, Any],
    sections: list[dict[str, Any]],
    boq_focus: dict[str, Any],
    quality_checks: dict[str, Any],
) -> dict[str, Any]:
    from backend.zhifei_autoplan.cross_index import build_cross_index
    from backend.zhifei_autoplan.drawing_index import build_drawing_index
    from backend.zhifei_autoplan.standard_index import build_standard_index

    registry_authority = load_runtime_registry_authority()

    drawing_index = _call_with_optional_workspace(
        build_drawing_index,
        topic,
        outline,
        project_id=project_id,
        workspace_dir=workspace_dir,
    )
    standard_index = _call_with_optional_workspace(
        build_standard_index,
        topic,
        outline,
        project_id=project_id,
        workspace_dir=workspace_dir,
        official_registry_bytes=registry_authority.raw,
        official_registry_path=registry_authority.path,
    )
    if (
        str(standard_index.get("official_registry_sha256") or "")
        != str(registry_authority.projection.get("registry_sha256") or "")
        or Path(str(standard_index.get("official_registry_path") or ""))
        != registry_authority.path
    ):
        raise ValueError("direct_export_registry_authority_mismatch")
    cross_index = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus=boq_focus,
        drawing_index=drawing_index,
        standard_index=standard_index,
        quality_checks=quality_checks,
        project_id=project_id,
    )
    indexes = {
        "drawing_index": drawing_index,
        "standard_index": standard_index,
        "cross_index": cross_index,
    }
    _validate_export_indexes(indexes, boq_focus=boq_focus)
    return indexes


def _validate_export_indexes(
    indexes: Any,
    *,
    boq_focus: dict[str, Any],
) -> dict[str, Any]:
    """Require a structurally valid cross-index even for injected builders."""

    from backend.zhifei_autoplan.cross_index import validate_cross_index_contract

    if not isinstance(indexes, dict):
        raise TypeError("export_indexes_not_object")
    cross_index = validate_cross_index_contract(
        indexes.get("cross_index"),
        expected_names=boq_focus.get("must_cover_keywords") or [],
    )
    focus_count = int(cross_index.get("focus_count") or 0)
    mentioned_count = int(cross_index.get("mentioned_count") or 0)
    closed_count = int(cross_index.get("closed_ok_count") or 0)
    missing_drawing = int(
        cross_index.get("missing_drawing_locator_count") or 0
    )
    missing_standard = int(
        cross_index.get("missing_standard_locator_count") or 0
    )
    if focus_count and (
        not str(cross_index.get("project_id") or "").strip()
        or mentioned_count != focus_count
        or closed_count != focus_count
        or missing_drawing != 0
        or missing_standard != 0
    ):
        raise ValueError("cross_index_formal_closure_incomplete")
    return indexes


def _validate_formal_export_indexes(
    indexes: Any,
    *,
    project_id: str,
) -> None:
    """Require complete, project-bound current indexes for formal re-export."""

    if not isinstance(indexes, dict):
        raise TypeError("direct_export_indexes_invalid")
    expected_project_id = str(project_id or "").strip()
    if not expected_project_id:
        raise ValueError("direct_export_project_id_required")
    cross_index = indexes.get("cross_index")
    if not isinstance(cross_index, dict):
        raise TypeError("direct_export_cross_index_invalid")
    if str(cross_index.get("project_id") or "").strip() != expected_project_id:
        raise ValueError("direct_export_cross_index_project_mismatch")
    focus_items = cross_index.get("focus_items")
    if not isinstance(focus_items, list) or any(
        not isinstance(row, dict) for row in focus_items
    ):
        raise ValueError("direct_export_cross_index_contract_incomplete")
    requirement_statuses: list[str] = []
    for row in focus_items:
        requirement = row.get("drawing_requirement")
        status = (
            str(requirement.get("status") or "").strip()
            if isinstance(requirement, dict)
            else ""
        )
        if status not in {"required", "optional", "not_applicable"}:
            raise ValueError("direct_export_cross_index_contract_incomplete")
        requirement_statuses.append(status)
    index_requires_rows = {
        "drawing_index": "required" in requirement_statuses,
        # Formal delivery always needs independent, current standard evidence.
        # A drawing exemption or an empty body cannot exempt this source gate.
        "standard_index": True,
    }
    index_rows = {
        "drawing_index": (
            "drawings",
            "indexed_drawing_count",
            "processed_drawing_count",
        ),
        "standard_index": (
            "standards",
            "indexed_standard_count",
            "indexed_standard_count",
        ),
    }
    for name, (rows_field, count_field, coverage_count_field) in index_rows.items():
        index = indexes.get(name)
        if not isinstance(index, dict):
            raise TypeError(f"direct_export_{name}_invalid")
        required_fields = {
            "ok",
            "project_id",
            "integrity_rejection_count",
            "invalid_identity_count",
            "missing_text_or_ocr_count",
            "locator_unavailable_count",
            "text_index_status",
            rows_field,
            count_field,
            coverage_count_field,
        }
        if name == "drawing_index":
            required_fields.add("page_coverage_status")
        if not required_fields.issubset(index):
            raise ValueError(f"direct_export_{name}_contract_incomplete")
        if str(index.get("project_id") or "").strip() != expected_project_id:
            raise ValueError(f"direct_export_{name}_project_mismatch")
        try:
            rejection_count = int(index.get("integrity_rejection_count") or 0)
            invalid_identity_count = int(index.get("invalid_identity_count") or 0)
            missing_text_count = int(index.get("missing_text_or_ocr_count") or 0)
            locator_unavailable_count = int(
                index.get("locator_unavailable_count") or 0
            )
            indexed_count = int(index.get(count_field) or 0)
            coverage_count = int(index.get(coverage_count_field) or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"direct_export_{name}_contract_incomplete") from exc
        indexed_rows = index.get(rows_field)
        integrity_failed = (
            rejection_count != 0
            or invalid_identity_count != 0
        )
        rows_invalid = (
            not isinstance(indexed_rows, list)
            or coverage_count < len(indexed_rows or [])
            or missing_text_count != 0
            or locator_unavailable_count != 0
            or (
                name == "drawing_index"
                and (index_requires_rows[name] or bool(indexed_rows))
                and str(index.get("page_coverage_status") or "").strip()
                != "complete"
            )
        )
        complete_rows = bool(indexed_rows)
        text_index_status = str(index.get("text_index_status") or "").strip()
        if name == "drawing_index":
            drawing_text_semantics_valid = (
                (
                    text_index_status == "complete"
                    and indexed_count == len(indexed_rows or [])
                )
                or (
                    text_index_status == "partial"
                    and 0 < indexed_count < len(indexed_rows or [])
                )
                or (
                    text_index_status == "no_text_locator"
                    and indexed_count == 0
                )
            )
            complete_contract = (
                index.get("ok") is True
                and drawing_text_semantics_valid
                and complete_rows
                and not rows_invalid
                and (not index_requires_rows[name] or indexed_count > 0)
            )
        else:
            complete_contract = (
                index.get("ok") is True
                and text_index_status == "complete"
                and complete_rows
                and not rows_invalid
            )
        empty_exempt_contract = (
            not index_requires_rows[name]
            and isinstance(indexed_rows, list)
            and not indexed_rows
            and indexed_count == 0
            and index.get("ok") is not True
            and bool(str(index.get("text_index_status") or "").strip())
            and not rows_invalid
        )
        if integrity_failed or not (
            complete_contract or empty_exempt_contract
        ):
            raise ValueError(f"direct_export_{name}_incomplete")


def _direct_export_binding_core(
    *,
    payload: dict[str, Any],
    raw_request: dict[str, Any],
) -> dict[str, Any]:
    requirement_matrix = payload.get("requirement_evidence_matrix")
    requirement_matrix = (
        requirement_matrix if isinstance(requirement_matrix, dict) else {}
    )
    return {
        "schema_version": "direct-export-binding-v1",
        "project_id": str(payload.get("project_id") or "").strip(),
        "source_job_id": str(
            raw_request.get("_formal_source_job_id") or ""
        ).strip(),
        "source_delivery_decision_digest": str(
            raw_request.get("_formal_source_delivery_decision_digest") or ""
        )
        .strip()
        .lower(),
        "source_sections_digest": str(
            raw_request.get("_formal_source_sections_digest") or ""
        )
        .strip()
        .lower(),
        "generation_release_identity_digest": canonical_export_digest(
            raw_request.get("_formal_source_generation_release_identity")
        ),
        "compliance_registry_authority_digest": str(
            (
                raw_request.get("_formal_source_compliance_registry_authority")
                or {}
            ).get("authority_digest")
            or ""
        )
        .strip()
        .lower(),
        "source_input_receipt_digest": str(
            (payload.get("source_input_receipt") or {}).get("receipt_digest")
            or ""
        )
        .strip()
        .lower(),
        "final_sections_digest": canonical_sections_digest(
            payload.get("sections")
        ),
        "delivery_decision_digest": str(
            (payload.get("delivery_quality_gate") or {}).get("decision_digest")
            or ""
        )
        .strip()
        .lower(),
        "drawing_index_digest": canonical_export_digest(
            payload.get("drawing_index")
        ),
        "standard_index_digest": canonical_export_digest(
            payload.get("standard_index")
        ),
        "cross_index_digest": canonical_export_digest(payload.get("cross_index")),
        "requirement_matrix_digest": str(
            requirement_matrix.get("matrix_digest") or ""
        ).strip(),
        "rebuilt_from_current_indexes": True,
    }


def _attach_direct_export_binding(
    payload: dict[str, Any],
    *,
    raw_request: dict[str, Any],
) -> None:
    core = _direct_export_binding_core(payload=payload, raw_request=raw_request)
    payload["direct_export_binding_receipt"] = {
        **core,
        "binding_digest": canonical_export_digest(core),
    }


def _validate_direct_export_receipts(
    payload: Any,
    *,
    raw_request: dict[str, Any],
) -> None:
    """Keep the legacy direct exporter behind a verified formal-job handoff."""

    if not isinstance(payload, dict):
        raise TypeError("direct_export_payload_invalid")
    source_digest = str(
        raw_request.get("_formal_source_delivery_decision_digest") or ""
    ).strip().lower()
    source_sections_digest = str(
        raw_request.get("_formal_source_sections_digest") or ""
    ).strip().lower()
    if (
        raw_request.get("_formal_source_verified") is not True
        or _FULL_SHA256_RE.fullmatch(source_digest) is None
        or _FULL_SHA256_RE.fullmatch(source_sections_digest) is None
        or not str(raw_request.get("_formal_source_job_id") or "").strip()
    ):
        raise ValueError("direct_export_formal_source_required")
    if str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1":
        expected_generation_release = {
            "schema_version": "autoplan-generation-release-v1",
            "system_id": str(
                os.environ.get("ZF_SYSTEM_ID") or "docgen-system"
            ).strip(),
            "release_id": str(os.environ.get("ZF_RELEASE_ID") or "").strip(),
            "manifest_digest": str(
                os.environ.get("ZF_RELEASE_MANIFEST_DIGEST") or ""
            ).strip(),
            "source_digest": str(
                os.environ.get("ZF_RELEASE_SOURCE_DIGEST") or ""
            ).strip(),
            "runtime_digest": str(
                os.environ.get("ZF_RUNTIME_DIGEST") or ""
            ).strip(),
            "release_root": str(
                os.environ.get("ZF_RELEASE_ROOT") or ""
            ).strip(),
            "runtime_mode": str(
                os.environ.get("ZF_RUNTIME_MODE") or "development"
            ).strip(),
            "release_managed": True,
        }
        expected_registry_authority = dict(
            load_runtime_registry_authority().projection
        )
        if (
            raw_request.get("_formal_source_generation_release_identity")
            != expected_generation_release
            or raw_request.get(
                "_formal_source_compliance_registry_authority"
            )
            != expected_registry_authority
            or payload.get("generation_release_identity")
            != expected_generation_release
            or payload.get("compliance_registry_authority")
            != expected_registry_authority
        ):
            raise ValueError("direct_export_registry_authority_mismatch")
    if not str(payload.get("project_id") or "").strip():
        raise ValueError("direct_export_project_id_required")
    if (
        not isinstance(raw_request.get("source_input_receipt"), dict)
        or payload.get("source_input_receipt")
        != raw_request.get("source_input_receipt")
    ):
        raise ValueError("direct_export_source_input_receipt_binding_invalid")
    final_sections_digest = canonical_sections_digest(payload.get("sections"))
    if final_sections_digest != source_sections_digest:
        raise ValueError("direct_export_sections_digest_mismatch")

    plan = payload.get("plan_consistency")
    if not isinstance(plan, dict) or plan.get("ok") is not True:
        raise ValueError("direct_export_plan_consistency_blocked")

    quality = payload.get("quality_checks")
    if not isinstance(quality, dict):
        raise TypeError("direct_export_content_quality_blocked")
    quality_gate = quality.get("quality_gate")
    review = quality.get("independent_content_review")
    review = review if isinstance(review, dict) else {}
    dimensions = review.get("dimensions")
    dimensions = dimensions if isinstance(dimensions, dict) else {}
    repetition = dimensions.get("non_repetition")
    repetition = repetition if isinstance(repetition, dict) else {}
    try:
        overall_score = float(review.get("score", quality.get("score")))
        non_repetition_score = float(repetition.get("score"))
    except (TypeError, ValueError) as exc:
        raise ValueError("direct_export_content_quality_blocked") from exc
    if (
        not isinstance(quality_gate, dict)
        or quality_gate.get("pass") is not True
        or overall_score < 75
        or non_repetition_score < 65
    ):
        raise ValueError("direct_export_content_quality_blocked")

    indexes = {
        "drawing_index": payload.get("drawing_index"),
        "standard_index": payload.get("standard_index"),
        "cross_index": payload.get("cross_index"),
    }
    _validate_formal_export_indexes(
        indexes,
        project_id=str(payload.get("project_id") or ""),
    )

    gate = payload.get("delivery_quality_gate")
    if not delivery_gate_digest_is_valid(gate):
        raise ValueError("direct_export_delivery_gate_digest_invalid")
    assert isinstance(gate, dict)
    from backend.zhifei_autoplan.delivery_quality import (
        FORMAL_DELIVERY_CONTRACT_VERSION,
    )

    check_rows = {
        str(row.get("name") or "").strip(): row
        for row in (gate.get("checks") or [])
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    }
    if (
        gate.get("delivery_allowed") is not True
        or gate.get("formal_contract_version")
        != FORMAL_DELIVERY_CONTRACT_VERSION
        or int(gate.get("blocker_count") or 0) != 0
        or bool(gate.get("blockers"))
        or not _DIRECT_EXPORT_REQUIRED_GATE_CHECKS.issubset(check_rows)
        or any(
            check_rows[name].get("pass") is not True
            for name in _DIRECT_EXPORT_REQUIRED_GATE_CHECKS
        )
        or check_rows["formal_project_parameters"].get("required") is not True
        or check_rows["formal_parameter_body_binding"].get("required") is not True
        or check_rows["independent_model_review"].get("required") is not True
        or check_rows["verified_standards"].get("required") is not True
        or check_rows["verified_standards"].get("standard_index_digest")
        != canonical_export_digest(payload.get("standard_index"))
        or check_rows["verified_standards"].get("standard_audit_digest")
        != canonical_export_digest(payload.get("standard_citation_audit"))
    ):
        raise ValueError("direct_export_delivery_quality_blocked")
    quality_gate_receipt = quality.get("delivery_quality_gate")
    if (
        not delivery_gate_digest_is_valid(quality_gate_receipt)
        or str((quality_gate_receipt or {}).get("decision_digest") or "").lower()
        != str(gate.get("decision_digest") or "").lower()
    ):
        raise ValueError("direct_export_delivery_gate_binding_invalid")

    receipt = payload.get("direct_export_binding_receipt")
    if not isinstance(receipt, dict):
        raise TypeError("direct_export_binding_receipt_missing")
    expected_core = _direct_export_binding_core(
        payload=payload,
        raw_request=raw_request,
    )
    supplied_binding_digest = str(receipt.get("binding_digest") or "").lower()
    if (
        {key: value for key, value in receipt.items() if key != "binding_digest"}
        != expected_core
        or _FULL_SHA256_RE.fullmatch(supplied_binding_digest) is None
        or supplied_binding_digest != canonical_export_digest(expected_core)
    ):
        raise ValueError("direct_export_binding_receipt_invalid")


def build_export_media(
    *,
    raw_request: dict[str, Any],
    project_id: str | None,
    boq: dict[str, Any],
    params: dict[str, Any],
    outline: list[str],
    workspace_dir: str,
    generate_boq_chart_fn: Callable[[dict[str, Any]], list[dict[str, Any]]] = generate_boq_chart,
    generate_ingested_previews_fn: Callable[..., list[dict[str, Any]]] = generate_ingested_previews,
    get_image_defaults_fn: Callable[[dict[str, Any]], dict[str, Any]] = get_image_defaults,
    iterate_image_failover_slots_fn: Callable[[], Any] = _no_admitted_image_slots,
    generate_outline_mindmap_fn: Callable[..., dict[str, Any] | None] = generate_outline_mindmap,
    resolve_logo_fn: Callable[..., Any] | None = None,
    prepare_logo_for_embedding_fn: Callable[[Any], Any] | None = None,
    update_branding_fn: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    stats = boq.get("stats") if isinstance(boq, dict) else None
    media: list[dict[str, Any]] = []
    if stats:
        media.extend(generate_boq_chart_fn(stats))
    project_source_media = list(
        _call_with_optional_workspace(
            generate_ingested_previews_fn,
            limit=6,
            project_id=project_id,
            workspace_dir=workspace_dir,
        )
        or []
    )
    media.extend(project_source_media)
    try:
        img_defaults = get_image_defaults_fn(params)
        aspect_ratio = (
            str(raw_request.get("image_aspect_ratio") or img_defaults.get("aspect_ratio") or "16:9").strip() or "16:9"
        )
        logo = _resolve_export_logo_context(
            raw_request=raw_request,
            project_id=project_id,
            workspace_dir=workspace_dir,
            resolve_logo_fn=resolve_logo_fn,
            prepare_logo_for_embedding_fn=prepare_logo_for_embedding_fn,
            update_branding_fn=update_branding_fn,
        )
        logo_embed = logo["logo_embed"]
        # Logos belong to cover/header branding, not the body image gallery.
        # When real project photos/drawings are available they outrank an AI
        # outline poster; callers can still opt in explicitly for diagnostics.
        include_outline_mindmap = bool(raw_request.get("include_outline_mindmap")) or not project_source_media
        if include_outline_mindmap:
            mindmap = build_export_mindmap_media(
                raw_request=raw_request,
                outline=outline,
                workspace_dir=workspace_dir,
                aspect_ratio=aspect_ratio,
                logo_embed=logo_embed,
                iterate_image_failover_slots_fn=iterate_image_failover_slots_fn,
                generate_outline_mindmap_fn=generate_outline_mindmap_fn,
            )
            if mindmap:
                media.append(mindmap)
    except Exception:  # noqa: BLE001,S110
        pass
    return media


def _resolve_export_logo_context(
    *,
    raw_request: dict[str, Any],
    project_id: str | None,
    workspace_dir: str,
    resolve_logo_fn: Callable[..., Any] | None = None,
    prepare_logo_for_embedding_fn: Callable[[Any], Any] | None = None,
    update_branding_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    logo_embed = None
    logo_raw_path = None
    try:
        if resolve_logo_fn is None or prepare_logo_for_embedding_fn is None:
            from backend.zhifei_autoplan.logo_runtime import (
                prepare_logo_for_embedding,
                resolve_logo,
            )

            resolve_logo_fn = resolve_logo_fn or resolve_logo
            prepare_logo_for_embedding_fn = prepare_logo_for_embedding_fn or prepare_logo_for_embedding

        if (
            raw_request.get("bidder_company")
            or raw_request.get("logo_url")
            or raw_request.get("bidder_domain")
            or project_id
        ):
            logo_raw = _call_with_optional_workspace(
                resolve_logo_fn,
                bidder_company=raw_request.get("bidder_company"),
                logo_url=raw_request.get("logo_url"),
                bidder_domain=raw_request.get("bidder_domain"),
                project_id=project_id,
                workspace_dir=workspace_dir,
            )
            if logo_raw:
                logo_raw_path = str(logo_raw)
                logo_embed = prepare_logo_for_embedding_fn(logo_raw) or None
    except Exception:  # noqa: BLE001
        logo_embed = None

    if logo_embed and project_id:
        try:
            if update_branding_fn is None:
                from backend.zhifei_autoplan.branding_store import update_branding

                update_branding_fn = update_branding
            _call_with_optional_workspace(
                update_branding_fn,
                str(project_id),
                {
                    "bidder_company": raw_request.get("bidder_company"),
                    "bidder_domain": raw_request.get("bidder_domain"),
                    "logo_url": raw_request.get("logo_url"),
                    "logo_raw_path": logo_raw_path,
                    "logo_embed_path": str(logo_embed),
                    "logo_path": str(logo_embed),
                },
                merge=True,
                workspace_dir=workspace_dir,
            )
        except Exception:  # noqa: BLE001,S110
            pass

    return {
        "logo_embed": logo_embed,
        "logo_raw_path": logo_raw_path,
    }


def build_export_mindmap_media(
    *,
    raw_request: dict[str, Any],
    outline: list[str],
    workspace_dir: str,
    aspect_ratio: str,
    logo_embed: str | None,
    iterate_image_failover_slots_fn: Callable[[], Any] = _no_admitted_image_slots,
    generate_outline_mindmap_fn: Callable[..., dict[str, Any] | None] = generate_outline_mindmap,
) -> dict[str, Any] | None:
    saw_supported_slot = False
    slot_rows = list(iterate_image_failover_slots_fn() or [])
    for image_slot in slot_rows:
        provider = str(getattr(image_slot, "provider", None) or "").strip().lower()
        if provider not in {"openai", "google"}:
            continue
        saw_supported_slot = True
        extra_kwargs: dict[str, Any] = {}
        if _accepts_keyword(generate_outline_mindmap_fn, "fallback_to_deterministic"):
            extra_kwargs["fallback_to_deterministic"] = False
        mindmap = _call_with_optional_workspace(
            generate_outline_mindmap_fn,
            raw_request.get("topic"),
            outline,
            provider=provider,
            api_key=getattr(image_slot, "api_key", None),
            model=getattr(image_slot, "model", None),
            aspect_ratio=aspect_ratio,
            logo_path=logo_embed,
            bidder_company=raw_request.get("bidder_company"),
            logo_url=raw_request.get("logo_url"),
            bidder_domain=raw_request.get("bidder_domain"),
            workspace_dir=workspace_dir,
            **extra_kwargs,
        )
        if mindmap:
            return mindmap
    if saw_supported_slot or not slot_rows:
        return _call_with_optional_workspace(
            generate_outline_mindmap_fn,
            raw_request.get("topic"),
            outline,
            aspect_ratio=aspect_ratio,
            logo_path=logo_embed,
            bidder_company=raw_request.get("bidder_company"),
            logo_url=raw_request.get("logo_url"),
            bidder_domain=raw_request.get("bidder_domain"),
            workspace_dir=workspace_dir,
        )
    return None


def execute_export_docx_request(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    load_tender_matrix_fn: Callable[..., dict[str, Any] | None] = load_tender_matrix,
    load_boq_data_fn: Callable[..., dict[str, Any] | None] = load_boq_data,
    build_boq_focus_fn: Callable[[dict[str, Any]], dict[str, Any]] = _build_boq_focus,
    load_params_fn: Callable[[], dict[str, Any]] = load_params,
    strip_nonconcrete_language_fn: Callable[[str], str] = strip_nonconcrete_language,
    normalize_metrics_in_sections_fn: Callable[[list[dict[str, Any]]], dict[str, Any] | None] = _normalize_metrics_in_sections,
    recommend_four_new_fn: Callable[..., Any] = recommend_four_new,
    run_quality_checks_fn: Callable[..., dict[str, Any]] = run_quality_checks,
    build_export_indexes_fn: Callable[..., dict[str, Any]] = build_export_indexes,
    build_evidence_tracking_fn: Callable[..., dict[str, Any]] = build_evidence_tracking,
    build_export_media_fn: Callable[..., list[dict[str, Any]]] = build_export_media,
    save_outputs_fn: Callable[..., dict[str, Any]] | None = None,
    create_job_fn: Callable[..., str] = create_job,
    update_job_fn: Callable[..., Any] = update_job,
) -> dict[str, Any]:
    job_id = _call_with_optional_workspace(
        create_job_fn,
        {"action": "export_docx", "workspace_dir": workspace_dir},
        user_id=None,
        workspace_dir=workspace_dir,
    )
    try:
        if save_outputs_fn is None:
            raise ValueError("save_outputs_fn required")
        payload = build_export_docx_payload(
            raw_request=raw_request,
            workspace_dir=workspace_dir,
            load_tender_matrix_fn=load_tender_matrix_fn,
            load_boq_data_fn=load_boq_data_fn,
            build_boq_focus_fn=build_boq_focus_fn,
            load_params_fn=load_params_fn,
            strip_nonconcrete_language_fn=strip_nonconcrete_language_fn,
            normalize_metrics_in_sections_fn=normalize_metrics_in_sections_fn,
            recommend_four_new_fn=recommend_four_new_fn,
            run_quality_checks_fn=run_quality_checks_fn,
            build_export_indexes_fn=build_export_indexes_fn,
            build_evidence_tracking_fn=build_evidence_tracking_fn,
            build_export_media_fn=build_export_media_fn,
        )
        _validate_direct_export_receipts(payload, raw_request=raw_request)
        outputs = _call_with_optional_workspace(
            save_outputs_fn,
            f"actions_export_{job_id}",
            [payload],
            workspace_dir=workspace_dir,
        )
        _call_with_optional_workspace(
            update_job_fn,
            job_id,
            status="done",
            result=outputs,
            workspace_dir=workspace_dir,
        )
        return {"ok": True, "job_id": job_id, "files": outputs}
    except Exception as exc:
        try:
            _call_with_optional_workspace(
                update_job_fn,
                job_id,
                status="failed",
                error={
                    "code": "EXPORT_DOCX_FAILED",
                    "stage": "export_pipeline",
                    "error_type": type(exc).__name__,
                },
                workspace_dir=workspace_dir,
            )
        except Exception:  # noqa: BLE001,S110 - preserve the export root cause.
            pass
        raise


def build_export_docx_payload(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    load_tender_matrix_fn: Callable[..., dict[str, Any] | None] = load_tender_matrix,
    load_boq_data_fn: Callable[..., dict[str, Any] | None] = load_boq_data,
    build_boq_focus_fn: Callable[[dict[str, Any]], dict[str, Any]] = _build_boq_focus,
    load_params_fn: Callable[[], dict[str, Any]] = load_params,
    strip_nonconcrete_language_fn: Callable[[str], str] = strip_nonconcrete_language,
    normalize_metrics_in_sections_fn: Callable[[list[dict[str, Any]]], dict[str, Any] | None] = _normalize_metrics_in_sections,
    recommend_four_new_fn: Callable[..., Any] = recommend_four_new,
    run_quality_checks_fn: Callable[..., dict[str, Any]] = run_quality_checks,
    build_export_indexes_fn: Callable[..., dict[str, Any]] = build_export_indexes,
    build_evidence_tracking_fn: Callable[..., dict[str, Any]] = build_evidence_tracking,
    build_export_media_fn: Callable[..., list[dict[str, Any]]] = build_export_media,
) -> dict[str, Any]:
    context = collect_export_docx_context(
        raw_request=raw_request,
        workspace_dir=workspace_dir,
        load_tender_matrix_fn=load_tender_matrix_fn,
        load_boq_data_fn=load_boq_data_fn,
        build_boq_focus_fn=build_boq_focus_fn,
        load_params_fn=load_params_fn,
        strip_nonconcrete_language_fn=strip_nonconcrete_language_fn,
        normalize_metrics_in_sections_fn=normalize_metrics_in_sections_fn,
        recommend_four_new_fn=recommend_four_new_fn,
        run_quality_checks_fn=run_quality_checks_fn,
        build_export_indexes_fn=build_export_indexes_fn,
    )
    return assemble_export_docx_payload(
        raw_request=raw_request,
        workspace_dir=workspace_dir,
        context=context,
        build_evidence_tracking_fn=build_evidence_tracking_fn,
        build_export_media_fn=build_export_media_fn,
    )


def collect_export_docx_context(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    load_tender_matrix_fn: Callable[..., dict[str, Any] | None] = load_tender_matrix,
    load_boq_data_fn: Callable[..., dict[str, Any] | None] = load_boq_data,
    build_boq_focus_fn: Callable[[dict[str, Any]], dict[str, Any]] = _build_boq_focus,
    load_params_fn: Callable[[], dict[str, Any]] = load_params,
    strip_nonconcrete_language_fn: Callable[[str], str] = strip_nonconcrete_language,
    normalize_metrics_in_sections_fn: Callable[[list[dict[str, Any]]], dict[str, Any] | None] = _normalize_metrics_in_sections,
    recommend_four_new_fn: Callable[..., Any] = recommend_four_new,
    run_quality_checks_fn: Callable[..., dict[str, Any]] = run_quality_checks,
    build_export_indexes_fn: Callable[..., dict[str, Any]] = build_export_indexes,
) -> dict[str, Any]:
    inputs = collect_export_docx_inputs(
        raw_request=raw_request,
        workspace_dir=workspace_dir,
        load_tender_matrix_fn=load_tender_matrix_fn,
        load_boq_data_fn=load_boq_data_fn,
        build_boq_focus_fn=build_boq_focus_fn,
        load_params_fn=load_params_fn,
        strip_nonconcrete_language_fn=strip_nonconcrete_language_fn,
        normalize_metrics_in_sections_fn=normalize_metrics_in_sections_fn,
    )
    analysis = compute_export_docx_analysis(
        raw_request=raw_request,
        workspace_dir=workspace_dir,
        project_id=inputs["project_id"],
        tender=inputs["tender"],
        boq=inputs["boq"],
        boq_focus=inputs["boq_focus"],
        sections=inputs["sections"],
        outline=inputs["outline"],
        recommend_four_new_fn=recommend_four_new_fn,
        run_quality_checks_fn=run_quality_checks_fn,
        build_export_indexes_fn=build_export_indexes_fn,
    )
    return {
        **inputs,
        **analysis,
    }


def collect_export_docx_inputs(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    load_tender_matrix_fn: Callable[..., dict[str, Any] | None] = load_tender_matrix,
    load_boq_data_fn: Callable[..., dict[str, Any] | None] = load_boq_data,
    build_boq_focus_fn: Callable[[dict[str, Any]], dict[str, Any]] = _build_boq_focus,
    load_params_fn: Callable[[], dict[str, Any]] = load_params,
    strip_nonconcrete_language_fn: Callable[[str], str] = strip_nonconcrete_language,
    normalize_metrics_in_sections_fn: Callable[[list[dict[str, Any]]], dict[str, Any] | None] = _normalize_metrics_in_sections,
) -> dict[str, Any]:
    project_id = str(raw_request.get("project_id") or "").strip() or None
    tender = _call_with_optional_workspace(
        load_tender_matrix_fn,
        project_id=project_id,
        workspace_dir=workspace_dir,
    ) or {}
    boq = _call_with_optional_workspace(
        load_boq_data_fn,
        project_id=project_id,
        workspace_dir=workspace_dir,
    ) or {}
    boq_focus = build_boq_focus_fn(boq)
    params = load_params_fn()
    source_sections = raw_request.get("sections") or []
    sections = copy.deepcopy(source_sections)
    formal_direct_export = raw_request.get("_formal_source_verified") is True
    if formal_direct_export:
        source_input_receipt = _validate_source_input_receipt(
            raw_request.get("source_input_receipt"),
            project_id=str(project_id or ""),
            tender=tender,
            boq=boq,
        )
        expected_digest = str(
            raw_request.get("_formal_source_sections_digest") or ""
        ).strip().lower()
        if (
            _FULL_SHA256_RE.fullmatch(expected_digest) is None
            or canonical_sections_digest(sections) != expected_digest
        ):
            raise ValueError("direct_export_source_sections_digest_invalid")
        normalized_sections = copy.deepcopy(sections)
        plan_receipt = normalize_metrics_in_sections_fn(normalized_sections)
        if canonical_sections_digest(normalized_sections) != expected_digest:
            raise ValueError("direct_export_sections_require_source_regeneration")
    else:
        for section in sections:
            section["content"] = strip_nonconcrete_language_fn(
                section.get("content") or ""
            )
        from backend.zhifei_autoplan.boq_focus_enforcer import (
            ensure_boq_focus_item_cards,
        )

        ensure_boq_focus_item_cards(
            sections,
            boq_focus,
            evidence_src=str(raw_request.get("evidence_src") or "").strip()
            or "工程量清单(解析统计)",
            params=params,
            project_id=project_id,
            boq_data=boq,
        )
        plan_receipt = normalize_metrics_in_sections_fn(sections)
    outline = raw_request.get("outline") or [section.get("title") for section in sections]
    inputs = {
        "project_id": project_id,
        "tender": tender,
        "boq": boq,
        "boq_focus": boq_focus,
        "params": params,
        "sections": sections,
        "plan_consistency": plan_receipt,
        "outline": outline,
    }
    if formal_direct_export:
        inputs["source_input_receipt"] = source_input_receipt
    return inputs


def compute_export_docx_analysis(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    project_id: str | None,
    tender: dict[str, Any],
    boq: dict[str, Any],
    boq_focus: dict[str, Any],
    sections: list[dict[str, Any]],
    outline: list[str],
    recommend_four_new_fn: Callable[..., Any] = recommend_four_new,
    run_quality_checks_fn: Callable[..., dict[str, Any]] = run_quality_checks,
    build_export_indexes_fn: Callable[..., dict[str, Any]] = build_export_indexes,
) -> dict[str, Any]:
    try:
        recommendations = recommend_four_new_fn(boq, outline=outline, limit=6, topic=str(raw_request.get("topic")))
        if isinstance(recommendations, list) and recommendations:
            boq_focus["four_new_recommendations"] = recommendations
    except Exception:  # noqa: BLE001,S110
        pass
    quality_checks = _call_with_optional_workspace(
        run_quality_checks_fn,
        tender,
        outline,
        sections,
        boq=boq,
        boq_focus=boq_focus,
        project_id=project_id,
        strict=True,
        workspace_dir=workspace_dir,
    )
    indexes = _call_with_optional_workspace(
        build_export_indexes_fn,
        topic=str(raw_request.get("topic") or ""),
        outline=outline,
        project_id=project_id,
        workspace_dir=workspace_dir,
        boq=boq,
        sections=sections,
        boq_focus=boq_focus,
        quality_checks=quality_checks,
    )
    _validate_export_indexes(indexes, boq_focus=boq_focus)
    return {
        "boq_focus": boq_focus,
        "quality_checks": quality_checks,
        "indexes": indexes,
    }


def _rebuild_formal_direct_export_receipts(
    payload: dict[str, Any],
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
) -> None:
    """Rebuild every formal gate input from final sections and current indexes."""

    if raw_request.get("_formal_source_verified") is not True:
        return

    from backend.zhifei_autoplan.compliance_policy import (
        audit_standard_citations,
        build_project_applicable_standards_manifest,
        canonical_standard_code,
    )
    from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
    from backend.zhifei_autoplan.requirement_evidence_matrix import (
        finalize_requirement_evidence_matrix,
        validate_requirement_evidence_matrix,
    )

    project_id = str(payload.get("project_id") or "").strip()
    indexes = {
        "drawing_index": payload.get("drawing_index"),
        "standard_index": payload.get("standard_index"),
        "cross_index": payload.get("cross_index"),
    }
    _validate_formal_export_indexes(indexes, project_id=project_id)

    sections = payload.get("sections")
    canonical_sections_digest(sections)
    assert isinstance(sections, list)
    evidence_tracking = payload.get("evidence_tracking")
    evidence_tracking = (
        evidence_tracking if isinstance(evidence_tracking, dict) else {}
    )
    requirement_plan = raw_request.get("requirement_evidence_plan")
    if not isinstance(requirement_plan, dict):
        raise TypeError("direct_export_requirement_plan_required")
    plan_validation = validate_requirement_evidence_matrix(requirement_plan)
    if plan_validation.get("ok") is not True:
        raise ValueError("direct_export_requirement_plan_invalid")
    chapter_pages = raw_request.get("chapter_pages")
    chapter_pages = chapter_pages if isinstance(chapter_pages, dict) else {}
    try:
        planned_total_pages = sum(
            max(0, int(value or 0)) for value in chapter_pages.values()
        )
        total_pages_limit = int(raw_request.get("total_pages_limit") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("direct_export_document_control_invalid") from exc
    requirement_matrix = finalize_requirement_evidence_matrix(
        plan=requirement_plan,
        sections=sections,
        evidence_tracking=evidence_tracking,
        document_control_evidence={
            "page_plan": {
                "planned_total_pages": planned_total_pages,
                "limit": total_pages_limit,
                "verified": bool(chapter_pages) and bool(total_pages_limit),
            },
            "format_policy": {
                "source": str(raw_request.get("style_source") or ""),
                "verified": bool(raw_request.get("style"))
                and not bool(
                    (
                        raw_request.get("requirement_decision_matrix")
                        if isinstance(
                            raw_request.get("requirement_decision_matrix"), dict
                        )
                        else {}
                    ).get("unresolved_fields")
                ),
            },
        },
    )
    requirement_validation = validate_requirement_evidence_matrix(
        requirement_matrix
    )
    if requirement_validation.get("ok") is not True:
        raise ValueError("direct_export_requirement_matrix_invalid")
    payload["requirement_evidence_matrix"] = requirement_matrix
    payload["requirement_evidence_validation"] = requirement_validation

    standard_manifest = build_project_applicable_standards_manifest(sections)
    standard_audit = audit_standard_citations(sections, standard_manifest)
    standard_index = indexes["standard_index"]
    assert isinstance(standard_index, dict)
    current_codes: set[str] = set()
    for row in standard_index.get("standards") or []:
        if (
            not isinstance(row, dict)
            or not str(row.get("official_registry_status") or "").startswith(
                "verified_"
            )
            or row.get("source_integrity_status") != "verified"
        ):
            continue
        canonical = canonical_standard_code(row.get("standard_code"))
        if canonical:
            current_codes.add(canonical)
    manifest_codes = {
        canonical_standard_code(
            (row.get("standard_code_and_name") or {}).get("code")
        )
        for row in (standard_manifest.get("verified_standards") or [])
        if isinstance(row, dict)
    }
    manifest_codes.discard("")
    stale_codes = sorted(manifest_codes - current_codes)
    if stale_codes:
        violations = list(standard_audit.get("violations") or [])
        violations.extend(
            {
                "chapter": "项目适用规范清单",
                "standard_code": code,
                "reason": "standard_absent_from_current_verified_index",
            }
            for code in stale_codes
        )
        standard_audit = {
            **standard_audit,
            "ok": False,
            "violation_count": len(violations),
            "violations": violations,
        }
    payload["project_applicable_standards"] = standard_manifest
    payload["standard_citation_audit"] = standard_audit

    registry_authority = load_runtime_registry_authority()
    if str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1" and (
        str(standard_index.get("official_registry_sha256") or "")
        != str(registry_authority.projection.get("registry_sha256") or "")
        or Path(str(standard_index.get("official_registry_path") or ""))
        != registry_authority.path
    ):
        raise ValueError("direct_export_registry_authority_mismatch")

    quality = payload.get("quality_checks")
    quality = quality if isinstance(quality, dict) else {}
    routing = raw_request.get("model_routing")
    routing = routing if isinstance(routing, dict) else {}
    gate = build_delivery_quality_gate(
        strict=True,
        content_review=(
            quality.get("independent_content_review")
            if isinstance(quality.get("independent_content_review"), dict)
            else {}
        ),
        plan_consistency=(
            payload.get("plan_consistency")
            if isinstance(payload.get("plan_consistency"), dict)
            else {}
        ),
        model_review_audit=(
            routing.get("review_audit")
            if isinstance(routing.get("review_audit"), dict)
            else {}
        ),
        requirement_matrix=requirement_matrix,
        standard_audit=standard_audit,
        cross_index=indexes["cross_index"],
        model_review_required=True,
        formal_delivery_required=True,
        project_parameters=(
            raw_request.get("missing_parameters")
            if isinstance(raw_request.get("missing_parameters"), dict)
            else {}
        ),
        project_fact_ledger=(
            raw_request.get("project_fact_ledger")
            if isinstance(raw_request.get("project_fact_ledger"), dict)
            else {}
        ),
        sections=sections,
        standard_index=indexes["standard_index"],
        standard_workspace_dir=workspace_dir,
        standard_compliance_root=registry_authority.path.parent,
        trusted_standard_registry_bytes=registry_authority.raw,
    )
    payload["delivery_quality_gate"] = gate
    quality["delivery_quality_gate"] = gate
    payload["quality_checks"] = quality
    payload["delivery_scope"] = "document"
    payload["dry_run"] = False
    payload["delivery_ready"] = gate.get("delivery_allowed") is True
    _attach_direct_export_binding(payload, raw_request=raw_request)


def assemble_export_docx_payload(
    *,
    raw_request: dict[str, Any],
    workspace_dir: str,
    context: dict[str, Any],
    build_evidence_tracking_fn: Callable[..., dict[str, Any]] = build_evidence_tracking,
    build_export_media_fn: Callable[..., list[dict[str, Any]]] = build_export_media,
) -> dict[str, Any]:
    project_id = str(context.get("project_id") or "").strip() or None
    tender = context.get("tender") if isinstance(context.get("tender"), dict) else {}
    boq = context.get("boq") if isinstance(context.get("boq"), dict) else {}
    boq_focus = context.get("boq_focus") if isinstance(context.get("boq_focus"), dict) else {}
    params = context.get("params") if isinstance(context.get("params"), dict) else {}
    sections = context.get("sections") if isinstance(context.get("sections"), list) else []
    outline = context.get("outline") if isinstance(context.get("outline"), list) else []
    quality_checks = context.get("quality_checks") if isinstance(context.get("quality_checks"), dict) else {}
    indexes = context.get("indexes") if isinstance(context.get("indexes"), dict) else {}
    payload = build_export_docx_base_payload(
        raw_request=raw_request,
        project_id=project_id,
        tender=tender,
        sections=sections,
        outline=outline,
        quality_checks=quality_checks,
        boq_focus=boq_focus,
        indexes=indexes,
        plan_consistency=context.get("plan_consistency"),
    )
    branding = build_export_docx_branding(raw_request=raw_request, project_id=project_id)
    if branding is not None:
        payload["branding"] = branding
    source_input_receipt = context.get("source_input_receipt")
    if isinstance(source_input_receipt, dict):
        payload["source_input_receipt"] = dict(source_input_receipt)
    payload["evidence_tracking"] = build_export_docx_evidence(
        sections=sections,
        tender=tender,
        build_evidence_tracking_fn=build_evidence_tracking_fn,
    )
    _rebuild_formal_direct_export_receipts(
        payload,
        raw_request=raw_request,
        workspace_dir=workspace_dir,
    )
    media = build_export_docx_media_attachment(
        raw_request=raw_request,
        project_id=project_id,
        boq=boq,
        params=params,
        outline=outline,
        workspace_dir=workspace_dir,
        build_export_media_fn=build_export_media_fn,
    )
    if media:
        payload["media"] = media
    return payload


def build_export_docx_base_payload(
    *,
    raw_request: dict[str, Any],
    project_id: str | None,
    tender: dict[str, Any],
    sections: list[dict[str, Any]],
    outline: list[str],
    quality_checks: dict[str, Any],
    boq_focus: dict[str, Any],
    indexes: dict[str, Any],
    plan_consistency: Any,
) -> dict[str, Any]:
    payload = {
        "topic": raw_request.get("topic"),
        "project_id": project_id,
        "project_name": str(tender.get("project_name") or "").strip() if isinstance(tender, dict) else "",
        "project_code": str(tender.get("project_code") or "").strip() if isinstance(tender, dict) else "",
        "style": raw_request.get("style") or {},
        "outline": outline,
        "sections": sections,
        "quality_checks": quality_checks,
        "boq_focus": boq_focus,
        "drawing_index": indexes.get("drawing_index"),
        "standard_index": indexes.get("standard_index"),
        "cross_index": indexes.get("cross_index"),
        "plan_consistency": plan_consistency,
    }
    generation_release = raw_request.get(
        "_formal_source_generation_release_identity"
    )
    registry_authority = raw_request.get(
        "_formal_source_compliance_registry_authority"
    )
    if isinstance(generation_release, dict):
        payload["generation_release_identity"] = dict(generation_release)
    if isinstance(registry_authority, dict):
        payload["compliance_registry_authority"] = dict(registry_authority)
    return payload


def build_export_docx_branding(
    *,
    raw_request: dict[str, Any],
    project_id: str | None,
) -> dict[str, Any] | None:
    if project_id or raw_request.get("bidder_company") or raw_request.get("logo_url") or raw_request.get("bidder_domain"):
        return {
            "project_id": project_id,
            "bidder_company": raw_request.get("bidder_company"),
            "bidder_domain": raw_request.get("bidder_domain"),
            "logo_url": raw_request.get("logo_url"),
        }
    return None


def build_export_docx_evidence(
    *,
    sections: list[dict[str, Any]],
    tender: dict[str, Any],
    build_evidence_tracking_fn: Callable[..., dict[str, Any]] = build_evidence_tracking,
) -> dict[str, Any]:
    try:
        return build_evidence_tracking_fn(
            sections=sections,
            tender=tender,
            chapter_pages={},
        )
    except Exception:  # noqa: BLE001
        return {"rows": [], "summary": {}}


def build_export_docx_media_attachment(
    *,
    raw_request: dict[str, Any],
    project_id: str | None,
    boq: dict[str, Any],
    params: dict[str, Any],
    outline: list[str],
    workspace_dir: str,
    build_export_media_fn: Callable[..., list[dict[str, Any]]] = build_export_media,
) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    def _append_media_rows(rows: Any) -> None:
        if not isinstance(rows, list):
            return
        for item in rows:
            if isinstance(item, dict):
                path = str(item.get("path") or "").strip()
                if not path or path in seen_paths:
                    continue
                seen_paths.add(path)
                media.append(dict(item))
                continue
            path = str(item or "").strip()
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            media.append({"path": path})

    _append_media_rows(raw_request.get("media"))
    _append_media_rows(image_selection_pack_media_entries(raw_request.get("image_selection_pack")))
    for section in raw_request.get("sections") or []:
        if not isinstance(section, dict):
            continue
        _append_media_rows(image_selection_pack_media_entries(section.get("image_selection_pack")))

    if bool(raw_request.get("generate_images", True)):
        _append_media_rows(
            build_export_media_fn(
                raw_request=raw_request,
                project_id=project_id,
                boq=boq,
                params=params,
                outline=outline,
                workspace_dir=workspace_dir,
            )
        )
    return media
