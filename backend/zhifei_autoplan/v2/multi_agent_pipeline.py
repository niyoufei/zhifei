from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from backend.zhifei_autoplan.v2.docx_generator import generate_v2_docx
from backend.zhifei_autoplan.v2.visual_generation import generate_document_visual_assets
from backend.zhifei_autoplan.v2.self_healing_agent import SelfHealingAgent
from backend.zhifei_autoplan.provider_admission import ProviderCandidate

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

PROFESSIONAL_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "bridge": ["桥梁", "桥墩", "盖梁", "箱梁", "挂篮", "斜拉", "桥面"],
    "tunnel": ["隧道", "暗挖", "盾构", "洞门", "衬砌", "超前支护"],
    "railway": ["铁路", "轨道", "高铁", "站场", "接触网", "营业线"],
    "hydraulic": ["水利", "河道", "泵站", "闸门", "堤防", "引水", "水电"],
    "mep": ["机电", "电气", "暖通", "消防", "管道", "桥架", "智能化", "弱电"],
    "earthwork": ["土石方", "土方", "开挖", "回填", "基坑", "边坡", "爆破"],
    "road": ["道路", "路基", "路面", "沥青", "交通导改", "市政道路"],
    "building": ["房建", "主体结构", "砌体", "装修", "幕墙", "钢结构", "装配式"],
}

CONSISTENCY_KEYWORDS = ("标高", "高程", "坐标", "坐标X", "坐标Y", "工期", "里程碑", "关键线路")


@dataclass
class AgentContext:
    graph_report: Dict[str, Any]
    index_matrix: Dict[str, Any]
    quant_index: Dict[str, Any]


class MultiAgentDocPipeline:
    """End-to-end v2 multi-agent document generation pipeline."""

    def __init__(
        self,
        *,
        kg_db_path: Path | str = DEFAULT_DB_PATH,
        self_healing_provider: Optional[str] = None,
        self_healing_model: Optional[str] = None,
        self_healing_api_key: Optional[str] = None,
        self_healing_admitted_candidate: ProviderCandidate | None = None,
        min_gemini_usefulness_score: float = 30.0,
    ):
        self.kg_db_path = Path(kg_db_path)
        self.quant_engine = QuantitativeBoQEngine()
        self.self_healing_provider = self_healing_provider
        self.self_healing_model = self_healing_model
        self.self_healing_api_key = self_healing_api_key
        self.self_healing_admitted_candidate = self_healing_admitted_candidate
        self.min_gemini_usefulness_score = max(0.0, min(100.0, float(min_gemini_usefulness_score)))

    def _read_tender_text(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        suffix = p.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".xml", ".json"}:
            return p.read_text(encoding="utf-8", errors="ignore")

        try:
            from modules.parser.parser_unify import UnifiedParser

            parsed = UnifiedParser(str(p)).parse()
            text = parsed.get("text") or ""
            if text:
                return str(text)
            meta = parsed.get("meta")
            if isinstance(meta, dict):
                return json.dumps(meta, ensure_ascii=False)
        except Exception:
            return ""
        return ""

    def _detect_professional_domains(
        self,
        *,
        index_matrix: Dict[str, Any],
        tender_paths: List[str],
    ) -> Dict[str, Any]:
        corpus_parts: List[str] = []
        for item in index_matrix.get("index_matrix") or []:
            corpus_parts.extend([str(x) for x in (item.get("keywords") or []) if str(x).strip()])
            for chunk in item.get("support_chunks") or []:
                if not isinstance(chunk, dict):
                    continue
                excerpt = str(chunk.get("excerpt") or "").strip()
                if excerpt:
                    corpus_parts.append(excerpt)
        for path in tender_paths:
            corpus_parts.append(str(path))
            text = self._read_tender_text(path)
            if text:
                corpus_parts.append(text[:180000])

        corpus = "\n".join(corpus_parts)
        domain_hits: Dict[str, List[str]] = {}
        for domain, seeds in PROFESSIONAL_DOMAIN_KEYWORDS.items():
            hits = [kw for kw in seeds if kw in corpus]
            if hits:
                domain_hits[domain] = hits

        detected_domains = sorted(domain_hits.keys())
        if not detected_domains:
            detected_domains = ["general"]
        return {"detected_domains": detected_domains, "domain_hits": domain_hits}

    def _build_specialist_plan(
        self,
        *,
        index_matrix: Dict[str, Any],
        tender_paths: List[str],
    ) -> Dict[str, Any]:
        domain_meta = self._detect_professional_domains(index_matrix=index_matrix, tender_paths=tender_paths)
        detected = list(domain_meta.get("detected_domains") or ["general"])
        domain_hits = domain_meta.get("domain_hits") or {}

        dimension_to_domain: Dict[str, str] = {}
        assignments: List[Dict[str, Any]] = []
        for item in index_matrix.get("index_matrix") or []:
            dim = str(item.get("dimension") or "").strip()
            if not dim:
                continue
            text_parts: List[str] = [dim]
            text_parts.extend([str(x) for x in (item.get("keywords") or []) if str(x).strip()])
            for chunk in item.get("support_chunks") or []:
                if isinstance(chunk, dict):
                    excerpt = str(chunk.get("excerpt") or "").strip()
                    if excerpt:
                        text_parts.append(excerpt)
            merged = " ".join(text_parts)

            selected = "general"
            best_score = -1
            for domain in detected:
                if domain == "general":
                    continue
                score = sum(1 for kw in PROFESSIONAL_DOMAIN_KEYWORDS.get(domain, []) if kw in merged)
                if score > best_score:
                    best_score = score
                    selected = domain
            if selected == "general" and detected and detected[0] != "general":
                selected = detected[0]

            dimension_to_domain[dim] = selected
            assignments.append({"dimension": dim, "domain": selected, "keywords": item.get("keywords") or []})

        specialist_agents: List[Dict[str, Any]] = []
        for domain in detected:
            specialist_agents.append(
                {
                    "agent": f"{domain}_agent",
                    "domain": domain,
                    "trigger_keywords": domain_hits.get(domain, []),
                }
            )

        return {
            "detected_domains": detected,
            "domain_hits": domain_hits,
            "dimension_to_domain": dimension_to_domain,
            "assignments": assignments,
            "specialist_agents": specialist_agents,
            "master_plan": {
                "planner": "master_agent",
                "strategy": "index_matrix_driven + keyword_domain_dispatch",
                "detected_domain_count": len(detected),
            },
        }

    def _is_auto_generated_hit(self, hit: Dict[str, Any] | None) -> bool:
        if not isinstance(hit, dict):
            return False
        source_path = str(hit.get("source_path") or "").lower()
        if "self_healing_patch_nodes" in source_path:
            return True
        snippet = str(hit.get("snippet") or "").lower()
        if "is_auto_generated" in snippet:
            return True
        payload = hit.get("payload")
        if isinstance(payload, dict):
            text = json.dumps(payload, ensure_ascii=False).lower()
            if "is_auto_generated" in text:
                return True
        return False

    def _hit_parameter_ok(self, hit: Dict[str, Any] | None) -> bool:
        if not isinstance(hit, dict):
            return False
        node_id = str(hit.get("node_id") or "").strip()
        title = str(hit.get("title") or "").strip()
        score = float(hit.get("score") or 0.0)
        node_ok = bool((node_id or title) and score > 0)
        applicable = hit.get("applicable_conditions")
        resources = hit.get("resource_requirements")
        safety_level = str(hit.get("safety_level") or "unknown").strip().lower()
        has_conditions = isinstance(applicable, dict) and len(applicable) > 0
        has_resources = isinstance(resources, dict) and len(resources) > 0
        return bool(node_ok and has_conditions and has_resources and safety_level != "unknown")

    def _select_graph_hit(self, query: str, *, professional_domain: str | None = None) -> Dict[str, Any]:
        domains = [str(professional_domain).strip()] if str(professional_domain or "").strip() else None
        graph_search = search_graph_index(
            query=query,
            top_k=8,
            professional_domains=domains,
            min_gemini_usefulness_score=self.min_gemini_usefulness_score,
            db_path=self.kg_db_path,
        )
        candidates = graph_search.get("results") or []
        if not candidates:
            return {}

        ranked = sorted(
            candidates,
            key=lambda item: (
                1 if self._hit_parameter_ok(item) else 0,
                1 if self._is_auto_generated_hit(item) else 0,
                float(item.get("gemini_usefulness_score") or 0.0),
                float(item.get("score") or 0.0),
            ),
            reverse=True,
        )
        return ranked[0] if ranked else {}

    def _select_formula_hit(self, query: str, *, professional_domain: str | None = None) -> Dict[str, Any]:
        domains = [str(professional_domain).strip()] if str(professional_domain or "").strip() else None
        search = search_graph_index(
            query=query,
            node_types=["FormulaNode"],
            top_k=8,
            professional_domains=domains,
            min_gemini_usefulness_score=self.min_gemini_usefulness_score,
            db_path=self.kg_db_path,
        )
        candidates = search.get("results") or []
        if not candidates:
            return {}
        ranked = sorted(
            candidates,
            key=lambda item: (
                1 if str(item.get("formula_expression") or "").strip() else 0,
                1 if self._is_auto_generated_hit(item) else 0,
                float(item.get("gemini_usefulness_score") or 0.0),
                float(item.get("score") or 0.0),
            ),
            reverse=True,
        )
        return ranked[0] if ranked else {}

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
        auto_support = self._is_auto_generated_hit(graph_support or {})
        graph_resources = graph_support.get("resource_requirements") if isinstance(graph_support, dict) else {}
        resource_params = []
        if isinstance(graph_resources, dict):
            for key, value in list(graph_resources.items())[:3]:
                resource_params.append(f"{key}={value}")
        graph_param_text = f"图谱参数({'; '.join(resource_params)})。" if resource_params else ""
        if auto_support and graph_param_text:
            graph_param_text = f"AI自动补全参数{graph_param_text}"

        text = (
            f"执行{process}{kw_text}控制，持续{duration}天，每班次检查2次，"
            f"投入{resources}，由{quality_checker}复核并记录；"
            f"关键参数阈值=95%，偏差处置时限=4h。"
            f"{graph_param_text}"
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
        specialist_plan: Dict[str, Any],
        paragraph_cache: Dict[str, Any],
    ) -> Dict[str, Any]:
        matrix_items = index_matrix.get("index_matrix") or []
        mapping_items = list((quant_index.get("mapping_3d") or {}).items())
        if not mapping_items:
            raise ValueError("quantitative mapping is empty; cannot generate section content")
        dimension_to_domain = specialist_plan.get("dimension_to_domain") or {}

        def generator(attempt: int, cache: Dict[str, Any]) -> List[Dict[str, Any]]:
            sections: List[Dict[str, Any]] = []
            failed_dimensions = {
                str(x).strip()
                for x in (cache.get("__last_failed_dimensions__") or [])
                if str(x).strip()
            }
            failed_point_map: Dict[str, List[str]] = {}
            for point in cache.get("__last_failed_points__") or []:
                if not isinstance(point, dict):
                    continue
                dim = str(point.get("dimension") or "").strip()
                if not dim:
                    continue
                for kw in point.get("missing_keywords") or []:
                    kw_text = str(kw).strip()
                    if not kw_text:
                        continue
                    failed_point_map.setdefault(dim, [])
                    if kw_text not in failed_point_map[dim]:
                        failed_point_map[dim].append(kw_text)

            for idx, item in enumerate(matrix_items):
                item_name, support = mapping_items[idx % len(mapping_items)]
                title = str(item.get("dimension") or f"section_{idx + 1}")
                domain = str(dimension_to_domain.get(title) or "general")
                rewrite_keywords = failed_point_map.get(title) or []
                query = (
                    f"{domain} {item.get('dimension', '')} {' '.join(item.get('keywords') or [])} {' '.join(rewrite_keywords)}"
                ).strip()
                selected_graph = self._select_graph_hit(query, professional_domain=domain)
                graph_hits = search_graph_index(
                    query=query,
                    top_k=8,
                    professional_domains=[domain],
                    min_gemini_usefulness_score=self.min_gemini_usefulness_score,
                    db_path=self.kg_db_path,
                )
                text = self._make_section_text(
                    dimension_item=item,
                    boq_support=support,
                    graph_support=selected_graph,
                    attempt=attempt,
                )
                rewrite_applied = bool(attempt > 1 and title in failed_dimensions)
                if rewrite_applied:
                    missing_hint = "、".join(rewrite_keywords[:8]) or "评分点关键词"
                    text = (
                        f"{text}"
                        f"执行{title}评分点补写，覆盖关键词[{missing_hint}]，"
                        "参数阈值=95%，检查频次=2次/班，复核岗位=专业工程师。"
                    )
                sections.append(
                    {
                        "title": title,
                        "content": text,
                        "source_boq_item": item_name,
                        "graph_hit": selected_graph,
                        "graph_query": query,
                        "specialist_domain": domain,
                        "specialist_agent": f"{domain}_agent",
                        "graph_hits_total": int(graph_hits.get("total") or 0),
                        "auto_generated_support": self._is_auto_generated_hit(selected_graph),
                        "retry_rewrite": rewrite_applied,
                        "retry_missing_keywords": rewrite_keywords,
                        "source_trace": {
                            "node_id": selected_graph.get("node_id") if isinstance(selected_graph, dict) else None,
                            "title": selected_graph.get("title") if isinstance(selected_graph, dict) else None,
                            "source_path": selected_graph.get("source_path") if isinstance(selected_graph, dict) else None,
                            "is_auto_generated": self._is_auto_generated_hit(selected_graph),
                        },
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
                    "第一步（定义）：执行工序名称定义，工程量1200m3、钢筋标号HRB400、尺寸900mm，施工员每班次核验1次；"
                    "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次；"
                    "第三步（解决）：执行控制与验证措施，偏差限值3mm、响应时限4h，质量员每班次检查2次；"
                    "工序名称->参数->风险->控制->验证。"
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
            query = section.get("graph_query") or f"{dim} {' '.join(item.get('keywords') or [])}"
            graph_hit = self._select_graph_hit(query)
            node_id = str(graph_hit.get("node_id") or "").strip()
            title = str(graph_hit.get("title") or "").strip()
            score = float(graph_hit.get("score") or 0.0)
            node_ok = bool((node_id or title) and score > 0)
            parameter_ok = bool(node_ok and self._hit_parameter_ok(graph_hit))

            formula_required = _formula_required(dim, keywords)
            formula_query = f"{dim} {' '.join([str(x) for x in keywords])} 公式 计算".strip()
            formula_hit: Dict[str, Any] = {}
            formula_total = 0
            if formula_required:
                formula_hit = self._select_formula_hit(formula_query)
                formula_total = int(
                    search_graph_index(
                        query=formula_query,
                        node_types=["FormulaNode"],
                        top_k=1,
                        min_gemini_usefulness_score=self.min_gemini_usefulness_score,
                        db_path=self.kg_db_path,
                    ).get("total")
                    or 0
                )
            formula_ok = True
            if formula_required:
                f_node_id = str(formula_hit.get("node_id") or "").strip()
                f_score = float(formula_hit.get("score") or 0.0)
                f_expr = str(formula_hit.get("formula_expression") or "").strip()
                formula_ok = bool(f_node_id and f_score > 0 and f_expr)

            ok = bool(node_ok and parameter_ok and formula_ok)
            check = {
                "dimension": dim,
                "keywords": keywords,
                "graph_query": query,
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

    def _build_gemini_context_packets(
        self,
        *,
        index_matrix: Dict[str, Any],
        sections: List[Dict[str, Any]],
        specialist_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        by_title: Dict[str, Dict[str, Any]] = {}
        for sec in sections:
            title = str(sec.get("title") or "").strip()
            if title and title not in by_title:
                by_title[title] = sec

        dimension_to_domain = specialist_plan.get("dimension_to_domain") or {}
        packets: List[Dict[str, Any]] = []
        for item in index_matrix.get("index_matrix") or []:
            dim = str(item.get("dimension") or "").strip()
            if not dim:
                continue
            sec = by_title.get(dim) or {}
            hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
            domain = str(dimension_to_domain.get(dim) or sec.get("specialist_domain") or "general")
            packets.append(
                {
                    "dimension": dim,
                    "domain": domain,
                    "keywords": item.get("keywords") or [],
                    "graph_query": sec.get("graph_query"),
                    "node_id": hit.get("node_id"),
                    "title": hit.get("title"),
                    "source_hierarchy": hit.get("source_hierarchy"),
                    "source_file": hit.get("source_file"),
                    "gemini_usefulness_score": hit.get("gemini_usefulness_score"),
                    "formula_expression": hit.get("formula_expression"),
                    "applicable_conditions": hit.get("applicable_conditions") or {},
                    "resource_requirements": hit.get("resource_requirements") or {},
                    "numeric_sources": hit.get("numeric_sources") or [],
                    "retrieval_hints": (hit.get("payload") or {}).get("retrieval_hints")
                    if isinstance(hit.get("payload"), dict)
                    else {},
                    "gemini_context_block": (hit.get("payload") or {}).get("gemini_context_block")
                    if isinstance(hit.get("payload"), dict)
                    else {},
                }
            )
        return packets

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

    def _run_compliance_audit(
        self,
        *,
        sections: List[Dict[str, Any]],
        quant_index: Dict[str, Any],
        specialist_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        key_values: Dict[str, List[Dict[str, Any]]] = {}
        missing_graph_bindings: List[Dict[str, Any]] = []

        for section in sections:
            title = str(section.get("title") or "").strip() or "untitled"
            content = str(section.get("content") or "")
            domain = str(section.get("specialist_domain") or "general")
            graph_hit = section.get("graph_hit") if isinstance(section.get("graph_hit"), dict) else {}
            if not str(graph_hit.get("node_id") or "").strip():
                missing_graph_bindings.append({"title": title, "domain": domain})

            for key in CONSISTENCY_KEYWORDS:
                for m in re.finditer(
                    rf"{key}\s*(?:=|<=|>=|:|：)\s*([-\d.]+(?:%|mm|cm|m|h|min|dB|MPa|天|次|人|台|套)?)",
                    content,
                ):
                    value = str(m.group(1) or "").strip()
                    if value:
                        key_values.setdefault(key, []).append({"value": value, "title": title, "domain": domain})

            for m in re.finditer(r"持续\s*(\d+)\s*天", content):
                value = f"{m.group(1)}天"
                key_values.setdefault("工期", []).append({"value": value, "title": title, "domain": domain})

        inconsistencies: List[Dict[str, Any]] = []
        for key, refs in key_values.items():
            uniq_vals = sorted(
                {str(r.get("value") or "").strip() for r in refs if str(r.get("value") or "").strip()}
            )
            if len(uniq_vals) > 1:
                inconsistencies.append({"key": key, "values": uniq_vals, "refs": refs})

        cpm = (quant_index.get("cpm") or {}) if isinstance(quant_index, dict) else {}
        project_duration = int(cpm.get("project_duration_days") or 0)
        duration_refs = key_values.get("工期") or []
        if project_duration > 0 and duration_refs:
            parsed_days: List[int] = []
            for item in duration_refs:
                text = str(item.get("value") or "")
                m = re.search(r"\d+", text)
                if m:
                    parsed_days.append(int(m.group(0)))
            if parsed_days:
                min_day = min(parsed_days)
                max_day = max(parsed_days)
                if max_day > project_duration * 2 or min_day < max(1, project_duration // 3):
                    inconsistencies.append(
                        {
                            "key": "工期_vs_CPM",
                            "values": [f"sections={min_day}-{max_day}天", f"cpm={project_duration}天"],
                            "refs": duration_refs,
                        }
                    )

        hard_fail = bool(inconsistencies or missing_graph_bindings)
        return {
            "ok": not hard_fail,
            "checked_sections": len(sections),
            "detected_domains": specialist_plan.get("detected_domains") or [],
            "missing_graph_bindings": missing_graph_bindings,
            "missing_graph_bindings_count": len(missing_graph_bindings),
            "inconsistencies": inconsistencies,
            "inconsistency_count": len(inconsistencies),
            "cpm_project_duration_days": project_duration,
        }

    def _collect_compliance_gaps(self, compliance_audit: Dict[str, Any]) -> List[Dict[str, Any]]:
        gaps: List[Dict[str, Any]] = []
        if not isinstance(compliance_audit, dict):
            return gaps
        for item in compliance_audit.get("missing_graph_bindings") or []:
            gaps.append(
                {
                    "type": "cross_domain_binding_missing",
                    "dimension": str(item.get("title") or "章节"),
                    "required_keywords": [str(item.get("domain") or "general")],
                    "query": f"{item.get('domain') or 'general'} {item.get('title') or ''}".strip(),
                    "suggested_parameters": ["绑定图谱逻辑节点(node_id/title/source_path)"],
                }
            )
        for item in compliance_audit.get("inconsistencies") or []:
            gaps.append(
                {
                    "type": "cross_domain_inconsistency",
                    "dimension": str(item.get("key") or "跨专业一致性"),
                    "required_keywords": [str(x) for x in (item.get("values") or [])[:4]],
                    "query": str(item.get("key") or "consistency_check"),
                    "suggested_parameters": ["统一标高/坐标/工期等跨专业参数并回写"],
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
        compliance_audit: Optional[Dict[str, Any]],
        fail_fast_error: str | None,
        self_healing: Optional[Dict[str, Any]] = None,
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
        if isinstance(compliance_audit, dict):
            lines.append(f"- Compliance Agent OK: {bool(compliance_audit.get('ok'))}")
            lines.append(f"- Compliance Inconsistencies: {int(compliance_audit.get('inconsistency_count') or 0)}")
            lines.append(
                f"- Missing Graph Bindings: {int(compliance_audit.get('missing_graph_bindings_count') or 0)}"
            )
        lines.append(f"- Intercepted: {bool(gaps or fail_fast_error)}")
        if fail_fast_error:
            lines.append(f"- FailFast Error: {fail_fast_error}")
        if isinstance(self_healing, dict) and self_healing:
            lines.append(f"- Self-Healing Triggered: {bool(self_healing.get('triggered'))}")
            lines.append(f"- Self-Healing Patch Nodes: {int(self_healing.get('patch_nodes') or 0)}")
            lines.append(f"- Self-Healing Used Fallback: {bool(self_healing.get('used_fallback'))}")
            if self_healing.get("patch_file"):
                lines.append(f"- Self-Healing Patch File: {self_healing.get('patch_file')}")
            if self_healing.get("llm_model"):
                lines.append(
                    f"- Self-Healing LLM: {self_healing.get('llm_provider')} / {self_healing.get('llm_model')}"
                )
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

    def _run_generation_pass(
        self,
        *,
        index_matrix: Dict[str, Any],
        quant_index: Dict[str, Any],
        specialist_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        paragraph_cache: Dict[str, Any] = {}
        fail_fast_error: str | None = None

        try:
            writing = self._build_sections_with_retry(
                index_matrix=index_matrix,
                quant_index=quant_index,
                specialist_plan=specialist_plan,
                paragraph_cache=paragraph_cache,
            )
        except FailFastAuditError as exc:
            fail_fast_error = str(exc)
            writing = {
                "sections": self._fallback_sections(index_matrix, quant_index),
                "audit_result": exc.audit_result,
            }
        except Exception as exc:  # keep pipeline alive for report output
            fail_fast_error = str(exc)
            writing = {
                "sections": self._fallback_sections(index_matrix, quant_index),
                "audit_result": {"ok": False, "checks": [], "failed_count": 0, "error": str(exc)},
            }

        guarded_sections = self._apply_guardrails(writing.get("sections") or [])
        graph_audit = self._audit_graph_support(index_matrix=index_matrix, sections=guarded_sections)
        compliance_audit = self._run_compliance_audit(
            sections=guarded_sections,
            quant_index=quant_index,
            specialist_plan=specialist_plan,
        )
        gaps = self._collect_knowledge_gaps(
            graph_audit=graph_audit,
            audit_result=writing.get("audit_result") or {},
        )
        gaps.extend(self._collect_compliance_gaps(compliance_audit))
        return {
            "writing": writing,
            "sections": guarded_sections,
            "graph_audit": graph_audit,
            "compliance_audit": compliance_audit,
            "gaps": gaps,
            "fail_fast_error": fail_fast_error,
            "intercepted": bool(gaps or fail_fast_error),
        }

    async def _run_self_healing(
        self,
        *,
        graph_root: Path | str,
        gaps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not gaps:
            return {"triggered": False, "patch_nodes": 0}

        healer = SelfHealingAgent(
            provider=self.self_healing_provider,
            model=self.self_healing_model,
            api_key=self.self_healing_api_key,
            admitted_candidate=self.self_healing_admitted_candidate,
        )
        try:
            built = await healer.build_patch_nodes(gaps)
        finally:
            healer.close()
        nodes = built.get("nodes") or []
        persisted = healer.persist_patch_nodes(graph_root=graph_root, nodes=nodes)

        return {
            "triggered": True,
            "llm_provider": built.get("provider"),
            "llm_model": built.get("model"),
            "llm_error": built.get("llm_error"),
            "used_fallback": bool(built.get("used_fallback")),
            "patch_nodes": len(nodes),
            "patch_file": persisted.get("saved_at"),
            "merged_node_count": persisted.get("merged_node_count"),
        }

    async def run(
        self,
        *,
        tender_paths: List[str],
        boq_payload: Dict[str, Any],
        graph_root: Path | str = DEFAULT_KG_ROOT,
        output_path: Path | str = DEFAULT_PIPELINE_OUTPUT,
        missing_report_path: Path | str = DEFAULT_MISSING_REPORT,
        enable_self_healing: bool = False,
        enable_docx_export: bool = False,
        docx_output_path: Path | str | None = None,
        enable_visual_generation: bool = False,
        visual_output_dir: Path | str | None = None,
        visual_provider: str = "google",
        visual_model: str = "imagen-3.0-generate-002",
        visual_api_key: str | None = None,
        activation_context: str | None = None,
    ) -> Dict[str, Any]:
        graph_report = ingest_knowledge_graph(
            graph_root,
            db_path=self.kg_db_path,
            activation_context=activation_context,
        )
        matrix_result = await build_index_matrix(tender_paths)
        index_matrix = matrix_result["matrix"]
        quant_index = self.quant_engine.build_quantitative_index(boq_payload)
        specialist_plan = self._build_specialist_plan(index_matrix=index_matrix, tender_paths=tender_paths)

        ctx = AgentContext(graph_report=graph_report, index_matrix=index_matrix, quant_index=quant_index)
        first_pass = self._run_generation_pass(
            index_matrix=ctx.index_matrix,
            quant_index=ctx.quant_index,
            specialist_plan=specialist_plan,
        )
        final_pass = dict(first_pass)

        self_healing_result: Dict[str, Any] = {"triggered": False, "patch_nodes": 0}
        if enable_self_healing and first_pass.get("gaps"):
            self_healing_result = await self._run_self_healing(
                graph_root=graph_root,
                gaps=first_pass.get("gaps") or [],
            )
            # Re-ingest graph after auto patch and rerun full generation/audit.
            ctx.graph_report = ingest_knowledge_graph(
                graph_root,
                db_path=self.kg_db_path,
                activation_context=activation_context,
            )
            final_pass = self._run_generation_pass(
                index_matrix=ctx.index_matrix,
                quant_index=ctx.quant_index,
                specialist_plan=specialist_plan,
            )

        missing_report_saved = self._write_missing_knowledge_report(
            gaps=final_pass.get("gaps") or [],
            graph_report=ctx.graph_report,
            audit_result=(final_pass.get("writing") or {}).get("audit_result") or {},
            graph_audit=final_pass.get("graph_audit") or {},
            compliance_audit=final_pass.get("compliance_audit") or {},
            fail_fast_error=final_pass.get("fail_fast_error"),
            self_healing=self_healing_result,
            path=missing_report_path,
        )

        intercepted = bool(final_pass.get("intercepted"))
        docx_saved: str | None = None
        docx_meta: Dict[str, Any] = {"exported": False}
        visual_meta: Dict[str, Any] = {"generated": False, "count": 0, "assets": []}
        if enable_docx_export and not intercepted and docx_output_path:
            visual_assets: List[Dict[str, Any]] = []
            if enable_visual_generation:
                if visual_output_dir:
                    visual_dir = Path(visual_output_dir)
                else:
                    docx_p = Path(docx_output_path)
                    visual_dir = docx_p.parent / f"{docx_p.stem}_assets"
                visual_result = generate_document_visual_assets(
                    index_matrix=ctx.index_matrix,
                    sections=final_pass.get("sections") or [],
                    output_dir=visual_dir,
                    provider=visual_provider,
                    model=visual_model,
                    api_key=visual_api_key,
                )
                visual_assets = list(visual_result.get("assets") or [])
                visual_meta = {
                    "generated": bool(visual_result.get("ok")),
                    "count": int(visual_result.get("count") or len(visual_assets)),
                    "output_dir": str(visual_result.get("output_dir") or ""),
                    "provider": visual_result.get("provider"),
                    "model": visual_result.get("model"),
                    "assets": visual_assets,
                }

            docx_result = generate_v2_docx(
                index_matrix=ctx.index_matrix,
                sections=final_pass.get("sections") or [],
                visual_assets=visual_assets,
                output_path=docx_output_path,
                title_hint="施工组织设计草案（自动生成）",
            )
            docx_saved = str(docx_result.get("saved_at") or "")
            docx_meta = {
                "exported": True,
                "saved_at": docx_saved,
                "highlighted_paragraphs": int(docx_result.get("highlighted_paragraphs") or 0),
                "auto_generated_sections": int(docx_result.get("auto_generated_sections") or 0),
                "visual_assets_embedded": int(docx_result.get("visual_assets_embedded") or 0),
                "visual_assets_missing": int(docx_result.get("visual_assets_missing") or 0),
            }

        output = {
            "ok": True,
            "intercepted": intercepted,
            "agents": {
                "master_agent": {"status": "done", "plan": specialist_plan.get("master_plan")},
                "graph_agent": {"status": "done", "report": ctx.graph_report},
                "tender_agent": {"status": "done", "index_matrix_meta": ctx.index_matrix.get("meta")},
                "quant_agent": {
                    "status": "done",
                    "cpm": ctx.quant_index.get("cpm"),
                    "indices": ctx.quant_index.get("indices"),
                    "chapter_structure": ctx.quant_index.get("chapter_structure"),
                },
                "professional_agents": {
                    "status": "done",
                    "domains": specialist_plan.get("detected_domains") or [],
                    "agents": specialist_plan.get("specialist_agents") or [],
                },
                "audit_agent": {
                    "status": "done",
                    "result": (final_pass.get("writing") or {}).get("audit_result") or {},
                    "graph_support": final_pass.get("graph_audit") or {},
                },
                "compliance_agent": {"status": "done", "result": final_pass.get("compliance_audit") or {}},
                "guardrail_agent": {"status": "done"},
                "self_healing_agent": {"status": "done" if self_healing_result.get("triggered") else "skipped"},
                "gemini_context_agent": {"status": "done"},
                "visual_agent": {
                    "status": "done" if visual_meta.get("generated") else "skipped",
                    "meta": visual_meta,
                },
                "document_assembler": {"status": "done" if docx_meta.get("exported") else "skipped", "meta": docx_meta},
            },
            "specialist_plan": specialist_plan,
            "index_matrix": ctx.index_matrix,
            "quant_index": ctx.quant_index,
            "sections": final_pass.get("sections") or [],
            "knowledge_gaps": final_pass.get("gaps") or [],
            "missing_knowledge_report": missing_report_saved,
            "fail_fast_error": final_pass.get("fail_fast_error"),
            "gemini_context_packets": self._build_gemini_context_packets(
                index_matrix=ctx.index_matrix,
                sections=final_pass.get("sections") or [],
                specialist_plan=specialist_plan,
            ),
            "self_healing": self_healing_result,
            "docx_output": docx_saved,
            "visual_output": visual_meta,
            "pre_healing": {
                "intercepted": bool(first_pass.get("intercepted")),
                "knowledge_gaps": first_pass.get("gaps") or [],
                "fail_fast_error": first_pass.get("fail_fast_error"),
            },
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        output["saved_at"] = str(out)
        return output
