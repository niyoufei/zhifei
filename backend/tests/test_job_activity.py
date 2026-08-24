from backend.zhifei_autoplan.job_activity import build_job_activity, format_duration


def test_format_duration_is_compact_and_chinese():
    assert format_duration(5) == "5秒"
    assert format_duration(65) == "1分05秒"
    assert format_duration(3661) == "1小时01分"


def test_live_heartbeat_reports_working_agent_and_counts():
    view = build_job_activity(
        {
            "status": "running",
            "created_at": 100,
            "updated_at": 190,
            "progress": {
                "heartbeat_at": 198,
                "activity": "4个章节Agent正在编辑",
                "chapters_done": 3,
                "chapters_total": 12,
            },
            "agent_runtime": {"active_agents": 4},
        },
        now=200,
    )
    assert view["tone"] == "working"
    assert view["headline"] == "Agent 正在编辑"
    assert view["active_agents"] == 4
    assert view["chapters_done"] == 3
    assert view["chapters_total"] == 12
    assert view["signal_text"] == "心跳 2 秒前"


def test_running_job_without_new_heartbeat_is_honest_waiting_state():
    view = build_job_activity(
        {
            "status": "running",
            "created_at": 100,
            "updated_at": 110,
            "progress": {"detail": "正在并行编制方案"},
        },
        now=200,
    )
    assert view["tone"] == "waiting"
    assert view["headline"] == "正在等待模型响应"
    assert view["has_heartbeat"] is False
    assert view["elapsed_text"] == "1分40秒"
