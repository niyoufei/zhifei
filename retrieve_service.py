# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parent
BUILD_DIR = BACKEND_DIR / "build"
BUILD_DIR.mkdir(exist_ok=True)

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _safe_load_json(p: Path) -> Tuple[Optional[Any], Optional[str]]:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
        return json.loads(txt), None
    except Exception as e:
        return None, repr(e)

def _tokenize(query: str) -> List[str]:
    q = (query or "").strip()
    if not q:
        return []
    toks = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", q)
    toks = [t.strip() for t in toks if t.strip()]
    if not toks:
        toks = [q]
    seen = set()
    out: List[str] = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def _render(v: Any, max_len: int = 800) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        s = v
    elif isinstance(v, (int, float, bool)):
        s = str(v)
    else:
        try:
            s = json.dumps(v, ensure_ascii=False)
        except Exception:
            s = str(v)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s

def _score(text: str, tokens: List[str]) -> float:
    if not text or not tokens:
        return 0.0
    t = text.lower()
    score = 0.0
    for tok in tokens:
        tok_l = tok.lower().strip()
        if not tok_l:
            continue
        c = t.count(tok_l)
        if c:
            score += float(c)
    norm = max(1.0, len(text) / 800.0)
    return score / norm

def _extract_work_item_like(d: Dict[str, Any]) -> bool:
    keys = set(d.keys())
    hit = 0
    for k in [
        "工序名称","操作步骤","设备材料","关键参数","风险点","控制措施","验证方法",
        "资源配置","成品保护","质量控制","安全文明施工","环保要点"
    ]:
        if k in keys:
            hit += 1
    return ("工序名称" in keys and hit >= 2) or hit >= 5

def _build_work_item_text(item: Dict[str, Any]) -> Tuple[str, str]:
    title = item.get("工序名称") or item.get("name") or item.get("title") or item.get("id") or "work_item"
    parts: List[str] = []
    order = [
        "工序名称","操作步骤","主要设备材料","设备材料","关键参数","风险点","控制措施","验证方法",
        "资源配置","关键线路","工期影响","最小间隔","评分点","可追溯字段","引用规范","图纸索引","清单编码"
    ]
    for k in order:
        v = item.get(k)
        if v not in (None, "", [], {}):
            parts.append(f"{k}: {_render(v, max_len=1200)}")
    for k, v in item.items():
        if k in order:
            continue
        if v in (None, "", [], {}):
            continue
        parts.append(f"{k}: {_render(v, max_len=800)}")
    text = "\n".join(parts).strip()
    return str(title), text

def _extract_docs_from_obj(obj: Any, source: str) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    seen: set = set()

    def add_doc(title: str, text: str, path: str):
        text = (text or "").strip()
        if len(text) < 40:
            return
        h = _sha256_text(source + "|" + title + "|" + text)
        if h in seen:
            return
        seen.add(h)
        docs.append({
            "source": source,
            "title": title,
            "text": text,
            "path": path,
            "sha256": _sha256_text(text),
        })

    def walk(x: Any, path: str):
        if isinstance(x, dict):
            if _extract_work_item_like(x):
                title, text = _build_work_item_text(x)
                add_doc(title, text, path)

            if isinstance(x.get("subdivisions"), list):
                for i, sub in enumerate(x.get("subdivisions") or []):
                    walk(sub, f"{path}.subdivisions[{i}]")
            if isinstance(x.get("work_items"), list):
                for i, wi in enumerate(x.get("work_items") or []):
                    walk(wi, f"{path}.work_items[{i}]")
            if isinstance(x.get("sections"), list):
                for i, sec in enumerate(x.get("sections") or []):
                    walk(sec, f"{path}.sections[{i}]")

            if isinstance(x.get("advanced"), dict):
                adv = x.get("advanced") or {}
                for k, v in adv.items():
                    if isinstance(v, list):
                        txt = "\n".join([_render(it, 200) for it in v if _render(it, 200)])
                        add_doc(f"advanced/{k}", txt, f"{path}.advanced.{k}")
                    else:
                        add_doc(f"advanced/{k}", _render(v, 1200), f"{path}.advanced.{k}")

            for k, v in x.items():
                if k in ("subdivisions","work_items","sections","advanced"):
                    continue
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}")

        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")

    walk(obj, "$")
    return docs

def _load_selected_pack_paths() -> Tuple[List[Path], Dict[str, Any]]:
    info: Dict[str, Any] = {"source": None, "details": None}
    kg_ctx = BUILD_DIR / "kg_context.json"
    if kg_ctx.exists():
        obj, err = _safe_load_json(kg_ctx)
        if isinstance(obj, dict):
            sel = obj.get("selected_packs") or []
            paths: List[Path] = []
            for it in sel:
                if isinstance(it, dict):
                    p = it.get("path") or it.get("file") or it.get("name")
                else:
                    p = str(it)
                if not p:
                    continue
                pp = Path(p)
                if not pp.is_absolute():
                    pp = BACKEND_DIR / pp
                paths.append(pp)
            paths2 = [p for p in paths if p.exists()]
            if paths2:
                info["source"] = "build/kg_context.json"
                # inject kg_pack (from build/kg_context.json) for traceability
                try:
                    import json as _json
                    _kgp = None
                    _p = BUILD_DIR / "kg_context.json"
                    if _p.exists():
                        _kgp = _json.loads(_p.read_text(encoding="utf-8")).get("kg_pack")
                    info["kg_pack"] = _kgp
                except Exception as _e:
                    info["kg_pack"] = {"error": str(_e)}
                info["details"] = {"selected_packs.count": len(paths2)}
                return paths2, info

    try:
        import kg_loader
        cfg = kg_loader.load_kg_config()
        paths = kg_loader.get_base_pack_paths(cfg)
        paths2 = [Path(p) for p in paths if Path(p).exists()]
        info["source"] = "kg_config.base_packs"
        info["details"] = {"base_packs.count": len(paths2)}
        return paths2, info
    except Exception as e:
        info["source"] = "kg_config.base_packs"
        info["details"] = {"error": repr(e)}
        return [], info

def retrieve(query: str, top_k: int = 10) -> Dict[str, Any]:
    query = (query or "").strip()
    top_k = int(top_k or 10)
    top_k = max(1, min(top_k, 50))

    tokens = _tokenize(query)
    pack_paths, pack_info = _load_selected_pack_paths()
    used = [{"path": str(p), "name": p.name, "exists": p.exists()} for p in pack_paths]

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    all_docs: List[Dict[str, Any]] = []
    for p in pack_paths:
        obj, err = _safe_load_json(p)
        if err:
            errors.append({"file": str(p), "error": err})
            continue
        docs = _extract_docs_from_obj(obj, source=p.name)
        if not docs:
            txt = _render(obj, max_len=4000)
            docs = [{"source": p.name, "title": p.name, "text": txt, "path": "$", "sha256": _sha256_text(txt)}]
        all_docs.extend(docs)

    scored = []
    for d in all_docs:
        sc = _score(d.get("text") or "", tokens)
        if sc <= 0:
            continue
        scored.append((sc, d))
    scored.sort(key=lambda x: x[0], reverse=True)

    for sc, d in scored[:top_k]:
        txt = d.get("text") or ""
        brief = txt if len(txt) <= 900 else (txt[:900] + "…")
        results.append({
            "source": d.get("source"),
            "title": d.get("title"),
            "text": brief,
            "score": round(float(sc), 6),
            "path": d.get("path"),
            "sha256": d.get("sha256"),
        })

    trace = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "tokens": tokens,
        "top_k": top_k,
        "pack_info": pack_info,
        "used_packs": used,
        "docs_scanned": len(all_docs),
        "results": results,
        "errors": errors,
    }
    out = BUILD_DIR / "retrieve.json"
    # inject kg_pack (top-level retrieve.json) for traceability
    try:
        import json as _json
        import hashlib as _hashlib
        from pathlib import Path as _Path
        _root = _Path(__file__).resolve().parent
        _kgp = None
        # 1) prefer build/kg_context.json (already contains kg_pack)
        _kc = _root / "build" / "kg_context.json"
        if _kc.exists():
            _kgp = _json.loads(_kc.read_text(encoding="utf-8")).get("kg_pack")
        # 2) fallback: compute from kg_config.json + manifest
        if not _kgp:
            _cfgp = _root / "kg_config.json"
            if _cfgp.exists():
                _cfg = _json.loads(_cfgp.read_text(encoding="utf-8"))
                _active = _cfg.get("active_pack") if isinstance(_cfg, dict) else None
                _packs = _cfg.get("packs") if isinstance(_cfg, dict) else None
                _pcfg = _packs.get(_active, {}) if isinstance(_packs, dict) and _active else {}
                _base_dir = _pcfg.get("base_dir") or _pcfg.get("base_path") or _pcfg.get("root") or "."
                _pack_version = _pcfg.get("pack_version") or _pcfg.get("version") or _active
                _manifest_rel = _pcfg.get("manifest") or f"{_base_dir}/manifest.json"
                _mp = (_root / _manifest_rel).resolve()
                _m_exists = bool(_mp.exists())
                _m_sha = None
                if _m_exists:
                    h = _hashlib.sha256()
                    with _mp.open("rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
                    _m_sha = h.hexdigest()
                _kgp = {
                    "active_pack": _active,
                    "pack_version": _pack_version,
                    "base_dir": _base_dir,
                    "manifest": str(_manifest_rel),
                    "manifest_exists": _m_exists,
                    "manifest_sha256": _m_sha,
                    "schema_version": _pcfg.get("schema_version") if isinstance(_pcfg, dict) else None,
                    "created_at": _pcfg.get("created_at") if isinstance(_pcfg, dict) else None,
                }
        if isinstance(trace, dict) and "kg_pack" not in trace:
            trace["kg_pack"] = _kgp
    except Exception:
        pass

    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "results": results,
        "trace_saved_at": str(out),
        "stats": {"docs_scanned": len(all_docs), "used_packs": len(pack_paths)},
        "errors": errors,
    }
