from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.standards_update_engine import refresh_kg_standards


def test_refresh_kg_standards_updates_superseded_codes(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    p = root / "ZF-KG-01-Test.json"
    p.write_text(
        json.dumps(
            {
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {
                                "node_id": "N1",
                                "name": "测试节点",
                                "reference_standard_codes": ["GB 50300-2013"],
                                "standard_validity_timeline": {"records": []},
                            }
                        ]
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = refresh_kg_standards(kg_root=root)
    assert report["ok"] is True
    assert int(report["files_changed"]) == 1

    out = json.loads(p.read_text(encoding="utf-8"))
    node = out["knowledge_database"]["sec"]["nodes"][0]
    assert any("50300-2024" in str(x) for x in (node.get("reference_standard_codes") or []))
    state = node.get("standard_update_state") or {}
    assert int(state.get("checked_codes") or 0) >= 1
    assert str(state.get("status") or "") in {"updated", "up_to_date"}

