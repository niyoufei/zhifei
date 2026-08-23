from __future__ import annotations

from backend.zhifei_autoplan import graph_dispatcher as gd


def _reset_caches() -> None:
    gd._load_domain_map.cache_clear()
    gd._load_pack_index.cache_clear()
    gd._docs_for_graph_file.cache_clear()


def test_detect_specialty_dispatch_with_domain_hits(monkeypatch):
    _reset_caches()
    domain_map = {
        "knowledge_graph_library": [
            {
                "category": "tier0",
                "maps": [
                    {
                        "filename": "bridge_master.json",
                        "cn_name": "桥梁主控图谱",
                        "keywords": ["桥梁", "桩基"],
                        "domain_tags": ["bridge"],
                    }
                ],
            },
            {
                "category": "tier1",
                "maps": [
                    {
                        "filename": "electrical.json",
                        "cn_name": "机电专项图谱",
                        "keywords": ["机电", "电缆"],
                        "domain_tags": ["mep"],
                    }
                ],
            },
            {
                "category": "tier2",
                "maps": [
                    {
                        "filename": "universal.json",
                        "cn_name": "通用图谱",
                        "keywords": ["施工"],
                        "domain_tags": ["general"],
                    }
                ],
            },
        ]
    }
    pack_index = {
        "bridge_master.json": {"content": {"工序名称": "桥梁施工", "指标": "厚度50mm"}, "domain_tags": ["bridge"]},
        "electrical.json": {"content": {"工序名称": "机电安装", "指标": "电缆间距1m"}, "domain_tags": ["mep"]},
        "universal.json": {"content": {"工序名称": "通用管理", "指标": "检查频次2次/日"}, "domain_tags": ["general"]},
    }
    monkeypatch.setattr(gd, "_load_domain_map", lambda: domain_map)
    monkeypatch.setattr(gd, "_load_pack_index", lambda: pack_index)

    res = gd.detect_specialty_dispatch(
        topic="桥梁及机电改造工程",
        outline=["桥梁下部结构", "机电安装"],
        requirements=["施工组织设计"],
        tender={"items": [{"dimension": "技术", "keywords": ["桥梁", "机电"]}]},
    )
    assert res["master"]["filename"] == "bridge_master.json"
    assert any(x["filename"] == "electrical.json" for x in res["specialists"])
    assert any(x["filename"] == "universal.json" for x in res["universals"])
    assert "桥梁" in res["detected_keywords"]
    assert "bridge" in (res.get("involved_domains") or [])


def test_assign_specialties_to_outline(monkeypatch):
    _reset_caches()
    dispatch = {
        "master": {"filename": "bridge_master.json", "graph_name": "桥梁主控图谱", "keywords": ["桥梁"]},
        "specialists": [
            {"filename": "electrical.json", "graph_name": "机电专项图谱", "keywords": ["机电", "电缆"]},
            {"filename": "waterproof.json", "graph_name": "防水专项图谱", "keywords": ["防水"]},
        ],
        "universals": [{"filename": "universal.json", "graph_name": "通用图谱", "keywords": []}],
    }
    mapping = gd.assign_specialties_to_outline(["桥梁下部结构", "机电安装", "质量管理"], dispatch)
    assert mapping["桥梁下部结构"][0]["filename"] == "bridge_master.json"
    assert mapping["机电安装"][0]["filename"] == "electrical.json"
    assert any(x["filename"] == "universal.json" for x in mapping["质量管理"])


def test_search_dispatch_graphs_and_extract_experience(monkeypatch):
    _reset_caches()
    monkeypatch.setattr(
        gd,
        "_load_pack_index",
        lambda: {
            "bridge_master.json": {
                "content": {
                    "工序名称": "桩基施工",
                    "控制点": "孔深20m",
                    "质量指标": "保护层厚度50mm",
                    "频次": "检查2次/日",
                }
            }
        },
    )
    gd._docs_for_graph_file.cache_clear()
    graphs = [
        {
            "filename": "bridge_master.json",
            "graph_name": "桥梁主控图谱",
            "keywords": ["桩基", "桥梁"],
        }
    ]
    hits = gd.search_dispatch_graphs(query="桥梁桩基 厚度 频次", graphs=graphs, top_k=4)
    assert hits
    exp = gd.extract_experience_values(hits, limit=3)
    assert exp
    assert any("50mm" in x or "2次/日" in x for x in exp)


def test_search_dispatch_graphs_isolated_by_allowed_domains(monkeypatch):
    _reset_caches()
    monkeypatch.setattr(
        gd,
        "_load_pack_index",
        lambda: {
            "bridge_master.json": {
                "content": {"工序名称": "桥梁施工", "质量指标": "厚度50mm"},
                "domain_tags": ["bridge"],
            },
            "hydro_master.json": {
                "content": {"工序名称": "闸门安装", "质量指标": "启闭频次2次/日"},
                "domain_tags": ["hydraulic"],
            },
        },
    )
    gd._docs_for_graph_file.cache_clear()
    graphs = [
        {"filename": "bridge_master.json", "graph_name": "桥梁主控图谱", "keywords": ["桥梁"], "domain_tags": ["bridge"]},
        {"filename": "hydro_master.json", "graph_name": "水利主控图谱", "keywords": ["闸门"], "domain_tags": ["hydraulic"]},
    ]
    hits = gd.search_dispatch_graphs(
        query="桥梁 厚度",
        graphs=graphs,
        top_k=5,
        allowed_domains=["bridge"],
    )
    assert hits
    assert all("bridge" in (h.get("domain_tags") or []) for h in hits)


def test_ai_markdown_catalog_is_loaded_dispatched_and_searchable(monkeypatch, tmp_path):
    _reset_caches()
    root = tmp_path / "知识图谱"
    catalog = root / "AI知识图谱大全" / "学校房建"
    catalog.mkdir(parents=True)
    (catalog / "学校房建规则.md").write_text(
        "# 主体结构施工\n\n学校房建主体结构施工应设置质量控制点、安全检查频次和验收闭环。\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gd, "_iter_project_kg_roots", lambda: [root])

    pack_index = gd._load_pack_index()
    ai_filenames = [name for name in pack_index if name.startswith("AIKG::学校房建/")]
    assert ai_filenames == ["AIKG::学校房建/学校房建规则.md"]
    assert pack_index[ai_filenames[0]]["project_type"] == "学校房建"

    dispatch = gd.detect_specialty_dispatch(
        topic="学校房建施工组织设计",
        outline=["主体结构施工"],
        requirements=["质量 安全 验收"],
        tender={},
    )
    selected = [dispatch.get("master")] + list(dispatch.get("specialists") or [])
    ai_graphs = [item for item in selected if isinstance(item, dict) and item.get("source") == "ai_knowledge_graph"]
    assert ai_graphs

    hits = gd.search_dispatch_graphs(
        query="学校房建施工组织设计 主体结构施工 质量 安全 验收",
        graphs=ai_graphs,
        top_k=5,
    )
    assert hits
    assert all(str(hit.get("graph_file") or "").startswith("AIKG::学校房建/") for hit in hits)
    assert all(hit.get("source") == "ai_knowledge_graph" for hit in hits)
