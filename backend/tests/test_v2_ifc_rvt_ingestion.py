from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.v2.data_graph_ingestion import ingest_knowledge_graph, search_graph_index


def test_ifc_and_rvt_are_ingested(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)

    ifc = root / "model.ifc"
    ifc.write_text(
        """
ISO-10303-21;
DATA;
#1= IFCPROJECT('id',#2,'DemoProject',$,$,$,$,$,$);
#10= IFCWALL('w1',#2,'Wall-A',$,$,$,$,$,$);
#11= IFCWALL('w2',#2,'Wall-B',$,$,$,$,$,$);
#20= IFCPROPERTYSINGLEVALUE('FireRating',$,IFCLABEL('A2'),$);
ENDSEC;
END-ISO-10303-21;
""",
        encoding="utf-8",
    )

    rvt = root / "demo.rvt"
    rvt.write_bytes(b"Autodesk Revit 2025 demo binary payload")
    (root / "demo.export.json").write_text('{"schedules":[{"name":"QTO"}]}', encoding="utf-8")

    db = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db, force_reindex=True)
    assert report["ok"] is True
    assert int(report.get("nodes_indexed") or 0) >= 3

    ifc_res = search_graph_index(query="IFC模型摘要", db_path=db, top_k=10, resolve_authority=False)
    assert ifc_res["total"] >= 1
    assert any(str(item.get("data_source_type") or "") == "IFC" for item in (ifc_res.get("results") or []))

    rvt_res = search_graph_index(query="Revit模型摘要", db_path=db, top_k=10, resolve_authority=False)
    assert rvt_res["total"] >= 1
    assert any(str(item.get("data_source_type") or "") == "RVT" for item in (rvt_res.get("results") or []))

