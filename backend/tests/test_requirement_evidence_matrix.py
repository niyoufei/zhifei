from __future__ import annotations

from backend.zhifei_autoplan.requirement_evidence_matrix import (
    build_requirement_evidence_plan,
    finalize_requirement_evidence_matrix,
    requirement_prompt_lines_for_chapter,
    validate_requirement_evidence_matrix,
)


def _agent_contract():
    return {
        "chapters": [
            {
                "chapter_id": "CH-001",
                "title": "质量管理与验收",
                "agents": {
                    "master": "章节主笔Agent",
                    "specialists": ["质量验收Agent"],
                    "auxiliary": [],
                    "compliance": "规范合规Agent",
                },
            }
        ]
    }


def _plan(*, dimension="扣分项", mandatory=None, with_source=True):
    item = {
        "dimension": dimension,
        "keywords": ["质量验收闭环"],
    }
    if mandatory is not None:
        item["mandatory"] = mandatory
    if with_source:
        item["source_spans"] = [
            {
                "file_name": "招标文件.pdf",
                "page": 27,
                "start": 120,
                "end": 168,
                "snippet": "须形成材料进场、复验和验收闭环。",
            }
        ]
    return build_requirement_evidence_plan(
        tender={"items": [item]},
        chapter_requirements={},
        global_requirements=[],
        agent_contract=_agent_contract(),
    )


def test_plan_sanitizes_snippets_and_assigns_accountability():
    plan = _plan()
    assert validate_requirement_evidence_matrix(plan)["ok"] is True
    row = plan["rows"][0]
    assert row["target_chapters"] == ["质量管理与验收"]
    assert row["responsibility"][0]["master_agent"] == "章节主笔Agent"
    assert row["source_evidence"][0]["snippet_sha256"]
    assert "snippet" not in row["source_evidence"][0]
    assert row["requirement_id"] in requirement_prompt_lines_for_chapter(
        plan, "质量管理与验收"
    )[0]


def test_digest_tamper_is_rejected():
    plan = _plan()
    plan["rows"][0]["requirement"] = "篡改后的要求"
    validation = validate_requirement_evidence_matrix(plan)
    assert validation["ok"] is False
    assert "digest_mismatch" in validation["errors"]


def test_nonmandatory_score_gap_warns_but_does_not_block():
    plan = _plan(dimension="质量目标", mandatory=False, with_source=False)
    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[{"title": "质量管理与验收", "content": "尚未覆盖"}],
        evidence_tracking={"rows": [], "summary": {}},
    )
    row = matrix["rows"][0]
    assert row["status"] == "MISSING_RESPONSE"
    assert row["blocking"] is False
    assert matrix["summary"]["blocking_count"] == 0
    assert matrix["summary"]["warning_count"] == 1


def test_mandatory_requirement_without_response_blocks():
    plan = _plan()
    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[{"title": "质量管理与验收", "content": "普通说明"}],
        evidence_tracking={"rows": [], "summary": {}},
    )
    row = matrix["rows"][0]
    assert row["status"] == "MISSING_RESPONSE"
    assert row["blocking"] is True
    assert matrix["summary"]["strict_delivery_allowed"] is False


def test_auto_placeholder_is_not_real_evidence():
    plan = _plan()
    requirement_id = plan["rows"][0]["requirement_id"]
    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[
            {
                "title": "质量管理与验收",
                "content": f"建立实质闭环。【要求:{requirement_id}】",
            }
        ],
        evidence_tracking={
            "rows": [
                {
                    "section_title": "质量管理与验收",
                    "paragraph_id": "P-1",
                    "evidence_sources": ["AUTO://no_explicit_evidence"],
                }
            ],
            "summary": {},
        },
    )
    assert matrix["rows"][0]["status"] == "COVERED_UNEVIDENCED"
    assert matrix["rows"][0]["blocking"] is True


def test_marker_and_traceable_explicit_evidence_pass():
    plan = _plan()
    requirement_id = plan["rows"][0]["requirement_id"]
    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[
            {
                "title": "质量管理与验收",
                "content": f"建立实质闭环。【要求:{requirement_id}】",
            }
        ],
        evidence_tracking={
            "rows": [
                {
                    "section_title": "质量管理与验收",
                    "paragraph_id": "P-1",
                    "page_estimate": 10,
                    "evidence_sources": ["招标文件.pdf#p27_a1b2c3d4@120"],
                }
            ],
            "summary": {},
        },
    )
    assert validate_requirement_evidence_matrix(matrix)["ok"] is True
    assert matrix["rows"][0]["status"] == "COVERED_TRACEABLE"
    assert matrix["rows"][0]["blocking"] is False
    assert matrix["summary"]["strict_delivery_allowed"] is True
