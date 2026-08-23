from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable


_ENGINEERING_TERMS = [
    "施工总平面",
    "总平面布置",
    "塔吊",
    "深基坑",
    "土方开挖",
    "基坑支护",
    "脚手架",
    "盘扣式脚手架",
    "模板支撑",
    "模板工程",
    "钢筋工程",
    "混凝土浇筑",
    "吊装作业",
    "临边防护",
    "临时用电",
    "防水施工",
    "屋面施工",
    "机电安装",
    "支模体系",
    "质量验收",
    "安全文明施工",
]
_CJK_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,16}")
_LATIN_RE = re.compile(r"[A-Za-z]")
_ALLOWED_OCR_CHAR_RE = re.compile(r"^[\u4e00-\u9fff0-9\s\-\—\(\)（）,.，。:：/%℃㎡m³、]+$")


def _dedup_keep_order(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def extract_semantic_image_terms(
    title: str,
    content: str,
    *,
    topic: str | None = None,
    limit: int = 6,
) -> list[str]:
    corpus = "\n".join([str(topic or ""), str(title or ""), str(content or "")])
    hits: list[str] = []
    for term in _ENGINEERING_TERMS:
        if term in corpus:
            hits.append(term)
    for token in _CJK_TOKEN_RE.findall(corpus):
        text = str(token or "").strip()
        if len(text) < 2:
            continue
        if any(marker in text for marker in ("施工", "工序", "工程", "基坑", "吊装", "脚手架", "混凝土", "钢筋", "模板", "防护", "平面")):
            hits.append(text)
    if not hits:
        hits.extend([str(title or "").strip(), str(topic or "").strip()])
    return _dedup_keep_order(hits)[: max(1, int(limit or 6))]


def contains_foreign_text(ocr_text: str | None) -> bool:
    text = str(ocr_text or "").strip()
    if not text:
        return False
    if _LATIN_RE.search(text):
        return True
    for line in text.splitlines():
        line = line.strip()
        if line and not _ALLOWED_OCR_CHAR_RE.match(line):
            return True
    return False


def _sha12(text: str) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8", errors="ignore")).hexdigest()[:12]


def _ensure_hd_image(path: str) -> str:
    img_path = Path(str(path or "")).expanduser()
    if not img_path.exists() or not img_path.is_file():
        return ""
    try:
        from backend.zhifei_autoplan.media_quality import validate_media_item

        receipt = validate_media_item({"path": str(img_path)})
        # Never upscale or crop an apparently low-resolution result and call it
        # HD.  Formal delivery accepts original, decodable assets only.
        return str(img_path) if receipt.get("ok") else ""
    except Exception:
        return ""


def _ocr_image_text(path: str) -> str:
    try:
        from PIL import Image
        import pytesseract
        from backend.zhifei_autoplan.ocr_runtime import guess_ocr_lang, is_tesseract_available
    except Exception:
        return ""
    if not is_tesseract_available():
        return ""
    img_path = Path(str(path or "")).expanduser()
    if not img_path.exists():
        return ""
    try:
        with Image.open(img_path) as im:
            return str(
                pytesseract.image_to_string(im, lang=guess_ocr_lang(prefer_chinese=True)) or ""
            ).strip()
    except Exception:
        return ""


def _build_generation_prompt(
    *,
    title: str,
    topic: str,
    query_terms: list[str],
    require_chinese_ocr_gate: bool,
) -> str:
    keyword_text = "、".join([str(x).strip() for x in query_terms if str(x).strip()][:6]) or str(title or "").strip()
    prompt = [
        "用于中国建设工程施工组织设计文档的专业插图。",
        f"项目主题：{str(topic or '').strip() or '施工组织设计'}。",
        f"章节标题：{str(title or '').strip() or '施工章节'}。",
        f"核心场景：{keyword_text}。",
        "风格要求：真实施工现场、工程技术表达、高清横版、适合 DOCX 插图。",
        "禁止卡通化、禁止夸张透视、禁止与施工无关的装饰性元素。",
    ]
    if require_chinese_ocr_gate:
        prompt.append(
            "若图中出现任何技术参数、安全标语、设备标注、流程标签或界面文字，必须全部为准确简体中文，严禁英文、拼音和其他外文字符。"
        )
    else:
        prompt.append("画面中不要出现任何可辨识的文字、字母、数字标牌或 UI 文本。")
    return "".join(prompt)


def build_semantic_image_item(
    *,
    title: str,
    content: str,
    topic: str,
    project_type: str | None = None,
    image_slots: list[Any] | None = None,
    workspace_dir: str | None = None,
) -> dict[str, Any] | None:
    from backend.zhifei_autoplan.media import generate_section_visuals
    from backend.zhifei_autoplan.media_quality import validate_media_item

    query_terms = extract_semantic_image_terms(title, content, topic=topic, limit=6)
    require_chinese_ocr_gate = True
    generation_attempts: list[dict[str, Any]] = []

    for slot in image_slots or []:
        provider = str(getattr(slot, "provider", "") or "").strip().lower()
        if provider not in {"openai", "google"}:
            continue
        api_key = str(getattr(slot, "api_key", "") or "").strip()
        if not api_key:
            continue
        try:
            from backend.zhifei_autoplan.image_runtime import generate_image

            prompt = _build_generation_prompt(
                title=title,
                topic=topic,
                query_terms=query_terms,
                require_chinese_ocr_gate=require_chinese_ocr_gate,
            )
            resp = generate_image(
                provider=provider,
                prompt=prompt,
                api_key=api_key,
                model=str(getattr(slot, "model", "") or "").strip() or None,
                aspect_ratio="16:9",
                out_dir=None,
            )
            paths = resp.get("paths") if isinstance(resp, dict) else []
            if not isinstance(paths, list) or not paths:
                generation_attempts.append(
                    {
                        "provider": provider,
                        "status": "failed",
                        "error": str((resp or {}).get("error") or "no_image_path") if isinstance(resp, dict) else "no_image_path",
                    }
                )
                continue
            source_path = _ensure_hd_image(paths[0])
            if not source_path:
                generation_attempts.append({"provider": provider, "status": "rejected", "error": "image_quality_gate_failed"})
                continue
            ocr_text = _ocr_image_text(source_path)
            if ocr_text and contains_foreign_text(ocr_text):
                generation_attempts.append({"provider": provider, "status": "rejected", "error": "foreign_text_detected"})
                continue
            caption = f"{str(title or '').strip() or '本章'}相关工程场景示意图"
            item = {
                "image_id": f"generated:{_sha12(source_path)}",
                "title": caption,
                "source_path": source_path,
                "storage_path": source_path,
                "caption": caption,
                "description": f"自动生成工程配图，关键词：{'、'.join(query_terms[:4])}",
                "tags": query_terms[:6],
                "chapter_scope": [str(title or "").strip()] if str(title or "").strip() else [],
                "process_scope": [],
                "matched_project_type": str(project_type or "").strip() or None,
                "source_mode": "semantic_generated",
                "provider": provider,
                "model": str(getattr(slot, 'model', '') or '').strip() or None,
                "ocr_text": ocr_text,
                "generation_attempts": generation_attempts + [{"provider": provider, "status": "accepted"}],
            }
            item["quality_receipt"] = validate_media_item(item, chapter_title=str(title or ""))
            return item
        except Exception as exc:
            generation_attempts.append({"provider": provider, "status": "failed", "error": type(exc).__name__})
            continue

    visuals = generate_section_visuals(
        title=title,
        content=content,
        image_count=1,
        include_mindmap=False,
    )
    if not visuals:
        return None
    first = visuals[0] if isinstance(visuals[0], dict) else {}
    source_path = _ensure_hd_image(str(first.get("path") or "").strip())
    caption = str(first.get("caption") or f"{str(title or '').strip()}相关工程示意图").strip()
    item = {
        "image_id": f"generated:{_sha12(source_path)}",
        "title": caption,
        "source_path": source_path,
        "storage_path": source_path,
        "caption": caption,
        "description": f"自动绘制工程示意图，关键词：{'、'.join(query_terms[:4])}",
        "tags": query_terms[:6],
        "chapter_scope": [str(title or "").strip()] if str(title or "").strip() else [],
        "process_scope": [],
        "matched_project_type": str(project_type or "").strip() or None,
        "source_mode": "deterministic_section_visual",
        "provider": "builtin",
        "model": "section_visuals",
        "ocr_text": "",
        "generation_attempts": generation_attempts + [{"provider": "builtin", "status": "accepted"}],
    }
    receipt = validate_media_item(item, chapter_title=str(title or ""))
    if not receipt.get("ok"):
        return None
    item["quality_receipt"] = receipt
    return item
