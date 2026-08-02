from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend import kg_loader


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_NUMERIC_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|次|人|台|套|%|MPa|kN|℃|dB|m2|m3)",
    re.IGNORECASE,
)
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}")
_PROJECT_KG_GLOB = "ZF-KG-*.json"
_ZF_ALIAS_MAP: Dict[str, List[str]] = {
    "housing": ["房建", "建筑工程", "主体结构"],
    "hospital": ["医院", "医疗", "医疗建筑"],
    "decoration": ["装修", "装饰", "精装修"],
    "exterior": ["室外附属", "附属工程"],
    "ancillary": ["附属工程", "室外工程"],
    "municipal": ["市政"],
    "drainage": ["排水", "雨污", "市政排水"],
    "road": ["道路", "市政道路", "路面"],
    "gas": ["燃气", "市政燃气"],
    "wtp": ["排水站", "泵站", "污水提升"],
    "bridge": ["桥梁", "市政桥梁"],
    "river": ["河道", "河道治理", "护岸"],
    "sponge": ["海绵城市", "雨洪管理"],
    "highway": ["公路", "公路工程", "路基路面"],
    "tunnel": ["隧道", "市政隧道"],
    "water": ["水利", "给排水"],
    "hydro": ["水利水电", "水电工程"],
    "district": ["供热", "区域能源"],
    "heating": ["供热", "热力"],
    "power": ["电力", "变配电"],
    "energy": ["能源", "电力能源"],
    "hydraulic": ["水利枢纽", "闸门", "泄洪"],
    "hub": ["枢纽", "水利枢纽"],
    "waste": ["固废", "垃圾焚烧"],
    "rail": ["轨道", "铁路", "轨道交通"],
    "transit": ["轨道交通", "地铁"],
    "petrochemical": ["石油化工", "化工装置"],
    "data": ["数据中心", "机房", "数据机房"],
    "airport": ["机场", "航站楼"],
    "port": ["港航", "港口", "码头"],
    "harbor": ["港航", "港池", "航道"],
    "railway": ["铁路", "高铁"],
    "industrial": ["工业", "工业管道"],
    "pipeline": ["管道", "工艺管道"],
    "utility": ["综合管廊", "管廊"],
    "waterproofing": ["防水", "防渗"],
    "intelligent": ["智能化", "信息化"],
    "weak": ["弱电", "弱电系统"],
    "current": ["弱电", "通信弱电"],
    "fire": ["消防", "消防系统"],
    "hvac": ["暖通", "空调通风"],
    "communication": ["通信", "通信工程"],
    "mep": ["机电", "机电安装"],
    "reinforcement": ["加固", "结构加固"],
    "steel": ["钢结构"],
    "prefabricated": ["装配式", "预制构件"],
    "excavation": ["深基坑", "土方开挖"],
    "crane": ["起重", "塔吊"],
    "lifting": ["吊装", "大型吊装"],
    "demolition": ["拆除"],
    "curtain": ["幕墙"],
    "scaffolding": ["脚手架"],
    "formwork": ["模板", "模板工程"],
    "bim": ["BIM", "数字建造"],
    "safety": ["安全文明", "安全管理"],
    "civilization": ["文明施工", "安全文明"],
    "fournew": ["四新技术", "新技术"],
    "smartsite": ["智慧工地", "信息化管理"],
    "foundation": ["基础工程", "地基基础"],
    "offshore": ["海上工程", "海工"],
    "wind": ["风电", "海上风电"],
    "temporary": ["临建", "临时工程"],
    "layout": ["总平面布置", "施工平面"],
    "green": ["绿色工地", "绿色施工"],
}


def _normalize_domain_token(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "").strip().lower())


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[;,，；、/|]+", value)
        return [str(x).strip() for x in parts if str(x).strip()]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _domain_seed_map() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for key, aliases in _ZF_ALIAS_MAP.items():
        seeds = [key]
        seeds.extend([str(x).strip() for x in aliases if str(x).strip()])
        if key == "bridge":
            seeds.extend(["市政桥梁工程", "桥梁工程"])
        elif key == "road":
            seeds.extend(["市政道路工程", "道路工程"])
        elif key == "hydraulic":
            seeds.extend(["水利工程", "水利枢纽工程"])
        elif key == "mep":
            seeds.extend(["机电安装工程", "弱电工程", "智能化工程"])
        elif key == "green":
            seeds.extend(["绿色建造", "绿色施工"])
        deduped: List[str] = []
        seen: set[str] = set()
        for seed in seeds:
            norm = _normalize_domain_token(seed)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(seed)
        out[key] = deduped
    return out


_DOMAIN_SEED_MAP = _domain_seed_map()


def _normalize_domain_keys(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in values:
        text = _norm_text(raw)
        if not text:
            continue
        direct = _normalize_domain_token(text)
        canonical = ""
        for domain, seeds in _DOMAIN_SEED_MAP.items():
            if any(_normalize_domain_token(seed) in direct for seed in seeds):
                canonical = domain
                break
        if not canonical:
            canonical = direct
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def _infer_domain_keys_from_text(text: str) -> List[str]:
    merged = _normalize_domain_token(text)
    if not merged:
        return []
    hits: List[str] = []
    for domain, seeds in _DOMAIN_SEED_MAP.items():
        for seed in seeds:
            if _normalize_domain_token(seed) in merged:
                hits.append(domain)
                break
    return _dedup_keep_order(hits, limit=24)


def _project_domain_tag_from_path(file_path: Path, root: Path) -> str:
    try:
        rel = file_path.resolve().relative_to(root.resolve())
    except Exception:
        try:
            rel = file_path.relative_to(root)
        except Exception:
            return ""
    parts = list(rel.parts)
    if len(parts) >= 2:
        return str(parts[0]).strip()
    return ""


def _extract_domain_tags_from_content(content: Any) -> List[str]:
    if not isinstance(content, dict):
        return []
    candidates: List[str] = []
    for key in ("domain_tag", "domain_tags", "domain", "domains", "工程领域", "专业领域", "领域"):
        candidates.extend(_coerce_list(content.get(key)))
    return _normalize_domain_keys(candidates)


def _resolve_domain_tags(*, filename: str, graph_name: str, keyword_hints: List[str], content: Any, path_hint: str = "") -> List[str]:
    tags = _extract_domain_tags_from_content(content)
    tags.extend(_normalize_domain_keys(_coerce_list(path_hint)))
    if not tags:
        tags.extend(_infer_domain_keys_from_text("\n".join([filename, graph_name] + list(keyword_hints or []))))
    if not tags:
        tags = ["general"]
    return _dedup_keep_order(tags, limit=12)


def _domains_overlap(left: Iterable[Any], right: Iterable[Any]) -> bool:
    a = set(_normalize_domain_keys(left))
    b = set(_normalize_domain_keys(right))
    if not a or not b:
        return False
    if "general" in a or "general" in b:
        return True
    return bool(a.intersection(b))


def _norm_text(v: Any) -> str:
    return str(v or "").strip()


def _dedup_keep_order(items: Iterable[str], limit: int | None = None) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in items:
        s = _norm_text(raw)
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if limit and len(out) >= limit:
            break
    return out


def _tokenize(text: str) -> List[str]:
    toks = [t.strip() for t in _TOKEN_RE.findall(text or "")]
    toks = [t for t in toks if len(t) >= 2]
    return _dedup_keep_order(toks, limit=200)


def _iter_project_kg_roots() -> List[Path]:
    roots: List[Path] = []
    env_root = _norm_text(os.environ.get("ZF_KG_ROOT"))
    if env_root:
        roots.append(Path(env_root).expanduser())
    roots.extend(
        [
            Path("知识图谱"),
            Path("backend/知识图谱"),
            Path("/Users/youfeini/Desktop/文档生成系统/知识图谱"),
        ]
    )
    out: List[Path] = []
    seen: set[str] = set()
    for p in roots:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        key = str(rp)
        if key in seen:
            continue
        seen.add(key)
        if rp.exists() and rp.is_dir():
            out.append(rp)
    return out


def _collect_scalar_snippets(obj: Any, *, max_items: int = 220, max_depth: int = 4) -> List[str]:
    out: List[str] = []

    def walk(x: Any, depth: int) -> None:
        if len(out) >= max_items or depth > max_depth:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                if len(out) >= max_items:
                    return
                ks = _norm_text(k)
                if ks:
                    out.append(ks)
                if isinstance(v, (dict, list)):
                    walk(v, depth + 1)
                else:
                    vs = _norm_text(v)
                    if vs:
                        out.append(vs)
        elif isinstance(x, list):
            for v in x:
                if len(out) >= max_items:
                    return
                if isinstance(v, (dict, list)):
                    walk(v, depth + 1)
                else:
                    vs = _norm_text(v)
                    if vs:
                        out.append(vs)

    walk(obj, 0)
    return out[:max_items]


def _extract_keyword_hints(filename: str, obj: Any) -> List[str]:
    base = Path(filename).stem
    file_terms = re.split(r"[-_/.\s]+", base)
    text_pool: List[str] = [t for t in file_terms if _norm_text(t)]
    if filename.startswith("ZF-KG-"):
        for t in file_terms:
            keys = _ZF_ALIAS_MAP.get(str(t).lower()) or []
            text_pool.extend(keys)
        # Combine two-token aliases like municipal+bridge -> 市政桥梁
        low_terms = {str(t).lower() for t in file_terms}
        if {"municipal", "bridge"}.issubset(low_terms):
            text_pool.append("市政桥梁")
        if {"municipal", "drainage"}.issubset(low_terms):
            text_pool.append("市政排水")
        if {"power", "energy"}.issubset(low_terms):
            text_pool.append("电力能源")
        if {"data", "center"}.issubset(low_terms) or {"data", "centers"}.issubset(low_terms):
            text_pool.append("数据机房")
    text_pool.extend(_collect_scalar_snippets(obj, max_items=240, max_depth=4))
    tokens = _tokenize("\n".join(text_pool))
    # Keep some uppercase/literal tokens so e.g. HVAC/MEP remain directly matchable.
    literal_ascii = []
    for t in _ASCII_TOKEN_RE.findall(base):
        if len(t) >= 2:
            literal_ascii.append(t)
    return _dedup_keep_order(tokens + literal_ascii, limit=180)


def _graph_display_name(filename: str, obj: Any) -> str:
    if isinstance(obj, dict):
        for k in ("cn_name", "name", "title", "graph_name", "图谱名称", "工程领域"):
            v = _norm_text(obj.get(k))
            if v:
                return v
    return Path(filename).stem


@lru_cache(maxsize=1)
def _load_domain_map() -> Dict[str, Any]:
    path: Path | None = None
    try:
        path = kg_loader.get_domain_map_path()
    except Exception:
        fallback = Path("backend/SuperKG-DOMAIN-MAP.json")
        if fallback.exists():
            path = fallback
    if not path or not path.exists():
        return {"knowledge_graph_library": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"knowledge_graph_library": []}


@lru_cache(maxsize=1)
def _load_pack_index() -> Dict[str, Dict[str, Any]]:
    cfg: Dict[str, Any] | None = None
    try:
        cfg = kg_loader.load_kg_config()
        paths = kg_loader.get_base_pack_paths(cfg)
    except Exception:
        paths = [
            Path("backend/Universal_Base_Pack.json"),
            Path("backend/Civil_Basic_Pack.json"),
            Path("backend/Transport_Infra_Pack.json"),
            Path("backend/Energy_Industrial_Pack.json"),
            Path("backend/Risk_Specialist_Pack.json"),
            Path("backend/Special_Medical_Pack.json"),
        ]

    out: Dict[str, Dict[str, Any]] = {}
    for p in paths:
        if not p.exists():
            continue
        try:
            arr = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for it in arr:
            if not isinstance(it, dict):
                continue
            fn = _norm_text(it.get("filename"))
            if not fn:
                continue
            if fn not in out:
                keyword_hints = _extract_keyword_hints(fn, it.get("content"))
                graph_name = _graph_display_name(fn, it.get("content"))
                out[fn] = {
                    "filename": fn,
                    "pack_path": str(p),
                    "content": it.get("content"),
                    "content_path": "",
                    "source": "base_pack",
                    "keyword_hints": keyword_hints,
                    "graph_name": graph_name,
                    "domain_tags": _resolve_domain_tags(
                        filename=fn,
                        graph_name=graph_name,
                        keyword_hints=keyword_hints,
                        content=it.get("content"),
                    ),
                }
    # Merge project-embedded ZF-KG files into the same runtime index.
    for root in _iter_project_kg_roots():
        for fp in sorted(root.rglob(_PROJECT_KG_GLOB)):
            if not fp.exists() or not fp.is_file():
                continue
            try:
                obj = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            fn = fp.name
            keyword_hints = _extract_keyword_hints(fn, obj)
            graph_name = _graph_display_name(fn, obj)
            path_domain = _project_domain_tag_from_path(fp, root)
            out[fn] = {
                "filename": fn,
                "pack_path": str(root),
                "content": obj,
                "content_path": str(fp),
                "source": "project_kg",
                "keyword_hints": keyword_hints,
                "graph_name": graph_name,
                "domain_tags": _resolve_domain_tags(
                    filename=fn,
                    graph_name=graph_name,
                    keyword_hints=keyword_hints,
                    content=obj,
                    path_hint=path_domain,
                ),
            }
    return out


def _extract_graph_docs(
    obj: Any,
    *,
    graph_file: str,
    graph_name: str,
    domain_tags: List[str] | None = None,
    path: str = "$",
) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []

    def add_doc(title: str, text: str, p: str) -> None:
        t = _norm_text(text)
        if len(t) < 20:
            return
        docs.append(
            {
                "title": _norm_text(title) or "图谱节点",
                "text": t[:1400],
                "path": p,
                "graph_file": graph_file,
                "graph_name": graph_name or graph_file,
                "logical_node": f"{graph_file}#{p}",
                "domain_tags": _normalize_domain_keys(domain_tags or []),
            }
        )

    def walk(x: Any, p: str) -> None:
        if isinstance(x, dict):
            title = (
                x.get("工序名称")
                or x.get("节点")
                or x.get("name")
                or x.get("title")
                or x.get("章节")
                or x.get("内容")
            )
            parts: List[str] = []
            for k, v in x.items():
                if v in (None, "", [], {}):
                    continue
                if isinstance(v, (dict, list)):
                    continue
                vs = _norm_text(v)
                if not vs:
                    continue
                parts.append(f"{k}: {vs}")
            if title and parts:
                add_doc(str(title), "\n".join(parts), p)
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    walk(v, f"{p}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")

    walk(obj, path)
    return docs


@lru_cache(maxsize=256)
def _docs_for_graph_file(graph_file: str, graph_name: str) -> List[Dict[str, Any]]:
    meta = _load_pack_index().get(graph_file) or {}
    content = meta.get("content")
    if content is None:
        cp = _norm_text(meta.get("content_path"))
        if cp:
            p = Path(cp)
            if p.exists():
                try:
                    content = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    content = None
    if content is None:
        return []
    domain_tags = _normalize_domain_keys(meta.get("domain_tags") or [])
    return _extract_graph_docs(content, graph_file=graph_file, graph_name=graph_name, domain_tags=domain_tags)


def _classify_graph_tier(filename: str, graph_name: str) -> int:
    name = f"{filename} {graph_name}".lower()
    if any(x in name for x in ("-01-", "master", "ultimate", "主控", "终极", "housing", "bridge", "road", "highway", "hydro", "power")):
        return 0
    if any(x in name for x in ("general", "universal", "safety", "green", "fournew", "通用", "安全文明", "绿色")):
        return 2
    return 1


def _record_for_meta(meta: Dict[str, Any], *, score: int, hits: List[str], tier: int | None = None) -> Dict[str, Any]:
    filename = _norm_text(meta.get("filename"))
    graph_name = _norm_text(meta.get("graph_name")) or Path(filename).stem
    t = _classify_graph_tier(filename, graph_name) if tier is None else int(tier)
    return {
        "tier": t,
        "filename": filename,
        "graph_name": graph_name,
        "keywords": list(meta.get("keyword_hints") or []),
        "hit_keywords": _dedup_keep_order(hits, limit=20),
        "score": int(score),
        "available": True,
        "source": _norm_text(meta.get("source")) or "project_kg",
        "domain_tags": _normalize_domain_keys(meta.get("domain_tags") or []),
    }


def extract_engineering_keywords(
    *,
    topic: str | None = None,
    outline: List[str] | None = None,
    requirements: List[str] | None = None,
    tender: Dict[str, Any] | None = None,
) -> List[str]:
    parts: List[str] = []
    if topic:
        parts.append(str(topic))
    if isinstance(outline, list):
        parts.extend([_norm_text(x) for x in outline if _norm_text(x)])
    if isinstance(requirements, list):
        parts.extend([_norm_text(x) for x in requirements if _norm_text(x)])
    if isinstance(tender, dict):
        parts.extend([_norm_text(x) for x in (tender.get("outline") or []) if _norm_text(x)])
        for it in (tender.get("items") or [])[:240]:
            if not isinstance(it, dict):
                continue
            parts.append(_norm_text(it.get("dimension")))
            parts.extend([_norm_text(k) for k in (it.get("keywords") or [])[:20] if _norm_text(k)])
    corpus = "\n".join(parts)
    if not corpus.strip():
        return []

    base_tokens = _tokenize(corpus)
    # Pull in domain-map keywords that are actually present in the corpus.
    dm = _load_domain_map()
    map_tokens: List[str] = []
    for grp in dm.get("knowledge_graph_library") or []:
        if not isinstance(grp, dict):
            continue
        for m in grp.get("maps") or []:
            if not isinstance(m, dict):
                continue
            for kw in m.get("keywords") or []:
                kws = _norm_text(kw)
                if kws and kws in corpus:
                    map_tokens.append(kws)
    return _dedup_keep_order(base_tokens + map_tokens, limit=160)


def _score_map_hit(corpus: str, kws: List[str]) -> tuple[int, List[str]]:
    hits = [kw for kw in kws if _norm_text(kw) and _norm_text(kw) in corpus]
    return len(hits), _dedup_keep_order(hits, limit=20)


def detect_specialty_dispatch(
    *,
    topic: str | None = None,
    outline: List[str] | None = None,
    requirements: List[str] | None = None,
    tender: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    keywords = extract_engineering_keywords(
        topic=topic,
        outline=outline,
        requirements=requirements,
        tender=tender,
    )
    corpus = "\n".join(keywords)
    tender_involved = _normalize_domain_keys(((tender or {}).get("involved_domains") or [])) if isinstance(tender, dict) else []
    inferred_involved = _infer_domain_keys_from_text(corpus)
    involved_domains = tender_involved or inferred_involved or ["general"]
    dm = _load_domain_map()
    packs = _load_pack_index()

    tier_hits: Dict[int, List[Dict[str, Any]]] = {0: [], 1: [], 2: []}
    missing_files: List[str] = []
    for i, grp in enumerate(dm.get("knowledge_graph_library") or []):
        if i > 2 or not isinstance(grp, dict):
            continue
        for m in grp.get("maps") or []:
            if not isinstance(m, dict):
                continue
            filename = _norm_text(m.get("filename"))
            kws = [str(x).strip() for x in (m.get("keywords") or []) if str(x).strip()]
            score, hits = _score_map_hit(corpus, kws)
            if score <= 0:
                continue
            domain_tags = _normalize_domain_keys(m.get("domain_tags") or [])
            if not domain_tags:
                domain_tags = _infer_domain_keys_from_text(
                    "\n".join([_norm_text(m.get("cn_name")), filename] + kws)
                ) or ["general"]
            if involved_domains and not _domains_overlap(domain_tags, involved_domains):
                continue
            rec = {
                "tier": i,
                "filename": filename,
                "graph_name": _norm_text(m.get("cn_name")) or filename,
                "keywords": kws,
                "hit_keywords": hits,
                "score": score,
                "available": filename in packs,
                "domain_tags": domain_tags,
            }
            if rec["available"]:
                tier_hits[i].append(rec)
            else:
                missing_files.append(filename)

    # Additional fallback from embedded project KG files (ZF-KG-*.json), so the main
    # Web pipeline can directly use the 57-domain graph set without manual switching.
    zf_candidates: List[Dict[str, Any]] = []
    generic_candidates: List[Dict[str, Any]] = []
    dm_filenames = {
        _norm_text(x.get("filename"))
        for tier in tier_hits.values()
        for x in tier
        if isinstance(x, dict) and _norm_text(x.get("filename"))
    }
    for fn, meta in packs.items():
        if fn in dm_filenames:
            continue
        kws = [str(x).strip() for x in (meta.get("keyword_hints") or []) if str(x).strip()]
        if not kws:
            continue
        score, hits = _score_map_hit(corpus, kws)
        if score <= 0:
            continue
        rec = _record_for_meta(meta, score=score, hits=hits)
        if involved_domains and not _domains_overlap(rec.get("domain_tags") or [], involved_domains):
            continue
        if fn.startswith("ZF-KG-"):
            zf_candidates.append(rec)
        else:
            generic_candidates.append(rec)

    zf_candidates.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("hit_keywords") or [])), reverse=True)
    generic_candidates.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("hit_keywords") or [])), reverse=True)

    # Prefer ZF-KG set as specialists when they match; this is the user's desktop 57-graph library.
    if zf_candidates:
        tier_hits[1].extend(zf_candidates[:8])
        tier_hits[2].extend([x for x in zf_candidates if int(x.get("tier") or 1) == 2][:3])
    else:
        tier_hits[1].extend(generic_candidates[:6])
        tier_hits[2].extend([x for x in generic_candidates if int(x.get("tier") or 1) == 2][:3])

    for arr in tier_hits.values():
        arr2 = []
        seen = set()
        for rec in sorted(arr, key=lambda x: (int(x.get("score") or 0), len(x.get("hit_keywords") or [])), reverse=True):
            key = _norm_text(rec.get("filename"))
            if not key or key in seen:
                continue
            seen.add(key)
            arr2.append(rec)
        arr[:] = arr2

    for arr in tier_hits.values():
        arr.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("hit_keywords") or [])), reverse=True)

    master = tier_hits[0][0] if tier_hits[0] else None
    specialists = tier_hits[1][:8]
    universals = tier_hits[2][:5]
    if zf_candidates and not any(str(x.get("filename") or "").startswith("ZF-KG-") for x in specialists):
        zf_top = dict(zf_candidates[0])
        if len(specialists) >= 8:
            specialists = [zf_top] + specialists[:7]
        else:
            specialists = [zf_top] + specialists

    # Hard fallback: always attach universal base if available, even when no keyword matched.
    if not universals:
        for fn, meta in packs.items():
            domain_tags = _normalize_domain_keys(meta.get("domain_tags") or []) or ["general"]
            if involved_domains and not _domains_overlap(domain_tags, involved_domains) and "general" not in domain_tags:
                continue
            if "Universal" in fn or "SafetyCivilization" in fn or "GreenConstruction" in fn:
                universals.append(
                    {
                        "tier": 2,
                        "filename": fn,
                        "graph_name": fn,
                        "keywords": [],
                        "hit_keywords": [],
                        "score": 0,
                        "available": True,
                        "domain_tags": domain_tags,
                    }
                )
            if len(universals) >= 5:
                break

    selected: List[Dict[str, Any]] = []
    if master:
        selected.append({"role": "master", **master})
    selected.extend([{"role": "specialist", **x} for x in specialists])
    selected.extend([{"role": "universal", **x} for x in universals])

    # If nothing matched, keep deterministic fallback from available packs.
    if not selected:
        for fn, meta in list(packs.items())[:3]:
            domain_tags = _normalize_domain_keys((meta or {}).get("domain_tags") or []) or ["general"]
            selected.append(
                {
                    "role": "fallback",
                    "tier": 2,
                    "filename": fn,
                    "graph_name": fn,
                    "keywords": [],
                    "hit_keywords": [],
                    "score": 0,
                    "available": True,
                    "domain_tags": domain_tags,
                }
            )

    detected_keywords = _dedup_keep_order(
        [x for x in keywords] + [x for it in selected for x in (it.get("hit_keywords") or [])],
        limit=120,
    )
    discipline_tags = _dedup_keep_order(
        [
            str(it.get("graph_name") or "").replace("图谱", "").replace("终极", "").strip()
            for it in selected
        ],
        limit=24,
    )
    return {
        "detected_keywords": detected_keywords,
        "involved_domains": involved_domains,
        "master": master,
        "specialists": specialists,
        "universals": universals,
        "selected_graphs": selected,
        "missing_graphs": _dedup_keep_order(missing_files, limit=40),
    }


def assign_specialties_to_outline(
    outline: List[str],
    dispatch: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    chapters = [str(x).strip() for x in (outline or []) if str(x).strip()]
    specialists = list(dispatch.get("specialists") or [])
    master = dispatch.get("master")
    universals = list(dispatch.get("universals") or [])
    involved_domains = _normalize_domain_keys(dispatch.get("involved_domains") or [])

    out: Dict[str, List[Dict[str, Any]]] = {}
    for title in chapters:
        chapter_domains = _infer_domain_keys_from_text(title) or involved_domains
        ranked: List[tuple[int, Dict[str, Any]]] = []
        for sp in specialists:
            kws = [str(x).strip() for x in (sp.get("keywords") or []) if str(x).strip()]
            hit = sum(1 for kw in kws if kw and kw in title)
            domain_tags = _normalize_domain_keys(sp.get("domain_tags") or [])
            if chapter_domains and _domains_overlap(domain_tags, chapter_domains):
                hit += 4
            if hit > 0:
                ranked.append((hit, sp))
        ranked.sort(key=lambda x: x[0], reverse=True)
        picks: List[Dict[str, Any]] = [x[1] for x in ranked[:2]]
        if not picks and master:
            master_domains = _normalize_domain_keys(master.get("domain_tags") or [])
            if (not chapter_domains) or (not master_domains) or _domains_overlap(master_domains, chapter_domains):
                picks = [master]
            else:
                picks = []
        if not picks and specialists:
            picks = specialists[:1]
        if universals:
            picks.extend(universals[:1])
        out[title] = picks
    return out


def search_dispatch_graphs(
    *,
    query: str,
    graphs: List[Dict[str, Any]],
    top_k: int = 8,
    allowed_domains: List[str] | None = None,
) -> List[Dict[str, Any]]:
    tokens = _tokenize(query)
    if not tokens:
        return []
    normalized_allowed_domains = _normalize_domain_keys(allowed_domains or [])
    scored: List[tuple[float, Dict[str, Any]]] = []
    for g in graphs:
        fn = _norm_text(g.get("filename"))
        gn = _norm_text(g.get("graph_name")) or fn
        if not fn:
            continue
        graph_domains = _normalize_domain_keys(g.get("domain_tags") or [])
        if normalized_allowed_domains and graph_domains and not _domains_overlap(graph_domains, normalized_allowed_domains):
            continue
        docs = _docs_for_graph_file(fn, gn)
        if not docs:
            continue
        g_keywords = [str(x).strip() for x in (g.get("keywords") or []) if str(x).strip()]
        for d in docs:
            doc_domains = _normalize_domain_keys(d.get("domain_tags") or graph_domains)
            if normalized_allowed_domains and doc_domains and not _domains_overlap(doc_domains, normalized_allowed_domains):
                continue
            text = f"{d.get('title')}\n{d.get('text')}\n{gn}"
            score = 0.0
            for t in tokens:
                if t in text:
                    score += 1.0
            for kw in g_keywords:
                if kw and kw in query:
                    score += 0.4
            if score <= 0:
                continue
            scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for score, d in scored:
        key = f"{d.get('logical_node')}:{d.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        item = dict(d)
        item["score"] = score
        item["domain_tags"] = _normalize_domain_keys(item.get("domain_tags") or [])
        out.append(item)
        if len(out) >= max(1, int(top_k)):
            break
    return out


def search_dispatch_graphs_batch(
    requests: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Search multiple graph requests while normalizing shared graph data once.

    The result at each position is behavior-equivalent to calling
    ``search_dispatch_graphs`` for the corresponding request. Cached source
    documents are never returned directly: every hit remains a fresh dict.
    """

    normalized_cache: Dict[tuple[str, ...], List[str]] = {}

    def normalized_domains(values: Iterable[Any]) -> List[str]:
        materialized = tuple(_norm_text(value) for value in values)
        cached = normalized_cache.get(materialized)
        if cached is None:
            cached = _normalize_domain_keys(materialized)
            normalized_cache[materialized] = cached
        return cached

    def domains_overlap(left: List[str], right: List[str]) -> bool:
        if not left or not right:
            return False
        if "general" in left or "general" in right:
            return True
        return not set(left).isdisjoint(right)

    graph_cache: Dict[
        tuple[str, str, tuple[str, ...], tuple[str, ...]],
        tuple[List[str], List[str], List[tuple[Dict[str, Any], List[str]]]],
    ] = {}

    def prepared_graph(
        graph: Dict[str, Any],
    ) -> tuple[List[str], List[str], List[tuple[Dict[str, Any], List[str]]]] | None:
        filename = _norm_text(graph.get("filename"))
        graph_name = _norm_text(graph.get("graph_name")) or filename
        if not filename:
            return None
        raw_domains = tuple(str(x) for x in (graph.get("domain_tags") or []))
        keywords = tuple(
            str(x).strip()
            for x in (graph.get("keywords") or [])
            if str(x).strip()
        )
        key = (filename, graph_name, raw_domains, keywords)
        prepared = graph_cache.get(key)
        if prepared is not None:
            return prepared
        graph_domains = normalized_domains(raw_domains)
        docs: List[tuple[Dict[str, Any], List[str]]] = []
        for document in _docs_for_graph_file(filename, graph_name):
            raw_doc_domains = document.get("domain_tags") or graph_domains
            doc_domains = normalized_domains(raw_doc_domains)
            docs.append((dict(document), doc_domains))
        prepared = (graph_domains, list(keywords), docs)
        graph_cache[key] = prepared
        return prepared

    output: List[List[Dict[str, Any]]] = []
    for request in requests:
        query = str(request.get("query") or "")
        tokens = _tokenize(query)
        if not tokens:
            output.append([])
            continue
        allowed_domains = normalized_domains(request.get("allowed_domains") or [])
        scored: List[tuple[float, Dict[str, Any], List[str]]] = []
        for graph in request.get("graphs") or []:
            if not isinstance(graph, dict):
                continue
            prepared = prepared_graph(graph)
            if prepared is None:
                continue
            graph_name = _norm_text(graph.get("graph_name")) or _norm_text(
                graph.get("filename")
            )
            graph_domains, graph_keywords, documents = prepared
            if (
                allowed_domains
                and graph_domains
                and not domains_overlap(graph_domains, allowed_domains)
            ):
                continue
            for document, doc_domains in documents:
                if (
                    allowed_domains
                    and doc_domains
                    and not domains_overlap(doc_domains, allowed_domains)
                ):
                    continue
                text = (
                    f"{document.get('title')}\n"
                    f"{document.get('text')}\n"
                    f"{graph_name}"
                )
                score = 0.0
                for token in tokens:
                    if token in text:
                        score += 1.0
                for keyword in graph_keywords:
                    if keyword and keyword in query:
                        score += 0.4
                if score > 0:
                    scored.append((score, document, doc_domains))
        scored.sort(key=lambda row: row[0], reverse=True)
        hits: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for score, document, doc_domains in scored:
            key = f"{document.get('logical_node')}:{document.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            item = dict(document)
            item["score"] = score
            item["domain_tags"] = list(doc_domains)
            hits.append(item)
            if len(hits) >= max(1, int(request.get("top_k", 8))):
                break
        output.append(hits)
    return output


def extract_experience_values(
    graph_hits: List[Dict[str, Any]],
    *,
    limit: int = 4,
) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for hit in graph_hits:
        txt = _norm_text(hit.get("text"))
        if not txt:
            continue
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        for ln in lines:
            if not _NUMERIC_UNIT_RE.search(ln):
                continue
            normalized = re.sub(r"\s+", " ", ln)
            if normalized in seen:
                continue
            seen.add(normalized)
            src = f"{hit.get('graph_file')}#{hit.get('path')}"
            out.append(f"【经验值】{normalized}【图谱经验值:{src}】")
            if len(out) >= limit:
                return out
    return out
