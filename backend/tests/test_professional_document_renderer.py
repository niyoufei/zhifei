from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan import docx_visual_quality as visual_quality
from backend.zhifei_autoplan import professional_document_renderer as renderer
from backend.zhifei_autoplan.execution_control import ExecutionControlRuntime
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
async def test_professional_render_creates_separate_artifact_and_receipt(
    tmp_path: Path,
) -> None:
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
    source_json.write_text(
        json.dumps(source_payload, ensure_ascii=False), encoding="utf-8"
    )
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
                        "content": "【证据：招标文件#p12】施工前完成界面复核、责任确认、过程检查和验收记录。"
                        * 12,
                        "change_summary": ["补强闭环"],
                        "evidence_preserved": True,
                    },
                    ensure_ascii=False,
                )
            },
        ]
    )

    def _fake_export(payload, output_path: str) -> str:
        Path(output_path).write_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        )
        return output_path

    def _fake_visual_qa(output_path: str | Path) -> dict[str, object]:
        visual_dir = tmp_path / "visual_qa"
        visual_dir.mkdir()
        receipt = visual_dir / "visual_quality.json"
        preview_pdf = visual_dir / "preview.pdf"
        preview_pdf.write_bytes(b"pdf")
        report: dict[str, object] = {
            "schema": "zhifei.docx_visual_quality.v1",
            "created_at": "2026-08-28T08:00:00+00:00",
            "status": "pass",
            "docx": str(output_path),
            "docx_sha256": hashlib.sha256(Path(output_path).read_bytes()).hexdigest(),
            "page_count": 12,
            "blank_pages": [],
            "sparse_pages": [],
            "orphan_heading_pages": [],
            "edge_clipping_risk_pages": [],
            "hard_failures": [],
            "warnings": [],
            "receipt": str(receipt),
            "pdf": str(preview_pdf),
            "preview_dir": str(visual_dir),
            "cjk_glyph_integrity": {"status": "pass"},
            "page_metrics": [],
        }
        report["decision_digest"] = (
            visual_quality.canonical_visual_quality_decision_digest(report)
        )
        receipt.write_text(json.dumps(report), encoding="utf-8")
        return report

    def _fake_structural_qa(
        output_path: str | Path,
        **_kwargs,
    ) -> dict[str, object]:
        receipt = tmp_path / "structural_quality.json"
        report: dict[str, object] = {
            "schema": "zhifei.docx_structural_quality.v1",
            "created_at": "2026-08-28T08:00:00+00:00",
            "status": "pass",
            "docx": str(output_path),
            "docx_sha256": hashlib.sha256(Path(output_path).read_bytes()).hexdigest(),
            "heading_count": 1,
            "table_count": 0,
            "word_fields": {"toc": True, "page": True, "numpages": True},
            "body_style": {"font": "宋体", "size_pt": 14, "line_spacing_pt": 22},
            "section_metrics": [],
            "figure_delivery": {"status": "pass"},
            "hard_failures": [],
            "warnings": [],
        }
        report["decision_digest"] = (
            renderer._canonical_structural_quality_decision_digest(report)
        )
        receipt.write_text(json.dumps(report), encoding="utf-8")
        return {**report, "receipt": str(receipt)}

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
    receipt = json.loads(
        Path(rendered["professional_render_receipt"]).read_text(encoding="utf-8")
    )
    assert receipt["model_id"] == "claude-sonnet-5"
    assert receipt["provider"] == "anthropic"
    assert receipt["slot"] == "document_render"
    assert receipt["role"] == "document_render"
    assert receipt["job_id"] == "job-test"
    assert receipt["variant"] == 1
    assert (
        receipt["professional_json_sha256"]
        == hashlib.sha256(Path(rendered["professional_json"]).read_bytes()).hexdigest()
    )
    attempt_evidence = receipt["render_attempt_evidence"]
    assert attempt_evidence["schema_version"] == ("document-render-attempt-evidence-v1")
    assert attempt_evidence["execution_control_schema_version"] == (
        "execution-control-v1"
    )
    assert attempt_evidence["attempt_count"] == 2
    assert attempt_evidence["provider_attempt_count"] == 2
    assert attempt_evidence["evidence_digest"] == (
        renderer.canonical_render_attempt_evidence_digest(attempt_evidence)
    )
    assert receipt["structural_quality"]["schema"] == (
        "zhifei.docx_structural_quality.v1"
    )
    assert receipt["visual_quality"]["schema"] == ("zhifei.docx_visual_quality.v1")
    assert (
        receipt["structural_quality"]["receipt_sha256"]
        == hashlib.sha256(
            Path(receipt["structural_quality"]["receipt"]).read_bytes()
        ).hexdigest()
    )
    assert (
        receipt["visual_quality"]["receipt_sha256"]
        == hashlib.sha256(
            Path(receipt["visual_quality"]["receipt"]).read_bytes()
        ).hexdigest()
    )
    assert receipt["receipt_digest"] == (
        renderer.canonical_professional_render_receipt_digest(receipt)
    )
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
    professional = json.loads(
        Path(rendered["professional_json"]).read_text(encoding="utf-8")
    )
    assert professional["variants"][0]["style"]["line_spacing_pt"] == 22
    assert (
        professional["variants"][0]["professional_render"]["tender_format_priority"]
        is True
    )
    assert len(provider.prompts) == 2


def test_visual_quality_decision_digest_is_stable_and_tamper_evident() -> None:
    common = {
        "schema": "zhifei.docx_visual_quality.v1",
        "created_at": "2026-08-28T08:00:00Z",
        "docx": "/one/final.docx",
        "docx_sha256": "a" * 64,
        "pdf": "/one/final.pdf",
        "preview_dir": "/one/pages",
        "receipt": "/one/visual_quality.json",
        "status": "pass",
        "hard_failures": [],
        "warnings": [],
        "page_metrics": [{"page": 1, "blank": False}],
    }
    relocated = {
        **common,
        "created_at": "2026-08-28T09:00:00Z",
        "docx": "/two/final.docx",
        "pdf": "/two/final.pdf",
        "preview_dir": "/two/pages",
        "receipt": "/two/visual_quality.json",
    }
    passed_digest = visual_quality.canonical_visual_quality_decision_digest(common)

    assert passed_digest == (
        visual_quality.canonical_visual_quality_decision_digest(relocated)
    )
    blocked = {
        **common,
        "status": "blocked",
        "hard_failures": [{"code": "BLANK_PAGES", "pages": [1]}],
    }
    assert passed_digest != (
        visual_quality.canonical_visual_quality_decision_digest(blocked)
    )
    sealed = visual_quality._seal_visual_quality_report(blocked)
    assert sealed["decision_digest"] == (
        visual_quality.canonical_visual_quality_decision_digest(sealed)
    )
    tampered = {**sealed, "docx_sha256": "b" * 64}
    assert sealed["decision_digest"] != (
        visual_quality.canonical_visual_quality_decision_digest(tampered)
    )


def test_professional_receipt_and_attempt_digests_detect_field_tampering() -> None:
    attempt = {
        "schema_version": "document-render-attempt-evidence-v1",
        "execution_control_schema_version": "execution-control-v1",
        "role": "document_render",
        "slot": "document_render",
        "provider": "anthropic",
        "model": "claude-sonnet-5",
        "job_id": "job-1",
        "variant": 1,
        "model_attempts_before": 3,
        "model_attempts_after": 5,
        "attempt_count": 2,
        "provider_attempts_before": 1,
        "provider_attempts_after": 3,
        "provider_attempt_count": 2,
    }
    sealed_attempt = {
        **attempt,
        "evidence_digest": renderer.canonical_render_attempt_evidence_digest(attempt),
    }
    assert sealed_attempt["evidence_digest"] == (
        renderer.canonical_render_attempt_evidence_digest(sealed_attempt)
    )
    assert sealed_attempt["evidence_digest"] != (
        renderer.canonical_render_attempt_evidence_digest(
            {**sealed_attempt, "variant": 2}
        )
    )

    receipt = {
        "schema": "zhifei.professional_document_render.v1",
        "created_at": "2026-08-28T08:00:00Z",
        "job_id": "job-1",
        "variant": 1,
        "provider": "anthropic",
        "model_id": "claude-sonnet-5",
        "professional_json_sha256": "c" * 64,
        "render_attempt_evidence": sealed_attempt,
    }
    sealed_receipt = {
        **receipt,
        "receipt_digest": renderer.canonical_professional_render_receipt_digest(
            receipt
        ),
    }
    assert sealed_receipt["receipt_digest"] == (
        renderer.canonical_professional_render_receipt_digest(sealed_receipt)
    )
    assert sealed_receipt["receipt_digest"] != (
        renderer.canonical_professional_render_receipt_digest(
            {**sealed_receipt, "professional_json_sha256": "d" * 64}
        )
    )


def test_quality_receipt_binding_rejects_persisted_summary_tampering(
    tmp_path: Path,
) -> None:
    receipt_path = tmp_path / "visual_quality.json"
    quality = visual_quality._seal_visual_quality_report(
        {
            "schema": "zhifei.docx_visual_quality.v1",
            "created_at": "2026-08-28T08:00:00Z",
            "status": "pass",
            "docx": str(tmp_path / "final.docx"),
            "docx_sha256": "a" * 64,
            "pdf": str(tmp_path / "final.pdf"),
            "preview_dir": str(tmp_path / "pages"),
            "receipt": str(receipt_path),
            "hard_failures": [],
            "warnings": [],
            "page_metrics": [],
        }
    )
    receipt_path.write_text(json.dumps(quality), encoding="utf-8")
    binding = renderer._quality_receipt_binding(
        quality,
        expected_schema="zhifei.docx_visual_quality.v1",
        expected_docx_sha256="a" * 64,
        label="视觉质量",
    )
    assert (
        binding["receipt_sha256"]
        == hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    )

    persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
    persisted["docx_sha256"] = "b" * 64
    receipt_path.write_text(json.dumps(persisted), encoding="utf-8")
    with pytest.raises(ProfessionalRenderError, match="身份或状态不完整"):
        renderer._quality_receipt_binding(
            quality,
            expected_schema="zhifei.docx_visual_quality.v1",
            expected_docx_sha256="a" * 64,
            label="视觉质量",
        )


@pytest.mark.asyncio
async def test_refine_chunk_blocks_evidence_loss() -> None:
    provider = _FakeProvider(
        [
            {
                "text": json.dumps(
                    {
                        "title": "质量管理",
                        "content": "质量管理措施与记录要求，责任到人并形成检查、复核、验收和归档闭环。"
                        * 50,
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


@pytest.mark.asyncio
async def test_refine_chunk_blocks_evidence_locator_substitution() -> None:
    replacement = (
        "【证据：其他项目文件#p99】质量管理措施、检查、复核、验收和归档闭环。" * 30
    )
    provider = _FakeProvider(
        [
            {
                "text": json.dumps(
                    {
                        "title": "质量管理",
                        "content": replacement,
                        "change_summary": [],
                        "evidence_preserved": True,
                    },
                    ensure_ascii=False,
                )
            }
        ]
    )

    with pytest.raises(ProfessionalRenderError, match="证据定位发生替换或增补"):
        await _refine_chunk(
            provider,
            topic="测试项目",
            title="质量管理",
            content="【证据：本项目招标文件#p15】质量管理措施、检查、复核、验收和归档闭环。"
            * 30,
            chunk_index=1,
            chunk_total=1,
            editorial_priorities=[],
        )


@pytest.mark.asyncio
async def test_refine_chunk_blocks_requirement_marker_change() -> None:
    provider = _FakeProvider(
        [
            {
                "text": json.dumps(
                    {
                        "title": "质量管理",
                        "content": "质量管理措施、检查、复核、验收和归档闭环。" * 40,
                        "change_summary": [],
                        "evidence_preserved": True,
                    },
                    ensure_ascii=False,
                )
            }
        ]
    )

    with pytest.raises(ProfessionalRenderError, match="要求绑定标记发生变化"):
        await _refine_chunk(
            provider,
            topic="测试项目",
            title="质量管理",
            content=(
                "【要求:REQ-GLOBAL-001】质量管理措施、检查、复核、验收和归档闭环。" * 30
            ),
            chunk_index=1,
            chunk_total=1,
            editorial_priorities=[],
        )


@pytest.mark.asyncio
async def test_controlled_complete_retries_transient_provider_error(
    monkeypatch,
) -> None:
    class TemporaryProviderError(RuntimeError):
        status_code = 503

    class Provider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, prompt, **kwargs):
            self.calls += 1
            if self.calls < 2:
                raise TemporaryProviderError("service unavailable")
            return {"text": "ok"}

    delays: list[int] = []

    async def no_delay(attempt, **kwargs):
        delays.append(attempt)

    monkeypatch.setenv("ZHIFEI_PROFESSIONAL_RENDER_RETRY_ATTEMPTS", "2")
    monkeypatch.setattr(renderer, "bounded_retry_delay", no_delay)
    provider = Provider()

    out = await renderer._controlled_complete(
        provider,
        "test",
        execution_runtime=None,
        provider_name="anthropic",
        model_name="claude-sonnet-5",
    )

    assert out["text"] == "ok"
    assert provider.calls == 2
    assert delays == [1]


@pytest.mark.asyncio
async def test_controlled_complete_does_not_retry_auth_error(monkeypatch) -> None:
    class AuthError(RuntimeError):
        status_code = 401

    class Provider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, prompt, **kwargs):
            self.calls += 1
            raise AuthError("bad key")

    delays: list[int] = []

    async def no_delay(attempt, **kwargs):
        delays.append(attempt)

    monkeypatch.setenv("ZHIFEI_PROFESSIONAL_RENDER_RETRY_ATTEMPTS", "3")
    monkeypatch.setattr(renderer, "bounded_retry_delay", no_delay)
    provider = Provider()

    with pytest.raises(AuthError):
        await renderer._controlled_complete(
            provider,
            "test",
            execution_runtime=None,
            provider_name="anthropic",
            model_name="claude-sonnet-5",
        )

    assert provider.calls == 1
    assert delays == []


@pytest.mark.asyncio
async def test_controlled_complete_counts_stable_shared_and_anthropic_default_budget() -> (
    None
):
    class Provider:
        async def complete(self, prompt, **kwargs):
            return {"text": "ok"}

    runtime = ExecutionControlRuntime(
        max_input_chars=100_000,
        max_requested_output_tokens=100_000,
    )
    prompt = "当前章节要求"
    stable = "固定系统规则与项目事实库"
    shared = "已生成章节摘要"

    result = await renderer._controlled_complete(
        Provider(),
        prompt,
        execution_runtime=runtime,
        provider_name="anthropic",
        model_name="claude-sonnet-test",
        stable_system_prompt=stable,
        shared_context_prompt=shared,
    )

    assert result["text"] == "ok"
    usage = runtime.snapshot()["usage"]
    assert usage["input_chars"] == len(prompt) + len(stable) + len(shared)
    assert usage["requested_output_tokens"] == 8192
