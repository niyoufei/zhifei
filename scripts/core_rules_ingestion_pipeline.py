#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="系统核心规则入口（单一数据源模式）"
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/Users/youfeini/Desktop/文档生成系统/03_系统核心规则与字典"),
        help="规则目录（仅校验 ZhiFei_Engineering_Rules_CN.json）",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/Users/youfeini/Desktop/文档生成系统/backend/data/autoplan"),
        help="仅用于清理历史遗留产物",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    rules_path = args.input_dir / "ZhiFei_Engineering_Rules_CN.json"
    if not rules_path.exists():
        print(json.dumps({"ok": False, "error": f"唯一规则源不存在: {rules_path}"}, ensure_ascii=False, indent=2))
        return 2

    removed = []
    for old_name in ("global_terminology.json", "labor_allocation_matrix.json"):
        old_path = args.output_dir / old_name
        if old_path.exists():
            try:
                old_path.unlink()
                removed.append(str(old_path))
            except Exception:
                pass

    report = {
        "ok": True,
        "mode": "single_source_of_truth",
        "rules_path": str(rules_path),
        "pdf_parsing_enabled": False,
        "removed_legacy_files": removed,
        "message": "术语、劳动力矩阵、法定工种白名单均以 ZhiFei_Engineering_Rules_CN.json 为唯一数据源。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

