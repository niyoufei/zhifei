#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.phase1_static_matrix import (  # noqa: E402
    PASS_STATUS,
    build_phase1e_static_matrix_snapshot,
    dump_phase1e_static_matrix_json,
    format_phase1e_static_matrix_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the no-runtime Phase 1E static test matrix snapshot."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the compact text report.")
    args = parser.parse_args()

    snapshot = build_phase1e_static_matrix_snapshot(args.root)
    if args.json:
        print(dump_phase1e_static_matrix_json(snapshot))
    else:
        print(format_phase1e_static_matrix_report(snapshot))
    return 0 if snapshot["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
