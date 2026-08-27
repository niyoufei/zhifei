#!/usr/bin/env python3
"""
End-to-end runner for Custom GPT Actions Bridge.

It does:
1) (optional) parse tender files -> /actions/tender/parse
2) (optional) parse BoQ file      -> /actions/boq/parse
3) (optional) ingest extra docs   -> /ingest/upload
4) (optional) save plan defaults  -> /actions/plan/save
5) generate (async)              -> /actions/generate_async
6) poll status                   -> /actions/job_status
7) read quality + files          -> /actions/result
8) download artifacts            -> /actions/download
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


_SENSITIVE_GENERATION_FIELDS = {
    "api_key",
    "base_url",
    "secret_key",
    "token_url",
    "image_api_key",
}

_SUCCESS_JOB_STATUSES = {"done", "succeeded"}
_TERMINAL_JOB_STATUSES = {
    *_SUCCESS_JOB_STATUSES,
    "failed",
    "cancelled",
    "interrupted_recoverable",
}


def _require_loopback_base_url(value: str) -> str:
    """Keep the Actions credential and project material on this Mac."""
    raw = str(value or "").strip().rstrip("/")
    try:
        parsed = urlparse(raw)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(
            "LOCAL_BACKEND_LOOPBACK_REQUIRED: 后端地址必须是本机 127.0.0.1"
        ) from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or port is None
        or not 1 <= port <= 65535
    ):
        raise ValueError(
            "LOCAL_BACKEND_LOOPBACK_REQUIRED: 后端地址必须是本机 127.0.0.1"
        )
    return f"http://127.0.0.1:{port}"


def _server_routed_generation_payload(payload: dict) -> dict:
    """Drop credentials and client-side provider routes before serialization."""
    return {
        key: value
        for key, value in dict(payload or {}).items()
        if key not in _SENSITIVE_GENERATION_FIELDS
        and key not in {"provider", "model", "image_provider", "image_model"}
    }


def _hdr(actions_key: str) -> dict:
    return {"X-Actions-Key": actions_key}


def _post_json(
    base: str,
    path: str,
    actions_key: str,
    payload: dict,
    *,
    params: dict | None = None,
    timeout: int = 120,
) -> dict:
    url = _require_loopback_base_url(base) + path
    wire_payload = (
        _server_routed_generation_payload(payload)
        if path in {"/actions/generate_async", "/actions/runs"}
        else dict(payload or {})
    )
    r = requests.post(
        url,
        headers={**_hdr(actions_key), "Content-Type": "application/json"},
        params=params or {},
        json=wire_payload,
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"POST {path} failed: {r.status_code} {r.text[:500]}")
    return r.json()


def _get_json(base: str, path: str, actions_key: str, params: dict | None = None, timeout: int = 60) -> dict:
    url = _require_loopback_base_url(base) + path
    r = requests.get(url, headers=_hdr(actions_key), params=params or {}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"GET {path} failed: {r.status_code} {r.text[:500]}")
    return r.json()


def _post_files(
    base: str,
    path: str,
    actions_key: str,
    field: str,
    file_paths: list[str],
    *,
    params: dict | None = None,
    timeout: int = 300,
) -> dict:
    url = _require_loopback_base_url(base) + path
    files = []
    handles = []
    try:
        for p in file_paths:
            fp = Path(p)
            f = fp.open("rb")
            handles.append(f)
            files.append((field, (fp.name, f, "application/octet-stream")))
        r = requests.post(url, headers=_hdr(actions_key), params=params or {}, files=files, timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} failed: {r.status_code} {r.text[:500]}")
        return r.json()
    finally:
        for h in handles:
            try:
                h.close()
            except Exception:
                pass


def _ingest_files(base: str, file_paths: list[str], *, project_id: str | None = None, timeout: int = 300) -> dict:
    url = _require_loopback_base_url(base) + "/ingest/upload"
    files = []
    handles = []
    try:
        for p in file_paths:
            fp = Path(p)
            f = fp.open("rb")
            handles.append(f)
            files.append(("files", (fp.name, f, "application/octet-stream")))
        params = {"project_id": project_id} if project_id else {}
        r = requests.post(url, params=params, files=files, timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"POST /ingest/upload failed: {r.status_code} {r.text[:500]}")
        return r.json()
    finally:
        for h in handles:
            try:
                h.close()
            except Exception:
                pass


def _download(base: str, actions_key: str, job_id: str, kind: str, variant: int, out_path: Path, timeout: int = 300):
    url = _require_loopback_base_url(base) + "/actions/download"
    r = requests.get(
        url,
        headers=_hdr(actions_key),
        params={"job_id": job_id, "kind": kind, "variant": variant},
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"GET /actions/download failed: {r.status_code} {r.text[:500]}")
    out_path.write_bytes(r.content)


def _print_quality(qc: dict):
    if not isinstance(qc, dict):
        print("[WARN] quality_checks missing or invalid")
        return
    keys = [
        "structure",
        "score_coverage",
        "closed_loop",
        "engineering",
        "risk_triplet",
        "qse_closed_loop",
        "logic_template_adherence",
        "chapter_blueprint_adherence",
        "variant_diversity",
        "quantitative",
        "vague_terms",
        "officialese",
        "consistency",
        "boq_focus_coverage",
        "boq_focus_item_closure",
        "boq_focus_item_typed_evidence",
        "required_topics",
        "required_topics_detail",
        "trade_names",
        "evidence",
        "evidence_quality",
        "evidence_traceability",
        "drawing_evidence",
        "standard_evidence",
        "template_style",
    ]
    print("\n[Quality Summary]")
    for k in keys:
        item = qc.get(k) or {}
        ok = item.get("ok")
        if ok is None:
            continue
        print(f"- {k}: {'PASS' if ok else 'FAIL'}")

    qse = qc.get("qse_closed_loop") or {}
    if isinstance(qse, dict) and qse.get("ok") is False:
        print("\n[QSE Closed Loop] (top 10)")
        for s in (qse.get("by_section") or [])[:10]:
            if not isinstance(s, dict) or s.get("ok"):
                continue
            title = s.get("title") or "章节"
            missing = ",".join([str(x) for x in (s.get("missing") or []) if str(x).strip()])
            cc = s.get("closed_card_count")
            tc = s.get("target_cards")
            print(f"- {title}: closed_cards={cc}/{tc} missing={missing}")

    adh = qc.get("logic_template_adherence") or {}
    if isinstance(adh, dict) and adh.get("ok") is False:
        print("\n[Logic Template Adherence] (top 10)")
        for s in (adh.get("by_section") or [])[:10]:
            if not isinstance(s, dict) or s.get("ok"):
                continue
            title = s.get("title") or "章节"
            tid = s.get("template_id") or ""
            dom = s.get("chapter_domain") or ""
            missing = ",".join([str(x) for x in (s.get("missing") or []) if str(x).strip()])
            print(f"- {title}: template={tid} domain={dom} missing={missing}")
    issues = qc.get("issue_list") or []
    if issues:
        print("\n[Issue List] (top 20)")
        for it in issues[:20]:
            sev = it.get("severity") or "medium"
            title = it.get("title") or "章节"
            typ = it.get("type") or "issue"
            prob = it.get("problem") or ""
            sugg = it.get("suggestion") or ""
            print(f"- [{sev}] {title} / {typ}: {prob} | {sugg}")
    recs = qc.get("auto_revision_suggestions") or []
    if recs:
        print("\n[Auto Revision Suggestions] (top 20)")
        for r in recs[:20]:
            title = r.get("title") or "章节"
            typ = r.get("type") or "issue"
            sugg = r.get("suggestion") or ""
            print(f"- {title} / {typ}: {sugg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8010", help="Backend base URL")
    ap.add_argument("--actions-key", default=os.environ.get("ZF_ACTIONS_KEY", ""), help="X-Actions-Key (or set env ZF_ACTIONS_KEY)")
    ap.add_argument("--topic", required=True, help="Project topic")
    ap.add_argument("--project-id", default="", help="Optional project_id for per-project storage/evidence scoping")
    ap.add_argument("--tender", action="append", default=[], help="Tender file path (repeatable)")
    ap.add_argument("--boq", default="", help="BoQ file path (xlsx/xls/pdf)")
    ap.add_argument("--ingest", action="append", default=[], help="Extra doc path to ingest for evidence (repeatable)")
    ap.add_argument("--plan-json", default="", help="Plan JSON file to POST /actions/plan/save")
    ap.add_argument("--outline", action="append", default=[], help="Override outline for this run (repeatable)")
    ap.add_argument("--requirements", action="append", default=[], help="Extra requirements (repeatable)")
    ap.add_argument("--variants", type=int, default=1, help="Number of variants")
    ap.add_argument("--quality-strict", action="store_true", default=True, help="Enable strict quality checks")
    ap.add_argument("--no-quality-strict", dest="quality_strict", action="store_false", help="Disable strict quality checks")
    ap.add_argument("--auto-remediate", action="store_true", default=True, help="Enable auto remediation")
    ap.add_argument("--no-auto-remediate", dest="auto_remediate", action="store_false", help="Disable auto remediation")
    ap.add_argument("--remediate-mode", default="template", choices=["template", "llm"], help="Remediation mode")
    ap.add_argument("--dry-run", action="store_true", default=False, help="Do not call external LLMs (will use fallback template)")
    ap.add_argument(
        "--generate-images",
        action="store_true",
        default=False,
        help="Generate optional document images (disabled by default for bounded validation runs)",
    )
    ap.add_argument("--no-gate", action="store_true", default=False, help="Do not fail the process even if quality gate fails")
    ap.add_argument("--timeout-sec", type=int, default=900, help="Polling timeout seconds")
    ap.add_argument("--poll-sec", type=float, default=2.0, help="Polling interval seconds")
    ap.add_argument("--download", action="store_true", default=True, help="Download artifacts to build/actions_runs/<job_id>/")
    ap.add_argument("--no-download", dest="download", action="store_false", help="Do not download artifacts")
    # Retained only so old invocations fail safely instead of silently changing
    # meaning.  Provider routing and credentials are server-owned and these
    # values are never serialized.
    ap.add_argument("--provider", default="", help=argparse.SUPPRESS)
    ap.add_argument("--model", default="", help=argparse.SUPPRESS)
    ap.add_argument("--api-key", default="", help=argparse.SUPPRESS)
    args = ap.parse_args()

    try:
        base = _require_loopback_base_url(args.base_url)
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    if not args.actions_key.strip():
        print("[FAIL] missing actions key: set env ZF_ACTIONS_KEY or pass --actions-key", file=sys.stderr)
        return 2
    project_id = (args.project_id or "").strip() or None

    tender_matrix = None
    if args.tender:
        print(f"[1/8] tender parse: {len(args.tender)} file(s)")
        tr = _post_files(
            base,
            "/actions/tender/parse",
            args.actions_key,
            "files",
            args.tender,
            params={"project_id": project_id} if project_id else None,
        )
        if isinstance(tr, dict):
            tender_matrix = tr.get("matrix")

    if args.boq:
        print("[2/8] boq parse: 1 file")
        _post_files(
            base,
            "/actions/boq/parse",
            args.actions_key,
            "file",
            [args.boq],
            params={"project_id": project_id} if project_id else None,
        )

    if args.ingest:
        print(f"[3/8] ingest extra docs: {len(args.ingest)} file(s)")
        _ingest_files(base, args.ingest, project_id=project_id)

    if args.plan_json:
        print("[4/8] save plan defaults")
        payload = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
        _post_json(base, "/actions/plan/save", args.actions_key, payload, params={"project_id": project_id} if project_id else None)

    print("[5/8] generate async")
    outline = list(args.outline or [])
    if not outline and isinstance(tender_matrix, dict):
        auto = tender_matrix.get("outline")
        if isinstance(auto, list) and auto:
            outline = [str(x) for x in auto if str(x).strip()]
    gen = {
        "topic": args.topic,
        "project_id": project_id,
        "outline": outline,
        "requirements": args.requirements,
        "variants": max(1, int(args.variants or 1)),
        "quality_strict": bool(args.quality_strict),
        "auto_remediate": bool(args.auto_remediate),
        "remediate_mode": args.remediate_mode,
        "compare_mode": "summary",
        "compare_max_chars": 1200,
        "generate_images": bool(args.generate_images),
        "dry_run": bool(args.dry_run),
    }
    if args.provider or args.model or args.api_key:
        print("[WARN] 已忽略客户端模型路由或密钥；生成仅使用后端已准入供应商。")
    gen = _server_routed_generation_payload(gen)

    ret = _post_json(base, "/actions/generate_async", args.actions_key, gen)
    job_id = ret.get("job_id") or ""
    if not job_id:
        print("[FAIL] generate_async missing job_id", file=sys.stderr)
        return 2
    print(f"job_id={job_id}")

    print("[6/8] poll status")
    deadline = time.time() + int(args.timeout_sec)
    status = ""
    while time.time() < deadline:
        try:
            js = _get_json(base, "/actions/job_status", args.actions_key, params={"job_id": job_id})
        except Exception as e:
            # Backend may briefly restart/reset during long jobs; keep polling until timeout.
            print(f"[WARN] poll transient error: {e}")
            time.sleep(float(args.poll_sec))
            continue
        job = js.get("job") or {}
        status = str(job.get("status") or "").strip().lower()
        if status in _TERMINAL_JOB_STATUSES:
            break
        time.sleep(float(args.poll_sec))
    if status not in _SUCCESS_JOB_STATUSES:
        print(f"[FAIL] job not done: status={status}", file=sys.stderr)
        return 3

    print("[7/8] read result")
    rr = _get_json(base, "/actions/result", args.actions_key, params={"job_id": job_id, "variant": 1, "include_sections": False})
    qc = rr.get("quality_checks") or {}
    _print_quality(qc)

    if args.download:
        print("[8/8] download artifacts")
        out_dir = Path("build") / "actions_runs" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        # json
        _download(base, args.actions_key, job_id, "json", 1, out_dir / f"autoplan_{job_id}.json")
        # docx + compare_docx
        variants = int(args.variants or 1)
        for v in range(1, variants + 1):
            _download(base, args.actions_key, job_id, "docx", v, out_dir / f"autoplan_{job_id}_v{v}.docx")
            _download(base, args.actions_key, job_id, "compare_docx", v, out_dir / f"autoplan_{job_id}_compare_v{v}.docx")
            try:
                _download(base, args.actions_key, job_id, "focus_xlsx", v, out_dir / f"autoplan_{job_id}_focus_v{v}.xlsx")
            except Exception:
                pass
            try:
                _download(
                    base,
                    args.actions_key,
                    job_id,
                    "score_overview_xlsx",
                    v,
                    out_dir / f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{v}.xlsx",
                )
            except Exception:
                pass
            try:
                _download(
                    base,
                    args.actions_key,
                    job_id,
                    "expert_review_docx",
                    v,
                    out_dir / f"autoplan_{job_id}_专家复核提要版_v{v}.docx",
                )
            except Exception:
                pass
        print(f"saved_to={out_dir}")
        for v in range(1, variants + 1):
            p1 = out_dir / f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{v}.xlsx"
            p2 = out_dir / f"autoplan_{job_id}_专家复核提要版_v{v}.docx"
            if p1.exists():
                print(f"评分点覆盖与证据引用总览.xlsx={p1}")
            if p2.exists():
                print(f"专家复核提要版.docx={p2}")

    # simple gate
    hard_keys = [
        "structure",
        "officialese",
        "risk_triplet",
        "qse_closed_loop",
        "logic_template_adherence",
        "quantitative",
        "required_topics_detail",
        "evidence_traceability",
        "drawing_evidence",
        "standard_evidence",
        "boq_focus_item_typed_evidence",
    ]
    hard_fail = []
    for k in hard_keys:
        item = qc.get(k) or {}
        if item.get("ok") is False:
            hard_fail.append(k)
    if hard_fail and not args.no_gate:
        print(f"[FAIL] hard gate failed: {','.join(hard_fail)}", file=sys.stderr)
        return 10
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
