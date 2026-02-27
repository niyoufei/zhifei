from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.index_matrix_engine import (
    DIMENSION_RULES,
    DIMENSION_WEIGHTS,
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
    assert isinstance(matrix.get("involved_domains"), list)


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
    assert "score" in quality
    assert "signals" in quality


@pytest.mark.asyncio
async def test_parse_tender_supports_semantic_keyword_exhaustion_and_weight_signals(tmp_path: Path) -> None:
    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        第一章 安全文明施工
        危大工程清单必须逐项交底，脚手架搭设验收频次2次/日，安全员复核。

        第二章 环境保护
        PM10控制值不高于150ug/m3，施工噪声昼间≤70dB，环保员每日检查并记录。
        """,
        encoding="utf-8",
    )

    engine = IndexMatrixEngine()
    matrix = await engine.parse_files([str(tender)])
    by_dim = {item["dimension"]: item for item in matrix["index_matrix"]}

    safety = by_dim["安全"]
    env = by_dim["环保"]
    assert "危大工程" in safety["keywords"]
    assert safety["weight"] > DIMENSION_WEIGHTS["安全"]
    assert safety["signals"]["mandatory_hits"] >= 1
    assert any(chunk.get("section_title") for chunk in safety["support_chunks"])
    assert any(term in {"2次/日", "150ug/m3", "70dB"} for chunk in env["support_chunks"] for term in chunk.get("numeric_terms") or [])
    assert matrix["meta"]["semantic_sections_total"] >= 2
    assert matrix["meta"]["keyword_candidates_total"] >= 1


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


@pytest.mark.asyncio
async def test_parse_tender_outputs_involved_domains(tmp_path: Path) -> None:
    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        本项目为市政桥梁工程，包含桥墩、盖梁与挂篮施工。
        同步建设智能化弱电系统，并落实绿色施工与扬尘治理。
        """,
        encoding="utf-8",
    )

    engine = IndexMatrixEngine()
    matrix = await engine.parse_files([str(tender)])

    involved = set(matrix.get("involved_domains") or [])
    assert "市政桥梁工程" in involved
    assert "机电安装" in involved
    assert "绿色建造" in involved
    assert isinstance(matrix.get("meta", {}).get("involved_domains_confidence"), dict)


def test_save_index_matrix(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    saved = save_index_matrix({"index_matrix": []}, path=path)
    assert Path(saved).exists()
