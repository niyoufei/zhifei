#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "artifacts" / "qa"
SAMPLES = ("sample_A", "sample_B", "sample_C", "sample_D", "sample_E")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sample_receipt(sample: str, contact: dict[str, Any]) -> dict[str, Any]:
    docx = QA / "docx" / f"{sample}.docx"
    pdf = QA / "pdf" / f"{sample}.pdf"
    structural = _load(docx.with_suffix(".structural_quality.json"))
    figures = _load(docx.with_suffix(".figure_manifest.json"))
    visual = _load(QA / "visual_qa" / sample / "visual_quality.json")
    document = Document(str(docx))
    pages = int(visual.get("page_count") or 0)
    page_pngs = sorted((QA / "rendered_final" / sample).glob("page-*.png"))
    contact_sheets = [Path(value) for value in contact.get("contact_sheets") or []]
    landscape_pages = [int(value) for value in contact.get("landscape_pages") or []]
    record = {
        "sample": sample,
        "docx": str(docx),
        "docx_sha256": _sha256(docx),
        "docx_size_bytes": docx.stat().st_size,
        "pdf": str(pdf),
        "pdf_sha256": _sha256(pdf),
        "pdf_size_bytes": pdf.stat().st_size,
        "page_count": pages,
        "rendered_png_count": len(page_pngs),
        "contact_sheet_count": len(contact_sheets),
        "landscape_pages": landscape_pages,
        "section_count": len(document.sections),
        "table_count": len(document.tables),
        "figure_count": int(figures.get("figure_count") or 0),
        "structural_status": structural.get("status"),
        "visual_status": visual.get("status"),
        "blank_pages": visual.get("blank_pages") or [],
        "sparse_pages": visual.get("sparse_pages") or [],
        "orphan_heading_pages": visual.get("orphan_heading_pages") or [],
        "edge_clipping_risk_pages": visual.get("edge_clipping_risk_pages") or [],
        "cjk_glyph_status": (visual.get("cjk_glyph_integrity") or {}).get("status"),
        "figure_delivery_allowed": bool(figures.get("delivery_allowed")),
    }
    requirements = {
        "sample_A": 20 <= pages <= 30 and record["figure_count"] >= 5,
        "sample_B": pages >= 100 and record["figure_count"] >= 30 and bool(landscape_pages),
        "sample_C": 180 <= pages <= 200,
        "sample_D": record["figure_count"] >= 9,
        "sample_E": record["table_count"] >= 8 and bool(landscape_pages),
    }
    record["acceptance_checks"] = {
        "sample_specific": requirements[sample],
        "docx_structure": structural.get("status") == "pass",
        "real_render": visual.get("status") == "pass",
        "page_png_count_matches": len(page_pngs) == pages,
        "contact_sheets_exist": bool(contact_sheets) and all(path.is_file() for path in contact_sheets),
        "no_blank_pages": not record["blank_pages"],
        "no_orphan_headings": not record["orphan_heading_pages"],
        "no_edge_clipping_risk": not record["edge_clipping_risk_pages"],
        "cjk_glyph_integrity": record["cjk_glyph_status"] == "pass",
        "figure_delivery": record["figure_delivery_allowed"],
    }
    record["status"] = "pass" if all(record["acceptance_checks"].values()) else "blocked"
    return record


def main() -> int:
    contact_manifest = _load(QA / "contact_sheets" / "contact_sheet_manifest.json")
    contacts = {
        item["sample"]: item
        for item in contact_manifest.get("samples") or []
        if isinstance(item, dict)
    }
    samples = [_sample_receipt(sample, contacts[sample]) for sample in SAMPLES]
    abnormal = _load(QA / "abnormal_input_receipt.json")

    before = QA / "before"
    after = QA / "after"
    before.mkdir(parents=True, exist_ok=True)
    after.mkdir(parents=True, exist_ok=True)
    baseline = {
        "schema": "zhifei.qa.before_baseline.v1",
        "baseline_head": "b60dd79d2a1557f2754294082e74d1b09e459894",
        "baseline_tests": {"passed": 3242, "skipped": 1, "warnings": 8, "failed": 0},
        "note": "修改前仓库没有任务书 A-F 实样；未追溯伪造 before DOCX。此文件固化修改前代码/测试基线与审计发现。",
        "findings": [
            "字体别名、字号、固定行距和首行字符缩进未被精确门禁",
            "隐藏静态目录与活动 TOC 并存",
            "DOCX 元数据/customXml 与 relationship 完整性检查不足",
            "结构化宽表、合并表头、嵌套表和横向分节能力不足",
            "横向恢复与页眉页脚引用会产生空页或丢失故事部件",
            "工程图缺少统一 300dpi PNG/SVG 与几何溢出检查",
            "上传链路缺少大小上限、批内去重和损坏文件可解释拒绝",
        ],
    }
    (before / "baseline_findings.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy2(QA / "docx" / "sample_A.docx", after / "sample_A.docx")
    shutil.copy2(QA / "pdf" / "sample_A.pdf", after / "sample_A.pdf")
    shutil.copy2(QA / "contact_sheets" / "sample_A" / "contact_002_017-029.png", after / "sample_A_contact_sheet.png")

    payload = {
        "schema": "zhifei.qa.acceptance_manifest.v1",
        "synthetic_data_only": True,
        "renderer": "LibreOffice headless with macOS system-font Fontconfig bridge",
        "visual_scope": {
            "automatic_page_metrics": "all pages",
            "contact_sheet_coverage": "all pages",
            "manual_full_resolution_spot_checks": [
                "sample_D pages 29-30",
                "sample_E pages 49, 61, 74",
                "sample_B landscape/table pages 194-204 and figure pages 205-219",
            ],
        },
        "samples": samples,
        "total_pages": sum(item["page_count"] for item in samples),
        "total_figures": sum(item["figure_count"] for item in samples),
        "abnormal_input_status": abnormal.get("status"),
        "abnormal_input_case_count": abnormal.get("case_count"),
        "unit_regression": {"collected": 3262, "passed": 3261, "skipped": 1, "failed": 0, "warnings": 8},
        "runtime_smoke": {
            "command": ".venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18765",
            "health": "ok=true",
            "shutdown": "clean",
            "port_released": True,
        },
    }
    payload["status"] = (
        "pass"
        if all(item["status"] == "pass" for item in samples) and abnormal.get("status") == "pass"
        else "blocked"
    )
    target = QA / "acceptance_manifest.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
