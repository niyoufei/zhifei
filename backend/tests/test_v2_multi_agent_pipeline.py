from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline


@pytest.mark.asyncio
async def test_multi_agent_pipeline_run(tmp_path: Path) -> None:
    kg_root = tmp_path / "知识图谱"
    kg_root.mkdir(parents=True, exist_ok=True)
    (kg_root / "kg.json").write_text(
        json.dumps(
            {
                "name": "sample-kg",
                "domain": "房建",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "N-1",
                                "name": "质量控制",
                                "qt_tag": ["quality", "safety"],
                                "content": {
                                    "operation_desc_premium": {
                                        "desc": "每班次检查 2 次，质量员复核。"
                                    }
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        项目名称：管廊工程
        项目编号：GL-2026-001
        质量、安全、进度、环保、重难点和扣分项均需响应。
        """,
        encoding="utf-8",
    )

    boq_payload = {
        "items": [
            {"boq_code": "A1", "name": "土方开挖", "quantity": 1200, "unit": "m3"},
            {"boq_code": "A2", "name": "主体结构钢筋", "quantity": 800, "unit": "t"},
            {"boq_code": "A3", "name": "机电管道安装", "quantity": 600, "unit": "m"},
        ]
    }

    output_path = tmp_path / "out.json"
    report_path = tmp_path / "Missing_Knowledge_Report.md"
    pipeline = MultiAgentDocPipeline(kg_db_path=tmp_path / "kg.sqlite3")
    result = await pipeline.run(
        tender_paths=[str(tender)],
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=output_path,
        missing_report_path=report_path,
    )

    assert result["ok"] is True
    assert output_path.exists()
    assert report_path.exists()
    assert len(result["sections"]) == len(result["index_matrix"]["index_matrix"])
    assert result["agents"]["graph_agent"]["report"]["ok"] is True
    assert result["agents"]["audit_agent"]["result"]["ok"] is True


@pytest.mark.asyncio
async def test_multi_agent_pipeline_outputs_missing_knowledge_report_on_graph_gap(tmp_path: Path) -> None:
    kg_root = tmp_path / "知识图谱"
    kg_root.mkdir(parents=True, exist_ok=True)
    (kg_root / "kg.json").write_text(
        json.dumps(
            {
                "name": "sample-kg",
                "domain": "房建",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "N-1",
                                "name": "无关节点",
                                "qt_tag": ["abc"],
                                "content": {"desc": "仅用于触发图谱缺失报告。"},
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        """
        项目名称：管廊工程
        项目编号：GL-2026-001
        质量、安全、进度、环保、重难点和扣分项均需响应。
        """,
        encoding="utf-8",
    )

    boq_payload = {
        "items": [
            {"boq_code": "A1", "name": "土方开挖", "quantity": 1200, "unit": "m3"},
            {"boq_code": "A2", "name": "主体结构钢筋", "quantity": 800, "unit": "t"},
            {"boq_code": "A3", "name": "机电管道安装", "quantity": 600, "unit": "m"},
        ]
    }

    output_path = tmp_path / "out.json"
    report_path = tmp_path / "Missing_Knowledge_Report.md"
    pipeline = MultiAgentDocPipeline(kg_db_path=tmp_path / "kg.sqlite3")
    result = await pipeline.run(
        tender_paths=[str(tender)],
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=output_path,
        missing_report_path=report_path,
    )

    assert result["ok"] is True
    assert result["intercepted"] is True
    assert len(result["knowledge_gaps"]) >= 1
    report = report_path.read_text(encoding="utf-8")
    assert "Missing Knowledge Report" in report
    assert "Gap List" in report


@pytest.mark.asyncio
async def test_multi_agent_pipeline_can_trigger_self_healing(tmp_path: Path) -> None:
    kg_root = tmp_path / "知识图谱"
    kg_root.mkdir(parents=True, exist_ok=True)
    (kg_root / "kg.json").write_text(
        json.dumps(
            {
                "name": "sample-kg",
                "domain": "房建",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "N-0",
                                "name": "无参数节点",
                                "qt_tag": ["质量"],
                                "content": {"desc": "仅用于触发自愈流程"},
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        "质量、安全、进度、环保、重难点、扣分点均需响应。",
        encoding="utf-8",
    )
    boq_payload = {"items": [{"boq_code": "A1", "name": "土方开挖", "quantity": 1000, "unit": "m3"}]}
    output_path = tmp_path / "out.json"
    report_path = tmp_path / "Missing_Knowledge_Report.md"

    pipeline = MultiAgentDocPipeline(
        kg_db_path=tmp_path / "kg.sqlite3",
        self_healing_provider="unknown",
        self_healing_model="none",
    )
    result = await pipeline.run(
        tender_paths=[str(tender)],
        boq_payload=boq_payload,
        graph_root=kg_root,
        output_path=output_path,
        missing_report_path=report_path,
        enable_self_healing=True,
    )

    assert result["ok"] is True
    assert result["self_healing"]["triggered"] is True
    assert result["self_healing"]["patch_nodes"] >= 1
    assert Path(result["self_healing"]["patch_file"]).exists()
