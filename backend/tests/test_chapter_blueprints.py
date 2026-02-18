from __future__ import annotations

from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint
from backend.zhifei_autoplan.quality_check import apply_remediation, run_quality_checks


def test_match_chapter_blueprint_bp01():
    bp = match_chapter_blueprint("01 对工程项目整体理解与实施路径")
    assert isinstance(bp, dict)
    assert bp.get("id") == "BP01"
    assert "工程特点" in (bp.get("anchors") or [])


def test_match_chapter_blueprint_bp02():
    bp = match_chapter_blueprint("安全生产管理体系与控制措施")
    assert isinstance(bp, dict)
    assert bp.get("id") == "BP02"


def test_match_chapter_blueprint_bp16_requires_all_keywords():
    # BP16 requires both "可行" and "落地" in title.
    assert match_chapter_blueprint("技术措施的可行性与落地性")["id"] == "BP16"
    assert match_chapter_blueprint("技术措施的可行性分析") is None


def test_quality_check_flags_missing_blueprint_anchors_in_strict_mode():
    sections = [{"title": "对工程项目整体理解与实施路径", "content": "本章只写了概述，没有按结构展开。"}]
    res = run_quality_checks(None, [s["title"] for s in sections], sections, strict=True)
    assert "chapter_blueprint_adherence" in res
    assert res["chapter_blueprint_adherence"]["ok"] is False
    assert any(it.get("type") == "chapter_blueprint_gap" for it in (res.get("issue_list") or []))
    assert any(it.get("type") == "chapter_blueprint_gap" for it in (res.get("remediation") or []))


def test_apply_remediation_can_inject_blueprint_anchors():
    sections = [{"title": "对工程项目整体理解与实施路径", "content": "原文。"}]
    remediation = [
        {
            "title": "对工程项目整体理解与实施路径",
            "type": "chapter_blueprint_gap",
            "blueprint_name": "对工程项目整体理解与实施路径",
            "missing_anchors": ["工程特点", "总体部署"],
            "suggestion": "补齐锚点。",
        }
    ]
    apply_remediation(sections, remediation, project_id=None, boq_focus=None, params=None)
    out = sections[0]["content"]
    assert "【工程特点】" in out
    assert "【总体部署】" in out

