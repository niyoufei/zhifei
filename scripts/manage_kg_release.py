#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.kg_release_manager import (
    approve_auto_generated_nodes,
    create_release_snapshot,
    get_release_environment_state,
    promote_release_snapshot,
    rollback_release_snapshot,
)


def main() -> int:
    p = argparse.ArgumentParser(description="KG release manager: snapshot, approve, rollback.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot")
    s.add_argument("--kg-root", default="/Users/youfeini/Desktop/文档生成系统/知识图谱")
    s.add_argument("--release-root", default="build/kg_releases")
    s.add_argument("--approver", default="system")
    s.add_argument("--label", default=None)

    a = sub.add_parser("approve")
    a.add_argument("--kg-root", default="/Users/youfeini/Desktop/文档生成系统/知识图谱")
    a.add_argument("--approver", default="system")
    a.add_argument("--signature", default="system-sign")
    a.add_argument("--note", default="manual approval")

    r = sub.add_parser("rollback")
    r.add_argument("--kg-root", default="/Users/youfeini/Desktop/文档生成系统/知识图谱")
    r.add_argument("--release-root", default="build/kg_releases")
    r.add_argument("--release-id", required=True)

    pr = sub.add_parser("promote")
    pr.add_argument("--release-root", default="build/kg_releases")
    pr.add_argument("--release-id", required=True)
    pr.add_argument("--environment", choices=["dev", "staging", "prod"], required=True)
    pr.add_argument("--approver", default="system")
    pr.add_argument("--canary-ratio", type=float, default=1.0)
    pr.add_argument("--note", default="")

    st = sub.add_parser("state")
    st.add_argument("--release-root", default="build/kg_releases")

    p.add_argument("--out-json", default="build/KG_Release_Manager_Result.json")
    args = p.parse_args()

    if args.cmd == "snapshot":
        result = create_release_snapshot(
            kg_root=Path(args.kg_root).expanduser().resolve(),
            release_root=Path(args.release_root).expanduser().resolve(),
            label=args.label,
            approver=args.approver,
        )
    elif args.cmd == "approve":
        result = approve_auto_generated_nodes(
            kg_root=Path(args.kg_root).expanduser().resolve(),
            approver=args.approver,
            signature=args.signature,
            note=args.note,
        )
    elif args.cmd == "promote":
        result = promote_release_snapshot(
            release_root=Path(args.release_root).expanduser().resolve(),
            release_id=args.release_id,
            environment=args.environment,
            approver=args.approver,
            canary_ratio=float(args.canary_ratio),
            note=args.note,
        )
    elif args.cmd == "state":
        result = get_release_environment_state(
            release_root=Path(args.release_root).expanduser().resolve(),
        )
    else:
        result = rollback_release_snapshot(
            kg_root=Path(args.kg_root).expanduser().resolve(),
            release_root=Path(args.release_root).expanduser().resolve(),
            release_id=args.release_id,
        )

    out = Path(args.out_json).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok={bool(result.get('ok'))}")
    print(f"out_json={out}")
    return 0 if bool(result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
