#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any

import requests
import streamlit as st

# Guard against low file-descriptor limits when launched from GUI contexts on macOS.
try:
    import resource  # type: ignore

    _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    _target = min(max(int(_soft), 4096), int(_hard) if int(_hard) > 0 else 4096)
    if _target > int(_soft):
        resource.setrlimit(resource.RLIMIT_NOFILE, (_target, _hard))
except Exception:
    pass


st.set_page_config(page_title="施组专家系统", page_icon="📄", layout="wide", initial_sidebar_state="collapsed")


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
    "google": "gemini-3-pro-preview",
    "openai": "gpt-5.2-pro",
    "grok": "grok-4-1-fast-reasoning",
}
GENERATION_MODE_OPTIONS = ["quality_200", "hq_speed_500"]
GENERATION_MODE_LABELS = {
    "quality_200": "模式1：品质优先（≤200页）",
    "hq_speed_500": "模式2：一键高质量加速（>500页）",
}
LOGIC_TEMPLATE_OPTIONS = ["A", "B", "C", "D", "E"]


def _latest_model_for(provider: str | None) -> str:
    return str(LATEST_TEXT_MODELS.get(str(provider or "").strip().lower()) or "")


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
        v = os.environ.get(k)
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
        v = os.environ.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _normalize_provider(raw: str | None, *, fallback: str) -> str:
    p = str(raw or "").strip().lower()
    if p in TEXT_PROVIDER_OPTIONS:
        return p
    return fallback


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
    mode = str(generation_mode or "quality_200").strip()
    qs = bool(quality_strict)
    ar = bool(auto_remediate)
    rm = str(remediate_mode or "template").strip() or "template"
    ap = max(1, min(16, int(agent_parallelism or 4)))
    vp = max(1, min(5, int(variant_parallelism or 1)))
    gi = bool(generate_images)
    compare_max_chars = 1200

    if mode == "quality_200":
        if int(planned_total_pages or 0) > 200:
            raise ValueError(f"当前为“品质优先（≤200页）”，但本次规划页数为 {planned_total_pages}。请切换到“高质量加速（>500页）”模式。")
        qs = True
        ar = True
        rm = "llm" if rm == "llm" else "template"
        vp = 1
    elif mode == "hq_speed_500":
        qs = True
        ar = True
        rm = "template"
        ap = max(6, ap)
        gi = False
        compare_max_chars = 800
    else:
        mode = "quality_200"
        qs = True
        ar = True
        vp = 1

    return {
        "generation_mode": mode,
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


def _resolve_style_for_ui(user_style: dict[str, Any] | None, tender_style: dict[str, Any] | None) -> dict[str, Any]:
    try:
        from backend.zhifei_autoplan.style_policy import resolve_style

        style, _ = resolve_style(user_style=user_style or {}, tender_style=tender_style or {})
        return style if isinstance(style, dict) else {}
    except Exception:
        return {
            "body_font": "宋体",
            "title_font": "宋体",
            "body_size": 14,
            "title_size": 16,
            "line_spacing_pt": 22.0,
            "margins_cm": {"top": 2.5, "right": 2.0, "bottom": 2.0, "left": 2.0},
            "chart_policy": {"enabled": True, "mode": "page_density_auto", "every_n_chapters": 2, "position": "chapter"},
        }


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
) -> tuple[list[str], dict[str, int], int]:
    titles = [str(x).strip() for x in (outline or []) if str(x).strip()]
    if not titles:
        return [], {}, 2
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
        planned = plan_chapter_pages(
            enriched,
            total_pages=total_limit,
            chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
        )
        chart_n = recommend_chart_every_n(enriched, planned)
        return enriched, planned, int(chart_n)
    except Exception:
        out = {}
        for t in titles:
            out[t] = int(_page_target((chapter_pages or {}).get(t)) or 2)
        return titles, out, 2


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
        params=params or {},
        files=files,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{path} 失败: {resp.status_code} {resp.text[:400]}")
    return resp.json()


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
        params=params or {},
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{path} 失败: {resp.status_code} {resp.text[:400]}")
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
        params=params or {},
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{path} 失败: {resp.status_code} {resp.text[:400]}")
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
        params={"job_id": job_id, "kind": kind, "variant": variant},
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"下载 {kind} v{variant} 失败: {resp.status_code} {resp.text[:300]}")
    return resp.content


def _ingest_docs(base_url: str, files: list[Any], project_id: str, source_hint: str | None = None) -> dict[str, Any]:
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
    params = {"project_id": project_id}
    if source_hint:
        params["source_hint"] = str(source_hint)
    resp = requests.post(base_url.rstrip("/") + "/ingest/upload", params=params, files=payload, timeout=900)
    if resp.status_code >= 400:
        raise RuntimeError(f"/ingest/upload 失败: {resp.status_code} {resp.text[:400]}")
    return resp.json()


def _append_log(message: str) -> None:
    st.session_state.setdefault("run_logs", [])
    st.session_state["run_logs"].append(f"[{_now()}] {message}")


def _render_logs(container) -> None:
    logs = st.session_state.get("run_logs", [])
    if not logs:
        container.info("等待任务开始…")
        return
    container.code("\n".join(logs[-300:]), language="text")


def _render_progress(percent: int, label: str) -> None:
    p = max(0, min(100, int(percent)))
    txt = str(label or "").strip()
    try:
        st.progress(p, text=txt)
    except TypeError:
        st.progress(p)
        if txt:
            st.caption(txt)


def _inject_ui_style() -> None:
    st.markdown(
        """
<style>
div.block-container {
  max-width: 1280px;
  padding-top: 1.2rem;
  padding-bottom: 1rem;
}
h1 {
  letter-spacing: 0.2px;
}
[data-testid="stFileUploader"] {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 12px;
  padding: 0.35rem 0.6rem 0.55rem 0.6rem;
  background: rgba(15, 23, 42, 0.25);
}
[data-testid="stFileUploaderDropzone"] {
  min-height: 88px;
  padding: 0.5rem 0.75rem;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div {
  font-size: 0.92rem;
}
[data-testid="stFileUploaderDropzone"] button {
  min-height: 2.2rem;
}
[data-testid="stExpander"] {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    env_main_provider = _normalize_provider(
        _env_first("ZF_LLM_MAIN_PROVIDER", "ZF_DEFAULT_PROVIDER"),
        fallback="google",
    )
    env_main_model = _env_first("ZF_LLM_MAIN_MODEL") or _latest_model_for(env_main_provider) or _latest_model_for("google")
    env_main_key = _env_first("ZF_LLM_MAIN_API_KEY") or _provider_key_from_env(env_main_provider)

    env_f1_provider_raw = _env_first("ZF_LLM_FALLBACK1_PROVIDER")
    env_f1_provider = _normalize_provider(env_f1_provider_raw, fallback="") if env_f1_provider_raw else ""
    env_f1_model = _env_first("ZF_LLM_FALLBACK1_MODEL") or (_latest_model_for(env_f1_provider) if env_f1_provider else "")
    env_f1_key = _env_first("ZF_LLM_FALLBACK1_API_KEY") or (_provider_key_from_env(env_f1_provider) if env_f1_provider else "")
    env_f1_enabled = bool(env_f1_provider and env_f1_model and env_f1_key)

    env_f2_provider_raw = _env_first("ZF_LLM_FALLBACK2_PROVIDER")
    env_f2_provider = _normalize_provider(env_f2_provider_raw, fallback="") if env_f2_provider_raw else ""
    env_f2_model = _env_first("ZF_LLM_FALLBACK2_MODEL") or (_latest_model_for(env_f2_provider) if env_f2_provider else "")
    env_f2_key = _env_first("ZF_LLM_FALLBACK2_API_KEY") or (_provider_key_from_env(env_f2_provider) if env_f2_provider else "")
    env_f2_enabled = bool(env_f2_provider and env_f2_model and env_f2_key)

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
        "generation_mode": "quality_200",
        "total_pages_target": 0,
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": "template",
        "agent_parallelism": 4,
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
        "auto_refresh": True,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    if PROJECT_TYPES and st.session_state.get("project_type") not in PROJECT_TYPES:
        st.session_state["project_type"] = PROJECT_TYPES[0]
    if st.session_state.get("generation_mode") not in GENERATION_MODE_OPTIONS:
        st.session_state["generation_mode"] = "quality_200"
    if st.session_state.get("provider_text") not in TEXT_PROVIDER_OPTIONS:
        st.session_state["provider_text"] = "google"
    if st.session_state.get("fallback_1_provider") not in FALLBACK_PROVIDER_OPTIONS:
        st.session_state["fallback_1_provider"] = ""
    if st.session_state.get("fallback_2_provider") not in FALLBACK_PROVIDER_OPTIONS:
        st.session_state["fallback_2_provider"] = ""
    selected_templates = _normalize_template_selection(st.session_state.get("selected_templates"))
    st.session_state["selected_templates"] = selected_templates or ["A"]
    st.session_state["variants_value"] = len(st.session_state["selected_templates"])
    legacy_main_model_map = {
        "gemini-2.0-flash": _latest_model_for("google"),
        "gemini-2.5-flash": _latest_model_for("google"),
        "gemini-3.1-pro-preview": _latest_model_for("google"),
        "gpt-4": _latest_model_for("openai"),
    }
    main_model_now = str(st.session_state.get("model_text") or "").strip()
    if not main_model_now:
        st.session_state["model_text"] = _latest_model_for(st.session_state.get("provider_text"))
    elif main_model_now in legacy_main_model_map:
        st.session_state["model_text"] = legacy_main_model_map[main_model_now]
    # 备选链默认保持空白，用户显式启用后再手工选择。
    if st.session_state.get("body_font") not in {"宋体", "仿宋体"}:
        st.session_state["body_font"] = "宋体"
    if st.session_state.get("title_font") not in {"宋体", "仿宋体"}:
        st.session_state["title_font"] = "宋体"
    valid_templates = list(TEMPLATE_LIBRARY.keys())
    if valid_templates and st.session_state.get("template_key") not in valid_templates:
        st.session_state["template_key"] = valid_templates[0]

    # UI 默认值迁移：将高级参数中的勾选项改为默认不勾选（仅迁移一次）。
    defaults_rev = "2026-02-26-high-quality-defaults"
    if st.session_state.get("_ui_defaults_rev") != defaults_rev:
        st.session_state["quality_strict"] = True
        st.session_state["auto_remediate"] = True
        st.session_state["generate_images"] = True
        st.session_state["fallback_1_enabled"] = bool(st.session_state.get("fallback_1_enabled"))
        st.session_state["fallback_2_enabled"] = bool(st.session_state.get("fallback_2_enabled"))
        st.session_state["_ui_defaults_rev"] = defaults_rev

    st.session_state.setdefault("run_logs", [])
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault("active_job", None)
    st.session_state.setdefault("chapter_page_map", {})


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
    tpl_outline = [str(x).strip() for x in (tpl.get("outline") or []) if str(x).strip()]
    if tpl_outline:
        _set_outline_items(tpl_outline)
    st.session_state["chapter_requirements_text"] = _json_pretty(tpl.get("chapter_requirements") or {})
    st.session_state["params_override_text"] = _json_pretty(tpl.get("params_override") or {})
    tpt = str(tpl.get("project_type") or template_key).strip()
    if tpt and tpt in PROJECT_TYPES:
        st.session_state["project_type"] = tpt


def _render_outline_editor() -> list[str]:
    st.markdown("#### 目录编辑器（默认按评审标准章目录，可实时改标题和顺序）")
    items = list(st.session_state.get("outline_items") or [])
    pages = list(st.session_state.get("outline_pages") or [])
    if len(pages) < len(items):
        pages += [2] * (len(items) - len(pages))
    elif len(pages) > len(items):
        pages = pages[: len(items)]

    if not items:
        st.info("目录为空。可先点击“从评审标准载入目录”，或手动新增章节。")

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
        if p2.button("↑", key=f"outline_up_{i}"):
            action = ("up", i)
        if p3.button("↓", key=f"outline_down_{i}"):
            action = ("down", i)
        if p4.button("✕", key=f"outline_del_{i}"):
            action = ("del", i)

    c_add, c_clear = st.columns([1, 1])
    if c_add.button("新增章节", use_container_width=True):
        items.append("")
        pages.append(2)
        st.session_state["outline_items"] = items
        st.session_state["outline_pages"] = pages
        _clear_outline_widget_state()
        st.rerun()
    if c_clear.button("清空目录", use_container_width=True):
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


def _render_downloads() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return

    st.subheader("结果预览与下载")
    job_id = result.get("job_id", "")
    variants = int(result.get("variants") or 1)
    st.write(f"job_id: `{job_id}`")

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
                    use_container_width=True,
                )
            if files.get("compare_docx"):
                st.download_button(
                    label=f"下载对照稿 v{i}.docx",
                    data=files["compare_docx"],
                    file_name=f"autoplan_{job_id}_compare_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_cmp_{i}",
                    use_container_width=True,
                )
            if files.get("focus_xlsx"):
                st.download_button(
                    label=f"下载问题清单+自动修订建议 v{i}.xlsx",
                    data=files["focus_xlsx"],
                    file_name=f"autoplan_{job_id}_focus_v{i}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{i}",
                    use_container_width=True,
                )
            if files.get("score_overview_xlsx"):
                st.download_button(
                    label=f"下载评分点覆盖与证据引用总览 v{i}.xlsx",
                    data=files["score_overview_xlsx"],
                    file_name=f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{i}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_score_overview_{i}",
                    use_container_width=True,
                )
            if files.get("expert_review_docx"):
                st.download_button(
                    label=f"下载专家复核提要版 v{i}.docx",
                    data=files["expert_review_docx"],
                    file_name=f"autoplan_{job_id}_专家复核提要版_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_expert_review_{i}",
                    use_container_width=True,
                )
            q = (result.get("quality_by_variant") or {}).get(i) or {}
            if q:
                st.json(q)
            runtime = (result.get("runtime_by_variant") or {}).get(i) or {}
            if runtime:
                mode = str(runtime.get("generation_mode") or "").strip() or "quality_200"
                planned = runtime.get("planned_total_pages")
                contract_ok = runtime.get("agent_contract_ok")
                risk_cnt = runtime.get("score_high_risk_count")
                st.caption(
                    f"运行模式={mode}；规划页数={planned if planned is not None else '-'}；"
                    f"Agent合同校验={'通过' if contract_ok else '未通过'}；评分高风险项={risk_cnt if risk_cnt is not None else '-'}"
                )
                stages = runtime.get("pipeline_stages") if isinstance(runtime.get("pipeline_stages"), list) else []
                if stages:
                    st.dataframe(stages, use_container_width=True, hide_index=True)


def _cancel_active_job(base_url: str, actions_key: str) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        st.warning("当前没有可中止任务")
        return
    _post_json(base_url, "/actions/job_cancel", actions_key, {"job_id": job_id}, timeout=60)
    _append_log(f"任务已请求中止: {job_id}")
    st.session_state["active_job"] = None


def _collect_job_result(base_url: str, actions_key: str, job_id: str) -> dict[str, Any]:
    raw_json = _download_bytes(base_url, actions_key, job_id, "json", 1, timeout=600)
    data = json.loads(raw_json.decode("utf-8", errors="ignore"))
    variants_data = data.get("variants") or []
    variants_n = max(1, len(variants_data))

    artifacts: dict[int, dict[str, bytes]] = {}
    quality_map: dict[int, dict[str, Any]] = {}
    runtime_map: dict[int, dict[str, Any]] = {}
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
        qc = rec.get("quality_checks") or {}
        mode_policy = rec.get("mode_policy") if isinstance(rec.get("mode_policy"), dict) else {}
        agent_contract_checks = rec.get("agent_contract_checks") if isinstance(rec.get("agent_contract_checks"), dict) else {}
        score_mapping = rec.get("score_mapping") if isinstance(rec.get("score_mapping"), dict) else {}
        runtime_map[v] = {
            "generation_mode": rec.get("generation_mode"),
            "planned_total_pages": mode_policy.get("planned_total_pages"),
            "pipeline_stages": rec.get("pipeline_stages") if isinstance(rec.get("pipeline_stages"), list) else [],
            "agent_contract_ok": agent_contract_checks.get("ok"),
            "agent_contract_error_count": agent_contract_checks.get("error_count"),
            "score_high_risk_count": ((score_mapping.get("summary") or {}).get("high_risk_item_count") if isinstance(score_mapping, dict) else None),
        }
        quality_map[v] = {
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
        }

    return {
        "job_id": job_id,
        "variants": variants_n,
        "artifacts": artifacts,
        "quality_by_variant": quality_map,
        "runtime_by_variant": runtime_map,
        "result_json": raw_json,
    }


def _poll_active_job(base_url: str, actions_key: str, poll_sec: float) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        return

    js = _get_json(base_url, "/actions/job_status", actions_key, params={"job_id": job_id}, timeout=90)
    job = js.get("job") or {}
    status = str(job.get("status") or "")
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    agent_runtime = job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {}
    st.session_state["active_job"]["status"] = status
    st.session_state["active_job"]["progress"] = progress
    st.session_state["active_job"]["agent_runtime"] = agent_runtime

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
        detail = str(progress.get("detail") or "").strip()
        variants_total = _to_int(progress.get("variants_total") or agent_runtime.get("variants_total") or active.get("variants") or 1, 1)
        variants_done = _to_int(progress.get("variants_done") or agent_runtime.get("variants_done") or 0, 0)
        line = f"{status} · {percent}% · {stage}"
        if detail:
            line = f"{line} · {detail}"
        _render_progress(percent, line)
        ap = _to_int(agent_runtime.get("agent_parallelism") or 0, 0)
        vp = _to_int(agent_runtime.get("variant_parallelism") or 0, 0)
        if ap > 0 or vp > 0:
            st.caption(
                f"多Agent并行：章节并行={max(1, ap)}，方案并行={max(1, vp)}，"
                f"完成方案={max(0, variants_done)}/{max(1, variants_total)}"
            )
        return

    if status == "cancelled":
        _append_log(f"任务已中止: {job_id}")
        st.warning("任务已中止")
        st.session_state["active_job"] = None
        return

    if status == "failed":
        _append_log(f"任务失败: {job.get('error')}")
        _render_progress(100, "failed · 100%")
        st.error(f"任务失败: {job.get('error')}")
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
    c1, c2, c3 = st.columns([1, 1, 2])
    variant = c1.selectbox("审核方案", options=list(range(1, variants + 1)), format_func=lambda x: f"v{x}", key=f"review_variant_{job_id}")
    if c2.button("载入问题清单", key=f"load_review_{job_id}", use_container_width=True):
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
        use_container_width=True,
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
    if b1.button("应用勾选项并重写文档", key=f"apply_review_{job_id}_v{variant}", type="primary", use_container_width=True):
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

    if b2.button("一键应用全部建议", key=f"apply_all_review_{job_id}_v{variant}", use_container_width=True):
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


_init_state()
_apply_pending_widget_updates()
_inject_ui_style()

st.title("施组专家系统")
st.caption("评审标准目录驱动 | 多Agent并行编制 | 全流程可追溯")

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
st.session_state["auto_refresh"] = bool(st.session_state.get("auto_refresh", True))

identity_ok, identity_msg = _backend_identity_check(base_url, expected_system_id)
if not identity_ok:
    st.error(
        "检测到当前 Web 页面连接到了其他系统后端，已阻断操作以避免两个系统互相影响。"
        f"\n\n{identity_msg}"
    )
    st.stop()

status_col, stop_col = st.columns([4, 1])
with status_col:
    active = st.session_state.get("active_job") or {}
    if active:
        st.warning(f"任务执行中：{active.get('job_id')} | 状态：{active.get('status', 'queued')}")
    else:
        st.success("当前无运行中任务")
with stop_col:
    if st.button("停止/中止任务", type="secondary", use_container_width=True):
        try:
            _cancel_active_job(base_url, actions_key)
            st.rerun()
        except Exception as e:
            st.error(f"中止失败: {e}")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("资料上传")
    st.caption("必传：招标文件/答疑、工程量清单；可选：图纸/标准资料、现场照片。")
    up1, up2 = st.columns(2)
    with up1:
        tender_files = st.file_uploader(
            "招标文件/答疑",
            type=["pdf", "doc", "docx", "txt", "md"],
            accept_multiple_files=True,
            help="支持多选。",
        )
        drawing_files = st.file_uploader(
            "图纸/标准资料（含DXF ASCII）",
            type=["pdf", "doc", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "dwg", "dxf"],
            accept_multiple_files=True,
            help="支持多选。",
        )
    with up2:
        boq_files = st.file_uploader(
            "工程量清单",
            type=["xlsx", "xls", "pdf", "doc", "docx"],
            accept_multiple_files=True,
            help="支持多选。",
        )
        site_photo_files = st.file_uploader(
            "现场照片",
            type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
            accept_multiple_files=True,
            help="支持多选。",
        )
    st.caption(
        f"已选文件：招标/答疑 {len(tender_files or [])}，清单 {len(boq_files or [])}，"
        f"图纸资料 {len(drawing_files or [])}，现场照片 {len(site_photo_files or [])}"
    )

with col_right:
    st.subheader("参数配置区")
    st.selectbox("项目类型", options=PROJECT_TYPES, key="project_type")
    st.selectbox(
        "编制模式",
        options=GENERATION_MODE_OPTIONS,
        key="generation_mode",
        format_func=lambda x: GENERATION_MODE_LABELS.get(str(x), str(x)),
    )
    st.text_input("项目主题", key="topic_text")
    st.text_input("项目ID（自动取招标文件项目编号）", key="project_id_text")
    st.multiselect("版本选择（A/B/C/D/E，可多选）", options=LOGIC_TEMPLATE_OPTIONS, key="selected_templates")
    sel_templates_now = _normalize_template_selection(st.session_state.get("selected_templates"))
    if not sel_templates_now:
        st.session_state["selected_templates"] = ["A"]
        sel_templates_now = ["A"]
    st.caption(f"当前将生成 {len(sel_templates_now)} 份：{' / '.join(sel_templates_now)}")
    st.number_input("总页数目标（0=按招标）", min_value=0, max_value=2000, key="total_pages_target")
    st.checkbox("目录严格对标评审标准（运行时覆盖当前目录）", key="strict_tender_outline")
    st.caption("模式规则：模式1用于200页内质量优先；模式2用于500页以上高质量加速。")

    st.text_area("全局指令（生成内容必须无条件服从）", key="global_instruction", height=90)
    st.text_area("编制要求（每行一条）", key="requirements_text", height=120)

outline = _render_outline_editor()

# Optional tender-outline loader
c_load, c_health = st.columns([1, 1])
if c_load.button("从评审标准载入目录", use_container_width=True):
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
        resolved_pid = str(tr.get("project_id") or auto_pid or pid).strip()
        pending_widget_patch = False
        # 版式自动策略：招标明确要求优先；无明确要求回落到系统默认值。
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
        if auto_topic:
            _append_log(f"已自动识别项目主题：{auto_topic}")
        if auto_pid:
            _append_log(f"已自动识别项目ID：{auto_pid}")
        ol = matrix.get("outline") if isinstance(matrix, dict) else []
        if isinstance(ol, list) and ol:
            parsed_outline = [str(x) for x in ol if str(x).strip()]
            strict_outline = bool(st.session_state.get("strict_tender_outline"))
            total_pages_target = int(st.session_state.get("total_pages_target") or 0)
            enriched_outline, planned_pages, chart_n = _plan_outline_pages_and_chart(
                parsed_outline,
                project_type=str(st.session_state.get("project_type") or ""),
                chapter_pages=matrix.get("chapter_pages") if isinstance(matrix, dict) else {},
                tender_matrix=matrix if isinstance(matrix, dict) else {},
                total_pages_target=(total_pages_target if total_pages_target > 0 else None),
                strict_outline=strict_outline,
            )
            _set_outline_items(enriched_outline)
            st.session_state["chapter_page_map"] = planned_pages
            st.session_state["outline_pages"] = [int(planned_pages.get(t) or 2) for t in enriched_outline]
            _queue_widget_update("chart_every_n", int(chart_n))
            _append_log(f"已自动规划章页数：总计{sum(planned_pages.values())}页（上限由招标/系统策略控制）")
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

if c_health.button("检查后端连接", use_container_width=True):
    try:
        r = requests.get(base_url.rstrip("/") + "/health", timeout=20)
        if r.status_code < 400:
            st.success("后端可用")
        else:
            st.error(f"后端不可用: {r.status_code}")
    except Exception as e:
        st.error(f"连接失败: {e}")

with st.expander("精细化排版渲染引擎", expanded=True):
    st.markdown("**排版参数**")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.selectbox("正文字体", options=["宋体", "仿宋体"], key="body_font")
    with p2:
        st.number_input("正文字号", min_value=9, max_value=24, key="body_size")
    with p3:
        st.selectbox("标题字体", options=["宋体", "仿宋体"], key="title_font")
    with p4:
        st.number_input("标题字号", min_value=10, max_value=36, key="title_size")

    p5, p6, p7 = st.columns([2, 1, 2])
    with p5:
        st.number_input("行距（磅）", min_value=10.0, max_value=60.0, step=0.5, key="line_spacing_pt")
    with p6:
        st.checkbox("章节另起新页", key="chapter_start_new_page")
    with p7:
        st.checkbox("启用图表策略", key="chart_enabled")
        st.caption("自动策略：总页数<=200时每页2图；>200时每2页2图；“项目概况/工程概况”章节自动排除。")
        st.selectbox("图表位置", options=["chapter", "end"], key="chart_position", format_func=lambda x: "按章节插入" if x == "chapter" else "文末集中")

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
        st.caption("每章页数请在“目录编辑器”中逐章设置（新增章节后可直接设置）。")

with st.expander("高级参数（可选）", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.checkbox("严格质控", key="quality_strict")
        st.checkbox("自动修订", key="auto_remediate")
        st.selectbox("修订模式", options=["template", "llm"], key="remediate_mode")
        st.number_input("章节并行 Agent 数", min_value=1, max_value=16, key="agent_parallelism")
    with c2:
        st.checkbox("生成图片/思维导图", key="generate_images")
        st.text_input("图片模型提供商", key="image_provider")
        st.text_input("图片模型", key="image_model")
        st.number_input("方案并行数", min_value=1, max_value=5, key="variant_parallelism")
    with c3:
        st.selectbox("主文本模型提供商", options=TEXT_PROVIDER_OPTIONS, key="provider_text")
        st.text_input("主文本模型", key="model_text")
        main_latest = _latest_model_for(st.session_state.get("provider_text"))
        if main_latest:
            st.caption(f"建议最新模型：{main_latest}")
        st.text_input("主文本模型 API Key", key="api_key_text", type="password")
    st.caption("并行说明：章节并行控制同一方案内的多Agent分工；方案并行控制A/B/C/D/E多份方案是否同时生成。")

    st.markdown("**文本模型备选链（主模型失败时自动切换）**")
    f1, f2 = st.columns(2)
    with f1:
        st.checkbox("启用备选1", key="fallback_1_enabled")
        st.selectbox(
            "备选1提供商",
            options=FALLBACK_PROVIDER_OPTIONS,
            key="fallback_1_provider",
            format_func=lambda x: "（不选择）" if str(x or "") == "" else str(x),
        )
        st.text_input("备选1模型", key="fallback_1_model")
        f1_latest = _latest_model_for(st.session_state.get("fallback_1_provider"))
        if f1_latest:
            st.caption(f"备选1建议：{f1_latest}")
        st.text_input("备选1 API Key（可留空走环境变量）", key="fallback_1_api_key", type="password")
    with f2:
        st.checkbox("启用备选2", key="fallback_2_enabled")
        st.selectbox(
            "备选2提供商",
            options=FALLBACK_PROVIDER_OPTIONS,
            key="fallback_2_provider",
            format_func=lambda x: "（不选择）" if str(x or "") == "" else str(x),
        )
        st.text_input("备选2模型", key="fallback_2_model")
        f2_latest = _latest_model_for(st.session_state.get("fallback_2_provider"))
        if f2_latest:
            st.caption(f"备选2建议：{f2_latest}")
        st.text_input("备选2 API Key（可留空走环境变量）", key="fallback_2_api_key", type="password")

    st.text_area("章级要求 JSON（可选）", key="chapter_requirements_text", height=100)
    st.text_area("参数覆盖 JSON（可选）", key="params_override_text", height=100)

run_btn = st.button("一键生成", type="primary", use_container_width=True)

progress_holder = st.empty()
status_holder = st.empty()
log_holder = st.empty()

if run_btn:
    st.session_state["run_logs"] = []
    st.session_state["run_result"] = None

    try:
        if not actions_key.strip():
            raise ValueError("Actions Key 不能为空")
        if not tender_files:
            raise ValueError("请至少上传 1 个招标文件/答疑")
        if not boq_files:
            raise ValueError("请至少上传 1 个工程量清单文件")

        topic = (st.session_state.get("topic_text") or "施工组织设计方案").strip()
        project_id = _safe_project_id(st.session_state.get("project_id_text") or topic)
        requirements = [x.strip() for x in (st.session_state.get("requirements_text") or "").splitlines() if x.strip()]
        global_instruction = str(st.session_state.get("global_instruction") or "").strip()
        project_type = str(st.session_state.get("project_type") or "").strip()
        selected_templates = _normalize_template_selection(st.session_state.get("selected_templates"))
        if not selected_templates:
            selected_templates = ["A"]
        variants_count = len(selected_templates)
        st.session_state["selected_templates"] = selected_templates
        st.session_state["variants_value"] = variants_count
        total_pages_target_raw = int(st.session_state.get("total_pages_target") or 0)
        total_pages_target = total_pages_target_raw if total_pages_target_raw > 0 else None
        generation_mode = str(st.session_state.get("generation_mode") or "quality_200").strip()
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
            "chapter_start_new_page": bool(st.session_state.get("chapter_start_new_page")),
            "enforce_chapter_pages": bool(st.session_state.get("enforce_chapter_pages")),
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

        _append_log("步骤 1/6: 解析招标文件")
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
        resolved_pid = str(tr.get("project_id") or auto_pid or project_id).strip()
        project_id = _safe_project_id(resolved_pid or project_id)
        if auto_topic:
            topic = auto_topic
            _append_log(f"项目主题已自动对齐：{topic}")
        if auto_pid:
            _append_log(f"项目ID已自动对齐：{project_id}")

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

        outline_now, chapter_pages_plan, chart_n = _plan_outline_pages_and_chart(
            outline_base,
            project_type=project_type,
            chapter_pages=page_seed,
            tender_matrix=matrix if isinstance(matrix, dict) else {},
            total_pages_target=total_pages_target,
            strict_outline=bool(st.session_state.get("strict_tender_outline")),
        )
        chapter_pages = dict(chapter_pages_plan)
        planned_total_pages = int(sum(chapter_pages.values()) or 0)
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
        if mode_params["generation_mode"] == "hq_speed_500" and planned_total_pages <= 500:
            _append_log(f"已选择高质量加速模式，但当前规划页数为 {planned_total_pages} 页（<=500）。仍按加速参数执行。")
        if bool(st.session_state.get("strict_tender_outline")):
            _append_log(f"目录严格对标评审标准：共{len(outline_now)}章（未自动补章）")
        else:
            _append_log(f"目录已结合项目类型自动补章：共{len(outline_now)}章")
        _append_log(f"章页数已自动规划：总计{planned_total_pages}页（上限由招标/系统策略控制）")
        _append_log(
            "编制模式已生效："
            f"{GENERATION_MODE_LABELS.get(mode_params['generation_mode'], mode_params['generation_mode'])}，"
            f"章节并行={mode_params['agent_parallelism']}，方案并行={mode_params['variant_parallelism']}"
        )
        if isinstance(style.get("chart_policy"), dict):
            style["chart_policy"]["mode"] = "page_density_auto"
            style["chart_policy"]["every_n_chapters"] = int(chart_n)
        _append_log("图表策略已启用：<=200页每页2图；>200页每2页2图；项目概况章节不插图。")
        pb.progress(20)

        _append_log("步骤 2/6: 解析工程量清单")
        _render_logs(log_holder)
        _post_files(
            base_url,
            "/actions/boq/parse",
            actions_key,
            "file",
            list(boq_files),
            params={"project_id": project_id},
            timeout=900,
        )
        pb.progress(35)

        ingest_groups = [
            ("招标/答疑", list(tender_files or []), "tender_qa"),
            ("工程量清单", list(boq_files or []), "boq"),
            ("图纸/标准资料", list(drawing_files or []), "drawing_standard"),
            ("现场照片", list(site_photo_files or []), "site_photo"),
        ]
        ingest_total = sum(len(g[1]) for g in ingest_groups)
        _append_log(f"步骤 3/6: 入库资料 ({ingest_total} 个文件)")
        _render_logs(log_holder)
        for group_name, group_files, source_hint in ingest_groups:
            if not group_files:
                continue
            _append_log(f"  - 入库 {group_name}：{len(group_files)} 个")
            _ingest_docs(base_url, group_files, project_id, source_hint=source_hint)
        pb.progress(50)

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
            "quality_strict": bool(mode_params["quality_strict"]),
            "auto_remediate": bool(mode_params["auto_remediate"]),
            "remediate_mode": str(mode_params["remediate_mode"]),
            "compare_mode": "summary",
            "compare_max_chars": int(mode_params["compare_max_chars"]),
            "compare_titles": None,
        }
        _append_log("步骤 4/6: 保存计划配置")
        _render_logs(log_holder)
        _post_json(base_url, "/actions/plan/save", actions_key, plan_payload, params={"project_id": project_id})
        pb.progress(62)

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
        }
        provider_chain_payload: list[dict[str, str]] = []
        provider_chain_labels: list[str] = []
        provider_chain_legacy: list[str] = []
        model_map: dict[str, str] = {}
        api_keys_map: dict[str, str] = {}

        def _append_provider(slot: str, pv: str, md: str, ak: str) -> None:
            p = str(pv or "").strip().lower()
            m = str(md or "").strip()
            k = str(ak or "").strip()
            if not p or not m:
                return
            provider_chain_payload.append(
                {
                    "slot": str(slot or "").strip() or f"slot_{len(provider_chain_payload) + 1}",
                    "provider": p,
                    "model": m,
                    "api_key": k,
                }
            )
            provider_chain_labels.append(f"{slot}:{p}")
            provider_chain_legacy.append(p)
            if p not in model_map:
                model_map[p] = m
            if p not in api_keys_map and k:
                api_keys_map[p] = k
            if k:
                api_keys_map[str(slot or "").strip() or p] = k

        _append_provider(
            "main",
            str(st.session_state.get("provider_text") or ""),
            str(st.session_state.get("model_text") or ""),
            str(st.session_state.get("api_key_text") or ""),
        )
        if bool(st.session_state.get("fallback_1_enabled")):
            _append_provider(
                "fallback_1",
                str(st.session_state.get("fallback_1_provider") or ""),
                str(st.session_state.get("fallback_1_model") or ""),
                str(st.session_state.get("fallback_1_api_key") or ""),
            )
        if bool(st.session_state.get("fallback_2_enabled")):
            _append_provider(
                "fallback_2",
                str(st.session_state.get("fallback_2_provider") or ""),
                str(st.session_state.get("fallback_2_model") or ""),
                str(st.session_state.get("fallback_2_api_key") or ""),
            )

        if provider_chain_payload:
            primary_provider = str(provider_chain_payload[0].get("provider") or "").strip().lower()
            generate_payload["provider"] = primary_provider
            generate_payload["model"] = str(provider_chain_payload[0].get("model") or "").strip()
            generate_payload["provider_chain"] = provider_chain_payload
            # Back-end 按 providers 顺序执行章节级轮询重试（主 + 备选）。
            if len(provider_chain_legacy) > 1:
                generate_payload["providers"] = provider_chain_legacy
                generate_payload["model_map"] = model_map
            if primary_provider in api_keys_map and api_keys_map[primary_provider]:
                generate_payload["api_key"] = api_keys_map[primary_provider]
            if api_keys_map:
                generate_payload["api_keys"] = api_keys_map
            _append_log(f"文本模型链：{' -> '.join(provider_chain_labels)}")
        if params_override:
            generate_payload["params_override"] = params_override

        _append_log("步骤 5/6: 启动异步生成")
        _render_logs(log_holder)
        job = _post_json(base_url, "/actions/generate_async", actions_key, generate_payload, timeout=180)
        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError("生成任务未返回 job_id")
        pb.progress(75)

        st.session_state["active_job"] = {
            "job_id": job_id,
            "status": "queued",
            "project_id": project_id,
            "variants": int(variants_count),
            "selected_templates": list(selected_templates),
            "base_url": base_url,
            "started_at": time.time(),
        }
        _append_log(f"步骤 6/6: 任务已排队 job_id={job_id}")
        _render_logs(log_holder)
        status_holder.success("任务已提交，正在后台生成")

    except Exception as e:
        status_holder.error(f"执行失败: {e}")
        _append_log(f"失败: {e}")

_render_logs(log_holder)

# Poll active job and update result area
if st.session_state.get("active_job"):
    try:
        _poll_active_job(base_url, actions_key, float(poll_sec))
        st.session_state["poll_fail_count"] = 0
    except Exception as e:
        fail_n = int(st.session_state.get("poll_fail_count") or 0) + 1
        st.session_state["poll_fail_count"] = fail_n
        _append_log(f"轮询失败: {e}")
        st.warning(f"后端暂时不可达，正在自动重连（第{fail_n}次）：{e}")

if st.session_state.get("run_result"):
    _render_downloads()
    _render_review_workspace(base_url, actions_key)
    with st.expander("JSON结果", expanded=False):
        raw = st.session_state["run_result"].get("result_json") or b"{}"
        try:
            st.json(json.loads(raw.decode("utf-8", errors="ignore")))
        except Exception:
            st.text(raw.decode("utf-8", errors="ignore"))

# lightweight auto-refresh for real-time progress
if st.session_state.get("active_job") and st.session_state.get("auto_refresh"):
    time.sleep(max(1.0, float(poll_sec)))
    st.rerun()
