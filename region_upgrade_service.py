# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, List
import json
import hashlib
import time

import kg_loader


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _pick_default_region_key(cfg: Dict[str, Any]) -> Optional[str]:
    m = cfg.get("region_upgrade_rules") or {}
    if not isinstance(m, dict) or not m:
        return None
    if "anhui_hefei_general" in m:
        return "anhui_hefei_general"
    return sorted(m.keys())[0]


def _extract_region_key(payload: Dict[str, Any], project_profile: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[str]:
    payload = payload or {}
    project_profile = project_profile or {}

    # payload 常见字段
    for k in ("region_key", "region_upgrade_key", "region", "region_code", "regionCode"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            kk = v.get("key")
            if isinstance(kk, str) and kk.strip():
                return kk.strip()

    # project_profile 常见字段路径（尽量宽容，不假设固定结构）
    paths = [
        ("region_key",),
        ("region", "key"),
        ("region", "region_key"),
        ("output_profile", "region_key"),
        ("output_profile", "region", "key"),
    ]
    for ps in paths:
        cur: Any = project_profile
        ok = True
        for p in ps:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()

    return _pick_default_region_key(cfg)


def resolve_region_upgrade(payload: Dict[str, Any], project_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析并记录“区域 Upgrade 规则”：
    - 根据 payload / project_profile 推断 region_key（无则取默认）
    - 通过 kg_loader.get_region_upgrade_rule 找到规则文件
    - 计算 sha256、读取 top keys，用于审计/回放
    """
    cfg = kg_loader.load_kg_config()
    region_key = _extract_region_key(payload or {}, project_profile or {}, cfg)

    out: Dict[str, Any] = {
        "applied": False,
        "region_key": region_key,
        "rule_path": None,
        "rule_sha256": None,
        "top_level_keys": [],
        "project_profile_decision": (project_profile or {}).get("decision"),
        "input_sha256": (project_profile or {}).get("input_sha256"),
        "ts": int(time.time()),
        "errors": [],
    }

    if not region_key:
        out["errors"].append("region_key not provided and no default configured in kg_config.json")
        return out

    rp = kg_loader.get_region_upgrade_rule(region_key, cfg)
    if rp is None:
        out["errors"].append(f"no region_upgrade_rule configured for region_key={region_key}")
        return out

    out["rule_path"] = str(rp)

    if not rp.exists():
        out["errors"].append(f"rule file not found: {rp}")
        return out

    out["rule_sha256"] = _sha256_file(rp)

    try:
        data = json.loads(rp.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            out["top_level_keys"] = sorted(list(data.keys()))[:50]
            # 尝试抓取元信息（如果规则文件里有）
            for k in ("name", "version", "rule_version", "upgrade_version", "id"):
                if k in data:
                    out[k] = data[k]
    except Exception as e:
        out["errors"].append(f"json parse error: {repr(e)}")
        return out

    out["applied"] = True
    return out
