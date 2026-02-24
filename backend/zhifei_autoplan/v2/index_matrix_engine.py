from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from modules.parser.parser_unify import UnifiedParser

DEFAULT_INDEX_MATRIX_DIR = Path("backend/data/autoplan/v2")
DEFAULT_INDEX_MATRIX_PATH = DEFAULT_INDEX_MATRIX_DIR / "index_matrix.json"

DIMENSION_RULES: Dict[str, List[str]] = {
    "质量": ["质量", "验收", "合格", "缺陷", "平整度", "强度", "检验", "抽检", "试验"],
    "安全": ["安全", "危险", "防护", "应急", "事故", "临电", "高处", "消防", "培训"],
    "进度": ["工期", "进度", "节点", "里程碑", "关键线路", "计划", "穿插", "延误", "赶工"],
    "环保": ["环保", "扬尘", "噪声", "污水", "固废", "节能", "低碳", "绿色", "排放"],
    "重难点": ["重难点", "难点", "关键工序", "复杂", "深基坑", "大体积", "高风险", "控制点", "专项"],
    "扣分点": ["扣分", "否决", "废标", "处罚", "违约", "偏差", "不响应", "遗漏", "失分"],
}

DIMENSION_WEIGHTS: Dict[str, float] = {
    "质量": 0.22,
    "安全": 0.20,
    "进度": 0.20,
    "环保": 0.12,
    "重难点": 0.16,
    "扣分点": 0.10,
}


def _normalize_keywords(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        term = str(value or "").strip()
        if len(term) < 2:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def _semantic_chunks(text: str, *, max_chars: int = 680) -> List[Dict[str, Any]]:
    paragraphs = [line.strip() for line in re.split(r"\n{2,}", text or "") if line.strip()]
    chunks: List[Dict[str, Any]] = []
    carry: List[str] = []
    carry_len = 0

    def flush() -> None:
        nonlocal carry, carry_len
        if not carry:
            return
        body = "\n".join(carry).strip()
        if body:
            chunks.append({"id": len(chunks) + 1, "text": body, "size": len(body)})
        carry = []
        carry_len = 0

    for para in paragraphs:
        # heading-like lines become their own semantic chunk anchor.
        is_heading = bool(re.match(r"^(第[一二三四五六七八九十百零\d]+[章节篇]|[一二三四五六七八九十]+、|\d+[\.、])", para))
        if is_heading and carry:
            flush()
        if len(para) > max_chars:
            for i in range(0, len(para), max_chars):
                piece = para[i : i + max_chars]
                if carry_len + len(piece) > max_chars:
                    flush()
                carry.append(piece)
                carry_len += len(piece)
                flush()
            continue

        if carry_len + len(para) > max_chars:
            flush()
        carry.append(para)
        carry_len += len(para)

    flush()
    return chunks


def _is_qa_file(path: str, text: str) -> bool:
    markers = ("答疑", "澄清", "补遗", "变更", "答疑文件", "补充通知")
    name_hit = any(k in str(path) for k in markers)
    text_hit = any(k in (text or "") for k in markers)
    return bool(name_hit or text_hit)


def _extract_project_meta(text: str) -> Dict[str, str | None]:
    project_name = None
    project_code = None

    for line in (text or "").splitlines()[:900]:
        line = line.strip()
        if not line:
            continue
        if project_name is None:
            m = re.search(r"(?:项目名称|工程名称|标段名称)\s*[：:]\s*(.+)$", line)
            if m:
                project_name = m.group(1).strip()
        if project_code is None:
            m = re.search(r"(?:项目编号|招标编号|工程编号)\s*[：:]\s*([A-Za-z0-9_\-./\u4e00-\u9fff]+)", line)
            if m:
                project_code = m.group(1).strip()
        if project_name and project_code:
            break

    return {"project_name": project_name, "project_code": project_code}


class IndexMatrixEngine:
    """Tender parsing engine that produces legal-bounded Index_Matrix JSON."""

    async def parse_files(self, paths: List[str]) -> Dict[str, Any]:
        docs = await asyncio.gather(*[asyncio.to_thread(self._read_source_text, p) for p in paths])
        base_docs = [doc for doc in docs if not _is_qa_file(doc["path"], doc["text"])]
        qa_docs = [doc for doc in docs if _is_qa_file(doc["path"], doc["text"])]

        base_matrix = self._extract_matrix(base_docs, source_type="tender")
        qa_matrix = self._extract_matrix(qa_docs, source_type="qa") if qa_docs else None

        if qa_matrix:
            final = self._override_with_qa(base_matrix, qa_matrix)
        else:
            final = base_matrix

        merged_text = "\n\n".join((doc["text"] or "") for doc in docs)
        meta = _extract_project_meta(merged_text)
        final["project_name"] = meta.get("project_name")
        final["project_code"] = meta.get("project_code")
        final.setdefault("meta", {})
        final["meta"].update(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                "source_count": len(docs),
                "qa_source_count": len(qa_docs),
                "qa_override_applied": bool(qa_docs),
                "source_files": [doc["path"] for doc in docs],
            }
        )
        return final

    def _read_source_text(self, path: str) -> Dict[str, str]:
        p = Path(path)
        if not p.exists():
            return {"path": str(path), "text": ""}

        suffix = p.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".xml", ".json"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            return {"path": str(path), "text": text}

        try:
            parsed = UnifiedParser(str(p)).parse()
            text = parsed.get("text") or ""
            if not text and parsed.get("meta"):
                text = json.dumps(parsed.get("meta"), ensure_ascii=False)
            return {"path": str(path), "text": text}
        except Exception:
            return {"path": str(path), "text": ""}

    def _extract_matrix(self, docs: List[Dict[str, str]], *, source_type: str) -> Dict[str, Any]:
        matrix_items: List[Dict[str, Any]] = []
        if not docs:
            for dim, seeds in DIMENSION_RULES.items():
                matrix_items.append(
                    {
                        "dimension": dim,
                        "keywords": seeds[:4],
                        "weight": DIMENSION_WEIGHTS.get(dim, 0.1),
                        "source_type": source_type,
                        "support_chunks": [],
                    }
                )
            return {
                "index_matrix": matrix_items,
                "legal_boundary": {
                    "required_dimensions": list(DIMENSION_RULES.keys()),
                    "strict_mode": True,
                },
                "meta": {"chunks_total": 0},
            }

        all_chunks: List[Dict[str, Any]] = []
        for doc in docs:
            chunks = _semantic_chunks(doc.get("text") or "")
            for chunk in chunks:
                all_chunks.append({"path": doc.get("path"), **chunk})

        for dim, seeds in DIMENSION_RULES.items():
            hit_keywords: List[str] = []
            support_chunks: List[Dict[str, Any]] = []
            score = 0
            for chunk in all_chunks:
                ctext = chunk.get("text") or ""
                matched = [kw for kw in seeds if kw in ctext]
                if not matched:
                    continue
                score += len(matched)
                for kw in matched:
                    if kw not in hit_keywords:
                        hit_keywords.append(kw)
                support_chunks.append(
                    {
                        "chunk_id": chunk.get("id"),
                        "source_path": chunk.get("path"),
                        "matched_keywords": matched,
                        "excerpt": ctext[:220],
                    }
                )

            if not hit_keywords:
                hit_keywords = seeds[:4]

            weight = DIMENSION_WEIGHTS.get(dim, 0.1)
            if score > 0:
                weight = min(0.35, round(weight + min(0.10, score * 0.01), 4))

            matrix_items.append(
                {
                    "dimension": dim,
                    "keywords": _normalize_keywords(hit_keywords)[:12],
                    "weight": round(weight, 4),
                    "source_type": source_type,
                    "support_chunks": support_chunks[:8],
                }
            )

        return {
            "index_matrix": matrix_items,
            "legal_boundary": {
                "required_dimensions": list(DIMENSION_RULES.keys()),
                "strict_mode": True,
            },
            "meta": {"chunks_total": len(all_chunks)},
        }

    def _override_with_qa(self, base: Dict[str, Any], qa: Dict[str, Any]) -> Dict[str, Any]:
        qa_by_dim = {item["dimension"]: item for item in qa.get("index_matrix") or []}
        out_items: List[Dict[str, Any]] = []

        for item in base.get("index_matrix") or []:
            dim = item.get("dimension")
            qa_item = qa_by_dim.get(dim)
            if qa_item and qa_item.get("support_chunks"):
                out_items.append(
                    {
                        "dimension": dim,
                        "keywords": qa_item.get("keywords") or item.get("keywords") or [],
                        "weight": qa_item.get("weight") or item.get("weight"),
                        "source_type": "qa_override",
                        "support_chunks": qa_item.get("support_chunks") or [],
                        "override": {
                            "applied": True,
                            "base_keywords": item.get("keywords") or [],
                            "base_weight": item.get("weight"),
                        },
                    }
                )
            else:
                out_items.append(item)

        return {
            "index_matrix": out_items,
            "legal_boundary": base.get("legal_boundary") or {},
            "meta": {
                **(base.get("meta") or {}),
                "override_strategy": "qa_file_overrides_tender",
            },
        }


def save_index_matrix(matrix: Dict[str, Any], path: Path | str = DEFAULT_INDEX_MATRIX_PATH) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


async def build_index_matrix(paths: List[str], *, save_path: Path | str = DEFAULT_INDEX_MATRIX_PATH) -> Dict[str, Any]:
    engine = IndexMatrixEngine()
    matrix = await engine.parse_files(paths)
    saved_at = save_index_matrix(matrix, path=save_path)
    return {"ok": True, "matrix": matrix, "saved_at": saved_at}
