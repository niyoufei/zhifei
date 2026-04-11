from __future__ import annotations

import json
import os
from collections.abc import Mapping
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from backend.zhifei_autoplan.provider_runtime import (
    build_server_text_slots,
    frontend_provider_status,
    resolve_automation_slot,
    resolve_image_slots,
)

ACTIONS_KEY_DEFAULT = "zf-webui-key"


def _project_root(root_dir: str | Path | None = None) -> Path:
    if root_dir is not None:
        return Path(root_dir).resolve()
    return Path(__file__).resolve().parents[2]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _json_dict_status(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    exists = path.exists()
    doc: dict[str, Any] = {}
    error = ""
    if exists:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                doc = raw
            else:
                error = "json_not_object"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    mtime = path.stat().st_mtime if exists else None
    mtime_human = None
    if mtime is not None:
        try:
            mtime_human = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except Exception:
            mtime_human = None
    meta = {
        "path": str(path),
        "exists": exists,
        "json_valid": bool(exists and not error and isinstance(doc, dict)),
        "error": error or None,
        "mtime": mtime,
        "mtime_human": mtime_human,
    }
    return doc, meta


def _resolve_default_pair(config_doc: Mapping[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    provider = _clean_text(config_doc.get("default_provider"))
    model = _clean_text(config_doc.get("default_model"))
    source = ""
    if provider or model:
        source = "config.json"
    else:
        provider = _clean_text(env.get("ZF_DEFAULT_PROVIDER"))
        model = _clean_text(env.get("ZF_DEFAULT_MODEL"))
        if provider or model:
            source = "env"
    return {
        "provider": provider or None,
        "model": model or None,
        "source": source or None,
        "configured": bool(provider and model),
        "api_key_configured": bool(_clean_text(env.get("ZF_DEFAULT_API_KEY"))),
        "scope": "compat_/compose_and_model_ping",
    }


def collect_main_chain_config_status(
    *,
    root_dir: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = _project_root(root_dir=root_dir)
    env_map = {str(k): str(v) for k, v in dict(os.environ if env is None else env).items()}

    config_path = root / "backend" / "data" / "autoplan" / "config.json"
    roles_path = root / "backend" / "data" / "autoplan" / "agent_roles.json"
    kg_config_path = root / "kg_config.json"

    config_doc, config_meta = _json_dict_status(config_path)
    roles_doc, roles_meta = _json_dict_status(roles_path)
    kg_doc, kg_meta = _json_dict_status(kg_config_path)

    config_meta["config_version"] = _clean_text(config_doc.get("config_version")) or None
    config_meta["default_provider"] = _clean_text(config_doc.get("default_provider")) or None
    config_meta["default_model"] = _clean_text(config_doc.get("default_model")) or None
    config_meta["job_list_default_fields_count"] = len(config_doc.get("job_list_default_fields") or [])

    rules = roles_doc.get("rules")
    roles_ready = bool(
        roles_meta["json_valid"]
        and _clean_text(roles_doc.get("default"))
        and isinstance(rules, list)
    )
    roles_meta["configured"] = roles_ready
    roles_meta["default_role"] = _clean_text(roles_doc.get("default")) or None
    roles_meta["rules_count"] = len(rules) if isinstance(rules, list) else 0

    packs = kg_doc.get("packs")
    active_pack = _clean_text(kg_doc.get("active_pack"))
    kg_ready = bool(kg_meta["json_valid"])
    kg_meta["configured"] = kg_ready
    kg_meta["active_pack"] = active_pack or None
    kg_meta["active_pack_known"] = bool(active_pack and isinstance(packs, dict) and active_pack in packs)
    kg_meta["base_packs_count"] = len(kg_doc.get("base_packs") or [])
    kg_meta["domain_map"] = _clean_text(kg_doc.get("domain_map")) or None

    env_ctx = patch.dict(os.environ, env_map, clear=True) if env is not None else nullcontext()
    with env_ctx:
        provider_status = frontend_provider_status()
        text_slots = [slot.as_payload() for slot in build_server_text_slots()]
        image_slots = [slot.as_payload() for slot in resolve_image_slots()]
        automation_slot = resolve_automation_slot()

    actions_key = _clean_text(env_map.get("ZF_ACTIONS_KEY"))
    actions_key_configured = bool(actions_key)
    actions_key_uses_default = (not actions_key) or actions_key == ACTIONS_KEY_DEFAULT
    actions_api_ready = True
    actions_api_secure = bool(actions_key_configured and not actions_key_uses_default)

    admin_key_configured = bool(_clean_text(env_map.get("ZF_ADMIN_KEY")))
    default_pair = _resolve_default_pair(config_doc, env_map)

    checks = {
        "config_json": {"ready": bool(config_meta["json_valid"]), "path": config_meta["path"]},
        "agent_roles": {"ready": roles_ready, "path": roles_meta["path"]},
        "kg_config": {
            "ready": kg_ready,
            "active_pack": kg_meta["active_pack"],
            "active_pack_known": kg_meta["active_pack_known"],
            "path": kg_meta["path"],
        },
        "actions_api_auth": {
            "ready": actions_api_ready,
            "configured": actions_key_configured,
            "secure": actions_api_secure,
            "uses_builtin_default": actions_key_uses_default,
            "env": "ZF_ACTIONS_KEY",
        },
        "admin_api_auth": {
            "ready": admin_key_configured,
            "env": "ZF_ADMIN_KEY",
        },
        "text_generation": {
            "ready": bool(text_slots),
            "slot_count": len(text_slots),
        },
        "image_generation": {
            "ready": bool(image_slots),
            "slot_count": len(image_slots),
        },
        "automation_generation": {
            "ready": automation_slot is not None,
            "env": "OPENAI_API_KEY_AUTOMATION",
        },
        "compat_default_model": {
            "ready": bool(default_pair["configured"]),
            "source": default_pair["source"],
        },
    }
    checks["actions_dry_run_ready"] = bool(checks["kg_config"]["ready"] and checks["actions_api_auth"]["ready"])
    checks["actions_generation_ready"] = bool(checks["text_generation"]["ready"] and checks["kg_config"]["ready"])
    checks["release_ready"] = bool(
        checks["config_json"]["ready"]
        and checks["kg_config"]["ready"]
        and checks["actions_generation_ready"]
        and actions_api_secure
    )

    warnings: list[str] = []
    next_actions: list[str] = []
    blocking: list[str] = []

    if not config_meta["json_valid"]:
        warnings.append("backend/data/autoplan/config.json 缺失或无效；主链会退回内置默认值。")
        next_actions.append("修复 backend/data/autoplan/config.json，至少保留 config_version 和主链非敏感配置。")
    if not roles_ready:
        warnings.append("backend/data/autoplan/agent_roles.json 缺失或无效；章节角色会回退到内置默认规则。")
        next_actions.append("修复 backend/data/autoplan/agent_roles.json，确保包含 default 和 rules。")
    if not kg_ready:
        blocking.append("kg_config.json 缺失或无效；KG pack 配置不可追溯。")
        next_actions.append("恢复根目录 kg_config.json，并确认 active_pack 与 packs 映射有效。")
    elif not kg_meta["active_pack_known"]:
        warnings.append("kg_config.json 已加载，但 active_pack 未在 packs 中命中；KG 配置口径需要收敛。")
        next_actions.append("校验 kg_config.json 中的 active_pack 是否存在于 packs。")
    if not actions_api_secure:
        warnings.append("ZF_ACTIONS_KEY 未配置或仍使用内置默认值；/actions 鉴权不满足发布要求。")
        next_actions.append("设置强随机 ZF_ACTIONS_KEY，避免继续使用 zf-webui-key。")
    if not checks["text_generation"]["ready"]:
        blocking.append("未配置正文生成 Provider；/actions 真实生成只能 dry-run。")
        next_actions.append("至少配置 OPENAI_API_KEY_TEXT_MAIN，或启用兼容文本链路。")
    if not admin_key_configured:
        warnings.append("ZF_ADMIN_KEY 未配置；配置管理与管理员接口将不可用。")
        next_actions.append("设置 ZF_ADMIN_KEY 以启用 /config/version 与管理接口。")
    if not checks["image_generation"]["ready"]:
        warnings.append("未配置视觉链路；导图、插图等能力会降级。")
        next_actions.append("配置 GEMINI_API_KEY_A，必要时再补 GEMINI_API_KEY_B。")
    if not checks["automation_generation"]["ready"]:
        warnings.append("未配置自动修订 Provider；自动修订/排障链会降级。")
        next_actions.append("配置 OPENAI_API_KEY_AUTOMATION 以恢复自动修订链。")

    deduped_next_actions: list[str] = []
    for item in next_actions:
        if item not in deduped_next_actions:
            deduped_next_actions.append(item)

    level = "ok"
    if blocking:
        level = "error"
    elif warnings:
        level = "warn"

    return {
        "level": level,
        "blocking": blocking,
        "warnings": warnings,
        "required_next_actions": deduped_next_actions,
        "checks": checks,
        "defaults": default_pair,
        "providers": {
            "status": provider_status,
            "text_chain": text_slots,
            "image_chain": image_slots,
            "automation": automation_slot.as_payload() if automation_slot else None,
        },
        "sources": {
            "config_json": config_meta,
            "agent_roles_json": roles_meta,
            "kg_config_json": kg_meta,
            "env": {
                "purpose": "runtime_secrets_and_deploy_knobs",
                "actions_key_env": "ZF_ACTIONS_KEY",
                "admin_key_env": "ZF_ADMIN_KEY",
                "text_envs": [
                    "OPENAI_API_KEY_TEXT_MAIN",
                    "OPENAI_API_KEY_TEXT_BACKUP",
                    "GEMINI_API_KEY_A",
                ],
                "image_envs": ["GEMINI_API_KEY_A", "GEMINI_API_KEY_B"],
                "automation_envs": ["OPENAI_API_KEY_AUTOMATION"],
                "compat_default_envs": [
                    "ZF_DEFAULT_PROVIDER",
                    "ZF_DEFAULT_MODEL",
                    "ZF_DEFAULT_API_KEY",
                ],
            },
        },
        "ssot": {
            "config_json": "backend/data/autoplan/config.json",
            "agent_roles_json": "backend/data/autoplan/agent_roles.json",
            "kg_config_json": "kg_config.json",
            "runtime_env": "environment_variables",
        },
    }
