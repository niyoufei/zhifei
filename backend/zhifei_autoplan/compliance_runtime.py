from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from backend.zhifei_autoplan.compliance_policy import is_verified_standard_metadata


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_CODE_WITH_YEAR_RE = re.compile(r"^(?P<prefix>[A-Z]+)_(?P<num>[A-Z0-9]+)_(?P<year>\d{2,4})$")
_CODE_KEY_RE = re.compile(r"^(?P<prefix>[A-Z]+)_(?P<num>[A-Z0-9]+)")
_DOMAIN_SPLIT_RE = re.compile(r"[;,，；、/|]+")
_REGISTRY_FILENAME = "_official_registry.json"


def _norm_text(v: Any) -> str:
    return str(v or "").strip()


def _norm_domain(v: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(v or "").strip().lower())


def _tokenize(text: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for t in _TOKEN_RE.findall(text or ""):
        tt = t.strip()
        if len(tt) < 2 or tt in seen:
            continue
        seen.add(tt)
        out.append(tt)
    return out


def _coerce_domains(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        vals = [x.strip() for x in _DOMAIN_SPLIT_RE.split(v) if x.strip()]
    elif isinstance(v, list):
        vals = [str(x).strip() for x in v if str(x).strip()]
    else:
        vals = [str(v).strip()] if str(v).strip() else []
    out: List[str] = []
    seen = set()
    for x in vals:
        nx = _norm_domain(x)
        if not nx or nx in seen:
            continue
        seen.add(nx)
        out.append(x)
    return out


def _domains_overlap(left: Iterable[Any], right: Iterable[Any]) -> bool:
    a = {_norm_domain(x) for x in (left or []) if _norm_domain(x)}
    b = {_norm_domain(x) for x in (right or []) if _norm_domain(x)}
    if not a or not b:
        return False
    if "general" in a or "通用工程" in a:
        return True
    if "general" in b or "通用工程" in b:
        return True
    return bool(a.intersection(b))


def _parse_standard_key_year(standard_code: str) -> Tuple[str, int]:
    code = _norm_text(standard_code).upper()
    canonical = re.sub(r"[^A-Z0-9]+", "_", code).strip("_")
    m1 = _CODE_WITH_YEAR_RE.match(canonical)
    if m1:
        return f"{m1.group('prefix')}_{m1.group('num')}", int(m1.group("year"))
    # Standards such as GB/T 50326-2017 contain a slash in the prefix.  Keep
    # the full canonical prefix and strip only the terminal year.
    m_year = re.match(r"^(?P<key>.+)_(?P<year>\d{4})$", canonical)
    if m_year:
        return str(m_year.group("key")), int(m_year.group("year"))
    m2 = _CODE_KEY_RE.match(canonical)
    if m2:
        return f"{m2.group('prefix')}_{m2.group('num')}", 0
    return canonical or "STD_UNKNOWN", 0


def _compliance_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("ZF_COMPLIANCE_ROOT")
    if env_root and str(env_root).strip():
        return Path(env_root).expanduser()
    repo_root = Path(__file__).resolve().parents[2]
    candidates = (
        repo_root / "知识图谱" / "compliance",
        repo_root / "knowledge_graph" / "compliance",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Deterministic default; never depend on the process launch directory.
    return candidates[0]


def _catalog_path(root: Path) -> Path:
    return root / "_catalog.json"


def _registry_path(root: Path) -> Path:
    return root / _REGISTRY_FILENAME


def _canonical_standard_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def _source_files(root: Path) -> List[Path]:
    files = [
        p
        for p in root.glob("*_compliance.json")
        if p.is_file() and not p.name.startswith("_")
    ]
    registry = _registry_path(root)
    if registry.is_file():
        files.append(registry)
    return sorted(files, key=lambda p: p.name)


def _source_fingerprint(root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in _source_files(root):
        try:
            stat = path.stat()
            out.append(
                {
                    "name": path.name,
                    "size": int(stat.st_size),
                    "mtime_ns": int(stat.st_mtime_ns),
                }
            )
        except OSError:
            continue
    return out


@lru_cache(maxsize=16)
def _load_json_file(path: str, mtime_ns: int) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_entry_from_payload(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    standard_code = _norm_text(meta.get("standard_code")) or _norm_text(path.stem.replace("_compliance", "")).upper()
    code_key, code_year = _parse_standard_key_year(standard_code)
    domain_tags = _coerce_domains(meta.get("domain_tags") or meta.get("domain_tag"))
    if not domain_tags:
        # Fallback to sample from nodes.
        for n in (payload.get("nodes") or [])[:120]:
            if not isinstance(n, dict):
                continue
            domain_tags.extend(_coerce_domains(n.get("domain_tag")))
            if domain_tags:
                break
    if not domain_tags:
        domain_tags = ["通用工程"]
    source_name = _norm_text(meta.get("source_name")) or path.name
    official_source = _norm_text(meta.get("official_source")) or _norm_text(meta.get("official_url"))
    effective_status = _norm_text(meta.get("effective_status")) or _norm_text(meta.get("status"))
    current_version = _norm_text(meta.get("current_version")) or standard_code
    prefix_tag = _norm_text(meta.get("prefix_tag")) or _norm_text(standard_code.split("_")[0])
    search_text = " ".join(
        [
            standard_code,
            code_key,
            source_name,
            " ".join(domain_tags),
            prefix_tag,
        ]
    )
    return {
        "path": str(path),
        "filename": path.name,
        "standard_code": standard_code,
        "code_key": code_key,
        "code_year": int(code_year),
        "prefix_tag": prefix_tag,
        "source_name": source_name,
        "official_source": official_source,
        "effective_status": effective_status,
        "current_version": current_version,
        "priority": _norm_text(meta.get("priority")),
        "conflicts": meta.get("conflicts") if isinstance(meta.get("conflicts"), list) else [],
        "domain_tags": domain_tags,
        "generated_at": _norm_text(meta.get("generated_at")),
        "mandatory_count": int(stats.get("mandatory_count") or 0),
        "parameter_count": int(stats.get("parameter_count") or 0),
        "search_text": search_text,
        # Unless an ingested source explicitly declares otherwise, the catalog
        # decides recency by standard key/year below.  Starting at False would
        # make every legacy source ineligible before that comparison runs.
        "latest": bool(meta.get("latest", True)),
        "metadata_only": False,
    }


def _load_official_registry(root: Path) -> List[Dict[str, Any]]:
    path = _registry_path(root)
    if not path.is_file():
        return []
    try:
        mtime_ns = int(path.stat().st_mtime_ns)
    except OSError:
        mtime_ns = 0
    payload = _load_json_file(str(path), mtime_ns)
    rows = payload.get("standards") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        code = _norm_text(raw.get("standard_code"))
        if not code:
            continue
        code_key, code_year = _parse_standard_key_year(code)
        domains = _coerce_domains(raw.get("domain_tags") or raw.get("domain_tag")) or ["通用工程"]
        rec = {
            "path": str(path),
            "filename": path.name,
            "standard_code": code,
            "code_key": code_key,
            "code_year": int(code_year),
            "prefix_tag": _norm_text(raw.get("prefix_tag")) or code_key.split("_")[0],
            "source_name": _norm_text(raw.get("source_name") or raw.get("standard_name")),
            "official_source": _norm_text(raw.get("official_source")),
            "effective_status": _norm_text(raw.get("effective_status")),
            "current_version": _norm_text(raw.get("current_version")) or code,
            "priority": _norm_text(raw.get("priority")),
            "conflicts": raw.get("conflicts") if isinstance(raw.get("conflicts"), list) else [],
            "domain_tags": domains,
            "generated_at": _norm_text(raw.get("verified_at") or raw.get("generated_at")),
            "mandatory_count": 0,
            "parameter_count": 0,
            "search_text": " ".join(
                [
                    code,
                    code_key,
                    _norm_text(raw.get("source_name") or raw.get("standard_name")),
                    " ".join(domains),
                ]
            ),
            "latest": bool(raw.get("latest", True)),
            "metadata_only": True,
            "verification_note": _norm_text(raw.get("verification_note")),
            "superseded_clauses": _string_list(raw.get("superseded_clauses")),
        }
        out.append(rec)
    return out


def _string_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        raw_values = value
    elif value is None:
        raw_values = []
    else:
        raw_values = [value]
    out: List[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = _norm_text(raw)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def build_compliance_catalog(root: str | Path | None = None) -> Dict[str, Any]:
    """
    Build compact catalog for fast pre-filter retrieval.
    """
    rt = _compliance_root(root)
    if not rt.is_dir():
        return {
            "version": 2,
            "root": str(rt),
            "count": 0,
            "verified_count": 0,
            "source_fingerprint": [],
            "entries": [],
        }
    files = [p for p in _source_files(rt) if p.name != _REGISTRY_FILENAME]
    registry_entries = _load_official_registry(rt)
    registry_by_code = {
        _canonical_standard_code(row.get("standard_code")): row
        for row in registry_entries
        if _canonical_standard_code(row.get("standard_code"))
    }
    entries: List[Dict[str, Any]] = []
    for p in files:
        try:
            mtime_ns = int(p.stat().st_mtime_ns)
        except Exception:
            mtime_ns = 0
        payload = _load_json_file(str(p), mtime_ns)
        if not isinstance(payload, dict):
            continue
        entry = _extract_entry_from_payload(p, payload)
        registry_meta = registry_by_code.get(_canonical_standard_code(entry.get("standard_code")))
        if registry_meta:
            # An official registry record may verify the version/source of a
            # locally ingested text without pretending that registry metadata
            # contains clause bytes.
            for key in (
                "source_name",
                "official_source",
                "effective_status",
                "current_version",
                "priority",
                "conflicts",
                "domain_tags",
                "verification_note",
                "superseded_clauses",
            ):
                value = registry_meta.get(key)
                if value not in (None, "", []):
                    entry[key] = value
            registry_meta["_has_clause_source"] = True
        entries.append(entry)

    entries.extend([row for row in registry_entries if not row.get("_has_clause_source")])

    latest_by_key: Dict[str, Tuple[int, str]] = {}
    for e in entries:
        key = str(e.get("code_key") or "")
        year = int(e.get("code_year") or 0)
        ga = str(e.get("generated_at") or "")
        cur = latest_by_key.get(key)
        if cur is None:
            latest_by_key[key] = (year, ga)
            continue
        cur_year, cur_ga = cur
        if year > cur_year or (year == cur_year and ga > cur_ga):
            latest_by_key[key] = (year, ga)

    for e in entries:
        key = str(e.get("code_key") or "")
        year = int(e.get("code_year") or 0)
        ga = str(e.get("generated_at") or "")
        ly, lga = latest_by_key.get(key, (0, ""))
        declared_latest = bool(e.get("latest", True))
        e["latest"] = declared_latest and (bool(year == ly and ga == lga) if (ly or lga) else True)
        e["verified"] = is_verified_standard_metadata(e)

    out = {
        "version": 2,
        "root": str(rt),
        "count": len(entries),
        "verified_count": len([e for e in entries if bool(e.get("verified"))]),
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
        "source_fingerprint": _source_fingerprint(rt),
        "entries": entries,
    }
    _catalog_path(rt).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


@lru_cache(maxsize=8)
def _load_catalog(root_str: str, catalog_mtime_ns: int) -> Dict[str, Any]:
    p = _catalog_path(Path(root_str))
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_or_build_catalog(root: Path) -> Dict[str, Any]:
    p = _catalog_path(root)
    if not p.exists():
        return build_compliance_catalog(root)
    try:
        mtime_ns = int(p.stat().st_mtime_ns)
    except Exception:
        mtime_ns = 0
    cat = _load_catalog(str(root), mtime_ns)
    if not isinstance(cat, dict) or not isinstance(cat.get("entries"), list):
        return build_compliance_catalog(root)
    if cat.get("source_fingerprint") != _source_fingerprint(root):
        return build_compliance_catalog(root)
    return cat


def list_verified_standard_metadata(
    *,
    domain_tags: List[str] | None = None,
    root: str | Path | None = None,
) -> List[Dict[str, Any]]:
    """Return de-duplicated, externally traceable standard metadata only."""
    rt = _compliance_root(root)
    if not rt.is_dir():
        return []
    catalog = _load_or_build_catalog(rt)
    allowed_domains = [str(x).strip() for x in (domain_tags or []) if str(x).strip()]
    chosen: Dict[str, Dict[str, Any]] = {}
    for raw in catalog.get("entries") or []:
        if not isinstance(raw, dict) or not is_verified_standard_metadata(raw):
            continue
        if allowed_domains and not _domains_overlap(raw.get("domain_tags") or [], allowed_domains):
            continue
        canonical = _canonical_standard_code(raw.get("standard_code"))
        if not canonical:
            continue
        current = chosen.get(canonical)
        if current is None or (current.get("metadata_only") and not raw.get("metadata_only")):
            chosen[canonical] = dict(raw)
    return sorted(chosen.values(), key=lambda row: str(row.get("standard_code") or ""))


def get_compliance_registry_status(root: str | Path | None = None) -> Dict[str, Any]:
    rt = _compliance_root(root)
    if not rt.is_dir():
        return {
            "root": str(rt),
            "exists": False,
            "ready": False,
            "source_count": 0,
            "catalog_count": 0,
            "verified_count": 0,
            "warnings": ["compliance_root_missing"],
        }
    catalog = _load_or_build_catalog(rt)
    verified_count = len(list_verified_standard_metadata(root=rt))
    warnings: List[str] = []
    if verified_count <= 0:
        warnings.append("no_verified_standard_metadata")
    return {
        "root": str(rt),
        "exists": True,
        "ready": verified_count > 0,
        "source_count": len(_source_files(rt)),
        "catalog_count": int(catalog.get("count") or 0),
        "verified_count": verified_count,
        "warnings": warnings,
    }


def _entry_prefilter_score(entry: Dict[str, Any], tokens: List[str], *, allowed_domains: List[str]) -> float:
    text = str(entry.get("search_text") or "")
    score = 0.0
    for t in tokens:
        if t and t in text:
            score += 1.0
    if entry.get("latest"):
        score += 0.6
    if allowed_domains and _domains_overlap(entry.get("domain_tags") or [], allowed_domains):
        score += 0.8
    return score


def _node_score(text: str, tokens: List[str]) -> float:
    score = 0.0
    for t in tokens:
        if t and t in text:
            score += 1.0
    if re.search(r"\d", text):
        score += 0.2
    return score


def query_compliance(
    query: str,
    *,
    domain_tags: List[str] | None = None,
    top_k: int = 8,
    prefer_latest: bool = True,
    verified_only: bool = False,
    root: str | Path | None = None,
) -> List[Dict[str, Any]]:
    """
    Fast, domain-filtered compliance retrieval with latest-version preference.
    """
    tokens = _tokenize(query)
    if not tokens:
        return []
    rt = _compliance_root(root)
    if not rt.is_dir():
        return []
    allowed_domains = [str(x).strip() for x in (domain_tags or []) if str(x).strip()]
    catalog = _load_or_build_catalog(rt)
    entries = catalog.get("entries") if isinstance(catalog.get("entries"), list) else []
    if not entries:
        return []

    prefiltered: List[Tuple[float, Dict[str, Any]]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if verified_only and not is_verified_standard_metadata(e):
            continue
        e_domains = e.get("domain_tags") or []
        if allowed_domains and e_domains and (not _domains_overlap(e_domains, allowed_domains)):
            continue
        sc = _entry_prefilter_score(e, tokens, allowed_domains=allowed_domains)
        if sc <= 0 and not (prefer_latest and e.get("latest")):
            continue
        prefiltered.append((sc, e))
    prefiltered.sort(key=lambda x: x[0], reverse=True)
    # limit deep file reads
    candidates = [x[1] for x in prefiltered[:20]]

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for e in candidates:
        p = Path(str(e.get("path") or ""))
        if not p.is_file():
            continue
        try:
            mtime_ns = int(p.stat().st_mtime_ns)
        except Exception:
            mtime_ns = 0
        payload = _load_json_file(str(p), mtime_ns)
        if not isinstance(payload, dict):
            continue
        latest_bonus = 0.5 if (prefer_latest and e.get("latest")) else (0.0 if not prefer_latest else -0.1)
        domain_bonus = 0.4 if (allowed_domains and _domains_overlap(e.get("domain_tags") or [], allowed_domains)) else 0.0

        for n in (payload.get("nodes") or [])[:2400]:
            if not isinstance(n, dict):
                continue
            text = _norm_text(n.get("text"))
            if not text:
                continue
            sc = _node_score(text, tokens)
            if sc <= 0:
                continue
            mandatory_level = _norm_text(n.get("mandatory_level"))
            if mandatory_level == "禁止类":
                sc += 0.3
            sc += latest_bonus + domain_bonus
            scored.append(
                (
                    sc,
                    {
                        "type": "clause",
                        "standard_code": e.get("standard_code"),
                        "code_year": e.get("code_year"),
                        "latest": bool(e.get("latest")),
                        "domain_tags": e.get("domain_tags") or [],
                        "source_name": e.get("source_name"),
                        "official_source": e.get("official_source"),
                        "effective_status": e.get("effective_status"),
                        "current_version": e.get("current_version"),
                        "priority": e.get("priority"),
                        "conflicts": e.get("conflicts") or [],
                        "clause_no": _norm_text(n.get("clause_no")),
                        "mandatory_level": mandatory_level,
                        "text": text[:320],
                        "locator": f"{p.name}#{_norm_text(n.get('node_id'))}",
                        "source_file": str(p),
                    },
                )
            )

        for pm in (payload.get("parameters") or [])[:2400]:
            if not isinstance(pm, dict):
                continue
            ctx = _norm_text(pm.get("context"))
            name = _norm_text(pm.get("parameter_name"))
            value = _norm_text(pm.get("value"))
            unit = _norm_text(pm.get("unit"))
            txt = " ".join([name, value, unit, ctx])
            sc = _node_score(txt, tokens)
            if sc <= 0:
                continue
            sc += 0.2 + latest_bonus + domain_bonus
            scored.append(
                (
                    sc,
                    {
                        "type": "parameter",
                        "standard_code": e.get("standard_code"),
                        "code_year": e.get("code_year"),
                        "latest": bool(e.get("latest")),
                        "domain_tags": e.get("domain_tags") or [],
                        "source_name": e.get("source_name"),
                        "official_source": e.get("official_source"),
                        "effective_status": e.get("effective_status"),
                        "current_version": e.get("current_version"),
                        "priority": e.get("priority"),
                        "conflicts": e.get("conflicts") or [],
                        "parameter_name": name,
                        "value": value,
                        "unit": unit,
                        "text": txt[:320],
                        "locator": f"{p.name}#{_norm_text(pm.get('parameter_id'))}",
                        "source_file": str(p),
                    },
                )
            )

    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    seen = set()
    for sc, item in scored:
        loc = str(item.get("locator") or "")
        if not loc or loc in seen:
            continue
        seen.add(loc)
        rec = dict(item)
        rec["score"] = round(float(sc), 4)
        out.append(rec)
        if len(out) >= max(1, int(top_k)):
            break
    return out
