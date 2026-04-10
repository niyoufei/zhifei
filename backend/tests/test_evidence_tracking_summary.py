from __future__ import annotations

from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking


def test_build_evidence_tracking_summary_includes_section_level_metrics():
    sections = [
        {
            "title": "工程概况",
            "content": "项目范围与场地条件。\n【证据:招标文件.pdf#p2_ab12cd34@100】",
        },
        {
            "title": "主要施工方法",
            "content": "工序安排与控制点。\n【证据:AUTO://no_explicit_evidence】",
        },
    ]
    tender = {
        "items": [
            {"rule_id": "I-1", "dimension": "工程概况", "keywords": ["项目范围"]},
            {"rule_id": "I-2", "dimension": "主要施工方法", "keywords": ["工序"]},
        ]
    }
    out = build_evidence_tracking(sections=sections, tender=tender, chapter_pages={})
    s = out.get("summary") or {}
    assert int(s.get("section_count") or 0) == 2
    assert int(s.get("score_point_bound_sections") or 0) >= 1
    assert int(s.get("evidence_bound_sections") or 0) == 1
    assert int(s.get("traceable_locator_sections") or 0) == 1
