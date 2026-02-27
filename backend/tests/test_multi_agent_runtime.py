from __future__ import annotations

from backend.zhifei_autoplan import multi_agent_runtime as mar


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
