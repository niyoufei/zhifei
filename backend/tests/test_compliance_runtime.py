from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from backend.zhifei_autoplan import compliance_runtime
from backend.zhifei_autoplan.compliance_policy import (
    is_verified_standard_metadata,
)
from backend.zhifei_autoplan.compliance_runtime import (
    build_compliance_catalog,
    get_compliance_registry_status,
    list_verified_standard_metadata,
    query_compliance,
)
from backend.zhifei_autoplan.sealed_compliance import (
    SealedComplianceError,
    SealedRegistryAuthority,
)


def _write_compliance_file(
    path: Path,
    *,
    standard_code: str,
    domain_tag: str,
    source_name: str,
    clause_text: str,
    generated_at: str,
    official_source: str = "",
    effective_status: str = "",
    source_document_sha256: str = "",
) -> None:
    payload = {
        "graph_track": "compliance",
        "metadata": {
            "source_name": source_name,
            "standard_code": standard_code,
            "domain_tag": domain_tag,
            "generated_at": generated_at,
            "official_source": official_source,
            "effective_status": effective_status,
            "source_document_sha256": source_document_sha256,
        },
        "stats": {"mandatory_count": 1, "parameter_count": 1},
        "nodes": [
            {
                "node_id": f"{standard_code}#C0001",
                "clause_no": "5.2.1",
                "mandatory_level": "要求类",
                "text": clause_text,
            }
        ],
        "parameters": [
            {
                "parameter_id": "P0001",
                "parameter_name": "搭接长度",
                "value": "35",
                "unit": "d",
                "context": "钢筋搭接长度不应小于35d",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_catalog_marks_latest_version(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)

    _write_compliance_file(
        root / "a_compliance.json",
        standard_code="GB_50502_2009",
        domain_tag="房建工程",
        source_name="旧版规范",
        clause_text="混凝土浇筑前应进行模板检查。",
        generated_at="2025-01-01T00:00:00",
    )
    _write_compliance_file(
        root / "b_compliance.json",
        standard_code="GB_50502_2022",
        domain_tag="房建工程",
        source_name="新版规范",
        clause_text="混凝土浇筑前应完成模板、钢筋及预埋件联合验收。",
        generated_at="2026-01-01T00:00:00",
    )

    cat = build_compliance_catalog(root)
    entries = cat.get("entries") or []
    latest = [e for e in entries if e.get("latest")]
    assert len(entries) == 2
    assert len(latest) == 1
    assert latest[0].get("standard_code") == "GB_50502_2022"


def test_query_prefers_latest_and_filters_by_domain(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    _write_compliance_file(
        root / "a_compliance.json",
        standard_code="GB_50502_2009",
        domain_tag="房建工程",
        source_name="旧版规范",
        clause_text="混凝土强度检验应按批次实施。",
        generated_at="2025-01-01T00:00:00",
    )
    _write_compliance_file(
        root / "b_compliance.json",
        standard_code="GB_50502_2022",
        domain_tag="房建工程",
        source_name="新版规范",
        clause_text="混凝土强度检验应按批次实施并留存复核记录。",
        generated_at="2026-01-01T00:00:00",
    )
    _write_compliance_file(
        root / "c_compliance.json",
        standard_code="SL_303_2017",
        domain_tag="水利水电",
        source_name="水利规范",
        clause_text="渠道防渗施工应设置分缝并控制渗漏率。",
        generated_at="2024-01-01T00:00:00",
    )

    build_compliance_catalog(root)

    hits_housing = query_compliance(
        "混凝土 强度 检验",
        domain_tags=["房建工程"],
        top_k=3,
        prefer_latest=True,
        root=root,
    )
    assert hits_housing
    assert hits_housing[0].get("standard_code") == "GB_50502_2022"

    hits_water = query_compliance(
        "渠道 防渗 渗漏率",
        domain_tags=["水利水电"],
        top_k=3,
        prefer_latest=True,
        root=root,
    )
    assert hits_water
    assert all("SL_303_2017" == str(h.get("standard_code")) for h in hits_water)


def test_mutable_clause_cannot_self_assert_verified_status(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    _write_compliance_file(
        root / "verified_compliance.json",
        standard_code="GB_50300_2024",
        domain_tag="房建工程",
        source_name="建筑工程施工质量验收统一标准",
        clause_text="检验批验收应形成可追溯记录。",
        generated_at="2026-01-01T00:00:00",
        official_source="https://official.example/GB_50300_2024",
        effective_status="active",
    )
    _write_compliance_file(
        root / "unverified_compliance.json",
        standard_code="GB_50204_2015",
        domain_tag="房建工程",
        source_name="未核验本地副本",
        clause_text="检验批验收应形成可追溯记录。",
        generated_at="2026-01-01T00:00:00",
    )
    build_compliance_catalog(root)

    ordinary_hits = query_compliance(
        "检验批 验收 记录",
        domain_tags=["房建工程"],
        top_k=8,
        root=root,
    )
    assert ordinary_hits
    for hit in ordinary_hits:
        assert hit["verified"] is False
        assert hit["official_registry_verified"] is False
        assert hit["clause_source_authoritative"] is False
        assert len(hit["clause_source_sha256"]) == 64
        assert hit["clause_source_document_sha256"] == ""

    verified_hits = query_compliance(
        "检验批 验收 记录",
        domain_tags=["房建工程"],
        top_k=8,
        verified_only=True,
        root=root,
    )
    assert verified_hits == []
    catalog = build_compliance_catalog(root)
    clause_rows = [
        row for row in catalog["entries"] if row.get("metadata_only") is False
    ]
    assert clause_rows
    assert all(row.get("verified") is False for row in clause_rows)
    assert all(
        row.get("clause_source_authoritative") is False for row in clause_rows
    )
    parameter_hits = query_compliance(
        "搭接长度 35d",
        domain_tags=["房建工程"],
        top_k=8,
        verified_only=False,
        root=root,
    )
    assert parameter_hits
    assert all(hit["type"] == "parameter" for hit in parameter_hits)
    for hit in parameter_hits:
        assert hit["verified"] is False
        assert hit["clause_source_authoritative"] is False
        assert len(hit["clause_source_sha256"]) == 64
        assert "clause_source_document_sha256" in hit


def test_missing_registry_root_is_read_only(tmp_path: Path):
    root = tmp_path / "missing" / "compliance"
    status = get_compliance_registry_status(root)
    assert status["ready"] is False
    assert status["official_registry_ready"] is False
    assert status["clause_catalog_ready"] is False
    assert status["warnings"] == [
        "compliance_clause_root_missing",
        "no_verified_standard_metadata",
    ]
    assert not root.exists()


def test_repository_registry_verifies_gb_55037_as_metadata_only(
    tmp_path: Path,
):
    repository_root = Path(__file__).resolve().parents[2]
    source_registry = (
        repository_root / "知识图谱" / "compliance" / "_official_registry.json"
    )
    root = tmp_path / "compliance"
    root.mkdir(parents=True)
    registry = root / "_official_registry.json"
    registry.write_bytes(source_registry.read_bytes())

    rows = list_verified_standard_metadata(root=root)
    matches = [
        row for row in rows if row.get("standard_code") == "GB 55037-2022"
    ]
    gb_50300_matches = [
        row for row in rows if row.get("standard_code") == "GB 50300-2013"
    ]
    gb_55032_matches = [
        row for row in rows if row.get("standard_code") == "GB 55032-2022"
    ]

    assert len(rows) == 5
    assert len(matches) == 1
    assert len(gb_50300_matches) == 1
    assert len(gb_55032_matches) == 1
    row = matches[0]
    assert row["source_name"] == "建筑防火通用规范"
    assert row["current_version"] == "GB 55037-2022"
    assert row["effective_status"] == "现行有效"
    assert row["latest"] is True
    assert row["metadata_only"] is True
    assert row["official_source"] == (
        "https://ha.119.gov.cn/2025/04-16/3491624.html"
    )
    assert row["official_document_url"] == (
        "https://oss.dahe.cn/bdtypt/sbgt-wztipt/typtfile/20250416/"
        "5aeb7bf9074144b9a3c0ec1901bc10c3.pdf"
    )
    assert row["official_content_sha256"] == (
        "04a42d414cc6f5e42f3fe33e2af7042666673b69aaf265f829885f2a1f83bafe"
    )
    assert row["priority"] == "全文强制性工程建设规范"
    assert "2023-06-01" in row["verification_note"]
    assert "全部条文必须严格执行" in row["verification_note"]
    assert is_verified_standard_metadata(row) is True
    gb_50300 = gb_50300_matches[0]
    assert gb_50300["official_source"] == (
        "https://zjw.sh.gov.cn/xcsc2020-jsbz/20200430/"
        "1af104eaf997443aae1fac5abfcf948a.html"
    )
    assert gb_50300["official_document_url"] == (
        "https://zjw.sh.gov.cn/cmsres/34/349cab456a80498091dd53105c3b6109/"
        "7573fa552919c7dbb9ddd603afc4eea0.pdf"
    )
    assert gb_50300["official_content_sha256"] == (
        "601d66445bcfaed9adae5efd1030230ccb379972e73acdd4714069b2bd1eaf24"
    )
    assert is_verified_standard_metadata(gb_50300) is True
    gb_55032 = gb_55032_matches[0]
    assert gb_55032["official_content_sha256"] == (
        "42950e7c080e513c10ba1d4ecb41c1188b8ee0155b122424b6cfa33b03e69e97"
    )
    assert gb_55032["official_document_url"] == (
        "https://szwb.sz.gov.cn/attachment/1/1356/1356241/10878088.pdf"
    )
    assert gb_55032["official_identity_without_cover"] is True
    assert is_verified_standard_metadata(gb_55032) is True

    first_catalog = build_compliance_catalog(root)
    first_bytes = (root / "_catalog.json").read_bytes()
    second_catalog = build_compliance_catalog(root)
    assert second_catalog == first_catalog
    assert (root / "_catalog.json").read_bytes() == first_bytes


def test_tracked_catalog_is_exact_projection_of_repository_registry() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    root = repository_root / "知识图谱" / "compliance"
    registry_path = root / "_official_registry.json"
    catalog_path = root / "_catalog.json"
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["version"] == 3
    assert catalog["root"] == "."
    assert catalog["warnings"] == []
    assert catalog["official_registry_sha256"] == hashlib.sha256(
        registry_bytes
    ).hexdigest()
    assert "/Users/" not in catalog_path.read_text(encoding="utf-8")
    assert catalog["source_fingerprint"] == [
        {
            "name": "_official_registry.json",
            "size": len(registry_bytes),
            "sha256": hashlib.sha256(registry_bytes).hexdigest(),
        }
    ]
    registry_by_code = {
        row["standard_code"]: row for row in registry["standards"]
    }
    catalog_by_code = {
        row["standard_code"]: row for row in catalog["entries"]
    }
    assert set(catalog_by_code) == set(registry_by_code)
    for code, metadata in registry_by_code.items():
        projected = catalog_by_code[code]
        assert projected["source_name"] == metadata["standard_name"]
        assert projected["current_version"] == metadata["current_version"]
        assert projected["official_source"] == metadata["official_source"]
        assert projected["official_document_url"] == metadata.get(
            "official_document_url", ""
        )
        assert projected["official_content_sha256"] == metadata.get(
            "official_content_sha256", ""
        )
        assert projected["official_identity_without_cover"] is bool(
            metadata.get("official_identity_without_cover", False)
        )


def test_official_registry_hydrates_matching_local_clause_source(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    _write_compliance_file(
        root / "road_compliance.json",
        standard_code="CJJ 1-2008",
        domain_tag="市政道路",
        source_name="城镇道路工程施工与质量验收规范",
        clause_text="道路工程施工质量验收应形成检验记录。",
        generated_at="2026-01-01T00:00:00",
    )
    (root / "_official_registry.json").write_text(
        json.dumps(
            {
                "standards": [
                    {
                        "standard_code": "CJJ 1-2008",
                        "standard_name": "城镇道路工程施工与质量验收规范",
                        "official_source": "https://official.example/CJJ-1-2008",
                        "effective_status": "active",
                        "current_version": "CJJ 1-2008",
                        "domain_tags": ["市政道路"],
                        "latest": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cat = build_compliance_catalog(root)
    # The sealed metadata row and mutable clause row coexist.  Only the former
    # contributes to the verified count.
    assert cat["verified_count"] == 1
    rows = list_verified_standard_metadata(domain_tags=["市政道路"], root=root)
    assert len(rows) == 1
    assert rows[0]["standard_code"] == "CJJ 1-2008"
    assert rows[0]["metadata_only"] is True
    assert rows[0]["official_registry_verified"] is True
    hits = query_compliance(
        "道路 质量 验收 记录",
        domain_tags=["市政道路"],
        verified_only=True,
        root=root,
    )
    assert hits == []
    ordinary_hits = query_compliance(
        "道路 质量 验收 记录",
        domain_tags=["市政道路"],
        verified_only=False,
        root=root,
    )
    assert ordinary_hits
    assert {row["standard_code"] for row in ordinary_hits} == {"CJJ 1-2008"}
    for hit in ordinary_hits:
        assert hit["verified"] is False
        assert hit["official_registry_verified"] is True
        assert hit["clause_source_authoritative"] is False
        assert len(hit["clause_source_sha256"]) == 64
    clause_row = next(
        row for row in cat["entries"] if row.get("metadata_only") is False
    )
    assert clause_row["official_registry_verified"] is True
    assert clause_row["clause_source_authoritative"] is False
    assert clause_row["verified"] is False


def test_matching_official_content_pin_cannot_self_authorize_mutable_clauses(
    tmp_path: Path,
) -> None:
    root = tmp_path / "compliance"
    root.mkdir(parents=True)
    pinned_pdf_sha256 = "a" * 64
    _write_compliance_file(
        root / "road_compliance.json",
        standard_code="CJJ 1-2008",
        domain_tag="市政道路",
        source_name="城镇道路工程施工与质量验收规范",
        clause_text="道路工程施工质量验收应形成检验记录。",
        generated_at="2026-01-01T00:00:00",
        source_document_sha256=pinned_pdf_sha256,
    )
    (root / "_official_registry.json").write_text(
        json.dumps(
            {
                "standards": [
                    {
                        "standard_code": "CJJ 1-2008",
                        "standard_name": "城镇道路工程施工与质量验收规范",
                        "official_source": "https://official.example/CJJ-1-2008",
                        "official_document_url": (
                            "https://official.example/CJJ-1-2008.pdf"
                        ),
                        "official_content_sha256": pinned_pdf_sha256,
                        "effective_status": "active",
                        "current_version": "CJJ 1-2008",
                        "domain_tags": ["市政道路"],
                        "latest": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    catalog = build_compliance_catalog(root)
    clause_row = next(
        row
        for row in catalog["entries"]
        if row.get("metadata_only") is False
    )
    assert clause_row["clause_source_content_pin_matches"] is True
    assert clause_row["clause_source_authoritative"] is False
    assert clause_row["verified"] is False

    ordinary_hits = query_compliance(
        "道路 质量 验收 记录",
        domain_tags=["市政道路"],
        verified_only=False,
        root=root,
    )
    assert ordinary_hits
    assert all(
        hit["clause_source_content_pin_matches"] is True
        and hit["clause_source_authoritative"] is False
        and hit["verified"] is False
        for hit in ordinary_hits
    )
    assert query_compliance(
        "道路 质量 验收 记录",
        domain_tags=["市政道路"],
        verified_only=True,
        root=root,
    ) == []


def test_catalog_rebuilds_when_registry_changes(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    registry = root / "_official_registry.json"
    registry.write_text('{"standards": []}', encoding="utf-8")
    assert build_compliance_catalog(root)["verified_count"] == 0
    registry.write_text(
        json.dumps(
            {
                "standards": [
                    {
                        "standard_code": "GB/T 50326-2017",
                        "standard_name": "建设工程项目管理规范",
                        "official_source": "https://official.example/GB-T-50326-2017",
                        "effective_status": "active",
                        "current_version": "GB/T 50326-2017",
                        "domain_tags": ["通用工程"],
                        "latest": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    status = get_compliance_registry_status(root)
    assert status["ready"] is True
    assert status["verified_count"] == 1


def test_catalog_does_not_rebuild_for_source_mtime_only_change(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    registry = root / "_official_registry.json"
    registry.write_text('{"standards": []}', encoding="utf-8")

    catalog = build_compliance_catalog(root)
    catalog_path = root / "_catalog.json"
    original_bytes = catalog_path.read_bytes()
    original_fingerprint = catalog["source_fingerprint"]

    stat = registry.stat()
    os.utime(registry, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    status = get_compliance_registry_status(root)

    assert status["ready"] is False
    assert catalog_path.read_bytes() == original_bytes
    reloaded = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert reloaded["source_fingerprint"] == original_fingerprint
    assert set(original_fingerprint[0]) == {"name", "size", "sha256"}


def test_explicit_catalog_rebuild_is_byte_stable_when_sources_are_unchanged(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    (root / "_official_registry.json").write_text('{"standards": []}', encoding="utf-8")

    build_compliance_catalog(root)
    catalog_path = root / "_catalog.json"
    original_bytes = catalog_path.read_bytes()

    rebuilt = build_compliance_catalog(root)

    assert catalog_path.read_bytes() == original_bytes
    assert rebuilt == json.loads(original_bytes.decode("utf-8"))


def test_transient_path_exists_patch_cannot_poison_registry_load(
    tmp_path: Path,
    monkeypatch,
):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    registry = root / "_official_registry.json"
    registry.write_text(
        json.dumps(
            {
                "standards": [
                    {
                        "standard_code": "GB/T 50326-2017",
                        "standard_name": "建设工程项目管理规范",
                        "official_source": "https://official.example/GB-T-50326-2017",
                        "effective_status": "active",
                        "current_version": "GB/T 50326-2017",
                        "domain_tags": ["通用工程"],
                        "latest": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "exists", lambda _path: False)
    catalog = build_compliance_catalog(root)

    assert catalog["verified_count"] == 1
    assert catalog["entries"][0]["standard_code"] == "GB/T 50326-2017"


def test_managed_registry_snapshot_cannot_be_downgraded_by_explicit_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sealed_raw = b'{"standards":[{"standard_code":"GB 50300-2013"}]}'
    sealed_path = (
        tmp_path / "release" / "sealed-compliance" / "_official_registry.json"
    )
    sealed = SealedRegistryAuthority(
        raw=sealed_raw,
        path=sealed_path,
        projection={"authority_digest": "a" * 64},
    )
    monkeypatch.setattr(
        compliance_runtime,
        "_managed_release_registry_authority",
        lambda: sealed,
    )

    attacker_root = tmp_path / "attacker"
    attacker_root.mkdir()
    assert compliance_runtime.load_runtime_registry_authority(attacker_root) is sealed
    assert compliance_runtime.resolve_runtime_registry_snapshot(attacker_root) == (
        sealed_raw,
        sealed_path,
    )
    assert compliance_runtime.resolve_runtime_registry_snapshot(
        attacker_root,
        official_registry_bytes=sealed_raw,
        official_registry_path=sealed_path,
    ) == (sealed_raw, sealed_path)
    with pytest.raises(SealedComplianceError) as bytes_error:
        compliance_runtime.resolve_runtime_registry_snapshot(
            attacker_root,
            official_registry_bytes=b'{"standards":[]}',
            official_registry_path=sealed_path,
        )
    assert bytes_error.value.code == "SEALED_COMPLIANCE_REGISTRY_BYTES_MISMATCH"
    with pytest.raises(SealedComplianceError) as path_error:
        compliance_runtime.resolve_runtime_registry_snapshot(
            attacker_root,
            official_registry_bytes=sealed_raw,
            official_registry_path=tmp_path / "forged.json",
        )
    assert path_error.value.code == "SEALED_COMPLIANCE_REGISTRY_PATH_MISMATCH"


def test_managed_explicit_root_rebuilds_catalog_from_sealed_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clause_root = tmp_path / "attacker-root"
    clause_root.mkdir()
    _write_compliance_file(
        clause_root / "road_compliance.json",
        standard_code="CJJ 1-2008",
        domain_tag="市政道路",
        source_name="城镇道路工程施工与质量验收规范",
        clause_text="道路工程施工质量验收应形成检验记录。",
        generated_at="2026-01-01T00:00:00",
    )
    forged_catalog = {
        "version": 3,
        "entries": [
            {
                "standard_code": "GB 99999-2099",
                "verified": True,
                "official_registry_verified": True,
                "clause_source_authoritative": True,
            }
        ],
    }
    catalog_path = clause_root / "_catalog.json"
    catalog_path.write_text(json.dumps(forged_catalog), encoding="utf-8")
    original_catalog_bytes = catalog_path.read_bytes()
    sealed_raw = json.dumps(
        {
            "standards": [
                {
                    "standard_code": "CJJ 1-2008",
                    "standard_name": "城镇道路工程施工与质量验收规范",
                    "official_source": "https://official.example/CJJ-1-2008",
                    "effective_status": "active",
                    "current_version": "CJJ 1-2008",
                    "domain_tags": ["市政道路"],
                    "latest": True,
                }
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")
    sealed_path = (
        tmp_path / "release" / "sealed-compliance" / "_official_registry.json"
    )
    sealed = SealedRegistryAuthority(
        raw=sealed_raw,
        path=sealed_path,
        projection={"authority_digest": "b" * 64},
    )
    monkeypatch.setenv("ZF_RELEASE_MANAGED", "1")
    monkeypatch.setattr(
        compliance_runtime,
        "_managed_release_registry_authority",
        lambda: sealed,
    )

    catalog = compliance_runtime._load_or_build_catalog(
        clause_root,
    )
    assert catalog_path.read_bytes() == original_catalog_bytes
    assert {row["standard_code"] for row in catalog["entries"]} == {"CJJ 1-2008"}
    assert all(
        row.get("clause_source_authoritative") is not True
        for row in catalog["entries"]
        if row.get("metadata_only") is False
    )
    metadata = list_verified_standard_metadata(root=clause_root)
    assert [row["standard_code"] for row in metadata] == ["CJJ 1-2008"]
    hits = query_compliance(
        "道路 质量 验收 记录",
        root=clause_root,
        verified_only=False,
    )
    assert hits
    assert all(hit["verified"] is False for hit in hits)
    assert all(hit["standard_code"] != "GB 99999-2099" for hit in hits)
    assert query_compliance(
        "道路 质量 验收 记录",
        root=clause_root,
        verified_only=True,
    ) == []


def test_oversized_clause_source_is_skipped_without_reading_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "compliance"
    root.mkdir()
    (root / "_official_registry.json").write_text(
        json.dumps(
            {
                "standards": [
                    {
                        "standard_code": "CJJ 1-2008",
                        "standard_name": "城镇道路工程施工与质量验收规范",
                        "official_source": "https://official.example/CJJ-1-2008",
                        "effective_status": "active",
                        "current_version": "CJJ 1-2008",
                        "domain_tags": ["市政道路"],
                        "latest": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    oversized = root / "oversized_compliance.json"
    with oversized.open("wb") as stream:
        stream.truncate(compliance_runtime._MAX_COMPLIANCE_JSON_BYTES + 1)

    original_snapshot = compliance_runtime._read_regular_json_snapshot

    def guarded_snapshot(path: Path, **kwargs):
        if Path(path) == oversized:
            raise AssertionError("oversized clause body must not be opened")
        return original_snapshot(path, **kwargs)

    monkeypatch.setattr(
        compliance_runtime,
        "_read_regular_json_snapshot",
        guarded_snapshot,
    )
    catalog = build_compliance_catalog(root)

    assert catalog["warnings"] == ["compliance_source_oversized:oversized_compliance.json"]
    assert all(
        row.get("path") != "oversized_compliance.json"
        for row in catalog["entries"]
    )
    status = get_compliance_registry_status(root)
    assert "compliance_source_oversized:oversized_compliance.json" in status["warnings"]
    assert query_compliance(
        "道路 质量 验收 记录",
        root=root,
        verified_only=False,
    ) == []
