from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

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
_GENERAL_STANDARD_PREFIX = (
    r"(?:GB(?:[/_ ]T)?|GBZ(?:[/_ ]T)?|JGJ(?:[/_ ]T)?|"
    r"CJJ(?:[/_ ]T)?|CECS|DB(?:J|\d+)?(?:[/_ ]T)?|DL(?:[/_ ]T)?|"
    r"SL(?:[/_ ]T)?|JT(?:[/_ ]T)?|TB(?:[/_ ]T)?|NB(?:[/_ ]T)?|"
    r"HJ(?:[/_ ]T)?|YY(?:[/_ ]T)?|WS(?:[/_ ]T)?)"
)
_JTG_STANDARD_PREFIX = r"JTG(?:[/_ ]T)?"
_GENERAL_STANDARD_BODY = r"\d+(?:\.\d+)*(?:/\d+)?"
_JTG_STANDARD_BODY = r"(?:[A-Z]\d+|\d+)(?:\.\d+)*(?:/\d+)?"
_STANDARD_CODE_RE = re.compile(
    rf"(?<![A-Z0-9])(?:{_GENERAL_STANDARD_PREFIX}\s*[-_/ ]?\s*"
    rf"{_GENERAL_STANDARD_BODY}|{_JTG_STANDARD_PREFIX}\s*[-_/ ]?\s*"
    rf"{_JTG_STANDARD_BODY})\s*[-_]\s*\d{{4}}(?![-_/.]?[A-Z0-9])",
    re.IGNORECASE,
)
_VERSIONED_STANDARD_CODE_RE = re.compile(
    rf"^(?:{_GENERAL_STANDARD_PREFIX}\s*[-_/ ]?\s*{_GENERAL_STANDARD_BODY}|"
    rf"{_JTG_STANDARD_PREFIX}\s*[-_/ ]?\s*{_JTG_STANDARD_BODY})"
    rf"\s*[-_]\s*\d{{4}}$",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_OFFICIAL_URL_RE = re.compile(r"^https://[^\s]+$", re.IGNORECASE)


def should_migrate_global_instruction(value: Any) -> bool:
    text = str(value or "").strip()
    return not text or text == LEGACY_GLOBAL_INSTRUCTION or "最新16条行业规定" in text


def is_verified_standard_metadata(item: dict[str, Any]) -> bool:
    code = str(item.get("standard_code") or "").strip()
    name = str(item.get("source_name") or item.get("standard_name") or "").strip()
    official_source = str(item.get("official_source") or "").strip()
    current_version = str(item.get("current_version") or "").strip()
    effective_status = str(item.get("effective_status") or "").strip().lower()
    official_content_sha256 = str(
        item.get("official_content_sha256") or ""
    ).strip()
    official_document_url = str(
        item.get("official_document_url") or ""
    ).strip()
    pin_valid = not official_content_sha256 or bool(
        _SHA256_RE.fullmatch(official_content_sha256)
        and _OFFICIAL_URL_RE.fullmatch(official_document_url)
    )
    identity_without_cover = item.get("official_identity_without_cover") is True
    identity_policy_valid = not identity_without_cover or bool(
        _SHA256_RE.fullmatch(official_content_sha256)
        and _OFFICIAL_URL_RE.fullmatch(official_document_url)
    )
    return bool(
        is_versioned_standard_code(code)
        and name
        and official_source
        and is_versioned_standard_code(current_version)
        and canonical_standard_code(current_version)
        == canonical_standard_code(code)
        and effective_status in _ACTIVE_STATUSES
        and bool(item.get("latest", True))
        and pin_valid
        and identity_policy_valid
    )


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    elif value is None:
        values = []
    else:
        values = [value]
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def build_project_applicable_standards_manifest(sections: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build the per-project standard register from verified chapter-level readback only."""
    records: dict[str, dict[str, Any]] = {}
    rejected: dict[str, dict[str, Any]] = {}
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
            trusted_projection = bool(
                hit.get("verified") is True
                and hit.get("official_registry_verified") is True
                and (
                    hit.get("metadata_only") is True
                    or hit.get("clause_source_authoritative") is True
                )
            )
            verified = trusted_projection and is_verified_standard_metadata(hit)
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


def extract_standard_codes(text: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for match in _STANDARD_CODE_RE.findall(str(text or "")):
        code = re.sub(r"\s+", " ", str(match).strip().upper())
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def canonical_standard_code(value: Any) -> str:
    canonical = re.sub(
        r"[^A-Z0-9]+",
        "_",
        unicodedata.normalize("NFKC", str(value or "")).strip().upper(),
    ).strip("_")
    # OCR and official covers commonly omit the visual space between a known
    # standard-system prefix and its numeric body (``GB55037`` vs
    # ``GB 55037``).  Normalize only that boundary; the strict validator still
    # rejects alphabetic or otherwise malformed numeric bodies.
    prefix = (
        r"(?:GB(?:_T)?|GBZ(?:_T)?|JGJ(?:_T)?|CJJ(?:_T)?|CECS|"
        r"DB(?:J|\d+)?(?:_T)?|DL(?:_T)?|SL(?:_T)?|JTG(?:_T)?|"
        r"JT(?:_T)?|TB(?:_T)?|NB(?:_T)?|HJ(?:_T)?|YY(?:_T)?|WS(?:_T)?)"
    )
    canonical = re.sub(rf"^({prefix})(?=\d)", r"\1_", canonical)
    return re.sub(r"^(JTG(?:_T)?)(?=[A-Z]\d)", r"\1_", canonical)


def is_versioned_standard_code(value: Any) -> bool:
    """Return whether a standard identity has a numeric body and 4-digit year."""

    normalized = re.sub(r"\s+", " ", str(value or "").strip().upper())
    return bool(normalized and _VERSIONED_STANDARD_CODE_RE.fullmatch(normalized))


def _registry_identity_name(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)


def _registry_rows_conflict(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    left_name = _registry_identity_name(
        left.get("source_name") or left.get("standard_name")
    )
    right_name = _registry_identity_name(
        right.get("source_name") or right.get("standard_name")
    )
    if not left_name or not right_name or left_name != right_name:
        return True
    if canonical_standard_code(left.get("current_version")) != canonical_standard_code(
        right.get("current_version")
    ):
        return True
    for field in ("official_content_sha256", "official_document_url"):
        left_value = str(left.get(field) or "").strip().lower()
        right_value = str(right.get(field) or "").strip().lower()
        if left_value and right_value and left_value != right_value:
            return True
    return bool(left.get("official_identity_without_cover")) != bool(
        right.get("official_identity_without_cover")
    )


def build_standard_registry_map(
    rows: Iterable[Any],
) -> dict[str, dict[str, Any]]:
    """Deduplicate registry rows without concealing provenance conflicts."""

    registry: dict[str, dict[str, Any]] = {}
    for raw in rows or []:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        canonical = canonical_standard_code(row.get("standard_code"))
        if not canonical:
            continue
        row["_registry_unverified"] = not is_verified_standard_metadata(row)
        current = registry.get(canonical)
        if current is None:
            registry[canonical] = row
            continue
        if current.get("_registry_ambiguous") is True:
            continue
        if _registry_rows_conflict(current, row):
            registry[canonical] = {
                "standard_code": row.get("standard_code"),
                "_registry_ambiguous": True,
                "_registry_unverified": True,
            }
            continue
        current_verified = not bool(current.get("_registry_unverified"))
        row_verified = not bool(row.get("_registry_unverified"))
        prefer_row = bool(
            (row_verified and not current_verified)
            or (
                row_verified == current_verified
                and bool(current.get("metadata_only"))
                and not bool(row.get("metadata_only"))
            )
            or (
                row_verified == current_verified
                and not str(current.get("official_content_sha256") or "").strip()
                and bool(str(row.get("official_content_sha256") or "").strip())
            )
        )
        if prefer_row:
            registry[canonical] = row
    return registry


# Backward-compatible private alias for callers/tests that imported the old name.
_canonical_standard_code = canonical_standard_code


def filter_evidence_to_verified_standard_codes(
    lines: Iterable[Any],
    verified_codes: Iterable[Any],
) -> dict[str, Any]:
    """Remove evidence lines that cite a standard outside the verified project allowlist."""
    allowed = {canonical_standard_code(code) for code in verified_codes}
    allowed.discard("")
    kept: list[str] = []
    dropped: list[dict[str, Any]] = []
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


def standard_citation_directive(verified_metadata: Iterable[dict[str, Any]]) -> str:
    """Return an explicit writer constraint derived only from verified metadata."""
    labels: list[str] = []
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
) -> dict[str, Any]:
    """Fail-safe sanitization for model-invented or stale standard identifiers.

    The surrounding requirement is retained, but the unverified identifier is
    replaced by a neutral reference to the verified project register.  This is
    deliberately not a claim that the removed standard is applicable.
    """
    allowed = {canonical_standard_code(code) for code in verified_codes}
    allowed.discard("")
    source = str(text or "")
    removed: list[str] = []

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
    sections: Iterable[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    verified_codes = {
        canonical_standard_code((row.get("standard_code_and_name") or {}).get("code"))
        for row in (manifest.get("verified_standards") or [])
        if isinstance(row, dict)
    }
    verified_codes.discard("")
    violations: list[dict[str, Any]] = []
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
        "verified_standard_codes": sorted(verified_codes),
        "violation_count": len(violations),
        "violations": violations,
    }
