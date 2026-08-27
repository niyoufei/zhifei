"""Unit tests for backend/zhifei_autoplan/orchestrator.py"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json
from pathlib import Path
import sys
import types

from backend.zhifei_autoplan.orchestrator import (
    _build_weights_and_penalties,
    _chapter_deadline_seconds,
    _is_critical_review_chapter,
    _provider_chain_for_role,
    run_autoplan,
)
from backend.zhifei_autoplan.execution_control import ExecutionBudgetExceededError


def test_long_chapter_deadline_allows_one_bounded_continuation() -> None:
    assert _chapter_deadline_seconds({}, target_pages=7) == 480
    assert _chapter_deadline_seconds({}, target_pages=10) == 900
    assert (
        _chapter_deadline_seconds(
            {"chapter_deadline_seconds": 1200}, target_pages=16
        )
        == 900
    )


@pytest.fixture(autouse=True)
def _allow_legacy_unadmitted_unit_payloads(monkeypatch):
    """Old direct unit payloads are not HTTP-callable production entrypoints."""

    from backend.zhifei_autoplan import orchestrator

    monkeypatch.setattr(
        orchestrator,
        "_ALLOW_UNADMITTED_PROVIDER_CALLS_FOR_TESTS",
        True,
    )


@pytest.fixture(autouse=True)
def _mock_mindmap_generation():
    """Avoid external image-model calls during unit tests."""
    with patch(
        "backend.zhifei_autoplan.orchestrator.generate_outline_mindmap",
        return_value={"path": "/tmp/mock_mindmap.png", "caption": "施工组织设计思维导图（Gemini）"},
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_verified_compliance_registry():
    """Keep orchestration unit tests independent from repository catalog state.

    The compliance registry has its own focused test module.  Tests in this
    module exercise orchestration, provider routing, roles, and failure
    handling, so they receive one traceable current standard by default.
    """
    verified_standard = {
        "standard_code": "GB/T 50326-2017",
        "standard_name": "建设工程项目管理规范",
        "source_name": "建设工程项目管理规范",
        "current_version": "GB/T 50326-2017",
        "effective_status": "现行有效",
        "official_source": "https://official.example/GB-T-50326-2017",
        "domain_tags": ["通用工程"],
        "latest": True,
    }
    with patch(
        "backend.zhifei_autoplan.orchestrator.get_compliance_registry_status",
        return_value={"ready": True, "verified_count": 1, "warnings": []},
    ), patch(
        "backend.zhifei_autoplan.orchestrator.list_verified_standard_metadata",
        return_value=[verified_standard],
    ):
        yield


def _find_ctx_by_title(mock_writer, title: str) -> dict:
    for call_args in mock_writer.write.call_args_list:
        if call_args and len(call_args[0]) >= 2 and str(call_args[0][0]) == title:
            ctx = call_args[0][1]
            return ctx if isinstance(ctx, dict) else {}
    return {}


WRITE_PATH_MODULES = {
    "backend.app.routers.actions_bridge",
    "backend.zhifei_autoplan.job_store",
    "backend.zhifei_autoplan.output_artifacts",
    "backend.zhifei_autoplan.exporter",
    "backend.zhifei_autoplan.export_docx_service",
}


def _passing_quality_result() -> dict:
    """Return the smallest complete quality receipt accepted by delivery gates.

    Most orchestrator tests isolate routing, role selection, and context wiring.
    Their quality checker is mocked, so the mock must still satisfy the same
    evidence contract as the real checker instead of accidentally exercising a
    missing-receipt failure path.
    """

    return {
        "score": 100,
        "remediation": [],
        "quality_gate": {"pass": True, "blocking_issue_count": 0},
        "independent_content_review": {
            "threshold": 80,
            "quality_gate": {"pass": True, "blocking_issues": []},
            "issues": [],
        },
    }


def _loaded_write_paths() -> set[str]:
    return WRITE_PATH_MODULES.intersection(sys.modules)


def _assert_write_paths_unchanged(before: set[str]) -> None:
    assert _loaded_write_paths() == before


def _file_count(path: str) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    if root.is_file():
        return 1
    return sum(1 for item in root.rglob("*") if item.is_file())


def test_tiered_provider_chain_keeps_fable_opt_in_only():
    chain = [
        {"slot": "text_draft", "provider": "anthropic", "model": "claude-sonnet-5"},
        {"slot": "text_review", "provider": "anthropic", "model": "claude-opus-5"},
        {"slot": "text_backup", "provider": "openai", "model": "gpt-5.6-sol"},
        {"slot": "text_escalation", "provider": "anthropic", "model": "claude-fable-5"},
    ]

    draft = _provider_chain_for_role(chain, "draft")
    review = _provider_chain_for_role(chain, "review")
    review_with_escalation = _provider_chain_for_role(
        chain,
        "review",
        allow_fable_escalation=True,
    )

    assert [item["slot"] for item in draft] == ["text_draft", "text_backup", "text_review"]
    assert [item["slot"] for item in review] == ["text_review", "text_backup", "text_draft"]
    assert [item["slot"] for item in review_with_escalation] == [
        "text_review",
        "text_escalation",
        "text_backup",
        "text_draft",
    ]


def test_critical_review_chapter_classifier():
    assert _is_critical_review_chapter("施工总体部署") is True
    assert _is_critical_review_chapter("质量验收与安全应急") is True
    assert _is_critical_review_chapter("项目概况") is False


# =============================================================================
# Tests for _build_weights_and_penalties
# =============================================================================

class TestBuildWeightsAndPenalties:
    """Tests for _build_weights_and_penalties function."""

    def test_empty_tender(self):
        """Empty tender returns empty lists."""
        weights, penalties = _build_weights_and_penalties({})
        assert weights == []
        assert penalties == []

    def test_tender_without_items(self):
        """Tender without items key returns empty lists."""
        weights, penalties = _build_weights_and_penalties({"name": "test"})
        assert weights == []
        assert penalties == []

    def test_tender_with_empty_items(self):
        """Tender with empty items list returns empty lists."""
        weights, penalties = _build_weights_and_penalties({"items": []})
        assert weights == []
        assert penalties == []

    def test_single_weight_item(self):
        """Single weight item is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": ["关键词1", "关键词2"], "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "技术" in weights[0]
        assert "权重=30" in weights[0]
        assert "关键词1" in weights[0]
        assert len(penalties) == 0

    def test_single_penalty_item_扣分项(self):
        """Penalty item with dimension '扣分项' is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "扣分项", "keywords": ["违规1", "违规2"], "weight": -10}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 0
        assert len(penalties) == 1
        assert "扣分项" in penalties[0]
        assert "违规1" in penalties[0]

    def test_single_penalty_item_PENALTY(self):
        """Penalty item with dimension 'PENALTY' is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "PENALTY", "keywords": ["penalty1"], "weight": -5}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 0
        assert len(penalties) == 1
        assert "扣分项" in penalties[0]

    def test_mixed_items(self):
        """Mixed weight and penalty items are correctly separated."""
        tender = {
            "items": [
                {"dimension": "技术方案", "keywords": ["kw1", "kw2"], "weight": 40},
                {"dimension": "扣分项", "keywords": ["p1", "p2"], "weight": -10},
                {"dimension": "商务", "keywords": ["kw3"], "weight": 30},
                {"dimension": "PENALTY", "keywords": ["p3"], "weight": -5},
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 2
        assert len(penalties) == 2

    def test_keywords_truncation_weights(self):
        """Keywords in weights are truncated to 8."""
        tender = {
            "items": [
                {
                    "dimension": "技术",
                    "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10"],
                    "weight": 30
                }
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        # kw9 and kw10 should not be in the output (truncated at 8)
        assert "kw8" in weights[0]
        assert "kw9" not in weights[0]

    def test_keywords_truncation_penalties(self):
        """Keywords in penalties are truncated to 10."""
        tender = {
            "items": [
                {
                    "dimension": "扣分项",
                    "keywords": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12"],
                    "weight": -10
                }
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(penalties) == 1
        assert "p10" in penalties[0]
        assert "p11" not in penalties[0]

    def test_missing_keywords(self):
        """Item without keywords handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "技术" in weights[0]

    def test_none_keywords(self):
        """Item with None keywords handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": None, "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1

    def test_missing_weight(self):
        """Item without weight handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": ["kw1"]}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "权重=None" in weights[0]

    def test_integer_dimension(self):
        """Integer dimension is converted to string."""
        tender = {
            "items": [
                {"dimension": 123, "keywords": ["kw1"], "weight": 10}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "123" in weights[0]


# =============================================================================
# Tests for run_autoplan
# =============================================================================

class TestRunAutoplan:
    """Tests for run_autoplan async function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mocks for all external dependencies."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart") as mock_chart, \
             patch("backend.zhifei_autoplan.orchestrator.generate_ingested_previews") as mock_previews, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_remediate, \
             patch("backend.zhifei_autoplan.orchestrator.get_compliance_registry_status") as mock_compliance_status, \
             patch("backend.zhifei_autoplan.orchestrator.list_verified_standard_metadata") as mock_verified_standards:

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer

            mock_quality.return_value = _passing_quality_result()
            mock_previews.return_value = []
            # These orchestration unit tests exercise routing and context
            # wiring, not the repository-backed compliance registry.  Keep a
            # minimal verified record in the fixture so an unrelated local
            # catalog refresh cannot make the suite fail closed.
            mock_compliance_status.return_value = {
                "ready": True,
                "verified_count": 1,
                "warnings": [],
            }
            mock_verified_standards.return_value = [
                {
                    "standard_code": "GB/T 50326-2017",
                    "standard_name": "建设工程项目管理规范",
                    "source_name": "建设工程项目管理规范",
                    "current_version": "GB/T 50326-2017",
                    "effective_status": "现行有效",
                    "official_source": "https://official.example/GB-T-50326-2017",
                    "domain_tags": ["通用工程"],
                    "latest": True,
                }
            ]

            yield {
                "tender": mock_tender,
                "boq": mock_boq,
                "kg": mock_kg,
                "docs": mock_docs,
                "llm_cls": mock_llm_cls,
                "writer_cls": mock_writer_cls,
                "writer": mock_writer,
                "chart": mock_chart,
                "previews": mock_previews,
                "quality": mock_quality,
                "remediate": mock_remediate,
                "compliance_status": mock_compliance_status,
                "verified_standards": mock_verified_standards,
            }

    @pytest.mark.asyncio
    async def test_empty_payload(self, mock_dependencies):
        """Empty payload returns default structure."""
        result = await run_autoplan({})

        assert result["topic"] == "未命名项目"
        assert isinstance(result["outline"], list) and result["outline"]
        assert "编制依据与原则" in result["outline"]
        assert len(result["sections"]) == len(result["outline"])
        assert "quality_checks" in result
        assert "evidence" in result

    @pytest.mark.asyncio
    async def test_topic_from_payload(self, mock_dependencies):
        """Topic is taken from payload."""
        result = await run_autoplan({"topic": "测试项目"})
        assert result["topic"] == "测试项目"

    @pytest.mark.asyncio
    async def test_project_fact_conflict_blocks_before_any_writer_call(self, mock_dependencies):
        """Conflicting tender facts fail closed before any chapter model is invoked."""
        with pytest.raises(ValueError, match="项目事实台账存在同优先级冲突"):
            await run_autoplan(
                {
                    "tender_matrix": {
                        "project_code": "HEADER-01",
                        "project_facts": {"project_code": "BODY-02"},
                    },
                    "outline": ["第一章"],
                    "generate_images": False,
                }
            )

        mock_dependencies["writer"].write.assert_not_called()

    @pytest.mark.asyncio
    async def test_project_fact_snapshot_is_shared_with_writer_and_result(self, mock_dependencies):
        """All chapter writers receive the same digest-bound project facts."""
        result = await run_autoplan(
            {
                "tender_matrix": {
                    "project_name": "招标权威项目名称",
                    "project_code": "TENDER-01",
                },
                "topic": "较低优先级用户名称",
                "outline": ["第一章"],
                "quality_strict": False,
                "dry_run": True,
                "generate_images": False,
            }
        )

        ledger = result["project_fact_ledger"]
        assert result["project_fact_validation"]["ok"] is True
        assert ledger["facts"]["project_name"]["value"] == "招标权威项目名称"
        writer_ctx = mock_dependencies["writer"].write.call_args.args[1]
        assert writer_ctx["project_fact_ledger_digest"] == ledger["ledger_digest"]
        assert writer_ctx["project_fact_snapshot"]["ledger_digest"] == ledger["ledger_digest"]
        assert writer_ctx["project_fact_snapshot"]["facts"]["project_code"]["value"] == "TENDER-01"

    @pytest.mark.asyncio
    async def test_outline_sections(self, mock_dependencies):
        """Sections are generated for each outline item."""
        result = await run_autoplan({
            "outline": ["第一章", "第二章", "第三章"]
        })

        assert len(result["sections"]) >= 3
        assert "第一章" in result["outline"]
        assert "第二章" in result["outline"]
        assert "第三章" in result["outline"]
        assert mock_dependencies["writer"].write.call_count == len(result["sections"])

    @pytest.mark.asyncio
    async def test_dry_run_no_llm(self, mock_dependencies):
        """Dry run does not instantiate LLM."""
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": True,
        })

        mock_dependencies["llm_cls"].assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_model_passed_to_llm(self, mock_dependencies):
        """Provider and model are passed to LLMClient."""
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "dry_run": False,
        })

        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["provider"] == "openai"
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_ollama_provider_path_passes_to_llm_without_real_ollama(self, mock_dependencies):
        """Ollama provider is passed to LLMClient, while the real adapter and write paths stay untouched."""
        write_paths_before = _loaded_write_paths()
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "base_url": "http://127.0.0.1:11434",
            "dry_run": False,
        })

        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["provider"] == "ollama"
        assert call_kwargs["model"] == "qwen3:0.6b"
        assert call_kwargs["base_url"] == "http://127.0.0.1:11434"
        assert call_kwargs["api_key"] is None
        _assert_write_paths_unchanged(write_paths_before)

    @pytest.mark.asyncio
    async def test_no_write_ollama_main_chain_smoke_guard(self, mock_dependencies, monkeypatch):
        """Ollama can enter run_autoplan with write paths patched and no real network calls."""
        from backend.zhifei_autoplan import param_trace

        before_counts = {
            "jobs": _file_count("backend/data/autoplan/jobs"),
            "build": _file_count("build"),
            "output": _file_count("output"),
        }
        blocked_calls: list[str] = []

        def _blocked(name: str):
            def _inner(*args, **kwargs):
                blocked_calls.append(name)
                raise AssertionError(f"{name} should not be called")

            return _inner

        def _fake_module(name: str, functions: list[str]):
            module = types.ModuleType(name)
            for fn in functions:
                setattr(module, fn, _blocked(f"{name}.{fn}"))
            return module

        save_receipt = MagicMock(return_value="mock://param_receipt")
        monkeypatch.setattr(param_trace, "save_latest_receipt", save_receipt)
        monkeypatch.setattr("urllib.request.urlopen", _blocked("urllib.request.urlopen"))
        mock_dependencies["boq"].return_value = {"stats": {"工程量": 1}}
        monkeypatch.setitem(
            sys.modules,
            "backend.zhifei_autoplan.job_store",
            _fake_module("backend.zhifei_autoplan.job_store", ["create_job", "update_job", "get_job"]),
        )
        monkeypatch.setitem(
            sys.modules,
            "backend.zhifei_autoplan.output_artifacts",
            _fake_module("backend.zhifei_autoplan.output_artifacts", ["save_outputs"]),
        )
        monkeypatch.setitem(
            sys.modules,
            "backend.zhifei_autoplan.exporter",
            _fake_module(
                "backend.zhifei_autoplan.exporter",
                [
                    "export_autoplan_docx",
                    "export_autoplan_compare_docx",
                    "export_autoplan_focus_xlsx",
                    "export_scoring_evidence_overview_xlsx",
                    "export_expert_review_brief_docx",
                ],
            ),
        )
        monkeypatch.setitem(
            sys.modules,
            "backend.zhifei_autoplan.export_docx_service",
            _fake_module("backend.zhifei_autoplan.export_docx_service", ["execute_export_docx_request"]),
        )
        monkeypatch.setitem(
            sys.modules,
            "backend.app.routers.actions_bridge",
            _fake_module("backend.app.routers.actions_bridge", ["actions_generate", "actions_generate_async", "_save_outputs"]),
        )

        result = await run_autoplan({
            "topic": "Ollama no-write smoke",
            "outline": ["章节1"],
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "base_url": "http://127.0.0.1:11434",
            "dry_run": False,
            "no_write": True,
        })

        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["provider"] == "ollama"
        assert call_kwargs["model"] == "qwen3:0.6b"
        assert call_kwargs["base_url"] == "http://127.0.0.1:11434"
        assert mock_dependencies["writer"].write.called
        assert result["sections"]
        save_receipt.assert_not_called()
        mock_dependencies["chart"].assert_not_called()
        mock_dependencies["previews"].assert_not_called()
        assert blocked_calls == []
        assert {
            "jobs": _file_count("backend/data/autoplan/jobs"),
            "build": _file_count("build"),
            "output": _file_count("output"),
        } == before_counts

    @pytest.mark.asyncio
    async def test_preview_only_alias_skips_param_receipt_write(self, mock_dependencies, monkeypatch):
        """preview_only is an alias for no-write preview mode."""
        from backend.zhifei_autoplan import param_trace

        save_receipt = MagicMock(return_value="mock://param_receipt")
        monkeypatch.setattr(param_trace, "save_latest_receipt", save_receipt)

        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "base_url": "http://127.0.0.1:11434",
            "dry_run": False,
            "preview_only": True,
        })

        mock_dependencies["llm_cls"].assert_called()
        assert result["sections"]
        save_receipt.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_mode_still_saves_param_receipt(self, mock_dependencies, monkeypatch):
        """Default run_autoplan behavior is unchanged when no_write/preview_only is absent."""
        from backend.zhifei_autoplan import param_trace

        save_receipt = MagicMock(return_value="mock://param_receipt")
        monkeypatch.setattr(param_trace, "save_latest_receipt", save_receipt)

        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "base_url": "http://127.0.0.1:11434",
            "dry_run": False,
            "generate_images": False,
        })

        mock_dependencies["llm_cls"].assert_called()
        assert result["sections"]
        save_receipt.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_openai(self, mock_dependencies, monkeypatch):
        """When api_key is absent, OpenAI provider falls back to OPENAI_API_KEY env."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-openai-key"

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_google(self, mock_dependencies, monkeypatch):
        """When api_key is absent, Google provider falls back to Gemini env keys."""
        monkeypatch.setenv("ZF_GOOGLE_API_KEY", "env-gemini-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "google",
            "model": "gemini-2.5-flash",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-gemini-key"

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_grok(self, mock_dependencies, monkeypatch):
        """When api_key is absent, Grok provider falls back to xAI env keys."""
        monkeypatch.setenv("XAI_API_KEY", "env-grok-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "grok",
            "model": "grok-4-1-fast-reasoning",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-grok-key"

    @pytest.mark.asyncio
    async def test_multi_provider_rotation(self, mock_dependencies):
        """Multiple providers rotate across sections."""
        await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "providers": ["provider1", "provider2"],
            "model_map": {"provider1": "model1", "provider2": "model2"},
            "dry_run": False,
        })

        # 3 sections, providers rotate
        assert mock_dependencies["llm_cls"].call_count >= 3

    @pytest.mark.asyncio
    async def test_kg_search_called(self, mock_dependencies):
        """Knowledge graph search is called for each section."""
        result = await run_autoplan({
            "topic": "测试",
            "outline": ["章节1", "章节2"],
        })

        assert mock_dependencies["kg"].call_count == len(result["sections"])

    @pytest.mark.asyncio
    async def test_doc_search_called(self, mock_dependencies):
        """Project-scoped document search is called for each section."""
        result = await run_autoplan({
            "topic": "测试",
            "outline": ["章节1"],
            "project_id": "P-001",
            "quality_strict": False,
        })

        assert mock_dependencies["docs"].call_count >= len(result["sections"])
        assert all(
            call.kwargs.get("project_id") == "P-001"
            for call in mock_dependencies["docs"].call_args_list
        )

    @pytest.mark.asyncio
    async def test_doc_search_is_not_global_without_project_scope(self, mock_dependencies):
        """Missing project scope must not search another project's documents."""
        await run_autoplan(
            {"topic": "测试", "outline": ["章节1"], "quality_strict": False}
        )

        mock_dependencies["docs"].assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_images_creates_charts(self, mock_dependencies):
        """When generate_images is True, BOQ charts are generated."""
        mock_dependencies["boq"].return_value = {"stats": {"total": 100}}
        mock_dependencies["chart"].return_value = [{"type": "chart", "data": "..."}]

        result = await run_autoplan({
            "outline": [],
            "generate_images": True,
        })

        mock_dependencies["chart"].assert_called_once()
        assert len(result["media"]) >= 1
        assert any(isinstance(m, dict) and m.get("type") == "chart" for m in (result.get("media") or []))

    @pytest.mark.asyncio
    async def test_generate_images_false_skips_charts(self, mock_dependencies):
        """When generate_images is False, BOQ charts are skipped."""
        mock_dependencies["boq"].return_value = {"stats": {"total": 100}}

        result = await run_autoplan({
            "outline": [],
            "generate_images": False,
        })

        mock_dependencies["chart"].assert_not_called()
        assert result["media"] == []

    @pytest.mark.asyncio
    async def test_quality_checks_applied(self, mock_dependencies):
        """Quality checks are run on sections."""
        mock_dependencies["quality"].return_value = {
            "score": 85,
            "issues": ["issue1"],
            "remediation": []
        }

        result = await run_autoplan({
            "outline": ["章节1"],
            # This test validates quality-result plumbing, not the production
            # delivery threshold enforced by the independent content review.
            "quality_strict": False,
        })

        assert result["quality_checks"]["score"] == 85

    @pytest.mark.asyncio
    async def test_auto_remediate_template_mode(self, mock_dependencies):
        """Template remediation is applied when auto_remediate is True."""
        mock_dependencies["quality"].return_value = {
            "score": 70,
            "remediation": [{"title": "章节1", "type": "missing", "suggestion": "add X"}]
        }

        await run_autoplan({
            "outline": ["章节1"],
            "auto_remediate": True,
            "remediate_mode": "template",
            "quality_strict": False,
        })

        mock_dependencies["remediate"].assert_called()

    @pytest.mark.asyncio
    async def test_auto_remediate_disabled(self, mock_dependencies):
        """Remediation is skipped when auto_remediate is False."""
        mock_dependencies["quality"].return_value = {
            "score": 70,
            "remediation": [{"title": "章节1", "type": "missing", "suggestion": "add X"}]
        }

        await run_autoplan({
            "outline": ["章节1"],
            "auto_remediate": False,
            "quality_strict": False,
        })

        mock_dependencies["remediate"].assert_not_called()

    @pytest.mark.asyncio
    async def test_chapter_pages_in_context(self, mock_dependencies):
        """Chapter pages are added to requirements context."""
        await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": 10},
        })

        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        assert any("目标页数" in str(r) for r in ctx.get("requirements", []))

    @pytest.mark.asyncio
    async def test_chapter_pages_dict_target_in_context(self, mock_dependencies):
        """Chapter pages support dict target format."""
        await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": {"pages": 8}},
        })

        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        assert ctx.get("chapter_target_pages") == 8
        assert any("目标页数" in str(r) for r in ctx.get("requirements", []))

    @pytest.mark.asyncio
    async def test_page_target_enrichment_forbids_mechanical_padding(self, mock_dependencies):
        """The legacy flag now means technical enrichment, never blank-page padding."""
        result = await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": 2},
            "style": {"enforce_chapter_pages": True},
            "dry_run": True,
        })

        ctx = _find_ctx_by_title(mock_dependencies["writer"], "第一章")
        requirements = [str(row) for row in ctx.get("requirements", [])]
        assert result["style"]["enforce_chapter_pages"] is True
        assert result["page_target_enrichment"]["policy"] == "technical_content_only_no_page_padding"
        assert any("禁止空白页" in row for row in requirements)
        stage = next(
            row for row in result["pipeline_stages"] if row.get("stage") == "page_target_enrichment"
        )
        assert stage["mechanical_padding_applied"] is False

    @pytest.mark.asyncio
    async def test_page_target_enrichment_accepts_only_material_content_gain(self, mock_dependencies):
        """A short chapter is replaced only when the model returns materially richer content."""
        mock_dependencies["writer"].write = AsyncMock(
            return_value={"title": "第一章", "content": "原有技术内容。"}
        )
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value={"text": "施工工序与检验验收闭环。" * 80}
        )
        mock_dependencies["llm_cls"].return_value = mock_llm

        result = await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": 2},
            "style": {"enforce_chapter_pages": True},
            "strict_tender_outline": True,
            "provider": "openai",
            "model": "test-model",
            "generate_images": False,
            "quality_strict": False,
            "auto_remediate": False,
        })

        assert result["page_target_enrichment"]["candidates"] == ["第一章"]
        assert len(result["page_target_enrichment"]["enhanced"]) == 1
        assert result["sections"][0]["page_target_enriched"] is True
        prompt = mock_llm.complete.await_args_list[0].args[0]
        assert "严禁用空白页" in prompt
        assert "质量优先于页数" in prompt

    @pytest.mark.asyncio
    async def test_chapter_requirements_in_context(self, mock_dependencies):
        """Chapter-specific requirements are merged into context."""
        await run_autoplan({
            "outline": ["第一章"],
            "requirements": ["全局要求A"],
            "chapter_requirements": {"第一章": ["章节要求1", "章节要求2"]},
            "quality_strict": False,
        })

        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        reqs = ctx.get("requirements", [])
        assert "全局要求A" in reqs
        assert "章节要求1" in reqs
        assert "章节要求2" in reqs

    @pytest.mark.asyncio
    async def test_style_passed_through(self, mock_dependencies):
        """Style configuration is normalized and merged with defaults."""
        result = await run_autoplan({
            "style": {"font": "宋体", "size": 12},
        })

        assert isinstance(result["style"], dict)
        assert result["style"].get("body_font") == "宋体"
        assert float(result["style"].get("line_spacing_pt") or 0) == 22.0
        assert isinstance(result["style"].get("margins_cm"), dict)
        assert result["style"].get("margins_cm", {}).get("top") == 2.5
        assert result.get("style_source") in {"default_or_user", "tender_override"}

    @pytest.mark.asyncio
    async def test_variant_id_passed_through(self, mock_dependencies):
        """Variant ID is passed through to result."""
        result = await run_autoplan({
            "variant_id": "v123",
        })

        assert result["variant_id"] == "v123"

    @pytest.mark.asyncio
    async def test_chapter_requirements_passed_through(self, mock_dependencies):
        """Chapter requirements are passed through to result."""
        result = await run_autoplan({
            "chapter_requirements": {"第一章": ["要求A"]},
            "quality_strict": False,
        })
        assert result["chapter_requirements"] == {"第一章": ["要求A"]}

    @pytest.mark.asyncio
    async def test_compare_config_defaults(self, mock_dependencies):
        """Compare configuration has correct defaults."""
        result = await run_autoplan({})

        assert result["compare"]["mode"] == "full"
        assert result["compare"]["max_chars"] == 800

    @pytest.mark.asyncio
    async def test_compare_config_custom(self, mock_dependencies):
        """Compare configuration can be customized."""
        result = await run_autoplan({
            "compare_mode": "summary",
            "compare_max_chars": "500",
            "compare_titles": ["第一章"],
        })

        assert result["compare"]["mode"] == "summary"
        assert result["compare"]["max_chars"] == 500
        assert result["compare"]["titles"] == ["第一章"]

    @pytest.mark.asyncio
    async def test_evidence_tracking(self, mock_dependencies):
        """Evidence tracking reports loaded data."""
        mock_dependencies["tender"].return_value = {"items": []}
        mock_dependencies["boq"].return_value = {"stats": {}}

        result = await run_autoplan({})

        assert result["evidence"]["tender_loaded"] is True
        assert result["evidence"]["boq_loaded"] is True

    @pytest.mark.asyncio
    async def test_evidence_tracking_empty(self, mock_dependencies):
        """Evidence tracking reports when data is empty."""
        mock_dependencies["tender"].return_value = None
        mock_dependencies["boq"].return_value = None

        result = await run_autoplan({})

        assert result["evidence"]["tender_loaded"] is False
        assert result["evidence"]["boq_loaded"] is False

    @pytest.mark.asyncio
    async def test_section_error_handling(self, mock_dependencies):
        """Section generation errors are handled gracefully."""
        mock_dependencies["writer"].write = AsyncMock(
            return_value={"title": "test", "content": "content", "error": "timeout"}
        )

        result = await run_autoplan({
            "outline": ["章节1"],
        })

        # Should still return sections even when writer reports errors.
        assert len(result["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_tender_weights_in_context(self, mock_dependencies):
        """Tender weights and penalties are passed to section context."""
        mock_dependencies["tender"].return_value = {
            "items": [
                {"dimension": "技术", "keywords": ["kw1"], "weight": 40},
                {"dimension": "扣分项", "keywords": ["p1"], "weight": -10},
            ]
        }

        await run_autoplan({
            "outline": ["章节1"],
            # This test verifies context plumbing, not the production
            # requirement-evidence delivery gate.
            "requirement_evidence_hard_gate": False,
            "quality_strict": False,
        })

        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        assert len(ctx.get("weights", [])) == 1
        assert len(ctx.get("penalties", [])) == 1

    @pytest.mark.asyncio
    async def test_requirements_passed_to_context(self, mock_dependencies):
        """Custom requirements are passed to section context."""
        await run_autoplan({
            "outline": ["章节1"],
            "requirements": ["要求1", "要求2"],
        })

        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        assert "要求1" in ctx.get("requirements", [])
        assert "要求2" in ctx.get("requirements", [])

    @pytest.mark.asyncio
    async def test_new_pipeline_outputs_present(self, mock_dependencies):
        """Enterprise profile / WBS-CPM / contract / score mapping receipts are returned."""
        result = await run_autoplan({
            "outline": ["工程概况"],
        })
        assert isinstance(result.get("enterprise_profile"), dict)
        assert isinstance(result.get("boq_wbs_cpm"), dict)
        assert isinstance(result.get("missing_parameters"), dict)
        assert isinstance(result.get("agent_contract"), dict)
        assert isinstance(result.get("agent_contract_checks"), dict)
        assert isinstance(result.get("score_mapping"), dict)
        assert isinstance(result.get("pipeline_stages"), list)

    @pytest.mark.asyncio
    async def test_missing_param_fallback_injected_into_requirements(self, mock_dependencies):
        """Missing-parameter fallback guidance should be injected into section requirements."""
        await run_autoplan({
            "outline": ["工程概况"],
            "requirements": [],
        })
        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        reqs = [str(x) for x in (ctx.get("requirements") or [])]
        assert any("参数缺失自动补位" in x for x in reqs)

    @pytest.mark.asyncio
    async def test_contract_chapter_id_attached(self, mock_dependencies):
        """Each section should carry contract chapter id for downstream audit."""
        result = await run_autoplan({
            "outline": ["工程概况"],
        })
        assert isinstance(result.get("sections"), list) and result["sections"]
        assert "contract_chapter_id" in result["sections"][0]

    @pytest.mark.asyncio
    async def test_progress_callback_reports_chapter_lifecycle(self, mock_dependencies):
        events = []
        result = await run_autoplan(
            {
                "outline": ["工程概况", "施工部署"],
                "_progress_callback": events.append,
            }
        )

        expected_chapters = len(result.get("sections") or [])
        names = [event.get("event") for event in events]
        assert "project_facts_ready" in names
        assert names.index("project_facts_ready") < names.index("chapters_ready")
        assert names.count("chapter_started") == expected_chapters
        assert names.count("chapter_completed") == expected_chapters
        assert names[-1] == "draft_complete"
        assert events[-1]["chapters_done"] == expected_chapters

    @pytest.mark.asyncio
    async def test_model_preflight_always_closes_provider_client(self, mock_dependencies):
        clients = []

        def _client_factory(*_args, **_kwargs):
            client = MagicMock()
            client.preflight = AsyncMock(
                return_value={
                    "ok": True,
                    "provider": "openai",
                    "model": "test-model",
                    "attempts": 1,
                    "error": None,
                    "error_info": None,
                }
            )
            clients.append(client)
            return client

        mock_dependencies["llm_cls"].side_effect = _client_factory

        await run_autoplan(
            {
                "outline": ["工程概况"],
                "provider": "openai",
                "model": "test-model",
                "api_key": "test-key",
                "model_preflight": True,
                "quality_strict": False,
                "requirement_evidence_hard_gate": False,
            }
        )

        assert clients
        assert clients[0].preflight.await_count == 1
        clients[0].close.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_requirement_evidence_preflight_blocks_before_any_model_call(
        self, mock_dependencies
    ):
        events = []
        tender = {
            "items": [
                {
                    "dimension": "扣分项",
                    "keywords": ["质量验收闭环"],
                    "source_spans": [
                        {
                            "file_name": "招标文件.pdf",
                            "page": 1,
                            "start": None,
                            "end": None,
                            "snippet": "",
                        }
                    ],
                }
            ]
        }

        with pytest.raises(ValueError, match="证据生成前准入失败"):
            await run_autoplan(
                {
                    "outline": ["质量管理"],
                    "strict_tender_outline": True,
                    "tender_matrix": tender,
                    "provider": "openai",
                    "model": "test-model",
                    "model_preflight": True,
                    "quality_strict": True,
                    "_progress_callback": events.append,
                }
            )

        names = [event.get("event") for event in events]
        assert "requirement_evidence_preflight" in names
        assert events[names.index("requirement_evidence_preflight")]["ok"] is False
        assert "model_preflight_started" not in names
        assert "provider_attempt_started" not in names
        assert mock_dependencies["llm_cls"].call_count == 0
        assert mock_dependencies["writer"].write.await_count == 0

    @pytest.mark.asyncio
    async def test_evidence_failure_retries_only_failed_chapter_before_checkpoint(
        self, mock_dependencies
    ):
        events = []
        calls = {"质量管理": 0, "安全管理": 0}
        saved_titles = []
        tender = {
            "items": [],
            "chapter_requirements": {
                "质量管理": [
                    {
                        "requirement": "落实质量验收闭环",
                        "source_spans": [
                            {
                                "file_name": "招标文件.pdf",
                                "page": 2,
                                "start": 20,
                                "end": 28,
                                "snippet": "质量验收闭环",
                            }
                        ],
                    }
                ],
                "安全管理": [
                    {
                        "requirement": "落实安全检查闭环",
                        "source_spans": [
                            {
                                "file_name": "招标文件.pdf",
                                "page": 4,
                                "start": 40,
                                "end": 48,
                                "snippet": "安全检查闭环",
                            }
                        ],
                    }
                ],
            },
        }

        async def _write(title, ctx):
            calls[title] += 1
            row = ctx["requirement_evidence_rows"][0]
            requirement_id = row["requirement_id"]
            locator = row["source_evidence"][0]["traceable_locator"]
            if title == "质量管理" and calls[title] == 1:
                content = (
                    f"落实要求。【要求:{requirement_id}】"
                    "【证据:无关资料.pdf#p1_deadbeef@9】"
                )
            else:
                content = (
                    f"落实要求。【要求:{requirement_id}】"
                    f"【证据:{locator}】"
                )
            return {"title": title, "content": content}

        mock_dependencies["writer"].write.side_effect = _write

        def _save(**kwargs):
            saved_titles.append(kwargs["chapter_title"])
            return {
                "saved_chapter_count": len(saved_titles),
                "saved_chapter_indexes": list(range(len(saved_titles))),
                "status": "running",
            }

        with patch(
            "backend.zhifei_autoplan.orchestrator.load_section_checkpoint",
            return_value=None,
        ), patch(
            "backend.zhifei_autoplan.orchestrator.save_section_checkpoint",
            side_effect=_save,
        ), patch(
            "backend.zhifei_autoplan.orchestrator.finalize_generation_checkpoint",
            return_value={
                "saved_chapter_count": 2,
                "saved_chapter_indexes": [0, 1],
                "status": "draft_complete",
            },
        ):
            result = await run_autoplan(
                {
                    "outline": ["质量管理", "安全管理"],
                    "strict_tender_outline": True,
                    "tender_matrix": tender,
                    "provider_chain": [
                        {
                            "slot": "main",
                            "provider": "provider_a",
                            "model": "model_a",
                            "api_key": "a",
                        },
                        {
                            "slot": "fallback_1",
                            "provider": "provider_b",
                            "model": "model_b",
                            "api_key": "b",
                        },
                    ],
                    "quality_strict": True,
                    "auto_remediate": False,
                    "generate_images": False,
                    "dry_run": False,
                    "_checkpoint_namespace": "evidence-retry-job",
                    "_progress_callback": events.append,
                }
            )

        assert calls == {"质量管理": 2, "安全管理": 1}
        assert sorted(saved_titles) == ["安全管理", "质量管理"]
        quality_events = [
            event
            for event in events
            if event.get("chapter_title") == "质量管理"
        ]
        quality_names = [event.get("event") for event in quality_events]
        assert quality_names.index("chapter_evidence_gate_failed") < quality_names.index(
            "chapter_evidence_gate_passed"
        )
        assert quality_names.index("chapter_evidence_gate_passed") < quality_names.index(
            "chapter_checkpoint_saved"
        )
        assert all(
            section["requirement_evidence_gate"]["ok"]
            for section in result["sections"]
        )

    @pytest.mark.asyncio
    async def test_invalid_checkpoint_is_rejected_and_only_chapter_is_regenerated(
        self, mock_dependencies
    ):
        events = []
        tender = {
            "items": [],
            "chapter_requirements": {
                "质量管理": [
                    {
                        "requirement": "落实质量验收闭环",
                        "source_spans": [
                            {
                                "file_name": "招标文件.pdf",
                                "page": 2,
                                "start": 20,
                                "end": 28,
                                "snippet": "质量验收闭环",
                            }
                        ],
                    }
                ]
            },
        }

        async def _write(title, ctx):
            row = ctx["requirement_evidence_rows"][0]
            return {
                "title": title,
                "content": (
                    f"落实要求。【要求:{row['requirement_id']}】"
                    f"【证据:{row['source_evidence'][0]['traceable_locator']}】"
                ),
            }

        mock_dependencies["writer"].write.side_effect = _write
        saved = []

        with patch(
            "backend.zhifei_autoplan.orchestrator.load_section_checkpoint",
            return_value={"title": "质量管理", "content": "旧检查点正文，无要求标记"},
        ), patch(
            "backend.zhifei_autoplan.orchestrator.save_section_checkpoint",
            side_effect=lambda **kwargs: saved.append(kwargs["chapter_title"])
            or {"saved_chapter_count": 1, "status": "running"},
        ), patch(
            "backend.zhifei_autoplan.orchestrator.finalize_generation_checkpoint",
            return_value={"saved_chapter_count": 1, "status": "draft_complete"},
        ):
            await run_autoplan(
                {
                    "outline": ["质量管理"],
                    "strict_tender_outline": True,
                    "tender_matrix": tender,
                    "provider": "provider_a",
                    "model": "model_a",
                    "quality_strict": True,
                    "auto_remediate": False,
                    "generate_images": False,
                    "dry_run": False,
                    "_checkpoint_namespace": "legacy-evidence-job",
                    "_progress_callback": events.append,
                }
            )

        names = [event.get("event") for event in events]
        assert "chapter_checkpoint_rejected" in names
        assert "chapter_resumed" not in names
        assert mock_dependencies["writer"].write.await_count == 1
        assert saved == ["质量管理"]


# =============================================================================
# Tests for _pick_agent_role (internal function via run_autoplan)
# =============================================================================

class TestAgentRoleSelection:
    """Tests for agent role selection logic."""

    @pytest.fixture
    def mock_deps(self):
        """Set up mocks for testing agent roles."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer

            mock_quality.return_value = _passing_quality_result()

            yield {"writer": mock_writer}

    @pytest.mark.asyncio
    async def test_quality_role_selection(self, mock_deps):
        """Quality-related titles get 质量负责人 role."""
        await run_autoplan({
            "outline": ["质量管理计划"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "质量管理计划")
        assert ctx.get("agent_role") == "质量负责人"

    @pytest.mark.asyncio
    async def test_safety_role_selection(self, mock_deps):
        """Safety-related titles get 安全负责人 role."""
        await run_autoplan({
            "outline": ["安全施工措施"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "安全施工措施")
        assert ctx.get("agent_role") == "安全负责人"

    @pytest.mark.asyncio
    async def test_progress_role_selection(self, mock_deps):
        """Progress-related titles get 进度负责人 role."""
        await run_autoplan({
            "outline": ["进度计划"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "进度计划")
        assert ctx.get("agent_role") == "进度负责人"

    @pytest.mark.asyncio
    async def test_environment_role_selection(self, mock_deps):
        """Environment-related titles get 环保负责人 role."""
        await run_autoplan({
            "outline": ["环保措施"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "环保措施")
        assert ctx.get("agent_role") == "环保负责人"

    @pytest.mark.asyncio
    async def test_resource_role_selection(self, mock_deps):
        """Resource-related titles get 资源统筹负责人 role."""
        await run_autoplan({
            "outline": ["设备配置方案"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "设备配置方案")
        assert ctx.get("agent_role") == "资源统筹负责人"

    @pytest.mark.asyncio
    async def test_default_role_selection(self, mock_deps):
        """Unmatched titles get 技术负责人 role."""
        await run_autoplan({
            "outline": ["工程概况"],
        })

        ctx = _find_ctx_by_title(mock_deps["writer"], "工程概况")
        assert ctx.get("agent_role") == "技术负责人"


# =============================================================================
# Integration-style tests
# =============================================================================

class TestOrchestratorIntegration:
    """Integration tests for orchestrator workflow."""

    @pytest.fixture
    def full_mocks(self):
        """Set up comprehensive mocks."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart") as mock_chart, \
             patch("backend.zhifei_autoplan.orchestrator.generate_ingested_previews") as mock_previews, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_remediate:

            # Realistic tender data
            mock_tender.return_value = {
                "items": [
                    {"dimension": "技术方案", "keywords": ["施工工艺", "技术措施"], "weight": 40},
                    {"dimension": "质量保证", "keywords": ["质量控制", "检验标准"], "weight": 30},
                    {"dimension": "扣分项", "keywords": ["安全事故", "质量问题"], "weight": -20},
                ]
            }

            # Realistic BOQ data
            mock_boq.return_value = {
                "stats": {"total_cost": 1000000, "items_count": 50},
                "items": []
            }

            # KG results
            mock_kg.return_value = {
                "results": [
                    {"title": "施工规范", "text": "混凝土施工应符合GB50204"},
                    {"title": "质量标准", "text": "钢筋保护层厚度偏差不超过5mm"},
                ]
            }

            # Document search results
            mock_docs.return_value = [
                {"filename": "招标文件.pdf", "snippet": "投标人应具备相关资质"},
            ]

            # Section writer
            mock_writer = MagicMock()
            async def write_section(title, ctx):
                return {
                    "title": title,
                    "content": f"{title}的详细内容，参考【证据:施工规范】",
                    "agent_role": ctx.get("agent_role"),
                }
            mock_writer.write = AsyncMock(side_effect=write_section)
            mock_writer_cls.return_value = mock_writer

            # Chart generation
            mock_chart.return_value = [{"type": "bar", "title": "工程量分布"}]
            mock_previews.return_value = []

            # Quality checks
            mock_quality.return_value = {
                **_passing_quality_result(),
                "score": 92,
                "issues": [],
            }

            yield {
                "tender": mock_tender,
                "boq": mock_boq,
                "kg": mock_kg,
                "docs": mock_docs,
                "llm_cls": mock_llm_cls,
                "writer_cls": mock_writer_cls,
                "writer": mock_writer,
                "chart": mock_chart,
                "previews": mock_previews,
                "quality": mock_quality,
                "remediate": mock_remediate,
            }

    @pytest.mark.asyncio
    async def test_full_workflow(self, full_mocks):
        """Test complete autoplan workflow."""
        result = await run_autoplan({
            "topic": "合肥市排水工程",
            "outline": ["工程概况", "施工部署", "质量管理"],
            "requirements": ["符合当地规范", "工期120天"],
            "style": {"font": "宋体"},
            "chapter_pages": {"工程概况": 5, "施工部署": 15, "质量管理": 10},
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": True,
            "generate_images": True,
            # The mocked writer is intentionally not evidence-complete; the
            # requirement-evidence gate has dedicated tests.
            "requirement_evidence_hard_gate": False,
            "quality_strict": False,
        })

        # Verify structure
        assert result["topic"] == "合肥市排水工程"
        assert len(result["sections"]) >= 3
        # Dry-run is a zero-provider preview: it must not call image models even
        # if the request left generate_images enabled.
        assert result["media"] == []
        assert result["quality_checks"]["score"] == 92
        assert result["evidence"]["tender_loaded"] is True
        assert result["evidence"]["boq_loaded"] is True

    @pytest.mark.asyncio
    async def test_workflow_with_remediation(self, full_mocks):
        """Test workflow with quality issues and remediation."""
        full_mocks["quality"].return_value = {
            "score": 75,
            "issues": ["missing_detail"],
            "remediation": [
                {"title": "质量管理", "type": "missing", "suggestion": "补充检验频次"}
            ]
        }

        result = await run_autoplan({
            "topic": "测试项目",
            "outline": ["质量管理"],
            "auto_remediate": True,
            "remediate_mode": "template",
            "requirement_evidence_hard_gate": False,
            "quality_strict": False,
        })

        # Remediation should be applied
        full_mocks["remediate"].assert_called()
        # Quality checks run twice (before and after remediation)
        assert full_mocks["quality"].call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_section_generation(self, full_mocks):
        """Test that sections are generated concurrently."""
        started = []
        release = asyncio.Event()

        async def timed_write(title, ctx):
            started.append(title)
            if len(started) >= 3:
                release.set()
            # A sequential implementation cannot reach the third writer while
            # the first one is waiting here.  This proves overlap without a
            # brittle wall-clock spread assertion on a busy CI host.
            await asyncio.wait_for(release.wait(), timeout=1.0)
            return {"title": title, "content": "content", "agent_role": ctx.get("agent_role")}

        full_mocks["writer"].write = AsyncMock(side_effect=timed_write)

        result = await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "strict_tender_outline": True,
            "agent_parallelism": 3,
            "requirement_evidence_hard_gate": False,
            "quality_strict": False,
        })

        assert len(started) == len(result["sections"])
        assert len(started) >= 3


# =============================================================================
# Tests for _pick_agent_role config file loading (lines 57-71)
# =============================================================================

class TestAgentRoleConfigLoading:
    """Tests for agent role config file loading."""

    @pytest.fixture
    def mock_deps_for_role(self):
        """Set up mocks for testing agent role config."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer

            mock_quality.return_value = _passing_quality_result()

            yield {"writer": mock_writer}

    @pytest.mark.asyncio
    async def test_config_file_custom_role_match(self, mock_deps_for_role, tmp_path, monkeypatch):
        """Custom config file rules override default roles."""
        import json
        from pathlib import Path

        # Create temp config file
        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_roles.json"
        config_file.write_text(json.dumps({
            "default": "项目负责人",
            "rules": [
                {"match": ["特殊"], "role": "特殊负责人"},
                {"match": ["自定义"], "role": "自定义负责人"}
            ]
        }))

        # Monkeypatch Path to find our temp config
        original_exists = Path.exists
        original_read_text = Path.read_text

        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return True
            return original_exists(self)

        def patched_read_text(self, encoding=None):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return config_file.read_text()
            return original_read_text(self, encoding=encoding)

        monkeypatch.setattr(Path, "exists", patched_exists)
        monkeypatch.setattr(Path, "read_text", patched_read_text)

        await run_autoplan({
            "outline": ["特殊章节"],
        })

        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "特殊章节")
        assert ctx.get("agent_role") == "特殊负责人"

    @pytest.mark.asyncio
    async def test_config_file_default_fallback(self, mock_deps_for_role, tmp_path, monkeypatch):
        """Config file default role is used when no rules match."""
        import json
        from pathlib import Path

        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_roles.json"
        config_file.write_text(json.dumps({
            "default": "默认配置负责人",
            "rules": [
                {"match": ["不匹配关键词"], "role": "其他负责人"}
            ]
        }))

        original_exists = Path.exists
        original_read_text = Path.read_text

        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return True
            return original_exists(self)

        def patched_read_text(self, encoding=None):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return config_file.read_text()
            return original_read_text(self, encoding=encoding)

        monkeypatch.setattr(Path, "exists", patched_exists)
        monkeypatch.setattr(Path, "read_text", patched_read_text)

        await run_autoplan({
            "outline": ["普通章节"],
        })

        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "普通章节")
        assert ctx.get("agent_role") == "默认配置负责人"

    @pytest.mark.asyncio
    async def test_config_file_exception_fallback(self, mock_deps_for_role, monkeypatch):
        """When config file causes exception, fallback to default rules."""
        from pathlib import Path

        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                raise OSError("Permission denied")
            return False

        monkeypatch.setattr(Path, "exists", patched_exists)

        await run_autoplan({
            "outline": ["质量检验章节"],
        })

        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "质量检验章节")
        # Should fallback to default rule matching "质量"
        assert ctx.get("agent_role") == "质量负责人"


# =============================================================================
# Tests for section build failure (line 137)
# =============================================================================

class TestSectionBuildFailure:
    """Tests for section build complete failure scenarios."""

    @pytest.fixture
    def mock_deps_fail(self):
        """Set up mocks for failure testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            mock_quality.return_value = _passing_quality_result()

            yield {
                "writer_cls": mock_writer_cls,
            }

    @pytest.mark.asyncio
    async def test_all_retries_fail_with_error(self, mock_deps_fail):
        """When all retries return errors, returns last result with agent_role."""
        mock_writer = MagicMock()
        # All attempts return error
        mock_writer.write = AsyncMock(return_value={"title": "test", "content": "error", "error": "timeout"})
        mock_deps_fail["writer_cls"].return_value = mock_writer

        result = await run_autoplan({
            "outline": ["章节1"],
            "providers": ["p1", "p2"],
            "model_map": {"p1": "m1", "p2": "m2"},
        })

        # Should return the last attempt's result with agent_role added
        assert len(result["sections"]) >= 1
        assert any(s.get("agent_role") == "技术负责人" for s in result["sections"])
        assert any("error" in s for s in result["sections"])

    @pytest.mark.asyncio
    async def test_section_returns_none(self, mock_deps_fail):
        """When writer returns None, fallback message is generated."""
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(return_value=None)
        mock_deps_fail["writer_cls"].return_value = mock_writer

        result = await run_autoplan({
            "outline": ["章节1"],
        })

        # Should return fallback section
        assert len(result["sections"]) >= 1
        assert any(s.get("content") == "章节生成失败" for s in result["sections"])


# =============================================================================
# Tests for LLM remediation (lines 152-196)
# =============================================================================

class TestLLMRemediation:
    """Tests for LLM-based remediation workflow."""

    @pytest.fixture
    def mock_deps_llm(self):
        """Set up mocks for LLM remediation testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart"), \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_apply:

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "原始内容"})
            mock_writer_cls.return_value = mock_writer

            # LLM client mock
            mock_llm = MagicMock()
            mock_llm.complete = AsyncMock(return_value={"text": "修复后的内容"})
            mock_llm_cls.return_value = mock_llm

            # First quality check has issues, second is clean
            mock_quality.side_effect = [
                {
                    "score": 70,
                    "remediation": [
                        {"title": "章节1", "type": "missing", "suggestion": "补充细节"}
                    ]
                },
                {"score": 95, "remediation": []}
            ]

            yield {
                "llm_cls": mock_llm_cls,
                "llm": mock_llm,
                "quality": mock_quality,
                "apply": mock_apply,
                "writer": mock_writer,
            }

    @pytest.mark.asyncio
    async def test_llm_remediation_applied(self, mock_deps_llm):
        """LLM remediation mode calls LLM to fix sections."""
        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
            "quality_strict": False,
        })

        # LLM complete should be called for remediation
        assert mock_deps_llm["llm"].complete.called
        # apply_remediation (template mode) should NOT be called
        mock_deps_llm["apply"].assert_not_called()
        # Quality checks run twice
        assert mock_deps_llm["quality"].call_count == 2

    @pytest.mark.asyncio
    async def test_llm_remediation_skipped_dry_run(self, mock_deps_llm):
        """LLM remediation skipped in dry run mode."""
        mock_deps_llm["quality"].side_effect = [
            {
                "score": 70,
                "remediation": [{"title": "章节1", "type": "missing", "suggestion": "fix"}]
            },
            {"score": 70, "remediation": []}
        ]

        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": True,
            "quality_strict": False,
        })

        # In dry_run, LLM is not called for remediation
        # LLMClient is called for section generation in dry_run=False
        # But since we have both provider and dry_run=True, LLM should not be instantiated for remediation

    @pytest.mark.asyncio
    async def test_llm_remediation_no_issues(self, mock_deps_llm):
        """No LLM calls when quality check has no remediation items."""
        mock_deps_llm["quality"].side_effect = [
            {"score": 100, "remediation": []},
            {"score": 100, "remediation": []}
        ]

        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
            "quality_strict": False,
        })

        # No remediation needed, LLM complete should not be called for remediation
        # (may be called for other purposes, but not for remediation of empty list)

    @pytest.mark.asyncio
    async def test_llm_remediation_updates_content(self, mock_deps_llm):
        """LLM remediation updates section content."""
        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
            "quality_strict": False,
        })

        # Check that section was updated
        section = result["sections"][0]
        assert section.get("auto_remediated") == "llm"
        assert section.get("original_content") in {"原始内容", "修复后的内容"}
        assert section.get("content", "").startswith("修复后的内容")
        assert "劳保用品配置矩阵" in section.get("content", "")
        assert "关键工序控制点表" in section.get("content", "")

    @pytest.mark.asyncio
    async def test_llm_remediation_no_provider(self, mock_deps_llm):
        """LLM remediation skipped when no provider specified."""
        mock_deps_llm["quality"].side_effect = [
            {"score": 70, "remediation": [{"title": "章节1", "type": "missing", "suggestion": "fix"}]},
            {"score": 70, "remediation": []}
        ]

        await run_autoplan({
            "outline": ["章节1"],
            # No provider/model specified
            "auto_remediate": True,
            "remediate_mode": "llm",
            "quality_strict": False,
        })

        # Without provider, _remediate_with_llm returns early

    @pytest.mark.asyncio
    async def test_llm_remediation_bad_response(self, mock_deps_llm):
        """LLM remediation handles bad response gracefully."""
        mock_deps_llm["llm"].complete = AsyncMock(return_value={"error": "timeout"})

        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
            "quality_strict": False,
        })

        # Content should not be updated on bad response
        section = result["sections"][0]
        # auto_remediated flag should not be set since response was bad


# =============================================================================
# Tests for _pick_provider with providers list (line 51)
# =============================================================================

class TestPickProviderWithList:
    """Tests for _pick_provider when providers list is used."""

    @pytest.fixture
    def mock_deps_prov(self):
        """Set up mocks for provider testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):

            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer

            mock_quality.return_value = _passing_quality_result()

            # Track LLMClient instantiations
            llm_calls = []
            def track_llm(**kwargs):
                llm_calls.append(kwargs)
                return MagicMock()
            mock_llm_cls.side_effect = track_llm

            yield {
                "llm_cls": mock_llm_cls,
                "llm_calls": llm_calls,
            }

    @pytest.mark.asyncio
    async def test_execution_budget_exhaustion_is_not_reported_as_provider_failure(
        self,
        mock_deps_prov,
    ):
        class _BudgetWriter:
            def __init__(self, llm):
                self.llm = llm

            async def write(self, title, ctx):
                raise ExecutionBudgetExceededError(
                    dimension="model_attempts",
                    attempted=5,
                    limit=4,
                )

        with patch("backend.zhifei_autoplan.orchestrator.SectionWriter", _BudgetWriter):
            with pytest.raises(RuntimeError) as exc_info:
                await run_autoplan(
                    {
                        "outline": ["章节1"],
                        "provider_chain": [
                            {
                                "slot": "text_draft",
                                "provider": "anthropic",
                                "model": "claude-sonnet-5",
                                "api_key": "test-key",
                            }
                        ],
                        "fail_on_model_exhaustion": True,
                        "quality_strict": False,
                        "auto_remediate": False,
                        "generate_images": False,
                        "dry_run": False,
                    }
                )

        failure = json.loads(str(exc_info.value))
        assert failure["code"] == "EXECUTION_BUDGET_EXCEEDED"
        assert failure["failures"][0]["code"] == "EXECUTION_BUDGET_EXCEEDED"
        assert failure["failures"][0]["failure_kind"] == "execution_control"

    @pytest.mark.asyncio
    async def test_tiered_route_uses_sonnet_for_draft_and_opus_for_critical_review(self, mock_deps_prov):
        calls = mock_deps_prov["llm_calls"]

        def _tracked_llm(**kwargs):
            calls.append(kwargs)
            llm = MagicMock()
            llm.complete = AsyncMock(return_value={"text": "Opus复核后的关键章节"})
            return llm

        class _Writer:
            def __init__(self, llm):
                self.llm = llm

            async def write(self, title, ctx):
                return {"title": title, "content": f"Sonnet起草：{title}"}

        mock_deps_prov["llm_cls"].side_effect = _tracked_llm
        with patch("backend.zhifei_autoplan.orchestrator.SectionWriter", _Writer):
            result = await run_autoplan(
                {
                    "outline": ["施工总体部署", "项目概况"],
                    "provider_chain": [
                        {"slot": "text_draft", "provider": "anthropic", "model": "claude-sonnet-5", "api_key": "a"},
                        {"slot": "text_review", "provider": "anthropic", "model": "claude-opus-5", "api_key": "a"},
                        {"slot": "text_backup", "provider": "openai", "model": "gpt-5.6-sol", "api_key": "o"},
                        {"slot": "text_escalation", "provider": "anthropic", "model": "claude-fable-5", "api_key": "a"},
                    ],
                    "quality_strict": False,
                    "auto_remediate": False,
                    "generate_images": False,
                    "dry_run": False,
                }
            )

        used_models = [call.get("model") for call in calls]
        assert "claude-sonnet-5" in used_models
        assert "claude-opus-5" in used_models
        assert "claude-fable-5" not in used_models
        assert result["model_routing"]["mode"] == "anthropic_tiered"
        assert result["model_routing"]["fable_escalation_enabled"] is False
        reviewed = result["model_routing"]["review_audit"]["reviewed_chapters"]
        assert "施工总体部署" in [row["title"] for row in reviewed]

    @pytest.mark.asyncio
    async def test_providers_list_rotation_with_model_map(self, mock_deps_prov):
        """Providers list rotates with model_map mapping."""
        await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "providers": ["provider_a", "provider_b"],
            "model_map": {"provider_a": "model_a", "provider_b": "model_b"},
            "dry_run": False,
        })

        calls = mock_deps_prov["llm_calls"]
        # Check that providers rotate correctly
        providers_used = [c["provider"] for c in calls]
        models_used = [c["model"] for c in calls]

        # 3 sections with 2 providers should show rotation pattern
        assert "provider_a" in providers_used
        assert "provider_b" in providers_used

    @pytest.mark.asyncio
    async def test_providers_list_fallback_model(self, mock_deps_prov):
        """When model_map doesn't have provider, falls back to default model."""
        await run_autoplan({
            "outline": ["章节1"],
            "providers": ["unknown_provider"],
            "model_map": {},  # Empty model_map
            "model": "fallback_model",  # Default model
            "dry_run": False,
        })

        calls = mock_deps_prov["llm_calls"]
        assert len(calls) >= 1
        # Should use fallback model
        assert calls[0]["model"] == "fallback_model"

    @pytest.mark.asyncio
    async def test_provider_init_failure_falls_through_to_next_provider(self):
        """If first provider init fails, orchestrator should continue with next provider."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value=_passing_quality_result()), \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"), \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls:

            # First provider fails on init, second succeeds.
            created = []
            def _mk(**kwargs):
                created.append(kwargs)
                if kwargs.get("provider") == "provider_a":
                    raise ValueError("init failed")
                return MagicMock()

            mock_llm_cls.side_effect = _mk
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "ok"})
            mock_writer_cls.return_value = mock_writer

            result = await run_autoplan(
                {
                    "outline": ["章节1"],
                    "providers": ["provider_a", "provider_b"],
                    "model_map": {"provider_a": "m1", "provider_b": "m2"},
                    "dry_run": False,
                }
            )

            assert len(result.get("sections") or []) >= 1
            # Ensure fallback provider was attempted after first init failure.
            providers_used = [c.get("provider") for c in created]
            assert "provider_a" in providers_used
            assert "provider_b" in providers_used

    @pytest.mark.asyncio
    async def test_provider_chain_supports_same_provider_with_different_keys(self, mock_deps_prov):
        """provider_chain keeps duplicate providers and rotates by slot (not dedup by provider)."""
        await run_autoplan(
            {
                "outline": ["章节1", "章节2", "章节3"],
                "provider_chain": [
                    {"slot": "main", "provider": "google", "model": "gemini-a", "api_key": "g_key_1"},
                    {"slot": "fallback_1", "provider": "google", "model": "gemini-b", "api_key": "g_key_2"},
                    {"slot": "fallback_2", "provider": "openai", "model": "gpt-x", "api_key": "o_key_1"},
                ],
                "dry_run": False,
            }
        )

        calls = mock_deps_prov["llm_calls"]
        assert len(calls) >= 3
        assert calls[0]["provider"] == "google"
        assert calls[1]["provider"] == "google"
        assert calls[2]["provider"] == "openai"
        assert calls[0]["api_key"] == "g_key_1"
        assert calls[1]["api_key"] == "g_key_2"
        assert calls[2]["api_key"] == "o_key_1"

    @pytest.mark.asyncio
    async def test_provider_chain_accepts_ollama_slot_without_real_ollama(self, mock_deps_prov):
        """provider_chain can carry an Ollama slot to LLMClient without invoking real Ollama or write paths."""
        write_paths_before = _loaded_write_paths()
        await run_autoplan(
            {
                "outline": ["章节1"],
                "provider_chain": [
                    {
                        "slot": "main",
                        "provider": "ollama",
                        "model": "qwen3:0.6b",
                    }
                ],
                "base_url": "http://127.0.0.1:11434",
                "dry_run": False,
            }
        )

        calls = mock_deps_prov["llm_calls"]
        assert len(calls) >= 1
        assert calls[0]["provider"] == "ollama"
        assert calls[0]["model"] == "qwen3:0.6b"
        assert calls[0]["base_url"] == "http://127.0.0.1:11434"
        assert calls[0]["api_key"] is None
        _assert_write_paths_unchanged(write_paths_before)

    @pytest.mark.asyncio
    async def test_provider_chain_same_provider_key_fallback(self):
        """When same provider first key fails, second key in chain should be attempted."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value=_passing_quality_result()), \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"), \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls:

            seen = []

            def _mk(**kwargs):
                seen.append(kwargs)
                if kwargs.get("provider") == "google" and kwargs.get("api_key") == "bad_key":
                    raise ValueError("init failed")
                return MagicMock()

            mock_llm_cls.side_effect = _mk
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "ok"})
            mock_writer_cls.return_value = mock_writer

            result = await run_autoplan(
                {
                    "outline": ["章节1"],
                    "provider_chain": [
                        {"slot": "main", "provider": "google", "model": "gemini-a", "api_key": "bad_key"},
                        {"slot": "fallback_1", "provider": "google", "model": "gemini-b", "api_key": "good_key"},
                    ],
                    "dry_run": False,
                }
            )

            assert len(result.get("sections") or []) >= 1
            keys_used = [c.get("api_key") for c in seen]
            assert "bad_key" in keys_used
            assert "good_key" in keys_used


@pytest.mark.asyncio
async def test_run_autoplan_injects_safe_case_reference_requirements(tmp_path):
    from backend.zhifei_autoplan.case_library_service import case_library_record_id
    from backend.zhifei_autoplan.image_library import image_library_record_id

    audit_path = tmp_path / "ingest.jsonl"
    case_record = {
        "ts": "2026-04-12T10:00:00Z",
        "filename": "房建案例A.txt",
        "project_type": "房建",
        "library_scope": "case_library",
        "saved_as": str(tmp_path / "房建案例A.txt"),
        "library_title": "房建案例A",
        "library_tags": ["医院"],
        "chapter_scope": ["工程概况"],
        "library_summary": "结构清晰",
        "library_style_profile": "短句表达",
        "sha256": "a" * 64,
    }
    image_record = {
        "ts": "2026-04-12T11:00:00Z",
        "filename": "现场平面.png",
        "project_type": "房建",
        "library_scope": "image_library",
        "saved_as": str(tmp_path / "现场平面.png"),
        "library_title": "现场平面",
        "library_tags": ["平面"],
        "chapter_scope": ["工程概况"],
        "library_caption": "现场平面示意",
        "sha256": "b" * 64,
    }
    audit_path.write_text(
        "\n".join([
            json.dumps(case_record, ensure_ascii=False),
            json.dumps(image_record, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )

    with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
         patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
         patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
         patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
         patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
         patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value=_passing_quality_result()), \
         patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(return_value={"title": "工程概况", "content": "正文保持不变"})
        mock_writer_cls.return_value = mock_writer

        result = await run_autoplan(
            {
                "topic": "医院改造项目",
                "outline": ["工程概况"],
                "project_type": "房建",
                "dry_run": True,
                "generate_images": False,
                "auto_remediate": False,
                "reference_library_audit_path": str(audit_path),
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": [case_library_record_id(case_record)],
                },
                "image_library": {
                    "enabled": True,
                    "selected_image_ids": [image_library_record_id(image_record)],
                },
            }
        )

    section = result["sections"][0]
    assert section["content"] == "正文保持不变"
    assert section["case_reference_pack"]["match_reason"] == "selected_case_ids"
    assert section["image_selection_pack"]["match_reason"] == "selected_image_ids"
    assert result["case_reference_pack"]["chapters"][0]["hit_count"] == 1
    assert result["image_selection_pack"]["chapters"][0]["hit_count"] == 1
    ctx = mock_writer.write.call_args.args[1]
    assert ctx["case_reference_pack"]["match_reason"] == "selected_case_ids"
    assert ctx["image_selection_pack"]["match_reason"] == "selected_image_ids"
    requirements_text = "\n".join(ctx["requirements"])
    assert "案例库安全增强（非事实源）" in requirements_text
    assert "结构清晰" in requirements_text
    assert "严禁复制案例中的项目名称" in requirements_text
