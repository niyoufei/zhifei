from __future__ import annotations

import pytest

from backend.zhifei_autoplan.outline_planner import plan_chapter_pages


def test_chapter_page_plan_fails_when_outline_cannot_fit_tender_limit() -> None:
    outline = [f"第{index}章" for index in range(1, 6)]

    with pytest.raises(ValueError, match="OUTLINE_EXCEEDS_PAGE_LIMIT"):
        plan_chapter_pages(outline, total_pages=4)


def test_chapter_page_plan_still_respects_feasible_limit() -> None:
    result = plan_chapter_pages(
        ["工程概况", "施工部署", "质量保证"],
        total_pages=8,
    )

    assert set(result) == {"工程概况", "施工部署", "质量保证"}
    assert all(pages >= 1 for pages in result.values())
    assert sum(result.values()) <= 8
