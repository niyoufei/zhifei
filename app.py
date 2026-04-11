#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import html
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
import streamlit as st
import streamlit.components.v1 as components

from backend.zhifei_autoplan.workspace import maybe_cleanup_expired_workspaces, resolve_workspace_dir

# Guard against low file-descriptor limits when launched from GUI contexts on macOS.
try:
    import resource  # type: ignore

    _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    _target = min(max(int(_soft), 4096), int(_hard) if int(_hard) > 0 else 4096)
    if _target > int(_soft):
        resource.setrlimit(resource.RLIMIT_NOFILE, (_target, _hard))
except Exception:
    pass


st.set_page_config(page_title="文档生成系统", page_icon="📄", layout="wide", initial_sidebar_state="collapsed")


def _load_project_types() -> list[str]:
    try:
        from backend.zhifei_autoplan.project_types import ordered_project_types

        arr = ordered_project_types()
        if isinstance(arr, list) and arr:
            return [str(x) for x in arr if str(x).strip()]
    except Exception:
        pass
    return [
        "房建",
        "维修改造",
        "装修",
        "市政道路",
        "市政排水",
        "室外附属",
        "城市更新",
        "景观园林",
        "市政桥梁",
        "市政燃气",
        "市政排水站",
        "河道治理",
        "水利水电",
        "公路工程",
        "电力能源",
        "水利枢纽",
        "石油化工",
        "综合管廊",
        "港航工程",
        "数据机房",
    ]


PROJECT_TYPES = _load_project_types()


def _load_template_page_bucket_config() -> tuple[list[str], dict[str, str]]:
    try:
        from backend.zhifei_autoplan.template_library import TEMPLATE_PAGE_BUCKETS, TEMPLATE_PAGE_BUCKET_LABELS

        buckets = [str(x) for x in (TEMPLATE_PAGE_BUCKETS or []) if str(x).strip()]
        labels = {str(k): str(v) for k, v in (TEMPLATE_PAGE_BUCKET_LABELS or {}).items() if str(k).strip()}
        if buckets and labels:
            return buckets, labels
    except Exception:
        pass
    return (
        ["50_pages", "le_200_pages", "gt_200_pages"],
        {
            "50_pages": "50页施组",
            "le_200_pages": "小于等于200页施组",
            "gt_200_pages": "大于200页施组",
        },
    )


TEMPLATE_PAGE_BUCKETS, TEMPLATE_PAGE_BUCKET_LABELS = _load_template_page_bucket_config()
TEXT_PROVIDER_OPTIONS = [
    "google",
    "openai",
    "grok",
    "anthropic",
    "deepseek",
    "zhipu",
    "qwen",
    "baidu",
    "iflytek",
    "tencent",
]
FALLBACK_PROVIDER_OPTIONS = [""] + TEXT_PROVIDER_OPTIONS
LATEST_TEXT_MODELS = {
    "google": "Gemini3.1pro",
    "openai": "ChatGPT-5.4",
    "grok": "grok-4-1-fast-reasoning",
}

def _load_generation_mode_catalog() -> list[dict[str, Any]]:
    ui_meta = {
        "speed_fast": {
            "ui_label": "极速：优先出稿速度",
            "engine_label": "极速执行",
            "legacy": False,
            "stable_output": False,
        },
        "standard_auto": {
            "ui_label": "标准：平衡质量与速度",
            "engine_label": "标准执行（自动按篇幅切换）",
            "legacy": False,
            "stable_output": False,
        },
        "stable_delivery": {
            "ui_label": "稳交：优先结果一致性",
            "engine_label": "稳定交付执行",
            "legacy": False,
            "stable_output": True,
        },
        "pro_polish": {
            "ui_label": "精编：优先修订与润色",
            "engine_label": "精编执行",
            "legacy": False,
            "stable_output": False,
        },
        "quality_200": {
            "ui_label": "标准：平衡质量与速度",
            "engine_label": "标准执行（≤200页）",
            "legacy": True,
            "stable_output": False,
        },
        "hq_speed_500": {
            "ui_label": "标准：平衡质量与速度",
            "engine_label": "标准执行（>200页加速）",
            "legacy": True,
            "stable_output": False,
        },
    }
    ordered_ids = [
        "speed_fast",
        "standard_auto",
        "stable_delivery",
        "pro_polish",
        "quality_200",
        "hq_speed_500",
    ]
    backend_catalog: dict[str, dict[str, Any]] = {}
    try:
        from backend.app.routers.actions_bridge import generation_mode_catalog as _backend_generation_mode_catalog

        for item in _backend_generation_mode_catalog():
            if isinstance(item, dict) and str(item.get("id") or "").strip():
                backend_catalog[str(item["id"]).strip()] = dict(item)
    except Exception:
        backend_catalog = {}

    out: list[dict[str, Any]] = []
    for mode_id in ordered_ids:
        merged = dict(backend_catalog.get(mode_id) or {"id": mode_id, "profile": mode_id})
        meta = ui_meta[mode_id]
        merged["legacy"] = bool(meta["legacy"] or merged.get("legacy"))
        merged["stable_output"] = bool(meta["stable_output"] or merged.get("stable_output"))
        merged["ui_label"] = meta["ui_label"]
        merged["engine_label"] = meta["engine_label"]
        out.append(merged)
    return out


GENERATION_MODE_CATALOG = _load_generation_mode_catalog()
GENERATION_MODE_OPTIONS = [str(item["id"]) for item in GENERATION_MODE_CATALOG if not bool(item.get("legacy"))]
GENERATION_MODE_LABELS = {str(item["id"]): str(item.get("ui_label") or item.get("label") or item["id"]) for item in GENERATION_MODE_CATALOG}
GENERATION_ENGINE_LABELS = {str(item["id"]): str(item.get("engine_label") or item.get("label") or item["id"]) for item in GENERATION_MODE_CATALOG}
FIXED_COVER_PAGES = 1
DEFAULT_FULL_INDEX_PAGES = 1
FRONT_MATTER_PAGE_MODE_OPTIONS = ["include", "exclude"]
FRONT_MATTER_PAGE_MODE_LABELS = {
    "include": "A：封面、目录计入总页数",
    "exclude": "B：封面、目录不计入总页数",
}
LOGIC_TEMPLATE_OPTIONS = ["A", "B", "C", "D", "E"]


def _latest_model_for(provider: str | None) -> str:
    return str(LATEST_TEXT_MODELS.get(str(provider or "").strip().lower()) or "")


def _template_page_bucket_label(bucket: str | None) -> str:
    key = str(bucket or "").strip()
    return str(TEMPLATE_PAGE_BUCKET_LABELS.get(key) or key)


def _dev_panels_enabled() -> bool:
    env_flag = str(os.environ.get("ZF_SHOW_DEV_PANELS") or "").strip().lower()
    if env_flag in {"1", "true", "yes", "on"}:
        return True
    try:
        query_flag = str(st.query_params.get("dev") or "").strip().lower()
    except Exception:
        query_flag = ""
    return query_flag in {"1", "true", "yes", "on"}


PRIMARY_TEXT_PROVIDER = "openai"
SECONDARY_TEXT_PROVIDER = "google"
PRIMARY_TEXT_MODEL = _latest_model_for(PRIMARY_TEXT_PROVIDER)
SECONDARY_TEXT_MODEL = _latest_model_for(SECONDARY_TEXT_PROVIDER)


def _legacy_model_alias_map() -> dict[str, str]:
    return {
        "gemini-2.0-flash": _latest_model_for("google"),
        "gemini-2.5-flash": _latest_model_for("google"),
        "gemini-3.1-pro-preview": _latest_model_for("google"),
        "gemini-3-pro-preview": _latest_model_for("google"),
        "gpt-4": _latest_model_for("openai"),
        "gpt-5.2-pro": _latest_model_for("openai"),
    }


def _normalize_provider_model_pair(provider: str | None, model: str | None, *, fallback: str = "") -> tuple[str, str]:
    normalized_provider = _normalize_provider(provider, fallback=fallback) if str(provider or "").strip() else fallback
    model_text = str(model or "").strip()
    if not normalized_provider:
        return "", ""
    latest = _latest_model_for(normalized_provider)
    if not model_text:
        return normalized_provider, latest
    alias = _legacy_model_alias_map().get(model_text)
    if alias:
        return normalized_provider, alias
    if normalized_provider == "openai" and model_text.lower().startswith("gemini"):
        return normalized_provider, latest
    if normalized_provider == "google" and (model_text.lower().startswith("gpt") or model_text.lower().startswith("chatgpt")):
        return normalized_provider, latest
    return normalized_provider, model_text


def _load_local_keys_env() -> dict[str, str]:
    keys_file = Path(os.environ.get("ZF_KEYS_FILE") or ".runtime/local_keys.env")
    if not keys_file.is_absolute():
        keys_file = Path(__file__).resolve().parent / keys_file
    if not keys_file.exists():
        return {}
    out: dict[str, str] = {}
    try:
        for raw in keys_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip()
            val = v.strip().strip('"').strip("'")
            if key:
                out[key] = val
    except Exception:
        return {}
    return out


LOCAL_KEYS = _load_local_keys_env()


def _normalize_template_selection(raw: Any) -> list[str]:
    arr = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
    alias = {
        "TEMPLATE_A": "A",
        "TEMPLATE_B": "B",
        "TEMPLATE_C": "C",
        "TEMPLATE_D": "D",
        "TEMPLATE_E": "E",
        "方案A": "A",
        "方案B": "B",
        "方案C": "C",
        "方案D": "D",
        "方案E": "E",
        "S": "C",
        "方案S": "C",
    }
    out: list[str] = []
    seen = set()
    for x in arr:
        s = str(x or "").strip().upper()
        if not s:
            continue
        s = alias.get(s, s)
        if s not in LOGIC_TEMPLATE_OPTIONS or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:5]


def _env_first(*keys: str) -> str:
    for k in keys:
        v = os.environ.get(k) or LOCAL_KEYS.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _provider_key_from_env(provider: str | None) -> str:
    p = str(provider or "").strip().lower()
    env_map = {
        "openai": ("ZF_OPENAI_API_KEY", "OPENAI_API_KEY"),
        "google": ("ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "grok": ("ZF_GROK_API_KEY", "GROK_API_KEY", "XAI_API_KEY"),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "zhipu": ("ZHIPU_API_KEY",),
        "qwen": ("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        "baidu": ("BAIDU_API_KEY",),
        "iflytek": ("IFLYTEK_API_KEY",),
        "tencent": ("TENCENT_API_KEY",),
    }
    for k in env_map.get(p, ()):
        v = os.environ.get(k) or LOCAL_KEYS.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _provider_runtime_status() -> dict[str, dict[str, Any]]:
    try:
        from backend.zhifei_autoplan.provider_runtime import frontend_provider_status

        status = frontend_provider_status()
        if isinstance(status, dict):
            return status
    except Exception:
        pass
    return {
        "text_main": {"configured": False, "env": "OPENAI_API_KEY_TEXT_MAIN", "model": PRIMARY_TEXT_MODEL},
        "text_backup": {"configured": False, "env": "OPENAI_API_KEY_TEXT_BACKUP", "model": PRIMARY_TEXT_MODEL},
        "automation": {"configured": False, "env": "OPENAI_API_KEY_AUTOMATION", "model": PRIMARY_TEXT_MODEL},
        "gemini_a": {"configured": False, "env": "GEMINI_API_KEY_A", "model": "gemini-2.5-flash-image"},
        "gemini_b": {"configured": False, "env": "GEMINI_API_KEY_B", "model": "gemini-2.5-flash-image"},
    }


def _provider_status_badge(configured: bool) -> str:
    return "已配置" if configured else "未配置"


def _normalize_provider(raw: str | None, *, fallback: str) -> str:
    p = str(raw or "").strip().lower()
    if p in TEXT_PROVIDER_OPTIONS:
        return p
    return fallback


def _normalize_generation_mode(raw: str | None) -> str:
    mode = str(raw or "").strip()
    if mode in {"quality_200", "hq_speed_500"}:
        return "standard_auto"
    if mode in GENERATION_MODE_OPTIONS:
        return mode
    return "standard_auto"


def _resolve_generation_mode_params(
    *,
    generation_mode: str,
    planned_total_pages: int,
    quality_strict: bool,
    auto_remediate: bool,
    remediate_mode: str,
    agent_parallelism: int,
    variant_parallelism: int,
    generate_images: bool,
) -> dict[str, Any]:
    mode = _normalize_generation_mode(generation_mode)
    qs = bool(quality_strict)
    ar = bool(auto_remediate)
    rm = str(remediate_mode or "template").strip() or "template"
    ap = max(1, min(16, int(agent_parallelism or 4)))
    vp = max(1, min(5, int(variant_parallelism or 1)))
    gi = bool(generate_images)
    compare_max_chars = 1200
    mode_effective = "quality_200"
    auto_switched = False

    if mode == "speed_fast":
        qs = True
        ar = True
        rm = "template"
        ap = max(8, ap)
        gi = False
        compare_max_chars = 600
        mode_effective = "speed_fast"
    elif mode == "stable_delivery":
        qs = True
        ar = True
        rm = "template"
        vp = 1
        ap = min(3, max(1, ap or 2))
        compare_max_chars = 1600
        mode_effective = "stable_delivery"
    elif mode == "pro_polish":
        qs = True
        ar = True
        rm = "llm"
        vp = 1
        ap = min(4, max(1, ap))
        compare_max_chars = 1600
        mode_effective = "pro_polish"
    else:
        if int(planned_total_pages or 0) > 200:
            mode_effective = "hq_speed_500"
            auto_switched = True
        else:
            mode_effective = "quality_200"
        qs = True
        ar = True
        if mode_effective == "hq_speed_500":
            rm = "template"
            ap = max(6, ap)
            gi = False
            compare_max_chars = 800
        else:
            rm = "template" if rm not in {"template", "llm"} else rm
            vp = 1

    return {
        "generation_mode": mode,
        "mode_effective": mode_effective,
        "auto_switched": bool(auto_switched),
        "quality_strict": qs,
        "auto_remediate": ar,
        "remediate_mode": rm,
        "agent_parallelism": ap,
        "variant_parallelism": vp,
        "generate_images": gi,
        "compare_max_chars": int(compare_max_chars),
    }


def _load_template_library(project_types: list[str]) -> dict[str, dict[str, Any]]:
    try:
        from backend.zhifei_autoplan.project_types import project_type_requirements
    except Exception:
        project_type_requirements = None

    library: dict[str, dict[str, Any]] = {}
    for tp in project_types:
        reqs: list[str] = []
        if callable(project_type_requirements):
            try:
                reqs = [str(x) for x in (project_type_requirements(tp) or []) if str(x).strip()]
            except Exception:
                reqs = []
        if not reqs:
            reqs = ["质量、安全、环保按“控制点→标准→指标→频率→责任位”闭环表达，且可追溯。"]
        library[tp] = {
            "label": tp,
            "desc": f"{tp}专项逻辑模板：不改招标目录，只约束章内逻辑与量化指标。",
            "project_type": tp,
            "topic_hint": f"{tp}施工组织设计",
            "requirements": reqs,
            "outline": [],
            "chapter_requirements": {},
            "params_override": {},
        }

    if "市政道路" in library:
        library["市政道路"]["params_override"] = {
            "quant_defaults": {
                "频次": "3次/日",
                "阈值": "偏差≤5mm",
                "间距": "50m",
                "厚度": "18cm",
                "时长": "6h/作业段",
                "人数": "12人/班",
                "设备型号": "20t压路机1台",
            }
        }
    if "市政桥梁" in library:
        library["市政桥梁"]["params_override"] = {
            "quant_defaults": {
                "频次": "2次/班",
                "阈值": "偏差≤3mm",
                "间距": "1.5m",
                "厚度": "80mm",
                "时长": "8h/作业段",
                "人数": "16人/班",
                "设备型号": "80t汽车吊1台",
            }
        }
    if "水利水电" in library:
        library["水利水电"]["params_override"] = {
            "quant_defaults": {
                "频次": "3次/班",
                "阈值": "渗压变化≤10%",
                "间距": "2m",
                "厚度": "30cm",
                "时长": "8h/作业段",
                "人数": "14人/班",
                "设备型号": "150kW水泵2台",
            }
        }
    return library


TEMPLATE_LIBRARY = _load_template_library(PROJECT_TYPES)


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _safe_project_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        s = datetime.now().strftime("project_%Y%m%d_%H%M%S")
    s = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", s).strip("_")
    return s[:96] or datetime.now().strftime("project_%Y%m%d_%H%M%S")


def _topic_from_project_name(project_name: str | None) -> str:
    name = str(project_name or "").strip()
    if not name:
        return ""
    if name.endswith("施工组织设计"):
        return name
    return f"{name}施工组织设计"


def _extract_project_meta_from_tender(matrix: dict[str, Any] | None) -> tuple[str, str]:
    if not isinstance(matrix, dict):
        return "", ""
    project_name = str(matrix.get("project_name") or "").strip()
    project_code = str(matrix.get("project_code") or "").strip()
    return project_name, project_code


def _apply_project_defaults_from_tender(matrix: dict[str, Any] | None) -> tuple[str, str]:
    project_name, project_code = _extract_project_meta_from_tender(matrix)
    return _topic_from_project_name(project_name), project_code


def _detect_project_type_from_tender(matrix: dict[str, Any] | None) -> str:
    if not isinstance(matrix, dict):
        return ""
    try:
        from backend.zhifei_autoplan.project_types import detect_project_type, normalize_project_type
    except Exception:
        return ""
    direct = normalize_project_type(matrix.get("project_type"))
    if direct:
        return str(direct)
    detected = detect_project_type(
        topic=str(matrix.get("project_name") or ""),
        outline=[str(x) for x in (matrix.get("outline") or []) if str(x).strip()],
        tender=matrix,
    )
    normalized = normalize_project_type(detected)
    return str(normalized or "")


def _ui_font_name(v: Any) -> str:
    s = str(v or "").strip()
    if s in {"SimSun", "宋体"}:
        return "宋体"
    if s in {"仿宋", "仿宋体", "FangSong"}:
        return "仿宋体"
    return "宋体" if "宋" in s else ("仿宋体" if "仿宋" in s else "宋体")


def _page_target(v: Any) -> int | None:
    if isinstance(v, dict):
        v = v.get("target") or v.get("pages") or v.get("page_target") or v.get("max")
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def _normalize_front_matter_page_mode(raw: Any) -> str:
    mode = str(raw or "").strip().lower()
    return "exclude" if mode == "exclude" else "include"


def _normalize_full_index_enabled(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on", "enable", "enabled"}


def _build_front_matter_plan(
    document_total_target: int,
    *,
    cover_page_count: Any,
    full_index_page_count: Any,
    full_index_enabled: Any,
    toc_page_count: Any,
    front_matter_page_mode: Any,
) -> dict[str, Any]:
    total_target = max(1, int(document_total_target or 1))
    cover_pages = max(1, int(_page_target(cover_page_count) or FIXED_COVER_PAGES))
    configured_index_pages = max(1, int(_page_target(full_index_page_count) or DEFAULT_FULL_INDEX_PAGES))
    index_enabled = _normalize_full_index_enabled(full_index_enabled)
    toc_pages = max(1, int(_page_target(toc_page_count) or 2))
    count_mode = _normalize_front_matter_page_mode(front_matter_page_mode)
    front_without_index = cover_pages + toc_pages
    full_index_pages = configured_index_pages if index_enabled else 0
    front_actual = front_without_index + full_index_pages
    front_reserved = front_actual if count_mode == "include" else 0
    chapter_budget = total_target - front_reserved if count_mode == "include" else total_target
    front_matter_overflow = chapter_budget < 1
    chapter_budget = max(1, chapter_budget)
    effective_document_pages = (
        total_target
        if count_mode == "include" and not front_matter_overflow
        else chapter_budget + front_actual
    )
    return {
        "document_total_target": total_target,
        "cover_pages": cover_pages,
        "configured_index_pages": configured_index_pages,
        "full_index_enabled": index_enabled,
        "toc_pages": toc_pages,
        "count_mode": count_mode,
        "full_index_pages": full_index_pages,
        "front_matter_actual": front_actual,
        "front_matter_reserved": front_reserved,
        "chapter_page_budget": chapter_budget,
        "effective_document_pages": int(effective_document_pages),
        "front_matter_overflow": front_matter_overflow,
    }


def _build_front_matter_outline(
    outline: list[str],
    *,
    chapter_pages: dict[str, Any] | None,
    front_plan: dict[str, Any],
) -> dict[str, Any]:
    titles = [str(x).strip() for x in (outline or []) if str(x).strip()]
    cover_pages = max(1, int(front_plan.get("cover_pages") or FIXED_COVER_PAGES))
    toc_pages = max(1, int(front_plan.get("toc_pages") or 2))
    full_index_pages = max(0, int(front_plan.get("full_index_pages") or 0))
    body_start_page = cover_pages + full_index_pages + toc_pages + 1
    current_page = int(body_start_page)
    chapter_page_map = chapter_pages if isinstance(chapter_pages, dict) else {}
    toc_entries: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []
    for idx, title in enumerate(titles, start=1):
        planned_pages = max(1, int(_page_target(chapter_page_map.get(title)) or 1))
        toc_entry = {
            "order": idx,
            "title": title,
            "start_page": current_page,
            "planned_pages": planned_pages,
        }
        toc_entries.append(toc_entry)
        index_entries.append(
            {
                "order": idx,
                "title": title,
                "summary": f"{idx:02d}. {title}（约{planned_pages}页）",
                "start_page": current_page,
                "planned_pages": planned_pages,
            }
        )
        current_page += planned_pages
    sequence = [f"封面{cover_pages}页"]
    if full_index_pages > 0:
        sequence.append(f"全文索引{full_index_pages}页")
    sequence.append(f"目录{toc_pages}页")
    sequence.append("正文")
    return {
        "cover_pages": cover_pages,
        "toc_pages": toc_pages,
        "configured_index_pages": int(front_plan.get("configured_index_pages") or DEFAULT_FULL_INDEX_PAGES),
        "full_index_enabled": bool(front_plan.get("full_index_enabled")),
        "full_index_pages": full_index_pages,
        "count_mode": str(front_plan.get("count_mode") or "include"),
        "document_total_target": int(front_plan.get("document_total_target") or 0),
        "effective_document_pages": int(front_plan.get("effective_document_pages") or 0),
        "body_start_page": int(body_start_page),
        "chapter_count": len(toc_entries),
        "sequence": sequence,
        "toc_entries": toc_entries,
        "index_entries": index_entries,
    }


def _resolve_style_for_ui(user_style: dict[str, Any] | None, tender_style: dict[str, Any] | None) -> dict[str, Any]:
    try:
        from backend.zhifei_autoplan.style_policy import resolve_style

        style, _ = resolve_style(user_style=user_style or {}, tender_style=tender_style or {})
        return style if isinstance(style, dict) else {}
    except Exception:
        fallback = {
            "body_font": "宋体",
            "title_font": "宋体",
            "body_size": 14,
            "title_size": 16,
            "line_spacing_pt": 22.0,
            "margins_cm": {"top": 2.5, "right": 2.0, "bottom": 2.0, "left": 2.0},
            "chart_policy": {"enabled": True, "mode": "page_density_auto", "every_n_chapters": 2, "position": "chapter"},
            "cover_page_count": FIXED_COVER_PAGES,
            "full_index_enabled": False,
            "full_index_page_count": DEFAULT_FULL_INDEX_PAGES,
            "toc_page_count": 2,
            "front_matter_page_mode": "include",
        }
        if isinstance(user_style, dict):
            for key in ("cover_page_count", "full_index_enabled", "full_index_page_count", "toc_page_count", "front_matter_page_mode"):
                if key in user_style:
                    fallback[key] = user_style[key]
        return fallback


def _resolve_style_for_ui_with_source(
    user_style: dict[str, Any] | None,
    tender_style: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    try:
        from backend.zhifei_autoplan.style_policy import resolve_style

        style, source = resolve_style(user_style=user_style or {}, tender_style=tender_style or {})
        return (style if isinstance(style, dict) else {}), str(source or "default_or_user")
    except Exception:
        return _resolve_style_for_ui(user_style, tender_style), "default_or_user"


def _plan_outline_pages_and_chart(
    outline: list[str],
    *,
    project_type: str,
    chapter_pages: dict[str, Any] | None,
    tender_matrix: dict[str, Any] | None,
    total_pages_target: int | None = None,
    strict_outline: bool = False,
    cover_page_count: Any = FIXED_COVER_PAGES,
    full_index_page_count: Any = DEFAULT_FULL_INDEX_PAGES,
    full_index_enabled: Any = False,
    toc_page_count: Any = 2,
    front_matter_page_mode: Any = "include",
) -> tuple[list[str], dict[str, int], int, dict[str, Any]]:
    titles = [str(x).strip() for x in (outline or []) if str(x).strip()]
    if not titles:
        empty_plan = _build_front_matter_plan(
            int(total_pages_target or 50),
            cover_page_count=cover_page_count,
            full_index_page_count=full_index_page_count,
            full_index_enabled=full_index_enabled,
            toc_page_count=toc_page_count,
            front_matter_page_mode=front_matter_page_mode,
        )
        return [], {}, 2, empty_plan
    try:
        from backend.zhifei_autoplan.outline_planner import (
            enrich_outline,
            infer_total_page_limit,
            plan_chapter_pages,
            recommend_chart_every_n,
        )

        tender = tender_matrix if isinstance(tender_matrix, dict) else {}
        if strict_outline:
            # 严格模式：目录必须与评审标准一致，不做自动补章。
            enriched = list(titles)
        else:
            enriched = enrich_outline(titles, project_type=project_type)
        total_limit = infer_total_page_limit(tender, default=50, override=total_pages_target)
        front_plan = _build_front_matter_plan(
            int(total_limit),
            cover_page_count=cover_page_count,
            full_index_page_count=full_index_page_count,
            full_index_enabled=full_index_enabled,
            toc_page_count=toc_page_count,
            front_matter_page_mode=front_matter_page_mode,
        )
        planned = plan_chapter_pages(
            enriched,
            total_pages=int(front_plan["chapter_page_budget"]),
            chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
        )
        chart_n = recommend_chart_every_n(enriched, planned)
        return enriched, planned, int(chart_n), front_plan
    except Exception:
        out = {}
        for t in titles:
            out[t] = int(_page_target((chapter_pages or {}).get(t)) or 2)
        fallback_total = int(total_pages_target or sum(out.values()) or 50)
        front_plan = _build_front_matter_plan(
            fallback_total,
            cover_page_count=cover_page_count,
            full_index_page_count=full_index_page_count,
            full_index_enabled=full_index_enabled,
            toc_page_count=toc_page_count,
            front_matter_page_mode=front_matter_page_mode,
        )
        return titles, out, 2, front_plan


def _apply_style_to_session(style: dict[str, Any], *, queue_only: bool = True) -> None:
    if not isinstance(style, dict):
        return

    font_cfg = style.get("font") if isinstance(style.get("font"), dict) else {}

    def _set(key: str, value: Any) -> None:
        if queue_only:
            _queue_widget_update(key, value)
        else:
            st.session_state[key] = value

    body_font = _ui_font_name(style.get("body_font") or font_cfg.get("eastAsia"))
    title_font = _ui_font_name(style.get("title_font") or body_font)
    _set("body_font", body_font)
    _set("title_font", title_font)
    try:
        _set("body_size", int(round(float(style.get("body_size") or 14))))
    except Exception:
        _set("body_size", 14)
    try:
        _set("title_size", int(round(float(style.get("title_size") or 16))))
    except Exception:
        _set("title_size", 16)

    line_spacing_pt = style.get("line_spacing_pt")
    if line_spacing_pt is None and font_cfg:
        line_spacing_pt = font_cfg.get("line_spacing_pt")
    try:
        _set("line_spacing_pt", float(line_spacing_pt if line_spacing_pt is not None else 22.0))
    except Exception:
        _set("line_spacing_pt", 22.0)

    margins = style.get("margins_cm") if isinstance(style.get("margins_cm"), dict) else {}
    _set("margin_top_cm", float(margins.get("top") or 2.5))
    _set("margin_right_cm", float(margins.get("right") or 2.0))
    _set("margin_bottom_cm", float(margins.get("bottom") or 2.0))
    _set("margin_left_cm", float(margins.get("left") or 2.0))

    cp = style.get("chart_policy") if isinstance(style.get("chart_policy"), dict) else {}
    _set("chart_enabled", bool(cp.get("enabled", True)))
    _set("chart_mode", str(cp.get("mode") or "page_density_auto"))
    try:
        _set("chart_every_n", int(cp.get("every_n_chapters") or 2))
    except Exception:
        _set("chart_every_n", 2)
    _set("chart_position", str(cp.get("position") or "chapter"))
    if style.get("toc_page_count") is not None:
        _set("toc_page_count", max(1, int(_page_target(style.get("toc_page_count")) or 2)))
    if style.get("cover_page_count") is not None:
        _set("cover_page_count", max(1, int(_page_target(style.get("cover_page_count")) or FIXED_COVER_PAGES)))
    if style.get("full_index_enabled") is not None:
        _set("full_index_enabled", _normalize_full_index_enabled(style.get("full_index_enabled")))
    if style.get("full_index_page_count") is not None:
        _set(
            "full_index_page_count",
            max(1, int(_page_target(style.get("full_index_page_count")) or DEFAULT_FULL_INDEX_PAGES)),
        )
    if style.get("front_matter_page_mode") is not None:
        _set("front_matter_page_mode", _normalize_front_matter_page_mode(style.get("front_matter_page_mode")))


def _queue_widget_update(key: str, value: Any) -> None:
    updates = st.session_state.setdefault("_pending_widget_updates", {})
    if not isinstance(updates, dict):
        updates = {}
    updates[str(key)] = value
    st.session_state["_pending_widget_updates"] = updates


def _apply_pending_widget_updates() -> None:
    updates = st.session_state.pop("_pending_widget_updates", {})
    if not isinstance(updates, dict):
        return
    for k, v in updates.items():
        st.session_state[k] = v


def _headers(actions_key: str) -> dict[str, str]:
    return {"X-Actions-Key": actions_key.strip()}


def _admin_headers(admin_key: str) -> dict[str, str]:
    token = str(admin_key or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _current_session_id() -> str:
    return str(st.session_state.get("session_id") or "").strip()


def _current_workspace_dir() -> str:
    return str(st.session_state.get("workspace_dir") or "").strip()


def _workspace_context_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "session_id": _current_session_id(),
        "workspace_dir": _current_workspace_dir(),
    }
    if isinstance(extra, dict):
        for key, value in extra.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            params[str(key)] = value
    return params


def _workspace_context_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(payload or {})
    merged["session_id"] = _current_session_id()
    merged["workspace_dir"] = _current_workspace_dir()
    return merged


def _backend_identity_check(base_url: str, expected_system_id: str) -> tuple[bool, str]:
    try:
        r = requests.get(base_url.rstrip("/") + "/health", timeout=3)
        if r.status_code >= 400:
            return True, ""
        js = r.json() if "application/json" in (r.headers.get("content-type") or "").lower() else {}
        sid = str((js or {}).get("system_id") or "").strip()
        service = str((js or {}).get("service") or "").strip()
        if sid and sid != expected_system_id:
            return False, f"检测到后端 system_id={sid}，期望={expected_system_id}"
        if (not sid) and service and service != "文档生成系统":
            return False, f"检测到后端 service={service}，非文档生成系统"
        return True, ""
    except Exception:
        # 后端不可达交给后续按钮操作时再提示，不在页面初始阶段阻断。
        return True, ""


def _json_pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _parse_json_text(label: str, text: str) -> dict[str, Any] | None:
    txt = (text or "").strip()
    if not txt:
        return None
    try:
        obj = json.loads(txt)
    except Exception as e:
        raise ValueError(f"{label} 不是合法 JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError(f"{label} 必须是 JSON 对象")
    return obj


def _post_files(
    base_url: str,
    path: str,
    actions_key: str,
    field: str,
    uploaded_files: list[Any],
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    files = []
    for uf in uploaded_files:
        files.append((field, (uf.name, uf.getvalue(), "application/octet-stream")))
    resp = requests.post(
        base_url.rstrip("/") + path,
        headers=_headers(actions_key),
        params=_workspace_context_params(params),
        files=files,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(_http_error_text(path, resp))
    return resp.json()


def _http_error_text(path: str, resp: requests.Response) -> str:
    payload: dict[str, Any] | None = None
    try:
        raw = resp.json()
        payload = raw if isinstance(raw, dict) else None
    except Exception:
        payload = None
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("code") or "").strip()
        next_action = str(detail.get("next_action") or "").strip()
        warnings = detail.get("warnings") if isinstance(detail.get("warnings"), list) else []
        pieces: list[str] = []
        if message:
            pieces.append(message)
        if next_action and next_action != "accept":
            pieces.append(f"建议动作：{next_action}")
        for item in warnings[:2]:
            if not isinstance(item, dict):
                continue
            warning_message = str(item.get("message") or "").strip()
            if warning_message:
                pieces.append(warning_message)
        if pieces:
            return f"{path} 失败: {resp.status_code} {'；'.join(pieces)}"
    if isinstance(detail, str) and detail.strip():
        return f"{path} 失败: {resp.status_code} {detail.strip()}"
    message = str((payload or {}).get("message") or "").strip() if isinstance(payload, dict) else ""
    if message:
        return f"{path} 失败: {resp.status_code} {message}"
    return f"{path} 失败: {resp.status_code} {resp.text[:400]}"


def _post_json(
    base_url: str,
    path: str,
    actions_key: str,
    payload: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    resp = requests.post(
        base_url.rstrip("/") + path,
        headers={**_headers(actions_key), "Content-Type": "application/json"},
        params=_workspace_context_params(params),
        json=_workspace_context_payload(payload),
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(_http_error_text(path, resp))
    return resp.json()


def _get_json(
    base_url: str,
    path: str,
    actions_key: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    resp = requests.get(
        base_url.rstrip("/") + path,
        headers=_headers(actions_key),
        params=_workspace_context_params(params),
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(_http_error_text(path, resp))
    return resp.json()


def _get_admin_json(
    base_url: str,
    path: str,
    admin_key: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    resp = requests.get(
        base_url.rstrip("/") + path,
        headers=_admin_headers(admin_key),
        params=params,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(_http_error_text(path, resp))
    return resp.json()


def _post_admin_json(
    base_url: str,
    path: str,
    admin_key: str,
    payload: dict[str, Any],
    *,
    timeout: int = 120,
) -> dict[str, Any]:
    resp = requests.post(
        base_url.rstrip("/") + path,
        headers={**_admin_headers(admin_key), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(_http_error_text(path, resp))
    return resp.json()


def _download_bytes(
    base_url: str,
    actions_key: str,
    job_id: str,
    kind: str,
    variant: int,
    *,
    timeout: int = 600,
) -> bytes:
    resp = requests.get(
        base_url.rstrip("/") + "/actions/download",
        headers=_headers(actions_key),
        params=_workspace_context_params({"job_id": job_id, "kind": kind, "variant": variant}),
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"下载 {kind} v{variant} 失败: {resp.status_code} {resp.text[:300]}")
    return resp.content


def _render_active_kg_panel(base_url: str, actions_key: str) -> None:
    with st.container(border=True):
        st.markdown("**D. 当前激活 KG**")
        st.caption("只读展示 8010 当前激活的知识图谱，不影响主流程生成。")
        active: dict[str, Any] | None = None
        try:
            payload = _get_json(base_url, "/autoplan/kg/active", actions_key, timeout=20)
            active = payload.get("active") if isinstance(payload, dict) else None
        except Exception as e:
            st.warning("当前激活 KG 读取失败")
            st.caption(str(e))
        kg_id = str((active or {}).get("kg_id") or "").strip() if isinstance(active, dict) else ""
        if not isinstance(active, dict) or not kg_id:
            st.info("当前未激活知识图谱")
        else:
            file_name = str(active.get("file_name") or "未命名图谱").strip() or "未命名图谱"
            uploaded_at = str(active.get("uploaded_at") or "").strip() or "未记录"
            stored_as = str(active.get("stored_as") or "").strip() or "未记录"

            st.markdown(f"**{file_name}**")
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"kg_id：`{kg_id}`")
                st.caption(f"uploaded_at：{uploaded_at}")
            with c2:
                st.caption(f"stored_as：{stored_as}")

        st.markdown("**KG 检索测试**")
        st.caption("直连 8010 的 /autoplan/kg/search，用于验证当前激活 KG 是否可检索。")
        q1, q2 = st.columns([6, 2], vertical_alignment="bottom")
        with q1:
            st.text_input(
                "query",
                key="kg_search_query",
                placeholder="例如：智飞工程 农民工工资专用账户 银行系统 劳务实名制",
            )
        with q2:
            st.number_input("top_k", min_value=1, max_value=20, key="kg_search_top_k")

        if st.button("测试检索", key="kg_search_run", width="stretch"):
            try:
                search_payload = _get_json(
                    base_url,
                    "/autoplan/kg/search",
                    actions_key,
                    params={
                        "q": str(st.session_state.get("kg_search_query") or "").strip(),
                        "top_k": int(st.session_state.get("kg_search_top_k") or 5),
                    },
                    timeout=30,
                )
                st.session_state["kg_search_last_response"] = search_payload if isinstance(search_payload, dict) else {}
                st.session_state["kg_search_last_error"] = ""
            except Exception as e:
                st.session_state["kg_search_last_response"] = {}
                st.session_state["kg_search_last_error"] = str(e)

        search_error = str(st.session_state.get("kg_search_last_error") or "").strip()
        if search_error:
            st.warning("KG 检索失败")
            st.caption(search_error)
            return

        search_payload = st.session_state.get("kg_search_last_response")
        if not isinstance(search_payload, dict):
            return
        results = search_payload.get("results")
        if not isinstance(results, list):
            results = []
        if not results:
            if search_payload:
                st.info("未命中知识图谱")
            return

        for idx, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "未命名结果").strip() or "未命名结果"
            score = item.get("score")
            path = str(item.get("path") or "").strip() or "$"
            preview = str(item.get("text") or "").strip().replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:220].rstrip() + "..."
            with st.container(border=True):
                st.markdown(f"**{idx}. {title}**")
                r1, r2 = st.columns(2)
                with r1:
                    st.caption(f"score：{score}")
                with r2:
                    st.caption(f"path：{path}")
                st.caption(preview or "无文本预览")


def _render_self_evolution_panel(base_url: str, actions_key: str) -> None:
    with st.container(border=True):
        st.markdown("**E. 自我进化（运行期学习）**")
        st.caption("只读展示运行期学习档案。当前阶段会学习章节预算、任务并发，以及高通过修订组合/语境组合包；不会自动改写目录、业务规则或 A/B/C/D/E 结构。")
        summary: dict[str, Any] | None = None
        try:
            payload = _get_json(base_url, "/actions/self_evolution/status", actions_key, params={"limit": 5}, timeout=20)
            summary = payload.get("self_evolution") if isinstance(payload, dict) else None
        except Exception as e:
            st.warning("自我进化状态读取失败")
            st.caption(str(e))
            return

        if not isinstance(summary, dict):
            st.info("当前暂无可用的运行期学习状态。")
            return

        enabled = bool(summary.get("enabled", False))
        updated_at = str(summary.get("updated_at") or "").strip() or "未记录"
        entry_count = int(summary.get("entry_count") or 0)
        profile_version = str(summary.get("profile_version") or "").strip() or "未记录"
        profile_path = str(summary.get("profile_path") or "").strip()
        maintenance = summary.get("maintenance") if isinstance(summary.get("maintenance"), dict) else {}

        c1, c2, c3 = st.columns(3)
        c1.metric("运行期学习", "已启用" if enabled else "未启用")
        c2.metric("样本条目", entry_count)
        c3.metric("Profile版本", profile_version)
        st.caption(f"最近更新时间：{updated_at}")
        if profile_path:
            st.caption(f"profile_path：{profile_path}")
        if maintenance:
            retained = int(maintenance.get("retained_entry_count") or 0)
            pruned = int(maintenance.get("pruned_entry_count") or 0)
            stale_pruned = int(maintenance.get("stale_pruned") or 0)
            overflow_pruned = int(maintenance.get("overflow_pruned") or 0)
            stale_days = int(maintenance.get("stale_days") or 0)
            if pruned > 0:
                st.caption(
                    f"样本治理：当前保留 {retained} 条；最近自动清理 {pruned} 条"
                    f"（过期低信号={stale_pruned}，超限收敛={overflow_pruned}，过期阈值={stale_days}天）"
                )
            else:
                st.caption(f"样本治理：当前保留 {retained} 条；最近未触发自动清理。")

        top_entries = summary.get("top_entries") if isinstance(summary.get("top_entries"), list) else []
        if not enabled:
            st.info("当前运行期学习已关闭。系统仍可正常生成，但不会根据历史运行结果自动微调章节预算。")
            return
        if not top_entries:
            st.info("当前尚未沉淀出可用的运行期学习样本。先完成几次真实生成后，这里会出现学习记录。")
            return

        st.caption("以下为最近最有代表性的学习样本：")
        for idx, row in enumerate(top_entries, start=1):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "未命名章节").strip() or "未命名章节"
            project_type = str(row.get("project_type") or "").strip()
            generation_mode = str(row.get("generation_mode") or "").strip()
            reason = str(row.get("last_runtime_budget_reason") or "").strip() or "未记录"
            key_alias = str(row.get("last_used_key_alias") or "").strip() or "未记录"
            runs = int(row.get("runs") or 0)
            success_rate = float(row.get("success_rate") or 0.0)
            fallback_runs = int(row.get("fallback_runs") or 0)
            quality_issue_runs = int(row.get("quality_issue_runs") or 0)
            compaction_runs = int(row.get("compaction_runs") or 0)
            avg_timeout = row.get("avg_timeout_sec")
            avg_tokens = row.get("avg_max_tokens")
            avg_retry = row.get("avg_retry_limit")
            indicator_groups = row.get("top_indicator_groups") if isinstance(row.get("top_indicator_groups"), list) else []
            strategy_ids = row.get("top_strategy_ids") if isinstance(row.get("top_strategy_ids"), list) else []
            action_tags = row.get("top_action_tags") if isinstance(row.get("top_action_tags"), list) else []
            context_signatures = row.get("top_context_signatures") if isinstance(row.get("top_context_signatures"), list) else []
            effective_combos = row.get("top_effective_combos") if isinstance(row.get("top_effective_combos"), list) else []
            effective_combo_bundles = row.get("top_effective_combo_bundles") if isinstance(row.get("top_effective_combo_bundles"), list) else []
            effective_context_bundles = row.get("top_effective_context_bundles") if isinstance(row.get("top_effective_context_bundles"), list) else []
            attributed_context_bundles = row.get("top_attributed_context_bundles") if isinstance(row.get("top_attributed_context_bundles"), list) else []
            metric_effects = row.get("top_metric_effects") if isinstance(row.get("top_metric_effects"), list) else []
            metric_action_effects = row.get("top_metric_action_effects") if isinstance(row.get("top_metric_action_effects"), list) else []
            with st.container(border=True):
                st.markdown(f"**{idx}. {title}**")
                st.caption(f"{project_type or '通用'} / {generation_mode or 'standard_auto'}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("历史运行", runs)
                m2.metric("成功率", f"{success_rate:.0%}")
                m3.metric("fallback", fallback_runs)
                m4.metric("质量问题", quality_issue_runs)
                st.caption(
                    "；".join(
                        [
                            f"压缩次数={compaction_runs}",
                            f"平均timeout={avg_timeout}",
                            f"平均tokens={avg_tokens}",
                            f"平均retry={avg_retry}",
                        ]
                    )
                )
                st.caption(f"最近预算原因：{reason}")
                st.caption(f"最近使用通道：{key_alias}")
                if indicator_groups:
                    st.caption("高频失败指标：" + "；".join([str(x) for x in indicator_groups[:3] if str(x).strip()]))
                if strategy_ids:
                    st.caption("高频修订策略：" + "；".join([str(x) for x in strategy_ids[:3] if str(x).strip()]))
                if action_tags:
                    st.caption("高频修订动作：" + "；".join([str(x) for x in action_tags[:3] if str(x).strip()]))
                if context_signatures:
                    st.caption("高频章节语境：" + "；".join([str(x) for x in context_signatures[:3] if str(x).strip()]))
                if effective_combos:
                    st.caption("高有效修订组合：" + "；".join([str(x) for x in effective_combos[:2] if str(x).strip()]))
                if effective_combo_bundles:
                    st.caption("高通过修订组合包：" + "；".join([str(x) for x in effective_combo_bundles[:2] if str(x).strip()]))
                if effective_context_bundles:
                    st.caption("高通过语境组合包：" + "；".join([str(x) for x in effective_context_bundles[:2] if str(x).strip()]))
                if attributed_context_bundles:
                    st.caption("高通过归因语境组合包：" + "；".join([str(x) for x in attributed_context_bundles[:2] if str(x).strip()]))
                if metric_effects:
                    st.caption("高频被拉平指标：" + "；".join([str(x) for x in metric_effects[:2] if str(x).strip()]))
                if metric_action_effects:
                    st.caption("高频被拉平动作组合：" + "；".join([str(x) for x in metric_action_effects[:2] if str(x).strip()]))


def _render_chief_agent_panel(base_url: str, actions_key: str) -> None:
    with st.container(border=True):
        st.markdown("**F. 常驻自治维护**")
        st.caption("只读展示后台常驻自治能力的健康状态。当前仅执行低风险维护：界面守护、job housekeep、自我进化 profile 维护、项目 watcher 轮询；不会在后台直接改正文。")
        try:
            payload = _get_json(base_url, "/actions/chief_agent/status", actions_key, timeout=20)
            summary = payload.get("chief_agent") if isinstance(payload, dict) else None
        except Exception as e:
            st.warning("常驻自治状态读取失败")
            st.caption(str(e))
            return
        try:
            watcher_payload = _get_json(base_url, "/actions/watcher/status", actions_key, timeout=20)
            watcher = watcher_payload.get("watcher") if isinstance(watcher_payload, dict) else None
        except Exception:
            watcher = None

        if not isinstance(summary, dict) or not summary:
            st.info("当前暂无可用的常驻自治状态。")
            return

        healthy = bool(summary.get("healthy", False))
        age_seconds = summary.get("age_seconds")
        last_action = str(summary.get("last_action") or "").strip() or "未记录"
        timestamp = str(summary.get("timestamp") or "").strip() or "未记录"
        c1, c2, c3 = st.columns(3)
        c1.metric("常驻自治", "正常" if healthy else "异常")
        c2.metric("最近动作", last_action)
        c3.metric("状态时效", f"{int(age_seconds)}s" if isinstance(age_seconds, int) else "未记录")
        st.caption(f"最近状态时间：{timestamp}")
        summary_line = str(summary.get("summary_line") or "").strip()
        if summary_line:
            st.caption(summary_line)
        recent_summary_line = str(summary.get("recent_summary_line") or "").strip()
        if recent_summary_line:
            st.caption("chief 最近概览：" + recent_summary_line)

        if isinstance(watcher, dict) and watcher:
            watcher_summary_line = str(watcher.get("summary_line") or "").strip()
            if watcher_summary_line:
                st.caption(watcher_summary_line)
            watcher_recent_summary_line = str(watcher.get("recent_summary_line") or "").strip()
            if watcher_recent_summary_line:
                st.caption("watcher 最近概览：" + watcher_recent_summary_line)

        with st.expander("自治维护详情", expanded=False):
            backend_ok = int(summary.get("backend_listener") or 0) == 1 and int(summary.get("backend_health") or 0) == 1
            web_ok = int(summary.get("web_listener") or 0) == 1 and int(summary.get("web_health") or 0) == 1
            st.caption(f"后端：{'正常' if backend_ok else '异常'}；前端：{'正常' if web_ok else '异常'}")

            job_housekeep = summary.get("job_housekeep") if isinstance(summary.get("job_housekeep"), dict) else {}
            if job_housekeep:
                st.caption(
                    "job housekeep："
                    f"stale_fixed={int(job_housekeep.get('stale_fixed') or 0)}；"
                    f"removed={int(job_housekeep.get('removed') or 0)}"
                )

            self_evolution = summary.get("self_evolution") if isinstance(summary.get("self_evolution"), dict) else {}
            if self_evolution:
                rt_text = f"runtime_profile={int(self_evolution.get('runtime_entry_count') or 0)}条"
                if bool(self_evolution.get("runtime_changed", False)):
                    rt_text += "（本轮有变更）"
                tp_text = f"task_profile={int(self_evolution.get('task_entry_count') or 0)}条"
                if bool(self_evolution.get("task_changed", False)):
                    tp_text += "（本轮有变更）"
                st.caption("self_evolution maintenance：" + rt_text + "；" + tp_text)

            recent = summary.get("recent") if isinstance(summary.get("recent"), list) else []
            if recent:
                st.caption("chief 最近摘要：")
                for item in recent[:3]:
                    if not isinstance(item, dict):
                        continue
                    ts = str(item.get("timestamp") or "").strip()
                    kind = str(item.get("kind") or "").strip()
                    text = str(item.get("summary") or "").strip()
                    if text:
                        st.caption(f"{ts} [{kind}] {text}".strip())

            if isinstance(watcher, dict) and watcher:
                watcher_healthy = bool(watcher.get("healthy", False))
                watcher_status = str(watcher.get("status") or "").strip() or "unknown"
                watcher_last_action = str(watcher.get("last_action") or "").strip() or "未记录"
                watcher_age = watcher.get("age_seconds")
                st.caption(
                    "watcher："
                    f"{'正常' if watcher_healthy else '异常'}；"
                    f"status={watcher_status}；"
                    f"最近动作={watcher_last_action}；"
                    f"时效={str(int(watcher_age)) + 's' if isinstance(watcher_age, int) else '未记录'}"
                )
                last_project_name = str(watcher.get("last_project_name") or "").strip()
                if last_project_name:
                    st.caption(f"watcher 最近项目：{last_project_name}")
                last_error = str(watcher.get("last_error") or "").strip()
                if last_error:
                    st.caption(f"watcher 最近错误：{last_error}")
                watcher_recent = watcher.get("recent") if isinstance(watcher.get("recent"), list) else []
                if watcher_recent:
                    st.caption("watcher 最近摘要：")
                    for item in watcher_recent[:3]:
                        if not isinstance(item, dict):
                            continue
                        ts = str(item.get("timestamp") or "").strip()
                        kind = str(item.get("kind") or "").strip()
                        text = str(item.get("summary") or "").strip()
                        if text:
                            st.caption(f"{ts} [{kind}] {text}".strip())


def _load_runtime_presence_summary(base_url: str, actions_key: str) -> dict[str, Any]:
    chief: dict[str, Any] = {}
    watcher: dict[str, Any] = {}
    try:
        payload = _get_json(base_url, "/actions/chief_agent/status", actions_key, timeout=20)
        chief = payload.get("chief_agent") if isinstance(payload, dict) and isinstance(payload.get("chief_agent"), dict) else {}
    except Exception:
        chief = {}
    try:
        payload = _get_json(base_url, "/actions/watcher/status", actions_key, timeout=20)
        watcher = payload.get("watcher") if isinstance(payload, dict) and isinstance(payload.get("watcher"), dict) else {}
    except Exception:
        watcher = {}

    backend_ok = bool(chief) and int(chief.get("backend_listener") or 0) == 1 and int(chief.get("backend_health") or 0) == 1
    chief_ok = bool(chief) and bool(chief.get("healthy", False))
    watcher_ok = bool(watcher) and bool(watcher.get("healthy", False))
    service_ok = backend_ok or chief_ok or watcher_ok

    detail_parts: list[str] = []
    if chief:
        detail_parts.append(f"后端：{'在线' if backend_ok else '异常'}")
        detail_parts.append(f"chief：{'在线' if chief_ok else '异常'}")
    if watcher:
        detail_parts.append(f"watcher：{'在线' if watcher_ok else '异常'}")

    return {
        "service_ok": service_ok,
        "notice_text": "服务在线，当前无生成任务" if service_ok else "当前无运行中任务",
        "detail_line": "；".join(detail_parts),
    }


def _build_kg_trace_query(
    *,
    topic: str,
    requirements: list[str] | None = None,
    global_instruction: str | None = None,
    outline: list[str] | None = None,
) -> str:
    parts: list[str] = []
    topic_text = str(topic or "").strip()
    if topic_text:
        parts.append(topic_text)
    for line in list(requirements or [])[:2]:
        txt = str(line or "").strip()
        if txt:
            parts.append(txt)
    for title in list(outline or [])[:2]:
        txt = str(title or "").strip()
        if txt:
            parts.append(txt)
    global_text = str(global_instruction or "").strip()
    if global_text:
        parts.append(global_text[:60])
    query = " ".join([x for x in parts if x]).strip()
    return query[:240]


def _sample_kg_trace(
    base_url: str,
    actions_key: str,
    *,
    topic: str,
    project_id: str,
    requirements: list[str] | None = None,
    global_instruction: str | None = None,
    outline: list[str] | None = None,
    top_k: int = 3,
) -> dict[str, Any]:
    sample: dict[str, Any] = {
        "status": "idle",
        "job_id": "",
        "project_id": str(project_id or "").strip(),
        "topic": str(topic or "").strip(),
        "query": _build_kg_trace_query(
            topic=topic,
            requirements=requirements,
            global_instruction=global_instruction,
            outline=outline,
        ),
        "top_k": max(1, int(top_k or 3)),
        "active": None,
        "results": [],
        "hit_count": 0,
        "error": "",
        "captured_at": _now(),
        "note": "辅助留痕，不代表后端唯一引用源。",
    }
    try:
        active_payload = _get_json(base_url, "/autoplan/kg/active", actions_key, timeout=20)
        sample["active"] = active_payload.get("active") if isinstance(active_payload, dict) else None
        search_payload = _get_json(
            base_url,
            "/autoplan/kg/search",
            actions_key,
            params={
                "q": sample["query"],
                "top_k": int(sample["top_k"]),
            },
            timeout=30,
        )
        results = search_payload.get("results") if isinstance(search_payload, dict) else []
        if not isinstance(results, list):
            results = []
        sample["results"] = [x for x in results if isinstance(x, dict)]
        sample["hit_count"] = len(sample["results"])
        sample["status"] = "ok"
        return sample
    except Exception as e:
        sample["status"] = "error"
        sample["error"] = str(e)
        return sample


def _render_kg_trace_assist_block() -> None:
    sample = st.session_state.get("kg_trace_sample")
    result = st.session_state.get("run_result") or {}
    if not isinstance(sample, dict):
        return
    sample_job_id = str(sample.get("job_id") or "").strip()
    result_job_id = str(result.get("job_id") or "").strip()
    if result_job_id and sample_job_id and result_job_id != sample_job_id:
        return

    with st.container(border=True):
        st.markdown("**KG证据留痕（辅助）**")
        st.caption("辅助留痕，不代表后端唯一引用源。")

        if str(sample.get("status") or "").strip() == "error":
            st.warning("KG 证据采样失败")
            err = str(sample.get("error") or "").strip()
            if err:
                st.caption(err)
            return

        active = sample.get("active") if isinstance(sample.get("active"), dict) else None
        if isinstance(active, dict) and str(active.get("kg_id") or "").strip():
            st.markdown(f"**{str(active.get('file_name') or '未命名图谱').strip() or '未命名图谱'}**")
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"kg_id：`{str(active.get('kg_id') or '').strip()}`")
                st.caption(f"uploaded_at：{str(active.get('uploaded_at') or '').strip() or '未记录'}")
            with c2:
                st.caption(f"stored_as：{str(active.get('stored_as') or '').strip() or '未记录'}")
        else:
            st.caption("当前未激活知识图谱")

        st.caption(f"本次采样 query：{str(sample.get('query') or '').strip() or '（空）'}")
        st.caption(f"命中数量：{int(sample.get('hit_count') or 0)}")

        results = sample.get("results") if isinstance(sample.get("results"), list) else []
        if not results:
            st.info("本次生成前未命中知识图谱")
            return

        for idx, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "未命名结果").strip() or "未命名结果"
            score = item.get("score")
            path = str(item.get("path") or "").strip() or "$"
            preview = str(item.get("text") or "").strip().replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:220].rstrip() + "..."
            with st.container(border=True):
                st.markdown(f"**{idx}. {title}**")
                r1, r2 = st.columns(2)
                with r1:
                    st.caption(f"score：{score}")
                with r2:
                    st.caption(f"path：{path}")
                st.caption(preview or "无文本预览")


def _ui_poll_timeout_seconds(poll_sec: float) -> float:
    try:
        p = float(poll_sec)
    except Exception:
        p = 2.0
    return max(3.0, min(8.0, p * 2.0))


def _ingest_docs(
    base_url: str,
    files: list[Any],
    project_id: str | None,
    source_hint: str | None = None,
    *,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not files:
        return {"saved": []}
    payload = []
    seen = set()
    for uf in files:
        key = (uf.name, len(uf.getvalue()))
        if key in seen:
            continue
        seen.add(key)
        payload.append(("files", (uf.name, uf.getvalue(), "application/octet-stream")))
    params: dict[str, Any] = {}
    pid = str(project_id or "").strip()
    if pid:
        params["project_id"] = pid
    if source_hint:
        params["source_hint"] = str(source_hint)
    if isinstance(extra_params, dict):
        for k, v in extra_params.items():
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            params[str(k)] = v
    resp = requests.post(
        base_url.rstrip("/") + "/ingest/upload",
        params=_workspace_context_params(params),
        files=payload,
        timeout=900,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"/ingest/upload 失败: {resp.status_code} {resp.text[:400]}")
    return resp.json()


class _MemoryUpload:
    def __init__(self, name: str, data: bytes):
        self.name = str(name or "upload.bin")
        self._data = data if isinstance(data, (bytes, bytearray)) else bytes(data or b"")

    def getvalue(self) -> bytes:
        return bytes(self._data)


def _infer_template_page_bucket_from_pages(page_count: Any) -> str:
    try:
        pages = int(float(page_count or 0))
    except Exception:
        pages = 0
    if pages <= 0:
        return TEMPLATE_PAGE_BUCKETS[0] if TEMPLATE_PAGE_BUCKETS else "50_pages"
    if pages <= 50:
        return "50_pages"
    if pages <= 200:
        return "le_200_pages"
    return "gt_200_pages"


def _infer_result_scene_tags(project_type: str | None, *parts: Any) -> list[str]:
    try:
        from backend.zhifei_autoplan.template_library import infer_template_scene_tags

        return infer_template_scene_tags(*parts, project_type=project_type)
    except Exception:
        return []


def _normalize_scene_tags_ui(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[，,、;；/\s]+", str(raw or "").strip())
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _format_iso_ts_short(raw: Any) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%m-%d %H:%M")
    except Exception:
        return txt.replace("T", " ")[:16]


def _format_ts_short(raw: Any) -> str:
    if raw is None:
        return ""
    try:
        if isinstance(raw, (int, float)):
            ts = float(raw)
        else:
            txt = str(raw or "").strip()
            if re.fullmatch(r"\d+(\.\d+)?", txt):
                ts = float(txt)
            else:
                return _format_iso_ts_short(raw)
        if ts > 0:
            return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
    except Exception:
        pass
    return _format_iso_ts_short(raw)


def _safe_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except Exception:
        return None
    return value


def _format_duration_short(raw: Any) -> str:
    seconds = _safe_float(raw)
    if seconds is None or seconds < 0:
        return ""
    total = int(round(seconds))
    if total < 60:
        return f"{total}秒"
    minutes, sec = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}分{sec:02d}秒" if sec else f"{minutes}分"
    hours, minute = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}时{minute:02d}分"
    days, hour = divmod(hours, 24)
    return f"{days}天{hour:02d}时"


def _admission_last_hour_usage(admission: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(admission, dict):
        return {}
    usage = admission.get("usage")
    if not isinstance(usage, dict):
        return {}
    profile = usage.get("usage_profile")
    if not isinstance(profile, dict):
        return {}
    windows = profile.get("windows")
    if not isinstance(windows, dict):
        return {}
    bucket = windows.get("last_hour")
    return bucket if isinstance(bucket, dict) else {}


def _render_admission_status(admission: dict[str, Any] | None) -> None:
    if not isinstance(admission, dict):
        return
    code = str(admission.get("code") or "").strip() or "accepted"
    warning_level = str(admission.get("warning_level") or "").strip() or "none"
    warnings = admission.get("warnings") if isinstance(admission.get("warnings"), list) else []
    degrade_plan = admission.get("degrade_plan") if isinstance(admission.get("degrade_plan"), dict) else {}
    usage_last_hour = _admission_last_hour_usage(admission)
    detail_lines: list[str] = []
    for item in warnings[:3]:
        if not isinstance(item, dict):
            continue
        message = str(item.get("message") or "").strip()
        if message:
            detail_lines.append(message)
    if degrade_plan.get("applied"):
        before_ap = int(degrade_plan.get("agent_parallelism_before") or 0)
        after_ap = int(degrade_plan.get("agent_parallelism_after") or 0)
        before_vp = int(degrade_plan.get("variant_parallelism_before") or 0)
        after_vp = int(degrade_plan.get("variant_parallelism_after") or 0)
        before_compare = int(degrade_plan.get("compare_max_chars_before") or 0)
        after_compare = int(degrade_plan.get("compare_max_chars_after") or 0)
        before_images = bool(degrade_plan.get("generate_images_before", False))
        after_images = bool(degrade_plan.get("generate_images_after", False))
        before_text_chain = str(degrade_plan.get("text_chain_profile_before") or "").strip()
        after_text_chain = str(degrade_plan.get("text_chain_profile_after") or "").strip()
        adjust_parts: list[str] = []
        if before_ap > 0 and after_ap > 0 and before_ap != after_ap:
            adjust_parts.append(f"章节并发 {before_ap}→{after_ap}")
        if before_vp > 0 and after_vp > 0 and before_vp != after_vp:
            adjust_parts.append(f"方案并发 {before_vp}→{after_vp}")
        if before_images and not after_images:
            adjust_parts.append("关闭图片生成")
        if before_compare > 0 and after_compare > 0 and before_compare != after_compare:
            adjust_parts.append(f"对比字数 {before_compare}→{after_compare}")
        if before_text_chain and after_text_chain and before_text_chain != after_text_chain:
            adjust_parts.append(f"文本链 {before_text_chain}→{after_text_chain}")
        if adjust_parts:
            detail_lines.insert(0, "本次任务已自动降并发：" + "，".join(adjust_parts))
    llm_calls = int(usage_last_hour.get("llm_call_count") or 0)
    total_tokens = int(usage_last_hour.get("total_tokens_total") or 0)
    queued_jobs = int(usage_last_hour.get("queued_jobs") or 0)
    rejected_jobs = int(usage_last_hour.get("rejected_jobs") or 0)
    if llm_calls > 0 or total_tokens > 0 or queued_jobs > 0 or rejected_jobs > 0:
        summary_parts: list[str] = []
        if llm_calls > 0:
            summary_parts.append(f"近1小时 LLM 调用 {llm_calls} 次")
        if total_tokens > 0:
            summary_parts.append(f"tokens={total_tokens}")
        if queued_jobs > 0:
            summary_parts.append(f"排队任务 {queued_jobs}")
        if rejected_jobs > 0:
            summary_parts.append(f"拒绝 {rejected_jobs}")
        detail_lines.append("；".join(summary_parts))
    if code != "accepted":
        message = str(admission.get("message") or "当前会话容量不足，请稍后再试。").strip()
        next_action = str(admission.get("next_action") or "").strip()
        st.warning(message)
        if next_action:
            st.caption(f"建议动作：{next_action}")
        for line in detail_lines:
            st.caption(line)
        return
    if warning_level not in {"notice", "warning"}:
        return
    headline = "当前会话接近容量阈值，本次任务可能排队更久。"
    if warning_level == "notice":
        headline = "当前会话资源占用偏高，请关注排队与 token 消耗。"
    st.warning(headline)
    for line in detail_lines:
        st.caption(line)


def _load_actions_quota_status(base_url: str, actions_key: str, *, force: bool = False) -> dict[str, Any]:
    now_ts = time.time()
    cached = st.session_state.get("_quota_status_cache")
    if (
        not force
        and isinstance(cached, dict)
        and str(cached.get("base_url") or "") == str(base_url)
        and str(cached.get("actions_key") or "") == str(actions_key)
        and float(cached.get("fetched_at") or 0.0) > 0
        and (now_ts - float(cached.get("fetched_at") or 0.0)) < 15.0
    ):
        return dict(cached.get("payload") or {})
    try:
        payload = _get_json(
            base_url,
            "/actions/usage_status",
            actions_key,
            params={"requested_jobs": 1},
            timeout=20,
        )
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
    st.session_state["_quota_status_cache"] = {
        "base_url": str(base_url),
        "actions_key": str(actions_key),
        "fetched_at": now_ts,
        "payload": payload,
    }
    return dict(payload or {})


def _render_quota_status_panel(base_url: str, actions_key: str) -> None:
    payload = _load_actions_quota_status(base_url, actions_key)
    if not isinstance(payload, dict):
        return
    if not bool(payload.get("ok")):
        error = str(payload.get("error") or "").strip()
        if error:
            with st.container(border=True):
                st.caption("当前会话容量状态")
                st.caption(f"状态读取失败：{error}")
        return
    admission = payload.get("admission") if isinstance(payload.get("admission"), dict) else {}
    usage = admission.get("usage") if isinstance(admission.get("usage"), dict) else {}
    limits = admission.get("limits") if isinstance(admission.get("limits"), dict) else {}
    last_hour = _admission_last_hour_usage(admission)

    def _limit_text(value: Any) -> str:
        try:
            return str(int(value))
        except Exception:
            return "∞"

    running_count = int(usage.get("running_count") or 0)
    queued_count = int(usage.get("queued_count") or 0)
    active_count = int(usage.get("active_count") or 0)
    total_tokens = int(last_hour.get("total_tokens_total") or 0)
    llm_calls = int(last_hour.get("llm_call_count") or 0)
    warning_level = str(admission.get("warning_level") or "").strip() or "none"
    code = str(admission.get("code") or "").strip() or "accepted"
    source_line = "策略版本：{version} · 来源：{source}".format(
        version=str(limits.get("config_version") or "-").strip(),
        source=str(limits.get("policy_source") or "-").strip(),
    )
    with st.container(border=True):
        st.caption("当前会话容量状态")
        c1, c2, c3 = st.columns(3)
        c1.metric("运行中", f"{running_count} / {_limit_text(limits.get('running_limit'))}")
        c2.metric("排队中", f"{queued_count} / {_limit_text(limits.get('queued_limit'))}")
        c3.metric("活跃任务", f"{active_count} / {_limit_text(limits.get('active_limit'))}")
        st.caption(source_line)
        st.caption(f"近1小时：LLM 调用 {llm_calls} 次 · tokens={total_tokens}")
        if code != "accepted":
            st.caption(f"当前准入状态：{str(admission.get('message') or code).strip()}")
        elif warning_level in {"notice", "warning"}:
            st.caption("当前已接近容量阈值，继续提交任务可能排队更久。")


def _admin_ops_last_hour(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    last_hour = summary.get("last_hour")
    return last_hour if isinstance(last_hour, dict) else {}


def _admin_ops_dashboard_payload(
    base_url: str,
    admin_key: str,
    *,
    tenant_limit: int,
    keep_latest: int,
    older_than_hours: int,
    snapshot_export_limit: int,
    export_format: str = "",
    force: bool = False,
) -> dict[str, Any]:
    normalized_key = str(admin_key or "").strip()
    if not normalized_key:
        return {"ok": False, "error": "请输入 Admin Key 后再读取运营管理台。"}
    normalized_tenant_limit = max(1, min(50, int(tenant_limit or 10)))
    normalized_keep_latest = max(0, min(500, int(keep_latest or 20)))
    normalized_older_than_hours = max(0, min(24 * 365, int(older_than_hours or 168)))
    normalized_snapshot_export_limit = max(1, min(100, int(snapshot_export_limit or 20)))
    normalized_export_format = str(export_format or "").strip().lower()
    if normalized_export_format not in {"", "csv", "json"}:
        normalized_export_format = ""
    key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
    cache = st.session_state.get("_admin_ops_dashboard_cache")
    now_ts = time.time()
    if (
        not force
        and isinstance(cache, dict)
        and str(cache.get("base_url") or "") == str(base_url)
        and str(cache.get("key_hash") or "") == key_hash
        and int(cache.get("tenant_limit") or 0) == normalized_tenant_limit
        and int(cache.get("keep_latest") or 0) == normalized_keep_latest
        and int(cache.get("older_than_hours") or 0) == normalized_older_than_hours
        and int(cache.get("snapshot_export_limit") or 0) == normalized_snapshot_export_limit
        and str(cache.get("export_format") or "") == normalized_export_format
        and (now_ts - float(cache.get("fetched_at") or 0.0)) < 30.0
    ):
        return dict(cache.get("payload") or {})

    payload: dict[str, Any] = {
        "ok": True,
        "errors": [],
        "tenant_reports": None,
        "exports_summary": None,
        "snapshot_export_summary": None,
    }
    try:
        payload["tenant_reports"] = _get_admin_json(
            base_url,
            "/auth/tenant_usage_reports",
            normalized_key,
            params={
                "limit": normalized_tenant_limit,
                "window_limit": max(50, normalized_tenant_limit * 5),
                "sort_by": "charge_cost_total",
                "sort_order": "desc",
            },
            timeout=30,
        )
    except Exception as exc:
        payload["errors"].append(f"租户报表读取失败：{exc}")
    try:
        payload["exports_summary"] = _get_admin_json(
            base_url,
            "/auth/tenant_usage_reports_exports_summary",
            normalized_key,
            params={
                "export_format": normalized_export_format,
                "keep_latest": normalized_keep_latest,
                "older_than_hours": normalized_older_than_hours,
            },
            timeout=30,
        )
    except Exception as exc:
        payload["errors"].append(f"导出资产总览读取失败：{exc}")
    try:
        payload["snapshot_export_summary"] = _get_admin_json(
            base_url,
            "/auth/tenant_usage_reports_exports_summary_snapshot_exports_summary",
            normalized_key,
            params={
                "limit": normalized_snapshot_export_limit,
                "keep_latest": normalized_keep_latest,
                "older_than_hours": normalized_older_than_hours,
            },
            timeout=30,
        )
    except Exception as exc:
        payload["errors"].append(f"快照导出总览读取失败：{exc}")

    st.session_state["_admin_ops_dashboard_cache"] = {
        "base_url": str(base_url),
        "key_hash": key_hash,
        "tenant_limit": normalized_tenant_limit,
        "keep_latest": normalized_keep_latest,
        "older_than_hours": normalized_older_than_hours,
        "snapshot_export_limit": normalized_snapshot_export_limit,
        "export_format": normalized_export_format,
        "fetched_at": now_ts,
        "payload": payload,
    }
    return payload


def _run_admin_preview(
    base_url: str,
    admin_key: str,
    *,
    state_key: str,
    path: str,
    payload: dict[str, Any],
) -> None:
    try:
        result = _post_admin_json(base_url, path, admin_key, payload, timeout=30)
        st.session_state[state_key] = {
            "ok": True,
            "payload": result,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }
    except Exception as exc:
        st.session_state[state_key] = {
            "ok": False,
            "error": str(exc),
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }


def _preview_candidate_kind(item: dict[str, Any]) -> str:
    path_text = str(item.get("path") or "").strip().lower()
    if str(item.get("confirm_token") or "").strip():
        return "confirm_token"
    if "summary_snapshot_exports" in path_text or "summary_snapshot_export" in path_text:
        return "summary_snapshot_export"
    if "summary_snapshots" in path_text:
        return "summary_snapshot"
    if "ops_exports" in path_text:
        return "ops_export"
    return "unknown"


def _preview_candidate_kind_label(kind: str) -> str:
    mapping = {
        "ops_export": "导出文件",
        "confirm_token": "确认票据",
        "summary_snapshot": "总览快照",
        "summary_snapshot_export": "快照导出元数据",
        "unknown": "其他对象",
    }
    key = str(kind or "").strip()
    return str(mapping.get(key) or key or "其他对象")


def _preview_candidate_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    total_size_bytes = 0
    kind_counts: dict[str, int] = {}
    oldest_time = ""
    newest_time = ""
    for item in candidates:
        if not isinstance(item, dict):
            continue
        total_size_bytes += max(0, int(item.get("size_bytes") or 0))
        kind = _preview_candidate_kind(item)
        kind_counts[kind] = int(kind_counts.get(kind) or 0) + 1
        ts = str(item.get("mtime_iso") or item.get("used_at") or "").strip()
        if not ts:
            continue
        if not oldest_time or ts < oldest_time:
            oldest_time = ts
        if not newest_time or ts > newest_time:
            newest_time = ts
    return {
        "total_size_bytes": total_size_bytes,
        "kind_counts": kind_counts,
        "oldest_time": oldest_time,
        "newest_time": newest_time,
    }


def _admin_preview_cache_entries() -> list[dict[str, Any]]:
    state_defs = [
        ("_admin_preview_exports_retention", "导出文件 retention preview"),
        ("_admin_preview_confirm_tokens_retention", "确认票据 retention preview"),
        ("_admin_preview_summary_snapshots_retention", "总览快照 retention preview"),
        ("_admin_preview_snapshot_export_retention", "快照导出 retention preview"),
    ]
    rows: list[dict[str, Any]] = []
    for state_key, title in state_defs:
        result = st.session_state.get(state_key)
        if not isinstance(result, dict):
            continue
        payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
        candidate_summary = _preview_candidate_summary(
            payload.get("prune_candidates") if isinstance(payload.get("prune_candidates"), list) else []
        )
        rows.append(
            {
                "标题": title,
                "最近预览时间": str(result.get("fetched_at") or "").strip(),
                "状态": "成功" if bool(result.get("ok")) else "失败",
                "候选数": int(payload.get("prune_candidates_count") or 0),
                "候选总大小": _format_uploaded_file_size(int(candidate_summary.get("total_size_bytes") or 0)),
                "对象类型": " / ".join(
                    f"{_preview_candidate_kind_label(str(kind))}:{int(count or 0)}"
                    for kind, count in sorted((candidate_summary.get("kind_counts") or {}).items())
                ),
            }
        )
    rows.sort(key=lambda item: str(item.get("最近预览时间") or ""), reverse=True)
    return rows


def _render_admin_preview_cache_overview() -> None:
    rows = _admin_preview_cache_entries()
    if not rows:
        return
    with st.container(border=True):
        st.caption("最近预览缓存")
        st.dataframe(rows, width="stretch", hide_index=True)


def _render_admin_preview_policy_card(
    *,
    export_format_label: str,
    keep_latest: int,
    older_than_hours: int,
) -> None:
    with st.container(border=True):
        st.caption("清理策略说明")
        c1, c2, c3 = st.columns(3)
        c1.metric("导出格式过滤", export_format_label)
        c2.metric("保留最近N份", int(keep_latest))
        c3.metric("过期小时阈值", int(older_than_hours))
        st.caption("当前页面所有按钮均为 preview-only，只返回候选集与保护信息，不执行任何删除。")
        st.caption("导出文件 preview 会额外受导出格式过滤影响；确认票据、总览快照和快照导出 preview 不受导出格式过滤影响。")


def _render_admin_preview_result(title: str, state_key: str) -> None:
    result = st.session_state.get(state_key)
    if not isinstance(result, dict):
        return
    with st.container(border=True):
        st.caption(title)
        fetched_at = str(result.get("fetched_at") or "").strip()
        if fetched_at:
            st.caption(f"最近预览时间：{fetched_at}")
        if not bool(result.get("ok")):
            st.warning(str(result.get("error") or "preview 读取失败"))
            return
        payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
        mode = str(payload.get("mode") or "preview")
        path = str(payload.get("path") or "")
        total = int(
            payload.get("total_exports")
            or payload.get("total_snapshots")
            or payload.get("total_records")
            or 0
        )
        prune_count = int(payload.get("prune_candidates_count") or 0)
        deleted_count = int(payload.get("deleted_count") or 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("模式", mode)
        c2.metric("候选数", prune_count)
        c3.metric("已删除", deleted_count)
        meta_parts: list[str] = []
        export_format = str(payload.get("export_format") or "").strip()
        if export_format:
            meta_parts.append(f"export_format={export_format}")
        if payload.get("keep_latest") is not None:
            meta_parts.append(f"keep_latest={int(payload.get('keep_latest') or 0)}")
        if payload.get("older_than_hours") is not None:
            meta_parts.append(f"older_than_hours={int(payload.get('older_than_hours') or 0)}")
        if meta_parts:
            st.caption("策略：" + "；".join(meta_parts))
        if path:
            st.caption(f"path：{path}")
        if total > 0:
            st.caption(f"当前总量：{total}")
        confirm_ttl = int(payload.get("confirm_ttl_seconds") or 0)
        confirm_valid_until = str(payload.get("confirm_valid_until") or "").strip()
        confirm_state_path = str(payload.get("confirm_state_path") or "").strip()
        if confirm_ttl > 0 or confirm_valid_until or confirm_state_path:
            detail_parts: list[str] = []
            if confirm_ttl > 0:
                detail_parts.append(f"confirm_ttl_seconds={confirm_ttl}")
            if confirm_valid_until:
                detail_parts.append(f"confirm_valid_until={confirm_valid_until}")
            if confirm_state_path:
                detail_parts.append(f"confirm_state_path={confirm_state_path}")
            st.caption("执行保护：" + "；".join(detail_parts))
        if str(payload.get("audit_path") or "").strip():
            st.caption(f"audit_path：{str(payload.get('audit_path') or '').strip()}")
        candidates = payload.get("prune_candidates") if isinstance(payload.get("prune_candidates"), list) else []
        candidate_summary = _preview_candidate_summary(candidates)
        total_candidate_size = int(candidate_summary.get("total_size_bytes") or 0)
        kind_counts = candidate_summary.get("kind_counts") if isinstance(candidate_summary.get("kind_counts"), dict) else {}
        oldest_time = str(candidate_summary.get("oldest_time") or "").strip()
        newest_time = str(candidate_summary.get("newest_time") or "").strip()
        if prune_count > 0:
            summary_parts: list[str] = []
            if total_candidate_size > 0:
                summary_parts.append(f"候选总大小={_format_uploaded_file_size(total_candidate_size)}")
            if kind_counts:
                kind_text = " / ".join(
                    "{label}:{count}({share:.0f}%)".format(
                        label=_preview_candidate_kind_label(str(kind)),
                        count=int(count or 0),
                        share=(float(int(count or 0)) * 100.0 / float(prune_count or 1)),
                    )
                    for kind, count in sorted(kind_counts.items())
                )
                summary_parts.append(f"对象类型={kind_text}")
            if oldest_time:
                summary_parts.append(f"最旧={oldest_time}")
            if newest_time:
                summary_parts.append(f"最新={newest_time}")
            if summary_parts:
                st.caption("候选摘要：" + "；".join(summary_parts))
        rows: list[dict[str, Any]] = []
        rows_by_kind: dict[str, list[dict[str, Any]]] = {}
        for item in candidates[:10]:
            if not isinstance(item, dict):
                continue
            kind = _preview_candidate_kind(item)
            row = {
                "对象": _preview_candidate_kind_label(kind),
                "文件": str(item.get("filename") or item.get("confirm_token") or ""),
                "路径": str(item.get("path") or ""),
                "大小": _format_uploaded_file_size(int(item.get("size_bytes") or 0)),
                "时间": str(item.get("mtime_iso") or item.get("used_at") or ""),
            }
            rows_by_kind.setdefault(kind, []).append(row)
            rows.append(
                row
            )
        if rows:
            st.caption("候选概览（前10条）")
            st.dataframe(rows, width="stretch", hide_index=True)
            if len(rows_by_kind) > 1:
                filter_options = ["全部"] + [_preview_candidate_kind_label(kind) for kind in sorted(rows_by_kind.keys())]
                selected_kind_label = st.selectbox(
                    "对象类型过滤",
                    options=filter_options,
                    index=0,
                    key=f"{state_key}_kind_filter",
                )
                if selected_kind_label != "全部":
                    filtered_rows = [
                        row for row in rows if str(row.get("对象") or "").strip() == selected_kind_label
                    ]
                    st.caption(f"当前过滤：{selected_kind_label}")
                    st.dataframe(filtered_rows, width="stretch", hide_index=True)
                st.caption("按对象类型折叠查看")
                for kind in sorted(rows_by_kind.keys()):
                    grouped_rows = rows_by_kind.get(kind) or []
                    with st.expander(
                        f"{_preview_candidate_kind_label(kind)}（前{len(grouped_rows)}条）",
                        expanded=False,
                    ):
                        st.dataframe(grouped_rows, width="stretch", hide_index=True)
        elif prune_count == 0:
            st.caption("当前没有待清理候选。")


def _render_admin_ops_panel(base_url: str) -> None:
    st.caption("只读管理台：统一查看租户报表、导出资产、确认票据与快照导出状态；不执行删除。")
    c1, c2, c3, c4, c5, c6 = st.columns([3.2, 1, 1, 1, 1, 1.1], vertical_alignment="bottom")
    with c1:
        admin_key = st.text_input("Admin Key", type="password", key="admin_api_key")
    with c2:
        tenant_limit = int(
            st.number_input("租户条数", min_value=1, max_value=50, value=10, step=1, key="admin_ops_tenant_limit")
        )
    with c3:
        keep_latest = int(
            st.number_input("保留最近N份", min_value=0, max_value=500, value=20, step=1, key="admin_ops_keep_latest")
        )
    with c4:
        older_than_hours = int(
            st.number_input(
                "过期小时阈值",
                min_value=0,
                max_value=24 * 365,
                value=168,
                step=1,
                key="admin_ops_older_than_hours",
            )
        )
    with c5:
        snapshot_export_limit = int(
            st.number_input(
                "快照导出条数",
                min_value=1,
                max_value=100,
                value=20,
                step=1,
                key="admin_ops_snapshot_export_limit",
            )
        )
    with c6:
        export_format_label = st.selectbox(
            "导出格式",
            options=["全部", "CSV", "JSON"],
            index=0,
            key="admin_ops_export_format_label",
        )
    export_format = {"全部": "", "CSV": "csv", "JSON": "json"}.get(str(export_format_label), "")
    refresh = st.button("刷新管理台", key="admin_ops_refresh", type="secondary", width="stretch")
    if not str(admin_key or "").strip():
        st.info("输入 Admin Key 后可启用只读运营管理台。")
        return

    payload = _admin_ops_dashboard_payload(
        base_url,
        admin_key,
        tenant_limit=tenant_limit,
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
        snapshot_export_limit=snapshot_export_limit,
        export_format=export_format,
        force=refresh,
    )
    if not bool(payload.get("ok")):
        st.warning(str(payload.get("error") or "运营管理台读取失败。"))
        return
    for item in payload.get("errors") or []:
        st.warning(str(item))
    _render_admin_preview_cache_overview()

    tenant_payload = payload.get("tenant_reports") if isinstance(payload.get("tenant_reports"), dict) else {}
    exports_payload = payload.get("exports_summary") if isinstance(payload.get("exports_summary"), dict) else {}
    snapshot_export_payload = (
        payload.get("snapshot_export_summary") if isinstance(payload.get("snapshot_export_summary"), dict) else {}
    )

    tab1, tab2, tab3 = st.tabs(["租户报表", "导出资产", "快照导出"])

    with tab1:
        if not bool(tenant_payload.get("ok")):
            st.info("租户报表暂不可用。")
        else:
            page = tenant_payload.get("page") if isinstance(tenant_payload.get("page"), dict) else {}
            summary = tenant_payload.get("summary") if isinstance(tenant_payload.get("summary"), dict) else {}
            last_hour = _admin_ops_last_hour(summary)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("当前页租户", int(summary.get("tenant_count") or 0))
            m2.metric("计费事件", int(summary.get("charge_event_count") or 0))
            m3.metric("累计费用", int(summary.get("charge_cost_total") or 0))
            m4.metric("近1小时拒绝", int(last_hour.get("rejected_jobs") or 0))
            st.caption(
                "分页模式：{mode}；扫描用户：{scanned}；匹配结果：{matched}".format(
                    mode=str(page.get("mode") or "unknown"),
                    scanned=int(page.get("scanned_users") or 0),
                    matched=int(page.get("total_matched") or 0),
                )
            )
            rows: list[dict[str, Any]] = []
            for item in tenant_payload.get("items") or []:
                if not isinstance(item, dict):
                    continue
                user = item.get("user") if isinstance(item.get("user"), dict) else {}
                report_summary = item.get("report_summary") if isinstance(item.get("report_summary"), dict) else {}
                admission = report_summary.get("admission") if isinstance(report_summary.get("admission"), dict) else {}
                billing = (
                    report_summary.get("billing_summary")
                    if isinstance(report_summary.get("billing_summary"), dict)
                    else {}
                )
                ops = report_summary.get("ops_summary") if isinstance(report_summary.get("ops_summary"), dict) else {}
                bucket = ops.get("last_hour") if isinstance(ops.get("last_hour"), dict) else {}
                profiles = (
                    bucket.get("text_chain_profiles") if isinstance(bucket.get("text_chain_profiles"), dict) else {}
                )
                profile_text = " / ".join(f"{k}:{int(v or 0)}" for k, v in sorted(profiles.items()))
                rows.append(
                    {
                        "用户ID": int(user.get("id") or 0),
                        "邮箱": str(user.get("email") or ""),
                        "余额": int(user.get("balance") or 0),
                        "告警": str(admission.get("warning_level") or ""),
                        "计费总额": int(billing.get("charge_cost_total") or 0),
                        "近1小时拒绝": int(bucket.get("rejected_jobs") or 0),
                        "近1小时降级": int(bucket.get("degraded_jobs") or 0),
                        "近1小时排队": int(bucket.get("queued_jobs") or 0),
                        "文本链命中": profile_text,
                    }
                )
            if rows:
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.info("当前没有可展示的租户报表结果。")

    with tab2:
        summary = exports_payload.get("summary") if isinstance(exports_payload.get("summary"), dict) else {}
        if not summary:
            st.info("导出资产总览暂不可用。")
        else:
            confirm_state = (
                summary.get("confirm_token_state") if isinstance(summary.get("confirm_token_state"), dict) else {}
            )
            snapshot_state = (
                summary.get("summary_snapshot_state") if isinstance(summary.get("summary_snapshot_state"), dict) else {}
            )
            snapshot_export_state = (
                summary.get("summary_snapshot_export_state")
                if isinstance(summary.get("summary_snapshot_export_state"), dict)
                else {}
            )
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("导出文件", int(summary.get("total_exports") or 0))
            m2.metric("导出体积", _format_uploaded_file_size(int(summary.get("total_size_bytes") or 0)))
            m3.metric("已用确认票据", int(confirm_state.get("record_count") or 0))
            m4.metric("总览快照", int(snapshot_state.get("count") or 0))
            st.caption(
                "当前导出格式过滤：{label}；以下按钮全部为 preview-only，不会删除文件。".format(
                    label=export_format_label
                )
            )
            st.caption(
                "导出格式分布：{fmt}；导出模式分布：{mode}".format(
                    fmt=json.dumps(summary.get("by_format") or {}, ensure_ascii=False, sort_keys=True),
                    mode=json.dumps(summary.get("by_mode") or {}, ensure_ascii=False, sort_keys=True),
                )
            )
            _render_admin_preview_policy_card(
                export_format_label=export_format_label,
                keep_latest=keep_latest,
                older_than_hours=older_than_hours,
            )
            state_rows = [
                {
                    "对象": "导出文件保留预览",
                    "路径": "-",
                    "当前数量": int(summary.get("total_exports") or 0),
                    "预览待清理": int(((summary.get("retention_preview") or {}).get("prune_candidates_count") or 0)),
                },
                {
                    "对象": "确认票据状态",
                    "路径": str(confirm_state.get("path") or ""),
                    "当前数量": int(confirm_state.get("record_count") or 0),
                    "预览待清理": int(((confirm_state.get("retention_preview") or {}).get("prune_candidates_count") or 0)),
                },
                {
                    "对象": "总览快照",
                    "路径": str(snapshot_state.get("path") or ""),
                    "当前数量": int(snapshot_state.get("count") or 0),
                    "预览待清理": int(((snapshot_state.get("retention_preview") or {}).get("prune_candidates_count") or 0)),
                },
                {
                    "对象": "快照导出元数据",
                    "路径": str(snapshot_export_state.get("path") or ""),
                    "当前数量": int(snapshot_export_state.get("count") or 0),
                    "预览待清理": int(
                        ((snapshot_export_state.get("retention_preview") or {}).get("prune_candidates_count") or 0)
                    ),
                },
            ]
            st.dataframe(state_rows, width="stretch", hide_index=True)
            p1, p2, p3 = st.columns(3)
            with p1:
                if st.button("预览导出文件清理", key="admin_preview_exports_retention", width="stretch"):
                    _run_admin_preview(
                        base_url,
                        admin_key,
                        state_key="_admin_preview_exports_retention",
                        path="/auth/tenant_usage_reports_exports_retention",
                        payload={
                            "keep_latest": keep_latest,
                            "older_than_hours": older_than_hours,
                            "export_format": export_format,
                            "execute": False,
                        },
                    )
            with p2:
                if st.button("预览确认票据清理", key="admin_preview_confirm_tokens_retention", width="stretch"):
                    _run_admin_preview(
                        base_url,
                        admin_key,
                        state_key="_admin_preview_confirm_tokens_retention",
                        path="/auth/tenant_usage_reports_exports_confirm_tokens_retention",
                        payload={
                            "keep_latest": keep_latest,
                            "older_than_hours": older_than_hours,
                            "execute": False,
                        },
                    )
            with p3:
                if st.button("预览总览快照清理", key="admin_preview_summary_snapshots_retention", width="stretch"):
                    _run_admin_preview(
                        base_url,
                        admin_key,
                        state_key="_admin_preview_summary_snapshots_retention",
                        path="/auth/tenant_usage_reports_exports_summary_snapshots_retention",
                        payload={
                            "keep_latest": keep_latest,
                            "older_than_hours": older_than_hours,
                            "execute": False,
                        },
                    )
            _render_admin_preview_result("导出文件 retention preview", "_admin_preview_exports_retention")
            _render_admin_preview_result("确认票据 retention preview", "_admin_preview_confirm_tokens_retention")
            _render_admin_preview_result("总览快照 retention preview", "_admin_preview_summary_snapshots_retention")

    with tab3:
        if not bool(snapshot_export_payload.get("ok")):
            st.info("快照导出总览暂不可用。")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("快照导出数", int(snapshot_export_payload.get("count") or 0))
            m2.metric("目录体积", _format_uploaded_file_size(int(snapshot_export_payload.get("size_bytes") or 0)))
            m3.metric(
                "预览待清理",
                int(((snapshot_export_payload.get("retention_preview") or {}).get("prune_candidates_count") or 0)),
            )
            st.caption(
                "格式分布：{fmt}".format(
                    fmt=json.dumps(snapshot_export_payload.get("by_format") or {}, ensure_ascii=False, sort_keys=True)
                )
            )
            st.caption("以下按钮为 preview-only，不会删除快照导出元数据文件。")
            newest_export = (
                snapshot_export_payload.get("newest_export")
                if isinstance(snapshot_export_payload.get("newest_export"), dict)
                else {}
            )
            oldest_export = (
                snapshot_export_payload.get("oldest_export")
                if isinstance(snapshot_export_payload.get("oldest_export"), dict)
                else {}
            )
            if newest_export or oldest_export:
                st.caption(
                    "最新：{newest}；最旧：{oldest}".format(
                        newest=str(newest_export.get("filename") or "未记录"),
                        oldest=str(oldest_export.get("filename") or "未记录"),
                    )
                )
            if st.button("预览快照导出清理", key="admin_preview_snapshot_export_retention", width="stretch"):
                _run_admin_preview(
                    base_url,
                    admin_key,
                    state_key="_admin_preview_snapshot_export_retention",
                    path="/auth/tenant_usage_reports_exports_summary_snapshot_exports_retention",
                    payload={
                        "keep_latest": keep_latest,
                        "older_than_hours": older_than_hours,
                        "execute": False,
                    },
                )
            _render_admin_preview_result("快照导出 retention preview", "_admin_preview_snapshot_export_retention")


def _job_stage_label(stage: Any) -> str:
    key = str(stage or "").strip()
    if not key:
        return "-"
    return JOB_STAGE_LABELS.get(key, key)


def _job_sla_snapshot(sla: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(sla, dict):
        return {}
    total_seconds = _safe_float(sla.get("total_seconds"))
    current_stage = str(sla.get("current_stage") or "").strip()
    current_stage_detail = str(sla.get("current_stage_detail") or "").strip()
    current_stage_seconds = _safe_float(sla.get("current_stage_seconds"))
    dominant_stage = str(sla.get("dominant_stage") or "").strip()
    dominant_stage_seconds = _safe_float(sla.get("dominant_stage_seconds"))
    dominant_stage_share = _safe_float(sla.get("dominant_stage_share"))
    exporting_seconds = _safe_float(sla.get("exporting_seconds"))
    exporting_share = _safe_float(sla.get("exporting_share"))
    variant_running_seconds = _safe_float(sla.get("variant_running_seconds"))
    variant_running_share = _safe_float(sla.get("variant_running_share"))
    stages = sla.get("stages") if isinstance(sla.get("stages"), list) else []
    if not current_stage and stages:
        for raw in reversed(stages):
            if not isinstance(raw, dict):
                continue
            current_stage = str(raw.get("name") or "").strip()
            current_stage_detail = str(raw.get("detail") or "").strip()
            current_stage_seconds = _safe_float(raw.get("duration_sec"))
            started_at = _safe_float(raw.get("started_at"))
            ended_at = _safe_float(raw.get("ended_at"))
            if current_stage_seconds is None and started_at is not None and ended_at is None:
                current_stage_seconds = max(0.0, time.time() - started_at)
            if current_stage or current_stage_detail or current_stage_seconds is not None:
                break
    if not dominant_stage and stages:
        longest_seconds = None
        for raw in stages:
            if not isinstance(raw, dict):
                continue
            stage_name = str(raw.get("name") or "").strip()
            stage_seconds = _safe_float(raw.get("duration_sec"))
            started_at = _safe_float(raw.get("started_at"))
            ended_at = _safe_float(raw.get("ended_at"))
            if stage_seconds is None and started_at is not None and ended_at is None:
                stage_seconds = max(0.0, time.time() - started_at)
            if stage_name == "exporting" and exporting_seconds is None:
                exporting_seconds = stage_seconds
            if stage_name == "variant_running" and variant_running_seconds is None:
                variant_running_seconds = stage_seconds
            if stage_seconds is None:
                continue
            if longest_seconds is None or stage_seconds > longest_seconds:
                dominant_stage = stage_name
                dominant_stage_seconds = stage_seconds
                longest_seconds = stage_seconds
    if dominant_stage_share is None and total_seconds and total_seconds > 0 and dominant_stage_seconds is not None:
        dominant_stage_share = round((dominant_stage_seconds / total_seconds) * 100.0, 1)
    if exporting_share is None and total_seconds and total_seconds > 0 and exporting_seconds is not None:
        exporting_share = round((exporting_seconds / total_seconds) * 100.0, 1)
    if variant_running_share is None and total_seconds and total_seconds > 0 and variant_running_seconds is not None:
        variant_running_share = round((variant_running_seconds / total_seconds) * 100.0, 1)
    return {
        "total_seconds": total_seconds,
        "total_text": _format_duration_short(total_seconds),
        "current_stage": current_stage,
        "current_stage_text": _job_stage_label(current_stage) if current_stage else "",
        "current_stage_detail": current_stage_detail,
        "current_stage_seconds": current_stage_seconds,
        "current_stage_seconds_text": _format_duration_short(current_stage_seconds),
        "dominant_stage": dominant_stage,
        "dominant_stage_text": _job_stage_label(dominant_stage) if dominant_stage else "",
        "dominant_stage_seconds": dominant_stage_seconds,
        "dominant_stage_seconds_text": _format_duration_short(dominant_stage_seconds),
        "dominant_stage_share": dominant_stage_share,
        "exporting_seconds": exporting_seconds,
        "exporting_seconds_text": _format_duration_short(exporting_seconds),
        "exporting_share": exporting_share,
        "variant_running_seconds": variant_running_seconds,
        "variant_running_seconds_text": _format_duration_short(variant_running_seconds),
        "variant_running_share": variant_running_share,
    }


def _job_stage_sla_warning(snapshot: dict[str, Any], stage_latency: dict[str, Any] | None) -> str:
    if not isinstance(snapshot, dict) or not isinstance(stage_latency, dict):
        return ""
    stage = str(snapshot.get("current_stage") or "").strip()
    current_stage_seconds = _safe_float(snapshot.get("current_stage_seconds"))
    if not stage or current_stage_seconds is None or current_stage_seconds < 0:
        return ""
    stage_row = stage_latency.get(stage) if isinstance(stage_latency.get(stage), dict) else {}
    p95_sec = _safe_float(stage_row.get("p95_sec"))
    if p95_sec is None or p95_sec <= 0:
        return ""
    threshold = max(p95_sec * 1.15, p95_sec + 15.0)
    if current_stage_seconds < threshold:
        return ""
    return (
        f"阶段耗时预警：{_job_stage_label(stage)} 已运行 {snapshot.get('current_stage_seconds_text') or _format_duration_short(current_stage_seconds)}，"
        f"高于近期P95 {_format_duration_short(p95_sec)}。"
    )


def _job_stage_latency_line(snapshot: dict[str, Any], stage_latency: dict[str, Any] | None) -> str:
    if not isinstance(snapshot, dict) or not isinstance(stage_latency, dict):
        return ""
    stage = str(snapshot.get("current_stage") or "").strip()
    if not stage:
        return ""
    row = stage_latency.get(stage) if isinstance(stage_latency.get(stage), dict) else {}
    p50_sec = _safe_float(row.get("p50_sec"))
    p95_sec = _safe_float(row.get("p95_sec"))
    if p50_sec is None and p95_sec is None:
        return ""
    parts = []
    if p50_sec is not None:
        parts.append(f"P50 {_format_duration_short(p50_sec)}")
    if p95_sec is not None:
        parts.append(f"P95 {_format_duration_short(p95_sec)}")
    if not parts:
        return ""
    return f"近期阶段基线：{_job_stage_label(stage)} {' / '.join(parts)}"


def _job_terminal_sla_line(snapshot: dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        return ""
    stage = str(snapshot.get("dominant_stage") or "").strip()
    stage_seconds_text = str(snapshot.get("dominant_stage_seconds_text") or "").strip()
    if not stage or not stage_seconds_text:
        return ""
    share = _safe_float(snapshot.get("dominant_stage_share"))
    line = f"主要耗时：{_job_stage_label(stage)} {stage_seconds_text}"
    if share is not None and share > 0:
        share_text = f"{share:.1f}".rstrip("0").rstrip(".")
        line += f"，占总耗时 {share_text}%"
    return line


def _job_terminal_sla_warning(snapshot: dict[str, Any], stage_latency: dict[str, Any] | None) -> str:
    if not isinstance(snapshot, dict) or not isinstance(stage_latency, dict):
        return ""
    stage = str(snapshot.get("dominant_stage") or "").strip()
    stage_seconds = _safe_float(snapshot.get("dominant_stage_seconds"))
    if not stage or stage_seconds is None or stage_seconds < 0:
        return ""
    stage_row = stage_latency.get(stage) if isinstance(stage_latency.get(stage), dict) else {}
    p95_sec = _safe_float(stage_row.get("p95_sec"))
    if p95_sec is None or p95_sec <= 0:
        return ""
    threshold = max(p95_sec * 1.15, p95_sec + 15.0)
    if stage_seconds < threshold:
        return ""
    return (
        f"耗时归因预警：{_job_stage_label(stage)} 本次耗时 {snapshot.get('dominant_stage_seconds_text') or _format_duration_short(stage_seconds)}，"
        f"高于近期P95 {_format_duration_short(p95_sec)}。"
    )


def _job_terminal_sla_split_line(snapshot: dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        return ""

    def _fmt_share(share: float | None) -> str:
        if share is None or share <= 0:
            return ""
        return f"{share:.1f}".rstrip("0").rstrip(".")

    variant_seconds_text = str(snapshot.get("variant_running_seconds_text") or "").strip()
    exporting_seconds_text = str(snapshot.get("exporting_seconds_text") or "").strip()
    if not variant_seconds_text or not exporting_seconds_text:
        return ""
    variant_share = _safe_float(snapshot.get("variant_running_share"))
    exporting_share = _safe_float(snapshot.get("exporting_share"))
    split_threshold = 20.0
    if (
        variant_share is None
        or exporting_share is None
        or variant_share < split_threshold
        or exporting_share < split_threshold
    ):
        return ""
    variant_share_text = _fmt_share(variant_share)
    exporting_share_text = _fmt_share(exporting_share)
    left = f"{_job_stage_label('variant_running')} {variant_seconds_text}"
    right = f"{_job_stage_label('exporting')} {exporting_seconds_text}"
    if variant_share_text:
        left += f"（{variant_share_text}%）"
    if exporting_share_text:
        right += f"（{exporting_share_text}%）"
    return f"本次耗时拆解：{left}；{right}"


def _job_terminal_dual_bottleneck_hint(snapshot: dict[str, Any], stage_artifacts_dir: Any = "") -> str:
    if not isinstance(snapshot, dict):
        return ""
    variant_share = _safe_float(snapshot.get("variant_running_share"))
    exporting_share = _safe_float(snapshot.get("exporting_share"))
    secondary_focus_threshold = 35.0
    if (
        variant_share is None
        or exporting_share is None
        or variant_share < secondary_focus_threshold
        or exporting_share < secondary_focus_threshold
    ):
        return ""
    stage_dir = str(stage_artifacts_dir or "").strip()
    variant_path = f"{stage_dir}/03_variant_results_summary.json" if stage_dir else "03_variant_results_summary.json"
    outputs_path = f"{stage_dir}/04_outputs.json" if stage_dir else "04_outputs.json"
    return (
        f"双瓶颈提示：本次耗时同时集中在并行编制方案和导出成品；"
        f"建议先看 {variant_path}，再看 {outputs_path}。"
    )


def _job_terminal_focus_hint(snapshot: dict[str, Any], stage_artifacts_dir: Any = "") -> str:
    if not isinstance(snapshot, dict):
        return ""
    dual_hint = _job_terminal_dual_bottleneck_hint(snapshot, stage_artifacts_dir)
    if dual_hint:
        return dual_hint
    dominant_stage = str(snapshot.get("dominant_stage") or "").strip()
    if dominant_stage == "variant_running":
        return _job_variant_artifact_hint(snapshot, stage_artifacts_dir)
    if dominant_stage == "exporting":
        return _job_export_artifact_hint(snapshot, stage_artifacts_dir)
    return ""


def _job_terminal_focus_hint_for_status(status: Any, focus_hint: Any, failure_hint: Any) -> str:
    status_key = str(status or "").strip().lower()
    focus = str(focus_hint or "").strip()
    if not focus:
        return ""
    if status_key in {"failed", "cancelled"} and str(failure_hint or "").strip():
        return ""
    return focus


def _job_terminal_summary_sections(
    status: Any,
    snapshot: dict[str, Any],
    terminal_focus_hint: Any = "",
    error_text: Any = "",
) -> dict[str, list[str]]:
    status_key = str(status or "").strip().lower()
    pre_warning: list[str] = []
    post_warning: list[str] = []

    error = str(error_text or "").strip()
    if status_key in {"failed", "cancelled"} and error:
        pre_warning.append(f"错误/原因：{error}")

    terminal_sla_line = _job_terminal_sla_line(snapshot)
    if terminal_sla_line:
        pre_warning.append(terminal_sla_line)

    terminal_sla_split_line = _job_terminal_sla_split_line(snapshot)
    if terminal_sla_split_line:
        pre_warning.append(terminal_sla_split_line)

    focus = str(terminal_focus_hint or "").strip()
    if focus:
        if status_key == "done":
            post_warning.append(focus)
        else:
            pre_warning.append(focus)

    return {"pre_warning": pre_warning, "post_warning": post_warning}


def _job_terminal_info_line(status: Any, failure_hint: Any = "") -> str:
    status_key = str(status or "").strip().lower()
    hint = str(failure_hint or "").strip()
    if status_key in {"failed", "cancelled"} and hint:
        return f"排查建议：{hint}"
    return ""


def _job_active_parallelism_lines(
    runtime: dict[str, Any] | None,
    variants_done: Any = 0,
    variants_total: Any = 0,
) -> list[str]:
    runtime_dict = runtime if isinstance(runtime, dict) else {}

    def _as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    ap = _as_int(runtime_dict.get("agent_parallelism") or 0, 0)
    requested_ap = _as_int(runtime_dict.get("requested_agent_parallelism") or 0, 0)
    vp = _as_int(runtime_dict.get("variant_parallelism") or 0, 0)
    done = _as_int(variants_done or 0, 0)
    total = max(1, _as_int(variants_total or 0, 1))
    reason = str(runtime_dict.get("runtime_agent_parallelism_reason") or "").strip()
    learning_applied = bool(runtime_dict.get("runtime_agent_parallelism_learning_applied", False))
    learning_reason = str(runtime_dict.get("runtime_agent_parallelism_learning_reason") or "").strip()
    learning_tokens = set(_split_runtime_parallelism_reasons(learning_reason)) if learning_applied and learning_reason else set()
    reason_text = _humanize_runtime_parallelism_reason(reason, exclude=learning_tokens)

    lines: list[str] = []
    if ap > 0 or vp > 0:
        line = f"多Agent并行：章节并行={max(1, ap)}"
        if requested_ap > 0 and ap > 0 and requested_ap != ap:
            line += f"（请求={requested_ap}，已按任务规模收敛）"
        line += f"，方案并行={max(1, vp)}，完成方案={max(0, done)}/{total}"
        lines.append(line)
    if reason_text:
        lines.append(f"并发收敛原因：{reason_text}")
    return lines


def _job_done_learning_overview(summary: dict[str, Any]) -> str:
    if not isinstance(summary, dict):
        return ""

    def _as_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    parts: list[str] = []
    groups = [
        ("排序学习", _as_int(summary.get("applied_count")), _as_int(summary.get("source_runs")), "样本"),
        ("组合包学习", _as_int(summary.get("bundle_applied_count")), _as_int(summary.get("bundle_source_runs")), "样本"),
        ("语境组合包", _as_int(summary.get("context_bundle_applied_count")), _as_int(summary.get("context_bundle_source_runs")), "样本"),
        ("效果归因", _as_int(summary.get("context_bundle_effect_applied_count")), _as_int(summary.get("context_bundle_effect_source_runs")), "归因样本"),
        ("指标归因", _as_int(summary.get("context_bundle_metric_effect_applied_count")), _as_int(summary.get("context_bundle_metric_effect_source_runs")), "样本"),
        ("动作归因", _as_int(summary.get("context_bundle_metric_action_effect_applied_count")), _as_int(summary.get("context_bundle_metric_action_effect_source_runs")), "样本"),
    ]
    for label, count, source_runs, source_label in groups:
        if count <= 0:
            continue
        piece = f"{label}={count}项"
        if source_runs > 0:
            piece += f"（{source_label}={source_runs}）"
        parts.append(piece)
    if not parts:
        return ""
    return "修订学习摘要：" + "；".join(parts)


def _job_done_learning_focus(summary: dict[str, Any]) -> str:
    if not isinstance(summary, dict):
        return ""

    def _first_strings(value: Any, limit: int = 2) -> list[str]:
        if not isinstance(value, list):
            return []
        out: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            out.append(text)
            if len(out) >= limit:
                break
        return out

    combos = _first_strings(summary.get("combos"))
    if combos:
        return "重点命中：" + "；".join(combos)
    bundles = _first_strings(summary.get("bundles"))
    if bundles:
        return "重点命中：" + "；".join(bundles)
    context_bundles = _first_strings(summary.get("context_bundles"))
    if context_bundles:
        return "重点命中：" + "；".join(context_bundles)
    metrics = _first_strings(summary.get("context_bundle_metric_effect_metrics"))
    if metrics:
        return "本次拉平指标：" + " / ".join(metrics)
    triplets = _first_strings(summary.get("context_bundle_metric_action_effect_triplets"))
    if triplets:
        return "本次拉平动作：" + " / ".join(triplets)
    return ""


def _job_done_profile_summary(
    runtime_budget_summary: list[dict[str, Any]] | None,
    remediation_strategy_summary: dict[str, Any] | None,
    remediation_execution_summary: dict[str, Any] | None,
) -> str:
    def _as_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    parts: list[str] = []

    if isinstance(runtime_budget_summary, list):
        budget_parts: list[str] = []
        for row in runtime_budget_summary[:2]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            timeout_sec = row.get("requested_timeout_sec")
            retry_limit = row.get("requested_section_retry_limit")
            if not title:
                continue
            seg = f"{title}({timeout_sec or '-'}s/{retry_limit or '-'}轮)"
            budget_parts.append(seg)
        if budget_parts:
            parts.append("预算=" + " / ".join(budget_parts))

    if isinstance(remediation_strategy_summary, dict):
        issue_parts: list[str] = []
        indicator_rows = remediation_strategy_summary.get("indicator_groups")
        if isinstance(indicator_rows, list):
            for row in indicator_rows[:2]:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("indicator_group") or "").strip()
                count = _as_int(row.get("count") or 0)
                if name:
                    issue_parts.append(f"{name}×{count}")
        if issue_parts:
            parts.append("问题=" + " / ".join(issue_parts))

    if isinstance(remediation_execution_summary, dict):
        action_parts: list[str] = []
        action_rows = remediation_execution_summary.get("action_tags")
        if isinstance(action_rows, list):
            for row in action_rows[:2]:
                if not isinstance(row, dict):
                    continue
                label = str(row.get("label") or row.get("action_tag") or "").strip()
                count = _as_int(row.get("count") or 0)
                if label:
                    action_parts.append(f"{label}×{count}")
        if action_parts:
            parts.append("动作=" + " / ".join(action_parts))

    if not parts:
        return ""
    return "修订画像摘要：" + "；".join(parts)


def _job_done_runtime_summary(runtime: dict[str, Any] | None, automation_summary: dict[str, Any] | None) -> str:
    def _as_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    runtime_dict = runtime if isinstance(runtime, dict) else {}
    automation_dict = automation_summary if isinstance(automation_summary, dict) else {}
    parts: list[str] = []

    requested_ap = _as_int(runtime_dict.get("requested_agent_parallelism") or 0)
    effective_ap = _as_int(runtime_dict.get("agent_parallelism") or 0)
    vp = _as_int(runtime_dict.get("variant_parallelism") or 0)
    if effective_ap > 0 or vp > 0:
        parallel_text = f"并发=章节{max(1, effective_ap or requested_ap or 1)} / 方案{max(1, vp or 1)}"
        if requested_ap > 0 and effective_ap > 0 and requested_ap != effective_ap:
            parallel_text += f"（请求={requested_ap}）"
        parts.append(parallel_text)

    learning_applied = bool(runtime_dict.get("runtime_agent_parallelism_learning_applied", False))
    learning_source_runs = _as_int(runtime_dict.get("runtime_agent_parallelism_learning_source_runs") or 0)
    if learning_applied:
        learning_text = "并发学习=已应用"
        if learning_source_runs > 0:
            learning_text += f"（样本={learning_source_runs}）"
        parts.append(learning_text)

    if automation_dict:
        gate_ok = bool(automation_dict.get("quality_gate_ok"))
        failed_count = _as_int(automation_dict.get("quality_gate_failed_count") or 0)
        retry_rounds = _as_int(automation_dict.get("quality_gate_retry_rounds") or 0)
        replacement_count = _as_int(automation_dict.get("terminology_replacement_count") or 0)
        gate_text = "自动巡检=通过" if gate_ok else "自动巡检=未完全通过"
        if failed_count > 0:
            gate_text += f"（剩余{failed_count}项）"
        parts.append(gate_text)
        parts.append(f"自动修复={retry_rounds}轮")
        parts.append(f"术语纠偏={replacement_count}次")

    if not parts:
        return ""
    return "运行画像摘要：" + "；".join(parts)


def _split_runtime_parallelism_reasons(reason_text: Any) -> list[str]:
    text = str(reason_text or "").replace("；", ";").strip()
    if not text:
        return []
    parts: list[str] = []
    for raw in text.replace(";", ",").split(","):
        token = raw.strip()
        if token and token not in parts:
            parts.append(token)
    return parts


def _humanize_runtime_parallelism_reason(reason_text: Any, exclude: set[str] | None = None) -> str:
    exclude_set = {str(item).strip() for item in (exclude or set()) if str(item).strip()}

    def _parse_cap(token: str, prefix: str) -> str:
        cap = token.removeprefix(prefix).strip()
        return cap if cap.isdigit() else ""

    def _parse_rate(token: str, prefix: str) -> str:
        rate_text = token.removeprefix(prefix).removesuffix("_reduce_parallelism").strip()
        try:
            return f"{float(rate_text):.0%}"
        except Exception:
            return rate_text

    out: list[str] = []
    for token in _split_runtime_parallelism_reasons(reason_text):
        if token in exclude_set:
            continue
        human = token
        if token.startswith("small_job_cap="):
            cap = _parse_cap(token, "small_job_cap=")
            if cap:
                human = f"小篇幅任务收敛到 {cap} 并行"
        elif token == "mid_small_cap=3":
            human = "中小篇幅任务收敛到 3 并行"
        elif token == "mid_job_cap=4":
            human = "中等篇幅任务收敛到 4 并行"
        elif token == "compact_outline_cap=2":
            human = "目录较紧凑，收敛到 2 并行"
        elif token == "outline_cap=3":
            human = "按目录规模收敛到 3 并行"
        elif token.startswith("historical_task_hard_failure_rate=") and token.endswith("_reduce_parallelism"):
            rate = _parse_rate(token, "historical_task_hard_failure_rate=")
            human = f"历史硬失败率 {rate}，降低并行度"
        elif token.startswith("historical_task_fallback_rate=") and token.endswith("_reduce_parallelism"):
            rate = _parse_rate(token, "historical_task_fallback_rate=")
            human = f"历史回退率 {rate}，降低并行度"
        elif token.startswith("historical_task_quality_issue_rate=") and token.endswith("_reduce_parallelism"):
            rate = _parse_rate(token, "historical_task_quality_issue_rate=")
            human = f"历史质量问题率 {rate}，降低并行度"
        elif token == "historical_task_high_pressure_extra_reduce":
            human = "历史高压样本偏多，额外降低并行度"
        if human:
            out.append(human)
    return "；".join(out)


def _job_done_runtime_focus(runtime: dict[str, Any] | None) -> str:
    runtime_dict = runtime if isinstance(runtime, dict) else {}
    reason = str(runtime_dict.get("runtime_agent_parallelism_reason") or "").strip()
    learning_applied = bool(runtime_dict.get("runtime_agent_parallelism_learning_applied", False))
    learning_reason = str(runtime_dict.get("runtime_agent_parallelism_learning_reason") or "").strip()
    try:
        learning_source_runs = int(runtime_dict.get("runtime_agent_parallelism_learning_source_runs") or 0)
    except Exception:
        learning_source_runs = 0

    learning_tokens = set(_split_runtime_parallelism_reasons(learning_reason)) if learning_applied and learning_reason else set()
    reason_text = _humanize_runtime_parallelism_reason(reason, exclude=learning_tokens)
    learning_text = _humanize_runtime_parallelism_reason(learning_reason)

    parts: list[str] = []
    if reason_text:
        parts.append("收敛=" + reason_text)
    if learning_applied and learning_text:
        learning_text = "学习命中=" + learning_text
        if learning_source_runs > 0:
            learning_text += f"（样本={learning_source_runs}）"
        parts.append(learning_text)
    if not parts:
        return ""
    return "运行期收敛摘要：" + "；".join(parts)


def _job_done_runtime_overview(runtime: dict[str, Any] | None, automation_summary: dict[str, Any] | None) -> str:
    runtime_summary = _job_done_runtime_summary(runtime, automation_summary)
    runtime_focus = _job_done_runtime_focus(runtime)
    parts: list[str] = []
    if runtime_summary:
        parts.append(runtime_summary.removeprefix("运行画像摘要："))
    if runtime_focus:
        parts.append(runtime_focus.removeprefix("运行期收敛摘要："))
    if not parts:
        return ""
    return "运行画像摘要：" + "；".join(parts)


def _job_done_budget_learning_focus(runtime_budget_summary: list[dict[str, Any]] | None) -> str:
    if not isinstance(runtime_budget_summary, list):
        return ""
    parts: list[str] = []
    for row in runtime_budget_summary[:2]:
        if not isinstance(row, dict) or not bool(row.get("evolution_applied", False)):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        seg = title
        try:
            src_runs = int(row.get("evolution_source_runs") or 0)
        except Exception:
            src_runs = 0
        if src_runs > 0:
            seg += f"（样本={src_runs}）"
        parts.append(seg)
    if not parts:
        return ""
    return "运行期学习命中：" + " / ".join(parts)


def _job_done_chapter_effect_focus(summary: dict[str, Any] | None) -> str:
    if not isinstance(summary, dict):
        return ""
    rows = summary.get("chapter_effect_summary")
    if not isinstance(rows, list):
        return ""
    parts: list[str] = []
    for row in rows[:2]:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        metrics = row.get("resolved_metrics") if isinstance(row.get("resolved_metrics"), list) else []
        triplets = row.get("resolved_action_triplets") if isinstance(row.get("resolved_action_triplets"), list) else []
        if not title:
            continue
        piece: list[str] = []
        if metrics:
            metric_texts = [str(x).strip() for x in metrics[:2] if str(x).strip()]
            if metric_texts:
                piece.append("指标=" + "/".join(metric_texts))
        if triplets:
            triplet_texts = [str(x).strip() for x in triplets[:2] if str(x).strip()]
            if triplet_texts:
                piece.append("动作=" + "/".join(triplet_texts))
        if piece:
            parts.append(f"{title}->{'; '.join(piece)}")
    if not parts:
        return ""
    return "章节级拉平：" + "；".join(parts)


def _job_done_learning_summary(
    runtime_budget_summary: list[dict[str, Any]] | None,
    remediation_learning_summary: dict[str, Any] | None,
) -> str:
    budget_focus = _job_done_budget_learning_focus(runtime_budget_summary)
    learning_overview = _job_done_learning_overview(remediation_learning_summary)
    parts: list[str] = []
    if budget_focus:
        parts.append("预算学习=" + budget_focus.removeprefix("运行期学习命中："))
    if learning_overview:
        parts.append(learning_overview.removeprefix("修订学习摘要："))
    if not parts:
        return ""
    return "学习画像摘要：" + "；".join(parts)


def _job_done_remediation_summary(profile_summary: str, learning_summary: str) -> str:
    parts: list[str] = []
    profile_text = str(profile_summary or "").strip()
    learning_text = str(learning_summary or "").strip()
    if profile_text:
        parts.append(profile_text.removeprefix("修订画像摘要："))
    if learning_text:
        parts.append(learning_text.removeprefix("学习画像摘要："))
    if not parts:
        return ""
    return "修订学习画像摘要：" + "；".join(parts)


def _job_done_summary_lines(
    runtime: dict[str, Any] | None,
    automation_summary: dict[str, Any] | None,
    runtime_budget_summary: list[dict[str, Any]] | None,
    remediation_strategy_summary: dict[str, Any] | None,
    remediation_execution_summary: dict[str, Any] | None,
    remediation_learning_summary: dict[str, Any] | None,
) -> list[str]:
    lines: list[str] = []
    runtime_overview = _job_done_runtime_overview(runtime, automation_summary)
    if runtime_overview:
        lines.append(runtime_overview)
    profile_summary = _job_done_profile_summary(
        runtime_budget_summary,
        remediation_strategy_summary,
        remediation_execution_summary,
    )
    learning_summary = _job_done_learning_summary(runtime_budget_summary, remediation_learning_summary)
    remediation_summary = _job_done_remediation_summary(profile_summary, learning_summary)
    if remediation_summary:
        lines.append(remediation_summary)
    focus_summary = _job_done_focus_summary(remediation_learning_summary)
    if focus_summary:
        lines.append(focus_summary)
    return lines


def _job_done_focus_summary(remediation_learning_summary: dict[str, Any] | None) -> str:
    learning_focus = _job_done_learning_focus(remediation_learning_summary or {})
    chapter_effect_focus = _job_done_chapter_effect_focus(remediation_learning_summary)
    parts: list[str] = []
    if learning_focus:
        if learning_focus.startswith("重点命中："):
            parts.append(learning_focus.removeprefix("重点命中："))
        elif learning_focus.startswith("本次拉平指标："):
            parts.append("指标=" + learning_focus.removeprefix("本次拉平指标："))
        elif learning_focus.startswith("本次拉平动作："):
            parts.append("动作=" + learning_focus.removeprefix("本次拉平动作："))
        else:
            parts.append(learning_focus)
    if chapter_effect_focus:
        parts.append(chapter_effect_focus.removeprefix("章节级拉平："))
    if not parts:
        return ""
    return "重点修订命中：" + "；".join(parts)


def _job_export_artifact_hint(snapshot: dict[str, Any], stage_artifacts_dir: Any = "") -> str:
    if not isinstance(snapshot, dict):
        return ""
    stage_dir = str(stage_artifacts_dir or "").strip()
    current_stage = str(snapshot.get("current_stage") or "").strip()
    dominant_stage = str(snapshot.get("dominant_stage") or "").strip()
    if current_stage != "exporting" and dominant_stage != "exporting":
        return ""
    outputs_path = f"{stage_dir}/04_outputs.json" if stage_dir else "04_outputs.json"
    return (
        f"导出排查入口：优先查看 {outputs_path}，确认 docx / compare_docx / focus_xlsx / "
        f"score_overview_xlsx 是否齐全。"
    )


def _job_variant_artifact_hint(snapshot: dict[str, Any], stage_artifacts_dir: Any = "") -> str:
    if not isinstance(snapshot, dict):
        return ""
    stage_dir = str(stage_artifacts_dir or "").strip()
    current_stage = str(snapshot.get("current_stage") or "").strip()
    dominant_stage = str(snapshot.get("dominant_stage") or "").strip()
    summary_path = f"{stage_dir}/03_variant_results_summary.json" if stage_dir else "03_variant_results_summary.json"
    if current_stage == "variant_running":
        return (
            f"方案编制排查入口：当前仍在并行编制阶段；优先关注阶段留痕目录 {stage_dir or '-'}，"
            f"任务完成后重点查看 {summary_path} 与章节预算摘要。"
        )
    if dominant_stage == "variant_running":
        return (
            f"方案编制排查入口：优先查看 {summary_path}，结合章节预算摘要与并发收敛原因定位慢章节。"
        )
    return ""


def _job_failure_hint(status: Any, error_text: Any, stage_artifacts_dir: Any = "") -> str:
    status_key = str(status or "").strip().lower()
    error = str(error_text or "").strip()
    stage_dir = str(stage_artifacts_dir or "").strip()
    suffix = f"；建议优先查看阶段留痕目录：{stage_dir}" if stage_dir else ""
    if status_key == "cancelled" or error == "cancelled_by_user":
        return "任务已由人工主动中止；若参数无需调整，可直接沿用当前参数重新发起。" + suffix
    if error.startswith("worker_spawn_failed:"):
        return "后台执行进程未成功拉起；优先检查后端/worker 启动日志，再核对本次任务是否已落留痕。" + suffix
    if error.startswith("all_variants_failed_hard_gate:"):
        return "所有候选方案均未通过最低质量门槛；优先查看 hard_failures 与问题清单留痕，定位是哪几章被硬闸门拦截。" + suffix
    if error.startswith("stale_worker_timeout("):
        return "任务心跳已超时，常见于子进程卡住或外部依赖长时间阻塞；建议先看最近 worker 日志与阶段留痕。" + suffix
    if error:
        return "系统已记录原始错误；建议结合阶段留痕目录与后端日志继续定位。" + suffix
    if status_key in {"failed", "cancelled"}:
        return "任务已结束但未返回明确错误说明；建议优先查看阶段留痕目录与后端日志。" + suffix
    return ""


def _render_template_library_items(
    base_url: str,
    actions_key: str,
    items: list[dict[str, Any]],
    *,
    key_prefix: str,
    empty_text: str,
    include_project_type: bool = False,
) -> None:
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        record_id = str(item.get("record_id") or "").strip()
        filename_text = str(item.get("filename") or "未命名样板").strip()
        filename = html.escape(filename_text)
        ts_text = _format_iso_ts_short(item.get("ts")) or "刚刚"
        note_text = str(item.get("library_note") or "").strip()
        scene_tags = [str(x).strip() for x in (item.get("template_scene_tags") or []) if str(x).strip()]
        feedback_origin = str(item.get("template_feedback_origin") or "").strip().lower()
        meta_parts = [ts_text]
        project_type = str(item.get("project_type") or "").strip()
        item_bucket = _template_page_bucket_label(item.get("template_page_bucket"))
        if include_project_type and project_type:
            meta_parts.append(project_type)
        if item_bucket:
            meta_parts.append(item_bucket)
        pages = item.get("pages")
        if pages:
            meta_parts.append(f"{int(pages)}页")
        body = html.escape(note_text) if note_text else "已入库，可在同类型章节生成时作为参考样板参与检索。"
        profile_count = int(item.get("template_chapter_profile_count") or 0)
        priority_label = str(item.get("learning_priority_label") or "").strip() or "基础"
        learning_state = f"已学习 {profile_count} 个章节画像" if profile_count > 0 else "待补全章节画像"
        if feedback_origin == "generated_accepted":
            learning_state += " · 系统回流"
        if scene_tags:
            learning_state += " · " + " / ".join(scene_tags[:3])
        learning_hint = f"{learning_state} · {priority_label}"
        cols = st.columns([0.83, 0.17], gap="small")
        with cols[0]:
            st.markdown(
                (
                    "<div class='zf-library-item'>"
                    f"<strong>{filename}</strong>"
                    f"<span>{html.escape(' · '.join(meta_parts))}</span>"
                    f"<p>{body}</p>"
                    f"<p>{html.escape(learning_hint)}</p>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        with cols[1]:
            st.write("")
            if st.button("删除", key=f"{key_prefix}_{record_id or filename_text}", width="stretch"):
                try:
                    deleted_payload = _post_json(
                        base_url,
                        "/ingest/template-library/delete",
                        actions_key,
                        {"record_id": record_id},
                        timeout=40,
                    )
                    deleted = deleted_payload.get("deleted") if isinstance(deleted_payload, dict) else {}
                    deleted_name = str((deleted or {}).get("filename") or filename_text or "样板").strip()
                    st.session_state["template_library_flash"] = f"已删除样板：{deleted_name}"
                    st.rerun()
                except Exception as e:
                    st.error(f"样板删除失败: {e}")


def _render_template_library_panel(base_url: str, actions_key: str) -> None:
    flash = str(st.session_state.pop("template_library_flash", "") or "").strip()
    if flash:
        st.success(flash)

    st.caption("按“项目类型 + 页数档位”沉淀优秀案例。入库后，系统会优先检索同类型、同篇幅档位的样板作为参考。")

    try:
        summary_payload = _get_json(base_url, "/ingest/template-library/summary", actions_key, timeout=40)
        summary = summary_payload.get("summary") if isinstance(summary_payload, dict) else {}
        if not isinstance(summary, dict):
            summary = {}
    except Exception as e:
        summary = {}
        st.caption(f"样板库摘要暂不可用：{e}")

    selected_project_type = str(st.session_state.get("sample_library_project_type") or "").strip()
    if selected_project_type not in PROJECT_TYPES and PROJECT_TYPES:
        selected_project_type = str(st.session_state.get("project_type") or PROJECT_TYPES[0]).strip()
        if selected_project_type not in PROJECT_TYPES:
            selected_project_type = PROJECT_TYPES[0]
        st.session_state["sample_library_project_type"] = selected_project_type
    selected_page_bucket = str(st.session_state.get("sample_library_page_bucket") or "").strip()
    if selected_page_bucket not in TEMPLATE_PAGE_BUCKETS and TEMPLATE_PAGE_BUCKETS:
        selected_page_bucket = TEMPLATE_PAGE_BUCKETS[0]
        st.session_state["sample_library_page_bucket"] = selected_page_bucket
    scene_scope_key = f"{selected_project_type}::{selected_page_bucket}"
    if st.session_state.get("sample_library_scene_filter_scope") != scene_scope_key:
        st.session_state["sample_library_scene_filter"] = []
        st.session_state["sample_library_scene_filter_scope"] = scene_scope_key

    counts = summary.get("by_project_type") if isinstance(summary.get("by_project_type"), dict) else {}
    bucket_counts = summary.get("by_template_page_bucket") if isinstance(summary.get("by_template_page_bucket"), dict) else {}
    nested_counts = summary.get("by_project_type_bucket") if isinstance(summary.get("by_project_type_bucket"), dict) else {}
    profile_counts = summary.get("by_project_type_profile_count") if isinstance(summary.get("by_project_type_profile_count"), dict) else {}
    nested_profile_counts = (
        summary.get("by_project_type_bucket_profile_count")
        if isinstance(summary.get("by_project_type_bucket_profile_count"), dict)
        else {}
    )
    total_count = int(summary.get("total_count") or 0)
    total_profile_count = int(summary.get("total_profile_count") or 0)
    high_priority_count = int(summary.get("high_priority_count") or 0)
    accepted_feedback_count = int(summary.get("accepted_feedback_count") or 0)
    system_feedback_count = int(summary.get("system_feedback_count") or 0)
    current_count = int(counts.get(selected_project_type) or 0) if selected_project_type else 0
    current_bucket_count = int(bucket_counts.get(selected_page_bucket) or 0) if selected_page_bucket else 0
    current_profile_count = int(profile_counts.get(selected_project_type) or 0) if selected_project_type else 0
    current_combo_count = int(
        ((nested_counts.get(selected_project_type) or {}) if isinstance(nested_counts.get(selected_project_type), dict) else {}).get(selected_page_bucket)
        or 0
    )
    current_combo_profile_count = int(
        (
            ((nested_profile_counts.get(selected_project_type) or {}) if isinstance(nested_profile_counts.get(selected_project_type), dict) else {}).get(
                selected_page_bucket
            )
        )
        or 0
    )
    latest_item = summary.get("latest_item") if isinstance(summary.get("latest_item"), dict) else {}
    latest_label = str((latest_item or {}).get("filename") or "暂无样板").strip()
    latest_ts = _format_iso_ts_short((latest_item or {}).get("ts"))
    latest_meta_parts = []
    if latest_ts:
        latest_meta_parts.append(latest_ts)
    latest_project_type = str((latest_item or {}).get("project_type") or "").strip()
    latest_bucket = _template_page_bucket_label((latest_item or {}).get("template_page_bucket"))
    if latest_project_type:
        latest_meta_parts.append(latest_project_type)
    if latest_bucket:
        latest_meta_parts.append(latest_bucket)
    latest_profile_count = int((latest_item or {}).get("template_chapter_profile_count") or 0)
    latest_priority_label = str((latest_item or {}).get("learning_priority_label") or "").strip()
    if latest_profile_count > 0:
        latest_meta_parts.append(f"已学{latest_profile_count}章")
    if latest_priority_label:
        latest_meta_parts.append(latest_priority_label)
    latest_meta = " · ".join(latest_meta_parts) if latest_meta_parts else "等待入库"
    st.markdown(
        "".join(
            [
                "<div class='zf-library-summary'>",
                (
                    "<div class='zf-library-stat'>"
                    f"<span>总样板数</span><strong>{total_count}</strong>"
                    f"<em>累计学习 {total_profile_count} 个章节画像</em></div>"
                ),
                (
                    "<div class='zf-library-stat'>"
                    f"<span>{html.escape(selected_project_type or '当前类型')} · {_template_page_bucket_label(selected_page_bucket)}</span>"
                    f"<strong>{current_combo_count}</strong>"
                    f"<em>类型总数 {current_count} · 档位总数 {current_bucket_count} · 已学 {current_combo_profile_count} 章</em></div>"
                ),
                (
                    "<div class='zf-library-stat'>"
                    f"<span>最近入库</span><strong>{html.escape(latest_label)}</strong>"
                    f"<em>{html.escape(latest_meta)}</em></div>"
                ),
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )
    if current_profile_count > 0:
        st.caption(f"当前项目类型累计已学习 {current_profile_count} 个章节画像；生成时会优先匹配同类型、同档位且优先级更高的样板。")
    if total_count > 0:
        st.caption(
            f"全库高优先样板 {high_priority_count} 份；系统回流样板 {accepted_feedback_count} 份；带反馈信号样板 {system_feedback_count} 份。"
        )
    try:
        base_digest_payload = _get_json(
            base_url,
            "/ingest/template-library/learning-digest",
            actions_key,
            params={
                "project_type": selected_project_type,
                "template_page_bucket": selected_page_bucket,
            },
            timeout=40,
        )
        base_learning_digest = base_digest_payload.get("digest") if isinstance(base_digest_payload, dict) else {}
        if not isinstance(base_learning_digest, dict):
            base_learning_digest = {}
    except Exception as e:
        base_learning_digest = {}
        st.caption(f"样板学习画像暂不可用：{e}")

    base_scene_coverage = (
        base_learning_digest.get("scene_coverage") if isinstance(base_learning_digest.get("scene_coverage"), list) else []
    )
    existing_scene_filter = _normalize_scene_tags_ui(st.session_state.get("sample_library_scene_filter") or [])
    scene_filter_options: list[str] = []
    scene_seen: set[str] = set()
    for raw_tag in existing_scene_filter + [
        str(item.get("scene_tag") or "").strip() for item in base_scene_coverage if isinstance(item, dict)
    ]:
        scene_tag = str(raw_tag or "").strip()
        if not scene_tag or scene_tag in scene_seen:
            continue
        scene_seen.add(scene_tag)
        scene_filter_options.append(scene_tag)
    st.multiselect(
        "子场景筛选（可选）",
        options=scene_filter_options,
        key="sample_library_scene_filter",
        help="例如医院、学校、地库、局部改造。筛选后，样板画像和列表都会优先显示对应子场景。",
    )
    selected_scene_tags = _normalize_scene_tags_ui(st.session_state.get("sample_library_scene_filter") or [])
    if selected_scene_tags:
        try:
            digest_payload = _get_json(
                base_url,
                "/ingest/template-library/learning-digest",
                actions_key,
                params={
                    "project_type": selected_project_type,
                    "template_page_bucket": selected_page_bucket,
                    "template_scene_tags": ",".join(selected_scene_tags),
                },
                timeout=40,
            )
            learning_digest = digest_payload.get("digest") if isinstance(digest_payload, dict) else {}
            if not isinstance(learning_digest, dict):
                learning_digest = {}
        except Exception as e:
            learning_digest = {}
            st.caption(f"子场景学习画像暂不可用：{e}")
    else:
        learning_digest = dict(base_learning_digest)

    theme_coverage = learning_digest.get("theme_coverage") if isinstance(learning_digest.get("theme_coverage"), list) else []
    anchor_coverage = learning_digest.get("anchor_coverage") if isinstance(learning_digest.get("anchor_coverage"), list) else []
    scene_coverage = learning_digest.get("scene_coverage") if isinstance(learning_digest.get("scene_coverage"), list) else []
    coverage_hint = str(learning_digest.get("coverage_hint") or "").strip()
    if coverage_hint:
        st.caption(coverage_hint)
    elif selected_scene_tags:
        st.caption("当前子场景下暂未形成稳定学习画像，可继续补充同场景高质量样板。")
    if theme_coverage:
        theme_text = " · ".join(
            [
                f"{str(item.get('theme') or '').strip()}({int(item.get('count') or 0)})"
                for item in theme_coverage
                if str(item.get("theme") or "").strip()
            ][:6]
        )
        if theme_text:
            st.markdown("**已学会的高频章节**")
            st.caption(theme_text)
    if anchor_coverage:
        anchor_text = " · ".join(
            [
                f"{str(item.get('anchor') or '').strip()}({int(item.get('count') or 0)})"
                for item in anchor_coverage
                if str(item.get("anchor") or "").strip()
            ][:6]
        )
        if anchor_text:
            st.markdown("**高频写法锚点**")
            st.caption(anchor_text)
    if scene_coverage:
        scene_text = " · ".join(
            [
                f"{str(item.get('scene_tag') or '').strip()}({int(item.get('count') or 0)})"
                for item in scene_coverage
                if str(item.get("scene_tag") or "").strip()
            ][:6]
        )
        if scene_text:
            st.markdown("**高频子场景**")
            st.caption(scene_text)

    try:
        recent_items_payload = _get_json(
            base_url,
            "/ingest/template-library/items",
            actions_key,
            params={"limit": 5},
            timeout=40,
        )
        recent_items = recent_items_payload.get("items") if isinstance(recent_items_payload, dict) else []
        if not isinstance(recent_items, list):
            recent_items = []
    except Exception as e:
        recent_items = []
        st.caption(f"最近入库样板暂不可用：{e}")

    st.markdown("**最近入库样板（可删除）**")
    _render_template_library_items(
        base_url,
        actions_key,
        recent_items,
        key_prefix="sample_library_recent_delete",
        empty_text="样板库里还没有可管理的已入库样板。",
        include_project_type=True,
    )

    st.selectbox("归档项目类型", options=PROJECT_TYPES, key="sample_library_project_type")
    st.selectbox(
        "样板档位",
        options=TEMPLATE_PAGE_BUCKETS,
        key="sample_library_page_bucket",
        format_func=_template_page_bucket_label,
    )
    st.text_input(
        "归档子场景（可选）",
        key="sample_library_scene_tags",
        placeholder="例如：医院, 局部改造, 地库",
    )
    sample_files = st.file_uploader(
        "上传优秀案例",
        type=["pdf", "doc", "docx", "txt", "md"],
        accept_multiple_files=True,
        key="sample_library_files",
        help="建议上传高质量最终版施组、评审得分高的案例或稳定可复用章节样板。",
    )
    st.text_area(
        "样板说明（可选）",
        key="sample_library_note",
        height=78,
        placeholder="例如：房建总承包，地库+装配式，目录完整、表达干净、评分高。",
    )
    st.caption("删除样板后会同步移出样板库；只有在没有其他记录继续引用时，系统才会清理对应源文件。")
    if st.button("加入样板库", key="sample_library_upload_btn", width="stretch", type="secondary"):
        try:
            target_type = str(st.session_state.get("sample_library_project_type") or "").strip()
            if target_type not in PROJECT_TYPES:
                raise ValueError("请选择有效的项目类型")
            target_bucket = str(st.session_state.get("sample_library_page_bucket") or "").strip()
            if target_bucket not in TEMPLATE_PAGE_BUCKETS:
                raise ValueError("请选择有效的样板档位")
            if not sample_files:
                raise ValueError("请先上传至少 1 个优秀案例文件")
            note = str(st.session_state.get("sample_library_note") or "").strip()
            scene_tags = _normalize_scene_tags_ui(st.session_state.get("sample_library_scene_tags") or "")
            saved = _ingest_docs(
                base_url,
                list(sample_files or []),
                None,
                source_hint="template_library",
                extra_params={
                    "project_type": target_type,
                    "library_scope": "template_library",
                    "library_note": note,
                    "template_page_bucket": target_bucket,
                    "template_scene_tags": ",".join(scene_tags),
                },
            )
            saved_count = len(saved.get("saved") or [])
            _queue_widget_update("sample_library_note", "")
            _queue_widget_update("sample_library_files", [])
            _queue_widget_update("sample_library_scene_tags", "")
            st.session_state["template_library_flash"] = (
                f"已加入样板库：{target_type} / {_template_page_bucket_label(target_bucket)} / {saved_count} 个文件。"
            )
            st.rerun()
        except Exception as e:
            st.error(f"样板入库失败: {e}")

    try:
        items_payload = _get_json(
            base_url,
            "/ingest/template-library/items",
            actions_key,
            params={
                "project_type": st.session_state.get("sample_library_project_type"),
                "template_page_bucket": st.session_state.get("sample_library_page_bucket"),
                "template_scene_tags": ",".join(selected_scene_tags),
                "sort_by": "priority",
                "limit": 8,
            },
            timeout=40,
        )
        items = items_payload.get("items") if isinstance(items_payload, dict) else []
        if not isinstance(items, list):
            items = []
    except Exception as e:
        items = []
        st.caption(f"样板列表暂不可用：{e}")

    title_parts = [f"当前类型样板 · {_template_page_bucket_label(st.session_state.get('sample_library_page_bucket'))}"]
    if selected_scene_tags:
        title_parts.append(" / ".join(selected_scene_tags))
    st.markdown(f"**{' · '.join(title_parts)}**")
    st.caption("当前列表按学习优先级排序，优先显示更适合作为系统学习参考的样板。")
    _render_template_library_items(
        base_url,
        actions_key,
        items,
        key_prefix="sample_library_filtered_delete",
        empty_text="当前项目类型和页数档位下还没有已入库样板。",
        include_project_type=False,
    )


def _append_log(message: str) -> None:
    st.session_state.setdefault("run_logs", [])
    st.session_state["run_logs"].append(f"[{_now()}] {message}")


def _render_logs(container) -> None:
    logs = st.session_state.get("run_logs", [])
    if not logs:
        container.markdown("<div class='zf-log-idle'>等待任务开始…</div>", unsafe_allow_html=True)
        return
    with container.container():
        active = bool(st.session_state.get("active_job"))
        title = f"运行日志（最近 {min(len(logs), 300)} 行）"
        with st.expander(title, expanded=active):
            st.code("\n".join(logs[-300:]), language="text")


def _render_progress(percent: int, label: str) -> None:
    p = max(0, min(100, int(percent)))


SUBMISSION_STAGE_LABELS = {
    "queued": "等待开始",
    "tender_parse": "解析招标文件",
    "boq_parse": "解析工程量清单",
    "ingest_tender_qa": "入库招标/答疑",
    "ingest_boq": "入库工程量清单",
    "ingest_drawing_standard": "入库图纸/标准资料",
    "ingest_site_photo": "入库现场照片",
    "front_matter_plan": "生成目录与索引计划",
    "plan_save": "保存计划配置",
    "generate_async": "启动异步生成",
}
JOB_STAGE_LABELS = {
    **SUBMISSION_STAGE_LABELS,
    "job_started": "任务已启动",
    "mode_switch": "模式切换",
    "mode_ready": "模式确认",
    "agent_ready": "多Agent就绪",
    "variant_running": "并行编制方案",
    "cross_variant_check": "跨方案审计",
    "exporting": "导出成品",
    "done": "任务完成",
    "failed": "任务失败",
    "cancelled": "任务已取消",
}


def _uploaded_file_size(uf: Any) -> int:
    try:
        size = getattr(uf, "size", None)
        if size is not None:
            return max(0, int(size))
    except Exception:
        pass
    try:
        return max(0, int(len(uf.getvalue())))
    except Exception:
        return 0


def _format_uploaded_file_size(size_bytes: int) -> str:
    size = max(0, int(size_bytes or 0))
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _render_uploaded_file_summary(group_label: str, uploaded_files: list[Any] | None) -> None:
    files = list(uploaded_files or [])
    if not files:
        st.markdown(
            "<div class='zf-upload-selected-empty'>当前未选择文件</div>",
            unsafe_allow_html=True,
        )
        return
    rows: list[str] = []
    for idx, uf in enumerate(files, start=1):
        file_name = html.escape(str(getattr(uf, "name", "") or f"未命名文件{idx}").strip() or f"未命名文件{idx}")
        file_size = html.escape(_format_uploaded_file_size(_uploaded_file_size(uf)))
        rows.append(
            "<div class='zf-upload-file-row'>"
            f"<span class='zf-upload-file-index'>{idx:02d}</span>"
            f"<span class='zf-upload-file-name' title='{file_name}'>{file_name}</span>"
            f"<span class='zf-upload-file-size'>{file_size}</span>"
            "</div>"
        )
    st.markdown(
        "<div class='zf-upload-selected'>"
        "<div class='zf-upload-selected-head'>"
        f"<span class='zf-upload-selected-title'>{html.escape(group_label)}</span>"
        f"<span class='zf-upload-selected-count'>已选 {len(files)} 个</span>"
        "</div>"
        f"<div class='zf-upload-file-list'>{''.join(rows)}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _submission_file_refs(files: list[Any] | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for uf in files or []:
        refs.append(
            {
                "name": str(getattr(uf, "name", "") or "").strip(),
                "size": _uploaded_file_size(uf),
            }
        )
    refs.sort(key=lambda item: (str(item.get("name") or ""), int(item.get("size") or 0)))
    return refs


def _build_submission_signature(
    *,
    topic: str,
    project_id: str,
    project_type: str,
    generation_mode: str,
    selected_templates: list[str],
    total_pages_target: int,
    tender_files: list[Any] | None,
    boq_files: list[Any] | None,
    drawing_files: list[Any] | None,
    site_photo_files: list[Any] | None,
) -> str:
    raw = {
        "topic": str(topic or "").strip(),
        "project_id": str(project_id or "").strip(),
        "project_type": str(project_type or "").strip(),
        "generation_mode": str(generation_mode or "").strip(),
        "selected_templates": [str(x).strip() for x in (selected_templates or []) if str(x).strip()],
        "total_pages_target": int(total_pages_target or 0),
        "files": {
            "tender_qa": _submission_file_refs(tender_files),
            "boq": _submission_file_refs(boq_files),
            "drawing_standard": _submission_file_refs(drawing_files),
            "site_photo": _submission_file_refs(site_photo_files),
        },
    }
    return hashlib.sha1(
        json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _get_submission_flow() -> dict[str, Any]:
    flow = st.session_state.get("submission_flow")
    return dict(flow) if isinstance(flow, dict) else {}


def _save_submission_flow(flow: dict[str, Any] | None) -> None:
    st.session_state["submission_flow"] = dict(flow) if isinstance(flow, dict) and flow else None


def _clear_submission_flow() -> None:
    st.session_state["submission_flow"] = None


def _submission_flow_stage_label(flow: dict[str, Any] | None) -> str:
    stage = str((flow or {}).get("stage") or "queued").strip()
    return str(SUBMISSION_STAGE_LABELS.get(stage) or stage or "等待开始")


def _submission_flow_notice(flow: dict[str, Any] | None) -> tuple[str, str] | None:
    current = dict(flow or {})
    if not current:
        return None
    status = str(current.get("status") or "").strip().lower()
    stage_label = _submission_flow_stage_label(current)
    detail = str(current.get("detail") or "").strip()
    if status == "running":
        text = f"任务准备中：{stage_label}"
        if detail and detail != stage_label:
            text = f"{text} · {detail}"
        project_id = str(current.get("project_id") or "").strip()
        if project_id:
            text = f"{text} · 项目ID：{project_id}"
        return ("running", text)
    if status == "failed":
        text = "上次提交流程已中断"
        error = str(current.get("error") or detail).strip()
        if error:
            text = f"{text}：{error}"
        return ("error", text)
    return None


def _touch_submission_flow(flow: dict[str, Any] | None, **updates: Any) -> dict[str, Any]:
    current = dict(flow or {})
    current.update(updates)
    current["updated_at"] = time.time()
    _save_submission_flow(current)
    return current


def _start_submission_flow(
    *,
    signature: str,
    topic: str,
    project_id: str,
    project_type: str,
) -> dict[str, Any]:
    flow = {
        "signature": str(signature or "").strip(),
        "status": "running",
        "stage": "queued",
        "detail": "",
        "topic": str(topic or "").strip(),
        "project_id": str(project_id or "").strip(),
        "project_type": str(project_type or "").strip(),
        "tender_parsed": False,
        "boq_parsed": False,
        "ingested_hints": [],
        "front_matter_planned": False,
        "plan_saved": False,
        "job_id": None,
        "error": None,
        "started_at": time.time(),
        "updated_at": time.time(),
        "resume_count": 0,
        "retry_count": 0,
    }
    _save_submission_flow(flow)
    return flow


def _load_saved_tender_matrix(project_id: str | None) -> dict[str, Any] | None:
    try:
        from backend.zhifei_autoplan.tender_store import load_tender_matrix

        matrix = load_tender_matrix(project_id=project_id)
        return matrix if isinstance(matrix, dict) else None
    except Exception:
        return None


def _has_saved_boq_data(project_id: str | None) -> bool:
    try:
        from backend.zhifei_autoplan.boq_store import load_boq_data

        return isinstance(load_boq_data(project_id=project_id), dict)
    except Exception:
        return False


def _has_saved_plan(project_id: str | None) -> bool:
    try:
        from backend.zhifei_autoplan.plan_store import load_plan

        return isinstance(load_plan(project_id=project_id), dict)
    except Exception:
        return False
    txt = str(label or "").strip()
    try:
        st.progress(p, text=txt)
    except TypeError:
        st.progress(p)
        if txt:
            st.caption(txt)


def _render_runtime_summary() -> None:
    image_provider = str(st.session_state.get("image_provider") or "google").strip() or "google"
    image_model = str(st.session_state.get("image_model") or "banana").strip() or "banana"
    blocks = [
        ("文本主模型", PRIMARY_TEXT_MODEL),
        ("次选链路", SECONDARY_TEXT_MODEL),
        ("目录策略", "评审标准优先"),
        ("图片模型", f"{image_provider}/{image_model}"),
    ]
    html_blocks = "".join(
        (
            "<div class='zf-runtime-pill'>"
            f"<span>{html.escape(label)}</span>"
            f"<strong>{html.escape(value)}</strong>"
            "</div>"
        )
        for label, value in blocks
    )
    st.markdown(f"<div class='zf-runtime-summary'>{html_blocks}</div>", unsafe_allow_html=True)


def _inject_ui_style() -> None:
    st.markdown(
        """
<style>
:root {
  --brand-50: #EEF6FF;
  --brand-100: #DCEEFF;
  --brand-200: #BEDBFB;
  --brand-300: #8FBEEC;
  --brand-400: #5D9AD9;
  --brand-500: #347ABF;
  --brand-600: #1F629F;
  --brand-700: #144B84;
  --brand-800: #103B67;
  --brand-900: #0F3154;

  --bg: #F3F6FA;
  --surface: #FFFFFF;
  --surface-soft: #F7FAFD;
  --surface-muted: #EEF3F8;
  --surface-deep: #E3EBF4;

  --border: #D7E1EC;
  --border-strong: #BFD0E2;

  --text: #24384F;
  --text-2: #4B617B;
  --text-3: #73879E;
  --text-on-brand: #FFFFFF;

  --success-bg: #EAF5EE;
  --success-text: #215B4B;

  --info-bg: #EAF2FB;
  --info-text: #1C4E84;

  --warning-bg: #FFF5E8;
  --warning-text: #8A5A17;

  --china-red: #DE2910;
  --danger-bg: #FDEEEE;
  --danger-text: #B03E3E;
  --danger-border: #E5B2B2;

  --focus-ring: rgba(17, 50, 133, 0.18);

  --shadow-sm: 0 8px 20px rgba(20, 75, 132, 0.06);
  --shadow-md: 0 16px 40px rgba(20, 75, 132, 0.08);

  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;

  /* aliases */
  --surface-2: var(--surface-soft);
  --text-secondary: var(--text-2);
  --text-tertiary: var(--text-3);
  --accent: var(--brand-700);
  --accent-hover: var(--brand-800);
  --soft-hover: var(--brand-50);
  --selected: var(--brand-100);
  --danger: var(--danger-text);
  --error-bg: var(--danger-bg);
  --error-text: var(--danger-text);
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(220, 238, 255, 0.78), transparent 30%),
    linear-gradient(180deg, #F7FAFD 0%, #F3F6FA 100%);
  color: var(--text);
  font-family: "Avenir Next", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: var(--bg) !important;
}

[data-testid="stHeader"] {
  background: transparent;
  border-bottom: 1px solid transparent;
}

div.block-container {
  max-width: 1440px;
  padding-top: 0;
  padding-bottom: 12px;
  row-gap: 4px;
}

.zf-page-title {
  font-size: 30px;
  line-height: 36px;
  font-weight: 700;
  color: var(--brand-800);
  margin: 0;
  position: relative;
  padding-bottom: 3px;
}

.zf-page-title::after {
  content: "";
  display: block;
  width: 56px;
  height: 3px;
  margin-top: 8px;
  border-radius: 2px;
  background: var(--brand-700);
}

.zf-page-subtitle {
  font-size: 14px;
  line-height: 19px;
  color: var(--text-2);
  font-weight: 700;
  margin-bottom: 2px;
}

.zf-runtime-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 4px 0 12px 0;
}

.zf-runtime-pill {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface-soft);
}

.zf-runtime-pill span {
  display: block;
  color: var(--text-3);
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
}

.zf-runtime-pill strong {
  display: block;
  margin-top: 5px;
  color: var(--brand-800);
  font-size: 16px;
  line-height: 22px;
  font-weight: 800;
}

.zf-step-kicker {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--brand-200);
  background: var(--brand-50);
  color: var(--brand-700);
  font-size: 12px;
  line-height: 16px;
  font-weight: 800;
  letter-spacing: 0.3px;
}

.zf-muted-note {
  margin-top: 4px;
  color: var(--text-3);
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
}

.zf-library-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 8px 0 12px 0;
}

.zf-library-stat {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: linear-gradient(180deg, #F7FAFD 0%, #EFF4FA 100%);
}

.zf-library-stat span {
  display: block;
  color: var(--text-3);
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
}

.zf-library-stat strong {
  display: block;
  margin-top: 4px;
  color: var(--brand-800);
  font-size: 16px;
  line-height: 22px;
  font-weight: 800;
}

.zf-library-stat em {
  display: block;
  margin-top: 6px;
  color: var(--text-3);
  font-size: 12px;
  line-height: 16px;
  font-style: normal;
  font-weight: 600;
}

.zf-library-item {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-soft);
  margin-top: 8px;
}

.zf-library-item strong {
  display: block;
  color: var(--brand-800);
  font-size: 15px;
  line-height: 21px;
  font-weight: 800;
}

.zf-library-item span {
  display: block;
  margin-top: 4px;
  color: var(--text-3);
  font-size: 12px;
  line-height: 17px;
  font-weight: 700;
}

.zf-library-item p {
  margin: 7px 0 0 0;
  color: var(--text-2);
  font-size: 13px;
  line-height: 19px;
  font-weight: 600;
}

h2 {
  font-size: 26px;
  line-height: 34px;
  font-weight: 700;
  color: var(--brand-800);
  border-left: 3px solid var(--brand-700);
  padding-left: 10px;
  margin: 2px 0 8px 0;
}

h3 {
  font-size: 19px;
  line-height: 26px;
  font-weight: 600;
  color: var(--brand-800);
  border-left: 3px solid var(--brand-700);
  padding-left: 10px;
  margin: 2px 0 8px 0;
}

p, .stCaption, [data-testid="stMarkdownContainer"] p {
  color: var(--text-2);
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
}

p code,
li code,
.stCaption code,
[data-testid="stMarkdownContainer"] code,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] pre code,
code {
  background: var(--brand-50) !important;
  color: var(--brand-800) !important;
  border: 1px solid var(--brand-200) !important;
  border-radius: 8px !important;
  padding: 2px 8px !important;
  font-size: 13px !important;
  line-height: 18px !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}

label, [data-testid="stWidgetLabel"] p {
  color: var(--text);
  font-size: 15px;
  line-height: 20px;
  font-weight: 600;
}

[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface);
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
  padding-top: 0;
  padding-bottom: 0;
}

.zf-top-strip [data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--radius-sm);
}

.zf-top-strip [data-testid="stVerticalBlockBorderWrapper"] > div {
  padding-top: 0;
  padding-bottom: 0;
}

.zf-top-strip [data-testid="stExpander"] {
  margin-top: 8px;
}

.zf-top-strip [data-testid="stExpander"] details {
  background: var(--surface-soft);
  border-color: var(--border);
}

.zf-top-strip [data-testid="stExpander"] summary {
  background: var(--surface-soft) !important;
  color: var(--brand-800) !important;
  min-height: 38px;
  font-size: 14px;
  line-height: 18px;
}

.zf-top-strip [data-testid="stExpander"] details > summary,
.zf-top-strip [data-testid="stExpander"] details[open] > summary,
.zf-top-strip [data-testid="stExpander"] summary:hover,
.zf-top-strip [data-testid="stExpander"] summary:focus-visible {
  background: var(--surface-soft) !important;
  color: var(--brand-800) !important;
  border-color: var(--border) !important;
  box-shadow: none !important;
}

.zf-top-strip [data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"] {
  border: 0;
  box-shadow: none;
  background: transparent;
}

.zf-top-strip [data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"] > div {
  padding-top: 6px;
  padding-bottom: 2px;
}

.zf-top-strip .zf-notice {
  margin: 0;
  padding: 7px 12px;
  font-size: 14px;
  line-height: 18px;
  font-weight: 700;
  }

.zf-maint-note {
  color: var(--text-3);
  font-size: 13px;
  line-height: 18px;
  margin: 0 0 6px 0;
}

.zf-maint-zone {
  margin-top: 18px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  opacity: 0.74;
}

.zf-maint-zone [data-testid="stExpander"] {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

.zf-maint-zone [data-testid="stExpander"] details,
.zf-maint-zone [data-testid="stExpander"] details[open],
.zf-maint-zone [data-testid="stExpander"] section,
.zf-maint-zone [data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"],
.zf-maint-zone [data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"] > div {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

.zf-maint-zone [data-testid="stExpander"] summary {
  max-width: 240px;
  min-height: 30px !important;
  background: var(--surface-soft) !important;
  color: var(--text-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  font-size: 12px !important;
  line-height: 16px !important;
  font-weight: 600 !important;
}

.zf-maint-zone [data-testid="stExpander"] details[open] > summary,
.zf-maint-zone [data-testid="stExpander"] summary:hover,
.zf-maint-zone [data-testid="stExpander"] summary:focus-visible {
  background: var(--surface-muted) !important;
  color: var(--brand-700) !important;
  border-color: var(--border-strong) !important;
}

.zf-maint-zone .zf-maint-note {
  margin-top: 4px;
  margin-bottom: 8px;
  font-size: 12px;
  line-height: 17px;
}

.zf-maint-footer {
  display: none;
}

.zf-maint-footer .zf-maint-note {
  margin: 0;
}

.zf-inline-summary,
.zf-mini-thread,
.zf-mini-thread-item,
.zf-mini-thread-role,
.zf-mini-thread-body {
  display: none !important;
}

.zf-constraint-chat {
  margin-top: 10px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 16px 14px;
}

.zf-constraint-chat-shell {
  margin-top: 4px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] {
  margin: 0 !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] > label {
  display: none !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] textarea[aria-hidden="true"] {
  display: none !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] div[aria-hidden="true"] {
  display: none !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] textarea {
  min-height: 184px !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
  padding: 20px 22px !important;
  font-size: 18px !important;
  line-height: 30px !important;
  resize: vertical !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] textarea::placeholder {
  color: var(--text-3) !important;
  opacity: 1 !important;
}

.zf-constraint-chat-shell [data-testid="stTextArea"] textarea:focus {
  border-color: var(--brand-400) !important;
  box-shadow: 0 0 0 3px rgba(17, 50, 133, 0.08) !important;
}

.zf-constraint-chat-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.zf-constraint-chat-note {
  color: var(--text-2);
  font-size: 13px;
  line-height: 20px;
}

.zf-log-idle {
  margin-top: 6px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--info-bg);
  color: var(--info-text);
  font-size: 14px;
  line-height: 18px;
  font-weight: 600;
}

.zf-top-strip [data-testid="stColumn"] {
  display: flex;
  align-items: center;
}

[data-testid="stExpander"] details {
  transition: all 180ms ease;
}

[data-testid="stExpander"] details[open] {
  border: 1px solid var(--brand-200);
  border-radius: var(--radius-md);
  background: var(--surface-soft);
  box-shadow: var(--shadow-sm);
}

[data-testid="stExpander"] summary {
  background: var(--surface) !important;
  color: var(--text);
  min-height: 42px;
  padding-top: 2px;
  padding-bottom: 2px;
}

[data-testid="stExpander"] details[open] summary {
  background: var(--surface-soft) !important;
  color: var(--brand-800) !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] section,
[data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"] > div {
  background: var(--surface) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
}

[data-testid="stExpander"] details[open],
[data-testid="stExpander"] details[open] > div {
  background: var(--surface-soft) !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stChatInput textarea,
[data-testid="stChatInputTextArea"],
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
  min-height: 42px;
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  box-shadow: none !important;
  font-size: 15px !important;
}

.zf-static-label {
  color: var(--text) !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  margin: 0 0 0.35rem 0 !important;
}

.zf-static-field {
  min-height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface-soft);
  color: var(--text);
  box-shadow: none;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  padding: 0 0.9rem;
}

.stTextArea textarea {
  min-height: 112px;
  background: var(--surface) !important;
  color: var(--text) !important;
  line-height: 1.55;
}

.stChatInput,
[data-testid="stChatInput"] {
  background: transparent !important;
}

[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
  background: var(--surface-soft) !important;
  border-color: var(--border) !important;
  box-shadow: none !important;
}

.stChatInput textarea,
[data-testid="stChatInputTextArea"] {
  background: var(--surface) !important;
  color: var(--text) !important;
  line-height: 1.5 !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
}

[data-testid="stChatInputSubmitButton"] {
  background: var(--surface-deep) !important;
  color: var(--brand-700) !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
}

[data-testid="stChatInputSubmitButton"]:hover {
  background: var(--brand-50) !important;
  color: var(--brand-800) !important;
  border-color: var(--brand-300) !important;
}

[data-testid="stChatInputSubmitButton"]:active,
[data-testid="stChatInputSubmitButton"]:focus-visible {
  background: var(--brand-100) !important;
  color: var(--brand-800) !important;
  border-color: var(--brand-400) !important;
  box-shadow: 0 0 0 3px var(--focus-ring) !important;
}

[data-testid="stChatInputSubmitButton"] svg,
[data-testid="stChatInputSubmitButton"] path {
  fill: currentColor !important;
  color: inherit !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
.stChatInput textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder {
  color: var(--text-3) !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus,
.stChatInput textarea:focus,
[data-testid="stChatInputTextArea"]:focus,
.stSelectbox [data-baseweb="select"] > div:focus-within,
.stMultiSelect [data-baseweb="select"] > div:focus-within {
  border-color: var(--brand-700) !important;
  box-shadow: 0 0 0 3px var(--focus-ring) !important;
}

.stButton > button:focus-visible,
[data-testid="stFormSubmitButton"] > button:focus-visible,
button:focus-visible {
  outline: none !important;
  box-shadow: 0 0 0 3px var(--focus-ring) !important;
}

.stNumberInput [data-testid="stNumberInputStepUp"],
.stNumberInput [data-testid="stNumberInputStepDown"] {
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text-secondary) !important;
  width: 26px !important;
  min-width: 26px !important;
  height: 26px !important;
  border-radius: 7px !important;
}

.stNumberInput [data-testid="stNumberInputStepUp"]:hover,
.stNumberInput [data-testid="stNumberInputStepDown"]:hover {
  background: var(--brand-50) !important;
  color: var(--brand-800) !important;
}

.stNumberInput [data-testid="stNumberInputStepUp"]:active,
.stNumberInput [data-testid="stNumberInputStepDown"]:active,
.stNumberInput [data-testid="stNumberInputStepUp"]:focus,
.stNumberInput [data-testid="stNumberInputStepDown"]:focus {
  background: var(--brand-100) !important;
  color: var(--brand-800) !important;
  border-color: var(--brand-400) !important;
}

[data-testid="stFileUploader"] {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  padding: 0;
  min-height: 176px;
  display: flex;
  flex-direction: column;
  justify-content: stretch;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 176px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.22);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: stretch;
  position: relative;
  overflow: hidden;
  gap: 14px;
}

.zf-upload-grid [data-testid="stFileUploaderDropzone"] section,
.zf-upload-grid [data-testid="stFileUploaderDropzone"] > div,
.zf-upload-grid [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"] {
  width: 100%;
}

[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--brand-400);
  background: var(--brand-50);
}

[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploader"] small {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  max-height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  font-size: 0 !important;
  line-height: 0 !important;
  pointer-events: none !important;
}

.zf-upload-helper-inner {
  width: 100%;
  flex: 1 1 auto;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 8px;
  pointer-events: none;
}

.zf-upload-helper-title {
  font-size: 19px;
  line-height: 26px;
  color: var(--text);
  font-weight: 700;
  letter-spacing: 0.1px;
}

.zf-upload-helper-sub {
  font-size: 15px;
  line-height: 21px;
  color: var(--text-2);
  font-weight: 600;
}

[data-testid="stFileUploaderDropzone"] button {
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  border-radius: 12px !important;
  min-height: 44px !important;
  min-width: 142px !important;
  padding: 0 18px !important;
  position: relative !important;
  box-shadow: var(--shadow-sm) !important;
  z-index: 3;
  font-size: 16px !important;
  line-height: 20px !important;
  font-weight: 700 !important;
  text-indent: 0 !important;
  overflow: visible !important;
  opacity: 1 !important;
  margin-top: auto !important;
  align-self: center !important;
}

[data-testid="stFileUploaderDropzone"] button::after {
  display: none !important;
}

.stButton > button {
  height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 15px;
  font-weight: 600;
  box-shadow: none !important;
}

.stButton > button:hover {
  background: var(--soft-hover);
  border-color: var(--brand-300);
}

.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: var(--text-on-brand) !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  letter-spacing: 0.2px;
  text-shadow: none !important;
  min-height: 50px !important;
  height: 50px !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 18px rgba(17, 50, 133, 0.12) !important;
}

.stButton > button[kind="primary"] *,
[data-testid="stFormSubmitButton"] > button[kind="primary"] *,
.zf-run-wrap .stButton > button[kind="primary"] *,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button[kind="primary"] * {
  color: var(--text-on-brand) !important;
  fill: var(--text-on-brand) !important;
  -webkit-text-fill-color: var(--text-on-brand) !important;
  opacity: 1 !important;
}

.zf-run-wrap .stButton > button,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button {
  background: var(--brand-700) !important;
  border-color: var(--brand-700) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: var(--text-on-brand) !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  min-height: 52px !important;
  height: 52px !important;
  border-radius: 12px !important;
  text-shadow: none !important;
}

.zf-run-wrap .stButton > button:hover,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button:hover {
  background: var(--brand-800) !important;
  border-color: var(--brand-800) !important;
}

.zf-run-wrap .stButton > button:active,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button:active,
.zf-run-wrap .stButton > button:focus-visible,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button:focus-visible {
  background: var(--brand-800) !important;
  border-color: var(--brand-800) !important;
  color: var(--text-on-brand) !important;
  -webkit-text-fill-color: var(--text-on-brand) !important;
}

.zf-run-wrap .stButton > button *,
.zf-run-wrap [data-testid="stFormSubmitButton"] > button * {
  color: var(--text-on-brand) !important;
  fill: var(--text-on-brand) !important;
  -webkit-text-fill-color: var(--text-on-brand) !important;
  opacity: 1 !important;
}

.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
}

.stButton > button[kind="primary"]:active,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:active {
  background: var(--brand-800) !important;
  border-color: var(--brand-800) !important;
}

[data-testid="stFormSubmitButton"] > button {
  height: 44px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  box-shadow: none !important;
}

[data-testid="stFormSubmitButton"] > button:hover {
  background: var(--soft-hover);
  border-color: var(--brand-300);
}

[data-testid="stCheckbox"] > label {
  gap: 8px;
}

label[data-baseweb="checkbox"] > span:first-child,
label[data-baseweb="radio"] > span:first-child {
  width: 20px !important;
  min-width: 20px !important;
  height: 20px !important;
  min-height: 20px !important;
  border-radius: 6px !important;
  border: 1px solid var(--border-strong) !important;
  background: var(--surface) !important;
  box-shadow: none !important;
  color: transparent !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}

label[data-baseweb="checkbox"] > span:first-child:hover,
label[data-baseweb="radio"] > span:first-child:hover,
div[role="checkbox"],
div[role="radio"] {
  background: var(--surface) !important;
  border-color: var(--border-strong) !important;
  color: transparent !important;
}

label[data-baseweb="checkbox"]:has(input[aria-checked="true"]) > span:first-child,
label[data-baseweb="radio"]:has(input[aria-checked="true"]) > span:first-child {
  background: var(--china-red) !important;
  border-color: var(--china-red) !important;
  color: #FFFFFF !important;
}

[data-testid="stCheckbox"] input[type="checkbox"] {
  accent-color: var(--china-red);
}

[data-testid="stRadio"] input[type="radio"] {
  accent-color: var(--china-red);
}

[data-testid="stCheckbox"] input[type="checkbox"]:focus,
[data-testid="stRadio"] input[type="radio"]:focus {
  box-shadow: 0 0 0 3px var(--focus-ring);
}

[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"],
[data-baseweb="radio"] [role="radio"][aria-checked="true"] {
  background: var(--china-red) !important;
  border-color: var(--china-red) !important;
  color: var(--text-on-brand) !important;
}

button[role="switch"][aria-checked="true"] {
  background: var(--brand-700) !important;
  border-color: var(--brand-700) !important;
}

[data-testid="stChatMessage"] {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

[data-testid="stMetric"] {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
  color: var(--text) !important;
}

[data-testid="stAlert"] {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--info-bg) !important;
  color: var(--info-text) !important;
}

[data-testid="stAlert"] p {
  color: var(--info-text) !important;
}

.stAlert[data-baseweb="notification"] {
  box-shadow: none !important;
}

div[data-baseweb="notification"][kind="info"] {
  background: var(--info-bg) !important;
  border: 1px solid var(--brand-300) !important;
  color: var(--info-text) !important;
}

div[data-baseweb="notification"][kind="success"] {
  background: var(--success-bg) !important;
  border: 1px solid var(--brand-200) !important;
  color: var(--success-text) !important;
}

div[data-baseweb="notification"][kind="warning"] {
  background: var(--warning-bg) !important;
  border: 1px solid #E2CDA7 !important;
  color: var(--warning-text) !important;
}

div[data-baseweb="notification"][kind="error"] {
  background: var(--danger-bg) !important;
  border: 1px solid var(--danger-border) !important;
  color: var(--danger-text) !important;
}

.zf-notice {
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 16px;
  line-height: 20px;
  border: 1px solid var(--border);
  font-weight: 700;
}

.zf-notice-success {
  background: var(--success-bg);
  color: var(--success-text);
  border-color: #B0C4DF;
}

.zf-notice-running {
  background: var(--info-bg);
  color: var(--info-text);
  border-color: #B0C4DF;
}

.zf-notice-error {
  background: #FEF2F2;
  color: #991B1B;
  border-color: #FECACA;
}

.zf-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 10px 0;
}

.zf-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
  color: var(--text-2);
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
}

.zf-chip:hover {
  background: var(--brand-50);
  border-color: var(--brand-200);
  color: var(--brand-700);
}

.zf-chip.is-active {
  background: var(--brand-100);
  border-color: var(--brand-300);
  color: var(--brand-800);
}

.stProgress > div > div > div > div {
  background: var(--accent);
}

.zf-upload-grid [data-testid="stHorizontalBlock"] {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  align-items: stretch !important;
}

.zf-upload-grid [data-testid="column"] > div {
  height: 100%;
}

.zf-upload-grid [data-testid="stVerticalBlockBorderWrapper"] {
  min-height: 298px;
  height: 100%;
}

.zf-upload-grid [data-testid="stVerticalBlockBorderWrapper"] > div {
  padding: 18px 18px 16px 18px;
  display: grid;
  grid-template-rows: 72px 48px 1fr;
  align-content: start;
  gap: 8px;
}

.zf-upload-grid [data-testid="column"],
.zf-upload-grid [data-testid="column"] > div,
.zf-upload-grid [data-testid="stVerticalBlock"] {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.zf-upload-card-title {
  min-height: 72px;
  display: flex;
  align-items: flex-start;
  color: var(--text);
  font-size: 18px;
  line-height: 25px;
  font-weight: 700;
}

.zf-upload-card-meta {
  min-height: 48px;
  color: var(--text-2);
  font-size: 15px;
  line-height: 22px;
  font-weight: 700;
  margin-bottom: 0;
}

.zf-upload-grid [data-testid="stVerticalBlockBorderWrapper"] p {
  color: var(--text-2) !important;
}

.zf-upload-grid .stFileUploaderFileData {
  min-height: 28px;
}

.zf-upload-grid [data-testid="stFileUploaderPagination"] {
  display: none !important;
}

.zf-upload-grid [data-testid="stFileUploader"] > div:has([data-testid="stFileUploaderFile"]) {
  display: none !important;
}

.zf-upload-selected {
  margin-top: 10px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface-soft);
  padding: 10px 12px;
}

.zf-upload-selected-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.zf-upload-selected-title {
  color: var(--brand-800);
  font-size: 14px;
  line-height: 18px;
  font-weight: 700;
}

.zf-upload-selected-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--brand-100);
  border: 1px solid var(--brand-200);
  color: var(--brand-800);
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.zf-upload-file-list {
  display: grid;
  gap: 6px;
  max-height: 176px;
  overflow-y: auto;
}

.zf-upload-file-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 7px 8px;
  border-radius: 10px;
  background: var(--surface);
  border: 1px solid rgba(176, 196, 223, 0.7);
}

.zf-upload-file-index {
  color: var(--brand-700);
  font-size: 12px;
  line-height: 16px;
  font-weight: 800;
}

.zf-upload-file-name {
  color: var(--text);
  font-size: 14px;
  line-height: 18px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.zf-upload-file-size {
  color: var(--text-2);
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.zf-upload-selected-empty {
  margin-top: 10px;
  border: 1px dashed var(--border-strong);
  border-radius: 14px;
  background: var(--surface-soft);
  padding: 12px 14px;
  color: var(--text-2);
  font-size: 14px;
  line-height: 18px;
  font-weight: 600;
}

.zf-section-tight h2,
.zf-section-tight h3 {
  margin-top: 4px;
  margin-bottom: 8px;
}

.zf-form-tight [data-testid="stVerticalBlock"] > div {
  gap: 6px;
}

.zf-form-tight label,
.zf-form-tight [data-testid="stWidgetLabel"] p {
  margin-bottom: 6px;
}

.zf-form-tight .stCaption,
.zf-form-tight p {
  line-height: 20px;
}

.zf-main-columns [data-testid="stHorizontalBlock"] {
  align-items: start;
  gap: 18px;
}

.zf-main-columns [data-testid="stColumn"] > div {
  gap: 18px;
}

.zf-run-wrap {
  margin-top: 10px;
}

.zf-top-strip .stButton > button,
.zf-top-strip [data-testid="stFormSubmitButton"] > button {
  min-height: 40px !important;
  height: 40px !important;
}

.zf-top-strip .stNumberInput input {
  min-height: 40px !important;
}

.zf-upload-grid [data-testid="stFileUploaderDropzone"] > span {
  display: flex !important;
  width: 100% !important;
  justify-content: center !important;
}

.zf-run-wrap .stButton > button[kind="primary"] {
  font-size: 16px !important;
  font-weight: 700 !important;
  color: #FFFFFF !important;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

[data-testid="stCodeBlock"] {
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

[data-testid="stCodeBlock"] pre,
[data-testid="stCodeBlock"] code {
  background: var(--surface) !important;
  color: var(--text) !important;
}

a {
  color: var(--brand-700) !important;
  text-decoration: none;
}

a:hover {
  color: var(--brand-800) !important;
  text-decoration: underline;
}

.stMultiSelect [data-baseweb="tag"] {
  background: var(--brand-100) !important;
  border: 1px solid var(--brand-300) !important;
  color: var(--brand-800) !important;
}

button[aria-label="停止/中止任务"] {
  background: var(--danger-bg) !important;
  color: var(--danger-text) !important;
  border: 1px solid var(--danger-border) !important;
}

button[aria-label="停止/中止任务"]:hover {
  background: #F8E5E5 !important;
  border-color: #D7A9A9 !important;
}

[data-testid="stTabs"] [role="tab"] {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-soft);
  color: var(--text-2);
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: var(--brand-50);
  border-color: var(--brand-300);
  color: var(--brand-800);
}

input[id*="outline_item_"] {
  background: var(--surface-soft) !important;
  border-color: var(--border-strong) !important;
}

input[id*="outline_item_"]:focus {
  background: var(--brand-50) !important;
  border-color: var(--brand-600) !important;
}

[data-testid="stNotificationContentInfo"],
[data-testid="stNotificationContentSuccess"] {
  background: var(--info-bg) !important;
  color: var(--info-text) !important;
}

div[role="checkbox"][aria-checked="true"],
div[role="radio"][aria-checked="true"] {
  background: var(--china-red) !important;
  border-color: var(--china-red) !important;
}

div[role="checkbox"][aria-checked="false"],
div[role="radio"][aria-checked="false"] {
  background: var(--surface) !important;
  border-color: var(--border-strong) !important;
  color: transparent !important;
}

div[role="checkbox"][aria-checked="true"] svg,
div[role="radio"][aria-checked="true"] svg {
  fill: #FFFFFF !important;
  stroke: #FFFFFF !important;
}

@media (max-width: 1200px) {
  div.block-container {
    padding-left: 16px;
    padding-right: 16px;
    padding-top: 4px;
    padding-bottom: 16px;
  }
  .zf-upload-grid [data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 288px;
  }
}

@media (max-width: 980px) {
  .zf-runtime-summary {
    grid-template-columns: minmax(0, 1fr);
  }
  .zf-library-summary {
    grid-template-columns: minmax(0, 1fr);
  }
  .zf-top-strip .zf-notice {
    margin-bottom: 6px;
  }
  .zf-page-title {
    font-size: 30px;
    line-height: 36px;
  }
  .zf-upload-grid [data-testid="stHorizontalBlock"] {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _inject_ui_dom_patch() -> None:
    components.html(
        """
<script>
(function () {
  let scheduled = false;
  const apply = () => {
    scheduled = false;
    const doc = window.parent.document;
    if (doc && doc.title !== '文档生成系统') {
      doc.title = '文档生成系统';
    }
    const zones = doc.querySelectorAll('[data-testid="stFileUploaderDropzone"]');
    zones.forEach((zone) => {
      const instructions = zone.querySelector('[data-testid="stFileUploaderDropzoneInstructions"]');
      if (instructions) {
        instructions.innerHTML = '';
        instructions.setAttribute('aria-hidden', 'true');
        instructions.style.display = 'none';
        instructions.style.visibility = 'hidden';
        instructions.style.opacity = '0';
        instructions.style.maxHeight = '0';
        instructions.style.width = '0';
        instructions.style.fontSize = '0';
        instructions.style.lineHeight = '0';
        instructions.style.overflow = 'hidden';
      }

      let helper = zone.querySelector('.zf-upload-helper-inner');
      if (!helper) {
        helper = doc.createElement('div');
        helper.className = 'zf-upload-helper-inner';
        zone.insertBefore(helper, zone.firstChild);
      }
      helper.innerHTML = '';

      const title = doc.createElement('div');
      title.className = 'zf-upload-helper-title';
      title.textContent = '拖拽文件到此处';

      const sub = doc.createElement('div');
      sub.className = 'zf-upload-helper-sub';
      sub.textContent = '或点击下方按钮选择文件';

      helper.appendChild(title);
      helper.appendChild(sub);

      const button = zone.querySelector('button');
      if (button) {
        button.textContent = '选择文件';
        button.setAttribute('aria-label', '选择文件');
        button.title = '选择文件';
        button.dataset.zfLocalized = '1';
        button.style.color = '#233751';
        button.style.fontWeight = '700';
        button.style.background = '#E1E6ED';
        button.style.border = '1px solid #B2BECC';
        button.style.minHeight = '44px';
      }

      const uploader = zone.closest('[data-testid="stFileUploader"]');
      if (uploader) {
        uploader.querySelectorAll('[data-testid="stFileUploaderPagination"]').forEach((node) => {
          node.style.display = 'none';
        });
        const fileList = uploader.querySelector('ul');
        if (fileList && fileList.querySelector('[data-testid="stFileUploaderFile"]')) {
          let shell = fileList.parentElement;
          while (shell && shell.parentElement && shell.parentElement !== uploader) {
            shell = shell.parentElement;
          }
          if (shell && shell !== uploader) {
            shell.style.display = 'none';
          }
        }
      }
    });

    const checkboxLabels = doc.querySelectorAll('label[data-baseweb="checkbox"], label[data-baseweb="radio"]');
    checkboxLabels.forEach((label) => {
      const box = label.querySelector('span:first-child');
      const input = label.querySelector('input');
      if (!box || !input) return;
      const checked = input.getAttribute('aria-checked') === 'true' || input.checked;
      box.style.width = '20px';
      box.style.minWidth = '20px';
      box.style.height = '20px';
      box.style.minHeight = '20px';
      box.style.borderRadius = '6px';
      box.style.display = 'inline-flex';
      box.style.alignItems = 'center';
      box.style.justifyContent = 'center';
      box.style.boxShadow = 'none';
      box.style.border = checked ? '1px solid #DE2910' : '1px solid #99ABBF';
      box.style.background = checked ? '#DE2910' : '#E1E6ED';
      box.style.color = checked ? '#FFFFFF' : 'transparent';
      if (checked) {
        box.textContent = '✓';
      } else {
        box.textContent = '';
      }
    });

    const chatWrap = doc.querySelector('[data-testid="stChatInput"]');
    if (chatWrap) {
      chatWrap.style.background = 'transparent';
      const wrapBlocks = chatWrap.querySelectorAll('div');
      wrapBlocks.forEach((node) => {
        if (node.querySelector('[data-testid="stChatInputTextArea"]')) {
          node.style.background = '#E8EDF3';
          node.style.borderColor = '#B2BECC';
          node.style.boxShadow = 'none';
        }
      });

      const baseInput = chatWrap.querySelector('[data-baseweb="base-input"]');
      if (baseInput) {
        baseInput.style.background = '#E8EDF3';
        baseInput.style.border = '1px solid #B2BECC';
        baseInput.style.boxShadow = 'none';
      }

      const textAreaShell = chatWrap.querySelector('[data-baseweb="textarea"]');
      if (textAreaShell) {
        textAreaShell.style.background = '#E8EDF3';
        textAreaShell.style.border = '1px solid #B2BECC';
        textAreaShell.style.boxShadow = 'none';
      }

      const textArea = chatWrap.querySelector('[data-testid="stChatInputTextArea"]');
      if (textArea) {
        textArea.style.background = '#E1E6ED';
        textArea.style.color = '#233751';
        textArea.style.border = '1px solid #B2BECC';
        textArea.style.boxShadow = 'none';
      }

      const submit = chatWrap.querySelector('[data-testid="stChatInputSubmitButton"]');
      if (submit) {
        submit.style.background = '#D3DBE5';
        submit.style.border = '1px solid #B2BECC';
        submit.style.boxShadow = 'none';
        submit.style.color = '#113285';
      }
    }
  };

  apply();
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(apply);
  });
  observer.observe(window.parent.document.body, { childList: true, subtree: true });
})();
</script>
        """,
        height=0,
        width=0,
    )


def _init_state() -> None:
    if not str(st.session_state.get("session_id") or "").strip():
        st.session_state["session_id"] = uuid4().hex
    workspace_dir = resolve_workspace_dir(session_id=str(st.session_state.get("session_id") or "").strip())
    st.session_state["workspace_dir"] = str(workspace_dir)
    maybe_cleanup_expired_workspaces(exclude_workspace=workspace_dir)

    env_main_provider = PRIMARY_TEXT_PROVIDER
    env_main_model = PRIMARY_TEXT_MODEL
    env_main_key = ""

    env_f1_provider = SECONDARY_TEXT_PROVIDER
    env_f1_model = SECONDARY_TEXT_MODEL
    env_f1_key = ""
    env_f1_enabled = False

    env_f2_provider = ""
    env_f2_model = ""
    env_f2_key = ""
    env_f2_enabled = False

    defaults = {
        "topic_text": "施工组织设计方案",
        "project_id_text": "",
        "project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "variants_value": 1,
        "selected_templates": ["A"],
        "global_instruction": "严格遵守最新16条行业规定；所有工序采用A/B/C/D/E结构表达。",
        "requirements_text": "严格按技术文件详细评审标准中的章目录组织内容，不新增顶层章节\n每节输出量化指标与风险-控制-验证闭环\n全文禁止官话、套话、空话",
        "outline_items": [],
        "outline_pages": [],
        "generation_mode": "standard_auto",
        "total_pages_target": 0,
        "cover_page_count": FIXED_COVER_PAGES,
        "full_index_enabled": False,
        "full_index_page_count": DEFAULT_FULL_INDEX_PAGES,
        "toc_page_count": 2,
        "front_matter_page_mode": "include",
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": "template",
        "agent_parallelism": 6,
        "variant_parallelism": 1,
        "generate_images": True,
        "image_provider": "google",
        "image_model": "banana",
        "provider_text": env_main_provider,
        "model_text": env_main_model,
        "api_key_text": env_main_key,
        "fallback_1_enabled": env_f1_enabled,
        "fallback_1_provider": env_f1_provider,
        "fallback_1_model": env_f1_model,
        "fallback_1_api_key": env_f1_key,
        "fallback_2_enabled": env_f2_enabled,
        "fallback_2_provider": env_f2_provider,
        "fallback_2_model": env_f2_model,
        "fallback_2_api_key": env_f2_key,
        "chapter_requirements_text": "",
        "params_override_text": "",
        "template_key": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "sample_library_project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "sample_library_page_bucket": TEMPLATE_PAGE_BUCKETS[0] if TEMPLATE_PAGE_BUCKETS else "",
        "sample_library_note": "",
        "template_library_flash": "",
        "recent_job_flash": "",
        "review_focus_job_id": "",
        "review_focus_variant": 1,
        "latest_admission": None,
        "kg_search_query": "",
        "kg_search_top_k": 5,
        "kg_search_last_response": None,
        "kg_search_last_error": "",
        "kg_trace_sample": None,
        "constraint_chat_input": "",
        "strict_tender_outline": True,
        "body_font": "宋体",
        "title_font": "宋体",
        "body_size": 14,
        "title_size": 16,
        "line_spacing_pt": 22.0,
        "margin_top_cm": 2.5,
        "margin_right_cm": 2.0,
        "margin_bottom_cm": 2.0,
        "margin_left_cm": 2.0,
        "enforce_chapter_pages": False,
        "chapter_start_new_page": False,
        "chart_enabled": True,
        "chart_mode": "page_density_auto",
        "chart_every_n": 2,
        "chart_position": "chapter",
        "auto_refresh": False,
        "maintenance_panel_visible": False,
        "submission_flow": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    if PROJECT_TYPES and st.session_state.get("project_type") not in PROJECT_TYPES:
        st.session_state["project_type"] = PROJECT_TYPES[0]
    if PROJECT_TYPES and st.session_state.get("sample_library_project_type") not in PROJECT_TYPES:
        st.session_state["sample_library_project_type"] = str(st.session_state.get("project_type") or PROJECT_TYPES[0])
    if TEMPLATE_PAGE_BUCKETS and st.session_state.get("sample_library_page_bucket") not in TEMPLATE_PAGE_BUCKETS:
        st.session_state["sample_library_page_bucket"] = TEMPLATE_PAGE_BUCKETS[0]
    normalized_front_matter_mode = _normalize_front_matter_page_mode(st.session_state.get("front_matter_page_mode"))
    if st.session_state.get("front_matter_page_mode") != normalized_front_matter_mode:
        st.session_state["front_matter_page_mode"] = normalized_front_matter_mode
    current_toc_pages = _page_target(st.session_state.get("toc_page_count"))
    if current_toc_pages is None:
        st.session_state["toc_page_count"] = 2
    current_cover_pages = _page_target(st.session_state.get("cover_page_count"))
    if current_cover_pages is None:
        st.session_state["cover_page_count"] = FIXED_COVER_PAGES
    st.session_state["full_index_enabled"] = _normalize_full_index_enabled(st.session_state.get("full_index_enabled"))
    current_index_pages = _page_target(st.session_state.get("full_index_page_count"))
    if current_index_pages is None:
        st.session_state["full_index_page_count"] = DEFAULT_FULL_INDEX_PAGES
    st.session_state.setdefault("global_instruction_draft", str(st.session_state.get("global_instruction") or ""))
    st.session_state.setdefault("requirements_text_draft", str(st.session_state.get("requirements_text") or ""))
    normalized_generation_mode = _normalize_generation_mode(st.session_state.get("generation_mode"))
    if st.session_state.get("generation_mode") != normalized_generation_mode:
        st.session_state["generation_mode"] = normalized_generation_mode
    if (st.session_state.get("active_job") or st.session_state.get("run_result")) and st.session_state.get("submission_flow"):
        _clear_submission_flow()
    if st.session_state.get("provider_text") not in TEXT_PROVIDER_OPTIONS:
        st.session_state["provider_text"] = "openai"
    if st.session_state.get("fallback_1_provider") not in FALLBACK_PROVIDER_OPTIONS:
        st.session_state["fallback_1_provider"] = ""
    if st.session_state.get("fallback_2_provider") not in FALLBACK_PROVIDER_OPTIONS:
        st.session_state["fallback_2_provider"] = ""
    st.session_state["provider_text"], st.session_state["model_text"] = _normalize_provider_model_pair(
        st.session_state.get("provider_text"),
        st.session_state.get("model_text"),
        fallback="openai",
    )
    st.session_state["fallback_1_provider"], st.session_state["fallback_1_model"] = _normalize_provider_model_pair(
        st.session_state.get("fallback_1_provider"),
        st.session_state.get("fallback_1_model"),
        fallback="",
    )
    st.session_state["fallback_2_provider"], st.session_state["fallback_2_model"] = _normalize_provider_model_pair(
        st.session_state.get("fallback_2_provider"),
        st.session_state.get("fallback_2_model"),
        fallback="",
    )
    selected_templates = _normalize_template_selection(st.session_state.get("selected_templates"))
    st.session_state["selected_templates"] = selected_templates or ["A"]
    st.session_state["variants_value"] = len(st.session_state["selected_templates"])
    # 备选链默认保持空白，用户显式启用后再手工选择。
    if st.session_state.get("body_font") not in {"宋体", "仿宋体"}:
        st.session_state["body_font"] = "宋体"
    if st.session_state.get("title_font") not in {"宋体", "仿宋体"}:
        st.session_state["title_font"] = "宋体"
    valid_templates = list(TEMPLATE_LIBRARY.keys())
    if valid_templates and st.session_state.get("template_key") not in valid_templates:
        st.session_state["template_key"] = valid_templates[0]

    # UI 默认值迁移：将高级参数中的勾选项改为默认不勾选（仅迁移一次）。
    defaults_rev = "2026-03-12-main-chatgpt54-gemini31pro-mainflow"
    if st.session_state.get("_ui_defaults_rev") != defaults_rev:
        try:
            current_agent_parallelism = int(st.session_state.get("agent_parallelism") or 0)
        except Exception:
            current_agent_parallelism = 0
        st.session_state["quality_strict"] = True
        st.session_state["auto_remediate"] = True
        st.session_state["generate_images"] = True
        st.session_state["agent_parallelism"] = max(6, current_agent_parallelism or 6)
        st.session_state["provider_text"] = PRIMARY_TEXT_PROVIDER
        st.session_state["model_text"] = PRIMARY_TEXT_MODEL
        st.session_state["api_key_text"] = ""
        st.session_state["fallback_1_provider"] = SECONDARY_TEXT_PROVIDER
        st.session_state["fallback_1_model"] = SECONDARY_TEXT_MODEL
        st.session_state["fallback_1_api_key"] = ""
        st.session_state["fallback_1_enabled"] = False
        st.session_state["fallback_2_enabled"] = False
        st.session_state["fallback_2_provider"] = ""
        st.session_state["fallback_2_model"] = ""
        st.session_state["fallback_2_api_key"] = ""
        st.session_state["_ui_defaults_rev"] = defaults_rev

    st.session_state.setdefault("run_logs", [])
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault(
        "constraint_chat_history",
        [
            {
                "role": "assistant",
                "content": "约束对话已就绪。可直接输入修改需求，例如：全局：...、新增：...、删除：关键词、清空要求。",
            }
        ],
    )


def _requirements_lines_from_text(text: str) -> list[str]:
    lines: list[str] = []
    seen = set()
    for raw in str(text or "").splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def _update_constraints_from_chat(user_text: str) -> str:
    msg = str(user_text or "").strip()
    if not msg:
        return "未检测到可执行内容。"

    draft_global = str(st.session_state.get("global_instruction_draft") or "").strip()
    req_lines = _requirements_lines_from_text(st.session_state.get("requirements_text_draft") or "")
    compact = msg.replace("\n", " ").strip()

    if compact.startswith(("全局：", "全局:", "指令：", "指令:")):
        value = compact.split("：", 1)[1] if "：" in compact else compact.split(":", 1)[1]
        draft_global = value.strip()
        st.session_state["global_instruction_draft"] = draft_global
        st.session_state["global_instruction"] = draft_global
        return "已更新全局指令。"

    if compact.startswith(("新增：", "新增:", "增加：", "增加:")):
        value = compact.split("：", 1)[1] if "：" in compact else compact.split(":", 1)[1]
        line = value.strip()
        if line and line not in req_lines:
            req_lines.append(line)
        st.session_state["requirements_text_draft"] = "\n".join(req_lines)
        st.session_state["requirements_text"] = st.session_state["requirements_text_draft"]
        return "已新增1条编制要求。"

    if compact.startswith(("删除：", "删除:", "移除：", "移除:")):
        value = compact.split("：", 1)[1] if "：" in compact else compact.split(":", 1)[1]
        kw = value.strip()
        if not kw:
            return "删除失败：未提供关键词。"
        kept = [x for x in req_lines if kw not in x]
        removed = len(req_lines) - len(kept)
        req_lines = kept
        st.session_state["requirements_text_draft"] = "\n".join(req_lines)
        st.session_state["requirements_text"] = st.session_state["requirements_text_draft"]
        if removed <= 0:
            return f"未匹配到包含“{kw}”的要求。"
        return f"已删除{removed}条包含“{kw}”的编制要求。"

    if compact in {"清空要求", "清空编制要求", "清空要求列表"}:
        st.session_state["requirements_text_draft"] = ""
        st.session_state["requirements_text"] = ""
        return "已清空编制要求。"

    # 默认将输入视为“新增编制要求”。
    if compact not in req_lines:
        req_lines.append(compact)
    st.session_state["requirements_text_draft"] = "\n".join(req_lines)
    st.session_state["requirements_text"] = st.session_state["requirements_text_draft"]
    return "已按新增编制要求处理。"


def _set_outline_items(items: list[str]) -> None:
    clean_items = [str(x).strip() for x in items if str(x).strip()]
    page_map = st.session_state.get("chapter_page_map") if isinstance(st.session_state.get("chapter_page_map"), dict) else {}
    page_map = page_map or {}
    clean_pages = [int(page_map.get(t) or 2) for t in clean_items]
    st.session_state["outline_items"] = clean_items
    st.session_state["outline_pages"] = clean_pages
    st.session_state["chapter_page_map"] = {t: int(p) for t, p in zip(clean_items, clean_pages)}


def _clear_outline_widget_state() -> None:
    for k in list(st.session_state.keys()):
        ks = str(k)
        if ks.startswith("outline_item_") or ks.startswith("outline_page_"):
            st.session_state.pop(k, None)


def _current_outline() -> list[str]:
    return [str(x).strip() for x in (st.session_state.get("outline_items") or []) if str(x).strip()]


def _apply_template(template_key: str) -> None:
    if not TEMPLATE_LIBRARY:
        return
    tpl = TEMPLATE_LIBRARY.get(template_key)
    if not isinstance(tpl, dict):
        return
    st.session_state["requirements_text"] = "\n".join([str(x) for x in (tpl.get("requirements") or []) if str(x).strip()])
    st.session_state["requirements_text_draft"] = str(st.session_state.get("requirements_text") or "")
    tpl_outline = [str(x).strip() for x in (tpl.get("outline") or []) if str(x).strip()]
    if tpl_outline:
        _set_outline_items(tpl_outline)
    st.session_state["chapter_requirements_text"] = _json_pretty(tpl.get("chapter_requirements") or {})
    st.session_state["params_override_text"] = _json_pretty(tpl.get("params_override") or {})
    tpt = str(tpl.get("project_type") or template_key).strip()
    if tpt and tpt in PROJECT_TYPES:
        st.session_state["project_type"] = tpt


def _render_outline_editor(show_title: bool = True) -> list[str]:
    if show_title:
        st.markdown("#### 目录编辑器（默认按评审标准章目录，可实时改标题和顺序）")
    items = list(st.session_state.get("outline_items") or [])
    pages = list(st.session_state.get("outline_pages") or [])
    if len(pages) < len(items):
        pages += [2] * (len(items) - len(pages))
    elif len(pages) > len(items):
        pages = pages[: len(items)]

    if not items:
        st.info("目录为空。可先点击“从评审标准载入目录”，或手动新增章节。")

    front_cover_pages = max(1, int(_page_target(st.session_state.get("cover_page_count")) or FIXED_COVER_PAGES))
    front_index_pages = max(1, int(_page_target(st.session_state.get("full_index_page_count")) or DEFAULT_FULL_INDEX_PAGES))
    front_index_enabled = _normalize_full_index_enabled(st.session_state.get("full_index_enabled"))
    front_toc_pages = max(1, int(_page_target(st.session_state.get("toc_page_count")) or 2))
    front_mode = _normalize_front_matter_page_mode(st.session_state.get("front_matter_page_mode"))
    front_total_seed = int(st.session_state.get("total_pages_target") or sum(int(x or 0) for x in pages) or 50)
    front_preview = _build_front_matter_plan(
        front_total_seed,
        cover_page_count=front_cover_pages,
        full_index_page_count=front_index_pages,
        full_index_enabled=front_index_enabled,
        toc_page_count=front_toc_pages,
        front_matter_page_mode=front_mode,
    )

    st.markdown("**前置页**")
    front_rows = [
        {"label": "封面", "state_key": "cover_page_count", "row_value": front_cover_pages, "hint": "项目封面页数"},
        {"label": "索引", "state_key": "full_index_page_count", "row_value": front_index_pages, "hint": "", "toggle": True},
        {"label": "目录", "state_key": "toc_page_count", "row_value": front_toc_pages, "hint": "目录预留页数"},
    ]
    for row in front_rows:
        row_label = str(row["label"])
        state_key = str(row["state_key"])
        row_value = int(row["row_value"])
        c1, c2 = st.columns([9, 5])
        c1.text_input(f"{row_label}标题", value=row_label, disabled=True, label_visibility="collapsed")
        if bool(row.get("toggle")):
            n1, n2 = c2.columns([2.0, 1.4], vertical_alignment="center")
        else:
            n1, n2 = c2.columns([2.3, 2.7], vertical_alignment="center")
        n1.number_input(
            f"{row_label}页数",
            min_value=1,
            max_value=20,
            key=state_key,
            label_visibility="collapsed",
        )
        if bool(row.get("toggle")):
            n2.checkbox("启用", key="full_index_enabled")
        else:
            n2.caption(str(row.get("hint") or ""))

    st.selectbox(
        "封面、目录是否计入总页数",
        options=FRONT_MATTER_PAGE_MODE_OPTIONS,
        key="front_matter_page_mode",
        format_func=lambda x: FRONT_MATTER_PAGE_MODE_LABELS.get(x, str(x)),
    )
    scope_label = "计入总页数" if front_preview["count_mode"] == "include" else "不计入总页数"
    if int(front_preview["full_index_pages"] or 0) > 0:
        st.caption(
            f"当前前置顺序：封面{front_preview['cover_pages']}页 -> 索引{front_preview['full_index_pages']}页 -> 目录{front_preview['toc_pages']}页 -> 正文。"
            f"当前口径={scope_label}；正文约 {front_preview['chapter_page_budget']} 页，成品约 {front_preview['effective_document_pages']} 页。"
        )
    else:
        st.caption(
            f"当前前置顺序：封面{front_preview['cover_pages']}页 -> 目录{front_preview['toc_pages']}页 -> 正文。"
            f"索引当前未启用；若启用则预留 {front_index_pages} 页。当前口径={scope_label}。"
        )

    st.markdown("**正文章节**")
    action = None
    for i, val in enumerate(items):
        c1, c2 = st.columns([9, 5])
        new_val = c1.text_input(f"第{i + 1}章", value=val, key=f"outline_item_{i}")
        items[i] = new_val.strip()
        p1, p2, p3, p4 = c2.columns([2, 1, 1, 1])
        page_value = p1.number_input(
            "页数",
            min_value=1,
            max_value=500,
            value=int(pages[i] or 2),
            key=f"outline_page_{i}",
            label_visibility="collapsed",
        )
        pages[i] = int(page_value)
        if p2.button("↑", key=f"outline_up_{i}", type="secondary"):
            action = ("up", i)
        if p3.button("↓", key=f"outline_down_{i}", type="secondary"):
            action = ("down", i)
        if p4.button("✕", key=f"outline_del_{i}", type="secondary"):
            action = ("del", i)

    c_add, c_clear = st.columns([1, 1])
    if c_add.button("新增章节", width="stretch", type="secondary"):
        items.append("")
        pages.append(2)
        st.session_state["outline_items"] = items
        st.session_state["outline_pages"] = pages
        _clear_outline_widget_state()
        st.rerun()
    if c_clear.button("清空目录", width="stretch", type="secondary"):
        st.session_state["outline_items"] = []
        st.session_state["outline_pages"] = []
        st.session_state["chapter_page_map"] = {}
        _clear_outline_widget_state()
        st.rerun()

    if action:
        typ, idx = action
        if typ == "up" and idx > 0:
            items[idx - 1], items[idx] = items[idx], items[idx - 1]
            pages[idx - 1], pages[idx] = pages[idx], pages[idx - 1]
        elif typ == "down" and idx < len(items) - 1:
            items[idx + 1], items[idx] = items[idx], items[idx + 1]
            pages[idx + 1], pages[idx] = pages[idx], pages[idx + 1]
        elif typ == "del" and 0 <= idx < len(items):
            items.pop(idx)
            pages.pop(idx)
        st.session_state["outline_items"] = items
        st.session_state["outline_pages"] = pages
        _clear_outline_widget_state()
        st.rerun()

    st.session_state["outline_items"] = items
    st.session_state["outline_pages"] = pages
    chapter_page_map: dict[str, int] = {}
    for idx, title in enumerate(items):
        tt = str(title or "").strip()
        if not tt:
            continue
        chapter_page_map[tt] = int(pages[idx] or 2)
    st.session_state["chapter_page_map"] = chapter_page_map
    return [x for x in items if x]


def _outline_to_chapter_pages(outline: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    m = st.session_state.get("chapter_page_map") or {}
    for title in outline:
        out[title] = int(m.get(title) or 2)
    st.session_state["chapter_page_map"] = out
    return out


def _render_constraint_chips() -> None:
    global_instruction = str(st.session_state.get("global_instruction_draft") or "").strip()
    req_lines = _requirements_lines_from_text(str(st.session_state.get("requirements_text_draft") or ""))
    chips = []
    if global_instruction:
        chips.append("全局指令")
    chips.append(f"编制要求 {len(req_lines)} 条")
    if req_lines:
        chips.extend(req_lines[:4])
    chip_html = "".join(
        f"<span class='zf-chip'>{html.escape(str(chip))}</span>" for chip in chips
    )
    st.markdown(f"<div class='zf-chip-row'>{chip_html}</div>", unsafe_allow_html=True)


def _render_downloads() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return

    st.subheader("结果预览与下载")
    st.markdown(
        "<div class='zf-notice zf-notice-running'>结果区已加载：可下载DOCX/XLSX并进行问题清单回写。</div>",
        unsafe_allow_html=True,
    )
    job_id = result.get("job_id", "")
    variants = int(result.get("variants") or 1)
    st.write(f"job_id: `{job_id}`")
    generation_mode_summary = result.get("generation_mode_summary") if isinstance(result.get("generation_mode_summary"), dict) else {}
    if generation_mode_summary:
        profile = str(generation_mode_summary.get("profile") or "").strip()
        mode_effective = str(generation_mode_summary.get("mode_effective") or "").strip()
        deterministic_template = str(generation_mode_summary.get("deterministic_logic_template_id") or "").strip()
        st.caption(
            f"生成档位={GENERATION_MODE_LABELS.get(profile, profile or '-')}；"
            f"执行策略={GENERATION_ENGINE_LABELS.get(mode_effective, mode_effective or '-')}；"
            f"稳定交付={'是' if generation_mode_summary.get('stable_output') else '否'}；"
            f"固定模板={deterministic_template or '-'}"
        )
    result_project_type = str(result.get("project_type") or st.session_state.get("project_type") or "").strip()
    result_topic = str(result.get("topic") or st.session_state.get("topic_text") or "施工组织设计方案").strip()
    result_project_id = _safe_project_id(st.session_state.get("project_id_text") or result_topic)

    delivery_sample_path = Path("build/交付级净化样稿.docx")
    if delivery_sample_path.exists() and delivery_sample_path.is_file():
        try:
            st.caption("纯净交付级样稿")
            st.download_button(
                label="下载纯净交付级样稿.docx",
                data=delivery_sample_path.read_bytes(),
                file_name=delivery_sample_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_delivery_sample_docx",
                width="stretch",
            )
        except Exception as exc:
            st.caption(f"纯净交付级样稿暂不可下载：{exc}")

    tabs = st.tabs([f"方案 v{i}" for i in range(1, variants + 1)])
    for i, tab in enumerate(tabs, start=1):
        with tab:
            files = result.get("artifacts", {}).get(i, {})
            if files.get("docx"):
                st.download_button(
                    label=f"下载施工组织设计 v{i}.docx",
                    data=files["docx"],
                    file_name=f"autoplan_{job_id}_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_docx_{i}",
                    width="stretch",
                )
            if files.get("compare_docx"):
                st.download_button(
                    label=f"下载对照稿 v{i}.docx",
                    data=files["compare_docx"],
                    file_name=f"autoplan_{job_id}_compare_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_cmp_{i}",
                    width="stretch",
                )
            if files.get("focus_xlsx"):
                st.download_button(
                    label=f"下载问题清单+自动修订建议 v{i}.xlsx",
                    data=files["focus_xlsx"],
                    file_name=f"autoplan_{job_id}_focus_v{i}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{i}",
                    width="stretch",
                )
            if files.get("score_overview_xlsx"):
                st.download_button(
                    label=f"下载评分点覆盖与证据引用总览 v{i}.xlsx",
                    data=files["score_overview_xlsx"],
                    file_name=f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{i}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_score_overview_{i}",
                    width="stretch",
                )
            if files.get("expert_review_docx"):
                st.download_button(
                    label=f"下载专家复核提要版 v{i}.docx",
                    data=files["expert_review_docx"],
                    file_name=f"autoplan_{job_id}_专家复核提要版_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_expert_review_{i}",
                    width="stretch",
                )
            q = (result.get("quality_by_variant") or {}).get(i) or {}
            if q:
                st.caption(
                    f"模板={str(q.get('logic_template_name') or q.get('logic_template_id') or '-').strip() or '-'}；"
                    f"质量分={q.get('quality_score') if q.get('quality_score') is not None else '-'}；"
                    f"质量闸门={'通过' if q.get('quality_gate_ok') else '未通过'}；"
                    f"未通过项={q.get('quality_gate_failed_count') if q.get('quality_gate_failed_count') is not None else '-'}"
                )
            if q:
                st.json(q)
            runtime = (result.get("runtime_by_variant") or {}).get(i) or {}
            if runtime:
                mode = str(runtime.get("generation_mode") or "").strip() or "standard_auto"
                mode_effective = str(runtime.get("mode_effective") or "").strip()
                planned = runtime.get("planned_total_pages")
                contract_ok = runtime.get("agent_contract_ok")
                risk_cnt = runtime.get("score_high_risk_count")
                st.caption(
                    f"运行档位={GENERATION_MODE_LABELS.get(mode, mode)}；"
                    f"执行策略={GENERATION_ENGINE_LABELS.get(mode_effective, mode_effective or '-')}；"
                    f"规划页数={planned if planned is not None else '-'}；"
                    f"Agent合同校验={'通过' if contract_ok else '未通过'}；评分高风险项={risk_cnt if risk_cnt is not None else '-'}"
                )
                stages = runtime.get("pipeline_stages") if isinstance(runtime.get("pipeline_stages"), list) else []
                if stages:
                    st.dataframe(stages, width="stretch", hide_index=True)
            if files.get("docx"):
                st.caption("本稿质量满意时，可直接回流到样板库，作为后续同类型章节的学习样板。")
                feedback_note_key = f"feedback_sample_note_{job_id}_v{i}"
                note_value = st.text_input(
                    "回流说明（可选）",
                    key=feedback_note_key,
                    placeholder="例如：医院局部改造，施工部署和安全文明章节成熟，可作为回流样板。",
                )
                feedback_scene_key = f"feedback_sample_scene_{job_id}_v{i}"
                scene_value = st.text_input(
                    "回流子场景（可选）",
                    key=feedback_scene_key,
                    placeholder="例如：医院, 局部改造, 地库",
                )
                suggested_scene_tags = _infer_result_scene_tags(
                    result_project_type,
                    result_topic,
                    note_value,
                    scene_value,
                    f"{result_project_type} {result_topic}",
                )
                if suggested_scene_tags:
                    st.caption("系统建议子场景：" + " / ".join(suggested_scene_tags[:4]))
                if st.button(
                    f"满意并沉淀为样板库 v{i}",
                    key=f"promote_template_{job_id}_v{i}",
                    type="secondary",
                    width="stretch",
                ):
                    try:
                        if result_project_type not in PROJECT_TYPES:
                            raise ValueError("当前结果缺少有效项目类型，无法沉淀为样板")
                        planned_pages = (runtime or {}).get("planned_total_pages")
                        fallback_pages = st.session_state.get("total_pages_target")
                        target_bucket = _infer_template_page_bucket_from_pages(planned_pages or fallback_pages)
                        note_raw = str(st.session_state.get(feedback_note_key) or "").strip()
                        note_parts = ["系统成品满意回流", "已通过人工确认可作为参考样板"]
                        if note_raw:
                            note_parts.append(note_raw)
                        note = "；".join([x for x in note_parts if str(x).strip()])
                        manual_scene_tags = _normalize_scene_tags_ui(st.session_state.get(feedback_scene_key) or "")
                        scene_tags = _normalize_scene_tags_ui(
                            manual_scene_tags
                            + _infer_result_scene_tags(
                                result_project_type,
                                result_topic,
                                note,
                                " ".join(manual_scene_tags),
                                f"{result_project_type} {result_topic}",
                            )
                        )
                        upload_name = f"autoplan_{job_id}_满意回流_v{i}.docx"
                        saved = _ingest_docs(
                            base_url,
                            [_MemoryUpload(upload_name, files["docx"])],
                            result_project_id,
                            source_hint="template_library",
                            extra_params={
                                "project_type": result_project_type,
                                "library_scope": "template_library",
                                "library_note": note,
                                "template_page_bucket": target_bucket,
                                "template_scene_tags": ",".join(scene_tags),
                                "template_feedback_score": 95,
                                "template_feedback_origin": "generated_accepted",
                                "source_job_id": job_id,
                                "source_variant": i,
                            },
                        )
                        saved_count = len(saved.get("saved") or [])
                        _queue_widget_update(feedback_note_key, "")
                        _queue_widget_update(feedback_scene_key, "")
                        flash_parts = [
                            result_project_type,
                            _template_page_bucket_label(target_bucket),
                            f"{saved_count} 个文件",
                        ]
                        if scene_tags:
                            flash_parts.append(" / ".join(scene_tags[:4]))
                        st.session_state["template_library_flash"] = (
                            "已回流满意成品到样板库：" + " / ".join(flash_parts) + "。"
                        )
                        st.success("当前成品已加入样板库，后续生成会优先参考。")
                    except Exception as e:
                        st.error(f"样板回流失败: {e}")
    _render_result_aux_summary()
    with st.expander("辅助留痕详情", expanded=False):
        _render_automation_summary()
        _render_runtime_parallelism_summary()
        _render_stage_trace_summary()


def _cancel_active_job(base_url: str, actions_key: str) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        st.warning("当前没有可中止任务")
        return
    _post_json(base_url, "/actions/job_cancel", actions_key, {"job_id": job_id}, timeout=60)
    _append_log(f"任务已请求中止: {job_id}")
    st.session_state["active_job"] = None


def _coerce_variant_position(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    text = str(raw or "").strip().lower()
    if text.startswith("v") and text[1:].isdigit():
        text = text[1:]
    try:
        value = int(text)
    except Exception:
        return None
    return value if value > 0 else None


def _normalize_variant_dict_map(raw: Any) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        idx = (
            _coerce_variant_position(value.get("variant_index"))
            or _coerce_variant_position(key)
            or _coerce_variant_position(value.get("variant_id"))
        )
        if idx is None:
            continue
        out[idx] = dict(value)
    return out


def _recent_job_mode_quality_caption(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    generation_mode_summary = item.get("generation_mode_summary") if isinstance(item.get("generation_mode_summary"), dict) else {}
    parts: list[str] = []
    profile = str(generation_mode_summary.get("profile") or item.get("generation_mode") or "").strip()
    mode_effective = str(generation_mode_summary.get("mode_effective") or item.get("mode_effective") or "").strip()
    if profile:
        parts.append(f"档位={GENERATION_MODE_LABELS.get(profile, profile)}")
    if mode_effective:
        parts.append(f"执行={GENERATION_ENGINE_LABELS.get(mode_effective, mode_effective)}")
    if generation_mode_summary.get("stable_output"):
        parts.append("稳定交付")
    template_name = str(item.get("logic_template_name") or item.get("logic_template_id") or "").strip()
    if template_name:
        parts.append(f"模板={template_name}")
    quality_score = item.get("quality_score")
    if quality_score is not None:
        parts.append(f"质量分={quality_score}")
    if item.get("quality_gate_ok") is not None:
        parts.append(f"质量闸门={'通过' if bool(item.get('quality_gate_ok')) else '未通过'}")
    failed_count = item.get("quality_gate_failed_count")
    if failed_count is not None:
        parts.append(f"未通过项={failed_count}")
    return "；".join(parts)


def _recent_job_quality_signal(item: dict[str, Any]) -> dict[str, str]:
    if not isinstance(item, dict):
        return {}
    gate_ok = item.get("quality_gate_ok")
    if gate_ok is None:
        return {}
    quality_score = item.get("quality_score")
    failed_count = item.get("quality_gate_failed_count")
    if bool(gate_ok):
        message = "质量提示：当前成品质量闸门已通过"
        if quality_score is not None:
            message += f"，质量分={quality_score}"
        return {"level": "success", "message": message}
    message = "质量提示：当前成品质量闸门未通过"
    if failed_count is not None:
        message += f"，未通过项={failed_count}"
    if quality_score is not None:
        message += f"，质量分={quality_score}"
    message += "。建议先载入结果复核后再交付。"
    return {"level": "warning", "message": message}


def _recent_job_needs_review(item: dict[str, Any]) -> bool:
    if not isinstance(item, dict):
        return False
    status = str(item.get("status") or "").strip().lower()
    return status == "done" and item.get("quality_gate_ok") is False


def _recent_job_action_label(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return "载入结果"
    status = str(item.get("status") or "").strip().lower()
    if status in {"queued", "running"}:
        return "接回任务"
    if _recent_job_needs_review(item):
        return "载入复核"
    return "载入结果"


def _review_workspace_focus_notice(result: dict[str, Any], focus_job_id: str) -> str:
    if not isinstance(result, dict):
        return ""
    job_id = str(result.get("job_id") or "").strip()
    if not job_id or job_id != str(focus_job_id or "").strip():
        return ""
    quality_map = result.get("quality_by_variant") if isinstance(result.get("quality_by_variant"), dict) else {}
    failed_variants = sum(
        1
        for info in quality_map.values()
        if isinstance(info, dict) and info.get("quality_gate_ok") is False
    )
    if failed_variants <= 0:
        return ""
    return (
        f"当前载入的是待复核成品，共 {failed_variants} 个方案未通过质量闸门。"
        "建议先载入问题清单并完成回写后再交付。"
    )


def _recent_job_sort_key(item: dict[str, Any]) -> tuple[int, float]:
    if not isinstance(item, dict):
        return (99, 0.0)
    status = str(item.get("status") or "").strip().lower()
    quality_gate_ok = item.get("quality_gate_ok")
    try:
        ts = float(item.get("updated_at") or item.get("created_at") or 0.0)
    except Exception:
        ts = 0.0
    if status == "running":
        priority = 0
    elif status == "queued":
        priority = 1
    elif status == "done" and quality_gate_ok is False:
        priority = 2
    elif status == "failed":
        priority = 3
    elif status == "cancelled":
        priority = 4
    elif status == "done":
        priority = 5
    else:
        priority = 6
    return (priority, -ts)


def _recent_job_matches_filter(item: dict[str, Any], filter_key: str) -> bool:
    if not isinstance(item, dict):
        return False
    status = str(item.get("status") or "").strip().lower()
    key = str(filter_key or "all").strip().lower()
    if key == "active":
        return status in {"queued", "running"}
    if key == "review_needed":
        return _recent_job_needs_review(item)
    if key == "exceptions":
        return status in {"failed", "cancelled"}
    return status in {"queued", "running", "done", "failed", "cancelled"}


def _collect_job_result(base_url: str, actions_key: str, job_id: str) -> dict[str, Any]:
    raw_json = _download_bytes(base_url, actions_key, job_id, "json", 1, timeout=600)
    data = json.loads(raw_json.decode("utf-8", errors="ignore"))
    job_status_payload = _get_json(
        base_url,
        "/actions/job_status",
        actions_key,
        params={"job_id": job_id},
        timeout=60,
    )
    job_status = job_status_payload.get("job") if isinstance(job_status_payload, dict) else {}
    persisted_runtime_map = _normalize_variant_dict_map(job_status.get("runtime_by_variant"))
    persisted_quality_map = _normalize_variant_dict_map(job_status.get("quality_by_variant"))
    generation_mode_summary = (
        job_status.get("generation_mode_summary")
        if isinstance(job_status.get("generation_mode_summary"), dict)
        else {}
    )
    variants_data = data.get("variants") or []
    variants_n = max(1, len(variants_data), len(persisted_runtime_map), len(persisted_quality_map))

    artifacts: dict[int, dict[str, bytes]] = {}
    quality_map: dict[int, dict[str, Any]] = {}
    runtime_map: dict[int, dict[str, Any]] = {}
    generation_trace_map: dict[int, dict[str, Any]] = {}
    runtime_budget_map: dict[int, list[dict[str, Any]]] = {}
    remediation_map: dict[int, dict[str, Any]] = {}
    for v in range(1, variants_n + 1):
        artifacts[v] = {}
        artifacts[v]["docx"] = _download_bytes(base_url, actions_key, job_id, "docx", v, timeout=600)
        artifacts[v]["compare_docx"] = _download_bytes(base_url, actions_key, job_id, "compare_docx", v, timeout=600)
        try:
            artifacts[v]["focus_xlsx"] = _download_bytes(base_url, actions_key, job_id, "focus_xlsx", v, timeout=600)
        except Exception:
            pass
        try:
            artifacts[v]["score_overview_xlsx"] = _download_bytes(
                base_url,
                actions_key,
                job_id,
                "score_overview_xlsx",
                v,
                timeout=600,
            )
        except Exception:
            pass
        try:
            artifacts[v]["expert_review_docx"] = _download_bytes(
                base_url,
                actions_key,
                job_id,
                "expert_review_docx",
                v,
                timeout=600,
            )
        except Exception:
            pass
        rec = variants_data[v - 1] if v <= len(variants_data) else {}
        persisted_runtime = persisted_runtime_map.get(v) if isinstance(persisted_runtime_map.get(v), dict) else {}
        persisted_quality = persisted_quality_map.get(v) if isinstance(persisted_quality_map.get(v), dict) else {}
        qc = rec.get("quality_checks") or {}
        mode_policy = rec.get("mode_policy") if isinstance(rec.get("mode_policy"), dict) else {}
        agent_contract_checks = rec.get("agent_contract_checks") if isinstance(rec.get("agent_contract_checks"), dict) else {}
        score_mapping = rec.get("score_mapping") if isinstance(rec.get("score_mapping"), dict) else {}
        logic_template = rec.get("logic_template") if isinstance(rec.get("logic_template"), dict) else {}
        runtime_map[v] = {
            "generation_mode": persisted_runtime.get("generation_mode") or rec.get("generation_mode"),
            "mode_effective": persisted_runtime.get("mode_effective") or mode_policy.get("mode_effective"),
            "planned_total_pages": mode_policy.get("planned_total_pages"),
            "section_count": persisted_runtime.get("section_count"),
            "pipeline_stages": persisted_runtime.get("pipeline_stages")
            if isinstance(persisted_runtime.get("pipeline_stages"), list)
            else (rec.get("pipeline_stages") if isinstance(rec.get("pipeline_stages"), list) else []),
            "retrieval_cache": persisted_runtime.get("retrieval_cache") if isinstance(persisted_runtime.get("retrieval_cache"), dict) else {},
            "self_evolution": persisted_runtime.get("self_evolution") if isinstance(persisted_runtime.get("self_evolution"), dict) else {},
            "section_runtime_budget_preview": persisted_runtime.get("section_runtime_budget_preview")
            if isinstance(persisted_runtime.get("section_runtime_budget_preview"), list)
            else [],
            "resource_usage_summary": persisted_runtime.get("resource_usage_summary")
            if isinstance(persisted_runtime.get("resource_usage_summary"), dict)
            else {},
            "agent_contract_ok": agent_contract_checks.get("ok"),
            "agent_contract_error_count": agent_contract_checks.get("error_count"),
            "score_high_risk_count": ((score_mapping.get("summary") or {}).get("high_risk_item_count") if isinstance(score_mapping, dict) else None),
        }
        generation_trace_map[v] = rec.get("generation_trace") if isinstance(rec.get("generation_trace"), dict) else {}
        runtime_budget_map[v] = [
            {
                "title": str(sec.get("title") or "").strip(),
                "requested_timeout_sec": sec.get("requested_timeout_sec"),
                "requested_max_output_tokens": sec.get("requested_max_output_tokens"),
                "requested_section_retry_limit": sec.get("requested_section_retry_limit"),
                "runtime_budget_reason": str(sec.get("runtime_budget_reason") or "").strip(),
                "evolution_applied": bool(sec.get("evolution_applied", False)),
                "evolution_reason": str(sec.get("evolution_reason") or "").strip(),
                "evolution_source_runs": int(sec.get("evolution_source_runs") or 0),
                "used_key_alias": str(sec.get("used_key_alias") or "").strip(),
            }
            for sec in (rec.get("sections") or [])
            if isinstance(sec, dict) and str(sec.get("title") or "").strip()
        ]
        quality_gate = rec.get("quality_gate") if isinstance(rec.get("quality_gate"), dict) else {}
        terminology_audit = rec.get("terminology_audit") if isinstance(rec.get("terminology_audit"), dict) else {}
        quality_draft = rec.get("quality_checks_draft") if isinstance(rec.get("quality_checks_draft"), dict) else {}
        pipeline_stages = rec.get("pipeline_stages") if isinstance(rec.get("pipeline_stages"), list) else []
        remediation_map[v] = {
            "quality_gate_ok": bool(quality_gate.get("ok", False)),
            "quality_gate_failed_count": len(quality_gate.get("failed") or []) if isinstance(quality_gate.get("failed"), list) else 0,
            "quality_gate_retry_rounds": int(rec.get("quality_gate_retry_rounds") or 0),
            "quality_score_final": qc.get("score"),
            "quality_score_draft": quality_draft.get("score"),
            "terminology_loaded": bool(terminology_audit.get("terminology_loaded", False)),
            "terminology_changed_sections": int(terminology_audit.get("changed_sections") or 0),
            "terminology_replacement_count": int(terminology_audit.get("replacement_count") or 0),
            "llm_invoked_sections": int(terminology_audit.get("llm_invoked_sections") or 0),
            "traceability_failed": next(
                (
                    int(item.get("failed") or 0)
                    for item in pipeline_stages
                    if isinstance(item, dict) and str(item.get("stage") or "") == "traceability_patch"
                ),
                0,
            ),
            "final_length_trimmed_total": sum(
                int(item.get("trimmed") or 0)
                for item in pipeline_stages
                if isinstance(item, dict) and "final_length_clamp" in str(item.get("stage") or "")
            ),
            "remediation_strategy_audit": persisted_quality.get("remediation_strategy_audit")
            if isinstance(persisted_quality.get("remediation_strategy_audit"), dict)
            else (qc.get("remediation_strategy_audit") if isinstance(qc.get("remediation_strategy_audit"), dict) else {}),
            "remediation_execution_audit": persisted_quality.get("remediation_execution_audit")
            if isinstance(persisted_quality.get("remediation_execution_audit"), dict)
            else (qc.get("remediation_execution_audit") if isinstance(qc.get("remediation_execution_audit"), dict) else {}),
        }
        quality_map[v] = {
            "logic_template_id": persisted_quality.get("logic_template_id")
            or rec.get("logic_template_id")
            or logic_template.get("id"),
            "logic_template_name": persisted_quality.get("logic_template_name")
            or rec.get("logic_template_name")
            or logic_template.get("name"),
            "quality_score": persisted_quality.get("quality_score", qc.get("score")),
            "quality_gate_ok": persisted_quality.get("quality_gate_ok", quality_gate.get("ok")),
            "quality_gate_failed_count": persisted_quality.get(
                "quality_gate_failed_count",
                len(quality_gate.get("failed") or []) if isinstance(quality_gate.get("failed"), list) else 0,
            ),
            "structure": (qc.get("structure") or {}).get("ok"),
            "officialese": (qc.get("officialese") or {}).get("ok"),
            "risk_triplet": (qc.get("risk_triplet") or {}).get("ok"),
            "qse_closed_loop": (qc.get("qse_closed_loop") or {}).get("ok"),
            "logic_template_adherence": (qc.get("logic_template_adherence") or {}).get("ok"),
            "chapter_blueprint_adherence": (qc.get("chapter_blueprint_adherence") or {}).get("ok"),
            "variant_diversity": (qc.get("variant_diversity") or {}).get("ok"),
            "quantitative": (qc.get("quantitative") or {}).get("ok"),
            "required_topics_detail": (qc.get("required_topics_detail") or {}).get("ok"),
            "evidence_traceability": (qc.get("evidence_traceability") or {}).get("ok"),
            "drawing_evidence": (qc.get("drawing_evidence") or {}).get("ok"),
            "standard_evidence": (qc.get("standard_evidence") or {}).get("ok"),
            "boq_focus_item_typed_evidence": (qc.get("boq_focus_item_typed_evidence") or {}).get("ok"),
            "consistency": (qc.get("consistency") or {}).get("ok"),
            "remediation_strategy_audit": persisted_quality.get("remediation_strategy_audit")
            if isinstance(persisted_quality.get("remediation_strategy_audit"), dict)
            else {},
            "remediation_execution_audit": persisted_quality.get("remediation_execution_audit")
            if isinstance(persisted_quality.get("remediation_execution_audit"), dict)
            else {},
        }

    return {
        "job_id": job_id,
        "variants": variants_n,
        "topic": (variants_data[0] or {}).get("topic") if variants_data else "",
        "project_type": (variants_data[0] or {}).get("project_type") if variants_data else "",
        "artifacts": artifacts,
        "quality_by_variant": quality_map,
        "runtime_by_variant": runtime_map,
        "generation_mode_summary": generation_mode_summary,
        "generation_trace_by_variant": generation_trace_map,
        "runtime_budget_by_variant": runtime_budget_map,
        "remediation_by_variant": remediation_map,
        "stage_artifacts_dir": str(job_status.get("stage_artifacts_dir") or "").strip(),
        "agent_runtime": job_status.get("agent_runtime") if isinstance(job_status.get("agent_runtime"), dict) else {},
        "result_json": raw_json,
    }


def _render_automation_summary() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return
    remediation_map = result.get("remediation_by_variant") if isinstance(result.get("remediation_by_variant"), dict) else {}
    generation_trace_map = result.get("generation_trace_by_variant") if isinstance(result.get("generation_trace_by_variant"), dict) else {}
    if not remediation_map:
        return

    st.markdown("#### 自动巡检/自动修复状态（辅助）")
    st.caption("辅助留痕，用于确认本次生成是否执行自动巡检与自动修复；不代表问题已全部自动闭环。")
    tabs = st.tabs([f"v{i}" for i in sorted(remediation_map.keys())]) if remediation_map else []
    for idx, tab in zip(sorted(remediation_map.keys()), tabs):
        with tab:
            info = remediation_map.get(idx) or {}
            gate_ok = bool(info.get("quality_gate_ok"))
            retry_rounds = int(info.get("quality_gate_retry_rounds") or 0)
            failed_count = int(info.get("quality_gate_failed_count") or 0)
            changed_sections = int(info.get("terminology_changed_sections") or 0)
            replacement_count = int(info.get("terminology_replacement_count") or 0)
            llm_invoked_sections = int(info.get("llm_invoked_sections") or 0)
            traceability_failed = int(info.get("traceability_failed") or 0)
            trimmed_total = int(info.get("final_length_trimmed_total") or 0)
            strategy_audit = info.get("remediation_strategy_audit") if isinstance(info.get("remediation_strategy_audit"), dict) else {}
            execution_audit = info.get("remediation_execution_audit") if isinstance(info.get("remediation_execution_audit"), dict) else {}

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("自动巡检", "已执行")
            c2.metric("自动修复轮次", retry_rounds)
            c3.metric("术语纠偏替换", replacement_count)
            c4.metric("长度收口次数", trimmed_total)

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("质量门", "通过" if gate_ok else "未完全通过")
            c6.metric("质量门失败项", failed_count)
            c7.metric("术语调整章节", changed_sections)
            c8.metric("术语LLM介入章节", llm_invoked_sections)

            if traceability_failed > 0:
                st.caption(f"证据追溯补丁失败项：{traceability_failed}")
            draft_score = info.get("quality_score_draft")
            final_score = info.get("quality_score_final")
            score_parts = []
            if draft_score is not None:
                score_parts.append(f"初检分={draft_score}")
            if final_score is not None:
                score_parts.append(f"终检分={final_score}")
            if score_parts:
                st.caption("；".join(score_parts))
            indicator_rows = strategy_audit.get("indicator_groups") if isinstance(strategy_audit.get("indicator_groups"), list) else []
            strategy_rows = strategy_audit.get("strategies") if isinstance(strategy_audit.get("strategies"), list) else []
            if indicator_rows:
                brief = []
                for row in indicator_rows[:3]:
                    if not isinstance(row, dict):
                        continue
                    name = str(row.get("indicator_group") or "").strip()
                    cnt = int(row.get("count") or 0)
                    if name:
                        brief.append(f"{name}={cnt}")
                if brief:
                    st.caption("修复策略命中：" + "；".join(brief))
            if strategy_rows:
                brief = []
                for row in strategy_rows[:3]:
                    if not isinstance(row, dict):
                        continue
                    sid = str(row.get("strategy_id") or "").strip()
                    cnt = int(row.get("count") or 0)
                    if sid:
                        brief.append(f"{sid}={cnt}")
                if brief:
                    st.caption("策略映射表：" + "；".join(brief))
            action_rows = execution_audit.get("action_tags") if isinstance(execution_audit.get("action_tags"), list) else []
            status_rows = execution_audit.get("status_counts") if isinstance(execution_audit.get("status_counts"), list) else []
            trace = generation_trace_map.get(idx) if isinstance(generation_trace_map.get(idx), dict) else {}
            evo = trace.get("self_evolution") if isinstance(trace.get("self_evolution"), dict) else {}
            combo_learning_applied_count = int(evo.get("remediation_combo_learning_applied_count") or 0)
            combo_learning_source_runs = int(evo.get("remediation_combo_learning_source_runs") or 0)
            combo_learning_reasons = evo.get("remediation_combo_learning_reasons") if isinstance(evo.get("remediation_combo_learning_reasons"), list) else []
            combo_learning_combos = evo.get("remediation_combo_learning_combos") if isinstance(evo.get("remediation_combo_learning_combos"), list) else []
            combo_bundle_learning_applied_count = int(evo.get("remediation_combo_bundle_learning_applied_count") or 0)
            combo_bundle_learning_source_runs = int(evo.get("remediation_combo_bundle_learning_source_runs") or 0)
            combo_bundle_learning_reasons = evo.get("remediation_combo_bundle_learning_reasons") if isinstance(evo.get("remediation_combo_bundle_learning_reasons"), list) else []
            combo_bundle_learning_bundles = evo.get("remediation_combo_bundle_learning_bundles") if isinstance(evo.get("remediation_combo_bundle_learning_bundles"), list) else []
            context_bundle_learning_applied_count = int(evo.get("remediation_context_bundle_learning_applied_count") or 0)
            context_bundle_learning_source_runs = int(evo.get("remediation_context_bundle_learning_source_runs") or 0)
            context_bundle_learning_contexts = evo.get("remediation_context_bundle_learning_contexts") if isinstance(evo.get("remediation_context_bundle_learning_contexts"), list) else []
            context_bundle_learning_reasons = evo.get("remediation_context_bundle_learning_reasons") if isinstance(evo.get("remediation_context_bundle_learning_reasons"), list) else []
            context_bundle_learning_bundles = evo.get("remediation_context_bundle_learning_bundles") if isinstance(evo.get("remediation_context_bundle_learning_bundles"), list) else []
            context_bundle_effect_applied_count = int(evo.get("remediation_context_bundle_learning_effect_applied_count") or 0)
            context_bundle_effect_source_runs = int(evo.get("remediation_context_bundle_learning_effect_source_runs") or 0)
            context_bundle_effect_reasons = evo.get("remediation_context_bundle_learning_effect_reasons") if isinstance(evo.get("remediation_context_bundle_learning_effect_reasons"), list) else []
            context_bundle_effect_bundles = evo.get("remediation_context_bundle_learning_effect_bundles") if isinstance(evo.get("remediation_context_bundle_learning_effect_bundles"), list) else []
            context_bundle_metric_effect_applied_count = int(evo.get("remediation_context_bundle_learning_metric_effect_applied_count") or 0)
            context_bundle_metric_effect_source_runs = int(evo.get("remediation_context_bundle_learning_metric_effect_source_runs") or 0)
            context_bundle_metric_effect_metrics = evo.get("remediation_context_bundle_learning_metric_effect_metrics") if isinstance(evo.get("remediation_context_bundle_learning_metric_effect_metrics"), list) else []
            context_bundle_metric_effect_reasons = evo.get("remediation_context_bundle_learning_metric_effect_reasons") if isinstance(evo.get("remediation_context_bundle_learning_metric_effect_reasons"), list) else []
            context_bundle_metric_effect_bundles = evo.get("remediation_context_bundle_learning_metric_effect_bundles") if isinstance(evo.get("remediation_context_bundle_learning_metric_effect_bundles"), list) else []
            context_bundle_metric_action_effect_applied_count = int(evo.get("remediation_context_bundle_learning_metric_action_effect_applied_count") or 0)
            context_bundle_metric_action_effect_source_runs = int(evo.get("remediation_context_bundle_learning_metric_action_effect_source_runs") or 0)
            context_bundle_metric_action_effect_triplets = evo.get("remediation_context_bundle_learning_metric_action_effect_triplets") if isinstance(evo.get("remediation_context_bundle_learning_metric_action_effect_triplets"), list) else []
            context_bundle_metric_action_effect_reasons = evo.get("remediation_context_bundle_learning_metric_action_effect_reasons") if isinstance(evo.get("remediation_context_bundle_learning_metric_action_effect_reasons"), list) else []
            context_bundle_metric_action_effect_bundles = evo.get("remediation_context_bundle_learning_metric_action_effect_bundles") if isinstance(evo.get("remediation_context_bundle_learning_metric_action_effect_bundles"), list) else []
            chapter_effect_summary = evo.get("chapter_effect_summary") if isinstance(evo.get("chapter_effect_summary"), list) else []
            if not chapter_effect_summary:
                try:
                    from backend.zhifei_autoplan.self_evolution import build_chapter_effect_summary

                    chapter_effect_summary = build_chapter_effect_summary(evo, limit=3)
                except Exception:
                    chapter_effect_summary = []
            if action_rows:
                brief = []
                for row in action_rows[:4]:
                    if not isinstance(row, dict):
                        continue
                    label = str(row.get("label") or row.get("action_tag") or "").strip()
                    cnt = int(row.get("count") or 0)
                    if label:
                        brief.append(f"{label}={cnt}")
                if brief:
                    st.caption("本次修订动作画像：" + "；".join(brief))
            if status_rows:
                brief = []
                for row in status_rows[:3]:
                    if not isinstance(row, dict):
                        continue
                    status_name = str(row.get("status") or "").strip()
                    cnt = int(row.get("count") or 0)
                    if status_name:
                        brief.append(f"{status_name}={cnt}")
                if brief:
                    st.caption("动作执行状态：" + "；".join(brief))
            if combo_learning_applied_count > 0:
                line = f"修订排序已叠加历史有效组合学习={combo_learning_applied_count}项"
                if combo_learning_source_runs > 0:
                    line += f"（样本={combo_learning_source_runs}）"
                st.caption(line)
                if combo_learning_combos:
                    st.caption("高有效组合：" + "；".join([str(x) for x in combo_learning_combos[:2] if str(x).strip()]))
                if combo_learning_reasons:
                    st.caption("排序依据：" + "；".join([str(x) for x in combo_learning_reasons[:2] if str(x).strip()]))
            if combo_bundle_learning_applied_count > 0:
                line = f"修订排序已叠加高通过组合包学习={combo_bundle_learning_applied_count}项"
                if combo_bundle_learning_source_runs > 0:
                    line += f"（样本={combo_bundle_learning_source_runs}）"
                st.caption(line)
                if combo_bundle_learning_bundles:
                    st.caption("高通过组合包：" + "；".join([str(x) for x in combo_bundle_learning_bundles[:2] if str(x).strip()]))
                if combo_bundle_learning_reasons:
                    st.caption("组合包依据：" + "；".join([str(x) for x in combo_bundle_learning_reasons[:2] if str(x).strip()]))
            if context_bundle_learning_applied_count > 0:
                line = f"修订排序已叠加高通过语境组合包学习={context_bundle_learning_applied_count}项"
                if context_bundle_learning_source_runs > 0:
                    line += f"（样本={context_bundle_learning_source_runs}）"
                st.caption(line)
                if context_bundle_learning_contexts:
                    st.caption("语境命中：" + "；".join([str(x) for x in context_bundle_learning_contexts[:2] if str(x).strip()]))
                if context_bundle_learning_bundles:
                    st.caption("高通过语境组合包：" + "；".join([str(x) for x in context_bundle_learning_bundles[:2] if str(x).strip()]))
                if context_bundle_learning_reasons:
                    st.caption("语境组合包依据：" + "；".join([str(x) for x in context_bundle_learning_reasons[:2] if str(x).strip()]))
            if context_bundle_effect_applied_count > 0:
                line = f"语境组合包效果归因已参与={context_bundle_effect_applied_count}项"
                if context_bundle_effect_source_runs > 0:
                    line += f"（归因样本={context_bundle_effect_source_runs}）"
                st.caption(line)
                if context_bundle_effect_bundles:
                    st.caption("高通过归因语境组合包：" + "；".join([str(x) for x in context_bundle_effect_bundles[:2] if str(x).strip()]))
                if context_bundle_effect_reasons:
                    st.caption("效果归因依据：" + "；".join([str(x) for x in context_bundle_effect_reasons[:2] if str(x).strip()]))
            if context_bundle_metric_effect_applied_count > 0:
                line = f"语境组合包硬闸门拉平归因已参与={context_bundle_metric_effect_applied_count}项"
                if context_bundle_metric_effect_source_runs > 0:
                    line += f"（样本={context_bundle_metric_effect_source_runs}）"
                st.caption(line)
                if context_bundle_metric_effect_metrics:
                    st.caption("被拉平指标：" + "；".join([str(x) for x in context_bundle_metric_effect_metrics[:3] if str(x).strip()]))
                if context_bundle_metric_effect_bundles:
                    st.caption("指标归因语境组合包：" + "；".join([str(x) for x in context_bundle_metric_effect_bundles[:2] if str(x).strip()]))
                if context_bundle_metric_effect_reasons:
                    st.caption("指标归因依据：" + "；".join([str(x) for x in context_bundle_metric_effect_reasons[:2] if str(x).strip()]))
            if context_bundle_metric_action_effect_applied_count > 0:
                line = f"指标+动作拉平归因已参与={context_bundle_metric_action_effect_applied_count}项"
                if context_bundle_metric_action_effect_source_runs > 0:
                    line += f"（样本={context_bundle_metric_action_effect_source_runs}）"
                st.caption(line)
                if context_bundle_metric_action_effect_triplets:
                    st.caption("被拉平动作组合：" + "；".join([str(x) for x in context_bundle_metric_action_effect_triplets[:3] if str(x).strip()]))
                if context_bundle_metric_action_effect_bundles:
                    st.caption("动作归因语境组合包：" + "；".join([str(x) for x in context_bundle_metric_action_effect_bundles[:2] if str(x).strip()]))
                if context_bundle_metric_action_effect_reasons:
                    st.caption("动作归因依据：" + "；".join([str(x) for x in context_bundle_metric_action_effect_reasons[:2] if str(x).strip()]))
            if chapter_effect_summary:
                brief = []
                for row in chapter_effect_summary[:2]:
                    if not isinstance(row, dict):
                        continue
                    title = str(row.get("title") or "").strip()
                    metrics = row.get("resolved_metrics") if isinstance(row.get("resolved_metrics"), list) else []
                    triplets = row.get("resolved_action_triplets") if isinstance(row.get("resolved_action_triplets"), list) else []
                    parts = []
                    if metrics:
                        parts.append("指标=" + "/".join([str(x) for x in metrics[:2] if str(x).strip()]))
                    if triplets:
                        parts.append("动作=" + "/".join([str(x) for x in triplets[:2] if str(x).strip()]))
                    if title and parts:
                        brief.append(f"{title} -> {'；'.join(parts)}")
                if brief:
                    st.caption("章节级拉平摘要：" + "；".join(brief))

            if gate_ok:
                st.success("本版本已执行自动巡检与自动修复，质量门已通过。")
            else:
                st.warning("本版本已执行自动巡检与自动修复，但质量门仍未完全通过。请优先查看“问题清单+自动修订建议”或进行人工复核。")


def _render_result_aux_summary() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return
    remediation_map = result.get("remediation_by_variant") if isinstance(result.get("remediation_by_variant"), dict) else {}
    runtime = result.get("agent_runtime") if isinstance(result.get("agent_runtime"), dict) else {}
    stage_artifacts_dir = str(result.get("stage_artifacts_dir") or "").strip()
    generation_trace_map = result.get("generation_trace_by_variant") if isinstance(result.get("generation_trace_by_variant"), dict) else {}
    if not remediation_map and not runtime and not stage_artifacts_dir and not generation_trace_map:
        return

    gate_rows = [v for v in remediation_map.values() if isinstance(v, dict)]
    total_variants = max(1, int(result.get("variants") or len(gate_rows) or 1))
    passed_variants = sum(1 for row in gate_rows if bool(row.get("quality_gate_ok")))
    failed_items = sum(int(row.get("quality_gate_failed_count") or 0) for row in gate_rows)
    retry_rounds = max([int(row.get("quality_gate_retry_rounds") or 0) for row in gate_rows] or [0])
    terminology_replacements = sum(int(row.get("terminology_replacement_count") or 0) for row in gate_rows)
    trimmed_total = sum(int(row.get("final_length_trimmed_total") or 0) for row in gate_rows)

    try:
        requested_ap = int(runtime.get("requested_agent_parallelism") or 0)
    except Exception:
        requested_ap = 0
    try:
        effective_ap = int(runtime.get("agent_parallelism") or 0)
    except Exception:
        effective_ap = 0
    try:
        variant_parallelism = int(runtime.get("variant_parallelism") or 0)
    except Exception:
        variant_parallelism = 0
    reason = str(runtime.get("runtime_agent_parallelism_reason") or "").strip()
    learning_applied = bool(runtime.get("runtime_agent_parallelism_learning_applied", False))
    learning_reason = str(runtime.get("runtime_agent_parallelism_learning_reason") or "").strip()
    try:
        learning_source_runs = int(runtime.get("runtime_agent_parallelism_learning_source_runs") or 0)
    except Exception:
        learning_source_runs = 0

    stage_count = 0
    self_evolution_applied_total = 0
    self_evolution_titles: list[str] = []
    self_evolution_source_runs = 0
    combo_learning_applied_total = 0
    combo_learning_source_runs = 0
    combo_learning_combos: list[str] = []
    combo_bundle_learning_applied_total = 0
    combo_bundle_learning_source_runs = 0
    combo_bundle_learning_bundles: list[str] = []
    context_bundle_learning_applied_total = 0
    context_bundle_learning_source_runs = 0
    context_bundle_learning_bundles: list[str] = []
    context_bundle_effect_applied_total = 0
    context_bundle_effect_source_runs = 0
    context_bundle_effect_bundles: list[str] = []
    for trace in generation_trace_map.values():
        if not isinstance(trace, dict):
            continue
        stages = trace.get("pipeline_stages") if isinstance(trace.get("pipeline_stages"), list) else []
        stage_count = max(stage_count, len(stages))
        evo = trace.get("self_evolution") if isinstance(trace.get("self_evolution"), dict) else {}
        self_evolution_applied_total += int(evo.get("applied_count") or 0)
        combo_learning_applied_total += int(evo.get("remediation_combo_learning_applied_count") or 0)
        combo_learning_source_runs = max(combo_learning_source_runs, int(evo.get("remediation_combo_learning_source_runs") or 0))
        combo_bundle_learning_applied_total += int(evo.get("remediation_combo_bundle_learning_applied_count") or 0)
        combo_bundle_learning_source_runs = max(combo_bundle_learning_source_runs, int(evo.get("remediation_combo_bundle_learning_source_runs") or 0))
        context_bundle_learning_applied_total += int(evo.get("remediation_context_bundle_learning_applied_count") or 0)
        context_bundle_learning_source_runs = max(context_bundle_learning_source_runs, int(evo.get("remediation_context_bundle_learning_source_runs") or 0))
        context_bundle_effect_applied_total += int(evo.get("remediation_context_bundle_learning_effect_applied_count") or 0)
        context_bundle_effect_source_runs = max(context_bundle_effect_source_runs, int(evo.get("remediation_context_bundle_learning_effect_source_runs") or 0))
        for title in (evo.get("applied_titles") or []) if isinstance(evo.get("applied_titles"), list) else []:
            name = str(title or "").strip()
            if name and name not in self_evolution_titles:
                self_evolution_titles.append(name)
        for combo in (evo.get("remediation_combo_learning_combos") or []) if isinstance(evo.get("remediation_combo_learning_combos"), list) else []:
            text = str(combo or "").strip()
            if text and text not in combo_learning_combos:
                combo_learning_combos.append(text)
        for bundle in (evo.get("remediation_combo_bundle_learning_bundles") or []) if isinstance(evo.get("remediation_combo_bundle_learning_bundles"), list) else []:
            text = str(bundle or "").strip()
            if text and text not in combo_bundle_learning_bundles:
                combo_bundle_learning_bundles.append(text)
        for bundle in (evo.get("remediation_context_bundle_learning_bundles") or []) if isinstance(evo.get("remediation_context_bundle_learning_bundles"), list) else []:
            text = str(bundle or "").strip()
            if text and text not in context_bundle_learning_bundles:
                context_bundle_learning_bundles.append(text)
        for bundle in (evo.get("remediation_context_bundle_learning_effect_bundles") or []) if isinstance(evo.get("remediation_context_bundle_learning_effect_bundles"), list) else []:
            text = str(bundle or "").strip()
            if text and text not in context_bundle_effect_bundles:
                context_bundle_effect_bundles.append(text)
    for rows in (result.get("runtime_budget_by_variant") or {}).values() if isinstance(result.get("runtime_budget_by_variant"), dict) else []:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or not bool(row.get("evolution_applied", False)):
                continue
            try:
                self_evolution_source_runs = max(self_evolution_source_runs, int(row.get("evolution_source_runs") or 0))
            except Exception:
                continue

    st.markdown("#### 本次运行摘要")
    st.caption("这是面向使用者的简明摘要；详细技术留痕已收纳到下方“辅助留痕详情”。")
    cols = st.columns(4)
    cols[0].metric("质量门通过版本", f"{passed_variants}/{total_variants}")
    cols[1].metric("自动修复轮次", retry_rounds)
    cols[2].metric("术语纠偏替换", terminology_replacements)
    cols[3].metric("长度收口次数", trimmed_total)

    summary_parts: list[str] = []
    if requested_ap > 0 and effective_ap > 0:
        part = f"章节并行请求={requested_ap}，实际执行={effective_ap}"
        if requested_ap != effective_ap and reason:
            part += f"（{reason}）"
        summary_parts.append(part)
    if variant_parallelism > 0:
        summary_parts.append(f"方案并行={variant_parallelism}")
    if stage_count > 0:
        summary_parts.append(f"阶段留痕已记录 {stage_count} 个主阶段")
    if stage_artifacts_dir:
        summary_parts.append(f"留痕目录已生成")
    if self_evolution_applied_total > 0:
        evo_line = f"运行期学习已应用到 {self_evolution_applied_total} 个章节"
        if self_evolution_source_runs > 0:
            evo_line += f"（基于 {self_evolution_source_runs} 次历史样本）"
        if self_evolution_titles:
            evo_line += f"，例如：{' / '.join(self_evolution_titles[:3])}"
        summary_parts.append(evo_line)
    if learning_applied:
        evo_parallel_line = "任务级并发学习已参与本次收敛"
        if learning_source_runs > 0:
            evo_parallel_line += f"（基于 {learning_source_runs} 次历史样本）"
        if learning_reason:
            evo_parallel_line += f"，原因：{learning_reason}"
        summary_parts.append(evo_parallel_line)
    if combo_learning_applied_total > 0:
        combo_line = f"修订排序已叠加历史有效组合学习={combo_learning_applied_total}项"
        if combo_learning_source_runs > 0:
            combo_line += f"（基于 {combo_learning_source_runs} 次历史样本）"
        if combo_learning_combos:
            combo_line += f"，例如：{' / '.join(combo_learning_combos[:2])}"
        summary_parts.append(combo_line)
    if combo_bundle_learning_applied_total > 0:
        bundle_line = f"修订排序已叠加高通过组合包学习={combo_bundle_learning_applied_total}项"
        if combo_bundle_learning_source_runs > 0:
            bundle_line += f"（基于 {combo_bundle_learning_source_runs} 次历史样本）"
        if combo_bundle_learning_bundles:
            bundle_line += f"，例如：{' / '.join(combo_bundle_learning_bundles[:2])}"
        summary_parts.append(bundle_line)
    if context_bundle_learning_applied_total > 0:
        context_bundle_line = f"修订排序已叠加高通过语境组合包学习={context_bundle_learning_applied_total}项"
        if context_bundle_learning_source_runs > 0:
            context_bundle_line += f"（基于 {context_bundle_learning_source_runs} 次历史样本）"
        if context_bundle_learning_bundles:
            context_bundle_line += f"，例如：{' / '.join(context_bundle_learning_bundles[:2])}"
        summary_parts.append(context_bundle_line)
    if context_bundle_effect_applied_total > 0:
        effect_line = f"语境组合包效果归因已参与={context_bundle_effect_applied_total}项"
        if context_bundle_effect_source_runs > 0:
            effect_line += f"（基于 {context_bundle_effect_source_runs} 次归因样本）"
        if context_bundle_effect_bundles:
            effect_line += f"，例如：{' / '.join(context_bundle_effect_bundles[:2])}"
        summary_parts.append(effect_line)
    if summary_parts:
        st.caption("；".join(summary_parts))

    if gate_rows and passed_variants == total_variants and failed_items == 0:
        st.success("自动巡检与自动修复已执行，本次版本的质量门已通过。")
    elif gate_rows:
        st.warning(f"自动巡检与自动修复已执行，但仍有 {failed_items} 项质量门问题未完全闭环。")
    else:
        st.info("本次结果尚未汇总出完整的自动巡检摘要，可展开下方详情查看阶段留痕。")


def _render_runtime_parallelism_summary() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return
    runtime = result.get("agent_runtime") if isinstance(result.get("agent_runtime"), dict) else {}
    try:
        requested_ap = int(runtime.get("requested_agent_parallelism") or 0)
    except Exception:
        requested_ap = 0
    try:
        effective_ap = int(runtime.get("agent_parallelism") or 0)
    except Exception:
        effective_ap = 0
    try:
        variant_parallelism = int(runtime.get("variant_parallelism") or 0)
    except Exception:
        variant_parallelism = 0
    try:
        planned_pages = int(runtime.get("planned_total_pages") or 0)
    except Exception:
        planned_pages = 0
    try:
        outline_count = int(runtime.get("outline_count") or 0)
    except Exception:
        outline_count = 0
    reason = str(runtime.get("runtime_agent_parallelism_reason") or "").strip()
    learning_applied = bool(runtime.get("runtime_agent_parallelism_learning_applied", False))
    learning_reason = str(runtime.get("runtime_agent_parallelism_learning_reason") or "").strip()
    try:
        learning_source_runs = int(runtime.get("runtime_agent_parallelism_learning_source_runs") or 0)
    except Exception:
        learning_source_runs = 0
    if requested_ap <= 0 and effective_ap <= 0 and variant_parallelism <= 0:
        return

    st.markdown("#### 运行期并发收敛（辅助）")
    st.caption("辅助留痕，展示本次任务实际执行时的并发收敛结果；不改变你在页面上填写的参数。")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("请求章节并行", requested_ap if requested_ap > 0 else "-")
    c2.metric("实际章节并行", effective_ap if effective_ap > 0 else "-")
    c3.metric("方案并行", variant_parallelism if variant_parallelism > 0 else "-")
    c4.metric("规划总页数", planned_pages if planned_pages > 0 else "-")
    if outline_count > 0:
        st.caption(f"目录项数：{outline_count}")
    learning_tokens = set(_split_runtime_parallelism_reasons(learning_reason)) if learning_applied and learning_reason else set()
    reason_text = _humanize_runtime_parallelism_reason(reason, exclude=learning_tokens)
    learning_reason_text = _humanize_runtime_parallelism_reason(learning_reason)
    if reason_text:
        st.info(f"本次运行期已自动收敛章节并行。原因：{reason_text}")
    elif requested_ap > 0 and effective_ap > 0:
        if requested_ap == effective_ap:
            st.success("本次运行期未下调章节并行，请求值已直接生效。")
        else:
            st.info(f"本次运行期已自动收敛章节并行：请求={requested_ap}，实际={effective_ap}。")
    if learning_applied:
        learning_line = "本次并发收敛已叠加运行期学习"
        if learning_source_runs > 0:
            learning_line += f"（样本={learning_source_runs}）"
        if learning_reason_text:
            learning_line += f"：{learning_reason_text}"
        st.caption(learning_line)


def _render_stage_trace_summary() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return
    generation_trace_map = result.get("generation_trace_by_variant") if isinstance(result.get("generation_trace_by_variant"), dict) else {}
    runtime_budget_map = result.get("runtime_budget_by_variant") if isinstance(result.get("runtime_budget_by_variant"), dict) else {}
    stage_artifacts_dir = str(result.get("stage_artifacts_dir") or "").strip()
    if not generation_trace_map and not stage_artifacts_dir and not runtime_budget_map:
        return

    st.markdown("#### 生成阶段留痕（辅助）")
    st.caption("辅助留痕，用于排障与阶段复盘；不代表后端唯一引用源。")
    if stage_artifacts_dir:
        st.code(stage_artifacts_dir, language="text")

    tabs = st.tabs([f"v{i}" for i in sorted(generation_trace_map.keys())]) if generation_trace_map else []
    for idx, tab in zip(sorted(generation_trace_map.keys()), tabs):
        with tab:
            trace = generation_trace_map.get(idx) or {}
            if not isinstance(trace, dict) or not trace:
                st.caption("当前版本暂无阶段留痕摘要。")
                continue
            meta_cols = st.columns(4)
            meta_cols[0].metric("章节数", int(trace.get("chapter_count") or 0))
            meta_cols[1].metric("目录项", int(trace.get("outline_count") or 0))
            meta_cols[2].metric("严格目录", "是" if bool(trace.get("strict_catalog_mode")) else "否")
            meta_cols[3].metric("质检重试", int(((trace.get("quality_gate") or {}).get("retry_rounds")) or 0))
            provider_chain = trace.get("provider_chain") if isinstance(trace.get("provider_chain"), list) else []
            if provider_chain:
                chips = []
                for row in provider_chain:
                    if not isinstance(row, dict):
                        continue
                    slot = str(row.get("slot") or "").strip()
                    provider = str(row.get("provider") or "").strip()
                    model = str(row.get("model") or "").strip()
                    alias = str(row.get("key_alias") or "").strip()
                    seg = " / ".join([x for x in [slot, provider, model, alias] if x])
                    if seg:
                        chips.append(seg)
                if chips:
                    st.caption("模型链：" + "  |  ".join(chips))
            stages = trace.get("pipeline_stages") if isinstance(trace.get("pipeline_stages"), list) else []
            if stages:
                rows = []
                for item in stages:
                    if not isinstance(item, dict):
                        continue
                    rows.append(
                        {
                            "stage": str(item.get("stage") or ""),
                            "ok": "是" if bool(item.get("ok", False)) else "否",
                            "score": item.get("score"),
                            "failed_count": item.get("failed_count"),
                            "round": item.get("round"),
                        }
                    )
                if rows:
                    st.dataframe(rows, width="stretch", hide_index=True)
            retrieval = trace.get("retrieval_cache") if isinstance(trace.get("retrieval_cache"), dict) else {}
            if retrieval:
                st.caption(
                    "检索缓存："
                    f"hits={int(retrieval.get('hits') or 0)} / "
                    f"misses={int(retrieval.get('misses') or 0)} / "
                    f"stores={int(retrieval.get('stores') or 0)}"
                )
            budget_rows = runtime_budget_map.get(idx) if isinstance(runtime_budget_map.get(idx), list) else []
            if budget_rows:
                st.caption("章节运行预算摘要：")
                table = []
                for row in budget_rows[:8]:
                    if not isinstance(row, dict):
                        continue
                    table.append(
                        {
                            "title": str(row.get("title") or ""),
                            "timeout_sec": row.get("requested_timeout_sec"),
                            "max_tokens": row.get("requested_max_output_tokens"),
                            "retry_limit": row.get("requested_section_retry_limit"),
                            "reason": str(row.get("runtime_budget_reason") or ""),
                            "evolution": "是" if bool(row.get("evolution_applied", False)) else "否",
                            "evolution_runs": int(row.get("evolution_source_runs") or 0),
                            "evolution_reason": str(row.get("evolution_reason") or ""),
                            "key_alias": str(row.get("used_key_alias") or ""),
                        }
                    )
                if table:
                    st.dataframe(table, width="stretch", hide_index=True)


def _load_recent_jobs(
    base_url: str,
    actions_key: str,
    limit: int = 6,
    *,
    statuses: str = "queued,running,done,failed,cancelled",
    max_age_hours: int = 48,
) -> list[dict[str, Any]]:
    try:
        payload = _get_json(
            base_url,
            "/actions/jobs/recent",
            actions_key,
            params={
                "limit": int(limit),
                "statuses": str(statuses or "queued,running,done,failed,cancelled"),
                "max_age_hours": int(max_age_hours or 48),
            },
            timeout=30,
        )
    except Exception:
        return []
    items = payload.get("items") if isinstance(payload, dict) else []
    return items if isinstance(items, list) else []


def _load_jobs_sla_summary(base_url: str, actions_key: str, limit: int = 200) -> dict[str, Any]:
    try:
        payload = _get_json(
            base_url,
            "/actions/jobs/sla_summary",
            actions_key,
            params={"limit": int(limit)},
            timeout=30,
        )
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _restore_recent_job(base_url: str, actions_key: str, item: dict[str, Any]) -> None:
    job_id = str(item.get("job_id") or "").strip()
    status = str(item.get("status") or "").strip().lower()
    if not job_id:
        raise ValueError("缺少 job_id")
    st.session_state["kg_trace_sample"] = None
    st.session_state["review_focus_job_id"] = ""
    st.session_state["review_focus_variant"] = 1
    if status in {"queued", "running"}:
        st.session_state["run_result"] = None
        st.session_state["active_job"] = {
            "job_id": job_id,
            "status": status,
            "project_id": item.get("project_id"),
            "variants": max(1, int(item.get("variants") or 1)),
            "progress": {
                "stage": item.get("progress_stage"),
                "percent": item.get("progress_percent"),
            },
        }
        _append_log(f"已接回后台任务：{job_id}")
        st.session_state["recent_job_flash"] = f"已接回后台任务：{job_id}"
        return
    if status == "done" and bool(item.get("result_available")):
        bundle = _collect_job_result(base_url, actions_key, job_id)
        bundle["project_id"] = item.get("project_id")
        quality_map = bundle.get("quality_by_variant") if isinstance(bundle.get("quality_by_variant"), dict) else {}
        review_needed = any(
            isinstance(info, dict) and info.get("quality_gate_ok") is False for info in quality_map.values()
        ) or _recent_job_needs_review(item)
        st.session_state["active_job"] = None
        st.session_state["run_result"] = bundle
        if review_needed:
            st.session_state["review_focus_job_id"] = job_id
            st.session_state["review_focus_variant"] = 1
            st.session_state[f"review_variant_{job_id}"] = 1
            _append_log(f"已载入待复核成品：{job_id}")
            st.session_state["recent_job_flash"] = f"已载入待复核成品：{job_id}，请优先查看问题清单审核区"
        else:
            _append_log(f"已载入最近成品：{job_id}")
            st.session_state["recent_job_flash"] = f"已载入最近成品：{job_id}"
        return
    raise ValueError("当前任务状态不可恢复")


def _maybe_resume_recent_job(recent_jobs: list[dict[str, Any]]) -> None:
    if st.session_state.get("active_job") or st.session_state.get("run_result"):
        return
    for item in recent_jobs:
        status = str(item.get("status") or "").strip().lower()
        job_id = str(item.get("job_id") or "").strip()
        if not job_id or status not in {"queued", "running"}:
            continue
        st.session_state["kg_trace_sample"] = None
        st.session_state["active_job"] = {
            "job_id": job_id,
            "status": status,
            "project_id": item.get("project_id"),
            "variants": max(1, int(item.get("variants") or 1)),
            "progress": {
                "stage": item.get("progress_stage"),
                "percent": item.get("progress_percent"),
            },
        }
        _append_log(f"检测到最近在途任务，已自动接回：{job_id}")
        st.session_state["recent_job_flash"] = f"已自动接回最近在途任务：{job_id}"
        return


def _render_recent_job_recovery(
    base_url: str,
    actions_key: str,
    items: list[dict[str, Any]],
    sla_summary: dict[str, Any] | None = None,
) -> None:
    display_items: list[dict[str, Any]] = []
    for item in items:
        status = str(item.get("status") or "").strip().lower()
        if status in {"queued", "running", "done", "failed", "cancelled"}:
            display_items.append(item)
    if not display_items:
        return

    status_labels = {
        "queued": "排队中",
        "running": "执行中",
        "done": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
    }
    counts = {key: 0 for key in ["queued", "running", "done", "failed", "cancelled"]}
    for item in display_items:
        status = str(item.get("status") or "").strip().lower()
        if status in counts:
            counts[status] += 1
    review_needed_count = sum(
        1
        for item in display_items
        if str(item.get("status") or "").strip().lower() == "done" and item.get("quality_gate_ok") is False
    )
    display_items = sorted(display_items, key=_recent_job_sort_key)
    sla_payload = sla_summary if isinstance(sla_summary, dict) else {}
    total_latency = sla_payload.get("total_latency") if isinstance(sla_payload.get("total_latency"), dict) else {}
    stage_latency = sla_payload.get("stage_latency") if isinstance(sla_payload.get("stage_latency"), dict) else {}
    p50_sec = total_latency.get("p50_sec")
    p95_sec = total_latency.get("p95_sec")
    p50_text = f"{float(p50_sec):.0f}s" if isinstance(p50_sec, (int, float)) else "-"
    p95_text = f"{float(p95_sec):.0f}s" if isinstance(p95_sec, (int, float)) else "-"
    has_running = counts["queued"] > 0 or counts["running"] > 0

    with st.expander("任务中心（后台任务 / 成品 / 异常）", expanded=has_running):
        st.caption("用于查看后台任务、最近成品和异常任务。在途任务可直接接回，待复核成品会直接进入审核提示。")
        if review_needed_count > 0:
            st.caption(f"待复核成品 {review_needed_count} 个，已自动前置展示。")
        filter_labels = {
            "all": "全部",
            "active": "在途",
            "review_needed": "待复核",
            "exceptions": "异常",
        }
        selected_filter = st.radio(
            "任务筛选",
            options=list(filter_labels.keys()),
            format_func=lambda key: filter_labels.get(key, key),
            horizontal=True,
            key="recent_job_filter",
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("在途任务", counts["queued"] + counts["running"])
        m2.metric("最近成品", counts["done"])
        m3.metric("异常任务", counts["failed"] + counts["cancelled"])
        m4.metric("成品P50/P95", f"{p50_text} / {p95_text}")

        def _recent_to_int(v: Any, default: int = 0) -> int:
            try:
                return int(v)
            except Exception:
                return int(default)

        filtered_items = [item for item in display_items if _recent_job_matches_filter(item, selected_filter)]
        if not filtered_items:
            st.caption("当前筛选下暂无任务。")
            return

        for item in filtered_items[:6]:
            job_id = str(item.get("job_id") or "").strip()
            status = str(item.get("status") or "").strip().lower()
            title = str(item.get("topic") or "").strip() or "施工组织设计方案"
            meta_parts = [status_labels.get(status, status or "-")]
            if str(item.get("project_type") or "").strip():
                meta_parts.append(str(item.get("project_type") or "").strip())
            mode = str(item.get("generation_mode") or "").strip()
            if mode:
                meta_parts.append(GENERATION_MODE_LABELS.get(mode, mode))
            planned_pages = item.get("planned_total_pages")
            if planned_pages:
                try:
                    meta_parts.append(f"{int(planned_pages)}页")
                except Exception:
                    meta_parts.append(f"{planned_pages}页")
            ts_label = _format_ts_short(item.get("updated_at") or item.get("created_at"))
            if ts_label:
                meta_parts.append(ts_label)
            stage = str(item.get("progress_stage") or "").strip()
            stage_label = _job_stage_label(stage) if stage else ""
            stage_artifacts_dir = str(item.get("stage_artifacts_dir") or "").strip()
            auto_remediate = bool(item.get("auto_remediate", False))
            retry_rounds_planned = int(item.get("quality_gate_retry_rounds_planned") or 0)
            automation_summary = item.get("automation_summary") if isinstance(item.get("automation_summary"), dict) else {}
            sla_snapshot = _job_sla_snapshot(item.get("sla_summary") if isinstance(item.get("sla_summary"), dict) else {})
            export_artifact_hint = _job_export_artifact_hint(sla_snapshot, stage_artifacts_dir)
            variant_artifact_hint = _job_variant_artifact_hint(sla_snapshot, stage_artifacts_dir)
            terminal_focus_hint = _job_terminal_focus_hint(sla_snapshot, stage_artifacts_dir)
            failure_hint = _job_failure_hint(status, item.get("error"), stage_artifacts_dir)
            terminal_focus_hint = _job_terminal_focus_hint_for_status(status, terminal_focus_hint, failure_hint)
            recoverable = status in {"queued", "running"} or (status == "done" and bool(item.get("result_available")))
            error_text = str(item.get("error") or "").strip()
            terminal_sections = _job_terminal_summary_sections(status, sla_snapshot, terminal_focus_hint, error_text)
            terminal_info_line = _job_terminal_info_line(status, failure_hint)
            with st.container(border=True):
                left, right = st.columns([8, 1.6], vertical_alignment="center")
                with left:
                    st.markdown(f"**{html.escape(title)}**")
                    st.caption(" · ".join(meta_parts))
                    summary_line = _recent_job_mode_quality_caption(item)
                    if summary_line:
                        st.caption(summary_line)
                    quality_signal = _recent_job_quality_signal(item) if status == "done" else {}
                    if str(quality_signal.get("level") or "") == "success":
                        st.success(str(quality_signal.get("message") or ""))
                    elif str(quality_signal.get("level") or "") == "warning":
                        st.warning(str(quality_signal.get("message") or ""))
                    if stage and status in {"queued", "running"}:
                        detail = str(sla_snapshot.get("current_stage_detail") or "").strip()
                        if detail and detail != stage_label:
                            st.caption(f"当前阶段：{stage_label} · {detail}")
                        else:
                            st.caption(f"当前阶段：{stage_label}")
                    if status in {"queued", "running"} and str(sla_snapshot.get("total_text") or "").strip():
                        st.caption(f"累计耗时：{sla_snapshot.get('total_text')}")
                    elif status in {"done", "failed", "cancelled"} and str(sla_snapshot.get("total_text") or "").strip():
                        st.caption(f"总耗时：{sla_snapshot.get('total_text')}")
                    if status in {"done", "failed", "cancelled"}:
                        for line in terminal_sections.get("pre_warning", []):
                            st.caption(line)
                    terminal_sla_warning = _job_terminal_sla_warning(sla_snapshot, stage_latency)
                    if status in {"done", "failed", "cancelled"} and terminal_sla_warning:
                        st.warning(terminal_sla_warning)
                    if status in {"done", "failed", "cancelled"} and terminal_info_line:
                        st.info(terminal_info_line)
                    if status in {"done", "failed", "cancelled"}:
                        for line in terminal_sections.get("post_warning", []):
                            st.caption(line)
                    if status in {"queued", "running"} and variant_artifact_hint:
                        st.caption(variant_artifact_hint)
                    if status in {"queued", "running"} and export_artifact_hint:
                        st.caption(export_artifact_hint)
                    if status in {"queued", "running"} and str(sla_snapshot.get("current_stage_seconds_text") or "").strip():
                        st.caption(
                            f"当前阶段耗时：{sla_snapshot.get('current_stage_text') or stage_label or '-'} · {sla_snapshot.get('current_stage_seconds_text')}"
                        )
                    stage_latency_line = _job_stage_latency_line(sla_snapshot, stage_latency)
                    if status in {"queued", "running"} and stage_latency_line:
                        st.caption(stage_latency_line)
                    slow_warning = _job_stage_sla_warning(sla_snapshot, stage_latency)
                    if status in {"queued", "running"} and slow_warning:
                        st.warning(slow_warning)
                    if status in {"queued", "running"} and auto_remediate:
                        st.caption(
                            f"自动巡检/自动修复：已启用；计划质检重试={retry_rounds_planned}轮。"
                        )
                    runtime = item.get("agent_runtime") if isinstance(item.get("agent_runtime"), dict) else {}
                    requested_ap = _recent_to_int(runtime.get("requested_agent_parallelism") or 0, 0)
                    effective_ap = _recent_to_int(runtime.get("agent_parallelism") or 0, 0)
                    vp = _recent_to_int(runtime.get("variant_parallelism") or 0, 0)
                    reason = str(runtime.get("runtime_agent_parallelism_reason") or "").strip()
                    learning_applied = bool(runtime.get("runtime_agent_parallelism_learning_applied", False))
                    learning_reason = str(runtime.get("runtime_agent_parallelism_learning_reason") or "").strip()
                    learning_source_runs = _recent_to_int(runtime.get("runtime_agent_parallelism_learning_source_runs") or 0, 0)
                    runtime_budget_summary = item.get("runtime_budget_summary") if isinstance(item.get("runtime_budget_summary"), list) else []
                    remediation_strategy_summary = item.get("remediation_strategy_summary") if isinstance(item.get("remediation_strategy_summary"), dict) else {}
                    remediation_execution_summary = item.get("remediation_execution_summary") if isinstance(item.get("remediation_execution_summary"), dict) else {}
                    remediation_learning_summary = item.get("remediation_learning_summary") if isinstance(item.get("remediation_learning_summary"), dict) else {}
                    done_summary_lines = (
                        _job_done_summary_lines(
                            runtime,
                            automation_summary,
                            runtime_budget_summary,
                            remediation_strategy_summary,
                            remediation_execution_summary,
                            remediation_learning_summary,
                        )
                        if status == "done"
                        else []
                    )
                    done_runtime_overview = done_summary_lines[0] if done_summary_lines else ""
                    if status == "done":
                        for line in done_summary_lines:
                            st.caption(line)
                    elif effective_ap > 0 or vp > 0:
                        line = f"运行期并发：章节并行={max(1, effective_ap or requested_ap or 1)}，方案并行={max(1, vp or 1)}"
                        if requested_ap > 0 and effective_ap > 0 and requested_ap != effective_ap:
                            line += f"（请求={requested_ap}，已收敛）"
                        st.caption(line)
                    if reason and status != "done":
                        label = "收敛原因" if status == "done" else "收敛原因"
                        st.caption(f"{label}：{reason}")
                    if status == "done" and not done_runtime_overview:
                        if learning_applied and learning_reason:
                            learning_line = "运行期学习已应用"
                            if learning_source_runs > 0:
                                learning_line += f"（样本={learning_source_runs}）"
                            learning_line += f"：{learning_reason}"
                            st.caption(learning_line)
                    elif learning_applied:
                        learning_line = "运行期学习已参与并发收敛"
                        if learning_source_runs > 0:
                            learning_line += f"（样本={learning_source_runs}）"
                        if learning_reason:
                            learning_line += f"：{learning_reason}"
                        st.caption(learning_line)
                    if stage_artifacts_dir:
                        st.caption(f"阶段留痕目录：{stage_artifacts_dir}")
                with right:
                    if recoverable:
                        action_label = _recent_job_action_label(item)
                        if st.button(action_label, key=f"restore_recent_job_{job_id}", width="stretch"):
                            try:
                                _restore_recent_job(base_url, actions_key, item)
                                st.rerun()
                            except Exception as e:
                                st.error(f"恢复失败: {e}")
                    else:
                        st.caption("不可接回")
                        if status in {"failed", "cancelled"}:
                            st.caption("可参考上方参数重新发起")


def _poll_active_job(
    base_url: str,
    actions_key: str,
    poll_sec: float,
    sla_summary: dict[str, Any] | None = None,
) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        return

    js = _get_json(
        base_url,
        "/actions/job_status",
        actions_key,
        params={"job_id": job_id},
        timeout=_ui_poll_timeout_seconds(poll_sec),
    )
    job = js.get("job") or {}
    status = str(job.get("status") or "")
    stage_artifacts_dir = str(job.get("stage_artifacts_dir") or "").strip()
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    sla = job.get("sla") if isinstance(job.get("sla"), dict) else {}
    agent_runtime = job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {}
    st.session_state["active_job"]["status"] = status
    st.session_state["active_job"]["progress"] = progress
    st.session_state["active_job"]["sla"] = sla
    st.session_state["active_job"]["agent_runtime"] = agent_runtime
    st.session_state["active_job"]["stage_artifacts_dir"] = stage_artifacts_dir
    stage_latency = sla_summary.get("stage_latency") if isinstance(sla_summary, dict) and isinstance(sla_summary.get("stage_latency"), dict) else {}

    def _to_int(v: Any, default: int) -> int:
        try:
            return int(v)
        except Exception:
            return int(default)

    st.info(f"任务状态：{status}（job_id={job_id}）")
    if status in {"queued", "running"}:
        percent = _to_int(progress.get("percent") or 0, 0)
        percent = max(0, min(100, percent))
        if percent <= 0:
            percent = 3 if status == "queued" else 8

        stage = str(progress.get("stage") or status).strip() or status
        stage_label = _job_stage_label(stage)
        detail = str(progress.get("detail") or "").strip()
        sla_snapshot = _job_sla_snapshot(sla)
        variants_total = _to_int(progress.get("variants_total") or agent_runtime.get("variants_total") or active.get("variants") or 1, 1)
        variants_done = _to_int(progress.get("variants_done") or agent_runtime.get("variants_done") or 0, 0)
        line = f"{status} · {percent}% · {stage_label}"
        if detail and detail != stage_label:
            line = f"{line} · {detail}"
        _render_progress(percent, line)
        if str(sla_snapshot.get("total_text") or "").strip():
            st.caption(f"累计耗时：{sla_snapshot.get('total_text')}")
        if str(sla_snapshot.get("current_stage_seconds_text") or "").strip():
            st.caption(
                f"当前阶段耗时：{sla_snapshot.get('current_stage_text') or stage_label or '-'} · {sla_snapshot.get('current_stage_seconds_text')}"
            )
        variant_artifact_hint = _job_variant_artifact_hint(sla_snapshot, stage_artifacts_dir)
        if variant_artifact_hint:
            st.caption(variant_artifact_hint)
        export_artifact_hint = _job_export_artifact_hint(sla_snapshot, stage_artifacts_dir)
        if export_artifact_hint:
            st.caption(export_artifact_hint)
        stage_latency_line = _job_stage_latency_line(sla_snapshot, stage_latency)
        if stage_latency_line:
            st.caption(stage_latency_line)
        slow_warning = _job_stage_sla_warning(sla_snapshot, stage_latency)
        if slow_warning:
            st.warning(slow_warning)
        ap = _to_int(agent_runtime.get("agent_parallelism") or 0, 0)
        requested_ap = _to_int(agent_runtime.get("requested_agent_parallelism") or 0, 0)
        vp = _to_int(agent_runtime.get("variant_parallelism") or 0, 0)
        active_parallelism_lines = _job_active_parallelism_lines(agent_runtime, variants_done, variants_total)
        if active_parallelism_lines:
            for line in active_parallelism_lines:
                st.caption(line)
        st.caption("自动巡检/自动修复：已随本次生成任务启用，完成后会在结果区展示摘要。")
        if stage_artifacts_dir:
            st.caption(f"阶段留痕目录：{stage_artifacts_dir}")
        return

    if status == "cancelled":
        _append_log(f"任务已中止: {job_id}")
        st.warning("任务已中止")
        failure_hint = _job_failure_hint(status, job.get("error"), stage_artifacts_dir)
        info_line = _job_terminal_info_line(status, failure_hint)
        if info_line:
            st.info(info_line)
        if stage_artifacts_dir:
            st.caption(f"阶段留痕目录：{stage_artifacts_dir}")
        st.session_state["active_job"] = None
        return

    if status == "failed":
        _append_log(f"任务失败: {job.get('error')}")
        _render_progress(100, "failed · 100%")
        st.error(f"任务失败: {job.get('error')}")
        failure_hint = _job_failure_hint(status, job.get("error"), stage_artifacts_dir)
        info_line = _job_terminal_info_line(status, failure_hint)
        if info_line:
            st.info(info_line)
        if stage_artifacts_dir:
            st.caption(f"阶段留痕目录：{stage_artifacts_dir}")
        st.session_state["active_job"] = None
        return

    if status != "done":
        return

    _render_progress(100, "done · 100%")
    _append_log("任务完成，开始下载结果")
    bundle = _collect_job_result(base_url, actions_key, job_id)
    bundle["project_id"] = active.get("project_id")
    st.session_state["run_result"] = bundle
    _append_log("结果下载完成")
    st.session_state["active_job"] = None


def _review_cache_key(job_id: str, variant: int) -> str:
    return f"review_items_{job_id}_v{variant}"


def _load_review_items(base_url: str, actions_key: str, job_id: str, variant: int) -> list[dict[str, Any]]:
    resp = _get_json(
        base_url,
        "/actions/review/issues",
        actions_key,
        params={"job_id": job_id, "variant": int(variant)},
        timeout=120,
    )
    rows = resp.get("items") if isinstance(resp.get("items"), list) else []
    cleaned: list[dict[str, Any]] = []
    for it in rows:
        if not isinstance(it, dict):
            continue
        cleaned.append(
            {
                "apply": bool(it.get("apply", True)),
                "issue_id": str(it.get("issue_id") or ""),
                "title": str(it.get("title") or ""),
                "type": str(it.get("type") or ""),
                "severity": str(it.get("severity") or ""),
                "problem": str(it.get("problem") or ""),
                "suggestion": str(it.get("suggestion") or ""),
                "section_excerpt": str(it.get("section_excerpt") or ""),
                "replacement": str(it.get("replacement") or ""),
            }
        )
    st.session_state[_review_cache_key(job_id, variant)] = cleaned
    return cleaned


def _render_review_workspace(base_url: str, actions_key: str) -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return
    job_id = str(result.get("job_id") or "").strip()
    variants = int(result.get("variants") or 1)
    if not job_id:
        return

    st.subheader("问题清单审核与原文回写")
    focus_job_id = str(st.session_state.get("review_focus_job_id") or "").strip()
    focus_notice = _review_workspace_focus_notice(result, focus_job_id)
    if focus_notice:
        st.warning(focus_notice)
    c1, c2, c3 = st.columns([1, 1, 2])
    variant = c1.selectbox("审核方案", options=list(range(1, variants + 1)), format_func=lambda x: f"v{x}", key=f"review_variant_{job_id}")
    if c2.button("载入问题清单", key=f"load_review_{job_id}", width="stretch"):
        try:
            if not actions_key.strip():
                raise ValueError("Actions Key 不能为空")
            rows = _load_review_items(base_url, actions_key, job_id, int(variant))
            st.success(f"已载入 {len(rows)} 条问题")
        except Exception as e:
            st.error(f"载入失败: {e}")

    rows = st.session_state.get(_review_cache_key(job_id, int(variant))) or []
    if not rows:
        st.info("点击“载入问题清单”后可进行审核回写。")
        return

    edited = st.data_editor(
        rows,
        hide_index=True,
        width="stretch",
        key=f"review_editor_{job_id}_v{variant}",
        disabled=["issue_id", "title", "type", "severity", "problem", "suggestion", "section_excerpt"],
        column_config={
            "apply": st.column_config.CheckboxColumn("应用"),
            "issue_id": st.column_config.TextColumn("ID", width="small"),
            "title": st.column_config.TextColumn("章节", width="medium"),
            "type": st.column_config.TextColumn("类型", width="small"),
            "severity": st.column_config.TextColumn("级别", width="small"),
            "problem": st.column_config.TextColumn("问题", width="large"),
            "suggestion": st.column_config.TextColumn("自动修订建议", width="large"),
            "section_excerpt": st.column_config.TextColumn("章节摘录", width="large"),
            "replacement": st.column_config.TextColumn("替换文本（可选）", width="large"),
        },
    )

    b1, b2 = st.columns([1, 1])
    if b1.button("应用勾选项并重写文档", key=f"apply_review_{job_id}_v{variant}", type="secondary", width="stretch"):
        try:
            if not actions_key.strip():
                raise ValueError("Actions Key 不能为空")
            decisions = []
            for r in edited or []:
                if not isinstance(r, dict):
                    continue
                decisions.append(
                    {
                        "issue_id": str(r.get("issue_id") or ""),
                        "apply": bool(r.get("apply")),
                        "replacement": str(r.get("replacement") or ""),
                    }
                )
            resp = _post_json(
                base_url,
                "/actions/review/apply",
                actions_key,
                {"job_id": job_id, "variant": int(variant), "decisions": decisions, "apply_all": False},
                timeout=900,
            )
            applied = int(resp.get("applied_count") or 0)
            st.success(f"已回写 {applied} 项，正在刷新产物")
            st.session_state["run_result"] = _collect_job_result(base_url, actions_key, job_id)
            _load_review_items(base_url, actions_key, job_id, int(variant))
            st.rerun()
        except Exception as e:
            st.error(f"回写失败: {e}")

    if b2.button("一键应用全部建议", key=f"apply_all_review_{job_id}_v{variant}", width="stretch"):
        try:
            if not actions_key.strip():
                raise ValueError("Actions Key 不能为空")
            resp = _post_json(
                base_url,
                "/actions/review/apply",
                actions_key,
                {"job_id": job_id, "variant": int(variant), "apply_all": True, "decisions": []},
                timeout=900,
            )
            applied = int(resp.get("applied_count") or 0)
            st.success(f"已自动回写 {applied} 项，正在刷新产物")
            st.session_state["run_result"] = _collect_job_result(base_url, actions_key, job_id)
            _load_review_items(base_url, actions_key, job_id, int(variant))
            st.rerun()
        except Exception as e:
            st.error(f"全量回写失败: {e}")


def _render_unified_cockpit() -> None:
    """Maintenance-only system status and diagnostics."""
    try:
        from backend.zhifei_autoplan.agents.section_writer import BANNED_PHRASES
        from backend.zhifei_autoplan.labor_calculator import generate_labor_plan, get_labor_ui_options
        from backend.zhifei_autoplan.terminology_guard import (
            load_engineering_rules,
            normalize_text_terminology,
            validate_engineering_rules,
        )
    except Exception as e:
        st.error(f"系统诊断模块加载失败：{e}")
        return

    now_ts = time.time()
    cache = st.session_state.get("_dash_rules_snapshot")
    if not isinstance(cache, dict) or (now_ts - float(cache.get("ts", 0))) > 120:
        rules_report = validate_engineering_rules()
        rules_obj = load_engineering_rules(rules_report.get("path"))
        cache = {
            "ts": now_ts,
            "report": rules_report if isinstance(rules_report, dict) else {},
            "term_count": len(rules_obj.get("建筑法定术语词典") or []) if isinstance(rules_obj, dict) else 0,
            "wl_count": len(rules_obj.get("法定工种白名单") or []) if isinstance(rules_obj, dict) else 0,
        }
        st.session_state["_dash_rules_snapshot"] = cache
    rules_report = cache.get("report") if isinstance(cache.get("report"), dict) else {}
    term_count = int(cache.get("term_count") or 0)
    wl_count = int(cache.get("wl_count") or 0)

    st.markdown('<div class="zf-maint-note">仅在维护、排障、规则核对时使用。</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    provider_status = _provider_runtime_status()
    gemini_ready = bool((provider_status.get("gemini_a") or {}).get("configured"))
    openai_ready = bool((provider_status.get("text_main") or {}).get("configured"))
    with c1:
        st.metric("Gemini API", "就绪" if gemini_ready else "未配置")
    with c2:
        st.metric("OpenAI API", "就绪" if openai_ready else "未配置")
    with c3:
        st.metric("规则文件", "已加载" if rules_report.get("ok") else "异常")
    st.caption(
        f"规则源：{rules_report.get('path')} | 术语词条：{term_count} | 法定工种：{wl_count}"
    )

    with st.expander("维护工具（开发）", expanded=False):
        st.caption("普通编制无需使用。")

        st.markdown("**劳动力智能排班测算**")
        opts = get_labor_ui_options()
        d_project = str(st.session_state.get("project_type") or "").strip()
        if not d_project:
            d_project = PROJECT_TYPES[0] if PROJECT_TYPES else "房建"
        with st.form("dash_labor_form", clear_on_submit=False):
            l1, l2, l3, l4 = st.columns([2, 1.2, 1.2, 1.2])
            with l1:
                st.text_input("项目类型（诊断）", value=d_project, disabled=True)
            with l2:
                d_size = st.selectbox("项目规模", options=opts.get("sizes") or ["中型项目"], key="dash_size")
            with l3:
                d_stage = st.selectbox("施工阶段", options=opts.get("stages") or ["中期"], key="dash_stage")
            with l4:
                d_total = st.number_input("总人数", min_value=1, max_value=10000, value=120, key="dash_total")
            labor_submit = st.form_submit_button("生成劳动力计划", width="stretch")
        if labor_submit:
            res = generate_labor_plan(
                project_type=str(d_project),
                size=str(d_size),
                stage=str(d_stage),
                total_personnel=int(d_total),
            )
            if not res.get("ok"):
                st.error(f"测算失败：{res.get('error')}")
            else:
                st.dataframe(res.get("trade_rows") or [], width="stretch", hide_index=True)

        st.markdown("**术语与文风审计台**")
        with st.form("dash_audit_form", clear_on_submit=False):
            src = st.text_area(
                "草稿文本",
                value="泥瓦匠负责砌筑，塔吊司机负责吊运。在实际工程中需要注意的是，现场实际情况要加强管理。",
                height=120,
                key="dash_audit_src",
            )
            audit_submit = st.form_submit_button("触发术语与黑名单拦截", width="stretch")
        if audit_submit:
            cleaned, receipt = normalize_text_terminology(src, use_llm=False)
            hits = []
            out = cleaned
            for p in BANNED_PHRASES:
                if p in out:
                    hits.append(p)
                    out = out.replace(p, "")
            out = re.sub(r"[，,。；;、]{2,}", lambda m: m.group(0)[0], out).strip("，,。；;、 \n\t")
            a1, a2 = st.columns(2)
            with a1:
                st.code(src, language=None)
            with a2:
                st.code(out, language=None)
            details = receipt.get("details") if isinstance(receipt, dict) else []
            if isinstance(details, list) and details:
                st.table(
                    [
                        {"违规词": d.get("from"), "替换后": d.get("to"), "次数": d.get("count")}
                        for d in details
                        if isinstance(d, dict)
                    ]
                )
            if hits:
                st.warning("黑名单命中：" + "、".join(sorted(set(hits))))


def _render_advanced_maintenance_panel(base_url: str) -> None:
    """Keep maintenance tools available without disturbing the main authoring flow."""
    if not _dev_panels_enabled():
        return
    st.markdown('<div class="zf-maint-zone">', unsafe_allow_html=True)
    with st.expander("维护 / 诊断（开发）", expanded=False):
        st.caption("普通编制可完全忽略。这里只保留后台任务监控与系统诊断。")
        with st.expander("任务监控（后台）", expanded=False):
            st.caption("主流程任务提交后会自动同步；这里的刷新开关仅用于开发态观察后台任务面板。")
            rc1, rc2, rc3 = st.columns([1.2, 1.1, 1.1], vertical_alignment="bottom")
            with rc1:
                st.checkbox("实时刷新（开发）", key="auto_refresh")
            with rc2:
                st.number_input("轮询秒", min_value=1.0, max_value=20.0, step=0.5, key="_poll_sec")
            with rc3:
                if st.button("手动刷新", width="stretch", type="secondary"):
                    st.rerun()
        with st.expander("系统诊断（只读）", expanded=False):
            _render_unified_cockpit()
        with st.expander("运营管理台（只读）", expanded=False):
            _render_admin_ops_panel(base_url)
    st.markdown('</div>', unsafe_allow_html=True)


_init_state()
_apply_pending_widget_updates()
_inject_ui_style()
_inject_ui_dom_patch()

st.markdown("<div class='zf-page-title'>文档生成系统</div>", unsafe_allow_html=True)
st.markdown("<div class='zf-page-subtitle'>施工组织设计文档自动生成 · 评审标准目录驱动 · 多Agent并行编制</div>", unsafe_allow_html=True)

# 连接参数改为系统内置，不在页面展示。
base_url = str(st.session_state.get("_base_url") or os.environ.get("ZF_BACKEND_BASE_URL", "http://127.0.0.1:8010")).strip()
actions_key = str(st.session_state.get("_actions_key") or os.environ.get("ZF_ACTIONS_KEY", "zf-webui-key")).strip()
expected_system_id = str(os.environ.get("ZF_SYSTEM_ID", "docgen-system")).strip() or "docgen-system"
try:
    poll_sec = float(st.session_state.get("_poll_sec") or os.environ.get("ZF_POLL_SEC", "2.0"))
except Exception:
    poll_sec = 2.0
poll_sec = max(1.0, min(20.0, poll_sec))
st.session_state["_base_url"] = base_url
st.session_state["_actions_key"] = actions_key
st.session_state["_poll_sec"] = poll_sec
st.session_state["auto_refresh"] = bool(st.session_state.get("auto_refresh", False))

identity_ok, identity_msg = _backend_identity_check(base_url, expected_system_id)
if not identity_ok:
    st.error(
        "检测到当前 Web 页面连接到了其他系统后端，已阻断操作以避免两个系统互相影响。"
        f"\n\n{identity_msg}"
    )
    st.stop()

recent_jobs_for_recovery: list[dict[str, Any]] = []
recent_jobs_sla_summary: dict[str, Any] = {}
top_submission_flow = _get_submission_flow()
top_submission_running = bool(
    top_submission_flow
    and str(top_submission_flow.get("status") or "").strip().lower() == "running"
)
recent_jobs_for_recovery = _load_recent_jobs(base_url, actions_key, limit=8)
recent_jobs_sla_summary = _load_jobs_sla_summary(base_url, actions_key, limit=200)
if not st.session_state.get("active_job") and not top_submission_running:
    _maybe_resume_recent_job(recent_jobs_for_recovery)

st.markdown("<div class='zf-top-strip zf-form-tight'>", unsafe_allow_html=True)
with st.container(border=True):
    status_col, action_col = st.columns([8.8, 1.2], vertical_alignment="center")
    with status_col:
        active = st.session_state.get("active_job") or {}
        submission_notice = _submission_flow_notice(_get_submission_flow())
        runtime_presence = _load_runtime_presence_summary(base_url, actions_key) if not active else {}
        if active:
            st.markdown(
                f"<div class='zf-notice zf-notice-running'>任务执行中：{active.get('job_id')} · 状态：{active.get('status', 'queued')}</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"页面会自动同步后台状态，每 {poll_sec:.1f} 秒刷新一次，直到任务完成。")
        elif submission_notice and submission_notice[0] == "running":
            st.markdown(
                f"<div class='zf-notice zf-notice-running'>{html.escape(submission_notice[1])}</div>",
                unsafe_allow_html=True,
            )
        elif submission_notice and submission_notice[0] == "error":
            st.markdown(
                f"<div class='zf-notice zf-notice-error'>{html.escape(submission_notice[1])}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='zf-notice zf-notice-success'>{html.escape(str(runtime_presence.get('notice_text') or '当前无运行中任务'))}</div>",
                unsafe_allow_html=True,
            )
            detail_line = str(runtime_presence.get("detail_line") or "").strip()
            if detail_line:
                st.caption(detail_line)
    with action_col:
        if active and st.button("停止/中止任务", type="secondary", width="stretch"):
            try:
                _cancel_active_job(base_url, actions_key)
                st.rerun()
            except Exception as e:
                st.error(f"中止失败: {e}")
        elif submission_notice and submission_notice[0] == "running":
            st.caption("准备中")
st.markdown('</div>', unsafe_allow_html=True)
recent_job_flash = str(st.session_state.pop("recent_job_flash", "") or "").strip()
if recent_job_flash:
    st.info(recent_job_flash)
_render_admission_status(st.session_state.get("latest_admission"))
_render_quota_status_panel(base_url, actions_key)
_render_recent_job_recovery(base_url, actions_key, recent_jobs_for_recovery, recent_jobs_sla_summary)

outline = _current_outline()
tender_files: list[Any] = []
boq_files: list[Any] = []
drawing_files: list[Any] = []
site_photo_files: list[Any] = []

st.markdown("<div class='zf-main-columns'>", unsafe_allow_html=True)
col_left, col_right = st.columns([7, 5], gap="medium")

with col_left:
    st.markdown("<div class='zf-form-tight'>", unsafe_allow_html=True)
    st.subheader("01 资料上传")
    st.caption("主流程只保留必传资料。招标文件/答疑、工程量清单必传；图纸、标准资料、现场照片按需补充。")
    st.markdown("<div class='zf-upload-grid'>", unsafe_allow_html=True)
    row1_col1, row1_col2 = st.columns(2, gap="medium")
    with row1_col1:
        with st.container(border=True):
            st.markdown("<div class='zf-upload-card-title'>招标文件/答疑（可多选）</div>", unsafe_allow_html=True)
            st.markdown("<div class='zf-upload-card-meta'>支持：PDF / DOC / DOCX / TXT / MD</div>", unsafe_allow_html=True)
            tender_files = st.file_uploader(
                "上传招标文件/答疑",
                type=["pdf", "doc", "docx", "txt", "md"],
                accept_multiple_files=True,
                help="支持多选。",
                label_visibility="collapsed",
            )
            _render_uploaded_file_summary("招标文件/答疑", tender_files)
    with row1_col2:
        with st.container(border=True):
            st.markdown("<div class='zf-upload-card-title'>工程量清单（可多选）</div>", unsafe_allow_html=True)
            st.markdown("<div class='zf-upload-card-meta'>支持：XLSX / XLS / PDF / DOC / DOCX</div>", unsafe_allow_html=True)
            boq_files = st.file_uploader(
                "上传工程量清单",
                type=["xlsx", "xls", "pdf", "doc", "docx"],
                accept_multiple_files=True,
                help="支持多选。",
                label_visibility="collapsed",
            )
            _render_uploaded_file_summary("工程量清单", boq_files)
    row2_col1, row2_col2 = st.columns(2, gap="medium")
    with row2_col1:
        with st.container(border=True):
            st.markdown("<div class='zf-upload-card-title'>图纸/标准资料（可多选，支持DXF ASCII）</div>", unsafe_allow_html=True)
            st.markdown("<div class='zf-upload-card-meta'>支持：PDF / DOC / DOCX / XLSX / PNG / JPG / DWG / DXF</div>", unsafe_allow_html=True)
            drawing_files = st.file_uploader(
                "上传图纸/标准资料",
                type=["pdf", "doc", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "dwg", "dxf"],
                accept_multiple_files=True,
                help="支持多选。",
                label_visibility="collapsed",
            )
            _render_uploaded_file_summary("图纸/标准资料", drawing_files)
    with row2_col2:
        with st.container(border=True):
            st.markdown("<div class='zf-upload-card-title'>现场照片（可多选）</div>", unsafe_allow_html=True)
            st.markdown("<div class='zf-upload-card-meta'>支持：PNG / JPG / JPEG / WEBP / BMP / TIF / TIFF</div>", unsafe_allow_html=True)
            site_photo_files = st.file_uploader(
                "上传现场照片",
                type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
                accept_multiple_files=True,
                help="支持多选。",
                label_visibility="collapsed",
            )
            _render_uploaded_file_summary("现场照片", site_photo_files)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        f"<div class='zf-notice zf-notice-running'>已选文件：招标/答疑 {len(tender_files or [])} · 清单 {len(boq_files or [])} · 图纸资料 {len(drawing_files or [])} · 现场照片 {len(site_photo_files or [])}</div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### 03 生成约束")
        chat_hist = st.session_state.get("constraint_chat_history") or []
        if not isinstance(chat_hist, list):
            chat_hist = []
        _render_constraint_chips()

        with st.expander("快速补充要求（可选）", expanded=False):
            st.markdown("<div class='zf-constraint-chat'>", unsafe_allow_html=True)
            with st.form("constraint_chat_form", clear_on_submit=False):
                st.markdown("<div class='zf-constraint-chat-shell'>", unsafe_allow_html=True)
                chat_text = st.text_area(
                    "输入你要修改的内容",
                    key="constraint_chat_input",
                    height=156,
                    placeholder="例如：全局：严格按评审标准目录；新增：第6章必须含关键工序验收。",
                    label_visibility="collapsed",
                )
                c1, c2 = st.columns([4.2, 1], vertical_alignment="center")
                with c1:
                    st.markdown(
                        "<div class='zf-constraint-chat-note'>支持：全局：…… / 新增：…… / 删除：关键词。</div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    submitted = st.form_submit_button("应用修改", width="stretch", type="primary")
                st.markdown("</div>", unsafe_allow_html=True)
                if submitted and str(chat_text or "").strip():
                    chat_hist.append({"role": "user", "content": chat_text})
                    ack = _update_constraints_from_chat(chat_text)
                    chat_hist.append({"role": "assistant", "content": ack})
                    st.session_state["constraint_chat_history"] = chat_hist[-60:]
                    st.session_state["constraint_chat_input"] = str(chat_text or "")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("手动编辑约束（高级）", expanded=False):
            st.text_area("全局指令（生成内容必须无条件服从）", key="global_instruction_draft", height=96)
            st.text_area("编制要求（每行一条）", key="requirements_text_draft", height=126)
            c_apply, c_clear = st.columns(2)
            if c_apply.button("手动应用约束", width="stretch", type="secondary"):
                st.session_state["global_instruction"] = str(st.session_state.get("global_instruction_draft") or "")
                st.session_state["requirements_text"] = str(st.session_state.get("requirements_text_draft") or "")
                st.success("已应用生成约束")
            if c_clear.button("清空对话记录", width="stretch", type="secondary"):
                st.session_state["constraint_chat_history"] = [
                    {
                        "role": "assistant",
                        "content": "约束对话已清空。继续输入即可实时修改约束。",
                    }
                ]
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("### 04 目录编辑器")
        st.caption("目录识别优先从“技术文件评审标准 / 施工组织设计 / 详细评审标准”提取；封面、索引、目录也在这里统一编排页数。点击“一键生成”后会先固化目录与索引计划，再按该目录生成正文。")
        outline = _render_outline_editor(show_title=False)

        c_load, c_health = st.columns([1, 1])
        if c_load.button("从评审标准载入目录", width="stretch", type="secondary"):
            try:
                if not actions_key.strip():
                    raise ValueError("Actions Key 不能为空")
                if not tender_files:
                    raise ValueError("请先上传招标文件/答疑")
                tender_parse_files = list(tender_files or [])
                pid_seed = str(st.session_state.get("project_id_text") or st.session_state.get("topic_text") or "").strip()
                pid = _safe_project_id(pid_seed)
                tr = _post_files(
                    base_url,
                    "/actions/tender/parse",
                    actions_key,
                    "files",
                    tender_parse_files,
                    params={"project_id": pid},
                    timeout=900,
                )
                matrix = tr.get("matrix") or {}
                outline_source = str(matrix.get("outline_source") or "").strip()
                auto_topic, auto_pid = _apply_project_defaults_from_tender(matrix)
                auto_project_type = _detect_project_type_from_tender(matrix)
                resolved_pid = str(tr.get("project_id") or auto_pid or pid).strip()
                pending_widget_patch = False
                resolved_style, style_source = _resolve_style_for_ui_with_source(
                    None,
                    matrix.get("style") if isinstance(matrix, dict) else {},
                )
                _apply_style_to_session(resolved_style, queue_only=True)
                pending_widget_patch = True
                if auto_topic:
                    _queue_widget_update("topic_text", auto_topic)
                    pending_widget_patch = True
                if auto_pid or resolved_pid:
                    _queue_widget_update("project_id_text", auto_pid or resolved_pid)
                    pending_widget_patch = True
                if auto_project_type and auto_project_type in PROJECT_TYPES:
                    _queue_widget_update("project_type", auto_project_type)
                    pending_widget_patch = True
                if auto_topic:
                    _append_log(f"已自动识别项目主题：{auto_topic}")
                if auto_pid:
                    _append_log(f"已自动识别项目ID：{auto_pid}")
                if auto_project_type:
                    _append_log(f"已自动识别项目类型：{auto_project_type}")
                ol = matrix.get("outline") if isinstance(matrix, dict) else []
                if isinstance(ol, list) and ol:
                    parsed_outline = [str(x) for x in ol if str(x).strip()]
                    strict_outline = bool(st.session_state.get("strict_tender_outline"))
                    total_pages_target = int(st.session_state.get("total_pages_target") or 0)
                    enriched_outline, planned_pages, chart_n, front_plan = _plan_outline_pages_and_chart(
                        parsed_outline,
                        project_type=str(st.session_state.get("project_type") or ""),
                        chapter_pages=matrix.get("chapter_pages") if isinstance(matrix, dict) else {},
                        tender_matrix=matrix if isinstance(matrix, dict) else {},
                        total_pages_target=(total_pages_target if total_pages_target > 0 else None),
                        strict_outline=strict_outline,
                        cover_page_count=st.session_state.get("cover_page_count"),
                        full_index_page_count=st.session_state.get("full_index_page_count"),
                        full_index_enabled=st.session_state.get("full_index_enabled"),
                        toc_page_count=st.session_state.get("toc_page_count"),
                        front_matter_page_mode=st.session_state.get("front_matter_page_mode"),
                    )
                    _set_outline_items(enriched_outline)
                    st.session_state["chapter_page_map"] = planned_pages
                    st.session_state["outline_pages"] = [int(planned_pages.get(t) or 2) for t in enriched_outline]
                    _queue_widget_update("chart_every_n", int(chart_n))
                    scope_label = "计入总页数" if front_plan["count_mode"] == "include" else "不计入总页数"
                    _append_log(
                        f"已自动规划章页数：正文{sum(planned_pages.values())}页；成品预计{front_plan['effective_document_pages']}页"
                    )
                    _append_log(
                        f"前置页设置：封面{front_plan['cover_pages']}页，目录预留{front_plan['toc_pages']}页，当前口径={scope_label}"
                    )
                    if front_plan["full_index_pages"]:
                        _append_log(f"全文索引已启用：将在封面后插入{front_plan['full_index_pages']}页全文索引")
                    if strict_outline:
                        _append_log("目录策略：严格对标评审标准，不做自动补章")
                    else:
                        _append_log(f"目录策略：结合项目类型自动补章（共{len(enriched_outline)}章）")
                    if style_source == "tender_override":
                        _append_log("已自动应用版式：按招标文件要求覆盖")
                    else:
                        _append_log("已自动应用版式：默认22磅、上2.5cm其余2.0cm、宋体三号/四号")
                    if outline_source:
                        _append_log(f"目录来源：{outline_source}")
                    _append_log("已从评审标准载入目录")
                    if outline_source == "review_standard":
                        st.success("目录已载入（来源：评审标准）")
                    elif outline_source:
                        st.warning(f"目录已载入，但来源为：{outline_source}（不是评审标准）")
                    else:
                        st.success("目录已载入")
                    st.rerun()
                else:
                    st.warning("未提取到目录")
                    if pending_widget_patch:
                        st.rerun()
            except Exception as e:
                st.error(f"载入目录失败: {e}")

        if c_health.button("检查后端连接", width="stretch", type="secondary"):
            try:
                r = requests.get(base_url.rstrip("/") + "/health", timeout=20)
                if r.status_code < 400:
                    st.success("后端可用")
                else:
                    st.error(f"后端不可用: {r.status_code}")
            except Exception as e:
                st.error(f"连接失败: {e}")

with col_right:
    st.markdown("<div class='zf-form-tight'>", unsafe_allow_html=True)
    st.subheader("02 参数配置")
    st.caption("主流程只保留项目类型、篇幅、模式与版本选择；版式、模型和高级覆盖收在下方折叠区。")
    with st.container(border=True):
        st.markdown("**主流程参数**")
        _render_runtime_summary()
        st.markdown(
            "<div class='zf-muted-note'>默认文本主模型为 ChatGPT-5.4，次选为 Gemini3.1pro；目录默认严格对标评审标准；章节并行默认提高到 6 以缩短生成耗时。</div>",
            unsafe_allow_html=True,
        )
        st.selectbox("项目类型", options=PROJECT_TYPES, key="project_type")
        st.selectbox(
            "编制模式",
            options=GENERATION_MODE_OPTIONS,
            key="generation_mode",
            format_func=lambda x: GENERATION_MODE_LABELS.get(str(x), str(x)),
        )
        st.text_input("项目主题", key="topic_text")
        st.text_input("项目ID（自动取招标文件项目编号）", key="project_id_text")
        st.markdown("**输出控制**")
        st.multiselect("版本选择（A/B/C/D/E，可多选）", options=LOGIC_TEMPLATE_OPTIONS, key="selected_templates")
        sel_templates_now = _normalize_template_selection(st.session_state.get("selected_templates"))
        if not sel_templates_now:
            sel_templates_now = ["A"]
        st.caption(f"当前将生成 {len(sel_templates_now)} 份：{' / '.join(sel_templates_now)}")
        st.number_input("总页数目标（0=按招标）", min_value=0, max_value=2000, key="total_pages_target")
        st.caption("封面 / 索引 / 目录页数，以及是否计入总页数，已移到左侧“04 目录编辑器”中统一设置。")
        st.checkbox("目录严格对标评审标准（运行时覆盖当前目录）", key="strict_tender_outline")
        st.caption("极速：更快出稿并默认关闭图片；标准：自动按篇幅切换执行策略；稳交：优先锁定结果一致性；精编：加强修订与润色。")

    with st.expander("版式设置（默认自动）", expanded=False):
        with st.container(border=True):
            st.caption("按招标提取优先；普通编制无需展开。缺失项按系统默认值兜底。")
            st.markdown("**字体与字号**")
            p1, p2 = st.columns(2)
            with p1:
                st.selectbox("正文字体", options=["宋体", "仿宋体"], key="body_font")
                st.number_input("正文字号", min_value=9, max_value=24, key="body_size")
            with p2:
                st.selectbox("标题字体", options=["宋体", "仿宋体"], key="title_font")
                st.number_input("标题字号", min_value=10, max_value=36, key="title_size")

            st.markdown("**版式参数**")
            p3, p4 = st.columns(2)
            with p3:
                st.number_input("行距（磅）", min_value=10.0, max_value=60.0, step=0.5, key="line_spacing_pt")
                st.checkbox("章节另起新页", key="chapter_start_new_page")
            with p4:
                st.checkbox("启用图表策略", key="chart_enabled")
                st.selectbox(
                    "图表位置",
                    options=["chapter", "end"],
                    key="chart_position",
                    format_func=lambda x: "按章节插入" if x == "chapter" else "文末集中",
                )
                st.caption("自动策略：≤200页每页2图；>200页每2页2图；概况章节不插图。")

            st.markdown("**页边距（cm）**")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.number_input("上", min_value=0.5, max_value=6.0, step=0.1, key="margin_top_cm")
            with m2:
                st.number_input("右", min_value=0.5, max_value=6.0, step=0.1, key="margin_right_cm")
            with m3:
                st.number_input("下", min_value=0.5, max_value=6.0, step=0.1, key="margin_bottom_cm")
            with m4:
                st.number_input("左", min_value=0.5, max_value=6.0, step=0.1, key="margin_left_cm")
            st.checkbox("按目标页数强制填充", key="enforce_chapter_pages")
            _outline_to_chapter_pages(outline)
            if outline:
                st.caption("每章页数在左侧目录编辑器中逐章设置。")

    provider_status = _provider_runtime_status()
    enabled_summary = []
    if bool(st.session_state.get("quality_strict")):
        enabled_summary.append("质控")
    if bool(st.session_state.get("auto_remediate")):
        enabled_summary.append("自动修订")
    if bool((provider_status.get("text_backup") or {}).get("configured")):
        enabled_summary.append("文本主备")
    if bool((provider_status.get("automation") or {}).get("configured")):
        enabled_summary.append("自动化修订")
    if bool(st.session_state.get("generate_images")):
        enabled_summary.append("图像")
    if bool((provider_status.get("gemini_b") or {}).get("configured")):
        enabled_summary.append("图像备份")
    summary_text = "、".join(enabled_summary) if enabled_summary else "无"

    with st.expander("更多设置（可选）", expanded=False):
        st.caption(f"当前已启用：{summary_text}。普通编制无需展开。")
        g1, g2 = st.columns(2)
        with g1:
            with st.container(border=True):
                st.markdown("**A. 生成策略**")
                st.checkbox("严格质控", key="quality_strict")
                st.checkbox("自动修订", key="auto_remediate")
                st.selectbox("修订模式", options=["template", "llm"], key="remediate_mode")
                st.number_input("章节并行 Agent 数", min_value=1, max_value=16, key="agent_parallelism")
                st.number_input("方案并行数", min_value=1, max_value=5, key="variant_parallelism")
        with g2:
            with st.container(border=True):
                text_main_status = provider_status.get("text_main") or {}
                text_backup_status = provider_status.get("text_backup") or {}
                automation_status = provider_status.get("automation") or {}
                gemini_a_status = provider_status.get("gemini_a") or {}
                gemini_b_status = provider_status.get("gemini_b") or {}
                st.markdown("**B. 服务端 Provider 路由**")
                st.caption("主生成链改为服务端环境变量托管。前端不再持有或提交任何 API Key。")
                st.markdown(
                    f"- 文本主通道：OpenAI / {text_main_status.get('model') or PRIMARY_TEXT_MODEL} / {_provider_status_badge(bool(text_main_status.get('configured')))}"
                )
                st.caption(f"  环境变量：{text_main_status.get('env') or 'OPENAI_API_KEY_TEXT_MAIN'}")
                st.markdown(
                    f"- 文本备用：OpenAI / {text_backup_status.get('model') or PRIMARY_TEXT_MODEL} / {_provider_status_badge(bool(text_backup_status.get('configured')))}"
                )
                st.caption(f"  环境变量：{text_backup_status.get('env') or 'OPENAI_API_KEY_TEXT_BACKUP'}")
                st.markdown(
                    f"- 自动化修订：OpenAI / {automation_status.get('model') or PRIMARY_TEXT_MODEL} / {_provider_status_badge(bool(automation_status.get('configured')))}"
                )
                st.caption(f"  环境变量：{automation_status.get('env') or 'OPENAI_API_KEY_AUTOMATION'}")
                st.markdown(
                    f"- 视觉主通道：Gemini / {gemini_a_status.get('model') or 'gemini-2.5-flash-image'} / {_provider_status_badge(bool(gemini_a_status.get('configured')))}"
                )
                st.caption(f"  环境变量：{gemini_a_status.get('env') or 'GEMINI_API_KEY_A'}")
                st.markdown(
                    f"- 视觉备用：Gemini / {gemini_b_status.get('model') or 'gemini-2.5-flash-image'} / {_provider_status_badge(bool(gemini_b_status.get('configured')))}"
                )
                st.caption(f"  环境变量：{gemini_b_status.get('env') or 'GEMINI_API_KEY_B'}")
                st.checkbox("生成图片/思维导图", key="generate_images")
                st.caption("视觉任务默认由 Gemini A/B 主备承担；正文主生成固定走 OpenAI 文本链。")

        with st.container(border=True):
            st.markdown("**C. 旧前端覆盖已收口**")
            f1, f2 = st.columns(2)
            with f1:
                st.caption("前端 Provider/Key 覆盖已关闭，避免明文密钥进入页面、日志和任务落盘。")
                st.caption("文本链环境变量：")
                st.code("OPENAI_API_KEY_TEXT_MAIN\nOPENAI_API_KEY_TEXT_BACKUP\nOPENAI_API_KEY_AUTOMATION", language="bash")
            with f2:
                st.caption("Gemini 视觉链环境变量：")
                st.code("GEMINI_API_KEY_A\nGEMINI_API_KEY_B", language="bash")
            st.caption("并行说明：章节并行控制同一方案内多Agent分工；方案并行控制A/B/C/D/E多份方案并发。")

        _render_active_kg_panel(base_url, actions_key)
        _render_self_evolution_panel(base_url, actions_key)
        _render_chief_agent_panel(base_url, actions_key)

        with st.expander("结构化覆盖（高级）", expanded=False):
            st.caption("普通使用留空即可。仅在需要精确覆盖章节或项目参数时填写。")
            j1, j2 = st.columns(2, gap="medium")
            with j1:
                st.text_area(
                    "章级要求 JSON",
                    key="chapter_requirements_text",
                    height=78,
                    placeholder='{"第3章":{"must_include":["危大工程"],"target_pages":4}}',
                )
            with j2:
                st.text_area(
                    "参数覆盖 JSON",
                    key="params_override_text",
                    height=78,
                    placeholder='{"project_type":"房建","duration_days":180}',
                )

    with st.expander("样板库（辅助学习）", expanded=False):
        _render_template_library_panel(base_url, actions_key)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div class='zf-step-kicker'>05 一键生成</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='zf-muted-note'>提交后会先解析评审标准目录，再按设定页数固化目录与全文索引计划，最后按该目录启动后台并行生成正文。</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='zf-run-wrap'>", unsafe_allow_html=True)
submission_flow = _get_submission_flow()
submission_locked = bool(
    submission_flow
    and str(submission_flow.get("status") or "").strip().lower() == "running"
    and not st.session_state.get("active_job")
)
run_btn = st.button("一键生成", type="primary", width="stretch", disabled=submission_locked)
st.markdown('</div>', unsafe_allow_html=True)
if submission_locked:
    st.caption(f"检测到未完成提交，当前阶段：{_submission_flow_stage_label(submission_flow)}。系统会自动从断点继续。")

progress_holder = st.empty()
status_holder = st.empty()
log_holder = st.empty()

current_topic = (st.session_state.get("topic_text") or "施工组织设计方案").strip()
current_project_id = _safe_project_id(st.session_state.get("project_id_text") or current_topic)
current_project_type = str(st.session_state.get("project_type") or "").strip()
current_selected_templates = _normalize_template_selection(st.session_state.get("selected_templates"))
if not current_selected_templates:
    current_selected_templates = ["A"]
current_total_pages_target = int(st.session_state.get("total_pages_target") or 0)
current_generation_mode = str(st.session_state.get("generation_mode") or "standard_auto").strip()
current_submission_signature = _build_submission_signature(
    topic=current_topic,
    project_id=current_project_id,
    project_type=current_project_type,
    generation_mode=current_generation_mode,
    selected_templates=current_selected_templates,
    total_pages_target=current_total_pages_target,
    tender_files=list(tender_files or []),
    boq_files=list(boq_files or []),
    drawing_files=list(drawing_files or []),
    site_photo_files=list(site_photo_files or []),
)
existing_submission_flow = _get_submission_flow()
submission_resume_reason = ""
resume_submission_flow: dict[str, Any] | None = None
if existing_submission_flow and not st.session_state.get("active_job"):
    existing_status = str(existing_submission_flow.get("status") or "").strip().lower()
    if existing_status == "running":
        submission_resume_reason = "auto_resume"
        resume_submission_flow = existing_submission_flow
    elif run_btn and existing_status == "failed":
        if str(existing_submission_flow.get("signature") or "").strip() == current_submission_signature:
            submission_resume_reason = "retry_failed"
            resume_submission_flow = existing_submission_flow

if run_btn or submission_resume_reason == "auto_resume":
    if run_btn and submission_resume_reason != "retry_failed":
        st.session_state["run_logs"] = []
        st.session_state["run_result"] = None
        st.session_state["kg_trace_sample"] = None
        flow = _start_submission_flow(
            signature=current_submission_signature,
            topic=current_topic,
            project_id=current_project_id,
            project_type=current_project_type,
        )
        _append_log("已锁定本次提交流程；若页面重连，系统将自动从断点继续。")
    else:
        flow = dict(resume_submission_flow or {})
        if submission_resume_reason == "auto_resume":
            status_holder.info("检测到未完成提交，正在从断点继续")
            _append_log(f"检测到未完成提交，正在从“{_submission_flow_stage_label(flow)}”继续。")
            flow = _touch_submission_flow(
                flow,
                status="running",
                error=None,
                resume_count=int(flow.get("resume_count") or 0) + 1,
            )
        else:
            status_holder.info("检测到上次中断，正在继续执行")
            _append_log(f"检测到上次在“{_submission_flow_stage_label(flow)}”中断，正在继续执行。")
            flow = _touch_submission_flow(
                flow,
                status="running",
                error=None,
                retry_count=int(flow.get("retry_count") or 0) + 1,
            )

    try:
        if not actions_key.strip():
            raise ValueError("Actions Key 不能为空")

        ingested_hints = {str(x).strip() for x in (flow.get("ingested_hints") or []) if str(x).strip()}
        need_tender_files = (not bool(flow.get("tender_parsed"))) or ("tender_qa" not in ingested_hints)
        need_boq_files = (not bool(flow.get("boq_parsed"))) or ("boq" not in ingested_hints)
        if need_tender_files and not tender_files:
            raise ValueError("请至少上传 1 个招标文件/答疑")
        if need_boq_files and not boq_files:
            raise ValueError("请至少上传 1 个工程量清单文件")

        # 生成前强制同步草稿约束，避免遗漏“应用生成约束”按钮导致参数未更新。
        st.session_state["global_instruction"] = str(st.session_state.get("global_instruction_draft") or "")
        st.session_state["requirements_text"] = str(st.session_state.get("requirements_text_draft") or "")

        topic = str(flow.get("topic") or current_topic).strip() or current_topic
        project_id = _safe_project_id(str(flow.get("project_id") or current_project_id).strip() or current_project_id)
        requirements = [x.strip() for x in (st.session_state.get("requirements_text") or "").splitlines() if x.strip()]
        global_instruction = str(st.session_state.get("global_instruction") or "").strip()
        project_type = str(flow.get("project_type") or current_project_type).strip() or current_project_type
        selected_templates = list(current_selected_templates)
        variants_count = len(selected_templates)
        st.session_state["variants_value"] = variants_count
        total_pages_target_raw = int(st.session_state.get("total_pages_target") or 0)
        total_pages_target = total_pages_target_raw if total_pages_target_raw > 0 else None
        generation_mode = current_generation_mode
        outline_now = _current_outline()

        chapter_requirements = _parse_json_text("章级要求 JSON", st.session_state.get("chapter_requirements_text") or "")
        params_override = _parse_json_text("参数覆盖 JSON", st.session_state.get("params_override_text") or "")

        style = {
            "body_font": st.session_state.get("body_font"),
            "title_font": st.session_state.get("title_font"),
            "body_size": int(st.session_state.get("body_size") or 14),
            "title_size": int(st.session_state.get("title_size") or 16),
            "line_spacing_pt": float(st.session_state.get("line_spacing_pt") or 22.0),
            "margins_cm": {
                "top": float(st.session_state.get("margin_top_cm") or 2.5),
                "right": float(st.session_state.get("margin_right_cm") or 2.0),
                "bottom": float(st.session_state.get("margin_bottom_cm") or 2.0),
                "left": float(st.session_state.get("margin_left_cm") or 2.0),
            },
            "cover_page_count": max(1, int(_page_target(st.session_state.get("cover_page_count")) or FIXED_COVER_PAGES)),
            "full_index_enabled": _normalize_full_index_enabled(st.session_state.get("full_index_enabled")),
            "full_index_page_count": max(
                1,
                int(_page_target(st.session_state.get("full_index_page_count")) or DEFAULT_FULL_INDEX_PAGES),
            ),
            "chapter_start_new_page": bool(st.session_state.get("chapter_start_new_page")),
            "enforce_chapter_pages": bool(st.session_state.get("enforce_chapter_pages")),
            "toc_page_count": max(1, int(_page_target(st.session_state.get("toc_page_count")) or 2)),
            "front_matter_page_mode": _normalize_front_matter_page_mode(st.session_state.get("front_matter_page_mode")),
            "chart_policy": {
                "enabled": bool(st.session_state.get("chart_enabled")),
                "mode": str(st.session_state.get("chart_mode") or "page_density_auto"),
                "every_n_chapters": int(st.session_state.get("chart_every_n") or 2),
                "position": str(st.session_state.get("chart_position") or "chapter"),
            },
        }
        chapter_pages = _outline_to_chapter_pages(outline_now)

        pb = progress_holder.progress(0)
        status_holder.info("准备执行")

        matrix = _load_saved_tender_matrix(project_id) if bool(flow.get("tender_parsed")) else None
        if bool(flow.get("tender_parsed")) and not isinstance(matrix, dict):
            flow = _touch_submission_flow(flow, tender_parsed=False)

        if not bool(flow.get("tender_parsed")):
            flow = _touch_submission_flow(flow, stage="tender_parse", detail="解析招标文件", project_id=project_id, topic=topic, project_type=project_type)
            _append_log("步骤 1/7: 解析招标文件")
            _render_logs(log_holder)
            tender_parse_files = list(tender_files or [])
            tr = _post_files(
                base_url,
                "/actions/tender/parse",
                actions_key,
                "files",
                tender_parse_files,
                params={"project_id": project_id},
                timeout=900,
            )
            matrix = tr.get("matrix") or {}
            auto_topic, auto_pid = _apply_project_defaults_from_tender(matrix)
            auto_project_type = _detect_project_type_from_tender(matrix)
            resolved_pid = str(tr.get("project_id") or auto_pid or project_id).strip()
            project_id = _safe_project_id(resolved_pid or project_id)
            if auto_topic:
                topic = auto_topic
                _append_log(f"项目主题已自动对齐：{topic}")
            if auto_pid:
                _append_log(f"项目ID已自动对齐：{project_id}")
            if auto_project_type and auto_project_type in PROJECT_TYPES:
                project_type = auto_project_type
                _append_log(f"项目类型已自动对齐：{auto_project_type}")
            flow = _touch_submission_flow(
                flow,
                tender_parsed=True,
                project_id=project_id,
                topic=topic,
                project_type=project_type,
                detail="招标文件解析完成",
            )
        else:
            _append_log("步骤 1/7: 已复用已解析招标结果")

        matrix = matrix if isinstance(matrix, dict) else {}
        auto_topic, auto_pid = _apply_project_defaults_from_tender(matrix)
        auto_project_type = _detect_project_type_from_tender(matrix)
        resolved_pid = str(flow.get("project_id") or auto_pid or project_id).strip()
        project_id = _safe_project_id(resolved_pid or project_id)
        if auto_topic and not str(flow.get("topic") or "").strip():
            topic = auto_topic
        else:
            topic = str(flow.get("topic") or topic).strip() or topic
        if auto_project_type and auto_project_type in PROJECT_TYPES and not str(flow.get("project_type") or "").strip():
            project_type = auto_project_type
        else:
            project_type = str(flow.get("project_type") or project_type).strip() or project_type

        # 版式自动设置：招标明确要求 > 当前输入 > 系统默认值。
        style, style_source = _resolve_style_for_ui_with_source(
            style,
            matrix.get("style") if isinstance(matrix, dict) else {},
        )
        if style_source == "tender_override":
            _append_log("版式已按招标要求自动覆盖（行距/边距/字体字号）")
        else:
            _append_log("招标未给出版式硬约束，已采用默认版式（22磅、上2.5cm其余2.0cm、宋体三号/四号）")

        auto_outline = matrix.get("outline") if isinstance(matrix, dict) else []
        parsed_outline = [str(x) for x in auto_outline if str(x).strip()] if isinstance(auto_outline, list) else []
        if bool(st.session_state.get("strict_tender_outline")) and parsed_outline:
            outline_base = parsed_outline
            _append_log("目录已按评审标准强制对标")
        elif outline_now:
            outline_base = outline_now
        else:
            outline_base = parsed_outline

        page_seed = dict(matrix.get("chapter_pages") or {}) if isinstance(matrix, dict) else {}
        for t, v in _outline_to_chapter_pages(outline_now).items():
            page_seed[t] = int(v)

        outline_now, chapter_pages_plan, chart_n, front_plan = _plan_outline_pages_and_chart(
            outline_base,
            project_type=project_type,
            chapter_pages=page_seed,
            tender_matrix=matrix if isinstance(matrix, dict) else {},
            total_pages_target=total_pages_target,
            strict_outline=bool(st.session_state.get("strict_tender_outline")),
            cover_page_count=style.get("cover_page_count"),
            full_index_page_count=style.get("full_index_page_count"),
            full_index_enabled=style.get("full_index_enabled"),
            toc_page_count=style.get("toc_page_count"),
            front_matter_page_mode=style.get("front_matter_page_mode"),
        )
        chapter_pages = dict(chapter_pages_plan)
        front_matter_outline = _build_front_matter_outline(
            outline_now,
            chapter_pages=chapter_pages,
            front_plan=front_plan,
        )
        planned_total_pages = int(sum(chapter_pages.values()) or 0)
        style["document_total_pages_target"] = int(front_plan["document_total_target"])
        style["chapter_page_budget"] = int(front_plan["chapter_page_budget"])
        style["effective_document_pages"] = int(front_plan["effective_document_pages"])
        style["cover_page_count"] = int(front_plan["cover_pages"])
        style["full_index_enabled"] = bool(front_plan.get("full_index_enabled"))
        style["full_index_page_count"] = int(front_plan.get("configured_index_pages") or DEFAULT_FULL_INDEX_PAGES)
        mode_params = _resolve_generation_mode_params(
            generation_mode=generation_mode,
            planned_total_pages=planned_total_pages,
            quality_strict=bool(st.session_state.get("quality_strict")),
            auto_remediate=bool(st.session_state.get("auto_remediate")),
            remediate_mode=str(st.session_state.get("remediate_mode") or "template"),
            agent_parallelism=int(st.session_state.get("agent_parallelism") or 4),
            variant_parallelism=int(st.session_state.get("variant_parallelism") or 1),
            generate_images=bool(st.session_state.get("generate_images")),
        )
        if bool(st.session_state.get("strict_tender_outline")):
            _append_log(f"目录严格对标评审标准：共{len(outline_now)}章（未自动补章）")
        else:
            _append_log(f"目录已结合项目类型自动补章：共{len(outline_now)}章")
        scope_label = "计入总页数" if front_plan["count_mode"] == "include" else "不计入总页数"
        _append_log(
            f"章页数已自动规划：正文{planned_total_pages}页；成品预计{front_plan['effective_document_pages']}页（上限由招标/系统策略控制）"
        )
        _append_log(
            f"前置页设置：封面{front_plan['cover_pages']}页，目录预留{front_plan['toc_pages']}页，当前口径={scope_label}"
        )
        if front_plan["full_index_pages"]:
            _append_log(f"全文索引已启用：将在封面后插入{front_plan['full_index_pages']}页全文索引")
        if front_plan["front_matter_overflow"]:
            _append_log("当前总页数目标小于前置页需求，正文已至少保留1页。")
        mode_effective_label = GENERATION_ENGINE_LABELS.get(mode_params["mode_effective"], mode_params["mode_effective"])
        _append_log(
            "编制档位已生效："
            f"{GENERATION_MODE_LABELS.get(mode_params['generation_mode'], mode_params['generation_mode'])}，"
            f"执行策略={mode_effective_label}，"
            f"章节并行={mode_params['agent_parallelism']}，方案并行={mode_params['variant_parallelism']}"
        )
        if mode_params["auto_switched"]:
            _append_log(f"标准档位已按篇幅自动切换到 {mode_effective_label}。")
        if isinstance(style.get("chart_policy"), dict):
            style["chart_policy"]["mode"] = "page_density_auto"
            style["chart_policy"]["every_n_chapters"] = int(chart_n)
        _append_log("图表策略已启用：<=200页每页2图；>200页每2页2图；项目概况章节不插图。")
        pb.progress(20)

        if bool(flow.get("boq_parsed")) and not _has_saved_boq_data(project_id):
            flow = _touch_submission_flow(flow, boq_parsed=False)
        if not bool(flow.get("boq_parsed")):
            flow = _touch_submission_flow(flow, stage="boq_parse", detail="解析工程量清单", project_id=project_id)
            _append_log("步骤 2/7: 解析工程量清单")
            _render_logs(log_holder)
            _post_files(
                base_url,
                "/actions/boq/parse",
                actions_key,
                "file",
                list(boq_files or []),
                params={"project_id": project_id},
                timeout=900,
            )
            flow = _touch_submission_flow(flow, boq_parsed=True, detail="工程量清单解析完成", project_id=project_id)
        else:
            _append_log("步骤 2/7: 已复用已解析工程量清单")
        pb.progress(35)

        ingest_groups = [
            ("招标/答疑", list(tender_files or []), "tender_qa"),
            ("工程量清单", list(boq_files or []), "boq"),
            ("图纸/标准资料", list(drawing_files or []), "drawing_standard"),
            ("现场照片", list(site_photo_files or []), "site_photo"),
        ]
        ingest_total = sum(len(g[1]) for g in ingest_groups)
        _append_log(f"步骤 3/7: 入库资料 ({ingest_total} 个文件)")
        _render_logs(log_holder)
        for group_name, group_files, source_hint in ingest_groups:
            if source_hint in ingested_hints:
                _append_log(f"  - 已复用 {group_name} 入库结果")
                continue
            if not group_files:
                if source_hint in {"tender_qa", "boq"}:
                    raise ValueError(f"{group_name} 缺失，无法继续提交")
                continue
            flow = _touch_submission_flow(flow, stage=f"ingest_{source_hint}", detail=f"入库 {group_name}", project_id=project_id)
            _append_log(f"  - 入库 {group_name}：{len(group_files)} 个")
            _ingest_docs(base_url, group_files, project_id, source_hint=source_hint)
            ingested_hints.add(source_hint)
            flow = _touch_submission_flow(flow, ingested_hints=sorted(ingested_hints), detail=f"{group_name} 已入库", project_id=project_id)
        pb.progress(50)

        if not bool(flow.get("front_matter_planned")):
            flow = _touch_submission_flow(flow, stage="front_matter_plan", detail="生成目录与索引计划", project_id=project_id)
            _append_log(f"步骤 4/7: 生成目录与索引计划（目录{front_plan['toc_pages']}页）")
            _append_log(f"  - 前置顺序：{' -> '.join(front_matter_outline.get('sequence') or [])}")
            toc_preview = list(front_matter_outline.get("toc_entries") or [])
            for entry in toc_preview[:3]:
                _append_log(
                    f"  - 目录锚点：{int(entry.get('order') or 0):02d}. {entry.get('title')} -> 第{int(entry.get('start_page') or 1)}页（约{int(entry.get('planned_pages') or 1)}页）"
                )
            if len(toc_preview) > 3:
                tail = toc_preview[-1]
                _append_log(
                    f"  - 末章锚点：{int(tail.get('order') or 0):02d}. {tail.get('title')} -> 第{int(tail.get('start_page') or 1)}页（约{int(tail.get('planned_pages') or 1)}页）"
                )
            flow = _touch_submission_flow(flow, front_matter_planned=True, detail="目录与索引计划已生成", project_id=project_id)
        else:
            _append_log("步骤 4/7: 已复用目录与索引计划")
        pb.progress(58)

        plan_payload: dict[str, Any] = {
            "outline": outline_now,
            "style": style,
            "project_type": project_type,
            "generation_mode": mode_params["generation_mode"],
            "global_instruction": global_instruction,
            "variants": int(variants_count),
            "selected_templates": selected_templates,
            "total_pages_target": int(total_pages_target or 0),
            "agent_parallelism": int(mode_params["agent_parallelism"]),
            "variant_parallelism": int(mode_params["variant_parallelism"]),
            "strict_tender_outline": bool(st.session_state.get("strict_tender_outline")),
            "chapter_requirements": chapter_requirements or {},
            "chapter_pages": chapter_pages,
            "front_matter_outline": front_matter_outline,
            "quality_strict": bool(mode_params["quality_strict"]),
            "auto_remediate": bool(mode_params["auto_remediate"]),
            "remediate_mode": str(mode_params["remediate_mode"]),
            "compare_mode": "summary",
            "compare_max_chars": int(mode_params["compare_max_chars"]),
            "compare_titles": None,
        }
        if bool(flow.get("plan_saved")) and not _has_saved_plan(project_id):
            flow = _touch_submission_flow(flow, plan_saved=False)
        if not bool(flow.get("plan_saved")):
            flow = _touch_submission_flow(flow, stage="plan_save", detail="保存计划配置", project_id=project_id)
            _append_log("步骤 5/7: 保存计划配置")
            _render_logs(log_holder)
            _post_json(base_url, "/actions/plan/save", actions_key, plan_payload, params={"project_id": project_id})
            flow = _touch_submission_flow(flow, plan_saved=True, detail="计划配置已保存", project_id=project_id)
        else:
            _append_log("步骤 5/7: 已复用已保存计划配置")
        pb.progress(66)

        generate_payload: dict[str, Any] = {
            "topic": topic,
            "project_id": project_id,
            "project_type": project_type,
            "generation_mode": mode_params["generation_mode"],
            "global_instruction": global_instruction,
            "outline": outline_now,
            "requirements": requirements,
            "variants": int(variants_count),
            "selected_templates": selected_templates,
            "total_pages_target": int(total_pages_target or 0),
            "agent_parallelism": int(mode_params["agent_parallelism"]),
            "variant_parallelism": int(mode_params["variant_parallelism"]),
            "strict_tender_outline": bool(st.session_state.get("strict_tender_outline")),
            "quality_strict": bool(mode_params["quality_strict"]),
            "auto_remediate": bool(mode_params["auto_remediate"]),
            "remediate_mode": str(mode_params["remediate_mode"]),
            "compare_mode": "summary",
            "compare_max_chars": int(mode_params["compare_max_chars"]),
            "generate_images": bool(mode_params["generate_images"]),
            "image_provider": str(st.session_state.get("image_provider") or "google"),
            "image_model": str(st.session_state.get("image_model") or "banana"),
            "style": style,
            "chapter_pages": chapter_pages,
            "chapter_requirements": chapter_requirements or {},
            "front_matter_outline": front_matter_outline,
        }
        _append_log("文本模型链：服务端路由托管（MAIN -> BACKUP -> AUTOMATION 分离）")
        if params_override:
            generate_payload["params_override"] = params_override

        if run_btn:
            kg_trace_sample = _sample_kg_trace(
                base_url,
                actions_key,
                topic=topic,
                project_id=project_id,
                requirements=requirements,
                global_instruction=global_instruction,
                outline=outline_now,
                top_k=3,
            )
            st.session_state["kg_trace_sample"] = kg_trace_sample
            if str(kg_trace_sample.get("status") or "").strip() == "error":
                _append_log("生成前 KG 证据采样失败（辅助留痕，不影响主流程）")
            else:
                _append_log(
                    f"生成前 KG 证据采样完成：query={str(kg_trace_sample.get('query') or '').strip() or '（空）'}；"
                    f"命中 {int(kg_trace_sample.get('hit_count') or 0)} 条。"
                )

        flow = _touch_submission_flow(flow, stage="generate_async", detail="启动异步生成", project_id=project_id)
        _append_log("步骤 6/7: 启动异步生成")
        _render_logs(log_holder)
        job = _post_json(base_url, "/actions/generate_async", actions_key, generate_payload, timeout=180)
        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError("生成任务未返回 job_id")
        job_status = str(job.get("status") or "queued").strip() or "queued"
        reused = bool(job.get("reused"))
        admission = job.get("admission") if isinstance(job.get("admission"), dict) else None
        st.session_state["latest_admission"] = admission
        if isinstance(st.session_state.get("kg_trace_sample"), dict):
            st.session_state["kg_trace_sample"]["job_id"] = job_id
        pb.progress(80)

        st.session_state["active_job"] = {
            "job_id": job_id,
            "status": job_status,
            "project_id": project_id,
            "variants": int(variants_count),
            "selected_templates": list(selected_templates),
            "base_url": base_url,
            "started_at": time.time(),
        }
        if reused and job_status in {"queued", "running"}:
            _append_log(f"步骤 7/7: 发现同参数在途任务，已复用 job_id={job_id}")
            status_holder.success("检测到同参数任务，已直接复用后台任务")
        elif reused and job_status == "done":
            _append_log(f"步骤 7/7: 发现同参数已完成任务，直接复用 job_id={job_id}")
            status_holder.success("检测到同参数成品，已直接复用现有结果")
        else:
            _append_log(f"步骤 7/7: 任务已排队 job_id={job_id}")
            status_holder.success("任务已提交，正在后台生成")
        _render_admission_status(admission)
        flow = _touch_submission_flow(flow, status="done", job_id=job_id, detail="后台任务已提交", project_id=project_id)
        _clear_submission_flow()
        _render_logs(log_holder)

    except Exception as e:
        status_holder.error(f"执行失败: {e}")
        _append_log(f"失败: {e}")
        flow = _touch_submission_flow(
            flow,
            status="failed",
            error=str(e),
            detail=str(e),
        )

_render_logs(log_holder)

# Poll active job and update result area
if st.session_state.get("active_job"):
    try:
        _poll_active_job(base_url, actions_key, float(poll_sec), recent_jobs_sla_summary)
        st.session_state["poll_fail_count"] = 0
    except Exception as e:
        fail_n = int(st.session_state.get("poll_fail_count") or 0) + 1
        st.session_state["poll_fail_count"] = fail_n
        _append_log(f"轮询失败: {e}")
        st.warning(f"后端暂时不可达，正在自动重连（第{fail_n}次）：{e}")

if st.session_state.get("run_result"):
    _render_downloads()
    _render_kg_trace_assist_block()
    _render_review_workspace(base_url, actions_key)
    with st.expander("JSON结果", expanded=False):
        raw = st.session_state["run_result"].get("result_json") or b"{}"
        try:
            st.json(json.loads(raw.decode("utf-8", errors="ignore")))
        except Exception:
            st.text(raw.decode("utf-8", errors="ignore"))

_render_advanced_maintenance_panel(base_url)

# Keep the main authoring page in sync with backend job progress.
# A submitted task should not look stuck at queued just because the hidden
# developer toggle is off.
if st.session_state.get("active_job"):
    time.sleep(max(1.0, float(poll_sec)))
    st.rerun()
