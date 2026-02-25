from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.audit_failfast import (
    FailFastAuditError,
    audit_against_index_matrix,
    enforce_fail_fast,
    run_with_fail_fast_retry,
    run_with_fail_fast_retry_async,
)


@pytest.fixture
def sample_index_matrix():
    return {
        "index_matrix": [
            {
                "dimension": "质量",
                "keywords": ["质量", "验收"],
                "score_points": [
                    {
                        "point_id": "Q1",
                        "description": "质量验收响应",
                        "required_keywords": ["质量", "验收"],
                        "match_mode": "all",
                    }
                ],
            },
            {
                "dimension": "安全",
                "keywords": ["安全", "应急"],
                "score_points": [
                    {
                        "point_id": "S1",
                        "description": "安全应急响应",
                        "required_keywords": ["安全", "应急"],
                        "match_mode": "all",
                    }
                ],
            },
        ]
    }


def test_audit_against_index_matrix_returns_boolean_points(sample_index_matrix):
    sections = [{"title": "章节1", "content": "质量验收通过，但风险处置方案缺失。"}]
    result = audit_against_index_matrix(sample_index_matrix, sections)

    assert result["ok"] is False
    assert result["failed_count"] == 1
    assert len(result["checks"]) == 2
    assert any(check["ok"] is False for check in result["checks"])
    assert all("score_points" in check for check in result["checks"])
    assert all(isinstance(check.get("score_points"), list) for check in result["checks"])


def test_audit_against_index_matrix_point_all_mode_requires_all_keywords():
    index_matrix = {
        "index_matrix": [
            {
                "dimension": "安全",
                "score_points": [
                    {
                        "point_id": "S-ALL",
                        "description": "必须包含安全和应急",
                        "required_keywords": ["安全", "应急"],
                        "match_mode": "all",
                    }
                ],
            }
        ]
    }
    result = audit_against_index_matrix(index_matrix, [{"title": "安全", "content": "已落实安全管理措施。"}])
    assert result["ok"] is False
    assert result["failed_count"] == 1
    check = result["checks"][0]
    assert check["score_points"][0]["ok"] is False
    assert "应急" in check["score_points"][0]["missing_keywords"]


def test_enforce_fail_fast_clears_cache_and_logs(tmp_path: Path, sample_index_matrix):
    log_path = tmp_path / "audit.jsonl"
    cache = {"p1": "draft paragraph"}
    sections = [{"title": "章节1", "content": "只有质量，没有风险处置体系。"}]

    with pytest.raises(FailFastAuditError):
        enforce_fail_fast(
            index_matrix=sample_index_matrix,
            sections=sections,
            paragraph_cache=cache,
            agent_name="writer-agent",
            attempt=1,
            max_attempts=3,
            log_path=log_path,
        )

    assert cache == {}
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    record = json.loads(line)
    assert record["agent"] == "writer-agent"
    assert record["event"] == "fail_fast_retry"


def test_run_with_fail_fast_retry_passes_after_retry(tmp_path: Path, sample_index_matrix):
    log_path = tmp_path / "audit.jsonl"
    cache = {}

    def generator(attempt: int, paragraph_cache: dict):
        if attempt == 1:
            paragraph_cache["draft"] = "first"
            return [{"title": "章节", "content": "质量验收已完成。"}]
        return [{"title": "章节", "content": "质量验收和安全应急均已落实。"}]

    sections, audit_result = run_with_fail_fast_retry(
        generator=generator,
        index_matrix=sample_index_matrix,
        paragraph_cache=cache,
        agent_name="writer-agent",
        max_attempts=3,
        log_path=log_path,
    )

    assert audit_result["ok"] is True
    assert "安全应急" in sections[0]["content"]
    assert "__last_failed_dimensions__" not in cache
    assert "__last_failed_points__" not in cache


@pytest.mark.asyncio
async def test_run_with_fail_fast_retry_async(tmp_path: Path, sample_index_matrix):
    log_path = tmp_path / "audit_async.jsonl"
    cache = {}

    async def generator(attempt: int, paragraph_cache: dict):
        if attempt == 1:
            paragraph_cache["draft"] = "bad"
            return [{"title": "章节", "content": "质量验收。"}]
        return [{"title": "章节", "content": "质量验收 + 安全应急。"}]

    sections, result = await run_with_fail_fast_retry_async(
        generator=generator,
        index_matrix=sample_index_matrix,
        paragraph_cache=cache,
        agent_name="writer-agent",
        max_attempts=2,
        log_path=log_path,
    )

    assert result["ok"] is True
    assert sections
