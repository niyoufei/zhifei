#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_finalize.py
- Finalize step for /export: generate Audit Trace Map (Excel + PDF)
- Idempotent: reads build/export_audit_chain.json and renders charts.
"""
import os, sys, subprocess

def main():
    # Reuse existing generator
    if not os.path.exists("tools/audit_trace_map.py"):
        print("ERROR: tools/audit_trace_map.py not found", file=sys.stderr); sys.exit(2)
    subprocess.run([sys.executable, "tools/audit_trace_map.py"], check=True)
    print("✅ Finalize done: audit_trace_map.xlsx/pdf updated.")

if __name__ == "__main__":
    main()
