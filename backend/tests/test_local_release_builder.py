from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from scripts import build_local_release as builder
from scripts.runtime_supervisor import SupervisorError, verify_release_manifest


class SimulatedProcessInterruption(BaseException):
    pass


@pytest.fixture(autouse=True)
def _restore_test_tree_permissions(tmp_path: Path):
    """Keep production seals read-only while allowing pytest to remove its own fixture."""

    yield
    builder._make_tree_writable_for_cleanup(tmp_path)


def _write(path: Path, content: str, *, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def _small_source(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    _write(source / "app.py", "print('ui')\n")
    _write(source / "backend" / "app" / "main.py", "APP = 'backend'\n")
    _write(source / "backend" / "tests" / "test_untracked_contract.py", "def test_it():\n    assert True\n")
    _write(source / "scripts" / "runtime_supervisor.py", "# sealed supervisor fixture\n")
    _write(
        source / builder.SOURCE_BOOTSTRAP_RELATIVE_PATH,
        "#!/usr/bin/python3\n# fixed bootstrap fixture\n",
        mode=0o555,
    )
    _write(source / "scripts" / "worker.sh", "#!/bin/sh\nexit 0\n", mode=0o755)
    _write(source / ".git" / "HEAD", "must-not-copy\n")
    _write(source / "__pycache__" / "app.pyc", "must-not-copy\n")
    _write(source / "diagnostic.log", "must-not-copy\n")
    _write(source / "docs" / "RUNTIME_ACCEPTANCE_REPORT.md", "finalized-after-seal\n")
    _write(source / "docs" / "RUNTIME_REMEDIATION_REPORT.md", "finalized-after-seal\n")
    _write(source / "docs" / "included.md", "sealed-documentation\n")
    _write(source / "data" / "input.txt", "seed-data\n")
    _write(source / "backend" / "data" / "runtime.txt", "seed-backend-data\n")
    _write(source / "build" / "generated.txt", "seed-build\n")

    env_file = source / ".env.local"
    _write(env_file, "OPENAI_API_KEY=fake-test-only-provider-value\n", mode=0o600)

    venv = source / ".venv"
    execution_marker = tmp_path / "candidate-python-executed"
    _write(
        venv / "bin" / "python",
        f"#!/bin/sh\nprintf executed > '{execution_marker}'\n"
        "exit 2\n",
        mode=0o755,
    )
    _write(venv / "pyvenv.cfg", "home = /fixture\n")
    _write(venv / "lib" / "python3.12" / "site-packages" / "fixture.py", "VALUE = 1\n")
    return source, venv, env_file


def _build(tmp_path: Path, *, seed_state: bool = True) -> tuple[dict, Path, Path]:
    source, venv, env_file = _small_source(tmp_path)
    base = tmp_path / "sealed-base"
    result = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=venv,
        source_env=env_file,
        seed_state=seed_state,
    )
    return result, source, base


def _replacement_record(first: dict, base: Path, hexadecimal: str) -> dict:
    replacement_id = "release-" + hexadecimal * 24
    replacement_dir = base / "releases" / replacement_id
    replacement_dir.mkdir(mode=0o555)
    return {
        **first,
        "release_id": replacement_id,
        "source_digest": hexadecimal * 24 + first["source_digest"][24:],
        "release_dir": str(replacement_dir),
    }


def test_default_base_has_no_extra_local_releases_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    account = type("Account", (), {"pw_dir": "/tmp/example-home"})()
    monkeypatch.setattr(builder.pwd, "getpwuid", lambda _uid: account)

    assert builder.default_release_base() == Path(
        "/tmp/example-home/Library/Application Support/com.zhifei.construction-expert"
    ).resolve()


def test_build_seals_complete_source_runtime_manifest_and_current_pointer(tmp_path: Path) -> None:
    result, source, base = _build(tmp_path)
    release = Path(result["release_dir"])
    runtime = base / "runtimes" / result["runtime_digest"]
    manifest_path = release / "release-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    provenance = json.loads(
        (release / builder.PROVENANCE_NAME).read_text(encoding="utf-8")
    )

    assert result["release_id"] == f"release-{result['source_digest'][:24]}"
    assert result["manifest_digest"] == __import__("hashlib").sha256(manifest_bytes).hexdigest()
    assert manifest["schema_version"] == 1
    assert provenance == {
        "schema_version": 1,
        "build_sha": None,
        "source_branch": None,
        "source_dirty": None,
        "runtime_digest": result["runtime_digest"],
    }
    assert builder.PROVENANCE_NAME in {item["path"] for item in manifest["files"]}
    assert (release / "backend" / "tests" / "test_untracked_contract.py").is_file()
    assert not (release / ".git").exists()
    assert not (release / ".venv").exists()
    assert not (release / ".env.local").exists()
    assert not (release / "__pycache__").exists()
    assert not (release / "diagnostic.log").exists()
    assert not (release / "docs" / "RUNTIME_ACCEPTANCE_REPORT.md").exists()
    assert not (release / "docs" / "RUNTIME_REMEDIATION_REPORT.md").exists()
    assert (release / "docs" / "included.md").is_file()
    assert (release / "scripts" / "worker.sh").stat().st_mode & stat.S_IXUSR

    expected_links = set(builder.MUTABLE_PATHS)
    assert {item["path"] for item in manifest["mutable_links"]} == expected_links
    for relative in expected_links:
        link = release / relative
        assert link.is_symlink()
        assert Path(os.readlink(link)).is_absolute()
        assert Path(os.readlink(link)).is_relative_to(base / "state" / "workspace")

    identity = builder.ExpectedIdentity(
        system_id=result["system_id"],
        release_id=result["release_id"],
        manifest_digest=result["manifest_digest"],
        source_digest=result["source_digest"],
        runtime_digest=result["runtime_digest"],
    )
    verified = verify_release_manifest(release, identity)
    assert verified["release_id"] == result["release_id"]
    assert builder.compute_runtime_digest(Path(result["python_executable"])) == result["runtime_digest"]

    for tree in (release, runtime):
        for current, directories, files in os.walk(tree, followlinks=False):
            current_path = Path(current)
            assert stat.S_IMODE(current_path.lstat().st_mode) & 0o222 == 0
            directories[:] = [name for name in directories if not (current_path / name).is_symlink()]
            for name in files:
                path = current_path / name
                if not path.is_symlink():
                    assert stat.S_IMODE(path.lstat().st_mode) & 0o222 == 0

    current_json = base / "current.json"
    current = json.loads(current_json.read_text(encoding="utf-8"))
    assert stat.S_IMODE(current_json.stat().st_mode) == 0o600
    assert current == result
    assert (base / "current").is_symlink()
    assert os.readlink(base / "current") == str(release)
    for secure_dir in (
        base,
        base / "state",
        base / "state" / "workspace",
        base / "state" / "supervisor",
        base / "secrets",
    ):
        assert stat.S_IMODE(secure_dir.stat().st_mode) == 0o700

    secret_bytes = (base / "secrets" / "runtime.env").read_bytes()
    assert b"fake-test-only-provider-value" in secret_bytes
    assert b"ZF_ACTIONS_KEY=" in secret_bytes
    assert b"fake-test-only-provider-value" not in json.dumps(result).encode()
    assert stat.S_IMODE((base / "secrets" / "runtime.env").stat().st_mode) == 0o600
    assert source.is_dir()
    assert not (tmp_path / "candidate-python-executed").exists()
    trusted_bootstrap = (
        base
        / builder.TRUSTED_BOOTSTRAP_DIRECTORY_NAME
        / builder.TRUSTED_BOOTSTRAP_NAME
    )
    assert trusted_bootstrap.read_bytes() == (
        source / builder.SOURCE_BOOTSTRAP_RELATIVE_PATH
    ).read_bytes()
    assert stat.S_IMODE(trusted_bootstrap.stat().st_mode) == 0o444
    assert stat.S_IMODE(trusted_bootstrap.parent.stat().st_mode) == 0o555


def test_seed_state_and_existing_secret_are_never_overwritten(tmp_path: Path) -> None:
    source, venv, env_file = _small_source(tmp_path)
    base = tmp_path / "sealed-base"
    existing_data = base / "state" / "workspace" / "data"
    _write(existing_data / "keep.txt", "external-state\n")
    existing_secret = base / "secrets" / "runtime.env"
    _write(existing_secret, "ZF_ACTIONS_KEY=preserve-existing-test-value\n", mode=0o600)

    builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=venv,
        source_env=env_file,
        seed_state=True,
    )

    assert (existing_data / "keep.txt").read_text(encoding="utf-8") == "external-state\n"
    assert not (existing_data / "input.txt").exists()
    assert (
        base / "state" / "workspace" / "backend" / "data" / "runtime.txt"
    ).read_text(encoding="utf-8") == "seed-backend-data\n"
    assert existing_secret.read_text(encoding="utf-8") == "ZF_ACTIONS_KEY=preserve-existing-test-value\n"


def test_failed_reverse_verification_never_switches_current(tmp_path: Path) -> None:
    result, source, base = _build(tmp_path)
    current_before = (base / "current.json").read_bytes()
    link_before = os.readlink(base / "current")
    _write(source / "new_untracked_source.py", "VALUE = 2\n")

    def reject(_release: Path, _identity: builder.ExpectedIdentity) -> dict:
        raise SupervisorError("TEST_REVERSE_VERIFY_BLOCKED", "fixture rejection")

    with pytest.raises(SupervisorError, match="fixture rejection"):
        builder.build_local_release(
            source_root=source,
            base=base,
            source_venv=source / ".venv",
            source_env=source / ".env.local",
            seed_state=False,
            verify_fn=reject,
        )

    assert (base / "current.json").read_bytes() == current_before
    assert os.readlink(base / "current") == link_before
    assert json.loads(current_before)["release_id"] == result["release_id"]


def test_full_frozen_runtime_digest_detects_site_packages_tampering(tmp_path: Path) -> None:
    result, source, base = _build(tmp_path)
    runtime_root = base / "runtimes" / result["runtime_digest"]
    package = runtime_root / "venv" / "lib" / "python3.12" / "site-packages" / "fixture.py"
    parent = package.parent

    parent.chmod(0o755)
    package.chmod(0o644)
    package.write_text("VALUE = 2\n", encoding="utf-8")
    package.chmod(0o444)
    parent.chmod(0o555)

    assert (
        builder.compute_runtime_digest(Path(result["python_executable"]))
        != result["runtime_digest"]
    )
    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.build_local_release(
            source_root=source,
            base=base,
            source_venv=source / ".venv",
            source_env=source / ".env.local",
        )
    assert captured.value.code == "RELEASE_RUNTIME_EXISTING_MISMATCH"


def test_runtime_change_alone_changes_source_and_release_identity(tmp_path: Path) -> None:
    first, source, base = _build(tmp_path)
    package = source / ".venv" / "lib" / "python3.12" / "site-packages" / "fixture.py"
    package.write_text("VALUE = 9\n", encoding="utf-8")

    second = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=source / ".venv",
        source_env=source / ".env.local",
    )

    assert second["runtime_digest"] != first["runtime_digest"]
    assert second["source_digest"] != first["source_digest"]
    assert second["release_id"] != first["release_id"]
    provenance = json.loads(
        (Path(second["release_dir"]) / builder.PROVENANCE_NAME).read_text(encoding="utf-8")
    )
    assert provenance["runtime_digest"] == second["runtime_digest"]


def test_rebuilding_same_target_is_idempotent_and_does_not_retire_it(tmp_path: Path) -> None:
    first, source, base = _build(tmp_path)

    second = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=source / ".venv",
        source_env=source / ".env.local",
    )

    assert second == first
    marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert not marker.exists()


def test_existing_external_bootstrap_mismatch_blocks_switch(tmp_path: Path) -> None:
    first, source, base = _build(tmp_path)
    current_before = (base / builder.CURRENT_JSON_NAME).read_bytes()
    link_before = os.readlink(base / builder.CURRENT_LINK_NAME)
    bootstrap_source = source / builder.SOURCE_BOOTSTRAP_RELATIVE_PATH
    bootstrap_source.chmod(0o755)
    bootstrap_source.write_text(
        "#!/usr/bin/python3\n# unexpected trust-root replacement\n",
        encoding="utf-8",
    )
    bootstrap_source.chmod(0o555)

    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.build_local_release(
            source_root=source,
            base=base,
            source_venv=source / ".venv",
            source_env=source / ".env.local",
        )

    assert captured.value.code == "RELEASE_BOOTSTRAP_MISMATCH"
    assert (base / builder.CURRENT_JSON_NAME).read_bytes() == current_before
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == link_before
    assert json.loads(current_before)["release_id"] == first["release_id"]


def test_retired_release_cannot_be_reactivated_a_b_a(tmp_path: Path) -> None:
    first, source, base = _build(tmp_path)
    app = source / "app.py"
    original = app.read_bytes()
    app.write_text("print('ui-v2')\n", encoding="utf-8")
    second = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=source / ".venv",
        source_env=source / ".env.local",
    )
    assert second["release_id"] != first["release_id"]
    marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert marker.is_file()
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600

    app.write_bytes(original)
    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.build_local_release(
            source_root=source,
            base=base,
            source_venv=source / ".venv",
            source_env=source / ".env.local",
        )

    assert captured.value.code == "RELEASE_ROLLBACK_BLOCKED"
    selected = json.loads((base / builder.CURRENT_JSON_NAME).read_text(encoding="utf-8"))
    assert selected["release_id"] == second["release_id"]
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == second["release_dir"]


def test_current_compare_and_swap_rejects_mid_switch_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _source, base = _build(tmp_path)
    current_before = (base / builder.CURRENT_JSON_NAME).read_bytes()
    link_before = os.readlink(base / builder.CURRENT_LINK_NAME)
    original_loader = builder._load_current_pointer
    observed = original_loader(base)
    assert observed is not None
    calls = 0

    def changed_after_observation(_base: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            return observed
        return {**observed, "raw": observed["raw"] + b"external-change"}

    replacement_id = "release-" + "f" * 24
    replacement_dir = base / "releases" / replacement_id
    replacement_dir.mkdir(mode=0o555)
    replacement = {
        **first,
        "release_id": replacement_id,
        "source_digest": "f" * 24 + first["source_digest"][24:],
        "release_dir": str(replacement_dir),
    }
    monkeypatch.setattr(builder, "_load_current_pointer", changed_after_observation)

    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.switch_current(base, replacement)

    assert captured.value.code == "RELEASE_CURRENT_CHANGED"
    assert (base / builder.CURRENT_JSON_NAME).read_bytes() == current_before
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == link_before


def test_failed_link_replace_restores_previous_current_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _source, base = _build(tmp_path)
    current_before = (base / builder.CURRENT_JSON_NAME).read_bytes()
    link_before = os.readlink(base / builder.CURRENT_LINK_NAME)
    replacement_id = "release-" + "e" * 24
    replacement_dir = base / "releases" / replacement_id
    replacement_dir.mkdir(mode=0o555)
    updated = {
        **first,
        "release_id": replacement_id,
        "source_digest": "e" * 24 + first["source_digest"][24:],
        "release_dir": str(replacement_dir),
    }
    original_replace = os.replace

    def fail_current_link(source, destination):
        if Path(destination) == base / builder.CURRENT_LINK_NAME:
            raise OSError("fixture link replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", fail_current_link)
    with pytest.raises(OSError, match="fixture link replace failure"):
        builder.switch_current(base, updated)

    assert (base / builder.CURRENT_JSON_NAME).read_bytes() == current_before
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == link_before
    failed_retirement = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert not failed_retirement.exists()


def test_process_interruption_after_intent_keeps_old_current_launchable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "d")
    original_assert = builder._assert_current_unchanged
    calls = 0

    def interrupt_after_intent(check_base: Path, expected):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SimulatedProcessInterruption()
        return original_assert(check_base, expected)

    monkeypatch.setattr(builder, "_assert_current_unchanged", interrupt_after_intent)
    with pytest.raises(SimulatedProcessInterruption):
        builder.switch_current(base, replacement)
    monkeypatch.setattr(builder, "_assert_current_unchanged", original_assert)

    selected = json.loads((base / builder.CURRENT_JSON_NAME).read_text(encoding="utf-8"))
    assert selected["release_id"] == first["release_id"]
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == first["release_dir"]
    assert (base / "state" / builder.TRANSITION_INTENT_NAME).is_file()
    old_marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert not old_marker.exists()

    rebuilt = builder.build_local_release(
        source_root=source,
        base=base,
        source_venv=source / ".venv",
        source_env=source / ".env.local",
    )
    assert rebuilt == first
    assert not (base / "state" / builder.TRANSITION_INTENT_NAME).exists()
    assert not old_marker.exists()


def test_process_interruption_after_new_current_finishes_retirement_on_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "c")
    original_record_retired = builder._record_retired_release

    def interrupt_before_marker(*args, **kwargs):
        raise SimulatedProcessInterruption()

    monkeypatch.setattr(builder, "_record_retired_release", interrupt_before_marker)
    with pytest.raises(SimulatedProcessInterruption):
        builder.switch_current(base, replacement)
    monkeypatch.setattr(builder, "_record_retired_release", original_record_retired)

    selected = json.loads((base / builder.CURRENT_JSON_NAME).read_text(encoding="utf-8"))
    assert selected["release_id"] == replacement["release_id"]
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == replacement["release_dir"]
    assert (base / "state" / builder.TRANSITION_INTENT_NAME).is_file()
    old_marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert not old_marker.exists()

    assert builder.recover_transition_intent(base) == "committed"
    assert old_marker.is_file()
    assert not (base / "state" / builder.TRANSITION_INTENT_NAME).exists()
    assert builder.recover_transition_intent(base) is None
    assert old_marker.is_file()


def test_transition_recovery_completes_json_new_link_old_split(tmp_path: Path) -> None:
    first, _source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "b")
    current = builder._load_current_pointer(base)
    assert current is not None
    builder._write_transition_intent(
        base,
        current,
        new_current=replacement,
    )
    builder._atomic_write_json(
        base / builder.CURRENT_JSON_NAME,
        replacement,
        mode=0o600,
    )

    assert builder.recover_transition_intent(base) == "committed"
    selected = builder._load_current_pointer(base)
    assert selected is not None
    assert selected["payload"] == replacement
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == replacement["release_dir"]
    assert not (base / "state" / builder.TRANSITION_INTENT_NAME).exists()
    marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert marker.is_file()


def test_transition_recovery_completes_json_old_link_new_split(tmp_path: Path) -> None:
    first, _source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "a")
    current = builder._load_current_pointer(base)
    assert current is not None
    builder._write_transition_intent(base, current, new_current=replacement)
    builder._replace_current_link(base, replacement["release_dir"])

    assert builder.recover_transition_intent(base) == "committed"
    selected = builder._load_current_pointer(base)
    assert selected is not None
    assert selected["payload"] == replacement
    assert os.readlink(base / builder.CURRENT_LINK_NAME) == replacement["release_dir"]


def test_real_process_exit_between_pointer_replaces_is_recoverable(tmp_path: Path) -> None:
    first, _source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "9")
    child = os.fork()
    if child == 0:  # pragma: no cover - assertions run in the parent
        original_replace = builder.os.replace

        def exit_after_current_json(source, destination):
            original_replace(source, destination)
            if Path(destination) == base / builder.CURRENT_JSON_NAME:
                os._exit(137)

        builder.os.replace = exit_after_current_json
        builder.switch_current(base, replacement)
        os._exit(0)

    _pid, status = os.waitpid(child, 0)
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 137
    split = builder._load_current_components(base)
    assert split is not None
    assert split["payload"] == replacement
    assert split["link_target"] == first["release_dir"]
    assert (base / "state" / builder.TRANSITION_INTENT_NAME).is_file()

    assert builder.recover_transition_intent(base) == "committed"
    selected = builder._load_current_pointer(base)
    assert selected is not None
    assert selected["payload"] == replacement


def test_first_install_process_exit_after_json_is_recoverable(tmp_path: Path) -> None:
    first, _source, base = _build(tmp_path)
    (base / builder.CURRENT_JSON_NAME).unlink()
    (base / builder.CURRENT_LINK_NAME).unlink()
    child = os.fork()
    if child == 0:  # pragma: no cover - assertions run in the parent
        original_replace = builder.os.replace

        def exit_after_current_json(source, destination):
            original_replace(source, destination)
            if Path(destination) == base / builder.CURRENT_JSON_NAME:
                os._exit(137)

        builder.os.replace = exit_after_current_json
        builder.switch_current(base, first)
        os._exit(0)

    _pid, status = os.waitpid(child, 0)
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 137
    assert (base / builder.CURRENT_JSON_NAME).is_file()
    assert not (base / builder.CURRENT_LINK_NAME).exists()
    assert (base / "state" / builder.TRANSITION_INTENT_NAME).is_file()

    assert builder.recover_transition_intent(base) == "committed"
    selected = builder._load_current_pointer(base)
    assert selected is not None
    assert selected["payload"] == first
    assert not (base / "state" / builder.TRANSITION_INTENT_NAME).exists()


def test_bootstrap_first_install_exit_before_rename_leaves_safe_staging(
    tmp_path: Path,
) -> None:
    source, _venv, _env = _small_source(tmp_path)
    base = tmp_path / "sealed-base"
    base.mkdir(mode=0o700)
    child = os.fork()
    if child == 0:  # pragma: no cover - assertions run in the parent
        original_replace = builder.os.replace

        def exit_before_bootstrap_rename(source_path, destination):
            if Path(destination) == base / builder.TRUSTED_BOOTSTRAP_DIRECTORY_NAME:
                os._exit(137)
            return original_replace(source_path, destination)

        builder.os.replace = exit_before_bootstrap_rename
        builder.ensure_trusted_bootstrap(base=base, source_root=source)
        os._exit(0)

    _pid, status = os.waitpid(child, 0)
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 137
    assert not (base / builder.TRUSTED_BOOTSTRAP_DIRECTORY_NAME).exists()
    staging = list(base.glob(".bootstrap.*.staging"))
    assert len(staging) == 1

    destination, digest = builder.ensure_trusted_bootstrap(
        base=base,
        source_root=source,
    )
    assert destination.is_file()
    assert builder._sha256_file(destination) == digest
    assert stat.S_IMODE(destination.stat().st_mode) == 0o444
    assert stat.S_IMODE(destination.parent.stat().st_mode) == 0o555


def test_transition_recovery_rejects_unknown_split_identity(tmp_path: Path) -> None:
    first, _source, base = _build(tmp_path)
    replacement = _replacement_record(first, base, "8")
    current = builder._load_current_pointer(base)
    assert current is not None
    builder._write_transition_intent(base, current, new_current=replacement)
    unknown_dir = base / "releases" / ("release-" + "7" * 24)
    unknown_dir.mkdir(mode=0o555)
    builder._replace_current_link(base, str(unknown_dir))

    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.recover_transition_intent(base)

    assert captured.value.code == "RELEASE_TRANSITION_STATE_INVALID"
    assert (base / "state" / builder.TRANSITION_INTENT_NAME).is_file()
    marker = (
        base
        / "state"
        / builder.RETIRED_RELEASES_DIRECTORY_NAME
        / f"{first['release_id']}.json"
    )
    assert not marker.exists()


def test_untrusted_build_lock_fails_before_current_mutation(tmp_path: Path) -> None:
    source, venv, env_file = _small_source(tmp_path)
    base = tmp_path / "sealed-base"
    base.mkdir(mode=0o700)
    lock = base / builder.BUILD_LOCK_NAME
    _write(lock, "", mode=0o644)

    with pytest.raises(builder.ReleaseBuildError) as captured:
        builder.build_local_release(
            source_root=source,
            base=base,
            source_venv=venv,
            source_env=env_file,
        )

    assert captured.value.code == "RELEASE_BUILD_LOCK_UNTRUSTED"
    assert not (base / builder.CURRENT_JSON_NAME).exists()
    assert not (base / builder.CURRENT_LINK_NAME).exists()
