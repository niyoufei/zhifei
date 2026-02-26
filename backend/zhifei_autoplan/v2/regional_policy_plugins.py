from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_PLUGIN_DIR = Path("backend/data/autoplan/v2/regional_policy_plugins")

DEFAULT_BUILTIN_PLUGINS: List[Dict[str, Any]] = [
    {
        "region_code": "CN",
        "aliases": ["CHN", "中国", "全国"],
        "region_bonus": 1.0,
        "prefer_policy_codes": ["GB ", "GB/T ", "JGJ ", "SL ", "TB ", "JTG"],
        "source_hierarchy_min": "企标",
    }
]


def normalize_region_code(value: Any) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", str(value or "").strip().upper())
    return text


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}, ()):
        return []
    return [value]


def _iter_plugin_dicts(plugin_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if plugin_dir.exists():
        for path in sorted(plugin_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, list):
                rows.extend([item for item in payload if isinstance(item, dict)])
            elif isinstance(payload, dict):
                rows.append(payload)
    rows.extend(DEFAULT_BUILTIN_PLUGINS)
    return rows


def load_regional_policy_plugins(
    plugin_dir: Path | str = DEFAULT_PLUGIN_DIR,
) -> Dict[str, Dict[str, Any]]:
    base = Path(plugin_dir).expanduser().resolve()
    rows = _iter_plugin_dicts(base)
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        region_code = normalize_region_code(row.get("region_code"))
        if not region_code:
            continue
        aliases = [normalize_region_code(x) for x in _as_list(row.get("aliases")) if normalize_region_code(x)]
        payload = {
            "region_code": region_code,
            "aliases": aliases,
            "region_bonus": float(row.get("region_bonus") or 0.0),
            "prefer_policy_codes": [str(x).strip() for x in _as_list(row.get("prefer_policy_codes")) if str(x).strip()],
            "require_any_policy_codes": [
                str(x).strip() for x in _as_list(row.get("require_any_policy_codes")) if str(x).strip()
            ],
            "exclude_policy_codes": [str(x).strip() for x in _as_list(row.get("exclude_policy_codes")) if str(x).strip()],
            "source_hierarchy_min": str(row.get("source_hierarchy_min") or "").strip(),
            "metadata": {
                "plugin_dir": str(base),
                "plugin_name": str(row.get("plugin_name") or row.get("name") or region_code),
            },
        }
        out[region_code] = payload
        for alias in aliases:
            out[alias] = payload
    return out


def resolve_regional_policy_plugin(
    region_context: str | None,
    *,
    plugin_dir: Path | str = DEFAULT_PLUGIN_DIR,
) -> Dict[str, Any]:
    key = normalize_region_code(region_context)
    if not key:
        return {}
    plugins = load_regional_policy_plugins(plugin_dir)
    plugin = plugins.get(key)
    return dict(plugin) if isinstance(plugin, dict) else {}
