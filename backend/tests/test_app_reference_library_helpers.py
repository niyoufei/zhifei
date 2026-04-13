from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {
        "_safe_local_preview_path",
        "_build_case_library_request_options",
        "_build_image_library_request_options",
        "_normalize_reference_library_summary_ui",
        "_reference_library_summary_has_content",
        "_aggregate_reference_library_summary_ui",
        "_merge_reference_library_summary_ui",
        "_resolve_result_reference_library_summaries",
        "_decode_result_json_ui",
        "_variant_sections_from_result_ui",
        "_chapter_case_reference_summary_ui",
        "_chapter_image_reference_summary_ui",
        "_chapter_reference_rows_ui",
        "_aggregate_reference_library_summary_from_chapter_rows_ui",
        "_chapter_reference_overview_ui",
        "_variant_reference_library_summaries_ui",
        "_submission_file_refs",
        "_build_submission_signature",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "hashlib": hashlib,
        "json": json,
        "st": SimpleNamespace(session_state={}),
    }
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_case_library_request_options_noop_when_disabled_even_if_selection_present():
    helpers = _load_helpers()
    helpers.st.session_state = {
        "case_library_enabled": False,
        "case_library_selected_ids": ["case-1", "case-2"],
        "case_library_top_k": 7,
    }

    assert helpers._build_case_library_request_options() is None


def test_case_library_request_options_enabled_clamps_top_k_and_trims_ids():
    helpers = _load_helpers()
    helpers.st.session_state = {
        "case_library_enabled": True,
        "case_library_selected_ids": [" case-1 ", "", "case-2"],
        "case_library_top_k": 99,
    }

    out = helpers._build_case_library_request_options()

    assert out == {
        "enabled": True,
        "selected_case_ids": ["case-1", "case-2"],
        "top_k": 8,
    }


def test_image_library_request_options_noop_when_disabled_even_if_selection_present():
    helpers = _load_helpers()
    helpers.st.session_state = {
        "image_library_enabled": False,
        "image_library_selected_ids": ["image-1"],
        "image_library_top_k": 6,
    }

    assert helpers._build_image_library_request_options() is None


def test_image_library_request_options_enabled_clamps_top_k_and_trims_ids():
    helpers = _load_helpers()
    helpers.st.session_state = {
        "image_library_enabled": True,
        "image_library_selected_ids": [" image-1 ", "", "image-2"],
        "image_library_top_k": 0,
    }

    out = helpers._build_image_library_request_options()

    assert out == {
        "enabled": True,
        "selected_image_ids": ["image-1", "image-2"],
        "top_k": 3,
    }


def test_submission_signature_changes_when_reference_libraries_enabled():
    helpers = _load_helpers()

    base = helpers._build_submission_signature(
        topic="施工组织设计",
        project_id="P-1",
        project_type="房建",
        generation_mode="standard_auto",
        selected_templates=["A"],
        total_pages_target=120,
        case_library=None,
        image_library=None,
        tender_files=None,
        boq_files=None,
        drawing_files=None,
        site_photo_files=None,
    )
    with_case = helpers._build_submission_signature(
        topic="施工组织设计",
        project_id="P-1",
        project_type="房建",
        generation_mode="standard_auto",
        selected_templates=["A"],
        total_pages_target=120,
        case_library={"enabled": True, "selected_case_ids": ["case-1"], "top_k": 3},
        image_library=None,
        tender_files=None,
        boq_files=None,
        drawing_files=None,
        site_photo_files=None,
    )
    with_image = helpers._build_submission_signature(
        topic="施工组织设计",
        project_id="P-1",
        project_type="房建",
        generation_mode="standard_auto",
        selected_templates=["A"],
        total_pages_target=120,
        case_library=None,
        image_library={"enabled": True, "selected_image_ids": ["image-1"], "top_k": 2},
        tender_files=None,
        boq_files=None,
        drawing_files=None,
        site_photo_files=None,
    )

    assert base != with_case
    assert base != with_image
    assert with_case != with_image


def test_submission_signature_stays_stable_when_disabled_reference_library_selection_is_ignored():
    helpers = _load_helpers()
    helpers.st.session_state = {
        "case_library_enabled": False,
        "case_library_selected_ids": ["case-9"],
        "case_library_top_k": 5,
        "image_library_enabled": False,
        "image_library_selected_ids": ["image-9"],
        "image_library_top_k": 5,
    }

    case_options = helpers._build_case_library_request_options()
    image_options = helpers._build_image_library_request_options()

    base = helpers._build_submission_signature(
        topic="施工组织设计",
        project_id="P-2",
        project_type="房建",
        generation_mode="standard_auto",
        selected_templates=["A", "B"],
        total_pages_target=180,
        case_library=None,
        image_library=None,
        tender_files=None,
        boq_files=None,
        drawing_files=None,
        site_photo_files=None,
    )
    ignored = helpers._build_submission_signature(
        topic="施工组织设计",
        project_id="P-2",
        project_type="房建",
        generation_mode="standard_auto",
        selected_templates=["A", "B"],
        total_pages_target=180,
        case_library=case_options,
        image_library=image_options,
        tender_files=None,
        boq_files=None,
        drawing_files=None,
        site_photo_files=None,
    )

    assert case_options is None
    assert image_options is None
    assert ignored == base


def test_normalize_reference_library_summary_ui_promotes_singular_fields():
    helpers = _load_helpers()

    out = helpers._normalize_reference_library_summary_ui(
        {
            "enabled": True,
            "selected_case_ids": [" case-1 ", "", "case-2"],
            "matched_project_type": "房建",
            "matched_chapter": "施工部署",
            "match_reason": "project_type_chapter_tags",
            "warning_list": [" no_case_match ", ""],
            "hit_count": 2,
        },
        id_key="selected_case_ids",
    )

    assert out == {
        "enabled": True,
        "selected_case_ids": ["case-1", "case-2"],
        "matched_project_type": "房建",
        "matched_chapters": ["施工部署"],
        "matched_chapter": "施工部署",
        "match_reasons": ["project_type_chapter_tags"],
        "match_reason": "project_type_chapter_tags",
        "hit_count": 2,
        "warning_list": ["no_case_match"],
        "variant_ids": [],
    }


def test_aggregate_reference_library_summary_ui_collects_variant_hits():
    helpers = _load_helpers()

    out = helpers._aggregate_reference_library_summary_ui(
        {
            1: {
                "variant_index": 1,
                "case_library_summary": {
                    "enabled": True,
                    "selected_case_ids": ["case-1"],
                    "matched_project_type": "房建",
                    "matched_chapter": "工程概况",
                    "match_reason": "selected_case_ids",
                    "hit_count": 1,
                },
            },
            "v3": {
                "variant_id": "v3",
                "case_library_summary": {
                    "enabled": True,
                    "selected_case_ids": ["case-2"],
                    "matched_project_type": "房建",
                    "matched_chapters": ["施工部署"],
                    "match_reasons": ["project_type_chapter_tags"],
                    "warning_list": ["case_copy_risk"],
                    "hit_count": 1,
                },
            },
        },
        summary_key="case_library_summary",
        id_key="selected_case_ids",
    )

    assert out == {
        "enabled": True,
        "selected_case_ids": ["case-1", "case-2"],
        "matched_project_type": "房建",
        "matched_chapters": ["工程概况", "施工部署"],
        "matched_chapter": "工程概况",
        "match_reasons": ["selected_case_ids", "project_type_chapter_tags"],
        "match_reason": "selected_case_ids",
        "hit_count": 2,
        "warning_list": ["case_copy_risk"],
        "variant_ids": ["v1", "v3"],
    }


def test_resolve_result_reference_library_summaries_falls_back_to_runtime_map():
    helpers = _load_helpers()

    resolved = helpers._resolve_result_reference_library_summaries(
        {
            "runtime_by_variant": {
                2: {
                    "variant_index": 2,
                    "case_library_summary": {
                        "enabled": True,
                        "selected_case_ids": ["case-9"],
                        "matched_project_type": "房建",
                        "matched_chapter": "主要施工方法",
                        "match_reason": "project_type_chapter_tags",
                        "hit_count": 1,
                    },
                    "image_library_summary": {
                        "enabled": True,
                        "selected_image_ids": ["image-2"],
                        "matched_project_type": "房建",
                        "matched_chapter": "施工总平面布置",
                        "match_reason": "project_type_chapter_tags",
                        "hit_count": 1,
                    },
                }
            }
        }
    )

    assert resolved["case_library_summary"]["selected_case_ids"] == ["case-9"]
    assert resolved["case_library_summary"]["variant_ids"] == ["v2"]
    assert resolved["case_library_summary"]["matched_chapters"] == ["主要施工方法"]
    assert resolved["image_library_summary"]["selected_image_ids"] == ["image-2"]
    assert resolved["image_library_summary"]["variant_ids"] == ["v2"]
    assert resolved["image_library_summary"]["match_reasons"] == ["project_type_chapter_tags"]


def test_resolve_result_reference_library_summaries_preserves_top_level_and_merges_warnings():
    helpers = _load_helpers()

    resolved = helpers._resolve_result_reference_library_summaries(
        {
            "case_library_summary": {
                "enabled": True,
                "selected_case_ids": ["case-top"],
                "matched_project_type": "房建",
                "matched_chapter": "施工部署",
                "match_reason": "selected_case_ids",
                "hit_count": 1,
            },
            "runtime_by_variant": {
                1: {
                    "variant_index": 1,
                    "case_library_summary": {
                        "enabled": True,
                        "selected_case_ids": ["case-runtime"],
                        "warning_list": ["case_copy_risk"],
                        "hit_count": 1,
                    },
                }
            },
        }
    )

    assert resolved["case_library_summary"]["selected_case_ids"] == ["case-top"]
    assert resolved["case_library_summary"]["variant_ids"] == ["v1"]
    assert resolved["case_library_summary"]["warning_list"] == ["case_copy_risk"]


def test_variant_sections_from_result_ui_reads_result_json_bytes():
    helpers = _load_helpers()

    payload = {
        "variants": [
            {
                "variant_id": 1,
                "sections": [{"title": "工程概况", "content": "A"}],
            },
            {
                "variant_id": 2,
                "sections": [{"title": "施工部署", "content": "B"}],
            },
        ]
    }

    sections = helpers._variant_sections_from_result_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        2,
    )

    assert sections == [{"title": "施工部署", "content": "B"}]


def test_chapter_reference_pack_helpers_extract_titles_hints_and_preview(tmp_path):
    helpers = _load_helpers()
    preview_path = tmp_path / "image-preview.png"
    preview_path.write_bytes(b"png")

    case_summary = helpers._chapter_case_reference_summary_ui(
        {
            "enabled": True,
            "selected_case_ids": ["case-1"],
            "matched_project_type": "房建",
            "matched_chapter": "施工部署",
            "match_reason": "selected_case_ids",
            "style_hints": ["案例提示：结构清晰"],
            "structure_hints": ["适用章节：施工部署"],
            "non_fact_reference_notice": "案例库仅用于参考",
            "hits": [{"case_id": "case-1", "title": "养老院改造样板"}],
        }
    )
    image_summary = helpers._chapter_image_reference_summary_ui(
        {
            "enabled": True,
            "selected_image_ids": ["image-1"],
            "matched_project_type": "房建",
            "matched_chapter": "施工总平面布置",
            "match_reason": "selected_image_ids",
            "caption_hint": "现场总平面",
            "insertion_hint": "优先在章节后插图",
            "images": [{"image_id": "image-1", "title": "总平图", "source_path": str(preview_path)}],
        }
    )

    assert case_summary["reference_titles"] == ["养老院改造样板"]
    assert case_summary["style_hints"] == ["案例提示：结构清晰"]
    assert case_summary["non_fact_reference_notice"] == "案例库仅用于参考"
    assert image_summary["image_titles"] == ["总平图"]
    assert image_summary["preview_paths"] == [str(preview_path)]
    assert image_summary["first_preview_path"] == str(preview_path)
    assert image_summary["caption_hint"] == "现场总平面"
    assert image_summary["insertion_hint"] == "优先在章节后插图"


def test_chapter_reference_rows_ui_filters_to_sections_with_reference_hits():
    helpers = _load_helpers()

    payload = {
        "variants": [
            {
                "variant_id": 1,
                "sections": [
                    {
                        "title": "工程概况",
                        "content": "A",
                    },
                    {
                        "title": "施工部署",
                        "content": "B",
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
                            "caption_hint": "现场布置图",
                            "images": [{"image_id": "image-1", "caption": "布置图"}],
                        },
                    },
                ],
            }
        ]
    }

    rows = helpers._chapter_reference_rows_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        1,
    )

    assert rows == [
        {
            "title": "施工部署",
            "case_library": {
                "enabled": True,
                "selected_case_ids": ["case-1"],
                "matched_project_type": "房建",
                "matched_chapters": ["施工部署"],
                "matched_chapter": "施工部署",
                "match_reasons": ["selected_case_ids"],
                "match_reason": "selected_case_ids",
                "hit_count": 1,
                "warning_list": [],
                "variant_ids": [],
                "reference_titles": ["养老院改造样板"],
                "style_hints": [],
                "structure_hints": [],
                "non_fact_reference_notice": "",
            },
            "image_library": {
                "enabled": True,
                "selected_image_ids": ["image-1"],
                "matched_project_type": "房建",
                "matched_chapters": ["施工部署"],
                "matched_chapter": "施工部署",
                "match_reasons": ["project_type_chapter_tags"],
                "match_reason": "project_type_chapter_tags",
                "hit_count": 1,
                "warning_list": [],
                "variant_ids": [],
                "image_titles": ["布置图"],
                "preview_paths": [],
                "first_preview_path": "",
                "caption_hint": "现场布置图",
                "insertion_hint": "",
            },
        }
    ]


def test_chapter_reference_overview_ui_counts_case_image_warning_and_preview_chapters():
    helpers = _load_helpers()

    out = helpers._chapter_reference_overview_ui(
        [
            {
                "title": "施工部署",
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": ["case-1"],
                    "warning_list": [],
                },
                "image_library": {
                    "enabled": True,
                    "selected_image_ids": ["image-1"],
                    "warning_list": ["no_image_match"],
                    "first_preview_path": "/tmp/preview-1.png",
                },
            },
            {
                "title": "安全文明",
                "case_library": {
                    "enabled": False,
                    "selected_case_ids": [],
                    "warning_list": ["case_copy_risk"],
                },
                "image_library": {
                    "enabled": True,
                    "selected_image_ids": ["image-2"],
                    "warning_list": [],
                    "first_preview_path": "",
                },
            },
        ]
    )

    assert out == {
        "chapter_count": 2,
        "case_chapter_count": 1,
        "image_chapter_count": 2,
        "warning_chapter_count": 2,
        "preview_chapter_count": 1,
    }


def test_aggregate_reference_library_summary_from_chapter_rows_ui_merges_ids_reasons_and_warnings():
    helpers = _load_helpers()

    out = helpers._aggregate_reference_library_summary_from_chapter_rows_ui(
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
                    "warning_list": [],
                }
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
                }
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
        "variant_ids": [],
    }


def test_variant_reference_library_summaries_ui_falls_back_to_chapter_rows_when_runtime_missing():
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
                            "caption_hint": "现场布置图",
                            "images": [{"image_id": "image-1", "caption": "布置图"}],
                        },
                    }
                ],
            }
        ]
    }

    out = helpers._variant_reference_library_summaries_ui(
        {"result_json": json.dumps(payload, ensure_ascii=False).encode("utf-8")},
        1,
        {},
    )

    assert out["case_library_summary"]["selected_case_ids"] == ["case-1"]
    assert out["case_library_summary"]["matched_chapters"] == ["施工部署"]
    assert out["image_library_summary"]["selected_image_ids"] == ["image-1"]
    assert out["image_library_summary"]["matched_chapters"] == ["施工部署"]
    assert len(out["chapter_rows"]) == 1
