#!/usr/bin/env python3
"""Fail-closed local supervisor for the sealed construction-expert release.

The supervisor intentionally owns exactly two processes: the backend ASGI
server and the Streamlit UI.  It never selects another release and never
falls back to a mutable source checkout.  A unit is healthy only when both
listeners belong to the processes started here and the backend reports the
exact, content-addressed identity supplied on the command line.

Secrets are inherited from the supervisor process or parsed from one explicit
0600 environment file.  They are never copied into the pid/state/event files.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import math
import os
import pwd
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO


SYSTEM_ID_DEFAULT = "docgen-system"
CRASH_WINDOW_SECONDS = 120.0
MAX_CRASHES_IN_WINDOW = 3
MAX_CONSECUTIVE_TRANSIENT_HEALTH_FAILURES = 3
MIN_TRANSIENT_HEALTH_FAILURE_SECONDS = 15.0
STABLE_RESET_SECONDS = 120.0
DEFAULT_HEALTH_INTERVAL_SECONDS = 3.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 45.0
DEFAULT_STOP_GRACE_SECONDS = 12.0
DEFAULT_EVENT_LOG_BYTES = 5 * 1024 * 1024
DEFAULT_EVENT_LOG_ARCHIVES = 3
STATE_FILE_NAME = "supervisor.json"
PID_FILE_NAME = "runtime_supervisor.pid"
LOCK_FILE_NAME = "runtime_supervisor.lock"
EVENT_FILE_NAME = "runtime_supervisor.events.jsonl"
RELEASE_MANIFEST_NAME = "release-manifest.json"
RELEASE_PROVENANCE_NAME = "release-provenance.json"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
_SYSTEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SECRET_FIELD_RE = re.compile(
    r"(?:api.?key|secret|token|password|authorization|credential|private.?key)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/=]+")
_KEY_LITERAL_RE = re.compile(
    r"\b(?:sk|key|token|secret)-[A-Za-z0-9._~+\-/=]{8,}", re.IGNORECASE
)
_URL_USERINFO_RE = re.compile(r"(https?://)[^/@\s]+@", re.IGNORECASE)

TRANSIENT_HEALTH_FAILURE_CODES = frozenset(
    {
        "SUPERVISOR_BACKEND_HEALTH_TIMEOUT",
        "SUPERVISOR_BACKEND_HEALTH_UNREACHABLE",
        "SUPERVISOR_BACKEND_HEALTH_HTTP_ERROR",
        "SUPERVISOR_BACKEND_HEALTH_INVALID",
        "SUPERVISOR_UI_HEALTH_TIMEOUT",
        "SUPERVISOR_UI_HEALTH_UNREACHABLE",
        "SUPERVISOR_UI_HEALTH_HTTP_ERROR",
    }
)


class SupervisorError(RuntimeError):
    """Stable, public supervisor failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExpectedIdentity:
    system_id: str
    release_id: str
    manifest_digest: str
    source_digest: str
    runtime_digest: str

    def validate(self) -> None:
        if not _SYSTEM_ID_RE.fullmatch(self.system_id):
            raise SupervisorError("SUPERVISOR_SYSTEM_ID_INVALID", "system_id 格式无效")
        if not _RELEASE_ID_RE.fullmatch(self.release_id):
            raise SupervisorError("SUPERVISOR_RELEASE_ID_INVALID", "release_id 格式无效")
        for name, value in (
            ("manifest_digest", self.manifest_digest),
            ("source_digest", self.source_digest),
            ("runtime_digest", self.runtime_digest),
        ):
            if not _DIGEST_RE.fullmatch(value):
                raise SupervisorError(
                    "SUPERVISOR_IDENTITY_DIGEST_INVALID", f"{name} 必须是小写 SHA-256"
                )

    def as_dict(self) -> dict[str, str]:
        return {
            "system_id": self.system_id,
            "release_id": self.release_id,
            "manifest_digest": self.manifest_digest,
            "source_digest": self.source_digest,
            "runtime_digest": self.runtime_digest,
        }


@dataclass(frozen=True)
class SupervisorConfig:
    release_dir: Path
    python_executable: Path
    backend_port: int
    ui_port: int
    identity: ExpectedIdentity
    state_dir: Path
    log_dir: Path
    env_file: Path | None = None
    health_interval_seconds: float = DEFAULT_HEALTH_INTERVAL_SECONDS
    startup_timeout_seconds: float = DEFAULT_STARTUP_TIMEOUT_SECONDS
    stop_grace_seconds: float = DEFAULT_STOP_GRACE_SECONDS

    @property
    def state_file(self) -> Path:
        return self.state_dir / STATE_FILE_NAME

    @property
    def pid_file(self) -> Path:
        return self.state_dir / PID_FILE_NAME

    @property
    def lock_file(self) -> Path:
        return self.state_dir / LOCK_FILE_NAME

    @property
    def event_file(self) -> Path:
        return self.log_dir / EVENT_FILE_NAME

    def validate(self) -> None:
        self.identity.validate()
        release_dir = _require_absolute_path(self.release_dir, "release_dir")
        python_executable = _require_absolute_path(
            self.python_executable, "python_executable"
        )
        _require_absolute_path(self.state_dir, "state_dir")
        _require_absolute_path(self.log_dir, "log_dir")
        if not release_dir.is_dir() or release_dir.is_symlink():
            raise SupervisorError(
                "SUPERVISOR_RELEASE_INVALID", "release_dir 必须是不可变发布目录"
            )
        if not (release_dir / "app.py").is_file() or not (
            release_dir / "backend" / "app" / "main.py"
        ).is_file():
            raise SupervisorError(
                "SUPERVISOR_RELEASE_INCOMPLETE", "发布目录缺少后端或界面入口"
            )
        if (
            not python_executable.is_file()
            or not os.access(python_executable, os.X_OK)
        ):
            raise SupervisorError(
                "SUPERVISOR_RUNTIME_INVALID", "Python 运行时必须是显式可执行普通文件"
            )
        _validate_python_executable(python_executable)
        if self.backend_port == self.ui_port:
            raise SupervisorError("SUPERVISOR_PORT_COLLISION", "后端与界面端口不能相同")
        for port in (self.backend_port, self.ui_port):
            if not 1 <= int(port) <= 65535:
                raise SupervisorError("SUPERVISOR_PORT_INVALID", "端口超出有效范围")
        if self.env_file is not None:
            _validate_secret_file(self.env_file)
        if self.health_interval_seconds <= 0 or self.startup_timeout_seconds <= 0:
            raise SupervisorError(
                "SUPERVISOR_TIMING_INVALID", "健康间隔与启动期限必须大于零"
            )
        if self.stop_grace_seconds <= 0:
            raise SupervisorError("SUPERVISOR_TIMING_INVALID", "停止宽限期必须大于零")


def _require_absolute_path(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise SupervisorError(
            "SUPERVISOR_PATH_NOT_ABSOLUTE", f"{label} 必须使用绝对路径"
        )
    return path


def _validate_secret_file(path: Path) -> None:
    _require_absolute_path(path, "env_file")
    try:
        info = path.lstat()
    except OSError as exc:
        raise SupervisorError(
            "SUPERVISOR_ENV_FILE_UNAVAILABLE", "密钥环境文件不可用"
        ) from exc
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise SupervisorError(
            "SUPERVISOR_ENV_FILE_UNTRUSTED", "密钥环境文件必须是普通文件"
        )
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise SupervisorError(
            "SUPERVISOR_ENV_FILE_PERMISSIONS",
            "密钥环境文件必须归当前用户所有且权限为0600",
        )
    if info.st_size > 1024 * 1024:
        raise SupervisorError(
            "SUPERVISOR_ENV_FILE_OVERSIZED", "密钥环境文件大小超出限制"
        )


def _validate_python_executable(path: Path) -> Path:
    """Validate a logical venv launcher while preserving its symlink semantics."""

    _require_absolute_path(path, "python_executable")
    try:
        logical_info = path.lstat()
        resolved = path.resolve(strict=True)
        resolved_info = resolved.stat()
    except OSError as exc:
        raise SupervisorError("SUPERVISOR_RUNTIME_INVALID", "Python 运行时不可用") from exc
    trusted_owners = {0, os.getuid()}
    if (
        logical_info.st_uid not in trusted_owners
        or resolved_info.st_uid not in trusted_owners
    ):
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_OWNER_MISMATCH", "Python 运行时所有者不可信"
        )
    if not (stat.S_ISREG(logical_info.st_mode) or stat.S_ISLNK(logical_info.st_mode)):
        raise SupervisorError("SUPERVISOR_RUNTIME_INVALID", "Python 运行时类型无效")
    if not stat.S_ISREG(resolved_info.st_mode) or not os.access(path, os.X_OK):
        raise SupervisorError("SUPERVISOR_RUNTIME_INVALID", "Python 运行时不可执行")
    return resolved


def load_secret_environment(path: Path | None) -> tuple[dict[str, str], set[str]]:
    """Return a child environment and the secret values used for redaction."""

    child_env = dict(os.environ)
    loaded_values: set[str] = {
        value
        for name, value in child_env.items()
        if value and _SECRET_FIELD_RE.search(name)
    }
    if path is None:
        return child_env, loaded_values
    _validate_secret_file(path)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SupervisorError(
            "SUPERVISOR_ENV_FILE_READ_FAILED", "密钥环境文件无法读取"
        ) from exc
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise SupervisorError(
                "SUPERVISOR_ENV_FILE_INVALID",
                f"密钥环境文件第{line_number}行格式无效",
            )
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not _ENV_NAME_RE.fullmatch(name):
            raise SupervisorError(
                "SUPERVISOR_ENV_FILE_INVALID",
                f"密钥环境文件第{line_number}行变量名无效",
            )
        if len(value) >= 2 and value[:1] == value[-1:] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if "\x00" in value or "\n" in value or "\r" in value:
            raise SupervisorError(
                "SUPERVISOR_ENV_FILE_INVALID",
                f"密钥环境文件第{line_number}行变量值无效",
            )
        child_env[name] = value
        if value:
            loaded_values.add(value)
    return child_env, loaded_values


def _redact_string(value: str, secret_values: set[str]) -> str:
    result = value
    for secret in sorted(secret_values, key=len, reverse=True):
        if len(secret) >= 4:
            result = result.replace(secret, "[REDACTED]")
    result = _BEARER_RE.sub("Bearer [REDACTED]", result)
    result = _KEY_LITERAL_RE.sub("[REDACTED]", result)
    result = _URL_USERINFO_RE.sub(r"\1[REDACTED]@", result)
    return result[:4096]


def redact(value: Any, secret_values: set[str]) -> Any:
    if isinstance(value, Mapping):
        projected: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            if _SECRET_FIELD_RE.search(key):
                projected[key] = "[REDACTED]"
            else:
                projected[key] = redact(item, secret_values)
        return projected
    if isinstance(value, (list, tuple)):
        return [redact(item, secret_values) for item in value]
    if isinstance(value, str):
        return _redact_string(value, secret_values)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _redact_string(str(value), secret_values)


def _secure_directory(path: Path) -> None:
    _require_absolute_path(path, "secure_directory")
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        raise SupervisorError(
            "SUPERVISOR_DIRECTORY_UNTRUSTED", "监管目录不是可信普通目录"
        )
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if info.st_uid != os.getuid():
        raise SupervisorError(
            "SUPERVISOR_DIRECTORY_OWNER_MISMATCH", "监管目录不属于当前用户"
        )
    os.chmod(path, 0o700)


def _secure_open(path: Path, flags: int, mode: int = 0o600) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags | no_follow, mode)
    os.fchmod(fd, mode)
    return fd


class EventLogger:
    def __init__(
        self,
        path: Path,
        *,
        secret_values: set[str] | None = None,
        max_bytes: int = DEFAULT_EVENT_LOG_BYTES,
        archives: int = DEFAULT_EVENT_LOG_ARCHIVES,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = path
        self.secret_values = set(secret_values or ())
        self.max_bytes = max(1024, int(max_bytes))
        self.archives = max(1, int(archives))
        self.wall_clock = wall_clock
        self._lock = threading.Lock()
        _secure_directory(path.parent)

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        try:
            current_size = self.path.lstat().st_size
            if self.path.is_symlink():
                raise SupervisorError(
                    "SUPERVISOR_LOG_UNTRUSTED", "事件日志不能是符号链接"
                )
        except FileNotFoundError:
            return
        if current_size + incoming_bytes <= self.max_bytes:
            return
        oldest = self.path.with_name(f"{self.path.name}.{self.archives}")
        if oldest.exists():
            if oldest.is_symlink() or not oldest.is_file():
                raise SupervisorError(
                    "SUPERVISOR_LOG_UNTRUSTED", "轮转日志目标不可信"
                )
            oldest.unlink()
        for index in range(self.archives - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            target = self.path.with_name(f"{self.path.name}.{index + 1}")
            if source.exists():
                if source.is_symlink() or not source.is_file():
                    raise SupervisorError(
                        "SUPERVISOR_LOG_UNTRUSTED", "轮转日志来源不可信"
                    )
                os.replace(source, target)
                os.chmod(target, 0o600)
        os.replace(self.path, self.path.with_name(f"{self.path.name}.1"))
        os.chmod(self.path.with_name(f"{self.path.name}.1"), 0o600)

    def emit(self, event: str, *, level: str = "info", **fields: Any) -> None:
        record = {
            "timestamp": self.wall_clock(),
            "event": event,
            "level": level,
            **fields,
        }
        safe_record = redact(record, self.secret_values)
        encoded = (
            json.dumps(safe_record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        with self._lock:
            self._rotate_if_needed(len(encoded))
            fd = _secure_open(
                self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
            )
            try:
                os.write(fd, encoded)
                os.fsync(fd)
            finally:
                os.close(fd)


class InstanceLock:
    def __init__(self, path: Path, instance_id: str) -> None:
        self.path = path
        self.instance_id = instance_id
        self._stream: BinaryIO | None = None

    def acquire(self) -> None:
        _secure_directory(self.path.parent)
        fd = _secure_open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        stream = os.fdopen(fd, "r+b", buffering=0)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            stream.close()
            raise SupervisorError(
                "SUPERVISOR_ALREADY_RUNNING", "已有监管器实例持有运行锁"
            ) from exc
        stream.seek(0)
        stream.truncate()
        payload = json.dumps(
            {"pid": os.getpid(), "instance_id": self.instance_id},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        stream.write(payload)
        os.fsync(stream.fileno())
        self._stream = stream

    def release(self) -> None:
        if self._stream is None:
            return
        try:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        finally:
            self._stream.close()
            self._stream = None


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _secure_directory(path.parent)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    fd = _secure_open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp_path, path)
    os.chmod(path, 0o600)


def _write_pid_file(path: Path, pid: int) -> None:
    _secure_directory(path.parent)
    fd = _secure_open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, f"{int(pid)}\n".encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _default_http_get(url: str, timeout: float) -> tuple[int, bytes]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(1024 * 1024)


def _is_timeout_exception(exc: BaseException) -> bool:
    """Recognize direct and urllib-wrapped timeouts without string matching."""

    current: BaseException | object | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, TimeoutError):
            return True
        if isinstance(current, OSError) and current.errno == errno.ETIMEDOUT:
            return True
        current = getattr(current, "reason", None)
    return False


def _default_listener_pids(port: int) -> set[int]:
    candidates = (Path("/usr/sbin/lsof"), Path("/usr/bin/lsof"))
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        return set()
    completed = subprocess.run(
        [
            str(executable),
            "-nP",
            f"-iTCP:{int(port)}",
            "-sTCP:LISTEN",
            "-t",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=2,
    )
    if completed.returncode not in {0, 1}:
        return set()
    result: set[int] = set()
    for line in completed.stdout.splitlines():
        try:
            result.add(int(line.strip()))
        except ValueError:
            continue
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise SupervisorError(
            "SUPERVISOR_RELEASE_FILE_UNREADABLE", "发布文件无法读取"
        ) from exc
    return digest.hexdigest()


def _manifest_mode(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} mode 无效")
    if isinstance(value, int):
        mode = value
    elif isinstance(value, str):
        raw = value.strip().lower()
        try:
            mode = int(raw[2:] if raw.startswith("0o") else raw, 8)
        except ValueError as exc:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", f"{field} mode 无效"
            ) from exc
    else:
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} mode 无效")
    if not 0 <= mode <= 0o7777:
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} mode 无效")
    return mode


def _manifest_relative_path(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} path 无效")
    if "\\" in value:
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} path 无效")
    candidate = Path(value)
    if candidate.is_absolute() or value != candidate.as_posix():
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} path 无效")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", f"{field} path 无效")
    if value == RELEASE_MANIFEST_NAME:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_INVALID", "manifest 自身不得列入发布条目"
        )
    return value


def _release_tree_entries(release_dir: Path) -> dict[str, str]:
    """Return physical tree entry kinds without following any symlink."""

    entries: dict[str, str] = {}

    def visit(directory: Path, prefix: str = "") -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_TREE_UNREADABLE", "发布目录无法遍历"
            ) from exc
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if relative == RELEASE_MANIFEST_NAME:
                continue
            try:
                if child.is_symlink():
                    entries[relative] = "mutable_link"
                elif child.is_dir(follow_symlinks=False):
                    entries[relative] = "directory"
                    visit(Path(child.path), relative)
                elif child.is_file(follow_symlinks=False):
                    entries[relative] = "file"
                else:
                    entries[relative] = "unsupported"
            except OSError as exc:
                raise SupervisorError(
                    "SUPERVISOR_RELEASE_TREE_UNREADABLE", "发布条目无法识别"
                ) from exc

    visit(release_dir)
    return entries


def verify_release_manifest(
    release_dir: Path, expected_identity: ExpectedIdentity
) -> dict[str, Any]:
    """Reverse-verify one complete immutable release tree, without link traversal."""

    manifest_path = release_dir / RELEASE_MANIFEST_NAME
    try:
        manifest_info = manifest_path.lstat()
        if not stat.S_ISREG(manifest_info.st_mode) or manifest_path.is_symlink():
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_UNTRUSTED", "发布清单必须是普通文件"
            )
        if (
            manifest_info.st_uid != os.getuid()
            or stat.S_IMODE(manifest_info.st_mode) != 0o444
        ):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_UNTRUSTED",
                "发布清单必须归当前用户所有且权限为0444",
            )
        if manifest_info.st_size > 16 * 1024 * 1024:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_OVERSIZED", "发布清单大小超出限制"
            )
        manifest_bytes = manifest_path.read_bytes()
    except FileNotFoundError as exc:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_MISSING", "发布目录缺少 release-manifest.json"
        ) from exc
    except OSError as exc:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_UNREADABLE", "发布清单无法读取"
        ) from exc
    actual_manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if actual_manifest_digest != expected_identity.manifest_digest:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_DIGEST_MISMATCH", "发布清单摘要与准入身份不一致"
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_INVALID", "发布清单不是有效 UTF-8 JSON"
        ) from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_INVALID", "发布清单 schema_version 必须为1"
        )
    content_addressed_release_id = f"release-{expected_identity.source_digest[:24]}"
    if expected_identity.release_id != content_addressed_release_id:
        raise SupervisorError(
            "SUPERVISOR_RELEASE_ID_NOT_CONTENT_ADDRESSED",
            "release_id 未绑定 source_digest",
        )
    for key, expected in (
        ("release_id", expected_identity.release_id),
        ("source_digest", expected_identity.source_digest),
        ("runtime_digest", expected_identity.runtime_digest),
    ):
        if str(manifest.get(key) or "") != expected:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_IDENTITY_MISMATCH", f"发布清单 {key} 不匹配"
            )

    files = manifest.get("files")
    directories = manifest.get("directories")
    mutable_links = manifest.get("mutable_links")
    if not isinstance(files, list) or not isinstance(directories, list) or not isinstance(
        mutable_links, list
    ):
        raise SupervisorError(
            "SUPERVISOR_MANIFEST_INVALID", "发布清单条目列表缺失"
        )

    expected_entries: dict[str, str] = {}

    def register(raw_path: Any, kind: str, field: str) -> tuple[str, Path]:
        relative = _manifest_relative_path(raw_path, field=field)
        if relative in expected_entries:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_DUPLICATE", f"发布清单重复条目: {relative}"
            )
        expected_entries[relative] = kind
        return relative, release_dir / relative

    for item in files:
        if not isinstance(item, dict):
            raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", "files 条目无效")
        relative, path = register(item.get("path"), "file", "files")
        try:
            info = path.lstat()
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_FILE_MISSING", f"发布文件缺失: {relative}"
            ) from exc
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise SupervisorError(
                "SUPERVISOR_RELEASE_FILE_TYPE_MISMATCH", f"发布文件类型不符: {relative}"
            )
        size = item.get("size")
        digest = item.get("sha256")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or not _DIGEST_RE.fullmatch(digest)
        ):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", f"发布文件元数据无效: {relative}"
            )
        expected_mode = _manifest_mode(item.get("mode"), field=relative)
        if info.st_size != size or stat.S_IMODE(info.st_mode) != expected_mode:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_FILE_METADATA_MISMATCH",
                f"发布文件大小或权限不符: {relative}",
            )
        if _sha256_file(path) != digest:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_FILE_DIGEST_MISMATCH", f"发布文件摘要不符: {relative}"
            )

    for item in directories:
        if not isinstance(item, dict):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", "directories 条目无效"
            )
        relative, path = register(item.get("path"), "directory", "directories")
        try:
            info = path.lstat()
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_DIRECTORY_MISSING", f"发布目录缺失: {relative}"
            ) from exc
        if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
            raise SupervisorError(
                "SUPERVISOR_RELEASE_DIRECTORY_TYPE_MISMATCH",
                f"发布目录类型不符: {relative}",
            )
        expected_mode = _manifest_mode(item.get("mode"), field=relative)
        if stat.S_IMODE(info.st_mode) != expected_mode:
            raise SupervisorError(
                "SUPERVISOR_RELEASE_DIRECTORY_MODE_MISMATCH",
                f"发布目录权限不符: {relative}",
            )

    for item in mutable_links:
        if not isinstance(item, dict):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", "mutable_links 条目无效"
            )
        relative, path = register(item.get("path"), "mutable_link", "mutable_links")
        target = item.get("target")
        if not isinstance(target, str) or not target or "\x00" in target:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", f"可变链接目标无效: {relative}"
            )
        target_path = Path(target)
        if not target_path.is_absolute():
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_TARGET_INVALID",
                f"可变链接必须指向发布树外绝对路径: {relative}",
            )
        try:
            target_info = target_path.lstat()
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_TARGET_UNAVAILABLE",
                f"可变链接目标不可用: {relative}",
            ) from exc
        if (
            not stat.S_ISDIR(target_info.st_mode)
            or target_path.is_symlink()
            or target_info.st_uid != os.getuid()
            or stat.S_IMODE(target_info.st_mode) != 0o700
        ):
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_TARGET_UNTRUSTED",
                f"可变链接目标必须归当前用户所有且权限为0700: {relative}",
            )
        try:
            info = path.lstat()
            actual_target = os.readlink(path)
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_MISSING", f"可变链接缺失: {relative}"
            ) from exc
        if not stat.S_ISLNK(info.st_mode) or actual_target != target:
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_MISMATCH", f"可变链接不符: {relative}"
            )
        try:
            target_path.resolve(strict=False).relative_to(release_dir.resolve())
        except ValueError:
            pass
        else:
            raise SupervisorError(
                "SUPERVISOR_MUTABLE_LINK_TARGET_INVALID",
                f"可变链接不得指回发布树: {relative}",
            )

    actual_entries = _release_tree_entries(release_dir)
    if actual_entries != expected_entries:
        missing = sorted(set(expected_entries) - set(actual_entries))
        extra = sorted(set(actual_entries) - set(expected_entries))
        wrong_kind = sorted(
            path
            for path in set(actual_entries) & set(expected_entries)
            if actual_entries[path] != expected_entries[path]
        )
        detail = (missing or extra or wrong_kind or ["unknown"])[0]
        raise SupervisorError(
            "SUPERVISOR_RELEASE_TREE_MISMATCH", f"发布树存在未清单或缺失条目: {detail}"
        )
    actual_source_digest = compute_source_digest(files, directories, mutable_links)
    if actual_source_digest != expected_identity.source_digest:
        raise SupervisorError(
            "SUPERVISOR_SOURCE_DIGEST_MISMATCH", "发布清单条目与 source_digest 不一致"
        )
    return manifest


def load_release_provenance(
    release_dir: Path,
    manifest: Mapping[str, Any],
    *,
    expected_runtime_digest: str,
) -> dict[str, Any]:
    """Read mandatory build provenance after the complete tree was verified."""

    listed_files = manifest.get("files") if isinstance(manifest, Mapping) else None
    listed = {
        str(item.get("path") or "")
        for item in (listed_files or [])
        if isinstance(item, Mapping)
    }
    if RELEASE_PROVENANCE_NAME not in listed:
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_MISSING",
            "不可变发布缺少 release-provenance.json",
        )
    path = release_dir / RELEASE_PROVENANCE_NAME
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or path.is_symlink()
            or info.st_size > 16 * 1024
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o444
        ):
            raise SupervisorError(
                "SUPERVISOR_PROVENANCE_UNTRUSTED",
                "发布来源记录必须归当前用户所有、只读且大小有效",
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
    except SupervisorError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_INVALID", "发布来源记录无法读取"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_INVALID", "发布来源记录 schema_version 必须为1"
        )
    build_sha = payload.get("build_sha")
    source_branch = payload.get("source_branch")
    source_dirty = payload.get("source_dirty")
    runtime_digest = payload.get("runtime_digest")
    if build_sha is not None and (
        not isinstance(build_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", build_sha)
    ):
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_INVALID", "发布来源 build_sha 无效"
        )
    if source_branch is not None and (
        not isinstance(source_branch, str)
        or not source_branch
        or len(source_branch) > 255
        or any(character in source_branch for character in "\x00\r\n")
    ):
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_INVALID", "发布来源分支无效"
        )
    if source_dirty is not None and not isinstance(source_dirty, bool):
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_INVALID", "发布来源 dirty 状态无效"
        )
    if (
        not isinstance(runtime_digest, str)
        or not _DIGEST_RE.fullmatch(runtime_digest)
        or runtime_digest != expected_runtime_digest
    ):
        raise SupervisorError(
            "SUPERVISOR_PROVENANCE_RUNTIME_MISMATCH",
            "发布来源记录未绑定当前冻结运行时",
        )
    return {
        "schema_version": 1,
        "build_sha": build_sha,
        "source_branch": source_branch,
        "source_dirty": source_dirty,
        "runtime_digest": runtime_digest,
    }


def compute_source_digest(
    files: Sequence[Mapping[str, Any]],
    directories: Sequence[Mapping[str, Any]],
    mutable_links: Sequence[Mapping[str, Any]],
) -> str:
    """Compute a location-independent digest of all physical source entries."""

    seen: set[str] = set()

    def unique_path(item: Mapping[str, Any], field: str) -> str:
        path = _manifest_relative_path(item.get("path"), field=field)
        if path in seen:
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_DUPLICATE", f"发布清单重复条目: {path}"
            )
        seen.add(path)
        return path

    canonical_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, Mapping):
            raise SupervisorError("SUPERVISOR_MANIFEST_INVALID", "files 条目无效")
        path = unique_path(item, "files")
        size = item.get("size")
        digest = item.get("sha256")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or not _DIGEST_RE.fullmatch(digest)
        ):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", f"发布文件元数据无效: {path}"
            )
        canonical_files.append(
            {
                "path": path,
                "size": size,
                "mode": _manifest_mode(item.get("mode"), field=path),
                "sha256": digest,
            }
        )

    canonical_directories: list[dict[str, Any]] = []
    for item in directories:
        if not isinstance(item, Mapping):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", "directories 条目无效"
            )
        path = unique_path(item, "directories")
        canonical_directories.append(
            {
                "path": path,
                "mode": _manifest_mode(item.get("mode"), field=path),
            }
        )

    canonical_links: list[dict[str, str]] = []
    for item in mutable_links:
        if not isinstance(item, Mapping):
            raise SupervisorError(
                "SUPERVISOR_MANIFEST_INVALID", "mutable_links 条目无效"
            )
        path = unique_path(item, "mutable_links")
        canonical_links.append({"path": path, "kind": "mutable_link"})

    canonical = json.dumps(
        {
            "schema_version": 1,
            "files": sorted(canonical_files, key=lambda item: item["path"]),
            "directories": sorted(
                canonical_directories, key=lambda item: item["path"]
            ),
            "mutable_links": sorted(canonical_links, key=lambda item: item["path"]),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _runtime_root_for_python(python_executable: Path) -> tuple[Path, str]:
    logical = Path(os.path.abspath(os.fspath(python_executable)))
    for candidate in (
        logical.parent.parent / "pyvenv.cfg",
        logical.parent / "pyvenv.cfg",
    ):
        if candidate.is_file() and not candidate.is_symlink():
            root = candidate.parent
            try:
                entry = logical.relative_to(root).as_posix()
            except ValueError as exc:
                raise SupervisorError(
                    "SUPERVISOR_RUNTIME_LAYOUT_INVALID",
                    "Python 入口不在冻结运行时根目录内",
                ) from exc
            return root, entry
    raise SupervisorError(
        "SUPERVISOR_RUNTIME_LAYOUT_INVALID", "冻结运行时缺少 pyvenv.cfg"
    )


_MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}


def _is_macho(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) in _MACHO_MAGICS
    except OSError as exc:
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_DEPENDENCY_UNREADABLE",
            "冻结运行时 Mach-O 文件无法读取",
        ) from exc


def _otool(path: Path, option: str) -> list[str]:
    executable = Path("/usr/bin/otool")
    if not executable.is_file():
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_DEPENDENCY_TOOL_MISSING",
            "系统缺少可信 Mach-O 依赖检查工具",
        )
    try:
        completed = subprocess.run(
            [str(executable), option, str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_DEPENDENCY_INSPECTION_FAILED",
            "Mach-O 依赖检查未能完成",
        ) from exc
    if completed.returncode != 0:
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_DEPENDENCY_INSPECTION_FAILED",
            "Mach-O 依赖检查返回失败",
        )
    return completed.stdout.splitlines()


def _macho_rpaths(path: Path, executable_dir: Path) -> list[Path]:
    lines = _otool(path, "-l")
    result: list[Path] = []
    expect_path = False
    for line in lines:
        stripped = line.strip()
        if stripped == "cmd LC_RPATH":
            expect_path = True
            continue
        if expect_path and stripped.startswith("path "):
            raw = stripped[5:].split(" (offset ", 1)[0]
            if raw.startswith("@loader_path/"):
                candidate = path.parent / raw[len("@loader_path/") :]
            elif raw == "@loader_path":
                candidate = path.parent
            elif raw.startswith("@executable_path/"):
                candidate = executable_dir / raw[len("@executable_path/") :]
            elif raw == "@executable_path":
                candidate = executable_dir
            elif raw.startswith("/"):
                candidate = Path(raw)
            else:
                expect_path = False
                continue
            result.append(Path(os.path.abspath(os.fspath(candidate))))
            expect_path = False
    return result


def _is_trusted_system_library(path: Path) -> bool:
    value = str(path)
    return value.startswith("/System/Library/") or value.startswith("/usr/lib/")


def _resolve_macho_dependency(
    raw: str,
    *,
    loader: Path,
    executable_dir: Path,
) -> Path | None:
    if raw.startswith("/"):
        candidates = [Path(raw)]
    elif raw.startswith("@loader_path/"):
        candidates = [loader.parent / raw[len("@loader_path/") :]]
    elif raw.startswith("@executable_path/"):
        candidates = [executable_dir / raw[len("@executable_path/") :]]
    elif raw.startswith("@rpath/"):
        suffix = raw[len("@rpath/") :]
        candidates = [loader.parent / suffix]
        candidates.extend(root / suffix for root in _macho_rpaths(loader, executable_dir))
    else:
        candidates = [loader.parent / raw]
    for candidate in candidates:
        absolute = Path(os.path.abspath(os.fspath(candidate)))
        if _is_trusted_system_library(absolute):
            return None
        try:
            return absolute.resolve(strict=True)
        except OSError:
            continue
    if any(_is_trusted_system_library(Path(os.path.abspath(os.fspath(item)))) for item in candidates):
        return None
    raise SupervisorError(
        "SUPERVISOR_RUNTIME_DEPENDENCY_UNRESOLVED",
        "非系统 Mach-O 依赖无法解析",
    )


def _macho_dependency_closure(
    roots: list[Path], *, runtime_root: Path, executable: Path
) -> list[dict[str, Any]]:
    if sys.platform != "darwin":
        return []
    queue = sorted({path.resolve(strict=True) for path in roots}, key=str)
    inspected: set[Path] = set()
    external: dict[str, dict[str, Any]] = {}
    executable_dir = executable.resolve(strict=True).parent
    while queue:
        loader = queue.pop(0)
        if loader in inspected:
            continue
        inspected.add(loader)
        lines = _otool(loader, "-L")
        install_names = {
            line.strip()
            for line in _otool(loader, "-D")[1:]
            if line.strip() and not line.strip().endswith(":")
        }
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped or " (compatibility version " not in stripped:
                continue
            raw = stripped.split(" (compatibility version ", 1)[0]
            if raw in install_names:
                continue
            dependency = _resolve_macho_dependency(
                raw,
                loader=loader,
                executable_dir=executable_dir,
            )
            if dependency is None or dependency == loader:
                continue
            try:
                info = dependency.stat()
            except OSError as exc:
                raise SupervisorError(
                    "SUPERVISOR_RUNTIME_DEPENDENCY_UNREADABLE",
                    "非系统 Mach-O 依赖无法读取",
                ) from exc
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid not in {0, os.getuid()}
            ):
                raise SupervisorError(
                    "SUPERVISOR_RUNTIME_DEPENDENCY_UNTRUSTED",
                    "非系统 Mach-O 依赖类型或所有者不可信",
                )
            try:
                dependency.relative_to(runtime_root)
            except ValueError:
                external[str(dependency)] = {
                    "path": str(dependency),
                    "size": info.st_size,
                    "mode": stat.S_IMODE(info.st_mode),
                    "sha256": _sha256_file(dependency),
                }
            if _is_macho(dependency) and dependency not in inspected:
                queue.append(dependency)
    return [external[key] for key in sorted(external)]


def runtime_tree_snapshot(python_executable: Path) -> dict[str, Any]:
    """Return a location-independent, physical snapshot without executing Python."""

    logical = Path(os.path.abspath(os.fspath(python_executable)))
    resolved_python = _validate_python_executable(logical)
    runtime_root, logical_entry = _runtime_root_for_python(logical)
    try:
        root_info = runtime_root.lstat()
    except OSError as exc:
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_TREE_UNREADABLE", "冻结运行时目录无法读取"
        ) from exc
    if not stat.S_ISDIR(root_info.st_mode) or runtime_root.is_symlink():
        raise SupervisorError(
            "SUPERVISOR_RUNTIME_LAYOUT_INVALID", "冻结运行时根目录类型无效"
        )

    directories: list[dict[str, Any]] = [
        {"path": ".", "mode": stat.S_IMODE(root_info.st_mode)}
    ]
    files: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    macho_roots: list[Path] = [resolved_python] if _is_macho(resolved_python) else []

    def visit(directory: Path, prefix: str = "") -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_RUNTIME_TREE_UNREADABLE", "冻结运行时目录无法遍历"
            ) from exc
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            path = Path(child.path)
            try:
                info = path.lstat()
                if child.is_symlink():
                    raw_target = os.readlink(path)
                    resolved_target = path.resolve(strict=True)
                    try:
                        resolved_target.relative_to(runtime_root)
                        external = None
                    except ValueError:
                        target_info = resolved_target.stat()
                        if not stat.S_ISREG(target_info.st_mode):
                            raise SupervisorError(
                                "SUPERVISOR_RUNTIME_EXTERNAL_LINK_INVALID",
                                f"冻结运行时外部链接不是普通文件: {relative}",
                            )
                        external = {
                            "size": target_info.st_size,
                            "mode": stat.S_IMODE(target_info.st_mode),
                            "sha256": _sha256_file(resolved_target),
                        }
                        if _is_macho(resolved_target):
                            macho_roots.append(resolved_target)
                    links.append(
                        {
                            "path": relative,
                            "target": raw_target,
                            "external_file": external,
                        }
                    )
                elif child.is_dir(follow_symlinks=False):
                    directories.append(
                        {"path": relative, "mode": stat.S_IMODE(info.st_mode)}
                    )
                    visit(path, relative)
                elif child.is_file(follow_symlinks=False):
                    files.append(
                        {
                            "path": relative,
                            "size": info.st_size,
                            "mode": stat.S_IMODE(info.st_mode),
                            "sha256": _sha256_file(path),
                        }
                    )
                    if _is_macho(path):
                        macho_roots.append(path)
                else:
                    raise SupervisorError(
                        "SUPERVISOR_RUNTIME_ENTRY_UNSUPPORTED",
                        f"冻结运行时包含不支持的条目: {relative}",
                    )
            except SupervisorError:
                raise
            except OSError as exc:
                raise SupervisorError(
                    "SUPERVISOR_RUNTIME_TREE_UNREADABLE",
                    f"冻结运行时条目无法读取: {relative}",
                ) from exc

    visit(runtime_root)
    dependency_closure = _macho_dependency_closure(
        macho_roots,
        runtime_root=runtime_root,
        executable=resolved_python,
    )
    return {
        "schema_version": 3,
        "dependency_policy": "non_system_macho_closure_v1",
        "python_logical_entry": logical_entry,
        "python_resolved_size": resolved_python.stat().st_size,
        "python_resolved_sha256": _sha256_file(resolved_python),
        "directories": sorted(directories, key=lambda item: item["path"]),
        "files": sorted(files, key=lambda item: item["path"]),
        "links": sorted(links, key=lambda item: item["path"]),
        "external_macho_dependencies": dependency_closure,
    }


def compute_runtime_digest(python_executable: Path) -> str:
    """Hash every physical venv entry without executing the candidate runtime."""

    canonical = json.dumps(
        runtime_tree_snapshot(python_executable),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class RuntimeSupervisor:
    def __init__(
        self,
        config: SupervisorConfig,
        *,
        popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        http_get: Callable[[str, float], tuple[int, bytes]] = _default_http_get,
        listener_pids: Callable[[int], set[int]] = _default_listener_pids,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        getpgid: Callable[[int], int] = os.getpgid,
        killpg: Callable[[int, int], None] = os.killpg,
        event_logger: EventLogger | None = None,
    ) -> None:
        config.validate()
        release_manifest = verify_release_manifest(config.release_dir, config.identity)
        actual_runtime_digest = compute_runtime_digest(config.python_executable)
        if actual_runtime_digest != config.identity.runtime_digest:
            raise SupervisorError(
                "SUPERVISOR_RUNTIME_DIGEST_MISMATCH",
                "Python 运行时摘要与发布清单不一致",
            )
        self.config = config
        self.release_provenance = load_release_provenance(
            config.release_dir,
            release_manifest,
            expected_runtime_digest=config.identity.runtime_digest,
        )
        self.popen_factory = popen_factory
        self.http_get = http_get
        self.listener_pids = listener_pids
        self.monotonic = monotonic
        self.wall_clock = wall_clock
        self.getpgid = getpgid
        self.killpg = killpg
        self.instance_id = uuid.uuid4().hex
        self.child_env, secret_values = load_secret_environment(config.env_file)
        self.logger = event_logger or EventLogger(
            config.event_file, secret_values=secret_values, wall_clock=wall_clock
        )
        self.backend: subprocess.Popen[bytes] | None = None
        self.ui: subprocess.Popen[bytes] | None = None
        # ``start_new_session=True`` makes each direct child the leader of a
        # process group that may outlive that child.  Retain that provenance so
        # cleanup can address descendants after the leader has already exited,
        # without ever signalling an unverified process group.
        self._owned_process_groups: set[int] = set()
        self.stop_requested = threading.Event()
        self.crash_times: list[float] = []
        self.healthy_since: float | None = None
        self.last_health_at: float | None = None
        self.last_error_code: str | None = None
        self.circuit_open = False
        self.consecutive_transient_health_failures = 0
        self.first_transient_health_failure_monotonic: float | None = None
        self.first_transient_health_failure_at: float | None = None
        self.last_probe_error_code: str | None = None
        self.started_at = self.wall_clock()
        self._lock = InstanceLock(config.lock_file, self.instance_id)

    def _restore_open_circuit(self) -> None:
        """Restore the complete breaker window, failing closed on bad state."""

        try:
            previous = _read_safe_state(self.config.state_dir)
        except SupervisorError as exc:
            self._latch_state_recovery_failure(exc.code)
            return

        if previous.get("status") == "not_started":
            return
        expected_identity = {
            "release_id": self.config.identity.release_id,
            "manifest_digest": self.config.identity.manifest_digest,
            "source_digest": self.config.identity.source_digest,
            "runtime_digest": self.config.identity.runtime_digest,
            "release_root": str(self.config.release_dir),
        }
        if any(field not in previous for field in expected_identity):
            self._latch_state_recovery_failure("SUPERVISOR_STATE_IDENTITY_INCOMPLETE")
            return
        if any(previous.get(field) != value for field, value in expected_identity.items()):
            # A newly selected, independently verified release starts with a
            # fresh breaker.  Partial identity never takes this path.
            return
        if previous.get("schema_version") != 1:
            self._latch_state_recovery_failure("SUPERVISOR_STATE_SCHEMA_INVALID")
            return

        count = previous.get("restart_count_window")
        circuit = previous.get("circuit_open")
        status = previous.get("status")
        raw_timestamps = previous.get("failure_timestamps")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or not 0 <= count <= MAX_CRASHES_IN_WINDOW
            or not isinstance(circuit, bool)
            or not isinstance(status, str)
        ):
            self._latch_state_recovery_failure("SUPERVISOR_STATE_BREAKER_INVALID")
            return

        # Legacy fully-open states remain safely latched.  A legacy non-open
        # nonzero counter cannot be reconstructed precisely and therefore
        # fails closed instead of silently forgetting failures.
        if raw_timestamps is None:
            if circuit is True:
                self.circuit_open = True
                self.last_error_code = (
                    "SUPERVISOR_STATE_RECOVERY_FAILED"
                    if previous.get("last_error_code")
                    == "SUPERVISOR_STATE_RECOVERY_FAILED"
                    else "SUPERVISOR_CRASH_LOOP"
                )
                return
            if count != 0:
                self._latch_state_recovery_failure("SUPERVISOR_STATE_FAILURE_WINDOW_MISSING")
                return
            raw_timestamps = []
        if not isinstance(raw_timestamps, list) or len(raw_timestamps) != count:
            self._latch_state_recovery_failure("SUPERVISOR_STATE_FAILURE_WINDOW_INVALID")
            return

        now = self.wall_clock()
        restored: list[float] = []
        for raw_stamp in raw_timestamps:
            if (
                isinstance(raw_stamp, bool)
                or not isinstance(raw_stamp, (int, float))
                or not math.isfinite(float(raw_stamp))
                or float(raw_stamp) < 0
                or float(raw_stamp) > now + 5.0
            ):
                self._latch_state_recovery_failure("SUPERVISOR_STATE_FAILURE_WINDOW_INVALID")
                return
            restored.append(float(raw_stamp))
        if restored != sorted(restored):
            self._latch_state_recovery_failure("SUPERVISOR_STATE_FAILURE_WINDOW_INVALID")
            return
        self.crash_times = restored
        self._prune_crashes(now)

        if circuit:
            # An opened breaker is latched until explicit operator recovery;
            # its diagnostic window may naturally age to zero while held.
            self.circuit_open = True
            self.last_error_code = (
                "SUPERVISOR_STATE_RECOVERY_FAILED"
                if previous.get("last_error_code")
                == "SUPERVISOR_STATE_RECOVERY_FAILED"
                else "SUPERVISOR_CRASH_LOOP"
            )
            return
        if status == "circuit_open" or count >= MAX_CRASHES_IN_WINDOW:
            self._latch_state_recovery_failure("SUPERVISOR_STATE_BREAKER_INCONSISTENT")
            return

    def _latch_state_recovery_failure(self, state_error_code: str) -> None:
        """Keep the process alive but prohibit child execution on bad state."""

        self.crash_times = []
        self.circuit_open = True
        self.last_error_code = "SUPERVISOR_STATE_RECOVERY_FAILED"
        self.logger.emit(
            "state_restore_failed",
            level="error",
            error_code="SUPERVISOR_STATE_RECOVERY_FAILED",
            state_error_code=state_error_code,
        )

    def _safe_state(self, status: str) -> dict[str, Any]:
        now = self.wall_clock()
        self._prune_crashes(now)
        return {
            "schema_version": 1,
            "status": status,
            "release_id": self.config.identity.release_id,
            "manifest_digest": self.config.identity.manifest_digest,
            "source_digest": self.config.identity.source_digest,
            "runtime_digest": self.config.identity.runtime_digest,
            "release_root": str(self.config.release_dir),
            "supervisor_pid": os.getpid(),
            "supervisor_instance_id": self.instance_id,
            "backend_pid": self.backend.pid if self.backend is not None else None,
            "ui_pid": self.ui.pid if self.ui is not None else None,
            "circuit_open": self.circuit_open,
            "restart_count_window": len(self.crash_times),
            "failure_timestamps": list(self.crash_times),
            "last_health_at": self.last_health_at,
            "last_error_code": self.last_error_code,
            "health_degraded": bool(self.consecutive_transient_health_failures),
            "consecutive_health_failures": self.consecutive_transient_health_failures,
            "first_health_failure_at": self.first_transient_health_failure_at,
            "last_probe_error_code": self.last_probe_error_code,
            "started_at": self.started_at,
            "updated_at": now,
        }

    def _write_state(self, status: str) -> None:
        state_file = self.config.state_file
        try:
            existing = state_file.lstat()
        except FileNotFoundError:
            existing = None
        except OSError as exc:
            raise SupervisorError(
                "SUPERVISOR_STATE_REPAIR_FAILED", "监管状态目标无法核验"
            ) from exc
        if existing is not None and (
            not stat.S_ISREG(existing.st_mode) or state_file.is_symlink()
        ):
            # Preserve the exact untrusted object for diagnosis while freeing
            # the canonical path for a safe 0600 fail-closed state file.
            quarantine = state_file.with_name(
                f".{state_file.name}.untrusted.{uuid.uuid4().hex}"
            )
            try:
                os.replace(state_file, quarantine)
            except OSError as exc:
                raise SupervisorError(
                    "SUPERVISOR_STATE_REPAIR_FAILED", "监管状态目标无法隔离"
                ) from exc
            self.logger.emit(
                "state_object_quarantined",
                level="error",
                error_code="SUPERVISOR_STATE_RECOVERY_FAILED",
                object_kind=(
                    "symlink" if stat.S_ISLNK(existing.st_mode) else "non_regular"
                ),
            )
        _atomic_write_json(self.config.state_file, self._safe_state(status))

    def _child_environment(self) -> dict[str, str]:
        env = dict(self.child_env)
        for name in ("ZF_BUILD_SHA", "ZF_BUILD_BRANCH", "ZF_BUILD_DIRTY"):
            env.pop(name, None)
        env.update(
            {
                "PYTHONPATH": str(self.config.release_dir),
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "ZF_SYSTEM_ID": self.config.identity.system_id,
                "ZF_RELEASE_ID": self.config.identity.release_id,
                "ZF_RELEASE_MANIFEST_DIGEST": self.config.identity.manifest_digest,
                "ZF_RELEASE_SOURCE_DIGEST": self.config.identity.source_digest,
                "ZF_RUNTIME_DIGEST": self.config.identity.runtime_digest,
                "ZF_RELEASE_ROOT": str(self.config.release_dir),
                "ZF_RELEASE_MANAGED": "1",
                "ZF_RUNTIME_MODE": "sealed_release",
                "ZF_SUPERVISED": "1",
                "ZF_SUPERVISOR_INSTANCE_ID": self.instance_id,
                "ZF_SUPERVISOR_STATE_FILE": str(self.config.state_file),
                "ZF_ENABLE_SELF_HEAL": "0",
                "ZF_WATCHDOG_MODE": "0",
                "BACKEND_PORT": str(self.config.backend_port),
                "WEB_PORT": str(self.config.ui_port),
                "ZF_BACKEND_BASE_URL": f"http://127.0.0.1:{self.config.backend_port}",
            }
        )
        build_sha = self.release_provenance.get("build_sha")
        source_branch = self.release_provenance.get("source_branch")
        source_dirty = self.release_provenance.get("source_dirty")
        if isinstance(build_sha, str) and build_sha:
            env["ZF_BUILD_SHA"] = build_sha
        if isinstance(source_branch, str) and source_branch:
            env["ZF_BUILD_BRANCH"] = source_branch
        if isinstance(source_dirty, bool):
            env["ZF_BUILD_DIRTY"] = "1" if source_dirty else "0"
        return env

    def _backend_argv(self) -> list[str]:
        return [
            str(self.config.python_executable),
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--app-dir",
            str(self.config.release_dir),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.config.backend_port),
        ]

    def _ui_argv(self) -> list[str]:
        return [
            str(self.config.python_executable),
            "-m",
            "streamlit",
            "run",
            str(self.config.release_dir / "app.py"),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(self.config.ui_port),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
            "--server.runOnSave",
            "false",
        ]

    def _spawn(self, argv: Sequence[str]) -> subprocess.Popen[bytes]:
        process = self.popen_factory(
            list(argv),
            cwd=str(self.config.release_dir),
            env=self._child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        pid = int(process.pid)
        try:
            current_pgid = self.getpgid(pid)
        except (OSError, ProcessLookupError) as exc:
            # A child can exit between Popen returning and this check.  The
            # successful start_new_session contract still establishes its
            # original group id, which is needed to reap surviving children.
            if process.poll() is None:
                try:
                    process.kill()
                except (AttributeError, OSError, ProcessLookupError):
                    pass
                raise SupervisorError(
                    "SUPERVISOR_PROCESS_GROUP_UNVERIFIED",
                    "子进程组所有权无法核验",
                ) from exc
        else:
            if current_pgid != pid:
                try:
                    process.kill()
                except (AttributeError, OSError, ProcessLookupError):
                    pass
                raise SupervisorError(
                    "SUPERVISOR_PROCESS_GROUP_MISMATCH",
                    "子进程未建立独立进程组",
                )
        self._owned_process_groups.add(pid)
        return process

    def _ports_are_clear(self) -> bool:
        return not self.listener_pids(self.config.backend_port) and not self.listener_pids(
            self.config.ui_port
        )

    def _spawn_unit(self) -> None:
        if not self._ports_are_clear():
            raise SupervisorError(
                "SUPERVISOR_FOREIGN_LISTENER", "目标端口已被非监管进程占用"
            )
        self._reset_transient_health_failures()
        self.backend = self._spawn(self._backend_argv())
        try:
            self.ui = self._spawn(self._ui_argv())
        except Exception:
            self._stop_unit()
            raise
        self.healthy_since = None
        self.logger.emit(
            "unit_started",
            release_id=self.config.identity.release_id,
            backend_pid=self.backend.pid,
            ui_pid=self.ui.pid,
        )
        self._write_state("starting")

    def _owns_listener(self, process: subprocess.Popen[bytes] | None, port: int) -> bool:
        if process is None or process.poll() is not None:
            return False
        try:
            if self.getpgid(process.pid) != process.pid:
                return False
        except (OSError, ProcessLookupError):
            return False
        owners = self.listener_pids(port)
        return owners == {process.pid}

    def _backend_identity_status(self) -> tuple[bool, str | None]:
        try:
            status_code, body = self.http_get(
                f"http://127.0.0.1:{self.config.backend_port}/livez", 2.0
            )
        except (OSError, urllib.error.URLError) as exc:
            if _is_timeout_exception(exc):
                return False, "SUPERVISOR_BACKEND_HEALTH_TIMEOUT"
            return False, "SUPERVISOR_BACKEND_HEALTH_UNREACHABLE"
        if status_code != 200:
            return False, "SUPERVISOR_BACKEND_HEALTH_HTTP_ERROR"
        try:
            payload = json.loads(body.decode("utf-8"))
        except (AttributeError, UnicodeError, ValueError, TypeError):
            return False, "SUPERVISOR_BACKEND_HEALTH_INVALID"
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return False, "SUPERVISOR_BACKEND_HEALTH_INVALID"
        expected = self.config.identity.as_dict()
        if not all(
            str(payload.get(key) or "") == value for key, value in expected.items()
        ):
            return False, "SUPERVISOR_BACKEND_IDENTITY_MISMATCH"
        return True, None

    def _backend_identity_healthy(self) -> bool:
        """Compatibility predicate backed by the classified probe result."""

        return self._backend_identity_status()[0]

    def _ui_health_status(self) -> tuple[bool, str | None]:
        try:
            status_code, _ = self.http_get(
                f"http://127.0.0.1:{self.config.ui_port}/", 2.0
            )
        except (OSError, urllib.error.URLError) as exc:
            if _is_timeout_exception(exc):
                return False, "SUPERVISOR_UI_HEALTH_TIMEOUT"
            return False, "SUPERVISOR_UI_HEALTH_UNREACHABLE"
        if not 200 <= status_code < 400:
            return False, "SUPERVISOR_UI_HEALTH_HTTP_ERROR"
        return True, None

    def _ui_healthy(self) -> bool:
        """Compatibility predicate backed by the classified probe result."""

        return self._ui_health_status()[0]

    def check_health(self) -> tuple[bool, str | None]:
        if self.backend is None or self.backend.poll() is not None:
            return False, "SUPERVISOR_BACKEND_EXITED"
        if self.ui is None or self.ui.poll() is not None:
            return False, "SUPERVISOR_UI_EXITED"
        if not self._owns_listener(self.backend, self.config.backend_port):
            return False, "SUPERVISOR_BACKEND_OWNERSHIP_MISMATCH"
        if not self._owns_listener(self.ui, self.config.ui_port):
            return False, "SUPERVISOR_UI_OWNERSHIP_MISMATCH"
        backend_healthy, backend_code = self._backend_identity_status()
        if not backend_healthy:
            return False, backend_code
        ui_healthy, ui_code = self._ui_health_status()
        if not ui_healthy:
            return False, ui_code
        return True, None

    def _restart_required_for_health_failure(self, code: str) -> bool:
        """Fail immediately on identity/process faults, debounce probe noise."""

        if code not in TRANSIENT_HEALTH_FAILURE_CODES:
            self._reset_transient_health_failures()
            return True
        now = self.monotonic()
        if self.first_transient_health_failure_monotonic is None:
            self.first_transient_health_failure_monotonic = now
            self.first_transient_health_failure_at = self.wall_clock()
        self.consecutive_transient_health_failures += 1
        self.last_probe_error_code = code
        count = self.consecutive_transient_health_failures
        first = self.first_transient_health_failure_monotonic
        elapsed = max(0.0, now - first) if first is not None else 0.0
        self.logger.emit(
            "health_probe_degraded",
            level="warning",
            error_code=code,
            consecutive_failures=count,
            restart_threshold=MAX_CONSECUTIVE_TRANSIENT_HEALTH_FAILURES,
            degraded_seconds=round(elapsed, 3),
            minimum_degraded_seconds=MIN_TRANSIENT_HEALTH_FAILURE_SECONDS,
        )
        return (
            count >= MAX_CONSECUTIVE_TRANSIENT_HEALTH_FAILURES
            and elapsed >= MIN_TRANSIENT_HEALTH_FAILURE_SECONDS
        )

    def _reset_transient_health_failures(self) -> None:
        self.consecutive_transient_health_failures = 0
        self.first_transient_health_failure_monotonic = None
        self.first_transient_health_failure_at = None
        self.last_probe_error_code = None

    def _prune_crashes(self, now: float) -> None:
        threshold = now - CRASH_WINDOW_SECONDS
        self.crash_times = [stamp for stamp in self.crash_times if stamp >= threshold]

    def _record_failure(self, code: str) -> bool:
        now = self.wall_clock()
        self._prune_crashes(now)
        self.crash_times.append(now)
        self.last_error_code = code
        self.healthy_since = None
        self.circuit_open = len(self.crash_times) >= MAX_CRASHES_IN_WINDOW
        if self.circuit_open:
            self.last_error_code = "SUPERVISOR_CRASH_LOOP"
        # Persist each failure before any retry wait.  A launchd restart after
        # failure one or two therefore resumes the same bounded window.
        self._write_state("circuit_open" if self.circuit_open else "restarting")
        self.logger.emit(
            "unit_failure",
            level="error",
            error_code=code,
            restart_count_window=len(self.crash_times),
            circuit_open=self.circuit_open,
        )
        if self.circuit_open:
            self.logger.emit(
                "circuit_opened",
                level="error",
                error_code="SUPERVISOR_CRASH_LOOP",
                crash_window_seconds=int(CRASH_WINDOW_SECONDS),
                max_crashes=MAX_CRASHES_IN_WINDOW,
            )
        return self.circuit_open

    def _hold_open_circuit(self) -> None:
        """Stay alive without children so launchd cannot bypass the breaker."""

        self._write_state("circuit_open")
        while not self.stop_requested.wait(self.config.health_interval_seconds):
            self._write_state("circuit_open")

    def _record_healthy(self) -> None:
        now = self.monotonic()
        if self.consecutive_transient_health_failures:
            first = self.first_transient_health_failure_monotonic
            self.logger.emit(
                "health_probe_recovered",
                consecutive_failures=self.consecutive_transient_health_failures,
                degraded_seconds=round(
                    max(0.0, now - first) if first is not None else 0.0, 3
                ),
            )
            self._reset_transient_health_failures()
        if self.healthy_since is None:
            self.healthy_since = now
        self.last_health_at = self.wall_clock()
        self.last_error_code = None
        if self.crash_times and now - self.healthy_since >= STABLE_RESET_SECONDS:
            self.crash_times.clear()
            self.circuit_open = False
            self.logger.emit("crash_window_reset", stable_seconds=int(STABLE_RESET_SECONDS))

    def _wait_for_initial_health(self) -> tuple[bool, str | None]:
        deadline = self.monotonic() + self.config.startup_timeout_seconds
        last_code = "SUPERVISOR_STARTUP_TIMEOUT"
        while not self.stop_requested.is_set() and self.monotonic() < deadline:
            healthy, code = self.check_health()
            if healthy:
                return True, None
            if code in {"SUPERVISOR_BACKEND_EXITED", "SUPERVISOR_UI_EXITED"}:
                return False, code
            last_code = code or last_code
            self.stop_requested.wait(min(0.25, self.config.health_interval_seconds))
        return False, last_code

    def _signal_process_group(
        self, process: subprocess.Popen[bytes], signum: int
    ) -> None:
        pid = int(process.pid)
        leader_running = process.poll() is None
        if leader_running:
            try:
                current_pgid = self.getpgid(pid)
            except (OSError, ProcessLookupError):
                # The leader may have exited between poll() and getpgid().
                # Continue only when spawn-time provenance already owns the
                # group; otherwise there is no safe signal target.
                if pid not in self._owned_process_groups:
                    return
            else:
                if current_pgid != pid:
                    try:
                        self.logger.emit(
                            "process_group_mismatch",
                            level="error",
                            error_code="SUPERVISOR_PROCESS_GROUP_MISMATCH",
                            pid=pid,
                        )
                    except Exception:
                        pass
                    return
                self._owned_process_groups.add(pid)
        elif pid not in self._owned_process_groups:
            try:
                self.logger.emit(
                    "process_group_signal_skipped",
                    level="error",
                    error_code="SUPERVISOR_PROCESS_GROUP_UNVERIFIED",
                    pid=pid,
                )
            except Exception:
                pass
            return
        try:
            self.killpg(pid, signum)
        except (OSError, ProcessLookupError):
            return

    def _stop_unit(self) -> None:
        processes = [process for process in (self.ui, self.backend) if process is not None]
        try:
            for process in processes:
                self._signal_process_group(process, signal.SIGTERM)
            for process in processes:
                try:
                    process.wait(timeout=self.config.stop_grace_seconds)
                except subprocess.TimeoutExpired:
                    self._signal_process_group(process, signal.SIGKILL)
                    try:
                        process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        try:
                            self.logger.emit(
                                "process_stop_failed",
                                level="error",
                                error_code="SUPERVISOR_CHILD_STOP_FAILED",
                                pid=process.pid,
                            )
                        except Exception:
                            pass
                else:
                    # Waiting for the leader does not establish that every
                    # descendant has exited.  Complete cleanup for every
                    # spawn-verified group after its graceful TERM window.
                    if int(process.pid) in self._owned_process_groups:
                        self._signal_process_group(process, signal.SIGKILL)
            if processes:
                try:
                    self.logger.emit("unit_stopped")
                except Exception:
                    pass
        finally:
            for process in processes:
                self._owned_process_groups.discard(int(process.pid))
            self.ui = None
            self.backend = None
            self.healthy_since = None

    def request_stop(self, *_args: Any) -> None:
        self.stop_requested.set()

    def run(self, *, install_signal_handlers: bool = True) -> int:
        self._lock.acquire()
        exit_code = 0
        final_status = "stopped"
        try:
            _write_pid_file(self.config.pid_file, os.getpid())
            if install_signal_handlers:
                signal.signal(signal.SIGTERM, self.request_stop)
                signal.signal(signal.SIGINT, self.request_stop)
            self._restore_open_circuit()
            self.logger.emit(
                "supervisor_started",
                instance_id=self.instance_id,
                release_id=self.config.identity.release_id,
            )
            self._write_state("starting")
            if self.circuit_open:
                final_status = "circuit_open"
                exit_code = 75
                self.logger.emit(
                    "circuit_restored",
                    level="error",
                    error_code=(
                        self.last_error_code or "SUPERVISOR_CRASH_LOOP"
                    ),
                )
                self._hold_open_circuit()
            while not self.stop_requested.is_set():
                try:
                    self._spawn_unit()
                except SupervisorError as exc:
                    self.logger.emit("unit_start_blocked", level="error", error_code=exc.code)
                    if self._record_failure(exc.code):
                        final_status = "circuit_open"
                        exit_code = 75
                        break
                    self._write_state("restarting")
                    self.stop_requested.wait(self.config.health_interval_seconds)
                    continue
                except Exception:
                    code = "SUPERVISOR_CHILD_SPAWN_FAILED"
                    if self._record_failure(code):
                        final_status = "circuit_open"
                        exit_code = 75
                        break
                    self._write_state("restarting")
                    self.stop_requested.wait(self.config.health_interval_seconds)
                    continue

                healthy, code = self._wait_for_initial_health()
                if not healthy:
                    self._stop_unit()
                    if self.stop_requested.is_set():
                        break
                    if self._record_failure(code or "SUPERVISOR_STARTUP_FAILED"):
                        final_status = "circuit_open"
                        exit_code = 75
                        break
                    self._write_state("restarting")
                    self.stop_requested.wait(self.config.health_interval_seconds)
                    continue

                self._record_healthy()
                self.logger.emit("unit_healthy")
                self._write_state("healthy")
                while not self.stop_requested.wait(self.config.health_interval_seconds):
                    healthy, code = self.check_health()
                    if not healthy:
                        failure_code = code or "SUPERVISOR_UNIT_UNHEALTHY"
                        if not self._restart_required_for_health_failure(failure_code):
                            self._write_state("degraded")
                            continue
                        self._stop_unit()
                        if self._record_failure(failure_code):
                            final_status = "circuit_open"
                            exit_code = 75
                        else:
                            self._write_state("restarting")
                        break
                    self._record_healthy()
                    self._write_state("healthy")
                if self.circuit_open:
                    break
            if self.circuit_open and not self.stop_requested.is_set():
                self._hold_open_circuit()
            if self.stop_requested.is_set() and not self.circuit_open:
                final_status = "stopped"
        finally:
            cleanup_error: BaseException | None = None

            def _cleanup_step(action: Callable[[], None]) -> None:
                nonlocal cleanup_error
                try:
                    action()
                except BaseException as exc:
                    if cleanup_error is None:
                        cleanup_error = exc

            _cleanup_step(
                lambda: self._write_state(
                    "stopping" if final_status == "stopped" else final_status
                )
            )
            _cleanup_step(self._stop_unit)
            _cleanup_step(lambda: self._write_state(final_status))
            _cleanup_step(
                lambda: self.logger.emit(
                    "supervisor_stopped", status=final_status, exit_code=exit_code
                )
            )
            try:
                _cleanup_step(lambda: self.config.pid_file.unlink(missing_ok=True))
            finally:
                self._lock.release()
            if cleanup_error is not None:
                raise cleanup_error
        return exit_code


def _default_runtime_dir() -> Path:
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError) as exc:
        raise SupervisorError(
            "SUPERVISOR_HOME_UNAVAILABLE", "系统用户主目录无法核验"
        ) from exc
    return (
        home
        / "Library"
        / "Application Support"
        / "com.zhifei.construction-expert"
        / "runtime"
    ).resolve()


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--python", dest="python_executable", type=Path, required=True)
    parser.add_argument("--backend-port", type=int, required=True)
    parser.add_argument("--ui-port", type=int, required=True)
    parser.add_argument("--expected-system-id", required=True)
    parser.add_argument("--expected-release-id", required=True)
    parser.add_argument("--expected-manifest-digest", required=True)
    parser.add_argument("--expected-source-digest", required=True)
    parser.add_argument("--expected-runtime-digest", required=True)
    parser.add_argument("--state-dir", type=Path, default=_default_runtime_dir())
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--env-file", type=Path)


def _config_from_args(args: argparse.Namespace) -> SupervisorConfig:
    state_dir = Path(os.path.abspath(os.fspath(args.state_dir)))
    log_dir = Path(os.path.abspath(os.fspath(args.log_dir or (state_dir / "logs"))))
    return SupervisorConfig(
        release_dir=args.release_dir.resolve(),
        python_executable=Path(os.path.abspath(os.fspath(args.python_executable))),
        backend_port=args.backend_port,
        ui_port=args.ui_port,
        identity=ExpectedIdentity(
            system_id=args.expected_system_id,
            release_id=args.expected_release_id,
            manifest_digest=args.expected_manifest_digest,
            source_digest=args.expected_source_digest,
            runtime_digest=args.expected_runtime_digest,
        ),
        state_dir=state_dir,
        log_dir=log_dir,
        env_file=(
            Path(os.path.abspath(os.fspath(args.env_file))) if args.env_file else None
        ),
    )


def _read_safe_state(state_dir: Path) -> dict[str, Any]:
    state_file = state_dir / STATE_FILE_NAME
    try:
        info = state_file.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or state_file.is_symlink()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 64 * 1024
        ):
            raise SupervisorError(
                "SUPERVISOR_STATE_UNTRUSTED", "监管状态文件权限或类型不可信"
            )
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "not_started", "running": False}
    except (OSError, UnicodeError, ValueError) as exc:
        raise SupervisorError(
            "SUPERVISOR_STATE_INVALID", "监管状态文件无法读取"
        ) from exc
    if not isinstance(payload, dict):
        raise SupervisorError("SUPERVISOR_STATE_INVALID", "监管状态格式无效")
    allowed = {
        "schema_version",
        "status",
        "release_id",
        "manifest_digest",
        "source_digest",
        "runtime_digest",
        "release_root",
        "supervisor_pid",
        "supervisor_instance_id",
        "backend_pid",
        "ui_pid",
        "circuit_open",
        "restart_count_window",
        "failure_timestamps",
        "last_health_at",
        "last_error_code",
        "health_degraded",
        "consecutive_health_failures",
        "first_health_failure_at",
        "last_probe_error_code",
        "started_at",
        "updated_at",
    }
    return {key: payload.get(key) for key in allowed if key in payload}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _process_command(pid: int) -> str:
    completed = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "command="],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=2,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def status_command(state_dir: Path) -> int:
    _require_absolute_path(state_dir, "state_dir")
    payload = _read_safe_state(state_dir)
    supervisor_pid = payload.get("supervisor_pid")
    running = False
    if isinstance(supervisor_pid, int) and _pid_alive(supervisor_pid):
        command = _process_command(supervisor_pid)
        running = (
            "runtime_supervisor.py" in command
            and " run " in f" {command} "
            and str(state_dir) in command
        )
    payload["running"] = bool(running)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if running else 3


def stop_command(state_dir: Path, timeout_seconds: float = 20.0) -> int:
    _require_absolute_path(state_dir, "state_dir")
    payload = _read_safe_state(state_dir)
    raw_pid = payload.get("supervisor_pid")
    if not isinstance(raw_pid, int) or raw_pid <= 1 or not _pid_alive(raw_pid):
        print(json.dumps({"status": "not_running"}, ensure_ascii=False))
        return 0
    command = _process_command(raw_pid)
    if (
        "runtime_supervisor.py" not in command
        or " run " not in f" {command} "
        or str(state_dir) not in command
    ):
        raise SupervisorError(
            "SUPERVISOR_PID_OWNERSHIP_MISMATCH", "状态中的 PID 不属于监管器"
        )
    os.kill(raw_pid, signal.SIGTERM)
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    while time.monotonic() < deadline and _pid_alive(raw_pid):
        time.sleep(0.1)
    if _pid_alive(raw_pid):
        os.kill(raw_pid, signal.SIGKILL)
        release_root = str(payload.get("release_root") or "")
        if release_root:
            _stop_orphaned_owned_group(
                payload.get("ui_pid"),
                required_fragments=("streamlit", str(Path(release_root) / "app.py")),
            )
            _stop_orphaned_owned_group(
                payload.get("backend_pid"),
                required_fragments=("uvicorn", "backend.app.main:app", release_root),
            )
    print(json.dumps({"status": "stopped"}, ensure_ascii=False))
    return 0


def _stop_orphaned_owned_group(
    raw_pid: Any, *, required_fragments: Sequence[str]
) -> None:
    """Best-effort forced cleanup after a wedged supervisor is killed."""

    if not isinstance(raw_pid, int) or raw_pid <= 1 or not _pid_alive(raw_pid):
        return
    command = _process_command(raw_pid)
    if not command or not all(fragment in command for fragment in required_fragments):
        return
    try:
        if os.getpgid(raw_pid) != raw_pid:
            return
        os.killpg(raw_pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and _pid_alive(raw_pid):
        time.sleep(0.05)
    if _pid_alive(raw_pid):
        try:
            os.killpg(raw_pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            return


def start_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    config.validate()
    script_path = Path(__file__).resolve()
    run_argv = [str(config.python_executable), str(script_path), "run"]
    forwarded = [
        ("--release-dir", str(config.release_dir)),
        ("--python", str(config.python_executable)),
        ("--backend-port", str(config.backend_port)),
        ("--ui-port", str(config.ui_port)),
        ("--expected-system-id", config.identity.system_id),
        ("--expected-release-id", config.identity.release_id),
        ("--expected-manifest-digest", config.identity.manifest_digest),
        ("--expected-source-digest", config.identity.source_digest),
        ("--expected-runtime-digest", config.identity.runtime_digest),
        ("--state-dir", str(config.state_dir)),
        ("--log-dir", str(config.log_dir)),
    ]
    for option, value in forwarded:
        run_argv.extend([option, value])
    if config.env_file is not None:
        run_argv.extend(["--env-file", str(config.env_file)])
    child = subprocess.Popen(
        run_argv,
        cwd=str(config.release_dir),
        env=dict(os.environ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise SupervisorError(
                "SUPERVISOR_START_FAILED", "监管器未能保持运行，请查看事件日志"
            )
        try:
            state = _read_safe_state(config.state_dir)
        except SupervisorError:
            state = {}
        if state.get("supervisor_pid") == child.pid and state.get("status") in {
            "starting",
            "healthy",
            "restarting",
        }:
            print(
                json.dumps(
                    {
                        "status": state.get("status"),
                        "supervisor_pid": child.pid,
                        "release_id": config.identity.release_id,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        time.sleep(0.1)
    child.terminate()
    raise SupervisorError(
        "SUPERVISOR_START_TIMEOUT", "监管器启动状态确认超时，请查看事件日志"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="施组专家系统不可变发布监管器")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="前台监管后端与界面")
    _add_run_arguments(run_parser)
    start_parser = subparsers.add_parser("start", help="后台启动监管器")
    _add_run_arguments(start_parser)
    status_parser = subparsers.add_parser("status", help="读取脱敏监管状态")
    status_parser.add_argument("--state-dir", type=Path, default=_default_runtime_dir())
    stop_parser = subparsers.add_parser("stop", help="停止监管单元")
    stop_parser.add_argument("--state-dir", type=Path, default=_default_runtime_dir())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "status":
            return status_command(args.state_dir.resolve())
        if args.command == "stop":
            return stop_command(args.state_dir.resolve())
        if args.command == "start":
            return start_command(args)
        config = _config_from_args(args)
        return RuntimeSupervisor(config).run()
    except SupervisorError as exc:
        print(
            json.dumps(
                {"ok": False, "error_code": exc.code, "message": exc.message},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "SUPERVISOR_UNEXPECTED_FAILURE",
                    "message": "监管器发生未分类故障，请查看脱敏事件日志",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
