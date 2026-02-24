from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.index_matrix_engine import (
    DIMENSION_RULES,
    IndexMatrixEngine,
    build_index_matrix,
    save_index_matrix,
)


@pytest.mark.asyncio
async def test_parse_tender_builds_all_dimensions(tmp_path: Path) -> None:
    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        项目名称：测试工程
        项目编号：T-2026-001
        第一章 质量管理
        质量验收与抽检要求：合格率不低于98%。

        第二章 安全文明施工
        高处作业防护、临电管理、应急演练。

        第三章 进度计划
        工期 120 天，设置关键线路节点。

        第四章 环保
        控制扬尘和噪声，落实绿色施工。

        第五章 重难点
        深基坑与大体积混凝土是关键工序。

        第六章 扣分点
        出现不响应条款将扣分。
        """,
        encoding="utf-8",
    )

    engine = IndexMatrixEngine()
    matrix = await engine.parse_files([str(tender)])

    dims = [item["dimension"] for item in matrix["index_matrix"]]
    assert set(dims) == set(DIMENSION_RULES.keys())
    assert matrix["meta"]["qa_override_applied"] is False
    assert matrix["project_name"] == "测试工程"
    assert matrix["project_code"] == "T-2026-001"


@pytest.mark.asyncio
async def test_qa_file_overrides_base_matrix(tmp_path: Path) -> None:
    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        质量要求：按常规标准执行。
        工期要求：总工期 200 天。
        """,
        encoding="utf-8",
    )

    qa = tmp_path / "答疑文件.txt"
    qa.write_text(
        """
        答疑文件
        质量：抽检频次提高，每批次复检一次，验收合格率≥99%。
        工期：调整为总工期 180 天，关键线路压缩 5 天。
        """,
        encoding="utf-8",
    )

    engine = IndexMatrixEngine()
    matrix = await engine.parse_files([str(tender), str(qa)])

    assert matrix["meta"]["qa_override_applied"] is True
    quality = [it for it in matrix["index_matrix"] if it["dimension"] == "质量"][0]
    schedule = [it for it in matrix["index_matrix"] if it["dimension"] == "进度"][0]
    assert quality["source_type"] == "qa_override"
    assert schedule["source_type"] == "qa_override"
    assert quality["override"]["applied"] is True


@pytest.mark.asyncio
async def test_build_index_matrix_saves_json(tmp_path: Path) -> None:
    tender = tmp_path / "tender.txt"
    tender.write_text("质量 安全 进度 环保 重难点 扣分", encoding="utf-8")

    out = tmp_path / "matrix.json"
    result = await build_index_matrix([str(tender)], save_path=out)

    assert result["ok"] is True
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "index_matrix" in loaded


def test_save_index_matrix(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    saved = save_index_matrix({"index_matrix": []}, path=path)
    assert Path(saved).exists()
