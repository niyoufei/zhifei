from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.evidence import best_ingested_hit
from backend.zhifei_autoplan.drawing_semantic import summarize_spatial_anchors, pick_chapter_anchor


_HAN_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {
    "工程",
    "施工",
    "图纸",
    "图",
    "节点",
    "大样",
    "详见",
    "详图",
    "示意",
    "详见图纸",
    "备注",
    "说明",
    "详见说明",
    "技术",
    "要求",
    "材料",
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
        if len(t) >= 12:
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    out = [k for k, _ in ranked[: max(0, int(limit or 0))]]
    return out


def _is_key_process_chapter(title: str) -> bool:
    t = str(title or "")
    keys = ("施工方法", "施工工艺", "施工方案", "主要施工", "工序", "专项", "技术措施", "作业方法", "工艺流程")
    return any(k in t for k in keys)


def build_drawing_index(topic: str, outline: List[str], project_id: str | None = None) -> Dict[str, Any]:
    """
    Build a lightweight “图纸目录/关键构件-章节映射表”.
    - Drawings are taken from ingest audit records where tags include 'drawing'.
    - For key process chapters, bind at least one drawing evidence locator (best-effort).
    """
    audit_path = Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return {"ok": False, "drawings": [], "chapter_bindings": [], "reason": "no_ingest_audit"}

    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    drawings: List[Dict[str, Any]] = []
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]
    except Exception:
        lines = []
    for ln in lines:
        if len(drawings) >= 40:
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
        fname = str(rec.get("filename") or "").strip()
        sha = str(rec.get("sha256") or "")
        if not fname or not sha:
            continue
        extract_path = str(rec.get("extract_saved_as") or "")
        preview = str(rec.get("preview_saved_as") or "")
        kw = []
        topo = {}
        sem = {}
        try:
            if extract_path and Path(extract_path).exists():
                kw = _top_keywords(Path(extract_path).read_text(encoding="utf-8", errors="ignore"), limit=10)
        except Exception:
            kw = []
        try:
            pm = rec.get("parsed_meta") if isinstance(rec.get("parsed_meta"), dict) else {}
            topo = pm.get("topology") if isinstance(pm.get("topology"), dict) else {}
            sem = summarize_spatial_anchors(pm, limit=6)
        except Exception:
            topo = {}
            sem = {}
        drawings.append(
            {
                "filename": fname,
                "sha256": sha,
                "pages": rec.get("pages"),
                "preview": preview if preview and Path(preview).exists() else None,
                "keywords": kw,
                "topology": {
                    "nodes_count": topo.get("nodes_count"),
                    "edges_count": topo.get("edges_count"),
                    "components_count": topo.get("components_count"),
                    "endpoint_count": topo.get("endpoint_count"),
                    "trunk_length": topo.get("trunk_length"),
                    "suggested_flow_segments": topo.get("suggested_flow_segments"),
                    "topology_confidence": topo.get("topology_confidence"),
                }
                if topo
                else {},
                "spatial_anchors": sem.get("component_anchors") if isinstance(sem, dict) else [],
                "dimension_anchors": sem.get("dimension_anchors") if isinstance(sem, dict) else [],
                "elevation_anchors": sem.get("elevation_anchors") if isinstance(sem, dict) else [],
            }
        )

    key_chapters = [str(t).strip() for t in (outline or []) if str(t).strip() and _is_key_process_chapter(str(t))]
    bindings: List[Dict[str, Any]] = []
    for title in key_chapters[:24]:
        hit = best_ingested_hit(
            f"{topic} {title} 图纸",
            limit=10,
            prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
            project_id=pid,
            require_tags=["drawing"],
            exclude_tags=["logo"],
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
                **pick_chapter_anchor(title, drawings),
            }
        )

    return {
        "ok": bool(drawings),
        "project_id": pid,
        "drawings": drawings[:30],
        "chapter_bindings": bindings[:24],
    }
