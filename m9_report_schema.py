# backend/m9_report_schema.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# --- 审计与溯源必备元数据 ---
class AuditMeta(BaseModel):
    input_hash: str = Field(..., description="源文件/输入的哈希，确保可复现")
    model_version: str = Field(..., description="生成所用模型版本")
    ruleset_version: str = Field(..., description="规则引擎/评分器版本")
    pipeline_version: str = Field(..., description="组合流水线版本号")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    human_edits: bool = Field(False, description="是否存在人工修改")
    notes: Optional[str] = None

# --- 证据锚点（溯源核心） ---
class EvidenceItem(BaseModel):
    evidence_id: str = Field(..., description="证据唯一ID（可与段落/向量检索ID对齐）")
    source_name: str = Field(..., description="来源文档名")
    page: Optional[int] = Field(None, description="来源页码（如有）")
    locator: Optional[str] = Field(None, description="章节/条款/图号等结构定位符")
    snippet: Optional[str] = Field(None, description="用于审查的短摘录")
    url: Optional[str] = Field(None, description="电子来源（本地或远程）")

# --- 评分点覆盖 ---
class ScoreItem(BaseModel):
    rule_id: str = Field(..., description="评分点/规则的唯一ID")
    title: str
    score: float = 0.0
    max_score: float = 0.0
    passed: bool = False
    remarks: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list, description="支撑该评分点的证据ID集合")

# --- 章节级报告（可映射到目录/大纲） ---
class SectionReport(BaseModel):
    section_id: str
    title: str
    content_summary: Optional[str] = None         # 10%复核提要可挂这里或单独导出
    evidence: List[EvidenceItem] = Field(default_factory=list)
    scores: List[ScoreItem] = Field(default_factory=list)

# --- 附录：标准化输出（引用索引表、评分点覆盖清单） ---
class Appendix(BaseModel):
    reference_index: List[EvidenceItem] = Field(default_factory=list)  # 引用索引表
    scoring_coverage: List[ScoreItem] = Field(default_factory=list)    # 评分点覆盖清单

# --- 总报表捆绑 ---
class ReportBundle(BaseModel):
    doc_title: str
    doc_version: str
    audit: AuditMeta
    sections: List[SectionReport] = Field(default_factory=list)
    appendix: Appendix = Field(default_factory=Appendix)
    # 供可视化/导出扩展的开放字典
    extras: Dict[str, Any] = Field(default_factory=dict)

# --- 占位装载函数：后续会由compose/score/export落盘的JSON来填充 ---
def load_report_bundle_from_json(payload: Dict[str, Any]) -> ReportBundle:
    """
    说明：
    - M9 的前端可视化与多格式导出（Excel/PDF/HTML）应基于统一JSON。
    - 上游 /compose（组稿）、/score（评分）与 M4 导出的元数据，统一整理为 payload。
    - 这里先提供一个轻量装载器，便于后续接线。
    """
    return ReportBundle(**payload)

# --- 最小可测样例（可选：用于后续前端与导出联调） ---
def sample_bundle() -> ReportBundle:
    return ReportBundle(
        doc_title="示例项目-施工组织方案",
        doc_version="1.0.0",
        audit=AuditMeta(
            input_hash="sha256:deadbeef",
            model_version="gpt-x.y",
            ruleset_version="rules-2025.10",
            pipeline_version="pipe-1.2.3",
            human_edits=False,
            notes="M9 skeleton"
        ),
        sections=[
            SectionReport(
                section_id="1.1",
                title="项目概述",
                content_summary="概述本项目范围、关键工期与组织结构。",
                evidence=[
                    EvidenceItem(
                        evidence_id="ev-001",
                        source_name="招标文件.pdf",
                        page=3,
                        locator="第1章 第1.2节",
                        snippet="本工程总工期为…",
                    )
                ],
                scores=[
                    ScoreItem(
                        rule_id="S-001",
                        title="进度计划完整性",
                        score=8.0,
                        max_score=10.0,
                        passed=True,
                        remarks="计划节点齐全",
                        evidence_ids=["ev-001"]
                    )
                ],
            )
        ],
        appendix=Appendix(
            reference_index=[
                EvidenceItem(
                    evidence_id="ev-001",
                    source_name="招标文件.pdf",
                    page=3,
                    locator="第1章 第1.2节",
                )
            ],
            scoring_coverage=[
                ScoreItem(
                    rule_id="S-001",
                    title="进度计划完整性",
                    score=8.0,
                    max_score=10.0,
                    passed=True,
                    remarks="计划节点齐全",
                    evidence_ids=["ev-001"]
                )
            ]
        ),
        extras={
            "toc": [{"id": "1.1", "title": "项目概述"}],
            "export_hints": {
                "word_template": "templates/m4_word_template.dotx",
                "pdf_style": "templates/pdf/style.css"
            }
        }
    )

