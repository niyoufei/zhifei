#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.p0_readiness import (  # noqa: E402
    build_p0_readiness_snapshot,
    format_p0_readiness_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only P0 readiness snapshot without starting services."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the compact text report.")
    args = parser.parse_args()

    snapshot = build_p0_readiness_snapshot(args.root)
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_p0_readiness_report(snapshot))
    return 0 if snapshot["status"] == "PASS_P0_READINESS_STATIC" else 1


if __name__ == "__main__":
    raise SystemExit(main())
