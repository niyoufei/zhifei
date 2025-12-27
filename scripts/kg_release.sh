#!/usr/bin/env bash
set -euo pipefail

DESC="${1:-snapshot release}"
PACK_ID="${PACK_ID:-kgpack-$(date +%Y%m%d_%H%M%S)}"
DRY_RUN="${DRY_RUN:-0}"

echo "[KG_RELEASE] pack_id=$PACK_ID"
echo "[KG_RELEASE] DRY_RUN=$DRY_RUN"
echo "[KG_RELEASE] desc=$DESC"

BASELINE="$(python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path("kg_config.json").read_text(encoding="utf-8"))
print(cfg.get("active_pack") or "default")
PY
)"
echo "[KG_RELEASE] baseline_active_pack=$BASELINE"

if [ "$DRY_RUN" = "1" ]; then
  PRE_CFG="$(mktemp /tmp/kgcfg.XXXXXX)"
  cp kg_config.json "$PRE_CFG"
  PRE_LIST="$(mktemp /tmp/kgcfglist.XXXXXX)"
  POST_LIST="$(mktemp /tmp/kgcfglist.XXXXXX)"
  ls -1 kg_config.json.bak.* 2>/dev/null | sort > "$PRE_LIST" || true
fi

python3 scripts/kg_pack.py status
python3 scripts/kg_pack.py pack --pack-id "$PACK_ID" --description "$DESC"
python3 scripts/kg_pack.py validate --pack-id "$PACK_ID"
python3 scripts/kg_pack.py eval --pack-id "$PACK_ID"

if [ "$DRY_RUN" = "1" ]; then
  cp "$PRE_CFG" kg_config.json
  rm -f "$PRE_CFG"
  rm -rf "kg_packs/$PACK_ID"
  ls -1 kg_config.json.bak.* 2>/dev/null | sort > "$POST_LIST" || true
  comm -13 "$PRE_LIST" "$POST_LIST" | xargs -I{} rm -f "{}" || true
  rm -f "$PRE_LIST" "$POST_LIST"
  echo "[KG_RELEASE] DRY_RUN cleanup done; no activate performed"
  python3 scripts/kg_pack.py status
  exit 0
fi

python3 scripts/kg_pack.py activate --pack-id "$PACK_ID" --smoke
python3 scripts/kg_pack.py status

echo "[KG_RELEASE] DONE. active_pack is now: $PACK_ID"
echo "[KG_RELEASE] report: build/kg_pack_eval.json"
