from backend.zhifei_autoplan.ui_theme import (
    EXPERT_SYSTEM_CSS,
    activity_html,
    hero_html,
    launch_html,
    section_heading_html,
    workflow_html,
)


def test_professional_theme_defines_accessible_palette_and_responsive_layout():
    assert "--rts-navy-950: #0b1f33" in EXPERT_SYSTEM_CSS
    assert "--rts-teal-700: #0f766e" in EXPERT_SYSTEM_CSS
    assert "@media (max-width: 900px)" in EXPERT_SYSTEM_CSS
    assert "prefers-reduced-motion" in EXPERT_SYSTEM_CSS
    assert 'button[kind="primary"]' in EXPERT_SYSTEM_CSS
    assert "@keyframes rts-agent-pulse" in EXPERT_SYSTEM_CSS


def test_professional_ui_fragments_escape_user_visible_copy():
    section = section_heading_html("01", "资料<上传", "招标&清单")
    assert "资料&lt;上传" in section
    assert "招标&amp;清单" in section
    assert 'class="rts-section-head"' in section

    assert "施组专家系统" in hero_html()
    assert hero_html().count('class="rts-badge"') == 3
    assert workflow_html().count('class="rts-workflow-step"') == 4
    assert "生成前确认" in launch_html()


def test_activity_html_escapes_runtime_text_and_renders_metrics():
    rendered = activity_html(
        {
            "tone": "working",
            "headline": "Agent 正在编辑",
            "activity": "<危险>章节",
            "elapsed_text": "2分03秒",
            "signal_text": "心跳 1 秒前",
            "active_agents": 4,
            "chapters_done": 3,
            "chapters_total": 12,
        }
    )
    assert "rts-activity-card is-working" in rendered
    assert "&lt;危险&gt;章节" in rendered
    assert "活动 Agent 4" in rendered
    assert "章节 3/12" in rendered
