from __future__ import annotations

import ast
import importlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

import image_generation.runtime.comfyui_operator_launcher as launcher_module
from image_generation.precheck.comfyui_precheck_validator import (
    validate_static_precheck,
)
from image_generation.runtime.local_comfyui_transport import LocalComfyUITransport


class _FailingOpener:
    def open(self, *_args, **_kwargs):
        raise OSError("offline")


class _FakeProcess:
    def __init__(self, *, pid: int = 4321) -> None:
        self.pid = pid
        self.return_code: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls: list[float | None] = []
        self.timeout_once = False

    def poll(self) -> int | None:
        return self.return_code

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self.timeout_once:
            self.timeout_once = False
            raise subprocess.TimeoutExpired(["comfyui"], timeout)
        self.return_code = 0
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
    fake_process = _FakeProcess()
    fake_process.timeout_once = True
    handle = launcher_module.ComfyUIProcess(fake_process)

    handle.stop(timeout_seconds=0.01)

    assert fake_process.terminate_calls == 1
    assert fake_process.kill_calls == 1
    assert fake_process.wait_calls == [0.01, 0.01]


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
