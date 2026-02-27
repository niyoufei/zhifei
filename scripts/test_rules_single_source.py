#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.terminology_guard import (
    ENGINEERING_RULES_PATH,
    get_labor_ratio_by_condition,
    normalize_text_terminology_async,
)


async def main() -> int:
    rules_path = ENGINEERING_RULES_PATH
    if not rules_path.exists():
        print(f"[ERROR] 规则文件不存在: {rules_path}")
        return 2

    # 测试1：术语拦截（白名单纠偏）
    source_text = "本班组安排吊车司机1人，负责起重吊装。"
    corrected_text, receipt = await normalize_text_terminology_async(
        source_text,
        rules_path=rules_path,
        use_llm=True,
    )

    # 测试2：劳动力矩阵三层穿透（房屋建筑工程 -> 大型项目 -> 主体结构）
    labor = get_labor_ratio_by_condition(
        project_type="房屋建筑工程",
        size="大型项目",
        stage="主体结构",
        trade_name="木工",
        rules_path=rules_path,
    )
    trade_value = labor.get("trade_value") if isinstance(labor, dict) else {}
    if not isinstance(trade_value, dict):
        trade_value = {}

    out = {
        "single_source_rules_path": str(rules_path),
        "terminology_test": {
            "input_term": "吊车司机",
            "output_text": corrected_text,
            "corrected_to": (
                "建筑起重机械司机" if "建筑起重机械司机" in corrected_text else ""
            ),
            "llm_invoked": bool(receipt.get("llm_invoked")),
            "receipt": receipt,
        },
        "labor_test": {
            "condition": "房屋建筑工程 - 大型项目 - 主体结构",
            "trade": "木工",
            "trade_ratio": trade_value,
        },
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
