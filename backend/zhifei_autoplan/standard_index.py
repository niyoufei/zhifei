from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.evidence import best_ingested_hit
from backend.zhifei_autoplan.workspace import workspace_paths


_HAN_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {
    "工程",
    "施工",
    "标准",
    "企业标准",
    "作业",
    "作业指导",
    "指导",
    "工法",
    "图集",
    "规范",
    "要求",
    "技术",
    "管理",
    "项目",
}


def _top_keywords(text: str, limit: int = 12) -> List[str]:
    s = (text or "").strip()
    if not s:
        return []
    toks = [t.strip() for t in _HAN_TOKEN_RE.findall(s[:8000]) if t and len(t) >= 2]
    freq: Dict[str, int] = {}
    for t in toks:
        if t in _STOP:
            continue
        if len(t) >= 14:
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    return [k for k, _ in ranked[: max(0, int(limit or 0))]]


def _is_key_process_chapter(title: str) -> bool:
    t = str(title or "")
    keys = ("施工方法", "施工工艺", "施工方案", "主要施工", "工序", "专项", "技术措施", "作业方法", "工艺流程", "质量")
    return any(k in t for k in keys)


def build_standard_index(
    topic: str,
    outline: List[str],
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> Dict[str, Any]:
    """
    Build a lightweight “企业标准/工法/作业指导 目录 + 章节-标准绑定”索引。
    Sources:
    - ingest audit records where tags include 'standard'
    Output:
    - standards: file list + keywords
    - chapter_bindings: best-effort locator bindings for key chapters
    """
    audit_path = workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return {"ok": False, "standards": [], "chapter_bindings": [], "reason": "no_ingest_audit"}

    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    standards: List[Dict[str, Any]] = []
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]
    except Exception:
        lines = []
    for ln in lines:
        if len(standards) >= 60:
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
        fname = str(rec.get("filename") or "").strip()
        sha = str(rec.get("sha256") or "")
        if not fname or not sha:
            continue
        extract_path = str(rec.get("extract_saved_as") or "")
        kw = []
        try:
            if extract_path and Path(extract_path).exists():
                kw = _top_keywords(Path(extract_path).read_text(encoding="utf-8", errors="ignore"), limit=10)
        except Exception:
            kw = []
        standards.append(
            {
                "filename": fname,
                "sha256": sha,
                "pages": rec.get("pages"),
                "keywords": kw,
            }
        )

    key_chapters = [str(t).strip() for t in (outline or []) if str(t).strip() and _is_key_process_chapter(str(t))]
    bindings: List[Dict[str, Any]] = []
    for title in key_chapters[:30]:
        hit = best_ingested_hit(
            f"{topic} {title} 企业标准 工法 作业指导 标准化 质量验收",
            limit=10,
            prefer_filename_keywords=["标准", "企业标准", "工法", "作业指导", "标准化", "技术标准", "图集"],
            project_id=pid,
            require_tags=["standard"],
            exclude_tags=["logo"],
            audit_path=audit_path,
        )
        if not hit or not hit.get("locator"):
            continue
        bindings.append(
            {
                "chapter": title,
                "locator": hit.get("locator"),
                "filename": hit.get("filename"),
                "page": hit.get("page"),
                "offset": hit.get("offset"),
                "snippet": hit.get("snippet"),
            }
        )

    return {
        "ok": bool(standards),
        "project_id": pid,
        "standards": standards[:40],
        "chapter_bindings": bindings[:30],
    }
