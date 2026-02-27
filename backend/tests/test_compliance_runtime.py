from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.compliance_runtime import build_compliance_catalog, query_compliance


def _write_compliance_file(
    path: Path,
    *,
    standard_code: str,
    domain_tag: str,
    source_name: str,
    clause_text: str,
    generated_at: str,
) -> None:
    payload = {
        "graph_track": "compliance",
        "metadata": {
            "source_name": source_name,
            "standard_code": standard_code,
            "domain_tag": domain_tag,
            "generated_at": generated_at,
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

