# -*- coding: utf-8 -*-
"""
KG Context Service
------------------
Builds a traceable "KG context" artifact before compose.

Output: build/kg_context.json
Purpose:
- Resolve domain_key (for selecting domain knowledge / packs)
- Select base packs (subset) deterministically
- Record file sha256 / sizes for audit & replay
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import re
import time

import kg_loader

__all__ = ["build_kg_context"]


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _safe_load_json(p: Path) -> Tuple[Optional[Any], Optional[str]]:
    try:
        txt = p.read_text(encoding="utf-8")
        return json.loads(txt), None
    except Exception as e:
        return None, repr(e)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _coerce_keywords(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        out: List[str] = []
        for x in v:
            if isinstance(x, str) and x.strip():
                out.append(x.strip())
        return out
    if isinstance(v, str):
        parts = re.split(r"[,，;；\s]+", v)
        return [x.strip() for x in parts if x.strip()]
    return []


def _collect_domain_map_entries(domain_map_obj: Any) -> List[Dict[str, Any]]:
    """
    Known layout example:
      { "meta": {...}, "knowledge_graph_library": [ { "maps": [ {...}, ...] }, ... ] }

    Tolerant implementation:
    - recursively collects dict items from any list under key 'maps'
    - avoids duplicates by object id + stable signature
    """
    out: List[Dict[str, Any]] = []
    seen: set[int] = set()

    def walk(obj: Any):
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)

        if isinstance(obj, dict):
            maps = obj.get("maps")
            if isinstance(maps, list):
                for it in maps:
                    if isinstance(it, dict):
                        out.append(it)
            for vv in obj.values():
                walk(vv)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    walk(domain_map_obj)

    uniq: Dict[str, Dict[str, Any]] = {}
    for m in out:
        cn = str(m.get("cn_name") or "")
        en = str(m.get("en_name") or m.get("en_key") or "")
        key = str(m.get("domain_key") or m.get("domain") or m.get("key") or "")
        sig = f"{cn}||{en}||{key}"
        uniq[sig] = m
    return list(uniq.values())


_DOMAIN_HINTS: List[Tuple[str, str]] = [
    (r"(装饰|装修|精装|石材|木饰面|墙面工程|吊顶)", "decoration"),
    (r"(房建|房屋建筑|主体|结构|混凝土|钢筋|模板|砌体)", "building"),
    (r"(市政.*道路|道路工程|路面|路床|沥青|水稳|交通导改)", "municipal_road"),
    (r"(排水|雨水|污水|给排水|管道|检查井|沟槽)", "municipal_drain"),
    (r"(机电|MEP|暖通|空调|电气|消防|弱电|桥架|管线综合|安装工程)", "mep"),
    (r"(公路|高速|路基|路面|JTG)", "highway"),
    (r"(水利|堤|闸|坝|泵站|SL\s?\d+)", "water_resources"),
    (r"(河道|清淤|疏浚|护坡|格宾|生态)", "river_improvement"),
    (r"(电力|输变电|变电|光伏|风电|能源|DL/T|NB/T)", "power_energy"),
    (r"(工业.*管道|工艺管道|压力试验|焊接|GB\s?50316)", "industrial_pipeline"),
    (r"(铁路|轨道|无砟|TB\s?\d+)", "railway"),
    (r"(室外|附属|园建|景观|广场|铺装|园林)", "exterior"),
]


def _fallback_domain_key(text: Optional[str]) -> Optional[str]:
    if not isinstance(text, str) or not text.strip():
        return None
    s = text.strip()
    for pat, key in _DOMAIN_HINTS:
        try:
            if re.search(pat, s, flags=re.IGNORECASE):
                return key
        except re.error:
            continue
    return None


def _extract_domain_key_from_map(m: Dict[str, Any]) -> Optional[str]:
    for k in ("domain_key", "domain", "en_key", "en_name", "key", "slug", "code", "id"):
        v = m.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    dom = m.get("domain")
    if isinstance(dom, dict):
        for k in ("domain_key", "en_key", "en_name", "key", "slug", "code", "id"):
            v = dom.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _score_map_entry(m: Dict[str, Any], query: str) -> int:
    if not query:
        return 0
    q = query.strip()
    if not q:
        return 0

    cn = m.get("cn_name") or m.get("name") or m.get("title") or ""
    desc = m.get("desc") or m.get("description") or ""
    kws = _coerce_keywords(m.get("keywords") or m.get("keyword"))

    score = 0
    if isinstance(cn, str) and cn.strip():
        if cn in q:
            score += 12
        if q in cn:
            score += 8

    for kw in kws:
        if kw and kw in q:
            score += 3

    for word in ("装饰", "装修", "房建", "市政", "道路", "排水", "雨水", "污水", "机电", "暖通", "电气", "水利", "河道", "电力", "光伏", "工业", "管道", "铁路", "公路", "景观", "室外"):
        if word in q:
            if isinstance(cn, str) and word in cn:
                score += 2
            if isinstance(desc, str) and word in desc:
                score += 1

    return score


def _resolve_domain(domain_map_obj: Any, project_type_cn: Optional[str], topic: Optional[str]) -> Dict[str, Any]:
    query_parts = [x.strip() for x in [project_type_cn, topic] if isinstance(x, str) and x.strip()]
    query = " | ".join(query_parts)

    res: Dict[str, Any] = {
        "domain_key": None,
        "matched_cn_name": None,
        "method": "none",
        "score": 0,
        "query": query,
        "candidate_count": 0,
        "matched_preview": None,
    }

    entries: List[Dict[str, Any]] = []
    if domain_map_obj is not None:
        try:
            entries = _collect_domain_map_entries(domain_map_obj)
        except Exception:
            entries = []

    res["candidate_count"] = len(entries)

    best: Optional[Dict[str, Any]] = None
    best_score = 0
    if query and entries:
        for m in entries:
            try:
                sc = _score_map_entry(m, query)
            except Exception:
                sc = 0
            if sc > best_score:
                best_score = sc
                best = m

    if best and best_score > 0:
        cn = best.get("cn_name")
        res["matched_cn_name"] = cn if isinstance(cn, str) else None
        res["score"] = int(best_score)

        domain_key = _extract_domain_key_from_map(best)
        if domain_key:
            res["domain_key"] = domain_key
            res["method"] = "domain_map"
        else:
            derived = _fallback_domain_key(res["matched_cn_name"] or "") or _fallback_domain_key(str(best.get("desc") or ""))
            if derived:
                res["domain_key"] = derived
                res["method"] = "domain_map+cn_fallback"
            else:
                res["method"] = "domain_map_unkeyed"

        keep_keys = ["cn_name", "en_name", "domain_key", "domain", "key", "slug", "code", "id", "keywords", "desc"]
        preview: Dict[str, Any] = {}
        if isinstance(best, dict):
            for k in keep_keys:
                if k in best:
                    preview[k] = best.get(k)
        res["matched_preview"] = preview or None
        return res

    fb = _fallback_domain_key(project_type_cn) or _fallback_domain_key(topic)
    if fb:
        res["domain_key"] = fb
        res["method"] = "fallback"
        res["score"] = 0
        return res

    return res


def _pack_name_map(base_pack_paths: List[Path]) -> Dict[str, Path]:
    m: Dict[str, Path] = {}
    for p in base_pack_paths:
        m[p.name] = p
    return m


def _select_base_packs(domain_key: Optional[str], base_pack_paths: List[Path]) -> List[Path]:
    names = _pack_name_map(base_pack_paths)

    def pick(fname: str) -> Optional[Path]:
        return names.get(fname)

    selected: List[Path] = []

    p = pick("Universal_Base_Pack.json")
    if p:
        selected.append(p)

    p = pick("Risk_Specialist_Pack.json")
    if p:
        selected.append(p)

    dk = (domain_key or "").strip().lower()
    if dk in ("municipal_road", "municipal_drain", "highway", "railway"):
        p = pick("Transport_Infra_Pack.json")
        if p:
            selected.append(p)
    elif dk in ("mep", "industrial_pipeline", "power_energy"):
        p = pick("Energy_Industrial_Pack.json")
        if p:
            selected.append(p)
    elif dk in ("special_medical", "medical"):
        p = pick("Special_Medical_Pack.json")
        if p:
            selected.append(p)
    else:
        p = pick("Civil_Basic_Pack.json")
        if p:
            selected.append(p)

    uniq: List[Path] = []
    seen: set[str] = set()
    for p in selected:
        if str(p) in seen:
            continue
        seen.add(str(p))
        uniq.append(p)
    return uniq


def build_kg_context(payload: Dict[str, Any], project_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = kg_loader.load_kg_config()
    domain_map_path = kg_loader.get_domain_map_path(cfg)
    base_pack_paths = kg_loader.get_base_pack_paths(cfg)

    try:
        payload_bytes = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    except Exception:
        payload_bytes = str(payload).encode("utf-8", errors="replace")
    input_sha256 = _sha256_bytes(payload_bytes)

    project_type_cn: Optional[str] = None
    if isinstance(project_profile, dict):
        pt = project_profile.get("project_type")
        if isinstance(pt, dict):
            project_type_cn = pt.get("value") or pt.get("cn_name") or pt.get("name")
        elif isinstance(pt, str):
            project_type_cn = pt

    topic = payload.get("topic") if isinstance(payload, dict) else None

    domain_map_obj: Optional[Any] = None
    domain_map_err: Optional[str] = None
    if isinstance(domain_map_path, Path) and domain_map_path.exists():
        domain_map_obj, domain_map_err = _safe_load_json(domain_map_path)
    else:
        domain_map_err = "domain_map_not_found"

    domain_res = _resolve_domain(domain_map_obj, project_type_cn, topic)
    domain_key = domain_res.get("domain_key")

    selected_paths = _select_base_packs(domain_key, base_pack_paths)

    selected_packs: List[Dict[str, Any]] = []
    for p in selected_paths:
        selected_packs.append(
            {
                "path": str(p),
                "name": p.name,
                "exists": p.exists(),
                "size_bytes": (p.stat().st_size if p.exists() else None),
                "sha256": (_sha256_file(p) if p.exists() else None),
            }
        )

    report: Dict[str, Any] = {
        "generated_at": _now_iso(),
        "input_sha256": input_sha256,
        "topic": topic,
        "project_type_cn": project_type_cn,
        "domain_map": {
            "path": str(domain_map_path),
            "exists": bool(isinstance(domain_map_path, Path) and domain_map_path.exists()),
            "sha256": (_sha256_file(domain_map_path) if isinstance(domain_map_path, Path) and domain_map_path.exists() else None),
            "error": domain_map_err,
        },
        "domain_resolution": domain_res,
        "base_packs": [
            {
                "path": str(p),
                "name": p.name,
                "exists": p.exists(),
                "size_bytes": (p.stat().st_size if p.exists() else None),
                "sha256": (_sha256_file(p) if p.exists() else None),
            }
            for p in base_pack_paths
        ],
        "selected_packs": selected_packs,
    }

    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)
    out_path = build_dir / "kg_context.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["saved_at"] = str(out_path)
    return report
