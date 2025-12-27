#!/usr/bin/env bash
set -euo pipefail

# KG release pipeline (one-command)
# Steps:
# 1) pack snapshot from current active pack
# 2) validate the new pack
# 3) eval the new pack (baseline smoke -> candidate smoke -> diff report)
# 4) activate the new pack with --smoke and keep it active
#
# Usage:
#   ./scripts/kg_release.sh "description text"
# Optional:
#   PACK_ID=kgpack-YYYYMMDD_HHMMSS ./scripts/kg_release.sh "desc"
# Output:
#   - new pack under kg_packs/<pack_id>/
#   - evaluation report build/kg_pack_eval.json

DESC="${1:-snapshot release}"
PACK_ID="${PACK_ID:-kgpack-$(date +%Y%m%d_%H%M%S)}"

echo "[KG_RELEASE] pack_id=$PACK_ID"
echo "[KG_RELEASE] desc=$DESC"

python3 scripts/kg_pack.py status
python3 scripts/kg_pack.py pack --pack-id "$PACK_ID" --description "$DESC"
python3 scripts/kg_pack.py validate --pack-id "$PACK_ID"
python3 scripts/kg_pack.py eval --pack-id "$PACK_ID"
python3 scripts/kg_pack.py activate --pack-id "$PACK_ID" --smoke
python3 scripts/kg_pack.py status

echo "[KG_RELEASE] DONE. active_pack is now: $PACK_ID"
echo "[KG_RELEASE] report: build/kg_pack_eval.json"
