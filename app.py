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


st.set_page_config(page_title="施组专家系统", page_icon="📄", layout="wide")


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
LATEST_GEMINI_TEXT_MODEL = "gemini-3.1-pro-preview"


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


def _ingest_docs(base_url: str, files: list[Any], project_id: str) -> dict[str, Any]:
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
    resp = requests.post(
        base_url.rstrip("/") + "/ingest/upload",
        params={"project_id": project_id},
        files=payload,
        timeout=900,
    )
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


def _init_state() -> None:
    defaults = {
        "topic_text": "施工组织设计方案",
        "project_id_text": "",
        "project_type": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "variants_value": 1,
        "global_instruction": "严格遵守最新16条行业规定；所有工序采用A/B/C结构表达。",
        "requirements_text": "严格按技术文件详细评审标准中的章目录组织内容，不新增顶层章节\n每节输出量化指标与风险-控制-验证闭环\n全文禁止官话、套话、空话",
        "outline_items": [],
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": "template",
        "generate_images": False,
        "image_provider": "google",
        "image_model": "banana",
        "provider_text": "google",
        "model_text": LATEST_GEMINI_TEXT_MODEL,
        "api_key_text": "",
        "chapter_requirements_text": "",
        "params_override_text": "",
        "template_key": PROJECT_TYPES[0] if PROJECT_TYPES else "",
        "strict_tender_outline": True,
        "body_font": "宋体",
        "title_font": "宋体",
        "body_size": 12,
        "title_size": 16,
        "line_spacing_pt": 22.0,
        "enforce_chapter_pages": False,
        "chapter_start_new_page": False,
        "chart_enabled": True,
        "chart_every_n": 2,
        "chart_position": "chapter",
        "auto_refresh": True,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    if PROJECT_TYPES and st.session_state.get("project_type") not in PROJECT_TYPES:
        st.session_state["project_type"] = PROJECT_TYPES[0]
    if st.session_state.get("body_font") not in {"宋体", "仿宋体"}:
        st.session_state["body_font"] = "宋体"
    if st.session_state.get("title_font") not in {"宋体", "仿宋体"}:
        st.session_state["title_font"] = "宋体"
    valid_templates = list(TEMPLATE_LIBRARY.keys())
    if valid_templates and st.session_state.get("template_key") not in valid_templates:
        st.session_state["template_key"] = valid_templates[0]
    st.session_state.setdefault("run_logs", [])
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault("active_job", None)
    st.session_state.setdefault("chapter_page_map", {})


def _set_outline_items(items: list[str]) -> None:
    st.session_state["outline_items"] = [str(x).strip() for x in items if str(x).strip()]


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

    if not items:
        st.info("目录为空。可先点击“从评审标准载入目录”，或手动新增章节。")

    action = None
    for i, val in enumerate(items):
        c1, c2, c3, c4 = st.columns([9, 1, 1, 1])
        new_val = c1.text_input(f"第{i + 1}章", value=val, key=f"outline_item_{i}")
        items[i] = new_val.strip()
        if c2.button("↑", key=f"outline_up_{i}"):
            action = ("up", i)
        if c3.button("↓", key=f"outline_down_{i}"):
            action = ("down", i)
        if c4.button("✕", key=f"outline_del_{i}"):
            action = ("del", i)

    c_add, c_clear = st.columns([1, 1])
    if c_add.button("新增章节", use_container_width=True):
        items.append("")
        st.session_state["outline_items"] = items
        st.rerun()
    if c_clear.button("清空目录", use_container_width=True):
        st.session_state["outline_items"] = []
        st.rerun()

    if action:
        typ, idx = action
        if typ == "up" and idx > 0:
            items[idx - 1], items[idx] = items[idx], items[idx - 1]
        elif typ == "down" and idx < len(items) - 1:
            items[idx + 1], items[idx] = items[idx], items[idx + 1]
        elif typ == "del" and 0 <= idx < len(items):
            items.pop(idx)
        st.session_state["outline_items"] = items
        st.rerun()

    st.session_state["outline_items"] = items
    return [x for x in items if x]


def _outline_to_chapter_pages(outline: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    m = st.session_state.get("chapter_page_map") or {}
    for title in outline:
        key = f"cp_{title}"
        if key not in st.session_state:
            st.session_state[key] = int(m.get(title) or 2)
        out[title] = int(st.session_state.get(key) or 2)
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
            q = (result.get("quality_by_variant") or {}).get(i) or {}
            if q:
                st.json(q)


def _cancel_active_job(base_url: str, actions_key: str) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        st.warning("当前没有可中止任务")
        return
    _post_json(base_url, "/actions/job_cancel", actions_key, {"job_id": job_id}, timeout=60)
    _append_log(f"任务已请求中止: {job_id}")
    st.session_state["active_job"] = None


def _poll_active_job(base_url: str, actions_key: str, poll_sec: float) -> None:
    active = st.session_state.get("active_job") or {}
    job_id = str(active.get("job_id") or "").strip()
    if not job_id:
        return

    js = _get_json(base_url, "/actions/job_status", actions_key, params={"job_id": job_id}, timeout=90)
    job = js.get("job") or {}
    status = str(job.get("status") or "")
    st.session_state["active_job"]["status"] = status

    st.info(f"任务状态：{status}（job_id={job_id}）")
    if status in {"queued", "running"}:
        if st.button("刷新进度", key="refresh_progress", use_container_width=True):
            st.rerun()
        return

    if status == "cancelled":
        _append_log(f"任务已中止: {job_id}")
        st.warning("任务已中止")
        st.session_state["active_job"] = None
        return

    if status == "failed":
        _append_log(f"任务失败: {job.get('error')}")
        st.error(f"任务失败: {job.get('error')}")
        st.session_state["active_job"] = None
        return

    if status != "done":
        return

    _append_log("任务完成，开始下载结果")
    raw_json = _download_bytes(base_url, actions_key, job_id, "json", 1, timeout=600)
    data = json.loads(raw_json.decode("utf-8", errors="ignore"))
    variants_data = data.get("variants") or []
    variants_n = max(1, len(variants_data))

    artifacts: dict[int, dict[str, bytes]] = {}
    quality_map: dict[int, dict[str, Any]] = {}
    for v in range(1, variants_n + 1):
        artifacts[v] = {}
        artifacts[v]["docx"] = _download_bytes(base_url, actions_key, job_id, "docx", v, timeout=600)
        artifacts[v]["compare_docx"] = _download_bytes(base_url, actions_key, job_id, "compare_docx", v, timeout=600)
        try:
            artifacts[v]["focus_xlsx"] = _download_bytes(base_url, actions_key, job_id, "focus_xlsx", v, timeout=600)
        except Exception:
            pass
        rec = variants_data[v - 1] if v <= len(variants_data) else {}
        qc = rec.get("quality_checks") or {}
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
        }

    st.session_state["run_result"] = {
        "job_id": job_id,
        "project_id": active.get("project_id"),
        "variants": variants_n,
        "artifacts": artifacts,
        "quality_by_variant": quality_map,
        "result_json": raw_json,
    }
    _append_log("结果下载完成")
    st.session_state["active_job"] = None


_init_state()
_apply_pending_widget_updates()

st.title("施组专家系统")
st.caption("Gemini 大脑 + 行业知识图谱 | 评审标准目录驱动 | A/B/C差异化编制")

with st.sidebar:
    st.header("连接配置")
    base_url = st.text_input("后端地址", value=os.environ.get("ZF_BACKEND_BASE_URL", "http://127.0.0.1:8010"))
    actions_key = st.text_input("Actions Key", value=os.environ.get("ZF_ACTIONS_KEY", ""), type="password")
    poll_sec = st.number_input("轮询间隔(秒)", min_value=1.0, max_value=20.0, value=2.0, step=1.0)
    st.session_state["auto_refresh"] = st.checkbox("实时轮询", value=bool(st.session_state.get("auto_refresh", True)))

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
    st.subheader("文件上传区")
    tender_files = st.file_uploader(
        "招标文件（可多选）",
        type=["pdf", "doc", "docx", "txt", "md"],
        accept_multiple_files=True,
    )
    boq_files = st.file_uploader(
        "工程量清单（可多选）",
        type=["xlsx", "xls", "pdf", "doc", "docx"],
        accept_multiple_files=True,
    )
    drawing_files = st.file_uploader(
        "图纸/补遗/标准资料（可多选，支持DXF ASCII）",
        type=["pdf", "doc", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "dwg", "dxf"],
        accept_multiple_files=True,
    )

with col_right:
    st.subheader("参数配置区")
    template_keys = [x for x in PROJECT_TYPES if x in TEMPLATE_LIBRARY]
    if not template_keys:
        template_keys = list(TEMPLATE_LIBRARY.keys())
    st.selectbox(
        "方案模板库",
        options=template_keys,
        format_func=lambda x: TEMPLATE_LIBRARY.get(x, {}).get("label", x),
        key="template_key",
    )
    st.caption(TEMPLATE_LIBRARY.get(st.session_state.get("template_key"), {}).get("desc", ""))
    if st.button("应用模板", use_container_width=True):
        _apply_template(st.session_state.get("template_key") or (PROJECT_TYPES[0] if PROJECT_TYPES else ""))
        st.rerun()

    st.selectbox("项目类型", options=PROJECT_TYPES, key="project_type")
    st.text_input("项目主题", key="topic_text")
    st.text_input("项目ID（自动取招标文件项目编号）", key="project_id_text")
    st.slider("生成份数（A/B/C轮转）", min_value=1, max_value=3, key="variants_value")
    st.checkbox("目录严格对标评审标准（运行时覆盖当前目录）", key="strict_tender_outline")

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
            raise ValueError("请先上传招标文件")
        pid_seed = str(st.session_state.get("project_id_text") or st.session_state.get("topic_text") or "").strip()
        pid = _safe_project_id(pid_seed)
        tr = _post_files(
            base_url,
            "/actions/tender/parse",
            actions_key,
            "files",
            list(tender_files),
            params={"project_id": pid},
            timeout=900,
        )
        matrix = tr.get("matrix") or {}
        auto_topic, auto_pid = _apply_project_defaults_from_tender(matrix)
        resolved_pid = str(tr.get("project_id") or auto_pid or pid).strip()
        pending_widget_patch = False
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
            _set_outline_items([str(x) for x in ol if str(x).strip()])
            _append_log("已从评审标准载入目录")
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
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("正文中文字体", options=["宋体", "仿宋体"], key="body_font")
        st.number_input("正文字号", min_value=9, max_value=24, key="body_size")
        st.number_input("行距（磅）", min_value=10.0, max_value=60.0, step=0.5, key="line_spacing_pt")
    with c2:
        st.selectbox("标题中文字体", options=["宋体", "仿宋体"], key="title_font")
        st.number_input("标题字号", min_value=10, max_value=36, key="title_size")
        st.checkbox("章节另起新页", key="chapter_start_new_page")
    with c3:
        st.checkbox("启用图表策略", key="chart_enabled")
        st.number_input("图表分布频率（每N章）", min_value=1, max_value=10, key="chart_every_n")
        st.selectbox("图表位置", options=["chapter", "end"], key="chart_position", format_func=lambda x: "按章节插入" if x == "chapter" else "文末集中")

    st.checkbox("按目标页数强制填充", key="enforce_chapter_pages")
    chapter_pages_map = _outline_to_chapter_pages(outline)
    if outline:
        st.markdown("**每章目标页数**")
        for title in outline:
            key = f"cp_{title}"
            st.number_input(f"{title}", min_value=1, max_value=80, key=key)

with st.expander("高级参数（可选）", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.checkbox("严格质控", key="quality_strict")
        st.checkbox("自动修订", key="auto_remediate")
        st.selectbox("修订模式", options=["template", "llm"], key="remediate_mode")
    with c2:
        st.checkbox("生成图片/思维导图", key="generate_images")
        st.text_input("图片模型提供商", key="image_provider")
        st.text_input("图片模型", key="image_model")
    with c3:
        st.text_input("文本模型提供商", key="provider_text")
        st.text_input("文本模型", key="model_text")
        if str(st.session_state.get("provider_text") or "").strip().lower() == "google":
            st.caption(f"建议：使用 {LATEST_GEMINI_TEXT_MODEL}（Gemini 3 系列）")
        st.text_input("文本模型 API Key", key="api_key_text", type="password")

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
            raise ValueError("请至少上传 1 个招标文件")
        if not boq_files:
            raise ValueError("请至少上传 1 个工程量清单文件")

        topic = (st.session_state.get("topic_text") or "施工组织设计方案").strip()
        project_id = _safe_project_id(st.session_state.get("project_id_text") or topic)
        requirements = [x.strip() for x in (st.session_state.get("requirements_text") or "").splitlines() if x.strip()]
        global_instruction = str(st.session_state.get("global_instruction") or "").strip()
        project_type = str(st.session_state.get("project_type") or "").strip()
        outline_now = _current_outline()

        chapter_requirements = _parse_json_text("章级要求 JSON", st.session_state.get("chapter_requirements_text") or "")
        params_override = _parse_json_text("参数覆盖 JSON", st.session_state.get("params_override_text") or "")

        style = {
            "body_font": st.session_state.get("body_font"),
            "title_font": st.session_state.get("title_font"),
            "body_size": int(st.session_state.get("body_size") or 12),
            "title_size": int(st.session_state.get("title_size") or 16),
            "line_spacing_pt": float(st.session_state.get("line_spacing_pt") or 22.0),
            "chapter_start_new_page": bool(st.session_state.get("chapter_start_new_page")),
            "enforce_chapter_pages": bool(st.session_state.get("enforce_chapter_pages")),
            "chart_policy": {
                "enabled": bool(st.session_state.get("chart_enabled")),
                "every_n_chapters": int(st.session_state.get("chart_every_n") or 2),
                "position": str(st.session_state.get("chart_position") or "chapter"),
            },
        }
        chapter_pages = {t: int(st.session_state.get(f"cp_{t}") or 2) for t in outline_now if t.strip()}

        pb = progress_holder.progress(0)
        status_holder.info("准备执行")

        _append_log("步骤 1/6: 解析招标文件")
        _render_logs(log_holder)
        tr = _post_files(
            base_url,
            "/actions/tender/parse",
            actions_key,
            "files",
            list(tender_files),
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
        auto_outline = matrix.get("outline") if isinstance(matrix, dict) else []
        if isinstance(auto_outline, list) and auto_outline:
            parsed_outline = [str(x) for x in auto_outline if str(x).strip()]
            if bool(st.session_state.get("strict_tender_outline")):
                _set_outline_items(parsed_outline)
                outline_now = _current_outline()
                _append_log("目录已按评审标准强制对标覆盖")
            elif not outline_now:
                _set_outline_items(parsed_outline)
                outline_now = _current_outline()
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

        ingest_all = list(tender_files) + list(boq_files or []) + list(drawing_files or [])
        _append_log(f"步骤 3/6: 入库资料 ({len(ingest_all)} 个文件)")
        _render_logs(log_holder)
        _ingest_docs(base_url, ingest_all, project_id)
        pb.progress(50)

        plan_payload: dict[str, Any] = {
            "outline": outline_now,
            "style": style,
            "project_type": project_type,
            "global_instruction": global_instruction,
            "variants": int(st.session_state.get("variants_value") or 1),
            "chapter_requirements": chapter_requirements or {},
            "chapter_pages": chapter_pages,
            "quality_strict": bool(st.session_state.get("quality_strict")),
            "auto_remediate": bool(st.session_state.get("auto_remediate")),
            "remediate_mode": st.session_state.get("remediate_mode") or "template",
            "compare_mode": "summary",
            "compare_max_chars": 1200,
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
            "global_instruction": global_instruction,
            "outline": outline_now,
            "requirements": requirements,
            "variants": int(st.session_state.get("variants_value") or 1),
            "quality_strict": bool(st.session_state.get("quality_strict")),
            "auto_remediate": bool(st.session_state.get("auto_remediate")),
            "remediate_mode": st.session_state.get("remediate_mode") or "template",
            "compare_mode": "summary",
            "compare_max_chars": 1200,
            "generate_images": bool(st.session_state.get("generate_images")),
            "image_provider": str(st.session_state.get("image_provider") or "google"),
            "image_model": str(st.session_state.get("image_model") or "banana"),
            "style": style,
            "chapter_pages": chapter_pages,
            "chapter_requirements": chapter_requirements or {},
        }
        provider = str(st.session_state.get("provider_text") or "").strip()
        model = str(st.session_state.get("model_text") or "").strip()
        api_key = str(st.session_state.get("api_key_text") or "").strip()
        if provider:
            generate_payload["provider"] = provider
        if model:
            generate_payload["model"] = model
        if api_key:
            generate_payload["api_key"] = api_key
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
            "variants": int(st.session_state.get("variants_value") or 1),
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
    except Exception as e:
        _append_log(f"轮询失败: {e}")
        st.error(f"轮询失败: {e}")

if st.session_state.get("run_result"):
    _render_downloads()
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
