#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_postprocess.py (M11-ready)
- Accepts layout params and calls tools/export_layout_fix.py
- Updates build/export_audit_chain.json with audit trace
Usage:
  python backend/hooks/export_postprocess.py build/_demo.docx \
    --paper A4 --orientation auto --margins 20,20,20,25
  # add --no-pagebreak to disable H1 page breaks
"""
import subprocess, os, sys, json, argparse
from datetime import datetime

def optimize_layout(docx_path: str, paper: str, orientation: str, margins: str, auto_pagebreak: bool):
    out_path = docx_path.replace(".docx", ".print.docx")
    cmd = [
        sys.executable, "tools/export_layout_fix.py",
        "--in", docx_path,
        "--out", out_path,
        "--paper", paper,
        "--orientation", orientation,
        "--margins", margins
    ]
    if not auto_pagebreak:
        cmd.append("--no-pagebreak")
    subprocess.run(cmd, check=True)
    audit_file = out_path + ".layout.json"
    audit = None
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            audit = json.load(f)
    return {"optimized_file": out_path, "audit": audit}

def run(docx_path: str, paper: str, orientation: str, margins: str, auto_pagebreak: bool, meta_log: str = "build/export_audit_chain.json"):
    result = optimize_layout(docx_path, paper, orientation, margins, auto_pagebreak)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": os.path.abspath(docx_path),
        "output": os.path.abspath(result["optimized_file"]),
        "audit_trace": result["audit"]
    }
    os.makedirs(os.path.dirname(meta_log) or ".", exist_ok=True)
    data = {"chain": []}
    if os.path.exists(meta_log):
        with open(meta_log, "r", encoding="utf-8") as f:
            try: data = json.load(f) or {"chain": []}
            except Exception: data = {"chain": []}
    data["chain"].append(entry)
    with open(meta_log, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"🧩 Export audit chain updated -> {meta_log}")

def parse_args():
    ap = argparse.ArgumentParser(description="Post-export hook with parameterized layout.")
    ap.add_argument("docx_path", help="input .docx to optimize")
    ap.add_argument("--paper", default="A4", choices=["A4","Letter"])
    ap.add_argument("--orientation", default="auto", choices=["auto","portrait","landscape"])
    ap.add_argument("--margins", default="20,20,20,25", help="mm: top,right,bottom,left")
    ap.add_argument("--no-pagebreak", action="store_true", help="disable H1 page break rule")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run(args.docx_path, args.paper, args.orientation, args.margins, (not args.no_pagebreak))
