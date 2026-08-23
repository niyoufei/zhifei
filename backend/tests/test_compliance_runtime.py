from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.compliance_runtime import (
    build_compliance_catalog,
    get_compliance_registry_status,
    list_verified_standard_metadata,
    query_compliance,
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


def test_verified_only_requires_official_source_and_active_status(tmp_path: Path):
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

    hits = query_compliance(
        "检验批 验收 记录",
        domain_tags=["房建工程"],
        top_k=8,
        verified_only=True,
        root=root,
    )
    assert hits
    assert {str(hit.get("standard_code")) for hit in hits} == {"GB_50300_2024"}
    assert all(hit.get("official_source") for hit in hits)


def test_missing_registry_root_is_read_only(tmp_path: Path):
    root = tmp_path / "missing" / "compliance"
    status = get_compliance_registry_status(root)
    assert status["ready"] is False
    assert status["warnings"] == ["compliance_root_missing"]
    assert not root.exists()


def test_official_registry_hydrates_matching_local_clause_source(tmp_path: Path):
    root = tmp_path / "compliance"
    root.mkdir(parents=True, exist_ok=True)
    _write_compliance_file(
        root / "road_compliance.json",
        standard_code="CJJ 1-2008",
        domain_tag="市政道路",
        source_name="本地规范条文",
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
    assert cat["verified_count"] == 1
    rows = list_verified_standard_metadata(domain_tags=["市政道路"], root=root)
    assert len(rows) == 1
    assert rows[0]["standard_code"] == "CJJ 1-2008"
    assert rows[0]["metadata_only"] is False
    hits = query_compliance(
        "道路 质量 验收 记录",
        domain_tags=["市政道路"],
        verified_only=True,
        root=root,
    )
    assert hits
    assert {row["standard_code"] for row in hits} == {"CJJ 1-2008"}


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
