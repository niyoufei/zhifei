#!/bin/bash
set -e
cd "$(dirname "$0")/.."
python3 scripts/smoke_e2e_v2.py
