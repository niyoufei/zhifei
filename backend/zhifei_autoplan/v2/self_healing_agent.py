from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.zhifei_autoplan.utils.llm_client import LLMClient


DEFAULT_PATCH_FILE = "_auto_generated/self_healing_patch_nodes.json"


DIMENSION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "质量": {
        "applicable_conditions": {"climate": "常温5-35C", "geology": "一般地质条件"},
        "resource_requirements": {
            "inspection_frequency_per_batch": 1,
            "sampling_frequency_per_100m3": 1,
            "checker_role": "质量员",
            "acceptance_pass_rate_target_percent": 95,
        },
        "safety_level": "medium",
        "reference_standard": ["GB 50300-2013", "GB 50204-2015", "JGJ 107-2016"],
        "formula_expression": "",
        "formula_variables": [],
    },
    "安全": {
        "applicable_conditions": {"climate": "大风/暴雨停工阈值执行", "geology": "深基坑专项论证"},
        "resource_requirements": {
            "safety_inspection_frequency_per_day": 2,
            "leakage_protector_ma": 30,
            "emergency_response_minutes": 30,
            "checker_role": "安全员",
        },
        "safety_level": "high",
        "reference_standard": ["JGJ 59-2011", "JGJ 46-2005", "GB 50720-2011"],
        "formula_expression": "",
        "formula_variables": [],
    },
    "进度": {
        "applicable_conditions": {"climate": "雨季施工调整", "geology": "工序受地质条件影响"},
        "resource_requirements": {
            "critical_interval_days": 1,
            "resource_peak_workers": 40,
            "resource_peak_equipment": 8,
            "deviation_correction_hours": 24,
        },
        "safety_level": "medium",
        "reference_standard": ["GB/T 50326-2017", "GB 50500-2013"],
        "formula_expression": "(work_volume / max(productivity_per_day, 1)) + min_interval_days",
        "formula_variables": ["work_volume", "productivity_per_day", "min_interval_days"],
    },
    "环保": {
        "applicable_conditions": {"climate": "干燥多风天气加强喷淋", "geology": "土方裸露面覆盖"},
        "resource_requirements": {
            "pm10_threshold_ug_m3": 150,
            "noise_day_db": 70,
            "noise_night_db": 55,
            "inspection_frequency_per_day": 2,
        },
        "safety_level": "medium",
        "reference_standard": ["GB 16297-1996", "GB 12523-2011", "JGJ 146-2013"],
        "formula_expression": "",
        "formula_variables": [],
    },
    "重难点": {
        "applicable_conditions": {"climate": "高温/低温专项措施", "geology": "复杂地层专项方案"},
        "resource_requirements": {
            "specialist_workers": 12,
            "special_equipment_sets": 3,
            "risk_trigger_threshold_percent": 5,
            "acceptance_loop_hours": 12,
        },
        "safety_level": "high",
        "reference_standard": ["GB 50666-2011", "JGJ 80-2016", "JGJ 59-2011"],
        "formula_expression": "base_crew + round(risk_factor * complexity_index)",
        "formula_variables": ["base_crew", "risk_factor", "complexity_index"],
    },
    "扣分点": {
        "applicable_conditions": {"climate": "不适用", "geology": "不适用"},
        "resource_requirements": {
            "response_deadline_hours": 4,
            "recheck_frequency_per_day": 2,
            "checker_role": "项目总工",
            "closed_loop_timeout_hours": 24,
        },
        "safety_level": "medium",
        "reference_standard": ["GB 50300-2013", "JGJ 59-2011"],
        "formula_expression": "",
        "formula_variables": [],
    },
}


def _extract_json(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    if "```" in raw:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.S | re.I)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
    return {}


def _normalize_formula_vars(raw: Any) -> List[str]:
    out: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            text = str(item or "").strip()
            if text and text not in out:
                out.append(text)
        return out
    if isinstance(raw, str):
        for item in re.split(r"[,\s;，；]+", raw):
            text = str(item or "").strip()
            if text and text not in out:
                out.append(text)
    return out


class SelfHealingAgent:
    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        defaults = LLMClient.load_defaults() or {}
        self.provider = (
            provider
            or os.getenv("ZF_DEFAULT_PROVIDER")
            or defaults.get("default_provider")
            or "google"
        )
        self.model = (
            model
            or os.getenv("ZF_DEFAULT_MODEL")
            or defaults.get("default_model")
            or "gemini-3.1-pro-preview"
        )
        self.api_key = api_key or self._resolve_api_key(self.provider)
        self._llm = LLMClient(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
        )

    def _resolve_api_key(self, provider: str) -> Optional[str]:
        p = str(provider or "").strip().lower()
        if p == "google":
            return os.getenv("ZF_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if p == "openai":
            return os.getenv("ZF_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if p == "anthropic":
            return os.getenv("ZF_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if p == "deepseek":
            return os.getenv("ZF_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if p == "qwen":
            return os.getenv("ZF_QWEN_API_KEY") or os.getenv("QWEN_API_KEY")
        if p == "zhipu":
            return os.getenv("ZF_ZHIPU_API_KEY") or os.getenv("ZHIPU_API_KEY")
        return None

    def _build_prompt(self, gaps: List[Dict[str, Any]]) -> str:
        payload = []
        for item in gaps:
            payload.append(
                {
                    "type": item.get("type"),
                    "dimension": item.get("dimension"),
                    "required_keywords": item.get("required_keywords") or [],
                    "query": item.get("query") or "",
                }
            )
        return (
            "你是中国工程总承包投标与施工组织设计专家。\n"
            "任务：根据下面的知识盲区清单，生成可直接写入知识图谱的节点补丁。\n"
            "要求：\n"
            "1) parameter_missing 类型 -> 生成 EngineeringNode。\n"
            "2) formula_missing 类型 -> 生成 FormulaNode，必须包含 formula_expression 与 formula_variables。\n"
            "3) 所有节点必须有 reference_standard(数组，列出GB/JGJ/SL规范号) 与 is_auto_generated=true。\n"
            "4) 所有节点必须提供 applicable_conditions、resource_requirements、safety_level、source_hierarchy='国标'。\n"
            "5) 参数需给出可执行红线值（阈值/频次/时限/岗位），避免空话。\n"
            "6) 仅返回 JSON，不要返回解释文字，格式：\n"
            "{\n"
            "  \"nodes\": [\n"
            "    {\n"
            "      \"node_id\": \"AUTO-...\",\n"
            "      \"name\": \"...\",\n"
            "      \"node_type\": \"EngineeringNode|FormulaNode\",\n"
            "      \"object_key\": \"...\",\n"
            "      \"source_hierarchy\": \"国标\",\n"
            "      \"qt_tag\": [\"质量\"],\n"
            "      \"keywords\": [\"...\"],\n"
            "      \"content\": {\"action\": \"...\", \"checker\": \"...\", \"parameter\": {...}},\n"
            "      \"applicable_conditions\": {...},\n"
            "      \"resource_requirements\": {...},\n"
            "      \"safety_level\": \"low|medium|high|critical\",\n"
            "      \"reference_standard\": [\"GB ...\"],\n"
            "      \"is_auto_generated\": true,\n"
            "      \"formula_expression\": \"...\",\n"
            "      \"formula_variables\": [\"...\"]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            f"盲区清单：{json.dumps(payload, ensure_ascii=False)}"
        )

    def _fallback_nodes(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        for idx, gap in enumerate(gaps, start=1):
            dimension = str(gap.get("dimension") or "未知维度")
            gap_type = str(gap.get("type") or "")
            conf = DIMENSION_DEFAULTS.get(dimension, DIMENSION_DEFAULTS["质量"])
            is_formula = gap_type == "formula_missing"
            node_type = "FormulaNode" if is_formula else "EngineeringNode"
            node_id = f"AUTO-{dimension}-{('FORMULA' if is_formula else 'PARAM')}-{idx}"
            title = f"{dimension}自动补全{'公式' if is_formula else '参数'}节点"
            keywords = [str(x) for x in (gap.get("required_keywords") or []) if str(x).strip()]

            content = {
                "action": f"执行{dimension}控制措施",
                "checker": "项目总工" if dimension in {"扣分点", "重难点"} else "专业工程师",
                "parameter": conf.get("resource_requirements") or {},
            }

            nodes.append(
                {
                    "node_id": node_id,
                    "name": title,
                    "node_type": node_type,
                    "object_key": f"auto_{dimension}_{'formula' if is_formula else 'param'}",
                    "source_hierarchy": "国标",
                    "qt_tag": [dimension, "auto_generated"],
                    "keywords": keywords,
                    "content": content,
                    "applicable_conditions": conf.get("applicable_conditions") or {},
                    "resource_requirements": conf.get("resource_requirements") or {},
                    "safety_level": conf.get("safety_level") or "medium",
                    "reference_standard": conf.get("reference_standard") or ["GB 50300-2013"],
                    "is_auto_generated": True,
                    "formula_expression": conf.get("formula_expression") if is_formula else "",
                    "formula_variables": conf.get("formula_variables") if is_formula else [],
                }
            )
        return nodes

    def _sanitize_nodes(self, raw_nodes: List[Dict[str, Any]], gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not raw_nodes:
            return self._fallback_nodes(gaps)

        fallback_map: Dict[str, Dict[str, Any]] = {}
        for item in gaps:
            dim = str(item.get("dimension") or "质量")
            fallback_map[dim] = DIMENSION_DEFAULTS.get(dim, DIMENSION_DEFAULTS["质量"])

        out: List[Dict[str, Any]] = []
        for idx, node in enumerate(raw_nodes, start=1):
            if not isinstance(node, dict):
                continue
            dim = ""
            tags = node.get("qt_tag")
            if isinstance(tags, list):
                for tag in tags:
                    text = str(tag)
                    if text in DIMENSION_DEFAULTS:
                        dim = text
                        break
            if not dim:
                name = str(node.get("name") or "")
                for candidate in DIMENSION_DEFAULTS.keys():
                    if candidate in name:
                        dim = candidate
                        break
            if not dim:
                dim = "质量"
            conf = fallback_map.get(dim, DIMENSION_DEFAULTS["质量"])

            node_type = str(node.get("node_type") or "EngineeringNode").strip() or "EngineeringNode"
            is_formula = node_type == "FormulaNode"
            node_id = str(node.get("node_id") or f"AUTO-{dim}-{idx}").strip()
            name = str(node.get("name") or f"{dim}自动补全节点").strip()
            object_key = str(node.get("object_key") or f"auto_{dim}_{idx}").strip()
            source_hierarchy = str(node.get("source_hierarchy") or "国标").strip() or "国标"
            qt_tag = node.get("qt_tag")
            if not isinstance(qt_tag, list) or not qt_tag:
                qt_tag = [dim, "auto_generated"]

            keywords = node.get("keywords")
            if not isinstance(keywords, list):
                keywords = []

            content = node.get("content")
            if not isinstance(content, dict):
                content = {
                    "action": f"执行{dim}控制措施",
                    "checker": "专业工程师",
                    "parameter": conf.get("resource_requirements") or {},
                }

            applicable = node.get("applicable_conditions")
            if not isinstance(applicable, dict) or not applicable:
                applicable = conf.get("applicable_conditions") or {}

            resources = node.get("resource_requirements")
            if not isinstance(resources, dict) or not resources:
                resources = conf.get("resource_requirements") or {}

            safety = str(node.get("safety_level") or conf.get("safety_level") or "medium").strip().lower()
            if safety not in {"low", "medium", "high", "critical"}:
                safety = "medium"

            standards = node.get("reference_standard")
            if isinstance(standards, str):
                standards = [standards]
            if not isinstance(standards, list) or not standards:
                standards = conf.get("reference_standard") or ["GB 50300-2013"]
            standards = [str(x).strip() for x in standards if str(x).strip()]

            formula_expression = str(node.get("formula_expression") or "").strip()
            formula_variables = _normalize_formula_vars(node.get("formula_variables"))
            if is_formula and not formula_expression:
                formula_expression = str(conf.get("formula_expression") or "").strip()
            if is_formula and not formula_variables:
                formula_variables = _normalize_formula_vars(conf.get("formula_variables"))
            if not is_formula:
                formula_expression = ""
                formula_variables = []

            out.append(
                {
                    "node_id": node_id,
                    "name": name,
                    "node_type": node_type,
                    "object_key": object_key,
                    "source_hierarchy": source_hierarchy,
                    "qt_tag": qt_tag,
                    "keywords": keywords,
                    "content": content,
                    "applicable_conditions": applicable,
                    "resource_requirements": resources,
                    "safety_level": safety,
                    "reference_standard": standards,
                    "is_auto_generated": True,
                    "formula_expression": formula_expression,
                    "formula_variables": formula_variables,
                }
            )

        if not out:
            return self._fallback_nodes(gaps)
        return out

    async def build_patch_nodes(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not gaps:
            return {
                "ok": True,
                "provider": self.provider,
                "model": self.model,
                "used_fallback": False,
                "nodes": [],
            }

        prompt = self._build_prompt(gaps)
        resp = await self._llm.complete(prompt)
        parsed = _extract_json(str(resp.get("text") or ""))
        raw_nodes = parsed.get("nodes") if isinstance(parsed, dict) else None
        if not isinstance(raw_nodes, list):
            raw_nodes = []

        used_fallback = False
        nodes = self._sanitize_nodes(raw_nodes, gaps)
        if not raw_nodes:
            used_fallback = True

        return {
            "ok": True,
            "provider": str(resp.get("provider") or self.provider),
            "model": str(resp.get("model") or self.model),
            "llm_error": resp.get("error"),
            "used_fallback": used_fallback or bool(resp.get("error")),
            "nodes": nodes,
        }

    def persist_patch_nodes(
        self,
        *,
        graph_root: Path | str,
        nodes: List[Dict[str, Any]],
        patch_file: str = DEFAULT_PATCH_FILE,
    ) -> Dict[str, Any]:
        root = Path(graph_root)
        out = root / patch_file
        out.parent.mkdir(parents=True, exist_ok=True)

        existing_nodes: List[Dict[str, Any]] = []
        if out.exists():
            try:
                raw = json.loads(out.read_text(encoding="utf-8"))
                existing_nodes = list(
                    (((raw or {}).get("knowledge_database") or {}).get("core") or {}).get("nodes") or []
                )
            except Exception:
                existing_nodes = []

        merged: Dict[str, Dict[str, Any]] = {}
        for item in existing_nodes:
            if not isinstance(item, dict):
                continue
            nid = str(item.get("node_id") or "").strip()
            if nid:
                merged[nid] = item
        for item in nodes:
            if not isinstance(item, dict):
                continue
            nid = str(item.get("node_id") or "").strip()
            if not nid:
                continue
            merged[nid] = item

        payload = {
            "name": "auto-self-healing-patch",
            "domain": "auto_generated",
            "source_hierarchy": "国标",
            "knowledge_database": {
                "core": {
                    "nodes": list(merged.values()),
                }
            },
            "meta": {
                "is_auto_generated": True,
                "node_count": len(merged),
            },
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "saved_at": str(out), "node_count": len(nodes), "merged_node_count": len(merged)}
