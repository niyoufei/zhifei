from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


class QuantitativeSupportError(Exception):
    """Raised when generated content lacks mandatory numeric/graph data support."""


@dataclass
class ProcessRule:
    keywords: Tuple[str, ...]
    process_name: str
    stage: int
    default_resources: Tuple[str, ...]
    productivity_per_day: float


PROCESS_RULES: Tuple[ProcessRule, ...] = (
    ProcessRule(("测量", "放线"), "测量放线", 1, ("测量工",), 4000.0),
    ProcessRule(("土方", "开挖", "回填"), "土方工程", 2, ("挖机", "装载机", "测量工"), 1200.0),
    ProcessRule(("桩", "基础", "承台", "垫层"), "基础工程", 3, ("钢筋工", "混凝土工"), 850.0),
    ProcessRule(("钢筋", "模板", "混凝土"), "主体结构", 4, ("钢筋工", "模板工", "混凝土工"), 700.0),
    ProcessRule(("砌体", "抹灰", "屋面", "防水"), "围护与建筑构造", 5, ("防水工", "抹灰工"), 650.0),
    ProcessRule(("管道", "电缆", "桥架", "暖通", "消防"), "机电安装", 6, ("电工", "管道工", "焊工"), 500.0),
    ProcessRule(("装修", "涂料", "门窗", "幕墙"), "装饰装修", 7, ("安装工", "油漆工"), 480.0),
    ProcessRule(("道路", "绿化", "附属", "场地"), "室外附属", 8, ("机械设备操作工", "测量工"), 900.0),
)

DEFAULT_RULE = ProcessRule(("通用",), "综合收尾", 9, ("项目管理人员",), 400.0)


class QuantitativeBoQEngine:
    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value)
        cleaned = re.sub(r"[^\d.\-]+", "", text)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except Exception:
            return None

    def _pick_rule(self, item_name: str) -> ProcessRule:
        name = str(item_name or "")
        for rule in PROCESS_RULES:
            if any(keyword in name for keyword in rule.keywords):
                return rule
        return DEFAULT_RULE

    def _estimate_duration_days(self, quantity: float | None, rule: ProcessRule) -> int:
        if quantity is None or quantity <= 0:
            return 1
        return max(1, int(math.ceil(quantity / max(1.0, rule.productivity_per_day))))

    def build_mapping(self, boq_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        mapping: Dict[str, Dict[str, Any]] = {}
        process_nodes: Dict[str, Dict[str, Any]] = {}

        for idx, item in enumerate(boq_items, start=1):
            name = str(item.get("name") or f"item_{idx}").strip()
            rule = self._pick_rule(name)
            quantity = self._to_float(item.get("quantity"))
            duration = self._estimate_duration_days(quantity, rule)

            resources = [str(r).strip() for r in (item.get("resources") or []) if str(r).strip()]
            if not resources:
                resources = list(rule.default_resources)

            mapping[name] = {
                "boq_code": item.get("boq_code"),
                "quantity": quantity,
                "unit": item.get("unit"),
                "process": rule.process_name,
                "stage": rule.stage,
                "duration_days": duration,
                "resources": resources,
                "predecessors": [],
                "successors": [],
            }

            node = process_nodes.setdefault(
                rule.process_name,
                {
                    "process": rule.process_name,
                    "stage": rule.stage,
                    "duration_days": 0,
                    "resources": set(),
                    "items": [],
                },
            )
            node["duration_days"] = max(node["duration_days"], duration)
            node["resources"].update(resources)
            node["items"].append(name)

        process_list = sorted(process_nodes.values(), key=lambda x: (x["stage"], x["process"]))
        for node in process_list:
            node["resources"] = sorted(node["resources"])

        stage_to_processes: Dict[int, List[str]] = defaultdict(list)
        for node in process_list:
            stage_to_processes[int(node["stage"])].append(str(node["process"]))

        edges: List[Dict[str, Any]] = []
        stages = sorted(stage_to_processes.keys())
        for idx, stage in enumerate(stages):
            if idx == len(stages) - 1:
                continue
            next_stage = stages[idx + 1]
            for src in stage_to_processes[stage]:
                for dst in stage_to_processes[next_stage]:
                    lag = max(1, next_stage - stage)
                    edges.append({"from": src, "to": dst, "lag_days": lag})

        predecessors_by_process: Dict[str, List[str]] = defaultdict(list)
        successors_by_process: Dict[str, List[str]] = defaultdict(list)
        for edge in edges:
            predecessors_by_process[edge["to"]].append(edge["from"])
            successors_by_process[edge["from"]].append(edge["to"])

        for item_name, payload in mapping.items():
            process = payload["process"]
            payload["predecessors"] = sorted(set(predecessors_by_process.get(process, [])))
            payload["successors"] = sorted(set(successors_by_process.get(process, [])))

        return {
            "items": mapping,
            "process_nodes": process_list,
            "process_edges": edges,
        }

    def _compute_cpm(self, process_nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        durations = {str(n["process"]): int(n.get("duration_days") or 1) for n in process_nodes}
        preds: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        succs: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        in_degree: Dict[str, int] = {name: 0 for name in durations.keys()}

        for edge in edges:
            src = str(edge["from"])
            dst = str(edge["to"])
            lag = int(edge.get("lag_days") or 1)
            preds[dst].append((src, lag))
            succs[src].append((dst, lag))
            in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = deque([name for name, deg in in_degree.items() if deg == 0])
        topo: List[str] = []
        while queue:
            node = queue.popleft()
            topo.append(node)
            for nxt, _ in succs.get(node, []):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(topo) != len(durations):
            raise ValueError("process network contains a cycle; CPM requires DAG")

        es: Dict[str, int] = {}
        ef: Dict[str, int] = {}
        for node in topo:
            start = 0
            for prev, lag in preds.get(node, []):
                start = max(start, ef[prev] + lag)
            es[node] = start
            ef[node] = start + durations[node]

        project_duration = max(ef.values()) if ef else 0

        lf: Dict[str, int] = {}
        ls: Dict[str, int] = {}
        for node in reversed(topo):
            if not succs.get(node):
                lf[node] = project_duration
            else:
                lf[node] = min(ls[nxt] - lag for nxt, lag in succs[node])
            ls[node] = lf[node] - durations[node]

        rows: List[Dict[str, Any]] = []
        critical_path: List[str] = []
        for node in topo:
            slack = ls[node] - es[node]
            is_critical = slack == 0
            if is_critical:
                critical_path.append(node)
            rows.append(
                {
                    "process": node,
                    "duration_days": durations[node],
                    "ES": es[node],
                    "EF": ef[node],
                    "LS": ls[node],
                    "LF": lf[node],
                    "slack": slack,
                    "is_critical": is_critical,
                    "predecessors": [p for p, _ in preds.get(node, [])],
                    "successors": [s for s, _ in succs.get(node, [])],
                }
            )

        min_interval = min((int(edge.get("lag_days") or 1) for edge in edges), default=1)
        critical_ratio = (len(critical_path) / max(1, len(process_nodes)))
        long_duration_ratio = (project_duration / max(1, sum(durations.values())))
        risk_index = round(min(1.0, critical_ratio * 0.65 + long_duration_ratio * 0.35), 4)

        return {
            "process_schedule": rows,
            "critical_path": critical_path,
            "project_duration_days": project_duration,
            "min_process_interval_days": min_interval,
            "risk_index": risk_index,
        }

    def build_quantitative_index(self, boq_payload: Dict[str, Any]) -> Dict[str, Any]:
        items = boq_payload.get("items") if isinstance(boq_payload.get("items"), list) else []
        mapping = self.build_mapping(items)
        cpm = self._compute_cpm(mapping["process_nodes"], mapping["process_edges"])

        return {
            "mapping_3d": mapping["items"],
            "process_network": {
                "nodes": mapping["process_nodes"],
                "edges": mapping["process_edges"],
            },
            "cpm": cpm,
        }


def assert_paragraph_quantitative_support(
    paragraph: str,
    *,
    boq_support: Dict[str, Any] | None = None,
    graph_support: Dict[str, Any] | None = None,
) -> None:
    text = str(paragraph or "")
    has_numeric = bool(re.search(r"\d+(?:\.\d+)?", text))
    has_unit = bool(re.search(r"(mm|cm|m|kg|t|h|小时|天|次|人|台|套|%)", text, re.IGNORECASE))

    boq_ok = False
    if isinstance(boq_support, dict):
        boq_ok = any(
            boq_support.get(key) not in (None, "", [], {})
            for key in ("boq_code", "quantity", "process", "resources", "duration_days")
        )

    graph_ok = False
    if isinstance(graph_support, dict):
        graph_ok = any(
            graph_support.get(key) not in (None, "", [], {})
            for key in ("node_id", "title", "source_path", "keywords")
        )

    if not has_numeric or not has_unit:
        raise QuantitativeSupportError("paragraph is missing numeric parameter/unit support")
    if not (boq_ok or graph_ok):
        raise QuantitativeSupportError("paragraph has no BOQ or knowledge-graph evidence support")


def assert_section_bundle_support(
    sections: List[Dict[str, Any]],
    *,
    support_by_title: Dict[str, Dict[str, Any]],
    graph_hits_by_title: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    graph_hits_by_title = graph_hits_by_title or {}
    for section in sections:
        title = str(section.get("title") or "")
        paragraph = section.get("content") or ""
        boq_support = support_by_title.get(title) or {}
        graph_support = graph_hits_by_title.get(title) or {}
        assert_paragraph_quantitative_support(paragraph, boq_support=boq_support, graph_support=graph_support)
