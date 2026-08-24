#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import pypdfium2 as pdfium
import pytesseract
from pypdf import PdfReader
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.getLogger("pypdf").setLevel(logging.ERROR)

from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.compliance_policy import canonical_standard_code
from modules.parser.parser_unify import UnifiedParser

STANDARD_CODE_RE_LIST = [
    re.compile(
        r"(?P<prefix>GB\s*/\s*T|GB/T|GB\s*[:：]\s*T|GB)\s*[-— ]?\s*(?P<num>\d{2,6})(?:[.\-－](?P<year>\d{2,4}))?",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<prefix>JTG)\s*[-— ]?(?P<num>[A-Z]?\s*\d{1,4})(?:[.\-－](?P<year>\d{2,4}))?", re.IGNORECASE),
    re.compile(r"(?P<prefix>SL)\s*[-— ]?(?P<num>\d{2,6})(?:[.\-－](?P<year>\d{2,4}))?", re.IGNORECASE),
    re.compile(r"(?P<prefix>JGJ)\s*[-— ]?(?P<num>\d{2,6})(?:[.\-－](?P<year>\d{2,4}))?", re.IGNORECASE),
    re.compile(r"(?P<prefix>DL/T|DL)\s*[-— ]?(?P<num>\d{2,6})(?:[.\-－](?P<year>\d{2,4}))?", re.IGNORECASE),
]
DOMAIN_SEEDS: Dict[str, Tuple[str, ...]] = {
    "水利水电": ("水利", "水电", "泵站", "闸门", "SL", "河道", "堤防"),
    "公路工程": ("公路", "JTG", "路基", "路面", "桥涵"),
    "房建工程": ("建筑", "施工质量", "住宅", "医院", "洁净", "幕墙"),
    "市政道路工程": ("市政道路", "道路交通", "道路工程", "交通工程"),
    "综合管廊": ("综合管廊", "管廊"),
    "BIM/数字化建造": ("BIM", "信息模型", "数字化", "数据中心"),
    "绿色建造": ("绿色施工", "节能", "环保", "低碳"),
    "消防工程": ("消防", "火灾", "灭火", "应急照明"),
}
WATERMARK_NOISE_WORDS = [
    "住房城乡建设部信息公开",
    "住房和城乡建设部信息公开",
    "中华人民共和国住房和城乡建设部",
    "信息公开",
    "住 房 城 乡 建 设 部 信 息 公 开",
]
ALLOWED_SUFFIXES = {".pdf", ".doc", ".docx", ".txt", ".md"}
OFFICIAL_METADATA_FIELDS = {
    "standard_name",
    "official_source",
    "effective_status",
    "current_version",
    "latest",
    "priority",
    "conflicts",
    "domain_tags",
    "verification_note",
    "verified_at",
    "superseded_clauses",
}


@dataclass
class FileResult:
    source_file: str
    ok: bool
    output_file: str = ""
    standard_code: str = ""
    prefix_tag: str = ""
    domain_tag: str = ""
    mandatory_count: int = 0
    parameter_count: int = 0
    chunk_count: int = 0
    skipped: bool = False
    source_sha256: str = ""
    source_size: int = 0
    source_mtime_ns: int = 0
    error: str = ""


def _normalize_line(text: str) -> str:
    s = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    s = re.sub(r"\u3000", " ", s)
    return s


def _safe_name(text: str, *, fallback_prefix: str = "standard") -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_\-]+", "_", str(text or "")).strip("_")
    if cleaned and not re.fullmatch(r"\d+", cleaned):
        return cleaned
    digest = hashlib.sha1(str(text or "").encode("utf-8", errors="ignore")).hexdigest()[:8]
    prefix = re.sub(r"[^0-9A-Za-z_\-]+", "_", fallback_prefix).strip("_") or "standard"
    return f"{prefix}_{digest}"


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _manifest_path(output_dir: Path) -> Path:
    return output_dir / "_ingest_manifest.json"


def _load_manifest(output_dir: Path) -> Dict[str, Any]:
    p = _manifest_path(output_dir)
    if not p.exists():
        return {"version": 1, "files": {}}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and isinstance(obj.get("files"), dict):
            return obj
    except Exception:
        pass
    return {"version": 1, "files": {}}


def _save_manifest(output_dir: Path, manifest: Dict[str, Any]) -> None:
    p = _manifest_path(output_dir)
    obj = {
        "version": 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "files": manifest.get("files") if isinstance(manifest.get("files"), dict) else {},
    }
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _source_key(path: Path) -> str:
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def _canonical_prefix(prefix: str) -> str:
    token = re.sub(r"[^A-Za-z/]", "", (prefix or "").upper())
    if token in {"GB/T", "GBT"}:
        return "GB/T"
    if token.startswith("GB"):
        return "GB"
    if token.startswith("JTG"):
        return "JTG"
    if token.startswith("SL"):
        return "SL"
    if token.startswith("JGJ"):
        return "JGJ"
    if token.startswith("DL"):
        return "DL"
    return "STD"


def _sniff_standard_code(file_name: str, text: str) -> Tuple[str, str]:
    candidates = [file_name, text[:24000]]
    for scope in candidates:
        for pattern in STANDARD_CODE_RE_LIST:
            m = pattern.search(scope or "")
            if not m:
                continue
            prefix = _canonical_prefix(m.group("prefix"))
            num = re.sub(r"\s+", "", str(m.group("num") or ""))
            year = str(m.group("year") or "").strip()
            if num:
                code = f"{prefix}_{num}_{year}" if year else f"{prefix}_{num}"
                return code, prefix
    stem = Path(file_name).stem
    return _safe_name(stem, fallback_prefix="STD").upper(), "STD"


def _sniff_domain_tag(file_name: str, text: str) -> str:
    merged = f"{file_name}\n{text[:24000]}"
    best_domain = "通用工程"
    best_score = 0
    for domain, seeds in DOMAIN_SEEDS.items():
        score = sum(1 for seed in seeds if seed and seed in merged)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain


def _official_metadata_sidecar_candidates(path: Path) -> List[Path]:
    """Return deterministic metadata sidecar locations without creating any file."""
    candidates = [
        path.with_name(path.name + ".metadata.json"),
        path.with_suffix(".metadata.json"),
    ]
    out: List[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def _load_official_metadata_sidecar(path: Path, *, standard_code: str) -> Dict[str, Any]:
    """Load explicit official metadata; never infer verification from document text.

    A sidecar must bind itself to the same standard code as the parsed source.
    Mismatched sidecars stop ingestion instead of granting the wrong document a
    verified identity.  Missing or incomplete sidecars remain unverified.
    """
    sidecar = next(
        (candidate for candidate in _official_metadata_sidecar_candidates(path) if candidate.is_file()),
        None,
    )
    if sidecar is None:
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_official_metadata_sidecar:{sidecar.name}:{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_official_metadata_sidecar:{sidecar.name}:object_required")
    raw = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else payload
    declared_code = str(raw.get("standard_code") or "").strip()
    if not declared_code:
        raise ValueError(f"invalid_official_metadata_sidecar:{sidecar.name}:standard_code_required")
    if canonical_standard_code(declared_code) != canonical_standard_code(standard_code):
        raise ValueError(
            "official_metadata_standard_code_mismatch:"
            f"{sidecar.name}:{declared_code}!={standard_code}"
        )
    out = {
        key: raw.get(key)
        for key in OFFICIAL_METADATA_FIELDS
        if key in raw and raw.get(key) not in (None, "", [])
    }
    out["official_metadata_sidecar"] = str(sidecar)
    return out


def _clean_watermark_noise(text: str) -> str:
    out = str(text or "")
    for token in WATERMARK_NOISE_WORDS:
        if token:
            out = out.replace(token, " ")
    for token in WATERMARK_NOISE_WORDS:
        spread = r"\s*".join([re.escape(ch) for ch in token if ch.strip()])
        if spread:
            out = re.sub(spread, " ", out, flags=re.IGNORECASE)
    lines = []
    for line in out.splitlines():
        raw = _normalize_line(line)
        if not raw:
            continue
        if any(token in raw for token in WATERMARK_NOISE_WORDS):
            continue
        lines.append(raw)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _text_quality_score(text: str) -> float:
    if not text:
        return 0.0
    cleaned = str(text)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
    digit_count = len(re.findall(r"\d", cleaned))
    bad_ratio = (cleaned.count("�") + cleaned.count("\x00")) / max(1, len(cleaned))
    return float(cjk_count * 1.0 + digit_count * 0.5 - bad_ratio * 400)


def _extract_with_pypdf(path: Path) -> Tuple[str, Dict[str, Any]]:
    reader = PdfReader(str(path))
    texts = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(texts), {"engine": "pypdf", "pages": len(reader.pages)}


def _extract_with_pdfplumber(path: Path) -> Tuple[str, Dict[str, Any]]:
    texts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
        pages = len(pdf.pages)
    return "\n\n".join(texts), {"engine": "pdfplumber", "pages": pages}


def _ocr_with_tesseract(path: Path, *, max_pages: int, dpi_zoom: float = 1.8) -> Tuple[str, Dict[str, Any]]:
    doc = pdfium.PdfDocument(str(path))
    pages = len(doc)
    pick_pages = min(max_pages, pages)
    texts: List[str] = []
    for i in range(pick_pages):
        page = doc[i]
        bitmap = page.render(scale=max(1.0, float(dpi_zoom)))
        img = bitmap.to_pil()
        txt = pytesseract.image_to_string(img, lang="chi_sim+eng", config="--psm 6")
        if txt:
            texts.append(txt)
        page.close()
        try:
            bitmap.close()
        except Exception:
            pass
    return "\n\n".join(texts), {"engine": "tesseract_ocr", "pages": pages, "ocr_pages": pick_pages}


def _parse_sync(path: Path, *, ocr_max_pages: int) -> Tuple[str, Dict[str, Any]]:
    if path.suffix.lower() != ".pdf":
        parsed = UnifiedParser(str(path)).parse()
        text = str(parsed.get("text") or "")
        meta = parsed.get("meta") if isinstance(parsed.get("meta"), dict) else {}
        return _clean_watermark_noise(text), {"engine": "unified_parser", **meta}

    candidates: List[Tuple[str, Dict[str, Any], float]] = []
    for fn in (_extract_with_pypdf, _extract_with_pdfplumber):
        try:
            text, meta = fn(path)
            clean = _clean_watermark_noise(text)
            candidates.append((clean, meta, _text_quality_score(clean)))
        except Exception:
            continue

    best_text = ""
    best_meta: Dict[str, Any] = {}
    best_score = -1.0
    for t, m, s in candidates:
        if s > best_score:
            best_text, best_meta, best_score = t, dict(m), s

    need_ocr = (best_score < 800.0) or (len(best_text) < 4000)
    if need_ocr:
        try:
            ocr_text, ocr_meta = _ocr_with_tesseract(path, max_pages=ocr_max_pages)
            ocr_clean = _clean_watermark_noise(ocr_text)
            ocr_score = _text_quality_score(ocr_clean)
            if ocr_score >= best_score or len(ocr_clean) > len(best_text):
                best_text = ocr_clean
                best_meta = {**best_meta, **ocr_meta, "selected_engine": "tesseract_ocr"}
                best_score = ocr_score
            else:
                best_meta["selected_engine"] = best_meta.get("engine", "pdf_parser")
        except Exception as exc:
            best_meta["ocr_error"] = repr(exc)

    best_meta["quality_score"] = round(best_score, 2)
    return best_text, best_meta


def _chunk_text(text: str, *, target_chars: int = 3600, overlap_chars: int = 360) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    lines = [line for line in raw.splitlines() if _normalize_line(line)]
    if not lines:
        return []

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for line in lines:
        ln = _normalize_line(line)
        if not ln:
            continue
        if cur_len + len(ln) + 1 > target_chars and cur:
            chunk = "\n".join(cur).strip()
            if chunk:
                chunks.append(chunk)
            if overlap_chars > 0:
                overlap: List[str] = []
                rev_len = 0
                for old in reversed(cur):
                    rev_len += len(old) + 1
                    overlap.append(old)
                    if rev_len >= overlap_chars:
                        break
                cur = list(reversed(overlap))
                cur_len = sum(len(x) + 1 for x in cur)
            else:
                cur = []
                cur_len = 0
        cur.append(ln)
        cur_len += len(ln) + 1

    if cur:
        chunk = "\n".join(cur).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _select_chunks(chunks: List[str], *, max_chunks: int) -> List[str]:
    if max_chunks <= 0 or len(chunks) <= max_chunks:
        return chunks
    if max_chunks <= 4:
        return chunks[:max_chunks]
    selected_idx = {0, 1, len(chunks) - 2, len(chunks) - 1}
    remain = max_chunks - len(selected_idx)
    if remain > 0:
        middle_start = 2
        middle_end = max(2, len(chunks) - 2)
        span = max(1, middle_end - middle_start)
        for i in range(remain):
            idx = middle_start + int((i + 0.5) * span / max(1, remain))
            idx = min(len(chunks) - 3, max(2, idx))
            selected_idx.add(idx)
    return [chunks[i] for i in sorted(selected_idx)[:max_chunks]]


class AsyncLLMRateLimiter:
    def __init__(self, *, min_interval_sec: float, max_tokens_per_minute: int):
        self.min_interval_sec = max(0.0, float(min_interval_sec))
        self.max_tokens_per_minute = max(1000, int(max_tokens_per_minute))
        self._lock = asyncio.Lock()
        self._last_call = 0.0
        self._window_start = time.monotonic()
        self._used_tokens = 0

    async def wait(self, token_estimate: int) -> None:
        tokens = max(1, int(token_estimate))
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._window_start
                if elapsed >= 60:
                    self._window_start = now
                    self._used_tokens = 0

                interval_wait = self.min_interval_sec - (now - self._last_call)
                token_wait = 0.0
                if self._used_tokens + tokens > self.max_tokens_per_minute:
                    token_wait = max(0.0, 60.0 - elapsed)

                wait_for = max(interval_wait, token_wait)
                if wait_for > 0:
                    pass
                else:
                    self._last_call = time.monotonic()
                    self._used_tokens += tokens
                    return
            await asyncio.sleep(min(2.0, max(0.02, wait_for)))


def _resolve_api_key(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p == "google":
        return (
            os.getenv("ZF_GOOGLE_API_KEY", "")
            or os.getenv("GOOGLE_API_KEY", "")
            or os.getenv("GEMINI_API_KEY", "")
        )
    if p == "openai":
        return os.getenv("ZF_OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if p == "grok":
        return os.getenv("ZF_GROK_API_KEY", "") or os.getenv("GROK_API_KEY", "") or os.getenv("XAI_API_KEY", "")
    return os.getenv("LLM_API_KEY", "")


def _build_chunk_prompt(*, file_name: str, standard_code: str, chunk_id: int, chunk_text: str) -> str:
    schema = {
        "clauses": [
            {
                "clause_no": "条款号或章节号",
                "text": "条文完整文本",
                "mandatory_level": "禁止类|要求类",
                "evidence_span": "原文短片段"
            }
        ],
        "parameters": [
            {
                "parameter_name": "参数名",
                "value": "数值",
                "unit": "单位",
                "operator": ">=|<=|>|<|=|约",
                "clause_no": "来源条款号",
                "context": "参数所在原文句"
            }
        ],
        "watermark_removed": True
    }
    return (
        "你是工程规范结构化解析专家，请执行深度阅读并输出严格JSON。\n"
        "硬性规则：\n"
        "1) 请自动忽略并剔除文本与表格中混入的“住房城乡建设部信息公开”等水印干扰词，"
        "确保工程真实数值（如：抽检比例、允许偏差、搭接长度）的完整提取，并转化为parameter节点。\n"
        "2) clauses 仅保留‘必须/应当/不得/严禁/禁止’等强制性条文，不要摘要。\n"
        "3) parameters 必须是‘有明确数值+单位’的工程参数；若来自表格也要提取。\n"
        "4) 不允许输出空字段，不允许输出解释文字，不允许markdown。\n"
        f"5) source 一律视为 llm（无需输出source字段）。\n\n"
        f"文件名: {file_name}\n"
        f"规范编号: {standard_code}\n"
        f"Chunk: {chunk_id}\n\n"
        f"输出JSON模板:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"待解析文本:\n{chunk_text}"
    )


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def _clean_clause_item(item: Dict[str, Any], *, chunk_id: int) -> Optional[Dict[str, Any]]:
    clause_no = _normalize_line(str(item.get("clause_no") or ""))
    text = _normalize_line(str(item.get("text") or ""))
    if len(text) < 8:
        return None
    for token in WATERMARK_NOISE_WORDS:
        text = text.replace(token, "")
    text = _normalize_line(text)
    if len(text) < 8:
        return None
    level = _normalize_line(str(item.get("mandatory_level") or "要求类"))
    if not level:
        level = "要求类"
    if any(x in text for x in ("不得", "严禁", "禁止")):
        level = "禁止类"
    return {
        "clause_no": clause_no,
        "text": text[:320],
        "mandatory_level": level,
        "source": "llm",
        "chunk_id": chunk_id,
        "evidence_span": _normalize_line(str(item.get("evidence_span") or text[:120])),
    }


def _clean_parameter_item(item: Dict[str, Any], *, chunk_id: int) -> Optional[Dict[str, Any]]:
    name = _normalize_line(str(item.get("parameter_name") or ""))
    value = _normalize_line(str(item.get("value") or ""))
    unit = _normalize_line(str(item.get("unit") or ""))
    op = _normalize_line(str(item.get("operator") or ""))
    clause_no = _normalize_line(str(item.get("clause_no") or ""))
    context = _normalize_line(str(item.get("context") or ""))

    if not value or not unit:
        return None
    if not re.search(r"\d", value):
        return None
    for token in WATERMARK_NOISE_WORDS:
        context = context.replace(token, "")
        name = name.replace(token, "")
    context = _normalize_line(context)
    name = _normalize_line(name) or "未命名参数"
    return {
        "parameter_name": name[:80],
        "value": value[:30],
        "unit": unit[:20],
        "operator": op[:5],
        "clause_no": clause_no[:40],
        "context": context[:260],
        "source": "llm",
        "chunk_id": chunk_id,
    }


async def _llm_extract_chunk(
    *,
    llm_client: LLMClient,
    llm_semaphore: asyncio.Semaphore,
    llm_limiter: AsyncLLMRateLimiter,
    llm_retries: int,
    prompt: str,
    chunk_id: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    last_error = "unknown"
    token_est = max(256, math.ceil(len(prompt) / 3))

    for attempt in range(1, llm_retries + 1):
        async with llm_semaphore:
            await llm_limiter.wait(token_est)
            resp = await llm_client.complete(prompt, temperature=0, timeout_sec=120)

        err = _normalize_line(str(resp.get("error") or ""))
        if err:
            last_error = err
        else:
            payload = _extract_json_object(str(resp.get("text") or ""))
            if isinstance(payload, dict):
                raw_clauses = payload.get("clauses") if isinstance(payload.get("clauses"), list) else []
                raw_params = payload.get("parameters") if isinstance(payload.get("parameters"), list) else []

                clauses: List[Dict[str, Any]] = []
                params: List[Dict[str, Any]] = []
                for x in raw_clauses:
                    if not isinstance(x, dict):
                        continue
                    cleaned = _clean_clause_item(x, chunk_id=chunk_id)
                    if cleaned:
                        clauses.append(cleaned)
                for x in raw_params:
                    if not isinstance(x, dict):
                        continue
                    cleaned = _clean_parameter_item(x, chunk_id=chunk_id)
                    if cleaned:
                        params.append(cleaned)
                return clauses, params, ""
            last_error = "invalid_json_output"

        if attempt < llm_retries:
            await asyncio.sleep(min(10.0, 1.3**attempt + random.random() * 0.8))

    return [], [], last_error


def _dedupe_clauses(items: List[Dict[str, Any]], *, max_items: int = 1800) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for x in items:
        key = _normalize_line(str(x.get("text") or ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(x)
        if len(out) >= max_items:
            break
    return out


def _dedupe_parameters(items: List[Dict[str, Any]], *, max_items: int = 4000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for x in items:
        key = "|".join(
            [
                _normalize_line(str(x.get("parameter_name") or "")),
                _normalize_line(str(x.get("value") or "")),
                _normalize_line(str(x.get("unit") or "")),
                _normalize_line(str(x.get("context") or "")),
            ]
        )
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(x)
        if len(out) >= max_items:
            break
    for i, x in enumerate(out, start=1):
        x["parameter_id"] = f"P{i:04d}"
    return out


async def _process_one_file(
    path: Path,
    *,
    output_dir: Path,
    semaphore: asyncio.Semaphore,
    parse_executor: ThreadPoolExecutor,
    llm_client: LLMClient,
    llm_semaphore: asyncio.Semaphore,
    llm_limiter: AsyncLLMRateLimiter,
    llm_retries: int,
    ocr_max_pages: int,
    max_chunks_per_file: int,
) -> FileResult:
    async with semaphore:
        try:
            try:
                st = path.stat()
                source_size = int(st.st_size)
                source_mtime_ns = int(st.st_mtime_ns)
            except Exception:
                source_size = 0
                source_mtime_ns = 0
            loop = asyncio.get_running_loop()
            text, parse_meta = await loop.run_in_executor(parse_executor, lambda: _parse_sync(path, ocr_max_pages=ocr_max_pages))
            if not text or len(text.strip()) < 300:
                raise ValueError("empty_text_after_parse")

            standard_code, prefix_tag = _sniff_standard_code(path.name, text)
            domain_tag = _sniff_domain_tag(path.name, text)
            official_metadata = _load_official_metadata_sidecar(
                path,
                standard_code=standard_code,
            )
            chunks_all = _chunk_text(text, target_chars=3600, overlap_chars=360)
            chunks = _select_chunks(chunks_all, max_chunks=max_chunks_per_file)
            if not chunks:
                raise ValueError("chunking_failed")

            all_clauses: List[Dict[str, Any]] = []
            all_params: List[Dict[str, Any]] = []
            llm_errors: List[str] = []

            for i, chunk in enumerate(chunks, start=1):
                prompt = _build_chunk_prompt(file_name=path.name, standard_code=standard_code, chunk_id=i, chunk_text=chunk)
                clauses, params, err = await _llm_extract_chunk(
                    llm_client=llm_client,
                    llm_semaphore=llm_semaphore,
                    llm_limiter=llm_limiter,
                    llm_retries=llm_retries,
                    prompt=prompt,
                    chunk_id=i,
                )
                all_clauses.extend(clauses)
                all_params.extend(params)
                if err:
                    llm_errors.append(f"chunk{i}:{err}")

            all_clauses = _dedupe_clauses(all_clauses)
            all_params = _dedupe_parameters(all_params)
            if not all_clauses:
                raise ValueError(f"llm_no_clauses_extracted errors={','.join(llm_errors[:5])}")

            # Stable output naming by source path hash to avoid uncontrolled file growth.
            src_tag = hashlib.sha1(_source_key(path).encode("utf-8", errors="ignore")).hexdigest()[:8]
            output_path = output_dir / f"SRC_{src_tag}_compliance.json"

            nodes: List[Dict[str, Any]] = []
            for idx, clause in enumerate(all_clauses, start=1):
                nodes.append(
                    {
                        "node_id": f"{standard_code}#C{idx:04d}",
                        "node_type": "ComplianceClause",
                        "track": "compliance",
                        "domain_tag": domain_tag,
                        "prefix_tag": prefix_tag,
                        "standard_code": standard_code,
                        "clause_no": clause.get("clause_no") or "",
                        "mandatory_level": clause.get("mandatory_level") or "要求类",
                        "text": clause.get("text") or "",
                        "source": "llm",
                        "chunk_id": clause.get("chunk_id"),
                        "evidence_span": clause.get("evidence_span") or "",
                    }
                )

            source_metadata = {
                "source_file": str(path),
                "source_name": path.name,
                "standard_code": standard_code,
                "prefix_tag": prefix_tag,
                "domain_tag": domain_tag,
                "parser_meta": parse_meta,
                "watermark_cleaning_enabled": True,
                "llm_enhanced": True,
                "llm_errors": llm_errors,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            }
            # Only explicit sidecar fields may elevate a parsed document to
            # verified status.  Text extraction/model output never does.
            source_metadata.update(official_metadata)
            payload = {
                "graph_track": "compliance",
                "metadata": source_metadata,
                "stats": {
                    "mandatory_count": len(nodes),
                    "parameter_count": len(all_params),
                    "chunk_count": len(chunks),
                    "chunk_total": len(chunks_all),
                },
                "nodes": nodes,
                "parameters": all_params,
            }
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            source_sha256 = _sha256_file(path)
            return FileResult(
                source_file=str(path),
                ok=True,
                output_file=str(output_path),
                standard_code=standard_code,
                prefix_tag=prefix_tag,
                domain_tag=domain_tag,
                mandatory_count=len(nodes),
                parameter_count=len(all_params),
                chunk_count=len(chunks),
                source_sha256=source_sha256,
                source_size=source_size,
                source_mtime_ns=source_mtime_ns,
            )
        except Exception as exc:
            try:
                st = path.stat()
                source_size = int(st.st_size)
                source_mtime_ns = int(st.st_mtime_ns)
            except Exception:
                source_size = 0
                source_mtime_ns = 0
            return FileResult(
                source_file=str(path),
                ok=False,
                error=repr(exc),
                source_size=source_size,
                source_mtime_ns=source_mtime_ns,
            )


def _pick_input_files(input_dir: Path, *, limit: Optional[int], sample_seed: int, recursive: bool = True) -> List[Path]:
    if recursive:
        files = sorted(
            [
                p
                for p in input_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES and "/." not in str(p)
            ]
        )
    else:
        files = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES])
    if limit is None or limit <= 0 or limit >= len(files):
        return files
    rnd = random.Random(sample_seed)
    return sorted(rnd.sample(files, k=limit), key=lambda x: x.name)


async def run_pipeline(
    *,
    input_dir: Path,
    output_dir: Path,
    max_workers: int,
    llm_workers: int,
    llm_provider: str,
    llm_model: str,
    llm_retries: int,
    llm_min_interval: float,
    llm_max_tokens_per_minute: int,
    ocr_max_pages: int,
    limit: Optional[int],
    sample_seed: int,
    max_chunks_per_file: int,
    force_reindex: bool,
    recursive: bool,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_files = _pick_input_files(input_dir, limit=limit, sample_seed=sample_seed, recursive=recursive)
    manifest = _load_manifest(output_dir)
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    if not isinstance(manifest_files, dict):
        manifest_files = {}
    current_keys = {_source_key(p) for p in all_files}
    # Prune deleted files from manifest to keep index stable over time.
    for k in list(manifest_files.keys()):
        if k not in current_keys:
            manifest_files.pop(k, None)

    files: List[Path] = []
    skipped_results: List[FileResult] = []
    for p in all_files:
        key = _source_key(p)
        rec = manifest_files.get(key) if isinstance(manifest_files.get(key), dict) else {}
        try:
            st = p.stat()
            size = int(st.st_size)
            mtime_ns = int(st.st_mtime_ns)
        except Exception:
            size = 0
            mtime_ns = 0
        output_file = str(rec.get("output_file") or "").strip()
        output_ok = bool(output_file and Path(output_file).exists())
        unchanged = (
            (not force_reindex)
            and bool(rec)
            and int(rec.get("source_size") or -1) == size
            and int(rec.get("source_mtime_ns") or -2) == mtime_ns
            and output_ok
        )
        if unchanged:
            skipped_results.append(
                FileResult(
                    source_file=str(p),
                    ok=True,
                    output_file=output_file,
                    standard_code=str(rec.get("standard_code") or ""),
                    prefix_tag=str(rec.get("prefix_tag") or ""),
                    domain_tag=str(rec.get("domain_tag") or ""),
                    mandatory_count=int(rec.get("mandatory_count") or 0),
                    parameter_count=int(rec.get("parameter_count") or 0),
                    chunk_count=int(rec.get("chunk_count") or 0),
                    skipped=True,
                    source_sha256=str(rec.get("source_sha256") or ""),
                    source_size=size,
                    source_mtime_ns=mtime_ns,
                )
            )
            continue
        files.append(p)

    parse_sem = asyncio.Semaphore(max(1, max_workers))
    parse_executor = ThreadPoolExecutor(max_workers=max(1, max_workers))
    llm_semaphore = asyncio.Semaphore(max(1, llm_workers))
    llm_limiter = AsyncLLMRateLimiter(
        min_interval_sec=llm_min_interval,
        max_tokens_per_minute=llm_max_tokens_per_minute,
    )

    api_key = _resolve_api_key(llm_provider)
    if not api_key:
        raise RuntimeError("LLM强制模式已启用，但未找到API Key（需设置ZF_GOOGLE_API_KEY/GOOGLE_API_KEY/GEMINI_API_KEY）")
    llm_client = LLMClient(provider=llm_provider, model=llm_model, api_key=api_key)
    if getattr(llm_client, "_impl", None) is None:
        raise RuntimeError(f"LLM客户端初始化失败: {getattr(llm_client, '_init_error', 'unknown')}")

    tasks = [
        asyncio.create_task(
            _process_one_file(
                path,
                output_dir=output_dir,
                semaphore=parse_sem,
                parse_executor=parse_executor,
                llm_client=llm_client,
                llm_semaphore=llm_semaphore,
                llm_limiter=llm_limiter,
                llm_retries=llm_retries,
                ocr_max_pages=ocr_max_pages,
                max_chunks_per_file=max_chunks_per_file,
            )
        )
        for path in files
    ]

    results: List[FileResult] = list(skipped_results)
    pbar = tqdm(total=len(tasks), desc="规范LLM深度入库", unit="file", ncols=130)
    try:
        for fut in asyncio.as_completed(tasks):
            result = await fut
            results.append(result)
            name = Path(result.source_file).name
            if result.ok:
                pbar.set_description(
                    f"正在解析: {name[:32]}... 强条:{result.mandatory_count} 参数:{result.parameter_count}"
                )
            else:
                pbar.set_description(f"解析失败: {name[:32]}...")
            pbar.update(1)
    finally:
        pbar.close()
        parse_executor.shutdown(wait=True)

    success = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    skipped_count = len([r for r in results if r.skipped])
    error_log_path = output_dir / "_ingest_errors.jsonl"
    if failed:
        with error_log_path.open("w", encoding="utf-8") as f:
            for item in failed:
                f.write(json.dumps({"source_file": item.source_file, "error": item.error}, ensure_ascii=False) + "\n")

    # Update manifest from processed + skipped results.
    for item in results:
        key = _source_key(Path(item.source_file))
        manifest_files[key] = {
            "source_file": item.source_file,
            "output_file": item.output_file,
            "standard_code": item.standard_code,
            "prefix_tag": item.prefix_tag,
            "domain_tag": item.domain_tag,
            "mandatory_count": int(item.mandatory_count or 0),
            "parameter_count": int(item.parameter_count or 0),
            "chunk_count": int(item.chunk_count or 0),
            "source_sha256": item.source_sha256,
            "source_size": int(item.source_size or 0),
            "source_mtime_ns": int(item.source_mtime_ns or 0),
            "ok": bool(item.ok),
            "error": item.error or "",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
    manifest["files"] = manifest_files
    _save_manifest(output_dir, manifest)

    # Build retrieval catalog for fast runtime pre-filter.
    catalog_summary: Dict[str, Any] = {}
    try:
        from backend.zhifei_autoplan.compliance_runtime import build_compliance_catalog

        catalog = build_compliance_catalog(output_dir)
        catalog_summary = {
            "catalog_count": int(catalog.get("count") or 0),
            "catalog_file": str((output_dir / "_catalog.json")),
        }
    except Exception as exc:
        catalog_summary = {"catalog_error": repr(exc)}

    summary = {
        "ok": True,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "total": len(results),
        "candidates": len(all_files),
        "processed": len(files),
        "skipped_unchanged": skipped_count,
        "success": len(success),
        "failed": len(failed),
        "llm_enabled": True,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "limit": limit or 0,
        "force_reindex": bool(force_reindex),
        "recursive": bool(recursive),
        "sample_seed": sample_seed,
        "error_log": str(error_log_path) if failed else "",
        **catalog_summary,
        "results": [r.__dict__ for r in results],
    }
    (output_dir / "_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _pick_sample_output_with_parameters(summary: Dict[str, Any]) -> Optional[Path]:
    for item in summary.get("results") or []:
        if item.get("ok") and int(item.get("parameter_count") or 0) > 0:
            return Path(str(item["output_file"]))
    for item in summary.get("results") or []:
        if item.get("ok") and item.get("output_file"):
            return Path(str(item["output_file"]))
    return None


async def _amain(args: argparse.Namespace) -> int:
    summary = await run_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        llm_workers=args.llm_workers,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_retries=args.llm_retries,
        llm_min_interval=args.llm_min_interval,
        llm_max_tokens_per_minute=args.llm_max_tokens_per_minute,
        ocr_max_pages=args.ocr_max_pages,
        limit=args.limit,
        sample_seed=args.sample_seed,
        max_chunks_per_file=args.max_chunks_per_file,
        force_reindex=bool(args.force_reindex),
        recursive=bool(args.recursive),
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, indent=2))
    sample = _pick_sample_output_with_parameters(summary)
    if sample and sample.exists():
        print(f"SAMPLE_OUTPUT={sample}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="规范摄入与清洗流水线（LLM深度阅读 + 水印脱敏 + 限流重试）")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/Users/youfeini/Desktop/文档生成系统/02_规范测试入库"),
        help="规范源文件目录",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/Users/youfeini/Desktop/文档生成系统/knowledge_graph/compliance"),
        help="compliance 轨道输出目录",
    )
    parser.add_argument("--max-workers", type=int, default=2, help="文件解析并发数")
    parser.add_argument("--llm-workers", type=int, default=2, help="LLM并发数")
    parser.add_argument("--llm-provider", type=str, default=os.getenv("ZF_STANDARD_LLM_PROVIDER", "google"))
    parser.add_argument("--llm-model", type=str, default=os.getenv("ZF_STANDARD_LLM_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--llm-retries", type=int, default=4, help="LLM重试次数")
    parser.add_argument("--llm-min-interval", type=float, default=1.8, help="LLM最小调用间隔（秒）")
    parser.add_argument("--llm-max-tokens-per-minute", type=int, default=120000, help="LLM每分钟估算Token上限")
    parser.add_argument("--ocr-max-pages", type=int, default=24, help="每个PDF最多OCR页数")
    parser.add_argument("--max-chunks-per-file", type=int, default=10, help="每份规范最多送入LLM的Chunk数量")
    parser.add_argument("--limit", type=int, default=0, help="灰度测试抽样数量（0表示全量）")
    parser.add_argument("--sample-seed", type=int, default=20260226, help="抽样随机种子")
    parser.add_argument("--force-reindex", action="store_true", help="强制全量重建（忽略增量manifest）")
    parser.add_argument("--recursive", action="store_true", default=True, help="递归扫描输入目录（默认开启）")
    parser.add_argument("--no-recursive", dest="recursive", action="store_false", help="仅扫描输入目录第一层文件")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        print(f"输入目录不存在: {args.input_dir}")
        return 2
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
