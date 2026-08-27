from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Iterator

import pytest

from scripts import build_local_release as builder
from scripts import launch_latest_release as launcher
from scripts import launch_latest_release_bootstrap as bootstrap
from scripts.runtime_supervisor import SupervisorError


def _write(path: Path, content: str, *, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def _isolated_bootstrap_command(base: Path, *arguments: str) -> list[str]:
    """Run a temp sealed fixture while replacing only the OS account lookup."""

    harness = (
        "import pwd,runpy,sys,types;"
        "home=sys.argv.pop(1);script=sys.argv.pop(1);"
        "pwd.getpwuid=lambda _uid:types.SimpleNamespace(pw_dir=home);"
        "runpy.run_path(script,run_name='__main__')"
    )
    return [
        "/usr/bin/python3",
        "-I",
        "-B",
        "-c",
        harness,
        str(base.parents[2]),
        str(base / "bootstrap" / "launch_current.py"),
        *arguments,
    ]


def _restore_tree_writable(path: Path) -> None:
    if not path.exists() or path.is_symlink():
        return
    for current, directories, files in os.walk(path, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            item = current_path / name
            if not item.is_symlink():
                item.chmod(stat.S_IMODE(item.stat().st_mode) | 0o600)
        for name in directories:
            item = current_path / name
            if not item.is_symlink():
                item.chmod(stat.S_IMODE(item.stat().st_mode) | 0o700)
        current_path.chmod(stat.S_IMODE(current_path.stat().st_mode) | 0o700)


@pytest.fixture
def sealed_release(tmp_path: Path) -> Iterator[tuple[dict, Path]]:
    source = tmp_path / "source"
    project_root = Path(__file__).resolve().parents[2]
    _write(source / "app.py", "print('ui')\n")
    _write(source / "backend" / "app" / "main.py", "APP = 'backend'\n")
    _write(
        source / "scripts" / "runtime_supervisor.py",
        "# immutable supervisor fixture used through an injected runner\n",
    )
    _write(
        source / "scripts" / "launch_latest_release.py",
        "# immutable launcher fixture executed only by the fake runtime\n",
    )
    _write(
        source / "scripts" / "launch_latest_release_bootstrap.py",
        (project_root / "scripts" / "launch_latest_release_bootstrap.py").read_text(
            encoding="utf-8"
        ),
    )
    env_file = source / ".env.local"
    _write(env_file, "ZF_ACTIONS_KEY=fake-local-test-value\n", mode=0o600)
    venv = source / ".venv"
    external_python = tmp_path / "fixture-python"
    isolation_marker = tmp_path / "candidate-environment-not-isolated"
    _write(
        external_python,
        "#!/bin/sh\n"
        f"if [ -n \"${{PYTHONPATH:-}}\" ]; then printf unsafe > '{isolation_marker}'; fi\n"
        f"if [ \"$1\" != \"-I\" ] || [ \"$2\" != \"-B\" ]; then printf unsafe > '{isolation_marker}'; fi\n"
        "shift 2\n"
        "if [ \"$1\" = \"-VV\" ]; then echo 'Fixture Python 3.12'; exit 0; fi\n"
        "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"pip\" ]; then "
        "echo 'fixture-package==1.0'; exit 0; fi\n"
        "case \"$1\" in\n"
        "  */scripts/launch_latest_release.py)\n"
        "    printf 'BOOTSTRAP_EXEC=%s\\n' \"$1\"\n"
        "    shift\n"
        "    printf '%s\\n' \"$@\"\n"
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
        "exit 2\n",
        mode=0o755,
    )
    (venv / "bin").mkdir(parents=True, exist_ok=True)
    os.symlink(str(external_python), venv / "bin" / "python")
    _write(venv / "pyvenv.cfg", "home = /fixture\n")
    _write(
        venv / "lib" / "python" / "site-packages" / "fixture.py",
        "VALUE = 'sealed'\n",
    )
    base = (
        tmp_path
        / "home"
        / "Library"
        / "Application Support"
        / "com.zhifei.construction-expert"
    )
    record = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=venv,
        source_env=env_file,
    )
    try:
        yield record, base
    finally:
        _restore_tree_writable(base)


def _running_state(record: dict, *, status: str = "healthy", release_id: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "status": status,
        "running": True,
        "release_id": release_id or record["release_id"],
        "manifest_digest": record["manifest_digest"],
        "source_digest": record["source_digest"],
        "runtime_digest": record["runtime_digest"],
        "release_root": record["release_dir"],
        "supervisor_instance_id": "fixture-instance",
        "supervisor_pid": 101,
        "backend_pid": 102,
        "ui_pid": 103,
    }


def test_not_running_starts_once_verifies_health_then_opens(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    commands: list[list[str]] = []
    status_calls = 0

    def runner(argv, cwd, timeout):
        nonlocal status_calls
        command = list(argv)
        commands.append(command)
        assert cwd == Path(record["release_dir"])
        assert timeout > 0
        if command[2] == "start":
            return launcher.CommandResult(
                0,
                json.dumps({"status": "starting", "release_id": record["release_id"]}),
                "",
            )
        status_calls += 1
        if status_calls == 1:
            return launcher.CommandResult(3, '{"status":"not_running","running":false}', "")
        return launcher.CommandResult(0, json.dumps(_running_state(record)), "")

    def http_get(url: str, timeout: float):
        assert timeout == 3.0
        if url.endswith("/health"):
            return 200, json.dumps(
                {
                    "ok": True,
                    "system_id": record["system_id"],
                    "release_id": record["release_id"],
                    "manifest_digest": record["manifest_digest"],
                    "source_digest": record["source_digest"],
                    "runtime_digest": record["runtime_digest"],
                    "release_root": record["release_dir"],
                    "release_managed": True,
                    "runtime_mode": "sealed_release",
                }
            ).encode()
        return 200, b"ui"

    opened: list[str] = []
    result = launcher.launch_latest(
        base=base,
        runner=runner,
        http_get=http_get,
        browser_opener=opened.append,
        sleep=lambda _seconds: None,
    )

    assert result["status"] == "healthy"
    assert result["start_calls"] == 1
    assert [command[2] for command in commands].count("start") == 1
    assert "stop" not in [command[2] for command in commands]
    start = next(command for command in commands if command[2] == "start")
    assert start == launcher.build_start_argv(
        launcher.parse_release_spec(
            launcher.load_current_snapshot(base / "current.json"), base
        )
    )
    assert opened == ["http://127.0.0.1:8501"]
    assert "fake-local-test-value" not in json.dumps(commands)


def test_running_different_release_fails_closed_without_stop_start_or_open(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    commands: list[list[str]] = []

    def runner(argv, cwd, timeout):
        commands.append(list(argv))
        return launcher.CommandResult(
            0,
            json.dumps(_running_state(record, release_id="release-deadbeefdeadbeefdeadbeef")),
            "",
        )

    opened: list[str] = []
    with pytest.raises(launcher.LaunchError) as caught:
        launcher.launch_latest(
            base=base,
            runner=runner,
            browser_opener=opened.append,
        )

    assert caught.value.code == "LAUNCH_RUNNING_RELEASE_MISMATCH"
    assert [command[2] for command in commands] == ["status"]
    assert opened == []


def test_current_json_and_current_symlink_must_cross_match_before_status(
    sealed_release: tuple[dict, Path],
) -> None:
    _record, base = sealed_release
    current = base / "current"
    current.unlink()
    os.symlink(str(base / "releases" / "release-not-selected"), current)
    calls: list[list[str]] = []

    with pytest.raises(launcher.LaunchError) as caught:
        launcher.launch_latest(
            base=base,
            runner=lambda argv, cwd, timeout: calls.append(list(argv)),  # type: ignore[arg-type,return-value]
        )

    assert caught.value.code == "LAUNCH_CURRENT_POINTER_MISMATCH"
    assert calls == []


def test_current_pointer_change_before_start_blocks_without_start(
    sealed_release: tuple[dict, Path],
) -> None:
    _record, base = sealed_release
    commands: list[list[str]] = []

    def runner(argv, cwd, timeout):
        commands.append(list(argv))
        current = base / "current"
        current.unlink()
        os.symlink(str(base / "releases" / "release-not-selected"), current)
        return launcher.CommandResult(3, '{"status":"not_running","running":false}', "")

    with pytest.raises(launcher.LaunchError) as caught:
        launcher.launch_latest(base=base, runner=runner)

    assert caught.value.code == "LAUNCH_CURRENT_CHANGED"
    assert [command[2] for command in commands] == ["status"]


def test_release_tamper_is_blocked_before_any_status_or_browser(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    app = Path(record["release_dir"]) / "app.py"
    app.chmod(0o644)
    app.write_text("tampered\n", encoding="utf-8")
    app.chmod(0o444)
    calls: list[list[str]] = []
    opened: list[str] = []

    with pytest.raises(SupervisorError):
        launcher.launch_latest(
            base=base,
            runner=lambda argv, cwd, timeout: calls.append(list(argv)),  # type: ignore[arg-type,return-value]
            browser_opener=opened.append,
        )

    assert calls == []
    assert opened == []


def test_backend_five_identity_gate_blocks_browser(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release

    def runner(argv, cwd, timeout):
        return launcher.CommandResult(0, json.dumps(_running_state(record)), "")

    def http_get(url: str, timeout: float):
        if url.endswith("/health"):
            return 200, json.dumps(
                {
                    "ok": True,
                    "system_id": record["system_id"],
                    "release_id": record["release_id"],
                    "manifest_digest": "0" * 64,
                    "source_digest": record["source_digest"],
                    "runtime_digest": record["runtime_digest"],
                    "release_root": record["release_dir"],
                    "release_managed": True,
                    "runtime_mode": "sealed_release",
                }
            ).encode()
        return 200, b"ui"

    opened: list[str] = []
    with pytest.raises(launcher.LaunchError) as caught:
        launcher.launch_latest(
            base=base,
            runner=runner,
            http_get=http_get,
            browser_opener=opened.append,
        )

    assert caught.value.code == "LAUNCH_BACKEND_IDENTITY_MISMATCH"
    assert opened == []


def test_circuit_open_never_starts_or_opens(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    commands: list[list[str]] = []
    state = _running_state(record)
    state["circuit_open"] = True

    def runner(argv, cwd, timeout):
        commands.append(list(argv))
        return launcher.CommandResult(0, json.dumps(state), "")

    opened: list[str] = []
    with pytest.raises(launcher.LaunchError) as caught:
        launcher.launch_latest(
            base=base,
            runner=runner,
            browser_opener=opened.append,
        )

    assert caught.value.code == "LAUNCH_RUNNING_STATE_BLOCKED"
    assert [command[2] for command in commands] == ["status"]
    assert opened == []


def test_explicit_stop_targets_only_matching_current_supervisor(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    commands: list[list[str]] = []

    def runner(argv, cwd, timeout):
        command = list(argv)
        commands.append(command)
        if command[2] == "status":
            state = _running_state(record, status="circuit_open")
            state["circuit_open"] = True
            return launcher.CommandResult(0, json.dumps(state), "")
        assert command[2] == "stop"
        return launcher.CommandResult(0, '{"status":"stopped"}', "")

    result = launcher.stop_latest(base=base, runner=runner)

    assert result == {
        "ok": True,
        "status": "stopped",
        "release_id": record["release_id"],
        "stop_calls": 1,
    }
    assert [command[2] for command in commands] == ["status", "stop"]
    assert all("start" not in command for command in commands)


def test_explicit_stop_rejects_running_different_release_without_stop(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    commands: list[list[str]] = []

    def runner(argv, cwd, timeout):
        commands.append(list(argv))
        return launcher.CommandResult(
            0,
            json.dumps(_running_state(record, release_id="release-deadbeefdeadbeefdeadbeef")),
            "",
        )

    with pytest.raises(launcher.LaunchError) as caught:
        launcher.stop_latest(base=base, runner=runner)

    assert caught.value.code == "LAUNCH_RUNNING_RELEASE_MISMATCH"
    assert [command[2] for command in commands] == ["status"]


def test_supervise_execves_foreground_current_supervisor_without_secrets(
    sealed_release: tuple[dict, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, base = sealed_release
    calls: list[tuple[str, list[str], dict[str, str]]] = []
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross-exec-boundary")
    monkeypatch.setenv("ZF_ACTIONS_KEY", "must-not-cross-exec-boundary")

    def runner(argv, cwd, timeout):
        return launcher.CommandResult(3, '{"status":"not_running","running":false}', "")

    class ExecBoundary(Exception):
        pass

    def execve(path, argv, environment):
        calls.append((path, list(argv), dict(environment)))
        raise ExecBoundary

    with pytest.raises(ExecBoundary):
        launcher.supervise_latest(base=base, runner=runner, execve_fn=execve)

    assert len(calls) == 1
    executable, argv, environment = calls[0]
    spec = launcher.parse_release_spec(
        launcher.load_current_snapshot(base / "current.json"), base
    )
    assert executable == record["python_executable"]
    assert argv == launcher.build_run_argv(spec)
    assert argv[2] == "run"
    assert "start" not in argv
    assert "OPENAI_API_KEY" not in environment
    assert "ZF_ACTIONS_KEY" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_supervise_rejects_running_old_release_without_exec(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    exec_calls: list[object] = []

    def runner(argv, cwd, timeout):
        return launcher.CommandResult(
            0,
            json.dumps(_running_state(record, release_id="release-deadbeefdeadbeefdeadbeef")),
            "",
        )

    with pytest.raises(launcher.LaunchError) as caught:
        launcher.supervise_latest(
            base=base,
            runner=runner,
            execve_fn=lambda *args: exec_calls.append(args),
        )

    assert caught.value.code == "LAUNCH_RUNNING_RELEASE_MISMATCH"
    assert exec_calls == []


def test_system_python_bootstrap_execs_only_selected_frozen_runtime(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    environment = dict(os.environ)
    environment["HOME"] = "/tmp/untrusted-home-must-be-ignored"
    environment["PYTHONPATH"] = "/tmp/untrusted-pythonpath-must-be-ignored"

    completed = subprocess.run(
        _isolated_bootstrap_command(base, "--no-open"),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0] == (
        "BOOTSTRAP_EXEC=" + record["release_dir"] + "/scripts/launch_latest_release.py"
    )
    assert lines[1:] == ["--no-open", "--base", str(base)]
    assert completed.stderr == ""
    assert not (base.parents[3] / "candidate-environment-not-isolated").exists()


def test_isolated_bootstrap_ignores_pythonpath_before_trust_checks(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    injection = tmp_path / "inject"
    marker = tmp_path / "sitecustomize-executed"
    _write(
        injection / "sitecustomize.py",
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(injection)

    completed = subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            "-B",
            str(root / "scripts" / "launch_latest_release_bootstrap.py"),
            "--base=/tmp/rejected",
        ],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert "LAUNCH_BOOTSTRAP_ARGUMENT_REJECTED" in completed.stderr
    assert not marker.exists()


def test_bootstrap_full_runtime_tamper_never_executes_candidate_python(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    site_file = (
        Path(record["python_executable"]).parents[1]
        / "lib"
        / "python"
        / "site-packages"
        / "fixture.py"
    )
    site_file.chmod(0o644)
    site_file.write_text("VALUE = 'tampered'\n", encoding="utf-8")
    site_file.chmod(0o444)
    environment = dict(os.environ)
    environment["HOME"] = "/tmp/untrusted-home-must-be-ignored"

    completed = subprocess.run(
        _isolated_bootstrap_command(base, "--no-open"),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert "BOOTSTRAP_EXEC=" not in completed.stdout
    assert "LAUNCH_BOOTSTRAP_RUNTIME_DIGEST_MISMATCH" in completed.stderr


def test_bootstrap_external_python_byte_tamper_never_executes_candidate(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    logical_python = Path(record["python_executable"])
    external_python = logical_python.resolve(strict=True)
    external_python.write_text(
        "#!/bin/sh\nprintf 'CANDIDATE_EXECUTED\\n'\nexit 0\n",
        encoding="utf-8",
    )
    external_python.chmod(0o755)
    environment = dict(os.environ)
    environment["HOME"] = "/tmp/untrusted-home-must-be-ignored"

    completed = subprocess.run(
        _isolated_bootstrap_command(base, "--no-open"),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert "CANDIDATE_EXECUTED" not in completed.stdout
    assert "LAUNCH_BOOTSTRAP_RUNTIME_DIGEST_MISMATCH" in completed.stderr


def test_bootstrap_rejects_writable_manifest_before_candidate_exec(
    sealed_release: tuple[dict, Path],
) -> None:
    record, base = sealed_release
    manifest = Path(record["release_dir"]) / "release-manifest.json"
    manifest.chmod(0o644)
    environment = dict(os.environ)
    environment["HOME"] = "/tmp/untrusted-home-must-be-ignored"

    completed = subprocess.run(
        _isolated_bootstrap_command(base, "--no-open"),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert "BOOTSTRAP_EXEC=" not in completed.stdout
    assert "LAUNCH_BOOTSTRAP_MANIFEST_UNTRUSTED" in completed.stderr


def test_fixed_shell_wrapper_and_legacy_entrypoints_are_fail_closed() -> None:
    root = Path(__file__).resolve().parents[2]
    wrapper = root / "scripts" / "launch_latest_release.sh"
    wrapper_source = wrapper.read_text(encoding="utf-8")
    bootstrap_source = (root / "scripts" / "launch_latest_release_bootstrap.py").read_text(
        encoding="utf-8"
    )
    run_source = (root / "scripts" / "run_web_ui.sh").read_text(encoding="utf-8")
    start_source = (root / "scripts" / "start_web_ui_background.sh").read_text(
        encoding="utf-8"
    )
    watchdog_source = (root / "scripts" / "web_ui_watchdog.sh").read_text(
        encoding="utf-8"
    )

    assert stat.S_IMODE(wrapper.stat().st_mode) & stat.S_IXUSR
    assert 'BOOTSTRAP_PYTHON="/usr/bin/python3"' in wrapper_source
    assert "pwd.getpwuid(os.getuid()).pw_dir" in wrapper_source
    assert 'exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" "$@"' in wrapper_source
    assert "os.execve" in bootstrap_source
    assert "eval(" not in bootstrap_source
    assert "ZF_DEV_WORKSPACE_MODE" in run_source
    assert "com.zhifei.construction-expert" in run_source
    assert 'exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" "${SEALED_ARGS[@]}"' in run_source
    assert "ZF_DEV_WORKSPACE_MODE" in start_source
    assert 'exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP"' in start_source
    assert "ZF_DEV_WORKSPACE_MODE" in watchdog_source
    assert 'exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" --no-open' in watchdog_source
    for source in (wrapper_source, run_source, start_source, watchdog_source):
        assert "current/scripts" not in source


def test_stop_and_desktop_generators_use_only_fixed_current_entrypoint() -> None:
    root = Path(__file__).resolve().parents[2]
    stop_source = (root / "scripts" / "stop_web_ui_background.sh").read_text(
        encoding="utf-8"
    )
    app_source = (root / "scripts" / "create_desktop_launcher.sh").read_text(
        encoding="utf-8"
    )
    shortcut_source = (root / "scripts" / "create_desktop_shortcut.sh").read_text(
        encoding="utf-8"
    )

    assert "ZF_DEV_WORKSPACE_MODE" in stop_source
    assert 'exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" --stop' in stop_source
    assert "/bootstrap/launch_current.py" in app_source
    assert "/usr/bin/python3" in app_source
    assert 'rootPath & "/scripts/run_web_ui.sh"' not in app_source
    assert "/bootstrap/launch_current.py" in shortcut_source
    assert "/usr/bin/python3" in shortcut_source
    assert "./scripts/run_web_ui.sh" not in shortcut_source
    assert "current/scripts" not in stop_source + app_source + shortcut_source
