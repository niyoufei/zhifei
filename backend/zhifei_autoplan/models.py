from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TenderDimension(str, Enum):
    # MECE 原则：维度“完全穷举、互不包含”
    QUALITY = "质量目标"
    SAFETY = "安全等级"
    SCHEDULE = "进度节点"
    ENVIRONMENT = "环保要求"
    DIFFICULTY = "重难点"
    PENALTY = "扣分项"


class SourceSpan(BaseModel):
    # 原文索引位置：证据可追溯
    file_name: str
    page: int
    start: int
    end: int
    snippet: str


class TenderIndexItem(BaseModel):
    # 单一维度指标
    dimension: TenderDimension
    keywords: List[str] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    source_spans: List[SourceSpan] = Field(default_factory=list)


class TenderIndexMatrix(BaseModel):
    # 招标文件指数矩阵
    project_name: Optional[str] = None
    items: List[TenderIndexItem]
    # 以下为“投标文件编制要求”抽取结果：用于自动生成章节结构与版式参数
    outline: List[str] = Field(default_factory=list)
    outline_source: Optional[str] = None  # toc | headings | fallback | none
    style: Dict[str, Any] = Field(default_factory=dict)  # exporter 兼容的 style dict
    style_source: Optional[str] = None  # rules | none
    chapter_pages: Dict[str, Any] = Field(default_factory=dict)  # {title: {target/pages/...}}
    chapter_requirements: Dict[str, Any] = Field(default_factory=dict)  # {title: [req...]}
    global_requirements: List[str] = Field(default_factory=list)  # 全局约束/版式/页数等
    extraction_meta: Dict[str, Any] = Field(default_factory=dict)


class Resource(BaseModel):
    # 资源与工序关联
    name: str
    resource_type: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None


class ConstructionProcess(BaseModel):
    # 施工工序：前后置工序形成有向关系
    name: str
    predecessors: List[str] = Field(default_factory=list)
    successors: List[str] = Field(default_factory=list)
    standard: Optional[str] = None
    risks: List[str] = Field(default_factory=list)


class BoQItem(BaseModel):
    # 工程量清单条目
    boq_code: str
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    process: Optional[ConstructionProcess] = None
    resources: List[Resource] = Field(default_factory=list)
