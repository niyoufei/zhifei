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
DEFAULT_RELEASE_HEALTH_THRESHOLDS = {
    "max_changed_file_ratio": 0.45,
    "max_auto_generated_growth_ratio": 0.35,
    "min_evidence_pass_ratio": 0.70,
    "max_high_authority_ratio_drop": 0.20,
}


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


def _load_manifest(snapshot_dir: Path) -> Dict[str, Any]:
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found in snapshot: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid manifest: {manifest_path}")
    return payload


def _iter_manifest_files(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    rows = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("file") or "").strip()
        if not name:
            continue
        out[name] = row
    return out


def _snapshot_node_stats(snapshot_dir: Path, files: List[str]) -> Dict[str, Any]:
    authority_dist: Dict[str, int] = {}
    stats = {
        "nodes_total": 0,
        "auto_generated_nodes": 0,
        "formula_nodes": 0,
        "evidence_pass_nodes": 0,
        "authority_distribution": authority_dist,
    }
    for name in files:
        path = snapshot_dir / name
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        kg = payload.get("knowledge_database")
        if not isinstance(kg, dict):
            continue
        for sec in kg.values():
            if not isinstance(sec, dict):
                continue
            nodes = sec.get("nodes")
            if not isinstance(nodes, list):
                continue
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                stats["nodes_total"] += 1
                if bool(node.get("is_auto_generated")):
                    stats["auto_generated_nodes"] += 1
                if str(node.get("node_type") or "").strip() == "FormulaNode":
                    stats["formula_nodes"] += 1
                evidence = node.get("evidence_completeness")
                if isinstance(evidence, dict) and float(evidence.get("completeness_ratio") or 0.0) >= 0.8:
                    stats["evidence_pass_nodes"] += 1
                hierarchy = str(node.get("source_hierarchy") or "未知").strip() or "未知"
                authority_dist[hierarchy] = int(authority_dist.get(hierarchy) or 0) + 1
    return stats


def _release_health_gate(
    *,
    base_stats: Dict[str, Any],
    target_stats: Dict[str, Any],
    changed_count: int,
    target_file_total: int,
    thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    cfg = dict(DEFAULT_RELEASE_HEALTH_THRESHOLDS)
    if isinstance(thresholds, dict):
        for key in cfg.keys():
            if key in thresholds:
                try:
                    cfg[key] = float(thresholds[key])
                except Exception:
                    pass

    changed_ratio = float(changed_count) / max(int(target_file_total or 0), 1)
    base_nodes = max(int(base_stats.get("nodes_total") or 0), 1)
    target_nodes = max(int(target_stats.get("nodes_total") or 0), 1)
    auto_growth_ratio = (
        float(int(target_stats.get("auto_generated_nodes") or 0) - int(base_stats.get("auto_generated_nodes") or 0))
        / float(base_nodes)
    )
    evidence_pass_ratio = float(target_stats.get("evidence_pass_nodes") or 0) / float(target_nodes)

    def high_authority_ratio(stats: Dict[str, Any]) -> float:
        dist = stats.get("authority_distribution") if isinstance(stats.get("authority_distribution"), dict) else {}
        top = int(dist.get("答疑文件", 0)) + int(dist.get("设计图纸", 0)) + int(dist.get("国标", 0))
        total = max(sum(int(v) for v in dist.values()), 1)
        return float(top) / float(total)

    base_high = high_authority_ratio(base_stats)
    target_high = high_authority_ratio(target_stats)
    high_authority_ratio_drop = max(0.0, base_high - target_high)

    checks = {
        "changed_file_ratio_ok": changed_ratio <= float(cfg["max_changed_file_ratio"]),
        "auto_generated_growth_ok": auto_growth_ratio <= float(cfg["max_auto_generated_growth_ratio"]),
        "evidence_pass_ratio_ok": evidence_pass_ratio >= float(cfg["min_evidence_pass_ratio"]),
        "high_authority_drop_ok": high_authority_ratio_drop <= float(cfg["max_high_authority_ratio_drop"]),
    }
    healthy = all(bool(v) for v in checks.values())
    return {
        "healthy": healthy,
        "rollback_recommended": not healthy,
        "thresholds": cfg,
        "metrics": {
            "changed_file_ratio": round(changed_ratio, 6),
            "auto_generated_growth_ratio": round(auto_growth_ratio, 6),
            "evidence_pass_ratio": round(evidence_pass_ratio, 6),
            "base_high_authority_ratio": round(base_high, 6),
            "target_high_authority_ratio": round(target_high, 6),
            "high_authority_ratio_drop": round(high_authority_ratio_drop, 6),
        },
        "checks": checks,
    }


def compare_release_snapshots(
    *,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
    base_release_id: str,
    target_release_id: str,
    health_thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    rel_root = Path(release_root).expanduser().resolve()
    base_dir = rel_root / str(base_release_id)
    target_dir = rel_root / str(target_release_id)
    if not base_dir.exists():
        raise FileNotFoundError(f"base release snapshot not found: {base_dir}")
    if not target_dir.exists():
        raise FileNotFoundError(f"target release snapshot not found: {target_dir}")

    base_manifest = _load_manifest(base_dir)
    target_manifest = _load_manifest(target_dir)
    base_files = _iter_manifest_files(base_manifest)
    target_files = _iter_manifest_files(target_manifest)

    base_names = set(base_files.keys())
    target_names = set(target_files.keys())
    added = sorted(target_names - base_names)
    removed = sorted(base_names - target_names)
    common = sorted(base_names & target_names)
    changed: List[Dict[str, Any]] = []
    unchanged = 0
    for name in common:
        a = str((base_files.get(name) or {}).get("sha256") or "")
        b = str((target_files.get(name) or {}).get("sha256") or "")
        if a and b and a != b:
            changed.append({"file": name, "base_sha256": a, "target_sha256": b})
        else:
            unchanged += 1

    base_stats = _snapshot_node_stats(base_dir, sorted(base_names))
    target_stats = _snapshot_node_stats(target_dir, sorted(target_names))
    authority_delta: Dict[str, int] = {}
    for k in sorted(set(base_stats["authority_distribution"].keys()) | set(target_stats["authority_distribution"].keys())):
        authority_delta[k] = int(target_stats["authority_distribution"].get(k, 0)) - int(
            base_stats["authority_distribution"].get(k, 0)
        )
    health_gate = _release_health_gate(
        base_stats=base_stats,
        target_stats=target_stats,
        changed_count=len(changed),
        target_file_total=len(target_names),
        thresholds=health_thresholds,
    )

    return {
        "ok": True,
        "release_root": str(rel_root),
        "base_release_id": str(base_release_id),
        "target_release_id": str(target_release_id),
        "files": {
            "base_total": len(base_names),
            "target_total": len(target_names),
            "added": added,
            "removed": removed,
            "changed": changed,
            "changed_count": len(changed),
            "unchanged_count": unchanged,
        },
        "node_stats": {
            "base": base_stats,
            "target": target_stats,
            "delta": {
                "nodes_total": int(target_stats["nodes_total"]) - int(base_stats["nodes_total"]),
                "auto_generated_nodes": int(target_stats["auto_generated_nodes"]) - int(base_stats["auto_generated_nodes"]),
                "formula_nodes": int(target_stats["formula_nodes"]) - int(base_stats["formula_nodes"]),
                "evidence_pass_nodes": int(target_stats["evidence_pass_nodes"]) - int(base_stats["evidence_pass_nodes"]),
                "authority_distribution": authority_delta,
            },
        },
        "health_gate": health_gate,
    }


def list_release_snapshots(
    *,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
) -> Dict[str, Any]:
    rel_root = Path(release_root).expanduser().resolve()
    rel_root.mkdir(parents=True, exist_ok=True)
    snapshots: List[Dict[str, Any]] = []
    for child in sorted([p for p in rel_root.iterdir() if p.is_dir()], key=lambda p: p.name):
        manifest_path = child / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        snapshots.append(
            {
                "release_id": child.name,
                "created_at": str((manifest or {}).get("created_at") or ""),
                "files_total": int((manifest or {}).get("files_total") or 0),
                "approver": str((manifest or {}).get("approver") or ""),
                "manifest": str(manifest_path),
            }
        )
    snapshots.sort(key=lambda x: str(x.get("release_id") or ""), reverse=True)
    return {"ok": True, "release_root": str(rel_root), "total": len(snapshots), "snapshots": snapshots}


def recommend_release_strategy(
    *,
    release_root: Path | str = DEFAULT_RELEASE_ROOT,
    target_release_id: str,
    base_release_id: str | None = None,
    health_thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    listing = list_release_snapshots(release_root=release_root)
    snapshots = listing.get("snapshots") if isinstance(listing.get("snapshots"), list) else []
    if not snapshots:
        return {"ok": False, "error": "no_release_snapshots", "strategy": "hold"}
    target_id = str(target_release_id or "").strip()
    if not target_id:
        return {"ok": False, "error": "target_release_id_missing", "strategy": "hold"}
    available_ids = [str(x.get("release_id") or "").strip() for x in snapshots if isinstance(x, dict)]
    if target_id not in available_ids:
        return {"ok": False, "error": "target_release_not_found", "strategy": "hold", "target_release_id": target_id}

    base_id = str(base_release_id or "").strip()
    if not base_id:
        for rid in available_ids:
            if rid and rid != target_id:
                base_id = rid
                break
    if not base_id:
        return {
            "ok": True,
            "strategy": "canary",
            "reason": "target_is_first_snapshot",
            "target_release_id": target_id,
            "base_release_id": "",
        }
    if base_id == target_id:
        return {
            "ok": True,
            "strategy": "hold",
            "reason": "base_equals_target",
            "target_release_id": target_id,
            "base_release_id": base_id,
        }

    compare = compare_release_snapshots(
        release_root=release_root,
        base_release_id=base_id,
        target_release_id=target_id,
        health_thresholds=health_thresholds,
    )
    health_gate = compare.get("health_gate") if isinstance(compare.get("health_gate"), dict) else {}
    healthy = bool(health_gate.get("healthy"))
    metrics = health_gate.get("metrics") if isinstance(health_gate.get("metrics"), dict) else {}
    changed_ratio = float(metrics.get("changed_file_ratio") or 0.0)
    strategy = "full"
    reason = "healthy_release"
    canary_ratio = 1.0
    if not healthy:
        strategy = "rollback_recommended"
        reason = "health_gate_failed"
        canary_ratio = 0.0
    elif changed_ratio >= 0.20:
        strategy = "canary"
        reason = "large_change_requires_canary"
        canary_ratio = 0.2
    return {
        "ok": True,
        "strategy": strategy,
        "reason": reason,
        "canary_ratio": canary_ratio,
        "target_release_id": target_id,
        "base_release_id": base_id,
        "comparison": compare,
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
