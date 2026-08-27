from __future__ import annotations

from enum import Enum
from typing import Any

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
    document_sha256: str | None = None
    source_sha256: str | None = None
    page_text_sha256: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class TenderIndexItem(BaseModel):
    # 单一维度指标
    dimension: TenderDimension
    keywords: list[str] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    source_spans: list[SourceSpan] = Field(default_factory=list)


class TenderIndexMatrix(BaseModel):
    # 招标文件指数矩阵
    project_name: str | None = None
    project_code: str | None = None
    items: list[TenderIndexItem]
    # 以下为“投标文件编制要求”抽取结果：用于自动生成章节结构与版式参数
    outline: list[str] = Field(default_factory=list)
    outline_source: str | None = None  # toc | headings | fallback | none
    style: dict[str, Any] = Field(default_factory=dict)  # exporter 兼容的 style dict
    style_source: str | None = None  # rules | none
    chapter_pages: dict[str, Any] = Field(default_factory=dict)  # {title: {target/pages/...}}
    chapter_requirements: dict[str, Any] = Field(default_factory=dict)  # {title: [req...]}
    global_requirements: list[str] = Field(default_factory=list)  # 全局约束/版式/页数等
    extraction_meta: dict[str, Any] = Field(default_factory=dict)


class Resource(BaseModel):
    # 资源与工序关联
    name: str
    resource_type: str | None = None
    quantity: float | None = None
    unit: str | None = None


class ConstructionProcess(BaseModel):
    # 施工工序：前后置工序形成有向关系
    name: str
    predecessors: list[str] = Field(default_factory=list)
    successors: list[str] = Field(default_factory=list)
    standard: str | None = None
    risks: list[str] = Field(default_factory=list)


class BoQItem(BaseModel):
    # 工程量清单条目
    boq_code: str
    name: str
    project_feature: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    source_locator: dict[str, Any] | None = None
    process: ConstructionProcess | None = None
    resources: list[Resource] = Field(default_factory=list)
