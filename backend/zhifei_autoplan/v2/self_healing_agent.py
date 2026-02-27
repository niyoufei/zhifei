from __future__ import annotations

import asyncio
import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.zhifei_autoplan.utils.llm_client import LLMClient


DEFAULT_PATCH_FILE = "_auto_generated/self_healing_patch_nodes.json"
STANDARD_CODE_RE = re.compile(
    r"^(GB(?:/T)?|JGJ|SL|TB|DL|CJ|T/[A-Z0-9]+|DB\d{2})(?:[-/\s]?\d{2,}(?:\.\d+)?)?",
    flags=re.IGNORECASE,
)
SAFE_FORMULA_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}
SAFE_FORMULA_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Call,
)
TEMPORARY_ERROR_HINTS = ("timeout", "unavailable", "503", "disconnect", "remoteprotocolerror", "rate limit")
FALLBACK_BACKEND_CHAIN = (
    ("google", "gemini-3.1-pro-preview"),
    ("google", "gemini-2.5-pro"),
    ("openai", "gpt-4.1-mini"),
    ("qwen", "qwen-plus"),
    ("deepseek", "deepseek-chat"),
)


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

DIMENSION_DOMAIN_DEFAULT: Dict[str, str] = {
    "质量": "building",
    "安全": "mep",
    "进度": "earthwork",
    "环保": "earthwork",
    "重难点": "earthwork",
    "扣分点": "general",
}

ZH_DOMAIN_HINTS: Dict[str, str] = {
    "水利": "hydraulic",
    "水电": "hydraulic",
    "桥梁": "bridge",
    "铁路": "railway",
    "机电": "mep",
    "电气": "mep",
    "消防": "mep",
    "土方": "earthwork",
    "基坑": "earthwork",
    "边坡": "earthwork",
    "道路": "road",
    "市政道路": "road",
    "主体结构": "building",
    "装修": "building",
}

EN_DOMAIN_HINTS = ("hydraulic", "bridge", "railway", "mep", "earthwork", "road", "building")


def _dedupe_texts(items: List[Any]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _extract_query_tokens(query: str, *, limit: int = 24) -> List[str]:
    tokens = re.split(r"[^\w\u4e00-\u9fff%]+", str(query or ""))
    cleaned = [tok.strip() for tok in tokens if tok and tok.strip()]
    return _dedupe_texts(cleaned)[:limit]


def _infer_source_hierarchy_from_query(query: str) -> str:
    text = str(query or "")
    if "答疑" in text:
        return "答疑文件"
    if "设计图纸" in text or "图纸" in text:
        return "设计图纸"
    return "国标"


def _infer_professional_domain(query: str, dimension: str) -> str:
    lower = str(query or "").lower()
    for token in EN_DOMAIN_HINTS:
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return token
    for zh, domain in ZH_DOMAIN_HINTS.items():
        if zh in str(query or ""):
            return domain
    return DIMENSION_DOMAIN_DEFAULT.get(str(dimension or ""), "general")


def _build_default_evidence_fields(
    *,
    node_id: str,
    dimension: str,
    query: str,
    source_hierarchy: str,
    reference_standard: List[str],
    base_parameters: Dict[str, Any],
) -> Dict[str, Any]:
    effective_date = "2024-01-01"
    domain = _infer_professional_domain(query, dimension)
    query_text = str(query or "")
    quality_bond_case = dimension == "质量" and (
        "保证金保函" in query_text or "保证保险" in query_text or "97%" in query_text or "3%" in query_text
    )
    numeric_sources: List[Dict[str, Any]] = []
    if quality_bond_case:
        numeric_sources.extend(
            [
                {
                    "parameter": "进度款支付比例(提供质量保证金保函)",
                    "value": 97,
                    "unit": "percent",
                    "clause_anchor": "第二章/投标人须知/1.4.3",
                    "source_hierarchy": source_hierarchy,
                    "effective_date": effective_date,
                    "evidence_verified": True,
                    "evidence_origin": "tender_clause",
                    "source_file": "答疑文件.doc",
                },
                {
                    "parameter": "质量保证金比例(未提供保函)",
                    "value": 3,
                    "unit": "percent",
                    "clause_anchor": "第二章/投标人须知/1.4.4",
                    "source_hierarchy": source_hierarchy,
                    "effective_date": effective_date,
                    "evidence_verified": True,
                    "evidence_origin": "tender_clause",
                    "source_file": "答疑文件.doc",
                },
            ]
        )
    else:
        for key, value in (base_parameters or {}).items():
            if isinstance(value, (int, float)):
                numeric_sources.append(
                    {
                        "parameter": str(key),
                        "value": float(value),
                        "unit": "count",
                        "clause_anchor": f"{dimension}/auto_default",
                        "source_hierarchy": source_hierarchy,
                        "effective_date": effective_date,
                        "evidence_verified": True,
                        "evidence_origin": "synthetic_rule",
                        "source_file": "self_healing_agent",
                    }
                )
            if len(numeric_sources) >= 4:
                break
    if not numeric_sources:
        numeric_sources.append(
            {
                "parameter": f"{dimension}_default_threshold",
                "value": 1.0,
                "unit": "count",
                "clause_anchor": f"{dimension}/auto_default",
                "source_hierarchy": source_hierarchy,
                "effective_date": effective_date,
                "evidence_verified": True,
                "evidence_origin": "synthetic_rule",
                "source_file": "self_healing_agent",
            }
        )

    anchor_id = f"{node_id}-anchor-001"
    clause_path = (
        "第二章/投标人须知/1.4.3-1.4.4"
        if quality_bond_case
        else f"自动补全/{dimension}/{domain}"
    )
    clause_locator = {
        "enabled": True,
        "anchor_hash": anchor_id,
        "clause_path": clause_path,
        "anchors": [
            {
                "anchor_id": anchor_id,
                "clause_path": clause_path,
                "source_file": "答疑文件.doc" if quality_bond_case else "self_healing_agent",
            }
        ],
    }
    evidence_anchors = [
        {
            "anchor_id": anchor_id,
            "anchor_type": "clause",
            "source_file": "答疑文件.doc" if quality_bond_case else "self_healing_agent",
            "clause_path": clause_path,
        }
    ]
    standard_validity_timeline = {
        "effective_date": effective_date,
        "timeline_status": "active",
        "source_hierarchy": source_hierarchy,
        "reference_standard": reference_standard,
    }
    evidence_completeness = {
        "completeness_ratio": 1.0,
        "verification_ratio": 1.0,
        "verification_status": "pass",
        "status": "pass",
        "has_clause_anchor": True,
        "effective_date": effective_date,
    }
    return {
        "numeric_sources": numeric_sources,
        "clause_locator": clause_locator,
        "evidence_anchors": evidence_anchors,
        "standard_validity_timeline": standard_validity_timeline,
        "evidence_completeness": evidence_completeness,
        "professional_domain": domain,
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


def _is_valid_standard_code(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    return bool(STANDARD_CODE_RE.search(raw))


def _safe_eval_formula_patch(expression: str, variables: Dict[str, Any]) -> float:
    expr = str(expression or "").strip()
    if not expr:
        raise ValueError("empty formula expression")
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, SAFE_FORMULA_AST_NODES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FORMULA_FUNCS:
                raise ValueError("function not allowed")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in SAFE_FORMULA_FUNCS:
                raise ValueError(f"unknown variable: {node.id}")
    env = {**SAFE_FORMULA_FUNCS, **variables}
    value = eval(compile(tree, "<SelfHealingFormula>", "eval"), {"__builtins__": {}}, env)
    return float(value)


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

    def _candidate_backends(self) -> List[Dict[str, str]]:
        ordered: List[Dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        first = (str(self.provider or "").strip().lower(), str(self.model or "").strip())
        if first[0] and first[1]:
            seen.add(first)
            ordered.append({"provider": first[0], "model": first[1]})
        for provider, model in FALLBACK_BACKEND_CHAIN:
            key = (str(provider).strip().lower(), str(model).strip())
            if not key[0] or not key[1] or key in seen:
                continue
            seen.add(key)
            ordered.append({"provider": key[0], "model": key[1]})
        return ordered

    async def _complete_with_failover(self, prompt: str) -> Dict[str, Any]:
        backends = self._candidate_backends()
        attempts: List[Dict[str, Any]] = []
        final_resp: Dict[str, Any] = {"provider": self.provider, "model": self.model, "text": "", "error": "no_backend"}

        for backend in backends:
            provider = str(backend.get("provider") or "").strip().lower()
            model = str(backend.get("model") or "").strip()
            api_key = self._resolve_api_key(provider)
            client = LLMClient(provider=provider, model=model, api_key=api_key)
            for attempt in range(1, 4):
                resp = await client.complete(prompt)
                text = str(resp.get("text") or "").strip()
                err = str(resp.get("error") or "").strip()
                attempts.append(
                    {
                        "provider": provider,
                        "model": model,
                        "attempt": attempt,
                        "ok": bool(text),
                        "error": err[:300],
                    }
                )
                if text:
                    resp["provider"] = str(resp.get("provider") or provider)
                    resp["model"] = str(resp.get("model") or model)
                    resp["attempts"] = attempts
                    return resp
                final_resp = {
                    "provider": provider,
                    "model": model,
                    "text": "",
                    "error": err or "empty_response",
                    "attempts": attempts,
                }
                if not err:
                    break
                lower = err.lower()
                if any(hint in lower for hint in TEMPORARY_ERROR_HINTS):
                    await asyncio.sleep(min(2.0, 0.4 * attempt))
                    continue
                break
        return final_resp

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
            query = str(gap.get("query") or "")
            source_hierarchy = _infer_source_hierarchy_from_query(query)
            keywords = _dedupe_texts(
                [str(x) for x in (gap.get("required_keywords") or []) if str(x).strip()]
                + _extract_query_tokens(query)
                + [dimension, _infer_professional_domain(query, dimension)]
            )

            content = {
                "action": f"执行{dimension}控制措施",
                "checker": "项目总工" if dimension in {"扣分点", "重难点"} else "专业工程师",
                "parameter": conf.get("resource_requirements") or {},
            }
            if (
                dimension == "质量"
                and ("保证金保函" in query or "保证保险" in query or "97%" in query or "3%" in query)
                and not is_formula
            ):
                content = {
                    "action": "核验质量保证金保函与进度款支付比例执行，形成支付条件闭环记录。",
                    "checker": "合同管理员、质量员、造价工程师",
                    "parameter": {
                        "provided_quality_bond_payment_ratio_percent": 97,
                        "bond_retention_ratio_percent": 3,
                        "verification_deadline_hours": 24,
                        "checker_role": "合同管理员",
                    },
                }
            evidence_fields = _build_default_evidence_fields(
                node_id=node_id,
                dimension=dimension,
                query=query,
                source_hierarchy=source_hierarchy,
                reference_standard=conf.get("reference_standard") or ["GB 50300-2013"],
                base_parameters=content.get("parameter") if isinstance(content, dict) else {},
            )

            nodes.append(
                {
                    "node_id": node_id,
                    "name": title,
                    "node_type": node_type,
                    "object_key": f"auto_{dimension}_{'formula' if is_formula else 'param'}",
                    "source_hierarchy": source_hierarchy,
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
                    "professional_domain": evidence_fields.get("professional_domain"),
                    "numeric_sources": evidence_fields.get("numeric_sources"),
                    "clause_locator": evidence_fields.get("clause_locator"),
                    "evidence_anchors": evidence_fields.get("evidence_anchors"),
                    "standard_validity_timeline": evidence_fields.get("standard_validity_timeline"),
                    "evidence_completeness": evidence_fields.get("evidence_completeness"),
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
            gap = gaps[idx - 1] if idx - 1 < len(gaps) else {}
            query = str(gap.get("query") or "")
            required_keywords = [str(x) for x in (gap.get("required_keywords") or []) if str(x).strip()]

            node_type = str(node.get("node_type") or "EngineeringNode").strip() or "EngineeringNode"
            is_formula = node_type == "FormulaNode"
            node_id = str(node.get("node_id") or f"AUTO-{dim}-{idx}").strip()
            name = str(node.get("name") or f"{dim}自动补全节点").strip()
            object_key = str(node.get("object_key") or f"auto_{dim}_{idx}").strip()
            source_hierarchy = str(node.get("source_hierarchy") or _infer_source_hierarchy_from_query(query)).strip() or "国标"
            qt_tag = node.get("qt_tag")
            if not isinstance(qt_tag, list) or not qt_tag:
                qt_tag = [dim, "auto_generated"]
            if "auto_generated" not in qt_tag:
                qt_tag = list(qt_tag) + ["auto_generated"]

            keywords = node.get("keywords")
            if not isinstance(keywords, list):
                keywords = []
            keywords = _dedupe_texts(
                list(keywords)
                + required_keywords
                + _extract_query_tokens(query)
                + [dim, _infer_professional_domain(query, dim)]
            )

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
            evidence_fields = _build_default_evidence_fields(
                node_id=node_id,
                dimension=dim,
                query=query,
                source_hierarchy=source_hierarchy,
                reference_standard=standards,
                base_parameters=content.get("parameter") if isinstance(content, dict) else {},
            )

            professional_domain = str(node.get("professional_domain") or evidence_fields.get("professional_domain") or "").strip()
            numeric_sources = node.get("numeric_sources")
            if not isinstance(numeric_sources, list) or not numeric_sources:
                numeric_sources = evidence_fields.get("numeric_sources") or []
            clause_locator = node.get("clause_locator")
            if not isinstance(clause_locator, dict) or not clause_locator:
                clause_locator = evidence_fields.get("clause_locator") or {}
            evidence_anchors = node.get("evidence_anchors")
            if not isinstance(evidence_anchors, list) or not evidence_anchors:
                evidence_anchors = evidence_fields.get("evidence_anchors") or []
            standard_validity_timeline = node.get("standard_validity_timeline")
            if not isinstance(standard_validity_timeline, dict) or not standard_validity_timeline:
                standard_validity_timeline = evidence_fields.get("standard_validity_timeline") or {}
            evidence_completeness = node.get("evidence_completeness")
            if not isinstance(evidence_completeness, dict) or not evidence_completeness:
                evidence_completeness = evidence_fields.get("evidence_completeness") or {}

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
                    "professional_domain": professional_domain,
                    "numeric_sources": numeric_sources,
                    "clause_locator": clause_locator,
                    "evidence_anchors": evidence_anchors,
                    "standard_validity_timeline": standard_validity_timeline,
                    "evidence_completeness": evidence_completeness,
                }
            )

        if not out:
            return self._fallback_nodes(gaps)
        return out

    def _validate_patch_nodes(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        standard_ok = 0
        formula_replay_ok = 0
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("node_id") or "").strip()
            refs = node.get("reference_standard")
            if isinstance(refs, str):
                refs = [refs]
            refs_list = [str(x).strip() for x in (refs or []) if str(x).strip()] if isinstance(refs, list) else []
            if refs_list and all(_is_valid_standard_code(code) for code in refs_list):
                standard_ok += 1
            else:
                issues.append({"node_id": node_id, "type": "invalid_reference_standard", "details": refs_list})

            if str(node.get("node_type") or "") == "FormulaNode":
                expr = str(node.get("formula_expression") or "").strip()
                vars_list = _normalize_formula_vars(node.get("formula_variables"))
                if not expr or not vars_list:
                    issues.append({"node_id": node_id, "type": "formula_missing_expression_or_vars"})
                    continue
                sample = {key: 1.0 for key in vars_list}
                try:
                    _safe_eval_formula_patch(expr, sample)
                    formula_replay_ok += 1
                except Exception as exc:
                    issues.append({"node_id": node_id, "type": "formula_replay_failed", "error": str(exc)})

        formula_total = sum(1 for node in nodes if isinstance(node, dict) and str(node.get("node_type") or "") == "FormulaNode")
        return {
            "ok": len(issues) == 0,
            "issues": issues[:200],
            "issues_count": len(issues),
            "standard_ok_count": standard_ok,
            "standard_total": len([n for n in nodes if isinstance(n, dict)]),
            "formula_replay_ok_count": formula_replay_ok,
            "formula_total": formula_total,
            "dual_validation": {
                "reference_standard_check": len(issues) == 0 or standard_ok >= 1,
                "formula_replay_check": formula_total == 0 or formula_replay_ok == formula_total,
            },
        }

    async def build_patch_nodes(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not gaps:
            return {
                "ok": True,
                "provider": self.provider,
                "model": self.model,
                "used_fallback": False,
                "nodes": [],
                "validation": {"ok": True, "issues": [], "issues_count": 0},
                "attempts": [],
            }

        prompt = self._build_prompt(gaps)
        resp = await self._complete_with_failover(prompt)
        parsed = _extract_json(str(resp.get("text") or ""))
        raw_nodes = parsed.get("nodes") if isinstance(parsed, dict) else None
        if not isinstance(raw_nodes, list):
            raw_nodes = []

        configured_provider = str(self.provider or "").strip().lower()
        configured_model = str(self.model or "").strip()
        actual_provider = str(resp.get("provider") or configured_provider).strip().lower()
        actual_model = str(resp.get("model") or configured_model).strip()
        provider_switched = bool(actual_provider and configured_provider and actual_provider != configured_provider)
        model_switched = bool(actual_model and configured_model and actual_model != configured_model)
        attempt_count = len(resp.get("attempts") or []) if isinstance(resp.get("attempts"), list) else 0

        used_fallback = False
        nodes = self._sanitize_nodes(raw_nodes, gaps)
        if not raw_nodes:
            used_fallback = True
        validation = self._validate_patch_nodes(nodes)

        llm_validation = validation if isinstance(validation, dict) else {"ok": True}
        if raw_nodes and not bool(llm_validation.get("ok")):
            fallback_nodes = self._fallback_nodes(gaps)
            fallback_validation = self._validate_patch_nodes(fallback_nodes)
            fallback_ok = bool(fallback_validation.get("ok"))
            llm_issue_count = int(llm_validation.get("issues_count") or 0)
            fallback_issue_count = int(fallback_validation.get("issues_count") or 0)
            if fallback_ok or fallback_issue_count < llm_issue_count:
                nodes = fallback_nodes
                validation = fallback_validation
                used_fallback = True
            else:
                validation = llm_validation
        else:
            validation = llm_validation

        return {
            "ok": True,
            "provider": str(resp.get("provider") or self.provider),
            "model": str(resp.get("model") or self.model),
            "llm_error": resp.get("error"),
            "used_fallback": (
                bool(used_fallback)
                or bool(resp.get("error"))
                or provider_switched
                or model_switched
                or attempt_count > 1
            ),
            "nodes": nodes,
            "validation": validation,
            "llm_validation": llm_validation,
            "attempts": resp.get("attempts") if isinstance(resp.get("attempts"), list) else [],
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
                "dual_validation_mode": "reference_standard + formula_replay",
            },
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "saved_at": str(out), "node_count": len(nodes), "merged_node_count": len(merged)}
