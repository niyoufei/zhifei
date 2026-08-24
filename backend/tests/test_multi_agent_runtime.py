from __future__ import annotations

import hashlib
import json

from backend.zhifei_autoplan import multi_agent_runtime as mar
from backend.zhifei_autoplan.project_fact_ledger import build_project_fact_ledger
from backend.zhifei_autoplan.requirement_evidence_matrix import SCHEMA as REQUIREMENT_MATRIX_SCHEMA


def test_build_multi_agent_plan_and_summary(monkeypatch):
    monkeypatch.setattr(
        mar,
        "detect_specialty_dispatch",
        lambda **kwargs: {
            "detected_keywords": ["桥梁", "机电"],
            "selected_graphs": [{"filename": "bridge_master.json"}],
            "missing_graphs": [],
            "master": {"filename": "bridge_master.json", "graph_name": "桥梁主控图谱"},
            "specialists": [{"filename": "electrical.json", "graph_name": "机电专项图谱"}],
            "universals": [],
        },
    )
    monkeypatch.setattr(
        mar,
        "assign_specialties_to_outline",
        lambda outline, dispatch: {
            "桥梁下部结构": [
                {"filename": "bridge_master.json", "graph_name": "桥梁主控图谱"},
                {"filename": "electrical.json", "graph_name": "机电专项图谱"},
            ]
        },
    )
    plan = mar.build_multi_agent_plan(
        topic="桥梁工程",
        outline=["桥梁下部结构"],
        requirements=["按图谱生成"],
        tender={},
    )
    s = plan.summary()
    assert s["master_agent"] == "主控Agent"
    assert s["compliance_agent"] == "合规Agent"
    assert "桥梁" in s["detected_keywords"]
    assert s["chapter_agent_count"] == 1
    assert s["agent_role_count"] >= 18
    assert any(x.get("name") == "项目事实仲裁Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "要求证据矩阵Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "规范证据Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "跨专业接口Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "证据溯源Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "招标评分响应Agent" for x in s["agent_role_catalog"])
    assert any(x.get("name") == "文档视觉质检Agent" for x in s["agent_role_catalog"])
    assert all(x.get("input_boundary") for x in s["agent_role_catalog"])
    assert all(x.get("output_schema") for x in s["agent_role_catalog"])
    assert all(x.get("quality_gate") for x in s["agent_role_catalog"])
    assert all(x.get("execution_stage") for x in s["agent_role_catalog"])
    assert s["role_execution_policy"]["chapter_provider_concurrency_is_separate"] is True
    chapter_roles = plan.chapter_agents("桥梁下部结构")
    auxiliary_names = [x.get("name") for x in chapter_roles["auxiliary"]]
    assert "图纸接口Agent" in auxiliary_names
    assert "跨专业接口Agent" in auxiliary_names
    assert "要求证据矩阵Agent" in auxiliary_names
    assert "风险闭环Agent" in auxiliary_names


def test_chapter_graph_context_with_experience_values(monkeypatch):
    monkeypatch.setattr(
        mar,
        "detect_specialty_dispatch",
        lambda **kwargs: {
            "detected_keywords": ["桥梁"],
            "involved_domains": ["bridge"],
            "selected_graphs": [{"filename": "bridge_master.json", "graph_name": "桥梁主控图谱"}],
            "missing_graphs": [],
            "master": {"filename": "bridge_master.json", "graph_name": "桥梁主控图谱"},
            "specialists": [],
            "universals": [],
        },
    )
    captured = {"allowed_domains": None}

    def _search_mock(**kwargs):
        captured["allowed_domains"] = kwargs.get("allowed_domains")
        return [
            {
                "logical_node": "bridge_master.json#$.节点1",
                "graph_file": "bridge_master.json",
                "path": "$.节点1",
                "text": "孔深20m；厚度50mm；检查2次/日",
                "domain_tags": ["bridge"],
            }
        ]

    monkeypatch.setattr(
        mar,
        "assign_specialties_to_outline",
        lambda outline, dispatch: {
            "桥梁下部结构": [
                {
                    "filename": "bridge_master.json",
                    "graph_name": "桥梁主控图谱",
                    "keywords": ["桥梁"],
                    "domain_tags": ["bridge"],
                }
            ]
        },
    )
    monkeypatch.setattr(mar, "search_dispatch_graphs", _search_mock)
    monkeypatch.setattr(
        mar,
        "extract_experience_values",
        lambda hits, limit=4: ["【经验值】厚度50mm【图谱经验值:bridge_master.json#$.节点1】"],
    )
    plan = mar.build_multi_agent_plan(topic="桥梁", outline=["桥梁下部结构"], requirements=[], tender={})
    ctx = plan.chapter_graph_context(
        title="桥梁下部结构",
        query="桥梁下部结构 厚度",
        section_requirements=["需给出控制点"],
        top_k=4,
    )
    assert ctx["need_experience"] is True
    assert ctx["experience_values"]
    assert ctx["node_bindings"] == ["bridge_master.json#$.节点1"]
    assert captured["allowed_domains"] == ["bridge"]


def test_chapter_graph_context_skip_experience_when_numeric(monkeypatch):
    monkeypatch.setattr(
        mar,
        "detect_specialty_dispatch",
        lambda **kwargs: {
            "detected_keywords": ["机电"],
            "selected_graphs": [{"filename": "electrical.json", "graph_name": "机电专项图谱"}],
            "missing_graphs": [],
            "master": {"filename": "electrical.json", "graph_name": "机电专项图谱"},
            "specialists": [],
            "universals": [],
        },
    )
    monkeypatch.setattr(
        mar,
        "assign_specialties_to_outline",
        lambda outline, dispatch: {
            "机电安装": [{"filename": "electrical.json", "graph_name": "机电专项图谱", "keywords": ["机电"]}]
        },
    )
    monkeypatch.setattr(
        mar,
        "search_dispatch_graphs",
        lambda **kwargs: [{"logical_node": "electrical.json#$.节点1", "graph_file": "electrical.json", "path": "$.节点1", "text": "电缆间距1m"}],
    )
    called = {"count": 0}

    def _exp(*args, **kwargs):
        called["count"] += 1
        return ["x"]

    monkeypatch.setattr(mar, "extract_experience_values", _exp)
    plan = mar.build_multi_agent_plan(topic="机电", outline=["机电安装"], requirements=[], tender={})
    ctx = plan.chapter_graph_context(
        title="机电安装",
        query="机电安装",
        section_requirements=["电缆间距1m"],
        top_k=4,
    )
    assert ctx["need_experience"] is False
    assert ctx["experience_values"] == []
    assert called["count"] == 0


def test_agent_execution_ledger_separates_roles_from_provider_calls():
    ledger = mar.build_agent_execution_ledger(
        plan_summary={"chapter_agent_count": 2},
        content_review={
            "dimensions": {
                "tender_alignment": {
                    "label": "招标与评分响应",
                    "score": 90,
                    "pass": True,
                    "responsible_agent": "招标评分响应Agent",
                }
            },
            "quality_gate": {"pass": True},
        },
        contract_checks={"ok": True},
        standard_audit={"ok": True},
    )
    assert ledger["role_count"] == len(mar.AGENT_ROLE_DIRECTIVES)
    rows = {row["agent"]: row for row in ledger["records"]}
    assert rows["招标评分响应Agent"]["execution_mode"] == "chapter_contract"
    assert rows["专业渲染Agent"]["execution_mode"] == "render_pipeline"
    assert rows["文档视觉质检Agent"]["execution_mode"] == "render_visual_gate"
    assert rows["项目事实仲裁Agent"]["status"] == "not_executed"
    assert rows["要求证据矩阵Agent"]["status"] == "not_executed"
    assert rows["跨专业接口Agent"]["status"] == "not_executed"
    assert ledger["not_executed_count"] == 3


def test_agent_execution_ledger_binds_fact_requirement_standard_and_interface_gates():
    facts = build_project_fact_ledger(
        [
            {
                "source_id": "tender-header",
                "source_type": "tender",
                "facts": {"project_name": "测试工程", "project_code": "TEST-001"},
                "evidence": {"locator": "tender#p1_abcdef@1"},
            }
        ]
    )
    requirement_core = {
        "schema": REQUIREMENT_MATRIX_SCHEMA,
        "phase": "verified",
        "rows": [
            {
                "requirement_id": "TS-001",
                "mandatory": True,
                "status": "COVERED_TRACEABLE",
                "blocking": False,
            }
        ],
        "summary": {
            "requirement_count": 1,
            "blocking_count": 0,
            "blocking_requirement_ids": [],
            "strict_delivery_allowed": True,
        },
    }
    requirement_digest = hashlib.sha256(
        json.dumps(
            requirement_core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    requirement_matrix = {**requirement_core, "matrix_digest": requirement_digest}
    cross_index = {
        "ok": True,
        "focus_count": 2,
        "mentioned_count": 2,
        "closed_ok_count": 2,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
    }

    ledger = mar.build_agent_execution_ledger(
        plan_summary={"chapter_agent_count": 2},
        content_review={"dimensions": {}, "quality_gate": {"pass": True}},
        contract_checks={"ok": True},
        standard_audit={"ok": True, "verified_standard_count": 3},
        fact_ledger=facts,
        requirement_matrix=requirement_matrix,
        cross_index=cross_index,
    )

    rows = {row["agent"]: row for row in ledger["records"]}
    for agent in ("项目事实仲裁Agent", "要求证据矩阵Agent", "规范证据Agent", "跨专业接口Agent"):
        assert rows[agent]["status"] == "completed"
        assert rows[agent]["checks"]
    assert ledger["blocked_count"] == 0
    assert ledger["not_executed_count"] == 0
