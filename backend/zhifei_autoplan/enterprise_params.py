from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


LIB_PATH = Path("backend/data/autoplan/enterprise_params.json")


def _default_profile() -> Dict[str, Any]:
    return {
        "productivity": {"通用施工工序": {"value": 1.0, "unit": "项/天"}},
        "crew_defaults": {"通用施工工序": "专业班组6-8人"},
        "equipment_defaults": {"通用施工工序": "按清单配置"},
        "material_loss_rate": {},
        "seasonal_coeff": {"夏季": 1.0, "雨季": 0.9, "冬季": 0.85},
        "risk_defaults": {
            "frequency": "2次/日",
            "threshold": "偏差≤5mm",
            "record": "记录=《过程检查台账》",
            "deviation_action": "偏差处置时限≤4h",
            "responsibility": "责任岗位=工长+质量员",
        },
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out.get(k) or {}, v)
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def load_enterprise_library() -> Dict[str, Any]:
    if not LIB_PATH.exists():
        return {"version": "builtin", "default": _default_profile(), "project_types": {}}
    try:
        obj = json.loads(LIB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "builtin", "default": _default_profile(), "project_types": {}}
    if not isinstance(obj, dict):
        return {"version": "builtin", "default": _default_profile(), "project_types": {}}
    base = _default_profile()
    default_cfg = obj.get("default") if isinstance(obj.get("default"), dict) else {}
    merged_default = _deep_merge(base, default_cfg)
    out = {
        "version": str(obj.get("version") or "unknown"),
        "default": merged_default,
        "project_types": obj.get("project_types") if isinstance(obj.get("project_types"), dict) else {},
    }
    return out


def get_enterprise_profile(project_type: str | None = None) -> Dict[str, Any]:
    lib = load_enterprise_library()
    default_cfg = lib.get("default") if isinstance(lib.get("default"), dict) else _default_profile()
    ptype = str(project_type or "").strip()
    pt_cfg = {}
    project_types = lib.get("project_types") if isinstance(lib.get("project_types"), dict) else {}
    if ptype and isinstance(project_types.get(ptype), dict):
        pt_cfg = project_types.get(ptype) or {}
    merged = _deep_merge(default_cfg, pt_cfg)
    merged["version"] = str(lib.get("version") or "unknown")
    merged["project_type"] = ptype or None
    return merged


def pick_productivity(profile: Dict[str, Any], process_name: str) -> Dict[str, Any]:
    pname = str(process_name or "").strip() or "通用施工工序"
    prod = profile.get("productivity") if isinstance(profile.get("productivity"), dict) else {}
    if isinstance(prod.get(pname), dict):
        return prod.get(pname) or {"value": 1.0, "unit": "项/天"}

    # keyword fallback
    for k, v in prod.items():
        if not isinstance(v, dict):
            continue
        ks = str(k or "").strip()
        if ks and (ks in pname or pname in ks):
            return v
    return prod.get("通用施工工序") if isinstance(prod.get("通用施工工序"), dict) else {"value": 1.0, "unit": "项/天"}
