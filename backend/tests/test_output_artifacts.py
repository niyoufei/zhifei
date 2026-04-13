from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.output_artifacts import save_outputs


def test_save_outputs_shared_module_includes_new_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    variant = {
        "topic": "测试施组",
        "project_id": "P-OUT-2",
        "style": {"body_font": "宋体", "title_font": "宋体"},
        "outline": ["工程概况", "主要施工方法"],
        "sections": [
            {"title": "工程概况", "content": "项目概况及施工范围。"},
            {"title": "主要施工方法", "content": "施工流程与质量控制。"},
        ],
        "quality_checks": {"issue_list": [], "auto_revision_suggestions": []},
        "score_mapping": {"item_cards": [], "high_risk_items": []},
        "evidence_tracking": {
            "rows": [
                {
                    "paragraph_id": "S01-P001",
                    "section_title": "工程概况",
                    "paragraph_index": 1,
                    "page_estimate": 1,
                    "tender_score_points": [],
                    "system_response": "项目概况及施工范围。",
                    "evidence_sources": ["AUTO://no_explicit_evidence"],
                    "evidence_typed": {"graph_nodes": [], "drawing_refs": [], "standard_refs": [], "other_refs": ["AUTO://no_explicit_evidence"]},
                }
            ],
            "summary": {"paragraph_count": 1},
        },
        "boq_wbs_cpm": {"summary": {"project_duration_days": 30, "resource_peak": 20, "critical_interval_days": 3}},
    }

    out = save_outputs("actions_test_shared", [variant])

    assert isinstance(out, dict)
    assert out.get("score_overview_xlsx")
    assert out.get("expert_review_docx")
    assert Path(out["score_overview_xlsx"][0]).exists()
    assert Path(out["expert_review_docx"][0]).exists()
