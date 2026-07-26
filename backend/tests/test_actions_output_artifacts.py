from __future__ import annotations

import json
from pathlib import Path

from backend.tests.export_test_contract_fixtures import export_admissible_sections
from backend.app.routers.actions_bridge import _save_outputs


def test_save_outputs_includes_new_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    variant = {
        "topic": "测试施组",
        "project_id": "P-OUT-1",
        "style": {"body_font": "宋体", "title_font": "宋体"},
        "outline": ["工程概况", "主要施工方法"],
        "sections": export_admissible_sections([
            {
                "title": "工程概况",
                "content": "项目概况及施工范围。",
                "case_reference_pack": {"enabled": True, "match_reason": "selected_case_ids", "hits": [{"case_id": "case-1"}]},
                "image_selection_pack": {"enabled": True, "match_reason": "selected_image_ids", "images": [{"image_id": "image-1"}]},
            },
            {"title": "主要施工方法", "content": "施工流程与质量控制。"},
        ]),
        "case_reference_pack": {
            "enabled": True,
            "chapters": [{"matched_chapter": "工程概况", "match_reason": "selected_case_ids", "hit_count": 1}],
        },
        "image_selection_pack": {
            "enabled": True,
            "chapters": [{"matched_chapter": "工程概况", "match_reason": "selected_image_ids", "hit_count": 1}],
        },
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

    out = _save_outputs("actions_test", [variant])
    assert isinstance(out, dict)
    assert out.get("score_overview_xlsx")
    assert out.get("expert_review_docx")
    assert Path(out["score_overview_xlsx"][0]).exists()
    assert Path(out["expert_review_docx"][0]).exists()
    payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
    saved = payload["variants"][0]
    assert saved["case_reference_pack"]["chapters"][0]["match_reason"] == "selected_case_ids"
    assert saved["image_selection_pack"]["chapters"][0]["match_reason"] == "selected_image_ids"
    assert saved["sections"][0]["case_reference_pack"]["hits"][0]["case_id"] == "case-1"
    assert saved["sections"][0]["image_selection_pack"]["images"][0]["image_id"] == "image-1"
