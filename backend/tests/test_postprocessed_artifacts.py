from __future__ import annotations

import sys
import types
from pathlib import Path

from backend.zhifei_autoplan import postprocessed_artifacts


def test_workspace_dir_from_payload_handles_missing_values():
    assert postprocessed_artifacts.workspace_dir_from_payload(None) is None
    assert postprocessed_artifacts.workspace_dir_from_payload({}) is None
    assert postprocessed_artifacts.workspace_dir_from_payload({"workspace_dir": "  "}) is None
    assert postprocessed_artifacts.workspace_dir_from_payload({"workspace_dir": "/tmp/ws"}) == "/tmp/ws"


def test_rebuild_postprocessed_artifacts_refreshes_derived_fields(monkeypatch):
    calls: dict[str, object] = {}

    monkeypatch.setattr(postprocessed_artifacts, "load_tender_matrix", lambda **kwargs: {"project_id": kwargs.get("project_id")})
    monkeypatch.setattr(postprocessed_artifacts, "load_boq_data", lambda **kwargs: {"items": [1, 2]})
    monkeypatch.setattr(postprocessed_artifacts, "_build_boq_focus", lambda boq: {"boq_size": len(boq.get("items") or [])})
    monkeypatch.setattr(postprocessed_artifacts, "load_params", lambda: {"default": {"value": 1}})
    monkeypatch.setattr(postprocessed_artifacts, "recommend_four_new", lambda *args, **kwargs: ["new-tech"])

    def fake_run_quality_checks(
        tender,
        outline,
        sections,
        *,
        boq,
        boq_focus,
        project_id,
        strict,
        workspace_dir,
    ):
        calls["quality_checks"] = {
            "tender": tender,
            "outline": outline,
            "section_count": len(sections),
            "boq_focus": boq_focus,
            "project_id": project_id,
            "strict": strict,
            "workspace_dir": workspace_dir,
        }
        return {"issue_list": [], "auto_revision_suggestions": []}

    monkeypatch.setattr(postprocessed_artifacts, "run_quality_checks", fake_run_quality_checks)
    monkeypatch.setattr(
        postprocessed_artifacts,
        "build_evidence_tracking",
        lambda **kwargs: {"rows": [{"section_count": len(kwargs.get("sections") or [])}], "summary": {"count": 1}},
    )

    monkeypatch.setitem(
        sys.modules,
        "backend.zhifei_autoplan.plan_consistency",
        types.SimpleNamespace(normalize_metrics_in_sections=lambda sections: {"normalized": len(sections)}),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.zhifei_autoplan.param_trace",
        types.SimpleNamespace(
            build_param_receipt=lambda sections, params: {"section_count": len(sections), "params": params},
            save_latest_receipt=lambda receipt, project_id=None, workspace_dir=None: f"{project_id}:{workspace_dir}",
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.zhifei_autoplan.cross_index",
        types.SimpleNamespace(
            build_cross_index=lambda **kwargs: {
                "project_id": kwargs.get("project_id"),
                "issue_count": len((kwargs.get("quality_checks") or {}).get("issue_list") or []),
            }
        ),
    )

    results = [
        {
            "sections": [{"title": "工程概况", "content": "正文"}],
            "chapter_pages": {"工程概况": 2},
        }
    ]
    report = {
        "variant_count": 2,
        "ok": False,
        "avg_max_similarity": 0.91,
        "avg_max_similarity_all": 0.87,
        "flagged_count": 1,
        "relaxed_flagged_count": 0,
        "chapter_threshold": 0.85,
        "relaxed_chapter_threshold": 0.8,
        "overall_threshold": 0.88,
        "flagged": [{"title": "工程概况", "pair": "v1-v2", "similarity": 0.95}],
        "relaxed_flagged": [],
    }

    postprocessed_artifacts.rebuild_postprocessed_artifacts(
        results,
        payload={
            "project_id": "P-1",
            "workspace_dir": "payload-workspace",
            "quality_strict": True,
            "outline": ["工程概况"],
            "topic": "测试主题",
        },
        report=report,
        params=None,
        workspace_dir="explicit-workspace",
    )

    variant = results[0]
    assert variant["plan_consistency"] == {"normalized": 1}
    assert variant["param_trace"]["ok"] is True
    assert variant["param_trace"]["saved_at"] == "P-1:explicit-workspace"
    assert variant["param_trace"]["receipt"]["section_count"] == 1
    assert variant["quality_checks"]["variant_diversity"]["flagged_count"] == 1
    assert variant["quality_checks"]["issue_list"][-1]["type"] == "variant_diversity_gap"
    assert variant["quality_checks"]["auto_revision_suggestions"][-1]["type"] == "variant_diversity_gap"
    assert variant["cross_index"]["project_id"] == "P-1"
    assert variant["evidence_tracking"]["summary"]["count"] == 1
    assert variant["variant_similarity"]["avg_max_similarity"] == 0.91
    assert calls["quality_checks"]["workspace_dir"] == "explicit-workspace"
    assert calls["quality_checks"]["boq_focus"]["four_new_recommendations"] == ["new-tech"]


def test_rebuild_postprocessed_artifacts_flags_case_reference_copy_risk(monkeypatch, tmp_path: Path):
    extract_path = tmp_path / "case_extract.txt"
    extract_paragraph = (
        "施工准备阶段应完成技术交底、材料报验、样板先行、风险识别与工序卡审批。"
        "实施阶段按楼层和作业面组织穿插施工，明确责任人、每日检查频次、隐蔽验收记录、整改闭环要求。"
        "收尾阶段同步完成成品保护、资料归档、专项复验、分项验收与交付移交。"
    )
    extract_text = extract_paragraph * 3
    extract_path.write_text(extract_text, encoding="utf-8")

    monkeypatch.setattr(postprocessed_artifacts, "load_tender_matrix", lambda **kwargs: {})
    monkeypatch.setattr(postprocessed_artifacts, "load_boq_data", lambda **kwargs: {})
    monkeypatch.setattr(postprocessed_artifacts, "_build_boq_focus", lambda boq: {})
    monkeypatch.setattr(postprocessed_artifacts, "load_params", lambda: {})
    monkeypatch.setattr(postprocessed_artifacts, "recommend_four_new", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        postprocessed_artifacts,
        "run_quality_checks",
        lambda *args, **kwargs: {"issue_list": [], "auto_revision_suggestions": []},
    )
    monkeypatch.setattr(
        postprocessed_artifacts,
        "build_evidence_tracking",
        lambda **kwargs: {"rows": [], "summary": {}},
    )

    copied_content = extract_text
    results = [
        {
            "sections": [
                {
                    "title": "施工部署",
                    "content": copied_content,
                    "case_reference_pack": {
                        "enabled": True,
                        "hits": [
                            {
                                "case_id": "case-1",
                                "title": "养老院改造样板",
                                "extract_saved_as": str(extract_path),
                            }
                        ],
                    },
                }
            ],
        }
    ]

    postprocessed_artifacts.rebuild_postprocessed_artifacts(
        results,
        payload={"project_id": "P-2", "workspace_dir": str(tmp_path), "quality_strict": True},
        report=None,
        params=None,
        workspace_dir=str(tmp_path),
    )

    quality = results[0]["quality_checks"]
    assert quality["issue_list"][-1]["type"] == "case_reference_copy_risk"
    assert quality["issue_list"][-1]["reference_case_id"] == "case-1"
    assert "相似度过高" in quality["issue_list"][-1]["problem"]
    assert quality["auto_revision_suggestions"][-1]["type"] == "case_reference_copy_risk"
    assert quality["auto_revision_suggestions"][-1]["reference_case_id"] == "case-1"
