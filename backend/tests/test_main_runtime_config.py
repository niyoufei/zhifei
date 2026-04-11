import json
import pytest

from backend.app import main as main_module
from backend.app.runtime_config import collect_main_chain_config_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_runtime_files(root):
    _write_json(
        root / "backend" / "data" / "autoplan" / "config.json",
        {
            "config_version": "2026-04-10",
            "default_provider": "openai",
            "default_model": "gpt-5.4",
            "job_list_default_fields": ["job_id", "status"],
        },
    )
    _write_json(
        root / "backend" / "data" / "autoplan" / "agent_roles.json",
        {
            "default": "技术负责人",
            "rules": [{"match": ["质量"], "role": "质量负责人"}],
        },
    )
    _write_json(
        root / "kg_config.json",
        {
            "base_packs": ["Universal_Base_Pack.json"],
            "domain_map": "SuperKG-DOMAIN-MAP.json",
            "packs": {
                "kgpack-test": {
                    "base_dir": ".",
                    "pack_version": "kgpack-test",
                    "manifest": "manifest.json",
                }
            },
            "active_pack": "kgpack-test",
        },
    )


def test_collect_main_chain_config_status_reports_release_ready(tmp_path):
    _seed_runtime_files(tmp_path)

    status = collect_main_chain_config_status(
        root_dir=tmp_path,
        env={
            "ZF_ACTIONS_KEY": "strong-actions-key",
            "ZF_ADMIN_KEY": "strong-admin-key",
            "OPENAI_API_KEY_TEXT_MAIN": "main-secret",
            "OPENAI_API_KEY_AUTOMATION": "automation-secret",
            "GEMINI_API_KEY_A": "gemini-secret",
        },
    )

    assert status["level"] == "ok"
    assert status["checks"]["release_ready"] is True
    assert status["checks"]["actions_generation_ready"] is True
    assert status["checks"]["actions_dry_run_ready"] is True
    assert status["checks"]["actions_api_auth"]["secure"] is True
    assert status["sources"]["config_json"]["config_version"] == "2026-04-10"
    assert status["defaults"]["provider"] == "openai"
    assert status["defaults"]["source"] == "config.json"
    assert status["providers"]["text_chain"][0]["key_alias"] == "OPENAI_API_KEY_TEXT_MAIN"


def test_collect_main_chain_config_status_flags_default_actions_key_and_missing_text_provider(tmp_path):
    _seed_runtime_files(tmp_path)

    status = collect_main_chain_config_status(root_dir=tmp_path, env={})

    assert status["level"] == "error"
    assert status["checks"]["release_ready"] is False
    assert status["checks"]["actions_dry_run_ready"] is True
    assert status["checks"]["actions_api_auth"]["secure"] is False
    assert status["checks"]["actions_api_auth"]["uses_builtin_default"] is True
    assert any("ZF_ACTIONS_KEY" in item for item in status["warnings"])
    assert any("正文生成 Provider" in item for item in status["blocking"])
    assert any("OPENAI_API_KEY_TEXT_MAIN" in item for item in status["required_next_actions"])


def test_health_exposes_runtime_config_summary(monkeypatch):
    canned = {
        "level": "warn",
        "warnings": ["warn-a"],
        "blocking": [],
        "checks": {
            "release_ready": False,
            "actions_generation_ready": True,
            "actions_dry_run_ready": True,
            "actions_api_auth": {"secure": False},
            "text_generation": {"ready": True},
            "kg_config": {"ready": True},
        },
        "sources": {
            "config_json": {
                "mtime": 123.0,
                "config_version": "2026-04-10",
                "mtime_human": "2026-04-10",
            }
        },
    }
    monkeypatch.setattr(main_module, "collect_main_chain_config_status", lambda: canned)

    out = main_module.health()

    assert out["config_version"] == "2026-04-10"
    assert out["config_status"]["level"] == "warn"
    assert out["config_status"]["release_ready"] is False
    assert out["config_status"]["actions_dry_run_ready"] is True
    assert out["config_status"]["warnings"] == ["warn-a"]


def test_capabilities_and_config_expose_generation_modes(monkeypatch):
    from backend.zhifei_autoplan import boq_store, kg_store, tender_store
    from backend.app.routers import zhifei_autoplan as compat_router
    from backend.zhifei_autoplan.utils.llm_client import LLMClient

    canned = {
        "level": "ok",
        "warnings": [],
        "blocking": [],
        "checks": {
            "release_ready": True,
            "actions_generation_ready": True,
            "actions_dry_run_ready": True,
            "actions_api_auth": {"secure": True},
            "text_generation": {"ready": True},
            "kg_config": {"ready": True},
            "agent_roles": {"ready": True},
        },
        "providers": {"status": {"text_chain_ready": True}},
        "defaults": {"provider": "openai", "model": "gpt-5.4"},
        "sources": {
            "config_json": {
                "mtime": 123.0,
                "config_version": "2026-04-11",
                "mtime_human": "2026-04-11 09:00",
            }
        },
    }
    monkeypatch.setattr(main_module, "collect_main_chain_config_status", lambda: canned)
    monkeypatch.setattr(kg_store, "get_active_kg", lambda: {"kg_id": "kgpack-test"})
    monkeypatch.setattr(tender_store, "load_tender_matrix", lambda: {"项目名称": "测试项目"})
    monkeypatch.setattr(boq_store, "load_boq_data", lambda: {"items": [1]})
    monkeypatch.setattr(compat_router, "_job_list_default_fields", lambda: {"job_id", "status"})
    monkeypatch.setattr(compat_router, "_job_list_field_alias", lambda: {"status": {"state"}})
    monkeypatch.setattr(LLMClient, "load_defaults", staticmethod(lambda: {"default_provider": "openai", "default_model": "gpt-5.4"}))

    caps = main_module.capabilities()
    cfg = main_module.config()

    assert [item["id"] for item in caps["generation_modes"]][:3] == [
        "standard_auto",
        "quality_200",
        "hq_speed_500",
    ]
    assert any(item["id"] == "stable_delivery" and item["stable_output"] is True for item in caps["generation_modes"])
    assert any(item["id"] == "stable_delivery" for item in cfg["generation_modes"])
    assert cfg["runtime_config"]["checks"]["release_ready"] is True


@pytest.mark.asyncio
async def test_lifespan_runs_startup_warmup(monkeypatch):
    seen = []

    async def _fake_startup():
        seen.append("startup")

    monkeypatch.setattr(main_module, "_startup_warmup", _fake_startup)

    async with main_module.lifespan(main_module.app):
        assert seen == ["startup"]
