#!/usr/bin/env bash
# Install one macOS LaunchAgent whose only target is the fixed current bootstrap.
# The bootstrap resolves and verifies the selected immutable release on every
# launchd start; the plist never pins one release, runtime, identity or secret.
set -euo pipefail

PLIST_ID="com.youfeini.docgen.runtime-supervisor"
BOOTSTRAP_PYTHON="/usr/bin/python3"
OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
PLIST_DIR="$OS_HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/${PLIST_ID}.plist"
BASE="$OS_HOME/Library/Application Support/com.zhifei.construction-expert"
TRUSTED_BOOTSTRAP="$BASE/bootstrap/launch_current.py"
LOG_DIR="$BASE/state/supervisor/logs"

if [ ! -d "$BASE" ] || [ -L "$BASE" ]; then
  echo "[FAIL] immutable release base is unavailable" >&2
  exit 1
fi
BASE_MODE="$(stat -f '%Lp' "$BASE" 2>/dev/null || stat -c '%a' "$BASE" 2>/dev/null || true)"
BASE_OWNER="$(stat -f '%u' "$BASE" 2>/dev/null || stat -c '%u' "$BASE" 2>/dev/null || true)"
if [ "$BASE_MODE" != "700" ] || [ "$BASE_OWNER" != "$UID" ]; then
  echo "[FAIL] immutable release base must be owned by this user with mode 0700" >&2
  exit 1
fi
if [ ! -f "$TRUSTED_BOOTSTRAP" ] || [ -L "$TRUSTED_BOOTSTRAP" ]; then
  echo "[FAIL] fixed external trust-root bootstrap is unavailable" >&2
  exit 1
fi
BOOTSTRAP_MODE="$(stat -f '%Lp' "$TRUSTED_BOOTSTRAP" 2>/dev/null || stat -c '%a' "$TRUSTED_BOOTSTRAP" 2>/dev/null || true)"
BOOTSTRAP_OWNER="$(stat -f '%u' "$TRUSTED_BOOTSTRAP" 2>/dev/null || stat -c '%u' "$TRUSTED_BOOTSTRAP" 2>/dev/null || true)"
if [ "$BOOTSTRAP_MODE" != "444" ] || [ "$BOOTSTRAP_OWNER" != "$UID" ]; then
  echo "[FAIL] fixed external trust-root bootstrap must be owned by this user with mode 0444" >&2
  exit 1
fi
if [ ! -d "$LOG_DIR" ] || [ -L "$LOG_DIR" ]; then
  echo "[FAIL] immutable supervisor log directory is unavailable" >&2
  exit 1
fi
LOG_MODE="$(stat -f '%Lp' "$LOG_DIR" 2>/dev/null || stat -c '%a' "$LOG_DIR" 2>/dev/null || true)"
LOG_OWNER="$(stat -f '%u' "$LOG_DIR" 2>/dev/null || stat -c '%u' "$LOG_DIR" 2>/dev/null || true)"
if [ "$LOG_MODE" != "700" ] || [ "$LOG_OWNER" != "$UID" ]; then
  echo "[FAIL] immutable supervisor log directory must have mode 0700" >&2
  exit 1
fi
if [ ! -x "$BOOTSTRAP_PYTHON" ]; then
  echo "[FAIL] trusted macOS bootstrap Python is unavailable" >&2
  exit 1
fi

UTF8_LOCALE="${ZF_LOCALE:-}"
if [ -z "$UTF8_LOCALE" ] && command -v locale >/dev/null 2>&1; then
  if locale -a 2>/dev/null | grep -Eiq '^zh_CN\.UTF-8$'; then
    UTF8_LOCALE="zh_CN.UTF-8"
  elif locale -a 2>/dev/null | grep -Eiq '^en_US\.UTF-8$'; then
    UTF8_LOCALE="en_US.UTF-8"
  fi
fi
[ -n "$UTF8_LOCALE" ] || UTF8_LOCALE="en_US.UTF-8"

mkdir -p "$PLIST_DIR"

# Retire historical multi-process/watchdog agents.  This installer never
# searches ports or kills arbitrary processes; all targets are fixed labels.
LEGACY_IDS=(
  "com.youfeini.docgen.webui.backend"
  "com.youfeini.docgen.webui.streamlit"
  "com.youfeini.docgen.webui.watchdog"
  "com.youfeini.docgen.autoplan"
  "com.youfeini.docgen.autoplan.watcher"
)
for old_id in "${LEGACY_IDS[@]}"; do
  old_path="$PLIST_DIR/${old_id}.plist"
  launchctl bootout "gui/$UID/${old_id}" >/dev/null 2>&1 || true
  launchctl bootout "gui/$UID" "$old_path" >/dev/null 2>&1 || true
  rm -f "$old_path"
done

# plistlib performs XML escaping.  The external bootstrap is independent of
# current and verifies every selected byte before the frozen Python executes.
/usr/bin/python3 -I -B - \
  "$PLIST_PATH" "$PLIST_ID" "$BASE" "$BOOTSTRAP_PYTHON" "$TRUSTED_BOOTSTRAP" \
  "$LOG_DIR" "$UTF8_LOCALE" <<'PY'
import os
import plistlib
import sys
import tempfile
from pathlib import Path

plist_path, label, base, bootstrap_python, trusted_bootstrap, log_dir, locale = sys.argv[1:]
program_arguments = [
    bootstrap_python,
    "-I",
    "-B",
    trusted_bootstrap,
    "--supervise",
]
payload = {
    "Label": label,
    "RunAtLoad": True,
    "KeepAlive": True,
    "ThrottleInterval": 10,
    "WorkingDirectory": base,
    "EnvironmentVariables": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": locale,
        "LC_ALL": locale,
        "PYTHONUTF8": "1",
    },
    "ProgramArguments": program_arguments,
    "StandardOutPath": str(Path(log_dir) / "runtime-supervisor.out.log"),
    "StandardErrorPath": str(Path(log_dir) / "runtime-supervisor.err.log"),
    "SoftResourceLimits": {"NumberOfFiles": 8192},
    "HardResourceLimits": {"NumberOfFiles": 65536},
}

target = Path(plist_path)
fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
try:
    with os.fdopen(fd, "wb") as handle:
        plistlib.dump(payload, handle, fmt=plistlib.FMT_XML, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary_name, 0o644)
    os.replace(temporary_name, target)
finally:
    try:
        os.unlink(temporary_name)
    except FileNotFoundError:
        pass
PY

# Updating current alone never stops a running supervisor.  Installation (or
# an operator's explicit bootout/kickstart) is the deliberate cutover point.
launchctl bootout "gui/$UID/${PLIST_ID}" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$PLIST_PATH"
launchctl enable "gui/$UID/${PLIST_ID}" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/${PLIST_ID}" >/dev/null 2>&1 || true

echo "[OK] current-aware runtime supervisor LaunchAgent installed: $PLIST_ID"
echo "     bootstrap: $TRUSTED_BOOTSTRAP"
echo "     logs:    $LOG_DIR"
echo "     uninstall: ./scripts/uninstall_web_ui_launchd.sh"
