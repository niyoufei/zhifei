#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.release_snapshot import (
    latest_snapshot_dir,
    load_snapshot_manifest,
    restore_release_state,
    snapshot_release_state,
)


def cmd_snapshot(args: argparse.Namespace) -> int:
    report = snapshot_release_state(label=args.label)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    latest = latest_snapshot_dir()
    if latest is None:
        print(json.dumps({"ok": True, "latest_snapshot": None}, ensure_ascii=False, indent=2))
        return 0
    manifest = load_snapshot_manifest(latest)
    print(
        json.dumps(
            {
                "ok": True,
                "latest_snapshot": str(latest),
                "created_at": manifest.get("created_at"),
                "label": manifest.get("label"),
                "copied_count": manifest.get("copied_count"),
                "missing_count": manifest.get("missing_count"),
                "git": manifest.get("git"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    snapshot = args.snapshot
    if snapshot == "latest":
        latest = latest_snapshot_dir()
        if latest is None:
            raise SystemExit("[ERROR] no release snapshot found under build/_release_snapshots")
        snapshot = str(latest)
    report = restore_release_state(snapshot_dir=Path(snapshot), execute=bool(args.yes))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.yes:
        print("[INFO] preview only; re-run with --yes to copy snapshot files back to the workspace")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release_snapshot.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_snapshot = sub.add_parser("snapshot", help="capture a rollback snapshot for config/KG state")
    p_snapshot.add_argument("--label", default="", help="optional label suffix for the snapshot directory")
    p_snapshot.set_defaults(func=cmd_snapshot)

    p_status = sub.add_parser("status", help="show the latest snapshot summary")
    p_status.set_defaults(func=cmd_status)

    p_restore = sub.add_parser("restore", help="preview or execute a config/KG restore from a snapshot")
    p_restore.add_argument("--snapshot", default="latest", help="snapshot directory or 'latest'")
    p_restore.add_argument("--yes", action="store_true", help="execute the restore; default is preview only")
    p_restore.set_defaults(func=cmd_restore)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
