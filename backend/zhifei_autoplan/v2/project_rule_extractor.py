from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "质量": ["质量", "验收", "强度", "偏差", "抽检", "样板"],
    "安全": ["安全", "隐患", "危大", "应急", "临电", "防护"],
    "进度": ["进度", "工期", "里程碑", "节点", "关键线路", "计划"],
    "环保": ["环保", "扬尘", "噪声", "PM10", "污水", "绿色施工"],
    "重难点": ["重难点", "关键工序", "复杂", "高风险", "界面", "穿插"],
    "扣分点": ["扣分", "废标", "否决", "处罚", "失分", "一票否决"],
}

SOURCE_PRIORITY = {"答疑文件": 5, "招标文件": 4, "合同文件": 3, "其他": 1}

THRESHOLD_RE = re.compile(
    r"(?P<subject>[\u4e00-\u9fffA-Za-z0-9_()/%-]{2,60}?)"
    r"(?P<cmp>不低于|不少于|不小于|不应低于|不应小于|不得高于|不应超过|不高于|至少|应达到|应控制在)"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|‰|dB|MPa|kPa|mm|cm|m|km|天|h|小时|min|分钟|次/日|次/班|次|人|台|套|m3|m²|m2|t|kg|ug/m3|μg/m3)?",
    flags=re.IGNORECASE,
)
DEADLINE_RE = re.compile(r"(?:在|于)?(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>小时|h|天|分钟|min)内")
PROHIBITION_RE = re.compile(r"(不得|禁止|严禁)(?P<target>[^。；;\n]{2,80})")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip().lower())


def _source_type(path: Path) -> str:
    name = path.name
    lower = name.lower()
    if any(k in name for k in ("答疑", "澄清", "补遗")) or "clarification" in lower:
        return "答疑文件"
    if any(k in name for k in ("合同",)) or "contract" in lower:
        return "合同文件"
    if any(k in name for k in ("招标",)) or "tender" in lower:
        return "招标文件"
    return "其他"


def _read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".json", ".xml", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    try:
        from modules.parser.parser_unify import UnifiedParser

        parsed = UnifiedParser(str(path)).parse()
        text = str(parsed.get("text") or "").strip()
        if text:
            return text
        return json.dumps(parsed.get("meta") or {}, ensure_ascii=False)
    except Exception:
        return ""


def _iter_sentences(text: str) -> Iterable[str]:
    for seg in re.split(r"[。；;\n]+", text or ""):
        s = str(seg).strip()
        if len(s) >= 4:
            yield s


def _detect_dimension(text: str) -> str:
    best = "质量"
    best_score = -1
    for dim, keywords in DIMENSION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text.lower())
        if score > best_score:
            best = dim
            best_score = score
    return best


def _make_rule_id(source_path: str, sentence: str, idx: int) -> str:
    seed = f"{source_path}|{idx}|{sentence}"
    return "PR-" + hashlib.md5(seed.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()


def _extract_from_sentence(sentence: str, *, source_path: str, source_type: str, idx: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    dim = _detect_dimension(sentence)
    priority = int(SOURCE_PRIORITY.get(source_type, 1))

    for m in THRESHOLD_RE.finditer(sentence):
        out.append(
            {
                "rule_id": _make_rule_id(source_path, sentence, idx),
                "dimension": dim,
                "rule_type": "threshold",
                "subject": str(m.group("subject") or "").strip(),
                "comparator": str(m.group("cmp") or "").strip(),
                "value": float(m.group("value")),
                "unit": str(m.group("unit") or "").strip(),
                "raw_sentence": sentence,
                "source_path": source_path,
                "source_type": source_type,
                "priority": priority,
            }
        )

    for m in DEADLINE_RE.finditer(sentence):
        out.append(
            {
                "rule_id": _make_rule_id(source_path, sentence, idx),
                "dimension": dim,
                "rule_type": "deadline",
                "subject": "响应时限",
                "comparator": "within",
                "value": float(m.group("value")),
                "unit": str(m.group("unit") or "").strip(),
                "raw_sentence": sentence,
                "source_path": source_path,
                "source_type": source_type,
                "priority": priority,
            }
        )

    for m in PROHIBITION_RE.finditer(sentence):
        out.append(
            {
                "rule_id": _make_rule_id(source_path, sentence, idx),
                "dimension": dim,
                "rule_type": "prohibition",
                "subject": str(m.group("target") or "").strip(),
                "comparator": "forbidden",
                "value": None,
                "unit": "",
                "raw_sentence": sentence,
                "source_path": source_path,
                "source_type": source_type,
                "priority": priority,
            }
        )
    return out


def build_project_rule_matrix(tender_paths: List[str]) -> Dict[str, Any]:
    rules: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    source_files: List[str] = []
    for raw in tender_paths:
        p = Path(raw).expanduser().resolve()
        if not p.exists() or not p.is_file():
            errors.append({"path": str(p), "error": "file_not_found"})
            continue
        source_files.append(str(p))
        text = _read_text(p)
        if not text:
            errors.append({"path": str(p), "error": "empty_text"})
            continue
        stype = _source_type(p)
        for idx, sentence in enumerate(_iter_sentences(text), start=1):
            rules.extend(_extract_from_sentence(sentence, source_path=str(p), source_type=stype, idx=idx))

    uniq: List[Dict[str, Any]] = []
    seen = set()
    for rule in rules:
        key = (
            str(rule.get("dimension") or ""),
            str(rule.get("rule_type") or ""),
            _normalize_text(str(rule.get("subject") or "")),
            str(rule.get("comparator") or ""),
            str(rule.get("value") or ""),
            str(rule.get("unit") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(rule)
    rules = uniq

    by_dimension: Dict[str, List[Dict[str, Any]]] = {}
    for rule in rules:
        dim = str(rule.get("dimension") or "质量")
        by_dimension.setdefault(dim, []).append(rule)

    overrides: Dict[str, Dict[str, Any]] = {}
    for dim, dim_rules in by_dimension.items():
        sorted_rules = sorted(
            dim_rules,
            key=lambda x: (int(x.get("priority") or 0), 1 if x.get("rule_type") == "threshold" else 0),
            reverse=True,
        )
        if sorted_rules:
            overrides[dim] = sorted_rules[0]

    return {
        "ok": True,
        "source_files": source_files,
        "errors": errors,
        "rules_total": len(rules),
        "rules": rules,
        "by_dimension": by_dimension,
        "dimension_overrides": overrides,
        "source_priority_rule": "答疑文件 > 招标文件 > 合同文件 > 其他",
    }

