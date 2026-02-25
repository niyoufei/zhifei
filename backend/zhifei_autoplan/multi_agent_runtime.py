from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from backend.zhifei_autoplan.graph_dispatcher import (
    assign_specialties_to_outline,
    detect_specialty_dispatch,
    extract_experience_values,
    search_dispatch_graphs,
)


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
        for p in picks:
            gname = str(p.get("graph_name") or p.get("filename") or "").strip()
            if not gname:
                continue
            specialist_agents.append(f"专业Agent:{gname}")
            specialty_tags.append(gname.replace("图谱", "").strip())
        if not specialist_agents:
            specialist_agents = ["专业Agent:通用施工"]
        return {
            "master": self.master_agent,
            "compliance": self.compliance_agent,
            "specialists": specialist_agents,
            "specialty_tags": specialty_tags,
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
        hits = search_dispatch_graphs(query=query, graphs=picks, top_k=top_k)
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
        return {
            "master_agent": self.master_agent,
            "compliance_agent": self.compliance_agent,
            "detected_keywords": self.dispatch.get("detected_keywords") or [],
            "selected_graphs": self.dispatch.get("selected_graphs") or [],
            "missing_graphs": self.dispatch.get("missing_graphs") or [],
            "chapter_agent_count": len(self.chapter_specialties),
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

