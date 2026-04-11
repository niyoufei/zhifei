from __future__ import annotations

from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.data_graph_ingestion import KnowledgeGraphIndex, ingest_knowledge_graph
from backend.zhifei_autoplan.v2.dxf_parser import parse_dxf_payload


def _build_min_dxf(path: Path) -> None:
    ezdxf = pytest.importorskip("ezdxf")
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "ROAD_BASE"})
    msp.add_text("项目名称: 测试道路工程", dxfattribs={"height": 2.5, "insert": (0, 10), "layer": "TITLE"})
    msp.add_text("比例 1:100", dxfattribs={"height": 2.5, "insert": (0, 14), "layer": "TITLE"})
    doc.saveas(str(path))


def test_parse_dxf_payload_returns_structured_fields(tmp_path: Path) -> None:
    dxf_path = tmp_path / "sample.dxf"
    _build_min_dxf(dxf_path)

    payload = parse_dxf_payload(dxf_path)

    assert payload["ok"] is True
    assert isinstance(payload.get("layers"), list) and len(payload["layers"]) >= 1
    assert isinstance(payload.get("texts"), list) and len(payload["texts"]) >= 2
    assert isinstance(payload.get("geometry_features"), list) and len(payload["geometry_features"]) >= 1
    title_block = payload.get("title_block") if isinstance(payload.get("title_block"), dict) else {}
    assert "project_name" in title_block
    assert "drawing_scale" in title_block


def test_ingest_knowledge_graph_accepts_dxf(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    dxf_path = root / "drawing.dxf"
    _build_min_dxf(dxf_path)

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)

    assert report["ok"] is True
    assert report["files_total"] == 1
    assert report["nodes_indexed"] >= 1


def test_connection_context_closes_sqlite_handle(tmp_path: Path) -> None:
    events = []

    class _FakeConn:
        def commit(self):
            events.append("commit")

        def rollback(self):
            events.append("rollback")

        def close(self):
            events.append("close")

    index = KnowledgeGraphIndex(db_path=tmp_path / "kg.sqlite3")
    fake = _FakeConn()

    index._connect = lambda: fake  # type: ignore[method-assign]
    with index._connection() as conn:
        assert conn is fake

    assert events == ["commit", "close"]
