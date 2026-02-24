from __future__ import annotations

from pathlib import Path

import ezdxf

from backend.zhifei_autoplan.v2.data_graph_ingestion import (
    EDGE_BELONGS_TO,
    get_graph_edges,
    ingest_knowledge_graph,
    search_graph_index,
)


def _build_dxf_fixture(path: Path) -> None:
    doc = ezdxf.new("R2010")
    for layer in ("STR_REBAR", "ARCH_WALL", "MEP_PIPE"):
        if layer not in doc.layers:
            doc.layers.add(layer)

    msp = doc.modelspace()
    note = msp.add_text(
        "设计总说明: 本工程钢筋保护层厚度 35mm。",
        dxfattribs={"layer": "STR_REBAR", "height": 2.5},
    )
    note.dxf.insert = (0.0, 0.0, 0.0)

    req = msp.add_mtext(
        "技术要求: 采用 HRB400 级钢筋，间距 200mm。",
        dxfattribs={"layer": "STR_REBAR"},
    )
    req.dxf.insert = (10.0, 5.0, 0.0)

    title_block = msp.add_mtext(
        "项目名称: V2 测试工程\\P出图比例: 1:100",
        dxfattribs={"layer": "ARCH_WALL"},
    )
    title_block.dxf.insert = (20.0, 5.0, 0.0)

    block = doc.blocks.new(name="PUMP_SYMBOL")
    block.add_circle((0.0, 0.0), radius=0.8)
    msp.add_blockref("PUMP_SYMBOL", (5.0, 8.0, 0.0), dxfattribs={"layer": "MEP_PIPE"})

    doc.saveas(str(path))


def test_dxf_ingestion_with_layer_semantics_and_edges(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    dxf_path = root / "sample.dxf"
    _build_dxf_fixture(dxf_path)

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True
    assert report["files_total"] == 1
    assert report["nodes_indexed"] >= 5

    search = search_graph_index(
        keywords=["技术要求"],
        db_path=db_path,
        resolve_authority=False,
        top_k=30,
    )
    assert search["ok"] is True
    assert search["total"] >= 1

    dxf_nodes = [node for node in search["results"] if node.get("data_source_type") == "DXF"]
    assert dxf_nodes
    assert any(node.get("spatial_context", {}).get("layer") == "STR_REBAR" for node in dxf_nodes)

    title_block_nodes = [node for node in search_graph_index(query="图框信息", db_path=db_path, top_k=30)["results"]]
    assert any(node.get("title") == "图框信息" and node.get("data_source_type") == "DXF" for node in title_block_nodes)

    edges = get_graph_edges(edge_type=EDGE_BELONGS_TO, db_path=db_path, limit=2000)
    assert edges["ok"] is True
    assert edges["total"] >= 2
    assert any(
        edge.get("to_title") == "系统图层 STR_REBAR" and edge.get("edge_type") == EDGE_BELONGS_TO
        for edge in edges["edges"]
    )
