from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {
        "_load_generation_mode_catalog",
        "_coerce_variant_position",
        "_normalize_variant_dict_map",
        "_recent_job_mode_quality_caption",
        "_recent_job_needs_review",
        "_recent_job_action_label",
        "_failed_variant_count",
        "_first_failed_variant_index",
        "_quality_failure_brief",
        "_quality_variant_snapshot",
        "_review_apply_feedback",
        "_review_issue_signature",
        "_review_issue_delta_feedback",
        "_review_severity_priority",
        "_review_rows_for_editor",
        "_review_editor_focus_summary",
        "_review_rows_match_filter",
        "_review_filter_counts",
        "_merge_review_rows",
        "_review_priority_summary",
        "_recent_job_quality_signal",
        "_review_workspace_focus_notice",
        "_recent_job_sort_key",
        "_recent_job_matches_filter",
    }
    wanted_assigns = {
        "GENERATION_MODE_CATALOG",
        "GENERATION_MODE_OPTIONS",
        "GENERATION_MODE_LABELS",
        "GENERATION_ENGINE_LABELS",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in wanted_assigns for name in target_names):
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_coerce_variant_position_accepts_variant_labels():
    helpers = _load_helpers()

    assert helpers._coerce_variant_position(3) == 3
    assert helpers._coerce_variant_position("7") == 7
    assert helpers._coerce_variant_position("v12") == 12
    assert helpers._coerce_variant_position(" V5 ") == 5
    assert helpers._coerce_variant_position("bad") is None
    assert helpers._coerce_variant_position(0) is None


def test_normalize_variant_dict_map_prefers_variant_index_then_key_then_variant_id():
    helpers = _load_helpers()

    out = helpers._normalize_variant_dict_map(
        {
            "47": {"variant_index": 1, "variant_id": 47, "quality_score": 98},
            "v2": {"variant_id": 99, "quality_score": 95},
            "bad": {"variant_id": 3, "quality_score": 92},
            "skip": "not-a-dict",
        }
    )

    assert sorted(out.keys()) == [1, 2, 3]
    assert out[1]["quality_score"] == 98
    assert out[2]["variant_id"] == 99
    assert out[3]["quality_score"] == 92


def test_recent_job_mode_quality_caption_renders_stable_delivery_summary():
    helpers = _load_helpers()

    line = helpers._recent_job_mode_quality_caption(
        {
            "generation_mode_summary": {
                "profile": "stable_delivery",
                "mode_effective": "stable_delivery",
                "stable_output": True,
            },
            "logic_template_name": "交付清单驱动",
            "quality_score": 98,
            "quality_gate_ok": False,
            "quality_gate_failed_count": 1,
        }
    )

    assert "档位=稳交：优先结果一致性" in line
    assert "执行=稳定交付执行" in line
    assert "稳定交付" in line
    assert "模板=交付清单驱动" in line
    assert "质量分=98" in line
    assert "质量闸门=未通过" in line
    assert "未通过项=1" in line


def test_recent_job_quality_signal_marks_warning_and_success_cases():
    helpers = _load_helpers()

    warning_signal = helpers._recent_job_quality_signal(
        {
            "quality_score": 98,
            "quality_gate_ok": False,
            "quality_gate_failed_count": 1,
        }
    )
    assert warning_signal["level"] == "warning"
    assert "质量闸门未通过" in warning_signal["message"]
    assert "未通过项=1" in warning_signal["message"]
    assert "质量分=98" in warning_signal["message"]

    success_signal = helpers._recent_job_quality_signal(
        {
            "quality_score": 100,
            "quality_gate_ok": True,
            "quality_gate_failed_count": 0,
        }
    )
    assert success_signal["level"] == "success"
    assert "质量闸门已通过" in success_signal["message"]
    assert "质量分=100" in success_signal["message"]


def test_recent_job_action_label_marks_review_needed_done_jobs():
    helpers = _load_helpers()

    assert helpers._recent_job_action_label({"status": "running"}) == "接回任务"
    assert helpers._recent_job_action_label({"status": "done", "quality_gate_ok": False}) == "载入复核"
    assert helpers._recent_job_action_label({"status": "done", "quality_gate_ok": True}) == "载入结果"


def test_first_failed_variant_index_finds_smallest_failed_variant():
    helpers = _load_helpers()

    quality_map = {
        3: {"quality_gate_ok": False},
        1: {"quality_gate_ok": True},
        2: {"quality_gate_ok": False},
    }

    assert helpers._failed_variant_count(quality_map) == 2
    assert helpers._first_failed_variant_index(quality_map) == 2
    assert helpers._first_failed_variant_index({1: {"quality_gate_ok": True}}) is None


def test_quality_failure_brief_and_priority_summary_render_indicator_and_action_hints():
    helpers = _load_helpers()

    quality_info = {
        "quality_score": 91,
        "quality_gate_ok": False,
        "quality_gate_failed_count": 3,
        "remediation_strategy_audit": {
            "indicator_groups": [
                {"indicator_group": "缺量化", "count": 2},
                {"indicator_group": "缺闭环", "count": 1},
            ]
        },
        "remediation_execution_audit": {
            "action_tags": [
                {"label": "补量化数值", "count": 2},
                {"label": "补验收记录", "count": 1},
            ]
        },
    }

    brief = helpers._quality_failure_brief(quality_info)
    assert brief == "问题=缺量化×2 / 缺闭环×1；动作=补量化数值×2 / 补验收记录×1"

    summary = helpers._review_priority_summary({"quality_by_variant": {1: {"quality_gate_ok": True}, 2: quality_info}})
    assert "优先复核 v2" in summary
    assert "质量分=91" in summary
    assert "未通过项=3" in summary
    assert "问题=缺量化×2 / 缺闭环×1" in summary
    assert "动作=补量化数值×2 / 补验收记录×1" in summary


def test_quality_variant_snapshot_and_review_apply_feedback_capture_delta():
    helpers = _load_helpers()

    before_result = {
        "quality_by_variant": {
            2: {
                "quality_score": 88,
                "quality_gate_ok": False,
                "quality_gate_failed_count": 3,
                "remediation_strategy_audit": {"indicator_groups": [{"indicator_group": "缺量化", "count": 2}]},
                "remediation_execution_audit": {"action_tags": [{"label": "补量化数值", "count": 2}]},
            }
        }
    }
    after_result = {
        "quality_by_variant": {
            2: {
                "quality_score": 94,
                "quality_gate_ok": True,
                "quality_gate_failed_count": 0,
                "remediation_strategy_audit": {"indicator_groups": [{"indicator_group": "缺闭环", "count": 1}]},
                "remediation_execution_audit": {"action_tags": [{"label": "补验收记录", "count": 1}]},
            }
        }
    }

    before_snapshot = helpers._quality_variant_snapshot(before_result, 2)
    after_snapshot = helpers._quality_variant_snapshot(after_result, 2)
    feedback = helpers._review_apply_feedback(before_snapshot, after_snapshot, variant=2, applied_count=3)

    assert before_snapshot["quality_score"] == 88
    assert before_snapshot["failure_brief"] == "问题=缺量化×2；动作=补量化数值×2"
    assert after_snapshot["quality_gate_ok"] is True
    assert feedback["level"] == "success"
    assert "v2 已回写 3 项" in feedback["message"]
    assert "质量分 88->94" in feedback["message"]
    assert "未通过项 3->0" in feedback["message"]
    assert "质量闸门 未通过->通过" in feedback["message"]
    assert "当前问题=问题=缺闭环×1；动作=补验收记录×1" in feedback["message"]


def test_review_issue_delta_feedback_reports_resolved_and_remaining_items():
    helpers = _load_helpers()

    before_rows = [
        {"source": "issue_list", "title": "主要施工方法", "type": "quantitative_gap", "problem": "量化不足", "suggestion": "补量化", "severity": "high"},
        {"source": "issue_list", "title": "安全措施", "type": "risk_triplet_gap", "problem": "闭环不足", "suggestion": "补闭环", "severity": "medium"},
    ]
    after_rows = [
        {"source": "issue_list", "title": "安全措施", "type": "risk_triplet_gap", "problem": "闭环不足", "suggestion": "补闭环", "severity": "high"},
        {"source": "auto_revision_suggestions", "title": "质量保证措施", "type": "consistency_gap", "problem": "", "suggestion": "统一表述", "severity": "medium"},
    ]

    assert helpers._review_issue_signature(before_rows[0]).startswith("issue_list||主要施工方法||quantitative_gap")
    feedback = helpers._review_issue_delta_feedback(before_rows, after_rows)
    assert feedback["level"] == "warning"
    assert "已闭合 1 项" in feedback["message"]
    assert "仍残留 2 项" in feedback["message"]
    assert "高优 1 项" in feedback["message"]
    assert "新增 1 项" in feedback["message"]
    assert "残留重点=安全措施/risk_triplet_gap / 质量保证措施/consistency_gap" in feedback["message"]


def test_review_rows_for_editor_prioritize_high_severity_first():
    helpers = _load_helpers()

    rows = [
        {"issue_id": "R0002", "title": "安全措施", "type": "risk_triplet_gap", "severity": "medium"},
        {"issue_id": "I0001", "title": "主要施工方法", "type": "quantitative_gap", "severity": "high"},
        {"issue_id": "R0003", "title": "质量保证措施", "type": "consistency_gap", "severity": "low"},
    ]

    ordered = helpers._review_rows_for_editor(rows)
    assert [row["issue_id"] for row in ordered] == ["I0001", "R0002", "R0003"]
    assert helpers._review_severity_priority("high") == 3
    assert helpers._review_severity_priority("medium") == 2


def test_review_editor_focus_summary_calls_out_high_priority_rows():
    helpers = _load_helpers()

    summary = helpers._review_editor_focus_summary(
        [
            {"issue_id": "I0001", "title": "主要施工方法", "type": "quantitative_gap", "severity": "high"},
            {"issue_id": "I0002", "title": "安全措施", "type": "risk_triplet_gap", "severity": "high"},
            {"issue_id": "R0003", "title": "质量保证措施", "type": "consistency_gap", "severity": "medium"},
        ]
    )

    assert summary["level"] == "warning"
    assert "当前高优问题 2 项" in summary["message"]
    assert "主要施工方法/quantitative_gap" in summary["message"]
    assert "安全措施/risk_triplet_gap" in summary["message"]


def test_review_rows_match_filter_and_counts_support_high_selected_and_replacement_views():
    helpers = _load_helpers()

    rows = [
        {
            "issue_id": "I0001",
            "title": "主要施工方法",
            "type": "quantitative_gap",
            "severity": "high",
            "apply": True,
            "replacement": "补充替换文本",
        },
        {
            "issue_id": "I0002",
            "title": "安全措施",
            "type": "risk_triplet_gap",
            "severity": "high",
            "apply": False,
            "replacement": "",
        },
        {
            "issue_id": "R0003",
            "title": "质量保证措施",
            "type": "consistency_gap",
            "severity": "medium",
            "apply": True,
            "replacement": "  ",
        },
    ]

    counts = helpers._review_filter_counts(rows)
    assert counts == {"all": 3, "high": 2, "selected": 2, "replacement_ready": 1}
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "all")] == ["I0001", "I0002", "R0003"]
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "high")] == ["I0001", "I0002"]
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "selected")] == ["I0001", "R0003"]
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "replacement_ready")] == ["I0001"]
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "all", "安全措施")] == ["I0002"]
    assert [row["issue_id"] for row in helpers._review_rows_match_filter(rows, "selected", "质量保证措施")] == ["R0003"]


def test_merge_review_rows_preserves_hidden_rows_and_applies_visible_edits():
    helpers = _load_helpers()

    current_rows = [
        {"issue_id": "I0001", "apply": True, "replacement": "", "title": "主要施工方法"},
        {"issue_id": "I0002", "apply": False, "replacement": "", "title": "安全措施"},
        {"issue_id": "R0003", "apply": True, "replacement": "", "title": "质量保证措施"},
    ]
    updated_rows = [
        {"issue_id": "I0001", "apply": False, "replacement": "替换后段落", "title": "主要施工方法"},
        {"issue_id": "R0003", "apply": True, "replacement": "", "title": "质量保证措施"},
    ]

    merged = helpers._merge_review_rows(current_rows, updated_rows)
    assert [row["issue_id"] for row in merged] == ["I0001", "I0002", "R0003"]
    assert merged[0]["apply"] is False
    assert merged[0]["replacement"] == "替换后段落"
    assert merged[1]["apply"] is False
    assert merged[2]["apply"] is True


def test_review_workspace_focus_notice_only_for_review_needed_current_job():
    helpers = _load_helpers()

    message = helpers._review_workspace_focus_notice(
        {
            "job_id": "job-1",
            "quality_by_variant": {
                1: {"quality_gate_ok": True},
                2: {"quality_gate_ok": True},
                3: {
                    "quality_gate_ok": False,
                    "quality_score": 88,
                    "quality_gate_failed_count": 2,
                    "remediation_strategy_audit": {"indicator_groups": [{"indicator_group": "缺量化", "count": 2}]},
                    "remediation_execution_audit": {"action_tags": [{"label": "补量化数值", "count": 2}]},
                },
            },
        },
        "job-1",
    )

    assert "待复核成品" in message
    assert "1 个方案未通过质量闸门" in message
    assert "优先复核 v3" in message
    assert "问题=缺量化×2" in message
    assert helpers._review_workspace_focus_notice({"job_id": "job-1", "quality_by_variant": {}}, "job-1") == ""
    assert helpers._review_workspace_focus_notice({"job_id": "job-2", "quality_by_variant": {1: {"quality_gate_ok": False}}}, "job-1") == ""


def test_recent_job_sort_key_prioritizes_running_then_review_needed_done():
    helpers = _load_helpers()

    running = {"status": "running", "updated_at": 100}
    queued = {"status": "queued", "updated_at": 110}
    review_needed_done = {"status": "done", "quality_gate_ok": False, "updated_at": 90}
    failed = {"status": "failed", "updated_at": 120}
    clean_done = {"status": "done", "quality_gate_ok": True, "updated_at": 130}

    ordered = sorted(
        [clean_done, failed, review_needed_done, queued, running],
        key=helpers._recent_job_sort_key,
    )

    assert ordered == [running, queued, review_needed_done, failed, clean_done]


def test_recent_job_matches_filter_supports_active_review_needed_and_exceptions():
    helpers = _load_helpers()

    running = {"status": "running"}
    review_needed_done = {"status": "done", "quality_gate_ok": False}
    clean_done = {"status": "done", "quality_gate_ok": True}
    failed = {"status": "failed"}

    assert helpers._recent_job_matches_filter(running, "all") is True
    assert helpers._recent_job_matches_filter(running, "active") is True
    assert helpers._recent_job_matches_filter(review_needed_done, "review_needed") is True
    assert helpers._recent_job_matches_filter(clean_done, "review_needed") is False
    assert helpers._recent_job_matches_filter(failed, "exceptions") is True
    assert helpers._recent_job_matches_filter(clean_done, "exceptions") is False
