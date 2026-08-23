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

    activity = str(progress.get("activity") or progress.get("detail") or "").strip()
    active_agents = max(0, int(runtime.get("active_agents") or 0))
    chapters_done = max(0, int(progress.get("chapters_done") or runtime.get("chapters_done") or 0))
    chapters_total = max(0, int(progress.get("chapters_total") or runtime.get("chapters_total") or 0))

    has_heartbeat = heartbeat_at > 0
    if status in {"queued", "running"} and has_heartbeat and signal_age <= 15:
        tone = "working"
        headline = "Agent 正在编辑"
        signal_text = f"心跳 {signal_age} 秒前"
    elif status in {"queued", "running"} and has_heartbeat and signal_age <= 60:
        tone = "waiting"
        headline = "正在等待模型响应"
        signal_text = f"心跳 {signal_age} 秒前"
    elif status in {"queued", "running"} and has_heartbeat:
        tone = "stale"
        headline = "任务仍在运行，心跳延迟"
        signal_text = f"最后心跳 {format_duration(signal_age)} 前"
    elif status in {"queued", "running"}:
        tone = "waiting"
        headline = "正在等待模型响应"
        signal_text = f"状态更新 {format_duration(signal_age)} 前"
    else:
        tone = "idle"
        headline = status or "未知状态"
        signal_text = f"状态更新 {format_duration(signal_age)} 前"

    if not activity:
        activity = "主控Agent已分派任务，正在等待章节Agent返回结果"

    return {
        "tone": tone,
        "headline": headline,
        "activity": activity,
        "elapsed_seconds": elapsed,
        "elapsed_text": format_duration(elapsed),
        "signal_age_seconds": signal_age,
        "signal_text": signal_text,
        "has_heartbeat": has_heartbeat,
        "active_agents": active_agents,
        "chapters_done": chapters_done,
        "chapters_total": chapters_total,
    }
