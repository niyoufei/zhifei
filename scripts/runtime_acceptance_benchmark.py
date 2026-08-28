#!/usr/bin/env python3
from __future__ import annotations

"""Isolated 34-file ingestion and health-latency acceptance benchmark."""

import argparse
import json
import statistics
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import requests


def _make_corpus(
    root: Path, *, file_count: int, total_bytes: int, corpus_nonce: str
) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    base, remainder = divmod(total_bytes, file_count)
    paths: list[Path] = []
    for index in range(file_count):
        size = base + (1 if index < remainder else 0)
        prefix = (
            "SYNTHETIC-NO-REAL-PROJECT-DATA "
            f"run={corpus_nonce} file={index + 1:02d}\n"
        ).encode("utf-8")
        if size <= len(prefix):
            raise ValueError("fixture size is too small")
        path = root / f"synthetic_tender_text_{index + 1:02d}.txt"
        filler = b"synthetic construction organization acceptance line\n" * 16384
        with path.open("wb") as handle:
            handle.write(prefix)
            remaining = size - len(prefix)
            while remaining:
                chunk = filler[: min(len(filler), remaining)]
                handle.write(chunk)
                remaining -= len(chunk)
        paths.append(path)
    return paths


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _run_ingest(
    base_url: str,
    paths: list[Path],
    workspace: Path,
    *,
    label: str,
) -> dict[str, Any]:
    stop = threading.Event()
    health_latencies: list[float] = []
    health_errors = 0

    def _sample_health() -> None:
        nonlocal health_errors
        while not stop.wait(0.1):
            started = time.perf_counter()
            try:
                response = requests.get(f"{base_url}/health", timeout=2)
                response.raise_for_status()
                health_latencies.append(time.perf_counter() - started)
            except Exception:
                health_errors += 1

    sampler = threading.Thread(target=_sample_health, daemon=True)
    sampler.start()
    handles = [path.open("rb") for path in paths]
    started = time.perf_counter()
    try:
        files = [
            ("files", (path.name, handle, "text/plain"))
            for path, handle in zip(paths, handles)
        ]
        response = requests.post(
            f"{base_url}/ingest/jobs",
            params={
                "project_id": "runtime-acceptance-synthetic",
                "source_hint": "drawing_standard",
                "workspace_dir": str(workspace),
            },
            files=files,
            timeout=900,
        )
        response.raise_for_status()
        created = response.json()
        accepted_at = time.perf_counter()
    finally:
        for handle in handles:
            handle.close()

    job_id = str(created.get("job_id") or "")
    if not job_id:
        raise RuntimeError("ingest benchmark did not receive job_id")
    terminal: dict[str, Any] = {}
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        status_response = requests.get(f"{base_url}/ingest/jobs/{job_id}", timeout=10)
        status_response.raise_for_status()
        terminal = status_response.json().get("job") or {}
        if str(terminal.get("status") or "") in {
            "succeeded",
            "failed",
            "cancelled",
            "interrupted_recoverable",
        }:
            break
        time.sleep(0.2)
    elapsed = time.perf_counter() - started
    upload_elapsed = accepted_at - started
    processing_elapsed = elapsed - upload_elapsed
    stop.set()
    sampler.join(timeout=2)
    result = terminal.get("result") if isinstance(terminal.get("result"), dict) else {}
    progress = terminal.get("progress") if isinstance(terminal.get("progress"), dict) else {}
    files_progress = progress.get("files") if isinstance(progress.get("files"), dict) else {}
    file_items = files_progress.get("items") if isinstance(files_progress.get("items"), list) else []
    file_durations = [
        float(item.get("elapsed_seconds") or 0.0)
        for item in file_items
        if isinstance(item, dict) and item.get("elapsed_seconds") is not None
    ]
    return {
        "label": label,
        "job_id": job_id,
        "status": terminal.get("status"),
        "elapsed_seconds": round(elapsed, 3),
        "upload_accept_seconds": round(upload_elapsed, 3),
        "processing_terminal_seconds": round(processing_elapsed, 3),
        "accepted": len(result.get("accepted") or []),
        "rejected": len(result.get("rejected") or []),
        "cache_hits": int(result.get("cache_hits") or 0),
        "health_samples": len(health_latencies),
        "health_errors": health_errors,
        "health_p50_seconds": round(statistics.median(health_latencies), 6)
        if health_latencies
        else None,
        "health_p95_seconds": round(_percentile(health_latencies, 0.95) or 0.0, 6)
        if health_latencies
        else None,
        "file_status_count": len(file_items),
        "file_elapsed_sum_seconds": round(sum(file_durations), 3),
        "file_elapsed_mean_seconds": round(statistics.mean(file_durations), 6)
        if file_durations
        else None,
        "file_elapsed_max_seconds": round(max(file_durations), 3) if file_durations else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18010")
    parser.add_argument("--files", type=int, default=34)
    parser.add_argument("--total-bytes", type=int, default=268_434_954)
    parser.add_argument("--output")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="zhifei-runtime-acceptance-") as temp_dir:
        root = Path(temp_dir)
        corpus_nonce = uuid.uuid4().hex
        paths = _make_corpus(
            root / "corpus",
            file_count=max(1, int(args.files)),
            total_bytes=max(1, int(args.total_bytes)),
            corpus_nonce=corpus_nonce,
        )
        first = _run_ingest(args.base_url.rstrip("/"), paths, root / "workspace-cold", label="cold")
        second = _run_ingest(args.base_url.rstrip("/"), paths, root / "workspace-warm", label="warm")

    report = {
        "schema_version": "runtime-ingest-benchmark-v1",
        "corpus_profile": "34 unique valid UTF-8 text files; synthetic content only; exact total bytes",
        "files": int(args.files),
        "total_bytes": int(args.total_bytes),
        "corpus_nonce": corpus_nonce,
        "runs": [first, second],
        "acceptance": {
            "cold_under_136_seconds": bool(first["status"] == "succeeded" and first["elapsed_seconds"] <= 136),
            "warm_under_30_seconds": bool(second["status"] == "succeeded" and second["elapsed_seconds"] <= 30),
            "health_p95_under_500ms": bool(
                max(float(first.get("health_p95_seconds") or 0), float(second.get("health_p95_seconds") or 0)) < 0.5
            ),
            "all_accepted": bool(first["accepted"] == int(args.files) and second["accepted"] == int(args.files)),
        },
    }
    report["ok"] = all(report["acceptance"].values())
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
