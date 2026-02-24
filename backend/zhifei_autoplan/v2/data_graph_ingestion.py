from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .dxf_parser import parse_dxf_payload

SUPPORTED_EXTENSIONS = {".json", ".md", ".markdown", ".xml", ".csv", ".dxf"}
DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_DB_PATH = Path("backend/data/autoplan/v2/knowledge_graph.sqlite3")

EDGE_REQUIRES = "REQUIRES"
EDGE_MITIGATES = "MITIGATES"
EDGE_CONFLICTS_WITH = "CONFLICTS_WITH"
EDGE_BELONGS_TO = "BELONGS_TO"
EDGE_TYPES = (EDGE_REQUIRES, EDGE_MITIGATES, EDGE_CONFLICTS_WITH, EDGE_BELONGS_TO)

SOURCE_HIERARCHY_RULE = "答疑文件 > 设计图纸 > 国标 > 行标 > 企标"
SOURCE_HIERARCHY_WEIGHTS: Dict[str, int] = {
    "答疑文件": 5,
    "设计图纸": 4,
    "国标": 3,
    "行标": 2,
    "企标": 1,
    "未知": 0,
}

RELATION_KEYS: Dict[str, Tuple[str, ...]] = {
    EDGE_REQUIRES: (
        "requires",
        "requires_nodes",
        "predecessors",
        "depends_on",
        "前置",
        "前置工序",
        "前置约束",
    ),
    EDGE_MITIGATES: (
        "mitigates",
        "mitigates_nodes",
        "controls_risk_of",
        "risk_controls",
        "缓解",
        "控制风险",
    ),
    EDGE_CONFLICTS_WITH: (
        "conflicts_with",
        "mutually_exclusive_with",
        "exclusions",
        "互斥",
        "冲突工艺",
    ),
    EDGE_BELONGS_TO: (
        "belongs_to",
        "layer",
        "from_layer",
        "所属图层",
    ),
}

ALLOWED_FORMULA_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}

ALLOWED_AST_NODES = (
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


@dataclass
class ParsedEdgeDraft:
    from_ref: str
    to_ref: str
    edge_type: str
    edge_label: str = ""


@dataclass
class ParsedNode:
    uid: str
    title: str
    body: str
    tags: List[str]
    keywords: List[str]
    payload_json: str
    node_type: str = "EngineeringNode"
    object_key: str = ""
    applicable_conditions_json: str = "{}"
    resource_requirements_json: str = "{}"
    safety_level: str = "unknown"
    source_hierarchy: str = "企标"
    formula_expression: str = ""
    formula_variables_json: str = "[]"
    data_source_type: str = "FILE"
    spatial_context_json: str = "{}"
    reference_keys: List[str] = field(default_factory=list)
    edge_drafts: List[ParsedEdgeDraft] = field(default_factory=list)


def _sha256_bytes(content: bytes) -> str:
    h = hashlib.sha256()
    h.update(content)
    return h.hexdigest()


def _normalize_term(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _normalize_key(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "").strip().lower())


def _normalize_alias(value: str) -> str:
    return _normalize_key(value)


def _tokenize(text: str) -> List[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-/]{1,}|\d+(?:\.\d+)?", text or "")
    out: List[str] = []
    seen = set()
    for part in parts:
        term = _normalize_term(part)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _ensure_ascii_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return json.dumps({"error": "payload_not_serializable"}, ensure_ascii=False)


def _safe_json_load(s: Any, fallback: Any) -> Any:
    if not isinstance(s, str) or not s.strip():
        return fallback
    try:
        return json.loads(s)
    except Exception:
        return fallback


def _flatten_scalars(obj: Any, *, max_items: int = 180) -> List[str]:
    lines: List[str] = []

    def walk(node: Any, path: str) -> None:
        if len(lines) >= max_items:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if len(lines) >= max_items:
                    return
                next_path = f"{path}.{key}" if path else str(key)
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if len(lines) >= max_items:
                    return
                next_path = f"{path}[{idx}]" if path else f"[{idx}]"
                if isinstance(value, (dict, list)):
                    walk(value, next_path)
                else:
                    text = str(value).strip()
                    if text:
                        lines.append(f"{next_path}: {text}")
        else:
            text = str(node).strip()
            if text:
                lines.append(f"{path}: {text}" if path else text)

    walk(obj, "")
    return lines


def _extract_terms(raw: Any) -> List[str]:
    out: List[str] = []
    if isinstance(raw, str):
        out.extend(_tokenize(raw))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.extend(_tokenize(item))
            elif item is not None:
                out.extend(_tokenize(str(item)))
    elif isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, (str, list, dict)):
                out.extend(_extract_terms(value))
    elif raw is not None:
        out.extend(_tokenize(str(raw)))

    uniq: List[str] = []
    seen = set()
    for term in out:
        if term in seen:
            continue
        seen.add(term)
        uniq.append(term)
    return uniq[:60]


def _dedupe_terms(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        term = _normalize_term(value)
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _safe_title(source_name: str, payload: Dict[str, Any], fallback: str) -> str:
    candidates = [
        payload.get("title"),
        payload.get("name"),
        payload.get("node_id"),
        payload.get("id"),
        payload.get("domain"),
        payload.get("category"),
        fallback,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return text[:120]
    return source_name


def _dict_get_case_insensitive(data: Dict[str, Any], candidates: Sequence[str]) -> Any:
    if not isinstance(data, dict):
        return None
    normalized = {_normalize_key(k): v for k, v in data.items()}
    for key in candidates:
        nk = _normalize_key(key)
        if nk in normalized:
            return normalized[nk]
    return None


def _split_targets(text: str) -> List[str]:
    parts = re.split(r"[;,，；、/|]+", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def _coerce_targets(raw: Any) -> List[str]:
    out: List[str] = []
    if raw is None:
        return out
    if isinstance(raw, str):
        out.extend(_split_targets(raw))
    elif isinstance(raw, list):
        for item in raw:
            out.extend(_coerce_targets(item))
    elif isinstance(raw, dict):
        target = _dict_get_case_insensitive(raw, ("target", "to", "node", "node_id", "id", "name", "object"))
        if target is not None:
            out.extend(_coerce_targets(target))
        else:
            for value in raw.values():
                out.extend(_coerce_targets(value))
    else:
        out.extend(_split_targets(str(raw)))
    uniq: List[str] = []
    seen = set()
    for item in out:
        norm = _normalize_alias(item)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        uniq.append(item)
    return uniq


def _extract_relation_targets(node: Dict[str, Any], edge_type: str) -> List[str]:
    keys = RELATION_KEYS.get(edge_type) or ()
    targets: List[str] = []
    for key in keys:
        val = _dict_get_case_insensitive(node, (key,))
        if val is not None:
            targets.extend(_coerce_targets(val))

    relations = _dict_get_case_insensitive(node, ("relations", "relationship", "edges"))
    if isinstance(relations, dict):
        for key in keys:
            val = _dict_get_case_insensitive(relations, (key,))
            if val is not None:
                targets.extend(_coerce_targets(val))
    elif isinstance(relations, list):
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            rtype = str(_dict_get_case_insensitive(rel, ("type", "edge_type", "relation")) or "").upper().strip()
            if rtype != edge_type:
                continue
            val = _dict_get_case_insensitive(rel, ("target", "to", "node", "node_id", "name", "object"))
            targets.extend(_coerce_targets(val))

    uniq: List[str] = []
    seen = set()
    for target in targets:
        norm = _normalize_alias(target)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        uniq.append(target)
    return uniq


def _infer_source_hierarchy_from_path(path_text: str) -> str:
    text = str(path_text or "")
    if any(k in text for k in ("答疑", "澄清", "补遗", "变更")):
        return "答疑文件"
    if any(k in text for k in ("图纸", "设计图", "施工图", "design")):
        return "设计图纸"
    if any(k in text for k in ("国标", "国家标准", "gb")):
        return "国标"
    if any(k in text for k in ("行标", "行业标准", "jgj", "tb")):
        return "行标"
    if any(k in text for k in ("企标", "企业标准", "q/", "q_")):
        return "企标"
    return "企标"


def _normalize_source_hierarchy(value: Any, *, source_path: str = "", inherited: str | None = None) -> str:
    if value is None or str(value).strip() == "":
        if inherited:
            return inherited
        return _infer_source_hierarchy_from_path(source_path)

    raw = str(value).strip().lower()
    if any(k in raw for k in ("答疑", "澄清", "补遗", "clarification", "qa")):
        return "答疑文件"
    if any(k in raw for k in ("设计图", "图纸", "drawing", "design")):
        return "设计图纸"
    if any(k in raw for k in ("国标", "国家", "gb")):
        return "国标"
    if any(k in raw for k in ("行标", "行业", "jgj", "tb")):
        return "行标"
    if any(k in raw for k in ("企标", "企业", "company", "enterprise")):
        return "企标"
    return "未知"


def _normalize_safety_level(value: Any, text: str = "") -> str:
    raw = str(value or "").strip().lower()
    merged = f"{raw} {text}".lower()
    if any(k in merged for k in ("critical", "极高", "特级")):
        return "critical"
    if any(k in merged for k in ("high", "高风险", "重大危险", "危大")):
        return "high"
    if any(k in merged for k in ("medium", "中风险", "较大风险")):
        return "medium"
    if any(k in merged for k in ("low", "低风险", "一般风险")):
        return "low"
    return "unknown"


def _extract_applicable_conditions(node: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(node, dict):
        return {}

    value = _dict_get_case_insensitive(
        node,
        (
            "applicable_conditions",
            "applicable_condition",
            "conditions",
            "condition",
            "适用条件",
            "环境条件",
        ),
    )
    if isinstance(value, dict):
        out = dict(value)
    elif value is not None:
        out = {"raw": value}
    else:
        out = {}

    climate = _dict_get_case_insensitive(node, ("climate", "气候", "temperature", "温度"))
    geology = _dict_get_case_insensitive(node, ("geology", "地质", "soil", "地层"))
    if climate is not None:
        out.setdefault("climate", climate)
    if geology is not None:
        out.setdefault("geology", geology)
    return out


def _extract_resource_requirements(node: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(node, dict):
        return {}
    value = _dict_get_case_insensitive(
        node,
        (
            "resource_requirements",
            "resource_requirement",
            "resources",
            "resource_model",
            "资源要求",
            "资源消耗模型",
        ),
    )
    if isinstance(value, dict):
        out = dict(value)
    elif isinstance(value, list):
        out = {"items": value}
    elif value is not None:
        out = {"raw": value}
    else:
        out = {}

    for key, alias in (("manpower", "人力"), ("material", "材料"), ("equipment", "机械")):
        v = _dict_get_case_insensitive(node, (key, alias))
        if v is not None:
            out.setdefault(key, v)
    return out


def _extract_formula_info(node: Dict[str, Any], body: str) -> Tuple[str, str, List[str]]:
    raw_type = str(_dict_get_case_insensitive(node, ("node_type", "type")) or "EngineeringNode").strip()
    expr = _dict_get_case_insensitive(node, ("formula_expression", "formula", "expression", "compute_formula"))
    if expr is None:
        content = _dict_get_case_insensitive(node, ("content",))
        if isinstance(content, dict):
            expr = _dict_get_case_insensitive(content, ("formula_expression", "formula", "expression", "compute_formula"))

    expression = str(expr or "").strip()
    node_type = "FormulaNode" if (raw_type.lower() == "formulanode" or bool(expression)) else "EngineeringNode"

    vars_raw = _dict_get_case_insensitive(node, ("formula_variables", "variables", "formula_vars"))
    variables: List[str] = []
    if isinstance(vars_raw, str):
        variables = [v.strip() for v in re.split(r"[;,，；、\s]+", vars_raw) if v.strip()]
    elif isinstance(vars_raw, list):
        variables = [str(v).strip() for v in vars_raw if str(v).strip()]

    if expression and not variables:
        guessed = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
        variables = [v for v in guessed if v not in ALLOWED_FORMULA_FUNCS]
    uniq_vars: List[str] = []
    seen = set()
    for item in variables:
        name = str(item).strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        uniq_vars.append(name)
    return node_type, expression, uniq_vars


def _build_object_key(node: Dict[str, Any], title: str, node_id: str) -> str:
    candidate = _dict_get_case_insensitive(node, ("object_key", "target_object", "object", "name", "title"))
    if candidate is None:
        candidate = title or node_id
    key = _normalize_alias(str(candidate))
    return key or _normalize_alias(str(title or node_id)) or _normalize_alias(node_id)


def _build_reference_keys(node: Dict[str, Any], *, uid: str, title: str, node_id: str, object_key: str) -> List[str]:
    refs: List[str] = [uid, title, node_id, object_key]
    refs.extend(_coerce_targets(_dict_get_case_insensitive(node, ("aliases", "alias", "ref", "references"))))
    if isinstance(node.get("name"), str):
        refs.append(str(node.get("name")))
    if isinstance(node.get("id"), str):
        refs.append(str(node.get("id")))

    out: List[str] = []
    seen = set()
    for ref in refs:
        norm = _normalize_alias(ref)
        if len(norm) < 2:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        out.append(ref)
    return out


def _build_parsed_node(
    *,
    path: Path,
    node_id: str,
    title: str,
    body: str,
    tags: List[str],
    keywords: List[str],
    payload: Dict[str, Any],
    node_type: str,
    object_key: str,
    applicable_conditions: Dict[str, Any],
    resource_requirements: Dict[str, Any],
    safety_level: str,
    source_hierarchy: str,
    formula_expression: str,
    formula_variables: List[str],
    reference_keys: List[str],
    edge_drafts: List[ParsedEdgeDraft],
    data_source_type: str = "FILE",
    spatial_context: Optional[Dict[str, Any]] = None,
) -> ParsedNode:
    uid = hashlib.sha1(f"{path}::{node_id}".encode("utf-8")).hexdigest()[:20]
    return ParsedNode(
        uid=uid,
        title=title,
        body=body[:12000],
        tags=_dedupe_terms(tags)[:24],
        keywords=_dedupe_terms(keywords)[:32],
        payload_json=_ensure_ascii_json(payload),
        node_type=node_type,
        object_key=object_key,
        applicable_conditions_json=_ensure_ascii_json(applicable_conditions),
        resource_requirements_json=_ensure_ascii_json(resource_requirements),
        safety_level=safety_level,
        source_hierarchy=source_hierarchy,
        formula_expression=formula_expression,
        formula_variables_json=_ensure_ascii_json(formula_variables),
        data_source_type=str(data_source_type or "FILE"),
        spatial_context_json=_ensure_ascii_json(spatial_context or {}),
        reference_keys=reference_keys,
        edge_drafts=edge_drafts,
    )


def _parse_markdown(path: Path) -> List[ParsedNode]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    nodes: List[ParsedNode] = []

    current_title = path.stem
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        body = "\n".join(current_lines).strip()
        if len(body) < 20:
            return
        title = current_title or path.stem
        node_id = f"{path.stem}:{title}"
        source_hierarchy = _normalize_source_hierarchy(None, source_path=str(path))
        safety_level = _normalize_safety_level(None, body)
        object_key = _normalize_alias(title)
        refs = [title, node_id, object_key]
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=_extract_terms([path.stem, "markdown"]),
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "markdown", "title": title},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level=safety_level,
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            reference_keys=refs,
            edge_drafts=[],
        )
        nodes.append(node)

    for line in lines:
        if line.lstrip().startswith("#"):
            flush()
            current_title = re.sub(r"^#+\s*", "", line).strip() or path.stem
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if not nodes and text.strip():
        current_title = path.stem
        current_lines = [text]
        flush()

    return nodes


def _parse_csv(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean = {k: v for k, v in row.items() if v not in (None, "")}
            if not clean:
                continue
            title = _safe_title(path.stem, clean, f"row_{idx}")
            node_id = str(clean.get("node_id") or clean.get("id") or f"{path.stem}:{idx}")
            body = "\n".join(f"{k}: {v}" for k, v in clean.items())
            source_hierarchy = _normalize_source_hierarchy(clean.get("source_hierarchy"), source_path=str(path))
            safety_level = _normalize_safety_level(clean.get("safety_level") or clean.get("risk_level"), body)
            object_key = _normalize_alias(str(clean.get("object_key") or title))
            refs = [title, node_id, object_key]

            node = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms([path.stem, "csv"]),
                keywords=_extract_terms(clean),
                payload={"type": "csv", "row": idx, "raw": clean},
                node_type="EngineeringNode",
                object_key=object_key,
                applicable_conditions={},
                resource_requirements={},
                safety_level=safety_level,
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=refs,
                edge_drafts=[],
            )
            nodes.append(node)

    return nodes


def _parse_xml(path: Path) -> List[ParsedNode]:
    nodes: List[ParsedNode] = []
    root = ET.parse(path).getroot()

    def walk(elem: ET.Element, x_path: str) -> None:
        text_parts: List[str] = []
        attrs: Dict[str, Any] = {}
        if elem.attrib:
            attrs.update(elem.attrib)
            for key, value in elem.attrib.items():
                if value is not None:
                    text_parts.append(f"@{key}: {value}")
        if elem.text and elem.text.strip():
            text_parts.append(elem.text.strip())
        for child in elem:
            if child.text and child.text.strip():
                text_parts.append(f"{child.tag}: {child.text.strip()}")

        body = "\n".join(text_parts).strip()
        if len(body) >= 20:
            title = str(elem.attrib.get("name") or elem.attrib.get("id") or elem.tag)
            node_id = str(elem.attrib.get("node_id") or elem.attrib.get("id") or x_path)
            source_hierarchy = _normalize_source_hierarchy(elem.attrib.get("source_hierarchy"), source_path=str(path))
            safety_level = _normalize_safety_level(elem.attrib.get("safety_level") or elem.attrib.get("risk_level"), body)
            object_key = _normalize_alias(str(elem.attrib.get("object_key") or title))
            refs = [title, node_id, object_key]

            node = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms([path.stem, elem.tag]),
                keywords=_tokenize(f"{title} {body}"),
                payload={"type": "xml", "path": x_path, "tag": elem.tag, "attrs": attrs},
                node_type="EngineeringNode",
                object_key=object_key,
                applicable_conditions={},
                resource_requirements={},
                safety_level=safety_level,
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=refs,
                edge_drafts=[],
            )
            nodes.append(node)

        for idx, child in enumerate(elem):
            walk(child, f"{x_path}/{child.tag}[{idx}]")

    walk(root, f"/{root.tag}")
    return nodes


def _parse_json(path: Path) -> List[ParsedNode]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    nodes: List[ParsedNode] = []

    def walk(
        node: Any,
        pointer: str,
        inherited_tags: List[str],
        inherited_keywords: List[str],
        inherited_source: str,
    ) -> None:
        if isinstance(node, dict):
            local_tags = list(inherited_tags)
            local_keywords = list(inherited_keywords)

            for tag_key in ("domain", "category", "type", "scene", "qt_tag", "tags", "labels"):
                val = _dict_get_case_insensitive(node, (tag_key,))
                if val is not None:
                    local_tags.extend(_extract_terms(val))
            for kw_key in ("keywords", "keyword", "trigger_keywords", "name", "title"):
                val = _dict_get_case_insensitive(node, (kw_key,))
                if val is not None:
                    local_keywords.extend(_extract_terms(val))

            source_hierarchy = _normalize_source_hierarchy(
                _dict_get_case_insensitive(node, ("source_hierarchy", "source_level", "source")),
                source_path=str(path),
                inherited=inherited_source,
            )

            has_identity = any(
                _dict_get_case_insensitive(node, (k,)) is not None
                for k in ("node_id", "name", "title", "id")
            )
            if has_identity:
                title = _safe_title(path.stem, node, pointer)
                node_id = str(_dict_get_case_insensitive(node, ("node_id", "id")) or pointer)
                body_lines = _flatten_scalars(node, max_items=160)
                body = "\n".join(body_lines).strip()
                if len(body) >= 20:
                    node_type, formula_expression, formula_variables = _extract_formula_info(node, body)
                    applicable_conditions = _extract_applicable_conditions(node)
                    resource_requirements = _extract_resource_requirements(node)
                    safety_level = _normalize_safety_level(
                        _dict_get_case_insensitive(node, ("safety_level", "risk_level", "风险等级")),
                        body,
                    )
                    object_key = _build_object_key(node, title, node_id)
                    refs = _build_reference_keys(
                        node,
                        uid="",
                        title=title,
                        node_id=node_id,
                        object_key=object_key,
                    )

                    primary_ref = str(_dict_get_case_insensitive(node, ("node_id", "id", "name", "title")) or title)
                    edge_drafts: List[ParsedEdgeDraft] = []
                    for edge_type in EDGE_TYPES:
                        targets = _extract_relation_targets(node, edge_type)
                        for target in targets:
                            edge_drafts.append(
                                ParsedEdgeDraft(
                                    from_ref=primary_ref,
                                    to_ref=target,
                                    edge_type=edge_type,
                                    edge_label="",
                                )
                            )

                    payload = {
                        "pointer": pointer,
                        "node_id": node_id,
                        "title": title,
                        "node_type": node_type,
                        "source_hierarchy": source_hierarchy,
                    }

                    parsed = _build_parsed_node(
                        path=path,
                        node_id=node_id,
                        title=title,
                        body=body,
                        tags=local_tags + _extract_terms(path.stem),
                        keywords=local_keywords + _tokenize(f"{title} {body}"),
                        payload=payload,
                        node_type=node_type,
                        object_key=object_key,
                        applicable_conditions=applicable_conditions,
                        resource_requirements=resource_requirements,
                        safety_level=safety_level,
                        source_hierarchy=source_hierarchy,
                        formula_expression=formula_expression,
                        formula_variables=formula_variables,
                        reference_keys=refs,
                        edge_drafts=edge_drafts,
                    )
                    # inject uid reference after creation
                    parsed.reference_keys = _build_reference_keys(
                        node,
                        uid=parsed.uid,
                        title=title,
                        node_id=node_id,
                        object_key=object_key,
                    )
                    nodes.append(parsed)

            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}.{key}", local_tags, local_keywords, source_hierarchy)

        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if isinstance(value, (dict, list)):
                    walk(value, f"{pointer}[{idx}]", inherited_tags, inherited_keywords, inherited_source)

    walk(raw, "$", _extract_terms(path.stem), [], _infer_source_hierarchy_from_path(str(path)))

    if not nodes:
        body = "\n".join(_flatten_scalars(raw, max_items=200)).strip()
        if body:
            title = path.stem
            node_id = f"{path.stem}:root"
            source_hierarchy = _infer_source_hierarchy_from_path(str(path))
            parsed = _build_parsed_node(
                path=path,
                node_id=node_id,
                title=title,
                body=body,
                tags=_extract_terms(path.stem),
                keywords=_tokenize(body),
                payload={"pointer": "$", "node_id": node_id, "title": title},
                node_type="EngineeringNode",
                object_key=_normalize_alias(title),
                applicable_conditions={},
                resource_requirements={},
                safety_level=_normalize_safety_level(None, body),
                source_hierarchy=source_hierarchy,
                formula_expression="",
                formula_variables=[],
                reference_keys=[title, node_id],
                edge_drafts=[],
            )
            nodes.append(parsed)

    return nodes


def _parse_dxf(path: Path) -> List[ParsedNode]:
    payload = parse_dxf_payload(path)
    source_hierarchy = _normalize_source_hierarchy("设计图纸", source_path=str(path))
    nodes: List[ParsedNode] = []

    layer_ref_map: Dict[str, str] = {}
    layer_domain_map: Dict[str, str] = {}

    for layer in payload.get("layers") or []:
        layer_name = str(layer.get("layer_name") or "").strip() or "0"
        professional_domain = str(layer.get("professional_domain") or "general").strip() or "general"
        entity_count = int(layer.get("entity_count") or 0)
        node_id = f"{path.stem}:layer:{layer_name}"
        title = f"系统图层 {layer_name}"
        body = "\n".join(
            [
                f"图层名称: {layer_name}",
                f"专业属性: {professional_domain}",
                f"实体数量: {entity_count}",
            ]
        )
        object_key = _normalize_alias(layer_name) or _normalize_alias(node_id)
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "layer", professional_domain, layer_name],
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "dxf_layer", "raw": layer},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "layer": layer_name, "context_type": "layer"},
            reference_keys=[node_id, title, layer_name, object_key],
            edge_drafts=[],
        )
        nodes.append(node)
        layer_ref_map[layer_name] = node_id
        layer_domain_map[layer_name] = professional_domain

    text_title_map = {
        "design_general_notes": "设计总说明",
        "technical_requirement": "技术要求",
        "title_block_info": "图框信息",
        "leader_annotation": "引线标注文本",
        "drawing_text": "图纸文本",
    }

    for idx, item in enumerate(payload.get("texts") or [], start=1):
        text = str(item.get("text") or "").strip()
        if len(text) < 2:
            continue
        layer_name = str(item.get("layer") or "0")
        category = str(item.get("category") or "drawing_text")
        professional_domain = str(item.get("professional_domain") or layer_domain_map.get(layer_name) or "general")
        node_id = f"{path.stem}:text:{idx}"
        title = text_title_map.get(category, "图纸文本")
        object_key = _normalize_alias(f"{layer_name}-{category}-{idx}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="text_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=text,
            tags=["dxf", "text", category, layer_name, professional_domain],
            keywords=_tokenize(f"{title} {text} {layer_name}"),
            payload={"type": "dxf_text", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level=_normalize_safety_level(None, text),
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "entity_type": item.get("entity_type"),
                "position": item.get("position") or {},
                "handle": item.get("handle") or "",
                "context_type": category,
            },
            reference_keys=[node_id, title, layer_name, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    title_block = payload.get("title_block") or {}
    project_name = str(title_block.get("project_name") or "").strip()
    drawing_scale = str(title_block.get("drawing_scale") or "").strip()
    if project_name or drawing_scale:
        body_lines = ["图框信息提取"]
        if project_name:
            body_lines.append(f"项目名称: {project_name}")
        if drawing_scale:
            body_lines.append(f"出图比例: {drawing_scale}")
        node_id = f"{path.stem}:title_block"
        title = "图框信息"
        object_key = _normalize_alias(f"{path.stem}-title-block")
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body="\n".join(body_lines),
            tags=["dxf", "title_block"],
            keywords=_tokenize(" ".join(body_lines)),
            payload={"type": "dxf_title_block", "raw": title_block},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "context_type": "title_block"},
            reference_keys=[node_id, title, object_key],
            edge_drafts=[],
        )
        nodes.append(node)

    for idx, item in enumerate(payload.get("blocks") or [], start=1):
        block_name = str(item.get("block_name") or "").strip()
        if not block_name:
            continue
        layer_name = str(item.get("layer") or "0")
        professional_domain = str(item.get("professional_domain") or layer_domain_map.get(layer_name) or "general")
        count = int(item.get("count") or 0)
        node_id = f"{path.stem}:block:{idx}:{block_name}"
        title = f"块符号 {block_name}"
        body = "\n".join(
            [
                f"块名称: {block_name}",
                f"所在图层: {layer_name}",
                f"数量: {count}",
                f"缩放: ({item.get('scale_x', 1.0)}, {item.get('scale_y', 1.0)}, {item.get('scale_z', 1.0)})",
                f"旋转: {item.get('rotation', 0.0)}",
            ]
        )
        object_key = _normalize_alias(f"{block_name}-{layer_name}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="block_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "block", professional_domain, layer_name],
            keywords=_tokenize(f"{title} {body}"),
            payload={"type": "dxf_block", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={"symbol_count": count},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "context_type": "block",
                "sample_inserts": item.get("sample_inserts") or [],
            },
            reference_keys=[node_id, title, block_name, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    for idx, item in enumerate(payload.get("dimensions") or [], start=1):
        layer_name = str(item.get("layer") or "0")
        measurement = item.get("measurement")
        text = str(item.get("text") or "").strip()
        detail = text or (f"{measurement}" if measurement is not None else "")
        if not detail:
            continue
        node_id = f"{path.stem}:dimension:{idx}"
        title = "尺寸标注"
        body_lines = [f"所在图层: {layer_name}"]
        if measurement is not None:
            body_lines.append(f"量测值: {measurement}")
        if text:
            body_lines.append(f"标注文本: {text}")
        object_key = _normalize_alias(f"{layer_name}-dimension-{idx}")
        edge_drafts: List[ParsedEdgeDraft] = []
        layer_ref = layer_ref_map.get(layer_name)
        if layer_ref:
            edge_drafts.append(
                ParsedEdgeDraft(
                    from_ref=node_id,
                    to_ref=layer_ref,
                    edge_type=EDGE_BELONGS_TO,
                    edge_label="dimension_layer_binding",
                )
            )

        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body="\n".join(body_lines),
            tags=["dxf", "dimension", layer_name],
            keywords=_tokenize(f"{title} {' '.join(body_lines)}"),
            payload={"type": "dxf_dimension", "raw": item},
            node_type="EngineeringNode",
            object_key=object_key,
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={
                "drawing": path.name,
                "layer": layer_name,
                "context_type": "dimension",
                "defpoint": item.get("defpoint") or {},
                "defpoint2": item.get("defpoint2") or {},
                "defpoint3": item.get("defpoint3") or {},
            },
            reference_keys=[node_id, title, object_key],
            edge_drafts=edge_drafts,
        )
        nodes.append(node)

    geometry_features = payload.get("geometry_features") or []
    if geometry_features:
        counter: Dict[str, int] = {}
        for feature in geometry_features:
            ftype = str(feature.get("entity_type") or "UNKNOWN")
            counter[ftype] = int(counter.get(ftype, 0)) + 1
        summary = ", ".join(f"{key}:{value}" for key, value in sorted(counter.items()))
        node_id = f"{path.stem}:geometry_summary"
        title = "几何特征摘要"
        body = f"几何实体统计: {summary}"
        node = _build_parsed_node(
            path=path,
            node_id=node_id,
            title=title,
            body=body,
            tags=["dxf", "geometry"],
            keywords=_tokenize(f"{title} {summary}"),
            payload={"type": "dxf_geometry_summary", "raw": geometry_features[:80]},
            node_type="EngineeringNode",
            object_key=_normalize_alias(f"{path.stem}-geometry-summary"),
            applicable_conditions={},
            resource_requirements={},
            safety_level="unknown",
            source_hierarchy=source_hierarchy,
            formula_expression="",
            formula_variables=[],
            data_source_type="DXF",
            spatial_context={"drawing": path.name, "context_type": "geometry_summary"},
            reference_keys=[node_id, title],
            edge_drafts=[],
        )
        nodes.append(node)

    return nodes


def _safe_eval_formula(expression: str, variables: Dict[str, Any]) -> Any:
    text = str(expression or "").strip()
    if not text:
        raise ValueError("empty formula expression")
    tree = ast.parse(text, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only direct function calls are allowed")
            if node.func.id not in ALLOWED_FORMULA_FUNCS:
                raise ValueError(f"function not allowed: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in ALLOWED_FORMULA_FUNCS:
                raise ValueError(f"unknown variable: {node.id}")
    env = {**ALLOWED_FORMULA_FUNCS, **variables}
    return eval(compile(tree, "<FormulaNode>", "eval"), {"__builtins__": {}}, env)


class KnowledgeGraphIndex:
    """SQLite-backed unified knowledge graph index with structure/relations/formula/arbitration support."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_needs_reindex = False
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column_def: str) -> None:
        col_name = column_def.split()[0].strip()
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(c[1]) for c in cols}
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    imported_at INTEGER NOT NULL,
                    node_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    node_uid TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    node_type TEXT NOT NULL DEFAULT 'EngineeringNode',
                    object_key TEXT NOT NULL DEFAULT '',
                    applicable_conditions_json TEXT NOT NULL DEFAULT '{}',
                    resource_requirements_json TEXT NOT NULL DEFAULT '{}',
                    safety_level TEXT NOT NULL DEFAULT 'unknown',
                    source_hierarchy TEXT NOT NULL DEFAULT '企标',
                    formula_expression TEXT NOT NULL DEFAULT '',
                    formula_variables_json TEXT NOT NULL DEFAULT '[]',
                    data_source_type TEXT NOT NULL DEFAULT 'FILE',
                    spatial_context_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, node_uid)
                );

                CREATE TABLE IF NOT EXISTS node_tags (
                    node_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(node_id, tag),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS node_keywords (
                    node_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    UNIQUE(node_id, keyword),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS node_aliases (
                    node_id INTEGER NOT NULL,
                    alias TEXT NOT NULL,
                    UNIQUE(node_id, alias),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node_id INTEGER NOT NULL,
                    to_node_id INTEGER NOT NULL,
                    edge_type TEXT NOT NULL,
                    edge_label TEXT NOT NULL DEFAULT '',
                    source_path TEXT NOT NULL DEFAULT '',
                    UNIQUE(from_node_id, to_node_id, edge_type),
                    FOREIGN KEY(from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY(to_node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_document_id ON nodes(document_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_object_key ON nodes(object_key);
                CREATE INDEX IF NOT EXISTS idx_nodes_source_hierarchy ON nodes(source_hierarchy);
                CREATE INDEX IF NOT EXISTS idx_nodes_data_source_type ON nodes(data_source_type);
                CREATE INDEX IF NOT EXISTS idx_node_tags_tag ON node_tags(tag);
                CREATE INDEX IF NOT EXISTS idx_node_keywords_keyword ON node_keywords(keyword);
                CREATE INDEX IF NOT EXISTS idx_node_aliases_alias ON node_aliases(alias);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type);
                """
            )

            # Migration for older databases.
            self._ensure_column(conn, "nodes", "node_type TEXT NOT NULL DEFAULT 'EngineeringNode'")
            self._ensure_column(conn, "nodes", "object_key TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "applicable_conditions_json TEXT NOT NULL DEFAULT '{}' ")
            self._ensure_column(conn, "nodes", "resource_requirements_json TEXT NOT NULL DEFAULT '{}' ")
            self._ensure_column(conn, "nodes", "safety_level TEXT NOT NULL DEFAULT 'unknown'")
            self._ensure_column(conn, "nodes", "source_hierarchy TEXT NOT NULL DEFAULT '企标'")
            self._ensure_column(conn, "nodes", "formula_expression TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "nodes", "formula_variables_json TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "nodes", "data_source_type TEXT NOT NULL DEFAULT 'FILE'")
            self._ensure_column(conn, "nodes", "spatial_context_json TEXT NOT NULL DEFAULT '{}'")

            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        node_uid,
                        title,
                        body,
                        tags,
                        keywords
                    );
                    """
                )
            except sqlite3.OperationalError as exc:
                raise RuntimeError(
                    "sqlite build does not support FTS5; cannot provide millisecond indexed retrieval"
                ) from exc

            # Schema version tracking for reindex safety.
            vrow = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
            version = str(vrow[0]) if vrow else "0"
            if version != "3":
                self._schema_needs_reindex = True
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', '3')"
                )
            conn.commit()

    def _clear_document_rows(self, conn: sqlite3.Connection, document_id: int) -> None:
        rows = conn.execute("SELECT id FROM nodes WHERE document_id = ?", (document_id,)).fetchall()
        node_ids = [int(r[0]) for r in rows]
        if node_ids:
            marks = ",".join("?" for _ in node_ids)
            conn.execute(f"DELETE FROM graph_edges WHERE from_node_id IN ({marks}) OR to_node_id IN ({marks})", node_ids + node_ids)
            conn.execute(f"DELETE FROM node_aliases WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM node_tags WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM node_keywords WHERE node_id IN ({marks})", node_ids)
            conn.execute(f"DELETE FROM nodes_fts WHERE rowid IN ({marks})", node_ids)
        conn.execute("DELETE FROM nodes WHERE document_id = ?", (document_id,))

    def _parse_file(self, path: Path) -> List[ParsedNode]:
        ext = path.suffix.lower()
        if ext == ".json":
            return _parse_json(path)
        if ext in {".md", ".markdown"}:
            return _parse_markdown(path)
        if ext == ".xml":
            return _parse_xml(path)
        if ext == ".csv":
            return _parse_csv(path)
        if ext == ".dxf":
            return _parse_dxf(path)
        return []

    def _resolve_node_id(self, conn: sqlite3.Connection, ref: str, local_alias_map: Dict[str, int]) -> Optional[int]:
        alias = _normalize_alias(ref)
        if len(alias) < 2:
            return None
        if alias in local_alias_map:
            return int(local_alias_map[alias])

        row = conn.execute(
            "SELECT node_id FROM node_aliases WHERE alias = ? ORDER BY node_id DESC LIMIT 1",
            (alias,),
        ).fetchone()
        if row:
            return int(row[0])

        row = conn.execute(
            "SELECT id FROM nodes WHERE object_key = ? ORDER BY id DESC LIMIT 1",
            (alias,),
        ).fetchone()
        if row:
            return int(row[0])
        return None

    def ingest_directory(
        self,
        root_dir: Path | str = DEFAULT_KG_ROOT,
        *,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        root = Path(root_dir)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"knowledge graph root not found: {root}")

        if self._schema_needs_reindex and not force_reindex:
            force_reindex = True

        start = time.perf_counter()
        parsed_files = 0
        skipped_files = 0
        total_nodes = 0
        total_edges = 0

        files = [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        with self._connect() as conn:
            for path in files:
                data = path.read_bytes()
                sha = _sha256_bytes(data)
                rec = conn.execute(
                    "SELECT id, sha256 FROM documents WHERE source_path = ?",
                    (str(path),),
                ).fetchone()
                if rec and (str(rec["sha256"]) == sha) and not force_reindex:
                    skipped_files += 1
                    continue

                if rec:
                    doc_id = int(rec["id"])
                    self._clear_document_rows(conn, doc_id)
                else:
                    conn.execute(
                        """
                        INSERT INTO documents(source_path, file_name, ext, sha256, imported_at, node_count)
                        VALUES(?, ?, ?, ?, ?, 0)
                        """,
                        (str(path), path.name, path.suffix.lower(), sha, int(time.time())),
                    )
                    doc_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

                nodes = self._parse_file(path)
                inserted = 0
                edge_count = 0
                local_alias_map: Dict[str, int] = {}
                all_edge_drafts: List[ParsedEdgeDraft] = []

                for node in nodes:
                    cursor = conn.execute(
                        """
                        INSERT OR REPLACE INTO nodes(
                            document_id,
                            node_uid,
                            title,
                            body,
                            payload_json,
                            node_type,
                            object_key,
                            applicable_conditions_json,
                            resource_requirements_json,
                            safety_level,
                            source_hierarchy,
                            formula_expression,
                            formula_variables_json,
                            data_source_type,
                            spatial_context_json
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            node.uid,
                            node.title,
                            node.body,
                            node.payload_json,
                            node.node_type,
                            node.object_key,
                            node.applicable_conditions_json,
                            node.resource_requirements_json,
                            node.safety_level,
                            node.source_hierarchy,
                            node.formula_expression,
                            node.formula_variables_json,
                            node.data_source_type,
                            node.spatial_context_json,
                        ),
                    )
                    node_id = int(cursor.lastrowid)
                    if node_id <= 0:
                        row = conn.execute(
                            "SELECT id FROM nodes WHERE document_id = ? AND node_uid = ?",
                            (doc_id, node.uid),
                        ).fetchone()
                        if not row:
                            continue
                        node_id = int(row["id"])

                    tags = _dedupe_terms(node.tags)
                    keywords = _dedupe_terms(node.keywords)
                    for tag in tags:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_tags(node_id, tag) VALUES(?, ?)",
                            (node_id, tag),
                        )
                    for keyword in keywords:
                        conn.execute(
                            "INSERT OR IGNORE INTO node_keywords(node_id, keyword) VALUES(?, ?)",
                            (node_id, keyword),
                        )
                    conn.execute(
                        "INSERT OR REPLACE INTO nodes_fts(rowid, node_uid, title, body, tags, keywords) VALUES(?, ?, ?, ?, ?, ?)",
                        (node_id, node.uid, node.title, node.body, " ".join(tags), " ".join(keywords)),
                    )

                    aliases = node.reference_keys + [node.uid, node.title, node.object_key]
                    for alias in aliases:
                        normalized = _normalize_alias(alias)
                        if len(normalized) < 2:
                            continue
                        conn.execute(
                            "INSERT OR IGNORE INTO node_aliases(node_id, alias) VALUES(?, ?)",
                            (node_id, normalized),
                        )
                        local_alias_map[normalized] = node_id

                    all_edge_drafts.extend(node.edge_drafts)
                    inserted += 1

                for edge in all_edge_drafts:
                    if edge.edge_type not in EDGE_TYPES:
                        continue
                    from_id = self._resolve_node_id(conn, edge.from_ref, local_alias_map)
                    to_id = self._resolve_node_id(conn, edge.to_ref, local_alias_map)
                    if not from_id or not to_id:
                        continue
                    if from_id == to_id:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO graph_edges(from_node_id, to_node_id, edge_type, edge_label, source_path)
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (from_id, to_id, edge.edge_type, edge.edge_label or "", str(path)),
                    )
                    edge_count += 1

                conn.execute(
                    """
                    UPDATE documents
                    SET sha256 = ?, imported_at = ?, node_count = ?
                    WHERE id = ?
                    """,
                    (sha, int(time.time()), inserted, doc_id),
                )

                parsed_files += 1
                total_nodes += inserted
                total_edges += edge_count

            conn.commit()

        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "root": str(root),
            "db_path": str(self.db_path),
            "files_total": len(files),
            "files_parsed": parsed_files,
            "files_skipped": skipped_files,
            "nodes_indexed": total_nodes,
            "edges_indexed": total_edges,
            "duration_ms": duration_ms,
        }

    def _candidate_ids_by_terms(
        self,
        conn: sqlite3.Connection,
        *,
        tags: List[str],
        keywords: List[str],
    ) -> Optional[set[int]]:
        candidate: Optional[set[int]] = None

        if tags:
            marks = ",".join("?" for _ in tags)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_tags WHERE tag IN ({marks})",
                tuple(tags),
            ).fetchall()
            tag_ids = {int(r[0]) for r in rows}
            candidate = tag_ids if candidate is None else candidate.intersection(tag_ids)

        if keywords:
            marks = ",".join("?" for _ in keywords)
            rows = conn.execute(
                f"SELECT DISTINCT node_id FROM node_keywords WHERE keyword IN ({marks})",
                tuple(keywords),
            ).fetchall()
            kw_ids = {int(r[0]) for r in rows}
            candidate = kw_ids if candidate is None else candidate.intersection(kw_ids)

        return candidate

    def _fts_rank_map(
        self,
        conn: sqlite3.Connection,
        query: str,
        *,
        limit: int,
    ) -> Dict[int, float]:
        tokens = _tokenize(query)
        if not tokens:
            return {}
        fts_query = " OR ".join(tokens[:16])
        rows = conn.execute(
            """
            SELECT rowid, bm25(nodes_fts) AS rank
            FROM nodes_fts
            WHERE nodes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, int(limit)),
        ).fetchall()
        return {int(r[0]): float(r[1]) for r in rows}

    def _apply_authority_resolution(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in rows:
            key = _normalize_alias(str(item.get("object_key") or "")) or _normalize_alias(str(item.get("title") or ""))
            if not key:
                key = str(item.get("node_id"))
            weight = int(SOURCE_HIERARCHY_WEIGHTS.get(str(item.get("source_hierarchy") or "未知"), 0))
            current = grouped.get(key)
            if current is None:
                grouped[key] = {**item, "_source_weight": weight}
                continue
            cur_weight = int(current.get("_source_weight") or 0)
            cur_score = float(current.get("score") or 0.0)
            new_score = float(item.get("score") or 0.0)
            if (weight > cur_weight) or (weight == cur_weight and new_score > cur_score):
                grouped[key] = {**item, "_source_weight": weight}

        selected: List[Dict[str, Any]] = []
        for item in grouped.values():
            item.pop("_source_weight", None)
            item["authority_resolution"] = {
                "applied": True,
                "rule": SOURCE_HIERARCHY_RULE,
                "selected_source_hierarchy": item.get("source_hierarchy"),
            }
            selected.append(item)
        return selected

    def search(
        self,
        *,
        query: str = "",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 12,
        node_types: Optional[List[str]] = None,
        resolve_authority: bool = True,
    ) -> Dict[str, Any]:
        top_k = max(1, min(int(top_k or 12), 200))
        norm_tags = _dedupe_terms(tags or [])
        norm_keywords = _dedupe_terms(keywords or [])
        norm_node_types = [str(x).strip() for x in (node_types or []) if str(x).strip()]

        with self._connect() as conn:
            candidates = self._candidate_ids_by_terms(conn, tags=norm_tags, keywords=norm_keywords)
            rank_map = self._fts_rank_map(conn, query, limit=max(180, top_k * 8)) if query.strip() else {}

            if candidates is not None and rank_map:
                target_ids = candidates.intersection(set(rank_map.keys()))
                if not target_ids and candidates:
                    target_ids = candidates
            elif candidates is not None:
                target_ids = candidates
            elif rank_map:
                target_ids = set(rank_map.keys())
            else:
                target_ids = set()

            where_clauses: List[str] = []
            params: List[Any] = []
            if target_ids:
                marks = ",".join("?" for _ in target_ids)
                where_clauses.append(f"n.id IN ({marks})")
                params.extend(sorted(target_ids))
            if norm_node_types:
                marks = ",".join("?" for _ in norm_node_types)
                where_clauses.append(f"n.node_type IN ({marks})")
                params.extend(norm_node_types)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            rows = conn.execute(
                f"""
                SELECT
                    n.id,
                    n.node_uid,
                    n.title,
                    n.body,
                    n.payload_json,
                    n.node_type,
                    n.object_key,
                    n.applicable_conditions_json,
                    n.resource_requirements_json,
                    n.safety_level,
                    n.source_hierarchy,
                    n.formula_expression,
                    n.formula_variables_json,
                    n.data_source_type,
                    n.spatial_context_json,
                    d.file_name,
                    d.source_path,
                    COALESCE(GROUP_CONCAT(DISTINCT t.tag), '') AS tags_csv,
                    COALESCE(GROUP_CONCAT(DISTINCT k.keyword), '') AS keywords_csv
                FROM nodes n
                JOIN documents d ON d.id = n.document_id
                LEFT JOIN node_tags t ON t.node_id = n.id
                LEFT JOIN node_keywords k ON k.node_id = n.id
                {where_sql}
                GROUP BY n.id
                ORDER BY n.id DESC
                LIMIT ?
                """,
                tuple(params + [max(top_k * 18, 240)]),
            ).fetchall()

        query_tokens = _tokenize(query)
        results: List[Dict[str, Any]] = []
        for row in rows:
            body = str(row["body"] or "")
            title = str(row["title"] or "")
            tags_row = [t for t in str(row["tags_csv"] or "").split(",") if t]
            keywords_row = [k for k in str(row["keywords_csv"] or "").split(",") if k]

            score = 0.0
            for tag in norm_tags:
                if tag in tags_row:
                    score += 10.0
            for keyword in norm_keywords:
                if keyword in keywords_row:
                    score += 8.0
                elif keyword in _normalize_term(title) or keyword in _normalize_term(body):
                    score += 5.0
            if query_tokens:
                merged = f"{title}\n{body}".lower()
                score += sum(1.5 for token in query_tokens if token in merged)
            row_id = int(row["id"])
            if row_id in rank_map:
                score += max(0.0, 20.0 - min(20.0, abs(rank_map[row_id]) * 4.0))

            if (norm_tags or norm_keywords or query_tokens) and score <= 0:
                continue

            result_item = {
                "node_id": row["node_uid"],
                "title": title,
                "snippet": body[:260],
                "tags": tags_row[:12],
                "keywords": keywords_row[:18],
                "source_file": row["file_name"],
                "source_path": row["source_path"],
                "source_hierarchy": row["source_hierarchy"],
                "node_type": row["node_type"],
                "object_key": row["object_key"],
                "applicable_conditions": _safe_json_load(row["applicable_conditions_json"], {}),
                "resource_requirements": _safe_json_load(row["resource_requirements_json"], {}),
                "safety_level": row["safety_level"],
                "formula_expression": row["formula_expression"],
                "formula_variables": _safe_json_load(row["formula_variables_json"], []),
                "data_source_type": row["data_source_type"],
                "spatial_context": _safe_json_load(row["spatial_context_json"], {}),
                "score": round(score, 4),
                "payload": _safe_json_load(row["payload_json"], {}),
                "source_provenance": {
                    "source_file": row["file_name"],
                    "source_path": row["source_path"],
                    "source_hierarchy": row["source_hierarchy"],
                },
            }
            results.append(result_item)

        results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        before = len(results)
        if resolve_authority:
            results = self._apply_authority_resolution(results)
            results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)

        return {
            "ok": True,
            "query": query,
            "tags": norm_tags,
            "keywords": norm_keywords,
            "node_types": norm_node_types,
            "total": len(results),
            "results": results[:top_k],
            "db_path": str(self.db_path),
            "authority_resolution": {
                "applied": bool(resolve_authority),
                "rule": SOURCE_HIERARCHY_RULE,
                "before": before,
                "after": len(results),
            },
        }

    def evaluate_formula_nodes(
        self,
        *,
        variables: Dict[str, Any],
        query: str = "",
        tags: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        top_k: int = 12,
        resolve_authority: bool = True,
    ) -> Dict[str, Any]:
        search_result = self.search(
            query=query,
            tags=tags,
            keywords=keywords,
            top_k=top_k,
            node_types=["FormulaNode"],
            resolve_authority=resolve_authority,
        )

        computed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for item in search_result.get("results") or []:
            expr = str(item.get("formula_expression") or "").strip()
            if not expr:
                errors.append({"node_id": item.get("node_id"), "error": "empty_formula_expression"})
                continue
            try:
                value = _safe_eval_formula(expr, variables)
                computed.append({**item, "computed_result": value, "variables": dict(variables)})
            except Exception as exc:
                errors.append({"node_id": item.get("node_id"), "error": str(exc), "formula_expression": expr})

        return {
            "ok": len(computed) > 0 and len(errors) == 0,
            "query": query,
            "variables": dict(variables),
            "total": len(computed),
            "results": computed,
            "errors": errors,
            "authority_resolution": search_result.get("authority_resolution"),
            "db_path": str(self.db_path),
        }

    def get_edges(
        self,
        *,
        edge_type: str | None = None,
        node_ref: str | None = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        clauses: List[str] = []
        params: List[Any] = []
        if edge_type:
            clauses.append("e.edge_type = ?")
            params.append(str(edge_type).strip().upper())

        node_id: Optional[int] = None
        if node_ref:
            with self._connect() as conn:
                node_id = self._resolve_node_id(conn, str(node_ref), {})
            if node_id:
                clauses.append("(e.from_node_id = ? OR e.to_node_id = ?)")
                params.extend([node_id, node_id])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    e.id,
                    e.edge_type,
                    e.edge_label,
                    e.source_path,
                    fn.node_uid AS from_uid,
                    fn.title AS from_title,
                    tn.node_uid AS to_uid,
                    tn.title AS to_title
                FROM graph_edges e
                JOIN nodes fn ON fn.id = e.from_node_id
                JOIN nodes tn ON tn.id = e.to_node_id
                {where_sql}
                ORDER BY e.id ASC
                LIMIT ?
                """,
                tuple(params + [max(1, min(int(limit), 5000))]),
            ).fetchall()

        items = [
            {
                "edge_id": int(r["id"]),
                "edge_type": r["edge_type"],
                "edge_label": r["edge_label"],
                "source_path": r["source_path"],
                "from_node_id": r["from_uid"],
                "from_title": r["from_title"],
                "to_node_id": r["to_uid"],
                "to_title": r["to_title"],
            }
            for r in rows
        ]
        return {"ok": True, "total": len(items), "edges": items, "db_path": str(self.db_path)}

    def validate_requires_closure(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    e.from_node_id,
                    e.to_node_id,
                    fn.node_uid AS from_uid,
                    tn.node_uid AS to_uid
                FROM graph_edges e
                JOIN nodes fn ON fn.id = e.from_node_id
                JOIN nodes tn ON tn.id = e.to_node_id
                WHERE e.edge_type = ?
                """,
                (EDGE_REQUIRES,),
            ).fetchall()

        graph: Dict[int, List[int]] = {}
        id_to_uid: Dict[int, str] = {}
        for row in rows:
            f = int(row["from_node_id"])
            t = int(row["to_node_id"])
            graph.setdefault(f, []).append(t)
            graph.setdefault(t, [])
            id_to_uid[f] = str(row["from_uid"])
            id_to_uid[t] = str(row["to_uid"])

        visited: Dict[int, int] = {}  # 0=unseen,1=visiting,2=done
        stack: List[int] = []
        cycles: List[List[str]] = []

        def dfs(node: int) -> None:
            state = visited.get(node, 0)
            if state == 1:
                if node in stack:
                    idx = stack.index(node)
                    cyc = stack[idx:] + [node]
                    cycles.append([id_to_uid.get(x, str(x)) for x in cyc])
                return
            if state == 2:
                return

            visited[node] = 1
            stack.append(node)
            for nxt in graph.get(node, []):
                dfs(nxt)
            stack.pop()
            visited[node] = 2

        for node in list(graph.keys()):
            if visited.get(node, 0) == 0:
                dfs(node)

        return {
            "ok": len(cycles) == 0,
            "edge_type": EDGE_REQUIRES,
            "edge_count": len(rows),
            "cycle_count": len(cycles),
            "cycles": cycles,
            "db_path": str(self.db_path),
        }


def ingest_knowledge_graph(
    root_dir: Path | str = DEFAULT_KG_ROOT,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
    force_reindex: bool = False,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.ingest_directory(root_dir=root_dir, force_reindex=force_reindex)


def search_graph_index(
    *,
    query: str = "",
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    top_k: int = 12,
    node_types: Optional[List[str]] = None,
    resolve_authority: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.search(
        query=query,
        tags=tags,
        keywords=keywords,
        top_k=top_k,
        node_types=node_types,
        resolve_authority=resolve_authority,
    )


def evaluate_formula_nodes_in_graph(
    *,
    variables: Dict[str, Any],
    query: str = "",
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    top_k: int = 12,
    resolve_authority: bool = True,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.evaluate_formula_nodes(
        variables=variables,
        query=query,
        tags=tags,
        keywords=keywords,
        top_k=top_k,
        resolve_authority=resolve_authority,
    )


def get_graph_edges(
    *,
    edge_type: str | None = None,
    node_ref: str | None = None,
    limit: int = 500,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.get_edges(edge_type=edge_type, node_ref=node_ref, limit=limit)


def validate_requires_edges(
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    index = KnowledgeGraphIndex(db_path=db_path)
    return index.validate_requires_closure()
