#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = re.sub(r"[^\d.\-]+", "", str(value))
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _pick_value(row: Dict[str, Any], aliases: List[str]) -> Any:
    for key in aliases:
        for row_key, row_val in row.items():
            if str(row_key).strip().lower() == key.lower():
                return row_val
    return None


def _load_boq_csv(path: Path) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            name = _pick_value(row, ["name", "项目名称", "清单项目名称", "名称"])
            if not str(name or "").strip():
                continue
            item = {
                "boq_code": str(_pick_value(row, ["boq_code", "code", "清单编码", "编码", "项目编码"]) or f"CSV-{idx}"),
                "name": str(name).strip(),
                "quantity": _to_float(_pick_value(row, ["quantity", "qty", "工程量", "数量"])),
                "unit": str(_pick_value(row, ["unit", "单位", "计量单位"]) or "").strip() or None,
                "unit_price": _to_float(_pick_value(row, ["unit_price", "综合单价", "单价"])),
                "total_price": _to_float(_pick_value(row, ["total_price", "合价", "总价", "金额"])),
            }
            items.append(item)

    stats = {
        "item_count": len(items),
        "total_quantity": sum([float(it.get("quantity") or 0.0) for it in items]),
    }
    return {"items": items, "stats": stats}


async def _load_boq_payload(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        payload = _load_boq_csv(path)
    else:
        parser = BoQParser()
        items, stats = await parser.parse(str(path))
        payload = {
            "items": [it.model_dump() for it in items],
            "stats": stats,
        }
    if not payload.get("items"):
        raise ValueError(f"BOQ parsing returned empty items: {path}")
    return payload


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v2 multi-agent simulation end-to-end.")
    parser.add_argument(
        "--tender",
        nargs="+",
        required=True,
        help="Path(s) to tender files (PDF/DOCX/TXT/MD supported by parser).",
    )
    parser.add_argument(
        "--boq",
        required=True,
        help="Path to BOQ file (XLSX/XLS/PDF/CSV).",
    )
    parser.add_argument(
        "--kg-root",
        default="/Users/youfeini/Desktop/文档生成系统/知识图谱",
        help="Knowledge graph root directory.",
    )
    parser.add_argument(
        "--kg-db",
        default="backend/data/autoplan/v2/knowledge_graph.sqlite3",
        help="SQLite path for KG index database.",
    )
    parser.add_argument(
        "--out",
        default="build/v2_simulation_output.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--missing-report",
        default="build/Missing_Knowledge_Report.md",
        help="Missing knowledge report output path.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    tender_paths = [str(Path(p).expanduser().resolve()) for p in (args.tender or [])]
    boq_path = Path(args.boq).expanduser().resolve()
    kg_root = Path(args.kg_root).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    report_path = Path(args.missing_report).expanduser().resolve()

    for tender in tender_paths:
        if not Path(tender).exists():
            raise FileNotFoundError(f"tender file not found: {tender}")
    if not boq_path.exists():
        raise FileNotFoundError(f"boq file not found: {boq_path}")
    if not kg_root.exists():
        raise FileNotFoundError(f"kg root not found: {kg_root}")

    boq_payload = await _load_boq_payload(boq_path)
    pipeline = MultiAgentDocPipeline(kg_db_path=Path(args.kg_db))

    result = await pipeline.run(
        tender_paths=tender_paths,
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=output_path,
        missing_report_path=report_path,
    )

    print("=== V2 Simulation Completed ===")
    print(f"Output JSON: {result.get('saved_at')}")
    print(f"Missing Report: {result.get('missing_knowledge_report')}")
    print(f"Sections: {len(result.get('sections') or [])}")
    print(f"Intercepted: {result.get('intercepted')}")
    print(f"Knowledge Gaps: {len(result.get('knowledge_gaps') or [])}")
    print(f"Audit Score Coverage OK: {bool(((result.get('agents') or {}).get('audit_agent') or {}).get('result', {}).get('ok'))}")
    print(f"Audit Graph Support OK: {bool(((result.get('agents') or {}).get('audit_agent') or {}).get('graph_support', {}).get('ok'))}")

    for idx, gap in enumerate((result.get("knowledge_gaps") or [])[:8], start=1):
        dim = gap.get("dimension")
        gtype = gap.get("type")
        kw = "、".join([str(x) for x in (gap.get("required_keywords") or [])[:5]])
        print(f"GAP[{idx}] {gtype} | {dim} | {kw}")

    return 0


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
