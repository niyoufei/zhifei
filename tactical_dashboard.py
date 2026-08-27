#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import csv
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.v2.data_graph_ingestion import ingest_knowledge_graph, search_graph_index
from backend.zhifei_autoplan.v2.index_matrix_engine import IndexMatrixEngine
from backend.zhifei_autoplan.v2.kg_paths import resolve_default_kg_root
from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline

DEFAULT_KG_ROOT = str(resolve_default_kg_root())
DEFAULT_DB_PATH = "backend/data/autoplan/v2/tactical_graph.sqlite3"
DEFAULT_BUILD_ROOT = Path("build/tactical_dashboard")
DEFAULT_BUILD_ROOT.mkdir(parents=True, exist_ok=True)


st.set_page_config(page_title="智飞战术指挥舱", page_icon="🛰️", layout="wide")


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
        "total_quantity": sum(float(it.get("quantity") or 0.0) for it in items),
    }
    return {"items": items, "stats": stats}


async def _load_boq_payload(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        payload = _load_boq_csv(path)
    else:
        parser = BoQParser()
        items, stats = await parser.parse(str(path))
        payload = {"items": [it.model_dump() for it in items], "stats": stats}

    if not payload.get("items"):
        raise ValueError(f"BOQ parsing returned empty items: {path}")
    return payload


def _read_text_for_trigger(path: Path) -> str:
    engine = IndexMatrixEngine()
    try:
        info = engine._read_source_text(str(path))
        return str(info.get("text") or "")
    except Exception:
        return ""


def _save_uploaded_file(uploaded: Any, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / uploaded.name
    out.write_bytes(uploaded.getvalue())
    return out


def _format_trigger_log(node: Dict[str, Any], keyword: str) -> str:
    node_id = str(node.get("payload", {}).get("node_id") or node.get("node_id") or "Unknown-Node")
    shield = node.get("competitor_shield") or {}
    booster = node.get("qt_score_booster") or {}
    trap_logic = str(shield.get("trap_logic") or shield.get("argument") or "防御护盾已部署")
    score_weight = str(booster.get("score_weight") or "+1")
    return (
        f"识别到关键词‘{keyword}’，已触发 {node_id} 节点，"
        f"已部署竞争护盾（{trap_logic}），预计得分 {score_weight}"
    )


def _collect_tactical_nodes(db_path: str, top_k: int = 200) -> List[Dict[str, Any]]:
    result = search_graph_index(
        query="",
        top_k=top_k,
        db_path=db_path,
        resolve_authority=False,
    )
    nodes: List[Dict[str, Any]] = []
    for item in result.get("results") or []:
        strategy = item.get("bid_response_strategy") or {}
        shield = item.get("competitor_shield") or {}
        booster = item.get("qt_score_booster") or {}
        is_tactical = bool(strategy or shield or booster or str(item.get("tactical_mode") or "").strip())
        if is_tactical:
            nodes.append(item)
    return nodes


def _render_graph_board(nodes: List[Dict[str, Any]]) -> None:
    trap_count = 0
    booster_count = 0
    rows: List[Dict[str, Any]] = []

    for node in nodes:
        shield = node.get("competitor_shield") or {}
        booster = node.get("qt_score_booster") or {}
        strategy = node.get("bid_response_strategy") or {}
        trap_logic = str(shield.get("trap_logic") or "").strip()
        if trap_logic:
            trap_count += 1
        if booster:
            booster_count += 1

        rows.append(
            {
                "node_id": node.get("payload", {}).get("node_id") or node.get("node_id"),
                "title": node.get("title"),
                "dna_verified": node.get("dna_verified"),
                "tactical_mode": node.get("tactical_mode"),
                "trigger_keywords": "、".join(strategy.get("trigger_keywords") or []),
                "trap_logic": trap_logic,
                "score_booster": str(booster.get("score_weight") or ""),
                "source_file": node.get("source_file"),
            }
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Tactical Nodes", len(nodes))
    c2.metric("Trap Logic", trap_count)
    c3.metric("Score Booster", booster_count)

    st.dataframe(rows, width="stretch", height=420)


def _stream_trigger_logs(tender_text: str, nodes: List[Dict[str, Any]]) -> List[str]:
    matched_logs: List[str] = []
    tender_lower = (tender_text or "").lower()

    sidebar_box = st.sidebar.empty()
    log_lines: List[str] = []

    for node in nodes:
        strategy = node.get("bid_response_strategy") or {}
        trigger_keywords = [str(k).strip() for k in (strategy.get("trigger_keywords") or []) if str(k).strip()]
        if not trigger_keywords:
            continue

        matched = None
        for kw in trigger_keywords:
            if kw.lower() in tender_lower:
                matched = kw
                break
        if not matched:
            continue

        msg = _format_trigger_log(node, matched)
        matched_logs.append(msg)
        log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sidebar_box.code("\n".join(log_lines[-18:]), language="text")
        time.sleep(0.08)

    if not matched_logs:
        msg = "未识别到战术关键词触发，已回退基础施工策略。"
        log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sidebar_box.code("\n".join(log_lines), language="text")

    return matched_logs


async def _run_pipeline(
    *,
    tender_path: Path,
    boq_path: Path,
    kg_root: Path,
    db_path: str,
    run_dir: Path,
    activation_context: str,
) -> Dict[str, Any]:
    boq_payload = await _load_boq_payload(boq_path)
    pipeline = MultiAgentDocPipeline(kg_db_path=Path(db_path))

    out_json = run_dir / "v2_tactical_output.json"
    out_report = run_dir / "Missing_Knowledge_Report.md"

    return await pipeline.run(
        tender_paths=[str(tender_path)],
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=out_json,
        missing_report_path=out_report,
        activation_context=activation_context,
        enable_self_healing=False,
        enable_docx_export=False,
    )


st.title("智飞战术指挥舱")
st.caption("V2 Tactical KG + Multi-Agent Pipeline")

with st.sidebar:
    st.subheader("运行配置")
    kg_root_raw = st.text_input("知识图谱目录", value=DEFAULT_KG_ROOT)
    db_path = st.text_input("图谱索引库", value=DEFAULT_DB_PATH)

kg_root = Path(kg_root_raw).expanduser().resolve()

left, right = st.columns([1.1, 1.4])

with left:
    st.subheader("模块 A - 战术图谱看板")
    if st.button("加载战术图谱", width="stretch"):
        if not kg_root.exists():
            st.error(f"知识图谱目录不存在: {kg_root}")
        else:
            with st.spinner("正在入库并加载战术节点..."):
                report = ingest_knowledge_graph(kg_root, db_path=db_path)
                nodes = _collect_tactical_nodes(db_path=db_path)
                st.session_state["tactical_nodes"] = nodes
                st.session_state["graph_report"] = report
            st.success(f"加载完成：{report.get('nodes_indexed')} 节点（本次解析）")

    report_cached = st.session_state.get("graph_report") or {}
    if report_cached:
        st.json(report_cached)

    tactical_nodes = st.session_state.get("tactical_nodes") or []
    if tactical_nodes:
        _render_graph_board(tactical_nodes)

with right:
    st.subheader("模块 B - 智能施组生成")

    tender_file = st.file_uploader(
        "上传招标文件（PDF/DOCX/TXT/MD）",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=False,
    )
    boq_file = st.file_uploader(
        "上传工程量清单（XLSX/XLS/CSV/PDF）",
        type=["xlsx", "xls", "csv", "pdf"],
        accept_multiple_files=False,
    )

    if st.button("启动战术生成", type="primary", width="stretch"):
        if tender_file is None or boq_file is None:
            st.error("请先上传招标文件和工程量清单。")
        elif not kg_root.exists():
            st.error(f"知识图谱目录不存在: {kg_root}")
        else:
            run_dir = DEFAULT_BUILD_ROOT / time.strftime("run_%Y%m%d_%H%M%S")
            run_dir.mkdir(parents=True, exist_ok=True)

            tender_path = _save_uploaded_file(tender_file, run_dir)
            boq_path = _save_uploaded_file(boq_file, run_dir)

            tender_text = _read_text_for_trigger(tender_path)
            ingest_knowledge_graph(
                kg_root,
                db_path=db_path,
                activation_context=tender_text,
            )
            tactical_nodes = _collect_tactical_nodes(db_path=db_path)
            st.session_state["tactical_nodes"] = tactical_nodes

            st.sidebar.subheader("战术触发状态")
            matched_logs = _stream_trigger_logs(tender_text, tactical_nodes)

            with st.spinner("多 Agent 流水线运行中..."):
                result = asyncio.run(
                    _run_pipeline(
                        tender_path=tender_path,
                        boq_path=boq_path,
                        kg_root=kg_root,
                        db_path=db_path,
                        run_dir=run_dir,
                        activation_context=tender_text,
                    )
                )

            st.success("流程完成")
            st.write(
                {
                    "output_json": result.get("saved_at"),
                    "missing_report": result.get("missing_knowledge_report"),
                    "intercepted": result.get("intercepted"),
                    "knowledge_gaps": len(result.get("knowledge_gaps") or []),
                    "triggered_tactics": len(matched_logs),
                }
            )

            st.subheader("核心章节草案（预览）")
            for section in (result.get("sections") or [])[:8]:
                title = section.get("title")
                content = str(section.get("content") or "").strip()
                if not content:
                    continue
                with st.expander(str(title), expanded=False):
                    st.write(content)

            report_path = result.get("missing_knowledge_report")
            if report_path and Path(str(report_path)).exists():
                report_text = Path(str(report_path)).read_text(encoding="utf-8", errors="ignore")
                st.subheader("Missing_Knowledge_Report.md")
                st.code(report_text[:6000], language="markdown")
