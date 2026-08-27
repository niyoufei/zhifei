from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from backend.zhifei_autoplan.cross_index import (
    build_cross_index,
    validate_cross_index_contract,
)


def _full_sha(prefix: str) -> str:
    return prefix + "a" * (64 - len(prefix))


def _locator(filename: str, sha_prefix: str, page: int, offset: int) -> str:
    return f"{filename}#p{page}_{_full_sha(sha_prefix)}@{offset}"


def _drawing_index(
    *,
    filename: str,
    sha8: str,
    page: int,
    offset: int,
    text: str,
    chapter: str | None = None,
    project_id: str | None = None,
    text_status: str = "indexed",
) -> dict:
    sha256 = _full_sha(sha8)
    locator = f"{filename}#p{page}_{sha256}@{offset}"
    page_text = " " * offset + text
    page_summary = " ".join(page_text.split())[:360]
    page_hash = hashlib.sha256(page_text.encode("utf-8")).hexdigest()
    matched_text = text[: max(1, min(4, len(text)))]
    window_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    drawing = {
        "filename": filename,
        "sha256": sha256,
        "text_status": text_status,
        "page_anchors": (
            [
                {
                    "page": page,
                    "start_offset": 0,
                    "end_offset": len(page_text),
                    "text_sha256": page_hash,
                    "snippet": page_summary,
                    "boundary_source": "declared_single_page",
                    "keywords": [],
                }
            ]
            if text_status == "indexed"
            else []
        ),
        "page_boundary_status": "reliable_declared_single_page",
    }
    bindings = []
    if chapter:
        bindings.append(
            {
                "chapter": chapter,
                "locator": locator,
                "filename": filename,
                "sha256": sha256,
                "page": page,
                "offset": offset,
                "snippet": text,
                "matched_text": matched_text,
                "match_start": offset,
                "match_end": offset + len(matched_text),
                "match_window": {
                    "start_offset": offset,
                    "end_offset": offset + len(text),
                    "text": text,
                    "text_sha256": window_hash,
                    "summary": " ".join(text.split()),
                },
                "page_text_sha256": page_hash,
                "page_summary": page_summary,
                "page_boundary_status": "reliable_declared_single_page",
                "binding_basis": "chapter_specific_extract_hit",
            }
        )
    return {
        "project_id": project_id,
        "drawings": [drawing],
        "chapter_bindings": bindings,
    }


def _closed_quality(chapter: str, *names: str) -> dict:
    return {
        "boq_focus_item_closure": {
            "items": [
                {
                    "item": name,
                    "ok": True,
                    "reason": "ok",
                    "hit_sections": [
                        {
                            "title": chapter,
                            "ok": True,
                            "triplet_count": 1,
                            "hit_keys": ["频次", "间距", "阈值"],
                            "has_units": True,
                            "evidence_count": 1,
                        }
                    ],
                }
                for name in names
            ]
        }
    }


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
    drawing_index = _drawing_index(
        filename="dwg.pdf",
        sha8="12345678",
        page=1,
        offset=90,
        text="钢筋绑扎构件位置、间距和节点做法。",
        chapter="钢筋绑扎施工工艺",
        project_id="p1",
    )
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
    assert row["drawing_locator"] == _locator("dwg.pdf", "12345678", 1, 90)
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


def test_build_cross_index_normalizes_wrapped_boq_names_across_sources():
    boq = {
        "items": [
            {
                "boq_code": "030304",
                "name": "预制钢筋混凝土\n管桩",
                "quantity": 20.0,
                "unit": "根",
                "process": {"name": "管桩施工"},
            }
        ],
        "stats": {
            "top_quantity_items": [
                {
                    "boq_code": "030304",
                    "name": "预制钢筋混凝土 管桩",
                    "quantity": 20.0,
                    "unit": "根",
                }
            ]
        },
    }
    title = "管桩施工工艺"
    quality_checks = {
        "boq_focus_item_closure": {
            "items": [
                {
                    "item": "预制钢筋混凝土管桩",
                    "ok": True,
                    "reason": "ok",
                    "hit_sections": [
                        {
                            "title": title,
                            "ok": True,
                            "triplet_count": 2,
                            "hit_keys": ["频次", "阈值"],
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
        sections=[
            {
                "title": title,
                "content": (
                    "预制钢筋混凝土管桩：风险→控制→验证；"
                    "频次1次/班，阈值95%。【证据:桩基图.pdf#p3_12345678@45】"
                ),
            }
        ],
        boq_focus={
            "must_cover_keywords": [
                "预制钢筋混凝土\n管桩",
                "预制钢筋混凝土 管桩",
            ]
        },
        drawing_index=_drawing_index(
            filename="桩基图.pdf",
            sha8="12345678",
            page=3,
            offset=45,
            text="预制钢筋混凝土管桩定位及节点做法。",
            chapter=title,
        ),
        standard_index={},
        quality_checks=quality_checks,
    )

    assert out["focus_count"] == 1
    assert out["focus_items"][0]["name"] == "预制钢筋混凝土管桩"
    assert "工程量大" in out["focus_items"][0]["categories"]
    assert out["focus_items"][0]["closure"]["ok"] is True


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda value: None, "not_object"),
        (lambda value: {}, "schema_incomplete"),
        (lambda value: {**value, "ok": False}, "not_ok"),
        (
            lambda value: {
                **value,
                "focus_items": [{**value["focus_items"][0], "name": "错项"}],
            },
            "identity_mismatch",
        ),
        (lambda value: {**value, "mentioned_count": 2}, "counter_out_of_range"),
    ],
)
def test_cross_index_contract_fails_closed_on_invalid_result(mutation, reason):
    valid = {
        "ok": True,
        "focus_count": 1,
        "mentioned_count": 1,
        "closed_ok_count": 1,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
        "focus_items": [
            {
                "name": "钢筋",
                "chapter": "钢筋绑扎施工工艺",
                "drawing_locator": "dwg.pdf#p1_12345678@90",
                "drawing_requirement": {"status": "required", "reason": "focus_item_default"},
                "drawing_validation": {"ok": True, "reason": "validated"},
                "closure": {"ok": True},
                "flags": [],
            }
        ],
    }

    with pytest.raises(ValueError, match=reason):
        validate_cross_index_contract(
            mutation(valid),
            expected_names=["钢筋"],
        )


def test_cross_index_contract_accepts_explicit_empty_focus_result():
    result = {
        "ok": False,
        "focus_count": 0,
        "mentioned_count": 0,
        "closed_ok_count": 0,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
        "focus_items": [],
    }

    assert validate_cross_index_contract(result, expected_names=[]) is result


def test_cross_index_fallback_never_drops_hazard_only_focus():
    out = build_cross_index(
        boq={
            "items": [{"name": "氧气瓶", "quantity": 2, "unit": "瓶"}],
            "stats": {"hazardous_material_items": [{"name": "氧气瓶"}]},
        },
        sections=[{"title": "安全管理", "content": "氧气瓶分类储运。"}],
        boq_focus=None,
        drawing_index={},
        standard_index={},
        quality_checks={},
    )

    assert out["focus_count"] == 1
    assert out["focus_items"][0]["name"] == "氧气瓶"
    assert "危险品材料" in out["focus_items"][0]["categories"]


def test_cross_index_merges_canonical_aliases_across_stats_categories():
    out = build_cross_index(
        boq={
            "items": [{"name": "预制钢筋混凝土管桩", "quantity": 10, "unit": "根"}],
            "stats": {
                "top_quantity_items": [
                    {"name": "预制钢筋混凝土\n管桩", "quantity": 10, "unit": "根"}
                ],
                "top_total_price_items": [
                    {"name": "预制钢筋混凝土 管桩", "total_price": 500000}
                ],
            },
        },
        sections=[{"title": "桩基工程", "content": "预制钢筋混凝土管桩施工。"}],
        boq_focus={"must_cover_keywords": ["预制钢筋混凝土管桩"]},
        drawing_index={},
        standard_index={},
        quality_checks={},
    )

    row = out["focus_items"][0]
    assert row["total_price"] == 500000
    assert set(row["categories"]) == {"工程量大", "单体造价高"}


def test_cross_index_locator_search_uses_nfkc_equivalent_span():
    locator = _locator("桩基图.pdf", "12345678", 3, 45)
    out = build_cross_index(
        boq={
            "items": [{"name": "管桩(DN100)", "quantity": 1, "unit": "根"}],
            "stats": {"top_quantity_items": [{"name": "管桩(DN100)"}]},
        },
        sections=[
            {
                "title": "桩基工程",
                "content": f"管桩（DN100）闭环。【证据:{locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["管桩(DN100)"]},
        drawing_index=_drawing_index(
            filename="桩基图.pdf",
            sha8="12345678",
            page=3,
            offset=45,
            text="管桩（DN100）定位与节点做法。",
            chapter="桩基工程",
        ),
        standard_index={},
        quality_checks={},
    )

    assert out["focus_items"][0]["evidence_locators_near"] == [locator]
    assert out["focus_items"][0]["drawing_locator"] == locator


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
    drawing_index = _drawing_index(
        filename="dwg_A.pdf",
        sha8="abcdef12",
        page=12,
        offset=220,
        text="模板安装构件位置、间距及节点做法。",
        chapter="模板安装施工工艺",
    )
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
    assert row["drawing_locator"] == _locator("dwg_A.pdf", "abcdef12", 12, 220)
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
        drawing_index=_drawing_index(
            filename="dwg.pdf",
            sha8="abcd1234",
            page=2,
            offset=88,
            text="钢筋绑扎间距及节点做法。",
            chapter="钢筋绑扎施工工艺",
        ),
        standard_index={},
        quality_checks=None,
    )
    row = out["focus_items"][0]
    assert row["chapter"] == "钢筋绑扎施工工艺"


def test_generic_drawing_words_cannot_validate_a_locator():
    chapter = "钢结构施工工艺"
    locator = _locator("结构图.pdf", "11111111", 1, 20)
    out = build_cross_index(
        boq={"items": [{"name": "钢梁"}], "stats": {}},
        sections=[
            {
                "title": chapter,
                "content": f"钢梁：频次1次/日，风险→控制→验证。【证据:{locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=_drawing_index(
            filename="结构图.pdf",
            sha8="11111111",
            page=1,
            offset=20,
            text="图纸详见施工图纸节点和大样说明。",
            chapter=chapter,
        ),
        quality_checks=_closed_quality(chapter, "钢梁"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == "drawing_locator_irrelevant"
    assert row["closure"]["content_ok"] is True
    assert row["closure"]["ok"] is False
    assert out["missing_drawing_locator_count"] == 1


def test_filename_scope_and_discipline_cannot_substitute_for_nearby_page_text():
    chapter = "钢梁安装施工工艺"
    locator = _locator("钢梁节点图.pdf", "12121212", 1, 20)
    drawing_index = _drawing_index(
        filename="钢梁节点图.pdf",
        sha8="12121212",
        page=1,
        offset=20,
        text="图纸详见节点和大样说明。",
        chapter=chapter,
    )
    drawing_index["drawings"][0].update(
        {
            "chapter_scope": chapter,
            "process_scope": "钢梁安装",
            "discipline_tags": ["钢结构", "钢梁"],
        }
    )
    out = build_cross_index(
        boq={
            "items": [{"name": "钢梁", "process": {"name": "钢梁安装"}}],
            "stats": {},
        },
        sections=[
            {
                "title": chapter,
                "content": f"钢梁风险→控制→验证。【证据:{locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=drawing_index,
        quality_checks=_closed_quality(chapter, "钢梁"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == "drawing_locator_irrelevant"


def test_short_hash_locator_is_rejected_even_when_prefix_collides():
    chapter = "钢梁安装施工工艺"
    drawing_index = _drawing_index(
        filename="结构图.pdf",
        sha8="deadbeef",
        page=1,
        offset=20,
        text="钢梁安装构件位置与节点做法。",
        chapter=chapter,
    )
    collision = deepcopy(drawing_index["drawings"][0])
    collision["sha256"] = "deadbeef" + "b" * 56
    drawing_index["drawings"].append(collision)
    short_locator = "结构图.pdf#p1_deadbeef@20"
    drawing_index["chapter_bindings"][0]["locator"] = short_locator
    out = build_cross_index(
        boq={"items": [{"name": "钢梁"}], "stats": {}},
        sections=[
            {
                "title": chapter,
                "content": f"钢梁风险→控制→验证。【证据:{short_locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=drawing_index,
        quality_checks=_closed_quality(chapter, "钢梁"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == "locator_format_invalid"


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (
            lambda binding: binding.update({"offset": int(binding["offset"]) + 1}),
            "binding_offset_mismatch",
        ),
        (
            lambda binding: binding.update({"page_summary": "伪造页摘要"}),
            "binding_page_summary_mismatch",
        ),
        (
            lambda binding: binding.update(
                {
                    "locator": _locator("钢梁图.pdf", "34343434", 1, 21),
                    "offset": 21,
                }
            ),
            "binding_match_window_out_of_bounds",
        ),
    ],
)
def test_locator_must_match_binding_offset_window_and_page_summary(
    mutation, expected_reason
):
    chapter = "钢梁安装施工工艺"
    drawing_index = _drawing_index(
        filename="钢梁图.pdf",
        sha8="34343434",
        page=1,
        offset=20,
        text="钢梁安装构件位置与节点做法。",
        chapter=chapter,
    )
    binding = drawing_index["chapter_bindings"][0]
    mutation(binding)
    locator = str(binding["locator"])
    out = build_cross_index(
        boq={"items": [{"name": "钢梁"}], "stats": {}},
        sections=[
            {
                "title": chapter,
                "content": f"钢梁风险→控制→验证。【证据:{locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=drawing_index,
        quality_checks=_closed_quality(chapter, "钢梁"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == expected_reason


def test_unrelated_items_cannot_share_one_drawing_locator_and_counts_reconcile():
    chapter = "钢结构与电气施工工艺"
    locator = _locator("钢结构图.pdf", "22222222", 2, 80)
    out = build_cross_index(
        boq={
            "items": [{"name": "钢梁"}, {"name": "插座"}],
            "stats": {},
        },
        sections=[
            {
                "title": chapter,
                "content": (
                    f"钢梁：频次1次/日，风险→控制→验证。【证据:{locator}】\n"
                    f"插座：频次1次/日，风险→控制→验证。【证据:{locator}】"
                ),
            }
        ],
        boq_focus={"must_cover_keywords": ["钢梁", "插座"]},
        drawing_index=_drawing_index(
            filename="钢结构图.pdf",
            sha8="22222222",
            page=2,
            offset=80,
            text="钢梁连接、构件位置与焊缝节点。",
            chapter=chapter,
        ),
        quality_checks=_closed_quality(chapter, "钢梁", "插座"),
    )

    steel, socket = out["focus_items"]
    assert steel["drawing_locator"] == locator
    assert steel["closure"]["ok"] is True
    assert socket["drawing_locator"] is None
    assert socket["drawing_validation"]["reason"] == "drawing_locator_irrelevant"
    assert socket["closure"]["ok"] is False
    assert out["focus_count"] == out["mentioned_count"] == 2
    assert out["closed_ok_count"] == 1
    assert out["missing_drawing_locator_count"] == 1
    assert validate_cross_index_contract(out, expected_names=["钢梁", "插座"]) is out


def test_discipline_only_locator_cannot_be_reused_for_another_item():
    chapter = "电气安装施工工艺"
    locator = _locator("电气总图.pdf", "26262626", 1, 30)
    out = build_cross_index(
        boq={"items": [{"name": "插座"}, {"name": "普通灯具"}], "stats": {}},
        sections=[
            {
                "title": chapter,
                "content": (
                    f"插座风险→控制→验证。【证据:{locator}】\n"
                    f"普通灯具风险→控制→验证。【证据:{locator}】"
                ),
            }
        ],
        boq_focus={"must_cover_keywords": ["插座", "普通灯具"]},
        drawing_index=_drawing_index(
            filename="电气总图.pdf",
            sha8="26262626",
            page=1,
            offset=30,
            text="电气安装平面布置及回路说明。",
            chapter=chapter,
        ),
        quality_checks=_closed_quality(chapter, "插座", "普通灯具"),
    )

    first, second = out["focus_items"]
    assert first["drawing_locator"] == locator
    assert second["drawing_locator"] is None
    assert (
        second["drawing_validation"]["reason"]
        == "drawing_locator_shared_without_item_or_process_match"
    )
    assert out["closed_ok_count"] == 1
    assert out["missing_drawing_locator_count"] == 1


def test_missing_drawing_text_or_ocr_fails_closed():
    chapter = "钢梁安装施工工艺"
    out = build_cross_index(
        boq={"items": [{"name": "钢梁"}], "stats": {}},
        sections=[{"title": chapter, "content": "钢梁风险→控制→验证。"}],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=_drawing_index(
            filename="钢梁图.pdf",
            sha8="33333333",
            page=1,
            offset=10,
            text="钢梁节点",
            chapter=chapter,
            text_status="missing_text_or_ocr",
        ),
        quality_checks=_closed_quality(chapter, "钢梁"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == "drawing_text_or_ocr_missing"
    assert out["closed_ok_count"] == 0


def test_drawing_alias_can_validate_a_specific_locator():
    chapter = "螺栓连接施工工艺"
    locator = _locator("钢结构节点图.pdf", "44444444", 4, 160)
    out = build_cross_index(
        boq={"items": [{"name": "高强螺栓"}], "stats": {}},
        sections=[
            {
                "title": chapter,
                "content": f"高强螺栓风险→控制→验证。【证据:{locator}】",
            }
        ],
        boq_focus={"must_cover_keywords": ["高强螺栓"]},
        drawing_index=_drawing_index(
            filename="钢结构节点图.pdf",
            sha8="44444444",
            page=4,
            offset=160,
            text="高强度螺栓连接节点及构件位置。",
            chapter=chapter,
        ),
        quality_checks=_closed_quality(chapter, "高强螺栓"),
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] == locator
    assert "高强度螺栓" in row["drawing_validation"]["matched_terms"]
    assert row["closure"]["ok"] is True


def test_not_applicable_requires_reason_and_can_close_without_drawing():
    chapter = "氧气瓶安全管理施工方案"
    out = build_cross_index(
        boq={"items": [{"name": "氧气瓶"}], "stats": {}},
        sections=[{"title": chapter, "content": "氧气瓶风险→控制→验证。"}],
        boq_focus={
            "must_cover_keywords": ["氧气瓶"],
            "drawing_requirements": {
                "氧气瓶": {
                    "status": "not_applicable",
                    "reason": "安全物资无构造图纸定位要求，已由项目负责人确认",
                    "approval_receipt": {
                        "receipt_id": "APR-001",
                        "status": "approved",
                        "project_id": "p1",
                        "summary": "氧气瓶为安全物资，不适用构造图纸定位。",
                        "approved_by": "项目负责人",
                        "approved_at": "2026-08-27T09:00:00+08:00",
                    },
                }
            },
        },
        drawing_index={},
        quality_checks=_closed_quality(chapter, "氧气瓶"),
        project_id="p1",
    )

    row = out["focus_items"][0]
    assert row["drawing_requirement"]["status"] == "not_applicable"
    assert row["drawing_validation"] == {"ok": True, "reason": "not_applicable"}
    assert out["missing_drawing_locator_count"] == 0
    assert out["closed_ok_count"] == 1


def test_drawing_exemption_without_reason_fails_closed_to_required():
    chapter = "氧气瓶安全管理施工方案"
    out = build_cross_index(
        boq={"items": [{"name": "氧气瓶"}], "stats": {}},
        sections=[{"title": chapter, "content": "氧气瓶风险→控制→验证。"}],
        boq_focus={
            "must_cover_keywords": ["氧气瓶"],
            "drawing_requirements": {"氧气瓶": {"status": "not_applicable"}},
        },
        drawing_index={},
        quality_checks=_closed_quality(chapter, "氧气瓶"),
    )

    row = out["focus_items"][0]
    assert row["drawing_requirement"] == {
        "status": "required",
        "reason": "missing_exemption_reason_fail_closed",
    }
    assert row["closure"]["ok"] is False
    assert out["missing_drawing_locator_count"] == 1


@pytest.mark.parametrize(
    ("receipt", "expected_reason"),
    [
        (None, "exemption_receipt_missing_fail_closed"),
        (
            {
                "receipt_id": "APR-002",
                "status": "draft",
                "project_id": "p1",
                "summary": "待批准。",
                "approved_by": "项目负责人",
                "approved_at": "2026-08-27T09:00:00+08:00",
            },
            "exemption_receipt_not_approved_fail_closed",
        ),
        (
            {
                "receipt_id": "APR-003",
                "status": "approved",
                "project_id": "other-project",
                "summary": "其他项目回执。",
                "approved_by": "项目负责人",
                "approved_at": "2026-08-27T09:00:00+08:00",
            },
            "exemption_receipt_project_mismatch_fail_closed",
        ),
        (
            {
                "receipt_id": "APR-004",
                "status": "approved",
                "project_id": "p1",
                "summary": "",
                "approved_by": "项目负责人",
                "approved_at": "2026-08-27T09:00:00+08:00",
            },
            "exemption_receipt_incomplete_fail_closed",
        ),
    ],
)
def test_drawing_exemption_requires_approved_project_receipt(receipt, expected_reason):
    chapter = "氧气瓶安全管理施工方案"
    requirement = {
        "status": "optional",
        "reason": "本项拟按项目审批回执降为可选",
    }
    if receipt is not None:
        requirement["approval_receipt"] = receipt
    out = build_cross_index(
        boq={"items": [{"name": "氧气瓶"}], "stats": {}},
        sections=[{"title": chapter, "content": "氧气瓶风险→控制→验证。"}],
        boq_focus={
            "must_cover_keywords": ["氧气瓶"],
            "drawing_requirements": {"氧气瓶": requirement},
        },
        drawing_index={},
        quality_checks=_closed_quality(chapter, "氧气瓶"),
        project_id="p1",
    )

    row = out["focus_items"][0]
    assert row["drawing_requirement"]["status"] == "required"
    assert row["drawing_requirement"]["reason"] == expected_reason
    assert row["closure"]["ok"] is False


def test_cross_project_drawing_index_is_rejected():
    chapter = "钢梁安装施工工艺"
    out = build_cross_index(
        boq={"items": [{"name": "钢梁"}], "stats": {}},
        sections=[{"title": chapter, "content": "钢梁风险→控制→验证。"}],
        boq_focus={"must_cover_keywords": ["钢梁"]},
        drawing_index=_drawing_index(
            filename="钢梁图.pdf",
            sha8="55555555",
            page=1,
            offset=10,
            text="钢梁节点",
            chapter=chapter,
            project_id="other-project",
        ),
        quality_checks=_closed_quality(chapter, "钢梁"),
        project_id="current-project",
    )

    row = out["focus_items"][0]
    assert row["drawing_locator"] is None
    assert row["drawing_validation"]["reason"] == "drawing_project_identity_mismatch"
