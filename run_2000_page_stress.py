#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import platform
import resource
import time
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_DB_PATH = Path("backend/data/autoplan/v2/knowledge_graph_stress.sqlite3")
DEFAULT_OUT_ROOT = Path("build/stress_2000")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _load_boq_csv(path: Path) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            item = {
                "boq_code": str(row.get("boq_code") or f"CSV-{idx}"),
                "name": name,
                "quantity": _to_float(row.get("quantity")),
                "unit": str(row.get("unit") or "").strip() or None,
                "unit_price": _to_float(row.get("unit_price")),
                "total_price": _to_float(row.get("total_price")),
            }
            items.append(item)

    stats = {
        "item_count": len(items),
        "total_quantity": sum(float(it.get("quantity") or 0.0) for it in items),
    }
    return {"items": items, "stats": stats}


def _build_tender_page(page_no: int) -> str:
    idx = page_no % 12
    return (
        f"第{page_no}页 施工组织设计响应条款\n"
        f"质量控制：执行混凝土强度 C35 检测，抽检频次 2次/班，允许偏差 5mm，质量员复核。\n"
        f"安全管理：实施临电巡检，漏保动作电流 30mA，应急响应时限 10min，安全员检查。\n"
        f"进度计划：关键线路节点 N{idx:02d}，最小工序间隔 1天，赶工窗口 4h，施工员跟踪。\n"
        f"环保文明：PM10 控制 <= 150ug/m3，噪声 <= 70dB，喷淋频次 3次/日，环保员核查。\n"
        f"重难点：深基坑监测位移阈值 8mm，监测周期 4h，技术负责人确认。\n"
        f"扣分点：资料遗漏处置时限 2h，闭环复核 1次/日，监理工程师抽查。\n"
    )


def _build_qa_page(page_no: int) -> str:
    return (
        f"第{page_no}页 答疑文件优先条款\n"
        "答疑说明：本项目所有响应以答疑文件为准。\n"
        "质量条款覆写：抽检频次调整为 3次/班；强度标准不低于 C40；责任岗位为质量总监。\n"
        "安全条款覆写：高空作业双人互检，巡检频次 4次/班，响应时限 8min。\n"
        "进度条款覆写：关键里程碑每 7天滚动校核一次，偏差纠偏时限 12h。\n"
    )


def _write_stress_tender(path: Path, *, pages: int) -> int:
    blocks = [_build_tender_page(i) for i in range(1, pages + 1)]
    text = "\n\n".join(blocks)
    path.write_text(text, encoding="utf-8")
    return len(text)


def _write_stress_qa(path: Path, *, pages: int) -> int:
    qa_pages = max(20, int(max(1, pages // 20)))
    blocks = [_build_qa_page(i) for i in range(1, qa_pages + 1)]
    text = "\n\n".join(blocks)
    path.write_text(text, encoding="utf-8")
    return len(text)


def _write_stress_boq(path: Path, *, rows: int) -> None:
    headers = ["boq_code", "name", "quantity", "unit", "unit_price", "total_price"]
    process_names = [
        ("测量放线", "m2", 6.0),
        ("土方开挖", "m3", 42.0),
        ("基础钢筋", "t", 5100.0),
        ("主体混凝土", "m3", 460.0),
        ("机电管线安装", "m", 320.0),
        ("装饰装修", "m2", 180.0),
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for i in range(1, rows + 1):
            base = process_names[(i - 1) % len(process_names)]
            name, unit, price = base
            qty = 100 + (i % 97) * 3
            writer.writerow(
                {
                    "boq_code": f"BOQ-{i:05d}",
                    "name": f"{name}-分项{i:05d}",
                    "quantity": f"{qty}",
                    "unit": unit,
                    "unit_price": f"{price}",
                    "total_price": f"{qty * price:.2f}",
                }
            )


def _max_rss_mb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    rss = float(ru.ru_maxrss)
    # Linux: KB; macOS: bytes
    if platform.system().lower() == "darwin":
        return round(rss / (1024 * 1024), 3)
    return round(rss / 1024, 3)


async def _run(args: argparse.Namespace) -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    run_dir = Path(args.out_root).expanduser().resolve() / f"run_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    tender_path = run_dir / "招标文件_2000页模拟.txt"
    qa_path = run_dir / "答疑文件_覆写条款.txt"
    boq_path = run_dir / "工程量清单_压测.csv"
    diag_out = run_dir / "stress_diagnosis.json"
    report_out = run_dir / "Missing_Knowledge_Report.md"

    tender_chars = _write_stress_tender(tender_path, pages=args.pages)
    qa_chars = _write_stress_qa(qa_path, pages=args.pages)
    _write_stress_boq(boq_path, rows=args.boq_rows)
    boq_payload = _load_boq_csv(boq_path)

    start = time.perf_counter()
    pipeline = MultiAgentDocPipeline(kg_db_path=Path(args.kg_db))
    result = await pipeline.run(
        tender_paths=[str(tender_path), str(qa_path)],
        boq_payload=boq_payload,
        graph_root=Path(args.kg_root).expanduser().resolve(),
        output_path=diag_out,
        missing_report_path=report_out,
        enable_self_healing=bool(args.self_heal),
        enable_docx_export=False,
        activation_context=tender_path.read_text(encoding="utf-8", errors="ignore")[:4000],
    )
    elapsed = round(time.perf_counter() - start, 3)
    peak_rss_mb = _max_rss_mb()

    audit_agent = (result.get("agents") or {}).get("audit_agent") or {}
    score_audit = audit_agent.get("result") or {}
    graph_audit = audit_agent.get("graph_support") or {}

    summary = {
        "ok": bool(result.get("ok")),
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "pages_simulated": int(args.pages),
        "boq_rows": int(args.boq_rows),
        "tender_chars": tender_chars,
        "qa_chars": qa_chars,
        "elapsed_seconds": elapsed,
        "peak_rss_mb": peak_rss_mb,
        "intercepted": bool(result.get("intercepted")),
        "knowledge_gaps": len(result.get("knowledge_gaps") or []),
        "sections_generated": len(result.get("sections") or []),
        "score_coverage_ok": bool(score_audit.get("ok")),
        "graph_support_ok": bool(graph_audit.get("ok")),
        "self_heal_triggered": bool((result.get("self_healing") or {}).get("triggered")),
        "self_heal_patch_nodes": int((result.get("self_healing") or {}).get("patch_nodes") or 0),
        "diagnosis_json": str(result.get("saved_at") or diag_out),
        "missing_report": str(result.get("missing_knowledge_report") or report_out),
        "run_dir": str(run_dir),
    }

    summary_path = run_dir / "Stress_Test_Summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# 2000页施组压测报告",
        "",
        f"- 运行时间: {summary['run_at']}",
        f"- 模拟页数: {summary['pages_simulated']}",
        f"- BOQ行数: {summary['boq_rows']}",
        f"- 招标文本字符数: {summary['tender_chars']}",
        f"- 答疑文本字符数: {summary['qa_chars']}",
        f"- 总耗时(秒): {summary['elapsed_seconds']}",
        f"- 峰值内存(MB): {summary['peak_rss_mb']}",
        f"- Fail-Fast拦截: {summary['intercepted']}",
        f"- 知识盲区数量: {summary['knowledge_gaps']}",
        f"- 评分覆盖通过: {summary['score_coverage_ok']}",
        f"- 图谱支撑通过: {summary['graph_support_ok']}",
        f"- 自愈触发: {summary['self_heal_triggered']}",
        f"- 自愈补丁节点: {summary['self_heal_patch_nodes']}",
        "",
        f"- 诊断结果: {summary['diagnosis_json']}",
        f"- 盲区报告: {summary['missing_report']}",
    ]
    md_path = run_dir / "Stress_Test_Report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print("=== 2000-page stress test completed ===")
    print(f"run_dir={run_dir}")
    print(f"elapsed_seconds={elapsed}")
    print(f"peak_rss_mb={peak_rss_mb}")
    print(f"intercepted={summary['intercepted']}")
    print(f"knowledge_gaps={summary['knowledge_gaps']}")
    print(f"score_coverage_ok={summary['score_coverage_ok']}")
    print(f"graph_support_ok={summary['graph_support_ok']}")
    print(f"summary_json={summary_path}")
    print(f"report_md={md_path}")
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 2000-page simulation stress test for V2 engine.")
    parser.add_argument("--pages", type=int, default=2000, help="Simulated tender pages.")
    parser.add_argument("--boq-rows", type=int, default=2000, help="BOQ CSV rows.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root path.")
    parser.add_argument("--kg-db", default=str(DEFAULT_DB_PATH), help="SQLite db path.")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Stress output root directory.")
    parser.add_argument(
        "--self-heal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable self-healing pass when gaps are detected.",
    )
    return parser


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
