from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_RELEASE_ROOT = Path("build/kg_releases")


def _iter_kg_files(kg_root: Path, pattern: str = "ZF-KG-*.json") -> List[Path]:
    return sorted([p for p in kg_root.glob(pattern) if p.is_file()], key=lambda p: p.name)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def create_release_snapshot(
    *,
    kg_root: Path | str,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
    label: str | None = None,
    approver: str = "system",
) -> Dict[str, Any]:
    root = Path(kg_root).expanduser().resolve()
    rel_root = Path(release_root).expanduser().resolve()
    rel_root.mkdir(parents=True, exist_ok=True)
    files = _iter_kg_files(root)
    if not files:
        raise FileNotFoundError(f"no kg files under: {root}")

    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    suffix = hashlib.md5(f"{root}|{ts}".encode("utf-8", errors="ignore")).hexdigest()[:8]
    release_id = f"{ts}_{suffix}"
    if label:
        release_id = f"{release_id}_{label}"
    dst = rel_root / release_id
    dst.mkdir(parents=True, exist_ok=True)

    manifest_files: List[Dict[str, Any]] = []
    for src in files:
        target = dst / src.name
        shutil.copy2(src, target)
        manifest_files.append({"file": src.name, "sha256": _sha256(src), "size": src.stat().st_size})

    manifest = {
        "release_id": release_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "kg_root": str(root),
        "status": "frozen",
        "approver": approver,
        "files_total": len(manifest_files),
        "files": manifest_files,
    }
    manifest_path = dst / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "release_id": release_id, "release_dir": str(dst), "manifest": str(manifest_path)}


def approve_auto_generated_nodes(
    *,
    kg_root: Path | str,
    approver: str,
    signature: str,
    note: str = "",
    pattern: str = "ZF-KG-*.json",
) -> Dict[str, Any]:
    root = Path(kg_root).expanduser().resolve()
    files = _iter_kg_files(root, pattern=pattern)
    touched_files = 0
    touched_nodes = 0
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        changed = False
        kg = payload.get("knowledge_database")
        if isinstance(kg, dict):
            for section in kg.values():
                if not isinstance(section, dict):
                    continue
                nodes = section.get("nodes")
                if not isinstance(nodes, list):
                    continue
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    if not bool(node.get("is_auto_generated")):
                        continue
                    wf = node.get("approval_workflow")
                    cur = dict(wf) if isinstance(wf, dict) else {}
                    desired = {
                        "required": True,
                        "status": "approved",
                        "reviewer_role": str(cur.get("reviewer_role") or "技术负责人"),
                        "release_gate": str(cur.get("release_gate") or "manual_or_system_approval_for_auto_generated"),
                        "reference_required": True,
                        "approval_source": "manual_signoff",
                        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                        "approved_by": approver,
                        "signature": signature,
                        "note": note,
                    }
                    if cur != desired:
                        node["approval_workflow"] = desired
                        changed = True
                        touched_nodes += 1
        if changed:
            touched_files += 1
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "kg_root": str(root),
        "files_total": len(files),
        "files_changed": touched_files,
        "nodes_approved": touched_nodes,
    }


def rollback_release_snapshot(
    *,
    kg_root: Path | str,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
    release_id: str,
) -> Dict[str, Any]:
    root = Path(kg_root).expanduser().resolve()
    rel_root = Path(release_root).expanduser().resolve()
    src = rel_root / str(release_id)
    if not src.exists():
        raise FileNotFoundError(f"release snapshot not found: {src}")
    manifest_path = src / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found in snapshot: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    restored = 0
    for row in rows:
        name = str((row or {}).get("file") or "").strip()
        if not name:
            continue
        s = src / name
        d = root / name
        if not s.exists():
            continue
        shutil.copy2(s, d)
        restored += 1
    return {
        "ok": True,
        "release_id": release_id,
        "kg_root": str(root),
        "restored_files": restored,
        "manifest": str(manifest_path),
    }

