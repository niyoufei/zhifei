from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.v2.data_graph_ingestion import (
    DEFAULT_DB_PATH,
    DEFAULT_KG_ROOT,
    ingest_knowledge_graph,
    search_graph_index,
)
from backend.zhifei_autoplan.v2.index_matrix_engine import build_index_matrix
from backend.zhifei_autoplan.v2.multi_agent_pipeline import MultiAgentDocPipeline
from backend.zhifei_autoplan.v2.quantitative_boq_engine import QuantitativeBoQEngine

router = APIRouter(prefix="/autoplan/v2", tags=["Zhifei AutoPlan v2"])


class KGIngestRequest(BaseModel):
    root_path: str = str(DEFAULT_KG_ROOT)
    force_reindex: bool = False
    db_path: str = str(DEFAULT_DB_PATH)


class PipelineRunRequest(BaseModel):
    tender_paths: List[str] = Field(default_factory=list)
    boq_payload: Dict[str, Any] = Field(default_factory=dict)
    graph_root: str = str(DEFAULT_KG_ROOT)
    kg_db_path: str = str(DEFAULT_DB_PATH)
    output_path: str = "build/v2_multi_agent_output.json"
    missing_report_path: str = "build/Missing_Knowledge_Report.md"


async def _save_upload(uf: UploadFile) -> str:
    data = await uf.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"empty file: {uf.filename}")
    suffix = f"_{uf.filename or 'upload.bin'}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        return f.name


@router.post("/kg/ingest")
def ingest_graph_api(req: KGIngestRequest = Body(default=KGIngestRequest())):
    try:
        report = ingest_knowledge_graph(
            root_dir=req.root_path,
            db_path=req.db_path,
            force_reindex=req.force_reindex,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/kg/search")
def search_graph_api(
    q: str = "",
    tags: str = "",
    keywords: str = "",
    top_k: int = 12,
    db_path: str = str(DEFAULT_DB_PATH),
):
    tag_list = [part.strip() for part in tags.split(",") if part.strip()]
    keyword_list = [part.strip() for part in keywords.split(",") if part.strip()]
    return search_graph_index(
        query=q,
        tags=tag_list,
        keywords=keyword_list,
        top_k=top_k,
        db_path=db_path,
    )


@router.post("/index-matrix/parse")
async def parse_index_matrix_api(files: List[UploadFile] = File(...), save_path: str | None = None):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")
    paths = [await _save_upload(uf) for uf in files]
    out = save_path or "backend/data/autoplan/v2/index_matrix.json"
    return await build_index_matrix(paths, save_path=out)


@router.post("/boq/quantify")
async def quantify_boq_api(file: UploadFile = File(...)):
    path = await _save_upload(file)
    parser = BoQParser()
    items, stats = await parser.parse(path)
    payload = {"items": [item.model_dump() for item in items], "stats": stats}
    quant_engine = QuantitativeBoQEngine()
    quant_index = quant_engine.build_quantitative_index(payload)
    return {"ok": True, "boq": payload, "quant_index": quant_index}


@router.post("/pipeline/run")
async def run_pipeline_api(req: PipelineRunRequest):
    if not req.tender_paths:
        raise HTTPException(status_code=400, detail="tender_paths is required")
    if not isinstance(req.boq_payload, dict) or not req.boq_payload.get("items"):
        raise HTTPException(status_code=400, detail="boq_payload.items is required")

    pipeline = MultiAgentDocPipeline(kg_db_path=req.kg_db_path)
    try:
        return await pipeline.run(
            tender_paths=req.tender_paths,
            boq_payload=req.boq_payload,
            graph_root=req.graph_root,
            output_path=req.output_path,
            missing_report_path=req.missing_report_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
