#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.phase1_demo_workflow import (  # noqa: E402
    PASS_STATUS,
    build_phase1b_demo_workflow_snapshot,
    format_phase1b_demo_workflow_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a no-runtime Phase 1B sanitized demo workflow snapshot."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the compact text report.")
    args = parser.parse_args()

    snapshot = build_phase1b_demo_workflow_snapshot(args.root)
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_phase1b_demo_workflow_report(snapshot))
    return 0 if snapshot["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
