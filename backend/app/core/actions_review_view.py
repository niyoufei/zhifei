from __future__ import annotations

from typing import Dict


def select_review_variant(variants: list[dict], requested_variant: int) -> tuple[int, dict]:
    if not variants:
        return 1, {}
    variant_no = max(1, int(requested_variant or 1))
    if variant_no <= len(variants):
        return variant_no, variants[variant_no - 1]
    return 1, variants[0]


def build_review_issues_response(
    *,
    job_id: str,
    requested_variant: int,
    variants: list[dict],
    review_items_fn= None,
) -> dict:
    selected_variant, record = select_review_variant(variants, requested_variant)
    items_builder = review_items_fn or review_items_for_variant
    items = items_builder(record)
    return {
        "ok": True,
        "job_id": job_id,
        "variant": int(selected_variant),
        "count": len(items),
        "items": items,
    }


def _reference_context_for_issue(variant_rec: dict, *, title: str, reference_case_id: str) -> dict:
    case_id = str(reference_case_id or "").strip()
    if not case_id:
        return {}
    sections = variant_rec.get("sections") if isinstance(variant_rec.get("sections"), list) else []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        sec_title = str(sec.get("title") or "").strip()
        if sec_title != title:
            continue
        case_pack = sec.get("case_reference_pack") if isinstance(sec.get("case_reference_pack"), dict) else {}
        if not case_pack:
            break
        hits = case_pack.get("hits") if isinstance(case_pack.get("hits"), list) else []
        match_hit = None
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            if str(hit.get("case_id") or "").strip() == case_id:
                match_hit = hit
                break
        context = {
            "reference_case_id": case_id,
            "match_reason": str(case_pack.get("match_reason") or "").strip() or None,
            "non_fact_reference_notice": str(case_pack.get("non_fact_reference_notice") or "").strip() or None,
        }
        if isinstance(match_hit, dict):
            context["reference_case_title"] = str(
                match_hit.get("title") or match_hit.get("filename") or match_hit.get("case_id") or ""
            ).strip() or None
        return {key: value for key, value in context.items() if value is not None}
    return {"reference_case_id": case_id}


def review_items_for_variant(variant_rec: dict, *, max_excerpt: int = 320) -> list[dict]:
    qc = variant_rec.get("quality_checks") if isinstance(variant_rec.get("quality_checks"), dict) else {}
    issues = qc.get("issue_list") if isinstance(qc.get("issue_list"), list) else []
    recs = qc.get("auto_revision_suggestions") if isinstance(qc.get("auto_revision_suggestions"), list) else []
    sections = variant_rec.get("sections") if isinstance(variant_rec.get("sections"), list) else []

    title_to_excerpt: Dict[str, str] = {}
    for s in sections:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "").strip()
        if not title or title in title_to_excerpt:
            continue
        content = str(s.get("content") or "").strip()
        title_to_excerpt[title] = content[:max_excerpt] + ("..." if len(content) > max_excerpt else "")

    out: list[dict] = []
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title") or "").strip() or "章节"
        reference_case_id = str(issue.get("reference_case_id") or "").strip()
        reference_context = _reference_context_for_issue(
            variant_rec,
            title=title,
            reference_case_id=reference_case_id,
        )
        out.append(
            {
                "issue_id": f"I{index:04d}",
                "source": "issue_list",
                "title": title,
                "type": str(issue.get("type") or "issue"),
                "severity": str(issue.get("severity") or "medium"),
                "severity_rank": severity_rank.get(str(issue.get("severity") or "").lower(), 2),
                "problem": str(issue.get("problem") or ""),
                "suggestion": str(issue.get("suggestion") or ""),
                "section_excerpt": title_to_excerpt.get(title, ""),
                "apply": True,
                "replacement": "",
                "reference_case_id": reference_case_id or None,
                "reference_context": reference_context,
            }
        )

    seen = {(str(item.get("title")), str(item.get("type")), str(item.get("suggestion"))) for item in out}
    rec_index = 0
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        title = str(rec.get("title") or "").strip() or "章节"
        rec_type = str(rec.get("type") or "issue")
        suggestion = str(rec.get("suggestion") or "")
        reference_case_id = str(rec.get("reference_case_id") or "").strip()
        reference_context = _reference_context_for_issue(
            variant_rec,
            title=title,
            reference_case_id=reference_case_id,
        )
        key = (title, rec_type, suggestion)
        if key in seen:
            continue
        seen.add(key)
        rec_index += 1
        out.append(
            {
                "issue_id": f"R{rec_index:04d}",
                "source": "auto_revision_suggestions",
                "title": title,
                "type": rec_type,
                "severity": "medium",
                "severity_rank": 2,
                "problem": "",
                "suggestion": suggestion,
                "section_excerpt": title_to_excerpt.get(title, ""),
                "apply": True,
                "replacement": "",
                "reference_case_id": reference_case_id or None,
                "reference_context": reference_context,
            }
        )
    out.sort(key=lambda item: (-int(item.get("severity_rank") or 0), str(item.get("title") or ""), str(item.get("type") or "")))
    return out
