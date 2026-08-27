from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from backend.zhifei_autoplan import standard_index
from backend.zhifei_autoplan.standard_index import build_standard_index


def _sha256(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def _write_audit(workspace: Path, rows: list[dict[str, Any]]) -> None:
    audit_path = workspace / "audit" / "ingest.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _record(
    workspace: Path,
    *,
    project_id: str,
    filename: str,
    text: str,
    pages: int | None = None,
    source_bytes: bytes | None = None,
    tags: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    page_texts = text.split("\f")
    page_count = pages if pages is not None else len(page_texts)
    if len(page_texts) != page_count:
        raise AssertionError("valid fixture text must preserve every page boundary")
    payload = source_bytes or f"{project_id}:{filename}:{text}:{page_count}".encode()
    digest = _sha256(payload)
    source_path = workspace / "uploads" / "20260827" / f"{digest}_{filename}"
    extract_digest = _sha256(text)
    extract_path = workspace / "extracts" / f"{digest}_{extract_digest}.txt"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    extract_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(payload)
    extract_path.write_text(text, encoding="utf-8")

    statuses = ["text" if page.strip() else "blank" for page in page_texts]
    record: dict[str, Any] = {
        "project_id": project_id,
        "workspace_dir": str(workspace),
        "filename": filename,
        "saved_as": str(source_path),
        "sha256": digest,
        "file_id": digest,
        "pages": page_count,
        "doc_type": "pdf",
        "tags": tags if tags is not None else ["standard"],
        "source_hint": "standard",
        "extract_saved_as": str(extract_path),
        "extract_text_sha256": extract_digest,
        "ocr_cache_policy": "standard_full_page",
        "ocr_page_proof_version": "ocr-page-proof-v1",
        "ocr_page_mapping": "source_page_all",
        "ocr_error": None,
        "ocr_source_pages": page_count,
        "ocr_pages": page_count,
        "ocr_page_text_count": page_count,
        "ocr_page_statuses": statuses,
        "ocr_page_image_sha256": [
            _sha256(f"rendered-page:{page}")
            for page in range(1, page_count + 1)
        ],
        "ocr_page_text_sha256": [
            _sha256(page.strip()) for page in page_texts
        ],
        "ocr_extract_page_sha256": [
            _sha256(page) for page in page_texts
        ],
        "ocr_blank_pages": [
            index
            for index, status in enumerate(statuses, start=1)
            if status == "blank"
        ],
    }
    record.update(extra)
    return record


def _registry_row(
    *,
    standard_code: str = "GB/T 50326-2017",
    source_name: str = "建设工程项目管理规范",
    metadata_only: bool = True,
) -> dict[str, Any]:
    return {
        "standard_code": standard_code,
        "source_name": source_name,
        "official_source": f"https://official.example/{_sha256(standard_code)[:12]}",
        "effective_status": "active",
        "current_version": standard_code,
        "latest": True,
        "metadata_only": metadata_only,
    }


def _rejection_codes(result: dict[str, Any]) -> set[str]:
    return {
        str(item.get("code"))
        for item in result.get("integrity_rejections") or []
        if isinstance(item, dict)
    }


def test_standard_index_requires_project_id(tmp_path: Path) -> None:
    result = build_standard_index(
        "示例项目",
        [],
        workspace_dir=tmp_path / "workspace",
    )

    assert result["ok"] is False
    assert result["reason"] == "missing_project_id"
    assert result["standards"] == []


def test_standard_index_is_project_isolated_and_preserves_full_sha_page_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    first_page = "封面 GB/T 50326-2017 建设工程项目管理规范。"
    second_page = "钢筋绑扎施工工艺应执行分段验收并保留记录。"
    p2 = _record(
        workspace,
        project_id="p2",
        filename="其他项目规范.pdf",
        text="封面 JGJ 18-2012 钢筋焊接及验收规程。",
    )
    p1 = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text=f"{first_page}\f{second_page}",
    )
    _write_audit(workspace, [p2, p1])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [_registry_row(metadata_only=True)],
    )

    result = build_standard_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["ok"] is True
    assert result["project_id"] == "p1"
    assert len(result["standards"]) == 1
    row = result["standards"][0]
    assert row["sha256"] == p1["sha256"] == row["file_id"]
    assert len(row["sha256"]) == 64
    assert row["source_integrity_status"] == "verified"
    assert row["extract_text_sha256"] == p1["extract_text_sha256"]
    assert row["standard_code"] == "GB/T 50326-2017"
    assert [anchor["page"] for anchor in row["page_anchors"]] == [1, 2]
    assert row["page_anchors"][1]["locator"].startswith(
        f"项目管理规范.pdf#p2_{p1['sha256']}@"
    )
    assert row["official_registry_status"] == "verified_metadata_only"
    assert row["official_source"].startswith("https://official.example/")
    assert row["official_registry"]["clause_evidence_eligible"] is False
    assert row["clause_evidence_eligible"] is True
    assert row["registry_metadata_used_as_clause_evidence"] is False

    binding = result["chapter_bindings"][0]
    assert binding["page"] == 2
    assert binding["sha256"] == p1["sha256"]
    assert binding["offset"] == len(first_page) + 1
    assert binding["binding_basis"] == "chapter_specific_ingested_standard_text"
    assert binding["registry_metadata_used_as_clause_evidence"] is False
    assert (
        binding["page_anchor"]["text_sha256"]
        == row["page_anchors"][1]["text_sha256"]
    )


def test_metadata_only_registry_cannot_create_clause_evidence_from_blank_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="GB 50326-2017 建设工程项目管理规范.pdf",
        text="",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [
            _registry_row(
                standard_code="GB 50326-2017",
                metadata_only=True,
            )
        ],
    )

    result = build_standard_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["ok"] is True
    row = result["standards"][0]
    assert row["official_registry_status"] == "verified_metadata_only"
    assert row["official_registry"]["clause_evidence_eligible"] is False
    assert row["clause_evidence_eligible"] is False
    assert len(row["page_anchors"]) == 1
    assert row["page_anchors"][0]["blank_proven"] is True
    assert row["page_anchors"][0]["evidence_eligible"] is False
    assert result["chapter_bindings"] == []
    assert result["chapter_binding_status"] == "no_chapter_specific_evidence"


def test_standard_index_accepts_explicit_blank_proof_with_complete_page_coverage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。\f",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [_registry_row()],
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["ok"] is True
    anchors = result["standards"][0]["page_anchors"]
    assert [anchor["page"] for anchor in anchors] == [1, 2]
    assert anchors[0]["ocr_status"] == "text"
    assert anchors[1]["ocr_status"] == "blank"
    assert anchors[1]["blank_proven"] is True


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda record: record.pop("ocr_page_statuses"),
            "ocr_page_proof_incomplete",
        ),
        (
            lambda record: record["ocr_page_statuses"].__setitem__(
                1,
                "unreadable",
            ),
            "ocr_page_failed_or_unreadable",
        ),
        (
            lambda record: record.__setitem__("ocr_source_pages", 3),
            "ocr_page_proof_incomplete",
        ),
        (
            lambda record: record.__setitem__("ocr_page_text_count", 1),
            "ocr_page_proof_incomplete",
        ),
        (
            lambda record: record["ocr_extract_page_sha256"].__setitem__(
                0,
                "f" * 64,
            ),
            "ocr_extract_page_digest_mismatch",
        ),
        (
            lambda record: record.__setitem__("ocr_blank_pages", [1]),
            "ocr_blank_page_manifest_mismatch",
        ),
    ],
)
def test_standard_index_rejects_incomplete_or_failed_full_page_ocr_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutate: Any,
    expected_code: str,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。\f第二页正文",
    )
    mutate(record)
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["ok"] is False
    assert result["standards"] == []
    assert expected_code in _rejection_codes(result)


def test_standard_index_rejects_partial_page_anchor_even_with_valid_hashes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。\f第二页正文",
    )
    extract_path = Path(record["extract_saved_as"])
    extract_path.write_text("只有一页但审计仍声明两页", encoding="utf-8")
    record["extract_text_sha256"] = _sha256(extract_path.read_bytes())
    renamed_extract = extract_path.with_name(
        f"{record['sha256']}_{record['extract_text_sha256']}.txt"
    )
    extract_path.rename(renamed_extract)
    record["extract_saved_as"] = str(renamed_extract)
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert "ocr_extract_page_proof_incomplete" in _rejection_codes(result)


def test_standard_index_rejects_short_or_mismatched_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    short = _record(
        workspace,
        project_id="p1",
        filename="企业标准.pdf",
        text="企业标准正文。",
    )
    short["sha256"] = "deadbeef"
    mismatch = _record(
        workspace,
        project_id="p1",
        filename="另一企业标准.pdf",
        text="另一份企业标准正文。",
    )
    mismatch["file_id"] = "f" * 64
    _write_audit(workspace, [short, mismatch])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert result["invalid_identity_count"] == 2
    assert _rejection_codes(result) == {"audit_sha_file_id_mismatch"}


def test_standard_index_rejects_source_and_extract_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    source_tamper = _record(
        workspace,
        project_id="p1",
        filename="源文件篡改.pdf",
        text="源文件篡改测试。",
    )
    Path(source_tamper["saved_as"]).write_bytes(b"tampered-source")
    extract_tamper = _record(
        workspace,
        project_id="p1",
        filename="提取文件篡改.pdf",
        text="提取文件篡改测试。",
    )
    Path(extract_tamper["extract_saved_as"]).write_text(
        "摘要不再匹配",
        encoding="utf-8",
    )
    _write_audit(workspace, [source_tamper, extract_tamper])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert _rejection_codes(result) == {
        "extract_text_sha256_mismatch",
        "source_bytes_sha256_mismatch",
    }


def test_standard_index_rejects_external_and_short_prefix_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    external = _record(
        workspace,
        project_id="p1",
        filename="外部提取路径.pdf",
        text="外部提取路径测试。",
    )
    outside_extract = tmp_path / "outside.txt"
    outside_extract.write_text("外部提取路径测试。", encoding="utf-8")
    external["extract_saved_as"] = str(outside_extract)

    prefix = _record(
        workspace,
        project_id="p1",
        filename="短摘要前缀.pdf",
        text="短摘要前缀测试。",
    )
    old_source = Path(prefix["saved_as"])
    short_source = old_source.with_name(f"{prefix['sha256'][:8]}_短摘要前缀.pdf")
    old_source.rename(short_source)
    prefix["saved_as"] = str(short_source)

    extract_prefix = _record(
        workspace,
        project_id="p1",
        filename="短提取摘要前缀.pdf",
        text="短提取摘要前缀测试。",
    )
    old_extract = Path(extract_prefix["extract_saved_as"])
    short_extract = old_extract.with_name(
        f"{extract_prefix['sha256'][:8]}_extract.txt"
    )
    old_extract.rename(short_extract)
    extract_prefix["extract_saved_as"] = str(short_extract)

    _write_audit(workspace, [external, prefix, extract_prefix])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert result["integrity_rejection_count"] == 3
    assert _rejection_codes(result) == {
        "extract_path_outside_workspace_or_not_full_sha",
        "source_path_outside_workspace_or_not_full_sha",
    }


def test_standard_index_rejects_cross_workspace_audit_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    other_workspace = tmp_path / "other-workspace"
    record = _record(
        other_workspace,
        project_id="p1",
        filename="其他工作区规范.pdf",
        text="其他工作区标准正文。",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert _rejection_codes(result) == {"audit_workspace_mismatch"}


def test_standard_index_rejects_raw_standard_drawing_double_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="旧双标签.pdf",
        text="旧双标签资料。",
        tags=["standard", "drawing"],
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        list,
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert _rejection_codes(result) == {"ambiguous_standard_drawing_tags"}


def test_reference_code_in_body_cannot_verify_current_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text=(
            "封面 GB/T 50326-2017 建设工程项目管理规范。"
            "\f参考文献：JGJ 18-2012 钢筋焊接及验收规程。"
        ),
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [
            _registry_row(
                standard_code="JGJ 18-2012",
                source_name="钢筋焊接及验收规程",
            )
        ],
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    row = result["standards"][0]
    assert row["standard_code"] == "GB/T 50326-2017"
    assert row["referenced_standard_codes"] == ["JGJ 18-2012"]
    assert row["official_registry_status"] == "not_verified"
    assert row["official_source"] is None


def test_registry_source_name_must_match_primary_document_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    record = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [_registry_row(source_name="混凝土结构工程施工规范")],
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    row = result["standards"][0]
    assert row["official_registry_status"] == "source_name_mismatch"
    assert row["official_registry"]["clause_evidence_eligible"] is False


def test_ambiguous_cover_or_registry_identity_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    ambiguous_cover = _record(
        workspace,
        project_id="p1",
        filename="规范合集.pdf",
        text=(
            "封面同时列出 GB/T 50326-2017 建设工程项目管理规范"
            "和 JGJ 18-2012 钢筋焊接及验收规程。"
        ),
    )
    ambiguous_registry = _record(
        workspace,
        project_id="p1",
        filename="项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。",
        source_bytes=b"different-primary-document",
    )
    _write_audit(workspace, [ambiguous_cover, ambiguous_registry])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda: [
            _registry_row(),
            _registry_row(source_name="冲突名称"),
        ],
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    rows = {row["filename"]: row for row in result["standards"]}
    assert rows["规范合集.pdf"]["primary_identity_status"] == (
        "primary_identity_ambiguous"
    )
    assert rows["规范合集.pdf"]["official_registry_status"] == (
        "primary_identity_ambiguous"
    )
    assert rows["项目管理规范.pdf"]["official_registry_status"] == (
        "registry_identity_ambiguous"
    )
