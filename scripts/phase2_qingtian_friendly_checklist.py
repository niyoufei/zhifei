#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.phase2_qingtian_friendly_checklist import (  # noqa: E402
    PASS_STATUS,
    build_phase2d_qingtian_friendly_checklist_snapshot,
    dump_phase2d_qingtian_friendly_checklist_json,
    format_phase2d_qingtian_friendly_checklist_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and validate the no-runtime Phase 2D Qingtian-friendly checklist."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument(
        "--fixture",
        default=None,
        help="Fixture path relative to the repository root.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the compact text report.")
    args = parser.parse_args()

    snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(
        args.root,
        fixture_path=args.fixture,
    )
    if args.json:
        print(dump_phase2d_qingtian_friendly_checklist_json(snapshot))
    else:
        print(format_phase2d_qingtian_friendly_checklist_report(snapshot))
    return 0 if snapshot["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
