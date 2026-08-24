from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_professional_delivery_promotes_rendered_word_and_preserves_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge

    source_json = tmp_path / "result.json"
    source_json.write_text('{"variants": [{}, {}]}', encoding="utf-8")
    source_docs = [tmp_path / "source-v1.docx", tmp_path / "source-v2.docx"]
    for path in source_docs:
        path.write_bytes(b"source")

    rendered_calls: list[int] = []

    async def fake_render(*, job_id, variant, result):
        rendered_calls.append(variant)
        professional_docx = tmp_path / f"professional-v{variant}.docx"
        professional_json = tmp_path / f"professional-v{variant}.json"
        receipt = tmp_path / f"professional-v{variant}.receipt.json"
        professional_docx.write_bytes(b"professional")
        professional_json.write_text("{}", encoding="utf-8")
        output_sha256 = hashlib.sha256(professional_docx.read_bytes()).hexdigest()
        structural = professional_docx.with_suffix(".structural_quality.json")
        structural.write_text(
            json.dumps({"status": "pass", "docx_sha256": output_sha256}),
            encoding="utf-8",
        )
        visual = professional_docx.with_suffix(".visual_quality.json")
        visual.write_text('{"status":"pass"}', encoding="utf-8")
        figure = professional_docx.with_suffix(".figure_manifest.json")
        figure.write_text('{"delivery_allowed":true}', encoding="utf-8")
        required = {
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
        receipt.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "variant": variant,
                    "professional_docx_sha256": output_sha256,
                    "quality_gate": required,
                    "structural_quality": {"receipt": str(structural)},
                    "visual_quality": {"receipt": str(visual)},
                }
            ),
            encoding="utf-8",
        )
        assert result["docx"] == [str(path) for path in source_docs]
        return {
            "professional_docx": str(professional_docx),
            "professional_json": str(professional_json),
            "professional_render_receipt": str(receipt),
        }

    monkeypatch.setattr(actions_bridge, "render_professional_document", fake_render)
    outputs = {
        "json": str(source_json),
        "docx": [str(path) for path in source_docs],
        "compare_docx": [str(tmp_path / "compare.docx")],
    }

    delivered = await actions_bridge._render_professional_outputs_for_job(
        job_id="job-professional",
        outputs=outputs,
    )

    assert rendered_calls == [1, 2]
    assert delivered["source_docx"] == [str(path) for path in source_docs]
    assert delivered["docx"] == delivered["professional_docx"]
    assert delivered["docx"] == [
        str(tmp_path / "professional-v1.docx"),
        str(tmp_path / "professional-v2.docx"),
    ]
    assert delivered["delivery_profile"] == "sonnet5_professional_word"
    delivery_receipt = json.loads(Path(delivered["delivery_receipt"]).read_text(encoding="utf-8"))
    assert delivery_receipt["status"] == "pass"
    assert delivery_receipt["variant_count"] == 2
    assert len(delivered["delivery_decision_digest"]) == 64
    assert outputs["docx"] == [str(path) for path in source_docs]


@pytest.mark.asyncio
async def test_professional_delivery_fails_atomically_without_exposing_source_as_final(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.professional_document_renderer import ProfessionalRenderError

    source_json = tmp_path / "result.json"
    source_json.write_text('{"variants": [{}, {}]}', encoding="utf-8")
    source_docs = [tmp_path / "source-v1.docx", tmp_path / "source-v2.docx"]
    for path in source_docs:
        path.write_bytes(b"source")

    async def fake_render(*, job_id, variant, result):
        if variant == 2:
            raise ProfessionalRenderError("专业质量门禁未通过")
        return {
            "professional_docx": str(tmp_path / "professional-v1.docx"),
            "professional_json": str(tmp_path / "professional-v1.json"),
            "professional_render_receipt": str(tmp_path / "professional-v1.receipt.json"),
        }

    monkeypatch.setattr(actions_bridge, "render_professional_document", fake_render)
    outputs = {"json": str(source_json), "docx": [str(path) for path in source_docs]}

    with pytest.raises(ProfessionalRenderError, match="专业质量门禁未通过"):
        await actions_bridge._render_professional_outputs_for_job(
            job_id="job-professional-failed",
            outputs=outputs,
        )

    assert outputs == {"json": str(source_json), "docx": [str(path) for path in source_docs]}


def test_web_ui_has_no_manual_professional_render_button() -> None:
    source = (Path(__file__).parents[2] / "app.py").read_text(encoding="utf-8")

    assert "由 Sonnet 5 精修并渲染专业版" not in source
    assert "下载专业施工组织设计" in source
    assert '"professional_render_receipt"' in source
    assert '"delivery_receipt"' in source
    assert "任务级交付凭证已通过" in source


def test_professional_render_failure_preserves_sources_without_exposing_final(
    tmp_path: Path,
) -> None:
    from backend.app.routers import actions_bridge

    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    compare = tmp_path / "compare.docx"
    compare.write_bytes(b"compare")
    outputs = {
        "json": ["x.json"],
        "docx": [str(source)],
        "compare_docx": [str(compare)],
    }
    secret = "sk-secret12345678"

    recovery, info = actions_bridge._professional_render_failure_result(
        outputs,
        ConnectionError(f"connection reset {secret}"),
    )

    assert recovery["source_docx"] == [str(source)]
    assert "docx" not in recovery
    assert recovery["compare_docx"] == [str(compare)]
    assert recovery["delivery_profile"] == "professional_render_incomplete"
    assert recovery["professional_render_status"]["status"] == "failed"
    assert recovery["professional_render_status"]["source_preserved"] is True
    assert secret not in json.dumps(recovery, ensure_ascii=False)
    assert info["retryable"] is True
    assert outputs["docx"] == [str(source)]
