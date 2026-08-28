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
        "ocr_page_proof_version": "ocr-page-proof-v3",
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
        "ocr_graphics_only_pages": [],
        "ocr_no_text_locators": [],
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


def test_standard_index_uses_supplied_audit_and_registry_bytes_without_reread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    compliance_root = tmp_path / "compliance"
    compliance_root.mkdir()
    record = _record(
        workspace,
        project_id="P-SNAPSHOT",
        filename="GB 55037-2022 建筑防火通用规范.pdf",
        text="封面 GB55037-2022 建筑防火通用规范。\f防火分隔应验收。",
    )
    _write_audit(workspace, [])
    audit_path = workspace / "audit" / "ingest.jsonl"
    registry_path = compliance_root / "_official_registry.json"
    registry_payload = {
        "standards": [
            {
                "standard_code": "GB 55037-2022",
                "source_name": "建筑防火通用规范",
                "official_source": "https://ha.119.gov.cn/example",
                "official_document_url": "https://oss.example/gb55037.pdf",
                "official_content_sha256": record["sha256"],
                "effective_status": "active",
                "current_version": "GB 55037-2022",
                "latest": True,
            }
        ]
    }
    registry_bytes = json.dumps(
        registry_payload,
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    registry_path.write_text('{"standards": []}', encoding="utf-8")
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes

    def _forbid_audit_reread(path: Path, *args, **kwargs) -> str:
        if path == audit_path:
            raise AssertionError("audit snapshot must not be reread")
        return original_read_text(path, *args, **kwargs)

    def _forbid_registry_reread(path: Path) -> bytes:
        if path == registry_path:
            raise AssertionError("registry snapshot must not be reread")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_text", _forbid_audit_reread)
    monkeypatch.setattr(Path, "read_bytes", _forbid_registry_reread)
    result = build_standard_index(
        "示例项目",
        ["防火分隔施工"],
        project_id="P-SNAPSHOT",
        workspace_dir=workspace,
        compliance_root=compliance_root,
        audit_lines=(json.dumps(record, ensure_ascii=False),),
        official_registry_bytes=registry_bytes,
    )
    empty = build_standard_index(
        "示例项目",
        [],
        project_id="P-SNAPSHOT",
        workspace_dir=workspace,
        compliance_root=compliance_root,
        audit_lines=(),
        official_registry_bytes=registry_bytes,
    )

    assert result["indexed_standard_count"] == 1
    assert result["official_registry_sha256"] == _sha256(registry_bytes)
    assert result["standards"][0]["standard_code"] == "GB 55037-2022"
    assert empty["indexed_standard_count"] == 0


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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text=f"{first_page}\f{second_page}",
    )
    _write_audit(workspace, [p2, p1])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [_registry_row(metadata_only=True)],
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
        f"GB_T 50326-2017 项目管理规范.pdf#p2_{p1['sha256']}@"
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


def test_gb_55037_requires_registry_metadata_and_ingested_pdf_page_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    first_page = (
        "封面 OCR 噪声 Dll、DL L、HY TR。"
        "GB 55037-2022 建筑防火通用规范。"
    )
    second_page = (
        "防火分区施工应按已批准方案实施并形成检查记录，"
        "相关设计引用 GB 50016-2014。"
    )
    filename = "GB 55037-2022 建筑防火通用规范.pdf"
    record = _record(
        workspace,
        project_id="p1",
        filename=filename,
        text=f"{first_page}\f{second_page}",
    )
    _write_audit(workspace, [record])
    registry_row = {
        "standard_code": "GB 55037-2022",
        "source_name": "建筑防火通用规范",
        "official_source": (
            "https://ha.119.gov.cn/2025/04-16/3491624.html"
        ),
        "effective_status": "现行有效",
        "current_version": "GB 55037-2022",
        "latest": True,
        "metadata_only": True,
        "official_document_url": (
            "https://oss.dahe.cn/bdtypt/sbgt-wztipt/typtfile/20250416/"
            "5aeb7bf9074144b9a3c0ec1901bc10c3.pdf"
        ),
        "official_content_sha256": record["sha256"],
    }
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [registry_row],
    )

    identity = standard_index._document_standard_identity(
        filename,
        f"{first_page}\f{second_page}",
    )
    assert identity["status"] == "identified"
    assert identity["primary_code"] == "GB 55037-2022"
    assert identity["filename_codes"] == ["GB 55037-2022"]
    assert identity["cover_codes"] == ["GB 55037-2022"]
    assert identity["cover_rejected_codes"] == []
    assert identity["all_codes"] == ["GB 55037-2022", "GB 50016-2014"]

    result = build_standard_index(
        "示例项目",
        ["防火分区施工方法"],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["ok"] is True
    assert result["official_registry_verified_count"] == 1
    assert result["metadata_only_registry_count"] == 1
    row = result["standards"][0]
    assert row["primary_identity_status"] == "identified"
    assert row["primary_identity_proof_basis"] == "filename_and_cover"
    assert row["standard_code"] == "GB 55037-2022"
    assert row["referenced_standard_codes"] == ["GB 50016-2014"]
    assert row["source_hash_proof_status"] == "verified"
    assert row["source_hash_proof"] == {
        "status": "verified",
        "basis": "official_content_sha256",
        "expected_sha256": record["sha256"],
        "actual_sha256": record["sha256"],
        "official_document_url": registry_row["official_document_url"],
    }
    assert row["official_registry_status"] == "verified_metadata_only"
    assert row["official_registry"]["source_hash_proof_status"] == "verified"
    assert row["official_registry"]["clause_evidence_eligible"] is False
    assert row["clause_evidence_eligible"] is True
    assert row["clause_evidence_source"] == "ingested_standard_text"
    assert row["registry_metadata_used_as_clause_evidence"] is False
    assert [anchor["page"] for anchor in row["page_anchors"]] == [1, 2]
    binding = result["chapter_bindings"][0]
    assert binding["page"] == 2
    assert binding["sha256"] == record["sha256"]
    assert binding["page_text_sha256"] == row["page_anchors"][1][
        "text_sha256"
    ]
    assert binding["binding_basis"] == (
        "chapter_specific_ingested_standard_text"
    )

    mismatched_registry = dict(registry_row)
    mismatched_registry["official_content_sha256"] = "0" * 64
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [mismatched_registry],
    )
    mismatched = build_standard_index(
        "示例项目",
        ["防火分区施工方法"],
        project_id="p1",
        workspace_dir=workspace,
    )
    assert mismatched["standards"][0]["primary_identity_status"] == "identified"
    assert mismatched["standards"][0]["official_registry_status"] == (
        "official_content_sha256_mismatch"
    )
    assert mismatched["standards"][0]["source_hash_proof_status"] == "mismatch"
    assert mismatched["standards"][0]["clause_evidence_eligible"] is False
    assert mismatched["standards"][0]["clause_evidence_source"] is None
    assert mismatched["chapter_bindings"] == []
    assert mismatched["official_registry_verified_count"] == 0


def test_gb_50300_requires_full_cover_and_pinned_source_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    filename = "GB 50300-2013 建筑工程施工质量验收统一标准.pdf"
    first_page = "封面 GB 50300-2013 建筑工程施工质量验收统一标准。"
    second_page = "检验批验收应保留可追溯记录。"
    record = _record(
        workspace,
        project_id="p1",
        filename=filename,
        text=f"{first_page}\f{second_page}",
    )
    _write_audit(workspace, [record])
    registry_row = _registry_row(
        standard_code="GB 50300-2013",
        source_name="建筑工程施工质量验收统一标准",
    )
    registry_row.update(
        {
            "official_document_url": (
                "https://zjw.sh.gov.cn/cmsres/34/"
                "349cab456a80498091dd53105c3b6109/"
                "7573fa552919c7dbb9ddd603afc4eea0.pdf"
            ),
            "official_content_sha256": record["sha256"],
        }
    )
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [registry_row],
    )

    identity = standard_index._document_standard_identity(
        filename,
        f"{first_page}\f{second_page}",
    )
    assert identity["status"] == "identified"
    assert identity["primary_code"] == "GB 50300-2013"
    assert identity["filename_codes"] == ["GB 50300-2013"]
    assert identity["cover_codes"] == ["GB 50300-2013"]
    assert identity["proof_basis"] == "filename_and_cover"
    assert identity["referenced_codes"] == []

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    row = result["standards"][0]
    assert row["primary_identity_status"] == "identified"
    assert row["primary_identity_proof_basis"] == "filename_and_cover"
    assert row["standard_code"] == "GB 50300-2013"
    assert row["source_hash_proof_status"] == "verified"
    assert row["official_registry_status"] == "verified_metadata_only"
    assert row["official_registry"]["current_version"] == "GB 50300-2013"

    base_only_identity = standard_index._document_standard_identity(
        filename,
        "封面 GB 50300 建筑工程施工质量验收统一标准。",
    )
    base_only_with_hash = standard_index._identity_with_official_content_proof(
        base_only_identity,
        {"GB_50300_2013": registry_row},
        source_sha256=record["sha256"],
    )
    assert base_only_with_hash["source_hash_proof"]["status"] == "verified"
    assert base_only_with_hash["primary_code"] is None
    assert base_only_with_hash["status"] == "primary_identity_conflict"

    mismatched_hash_registry = dict(registry_row)
    mismatched_hash_registry["official_content_sha256"] = "0" * 64
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [mismatched_hash_registry],
    )
    mismatched_hash = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )
    mismatched_hash_row = mismatched_hash["standards"][0]
    assert mismatched_hash_row["primary_identity_status"] == "identified"
    assert mismatched_hash_row["official_registry_status"] == (
        "official_content_sha256_mismatch"
    )
    assert mismatched_hash_row["source_hash_proof_status"] == "mismatch"

    mismatched_registry = dict(registry_row)
    mismatched_registry["current_version"] = "GB 50300-2024"
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [mismatched_registry],
    )
    mismatch = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )
    assert mismatch["standards"][0]["official_registry_status"] == (
        "registry_current_version_mismatch"
    )


def test_official_preface_only_pdf_requires_explicit_exact_pin_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    filename = "GB55032-2022 建筑与市政工程施工质量控制通用规范.pdf"
    record = _record(
        workspace,
        project_id="p1",
        filename=filename,
        text="前言 建筑与市政工程施工质量控制通用规范。\f质量控制应形成记录。",
    )
    _write_audit(workspace, [record])
    registry_row = _registry_row(
        standard_code="GB 55032-2022",
        source_name="建筑与市政工程施工质量控制通用规范",
    )
    registry_row.update(
        {
            "official_source": (
                "https://szwb.sz.gov.cn/gwszwfw/zsk/hybz/content/"
                "post_10878088.html"
            ),
            "official_document_url": (
                "https://szwb.sz.gov.cn/attachment/1/1356/1356241/10878088.pdf"
            ),
            "official_content_sha256": record["sha256"],
            "official_identity_without_cover": True,
        }
    )
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [registry_row],
    )

    result = build_standard_index(
        "示例项目",
        ["质量控制"],
        project_id="p1",
        workspace_dir=workspace,
    )

    row = result["standards"][0]
    assert row["standard_code"] == "GB 55032-2022"
    assert row["primary_identity_status"] == "identified"
    assert row["primary_identity_proof_basis"] == (
        "official_page_and_content_sha256"
    )
    assert row["source_hash_proof_status"] == "verified"
    assert row["official_registry_status"] == "verified_metadata_only"
    assert row["clause_evidence_eligible"] is True
    assert result["chapter_bindings"]

    no_policy = dict(registry_row)
    no_policy.pop("official_identity_without_cover")
    identity = standard_index._document_standard_identity(filename, "前言 正文")
    without_policy = standard_index._identity_with_official_content_proof(
        identity,
        {"GB_55032_2022": no_policy},
        source_sha256=record["sha256"],
    )
    assert without_policy["status"] != "identified"

    conflicting_cover = standard_index._document_standard_identity(
        filename,
        "封面 GB 55037-2022 建筑防火通用规范。",
    )
    conflict = standard_index._identity_with_official_content_proof(
        conflicting_cover,
        {"GB_55032_2022": registry_row},
        source_sha256=record["sha256"],
    )
    assert conflict["status"] == "primary_identity_conflict"
    assert conflict["primary_code"] is None

    hash_mismatch = standard_index._identity_with_official_content_proof(
        identity,
        {"GB_55032_2022": registry_row},
        source_sha256="0" * 64,
    )
    assert hash_mismatch["status"] != "identified"
    assert hash_mismatch["source_hash_proof"]["status"] == "mismatch"


@pytest.mark.parametrize(
    "cover_text",
    [
        "封面 GB 55037-2022 建筑防火通用规范。",
        "封面 GB 50300-2024 建筑工程施工质量验收统一标准。",
    ],
)
def test_full_filename_identity_conflicts_with_different_base_or_year(
    cover_text: str,
) -> None:
    identity = standard_index._document_standard_identity(
        "GB 50300-2013 建筑工程施工质量验收统一标准.pdf",
        cover_text,
    )

    assert identity["primary_code"] is None
    assert identity["status"] == "primary_identity_conflict"


def test_document_identity_shape_filter_preserves_legal_numeric_codes() -> None:
    assert standard_index._unique_standard_codes(
        "Dll DL L HY TR；DL/T 5210.1-2012；JTG D60-2015"
    ) == ["DL/T 5210.1-2012", "JTG D60-2015"]


@pytest.mark.parametrize(
    ("filename", "cover_text", "source_sha256"),
    [
        (
            "GB 55037-2022 建筑防火通用规范.pdf",
            "Dll HY TR 建筑防火通用规范。",
            "a" * 64,
        ),
        (
            "GB 55037-2022 建筑防火通用规范.pdf",
            "Dll HY TR 建筑防火通用规范。",
            "b" * 64,
        ),
        (
            "GB 55037-2022 建筑防火通用规范.pdf",
            "封面 GB 55032-2022 建筑防火通用规范。",
            "a" * 64,
        ),
        (
            "GB 55032-2022 重命名.pdf",
            "Dll HY TR 建筑防火通用规范。",
            "a" * 64,
        ),
    ],
)
def test_pinned_hash_never_replaces_missing_or_conflicting_cover_identity(
    filename: str,
    cover_text: str,
    source_sha256: str,
) -> None:
    registry_row = {
        "standard_code": "GB 55037-2022",
        "source_name": "建筑防火通用规范",
        "official_source": "https://official.example/gb55037",
        "effective_status": "现行有效",
        "current_version": "GB 55037-2022",
        "latest": True,
        "metadata_only": True,
        "official_content_sha256": "a" * 64,
    }
    identity = standard_index._identity_with_official_content_proof(
        standard_index._document_standard_identity(filename, cover_text),
        {"GB_55037_2022": registry_row},
        source_sha256=source_sha256,
    )

    assert identity["primary_code"] is None
    assert identity["status"] == "primary_identity_conflict"


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
        lambda _root=None: [
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
    assert row["official_registry_status"] == "primary_identity_conflict"
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。\f",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [_registry_row()],
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
            "ocr_page_status_invalid",
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
            "ocr_blank_page_manifest_invalid",
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。\f第二页正文",
    )
    mutate(record)
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [],
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
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
        lambda _root=None: [],
    )

    result = build_standard_index(
        "示例项目",
        [],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert result["standards"] == []
    assert "ocr_extract_page_count_mismatch" in _rejection_codes(result)


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
        lambda _root=None: [],
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
        lambda _root=None: [],
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
        lambda _root=None: [],
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
        lambda _root=None: [],
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
        lambda _root=None: [],
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text=(
            "封面 GB/T 50326-2017 建设工程项目管理规范。"
            "\f参考文献：JGJ 18-2012 钢筋焊接及验收规程。"
        ),
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。",
    )
    _write_audit(workspace, [record])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [_registry_row(source_name="混凝土结构工程施工规范")],
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
        filename="GB_T 50326-2017 项目管理规范.pdf",
        text="封面 GB/T 50326-2017 建设工程项目管理规范。",
        source_bytes=b"different-primary-document",
    )
    _write_audit(workspace, [ambiguous_cover, ambiguous_registry])
    monkeypatch.setattr(
        standard_index,
        "list_verified_standard_metadata",
        lambda _root=None: [
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
    assert rows["GB_T 50326-2017 项目管理规范.pdf"]["official_registry_status"] == (
        "registry_identity_ambiguous"
    )
