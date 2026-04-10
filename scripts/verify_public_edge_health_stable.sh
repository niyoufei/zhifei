#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_SCRIPT="${DOCGEN_EDGE_VERIFY_SCRIPT:-$ROOT/scripts/verify_public_edge_health.sh}"

exec env ZF_EDGE_PROFILE=stable bash "$TARGET_SCRIPT" "$@"
