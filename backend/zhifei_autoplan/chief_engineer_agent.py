from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, TextIO
from urllib.request import Request, urlopen

import fcntl


_START_LOCK = threading.Lock()
_AGENT_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()
_PROCESS_LOCK_FH: TextIO | None = None
_RECENT_LIMIT = 6


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_dir() -> Path:
    root = _project_root()
    p = root / ".runtime" / "docgen"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _to_int(v: str | None, default: int) -> int:
    try:
        return int(str(v or "").strip())
    except Exception:
        return default


def _log_file() -> Path:
    root = _project_root()
    p = root / "logs" / "chief_engineer_agent.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _state_file() -> Path:
    return _runtime_dir() / "chief_engineer_state.json"


def _lock_file() -> Path:
    return _runtime_dir() / "chief_engineer_agent.lock"


def load_chief_engineer_state() -> Dict[str, Any]:
    path = _state_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_recent_items(items: Any, *, limit: int = _RECENT_LIMIT) -> Deque[Dict[str, Any]]:
    out: Deque[Dict[str, Any]] = deque(maxlen=max(1, int(limit or _RECENT_LIMIT)))
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "timestamp": str(item.get("timestamp") or "").strip(),
                "kind": str(item.get("kind") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
            }
        )
    return out


def _push_recent_event(events: Deque[Dict[str, Any]], *, kind: str, summary: str) -> None:
    text = str(summary or "").strip()
    if not text:
        return
    if events and events[-1].get("kind") == str(kind or "").strip() and events[-1].get("summary") == text:
        return
    item = {
        "timestamp": _now(),
        "kind": str(kind or "").strip() or "info",
        "summary": text,
    }
    events.append(item)


def _try_acquire_process_lock() -> bool:
    global _PROCESS_LOCK_FH
    if _PROCESS_LOCK_FH is not None:
        return True
    try:
        fh = _lock_file().open("a+", encoding="utf-8")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _PROCESS_LOCK_FH = fh
        return True
    except Exception:
        try:
            fh.close()  # type: ignore[name-defined]
        except Exception:
            pass
        return False


def _append_log(msg: str) -> None:
    try:
        with _log_file().open("a", encoding="utf-8") as f:
            f.write(f"[{_now()}] {msg}\n")
    except Exception:
        pass


def _write_state(
    *,
    backend_listener: int,
    web_listener: int,
    backend_health: int,
    web_health: int,
    action: str,
    maintenance: Dict[str, Any] | None = None,
    recent: list[Dict[str, Any]] | None = None,
) -> None:
    payload = {
        "timestamp": _now(),
        "backend_listener": int(backend_listener),
        "web_listener": int(web_listener),
        "backend_health": int(backend_health),
        "web_health": int(web_health),
        "last_action": str(action),
    }
    if isinstance(maintenance, dict) and maintenance:
        payload["maintenance"] = maintenance
    if isinstance(recent, list) and recent:
        payload["recent"] = recent
    try:
        _state_file().write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _to_bool(v: str | None, default: bool = False) -> bool:
    s = str(v or "").strip().lower()
    if not s:
        return default
    return s in {"1", "true", "yes", "on", "y"}


def _port_listening(host: str, port: int, timeout: float = 1.2) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, int(port))) == 0
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            code = int(getattr(resp, "status", 200))
            return 200 <= code < 400
    except Exception:
        return False


def _web_http_ok(host: str, port: int, timeout: float = 3.0) -> bool:
    return _http_ok(f"http://{host}:{int(port)}/_stcore/health", timeout=timeout)


def _web_pid_file() -> Path:
    return _runtime_dir() / "streamlit.pid"


def _web_start_grace_active(grace_seconds: int) -> bool:
    grace = max(0, int(grace_seconds or 0))
    if grace <= 0:
        return False
    path = _web_pid_file()
    if not path.exists():
        return False
    try:
        age = max(0.0, time.time() - float(path.stat().st_mtime))
    except Exception:
        return False
    return age <= float(grace)


def _kill_listener_on_port(port: int) -> None:
    try:
        out = subprocess.check_output(
            ["lsof", "-tiTCP:%d" % int(port), "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        out = ""
    for line in out.splitlines():
        p = line.strip()
        if not p:
            continue
        try:
            os.kill(int(p), 15)
        except Exception:
            continue


def _start_streamlit() -> None:
    root = _project_root()
    pid_file = _runtime_dir() / "streamlit.pid"
    python = sys_exe = os.environ.get("PYTHON_EXECUTABLE_OVERRIDE") or ""
    if not python:
        python = sys_exe = os.environ.get("VIRTUAL_ENV", "")
    if python and Path(python).is_dir():
        py = Path(python) / "bin" / "python3"
        python = str(py) if py.exists() else ""
    if not python:
        python = os.environ.get("PYTHON", "")
    if not python:
        import sys

        python = sys.executable
    app_path = root / "app.py"
    out_log = root / "logs" / "streamlit.out.log"
    err_log = root / "logs" / "streamlit.err.log"
    out_log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(root))
    env.setdefault("ZF_SYSTEM_ID", "docgen-system")
    env.setdefault("ZF_BACKEND_BASE_URL", f"http://127.0.0.1:{_to_int(os.environ.get('ZF_BACKEND_PORT') or os.environ.get('BACKEND_PORT'), 8010)}")
    with out_log.open("ab") as so, err_log.open("ab") as se:
        proc = subprocess.Popen(
            [
                python,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(_to_int(os.environ.get("ZF_WEB_PORT") or os.environ.get("WEB_PORT"), 8501)),
                "--server.headless",
                "true",
                "--server.fileWatcherType",
                "none",
                "--server.runOnSave",
                "false",
            ],
            cwd=str(root),
            env=env,
            stdout=so,
            stderr=se,
            start_new_session=True,
        )
    try:
        pid_file.write_text(str(int(proc.pid)), encoding="utf-8")
    except Exception:
        pass


def _run_job_housekeeping() -> Dict[str, Any]:
    from backend.zhifei_autoplan.job_store import cleanup_jobs, mark_stale_running_jobs

    lease_seconds = max(60, _to_int(os.environ.get("ZF_JOB_LEASE_SECONDS"), 900))
    scan_limit = max(10, _to_int(os.environ.get("ZF_STALE_SCAN_LIMIT"), 2000))
    retention_seconds = max(3600, _to_int(os.environ.get("ZF_JOB_RETENTION_SECONDS"), 14 * 24 * 3600))
    archive_enabled = _to_bool(os.environ.get("ZF_JOB_ARCHIVE"), default=True)
    stale_fixed = int(mark_stale_running_jobs(lease_seconds=lease_seconds, limit=scan_limit) or 0)
    removed = int(cleanup_jobs(older_than_seconds=retention_seconds, archive=archive_enabled) or 0)
    return {
        "lease_seconds": lease_seconds,
        "scan_limit": scan_limit,
        "retention_seconds": retention_seconds,
        "archive_enabled": archive_enabled,
        "stale_fixed": stale_fixed,
        "removed": removed,
        "changed": bool(stale_fixed or removed),
    }


def _run_self_evolution_maintenance() -> Dict[str, Any]:
    from backend.zhifei_autoplan.self_evolution import run_self_evolution_maintenance

    out = run_self_evolution_maintenance()
    runtime = out.get("runtime_budget_profile") if isinstance(out.get("runtime_budget_profile"), dict) else {}
    task = out.get("task_parallelism_profile") if isinstance(out.get("task_parallelism_profile"), dict) else {}
    return {
        "enabled": bool(out.get("enabled", False)),
        "runtime_budget_profile": {
            "changed": bool(runtime.get("changed", False)),
            "entry_count": int(runtime.get("entry_count") or 0),
            "maintenance": runtime.get("maintenance") if isinstance(runtime.get("maintenance"), dict) else {},
        },
        "task_parallelism_profile": {
            "changed": bool(task.get("changed", False)),
            "entry_count": int(task.get("entry_count") or 0),
            "maintenance": task.get("maintenance") if isinstance(task.get("maintenance"), dict) else {},
        },
    }


def _loop() -> None:
    backend_host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    backend_port = _to_int(os.environ.get("ZF_BACKEND_PORT") or os.environ.get("BACKEND_PORT"), 8010)
    web_host = os.environ.get("WEB_HOST", "127.0.0.1")
    web_port = _to_int(os.environ.get("ZF_WEB_PORT") or os.environ.get("WEB_PORT"), 8501)
    interval = max(3, _to_int(os.environ.get("ZF_WATCHDOG_INTERVAL"), 8))
    max_restarts = max(1, _to_int(os.environ.get("ZF_MAX_RESTARTS_PER_HOUR"), 10))
    web_start_grace_seconds = max(interval, _to_int(os.environ.get("ZF_WEB_START_GRACE_SECONDS"), 90))
    housekeep_interval = max(60, _to_int(os.environ.get("ZF_CHIEF_HOUSEKEEP_INTERVAL"), 300))
    evolution_interval = max(120, _to_int(os.environ.get("ZF_CHIEF_EVOLUTION_INTERVAL"), 900))
    restart_hist: Deque[float] = deque(maxlen=256)
    previous_state = load_chief_engineer_state()
    recent_events = _coerce_recent_items(previous_state.get("recent"))
    last_housekeep_ts = 0.0
    last_evolution_ts = 0.0
    maintenance_state: Dict[str, Any] = {}
    _append_log(
        "chief-engineer agent started "
        f"(backend={backend_host}:{backend_port}, web={web_host}:{web_port}, interval={interval}s, "
        f"housekeep={housekeep_interval}s, evolution={evolution_interval}s)"
    )

    while not _STOP_EVENT.is_set():
        now_ts = time.time()
        backend_listener = 1 if _port_listening(backend_host, backend_port) else 0
        web_listener = 1 if _port_listening(web_host, web_port) else 0
        backend_health = 1 if _http_ok(f"http://{backend_host}:{backend_port}/health") else 0
        web_health = 1 if _web_http_ok(web_host, web_port) else 0
        action = "noop"

        if (web_listener == 0) or (web_health == 0):
            if _web_start_grace_active(web_start_grace_seconds):
                action = "wait_web_grace"
            else:
                while restart_hist and (now_ts - restart_hist[0]) > 3600:
                    restart_hist.popleft()
                if len(restart_hist) >= max_restarts:
                    action = "throttled"
                    _append_log(f"restart throttled ({len(restart_hist)}/{max_restarts} per hour)")
                    _push_recent_event(
                        recent_events,
                        kind="restart_throttled",
                        summary=f"restart throttled ({len(restart_hist)}/{max_restarts} per hour)",
                    )
                else:
                    action = "restart_web_ui"
                    _append_log(
                        "web unhealthy -> restart "
                        f"(backend_listener={backend_listener}, web_listener={web_listener}, "
                        f"backend_health={backend_health}, web_health={web_health})"
                    )
                    _push_recent_event(
                        recent_events,
                        kind="restart_web_ui",
                        summary=(
                            "web unhealthy -> restart "
                            f"(backend_listener={backend_listener}, web_listener={web_listener}, "
                            f"backend_health={backend_health}, web_health={web_health})"
                        ),
                    )
                    _kill_listener_on_port(web_port)
                    _start_streamlit()
                    restart_hist.append(now_ts)

        if (now_ts - last_housekeep_ts) >= float(housekeep_interval):
            try:
                report = _run_job_housekeeping()
                maintenance_state["job_housekeep"] = report
                last_housekeep_ts = now_ts
                if report.get("changed"):
                    _append_log(
                        "job housekeep applied "
                        f"(stale_fixed={int(report.get('stale_fixed') or 0)}, removed={int(report.get('removed') or 0)})"
                    )
                    _push_recent_event(
                        recent_events,
                        kind="job_housekeep",
                        summary=(
                            "job housekeep applied "
                            f"(stale_fixed={int(report.get('stale_fixed') or 0)}, removed={int(report.get('removed') or 0)})"
                        ),
                    )
            except Exception as e:
                maintenance_state["job_housekeep"] = {"error": repr(e)}
                last_housekeep_ts = now_ts
                _append_log(f"job housekeep failed: {repr(e)}")
                _push_recent_event(
                    recent_events,
                    kind="job_housekeep_error",
                    summary=f"job housekeep failed: {repr(e)}",
                )

        if (now_ts - last_evolution_ts) >= float(evolution_interval):
            try:
                report = _run_self_evolution_maintenance()
                maintenance_state["self_evolution"] = report
                last_evolution_ts = now_ts
                runtime_changed = bool(((report.get("runtime_budget_profile") or {}).get("changed")))
                task_changed = bool(((report.get("task_parallelism_profile") or {}).get("changed")))
                if runtime_changed or task_changed:
                    _append_log(
                        "self_evolution maintenance applied "
                        f"(runtime_changed={runtime_changed}, task_changed={task_changed})"
                    )
                    _push_recent_event(
                        recent_events,
                        kind="self_evolution_maintenance",
                        summary=(
                            "self_evolution maintenance applied "
                            f"(runtime_changed={runtime_changed}, task_changed={task_changed})"
                        ),
                    )
            except Exception as e:
                maintenance_state["self_evolution"] = {"error": repr(e)}
                last_evolution_ts = now_ts
                _append_log(f"self_evolution maintenance failed: {repr(e)}")
                _push_recent_event(
                    recent_events,
                    kind="self_evolution_error",
                    summary=f"self_evolution maintenance failed: {repr(e)}",
                )

        _write_state(
            backend_listener=backend_listener,
            web_listener=web_listener,
            backend_health=backend_health,
            web_health=web_health,
            action=action,
            maintenance=maintenance_state,
            recent=list(recent_events),
        )
        _STOP_EVENT.wait(interval)

    _append_log("chief-engineer agent stopped")


def start_chief_engineer_agent() -> None:
    global _AGENT_THREAD
    if str(os.environ.get("ZF_ENABLE_CHIEF_AGENT", "1")).strip().lower() in {"0", "false", "off", "no"}:
        return
    with _START_LOCK:
        if _AGENT_THREAD and _AGENT_THREAD.is_alive():
            return
        if not _try_acquire_process_lock():
            _append_log("chief-engineer agent skipped: process lock already held")
            return
        _STOP_EVENT.clear()
        _AGENT_THREAD = threading.Thread(target=_loop, daemon=True, name="chief-engineer-agent")
        _AGENT_THREAD.start()
