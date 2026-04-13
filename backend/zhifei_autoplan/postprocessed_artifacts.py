from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.params_runtime import load_params
from backend.zhifei_autoplan.quality_check import run_quality_checks
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.variant_similarity import pair_similarity


CASE_REFERENCE_COPY_MIN_CHARS = 240
CASE_REFERENCE_COPY_THRESHOLD = 0.9


def workspace_dir_from_payload(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    return str(payload.get("workspace_dir") or "").strip() or None


def _resolve_existing_path(raw_path: Any, *, workspace_dir: str | None = None) -> Path | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    candidate = Path(text)
    search_paths = [candidate]
    if workspace_dir and not candidate.is_absolute():
        search_paths.insert(0, Path(workspace_dir) / candidate)
    if not candidate.is_absolute():
        search_paths.append(Path.cwd() / candidate)
    for path in search_paths:
        try:
            if path.exists() and path.is_file():
                return path
        except Exception:
            continue
    return None


def _load_case_reference_text(hit: dict[str, Any], *, workspace_dir: str | None = None) -> str:
    if not isinstance(hit, dict):
        return ""
    path = _resolve_existing_path(hit.get("extract_saved_as"), workspace_dir=workspace_dir)
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _append_case_reference_copy_risks(
    quality_checks: dict[str, Any],
    *,
    sections: list[dict[str, Any]],
    fallback_case_pack: dict[str, Any] | None,
    workspace_dir: str | None = None,
) -> None:
    issue_list = quality_checks.setdefault("issue_list", [])
    auto_recs = quality_checks.setdefault("auto_revision_suggestions", [])
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip() or "章节"
        content = str(section.get("content") or "")
        if len(content.strip()) < CASE_REFERENCE_COPY_MIN_CHARS:
            continue
        case_pack = section.get("case_reference_pack") if isinstance(section.get("case_reference_pack"), dict) else fallback_case_pack
        hits = case_pack.get("hits") if isinstance(case_pack, dict) and isinstance(case_pack.get("hits"), list) else []
        if not hits:
            continue
        best_hit: dict[str, Any] | None = None
        best_similarity = 0.0
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            reference_text = _load_case_reference_text(hit, workspace_dir=workspace_dir)
            if len(reference_text.strip()) < CASE_REFERENCE_COPY_MIN_CHARS:
                continue
            similarity = float(pair_similarity(content, reference_text).get("combined") or 0.0)
            if similarity > best_similarity:
                best_similarity = similarity
                best_hit = hit
        if best_hit is None or best_similarity < CASE_REFERENCE_COPY_THRESHOLD:
            continue
        case_label = str(best_hit.get("title") or best_hit.get("filename") or best_hit.get("case_id") or "").strip() or "案例"
        case_id = str(best_hit.get("case_id") or "").strip()
        similarity_text = f"{best_similarity:.2f}"
        msg = (
            f"章节与案例“{case_label}”相似度过高（combined={similarity_text}）。"
            "案例库仅可借鉴结构、格式和表达方式，不得直接改写或照搬正文；"
            "请保留本项目事实约束，重写本章步骤、责任、频次、验收与记录表达。"
        )
        issue = {
            "severity": "high",
            "title": title,
            "type": "case_reference_copy_risk",
            "problem": msg,
            "suggestion": msg,
        }
        if case_id:
            issue["reference_case_id"] = case_id
        issue_list.append(issue)
        recommendation = {
            "title": title,
            "type": "case_reference_copy_risk",
            "suggestion": msg,
        }
        if case_id:
            recommendation["reference_case_id"] = case_id
        auto_recs.append(recommendation)


def rebuild_postprocessed_artifacts(
    results: list[dict],
    *,
    payload: dict,
    report: dict | None,
    params: dict | None,
    workspace_dir: str | None = None,
) -> None:
    pid = str(payload.get("project_id") or "").strip() or None
    strict = bool(payload.get("quality_strict", True))
    workspace_dir = str(workspace_dir or "").strip() or workspace_dir_from_payload(payload)

    tender = load_tender_matrix(project_id=pid, workspace_dir=workspace_dir) or {}
    boq = load_boq_data(project_id=pid, workspace_dir=workspace_dir) or {}
    base_focus = _build_boq_focus(boq)

    if not isinstance(params, dict):
        params = load_params()
        overrides = payload.get("params_override")
        if isinstance(overrides, dict) and overrides:
            for k, v in overrides.items():
                if isinstance(v, dict) and isinstance(params.get(k), dict):
                    merged = dict(params.get(k) or {})
                    merged.update(v)
                    params[k] = merged
                else:
                    params[k] = v

    try:
        outline_base = payload.get("outline") if isinstance(payload.get("outline"), list) else []
        recs = recommend_four_new(boq, outline=outline_base, limit=6, topic=str(payload.get("topic") or ""))
        if isinstance(recs, list) and recs:
            base_focus["four_new_recommendations"] = recs
    except Exception:
        pass

    for v in results:
        if not isinstance(v, dict):
            continue
        sections = v.get("sections") if isinstance(v.get("sections"), list) else []
        outline = v.get("outline") if isinstance(v.get("outline"), list) and v.get("outline") else []
        if not outline:
            outline = [str(s.get("title") or "").strip() for s in sections if isinstance(s, dict) and str(s.get("title") or "").strip()]

        boq_focus = v.get("boq_focus") if isinstance(v.get("boq_focus"), dict) else base_focus
        if isinstance(boq_focus, dict) and isinstance(base_focus.get("four_new_recommendations"), list):
            if not isinstance(boq_focus.get("four_new_recommendations"), list):
                merged = dict(boq_focus)
                merged["four_new_recommendations"] = base_focus.get("four_new_recommendations") or []
                boq_focus = merged
                v["boq_focus"] = merged

        try:
            from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

            v["plan_consistency"] = normalize_metrics_in_sections(sections)
        except Exception:
            pass

        try:
            from backend.zhifei_autoplan.param_trace import build_param_receipt, save_latest_receipt

            receipt = build_param_receipt(sections, params)
            saved_at = save_latest_receipt(
                receipt,
                project_id=str(pid) if pid else None,
                workspace_dir=workspace_dir,
            )
            v["param_trace"] = {"ok": True, "saved_at": saved_at, "receipt": receipt}
        except Exception:
            pass

        qc = run_quality_checks(
            tender,
            outline,
            sections,
            boq=boq,
            boq_focus=boq_focus,
            project_id=pid,
            strict=strict,
            workspace_dir=workspace_dir,
        )
        fallback_case_pack = v.get("case_reference_pack") if isinstance(v.get("case_reference_pack"), dict) else None
        _append_case_reference_copy_risks(
            qc,
            sections=sections,
            fallback_case_pack=fallback_case_pack,
            workspace_dir=workspace_dir,
        )

        if isinstance(report, dict) and int(report.get("variant_count") or 0) >= 2:
            v["variant_similarity"] = report
            qc["variant_diversity"] = {
                "ok": bool(report.get("ok")),
                "avg_max_similarity": report.get("avg_max_similarity"),
                "avg_max_similarity_all": report.get("avg_max_similarity_all"),
                "flagged_count": report.get("flagged_count"),
                "relaxed_flagged_count": report.get("relaxed_flagged_count"),
                "chapter_threshold": report.get("chapter_threshold"),
                "relaxed_chapter_threshold": report.get("relaxed_chapter_threshold"),
                "overall_threshold": report.get("overall_threshold"),
                "flagged": report.get("flagged") or [],
                "relaxed_flagged": report.get("relaxed_flagged") or [],
            }
            if report.get("ok") is False:
                issue_list = qc.setdefault("issue_list", [])
                auto_recs = qc.setdefault("auto_revision_suggestions", [])
                for f in (report.get("flagged") or [])[:10]:
                    title = str(f.get("title") or "").strip() or "章节"
                    pair = str(f.get("pair") or "").strip() or "pair"
                    sim = f.get("similarity")
                    s_sim = str(sim) if sim is not None else ""
                    msg = (
                        f"多方案相似度过高：{pair}={s_sim}。要求：不改招标目录，仅重写本章章内逻辑；"
                        "强制使用模版锚点标题（A=交付物/约束/步骤/闭环，B=工序流程/控制点表/资源节拍，C=指标矩阵/人机料法环/闭环分组），"
                        "并把同类条目改为“清单项控制卡/闭环卡片/指标矩阵”短句结构，避免段落复述。"
                    )
                    issue_list.append(
                        {
                            "severity": "high",
                            "title": title,
                            "type": "variant_diversity_gap",
                            "problem": msg,
                            "suggestion": msg,
                        }
                    )
                    auto_recs.append({"title": title, "type": "variant_diversity_gap", "suggestion": msg})

        v["quality_checks"] = qc

        try:
            from backend.zhifei_autoplan.cross_index import build_cross_index

            drawing_index = v.get("drawing_index") if isinstance(v.get("drawing_index"), dict) else None
            standard_index = v.get("standard_index") if isinstance(v.get("standard_index"), dict) else None
            v["cross_index"] = build_cross_index(
                boq=boq,
                sections=sections,
                boq_focus=boq_focus,
                drawing_index=drawing_index,
                standard_index=standard_index,
                quality_checks=qc,
                project_id=pid,
            )
        except Exception:
            pass
        try:
            v["evidence_tracking"] = build_evidence_tracking(
                sections=sections,
                tender=tender,
                chapter_pages=v.get("chapter_pages") if isinstance(v.get("chapter_pages"), dict) else {},
            )
        except Exception:
            v["evidence_tracking"] = {"rows": [], "summary": {}}
