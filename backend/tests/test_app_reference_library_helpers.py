from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {
        "_normalize_reference_summary_ui",
        "_reference_summary_has_content",
        "_normalize_reference_text_list_ui",
        "_reference_top_k_state",
        "_build_case_library_request_options",
        "_build_image_library_request_options",
        "_decode_result_json_ui",
        "_variant_sections_from_result_ui",
        "_chapter_case_reference_summary_ui",
        "_chapter_image_reference_summary_ui",
        "_chapter_reference_rows_ui",
        "_aggregate_reference_summary_from_chapter_rows_ui",
        "_merge_reference_summary_ui",
        "_variant_reference_summaries_ui",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {
        "Any": Any,
        "json": json,
        "re": re,
        "st": SimpleNamespace(session_state={}),
    }
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_reference_library_request_options_default_to_disabled():
    helpers = _load_helpers()
    helpers.st.session_state.clear()

    assert helpers._build_case_library_request_options() == {
        "enabled": False,
        "selected_case_ids": [],
        "top_k": 3,
    }
    assert helpers._build_image_library_request_options() == {
        "enabled": False,
        "selected_image_ids": [],
        "top_k": 3,
    }


def test_reference_library_request_options_normalize_selected_ids_and_top_k():
    helpers = _load_helpers()
    helpers.st.session_state.clear()
    helpers.st.session_state.update(
        {
            "case_library_enabled": True,
            "case_library_selected_ids": ["case-1", "case-1", " case-2 "],
            "case_library_top_k": 99,
            "image_library_enabled": True,
            "image_library_selected_ids": "image-1, image-2，image-1",
            "image_library_top_k": 0,
        }
    )

    assert helpers._build_case_library_request_options() == {
        "enabled": True,
        "selected_case_ids": ["case-1", "case-2"],
        "top_k": 8,
    }
    assert helpers._build_image_library_request_options() == {
        "enabled": True,
        "selected_image_ids": ["image-1", "image-2"],
        "top_k": 1,
    }


def test_variant_sections_from_result_ui_reads_result_json_bytes():
    helpers = _load_helpers()

    payload = {
        "variants": [
            {"variant_id": 1, "sections": [{"title": "工程概况", "content": "A"}]},
            {"variant_id": 2, "sections": [{"title": "施工部署", "content": "B"}]},
        ]
    }

    sections = helpers._variant_sections_from_result_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        2,
    )

    assert sections == [{"title": "施工部署", "content": "B"}]


def test_aggregate_reference_summary_from_chapter_rows_ui_merges_rows():
    helpers = _load_helpers()

    out = helpers._aggregate_reference_summary_from_chapter_rows_ui(
        [
            {
                "title": "施工部署",
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": ["case-1"],
                    "matched_project_type": "房建",
                    "matched_chapters": ["施工部署"],
                    "match_reasons": ["selected_case_ids"],
                    "hit_count": 1,
                },
            },
            {
                "title": "安全文明",
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": ["case-2"],
                    "matched_project_type": "房建",
                    "match_reason": "project_type_chapter_tags",
                    "hit_count": 1,
                    "warning_list": ["case_copy_risk"],
                },
            },
        ],
        summary_key="case_library",
        id_key="selected_case_ids",
    )

    assert out == {
        "enabled": True,
        "selected_case_ids": ["case-1", "case-2"],
        "matched_project_type": "房建",
        "matched_chapters": ["施工部署", "安全文明"],
        "matched_chapter": "施工部署",
        "match_reasons": ["selected_case_ids", "project_type_chapter_tags"],
        "match_reason": "selected_case_ids",
        "hit_count": 2,
        "warning_list": ["case_copy_risk"],
    }


def test_variant_reference_summaries_ui_falls_back_to_section_packs_when_runtime_missing():
    helpers = _load_helpers()

    payload = {
        "variants": [
            {
                "variant_id": 1,
                "sections": [
                    {
                        "title": "施工部署",
                        "case_reference_pack": {
                            "enabled": True,
                            "selected_case_ids": ["case-1"],
                            "matched_project_type": "房建",
                            "matched_chapter": "施工部署",
                            "match_reason": "selected_case_ids",
                            "hits": [{"case_id": "case-1", "title": "养老院改造样板"}],
                        },
                        "image_selection_pack": {
                            "enabled": True,
                            "selected_image_ids": ["image-1"],
                            "matched_project_type": "房建",
                            "matched_chapter": "施工部署",
                            "match_reason": "project_type_chapter_tags",
                            "images": [{"image_id": "image-1", "caption": "布置图"}],
                        },
                    }
                ],
            }
        ]
    }

    out = helpers._variant_reference_summaries_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        1,
        {},
    )

    assert out["case_library_summary"] == {
        "enabled": True,
        "selected_case_ids": ["case-1"],
        "matched_project_type": "房建",
        "matched_chapters": ["施工部署"],
        "matched_chapter": "施工部署",
        "match_reasons": ["selected_case_ids"],
        "match_reason": "selected_case_ids",
        "hit_count": 1,
        "warning_list": [],
    }
    assert out["image_library_summary"] == {
        "enabled": True,
        "selected_image_ids": ["image-1"],
        "matched_project_type": "房建",
        "matched_chapters": ["施工部署"],
        "matched_chapter": "施工部署",
        "match_reasons": ["project_type_chapter_tags"],
        "match_reason": "project_type_chapter_tags",
        "hit_count": 1,
        "warning_list": [],
    }


def test_variant_reference_summaries_ui_keeps_runtime_summary_and_merges_warnings():
    helpers = _load_helpers()

    payload = {
        "variants": [
            {
                "variant_id": 1,
                "sections": [
                    {
                        "title": "施工部署",
                        "case_reference_pack": {
                            "enabled": True,
                            "selected_case_ids": ["case-fallback"],
                            "matched_project_type": "房建",
                            "matched_chapter": "施工部署",
                            "match_reason": "project_type_chapter_tags",
                            "hits": [{"case_id": "case-fallback"}],
                            "warning_list": ["case_copy_risk"],
                        }
                    }
                ],
            }
        ]
    }

    out = helpers._variant_reference_summaries_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        1,
        {
            "case_library_summary": {
                "enabled": True,
                "selected_case_ids": ["case-top"],
                "matched_project_type": "房建",
                "matched_chapter": "施工部署",
                "match_reason": "selected_case_ids",
                "hit_count": 1,
            }
        },
    )

    assert out["case_library_summary"] == {
        "enabled": True,
        "selected_case_ids": ["case-top"],
        "matched_project_type": "房建",
        "matched_chapters": ["施工部署"],
        "matched_chapter": "施工部署",
        "match_reasons": ["selected_case_ids"],
        "match_reason": "selected_case_ids",
        "hit_count": 1,
        "warning_list": ["case_copy_risk"],
    }
