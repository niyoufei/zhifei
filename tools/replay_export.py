#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_export.py
- Reproduce a past export using parameters stored in build/export_audit_chain.json
- Usage:
    python3 tools/replay_export.py --index -1
    python3 tools/replay_export.py --index 3
Notes:
- It reads params: paper, orientation, margins, auto_pagebreak
- Calls backend/hooks/export_postprocess.py and backend/hooks/export_finalize.py
- Writes a small summary report to build/replay_summary.txt
"""
import os, sys, json, argparse, subprocess
from datetime import datetime

CHAIN = "build/export_audit_chain.json"
DOCX  = "build/_demo.docx"  # 这里沿用当前演示文档路径；实际系统可替换为你导出的主文档路径

def load_chain():
    if not os.path.exists(CHAIN):
        raise FileNotFoundError(f"Audit chain not found: {CHAIN}")
    with open(CHAIN, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    chain = data.get("chain", [])
    if not chain:
        raise ValueError("Audit chain is empty.")
    return chain

def pick_entry(chain, idx):
    if idx < 0:
        idx = len(chain) + idx
    if idx < 0 or idx >= len(chain):
        raise IndexError(f"Index out of range: {idx} (len={len(chain)})")
    return idx, chain[idx]

def run_postprocess(docx_path, params):
    hook = "backend/hooks/export_postprocess.py"
    if not os.path.exists(hook):
        raise FileNotFoundError(hook)
    paper = params.get("paper", "A4")
    orientation = params.get("orientation", "auto")
    margins = params.get("margins", "20,20,20,25")
    auto_pagebreak = params.get("auto_pagebreak", True)

    cmd = [sys.executable, hook, docx_path,
           "--paper", paper, "--orientation", orientation, "--margins", margins]
    if not auto_pagebreak:
        cmd.append("--no-pagebreak")
    subprocess.run(cmd, check=True)

def run_finalize():
    hook = "backend/hooks/export_finalize.py"
    if not os.path.exists(hook):
        raise FileNotFoundError(hook)
    subprocess.run([sys.executable, hook], check=True)

def write_summary(index, entry, replay_note):
    out = os.path.abspath("build/replay_summary.txt")
    with open(out, "a", encoding="utf-8") as f:
        f.write("\n==== REPLAY ====\n")
        f.write(f"time: {datetime.now().isoformat()}\n")
        f.write(f"from_index: {index}\n")
        f.write(f"source: {entry.get('source')}\n")
        f.write(f"output: {entry.get('output')}\n")
        f.write(f"params: {json.dumps(entry.get('params', {}), ensure_ascii=False)}\n")
        f.write(f"note: {replay_note}\n")
    print(f"📝 Replay summary -> {out}")

def main():
    ap = argparse.ArgumentParser(description="Replay a past export by index.")
    ap.add_argument("--index", type=int, default=-1, help="record index in export_audit_chain.json (default last)")
    args = ap.parse_args()

    chain = load_chain()
    idx, entry = pick_entry(chain, args.index)
    params = entry.get("params") or {}
    print(f"▶️ Replaying index {idx} with params: {params}")

    # 这里使用现有演示 DOCX；如果你有真实导出路径，可替换 DOCX 变量
    if not os.path.exists(DOCX):
        raise FileNotFoundError(f"Input DOCX not found: {DOCX}")

    run_postprocess(DOCX, params)
    run_finalize()
    write_summary(idx, entry, replay_note="replayed using stored params")

    print("✅ Replay completed.")

if __name__ == "__main__":
    main()
