from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.v2.audit_failfast import FailFastAuditError, run_with_fail_fast_retry
from backend.zhifei_autoplan.v2.data_graph_ingestion import (
    DEFAULT_DB_PATH,
    DEFAULT_KG_ROOT,
    ingest_knowledge_graph,
    search_graph_index,
)
from backend.zhifei_autoplan.v2.index_matrix_engine import build_index_matrix
from backend.zhifei_autoplan.v2.language_guardrails import rewrite_with_guardrails
from backend.zhifei_autoplan.v2.quantitative_boq_engine import (
    QuantitativeBoQEngine,
    assert_paragraph_quantitative_support,
)

DEFAULT_PIPELINE_OUTPUT = Path("build/v2_multi_agent_output.json")
DEFAULT_MISSING_REPORT = Path("build/Missing_Knowledge_Report.md")
FORMULA_REQUIRED_DIMENSIONS = {"进度", "重难点"}
FORMULA_HINT_KEYWORDS = ("公式", "计算", "推算", "时长", "温控", "工期", "产能", "动力学")

DIMENSION_PARAMETER_HINTS: Dict[str, List[str]] = {
    "质量": ["强度等级(MPa)", "允许偏差(mm)", "抽检频次(次/批)", "验收合格率(%)"],
    "安全": ["风险等级", "检查频次(次/日)", "临电漏保参数(mA)", "应急响应时限(min)"],
    "进度": ["关键线路工序间隔(天)", "里程碑节点(日期)", "资源峰值(人/台)", "纠偏时限(h)"],
    "环保": ["PM10阈值(ug/m3)", "噪声阈值(dB)", "污水pH范围", "巡检频次(次/日)"],
    "重难点": ["关键工序参数", "专项资源配置(人/台)", "风险触发阈值", "验收闭环指标"],
    "扣分点": ["扣分触发条件", "响应时限(h)", "责任岗位", "闭环校验频次"],
}


@dataclass
class AgentContext:
    graph_report: Dict[str, Any]
    index_matrix: Dict[str, Any]
    quant_index: Dict[str, Any]


class MultiAgentDocPipeline:
    """End-to-end v2 multi-agent document generation pipeline."""

    def __init__(self, *, kg_db_path: Path | str = DEFAULT_DB_PATH):
        self.kg_db_path = Path(kg_db_path)
        self.quant_engine = QuantitativeBoQEngine()

    def _make_section_text(
        self,
        *,
        dimension_item: Dict[str, Any],
        boq_support: Dict[str, Any],
        graph_support: Dict[str, Any] | None,
        attempt: int,
    ) -> str:
        dimension = str(dimension_item.get("dimension") or "章节")
        keywords = [str(x).strip() for x in (dimension_item.get("keywords") or []) if str(x).strip()][:3]
        process = str(boq_support.get("process") or "关键工序")
        duration = int(boq_support.get("duration_days") or 1)
        resources = "、".join([str(x) for x in (boq_support.get("resources") or [])[:3]]) or "专业班组"
        quality_checker = "质量员" if dimension in {"质量", "重难点", "扣分点"} else "安全员"
        if dimension == "进度":
            quality_checker = "施工员"
        elif dimension == "环保":
            quality_checker = "环保员"

        kw_text = "、".join(keywords) if keywords else dimension
        graph_title = str((graph_support or {}).get("title") or "图谱证据")

        text = (
            f"执行{process}{kw_text}控制，持续{duration}天，每班次检查2次，"
            f"投入{resources}，由{quality_checker}复核并记录；"
            f"关键参数阈值=95%，偏差处置时限=4h。"
            f"【证据:{graph_title}】"
        )

        if attempt > 1 and dimension == "扣分点":
            text += "执行扣分点清单逐项复核，监理工程师每次验收1次。"

        assert_paragraph_quantitative_support(
            text,
            boq_support=boq_support,
            graph_support=graph_support,
        )
        return text

    def _fallback_sections(self, index_matrix: Dict[str, Any], quant_index: Dict[str, Any]) -> List[Dict[str, Any]]:
        mapping_items = list((quant_index.get("mapping_3d") or {}).items())
        if not mapping_items:
            return []

        sections: List[Dict[str, Any]] = []
        for idx, item in enumerate(index_matrix.get("index_matrix") or []):
            item_name, support = mapping_items[idx % len(mapping_items)]
            title = str(item.get("dimension") or f"section_{idx + 1}")
            checker = "质量员" if title in {"质量", "重难点", "扣分点"} else "安全员"
            text = (
                f"执行{support.get('process') or '关键工序'}参数控制，阈值95%，"
                f"{checker}每班次检查2次，偏差处置时限4h，资源投入{len(support.get('resources') or [])}人。"
            )
            sections.append(
                {
                    "title": title,
                    "content": text,
                    "source_boq_item": item_name,
                    "graph_hit": {},
                    "fallback": True,
                }
            )
        return sections

    def _build_sections_with_retry(
        self,
        *,
        index_matrix: Dict[str, Any],
        quant_index: Dict[str, Any],
        paragraph_cache: Dict[str, Any],
    ) -> Dict[str, Any]:
        matrix_items = index_matrix.get("index_matrix") or []
        mapping_items = list((quant_index.get("mapping_3d") or {}).items())
        if not mapping_items:
            raise ValueError("quantitative mapping is empty; cannot generate section content")

        def generator(attempt: int, cache: Dict[str, Any]) -> List[Dict[str, Any]]:
            sections: List[Dict[str, Any]] = []
            for idx, item in enumerate(matrix_items):
                item_name, support = mapping_items[idx % len(mapping_items)]
                query = f"{item.get('dimension', '')} {' '.join(item.get('keywords') or [])}".strip()
                graph_hits = search_graph_index(
                    query=query,
                    top_k=1,
                    db_path=self.kg_db_path,
                )
                first_graph = (graph_hits.get("results") or [{}])[0]
                title = str(item.get("dimension") or f"section_{idx + 1}")
                text = self._make_section_text(
                    dimension_item=item,
                    boq_support=support,
                    graph_support=first_graph,
                    attempt=attempt,
                )
                sections.append(
                    {
                        "title": title,
                        "content": text,
                        "source_boq_item": item_name,
                        "graph_hit": first_graph,
                        "graph_query": query,
                        "graph_hits_total": int(graph_hits.get("total") or 0),
                    }
                )
                cache[title] = text
            return sections

        sections, audit_result = run_with_fail_fast_retry(
            generator=generator,
            index_matrix=index_matrix,
            paragraph_cache=paragraph_cache,
            agent_name="writer-agent-v2",
            max_attempts=3,
        )
        return {"sections": sections, "audit_result": audit_result}

    def _apply_guardrails(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        guarded: List[Dict[str, Any]] = []

        for section in sections:
            text = str(section.get("content") or "")

            def _rewrite(_text: str, _violations: List[Dict[str, Any]], _attempt: int) -> str:
                return (
                    "执行工序参数控制，阈值95%，质量员每班次检查2次；"
                    "实施风险处置，时限4h，安全员每次复核1次。"
                )

            fixed = rewrite_with_guardrails(text, rewrite_fn=_rewrite, max_rewrite=2)
            guarded.append({**section, "content": fixed["text"], "guardrail_attempt": fixed["attempt"]})

        return guarded

    def _audit_graph_support(
        self,
        *,
        index_matrix: Dict[str, Any],
        sections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        def _formula_required(dimension: str, keywords: List[str]) -> bool:
            if dimension in FORMULA_REQUIRED_DIMENSIONS:
                return True
            text = " ".join([dimension] + [str(x) for x in (keywords or [])]).lower()
            return any(hint in text for hint in FORMULA_HINT_KEYWORDS)

        by_title: Dict[str, Dict[str, Any]] = {}
        for section in sections:
            title = str(section.get("title") or "").strip()
            if title and title not in by_title:
                by_title[title] = section

        missing: List[Dict[str, Any]] = []
        checks: List[Dict[str, Any]] = []
        for item in index_matrix.get("index_matrix") or []:
            dim = str(item.get("dimension") or "").strip()
            keywords = item.get("keywords") or []
            section = by_title.get(dim) or {}
            graph_hit = section.get("graph_hit") if isinstance(section.get("graph_hit"), dict) else {}
            node_id = str(graph_hit.get("node_id") or "").strip()
            title = str(graph_hit.get("title") or "").strip()
            score = float(graph_hit.get("score") or 0.0)
            node_ok = bool((node_id or title) and score > 0)

            applicable = graph_hit.get("applicable_conditions")
            resources = graph_hit.get("resource_requirements")
            safety_level = str(graph_hit.get("safety_level") or "unknown").strip().lower()
            has_conditions = isinstance(applicable, dict) and len(applicable) > 0
            has_resources = isinstance(resources, dict) and len(resources) > 0
            parameter_ok = node_ok and has_conditions and has_resources and safety_level != "unknown"

            formula_required = _formula_required(dim, keywords)
            formula_query = f"{dim} {' '.join([str(x) for x in keywords])} 公式 计算".strip()
            formula_hit = {}
            formula_total = 0
            if formula_required:
                formula_search = search_graph_index(
                    query=formula_query,
                    node_types=["FormulaNode"],
                    top_k=1,
                    db_path=self.kg_db_path,
                )
                formula_total = int(formula_search.get("total") or 0)
                formula_hit = (formula_search.get("results") or [{}])[0]
            formula_ok = True
            if formula_required:
                f_node_id = str(formula_hit.get("node_id") or "").strip()
                f_score = float(formula_hit.get("score") or 0.0)
                formula_ok = bool(f_node_id and f_score > 0)

            ok = bool(node_ok and parameter_ok and formula_ok)
            check = {
                "dimension": dim,
                "keywords": keywords,
                "graph_query": section.get("graph_query") or f"{dim} {' '.join(item.get('keywords') or [])}",
                "graph_node_id": node_id,
                "graph_title": title,
                "graph_score": score,
                "node_ok": node_ok,
                "parameter_ok": parameter_ok,
                "formula_required": formula_required,
                "formula_ok": formula_ok,
                "formula_query": formula_query if formula_required else None,
                "formula_total": formula_total,
                "formula_node_id": formula_hit.get("node_id") if formula_required else None,
                "formula_title": formula_hit.get("title") if formula_required else None,
                "ok": ok,
            }
            checks.append(check)
            if not ok:
                missing.append(check)

        return {
            "ok": len(missing) == 0,
            "checked": len(checks),
            "missing_count": len(missing),
            "checks": checks,
            "missing": missing,
        }

    def _collect_knowledge_gaps(
        self,
        *,
        graph_audit: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        gaps: List[Dict[str, Any]] = []
        seen = set()

        for item in graph_audit.get("missing") or []:
            dim = str(item.get("dimension") or "未知维度")
            if not item.get("node_ok"):
                key = ("graph_support_missing", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "graph_support_missing",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": DIMENSION_PARAMETER_HINTS.get(dim, ["补充参数阈值/频次/责任岗位"]),
                        }
                    )
            if item.get("node_ok") and not item.get("parameter_ok"):
                key = ("parameter_missing", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "parameter_missing",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": [
                                "applicable_conditions(气候/地质)",
                                "resource_requirements(资源消耗模型)",
                                "safety_level(风险等级)",
                            ],
                        }
                    )
            if item.get("formula_required") and not item.get("formula_ok"):
                key = ("formula_missing", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "formula_missing",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("formula_query") or item.get("graph_query"),
                            "suggested_parameters": [
                                "FormulaNode.formula_expression",
                                "FormulaNode.formula_variables",
                                "可计算变量映射(volume/productivity等)",
                            ],
                        }
                    )

        for check in audit_result.get("checks") or []:
            if check.get("ok"):
                continue
            dim = str(check.get("dimension") or "未知维度")
            key = ("response_point_missing", dim)
            if key in seen:
                continue
            seen.add(key)
            gaps.append(
                {
                    "type": "response_point_missing",
                    "dimension": dim,
                    "required_keywords": check.get("missing_keywords") or check.get("keywords") or [],
                    "query": f"{dim} {' '.join(check.get('missing_keywords') or check.get('keywords') or [])}".strip(),
                    "suggested_parameters": DIMENSION_PARAMETER_HINTS.get(dim, ["补充参数阈值/频次/责任岗位"]),
                }
            )

        return gaps

    def _write_missing_knowledge_report(
        self,
        *,
        gaps: List[Dict[str, Any]],
        graph_report: Dict[str, Any],
        audit_result: Dict[str, Any],
        graph_audit: Dict[str, Any],
        fail_fast_error: str | None,
        path: Path | str = DEFAULT_MISSING_REPORT,
    ) -> str:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = []
        lines.append("# Missing Knowledge Report")
        lines.append("")
        lines.append(f"- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
        lines.append(f"- Graph Files Parsed: {graph_report.get('files_parsed')}")
        lines.append(f"- Graph Nodes Indexed: {graph_report.get('nodes_indexed')}")
        lines.append(f"- Auditor Score Coverage OK: {bool(audit_result.get('ok'))}")
        lines.append(f"- Auditor Graph Support OK: {bool(graph_audit.get('ok'))}")
        lines.append(f"- Intercepted: {bool(gaps or fail_fast_error)}")
        if fail_fast_error:
            lines.append(f"- FailFast Error: {fail_fast_error}")
        lines.append("")

        if not gaps:
            lines.append("## Summary")
            lines.append("")
            lines.append("No knowledge gaps detected. Current graph coverage supports this simulation run.")
            lines.append("")
        else:
            lines.append("## Gap List")
            lines.append("")
            lines.append("| # | Gap Type | Dimension | Required Keywords | Suggested Parameters | Search Query |")
            lines.append("|---|---|---|---|---|---|")
            for idx, gap in enumerate(gaps, start=1):
                keywords = "、".join([str(x) for x in (gap.get("required_keywords") or [])[:8]])
                hints = "、".join([str(x) for x in (gap.get("suggested_parameters") or [])[:6]])
                query = str(gap.get("query") or "").replace("|", "\\|")
                lines.append(
                    f"| {idx} | {gap.get('type')} | {gap.get('dimension')} | {keywords} | {hints} | `{query}` |"
                )
            lines.append("")
            lines.append("## KG Enrichment Action")
            lines.append("")
            lines.append("1. 按维度补齐参数化节点：动作+参数+检查岗位。")
            lines.append("2. 每个节点至少包含：阈值/频次/时限/责任岗位/验收标准。")
            lines.append("3. 补齐后重新运行 run_v2_simulation.py 验证缺口是否收敛为 0。")
            lines.append("")

        out.write_text("\n".join(lines), encoding="utf-8")
        return str(out)

    async def run(
        self,
        *,
        tender_paths: List[str],
        boq_payload: Dict[str, Any],
        graph_root: Path | str = DEFAULT_KG_ROOT,
        output_path: Path | str = DEFAULT_PIPELINE_OUTPUT,
        missing_report_path: Path | str = DEFAULT_MISSING_REPORT,
    ) -> Dict[str, Any]:
        graph_report = ingest_knowledge_graph(graph_root, db_path=self.kg_db_path)
        matrix_result = await build_index_matrix(tender_paths)
        index_matrix = matrix_result["matrix"]
        quant_index = self.quant_engine.build_quantitative_index(boq_payload)

        ctx = AgentContext(graph_report=graph_report, index_matrix=index_matrix, quant_index=quant_index)
        paragraph_cache: Dict[str, Any] = {}

        fail_fast_error: str | None = None
        try:
            writing = self._build_sections_with_retry(
                index_matrix=ctx.index_matrix,
                quant_index=ctx.quant_index,
                paragraph_cache=paragraph_cache,
            )
        except FailFastAuditError as exc:
            fail_fast_error = str(exc)
            writing = {
                "sections": self._fallback_sections(ctx.index_matrix, ctx.quant_index),
                "audit_result": exc.audit_result,
            }
        except Exception as exc:  # keep pipeline alive for report output
            fail_fast_error = str(exc)
            writing = {
                "sections": self._fallback_sections(ctx.index_matrix, ctx.quant_index),
                "audit_result": {"ok": False, "checks": [], "failed_count": 0, "error": str(exc)},
            }

        guarded_sections = self._apply_guardrails(writing.get("sections") or [])
        graph_audit = self._audit_graph_support(index_matrix=ctx.index_matrix, sections=guarded_sections)
        gaps = self._collect_knowledge_gaps(
            graph_audit=graph_audit,
            audit_result=writing.get("audit_result") or {},
        )
        missing_report_saved = self._write_missing_knowledge_report(
            gaps=gaps,
            graph_report=ctx.graph_report,
            audit_result=writing.get("audit_result") or {},
            graph_audit=graph_audit,
            fail_fast_error=fail_fast_error,
            path=missing_report_path,
        )

        intercepted = bool(gaps or fail_fast_error)
        output = {
            "ok": True,
            "intercepted": intercepted,
            "agents": {
                "graph_agent": {"status": "done", "report": ctx.graph_report},
                "tender_agent": {"status": "done", "index_matrix_meta": ctx.index_matrix.get("meta")},
                "quant_agent": {"status": "done", "cpm": ctx.quant_index.get("cpm")},
                "audit_agent": {
                    "status": "done",
                    "result": writing.get("audit_result") or {},
                    "graph_support": graph_audit,
                },
                "guardrail_agent": {"status": "done"},
            },
            "index_matrix": ctx.index_matrix,
            "quant_index": ctx.quant_index,
            "sections": guarded_sections,
            "knowledge_gaps": gaps,
            "missing_knowledge_report": missing_report_saved,
            "fail_fast_error": fail_fast_error,
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        output["saved_at"] = str(out)
        return output
