#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${DOCGEN_SMOKE_PYTHON:-python3}"
SMOKE_E2E_SCRIPT="${DOCGEN_SMOKE_E2E_SCRIPT:-scripts/smoke_e2e_v2.py}"
RUN_LOCAL_UI_ADMIN_SMOKE="${DOCGEN_RUN_LOCAL_UI_ADMIN_SMOKE:-0}"
LOCAL_UI_ADMIN_SCRIPT="${DOCGEN_LOCAL_UI_ADMIN_SCRIPT:-$ROOT_DIR/scripts/verify_local_ui_admin_chain.sh}"

"$PYTHON_BIN" "$SMOKE_E2E_SCRIPT"

# MECE/Observability: print consistency summary from build/audit_report.json (top-level)
"$PYTHON_BIN" - <<'PY'
import json, os
from pathlib import Path
mode = (os.getenv('QUALITY_CONSISTENCY_MODE') or 'warn').strip().lower()
if mode not in ('warn','fail'):
    mode = 'warn'

p = Path('build/audit_report.json')
def status(v):
    if v is True: return 'OK'
    if v is False: return 'MISMATCH'
    return 'NA'
if not p.exists():
    print(f'[WARN] consistency(mode={mode}): audit_report missing')
else:
    d = json.loads(p.read_text(encoding='utf-8'))
    print(
        f"[WARN] consistency(mode={mode}): topic={status(d.get('topic_consistency_ok'))} "
        f"domain_key={status(d.get('domain_key_consistency_ok'))} "
        f"region_key={status(d.get('region_key_consistency_ok'))}"
    )
PY

# MECE/Control: consistency gate (warn-only by default; set QUALITY_CONSISTENCY_MODE=fail to block)
"$PYTHON_BIN" - <<'PY'
import json, os, sys
from pathlib import Path
mode = (os.getenv('QUALITY_CONSISTENCY_MODE') or 'warn').strip().lower()
if mode not in ('warn','fail'):
    mode = 'warn'
p = Path('build/audit_report.json')
if not p.exists():
    print(f'[WARN] consistency_gate: audit_report missing (mode={mode})')
    sys.exit(0)
d = json.loads(p.read_text(encoding='utf-8'))
checks = [
  ('topic', 'topic_consistency_ok'),
  ('domain_key', 'domain_key_consistency_ok'),
  ('region_key', 'region_key_consistency_ok'),
]
bad = []
for name, key in checks:
    v = d.get(key)
    if v is False:
        bad.append(name)
if bad:
    msg = '[%s] consistency_gate(%s): %s' % ('FAIL' if mode=='fail' else 'WARN', mode, ','.join(bad))
    print(msg)
    sys.exit(2 if mode=='fail' else 0)
print(f'[OK] consistency_gate: OK (mode={mode})')
sys.exit(0)
PY

if [ "$RUN_LOCAL_UI_ADMIN_SMOKE" = "1" ]; then
    if [ ! -f "$LOCAL_UI_ADMIN_SCRIPT" ]; then
        echo "[FAIL] local_ui_admin_smoke: missing script $LOCAL_UI_ADMIN_SCRIPT"
        exit 1
    fi
    echo "[INFO] local_ui_admin_smoke: enabled ($LOCAL_UI_ADMIN_SCRIPT)"
    bash "$LOCAL_UI_ADMIN_SCRIPT"
fi
