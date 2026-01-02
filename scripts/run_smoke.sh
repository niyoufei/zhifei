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
