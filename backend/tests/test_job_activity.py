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
    assert view["headline"] == "任务正在处理"
    assert view["active_agents"] == 4
    assert view["chapters_done"] == 3
    assert view["chapters_total"] == 12
    assert view["signal_text"] == "心跳 2 秒前"


def test_live_heartbeat_reports_provider_wait_instead_of_editing():
    view = build_job_activity(
        {
            "status": "running",
            "created_at": 100,
            "updated_at": 198,
            "progress": {
                "heartbeat_at": 199,
                "work_state": "waiting_provider",
                "activity": "正在等待模型响应",
            },
        },
        now=200,
    )
    assert view["tone"] == "waiting"
    assert view["headline"] == "正在等待模型响应"
    assert view["work_state"] == "waiting_provider"


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
    assert view["headline"] == "任务正在处理，等待新的运行信号"
    assert view["has_heartbeat"] is False
    assert view["elapsed_text"] == "1分40秒"


def test_queued_job_is_not_misreported_as_waiting_for_model():
    view = build_job_activity(
        {
            "status": "queued",
            "created_at": 100,
            "updated_at": 195,
            "progress": {"activity": "正在等待模型响应"},
        },
        now=200,
    )

    assert view["tone"] == "waiting"
    assert view["headline"] == "任务已进入队列"
    assert view["activity"] == "任务正在等待本地工作进程接收"
    assert view["work_state"] == "queued"


def test_cancel_requested_is_an_active_safe_stop_state():
    view = build_job_activity(
        {
            "status": "cancel_requested",
            "created_at": 100,
            "updated_at": 198,
            "progress": {
                "heartbeat_at": 199,
                "activity": "4个章节Agent正在编辑",
            },
        },
        now=200,
    )

    assert view["tone"] == "waiting"
    assert view["headline"] == "取消请求已提交，正在安全停止"
    assert view["activity"] == "正在等待工作进程确认取消并封存检查点"
    assert view["signal_text"] == "心跳 1 秒前"
    assert view["work_state"] == "cancel_requested"
