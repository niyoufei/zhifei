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


st.set_page_config(page_title="文档生成系统", page_icon="📄", layout="wide")


TEMPLATE_LIBRARY: dict[str, dict[str, Any]] = {
    "custom": {
        "label": "自定义（不覆盖）",
        "desc": "不替换现有输入，按你当前手工配置生成。",
        "topic_hint": "施工组织设计方案",
        "requirements": [],
        "outline": [],
        "chapter_requirements": {},
        "params_override": {},
        "style": {},
    },
    "road": {
        "label": "道路工程",
        "desc": "道路/排水/交通配套工程，强调路基路面工序、交通导改和线性施工组织。",
        "topic_hint": "道路工程施工组织设计方案",
        "requirements": [
            "重点章节覆盖路基处理、排水、路面结构层、交安与导改。",
            "量化参数必须包含压实度、平整度、厚度、碾压遍数、养护时长。",
            "每节必须给出风险-控制-验证闭环与记录表单。",
        ],
        "outline": [
            "工程概况与实施路径",
            "施工总体部署与交通组织",
            "主要施工方案与工序安排",
            "资源配置计划（人员/机械/材料）",
            "质量管理与检验试验计划",
            "安全管理与应急预案",
            "文明施工与绿色工地",
            "信息化管理与资料归档",
        ],
        "chapter_requirements": {
            "主要施工方案与工序安排": "按路基->基层->面层->附属设施顺序组织，写清工序衔接间隔、机械组合、班组配置。",
            "质量管理与检验试验计划": "列出压实度、弯沉、平整度、厚度、强度等指标与抽检频次。",
        },
        "params_override": {
            "quant_defaults": {
                "频次": "3次/日",
                "阈值": "偏差≤5mm",
                "间距": "50m",
                "厚度": "18cm",
                "时长": "6h/作业段",
                "人数": "12人/班",
                "设备型号": "20t压路机1台",
            },
            "qse_defaults": {
                "PM10阈值": "≤120ug/m3",
                "昼间噪声阈值": "≤70dB",
                "夜间噪声阈值": "≤55dB",
            },
        },
        "style": {},
    },
    "bridge": {
        "label": "桥梁工程",
        "desc": "桥梁/构造物工程，强调桩基、下部结构、预应力与架设安全。",
        "topic_hint": "桥梁工程施工组织设计方案",
        "requirements": [
            "重点章节覆盖桩基、承台墩柱、梁体架设与桥面系。",
            "关键控制点必须量化：轴线偏位、标高、张拉力、压浆饱满度、吊装工况。",
            "高风险作业必须给出专项风险闭环和停复工条件。",
        ],
        "outline": [
            "工程概况与桥型特征",
            "总体施工组织与分段安排",
            "桩基及下部结构施工方案",
            "上部结构施工与架设方案",
            "质量控制与监测方案",
            "安全管理与专项应急",
            "文明环保与水土保持",
            "信息化与测量监控管理",
        ],
        "chapter_requirements": {
            "上部结构施工与架设方案": "明确架桥机/吊车工况、临边防护、作业窗口、测量复核流程。",
            "质量控制与监测方案": "给出张拉压浆、线形控制、应力监测与复测频次。",
        },
        "params_override": {
            "quant_defaults": {
                "频次": "2次/班",
                "阈值": "偏差≤3mm",
                "间距": "1.5m",
                "厚度": "80mm",
                "时长": "8h/作业段",
                "人数": "16人/班",
                "设备型号": "80t汽车吊1台",
            },
            "qse_defaults": {
                "PM10阈值": "≤120ug/m3",
                "昼间噪声阈值": "≤70dB",
                "夜间噪声阈值": "≤55dB",
            },
        },
        "style": {},
    },
    "water": {
        "label": "水利工程",
        "desc": "水利/河道/泵站工程，强调导流度汛、防渗防冲、监测与应急。",
        "topic_hint": "水利工程施工组织设计方案",
        "requirements": [
            "重点章节覆盖导流与度汛、基坑防渗、主体结构与机电安装。",
            "关键参数量化：围堰高程、渗压变化、沉降速率、混凝土温控与养护。",
            "施工期防洪防汛和环保措施必须闭环到责任岗位与响应时限。",
        ],
        "outline": [
            "工程概况与水文地质条件",
            "导流度汛与施工总布置",
            "土建主体施工方案",
            "机电设备安装与调试方案",
            "质量控制与监测计划",
            "安全生产与防汛应急",
            "文明施工与生态环保",
            "信息化管理与资料追溯",
        ],
        "chapter_requirements": {
            "导流度汛与施工总布置": "明确导流标准、围堰控制高程、预警阈值与撤离机制。",
            "质量控制与监测计划": "量化渗压、沉降、变形、温控等监测项目与频次。",
        },
        "params_override": {
            "quant_defaults": {
                "频次": "3次/班",
                "阈值": "渗压变化≤10%",
                "间距": "2m",
                "厚度": "30cm",
                "时长": "8h/作业段",
                "人数": "14人/班",
                "设备型号": "150kW水泵2台",
            },
            "qse_defaults": {
                "PM10阈值": "≤120ug/m3",
                "昼间噪声阈值": "≤70dB",
                "夜间噪声阈值": "≤55dB",
            },
        },
        "style": {},
    },
}


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _safe_project_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        s = datetime.now().strftime("project_%Y%m%d_%H%M%S")
    s = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", s).strip("_")
    return s[:96] or datetime.now().strftime("project_%Y%m%d_%H%M%S")


def _headers(actions_key: str) -> dict[str, str]:
    return {"X-Actions-Key": actions_key.strip()}


def _json_text(obj: dict[str, Any]) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, indent=2)


def _init_form_state() -> None:
    defaults = {
        "topic_text": "施工组织设计方案",
        "project_id_text": "",
        "variants_value": 3,
        "requirements_text": "严格按招标目录组织内容，不新增顶层章节\n每节输出量化指标与风险-控制-验证闭环\n全文禁止官话、套话、空话",
        "outline_text": "",
        "quality_strict": True,
        "auto_remediate": True,
        "remediate_mode": "template",
        "generate_images": False,
        "image_provider": "google",
        "image_model": "banana",
        "provider_text": "",
        "model_text": "",
        "api_key_text": "",
        "chapter_pages_text": "",
        "chapter_requirements_text": "",
        "style_text": "",
        "params_override_text": "",
        "template_key": "custom",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _apply_template_to_form(template_key: str) -> None:
    tpl = TEMPLATE_LIBRARY.get(template_key) or TEMPLATE_LIBRARY["custom"]
    if template_key == "custom":
        return

    st.session_state["requirements_text"] = "\n".join(tpl.get("requirements") or [])
    st.session_state["outline_text"] = "\n".join(tpl.get("outline") or [])
    st.session_state["chapter_requirements_text"] = _json_text(tpl.get("chapter_requirements") or {})
    st.session_state["params_override_text"] = _json_text(tpl.get("params_override") or {})
    st.session_state["style_text"] = _json_text(tpl.get("style") or {})

    topic = (st.session_state.get("topic_text") or "").strip()
    if not topic or topic == "施工组织设计方案":
        st.session_state["topic_text"] = str(tpl.get("topic_hint") or "施工组织设计方案")


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
        data = uf.getvalue()
        files.append((field, (uf.name, data, "application/octet-stream")))
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
    container.code("\n".join(logs[-200:]), language="text")


def _render_downloads() -> None:
    result = st.session_state.get("run_result") or {}
    if not result:
        return

    st.subheader("结果下载")
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
                )
            if files.get("compare_docx"):
                st.download_button(
                    label=f"下载对照稿 v{i}.docx",
                    data=files["compare_docx"],
                    file_name=f"autoplan_{job_id}_compare_v{i}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_cmp_{i}",
                )
            if files.get("focus_xlsx"):
                st.download_button(
                    label=f"下载问题清单+自动修订建议 v{i}.xlsx",
                    data=files["focus_xlsx"],
                    file_name=f"autoplan_{job_id}_focus_v{i}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{i}",
                )

            q = (result.get("quality_by_variant") or {}).get(i) or {}
            if q:
                st.json(q)


st.title("施工组织设计智能编制 Web 控制台")
st.caption("上传招标资料 -> 参数配置 -> 一键生成 -> 在线下载 DOCX")
_init_form_state()

with st.sidebar:
    st.header("连接配置")
    base_url = st.text_input("后端地址", value=os.environ.get("ZF_BACKEND_BASE_URL", "http://127.0.0.1:8010"))
    actions_key = st.text_input("Actions Key", value=os.environ.get("ZF_ACTIONS_KEY", ""), type="password")
    poll_sec = st.number_input("轮询间隔(秒)", min_value=1.0, max_value=20.0, value=2.0, step=1.0)

    if st.button("检查后端连接", use_container_width=True):
        try:
            r = requests.get(base_url.rstrip("/") + "/health", timeout=15)
            if r.status_code < 400:
                st.success("后端可用")
            else:
                st.error(f"后端不可用: {r.status_code}")
        except Exception as e:
            st.error(f"后端连接失败: {e}")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("文件上传区")
    tender_files = st.file_uploader(
        "招标文件（可多选）",
        type=["pdf", "doc", "docx", "txt", "md"],
        accept_multiple_files=True,
    )
    boq_file = st.file_uploader(
        "工程量清单（单个）",
        type=["xlsx", "xls", "pdf", "doc", "docx"],
        accept_multiple_files=False,
    )
    drawing_files = st.file_uploader(
        "图纸/补遗/标准资料（可多选）",
        type=["pdf", "doc", "docx", "xlsx", "xls", "png", "jpg", "jpeg", "dwg", "dxf"],
        accept_multiple_files=True,
    )

with col_right:
    st.subheader("参数配置区")
    st.markdown("#### 方案模板库")
    template_keys = list(TEMPLATE_LIBRARY.keys())
    template_key = st.selectbox(
        "工程类型模板",
        options=template_keys,
        format_func=lambda x: TEMPLATE_LIBRARY.get(x, {}).get("label", x),
        key="template_key",
    )
    st.caption(TEMPLATE_LIBRARY.get(template_key, {}).get("desc", ""))
    if st.button("应用模板", use_container_width=True, key="apply_template_btn"):
        _apply_template_to_form(template_key)
        st.success(f"已应用模板：{TEMPLATE_LIBRARY.get(template_key, {}).get('label', template_key)}")
        st.rerun()

    topic = st.text_input("项目主题", key="topic_text")
    project_id_input = st.text_input("项目ID（可留空自动生成）", key="project_id_text")
    variants = st.slider("生成份数（A/B/C轮转）", min_value=1, max_value=3, key="variants_value")
    requirements_text = st.text_area(
        "编制要求（每行一条）",
        key="requirements_text",
        height=120,
    )
    outline_text = st.text_area("章节目录（可选，每行一章）", key="outline_text", height=100)

with st.expander("高级参数（可选）", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        quality_strict = st.checkbox("严格质控", key="quality_strict")
        auto_remediate = st.checkbox("自动修订", key="auto_remediate")
        remediate_mode = st.selectbox("修订模式", options=["template", "llm"], key="remediate_mode")
    with c2:
        generate_images = st.checkbox("生成图片/思维导图", key="generate_images")
        image_provider = st.text_input("图片模型提供商", key="image_provider")
        image_model = st.text_input("图片模型", key="image_model")
    with c3:
        provider = st.text_input("文本模型提供商（可选）", key="provider_text")
        model = st.text_input("文本模型（可选）", key="model_text")
        api_key = st.text_input("文本模型 API Key（可选）", key="api_key_text", type="password")
    chapter_pages_text = st.text_area("章节页数 JSON（可选）", key="chapter_pages_text", height=100)
    chapter_requirements_text = st.text_area("章级要求 JSON（可选）", key="chapter_requirements_text", height=100)
    style_text = st.text_area("样式 JSON（可选）", key="style_text", height=80)
    params_override_text = st.text_area("参数覆盖 JSON（可选）", key="params_override_text", height=100)

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
        if boq_file is None:
            raise ValueError("请上传工程量清单文件")

        project_id = _safe_project_id(project_id_input or topic)
        requirements = [x.strip() for x in (requirements_text or "").splitlines() if x.strip()]
        outline = [x.strip() for x in (outline_text or "").splitlines() if x.strip()]

        chapter_pages = _parse_json_text("章节页数 JSON", chapter_pages_text)
        chapter_requirements = _parse_json_text("章级要求 JSON", chapter_requirements_text)
        style = _parse_json_text("样式 JSON", style_text)
        params_override = _parse_json_text("参数覆盖 JSON", params_override_text)

        pb = progress_holder.progress(0)
        status_holder.info("准备执行")

        _append_log("步骤 1/8: 解析招标文件")
        _render_logs(log_holder)
        _post_files(
            base_url,
            "/actions/tender/parse",
            actions_key,
            "files",
            list(tender_files),
            params={"project_id": project_id},
            timeout=900,
        )
        pb.progress(12)

        _append_log("步骤 2/8: 解析工程量清单")
        _render_logs(log_holder)
        _post_files(
            base_url,
            "/actions/boq/parse",
            actions_key,
            "file",
            [boq_file],
            params={"project_id": project_id},
            timeout=900,
        )
        pb.progress(25)

        ingest_all = list(tender_files) + [boq_file] + list(drawing_files or [])
        _append_log(f"步骤 3/8: 入库资料与图纸 ({len(ingest_all)} 个文件)")
        _render_logs(log_holder)
        _ingest_docs(base_url, ingest_all, project_id)
        pb.progress(38)

        plan_payload: dict[str, Any] = {
            "outline": outline,
            "style": style or {},
            "variants": int(variants),
            "chapter_requirements": chapter_requirements or {},
            "chapter_pages": chapter_pages or {},
            "quality_strict": bool(quality_strict),
            "auto_remediate": bool(auto_remediate),
            "remediate_mode": remediate_mode,
            "compare_mode": "summary",
            "compare_max_chars": 1200,
            "compare_titles": None,
        }
        _append_log("步骤 4/8: 保存项目计划配置")
        _render_logs(log_holder)
        _post_json(base_url, "/actions/plan/save", actions_key, plan_payload, params={"project_id": project_id})
        pb.progress(48)

        generate_payload: dict[str, Any] = {
            "topic": topic.strip() or "施工组织设计方案",
            "project_id": project_id,
            "outline": outline,
            "requirements": requirements,
            "variants": int(variants),
            "quality_strict": bool(quality_strict),
            "auto_remediate": bool(auto_remediate),
            "remediate_mode": remediate_mode,
            "compare_mode": "summary",
            "compare_max_chars": 1200,
            "generate_images": bool(generate_images),
            "image_provider": image_provider.strip() or None,
            "image_model": image_model.strip() or None,
        }
        if provider.strip():
            generate_payload["provider"] = provider.strip()
        if model.strip():
            generate_payload["model"] = model.strip()
        if api_key.strip():
            generate_payload["api_key"] = api_key.strip()
        if style:
            generate_payload["style"] = style
        if chapter_pages:
            generate_payload["chapter_pages"] = chapter_pages
        if chapter_requirements:
            generate_payload["chapter_requirements"] = chapter_requirements
        if params_override:
            generate_payload["params_override"] = params_override

        _append_log("步骤 5/8: 启动异步生成任务")
        _render_logs(log_holder)
        job = _post_json(base_url, "/actions/generate_async", actions_key, generate_payload, timeout=180)
        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError("生成任务未返回 job_id")
        pb.progress(58)

        _append_log(f"步骤 6/8: 轮询任务状态 job_id={job_id}")
        _render_logs(log_holder)
        status_holder.info(f"任务执行中：{job_id}")

        start = time.time()
        timeout_sec = 60 * 90
        last_status = "queued"
        while True:
            js = _get_json(base_url, "/actions/job_status", actions_key, params={"job_id": job_id}, timeout=90)
            job_obj = js.get("job") or {}
            status = str(job_obj.get("status") or "")
            if status and status != last_status:
                _append_log(f"状态更新: {status}")
                _render_logs(log_holder)
                last_status = status

            elapsed = time.time() - start
            if status == "done":
                pb.progress(90)
                _append_log("步骤 7/8: 任务完成，读取结果")
                _render_logs(log_holder)
                break
            if status == "failed":
                raise RuntimeError(f"任务失败: {job_obj.get('error')}")
            if elapsed > timeout_sec:
                raise TimeoutError("任务超时")

            p = min(88, 58 + int(elapsed / max(2, poll_sec) * 2))
            pb.progress(max(58, p))
            time.sleep(float(poll_sec))

        # Download artifacts
        status_holder.info("下载生成文件中…")
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

        pb.progress(100)
        _append_log("步骤 8/8: 下载完成，可直接导出 DOCX")
        _render_logs(log_holder)
        status_holder.success("编制完成")

        st.session_state["run_result"] = {
            "job_id": job_id,
            "project_id": project_id,
            "variants": variants_n,
            "artifacts": artifacts,
            "quality_by_variant": quality_map,
            "result_json": raw_json,
        }

    except Exception as e:
        status_holder.error(f"执行失败: {e}")
        _append_log(f"失败: {e}")
        _render_logs(log_holder)

if st.session_state.get("run_result"):
    _render_downloads()
    with st.expander("JSON 结果", expanded=False):
        raw = st.session_state["run_result"].get("result_json") or b"{}"
        try:
            st.json(json.loads(raw.decode("utf-8", errors="ignore")))
        except Exception:
            st.text(raw.decode("utf-8", errors="ignore"))
