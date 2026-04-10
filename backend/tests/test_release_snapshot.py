import json
from pathlib import Path

from backend.zhifei_autoplan.release_snapshot import (
    restore_release_state,
    snapshot_release_state,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_release_state(root: Path) -> None:
    _write_json(root / "backend" / "data" / "autoplan" / "config.json", {"config_version": "v1"})
    _write_json(
        root / "backend" / "data" / "autoplan" / "agent_roles.json",
        {"default": "技术负责人", "rules": [{"match": ["质量"], "role": "质量负责人"}]},
    )
    _write_json(root / "backend" / "data" / "autoplan" / "quota_policy.json", {"config_version": "quota-v1"})
    _write_json(
        root / "kg_config.json",
        {
            "packs": {"default": {"base_dir": ".", "manifest": "manifest.json"}},
            "active_pack": "default",
            "base_packs": ["Universal_Base_Pack.json"],
            "domain_map": "map.json",
        },
    )
    _write_json(root / "backend" / "data" / "kg" / "active_kg.json", {"file_name": "kg.json"})
    _write_json(root / ".kg_pack_state.json", {"active_pack_prev": "baseline"})


def test_snapshot_release_state_writes_manifest_and_files(tmp_path):
    _seed_release_state(tmp_path)

    out = snapshot_release_state(
        root_dir=tmp_path,
        snapshot_root=tmp_path / "build" / "_release_snapshots",
        label="before_patch",
        env={
            "ZF_ACTIONS_KEY": "strong-actions-key",
            "OPENAI_API_KEY_TEXT_MAIN": "main-secret",
            "ZF_ADMIN_KEY": "admin-secret",
            "OPENAI_API_KEY_AUTOMATION": "automation-secret",
            "GEMINI_API_KEY_A": "gemini-secret",
        },
    )

    snapshot_dir = Path(out["snapshot_dir"])
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))

    assert out["ok"] is True
    assert snapshot_dir.name.endswith("before_patch")
    assert manifest["copied_count"] >= 5
    assert manifest["runtime_config"]["checks"]["release_ready"] is True
    assert (snapshot_dir / "files" / "backend" / "data" / "autoplan" / "config.json").exists()
    assert (snapshot_dir / "files" / "kg_config.json").exists()


def test_restore_release_state_preview_and_execute(tmp_path):
    _seed_release_state(tmp_path)

    snap = snapshot_release_state(
        root_dir=tmp_path,
        snapshot_root=tmp_path / "build" / "_release_snapshots",
        env={"OPENAI_API_KEY_TEXT_MAIN": "main-secret", "ZF_ACTIONS_KEY": "strong-actions-key"},
    )
    snapshot_dir = Path(snap["snapshot_dir"])

    changed_cfg = tmp_path / "backend" / "data" / "autoplan" / "config.json"
    changed_cfg.write_text(json.dumps({"config_version": "v2"}), encoding="utf-8")

    preview = restore_release_state(snapshot_dir=snapshot_dir, root_dir=tmp_path, execute=False)
    assert preview["executed"] is False
    assert any(item["path"] == "backend/data/autoplan/config.json" and item["action"] == "copy" for item in preview["plan"])

    execute = restore_release_state(snapshot_dir=snapshot_dir, root_dir=tmp_path, execute=True)
    restored = json.loads(changed_cfg.read_text(encoding="utf-8"))

    assert execute["executed"] is True
    assert execute["copied_count"] >= 1
    assert restored["config_version"] == "v1"
