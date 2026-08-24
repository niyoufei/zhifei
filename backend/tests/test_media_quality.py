from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document
from PIL import Image

from backend.zhifei_autoplan.exporter import export_autoplan_docx
from backend.zhifei_autoplan.media_quality import (
    build_media_delivery_manifest,
    media_matches_chapter,
    validate_media_collection,
    verify_docx_media_hashes,
)


pytestmark = pytest.mark.usefixtures("allow_legacy_export_contract")


def _formal_image(path: Path, *, noise: float = 32.0) -> Path:
    Image.effect_noise((960, 640), noise).convert("RGB").save(path)
    return path


def test_collection_rejects_low_resolution_and_deduplicates(tmp_path: Path):
    low = tmp_path / "low.png"
    Image.new("RGB", (120, 80), color="white").save(low)
    first = _formal_image(tmp_path / "first.png")
    duplicate = tmp_path / "duplicate.png"
    duplicate.write_bytes(first.read_bytes())

    result = validate_media_collection(
        [
            {"path": str(low), "caption": "低质量图"},
            {"path": str(first), "caption": "现场图", "source_kind": "site_photo"},
            {"path": str(duplicate), "caption": "重复现场图"},
        ]
    )

    assert result["status"] == "pass"
    assert result["accepted_count"] == 1
    reasons = {reason for row in result["rejected"] for reason in row["reason"]}
    assert "image_resolution_below_formal_minimum" in reasons
    assert "exact_duplicate_image" in reasons


def test_required_rejected_image_blocks_export(tmp_path: Path):
    image_path = _formal_image(tmp_path / "required-ai.png")

    with pytest.raises(RuntimeError) as exc_info:
        export_autoplan_docx(
            {
                "topic": "项目施工组织设计",
                "sections": [{"title": "第一章 工程概况", "content": "项目条件已复核。"}],
                "media": [
                    {
                        "path": str(image_path),
                        "caption": "AI生成总平面图",
                        "source_kind": "external_ai",
                        "required": True,
                    }
                ],
            },
            str(tmp_path / "blocked.docx"),
        )

    payload = json.loads(str(exc_info.value))
    assert payload["status"] == "blocked"
    assert payload["issues"][0]["code"] == "REQUIRED_FIGURE_REJECTED"


def test_chapter_binding_and_docx_media_verification(tmp_path: Path):
    image_path = _formal_image(tmp_path / "chapter.png")
    item = {
        "path": str(image_path),
        "caption": "临时用电三级配电控制图",
        "chapter_scope": ["施工现场临时用电"],
    }
    assert media_matches_chapter(item, "第六章 施工现场临时用电")
    assert not media_matches_chapter(item, "第五章 施工进度计划")

    docx_path = tmp_path / "embedded.docx"
    document = Document()
    document.add_picture(str(image_path))
    document.save(docx_path)
    expected = validate_media_collection([item])["accepted"][0]["asset_sha256"]
    verification = verify_docx_media_hashes(docx_path, [expected])
    assert verification["ok"] is True
    assert verification["missing_hashes"] == []


def test_figure_delivery_manifest_requires_complete_traceability() -> None:
    digest = "a" * 64
    report = build_media_delivery_manifest(
        source_media={"accepted_count": 1, "rejected_count": 0},
        insertions=[
            {
                "figure_number": 1,
                "caption": "施工总平面布置图",
                "chapter_title": "施工总体部署",
                "source_kind": "drawing",
                "source_ref": "总平面图.pdf",
                "asset_sha256": digest,
            }
        ],
        insertion_failures=[],
        embedded_media_verification={"ok": True, "missing_hashes": []},
    )

    assert report["schema_version"] == "docx_figure_delivery.v2"
    assert report["status"] == "pass"
    assert report["delivery_allowed"] is True
    assert len(report["decision_digest"]) == 64
    assert report["decision_digest"] == build_media_delivery_manifest(
        source_media={"accepted_count": 1, "rejected_count": 0},
        insertions=report["insertions"],
        insertion_failures=[],
        embedded_media_verification={"ok": True, "missing_hashes": []},
    )["decision_digest"]


def test_figure_delivery_manifest_blocks_missing_source_reference() -> None:
    report = build_media_delivery_manifest(
        source_media={"accepted_count": 1, "rejected_count": 0},
        insertions=[
            {
                "figure_number": 1,
                "caption": "临时用电系统图",
                "chapter_title": "临时用电",
                "source_kind": "deterministic_generated",
                "source_ref": "",
                "asset_sha256": "b" * 64,
            }
        ],
        insertion_failures=[],
        embedded_media_verification={"ok": True, "missing_hashes": []},
    )

    assert report["status"] == "blocked"
    assert report["delivery_allowed"] is False
    issue = next(item for item in report["issues"] if item["code"] == "FIGURE_TRACEABILITY_INCOMPLETE")
    assert issue["missing_fields"] == ["source_ref"]


def test_figure_delivery_manifest_distinguishes_required_and_optional_failures() -> None:
    report = build_media_delivery_manifest(
        source_media={"accepted_count": 0, "rejected_count": 2},
        insertions=[],
        insertion_failures=[
            {
                "caption": "关键节点图",
                "chapter_title": "关键施工技术",
                "reason": ["image_file_missing"],
                "required": True,
            },
            {
                "caption": "装饰图片",
                "chapter_title": "附录",
                "reason": ["image_may_be_blurred"],
                "required": False,
            },
        ],
        embedded_media_verification={"ok": True, "missing_hashes": []},
    )

    assert report["delivery_allowed"] is False
    assert {item["code"] for item in report["issues"]} == {"REQUIRED_FIGURE_INSERTION_FAILED"}
    assert {item["code"] for item in report["warnings"]} == {"OPTIONAL_FIGURE_INSERTION_SKIPPED"}


def test_export_writes_verified_figure_manifest(tmp_path: Path) -> None:
    image_path = _formal_image(tmp_path / "project-evidence.png")
    output_path = tmp_path / "formal.docx"

    export_autoplan_docx(
        {
            "topic": "道路工程施工组织设计",
            "style": {
                "chart_policy": {
                    "enabled": True,
                    "position": "chapter",
                    "every_n_chapters": 1,
                }
            },
            "sections": [
                {
                    "title": "第一章 施工总体部署",
                    "content": "施工现场总平面布置已结合场地条件复核。",
                }
            ],
            "media": [
                {
                    "path": str(image_path),
                    "caption": "施工现场总平面布置图",
                    "source_kind": "drawing",
                    "source_filename": "施工总平面图.pdf",
                    "chapter_scope": ["施工总体部署"],
                    "required": True,
                }
            ],
        },
        str(output_path),
    )

    manifest = json.loads(output_path.with_suffix(".figure_manifest.json").read_text(encoding="utf-8"))
    assert manifest["delivery_allowed"] is True
    assert manifest["insertions"][0]["source_ref"] == "施工总平面图.pdf"
    assert manifest["insertions"][0]["chapter_title"] == "第一章 施工总体部署"
    assert manifest["embedded_media_verification"]["ok"] is True
