#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_audit.py
Compare two export records (default: last vs previous) using their .layout.json decisions.
Outputs:
- build/diff_audit_report.json
- build/diff_audit_report.txt  (readable summary with PASS/FAIL)
Usage:
  python3 tools/diff_audit.py                # compare last two
  python3 tools/diff_audit.py --a -1 --b -2  # explicit (last vs prev)
  python3 tools/diff_audit.py --a 5  --b 2   # by index
"""
import os, json, argparse
from deepdiff import DeepDiff

CHAIN = "build/export_audit_chain.json"

def load_chain():
    if not os.path.exists(CHAIN):
        raise FileNotFoundError(f"No audit chain: {CHAIN}")
    with open(CHAIN, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    chain = data.get("chain", [])
    if len(chain) < 2:
        raise ValueError("Need at least two records to diff.")
    return chain

def pick(chain, idx):
    if idx < 0: idx = len(chain) + idx
    if idx < 0 or idx >= len(chain):
        raise IndexError(f"Index {idx} out of range (len={len(chain)})")
    return idx, chain[idx]

def layout_path(entry):
    out = entry.get("output") or ""
    return (out + ".layout.json")

def load_decisions(entry):
    path = layout_path(entry)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Layout audit not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        meta = json.load(f) or {}
    return meta.get("decisions", {}), path, meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=-1, help="index for record A (default last)")
    ap.add_argument("--b", type=int, default=-2, help="index for record B (default previous)")
    args = ap.parse_args()

    chain = load_chain()
    ia, A = pick(chain, args.a)
    ib, B = pick(chain, args.b)

    A_dec, A_path, A_meta = load_decisions(A)
    B_dec, B_path, B_meta = load_decisions(B)

    # Only diff the "decisions" object (paper/orientation/margins_mm/heading_rules/…)
    diff = DeepDiff(B_dec, A_dec, ignore_order=True)

    passed = (not diff)
    summary = {
        "passed": passed,
        "compare": {"A_index": ia, "A_layout": A_path,
                    "B_index": ib, "B_layout": B_path},
        "A_params": A.get("params"),
        "B_params": B.get("params"),
        "A_model": A_meta.get("tool"), "B_model": B_meta.get("tool"),
        "diff": diff.to_dict() if diff else {},
    }

    os.makedirs("build", exist_ok=True)
    with open("build/diff_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open("build/diff_audit_report.txt", "w", encoding="utf-8") as f:
        f.write("=== Diff Audit Report ===\n")
        f.write(f"A(index={ia}): {A_path}\n")
        f.write(f"B(index={ib}): {B_path}\n")
        f.write(f"Params(A): {json.dumps(summary['A_params'], ensure_ascii=False)}\n")
        f.write(f"Params(B): {json.dumps(summary['B_params'], ensure_ascii=False)}\n")
        f.write(f"\nRESULT: {'PASS (identical decisions)' if passed else 'FAIL (differences found)'}\n")
        if not passed:
            f.write("\nDIFF (B -> A):\n")
            f.write(json.dumps(summary["diff"], ensure_ascii=False, indent=2))
    print(f"{'✅' if passed else '❌'} Diff complete. See build/diff_audit_report.txt and .json")

if __name__ == "__main__":
    main()
