from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from backend.zhifei_autoplan.agents.section_writer import SectionWriter
from backend.zhifei_autoplan.async_cache import AsyncThreadCache
from backend.zhifei_autoplan.orchestrator import (
    _build_section_checklist,
    _build_section_runtime_budget,
    _resolve_runtime_speed_profile,
)


def test_build_section_checklist_prefers_relevant_and_limited():
    tender = {
        "items": [
            {"dimension": "工程概况", "keywords": ["项目范围", "工程特点"], "weight": 30},
            {"dimension": "主要施工方法", "keywords": ["模板", "混凝土"], "weight": 40},
            {"dimension": "报价文件评审标准", "keywords": ["评标价", "偏差率"], "weight": 85},
            {"dimension": "安全生产", "keywords": ["临电", "高处作业"], "weight": 35},
        ]
    }
    out = _build_section_checklist(tender, "主要施工方法", limit=3)
    assert len(out) == 3
    assert any("主要施工方法" in x for x in out)


def test_resolve_runtime_speed_profile_quality_mode():
    p = _resolve_runtime_speed_profile(
        mode_effective="quality_200",
        total_pages_limit=50,
        payload={},
    )
    assert p["kg_top_k"] <= 3
    assert p["section_retry_limit"] >= 1
    assert 0.5 <= p["chars_per_page_factor"] <= 1.0


def test_resolve_runtime_speed_profile_large_pages_more_aggressive():
    p = _resolve_runtime_speed_profile(
        mode_effective="quality_200",
        total_pages_limit=600,
        payload={},
    )
    assert p["section_retry_limit"] == 1
    assert p["chars_per_page_factor"] <= 0.70


def test_resolve_runtime_speed_profile_speed_fast_mode():
    p = _resolve_runtime_speed_profile(
        mode_effective="speed_fast",
        total_pages_limit=80,
        payload={},
    )
    assert p["doc_limit"] <= 3
    assert p["llm_timeout_sec"] <= 60
    assert p["chars_per_page_factor"] <= 0.60


def test_resolve_runtime_speed_profile_pro_polish_mode():
    p = _resolve_runtime_speed_profile(
        mode_effective="pro_polish",
        total_pages_limit=80,
        payload={},
    )
    assert p["kg_top_k"] >= 4
    assert p["section_retry_limit"] >= 3
    assert p["chars_per_page_factor"] >= 0.85


def test_build_section_runtime_budget_compacts_simple_chapter():
    speed_profile = {
        "kg_top_k": 3,
        "doc_limit": 5,
        "standard_limit": 2,
        "llm_timeout_sec": 120,
        "section_retry_limit": 2,
    }
    got = _build_section_runtime_budget(
        title="编制依据与原则",
        chapter_target_pages=1,
        speed_profile=speed_profile,
        specialist_count=0,
        has_boq_focus=False,
        has_chapter_contract=False,
    )
    assert got["kg_top_k"] <= 2
    assert got["doc_limit"] <= 3
    assert got["requirements_limit"] <= 18
    assert got["section_retry_limit"] == 1
    assert got["llm_timeout_sec"] <= 55
    assert got["max_output_tokens_hint"] <= 1800
    assert got["runtime_budget_reason"] == "low_complexity_small_section"


def test_build_section_runtime_budget_keeps_rich_budget_for_complex_chapter():
    speed_profile = {
        "kg_top_k": 3,
        "doc_limit": 5,
        "standard_limit": 2,
        "llm_timeout_sec": 120,
        "section_retry_limit": 2,
    }
    got = _build_section_runtime_budget(
        title="关键工序与危大工程质量安全控制",
        chapter_target_pages=6,
        speed_profile=speed_profile,
        specialist_count=3,
        has_boq_focus=True,
        has_chapter_contract=True,
    )
    assert got["graph_top_k"] >= 5
    assert got["doc_limit"] >= 5
    assert got["requirements_limit"] >= 24
    assert got["section_retry_limit"] == 2
    assert got["llm_timeout_sec"] == 120
    assert got["max_output_tokens_hint"] >= 5200
    assert got["runtime_budget_reason"] == "complex_section_full_budget"


def test_build_section_runtime_budget_tightens_retry_for_medium_complexity_small_pages():
    speed_profile = {
        "kg_top_k": 3,
        "doc_limit": 5,
        "standard_limit": 2,
        "section_retry_limit": 3,
        "llm_timeout_sec": 120,
    }
    got = _build_section_runtime_budget(
        title="工程概况与项目质量理解",
        chapter_target_pages=2,
        speed_profile=speed_profile,
        specialist_count=2,
        has_boq_focus=False,
        has_chapter_contract=True,
    )
    assert got["section_retry_limit"] == 1
    assert got["llm_timeout_sec"] <= 95
    assert got["runtime_budget_reason"] == "medium_complexity_tightened_budget"


@pytest.mark.asyncio
async def test_section_writer_passes_timeout_and_token_budget():
    llm = AsyncMock()
    llm.complete.return_value = {
        "provider": "google",
        "model": "gemini-3-pro-preview",
        "text": "工序控制：每班2次巡检，偏差≤5mm，记录齐全。",
    }
    writer = SectionWriter(llm=llm, max_retry=1)
    result = await writer.write(
        "测试章节",
        {
            "section_min_length": 10,
            "section_max_length": 200,
            "llm_timeout_sec": 77,
            "max_output_tokens_hint": 1200,
        },
    )
    assert "content" in result
    assert llm.complete.call_count == 1
    _, kwargs = llm.complete.call_args
    assert int(kwargs["timeout_sec"]) == 77
    assert int(kwargs["max_output_tokens"]) == 900


@pytest.mark.asyncio
async def test_section_writer_respects_runtime_token_hint_for_small_sections():
    llm = AsyncMock()
    llm.complete.return_value = {
        "provider": "openai",
        "model": "gpt-5.4",
        "text": "施工步骤：放线、复核、验收。每班2次巡检，偏差控制在5mm以内。",
    }
    writer = SectionWriter(llm=llm, max_retry=1)
    result = await writer.write(
        "小章节测试",
        {
            "section_min_length": 100,
            "section_max_length": 2600,
            "section_target_length": 1800,
            "llm_timeout_sec": 55,
            "max_output_tokens_hint": 1800,
        },
    )
    assert "content" in result
    _, kwargs = llm.complete.call_args
    assert int(kwargs["timeout_sec"]) == 55
    assert int(kwargs["max_output_tokens"]) == 1800


@pytest.mark.asyncio
async def test_async_thread_cache_coalesces_same_inflight_request():
    calls = {"count": 0}
    stats = {}
    cache = AsyncThreadCache(items={}, stats=stats, enabled=True)

    def slow_sync():
        calls["count"] += 1
        time.sleep(0.05)
        return {"ok": True, "n": calls["count"]}

    out1, out2 = await asyncio.gather(
        cache.get_or_run("same-key", slow_sync),
        cache.get_or_run("same-key", slow_sync),
    )

    assert out1 == out2
    assert calls["count"] == 1
    assert int(stats["misses"]) == 1
    assert int(stats["stores"]) == 1
    assert int(stats["coalesced"]) == 1


@pytest.mark.asyncio
async def test_async_thread_cache_clears_failed_inflight_and_allows_retry():
    calls = {"count": 0}
    cache = AsyncThreadCache(items={}, stats={}, enabled=True)

    def flaky_sync():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    with pytest.raises(RuntimeError):
        await cache.get_or_run("flaky-key", flaky_sync)

    out = await cache.get_or_run("flaky-key", flaky_sync)
    assert out == {"ok": True}
    assert calls["count"] == 2
