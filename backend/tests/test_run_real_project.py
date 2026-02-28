from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "run_real_project.py"
    spec = importlib.util.spec_from_file_location("run_real_project", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_boq_payload_can_merge_directory_csv_files(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "a.csv").write_text(
        "boq_code,name,quantity,unit\nA01,土方开挖,100,m3\nA02,钢筋工程,20,t\n",
        encoding="utf-8",
    )
    (boq_dir / "b.csv").write_text(
        "boq_code,name,quantity,unit\nA01,土方开挖,100,m3\nA03,模板工程,300,m2\n",
        encoding="utf-8",
    )

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    assert isinstance(payload.get("items"), list)
    assert len(payload["items"]) == 3  # one duplicate row should be deduped
    assert int((payload.get("stats") or {}).get("source_file_count") or 0) == 2
    assert int((payload.get("stats") or {}).get("failed_file_count") or 0) == 0


def test_load_boq_payload_keeps_running_when_some_files_fail(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "ok.csv").write_text(
        "boq_code,name,quantity,unit\nB01,机电管线安装,260,m\n",
        encoding="utf-8",
    )
    # Invalid PDF content to force parser failure; merge should continue.
    (boq_dir / "broken.pdf").write_text("not-a-real-pdf", encoding="utf-8")

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    stats = payload.get("stats") or {}
    assert int(stats.get("item_count") or 0) >= 1
    assert int(stats.get("source_file_count") or 0) == 2
    assert int(stats.get("failed_file_count") or 0) == 1
    assert len(payload.get("parse_errors") or []) == 1


def test_load_boq_payload_filters_extreme_numeric_outliers(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "outlier.csv").write_text(
        "boq_code,name,quantity,unit,unit_price,total_price\n"
        "C01,异常数量项,1221118015682100400000000000000000000000000000,m3,999,1221118015682100400000000000000000000000000000\n"
        "C02,正常数量项,120,m3,56,6720\n",
        encoding="utf-8",
    )

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    items = payload.get("items") or []
    by_code = {str(it.get("boq_code")): it for it in items}
    assert "C01" not in by_code  # outlier row should be dropped
    assert by_code["C02"]["quantity"] == 120.0
    assert by_code["C02"]["total_price"] == 6720.0
    stats = payload.get("stats") or {}
    assert int(stats.get("item_count") or 0) == 1


def test_load_boq_payload_flags_scientific_explosion_values(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "sci.csv").write_text(
        "boq_code,name,quantity,unit,unit_price,total_price\n"
        "D01,科学计数异常,1.23E+42,m3,5.0E+11,6.15E+53\n"
        "D02,正常项,80,m3,66,5280\n",
        encoding="utf-8",
    )

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    items = payload.get("items") or []
    by_code = {str(it.get("boq_code")): it for it in items}
    assert "D01" not in by_code  # fully invalid numeric row should be dropped as noise
    assert by_code["D02"]["quantity"] == 80.0
    stats = payload.get("stats") or {}
    assert int(stats.get("item_count") or 0) == 1


def test_build_boq_governance_and_review_queue_report(tmp_path: Path) -> None:
    mod = _load_module()
    payload = {
        "items": [{"boq_code": "X1", "name": "测试项", "quantity": 10, "unit": "m3"}],
        "stats": {
            "source_file_count": 2,
            "source_stats": {
                str(tmp_path / "a.csv"): {
                    "item_count": 10,
                    "anomaly_count": 5,
                    "valid_quantity_count": 6,
                    "valid_price_count": 4,
                    "fallback_used": False,
                    "anomaly_items": [{"boq_code": "A1", "name": "异常1", "anomalies": ["quantity_scientific_explosion"]}],
                },
                str(tmp_path / "b.pdf"): {
                    "item_count": 6,
                    "anomaly_count": 0,
                    "valid_quantity_count": 6,
                    "valid_price_count": 6,
                    "fallback_used": True,
                    "anomaly_items": [],
                },
            },
            "file_item_count": {str(tmp_path / "a.csv"): 10, str(tmp_path / "b.pdf"): 6},
        },
        "parse_errors": [{"file": str(tmp_path / "broken.pdf"), "error": "parse failed"}],
    }
    gov = mod._build_boq_governance(boq_payload=payload, trust_threshold=0.78)
    assert gov["enabled"] is True
    assert isinstance(gov.get("file_scores"), list)
    assert int(gov.get("manual_review_total") or 0) >= 1
    report = mod._write_boq_manual_review_report(gov, output_path=tmp_path / "queue.md")
    assert Path(report).exists()
    text = Path(report).read_text(encoding="utf-8")
    assert "BOQ Manual Review Queue" in text


def test_load_boq_payload_emits_parsing_confidence_fields(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "confidence.csv").write_text(
        "boq_code,name,quantity,unit,unit_price,total_price\n"
        "E01,正常项,100,m3,66,6600\n"
        "E02,异常项,1.23E+42,m3,5.0E+11,6.15E+53\n",
        encoding="utf-8",
    )

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    items = payload.get("items") or []
    assert items
    for row in items:
        conf = float(row.get("parsing_confidence") or 0.0)
        assert 0.0 <= conf <= 1.0
        assert str(row.get("confidence_level") or "") in {"high", "medium", "low"}
    stats = payload.get("stats") or {}
    source_stats = stats.get("source_stats") or {}
    assert source_stats
    first_file = next(iter(source_stats.values()))
    assert "avg_parsing_confidence" in first_file


def test_extract_pdf_row_from_line_supports_codeless_rows() -> None:
    mod = _load_module()
    row = mod._extract_pdf_row_from_line("主体结构钢筋绑扎 1200 t 5600 6720000", parse_route="pdf_text")
    assert isinstance(row, dict)
    assert row.get("name") == "主体结构钢筋绑扎"
    assert str(row.get("quantity")) == "1200"
    assert str(row.get("unit")).lower() in {"t", "吨"}


def test_normalize_boq_item_soft_price_penalty_for_quantity_only_pdf(tmp_path: Path) -> None:
    mod = _load_module()
    normalized = mod._normalize_boq_item(
        {
            "boq_code": "A-01",
            "name": "土方开挖",
            "quantity": "860",
            "unit": "m3",
            "_parse_route": "pdf_text",
        },
        tmp_path / "boq.pdf",
        1,
        file_price_optional=True,
    )
    assert normalized
    assert "missing_price_pair_soft" in (normalized.get("anomalies") or [])
    assert float(normalized.get("parsing_confidence") or 0.0) > 0.6


def test_normalize_retrieval_domain_label_maps_file_stem() -> None:
    mod = _load_module()
    assert mod._normalize_retrieval_domain_label("ZF-KG-09-Landscape-Master.json") == "road"
    assert mod._normalize_retrieval_domain_label("ZF-KG-35-Fire-Protection.json") == "mep"
    assert mod._normalize_retrieval_domain_label("ZF-KG-51-SmartSite-General.json") == "digital"
    assert mod._normalize_retrieval_domain_label("ZF-KG-23-Petrochemical.json") == "mep"


def test_build_retrieval_remediation_plan_and_write_report(tmp_path: Path) -> None:
    mod = _load_module()
    benchmark = {
        "ok": False,
        "total_cases": 10,
        "pass_rate": 0.6,
        "avg_mrr": 0.55,
        "rows": [
            {
                "case_id": "c1",
                "query": "景观 模块化 施工",
                "expected_keywords": ["景观", "施工"],
                "ok": False,
                "domain": "ZF-KG-09-Landscape-Master",
            },
            {
                "case_id": "c2",
                "query": "消防 管网 压力",
                "expected_keywords": ["消防", "压力"],
                "ok": True,
                "domain": "mep",
            },
        ],
    }
    plan = mod._build_retrieval_remediation_plan(
        benchmark=benchmark,
        domain_warnings=[
            {"domain": "road", "raw_domain": "ZF-KG-09-Landscape-Master", "total_cases": 4, "pass_rate": 0.42}
        ],
        quality_warnings=[{"raw_domain": "???", "total_cases": 3, "pass_rate": 0.1}],
        min_domain_pass_rate=0.70,
    )
    assert int(plan.get("domain_warnings_total") or 0) == 1
    assert int(plan.get("domain_quality_warnings_total") or 0) == 1
    first = (plan.get("domain_actions") or [])[0]
    assert str(first.get("domain") or "") == "road"
    assert any("景观" in str(x) for x in (first.get("candidate_keywords") or []))

    out = mod._write_retrieval_remediation_report(plan, output_path=tmp_path / "retrieval_plan.md")
    assert Path(out).exists()
    text = Path(out).read_text(encoding="utf-8")
    assert "KG Retrieval Remediation Report" in text
    assert "Domain Remediation" in text
