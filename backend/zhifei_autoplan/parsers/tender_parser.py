from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

from backend.zhifei_autoplan.models import (
    TenderIndexMatrix,
    TenderIndexItem,
    TenderDimension,
    SourceSpan,
)
from backend.zhifei_autoplan.utils.llm_client import LLMClient


@dataclass
class Section:
    title: str
    text: str
    page_spans: List[Tuple[int, int, int]]  # (page, start, end)


class TenderParser:
    """
    招标文件指数级解析引擎（Module 1）
    - MECE 原则：把指标维度拆成 6 类，互斥且覆盖评标重点
    - 答疑为准：同时上传答疑/澄清文件时，优先使用答疑文本进行修正
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm

    async def parse(self, pdf_paths: List[str]) -> TenderIndexMatrix:
        # 并发读取多份资料（PDF 优先，其它格式走统一解析器）
        texts = await asyncio.gather(
            *[asyncio.to_thread(self._read_source_text, p) for p in pdf_paths]
        )

        qa_texts = [t for p, t in texts if self._is_qa_file(p, t)]
        base_texts = [t for p, t in texts if not self._is_qa_file(p, t)]
        merged_text = "\n\n".join(base_texts)
        if qa_texts:
            merged_text = merged_text + "\n\n【答疑优先文本】\n" + "\n\n".join(qa_texts)

        sections = self._split_sections(merged_text)
        items = await self._extract_index_matrix(sections, texts)
        outline, outline_meta = self._extract_outline(merged_text)
        style, style_meta = self._extract_style_requirements(merged_text)
        chapter_pages = self._extract_chapter_page_targets(merged_text, outline)
        chapter_requirements = self._extract_chapter_requirements(merged_text, outline)
        project_name, project_code = self._extract_project_meta(merged_text)
        global_requirements = []
        global_requirements.extend(style_meta.get("global_requirements") or [])
        global_requirements.extend(outline_meta.get("global_requirements") or [])
        extraction_meta: Dict[str, Any] = {
            "outline": outline_meta,
            "style": style_meta,
        }
        return TenderIndexMatrix(
            project_name=project_name,
            project_code=project_code,
            items=items,
            outline=outline,
            outline_source=outline_meta.get("source"),
            style=style,
            style_source=style_meta.get("source"),
            chapter_pages=chapter_pages,
            chapter_requirements=chapter_requirements,
            global_requirements=global_requirements,
            extraction_meta=extraction_meta,
        )

    def _extract_project_meta(self, text: str) -> tuple[str | None, str | None]:
        lines = [ln.strip() for ln in (text or "").splitlines() if ln and ln.strip()]
        if not lines:
            return None, None

        name_keys = (
            "项目名称",
            "工程名称",
            "招标项目名称",
            "标段名称",
            "项目名称及标段",
        )
        code_keys = (
            "项目编号",
            "招标编号",
            "招标项目编号",
            "工程编号",
            "项目代码",
            "采购编号",
        )

        name: str | None = None
        code: str | None = None

        def _clean_name(raw: str) -> str:
            s = (raw or "").strip()
            s = re.sub(r"[（(]?(?:项目编号|招标编号|招标项目编号|工程编号|项目代码|采购编号)\s*[：:].*$", "", s)
            s = s.strip("：:;；,.，。 ")
            s = re.sub(r"\s{2,}", " ", s)
            if len(s) > 120:
                s = s[:120].strip()
            return s

        def _clean_code(raw: str) -> str:
            s = (raw or "").strip()
            s = re.split(r"[，。；;,\s]", s)[0].strip()
            s = re.sub(r"[^A-Za-z0-9_\-./\u4e00-\u9fff]+", "", s)
            if len(s) > 80:
                s = s[:80]
            return s

        for ln in lines[:800]:
            normalized = ln.replace("\u3000", " ").strip()

            if not name:
                for k in name_keys:
                    m = re.search(rf"{re.escape(k)}\s*[：:]\s*(.+)$", normalized)
                    if m:
                        candidate = _clean_name(m.group(1))
                        if len(candidate) >= 2:
                            name = candidate
                            break
                if not name:
                    for k in name_keys:
                        m = re.search(rf"{re.escape(k)}\s+(.+)$", normalized)
                        if m:
                            candidate = _clean_name(m.group(1))
                            if len(candidate) >= 2:
                                name = candidate
                                break

            if not code:
                for k in code_keys:
                    m = re.search(rf"{re.escape(k)}\s*[：:]\s*([A-Za-z0-9_\-./\u4e00-\u9fff]+)", normalized)
                    if m:
                        candidate = _clean_code(m.group(1))
                        if len(candidate) >= 2:
                            code = candidate
                            break
                if not code:
                    for k in code_keys:
                        m = re.search(rf"{re.escape(k)}\s+([A-Za-z0-9_\-./\u4e00-\u9fff]+)", normalized)
                        if m:
                            candidate = _clean_code(m.group(1))
                            if len(candidate) >= 2:
                                code = candidate
                                break

            if name and code:
                break

        if not name:
            for ln in lines[:160]:
                if "招标文件" not in ln:
                    continue
                maybe = ln.replace("招标文件", "").strip("：:-_ ")
                maybe = _clean_name(maybe)
                if 4 <= len(maybe) <= 80 and any(k in maybe for k in ("工程", "项目", "建设")):
                    name = maybe
                    break

        return name or None, code or None

    def _read_pdf(self, path: str) -> Tuple[str, str]:
        texts: List[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
        extracted = "\n".join(texts)

        # OCR fallback: only when file exists on disk AND text is likely from a scanned PDF.
        try:
            if Path(path).exists():
                from backend.zhifei_autoplan.ocr_runtime import (
                    is_text_probably_scanned,
                    ocr_pdf_path,
                )

                if is_text_probably_scanned(extracted):
                    ocr = ocr_pdf_path(path, max_pages=18, scale=2.2, stop_on_catalog=True)
                    if ocr.text:
                        extracted = (extracted + "\n\n" + ocr.text).strip()
        except Exception:
            # OCR is best-effort; never break core parsing.
            pass

        return path, extracted

    def _read_source_text(self, path: str) -> Tuple[str, str]:
        if Path(path).suffix.lower() == ".pdf":
            return self._read_pdf(path)
        try:
            from modules.parser.parser_unify import UnifiedParser
            parsed = UnifiedParser(path).parse()
            text = parsed.get("text") or ""
            if not text and isinstance(parsed.get("meta"), dict):
                text = json.dumps(parsed.get("meta"), ensure_ascii=False)
            return path, text
        except Exception:
            return path, ""

    def _is_qa_file(self, path: str, text: str) -> bool:
        name_hit = any(k in path for k in ("答疑", "澄清", "补遗", "变更"))
        text_hit = any(k in text for k in ("答疑", "澄清", "补遗", "变更"))
        return name_hit or text_hit

    def _split_sections(self, text: str) -> List[Section]:
        # 语义分区（规则版）
        title_patterns = [
            r"(前言|编制说明)",
            r"(工程概况|项目概况)",
            r"(技术标准|技术要求|质量标准)",
            r"(安全|安全文明施工)",
            r"(进度计划|工期要求)",
            r"(环保|环境保护)",
            r"(评分|扣分|废标|否决)",
        ]
        title_re = re.compile("|".join(title_patterns))
        lines = text.splitlines()

        sections: List[Section] = []
        cur_title = "未分类"
        cur_lines: List[str] = []
        cur_spans: List[Tuple[int, int, int]] = []

        for line in lines:
            m = title_re.search(line)
            if m:
                if cur_lines:
                    sections.append(Section(cur_title, "\n".join(cur_lines), cur_spans))
                cur_title = m.group(0)
                cur_lines = [line]
                cur_spans = []
            else:
                cur_lines.append(line)

        if cur_lines:
            sections.append(Section(cur_title, "\n".join(cur_lines), cur_spans))
        return sections

    def _extract_outline(self, text: str) -> tuple[list[str], dict]:
        """
        从招标文件里抽取“投标文件/技术标/施工组织设计”的章节目录。
        规则优先，不依赖 LLM；抽取失败时回退到最小覆盖章集合（仅兜底）。
        """
        merged = text or ""
        if not merged.strip():
            # 仍需给出可运行的目录，避免后续链路因为 outline 为空而中断
            fallback = [
                "编制说明",
                "工程概况",
                "施工部署与组织机构",
                "施工进度计划与关键线路",
                "资源配置计划（劳动力/材料/机械设备）",
                "施工平面布置与临建",
                "主要施工方法与工艺（按清单重点项展开）",
                "质量管理与验收",
                "安全文明施工与应急",
                "绿色施工与环境保护",
                "信息化管理与资料闭环",
                "成品保护与交付",
            ]
            return fallback, {"source": "fallback", "global_requirements": ["招标文本未解析出可用正文，已启用最小覆盖章集合兜底。"]}
        lines = [ln.strip() for ln in merged.splitlines() if ln.strip()]
        # 0) 优先从“技术文件详细评审标准/评审标准”中的“包括但不限于以下内容”抽章目录
        review_outline = self._extract_outline_from_review_standard(merged, lines)
        if review_outline:
            return review_outline, {"source": "review_standard", "global_requirements": []}
        # 1) 目录块优先
        toc_idx = None
        for i, ln in enumerate(lines[:1200]):
            if ln.replace(" ", "") in ("目录", "目錄", "目 录", "目錄"):
                toc_idx = i
                break
        if toc_idx is not None:
            toc_lines = lines[toc_idx + 1 : toc_idx + 260]
            outline = self._parse_outline_lines(toc_lines)
            if outline:
                return outline, {"source": "toc", "global_requirements": []}
        # 2) 全文标题线扫描
        outline = self._parse_outline_lines(lines[:3000])
        if outline:
            return outline, {"source": "headings", "global_requirements": []}
        # 3) 兜底：仅做“覆盖最小集合”，避免空目录导致生成链路中断
        fallback = [
            "编制说明",
            "工程概况",
            "施工部署与组织机构",
            "施工进度计划与关键线路",
            "资源配置计划（劳动力/材料/机械设备）",
            "施工平面布置与临建",
            "主要施工方法与工艺（按清单重点项展开）",
            "质量管理与验收",
            "安全文明施工与应急",
            "绿色施工与环境保护",
            "信息化管理与资料闭环",
            "成品保护与交付",
        ]
        return fallback, {"source": "fallback", "global_requirements": ["目录未从招标文本中明确抽取，已启用最小覆盖章集合兜底。"]}

    def _extract_outline_from_review_standard(self, merged: str, lines: list[str]) -> list[str]:
        """
        从“技术文件详细评审标准/评审标准”区域抽取章节列表。
        典型文本：
        - 依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
          1）工程概况 2）主要施工方法 ...
        """
        if not merged.strip():
            return []

        compact_merged = re.sub(r"\s+", "", merged or "")
        if not compact_merged:
            return []
        stop_markers = (
            "一般得",
            "良好得",
            "优秀得",
            "不得分",
            "注：",
            "注:",
            "编制建议",
            "AI“类人”评审",
            "评标委员会",
        )
        stop_markers_compact = tuple(re.sub(r"\s+", "", s or "") for s in stop_markers)
        noise_keywords = (
            "评分",
            "得分",
            "评审",
            "建议",
            "页面排版",
            "字体图片",
            "编制篇幅",
            "AI",
        )
        noise_exact = {
            "施工组织设计",
            "施工组织设计编制",
            "技术文件详细评审标准",
            "评审标准",
        }

        def _norm(s: str) -> str:
            t = (s or "").strip()
            t = re.sub(r"\s+", " ", t)
            return t.strip("：:;；,.，。 ")

        def _extract_numbered_items(blob: str) -> list[str]:
            if not blob.strip():
                return []
            token_re = re.compile(r"(?<![0-9A-Za-z])([0-9]{1,2}|[一二三四五六七八九十]{1,2})\s*[）\)\\.、]")
            marks = list(token_re.finditer(blob))
            if not marks:
                return []
            out: list[str] = []
            seen = set()
            for i, m in enumerate(marks):
                start = m.end()
                end = marks[i + 1].start() if i + 1 < len(marks) else len(blob)
                seg = blob[start:end]
                for sm in stop_markers:
                    p = seg.find(sm)
                    if p >= 0:
                        seg = seg[:p]
                        break
                title = _norm(seg)
                title = re.sub(r"^[：:、\-\s]+", "", title)
                title = re.sub(r"[;；。]+$", "", title)
                if len(title) < 2 or len(title) > 48:
                    continue
                if title in noise_exact:
                    continue
                if any(nk in title for nk in noise_keywords):
                    continue
                if title not in seen:
                    seen.add(title)
                    out.append(title)
            return out

        def _pick_best(items_arr: list[list[str]]) -> list[str]:
            if not items_arr:
                return []
            filtered = [arr for arr in items_arr if 3 <= len(arr) <= 20]
            pool = filtered if filtered else items_arr

            def _score(arr: list[str]) -> tuple[int, int, int]:
                bad = 0
                for t in arr:
                    if re.search(r"(评标|投标文件|否决|偏差|清标|澄清|报价|得分)", t):
                        bad += 1
                score = 0
                score += len(arr) * 5
                if 6 <= len(arr) <= 15:
                    score += 12
                if arr and ("工程概况" in arr[0] or "项目概况" in arr[0]):
                    score += 10
                if any("施工总平面布置图" in t or "总平面布置图" in t for t in arr):
                    score += 8
                score -= bad * 6
                # 次序：总分高优先；坏项少优先；条目少优先（避免吞入长清单）
                return (score, -bad, -len(arr))

            return max(pool, key=_score)

        def _extract_by_precise_anchor(compact_text: str) -> list[str]:
            """
            精确锚点抽取：先定位“施工组织设计...评审...包括但不限于以下内容”，
            再在该段内抽 1）2）... 清单，避免被评标办法长枚举污染。
            """
            anchor_re = re.compile(
                r"施工组织设计(?:进行)?评审.*?(?:包括但不限于以下内容|以下内容)[：:]"
            )
            m = anchor_re.search(compact_text)
            if not m:
                return []
            tail = compact_text[m.end() : m.end() + 2600]
            if not tail:
                return []
            cut = len(tail)
            for sm in stop_markers_compact:
                p = tail.find(sm)
                if p >= 0 and p < cut:
                    cut = p
            if cut < len(tail):
                tail = tail[:cut]
            return _extract_numbered_items(tail)

        precise = _extract_by_precise_anchor(compact_merged)
        if len(precise) >= 3:
            return precise

        candidates: list[list[str]] = []

        # A) 按行窗口抽取（锚点向后扫描）
        for i, ln in enumerate(lines[:2500]):
            ln_compact = re.sub(r"\s+", "", ln or "")
            if "施工组织设计进行评审" in ln_compact or "包括但不限于以下内容" in ln_compact:
                window = "\n".join(lines[i : i + 180])
                items = _extract_numbered_items(window)
                if items:
                    candidates.append(items)
                continue
            if "技术文件详细评审标准" in ln_compact:
                near = "".join(re.sub(r"\s+", "", x or "") for x in lines[i : i + 40])
                if "包括但不限于以下内容" not in near and "以下内容" not in near:
                    continue
            else:
                continue
            window = "\n".join(lines[i : i + 180])
            items = _extract_numbered_items(window)
            if items:
                candidates.append(items)

        # B) 文本块抽取（“包括但不限于以下内容”后的连续片段）
        for m in re.finditer(r"(包括但不限于以下内容|以下内容)\s*[：:]", merged):
            tail = merged[m.end() : m.end() + 2800]
            items = _extract_numbered_items(tail)
            if items:
                candidates.append(items)

        if not candidates:
            return []

        best = _pick_best(candidates)
        return best if len(best) >= 3 else []

    def _parse_outline_lines(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        seen = set()

        def _clean(ln: str) -> str:
            s = ln.strip()
            # 去掉目录中的引导点与页码
            s = re.sub(r"[·\\.…．]{2,}", " ", s)
            s = re.sub(r"\s+\d{1,4}\s*$", "", s)
            s = re.sub(r"\s*第?\s*\d+\s*页\s*$", "", s)
            return s.strip()

        def _strip_prefix(ln: str) -> str:
            s = ln.strip()
            s = re.sub(r"^第[一二三四五六七八九十百0-9]+章\s*", "", s)
            # 1、 1. 1) 1）
            s = re.sub(r"^\d{1,2}\s*[\\.、\\)）]\s*", "", s)
            # 一、 一. 一) 一）
            s = re.sub(r"^[一二三四五六七八九十]{1,2}\s*[\\.、\\)）]\s*", "", s)
            return s.strip()

        # 仅取一级目录，排除 1.1 / 2.3 之类的二级目录
        lvl1_patterns = [
            re.compile(r"^第[一二三四五六七八九十百0-9]+章\s*.+$"),
            re.compile(r"^(?!\d{1,2}\.\d)\d{1,2}\s*[\\.、\\)）]\s*\\S.+$"),
            re.compile(r"^[一二三四五六七八九十]{1,2}\s*[\\.、\\)）]\s*\\S.+$"),
        ]

        for raw in lines:
            ln = _clean(raw)
            if not ln:
                continue
            if any(x in ln for x in ("附录", "附件", "参考文献", "致谢")):
                continue
            if not any(rx.match(ln) for rx in lvl1_patterns):
                continue
            title = _strip_prefix(ln)
            # 过滤过短/过长以及纯数字
            if len(title) < 2 or len(title) > 48:
                continue
            if re.fullmatch(r"\d+", title):
                continue
            if title not in seen:
                seen.add(title)
                out.append(title)
            if len(out) >= 30:
                break
        return out

    def _extract_style_requirements(self, text: str) -> tuple[dict, dict]:
        """
        抽取版式/字体/字号/行距/纸张/页数等编制要求。
        输出的 style dict 尽量与 exporter._normalize_style 兼容。
        """
        merged = text or ""
        meta: Dict[str, Any] = {"source": "rules", "global_requirements": []}
        if not merged.strip():
            return {}, {"source": "none", "global_requirements": []}

        compact = re.sub(r"\s+", "", merged)

        cn_size_map = {
            "初号": 42.0,
            "小初": 36.0,
            "一号": 26.0,
            "小一": 24.0,
            "二号": 22.0,
            "小二": 18.0,
            "三号": 16.0,
            "小三": 15.0,
            "四号": 14.0,
            "小四": 12.0,
            "五号": 10.5,
            "小五": 9.0,
            "六号": 7.5,
            "小六": 6.5,
        }
        size_token_re = r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五|六号|小六|\d+(?:\.\d+)?\s*(?:pt|磅)?)"

        def _font_alias(v: str | None) -> str | None:
            s = str(v or "").strip()
            if not s:
                return None
            if s in {"SimSun", "宋体"}:
                return "宋体"
            if s in {"仿宋", "仿宋体", "FangSong"}:
                return "仿宋体"
            return s

        def _parse_size_token(token: str | None) -> float | None:
            s = str(token or "").strip()
            if not s:
                return None
            if s in cn_size_map:
                return float(cn_size_map[s])
            m = re.search(r"(\d+(?:\.\d+)?)", s)
            if not m:
                return None
            try:
                return float(m.group(1))
            except Exception:
                return None

        # 纸张
        paper = None
        if re.search(r"\bA4\b", merged, flags=re.IGNORECASE) or "A4" in compact:
            paper = "A4"
        elif re.search(r"\bA3\b", merged, flags=re.IGNORECASE) or "A3" in compact:
            paper = "A3"

        # 字体
        font_candidates = [
            "宋体",
            "仿宋体",
            "仿宋",
            "黑体",
            "楷体",
            "微软雅黑",
            "SimSun",
            "FangSong",
            "SimHei",
            "KaiTi",
            "Times New Roman",
            "Arial",
        ]
        body_font = None
        title_font = None
        m_body_font = re.search(r"(?:字体(?:图片)?要求|字体要求)?[^。\n]{0,80}?字体[:：]\s*([A-Za-z\u4e00-\u9fff]+)", merged)
        if m_body_font:
            body_font = _font_alias(m_body_font.group(1))
        m_title_font = re.search(r"标题(?:字体)?[:：]\s*([A-Za-z\u4e00-\u9fff]+)", merged)
        if m_title_font:
            title_font = _font_alias(m_title_font.group(1))
        if not body_font:
            for f in font_candidates:
                if f in merged:
                    body_font = _font_alias(f)
                    break
        if not title_font and body_font:
            title_font = body_font

        # 字号：优先抽“标题/其他(正文)”的独立设置
        body_size = None
        title_size = None
        m_title_size = re.search(rf"标题[^。\n]{{0,12}}?[:：]?\s*{size_token_re}", merged)
        if m_title_size:
            title_size = _parse_size_token(m_title_size.group(1))
        m_body_size = re.search(rf"(?:其他(?:为)?|其余(?:为)?|正文)[^。\n]{{0,8}}?[:：]?\s*{size_token_re}", merged)
        if m_body_size:
            body_size = _parse_size_token(m_body_size.group(1))
        if body_size is None:
            m_size = re.search(r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五|六号|小六)", merged)
            if m_size:
                body_size = _parse_size_token(m_size.group(1))
        if body_size is None:
            m_num = re.search(r"字号[:：]?\s*(\d+(?:\.\d+)?)", merged)
            if m_num:
                body_size = _parse_size_token(m_num.group(1))
        if title_size is None and body_size is not None:
            title_size = min(36.0, body_size + 2.0)

        # 行距（倍数优先；固定值磅次之）
        line_spacing = None
        line_spacing_pt = None
        m_ls = re.search(r"行距[^。\n]{0,10}?[:：]?\s*(\d+(?:\.\d+)?)\s*倍", merged)
        if m_ls:
            try:
                line_spacing = float(m_ls.group(1))
            except Exception:
                line_spacing = None
        if line_spacing is None:
            m_lsp = re.search(r"(?:行距[^。\n]{0,8}?固定值|行距|固定值)[：:\s]*?(\d+(?:\.\d+)?)\s*磅", merged)
            if m_lsp:
                try:
                    line_spacing_pt = float(m_lsp.group(1))
                except Exception:
                    line_spacing_pt = None

        # 页边距（cm/厘米）
        margins_cm: Dict[str, float] = {}
        side_map = {"上": "top", "下": "bottom", "左": "left", "右": "right"}
        for zh, key in side_map.items():
            m_side = re.search(rf"{zh}\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)", merged, flags=re.IGNORECASE)
            if m_side:
                try:
                    margins_cm[key] = float(m_side.group(1))
                except Exception:
                    pass
        # 常见写法：页边距：上2.5cm 下2.0cm 左2.0cm 右2.0cm
        m_margins = re.search(
            r"页边距[:：]?\s*上(?P<top>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)\s*下(?P<bottom>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)\s*左(?P<left>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)\s*右(?P<right>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)",
            merged,
            flags=re.IGNORECASE,
        )
        if m_margins:
            for k in ("top", "bottom", "left", "right"):
                try:
                    margins_cm[k] = float(m_margins.group(k))
                except Exception:
                    pass
        # 写法：页边距：上2.5厘米，其余均为2.0厘米
        m_top_other = re.search(
            r"页边距[^。\n]{0,40}?上\s*(?P<top>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)[,，;；、\s]*(?:其余|其他|其它)[^。\n]{0,8}?(?:均为|为)\s*(?P<other>\d+(?:\.\d+)?)\s*(?:cm|厘米|㎝)",
            merged,
            flags=re.IGNORECASE,
        )
        if m_top_other:
            try:
                top = float(m_top_other.group("top"))
                other = float(m_top_other.group("other"))
                margins_cm["top"] = top
                margins_cm.setdefault("right", other)
                margins_cm.setdefault("bottom", other)
                margins_cm.setdefault("left", other)
            except Exception:
                pass

        # 总页数限制（若出现）
        max_pages = None
        m_pages = re.search(r"(?:施工组织设计|总页数|页数|篇幅).{0,18}?(?:不超过|不得超过|控制在|最多)\s*(\d{1,3})\s*页", merged)
        if m_pages:
            max_pages = int(m_pages.group(1))
            meta["global_requirements"].append(f"总页数不超过{max_pages}页。")

        style: Dict[str, Any] = {}
        font_cfg: Dict[str, Any] = {}
        if body_font:
            if body_font in {"Times New Roman", "Arial"}:
                font_cfg["latin"] = body_font
            else:
                font_cfg["eastAsia"] = body_font
            style["body_font"] = body_font
        if title_font:
            style["title_font"] = title_font
        if body_size is not None:
            style["body_size"] = max(9.0, min(24.0, float(body_size)))
            font_cfg["size_pt"] = style["body_size"]
        if title_size is not None:
            style["title_size"] = max(10.0, min(36.0, float(title_size)))
        if line_spacing is not None:
            style["line_spacing"] = line_spacing
            font_cfg["line_spacing"] = line_spacing
        if line_spacing_pt is not None:
            style["line_spacing_pt"] = line_spacing_pt
            font_cfg["line_spacing_pt"] = line_spacing_pt
        if font_cfg:
            style["font"] = font_cfg
        if paper:
            style["paper"] = paper
        if margins_cm:
            style["margins_cm"] = margins_cm
        if max_pages is not None:
            style["max_pages"] = int(max_pages)

        if style:
            summary = []
            if paper:
                summary.append(f"纸张{paper}")
            if body_font:
                summary.append(f"正文字体{body_font}")
            if body_size is not None:
                summary.append(f"正文{body_size}pt")
            if title_size is not None:
                summary.append(f"标题{title_size}pt")
            if line_spacing is not None:
                summary.append(f"行距{line_spacing}倍")
            if line_spacing_pt is not None:
                summary.append(f"行距固定值{line_spacing_pt}磅")
            if margins_cm:
                summary.append(
                    "页边距上{top}cm/右{right}cm/下{bottom}cm/左{left}cm".format(
                        top=margins_cm.get("top", "-"),
                        right=margins_cm.get("right", "-"),
                        bottom=margins_cm.get("bottom", "-"),
                        left=margins_cm.get("left", "-"),
                    )
                )
            if summary:
                meta["global_requirements"].append("版式要求：" + "，".join(summary) + "。")
        return style, meta

    def _extract_chapter_page_targets(self, text: str, outline: list[str]) -> Dict[str, Any]:
        """
        抽取章节页数目标（若招标明确给出）。
        仅做轻量规则：识别“章节名（x-y页）/（x页）”或“章节名：x页”。
        """
        merged = text or ""
        if not merged.strip() or not outline:
            return {}
        chapter_pages: Dict[str, Any] = {}

        def _norm_title(t: str) -> str:
            return re.sub(r"\s+", "", t or "")

        compact = merged.replace(" ", "")
        for title in outline:
            tkey = _norm_title(title)
            if not tkey:
                continue
            # （x-y页）
            m_range = re.search(rf"{re.escape(tkey)}[（(](\d{{1,3}})\s*[-~到]\s*(\d{{1,3}})\s*页[）)]", compact)
            if m_range:
                lo, hi = int(m_range.group(1)), int(m_range.group(2))
                chapter_pages[title] = {"min": lo, "max": hi, "target": hi}
                continue
            # （x页）
            m_single = re.search(rf"{re.escape(tkey)}[（(](\d{{1,3}})\s*页[）)]", compact)
            if m_single:
                n = int(m_single.group(1))
                chapter_pages[title] = {"target": n}
                continue
            # 章节名：x页
            m_colon = re.search(rf"{re.escape(tkey)}[:：](\d{{1,3}})\s*页", compact)
            if m_colon:
                n = int(m_colon.group(1))
                chapter_pages[title] = {"target": n}
                continue
        return chapter_pages

    def _extract_chapter_requirements(self, text: str, outline: list[str]) -> Dict[str, Any]:
        """
        抽取与章节标题强相关的“应包含/要求/提供”条款。
        规则：以标题为锚点向后截取少量文本，抓取含关键动词的句子。
        """
        merged = text or ""
        if not merged.strip() or not outline:
            return {}
        lines = [ln.strip() for ln in merged.splitlines() if ln.strip()]
        joined = "\n".join(lines)
        chapter_reqs: Dict[str, Any] = {}
        verbs = ("应", "必须", "提供", "包含", "阐述", "说明", "明确")
        for title in outline[:30]:
            # 简单锚点：找到标题出现位置后截取一段
            idx = joined.find(title)
            if idx < 0:
                continue
            chunk = joined[idx : idx + 600]
            cand = []
            for sent in re.split(r"[。；;\n]", chunk):
                s = sent.strip()
                if not s or len(s) < 6:
                    continue
                if any(v in s for v in verbs) and ("页" not in s):
                    # 避免把目录行本身当要求
                    if title in s and len(s) < len(title) + 8:
                        continue
                    cand.append(s[:120])
                if len(cand) >= 6:
                    break
            if cand:
                chapter_reqs[title] = cand
        return chapter_reqs

    async def _extract_index_matrix(
        self, sections: List[Section], sources: List[Tuple[str, str]]
    ) -> List[TenderIndexItem]:
        dim_keywords = {
            TenderDimension.QUALITY: ["质量", "验收", "标准", "合格", "优良"],
            TenderDimension.SAFETY: ["安全", "文明施工", "风险", "事故"],
            TenderDimension.SCHEDULE: ["工期", "进度", "节点", "计划"],
            TenderDimension.ENVIRONMENT: ["环保", "扬尘", "噪声", "水土保持"],
            TenderDimension.DIFFICULTY: ["重难点", "复杂", "关键工序"],
            TenderDimension.PENALTY: ["扣分", "废标", "否决", "重大偏差"],
        }

        items: List[TenderIndexItem] = []
        for dim, kws in dim_keywords.items():
            hits = []
            spans = []
            weight = 0.2
            for sec in sections:
                for kw in kws:
                    if kw in sec.text:
                        hits.append(kw)
                        weight = min(1.0, weight + 0.1)

            for path, txt in sources:
                for kw in kws:
                    if kw in txt:
                        idx = txt.find(kw)
                        spans.append(
                            SourceSpan(
                                file_name=path,
                                page=0,
                                start=idx,
                                end=idx + len(kw),
                                snippet=txt[max(0, idx - 30) : idx + 30],
                            )
                        )
                        break

            if self.llm:
                prompt = f"从招标文本中提取 {dim.value} 的关键指标，输出关键词列表。"
                await self.llm.complete(prompt)

            items.append(
                TenderIndexItem(
                    dimension=dim,
                    keywords=sorted(set(hits)),
                    weight=weight,
                    source_spans=spans[:5],
                )
            )
        return items
