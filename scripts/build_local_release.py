#!/usr/bin/env python3
"""Build and atomically select a fully verified local immutable release."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pwd
import re
import secrets
import shutil
import stat
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.zhifei_autoplan.sealed_compliance import (
    SEALED_COMPLIANCE_ROOT_RELATIVE_PATH,
    SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH,
    SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH,
)
from scripts.runtime_supervisor import (
    ExpectedIdentity,
    SupervisorError,
    compute_runtime_digest,
    compute_source_digest,
    verify_release_manifest,
)

SCHEMA_VERSION = 1
SYSTEM_ID_DEFAULT = "docgen-system"
CURRENT_JSON_NAME = "current.json"
CURRENT_LINK_NAME = "current"
CURRENT_FIELDS = frozenset(
    {
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
)
MANIFEST_NAME = "release-manifest.json"
PROVENANCE_NAME = "release-provenance.json"
TRUSTED_BOOTSTRAP_DIRECTORY_NAME = "bootstrap"
TRUSTED_BOOTSTRAP_NAME = "launch_current.py"
SOURCE_BOOTSTRAP_RELATIVE_PATH = Path("scripts/launch_latest_release_bootstrap.py")
BUILD_LOCK_NAME = "release-build.lock"
RETIRED_RELEASES_DIRECTORY_NAME = "retired-releases"
TRANSITION_INTENT_NAME = "release-transition.json"
MUTABLE_PATHS = (
    "backend/data",
    "build",
    "data",
    "logs",
    "artifacts",
    "projects",
    ".runtime",
    "知识图谱",
)
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".cache",
    "node_modules",
}
EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".coverage",
    MANIFEST_NAME,
    PROVENANCE_NAME,
}
EXCLUDED_RELATIVE_PATHS = {
    "docs/RUNTIME_ACCEPTANCE_REPORT.md",
    "docs/RUNTIME_REMEDIATION_REPORT.md",
}
EXCLUDED_FILE_SUFFIXES = {
    ".log",
    ".pyc",
    ".pyo",
    ".pid",
    ".sock",
    ".tmp",
}
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ENV_ACTIONS_RE = re.compile(r"^(?:export\s+)?ZF_ACTIONS_KEY\s*=\s*(.*)$")
_GIT_HEAD_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_RELEASE_ID_RE = re.compile(r"^release-[0-9a-f]{24}$")
_MAX_SEALED_REGISTRY_BYTES = 2 * 1024 * 1024


class ReleaseBuildError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def default_release_base() -> Path:
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError) as exc:
        raise ReleaseBuildError(
            "RELEASE_HOME_UNAVAILABLE", "系统用户主目录无法核验"
        ) from exc
    return (
        home
        / "Library"
        / "Application Support"
        / "com.zhifei.construction-expert"
    ).resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _source_vcs_metadata(source_root: Path) -> dict[str, Any]:
    """Capture non-network Git provenance without using it as file authority."""

    command_env = dict(os.environ)
    command_env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})

    def run(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=str(source_root),
                env=command_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    raw_head = run("rev-parse", "HEAD")
    head = raw_head if raw_head and _GIT_HEAD_RE.fullmatch(raw_head) else None
    branch = run("branch", "--show-current")
    if branch is not None:
        branch = branch[:255] or None
    porcelain = run("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "schema_version": 1,
        "build_sha": head,
        "source_branch": branch,
        "source_dirty": None if porcelain is None else bool(porcelain),
    }


def _atomic_write_bytes(path: Path, payload: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temporary, flags, mode)
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(payload):
            offset += os.write(fd, payload[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
        os.chmod(path, mode, follow_symlinks=False)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_write_json(path: Path, payload: Mapping[str, Any], *, mode: int) -> bytes:
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    _atomic_write_bytes(path, encoded, mode=mode)
    return encoded


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _secure_directory(path: Path) -> Path:
    path = Path(os.path.abspath(os.fspath(path)))
    if (path.exists() or path.is_symlink()) and (
        path.is_symlink() or not path.is_dir()
    ):
        raise ReleaseBuildError(
            "RELEASE_DIRECTORY_UNTRUSTED", "发布基础目录必须是普通目录"
        )
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if info.st_uid != os.getuid():
        raise ReleaseBuildError(
            "RELEASE_DIRECTORY_OWNER_MISMATCH", "发布基础目录不属于当前用户"
        )
    os.chmod(path, 0o700)
    return path


@contextmanager
def _exclusive_build_lock(base: Path):
    """Serialize every mutation of one local release base."""

    path = base / BUILD_LOCK_NAME
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd: int | None = None
    try:
        try:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
            os.fchmod(fd, 0o600)
            _fsync_directory(base)
        except FileExistsError:
            fd = os.open(path, os.O_RDWR | nofollow)
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise ReleaseBuildError(
            "RELEASE_BUILD_LOCK_UNAVAILABLE", "发布构建锁不可用"
        ) from exc
    assert fd is not None
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise ReleaseBuildError(
                "RELEASE_BUILD_LOCK_UNTRUSTED",
                "发布构建锁必须归当前用户所有且权限为0600",
            )
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _validate_secret_file(path: Path) -> bytes:
    path = Path(os.path.abspath(os.fspath(path)))
    try:
        info = path.lstat()
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SECRET_SOURCE_UNAVAILABLE", "密钥环境文件不可用"
        ) from exc
    if (
        not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_size > 1024 * 1024
    ):
        raise ReleaseBuildError(
            "RELEASE_SECRET_SOURCE_UNTRUSTED",
            "密钥环境文件必须归当前用户所有、为普通文件且权限为0600",
        )
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SECRET_SOURCE_UNAVAILABLE", "密钥环境文件不可用"
        ) from exc


def _has_actions_key(content: bytes) -> bool:
    try:
        text = content.decode("utf-8")
    except UnicodeError as exc:
        raise ReleaseBuildError(
            "RELEASE_SECRET_SOURCE_INVALID", "密钥环境文件必须是UTF-8文本"
        ) from exc
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_ACTIONS_RE.fullmatch(line)
        if not match:
            continue
        raw_value = match.group(1).strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {"'", '"'}:
            raw_value = raw_value[1:-1]
        return bool(raw_value)
    return False


def ensure_runtime_secret(
    *,
    base: Path,
    source_env: Path | None,
    token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
) -> Path:
    secrets_dir = _secure_directory(base / "secrets")
    destination = secrets_dir / "runtime.env"
    if destination.exists() or destination.is_symlink():
        _validate_secret_file(destination)
        return destination

    content = b""
    if source_env is not None and source_env.exists():
        content = _validate_secret_file(source_env)
    if not _has_actions_key(content):
        generated = token_factory()
        if not generated or any(character in generated for character in "\x00\r\n"):
            raise ReleaseBuildError(
                "RELEASE_ACTIONS_KEY_GENERATION_FAILED", "本机操作凭据生成失败"
            )
        if content and not content.endswith(b"\n"):
            content += b"\n"
        content += f"ZF_ACTIONS_KEY={generated}\n".encode()
    _atomic_write_bytes(destination, content, mode=0o600)
    return destination


def _read_bootstrap_source(path: Path) -> bytes:
    path = Path(os.path.abspath(os.fspath(path)))
    try:
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or path.is_symlink()
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) & 0o222
            or before.st_size <= 0
            or before.st_size > 2 * 1024 * 1024
        ):
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_SOURCE_UNTRUSTED",
                "固定启动入口源文件类型、所有者或大小不可信",
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            descriptor = os.fstat(fd)
            chunks: list[bytes] = []
            while chunk := os.read(fd, 1024 * 1024):
                chunks.append(chunk)
        finally:
            os.close(fd)
        after = path.lstat()
    except ReleaseBuildError:
        raise
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_BOOTSTRAP_SOURCE_UNAVAILABLE", "固定启动入口源文件不可用"
        ) from exc
    signature = lambda info: (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_mode,
    )
    if signature(before) != signature(descriptor) or signature(before) != signature(after):
        raise ReleaseBuildError(
            "RELEASE_BOOTSTRAP_SOURCE_CHANGED", "读取期间固定启动入口源文件发生变化"
        )
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise ReleaseBuildError(
            "RELEASE_BOOTSTRAP_SOURCE_CHANGED", "读取期间固定启动入口源文件发生变化"
        )
    return payload


def ensure_trusted_bootstrap(*, base: Path, source_root: Path) -> tuple[Path, str]:
    """Install the one fixed pre-runtime trust root, without automatic upgrades."""

    source = source_root / SOURCE_BOOTSTRAP_RELATIVE_PATH
    payload = _read_bootstrap_source(source)
    digest = hashlib.sha256(payload).hexdigest()
    directory = base / TRUSTED_BOOTSTRAP_DIRECTORY_NAME
    destination = directory / TRUSTED_BOOTSTRAP_NAME

    if directory.exists() or directory.is_symlink():
        try:
            directory_info = directory.lstat()
        except OSError as exc:
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_DIRECTORY_UNTRUSTED", "固定启动入口目录不可用"
            ) from exc
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or directory.is_symlink()
            or directory_info.st_uid != os.getuid()
            or stat.S_IMODE(directory_info.st_mode) != 0o555
        ):
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_DIRECTORY_UNTRUSTED",
                "既有固定启动入口目录必须归当前用户所有且权限为0555",
            )
        try:
            destination_info = destination.lstat()
            existing = _read_bootstrap_source(destination)
        except (OSError, ReleaseBuildError) as exc:
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_UNAVAILABLE", "既有固定启动入口不可用"
            ) from exc
        if (
            not stat.S_ISREG(destination_info.st_mode)
            or destination.is_symlink()
            or destination_info.st_uid != os.getuid()
            or stat.S_IMODE(destination_info.st_mode) != 0o444
            or hashlib.sha256(existing).hexdigest() != digest
            or existing != payload
        ):
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_MISMATCH",
                "既有固定启动入口与当前可信源不一致，禁止自动替换",
            )
        return destination, digest

    staging = base / f".{TRUSTED_BOOTSTRAP_DIRECTORY_NAME}.{uuid.uuid4().hex}.staging"
    staged_destination = staging / TRUSTED_BOOTSTRAP_NAME
    try:
        staging.mkdir(mode=0o700)
        _atomic_write_bytes(staged_destination, payload, mode=0o444)
        written_info = staged_destination.lstat()
        if (
            not stat.S_ISREG(written_info.st_mode)
            or staged_destination.is_symlink()
            or written_info.st_uid != os.getuid()
            or stat.S_IMODE(written_info.st_mode) != 0o444
            or _sha256_file(staged_destination) != digest
        ):
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_REVERSE_VERIFY_FAILED",
                "固定启动入口写入后反向校验失败",
            )
        os.chmod(staging, 0o555)
        if directory.exists() or directory.is_symlink():
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_INSTALL_RACE",
                "固定启动入口安装目标在切换前出现",
            )
        os.replace(staging, directory)
        _fsync_directory(base)
        directory_info = directory.lstat()
        destination_info = destination.lstat()
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or directory.is_symlink()
            or directory_info.st_uid != os.getuid()
            or stat.S_IMODE(directory_info.st_mode) != 0o555
            or not stat.S_ISREG(destination_info.st_mode)
            or destination.is_symlink()
            or destination_info.st_uid != os.getuid()
            or stat.S_IMODE(destination_info.st_mode) != 0o444
            or _sha256_file(destination) != digest
        ):
            raise ReleaseBuildError(
                "RELEASE_BOOTSTRAP_REVERSE_VERIFY_FAILED",
                "固定启动入口原子安装后反向校验失败",
            )
    except ReleaseBuildError:
        raise
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_BOOTSTRAP_INSTALL_FAILED", "固定启动入口安装失败"
        ) from exc
    finally:
        # A live exception can clean its private sibling.  A SIGKILL may leave
        # the uniquely named staging directory, which is never treated as the
        # fixed trust root and is therefore safe for a later build to ignore.
        if staging.exists() and staging.is_dir() and not staging.is_symlink():
            try:
                os.chmod(staging, 0o700)
                if staged_destination.exists() and not staged_destination.is_symlink():
                    os.chmod(staged_destination, 0o600)
                    staged_destination.unlink()
                staging.rmdir()
            except OSError:
                pass
    return destination, digest


def _relative_text(path: Path) -> str:
    return path.as_posix()


def _is_mutable_path(relative: str) -> bool:
    return relative in MUTABLE_PATHS


def _is_excluded(relative: Path, *, is_directory: bool) -> bool:
    if relative.as_posix() in EXCLUDED_RELATIVE_PATHS:
        return True
    name = relative.name
    parts = relative.parts
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in parts):
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    if is_directory:
        return False
    if name in EXCLUDED_FILE_NAMES:
        return True
    if Path(name).suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return True
    return bool(name.endswith("~") or name.startswith(".#"))


def _source_inventory(root: Path) -> tuple[list[Path], list[Path], dict[str, tuple[Any, ...]]]:
    directories: list[Path] = []
    files: list[Path] = []
    signatures: dict[str, tuple[Any, ...]] = {}

    def visit(directory: Path, relative_parent: Path = Path()) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise ReleaseBuildError(
                "RELEASE_SOURCE_UNREADABLE", "源代码目录无法遍历"
            ) from exc
        for child in children:
            relative = relative_parent / child.name
            relative_text = _relative_text(relative)
            if _is_mutable_path(relative_text):
                continue
            try:
                if child.is_symlink():
                    raise ReleaseBuildError(
                        "RELEASE_SOURCE_SYMLINK_UNSUPPORTED",
                        f"源快照存在未准入符号链接: {relative_text}",
                    )
                if child.is_dir(follow_symlinks=False):
                    if _is_excluded(relative, is_directory=True):
                        continue
                    info = child.stat(follow_symlinks=False)
                    directories.append(relative)
                    signatures[relative_text] = (
                        "directory",
                        info.st_dev,
                        info.st_ino,
                        stat.S_IMODE(info.st_mode),
                        info.st_mtime_ns,
                    )
                    visit(Path(child.path), relative)
                elif child.is_file(follow_symlinks=False):
                    if _is_excluded(relative, is_directory=False):
                        continue
                    info = child.stat(follow_symlinks=False)
                    files.append(relative)
                    signatures[relative_text] = (
                        "file",
                        info.st_dev,
                        info.st_ino,
                        stat.S_IMODE(info.st_mode),
                        info.st_size,
                        info.st_mtime_ns,
                    )
                else:
                    raise ReleaseBuildError(
                        "RELEASE_SOURCE_ENTRY_UNSUPPORTED",
                        f"源快照存在不支持的文件类型: {relative_text}",
                    )
            except OSError as exc:
                raise ReleaseBuildError(
                    "RELEASE_SOURCE_UNREADABLE", "源代码条目无法读取"
                ) from exc

    visit(root)
    return directories, files, signatures


def _copy_inventory(
    source_root: Path,
    destination_root: Path,
    directories: Sequence[Path],
    files: Sequence[Path],
) -> None:
    for relative in sorted(directories, key=lambda item: (len(item.parts), item.as_posix())):
        destination = destination_root / relative
        destination.mkdir(mode=0o700)
    for relative in sorted(files, key=lambda item: item.as_posix()):
        source = source_root / relative
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        before = source.lstat()
        if not stat.S_ISREG(before.st_mode) or source.is_symlink():
            raise ReleaseBuildError(
                "RELEASE_SOURCE_CHANGED", f"复制期间源文件类型发生变化: {relative.as_posix()}"
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        source_fd = os.open(source, flags)
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            stat.S_IMODE(before.st_mode),
        )
        try:
            while chunk := os.read(source_fd, 1024 * 1024):
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_fd, view)
                    view = view[written:]
            os.fsync(destination_fd)
            source_info = os.fstat(source_fd)
        finally:
            os.close(destination_fd)
            os.close(source_fd)
        after = source.lstat()
        before_signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        after_signature = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        descriptor_signature = (
            source_info.st_dev,
            source_info.st_ino,
            source_info.st_size,
            source_info.st_mtime_ns,
        )
        if before_signature != after_signature or before_signature != descriptor_signature:
            raise ReleaseBuildError(
                "RELEASE_SOURCE_CHANGED", f"复制期间源文件发生变化: {relative.as_posix()}"
            )


def _read_authoritative_registry(
    source_root: Path,
) -> tuple[bytes, tuple[int, int, int, int, int, str]]:
    source = source_root / SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH
    current = source_root
    try:
        for index, part in enumerate(SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH.parts):
            current = current / part
            info = current.lstat()
            if current.is_symlink():
                raise ReleaseBuildError(
                    "RELEASE_SEALED_REGISTRY_SOURCE_UNTRUSTED",
                    "正式标准registry源路径不得包含符号链接",
                )
            if index < len(SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH.parts) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    raise ReleaseBuildError(
                        "RELEASE_SEALED_REGISTRY_SOURCE_UNTRUSTED",
                        "正式标准registry源目录类型不可信",
                    )
            elif not stat.S_ISREG(info.st_mode):
                raise ReleaseBuildError(
                    "RELEASE_SEALED_REGISTRY_SOURCE_UNTRUSTED",
                    "正式标准registry源必须是普通文件",
                )
    except FileNotFoundError as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_MISSING",
            "源代码缺少正式标准registry",
        ) from exc
    except ReleaseBuildError:
        raise
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_UNREADABLE",
            "正式标准registry源路径无法验证",
        ) from exc

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(source, flags)
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_UNREADABLE",
            "正式标准registry源无法安全读取",
        ) from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size <= 0
            or before.st_size > _MAX_SEALED_REGISTRY_BYTES
        ):
            raise ReleaseBuildError(
                "RELEASE_SEALED_REGISTRY_SOURCE_UNTRUSTED",
                "正式标准registry源类型、所有者或大小不可信",
            )
        chunks: list[bytes] = []
        remaining = _MAX_SEALED_REGISTRY_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(raw) > _MAX_SEALED_REGISTRY_BYTES or len(raw) != before.st_size:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_UNTRUSTED",
            "正式标准registry源大小超出限制或读取不完整",
        )
    signature_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
    if any(getattr(before, field) != getattr(after, field) for field in signature_fields):
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_CHANGED",
            "读取期间正式标准registry源发生变化",
        )
    try:
        current_info = source.lstat()
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_CHANGED",
            "读取后正式标准registry源无法复验",
        ) from exc
    if source.is_symlink() or any(
        getattr(after, field) != getattr(current_info, field)
        for field in signature_fields
    ):
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_SOURCE_CHANGED",
            "读取后正式标准registry源身份发生变化",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_INVALID",
            "正式标准registry不是有效UTF-8 JSON",
        ) from exc
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("standards"), list)
        or not payload["standards"]
        or not all(isinstance(row, dict) for row in payload["standards"])
    ):
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_INVALID",
            "正式标准registry缺少有效标准元数据",
        )
    digest = hashlib.sha256(raw).hexdigest()
    signature = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        stat.S_IMODE(after.st_mode),
        digest,
    )
    return raw, signature


def _install_sealed_compliance_registry(
    *,
    source_root: Path,
    destination_root: Path,
) -> tuple[int, int, int, int, int, str]:
    raw, signature = _read_authoritative_registry(source_root)
    sealed_root = destination_root / SEALED_COMPLIANCE_ROOT_RELATIVE_PATH
    destination = destination_root / SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH
    if sealed_root.exists() or sealed_root.is_symlink():
        raise ReleaseBuildError(
            "RELEASE_SEALED_COMPLIANCE_COLLISION",
            "发布源与专用密封标准目录发生冲突",
        )
    sealed_root.mkdir(parents=True, mode=0o700)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(destination, flags, 0o600)
        try:
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("sealed registry write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_INSTALL_FAILED",
            "正式标准registry无法写入专用密封目录",
        ) from exc
    if _sha256_file(destination) != signature[-1]:
        raise ReleaseBuildError(
            "RELEASE_SEALED_REGISTRY_INSTALL_MISMATCH",
            "专用密封registry写入后摘要不一致",
        )
    return signature


def _prepare_mutable_targets(
    *,
    source_root: Path,
    base: Path,
    seed_state: bool,
) -> dict[str, Path]:
    state_root = _secure_directory(base / "state")
    workspace_state = _secure_directory(state_root / "workspace")
    targets: dict[str, Path] = {}
    for relative_text in MUTABLE_PATHS:
        relative = Path(PurePosixPath(relative_text))
        source = source_root / relative
        target = workspace_state / relative
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not target.is_dir():
                raise ReleaseBuildError(
                    "RELEASE_MUTABLE_STATE_UNTRUSTED",
                    f"外部状态目标不是普通目录: {relative_text}",
                )
        else:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if seed_state and source.exists():
                if source.is_symlink() or not source.is_dir():
                    raise ReleaseBuildError(
                        "RELEASE_MUTABLE_SOURCE_UNTRUSTED",
                        f"可变源不是普通目录: {relative_text}",
                    )
                shutil.copytree(source, target, symlinks=True)
            else:
                target.mkdir(mode=0o700)
        os.chmod(target, 0o700)
        targets[relative_text] = target.resolve()
    return targets


def _install_mutable_links(destination_root: Path, targets: Mapping[str, Path]) -> None:
    for relative_text, target in sorted(targets.items()):
        link = destination_root / Path(PurePosixPath(relative_text))
        link.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if link.exists() or link.is_symlink():
            raise ReleaseBuildError(
                "RELEASE_MUTABLE_LINK_COLLISION", f"可变链接路径冲突: {relative_text}"
            )
        os.symlink(str(target), link)


def _freeze_tree(root: Path, *, include_root: bool = True) -> None:
    directories: list[Path] = []
    for current, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dir_names[:] = sorted(
            name for name in dir_names if not (current_path / name).is_symlink()
        )
        for name in sorted(file_names):
            path = current_path / name
            if path.is_symlink():
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ReleaseBuildError(
                    "RELEASE_FREEZE_ENTRY_UNSUPPORTED", "只读发布存在不支持的文件类型"
                )
            os.chmod(path, 0o555 if stat.S_IMODE(info.st_mode) & 0o111 else 0o444)
        directories.extend(current_path / name for name in dir_names)
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        os.chmod(directory, 0o555)
    if include_root:
        os.chmod(root, 0o555)


def _make_tree_writable_for_cleanup(root: Path) -> None:
    if not root.exists() or root.is_symlink():
        return
    for current, dir_names, file_names in os.walk(root, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in file_names:
            path = current_path / name
            if not path.is_symlink():
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass
        for name in dir_names:
            path = current_path / name
            if not path.is_symlink():
                try:
                    os.chmod(path, 0o700)
                except OSError:
                    pass
        try:
            os.chmod(current_path, 0o700)
        except OSError:
            pass


def _assert_tree_read_only(root: Path) -> None:
    for current, dir_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        current_info = current_path.lstat()
        if stat.S_IMODE(current_info.st_mode) & 0o222:
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_NOT_READ_ONLY", "运行时目录仍包含可写目录"
            )
        dir_names[:] = [
            name for name in dir_names if not (current_path / name).is_symlink()
        ]
        for name in file_names:
            path = current_path / name
            if path.is_symlink():
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o222:
                raise ReleaseBuildError(
                    "RELEASE_RUNTIME_NOT_READ_ONLY", "运行时目录仍包含可写文件"
                )


def _remove_staging(root: Path) -> None:
    if not root.exists() or root.is_symlink():
        return
    _make_tree_writable_for_cleanup(root)
    shutil.rmtree(root)


def _runtime_python(runtime_root: Path) -> Path:
    candidates = (
        runtime_root / "venv" / "bin" / "python",
        runtime_root / "venv" / "bin" / "python3",
    )
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    raise ReleaseBuildError(
        "RELEASE_RUNTIME_PYTHON_MISSING", "复制的运行时缺少可执行Python"
    )


_PYTHON_SHEBANG_RE = re.compile(
    rb"^#![^\r\n]*python(?:\d+(?:\.\d+)*)?(?:[ \t][^\r\n]*)?\r?\n"
)
_RELOCATABLE_CONSOLE_PREFIX = (
    b"#!/bin/sh\n"
    b"'''exec' \"$(dirname -- \"$0\")/python\" \"$0\" \"$@\"\n"
    b"' '''\n"
)


def _relocate_console_scripts(venv_root: Path) -> int:
    """Remove absolute source-venv shebangs from copied Python entrypoints."""

    bin_dir = venv_root / "bin"
    if not bin_dir.is_dir() or bin_dir.is_symlink():
        raise ReleaseBuildError(
            "RELEASE_RUNTIME_BIN_INVALID", "复制的运行时缺少可信 bin 目录"
        )
    relocated = 0
    for entry in sorted(os.scandir(bin_dir), key=lambda item: item.name):
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            continue
        path = Path(entry.path)
        info = path.lstat()
        if not stat.S_IMODE(info.st_mode) & 0o111:
            continue
        with path.open("rb") as handle:
            first_line = handle.readline(4096)
            remainder = handle.read()
        if not _PYTHON_SHEBANG_RE.fullmatch(first_line):
            continue
        path.write_bytes(_RELOCATABLE_CONSOLE_PREFIX + remainder)
        path.chmod(stat.S_IMODE(info.st_mode))
        relocated += 1
    return relocated


def _assert_console_scripts_relocatable(venv_root: Path) -> None:
    bin_dir = venv_root / "bin"
    for entry in sorted(os.scandir(bin_dir), key=lambda item: item.name):
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            continue
        path = Path(entry.path)
        info = path.lstat()
        if not stat.S_IMODE(info.st_mode) & 0o111:
            continue
        with path.open("rb") as handle:
            prefix = handle.read(max(4096, len(_RELOCATABLE_CONSOLE_PREFIX)))
        first_line = prefix.splitlines(keepends=True)[:1]
        if first_line and _PYTHON_SHEBANG_RE.fullmatch(first_line[0]):
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_ABSOLUTE_SHEBANG",
                f"运行时命令仍绑定外部Python: {entry.name}",
            )
        if prefix.startswith(b"#!/bin/sh\n'''exec'") and not prefix.startswith(
            _RELOCATABLE_CONSOLE_PREFIX
        ):
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_CONSOLE_WRAPPER_INVALID",
                f"运行时命令相对启动器无效: {entry.name}",
            )


def build_runtime(
    *,
    source_venv: Path,
    runtimes_dir: Path,
    digest_fn: Callable[[Path], str] = compute_runtime_digest,
) -> tuple[str, Path]:
    source_venv = Path(os.path.abspath(os.fspath(source_venv)))
    if not source_venv.is_dir() or source_venv.is_symlink():
        raise ReleaseBuildError(
            "RELEASE_RUNTIME_SOURCE_INVALID", "源Python运行时必须是普通目录"
        )
    runtimes_dir = _secure_directory(runtimes_dir)
    staging = runtimes_dir / f".staging-{uuid.uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        shutil.copytree(source_venv, staging / "venv", symlinks=True)
        staging_python = _runtime_python(staging)
        _relocate_console_scripts(staging / "venv")
        _assert_console_scripts_relocatable(staging / "venv")
        _freeze_tree(staging)
        digest = digest_fn(staging_python)
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_DIGEST_INVALID", "运行时摘要格式无效"
            )
        if digest_fn(staging_python) != digest:
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_REVERSE_VERIFY_FAILED", "冻结运行时反向摘要不一致"
            )
        _assert_tree_read_only(staging)
        destination = runtimes_dir / digest
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_dir():
                raise ReleaseBuildError(
                    "RELEASE_RUNTIME_DESTINATION_UNTRUSTED", "运行时摘要目标不可信"
                )
            existing_python = _runtime_python(destination)
            if digest_fn(existing_python) != digest:
                raise ReleaseBuildError(
                    "RELEASE_RUNTIME_EXISTING_MISMATCH", "已有运行时摘要反向校验失败"
                )
            _assert_tree_read_only(destination)
            _assert_console_scripts_relocatable(destination / "venv")
            _remove_staging(staging)
        else:
            os.replace(staging, destination)
            _fsync_directory(runtimes_dir)
        final_python = _runtime_python(destination)
        if digest_fn(final_python) != digest:
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_REVERSE_VERIFY_FAILED", "最终运行时摘要反向校验失败"
            )
        _assert_tree_read_only(destination)
        _assert_console_scripts_relocatable(destination / "venv")
        return digest, final_python
    except Exception:
        _remove_staging(staging)
        raise


def _manifest_entries(
    release_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    mutable_links: list[dict[str, str]] = []

    def visit(directory: Path, prefix: str = "") -> None:
        for child in sorted(os.scandir(directory), key=lambda item: item.name):
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if relative == MANIFEST_NAME:
                continue
            path = Path(child.path)
            if child.is_symlink():
                if relative not in MUTABLE_PATHS:
                    raise ReleaseBuildError(
                        "RELEASE_UNDECLARED_SYMLINK", f"发布树存在未声明链接: {relative}"
                    )
                mutable_links.append({"path": relative, "target": os.readlink(path)})
            elif child.is_dir(follow_symlinks=False):
                info = path.lstat()
                directories.append({"path": relative, "mode": stat.S_IMODE(info.st_mode)})
                visit(path, relative)
            elif child.is_file(follow_symlinks=False):
                info = path.lstat()
                files.append(
                    {
                        "path": relative,
                        "size": info.st_size,
                        "mode": stat.S_IMODE(info.st_mode),
                        "sha256": _sha256_file(path),
                    }
                )
            else:
                raise ReleaseBuildError(
                    "RELEASE_ENTRY_UNSUPPORTED", f"发布树存在不支持的条目: {relative}"
                )

    visit(release_root)
    return files, directories, mutable_links


def build_source_release(
    *,
    source_root: Path,
    base: Path,
    runtime_digest: str,
    system_id: str,
    seed_state: bool,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
    provenance_fn: Callable[[Path], dict[str, Any]] = _source_vcs_metadata,
) -> tuple[ExpectedIdentity, Path]:
    releases_dir = _secure_directory(base / "releases")
    staging = releases_dir / f".staging-{uuid.uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        provenance_before = provenance_fn(source_root)
        before_dirs, before_files, before_signatures = _source_inventory(source_root)
        _copy_inventory(source_root, staging, before_dirs, before_files)
        registry_signature = _install_sealed_compliance_registry(
            source_root=source_root,
            destination_root=staging,
        )
        _, _, after_signatures = _source_inventory(source_root)
        _registry_raw, registry_signature_after = _read_authoritative_registry(
            source_root
        )
        provenance_after = provenance_fn(source_root)
        if (
            after_signatures != before_signatures
            or registry_signature_after != registry_signature
            or provenance_after != provenance_before
        ):
            raise ReleaseBuildError(
                "RELEASE_SOURCE_CHANGED", "构建期间源代码目录发生变化"
            )
        targets = _prepare_mutable_targets(
            source_root=source_root,
            base=base,
            seed_state=seed_state,
        )
        _install_mutable_links(staging, targets)
        provenance = {
            **provenance_before,
            "runtime_digest": runtime_digest,
        }
        _atomic_write_json(
            staging / PROVENANCE_NAME,
            provenance,
            mode=0o444,
        )
        _freeze_tree(staging, include_root=False)
        files, directories, mutable_links = _manifest_entries(staging)
        source_digest = compute_source_digest(files, directories, mutable_links)
        release_id = f"release-{source_digest[:24]}"
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "release_id": release_id,
            "source_digest": source_digest,
            "runtime_digest": runtime_digest,
            "files": sorted(files, key=lambda item: item["path"]),
            "directories": sorted(directories, key=lambda item: item["path"]),
            "mutable_links": sorted(mutable_links, key=lambda item: item["path"]),
        }
        manifest_bytes = _atomic_write_json(staging / MANIFEST_NAME, manifest, mode=0o444)
        manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
        identity = ExpectedIdentity(
            system_id=system_id,
            release_id=release_id,
            manifest_digest=manifest_digest,
            source_digest=source_digest,
            runtime_digest=runtime_digest,
        )
        os.chmod(staging, 0o555)
        verify_fn(staging, identity)

        destination = releases_dir / release_id
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_dir():
                raise ReleaseBuildError(
                    "RELEASE_DESTINATION_UNTRUSTED", "已有发布目标不可信"
                )
            verify_fn(destination, identity)
            _remove_staging(staging)
        else:
            os.replace(staging, destination)
            _fsync_directory(releases_dir)
        verify_fn(destination, identity)
        return identity, destination
    except Exception:
        _remove_staging(staging)
        raise


def _validate_existing_pointer(path: Path, *, symlink: bool) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    info = path.lstat()
    if symlink:
        if not stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
            raise ReleaseBuildError(
                "RELEASE_CURRENT_POINTER_UNTRUSTED", "current 必须是符号链接"
            )
    elif (
        not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ReleaseBuildError(
            "RELEASE_CURRENT_METADATA_UNTRUSTED", "current.json 权限或类型不可信"
        )


def _validate_current_payload(
    payload: Any,
    *,
    base: Path,
    code: str,
    message: str,
) -> None:
    if (
        not isinstance(payload, Mapping)
        or set(payload) != CURRENT_FIELDS
        or payload.get("schema_version") != SCHEMA_VERSION
    ):
        raise ReleaseBuildError(code, message)
    try:
        identity = ExpectedIdentity(
            system_id=str(payload["system_id"]),
            release_id=str(payload["release_id"]),
            manifest_digest=str(payload["manifest_digest"]),
            source_digest=str(payload["source_digest"]),
            runtime_digest=str(payload["runtime_digest"]),
        )
        identity.validate()
    except (KeyError, SupervisorError) as exc:
        raise ReleaseBuildError(code, message) from exc
    if identity.release_id != f"release-{identity.source_digest[:24]}":
        raise ReleaseBuildError(code, message)

    expected_paths = {
        "release_dir": base / "releases" / identity.release_id,
        "env_file": base / "secrets" / "runtime.env",
        "state_dir": base / "state" / "supervisor",
        "log_dir": base / "state" / "supervisor" / "logs",
    }
    for field, expected in expected_paths.items():
        value = payload.get(field)
        if not isinstance(value, str) or Path(value) != expected:
            raise ReleaseBuildError(code, message)
    python_value = payload.get("python_executable")
    expected_bin = base / "runtimes" / identity.runtime_digest / "venv" / "bin"
    if (
        not isinstance(python_value, str)
        or Path(python_value) not in (expected_bin / "python", expected_bin / "python3")
    ):
        raise ReleaseBuildError(code, message)
    backend_port = payload.get("backend_port")
    ui_port = payload.get("ui_port")
    if (
        isinstance(backend_port, bool)
        or isinstance(ui_port, bool)
        or not isinstance(backend_port, int)
        or not isinstance(ui_port, int)
        or backend_port == ui_port
        or not all(1 <= port <= 65535 for port in (backend_port, ui_port))
    ):
        raise ReleaseBuildError(code, message)


def _load_current_components(
    base: Path, *, allow_incomplete: bool = False
) -> dict[str, Any] | None:
    """Read and validate both current pointer halves without requiring equality.

    A durable release switch necessarily has a very small interval in which
    ``current.json`` and ``current`` name different, independently valid
    releases.  Normal launch paths must reject that split state, while the
    transition recovery path must be able to inspect it without executing
    either candidate.
    """

    current_json = base / CURRENT_JSON_NAME
    current_link = base / CURRENT_LINK_NAME
    json_exists = current_json.exists() or current_json.is_symlink()
    link_exists = current_link.exists() or current_link.is_symlink()
    if not json_exists and not link_exists:
        return None
    if json_exists != link_exists and not allow_incomplete:
        raise ReleaseBuildError(
            "RELEASE_CURRENT_POINTER_INCOMPLETE", "current 与 current.json 必须同时存在"
        )
    raw: bytes | None = None
    payload: dict[str, Any] | None = None
    release_id: str | None = None
    release_dir: str | None = None
    link_target: str | None = None
    if json_exists:
        _validate_existing_pointer(current_json, symlink=False)
        try:
            if current_json.stat().st_size > 128 * 1024:
                raise ReleaseBuildError(
                    "RELEASE_CURRENT_METADATA_UNTRUSTED", "current.json 大小超出限制"
                )
            raw = current_json.read_bytes()
            decoded = json.loads(raw.decode("utf-8"))
        except ReleaseBuildError:
            raise
        except (OSError, UnicodeError, ValueError) as exc:
            raise ReleaseBuildError(
                "RELEASE_CURRENT_METADATA_INVALID", "current.json 无法核验"
            ) from exc
        _validate_current_payload(
            decoded,
            base=base,
            code="RELEASE_CURRENT_METADATA_INVALID",
            message="current.json 内容无效",
        )
        payload = dict(decoded)
        release_id = payload.get("release_id")
        release_dir = payload.get("release_dir")
        if (
            not isinstance(release_id, str)
            or not _RELEASE_ID_RE.fullmatch(release_id)
            or not isinstance(release_dir, str)
            or not Path(release_dir).is_absolute()
            or Path(release_dir) != base / "releases" / release_id
        ):
            raise ReleaseBuildError(
                "RELEASE_CURRENT_METADATA_INVALID", "current.json 发布身份无效"
            )
    if link_exists:
        _validate_existing_pointer(current_link, symlink=True)
        try:
            link_target = os.readlink(current_link)
        except OSError as exc:
            raise ReleaseBuildError(
                "RELEASE_CURRENT_METADATA_INVALID", "current 无法核验"
            ) from exc
    return {
        "raw": raw,
        "payload": payload,
        "link_target": link_target,
        "release_id": release_id,
        "release_dir": release_dir,
    }


def _load_current_pointer(base: Path) -> dict[str, Any] | None:
    current = _load_current_components(base)
    if current is None:
        return None
    if (
        current["payload"] is None
        or current["link_target"] is None
        or current["release_dir"] != current["link_target"]
    ):
        raise ReleaseBuildError(
            "RELEASE_CURRENT_POINTER_MISMATCH", "current 与 current.json 身份不一致"
        )
    return current


def _assert_current_unchanged(base: Path, expected: Mapping[str, Any] | None) -> None:
    actual = _load_current_pointer(base)
    if actual != expected:
        raise ReleaseBuildError(
            "RELEASE_CURRENT_CHANGED", "发布切换期间 current 指针发生变化"
        )


def _retired_marker_path(base: Path, release_id: str) -> Path:
    if not _RELEASE_ID_RE.fullmatch(release_id):
        raise ReleaseBuildError(
            "RELEASE_ID_INVALID", "发布身份格式无效"
        )
    directory = _secure_directory(
        base / "state" / RETIRED_RELEASES_DIRECTORY_NAME
    )
    return directory / f"{release_id}.json"


def _validate_retired_marker(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ReleaseBuildError(
            "RELEASE_RETIRED_MARKER_UNAVAILABLE", "退役发布记录不可用"
        ) from exc
    if (
        not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_size > 128 * 1024
    ):
        raise ReleaseBuildError(
            "RELEASE_RETIRED_MARKER_UNTRUSTED", "退役发布记录类型或权限不可信"
        )


def _is_retired(base: Path, release_id: str) -> bool:
    marker = _retired_marker_path(base, release_id)
    if not (marker.exists() or marker.is_symlink()):
        return False
    _validate_retired_marker(marker)
    return True


def _record_retired_release(
    base: Path,
    current: Mapping[str, Any],
    *,
    superseded_by_release_id: str,
) -> Path | None:
    release_id = str(current["release_id"])
    marker = _retired_marker_path(base, release_id)
    if marker.exists() or marker.is_symlink():
        _validate_retired_marker(marker)
        return None
    _atomic_write_json(
        marker,
        {
            "schema_version": 1,
            "release_id": release_id,
            "release_dir": str(current["release_dir"]),
            "superseded_by_release_id": superseded_by_release_id,
        },
        mode=0o600,
    )
    return marker


def _transition_intent_path(base: Path) -> Path:
    state = _secure_directory(base / "state")
    return state / TRANSITION_INTENT_NAME


def _load_transition_intent(base: Path) -> dict[str, Any] | None:
    path = _transition_intent_path(base)
    if not (path.exists() or path.is_symlink()):
        return None
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or path.is_symlink()
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 128 * 1024
        ):
            raise ReleaseBuildError(
                "RELEASE_TRANSITION_INTENT_UNTRUSTED",
                "发布切换意图记录类型或权限不可信",
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ReleaseBuildError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_INVALID", "发布切换意图记录无法核验"
        ) from exc
    fields = {"schema_version", "old_current", "new_current"}
    if not isinstance(payload, dict) or set(payload) != fields or payload.get(
        "schema_version"
    ) != 2:
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_INVALID", "发布切换意图记录字段无效"
        )
    old_current = payload.get("old_current")
    new_current = payload.get("new_current")
    if old_current is not None:
        _validate_current_payload(
            old_current,
            base=base,
            code="RELEASE_TRANSITION_INTENT_INVALID",
            message="发布切换意图旧身份无效",
        )
    _validate_current_payload(
        new_current,
        base=base,
        code="RELEASE_TRANSITION_INTENT_INVALID",
        message="发布切换意图新身份无效",
    )
    if (
        (old_current is not None and not isinstance(old_current, Mapping))
        or not isinstance(new_current, Mapping)
        or (
            isinstance(old_current, Mapping)
            and (
                old_current["release_id"] == new_current["release_id"]
                or old_current["release_dir"] == new_current["release_dir"]
            )
        )
    ):
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_INVALID", "发布切换意图记录身份无效"
        )
    return payload


def _remove_transition_intent(base: Path) -> None:
    path = _transition_intent_path(base)
    path.unlink(missing_ok=True)
    _fsync_directory(path.parent)


def _write_transition_intent(
    base: Path,
    current: Mapping[str, Any] | None,
    *,
    new_current: Mapping[str, Any],
) -> None:
    path = _transition_intent_path(base)
    if path.exists() or path.is_symlink():
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_EXISTS", "已有未完成发布切换意图"
        )
    old_current = None if current is None else current.get("payload")
    if current is not None and not isinstance(old_current, Mapping):
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_INVALID", "旧发布完整身份不可用"
        )
    intent = {
        "schema_version": 2,
        "old_current": None if old_current is None else dict(old_current),
        "new_current": dict(new_current),
    }
    _atomic_write_json(path, intent, mode=0o600)
    # Reverse-validate the durable bytes before either current half changes.
    if _load_transition_intent(base) != intent:
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_INTENT_INVALID", "发布切换意图反向核验失败"
        )


def _replace_current_link(base: Path, target: str) -> None:
    temporary = base / f".{CURRENT_LINK_NAME}.{uuid.uuid4().hex}.recovery"
    try:
        os.symlink(target, temporary)
        os.replace(temporary, base / CURRENT_LINK_NAME)
        _fsync_directory(base)
    finally:
        temporary.unlink(missing_ok=True)


def recover_transition_intent(base: Path) -> str | None:
    """Reconcile all valid crash windows without executing a candidate release."""

    intent = _load_transition_intent(base)
    if intent is None:
        return None
    current = _load_current_components(base, allow_incomplete=True)
    old_current = intent["old_current"]
    new_current = intent["new_current"]
    assert old_current is None or isinstance(old_current, Mapping)
    assert isinstance(new_current, Mapping)

    json_payload = None if current is None else current["payload"]
    link_target = None if current is None else current["link_target"]
    json_side = (
        "none"
        if json_payload is None
        else "old"
        if old_current is not None and json_payload == old_current
        else "new"
        if json_payload == new_current
        else None
    )
    link_side = (
        "none"
        if link_target is None
        else "old"
        if old_current is not None and link_target == old_current["release_dir"]
        else "new"
        if link_target == new_current["release_dir"]
        else None
    )
    if json_side is None or link_side is None:
        raise ReleaseBuildError(
            "RELEASE_TRANSITION_STATE_INVALID",
            "发布切换意图与 current 独立身份不一致",
        )

    old_release_id = (
        None if old_current is None else str(old_current["release_id"])
    )
    new_release_id = str(new_current["release_id"])
    old_side = "none" if old_current is None else "old"
    if json_side == old_side and link_side == old_side:
        if old_release_id is not None and _is_retired(base, old_release_id):
            raise ReleaseBuildError(
                "RELEASE_TRANSITION_STATE_INVALID",
                "未完成切换的旧发布已存在正式退役记录",
            )
        _remove_transition_intent(base)
        return "aborted"

    if (json_side, link_side) != ("new", "new"):
        if old_release_id is not None and _is_retired(base, old_release_id):
            raise ReleaseBuildError(
                "RELEASE_TRANSITION_STATE_INVALID",
                "分裂 current 的旧发布已退役，拒绝自动修复",
            )
        if json_side == old_side:
            _atomic_write_json(
                base / CURRENT_JSON_NAME,
                dict(new_current),
                mode=0o600,
            )
        if link_side == old_side:
            _replace_current_link(base, str(new_current["release_dir"]))

    verified = _load_current_pointer(base)
    if verified is None or verified["payload"] != new_current:
        raise ReleaseBuildError(
            "RELEASE_CURRENT_RECOVERY_FAILED", "发布切换分裂状态恢复后反向核验失败"
        )
    if old_current is not None and old_release_id is not None:
        _record_retired_release(
            base,
            {
                "release_id": old_release_id,
                "release_dir": str(old_current["release_dir"]),
            },
            superseded_by_release_id=new_release_id,
        )
    _remove_transition_intent(base)
    return "committed"


def switch_current(base: Path, record: Mapping[str, Any]) -> None:
    recover_transition_intent(base)
    _validate_current_payload(
        record,
        base=base,
        code="RELEASE_CURRENT_RECORD_INVALID",
        message="待切换发布记录无效",
    )
    release_id = record.get("release_id")
    release_dir_raw = record.get("release_dir")
    assert isinstance(release_id, str)
    assert isinstance(release_dir_raw, str)
    release_dir = Path(release_dir_raw)
    if (
        not release_dir.is_absolute()
        or release_dir != base / "releases" / release_id
        or not release_dir.is_dir()
        or release_dir.is_symlink()
    ):
        raise ReleaseBuildError(
            "RELEASE_CURRENT_RECORD_INVALID", "待切换发布路径未绑定内容寻址目标"
        )

    current_json = base / CURRENT_JSON_NAME
    current_link = base / CURRENT_LINK_NAME
    current_before = _load_current_pointer(base)

    json_bytes = (
        json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    same_target = bool(
        current_before
        and current_before["release_id"] == release_id
        and current_before["release_dir"] == str(release_dir)
    )
    if same_target and current_before and current_before["raw"] == json_bytes:
        return
    if not same_target and _is_retired(base, release_id):
        raise ReleaseBuildError(
            "RELEASE_ROLLBACK_BLOCKED", "目标发布已退役，禁止回滚重新激活"
        )

    json_temp = base / f".{CURRENT_JSON_NAME}.{uuid.uuid4().hex}.tmp"
    link_temp = base / f".{CURRENT_LINK_NAME}.{uuid.uuid4().hex}.tmp"
    json_replaced = False
    link_replaced = False
    switch_committed = False
    transition_written = False
    try:
        _atomic_write_bytes(json_temp, json_bytes, mode=0o600)
        os.symlink(str(release_dir), link_temp)
        _assert_current_unchanged(base, current_before)
        if not same_target:
            _write_transition_intent(
                base,
                current_before,
                new_current=record,
            )
            transition_written = True
            _assert_current_unchanged(base, current_before)
        os.replace(json_temp, current_json)
        json_replaced = True
        _fsync_directory(base)
        os.replace(link_temp, current_link)
        link_replaced = True
        _fsync_directory(base)
        switch_committed = True
        if transition_written:
            recover_transition_intent(base)
    except Exception:
        if switch_committed:
            # The new pointer pair is already durable and self-consistent.
            # Leave the intent for the next build to finish retirement rather
            # than rolling a committed selection back.
            raise
        if json_replaced:
            try:
                if link_replaced:
                    if current_before is None:
                        current_link.unlink(missing_ok=True)
                    else:
                        recovery_link = base / f".{CURRENT_LINK_NAME}.{uuid.uuid4().hex}.recovery"
                        try:
                            os.symlink(str(current_before["link_target"]), recovery_link)
                            os.replace(recovery_link, current_link)
                        finally:
                            recovery_link.unlink(missing_ok=True)
                    _fsync_directory(base)
                if current_before is None:
                    current_json.unlink(missing_ok=True)
                    _fsync_directory(base)
                else:
                    _atomic_write_bytes(
                        current_json,
                        bytes(current_before["raw"]),
                        mode=0o600,
                    )
                if transition_written:
                    outcome = recover_transition_intent(base)
                    if outcome != "aborted":
                        raise ReleaseBuildError(
                            "RELEASE_CURRENT_RECOVERY_FAILED",
                            "current 已恢复但发布切换意图未终止",
                        )
            except (OSError, ReleaseBuildError) as exc:
                raise ReleaseBuildError(
                    "RELEASE_CURRENT_RECOVERY_FAILED",
                    "current 切换失败且旧元数据恢复失败",
                ) from exc
        elif transition_written:
            try:
                outcome = recover_transition_intent(base)
                if outcome != "aborted":
                    raise ReleaseBuildError(
                        "RELEASE_CURRENT_RECOVERY_FAILED",
                        "发布切换意图未能按旧 current 终止",
                    )
            except (OSError, ReleaseBuildError) as exc:
                raise ReleaseBuildError(
                    "RELEASE_CURRENT_RECOVERY_FAILED",
                    "current 切换失败且意图记录补偿失败",
                ) from exc
        raise
    finally:
        json_temp.unlink(missing_ok=True)
        link_temp.unlink(missing_ok=True)


def build_local_release(
    *,
    source_root: Path,
    base: Path,
    source_venv: Path,
    source_env: Path | None,
    seed_state: bool = False,
    system_id: str = SYSTEM_ID_DEFAULT,
    backend_port: int = 8010,
    ui_port: int = 8501,
    runtime_digest_fn: Callable[[Path], str] = compute_runtime_digest,
    verify_fn: Callable[[Path, ExpectedIdentity], dict[str, Any]] = verify_release_manifest,
) -> dict[str, Any]:
    source_root = Path(os.path.abspath(os.fspath(source_root)))
    base = Path(os.path.abspath(os.fspath(base)))
    if not source_root.is_dir() or source_root.is_symlink():
        raise ReleaseBuildError(
            "RELEASE_SOURCE_ROOT_INVALID", "源代码根目录必须是普通目录"
        )
    try:
        base.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise ReleaseBuildError(
            "RELEASE_BASE_INSIDE_SOURCE", "发布基础目录不得位于源代码树内"
        )
    if backend_port == ui_port or not all(1 <= int(port) <= 65535 for port in (backend_port, ui_port)):
        raise ReleaseBuildError("RELEASE_PORT_INVALID", "后端与界面端口配置无效")

    base = _secure_directory(base)
    with _exclusive_build_lock(base):
        state_root = _secure_directory(base / "state")
        recover_transition_intent(base)
        state_dir = _secure_directory(state_root / "supervisor")
        log_dir = _secure_directory(state_dir / "logs")
        env_file = ensure_runtime_secret(base=base, source_env=source_env)
        runtime_digest, python_executable = build_runtime(
            source_venv=source_venv,
            runtimes_dir=base / "runtimes",
            digest_fn=runtime_digest_fn,
        )
        identity, release_dir = build_source_release(
            source_root=source_root,
            base=base,
            runtime_digest=runtime_digest,
            system_id=system_id,
            seed_state=seed_state,
            verify_fn=verify_fn,
        )
        verify_fn(release_dir, identity)
        if runtime_digest_fn(python_executable) != identity.runtime_digest:
            raise ReleaseBuildError(
                "RELEASE_RUNTIME_REVERSE_VERIFY_FAILED", "切换前运行时摘要反向校验失败"
            )
        # Copy only from the already reverse-verified, read-only release.  The
        # mutable checkout is no longer a trust source at this point.
        ensure_trusted_bootstrap(base=base, source_root=release_dir)

        record = {
            "schema_version": SCHEMA_VERSION,
            **identity.as_dict(),
            "release_dir": str(release_dir),
            "python_executable": str(python_executable),
            "env_file": str(env_file),
            "state_dir": str(state_dir),
            "log_dir": str(log_dir),
            "backend_port": int(backend_port),
            "ui_port": int(ui_port),
        }
        switch_current(base, record)
        return dict(record)


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="构建并选择不可变本地施组系统发布")
    parser.add_argument("--source-root", type=Path, default=root)
    parser.add_argument("--base", type=Path, default=default_release_base())
    parser.add_argument("--venv", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--seed-state", action="store_true")
    parser.add_argument("--system-id", default=SYSTEM_ID_DEFAULT)
    parser.add_argument("--backend-port", type=int, default=8010)
    parser.add_argument("--ui-port", type=int, default=8501)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_root = Path(os.path.abspath(os.fspath(args.source_root)))
    source_venv = args.venv or (source_root / ".venv")
    source_env = args.env_file or (source_root / ".env.local")
    try:
        result = build_local_release(
            source_root=source_root,
            base=args.base,
            source_venv=source_venv,
            source_env=source_env,
            seed_state=args.seed_state,
            system_id=args.system_id,
            backend_port=args.backend_port,
            ui_port=args.ui_port,
        )
    except (ReleaseBuildError, SupervisorError) as exc:
        code = getattr(exc, "code", "RELEASE_BUILD_FAILED")
        message = getattr(exc, "message", "不可变本地发布构建失败")
        print(
            json.dumps({"ok": False, "error_code": code, "message": message}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        return 130
    print(
        json.dumps(
            {
                "ok": True,
                "release_id": result["release_id"],
                "manifest_digest": result["manifest_digest"],
                "source_digest": result["source_digest"],
                "runtime_digest": result["runtime_digest"],
                "release_dir": result["release_dir"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
