from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.regional_policy_plugins import (
    load_regional_policy_plugins,
    resolve_regional_policy_plugin,
)


def test_regional_policy_plugin_loader_and_resolver(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "bj.json").write_text(
        json.dumps(
            {
                "plugin_name": "BeijingPolicyPlugin",
                "region_code": "BJ",
                "aliases": ["北京", "11"],
                "region_bonus": 1.5,
                "prefer_policy_codes": ["DB11"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    all_plugins = load_regional_policy_plugins(plugin_dir)
    assert "BJ" in all_plugins
    assert "北京" in all_plugins

    plugin = resolve_regional_policy_plugin("北京", plugin_dir=plugin_dir)
    assert plugin["region_code"] == "BJ"
    assert float(plugin["region_bonus"]) == 1.5
