from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.runtime_config import collect_main_chain_config_status

ROOT_DIR = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = ROOT_DIR / "build" / "_release_snapshots"
SNAPSHOT_TARGETS = (
    {"path": "backend/data/autoplan/config.json", "required": True, "kind": "config"},
    {"path": "backend/data/autoplan/agent_roles.json", "required": True, "kind": "config"},
    {"path": "backend/data/autoplan/quota_policy.json", "required": False, "kind": "config"},
    {"path": "kg_config.json", "required": True, "kind": "kg_config"},
    {"path": "backend/data/kg/active_kg.json", "required": False, "kind": "kg_runtime"},
    {"path": ".kg_pack_state.json", "required": False, "kind": "kg_runtime"},
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _sanitize_label(label: str | None) -> str:
    raw = _clean_text(label)
    if not raw:
        return ""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_meta(root_dir: Path) -> dict[str, Any]:
    def _run(*args: str) -> str | None:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(root_dir),
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            return None
        raw = proc.stdout.strip()
        return raw or None

    return {
        "commit": _run("rev-parse", "HEAD"),
        "branch": _run("rev-parse", "--abbrev-ref", "HEAD"),
    }


def _snapshot_name(label: str | None = None) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = _sanitize_label(label)
    return f"{stamp}_{safe_label}" if safe_label else stamp


def latest_snapshot_dir(*, root_dir: str | Path | None = None) -> Path | None:
    root = Path(root_dir or ROOT_DIR).resolve()
    base = root / "build" / "_release_snapshots"
    if not base.exists():
        return None
    dirs = sorted([item for item in base.iterdir() if item.is_dir()])
    return dirs[-1] if dirs else None


def snapshot_release_state(
    *,
    root_dir: str | Path | None = None,
    snapshot_root: str | Path | None = None,
    label: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(root_dir or ROOT_DIR).resolve()
    base = Path(snapshot_root or (root / "build" / "_release_snapshots")).resolve()
    snapshot_dir = base / _snapshot_name(label)
    files_dir = snapshot_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "label": _sanitize_label(label) or None,
        "root_dir": str(root),
        "git": _git_meta(root),
        "runtime_config": collect_main_chain_config_status(root_dir=root, env=env),
        "targets": [],
    }

    copied_count = 0
    missing_count = 0
    for spec in SNAPSHOT_TARGETS:
        rel = str(spec["path"])
        src = root / rel
        entry = {
            "path": rel,
            "required": bool(spec.get("required")),
            "kind": str(spec.get("kind") or "file"),
            "exists": src.exists(),
            "snapshot_path": str((files_dir / rel).relative_to(snapshot_dir)),
            "sha256": None,
            "size": None,
        }
        if src.exists():
            dst = files_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            entry["sha256"] = _sha256_file(src)
            entry["size"] = src.stat().st_size
            copied_count += 1
        else:
            missing_count += 1
        manifest["targets"].append(entry)

    manifest["copied_count"] = copied_count
    manifest["missing_count"] = missing_count
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "snapshot_dir": str(snapshot_dir),
        "manifest_path": str(manifest_path),
        "copied_count": copied_count,
        "missing_count": missing_count,
    }


def load_snapshot_manifest(snapshot_dir: str | Path) -> dict[str, Any]:
    path = Path(snapshot_dir).resolve() / "manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("snapshot manifest must be a JSON object")
    return doc


def restore_release_state(
    *,
    snapshot_dir: str | Path,
    root_dir: str | Path | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    root = Path(root_dir or ROOT_DIR).resolve()
    snap = Path(snapshot_dir).resolve()
    manifest = load_snapshot_manifest(snap)
    files_dir = snap / "files"

    plan: list[dict[str, Any]] = []
    copied = 0
    skipped = 0
    missing_snapshot_files = 0

    for target in manifest.get("targets") or []:
        rel = str(target.get("path") or "").strip()
        if not rel:
            continue
        src = files_dir / rel
        dst = root / rel
        exists_in_snapshot = bool(target.get("exists"))
        action = "skip_missing_in_snapshot"
        if exists_in_snapshot and src.exists():
            action = "copy"
        elif exists_in_snapshot and not src.exists():
            action = "snapshot_file_missing"
            missing_snapshot_files += 1
        else:
            skipped += 1
        entry = {
            "path": rel,
            "action": action,
            "destination_exists": dst.exists(),
            "snapshot_exists": src.exists(),
        }
        if execute and action == "copy":
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        plan.append(entry)

    return {
        "ok": True,
        "snapshot_dir": str(snap),
        "executed": bool(execute),
        "copied_count": copied,
        "skipped_count": skipped,
        "missing_snapshot_files": missing_snapshot_files,
        "plan": plan,
    }
