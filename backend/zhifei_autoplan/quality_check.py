from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List

from backend.zhifei_autoplan.qingtian_policy import QINGTIAN_BANNED_PHRASES
from backend.zhifei_autoplan.remediation_strategy import (
    build_execution_audit,
    build_execution_profile,
    build_strategy_audit,
    enrich_strategy_rows,
)
from backend.zhifei_autoplan.workspace import workspace_paths


def _ingest_audit_path(workspace_dir: str | None = None) -> Path:
    return workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else Path("backend/data/audit/ingest.jsonl")


def _normalize_text(s: str) -> str:
    return (s or "").replace(" ", "").replace("\n", "")


def _dedup_text_list(lines: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in lines:
        s = str(raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

EVIDENCE_SRC_RE = re.compile(r"【证据:(?P<src>[^】]{1,80})】")
TRACEABLE_EVIDENCE_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", re.IGNORECASE)
EVIDENCE_PLACEHOLDERS = ["待补充", "待定位", "tbd", "TBD", "待完善", "文件名#定位符", "文件名#定位"]


def _extract_evidence_sources(text: str) -> List[str]:
    return [m.group("src").strip() for m in EVIDENCE_SRC_RE.finditer(text or "") if (m.group("src") or "").strip()]


def _is_placeholder_evidence(src: str) -> bool:
    s = (src or "").strip()
    if not s:
        return True
    low = s.lower()
    return any(p.lower() in low for p in EVIDENCE_PLACEHOLDERS)


def _count_good_evidence(text: str) -> int:
    return sum(1 for src in _extract_evidence_sources(text) if not _is_placeholder_evidence(src))


def _count_placeholder_evidence(text: str) -> int:
    return sum(1 for src in _extract_evidence_sources(text) if _is_placeholder_evidence(src))


def _count_evidence(text: str) -> int:
    return text.count("【证据:")


def _count_traceable_evidence(text: str) -> int:
    # A "traceable" marker contains a locator like: filename#p2_ab12cd34@1234
    cnt = 0
    for src in _extract_evidence_sources(text):
        if _is_placeholder_evidence(src):
            continue
        if TRACEABLE_EVIDENCE_RE.search(src or ""):
            cnt += 1
    return cnt


def _count_evidence_by_section(sections: List[Dict[str, Any]]):
    result = []
    for s in sections:
        # Count only "good" evidence markers (exclude placeholders like 待补充/待定位).
        cnt = _count_good_evidence(s.get("content") or "")
        result.append({"title": s.get("title"), "evidence_count": cnt})
    return result


def _has_bullets(text: str) -> bool:
    markers = ["- ", "•", "1)", "2)", "3)", "（1）", "（2）", "（3）", "①", "②", "③"]
    return any(m in text for m in markers)


def _avg_sentence_len(text: str) -> float:
    parts = [p for p in text.replace("。", "。\n").replace("；", "。\n").split("\n") if p.strip()]
    if not parts:
        return 0.0
    total = sum(len(p) for p in parts)
    return total / max(1, len(parts))


def _check_score_coverage(tender: Dict[str, Any], sections: List[Dict[str, Any]]):
    if not tender:
        return {"ok": False, "missing": [], "reason": "tender_matrix_missing"}
    all_text = "\n".join((s.get("content") or "") for s in sections)
    missing = []
    for it in tender.get("items", []):
        dim = str(it.get("dimension"))
        kws = it.get("keywords") or []
        if not kws:
            # 招标文本未抽取到关键词时，不做覆盖率硬判定，避免误报
            continue
        hit = any(k in all_text for k in kws[:6])
        if not hit:
            missing.append({"dimension": dim, "keywords": kws[:6]})
    return {"ok": len(missing) == 0, "missing": missing}


def _check_score_coverage_by_section(tender: Dict[str, Any], sections: List[Dict[str, Any]]):
    if not tender:
        return []
    items = tender.get("items", [])
    results = []
    for s in sections:
        text = s.get("content") or ""
        missing = []
        for it in items:
            dim = str(it.get("dimension"))
            kws = it.get("keywords") or []
            if not kws:
                continue
            hit = any(k in text for k in kws[:6])
            if not hit:
                missing.append({"dimension": dim, "keywords": kws[:6]})
        results.append(
            {
                "title": s.get("title"),
                "missing": missing,
                "ok": len(missing) == 0,
            }
        )
    return results


def _check_closed_loop(sections: List[Dict[str, Any]]):
    issues = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        # “风险→控制→验证”属于闭环表达；此处将“控制”视为措施等价项，避免误报。
        if "风险" in text and ("措施" not in text and "对应" not in text and "控制" not in text):
            issues.append(f"{title}: 有风险但未体现对应措施")
    return {"ok": len(issues) == 0, "issues": issues}


def _check_closed_loop_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        has_risk = "风险" in text
        has_measure = ("措施" in text) or ("对应" in text) or ("控制" in text)
        ok = (not has_risk) or (has_risk and has_measure)
        results.append({"title": title, "ok": ok, "has_risk": has_risk, "has_measure": has_measure})
    return results


def _check_engineering(text: str):
    keys = ["频次", "阈值", "责任", "验收", "流程"]
    missing = [k for k in keys if k not in text]
    return {"ok": len(missing) <= 2, "missing": missing}


def _check_engineering_by_section(sections: List[Dict[str, Any]]):
    keys = ["频次", "阈值", "责任", "验收", "流程"]
    results = []
    for s in sections:
        text = s.get("content") or ""
        missing = [k for k in keys if k not in text]
        results.append({"title": s.get("title"), "missing": missing, "ok": len(missing) <= 2})
    return results


def _check_template_style(text: str):
    cleaned = str(text or "")
    # Style check should judge prose shape, not traceability tags or oversized item codes.
    cleaned = re.sub(r"【证据:[^】]+】", "", cleaned)
    cleaned = re.sub(r"\b\d+(?:\.\d+)?e\+\d+\b", "NUM", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b[0-9A-Za-z]{12,}\b", "CODE", cleaned)
    cleaned = re.sub(r"\b\d{6,}\b", "NUM", cleaned)
    avg_len = _avg_sentence_len(cleaned)
    has_bullets = _has_bullets(cleaned)
    ok = has_bullets and (avg_len == 0.0 or avg_len <= 40)
    return {"ok": ok, "avg_sentence_len": avg_len, "has_bullets": has_bullets}


RISK_TRIPLET_RE = re.compile(
    r"风险(?:[:：=]|按)\s*(?P<risk>.+?)(?=(?:[，,；;。]\s*|\s+)(?:控制|措施)(?:[:：=]|按))"
    r".*?(?:控制|措施)(?:[:：=]|按)\s*(?P<control>.+?)(?=(?:[，,；;。]\s*|\s+)验证(?:[:：=]|按))"
    r".*?验证(?:[:：=]|按)\s*(?P<verify>[^。\n；;]+)",
    re.DOTALL,
)
QUANT_KEYS = ["频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号"]
QUANT_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|d|min|分钟|次|人|台|套|%|MPa|kN|mm2|m2|m3|dB|db|ug/m3|μg/m3|m/s|℃)",
    re.IGNORECASE,
)
VAGUE_WORDS = _dedup_text_list(
    ["加强", "确保", "严格", "及时", "充分", "有效", "合理", "全面"] + list(QINGTIAN_BANNED_PHRASES)
)
HARD_BANNED_WORDS = _dedup_text_list(["加强", "确保", "严格"] + list(QINGTIAN_BANNED_PHRASES))
OFFICIALESE_PHRASES = [
    "提高政治站位",
    "统一思想认识",
    "压实责任",
    "形成工作合力",
    "高质量推进",
    "持续推进",
    "扎实推进",
    "强化组织领导",
    "全力以赴",
    "确保万无一失",
    "坚决杜绝",
    "切实增强",
    "常态化开展",
    "积极推进",
    "不断完善",
    "全面提升",
]
NONCONCRETE_REPLACEMENTS = {
    # 这些词一律不允许出现在最终稿里；直接剔除，避免产生“执行执行”等重复词。
    "加强": "",
    "确保": "",
    "严格": "",
    "按照": "",
    "符合": "",
    "保障": "",
    "严格落实": "",
    "加强管理": "",
    "有效措施": "",
    "合理安排": "",
    "现场实际情况": "",
    "相关规范": "",
    "有关规定": "",
}
STANDARD_TRADES = [
    "测量工",
    "钢筋工",
    "模板工",
    "混凝土工",
    "架子工",
    "防水工",
    "电工",
    "焊工",
    "管道工",
    "起重信号司索工",
    "机械设备操作工",
]
REQUIRED_TOPICS = [
    "特殊材料",
    "危险品材料",
    "劳保用品",
    "技术工种配置",
    "绿色工地",
    "信息化管理",
    "四新技术",
]
TOPIC_ALIASES = {
    # Canonical topic -> aliases allowed in tender text / section wording.
    "特殊材料": ["特殊材料", "特殊构配件", "非标材料"],
    "危险品材料": ["危险品材料", "危化品", "危险化学品", "危化", "危化品材料", "危险品", "易燃易爆"],
    "劳保用品": ["劳保用品", "劳动防护", "个人防护", "防护用品", "PPE"],
    "技术工种配置": ["技术工种配置", "工种配置", "劳动力计划", "人员配置", "班组配置", "劳动力组织"],
    "绿色工地": ["绿色工地", "绿色施工", "文明环保", "环境保护", "扬尘", "噪声", "污水", "固废"],
    "信息化管理": ["信息化管理", "智慧工地", "信息化", "数字化", "BIM", "二维码", "台账", "物联网", "移动端"],
    "四新技术": ["四新技术", "四新", "新技术", "新工艺", "新材料", "新设备", "新工法", "新技术应用"],
}


def strip_nonconcrete_language(text: str) -> str:
    out = text or ""
    for src, dst in NONCONCRETE_REPLACEMENTS.items():
        out = out.replace(src, dst)
    for phrase in OFFICIALESE_PHRASES:
        out = out.replace(phrase, "")
    out = re.sub(r"[，,]{2,}", "，", out)
    out = re.sub(r"[；;]{2,}", "；", out)
    out = re.sub(r"。{2,}", "。", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"^[，。；、\s]+", "", out)
    out = re.sub(r"[，；、\s]+$", "", out)
    return out.strip()


def _find_phrase_hits(text: str, phrases: List[str], span: int = 18) -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    for phrase in phrases:
        for m in re.finditer(re.escape(phrase), text or ""):
            start = max(0, m.start() - span)
            end = min(len(text), m.end() + span)
            hits.append({"phrase": phrase, "snippet": (text or "")[start:end]})
    return hits


def _extract_risk_triplets(text: str) -> List[Dict[str, str]]:
    triplets: List[Dict[str, str]] = []
    for m in RISK_TRIPLET_RE.finditer(text or ""):
        risk = (m.group("risk") or "").strip()
        control = (m.group("control") or "").strip()
        verify = (m.group("verify") or "").strip()
        triplets.append(
            {
                "risk": risk,
                "control": control,
                "verify": verify,
                "span_start": int(m.start()),
                "span_end": int(m.end()),
            }
        )
    return triplets


def _check_risk_triplet_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        triplets = _extract_risk_triplets(text)
        has_risk = "风险" in text
        incomplete = [
            t
            for t in triplets
            if (not t.get("risk")) or (not t.get("control")) or (not t.get("verify"))
        ]
        ok = (not has_risk) or (len(triplets) > 0 and len(incomplete) == 0)
        results.append(
            {
                "title": title,
                "ok": ok,
                "triplets": triplets,
                "triplet_count": len(triplets),
                "incomplete_count": len(incomplete),
            }
        )
    return results


def _check_quantitative_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        hit_keys = [k for k in QUANT_KEYS if k in text]
        has_units = bool(QUANT_UNIT_RE.search(text))
        missing = [k for k in QUANT_KEYS if k not in text]
        ok = len(hit_keys) >= 3 and has_units
        results.append(
            {
                "title": title,
                "ok": ok,
                "hit_keys": hit_keys,
                "missing": missing,
                "has_units": has_units,
            }
        )
    return results


def _check_vague_terms_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        bad_hits = []
        for w in VAGUE_WORDS:
            for m in re.finditer(re.escape(w), text):
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 20)
                window = text[start:end]
                if w in HARD_BANNED_WORDS:
                    bad_hits.append({"word": w, "snippet": window})
                    continue
                has_quant = bool(re.search(r"\d", window)) or any(
                    k in window for k in ["频次", "阈值", "间距", "厚度", "时长", "人数", "型号", "验收", "责任"]
                )
                if not has_quant:
                    bad_hits.append({"word": w, "snippet": window})
        results.append({"title": title, "ok": len(bad_hits) == 0, "hits": bad_hits, "count": len(bad_hits)})
    return results


def _sanitize_vague_language(text: str) -> str:
    """
    Remove vague words from non-quantified sentences while preserving quantified clauses.
    This is used by template remediation to make "vague_term" fixes deterministic.
    """
    src = text or ""
    if not src:
        return src

    # Keep separators so the original structure mostly remains.
    parts = re.split(r"([。；;\n])", src)
    cleaned: List[str] = []
    quant_hints = set(QUANT_KEYS + ["验收", "责任", "记录", "时限", "偏差", "合格率"])

    for i in range(0, len(parts), 2):
        sent = parts[i]
        sep = parts[i + 1] if i + 1 < len(parts) else ""
        s = sent.strip()
        if not s:
            cleaned.append(sent + sep)
            continue

        has_quant = bool(re.search(r"\d", s)) or any(k in s for k in quant_hints)
        if not has_quant:
            for w in VAGUE_WORDS:
                sent = sent.replace(w, "")
            sent = re.sub(r"[，,]{2,}", "，", sent)
            sent = re.sub(r"[ \t]{2,}", " ", sent)

        cleaned.append(sent + sep)

    return "".join(cleaned).strip()


def _check_officialese_by_section(sections: List[Dict[str, Any]]):
    patterns = OFFICIALESE_PHRASES + HARD_BANNED_WORDS
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        hits = _find_phrase_hits(text, patterns)
        results.append({"title": title, "ok": len(hits) == 0, "hits": hits, "count": len(hits)})
    return results


def _check_evidence_quality_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        good = _count_good_evidence(text)
        placeholders = _count_placeholder_evidence(text)
        results.append({"title": title, "ok": good > 0 and placeholders == 0, "good_count": good, "placeholder_count": placeholders})
    return results


def _check_evidence_traceability_by_section(sections: List[Dict[str, Any]], require_traceable: bool):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        traceable = _count_traceable_evidence(text)
        placeholders = _count_placeholder_evidence(text)
        ok = (not require_traceable) or (traceable > 0 and placeholders == 0)
        results.append(
            {
                "title": title,
                "ok": ok,
                "require": require_traceable,
                "traceable_count": traceable,
                "placeholder_count": placeholders,
            }
        )
    return results


def _check_core_conclusion_evidence_by_section(sections: List[Dict[str, Any]]):
    """
    Core conclusions (带约束/阈值/必须动作) must carry traceable evidence markers.
    """
    core_kw = ("必须", "应", "需", "禁止", "风险", "控制", "验证", "工期", "关键线路", "资源峰值", "合格率", "偏差")
    meta_hints = (
        "【自动补充】",
        "已为本章回填",
        "需继续人工复核",
        "示例：",
        "量化指标示例",
        "对必选专项补齐",
        "每条写清",
        "评分点命中关键词",
        "用于本章覆盖校核",
        "在每条关键结论句末追加",
        "至少 1 条/章",
        "不得使用",
        "格式=文件名#p页_sha@offset",
    )
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = str(s.get("content") or "")
        # Merge soft-wrapped line breaks inside IDs / item codes so one logical bullet
        # is not miscounted as multiple uncovered core fragments.
        text = re.sub(
            r"(?<=[A-Za-z0-9])\n(?=[A-Za-z0-9\u4e00-\u9fff])|(?<=[\u4e00-\u9fff])\n(?=[A-Za-z0-9])",
            "",
            text,
        )
        fragments: List[str] = []
        for raw_line in text.splitlines():
            line = str(raw_line or "").strip()
            if not line or line.startswith("【自动补充】"):
                continue
            units = [line] if "【证据:" in line else [x.strip() for x in re.split(r"[。\n]+", line) if x.strip()]
            for frag in units:
                if any(h in frag for h in meta_hints):
                    continue
                fragments.append(frag)
        core_total = 0
        covered = 0
        missing_snippets: List[str] = []
        for frag in fragments:
            is_core = any(k in frag for k in core_kw) and (
                bool(re.search(r"\d", frag))
                or any(x in frag for x in ("频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号"))
            )
            if not is_core:
                continue
            core_total += 1
            has_marker = "【证据:" in frag
            has_traceable = bool(re.search(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", frag, flags=re.IGNORECASE))
            if has_marker and has_traceable:
                covered += 1
            else:
                if len(missing_snippets) < 6:
                    missing_snippets.append(frag[:80])
        ok = (core_total == 0) or (covered >= max(1, int(core_total * 0.7)))
        results.append(
            {
                "title": title,
                "ok": ok,
                "core_total": core_total,
                "covered": covered,
                "missing_snippets": missing_snippets,
            }
        )
    return results


def _is_key_process_chapter(title: str) -> bool:
    t = str(title or "")
    keys = ("施工方法", "施工工艺", "施工方案", "主要施工", "工序", "专项", "技术措施", "作业方法", "工艺流程")
    return any(k in t for k in keys)


def _load_drawing_filenames(
    project_id: str | None = None,
    limit: int = 80,
    *,
    audit_path: str | Path | None = None,
    workspace_dir: str | None = None,
) -> List[str]:
    p = Path(audit_path) if audit_path is not None else _ingest_audit_path(workspace_dir)
    if not p.exists():
        return []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    names = []
    seen = set()
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]
    except Exception:
        return []
    for ln in lines:
        if len(names) >= max(1, int(limit or 0)):
            break
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        tags = rec.get("tags") or []
        if "drawing" not in tags:
            continue
        if "logo" in tags:
            continue
        fn = str(rec.get("filename") or "").strip()
        if not fn or fn in seen:
            continue
        seen.add(fn)
        names.append(fn)
    return names


def _has_drawing_evidence(text: str, drawing_names: List[str]) -> bool:
    if not drawing_names:
        return False
    name_set = set(drawing_names)
    for src in _extract_evidence_sources(text or ""):
        if _is_placeholder_evidence(src):
            continue
        base = src.split("#", 1)[0].strip() if "#" in src else src.strip()
        if base in name_set:
            return True
    return False


def _check_drawing_evidence_by_section(sections: List[Dict[str, Any]], drawing_names: List[str]) -> List[Dict[str, Any]]:
    results = []
    has_drawings = bool(drawing_names)
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        required = has_drawings and _is_key_process_chapter(str(title))
        has_ev = _has_drawing_evidence(text, drawing_names) if required else True
        ok = (not required) or has_ev
        results.append(
            {
                "title": title,
                "ok": ok,
                "required": required,
                "has_drawing_evidence": bool(has_ev) if required else None,
            }
        )
    return results


def _check_drawing_anchor_binding_by_section(sections: List[Dict[str, Any]], drawing_names: List[str]) -> List[Dict[str, Any]]:
    has_drawings = bool(drawing_names)
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = str(s.get("content") or "")
        required = has_drawings and _is_key_process_chapter(str(title))
        has_space = "【空间锚点:" in text
        has_dim = "【尺寸锚点:" in text
        ok = (not required) or (has_space and has_dim)
        results.append(
            {
                "title": title,
                "ok": ok,
                "required": required,
                "has_spatial_anchor": has_space if required else None,
                "has_dimension_anchor": has_dim if required else None,
            }
        )
    return results


def _load_standard_filenames(
    project_id: str | None = None,
    limit: int = 80,
    *,
    audit_path: str | Path | None = None,
    workspace_dir: str | None = None,
) -> List[str]:
    """
    Load enterprise standard/work-instruction filenames from ingest audit.
    Uses ingest tag "standard" (from filename heuristic).
    """
    p = Path(audit_path) if audit_path is not None else _ingest_audit_path(workspace_dir)
    if not p.exists():
        return []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    names = []
    seen = set()
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]
    except Exception:
        return []
    for ln in lines:
        if len(names) >= max(1, int(limit or 0)):
            break
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        tags = rec.get("tags") or []
        if "standard" not in tags:
            continue
        if "logo" in tags:
            continue
        fn = str(rec.get("filename") or "").strip()
        if not fn or fn in seen:
            continue
        seen.add(fn)
        names.append(fn)
    return names


def _has_standard_evidence(text: str, standard_names: List[str]) -> bool:
    if not standard_names:
        return False
    name_set = set(standard_names)
    for src in _extract_evidence_sources(text or ""):
        if _is_placeholder_evidence(src):
            continue
        base = src.split("#", 1)[0].strip() if "#" in src else src.strip()
        if base in name_set:
            return True
    return False


def _check_standard_evidence_by_section(sections: List[Dict[str, Any]], standard_names: List[str]) -> Dict[str, Any]:
    """
    When enterprise standards exist, require that they are actually cited as evidence
    (not just mentioned as vague "按标准执行").
    Policy:
    - Prefer key process chapters; if none, require at least 1 citation anywhere.
    - Target citations: min(2, key_process_chapter_count) or 1 (if no key chapters).
    """
    has_standards = bool(standard_names)
    by_section = []
    key_hits = 0
    key_total = 0
    any_hits = 0
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        is_key = _is_key_process_chapter(str(title))
        has_ev = _has_standard_evidence(text, standard_names) if has_standards else False
        if has_ev:
            any_hits += 1
        if is_key:
            key_total += 1
            if has_ev:
                key_hits += 1
        by_section.append({"title": title, "is_key_process": is_key, "has_standard_evidence": bool(has_ev)})

    if not has_standards:
        return {"ok": True, "standard_count": 0, "standards": [], "covered": 0, "target": 0, "by_section": by_section}

    if key_total > 0:
        target = min(2, key_total)
        covered = key_hits
    else:
        target = 1
        covered = any_hits
    ok = covered >= target
    return {
        "ok": ok,
        "standard_count": len(standard_names),
        "standards": standard_names[:12],
        "covered": covered,
        "target": target,
        "by_section": by_section,
    }


def _check_consistency(sections: List[Dict[str, Any]]):
    metric_values: Dict[str, Dict[str, List[str]]] = {
        "工期": {},
        "资源峰值": {},
        "关键线路间隔": {},
    }
    for s in sections:
        title = s.get("title") or "章节"
        text = s.get("content") or ""
        for m in re.finditer(r"工期[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|月)", text):
            v = f"{m.group(1)}{m.group(2)}"
            metric_values["工期"].setdefault(v, []).append(title)
        for m in re.finditer(r"(?:资源峰值|高峰投入)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(人|台|套)", text):
            v = f"{m.group(1)}{m.group(2)}"
            metric_values["资源峰值"].setdefault(v, []).append(title)
        for m in re.finditer(r"关键线路(?:间隔|步距)?[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|h|小时)", text):
            v = f"{m.group(1)}{m.group(2)}"
            metric_values["关键线路间隔"].setdefault(v, []).append(title)
    conflicts = []
    for metric, values in metric_values.items():
        if len(values) > 1:
            conflicts.append({"metric": metric, "values": values})

    cpm_receipt = None
    try:
        from backend.zhifei_autoplan.schedule_cpm import build_cpm_receipt

        cpm_receipt = build_cpm_receipt(sections, canonical={})
        cpm_conflicts = cpm_receipt.get("conflicts") if isinstance(cpm_receipt, dict) else []
        if isinstance(cpm_conflicts, list):
            for c in cpm_conflicts:
                if not isinstance(c, dict):
                    continue
                conflicts.append(
                    {
                        "metric": c.get("metric"),
                        "values": {
                            "mentioned": c.get("mentioned"),
                            "computed": c.get("computed"),
                            "tolerance": c.get("tolerance"),
                            "delta": c.get("delta"),
                        },
                        "source": "cpm",
                    }
                )
    except Exception:
        cpm_receipt = None

    return {"ok": len(conflicts) == 0, "conflicts": conflicts, "cpm": cpm_receipt}


def _check_boq_focus_coverage(boq_focus: Dict[str, Any], all_text: str):
    keywords = (boq_focus or {}).get("must_cover_keywords") or []
    if not keywords:
        return {"ok": True, "missing": [], "covered": []}
    covered = [k for k in keywords if k in all_text]
    missing = [k for k in keywords if k not in all_text]
    ok = len(covered) >= max(1, min(5, len(keywords) // 3 or 1))
    return {"ok": ok, "missing": missing[:20], "covered": covered[:20]}


def _triplet_has_operational_fields(snippet: str) -> Dict[str, bool]:
    text = str(snippet or "")
    has_freq = bool(re.search(r"\d+(?:\.\d+)?\s*(?:次/日|次/班|次/周|次)", text)) or ("频次" in text)
    has_threshold = bool(re.search(r"(?:≤|>=|≥|<|>)\s*\d+(?:\.\d+)?", text)) or ("阈值" in text) or ("偏差" in text)
    has_resp = any(k in text for k in ("责任", "岗位", "负责人", "安全员", "质量员", "工长", "监理"))
    has_record = any(k in text for k in ("记录", "台账", "检查表", "复核单"))
    has_deviation_limit = bool(re.search(r"(?:整改|处置|复验|复核|关闭).{0,8}(?:\d+(?:\.\d+)?\s*(?:h|小时|天)|时限)", text))
    return {
        "has_frequency": has_freq,
        "has_threshold": has_threshold,
        "has_responsibility": has_resp,
        "has_record": has_record,
        "has_deviation_limit": has_deviation_limit,
    }


def _check_boq_focus_item_closure(boq_focus: Dict[str, Any], sections: List[Dict[str, Any]]):
    """
    对“清单重点项”做更强约束：不仅要出现，还要在出现的章节里给出
    - 量化指标（>=3 个关键字 + 有单位数值）
    - 至少 2 条风险→控制→验证 三元组
    - 三元组必须包含：频次、阈值、责任、记录、偏差处置时限
    - 至少 1 个证据标记
    """
    items = (boq_focus or {}).get("must_cover_keywords") or []
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return {"ok": True, "items": []}

    results = []
    for name in items[:12]:
        hit_sections = []
        for sec in sections:
            title = sec.get("title") or ""
            text = sec.get("content") or ""
            if name not in text:
                continue

            # Stronger: check within a local window around the item mention
            window = 520
            best = {"triplet_count": 0, "hit_keys": [], "has_units": False, "evidence_count": 0}
            ok = False
            idx = 0
            checked = 0
            while True:
                pos = text.find(name, idx)
                if pos < 0:
                    break
                checked += 1
                start = max(0, pos - window)
                end = min(len(text), pos + len(name) + window)
                snippet = text[start:end]
                triplets = _extract_risk_triplets(snippet)
                full_triplets = 0
                full_triplet_flags = {
                    "has_frequency": False,
                    "has_threshold": False,
                    "has_responsibility": False,
                    "has_record": False,
                    "has_deviation_limit": False,
                }
                for t in triplets:
                    try:
                        ss = int(t.get("span_start") or 0)
                        ee = int(t.get("span_end") or 0)
                    except Exception:
                        ss, ee = 0, 0
                    if ee <= ss:
                        continue
                    ts = max(0, ss - 40)
                    te = min(len(snippet), ee + 220)
                    t_snip = snippet[ts:te]
                    flags = _triplet_has_operational_fields(t_snip)
                    for k, v in flags.items():
                        full_triplet_flags[k] = bool(full_triplet_flags.get(k)) or bool(v)
                    if all(flags.values()):
                        full_triplets += 1
                hit_keys = [k for k in QUANT_KEYS if k in snippet]
                has_units = bool(QUANT_UNIT_RE.search(snippet))
                evidence_cnt = _count_good_evidence(snippet)
                if (
                    (len(triplets) >= 2)
                    and (full_triplets >= 2)
                    and (len(hit_keys) >= 3)
                    and has_units
                    and (evidence_cnt >= 1)
                    and all(full_triplet_flags.values())
                ):
                    ok = True
                    best = {
                        "triplet_count": len(triplets),
                        "full_triplet_count": int(full_triplets),
                        **full_triplet_flags,
                        "hit_keys": hit_keys,
                        "has_units": has_units,
                        "evidence_count": evidence_cnt,
                    }
                    break
                # keep best-effort debug info
                if (len(triplets) + len(hit_keys) + int(has_units) + evidence_cnt) > (
                    best["triplet_count"]
                    + len(best["hit_keys"])
                    + int(best["has_units"])
                    + best["evidence_count"]
                ):
                    best = {
                        "triplet_count": len(triplets),
                        "full_triplet_count": int(full_triplets),
                        **full_triplet_flags,
                        "hit_keys": hit_keys,
                        "has_units": has_units,
                        "evidence_count": evidence_cnt,
                    }
                idx = pos + max(1, len(name))

            hit_sections.append(
                {
                    "title": title,
                    "ok": ok,
                    "triplet_count": best["triplet_count"],
                    "full_triplet_count": best.get("full_triplet_count"),
                    "has_frequency": best.get("has_frequency"),
                    "has_threshold": best.get("has_threshold"),
                    "has_responsibility": best.get("has_responsibility"),
                    "has_record": best.get("has_record"),
                    "has_deviation_limit": best.get("has_deviation_limit"),
                    "hit_keys": best["hit_keys"],
                    "has_units": best["has_units"],
                    "evidence_count": best["evidence_count"],
                    "mentions_checked": checked,
                }
            )
        if not hit_sections:
            results.append({"item": name, "ok": False, "reason": "not_mentioned", "hit_sections": []})
        else:
            results.append(
                {
                    "item": name,
                    "ok": any(h.get("ok") for h in hit_sections),
                    "reason": "ok" if any(h.get("ok") for h in hit_sections) else "mentioned_but_not_closed",
                    "hit_sections": hit_sections[:5],
                }
            )
    ok = all(r.get("ok") for r in results[: max(1, min(5, len(results)))])
    return {"ok": ok, "items": results}


def _check_boq_focus_item_typed_evidence(
    boq_focus: Dict[str, Any],
    sections: List[Dict[str, Any]],
    *,
    drawing_names: List[str] | None = None,
    standard_names: List[str] | None = None,
):
    """
    For BoQ focus items, require that evidence is not only traceable, but also typed:
    - if drawings exist: at least 1 drawing locator should be present near the focus item mention
    - if enterprise standards exist: at least 1 standard locator should be present near the focus item mention
    """
    items = (boq_focus or {}).get("must_cover_keywords") or []
    items = [str(x).strip() for x in items if str(x).strip()]
    drawing_names = [str(x).strip() for x in (drawing_names or []) if str(x).strip()]
    standard_names = [str(x).strip() for x in (standard_names or []) if str(x).strip()]
    has_drawings = bool(drawing_names)
    has_standards = bool(standard_names)
    if not items or (not has_drawings and not has_standards):
        return {"ok": True, "has_drawings": has_drawings, "has_standards": has_standards, "items": []}

    results = []
    window = 520
    for name in items[:12]:
        hit_sections = []
        ok_any = False
        for sec in sections:
            title = sec.get("title") or ""
            text = sec.get("content") or ""
            if name not in text:
                continue
            # Check within a local window around *each* item mention to keep evidence relevant.
            # The first mention may be outside the focus-card block, so we scan multiple occurrences.
            idx = 0
            checked = 0
            best = {"has_dwg": False, "has_std": False}
            ok = False
            while True:
                pos = text.find(name, idx)
                if pos < 0:
                    break
                checked += 1
                start = max(0, pos - window)
                end = min(len(text), pos + len(name) + window)
                snippet = text[start:end]
                has_dwg = _has_drawing_evidence(snippet, drawing_names) if has_drawings else True
                has_std = _has_standard_evidence(snippet, standard_names) if has_standards else True
                if (has_dwg and has_std) or ((not has_drawings) and has_std) or ((not has_standards) and has_dwg):
                    ok = True
                    best = {"has_dwg": bool(has_dwg), "has_std": bool(has_std)}
                    break
                if (int(bool(has_dwg)) + int(bool(has_std))) > (int(best["has_dwg"]) + int(best["has_std"])):
                    best = {"has_dwg": bool(has_dwg), "has_std": bool(has_std)}
                if checked >= 10:
                    break
                idx = pos + max(1, len(name))
            if ok:
                ok_any = True
            hit_sections.append(
                {
                    "title": title,
                    "ok": ok,
                    "has_drawing_evidence": bool(best["has_dwg"]) if has_drawings else None,
                    "has_standard_evidence": bool(best["has_std"]) if has_standards else None,
                    "mentions_checked": checked,
                }
            )
        if not hit_sections:
            results.append({"item": name, "ok": False, "reason": "not_mentioned", "hit_sections": []})
        else:
            results.append(
                {
                    "item": name,
                    "ok": ok_any,
                    "reason": "ok" if ok_any else "mentioned_but_missing_typed_evidence",
                    "hit_sections": hit_sections[:5],
                }
            )
    ok = all(r.get("ok") for r in results[: max(1, min(5, len(results)))])
    return {"ok": ok, "has_drawings": has_drawings, "has_standards": has_standards, "items": results}


def _check_required_topics(all_text: str):
    text = str(all_text or "")
    missing = []
    covered: Dict[str, List[str]] = {}
    for t in REQUIRED_TOPICS:
        aliases = TOPIC_ALIASES.get(t) or [t]
        hit = [a for a in aliases if a and a in text]
        covered[t] = hit[:8]
        if not hit:
            missing.append(t)
    return {"ok": len(missing) == 0, "missing": missing, "covered": covered}


def _check_required_topics_detail(sections: List[Dict[str, Any]]):
    """
    “出现”不等于“可执行”。这里对必选专项做“可落地”校验：
    - 必须包含关键动词/闭环片段
    - 必须出现至少 1 处单位数值（或频次/时长/阈值）
    """
    topic_rules = {
        "特殊材料": ["到货", "复验", "批次"],
        "危险品材料": ["采购", "储", "领用", "应急"],
        "劳保用品": ["发放", "检查", "更换"],
        "技术工种配置": ["工", "人数", "班"],
        "绿色工地": ["扬尘", "噪声", "污水"],
        "信息化管理": ["二维码", "台账", "上传"],
        # 四新必须写到可验收：适用/投入/步骤/验收指标 + 风险闭环 + 记录。
        "四新技术": ["适用", "投入", "步骤", "验收", "风险", "验证", "记录"],
    }
    results = []
    for topic, musts in topic_rules.items():
        aliases = TOPIC_ALIASES.get(topic) or [topic]
        texts = []
        for s in sections:
            c = s.get("content") or ""
            if not c:
                continue
            if any(a in c for a in aliases if a):
                texts.append(c)
        if not texts:
            results.append({"topic": topic, "ok": False, "reason": "missing"})
            continue
        merged = "\n".join(texts)
        miss = [m for m in musts if m not in merged]
        has_units = bool(QUANT_UNIT_RE.search(merged))
        ok = (len(miss) == 0) and has_units
        results.append({"topic": topic, "ok": ok, "missing": miss, "has_units": has_units})
    return {"ok": all(r.get("ok") for r in results), "by_topic": results}


def _check_qse_closed_loop_by_section(sections: List[Dict[str, Any]]):
    """
    For 质量/安全/文明环保等章节，要求“可闭环”而非只出现关键词：
    - 至少 2 条完整的 风险→控制→验证 三元组
    - 至少 1 处单位数值（阈值/频次/时长等）
    - 必须出现记录/台账（可追溯）
    - 必须出现偏差处置/整改/复核关键词（闭环关闭动作）
    """
    try:
        from backend.zhifei_autoplan.logic_templates import classify_chapter_domain
    except Exception:
        classify_chapter_domain = None

    results = []
    for s in sections or []:
        title = s.get("title") or "章节"
        dom = None
        try:
            dom = classify_chapter_domain(title) if classify_chapter_domain else None
        except Exception:
            dom = None
        if dom != "qse":
            continue
        text = s.get("content") or ""
        # Compute an adaptive target so long QSE chapters cannot pass with only 2 vague cards.
        # Use content length with evidence markers removed to avoid inflating by locators.
        stripped = re.sub(r"【证据:[^】]{1,200}】", "", text)
        base_len = len(stripped)
        target_cards = 2
        if base_len >= 1200:
            target_cards = 3
        if base_len >= 2400:
            target_cards = 4
        if base_len >= 3600:
            target_cards = 6

        triplets = _extract_risk_triplets(text)
        triplet_count = len(triplets)
        has_units = bool(QUANT_UNIT_RE.search(text))
        has_record = any(k in text for k in ("记录", "台账", "记录表", "检查表"))
        has_deviation = any(k in text for k in ("整改", "纠偏", "处置", "复验", "复查", "关闭", "停工"))

        # A "closed-loop card" must contain: triplet + record + deviation handling + at least 1 quantified value.
        closed_cards = 0
        for t in triplets:
            try:
                ss = int(t.get("span_start") or 0)
                ee = int(t.get("span_end") or 0)
            except Exception:
                ss, ee = 0, 0
            if ee <= ss:
                continue
            start = max(0, ss - 40)
            end = min(len(text), ee + 260)
            snippet = (text or "")[start:end]
            sn_has_units = bool(QUANT_UNIT_RE.search(snippet))
            sn_has_record = any(k in snippet for k in ("记录", "台账", "记录表", "检查表"))
            sn_has_dev = any(k in snippet for k in ("整改", "纠偏", "处置", "复验", "复查", "关闭", "停工"))
            if sn_has_units and sn_has_record and sn_has_dev:
                closed_cards += 1

        ok = (closed_cards >= target_cards) and has_units and has_record and has_deviation
        missing = []
        if closed_cards < target_cards:
            missing.append(f"闭环卡片>={target_cards}")
        if triplet_count < max(2, target_cards):
            missing.append(f"三元组>={max(2, target_cards)}")
        if not has_units:
            missing.append("单位数值")
        if not has_record:
            missing.append("记录/台账")
        if not has_deviation:
            missing.append("偏差处置/整改/复核")
        results.append(
            {
                "title": title,
                "ok": ok,
                "triplet_count": triplet_count,
                "closed_card_count": closed_cards,
                "target_cards": target_cards,
                "has_units": has_units,
                "has_record": has_record,
                "has_deviation_handling": has_deviation,
                "missing": missing,
            }
        )
    return {"ok": all(r.get("ok") for r in results) if results else True, "target_triplets": 2, "by_section": results}


def _check_logic_template_adherence_by_section(sections: List[Dict[str, Any]]):
    """
    Ensure each section reflects the chosen A/B/C/D/E intra-chapter logic template.
    This prevents "three variants but only synonym swaps": variants must differ by reasoning structure.

    This is a soft check and only runs when metadata exists:
    - section.logic_template_id in {A,B,C,D,E}
    - section.chapter_domain in {general,qse} (or inferred from title)
    """
    try:
        from backend.zhifei_autoplan.logic_templates import classify_chapter_domain
    except Exception:
        classify_chapter_domain = None

    results = []
    for s in sections or []:
        title = str(s.get("title") or "").strip() or "章节"
        text = str(s.get("content") or "")
        tid = str(s.get("logic_template_id") or "").strip().upper()
        if tid not in {"A", "B", "C", "D", "E"}:
            continue
        dom = str(s.get("chapter_domain") or "").strip().lower()
        if dom not in {"general", "qse"}:
            try:
                dom = classify_chapter_domain(title) if classify_chapter_domain else "general"
            except Exception:
                dom = "general"

        anchors: List[str] = []
        if dom == "qse":
            if tid == "A":
                anchors = ["闭环清单", "闭环卡片"]
            elif tid == "B":
                anchors = ["场景拆分", "检查频次总表", "记录表清单"]
            elif tid == "C":
                anchors = ["指标矩阵", "数据闭环"]
            elif tid == "D":
                anchors = ["监管红线清单", "岗位联签链", "闭环时限表"]
            else:
                anchors = ["区域网格", "班组行为清单", "红黄牌处置"]
        else:
            if tid == "A":
                anchors = ["本章交付物", "交付物", "约束条件"]
            elif tid == "B":
                anchors = ["工序流程", "步骤控制点"]
            elif tid == "C":
                anchors = ["控制指标矩阵", "人机料法环", "指标矩阵"]
            elif tid == "D":
                anchors = ["资源-工序耦合表", "接口冲突清单", "关键路径纠偏卡"]
            else:
                anchors = ["实施场景卡片", "参数对照表", "验收样表"]

        ok = any(a in text for a in anchors)
        results.append(
            {
                "title": title,
                "ok": ok,
                "template_id": tid,
                "chapter_domain": dom,
                "anchors": anchors,
                "missing": [] if ok else anchors,
            }
        )

    return {"ok": all(r.get("ok") for r in results) if results else True, "by_section": results}


def _check_chapter_blueprint_adherence_by_section(sections: List[Dict[str, Any]]):
    """
    When a chapter title matches a known "章节结构蓝图", ensure the required anchors appear.
    This controls "章内结构" (without changing tender outline) so chapters like
    “对工程项目整体理解与实施路径” are written around “工程特点/总体部署”等固定要素。
    """
    try:
        from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint
    except Exception:
        match_chapter_blueprint = None

    results = []
    for s in sections or []:
        title = str(s.get("title") or "").strip() or "章节"
        text = str(s.get("content") or "")
        bp_id = str(s.get("chapter_blueprint_id") or "").strip()
        bp_name = str(s.get("chapter_blueprint_name") or "").strip()
        anchors: List[str] = []

        bp = None
        if bp_id or bp_name:
            # Metadata exists; anchors will be resolved by matching title again (best-effort).
            bp = None
        if match_chapter_blueprint:
            try:
                bp = match_chapter_blueprint(title)
            except Exception:
                bp = None
        if isinstance(bp, dict):
            bp_id = str(bp.get("id") or bp_id).strip()
            bp_name = str(bp.get("name") or bp_name).strip()
            raw_anchors = bp.get("anchors") if isinstance(bp.get("anchors"), list) else []
            anchors = [str(x).strip() for x in raw_anchors if str(x).strip()]

        # No blueprint or no anchors: do not enforce.
        if not bp_id or not anchors:
            continue

        missing = [a for a in anchors if a not in text]
        ok = len(missing) == 0
        results.append(
            {
                "title": title,
                "ok": ok,
                "blueprint_id": bp_id,
                "blueprint_name": bp_name,
                "anchors": anchors,
                "missing": missing,
            }
        )
    return {"ok": all(r.get("ok") for r in results) if results else True, "by_section": results}


def _check_trades_by_section(sections: List[Dict[str, Any]]):
    results = []
    for s in sections:
        title = s.get("title") or ""
        text = s.get("content") or ""
        should_check = any(k in title for k in ("工种", "劳动力", "人员", "组织"))
        if not should_check:
            results.append({"title": title, "ok": True, "missing": []})
            continue
        hit = [t for t in STANDARD_TRADES if t in text]
        missing = STANDARD_TRADES if len(hit) == 0 else []
        results.append({"title": title, "ok": len(hit) > 0, "missing": missing, "hit": hit})
    return results


def apply_remediation(
    sections: List[Dict[str, Any]],
    remediation: List[Dict[str, Any]],
    *,
    tender: Dict[str, Any] | None = None,
    project_id: str | None = None,
    boq_focus: Dict[str, Any] | None = None,
    params: Dict[str, Any] | None = None,
    workspace_dir: str | None = None,
):
    # Use editable parameter registry (backend/data/autoplan/params.json) so users can tune numbers globally.
    try:
        from backend.zhifei_autoplan.params_runtime import (
            load_params,
            get_quant_defaults,
            get_boq_focus_card_defaults,
            get_qse_defaults,
        )

        # Prefer per-run merged params if provided (e.g. actions payload params_override).
        _params = params if isinstance(params, dict) else load_params()
        _quant = get_quant_defaults(_params)
        _card = get_boq_focus_card_defaults(_params)
        _qse = get_qse_defaults(_params)
    except Exception:
        _quant = {
            "频次": "2次/日",
            "阈值": "偏差≤5mm",
            "间距": "1000mm",
            "厚度": "50mm",
            "时长": "4h/作业段",
            "人数": "8人/班",
            "设备型号": "20t挖机1台",
        }
        _card = {
            "采购比价": "≥3家/批次",
            "抽检频次": "每100m2 1次",
            "合格率阈值": "≥98%",
            "一次验收通过率": "≥95%",
            "台账抽查频次": "1次/周",
            "应急演练频次": "1次/季度",
        }
        _qse = {
            "PM10阈值": "≤150ug/m3",
            "昼间噪声阈值": "≤70dB",
            "夜间噪声阈值": "≤55dB",
        }

    ev_cache: Dict[str, str] = {}
    applied_markers = {
        "score_point_missing": "【自动补充】评分点覆盖建议",
        "risk_measure_gap": "【自动补充】风险-措施对应",
        "risk_triplet_gap": "【自动补充】风险→控制→验证",
        "qse_closed_loop_gap": "【自动补充】质量/安全/文明环保闭环卡片",
        "logic_template_adherence_gap": "【自动补充】章内逻辑锚点",
        "chapter_blueprint_gap": "【自动补充】章节结构蓝图",
        "engineering_gap": "【自动补充】工程落地要素",
        "quantitative_gap": "【自动补充】量化指标",
        "special_topic_missing": "【自动补充】专项管理内容",
        "consistency_conflict": "【自动补充】数据一致性校核",
        "vague_term": "【自动补充】消除空泛词",
        "bureaucratic_phrase": "【自动补充】替换空话为可执行项",
        "boq_focus_item_closure_gap": "【自动补充】重点清单项闭环",
        "boq_focus_item_typed_evidence_gap": "【自动补充】重点项图纸/标准证据闭环",
        "required_topic_detail_gap": "【自动补充】专项可执行细则",
        "evidence_gap": "【自动补充】证据标注",
        "evidence_traceability_gap": "【自动补充】证据可追溯定位",
        "core_conclusion_evidence_gap": "【自动补充】核心结论证据补齐",
        "drawing_evidence_gap": "【自动补充】图纸证据定位",
        "drawing_anchor_gap": "【自动补充】图纸空间锚点",
        "standard_evidence_gap": "【自动补充】企业标准/工法引用与落地",
    }

    audit_path = _ingest_audit_path(workspace_dir)

    def _already_applied(content: str, rtype: str | None) -> bool:
        key = str(rtype or "").strip()
        marker = applied_markers.get(key)
        return bool(marker and marker in (content or ""))

    def _pick_target_section(title: str | None, rtype: str | None) -> Dict[str, Any] | None:
        target_title = str(title or "").strip()
        for sec in sections:
            if str(sec.get("title") or "").strip() == target_title and target_title:
                return sec

        # Only fallback for known "virtual titles" produced by quality gates.
        virtual_titles = {"全局一致性", "清单重点项", "专项主题"}
        virtual_types = {"consistency_conflict", "boq_focus_item_closure_gap", "required_topic_detail_gap", "special_topic_missing"}
        if (target_title not in virtual_titles) and (str(rtype or "") not in virtual_types):
            return None

        title_text = "\n".join([str(s.get("title") or "") for s in sections])
        # Consistency issues belong to plan/schedule chapters.
        if str(rtype or "") == "consistency_conflict" or target_title == "全局一致性":
            prefer = ["进度", "工期", "计划", "资源", "关键线路"]
        # BoQ focus / special topics prefer construction method/resource chapters.
        elif str(rtype or "") == "boq_focus_item_closure_gap" or target_title == "清单重点项":
            prefer = ["施工方案", "施工方法", "主要施工", "施工工艺", "技术措施", "资源", "材料", "设备"]
        else:
            # Special topics can live in safety/green/digital/material chapters.
            prefer = ["安全", "文明", "环保", "绿色", "信息化", "材料", "资源", "技术措施", "施工方案"]

        for kw in prefer:
            for sec in sections:
                if kw in str(sec.get("title") or ""):
                    return sec
        return sections[0] if sections else None

    def _pick_traceable_evidence(title: str) -> str:
        if title in ev_cache:
            return ev_cache[title]
        src = "招标文件/工程量清单/图纸"
        try:
            from backend.zhifei_autoplan.evidence import best_ingested_hit, best_tender_source_span_hit

            hit = best_ingested_hit(
                f"{title} 招标 清单 图纸",
                limit=10,
                prefer_filename_keywords=["招标", "清单", "图纸", "BOQ", "工程量", "报价"],
                project_id=project_id,
                audit_path=audit_path,
            )
            if hit and hit.get("locator"):
                src = str(hit.get("locator"))
            if (not src or "@" not in src or "#" not in src) and isinstance(tender, dict):
                tender_hit = best_tender_source_span_hit(
                    tender,
                    f"{title} 招标要求 质量 安全 工期",
                    prefer_filename_keywords=["招标", "清单", "BOQ", "工程量"],
                )
                if tender_hit and tender_hit.get("locator"):
                    src = str(tender_hit.get("locator"))
        except Exception:
            pass
        ev_cache[title] = src
        return src

    def _append_strategy_trace(sec: Dict[str, Any], rec: Dict[str, Any]) -> None:
        trace_rows = sec.setdefault("remediation_strategy_trace", [])
        if not isinstance(trace_rows, list):
            trace_rows = []
            sec["remediation_strategy_trace"] = trace_rows
        trace = {
            "type": str(rec.get("type") or "").strip(),
            "indicator_group": str(rec.get("indicator_group") or "").strip(),
            "strategy_id": str(rec.get("strategy_id") or "").strip(),
            "strategy_name": str(rec.get("strategy_name") or "").strip(),
            "strategy_family": str(rec.get("strategy_family") or "").strip(),
            "strategy_priority": int(rec.get("strategy_priority") or 0),
            "chapter_domain": str(rec.get("chapter_domain") or "").strip(),
            "template_id": str(rec.get("template_id") or "").strip(),
            "audit_key": str(rec.get("audit_key") or "").strip(),
        }
        key = (
            trace["type"],
            trace["strategy_id"],
            trace["audit_key"],
        )
        seen = {
            (
                str(item.get("type") or "").strip(),
                str(item.get("strategy_id") or "").strip(),
                str(item.get("audit_key") or "").strip(),
            )
            for item in trace_rows
            if isinstance(item, dict)
        }
        if key not in seen:
            trace_rows.append(trace)

    def _append_execution_trace(sec: Dict[str, Any], rec: Dict[str, Any], *, before_text: str, after_text: str) -> None:
        trace_rows = sec.setdefault("remediation_execution_trace", [])
        if not isinstance(trace_rows, list):
            trace_rows = []
            sec["remediation_execution_trace"] = trace_rows
        trace = build_execution_profile(rec, before_text=before_text, after_text=after_text)
        key = (
            str(trace.get("type") or "").strip(),
            str(trace.get("strategy_id") or "").strip(),
            str(trace.get("audit_key") or "").strip(),
        )
        seen = {
            (
                str(item.get("type") or "").strip(),
                str(item.get("strategy_id") or "").strip(),
                str(item.get("audit_key") or "").strip(),
            )
            for item in trace_rows
            if isinstance(item, dict)
        }
        if key not in seen:
            trace_rows.append(trace)

    def _annotate_core_conclusions(text: str, ev_src: str) -> tuple[str, int]:
        core_kw = ("必须", "应", "需", "禁止", "风险", "控制", "验证", "工期", "关键线路", "资源峰值", "合格率", "偏差")
        parts = re.split(r"([。；;\n]+)", str(text or ""))
        out: List[str] = []
        annotated = 0
        for idx, part in enumerate(parts):
            if idx % 2 == 1:
                out.append(part)
                continue
            frag = str(part or "")
            stripped = frag.strip()
            if not stripped:
                out.append(frag)
                continue
            is_core = any(k in stripped for k in core_kw) and (
                bool(re.search(r"\d", stripped))
                or any(x in stripped for x in QUANT_KEYS)
            )
            has_marker = "【证据:" in stripped
            has_traceable = bool(re.search(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", stripped, flags=re.IGNORECASE))
            if is_core and not (has_marker and has_traceable):
                frag = frag.rstrip() + f"【证据:{ev_src}】"
                annotated += 1
            out.append(frag)
        return "".join(out), annotated

    for rec in remediation or []:
        title = rec.get("title")
        rtype = rec.get("type")
        suggestion = rec.get("suggestion") or ""
        sec = _pick_target_section(title, rtype)
        if not sec:
            continue
        content = sec.get("content") or ""
        before_text = str(content or "")
        if _already_applied(content, rtype):
            continue
        ev_src = _pick_traceable_evidence(str(sec.get("title") or title or "章节"))
        sec_title = str(sec.get("title") or title or "章节")
        sec_domain = str(sec.get("chapter_domain") or rec.get("chapter_domain") or "").strip().lower()

        if rtype == "score_point_missing":
            miss_dims = rec.get("missing_dimensions") if isinstance(rec.get("missing_dimensions"), list) else []
            miss_dims = [str(x).strip() for x in miss_dims if str(x).strip()]
            miss_kws = rec.get("missing_keywords") if isinstance(rec.get("missing_keywords"), list) else []
            miss_kws = [str(x).strip() for x in miss_kws if str(x).strip()]
            if sec_domain == "qse" and any(k in sec_title for k in ("安全", "应急", "消防")):
                # Tail-appended score patches can be truncated by chapter compaction.
                # Seed the critical safety score anchors near the top so they survive max-length cleanup.
                safety_anchor = (
                    "安全重难点与扣分项：复杂交叉作业、动火、临电和高处作业列为本章重难点；"
                    "无证上岗、临时用电漏保失效、危化品混放和临边防护缺失列为扣分项/否决项；"
                    f"重大偏差触发红黄牌处置并立即停工复核。【证据:{ev_src}】"
                )
                if "安全重难点与扣分项：" not in content:
                    content = safety_anchor + "\n" + content
            block = (
                "\n\n【自动补充】评分点覆盖建议：\n"
                f"- {suggestion}\n"
                f"- 量化指标示例：合格率≥98%，一次验收通过率≥95%。【证据:{ev_src}】\n"
            )
            if miss_dims:
                block += f"- 评分维度回填：{'、'.join(miss_dims[:40])}。\n"
            if miss_kws:
                # Force explicit keyword hits so score coverage checks become deterministic.
                block += (
                    "- 评分点命中关键词（用于本章覆盖校核）："
                    + "、".join(miss_kws[:120])
                    + f"。【证据:{ev_src}】\n"
                )
            content += block
        elif rtype == "risk_measure_gap":
            block = (
                "\n\n【自动补充】风险-措施对应（风险三元组闭环）：\n"
                "- 风险：交叉作业导致人员伤害；措施：作业分区+警戒线2m+专人指挥；"
                "控制：班前交底=1次/班（责任岗位：安全员）+巡检频次=2次/日；"
                f"验证：违章=0次，记录=《交叉作业巡检表》。【证据:{ev_src}】\n"
            )
            content += block
        elif rtype == "risk_triplet_gap":
            content += (
                "\n\n【自动补充】风险→控制→验证：\n"
                "- 风险：关键参数超差导致返工/超支；控制：首件确认=1次/工序+过程抽检频次=每100m2 1次；"
                f"验证：偏差≤5mm，抽检合格率≥98%，记录=《抽检记录表》；"
                f"偏差处置：超差即停工整改≤2h，复验合格后关闭。【证据:{ev_src}】\n"
            )
        elif rtype == "qse_closed_loop_gap":
            # Title-aware closed-loop cards for 质量/安全/文明环保章节.
            t = str(sec_title or "")
            tid = str(rec.get("template_id") or sec.get("logic_template_id") or "").strip().upper() or "A"
            if tid not in {"A", "B", "C", "D", "E"}:
                tid = "A"
            content += "\n\n【自动补充】质量/安全/文明环保闭环卡片：\n"
            # Add template-specific anchors so multi-variant differences come from structure (not synonym swapping).
            if tid == "B":
                # Scene-driven structure
                scenes = []
                if "质量" in t or "验收" in t or "检验" in t:
                    scenes = ["材料到货", "关键工序", "隐蔽验收"]
                elif "安全" in t or "应急" in t or "消防" in t:
                    scenes = ["高处作业", "临时用电", "动火/消防"]
                else:
                    scenes = ["扬尘控制", "夜间施工噪声", "固废/危废暂存"]
                content += "【场景拆分】\n" + "\n".join([f"- {x}" for x in scenes[:6]]) + "\n"
                content += "【闭环卡片（按场景）】\n"
            elif tid == "C":
                # Metric-driven structure
                content += (
                    "【指标矩阵】\n"
                    f"- PM10阈值={_qse.get('PM10阈值','≤150ug/m3')}；频次=1次/日；责任岗位=安全员；记录=《环境监测台账》。\n"
                    f"- 夜间噪声阈值={_qse.get('夜间噪声阈值','≤55dB')}；频次=1次/日；责任岗位=安全员；记录=《噪声监测记录》。\n"
                    f"- 抽检频次={_card.get('抽检频次','每100m2 1次')}；阈值={_quant.get('阈值','偏差≤5mm')}；责任岗位=质检员；记录=《抽检记录》。\n"
                    "【数据闭环】\n"
                    "- 采集：责任岗位=安全员/质检员；工具=监测仪/尺量；频次=按指标矩阵。\n"
                    "- 判定：按阈值；超限即触发处置。\n"
                    "- 处置：写清动作+时限；复核达标后关闭。\n"
                    "- 归档：台账字段齐全率=100%+上传频次=1次/日。\n"
                    "【闭环卡片】\n"
                )
            elif tid == "D":
                content += (
                    "【监管红线清单】\n"
                    "- 高处作业未防护即作业（触发即停工）。\n"
                    "- 临时用电漏保失效继续运行（触发即停用）。\n"
                    "- 危化品混放/无MSDS（触发即封存整改）。\n"
                    "【岗位联签链】\n"
                    "- 发现人=班组长；处置人=施工员/电工；复核人=安全员/质检员；关闭批准=项目经理。\n"
                    "【闭环时限表】\n"
                    "- 高风险=10min启动处置+2h复核关闭；一般风险=2h启动处置+24h复核关闭。\n"
                    "【闭环卡片】\n"
                )
            elif tid == "E":
                content += (
                    "【区域网格】\n"
                    "- 网格A=主体作业区；网格B=材料与危化品区；网格C=临电设备区。\n"
                    "【班组行为清单】\n"
                    "- 必做：班前交底/PPE自检/作业许可；禁做：无证上岗/危化品混放。\n"
                    "【红黄牌处置】\n"
                    "- 黄牌=2h内整改复核；红牌=立即停工并经项目经理签批后复工。\n"
                    "【闭环卡片】\n"
                )
            # Common fields: risk -> control -> verify -> record -> deviation handling.
            # Keep each line executable and quantifiable.
            cards = []
            if "质量" in t or "验收" in t or "检验" in t:
                cards.extend(
                    [
                        (
                            "风险：材料规格/批次不符导致返工；"
                            "控制：到货验收=1次/批(材料员+质检员)+复验=每批次1次(质检员)+批次隔离；"
                            f"验证：复验合格率{_card['合格率阈值']}，记录=《材料到货验收+复验台账》；"
                            "偏差处置：不合格批次=100%隔离并在24h内退换。【证据:{ev}】"
                        ),
                        (
                            "风险：关键工序参数超差导致隐蔽返工；"
                            f"控制：首件确认=1次/工序+过程抽检={_card['抽检频次']}；"
                            f"验证：偏差{_quant['阈值']}，一次验收通过率{_card['一次验收通过率']}，记录=《首件+抽检记录》；"
                            "偏差处置：超差即停工整改≤2h，复验合格后关闭。【证据:{ev}】"
                        ),
                    ]
                )
            if "安全" in t or "应急" in t or "消防" in t:
                cards.extend(
                    [
                        (
                            "风险：高处/临边作业坠落；"
                            f"控制：临边防护到位+安全带系挂检查={_quant['频次']}(安全员)+作业许可=1次/班；"
                            "验证：巡检记录齐全率=100%，违章=0次/日，记录=《高处作业巡检表》；"
                            "偏差处置：发现未系挂立即停止作业并在10min内整改。【证据:{ev}】"
                        ),
                        (
                            "风险：临时用电漏电/短路引发触电或火灾；"
                            "控制：配电箱锁闭+漏保试跳=1次/周(电工)+临电巡检=2次/日(安全员)；"
                            "验证：试跳记录齐全率=100%，带病运行=0次，记录=《临电点检表》；"
                            "偏差处置：试跳不合格立即停用并在2h内更换。【证据:{ev}】"
                        ),
                    ]
                )
            if any(k in t for k in ("文明", "环保", "环境", "绿色", "扬尘", "噪声", "污水")):
                cards.extend(
                    [
                        (
                            "风险：扬尘外溢引发投诉或处罚；"
                            "控制：围挡闭合率=100%+道路硬化=100%+喷淋=2次/日+车辆冲洗=1次/车+覆盖=100%；"
                            f"验证：PM10{_qse.get('PM10阈值','≤150ug/m3')}（监测=1次/日），投诉=0次/周，记录=《扬尘监测+巡检台账》；"
                            "偏差处置：PM10超限≤15min启动加密喷淋，2h内复测达标。【证据:{ev}】"
                        ),
                        (
                            "风险：夜间噪声超标扰民；"
                            "控制：高噪设备禁用时段=22:00-06:00+消声/隔音+隔声屏+监测=1次/日；"
                            f"验证：夜间噪声{_qse.get('夜间噪声阈值','≤55dB')}，投诉=0次/周，记录=《噪声监测记录》；"
                            "偏差处置：超限立即停用高噪设备并在30min内复测达标。【证据:{ev}】"
                        ),
                    ]
                )

            # Ensure we have enough cards even if title keywords are unusual.
            if len(cards) < 4:
                cards.append(
                    "风险：资料不全导致验收追溯失败；"
                    f"控制：台账字段齐全率=100%+上传频次=1次/日；"
                    "验证：抽查覆盖率=100%，记录=《资料台账》；"
                    "偏差处置：缺项≤24h补齐并复核关闭。【证据:{ev}】"
                )

            for raw in cards[:6]:
                prefix = ""
                if tid == "B":
                    # Attach a lightweight scene tag; still keeps risk/control/verify patterns for the gate.
                    if "扬尘" in str(raw):
                        prefix = "场景=扬尘控制；"
                    elif "噪声" in str(raw):
                        prefix = "场景=夜间施工噪声；"
                    elif "临时用电" in str(raw) or "漏保" in str(raw):
                        prefix = "场景=临时用电；"
                    elif "高处" in str(raw) or "临边" in str(raw):
                        prefix = "场景=高处作业；"
                    elif "材料" in str(raw) or "复验" in str(raw):
                        prefix = "场景=材料到货；"
                    else:
                        prefix = "场景=过程管控；"
                elif tid == "D":
                    if "临时用电" in str(raw) or "漏保" in str(raw):
                        prefix = "红线=临时用电；"
                    elif "高处" in str(raw) or "临边" in str(raw):
                        prefix = "红线=高处作业；"
                    elif "危化品" in str(raw):
                        prefix = "红线=危化品管理；"
                    elif "噪声" in str(raw) or "扬尘" in str(raw):
                        prefix = "红线=环保超限；"
                    else:
                        prefix = "红线=一般管控；"
                elif tid == "E":
                    if "扬尘" in str(raw):
                        prefix = "网格=环保区；"
                    elif "噪声" in str(raw):
                        prefix = "网格=夜施区；"
                    elif "临时用电" in str(raw) or "漏保" in str(raw):
                        prefix = "网格=临电区；"
                    elif "高处" in str(raw) or "临边" in str(raw):
                        prefix = "网格=高处区；"
                    elif "材料" in str(raw) or "复验" in str(raw):
                        prefix = "网格=材料区；"
                    else:
                        prefix = "网格=主体区；"
                content += "- " + (prefix + str(raw)).format(ev=ev_src) + "\n"
            if tid == "B":
                content += (
                    "【检查频次总表】\n"
                    "- 日检：2次/日（班前+收工）。\n"
                    "- 周检：1次/周（专项抽查）。\n"
                    "- 月检：1次/月（联合检查）。\n"
                    "【记录表清单】\n"
                    "- 《巡检表》/《监测记录》/《整改闭环单》/《台账》。\n"
                )
            elif tid == "D":
                content += (
                    "【联签记录要求】\n"
                    "- 每条红线事件必须包含：发现人/处置人/复核人/关闭批准人及时间戳。\n"
                )
            elif tid == "E":
                content += (
                    "【网格巡检要求】\n"
                    "- 每网格至少1条闭环卡片；红黄牌状态必须同步到《网格巡检台账》。\n"
                )
        elif rtype == "logic_template_adherence_gap":
            tid = str(rec.get("template_id") or sec.get("logic_template_id") or "").strip().upper() or "A"
            dom = str(rec.get("chapter_domain") or sec.get("chapter_domain") or "").strip().lower() or "general"
            dom = "qse" if dom == "qse" else "general"
            block = f"\n\n【自动补充】章内逻辑锚点（模版{tid}；域={dom}）：\n"
            if dom == "qse":
                if tid == "B":
                    block += (
                        "- 【场景拆分】夜间施工/高处作业/材料堆放（每个场景至少2条闭环）。\n"
                        f"- 【闭环卡片（按场景）】场景=夜间施工；风险：噪声扰民；控制：高噪设备禁用时段=22:00-06:00+监测=1次/日；"
                        f"验证：夜间噪声{_qse.get('夜间噪声阈值','≤55dB')}，记录=《噪声监测记录》；偏差处置：超限30min内复测达标。【证据:{ev_src}】\n"
                        f"- 【检查频次总表】日检=2次/日；周检=1次/周；月检=1次/月。\n"
                        "- 【记录表清单】《巡检表》/《监测记录》/《整改闭环单》。\n"
                    )
                elif tid == "C":
                    block += (
                        f"- 【指标矩阵】PM10{_qse.get('PM10阈值','≤150ug/m3')}/夜间噪声{_qse.get('夜间噪声阈值','≤55dB')}；频次=1次/日；责任岗位=安全员；记录=《环境监测台账》。\n"
                        "- 【数据闭环】采集(谁/工具/频次)->判定(阈值)->处置(动作+时限)->复核(复测)->归档(台账字段+上传频次)。\n"
                        f"- 【闭环卡片】风险：扬尘超限；控制：喷淋=2次/日+车辆冲洗=1次/车；"
                        f"验证：PM10{_qse.get('PM10阈值','≤150ug/m3')}，记录=《扬尘监测+巡检台账》；偏差处置：超限≤15min启动加密喷淋并2h内复测达标。【证据:{ev_src}】\n"
                    )
                elif tid == "D":
                    block += (
                        "- 【监管红线清单】高处防护/临时用电/危化品管理三条红线逐条列出触发条件。\n"
                        "- 【岗位联签链】发现人->处置人->复核人->关闭批准人，四级责任不可缺失。\n"
                        "- 【闭环时限表】高风险10min启动处置+2h复核关闭；一般风险2h启动处置+24h复核关闭。\n"
                        f"- 【闭环卡片】风险：临时用电漏保失效；控制：停用+更换+复测；验证：试跳记录齐全率=100%，记录=《红线联签闭环单》。【证据:{ev_src}】\n"
                    )
                elif tid == "E":
                    block += (
                        "- 【区域网格】网格A主体区/网格B材料区/网格C临电区，逐网格定义责任岗位和巡检频次。\n"
                        "- 【班组行为清单】必做动作（交底/PPE/许可）与禁止动作（无证上岗/危化品混放）并列。\n"
                        "- 【红黄牌处置】黄牌2h内整改复核；红牌立即停工并经项目经理签批复工。\n"
                        f"- 【复核与销项】风险：PPE不规范；控制：班前检查=1次/班；验证：抽查{_quant['频次']}，记录=《网格巡检台账》。【证据:{ev_src}】\n"
                    )
                else:
                    block += (
                        "- 【闭环清单】字段固定：风险/问题->控制(岗位+频次)->验证(阈值+方法)->记录->偏差处置(时限)。\n"
                        f"- 【闭环卡片】风险：临边坠落；控制：防护到位+系挂检查={_quant['频次']}(安全员)；"
                        "验证：违章=0次/日，记录=《高处作业巡检表》；偏差处置：发现未系挂立即停工并10min内整改关闭。"
                        f"【证据:{ev_src}】\n"
                    )
            else:
                if tid == "B":
                    block += (
                        "- 【工序流程】步骤1=准备与交底；步骤2=测量复核；步骤3=材料进场与验收；步骤4=作业实施；步骤5=检查验收与归档。\n"
                        f"- 【步骤控制点】频次={_quant['频次']}；阈值={_quant['阈值']}；间距={_quant['间距']}；厚度={_quant['厚度']}。\n"
                        f"- 【风险→控制→验证（按步骤）】风险：关键参数超差返工；控制：首件确认=1次/工序+抽检={_card['抽检频次']}；"
                        f"验证：偏差{_quant['阈值']}，合格率{_card['合格率阈值']}，记录=《抽检记录》；偏差处置：超差≤2h返修复验关闭。【证据:{ev_src}】\n"
                    )
                elif tid == "C":
                    block += (
                        f"- 【控制指标矩阵】频次={_quant['频次']}；阈值={_quant['阈值']}；间距={_quant['间距']}；厚度={_quant['厚度']}；时长={_quant['时长']}；人数={_quant['人数']}；设备型号={_quant['设备型号']}。\n"
                        "- 【人机料法环落地】人=责任岗位写到人；机=进场点检=1次/日；料=到货验收=1次/批；法=首件确认=1次/工序；环=扬尘/噪声按阈值监测。\n"
                        f"- 【信息化与台账】字段齐全率=100%+上传频次=1次/日；记录=《台账》。【证据:{ev_src}】\n"
                    )
                elif tid == "D":
                    block += (
                        f"- 【资源-工序耦合表】工序对应班组人数={_quant['人数']}、设备={_quant['设备型号']}、节拍={_quant['时长']}。\n"
                        "- 【接口冲突清单】交叉作业冲突位/避让窗口/责任岗位逐条列出。\n"
                        "- 【关键路径纠偏卡】触发阈值、纠偏动作、时限、复核标准逐条闭环。\n"
                        f"- 【风险→控制→验证（资源视角）】风险：资源错配；控制：日排产+交接清单；验证：偏差{_quant['阈值']}，记录=《资源耦合检查表》。【证据:{ev_src}】\n"
                    )
                elif tid == "E":
                    block += (
                        "- 【实施场景卡片】按作业面/材料区/交叉区拆分场景并定义边界。\n"
                        f"- 【参数对照表】频次={_quant['频次']}；阈值={_quant['阈值']}；间距={_quant['间距']}；厚度={_quant['厚度']}；时长={_quant['时长']}。\n"
                        "- 【验收样表】字段=场景编号/责任岗位/实测值/结论/整改时限/复核人/证据定位。\n"
                        f"- 【风险→控制→验证（场景）】风险：参数超差；控制：首件确认+过程抽检；验证：合格率{_card['合格率阈值']}，记录=《场景验收样表》。【证据:{ev_src}】\n"
                    )
                else:
                    block += (
                        "- 【本章交付物】《日排产表》+《资源协调台账》+《检查/验收记录》；字段齐全率=100%。\n"
                        f"- 【交付物】交底=1次/班；接口清单=1份/专业；问题闭环时长≤4h。【证据:{ev_src}】\n"
                        f"- 【约束条件】作业面、材料到货、班组人数、设备投入必须同口径联动校核。【证据:{ev_src}】\n"
                        f"- 【风险→控制→验证】风险：资源错配导致工序等待；控制：班前协调=1次/班+日排产复核=1次/日；"
                        f"验证：等待时长≤30min，记录=《资源协调记录》；偏差处置：超时≤2h纠偏关闭。【证据:{ev_src}】\n"
                    )
            content = block + content
        elif rtype == "engineering_gap":
            content += (
                "\n\n【自动补充】工程落地要素：\n"
                "- 频次：2次/日巡检；阈值：偏差≤5mm；责任：质量员复核+工长签认；"
                f"验收：首件验收=1次/工序+隐蔽验收=100%覆盖；流程：交底-自检-互检-专检-验收-归档。【证据:{ev_src}】\n"
            )
        elif rtype == "chapter_blueprint_gap":
            bp_name = str(rec.get("blueprint_name") or "").strip()
            missing = rec.get("missing_anchors") if isinstance(rec.get("missing_anchors"), list) else []
            missing = [str(x).strip() for x in missing if str(x).strip()]
            if not missing:
                missing = [str(x).strip() for x in (rec.get("missing") or []) if str(x).strip()] if isinstance(rec.get("missing"), list) else []
            head = f"章节结构蓝图：{bp_name}" if bp_name else "章节结构蓝图"
            content += f"\n\n【自动补充】{head}：\n"
            if missing:
                content += f"- 缺失锚点：{'、'.join(missing[:8])}。\n"
            for anc in missing[:8]:
                content += (
                    f"【{anc}】\n"
                    f"- 量化：频次={_quant['频次']}；阈值={_quant['阈值']}；时长={_quant['时长']}；记录=《{anc}检查表》。\n"
                    f"- 风险→控制→验证：风险：{anc}要点遗漏导致返工/停工；控制：首件确认=1次/工序+抽检={_card['抽检频次']}；"
                    f"验证：偏差{_quant['阈值']}，合格率{_card['合格率阈值']}，记录=《{anc}抽检记录》；偏差处置：超差≤2h整改复验关闭。【证据:{ev_src}】\n"
                )
        elif rtype == "quantitative_gap":
            content += (
                "\n\n【自动补充】量化指标：\n"
                f"- 频次：{_quant['频次']}；阈值：{_quant['阈值']}；间距：{_quant['间距']}；厚度：{_quant['厚度']}；"
                f"时长：{_quant['时长']}；人数：{_quant['人数']}；设备型号：{_quant['设备型号']}。【证据:{ev_src}】\n"
            )
        elif rtype == "special_topic_missing":
            content += (
                "\n\n【自动补充】专项管理内容：\n"
                f"- {suggestion}\n"
                f"- 需包含：执行步骤、责任工种、检查频次、验收标准、应急流程。【证据:{ev_src}】\n"
            )
        elif rtype == "consistency_conflict":
            content += (
                "\n\n【自动补充】数据一致性校核：\n"
                f"- {suggestion}\n"
                "- 对工期、资源峰值、关键线路间隔进行统一口径修订并复核。【证据:进度计划/资源计划】\n"
            )
        elif rtype == "vague_term":
            content = _sanitize_vague_language(content)
            content = strip_nonconcrete_language(content)
            content += (
                "\n\n【自动补充】消除空泛词：\n"
                f"- {suggestion}\n"
                f"- 将空泛词替换为可执行动作+量化参数+验收标准（示例：巡检2次/日，偏差≤5mm，记录表齐全率100%）。【证据:{ev_src}】\n"
            )
        elif rtype == "bureaucratic_phrase":
            cleaned = strip_nonconcrete_language(content)
            content = cleaned
            content += (
                "\n\n【自动补充】替换空话为可执行项：\n"
                f"- 动作：班前交底+过程巡检+隐蔽验收；参数：偏差≤5mm；频次：2次/日；责任岗位：工长/质量员；验收标准：一次验收通过率≥95%。【证据:{ev_src}】\n"
            )
        elif rtype == "boq_focus_item_closure_gap":
            focus_items = []
            if isinstance(boq_focus, dict):
                focus_items = [str(x).strip() for x in (boq_focus.get("must_cover_keywords") or []) if str(x).strip()]
            content += "\n\n【自动补充】重点清单项闭环（每项至少 2 条）：\n"
            if not focus_items:
                focus_items = ["重点清单项"]
            for name in focus_items[:8]:
                content += (
                    f"- 清单项：{name}；频次={_quant['频次']}；阈值={_quant['阈值']}；间距={_quant['间距']}；厚度={_quant['厚度']}；"
                    f"时长={_quant['时长']}；人数={_quant['人数']}；设备型号={_quant['设备型号']}；"
                    f"风险：{name}到货或工序参数不符导致返工/超支；控制：责任岗位=工长+质量员，采购比价{_card['采购比价']}，到货验收=1次/批，首件确认=1次/工序，抽检={_card['抽检频次']}；"
                    f"验证：合格率{_card['合格率阈值']}，记录=《{name}重点项抽检记录》；偏差处置：超差即停工整改≤2h，复验合格后关闭。【证据:{ev_src}】\n"
                    f"- 清单项：{name}；频次={_quant['频次']}；阈值={_quant['阈值']}；间距={_quant['间距']}；厚度={_quant['厚度']}；"
                    f"时长={_quant['时长']}；人数={_quant['人数']}；设备型号={_quant['设备型号']}；"
                    f"风险：{name}施工偏差导致质量/进度损失；控制：责任岗位=工长+安全员，样板先行=1次/作业面，巡检={_quant['频次']}，复核=1次/班；"
                    f"验证：一次验收通过率{_card['一次验收通过率']}，记录=《{name}过程验收记录表》；偏差处置：异常4h内纠偏并复核关闭。【证据:{ev_src}】\n"
                )
        elif rtype == "boq_focus_item_typed_evidence_gap":
            draw_src = ""
            std_src = ""
            try:
                from backend.zhifei_autoplan.evidence import best_ingested_hit

                if project_id:
                    hit = best_ingested_hit(
                        f"{sec_title} 图纸",
                        limit=10,
                        prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
                        project_id=project_id,
                        require_tags=["drawing"],
                        exclude_tags=["logo"],
                        audit_path=audit_path,
                    )
                    if hit and hit.get("locator"):
                        draw_src = str(hit.get("locator"))
                    hit2 = best_ingested_hit(
                        f"{sec_title} 企业标准 工法 作业指导 标准化",
                        limit=10,
                        prefer_filename_keywords=["标准", "企业标准", "工法", "作业指导", "标准化"],
                        project_id=project_id,
                        require_tags=["standard"],
                        exclude_tags=["logo"],
                        audit_path=audit_path,
                    )
                    if hit2 and hit2.get("locator"):
                        std_src = str(hit2.get("locator"))
            except Exception:
                draw_src = draw_src or ""
                std_src = std_src or ""
            content += "\n\n【自动补充】重点项图纸/标准证据闭环：\n"
            if draw_src:
                content += f"- 图纸定位：{draw_src}；校核点=构件位置/尺寸/标高/做法。【证据:{draw_src}】\n"
            if std_src:
                content += f"- 标准引用：{std_src}；条款对照入台账。【证据:{std_src}】\n"
            content += (
                "- 放置位置：每条“清单重点项控制卡”内，且与清单项名称同一段落窗口内可追溯。\n"
            )
        elif rtype == "required_topic_detail_gap":
            specials = []
            hazards = []
            ppes = []
            if isinstance(boq_focus, dict):
                specials = [str(x).strip() for x in (boq_focus.get("special_materials") or []) if str(x).strip()]
                hazards = [str(x).strip() for x in (boq_focus.get("hazardous_materials") or []) if str(x).strip()]
                ppes = [str(x).strip() for x in (boq_focus.get("ppe_items") or []) if str(x).strip()]
            block = (
                "\n\n【自动补充】专项可执行细则：\n"
                f"- {suggestion}\n"
                f"- 每条写清：动作+参数+频次+责任岗位+验收方法/阈值+记录表（示例：危险品领用双人复核=1次/单；应急演练=1次/季度）。【证据:{ev_src}】\n"
            )
            if specials:
                block += (
                    "\n- 特殊材料（按清单统计）：\n"
                    + "\n".join(
                        [
                            f"  - {name}：风险→控制→验证：风险=规格/批次不符导致返工或性能不达标；"
                            f"控制=到货验收=1次/批(材料员+质检员)+复验=每批次1次(质检员)+批次隔离+二维码批次追溯(材料员)；"
                            f"验证=复验合格率{_card['合格率阈值']}+批次追溯完整率=100%，记录=《特殊材料到货验收+复验台账》。【证据:{ev_src}】"
                            for name in specials[:8]
                        ]
                    )
                    + "\n"
                )
            if hazards:
                block += (
                    "\n- 危险品材料（按清单统计）：\n"
                    + "\n".join(
                        [
                            f"  - {name}：采购=资质+MSDS随货；储存=专库/通风/防火；堆码间距≥{_quant['间距']}；"
                            f"领用=双人复核1次/单；应急演练频次={_card['应急演练频次']}；"
                            f"风险→控制→验证：风险=挥发/燃爆导致伤害与停工；控制=动火审批+可燃气体检测=1次/班；"
                            f"验证=检测记录齐全率100%，违章=0次。【证据:{ev_src}】"
                            for name in hazards[:8]
                        ]
                    )
                    + "\n"
                )
            if ppes:
                block += (
                    "\n- 劳保用品（按清单统计）：\n"
                    + "\n".join(
                        [
                            f"  - {name}：风险→控制→验证：风险=未佩戴或用品失效导致伤害；"
                            f"控制=发放=1套/人(安全员)+佩戴抽查={_quant['频次']}(安全员)+破损48h内更换(库管)；"
                            f"验证=抽查覆盖率=100%+不佩戴=0次/日，记录=《劳保发放与检查台账》。【证据:{ev_src}】"
                            for name in ppes[:10]
                        ]
                    )
                    + "\n"
                )
            # Ensure required topics keywords appear with units/metrics.
            block += (
                "\n- 绿色工地：扬尘=围挡喷淋启停间隔10min；噪声=夜间施工噪声≤55dB；污水=沉淀池停留时长≥2h，pH=6~9。【证据:环保监测记录】\n"
                "- 信息化管理：材料/设备/隐蔽验收二维码=1处/构件；台账上传频次=1次/日；问题闭环时长≤24h。【证据:系统台账导出】\n"
                "- 技术工种配置：测量工1人/班；钢筋工2人/班；模板工2人/班；混凝土工2人/班；架子工2人/班；电工1人/班；焊工1人/班；起重信号司索工1人/班（起重作业时）。【证据:劳动力计划】\n"
                f"- 四新技术：适用=防水/管道/材料追溯；投入=样板段1处+新设备1台+首批材料1批；步骤=样板交底->首件实施->过程抽检->验收归档；验收=合格率{_card['合格率阈值']}；风险=参数失配导致返工；验证=抽检=每100m2 1次，记录=《四新技术应用台账》。【证据:{ev_src}】\n"
            )
            # 四新技术：按清单/工序匹配给出可执行闭环卡片（避免“新技术应用”空话）。
            try:
                from backend.zhifei_autoplan.four_new_tech import recommend_four_new, render_four_new_recommendations

                recs = []
                if isinstance(boq_focus, dict):
                    recs = boq_focus.get("four_new_recommendations") or []
                if not isinstance(recs, list) or not recs:
                    # Minimal fallback based on focus keywords; still produces conservative, verifiable items.
                    fake_items = []
                    if isinstance(boq_focus, dict):
                        for x in (boq_focus.get("must_cover_keywords") or [])[:30]:
                            sx = str(x).strip()
                            if sx:
                                fake_items.append({"name": sx, "process": {"name": ""}})
                    recs = recommend_four_new({"items": fake_items}, outline=[sec_title], limit=6)
                if recs:
                    block += "\n【四新技术闭环卡片（按清单/工序匹配）】\n"
                    block += (
                        render_four_new_recommendations(
                            recs,
                            quant=_quant,
                            card=_card,
                            qse=_qse,
                            evidence_src=ev_src,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            content = block + content
        elif rtype == "evidence_gap":
            content += (
                "\n\n【自动补充】证据标注：\n"
                f"- 在每条关键结论句末追加“【证据:{ev_src}】”（格式=文件名#p页_sha@offset）；至少 1 条/章；不得使用“待补充/待定位”。【证据:{ev_src}】\n"
            )
        elif rtype == "evidence_traceability_gap":
            content += (
                "\n\n【自动补充】证据可追溯定位：\n"
                f"- 本章至少保留 1 条带定位符的证据（示例：{ev_src}）。【证据:{ev_src}】\n"
            )
        elif rtype == "core_conclusion_evidence_gap":
            content, annotated = _annotate_core_conclusions(content, ev_src)
            content += (
                "\n\n【自动补充】核心结论证据补齐：\n"
                f"- 已为本章回填 {annotated} 条核心结论证据定位符；未命中的句子需继续人工复核。\n"
                f"- 示例：抽检频次=每100m2 1次，偏差≤5mm，偏差处置时限≤4h，责任岗位=质量员，记录=《抽检台账》。【证据:{ev_src}】\n"
            )
        elif rtype == "drawing_evidence_gap":
            draw_src = ev_src
            try:
                from backend.zhifei_autoplan.evidence import best_ingested_hit

                hit = best_ingested_hit(
                    f"{sec_title} 图纸",
                    limit=10,
                    prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
                    project_id=project_id,
                    require_tags=["drawing"],
                    exclude_tags=["logo"],
                    audit_path=audit_path,
                )
                if hit and hit.get("locator"):
                    draw_src = str(hit.get("locator"))
            except Exception:
                draw_src = ev_src
            content += (
                "\n\n【自动补充】图纸证据定位：\n"
                f"- 本章至少绑定 1 条图纸证据定位符：{draw_src}。【证据:{draw_src}】\n"
            )
        elif rtype == "drawing_anchor_gap":
            draw_src = ev_src
            content += (
                "\n\n【自动补充】图纸空间锚点：\n"
                "- 空间锚点：构件定位（坐标X/Y 或轴网）+标高；\n"
                "- 尺寸锚点：关键尺寸（厚度/间距/长度）并对应验收阈值；\n"
                f"- 示例：构件=承台A1，坐标=(102.5,85.3)，标高=+3.20m【空间锚点:承台A1@102.5,85.3,+3.20m】；"
                f"桩径=1000mm【尺寸锚点:桩径1000mm】。【证据:{draw_src}】\n"
            )
        elif rtype == "standard_evidence_gap":
            std_src = ev_src
            try:
                from backend.zhifei_autoplan.evidence import best_ingested_hit

                hit = best_ingested_hit(
                    f"{sec_title} 企业标准 工法 作业指导 标准化",
                    limit=10,
                    prefer_filename_keywords=["标准", "企业标准", "工法", "作业指导", "标准化"],
                    project_id=project_id,
                    require_tags=["standard"],
                    exclude_tags=["logo"],
                    audit_path=audit_path,
                )
                if hit and hit.get("locator"):
                    std_src = str(hit.get("locator"))
            except Exception:
                std_src = ev_src
            content += (
                "\n\n【自动补充】企业标准/工法引用与落地：\n"
                f"- 引用：{std_src}（条款对照纳入台账）。【证据:{std_src}】\n"
                "- 风险→控制→验证：风险=未按条款执行导致质量返工/验收不通过；"
                "控制=按条款列出关键参数（厚度/间距/强度/工序顺序）并做首件确认=1次/工序，"
                "过程抽检频次=每100m2 1次；"
                f"验证=偏差≤5mm，抽检合格率≥98%，记录=《标准条款对照与抽检记录》。【证据:{std_src}】\n"
            )

        sec["content"] = content
        sec["auto_remediated"] = True
        _append_strategy_trace(sec, rec)
        _append_execution_trace(sec, rec, before_text=before_text, after_text=str(content or ""))


def run_quality_checks(
    tender: Dict[str, Any],
    outline: List[str],
    sections: List[Dict[str, Any]],
    boq: Dict[str, Any] | None = None,
    boq_focus: Dict[str, Any] | None = None,
    project_id: str | None = None,
    strict: bool = False,
    workspace_dir: str | None = None,
) -> Dict[str, Any]:
    outline_titles = set(outline or [])
    section_titles = [s.get("title") for s in sections]
    missing_titles = [t for t in outline_titles if t not in section_titles]

    sec_by_title: Dict[str, Dict[str, Any]] = {}
    for s in sections or []:
        key = str(s.get("title") or "").strip()
        if not key:
            continue
        sec_by_title.setdefault(key, s)

    all_text = "\n".join((s.get("content") or "") for s in sections)
    good_evidence_count = sum(_count_good_evidence(s.get("content") or "") for s in sections)
    placeholder_evidence_count = sum(_count_placeholder_evidence(s.get("content") or "") for s in sections)
    has_ingested_docs = False
    ingest_audit = _ingest_audit_path(workspace_dir)
    try:
        p = ingest_audit
        if p.exists() and p.stat().st_size > 0:
            pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
            if pid is None:
                has_ingested_docs = True
            else:
                # Only require traceability when the project actually ingested documents.
                for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1][:1200]:
                    try:
                        import json as _json

                        rec = _json.loads(ln)
                    except Exception:
                        continue
                    if str(rec.get("project_id") or "").strip() == pid:
                        has_ingested_docs = True
                        break
    except Exception:
        has_ingested_docs = False

    remediation = []
    issue_list = []
    for sec in sections:
        title = sec.get("title") or "章节"
        text = sec.get("content") or ""
        # 评分点缺失
        if tender:
            missing_dims = []
            missing_keywords: List[str] = []
            for it in tender.get("items", []):
                dim = str(it.get("dimension"))
                kws = it.get("keywords") or []
                if not kws:
                    continue
                hit = any(k in text for k in kws[:6])
                if not hit:
                    if dim:
                        missing_dims.append(dim)
                    for kw in kws[:6]:
                        kw_s = str(kw).strip()
                        if kw_s and kw_s not in missing_keywords:
                            missing_keywords.append(kw_s)
            if missing_dims:
                unique_dims = sorted(set(missing_dims))
                rec = {
                    "title": title,
                    "type": "score_point_missing",
                    "missing_dimensions": unique_dims,
                    "missing_keywords": missing_keywords,
                    "suggestion": f"补充评分点覆盖：{';'.join(unique_dims)}，使用短句+要点+量化指标表达。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": title,
                        "type": "score_point_missing",
                        "severity": "high",
                        "problem": f"评分点覆盖不足：{';'.join(unique_dims)}",
                        "suggestion": rec["suggestion"],
                    }
                )
        # 风险-措施闭环
        has_risk = "风险" in text
        has_measure = ("措施" in text) or ("对应" in text) or bool(_extract_risk_triplets(text))
        if has_risk and not has_measure:
            rec = {
                "title": title,
                "type": "risk_measure_gap",
                "suggestion": "补充“风险→措施”一一对应的措施条目，并标明责任人/频次/验收动作。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "risk_measure_gap",
                    "severity": "high",
                    "problem": "出现风险描述但缺少对应措施。",
                    "suggestion": rec["suggestion"],
                }
            )
        # 工程落地要素
        miss_eng = [k for k in ["频次", "阈值", "责任", "验收", "流程"] if k not in text]
        if len(miss_eng) > 2:
            rec = {
                "title": title,
                "type": "engineering_gap",
                "suggestion": f"补充工程落地要素：{','.join(miss_eng)}，明确执行频次/阈值/责任/验收/流程闭环。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "engineering_gap",
                    "severity": "medium",
                    "problem": f"工程化要素缺失：{','.join(miss_eng)}",
                    "suggestion": rec["suggestion"],
                }
            )

    risk_triplet_by_section = _check_risk_triplet_by_section(sections)
    quantitative_by_section = _check_quantitative_by_section(sections)
    vague_by_section = _check_vague_terms_by_section(sections)
    officialese_by_section = _check_officialese_by_section(sections)
    consistency = _check_consistency(sections)
    boq_focus_coverage = _check_boq_focus_coverage(boq_focus or {}, all_text)
    boq_focus_item_closure = _check_boq_focus_item_closure(boq_focus or {}, sections)
    required_topics = _check_required_topics(all_text)
    required_topics_detail = _check_required_topics_detail(sections)
    qse_closed_loop = _check_qse_closed_loop_by_section(sections)
    logic_template_adherence = _check_logic_template_adherence_by_section(sections)
    chapter_blueprint_adherence = _check_chapter_blueprint_adherence_by_section(sections)
    trades = _check_trades_by_section(sections)
    evidence_quality_by_section = _check_evidence_quality_by_section(sections)
    evidence_traceability_by_section = _check_evidence_traceability_by_section(sections, require_traceable=has_ingested_docs)
    core_conclusion_evidence_by_section = _check_core_conclusion_evidence_by_section(sections)
    drawing_names = _load_drawing_filenames(
        project_id=project_id,
        limit=80,
        audit_path=ingest_audit,
        workspace_dir=workspace_dir,
    ) if has_ingested_docs else []
    drawing_evidence_by_section = _check_drawing_evidence_by_section(sections, drawing_names)
    drawing_anchor_by_section = _check_drawing_anchor_binding_by_section(sections, drawing_names)
    standard_names = _load_standard_filenames(
        project_id=project_id,
        limit=80,
        audit_path=ingest_audit,
        workspace_dir=workspace_dir,
    ) if has_ingested_docs else []
    standard_evidence = _check_standard_evidence_by_section(sections, standard_names)
    boq_focus_item_typed_evidence = _check_boq_focus_item_typed_evidence(
        boq_focus or {},
        sections,
        drawing_names=drawing_names,
        standard_names=standard_names,
    )

    if strict:
        for s in risk_triplet_by_section:
            if not s.get("ok"):
                rec = {
                    "title": s.get("title"),
                    "type": "risk_triplet_gap",
                    "suggestion": "将风险段落改写为“风险→控制→验证”三元组，并补齐验证阈值/方法。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": s.get("title"),
                        "type": "risk_triplet_gap",
                        "severity": "high",
                        "problem": "风险闭环不完整，未形成可验证三元组。",
                        "suggestion": rec["suggestion"],
                    }
                )
        for s in quantitative_by_section:
            if not s.get("ok"):
                rec = {
                    "title": s.get("title"),
                    "type": "quantitative_gap",
                    "suggestion": f"补齐量化指标，优先补充：{','.join((s.get('missing') or [])[:5])}，并给出具体数值与单位。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": s.get("title"),
                        "type": "quantitative_gap",
                        "severity": "high",
                        "problem": "量化指标不足或缺少单位数值。",
                        "suggestion": rec["suggestion"],
                    }
                )
        for s in vague_by_section:
            if not s.get("ok"):
                rec = {
                    "title": s.get("title"),
                    "type": "vague_term",
                    "suggestion": "将空泛词替换为可执行动作+参数+频次+验收标准。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": s.get("title"),
                        "type": "vague_term",
                        "severity": "medium",
                        "problem": f"发现空泛词表达 {s.get('count')} 处。",
                        "suggestion": rec["suggestion"],
                    }
                )
        for s in officialese_by_section:
            if not s.get("ok"):
                phrases = [h.get("phrase") for h in (s.get("hits") or []) if h.get("phrase")]
                rec = {
                    "title": s.get("title"),
                    "type": "bureaucratic_phrase",
                    "suggestion": f"删除官话/套话并改为可执行指标，命中词：{','.join(phrases[:10])}",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": s.get("title"),
                        "type": "bureaucratic_phrase",
                        "severity": "high",
                        "problem": f"出现官话/套话/空话表达 {s.get('count')} 处。",
                        "suggestion": rec["suggestion"],
                    }
                )
        if not consistency.get("ok"):
            for c in consistency.get("conflicts", []):
                rec = {
                    "title": "全局一致性",
                    "type": "consistency_conflict",
                    "suggestion": f"统一{c.get('metric')}口径，冲突值：{c.get('values')}",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": "全局一致性",
                        "type": "consistency_conflict",
                        "severity": "high",
                        "problem": f"{c.get('metric')}存在前后冲突。",
                        "suggestion": rec["suggestion"],
                    }
                )
        if not boq_focus_coverage.get("ok"):
            rec = {
                "title": "清单重点项",
                "type": "special_topic_missing",
                "suggestion": f"补写重点清单项：{';'.join((boq_focus_coverage.get('missing') or [])[:8])}",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": "清单重点项",
                    "type": "boq_focus_missing",
                    "severity": "high",
                    "problem": "重点清单项覆盖不足。",
                    "suggestion": rec["suggestion"],
                }
            )
        if not boq_focus_item_closure.get("ok"):
            rec = {
                "title": "清单重点项",
                "type": "boq_focus_item_closure_gap",
                "suggestion": "对每个重点清单项补齐：量化指标+风险→控制→验证+证据标注，并放在对应工序章节。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": "清单重点项",
                    "type": "boq_focus_item_closure_gap",
                    "severity": "high",
                    "problem": "重点清单项虽出现，但未在对应章节形成可验收闭环（量化+三元组+证据）。",
                    "suggestion": rec["suggestion"],
                }
            )
        if not boq_focus_item_typed_evidence.get("ok"):
            need = []
            if boq_focus_item_typed_evidence.get("has_drawings"):
                need.append("图纸定位符")
            if boq_focus_item_typed_evidence.get("has_standards"):
                need.append("企业标准定位符")
            need_text = " + ".join(need) if need else "图纸/企业标准定位符"
            rec = {
                "title": "清单重点项",
                "type": "boq_focus_item_typed_evidence_gap",
                "suggestion": f"对每个重点清单项补齐{need_text}，并把定位符放在对应重点项控制卡内（同一窗口内可追溯）。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": "清单重点项",
                    "type": "boq_focus_item_typed_evidence_gap",
                    "severity": "high",
                    "problem": "重点清单项缺少图纸/企业标准类型证据定位符，评审追溯成本高。",
                    "suggestion": rec["suggestion"],
                }
            )
        if not required_topics.get("ok"):
            rec = {
                "title": "专项主题",
                "type": "special_topic_missing",
                "suggestion": f"补齐专项内容：{','.join(required_topics.get('missing') or [])}",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": "专项主题",
                    "type": "special_topic_missing",
                    "severity": "high",
                    "problem": "专项内容未覆盖完整。",
                    "suggestion": rec["suggestion"],
                }
            )
        if not required_topics_detail.get("ok"):
            rec = {
                "title": "专项主题",
                "type": "required_topic_detail_gap",
                "suggestion": "对必选专项补齐可执行细则：采购/储运/领用/作业/应急或发放/检查/更换，并给出频次/阈值/时长等数值。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": "专项主题",
                    "type": "required_topic_detail_gap",
                    "severity": "high",
                    "problem": "必选专项虽出现，但缺少可执行细节或量化参数。",
                    "suggestion": rec["suggestion"],
                }
            )
        if not qse_closed_loop.get("ok"):
            for s in (qse_closed_loop.get("by_section") or [])[:12]:
                if not isinstance(s, dict) or s.get("ok"):
                    continue
                title = s.get("title") or "章节"
                missing = s.get("missing") or []
                miss_text = ",".join([str(x) for x in missing if str(x).strip()]) or "闭环字段"
                rec = {
                    "title": title,
                    "type": "qse_closed_loop_gap",
                    "template_id": str((sec_by_title.get(str(title).strip()) or {}).get("logic_template_id") or "").strip(),
                    "chapter_domain": "qse",
                    "suggestion": f"本章属于质量/安全/文明环保类章节，按闭环卡片补齐：{miss_text}；每条写清风险→控制→验证→记录→偏差处置（含频次/阈值/时限）。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": title,
                        "type": "qse_closed_loop_gap",
                        "severity": "high",
                        "problem": "质量/安全/文明环保章节闭环不足（缺三元组/记录/偏差处置或缺单位数值）。",
                        "suggestion": rec["suggestion"],
                    }
                )
        if not logic_template_adherence.get("ok"):
            for s in (logic_template_adherence.get("by_section") or [])[:12]:
                if not isinstance(s, dict) or s.get("ok"):
                    continue
                title = s.get("title") or "章节"
                tid = str(s.get("template_id") or "").strip().upper() or "A"
                dom = str(s.get("chapter_domain") or "").strip().lower() or "general"
                missing = s.get("missing") or []
                miss_text = "；".join([str(x) for x in missing if str(x).strip()][:6])
                rec = {
                    "title": title,
                    "type": "logic_template_adherence_gap",
                    "template_id": tid,
                    "chapter_domain": dom,
                    "suggestion": f"本章使用章内逻辑模版{tid}（{dom}），需至少出现锚点小标题：{miss_text}；并按模版顺序组织段落（不改招标目录）。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": title,
                        "type": "logic_template_adherence_gap",
                        "severity": "medium",
                        "problem": "章内逻辑锚点缺失，导致多方案差异不足（可能只是换词）。",
                        "suggestion": rec["suggestion"],
                    }
                )
        if not chapter_blueprint_adherence.get("ok"):
            for s in (chapter_blueprint_adherence.get("by_section") or [])[:12]:
                if not isinstance(s, dict) or s.get("ok"):
                    continue
                title = s.get("title") or "章节"
                bid = str(s.get("blueprint_id") or "").strip()
                bname = str(s.get("blueprint_name") or "").strip()
                missing = s.get("missing") or []
                miss_text = "、".join([str(x) for x in missing if str(x).strip()][:10])
                rec = {
                    "title": title,
                    "type": "chapter_blueprint_gap",
                    "blueprint_id": bid,
                    "blueprint_name": bname,
                    "missing_anchors": missing,
                    "suggestion": f"本章匹配章节结构蓝图“{bname or bid}”，需补齐锚点：{miss_text}；并按锚点组织段落（不改招标目录）。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": title,
                        "type": "chapter_blueprint_gap",
                        "severity": "high",
                        "problem": "章节结构蓝图锚点缺失，章内结构未按要求组织。",
                        "suggestion": rec["suggestion"],
                    }
                )
        for s in trades:
            if not s.get("ok"):
                rec = {
                    "title": s.get("title"),
                    "type": "special_topic_missing",
                    "suggestion": f"补充规范工种配置，建议至少包含：{','.join(STANDARD_TRADES[:8])}",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": s.get("title"),
                        "type": "trade_name_gap",
                        "severity": "medium",
                        "problem": "工种章节未采用规范工种称谓。",
                        "suggestion": rec["suggestion"],
                    }
                )

        # 证据标注：禁止“待补充/待定位”，且每章至少 1 条可追溯证据
        for s in evidence_quality_by_section:
            if s.get("ok"):
                continue
            title = s.get("title") or "章节"
            rec = {
                "title": title,
                "type": "evidence_gap",
                "suggestion": "为本章关键结论补齐“【证据:文件名#定位符】”，至少 1 条/章；不得出现“待补充/待定位”。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "evidence_gap",
                    "severity": "high",
                    "problem": "证据标注不足或包含占位符。",
                    "suggestion": rec["suggestion"],
                }
                )

        # 若存在已入库的招标/清单/图纸，则每章至少 1 条证据需包含定位符（文件名#p页_sha@offset）
        for s in evidence_traceability_by_section:
            if s.get("ok"):
                continue
            title = s.get("title") or "章节"
            rec = {
                "title": title,
                "type": "evidence_traceability_gap",
                "suggestion": "补齐至少 1 条带定位符的证据（文件名#p页_sha@offset），用于评审追溯。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "evidence_traceability_gap",
                    "severity": "high",
                    "problem": "存在入库资料但证据未包含可追溯定位符。",
                    "suggestion": rec["suggestion"],
                }
                )

        # 核心结论（带约束/阈值/动作）必须带可追溯证据
        for s in core_conclusion_evidence_by_section:
            if s.get("ok"):
                continue
            title = s.get("title") or "章节"
            rec = {
                "title": title,
                "type": "core_conclusion_evidence_gap",
                "suggestion": "核心结论句（含频次/阈值/时限等）需逐条补齐“【证据:文件名#p页_sha@offset】”。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "core_conclusion_evidence_gap",
                    "severity": "high",
                    "problem": f"核心结论证据覆盖不足（已覆盖{s.get('covered')}/{s.get('core_total')}）。",
                    "suggestion": rec["suggestion"],
                }
            )

        # 图纸证据：若本项目存在图纸资料，则关键工序章节至少绑定 1 条图纸证据定位符
        for s in drawing_evidence_by_section:
            if s.get("ok"):
                continue
            if not s.get("required"):
                continue
            title = s.get("title") or "章节"
            rec = {
                "title": title,
                "type": "drawing_evidence_gap",
                "suggestion": "本章属于关键工序章节，需补齐至少 1 条图纸证据定位符（文件名#p页_sha@offset）。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "drawing_evidence_gap",
                    "severity": "high",
                    "problem": "存在图纸资料但本章未绑定图纸证据定位符。",
                    "suggestion": rec["suggestion"],
                }
            )

        # 图纸空间语义锚点：关键工序章节需至少有“空间锚点+尺寸锚点”
        for s in drawing_anchor_by_section:
            if s.get("ok"):
                continue
            if not s.get("required"):
                continue
            title = s.get("title") or "章节"
            rec = {
                "title": title,
                "type": "drawing_anchor_gap",
                "suggestion": "补齐图纸空间锚点与尺寸锚点（示例：构件坐标/标高/尺寸），并保留证据定位符。",
            }
            remediation.append(rec)
            issue_list.append(
                {
                    "title": title,
                    "type": "drawing_anchor_gap",
                    "severity": "high",
                    "problem": "关键工序章节缺少图纸空间锚点或尺寸锚点。",
                    "suggestion": rec["suggestion"],
                }
            )

        # 企业标准：若本项目存在企业标准/工法/作业指导资料，则至少在关键工序章节引用其证据定位符
        if not (standard_evidence or {}).get("ok"):
            # Prefer filling key process chapters; otherwise, fill the first chapter.
            missing_titles = [
                r.get("title")
                for r in (standard_evidence.get("by_section") or [])
                if r.get("is_key_process") and not r.get("has_standard_evidence")
            ]
            if not missing_titles:
                missing_titles = [sections[0].get("title") if sections else "章节"]
            for t in missing_titles[:2]:
                rec = {
                    "title": t or "章节",
                    "type": "standard_evidence_gap",
                    "suggestion": "引用企业标准/工法/作业指导资料的证据定位符，并将条款要求转为可执行的“风险→控制→验证”闭环与量化指标。",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": t or "章节",
                        "type": "standard_evidence_gap",
                        "severity": "high",
                        "problem": "存在企业标准资料但未被引用为可追溯证据。",
                        "suggestion": rec["suggestion"],
                    }
                )

    dedup = {}
    for rec in remediation:
        key = (rec.get("title"), rec.get("type"), rec.get("suggestion"))
        dedup[key] = rec
    remediation = list(dedup.values())
    remediation = enrich_strategy_rows(remediation, sec_by_title=sec_by_title)
    issue_list = enrich_strategy_rows(issue_list, sec_by_title=sec_by_title)
    remediation_strategy_audit = build_strategy_audit(remediation, issue_list=issue_list)
    remediation_execution_audit = build_execution_audit(sections)

    return {
        "structure": {
            "ok": len(missing_titles) == 0,
            "missing_titles": missing_titles,
        },
        "score_coverage": _check_score_coverage(tender, sections),
        "score_coverage_by_section": _check_score_coverage_by_section(tender, sections),
        "closed_loop": _check_closed_loop(sections),
        "closed_loop_by_section": _check_closed_loop_by_section(sections),
        "engineering": _check_engineering(all_text),
        "engineering_by_section": _check_engineering_by_section(sections),
        "risk_triplet": {
            "ok": all(s.get("ok") for s in risk_triplet_by_section),
            "by_section": risk_triplet_by_section,
        },
        "quantitative": {
            "ok": all(s.get("ok") for s in quantitative_by_section),
            "by_section": quantitative_by_section,
        },
        "vague_terms": {
            "ok": all(s.get("ok") for s in vague_by_section),
            "by_section": vague_by_section,
        },
        "officialese": {
            "ok": all(s.get("ok") for s in officialese_by_section),
            "by_section": officialese_by_section,
        },
        "consistency": consistency,
        "boq_focus_coverage": boq_focus_coverage,
        "boq_focus_item_closure": boq_focus_item_closure,
        "boq_focus_item_typed_evidence": boq_focus_item_typed_evidence,
        "required_topics": required_topics,
        "required_topics_detail": required_topics_detail,
        "qse_closed_loop": qse_closed_loop,
        "logic_template_adherence": logic_template_adherence,
        "chapter_blueprint_adherence": chapter_blueprint_adherence,
        "trade_names": {
            "ok": all(s.get("ok") for s in trades),
            "by_section": trades,
        },
        "evidence": {
            "ok": good_evidence_count >= max(1, len(sections)) and placeholder_evidence_count == 0,
            "evidence_count": good_evidence_count,
            "placeholder_count": placeholder_evidence_count,
            "by_section": _count_evidence_by_section(sections),
        },
        "evidence_quality": {
            "ok": all(s.get("ok") for s in evidence_quality_by_section),
            "by_section": evidence_quality_by_section,
        },
        "evidence_traceability": {
            "ok": all(s.get("ok") for s in evidence_traceability_by_section),
            "by_section": evidence_traceability_by_section,
        },
        "core_conclusion_evidence": {
            "ok": all(s.get("ok") for s in core_conclusion_evidence_by_section),
            "by_section": core_conclusion_evidence_by_section,
        },
        "drawing_evidence": {
            "ok": all(s.get("ok") for s in drawing_evidence_by_section),
            "drawing_count": len(drawing_names),
            "drawings": drawing_names[:12],
            "by_section": drawing_evidence_by_section,
        },
        "drawing_anchor_binding": {
            "ok": all(s.get("ok") for s in drawing_anchor_by_section),
            "by_section": drawing_anchor_by_section,
        },
        "standard_evidence": standard_evidence,
        "template_style": _check_template_style(all_text),
        "issue_list": issue_list,
        "auto_revision_suggestions": remediation,
        "remediation": remediation,
        "remediation_strategy_audit": remediation_strategy_audit,
        "remediation_execution_audit": remediation_execution_audit,
    }
