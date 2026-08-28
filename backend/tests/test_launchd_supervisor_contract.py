from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_INSTALLER = ROOT / "scripts" / "install_web_ui_launchd.sh"
LEGACY_INSTALLER = ROOT / "scripts" / "install_launchd_agent.sh"
CANONICAL_UNINSTALLER = ROOT / "scripts" / "uninstall_web_ui_launchd.sh"
LEGACY_UNINSTALLER = ROOT / "scripts" / "uninstall_launchd_agent.sh"
SYSTEMD_UNIT = ROOT / "deploy" / "systemd" / "docgen-autoplan.service"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _embedded_program_arguments(source: str) -> str:
    match = re.search(
        r"program_arguments\s*=\s*\[(?P<body>.*?)\]\s*\npayload\s*=",
        source,
        flags=re.DOTALL,
    )
    assert match, "installer must build one explicit ProgramArguments allowlist"
    return match.group("body")


def test_launchd_plist_has_one_supervisor_entrypoint_and_no_legacy_children() -> None:
    source = _source(CANONICAL_INSTALLER)
    arguments = _embedded_program_arguments(source)

    assert 'PLIST_ID="com.youfeini.docgen.runtime-supervisor"' in source
    assert "pwd.getpwuid(os.getuid()).pw_dir" in source
    assert 'BASE="$OS_HOME/Library/Application Support/com.zhifei.construction-expert"' in source
    assert 'TRUSTED_BOOTSTRAP="$BASE/bootstrap/launch_current.py"' in source
    assert 'BOOTSTRAP_PYTHON="/usr/bin/python3"' in source
    assert source.count('"ProgramArguments": program_arguments') == 1
    assert source.count("launchctl bootstrap") == 1
    assert "bootstrap_python" in arguments
    assert '"-I"' in arguments
    assert '"-B"' in arguments
    assert "trusted_bootstrap" in arguments
    assert '"--supervise"' in arguments
    assert "runtime_supervisor.py" not in arguments
    assert '"KeepAlive": True' in source
    assert '"WorkingDirectory": base' in source
    assert "current/scripts" not in source

    for pinned_fragment in (
        "--release-dir",
        "--python",
        "--backend-port",
        "--ui-port",
        "--expected-system-id",
        "--expected-release-id",
        "--expected-manifest-digest",
        "--expected-source-digest",
        "--expected-runtime-digest",
        "--env-file",
        "/venv/",
        "/releases/release-",
    ):
        assert pinned_fragment not in arguments

    for forbidden_entrypoint in (
        "uvicorn",
        "streamlit run",
        "backend.app.main:app",
        "web_ui_watchdog.sh",
        "watch_projects_autoplan.py",
    ):
        assert forbidden_entrypoint not in arguments.lower()


def test_launchd_plist_never_serializes_or_expands_credentials() -> None:
    source = _source(CANONICAL_INSTALLER)
    lowered = source.lower()

    for forbidden_name in (
        "api_key",
        "api-key",
        "actions_key",
        "access_token",
        "authorization",
        "client_secret",
    ):
        assert forbidden_name not in lowered

    assert "ZF_RELEASE_ID" not in source
    assert "ZF_RELEASE_MANIFEST_DIGEST" not in source
    assert "ZF_RELEASE_SOURCE_DIGEST" not in source
    assert "ZF_RUNTIME_DIGEST" not in source
    assert '"--env-file"' not in source
    assert "plistlib.dump" in source
    assert not re.search(r"(?m)^\s*(?:source|\.)\s+", source)

    environment_block = re.search(
        r'"EnvironmentVariables":\s*\{(?P<body>.*?)\},\s*\n\s*"ProgramArguments"',
        source,
        flags=re.DOTALL,
    )
    assert environment_block
    serialized_names = set(re.findall(r'^\s*"([A-Z0-9_]+)"\s*:', environment_block.group("body"), re.MULTILINE))
    assert serialized_names == {"PATH", "LANG", "LC_ALL", "PYTHONUTF8"}


def test_legacy_installer_delegates_to_the_single_canonical_installer() -> None:
    source = _source(LEGACY_INSTALLER)

    assert 'exec "$SCRIPT_DIR/install_web_ui_launchd.sh" "$@"' in source
    assert "plistlib" not in source
    assert "launchctl bootstrap" not in source
    assert "uvicorn" not in source.lower()
    assert "watch_projects_autoplan" not in source


def test_uninstallers_stop_the_supervisor_and_remove_obsolete_agents() -> None:
    canonical = _source(CANONICAL_UNINSTALLER)
    legacy = _source(LEGACY_UNINSTALLER)

    assert 'SUPERVISOR_ID="com.youfeini.docgen.runtime-supervisor"' in canonical
    assert 'launchctl bootout "gui/$UID/${label}"' in canonical
    assert 'launchctl bootout "gui/$UID" "$path"' in canonical
    assert "runtime supervisor is stopped and uninstalled" in canonical
    assert 'exec "$SCRIPT_DIR/uninstall_web_ui_launchd.sh" "$@"' in legacy


def test_systemd_template_also_uses_the_single_secret_free_supervisor_unit() -> None:
    source = _source(SYSTEMD_UNIT)

    assert "runtime_supervisor.py run" in source
    assert "EnvironmentFile=/etc/docgen-autoplan/runtime.env" in source
    assert " -m uvicorn " not in source
    assert "Restart=always" not in source
    for forbidden in (
        "API_KEY=",
        "ACTIONS_KEY=",
        "ACCESS_TOKEN=",
        "CLIENT_SECRET=",
        "CHANGE_ME",
    ):
        assert forbidden not in source
