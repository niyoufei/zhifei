#!/usr/bin/env python3
"""
清理审计导出目录中的旧文件（可不启动服务，直接运行或配合 cron）。
用法:
  python3 scripts/clean_audit_exports.py --days 7
  python3 scripts/clean_audit_exports.py --keep 10
  python3 scripts/clean_audit_exports.py --days 7 --keep 20
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Clean old audit export files")
    parser.add_argument("--days", type=int, default=None, help="Remove files older than N days")
    parser.add_argument("--keep", type=int, default=None, help="Keep only latest N files per user dir")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be removed")
    args = parser.parse_args()

    if args.days is None and args.keep is None:
        args.days = 7

    base = Path("build/audit_exports")
    if not base.exists():
        print("No audit_exports dir")
        return

    now = time.time()
    removed = 0
    for user_dir in base.iterdir():
        if not user_dir.is_dir():
            continue
        files = sorted(user_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if args.keep is not None and args.keep >= 0:
            for p in files[args.keep:]:
                if args.dry_run:
                    print("Would remove:", p)
                else:
                    try:
                        p.unlink()
                        removed += 1
                    except Exception as e:
                        print("Error removing", p, e)
        if args.days is not None:
            threshold = now - args.days * 86400
            for p in files:
                if not p.exists():
                    continue
                if p.stat().st_mtime < threshold:
                    if args.dry_run:
                        print("Would remove:", p)
                    else:
                        try:
                            p.unlink()
                            removed += 1
                        except Exception as e:
                            print("Error removing", p, e)

    print("Removed:", removed)


if __name__ == "__main__":
    main()
