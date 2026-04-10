from __future__ import annotations

import re
from typing import List, Tuple

from backend.zhifei_autoplan.agents.outline_guard_agent import OutlineGuardAgent


class OutlineManagerAgent:
    """
    目录治理 Agent：
    - 统一裁决目录来源（优先“详细评审标准/技术文件评审标准”）
    - 识别并拦截“招标总目录/评分尾注/报价规则”等污染
    - 在主提取器失效时执行兜底重提取
    """

    _generic_toc_titles = {
        "招标公告",
        "投标人须知",
        "评标及定标办法",
        "评标办法",
        "合同条款及格式",
        "工程量清单",
        "图纸",
        "技术标准和要求",
        "投标文件格式",
    }

    _noise_re = re.compile(
        r"(其余为B|综合评价结果|评标价|偏差率|本项满分|本项评委打分|投标人业绩|项目经理业绩|错误!未定义书签|未定义书签|÷|/\\s*4)"
    )
    _positive_hints = (
        "工程概况",
        "项目概况",
        "施工方法",
        "技术组织措施",
        "整体理解",
        "新技术",
        "新工艺",
        "重点难点",
        "危大工程",
        "保障体系",
        "人、材、机",
        "人材机",
        "安全文明",
        "工期",
        "质量",
        "平面布置图",
    )
    _stop_tokens = (
        "2.2.1（3）",
        "2.2.1(3)",
        "报价文件评审标准",
        "商务及技术文件评审要求",
        "评标价等级",
    )

    def __init__(self):
        self.guard = OutlineGuardAgent()

    def finalize(
        self,
        *,
        current_outline: List[str],
        current_source: str,
        review_outline: List[str],
        merged_text: str,
        lines: List[str],
    ) -> Tuple[List[str], str, List[str]]:
        """
        返回：最终目录、最终来源、治理说明
        """
        current = self.guard.sanitize_review_outline(list(current_outline or []))
        review = self.guard.sanitize_review_outline(list(review_outline or []))
        notes: List[str] = []

        if len(review) < 3:
            fallback = self._extract_review_outline_fallback(merged_text, lines)
            if len(fallback) >= 3:
                review = self.guard.sanitize_review_outline(fallback)
                if len(review) >= 3:
                    notes.append("目录治理Agent触发兜底：由技术文件评审标准段重提取章目录。")
        if len(review) < 3:
            fallback_comprehensive = self._extract_comprehensive_table_outline(merged_text, lines)
            if len(fallback_comprehensive) >= 3:
                review = self.guard.sanitize_review_outline(fallback_comprehensive)
                if len(review) >= 3:
                    notes.append("目录治理Agent触发兜底：由综合评审表中“施工组织设计”条目重提取章目录。")

        if len(review) >= 3:
            if current_source != "review_standard":
                notes.append(f"目录治理Agent修正来源：{current_source} -> review_standard。")
                return review, "review_standard", notes
            if self._is_noisy_outline(current) and not self._is_noisy_outline(review):
                notes.append("目录治理Agent清洗污染：替换异常评审尾注/报价语句目录。")
                return review, "review_standard", notes
            if self._score(review) > self._score(current):
                notes.append("目录治理Agent提升精度：采用评分更高的评审标准目录。")
                return review, "review_standard", notes

        if self._is_generic_toc(current):
            notes.append("目录治理Agent告警：当前仍为招标总目录，未识别到有效技术评审章目录。")
        return current, current_source, notes

    def _is_generic_toc(self, outline: List[str]) -> bool:
        if not outline:
            return True
        generic_compact = {re.sub(r"\s+", "", x or "") for x in self._generic_toc_titles}
        hit = sum(1 for t in outline if self._normalize_title_compact(t) in generic_compact)
        return hit >= 4

    def _is_noisy_outline(self, outline: List[str]) -> bool:
        if not outline:
            return True
        bad = sum(1 for t in outline if self._noise_re.search(str(t)))
        if bad >= 1:
            return True
        if self._is_generic_toc(outline):
            return True
        return False

    def _score(self, outline: List[str]) -> int:
        if not outline:
            return -999
        score = 0
        for t in outline:
            s = str(t or "").strip()
            if not s:
                continue
            if any(k in s for k in self._positive_hints):
                score += 3
            if self._noise_re.search(s):
                score -= 8
            if self._normalize_title_compact(s) in {re.sub(r"\s+", "", x or "") for x in self._generic_toc_titles}:
                score -= 4
        score += min(len(outline), 20)
        return score

    def _normalize_title_compact(self, title: str) -> str:
        s = str(title or "").strip()
        s = re.sub(r"错误!?未定义书签[。.]?", "", s)
        s = re.sub(r"\s+", "", s)
        return s

    def _extract_review_outline_fallback(self, merged_text: str, lines: List[str]) -> List[str]:
        """
        兜底提取（弱依赖格式）：从“2.2.1（2）技术文件评审标准”分段中抽
        “依据投标人提供的XXX进行评审”的 XXX。
        """
        if not merged_text:
            return []
        start_idx: int | None = None
        for i, ln in enumerate(lines[:4500]):
            compact = re.sub(r"\s+", "", ln or "")
            if re.search(r"2\.?2\.?1[（(]?\s*2[)）]?", compact) and ("技术文件评审标准" in compact or "技术文件详细评审标准" in compact):
                start_idx = i
                break
            if "技术文件评审标准" in compact:
                start_idx = i
                break
        if start_idx is None:
            return []

        end_idx = min(len(lines), start_idx + 420)
        for j in range(start_idx + 1, end_idx):
            compact = re.sub(r"\s+", "", lines[j] or "")
            if any(tok in compact for tok in self._stop_tokens):
                end_idx = j
                break
            if re.search(r"2\.?2\.?1[（(]?\s*3[)）]?", compact):
                end_idx = j
                break

        seg = "\n".join(lines[start_idx:end_idx])
        seg_compact = re.sub(r"\s+", "", seg)
        out: List[str] = []
        seen = set()
        for m in re.finditer(r"依据投标人提供的(.{2,140}?)(?:进行评审|的内容进行评审)", seg_compact):
            title = m.group(1)
            title = re.sub(r"^针对", "", title).strip()
            title = re.sub(r"[（(]如有[)）]", "", title).strip()
            title = re.sub(r"如有", "", title).strip()
            title = re.sub(r"(?:的内容|内容)$", "", title).strip()
            title = title.strip("：:;；,.，。 ")
            if len(title) < 2 or len(title) > 64:
                continue
            if self._noise_re.search(title):
                continue
            if "投标人业绩" in title or "项目经理业绩" in title:
                continue
            if title not in seen:
                seen.add(title)
                out.append(title)
        return out

    def _extract_comprehensive_table_outline(self, merged_text: str, lines: List[str]) -> List[str]:
        """
        兜底提取（综合评审表场景）：
        从“综合评审表”中“施工组织设计”对应的 1、2、... 条目提取章目录。
        """
        if not merged_text:
            return []

        def _compact(s: str) -> str:
            return re.sub(r"\s+", "", s or "")

        start_idx: int | None = None
        scan_limit = min(len(lines), 5000)
        for i in range(scan_limit):
            lc = _compact(lines[i])
            if "综合评审表" in lc:
                near = _compact("".join(lines[i : i + 120]))
                if "施工组织设计" in near:
                    start_idx = i
                    break
        if start_idx is None:
            return []

        end_idx = min(len(lines), start_idx + 320)
        for j in range(start_idx + 1, end_idx):
            lc = _compact(lines[j])
            if "评标委员会结合本项目特点" in lc or re.search(r"以上\\d+项", lc) or "注：" in lc or "注:" in lc:
                end_idx = j + 2
                break

        seg = "".join(lines[start_idx:end_idx])
        seg_compact = _compact(seg)
        if not seg_compact:
            return []

        out: List[str] = []
        seen = set()
        item_re = re.compile(r"([1-9]|1[0-9])、(.{2,260}?)(?=(?:[1-9]|1[0-9])、|以上\\d+项|评标委员会结合本项目特点|注[:：]|$)")
        for m in item_re.finditer(seg_compact):
            body = m.group(2).strip()
            title = re.split(r"[：:]", body, maxsplit=1)[0].strip()
            title = title.strip("；;，,。. ")
            if len(title) < 2 or len(title) > 56:
                continue
            if self._noise_re.search(title):
                continue
            if title in seen:
                continue
            # 控制为施组可执行目录，避免抓到评分句尾。
            if not any(k in title for k in ("施工", "质量", "安全", "进度", "成本", "环境", "文明", "机械", "设备", "应急", "措施", "体系", "计划")):
                continue
            seen.add(title)
            out.append(title)
        return out
