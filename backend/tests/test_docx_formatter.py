from __future__ import annotations

from backend.zhifei_autoplan.docx_formatter import (
    DEFAULT_FORMAT_CONFIG,
    build_bidding_format_config_from_style,
    merge_style_with_bidding_fallback,
    naturalize_machine_text,
    prepare_delivery_render,
    sanitize_delivery_line,
)


def test_build_bidding_format_config_keeps_null_for_missing_fields():
    cfg = build_bidding_format_config_from_style({})
    assert cfg["body_font"] is None
    assert cfg["title_font"] is None
    assert cfg["body_size_pt"] is None
    assert cfg["title_size_pt"] is None
    assert cfg["line_spacing_pt"] is None
    assert cfg["line_spacing"] is None
    assert cfg["margins_cm"]["top"] is None
    assert cfg["margins_cm"]["right"] is None
    assert cfg["margins_cm"]["bottom"] is None
    assert cfg["margins_cm"]["left"] is None


def test_merge_style_with_bidding_fallback_prefers_bidding_non_null_values():
    user_style = {
        "body_font": "仿宋体",
        "title_font": "仿宋体",
        "body_size": 13,
        "title_size": 15,
        "line_spacing_pt": 20,
        "margins_cm": {"top": 3.0, "right": 2.2, "bottom": 2.2, "left": 2.2},
    }
    bidding_cfg = {
        "body_font": "宋体",
        "title_font": None,
        "body_size_pt": 14,
        "title_size_pt": 16,
        "line_spacing_pt": 22,
        "margins_cm": {"top": 2.5, "right": None, "bottom": 2.0, "left": 2.0},
    }
    merged = merge_style_with_bidding_fallback(user_style=user_style, bidding_format_config=bidding_cfg)
    assert merged["body_font"] == "宋体"
    assert merged["title_font"] == "仿宋体"
    assert merged["body_size"] == 14
    assert merged["title_size"] == 16
    assert merged["line_spacing_pt"] == 22
    assert merged["margins_cm"]["top"] == 2.5
    assert merged["margins_cm"]["right"] == 2.2


def test_merge_style_with_bidding_fallback_uses_default_when_all_missing():
    merged = merge_style_with_bidding_fallback(user_style={}, bidding_format_config={})
    assert merged["body_font"] == DEFAULT_FORMAT_CONFIG["body_font"]
    assert merged["title_font"] == DEFAULT_FORMAT_CONFIG["title_font"]
    assert merged["body_size"] == DEFAULT_FORMAT_CONFIG["body_size_pt"]
    assert merged["title_size"] == DEFAULT_FORMAT_CONFIG["title_size_pt"]
    assert merged["line_spacing_pt"] == DEFAULT_FORMAT_CONFIG["line_spacing_pt"]
    assert "line_spacing" not in merged
    assert merged["margins_cm"] == DEFAULT_FORMAT_CONFIG["margins_cm"]


def test_merge_style_with_bidding_fallback_normalizes_cn_font_aliases():
    merged = merge_style_with_bidding_fallback(
        user_style={"body_font": "黑", "title_font": "楷"},
        bidding_format_config={"body_font": "宋", "title_font": "仿宋"},
    )
    assert merged["body_font"] == "宋体"
    assert merged["title_font"] == "仿宋体"


def test_merge_style_with_bidding_fallback_prefers_bidding_multiple_spacing():
    merged = merge_style_with_bidding_fallback(
        user_style={"line_spacing_pt": 22},
        bidding_format_config={"line_spacing": 1.5},
    )
    assert merged["line_spacing"] == 1.5
    assert "line_spacing_pt" not in merged


def test_merge_style_with_bidding_fallback_defaults_to_22pt_without_requirement():
    merged = merge_style_with_bidding_fallback(
        user_style={},
        bidding_format_config={"line_spacing": None, "line_spacing_pt": None},
    )
    assert merged["line_spacing_pt"] == 22.0
    assert "line_spacing" not in merged


def test_naturalize_machine_text_rewrites_kv_pairs():
    text = naturalize_machine_text("【量化指标】频次=2次/日；阈值=偏差≤5mm；人数=8人/班；设备型号=20t挖机1台")
    assert "频次=2次/日" not in text
    assert "巡检频次控制为2次/日" in text
    assert "关键偏差控制在5mm以内" in text
    assert "现场安排8人/班组织施工" in text


def test_sanitize_delivery_line_strips_system_scaffold_and_internal_tags():
    item = sanitize_delivery_line("【系统全局指令】不得输出调试日志")
    assert item["stripped"] is True
    item2 = sanitize_delivery_line("施工组织执行【图谱节点:node-1】并形成记录。【证据:样例.pdf#p9】")
    assert item2["visible"] == "施工组织执行并形成记录。"
    assert item2["anchors"] == ["样例.pdf#p9"]


def test_prepare_delivery_render_builds_tables():
    prepared = prepare_delivery_render(
        "\n".join(
            [
                "【风险→控制→验证】",
                "风险：交叉作业伤人；控制：设置警戒线并专人指挥；验证：违章为零并完成巡检记录。【证据:图纸A.pdf#p9】",
                "【资源-工序耦合表】",
                "工序=测量复核；班组人数=8人/班；设备=全站仪1台；节拍=4h/作业段。【证据:图纸B.pdf#p3】",
            ]
        )
    )
    assert len(prepared["blocks"]) == 2
    assert prepared["blocks"][0]["type"] == "table"
    assert prepared["blocks"][0]["headers"] == ["风险源", "控制措施", "验证方式"]
    assert prepared["blocks"][1]["type"] == "table"
    assert prepared["blocks"][1]["headers"] == ["工序", "资源配置", "控制要求"]
