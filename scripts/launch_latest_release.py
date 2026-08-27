#!/usr/bin/env python3
"""Verify and launch exactly the immutable release selected by current.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_local_release import default_release_base
from scripts.runtime_supervisor import (
    ExpectedIdentity,
    SupervisorError,
    compute_runtime_digest,
    verify_release_manifest,
)

CURRENT_FIELDS = {
    "schema_version",
    "system_id",
    "release_id",
    "manifest_digest",
    "source_digest",
    "runtime_digest",
    "release_dir",
    "python_executable",
    "env_file",
    "state_dir",
    "log_dir",
    "backend_port",
    "ui_port",
}
RUNNING_IDENTITY_FIELDS = (
    "release_id",
    "manifest_digest",
    "source_digest",
    "runtime_digest",
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SUPERVISOR_START_COMMAND_TIMEOUT_SECONDS = 120.0
SUPERVISOR_ADOPTION_POLL_SECONDS = 2.0


class LaunchError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CurrentSnapshot:
    path: Path
    raw_bytes: bytes
    raw_digest: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ReleaseSpec:
    base: Path
    release_dir: Path
    python_executable: Path
    supervisor_script: Path
    env_file: Path
    state_dir: Path
    log_dir: Path
    backend_port: int
    ui_port: int
    identity: ExpectedIdentity


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[Sequence[str], Path, float], CommandResult]
HttpGetter = Callable[[str, float], tuple[int, bytes]]
Execve = Callable[[str, Sequence[str], Mapping[str, str]], Any]


def load_current_snapshot(path: Path) -> CurrentSnapshot:
    path = Path(os.path.abspath(os.fspath(path)))
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or path.is_symlink()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 128 * 1024
        ):
            raise LaunchError(
                "LAUNCH_CURRENT_UNTRUSTED", "current.json 权限、类型或大小不可信"
            )
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise LaunchError("LAUNCH_CURRENT_MISSING", "尚未构建不可变本地发布") from exc
    except OSError as exc:
        raise LaunchError("LAUNCH_CURRENT_UNREADABLE", "current.json 无法读取") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise LaunchError("LAUNCH_CURRENT_INVALID", "current.json 不是有效UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise LaunchError("LAUNCH_CURRENT_INVALID", "current.json schema_version 必须为1")
    if set(payload) != CURRENT_FIELDS:
        raise LaunchError("LAUNCH_CURRENT_INVALID", "current.json 字段集合不完整或包含未知字段")
    return CurrentSnapshot(
        path=path,
        raw_bytes=raw,
        raw_digest=hashlib.sha256(raw).hexdigest(),
        payload=payload,
    )


def _absolute_exact(value: Any, expected: Path, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise LaunchError("LAUNCH_CURRENT_INVALID", f"current.json {field} 无效")
    candidate = Path(value)
    if not candidate.is_absolute() or candidate != expected:
        raise LaunchError("LAUNCH_PATH_MISMATCH", f"current.json {field} 未绑定固定发布路径")
    return candidate


def parse_release_spec(snapshot: CurrentSnapshot, base: Path) -> ReleaseSpec:
    base = Path(os.path.abspath(os.fspath(base)))
    try:
        base_info = base.lstat()
    except OSError as exc:
        raise LaunchError("LAUNCH_BASE_UNTRUSTED", "不可变发布基础目录不可用") from exc
    if (
        not stat.S_ISDIR(base_info.st_mode)
        or base.is_symlink()
        or base_info.st_uid != os.getuid()
        or stat.S_IMODE(base_info.st_mode) != 0o700
    ):
        raise LaunchError("LAUNCH_BASE_UNTRUSTED", "不可变发布基础目录权限或类型不可信")
    payload = snapshot.payload
    identity = ExpectedIdentity(
        system_id=str(payload.get("system_id") or ""),
        release_id=str(payload.get("release_id") or ""),
        manifest_digest=str(payload.get("manifest_digest") or ""),
        source_digest=str(payload.get("source_digest") or ""),
        runtime_digest=str(payload.get("runtime_digest") or ""),
    )
    identity.validate()
    release_dir = _absolute_exact(
        payload.get("release_dir"),
        base / "releases" / identity.release_id,
        "release_dir",
    )
    if not release_dir.is_dir() or release_dir.is_symlink():
        raise LaunchError("LAUNCH_RELEASE_UNTRUSTED", "发布目录不存在或为符号链接")
    release_info = release_dir.lstat()
    if release_info.st_uid != os.getuid() or stat.S_IMODE(release_info.st_mode) & 0o222:
        raise LaunchError("LAUNCH_RELEASE_UNTRUSTED", "发布目录并非当前用户只读封存")
    runtime_root = base / "runtimes" / identity.runtime_digest / "venv"
    python_executable = Path(str(payload.get("python_executable") or ""))
    if (
        not python_executable.is_absolute()
        or python_executable.parent != runtime_root / "bin"
        or python_executable.name not in {"python", "python3"}
    ):
        raise LaunchError("LAUNCH_RUNTIME_PATH_MISMATCH", "Python未绑定摘要运行时目录")
    env_file = _absolute_exact(payload.get("env_file"), base / "secrets" / "runtime.env", "env_file")
    state_dir = _absolute_exact(payload.get("state_dir"), base / "state" / "supervisor", "state_dir")
    log_dir = _absolute_exact(payload.get("log_dir"), state_dir / "logs", "log_dir")
    try:
        env_info = env_file.lstat()
        state_info = state_dir.lstat()
        log_info = log_dir.lstat()
    except OSError as exc:
        raise LaunchError("LAUNCH_RUNTIME_PATH_UNAVAILABLE", "密钥或监管状态目录不可用") from exc
    if (
        not stat.S_ISREG(env_info.st_mode)
        or env_file.is_symlink()
        or env_info.st_uid != os.getuid()
        or stat.S_IMODE(env_info.st_mode) != 0o600
    ):
        raise LaunchError("LAUNCH_ENV_UNTRUSTED", "监管环境文件权限或类型不可信")
    for path, info in ((state_dir, state_info), (log_dir, log_info)):
        if (
            not stat.S_ISDIR(info.st_mode)
            or path.is_symlink()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise LaunchError("LAUNCH_STATE_UNTRUSTED", "监管状态目录权限或类型不可信")
    try:
        backend_port = int(payload.get("backend_port"))
        ui_port = int(payload.get("ui_port"))
    except (TypeError, ValueError) as exc:
        raise LaunchError("LAUNCH_PORT_INVALID", "current.json 端口无效") from exc
    if (
        backend_port == ui_port
        or not 1 <= backend_port <= 65535
        or not 1 <= ui_port <= 65535
    ):
        raise LaunchError("LAUNCH_PORT_INVALID", "current.json 端口无效")

    current_link = base / "current"
    try:
        if not current_link.is_symlink() or os.readlink(current_link) != str(release_dir):
            raise LaunchError(
                "LAUNCH_CURRENT_POINTER_MISMATCH", "current与current.json未指向同一发布"
            )
    except OSError as exc:
        raise LaunchError("LAUNCH_CURRENT_POINTER_MISMATCH", "current链接无法核验") from exc

    supervisor_script = release_dir / "scripts" / "runtime_supervisor.py"
    if not supervisor_script.is_file() or supervisor_script.is_symlink():
        raise LaunchError("LAUNCH_SUPERVISOR_MISSING", "冻结发布缺少监管器入口")
    return ReleaseSpec(
        base=base,
        release_dir=release_dir,
        python_executable=python_executable,
        supervisor_script=supervisor_script,
        env_file=env_file,
        state_dir=state_dir,
        log_dir=log_dir,
        backend_port=backend_port,
        ui_port=ui_port,
        identity=identity,
    )


def preflight_release(
    spec: ReleaseSpec,
    *,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
) -> None:
    verify_fn(spec.release_dir, spec.identity)
    if runtime_digest_fn(spec.python_executable) != spec.identity.runtime_digest:
        raise LaunchError("LAUNCH_RUNTIME_DIGEST_MISMATCH", "运行时摘要反向校验失败")


def build_status_argv(spec: ReleaseSpec) -> list[str]:
    return [
        str(spec.python_executable),
        str(spec.supervisor_script),
        "status",
        "--state-dir",
        str(spec.state_dir),
    ]


def build_start_argv(spec: ReleaseSpec) -> list[str]:
    return [
        str(spec.python_executable),
        str(spec.supervisor_script),
        "start",
        "--release-dir",
        str(spec.release_dir),
        "--python",
        str(spec.python_executable),
        "--backend-port",
        str(spec.backend_port),
        "--ui-port",
        str(spec.ui_port),
        "--expected-system-id",
        spec.identity.system_id,
        "--expected-release-id",
        spec.identity.release_id,
        "--expected-manifest-digest",
        spec.identity.manifest_digest,
        "--expected-source-digest",
        spec.identity.source_digest,
        "--expected-runtime-digest",
        spec.identity.runtime_digest,
        "--state-dir",
        str(spec.state_dir),
        "--log-dir",
        str(spec.log_dir),
        "--env-file",
        str(spec.env_file),
    ]


def build_stop_argv(spec: ReleaseSpec) -> list[str]:
    return [
        str(spec.python_executable),
        str(spec.supervisor_script),
        "stop",
        "--state-dir",
        str(spec.state_dir),
    ]


def build_run_argv(spec: ReleaseSpec) -> list[str]:
    argv = build_start_argv(spec)
    argv[2] = "run"
    return argv


def _default_runner(argv: Sequence[str], cwd: Path, timeout: float) -> CommandResult:
    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LaunchError("LAUNCH_SUPERVISOR_COMMAND_FAILED", "监管器命令执行失败") from exc
    if len(completed.stdout) + len(completed.stderr) > 256 * 1024:
        raise LaunchError("LAUNCH_SUPERVISOR_OUTPUT_OVERSIZED", "监管器命令输出超出限制")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _parse_command_payload(result: CommandResult, *, accepted_codes: set[int]) -> dict[str, Any]:
    if len(result.stdout) + len(result.stderr) > 256 * 1024:
        raise LaunchError("LAUNCH_SUPERVISOR_OUTPUT_OVERSIZED", "监管器命令输出超出限制")
    if result.returncode not in accepted_codes:
        raise LaunchError("LAUNCH_SUPERVISOR_COMMAND_REJECTED", "监管器命令未成功完成")
    try:
        payload = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise LaunchError("LAUNCH_SUPERVISOR_OUTPUT_INVALID", "监管器命令未返回有效JSON") from exc
    if not isinstance(payload, dict):
        raise LaunchError("LAUNCH_SUPERVISOR_OUTPUT_INVALID", "监管器命令状态格式无效")
    return payload


def _assert_running_identity(payload: Mapping[str, Any], spec: ReleaseSpec) -> None:
    if payload.get("running") is not True or payload.get("schema_version") != 1:
        raise LaunchError("LAUNCH_RUNNING_STATE_INVALID", "运行中监管状态不完整")
    for field in RUNNING_IDENTITY_FIELDS:
        if str(payload.get(field) or "") != getattr(spec.identity, field):
            raise LaunchError(
                "LAUNCH_RUNNING_RELEASE_MISMATCH", "已有监管器运行的不是当前冻结发布"
            )
    if str(payload.get("release_root") or "") != str(spec.release_dir):
        raise LaunchError(
            "LAUNCH_RUNNING_RELEASE_MISMATCH", "已有监管器发布目录与当前选择不一致"
        )


def _read_status(spec: ReleaseSpec, runner: CommandRunner) -> tuple[int, dict[str, Any]]:
    result = runner(build_status_argv(spec), spec.release_dir, 10.0)
    return result.returncode, _parse_command_payload(result, accepted_codes={0, 3})


def _assert_current_unchanged(snapshot: CurrentSnapshot) -> None:
    latest = load_current_snapshot(snapshot.path)
    if latest.raw_digest != snapshot.raw_digest or latest.raw_bytes != snapshot.raw_bytes:
        raise LaunchError("LAUNCH_CURRENT_CHANGED", "启动期间current.json发生变化，已停止继续操作")
    current_link = snapshot.path.parent / "current"
    expected_release = str(snapshot.payload.get("release_dir") or "")
    try:
        if not current_link.is_symlink() or os.readlink(current_link) != expected_release:
            raise LaunchError("LAUNCH_CURRENT_CHANGED", "操作期间current链接发生变化，已停止继续操作")
    except OSError as exc:
        raise LaunchError("LAUNCH_CURRENT_CHANGED", "操作期间current链接无法核验") from exc


def _default_http_get(url: str, timeout: float) -> tuple[int, bytes]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(1024 * 1024)
    except (OSError, urllib.error.URLError) as exc:
        raise LaunchError("LAUNCH_HEALTH_UNAVAILABLE", "本地服务健康检查不可用") from exc


def _probe_backend(spec: ReleaseSpec, http_get: HttpGetter) -> None:
    status, body = http_get(f"http://127.0.0.1:{spec.backend_port}/health", 3.0)
    if status != 200 or len(body) > 1024 * 1024:
        raise LaunchError("LAUNCH_BACKEND_UNHEALTHY", "后端未通过冻结身份健康检查")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise LaunchError("LAUNCH_BACKEND_UNHEALTHY", "后端健康响应无效") from exc
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise LaunchError("LAUNCH_BACKEND_UNHEALTHY", "后端健康响应未通过")
    for field, expected in spec.identity.as_dict().items():
        if str(payload.get(field) or "") != expected:
            raise LaunchError("LAUNCH_BACKEND_IDENTITY_MISMATCH", "后端身份与当前冻结发布不一致")
    if (
        str(payload.get("release_root") or "") != str(spec.release_dir)
        or payload.get("release_managed") is not True
        or payload.get("runtime_mode") != "sealed_release"
    ):
        raise LaunchError("LAUNCH_BACKEND_IDENTITY_MISMATCH", "后端未以冻结监管模式运行")


def _probe_ui(spec: ReleaseSpec, http_get: HttpGetter) -> None:
    status, _ = http_get(f"http://127.0.0.1:{spec.ui_port}/", 3.0)
    if not 200 <= status < 400:
        raise LaunchError("LAUNCH_UI_UNHEALTHY", "本地界面未通过健康检查")


def _default_browser_opener(url: str) -> None:
    try:
        completed = subprocess.run(
            ["/usr/bin/open", url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LaunchError("LAUNCH_BROWSER_OPEN_FAILED", "系统无法打开本地界面") from exc
    if completed.returncode != 0:
        raise LaunchError("LAUNCH_BROWSER_OPEN_FAILED", "系统无法打开本地界面")


def launch_latest(
    *,
    base: Path,
    timeout_seconds: float = 180.0,
    no_open: bool = False,
    runner: CommandRunner = _default_runner,
    http_get: HttpGetter = _default_http_get,
    browser_opener: Callable[[str], None] = _default_browser_opener,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    base = Path(os.path.abspath(os.fspath(base)))
    snapshot = load_current_snapshot(base / "current.json")
    spec = parse_release_spec(snapshot, base)
    preflight_release(spec, runtime_digest_fn=runtime_digest_fn, verify_fn=verify_fn)

    status_code, status = _read_status(spec, runner)
    start_calls = 0
    if status_code == 0:
        _assert_running_identity(status, spec)
        if status.get("circuit_open") is True:
            raise LaunchError("LAUNCH_RUNNING_STATE_BLOCKED", "监管器熔断已打开，禁止自动继续")
        if status.get("status") not in {
            "starting",
            "restarting",
            "degraded",
            "healthy",
        }:
            raise LaunchError("LAUNCH_RUNNING_STATE_BLOCKED", "已有监管器处于不可继续的运行状态")
    else:
        if status.get("running") is True or status.get("status") not in {
            "not_started",
            "not_running",
            "stopped",
            "failed",
        }:
            raise LaunchError("LAUNCH_STALE_STATE_BLOCKED", "监管状态矛盾或熔断，禁止自动重启")
        _assert_current_unchanged(snapshot)
        # The start wrapper and the detached supervisor both reverse-verify the
        # sealed runtime before the first state write.  A full runtime digest
        # takes longer than the generic command budget on real installations.
        # Keep this timeout above the supervisor's bounded confirmation window
        # so the wrapper, rather than subprocess.run, always owns cleanup.
        start_result = runner(
            build_start_argv(spec),
            spec.release_dir,
            SUPERVISOR_START_COMMAND_TIMEOUT_SECONDS,
        )
        start_payload = _parse_command_payload(start_result, accepted_codes={0})
        if str(start_payload.get("release_id") or "") != spec.identity.release_id:
            raise LaunchError("LAUNCH_START_IDENTITY_MISMATCH", "监管器启动回执身份不匹配")
        start_calls = 1

    deadline = monotonic() + max(1.0, float(timeout_seconds))
    first_healthy: dict[str, Any] | None = None
    while monotonic() < deadline:
        status_code, status = _read_status(spec, runner)
        if status_code != 0:
            raise LaunchError("LAUNCH_SUPERVISOR_STOPPED", "监管器在健康确认前停止")
        _assert_running_identity(status, spec)
        state = str(status.get("status") or "")
        if state in {"failed", "stopped", "stopping", "circuit_open"}:
            raise LaunchError("LAUNCH_RUNNING_STATE_BLOCKED", "监管器未达到健康终态")
        if state == "healthy":
            first_healthy = dict(status)
            break
        if state not in {"starting", "restarting", "degraded"}:
            raise LaunchError("LAUNCH_RUNNING_STATE_INVALID", "监管器返回未知运行状态")
        sleep(0.2)
    if first_healthy is None:
        raise LaunchError("LAUNCH_HEALTH_TIMEOUT", "本地冻结发布未在期限内达到健康状态")

    _probe_backend(spec, http_get)
    _probe_ui(spec, http_get)
    final_code, final_status = _read_status(spec, runner)
    if final_code != 0:
        raise LaunchError("LAUNCH_SUPERVISOR_STOPPED", "监管器在最终确认前停止")
    _assert_running_identity(final_status, spec)
    if final_status.get("status") != "healthy":
        raise LaunchError("LAUNCH_HEALTH_CHANGED", "监管器健康状态在确认期间发生变化")
    for field in ("supervisor_instance_id", "backend_pid", "ui_pid"):
        if final_status.get(field) != first_healthy.get(field):
            raise LaunchError("LAUNCH_HEALTH_CHANGED", "监管进程在确认期间发生变化")
    _assert_current_unchanged(snapshot)

    url = f"http://127.0.0.1:{spec.ui_port}"
    if not no_open:
        browser_opener(url)
    return {
        "ok": True,
        "status": "healthy",
        "release_id": spec.identity.release_id,
        "manifest_digest": spec.identity.manifest_digest,
        "source_digest": spec.identity.source_digest,
        "runtime_digest": spec.identity.runtime_digest,
        "url": url,
        "start_calls": start_calls,
    }


def status_latest(
    *,
    base: Path,
    runner: CommandRunner = _default_runner,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
) -> dict[str, Any]:
    base = Path(os.path.abspath(os.fspath(base)))
    snapshot = load_current_snapshot(base / "current.json")
    spec = parse_release_spec(snapshot, base)
    preflight_release(spec, runtime_digest_fn=runtime_digest_fn, verify_fn=verify_fn)
    status_code, payload = _read_status(spec, runner)
    if status_code == 0:
        _assert_running_identity(payload, spec)
    elif payload.get("running") is True:
        raise LaunchError("LAUNCH_STALE_STATE_BLOCKED", "监管状态矛盾，禁止继续操作")
    _assert_current_unchanged(snapshot)
    return {
        "ok": True,
        "status": str(payload.get("status") or "not_running"),
        "running": status_code == 0,
        "release_id": spec.identity.release_id,
        "manifest_digest": spec.identity.manifest_digest,
        "source_digest": spec.identity.source_digest,
        "runtime_digest": spec.identity.runtime_digest,
    }


def stop_latest(
    *,
    base: Path,
    runner: CommandRunner = _default_runner,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
) -> dict[str, Any]:
    base = Path(os.path.abspath(os.fspath(base)))
    snapshot = load_current_snapshot(base / "current.json")
    spec = parse_release_spec(snapshot, base)
    preflight_release(spec, runtime_digest_fn=runtime_digest_fn, verify_fn=verify_fn)
    status_code, payload = _read_status(spec, runner)
    if status_code != 0:
        if payload.get("running") is True:
            raise LaunchError("LAUNCH_STALE_STATE_BLOCKED", "监管状态矛盾，禁止停止任何进程")
        _assert_current_unchanged(snapshot)
        return {
            "ok": True,
            "status": "not_running",
            "release_id": spec.identity.release_id,
            "stop_calls": 0,
        }
    _assert_running_identity(payload, spec)
    _assert_current_unchanged(snapshot)
    stop_result = runner(build_stop_argv(spec), spec.release_dir, 30.0)
    stop_payload = _parse_command_payload(stop_result, accepted_codes={0})
    if stop_payload.get("status") not in {"stopped", "not_running"}:
        raise LaunchError("LAUNCH_STOP_RESULT_INVALID", "监管器停止回执无效")
    _assert_current_unchanged(snapshot)
    return {
        "ok": True,
        "status": str(stop_payload["status"]),
        "release_id": spec.identity.release_id,
        "stop_calls": 1,
    }


def _minimal_supervisor_environment() -> dict[str, str]:
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError) as exc:
        raise LaunchError("LAUNCH_HOME_UNAVAILABLE", "系统用户主目录无法核验") from exc
    environment: dict[str, str] = {
        "HOME": str(home),
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
    }
    for name in ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "USER", "LOGNAME"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def supervise_latest(
    *,
    base: Path,
    runner: CommandRunner = _default_runner,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
    execve_fn: Execve = os.execve,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Adopt ownership, then replace this process with the foreground supervisor.

    A pre-existing, identity-verified detached supervisor may have been started
    by the desktop launcher before the LaunchAgent was installed.  Exiting in
    that state makes ``KeepAlive`` relaunch this bootstrap forever.  Waiting is
    both safer for active jobs and lets launchd take ownership automatically as
    soon as the verified detached supervisor stops.
    """

    base = Path(os.path.abspath(os.fspath(base)))
    snapshot = load_current_snapshot(base / "current.json")
    spec = parse_release_spec(snapshot, base)
    preflight_release(spec, runtime_digest_fn=runtime_digest_fn, verify_fn=verify_fn)

    while True:
        status_code, payload = _read_status(spec, runner)
        if status_code == 0:
            try:
                _assert_running_identity(payload, spec)
            except LaunchError:
                latest = load_current_snapshot(base / "current.json")
                if (
                    latest.raw_digest == snapshot.raw_digest
                    and latest.raw_bytes == snapshot.raw_bytes
                ):
                    raise
                snapshot = latest
                spec = parse_release_spec(snapshot, base)
                preflight_release(
                    spec,
                    runtime_digest_fn=runtime_digest_fn,
                    verify_fn=verify_fn,
                )
                continue
            sleep(SUPERVISOR_ADOPTION_POLL_SECONDS)
            continue
        if payload.get("running") is True:
            raise LaunchError(
                "LAUNCH_STALE_STATE_BLOCKED", "监管状态矛盾，禁止启动第二个监管器"
            )

        latest = load_current_snapshot(base / "current.json")
        if (
            latest.raw_digest != snapshot.raw_digest
            or latest.raw_bytes != snapshot.raw_bytes
        ):
            snapshot = latest
            spec = parse_release_spec(snapshot, base)
            preflight_release(
                spec,
                runtime_digest_fn=runtime_digest_fn,
                verify_fn=verify_fn,
            )
            continue

        _assert_current_unchanged(snapshot)
        argv = build_run_argv(spec)
        execve_fn(
            str(spec.python_executable),
            argv,
            _minimal_supervisor_environment(),
        )
        raise LaunchError("LAUNCH_SUPERVISE_EXEC_RETURNED", "监管器进程替换未生效")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="验证并启动当前不可变本地发布",
        allow_abbrev=False,
    )
    parser.add_argument("--base", type=Path, default=default_release_base())
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--no-open", action="store_true")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--status", action="store_true")
    operation.add_argument("--stop", action="store_true")
    operation.add_argument("--supervise", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.supervise:
            supervise_latest(base=args.base)
            raise AssertionError("unreachable")
        if args.stop:
            result = stop_latest(base=args.base)
        elif args.status:
            result = status_latest(base=args.base)
        else:
            result = launch_latest(
                base=args.base,
                timeout_seconds=args.timeout,
                no_open=args.no_open,
            )
    except (LaunchError, SupervisorError) as exc:
        code = getattr(exc, "code", "LAUNCH_FAILED")
        message = getattr(exc, "message", "不可变本地发布启动失败")
        print(
            json.dumps({"ok": False, "error_code": code, "message": message}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    except Exception:  # noqa: BLE001 - top-level fail-closed error boundary
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "LAUNCH_UNEXPECTED_FAILURE",
                    "message": "不可变本地发布启动发生未分类故障，请查看监管日志",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        return 130
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
