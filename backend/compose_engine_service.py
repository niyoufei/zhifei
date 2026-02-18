# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import re
from backend.zhifei_autoplan.kg_runtime import search_kg as _search_active_kg
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data


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


def _calc_keyword_coverage(text: str, keywords: List[str]) -> Dict[str, Any]:
    if not keywords:
        return {"covered": [], "missed": [], "coverage": 0.0}
    covered = []
    missed = []
    for k in keywords:
        if k and k in text:
            covered.append(k)
        else:
            missed.append(k)
    coverage = round(len(covered) / max(1, len(keywords)), 3)
    return {"covered": covered, "missed": missed, "coverage": coverage}


def _select_boq_processes(boq_data: Dict[str, Any], limit: int = 6) -> List[str]:
    items = boq_data.get("items") if isinstance(boq_data, dict) else None
    if not isinstance(items, list):
        return []
    names = []
    for it in items:
        proc = (it or {}).get("process") or {}
        pname = proc.get("name")
        if isinstance(pname, str) and pname.strip():
            names.append(pname.strip())
    # 去重并截断
    uniq = list(dict.fromkeys(names))
    return uniq[:limit]


def _select_boq_resources(boq_data: Dict[str, Any], limit: int = 8) -> List[str]:
    items = boq_data.get("items") if isinstance(boq_data, dict) else None
    if not isinstance(items, list):
        return []
    names = []
    for it in items:
        res = (it or {}).get("resources") or []
        if not isinstance(res, list):
            continue
        for r in res:
            nm = (r or {}).get("name")
            if isinstance(nm, str) and nm.strip():
                names.append(nm.strip())
    uniq = list(dict.fromkeys(names))
    return uniq[:limit]


def _calc_dimension_priority(tender_matrix: Dict[str, Any], title: str) -> float:
    """
    根据章节标题与招标指标关键词匹配，估算优先级权重。
    用于提升高权重章节的工序/资源描述密度。
    """
    if not isinstance(tender_matrix, dict):
        return 0.0
    items = tender_matrix.get("items") or []
    max_w = 0.0
    for it in items:
        dim = str(it.get("dimension"))
        kws = it.get("keywords") or []
        weight = float(it.get("weight") or 0.0)
        if dim in title or any(k in title for k in kws):
            max_w = max(max_w, weight)
    return max_w


def _ensure_retrieve_trace(topic: str, domain_key: str | None, outline: List[str]) -> None:
    """
    Ensure `build/retrieve.json` is always generated during compose.
    This keeps downstream audit/smoke checks deterministic even when
    no retrieval evidence is found.
    """
    q_parts: List[str] = []
    if isinstance(topic, str) and topic.strip():
        q_parts.append(topic.strip())
    if isinstance(domain_key, str) and domain_key.strip():
        q_parts.append(domain_key.strip())
    for t in (outline or [])[:2]:
        s = str(t or "").strip()
        if s:
            q_parts.append(s)
    q_parts.extend(["质量控制", "安全风险", "资源配置", "关键线路"])
    query = " ".join(q_parts).strip() or "施工组织设计"

    try:
        from backend.retrieve_service import retrieve as _retrieve

        _retrieve(query, top_k=6)
        return
    except Exception as e:
        build_dir = Path("build")
        build_dir.mkdir(parents=True, exist_ok=True)
        trace = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "tokens": [],
            "top_k": 6,
            "pack_info": {"source": "compose_fallback", "details": {"reason": "retrieve_error"}},
            "used_packs": [],
            "docs_scanned": 0,
            "results": [],
            "errors": [{"error": repr(e)}],
            "kg_pack": None,
        }
        # Best-effort kg_pack injection for trace continuity
        try:
            kg_ctx_path = build_dir / "kg_context.json"
            if kg_ctx_path.exists():
                trace["kg_pack"] = json.loads(kg_ctx_path.read_text(encoding="utf-8")).get("kg_pack")
        except Exception:
            pass
        (build_dir / "retrieve.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _search_ingested_docs(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    audit_path = Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return []

    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", query or "")
    uniq: List[str] = []
    seen: set[str] = set()
    for t in tokens:
        tt = t.strip()
        if len(tt) < 2:
            continue
        if tt not in seen:
            seen.add(tt)
            uniq.append(tt)
    if not uniq:
        return []

    hits: List[Dict[str, Any]] = []
    for ln in audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]:
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        p = Path(rec.get("extract_saved_as") or "")
        if not p.exists() or not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for tok in uniq:
            if tok.lower() not in lower:
                continue
            try:
                pat = re.compile(re.escape(tok), re.IGNORECASE)
            except re.error:
                continue
            m = pat.search(text)
            if not m:
                continue
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 160)
            snippet = text[start:end].replace("\n", " ")
            hits.append({
                "filename": rec.get("filename"),
                "sha256": rec.get("sha256"),
                "extract_saved_as": str(p),
                "offset": m.start(),
                "snippet": snippet,
            })
            if len(hits) >= limit:
                return hits
    return hits


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

    # Produce retrieval trace artifact for downstream gates.
    _ensure_retrieve_trace(topic=topic, domain_key=domain_key, outline=outline if isinstance(outline, list) else [])

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

    # 提前加载招标矩阵，供后续多处使用
    tender_matrix = load_tender_matrix()

    # Section 1.4: 审计追溯索引（本次使用证据来源）
    trace_lines = ["【审计追溯索引】"]
    trace_lines.append(f"- 招标矩阵：{'已加载' if tender_matrix else '未加载'}")
    # 已上传 KG
    try:
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        _ak = _get_active_kg()
        trace_lines.append(f"- 知识图谱：{_ak.get('file_name') if _ak else '未启用'}")
    except Exception:
        trace_lines.append("- 知识图谱：状态未知")
    # 资料上传
    try:
        from pathlib import Path as _Path
        _audit = _Path("backend/data/audit/ingest.jsonl")
        _cnt = len(_audit.read_text(encoding='utf-8').splitlines()) if _audit.exists() else 0
        trace_lines.append(f"- 已上传资料条数：{_cnt}")
    except Exception:
        trace_lines.append("- 已上传资料条数：未知")
    sections.append({"title": "审计追溯索引", "content": "\n".join(trace_lines)})

    # Section 1.5: 招标指数矩阵摘要（如已解析）
    if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
        tlines = ["【招标指数矩阵摘要】"]
        for it in tender_matrix.get("items", []):
            try:
                dim = it.get("dimension")
                weight = it.get("weight")
                kws = it.get("keywords") or []
                tlines.append(f"- {dim}：权重={weight} 关键词={';'.join(kws[:8])}")
            except Exception:
                continue
        sections.append({"title": "招标指标权重摘要", "content": "\n".join(tlines)})
    else:
        sections.append({"title": "招标指标权重摘要", "content": "尚未解析招标指数矩阵，请先 /autoplan/tender/parse。"})

    # Section 1.55: 清单统计摘要（如已解析）
    boq_data = load_boq_data()
    if isinstance(boq_data, dict) and boq_data.get("stats"):
        st = boq_data["stats"]
        lines = [
            "【清单统计摘要】",
            f"- 清单条目数：{st.get('item_count')}",
            f"- 工程量合计：{st.get('total_quantity')}",
            f"- 施工密度：{st.get('density')}",
        ]
        sections.append({"title": "清单统计摘要", "content": "\n".join(lines)})
    else:
        sections.append({"title": "清单统计摘要", "content": "尚未解析清单，请先 /autoplan/boq/parse。"})

    # Section 1.6: 重点施工控制清单（重难点/风险点/关键工序）
    if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
        ctl = ["【重点施工控制清单】"]
        keys = []
        for it in tender_matrix.get("items", []):
            dim = it.get("dimension")
            if str(dim) in ("重难点", "DIFFICULTY"):
                keys.extend(it.get("keywords") or [])
        keys = list(dict.fromkeys(keys))
        if keys:
            ctl.append(f"- 重点关键词：{';'.join(keys[:12])}")
            # 结合已上传 KG 检索验证
            _kc = _search_active_kg(" ".join(keys[:6]), top_k=3)
            if isinstance(_kc, dict) and _kc.get("results"):
                ctl.append("- 图谱证据：")
                for i, r in enumerate(_kc["results"], 1):
                    ctl.append(f"  {i}. {r.get('title')} score={r.get('score')}")
        else:
            ctl.append("- 未识别到重难点关键词，请补充招标矩阵。")
        sections.append({"title": "重点施工控制清单", "content": "\n".join(ctl)})

    # Section 1.7: 高分合规性检查清单（质量/安全/环保/进度）
    if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
        chk = ["【高分合规性检查清单】"]
        focus_dims = {"质量目标", "安全等级", "环保要求", "进度节点"}
        for it in tender_matrix.get("items", []):
            dim = str(it.get("dimension"))
            if dim in focus_dims:
                kws = it.get("keywords") or []
                chk.append(f"- {dim}：{';'.join(kws[:10]) if kws else '未提取关键词'}")
        sections.append({"title": "高分合规性检查清单", "content": "\n".join(chk)})

    # Section 2: Work Items (auto extract)
    # --- Retrieve evidence: build SuperKG snippet from /retrieve (traceable) ---
    try:
        from backend.retrieve_service import retrieve as _kg_retrieve
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

    # Section 2.3: Active KG evidence (user-uploaded knowledge graph)
    _kg_query = " ".join([str(topic or ""), str(domain_key or ""), "质量", "安全", "工期", "施工组织"]).strip()
    _kg_res = _search_active_kg(_kg_query, top_k=6)
    if isinstance(_kg_res, dict) and _kg_res.get("results"):
        _kl = [f"检索查询：{_kg_query}", f"命中条目数：{len(_kg_res['results'])}", ""]
        for i, r in enumerate(_kg_res["results"], 1):
            _kl.append(f"{i}. {r.get('title')}  score={r.get('score')}")
            _kl.append(f"   path：{r.get('path')}")
            _kl.append(f"   摘要：{(r.get('text') or '').strip()}")
            _kl.append("")
        sections.append({"title": "知识图谱证据摘要（已上传 KG）", "content": "\n".join(_kl).strip()})
    else:
        sections.append({"title": "知识图谱证据摘要（已上传 KG）", "content": "当前未启用知识图谱或检索为空。请先 /autoplan/kg/upload 并 /autoplan/kg/activate。"})

    # Section 2.5: Ingested docs evidence (tender/design/bill/drawing)
    _doc_query = " ".join([str(topic or ""), str(domain_key or ""), "质量", "安全", "工期", "施工", "图纸", "清单"]).strip()
    _doc_hits = _search_ingested_docs(_doc_query, limit=8)
    if _doc_hits:
        _dl = [f"检索查询：{_doc_query}", f"命中条目数：{len(_doc_hits)}", ""]
        for i, h in enumerate(_doc_hits, 1):
            _dl.append(f"{i}. {h.get('filename')}  offset={h.get('offset')}")
            _dl.append(f"   extract：{h.get('extract_saved_as')}")
            _dl.append(f"   摘要：{h.get('snippet')}")
            _dl.append("")
        sections.append({"title": "招标/清单/图纸证据摘要", "content": "\n".join(_dl).strip()})
    else:
        sections.append({"title": "招标/清单/图纸证据摘要", "content": "未从已上传的资料中检索到证据，请先上传招标/清单/图纸等文件。"})

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
            "content": "未能从 selected_packs 中解析到 work_items（pack schema 可能不含 work_items 字段）。未能从 selected_packs 中解析到 work_items（pack schema 可能不含 work_items 字段）。已通过“SuperKG 工序样例（检索证据）”章节提供检索证据与追溯信息。",
        })

    # Sections for each outline item (retrieve-based MVP)
    try:
        from backend.retrieve_service import retrieve as _kg_retrieve_local
    except Exception:
        _kg_retrieve_local = None

    gap_summary: List[str] = []

    section_meta: List[Dict[str, Any]] = []

    for i, t in enumerate(outline, 1):
        title = str(t).strip() or f"章节{i}"
        q = " ".join([str(topic or ""), str(domain_key or ""), title, "质量控制", "安全风险", "控制措施", "验收标准", "资源配置"]).strip()
        retr = None
        if _kg_retrieve_local is not None:
            try:
                retr = _kg_retrieve_local(q, top_k=4)
            except Exception:
                retr = None
        _lines = []
        _lines.append(f"检索查询：{q}")

        # 章节优先级标注（高权重优先）
        pr = 0.0
        if isinstance(tender_matrix, dict):
            pr = _calc_dimension_priority(tender_matrix, title)
            _lines.append(f"章节优先级权重：{pr}")
        if isinstance(retr, dict) and isinstance(retr.get('results'), list) and retr['results']:
            _lines.append(f"命中条目数：{len(retr['results'])}（展示前 4 条）")
            _lines.append("")
            for idx, r in enumerate(retr['results'][:4], 1):
                _lines.append(f"{idx}) {r.get('title')}（{r.get('source')}）score={r.get('score')} sha256={r.get('sha256')}")
                _lines.append(f"   path：{r.get('path')}")
                txt = (r.get('text') or '').strip()
                if len(txt) > 900:
                    txt = txt[:900] + '…'
                _lines.append('   摘要：')
                _lines.append(txt)
                _lines.append('')
            _lines.append('备注：以上为检索证据摘要（MVP）。后续可接入 LLM 进行更自然的技术标语言组稿，并继续引用证据锚点。')
        else:
            _lines.append('未检索到证据：请补充更具体的 topic/outline 关键词，或完善 BasePack 内容。')

        # 章节级：评分点覆盖率（基于招标矩阵关键词）
        if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
            all_kws = []
            for it in tender_matrix.get("items", []):
                all_kws.extend(it.get("keywords") or [])
            all_kws = list(dict.fromkeys([k for k in all_kws if isinstance(k, str) and k.strip()]))[:60]
            cov = _calc_keyword_coverage("\n".join(_lines), all_kws)
            _lines.append("")
            _lines.append("【评分点覆盖率】")
            _lines.append(f"- 覆盖率：{cov['coverage']*100:.1f}%")
            _lines.append(f"- 已覆盖：{';'.join(cov['covered'][:12]) if cov['covered'] else '无'}")
            _lines.append(f"- 未覆盖：{';'.join(cov['missed'][:12]) if cov['missed'] else '无'}")
            # 缺口汇总
            if cov["missed"]:
                gap_summary.append(f"{title}：{';'.join(cov['missed'][:12])}")

        # 章节级：清单工序绑定（BoQ -> 工序 -> 章节）
        if isinstance(boq_data, dict):
            # 高权重章节增加工序密度
            priority = _calc_dimension_priority(tender_matrix, title)
            proc_limit = 10 if priority >= 0.7 else 6
            procs = _select_boq_processes(boq_data, limit=proc_limit)
            if procs:
                _lines.append("")
                _lines.append("【清单工序绑定】")
                for p in procs:
                    _lines.append(f"- {p}")
            else:
                _lines.append("")
                _lines.append("【清单工序绑定】未发现可用工序，请先解析清单。")

        # 章节级：清单资源绑定（工序 -> 资源）
        if isinstance(boq_data, dict):
            # 高权重章节增加资源密度
            priority = _calc_dimension_priority(tender_matrix, title)
            res_limit = 14 if priority >= 0.7 else 8
            res = _select_boq_resources(boq_data, limit=res_limit)
            _lines.append("")
            _lines.append("【清单资源绑定】")
            if res:
                _lines.append(f"- 资源清单：{';'.join(res)}")
            else:
                _lines.append("- 未发现资源清单，请先解析清单。")

        # 章节级：招标指数矩阵绑定（按关键词匹配）
        if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
            _lines.append("")
            _lines.append("【招标指标绑定】")
            matched = 0
            for it in tender_matrix.get("items", []):
                dim = it.get("dimension")
                weight = it.get("weight")
                kws = it.get("keywords") or []
                if any(k in title for k in kws) or any(k in title for k in [str(dim)]):
                    _lines.append(f"- {dim}（权重={weight}）关键词：{';'.join(kws[:6])}")
                    matched += 1
            if matched == 0:
                _lines.append("- 未命中：建议补充章节关键词或优化招标矩阵关键词")

        # 章节级：扣分项/废标风险提示（高分保障）
        if isinstance(tender_matrix, dict) and tender_matrix.get("items"):
            _lines.append("")
            _lines.append("【扣分项/废标风险提示】")
            risk_hits = 0
            for it in tender_matrix.get("items", []):
                dim = it.get("dimension")
                if str(dim) not in ("扣分项", "PENALTY"):
                    continue
                kws = it.get("keywords") or []
                if any(k in _lines[-1] for k in kws) or any(k in title for k in kws):
                    _lines.append(f"- 可能触发扣分项：{';'.join(kws[:8])}")
                    risk_hits += 1
            if risk_hits == 0:
                _lines.append("- 未发现明显扣分项命中（仍需人工复核）。")

        # 章节级：已上传 KG 证据绑定（强制输出证据）
        _kg_q = " ".join([str(topic or ""), title, "施工组织", "质量", "安全", "工期"]).strip()
        _kg_hits = _search_active_kg(_kg_q, top_k=3)
        if isinstance(_kg_hits, dict) and _kg_hits.get("results"):
            _lines.append("")
            _lines.append("【知识图谱证据绑定】")
            for j, kr in enumerate(_kg_hits["results"], 1):
                _lines.append(f"- {j}. {kr.get('title')} score={kr.get('score')}")
                _lines.append(f"  path：{kr.get('path')}")
                _lines.append(f"  摘要：{(kr.get('text') or '').strip()}")
        else:
            _lines.append("")
            _lines.append("【知识图谱证据绑定】未命中，请先上传并激活 KG，或补充关键词。")

        # 章节级：招标/清单/图纸证据绑定
        _doc_q = " ".join([str(topic or ""), title, "招标", "清单", "图纸", "质量", "安全", "工期"]).strip()
        _doc_hits = _search_ingested_docs(_doc_q, limit=3)
        if _doc_hits:
            _lines.append("")
            _lines.append("【招标/清单/图纸证据绑定】")
            for j, h in enumerate(_doc_hits, 1):
                _lines.append(f"- {j}. {h.get('filename')} offset={h.get('offset')}")
                _lines.append(f"  extract：{h.get('extract_saved_as')}")
                _lines.append(f"  摘要：{h.get('snippet')}")
        else:
            _lines.append("")
            _lines.append("【招标/清单/图纸证据绑定】未命中，请先上传资料或补充章节关键词。")
        sections.append({'title': title, 'content': '\n'.join(_lines).strip()})
        section_meta.append({
            "title": title,
            "priority": pr,
            "has_kg": bool(_search_active_kg(_kg_q, top_k=1).get("results")),
            "has_docs": bool(_search_ingested_docs(_doc_q, limit=1)),
        })

    # 末尾：缺口清单汇总 + 整改建议
    if gap_summary:
        lines = ["【缺口清单汇总】"]
        lines.extend([f"- {g}" for g in gap_summary[:30]])
        lines.append("")
        lines.append("【整改建议】")
        lines.append("- 根据未覆盖关键词补充对应章节的技术标准/措施/验收要求。")
        lines.append("- 优先补齐“扣分项/废标项”相关描述，确保合规。")
        lines.append("- 对关键工序增加质量/安全/工期/环保四维措施闭环。")
        sections.append({"title": "缺口清单与整改建议", "content": "\n".join(lines)})

    # 章节元信息附录（供后续评分系统读取）
    if section_meta:
        lines = ["【章节元信息】"]
        for m in section_meta:
            lines.append(f"- {m['title']} | priority={m['priority']} | kg={m['has_kg']} | docs={m['has_docs']}")
        sections.append({"title": "章节元信息附录", "content": "\n".join(lines)})

    # 末尾：证据摘要附录（写入导出 DOCX 便于交付复核）
    try:
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        from backend.zhifei_autoplan.tender_store import load_tender_matrix as _load_tender_matrix
        _ak = _get_active_kg()
        _ing = Path("backend/data/audit/ingest.jsonl")
        _ing_cnt = len(_ing.read_text(encoding="utf-8").splitlines()) if _ing.exists() else 0
        _sel = (kg_context or {}).get("selected_packs") or []
        _sel_names = []
        for _p in _sel:
            if isinstance(_p, dict):
                _sel_names.append(_p.get("name") or _p.get("path"))
            else:
                _sel_names.append(str(_p))
        evidence_lines = [
            "【证据摘要附录】",
            f"- 招标矩阵：{'已加载' if _load_tender_matrix() else '未加载'}",
            f"- 知识图谱：{_ak.get('file_name') if _ak else '未启用'}",
            f"- 知识图谱 SHA256：{_ak.get('sha256') if _ak else 'N/A'}",
            f"- 已上传资料条数：{_ing_cnt}",
            f"- 选用 KG Packs：{'; '.join([n for n in _sel_names if n]) if _sel_names else '无'}",
        ]
        sections.append({"title": "证据摘要附录", "content": "\n".join(evidence_lines)})
    except Exception:
        sections.append({"title": "证据摘要附录", "content": "证据摘要生成失败，请检查审计数据。"})

    return sections
