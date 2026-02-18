from __future__ import annotations

from backend.zhifei_autoplan.cross_index import build_cross_index


def test_build_cross_index_happy_path():
    boq = {
        "items": [
            {
                "boq_code": "010101",
                "name": "钢筋",
                "quantity": 120.0,
                "unit": "t",
                "unit_price": 5200.0,
                "total_price": 624000.0,
                "process": {"name": "钢筋绑扎"},
            }
        ],
        "stats": {
            "top_quantity_items": [
                {"boq_code": "010101", "name": "钢筋", "quantity": 120.0, "unit": "t", "unit_price": 5200.0, "total_price": 624000.0}
            ],
            "top_material_demand_items": [
                {"boq_code": "010101", "name": "钢筋", "quantity": 120.0, "unit": "t", "unit_price": 5200.0, "total_price": 624000.0}
            ],
            "top_total_price_items": [
                {"boq_code": "010101", "name": "钢筋", "quantity": 120.0, "unit": "t", "unit_price": 5200.0, "total_price": 624000.0}
            ],
            "top_unit_price_items": [
                {"boq_code": "010101", "name": "钢筋", "quantity": 120.0, "unit": "t", "unit_price": 5200.0, "total_price": 624000.0}
            ],
        },
    }
    sections = [
        {
            "title": "钢筋绑扎施工工艺",
            "content": "钢筋：间距200mm，频次=1次/天。风险→控制→验证。【证据:dwg.pdf#p1_12345678@90】",
        }
    ]
    boq_focus = {"must_cover_keywords": ["钢筋"]}
    drawing_index = {"chapter_bindings": [{"chapter": "钢筋绑扎施工工艺", "locator": "dwg.pdf#p1_12345678@90"}]}
    standard_index = {
        "standards": [{"filename": "std.pdf", "sha256": "x" * 64}],
        "chapter_bindings": [{"chapter": "钢筋绑扎施工工艺", "locator": "std.pdf#p2_abcdef12@34"}],
    }
    quality_checks = {
        "boq_focus_item_closure": {
            "items": [
                {
                    "item": "钢筋",
                    "ok": True,
                    "reason": "ok",
                    "hit_sections": [
                        {
                            "title": "钢筋绑扎施工工艺",
                            "ok": True,
                            "triplet_count": 1,
                            "hit_keys": ["频次", "间距", "阈值"],
                            "has_units": True,
                            "evidence_count": 1,
                            "mentions_checked": 1,
                        }
                    ],
                }
            ]
        }
    }

    out = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus=boq_focus,
        drawing_index=drawing_index,
        standard_index=standard_index,
        quality_checks=quality_checks,
        project_id="p1",
    )
    assert out["ok"] is True
    assert out["project_id"] == "p1"
    assert out["focus_count"] == 1
    row = out["focus_items"][0]
    assert row["name"] == "钢筋"
    assert row["chapter"] == "钢筋绑扎施工工艺"
    assert row["drawing_locator"] == "dwg.pdf#p1_12345678@90"
    assert row["standard_locator"] == "std.pdf#p2_abcdef12@34"
    assert "工程量大" in row["categories"]
    assert row["process_name"] == "钢筋绑扎"
    assert row["closure"]["ok"] is True


def test_build_cross_index_missing_parts_when_not_closed():
    boq = {
        "items": [{"boq_code": "020202", "name": "混凝土", "quantity": 300.0, "unit": "m3", "unit_price": 480.0, "total_price": 144000.0}],
        "stats": {"top_quantity_items": [{"boq_code": "020202", "name": "混凝土", "quantity": 300.0, "unit": "m3", "unit_price": 480.0, "total_price": 144000.0}]},
    }
    sections = [{"title": "混凝土浇筑施工方法", "content": "混凝土：本章提到但未给出可核查闭环。"}]
    quality_checks = {
        "boq_focus_item_closure": {
            "items": [
                {
                    "item": "混凝土",
                    "ok": False,
                    "reason": "mentioned_but_not_closed",
                    "hit_sections": [
                        {
                            "title": "混凝土浇筑施工方法",
                            "ok": False,
                            "triplet_count": 0,
                            "hit_keys": ["频次"],
                            "has_units": False,
                            "evidence_count": 0,
                            "mentions_checked": 1,
                        }
                    ],
                }
            ]
        }
    }
    out = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus={"must_cover_keywords": ["混凝土"]},
        drawing_index={},
        standard_index={},
        quality_checks=quality_checks,
    )
    row = out["focus_items"][0]
    assert row["chapter"] == "混凝土浇筑施工方法"
    missing = row["closure"]["missing_parts"]
    assert "三元组" in missing
    assert "量化" in missing
    assert "证据" in missing


def test_build_cross_index_fallback_to_stats_when_focus_missing():
    boq = {
        "items": [{"boq_code": "030303", "name": "模板", "quantity": 1000.0, "unit": "m2", "unit_price": 80.0, "total_price": 80000.0}],
        "stats": {"top_quantity_items": [{"boq_code": "030303", "name": "模板", "quantity": 1000.0, "unit": "m2", "unit_price": 80.0, "total_price": 80000.0}]},
    }
    sections = [{"title": "模板安装施工工艺", "content": "模板【证据:x.pdf#p1_aaaaaaaa@1】"}]
    out = build_cross_index(boq=boq, sections=sections, boq_focus=None, drawing_index=None, standard_index=None, quality_checks=None)
    assert out["ok"] is True
    assert out["focus_count"] == 1
    assert out["focus_items"][0]["name"] == "模板"


def test_build_cross_index_prefers_precise_process_chapter():
    boq = {
        "items": [
            {
                "boq_code": "040404",
                "name": "模板",
                "quantity": 2600.0,
                "unit": "m2",
                "unit_price": 82.0,
                "total_price": 213200.0,
                "process": {"name": "模板安装"},
            }
        ],
        "stats": {
            "top_quantity_items": [{"boq_code": "040404", "name": "模板", "quantity": 2600.0, "unit": "m2", "unit_price": 82.0, "total_price": 213200.0}],
            "top_total_price_items": [{"boq_code": "040404", "name": "模板", "quantity": 2600.0, "unit": "m2", "unit_price": 82.0, "total_price": 213200.0}],
        },
    }
    sections = [
        {
            "title": "工程总体部署",
            "content": "模板工程总体安排：风险→控制→验证；频次1次/日，阈值95%。【证据:summary.pdf#p1_11111111@12】",
        },
        {
            "title": "模板安装施工工艺",
            "content": (
                "模板安装流程：间距900mm，厚度18mm，频次2次/日。风险→控制→验证。"
                "图纸定位与标准对照同步执行。"
                "【证据:dwg_A.pdf#p12_abcdef12@220】【证据:std_A.pdf#p3_9876abcd@55】"
            ),
        },
    ]
    quality_checks = {
        "boq_focus_item_closure": {
            "items": [
                {
                    "item": "模板",
                    "ok": True,
                    "reason": "ok",
                    "hit_sections": [
                        {
                            "title": "工程总体部署",
                            "ok": True,
                            "triplet_count": 3,
                            "hit_keys": ["频次", "阈值", "人数"],
                            "has_units": True,
                            "evidence_count": 1,
                            "mentions_checked": 1,
                        },
                        {
                            "title": "模板安装施工工艺",
                            "ok": True,
                            "triplet_count": 2,
                            "hit_keys": ["频次", "间距", "厚度"],
                            "has_units": True,
                            "evidence_count": 2,
                            "mentions_checked": 1,
                        },
                    ],
                }
            ]
        }
    }
    drawing_index = {
        "drawings": [{"filename": "dwg_A.pdf", "sha256": "x" * 64}],
        "chapter_bindings": [{"chapter": "模板安装施工工艺", "locator": "dwg_A.pdf#p12_abcdef12@220"}],
    }
    standard_index = {
        "standards": [{"filename": "std_A.pdf", "sha256": "y" * 64}],
        "chapter_bindings": [{"chapter": "模板安装施工工艺", "locator": "std_A.pdf#p3_9876abcd@55"}],
    }
    out = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus={"must_cover_keywords": ["模板"]},
        drawing_index=drawing_index,
        standard_index=standard_index,
        quality_checks=quality_checks,
    )
    row = out["focus_items"][0]
    assert row["chapter"] == "模板安装施工工艺"
    assert row["drawing_locator"] == "dwg_A.pdf#p12_abcdef12@220"
    assert row["standard_locator"] == "std_A.pdf#p3_9876abcd@55"


def test_build_cross_index_fallback_mentioned_prefers_relevant_title():
    boq = {
        "items": [
            {
                "boq_code": "050505",
                "name": "钢筋",
                "quantity": 120.0,
                "unit": "t",
                "unit_price": 5200.0,
                "total_price": 624000.0,
                "process": {"name": "钢筋绑扎"},
            }
        ],
        "stats": {
            "top_quantity_items": [{"boq_code": "050505", "name": "钢筋", "quantity": 120.0, "unit": "t", "unit_price": 5200.0, "total_price": 624000.0}]
        },
    }
    sections = [
        {"title": "工程概况", "content": "本项目使用钢筋，详见总说明。"},
        {"title": "钢筋绑扎施工工艺", "content": "钢筋绑扎：间距200mm，频次1次/日。【证据:dwg.pdf#p2_abcd1234@88】"},
    ]
    out = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus={"must_cover_keywords": ["钢筋"]},
        drawing_index={"drawings": [{"filename": "dwg.pdf", "sha256": "z" * 64}], "chapter_bindings": []},
        standard_index={},
        quality_checks=None,
    )
    row = out["focus_items"][0]
    assert row["chapter"] == "钢筋绑扎施工工艺"
