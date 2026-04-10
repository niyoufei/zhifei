from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def test_append_resource_event_writes_workspace_scoped_jsonl(tmp_path: Path):
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan import resource_audit as ra

    root = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", root):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-a"))
        path = ra.append_resource_event(
            "job_queued",
            workspace_dir=workspace_dir,
            session_id="sess-a",
            job_id="job-1",
            token_usage={"input_tokens": 12, "output_tokens": 5, "total_tokens": 17},
        )
        audit_path = Path(path)
        assert audit_path == ws.workspace_paths(workspace_dir)["resource_usage_audit"]
        rows = audit_path.read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        rec = json.loads(rows[0])
        assert rec["event"] == "job_queued"
        assert rec["job_id"] == "job-1"
        assert rec["input_tokens"] == 12
        assert rec["total_tokens"] == 17


def test_summarize_variants_aggregates_attempts_across_sections():
    from backend.zhifei_autoplan.resource_audit import summarize_variants

    summary = summarize_variants(
        [
            {
                "variant_id": 1,
                "topic": "示例项目",
                "sections": [
                    {
                        "title": "工程概况",
                        "resource_usage_attempts": [
                            {
                                "attempt": 1,
                                "provider": "openai",
                                "model": "gpt-5.4",
                                "latency_ms": 320,
                                "token_usage": {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140},
                            }
                        ],
                    },
                    {
                        "title": "施工部署",
                        "resource_usage_attempts": [
                            {
                                "attempt": 1,
                                "provider": "google",
                                "model": "gemini-3.1-pro-preview",
                                "latency_ms": 210,
                                "token_usage": {"input_tokens": 80, "output_tokens": 35, "total_tokens": 115},
                                "cache_hit": True,
                                "cached_tokens": 24,
                            }
                        ],
                    },
                ],
            }
        ]
    )
    assert summary["variant_count"] == 1
    assert summary["call_count"] == 2
    assert summary["input_tokens_total"] == 180
    assert summary["output_tokens_total"] == 75
    assert summary["total_tokens_total"] == 255
    assert summary["cache_hit_calls"] == 1
    assert summary["cached_tokens_total"] == 24
    assert len(summary["providers"]) == 2
    assert summary["variants"][0]["section_count_declared"] == 2


def test_append_resource_events_prefers_explicit_workspace_and_avoids_duplicate_kwarg(tmp_path: Path):
    from backend.zhifei_autoplan import workspace as ws
    from backend.zhifei_autoplan import resource_audit as ra

    root = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", root):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="sess-b"))
        path = ra.append_resource_events(
            [
                {
                    "event": "llm_section_generation",
                    "workspace_dir": workspace_dir,
                    "session_id": "sess-b",
                    "job_id": "job-2",
                    "token_usage": {"input_tokens": 20, "output_tokens": 8, "total_tokens": 28},
                }
            ],
            workspace_dir=workspace_dir,
        )
        assert path == str(ws.workspace_paths(workspace_dir)["resource_usage_audit"])
        rows = ws.workspace_paths(workspace_dir)["resource_usage_audit"].read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        rec = json.loads(rows[0])
        assert rec["event"] == "llm_section_generation"
        assert rec["session_id"] == "sess-b"
        assert rec["job_id"] == "job-2"
        assert rec["total_tokens"] == 28
