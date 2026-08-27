from __future__ import annotations

from backend.zhifei_autoplan.requirement_evidence_matrix import (
    build_requirement_evidence_plan,
    finalize_requirement_evidence_matrix,
    requirement_prompt_lines_for_chapter,
    scope_requirement_evidence_plan_to_chapters,
    validate_chapter_requirement_evidence,
    validate_requirement_evidence_matrix,
    validate_requirement_evidence_plan_readiness,
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
    locator = row["source_evidence"][0]["traceable_locator"]
    assert locator.startswith("招标文件.pdf#p27_")
    assert locator.endswith("@120")
    assert "snippet" not in row["source_evidence"][0]
    prompt = requirement_prompt_lines_for_chapter(
        plan, "质量管理与验收"
    )[0]
    assert row["requirement_id"] in prompt
    assert f"【证据:{locator}】" in prompt
    assert "须形成材料进场" not in prompt
    assert validate_requirement_evidence_plan_readiness(plan)["ok"] is True


def test_chapter_validation_scope_drops_unselected_and_document_controls():
    contract = _agent_contract()
    contract["chapters"].append(
        {"chapter_id": "CH-002", "title": "安全生产", "agents": {}}
    )
    full_plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={
            "质量管理与验收": ["必须形成质量验收闭环"],
            "安全生产": ["必须形成安全巡检闭环"],
        },
        global_requirements=["总页数不超过50页。"],
        agent_contract=contract,
    )

    scoped = scope_requirement_evidence_plan_to_chapters(
        full_plan,
        ["质量管理与验收"],
    )

    assert validate_requirement_evidence_matrix(scoped)["ok"] is True
    assert scoped["summary"]["scope"] == "chapter_validation"
    assert scoped["summary"]["unmapped_count"] == 0
    assert [row["target_chapters"] for row in scoped["rows"]] == [
        ["质量管理与验收"]
    ]
    assert all(
        row.get("verification_mode") != "document_control"
        for row in scoped["rows"]
    )


def test_chapter_validation_scopes_after_full_outline_ownership_mapping():
    full_contract = {
        "chapters": [
            {"chapter_id": "CH-001", "title": "质量管理与验收", "agents": {}},
            {"chapter_id": "CH-002", "title": "安全消防措施", "agents": {}},
        ]
    }
    full_plan = build_requirement_evidence_plan(
        tender={
            "items": [
                {
                    "dimension": "安全等级",
                    "keywords": ["消防巡检"],
                    "mandatory": True,
                }
            ]
        },
        chapter_requirements={},
        global_requirements=[],
        agent_contract=full_contract,
    )

    assert full_plan["rows"][0]["target_chapters"] == ["安全消防措施"]
    scoped = scope_requirement_evidence_plan_to_chapters(
        full_plan,
        ["质量管理与验收"],
    )

    assert scoped["rows"] == []
    assert validate_requirement_evidence_plan_readiness(scoped)["ok"] is True


def test_prompt_uses_basename_and_never_leaks_local_source_path():
    plan = build_requirement_evidence_plan(
        tender={
            "items": [
                {
                    "dimension": "扣分项",
                    "keywords": ["质量验收闭环"],
                    "source_spans": [
                        {
                            "file_name": "/private/upload/secret/招标文件.pdf",
                            "page": 2,
                            "start": 9,
                            "end": 18,
                            "snippet": "不得泄漏的原文",
                        }
                    ],
                }
            ]
        },
        chapter_requirements={},
        global_requirements=[],
        agent_contract=_agent_contract(),
    )
    row = plan["rows"][0]
    prompt = requirement_prompt_lines_for_chapter(plan, "质量管理与验收")[0]
    assert row["source_evidence"][0]["file_name"].startswith("/private/")
    assert "招标文件.pdf#p2_" in prompt
    assert "/private/" not in prompt
    assert "不得泄漏的原文" not in prompt


def test_plan_readiness_rejects_mandatory_untraceable_source():
    plan = build_requirement_evidence_plan(
        tender={
            "items": [
                {
                    "dimension": "扣分项",
                    "keywords": ["质量验收闭环"],
                    "source_spans": [
                        {
                            "file_name": "招标文件.pdf",
                            "page": 1,
                            "start": None,
                            "end": None,
                            "snippet": "",
                        }
                    ],
                }
            ]
        },
        chapter_requirements={},
        global_requirements=[],
        agent_contract=_agent_contract(),
    )
    readiness = validate_requirement_evidence_plan_readiness(plan)
    requirement_id = plan["rows"][0]["requirement_id"]
    assert readiness["ok"] is False
    assert readiness["blocking_requirement_ids"] == [requirement_id]
    assert readiness["blocking"][0]["code"] == "SOURCE_LOCATOR_UNTRACEABLE"
    prompt = requirement_prompt_lines_for_chapter(plan, "质量管理与验收")[0]
    assert "文件#页码_哈希@偏移" not in prompt
    assert "禁止编造" in prompt


def test_chapter_gate_requires_exact_planned_locator_in_same_paragraph():
    plan = _plan()
    row = plan["rows"][0]
    requirement_id = row["requirement_id"]
    locator = row["source_evidence"][0]["traceable_locator"]

    wrong_paragraph = validate_chapter_requirement_evidence(
        plan=plan,
        title="质量管理与验收",
        section={
            "title": "质量管理与验收",
            "content": f"落实质量验收闭环。【要求:{requirement_id}】\n另一段【证据:{locator}】",
        },
    )
    assert wrong_paragraph["ok"] is False
    assert wrong_paragraph["rows"][0]["status"] == "COVERED_UNEVIDENCED"

    unrelated_source = validate_chapter_requirement_evidence(
        plan=plan,
        title="质量管理与验收",
        section={
            "title": "质量管理与验收",
            "content": (
                f"落实质量验收闭环。【要求:{requirement_id}】"
                "【证据:无关资料.pdf#p1_deadbeef@9】"
            ),
        },
    )
    assert unrelated_source["ok"] is False
    assert unrelated_source["rows"][0]["status"] == "EVIDENCE_SOURCE_MISMATCH"

    accepted = validate_chapter_requirement_evidence(
        plan=plan,
        title="质量管理与验收",
        section={
            "title": "质量管理与验收",
            "content": (
                f"落实质量验收闭环。【要求:{requirement_id}】"
                f"【证据:{locator}】"
            ),
        },
    )
    assert accepted["ok"] is True
    assert accepted["rows"][0]["status"] == "COVERED_TRACEABLE"


def test_low_quality_chapter_fragments_are_review_only_and_prompt_excluded():
    fragments = [
        "内容未提供或无任何针对性、可行性，本项不得",
        "每提供 1 个得 2 分，本项满分 4",
        "中规定提供的业绩证明材料",
    ]
    executable = "投标人必须建立质量保证体系，明确岗位职责和验收流程"
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={
            "质量管理与验收": [*fragments, executable],
        },
        global_requirements=[],
        agent_contract=_agent_contract(),
    )

    review_rows = [
        row for row in plan["rows"] if row["planning_status"] == "NEEDS_REVIEW"
    ]
    executable_row = next(
        row for row in plan["rows"] if row["requirement"] == executable
    )
    assert len(review_rows) == 3
    assert all(row["mandatory"] is False for row in review_rows)
    assert all(row["prompt_eligible"] is False for row in review_rows)
    assert plan["summary"]["needs_review_count"] == 3
    assert plan["summary"]["mandatory_count"] == 1
    assert plan["summary"]["prompt_eligible_count"] == 1
    assert executable_row["mandatory"] is True
    assert executable_row["quality_status"] == "READY"

    prompt = "\n".join(
        requirement_prompt_lines_for_chapter(plan, "质量管理与验收")
    )
    assert executable in prompt
    assert all(fragment not in prompt for fragment in fragments)

    readiness = validate_requirement_evidence_plan_readiness(plan)
    assert readiness["ok"] is True
    assert readiness["blocking_requirement_ids"] == []
    assert set(readiness["warning_requirement_ids"]) == {
        row["requirement_id"] for row in review_rows
    }
    assert {
        row["code"] for row in readiness["warnings"]
    } == {"REQUIREMENT_NEEDS_REVIEW"}

    gate = validate_chapter_requirement_evidence(
        plan=plan,
        title="质量管理与验收",
        section={
            "title": "质量管理与验收",
            "content": f"{executable}。【要求:{executable_row['requirement_id']}】",
        },
    )
    assert gate["ok"] is True
    assert gate["blocking_requirement_ids"] == []
    assert sum(row["status"] == "NEEDS_REVIEW" for row in gate["rows"]) == 3

    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[
            {
                "title": "质量管理与验收",
                "content": f"{executable}。【要求:{executable_row['requirement_id']}】",
            }
        ],
        evidence_tracking={"rows": [], "summary": {}},
    )
    assert matrix["summary"]["blocking_count"] == 0
    assert matrix["summary"]["warning_count"] == 3
    assert matrix["summary"]["strict_delivery_allowed"] is True


def test_executable_requirement_with_scoring_tail_remains_mandatory():
    requirement = "投标人应提供质量保证体系及岗位职责，每缺一项扣2分"
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={"质量管理与验收": [requirement]},
        global_requirements=[],
        agent_contract=_agent_contract(),
    )

    row = plan["rows"][0]
    assert row["quality_status"] == "READY"
    assert row["planning_status"] == "PLANNED"
    assert row["mandatory"] is True
    assert row["prompt_eligible"] is True
    assert requirement in requirement_prompt_lines_for_chapter(
        plan, "质量管理与验收"
    )[0]


def test_actionable_requirement_with_arbitrary_subject_remains_mandatory():
    requirement = "（1）施工期间应设置每日纠偏闭环"
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={"进度纠偏": [{"requirement": requirement, "mandatory": False}]},
        global_requirements=[],
        agent_contract={
            "chapters": [
                {
                    "chapter_id": "CH-001",
                    "title": "进度纠偏",
                    "agents": {
                        "master": "章节主笔Agent",
                        "specialists": ["进度计划Agent"],
                        "auxiliary": [],
                        "compliance": "规范合规Agent",
                    },
                }
            ]
        },
    )

    row = plan["rows"][0]
    assert row["quality_status"] == "READY"
    assert row["planning_status"] == "PLANNED"
    assert row["mandatory"] is True
    assert row["prompt_eligible"] is True
    assert requirement in requirement_prompt_lines_for_chapter(
        plan, "进度纠偏"
    )[0]


def test_parser_review_metadata_is_preserved_as_nonblocking_plan_evidence():
    fragment = "每提供 1 个得 2 分，本项满分 4"
    plan = build_requirement_evidence_plan(
        tender={
            "extraction_meta": {
                "chapter_requirement_review": {
                    "status": "NEEDS_REVIEW",
                    "rows": [
                        {
                            "chapter_title": "质量管理与验收",
                            "requirement": fragment,
                            "status": "NEEDS_REVIEW",
                            "reason_codes": ["SCORE_ONLY_FRAGMENT"],
                        }
                    ],
                }
            }
        },
        chapter_requirements={
            "质量管理与验收": ["投标人应建立质量保证体系"]
        },
        global_requirements=[],
        agent_contract=_agent_contract(),
    )

    review_row = next(
        row for row in plan["rows"] if row["requirement"] == fragment
    )
    assert review_row["planning_status"] == "NEEDS_REVIEW"
    assert review_row["mandatory"] is False
    assert review_row["prompt_eligible"] is False
    assert fragment not in "\n".join(
        requirement_prompt_lines_for_chapter(plan, "质量管理与验收")
    )
    assert validate_requirement_evidence_plan_readiness(plan)["ok"] is True


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
    locator = plan["rows"][0]["source_evidence"][0]["traceable_locator"]
    paragraph = (
        f"建立实质闭环。【要求:{requirement_id}】"
        f"【证据:{locator}】"
    )
    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[
            {
                "title": "质量管理与验收",
                "content": paragraph,
            }
        ],
        evidence_tracking={
            "rows": [
                {
                    "section_title": "质量管理与验收",
                    "paragraph_id": "P-1",
                    "page_estimate": 10,
                    "system_response": paragraph,
                    "evidence_sources": [locator],
                }
            ],
            "summary": {},
        },
    )
    assert validate_requirement_evidence_matrix(matrix)["ok"] is True
    assert matrix["rows"][0]["status"] == "COVERED_TRACEABLE"
    assert matrix["rows"][0]["blocking"] is False
    assert matrix["summary"]["strict_delivery_allowed"] is True


def test_uncovered_global_document_control_requirement_blocks_delivery():
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={},
        global_requirements=["全文必须建立绿色施工台账"],
        agent_contract=_agent_contract(),
    )

    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[{"title": "质量管理与验收", "content": "只有质量验收内容。"}],
        evidence_tracking={"rows": [], "summary": {}},
    )

    assert matrix["rows"][0]["status"] == "MISSING_RESPONSE"
    assert matrix["rows"][0]["blocking"] is True
    assert matrix["summary"]["strict_delivery_allowed"] is False


def test_global_document_control_requirement_is_verified_across_chapters():
    contract = _agent_contract()
    contract["chapters"].append(
        {
            "chapter_id": "CH-002",
            "title": "绿色施工",
            "agents": {},
        }
    )
    requirement = "全文必须建立绿色施工台账"
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={},
        global_requirements=[requirement],
        agent_contract=contract,
    )

    matrix = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[
            {"title": "质量管理与验收", "content": "质量验收闭环。"},
            {"title": "绿色施工", "content": f"{requirement}，每日归档。"},
        ],
        evidence_tracking={"rows": [], "summary": {}},
    )

    row = matrix["rows"][0]
    assert row["status"] == "COVERED"
    assert row["matched_chapters"] == ["绿色施工"]
    assert row["blocking"] is False
    assert matrix["summary"]["strict_delivery_allowed"] is True


def test_page_limit_control_is_verified_from_page_plan_not_body_text():
    plan = build_requirement_evidence_plan(
        tender={},
        chapter_requirements={},
        global_requirements=["总页数不超过50页。"],
        agent_contract=_agent_contract(),
    )

    accepted = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[{"title": "质量管理与验收", "content": "正文不应夹带内部页数控制语句。"}],
        evidence_tracking={"rows": [], "summary": {}},
        document_control_evidence={
            "page_plan": {"planned_total_pages": 50, "verified": True}
        },
    )
    rejected = finalize_requirement_evidence_matrix(
        plan=plan,
        sections=[{"title": "质量管理与验收", "content": "正文。"}],
        evidence_tracking={"rows": [], "summary": {}},
        document_control_evidence={
            "page_plan": {"planned_total_pages": 51, "verified": True}
        },
    )

    assert accepted["rows"][0]["status"] == "COVERED_CONTROL_VERIFIED"
    assert accepted["summary"]["strict_delivery_allowed"] is True
    assert rejected["rows"][0]["status"] == "CONTROL_VERIFICATION_FAILED"
    assert rejected["summary"]["strict_delivery_allowed"] is False
