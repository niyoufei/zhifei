from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from pydantic import BaseModel
from ..schemas import IngestResponse  # 后续 schema 导入

router = APIRouter(prefix="/ingest", tags=["文档解析"])

class IngestRequest(BaseModel):
    """文档解析请求模型"""
    file_type: str = Form(...)  # 文件类型: docx/pdf/txt
    chunk_size: int = Form(512)  # 分块大小 (tokens)

@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    request: IngestRequest = IngestRequest()
):
    """上传并解析文档，返回结构化块列表"""
    if not file:
        raise HTTPException(status_code=400, detail="未上传文件")

    # 临时占位: 后续实现文件读取、解析、元数据提取
    content = await file.read()
    filename = file.filename

    # 示例响应 (后续替换为实际解析结果)
    chunks = [
        {
            "id": "chunk_1",
            "content": f"示例块: {filename} 的第一段内容",
            "metadata": {"page": 1, "source": filename}
        }
    ]

    return IngestResponse(
        success=True,
        message="解析成功",
        chunks=chunks,
        total_chunks=1
    )

# 后续端点: /ingest/analyze (分析块), /ingest/index (建索引)
