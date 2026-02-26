from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_RELEASE_ROOT = Path("build/kg_releases")
DEFAULT_ENV_STATE_FILE = "environments.json"
ENVIRONMENTS = ("dev", "staging", "prod")


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


def _state_path(release_root: Path | str = DEFAULT_RELEASE_ROOT) -> Path:
    rel_root = Path(release_root).expanduser().resolve()
    rel_root.mkdir(parents=True, exist_ok=True)
    return rel_root / DEFAULT_ENV_STATE_FILE


def _load_env_state(release_root: Path | str = DEFAULT_RELEASE_ROOT) -> Dict[str, Any]:
    path = _state_path(release_root)
    if not path.exists():
        return {
            "version": "v1",
            "updated_at": "",
            "environments": {env: {"release_id": "", "mode": "idle", "updated_at": "", "approver": ""} for env in ENVIRONMENTS},
            "canary": {},
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {
            "version": "v1",
            "updated_at": "",
            "environments": {env: {"release_id": "", "mode": "idle", "updated_at": "", "approver": ""} for env in ENVIRONMENTS},
            "canary": {},
        }
    envs = payload.get("environments")
    if not isinstance(envs, dict):
        envs = {}
    for env in ENVIRONMENTS:
        row = envs.get(env)
        if not isinstance(row, dict):
            envs[env] = {"release_id": "", "mode": "idle", "updated_at": "", "approver": ""}
    payload["environments"] = envs
    payload.setdefault("version", "v1")
    payload.setdefault("updated_at", "")
    payload.setdefault("canary", {})
    return payload


def get_release_environment_state(
    *,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
) -> Dict[str, Any]:
    state = _load_env_state(release_root)
    return {
        "ok": True,
        "release_root": str(Path(release_root).expanduser().resolve()),
        "state_path": str(_state_path(release_root)),
        "state": state,
    }


def promote_release_snapshot(
    *,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
    release_id: str,
    environment: str,
    approver: str,
    canary_ratio: float = 1.0,
    note: str = "",
) -> Dict[str, Any]:
    rel_root = Path(release_root).expanduser().resolve()
    env = str(environment or "").strip().lower()
    if env not in ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")

    snapshot_dir = rel_root / str(release_id)
    manifest_path = snapshot_dir / "manifest.json"
    if not snapshot_dir.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"release snapshot not found: {snapshot_dir}")

    state = _load_env_state(rel_root)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    ratio = max(0.0, min(1.0, float(canary_ratio)))
    mode = "full"
    if env == "prod" and 0.0 < ratio < 1.0:
        mode = "canary"
    state["environments"][env] = {
        "release_id": str(release_id),
        "mode": mode,
        "canary_ratio": ratio if mode == "canary" else 1.0,
        "updated_at": ts,
        "approver": approver,
        "note": note,
    }
    if mode == "canary":
        state["canary"] = {
            "environment": env,
            "release_id": str(release_id),
            "ratio": ratio,
            "updated_at": ts,
            "approver": approver,
        }
    elif env == "prod":
        state["canary"] = {}
    state["updated_at"] = ts

    path = _state_path(rel_root)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "release_root": str(rel_root),
        "release_id": str(release_id),
        "environment": env,
        "mode": mode,
        "state_path": str(path),
        "state": state,
    }
