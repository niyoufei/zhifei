#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.phase2_business_input_contract import (  # noqa: E402
    PASS_STATUS,
    build_phase2a_business_input_contract_snapshot,
    dump_phase2a_business_input_contract_json,
    format_phase2a_business_input_contract_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the no-runtime Phase 2A business input contract snapshot."
    )
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument(
        "--fixture",
        default=None,
        help="Fixture path relative to the repository root.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the compact text report.")
    args = parser.parse_args()

    snapshot = build_phase2a_business_input_contract_snapshot(
        args.root,
        fixture_path=args.fixture,
    )
    if args.json:
        print(dump_phase2a_business_input_contract_json(snapshot))
    else:
        print(format_phase2a_business_input_contract_report(snapshot))
    return 0 if snapshot["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
