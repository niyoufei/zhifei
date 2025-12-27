#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG Pack Manager (pack-aware, rollback-safe)

Goals:
- Make KG upgrade replaceable: pack -> validate -> activate -> (optional smoke) -> rollback if needed
- Keep backward compatibility with existing kg_config.json layout

Key idea:
- kg_loader.py now supports active_pack/packs to switch BASE_DIR.
- This tool manages pack directories under: backend/kg_packs/<pack_id>/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "kg_config.json"
PACKS_DIR = ROOT_DIR / "kg_packs"

SKIP_KEYS = {
    "packs",
    "active_pack",
    "_active_pack_prev",
    "active_pack_history",
}

def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _load_cfg() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"[ERROR] kg_config.json not found: {CONFIG_PATH}")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise SystemExit("[ERROR] kg_config.json must be a JSON object")
    packs = cfg.get("packs")
    if packs is None:
        cfg["packs"] = {}
    elif not isinstance(packs, dict):
        raise SystemExit("[ERROR] kg_config.json: 'packs' exists but is not an object")
    if "active_pack" not in cfg:
        cfg["active_pack"] = "default"
    return cfg

def _write_cfg(cfg: Dict[str, Any], *, backup: bool = True) -> Optional[Path]:
    raw = CONFIG_PATH.read_text(encoding="utf-8") if CONFIG_PATH.exists() else "{}"
    bak_path: Optional[Path] = None
    if backup:
        bak_path = ROOT_DIR / f"kg_config.json.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        bak_path.write_text(raw, encoding="utf-8")
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return bak_path

def _pack_cfg(cfg: Dict[str, Any], pack_id: str) -> Dict[str, Any]:
    packs = cfg.get("packs", {})
    pcfg = packs.get(pack_id)
    if pcfg is None:
        return {}
    if not isinstance(pcfg, dict):
        raise SystemExit(f"[ERROR] packs[{pack_id}] must be an object")
    return pcfg

def _pack_base_dir(cfg: Dict[str, Any], pack_id: Optional[str] = None) -> Path:
    pid = pack_id or cfg.get("active_pack") or "default"
    pcfg = _pack_cfg(cfg, pid)
    base_dir = pcfg.get("base_dir") or pcfg.get("base_path") or pcfg.get("root") or "."
    base = (ROOT_DIR / str(base_dir)).resolve()
    if not base.exists():
        raise SystemExit(f"[ERROR] pack base_dir not found: pack={pid} base_dir={base}")
    return base

def _is_probably_path(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if s.startswith("http://") or s.startswith("https://"):
        return False
    # common relative path hints
    if "/" in s or "\\" in s:
        return True
    if s.endswith((".json", ".yaml", ".yml", ".txt", ".md")):
        return True
    return False

def _collect_existing_relpaths(cfg: Dict[str, Any], base_dir: Path) -> List[str]:
    found: Set[str] = set()

    def add_candidate(val: str) -> None:
        v = (val or "").strip()
        if not _is_probably_path(v):
            return
        p = Path(v)
        if p.is_absolute():
            # Only accept absolute paths that are under base_dir (for safety)
            try:
                rel = p.resolve().relative_to(base_dir.resolve())
            except Exception:
                return
            rel_s = rel.as_posix()
        else:
            rel_s = p.as_posix()
        if (base_dir / rel_s).exists():
            found.add(rel_s)

    def walk(obj: Any, key: Optional[str] = None) -> None:
        if key in SKIP_KEYS:
            return
        if isinstance(obj, str):
            add_candidate(obj)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, k)

    for k, v in cfg.items():
        walk(v, k)

    # Ensure stable ordering
    return sorted(found)

def _copy_any(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

def _build_manifest(pack_dir: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    total_bytes = 0
    for f in sorted(pack_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(pack_dir).as_posix()
        if rel == "manifest.json":
            continue
        size = f.stat().st_size
        total_bytes += size
        entries.append(
            {
                "path": rel,
                "size": size,
                "sha256": _sha256_file(f),
            }
        )
    manifest = {
        "schema_version": 1,
        "created_at": _now_iso(),
        **meta,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }
    return manifest

def _validate_pack_by_manifest(pack_dir: Path) -> Tuple[bool, List[str]]:
    problems: List[str] = []
    mpath = pack_dir / "manifest.json"
    if not mpath.exists():
        problems.append(f"manifest.json missing: {mpath}")
        return False, problems
    try:
        man = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception as e:
        problems.append(f"manifest.json invalid JSON: {e}")
        return False, problems

    files = man.get("files", [])
    if not isinstance(files, list) or not files:
        problems.append("manifest.json: 'files' missing or empty")
        return False, problems

    for it in files:
        if not isinstance(it, dict):
            problems.append("manifest.json: files[] item is not object")
            continue
        rel = it.get("path")
        sha = it.get("sha256")
        if not rel or not sha:
            problems.append("manifest.json: files[] missing path/sha256")
            continue
        fp = pack_dir / rel
        if not fp.exists():
            problems.append(f"missing file: {rel}")
            continue
        try:
            actual = _sha256_file(fp)
            if actual != sha:
                problems.append(f"sha256 mismatch: {rel}")
        except Exception as e:
            problems.append(f"hash error: {rel}: {e}")

    return (len(problems) == 0), problems

def cmd_status(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    active = cfg.get("active_pack", "default")
    packs = cfg.get("packs", {})
    print("[INFO] root_dir:", ROOT_DIR)
    print("[INFO] kg_config:", CONFIG_PATH)
    print("[INFO] active_pack:", active)
    try:
        base = _pack_base_dir(cfg, active)
        print("[INFO] active_pack.base_dir:", base)
    except SystemExit as e:
        print(str(e))
    print("[INFO] packs:", sorted(list(packs.keys())))
    return 0

def cmd_list(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    packs = cfg.get("packs", {})
    active = cfg.get("active_pack", "default")
    for pid in sorted(packs.keys()):
        pcfg = _pack_cfg(cfg, pid)
        bd = pcfg.get("base_dir", ".")
        mark = "*" if pid == active else " "
        print(f"{mark} {pid}\tbase_dir={bd}")
    return 0

def cmd_validate(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    pid = args.pack_id or cfg.get("active_pack") or "default"

    # Determine base_dir from config if registered; else assume kg_packs/<pid>
    packs = cfg.get("packs", {})
    if pid not in packs:
        guess = PACKS_DIR / pid
        base_dir = guess.resolve()
        if not base_dir.exists():
            raise SystemExit(f"[ERROR] pack not registered and directory not found: {pid}")
    else:
        base_dir = _pack_base_dir(cfg, pid)

    print("[INFO] validating pack:", pid)
    print("[INFO] base_dir:", base_dir)

    # 1) config-path existence check under base_dir
    rels = _collect_existing_relpaths(cfg, base_dir)
    missing_cfg_assets = []
    for rel in rels:
        if not (base_dir / rel).exists():
            missing_cfg_assets.append(rel)
    if missing_cfg_assets:
        print("[ERROR] missing config-referenced assets in this pack:")
        for x in missing_cfg_assets[:200]:
            print(" -", x)
        return 2
    print("[OK] config-referenced assets present:", len(rels))

    # 2) manifest validation if present (optional for root-layout packs)
    m = base_dir / "manifest.json"
    if m.exists():
        ok, problems = _validate_pack_by_manifest(base_dir)
        if not ok:
            print("[ERROR] manifest validation failed:")
            for p in problems[:200]:
                print(" -", p)
            return 2
        print("[OK] manifest validated")
    else:
        print("[WARN] manifest.json not found; skipped hash validation (allowed for root-layout packs)")

    return 0

def _sanitize_pack_id(pid: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", pid):
        raise SystemExit("[ERROR] pack_id must match: [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return pid

def cmd_pack(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    pack_id = _sanitize_pack_id(args.pack_id)
    src_pack = args.from_pack or (cfg.get("active_pack") or "default")

    src_base = _pack_base_dir(cfg, src_pack)
    dst_dir = (PACKS_DIR / pack_id).resolve()

    if dst_dir.exists():
        if not args.force:
            raise SystemExit(f"[ERROR] pack directory exists (use --force to overwrite): {dst_dir}")
        shutil.rmtree(dst_dir)

    dst_dir.mkdir(parents=True, exist_ok=True)

    rels = _collect_existing_relpaths(cfg, src_base)
    if not rels:
        raise SystemExit("[ERROR] no existing asset paths found from kg_config.json; aborting")

    # Copy assets preserving relative paths
    for rel in rels:
        s = src_base / rel
        d = dst_dir / rel
        _copy_any(s, d)

    meta = {
        "pack_id": pack_id,
        "pack_version": args.pack_version or pack_id,
        "description": args.description or "",
        "source_pack": src_pack,
    }
    manifest = _build_manifest(dst_dir, meta)
    (dst_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Register in kg_config.json
    packs = cfg.get("packs", {})
    packs[pack_id] = {
        "base_dir": f"kg_packs/{pack_id}",
        "pack_version": meta["pack_version"],
        "schema_version": 1,
        "created_at": _now_iso(),
        "manifest": f"kg_packs/{pack_id}/manifest.json",
    }
    cfg["packs"] = packs
    bak = _write_cfg(cfg, backup=True)

    print("[OK] packed:", pack_id)
    print("[INFO] src_pack:", src_pack, "src_base:", src_base)
    print("[INFO] dst_dir:", dst_dir)
    print("[INFO] assets_copied:", len(rels))
    print("[INFO] registered in kg_config.json; backup:", bak.name if bak else "(none)")
    return 0

def cmd_activate(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    pack_id = _sanitize_pack_id(args.pack_id)

    # Auto-register if directory exists but config missing
    packs = cfg.get("packs", {})
    if pack_id not in packs:
        guess = (PACKS_DIR / pack_id).resolve()
        if not guess.exists():
            raise SystemExit(f"[ERROR] pack not found: {pack_id} (not in config and no dir {guess})")
        packs[pack_id] = {
            "base_dir": f"kg_packs/{pack_id}",
            "pack_version": pack_id,
            "schema_version": 1,
            "created_at": _now_iso(),
            "manifest": f"kg_packs/{pack_id}/manifest.json" if (guess / "manifest.json").exists() else "",
        }
        cfg["packs"] = packs

    # Validate before switching
    vcode = cmd_validate(argparse.Namespace(pack_id=pack_id))
    if vcode != 0:
        raise SystemExit("[ERROR] activate blocked: validation failed")

    prev = cfg.get("active_pack", "default")
    cfg["_active_pack_prev"] = prev
    hist = cfg.get("active_pack_history")
    if not isinstance(hist, list):
        hist = []
    hist.append({"from": prev, "to": pack_id, "at": _now_iso()})
    cfg["active_pack_history"] = hist[-20:]
    cfg["active_pack"] = pack_id

    bak = _write_cfg(cfg, backup=True)
    print("[OK] active_pack set:", prev, "->", pack_id)
    print("[BACKUP]", bak.name if bak else "(none)")

    if args.smoke:
        print("[INFO] running smoke: ./scripts/run_smoke.sh")
        r = subprocess.run(["./scripts/run_smoke.sh"], cwd=str(ROOT_DIR))
        if r.returncode != 0:
            print("[ERROR] smoke failed; restoring config from backup:", bak.name if bak else "(none)")
            if bak and bak.exists():
                CONFIG_PATH.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
                print("[OK] restored:", CONFIG_PATH)
            return 2
        print("[OK] smoke passed")

    return 0



def cmd_eval(args: argparse.Namespace) -> int:
    """
    Evaluate a pack upgrade with a reproducible report:
      1) Run smoke on current active_pack (baseline) and collect metrics from build/*
      2) Activate candidate pack with --smoke (auto-rollback on failure)
      3) Collect metrics again and print diff; write build/kg_pack_eval.json
      4) Default: rollback to baseline (use --keep to keep candidate active)
    """
    cfg = _load_cfg()
    baseline_pack = cfg.get("active_pack") or "default"
    candidate_pack = args.pack_id

    def _run_smoke(label: str) -> None:
        print(f"[EVAL] running smoke ({label}) ...")
        r = subprocess.run(["./scripts/run_smoke.sh"], cwd=str(ROOT_DIR))
        if r.returncode != 0:
            raise SystemExit(f"[ERROR] smoke failed on {label}")

    def _read_json(fp: Path):
        if not fp.exists():
            return None
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _extract_metrics() -> Dict[str, Any]:
        build_dir = ROOT_DIR / "build"
        m: Dict[str, Any] = {"files": {}}

        kc = _read_json(build_dir / "kg_context.json") or {}
        kp = kc.get("kg_pack") if isinstance(kc, dict) else None
        m["kg_pack"] = kp
        m["kg_active_pack"] = (kp or {}).get("active_pack") if isinstance(kp, dict) else None
        m["kg_manifest_sha256"] = (kp or {}).get("manifest_sha256") if isinstance(kp, dict) else None
        m["domain_key"] = ((kc.get("domain_resolution") or {}) if isinstance(kc, dict) else {}).get("domain_key")
        sp = kc.get("selected_packs") if isinstance(kc, dict) else None
        if isinstance(sp, list):
            m["selected_packs_count"] = len(sp)
            m["selected_packs_names"] = [x.get("name") for x in sp if isinstance(x, dict) and x.get("name")]
        else:
            m["selected_packs_count"] = None
            m["selected_packs_names"] = []

        rj = _read_json(build_dir / "retrieve.json") or {}
        res = rj.get("results") if isinstance(rj, dict) else None
        if isinstance(res, list):
            m["retrieve_results_count"] = len(res)
            m["retrieve_sources"] = sorted({x.get("source") for x in res if isinstance(x, dict) and x.get("source")})
        else:
            m["retrieve_results_count"] = None
            m["retrieve_sources"] = []

        cj = _read_json(build_dir / "compose.json") or {}
        secs = cj.get("sections") if isinstance(cj, dict) else None
        if isinstance(secs, list):
            m["compose_sections_count"] = len(secs)
            m["compose_first_titles"] = [x.get("title") for x in secs[:8] if isinstance(x, dict) and x.get("title")]
        else:
            m["compose_sections_count"] = cj.get("sections_count") if isinstance(cj, dict) else None
            m["compose_first_titles"] = []

        aj = _read_json(build_dir / "audit_report.json") or _read_json(build_dir / "audit.json") or {}
        if isinstance(aj, dict):
            m["audit_replayable"] = aj.get("replayable") if "replayable" in aj else (aj.get("audit") or {}).get("replayable")
            m["audit_missing_count"] = aj.get("missing_count") if "missing_count" in aj else (aj.get("audit") or {}).get("missing_count")

        for fn in ("kg_context.json", "retrieve.json", "compose.json", "audit_report.json", "compose_exported_with_trace.docx"):
            fp = build_dir / fn
            if fp.exists():
                m["files"][fn] = {"size_bytes": fp.stat().st_size}
        return m

    def _diff(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "kg_active_pack",
            "kg_manifest_sha256",
            "domain_key",
            "selected_packs_count",
            "selected_packs_names",
            "retrieve_results_count",
            "retrieve_sources",
            "compose_sections_count",
            "compose_first_titles",
            "audit_replayable",
            "audit_missing_count",
        ]
        changes: Dict[str, Any] = {}
        for k in keys:
            av = a.get(k)
            bv = b.get(k)
            if av != bv:
                changes[k] = {"from": av, "to": bv}
        # file sizes
        af = a.get("files") if isinstance(a.get("files"), dict) else {}
        bf = b.get("files") if isinstance(b.get("files"), dict) else {}
        fchg = {}
        for fn in sorted(set(af.keys()) | set(bf.keys())):
            av = (af.get(fn) or {}).get("size_bytes")
            bv = (bf.get(fn) or {}).get("size_bytes")
            if av != bv:
                fchg[fn] = {"from": av, "to": bv}
        if fchg:
            changes["files.size_bytes"] = fchg
        return changes

    print("[EVAL] baseline_pack:", baseline_pack)
    print("[EVAL] candidate_pack:", candidate_pack)

    _run_smoke("baseline")
    baseline_metrics = _extract_metrics()

    # Activate candidate with smoke (auto-rollback on failure is handled by cmd_activate)
    print("[EVAL] activating candidate pack with --smoke ...")
    r = cmd_activate(argparse.Namespace(pack_id=candidate_pack, smoke=True))
    if r != 0:
        return int(r)

    candidate_metrics = _extract_metrics()
    changes = _diff(baseline_metrics, candidate_metrics)

    report = {
        "generated_at": _now_iso(),
        "baseline_pack": baseline_pack,
        "candidate_pack": candidate_pack,
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "changes": changes,
    }
    out_path = ROOT_DIR / "build" / "kg_pack_eval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[EVAL] diff_keys_count:", len(changes))
    for k, v in list(changes.items())[:80]:
        print(" -", k, ":", v)
    print("[EVAL] report_saved:", str(out_path))

    if not args.keep:
        print("[EVAL] rolling back to baseline (no smoke) ...")
        cmd_activate(argparse.Namespace(pack_id=baseline_pack, smoke=False))
        print("[EVAL] active_pack restored:", baseline_pack)
    else:
        print("[EVAL] keeping candidate active:", candidate_pack)

    return 0

def cmd_rollback(args: argparse.Namespace) -> int:
    cfg = _load_cfg()
    to_pack = args.to_pack
    if not to_pack:
        prev = cfg.get("_active_pack_prev")
        if not prev:
            raise SystemExit("[ERROR] no _active_pack_prev in kg_config.json; specify --to <pack_id>")
        to_pack = prev
    args2 = argparse.Namespace(pack_id=to_pack, smoke=args.smoke)
    return cmd_activate(args2)

def main() -> int:
    parser = argparse.ArgumentParser(prog="kg_pack.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="show current active pack and pack list")
    p_status.set_defaults(func=cmd_status)

    p_list = sub.add_parser("list", help="list packs in kg_config.json")
    p_list.set_defaults(func=cmd_list)

    p_validate = sub.add_parser("validate", help="validate a pack by config assets + manifest (if exists)")
    p_validate.add_argument("--pack-id", default=None)
    p_validate.set_defaults(func=cmd_validate)

    p_pack = sub.add_parser("pack", help="create a new pack from current (or specified) pack base_dir")
    p_pack.add_argument("--pack-id", required=True)
    p_pack.add_argument("--from-pack", default=None)
    p_pack.add_argument("--pack-version", default=None)
    p_pack.add_argument("--description", default=None)
    p_pack.add_argument("--force", action="store_true")
    p_pack.set_defaults(func=cmd_pack)

    p_act = sub.add_parser("activate", help="activate a pack (optional --smoke will auto rollback on failure)")
    p_act.add_argument("--pack-id", required=True)
    p_act.add_argument("--smoke", action="store_true")
    p_act.set_defaults(func=cmd_activate)

    p_eval = sub.add_parser("eval", help="evaluate a pack: baseline smoke -> activate+smoke -> diff report (default rollback)")
    p_eval.add_argument("--pack-id", required=True)
    p_eval.add_argument("--keep", action="store_true", help="keep candidate active after eval (default rollback to baseline)")
    p_eval.set_defaults(func=cmd_eval)

    p_rb = sub.add_parser("rollback", help="rollback to previous pack or specified --to")
    p_rb.add_argument("--to", dest="to_pack", default=None)
    p_rb.add_argument("--smoke", action="store_true")
    p_rb.set_defaults(func=cmd_rollback)

    args = parser.parse_args()
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main())
