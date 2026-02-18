#!/usr/bin/env python3
"""
Unattended batch autoplan runner (polling-based).

Workflow (per project folder):
1) Detect stable folder in projects/inbox/
2) Move to projects/work/
3) Parse tender + BoQ (Actions endpoints)
4) Ingest all docs with project_id (ingest endpoint)
5) Generate DOCX (Actions generate_async)
6) Download artifacts + write summary
7) Move to projects/done/ or projects/failed/

This script is designed to run under launchd as a daemon.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import uuid
import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str):
    print(f"[{_now()}] {msg}", flush=True)


def _safe_name(s: str, limit: int = 60) -> str:
    out = re.sub(r"[^A-Za-z0-9_\\-\\u4e00-\\u9fff]+", "_", (s or "").strip())
    out = out.strip("_")
    return (out[:limit] or "project").strip("_")


def _iter_files(root: Path) -> list[Path]:
    exts = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".dxf", ".dwg", ".txt", ".md"}
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if any(seg in {"_output", "output", "__pycache__"} for seg in p.parts):
            continue
        if p.suffix.lower() not in exts:
            continue
        out.append(p)
    return out


def _max_mtime(paths: Iterable[Path]) -> float:
    m = 0.0
    for p in paths:
        try:
            mt = float(p.stat().st_mtime)
            if mt > m:
                m = mt
        except Exception:
            continue
    return m


def _is_stable_folder(folder: Path, stable_sec: int) -> bool:
    files = _iter_files(folder)
    if not files:
        return False
    newest = _max_mtime(files)
    return (time.time() - newest) >= float(max(1, int(stable_sec)))


@dataclass
class ProjectFiles:
    tender: list[Path]
    boq: Path | None
    logo: Path | None
    all_docs: list[Path]


def _pick_project_files(folder: Path) -> ProjectFiles:
    files = _iter_files(folder)
    tender_keys = ("招标", "招標", "tender", "投标", "招标文件", "招标书", "补遗", "澄清", "答疑")
    boq_keys = ("清单", "工程量清单", "boq", "报价", "计价")
    logo_keys = ("logo", "标志", "标识", "徽标")

    tender = [p for p in files if any(k.lower() in p.name.lower() for k in tender_keys)]
    boq_candidates = [p for p in files if any(k.lower() in p.name.lower() for k in boq_keys)]
    logo_candidates = [p for p in files if any(k.lower() in p.name.lower() for k in logo_keys)]

    # Prefer PDF/DOCX for tender
    tender_sorted = sorted(
        tender,
        key=lambda p: (0 if p.suffix.lower() in {".pdf", ".docx", ".doc"} else 1, -p.stat().st_size),
    )
    tender_final = tender_sorted[:6]

    # Prefer Excel for BoQ, then PDF; pick the largest among candidates.
    boq_final = None
    if boq_candidates:
        boq_sorted = sorted(
            boq_candidates,
            key=lambda p: (0 if p.suffix.lower() in {".xlsx", ".xls"} else 1, -p.stat().st_size),
        )
        boq_final = boq_sorted[0]

    logo_final = None
    if logo_candidates:
        logo_sorted = sorted(logo_candidates, key=lambda p: -p.stat().st_size)
        logo_final = logo_sorted[0]

    # If tender not detected, fall back to top-level PDFs (best-effort).
    if not tender_final:
        pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
        tender_final = sorted(pdfs, key=lambda p: -p.stat().st_size)[:2]

    return ProjectFiles(tender=tender_final, boq=boq_final, logo=logo_final, all_docs=files)


def _read_project_config(folder: Path) -> dict:
    cfg = folder / "project.json"
    if not cfg.exists():
        return {}
    try:
        obj = json.loads(cfg.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _hdr(actions_key: str) -> dict:
    return {"X-Actions-Key": actions_key}


def _post_files(
    base: str,
    path: str,
    actions_key: str,
    field: str,
    file_paths: list[str],
    timeout: int,
    params: dict | None = None,
) -> dict:
    url = base + path
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


def _ingest_files(base: str, project_id: str, file_paths: list[str], timeout: int) -> dict:
    url = base + "/ingest/upload"
    files = []
    handles = []
    try:
        for p in file_paths:
            fp = Path(p)
            f = fp.open("rb")
            handles.append(f)
            files.append(("files", (fp.name, f, "application/octet-stream")))
        r = requests.post(url, params={"project_id": project_id}, files=files, timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"POST /ingest/upload failed: {r.status_code} {r.text[:500]}")
        return r.json()
    finally:
        for h in handles:
            try:
                h.close()
            except Exception:
                pass


def _post_json(base: str, path: str, actions_key: str, payload: dict, timeout: int, params: dict | None = None) -> dict:
    url = base + path
    r = requests.post(
        url,
        headers={**_hdr(actions_key), "Content-Type": "application/json"},
        params=params or {},
        json=payload,
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"POST {path} failed: {r.status_code} {r.text[:500]}")
    return r.json()


def _get_json(base: str, path: str, actions_key: str, params: dict | None = None, timeout: int = 60) -> dict:
    url = base + path
    r = requests.get(url, headers=_hdr(actions_key), params=params or {}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"GET {path} failed: {r.status_code} {r.text[:500]}")
    return r.json()


def _download(base: str, actions_key: str, job_id: str, kind: str, variant: int, out_path: Path, timeout: int):
    url = base + "/actions/download"
    r = requests.get(url, headers=_hdr(actions_key), params={"job_id": job_id, "kind": kind, "variant": variant}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"GET /actions/download failed: {r.status_code} {r.text[:500]}")
    out_path.write_bytes(r.content)


def _check_quality(qc: dict) -> tuple[bool, list[str]]:
    hard_keys = [
        "structure",
        "officialese",
        "risk_triplet",
        "qse_closed_loop",
        "logic_template_adherence",
        "chapter_blueprint_adherence",
        "variant_diversity",
        "quantitative",
        "required_topics_detail",
        "evidence_traceability",
        "drawing_evidence",
        "standard_evidence",
        "boq_focus_item_typed_evidence",
    ]
    failed = []
    for k in hard_keys:
        item = qc.get(k) or {}
        if item.get("ok") is False:
            failed.append(k)
    return (len(failed) == 0), failed


def _process_one_project(base_url: str, actions_key: str, work_dir: Path, out_dir: Path, project_id: str) -> dict:
    cfg = _read_project_config(work_dir)
    topic = str(cfg.get("topic") or work_dir.name).strip() or "未命名项目"

    files = _pick_project_files(work_dir)
    if not files.tender:
        raise RuntimeError("no tender files detected")
    if not files.boq:
        raise RuntimeError("no BoQ file detected")

    # 1) tender parse
    _log(f"[{project_id}] tender parse: {len(files.tender)} file(s)")
    _post_files(
        base_url,
        "/actions/tender/parse",
        actions_key,
        "files",
        [str(p) for p in files.tender],
        timeout=600,
        params={"project_id": project_id},
    )

    # 2) boq parse
    _log(f"[{project_id}] boq parse: 1 file")
    _post_files(
        base_url,
        "/actions/boq/parse",
        actions_key,
        "file",
        [str(files.boq)],
        timeout=600,
        params={"project_id": project_id},
    )

    # 3) ingest docs (includes drawings/standards)
    ingest_paths = [str(p) for p in files.all_docs if p.name != "project.json"]
    _log(f"[{project_id}] ingest: {len(ingest_paths)} file(s)")
    _ingest_files(base_url, project_id, ingest_paths, timeout=900)

    # 3.5) optional plan overrides (outline/style/chapter_pages/etc), stored by project_id
    # This lets one project tune page counts, fonts, per-chapter requirements without changing code.
    plan_payload = None
    plan_file = work_dir / "plan.json"
    if plan_file.exists():
        try:
            obj = json.loads(plan_file.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(obj, dict):
                plan_payload = obj
        except Exception:
            plan_payload = None
    if plan_payload is None and isinstance(cfg.get("plan"), dict):
        plan_payload = cfg.get("plan")
    # Backward-compatible: allow plan fields at top-level of project.json
    if plan_payload is None:
        keys = (
            "outline",
            "style",
            "variants",
            "chapter_requirements",
            "chapter_pages",
            "quality_strict",
            "auto_remediate",
            "remediate_mode",
            "compare_mode",
            "compare_max_chars",
            "compare_titles",
        )
        has_any = any(k in cfg for k in keys)
        if has_any:
            plan_payload = {k: cfg.get(k) for k in keys if k in cfg}

    if isinstance(plan_payload, dict) and plan_payload:
        # Normalize required keys expected by /actions/plan/save
        plan_payload.setdefault("outline", [])
        plan_payload.setdefault("style", {})
        plan_payload.setdefault("variants", int(cfg.get("variants") or plan_payload.get("variants") or 1))
        plan_payload.setdefault("chapter_requirements", {})
        plan_payload.setdefault("chapter_pages", {})
        plan_payload.setdefault("quality_strict", True)
        plan_payload.setdefault("auto_remediate", True)
        plan_payload.setdefault("remediate_mode", str(plan_payload.get("remediate_mode") or "template"))
        plan_payload.setdefault("compare_mode", str(plan_payload.get("compare_mode") or "summary"))
        plan_payload.setdefault("compare_max_chars", int(plan_payload.get("compare_max_chars") or 1200))
        _log(f"[{project_id}] plan/save (overrides)")
        _post_json(
            base_url,
            "/actions/plan/save",
            actions_key,
            plan_payload,
            timeout=120,
            params={"project_id": project_id},
        )

    # 4) generate async
    gen = {
        "topic": topic,
        "project_id": project_id,
        "variants": int(cfg.get("variants") or 1),
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": str(cfg.get("remediate_mode") or "template"),
        "compare_mode": "summary",
        "compare_max_chars": 1200,
        "generate_images": bool(cfg.get("generate_images", True)),
    }
    if isinstance(cfg.get("requirements"), list) and cfg.get("requirements"):
        gen["requirements"] = [str(x).strip() for x in cfg.get("requirements") if str(x).strip()]
    if isinstance(cfg.get("params_override"), dict) and cfg.get("params_override"):
        gen["params_override"] = cfg.get("params_override")
    # Optional overrides
    for k in ("provider", "model", "api_key", "base_url", "secret_key", "token_url"):
        if cfg.get(k):
            gen[k] = cfg.get(k)
    for k in ("image_provider", "image_model", "image_aspect_ratio", "image_api_key", "bidder_company", "bidder_domain", "logo_url"):
        if cfg.get(k):
            gen[k] = cfg.get(k)

    _log(f"[{project_id}] generate_async")
    ret = _post_json(base_url, "/actions/generate_async", actions_key, gen, timeout=120)
    job_id = str(ret.get("job_id") or "")
    if not job_id:
        raise RuntimeError("generate_async missing job_id")

    # poll
    _log(f"[{project_id}] poll job: {job_id}")
    deadline = time.time() + int(cfg.get("timeout_sec") or 1800)
    status = ""
    while time.time() < deadline:
        js = _get_json(base_url, "/actions/job_status", actions_key, params={"job_id": job_id}, timeout=60)
        job = js.get("job") or {}
        status = str(job.get("status") or "")
        if status in ("done", "failed"):
            break
        time.sleep(float(cfg.get("poll_sec") or 2.0))
    if status != "done":
        raise RuntimeError(f"job not done: status={status}")

    out_dir.mkdir(parents=True, exist_ok=True)
    variants = max(1, int(gen.get("variants") or 1))
    json_path = out_dir / f"autoplan_{project_id}.json"
    _download(base_url, actions_key, job_id, "json", 1, json_path, timeout=600)

    data = {}
    variants_data = []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
        variants_data = data.get("variants") or []
        variants_data = variants_data if isinstance(variants_data, list) else []
    except Exception:
        variants_data = []

    by_variant = []
    failed_union: set[str] = set()
    for v in range(1, variants + 1):
        rec = {}
        if variants_data:
            rec = variants_data[v - 1] if v <= len(variants_data) else variants_data[0]
        qc = rec.get("quality_checks") if isinstance(rec, dict) else {}
        qc = qc if isinstance(qc, dict) else {}
        ok_v, failed_v = _check_quality(qc)
        for k in failed_v:
            failed_union.add(k)

        lt_gen = (rec.get("logic_templates") or {}).get("general") if isinstance(rec, dict) else None
        lt_qse = (rec.get("logic_templates") or {}).get("qse") if isinstance(rec, dict) else None
        lt_gen = lt_gen if isinstance(lt_gen, dict) else (rec.get("logic_template") if isinstance(rec.get("logic_template"), dict) else {})
        lt_qse = lt_qse if isinstance(lt_qse, dict) else {}

        _download(base_url, actions_key, job_id, "docx", v, out_dir / f"autoplan_{project_id}_v{v}.docx", timeout=600)
        _download(base_url, actions_key, job_id, "compare_docx", v, out_dir / f"autoplan_{project_id}_compare_v{v}.docx", timeout=600)
        try:
            _download(base_url, actions_key, job_id, "focus_xlsx", v, out_dir / f"autoplan_{project_id}_focus_v{v}.xlsx", timeout=600)
        except Exception:
            pass

        by_variant.append(
            {
                "variant": v,
                "ok": bool(ok_v),
                "failed_gates": failed_v,
                "logic_templates": {
                    "general": {"id": str((lt_gen or {}).get("id") or ""), "name": str((lt_gen or {}).get("name") or "")},
                    "qse": {"id": str((lt_qse or {}).get("id") or ""), "name": str((lt_qse or {}).get("name") or "")},
                },
                "quality": {k: (qc.get(k) or {}).get("ok") for k in ("structure", "officialese", "risk_triplet", "qse_closed_loop", "logic_template_adherence", "chapter_blueprint_adherence", "variant_diversity", "quantitative", "required_topics_detail", "evidence_traceability", "drawing_evidence", "standard_evidence", "boq_focus_item_typed_evidence")},
                "files": {
                    "docx": str(out_dir / f"autoplan_{project_id}_v{v}.docx"),
                    "compare_docx": str(out_dir / f"autoplan_{project_id}_compare_v{v}.docx"),
                    "focus_xlsx": str(out_dir / f"autoplan_{project_id}_focus_v{v}.xlsx"),
                },
            }
        )

    summary = {
        "ok": all(bool(x.get("ok")) for x in by_variant) if by_variant else False,
        "failed_gates": sorted(failed_union),
        "project_id": project_id,
        "topic": topic,
        "job_id": job_id,
        "generated_at": _now(),
        "variants": variants,
        "by_variant": by_variant,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Unattended batch autoplan runner (polling-based).")
    ap.add_argument(
        "--once",
        action="store_true",
        help="Run one polling cycle then exit (useful for debugging without launchd).",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    watch_root = Path(os.environ.get("ZF_WATCH_ROOT") or (root / "projects"))
    inbox = watch_root / "inbox"
    work = watch_root / "work"
    done = watch_root / "done"
    failed = watch_root / "failed"
    for d in (inbox, work, done, failed):
        d.mkdir(parents=True, exist_ok=True)

    host = os.environ.get("ZF_HOST") or "127.0.0.1"
    port = os.environ.get("ZF_PORT") or "8000"
    base_url = (os.environ.get("ZF_BACKEND_BASE_URL") or f"http://{host}:{port}").rstrip("/")
    actions_key = (os.environ.get("ZF_ACTIONS_KEY") or "").strip()
    if not actions_key:
        _log("[FAIL] missing ZF_ACTIONS_KEY")
        return 2

    poll_sec = float(os.environ.get("ZF_WATCH_POLL_SEC") or 3.0)
    stable_sec = int(os.environ.get("ZF_WATCH_STABLE_SEC") or 15)
    once = bool(args.once) or bool(str(os.environ.get("ZF_WATCH_ONCE") or "").strip())

    _log(f"watch_root={watch_root}")
    _log(f"base_url={base_url}")
    _log("watcher started" + (" (once mode)" if once else ""))

    while True:
        try:
            projects = [p for p in inbox.iterdir() if p.is_dir() and not p.name.startswith(".")]
        except Exception:
            projects = []

        for p in sorted(projects, key=lambda x: x.name):
            try:
                if not _is_stable_folder(p, stable_sec=stable_sec):
                    continue
                # Move into work (atomic)
                dst = work / p.name
                if dst.exists():
                    # Avoid collision
                    dst = work / f"{p.name}_{uuid.uuid4().hex[:6]}"
                shutil.move(str(p), str(dst))

                # Allow a stable project_id from project.json for repeated reruns / stable branding/plan binding.
                cfg = _read_project_config(dst)
                cfg_pid = str((cfg or {}).get("project_id") or "").strip()
                if cfg_pid:
                    proj_id = _safe_name(cfg_pid, limit=80)
                else:
                    proj_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6] + "_" + _safe_name(dst.name)
                out_dir = dst / "_output"
                _log(f"[{proj_id}] start: {dst}")
                summary = _process_one_project(base_url, actions_key, dst, out_dir, proj_id)
                # Move to done/failed
                target_base = done if summary.get("ok") else failed
                final = target_base / dst.name
                if final.exists():
                    final = target_base / f"{dst.name}_{uuid.uuid4().hex[:6]}"
                shutil.move(str(dst), str(final))
                _log(f"[{proj_id}] completed: ok={summary.get('ok')} -> {final}")
            except Exception as e:
                try:
                    _log(f"[ERROR] {p}: {repr(e)}")
                except Exception:
                    pass
                # best-effort move to failed
                try:
                    if p.exists() and p.parent == inbox:
                        bad = failed / p.name
                        if bad.exists():
                            bad = failed / f"{p.name}_{uuid.uuid4().hex[:6]}"
                        shutil.move(str(p), str(bad))
                except Exception:
                    pass

        if once:
            _log("watcher once mode: exit")
            return 0

        time.sleep(max(0.5, poll_sec))


if __name__ == "__main__":
    raise SystemExit(main())
