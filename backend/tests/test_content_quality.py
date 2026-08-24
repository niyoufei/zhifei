from __future__ import annotations

from backend.zhifei_autoplan.content_quality import build_independent_content_review


def _checks(ok: bool) -> dict:
    scalar_names = (
        "score_coverage",
        "required_topics",
        "chapter_blueprint_adherence",
        "core_conclusion_evidence",
        "boq_focus_item_closure",
        "qse_closed_loop",
        "content_specificity",
        "vague_terms",
        "officialese",
        "repetition_control",
        "structure",
        "content_density",
        "logic_template_adherence",
    )
    result = {name: {"ok": ok} for name in scalar_names}
    for name in (
        "evidence_quality",
        "evidence_traceability",
        "engineering",
        "quantitative",
        "risk_triplet",
        "closed_loop",
    ):
        result[name] = {"by_section": [{"title": "施工方案", "ok": ok}]}
    result["engineering_by_section"] = [{"title": "施工方案", "ok": ok}]
    result["closed_loop_by_section"] = [{"title": "施工方案", "ok": ok}]
    result["score_coverage_by_section"] = [{"title": "施工方案", "ok": ok}]
    return result


def test_high_quality_content_passes_strict_gate():
    review = build_independent_content_review(
        _checks(True),
        sections=[{"title": "施工方案", "content": "本章结合本项目清单、图纸接口和工期条件，明确工序、资源、风险控制、检验与验收记录。" * 3}],
        strict=True,
    )
    assert review["score"] == 100
    assert review["quality_gate"]["pass"] is True


def test_low_quality_dimensions_block_strict_delivery():
    review = build_independent_content_review(
        _checks(False),
        sections=[{"title": "施工方案", "content": "本章为完整章节正文。" * 12}],
        strict=True,
    )
    codes = {row["code"] for row in review["quality_gate"]["blocking_issues"]}
    assert review["quality_gate"]["pass"] is False
    assert "QUALITY_SCORE_BELOW_THRESHOLD" in codes
    assert "TENDER_ALIGNMENT_GAP" in codes


def test_trivial_chapter_is_always_blocked():
    review = build_independent_content_review(
        _checks(True),
        sections=[{"title": "施工方案", "content": "内容不足"}],
        strict=False,
    )
    assert review["quality_gate"]["pass"] is False
    assert review["by_section"][0]["status"] == "blocked"


def test_weak_chapter_cannot_ride_on_other_dimension_scores_in_strict_mode():
    checks = _checks(True)
    for name in (
        "score_coverage_by_section",
        "evidence_quality",
        "evidence_traceability",
        "engineering_by_section",
        "quantitative",
        "risk_triplet",
        "closed_loop_by_section",
    ):
        value = checks[name]
        rows = value if isinstance(value, list) else value["by_section"]
        rows[0]["ok"] = False
    review = build_independent_content_review(
        checks,
        sections=[{"title": "施工方案", "content": "项目专属施工工序、资源投入、风险控制和验收记录。" * 8}],
        strict=True,
    )
    assert review["by_section"][0]["status"] == "blocked"
    assert "CHAPTER_QUALITY_BELOW_THRESHOLD" in {
        row["code"] for row in review["quality_gate"]["blocking_issues"]
    }
