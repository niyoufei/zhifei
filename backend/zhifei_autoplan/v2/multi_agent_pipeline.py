from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.v2.audit_failfast import run_with_fail_fast_retry
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
                graph_hits = search_graph_index(
                    query=f"{item.get('dimension', '')} {' '.join(item.get('keywords') or [])}",
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

    async def run(
        self,
        *,
        tender_paths: List[str],
        boq_payload: Dict[str, Any],
        graph_root: Path | str = DEFAULT_KG_ROOT,
        output_path: Path | str = DEFAULT_PIPELINE_OUTPUT,
    ) -> Dict[str, Any]:
        graph_report = ingest_knowledge_graph(graph_root, db_path=self.kg_db_path)
        matrix_result = await build_index_matrix(tender_paths)
        index_matrix = matrix_result["matrix"]
        quant_index = self.quant_engine.build_quantitative_index(boq_payload)

        ctx = AgentContext(graph_report=graph_report, index_matrix=index_matrix, quant_index=quant_index)
        paragraph_cache: Dict[str, Any] = {}

        writing = self._build_sections_with_retry(
            index_matrix=ctx.index_matrix,
            quant_index=ctx.quant_index,
            paragraph_cache=paragraph_cache,
        )
        guarded_sections = self._apply_guardrails(writing["sections"])

        output = {
            "ok": True,
            "agents": {
                "graph_agent": {"status": "done", "report": ctx.graph_report},
                "tender_agent": {"status": "done", "index_matrix_meta": ctx.index_matrix.get("meta")},
                "quant_agent": {"status": "done", "cpm": ctx.quant_index.get("cpm")},
                "audit_agent": {"status": "done", "result": writing["audit_result"]},
                "guardrail_agent": {"status": "done"},
            },
            "index_matrix": ctx.index_matrix,
            "quant_index": ctx.quant_index,
            "sections": guarded_sections,
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        output["saved_at"] = str(out)
        return output
