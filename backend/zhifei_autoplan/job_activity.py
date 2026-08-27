from __future__ import annotations

import time
from typing import Any, Dict


def format_duration(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except Exception:
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes:02d}分"
    if minutes:
        return f"{minutes}分{secs:02d}秒"
    return f"{secs}秒"


def build_job_activity(job: Dict[str, Any], *, now: float | None = None) -> Dict[str, Any]:
    current = float(now if now is not None else time.time())
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    runtime = job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {}
    created_at = float(job.get("created_at") or current)
    heartbeat_at = float(progress.get("heartbeat_at") or 0)
    updated_at = float(job.get("updated_at") or created_at)
    last_signal = heartbeat_at or updated_at
    signal_age = max(0, int(current - last_signal))
    elapsed = max(0, int(current - created_at))
    status = str(job.get("status") or "").strip().lower()
    work_state = str(progress.get("work_state") or "").strip().lower()

    activity = str(progress.get("activity") or progress.get("detail") or "").strip()
    active_agents = max(0, int(runtime.get("active_agents") or 0))
    chapters_done = max(0, int(progress.get("chapters_done") or runtime.get("chapters_done") or 0))
    chapters_total = max(0, int(progress.get("chapters_total") or runtime.get("chapters_total") or 0))

    has_heartbeat = heartbeat_at > 0
    if status == "queued":
        activity = "任务正在等待本地工作进程接收"
        tone = "waiting"
        headline = "任务已进入队列"
        signal_text = f"状态更新 {format_duration(signal_age)} 前"
    elif status == "cancel_requested":
        activity = "正在等待工作进程确认取消并封存检查点"
        tone = "waiting"
        headline = "取消请求已提交，正在安全停止"
        signal_text = (
            f"心跳 {signal_age} 秒前"
            if has_heartbeat
            else f"状态更新 {format_duration(signal_age)} 前"
        )
    elif status == "running" and work_state == "waiting_provider":
        tone = "waiting"
        headline = "正在等待模型响应"
        signal_text = f"心跳 {signal_age} 秒前" if has_heartbeat else f"状态更新 {format_duration(signal_age)} 前"
    elif status == "running" and work_state == "retry_backoff":
        tone = "waiting"
        headline = "模型限流，正在有限退避"
        signal_text = f"心跳 {signal_age} 秒前" if has_heartbeat else f"状态更新 {format_duration(signal_age)} 前"
    elif status == "running" and work_state == "checkpointing":
        tone = "working"
        headline = "正在保存可信检查点"
        signal_text = f"心跳 {signal_age} 秒前" if has_heartbeat else f"状态更新 {format_duration(signal_age)} 前"
    elif status == "running" and has_heartbeat and signal_age <= 15:
        tone = "working"
        headline = "任务正在处理"
        signal_text = f"心跳 {signal_age} 秒前"
    elif status == "running" and has_heartbeat and signal_age <= 60:
        tone = "waiting"
        headline = "正在等待模型响应"
        signal_text = f"心跳 {signal_age} 秒前"
    elif status == "running" and has_heartbeat:
        tone = "stale"
        headline = "任务仍在运行，心跳延迟"
        signal_text = f"最后心跳 {format_duration(signal_age)} 前"
    elif status == "running":
        tone = "waiting"
        headline = "任务正在处理，等待新的运行信号"
        signal_text = f"状态更新 {format_duration(signal_age)} 前"
    else:
        tone = "idle"
        headline = status or "未知状态"
        signal_text = f"状态更新 {format_duration(signal_age)} 前"

    if not activity:
        activity = {
            "queued": "任务正在等待本地工作进程接收",
            "cancel_requested": "正在等待工作进程确认取消并封存检查点",
            "running": "任务正在等待新的运行信号",
            "succeeded": "任务已完成",
            "done": "任务已完成",
            "failed": "任务已失败",
            "cancelled": "任务已取消",
            "interrupted": "任务已中断，检查点可用于恢复",
            "interrupted_recoverable": "任务已中断，检查点可用于恢复",
        }.get(status, "当前没有可确认的运行活动")

    return {
        "tone": tone,
        "headline": headline,
        "activity": activity,
        "elapsed_seconds": elapsed,
        "elapsed_text": format_duration(elapsed),
        "signal_age_seconds": signal_age,
        "signal_text": signal_text,
        "has_heartbeat": has_heartbeat,
        "work_state": work_state or (
            status if status in {"queued", "cancel_requested"} else "idle"
        ),
        "active_agents": active_agents,
        "chapters_done": chapters_done,
        "chapters_total": chapters_total,
    }
