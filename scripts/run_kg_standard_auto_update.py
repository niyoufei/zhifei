#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.standards_update_engine import refresh_kg_standards


def main() -> int:
    p = argparse.ArgumentParser(description="Refresh KG standards with latest catalog mapping.")
    p.add_argument("--kg-root", default="/Users/youfeini/Desktop/文档生成系统/知识图谱")
    p.add_argument("--catalog", default=None)
    p.add_argument("--out-json", default="build/KG_Standard_Update_Report.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    report = refresh_kg_standards(
        kg_root=Path(args.kg_root).expanduser().resolve(),
        catalog_path=Path(args.catalog).expanduser().resolve() if args.catalog else None,
        dry_run=bool(args.dry_run),
    )
    out = Path(args.out_json).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"files_total={int(report.get('files_total') or 0)}")
    print(f"files_changed={int(report.get('files_changed') or 0)}")
    print(f"nodes_updated={int(report.get('nodes_updated') or 0)}")
    print(f"superseded_total={int(report.get('superseded_total') or 0)}")
    print(f"out_json={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
