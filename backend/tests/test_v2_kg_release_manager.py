from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.kg_release_manager import (
    approve_auto_generated_nodes,
    compare_release_snapshots,
    create_release_snapshot,
    get_release_environment_state,
    promote_release_snapshot,
    rollback_release_snapshot,
)


def test_release_snapshot_approve_and_rollback(tmp_path: Path) -> None:
    kg_root = tmp_path / "kg"
    kg_root.mkdir(parents=True, exist_ok=True)
    kg_file = kg_root / "ZF-KG-01-Test.json"
    kg_file.write_text(
        json.dumps(
            {
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {
                                "node_id": "N1",
                                "name": "测试",
                                "is_auto_generated": True,
                                "approval_workflow": {"required": True, "status": "pending_review"},
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

    release = create_release_snapshot(kg_root=kg_root, release_root=tmp_path / "releases", approver="tester")
    assert release["ok"] is True
    assert Path(release["manifest"]).exists()

    approved = approve_auto_generated_nodes(kg_root=kg_root, approver="tester", signature="sig-001")
    assert approved["ok"] is True
    out = json.loads(kg_file.read_text(encoding="utf-8"))
    node = out["knowledge_database"]["sec"]["nodes"][0]
    assert (node.get("approval_workflow") or {}).get("status") == "approved"

    # Mutate then rollback from snapshot.
    out["knowledge_database"]["sec"]["nodes"][0]["name"] = "已污染"
    kg_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    rb = rollback_release_snapshot(
        kg_root=kg_root,
        release_root=tmp_path / "releases",
        release_id=release["release_id"],
    )
    assert rb["ok"] is True
    rolled = json.loads(kg_file.read_text(encoding="utf-8"))
    assert rolled["knowledge_database"]["sec"]["nodes"][0]["name"] == "测试"

    promoted = promote_release_snapshot(
        release_root=tmp_path / "releases",
        release_id=release["release_id"],
        environment="staging",
        approver="tester",
    )
    assert promoted["ok"] is True
    assert promoted["state"]["environments"]["staging"]["release_id"] == release["release_id"]

    canary = promote_release_snapshot(
        release_root=tmp_path / "releases",
        release_id=release["release_id"],
        environment="prod",
        approver="tester",
        canary_ratio=0.2,
    )
    assert canary["ok"] is True
    assert canary["mode"] == "canary"
    assert float(canary["state"]["environments"]["prod"]["canary_ratio"]) == 0.2

    state = get_release_environment_state(release_root=tmp_path / "releases")
    assert state["ok"] is True
    assert state["state"]["environments"]["staging"]["release_id"] == release["release_id"]


def test_compare_release_snapshots_reports_changed_files_and_node_deltas(tmp_path: Path) -> None:
    kg_root = tmp_path / "kg"
    release_root = tmp_path / "releases"
    kg_root.mkdir(parents=True, exist_ok=True)
    kg_file = kg_root / "ZF-KG-01-Test.json"
    kg_file.write_text(
        json.dumps(
            {
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {
                                "node_id": "N1",
                                "name": "节点A",
                                "source_hierarchy": "国标",
                                "node_type": "FormulaNode",
                                "formula_expression": "a/max(b,1)",
                                "is_auto_generated": False,
                                "evidence_completeness": {"completeness_ratio": 1.0},
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

    rel_a = create_release_snapshot(kg_root=kg_root, release_root=release_root, label="A")
    assert rel_a["ok"] is True

    payload = json.loads(kg_file.read_text(encoding="utf-8"))
    payload["knowledge_database"]["sec"]["nodes"].append(
        {
            "node_id": "N2",
            "name": "节点B",
            "source_hierarchy": "答疑文件",
            "node_type": "LogicNode",
            "is_auto_generated": True,
            "evidence_completeness": {"completeness_ratio": 0.6},
        }
    )
    kg_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rel_b = create_release_snapshot(kg_root=kg_root, release_root=release_root, label="B")
    assert rel_b["ok"] is True

    diff = compare_release_snapshots(
        release_root=release_root,
        base_release_id=rel_a["release_id"],
        target_release_id=rel_b["release_id"],
    )
    assert diff["ok"] is True
    assert int((diff.get("files") or {}).get("changed_count") or 0) == 1
    node_delta = ((diff.get("node_stats") or {}).get("delta") or {})
    assert int(node_delta.get("nodes_total") or 0) == 1
    assert int(node_delta.get("auto_generated_nodes") or 0) == 1
