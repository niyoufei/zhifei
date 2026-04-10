from __future__ import annotations

import re
from typing import List


class OutlineGuardAgent:
    """
    章目录识别专用守门 Agent：
    - 过滤“技术文件详细评审标准”之外的评分/商务条款污染
    - 在已抽到有效施组目录后，遇到评分语句时及时截断
    """

    _hard_negative_re = re.compile(
        r"(本项评委打分|本项满分|评标报告|评审报告|评标委员会.*理由|报价文件评|商务文件评|"
        r"投标报价|评标基准价|偏差率|有效评标价|投标人业绩|项目经理业绩|获奖|荣誉|证书|证明材料)"
    )
    _soft_negative_re = re.compile(r"(评分|得分|分值|报价|商务文件|投标函|合同条款)")
    _positive_hints = (
        "工程概况",
        "项目概况",
        "施工方法",
        "施工工艺",
        "物资计划",
        "机械",
        "设备计划",
        "劳动力",
        "质量",
        "安全",
        "工期",
        "文明施工",
        "平面布置",
        "技术组织措施",
        "重点",
        "难点",
        "危险性较大工程",
        "危大工程",
        "应急",
        "绿色施工",
        "信息化",
        "四新技术",
        "新技术",
    )

    def sanitize_review_outline(self, items: List[str]) -> List[str]:
        cleaned: List[str] = []
        seen = set()
        for raw in items:
            title = self._normalize(raw)
            if not title or title in seen:
                continue

            if self._is_hard_negative(title):
                if len(cleaned) >= 6:
                    break
                continue

            if self._is_soft_negative(title) and len(cleaned) >= 8:
                break

            # 当目录已足够长时，遇到非施组语义条目直接截断，阻断“13-17章污染”。
            if len(cleaned) >= 10 and not self._is_positive(title):
                break

            cleaned.append(title)
            seen.add(title)
            if len(cleaned) >= 30:
                break
        return cleaned

    def _normalize(self, text: str) -> str:
        t = str(text or "").strip()
        t = re.sub(r"\s+", " ", t)
        t = re.sub(r"^[（(]?[0-9一二三四五六七八九十]{1,2}[)）、.．]\s*", "", t)
        t = re.sub(r"[;；。]+$", "", t)
        t = re.sub(r"[（(]+$", "", t)
        t = re.sub(r"\s*\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s*$", "", t)
        return t.strip("：:;；,，。 ")

    def _is_hard_negative(self, title: str) -> bool:
        if title in {"对于", "本项满分5分", "本项满分"}:
            return True
        return bool(self._hard_negative_re.search(title))

    def _is_soft_negative(self, title: str) -> bool:
        return bool(self._soft_negative_re.search(title))

    def _is_positive(self, title: str) -> bool:
        return any(k in title for k in self._positive_hints)
