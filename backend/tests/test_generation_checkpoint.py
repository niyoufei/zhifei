from __future__ import annotations

import json

import pytest

from backend.zhifei_autoplan.generation_checkpoint import (
    CheckpointIntegrityError,
    build_chapter_context_digest,
    build_generation_binding,
    cleanup_checkpoint_namespace,
    finalize_generation_checkpoint,
    load_section_checkpoint,
    mark_checkpoint_namespace_interrupted,
    mark_failed_checkpoint_namespace,
    save_section_checkpoint,
)


def _binding(
    *,
    topic: str = "示例工程",
    delivery_scope: str = "document",
    attempt_id: str = "b" * 32,
) -> dict:
    return build_generation_binding(
        job_id="a" * 32,
        attempt_id=attempt_id,
        owner_instance_id="c" * 32,
        job_revision=2,
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
        delivery_scope=delivery_scope,
    )


def _context_digest(
    *,
    chapter_index: int = 0,
    chapter_title: str = "施工部署",
    evidence: str = "文档证据-A",
    delivery_scope: str = "document",
) -> str:
    return build_chapter_context_digest(
        chapter_index=chapter_index,
        chapter_title=chapter_title,
        delivery_scope=delivery_scope,
        writer_context={
            "doc_evidence": [evidence],
            "kg_evidence": ["图谱节点-A"],
            "compliance_hits": [{"standard_code": "GB/T 50326-2017"}],
        },
    )


def test_section_round_trip_is_integrity_bound_and_redacts_credentials(tmp_path):
    binding = _binding()
    summary = save_section_checkpoint(
        namespace="job-1",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=_context_digest(),
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
        chapter_context_digest=_context_digest(),
        root=tmp_path,
    )
    assert loaded["content"] == "正文"
    raw = (tmp_path / "job-1" / "variant-1.json").read_text(encoding="utf-8")
    persisted = json.loads(raw)
    assert persisted["schema_version"] == "generation-checkpoint-v3"
    assert persisted["sections"]["0"]["chapter_context_digest"] == _context_digest()
    assert "must-never-persist" not in raw
    assert "secret" not in raw


def test_binding_drift_never_reuses_old_section(tmp_path):
    save_section_checkpoint(
        namespace="job-2",
        scope="variant-1",
        binding=_binding(topic="旧项目"),
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=_context_digest(),
        result={"title": "施工部署", "content": "旧正文"},
        root=tmp_path,
    )
    assert load_section_checkpoint(
        namespace="job-2",
        scope="variant-1",
        binding=_binding(topic="新项目"),
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=_context_digest(),
        root=tmp_path,
    ) is None


def test_delivery_scope_is_part_of_generation_binding() -> None:
    document = _binding(delivery_scope="document")
    validation = _binding(delivery_scope="chapter_validation")

    assert document["delivery_scope"] == "document"
    assert validation["delivery_scope"] == "chapter_validation"
    assert document["binding_digest"] != validation["binding_digest"]


def test_terminal_execution_lineage_is_part_of_generation_binding() -> None:
    first = _binding(attempt_id="b" * 32)
    second = _binding(attempt_id="d" * 32)

    assert first["job_id"] == "a" * 32
    assert first["attempt_id"] == "b" * 32
    assert first["owner_instance_id"] == "c" * 32
    assert first["job_revision"] == 2
    assert first["binding_digest"] != second["binding_digest"]


def test_chapter_context_digest_ignores_wall_clock_and_secrets() -> None:
    base = {
        "doc_evidence": ["招标文件.pdf#p3: 工期要求"],
        "kg_evidence": ["进度图谱/关键线路: 先地下后地上"],
        "max_chapter_output_tokens": 4096,
        "max_model_output_tokens": 4096,
        "created_at": "2026-08-27T10:00:00+08:00",
        "provider_api_key": "first-secret",
    }
    changed_ephemeral = {
        **base,
        "created_at": "2026-08-28T11:00:00+08:00",
        "provider_api_key": "second-secret",
    }

    first = build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context=base,
    )
    second = build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context=changed_ephemeral,
    )

    assert first == second
    assert first == build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context={
            key: value for key, value in base.items() if key != "provider_api_key"
        },
    )
    assert first != build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context={**base, "doc_evidence": ["招标文件.pdf#p4: 新工期要求"]},
    )
    assert first != build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context={**base, "max_chapter_output_tokens": 8192},
    )
    assert first != build_chapter_context_digest(
        chapter_index=0,
        chapter_title="施工部署",
        delivery_scope="document",
        writer_context={**base, "max_model_output_tokens": 8192},
    )


def test_context_drift_rejects_only_affected_chapter(tmp_path) -> None:
    binding = _binding()
    first_context = _context_digest()
    second_context = _context_digest(
        chapter_index=1,
        chapter_title="质量管理",
        evidence="质量证据-A",
    )
    save_section_checkpoint(
        namespace="job-context-drift",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=first_context,
        result={"title": "施工部署", "content": "部署正文"},
        root=tmp_path,
    )
    save_section_checkpoint(
        namespace="job-context-drift",
        scope="variant-1",
        binding=binding,
        chapter_index=1,
        chapter_title="质量管理",
        chapter_context_digest=second_context,
        result={"title": "质量管理", "content": "质量正文"},
        root=tmp_path,
    )

    assert load_section_checkpoint(
        namespace="job-context-drift",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=_context_digest(evidence="文档证据-B"),
        root=tmp_path,
    ) is None
    assert load_section_checkpoint(
        namespace="job-context-drift",
        scope="variant-1",
        binding=binding,
        chapter_index=1,
        chapter_title="质量管理",
        chapter_context_digest=second_context,
        root=tmp_path,
    )["content"] == "质量正文"


def test_tampered_file_is_rejected(tmp_path):
    binding = _binding()
    save_section_checkpoint(
        namespace="job-3",
        scope="variant-1",
        binding=binding,
        chapter_index=0,
        chapter_title="施工部署",
        chapter_context_digest=_context_digest(),
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
            chapter_context_digest=_context_digest(),
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
        chapter_context_digest=_context_digest(),
        result={"title": "施工部署", "content": "正文"},
        root=tmp_path,
    )
    save_section_checkpoint(
        namespace="job-4",
        scope="variant-1",
        binding=binding,
        chapter_index=1,
        chapter_title="质量管理",
        chapter_context_digest=_context_digest(
            chapter_index=1,
            chapter_title="质量管理",
        ),
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
        chapter_context_digest=_context_digest(),
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
        chapter_context_digest=_context_digest(),
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
        chapter_context_digest=_context_digest(),
        result={"title": "施工部署", "content": "可信正文"},
        root=tmp_path,
    )

    summaries = mark_failed_checkpoint_namespace("job-6", root=tmp_path)

    assert summaries[0]["status"] == "failed_partial"
    assert summaries[0]["saved_chapter_count"] == 1
    assert summaries[0]["chapters_total"] == 2
