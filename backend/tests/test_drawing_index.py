from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.zhifei_autoplan import evidence
from backend.zhifei_autoplan.drawing_index import build_drawing_index


def _write_audit(tmp_path: Path, rows: list[dict]) -> None:
    audit_path = tmp_path / "backend/data/audit/ingest.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    evidence._load_audit_records.cache_clear()
    evidence._load_extract_text.cache_clear()


def _record(
    tmp_path: Path,
    *,
    filename: str,
    sha: str,
    text: str,
    **extra,
) -> dict:
    workspace = tmp_path / "backend/data"
    uploads = workspace / "uploads"
    extracts = workspace / "extracts"
    uploads.mkdir(parents=True, exist_ok=True)
    extracts.mkdir(parents=True, exist_ok=True)
    source_bytes = f"drawing-source:{sha}:{filename}".encode()
    digest = hashlib.sha256(source_bytes).hexdigest()
    source = uploads / f"{digest}_{filename}"
    source.write_bytes(source_bytes)
    extract_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    extract = extracts / f"{digest}_{extract_text_sha256}.txt"
    extract.write_text(text, encoding="utf-8")
    page_count = int(extra.get("pages") or 1)
    if "\f" in text:
        page_texts = text.split("\f")
    elif page_count == 1:
        page_texts = [text]
    else:
        page_texts = [text, *([""] * (page_count - 1))]
    page_statuses = ["text" if page_text.strip() else "blank" for page_text in page_texts]
    return {
        "project_id": "p1",
        "workspace_dir": str(workspace),
        "filename": filename,
        "saved_as": str(source),
        "sha256": digest,
        "file_id": digest,
        "pages": 1,
        "doc_type": "pdf",
        "tags": [],
        "source_hint": "drawing_standard",
        "ocr_cache_policy": "drawing_full_page",
        "ocr_page_proof_version": "ocr-page-proof-v1",
        "ocr_page_mapping": "source_page_all",
        "ocr_source_pages": page_count,
        "ocr_error": None,
        "ocr_pages": page_count,
        "ocr_page_text_count": page_count,
        "ocr_page_statuses": page_statuses,
        "ocr_blank_pages": [
            index
            for index, status in enumerate(page_statuses, start=1)
            if status == "blank"
        ],
        "ocr_page_image_sha256": [
            hashlib.sha256(f"image-{index}".encode()).hexdigest()
            for index in range(page_count)
        ],
        "ocr_page_text_sha256": [
            hashlib.sha256(page_text.encode()).hexdigest()
            for page_text in page_texts
        ],
        "ocr_extract_page_sha256": [
            hashlib.sha256(page_text.encode()).hexdigest()
            for page_text in page_texts
        ],
        "extract_saved_as": str(extract),
        "extract_text_sha256": extract_text_sha256,
        **extra,
    }


def test_drawing_index_deduplicates_same_content_and_keeps_distinct_revisions(
    monkeypatch, tmp_path: Path
) -> None:
    same_sha = "a" * 64
    rows = [
        _record(tmp_path, filename="1 挤奶厅.pdf", sha=same_sha, text="旧记录"),
        _record(tmp_path, filename="1 挤奶厅.pdf", sha=same_sha, text="新记录"),
        _record(tmp_path, filename="1 挤奶厅.pdf", sha="b" * 64, text="修订版"),
    ]
    _write_audit(
        tmp_path,
        rows,
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", [], project_id="p1")

    assert len(result["drawings"]) == 2
    assert {row["sha256"] for row in result["drawings"]} == {
        rows[0]["sha256"],
        rows[2]["sha256"],
    }


def test_latest_disabled_record_prevents_older_content_from_resurrecting(
    monkeypatch, tmp_path: Path
) -> None:
    sha = "c" * 64
    _write_audit(
        tmp_path,
        [
            _record(tmp_path, filename="2 地磅.pdf", sha=sha, text="旧记录"),
            _record(
                tmp_path,
                filename="2 地磅.pdf",
                sha=sha,
                text="新记录",
                enabled=False,
            ),
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", [], project_id="p1")

    assert result["drawings"] == []


def test_topic_only_hit_does_not_create_claim_grade_chapter_binding(
    monkeypatch, tmp_path: Path
) -> None:
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="3 围墙.pdf",
                sha="d" * 64,
                text="示例项目总图资料，不含章节特异内容。",
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
    )

    assert len(result["drawings"]) == 1
    assert result["chapter_bindings"] == []
    assert result["chapter_binding_status"] == "no_chapter_specific_evidence"


def test_chapter_specific_extract_binding_preserves_drawing_identity(
    monkeypatch, tmp_path: Path
) -> None:
    sha = "e" * 64
    record = _record(
        tmp_path,
        filename="钢筋详图.pdf",
        sha=sha,
        text="钢筋绑扎施工工艺：构件位置与节点做法。",
    )
    _write_audit(
        tmp_path,
        [record],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
    )

    binding = result["chapter_bindings"][0]
    drawing = result["drawings"][0]
    assert binding["filename"] == "钢筋详图.pdf"
    assert binding["sha256"] == record["sha256"]
    assert f"#p1_{record['sha256']}@" in binding["locator"]
    assert binding["binding_basis"] == "chapter_specific_extract_hit"
    assert binding["matched_terms"] == ["钢筋绑扎"]
    assert binding["offset"] == binding["match_start"]
    assert binding["page_text_sha256"] == drawing["page_anchors"][0]["text_sha256"]
    assert binding["page_summary"] == drawing["page_anchors"][0]["snippet"]
    assert binding["match_window"]["text_sha256"]
    assert drawing["text_status"] == "indexed"
    assert drawing["page_boundary_status"] == "reliable_declared_single_page"
    assert drawing["page_anchors"][0]["page"] == 1
    assert drawing["page_anchors"][0]["text_sha256"]
    extract_path = Path(drawing["extract_saved_as"])
    extract_bytes = extract_path.read_bytes()
    assert drawing["extract_bytes_sha256"] == hashlib.sha256(extract_bytes).hexdigest()
    assert drawing["extract_text_sha256"] == hashlib.sha256(
        extract_bytes.decode("utf-8", errors="ignore").encode("utf-8")
    ).hexdigest()


def test_generic_drawing_phrase_does_not_create_binding(monkeypatch, tmp_path: Path) -> None:
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="总图.pdf",
                sha="f" * 64,
                text="图纸施工方案详见图纸说明。",
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", ["图纸施工方案"], project_id="p1")

    assert result["chapter_bindings"] == []
    assert result["chapter_binding_status"] == "no_chapter_specific_evidence"


def test_empty_extract_is_marked_missing_ocr_and_never_bound(monkeypatch, tmp_path: Path) -> None:
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="扫描钢梁图.pdf",
                sha="1" * 64,
                text="",
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", ["钢梁安装施工工艺"], project_id="p1")

    assert result["drawings"][0]["text_status"] == "missing_text_or_ocr"
    assert result["drawings"][0]["page_anchors"] == []
    assert result["chapter_bindings"] == []
    assert result["missing_text_or_ocr_count"] == 1
    assert result["chapter_binding_status"] == "drawing_text_or_ocr_missing"


def test_multi_page_extract_without_boundaries_is_locator_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="多页钢梁图.pdf",
                sha="2" * 64,
                text="钢梁安装构件位置与节点做法。",
                pages=3,
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", ["钢梁安装施工工艺"], project_id="p1")

    drawing = result["drawings"][0]
    assert drawing["text_status"] == "locator_unavailable"
    assert drawing["page_boundary_status"] == "unreliable_missing_page_boundaries"
    assert drawing["page_anchors"] == []
    assert result["locator_unavailable_count"] == 1
    assert result["chapter_bindings"] == []
    assert result["chapter_binding_status"] == "drawing_locator_unavailable"


def test_multi_page_form_feed_preserves_real_page_and_offset(monkeypatch, tmp_path: Path) -> None:
    sha = "3" * 64
    first_page = "总说明与目录。"
    second_page = "钢梁安装构件位置与节点做法。"
    record = _record(
        tmp_path,
        filename="钢梁图.pdf",
        sha=sha,
        text=f"{first_page}\f{second_page}",
        pages=2,
    )
    _write_audit(
        tmp_path,
        [record],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", ["钢梁安装施工工艺"], project_id="p1")

    binding = result["chapter_bindings"][0]
    assert binding["page"] == 2
    assert binding["offset"] == len(first_page) + 1
    assert binding["page_boundary_status"] == "reliable_form_feed"
    assert binding["locator"] == (
        f"钢梁图.pdf#p2_{record['sha256']}@{len(first_page) + 1}"
    )


def test_merged_native_and_ocr_pages_validate_against_extract_page_proof(
    monkeypatch,
    tmp_path: Path,
) -> None:
    sha = "4" * 64
    first_page = "总说明。\n\nOCR目录。\n\n"
    second_page = "\n\n钢梁安装构件位置。\n\nOCR节点做法。"
    merged = f"{first_page}\f{second_page}"
    record = _record(
        tmp_path,
        filename="钢梁合并图.pdf",
        sha=sha,
        text=merged,
        pages=2,
        ocr_page_statuses=["text", "text"],
        ocr_page_text_sha256=[
            hashlib.sha256("OCR目录。".encode()).hexdigest(),
            hashlib.sha256("OCR节点做法。".encode()).hexdigest(),
        ],
    )
    _write_audit(tmp_path, [record])
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢梁安装施工工艺"],
        project_id="p1",
    )

    drawing = result["drawings"][0]
    assert drawing["ocr_page_proof_status"] == "complete"
    assert drawing["page_boundary_status"] == "reliable_form_feed"
    assert len(drawing["page_anchors"]) == 2
    assert drawing["page_anchors"][0]["text_sha256"] == hashlib.sha256(
        first_page.encode()
    ).hexdigest()
    assert drawing["page_anchors"][1]["text_sha256"] == hashlib.sha256(
        second_page.encode()
    ).hexdigest()
    assert result["chapter_bindings"][0]["page"] == 2


def test_forged_audit_identity_and_external_extract_are_rejected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    forged_extract = tmp_path / "forged.txt"
    forged_extract.write_text("钢梁安装构件位置与节点做法。", encoding="utf-8")
    forged = {
        "project_id": "p1",
        "workspace_dir": str(tmp_path / "backend/data"),
        "filename": "forged.pdf",
        "saved_as": str(tmp_path / "forged.pdf"),
        "sha256": "a" * 64,
        "file_id": "b" * 64,
        "pages": 1,
        "tags": ["drawing"],
        "extract_saved_as": str(forged_extract),
        "extract_text_sha256": hashlib.sha256(
            forged_extract.read_bytes()
        ).hexdigest(),
    }
    _write_audit(tmp_path, [forged])
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢梁安装施工工艺"],
        project_id="p1",
    )

    assert result["drawings"] == []
    assert result["chapter_bindings"] == []
    assert result["invalid_identity_count"] == 1
    assert result["integrity_rejection_count"] == 1
    assert result["integrity_rejections"][0]["reason"] == (
        "audit_sha_file_id_mismatch"
    )


def test_failed_drawing_ocr_page_blocks_all_page_bindings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    record = _record(
        tmp_path,
        filename="两页钢梁图.pdf",
        sha="ocr-failure",
        text="\f钢梁安装构件位置与节点做法。",
        pages=2,
        ocr_error="page_ocr_incomplete",
        ocr_page_statuses=["failed", "text"],
    )
    _write_audit(tmp_path, [record])
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢梁安装施工工艺"],
        project_id="p1",
    )

    drawing = result["drawings"][0]
    assert result["ok"] is False
    assert drawing["text_status"] == "locator_unavailable"
    assert drawing["page_anchors"] == []
    assert drawing["ocr_page_proof_status"] == "ocr_page_proof_incomplete"
    assert result["chapter_bindings"] == []


def test_integrity_rejection_prevents_mixed_catalog_from_reporting_complete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    valid = _record(
        tmp_path,
        filename="钢梁图.pdf",
        sha="valid",
        text="钢梁安装构件位置与节点做法。",
    )
    forged = dict(valid)
    forged.update(
        {
            "filename": "伪造钢柱图.pdf",
            "sha256": "a" * 64,
            "file_id": "b" * 64,
        }
    )
    _write_audit(tmp_path, [valid, forged])
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢梁安装施工工艺"],
        project_id="p1",
    )

    assert len(result["drawings"]) == 1
    assert result["integrity_rejection_count"] == 1
    assert result["ok"] is False
    assert result["text_index_status"] == "incomplete"
