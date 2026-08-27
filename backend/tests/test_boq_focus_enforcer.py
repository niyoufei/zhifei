"""Unit tests for backend/zhifei_autoplan/boq_focus_enforcer.py"""

from __future__ import annotations

from backend.zhifei_autoplan.boq_focus_enforcer import _find_focus_card_span, ensure_boq_focus_item_cards


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
