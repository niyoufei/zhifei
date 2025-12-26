# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _file_meta(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {"exists": False, "path": str(p)}
    bs = p.read_bytes()
    st = p.stat()
    return {
        "exists": True,
        "path": str(p),
        "size_bytes": len(bs),
        "sha256": _sha256_bytes(bs),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def _short(s: Any, n: int = 16) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else (s[:n] + "...")


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _extract_work_items(obj: Any, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Best-effort recursive extraction of work_items from arbitrary SuperKG/base-pack JSON.
    """
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def add(it: Dict[str, Any]) -> None:
        nonlocal items
        if len(items) >= limit:
            return
        _id = str(it.get("id") or it.get("ID") or it.get("uid") or it.get("工序名称") or it.get("name") or "")
        if _id and _id in seen:
            return
        if _id:
            seen.add(_id)
        items.append(it)

    def visit(node: Any, depth: int) -> None:
        if len(items) >= limit or depth > 6:
            return
        if isinstance(node, dict):
            wi = node.get("work_items")
            if isinstance(wi, list):
                for it in wi:
                    if isinstance(it, dict):
                        add(it)
                        if len(items) >= limit:
                            return
            subs = node.get("subdivisions")
            if isinstance(subs, list):
                for s in subs:
                    visit(s, depth + 1)
                    if len(items) >= limit:
                        return
            for k, v in node.items():
                if k in ("work_items", "subdivisions"):
                    continue
                visit(v, depth + 1)
                if len(items) >= limit:
                    return
        elif isinstance(node, list):
            for v in node:
                visit(v, depth + 1)
                if len(items) >= limit:
                    return

    visit(obj, 0)
    return items[:limit]


def _fmt_work_item(it: Dict[str, Any]) -> str:
    name = it.get("工序名称") or it.get("name") or it.get("title") or it.get("id") or "未命名工序"
    lines: List[str] = [f"工序：{name}"]

    def show_list(label: str, v: Any, max_n: int = 6) -> None:
        arr = _as_list(v)
        if not arr:
            return
        s = "；".join([_short(x, 120) for x in arr[:max_n]])
        if len(arr) > max_n:
            s += f"（共{len(arr)}项）"
        lines.append(f"- {label}：{s}")

    show_list("操作步骤", it.get("操作步骤") or it.get("steps"))
    show_list("设备材料", it.get("设备材料") or it.get("materials"))
    show_list("关键参数", it.get("关键参数") or it.get("params"))
    show_list("风险点", it.get("风险点") or it.get("risks"))
    show_list("控制措施", it.get("控制措施") or it.get("controls"))
    show_list("验证方法", it.get("验证方法") or it.get("verify"))

    rc = it.get("资源配置")
    if isinstance(rc, dict):
        parts = [f"{k}={v}" for k, v in list(rc.items())[:12]]
        lines.append(f"- 资源配置：{'; '.join(parts)}")

    if it.get("评分点"):
        show_list("评分点", it.get("评分点"))

    tr = it.get("可追溯字段")
    if isinstance(tr, dict):
        parts = [f"{k}={v}" for k, v in list(tr.items())[:12]]
        lines.append(f"- 可追溯字段：{'; '.join(parts)}")

    for k in ("关键线路", "工期影响", "最小间隔"):
        if k in it:
            lines.append(f"- {k}：{it.get(k)}")

    return "\n".join(lines)


def build_sections_from_kg(
    payload: Optional[Dict[str, Any]] = None,
    project_profile: Optional[Dict[str, Any]] = None,
    precheck: Optional[Dict[str, Any]] = None,
    region_upgrade: Optional[Dict[str, Any]] = None,
    kg_context: Optional[Dict[str, Any]] = None,
    outline: Optional[List[str]] = None,
    topic: Optional[str] = None,
    max_work_items: int = 3,
) -> List[Dict[str, str]]:
    """
    Demo compose engine: turn trace artifacts into human-readable sections.
    Downstream LLM/RAG can replace the placeholder parts later.
    """
    payload = payload or {}
    project_profile = project_profile or {}
    precheck = precheck or {}
    region_upgrade = region_upgrade or {}
    kg_context = kg_context or {}
    outline = outline or payload.get("outline") or []
    topic = topic or payload.get("topic") or ""

    dr = kg_context.get("domain_resolution") or {}
    domain_key = dr.get("domain_key")
    matched_cn_name = dr.get("matched_cn_name")
    method = dr.get("method")
    score = dr.get("score")

    selected_packs = kg_context.get("selected_packs") or []
    pack_names: List[str] = []
    pack_paths: List[Path] = []
    for p in selected_packs:
        if isinstance(p, dict) and p.get("path"):
            path = Path(p["path"])
            pack_paths.append(path)
            pack_names.append(path.name)
        elif isinstance(p, str):
            path = Path(p)
            pack_paths.append(path)
            pack_names.append(path.name)

    # Section 1: Trace Summary
    lines: List[str] = []
    lines.append("【输入】")
    lines.append(f"- topic：{topic}")
    if outline:
        lines.append(f"- outline：{'; '.join([str(x) for x in outline])}")
    lines.append("")
    lines.append("【项目画像】")
    lines.append(f"- decision：{project_profile.get('decision')}")
    pt = project_profile.get("project_type") or {}
    if isinstance(pt, dict):
        lines.append(f"- project_type：{pt.get('value')}（confidence={pt.get('confidence')} source={pt.get('source')}）")
    md = project_profile.get("mandatory_dimensions") or []
    if md:
        lines.append(f"- mandatory_dimensions：{'; '.join([str(x) for x in md])}")
    lines.append("")
    lines.append("【PreCheck Guard】")
    lines.append(f"- passed：{precheck.get('passed')}")
    lines.append(f"- project_profile_decision：{precheck.get('project_profile_decision') or project_profile.get('decision')}")
    lines.append("")
    lines.append("【区域升级】")
    lines.append(f"- applied：{region_upgrade.get('applied')}")
    lines.append(f"- region_key：{region_upgrade.get('region_key')}")
    lines.append("")
    lines.append("【KG Context】")
    lines.append(f"- domain_key：{domain_key}")
    lines.append(f"- matched_cn_name：{matched_cn_name}")
    lines.append(f"- method：{method}")
    lines.append(f"- score：{score}")
    lines.append(f"- selected_packs：{'; '.join(pack_names) if pack_names else '<empty>'}")

    build_dir = Path("build")
    metas = {
        "project_profile.json": _file_meta(build_dir / "project_profile.json"),
        "precheck_guard.json": _file_meta(build_dir / "precheck_guard.json"),
        "region_upgrade.json": _file_meta(build_dir / "region_upgrade.json"),
        "kg_context.json": _file_meta(build_dir / "kg_context.json"),
    }
    lines.append("")
    lines.append("【可追溯文件】")
    for fn, meta in metas.items():
        if meta.get("exists"):
            lines.append(f"- {fn}：exists=True size={meta.get('size_bytes')} sha256={_short(meta.get('sha256'), 16)}")
        else:
            lines.append(f"- {fn}：exists=False")

    sections: List[Dict[str, str]] = []
    sections.append({"title": "可追溯性摘要", "content": "\n".join(lines)})

    # Section 2: Work Items (auto extract)
    # --- Retrieve evidence: build SuperKG snippet from /retrieve (traceable) ---
    try:
        from retrieve_service import retrieve as _kg_retrieve
    except Exception:
        _kg_retrieve = None
    
    _evidence_query = " ".join([
        str(topic or ""),
        str(domain_key or ""),
        "质量控制", "安全风险", "控制措施", "验收标准", "资源配置"
    ]).strip()
    _retr = None
    if _kg_retrieve is not None:
        try:
            _retr = _kg_retrieve(_evidence_query, top_k=6)
        except Exception:
            _retr = None
    
    if isinstance(_retr, dict) and isinstance(_retr.get('results'), list) and _retr['results']:
        _lines = []
        _lines.append(f"检索查询：{_evidence_query}")
        _lines.append(f"命中条目数：{len(_retr['results'])}（展示前 6 条）")
        _lines.append("")
        for _i, _r in enumerate(_retr['results'][:6], 1):
            _lines.append(f"{_i}. 来源：{_r.get('source')}  标题：{_r.get('title')}  score={_r.get('score')}")
            _lines.append(f"   path：{_r.get('path')}")
            _lines.append(f"   sha256：{_r.get('sha256')}")
            _lines.append("   摘要：")
            _lines.append((_r.get('text') or '').strip())
            _lines.append("")
        sections.append({"title": "SuperKG 工序样例（检索证据）", "content": "\n".join(_lines).strip()})
    else:
        sections.append({"title": "SuperKG 工序样例（检索证据）", "content": "未检索到证据（retrieve 返回为空或不可用）。请先确认 /retrieve 可用且 build/kg_context.json 已生成 selected_packs。"})
    # --------------------------------------------------------------------------

    work_items: List[Dict[str, Any]] = []
    for p in pack_paths:
        if len(work_items) >= max_work_items:
            break
        try:
            if p.exists() and p.is_file():
                obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                work_items.extend(_extract_work_items(obj, limit=max_work_items - len(work_items)))
        except Exception:
            continue

    if work_items:
        wi_lines: List[str] = []
        for idx, it in enumerate(work_items, 1):
            wi_lines.append(f"{idx}. {_fmt_work_item(it)}")
            wi_lines.append("")
        sections.append({"title": "SuperKG 工序样例（自动抽取）", "content": "\n".join(wi_lines).strip()})
    else:
        sections.append({
            "title": "SuperKG 工序样例（自动抽取）",
            "content": "未能从 selected_packs 中解析到 work_items（pack schema 可能不含 work_items 字段）。该章节为占位。",
        })

    # Placeholder sections for each outline item
    for i, t in enumerate(outline, 1):
        title = str(t).strip() or f"章节{i}"
        content = (
            "本章节为占位输出，用于验证 Compose Engine 已接入 KG Context / 项目画像 / 区域升级 / PreCheck Guard 的闭环链路。\n"
            f"- domain_key：{domain_key}\n"
            f"- matched_cn_name：{matched_cn_name}\n"
            "下一步：接入 /retrieve + LLM 组稿，把检索证据与可追溯索引写入章节内容。"
        )
        sections.append({"title": title, "content": content})

    return sections
