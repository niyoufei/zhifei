from __future__ import annotations

import hashlib
import json
import os
import signal
import stat
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import launch_latest_release as launcher
from scripts import launch_latest_release_bootstrap as bootstrap
from scripts import runtime_supervisor as supervisor


class FakeProcess:
    def __init__(self, pid: int, *, timeout_once: bool = False) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.timeout_once = timeout_once
        self.wait_calls: list[float | None] = []

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self.timeout_once:
            self.timeout_once = False
            raise subprocess.TimeoutExpired("fake", timeout)
        self.returncode = 0
        return 0


def _make_config(
    tmp_path: Path,
    *,
    env_file: Path | None = None,
    health_interval: float = 0.001,
    startup_timeout: float = 0.01,
    with_mutable_link: bool = False,
) -> supervisor.SupervisorConfig:
    release_dir = tmp_path / "release"
    (release_dir / "backend" / "app").mkdir(parents=True)
    (release_dir / "backend" / "app" / "main.py").write_text("", encoding="utf-8")
    (release_dir / "app.py").write_text("", encoding="utf-8")
    actual_python = tmp_path / "runtime-python"
    actual_python.write_text(
        """#!/bin/sh
if [ "$1" = "-VV" ]; then
  printf '%s\\n' 'Fake Python 3.12.0'
  exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ] && [ "$3" = "freeze" ]; then
  printf '%s\\n' 'pip==24.0' 'example==1.0'
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    actual_python.chmod(0o700)
    venv_dir = tmp_path / "venv"
    (venv_dir / "bin").mkdir(parents=True)
    site_packages = venv_dir / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)
    (site_packages / "demo_runtime.py").write_text("VALUE = 1\n", encoding="utf-8")
    (venv_dir / "pyvenv.cfg").write_text("home = /fake\n", encoding="utf-8")
    python_executable = venv_dir / "bin" / "python"
    python_executable.symlink_to(Path("../..") / actual_python.name)
    runtime_digest = supervisor.compute_runtime_digest(python_executable)
    (release_dir / supervisor.RELEASE_PROVENANCE_NAME).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "build_sha": "a" * 40,
                "source_branch": "codex/test-seal",
                "source_dirty": True,
                "runtime_digest": runtime_digest,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (release_dir / supervisor.RELEASE_PROVENANCE_NAME).chmod(0o444)

    if with_mutable_link:
        mutable_target = tmp_path / "mutable-state"
        mutable_target.mkdir()
        mutable_target.chmod(0o700)
        (mutable_target / "ignored.json").write_text("mutable", encoding="utf-8")
        (release_dir / "runtime-data").symlink_to(mutable_target)

    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    mutable_links: list[dict[str, Any]] = []
    for relative, kind in sorted(
        supervisor._release_tree_entries(release_dir).items()
    ):
        path = release_dir / relative
        info = path.lstat()
        if kind == "directory":
            directories.append(
                {"path": relative, "mode": stat.S_IMODE(info.st_mode)}
            )
        elif kind == "file":
            content = path.read_bytes()
            files.append(
                {
                    "path": relative,
                    "size": len(content),
                    "mode": stat.S_IMODE(info.st_mode),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
        elif kind == "mutable_link":
            mutable_links.append({"path": relative, "target": os.readlink(path)})
    source_digest = supervisor.compute_source_digest(
        files, directories, mutable_links
    )
    release_id = f"release-{source_digest[:24]}"
    manifest = {
        "schema_version": 1,
        "release_id": release_id,
        "source_digest": source_digest,
        "runtime_digest": runtime_digest,
        "files": files,
        "directories": directories,
        "mutable_links": mutable_links,
    }
    manifest_bytes = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    manifest_path = release_dir / supervisor.RELEASE_MANIFEST_NAME
    manifest_path.write_bytes(manifest_bytes)
    manifest_path.chmod(0o444)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    return supervisor.SupervisorConfig(
        release_dir=release_dir.resolve(),
        python_executable=python_executable,
        backend_port=18010,
        ui_port=18501,
        identity=supervisor.ExpectedIdentity(
            system_id="docgen-system",
            release_id=release_id,
            manifest_digest=manifest_digest,
            source_digest=source_digest,
            runtime_digest=runtime_digest,
        ),
        state_dir=(tmp_path / "state").resolve(),
        log_dir=(tmp_path / "logs").resolve(),
        env_file=env_file,
        health_interval_seconds=health_interval,
        startup_timeout_seconds=startup_timeout,
        stop_grace_seconds=0.01,
    )


def _health_body(config: supervisor.SupervisorConfig, **overrides: Any) -> bytes:
    payload: dict[str, Any] = {"ok": True, **config.identity.as_dict()}
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


def test_start_timeout_reaps_detached_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    class _Candidate:
        pid = 7311

        @staticmethod
        def poll():
            return None

        @staticmethod
        def terminate():
            calls.append("terminate")

        @staticmethod
        def kill():
            calls.append("kill")

        @staticmethod
        def wait(timeout=None):
            calls.append(("wait", timeout))
            if calls.count(("wait", supervisor.START_CHILD_REAP_TIMEOUT_SECONDS)) == 1:
                raise subprocess.TimeoutExpired("candidate", timeout)
            return 0

    config = SimpleNamespace(
        validate=lambda: None,
        release_dir=tmp_path.resolve(),
        python_executable=Path("/fixture/python"),
        backend_port=18010,
        ui_port=18501,
        identity=SimpleNamespace(
            system_id="docgen-system",
            release_id="release-fixture1234567890abcdef",
            manifest_digest="a" * 64,
            source_digest="b" * 64,
            runtime_digest="c" * 64,
        ),
        state_dir=(tmp_path / "state").resolve(),
        log_dir=(tmp_path / "logs").resolve(),
        env_file=None,
    )
    ticks = iter((0.0, supervisor.START_CONFIRM_TIMEOUT_SECONDS + 1.0))
    monkeypatch.setattr(supervisor, "_config_from_args", lambda _args: config)
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *args, **kwargs: _Candidate())
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: next(ticks))

    with pytest.raises(supervisor.SupervisorError) as caught:
        supervisor.start_command(SimpleNamespace())

    assert caught.value.code == "SUPERVISOR_START_TIMEOUT"
    assert calls == [
        "terminate",
        ("wait", supervisor.START_CHILD_REAP_TIMEOUT_SECONDS),
        "kill",
        ("wait", supervisor.START_CHILD_REAP_TIMEOUT_SECONDS),
    ]
    assert (
        supervisor.START_CONFIRM_TIMEOUT_SECONDS
        < launcher.SUPERVISOR_START_COMMAND_TIMEOUT_SECONDS
    )


def _rewrite_manifest(
    config: supervisor.SupervisorConfig, mutate: Any
) -> supervisor.SupervisorConfig:
    manifest_path = config.release_dir / supervisor.RELEASE_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    raw = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(raw)
    manifest_path.chmod(0o444)
    identity = supervisor.ExpectedIdentity(
        system_id=config.identity.system_id,
        release_id=manifest["release_id"],
        manifest_digest=hashlib.sha256(raw).hexdigest(),
        source_digest=manifest["source_digest"],
        runtime_digest=manifest["runtime_digest"],
    )
    return replace(config, identity=identity)


def test_env_file_requires_0600_and_values_never_enter_state_or_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "keys.env"
    secret = "sk-test-value-that-must-never-leak"
    env_file.write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")
    env_file.chmod(0o644)
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.load_secret_environment(env_file.resolve())
    assert exc_info.value.code == "SUPERVISOR_ENV_FILE_PERMISSIONS"

    env_file.chmod(0o600)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "inherited-secret-value")
    config = _make_config(tmp_path, env_file=env_file.resolve())
    runtime = supervisor.RuntimeSupervisor(config)
    runtime.logger.emit(
        "probe_failed",
        detail=f"Bearer {secret}",
        credential="inherited-secret-value",
    )
    runtime._write_state("starting")

    event_text = config.event_file.read_text(encoding="utf-8")
    state_text = config.state_file.read_text(encoding="utf-8")
    assert secret not in event_text
    assert "inherited-secret-value" not in event_text
    assert "[REDACTED]" in event_text
    assert secret not in state_text
    assert "inherited-secret-value" not in state_text
    assert stat.S_IMODE(config.event_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(config.state_file.stat().st_mode) == 0o600


def test_spawn_uses_two_new_process_groups_and_exact_release_environment(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    calls: list[tuple[list[str], dict[str, Any]]] = []
    processes = iter((FakeProcess(4101), FakeProcess(4102)))

    def fake_popen(argv: list[str], **kwargs: Any) -> FakeProcess:
        calls.append((argv, kwargs))
        return next(processes)

    runtime = supervisor.RuntimeSupervisor(
        config,
        popen_factory=fake_popen,
        listener_pids=lambda _port: set(),
        getpgid=lambda pid: pid,
        killpg=lambda _pid, _sig: None,
    )
    runtime.child_env.update(
        {
            "ZF_RELEASE_ROOT": "/tmp/attacker-release",
            "ZF_RELEASE_MANAGED": "0",
            "ZF_RUNTIME_MODE": "mutable_checkout",
        }
    )
    runtime._spawn_unit()

    assert len(calls) == 2
    assert runtime._owned_process_groups == {4101, 4102}
    assert calls[0][0][1:4] == ["-m", "uvicorn", "backend.app.main:app"]
    assert calls[1][0][1:4] == ["-m", "streamlit", "run"]
    for _argv, kwargs in calls:
        assert kwargs["start_new_session"] is True
        assert kwargs["cwd"] == str(config.release_dir)
        assert kwargs["env"]["ZF_RELEASE_ID"] == config.identity.release_id
        assert (
            kwargs["env"]["ZF_RELEASE_MANIFEST_DIGEST"]
            == config.identity.manifest_digest
        )
        assert (
            kwargs["env"]["ZF_RELEASE_SOURCE_DIGEST"]
            == config.identity.source_digest
        )
        assert kwargs["env"]["ZF_RUNTIME_DIGEST"] == config.identity.runtime_digest
        assert kwargs["env"]["ZF_RELEASE_ROOT"] == str(config.release_dir)
        assert kwargs["env"]["ZF_RELEASE_MANAGED"] == "1"
        assert kwargs["env"]["ZF_RUNTIME_MODE"] == "sealed_release"
        assert kwargs["env"]["ZF_SUPERVISOR_STATE_FILE"] == str(config.state_file)
        assert kwargs["env"]["ZF_ENABLE_SELF_HEAL"] == "0"
        assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
        assert kwargs["env"]["ZF_BUILD_SHA"] == "a" * 40
        assert kwargs["env"]["ZF_BUILD_BRANCH"] == "codex/test-seal"
        assert kwargs["env"]["ZF_BUILD_DIRTY"] == "1"
        assert _argv[0] == str(config.python_executable)
        assert config.python_executable.is_symlink()


def test_release_manifest_verifies_complete_tree_without_following_mutable_link(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path, with_mutable_link=True)

    manifest = supervisor.verify_release_manifest(config.release_dir, config.identity)

    assert manifest["mutable_links"] == [
        {
            "path": "runtime-data",
            "target": str((tmp_path / "mutable-state").resolve()),
        }
    ]
    # Content below the mutable link is deliberately outside the immutable tree.
    (tmp_path / "mutable-state" / "new-job.json").write_text("new", encoding="utf-8")
    supervisor.verify_release_manifest(config.release_dir, config.identity)

    (tmp_path / "mutable-state").chmod(0o755)
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)
    assert exc_info.value.code == "SUPERVISOR_MUTABLE_LINK_TARGET_UNTRUSTED"


def test_release_manifest_rejects_file_tamper_extra_entry_and_raw_manifest_tamper(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    app_path = config.release_dir / "app.py"
    app_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)
    assert exc_info.value.code == "SUPERVISOR_RELEASE_FILE_METADATA_MISMATCH"

    app_path.write_text("", encoding="utf-8")
    (config.release_dir / "unlisted.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)
    assert exc_info.value.code == "SUPERVISOR_RELEASE_TREE_MISMATCH"
    (config.release_dir / "unlisted.txt").unlink()

    manifest_path = config.release_dir / supervisor.RELEASE_MANIFEST_NAME
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
    manifest_path.chmod(0o444)
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)
    assert exc_info.value.code == "SUPERVISOR_MANIFEST_DIGEST_MISMATCH"


def test_release_id_and_source_digest_are_independently_recomputed(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    wrong_source = "d" * 64
    config = _rewrite_manifest(
        config,
        lambda manifest: manifest.update(
            {
                "source_digest": wrong_source,
                "release_id": f"release-{wrong_source[:24]}",
            }
        ),
    )
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)
    assert exc_info.value.code == "SUPERVISOR_SOURCE_DIGEST_MISMATCH"

    valid = _make_config(tmp_path / "second")
    impostor_release_id = "release-" + "0" * 24
    valid = _rewrite_manifest(
        valid,
        lambda manifest: manifest.update({"release_id": impostor_release_id}),
    )
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(valid.release_dir, valid.identity)
    assert exc_info.value.code == "SUPERVISOR_RELEASE_ID_NOT_CONTENT_ADDRESSED"


def test_runtime_digest_binds_logical_venv_and_pyvenv_content(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    before = supervisor.compute_runtime_digest(config.python_executable)
    assert before == config.identity.runtime_digest
    assert config.python_executable.is_symlink()

    (config.python_executable.parent.parent / "pyvenv.cfg").write_text(
        "home = /changed\n", encoding="utf-8"
    )
    after = supervisor.compute_runtime_digest(config.python_executable)
    assert after != before
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.RuntimeSupervisor(config)
    assert exc_info.value.code == "SUPERVISOR_RUNTIME_DIGEST_MISMATCH"


def test_runtime_digest_binds_every_site_packages_file_without_execution(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "candidate-executed"
    config = _make_config(tmp_path)
    config.python_executable.resolve().write_text(
        f"#!/bin/sh\nprintf executed > {marker}\nexit 2\n",
        encoding="utf-8",
    )
    config.python_executable.resolve().chmod(0o700)
    baseline = supervisor.compute_runtime_digest(config.python_executable)
    assert not marker.exists()

    site_file = (
        config.python_executable.parent.parent
        / "lib"
        / "python3.12"
        / "site-packages"
        / "demo_runtime.py"
    )
    site_file.write_text("VALUE = 2\n", encoding="utf-8")
    assert supervisor.compute_runtime_digest(config.python_executable) != baseline
    assert not marker.exists()


def test_runtime_digest_binds_non_system_macho_dependency_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv = tmp_path / "venv"
    python = venv / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"\xcf\xfa\xed\xfe" + b"fixture-python")
    python.chmod(0o700)
    (venv / "pyvenv.cfg").write_text("home = /fixture\n", encoding="utf-8")
    framework = tmp_path / "external" / "Python.framework" / "Python"
    framework.parent.mkdir(parents=True)
    framework.write_bytes(b"\xcf\xfa\xed\xfe" + b"framework-v1")
    framework.chmod(0o755)

    def fake_otool(path: Path, option: str) -> list[str]:
        resolved = Path(path).resolve()
        if option == "-D":
            return [f"{resolved}:"]
        if option == "-l":
            return [f"{resolved}:"]
        if resolved == python.resolve():
            return [
                f"{resolved}:",
                f"\t{framework} (compatibility version 1.0.0, current version 1.0.0)",
            ]
        return [
            f"{resolved}:",
            "\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1.0.0)",
        ]

    monkeypatch.setattr(supervisor.sys, "platform", "darwin")
    monkeypatch.setattr(bootstrap.sys, "platform", "darwin")
    monkeypatch.setattr(supervisor, "_otool", fake_otool)
    monkeypatch.setattr(bootstrap, "_otool", fake_otool)
    first = supervisor.compute_runtime_digest(python)
    assert first == bootstrap.compute_runtime_digest(python)
    snapshot = supervisor.runtime_tree_snapshot(python)
    assert snapshot["dependency_policy"] == "non_system_macho_closure_v1"
    assert snapshot["external_macho_dependencies"][0]["path"] == str(framework)

    framework.write_bytes(b"\xcf\xfa\xed\xfe" + b"framework-v2")
    framework.chmod(0o755)
    second = supervisor.compute_runtime_digest(python)
    assert second == bootstrap.compute_runtime_digest(python)
    assert second != first


def test_manifest_requires_exact_read_only_mode_and_current_owner(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    manifest_path = config.release_dir / supervisor.RELEASE_MANIFEST_NAME
    manifest_path.chmod(0o644)

    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.verify_release_manifest(config.release_dir, config.identity)

    assert exc_info.value.code == "SUPERVISOR_MANIFEST_UNTRUSTED"


def test_provenance_is_mandatory_and_must_bind_runtime(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    manifest = supervisor.verify_release_manifest(config.release_dir, config.identity)

    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.load_release_provenance(
            config.release_dir,
            {**manifest, "files": []},
            expected_runtime_digest=config.identity.runtime_digest,
        )
    assert exc_info.value.code == "SUPERVISOR_PROVENANCE_MISSING"

    provenance_path = config.release_dir / supervisor.RELEASE_PROVENANCE_NAME
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["runtime_digest"] = "0" * 64
    provenance_path.chmod(0o644)
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    provenance_path.chmod(0o444)
    with pytest.raises(supervisor.SupervisorError) as exc_info:
        supervisor.load_release_provenance(
            config.release_dir,
            manifest,
            expected_runtime_digest=config.identity.runtime_digest,
        )
    assert exc_info.value.code == "SUPERVISOR_PROVENANCE_RUNTIME_MISMATCH"


def test_health_requires_process_ownership_and_all_five_identity_fields(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(
        config,
        listener_pids=lambda port: {5101 if port == config.backend_port else 5102},
        getpgid=lambda pid: pid,
        http_get=lambda url, _timeout: (
            (200, _health_body(config))
            if url.endswith("/livez")
            else (200, b"ok")
        ),
    )
    runtime.backend = FakeProcess(5101)  # type: ignore[assignment]
    runtime.ui = FakeProcess(5102)  # type: ignore[assignment]

    assert runtime.check_health() == (True, None)

    runtime.http_get = lambda url, _timeout: (
        (200, _health_body(config, runtime_digest="d" * 64))
        if url.endswith("/livez")
        else (200, b"ok")
    )
    assert runtime.check_health() == (
        False,
        "SUPERVISOR_BACKEND_IDENTITY_MISMATCH",
    )

    runtime.http_get = lambda url, _timeout: (
        (200, _health_body(config)) if url.endswith("/livez") else (200, b"ok")
    )
    runtime.listener_pids = lambda port: {
        9999 if port == config.backend_port else 5102
    }
    assert runtime.check_health() == (
        False,
        "SUPERVISOR_BACKEND_OWNERSHIP_MISMATCH",
    )


def test_health_classifies_timeout_without_weakening_five_field_identity(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(
        config,
        listener_pids=lambda port: {5101 if port == config.backend_port else 5102},
        getpgid=lambda pid: pid,
    )
    runtime.backend = FakeProcess(5101)  # type: ignore[assignment]
    runtime.ui = FakeProcess(5102)  # type: ignore[assignment]

    runtime.http_get = lambda _url, _timeout: (_ for _ in ()).throw(
        TimeoutError("probe timed out")
    )
    assert runtime.check_health() == (
        False,
        "SUPERVISOR_BACKEND_HEALTH_TIMEOUT",
    )

    for field in config.identity.as_dict():
        runtime.http_get = lambda url, _timeout, field=field: (
            (
                200,
                _health_body(
                    config,
                    **{field: "wrong-identity"},
                ),
            )
            if url.endswith("/livez")
            else (200, b"ok")
        )
        assert runtime.check_health() == (
            False,
            "SUPERVISOR_BACKEND_IDENTITY_MISMATCH",
        )


def test_transient_probe_requires_three_failures_spanning_fifteen_seconds(
    tmp_path: Path,
) -> None:
    now = [0.0]
    wall = [1_000.0]
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(
        config,
        monotonic=lambda: now[0],
        wall_clock=lambda: wall[0],
    )
    code = "SUPERVISOR_BACKEND_HEALTH_TIMEOUT"

    assert runtime._restart_required_for_health_failure(code) is False
    now[0] += 5.0
    wall[0] += 5.0
    assert runtime._restart_required_for_health_failure(code) is False
    now[0] += 5.0
    wall[0] += 5.0
    assert runtime._restart_required_for_health_failure(code) is False
    assert runtime.consecutive_transient_health_failures == 3
    assert runtime._safe_state("degraded")["health_degraded"] is True
    assert runtime._safe_state("degraded")["first_health_failure_at"] == 1_000.0

    now[0] += 5.0
    wall[0] += 5.0
    assert runtime._restart_required_for_health_failure(code) is True

    runtime._record_healthy()
    recovered = runtime._safe_state("healthy")
    assert recovered["health_degraded"] is False
    assert recovered["consecutive_health_failures"] == 0
    assert recovered["last_probe_error_code"] is None

    assert (
        runtime._restart_required_for_health_failure(
            "SUPERVISOR_BACKEND_IDENTITY_MISMATCH"
        )
        is True
    )


def test_crash_breaker_opens_on_third_failure_and_stable_run_resets(
    tmp_path: Path,
) -> None:
    now = [10.0]
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(config, monotonic=lambda: now[0])

    assert runtime._record_failure("FAIL_ONE") is False
    now[0] += 1
    assert runtime._record_failure("FAIL_TWO") is False
    now[0] += 1
    assert runtime._record_failure("FAIL_THREE") is True
    assert runtime.circuit_open is True
    assert len(runtime.crash_times) == 3

    runtime.healthy_since = now[0]
    now[0] += supervisor.STABLE_RESET_SECONDS
    runtime._record_healthy()
    assert runtime.crash_times == []
    assert runtime.circuit_open is False


def test_failure_window_persists_across_processes_and_third_failure_opens(
    tmp_path: Path,
) -> None:
    now = [1_000.0]
    config = _make_config(tmp_path)

    first = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    assert first._record_failure("FAIL_ONE") is False
    first_state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert first_state["restart_count_window"] == 1
    assert first_state["failure_timestamps"] == [1_000.0]

    now[0] += 1.0
    second = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    second._restore_open_circuit()
    assert second.circuit_open is False
    assert second.crash_times == [1_000.0]
    assert second._record_failure("FAIL_TWO") is False

    now[0] += 1.0
    third = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    third._restore_open_circuit()
    assert third.circuit_open is False
    assert third.crash_times == [1_000.0, 1_001.0]
    assert third._record_failure("FAIL_THREE") is True

    state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert state["status"] == "circuit_open"
    assert state["circuit_open"] is True
    assert state["restart_count_window"] == supervisor.MAX_CRASHES_IN_WINDOW
    assert state["failure_timestamps"] == [1_000.0, 1_001.0, 1_002.0]
    assert state["last_error_code"] == "SUPERVISOR_CRASH_LOOP"

    now[0] += supervisor.CRASH_WINDOW_SECONDS + 1.0
    third._write_state("circuit_open")
    aged_state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert aged_state["restart_count_window"] == 0
    assert aged_state["failure_timestamps"] == []
    assert aged_state["circuit_open"] is True

    fourth = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    fourth._restore_open_circuit()
    assert fourth.circuit_open is True
    assert fourth.last_error_code == "SUPERVISOR_CRASH_LOOP"


@pytest.mark.parametrize(
    "damage", ["invalid_json", "wrong_mode", "symlink", "directory"]
)
def test_damaged_existing_state_fails_closed_and_supervisor_holds(
    tmp_path: Path,
    damage: str,
) -> None:
    config = _make_config(tmp_path)
    config.state_dir.mkdir(parents=True, mode=0o700)
    if damage == "symlink":
        outside = tmp_path / "outside-state.json"
        outside.write_text('{"must":"remain"}\n', encoding="utf-8")
        config.state_file.symlink_to(outside)
    elif damage == "directory":
        config.state_file.mkdir()
        (config.state_file / "evidence.txt").write_text("preserve", encoding="utf-8")
    else:
        config.state_file.write_text(
            "not-json\n" if damage == "invalid_json" else "{}\n",
            encoding="utf-8",
        )
        config.state_file.chmod(0o644 if damage == "wrong_mode" else 0o600)

    class HoldingSupervisor(supervisor.RuntimeSupervisor):
        hold_calls = 0
        spawn_calls = 0

        def _spawn_unit(self) -> None:
            self.spawn_calls += 1
            raise AssertionError("children must not start after state recovery failure")

        def _hold_open_circuit(self) -> None:
            self.hold_calls += 1
            self._write_state("circuit_open")
            self.stop_requested.set()

    runtime = HoldingSupervisor(config)
    result = runtime.run(install_signal_handlers=False)

    assert result == 75
    assert runtime.hold_calls == 1
    assert runtime.spawn_calls == 0
    state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert state["status"] == "circuit_open"
    assert state["circuit_open"] is True
    assert state["last_error_code"] == "SUPERVISOR_STATE_RECOVERY_FAILED"
    assert stat.S_IMODE(config.state_file.stat().st_mode) == 0o600
    events = [
        json.loads(line)
        for line in config.event_file.read_text(encoding="utf-8").splitlines()
    ]
    restored = [event for event in events if event["event"] == "circuit_restored"]
    assert restored[-1]["error_code"] == "SUPERVISOR_STATE_RECOVERY_FAILED"
    if damage == "symlink":
        assert (tmp_path / "outside-state.json").read_text(encoding="utf-8") == (
            '{"must":"remain"}\n'
        )
    if damage == "directory":
        quarantined = list(config.state_dir.glob(".supervisor.json.untrusted.*"))
        assert len(quarantined) == 1
        assert (quarantined[0] / "evidence.txt").read_text(encoding="utf-8") == "preserve"


def test_incomplete_persisted_failure_window_fails_closed(tmp_path: Path) -> None:
    now = [2_000.0]
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    runtime._record_failure("FAIL_ONE")
    now[0] += 1.0
    runtime._record_failure("FAIL_TWO")
    payload = json.loads(config.state_file.read_text(encoding="utf-8"))
    payload.pop("failure_timestamps")
    config.state_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    config.state_file.chmod(0o600)

    restored = supervisor.RuntimeSupervisor(config, wall_clock=lambda: now[0])
    restored._restore_open_circuit()

    assert restored.circuit_open is True
    assert restored.last_error_code == "SUPERVISOR_STATE_RECOVERY_FAILED"


def test_run_stops_restarting_after_three_startup_failures(tmp_path: Path) -> None:
    config = _make_config(tmp_path)

    class AlwaysFailSupervisor(supervisor.RuntimeSupervisor):
        starts = 0

        def _spawn_unit(self) -> None:
            self.starts += 1
            self.backend = FakeProcess(6100 + self.starts)  # type: ignore[assignment]
            self.ui = FakeProcess(7100 + self.starts)  # type: ignore[assignment]
            self._write_state("starting")

        def _wait_for_initial_health(self) -> tuple[bool, str | None]:
            return False, "SUPERVISOR_BACKEND_EXITED"

        def _stop_unit(self) -> None:
            self.backend = None
            self.ui = None

        def _hold_open_circuit(self) -> None:
            self._write_state("circuit_open")

    runtime = AlwaysFailSupervisor(config)
    result = runtime.run(install_signal_handlers=False)

    assert result == 75
    assert runtime.starts == supervisor.MAX_CRASHES_IN_WINDOW
    state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert state["status"] == "circuit_open"
    assert state["circuit_open"] is True
    assert state["restart_count_window"] == 3
    assert not config.pid_file.exists()
    assert stat.S_IMODE(config.lock_file.stat().st_mode) == 0o600


def test_spawn_policy_failure_opens_persistent_circuit_on_third_attempt(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)

    class PolicyBlockedSupervisor(supervisor.RuntimeSupervisor):
        starts = 0

        def _spawn_unit(self) -> None:
            self.starts += 1
            raise supervisor.SupervisorError(
                "SUPERVISOR_FOREIGN_LISTENER", "端口已被非本监管器进程占用"
            )

        def _hold_open_circuit(self) -> None:
            self._write_state("circuit_open")

    runtime = PolicyBlockedSupervisor(config)
    result = runtime.run(install_signal_handlers=False)

    assert result == 75
    assert runtime.starts == supervisor.MAX_CRASHES_IN_WINDOW
    state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert state["status"] == "circuit_open"
    assert state["circuit_open"] is True
    assert state["restart_count_window"] == supervisor.MAX_CRASHES_IN_WINDOW
    assert state["last_error_code"] == "SUPERVISOR_CRASH_LOOP"


def test_stop_unit_gracefully_terminates_then_forces_process_group(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    killed: list[tuple[int, int]] = []
    backend = FakeProcess(8101)
    ui = FakeProcess(8102, timeout_once=True)

    def fake_killpg(pid: int, signum: int) -> None:
        killed.append((pid, signum))

    runtime = supervisor.RuntimeSupervisor(
        config,
        getpgid=lambda pid: pid,
        killpg=fake_killpg,
    )
    runtime.backend = backend  # type: ignore[assignment]
    runtime.ui = ui  # type: ignore[assignment]
    runtime._stop_unit()

    assert (8101, signal.SIGTERM) in killed
    assert (8102, signal.SIGTERM) in killed
    assert (8102, signal.SIGKILL) in killed
    assert runtime.backend is None
    assert runtime.ui is None


def test_stop_unit_cleans_verified_orphan_group_but_skips_unverified_group(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    killed: list[tuple[int, int]] = []
    verified_orphan = FakeProcess(8201)
    unverified_exited_process = FakeProcess(8202)
    verified_orphan.returncode = 9
    unverified_exited_process.returncode = 9

    runtime = supervisor.RuntimeSupervisor(
        config,
        getpgid=lambda _pid: (_ for _ in ()).throw(
            AssertionError("an exited leader must use spawn-time provenance")
        ),
        killpg=lambda pid, signum: killed.append((pid, signum)),
    )
    runtime.backend = verified_orphan  # type: ignore[assignment]
    runtime.ui = unverified_exited_process  # type: ignore[assignment]
    runtime._owned_process_groups.add(verified_orphan.pid)

    runtime._stop_unit()

    assert (verified_orphan.pid, signal.SIGTERM) in killed
    assert (verified_orphan.pid, signal.SIGKILL) in killed
    assert not any(pid == unverified_exited_process.pid for pid, _sig in killed)
    assert runtime._owned_process_groups == set()


def test_run_releases_lock_and_stops_unit_when_final_state_write_fails(
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)

    class FinalStateFailureSupervisor(supervisor.RuntimeSupervisor):
        state_write_calls = 0
        stop_calls = 0

        def _restore_open_circuit(self) -> None:
            self.stop_requested.set()

        def _write_state(self, status: str) -> None:
            self.state_write_calls += 1
            if self.state_write_calls == 2:
                raise OSError("injected final state write failure")
            super()._write_state(status)

        def _stop_unit(self) -> None:
            self.stop_calls += 1
            super()._stop_unit()

    runtime = FinalStateFailureSupervisor(config)

    with pytest.raises(OSError, match="injected final state write failure"):
        runtime.run(install_signal_handlers=False)

    assert runtime.stop_calls == 1
    assert not config.pid_file.exists()
    state = json.loads(config.state_file.read_text(encoding="utf-8"))
    assert state["status"] == "stopped"
    lock_probe = supervisor.InstanceLock(config.lock_file, "lock-probe")
    lock_probe.acquire()
    lock_probe.release()


def test_run_releases_lock_when_pid_file_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = _make_config(tmp_path)
    runtime = supervisor.RuntimeSupervisor(config)
    stop_calls = 0
    original_stop = runtime._stop_unit

    def _tracked_stop() -> None:
        nonlocal stop_calls
        stop_calls += 1
        original_stop()

    monkeypatch.setattr(runtime, "_stop_unit", _tracked_stop)
    monkeypatch.setattr(
        supervisor,
        "_write_pid_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("injected pid write failure")
        ),
    )

    with pytest.raises(OSError, match="injected pid write failure"):
        runtime.run(install_signal_handlers=False)

    assert stop_calls == 1
    lock_probe = supervisor.InstanceLock(config.lock_file, "lock-probe")
    lock_probe.acquire()
    lock_probe.release()


def test_lock_is_single_instance_and_all_control_files_are_0600(tmp_path: Path) -> None:
    state_dir = (tmp_path / "state").resolve()
    lock_path = state_dir / supervisor.LOCK_FILE_NAME
    first = supervisor.InstanceLock(lock_path, "first")
    second = supervisor.InstanceLock(lock_path, "second")
    first.acquire()
    try:
        with pytest.raises(supervisor.SupervisorError) as exc_info:
            second.acquire()
        assert exc_info.value.code == "SUPERVISOR_ALREADY_RUNNING"
        supervisor._write_pid_file(state_dir / supervisor.PID_FILE_NAME, os.getpid())
        assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(
            (state_dir / supervisor.PID_FILE_NAME).stat().st_mode
        ) == 0o600
        assert stat.S_IMODE(state_dir.stat().st_mode) == 0o700
    finally:
        first.release()
