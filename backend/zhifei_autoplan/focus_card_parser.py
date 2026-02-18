from __future__ import annotations

import re
from typing import Any, Dict, List


_CARD_START_RE = re.compile(r"(?m)^-\s*清单项：")
_EVIDENCE_RE = re.compile(r"【证据:(?P<src>[^】]{1,200})】")


def _parse_kv_segments(line: str) -> Dict[str, str]:
    """
    Parse a semicolon-delimited line into key/value pairs.
    Accept both '：' and '=' separators (to tolerate minor variations).
    """
    out: Dict[str, str] = {}
    s = str(line or "").strip()
    if not s:
        return out
    for seg in s.split("；"):
        part = seg.strip()
        if not part:
            continue
        if "：" in part:
            k, v = part.split("：", 1)
        elif "=" in part:
            k, v = part.split("=", 1)
        else:
            continue
        kk = str(k).strip()
        vv = str(v).strip()
        if kk and vv and kk not in out:
            out[kk] = vv
    return out


def _extract_first(text: str, pattern: str, group: str = "v") -> str:
    try:
        m = re.search(pattern, text or "", flags=re.MULTILINE)
        if not m:
            return ""
        val = m.group(group) if group in m.groupdict() else m.group(1)
        return str(val or "").strip()
    except Exception:
        return ""


def extract_focus_cards(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract structured focus-control cards from section text.
    These cards are injected by boq_focus_enforcer with a stable format:
    - '- 清单项：...'
    - '  量化指标：频次=...；阈值=...；...'
    - optional '  图纸定位：...'
    - optional '  标准引用：...'
    - '  风险→控制→验证：风险：...；控制：...；验证：...【证据:...]'
    """
    out: List[Dict[str, Any]] = []
    for sec in sections or []:
        title = str(sec.get("title") or "").strip()
        text = str(sec.get("content") or "")
        if "【清单重点项控制卡】" not in text:
            continue
        # Only scan the tail to reduce false positives.
        start_idx = text.find("【清单重点项控制卡】")
        tail = text[start_idx:] if start_idx >= 0 else text
        starts = [m.start() for m in _CARD_START_RE.finditer(tail)]
        if not starts:
            continue
        starts.append(len(tail))
        for i in range(len(starts) - 1):
            block = tail[starts[i] : starts[i + 1]].strip()
            if not block:
                continue
            lines = block.splitlines()
            head_line = lines[0].strip() if lines else ""
            if head_line.startswith("- "):
                head_line = head_line[2:].strip()
            head = _parse_kv_segments(head_line.replace("清单项：", "清单项："))
            name = head.get("清单项") or head.get("清单项") or ""
            if not name:
                name = _extract_first(head_line, r"清单项[:：]\s*(?P<v>[^；\n]+)", group="v")

            quant_line = ""
            for ln in lines:
                if "量化指标" in ln:
                    quant_line = ln.strip()
                    break
            quant_line = quant_line.replace("量化指标：", "").strip()
            quant = _parse_kv_segments(quant_line)

            drawing_locator = _extract_first(block, r"图纸定位[:：]\s*(?P<v>[^；\n]+)", group="v")
            standard_locator = _extract_first(block, r"标准引用[:：]\s*(?P<v>[^；\n]+)", group="v")

            risk = _extract_first(block, r"风险：(?P<v>[^；\n]{1,400})", group="v")
            control = _extract_first(block, r"控制：(?P<v>[^；\n]{1,400})", group="v")
            verify = _extract_first(block, r"验证：(?P<v>[^。\n]{1,500})", group="v")

            evidence_sources = []
            for m in _EVIDENCE_RE.finditer(block):
                src = str(m.group("src") or "").strip()
                if src and src not in evidence_sources:
                    evidence_sources.append(src)

            out.append(
                {
                    "chapter": title,
                    "name": name.strip(),
                    "head": head,
                    "quant": quant,
                    "drawing_locator": drawing_locator,
                    "standard_locator": standard_locator,
                    "risk": risk,
                    "control": control,
                    "verify": verify,
                    "evidence_sources": evidence_sources,
                    "raw": block[:2000],
                }
            )
    return out
