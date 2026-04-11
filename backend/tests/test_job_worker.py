import json

from backend.zhifei_autoplan.job_worker import _collect_hard_variant_failures, _derive_runtime_agent_parallelism
from backend.zhifei_autoplan import job_worker


def test_execute_job_persists_stage_artifacts(tmp_path, monkeypatch):
    store = {
        "job-1": {
            "job_id": "job-1",
            "status": "queued",
            "payload": {
                "project_id": "P-1",
                "topic": "测试项目",
                "outline": ["工程概况"],
                "provider_chain": [{"slot": "main", "provider": "openai", "model": "gpt-5.4", "key_alias": "OPENAI_API_KEY_TEXT_MAIN"}],
            },
        }
    }

    def fake_get_job(job_id: str):
        rec = store.get(job_id)
        if rec is None:
            return None
        return json.loads(json.dumps(rec))

    def fake_update_job(job_id: str, **kwargs):
        rec = store.setdefault(job_id, {"job_id": job_id})
        rec.update(kwargs)
        return rec

    async def fake_run_autoplan(payload):
        return {
            "variant_id": payload.get("variant_id") or 1,
            "topic": payload.get("topic") or "",
            "project_type": "房建",
            "generation_mode": "quality_200",
            "logic_template_id": "A",
            "logic_template_name": "交付清单驱动",
            "sections": [
                {
                    "title": "工程概况",
                    "content": "正文内容",
                    "error": "",
                    "requested_timeout_sec": 77,
                    "requested_max_output_tokens": 2600,
                    "requested_section_retry_limit": 1,
                    "runtime_budget_reason": "low_complexity_small_section",
                    "used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                    "latency_ms": 456,
                    "token_usage": {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140},
                    "resource_usage_attempts": [
                        {
                            "attempt": 1,
                            "provider": "openai",
                            "model": "gpt-5.4",
                            "used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                            "latency_ms": 456,
                            "token_usage": {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140},
                        }
                    ],
                }
            ],
            "quality_gate": {"ok": True, "failed": []},
            "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
            "generation_trace": {
                "generation_mode": "quality_200",
                "mode_effective": "quality_200",
                "stable_output": False,
                "deterministic_variant_forced": False,
                "deterministic_logic_template_id": "A",
                "pipeline_stages": [{"stage": "draft_generation", "ok": True}],
                "self_evolution": {"enabled": True, "applied_count": 0},
            },
            "quality_checks": {
                "score": 92,
                "remediation_strategy_audit": {
                    "audit_version": "v1",
                    "applied": True,
                },
                "remediation_execution_audit": {
                    "trace_count": 1,
                    "action_tags": [{"action_tag": "add_quant_value", "label": "补量化数值", "count": 1}],
                },
            },
        }

    monkeypatch.setattr(job_worker, "STAGE_RUN_DIR", tmp_path)
    monkeypatch.setattr(job_worker, "get_job", fake_get_job)
    monkeypatch.setattr(job_worker, "update_job", fake_update_job)
    monkeypatch.setattr(job_worker, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(job_worker, "_save_outputs", lambda prefix, results: {"docx": f"/tmp/{prefix}.docx"})
    monkeypatch.setattr(job_worker, "append_resource_event", lambda *args, **kwargs: "/tmp/resource_usage.jsonl")
    monkeypatch.setattr(
        job_worker,
        "record_task_parallelism_learning",
        lambda *args, **kwargs: {"enabled": True, "updated_entries": 1, "sample": {"runs": 1}},
    )

    job_worker.execute_job("job-1")

    stage_dir = tmp_path / "job-1"
    assert stage_dir.exists()
    assert (stage_dir / "01_job_started.json").exists()
    assert (stage_dir / "02_variant_plan.json").exists()
    assert (stage_dir / "03_variant_results_summary.json").exists()
    assert (stage_dir / "03_self_evolution_learning.json").exists()
    assert (stage_dir / "04_outputs.json").exists()
    started = json.loads((stage_dir / "01_job_started.json").read_text(encoding="utf-8"))
    summary = json.loads((stage_dir / "03_variant_results_summary.json").read_text(encoding="utf-8"))
    learning = json.loads((stage_dir / "03_self_evolution_learning.json").read_text(encoding="utf-8"))
    assert started["payload_summary"]["requested_agent_parallelism"] == 4
    assert started["payload_summary"]["runtime_agent_parallelism"] <= 2
    assert started["payload_summary"]["runtime_agent_parallelism_learning_applied"] is False
    preview = summary["result_summary"]["variants"][0]["section_runtime_budget_preview"][0]
    assert preview["requested_timeout_sec"] == 77
    assert preview["requested_section_retry_limit"] == 1
    assert preview["runtime_budget_reason"] == "low_complexity_small_section"
    assert preview["evolution_applied"] is False
    assert summary["result_summary"]["variants"][0]["self_evolution"]["enabled"] is True
    assert summary["result_summary"]["variants"][0]["remediation_execution_audit"]["trace_count"] == 1
    assert learning["runtime_budget_learning_summary"]["updated_entries"] == 1
    assert learning["task_parallelism_learning_summary"]["updated_entries"] == 1
    assert store["job-1"]["status"] == "done"
    assert store["job-1"]["stage_artifacts_dir"] == str(stage_dir)
    assert store["job-1"]["result"]["resource_usage_summary"]["total_tokens_total"] == 140
    assert store["job-1"]["result"]["resource_usage_summary"]["call_count"] == 1
    assert store["job-1"]["result"]["generation_mode_summary"]["profile"] == "standard_auto"
    assert store["job-1"]["result"]["generation_mode_summary"]["mode_effective"] == "quality_200"
    assert store["job-1"]["result"]["generation_mode_summary"]["stable_output"] is False
    assert store["job-1"]["result"]["generation_mode_summary"]["deterministic_logic_template_id"] == "A"
    assert store["job-1"]["result"]["logic_template_id"] == "A"
    assert store["job-1"]["result"]["logic_template_name"] == "交付清单驱动"
    runtime_variant = next(iter(store["job-1"]["result"]["runtime_by_variant"].values()))
    quality_variant = next(iter(store["job-1"]["result"]["quality_by_variant"].values()))
    assert runtime_variant["pipeline_stages"][0]["stage"] == "draft_generation"
    assert runtime_variant["section_runtime_budget_preview"][0]["requested_timeout_sec"] == 77
    assert quality_variant["quality_score"] == 92
    assert quality_variant["quality_gate_ok"] is True
    assert quality_variant["logic_template_name"] == "交付清单驱动"
    assert quality_variant["remediation_strategy_audit"]["audit_version"] == "v1"
    assert quality_variant["remediation_execution_audit"]["trace_count"] == 1


def test_execute_job_persists_hard_failure_artifact(tmp_path, monkeypatch):
    store = {
        "job-2": {
            "job_id": "job-2",
            "status": "queued",
            "payload": {
                "project_id": "P-2",
                "topic": "失败项目",
                "outline": ["工程概况"],
            },
        }
    }

    def fake_get_job(job_id: str):
        rec = store.get(job_id)
        if rec is None:
            return None
        return json.loads(json.dumps(rec))

    def fake_update_job(job_id: str, **kwargs):
        rec = store.setdefault(job_id, {"job_id": job_id})
        rec.update(kwargs)
        return rec

    async def fake_run_autoplan(_payload):
        return {
            "variant_id": 1,
            "sections": [{"title": "工程概况", "content": "", "error": "quota_exhausted"}],
            "quality_checks": {"score": 0},
            "quality_gate": {"ok": False, "failed": ["all_failed"]},
            "pipeline_stages": [{"stage": "draft_generation", "ok": False}],
            "generation_trace": {"pipeline_stages": [{"stage": "draft_generation", "ok": False}]},
        }

    monkeypatch.setattr(job_worker, "STAGE_RUN_DIR", tmp_path)
    monkeypatch.setattr(job_worker, "get_job", fake_get_job)
    monkeypatch.setattr(job_worker, "update_job", fake_update_job)
    monkeypatch.setattr(job_worker, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(job_worker, "_save_outputs", lambda prefix, results: {"docx": f"/tmp/{prefix}.docx"})
    monkeypatch.setattr(job_worker, "append_resource_event", lambda *args, **kwargs: "/tmp/resource_usage.jsonl")
    monkeypatch.setattr(
        job_worker,
        "record_task_parallelism_learning",
        lambda *args, **kwargs: {"enabled": True, "updated_entries": 1, "sample": {"runs": 1}},
    )

    job_worker.execute_job("job-2")

    stage_dir = tmp_path / "job-2"
    assert (stage_dir / "03_variant_results_summary.json").exists()
    assert (stage_dir / "03_self_evolution_learning.json").exists()
    assert (stage_dir / "04_hard_failures.json").exists()
    learning = json.loads((stage_dir / "03_self_evolution_learning.json").read_text(encoding="utf-8"))
    assert learning["task_parallelism_learning_summary"]["updated_entries"] == 1
    assert store["job-2"]["status"] == "failed"
    assert str(store["job-2"]["error"]).startswith("all_variants_failed_hard_gate:")


def test_collect_hard_variant_failures_when_all_sections_error():
    failures = _collect_hard_variant_failures(
        [
            {
                "variant_id": 2,
                "sections": [
                    {"title": "工程概况", "content": "", "error": "model_not_found"},
                    {"title": "主要施工方法", "content": "", "error": "invalid_argument"},
                ],
            }
        ]
    )
    assert len(failures) == 1
    assert failures[0]["reason"] == "all_sections_failed"
    assert failures[0]["error_count"] == 2
    assert failures[0]["section_total"] == 2


def test_collect_hard_variant_failures_skips_variant_with_real_content():
    failures = _collect_hard_variant_failures(
        [
            {
                "variant_id": 1,
                "sections": [
                    {"title": "工程概况", "content": "正文", "error": ""},
                    {"title": "主要施工方法", "content": "", "error": "timeout"},
                ],
            }
        ]
    )
    assert failures == []


def test_collect_hard_variant_failures_marks_missing_sections():
    failures = _collect_hard_variant_failures([{"variant_id": 3, "sections": []}])
    assert len(failures) == 1
    assert failures[0]["reason"] == "sections_missing"


def test_derive_runtime_agent_parallelism_reduces_small_job():
    runtime = _derive_runtime_agent_parallelism(
        {
            "_mode_policy": {"planned_total_pages": 8},
            "outline": ["工程概况", "施工部署", "质量保证"],
        },
        requested=8,
        variants_total=1,
    )
    assert runtime["effective"] == 2
    assert runtime["planned_pages"] == 8
    assert "small_job_cap=2" in runtime["reason"]


def test_derive_runtime_agent_parallelism_caps_multi_variant_run():
    runtime = _derive_runtime_agent_parallelism(
        {
            "_mode_policy": {"planned_total_pages": 80},
            "outline": ["工程概况", "施工部署", "质量保证", "安全文明施工", "进度计划", "资源配置"],
        },
        requested=8,
        variants_total=2,
    )
    assert runtime["effective"] == 3
    assert "variants>=2_cap=4" in runtime["reason"]
    assert "outline_cap=3" in runtime["reason"]


def test_derive_runtime_agent_parallelism_keeps_large_job_requested_value():
    runtime = _derive_runtime_agent_parallelism(
        {
            "_mode_policy": {"planned_total_pages": 260},
            "outline": [f"第{i}章" for i in range(1, 15)],
        },
        requested=8,
        variants_total=1,
    )
    assert runtime["effective"] == 8
    assert runtime["reason"] == ""


def test_derive_runtime_agent_parallelism_applies_task_learning(monkeypatch):
    monkeypatch.setattr(
        job_worker,
        "build_task_parallelism_hint",
        lambda **kwargs: {
            "enabled": True,
            "applied": True,
            "effective": 2,
            "reason": "historical_task_fallback_rate=0.50_reduce_parallelism",
            "source_runs": 4,
        },
    )
    runtime = _derive_runtime_agent_parallelism(
        {
            "_mode_policy": {"planned_total_pages": 24},
            "outline": ["工程概况", "施工部署", "质量保证", "安全文明施工", "进度计划"],
            "project_type": "房建",
            "generation_mode": "quality_200",
        },
        requested=4,
        variants_total=1,
        params={"self_evolution": {"task_parallelism_enabled": True}},
        task_profile={"entries": {}},
    )
    assert runtime["effective"] == 2
    assert runtime["learning_applied"] is True
    assert runtime["learning_source_runs"] == 4
    assert "historical_task_fallback_rate=0.50_reduce_parallelism" in runtime["reason"]
