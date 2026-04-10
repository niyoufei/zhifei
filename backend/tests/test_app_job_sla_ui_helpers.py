from __future__ import annotations

import ast
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_assigns = {"SUBMISSION_STAGE_LABELS", "JOB_STAGE_LABELS"}
    wanted_funcs = {
        "_safe_float",
        "_format_duration_short",
        "_job_stage_label",
        "_job_failure_hint",
        "_job_sla_snapshot",
        "_job_stage_sla_warning",
        "_job_stage_latency_line",
        "_job_terminal_sla_line",
        "_job_terminal_sla_warning",
        "_job_terminal_sla_split_line",
        "_job_terminal_dual_bottleneck_hint",
        "_job_terminal_focus_hint",
        "_job_terminal_focus_hint_for_status",
        "_job_terminal_summary_sections",
        "_job_terminal_info_line",
        "_job_active_parallelism_lines",
        "_job_done_learning_overview",
        "_job_done_learning_focus",
        "_job_done_profile_summary",
        "_job_done_runtime_summary",
        "_split_runtime_parallelism_reasons",
        "_humanize_runtime_parallelism_reason",
        "_job_done_runtime_focus",
        "_job_done_runtime_overview",
        "_job_done_budget_learning_focus",
        "_job_done_chapter_effect_focus",
        "_job_done_learning_summary",
        "_job_done_remediation_summary",
        "_job_done_summary_lines",
        "_job_done_focus_summary",
        "_job_export_artifact_hint",
        "_job_variant_artifact_hint",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(name in wanted_assigns for name in target_names):
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any, "time": time}
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_job_sla_snapshot_formats_running_stage_and_total_text(monkeypatch):
    helpers = _load_helpers()
    monkeypatch.setattr(helpers.time, "time", lambda: 150.0)
    out = helpers._job_sla_snapshot(
        {
            "total_seconds": 245.7,
            "stages": [
                {
                    "name": "agent_ready",
                    "started_at": 100.0,
                    "ended_at": 120.0,
                    "duration_sec": 20.0,
                    "detail": "多Agent已就绪",
                },
                {
                    "name": "variant_running",
                    "started_at": 130.0,
                    "ended_at": None,
                    "duration_sec": None,
                    "detail": "方案完成进度：1/3",
                },
            ],
        }
    )
    assert out["total_seconds"] == 245.7
    assert out["total_text"] == "4分06秒"
    assert out["current_stage"] == "variant_running"
    assert out["current_stage_text"] == "并行编制方案"
    assert out["current_stage_detail"] == "方案完成进度：1/3"
    assert out["current_stage_seconds"] == 20.0
    assert out["current_stage_seconds_text"] == "20秒"


def test_job_stage_sla_warning_uses_p95_threshold():
    helpers = _load_helpers()
    snapshot = {
        "current_stage": "exporting",
        "current_stage_seconds": 65.0,
        "current_stage_seconds_text": "1分05秒",
    }
    out = helpers._job_stage_sla_warning(snapshot, {"exporting": {"p95_sec": 42.387}})
    assert "阶段耗时预警" in out
    assert "导出成品" in out
    assert "1分05秒" in out
    assert "42秒" in out


def test_job_stage_latency_line_renders_p50_and_p95():
    helpers = _load_helpers()
    snapshot = {"current_stage": "variant_running"}
    out = helpers._job_stage_latency_line(snapshot, {"variant_running": {"p50_sec": 13.408, "p95_sec": 152.0334}})
    assert out == "近期阶段基线：并行编制方案 P50 13秒 / P95 2分32秒"


def test_job_sla_snapshot_keeps_terminal_dominant_stage_fields():
    helpers = _load_helpers()
    out = helpers._job_sla_snapshot(
        {
            "total_seconds": 80.937,
            "current_stage": "done",
            "dominant_stage": "exporting",
            "dominant_stage_seconds": 61.714,
            "dominant_stage_share": 76.2,
            "exporting_seconds": 61.714,
            "exporting_share": 76.2,
            "variant_running_seconds": 19.161,
            "variant_running_share": 23.7,
        }
    )
    assert out["dominant_stage"] == "exporting"
    assert out["dominant_stage_text"] == "导出成品"
    assert out["dominant_stage_seconds_text"] == "1分02秒"
    assert out["dominant_stage_share"] == 76.2
    assert out["exporting_seconds_text"] == "1分02秒"
    assert out["variant_running_seconds_text"] == "19秒"
    assert out["variant_running_share"] == 23.7


def test_job_terminal_sla_line_and_warning_use_dominant_stage():
    helpers = _load_helpers()
    snapshot = {
        "dominant_stage": "exporting",
        "dominant_stage_seconds": 61.714,
        "dominant_stage_seconds_text": "1分02秒",
        "dominant_stage_share": 76.2,
    }
    line = helpers._job_terminal_sla_line(snapshot)
    assert line == "主要耗时：导出成品 1分02秒，占总耗时 76.2%"
    warning = helpers._job_terminal_sla_warning(snapshot, {"exporting": {"p95_sec": 42.387}})
    assert "耗时归因预警" in warning
    assert "导出成品" in warning
    assert "1分02秒" in warning
    assert "42秒" in warning


def test_job_terminal_sla_split_line_shows_variant_and_exporting_breakdown():
    helpers = _load_helpers()
    snapshot = {
        "variant_running_seconds_text": "49秒",
        "variant_running_share": 49.9,
        "exporting_seconds_text": "49秒",
        "exporting_share": 50.1,
    }
    line = helpers._job_terminal_sla_split_line(snapshot)
    assert line == "本次耗时拆解：并行编制方案 49秒（49.9%）；导出成品 49秒（50.1%）"

    quiet = helpers._job_terminal_sla_split_line(
        {
            "variant_running_seconds_text": "21秒",
            "variant_running_share": 84.4,
            "exporting_seconds_text": "4秒",
            "exporting_share": 15.6,
        }
    )
    assert quiet == ""


def test_job_terminal_dual_bottleneck_hint_points_to_both_stage_artifacts():
    helpers = _load_helpers()
    hint = helpers._job_terminal_dual_bottleneck_hint(
        {
            "variant_running_share": 43.2,
            "exporting_share": 41.6,
        },
        "build/_stage_runs/job-7",
    )
    assert "双瓶颈提示" in hint
    assert "build/_stage_runs/job-7/03_variant_results_summary.json" in hint
    assert "build/_stage_runs/job-7/04_outputs.json" in hint

    quiet = helpers._job_terminal_dual_bottleneck_hint(
        {
            "variant_running_share": 74.0,
            "exporting_share": 18.2,
        },
        "build/_stage_runs/job-8",
    )
    assert quiet == ""


def test_job_terminal_focus_hint_prefers_dual_then_dominant_stage_specific_hint():
    helpers = _load_helpers()
    dual = helpers._job_terminal_focus_hint(
        {
            "dominant_stage": "exporting",
            "variant_running_share": 41.2,
            "exporting_share": 44.8,
        },
        "build/_stage_runs/job-9",
    )
    assert "双瓶颈提示" in dual
    assert "03_variant_results_summary.json" in dual
    assert "04_outputs.json" in dual

    variant_only = helpers._job_terminal_focus_hint(
        {
            "dominant_stage": "variant_running",
            "variant_running_share": 80.8,
            "exporting_share": 19.2,
            "current_stage": "done",
        },
        "build/_stage_runs/job-10",
    )
    assert "方案编制排查入口" in variant_only
    assert "03_variant_results_summary.json" in variant_only

    export_only = helpers._job_terminal_focus_hint(
        {
            "dominant_stage": "exporting",
            "variant_running_share": 24.1,
            "exporting_share": 73.6,
            "current_stage": "done",
        },
        "build/_stage_runs/job-11",
    )
    assert "导出排查入口" in export_only
    assert "04_outputs.json" in export_only


def test_job_terminal_focus_hint_for_status_suppresses_generic_focus_on_failure():
    helpers = _load_helpers()
    kept = helpers._job_terminal_focus_hint_for_status("done", "导出排查入口：优先查看 04_outputs.json", "")
    assert "导出排查入口" in kept

    hidden = helpers._job_terminal_focus_hint_for_status(
        "failed",
        "导出排查入口：优先查看 04_outputs.json",
        "后台执行进程未成功拉起；优先检查后端/worker 启动日志。",
    )
    assert hidden == ""


def test_job_terminal_summary_sections_keep_done_focus_after_warning_group():
    helpers = _load_helpers()
    sections = helpers._job_terminal_summary_sections(
        "done",
        {
            "dominant_stage": "exporting",
            "dominant_stage_seconds_text": "1分02秒",
            "dominant_stage_share": 76.2,
            "variant_running_seconds_text": "19秒",
            "variant_running_share": 23.7,
            "exporting_seconds_text": "1分02秒",
            "exporting_share": 76.2,
        },
        "导出排查入口：优先查看 build/_stage_runs/job-2/04_outputs.json",
        "",
    )
    assert sections == {
        "pre_warning": [
            "主要耗时：导出成品 1分02秒，占总耗时 76.2%",
            "本次耗时拆解：并行编制方案 19秒（23.7%）；导出成品 1分02秒（76.2%）",
        ],
        "post_warning": [
            "导出排查入口：优先查看 build/_stage_runs/job-2/04_outputs.json",
        ],
    }


def test_job_terminal_summary_sections_prioritize_failure_error_before_sla():
    helpers = _load_helpers()
    sections = helpers._job_terminal_summary_sections(
        "failed",
        {
            "dominant_stage": "variant_running",
            "dominant_stage_seconds_text": "2分11秒",
            "dominant_stage_share": 88.0,
        },
        "",
        "worker_spawn_failed: subprocess exited early",
    )
    assert sections == {
        "pre_warning": [
            "错误/原因：worker_spawn_failed: subprocess exited early",
            "主要耗时：并行编制方案 2分11秒，占总耗时 88%",
        ],
        "post_warning": [],
    }


def test_job_terminal_info_line_only_returns_failure_guidance():
    helpers = _load_helpers()
    assert helpers._job_terminal_info_line("failed", "后台执行进程未成功拉起") == "排查建议：后台执行进程未成功拉起"
    assert helpers._job_terminal_info_line("done", "后台执行进程未成功拉起") == ""


def test_job_active_parallelism_lines_humanizes_reason_and_progress():
    helpers = _load_helpers()
    out = helpers._job_active_parallelism_lines(
        {
            "agent_parallelism": 3,
            "requested_agent_parallelism": 4,
            "variant_parallelism": 2,
            "runtime_agent_parallelism_reason": "outline_cap=3, historical_task_quality_issue_rate=0.67_reduce_parallelism",
            "runtime_agent_parallelism_learning_applied": True,
            "runtime_agent_parallelism_learning_reason": "historical_task_quality_issue_rate=0.67_reduce_parallelism",
        },
        1,
        3,
    )
    assert out == [
        "多Agent并行：章节并行=3（请求=4，已按任务规模收敛），方案并行=2，完成方案=1/3",
        "并发收敛原因：按目录规模收敛到 3 并行",
    ]


def test_job_done_learning_overview_summarizes_learning_layers():
    helpers = _load_helpers()
    out = helpers._job_done_learning_overview(
        {
            "applied_count": 2,
            "source_runs": 3,
            "bundle_applied_count": 1,
            "bundle_source_runs": 2,
            "context_bundle_applied_count": 1,
            "context_bundle_source_runs": 2,
            "context_bundle_effect_applied_count": 1,
            "context_bundle_effect_source_runs": 2,
            "context_bundle_metric_effect_applied_count": 2,
            "context_bundle_metric_effect_source_runs": 3,
            "context_bundle_metric_action_effect_applied_count": 2,
            "context_bundle_metric_action_effect_source_runs": 3,
        }
    )
    assert out == (
        "修订学习摘要：排序学习=2项（样本=3）；组合包学习=1项（样本=2）；"
        "语境组合包=1项（样本=2）；效果归因=1项（归因样本=2）；"
        "指标归因=2项（样本=3）；动作归因=2项（样本=3）"
    )


def test_job_done_learning_focus_prefers_combo_then_metric_fallback():
    helpers = _load_helpers()
    combo = helpers._job_done_learning_focus(
        {
            "combos": ["缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3"],
            "context_bundle_metric_action_effect_triplets": ["量化指标达标率/补量化数值"],
        }
    )
    assert combo == "重点命中：缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3"

    fallback = helpers._job_done_learning_focus(
        {
            "context_bundle_metric_action_effect_triplets": ["量化指标达标率/补量化数值", "风险三元组达标率/补风险→控制→验证"],
        }
    )
    assert fallback == "本次拉平动作：量化指标达标率/补量化数值 / 风险三元组达标率/补风险→控制→验证"


def test_job_done_profile_summary_merges_budget_issue_and_action():
    helpers = _load_helpers()
    out = helpers._job_done_profile_summary(
        [
            {
                "title": "工程概况",
                "requested_timeout_sec": 77,
                "requested_section_retry_limit": 1,
            },
            {
                "title": "主要施工方法",
                "requested_timeout_sec": 120,
                "requested_section_retry_limit": 2,
            },
        ],
        {
            "indicator_groups": [
                {"indicator_group": "缺量化", "count": 2},
                {"indicator_group": "缺闭环", "count": 1},
            ]
        },
        {
            "action_tags": [
                {"label": "补量化数值", "count": 2},
                {"label": "补验收/记录", "count": 1},
            ]
        },
    )
    assert out == (
        "修订画像摘要：预算=工程概况(77s/1轮) / 主要施工方法(120s/2轮)；"
        "问题=缺量化×2 / 缺闭环×1；动作=补量化数值×2 / 补验收/记录×1"
    )


def test_job_done_runtime_summary_merges_parallel_learning_and_quality_gate():
    helpers = _load_helpers()
    out = helpers._job_done_runtime_summary(
        {
            "requested_agent_parallelism": 6,
            "agent_parallelism": 4,
            "variant_parallelism": 3,
            "runtime_agent_parallelism_learning_applied": True,
            "runtime_agent_parallelism_learning_source_runs": 5,
        },
        {
            "quality_gate_ok": False,
            "quality_gate_failed_count": 2,
            "quality_gate_retry_rounds": 1,
            "terminology_replacement_count": 7,
        },
    )
    assert out == (
        "运行画像摘要：并发=章节4 / 方案3（请求=6）；并发学习=已应用（样本=5）；"
        "自动巡检=未完全通过（剩余2项）；自动修复=1轮；术语纠偏=7次"
    )


def test_humanize_runtime_parallelism_reason_translates_builtin_tokens():
    helpers = _load_helpers()
    out = helpers._humanize_runtime_parallelism_reason(
        "outline_cap=3, historical_task_quality_issue_rate=0.67_reduce_parallelism"
    )
    assert out == "按目录规模收敛到 3 并行；历史质量问题率 67%，降低并行度"


def test_job_done_runtime_focus_merges_reason_and_learning_hit():
    helpers = _load_helpers()
    out = helpers._job_done_runtime_focus(
        {
            "runtime_agent_parallelism_reason": (
                "outline_cap=3, historical_task_quality_issue_rate=0.67_reduce_parallelism"
            ),
            "runtime_agent_parallelism_learning_applied": True,
            "runtime_agent_parallelism_learning_reason": "historical_task_quality_issue_rate=0.67_reduce_parallelism",
            "runtime_agent_parallelism_learning_source_runs": 5,
        }
    )
    assert out == (
        "运行期收敛摘要：收敛=按目录规模收敛到 3 并行；"
        "学习命中=历史质量问题率 67%，降低并行度（样本=5）"
    )


def test_job_done_runtime_overview_merges_runtime_and_focus_layers():
    helpers = _load_helpers()
    out = helpers._job_done_runtime_overview(
        {
            "requested_agent_parallelism": 6,
            "agent_parallelism": 4,
            "variant_parallelism": 3,
            "runtime_agent_parallelism_learning_applied": True,
            "runtime_agent_parallelism_learning_source_runs": 5,
            "runtime_agent_parallelism_reason": "章节粒度收敛到 4 并行",
            "runtime_agent_parallelism_learning_reason": "历史样本显示工程概况章节需提高稳定度",
        },
        {
            "quality_gate_ok": False,
            "quality_gate_failed_count": 2,
            "quality_gate_retry_rounds": 1,
            "terminology_replacement_count": 7,
        },
    )
    assert out == (
        "运行画像摘要：并发=章节4 / 方案3（请求=6）；并发学习=已应用（样本=5）；"
        "自动巡检=未完全通过（剩余2项）；自动修复=1轮；术语纠偏=7次；"
        "收敛=章节粒度收敛到 4 并行；学习命中=历史样本显示工程概况章节需提高稳定度（样本=5）"
    )


def test_job_done_budget_learning_focus_lists_applied_sections_only():
    helpers = _load_helpers()
    out = helpers._job_done_budget_learning_focus(
        [
            {
                "title": "工程概况",
                "evolution_applied": True,
                "evolution_source_runs": 3,
                "evolution_reason": "historical_quality_issue_rate=0.67_raise_tokens",
            },
            {
                "title": "主要施工方法",
                "evolution_applied": False,
                "evolution_source_runs": 2,
            },
        ]
    )
    assert out == "运行期学习命中：工程概况（样本=3）"


def test_job_done_chapter_effect_focus_summarizes_metric_and_action():
    helpers = _load_helpers()
    out = helpers._job_done_chapter_effect_focus(
        {
            "chapter_effect_summary": [
                {
                    "title": "工程概况",
                    "resolved_metrics": ["量化指标达标率", "风险三元组达标率"],
                    "resolved_action_triplets": ["量化指标达标率/补量化数值"],
                }
            ]
        }
    )
    assert out == "章节级拉平：工程概况->指标=量化指标达标率/风险三元组达标率; 动作=量化指标达标率/补量化数值"


def test_job_done_learning_summary_merges_budget_and_learning_overview():
    helpers = _load_helpers()
    out = helpers._job_done_learning_summary(
        [
            {
                "title": "工程概况",
                "evolution_applied": True,
                "evolution_source_runs": 3,
            }
        ],
        {
            "applied_count": 2,
            "source_runs": 3,
            "bundle_applied_count": 1,
            "bundle_source_runs": 2,
        },
    )
    assert out == (
        "学习画像摘要：预算学习=工程概况（样本=3）；"
        "排序学习=2项（样本=3）；组合包学习=1项（样本=2）"
    )


def test_job_done_focus_summary_merges_learning_hit_and_chapter_effect():
    helpers = _load_helpers()
    out = helpers._job_done_focus_summary(
        {
            "combos": ["缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3"],
            "chapter_effect_summary": [
                {
                    "title": "工程概况",
                    "resolved_metrics": ["量化指标达标率", "风险三元组达标率"],
                    "resolved_action_triplets": ["量化指标达标率/补量化数值"],
                }
            ],
        }
    )
    assert out == (
        "重点修订命中：缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3；"
        "工程概况->指标=量化指标达标率/风险三元组达标率; 动作=量化指标达标率/补量化数值"
    )


def test_job_done_remediation_summary_merges_profile_and_learning_layers():
    helpers = _load_helpers()
    out = helpers._job_done_remediation_summary(
        "修订画像摘要：预算=工程概况(77s/1轮)；问题=缺量化×2；动作=补量化数值×2",
        "学习画像摘要：预算学习=工程概况（样本=3）；排序学习=2项（样本=3）",
    )
    assert out == (
        "修订学习画像摘要：预算=工程概况(77s/1轮)；问题=缺量化×2；动作=补量化数值×2；"
        "预算学习=工程概况（样本=3）；排序学习=2项（样本=3）"
    )


def test_job_done_summary_lines_keep_runtime_then_remediation_then_focus():
    helpers = _load_helpers()
    out = helpers._job_done_summary_lines(
        {
            "requested_agent_parallelism": 6,
            "agent_parallelism": 4,
            "variant_parallelism": 3,
            "runtime_agent_parallelism_reason": "outline_cap=3",
            "runtime_agent_parallelism_learning_applied": False,
        },
        {
            "quality_gate_ok": True,
            "quality_gate_failed_count": 0,
            "quality_gate_retry_rounds": 1,
            "terminology_replacement_count": 2,
        },
        [
            {
                "title": "工程概况",
                "requested_timeout_sec": 77,
                "requested_section_retry_limit": 1,
                "evolution_applied": True,
                "evolution_source_runs": 3,
            }
        ],
        {"indicator_groups": [{"indicator_group": "缺量化", "count": 2}]},
        {"action_tags": [{"label": "补量化数值", "count": 2}]},
        {"combos": ["缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3"]},
    )
    assert out == [
        "运行画像摘要：并发=章节4 / 方案3（请求=6）；自动巡检=通过；自动修复=1轮；术语纠偏=2次；收敛=按目录规模收敛到 3 并行",
        "修订学习画像摘要：预算=工程概况(77s/1轮)；问题=缺量化×2；动作=补量化数值×2；预算学习=工程概况（样本=3）",
        "重点修订命中：缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3",
    ]


def test_job_export_artifact_hint_appears_for_exporting_stage_only():
    helpers = _load_helpers()
    hint = helpers._job_export_artifact_hint(
        {"current_stage": "exporting"},
        "build/_stage_runs/job-1",
    )
    assert "04_outputs.json" in hint
    assert "docx / compare_docx / focus_xlsx / score_overview_xlsx" in hint
    assert "build/_stage_runs/job-1/04_outputs.json" in hint

    terminal_hint = helpers._job_export_artifact_hint(
        {"current_stage": "done", "dominant_stage": "exporting"},
        "build/_stage_runs/job-2",
    )
    assert "build/_stage_runs/job-2/04_outputs.json" in terminal_hint

    empty = helpers._job_export_artifact_hint(
        {"current_stage": "variant_running", "dominant_stage": "variant_running"},
        "build/_stage_runs/job-3",
    )
    assert empty == ""


def test_job_variant_artifact_hint_distinguishes_running_and_terminal_generation_slow():
    helpers = _load_helpers()
    running_hint = helpers._job_variant_artifact_hint(
        {"current_stage": "variant_running"},
        "build/_stage_runs/job-4",
    )
    assert "当前仍在并行编制阶段" in running_hint
    assert "build/_stage_runs/job-4/03_variant_results_summary.json" in running_hint
    assert "章节预算摘要" in running_hint

    terminal_hint = helpers._job_variant_artifact_hint(
        {"current_stage": "done", "dominant_stage": "variant_running"},
        "build/_stage_runs/job-5",
    )
    assert "定位慢章节" in terminal_hint
    assert "build/_stage_runs/job-5/03_variant_results_summary.json" in terminal_hint

    empty = helpers._job_variant_artifact_hint(
        {"current_stage": "done", "dominant_stage": "exporting"},
        "build/_stage_runs/job-6",
    )
    assert empty == ""


def test_job_failure_hint_maps_confirmed_backend_error_prefixes():
    helpers = _load_helpers()
    hint = helpers._job_failure_hint(
        "failed",
        "all_variants_failed_hard_gate: v1:coverage(3/12); v2:logic(2/12)",
        "/tmp/job-123",
    )
    assert "最低质量门槛" in hint
    assert "hard_failures" in hint
    assert "/tmp/job-123" in hint

    hint = helpers._job_failure_hint("failed", "worker_spawn_failed: RuntimeError('boom')", "")
    assert "后台执行进程未成功拉起" in hint

    hint = helpers._job_failure_hint("failed", "stale_worker_timeout(lease=600, heartbeat_age=901)", "")
    assert "任务心跳已超时" in hint

    hint = helpers._job_failure_hint("cancelled", "cancelled_by_user", "")
    assert "人工主动中止" in hint
