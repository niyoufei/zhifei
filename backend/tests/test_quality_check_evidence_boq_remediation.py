from __future__ import annotations

from backend.zhifei_autoplan.quality_check import (
    _check_boq_focus_item_closure,
    _check_core_conclusion_evidence_by_section,
    apply_remediation,
)


def test_core_conclusion_evidence_remediation_annotates_existing_fragments(tmp_path) -> None:
    tender_file = tmp_path / "招标文件.pdf"
    tender_file.write_bytes(b"fake tender pdf bytes")
    tender = {
        "items": [
            {
                "dimension": "进度节点",
                "keywords": ["工期", "进度"],
                "weight": 1.0,
                "source_spans": [
                    {
                        "file_name": str(tender_file),
                        "page": 0,
                        "start": 123,
                        "end": 129,
                        "snippet": "计划工期120天，关键线路控制要求。",
                    }
                ],
            }
        ]
    }
    sections = [
        {
            "title": "工程概况",
            "content": "总工期120天，关键线路间隔3天，资源峰值18人，抽检频次=每100m2 1次，偏差≤5mm。",
        }
    ]

    apply_remediation(
        sections,
        [{"title": "工程概况", "type": "core_conclusion_evidence_gap", "suggestion": ""}],
        tender=tender,
        project_id="test_core_conclusion_locator_only_from_tender",
    )

    result = _check_core_conclusion_evidence_by_section(sections)

    assert result[0]["ok"] is True
    assert result[0]["covered"] >= 1
    assert "总工期120天" in sections[0]["content"]
    assert "【证据:" in sections[0]["content"]
    assert "#p1_" in sections[0]["content"]
    assert "@123" in sections[0]["content"]


def test_boq_focus_item_closure_remediation_writes_per_item_closed_loop_cards() -> None:
    boq_focus = {"must_cover_keywords": ["钢筋混凝土管"]}
    sections = [{"title": "主要施工方法", "content": "本章针对钢筋混凝土管施工进行组织。"}]

    apply_remediation(
        sections,
        [{"title": "清单重点项", "type": "boq_focus_item_closure_gap", "suggestion": ""}],
        boq_focus=boq_focus,
    )

    result = _check_boq_focus_item_closure(boq_focus, sections)

    assert result["ok"] is True
    assert "钢筋混凝土管重点项抽检记录" in sections[0]["content"]
    assert "责任岗位=" in sections[0]["content"]
    assert "偏差处置" in sections[0]["content"]


def test_core_conclusion_evidence_uses_line_level_shared_locator_and_skips_meta_guidance() -> None:
    sections = [
        {
            "title": "施工部署",
            "content": (
                "- 【风险→控制→验证】风险：资源错配导致工序等待；控制：班前协调=1次/班+日排产复核=1次/日；"
                "验证：等待时长≤30min，记录=《资源协调记录》；偏差处置：超时≤2h纠偏关闭。"
                "【证据:招标文件.pdf#p1_ab12cd34@12】\n\n"
                "【自动补充】核心结论证据补齐：\n"
                "- 已为本章回填 12 条核心结论证据定位符；未命中的句子需继续人工复核。\n"
                "- 示例：抽检频次=每100m2 1次，偏差≤5mm，偏差处置时限≤4h，责任岗位=质量员，记录=《抽检台账》。"
                "【证据:招标文件.pdf#p1_ab12cd34@12】\n"
                "- 对必选专项补齐可执行细则：采购/储运/领用/作业/应急或发放/检查/更换，并给出频次/阈值/时长等数值。\n"
            ),
        }
    ]

    result = _check_core_conclusion_evidence_by_section(sections)

    assert result[0]["ok"] is True
    assert result[0]["core_total"] == 1
    assert result[0]["covered"] == 1
    assert result[0]["missing_snippets"] == []


def test_core_conclusion_evidence_merges_soft_wrapped_item_codes() -> None:
    sections = [
        {
            "title": "建筑工程施工方案",
            "content": (
                "- 清单项：01170100600\n"
                "1；频次=2次/日（班前+收工）；阈值=偏差≤5mm；时长=4h/作业段；人数=8人/班；"
                "风险：01170100600\n"
                "1到货或工序参数不符导致返工/超支；控制：责任岗位=工长+质量员，"
                "到货验收=1次/批，抽检=每100m2 1次；验证：合格率≥98%，"
                "记录=《01170100600\n"
                "1重点项抽检记录》；偏差处置：超差即停工整改≤2h，复验合格后关闭。"
                "【证据:招标文件.pdf#p1_ab12cd34@12】"
            ),
        }
    ]

    result = _check_core_conclusion_evidence_by_section(sections)

    assert result[0]["ok"] is True
    assert result[0]["core_total"] == 1
    assert result[0]["covered"] == 1
    assert result[0]["missing_snippets"] == []
