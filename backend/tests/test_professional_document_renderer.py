from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.professional_document_renderer import (
    ProfessionalRenderError,
    _merge_professional_style,
    _refine_chunk,
    render_professional_document,
)
from backend.zhifei_autoplan.provider_runtime import ProviderSlot


class _FakeProvider:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def complete(self, prompt: str, **_kwargs):
        self.prompts.append(prompt)
        return self._responses.pop(0)


def _slot() -> ProviderSlot:
    return ProviderSlot(
        slot="document_render",
        role="document_render",
        provider="anthropic",
        model="claude-sonnet-5",
        api_key="test-secret",
        key_alias="ANTHROPIC_API_KEY",
    )


def test_professional_style_preserves_tender_typography_and_margins() -> None:
    source = {
        "body_font": "仿宋_GB2312",
        "body_size_pt": 12,
        "line_spacing_rule": "fixed",
        "line_spacing_pt": 20,
        "margin_top_cm": 3.0,
        "margin_bottom_cm": 2.4,
        "palette": {"accent": "123456"},
    }
    design = {
        "palette": {
            "accent": "006C75",
            "accent_dark": "FFFFFF",
            "table_header": "F8F8F8",
        }
    }

    merged = _merge_professional_style(source, design)

    for key in (
        "body_font",
        "body_size_pt",
        "line_spacing_rule",
        "line_spacing_pt",
        "margin_top_cm",
        "margin_bottom_cm",
    ):
        assert merged[key] == source[key]
    assert merged["palette"]["accent"] == "123456"
    assert merged["palette"]["accent_dark"] == "103B52"
    assert merged["palette"]["table_header"] == "103B52"
    assert merged["body_align"] == "justify"


@pytest.mark.asyncio
async def test_professional_render_creates_separate_artifact_and_receipt(tmp_path: Path) -> None:
    source_docx = tmp_path / "original.docx"
    source_docx.write_bytes(b"original-docx-must-not-change")
    source_json = tmp_path / "result.json"
    source_payload = {
        "variants": [
            {
                "topic": "测试工程施工组织设计",
                "project_type": "房屋建筑工程",
                "style": {
                    "body_font": "宋体",
                    "body_size_pt": 14,
                    "line_spacing_rule": "fixed",
                    "line_spacing_pt": 22,
                    "margin_top_cm": 2.5,
                    "margin_right_cm": 2.0,
                    "margin_bottom_cm": 2.0,
                    "margin_left_cm": 2.0,
                },
                "sections": [
                    {
                        "title": "施工部署",
                        "content": "【证据：招标文件#p12】施工前完成界面复核。" * 12,
                    }
                ],
            }
        ]
    }
    source_json.write_text(json.dumps(source_payload, ensure_ascii=False), encoding="utf-8")
    provider = _FakeProvider(
        [
            {
                "text": json.dumps(
                    {
                        "design": {"palette": {"accent": "0F5966"}},
                        "editorial_priorities": ["强化工序和验收闭环"],
                        "quality_assertions": ["不虚构"],
                    },
                    ensure_ascii=False,
                )
            },
            {
                "text": json.dumps(
                    {
                        "title": "施工部署",
                        "content": "【证据：招标文件#p12】施工前完成界面复核、责任确认、过程检查和验收记录。" * 12,
                        "change_summary": ["补强闭环"],
                        "evidence_preserved": True,
                    },
                    ensure_ascii=False,
                )
            },
        ]
    )

    def _fake_export(payload, output_path: str) -> str:
        Path(output_path).write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        return output_path

    def _fake_visual_qa(output_path: str | Path) -> dict[str, object]:
        visual_dir = tmp_path / "visual_qa"
        visual_dir.mkdir()
        receipt = visual_dir / "visual_quality.json"
        receipt.write_text('{"status":"pass"}', encoding="utf-8")
        preview_pdf = visual_dir / "preview.pdf"
        preview_pdf.write_bytes(b"pdf")
        return {
            "status": "pass",
            "page_count": 12,
            "blank_pages": [],
            "sparse_pages": [],
            "orphan_heading_pages": [],
            "edge_clipping_risk_pages": [],
            "receipt": str(receipt),
            "pdf": str(preview_pdf),
            "preview_dir": str(visual_dir),
        }

    def _fake_structural_qa(
        output_path: str | Path,
        **_kwargs,
    ) -> dict[str, object]:
        receipt = tmp_path / "structural_quality.json"
        receipt.write_text('{"status":"pass"}', encoding="utf-8")
        return {
            "status": "pass",
            "docx_sha256": "a" * 64,
            "heading_count": 1,
            "table_count": 0,
            "word_fields": {"toc": True, "page": True, "numpages": True},
            "body_style": {"font": "宋体", "size_pt": 14, "line_spacing_pt": 22},
            "section_metrics": [],
            "figure_delivery": {"status": "pass"},
            "decision_digest": "b" * 64,
            "receipt": str(receipt),
        }

    rendered = await render_professional_document(
        job_id="job-test",
        variant=1,
        result={"json": str(source_json), "docx": [str(source_docx)]},
        slot_override=_slot(),
        provider_override=provider,
        export_fn=_fake_export,
        structural_qa_fn=_fake_structural_qa,
        visual_qa_fn=_fake_visual_qa,
    )

    assert source_docx.read_bytes() == b"original-docx-must-not-change"
    assert Path(rendered["professional_docx"]).exists()
    assert Path(rendered["professional_json"]).exists()
    receipt = json.loads(Path(rendered["professional_render_receipt"]).read_text(encoding="utf-8"))
    assert receipt["model_id"] == "claude-sonnet-5"
    assert receipt["quality_gate"] == {
        "original_preserved": True,
        "titles_preserved": True,
        "evidence_not_reduced": True,
        "tender_style_fields_preserved": True,
        "export_succeeded": True,
        "structural_quality_passed": True,
        "visual_page_quality_passed": True,
        "no_blank_pages": True,
        "no_orphan_headings": True,
    }
    assert receipt["visual_quality"]["page_count"] == 12
    professional = json.loads(Path(rendered["professional_json"]).read_text(encoding="utf-8"))
    assert professional["variants"][0]["style"]["line_spacing_pt"] == 22
    assert professional["variants"][0]["professional_render"]["tender_format_priority"] is True
    assert len(provider.prompts) == 2


@pytest.mark.asyncio
async def test_refine_chunk_blocks_evidence_loss() -> None:
    provider = _FakeProvider(
        [
            {
                "text": json.dumps(
                    {
                        "title": "质量管理",
                        "content": "质量管理措施与记录要求，责任到人并形成检查、复核、验收和归档闭环。" * 50,
                        "change_summary": [],
                        "evidence_preserved": False,
                    },
                    ensure_ascii=False,
                )
            }
        ]
    )

    with pytest.raises(ProfessionalRenderError, match="证据定位减少"):
        await _refine_chunk(
            provider,
            topic="测试项目",
            title="质量管理",
            content="【证据：招标文件#p15】质量管理措施与记录要求。" * 30,
            chunk_index=1,
            chunk_total=1,
            editorial_priorities=[],
        )
