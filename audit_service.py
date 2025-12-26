# -*- coding: utf-8 -*-
"""
Audit & Replay (traceability)
- 汇总 build/ 下的可追溯产物：project_profile / kg_context / region_upgrade / precheck_guard / compose
- 校验关键规则文件：project_profile_rules / precheck_guard_rules / region_upgrade_rules / domain_map / base_packs
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Tuple
import json
import hashlib

import kg_loader


BACKEND_DIR = Path(__file__).resolve().parent
BUILD_DIR = BACKEND_DIR / "build"


def _sha256_file(p: Optional[Path]) -> Optional[str]:
    if not p or not isinstance(p, Path) or (not p.exists()) or (not p.is_file()):
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_meta(p: Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"path": str(p), "exists": False}
    try:
        if p.exists():
            meta["exists"] = True
            st = p.stat()
            meta["size_bytes"] = st.st_size
            meta["mtime"] = datetime.fromtimestamp(st.st_mtime).isoformat()
    except Exception:
        pass
    return meta


def _safe_read_json(p: Path) -> Tuple[Optional[Any], Optional[str]]:
    if not p.exists():
        return None, "not_found"
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return None, f"read_error:{e!r}"
    try:
        return json.loads(txt), None
    except Exception as e:
        return None, f"json_error:{e!r}"


def _first_str(d: Any, keys: List[str]) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def build_audit_report() -> Dict[str, Any]:
    BUILD_DIR.mkdir(exist_ok=True)
    cfg = kg_loader.load_kg_config()

    artifacts = {
        "project_profile": BUILD_DIR / "project_profile.json",
        "kg_context": BUILD_DIR / "kg_context.json",
        "region_upgrade": BUILD_DIR / "region_upgrade.json",
        "precheck_guard": BUILD_DIR / "precheck_guard.json",
        "compose": BUILD_DIR / "compose.json",
        "retrieve": BUILD_DIR / "retrieve.json",
    }

    parsed: Dict[str, Any] = {}
    for name, path in artifacts.items():
        obj, err = _safe_read_json(path)
        parsed[name] = {"file": _file_meta(path), "json": obj, "error": err}

    def _get_json(name: str) -> Any:
        return parsed.get(name, {}).get("json")

    pp = _get_json("project_profile") or {}
    kg = _get_json("kg_context") or {}
    ru = _get_json("region_upgrade") or {}
    pg = _get_json("precheck_guard") or {}
    cj = _get_json("compose") or {}

    # retrieve (trace)
    rt = _get_json("retrieve") or {}
    retrieve_trace = {
        **parsed.get("retrieve", {}).get("file", {}),
        "query": rt.get("query") if isinstance(rt, dict) else None,
        "tokens": rt.get("tokens") if isinstance(rt, dict) else None,
        "top_k": rt.get("top_k") if isinstance(rt, dict) else None,
        "docs_scanned": rt.get("docs_scanned") if isinstance(rt, dict) else None,
        "results_count": (len(rt.get("results") or []) if isinstance(rt, dict) else None),
        "trace_file": str(BUILD_DIR / "retrieve.json"),
    }

    project_profile = {
        **parsed["project_profile"]["file"],
        "decision": pp.get("decision") if isinstance(pp, dict) else None,
        "project_type": pp.get("project_type") if isinstance(pp, dict) else None,
        "mandatory_dimensions": pp.get("mandatory_dimensions") if isinstance(pp, dict) else None,
        "input_sha256": pp.get("input_sha256") if isinstance(pp, dict) else None,
        "rule_path": pp.get("rule_path") if isinstance(pp, dict) else None,
        "rule_sha256": pp.get("rule_sha256") if isinstance(pp, dict) else None,
    }

    kg_context = {
        **parsed["kg_context"]["file"],
        "input_sha256": kg.get("input_sha256") if isinstance(kg, dict) else None,
        "domain_resolution": kg.get("domain_resolution") if isinstance(kg, dict) else None,
        "selected_packs": kg.get("selected_packs") if isinstance(kg, dict) else None,
        "domain_map_path": _first_str(kg.get("domain_map") if isinstance(kg, dict) else None, ["path", "rule_path"]),
        "domain_map_sha256": _first_str(kg.get("domain_map") if isinstance(kg, dict) else None, ["sha256", "rule_sha256"]),
    }

    region_upgrade = {
        **parsed["region_upgrade"]["file"],
        "applied": ru.get("applied") if isinstance(ru, dict) else None,
        "region_key": ru.get("region_key") if isinstance(ru, dict) else None,
        "rule_path": ru.get("rule_path") if isinstance(ru, dict) else None,
        "rule_sha256": ru.get("rule_sha256") if isinstance(ru, dict) else None,
        "project_profile_decision": ru.get("project_profile_decision") if isinstance(ru, dict) else None,
        "input_sha256": ru.get("input_sha256") if isinstance(ru, dict) else None,
    }

    precheck_guard = {
        **parsed["precheck_guard"]["file"],
        "passed": pg.get("passed") if isinstance(pg, dict) else None,
        "project_profile_decision": pg.get("project_profile_decision") if isinstance(pg, dict) else None,
        "rule_path": pg.get("rule_path") if isinstance(pg, dict) else None,
        "rule_sha256": pg.get("rule_sha256") if isinstance(pg, dict) else None,
        "input_sha256": pg.get("input_sha256") if isinstance(pg, dict) else None,
    }

    compose = {
        **parsed["compose"]["file"],
        "status": cj.get("status") if isinstance(cj, dict) else None,
        "saved_at": cj.get("saved_at") if isinstance(cj, dict) else None,
        "topic": cj.get("topic") if isinstance(cj, dict) else None,
        "sections_count": (len(cj.get("sections") or []) if isinstance(cj, dict) else None),
    }

    checks: List[Dict[str, Any]] = []

    # 1) input_sha256 consistency
    candidates: List[str] = []
    for name in ["project_profile", "kg_context", "region_upgrade", "precheck_guard"]:
        obj = _get_json(name)
        if isinstance(obj, dict) and isinstance(obj.get("input_sha256"), str) and obj.get("input_sha256").strip():
            candidates.append(obj["input_sha256"].strip())
    uniq = sorted(set(candidates))
    checks.append({
        "check": "input_sha256_consistency",
        "value": {"ok": len(uniq) <= 1, "candidates": candidates, "unique": uniq},
    })

    # 2) project_profile rule file
    try:
        pp_rule = kg_loader.get_project_profile_rule_path(cfg)
        pp_rule_sha = _sha256_file(pp_rule)
        expected = pp.get("rule_sha256") if isinstance(pp, dict) else None
        checks.append({
            "check": "project_profile_rule_file",
            "value": {
                "rule_path": str(pp_rule),
                "exists": pp_rule.exists(),
                "sha256": pp_rule_sha,
                "sha256_match": (pp_rule_sha == expected) if (pp_rule_sha and isinstance(expected, str)) else None,
            },
        })
    except Exception as e:
        checks.append({"check": "project_profile_rule_file", "value": {"error": repr(e)}})

    # 3) precheck_guard rule file
    try:
        pg_rule = kg_loader.get_precheck_guard_rule_path(cfg)
        pg_rule_sha = _sha256_file(pg_rule)
        expected = pg.get("rule_sha256") if isinstance(pg, dict) else None
        checks.append({
            "check": "precheck_guard_rule_file",
            "value": {
                "rule_path": str(pg_rule),
                "exists": pg_rule.exists(),
                "sha256": pg_rule_sha,
                "sha256_match": (pg_rule_sha == expected) if (pg_rule_sha and isinstance(expected, str)) else None,
            },
        })
    except Exception as e:
        checks.append({"check": "precheck_guard_rule_file", "value": {"error": repr(e)}})

    # 4) region_upgrade rule file
    try:
        region_key = ru.get("region_key") if isinstance(ru, dict) else None
        if not region_key:
            keys = sorted((cfg.get("region_upgrade_rules") or {}).keys())
            region_key = keys[0] if keys else None
        rp = kg_loader.get_region_upgrade_rule(region_key, cfg) if region_key else None
        rp_sha = _sha256_file(rp) if rp else None
        expected = ru.get("rule_sha256") if isinstance(ru, dict) else None
        checks.append({
            "check": "region_upgrade_rule_file",
            "value": {
                "region_key": region_key,
                "rule_path": (str(rp) if rp else None),
                "exists": (rp.exists() if rp else None),
                "sha256": rp_sha,
                "sha256_match": (rp_sha == expected) if (rp_sha and isinstance(expected, str)) else None,
            },
        })
    except Exception as e:
        checks.append({"check": "region_upgrade_rule_file", "value": {"error": repr(e)}})

    # 5) domain_map rule file
    try:
        dm = kg_loader.get_domain_map_path(cfg)
        dm_sha = _sha256_file(dm)
        expected = None
        if isinstance(kg, dict):
            dm_info = kg.get("domain_map")
            if isinstance(dm_info, dict):
                expected = dm_info.get("sha256") or dm_info.get("rule_sha256")
        checks.append({
            "check": "domain_map_rule_file",
            "value": {
                "rule_path": str(dm),
                "exists": dm.exists(),
                "sha256": dm_sha,
                "sha256_match": (dm_sha == expected) if (dm_sha and isinstance(expected, str)) else None,
            },
        })
    except Exception as e:
        checks.append({"check": "domain_map_rule_file", "value": {"error": repr(e)}})

    # 6) base pack files (all configured)
    try:
        bps = kg_loader.get_base_pack_paths(cfg)
        values = []
        for p in bps:
            values.append({
                "name": p.name,
                "path": str(p),
                "exists": p.exists(),
                "sha256": _sha256_file(p),
            })
        checks.append({"check": "base_pack_files", "value": values})
    except Exception as e:
        checks.append({"check": "base_pack_files", "value": {"error": repr(e)}})

    # 7) selected pack files (from kg_context)
    try:
        sel = kg.get("selected_packs") if isinstance(kg, dict) else None
        if isinstance(sel, list):
            values = []
            for x in sel:
                if not isinstance(x, dict):
                    continue
                path_s = x.get("path")
                p = Path(path_s) if isinstance(path_s, str) and path_s else None
                values.append({
                    "name": x.get("name") or (p.name if p else None),
                    "path": path_s,
                    "exists": (p.exists() if p else None),
                    "sha256": (_sha256_file(p) if p else None),
                    "reason": x.get("reason"),
                })
            checks.append({"check": "selected_pack_files", "value": values})
        else:
            checks.append({"check": "selected_pack_files", "value": None})
    except Exception as e:
        checks.append({"check": "selected_pack_files", "value": {"error": repr(e)}})

    # replayability = artifacts + rule files all present
    missing: List[str] = []
    for _, path in artifacts.items():
        if not path.exists():
            missing.append(str(path))

    # rule files required
    try:
        if not kg_loader.get_project_profile_rule_path(cfg).exists():
            missing.append(str(kg_loader.get_project_profile_rule_path(cfg)))
    except Exception as e:
        missing.append(f"project_profile_rule_error:{e!r}")

    try:
        if not kg_loader.get_precheck_guard_rule_path(cfg).exists():
            missing.append(str(kg_loader.get_precheck_guard_rule_path(cfg)))
    except Exception as e:
        missing.append(f"precheck_guard_rule_error:{e!r}")

    try:
        keys = sorted((cfg.get("region_upgrade_rules") or {}).keys())
        default_key = keys[0] if keys else None
        region_key = (ru.get("region_key") if isinstance(ru, dict) else None) or default_key
        rp = kg_loader.get_region_upgrade_rule(region_key, cfg) if region_key else None
        if rp and not rp.exists():
            missing.append(str(rp))
    except Exception as e:
        missing.append(f"region_upgrade_rule_error:{e!r}")

    try:
        dm = kg_loader.get_domain_map_path(cfg)
        if not dm.exists():
            missing.append(str(dm))
    except Exception as e:
        missing.append(f"domain_map_error:{e!r}")

    try:
        for p in kg_loader.get_base_pack_paths(cfg):
            if not p.exists():
                missing.append(str(p))
    except Exception as e:
        missing.append(f"base_pack_error:{e!r}")

    replayable = (len(missing) == 0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_profile": project_profile,
        "kg_context": kg_context,
        "retrieve": retrieve_trace,
        "region_upgrade": region_upgrade,
        "precheck_guard": precheck_guard,
        "compose": compose,
        "checks": checks,
        "replay": {"replayable": replayable, "missing": missing},
    }


__all__ = ["build_audit_report"]
