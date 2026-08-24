from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


LEGACY_GLOBAL_INSTRUCTION = "严格遵守最新16条行业规定；所有工序采用A/B/C/D/E结构表达。"

DEFAULT_GLOBAL_INSTRUCTION = (
    "生成内容必须服从现行有效的法律法规、工程建设强制性规范、招标文件及澄清答疑、"
    "审查合格的设计文件和工程量清单。所有规范必须具有可追溯的名称、编号、版本及来源；"
    "未核验的规范不得引用或编造。发生冲突时必须标记冲突并停止自行裁决。"
)

GLOBAL_COMPLIANCE_REQUIREMENT = DEFAULT_GLOBAL_INSTRUCTION

PROJECT_STANDARD_RECORD_FIELDS = (
    "standard_code_and_name",
    "current_effective_version",
    "effective_status_and_official_source",
    "applicable_specialties_and_chapters",
    "mandatory_clauses",
    "tender_evidence_locations",
    "conflicts_and_priority",
)

_ACTIVE_STATUSES = {
    "active",
    "current",
    "effective",
    "valid",
    "现行",
    "有效",
    "现行有效",
}
_STANDARD_CODE_RE = re.compile(
    r"(?<![A-Z0-9])(?:GB(?:/T)?|GBZ(?:/T)?|JGJ(?:/T)?|CJJ(?:/T)?|CECS|DB(?:J|\d+)?(?:/T)?|"
    r"DL(?:/T)?|SL(?:/T)?|JT(?:G|/T)?|NB(?:/T)?|HJ(?:/T)?|YY(?:/T)?|WS(?:/T)?)"
    r"\s*[-_/]?[A-Z0-9.]+(?:[-_/]\d{2,4})?(?![A-Z0-9])",
    re.IGNORECASE,
)


def should_migrate_global_instruction(value: Any) -> bool:
    text = str(value or "").strip()
    return not text or text == LEGACY_GLOBAL_INSTRUCTION or "最新16条行业规定" in text


def is_verified_standard_metadata(item: Dict[str, Any]) -> bool:
    code = str(item.get("standard_code") or "").strip()
    name = str(item.get("source_name") or item.get("standard_name") or "").strip()
    official_source = str(item.get("official_source") or "").strip()
    current_version = str(item.get("current_version") or "").strip()
    effective_status = str(item.get("effective_status") or "").strip().lower()
    return bool(
        code
        and name
        and official_source
        and current_version
        and effective_status in _ACTIVE_STATUSES
        and bool(item.get("latest", True))
    )


def _string_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    elif value is None:
        values = []
    else:
        values = [value]
    out: List[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def build_project_applicable_standards_manifest(sections: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the per-project standard register from verified chapter-level readback only."""
    records: Dict[str, Dict[str, Any]] = {}
    rejected: Dict[str, Dict[str, Any]] = {}
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        chapter = str(section.get("title") or "").strip()
        for hit in section.get("compliance_hits") or []:
            if not isinstance(hit, dict):
                continue
            code = str(hit.get("standard_code") or "").strip()
            if not code:
                continue
            verified = is_verified_standard_metadata(hit)
            target = records if verified else rejected
            rec = target.setdefault(
                code,
                {
                    "standard_code_and_name": {
                        "code": code,
                        "name": str(hit.get("source_name") or hit.get("standard_name") or "").strip(),
                    },
                    "current_effective_version": str(hit.get("current_version") or hit.get("code_year") or "").strip(),
                    "effective_status_and_official_source": {
                        "status": str(hit.get("effective_status") or "unverified").strip(),
                        "official_source": str(hit.get("official_source") or "").strip(),
                    },
                    "applicable_specialties_and_chapters": {
                        "specialties": _string_list(hit.get("domain_tags")),
                        "chapters": [],
                    },
                    "mandatory_clauses": [],
                    "tender_evidence_locations": [],
                    "conflicts_and_priority": {
                        "conflicts": _string_list(hit.get("conflicts")),
                        "priority": str(hit.get("priority") or "").strip(),
                    },
                    "verification_status": "verified" if verified else "unverified",
                    "eligible_for_citation": bool(verified),
                },
            )
            chapters = rec["applicable_specialties_and_chapters"]["chapters"]
            if chapter and chapter not in chapters:
                chapters.append(chapter)
            clause_no = str(hit.get("clause_no") or "").strip()
            if clause_no and clause_no not in rec["mandatory_clauses"]:
                rec["mandatory_clauses"].append(clause_no)
            for locator in _string_list(hit.get("tender_evidence_locations")):
                if locator not in rec["tender_evidence_locations"]:
                    rec["tender_evidence_locations"].append(locator)

    verified_records = list(records.values())
    rejected_records = list(rejected.values())
    return {
        "schema_version": 1,
        "fixed_count_required": False,
        "required_fields": list(PROJECT_STANDARD_RECORD_FIELDS),
        "verified_standards": verified_records,
        "unverified_candidates": rejected_records,
        "verified_count": len(verified_records),
        "unverified_count": len(rejected_records),
        "citation_policy": "verified_only",
    }


def extract_standard_codes(text: Any) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for match in _STANDARD_CODE_RE.findall(str(text or "")):
        code = re.sub(r"\s+", " ", str(match).strip().upper())
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def canonical_standard_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


# Backward-compatible private alias for callers/tests that imported the old name.
_canonical_standard_code = canonical_standard_code


def filter_evidence_to_verified_standard_codes(
    lines: Iterable[Any],
    verified_codes: Iterable[Any],
) -> Dict[str, Any]:
    """Remove evidence lines that cite a standard outside the verified project allowlist."""
    allowed = {canonical_standard_code(code) for code in verified_codes}
    allowed.discard("")
    kept: List[str] = []
    dropped: List[Dict[str, Any]] = []
    for raw in lines or []:
        line = str(raw or "").strip()
        if not line:
            continue
        codes = extract_standard_codes(line)
        invalid = [code for code in codes if canonical_standard_code(code) not in allowed]
        if invalid:
            dropped.append({"line": line, "standard_codes": invalid})
            continue
        kept.append(line)
    return {
        "lines": kept,
        "dropped": dropped,
        "dropped_count": len(dropped),
    }


def standard_citation_directive(verified_metadata: Iterable[Dict[str, Any]]) -> str:
    """Return an explicit writer constraint derived only from verified metadata."""
    labels: List[str] = []
    seen: set[str] = set()
    for row in verified_metadata or []:
        if not isinstance(row, dict) or not is_verified_standard_metadata(row):
            continue
        code = str(row.get("standard_code") or "").strip()
        canonical = canonical_standard_code(code)
        if not code or not canonical or canonical in seen:
            continue
        seen.add(canonical)
        name = str(row.get("source_name") or row.get("standard_name") or "").strip()
        labels.append(f"{code}《{name}》" if name else code)
    if not labels:
        return (
            "本章不得自行写入任何工程建设标准编号；需要表达合规要求时，只能写成"
            "“按项目适用且已核验的现行标准执行”，并保留证据定位。"
        )
    return (
        "本章只允许引用以下已核验项目适用规范编号："
        + "；".join(labels)
        + "。不得从模型记忆、案例库、通用知识图谱或未核验资料新增其他规范编号。"
    )


def replace_unverified_standard_citations(
    text: Any,
    verified_codes: Iterable[Any],
) -> Dict[str, Any]:
    """Fail-safe sanitization for model-invented or stale standard identifiers.

    The surrounding requirement is retained, but the unverified identifier is
    replaced by a neutral reference to the verified project register.  This is
    deliberately not a claim that the removed standard is applicable.
    """
    allowed = {canonical_standard_code(code) for code in verified_codes}
    allowed.discard("")
    source = str(text or "")
    removed: List[str] = []

    def _replace(match: re.Match[str]) -> str:
        code = re.sub(r"\s+", " ", str(match.group(0) or "").strip().upper())
        if canonical_standard_code(code) in allowed:
            return str(match.group(0))
        if code and code not in removed:
            removed.append(code)
        return "项目适用规范清单中的已核验现行标准"

    sanitized = _STANDARD_CODE_RE.sub(_replace, source)
    return {
        "text": sanitized,
        "removed_codes": removed,
        "changed": bool(removed),
    }


def audit_standard_citations(
    sections: Iterable[Dict[str, Any]],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    verified_codes = {
        canonical_standard_code((row.get("standard_code_and_name") or {}).get("code"))
        for row in (manifest.get("verified_standards") or [])
        if isinstance(row, dict)
    }
    verified_codes.discard("")
    violations: List[Dict[str, Any]] = []
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        for code in extract_standard_codes(section.get("content")):
            if canonical_standard_code(code) in verified_codes:
                continue
            violations.append(
                {
                    "chapter": title,
                    "standard_code": code,
                    "reason": "standard_not_in_verified_project_manifest",
                }
            )
    for row in (manifest.get("verified_standards") or []):
        if not isinstance(row, dict):
            continue
        conflicts = (row.get("conflicts_and_priority") or {}).get("conflicts") or []
        if not conflicts:
            continue
        code = str((row.get("standard_code_and_name") or {}).get("code") or "").strip()
        violations.append(
            {
                "chapter": "项目适用规范清单",
                "standard_code": code,
                "reason": "unresolved_standard_conflict",
                "conflicts": _string_list(conflicts),
            }
        )
    return {
        "ok": not violations,
        "verified_standard_count": len(verified_codes),
        "violation_count": len(violations),
        "violations": violations,
    }
