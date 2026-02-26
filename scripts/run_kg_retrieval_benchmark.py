#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.v2.kg_retrieval_benchmark import (
    DEFAULT_DATASET_PATH,
    run_retrieval_benchmark,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Run KG retrieval benchmark and quality gate.")
    p.add_argument("--db-path", default="backend/data/autoplan/v2/knowledge_graph.sqlite3")
    p.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    p.add_argument("--out-json", default="build/KG_Retrieval_Benchmark.json")
    p.add_argument("--min-pass-rate", type=float, default=0.8)
    p.add_argument("--min-avg-mrr", type=float, default=0.55)
    args = p.parse_args()

    report = run_retrieval_benchmark(
        db_path=Path(args.db_path).expanduser().resolve(),
        dataset_path=Path(args.dataset).expanduser().resolve(),
        min_pass_rate=float(args.min_pass_rate),
        min_avg_mrr=float(args.min_avg_mrr),
    )
    out = Path(args.out_json).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok={bool(report.get('ok'))}")
    print(f"total_cases={int(report.get('total_cases') or 0)}")
    print(f"pass_rate={float(report.get('pass_rate') or 0.0):.4f}")
    print(f"avg_mrr={float(report.get('avg_mrr') or 0.0):.4f}")
    print(f"out_json={out}")
    return 0 if bool(report.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
