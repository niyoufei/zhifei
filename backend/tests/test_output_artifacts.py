from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan import output_artifacts
from backend.zhifei_autoplan import exporter as exporter_module


def test_save_outputs_writes_expected_artifact_bundle(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _write_docx(_variant, out_path: str) -> str:
        Path(out_path).write_bytes(b"docx")
        return out_path

    def _write_compare(_variant, out_path: str) -> str:
        Path(out_path).write_bytes(b"compare")
        return out_path

    def _write_focus(_variant, out_path: str) -> str:
        Path(out_path).write_bytes(b"focus")
        return out_path

    monkeypatch.setattr(output_artifacts, "export_autoplan_docx", _write_docx)
    monkeypatch.setattr(output_artifacts, "export_autoplan_compare_docx", _write_compare)
    monkeypatch.setattr(output_artifacts, "export_autoplan_focus_xlsx", _write_focus)
    monkeypatch.delattr(exporter_module, "export_scoring_evidence_overview_xlsx", raising=False)
    monkeypatch.delattr(exporter_module, "export_expert_review_brief_docx", raising=False)

    variant = {
        "topic": "测试施组",
        "sections": [
            {
                "title": "工程概况",
                "content": "项目概况。",
                "case_reference_pack": {"enabled": True, "selected_case_ids": ["case-1"]},
                "image_selection_pack": {"enabled": True, "selected_image_ids": ["image-1"]},
            }
        ],
    }

    out = output_artifacts.save_outputs("artifact_test", [variant])

    assert sorted(out) == [
        "compare_docx",
        "docx",
        "expert_review_docx",
        "focus_xlsx",
        "json",
        "score_overview_xlsx",
    ]
    assert Path(out["json"]).exists()
    assert Path(out["docx"][0]).read_bytes() == b"docx"
    assert Path(out["compare_docx"][0]).read_bytes() == b"compare"
    assert Path(out["focus_xlsx"][0]).read_bytes() == b"focus"
    assert out["score_overview_xlsx"] == [None]
    assert out["expert_review_docx"] == [None]

    payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
    saved = payload["variants"][0]["sections"][0]
    assert saved["case_reference_pack"]["selected_case_ids"] == ["case-1"]
    assert saved["image_selection_pack"]["selected_image_ids"] == ["image-1"]


def test_preview_only_writes_sanitized_json_without_formal_exporters(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    formal_calls: list[str] = []
    monkeypatch.setattr(
        output_artifacts,
        "export_autoplan_docx",
        lambda *_args, **_kwargs: formal_calls.append("docx"),
    )
    monkeypatch.setattr(
        output_artifacts,
        "export_autoplan_compare_docx",
        lambda *_args, **_kwargs: formal_calls.append("compare_docx"),
    )
    monkeypatch.setattr(
        output_artifacts,
        "export_autoplan_focus_xlsx",
        lambda *_args, **_kwargs: formal_calls.append("focus_xlsx"),
    )

    out = output_artifacts.save_outputs(
        "preview_test",
        [{"sections": [], "dynamic_prompt": "sensitive prompt"}],
        preview_only=True,
    )

    assert formal_calls == []
    assert out["docx"] == []
    assert out["compare_docx"] == []
    assert out["focus_xlsx"] == []
    assert Path(out["json"]).is_file()
    payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
    assert payload["variants"][0]["dynamic_prompt"] == "[OMITTED]"
