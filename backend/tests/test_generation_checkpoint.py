from __future__ import annotations

import json

import pytest

from backend.zhifei_autoplan.generation_checkpoint import (
    CheckpointIntegrityError,
    build_generation_binding,
    cleanup_checkpoint_namespace,
    finalize_generation_checkpoint,
    load_section_checkpoint,
    mark_checkpoint_namespace_interrupted,
    mark_failed_checkpoint_namespace,
    save_section_checkpoint,
)


def _binding(*, topic: str = "示例工程") -> dict:
    return build_generation_binding(
        topic=topic,
        project_id="P-001",
        project_type="房建",
        outline=["施工部署", "质量管理"],
        style={"line_spacing_pt": 22},
        chapter_pages={"施工部署": 10, "质量管理": 12},
        variant_id=1,
        project_fact_digest="a" * 64,
        requirement_plan_digest="b" * 64,
        provider_routes=[
            {
                "slot": "text_draft",
                "provider": "anthropic",
                "model": "claude-sonnet",
                "api_key": "must-never-persist",
            }
        ],
    )


def test_section_round_trip_is_integrity_bound_and_redacts_credentials(tmp_path):
    binding = _binding()
    summary = save_section_checkpoint(
        namespace="job-1",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "正文", "api_key": "secret"},
        root=tmp_path,
    )
    assert summary["saved_chapter_count"] == 1
    loaded = load_section_checkpoint(
        namespace="job-1",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        root=tmp_path,
    )
    assert loaded["content"] == "正文"
    raw = (tmp_path / "job-1" / "variant-1.json").read_text(encoding="utf-8")
    assert "must-never-persist" not in raw
    assert "secret" not in raw


def test_binding_drift_never_reuses_old_section(tmp_path):
    save_section_checkpoint(
        namespace="job-2",
        scope="variant-1",
        binding=_binding(topic="旧项目"),
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "旧正文"},
        root=tmp_path,
    )
    assert load_section_checkpoint(
        namespace="job-2",
        scope="variant-1",
        binding=_binding(topic="新项目"),
        chapter_index=0,
        chapter_title="施工部署",
        root=tmp_path,
    ) is None


def test_tampered_file_is_rejected(tmp_path):
    binding = _binding()
    save_section_checkpoint(
        namespace="job-3",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "可信正文"},
        root=tmp_path,
    )
    path = tmp_path / "job-3" / "variant-1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["sections"]["0"]["result"]["content"] = "篡改正文"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CheckpointIntegrityError, match="integrity"):
        load_section_checkpoint(
            namespace="job-3",
            scope="variant-1",
            binding=binding,
            chapter_index=0,
            chapter_title="施工部署",
            root=tmp_path,
        )


def test_finalize_and_cleanup(tmp_path):
    binding = _binding()
    save_section_checkpoint(
        namespace="job-4",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "正文"},
        root=tmp_path,
    )
    save_section_checkpoint(
        namespace="job-4",
        scope="variant-1",
        binding=binding,
        chapter_index=1,
        chapter_title="质量管理",
        result={"title": "质量管理", "content": "正文"},
        root=tmp_path,
    )
    summary = finalize_generation_checkpoint(
        namespace="job-4",
        scope="variant-1",
        binding=binding,
        root=tmp_path,
    )
    assert summary["status"] == "complete"
    assert cleanup_checkpoint_namespace("job-4", root=tmp_path) is True
    assert not (tmp_path / "job-4").exists()


def test_interrupted_namespace_preserves_saved_sections(tmp_path):
    binding = _binding()
    save_section_checkpoint(
        namespace="job-5",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "可信正文"},
        root=tmp_path,
    )

    summaries = mark_checkpoint_namespace_interrupted("job-5", root=tmp_path)

    assert summaries[0]["status"] == "interrupted_recoverable"
    assert summaries[0]["saved_chapter_count"] == 1
    assert load_section_checkpoint(
        namespace="job-5",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        root=tmp_path,
    )["content"] == "可信正文"


def test_failed_namespace_uses_saved_section_count(tmp_path):
    binding = _binding()
    save_section_checkpoint(
        namespace="job-6",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        result={"title": "施工部署", "content": "可信正文"},
        root=tmp_path,
    )

    summaries = mark_failed_checkpoint_namespace("job-6", root=tmp_path)

    assert summaries[0]["status"] == "failed_partial"
    assert summaries[0]["saved_chapter_count"] == 1
    assert summaries[0]["chapters_total"] == 2
