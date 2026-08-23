from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Sequence


SCHEMA = "requirement-evidence-matrix-v1"
_TRACEABLE_LOCATOR_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", re.IGNORECASE)
_REQUIREMENT_MARKER_RE = re.compile(r"【要求:([^】]{3,80})】")
_SPACE_RE = re.compile(r"\s+")


_DIMENSION_CHAPTER_HINTS: Dict[str, Sequence[str]] = {
    "质量目标": ("质量", "检验", "验收", "试验", "测量"),
    "安全等级": ("安全", "应急", "危大", "消防"),
    "进度节点": ("进度", "工期", "计划", "资源", "部署"),
    "环保要求": ("环保", "环境", "文明", "绿色"),
    "重难点": ("重难点", "关键", "施工方案", "技术", "工艺"),
    "扣分项": ("质量", "安全", "进度", "保证", "控制", "验收"),
}


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _stable_id(kind: str, payload: Dict[str, Any]) -> str:
    prefix = {
        "tender_score_item": "TS",
        "chapter_requirement": "CR",
        "global_requirement": "GR",
    }.get(kind, "RQ")
    return f"REQ-{prefix}-{_digest(payload)[:12].upper()}"


def _dedupe(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for value in values:
        text = _clean(value)
        if text and text not in out:
            out.append(text)
    return out


def _chapter_contracts(agent_contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in (agent_contract.get("chapters") or [])
        if isinstance(row, dict) and _clean(row.get("title"))
    ]


def _responsibility(contract: Dict[str, Any] | None) -> Dict[str, Any]:
    contract = contract if isinstance(contract, dict) else {}
    agents = contract.get("agents") if isinstance(contract.get("agents"), dict) else {}
    auxiliary = [
        _clean(row.get("name") or row.get("agent") or row.get("role"))
        for row in (agents.get("auxiliary") or [])
        if isinstance(row, dict)
    ]
    return {
        "chapter_id": _clean(contract.get("chapter_id")),
        "master_agent": _clean(agents.get("master")),
        "specialist_agents": _dedupe(agents.get("specialists") or []),
        "auxiliary_agents": _dedupe(auxiliary),
        "compliance_agent": _clean(agents.get("compliance")),
    }


def _source_receipts(spans: Any) -> List[Dict[str, Any]]:
    receipts: List[Dict[str, Any]] = []
    for raw in spans if isinstance(spans, list) else []:
        if not isinstance(raw, dict):
            continue
        snippet = str(raw.get("snippet") or "")
        receipt = {
            "file_name": _clean(raw.get("file_name")),
            "page": raw.get("page"),
            "start": raw.get("start"),
            "end": raw.get("end"),
            "snippet_sha256": hashlib.sha256(snippet.encode("utf-8")).hexdigest() if snippet else None,
        }
        receipt["locator"] = "#".join(
            [
                receipt["file_name"] or "tender",
                f"p{receipt['page']}" if receipt.get("page") not in (None, "") else "p?",
                f"{receipt.get('start')}:{receipt.get('end')}",
            ]
        )
        receipts.append(receipt)
    return receipts


def _explicit_bool(row: Dict[str, Any], *names: str) -> bool:
    return any(bool(row.get(name)) for name in names)


def _select_chapters(
    *,
    dimension: str,
    keywords: Sequence[str],
    contracts: Sequence[Dict[str, Any]],
) -> List[str]:
    scores: List[tuple[int, int, str]] = []
    hints = list(_DIMENSION_CHAPTER_HINTS.get(dimension, ()))
    for idx, contract in enumerate(contracts):
        title = _clean(contract.get("title"))
        compact_title = _SPACE_RE.sub("", title).lower()
        score = 0
        for keyword in keywords:
            compact_keyword = _SPACE_RE.sub("", _clean(keyword)).lower()
            if compact_keyword and compact_keyword in compact_title:
                score += 6
        for hint in hints:
            if hint and hint in title:
                score += 2
        if score:
            scores.append((score, -idx, title))
    if scores:
        scores.sort(reverse=True)
        best = scores[0][0]
        return [title for score, _, title in scores if score == best][:3]
    # A score item must still have one accountable owner. Prefer the first substantive
    # chapter rather than leaving it silently unowned.
    return [_clean(contracts[0].get("title"))] if contracts else []


def _requirement_text(raw: Any) -> str:
    if isinstance(raw, dict):
        return _clean(
            raw.get("requirement")
            or raw.get("text")
            or raw.get("content")
            or raw.get("title")
        )
    return _clean(raw)


def _match_terms(text: str, explicit_keywords: Sequence[str]) -> List[str]:
    terms = _dedupe(explicit_keywords)
    if terms:
        return terms[:12]
    # Preserve meaningful Chinese/ASCII chunks while dropping generic obligation words.
    stop = {"必须", "应当", "应该", "需要", "要求", "本章", "内容", "提供", "符合", "进行"}
    chunks = re.findall(r"[\u4e00-\u9fff]{2,12}|[A-Za-z][A-Za-z0-9_.-]{2,}", text)
    return [chunk for chunk in _dedupe(chunks) if chunk not in stop][:12]


def build_requirement_evidence_plan(
    *,
    tender: Dict[str, Any],
    chapter_requirements: Dict[str, Any],
    global_requirements: Sequence[Any],
    agent_contract: Dict[str, Any],
) -> Dict[str, Any]:
    contracts = _chapter_contracts(agent_contract)
    by_title = {_clean(row.get("title")): row for row in contracts}
    rows: List[Dict[str, Any]] = []

    for index, raw in enumerate(tender.get("items") or [], start=1):
        if not isinstance(raw, dict):
            continue
        dimension = _clean(raw.get("dimension")) or "评分点"
        keywords = _dedupe(raw.get("keywords") or [])
        source_receipts = _source_receipts(raw.get("source_spans"))
        identity = {
            "kind": "tender_score_item",
            "index": index,
            "dimension": dimension,
            "keywords": keywords,
            "source_receipts": source_receipts,
        }
        requirement_id = _clean(raw.get("rule_id")) or _stable_id("tender_score_item", identity)
        targets = _select_chapters(
            dimension=dimension,
            keywords=keywords,
            contracts=contracts,
        )
        mandatory = dimension in {"扣分项", "PENALTY"} or _explicit_bool(
            raw, "mandatory", "required", "critical", "is_mandatory"
        )
        rows.append(
            {
                "requirement_id": requirement_id,
                "kind": "tender_score_item",
                "requirement": f"{dimension}：{'；'.join(keywords) or '按招标评分要求落实'}",
                "dimension": dimension,
                "keywords": keywords,
                "match_terms": _match_terms("", keywords),
                "weight": raw.get("weight"),
                "mandatory": mandatory,
                "verification_mode": "content",
                "evidence_required": bool(source_receipts),
                "source_evidence": source_receipts,
                "target_chapters": targets,
                "responsibility": [_responsibility(by_title.get(title)) for title in targets],
                "planning_status": "PLANNED" if targets else "UNMAPPED",
            }
        )

    for title, raw_requirements in (chapter_requirements or {}).items():
        target = _clean(title)
        requirements = raw_requirements if isinstance(raw_requirements, list) else [raw_requirements]
        for index, raw in enumerate(requirements, start=1):
            text = _requirement_text(raw)
            if not text:
                continue
            raw_dict = raw if isinstance(raw, dict) else {}
            source_receipts = _source_receipts(
                raw_dict.get("source_spans") or raw_dict.get("sources")
            )
            identity = {
                "kind": "chapter_requirement",
                "chapter": target,
                "index": index,
                "requirement": text,
                "source_receipts": source_receipts,
            }
            requirement_id = _clean(raw_dict.get("requirement_id")) or _stable_id(
                "chapter_requirement", identity
            )
            targets = [target] if target in by_title else []
            rows.append(
                {
                    "requirement_id": requirement_id,
                    "kind": "chapter_requirement",
                    "requirement": text,
                    "dimension": "章节强制要求",
                    "keywords": _dedupe(raw_dict.get("keywords") or []),
                    "match_terms": _match_terms(text, raw_dict.get("keywords") or []),
                    "weight": raw_dict.get("weight"),
                    "mandatory": True,
                    "verification_mode": "content",
                    "evidence_required": bool(source_receipts) or bool(raw_dict.get("evidence_required")),
                    "source_evidence": source_receipts,
                    "target_chapters": targets,
                    "responsibility": [_responsibility(by_title.get(target))] if targets else [],
                    "planning_status": "PLANNED" if targets else "UNMAPPED",
                }
            )

    for index, raw in enumerate(global_requirements or [], start=1):
        text = _requirement_text(raw)
        if not text:
            continue
        raw_dict = raw if isinstance(raw, dict) else {}
        source_receipts = _source_receipts(raw_dict.get("source_spans") or raw_dict.get("sources"))
        identity = {
            "kind": "global_requirement",
            "index": index,
            "requirement": text,
            "source_receipts": source_receipts,
        }
        rows.append(
            {
                "requirement_id": _clean(raw_dict.get("requirement_id"))
                or _stable_id("global_requirement", identity),
                "kind": "global_requirement",
                "requirement": text,
                "dimension": "全局强制要求",
                "keywords": _dedupe(raw_dict.get("keywords") or []),
                "match_terms": _match_terms(text, raw_dict.get("keywords") or []),
                "weight": raw_dict.get("weight"),
                "mandatory": True,
                "verification_mode": "document_control",
                "evidence_required": bool(source_receipts),
                "source_evidence": source_receipts,
                "target_chapters": [],
                "responsibility": [
                    {
                        "chapter_id": "DOCUMENT-CONTROL",
                        "master_agent": "总控Agent",
                        "specialist_agents": [],
                        "auxiliary_agents": [],
                        "compliance_agent": "规范合规Agent",
                    }
                ],
                "planning_status": "DELEGATED_DOCUMENT_CONTROL",
            }
        )

    core = {
        "schema": SCHEMA,
        "phase": "planned",
        "rows": rows,
        "summary": {
            "requirement_count": len(rows),
            "mandatory_count": sum(1 for row in rows if row.get("mandatory")),
            "source_bound_count": sum(1 for row in rows if row.get("source_evidence")),
            "unmapped_count": sum(1 for row in rows if row.get("planning_status") == "UNMAPPED"),
        },
    }
    return {**core, "matrix_digest": _digest(core)}


def validate_requirement_evidence_matrix(matrix: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    if matrix.get("schema") != SCHEMA:
        errors.append("schema_mismatch")
    supplied = _clean(matrix.get("matrix_digest"))
    core = {key: value for key, value in matrix.items() if key != "matrix_digest"}
    computed = _digest(core)
    if not supplied or supplied != computed:
        errors.append("digest_mismatch")
    ids = [_clean(row.get("requirement_id")) for row in (matrix.get("rows") or []) if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_requirement_id")
    return {"ok": not errors, "errors": errors, "computed_digest": computed}


def requirement_rows_for_chapter(plan: Dict[str, Any], title: str) -> List[Dict[str, Any]]:
    chapter = _clean(title)
    return [
        dict(row)
        for row in (plan.get("rows") or [])
        if isinstance(row, dict)
        and chapter in [_clean(value) for value in (row.get("target_chapters") or [])]
    ]


def requirement_prompt_lines_for_chapter(plan: Dict[str, Any], title: str) -> List[str]:
    lines: List[str] = []
    for row in requirement_rows_for_chapter(plan, title):
        requirement_id = _clean(row.get("requirement_id"))
        requirement = _clean(row.get("requirement"))
        responsibility = row.get("responsibility") or []
        agents: List[str] = []
        for receipt in responsibility:
            if not isinstance(receipt, dict):
                continue
            agents.extend(
                [
                    receipt.get("master_agent"),
                    *(receipt.get("specialist_agents") or []),
                    receipt.get("compliance_agent"),
                ]
            )
        line = (
            f"【要求绑定:{requirement_id}】责任Agent={'、'.join(_dedupe(agents)) or '章节主笔Agent'}；"
            f"必须在本章实质落实：{requirement}；落实段落必须保留【要求:{requirement_id}】标记。"
        )
        if row.get("evidence_required"):
            line += "并必须在同段给出可反查的【证据:文件#页码_哈希@偏移】定位。"
        lines.append(line)
    return lines


def _explicit_sources(row: Dict[str, Any]) -> List[str]:
    return [
        _clean(value)
        for value in (row.get("evidence_sources") or [])
        if _clean(value) and not _clean(value).startswith("AUTO://")
    ]


def finalize_requirement_evidence_matrix(
    *,
    plan: Dict[str, Any],
    sections: Sequence[Dict[str, Any]],
    evidence_tracking: Dict[str, Any],
) -> Dict[str, Any]:
    sections_by_title = {
        _clean(section.get("title")): section
        for section in sections
        if isinstance(section, dict) and _clean(section.get("title"))
    }
    evidence_rows = [row for row in (evidence_tracking.get("rows") or []) if isinstance(row, dict)]
    finalized: List[Dict[str, Any]] = []

    for planned in plan.get("rows") or []:
        if not isinstance(planned, dict):
            continue
        row = dict(planned)
        mode = _clean(row.get("verification_mode")) or "content"
        targets = [_clean(value) for value in (row.get("target_chapters") or []) if _clean(value)]
        if mode == "document_control":
            row.update(
                {
                    "status": "DELEGATED_DOCUMENT_CONTROL",
                    "matched_chapters": [],
                    "response_evidence": [],
                    "blocking": False,
                }
            )
            finalized.append(row)
            continue
        if not targets:
            row.update(
                {
                    "status": "UNMAPPED",
                    "matched_chapters": [],
                    "response_evidence": [],
                    "blocking": bool(row.get("mandatory")),
                }
            )
            finalized.append(row)
            continue

        requirement_id = _clean(row.get("requirement_id"))
        matched_chapters: List[str] = []
        marker_found = False
        term_hits: List[str] = []
        for title in targets:
            section = sections_by_title.get(title) or {}
            content = str(section.get("content") or "")
            if f"【要求:{requirement_id}】" in content or requirement_id in _REQUIREMENT_MARKER_RE.findall(content):
                marker_found = True
                matched_chapters.append(title)
                continue
            compact = _SPACE_RE.sub("", content).lower()
            hits = [term for term in (row.get("match_terms") or []) if _SPACE_RE.sub("", _clean(term)).lower() in compact]
            if hits:
                term_hits.extend(hits)
                matched_chapters.append(title)

        response_evidence: List[Dict[str, Any]] = []
        for evidence_row in evidence_rows:
            if _clean(evidence_row.get("section_title")) not in targets:
                continue
            sources = _explicit_sources(evidence_row)
            if not sources:
                continue
            response_evidence.append(
                {
                    "paragraph_id": _clean(evidence_row.get("paragraph_id")),
                    "page_estimate": evidence_row.get("page_estimate"),
                    "sources": sources,
                    "traceable": any(_TRACEABLE_LOCATOR_RE.search(source) for source in sources),
                }
            )

        covered = bool(matched_chapters)
        has_explicit_evidence = bool(response_evidence)
        has_traceable_evidence = any(item.get("traceable") for item in response_evidence)
        if not covered:
            status = "MISSING_RESPONSE"
        elif row.get("evidence_required") and not has_explicit_evidence:
            status = "COVERED_UNEVIDENCED"
        elif row.get("evidence_required") and not has_traceable_evidence:
            status = "COVERED_UNTRACEABLE"
        elif has_traceable_evidence:
            status = "COVERED_TRACEABLE"
        else:
            status = "COVERED"
        blocking = bool(row.get("mandatory")) and status in {
            "MISSING_RESPONSE",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
        }
        row.update(
            {
                "status": status,
                "matched_chapters": _dedupe(matched_chapters),
                "marker_found": marker_found,
                "matched_terms": _dedupe(term_hits),
                "response_evidence": response_evidence,
                "blocking": blocking,
            }
        )
        finalized.append(row)

    blocking_ids = [row["requirement_id"] for row in finalized if row.get("blocking")]
    warning_ids = [
        row["requirement_id"]
        for row in finalized
        if not row.get("blocking") and row.get("status") in {"MISSING_RESPONSE", "UNMAPPED", "COVERED_UNEVIDENCED", "COVERED_UNTRACEABLE"}
    ]
    core = {
        "schema": SCHEMA,
        "phase": "verified",
        "plan_digest": plan.get("matrix_digest"),
        "rows": finalized,
        "summary": {
            "requirement_count": len(finalized),
            "covered_count": sum(1 for row in finalized if str(row.get("status") or "").startswith("COVERED")),
            "traceable_count": sum(1 for row in finalized if row.get("status") == "COVERED_TRACEABLE"),
            "blocking_count": len(blocking_ids),
            "warning_count": len(warning_ids),
            "blocking_requirement_ids": blocking_ids,
            "warning_requirement_ids": warning_ids,
            "strict_delivery_allowed": not blocking_ids,
        },
    }
    return {**core, "matrix_digest": _digest(core)}
