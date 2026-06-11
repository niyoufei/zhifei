from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from backend.zhifei_autoplan.local_adapter_contract import make_issue, mark_missing_param

FILE_LOCATOR_RE = re.compile(r"^[^#\s]+#p[\w.-]+_sha@[\w:.-]+$")
BOQ_LOCATOR_RE = re.compile(r"^boq:[^:\s]+(?:/.+)?$")
DRAWING_LOCATOR_RE = re.compile(r"^drawing#[^\s]+$")
USER_PARAM_RE = re.compile(r"^user_param:[^\s]+$")
INFERENCE_RE = re.compile(r"^inference:[^\s]+$")
QUALITY_RE = re.compile(r"^quality:[^\s]+$")
MISSING_RE = re.compile(r"^需补充（缺：(?P<name>.+)）$")


def _as_refs(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,，\n]+", value) if part.strip()]
    return [str(value).strip()]


def _extract_section_refs(sections: Iterable[Any]) -> List[str]:
    refs: List[str] = []
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        for key in ("evidence_refs", "evidence_sources", "source_refs"):
            refs.extend(_as_refs(section.get(key)))
        content = str(section.get("content") or "")
        refs.extend(match.group(0) for match in FILE_LOCATOR_RE.finditer(content))
        refs.extend(match.group(0) for match in MISSING_RE.finditer(content))
    return refs


def classify_evidence_ref(ref: Any) -> Dict[str, Any]:
    text = str(ref or "").strip()
    result = {
        "ref": text,
        "source_type": "unknown",
        "strength": "weak",
        "issue": None,
    }
    if not text:
        result["source_type"] = "missing_param"
        result["strength"] = "missing"
        result["issue"] = make_issue("EVIDENCE_REF_EMPTY", "evidence reference is empty", evidence_ref=text)
        return result
    if MISSING_RE.match(text):
        result["source_type"] = "missing_param"
        result["strength"] = "missing"
        result["issue"] = make_issue("MISSING_PARAM", text, evidence_ref=text)
        return result
    if "preview" in text.lower() or "预览" in text:
        result["source_type"] = "file"
        result["strength"] = "weak"
        return result
    if FILE_LOCATOR_RE.match(text):
        result["source_type"] = "file"
        result["strength"] = "strong"
    elif BOQ_LOCATOR_RE.match(text):
        result["source_type"] = "BOQ"
        result["strength"] = "strong"
    elif DRAWING_LOCATOR_RE.match(text):
        result["source_type"] = "drawing"
        result["strength"] = "strong"
    elif USER_PARAM_RE.match(text):
        result["source_type"] = "user_param"
        result["strength"] = "strong"
    elif INFERENCE_RE.match(text):
        result["source_type"] = "AI_inference"
        result["strength"] = "weak"
    elif QUALITY_RE.match(text):
        result["source_type"] = "quality"
        result["strength"] = "strong"
    else:
        result["issue"] = make_issue("EVIDENCE_REF_UNCLASSIFIED", "evidence reference is not classified", evidence_ref=text)
    return result


def build_evidence_summary(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    data = dict(envelope or {})
    refs = []
    refs.extend(_as_refs(data.get("evidence_refs")))
    refs.extend(_extract_section_refs(data.get("sections") or []))
    for missing in data.get("missing_params") or []:
        refs.append(mark_missing_param(missing))

    seen = set()
    classified: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    counts = {"strong": 0, "weak": 0, "missing": 0}
    by_type: Dict[str, int] = {}
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        item = classify_evidence_ref(ref)
        classified.append(item)
        counts[item["strength"]] = counts.get(item["strength"], 0) + 1
        by_type[item["source_type"]] = by_type.get(item["source_type"], 0) + 1
        if item.get("issue"):
            issues.append(item["issue"])

    return {
        "status": "ok" if not issues else "issues",
        "refs": classified,
        "counts": counts,
        "by_type": by_type,
        "issues": issues,
    }
