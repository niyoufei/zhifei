from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from typing import Any, Dict
from pydantic import ValidationError
from datetime import datetime
import tempfile, re

from backend.m9_report_schema import (
    ReportBundle,
    load_report_bundle_from_json,
    sample_bundle,
)
from backend.export_excel import export_report_to_excel

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/report/sample")
def get_report_sample() -> Dict[str, Any]:
    """返回一份最小可测示例，用于前端与导出联调。"""
    bundle = sample_bundle()
    return bundle.model_dump()

@router.post("/report")
def post_report(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """接收 /compose 与 /score 汇总后的 payload，按 M9 契约校验并返回。"""
    try:
        bundle: ReportBundle = load_report_bundle_from_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    total_score = 0.0
    max_score = 0.0
    for sec in bundle.sections:
        for s in sec.scores:
            total_score += (s.score or 0.0)
            max_score += (s.max_score or 0.0)

    result = bundle.model_dump()
    result.setdefault("extras", {})
    result["extras"]["score_summary"] = {
        "total_score": total_score,
        "max_score": max_score,
        "ratio": (total_score / max_score) if max_score > 0 else None,
    }
    return result

@router.get("/report/schema")
def get_report_schema() -> Dict[str, Any]:
    """暴露 ReportBundle 的 JSON Schema，便于前端表单校验与离线导出器对齐。"""
    return ReportBundle.model_json_schema()

def _safe_filename(name: str) -> str:
    name = re.sub(r'[^\w一-龥\-]+', '_', name).strip('_')  # 保留中文、字母数字与下划线/连字符
    return name or "report"

@router.post("/report/excel")
def post_report_excel(payload: Dict[str, Any] = Body(...)) -> FileResponse:
    """接收与 /export/report 相同的 JSON 契约，生成 Excel 报表并返回可下载文件。"""
    try:
        bundle: ReportBundle = load_report_bundle_from_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = _safe_filename(bundle.doc_title)
    filename = f"{base}-m9-report-{ts}.xlsx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name

    export_report_to_excel(bundle, tmp_path)

    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
