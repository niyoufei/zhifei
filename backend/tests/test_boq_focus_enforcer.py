"""Unit tests for backend/zhifei_autoplan/boq_focus_enforcer.py"""

from __future__ import annotations

from backend.zhifei_autoplan.boq_focus_enforcer import (
    _find_focus_card_span,
    ensure_boq_focus_item_cards,
)
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger


def _boq_focus():
    return {
        "must_cover_keywords": ["防水卷材"],
        "lines": [
            "清单重点（材料价格高）：",
            "- 防水卷材 / 工程量=100m2 / 单价=50 / 合价=5000",
        ],
    }


def test_injects_into_section_where_item_is_mentioned():
    sections = [
        {"title": "质量管理", "content": "本章涉及防水卷材的进场复验与验收。"},
        {"title": "主要施工方案", "content": "施工方案内容。"},
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is True
    assert "防水卷材" in injected
    assert "【清单重点项控制卡】" in sections[0]["content"]
    assert "防水卷材" in sections[0]["content"]


def test_title_token_match_selects_best_chapter():
    sections = [
        {"title": "防水工程施工方案", "content": "方案正文。"},
        {"title": "质量管理", "content": "质量正文。"},
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is True
    assert "防水卷材" in injected
    assert "【清单重点项控制卡】" in sections[0]["content"]
    assert "防水卷材" in sections[0]["content"]


def test_idempotent_second_call_no_changes():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    boq_focus = _boq_focus()
    changed1, injected1 = ensure_boq_focus_item_cards(sections, boq_focus, evidence_src="清单.pdf#p1_abcd@10")
    assert changed1 is True
    assert injected1

    changed2, injected2 = ensure_boq_focus_item_cards(sections, boq_focus, evidence_src="清单.pdf#p1_abcd@10")
    assert changed2 is False
    assert injected2 == []


def test_missing_project_facts_never_promote_registry_defaults_into_focus_card():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        _boq_focus(),
        evidence_src="清单.pdf#p1_abcd@10",
        params={
            "quant_defaults": {
                "频次": "2次/日（班前+收工）",
                "阈值": "偏差≤5mm",
                "时长": "4h/作业段",
                "人数": "8人/班",
                "设备型号": "20t挖机1台",
            }
        },
    )

    content = sections[0]["content"]
    assert changed is True
    assert injected == ["防水卷材"]
    for guessed in ("2次/日", "偏差≤5mm", "4h", "8人/班", "20t挖机"):
        assert guessed not in content
    assert "频次=待依据经批准项目制度确认" in content
    assert "阈值=待按图纸及适用规范逐工序确认" in content
    assert "偏差处置时限=待依据经批准项目制度确认" in content
    assert "【证据:清单.pdf#p1_abcd@10】" in content


def test_focus_card_uses_only_accepted_project_facts_with_locators():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    ledger = build_project_fact_ledger(
        [
            {
                "source_id": "approved",
                "source_type": "approved_resolution",
                "facts": {
                    "risk_inspection_frequency": "逐班",
                    "quality_threshold": "按工序允许偏差表",
                    "deviation_action_deadline": {"value": 6, "unit": "小时"},
                },
                "evidence": {"locator": "approved_resolution"},
            }
        ]
    )

    changed, _ = ensure_boq_focus_item_cards(
        sections,
        _boq_focus(),
        evidence_src="清单.pdf#p1_abcd@10",
        project_fact_ledger=ledger,
    )

    content = sections[0]["content"]
    assert changed is True
    assert "频次=逐班【证据:approved_resolution】" in content
    assert "阈值=按工序允许偏差表【证据:approved_resolution】" in content
    assert "偏差处置时限=6小时【证据:approved_resolution】" in content
    assert "2次/日" not in content
    assert "偏差≤5mm" not in content
    assert "4h" not in content


def test_skip_when_item_already_closed_in_existing_content():
    sections = [
        {
            "title": "主要施工方案",
            "content": (
                "防水卷材已纳入控制。"
                "量化指标：频次=2次/日；阈值=偏差≤5mm；人数=8人/班。"
                "风险→控制→验证：风险：返工；控制：抽检；验证：合格率≥98%。【证据:清单.pdf#p1_abcd@10】"
            ),
        }
    ]
    changed, injected = ensure_boq_focus_item_cards(sections, _boq_focus(), evidence_src="清单.pdf#p1_abcd@10")
    assert changed is False
    assert injected == []


def test_injects_focus_items_beyond_the_legacy_twelve_item_prefix():
    names = [f"重点项{i}" for i in range(1, 14)]
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        {"must_cover_keywords": names, "lines": []},
        evidence_src="清单.pdf#p1_abcd1234@10",
    )

    assert changed is True
    assert injected == names
    assert "清单项：重点项13" in sections[0]["content"]


def test_focus_line_details_join_card_by_canonical_name_key():
    sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
    boq_focus = {
        "must_cover_keywords": ["铝 方通吊顶（顶棚四）"],
        "lines": ["- 铝方通吊顶(顶棚四) / 工程量=12m2 / 单价=50 / 合价=600"],
    }

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p1_abcd1234@10",
    )

    assert changed is True
    assert injected == ["铝 方通吊顶(顶棚四)"]
    assert "清单项：铝方通吊顶(顶棚四)；工程量=12m2；单价=50；合价=600" in sections[0]["content"]


def test_focus_card_lookup_uses_canonical_name_key():
    text = (
        "前文\n"
        "- 清单项: 铝 方通吊顶（顶棚四）；工程量=12m2\n"
        "  量化指标：频次=2次/日。\n"
        "后文\n"
    )

    span = _find_focus_card_span(text, "铝方通吊顶(顶棚四)")

    assert span is not None
    start, end, line_end = span
    assert text[start:line_end].startswith("- 清单项: 铝 方通吊顶")
    assert text[start:end].endswith("后文\n")


def test_hazardous_material_boilerplate_is_centralized_and_idempotent():
    names = ["氧气瓶", "乙炔瓶", "防水涂料"]
    sections = [{"title": "材料与安全管理", "content": "危险品材料分类管理。"}]
    boq_focus = {
        "must_cover_keywords": names,
        "hazardous_materials": names,
        "lines": [f"- {name} / 工程量=1项" for name in names],
    }

    changed, injected = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p3_abcd1234@30",
    )

    content = sections[0]["content"]
    assert changed is True
    assert injected == names
    assert content.count("【危险品材料统一管理基线】") == 1
    assert content.count("MSDS随货逐批核验") == 1
    for name in names:
        assert f"{name}挥发/燃爆/泄漏" in content
        assert f"《{name}风险与领用核验记录》" in content

    first = content
    changed_again, injected_again = ensure_boq_focus_item_cards(
        sections,
        boq_focus,
        evidence_src="清单.pdf#p3_abcd1234@30",
    )
    assert changed_again is False
    assert injected_again == []
    assert sections[0]["content"] == first
