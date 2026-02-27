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
    "质量": [
        "质量",
        "验收",
        "合格",
        "缺陷",
        "平整度",
        "强度",
        "检验",
        "抽检",
        "试验",
        "一次验收合格率",
        "复检",
        "首件",
        "样板",
        "质量通病",
        "成品保护",
    ],
    "安全": [
        "安全",
        "危险",
        "防护",
        "应急",
        "事故",
        "临电",
        "高处",
        "消防",
        "培训",
        "危大工程",
        "脚手架",
        "吊装",
        "动火",
        "隐患",
        "安全交底",
    ],
    "进度": [
        "工期",
        "进度",
        "节点",
        "里程碑",
        "关键线路",
        "计划",
        "穿插",
        "延误",
        "赶工",
        "总工期",
        "倒排",
        "流水段",
        "月计划",
        "周计划",
        "资源配置",
    ],
    "环保": [
        "环保",
        "扬尘",
        "噪声",
        "污水",
        "固废",
        "节能",
        "低碳",
        "绿色",
        "排放",
        "PM10",
        "TSP",
        "泥浆",
        "水土保持",
        "在线监测",
        "弃土",
    ],
    "重难点": [
        "重难点",
        "难点",
        "关键工序",
        "复杂",
        "深基坑",
        "大体积",
        "高风险",
        "控制点",
        "专项",
        "高支模",
        "双曲面",
        "超长结构",
        "大跨度",
        "临近营业线",
    ],
    "扣分点": [
        "扣分",
        "否决",
        "废标",
        "处罚",
        "违约",
        "偏差",
        "不响应",
        "遗漏",
        "失分",
        "一票否决",
        "扣罚",
        "信用扣分",
        "未按时",
        "未报审",
        "红线",
    ],
}

DIMENSION_WEIGHTS: Dict[str, float] = {
    "质量": 0.22,
    "安全": 0.20,
    "进度": 0.20,
    "环保": 0.12,
    "重难点": 0.16,
    "扣分点": 0.10,
}

DOMAIN_SNIFFER_RULES: Dict[str, List[str]] = {
    "房建工程": ["房建", "主体结构", "砌体", "二次结构", "幕墙", "装配式"],
    "装修工程": ["装修", "装饰", "精装修", "吊顶", "墙面", "地面"],
    "市政道路工程": ["市政道路", "道路工程", "路基", "路面", "沥青", "交通导改"],
    "市政桥梁工程": ["市政桥梁", "桥梁", "箱梁", "盖梁", "桥墩", "挂篮"],
    "市政排水工程": ["市政排水", "雨污", "雨水", "污水", "排水管网", "检查井"],
    "市政燃气工程": ["燃气", "燃气管线", "调压", "燃气阀井", "中压", "次高压"],
    "河道治理": ["河道", "护岸", "清淤", "堤防", "驳岸", "水生态"],
    "水利水电": ["水利", "水电", "泵站", "闸门", "引水", "泄洪"],
    "公路工程": ["公路", "高速", "互通", "服务区", "路基路面", "隧道"],
    "机电安装": ["机电", "电气", "暖通", "消防", "弱电", "智能化"],
    "绿色建造": ["绿色建造", "绿色施工", "双碳", "节能减排", "扬尘治理", "环保"],
    "BIM/数字化建造": ["BIM", "数字化建造", "智慧工地", "数字孪生", "三维建模", "信息化管理"],
    "深基坑工程(危大)": ["深基坑", "支护", "降水", "危大工程", "监测点", "变形监测"],
}

MANDATORY_MARKERS: Tuple[str, ...] = (
    "必须",
    "应当",
    "应",
    "需",
    "不得",
    "严禁",
    "禁止",
    "确保",
    "shall",
)

KEYWORD_STOPWORDS = {
    "项目",
    "工程",
    "施工",
    "要求",
    "条款",
    "本工程",
    "本项目",
    "应当",
    "必须",
    "不得",
    "进行",
    "落实",
    "执行",
    "管理",
    "措施",
    "内容",
    "标准",
    "规范",
    "相关",
    "以及",
    "其中",
    "负责",
    "完成",
    "工作",
}

HEADING_RE = re.compile(r"^(第[一二三四五六七八九十百零\d]+[章节篇]|[一二三四五六七八九十]+、|\d+[\.、])")
SENTENCE_SPLIT_RE = re.compile(r"[。\n；;!?！？]+")
CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,16}")
MIXED_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-./%]{1,24}")
NUMERIC_TERM_RE = re.compile(
    r"\d+(?:\.\d+)?(?:%|‰|dB|MPa|kPa|mm|cm|m|km|天|h|小时|分钟|min|次/日|次/班|次|m3|m²|m2|t|kg|ug/m3|μg/m3)?"
)


def _sniff_involved_domains(text: str, matrix_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    matrix_terms: List[str] = []
    for item in matrix_items:
        matrix_terms.extend([str(x) for x in (item.get("keywords") or []) if str(x).strip()])
        for chunk in item.get("support_chunks") or []:
            if isinstance(chunk, dict):
                matrix_terms.extend([str(x) for x in (chunk.get("matched_keywords") or []) if str(x).strip()])
                matrix_terms.extend([str(x) for x in (chunk.get("semantic_tags") or []) if str(x).strip()])
    corpus = f"{text}\n" + "\n".join(matrix_terms)

    ranked: List[Tuple[str, float, List[str]]] = []
    for domain, seeds in DOMAIN_SNIFFER_RULES.items():
        hits = [seed for seed in seeds if seed and seed in corpus]
        if not hits:
            continue
        density = len(hits) / max(len(seeds), 1)
        score = round(min(1.0, 0.55 + density * 0.45), 4)
        ranked.append((domain, score, hits))

    ranked.sort(key=lambda x: (x[1], len(x[2]), len(x[0])), reverse=True)
    involved_domains = [x[0] for x in ranked]
    confidence = {x[0]: x[1] for x in ranked}
    evidence = {x[0]: x[2][:8] for x in ranked}
    return {
        "involved_domains": involved_domains,
        "confidence": confidence,
        "evidence": evidence,
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


def _normalize_term(value: str) -> str:
    term = re.sub(r"^[\s:：，,。；;、\[\]（）(){}]+|[\s:：，,。；;、\[\]（）(){}]+$", "", str(value or "").strip())
    return term


def _candidate_terms(sentence: str) -> List[str]:
    terms: List[str] = []
    for pattern in (NUMERIC_TERM_RE, MIXED_TERM_RE, CHINESE_TERM_RE):
        for match in pattern.finditer(sentence):
            term = _normalize_term(match.group(0))
            if len(term) < 2:
                continue
            if term in KEYWORD_STOPWORDS:
                continue
            terms.append(term)
    return _normalize_keywords(terms)


def _chunk_semantic_tags(text: str) -> List[str]:
    tags: List[str] = []
    for dim, seeds in DIMENSION_RULES.items():
        if any(seed in text for seed in seeds):
            tags.append(dim)
    return tags


def _dimension_sentence_terms(text: str, dimension: str) -> List[str]:
    seeds = DIMENSION_RULES.get(dimension, [])
    terms: List[str] = []
    for sentence in SENTENCE_SPLIT_RE.split(text or ""):
        sentence = sentence.strip()
        if not sentence:
            continue
        if any(seed in sentence for seed in seeds):
            terms.extend(_candidate_terms(sentence))
    return _normalize_keywords(terms)


def _score_to_weight(
    base_weight: float,
    raw_score: float,
    *,
    total_chunks: int,
    hit_chunks: int,
    mandatory_hits: int,
) -> float:
    coverage = hit_chunks / max(total_chunks, 1)
    score_factor = min(0.12, raw_score * 0.004)
    coverage_factor = min(0.10, coverage * 0.10)
    mandatory_factor = min(0.06, mandatory_hits * 0.008)
    weight = base_weight + score_factor + coverage_factor + mandatory_factor
    return round(min(0.50, max(base_weight * 0.60, weight)), 4)


def _semantic_chunks(text: str, *, max_chars: int = 680) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    chunks: List[Dict[str, Any]] = []
    carry: List[str] = []
    carry_len = 0
    current_heading = "正文"
    section_index = 0

    def flush() -> None:
        nonlocal carry, carry_len
        if not carry:
            return
        body = "\n".join(carry).strip()
        if body:
            chunks.append(
                {
                    "id": len(chunks) + 1,
                    "text": body,
                    "size": len(body),
                    "section_title": current_heading,
                    "section_index": section_index,
                    "semantic_tags": _chunk_semantic_tags(body),
                }
            )
        carry = []
        carry_len = 0

    for line in lines:
        if HEADING_RE.match(line):
            flush()
            section_index += 1
            current_heading = line[:120]
            continue

        pieces = [part.strip() for part in re.split(r"(?<=[。；;!?！？])", line) if part.strip()]
        if not pieces:
            pieces = [line]

        for piece in pieces:
            if len(piece) > max_chars:
                for i in range(0, len(piece), max_chars):
                    block = piece[i : i + max_chars]
                    if carry_len + len(block) > max_chars:
                        flush()
                    carry.append(block)
                    carry_len += len(block)
                    flush()
                continue

            if carry_len + len(piece) > max_chars:
                flush()
            carry.append(piece)
            carry_len += len(piece)

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
        sniffer = _sniff_involved_domains(merged_text, final.get("index_matrix") or [])
        final["project_name"] = meta.get("project_name")
        final["project_code"] = meta.get("project_code")
        final["involved_domains"] = sniffer.get("involved_domains") or []
        final.setdefault("meta", {})
        final["meta"].update(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                "source_count": len(docs),
                "qa_source_count": len(qa_docs),
                "qa_override_applied": bool(qa_docs),
                "source_files": [doc["path"] for doc in docs],
                "involved_domains_confidence": sniffer.get("confidence") or {},
                "involved_domains_evidence": sniffer.get("evidence") or {},
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
                        "keywords": seeds[:6],
                        "weight": DIMENSION_WEIGHTS.get(dim, 0.1),
                        "score": 0.0,
                        "source_type": source_type,
                        "signals": {
                            "hit_chunks": 0,
                            "coverage": 0.0,
                            "mandatory_hits": 0,
                            "keyword_count": min(6, len(seeds)),
                        },
                        "support_chunks": [],
                    }
                )
            return {
                "index_matrix": matrix_items,
                "legal_boundary": {
                    "required_dimensions": list(DIMENSION_RULES.keys()),
                    "strict_mode": True,
                },
                "meta": {"chunks_total": 0, "semantic_sections_total": 0, "keyword_candidates_total": 0},
            }

        all_chunks: List[Dict[str, Any]] = []
        for doc in docs:
            chunks = _semantic_chunks(doc.get("text") or "")
            for chunk in chunks:
                all_chunks.append({"path": doc.get("path"), **chunk})

        keyword_candidates_total = 0
        for dim, seeds in DIMENSION_RULES.items():
            hit_keywords: List[str] = []
            support_chunks: List[Dict[str, Any]] = []
            raw_score = 0.0
            hit_chunk_count = 0
            mandatory_hits = 0

            for chunk in all_chunks:
                ctext = chunk.get("text") or ""
                matched = [kw for kw in seeds if kw in ctext]
                semantic_tags = [str(x) for x in (chunk.get("semantic_tags") or [])]
                if not matched and dim not in semantic_tags:
                    continue

                hit_chunk_count += 1
                sentence_terms = _dimension_sentence_terms(ctext, dim)
                numeric_terms = [term for term in sentence_terms if any(ch.isdigit() for ch in term)]
                mandatory_terms = [mk for mk in MANDATORY_MARKERS if mk in ctext]

                mandatory_hits += len(mandatory_terms)
                keyword_candidates_total += len(sentence_terms)

                for kw in matched + sentence_terms:
                    if kw not in hit_keywords:
                        hit_keywords.append(kw)

                chunk_score = (
                    len(matched) * 1.6
                    + (1.0 if dim in semantic_tags else 0.0)
                    + len(sentence_terms) * 0.12
                    + len(mandatory_terms) * 0.40
                    + min(1.40, len(numeric_terms) * 0.20)
                )
                raw_score += chunk_score

                support_chunks.append(
                    {
                        "chunk_id": chunk.get("id"),
                        "source_path": chunk.get("path"),
                        "section_title": chunk.get("section_title"),
                        "semantic_tags": semantic_tags,
                        "matched_keywords": matched,
                        "extracted_terms": sentence_terms[:12],
                        "numeric_terms": numeric_terms[:8],
                        "mandatory_markers": mandatory_terms[:8],
                        "excerpt": ctext[:220],
                    }
                )

            if not hit_keywords:
                hit_keywords = seeds[:6]

            merged_keywords = _normalize_keywords(hit_keywords + seeds)
            weight = _score_to_weight(
                DIMENSION_WEIGHTS.get(dim, 0.1),
                raw_score,
                total_chunks=len(all_chunks),
                hit_chunks=hit_chunk_count,
                mandatory_hits=mandatory_hits,
            )

            matrix_items.append(
                {
                    "dimension": dim,
                    "keywords": merged_keywords[:18],
                    "weight": weight,
                    "score": round(raw_score, 3),
                    "source_type": source_type,
                    "signals": {
                        "hit_chunks": hit_chunk_count,
                        "coverage": round(hit_chunk_count / max(1, len(all_chunks)), 4),
                        "mandatory_hits": mandatory_hits,
                        "keyword_count": len(merged_keywords[:18]),
                    },
                    "support_chunks": support_chunks[:12],
                }
            )

        return {
            "index_matrix": matrix_items,
            "legal_boundary": {
                "required_dimensions": list(DIMENSION_RULES.keys()),
                "strict_mode": True,
            },
            "meta": {
                "chunks_total": len(all_chunks),
                "semantic_sections_total": len({str(chunk.get("section_title") or "") for chunk in all_chunks}),
                "keyword_candidates_total": keyword_candidates_total,
            },
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
                        "score": qa_item.get("score", item.get("score", 0.0)),
                        "source_type": "qa_override",
                        "signals": qa_item.get("signals") or item.get("signals") or {},
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

        base_meta = dict(base.get("meta") or {})
        qa_meta = dict(qa.get("meta") or {})
        base_chunks = int(base_meta.get("chunks_total") or 0)
        qa_chunks = int(qa_meta.get("chunks_total") or 0)
        effective_chunks = max(base_chunks, qa_chunks)

        return {
            "index_matrix": out_items,
            "legal_boundary": base.get("legal_boundary") or {},
            "meta": {
                **base_meta,
                "override_strategy": "qa_file_overrides_tender",
                "base_chunks_total": base_chunks,
                "qa_chunks_total": qa_chunks,
                "chunks_total": effective_chunks,
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
