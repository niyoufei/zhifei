#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_SCRIPT="${DOCGEN_RUNTIME_REPORT_SCRIPT:-$ROOT/scripts/report_docgen_runtime_health.sh}"
SUMMARY_ONLY="${DOCGEN_RUNTIME_SUMMARY_ONLY:-1}"

exec env ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY="$SUMMARY_ONLY" bash "$TARGET_SCRIPT" "$@"
