#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
from datetime import datetime
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components
from requests_toolbelt.multipart.encoder import MultipartEncoder

from backend.zhifei_autoplan.compliance_policy import (
    DEFAULT_GLOBAL_INSTRUCTION,
    should_migrate_global_instruction,
)
from backend.zhifei_autoplan.job_activity import build_job_activity
from backend.zhifei_autoplan.local_env import load_local_env
from backend.zhifei_autoplan.ui_theme import (
    EXPERT_SYSTEM_CSS,
    activity_html,
    hero_html,
    launch_html,
    section_heading_html,
    workflow_html,
)


load_local_env()

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


_PAGE_LANGUAGE_GUARD_HTML = """
<!doctype html>
<html lang="zh-CN" translate="no" class="notranslate">
<head><meta name="google" content="notranslate"></head>
<body>
<script>
(() => {
  "use strict";
  try {
    const parentDocument = window.parent.document;
    const root = parentDocument.documentElement;
    root.setAttribute("lang", "zh-CN");
    root.setAttribute("translate", "no");
    root.classList.add("notranslate");

    if (!parentDocument.head.querySelector('meta[name="google"][content="notranslate"]')) {
      const meta = parentDocument.createElement("meta");
      meta.setAttribute("name", "google");
      meta.setAttribute("content", "notranslate");
      parentDocument.head.appendChild(meta);
    }
  } catch (error) {
    console.warn("Page language guard could not access the parent document.", error);
  }
})();
</script>
</body>
</html>
"""


def _inject_page_language_guard() -> None:
    """Keep this Chinese UI and its canonical A-E labels out of page translation."""

    components.html(
        _PAGE_LANGUAGE_GUARD_HTML,
        height=0,
        scrolling=False,
        tab_index=-1,
    )


_inject_page_language_guard()


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
    "google": "gemini-3.1-pro-preview",
    "openai": "gpt-5.6-sol",
    "anthropic": "claude-opus-5",
    "grok": "grok-4-1-fast-reasoning",
    "deepseek": "deepseek-v4-pro",
}
GENERATION_MODE_OPTIONS = ["quality_200", "hq_speed_500"]
GENERATION_MODE_LABELS = {
    "quality_200": "模式1：品质优先（≤200页）",
    "hq_speed_500": "模式2：一键高质量加速（>500页）",
}
LOGIC_TEMPLATE_OPTIONS = ["A", "B", "C", "D", "E"]


def _latest_model_for(provider: str | None) -> str:
    normalized = str(provider or "").strip().lower()
    env_map = {
        "google": ("GEMINI_TEXT_MODEL", "ZF_GOOGLE_TEXT_MODEL_ID"),
        "openai": ("OPENAI_TEXT_MODEL_MAIN", "ZF_OPENAI_TEXT_MODEL_ID"),
        "anthropic": ("ANTHROPIC_TEXT_MODEL_MAIN", "ZF_ANTHROPIC_TEXT_MODEL_ID"),
        "deepseek": ("DEEPSEEK_TEXT_MODEL", "ZF_DEEPSEEK_TEXT_MODEL_ID"),
    }
    for env_name in env_map.get(normalized, ()):
        value = os.environ.get(env_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(LATEST_TEXT_MODELS.get(normalized) or "")


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


def _sync_provider_model(provider_key: str, model_key: str) -> None:
    provider = str(st.session_state.get(provider_key) or "").strip().lower()
    latest = _latest_model_for(provider)
    if latest:
        st.session_state[model_key] = latest


def _provider_status(provider: str | None) -> tuple[bool, str]:
    admission = st.session_state.get("_provider_admission")
    if not isinstance(admission, dict):
        return False, "供应商准入状态尚未取得"
    state = str(admission.get("status") or "missing")
    labels = {
        "admitted": "模型供应商已准入",
        "degraded": "模型供应商已降级准入",
        "expired": "模型供应商准入已过期，将在证据门通过后重新检查",
        "stale_route": "模型路由已变化，将在证据门通过后重新检查",
        "configured_not_admitted": "模型已配置但尚未准入",
        "missing": "模型供应商尚未形成准入回执",
    }
    return state in {"admitted", "degraded"}, labels.get(state, "模型供应商准入状态未知")


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
    line_spacing = style.get("line_spacing")
    if line_spacing is None and font_cfg:
        line_spacing = font_cfg.get("line_spacing")
    if line_spacing_pt is not None:
        _set("line_spacing_mode", "fixed_pt")
        try:
            _set("line_spacing_pt", float(line_spacing_pt))
        except Exception:
            _set("line_spacing_pt", 22.0)
    elif line_spacing is not None:
        _set("line_spacing_mode", "multiple")
        try:
            _set("line_spacing_multiple", float(line_spacing))
        except Exception:
            _set("line_spacing_multiple", 1.5)
    else:
        _set("line_spacing_mode", "fixed_pt")
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


def _stable_http_error(path: str, status_code: int, raw_text: str) -> RuntimeError:
    """Project only a stable backend error; never surface raw response text."""
    status_defaults = {
        400: ("REQUEST_REJECTED", "请求内容未通过校验。", "请核对输入资料后重试。"),
        401: ("SYSTEM_ACCESS_DENIED", "系统内部凭据无效。", "请从最新受监管版本重新打开页面。"),
        403: ("SYSTEM_ACCESS_DENIED", "当前操作未获授权。", "请核对本机运行状态后重试。"),
        404: ("SYSTEM_RESOURCE_NOT_FOUND", "请求的任务或文件不存在。", "请刷新页面并重新选择任务。"),
        409: ("SYSTEM_STATE_CONFLICT", "任务状态已经变化，本次操作未执行。", "请刷新最新状态后重试。"),
        413: ("UPLOAD_TOO_LARGE", "上传资料超过允许大小。", "请拆分文件或减少单批资料后重试。"),
        422: ("REQUEST_VALIDATION_FAILED", "请求参数不完整或格式不正确。", "请检查必填项后重试。"),
        429: ("SERVICE_RATE_LIMITED", "服务当前请求过多。", "请稍候再试。"),
    }
    default = status_defaults.get(
        int(status_code),
        (
            "BACKEND_SERVICE_UNAVAILABLE" if int(status_code) >= 500 else "REQUEST_FAILED",
            "后端服务暂时不可用。" if int(status_code) >= 500 else "请求未能完成。",
            "请检查系统运行状态后重试。",
        ),
    )
    detail: Any = None
    try:
        parsed = json.loads(str(raw_text or ""))
        detail = parsed.get("detail") if isinstance(parsed, dict) else None
        if detail is None and isinstance(parsed, dict):
            detail = parsed.get("error") or parsed
    except Exception:
        detail = None
    if isinstance(detail, dict):
        raw_code = str(detail.get("code") or "").strip().upper()
        code = raw_code if re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}", raw_code) else default[0]
        message = str(detail.get("message") or default[1]).strip()[:300]
        action = str(detail.get("action") or default[2]).strip()[:300]
    else:
        code, message, action = default
    sensitive_literal = re.compile(
        r"(?i)\b(?:bearer|sk|secret|token|key)[-_ :][A-Za-z0-9._~+/=-]{6,}"
    )
    message = sensitive_literal.sub("[已脱敏]", message)
    action = sensitive_literal.sub("[已脱敏]", action)
    return RuntimeError(f"{code}：{message} 建议：{action}（{path}，HTTP {status_code}）")


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
        raise _stable_http_error(path, resp.status_code, resp.text)
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
        raise _stable_http_error(path, resp.status_code, resp.text)
    return resp.json()


def _post_file_ids(
    base_url: str,
    path: str,
    actions_key: str,
    file_ids: list[str],
    *,
    project_id: str,
    timeout: int = 900,
) -> dict[str, Any]:
    params: list[tuple[str, str]] = [("project_id", str(project_id))]
    params.extend(("file_id", str(item)) for item in file_ids if str(item).strip())
    resp = requests.post(
        base_url.rstrip("/") + path,
        headers=_headers(actions_key),
        params=params,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise _stable_http_error(path, resp.status_code, resp.text)
    return resp.json()


def _is_stale_review_error(exc: Exception) -> bool:
    return "STALE_REVIEW_STATE" in str(exc)


def _render_review_apply_error(exc: Exception, *, prefix: str) -> None:
    if _is_stale_review_error(exc):
        st.warning("问题清单对应的文档版本已经变化，本次未写入。请重新载入问题清单后再操作。")
        return
    st.error(f"{prefix}: {exc}")


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
        raise _stable_http_error(path, resp.status_code, resp.text)
    return resp.json()


def _normalize_runtime_job_id(raw: Any) -> str:
    """Return the only job-id shape that may cross the browser URL boundary."""

    if isinstance(raw, (list, tuple)):
        raw = raw[-1] if raw else ""
    value = str(raw or "").strip().lower()
    return value if re.fullmatch(r"[0-9a-f]{32}", value) else ""


def _query_runtime_job_id() -> str:
    try:
        return _normalize_runtime_job_id(st.query_params.get("job_id"))
    except Exception:
        return ""


def _persist_active_job_query(job_id: Any) -> bool:
    """Persist only an opaque job id; credentials and request data stay server-side."""

    normalized = _normalize_runtime_job_id(job_id)
    if not normalized:
        return False
    try:
        if _query_runtime_job_id() != normalized:
            st.query_params["job_id"] = normalized
        st.session_state.pop("_active_job_query_restore_attempted", None)
        return True
    except Exception:
        return False


def _clear_active_job_query(expected_job_id: Any | None = None) -> None:
    """Clear a completed/stale URL job id without disturbing a newer one."""

    expected = _normalize_runtime_job_id(expected_job_id)
    try:
        current = _query_runtime_job_id()
        if expected and current and current != expected:
            return
        if "job_id" in st.query_params:
            del st.query_params["job_id"]
    except Exception:
        pass


def _active_job_from_snapshot(job: Any, requested_job_id: Any) -> dict[str, Any] | None:
    """Build the minimal browser state from the authenticated public snapshot."""

    if not isinstance(job, dict):
        return None
    expected = _normalize_runtime_job_id(requested_job_id)
    snapshot_id = _normalize_runtime_job_id(job.get("job_id") or job.get("run_id"))
    if not expected or snapshot_id != expected:
        return None

    status = str(job.get("status") or "").strip().lower()
    status = {
        "done": "succeeded",
        "interrupted": "interrupted_recoverable",
    }.get(status, status)
    if status not in {
        "queued",
        "running",
        "cancel_requested",
        "interrupted_recoverable",
        "failed",
        "succeeded",
    }:
        return None
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    agent_runtime = (
        job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {}
    )
    try:
        variants = max(
            1,
            min(
                5,
                int(
                    job.get("variants")
                    or progress.get("variants_total")
                    or agent_runtime.get("variants_total")
                    or 1
                ),
            ),
        )
    except (TypeError, ValueError):
        variants = 1
    try:
        started_at = float(job.get("created_at") or time.time())
    except (TypeError, ValueError):
        started_at = time.time()
    return {
        "job_id": snapshot_id,
        "status": status,
        "project_id": str(job.get("project_id") or "").strip(),
        "variants": variants,
        "started_at": started_at,
        "progress": progress,
        "agent_runtime": agent_runtime,
        "restored_from_url": True,
    }


def _restore_active_job_from_query(base_url: str, actions_key: str) -> bool:
    """Recover a refreshed Streamlit session from the authenticated job snapshot."""

    if st.session_state.get("active_job"):
        return False
    try:
        raw_job_id = st.query_params.get("job_id")
    except Exception:
        return False
    if raw_job_id in (None, "", []):
        return False
    job_id = _normalize_runtime_job_id(raw_job_id)
    if not job_id:
        _clear_active_job_query()
        return False
    if st.session_state.get("_active_job_query_restore_attempted") == job_id:
        return False
    st.session_state["_active_job_query_restore_attempted"] = job_id
    try:
        response = _get_json(
            base_url,
            "/actions/job_status",
            actions_key,
            params={"job_id": job_id},
            timeout=15,
        )
    except Exception as exc:
        # A transient outage must not permanently consume the one-session
        # recovery attempt. Keep the query id so the next refresh reconciles
        # the durable job before any new submission.
        st.session_state.pop("_active_job_query_restore_attempted", None)
        if "SYSTEM_RESOURCE_NOT_FOUND" in str(exc):
            _clear_active_job_query(job_id)
        raise
    if not isinstance(response, dict):
        _clear_active_job_query(job_id)
        return False
    active = _active_job_from_snapshot(response.get("job"), job_id)
    if active is None:
        _clear_active_job_query(job_id)
        return False
    st.session_state["active_job"] = active
    return True


def _finish_active_job(job_id: Any) -> None:
    """End browser tracking atomically enough to prevent terminal reload loops."""

    _clear_active_job_query(job_id)
    st.session_state["active_job"] = None
    st.session_state.pop("_active_job_query_restore_attempted", None)


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
        raise _stable_http_error(f"/actions/download/{kind}/v{variant}", resp.status_code, resp.text)
    return resp.content


def _uploaded_file_size(uploaded_file: Any) -> int:
    raw_size = getattr(uploaded_file, "size", None)
    if isinstance(raw_size, int) and raw_size >= 0:
        return raw_size

    original_pos = uploaded_file.tell()
    try:
        uploaded_file.seek(0, 2)
        return int(uploaded_file.tell())
    finally:
        uploaded_file.seek(original_pos)


def _ingest_docs(
    base_url: str,
    files: list[Any],
    project_id: str,
    source_hint: str | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    class _StreamingUploadReader:
        def __init__(self, source: Any, size: int) -> None:
            self._source = source
            self._size = max(0, int(size))

        @property
        def len(self) -> int:
            return max(0, self._size - int(self._source.tell()))

        def read(self, size: int = -1) -> bytes:
            return self._source.read(size)

    if not files:
        return {"saved": []}
    payload = []
    seen = set()
    for uf in files:
        file_size = _uploaded_file_size(uf)
        key = (uf.name, file_size)
        if key in seen:
            continue
        seen.add(key)
        uf.seek(0)
        content_type = mimetypes.guess_type(str(uf.name or ""))[0] or "application/octet-stream"
        payload.append(("files", (uf.name, _StreamingUploadReader(uf, file_size), content_type)))
    params = {"project_id": project_id}
    if source_hint:
        params["source_hint"] = str(source_hint)
    body = MultipartEncoder(fields=payload)
    resp = requests.post(
        base_url.rstrip("/") + "/ingest/jobs",
        params=params,
        data=body,
        headers={"Content-Type": body.content_type},
        timeout=900,
    )
    if resp.status_code >= 400:
        raise _stable_http_error("/ingest/jobs", resp.status_code, resp.text)
    created = resp.json()
    job_id = str(created.get("job_id") or "").strip()
    if not job_id:
        raise RuntimeError("/ingest/jobs 未返回 job_id")
    deadline = time.monotonic() + 20 * 60
    while time.monotonic() < deadline:
        status_response = requests.get(
            base_url.rstrip("/") + f"/ingest/jobs/{job_id}",
            timeout=30,
        )
        if status_response.status_code >= 400:
            raise _stable_http_error(
                f"/ingest/jobs/{job_id}",
                status_response.status_code,
                status_response.text,
            )
        job = status_response.json().get("job") or {}
        progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
        if callable(progress_callback):
            progress_callback(progress)
        status = str(job.get("status") or "").strip().lower()
        if status in {"succeeded", "done"}:
            result = job.get("result") if isinstance(job.get("result"), dict) else {}
            result["job_id"] = job_id
            return result
        if status in {"failed", "cancelled", "interrupted_recoverable"}:
            error = job.get("error")
            raise RuntimeError(
                json.dumps(error, ensure_ascii=False) if isinstance(error, dict) else str(error or status)
            )
        time.sleep(0.5)
    raise RuntimeError(f"资料导入任务超时: job_id={job_id}")


def _normalize_reference_text_list_ui(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[，,、;；/\s]+", str(raw or "").strip())
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _reference_top_k_state(key: str, default: int = 3) -> int:
    raw = st.session_state.get(key)
    try:
        value = int(default if raw in (None, "") else raw)
    except Exception:
        value = default
    return max(1, min(8, value))


def _build_case_library_request_options() -> dict[str, Any]:
    return {
        "enabled": bool(st.session_state.get("case_library_enabled")),
        "selected_case_ids": _normalize_reference_text_list_ui(st.session_state.get("case_library_selected_ids") or []),
        "top_k": _reference_top_k_state("case_library_top_k"),
    }


def _build_image_library_request_options() -> dict[str, Any]:
    return {
        "enabled": bool(st.session_state.get("image_library_enabled")),
        "selected_image_ids": _normalize_reference_text_list_ui(st.session_state.get("image_library_selected_ids") or []),
        "top_k": _reference_top_k_state("image_library_top_k"),
    }


def _ollama_preview_timeout_state() -> int:
    raw = st.session_state.get("ollama_preview_timeout")
    try:
        value = int(raw if raw not in (None, "") else 60)
    except Exception:
        value = 60
    return max(1, min(300, value))


def _build_ollama_preview_request_payload() -> dict[str, Any]:
    outline = _normalize_reference_text_list_ui(st.session_state.get("outline_items") or [])
    selected_templates = _normalize_reference_text_list_ui(st.session_state.get("selected_templates") or [])
    topic = str(st.session_state.get("topic_text") or "施工组织设计方案").strip() or "施工组织设计方案"
    project_type = str(st.session_state.get("project_type") or "").strip() or "-"
    generation_mode = str(st.session_state.get("generation_mode") or "").strip() or "-"
    requirements = str(st.session_state.get("requirements_text") or "").strip()
    global_instruction = str(st.session_state.get("global_instruction") or "").strip()
    preview_body = str(st.session_state.get("ollama_preview_content") or "").strip()

    lines = [
        f"项目主题：{topic}",
        f"项目类型：{project_type}",
        f"编制模式：{generation_mode}",
        f"版本选择：{' / '.join(selected_templates) if selected_templates else '-'}",
        "目录：",
        *[f"- {item}" for item in outline[:80]],
    ]
    if requirements:
        lines.extend(["编制要求：", requirements])
    if global_instruction:
        lines.extend(["全局指令：", global_instruction])
    if preview_body:
        lines.extend(["待预览正文：", preview_body])

    content = "\n".join([line for line in lines if str(line).strip()]).strip()
    instruction = str(st.session_state.get("ollama_preview_instruction") or "").strip()
    return {
        "content": content[:12000],
        "section_title": str(st.session_state.get("ollama_preview_section_title") or topic).strip() or topic,
        "instruction": instruction or "只做人工预览增强，指出缺项、风险和可人工采纳的优化建议；不要改写正文，不要生成新事实。",
        "model": str(st.session_state.get("ollama_preview_model") or "qwen3.5:4b").strip() or "qwen3.5:4b",
        "base_url": "http://127.0.0.1:11434",
        "timeout": _ollama_preview_timeout_state(),
    }


def _normalize_ollama_preview_result_ui(raw: Any) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    fallback = payload.get("fallback") if isinstance(payload.get("fallback"), dict) else {}
    status = str(payload.get("status") or ("ok" if payload.get("ok") else "fallback")).strip()
    content = str(payload.get("content") or "").strip()
    warning = str(payload.get("warning") or payload.get("error") or fallback.get("message") or "").strip()
    return {
        "ok": bool(payload.get("ok")),
        "status": status or "fallback",
        "model": str(payload.get("model") or "").strip(),
        "content": content,
        "warning": warning,
        "has_content": bool(content),
    }


def _normalize_ollama_section_review_result_ui(raw: Any) -> dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    normalized = _normalize_ollama_preview_result_ui(payload)
    normalized["review_type"] = str(payload.get("review_type") or "").strip()
    normalized["error"] = str(payload.get("error") or "").strip()
    return normalized


def _reference_item_label(item: dict[str, Any], id_key: str) -> str:
    title = str(item.get("title") or item.get("filename") or item.get(id_key) or "").strip()
    project_type = str(item.get("project_type") or "").strip()
    tags = _normalize_reference_text_list_ui(item.get("tags") or [])
    meta = [x for x in [project_type, " / ".join(tags[:3])] if x]
    return f"{title}（{'；'.join(meta)}）" if meta else title


def _render_reference_item_cards(items: list[dict[str, Any]], *, id_key: str, selected_ids: list[str]) -> None:
    selected = {str(x).strip() for x in (selected_ids or []) if str(x).strip()}
    if not items:
        st.info("暂无已录入条目。")
        return
    for item in items[:8]:
        item_id = str(item.get(id_key) or "").strip()
        title = str(item.get("title") or item.get("filename") or item_id or "未命名").strip()
        tags = " / ".join(_normalize_reference_text_list_ui(item.get("tags") or [])[:4])
        chapter_scope = " / ".join(_normalize_reference_text_list_ui(item.get("chapter_scope") or [])[:4])
        status = "已选择" if item_id and item_id in selected else "可选"
        caption_parts = [
            f"项目类型：{item.get('project_type') or '-'}",
            f"标签：{tags or '-'}",
            f"章节：{chapter_scope or '-'}",
            f"状态：{status}",
        ]
        st.caption(f"{title}  " + "；".join(caption_parts))


def _fetch_reference_items(
    base_url: str,
    actions_key: str,
    path: str,
    *,
    project_type: str,
) -> list[dict[str, Any]]:
    payload = _get_json(
        base_url,
        path,
        actions_key,
        params={"project_type": project_type, "limit": 100},
        timeout=60,
    )
    rows = payload.get("items") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _render_case_library_panel(base_url: str, actions_key: str) -> None:
    st.markdown("**案例库**")
    st.caption(
        "启用后，仅将匹配到的可用案例作为章节结构、逻辑顺序、表达风格和方法组织提示；"
        "案例不是项目事实源，不覆盖招标文件、清单、图纸、答疑、已核验规范与企业参数。"
    )
    project_type = str(st.session_state.get("case_library_project_type") or st.session_state.get("project_type") or "").strip()
    items: list[dict[str, Any]] = []
    try:
        items = _fetch_reference_items(base_url, actions_key, "/actions/case_library/items", project_type=project_type)
    except Exception as e:
        st.warning(f"案例库列表暂不可用：{e}")

    item_ids = [str(item.get("case_id") or "").strip() for item in items if str(item.get("case_id") or "").strip()]
    labels = {str(item.get("case_id") or "").strip(): _reference_item_label(item, "case_id") for item in items}
    current_selected = [x for x in _normalize_reference_text_list_ui(st.session_state.get("case_library_selected_ids") or []) if x in set(item_ids)]
    if current_selected != list(st.session_state.get("case_library_selected_ids") or []):
        st.session_state["case_library_selected_ids"] = current_selected
    has_items = bool(item_ids)
    if not has_items:
        st.session_state["case_library_enabled"] = False
        st.info("当前项目类型暂无可用案例；请先录入案例，系统不会启用空库增强。")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.checkbox(
            "生成时启用案例库安全增强",
            key="case_library_enabled",
            disabled=not has_items,
            help="只有匹配到已启用且可用的案例时，提示才会进入章节起草。",
        )
    with c2:
        st.number_input(
            "案例检索数量",
            min_value=1,
            max_value=8,
            key="case_library_top_k",
            disabled=not has_items,
        )
    st.multiselect(
        "显式选择案例（可选）",
        options=item_ids,
        key="case_library_selected_ids",
        format_func=lambda value: labels.get(str(value), str(value)),
        disabled=not has_items,
    )
    _render_reference_item_cards(items, id_key="case_id", selected_ids=st.session_state.get("case_library_selected_ids") or [])

    with st.expander("录入案例", expanded=False):
        st.selectbox("案例项目类型", options=PROJECT_TYPES, key="case_library_project_type")
        st.text_input("案例标题（可选）", key="case_library_upload_title")
        st.text_input("标签（可选，逗号/顿号分隔）", key="case_library_upload_tags")
        st.text_input("适用章节（可选，逗号/顿号分隔）", key="case_library_upload_chapter_scope")
        st.text_area("摘要（可选）", key="case_library_upload_summary", height=80)
        st.text_area("风格画像（可选）", key="case_library_upload_style_profile", height=80)
        files = st.file_uploader(
            "案例文件",
            type=["pdf", "doc", "docx", "txt", "md"],
            accept_multiple_files=True,
            key="case_library_files",
        )
        if st.button("加入案例库", key="case_library_upload_btn", width="stretch"):
            try:
                if not files:
                    raise ValueError("请先选择案例文件")
                params = {
                    "project_type": str(st.session_state.get("case_library_project_type") or "").strip(),
                    "title": str(st.session_state.get("case_library_upload_title") or "").strip(),
                    "tags": ",".join(_normalize_reference_text_list_ui(st.session_state.get("case_library_upload_tags") or "")),
                    "chapter_scope": ",".join(_normalize_reference_text_list_ui(st.session_state.get("case_library_upload_chapter_scope") or "")),
                    "summary": str(st.session_state.get("case_library_upload_summary") or "").strip(),
                    "style_profile": str(st.session_state.get("case_library_upload_style_profile") or "").strip(),
                    "usable": "true",
                }
                res = _post_files(base_url, "/actions/case_library/upload", actions_key, "files", list(files), params=params, timeout=900)
                saved = res.get("items") if isinstance(res, dict) else []
                st.success(f"已加入案例库：{len(saved or [])} 个文件")
                st.rerun()
            except Exception as e:
                st.error(f"案例库录入失败：{e}")


def _render_image_library_panel(base_url: str, actions_key: str) -> None:
    st.markdown("**图片库**")
    st.caption("默认关闭。启用后只在命中时提供章节图片选择包；无匹配图片时不强行插图。")
    project_type = str(st.session_state.get("image_library_project_type") or st.session_state.get("project_type") or "").strip()
    items: list[dict[str, Any]] = []
    try:
        items = _fetch_reference_items(base_url, actions_key, "/actions/image_library/items", project_type=project_type)
    except Exception as e:
        st.warning(f"图片库列表暂不可用：{e}")

    item_ids = [str(item.get("image_id") or "").strip() for item in items if str(item.get("image_id") or "").strip()]
    labels = {str(item.get("image_id") or "").strip(): _reference_item_label(item, "image_id") for item in items}
    current_selected = [x for x in _normalize_reference_text_list_ui(st.session_state.get("image_library_selected_ids") or []) if x in set(item_ids)]
    if current_selected != list(st.session_state.get("image_library_selected_ids") or []):
        st.session_state["image_library_selected_ids"] = current_selected
    has_items = bool(item_ids)
    if not has_items:
        st.session_state["image_library_enabled"] = False
        st.info("当前项目类型暂无可用图片；请先录入图片，系统不会启用空库增强或强行插图。")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.checkbox("生成时启用图片库增强", key="image_library_enabled", disabled=not has_items)
    with c2:
        st.number_input(
            "图片检索数量",
            min_value=1,
            max_value=8,
            key="image_library_top_k",
            disabled=not has_items,
        )
    st.multiselect(
        "显式选择图片（可选）",
        options=item_ids,
        key="image_library_selected_ids",
        format_func=lambda value: labels.get(str(value), str(value)),
        disabled=not has_items,
    )
    _render_reference_item_cards(items, id_key="image_id", selected_ids=st.session_state.get("image_library_selected_ids") or [])

    with st.expander("录入图片", expanded=False):
        st.selectbox("图片项目类型", options=PROJECT_TYPES, key="image_library_project_type")
        st.text_input("图片标题（可选）", key="image_library_upload_title")
        st.text_input("标签（可选，逗号/顿号分隔）", key="image_library_upload_tags")
        st.text_input("章节范围（可选，逗号/顿号分隔）", key="image_library_upload_chapter_scope")
        st.text_input("工序范围（可选，逗号/顿号分隔）", key="image_library_upload_process_scope")
        st.text_input("图注（可选）", key="image_library_upload_caption")
        st.text_area("图片说明（可选）", key="image_library_upload_description", height=80)
        files = st.file_uploader(
            "图片文件",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key="image_library_files",
        )
        if st.button("加入图片库", key="image_library_upload_btn", width="stretch"):
            try:
                if not files:
                    raise ValueError("请先选择图片文件")
                params = {
                    "project_type": str(st.session_state.get("image_library_project_type") or "").strip(),
                    "title": str(st.session_state.get("image_library_upload_title") or "").strip(),
                    "tags": ",".join(_normalize_reference_text_list_ui(st.session_state.get("image_library_upload_tags") or "")),
                    "chapter_scope": ",".join(_normalize_reference_text_list_ui(st.session_state.get("image_library_upload_chapter_scope") or "")),
                    "process_scope": ",".join(_normalize_reference_text_list_ui(st.session_state.get("image_library_upload_process_scope") or "")),
                    "caption": str(st.session_state.get("image_library_upload_caption") or "").strip(),
                    "description": str(st.session_state.get("image_library_upload_description") or "").strip(),
                    "usable": "true",
                }
                res = _post_files(base_url, "/actions/image_library/upload", actions_key, "files", list(files), params=params, timeout=900)
                saved = res.get("items") if isinstance(res, dict) else []
                st.success(f"已加入图片库：{len(saved or [])} 张图片")
                st.rerun()
            except Exception as e:
                st.error(f"图片库录入失败：{e}")


def _render_reference_libraries_panel(base_url: str, actions_key: str) -> None:
    with st.expander("参考库安全增强（按需启用）", expanded=False):
        case_tab, image_tab = st.tabs(["案例库", "图片库"])
        with case_tab:
            _render_case_library_panel(base_url, actions_key)
        with image_tab:
            _render_image_library_panel(base_url, actions_key)


def _render_ollama_preview_panel(base_url: str, actions_key: str) -> None:
    with st.expander("本地模型预览（人工触发）", expanded=False):
        st.caption("仅调用 `/actions/ollama/preview` 做只读预览，不写 job/result bundle，不接主生成链，不自动改正文。")
        m1, m2, m3 = st.columns([2, 2, 1])
        with m1:
            st.caption("Ollama 地址（系统锁定）")
            st.code("http://127.0.0.1:11434", language=None)
        with m2:
            st.text_input("本地模型", key="ollama_preview_model")
            st.caption(
                "推荐：qwen3.5:4b 用于默认质量预览；"
                "deepseek-r1:1.5b 用于轻量推理复核。系统按需切换，一次只加载一个模型。"
            )
        with m3:
            st.number_input("超时（秒）", min_value=1, max_value=300, key="ollama_preview_timeout")
        st.text_input("预览标题", key="ollama_preview_section_title")
        st.text_area("人工预览指令", key="ollama_preview_instruction", height=80)
        st.text_area("待预览补充正文（可选）", key="ollama_preview_content", height=120)

        if st.button("本地模型预览", key="ollama_preview_btn", type="secondary", width="stretch"):
            try:
                if not actions_key.strip():
                    raise ValueError("Actions Key 不能为空")
                payload = _build_ollama_preview_request_payload()
                result = _post_json(
                    base_url,
                    "/actions/ollama/preview",
                    actions_key,
                    payload,
                    timeout=int(payload.get("timeout") or 60) + 10,
                )
                st.session_state["ollama_preview_result"] = result
            except Exception as e:
                st.session_state["ollama_preview_result"] = {
                    "ok": False,
                    "status": "fallback",
                    "content": "",
                    "warning": str(e),
                }

        raw_result = st.session_state.get("ollama_preview_result") or {}
        if isinstance(raw_result, dict) and raw_result:
            normalized = _normalize_ollama_preview_result_ui(raw_result)
            if normalized.get("ok"):
                st.success(f"本地模型预览完成：{normalized.get('model') or 'ollama'}")
            elif normalized.get("warning"):
                st.warning(f"本地模型预览未完成：{normalized.get('warning')}")
            if normalized.get("content"):
                st.markdown("**预览结果（只读，不自动写回正文）**")
                st.code(normalized.get("content") or "", language="markdown")


def _render_claude_cache_metrics_panel(base_url: str, actions_key: str) -> None:
    """Render privacy-safe Claude token/cache aggregates from persisted usage."""

    with st.expander("Claude Token / Prompt Cache 统计", expanded=False):
        st.caption(
            "数据来自 Claude API 的 usage 字段；仅记录模型、Token、耗时、估算费用、项目 ID 和任务类型，"
            "不记录 API Key、提示词、项目正文或用户隐私。缓存默认采用 5 分钟 ephemeral TTL。"
        )
        if not actions_key.strip():
            st.info("填写 Actions Key 后可读取后端 Claude 使用统计。")
            return
        try:
            response = _get_json(base_url, "/actions/claude_usage_stats", actions_key, timeout=30)
            stats = response.get("stats") if isinstance(response, dict) else {}
            stats = stats if isinstance(stats, dict) else {}
            totals = stats.get("totals") if isinstance(stats.get("totals"), dict) else {}
        except Exception as exc:
            error = _stable_ui_error(exc)
            st.warning(f"Claude 统计暂不可用：{error.get('message') or '后端返回异常'}")
            return

        columns = st.columns(6)
        values = (
            ("总输入 Token", int(totals.get("total_input_tokens") or 0)),
            ("总输出 Token", int(totals.get("output_tokens") or 0)),
            ("Cache Write", int(totals.get("cache_creation_input_tokens") or 0)),
            ("Cache Read", int(totals.get("cache_read_input_tokens") or 0)),
            ("Cache 命中率", f"{float(totals.get('cache_hit_ratio') or 0.0):.1%}"),
            ("估算费用", f"${float(totals.get('estimated_cost_usd') or 0.0):.4f}"),
        )
        for column, (label, value) in zip(columns, values):
            column.metric(label, value)

        st.caption(
            f"调用 {int(totals.get('calls') or 0)} 次；未缓存输入 "
            f"{int(totals.get('input_tokens') or 0)} Token；按无缓存基线估算节省 "
            f"${float(totals.get('estimated_savings_usd') or 0.0):.4f} "
            f"（{float(totals.get('estimated_savings_ratio') or 0.0):.1%}）。"
        )

        model_rows = stats.get("by_model") if isinstance(stats.get("by_model"), list) else []
        if model_rows:
            st.markdown("**各模型调用量**")
            st.dataframe(model_rows, width="stretch", hide_index=True)

        current_project_id = str(st.session_state.get("project_id_text") or "").strip()
        project_stats = stats
        if current_project_id:
            try:
                project_response = _get_json(
                    base_url,
                    "/actions/claude_usage_stats",
                    actions_key,
                    params={"project_id": current_project_id},
                    timeout=30,
                )
                candidate = project_response.get("stats") if isinstance(project_response, dict) else {}
                if isinstance(candidate, dict):
                    project_stats = candidate
            except Exception:
                project_stats = {"totals": {}, "by_task": []}

        project_totals = (
            project_stats.get("totals")
            if isinstance(project_stats.get("totals"), dict)
            else {}
        )
        project_label = current_project_id or "全部项目（尚未选择当前项目）"
        st.markdown(f"**当前项目 API 消耗：{project_label}**")
        st.caption(
            f"输入 {int(project_totals.get('total_input_tokens') or 0)} Token，"
            f"输出 {int(project_totals.get('output_tokens') or 0)} Token，"
            f"Cache Read {int(project_totals.get('cache_read_input_tokens') or 0)} Token，"
            f"估算费用 ${float(project_totals.get('estimated_cost_usd') or 0.0):.4f}。"
        )
        task_rows = (
            project_stats.get("by_task")
            if isinstance(project_stats.get("by_task"), list)
            else []
        )
        if task_rows:
            st.markdown("**当前项目各任务 API 消耗**")
            st.dataframe(task_rows, width="stretch", hide_index=True)


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


def _stable_ui_error(exc: Exception) -> dict[str, str]:
    """Convert local runtime failures into stable, non-sensitive Chinese UI errors."""

    if isinstance(exc, requests.exceptions.ConnectionError):
        return {
            "code": "BACKEND_UNAVAILABLE",
            "message": "后端服务暂不可用，当前操作结果尚无法确认。",
            "action": "等待系统恢复后先核对任务状态；页面不会自动重复提交。",
        }
    if isinstance(exc, requests.exceptions.Timeout):
        return {
            "code": "BACKEND_TIMEOUT",
            "message": "后端请求超时，本次操作未确认完成。",
            "action": "请先检查任务状态，避免重复提交；确认无运行任务后再重试。",
        }

    raw = str(exc or "").strip()
    if "Connection refused" in raw or "Failed to establish a new connection" in raw:
        return {
            "code": "BACKEND_UNAVAILABLE",
            "message": "后端服务暂不可用，当前操作结果尚无法确认。",
            "action": "等待系统恢复后先核对任务状态；页面不会自动重复提交。",
        }
    if isinstance(exc, ValueError):
        return {
            "code": "INPUT_INVALID",
            "message": raw[:300] or "输入资料或配置不完整。",
            "action": "请按页面提示补齐或修正输入后重试。",
        }

    for candidate in (raw, raw[raw.find("{") :] if "{" in raw else ""):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        detail = parsed.get("detail") if isinstance(parsed.get("detail"), dict) else parsed
        code = str(detail.get("code") or "RUNTIME_REQUEST_FAILED")[:80]
        message = str(detail.get("message") or "后端未完成本次操作。")[:500]
        action = str(detail.get("action") or "请核对任务状态和资料后重试。")[:500]
        return {"code": code, "message": message, "action": action}

    if "超时" in raw or "timeout" in raw.lower():
        return {
            "code": "INGEST_TIMEOUT",
            "message": "资料处理超过允许时间，本次操作未确认完成。",
            "action": "请先检查任务状态，再拆分大型文件或稍后重试。",
        }
    if "失败: 4" in raw or "失败: 5" in raw:
        return {
            "code": "BACKEND_REQUEST_REJECTED",
            "message": "后端拒绝或未能完成本次请求。",
            "action": "请核对必传资料、文件解析状态和后端健康状态后重试。",
        }
    return {
        "code": "RUNTIME_REQUEST_FAILED",
        "message": "系统未能完成本次操作，未进入可确认的生成阶段。",
        "action": "请核对任务状态与运行日志后重试。",
    }


def _set_preflight_status(stage: int, label: str, *, state: str = "running") -> None:
    st.session_state["preflight_status"] = {
        "state": str(state or "running"),
        "stage": max(0, min(6, int(stage))),
        "label": str(label or "").strip(),
        "updated_at": time.time(),
    }


def _render_task_status(container) -> None:
    active = st.session_state.get("active_job") or {}
    if active:
        container.warning(f"任务执行中：{active.get('job_id')} | 状态：{active.get('status', 'queued')}")
        return

    preflight = st.session_state.get("preflight_status") or {}
    state = str(preflight.get("state") or "").strip().lower()
    stage = max(0, min(6, int(preflight.get("stage") or 0)))
    label = str(preflight.get("label") or "").strip()
    if state == "running":
        container.warning(f"资料预检进行中（{stage}/6）：{label or '正在处理'}")
    elif state == "failed":
        container.error(f"上次预检失败（{stage}/6）：{label or '请查看下方错误日志'}")
    else:
        container.success("当前无运行中任务")


def _inject_ui_style() -> None:
    st.markdown(EXPERT_SYSTEM_CSS, unsafe_allow_html=True)


def _init_state() -> None:
    env_main_provider = _normalize_provider(
        _env_first("ZF_LLM_MAIN_PROVIDER", "ZF_DEFAULT_PROVIDER"),
        fallback="google",
    )
    env_main_model = _env_first("ZF_LLM_MAIN_MODEL") or _latest_model_for(env_main_provider) or _latest_model_for("google")
    env_f1_provider_raw = _env_first("ZF_LLM_FALLBACK1_PROVIDER")
    env_f1_provider = _normalize_provider(env_f1_provider_raw, fallback="") if env_f1_provider_raw else ""
    env_f1_model = _env_first("ZF_LLM_FALLBACK1_MODEL") or (_latest_model_for(env_f1_provider) if env_f1_provider else "")
    env_f1_enabled = bool(env_f1_provider and env_f1_model)

    env_f2_provider_raw = _env_first("ZF_LLM_FALLBACK2_PROVIDER")
    env_f2_provider = _normalize_provider(env_f2_provider_raw, fallback="") if env_f2_provider_raw else ""
    env_f2_model = _env_first("ZF_LLM_FALLBACK2_MODEL") or (_latest_model_for(env_f2_provider) if env_f2_provider else "")
    env_f2_enabled = bool(env_f2_provider and env_f2_model)
    env_image_provider = _env_first("ZF_IMAGE_MAIN_PROVIDER") or "openai"
    env_image_model = _env_first("ZF_IMAGE_MAIN_MODEL", "OPENAI_IMAGE_MODEL") or "gpt-image-2"

    defaults = {
        "topic_text": "施工组织设计方案",
        "project_id_text": "",
        "project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "variants_value": 1,
        "selected_templates": ["A"],
        "global_instruction": DEFAULT_GLOBAL_INSTRUCTION,
        "requirements_text": "严格按技术文件详细评审标准中的章目录组织内容，不新增顶层章节\n每节输出量化指标与风险-控制-验证闭环\n全文禁止官话、套话、空话",
        "outline_items": [],
        "outline_pages": [],
        "generation_mode": "quality_200",
        "total_pages_target": 0,
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": "template",
        "allow_fable_escalation": False,
        "agent_parallelism": 4,
        "variant_parallelism": 1,
        "generate_images": True,
        "image_provider": env_image_provider,
        "image_model": env_image_model,
        "provider_text": env_main_provider,
        "model_text": env_main_model,
        "fallback_1_enabled": env_f1_enabled,
        "fallback_1_provider": env_f1_provider,
        "fallback_1_model": env_f1_model,
        "fallback_2_enabled": env_f2_enabled,
        "fallback_2_provider": env_f2_provider,
        "fallback_2_model": env_f2_model,
        "chapter_requirements_text": "",
        "params_override_text": "",
        "template_key": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "strict_tender_outline": True,
        "body_font": "宋体",
        "title_font": "宋体",
        "body_size": 14,
        "title_size": 16,
        "line_spacing_pt": 22.0,
        "line_spacing_mode": "fixed_pt",
        "line_spacing_multiple": 1.5,
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
        "case_library_enabled": False,
        "case_library_top_k": 3,
        "case_library_selected_ids": [],
        "case_library_project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "case_library_upload_title": "",
        "case_library_upload_tags": "",
        "case_library_upload_chapter_scope": "",
        "case_library_upload_summary": "",
        "case_library_upload_style_profile": "",
        "image_library_enabled": False,
        "image_library_top_k": 3,
        "image_library_selected_ids": [],
        "image_library_project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "image_library_upload_title": "",
        "image_library_upload_tags": "",
        "image_library_upload_chapter_scope": "",
        "image_library_upload_process_scope": "",
        "image_library_upload_caption": "",
        "image_library_upload_description": "",
        "ollama_preview_model": "qwen3.5:4b",
        "ollama_preview_timeout": 60,
        "ollama_preview_section_title": "",
        "ollama_preview_instruction": "只做人工预览增强，指出缺项、风险和可人工采纳的优化建议；不要改写正文，不要生成新事实。",
        "ollama_preview_content": "",
        "ollama_preview_result": {},
        "ollama_section_review_focus": "章节完整性、缺项、风险点、可执行字段、证据支撑和表达清晰度",
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
    selected_templates = _normalize_template_selection(st.session_state.get("selected_templates")) or ["A"]
    st.session_state["variants_value"] = len(selected_templates)
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
    if PROJECT_TYPES and st.session_state.get("case_library_project_type") not in PROJECT_TYPES:
        st.session_state["case_library_project_type"] = str(st.session_state.get("project_type") or PROJECT_TYPES[0])
    if PROJECT_TYPES and st.session_state.get("image_library_project_type") not in PROJECT_TYPES:
        st.session_state["image_library_project_type"] = str(st.session_state.get("project_type") or PROJECT_TYPES[0])

    # UI 默认值迁移：将高级参数中的勾选项改为默认不勾选（仅迁移一次）。
    defaults_rev = "2026-02-26-high-quality-defaults"
    if st.session_state.get("_ui_defaults_rev") != defaults_rev:
        st.session_state["quality_strict"] = True
        st.session_state["auto_remediate"] = True
        st.session_state["generate_images"] = True
        st.session_state["fallback_1_enabled"] = bool(st.session_state.get("fallback_1_enabled"))
        st.session_state["fallback_2_enabled"] = bool(st.session_state.get("fallback_2_enabled"))
        st.session_state["_ui_defaults_rev"] = defaults_rev

    compliance_policy_rev = "2026-08-22-project-applicable-standards-v1"
    if st.session_state.get("_compliance_policy_rev") != compliance_policy_rev:
        if should_migrate_global_instruction(st.session_state.get("global_instruction")):
            st.session_state["global_instruction"] = DEFAULT_GLOBAL_INSTRUCTION
        st.session_state["_compliance_policy_rev"] = compliance_policy_rev

    model_route_rev = "2026-08-22-anthropic-sonnet-opus-tiered-v2"
    if st.session_state.get("_model_route_rev") != model_route_rev:
        st.session_state["provider_text"] = env_main_provider
        st.session_state["model_text"] = env_main_model
        st.session_state["fallback_1_provider"] = env_f1_provider
        st.session_state["fallback_1_model"] = env_f1_model
        st.session_state["fallback_1_enabled"] = env_f1_enabled
        st.session_state["image_provider"] = env_image_provider
        st.session_state["image_model"] = env_image_model
        st.session_state["allow_fable_escalation"] = False
        st.session_state["_model_route_rev"] = model_route_rev

    st.session_state.setdefault("run_logs", [])
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault("active_job", None)
    st.session_state.setdefault("preflight_status", None)
    st.session_state.setdefault("chapter_page_map", {})

    # A browser disconnect or an app restart can interrupt the synchronous
    # preflight before an async job exists. Preserve that fact instead of
    # presenting the stale run as "no running task".
    if (
        not st.session_state.get("preflight_status")
        and not st.session_state.get("active_job")
        and not st.session_state.get("run_result")
    ):
        logs = st.session_state.get("run_logs") or []
        last_stage = 0
        has_terminal_marker = False
        for entry in logs:
            text = str(entry or "")
            match = re.search(r"步骤\s+([1-6])/6", text)
            if match:
                last_stage = max(last_stage, int(match.group(1)))
            if "任务已排队" in text or "失败:" in text:
                has_terminal_marker = True
        if last_stage and not has_terminal_marker:
            st.session_state["preflight_status"] = {
                "state": "failed",
                "stage": last_stage,
                "label": "上次预检意外中断；已选文件仍保留，可安全重试",
                "updated_at": time.time(),
            }


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
    st.markdown(
        section_heading_html("03", "评审目录", "从招标评审标准提取章节，也可调整标题、顺序与目标页数。"),
        unsafe_allow_html=True,
    )
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
    if c_add.button("新增章节", width="stretch"):
        items.append("")
        pages.append(2)
        st.session_state["outline_items"] = items
        st.session_state["outline_pages"] = pages
        _clear_outline_widget_state()
        st.rerun()
    if c_clear.button("清空目录", width="stretch"):
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


def _normalize_reference_summary_ui(summary: dict[str, Any] | None, *, id_key: str) -> dict[str, Any]:
    data = summary if isinstance(summary, dict) else {}
    selected_ids = []
    seen_ids: set[str] = set()
    for item in (data.get(id_key) or []):
        text = str(item or "").strip()
        if not text or text in seen_ids:
            continue
        seen_ids.add(text)
        selected_ids.append(text)
    matched_chapters = []
    seen_chapters: set[str] = set()
    for item in [
        *(data.get("matched_chapters") or []),
        data.get("matched_chapter"),
    ]:
        text = str(item or "").strip()
        if not text or text in seen_chapters:
            continue
        seen_chapters.add(text)
        matched_chapters.append(text)
    match_reasons = []
    seen_reasons: set[str] = set()
    for item in [
        *(data.get("match_reasons") or []),
        data.get("match_reason"),
    ]:
        text = str(item or "").strip()
        if not text or text in seen_reasons:
            continue
        seen_reasons.add(text)
        match_reasons.append(text)
    warning_list = []
    seen_warnings: set[str] = set()
    for item in (data.get("warning_list") or []):
        text = str(item or "").strip()
        if not text or text in seen_warnings:
            continue
        seen_warnings.add(text)
        warning_list.append(text)
    return {
        "enabled": bool(data.get("enabled", False)),
        id_key: selected_ids,
        "matched_project_type": str(data.get("matched_project_type") or "").strip() or None,
        "matched_chapters": matched_chapters,
        "matched_chapter": matched_chapters[0] if matched_chapters else None,
        "match_reasons": match_reasons,
        "match_reason": match_reasons[0] if match_reasons else None,
        "hit_count": int(data.get("hit_count") or len(selected_ids) or 0),
        "warning_list": warning_list,
    }


def _reference_summary_has_content(summary: dict[str, Any] | None, *, id_key: str) -> bool:
    normalized = _normalize_reference_summary_ui(summary, id_key=id_key)
    return any(
        [
            bool(normalized.get("enabled")),
            bool(normalized.get(id_key)),
            bool(normalized.get("matched_project_type")),
            bool(normalized.get("matched_chapters")),
            bool(normalized.get("match_reasons")),
            bool(normalized.get("warning_list")),
            int(normalized.get("hit_count") or 0) > 0,
        ]
    )


def _decode_result_json_ui(result: dict[str, Any] | None) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    raw = payload.get("result_json")
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="ignore")
    else:
        text = str(raw or "").strip()
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except Exception:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _variant_sections_from_result_ui(result: dict[str, Any] | None, variant: int) -> list[dict[str, Any]]:
    payload = _decode_result_json_ui(result)
    rows = payload.get("variants") if isinstance(payload.get("variants"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate = row.get("variant_id")
        try:
            if int(candidate) == int(variant):
                sections = row.get("sections")
                return sections if isinstance(sections, list) else []
        except Exception:
            continue
    return []


def _section_review_title_ui(section: dict[str, Any], index: int) -> str:
    title = str(section.get("title") or section.get("heading") or "").strip()
    return title or f"章节 {index + 1}"


def _section_review_content_ui(section: dict[str, Any]) -> str:
    for key in ["content", "body", "markdown", "text"]:
        value = section.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_ollama_section_review_request_payload(section: dict[str, Any], *, section_title: str) -> dict[str, Any]:
    project_name = (
        str(st.session_state.get("topic_text") or "").strip()
        or str(st.session_state.get("project_id_text") or "").strip()
        or "施工组织设计方案"
    )
    review_focus = str(st.session_state.get("ollama_section_review_focus") or "").strip()
    return {
        "project_name": project_name,
        "section_title": section_title,
        "section_content": _section_review_content_ui(section)[:12000],
        "review_focus": review_focus or "章节完整性、缺项、风险点、可执行字段、证据支撑和表达清晰度",
        "model": str(st.session_state.get("ollama_preview_model") or "qwen3.5:4b").strip() or "qwen3.5:4b",
        "base_url": "http://127.0.0.1:11434",
        "timeout": _ollama_preview_timeout_state(),
    }


def _chapter_case_reference_summary_ui(raw: dict[str, Any] | None) -> dict[str, Any]:
    pack = raw if isinstance(raw, dict) else {}
    hits = pack.get("hits") if isinstance(pack.get("hits"), list) else []
    return _normalize_reference_summary_ui(
        {
            "enabled": bool(pack.get("enabled", False)),
            "selected_case_ids": [
                str(item).strip()
                for item in (pack.get("selected_case_ids") or [])
                if str(item).strip()
            ],
            "matched_project_type": pack.get("matched_project_type"),
            "matched_chapter": pack.get("matched_chapter"),
            "match_reason": pack.get("match_reason"),
            "hit_count": len(hits),
            "warning_list": pack.get("warning_list") or [],
        },
        id_key="selected_case_ids",
    )


def _chapter_image_reference_summary_ui(raw: dict[str, Any] | None) -> dict[str, Any]:
    pack = raw if isinstance(raw, dict) else {}
    images = pack.get("images") if isinstance(pack.get("images"), list) else []
    return _normalize_reference_summary_ui(
        {
            "enabled": bool(pack.get("enabled", False)),
            "selected_image_ids": [
                str(item).strip()
                for item in (pack.get("selected_image_ids") or [])
                if str(item).strip()
            ],
            "matched_project_type": pack.get("matched_project_type"),
            "matched_chapter": pack.get("matched_chapter"),
            "match_reason": pack.get("match_reason"),
            "hit_count": len(images),
            "warning_list": pack.get("warning_list") or [],
        },
        id_key="selected_image_ids",
    )


def _chapter_reference_rows_ui(result: dict[str, Any] | None, variant: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in _variant_sections_from_result_ui(result, variant):
        if not isinstance(section, dict):
            continue
        case_summary = _chapter_case_reference_summary_ui(section.get("case_reference_pack"))
        image_summary = _chapter_image_reference_summary_ui(section.get("image_selection_pack"))
        if not (
            _reference_summary_has_content(case_summary, id_key="selected_case_ids")
            or _reference_summary_has_content(image_summary, id_key="selected_image_ids")
        ):
            continue
        rows.append(
            {
                "title": str(section.get("title") or "").strip() or "章节",
                "case_library": case_summary,
                "image_library": image_summary,
            }
        )
    return rows


def _aggregate_reference_summary_from_chapter_rows_ui(
    rows: list[dict[str, Any]] | None,
    *,
    summary_key: str,
    id_key: str,
) -> dict[str, Any]:
    normalized_rows = rows if isinstance(rows, list) else []
    enabled = False
    selected_ids: list[str] = []
    seen_ids: set[str] = set()
    matched_project_types: list[str] = []
    seen_project_types: set[str] = set()
    matched_chapters: list[str] = []
    seen_chapters: set[str] = set()
    match_reasons: list[str] = []
    seen_reasons: set[str] = set()
    warning_list: list[str] = []
    seen_warnings: set[str] = set()
    hit_count = 0
    for row in normalized_rows:
        if not isinstance(row, dict):
            continue
        summary = row.get(summary_key) if isinstance(row.get(summary_key), dict) else {}
        item = _normalize_reference_summary_ui(summary, id_key=id_key)
        if not _reference_summary_has_content(item, id_key=id_key):
            continue
        enabled = enabled or bool(item.get("enabled"))
        hit_count += int(item.get("hit_count") or 0)
        for value in item.get(id_key) or []:
            if value not in seen_ids:
                seen_ids.add(value)
                selected_ids.append(value)
        project_type = str(item.get("matched_project_type") or "").strip()
        if project_type and project_type not in seen_project_types:
            seen_project_types.add(project_type)
            matched_project_types.append(project_type)
        chapters = [str(x).strip() for x in (item.get("matched_chapters") or []) if str(x).strip()]
        if not chapters:
            fallback_title = str(row.get("title") or "").strip()
            if fallback_title:
                chapters = [fallback_title]
        for chapter in chapters:
            if chapter not in seen_chapters:
                seen_chapters.add(chapter)
                matched_chapters.append(chapter)
        for reason in item.get("match_reasons") or []:
            text = str(reason or "").strip()
            if text and text not in seen_reasons:
                seen_reasons.add(text)
                match_reasons.append(text)
        for warning in item.get("warning_list") or []:
            text = str(warning or "").strip()
            if text and text not in seen_warnings:
                seen_warnings.add(text)
                warning_list.append(text)
    return {
        "enabled": enabled,
        id_key: selected_ids,
        "matched_project_type": matched_project_types[0] if len(matched_project_types) == 1 else None,
        "matched_chapters": matched_chapters,
        "matched_chapter": matched_chapters[0] if matched_chapters else None,
        "match_reasons": match_reasons,
        "match_reason": match_reasons[0] if match_reasons else None,
        "hit_count": hit_count,
        "warning_list": warning_list,
    }


def _merge_reference_summary_ui(
    primary: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
    *,
    id_key: str,
) -> dict[str, Any]:
    current = _normalize_reference_summary_ui(primary, id_key=id_key)
    fallback_summary = _normalize_reference_summary_ui(fallback, id_key=id_key)
    merged = dict(current)
    if not merged.get("enabled"):
        merged["enabled"] = bool(fallback_summary.get("enabled"))
    if not merged.get(id_key):
        merged[id_key] = list(fallback_summary.get(id_key) or [])
    if not merged.get("matched_project_type"):
        merged["matched_project_type"] = fallback_summary.get("matched_project_type")
    if not merged.get("matched_chapters"):
        merged["matched_chapters"] = list(fallback_summary.get("matched_chapters") or [])
        merged["matched_chapter"] = merged["matched_chapters"][0] if merged["matched_chapters"] else None
    if not merged.get("match_reasons"):
        merged["match_reasons"] = list(fallback_summary.get("match_reasons") or [])
        merged["match_reason"] = merged["match_reasons"][0] if merged["match_reasons"] else None
    if not int(merged.get("hit_count") or 0):
        merged["hit_count"] = int(fallback_summary.get("hit_count") or 0)
    if fallback_summary.get("warning_list"):
        merged["warning_list"] = list(
            dict.fromkeys(
                [
                    *[str(x).strip() for x in (merged.get("warning_list") or []) if str(x).strip()],
                    *[str(x).strip() for x in (fallback_summary.get("warning_list") or []) if str(x).strip()],
                ]
            )
        )
    return merged


def _variant_reference_summaries_ui(
    result: dict[str, Any] | None,
    variant: int,
    runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    runtime_payload = runtime if isinstance(runtime, dict) else {}
    chapter_rows = _chapter_reference_rows_ui(result, variant)
    return {
        "case_library_summary": _merge_reference_summary_ui(
            runtime_payload.get("case_library_summary") if isinstance(runtime_payload.get("case_library_summary"), dict) else {},
            _aggregate_reference_summary_from_chapter_rows_ui(
                chapter_rows,
                summary_key="case_library",
                id_key="selected_case_ids",
            ),
            id_key="selected_case_ids",
        ),
        "image_library_summary": _merge_reference_summary_ui(
            runtime_payload.get("image_library_summary") if isinstance(runtime_payload.get("image_library_summary"), dict) else {},
            _aggregate_reference_summary_from_chapter_rows_ui(
                chapter_rows,
                summary_key="image_library",
                id_key="selected_image_ids",
            ),
            id_key="selected_image_ids",
        ),
    }


def _render_ollama_section_review_panel(
    base_url: str,
    actions_key: str,
    result: dict[str, Any],
    variant: int,
) -> None:
    sections = _variant_sections_from_result_ui(result, variant)
    if not sections:
        return

    with st.expander("本地模型章节复核（人工触发）", expanded=False):
        st.caption("只调用 `/actions/ollama/review_section` 展示复核建议，不改正文、不写 job/result bundle、不刷新导出产物。")
        options = list(range(len(sections)))
        selected_index = st.selectbox(
            "选择待复核章节",
            options=options,
            format_func=lambda idx: _section_review_title_ui(sections[int(idx)], int(idx)),
            key=f"ollama_section_review_selected_v{variant}",
        )
        section = sections[int(selected_index)] if options else {}
        section_title = _section_review_title_ui(section, int(selected_index))
        section_content = _section_review_content_ui(section)
        result_key = f"ollama_section_review_result_v{variant}_s{int(selected_index)}"
        st.text_area(
            "复核重点",
            key="ollama_section_review_focus",
            height=80,
            placeholder="例如：章节完整性、参数、责任、频次、验收、记录、证据支撑和风险闭环",
        )
        st.caption(
            f"当前章节：{section_title}；可复核正文长度={len(section_content)} 字；"
            f"模型={st.session_state.get('ollama_preview_model') or 'qwen3.5:4b'}"
        )

        if st.button("本地模型复核本章", key=f"ollama_section_review_btn_v{variant}", type="secondary", width="stretch"):
            try:
                if not actions_key.strip():
                    raise ValueError("Actions Key 不能为空")
                if not section_content:
                    raise ValueError("当前章节未找到可复核正文")
                payload = _build_ollama_section_review_request_payload(section, section_title=section_title)
                result_payload = _post_json(
                    base_url,
                    "/actions/ollama/review_section",
                    actions_key,
                    payload,
                    timeout=int(payload.get("timeout") or 60) + 10,
                )
                st.session_state[result_key] = result_payload
            except Exception as e:
                st.session_state[result_key] = {
                    "ok": False,
                    "status": "fallback",
                    "review_type": "section_review",
                    "model": str(st.session_state.get("ollama_preview_model") or "qwen3.5:4b"),
                    "content": "",
                    "warning": str(e),
                }

        raw_result = st.session_state.get(result_key) or {}
        if isinstance(raw_result, dict) and raw_result:
            normalized = _normalize_ollama_section_review_result_ui(raw_result)
            st.caption(
                f"ok={normalized.get('ok')}；status={normalized.get('status') or '-'}；"
                f"model={normalized.get('model') or '-'}；review_type={normalized.get('review_type') or '-'}"
            )
            if normalized.get("ok"):
                st.success("本地模型章节复核完成")
            else:
                st.warning(f"本地模型章节复核未完成：{normalized.get('error') or normalized.get('warning') or '-'}")
            if normalized.get("content"):
                st.markdown("**章节复核建议（只读，不自动写回正文）**")
                review_content = str(normalized.get("content") or "").strip()
                st.code(review_content, language="markdown")
                markdown_export = "\n\n".join(
                    [
                        "# 本地模型章节复核建议",
                        f"- 方案编号：v{variant}",
                        f"- 章节标题：{section_title}",
                        f"- 模型：{normalized.get('model') or '-'}",
                        f"- 状态：{normalized.get('status') or '-'}",
                        "## 复核建议正文",
                        review_content,
                    ]
                )
                text_export = "\n".join(
                    [
                        "本地模型章节复核建议",
                        f"方案编号：v{variant}",
                        f"章节标题：{section_title}",
                        f"模型：{normalized.get('model') or '-'}",
                        f"状态：{normalized.get('status') or '-'}",
                        "",
                        "复核建议正文：",
                        review_content,
                    ]
                )
                st.text_area(
                    "复制复核建议",
                    value=review_content,
                    height=180,
                    key=f"ollama_section_review_copy_v{variant}_s{int(selected_index)}",
                    help="仅供手动复制，不会写回正文或产物。",
                )
                dl_md, dl_txt = st.columns([1, 1])
                with dl_md:
                    st.download_button(
                        "下载复核建议.md",
                        data=markdown_export,
                        file_name=f"ollama_section_review_v{variant}_s{int(selected_index) + 1}.md",
                        mime="text/markdown",
                        key=f"ollama_section_review_download_md_v{variant}_s{int(selected_index)}",
                        width="stretch",
                    )
                with dl_txt:
                    st.download_button(
                        "下载复核建议.txt",
                        data=text_export,
                        file_name=f"ollama_section_review_v{variant}_s{int(selected_index) + 1}.txt",
                        mime="text/plain",
                        key=f"ollama_section_review_download_txt_v{variant}_s{int(selected_index)}",
                        width="stretch",
                    )
                st.markdown("**草稿对比预览（不写回）**")
                st.caption("当前仅生成草稿对比预览，不写回正文，不更新成果，不触发导出。")
                draft_content_key = f"ollama_section_draft_content_v{variant}_s{int(selected_index)}"
                draft_source_key = f"{draft_content_key}_source"
                if st.session_state.get(draft_source_key) != review_content:
                    st.session_state[draft_content_key] = review_content
                    st.session_state[draft_source_key] = review_content
                draft_content = st.text_area(
                    "草稿内容（仅用于草稿预览，不会写回正文）",
                    key=draft_content_key,
                    height=220,
                    help="默认填入本地模型章节复核建议，可手动编辑后生成只读 diff/audit 预览。",
                )
                draft_result_key = f"ollama_section_draft_preview_result_v{variant}_s{int(selected_index)}"
                if st.button(
                    "生成草稿对比预览（不写回）",
                    key=f"ollama_section_draft_preview_btn_v{variant}_s{int(selected_index)}",
                    type="secondary",
                    width="stretch",
                ):
                    try:
                        if not actions_key.strip():
                            raise ValueError("Actions Key 不能为空")
                        if not section_content:
                            raise ValueError("当前章节未找到可对比正文")
                        if not str(draft_content or "").strip():
                            raise ValueError("草稿内容不能为空")
                        project_name = (
                            str(st.session_state.get("topic_text") or "").strip()
                            or str(st.session_state.get("project_id_text") or "").strip()
                            or "施工组织设计方案"
                        )
                        draft_payload = {
                            "project_name": project_name,
                            "section_title": section_title,
                            "original_content": section_content,
                            "draft_content": str(draft_content or "").strip(),
                            "provider": "ollama",
                            "model": str(normalized.get("model") or st.session_state.get("ollama_preview_model") or "qwen3.5:4b"),
                            "base_url": "http://127.0.0.1:11434",
                            "prompt": str(st.session_state.get("ollama_section_review_focus") or "").strip()
                            or "基于本地模型章节复核建议生成草稿对比预览",
                            "confirmed_by": "streamlit_manual_preview",
                        }
                        draft_decision_result_key = f"ollama_section_draft_decision_result_v{variant}_s{int(selected_index)}"
                        st.session_state.pop(draft_decision_result_key, None)
                        st.session_state[draft_result_key] = _post_json(
                            base_url,
                            "/actions/ollama/section_draft/build",
                            actions_key,
                            draft_payload,
                            timeout=60,
                        )
                    except Exception as e:
                        st.session_state[draft_result_key] = {
                            "ok": False,
                            "status": "error",
                            "draft_type": "section_draft",
                            "section_title": section_title,
                            "draft": None,
                            "diff_preview": "",
                            "audit": [],
                            "error": str(e),
                        }
                draft_preview_result = st.session_state.get(draft_result_key) or {}
                draft_decision_result_key = f"ollama_section_draft_decision_result_v{variant}_s{int(selected_index)}"
                if isinstance(draft_preview_result, dict) and draft_preview_result:
                    draft_status = str(draft_preview_result.get("status") or "").strip()
                    draft_warning = str(draft_preview_result.get("warning") or draft_preview_result.get("error") or "").strip()
                    st.caption(
                        f"ok={bool(draft_preview_result.get('ok'))}；status={draft_status or '-'}；"
                        f"draft_type={draft_preview_result.get('draft_type') or '-'}"
                    )
                    if draft_status == "disabled":
                        st.warning(f"草稿预览未启用：{draft_warning or 'ollama_write_back_disabled'}")
                    elif draft_preview_result.get("ok"):
                        st.success("草稿对比预览已生成")
                    else:
                        st.warning(f"草稿对比预览未完成：{draft_warning or '-'}")
                    diff_preview = str(draft_preview_result.get("diff_preview") or "")
                    if diff_preview.strip():
                        st.code(diff_preview, language="diff")
                    else:
                        st.info("暂无 diff_preview。")
                    st.markdown("**草稿审计记录（只读）**")
                    st.json(draft_preview_result.get("audit") or [])
                    st.markdown("**草稿决策预览（不写回）**")
                    st.caption("当前操作仅生成草稿决策预览，不写回正式正文，不更新成果，不触发导出。")
                    draft_data = draft_preview_result.get("draft") if isinstance(draft_preview_result.get("draft"), dict) else {}
                    decision_buttons = st.columns([1, 1, 1])
                    decision_actions = [
                        ("应用预览（不写回）", "apply_preview", "/actions/ollama/section_draft/apply_preview"),
                        ("拒绝草稿", "reject", "/actions/ollama/section_draft/reject"),
                        ("回滚预览", "rollback", "/actions/ollama/section_draft/rollback"),
                    ]
                    for idx, (label, action_name, endpoint) in enumerate(decision_actions):
                        with decision_buttons[idx]:
                            if st.button(
                                label,
                                key=f"ollama_section_draft_decision_{action_name}_btn_v{variant}_s{int(selected_index)}",
                                type="secondary",
                                width="stretch",
                            ):
                                try:
                                    if not actions_key.strip():
                                        raise ValueError("Actions Key 不能为空")
                                    if not draft_data:
                                        raise ValueError("请先生成可用的草稿对比预览")
                                    st.session_state[draft_decision_result_key] = _post_json(
                                        base_url,
                                        endpoint,
                                        actions_key,
                                        {
                                            "draft": draft_data,
                                            "confirmed_by": f"streamlit_manual_{action_name}",
                                        },
                                        timeout=60,
                                    )
                                except Exception as e:
                                    st.session_state[draft_decision_result_key] = {
                                        "ok": False,
                                        "status": "error",
                                        "draft_type": "section_draft",
                                        "action_type": action_name,
                                        "draft": None,
                                        "audit": [],
                                        "error": str(e),
                                    }
                    draft_decision_result = st.session_state.get(draft_decision_result_key) or {}
                    if isinstance(draft_decision_result, dict) and draft_decision_result:
                        decision_status = str(draft_decision_result.get("status") or "").strip()
                        decision_action = str(draft_decision_result.get("action_type") or "").strip()
                        decision_warning = str(draft_decision_result.get("warning") or draft_decision_result.get("error") or "").strip()
                        decision_draft = (
                            draft_decision_result.get("draft") if isinstance(draft_decision_result.get("draft"), dict) else {}
                        )
                        decision_draft_status = str(decision_draft.get("status") or "").strip()
                        st.info(
                            f"status={decision_status or '-'}；action_type={decision_action or '-'}；"
                            f"draft.status={decision_draft_status or '-'}"
                        )
                        if decision_status == "disabled":
                            st.warning(f"草稿决策预览未启用：{decision_warning or 'ollama_write_back_disabled'}")
                        elif not draft_decision_result.get("ok"):
                            st.warning(f"草稿决策预览未完成：{decision_warning or '-'}")
                        st.markdown("**草稿决策审计记录（只读）**")
                        st.json(draft_decision_result.get("audit") or [])
                        with st.expander("草稿决策数据（只读）", expanded=False):
                            st.json(decision_draft)
                    with st.expander("草稿数据（只读）", expanded=False):
                        st.json(draft_preview_result.get("draft") or {})


def _render_downloads(base_url: str, actions_key: str) -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return

    st.subheader("结果预览与下载")
    job_id = result.get("job_id", "")
    variants = int(result.get("variants") or 1)
    st.write(f"job_id: `{job_id}`")
    delivery_receipt = result.get("delivery_receipt")
    if isinstance(delivery_receipt, dict):
        decision_digest = str(delivery_receipt.get("decision_digest") or "")
        st.success(
            "任务级交付凭证已通过：全部方案的内容、结构、图表、页面视觉和最终文件哈希均已封存。"
        )
        st.caption(
            f"交付决策摘要：{decision_digest[:16] or '-'}…；"
            f"方案数={delivery_receipt.get('variant_count') or variants}。"
        )
        st.download_button(
            label="下载任务级质量与追溯凭证.json",
            data=json.dumps(delivery_receipt, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"autoplan_{job_id}_delivery_receipt.json",
            mime="application/json",
            key="dl_delivery_receipt",
            width="stretch",
        )

    tabs = st.tabs([f"方案 v{i}" for i in range(1, variants + 1)])
    for i, tab in enumerate(tabs, start=1):
        with tab:
            _render_review_insight_dashboard((result.get("insight_by_variant") or {}).get(i) or {}, i)
            files = result.get("artifacts", {}).get(i, {})
            if files.get("docx"):
                st.success("专业 Word 已完成：Sonnet 5 内容精修、专业落版与质量闸门均已通过。")
                st.download_button(
                    label=f"下载专业施工组织设计 v{i}.docx",
                    data=files["docx"],
                    file_name=f"autoplan_{job_id}_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_docx_{i}",
                    width="stretch",
                )
                receipt = files.get("professional_render_receipt")
                if isinstance(receipt, dict):
                    st.caption(
                        f"实际精修模型：{receipt.get('display_model') or 'Claude Sonnet 5'} "
                        f"({receipt.get('model_id') or '-'})；招标排版约束优先；章节数="
                        f"{receipt.get('section_count') or '-'}。中间稿仅供系统追溯，不对外展示。"
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
                    st.dataframe(stages, width="stretch", hide_index=True)
            variant_reference = _variant_reference_summaries_ui(result, i, runtime)
            for label, summary, id_key in [
                (
                    "案例库",
                    variant_reference.get("case_library_summary") if isinstance(variant_reference.get("case_library_summary"), dict) else {},
                    "selected_case_ids",
                ),
                (
                    "图片库",
                    variant_reference.get("image_library_summary") if isinstance(variant_reference.get("image_library_summary"), dict) else {},
                    "selected_image_ids",
                ),
            ]:
                normalized = _normalize_reference_summary_ui(summary, id_key=id_key)
                if not _reference_summary_has_content(normalized, id_key=id_key):
                    continue
                selected_ids = normalized.get(id_key) or []
                matched_project_type = str(normalized.get("matched_project_type") or "").strip() or "未命中"
                matched_chapters = [str(x).strip() for x in (normalized.get("matched_chapters") or []) if str(x).strip()]
                match_reasons = [str(x).strip() for x in (normalized.get("match_reasons") or []) if str(x).strip()]
                st.caption(
                    f"{label}：命中 {int(normalized.get('hit_count') or len(selected_ids) or 0)} 个；"
                    f"项目类型={matched_project_type}"
                    + (f"；章节={' / '.join(matched_chapters[:3])}" if matched_chapters else "")
                    + (f"；依据={' / '.join(match_reasons[:2])}" if match_reasons else "")
                )
                if selected_ids:
                    st.caption(f"{label}ID：{' / '.join(selected_ids[:6])}")
                for warning in normalized.get("warning_list") or []:
                    st.warning(f"{label}告警：{warning}")
            chapter_rows = _chapter_reference_rows_ui(result, i)
            if chapter_rows:
                table_rows = []
                for row in chapter_rows:
                    case_summary = row.get("case_library") if isinstance(row.get("case_library"), dict) else {}
                    image_summary = row.get("image_library") if isinstance(row.get("image_library"), dict) else {}
                    case_ids = [str(x).strip() for x in (case_summary.get("selected_case_ids") or []) if str(x).strip()]
                    image_ids = [str(x).strip() for x in (image_summary.get("selected_image_ids") or []) if str(x).strip()]
                    warnings = [
                        *[str(x).strip() for x in (case_summary.get("warning_list") or []) if str(x).strip()],
                        *[str(x).strip() for x in (image_summary.get("warning_list") or []) if str(x).strip()],
                    ]
                    table_rows.append(
                        {
                            "章节": str(row.get("title") or "章节"),
                            "案例命中": int(case_summary.get("hit_count") or len(case_ids) or 0),
                            "案例ID": " / ".join(case_ids[:4]),
                            "图片命中": int(image_summary.get("hit_count") or len(image_ids) or 0),
                            "图片ID": " / ".join(image_ids[:4]),
                            "告警": " / ".join(warnings[:4]),
                        }
                    )
                with st.expander("章节级参考库摘要", expanded=False):
                    st.dataframe(table_rows, width="stretch", hide_index=True)
            _render_ollama_section_review_panel(base_url, actions_key, result, i)


def _format_ratio_ui(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "待生成"


def _render_review_insight_dashboard(insight: dict[str, Any], variant: int) -> None:
    if not isinstance(insight, dict) or not insight:
        return

    st.markdown("#### 投标质量评审看板（内部质控）")
    st.caption(str(insight.get("disclaimer") or "仅供内部质量控制，不代表官方评标结论。"))
    metrics = insight.get("metrics") if isinstance(insight.get("metrics"), dict) else {}
    quality_score = metrics.get("internal_quality_score")
    quality_text = f"{float(quality_score):.0f}" if isinstance(quality_score, (int, float)) else "待生成"
    columns = st.columns(6)
    columns[0].metric("内部质量分", quality_text)
    columns[1].metric("评分点覆盖", _format_ratio_ui(metrics.get("score_coverage_ratio")))
    columns[2].metric("段落证据定位", _format_ratio_ui(metrics.get("evidence_traceability_ratio")))
    columns[3].metric("章节证据覆盖", _format_ratio_ui(metrics.get("evidence_traceability_section_ratio")))
    columns[4].metric("评分高风险", int(metrics.get("high_risk_score_item_count") or 0))
    columns[5].metric("高等级问题", int(metrics.get("high_issue_count") or 0))

    readiness_label = str(insight.get("readiness_label") or "待人工复核")
    if str(insight.get("readiness") or "") == "human_final_review":
        st.success(f"提交准备度：{readiness_label}")
    else:
        st.warning(f"提交准备度：{readiness_label}")

    paragraph_count = int(metrics.get("evidence_paragraph_count") or 0)
    traceable_paragraphs = int(metrics.get("evidence_traceable_paragraph_count") or 0)
    section_count = int(metrics.get("evidence_section_count") or 0)
    traceable_sections = int(metrics.get("evidence_traceable_section_count") or 0)
    if paragraph_count or section_count:
        st.caption(
            f"证据定位明细：段落 {traceable_paragraphs}/{paragraph_count}；"
            f"章节 {traceable_sections}/{section_count}。段落定位率低时不得用章节覆盖率替代。"
        )

    composite = insight.get("composite_score")
    if isinstance(composite, (int, float)):
        st.progress(max(0.0, min(1.0, float(composite) / 100.0)), text=f"内部综合质控 {float(composite):.1f} · {insight.get('quality_level') or '-'}")

    dimensions = insight.get("dimensions") if isinstance(insight.get("dimensions"), list) else []
    if dimensions:
        st.dataframe(
            [{"质控维度": row.get("dimension"), "状态": row.get("status")} for row in dimensions if isinstance(row, dict)],
            width="stretch",
            hide_index=True,
        )

    top_risks = insight.get("top_risks") if isinstance(insight.get("top_risks"), list) else []
    if top_risks:
        with st.expander(f"高风险评分项 · v{variant}", expanded=True):
            st.dataframe(top_risks, width="stretch", hide_index=True)

    actions = [str(item).strip() for item in (insight.get("priority_actions") or []) if str(item).strip()]
    if actions:
        with st.expander("优先整改与终审动作", expanded=True):
            for index, action in enumerate(actions, start=1):
                st.write(f"{index}. {action}")


def _cancel_active_job(base_url: str, actions_key: str) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        st.warning("当前没有可中止任务")
        return
    response = _post_json(
        base_url,
        "/actions/job_cancel",
        actions_key,
        {"job_id": job_id},
        timeout=60,
    )
    returned_status = str(response.get("status") or "cancel_requested").strip().lower()
    active["status"] = returned_status or "cancel_requested"
    st.session_state["active_job"] = active
    _persist_active_job_query(job_id)
    _append_log(f"任务已请求中止，等待工作进程确认: {job_id}")


def _collect_job_result(base_url: str, actions_key: str, job_id: str) -> dict[str, Any]:
    raw_json = _download_bytes(base_url, actions_key, job_id, "json", 1, timeout=600)
    data = json.loads(raw_json.decode("utf-8", errors="ignore"))
    variants_data = data.get("variants") or []
    variants_n = max(1, len(variants_data))

    artifacts: dict[int, dict[str, bytes]] = {}
    quality_map: dict[int, dict[str, Any]] = {}
    runtime_map: dict[int, dict[str, Any]] = {}
    insight_map: dict[int, dict[str, Any]] = {}
    from backend.zhifei_autoplan.review_insights import build_review_insight

    delivery_receipt_bytes = _download_bytes(
        base_url,
        actions_key,
        job_id,
        "delivery_receipt",
        1,
        timeout=120,
    )
    delivery_receipt = json.loads(delivery_receipt_bytes.decode("utf-8"))
    if not isinstance(delivery_receipt, dict):
        raise RuntimeError("任务级交付凭证格式无效")
    decision_digest = str(delivery_receipt.get("decision_digest") or "")
    if (
        str(delivery_receipt.get("status") or "").lower() != "pass"
        or str(delivery_receipt.get("job_id") or "") != str(job_id)
        or int(delivery_receipt.get("variant_count") or 0) != variants_n
        or len(decision_digest) != 64
    ):
        raise RuntimeError("任务级交付凭证未通过一致性校验")

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
        # A completed job is deliverable only when the professional-render
        # receipt is present and valid.  The public ``docx`` artifact above is
        # already the Sonnet-refined Word file; the deterministic source DOCX
        # is retained by the backend for audit and controlled re-rendering.
        receipt_bytes = _download_bytes(
            base_url,
            actions_key,
            job_id,
            "professional_render_receipt",
            v,
            timeout=120,
        )
        professional_receipt = json.loads(receipt_bytes.decode("utf-8"))
        if not isinstance(professional_receipt, dict):
            raise RuntimeError(f"专业 Word 渲染回执格式无效（方案 {v}）")
        quality_gate = professional_receipt.get("quality_gate")
        if (
            not isinstance(quality_gate, dict)
            or not quality_gate
            or any(value is not True for value in quality_gate.values())
        ):
            raise RuntimeError(f"专业 Word 质量门禁未通过（方案 {v}）")
        artifacts[v]["professional_render_receipt"] = professional_receipt
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
        insight_map[v] = build_review_insight(rec if isinstance(rec, dict) else {})

    return {
        "job_id": job_id,
        "variants": variants_n,
        "artifacts": artifacts,
        "quality_by_variant": quality_map,
        "runtime_by_variant": runtime_map,
        "insight_by_variant": insight_map,
        "delivery_receipt": delivery_receipt,
        "delivery_decision_digest": decision_digest,
        "result_json": raw_json,
    }


def _poll_active_job(base_url: str, actions_key: str, poll_sec: float) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        return

    js = _get_json(base_url, "/actions/job_status", actions_key, params={"job_id": job_id}, timeout=90)
    job = js.get("job") or {}
    status = str(job.get("status") or "").strip().lower()
    status = {"interrupted": "interrupted_recoverable"}.get(status, status)
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
    if status in {"queued", "running", "cancel_requested"}:
        activity_view = build_job_activity(job)
        st.markdown(activity_html(activity_view), unsafe_allow_html=True)
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
        specialist_roles = _to_int(agent_runtime.get("specialist_role_count") or 14, 14)
        if ap > 0 or vp > 0:
            st.caption(
                f"专业角色={max(1, specialist_roles)}（按任务参与）；"
                f"章节并行={max(1, ap)}，方案并行={max(1, vp)}，"
                f"完成方案={max(0, variants_done)}/{max(1, variants_total)}"
            )
        chapters = job.get("chapters") if isinstance(job.get("chapters"), dict) else progress.get("chapters") or {}
        if isinstance(chapters, dict) and int(chapters.get("total") or 0) > 0:
            st.caption(
                "章节："
                f"已启动 {int(chapters.get('started') or 0)} · "
                f"成功 {int(chapters.get('succeeded') or 0)} · "
                f"失败 {int(chapters.get('failed') or 0)} · "
                f"总计 {int(chapters.get('total') or 0)}"
            )
        provider_state = job.get("provider") if isinstance(job.get("provider"), dict) else {}
        if provider_state.get("name") or provider_state.get("model"):
            st.caption(
                f"当前模型：{provider_state.get('slot') or '-'} · "
                f"{provider_state.get('name') or '-'} / {provider_state.get('model') or '-'}"
            )
        return

    if status == "cancelled":
        _append_log(f"任务已中止: {job_id}")
        st.warning("任务已中止")
        _finish_active_job(job_id)
        return

    if status == "interrupted_recoverable":
        error = job.get("error") if isinstance(job.get("error"), dict) else {}
        st.warning(str(error.get("message") or "任务因服务中断停止，检查点已保留。"))
        if error.get("action"):
            st.caption(str(error.get("action")))
        _finish_active_job(job_id)
        return

    if status == "failed":
        error = job.get("error") if isinstance(job.get("error"), dict) else {
            "code": "RUNTIME_FAILED",
            "message": str(job.get("error") or "任务执行失败。"),
        }
        current_percent = max(0, min(99, _to_int(progress.get("percent") or 0, 0)))
        _append_log(f"任务失败: {error.get('code')} {error.get('message')}")
        _render_progress(current_percent, f"failed · {current_percent}% · {error.get('code')}")
        st.error(str(error.get("message") or "任务执行失败。"))
        if error.get("action"):
            st.caption(f"建议：{error.get('action')}")
        failures = error.get("failures") if isinstance(error.get("failures"), list) else []
        if failures:
            st.dataframe(failures, width="stretch", hide_index=True)
        _finish_active_job(job_id)
        return

    if status not in {"done", "succeeded"}:
        return

    _clear_active_job_query(job_id)
    _render_progress(100, "succeeded · 100%")
    _append_log("任务完成，开始下载结果")
    bundle = _collect_job_result(base_url, actions_key, job_id)
    bundle["project_id"] = active.get("project_id")
    st.session_state["run_result"] = bundle
    _append_log("结果下载完成")
    _finish_active_job(job_id)


def _review_cache_key(job_id: str, variant: int) -> str:
    return f"review_items_{job_id}_v{variant}"


def _review_meta_key(job_id: str, variant: int) -> str:
    return f"review_meta_{job_id}_v{variant}"


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
    st.session_state[_review_meta_key(job_id, variant)] = {
        "result_version": str(resp.get("result_version") or ""),
        "variant_version": str(resp.get("variant_version") or ""),
        "issue_digest": str(resp.get("issue_digest") or ""),
    }
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
    if c2.button("载入问题清单", key=f"load_review_{job_id}", width="stretch"):
        try:
            if not actions_key.strip():
                raise ValueError("Actions Key 不能为空")
            rows = _load_review_items(base_url, actions_key, job_id, int(variant))
            st.success(f"已载入 {len(rows)} 条问题")
        except Exception as e:
            st.error(f"载入失败: {e}")

    rows = st.session_state.get(_review_cache_key(job_id, int(variant))) or []
    review_meta = st.session_state.get(_review_meta_key(job_id, int(variant))) or {}
    if not rows:
        st.info("点击“载入问题清单”后可进行审核回写。")
        return

    st.caption(
        "勾选项将由复核模型按章节精修，随后执行全量质检；仍有问题时自动进行至多一轮二次精修并重新导出。"
        "“完整章节替换文本”仅供人工明确覆盖整章，通常请留空。"
    )

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
            "replacement": st.column_config.TextColumn("完整章节替换文本（可选）", width="large"),
        },
    )

    b1, b2 = st.columns([1, 1])
    if b1.button("应用勾选项 · AI复核精修并重编", key=f"apply_review_{job_id}_v{variant}", type="primary", width="stretch"):
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
            with st.spinner("正在执行章节精修、全量质检和二次复核，请勿关闭页面…"):
                resp = _post_json(
                    base_url,
                    "/actions/review/apply",
                    actions_key,
                    {
                        "job_id": job_id,
                        "variant": int(variant),
                        "decisions": decisions,
                        "apply_all": False,
                        "expected_result_version": review_meta.get("result_version", ""),
                        "expected_variant_version": review_meta.get("variant_version", ""),
                        "expected_issue_digest": review_meta.get("issue_digest", ""),
                        "actor": "webui",
                    },
                    timeout=900,
                )
            applied = int(resp.get("applied_count") or 0)
            ai_chapters = int(resp.get("ai_rewritten_chapter_count") or 0)
            second_round = int(resp.get("round_2_rewritten_chapter_count") or 0)
            fallback_items = int(resp.get("template_fallback_item_count") or 0)
            remaining = int(resp.get("remaining_issue_count") or 0)
            st.success(
                f"闭环完成：处理 {applied} 项，AI精修 {ai_chapters} 章，二次精修 {second_round} 章，"
                f"模板降级 {fallback_items} 项；复核后剩余问题 {remaining} 项。正在刷新产物。"
            )
            st.session_state["run_result"] = _collect_job_result(base_url, actions_key, job_id)
            _load_review_items(base_url, actions_key, job_id, int(variant))
            st.rerun()
        except Exception as e:
            _render_review_apply_error(e, prefix="回写失败")

    if b2.button("全部问题 · AI复核精修并重编", key=f"apply_all_review_{job_id}_v{variant}", width="stretch"):
        try:
            if not actions_key.strip():
                raise ValueError("Actions Key 不能为空")
            with st.spinner("正在执行全量章节精修、质检和二次复核，请勿关闭页面…"):
                resp = _post_json(
                    base_url,
                    "/actions/review/apply",
                    actions_key,
                    {
                        "job_id": job_id,
                        "variant": int(variant),
                        "apply_all": True,
                        "decisions": [],
                        "expected_result_version": review_meta.get("result_version", ""),
                        "expected_variant_version": review_meta.get("variant_version", ""),
                        "expected_issue_digest": review_meta.get("issue_digest", ""),
                        "actor": "webui",
                    },
                    timeout=900,
                )
            applied = int(resp.get("applied_count") or 0)
            ai_chapters = int(resp.get("ai_rewritten_chapter_count") or 0)
            second_round = int(resp.get("round_2_rewritten_chapter_count") or 0)
            fallback_items = int(resp.get("template_fallback_item_count") or 0)
            remaining = int(resp.get("remaining_issue_count") or 0)
            st.success(
                f"全量闭环完成：处理 {applied} 项，AI精修 {ai_chapters} 章，二次精修 {second_round} 章，"
                f"模板降级 {fallback_items} 项；复核后剩余问题 {remaining} 项。正在刷新产物。"
            )
            st.session_state["run_result"] = _collect_job_result(base_url, actions_key, job_id)
            _load_review_items(base_url, actions_key, job_id, int(variant))
            st.rerun()
        except Exception as e:
            _render_review_apply_error(e, prefix="全量回写失败")

    with st.expander("安全版本与回退", expanded=False):
        st.caption("每次回写前自动保留不可变版本；回退前也会先保存当前版本，避免误操作无法恢复。")
        try:
            revision_resp = _get_json(
                base_url,
                "/actions/review/revisions",
                actions_key,
                params={"job_id": job_id},
                timeout=60,
            )
            revisions = revision_resp.get("revisions") if isinstance(revision_resp.get("revisions"), list) else []
        except Exception as exc:
            revisions = []
            st.warning(f"版本列表暂不可用: {exc}")
        if revisions:
            revision_options = [str(row.get("revision_id") or "") for row in revisions if row.get("revision_id")]
            selected_revision = st.selectbox(
                "选择回退版本",
                revision_options,
                format_func=lambda revision_id: next(
                    (
                        f"{revision_id} · {row.get('reason', '')} · {row.get('created_at', '')}"
                        for row in revisions
                        if str(row.get("revision_id") or "") == revision_id
                    ),
                    revision_id,
                ),
                key=f"review_rollback_revision_{job_id}",
            )
            if st.button("回退到所选安全版本", key=f"review_rollback_{job_id}", width="stretch"):
                try:
                    with st.spinner("正在验证版本并重新生成专业交付 Word…"):
                        rollback_resp = _post_json(
                            base_url,
                            "/actions/review/rollback",
                            actions_key,
                            {
                                "job_id": job_id,
                                "revision_id": selected_revision,
                                "expected_result_version": review_meta.get("result_version", ""),
                                "actor": "webui",
                            },
                            timeout=900,
                        )
                    st.success(
                        f"已安全回退到 {rollback_resp.get('restored_revision_id')}；"
                        f"回退前版本保存在 {rollback_resp.get('safety_revision_id')}。"
                    )
                    st.session_state["run_result"] = _collect_job_result(base_url, actions_key, job_id)
                    _load_review_items(base_url, actions_key, job_id, int(variant))
                    st.rerun()
                except Exception as exc:
                    st.error(f"回退失败，当前 Word 未变更: {exc}")
        else:
            st.info("尚无回写前安全版本。首次应用问题清单后会自动建立。")


_init_state()
_apply_pending_widget_updates()
_inject_ui_style()

st.markdown(hero_html(), unsafe_allow_html=True)
st.markdown(workflow_html(), unsafe_allow_html=True)

# 连接参数改为系统内置，不在页面展示。
base_url = str(st.session_state.get("_base_url") or os.environ.get("ZF_BACKEND_BASE_URL", "http://127.0.0.1:8010")).strip()
actions_key = str(st.session_state.get("_actions_key") or os.environ.get("ZF_ACTIONS_KEY", "")).strip()
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

if not actions_key:
    st.error(
        "SYSTEM_ACTIONS_KEY_NOT_CONFIGURED：系统内部操作凭据尚未配置，"
        "已阻断页面请求。请从最新受监管版本重新启动系统。"
    )
    st.stop()

identity_ok, identity_msg = _backend_identity_check(base_url, expected_system_id)
if not identity_ok:
    st.error(
        "检测到当前 Web 页面连接到了其他系统后端，已阻断操作以避免两个系统互相影响。"
        f"\n\n{identity_msg}"
    )
    st.stop()

try:
    admission_response = _get_json(
        base_url,
        "/actions/provider_admission",
        actions_key,
        timeout=5,
    )
    admission_snapshot = admission_response.get("admission")
    st.session_state["_provider_admission"] = (
        admission_snapshot if isinstance(admission_snapshot, dict) else {}
    )
except Exception:
    st.session_state["_provider_admission"] = {
        "status": "unavailable",
        "generation_allowed": False,
        "degraded": False,
        "admitted_chain": [],
    }

try:
    if _restore_active_job_from_query(base_url, actions_key):
        restored_job_id = str((st.session_state.get("active_job") or {}).get("job_id") or "")
        _append_log(f"页面刷新后已恢复任务状态: {restored_job_id}")
except Exception as exc:
    recovery_error = _stable_ui_error(exc)
    _append_log(
        f"任务状态恢复暂缓[{recovery_error['code']}]: {recovery_error['message']}"
    )
    st.warning(
        f"TASK_STATE_RECOVERY_DEFERRED：{recovery_error['message']}"
        " 页面未重复提交任务；后端恢复后可刷新页面重试。"
    )

status_col, stop_col = st.columns([4, 1])
with status_col:
    top_status_holder = st.empty()
    _render_task_status(top_status_holder)
with stop_col:
    if st.button("停止/中止任务", type="secondary", width="stretch"):
        try:
            _cancel_active_job(base_url, actions_key)
            st.rerun()
        except Exception as e:
            st.error(f"中止失败: {e}")

with st.container(border=True):
    st.markdown(
        section_heading_html("01", "资料上传", "必传招标文件与工程量清单；图纸、标准资料和现场照片可选。"),
        unsafe_allow_html=True,
    )
    tender_col, boq_col, drawing_col, photo_col = st.columns(4)
    with tender_col:
        tender_files = st.file_uploader(
            "招标文件/答疑",
            type=["pdf", "doc", "docx", "txt", "md"],
            accept_multiple_files=True,
            help="支持多选。",
        )
    with boq_col:
        boq_files = st.file_uploader(
            "工程量清单",
            type=["xlsx", "xls", "pdf", "doc", "docx"],
            accept_multiple_files=True,
            help="支持多选。",
        )
    with drawing_col:
        drawing_files = st.file_uploader(
            "图纸/标准资料（含DXF ASCII）",
            type=["pdf", "doc", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "dwg", "dxf"],
            accept_multiple_files=True,
            help="支持多选。",
        )
    with photo_col:
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

with st.container(border=True):
    st.markdown(
        section_heading_html("02", "项目配置", "设置项目属性、生成版本和评审目录策略。"),
        unsafe_allow_html=True,
    )
    project_type_col, generation_mode_col, topic_col, project_id_col = st.columns(4)
    with project_type_col:
        st.selectbox("项目类型", options=PROJECT_TYPES, key="project_type")
    with generation_mode_col:
        st.selectbox(
            "编制模式",
            options=GENERATION_MODE_OPTIONS,
            key="generation_mode",
            format_func=lambda x: GENERATION_MODE_LABELS.get(str(x), str(x)),
        )
    with topic_col:
        st.text_input("项目主题", key="topic_text")
    with project_id_col:
        st.text_input("项目 ID（自动识别）", key="project_id_text")

    versions_col, pages_col, strict_outline_col = st.columns([2, 1, 1.35])
    with versions_col:
        st.multiselect(
            "版本选择（A/B/C/D/E，可多选）",
            options=LOGIC_TEMPLATE_OPTIONS,
            key="selected_templates",
        )
    sel_templates_now = _normalize_template_selection(st.session_state.get("selected_templates"))
    if not sel_templates_now:
        sel_templates_now = ["A"]
    with pages_col:
        st.number_input("总页数目标（0=按招标）", min_value=0, max_value=2000, key="total_pages_target")
    with strict_outline_col:
        st.checkbox("目录严格对标评审标准", key="strict_tender_outline")
    st.caption(
        f"当前生成 {len(sel_templates_now)} 份：{' / '.join(sel_templates_now)}。"
        "项目 ID 将在载入评审目录或启动生成时自动识别；模式1用于200页内质量优先，模式2用于500页以上高质量加速。"
    )

constraint_lines = [
    line.strip()
    for line in str(st.session_state.get("requirements_text") or "").splitlines()
    if line.strip()
]
with st.expander(
    f"编制约束 · 已启用（合规底线 + {len(constraint_lines)} 条项目要求，点击展开修改）",
    expanded=False,
):
    st.caption(
        "高级设置：系统级合规底线自动作用于全部章节；项目补充要求按行进入生成、识别与检查链路。"
        "日常使用无需展开。"
    )
    instruction_col, requirements_col = st.columns(2)
    with instruction_col:
        st.text_area("系统级合规底线（通常无需修改）", key="global_instruction", height=136)
        st.caption(
            "合规规则：不再使用固定“16条”。系统仅允许引用具有可追溯名称、编号、现行版本、"
            "生效状态和官方来源的项目适用规范；未核验规范及冲突项不得自动裁决。"
        )
    with requirements_col:
        st.text_area("项目补充编制要求（每行一条，可选）", key="requirements_text", height=120)

outline = _render_outline_editor()

# Optional tender-outline loader
c_load, c_health = st.columns([1, 1])
if c_load.button("从评审标准载入目录", width="stretch"):
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

if c_health.button("检查后端连接", width="stretch"):
    try:
        r = requests.get(base_url.rstrip("/") + "/health", timeout=20)
        if r.status_code < 400:
            st.success("后端可用")
        else:
            st.error(f"后端不可用: {r.status_code}")
    except Exception as e:
        st.error(f"连接失败: {e}")

st.markdown(
    section_heading_html("04", "排版与生成策略", "统一正文、标题、页边距和图表策略；专业参数默认收起。"),
    unsafe_allow_html=True,
)

with st.expander("专业排版设置", expanded=False):
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

    p5, p6, p7, p8 = st.columns([1.25, 1.75, 1, 2])
    with p5:
        st.selectbox(
            "行距方式（招标优先）",
            options=["fixed_pt", "multiple"],
            key="line_spacing_mode",
            format_func=lambda value: "固定值（磅）" if value == "fixed_pt" else "倍数行距",
        )
    with p6:
        if st.session_state.get("line_spacing_mode") == "multiple":
            st.number_input("行距（倍）", min_value=1.0, max_value=3.0, step=0.1, key="line_spacing_multiple")
        else:
            st.number_input("行距（磅，无要求默认22）", min_value=10.0, max_value=60.0, step=0.5, key="line_spacing_pt")
    with p7:
        st.checkbox("章节另起新页", key="chapter_start_new_page")
    with p8:
        st.checkbox("启用图表策略", key="chart_enabled")
        st.caption("自动策略：每章按篇幅选取1–2幅有效图表，全篇最多24幅；工程概况自动排除；优先使用已上传图片，不重复填充。")
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

    st.checkbox(
        "不足目标页数时强化技术内容（不补空白页）",
        key="enforce_chapter_pages",
        help=(
            "仅在章节有效内容低于目标下限时，触发一次项目相关技术深化；"
            "禁止插入空白页、重复段落、无关内容或虚构参数。"
        ),
    )
    st.caption(
        "目标页数用于内容规划和缺口提示，不作为机械凑页指标；"
        "不足时只补充施工工序、资源配置、接口协调、风险控制、检验与验收证据等有效技术内容。"
    )
    _outline_to_chapter_pages(outline)
    if outline:
        st.caption("每章页数请在“目录编辑器”中逐章设置（新增章节后可直接设置）。")

with st.expander("模型与生成策略（高级）", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.checkbox("严格质控", key="quality_strict")
        st.checkbox("自动修订", key="auto_remediate")
        st.selectbox("修订模式", options=["template", "llm"], key="remediate_mode")
        st.number_input(
            "同时编写章节数（建议4）",
            min_value=1,
            max_value=16,
            key="agent_parallelism",
            help="控制同时调用模型编写的章节数量；不是专业Agent角色数量。提高该值会增加限流和失败风险。",
        )
    with c2:
        st.checkbox(
            "生成本地图表/思维导图",
            key="generate_images",
            help="使用已导入项目图片和确定性本地绘图；不会调用未准入的外部图片模型。",
        )
        st.selectbox(
            "外部图片模型提供商",
            options=["未准入（本地确定性模式）"],
            disabled=True,
        )
        st.warning(
            "IMAGE_PROVIDER_ADMISSION_REQUIRED：外部图片模型尚未建立独立准入，"
            "因此保持关闭；文本/文档模型准入不代表图片模型已准入。"
        )
        st.number_input("方案并行数", min_value=1, max_value=5, key="variant_parallelism")
    with c3:
        main_ready, main_status = _provider_status(st.session_state.get("provider_text"))
        (st.success if main_ready else st.warning)(main_status)
        admission = st.session_state.get("_provider_admission") or {}
        route_labels = [
            f"{item.get('slot')}:{item.get('provider')}/{item.get('model')}"
            for item in (admission.get("admitted_chain") or [])
            if isinstance(item, dict)
        ]
        if route_labels:
            st.caption("服务端准入链：" + " → ".join(route_labels))
        st.info("模型、路由与凭据由本机后端统一管理；页面不读取、显示或传输密钥。")
        st.checkbox(
            "允许 Fable 5 异常升级（默认关闭）",
            key="allow_fable_escalation",
        )
    st.info(
        "14个专业角色已启用：主控、合规、招标评分响应、证据溯源、技术深度、清单响应、图纸接口、"
        "进度资源、风险闭环、图表质量、全篇一致性、专业渲染、文档视觉质检和交付验收。"
        "系统按章节与交付阶段自动调度，不需要手工增加并发。"
    )
    st.caption("并行说明：章节并行只控制同时编写的章节数；方案并行控制A/B/C/D/E多份方案是否同时生成。")

    st.markdown("**文本模型备选链（服务端管理）**")
    st.caption("主模型、备用模型、熔断与降级均以生成前准入回执为准，前端不能覆盖。")

    st.text_area("章级要求 JSON（可选）", key="chapter_requirements_text", height=100)
    st.text_area("参数覆盖 JSON（可选）", key="params_override_text", height=100)

st.markdown(
    section_heading_html("05", "知识资产与诊断工具", "案例库、图片库和本地模型预览默认收起，不干扰主编制流程。"),
    unsafe_allow_html=True,
)
_render_reference_libraries_panel(base_url, actions_key)
_render_ollama_preview_panel(base_url, actions_key)
_render_claude_cache_metrics_panel(base_url, actions_key)
current_case_library_options = _build_case_library_request_options()
current_image_library_options = _build_image_library_request_options()

st.markdown(launch_html(), unsafe_allow_html=True)
run_btn = st.button("一键生成", type="primary", width="stretch")

progress_holder = st.empty()
status_holder = st.empty()
log_holder = st.empty()

if run_btn:
    st.session_state["run_logs"] = []
    st.session_state["run_result"] = None
    _set_preflight_status(0, "正在校验输入")
    _render_task_status(top_status_holder)

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
        if st.session_state.get("line_spacing_mode") == "multiple":
            style["line_spacing"] = float(st.session_state.get("line_spacing_multiple") or 1.5)
        else:
            style["line_spacing_pt"] = float(st.session_state.get("line_spacing_pt") or 22.0)
        chapter_pages = _outline_to_chapter_pages(outline_now)

        pb = progress_holder.progress(0)
        status_holder.info("准备执行")

        def _show_ingest_progress(group_name: str, base_percent: int, span: int):
            def _callback(progress: dict[str, Any]) -> None:
                files_progress = progress.get("files") if isinstance(progress.get("files"), dict) else {}
                completed = int(files_progress.get("completed") or 0)
                total = max(1, int(files_progress.get("total") or 1))
                current_file = str(progress.get("current_file") or "").strip()
                percent = min(base_percent + span, base_percent + int((completed / total) * span))
                pb.progress(percent)
                suffix = f"：{current_file}" if current_file else ""
                status_holder.info(f"{group_name} {completed}/{total}{suffix}")
            return _callback

        _set_preflight_status(1, "导入并解析招标文件")
        _render_task_status(top_status_holder)
        _append_log("步骤 1/6: 导入并解析招标文件")
        _render_logs(log_holder)
        tender_parse_files = list(tender_files or [])
        tender_ingest = _ingest_docs(
            base_url,
            tender_parse_files,
            project_id,
            source_hint="tender_qa",
            progress_callback=_show_ingest_progress("招标/答疑导入", 0, 14),
        )
        tender_file_ids = [
            str(item.get("file_id") or item.get("sha256") or "").strip()
            for item in (tender_ingest.get("accepted") or tender_ingest.get("saved") or [])
            if isinstance(item, dict)
        ]
        if tender_ingest.get("rejected") or not tender_file_ids:
            raise RuntimeError("招标/答疑存在未解析文件，已阻止生成")
        tr = _post_file_ids(
            base_url,
            "/actions/tender/parse",
            actions_key,
            tender_file_ids,
            project_id=project_id,
        )
        matrix = tr.get("matrix") or {}
        auto_topic, auto_pid = _apply_project_defaults_from_tender(matrix)
        resolved_pid = str(tr.get("project_id") or auto_pid or project_id).strip()
        project_id = _safe_project_id(resolved_pid or project_id)
        if auto_topic:
            topic = auto_topic
            _queue_widget_update("topic_text", auto_topic)
            _append_log(f"项目主题已自动对齐：{topic}")
        if auto_pid:
            _queue_widget_update("project_id_text", project_id)
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
        _append_log("图表策略已启用：每章按篇幅选取1–2幅有效图表，全篇最多24幅；项目概况章节不插图，不重复填充。")
        pb.progress(20)

        _set_preflight_status(2, "导入并解析工程量清单")
        _render_task_status(top_status_holder)
        _append_log("步骤 2/6: 导入并解析工程量清单")
        _render_logs(log_holder)
        boq_ingest = _ingest_docs(
            base_url,
            list(boq_files),
            project_id,
            source_hint="boq",
            progress_callback=_show_ingest_progress("工程量清单导入", 20, 14),
        )
        boq_file_ids = [
            str(item.get("file_id") or item.get("sha256") or "").strip()
            for item in (boq_ingest.get("accepted") or boq_ingest.get("saved") or [])
            if isinstance(item, dict)
        ]
        if boq_ingest.get("rejected") or not boq_file_ids:
            raise RuntimeError("工程量清单存在未解析文件，已阻止生成")
        _post_file_ids(
            base_url,
            "/actions/boq/parse",
            actions_key,
            boq_file_ids,
            project_id=project_id,
        )
        pb.progress(35)

        ingest_groups = [
            ("图纸/标准资料", list(drawing_files or []), "drawing_standard"),
            ("现场照片", list(site_photo_files or []), "site_photo"),
        ]
        ingest_total = sum(len(g[1]) for g in ingest_groups)
        _set_preflight_status(3, f"入库资料（{ingest_total} 个文件）")
        _render_task_status(top_status_holder)
        _append_log(f"步骤 3/6: 入库资料 ({ingest_total} 个文件)")
        _render_logs(log_holder)
        optional_warnings: list[dict[str, Any]] = []
        for group_index, (group_name, group_files, source_hint) in enumerate(ingest_groups):
            if not group_files:
                continue
            _append_log(f"  - 入库 {group_name}：{len(group_files)} 个")
            ingest_result = _ingest_docs(
                base_url,
                group_files,
                project_id,
                source_hint=source_hint,
                progress_callback=_show_ingest_progress(group_name, 35 + group_index * 7, 7),
            )
            optional_warnings.extend(
                item for item in (ingest_result.get("warnings") or []) if isinstance(item, dict)
            )
            if ingest_result.get("rejected"):
                _append_log(f"  - {group_name} 有 {len(ingest_result.get('rejected') or [])} 个文件降级")
        if optional_warnings:
            status_holder.warning("可选资料存在降级，详情已写入运行日志")
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
            "allow_fable_escalation": bool(st.session_state.get("allow_fable_escalation", False)),
            "compare_mode": "summary",
            "compare_max_chars": int(mode_params["compare_max_chars"]),
            "compare_titles": None,
            "case_library": current_case_library_options,
            "image_library": current_image_library_options,
        }
        _set_preflight_status(4, "保存计划配置")
        _render_task_status(top_status_holder)
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
            "image_provider": str(st.session_state.get("image_provider") or "openai"),
            "image_model": str(st.session_state.get("image_model") or "gpt-image-2"),
            "style": style,
            "chapter_pages": chapter_pages,
            "chapter_requirements": chapter_requirements or {},
            "case_library": current_case_library_options,
            "image_library": current_image_library_options,
        }
        _append_log("文本模型链：由后端服务端白名单与生成前供应商准入统一决定")
        if params_override:
            generate_payload["params_override"] = params_override
        if current_case_library_options.get("enabled"):
            _append_log(
                "案例库增强已启用："
                f"top_k={current_case_library_options.get('top_k')}，"
                f"显式案例={len(current_case_library_options.get('selected_case_ids') or [])}"
            )
        if current_image_library_options.get("enabled"):
            _append_log(
                "图片库增强已启用："
                f"top_k={current_image_library_options.get('top_k')}，"
                f"显式图片={len(current_image_library_options.get('selected_image_ids') or [])}"
            )

        _set_preflight_status(5, "启动异步生成")
        _render_task_status(top_status_holder)
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
        _persist_active_job_query(job_id)
        st.session_state["preflight_status"] = None
        _render_task_status(top_status_holder)
        _append_log(f"步骤 6/6: 任务已排队 job_id={job_id}")
        _render_logs(log_holder)
        status_holder.success("任务已提交，正在后台生成")

    except Exception as e:
        public_error = _stable_ui_error(e)
        error_label = f"{public_error['code']}：{public_error['message']}"
        current_preflight = st.session_state.get("preflight_status") or {}
        _set_preflight_status(
            int(current_preflight.get("stage") or 0),
            error_label,
            state="failed",
        )
        _render_task_status(top_status_holder)
        status_holder.error(error_label)
        status_holder.caption(f"建议：{public_error['action']}")
        _append_log(f"失败[{public_error['code']}]: {public_error['message']}")

_render_logs(log_holder)

# Poll active job and update result area
if st.session_state.get("active_job"):
    try:
        _poll_active_job(base_url, actions_key, float(poll_sec))
        st.session_state["poll_fail_count"] = 0
        _render_task_status(top_status_holder)
    except Exception as e:
        fail_n = int(st.session_state.get("poll_fail_count") or 0) + 1
        st.session_state["poll_fail_count"] = fail_n
        public_error = _stable_ui_error(e)
        _append_log(f"轮询失败[{public_error['code']}]: {public_error['message']}")
        st.warning(
            f"{public_error['code']}：{public_error['message']}（自动重连第{fail_n}次）"
        )
        _render_task_status(top_status_holder)

if st.session_state.get("run_result"):
    _render_downloads(base_url, actions_key)
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
