from __future__ import annotations

import copy
import sys

from backend.zhifei_autoplan import section_drafts
from backend.zhifei_autoplan.section_drafts import (
    apply_section_draft,
    build_draft_audit_record,
    build_section_draft,
    compute_section_draft_diff,
    hash_section_content,
    reject_section_draft,
    rollback_section_draft,
)


FIXED_AT = "2026-05-01T00:00:00Z"


def test_hash_section_content_is_deterministic() -> None:
    assert hash_section_content("施工部署") == hash_section_content("施工部署")
    assert hash_section_content("施工部署") != hash_section_content("施工部署补充")


def test_build_section_draft_preserves_original_inputs() -> None:
    original = "原章节正文"
    draft_text = "本地模型建议后的章节正文"

    draft = build_section_draft(
        draft_id="draft-1",
        section_title="Ollama主链烟测",
        original_content=original,
        draft_content=draft_text,
        provider="ollama",
        model="qwen3:0.6b",
        base_url="http://127.0.0.1:11434",
        prompt_hash="prompt-sha",
        created_at=FIXED_AT,
    )

    assert original == "原章节正文"
    assert draft["draft_id"] == "draft-1"
    assert draft["section_title"] == "Ollama主链烟测"
    assert draft["original_content"] == original
    assert draft["draft_content"] == draft_text
    assert draft["original_hash"] == hash_section_content(original)
    assert draft["draft_hash"] == hash_section_content(draft_text)
    assert draft["original_hash"] != draft["draft_hash"]
    assert draft["status"] == "draft"
    assert draft["provider"] == "ollama"
    assert draft["model"] == "qwen3:0.6b"
    assert draft["base_url"] == "http://127.0.0.1:11434"
    assert draft["prompt_hash"] == "prompt-sha"
    assert draft["created_at"] == FIXED_AT
    assert draft["audit"][0]["action_type"] == "created"


def test_build_section_draft_can_hash_prompt_when_prompt_hash_missing() -> None:
    draft = build_section_draft(
        draft_id="draft-2",
        section_title="质量控制",
        original_content="原文",
        draft_content="草稿",
        prompt="复核质量控制",
        created_at=FIXED_AT,
    )

    assert draft["prompt_hash"] == hash_section_content("复核质量控制")


def test_compute_section_draft_diff_generates_preview() -> None:
    diff = compute_section_draft_diff("第一行\n原措施", "第一行\n新措施")

    assert "--- original" in diff
    assert "+++ draft" in diff
    assert "-原措施" in diff
    assert "+新措施" in diff


def test_build_draft_audit_record_contains_required_fields() -> None:
    record = build_draft_audit_record(
        provider="ollama",
        model="qwen3:0.6b",
        base_url="http://127.0.0.1:11434",
        prompt_hash="prompt-sha",
        section_title="安全措施",
        original_hash="orig",
        draft_hash="draft",
        confirmed_by="reviewer",
        confirmed_at=FIXED_AT,
        action_type="applied",
    )

    assert record == {
        "provider": "ollama",
        "model": "qwen3:0.6b",
        "base_url": "http://127.0.0.1:11434",
        "prompt_hash": "prompt-sha",
        "section_title": "安全措施",
        "original_hash": "orig",
        "draft_hash": "draft",
        "confirmed_by": "reviewer",
        "confirmed_at": FIXED_AT,
        "action_type": "applied",
    }


def test_apply_section_draft_returns_new_structure_without_mutating_input() -> None:
    draft = build_section_draft(
        draft_id="draft-3",
        section_title="进度计划",
        original_content="原进度",
        draft_content="草稿进度",
        provider="ollama",
        model="qwen3:0.6b",
        created_at=FIXED_AT,
    )
    before = copy.deepcopy(draft)

    applied = apply_section_draft(draft, confirmed_by="user-1", confirmed_at=FIXED_AT)

    assert draft == before
    assert applied is not draft
    assert applied["status"] == "applied"
    assert applied["applied_content"] == "草稿进度"
    assert applied["applied_hash"] == hash_section_content("草稿进度")
    assert applied["audit"][-1]["action_type"] == "applied"
    assert applied["audit"][-1]["confirmed_by"] == "user-1"
    assert applied["audit"][-1]["confirmed_at"] == FIXED_AT


def test_reject_section_draft_returns_rejected_status_without_content_change() -> None:
    draft = build_section_draft(
        draft_id="draft-4",
        section_title="资源配置",
        original_content="原资源",
        draft_content="草稿资源",
        created_at=FIXED_AT,
    )

    rejected = reject_section_draft(draft, confirmed_by="reviewer", confirmed_at=FIXED_AT)

    assert rejected["status"] == "rejected"
    assert rejected["original_content"] == "原资源"
    assert rejected["draft_content"] == "草稿资源"
    assert rejected["audit"][-1]["action_type"] == "rejected"
    assert draft["status"] == "draft"


def test_rollback_section_draft_restores_original_content() -> None:
    draft = build_section_draft(
        draft_id="draft-5",
        section_title="质量验收",
        original_content="原验收",
        draft_content="草稿验收",
        created_at=FIXED_AT,
    )

    rolled_back = rollback_section_draft(draft, confirmed_by="reviewer", confirmed_at=FIXED_AT)

    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["draft_content"] == "原验收"
    assert rolled_back["rolled_back_content"] == "原验收"
    assert rolled_back["draft_hash"] == hash_section_content("原验收")
    assert rolled_back["audit"][-1]["action_type"] == "rolled_back"
    assert draft["draft_content"] == "草稿验收"


def test_section_drafts_module_does_not_pull_main_chain_or_write_modules(assert_clean_import) -> None:
    assert not hasattr(section_drafts, "LLMClient")
    assert not hasattr(section_drafts, "run_autoplan")
    assert not hasattr(section_drafts, "OllamaProvider")
    assert_clean_import(
        "backend.zhifei_autoplan.section_drafts",
        {
            "backend.zhifei_autoplan.orchestrator",
            "backend.zhifei_autoplan.job_store",
            "backend.zhifei_autoplan.output_artifacts",
            "backend.zhifei_autoplan.export_docx_service",
            "backend.app.routers.actions_bridge",
        },
    )
