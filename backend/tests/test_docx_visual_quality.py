from __future__ import annotations

from backend.zhifei_autoplan.docx_visual_quality import (
    assess_cjk_glyph_integrity,
    evaluate_page_quality,
)


def _page(page: int, **overrides):
    value = {
        "page": page,
        "blank": False,
        "sparse": False,
        "orphan_heading": False,
        "edge_clipping_risk": False,
    }
    value.update(overrides)
    return value


def test_visual_quality_blocks_blank_pages() -> None:
    result = evaluate_page_quality([_page(1), _page(2, blank=True), _page(3)])

    assert result["status"] == "blocked"
    assert result["blank_pages"] == [2]
    assert result["hard_failures"][0]["code"] == "BLANK_PAGES"


def test_visual_quality_blocks_orphan_heading() -> None:
    result = evaluate_page_quality([_page(1), _page(2, orphan_heading=True), _page(3)])

    assert result["status"] == "blocked"
    assert result["orphan_heading_pages"] == [2]


def test_visual_quality_allows_small_sparse_budget_but_blocks_systemic_padding() -> None:
    within_budget = evaluate_page_quality([_page(i, sparse=(i == 6)) for i in range(1, 51)])
    excessive = evaluate_page_quality([_page(i, sparse=(i in {6, 12, 18})) for i in range(1, 51)])

    assert within_budget["status"] == "pass"
    assert within_budget["sparse_page_budget"] == 2
    assert excessive["status"] == "blocked"
    assert excessive["hard_failures"][0]["code"] == "EXCESSIVE_SPARSE_PAGES"


def test_visual_quality_reports_edge_risk_without_false_blocking() -> None:
    result = evaluate_page_quality([_page(1), _page(2, edge_clipping_risk=True)])

    assert result["status"] == "pass"
    assert result["edge_clipping_risk_pages"] == [2]
    assert result["warnings"][0]["code"] == "EDGE_CLIPPING_RISK"


def test_visual_quality_blocks_systemic_edge_clipping() -> None:
    result = evaluate_page_quality(
        [
            _page(1),
            _page(2, edge_clipping_risk=True),
            _page(3, edge_clipping_risk=True),
        ]
    )

    assert result["status"] == "blocked"
    assert "SYSTEMIC_EDGE_CLIPPING_RISK" in {
        item["code"] for item in result["hard_failures"]
    }


def test_visual_quality_blocks_consecutive_sparse_pages_within_global_budget() -> None:
    result = evaluate_page_quality(
        [_page(i, sparse=(i in {20, 21})) for i in range(1, 101)]
    )

    assert result["sparse_page_budget"] == 4
    assert result["status"] == "blocked"
    assert result["sparse_page_streaks"] == [[20, 21]]


def test_visual_quality_accepts_a4_orientation_changes() -> None:
    result = evaluate_page_quality(
        [
            _page(1, pixel_width=1240, pixel_height=1754),
            _page(2, pixel_width=1240, pixel_height=1754),
            _page(3, pixel_width=1754, pixel_height=1240),
        ]
    )

    assert result["status"] == "pass"
    assert result["page_geometry_outliers"] == []


def test_visual_quality_blocks_inconsistent_page_geometry() -> None:
    result = evaluate_page_quality(
        [
            _page(1, pixel_width=1240, pixel_height=1754),
            _page(2, pixel_width=1240, pixel_height=1754),
            _page(3, pixel_width=1400, pixel_height=1754),
        ]
    )

    assert result["status"] == "blocked"
    assert result["page_geometry_outliers"] == [3]


def test_cjk_glyph_integrity_blocks_replacement_box_collapse() -> None:
    result = assess_cjk_glyph_integrity(
        {character: {"same-tofu-box"} for character in "施工组织设计质量安全工期进度资源机械人员道路排水"},
        inspected_glyphs=200,
    )

    assert result["status"] == "blocked"
    assert result["largest_shape_collision"] >= 8
    assert result["hard_failures"] == [{"code": "CJK_GLYPH_COLLAPSE"}]


def test_cjk_glyph_integrity_accepts_distinct_rendered_characters() -> None:
    characters = "施工组织设计质量安全工期进度资源机械人员道路排水环境保护验收方案"
    result = assess_cjk_glyph_integrity(
        {character: {f"shape-{index}"} for index, character in enumerate(characters)},
        inspected_glyphs=300,
    )

    assert result["status"] == "pass"
    assert result["shape_retention"] == 1.0
