"""Explicit operator-only launcher for the fixed local ComfyUI service."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from typing import Protocol, Sequence
from urllib.parse import urlsplit

from image_generation.runtime.local_comfyui_transport import LocalComfyUITransport


CANONICAL_MODULE = "image_generation.runtime.comfyui_operator_launcher"
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8188
READINESS_TIMEOUT_SECONDS = 30.0
READINESS_POLL_INTERVAL_SECONDS = 0.25
STOP_TIMEOUT_SECONDS = 10.0


class ComfyUILauncherError(RuntimeError):
    """Structured failure raised before or while managing the launched process."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _ProcessPort(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ComfyUILaunchSpec:
    """Validated immutable argv contract for one local ComfyUI instance."""

    python_executable: Path
    comfyui_root: Path
    comfyui_main: Path
    argv: tuple[str, ...]

    def as_dict(self, *, would_start: bool) -> dict[str, object]:
        return {
            "status": "ok",
            "launcher": CANONICAL_MODULE,
            "python_executable": str(self.python_executable),
            "comfyui_main": str(self.comfyui_main),
            "listen": LISTEN_HOST,
            "port": LISTEN_PORT,
            "disable_auto_launch": True,
            "disable_api_nodes": True,
            "explicit_operator_only": True,
            "auto_start": False,
            "argv": list(self.argv),
            "shell": False,
            "would_start": would_start,
        }


@dataclass(slots=True)
class ComfyUIProcess:
    """Handle that can stop only the exact process created by this launcher."""

    _process: _ProcessPort

    @property
    def pid(self) -> int:
        return self._process.pid

    def poll(self) -> int | None:
        return self._process.poll()

    def wait(self) -> int:
        return self._process.wait()

    def stop(self, *, timeout_seconds: float = STOP_TIMEOUT_SECONDS) -> None:
        if self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=timeout_seconds)
            return
        except subprocess.TimeoutExpired:
            self._process.kill()
        try:
            self._process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise ComfyUILauncherError(
                "COMFYUI_PROCESS_STOP_TIMEOUT",
                "the launched ComfyUI process did not stop within the bounded timeout",
            ) from exc


def build_launch_spec(
    python_executable: str | Path,
    comfyui_root: str | Path,
    *,
    listen: str = LISTEN_HOST,
    port: int = LISTEN_PORT,
) -> ComfyUILaunchSpec:
    """Resolve paths and build the exact frozen argv without starting a process."""

    if listen != LISTEN_HOST or type(port) is not int or port != LISTEN_PORT:
        raise ComfyUILauncherError(
            "COMFYUI_NETWORK_BOUNDARY_INVALID",
            f"listen and port must be exactly {LISTEN_HOST}:{LISTEN_PORT}",
        )

    python_path = _resolve_python_executable(python_executable)
    root_path = _resolve_comfyui_root(comfyui_root)
    main_path = _resolve_comfyui_main(root_path)
    argv = (
        str(python_path),
        str(main_path),
        "--listen",
        LISTEN_HOST,
        "--port",
        str(LISTEN_PORT),
        "--disable-auto-launch",
        "--disable-api-nodes",
    )
    _validate_argv_contract(argv, python_path=python_path, main_path=main_path)
    return ComfyUILaunchSpec(
        python_executable=python_path,
        comfyui_root=root_path,
        comfyui_main=main_path,
        argv=argv,
    )


def launch_comfyui(
    python_executable: str | Path,
    comfyui_root: str | Path,
    *,
    explicit_operator_request: bool = False,
) -> ComfyUIProcess:
    """Start ComfyUI only after an explicit operator request and readiness check."""

    if explicit_operator_request is not True:
        raise ComfyUILauncherError(
            "EXPLICIT_OPERATOR_LAUNCH_REQUIRED",
            "an explicit operator start request is required",
        )

    spec = build_launch_spec(python_executable, comfyui_root)
    if not _port_is_available():
        raise ComfyUILauncherError(
            "COMFYUI_PORT_ALREADY_IN_USE",
            f"{LISTEN_HOST}:{LISTEN_PORT} is already in use",
        )

    try:
        process = subprocess.Popen(
            list(spec.argv),
            cwd=str(spec.comfyui_root),
            shell=False,
        )
    except OSError as exc:
        raise ComfyUILauncherError(
            "COMFYUI_PROCESS_START_FAILED",
            "the explicit ComfyUI process could not be started",
        ) from exc

    handle = ComfyUIProcess(process)
    try:
        _wait_for_readiness(handle)
    except BaseException:
        handle.stop()
        raise
    return handle


def _resolve_python_executable(value: str | Path) -> Path:
    path = _validated_absolute_path(value, field_name="python executable")
    try:
        resolved_target = path.resolve(strict=True)
    except OSError as exc:
        raise ComfyUILauncherError(
            "PYTHON_EXECUTABLE_NOT_FOUND",
            "the provided Python executable does not exist",
        ) from exc
    if (
        not resolved_target.is_file()
        or not path.is_file()
        or not os.access(path, os.X_OK)
    ):
        raise ComfyUILauncherError(
            "PYTHON_EXECUTABLE_INVALID",
            "the provided Python executable must resolve to an executable regular file",
        )
    return path


def _resolve_comfyui_root(value: str | Path) -> Path:
    path = _validated_absolute_path(value, field_name="ComfyUI root")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ComfyUILauncherError(
            "COMFYUI_ROOT_NOT_FOUND",
            "the provided ComfyUI root does not exist",
        ) from exc
    if not resolved.is_dir():
        raise ComfyUILauncherError(
            "COMFYUI_ROOT_INVALID",
            "the provided ComfyUI root must resolve to a directory",
        )
    return resolved


def _resolve_comfyui_main(root_path: Path) -> Path:
    candidate = root_path / "main.py"
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ComfyUILauncherError(
            "COMFYUI_MAIN_NOT_FOUND",
            "ComfyUI main.py does not exist under the provided root",
        ) from exc
    if not resolved.is_file() or resolved.parent != root_path:
        raise ComfyUILauncherError(
            "COMFYUI_MAIN_INVALID",
            "ComfyUI main.py must resolve to a regular file directly under the root",
        )
    return resolved


def _validated_absolute_path(value: str | Path, *, field_name: str) -> Path:
    raw_value = str(value)
    if not raw_value or not raw_value.strip():
        raise ComfyUILauncherError(
            "COMFYUI_PATH_INVALID",
            f"{field_name} must not be empty",
        )
    if raw_value != raw_value.strip() or any(
        ord(character) < 32 or ord(character) == 127 for character in raw_value
    ):
        raise ComfyUILauncherError(
            "COMFYUI_PATH_INVALID",
            f"{field_name} contains forbidden whitespace or control characters",
        )
    if urlsplit(raw_value).scheme:
        raise ComfyUILauncherError(
            "COMFYUI_PATH_INVALID",
            f"{field_name} must be a filesystem path, not a URL",
        )
    path = Path(raw_value)
    if not path.is_absolute():
        raise ComfyUILauncherError(
            "COMFYUI_PATH_INVALID",
            f"{field_name} must be an absolute path",
        )
    return path


def _validate_argv_contract(
    argv: tuple[str, ...],
    *,
    python_path: Path,
    main_path: Path,
) -> None:
    expected = (
        str(python_path),
        str(main_path),
        "--listen",
        LISTEN_HOST,
        "--port",
        str(LISTEN_PORT),
        "--disable-auto-launch",
        "--disable-api-nodes",
    )
    if argv != expected or any(type(item) is not str or not item for item in argv):
        raise ComfyUILauncherError(
            "COMFYUI_ARGV_CONTRACT_FAILED",
            "ComfyUI argv does not match the frozen production contract",
        )
    if (
        argv.count("--listen") != 1
        or argv.count(LISTEN_HOST) != 1
        or argv.count("--port") != 1
        or argv.count(str(LISTEN_PORT)) != 1
        or argv.count("--disable-auto-launch") != 1
        or argv.count("--disable-api-nodes") != 1
    ):
        raise ComfyUILauncherError(
            "COMFYUI_ARGV_CONTRACT_FAILED",
            "ComfyUI frozen argv values must each occur exactly once",
        )


def _port_is_available() -> bool:
    port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port_socket.bind((LISTEN_HOST, LISTEN_PORT))
    except OSError:
        return False
    finally:
        port_socket.close()
    return True


def _readiness_probe() -> bool:
    return LocalComfyUITransport().check()


def _wait_for_readiness(
    handle: ComfyUIProcess,
    *,
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        if handle.poll() is not None:
            raise ComfyUILauncherError(
                "COMFYUI_PROCESS_EXITED_BEFORE_READY",
                "the explicit ComfyUI process exited before localhost readiness",
            )
        if _readiness_probe():
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ComfyUILauncherError(
                "COMFYUI_READINESS_TIMEOUT",
                "localhost ComfyUI readiness did not pass within the bounded timeout",
            )
        time.sleep(min(READINESS_POLL_INTERVAL_SECONDS, remaining))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"python -m {CANONICAL_MODULE}",
        description="Explicit operator-only launcher for localhost ComfyUI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("dry-run", "resolve paths and print the frozen argv without side effects"),
        ("start", "explicitly start and supervise the localhost ComfyUI process"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--python-executable", required=True)
        command_parser.add_argument("--comfyui-root", required=True)
    return parser


def _emit_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _raise_operator_interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handle: ComfyUIProcess | None = None
    previous_sigterm = None
    try:
        if args.command == "dry-run":
            spec = build_launch_spec(args.python_executable, args.comfyui_root)
            _emit_json(spec.as_dict(would_start=False))
            return 0

        previous_sigterm = signal.signal(signal.SIGTERM, _raise_operator_interrupt)
        handle = launch_comfyui(
            args.python_executable,
            args.comfyui_root,
            explicit_operator_request=True,
        )
        started = build_launch_spec(args.python_executable, args.comfyui_root).as_dict(
            would_start=True
        )
        started.update({"status": "ready", "pid": handle.pid})
        _emit_json(started)
        return_code = handle.wait()
        _emit_json(
            {
                "status": "stopped",
                "launcher": CANONICAL_MODULE,
                "pid": handle.pid,
                "return_code": return_code,
            }
        )
        return return_code if return_code >= 0 else 1
    except ComfyUILauncherError as exc:
        _emit_json(
            {
                "status": "error",
                "launcher": CANONICAL_MODULE,
                "error_code": exc.code,
                "message": str(exc),
                "would_start": False,
            }
        )
        return 2
    except KeyboardInterrupt:
        if handle is not None:
            handle.stop()
        _emit_json(
            {
                "status": "stopped",
                "launcher": CANONICAL_MODULE,
                "reason": "operator_interrupt",
            }
        )
        return 130
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "build_launch_spec",
    "ComfyUILauncherError",
    "ComfyUIProcess",
    "launch_comfyui",
    "main",
]
