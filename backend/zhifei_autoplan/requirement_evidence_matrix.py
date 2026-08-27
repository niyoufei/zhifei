from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Sequence


SCHEMA = "requirement-evidence-matrix-v1"
EVIDENCE_GATE_VERSION = "requirement-evidence-precheckpoint-v3"
_TRACEABLE_LOCATOR_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", re.IGNORECASE)
_REQUIREMENT_MARKER_RE = re.compile(r"【要求:([^】]{3,80})】")
_SPACE_RE = re.compile(r"\s+")
_PAGE_LIMIT_RE = re.compile(r"总页数\s*(?:不超过|≤|<=)\s*(\d+)\s*页")
_SCORE_FRAGMENT_RE = re.compile(
    r"(?:每\s*(?:提供|具备|有|缺少|缺|少|增加).{0,24}?(?:得|扣)\s*\d+(?:\.\d+)?\s*分|"
    r"本项.{0,12}?(?:(?:满分|得分)\s*\d*(?:\.\d+)?\s*分?|不得分)|"
    r"满分\s*\d+(?:\.\d+)?\s*分?|"
    r"(?:得|扣|加)\s*\d+(?:\.\d+)?\s*分|评分标准|得分项)",
    re.IGNORECASE,
)
_ACTIONABLE_REQUIREMENT_RE = re.compile(
    r"(?:必须|应当|须|需|不得|严禁|禁止|编制|建立|制定|提供|包含|包括|"
    r"明确|说明|阐述|配置|配备|落实|提交|采用|设置|执行|保证|确保|满足|"
    r"符合|安排|实施|检查|验收|监测|记录|报告|控制|保护|维护|组织|完成|"
    r"列明|附具|到位)",
)
_TRUNCATED_PREFIX_RE = re.compile(
    r"^(?:中|其中|内|所述|上述|以上|以下|前述)(?:规定|要求|所列|中|的|应|须|提供|包含|包括)"
)
_TRUNCATED_SUFFIX_RE = re.compile(
    r"(?:不得|应|须|必须|需|提供|包含|包括|明确|说明|阐述|本项满分?|得分|扣分|"
    r"所述|如下|下列|以下|以上)\s*[：:]?$"
)


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
        source_file_name = _clean(raw.get("file_name"))
        display_file_name = re.split(r"[/\\\\]", source_file_name)[-1]
        snippet_sha256 = (
            hashlib.sha256(snippet.encode("utf-8")).hexdigest() if snippet else None
        )
        supplied_sha256 = _clean(raw.get("sha256")).lower()
        source_sha256 = (
            supplied_sha256
            if re.fullmatch(r"[0-9a-f]{64}", supplied_sha256)
            else snippet_sha256
        )
        receipt = {
            "file_name": source_file_name,
            # Only this basename-derived field may flow into a model prompt.
            "display_file_name": display_file_name,
            "page": raw.get("page"),
            "start": raw.get("start"),
            "end": raw.get("end"),
            "snippet_sha256": snippet_sha256,
        }
        receipt["locator"] = "#".join(
            [
                receipt["file_name"] or "tender",
                f"p{receipt['page']}" if receipt.get("page") not in (None, "") else "p?",
                f"{receipt.get('start')}:{receipt.get('end')}",
            ]
        )
        try:
            offset = int(receipt.get("start"))
        except (TypeError, ValueError):
            offset = None
        page = receipt.get("page")
        try:
            page_token = f"p{int(page)}_" if page not in (None, "") else ""
        except (TypeError, ValueError):
            page_token = ""
        receipt["traceable_locator"] = (
            f"{display_file_name or 'tender'}#{page_token}{source_sha256[:8]}@{offset}"
            if source_sha256 and offset is not None
            else None
        )
        receipts.append(receipt)
    return receipts


def _source_receipt_identity(receipts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep requirement IDs stable when receipt/policy metadata is extended."""

    legacy_keys = ("file_name", "page", "start", "end", "snippet_sha256", "locator")
    return [
        {key: receipt.get(key) for key in legacy_keys}
        for receipt in receipts
        if isinstance(receipt, dict)
    ]


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
        # One accountable chapter owns a score item.  Other chapters may refer to
        # it, but are not all forced to duplicate the same response/evidence marker.
        return [scores[0][2]]
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


def classify_chapter_requirement_quality(raw: Any) -> Dict[str, Any]:
    """Classify whether one extracted chapter clause is executable.

    Tender score tables are frequently split into sentence fragments such as
    ``每提供 1 个得 2 分`` or ``本项不得``. They are useful review evidence,
    but they are not standalone instructions that a model can faithfully
    implement. Keep those fragments observable while preventing them from
    becoming mandatory prompt/gate contracts.
    """

    raw_dict = raw if isinstance(raw, dict) else {}
    text = _requirement_text(raw)
    compact = _SPACE_RE.sub("", text)
    reasons = _dedupe(raw_dict.get("review_reason_codes") or [])
    explicit_statuses = {
        _clean(raw_dict.get(name)).upper()
        for name in ("quality_status", "review_status", "planning_status", "status")
        if _clean(raw_dict.get(name))
    }
    if "NEEDS_REVIEW" in explicit_statuses or raw_dict.get("prompt_eligible") is False:
        reasons.append("EXPLICIT_REVIEW_REQUIRED")
    if len(compact) < 8:
        reasons.append("TOO_SHORT")
    if _TRUNCATED_PREFIX_RE.search(text):
        reasons.append("TRUNCATED_PREFIX")
    if _TRUNCATED_SUFFIX_RE.search(text):
        reasons.append("TRUNCATED_SUFFIX")

    has_score_fragment = bool(_SCORE_FRAGMENT_RE.search(text))
    action_text = _SCORE_FRAGMENT_RE.sub(" ", text) if has_score_fragment else text
    actionable = bool(_ACTIONABLE_REQUIREMENT_RE.search(action_text))
    if has_score_fragment and not actionable:
        reasons.append("SCORE_ONLY_FRAGMENT")
    if not actionable:
        reasons.append("NO_EXECUTABLE_ACTION")

    reasons = _dedupe(reasons)
    needs_review = bool(reasons)
    return {
        "requirement": text,
        "quality_status": "NEEDS_REVIEW" if needs_review else "READY",
        "mandatory": not needs_review,
        "prompt_eligible": not needs_review,
        "review_reason_codes": reasons,
    }


def _row_needs_review(row: Dict[str, Any]) -> bool:
    return (
        _clean(row.get("planning_status")).upper() == "NEEDS_REVIEW"
        or _clean(row.get("quality_status")).upper() == "NEEDS_REVIEW"
        or row.get("prompt_eligible") is False
    )


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
            "source_receipts": _source_receipt_identity(source_receipts),
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

    chapter_requirement_inputs: Dict[str, List[Any]] = {}
    seen_chapter_requirements: set[tuple[str, str]] = set()
    for title, raw_requirements in (chapter_requirements or {}).items():
        target = _clean(title)
        requirements = raw_requirements if isinstance(raw_requirements, list) else [raw_requirements]
        for raw in requirements:
            identity = (target, _requirement_text(raw))
            if not target or not identity[1] or identity in seen_chapter_requirements:
                continue
            seen_chapter_requirements.add(identity)
            chapter_requirement_inputs.setdefault(target, []).append(raw)

    extraction_meta = tender.get("extraction_meta") if isinstance(tender, dict) else {}
    review_meta = (
        extraction_meta.get("chapter_requirement_review")
        if isinstance(extraction_meta, dict)
        else {}
    )
    review_candidates = review_meta.get("rows") if isinstance(review_meta, dict) else []
    for raw in review_candidates if isinstance(review_candidates, list) else []:
        if not isinstance(raw, dict):
            continue
        target = _clean(raw.get("chapter_title") or raw.get("chapter"))
        reviewed = dict(raw)
        reviewed["planning_status"] = "NEEDS_REVIEW"
        reviewed["prompt_eligible"] = False
        reviewed["mandatory"] = False
        reviewed["review_reason_codes"] = _dedupe(
            reviewed.get("review_reason_codes") or reviewed.get("reason_codes") or []
        )
        identity = (target, _requirement_text(reviewed))
        if not target or not identity[1] or identity in seen_chapter_requirements:
            continue
        seen_chapter_requirements.add(identity)
        chapter_requirement_inputs.setdefault(target, []).append(reviewed)

    for target, requirements in chapter_requirement_inputs.items():
        for index, raw in enumerate(requirements, start=1):
            quality = classify_chapter_requirement_quality(raw)
            text = _clean(quality.get("requirement"))
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
                "source_receipts": _source_receipt_identity(source_receipts),
            }
            requirement_id = _clean(raw_dict.get("requirement_id")) or _stable_id(
                "chapter_requirement", identity
            )
            targets = [target] if target in by_title else []
            needs_review = quality.get("quality_status") == "NEEDS_REVIEW"
            rows.append(
                {
                    "requirement_id": requirement_id,
                    "kind": "chapter_requirement",
                    "requirement": text,
                    "dimension": "章节要求待复核" if needs_review else "章节强制要求",
                    "keywords": _dedupe(raw_dict.get("keywords") or []),
                    "match_terms": _match_terms(text, raw_dict.get("keywords") or []),
                    "weight": raw_dict.get("weight"),
                    "mandatory": bool(quality.get("mandatory")),
                    "verification_mode": "manual_review" if needs_review else "content",
                    "evidence_required": bool(source_receipts) or bool(raw_dict.get("evidence_required")),
                    "source_evidence": source_receipts,
                    "target_chapters": targets,
                    "responsibility": [_responsibility(by_title.get(target))] if targets else [],
                    "planning_status": (
                        "NEEDS_REVIEW"
                        if needs_review
                        else "PLANNED"
                        if targets
                        else "UNMAPPED"
                    ),
                    "quality_status": quality.get("quality_status"),
                    "prompt_eligible": bool(quality.get("prompt_eligible")),
                    "review_reason_codes": list(
                        quality.get("review_reason_codes") or []
                    ),
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
            "source_receipts": _source_receipt_identity(source_receipts),
        }
        page_limit_match = _PAGE_LIMIT_RE.search(text)
        document_control_kind = (
            "page_limit"
            if page_limit_match
            else "format_policy"
            if any(token in text for token in ("字体", "字号", "行距", "页边距", "版式参数"))
            else "content"
        )
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
                "document_control_kind": document_control_kind,
                "control_expected": (
                    {"max_pages": int(page_limit_match.group(1))}
                    if page_limit_match
                    else {}
                ),
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
        "evidence_gate_version": EVIDENCE_GATE_VERSION,
        "phase": "planned",
        "rows": rows,
        "summary": {
            "requirement_count": len(rows),
            "mandatory_count": sum(1 for row in rows if row.get("mandatory")),
            "needs_review_count": sum(1 for row in rows if _row_needs_review(row)),
            "prompt_eligible_count": sum(
                1 for row in rows if row.get("prompt_eligible") is not False
            ),
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


def _planned_traceable_locators(row: Dict[str, Any]) -> List[str]:
    return _dedupe(
        receipt.get("traceable_locator")
        for receipt in (row.get("source_evidence") or [])
        if isinstance(receipt, dict)
        and _TRACEABLE_LOCATOR_RE.search(_clean(receipt.get("traceable_locator")))
    )


def validate_requirement_evidence_plan_readiness(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Fail closed before provider calls when a mandatory evidence plan is unusable."""

    structural = validate_requirement_evidence_matrix(plan)
    blocking: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    for row in (plan.get("rows") or []):
        if not isinstance(row, dict):
            continue
        requirement_id = _clean(row.get("requirement_id")) or "UNKNOWN"
        if _row_needs_review(row):
            warnings.append(
                {
                    "requirement_id": requirement_id,
                    "code": "REQUIREMENT_NEEDS_REVIEW",
                }
            )
            continue
        mandatory = bool(row.get("mandatory"))
        row_findings: List[Dict[str, str]] = []
        if (
            _clean(row.get("verification_mode")) != "document_control"
            and not _dedupe(row.get("target_chapters") or [])
        ):
            row_findings.append(
                {"requirement_id": requirement_id, "code": "REQUIREMENT_UNMAPPED"}
            )
        if bool(row.get("evidence_required")) and not _planned_traceable_locators(row):
            row_findings.append(
                {
                    "requirement_id": requirement_id,
                    "code": "SOURCE_LOCATOR_UNTRACEABLE",
                }
            )
        (blocking if mandatory else warnings).extend(row_findings)

    errors = list(structural.get("errors") or [])
    errors.extend(
        f"{finding['code']}:{finding['requirement_id']}" for finding in blocking
    )
    return {
        "ok": bool(structural.get("ok")) and not blocking,
        "errors": errors,
        "blocking": blocking,
        "warnings": warnings,
        "blocking_requirement_ids": _dedupe(
            finding.get("requirement_id") for finding in blocking
        ),
        "warning_requirement_ids": _dedupe(
            finding.get("requirement_id") for finding in warnings
        ),
        "computed_digest": structural.get("computed_digest"),
    }


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
        if _row_needs_review(row):
            continue
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
            locators = _planned_traceable_locators(row)
            if locators:
                markers = "、".join(f"【证据:{value}】" for value in locators[:3])
                line += (
                    f"并必须在同段原样引用已核验来源定位{markers}；"
                    "禁止改写定位、禁止编造其他来源。"
                )
            else:
                line += "当前没有已核验来源定位；禁止编造【证据:...】标记。"
        lines.append(line)
    return lines


def validate_chapter_requirement_evidence(
    *,
    plan: Dict[str, Any],
    title: str,
    section: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate one chapter before it is counted or persisted as successful.

    Evidence is deliberately checked in the same paragraph as its requirement
    marker.  A locator elsewhere in the chapter cannot accidentally satisfy a
    different tender requirement.
    """

    content = str((section or {}).get("content") or "")
    paragraphs = [
        value.strip()
        for value in re.split(r"[\r\n]+", content)
        if value.strip()
    ]
    results: List[Dict[str, Any]] = []
    for row in requirement_rows_for_chapter(plan, title):
        requirement_id = _clean(row.get("requirement_id"))
        if _row_needs_review(row):
            results.append(
                {
                    "requirement_id": requirement_id,
                    "status": "NEEDS_REVIEW",
                    "blocking": False,
                    "marker_found": False,
                    "traceable_locators": [],
                    "planned_traceable_locators": _planned_traceable_locators(row),
                    "matched_planned_locators": [],
                    "review_reason_codes": list(
                        row.get("review_reason_codes") or []
                    ),
                }
            )
            continue
        marker = f"【要求:{requirement_id}】"
        matched = [paragraph for paragraph in paragraphs if marker in paragraph]
        marker_found = bool(matched)
        locators: List[str] = []
        for paragraph in matched:
            locators.extend(
                value.strip()
                for value in re.findall(r"【证据:([^】]{1,260})】", paragraph)
                if value.strip() and not value.strip().startswith("AUTO://")
            )
        locators = _dedupe(locators)
        traceable = [
            value for value in locators if _TRACEABLE_LOCATOR_RE.search(value)
        ]
        planned_locators = _planned_traceable_locators(row)
        matched_planned_locators = [
            value for value in traceable if value in planned_locators
        ]
        if not marker_found:
            status = "MISSING_REQUIREMENT_MARKER"
        elif row.get("evidence_required") and not locators:
            status = "COVERED_UNEVIDENCED"
        elif row.get("evidence_required") and not traceable:
            status = "COVERED_UNTRACEABLE"
        elif row.get("evidence_required") and not matched_planned_locators:
            status = "EVIDENCE_SOURCE_MISMATCH"
        else:
            status = "COVERED_TRACEABLE" if traceable else "COVERED"
        blocking = bool(row.get("mandatory")) and status in {
            "MISSING_REQUIREMENT_MARKER",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
            "EVIDENCE_SOURCE_MISMATCH",
        }
        results.append(
            {
                "requirement_id": requirement_id,
                "status": status,
                "blocking": blocking,
                "marker_found": marker_found,
                "traceable_locators": traceable,
                "planned_traceable_locators": planned_locators,
                "matched_planned_locators": matched_planned_locators,
            }
        )
    blocking_ids = [
        row["requirement_id"] for row in results if row.get("blocking")
    ]
    warning_ids = [
        row["requirement_id"]
        for row in results
        if not row.get("blocking")
        and row.get("status")
        in {
            "MISSING_REQUIREMENT_MARKER",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
            "EVIDENCE_SOURCE_MISMATCH",
            "NEEDS_REVIEW",
        }
    ]
    return {
        "ok": not blocking_ids,
        "chapter_title": _clean(title),
        "rows": results,
        "blocking_requirement_ids": blocking_ids,
        "warning_requirement_ids": warning_ids,
    }


def _explicit_sources(row: Dict[str, Any]) -> List[str]:
    return [
        _clean(value)
        for value in (row.get("evidence_sources") or [])
        if _clean(value) and not _clean(value).startswith("AUTO://")
    ]


def _verify_document_control_requirement(
    *,
    row: Dict[str, Any],
    sections_by_title: Dict[str, Dict[str, Any]],
    control_evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Verify a document-wide mandatory requirement against actual chapter text.

    ``document_control`` is a verification scope, not a waiver.  A requirement
    is covered only when its substantive text is present somewhere in the
    generated document.  Evidence-bound controls additionally have to retain an
    exact planned locator in the same matched chapter.
    """

    requirement_id = _clean(row.get("requirement_id"))
    control_kind = _clean(row.get("document_control_kind")) or "content"
    evidence = control_evidence if isinstance(control_evidence, dict) else {}
    if control_kind == "page_limit":
        page_plan = evidence.get("page_plan") if isinstance(evidence.get("page_plan"), dict) else {}
        expected = row.get("control_expected") if isinstance(row.get("control_expected"), dict) else {}
        try:
            maximum = int(expected.get("max_pages"))
            planned = int(page_plan.get("planned_total_pages"))
        except (TypeError, ValueError):
            maximum = 0
            planned = -1
        covered = maximum > 0 and 0 <= planned <= maximum and bool(page_plan.get("verified"))
        return {
            "status": "COVERED_CONTROL_VERIFIED" if covered else "CONTROL_VERIFICATION_FAILED",
            "matched_chapters": [],
            "marker_found": False,
            "matched_terms": [],
            "response_evidence": [
                {
                    "control": "page_limit",
                    "planned_total_pages": planned if planned >= 0 else None,
                    "max_pages": maximum if maximum > 0 else None,
                    "verified": covered,
                }
            ],
            "blocking": bool(row.get("mandatory")) and not covered,
        }
    if control_kind == "format_policy":
        format_policy = (
            evidence.get("format_policy")
            if isinstance(evidence.get("format_policy"), dict)
            else {}
        )
        covered = bool(format_policy.get("verified"))
        return {
            "status": "COVERED_CONTROL_VERIFIED" if covered else "CONTROL_VERIFICATION_FAILED",
            "matched_chapters": [],
            "marker_found": False,
            "matched_terms": [],
            "response_evidence": [
                {
                    "control": "format_policy",
                    "source": _clean(format_policy.get("source")) or None,
                    "verified": covered,
                }
            ],
            "blocking": bool(row.get("mandatory")) and not covered,
        }
    requirement = _SPACE_RE.sub("", _clean(row.get("requirement"))).lower()
    match_terms = [
        term
        for term in (_clean(value) for value in (row.get("match_terms") or []))
        if term
    ]
    marker = f"【要求:{requirement_id}】"
    matched_chapters: List[str] = []
    matched_terms: List[str] = []
    marker_found = False
    evidence_locators: List[str] = []

    for title, section in sections_by_title.items():
        content = str(section.get("content") or "")
        compact = _SPACE_RE.sub("", content).lower()
        chapter_marker = marker in content
        chapter_terms = [
            term
            for term in match_terms
            if _SPACE_RE.sub("", term).lower() in compact
        ]
        exact_requirement = bool(requirement and requirement in compact)
        if chapter_marker or exact_requirement or chapter_terms:
            matched_chapters.append(title)
            matched_terms.extend(chapter_terms)
            marker_found = marker_found or chapter_marker
            evidence_locators.extend(
                value.strip()
                for value in re.findall(r"【证据:([^】]{1,260})】", content)
                if value.strip() and not value.strip().startswith("AUTO://")
            )

    matched_chapters = _dedupe(matched_chapters)
    matched_terms = _dedupe(matched_terms)
    evidence_locators = _dedupe(evidence_locators)
    # One substantive planned term is the established content-coverage policy
    # used by chapter requirements.  The marker alone never establishes
    # document-wide coverage.
    covered = bool(matched_terms) or any(
        requirement
        and requirement
        in _SPACE_RE.sub("", str(section.get("content") or "")).lower()
        for section in sections_by_title.values()
    )
    traceable = [
        value for value in evidence_locators if _TRACEABLE_LOCATOR_RE.search(value)
    ]
    planned_locators = _planned_traceable_locators(row)
    matched_planned_locators = [
        value for value in traceable if value in planned_locators
    ]

    if not covered:
        status = "MISSING_RESPONSE"
    elif row.get("evidence_required") and not evidence_locators:
        status = "COVERED_UNEVIDENCED"
    elif row.get("evidence_required") and not traceable:
        status = "COVERED_UNTRACEABLE"
    elif row.get("evidence_required") and not matched_planned_locators:
        status = "EVIDENCE_SOURCE_MISMATCH"
    else:
        status = "COVERED_TRACEABLE" if traceable else "COVERED"
    blocking = bool(row.get("mandatory")) and status not in {
        "COVERED",
        "COVERED_TRACEABLE",
    }
    return {
        "status": status,
        "matched_chapters": matched_chapters,
        "marker_found": marker_found,
        "matched_terms": matched_terms,
        "response_evidence": [
            {
                "sources": evidence_locators,
                "traceable": bool(traceable),
                "matched_planned_locators": matched_planned_locators,
            }
        ]
        if evidence_locators
        else [],
        "blocking": blocking,
    }


def finalize_requirement_evidence_matrix(
    *,
    plan: Dict[str, Any],
    sections: Sequence[Dict[str, Any]],
    evidence_tracking: Dict[str, Any],
    document_control_evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    sections_by_title = {
        _clean(section.get("title")): section
        for section in sections
        if isinstance(section, dict) and _clean(section.get("title"))
    }
    evidence_rows = [row for row in (evidence_tracking.get("rows") or []) if isinstance(row, dict)]
    chapter_gate_rows: Dict[tuple[str, str], Dict[str, Any]] = {}
    for title, section in sections_by_title.items():
        gate = validate_chapter_requirement_evidence(
            plan=plan,
            title=title,
            section=section,
        )
        for gate_row in gate.get("rows") or []:
            if not isinstance(gate_row, dict):
                continue
            chapter_gate_rows[(title, _clean(gate_row.get("requirement_id")))] = gate_row
    finalized: List[Dict[str, Any]] = []

    for planned in plan.get("rows") or []:
        if not isinstance(planned, dict):
            continue
        row = dict(planned)
        if _row_needs_review(row):
            row.update(
                {
                    "status": "NEEDS_REVIEW",
                    "matched_chapters": [],
                    "marker_found": False,
                    "matched_terms": [],
                    "response_evidence": [],
                    "blocking": False,
                }
            )
            finalized.append(row)
            continue
        mode = _clean(row.get("verification_mode")) or "content"
        targets = [_clean(value) for value in (row.get("target_chapters") or []) if _clean(value)]
        if mode == "document_control":
            row.update(
                _verify_document_control_requirement(
                    row=row,
                    sections_by_title=sections_by_title,
                    control_evidence=document_control_evidence,
                )
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
        per_chapter_gate = [
            chapter_gate_rows[(title, requirement_id)]
            for title in targets
            if (title, requirement_id) in chapter_gate_rows
        ]
        gate_status = next(
            (
                _clean(item.get("status"))
                for item in per_chapter_gate
                if _clean(item.get("status"))
                in {"COVERED_TRACEABLE", "COVERED"}
            ),
            _clean((per_chapter_gate[0] if per_chapter_gate else {}).get("status")),
        )
        if not covered:
            status = "MISSING_RESPONSE"
        elif gate_status in {
            "MISSING_REQUIREMENT_MARKER",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
            "EVIDENCE_SOURCE_MISMATCH",
        }:
            status = gate_status
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
            "MISSING_REQUIREMENT_MARKER",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
            "EVIDENCE_SOURCE_MISMATCH",
            "CONTROL_VERIFICATION_FAILED",
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
        if not row.get("blocking")
        and row.get("status")
        in {
            "MISSING_RESPONSE",
            "MISSING_REQUIREMENT_MARKER",
            "UNMAPPED",
            "COVERED_UNEVIDENCED",
            "COVERED_UNTRACEABLE",
            "EVIDENCE_SOURCE_MISMATCH",
            "NEEDS_REVIEW",
        }
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
