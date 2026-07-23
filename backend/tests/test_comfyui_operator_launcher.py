from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

import image_generation.runtime.comfyui_operator_launcher as launcher_module
from image_generation.precheck.comfyui_precheck_validator import (
    validate_static_precheck,
)
from image_generation.runtime.local_comfyui_transport import LocalComfyUITransport


class _FailingOpener:
    def open(self, *_args, **_kwargs):
        raise OSError("offline")


def _raise_keyboard_interrupt(_handle) -> None:
    raise KeyboardInterrupt


def _source_line_number(function, statement: str) -> int:
    source_lines, first_line = inspect.getsourcelines(function)
    offset = next(
        index
        for index, source_line in enumerate(source_lines)
        if statement in source_line
    )
    return first_line + offset


class _FakeProcess:
    def __init__(
        self,
        *,
        pid: int = 4321,
        wait_effects: list[BaseException | int] | None = None,
    ) -> None:
        self.pid = pid
        self.return_code: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls: list[float | None] = []
        self.wait_effects = list(wait_effects or [])

    def poll(self) -> int | None:
        return self.return_code

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        effect: BaseException | int = (
            self.wait_effects.pop(0) if self.wait_effects else 0
        )
        if isinstance(effect, BaseException):
            raise effect
        self.return_code = effect
        return self.return_code

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1


@pytest.fixture
def launch_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    python_executable = tmp_path / "python"
    python_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    python_executable.chmod(0o755)
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()
    comfyui_main = comfyui_root / "main.py"
    comfyui_main.write_text("# fixture\n", encoding="utf-8")
    return python_executable, comfyui_root, comfyui_main


def test_frozen_argv_is_exact_and_contains_each_required_value_once(
    launch_paths,
) -> None:
    python_executable, comfyui_root, comfyui_main = launch_paths

    spec = launcher_module.build_launch_spec(python_executable, comfyui_root)

    assert list(spec.argv) == [
        str(python_executable),
        str(comfyui_main),
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
        "--disable-auto-launch",
        "--disable-api-nodes",
    ]
    for frozen_value in (
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
        "--disable-auto-launch",
        "--disable-api-nodes",
    ):
        assert spec.argv.count(frozen_value) == 1


@pytest.mark.parametrize("listen", ["0.0.0.0", "::", "192.168.1.10", "8.8.8.8"])
def test_non_loopback_listen_values_are_rejected(launch_paths, listen: str) -> None:
    python_executable, comfyui_root, _ = launch_paths

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.build_launch_spec(
            python_executable,
            comfyui_root,
            listen=listen,
        )

    assert caught.value.code == "COMFYUI_NETWORK_BOUNDARY_INVALID"


def test_port_override_is_rejected(launch_paths) -> None:
    python_executable, comfyui_root, _ = launch_paths

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.build_launch_spec(python_executable, comfyui_root, port=8189)

    assert caught.value.code == "COMFYUI_NETWORK_BOUNDARY_INVALID"


@pytest.mark.parametrize(
    "invalid_value",
    ["", "relative/path", "https://example.com/ComfyUI", "/tmp/ComfyUI\n--listen"],
)
def test_empty_relative_url_and_control_character_paths_are_rejected(
    launch_paths,
    invalid_value: str,
) -> None:
    python_executable, _, _ = launch_paths

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.build_launch_spec(python_executable, invalid_value)

    assert caught.value.code == "COMFYUI_PATH_INVALID"


def test_missing_main_is_structured_failure(tmp_path: Path) -> None:
    python_executable = tmp_path / "python"
    python_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    python_executable.chmod(0o755)
    comfyui_root = tmp_path / "ComfyUI"
    comfyui_root.mkdir()

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.build_launch_spec(python_executable, comfyui_root)

    assert caught.value.code == "COMFYUI_MAIN_NOT_FOUND"


def test_implicit_launch_is_rejected_before_path_or_process_work(monkeypatch) -> None:
    popen_calls: list[object] = []
    monkeypatch.setattr(
        launcher_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.launch_comfyui("missing", "missing")

    assert caught.value.code == "EXPLICIT_OPERATOR_LAUNCH_REQUIRED"
    assert popen_calls == []


def test_explicit_start_calls_popen_once_with_list_and_shell_false(
    launch_paths,
    monkeypatch,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess()
    popen_calls: list[tuple[tuple, dict]] = []

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        return fake_process

    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(launcher_module, "_wait_for_readiness", lambda _handle: None)
    monkeypatch.setattr(launcher_module.subprocess, "Popen", fake_popen)

    handle = launcher_module.launch_comfyui(
        python_executable,
        comfyui_root,
        explicit_operator_request=True,
    )

    assert handle.pid == fake_process.pid
    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    assert isinstance(args[0], list)
    assert kwargs == {"cwd": str(comfyui_root), "shell": False}


def test_cli_start_is_the_explicit_command_that_calls_popen_once(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess()
    popen_calls: list[tuple[tuple, dict]] = []

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        return fake_process

    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(launcher_module, "_wait_for_readiness", lambda _handle: None)
    monkeypatch.setattr(launcher_module.subprocess, "Popen", fake_popen)

    exit_code = launcher_module.main(
        [
            "start",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    output_lines = capsys.readouterr().out.splitlines()

    assert exit_code == 0
    assert len(popen_calls) == 1
    assert json.loads(output_lines[0])["status"] == "ready"
    assert json.loads(output_lines[1])["status"] == "stopped"


def test_occupied_port_never_starts_or_terminates_a_process(
    launch_paths,
    monkeypatch,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    popen_calls: list[object] = []
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: False)
    monkeypatch.setattr(
        launcher_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.launch_comfyui(
            python_executable,
            comfyui_root,
            explicit_operator_request=True,
        )

    assert caught.value.code == "COMFYUI_PORT_ALREADY_IN_USE"
    assert popen_calls == []


def test_readiness_failure_stops_only_the_new_process(
    launch_paths, monkeypatch
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess()
    readiness_error = launcher_module.ComfyUILauncherError(
        "COMFYUI_READINESS_TIMEOUT",
        "timeout",
    )
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )

    def fail_readiness(_handle):
        raise readiness_error

    monkeypatch.setattr(launcher_module, "_wait_for_readiness", fail_readiness)

    with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
        launcher_module.launch_comfyui(
            python_executable,
            comfyui_root,
            explicit_operator_request=True,
        )

    assert caught.value is readiness_error
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 0


def test_stop_escalates_from_terminate_to_kill_on_the_same_handle() -> None:
    fake_process = _FakeProcess(
        wait_effects=[subprocess.TimeoutExpired(["comfyui"], 0.01)]
    )
    handle = launcher_module.ComfyUIProcess(fake_process)

    handle.stop(timeout_seconds=0.01)

    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1
    assert len(fake_process.wait_calls) == 2
    assert all(
        wait_timeout is not None and 0 < wait_timeout <= 0.01
        for wait_timeout in fake_process.wait_calls
    )


def test_main_terminate_return_boundary_dispatch_is_interrupt_atomic(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess(wait_effects=[0])
    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    dispatch_commit_line = _source_line_number(
        launcher_module._dispatch_stop_action,
        "dispatch.state = _StopDispatchState.DISPATCHED",
    )
    injected = False

    def inject_after_terminate_return(frame, event, _arg):
        nonlocal injected
        if (
            not injected
            and event == "line"
            and frame.f_code is launcher_module._dispatch_stop_action.__code__
            and frame.f_lineno == dispatch_commit_line
            and frame.f_locals["phase"] == "terminate"
        ):
            injected = True
            os.kill(os.getpid(), signal.SIGTERM)
        return inject_after_terminate_return

    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )
    monkeypatch.setattr(
        launcher_module,
        "_wait_for_readiness",
        _raise_keyboard_interrupt,
    )

    sys.settrace(inject_after_terminate_return)
    try:
        exit_code = launcher_module.main(
            [
                "start",
                "--python-executable",
                str(python_executable),
                "--comfyui-root",
                str(comfyui_root),
            ]
        )
    finally:
        sys.settrace(None)
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert injected is True
    assert exit_code == 130
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 0
    assert fake_process.poll() == 0
    assert [payload["status"] for payload in payloads] == ["stopped"]
    assert signal.getsignal(signal.SIGINT) is previous_sigint
    assert signal.getsignal(signal.SIGTERM) is previous_sigterm
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == previous_mask


def test_stop_kill_return_boundary_dispatch_is_interrupt_atomic() -> None:
    fake_process = _FakeProcess(
        wait_effects=[subprocess.TimeoutExpired(["comfyui"], 0.01), 0]
    )
    previous_sigint = signal.signal(
        signal.SIGINT, launcher_module._raise_operator_interrupt
    )
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    dispatch_commit_line = _source_line_number(
        launcher_module._dispatch_stop_action,
        "dispatch.state = _StopDispatchState.DISPATCHED",
    )
    injected = False

    def inject_after_kill_return(frame, event, _arg):
        nonlocal injected
        if (
            not injected
            and event == "line"
            and frame.f_code is launcher_module._dispatch_stop_action.__code__
            and frame.f_lineno == dispatch_commit_line
            and frame.f_locals["phase"] == "kill"
        ):
            injected = True
            os.kill(os.getpid(), signal.SIGINT)
        return inject_after_kill_return

    sys.settrace(inject_after_kill_return)
    try:
        launcher_module.ComfyUIProcess(fake_process).stop(timeout_seconds=0.01)
    finally:
        sys.settrace(None)
        signal.signal(signal.SIGINT, previous_sigint)

    assert injected is True
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1
    assert fake_process.poll() == 0
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == previous_mask


def test_stop_pre_call_interrupt_does_not_lose_terminate() -> None:
    fake_process = _FakeProcess(wait_effects=[0])
    previous_sigint = signal.signal(
        signal.SIGINT, launcher_module._raise_operator_interrupt
    )
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    dispatch_start_line = _source_line_number(
        launcher_module._dispatch_stop_action,
        "dispatch.state = _StopDispatchState.DISPATCHING",
    )
    injected = False

    def inject_before_terminate_call(frame, event, _arg):
        nonlocal injected
        if (
            not injected
            and event == "line"
            and frame.f_code is launcher_module._dispatch_stop_action.__code__
            and frame.f_lineno == dispatch_start_line
            and frame.f_locals["phase"] == "terminate"
        ):
            injected = True
            os.kill(os.getpid(), signal.SIGINT)
        return inject_before_terminate_call

    sys.settrace(inject_before_terminate_call)
    try:
        launcher_module.ComfyUIProcess(fake_process).stop(timeout_seconds=0.01)
    finally:
        sys.settrace(None)
        signal.signal(signal.SIGINT, previous_sigint)

    assert injected is True
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 0
    assert fake_process.poll() == 0
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == previous_mask


@pytest.mark.parametrize("ambiguous_phase", ["terminate", "kill"])
def test_stop_does_not_repeat_ambiguous_action_failure(
    ambiguous_phase: str,
    monkeypatch,
) -> None:
    fake_process = _FakeProcess(
        wait_effects=[
            subprocess.TimeoutExpired(["comfyui"], 0.01),
            0
            if ambiguous_phase == "terminate"
            else subprocess.TimeoutExpired(["comfyui"], 0.01),
        ]
    )

    def fail_ambiguously() -> None:
        if ambiguous_phase == "terminate":
            fake_process.terminate_calls += 1
        else:
            fake_process.kill_calls += 1
        raise OSError("dispatch result is ambiguous")

    monkeypatch.setattr(fake_process, ambiguous_phase, fail_ambiguously)
    handle = launcher_module.ComfyUIProcess(fake_process)

    if ambiguous_phase == "terminate":
        handle.stop(timeout_seconds=0.01)
        assert fake_process.poll() == 0
    else:
        with pytest.raises(launcher_module.ComfyUILauncherError) as caught:
            handle.stop(timeout_seconds=0.01)
        assert caught.value.code == "COMFYUI_PROCESS_STOP_TIMEOUT"
        assert fake_process.poll() is None

    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1


def test_main_readiness_interrupt_survives_secondary_cleanup_interrupt(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess(wait_effects=[KeyboardInterrupt(), 0])
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )
    monkeypatch.setattr(
        launcher_module,
        "_wait_for_readiness",
        _raise_keyboard_interrupt,
    )

    exit_code = launcher_module.main(
        [
            "start",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert exit_code == 130
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 0
    assert fake_process.poll() == 0
    assert [payload["status"] for payload in payloads] == ["stopped"]


def test_main_supervision_interrupt_reports_structured_kill_timeout(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess(
        wait_effects=[
            KeyboardInterrupt(),
            subprocess.TimeoutExpired(["comfyui"], 10.0),
            subprocess.TimeoutExpired(["comfyui"], 10.0),
        ]
    )
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(launcher_module, "_wait_for_readiness", lambda _handle: None)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )

    exit_code = launcher_module.main(
        [
            "start",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert exit_code == 2
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1
    assert [payload["status"] for payload in payloads] == ["ready", "error"]
    assert payloads[-1]["error_code"] == "COMFYUI_PROCESS_STOP_TIMEOUT"


def test_main_readiness_interrupt_reports_cleanup_timeout_and_restores_signals(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess(
        wait_effects=[
            subprocess.TimeoutExpired(["comfyui"], 10.0),
            subprocess.TimeoutExpired(["comfyui"], 10.0),
        ]
    )
    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )
    monkeypatch.setattr(
        launcher_module,
        "_wait_for_readiness",
        _raise_keyboard_interrupt,
    )

    exit_code = launcher_module.main(
        [
            "start",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert exit_code == 2
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1
    assert [payload["status"] for payload in payloads] == ["error"]
    assert payloads[0]["error_code"] == "COMFYUI_PROCESS_STOP_TIMEOUT"
    assert signal.getsignal(signal.SIGINT) is previous_sigint
    assert signal.getsignal(signal.SIGTERM) is previous_sigterm


def test_main_supervision_interrupt_stops_confirmed_process(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, _ = launch_paths
    fake_process = _FakeProcess(wait_effects=[KeyboardInterrupt(), 0])
    monkeypatch.setattr(launcher_module, "_port_is_available", lambda: True)
    monkeypatch.setattr(launcher_module, "_wait_for_readiness", lambda _handle: None)
    monkeypatch.setattr(
        launcher_module.subprocess, "Popen", lambda *_args, **_kwargs: fake_process
    )

    exit_code = launcher_module.main(
        [
            "start",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    assert exit_code == 130
    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 0
    assert fake_process.poll() == 0
    assert [payload["status"] for payload in payloads] == ["ready", "stopped"]


def test_stop_does_nothing_for_an_already_exited_process() -> None:
    fake_process = _FakeProcess()
    fake_process.return_code = 0

    launcher_module.ComfyUIProcess(fake_process).stop()

    assert fake_process.terminate_calls == 0
    assert fake_process.kill_calls == 0


def test_dry_run_outputs_machine_readable_contract_without_runtime_side_effects(
    launch_paths,
    monkeypatch,
    capsys,
) -> None:
    python_executable, comfyui_root, comfyui_main = launch_paths

    def unexpected_side_effect(*_args, **_kwargs):
        raise AssertionError("dry-run attempted a process or network side effect")

    monkeypatch.setattr(launcher_module.subprocess, "Popen", unexpected_side_effect)
    monkeypatch.setattr(launcher_module.socket, "socket", unexpected_side_effect)
    monkeypatch.setattr(launcher_module.signal, "signal", unexpected_side_effect)
    monkeypatch.setattr(
        launcher_module.signal, "pthread_sigmask", unexpected_side_effect
    )
    monkeypatch.setattr(LocalComfyUITransport, "check", unexpected_side_effect)

    exit_code = launcher_module.main(
        [
            "dry-run",
            "--python-executable",
            str(python_executable),
            "--comfyui-root",
            str(comfyui_root),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "argv": [
            str(python_executable),
            str(comfyui_main),
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
            "--disable-auto-launch",
            "--disable-api-nodes",
        ],
        "auto_start": False,
        "comfyui_main": str(comfyui_main),
        "disable_api_nodes": True,
        "disable_auto_launch": True,
        "explicit_operator_only": True,
        "launcher": launcher_module.CANONICAL_MODULE,
        "listen": "127.0.0.1",
        "port": 8188,
        "python_executable": str(python_executable),
        "shell": False,
        "status": "ok",
        "would_start": False,
    }


def test_module_import_calls_popen_zero_times(monkeypatch) -> None:
    popen_calls: list[object] = []
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    importlib.reload(launcher_module)

    assert popen_calls == []


def test_transport_health_failure_and_construction_never_start_comfyui(
    monkeypatch,
) -> None:
    popen_calls: list[object] = []
    monkeypatch.setattr(
        launcher_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    transport = LocalComfyUITransport(opener=_FailingOpener())

    assert transport.check() is False
    assert popen_calls == []


def test_static_precheck_never_starts_comfyui(monkeypatch) -> None:
    popen_calls: list[object] = []
    monkeypatch.setattr(
        launcher_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    report = validate_static_precheck(Path(__file__).resolve().parents[2])

    assert report is not None
    assert popen_calls == []


def test_web_ui_script_has_no_comfyui_launcher_or_port_reference() -> None:
    script = (Path(__file__).resolve().parents[2] / "scripts/run_web_ui.sh").read_text(
        encoding="utf-8"
    )

    assert "comfyui" not in script.lower()
    assert "8188" not in script
    assert launcher_module.CANONICAL_MODULE not in script


def test_no_extra_args_or_shell_command_override_surface() -> None:
    assert (
        "extra_args"
        not in inspect.signature(launcher_module.build_launch_spec).parameters
    )
    assert (
        "extra_args" not in inspect.signature(launcher_module.launch_comfyui).parameters
    )

    source = inspect.getsource(launcher_module)
    tree = ast.parse(source)
    forbidden_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    direct_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "system" not in forbidden_calls
    assert {"eval", "exec"}.isdisjoint(direct_calls)
    assert "shell=True" not in source.replace(" ", "")
    assert "--enable-cors-header" not in source
