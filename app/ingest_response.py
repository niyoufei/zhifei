from pydantic import BaseModel
from typing import List, Dict, Any

class Chunk(BaseModel):
    """文档块模型: 内容 + 元数据"""
    id: str
    content: str
    metadata: Dict[str, Any]

class IngestResponse(BaseModel):
    """文档解析响应模型"""
    success: bool
    message: str
    chunks: List[Chunk]
    total_chunks: int
