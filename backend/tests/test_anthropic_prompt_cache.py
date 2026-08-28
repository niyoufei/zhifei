from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.zhifei_autoplan.agents.section_writer import SectionWriter
from backend.zhifei_autoplan.claude_usage import claude_usage_stats
from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider


class _CachingMessages:
    """Small deterministic stand-in for Anthropic's server-side prefix cache."""

    def __init__(self) -> None:
        self.cache: set[str] = set()
        self.requests: list[dict[str, Any]] = []

    @staticmethod
    def _cache_keys(request: dict[str, Any]) -> list[str]:
        model = str(request.get("model") or "")
        cumulative: list[dict[str, Any]] = []
        keys: list[str] = []
        for block in request.get("system") or []:
            cumulative.append({key: value for key, value in block.items() if key != "cache_control"})
            if block.get("cache_control") == {"type": "ephemeral"}:
                keys.append(
                    hashlib.sha256(
                        json.dumps([model, cumulative], ensure_ascii=False, sort_keys=True).encode()
                    ).hexdigest()
                )
        for message in request.get("messages") or []:
            cumulative.append({"role": message.get("role")})
            for block in message.get("content") or []:
                cumulative.append({key: value for key, value in block.items() if key != "cache_control"})
                if block.get("cache_control") == {"type": "ephemeral"}:
                    keys.append(
                        hashlib.sha256(
                            json.dumps([model, cumulative], ensure_ascii=False, sort_keys=True).encode()
                        ).hexdigest()
                    )
        if request.get("cache_control") == {"type": "ephemeral"}:
            keys.append(
                hashlib.sha256(
                    json.dumps([model, cumulative], ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest()
            )
        return keys

    def create(self, **kwargs: Any) -> Any:
        request = {key: value for key, value in kwargs.items() if key != "timeout"}
        self.requests.append(request)
        keys = self._cache_keys(request)
        hit = any(key in self.cache for key in reversed(keys))
        self.cache.update(keys)
        usage = SimpleNamespace(
            input_tokens=23,
            output_tokens=7,
            cache_creation_input_tokens=0 if hit else (1200 if keys else 0),
            cache_read_input_tokens=1200 if hit else 0,
        )
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="完成")], usage=usage)


def _provider(messages: _CachingMessages, model: str = "claude-sonnet-4-5") -> AnthropicProvider:
    provider = object.__new__(AnthropicProvider)
    provider.client = SimpleNamespace(messages=messages)
    provider.model = model
    return provider


@pytest.mark.asyncio
async def test_first_request_creates_cache_and_second_changed_chapter_reads_prefix():
    messages = _CachingMessages()
    provider = _provider(messages)

    first = await provider.complete(
        "当前章节：第一章",
        stable_system_prompt="固定规则 + 项目事实库 + 评分规则 + 排版规范",
        shared_context_prompt="已生成章节摘要",
        cache_mode="section",
        project_id="P-001",
        task_type="chapter_generation",
    )
    second = await provider.complete(
        "当前章节：第二章（动态要求已改变）",
        stable_system_prompt="固定规则 + 项目事实库 + 评分规则 + 排版规范",
        shared_context_prompt="已生成章节摘要",
        cache_mode="section",
        project_id="P-001",
        task_type="chapter_generation",
    )

    assert first["cache"]["prewarm_cache_creation_input_tokens"] == 1200
    assert first["cache"]["prewarm_effective"] is True
    assert first["usage"]["cache_creation_input_tokens"] == 0
    assert first["usage"]["cache_read_input_tokens"] == 1200
    assert second["usage"]["cache_creation_input_tokens"] == 0
    assert second["usage"]["cache_read_input_tokens"] == 1200
    assert second["usage"]["cache_hit_ratio"] == pytest.approx(1200 / 1223, abs=1e-6)

    request = messages.requests[-1]
    assert "cache_control" not in request  # top-level auto would cache the dynamic tail
    assert request["system"][-1]["cache_control"] == {"type": "ephemeral"}
    shared_block, dynamic_block = request["messages"][0]["content"]
    assert shared_block["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in dynamic_block
    assert "第二章" in dynamic_block["text"]
    assert second["cache"]["breakpoint_slots"] == 2
    assert second["cache"]["ttl"] == "5m"
    prewarm_request = messages.requests[0]
    assert prewarm_request["max_tokens"] == 0
    assert "第一章" not in json.dumps(prewarm_request, ensure_ascii=False)
    assert prewarm_request["messages"][0]["content"][-1]["text"] == "cache warmup"


@pytest.mark.asyncio
async def test_model_switch_uses_a_distinct_cache_namespace():
    messages = _CachingMessages()
    first_provider = _provider(messages, "claude-sonnet-4-5")
    second_provider = _provider(messages, "claude-haiku-4-5")

    first = await first_provider.complete(
        "章节任务",
        stable_system_prompt="同一稳定前缀",
        cache_mode="section",
    )
    switched = await second_provider.complete(
        "章节任务",
        stable_system_prompt="同一稳定前缀",
        cache_mode="section",
    )

    assert first["cache"]["prewarm_cache_creation_input_tokens"] > 0
    assert switched["cache"]["prewarm_cache_creation_input_tokens"] > 0
    assert switched["usage"]["cache_read_input_tokens"] > 0


@pytest.mark.asyncio
async def test_stable_prompt_change_does_not_reuse_old_cache():
    messages = _CachingMessages()
    provider = _provider(messages)

    await provider.complete(
        "章节任务",
        stable_system_prompt="固定规则版本 A",
        cache_mode="section",
    )
    changed = await provider.complete(
        "章节任务",
        stable_system_prompt="固定规则版本 B",
        cache_mode="section",
    )

    assert changed["cache"]["prewarm_cache_creation_input_tokens"] == 1200
    assert changed["usage"]["cache_read_input_tokens"] == 1200


@pytest.mark.asyncio
async def test_missing_cache_usage_fields_are_normalized_to_zero():
    class _Messages:
        def create(self, **_kwargs: Any) -> Any:
            usage = SimpleNamespace(input_tokens=17, output_tokens=3)
            return SimpleNamespace(content=[SimpleNamespace(text="完成")], usage=usage)

    result = await _provider(_Messages()).complete("普通任务")

    assert result["usage"]["input_tokens"] == 17
    assert result["usage"]["cache_creation_input_tokens"] == 0
    assert result["usage"]["cache_read_input_tokens"] == 0
    assert result["usage"]["cache_hit_ratio"] == 0.0


@pytest.mark.asyncio
async def test_generic_calls_do_not_cache_the_changing_tail_by_default():
    messages = _CachingMessages()
    result = await _provider(messages).complete("通用多轮任务")

    assert "cache_control" not in messages.requests[-1]
    assert result["cache"]["enabled"] is False
    assert result["cache"]["strategy"] == "disabled"
    assert result["cache"]["automatic"] is False
    assert result["cache"]["breakpoint_slots"] == 0
    assert result["cache"]["ttl"] is None


@pytest.mark.asyncio
async def test_generic_calls_use_automatic_cache_only_when_explicitly_requested():
    messages = _CachingMessages()
    result = await _provider(messages).complete(
        "通用多轮任务",
        cache_mode="automatic",
    )

    assert messages.requests[-1]["cache_control"] == {"type": "ephemeral"}
    assert result["cache"]["strategy"] == "automatic_5m"
    assert result["cache"]["enabled"] is True
    assert result["cache"]["automatic"] is True
    assert result["cache"]["breakpoint_slots"] == 1
    assert result["cache"]["ttl"] == "5m"


@pytest.mark.asyncio
async def test_automatic_cache_can_combine_with_one_explicit_stable_prefix():
    messages = _CachingMessages()
    result = await _provider(messages).complete(
        "增长中的多轮对话",
        stable_system_prompt="稳定系统规则",
        cache_mode="automatic",
    )

    request = messages.requests[-1]
    assert request["cache_control"] == {"type": "ephemeral"}
    assert request["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert result["cache"]["automatic"] is True
    assert result["cache"]["explicit_breakpoints"] == 1
    assert result["cache"]["breakpoint_slots"] == 2


@pytest.mark.asyncio
async def test_cache_enabled_response_without_cache_fields_does_not_fail():
    class _Messages:
        def create(self, **_kwargs: Any) -> Any:
            usage = SimpleNamespace(input_tokens=19, output_tokens=2)
            return SimpleNamespace(content=[SimpleNamespace(text="完成")], usage=usage)

    result = await _provider(_Messages()).complete(
        "动态章节",
        stable_system_prompt="不满足缓存最短长度的稳定前缀",
        cache_mode="section",
    )

    assert result["text"] == "完成"
    assert result["cache"]["prewarm_performed"] is True
    assert result["cache"]["prewarm_effective"] is False
    assert result["usage"]["cache_creation_input_tokens"] == 0
    assert result["usage"]["cache_read_input_tokens"] == 0


@pytest.mark.asyncio
async def test_identical_stable_prefix_has_one_cache_warmup_in_flight():
    class _SlowCachingMessages(_CachingMessages):
        def __init__(self) -> None:
            super().__init__()
            self._lock = threading.Lock()
            self.active = 0
            self.peak_active = 0

        def create(self, **kwargs: Any) -> Any:
            with self._lock:
                self.active += 1
                self.peak_active = max(self.peak_active, self.active)
            try:
                time.sleep(0.05)
                return super().create(**kwargs)
            finally:
                with self._lock:
                    self.active -= 1

    messages = _SlowCachingMessages()
    provider = _provider(messages, model="claude-singleflight-test-model")
    common = {
        "stable_system_prompt": "singleflight 固定系统规则 8b5b8c",
        "shared_context_prompt": "singleflight 项目事实库 8b5b8c",
        "cache_mode": "section",
    }

    first, second = await asyncio.gather(
        provider.complete("动态章节 A", **common),
        provider.complete("动态章节 B", **common),
    )

    assert len(messages.requests) == 3
    assert messages.peak_active == 2
    assert sorted(
        result["cache"]["prewarm_cache_creation_input_tokens"]
        for result in (first, second)
    ) == [0, 1200]
    assert [
        result["usage"]["cache_read_input_tokens"]
        for result in (first, second)
    ] == [1200, 1200]


@pytest.mark.asyncio
async def test_section_writer_separates_stable_shared_and_dynamic_content():
    class _LLM:
        provider = "anthropic"

        def __init__(self) -> None:
            self.prompt = ""
            self.kwargs: dict[str, Any] = {}

        async def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            self.prompt = prompt
            self.kwargs = kwargs
            return {"text": "章节正文", "provider": "anthropic", "model": "test"}

    llm = _LLM()
    writer = SectionWriter(llm=llm)  # type: ignore[arg-type]
    await writer.write(
        "第二章 施工部署",
        {
            "project_id": "P-002",
            "project_fact_snapshot": {
                "facts": {
                    "project_name": {
                        "value": "示例项目",
                        "status": "verified",
                        "evidence": {
                            "locator": "招标文件.pdf#p1_deadbeef@10"
                        },
                    }
                }
            },
            "weights": ["技术方案 30分"],
            "word_format_rules": {"body_font": "宋体"},
            "graphics_rules": {"chart": "确定性生成"},
            "chapter_summaries": [{"title": "第一章", "summary": "工程概况摘要"}],
            "requirements": ["本章临时增加塔吊布置要求"],
        },
    )

    stable = llm.kwargs["stable_system_prompt"]
    shared = llm.kwargs["shared_context_prompt"]
    assert "项目事实库" in stable and "示例项目" in stable
    assert "招标评分规则" in stable and "技术方案 30分" in stable
    assert "Word排版规范" in stable and "宋体" in stable
    assert "图形生成规范" in stable and "确定性生成" in stable
    assert "属于批准的交付追溯标记" in stable
    assert "必须逐字保留" in stable
    assert "已生成章节摘要" in shared and "工程概况摘要" in shared
    assert "当前章节任务" in llm.prompt and "第二章 施工部署" in llm.prompt
    assert "本章临时增加塔吊布置要求" in llm.prompt
    assert "第二章 施工部署" not in stable
    assert llm.kwargs["cache_mode"] == "section"


@pytest.mark.asyncio
async def test_usage_log_and_aggregates_are_privacy_safe():
    messages = _CachingMessages()
    provider = _provider(messages)
    private_text = "居民身份证号310000000000000000"
    private_project_id = "310000000000000000"
    await provider.complete(
        f"动态任务 {private_text}",
        stable_system_prompt="敏感项目正文不得进入日志",
        cache_mode="section",
        project_id=private_project_id,
        task_type="Chapter Generation",
    )

    log_path = os.environ["ZHIFEI_CLAUDE_USAGE_LOG"]
    raw = await asyncio.to_thread(Path(log_path).read_text, encoding="utf-8")
    assert private_text not in raw
    assert "敏感项目正文" not in raw
    assert "api_key" not in raw.lower()
    event = json.loads(raw.splitlines()[-1])
    assert event["project_id"].startswith("project-")
    assert event["project_id"] != private_project_id
    assert private_project_id not in raw
    stats = claude_usage_stats(project_id=private_project_id, path=log_path)
    assert stats["totals"]["calls"] == 2
    assert stats["totals"]["cache_creation_input_tokens"] == 1200
    assert stats["totals"]["cache_read_input_tokens"] == 1200
    assert stats["by_model"][0]["model"] == "claude-sonnet-4-5"
    assert {row["task_type"] for row in stats["by_task"]} == {
        "chapter_generation",
        "chapter_generation_cache_prewarm",
    }
