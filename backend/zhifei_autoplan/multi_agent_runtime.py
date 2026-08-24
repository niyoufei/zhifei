from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from backend.zhifei_autoplan.graph_dispatcher import (
    assign_specialties_to_outline,
    detect_specialty_dispatch,
    extract_experience_values,
    search_dispatch_graphs,
)
from backend.zhifei_autoplan.project_fact_ledger import validate_project_fact_ledger
from backend.zhifei_autoplan.requirement_evidence_matrix import (
    validate_requirement_evidence_matrix,
)


AGENT_ROLE_DIRECTIVES: Dict[str, str] = {
    "主控Agent": "统筹招标响应、章节边界、技术路线与交付完整性。",
    "项目事实仲裁Agent": "按来源优先级冻结项目名称、范围、工期、参数等事实，发现同级冲突立即阻断生成。",
    "要求证据矩阵Agent": "把招标要求、评分点和强制条款逐项绑定到责任章节、责任Agent及可反查证据。",
    "合规Agent": "核验招标、答疑、设计文件、清单和现行规范的优先级与引用边界。",
    "规范证据Agent": "核验规范名称、编号、现行版本、生效状态、官方来源及正文引用位置。",
    "证据溯源Agent": "把关键结论绑定到可追溯证据，禁止无来源的项目事实和参数。",
    "清单响应Agent": "逐项覆盖工程量清单重点，补齐材料、工序、资源、验收和偏差处置。",
    "图纸接口Agent": "核对专业接口、施工顺序、测量复核、预留预埋和交叉作业条件。",
    "跨专业接口Agent": "核对清单重点项、图纸、规范、专业工序和章节闭环之间的跨专业接口。",
    "进度资源Agent": "校核工期逻辑、流水组织、劳动力、机械设备和材料供应匹配关系。",
    "风险闭环Agent": "把主要风险写成风险、控制、验证、记录和偏差处置闭环。",
    "招标评分响应Agent": "逐项绑定评审目录、评分点、强制条款和招标证据，阻止漏项与偏题。",
    "技术深度Agent": "补强项目专属工序、参数、接口、资源与验收闭环，删除套话和机械扩写。",
    "图表质量Agent": "核验图表的项目相关性、可读性、去重、证据绑定和正文引用。",
    "全篇一致性Agent": "统一项目名称、范围、参数、工期、资源口径和跨章节引用。",
    "专业渲染Agent": "按招标格式优先原则统一Word层级、分页、表格、图表和版式。",
    "文档视觉质检Agent": "检查空白页、稀疏页、孤行孤字、表格跨页、标题层级和图文版面。",
    "交付验收Agent": "汇总内容、证据、规范、图表和版式质量门，只放行可直接交付的成品。",
}


_DEFAULT_ROLE_CONTRACT: Dict[str, Any] = {
    "input_boundary": ["章节合同", "招标要求", "项目证据上下文"],
    "output_schema": ["checks", "status", "evidence_receipts"],
    "quality_gate": "检查结果必须可追溯；未通过项进入问题清单。",
    "execution_stage": "chapter_generation",
    "may_call_provider": False,
}


AGENT_ROLE_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "主控Agent": {
        "input_boundary": ["评审目录", "章节合同", "质量门汇总"],
        "output_schema": ["chapter_plan", "responsibility_map", "delivery_decision"],
        "quality_gate": "每个评审章节必须有唯一责任边界和可执行交付状态。",
        "execution_stage": "planning_and_delivery",
    },
    "项目事实仲裁Agent": {
        "input_boundary": ["项目事实来源台账（不读取章节推测值）"],
        "output_schema": ["ledger_digest", "unresolved_fields", "validation"],
        "quality_gate": "台账摘要必须一致且未解决同级事实冲突数为0。",
        "execution_stage": "pre_model_fact_arbitration",
    },
    "要求证据矩阵Agent": {
        "input_boundary": ["招标评分项", "强制要求", "章节责任", "证据追踪结果"],
        "output_schema": ["matrix_digest", "coverage", "blocking_requirement_ids"],
        "quality_gate": "强制要求必须有响应章节及可反查证据，不得存在阻断项。",
        "execution_stage": "planning_and_delivery_gate",
    },
    "规范证据Agent": {
        "input_boundary": ["项目适用规范清单", "官方来源元数据", "章节规范引用"],
        "output_schema": ["verified_standard_count", "violations", "citation_integrity"],
        "quality_gate": "仅允许引用已核验现行规范，编号、版本和引用位置必须可追溯。",
        "execution_stage": "compliance_gate",
    },
    "跨专业接口Agent": {
        "input_boundary": ["清单重点项", "图纸索引", "规范索引", "章节闭环检查"],
        "output_schema": ["focus_item_coverage", "closure_coverage", "missing_locators"],
        "quality_gate": "重点项必须进入相应工序章节并形成图纸、规范和验收闭环。",
        "execution_stage": "chapter_and_global_review",
    },
    "专业渲染Agent": {
        "input_boundary": ["已通过内容门的Word源文档", "招标格式要求", "版式策略"],
        "output_schema": ["professional_docx", "render_receipt", "layout_metrics"],
        "quality_gate": "招标格式优先；无空白页、稀疏页、断裂表格或失控分页。",
        "execution_stage": "professional_render",
        "may_call_provider": True,
    },
    "文档视觉质检Agent": {
        "input_boundary": ["逐页渲染图", "版式指标", "图表清单"],
        "output_schema": ["page_findings", "visual_gate", "blocking_pages"],
        "quality_gate": "所有阻断级视觉缺陷清零后方可交付。",
        "execution_stage": "render_visual_gate",
    },
    "交付验收Agent": {
        "input_boundary": ["内容质量门", "证据矩阵", "规范审计", "图表门", "视觉门"],
        "output_schema": ["delivery_allowed", "blocking_issues", "receipts"],
        "quality_gate": "任一硬门未通过时禁止输出可交付成品。",
        "execution_stage": "final_delivery_gate",
    },
}


GLOBAL_REVIEW_AGENT_NAMES = (
    "全篇一致性Agent",
    "专业渲染Agent",
    "文档视觉质检Agent",
    "交付验收Agent",
)


def _role_record(name: str) -> Dict[str, Any]:
    contract = dict(_DEFAULT_ROLE_CONTRACT)
    contract.update(AGENT_ROLE_CONTRACTS.get(name) or {})
    return {"name": name, "directive": AGENT_ROLE_DIRECTIVES[name], **contract}


def select_auxiliary_agents(title: str, *, specialty_tags: List[str] | None = None) -> List[Dict[str, Any]]:
    """Select quality roles for one chapter without increasing provider concurrency.

    These roles are explicit review responsibilities carried by the chapter contract
    and prompt.  ``agent_parallelism`` remains the bounded number of chapter tasks.
    """

    text = " ".join([str(title or ""), *[str(x or "") for x in (specialty_tags or [])]]).lower()
    names = [
        "要求证据矩阵Agent",
        "招标评分响应Agent",
        "证据溯源Agent",
        "技术深度Agent",
        "风险闭环Agent",
        "全篇一致性Agent",
    ]

    if any(k in text for k in ("清单", "工程量", "材料", "采购", "计量", "造价", "重点项")):
        names.append("清单响应Agent")
    if any(
        k in text
        for k in (
            "图纸",
            "接口",
            "预留",
            "预埋",
            "机电",
            "安装",
            "结构",
            "道路",
            "桥",
            "管线",
            "排水",
            "装饰",
        )
    ):
        names.append("图纸接口Agent")
        names.append("跨专业接口Agent")
    if any(k in text for k in ("进度", "工期", "资源", "劳动力", "机械", "设备", "材料计划", "施工组织", "总平面")):
        names.append("进度资源Agent")
    if any(k in text for k in ("图", "流程", "网络计划", "平面", "进度", "工艺", "接口", "节点", "示意")):
        names.append("图表质量Agent")

    # Technical chapters benefit from BoQ and drawing/interface checks even when
    # their short title does not repeat those keywords.
    if any(k in text for k in ("施工", "方案", "工艺", "重难点", "质量", "安全")):
        if "清单响应Agent" not in names:
            names.append("清单响应Agent")
        if "图纸接口Agent" not in names:
            names.append("图纸接口Agent")
        if "跨专业接口Agent" not in names:
            names.append("跨专业接口Agent")
        if "图表质量Agent" not in names:
            names.append("图表质量Agent")

    return [_role_record(name) for name in names]


def _has_numeric_requirement(lines: List[str]) -> bool:
    for ln in lines:
        text = str(ln or "")
        if any(ch.isdigit() for ch in text):
            return True
    return False


@dataclass
class MultiAgentPlan:
    dispatch: Dict[str, Any]
    chapter_specialties: Dict[str, List[Dict[str, Any]]]
    master_agent: str = "主控Agent"
    compliance_agent: str = "合规Agent"

    def chapter_agents(self, title: str) -> Dict[str, Any]:
        picks = list(self.chapter_specialties.get(str(title), []) or [])
        specialist_agents = []
        specialty_tags = []
        domain_tags: List[str] = []
        for p in picks:
            gname = str(p.get("graph_name") or p.get("filename") or "").strip()
            if not gname:
                continue
            specialist_agents.append(f"专业Agent:{gname}")
            specialty_tags.append(gname.replace("图谱", "").strip())
            for dom in (p.get("domain_tags") or []):
                ds = str(dom).strip()
                if ds and ds not in domain_tags:
                    domain_tags.append(ds)
        if not specialist_agents:
            specialist_agents = ["专业Agent:通用施工"]
        auxiliary_agents = select_auxiliary_agents(title, specialty_tags=specialty_tags)
        return {
            "master": self.master_agent,
            "compliance": self.compliance_agent,
            "specialists": specialist_agents,
            "auxiliary": auxiliary_agents,
            "specialty_tags": specialty_tags,
            "domain_tags": domain_tags,
            "graphs": picks,
        }

    def chapter_graph_context(
        self,
        *,
        title: str,
        query: str,
        section_requirements: List[str] | None = None,
        top_k: int = 8,
    ) -> Dict[str, Any]:
        reqs = [str(x).strip() for x in (section_requirements or []) if str(x).strip()]
        need_experience = not _has_numeric_requirement(reqs)
        agents = self.chapter_agents(title)
        picks = list(agents.get("graphs") or [])
        if not picks:
            picks = list(self.dispatch.get("selected_graphs") or [])[:3]
        allowed_domains = [str(x).strip() for x in (agents.get("domain_tags") or []) if str(x).strip()]
        if not allowed_domains:
            allowed_domains = [str(x).strip() for x in (self.dispatch.get("involved_domains") or []) if str(x).strip()]
        hits = search_dispatch_graphs(query=query, graphs=picks, top_k=top_k, allowed_domains=allowed_domains or None)
        node_bindings = []
        seen = set()
        for h in hits:
            node = str(h.get("logical_node") or "").strip()
            if not node or node in seen:
                continue
            seen.add(node)
            node_bindings.append(node)
            if len(node_bindings) >= 8:
                break
        exp = extract_experience_values(hits, limit=4) if need_experience else []
        return {
            "hits": hits,
            "node_bindings": node_bindings,
            "experience_values": exp,
            "need_experience": need_experience,
            "agents": agents,
        }

    def summary(self) -> Dict[str, Any]:
        chapter_auxiliary_agents = {
            str(title): list(self.chapter_agents(str(title)).get("auxiliary") or [])
            for title in self.chapter_specialties
        }
        return {
            "master_agent": self.master_agent,
            "compliance_agent": self.compliance_agent,
            "detected_keywords": self.dispatch.get("detected_keywords") or [],
            "involved_domains": self.dispatch.get("involved_domains") or [],
            "selected_graphs": self.dispatch.get("selected_graphs") or [],
            "missing_graphs": self.dispatch.get("missing_graphs") or [],
            "chapter_agent_count": len(self.chapter_specialties),
            "agent_role_count": len(AGENT_ROLE_DIRECTIVES),
            "agent_role_catalog": [
                _role_record(name) for name in AGENT_ROLE_DIRECTIVES
            ],
            "chapter_auxiliary_agents": chapter_auxiliary_agents,
            "global_review_agents": [_role_record(name) for name in GLOBAL_REVIEW_AGENT_NAMES],
            "role_execution_policy": {
                "specialist_role_count": len(AGENT_ROLE_DIRECTIVES),
                "chapter_provider_concurrency_is_separate": True,
                "chapter_provider_concurrency_field": "agent_parallelism",
                "description": "专业角色定义质量责任；agent_parallelism只限制同时调用模型编写的章节任务。",
            },
        }


def build_agent_execution_ledger(
    *,
    plan_summary: Dict[str, Any] | None,
    content_review: Dict[str, Any] | None,
    contract_checks: Dict[str, Any] | None,
    standard_audit: Dict[str, Any] | None,
    media_quality: Dict[str, Any] | None = None,
    fact_ledger: Dict[str, Any] | None = None,
    requirement_matrix: Dict[str, Any] | None = None,
    cross_index: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Describe what each professional role actually checked.

    The ledger deliberately distinguishes a role from a provider call.  Most
    chapter roles execute through the shared chapter contract/prompt; global
    quality roles execute through deterministic gates or the existing review
    calls.  This prevents the UI from overstating the number of concurrent
    model requests while still making every responsibility auditable.
    """

    summary = dict(plan_summary or {})
    review = dict(content_review or {})
    dimensions = review.get("dimensions") if isinstance(review.get("dimensions"), dict) else {}
    contract = dict(contract_checks or {})
    standards = dict(standard_audit or {})
    media = dict(media_quality or {})
    facts = dict(fact_ledger or {})
    requirements = dict(requirement_matrix or {})
    interfaces = dict(cross_index or {})

    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for key, row in dimensions.items():
        if not isinstance(row, dict):
            continue
        agent = str(row.get("responsible_agent") or "交付验收Agent")
        by_agent.setdefault(agent, []).append(
            {
                "check": str(key),
                "label": str(row.get("label") or key),
                "score": row.get("score"),
                "pass": bool(row.get("pass")),
            }
        )

    records: List[Dict[str, Any]] = []
    chapter_bound = {
        "主控Agent", "要求证据矩阵Agent", "合规Agent", "证据溯源Agent", "清单响应Agent", "图纸接口Agent",
        "跨专业接口Agent",
        "进度资源Agent", "风险闭环Agent", "招标评分响应Agent", "技术深度Agent", "图表质量Agent",
    }
    for name, directive in AGENT_ROLE_DIRECTIVES.items():
        checks = list(by_agent.get(name) or [])
        execution_mode = "chapter_contract" if name in chapter_bound else "deterministic_gate"
        status = "completed"
        if any(not bool(row.get("pass")) for row in checks):
            status = "needs_attention"
        if name == "主控Agent":
            checks.append({"check": "chapter_plan", "pass": bool(summary.get("chapter_agent_count", 0) > 0)})
        elif name == "项目事实仲裁Agent":
            execution_mode = "pre_model_deterministic_gate"
            if not facts:
                status = "not_executed"
            else:
                validation = validate_project_fact_ledger(facts)
                checks.extend(
                    [
                        {"check": "ledger_integrity", "pass": bool(validation.get("ok"))},
                        {
                            "check": "unresolved_fact_conflicts",
                            "pass": not bool(validation.get("unresolved_fields")),
                            "unresolved_fields": list(validation.get("unresolved_fields") or []),
                        },
                        {"check": "project_fact_binding", "pass": bool(facts.get("facts"))},
                    ]
                )
        elif name == "要求证据矩阵Agent":
            execution_mode = "hybrid_contract_gate"
            if not requirements:
                status = "not_executed"
            else:
                validation = validate_requirement_evidence_matrix(requirements)
                req_summary = requirements.get("summary") if isinstance(requirements.get("summary"), dict) else {}
                checks.extend(
                    [
                        {"check": "matrix_integrity", "pass": bool(validation.get("ok"))},
                        {
                            "check": "mandatory_requirement_closure",
                            "pass": int(req_summary.get("blocking_count") or 0) == 0,
                            "blocking_requirement_ids": list(req_summary.get("blocking_requirement_ids") or []),
                        },
                        {
                            "check": "strict_delivery_allowed",
                            "pass": bool(req_summary.get("strict_delivery_allowed")),
                        },
                    ]
                )
        elif name == "合规Agent":
            checks.extend(
                [
                    {"check": "agent_contract", "pass": bool(contract.get("ok", True))},
                    {"check": "standard_citations", "pass": bool(standards.get("ok", True))},
                ]
            )
        elif name == "规范证据Agent":
            execution_mode = "standard_citation_integrity"
            checks.append({"check": "standard_citations", "pass": bool(standards.get("ok", True))})
            if "verified_standard_count" in standards:
                checks.append(
                    {
                        "check": "verified_standard_inventory",
                        "pass": int(standards.get("verified_standard_count") or 0) > 0,
                        "verified_standard_count": int(standards.get("verified_standard_count") or 0),
                    }
                )
        elif name == "跨专业接口Agent":
            execution_mode = "hybrid_contract_gate"
            if not interfaces:
                status = "not_executed"
            else:
                focus_count = int(interfaces.get("focus_count") or 0)
                mentioned_count = int(interfaces.get("mentioned_count") or 0)
                closed_count = int(interfaces.get("closed_ok_count") or 0)
                missing_drawing = int(interfaces.get("missing_drawing_locator_count") or 0)
                missing_standard = int(interfaces.get("missing_standard_locator_count") or 0)
                checks.extend(
                    [
                        {"check": "cross_index_available", "pass": bool(interfaces.get("ok", True))},
                        {
                            "check": "focus_item_coverage",
                            "pass": focus_count == 0 or mentioned_count >= focus_count,
                            "focus_count": focus_count,
                            "mentioned_count": mentioned_count,
                        },
                        {
                            "check": "cross_evidence_closure",
                            "pass": focus_count == 0 or closed_count >= focus_count,
                            "closed_ok_count": closed_count,
                        },
                        {
                            "check": "locator_completeness",
                            "pass": missing_drawing == 0 and missing_standard == 0,
                            "missing_drawing_locator_count": missing_drawing,
                            "missing_standard_locator_count": missing_standard,
                        },
                    ]
                )
        elif name == "图表质量Agent" and media:
            checks.append({"check": "media_quality", "pass": bool(media.get("ok", True))})
        elif name == "专业渲染Agent":
            execution_mode = "render_pipeline"
        elif name == "文档视觉质检Agent":
            execution_mode = "render_visual_gate"
        elif name == "交付验收Agent":
            gate = review.get("quality_gate") if isinstance(review.get("quality_gate"), dict) else {}
            checks.append({"check": "independent_content_quality", "pass": bool(gate.get("pass", True))})

        failed = [row for row in checks if row.get("pass") is False]
        if failed and status != "not_executed":
            status = (
                "blocked"
                if name in {"项目事实仲裁Agent", "要求证据矩阵Agent", "合规Agent", "规范证据Agent", "交付验收Agent"}
                else "needs_attention"
            )
        contract_meta = _role_record(name)
        records.append(
            {
                "agent": name,
                "directive": directive,
                "input_boundary": contract_meta["input_boundary"],
                "output_schema": contract_meta["output_schema"],
                "quality_gate": contract_meta["quality_gate"],
                "execution_stage": contract_meta["execution_stage"],
                "may_call_provider": contract_meta["may_call_provider"],
                "execution_mode": execution_mode,
                "status": status,
                "checks": checks,
            }
        )

    return {
        "version": "agent-execution-ledger-v2",
        "role_count": len(records),
        "completed_count": sum(1 for row in records if row["status"] == "completed"),
        "needs_attention_count": sum(1 for row in records if row["status"] == "needs_attention"),
        "blocked_count": sum(1 for row in records if row["status"] == "blocked"),
        "not_executed_count": sum(1 for row in records if row["status"] == "not_executed"),
        "records": records,
    }


def build_multi_agent_plan(
    *,
    topic: str | None = None,
    outline: List[str] | None = None,
    requirements: List[str] | None = None,
    tender: Dict[str, Any] | None = None,
) -> MultiAgentPlan:
    dispatch = detect_specialty_dispatch(
        topic=topic,
        outline=outline or [],
        requirements=requirements or [],
        tender=tender or {},
    )
    chapter_specialties = assign_specialties_to_outline(outline or [], dispatch)
    return MultiAgentPlan(
        dispatch=dispatch,
        chapter_specialties=chapter_specialties,
    )
