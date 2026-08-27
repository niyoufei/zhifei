from __future__ import annotations

import inspect
from typing import Any, Callable

from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.image_library import image_selection_pack_media_entries
from backend.zhifei_autoplan.job_store import create_job, update_job
from backend.zhifei_autoplan.media import generate_boq_chart, generate_ingested_previews, generate_outline_mindmap
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.params_runtime import get_image_defaults, load_params
from backend.zhifei_autoplan.quality_check import run_quality_checks, strip_nonconcrete_language
from backend.zhifei_autoplan.tender_store import load_tender_matrix


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
        from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

        return normalize_metrics_in_sections(sections)
    except Exception:
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
    drawing_index = None
    standard_index = None
    cross_index = None
    try:
        from backend.zhifei_autoplan.cross_index import build_cross_index
        from backend.zhifei_autoplan.drawing_index import build_drawing_index
        from backend.zhifei_autoplan.standard_index import build_standard_index

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
        )
        cross_index = build_cross_index(
            boq=boq,
            sections=sections,
            boq_focus=boq_focus,
            drawing_index=drawing_index,
            standard_index=standard_index,
            quality_checks=quality_checks,
            project_id=project_id,
        )
    except Exception:
        drawing_index = None
        standard_index = None
        cross_index = None
    return {
        "drawing_index": drawing_index,
        "standard_index": standard_index,
        "cross_index": cross_index,
    }


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
    except Exception:
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
            from backend.zhifei_autoplan.logo_runtime import prepare_logo_for_embedding, resolve_logo

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
    except Exception:
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
        except Exception:
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
    if save_outputs_fn is None:
        raise ValueError("save_outputs_fn required")
    job_id = _call_with_optional_workspace(
        create_job_fn,
        {"action": "export_docx", "workspace_dir": workspace_dir},
        user_id=None,
        workspace_dir=workspace_dir,
    )
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
    sections = [dict(section) for section in raw_request.get("sections") or []]
    for section in sections:
        section["content"] = strip_nonconcrete_language_fn(section.get("content") or "")
    plan_receipt = normalize_metrics_in_sections_fn(sections)
    outline = raw_request.get("outline") or [section.get("title") for section in sections]
    return {
        "project_id": project_id,
        "tender": tender,
        "boq": boq,
        "boq_focus": boq_focus,
        "params": params,
        "sections": sections,
        "plan_consistency": plan_receipt,
        "outline": outline,
    }


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
    except Exception:
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
    return {
        "boq_focus": boq_focus,
        "quality_checks": quality_checks,
        "indexes": indexes,
    }


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
    payload["evidence_tracking"] = build_export_docx_evidence(
        sections=sections,
        tender=tender,
        build_evidence_tracking_fn=build_evidence_tracking_fn,
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
    return {
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
    except Exception:
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
