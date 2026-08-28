from __future__ import annotations

from backend.zhifei_autoplan.boq_focus_policy import (
    MAX_BOQ_FOCUS_ITEMS,
    boq_focus_name_in_text,
    find_boq_focus_name_spans,
    normalize_boq_focus_items,
    select_boq_focus_names,
)


def test_focus_names_collapse_spreadsheet_line_wraps_and_deduplicate() -> None:
    result = normalize_boq_focus_items(
        [
            "预制钢筋混凝\n土管桩",
            "预制钢筋混凝土\n管桩",
            "铝方通吊顶\n（顶棚四）",
        ]
    )

    assert result == ["预制钢筋混凝土管桩", "铝方通吊顶(顶棚四)"]
    assert boq_focus_name_in_text(result[0], "本章控制预制钢筋混凝土管桩施工。")


def test_focus_policy_applies_one_shared_twenty_item_bound() -> None:
    result = normalize_boq_focus_items(
        [f"重点项{i}" for i in range(MAX_BOQ_FOCUS_ITEMS + 3)]
    )

    assert len(result) == MAX_BOQ_FOCUS_ITEMS
    assert result[-1] == "重点项19"


def test_canonical_span_search_returns_offsets_in_original_text() -> None:
    text = "前置：预制 A\u3000型\n管，后置"

    spans = find_boq_focus_name_spans("预制Ａ型管", text)

    expected_start = text.index("预")
    expected_end = text.index("，")
    assert spans == [(expected_start, expected_end)]
    assert text[spans[0][0] : spans[0][1]] == "预制 A\u3000型\n管"
    assert boq_focus_name_in_text("预制Ａ型管", text) is True


def test_focus_policy_limit_zero_returns_empty() -> None:
    assert normalize_boq_focus_items(["重点项1"], limit=0) == []
    assert find_boq_focus_name_spans("重点项1", "重点项1", limit=0) == []


def test_effective_focus_list_prioritizes_safety_categories() -> None:
    stats = {
        "top_total_price_items": [
            {"name": f"造价项{i}"} for i in range(MAX_BOQ_FOCUS_ITEMS + 2)
        ],
        "hazardous_material_items": [{"name": "氧气瓶"}],
        "ppe_items": [{"name": "安全带"}],
        "special_material_items": [{"name": "特种灌浆料"}],
    }

    selected = select_boq_focus_names(stats)

    assert selected[:3] == ["氧气瓶", "安全带", "特种灌浆料"]
    assert len(selected) == MAX_BOQ_FOCUS_ITEMS
