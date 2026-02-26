#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.v2.kg_paths import resolve_default_kg_root
from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline

BOQ_FILE_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf"}


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


def _boq_candidates(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    files = [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in BOQ_FILE_EXTENSIONS]
    return sorted(files, key=lambda p: str(p))


def _normalize_boq_item(raw: Dict[str, Any], source_file: Path, seq: int) -> Dict[str, Any]:
    name = str(raw.get("name") or "").strip()
    if not name:
        return {}
    return {
        "boq_code": str(raw.get("boq_code") or raw.get("code") or f"AUTO-{seq}"),
        "name": name,
        "quantity": _to_float(raw.get("quantity")),
        "unit": str(raw.get("unit") or "").strip() or None,
        "unit_price": _to_float(raw.get("unit_price")),
        "total_price": _to_float(raw.get("total_price")),
        "source_file": str(source_file),
    }


async def _load_single_boq(path: Path) -> Dict[str, Any]:
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
    normalized_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(payload.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_boq_item(item, path, idx)
        if normalized:
            normalized_items.append(normalized)
    payload["items"] = normalized_items
    payload["source_file"] = str(path)
    payload["stats"] = dict(payload.get("stats") or {})
    payload["stats"]["item_count"] = len(normalized_items)
    payload["stats"]["total_quantity"] = sum(float(it.get("quantity") or 0.0) for it in normalized_items)
    if not payload.get("items"):
        raise ValueError(f"BOQ parsing returned empty items: {path}")
    return payload


def _dedupe_boq_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (
            str(item.get("boq_code") or "").strip().lower(),
            str(item.get("name") or "").strip().lower(),
            float(item.get("quantity") or 0.0),
            str(item.get("unit") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


async def _load_boq_payload(path: Path) -> Dict[str, Any]:
    candidates = _boq_candidates(path)
    if not candidates:
        raise ValueError(f"No BOQ files found under: {path}")

    merged_items: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, str]] = []
    file_item_count: Dict[str, int] = {}
    source_stats: Dict[str, Any] = {}

    for file_path in candidates:
        try:
            payload = await _load_single_boq(file_path)
            items = payload.get("items") or []
            merged_items.extend(items)
            file_item_count[str(file_path)] = len(items)
            source_stats[str(file_path)] = payload.get("stats") or {}
        except Exception as exc:
            parse_errors.append({"file": str(file_path), "error": str(exc)})

    merged_items = _dedupe_boq_items(merged_items)
    if not merged_items:
        raise ValueError(f"BOQ parsing returned empty items for all candidates: {path}; errors={parse_errors}")

    top_quantity_items = sorted(
        merged_items,
        key=lambda it: float(it.get("quantity") or 0.0),
        reverse=True,
    )[:10]

    return {
        "items": merged_items,
        "stats": {
            "item_count": len(merged_items),
            "total_quantity": sum(float(it.get("quantity") or 0.0) for it in merged_items),
            "source_file_count": len(candidates),
            "parsed_file_count": len(file_item_count),
            "failed_file_count": len(parse_errors),
            "file_item_count": file_item_count,
            "source_stats": source_stats,
            "top_quantity_items": top_quantity_items,
        },
        "source_files": [str(p) for p in candidates],
        "parse_errors": parse_errors,
    }


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run V2 engine on a real project (production mode).")
    p.add_argument("--tender", nargs="+", required=True, help="招标文件路径（PDF/Word/TXT等）。")
    p.add_argument("--boq", required=True, help="工程量清单路径（Excel/CSV/PDF 文件，或目录自动合并解析）。")
    p.add_argument(
        "--kg-root",
        default=str(resolve_default_kg_root()),
        help="知识图谱根目录。",
    )
    p.add_argument(
        "--kg-db",
        default="backend/data/autoplan/v2/knowledge_graph.sqlite3",
        help="图谱SQLite索引路径。",
    )
    p.add_argument(
        "--out",
        default="build/real_project_diagnosis.json",
        help="诊断JSON输出路径（不导出Word/PDF）。",
    )
    p.add_argument(
        "--missing-report",
        default="build/Missing_Knowledge_Report.md",
        help="知识盲区体检报告输出路径。",
    )
    p.add_argument(
        "--docx-out",
        default="/Users/youfeini/Desktop/文档生成系统/01_真实项目测试/最终施组草案_带AI审校标记.docx",
        help="最终施组草案DOCX输出路径。",
    )
    p.add_argument(
        "--docx-export",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否导出最终DOCX文档。",
    )
    p.add_argument(
        "--self-heal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="启用知识图谱自愈合Agent并在缺口后自动二次重跑。",
    )
    p.add_argument(
        "--self-heal-provider",
        default=None,
        help="自愈Agent模型提供商（默认自动选择）。",
    )
    p.add_argument(
        "--self-heal-model",
        default=None,
        help="自愈Agent模型名称（默认自动选择）。",
    )
    return p


async def _run(args: argparse.Namespace) -> int:
    tender_paths = [str(Path(p).expanduser().resolve()) for p in (args.tender or [])]
    boq_path = Path(args.boq).expanduser().resolve()
    kg_root = Path(args.kg_root).expanduser().resolve()
    kg_db = Path(args.kg_db).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    report_path = Path(args.missing_report).expanduser().resolve()
    docx_out_path = Path(args.docx_out).expanduser().resolve()

    for tender in tender_paths:
        if not Path(tender).exists():
            raise FileNotFoundError(f"tender file not found: {tender}")
    if not boq_path.exists():
        raise FileNotFoundError(f"boq file not found: {boq_path}")
    if not kg_root.exists():
        raise FileNotFoundError(f"kg root not found: {kg_root}")

    boq_payload = await _load_boq_payload(boq_path)
    pipeline = MultiAgentDocPipeline(
        kg_db_path=kg_db,
        self_healing_provider=args.self_heal_provider,
        self_healing_model=args.self_heal_model,
    )

    result = await pipeline.run(
        tender_paths=tender_paths,
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=output_path,
        missing_report_path=report_path,
        enable_self_healing=bool(args.self_heal),
        enable_docx_export=bool(args.docx_export),
        docx_output_path=docx_out_path,
    )

    audit_agent = (result.get("agents") or {}).get("audit_agent") or {}
    score_audit = audit_agent.get("result") or {}
    graph_audit = audit_agent.get("graph_support") or {}
    gaps = result.get("knowledge_gaps") or []

    print("=== Real Project Penetration Run Completed ===")
    print(f"Tender: {', '.join(tender_paths)}")
    print(f"BOQ: {boq_path}")
    boq_stats = boq_payload.get("stats") or {}
    print(
        "BOQ Parse: "
        f"source_files={int(boq_stats.get('source_file_count') or 0)}, "
        f"parsed={int(boq_stats.get('parsed_file_count') or 0)}, "
        f"failed={int(boq_stats.get('failed_file_count') or 0)}, "
        f"items={int(boq_stats.get('item_count') or 0)}"
    )
    print(f"Diagnosis JSON: {result.get('saved_at')}")
    print(f"Missing_Knowledge_Report: {result.get('missing_knowledge_report')}")
    print(f"Production DOCX: {result.get('docx_output')}")
    print(f"Strict Fail-Fast Intercepted: {result.get('intercepted')}")
    print(f"Score Coverage OK: {bool(score_audit.get('ok'))}")
    print(f"Graph Support OK: {bool(graph_audit.get('ok'))}")
    print(f"Knowledge Gaps: {len(gaps)}")
    evidence_stats = result.get("sentence_evidence_stats") or {}
    if evidence_stats:
        print(
            "Sentence Trace: "
            f"total={int(evidence_stats.get('total_sentences') or 0)}, "
            f"traceable={int(evidence_stats.get('traceable_sentences') or 0)}, "
            f"coverage={float(evidence_stats.get('trace_coverage_ratio') or 0.0):.4f}"
        )
    self_heal = result.get("self_healing") or {}
    if self_heal.get("triggered"):
        print(
            "Self-Healing: "
            f"triggered=True, provider={self_heal.get('llm_provider')}, model={self_heal.get('llm_model')}, "
            f"patch_nodes={self_heal.get('patch_nodes')}, used_fallback={self_heal.get('used_fallback')}"
        )
    else:
        print("Self-Healing: triggered=False")

    for i, gap in enumerate(gaps[:20], start=1):
        gtype = str(gap.get("type") or "")
        dim = str(gap.get("dimension") or "")
        kw = "、".join([str(x) for x in (gap.get("required_keywords") or [])[:6]])
        q = str(gap.get("query") or "")
        print(f"GAP[{i}] {gtype} | {dim} | {kw} | query={q}")

    parse_errors = boq_payload.get("parse_errors") or []
    for i, err in enumerate(parse_errors[:10], start=1):
        print(f"BOQ_PARSE_ERROR[{i}] {err.get('file')} | {err.get('error')}")

    return 0


def main() -> int:
    parser = _arg_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
