#!/bin/bash
set -e
cd "$(dirname "$0")/.."
python3 scripts/smoke_e2e_v2.py

# MECE/Observability: print consistency summary from build/audit_report.json (top-level)
python3 - <<'PY'
import json
from pathlib import Path
p = Path('build/audit_report.json')
def status(v):
    if v is True: return 'OK'
    if v is False: return 'MISMATCH'
    return 'NA'
if not p.exists():
    print('[WARN] consistency: audit_report missing')
else:
    d = json.loads(p.read_text(encoding='utf-8'))
    print(
        f"[WARN] consistency: topic={status(d.get('topic_consistency_ok'))} "
        f"domain_key={status(d.get('domain_key_consistency_ok'))} "
        f"region_key={status(d.get('region_key_consistency_ok'))}"
    )
PY

# MECE/Control: consistency gate (warn-only by default; set QUALITY_CONSISTENCY_MODE=fail to block)
python3 - <<'PY'
import json, os, sys
from pathlib import Path
mode = (os.getenv('QUALITY_CONSISTENCY_MODE') or 'warn').strip().lower()
if mode not in ('warn','fail'):
    mode = 'warn'
p = Path('build/audit_report.json')
if not p.exists():
    print('[WARN] consistency_gate: audit_report missing')
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
    msg = '[%s] consistency_gate: %s' % ('FAIL' if mode=='fail' else 'WARN', ','.join(bad))
    print(msg)
    sys.exit(2 if mode=='fail' else 0)
print('[OK] consistency_gate: OK')
sys.exit(0)
PY
