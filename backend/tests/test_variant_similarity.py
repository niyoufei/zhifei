from __future__ import annotations


from backend.zhifei_autoplan.variant_similarity import pair_similarity, compute_variant_similarity


def test_pair_similarity_strips_evidence_and_locators():
    a = (
        "本章交付物：隐蔽验收记录；测量复核记录。【证据:dwg.pdf#p1_abcdef12@90】\n"
        "图纸定位：dwg.pdf#p1_abcdef12@90；标准定位：std.pdf#p2_12345678@10。\n"
    )
    b = (
        "本章交付物：隐蔽验收记录；测量复核记录。【证据:other.pdf#p9_ffffffff@1】\n"
        "图纸定位：other.pdf#p9_ffffffff@1；标准定位：x.pdf#p2_12345678@10。\n"
    )
    sim = pair_similarity(a, b)
    assert sim["combined"] >= 0.95


def test_pair_similarity_ignores_focus_card_blocks():
    a = (
        "工序流程\n- 步骤1 ...\n\n"
        "【清单重点项控制卡】\n- 清单项：钢筋；工程量=120t；单价=5200元/t；合价=624000元\n"
        "  风险→控制→验证：风险：...；控制：...；验证：...。【证据:boq.xlsx#p1_11111111@10】\n"
    )
    b = (
        "控制指标矩阵\n- 频次=2次/日\n\n"
        "【清单重点项控制卡】\n- 清单项：钢筋；工程量=120t；单价=5200元/t；合价=624000元\n"
        "  风险→控制→验证：风险：...；控制：...；验证：...。【证据:boq.xlsx#p1_11111111@10】\n"
    )
    sim = pair_similarity(a, b)
    # Focus blocks are ignored, so the remaining structure differs.
    assert sim["combined"] < 0.80


def test_compute_variant_similarity_flags_near_duplicates():
    variants = [
        {"outline": ["章节1"], "sections": [{"title": "章节1", "content": "A" * 1200}]},
        {"outline": ["章节1"], "sections": [{"title": "章节1", "content": "A" * 1200}]},
        {"outline": ["章节1"], "sections": [{"title": "章节1", "content": "A" * 1200}]},
    ]
    rep = compute_variant_similarity(variants, chapter_threshold=0.9, overall_threshold=0.85, min_chars=800, ignore_title_keywords=[])
    assert rep["ok"] is False
    assert rep["flagged_count"] == 1
    assert rep["by_chapter"] and rep["by_chapter"][0]["title"] == "章节1"


def test_compute_variant_similarity_skips_short_chapters():
    variants = [
        {"outline": ["章节1"], "sections": [{"title": "章节1", "content": "短文本" * 30}]},
        {"outline": ["章节1"], "sections": [{"title": "章节1", "content": "短文本" * 30}]},
    ]
    rep = compute_variant_similarity(variants, min_chars=800, ignore_title_keywords=[])
    assert rep["ok"] is True
    assert rep["flagged_count"] == 0
    assert rep.get("by_chapter") == []


def test_compute_variant_similarity_ignores_catalog_like_titles():
    variants = [
        {"outline": ["目录"], "sections": [{"title": "目录", "content": "1. a\\n2. b\\n" * 200}]},
        {"outline": ["目录"], "sections": [{"title": "目录", "content": "1. a\\n2. b\\n" * 200}]},
    ]
    rep = compute_variant_similarity(variants)
    assert rep["ok"] is True


def test_compute_variant_similarity_relaxes_project_overview_titles():
    variants = [
        {"outline": ["项目概况"], "sections": [{"title": "项目概况", "content": "A" * 1200}]},
        {"outline": ["项目概况"], "sections": [{"title": "项目概况", "content": "A" * 1200}]},
        {"outline": ["项目概况"], "sections": [{"title": "项目概况", "content": "A" * 1200}]},
    ]
    rep = compute_variant_similarity(variants, ignore_title_keywords=[])
    # Relaxed title should not fail the diversity gate.
    assert rep["ok"] is True
    assert rep["flagged_count"] == 0
    assert rep["relaxed_flagged_count"] >= 1
