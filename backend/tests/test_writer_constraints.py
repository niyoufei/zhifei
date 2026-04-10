"""Runtime acceptance script for SectionWriter hard constraints.

Run:
    venv/bin/python backend/tests/test_writer_constraints.py
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from backend.zhifei_autoplan.agents.section_writer import SectionWriter


async def case_blacklist_interceptor() -> None:
    llm = AsyncMock()
    llm.complete.return_value = {
        "provider": "google",
        "model": "gemini-3-pro-preview",
        "text": (
            "众所周知，在实际工程中，现场配置2台QTZ80塔吊。"
            "主体结构采用C30混凝土，抗渗等级P6，钢筋HRB400E。"
        ),
    }
    writer = SectionWriter(llm=llm)
    result = await writer.write("主体结构施工", {})
    cleaned = result.get("content") or ""

    print("\n=== CASE 1: 黑名单净化 ===")
    print("[input] 含废话文本 -> 众所周知 / 在实际工程中")
    print(f"[output] {cleaned}")

    assert "众所周知" not in cleaned
    assert "在实际工程中" not in cleaned
    assert "C30" in cleaned
    assert "QTZ80" in cleaned


async def case_length_error_compacted() -> None:
    llm = AsyncMock()
    llm.complete.return_value = {
        "provider": "google",
        "model": "gemini-3-pro-preview",
        "text": (
            "工序：钢筋绑扎。设备：GW40弯曲机1台。"
            "指标：间距200mm，抽检每100m2一次，合格率≥98%。"
            "责任：施工员复核，质检员每班检查。记录：《钢筋检验批验收记录》。"
        )
        * 12,
    }
    writer = SectionWriter(llm=llm, max_retry=3)
    result = await writer.write("钢筋工程", {}, min_length=60, max_length=180)
    logs = result.get("constraint_log") or []

    print("\n=== CASE 2: 超长文本软收缩成功 ===")
    print(f"[llm_call_count] {llm.complete.call_count}")
    print(f"[constraint_log] {logs}")
    print(f"[final_output] {result.get('content')}")

    assert llm.complete.call_count == 1
    assert any(item.get("status") == "compacted" for item in logs)
    assert "间距200mm" in str(result.get("content") or "")
    assert "合格率≥98%" in str(result.get("content") or "")
    assert len(str(result.get("content") or "")) <= 180


async def main() -> None:
    await case_blacklist_interceptor()
    await case_length_error_compacted()
    print("\nPASS: writer hard constraints acceptance completed.")


if __name__ == "__main__":
    asyncio.run(main())
