#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[CHECK] repo root: $ROOT"

# 1) No nested git repositories. (macOS bash 3 compatible)
nested="$(find . -mindepth 2 -type d -name .git | sed 's#^\./##' | sort || true)"
if [ -n "$nested" ]; then
  echo "[FAIL] nested .git directories found:"
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    printf ' - %s\n' "$line"
  done <<EOF
$nested
EOF
  exit 2
fi
echo "[OK] no nested .git repositories"

# 2) Canonical backend app entry exists.
if [ ! -f backend/app/main.py ]; then
  echo "[FAIL] missing canonical backend entry: backend/app/main.py"
  exit 2
fi
echo "[OK] backend/app/main.py exists"

# 3) Compatibility entry points to canonical app.
if ! rg -n "from backend\.app\.main import app" app/main.py >/dev/null 2>&1; then
  echo "[FAIL] app/main.py is not mapped to backend.app.main"
  exit 2
fi
echo "[OK] app/main.py compatibility mapping is valid"

# 4) Inbox folder exists for unattended pipeline.
mkdir -p projects/inbox projects/work projects/done projects/failed
if [ ! -d projects/inbox ]; then
  echo "[FAIL] projects/inbox missing"
  exit 2
fi
echo "[OK] projects workspace folders ready"

echo "[PASS] repository layout convergence checks passed"
