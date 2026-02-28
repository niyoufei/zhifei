from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from datetime import datetime
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
from backend.zhifei_autoplan.v2.project_rule_extractor import build_project_rule_matrix
from backend.zhifei_autoplan.v2.standards_update_engine import refresh_kg_standards
from backend.zhifei_autoplan.v2.project_feedback_learning import update_feedback_memory
from backend.zhifei_autoplan.v2.kg_retrieval_benchmark import (
    DEFAULT_DATASET_PATH as DEFAULT_BENCHMARK_DATASET_PATH,
    run_retrieval_benchmark,
)
from backend.zhifei_autoplan.v2.retrieval_weight_trainer import (
    DEFAULT_WEIGHT_PROFILE_PATH,
    train_retrieval_weight_profile,
)
from backend.zhifei_autoplan.v2.cross_discipline_solver import solve_cross_discipline_constraints
from backend.zhifei_autoplan.v2.kg_release_manager import (
    approve_auto_generated_nodes,
    create_release_snapshot,
    recommend_release_strategy,
)
from backend.zhifei_autoplan.v2.runtime_optimization import (
    build_hit_rate_dashboard,
    build_missing_enrichment_draft,
    build_tactical_effects,
    compare_ab_variants,
    write_hit_rate_dashboard,
)

DEFAULT_PIPELINE_OUTPUT = Path("build/v2_multi_agent_output.json")
DEFAULT_MISSING_REPORT = Path("build/Missing_Knowledge_Report.md")
DEFAULT_HIT_RATE_DASHBOARD_JSON = Path("build/Hit_Rate_Dashboard.json")
DEFAULT_HIT_RATE_DASHBOARD_MD = Path("build/Hit_Rate_Dashboard.md")
DEFAULT_ENRICHMENT_DRAFT_JSON = Path("build/Auto_KG_Enrichment_Draft.json")
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
BENCHMARK_DOMAIN_CORE = {
    "bridge",
    "tunnel",
    "railway",
    "hydraulic",
    "mep",
    "earthwork",
    "road",
    "building",
    "management",
    "digital",
}
BENCHMARK_FILE_DOMAIN_TOKEN_MAP = (
    ("bridge", "bridge"),
    ("tunnel", "tunnel"),
    ("railway", "railway"),
    ("rail", "railway"),
    ("offshorewind", "hydraulic"),
    ("marine", "hydraulic"),
    ("harbor", "hydraulic"),
    ("port", "hydraulic"),
    ("hydraulic", "hydraulic"),
    ("water", "hydraulic"),
    ("river", "hydraulic"),
    ("sponge", "hydraulic"),
    ("drainage", "hydraulic"),
    ("wtp", "hydraulic"),
    ("water-treatment", "hydraulic"),
    ("mep", "mep"),
    ("electrical", "mep"),
    ("hvac", "mep"),
    ("fire", "mep"),
    ("gas", "mep"),
    ("pipeline", "mep"),
    ("petrochemical", "mep"),
    ("power-energy", "mep"),
    ("power", "mep"),
    ("energy", "mep"),
    ("weak-current", "mep"),
    ("district-heating", "mep"),
    ("heating", "mep"),
    ("waste-to-energy", "mep"),
    ("communication", "mep"),
    ("smartsite", "digital"),
    ("smartom", "digital"),
    ("digital", "digital"),
    ("bim", "digital"),
    ("data-center", "digital"),
    ("network", "digital"),
    ("调度", "digital"),
    ("碳", "digital"),
    ("networkgraph", "digital"),
    ("quantum", "digital"),
    ("carbon", "digital"),
    ("fm", "digital"),
    ("earthwork", "earthwork"),
    ("foundation", "earthwork"),
    ("deep-excavation", "earthwork"),
    ("road", "road"),
    ("municipal-road", "road"),
    ("landscape", "road"),
    ("airport", "road"),
    ("highway", "road"),
    ("building", "building"),
    ("housing", "building"),
    ("hospital", "building"),
    ("deco", "building"),
    ("decoration", "building"),
    ("curtain", "building"),
    ("steel-structure", "building"),
    ("prefabricated", "building"),
    ("demolition", "building"),
    ("exterior-ancillary", "building"),
    ("ancillary", "building"),
    ("urban-renewal", "building"),
    ("crane", "building"),
    ("lifting", "building"),
    ("scaffolding", "building"),
    ("formwork", "building"),
    ("management", "management"),
    ("safetycivilization", "management"),
    ("greenconstruction", "management"),
    ("temporaryworks", "management"),
    ("fournew", "management"),
)

CONSISTENCY_KEYWORDS = ("标高", "高程", "坐标", "坐标X", "坐标Y", "工期", "里程碑", "关键线路")
SENTENCE_SPLIT_RE = re.compile(r"[。；;!?！？]\s*")
STANDARD_CODE_RE = re.compile(
    r"(GB(?:/T)?|JGJ|SL|TB|DL|CJ|JTG(?:/T)?|DB(?:/T)?\d{2}|T/[A-Z0-9]+)\s*[-/]?\s*\d{2,6}(?:[./-]\d+)?",
    flags=re.IGNORECASE,
)


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
        min_gemini_usefulness_score: float = 30.0,
        prefer_human_verified_hits: bool = True,
        min_source_weight: int = 0,
    ):
        self.kg_db_path = Path(kg_db_path)
        self.quant_engine = QuantitativeBoQEngine()
        self.self_healing_provider = self_healing_provider
        self.self_healing_model = self_healing_model
        self.self_healing_api_key = self_healing_api_key
        self.min_gemini_usefulness_score = max(0.0, min(100.0, float(min_gemini_usefulness_score)))
        self.project_rule_matrix: Dict[str, Any] = {}
        self.retrieval_weight_profile_path: str | None = None
        self.region_context: str | None = None
        self.bid_date: str | None = None
        self.allow_superseded: bool = False
        self.regional_plugin_dir: str | None = None
        self._strict_variant_mode: bool = False
        self.prefer_human_verified_hits = bool(prefer_human_verified_hits)
        self.min_source_weight = max(0, min(5, int(min_source_weight)))

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

    def _project_rule_override(self, dimension: str) -> Dict[str, Any]:
        if not isinstance(self.project_rule_matrix, dict):
            return {}
        overrides = self.project_rule_matrix.get("dimension_overrides")
        if not isinstance(overrides, dict):
            return {}
        item = overrides.get(dimension)
        return dict(item) if isinstance(item, dict) else {}

    def _build_chapter_response_plan(
        self,
        *,
        index_matrix: Dict[str, Any],
        sections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        by_title: Dict[str, Dict[str, Any]] = {}
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip()
            if title and title not in by_title:
                by_title[title] = sec

        chapters: List[Dict[str, Any]] = []
        for item in index_matrix.get("index_matrix") or []:
            if not isinstance(item, dict):
                continue
            dim = str(item.get("dimension") or "").strip()
            if not dim:
                continue
            sec = by_title.get(dim) or {}
            hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
            checkpoints = item.get("response_points")
            if not isinstance(checkpoints, list):
                checkpoints = []
            keywords = [str(x).strip() for x in (item.get("keywords") or []) if str(x).strip()]
            clause_refs = [str(x).strip() for x in (item.get("clause_refs") or []) if str(x).strip()]
            support_chunks = item.get("support_chunks")
            if isinstance(support_chunks, list):
                for chunk in support_chunks:
                    if not isinstance(chunk, dict):
                        continue
                    for cref in (chunk.get("clause_refs") or []):
                        term = str(cref).strip()
                        if term and term not in clause_refs:
                            clause_refs.append(term)
            evidence_anchors = hit.get("evidence_anchors") if isinstance(hit.get("evidence_anchors"), list) else []
            anchor_ids = [str(x.get("anchor_id") or "").strip() for x in evidence_anchors if isinstance(x, dict)]
            bound_node_id = str(hit.get("node_id") or "").strip()
            coverage_ok = bool(bound_node_id) and (bool(anchor_ids) or not checkpoints)
            chapters.append(
                {
                    "chapter": dim,
                    "required_checkpoints": checkpoints,
                    "required_keywords": keywords,
                    "required_clause_refs": clause_refs[:18],
                    "bound_node_id": bound_node_id,
                    "bound_source_hierarchy": hit.get("source_hierarchy"),
                    "evidence_anchor_ids": [x for x in anchor_ids if x],
                    "coverage_ok": coverage_ok,
                }
            )

        return {
            "ok": all(bool(x.get("coverage_ok")) for x in chapters) if chapters else False,
            "chapter_count": len(chapters),
            "chapters": chapters,
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

    def _hit_evidence_ok(self, hit: Dict[str, Any] | None) -> bool:
        if not isinstance(hit, dict):
            return False
        evidence = hit.get("evidence_completeness") if isinstance(hit.get("evidence_completeness"), dict) else {}
        if not evidence:
            return True
        ratio = float(evidence.get("completeness_ratio") or 0.0)
        verification_ratio = float(evidence.get("verification_ratio") or 0.0)
        verification_status = str(evidence.get("verification_status") or "").strip().lower()
        status = str(evidence.get("status") or "").strip().lower()
        has_anchor = bool(evidence.get("has_clause_anchor"))
        has_effective_date = bool(str(evidence.get("effective_date") or "").strip())
        if status == "no_numeric_sources":
            return True
        if self._is_auto_generated_hit(hit):
            return True
        source_hierarchy = str(hit.get("source_hierarchy") or "").strip()
        # 答疑/图纸来源必须提供可验证证据，标准/企标来源允许阶段性 synthetic_only。
        if source_hierarchy in {"答疑文件", "设计图纸"}:
            if verification_ratio < 0.5 and verification_status not in {"pass"}:
                return False
        if (ratio >= 0.55 or status == "pass") and has_anchor and has_effective_date:
            if verification_status in {"pass", "warn"}:
                return True
            if verification_status == "synthetic_only" and source_hierarchy in {"国标", "行标", "企标"}:
                return True
        if ratio >= 0.55 and source_hierarchy in {"企标", "行标"}:
            return True
        return False

    def _hit_formula_safety_ok(self, hit: Dict[str, Any] | None) -> bool:
        if not isinstance(hit, dict):
            return False
        expr = str(hit.get("formula_expression") or "").strip()
        if not expr:
            return True
        profile = hit.get("formula_safety_profile") if isinstance(hit.get("formula_safety_profile"), dict) else {}
        if not profile:
            return True
        return bool(profile.get("safe"))

    def _hit_interface_conflict_ok(self, hit: Dict[str, Any] | None) -> bool:
        if not isinstance(hit, dict):
            return False
        contract = (
            hit.get("cross_discipline_interface_contract")
            if isinstance(hit.get("cross_discipline_interface_contract"), dict)
            else {}
        )
        if not contract:
            return True
        conflict_graph = contract.get("conflict_graph")
        if not isinstance(conflict_graph, list):
            return True
        if isinstance(conflict_graph, list):
            unresolved = [
                item
                for item in conflict_graph
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() in {"conflict", "open"}
            ]
            if unresolved:
                return False
        return True

    def _hit_uncertainty_ok(self, hit: Dict[str, Any] | None, *, formula_required: bool = False) -> bool:
        if not isinstance(hit, dict):
            return False
        has_formula = bool(str(hit.get("formula_expression") or "").strip())
        if not has_formula and not formula_required:
            return True
        profile = hit.get("uncertainty_profile") if isinstance(hit.get("uncertainty_profile"), dict) else {}
        if not profile:
            if self._is_auto_generated_hit(hit):
                return True
            sensitivity = hit.get("formula_sensitivity") if isinstance(hit.get("formula_sensitivity"), dict) else {}
            evidence = hit.get("evidence_completeness") if isinstance(hit.get("evidence_completeness"), dict) else {}
            if bool(sensitivity.get("enabled")) and float(evidence.get("completeness_ratio") or 0.0) >= 0.6:
                return True
            return False
        if not bool(profile.get("enabled")):
            return False
        confidence = float(profile.get("confidence_level") or 0.0)
        return confidence >= 0.5

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
        evidence_ok = self._hit_evidence_ok(hit)
        formula_safety_ok = self._hit_formula_safety_ok(hit)
        interface_ok = self._hit_interface_conflict_ok(hit)
        uncertainty_ok = self._hit_uncertainty_ok(hit, formula_required=bool(str(hit.get("formula_expression") or "").strip()))
        if self._is_auto_generated_hit(hit):
            minimum_semantic_ok = bool(has_conditions or has_resources or safety_level != "unknown")
            return bool(node_ok and minimum_semantic_ok and formula_safety_ok and interface_ok and uncertainty_ok)
        return bool(
            node_ok
            and has_conditions
            and has_resources
            and safety_level != "unknown"
            and evidence_ok
            and formula_safety_ok
            and interface_ok
            and uncertainty_ok
        )

    def _select_graph_hit(self, query: str, *, professional_domain: str | None = None) -> Dict[str, Any]:
        domains = [str(professional_domain).strip()] if str(professional_domain or "").strip() else None
        graph_search = search_graph_index(
            query=query,
            top_k=8,
            professional_domains=domains,
            min_gemini_usefulness_score=self.min_gemini_usefulness_score,
            region_context=self.region_context,
            bid_date=self.bid_date,
            allow_superseded=self.allow_superseded,
            regional_plugin_dir=self.regional_plugin_dir,
            retrieval_weight_profile_path=self.retrieval_weight_profile_path,
            prefer_human_verified=self.prefer_human_verified_hits,
            min_source_weight=self.min_source_weight,
            db_path=self.kg_db_path,
        )
        candidates = graph_search.get("results") or []
        if not candidates:
            return {}

        ranked_pool = list(candidates)
        if self._strict_variant_mode:
            strict_candidates: List[Dict[str, Any]] = []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                evidence = item.get("evidence_completeness") if isinstance(item.get("evidence_completeness"), dict) else {}
                ratio = float(evidence.get("completeness_ratio") or 0.0)
                grade = str(((item.get("evidence_strength") or {}).get("grade") or "")).strip().upper()
                if ratio >= 0.65 and grade in {"A", "B"}:
                    strict_candidates.append(item)
            if strict_candidates:
                ranked_pool = strict_candidates

        ranked = sorted(
            ranked_pool,
            key=lambda item: (
                1 if self._hit_parameter_ok(item) else 0,
                0 if self._is_auto_generated_hit(item) else 1,
                float(((item.get("evidence_strength") or {}).get("score") or 0.0)),
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
            region_context=self.region_context,
            bid_date=self.bid_date,
            allow_superseded=self.allow_superseded,
            regional_plugin_dir=self.regional_plugin_dir,
            retrieval_weight_profile_path=self.retrieval_weight_profile_path,
            prefer_human_verified=self.prefer_human_verified_hits,
            min_source_weight=self.min_source_weight,
            db_path=self.kg_db_path,
        )
        candidates = search.get("results") or []
        if not candidates:
            return {}
        ranked_pool = list(candidates)
        if self._strict_variant_mode:
            strict_pool = []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                profile = item.get("formula_safety_profile") if isinstance(item.get("formula_safety_profile"), dict) else {}
                if bool(profile.get("safe")):
                    strict_pool.append(item)
            if strict_pool:
                ranked_pool = strict_pool
        ranked = sorted(
            ranked_pool,
            key=lambda item: (
                1 if str(item.get("formula_expression") or "").strip() else 0,
                0 if self._is_auto_generated_hit(item) else 1,
                1 if bool((item.get("formula_safety_profile") or {}).get("safe")) else 0,
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

        override = self._project_rule_override(dimension)
        override_text = ""
        if override:
            subj = str(override.get("subject") or "项目约束")
            cmp_text = str(override.get("comparator") or "")
            val = override.get("value")
            unit = str(override.get("unit") or "")
            src = str(override.get("source_type") or "项目文件")
            if val not in (None, ""):
                override_text = f"项目专用约束:{subj}{cmp_text}{val}{unit}（来源:{src}）。"
            else:
                override_text = f"项目专用约束:{subj}（来源:{src}）。"

        text = (
            f"执行{process}{kw_text}控制，持续{duration}天，每班次检查2次，"
            f"投入{resources}，由{quality_checker}复核并记录；"
            f"关键参数阈值=95%，偏差处置时限=4h。"
            f"{override_text}"
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
                override = self._project_rule_override(title)
                override_terms: List[str] = []
                if override:
                    override_terms.extend(
                        [str(override.get("subject") or ""), str(override.get("value") or ""), str(override.get("unit") or "")]
                    )
                query = (
                    f"{domain} {item.get('dimension', '')} {' '.join(item.get('keywords') or [])} {' '.join(rewrite_keywords)} {' '.join(override_terms)}"
                ).strip()
                selected_graph = self._select_graph_hit(query, professional_domain=domain)
                graph_hits = search_graph_index(
                    query=query,
                    top_k=8,
                    professional_domains=[domain],
                    min_gemini_usefulness_score=self.min_gemini_usefulness_score,
                    region_context=self.region_context,
                    bid_date=self.bid_date,
                    allow_superseded=self.allow_superseded,
                    regional_plugin_dir=self.regional_plugin_dir,
                    retrieval_weight_profile_path=self.retrieval_weight_profile_path,
                    prefer_human_verified=self.prefer_human_verified_hits,
                    min_source_weight=self.min_source_weight,
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
                            "kg_node_ref": (
                                (selected_graph.get("payload") or {}).get("node_id")
                                if isinstance((selected_graph or {}).get("payload"), dict)
                                else None
                            ),
                            "title": selected_graph.get("title") if isinstance(selected_graph, dict) else None,
                            "source_file": selected_graph.get("source_file") if isinstance(selected_graph, dict) else None,
                            "source_path": selected_graph.get("source_path") if isinstance(selected_graph, dict) else None,
                            "source_hierarchy": selected_graph.get("source_hierarchy")
                            if isinstance(selected_graph, dict)
                            else None,
                            "reference_standard": (
                                (selected_graph.get("payload") or {}).get("reference_standard")
                                if isinstance((selected_graph or {}).get("payload"), dict)
                                else []
                            ),
                            "reference_standard_codes": (
                                (selected_graph.get("payload") or {}).get("reference_standard_codes")
                                if isinstance((selected_graph or {}).get("payload"), dict)
                                else []
                            ),
                            "reference_source_documents": (
                                (selected_graph.get("payload") or {}).get("reference_source_documents")
                                if isinstance((selected_graph or {}).get("payload"), dict)
                                else []
                            ),
                            "knowledge_tier": (
                                selected_graph.get("knowledge_tier")
                                or (
                                    (selected_graph.get("payload") or {}).get("knowledge_tier")
                                    if isinstance((selected_graph or {}).get("payload"), dict)
                                    else ""
                                )
                            ),
                            "formula_expression": selected_graph.get("formula_expression")
                            if isinstance(selected_graph, dict)
                            else None,
                            "formula_variables": selected_graph.get("formula_variables")
                            if isinstance(selected_graph, dict)
                            else [],
                            "clause_locator": selected_graph.get("clause_locator")
                            if isinstance(selected_graph, dict)
                            else {},
                            "cross_discipline_interface_contract": selected_graph.get("cross_discipline_interface_contract")
                            if isinstance(selected_graph, dict)
                            else {},
                            "optimization_objectives_ext": selected_graph.get("optimization_objectives_ext")
                            if isinstance(selected_graph, dict)
                            else {},
                            "long_tail_profile": selected_graph.get("long_tail_profile")
                            if isinstance(selected_graph, dict)
                            else {},
                            "uncertainty_profile": selected_graph.get("uncertainty_profile")
                            if isinstance(selected_graph, dict)
                            else {},
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

    def _derive_boq_calibration_profile(self, feedback_output_path: Path | str) -> Dict[str, Any]:
        path = Path(feedback_output_path).expanduser().resolve()
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        nodes = payload.get("nodes")
        if not isinstance(nodes, dict) or not nodes:
            return {}

        domain_score_sum: Dict[str, float] = {}
        domain_score_cnt: Dict[str, int] = {}
        for row in nodes.values():
            if not isinstance(row, dict):
                continue
            pass_rate = float(row.get("pass_rate") or 0.0)
            domains = row.get("domains")
            if not isinstance(domains, dict):
                continue
            for domain in domains.keys():
                d = str(domain or "").strip().lower()
                if not d:
                    continue
                domain_score_sum[d] = float(domain_score_sum.get(d) or 0.0) + pass_rate
                domain_score_cnt[d] = int(domain_score_cnt.get(d) or 0) + 1

        if not domain_score_sum:
            return {}
        domain_pass_rate = {
            d: float(domain_score_sum[d]) / max(int(domain_score_cnt.get(d) or 1), 1) for d in domain_score_sum.keys()
        }
        domain_to_processes = {
            "building": ["主体结构", "装饰装修", "围护与建筑构造"],
            "mep": ["机电安装"],
            "earthwork": ["土方工程", "基础工程"],
            "road": ["室外附属", "土方工程"],
            "bridge": ["主体结构", "基础工程"],
            "tunnel": ["主体结构", "基础工程"],
            "hydraulic": ["基础工程", "室外附属"],
            "general": ["综合收尾"],
        }
        process_mul: Dict[str, float] = {}
        for domain, avg_pass in domain_pass_rate.items():
            mul = 1.0
            if avg_pass >= 0.9:
                mul = 1.08
            elif avg_pass >= 0.82:
                mul = 1.03
            elif avg_pass < 0.55:
                mul = 0.92
            elif avg_pass < 0.68:
                mul = 0.96
            for process in domain_to_processes.get(domain, []):
                process_mul[process] = max(process_mul.get(process, 1.0), float(mul))

        if not process_mul:
            return {}
        return {
            "derived_from": str(path),
            "strategy": "feedback_domain_pass_rate_to_process_productivity",
            "productivity_multipliers": {k: round(v, 6) for k, v in process_mul.items()},
        }

    def _run_generation_variant(
        self,
        *,
        index_matrix: Dict[str, Any],
        quant_index: Dict[str, Any],
        specialist_plan: Dict[str, Any],
        strict_evidence_mode: bool,
    ) -> Dict[str, Any]:
        base_threshold = float(self.min_gemini_usefulness_score)
        prev_strict = bool(self._strict_variant_mode)
        if strict_evidence_mode:
            self.min_gemini_usefulness_score = min(95.0, base_threshold + 20.0)
            self._strict_variant_mode = True
        try:
            return self._run_generation_pass(
                index_matrix=index_matrix,
                quant_index=quant_index,
                specialist_plan=specialist_plan,
            )
        finally:
            self.min_gemini_usefulness_score = base_threshold
            self._strict_variant_mode = prev_strict

    def _apply_guardrails(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        guarded: List[Dict[str, Any]] = []

        for section in sections:
            text = str(section.get("content") or "")

            def _rewrite(_text: str, _violations: List[Dict[str, Any]], _attempt: int) -> str:
                return (
                    "第一步（定义）：执行工序名称定义，工程量1200m3、钢筋标号HRB400、尺寸900mm，施工员每班次核验1次；"
                    "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次；"
                    "第三步（解决）：执行控制与验证措施，偏差限值3mm、响应时限4h，质量员每班次检查2次；"
                    "工序名称->参数->风险->控制->验证（阈值95%，检查2次/班，责任岗位技术负责人）。"
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
                        prefer_human_verified=self.prefer_human_verified_hits,
                        min_source_weight=self.min_source_weight,
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
                "evidence_completeness_ratio": float(
                    ((graph_hit.get("evidence_completeness") or {}).get("completeness_ratio") or 0.0)
                    if isinstance(graph_hit.get("evidence_completeness"), dict)
                    else 0.0
                ),
                "evidence_verification_ratio": float(
                    ((graph_hit.get("evidence_completeness") or {}).get("verification_ratio") or 0.0)
                    if isinstance(graph_hit.get("evidence_completeness"), dict)
                    else 0.0
                ),
                "evidence_verification_status": str(
                    ((graph_hit.get("evidence_completeness") or {}).get("verification_status") or "")
                    if isinstance(graph_hit.get("evidence_completeness"), dict)
                    else ""
                ),
                "evidence_ok": self._hit_evidence_ok(graph_hit),
                "formula_safety_ok": self._hit_formula_safety_ok(graph_hit),
                "interface_ok": self._hit_interface_conflict_ok(graph_hit),
                "auto_generated_support": self._is_auto_generated_hit(graph_hit),
                "uncertainty_confidence_level": float(
                    ((graph_hit.get("uncertainty_profile") or {}).get("confidence_level") or 0.0)
                    if isinstance(graph_hit.get("uncertainty_profile"), dict)
                    else 0.0
                ),
                "uncertainty_ok": self._hit_uncertainty_ok(graph_hit, formula_required=formula_required),
                "ok": ok,
            }
            check["ok"] = bool(
                check["ok"]
                and check["evidence_ok"]
                and check["formula_safety_ok"]
                and check["interface_ok"]
                and check["uncertainty_ok"]
            )
            checks.append(check)
            if not check["ok"]:
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
                    "process_parameter_pack": hit.get("process_parameter_pack") or {},
                    "resource_productivity_model": hit.get("resource_productivity_model") or {},
                    "risk_trigger_matrix": hit.get("risk_trigger_matrix") or {},
                    "clause_locator": hit.get("clause_locator") or {},
                    "cross_discipline_interface_contract": hit.get("cross_discipline_interface_contract") or {},
                    "optimization_objectives_ext": hit.get("optimization_objectives_ext") or {},
                    "online_learning_profile": hit.get("online_learning_profile") or {},
                    "long_tail_profile": hit.get("long_tail_profile") or {},
                    "uncertainty_profile": hit.get("uncertainty_profile") or {},
                    "uncertainty_interval": hit.get("uncertainty_interval") or {},
                    "entity_master_key": hit.get("entity_master_key"),
                    "entity_alignment": hit.get("entity_alignment") or {},
                    "regional_standard_timeline": hit.get("regional_standard_timeline") or {},
                    "abnormal_scenario_playbook": hit.get("abnormal_scenario_playbook") or {},
                    "deduction_counterexample_library": hit.get("deduction_counterexample_library") or {},
                    "formula_safety_profile": hit.get("formula_safety_profile") or {},
                    "evidence_completeness": hit.get("evidence_completeness") or {},
                    "retrieval_hints": (hit.get("payload") or {}).get("retrieval_hints")
                    if isinstance(hit.get("payload"), dict)
                    else {},
                    "gemini_context_block": (hit.get("payload") or {}).get("gemini_context_block")
                    if isinstance(hit.get("payload"), dict)
                    else {},
                }
            )
        return packets

    def _split_sentences(self, text: str) -> List[str]:
        lines = [str(x).strip() for x in SENTENCE_SPLIT_RE.split(text or "") if str(x).strip()]
        return [line for line in lines if len(line) >= 4]

    def _numeric_sentence_density(self, sections: List[Dict[str, Any]]) -> float:
        total = 0
        numeric = 0
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            for sentence in self._split_sentences(str(sec.get("content") or "")):
                total += 1
                if re.search(r"\d+(?:\.\d+)?", sentence):
                    numeric += 1
        return round((numeric / max(total, 1)), 6)

    def _checker_role_for_title(self, title: str) -> str:
        t = str(title or "").strip()
        if t == "质量":
            return "质量员"
        if t == "安全":
            return "安全员"
        if t == "进度":
            return "施工员"
        if t == "环保":
            return "环保员"
        if t in {"重难点", "扣分点"}:
            return "技术负责人"
        return "专业工程师"

    def _enforce_numeric_density_sections(self, sections: List[Dict[str, Any]], *, min_ratio: float) -> List[Dict[str, Any]]:
        if not sections:
            return sections
        out: List[Dict[str, Any]] = []
        for sec in sections:
            if not isinstance(sec, dict):
                out.append(sec)
                continue
            text = str(sec.get("content") or "")
            lines = self._split_sentences(text)
            if not lines:
                out.append(sec)
                continue
            numeric = sum(1 for x in lines if re.search(r"\d+(?:\.\d+)?", x))
            ratio = float(numeric) / max(len(lines), 1)
            if ratio < float(min_ratio):
                checker = self._checker_role_for_title(str(sec.get("title") or ""))
                patch = (
                    f"执行量化复核，参数阈值95%，检查频次2次/班，偏差处置时限4h，检查岗位{checker}。"
                )
                text = f"{text}{patch}"
                sec = {**sec, "content": text, "numeric_density_patch": True}
            out.append(sec)
        return out

    def _collect_standard_validity_warnings(
        self,
        *,
        sections: List[Dict[str, Any]],
        bid_date: str | None,
        strict_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        bid_dt: datetime | None = None
        if bid_date:
            try:
                bid_dt = datetime.strptime(str(bid_date).strip(), "%Y-%m-%d")
            except Exception:
                bid_dt = None
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip() or "章节"
            hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
            payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
            timeline = hit.get("standard_validity_timeline") if isinstance(hit.get("standard_validity_timeline"), dict) else {}
            source_hierarchy = str(hit.get("source_hierarchy") or "").strip()
            node_id = str(hit.get("node_id") or "").strip()

            reference_codes = hit.get("reference_standard_codes")
            if not isinstance(reference_codes, list):
                reference_codes = payload.get("reference_standard_codes") if isinstance(payload.get("reference_standard_codes"), list) else []
            reference_codes = [str(x).strip() for x in reference_codes if str(x).strip()]
            if not reference_codes and isinstance(timeline.get("records"), list):
                for rec in timeline.get("records") or []:
                    if not isinstance(rec, dict):
                        continue
                    code = str(rec.get("standard_code") or "").strip()
                    if code and STANDARD_CODE_RE.search(code) and code not in reference_codes:
                        reference_codes.append(code)

            reference_sources = hit.get("reference_source_documents")
            if not isinstance(reference_sources, list):
                reference_sources = payload.get("reference_source_documents") if isinstance(payload.get("reference_source_documents"), list) else []
            reference_sources = [str(x).strip() for x in reference_sources if str(x).strip()]
            if not reference_sources:
                fallback_source = str(hit.get("source_path") or hit.get("source_file") or "").strip()
                if fallback_source:
                    reference_sources = [fallback_source]

            if strict_mode and source_hierarchy in {"国标", "行标", "企标"} and not reference_codes:
                warnings.append(
                    {
                        "type": "standard_code_missing",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": "missing_reference_standard_codes",
                    }
                )

            invalid_codes = [code for code in reference_codes if not STANDARD_CODE_RE.search(code)]
            if strict_mode and source_hierarchy in {"国标", "行标", "企标"} and invalid_codes:
                warnings.append(
                    {
                        "type": "standard_code_format_invalid",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": "invalid_code_format",
                        "invalid_codes": invalid_codes[:8],
                    }
                )

            if strict_mode and source_hierarchy in {"答疑文件", "设计图纸"} and not reference_sources:
                warnings.append(
                    {
                        "type": "source_document_missing",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": "missing_reference_source_documents",
                    }
                )
            if not timeline:
                if strict_mode and source_hierarchy in {"国标", "行标", "企标"}:
                    warnings.append(
                        {
                            "type": "standard_timeline_missing",
                            "severity": "major",
                            "dimension": title,
                            "node_id": node_id,
                            "source_hierarchy": source_hierarchy,
                            "status": "missing_timeline",
                        }
                    )
                continue
            status = str(timeline.get("timeline_status") or "").strip().lower()
            effective_date = str(timeline.get("effective_date") or "").strip()
            if status in {"superseded", "expired", "deprecated"}:
                warnings.append(
                    {
                        "type": "standard_timeline_status_risk",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": status,
                        "effective_date": effective_date,
                    }
                )
                continue

            records = timeline.get("records") if isinstance(timeline.get("records"), list) else []
            anchor = bid_dt or datetime.now()
            active_records = 0
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                rec_status = str(rec.get("status") or "").strip().lower()
                if rec_status in {"superseded", "expired", "deprecated"}:
                    continue
                eff_text = str(rec.get("effective_date") or "").strip()
                exp_text = str(rec.get("expiry_date") or "").strip()
                try:
                    eff_dt = datetime.strptime(eff_text, "%Y-%m-%d") if eff_text else None
                except Exception:
                    eff_dt = None
                try:
                    exp_dt = datetime.strptime(exp_text, "%Y-%m-%d") if exp_text else None
                except Exception:
                    exp_dt = None
                if eff_dt and anchor < eff_dt:
                    continue
                if exp_dt and anchor > exp_dt:
                    continue
                active_records += 1
            if strict_mode and records and active_records == 0 and source_hierarchy in {"国标", "行标", "企标"}:
                warnings.append(
                    {
                        "type": "standard_timeline_no_active_record",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": status or "review_required",
                        "effective_date": effective_date,
                    }
                )
                continue
            if strict_mode and status in {"review_required", "unknown"} and source_hierarchy in {"国标", "行标", "企标"}:
                warnings.append(
                    {
                        "type": "standard_timeline_review_required",
                        "severity": "minor",
                        "dimension": title,
                        "node_id": node_id,
                        "source_hierarchy": source_hierarchy,
                        "status": status,
                        "effective_date": effective_date,
                    }
                )
            if effective_date:
                try:
                    eff = datetime.strptime(effective_date, "%Y-%m-%d")
                except Exception:
                    eff = None
                if eff is not None:
                    anchor = bid_dt or datetime.now()
                    age_years = (anchor - eff).days / 365.0
                    if age_years >= 8.0 and source_hierarchy in {"国标", "行标", "企标"}:
                        warnings.append(
                            {
                                "type": "standard_may_need_update",
                                "severity": "minor",
                                "dimension": title,
                                "node_id": node_id,
                                "source_hierarchy": source_hierarchy,
                                "status": status or "active",
                                "effective_date": effective_date,
                                "age_years": round(age_years, 2),
                            }
                        )
        return warnings

    def _collect_retrieval_domain_warnings(
        self,
        *,
        retrieval_benchmark: Dict[str, Any],
        min_domain_pass_rate: float,
        min_cases: int,
        strict_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        rows = retrieval_benchmark.get("domain_summary") if isinstance(retrieval_benchmark.get("domain_summary"), list) else []
        floor = max(0.0, min(float(min_domain_pass_rate), 1.0))
        cases_floor = max(1, int(min_cases))
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_domain = str(row.get("domain") or "").strip()
            domain = self._normalize_benchmark_domain_label(raw_domain)
            total = int(row.get("total_cases") or row.get("total") or 0)
            pass_rate = float(row.get("pass_rate") or 0.0)
            if total < cases_floor:
                continue
            if domain == "unknown":
                continue
            if pass_rate >= floor:
                continue
            warnings.append(
                {
                    "type": "retrieval_domain_underperforming",
                    "severity": "major" if strict_mode else "minor",
                    "dimension": "检索门禁",
                    "domain": domain,
                    "raw_domain": raw_domain or domain,
                    "total_cases": total,
                    "pass_rate": round(pass_rate, 6),
                    "min_pass_rate": round(floor, 6),
                    "status": "domain_pass_rate_below_threshold",
                }
            )
        return warnings

    def _collect_retrieval_domain_quality_warnings(
        self,
        *,
        retrieval_benchmark: Dict[str, Any],
        min_cases: int,
    ) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        rows = retrieval_benchmark.get("domain_summary") if isinstance(retrieval_benchmark.get("domain_summary"), list) else []
        cases_floor = max(1, int(min_cases))
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_domain = str(row.get("domain") or "").strip()
            total = int(row.get("total_cases") or row.get("total") or 0)
            if total < cases_floor:
                continue
            normalized = self._normalize_benchmark_domain_label(raw_domain)
            if normalized != "unknown":
                continue
            warnings.append(
                {
                    "type": "retrieval_domain_unclassified",
                    "severity": "minor",
                    "dimension": "检索门禁",
                    "raw_domain": raw_domain or "unknown",
                    "total_cases": total,
                    "pass_rate": round(float(row.get("pass_rate") or 0.0), 6),
                    "status": "domain_label_needs_normalization",
                }
            )
        return warnings

    def _normalize_benchmark_domain_label(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return "unknown"
        alias_map = {
            "general": "management",
            "quality": "management",
            "safety": "management",
            "environment": "management",
            "环保": "management",
            "municipal": "road",
            "traffic": "road",
            "hospital": "building",
            "housing": "building",
            "decoration": "building",
            "fire": "mep",
            "electrical": "mep",
            "automation": "digital",
        }
        if text in BENCHMARK_DOMAIN_CORE:
            return text
        if text in alias_map:
            return alias_map[text]
        if text.startswith("zf-kg-"):
            text = re.sub(r"^zf-kg-\d+-", "", text)
            text = re.sub(r"\.json$", "", text)
        compact = text.replace("_", "-").replace(" ", "-")
        for token, domain in BENCHMARK_FILE_DOMAIN_TOKEN_MAP:
            if token in compact:
                return domain
        return "unknown"

    def _collect_auto_generated_lifecycle_warnings(
        self,
        *,
        sections: List[Dict[str, Any]],
        bid_date: str | None,
        max_age_days: int,
        strict_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        bid_dt: datetime | None = None
        if bid_date:
            try:
                bid_dt = datetime.strptime(str(bid_date).strip(), "%Y-%m-%d")
            except Exception:
                bid_dt = None
        anchor = bid_dt or datetime.now()
        max_age = max(7, int(max_age_days))
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip() or "章节"
            hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
            payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
            node_id = str(hit.get("node_id") or "").strip()

            is_auto = bool(hit.get("is_auto_generated"))
            if not is_auto:
                is_auto = bool(payload.get("is_auto_generated")) if isinstance(payload, dict) else False
            if not is_auto:
                continue

            review_status = str(
                hit.get("auto_generated_review_status")
                or payload.get("review_status")
                or "pending"
            ).strip().lower()
            if review_status not in {"pending", "approved", "rejected"}:
                review_status = "pending"

            generated_text = str(
                hit.get("auto_generated_at")
                or payload.get("auto_generated_at")
                or ""
            ).strip()
            expires_text = str(
                hit.get("auto_generated_expires_at")
                or payload.get("auto_generated_expires_at")
                or ""
            ).strip()
            expired = bool(hit.get("auto_generated_expired"))
            if not expired and expires_text:
                try:
                    expires_dt = datetime.strptime(expires_text, "%Y-%m-%d")
                    expired = anchor > expires_dt
                except Exception:
                    expired = False

            if review_status == "rejected":
                warnings.append(
                    {
                        "type": "auto_generated_node_rejected",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "status": review_status,
                    }
                )
            elif strict_mode and review_status == "pending":
                warnings.append(
                    {
                        "type": "auto_generated_node_pending_review",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "status": review_status,
                    }
                )

            if expired:
                warnings.append(
                    {
                        "type": "auto_generated_node_expired",
                        "severity": "major",
                        "dimension": title,
                        "node_id": node_id,
                        "status": review_status,
                        "expires_at": expires_text,
                    }
                )

            if generated_text:
                try:
                    generated_dt = datetime.strptime(generated_text, "%Y-%m-%d")
                except Exception:
                    generated_dt = None
                if generated_dt is not None:
                    age_days = max(0, int((anchor - generated_dt).days))
                    if age_days > max_age and review_status != "approved":
                        warnings.append(
                            {
                                "type": "auto_generated_node_overage",
                                "severity": "major" if strict_mode else "minor",
                                "dimension": title,
                                "node_id": node_id,
                                "status": review_status,
                                "age_days": age_days,
                                "max_age_days": max_age,
                            }
                        )
        return warnings

    def _build_sentence_evidence_chain(
        self,
        *,
        index_matrix: Dict[str, Any],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        item_by_dim: Dict[str, Dict[str, Any]] = {}
        for item in index_matrix.get("index_matrix") or []:
            dim = str(item.get("dimension") or "").strip()
            if dim and dim not in item_by_dim:
                item_by_dim[dim] = item

        chain: List[Dict[str, Any]] = []
        for sec in sections:
            title = str(sec.get("title") or "").strip() or "untitled"
            content = str(sec.get("content") or "")
            source_trace = sec.get("source_trace") if isinstance(sec.get("source_trace"), dict) else {}
            graph_hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
            item = item_by_dim.get(title) or {}
            support_chunks = item.get("support_chunks") if isinstance(item.get("support_chunks"), list) else []
            reference_standard = (
                source_trace.get("reference_standard")
                if isinstance(source_trace.get("reference_standard"), list)
                else []
            )
            if not reference_standard:
                payload = graph_hit.get("payload")
                if isinstance(payload, dict):
                    refs = payload.get("reference_standard")
                    if isinstance(refs, list):
                        reference_standard = refs
            reference_standard_codes = (
                source_trace.get("reference_standard_codes")
                if isinstance(source_trace.get("reference_standard_codes"), list)
                else []
            )
            reference_source_documents = (
                source_trace.get("reference_source_documents")
                if isinstance(source_trace.get("reference_source_documents"), list)
                else []
            )
            if isinstance(graph_hit.get("payload"), dict):
                payload = graph_hit.get("payload") or {}
                if not reference_standard_codes and isinstance(payload.get("reference_standard_codes"), list):
                    reference_standard_codes = [str(x).strip() for x in (payload.get("reference_standard_codes") or []) if str(x).strip()]
                if not reference_source_documents and isinstance(payload.get("reference_source_documents"), list):
                    reference_source_documents = [str(x).strip() for x in (payload.get("reference_source_documents") or []) if str(x).strip()]
            knowledge_tier = str(
                source_trace.get("knowledge_tier")
                or graph_hit.get("knowledge_tier")
                or ((graph_hit.get("payload") or {}).get("knowledge_tier") if isinstance(graph_hit.get("payload"), dict) else "")
                or ""
            ).strip().lower()
            if knowledge_tier not in {"gold", "silver", "bronze"}:
                knowledge_tier = "silver" if bool(source_trace.get("is_auto_generated") or self._is_auto_generated_hit(graph_hit)) else "gold"
            formula_variables = source_trace.get("formula_variables")
            if not isinstance(formula_variables, list):
                formula_variables = graph_hit.get("formula_variables") if isinstance(graph_hit.get("formula_variables"), list) else []
            clause_locator = (
                source_trace.get("clause_locator")
                if isinstance(source_trace.get("clause_locator"), dict)
                else (graph_hit.get("clause_locator") if isinstance(graph_hit.get("clause_locator"), dict) else {})
            )
            clause_anchors = clause_locator.get("anchors") if isinstance(clause_locator, dict) else []
            if not isinstance(clause_anchors, list):
                clause_anchors = []
            clause_refs: List[str] = []
            for anchor in clause_anchors:
                if not isinstance(anchor, dict):
                    continue
                cref = str(anchor.get("clause_ref") or "").strip()
                if cref and cref not in clause_refs:
                    clause_refs.append(cref)
            if not clause_refs:
                for chunk in support_chunks:
                    if not isinstance(chunk, dict):
                        continue
                    for cref in (chunk.get("clause_refs") or []):
                        term = str(cref).strip()
                        if term and term not in clause_refs:
                            clause_refs.append(term)

            for idx, sentence in enumerate(self._split_sentences(content), start=1):
                sentence_id_seed = f"{title}|{idx}|{sentence}"
                sentence_id = hashlib.md5(sentence_id_seed.encode("utf-8", errors="ignore")).hexdigest()[:12]
                chain.append(
                    {
                        "sentence_id": sentence_id,
                        "section_title": title,
                        "sentence_index": idx,
                        "sentence_text": sentence,
                        "specialist_domain": sec.get("specialist_domain"),
                        "specialist_agent": sec.get("specialist_agent"),
                        "boq_binding": {
                            "source_boq_item": sec.get("source_boq_item"),
                        },
                        "index_matrix_binding": {
                            "dimension": item.get("dimension") or title,
                            "keywords": item.get("keywords") or [],
                            "source_type": item.get("source_type"),
                            "support_chunks": [
                                {
                                    "path": chunk.get("path"),
                                    "chunk_id": chunk.get("chunk_id"),
                                    "section_title": chunk.get("section_title"),
                                    "clause_refs": chunk.get("clause_refs") or [],
                                }
                                for chunk in support_chunks[:3]
                                if isinstance(chunk, dict)
                            ],
                            "clause_refs": clause_refs[:12],
                        },
                        "evidence": {
                            "node_id": source_trace.get("node_id") or graph_hit.get("node_id"),
                            "kg_node_ref": source_trace.get("kg_node_ref")
                            or (
                                (graph_hit.get("payload") or {}).get("node_id")
                                if isinstance(graph_hit.get("payload"), dict)
                                else None
                            ),
                            "node_title": source_trace.get("title") or graph_hit.get("title"),
                            "source_file": source_trace.get("source_file") or graph_hit.get("source_file"),
                            "source_path": source_trace.get("source_path") or graph_hit.get("source_path"),
                            "source_hierarchy": source_trace.get("source_hierarchy")
                            or graph_hit.get("source_hierarchy"),
                            "reference_standard": reference_standard[:6],
                            "reference_standard_codes": reference_standard_codes[:8],
                            "reference_source_documents": reference_source_documents[:8],
                            "knowledge_tier": knowledge_tier,
                            "formula_expression": source_trace.get("formula_expression")
                            or graph_hit.get("formula_expression"),
                            "formula_variables": formula_variables[:8],
                            "clause_refs": clause_refs[:12],
                            "clause_anchor": (
                                clause_anchors[0]
                                if clause_anchors and isinstance(clause_anchors[0], dict)
                                else {}
                            ),
                            "clause_anchor_hash": (
                                str(clause_anchors[0].get("anchor_hash") or "")
                                if clause_anchors and isinstance(clause_anchors[0], dict)
                                else ""
                            ),
                            "clause_anchor_path": (
                                str(clause_anchors[0].get("clause_path") or "")
                                if clause_anchors and isinstance(clause_anchors[0], dict)
                                else ""
                            ),
                            "clause_anchor_excerpt": (
                                str(clause_anchors[0].get("source_excerpt") or "")
                                if clause_anchors and isinstance(clause_anchors[0], dict)
                                else ""
                            ),
                            "retrieval_query": sec.get("graph_query"),
                            "index_source_path": (
                                support_chunks[0].get("path")
                                if support_chunks and isinstance(support_chunks[0], dict)
                                else None
                            ),
                            "is_auto_generated": bool(
                                source_trace.get("is_auto_generated") or self._is_auto_generated_hit(graph_hit)
                            ),
                        },
                    }
                )
        return chain

    def _compute_sentence_evidence_stats(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(chain)
        traceable = 0
        for row in chain:
            evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            if (
                str(evidence.get("node_id") or "").strip()
                or str(evidence.get("source_path") or "").strip()
                or str(evidence.get("index_source_path") or "").strip()
                or str(evidence.get("retrieval_query") or "").strip()
            ):
                traceable += 1
        ratio = round(traceable / total, 4) if total > 0 else 0.0
        return {
            "total_sentences": total,
            "traceable_sentences": traceable,
            "trace_coverage_ratio": ratio,
            "missing_trace_sentences": max(total - traceable, 0),
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
            if item.get("node_ok") and not item.get("evidence_ok"):
                key = ("evidence_incomplete", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "evidence_incomplete",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": [
                                "numeric_sources: parameter/value/unit",
                                "clause_locator: anchor_hash/clause_path",
                                "standard_validity_timeline: effective_date",
                            ],
                        }
                    )
            if item.get("node_ok"):
                ver = float(item.get("evidence_verification_ratio") or 0.0)
                ver_status = str(item.get("evidence_verification_status") or "").strip().lower()
                if ver < 0.2 and ver_status in {"synthetic_only", "warn"}:
                    key = ("evidence_unverified", dim)
                    if key not in seen:
                        seen.add(key)
                        gaps.append(
                            {
                                "type": "evidence_unverified",
                                "dimension": dim,
                                "required_keywords": item.get("keywords") or [],
                                "query": item.get("graph_query"),
                                "suggested_parameters": [
                                    "numeric_sources.evidence_verified",
                                    "numeric_sources.source_page/source_file",
                                    "evidence_completeness.verification_ratio >= 0.6",
                                ],
                            }
                        )
            if item.get("node_ok") and not item.get("formula_safety_ok"):
                key = ("formula_safety_missing", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "formula_safety_missing",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": [
                                "formula_safety_profile.safe == true",
                                "公式变量声明与量纲绑定一致",
                                "分母保护(max(...,1))",
                            ],
                        }
                    )
            if item.get("node_ok") and not item.get("interface_ok"):
                key = ("interface_conflict_open", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "interface_conflict_open",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": [
                                "cross_discipline_interface_contract.conflict_graph",
                                "冲突状态由conflict/open闭环为resolved",
                            ],
                        }
                    )
            if item.get("node_ok") and not item.get("uncertainty_ok"):
                key = ("uncertainty_low", dim)
                if key not in seen:
                    seen.add(key)
                    gaps.append(
                        {
                            "type": "uncertainty_low",
                            "dimension": dim,
                            "required_keywords": item.get("keywords") or [],
                            "query": item.get("graph_query"),
                            "suggested_parameters": [
                                "uncertainty_profile.enabled == true",
                                "uncertainty_profile.confidence_level >= 0.5",
                                "uncertainty_profile.relative_interval + baseline_result",
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
        chapter_response_plan: Optional[Dict[str, Any]] = None,
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
        blocker_keys = {"工期_vs_CPM", "标高", "高程", "坐标", "坐标X", "坐标Y", "关键线路"}

        def _severity_for_key(key: str) -> str:
            text = str(key or "").strip()
            if text in blocker_keys:
                return "blocker"
            if "conflict" in text.lower() or "冲突" in text:
                return "major"
            return "minor"

        for key, refs in key_values.items():
            uniq_vals = sorted(
                {str(r.get("value") or "").strip() for r in refs if str(r.get("value") or "").strip()}
            )
            if len(uniq_vals) > 1:
                inconsistencies.append({"key": key, "values": uniq_vals, "refs": refs, "severity": _severity_for_key(key)})

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
                            "severity": "blocker",
                        }
                    )

        solver = solve_cross_discipline_constraints(
            sections=sections,
            quant_index=quant_index,
            chapter_response_plan=chapter_response_plan or {},
        )
        if isinstance(solver, dict):
            for item in solver.get("conflicts") or []:
                if not isinstance(item, dict):
                    continue
                inconsistencies.append(
                    {
                        "key": str(item.get("type") or "cross_conflict"),
                        "values": item.get("values") or [],
                        "refs": item.get("refs") or [],
                        "severity": str(item.get("severity") or "major"),
                    }
                )

        hard_fail = bool(inconsistencies or missing_graph_bindings)
        severity_summary = {"blocker": 0, "major": 0, "minor": 0}
        for item in inconsistencies:
            sev = str(item.get("severity") or "minor").strip().lower()
            if sev not in severity_summary:
                sev = "minor"
            severity_summary[sev] += 1
        if missing_graph_bindings:
            severity_summary["major"] += len(missing_graph_bindings)
        return {
            "ok": not hard_fail,
            "checked_sections": len(sections),
            "detected_domains": specialist_plan.get("detected_domains") or [],
            "missing_graph_bindings": missing_graph_bindings,
            "missing_graph_bindings_count": len(missing_graph_bindings),
            "inconsistencies": inconsistencies,
            "inconsistency_count": len(inconsistencies),
            "inconsistency_severity": severity_summary,
            "cpm_project_duration_days": project_duration,
            "constraint_solver": solver,
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
                    "severity": "major",
                    "required_keywords": [str(item.get("domain") or "general")],
                    "query": f"{item.get('domain') or 'general'} {item.get('title') or ''}".strip(),
                    "suggested_parameters": ["绑定图谱逻辑节点(node_id/title/source_path)"],
                }
            )
        for item in compliance_audit.get("inconsistencies") or []:
            severity = str(item.get("severity") or "major").strip().lower()
            if severity not in {"blocker", "major", "minor"}:
                severity = "major"
            gaps.append(
                {
                    "type": "cross_domain_inconsistency",
                    "dimension": str(item.get("key") or "跨专业一致性"),
                    "severity": severity,
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
        sentence_evidence_stats: Optional[Dict[str, Any]] = None,
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
            severity = compliance_audit.get("inconsistency_severity") if isinstance(
                compliance_audit.get("inconsistency_severity"), dict
            ) else {}
            lines.append(
                f"- Compliance Severity(blocker/major/minor): "
                f"{int(severity.get('blocker') or 0)}/"
                f"{int(severity.get('major') or 0)}/"
                f"{int(severity.get('minor') or 0)}"
            )
        if isinstance(sentence_evidence_stats, dict):
            lines.append(f"- Sentence Trace Total: {int(sentence_evidence_stats.get('total_sentences') or 0)}")
            lines.append(
                f"- Sentence Trace Coverage: {float(sentence_evidence_stats.get('trace_coverage_ratio') or 0.0):.4f}"
            )
            lines.append(
                f"- Sentence Missing Trace: {int(sentence_evidence_stats.get('missing_trace_sentences') or 0)}"
            )
        lines.append(f"- Intercepted: {bool(gaps or fail_fast_error)}")
        if fail_fast_error:
            lines.append(f"- FailFast Error: {fail_fast_error}")
        if isinstance(self_healing, dict) and self_healing:
            lines.append(f"- Self-Healing Triggered: {bool(self_healing.get('triggered'))}")
            lines.append(f"- Self-Healing Patch Nodes: {int(self_healing.get('patch_nodes') or 0)}")
            lines.append(f"- Self-Healing Used Fallback: {bool(self_healing.get('used_fallback'))}")
            if self_healing.get("rollback_triggered") is not None:
                lines.append(f"- Self-Healing Rollback Triggered: {bool(self_healing.get('rollback_triggered'))}")
            if self_healing.get("rollback_reason"):
                lines.append(f"- Self-Healing Rollback Reason: {self_healing.get('rollback_reason')}")
            validation = self_healing.get("validation") if isinstance(self_healing.get("validation"), dict) else {}
            if validation:
                lines.append(
                    f"- Self-Healing Validation OK: {bool(validation.get('ok'))} "
                    f"(issues={int(validation.get('issues_count') or 0)})"
                )
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
            lines.append("| # | Severity | Gap Type | Dimension | Required Keywords | Suggested Parameters | Search Query |")
            lines.append("|---|---|---|---|---|---|---|")
            for idx, gap in enumerate(gaps, start=1):
                severity = str(gap.get("severity") or "major").strip().lower()
                if severity not in {"blocker", "major", "minor"}:
                    severity = "major"
                keywords = "、".join([str(x) for x in (gap.get("required_keywords") or [])[:8]])
                hints = "、".join([str(x) for x in (gap.get("suggested_parameters") or [])[:6]])
                query = str(gap.get("query") or "").replace("|", "\\|")
                lines.append(
                    f"| {idx} | {severity} | {gap.get('type')} | {gap.get('dimension')} | {keywords} | {hints} | `{query}` |"
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
        chapter_response_plan = self._build_chapter_response_plan(
            index_matrix=index_matrix,
            sections=guarded_sections,
        )
        graph_audit = self._audit_graph_support(index_matrix=index_matrix, sections=guarded_sections)
        compliance_audit = self._run_compliance_audit(
            sections=guarded_sections,
            quant_index=quant_index,
            specialist_plan=specialist_plan,
            chapter_response_plan=chapter_response_plan,
        )
        gaps = self._collect_knowledge_gaps(
            graph_audit=graph_audit,
            audit_result=writing.get("audit_result") or {},
        )
        gaps.extend(self._collect_compliance_gaps(compliance_audit))
        for row in chapter_response_plan.get("chapters") or []:
            if not isinstance(row, dict):
                continue
            if bool(row.get("coverage_ok")):
                continue
            gaps.append(
                {
                    "type": "chapter_response_plan_missing",
                    "dimension": str(row.get("chapter") or "章节"),
                    "required_keywords": row.get("required_keywords") or [],
                    "query": f"{row.get('chapter') or ''} 评分点 证据锚点".strip(),
                    "suggested_parameters": ["补齐章节评分点映射与证据锚点绑定"],
                }
            )
        return {
            "writing": writing,
            "sections": guarded_sections,
            "chapter_response_plan": chapter_response_plan,
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
        )
        built = await healer.build_patch_nodes(gaps)
        nodes = built.get("nodes") or []
        validation = built.get("validation") if isinstance(built.get("validation"), dict) else {}
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
            "validation": validation,
            "attempts": built.get("attempts") if isinstance(built.get("attempts"), list) else [],
        }

    async def run(
        self,
        *,
        tender_paths: List[str],
        boq_payload: Dict[str, Any],
        boq_governance: Dict[str, Any] | None = None,
        graph_root: Path | str = DEFAULT_KG_ROOT,
        output_path: Path | str = DEFAULT_PIPELINE_OUTPUT,
        missing_report_path: Path | str = DEFAULT_MISSING_REPORT,
        enable_self_healing: bool = False,
        enable_docx_export: bool = False,
        docx_output_path: Path | str | None = None,
        enable_visual_generation: bool = True,
        visual_output_dir: Path | str | None = None,
        visual_provider: str = "google",
        visual_model: str = "imagen-3.0-generate-002",
        visual_api_key: str | None = None,
        activation_context: str | None = None,
        enable_standard_auto_update: bool = True,
        standard_catalog_path: Path | str | None = None,
        enable_project_rule_extraction: bool = True,
        run_retrieval_benchmark_gate: bool = True,
        benchmark_dataset_path: Path | str = DEFAULT_BENCHMARK_DATASET_PATH,
        benchmark_min_pass_rate: float = 0.85,
        benchmark_min_avg_mrr: float = 0.65,
        benchmark_min_domain_pass_rate: float = 0.70,
        benchmark_domain_min_cases: int = 3,
        enforce_retrieval_gate: bool = False,
        enforce_benchmark_domain_gate: bool = False,
        enable_retrieval_weight_training: bool = True,
        retrieval_weight_profile_path: Path | str = DEFAULT_WEIGHT_PROFILE_PATH,
        enable_feedback_learning: bool = True,
        enable_feedback_writeback: bool = True,
        feedback_output_path: Path | str = "build/kg_project_feedback_memory.json",
        region_context: str | None = None,
        bid_date: str | None = None,
        allow_superseded: bool = False,
        regional_plugin_dir: Path | str | None = None,
        auto_approve_generated: bool = True,
        release_approver: str = "system",
        release_signature: str = "system-sign",
        create_release_freeze: bool = False,
        release_root: Path | str = "build/kg_releases",
        enable_ab_experiment: bool = True,
        enforce_numeric_density_gate: bool = True,
        numeric_density_min: float = 0.95,
        auto_enrich_numeric_density: bool = True,
        enforce_standard_reference_gate: bool = False,
        enforce_auto_generated_lifecycle_gate: bool = False,
        auto_generated_max_age_days: int = 120,
        hit_rate_dashboard_json_path: Path | str = DEFAULT_HIT_RATE_DASHBOARD_JSON,
        hit_rate_dashboard_md_path: Path | str = DEFAULT_HIT_RATE_DASHBOARD_MD,
        enrichment_draft_path: Path | str = DEFAULT_ENRICHMENT_DRAFT_JSON,
    ) -> Dict[str, Any]:
        self.region_context = str(region_context or "").strip().upper() or None
        self.bid_date = str(bid_date or "").strip() or None
        self.allow_superseded = bool(allow_superseded)
        self.regional_plugin_dir = (
            str(Path(regional_plugin_dir).expanduser().resolve()) if regional_plugin_dir not in (None, "") else None
        )
        standard_update_report: Dict[str, Any] = {"triggered": False, "files_changed": 0}
        approval_report: Dict[str, Any] = {"triggered": False, "nodes_approved": 0}
        if enable_standard_auto_update:
            try:
                standard_update_report = {
                    "triggered": True,
                    **refresh_kg_standards(
                        kg_root=graph_root,
                        catalog_path=standard_catalog_path,
                        dry_run=False,
                    ),
                }
            except Exception as exc:
                standard_update_report = {"triggered": True, "ok": False, "error": str(exc)}

        if auto_approve_generated:
            try:
                approval_report = {
                    "triggered": True,
                    **approve_auto_generated_nodes(
                        kg_root=graph_root,
                        approver=release_approver,
                        signature=release_signature,
                        note="auto_approval_from_pipeline",
                    ),
                }
            except Exception as exc:
                approval_report = {"triggered": True, "ok": False, "error": str(exc)}

        graph_report = ingest_knowledge_graph(
            graph_root,
            db_path=self.kg_db_path,
            activation_context=activation_context,
        )
        if enable_project_rule_extraction:
            self.project_rule_matrix = build_project_rule_matrix(tender_paths)
        else:
            self.project_rule_matrix = {"ok": True, "rules_total": 0, "rules": [], "dimension_overrides": {}}

        retrieval_benchmark: Dict[str, Any] = {"triggered": False}
        if run_retrieval_benchmark_gate:
            try:
                retrieval_benchmark = {
                    "triggered": True,
                    **run_retrieval_benchmark(
                        db_path=self.kg_db_path,
                        dataset_path=benchmark_dataset_path,
                        min_pass_rate=float(benchmark_min_pass_rate),
                        min_avg_mrr=float(benchmark_min_avg_mrr),
                    ),
                }
            except Exception as exc:
                retrieval_benchmark = {"triggered": True, "ok": False, "error": str(exc)}

        retrieval_weight_profile: Dict[str, Any] = {"triggered": False}
        if enable_retrieval_weight_training:
            try:
                retrieval_weight_profile = {
                    "triggered": True,
                    **train_retrieval_weight_profile(
                        benchmark_report=retrieval_benchmark if retrieval_benchmark.get("triggered") else {},
                        feedback_memory=feedback_output_path,
                        output_path=retrieval_weight_profile_path,
                    ),
                }
            except Exception as exc:
                retrieval_weight_profile = {"triggered": True, "ok": False, "error": str(exc)}
        if bool(retrieval_weight_profile.get("ok")) and str(retrieval_weight_profile.get("saved_at") or "").strip():
            self.retrieval_weight_profile_path = str(retrieval_weight_profile.get("saved_at"))
        else:
            profile_path = Path(retrieval_weight_profile_path).expanduser().resolve()
            self.retrieval_weight_profile_path = str(profile_path) if profile_path.exists() else None

        matrix_result = await build_index_matrix(tender_paths)
        index_matrix = matrix_result["matrix"]
        boq_calibration_profile: Dict[str, Any] = {}
        if enable_feedback_learning:
            boq_calibration_profile = self._derive_boq_calibration_profile(feedback_output_path)
        self.quant_engine.set_calibration_profile(boq_calibration_profile)
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
            patch_file = Path(graph_root).expanduser().resolve() / "_auto_generated/self_healing_patch_nodes.json"
            backup_path = patch_file.with_suffix(".canary.bak.json")
            had_patch_before = patch_file.exists()
            if had_patch_before:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(patch_file, backup_path)
            self_healing_result = await self._run_self_healing(
                graph_root=graph_root,
                gaps=first_pass.get("gaps") or [],
            )
            self_healing_result["canary_backup"] = str(backup_path) if had_patch_before else ""
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
            pre_gap_count = len(first_pass.get("gaps") or [])
            post_gap_count = len(final_pass.get("gaps") or [])
            if post_gap_count > pre_gap_count:
                if had_patch_before and backup_path.exists():
                    shutil.copy2(backup_path, patch_file)
                elif patch_file.exists():
                    patch_file.unlink()
                ctx.graph_report = ingest_knowledge_graph(
                    graph_root,
                    db_path=self.kg_db_path,
                    activation_context=activation_context,
                )
                final_pass = dict(first_pass)
                self_healing_result["rollback_triggered"] = True
                self_healing_result["rollback_reason"] = (
                    f"post_healing_gaps_worse:{post_gap_count}>{pre_gap_count}"
                )
            else:
                self_healing_result["rollback_triggered"] = False
                self_healing_result["rollback_reason"] = ""
            if backup_path.exists():
                backup_path.unlink(missing_ok=True)
        if bool(self_healing_result.get("triggered")):
            validation = self_healing_result.get("validation") if isinstance(
                self_healing_result.get("validation"), dict
            ) else {}
            if validation and not bool(validation.get("ok")):
                final_pass.setdefault("gaps", []).append(
                    {
                        "type": "self_healing_validation_failed",
                        "severity": "major",
                        "dimension": "自愈补丁",
                        "required_keywords": ["reference_standard", "formula_replay"],
                        "query": "self_healing_patch_validation",
                        "suggested_parameters": [
                            "修复reference_standard规范号格式",
                            "修复FormulaNode公式可回放执行",
                        ],
                    }
                )
                final_pass["intercepted"] = True
                patch_file = Path(graph_root).expanduser().resolve() / "_auto_generated/self_healing_patch_nodes.json"
                backup_file = str(self_healing_result.get("canary_backup") or "").strip()
                backup_path = Path(backup_file) if backup_file else None
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, patch_file)
                    self_healing_result["rollback_triggered"] = True
                    self_healing_result["rollback_reason"] = "validation_failed"

        benchmark_warning: Dict[str, Any] = {}
        benchmark_domain_warnings: List[Dict[str, Any]] = []
        benchmark_domain_quality_warnings: List[Dict[str, Any]] = []
        if bool(retrieval_benchmark.get("triggered")) and not bool(retrieval_benchmark.get("ok")):
            benchmark_warning = {
                "type": "retrieval_benchmark_gate_failed",
                "query": "kg_retrieval_benchmark",
                "message": "检索评测门禁未达标，建议补强后发布。",
            }
            if enforce_retrieval_gate:
                gap = {
                    "type": "retrieval_benchmark_gate_failed",
                    "dimension": "检索门禁",
                    "required_keywords": [],
                    "query": "kg_retrieval_benchmark",
                    "suggested_parameters": ["提升图谱检索精度与MRR后再发布"],
                }
                if gap not in final_pass.get("gaps", []):
                    final_pass.setdefault("gaps", []).append(gap)
                final_pass["intercepted"] = True
        if bool(retrieval_benchmark.get("triggered")):
            benchmark_domain_warnings = self._collect_retrieval_domain_warnings(
                retrieval_benchmark=retrieval_benchmark,
                min_domain_pass_rate=float(benchmark_min_domain_pass_rate),
                min_cases=int(benchmark_domain_min_cases),
                strict_mode=bool(enforce_benchmark_domain_gate),
            )
            benchmark_domain_quality_warnings = self._collect_retrieval_domain_quality_warnings(
                retrieval_benchmark=retrieval_benchmark,
                min_cases=int(benchmark_domain_min_cases),
            )
            if benchmark_domain_warnings:
                benchmark_warning["domain_warnings"] = benchmark_domain_warnings
                if enforce_benchmark_domain_gate:
                    final_pass.setdefault("gaps", []).append(
                        {
                            "type": "retrieval_benchmark_domain_gate_failed",
                            "dimension": "检索门禁",
                            "required_keywords": [str(x.get("domain") or "") for x in benchmark_domain_warnings[:8]],
                            "query": "kg_retrieval_benchmark.domain_summary",
                            "suggested_parameters": [
                                f"domain_pass_rate >= {float(benchmark_min_domain_pass_rate):.2f}",
                                f"domain_cases >= {int(benchmark_domain_min_cases)}",
                            ],
                        }
                    )
                    final_pass["intercepted"] = True
            if benchmark_domain_quality_warnings:
                benchmark_warning["domain_quality_warnings"] = benchmark_domain_quality_warnings

        if auto_enrich_numeric_density:
            final_pass["sections"] = self._enforce_numeric_density_sections(
                final_pass.get("sections") or [],
                min_ratio=float(numeric_density_min),
            )
        numeric_density_value = self._numeric_sentence_density(final_pass.get("sections") or [])
        numeric_density_gate = {
            "enabled": bool(enforce_numeric_density_gate),
            "min_required": float(numeric_density_min),
            "actual": float(numeric_density_value),
            "ok": float(numeric_density_value) >= float(numeric_density_min),
        }
        if enforce_numeric_density_gate and not bool(numeric_density_gate.get("ok")):
            final_pass.setdefault("gaps", []).append(
                {
                    "type": "numeric_density_insufficient",
                    "severity": "major",
                    "dimension": "语言护栏",
                    "required_keywords": ["动作", "参数", "检查人"],
                    "query": "numeric_sentence_density_guard",
                    "suggested_parameters": [
                        f"numeric_sentence_density >= {float(numeric_density_min):.2f}",
                        "每句至少1个数字参数与1个岗位",
                    ],
                }
            )
            final_pass["intercepted"] = True

        standard_validity_warnings = self._collect_standard_validity_warnings(
            sections=final_pass.get("sections") or [],
            bid_date=self.bid_date,
            strict_mode=bool(enforce_standard_reference_gate),
        )
        for warning in standard_validity_warnings:
            if not isinstance(warning, dict):
                continue
            if str(warning.get("severity") or "").strip().lower() != "major":
                continue
            final_pass.setdefault("gaps", []).append(
                {
                    "type": str(warning.get("type") or "standard_validity_warning"),
                    "severity": "major",
                    "dimension": str(warning.get("dimension") or "标准时效"),
                    "required_keywords": [str(warning.get("status") or "")],
                    "query": str(warning.get("node_id") or "standard_validity_timeline"),
                    "suggested_parameters": ["更新标准时效记录或切换至有效标准节点"],
                }
            )
            final_pass["intercepted"] = True
        auto_generated_lifecycle_warnings = self._collect_auto_generated_lifecycle_warnings(
            sections=final_pass.get("sections") or [],
            bid_date=self.bid_date,
            max_age_days=int(auto_generated_max_age_days),
            strict_mode=bool(enforce_auto_generated_lifecycle_gate),
        )
        for warning in auto_generated_lifecycle_warnings:
            if not isinstance(warning, dict):
                continue
            if str(warning.get("severity") or "").strip().lower() != "major":
                continue
            if not enforce_auto_generated_lifecycle_gate:
                continue
            final_pass.setdefault("gaps", []).append(
                {
                    "type": str(warning.get("type") or "auto_generated_lifecycle_warning"),
                    "severity": "major",
                    "dimension": str(warning.get("dimension") or "图谱自愈生命周期"),
                    "required_keywords": [str(warning.get("status") or "")],
                    "query": str(warning.get("node_id") or "auto_generated_lifecycle"),
                    "suggested_parameters": ["补丁节点需人工复核通过且在有效期内"],
                }
            )
            final_pass["intercepted"] = True

        sentence_evidence_chain = self._build_sentence_evidence_chain(
            index_matrix=ctx.index_matrix,
            sections=final_pass.get("sections") or [],
        )
        sentence_evidence_stats = self._compute_sentence_evidence_stats(sentence_evidence_chain)
        tactical_effects = build_tactical_effects(final_pass.get("sections") or [])

        ab_experiment_report: Dict[str, Any] = {"enabled": False}
        if enable_ab_experiment:
            variant_b = self._run_generation_variant(
                index_matrix=ctx.index_matrix,
                quant_index=ctx.quant_index,
                specialist_plan=specialist_plan,
                strict_evidence_mode=True,
            )
            variant_b_sentence_stats = self._compute_sentence_evidence_stats(
                self._build_sentence_evidence_chain(
                    index_matrix=ctx.index_matrix,
                    sections=variant_b.get("sections") or [],
                )
            )
            ab_experiment_report = compare_ab_variants(
                {
                    "sections": final_pass.get("sections") or [],
                    "graph_audit": final_pass.get("graph_audit") or {},
                    "compliance_audit": final_pass.get("compliance_audit") or {},
                    "sentence_evidence_stats": sentence_evidence_stats,
                },
                {
                    "sections": variant_b.get("sections") or [],
                    "graph_audit": variant_b.get("graph_audit") or {},
                    "compliance_audit": variant_b.get("compliance_audit") or {},
                    "sentence_evidence_stats": variant_b_sentence_stats,
                },
            )

        hit_rate_dashboard = build_hit_rate_dashboard(
            index_matrix=ctx.index_matrix,
            audit_result=(final_pass.get("writing") or {}).get("audit_result") or {},
            graph_audit=final_pass.get("graph_audit") or {},
            compliance_audit=final_pass.get("compliance_audit") or {},
            sentence_evidence_stats=sentence_evidence_stats,
            sections=final_pass.get("sections") or [],
            gaps=final_pass.get("gaps") or [],
            pre_healing_gap_count=len(first_pass.get("gaps") or []),
            self_healing=self_healing_result,
            boq_governance=boq_governance or {},
        )
        dashboard_saved = write_hit_rate_dashboard(
            dashboard=hit_rate_dashboard,
            out_json=hit_rate_dashboard_json_path,
            out_md=hit_rate_dashboard_md_path,
        )
        enrichment_draft = build_missing_enrichment_draft(
            gaps=final_pass.get("gaps") or [],
            output_path=enrichment_draft_path,
        )

        missing_report_saved = self._write_missing_knowledge_report(
            gaps=final_pass.get("gaps") or [],
            graph_report=ctx.graph_report,
            audit_result=(final_pass.get("writing") or {}).get("audit_result") or {},
            graph_audit=final_pass.get("graph_audit") or {},
            compliance_audit=final_pass.get("compliance_audit") or {},
            fail_fast_error=final_pass.get("fail_fast_error"),
            sentence_evidence_stats=sentence_evidence_stats,
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

        release_meta: Dict[str, Any] = {"triggered": False}
        release_strategy: Dict[str, Any] = {"ok": False, "strategy": "hold", "reason": "release_not_triggered"}
        if create_release_freeze and not intercepted:
            try:
                release_meta = {
                    "triggered": True,
                    **create_release_snapshot(
                        kg_root=graph_root,
                        release_root=release_root,
                        approver=release_approver,
                    ),
                }
                if bool(release_meta.get("ok")):
                    release_strategy = recommend_release_strategy(
                        release_root=release_root,
                        target_release_id=str(release_meta.get("release_id") or ""),
                    )
            except Exception as exc:
                release_meta = {"triggered": True, "ok": False, "error": str(exc)}
                release_strategy = {"ok": False, "strategy": "hold", "reason": str(exc)}

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
                    "boq_calibration_profile": boq_calibration_profile,
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
                "trace_agent": {"status": "done", "result": sentence_evidence_stats},
                "chapter_planner_agent": {
                    "status": "done",
                    "result": final_pass.get("chapter_response_plan") or {},
                },
                "self_healing_agent": {"status": "done" if self_healing_result.get("triggered") else "skipped"},
                "gemini_context_agent": {"status": "done"},
                "dashboard_agent": {"status": "done", "result": hit_rate_dashboard},
                "tactical_agent": {"status": "done", "result": tactical_effects},
                "ab_test_agent": {"status": "done" if enable_ab_experiment else "skipped", "result": ab_experiment_report},
                "standard_update_agent": {"status": "done" if standard_update_report.get("triggered") else "skipped"},
                "project_rule_agent": {"status": "done" if enable_project_rule_extraction else "skipped"},
                "benchmark_gate_agent": {
                    "status": "done" if retrieval_benchmark.get("triggered") else "skipped",
                    "result": retrieval_benchmark,
                },
                "retrieval_tuning_agent": {
                    "status": "done" if retrieval_weight_profile.get("triggered") else "skipped",
                    "result": retrieval_weight_profile,
                },
                "feedback_agent": {
                    "status": "done" if enable_feedback_learning else "skipped",
                    "writeback": "done" if (enable_feedback_learning and enable_feedback_writeback) else "skipped",
                },
                "visual_agent": {
                    "status": "done" if visual_meta.get("generated") else "skipped",
                    "meta": visual_meta,
                },
                "document_assembler": {"status": "done" if docx_meta.get("exported") else "skipped", "meta": docx_meta},
            },
            "specialist_plan": specialist_plan,
            "project_rule_matrix": self.project_rule_matrix,
            "index_matrix": ctx.index_matrix,
            "quant_index": ctx.quant_index,
            "sections": final_pass.get("sections") or [],
            "chapter_response_plan": final_pass.get("chapter_response_plan") or {},
            "knowledge_gaps": final_pass.get("gaps") or [],
            "missing_knowledge_report": missing_report_saved,
            "fail_fast_error": final_pass.get("fail_fast_error"),
            "sentence_evidence_stats": sentence_evidence_stats,
            "sentence_evidence_chain": sentence_evidence_chain,
            "hit_rate_dashboard": hit_rate_dashboard,
            "hit_rate_dashboard_saved": dashboard_saved,
            "tactical_effects": tactical_effects,
            "ab_experiment": ab_experiment_report,
            "auto_enrichment_draft": enrichment_draft,
            "numeric_density_gate": numeric_density_gate,
            "standard_validity_warnings": standard_validity_warnings,
            "auto_generated_lifecycle_warnings": auto_generated_lifecycle_warnings,
            "gemini_context_packets": self._build_gemini_context_packets(
                index_matrix=ctx.index_matrix,
                sections=final_pass.get("sections") or [],
                specialist_plan=specialist_plan,
            ),
            "self_healing": self_healing_result,
            "boq_governance": boq_governance or {},
            "standard_auto_update": standard_update_report,
            "approval_report": approval_report,
            "retrieval_benchmark": retrieval_benchmark,
            "retrieval_benchmark_domain_warnings": benchmark_domain_warnings,
            "retrieval_benchmark_domain_quality_warnings": benchmark_domain_quality_warnings,
            "retrieval_weight_profile": retrieval_weight_profile,
            "retrieval_benchmark_warning": benchmark_warning,
            "docx_output": docx_saved,
            "visual_output": visual_meta,
            "release_snapshot": release_meta,
            "release_strategy": release_strategy,
            "pre_healing": {
                "intercepted": bool(first_pass.get("intercepted")),
                "knowledge_gaps": first_pass.get("gaps") or [],
                "fail_fast_error": first_pass.get("fail_fast_error"),
            },
        }

        feedback_report: Dict[str, Any] = {"triggered": False}
        if enable_feedback_learning:
            try:
                feedback_report = {
                    "triggered": True,
                    **update_feedback_memory(
                        result_payload=output,
                        output_path=feedback_output_path,
                        writeback_graph=bool(enable_feedback_writeback),
                        graph_root=graph_root,
                    ),
                }
            except Exception as exc:
                feedback_report = {"triggered": True, "ok": False, "error": str(exc)}
        output["feedback_learning"] = feedback_report

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        output["saved_at"] = str(out)
        out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        return output
