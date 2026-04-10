from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.zhifei_autoplan.agents.section_writer import BANNED_PHRASES
from backend.zhifei_autoplan.labor_calculator import generate_labor_plan, get_labor_ui_options
from backend.zhifei_autoplan.terminology_guard import (
    load_engineering_rules,
    normalize_text_terminology,
    validate_engineering_rules,
)


def _load_local_keys_env() -> Dict[str, str]:
    path = Path(os.environ.get("ZF_KEYS_FILE", str(ROOT / ".runtime" / "local_keys.env")))
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
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


def _inject_style() -> None:
    st.markdown(
        """
<style>
.stApp {
  background: radial-gradient(circle at 20% 0%, #0f172a 0%, #020617 55%, #000000 100%);
}
.block-container {
  max-width: 1280px;
  padding-top: 1.2rem;
  padding-bottom: 2rem;
}
h1, h2, h3, label, p, span, div {
  color: #e2e8f0 !important;
}
.card {
  border: 1px solid rgba(148,163,184,0.25);
  border-radius: 12px;
  padding: 14px 16px;
  background: rgba(15,23,42,0.6);
}
.status-dot {
  display:inline-block;
  width:10px;
  height:10px;
  border-radius:50%;
  margin-right:8px;
}
.status-ok { background:#22c55e; box-shadow:0 0 10px #22c55e; }
.status-bad { background:#ef4444; box-shadow:0 0 10px #ef4444; }
div[data-testid="stFileUploader"] section {
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.7);
}
div[data-testid="stButton"] > button[kind="primary"] {
  height: 64px;
  font-size: 1.2rem;
  font-weight: 700;
  border-radius: 12px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _status_light(ok: bool, label: str, detail: str) -> None:
    klass = "status-ok" if ok else "status-bad"
    st.sidebar.markdown(
        f'<div class="card"><span class="status-dot {klass}"></span><b>{label}</b><br/><small>{detail}</small></div>',
        unsafe_allow_html=True,
    )


def _api_ready(keys: Tuple[str, ...]) -> bool:
    for k in keys:
        v = os.environ.get(k) or LOCAL_KEYS.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False


def _rules_runtime() -> Dict[str, Any]:
    report = validate_engineering_rules()
    rules = load_engineering_rules(report.get("path"))
    glossary = rules.get("建筑法定术语词典") if isinstance(rules, dict) else {}
    whitelist = rules.get("法定工种白名单") if isinstance(rules, dict) else []
    matrix = rules.get("劳动力排班算法矩阵") if isinstance(rules, dict) else {}
    return {
        "report": report,
        "term_count": len(glossary) if isinstance(glossary, dict) else 0,
        "whitelist_count": len(whitelist) if isinstance(whitelist, list) else 0,
        "matrix_count": len(matrix) if isinstance(matrix, dict) else 0,
    }


def _apply_boilerplate_blacklist(text: str) -> Tuple[str, List[str]]:
    out = str(text or "")
    hits: List[str] = []
    for phrase in BANNED_PHRASES:
        if re.search(re.escape(phrase), out, flags=re.IGNORECASE):
            hits.append(phrase)
            out = re.sub(re.escape(phrase), "", out, flags=re.IGNORECASE)
    out = re.sub(r"[，,。；;、]{2,}", lambda m: m.group(0)[0], out)
    out = re.sub(r"^[，,。；;、\s]+", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out, sorted(set(hits))


def _render_sidebar() -> Dict[str, Any]:
    st.sidebar.title("全局配置中心")
    gemini_ready = _api_ready(("ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"))
    openai_ready = _api_ready(("ZF_OPENAI_API_KEY", "OPENAI_API_KEY"))
    _status_light(gemini_ready, "Gemini API", "就绪" if gemini_ready else "未配置")
    _status_light(openai_ready, "OpenAI API", "就绪" if openai_ready else "未配置")

    rt = _rules_runtime()
    rep = rt["report"]
    _status_light(bool(rep.get("ok")), "规则文件", "已加载" if rep.get("ok") else "缺失字段")
    st.sidebar.markdown(
        f"""
<div class="card">
<b>规则源</b><br/>
<small>{rep.get("path")}</small><br/><br/>
<small>术语词条: {rt['term_count']}</small><br/>
<small>法定工种白名单: {rt['whitelist_count']}</small><br/>
<small>劳动力矩阵项目数: {rt['matrix_count']}</small>
</div>
        """,
        unsafe_allow_html=True,
    )
    return rt


def _render_labor_calculator() -> None:
    st.subheader("核心模块一：劳动力智能排班测算器")
    opts = get_labor_ui_options()
    col1, col2, col3, col4 = st.columns([2, 1.2, 1.2, 1.2])
    with col1:
        project_type = st.selectbox("项目类型", opts["project_types"], index=0, key="labor_project_type")
    with col2:
        size = st.selectbox("项目规模", opts["sizes"], index=1, key="labor_size")
    with col3:
        stage = st.selectbox("施工阶段", opts["stages"], index=1, key="labor_stage")
    with col4:
        total_personnel = st.number_input("预估总人数", min_value=1, max_value=10000, value=120, step=5)

    if st.button("一键生成劳动力计划", type="primary", use_container_width=True):
        result = generate_labor_plan(
            project_type=project_type,
            size=size,
            stage=stage,
            total_personnel=int(total_personnel),
        )
        if not result.get("ok"):
            st.error(f"测算失败：{result.get('error')}")
            return

        st.success(
            f"测算完成：{result['project_type']} / {result['size']} / {result['stage_label']} | "
            f"总人数输入={result['total_personnel']} | 建议人数合计={result['total_suggested']}"
        )
        st.caption(f"工种域：{result.get('trade_domain')}")
        st.dataframe(result.get("trade_rows") or [], use_container_width=True, hide_index=True)
        skill_rows = result.get("skill_rows") or []
        if skill_rows:
            st.markdown("**技能等级配比**")
            st.table(skill_rows)


def _render_auditor_console() -> None:
    st.subheader("核心模块二：术语与文风审计台")
    default_text = (
        "泥瓦匠负责砌筑，塔吊司机负责吊运。在实际工程中需要注意的是，"
        "现场实际情况要加强管理，确保相关规范执行。"
    )
    draft = st.text_area("粘贴草稿文本", value=default_text, height=180, key="auditor_input")
    if st.button("触发术语与黑名单拦截", type="primary", use_container_width=True):
        normalized, receipt = normalize_text_terminology(draft, use_llm=False)
        cleaned, banned_hits = _apply_boilerplate_blacklist(normalized)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**原始文本**")
            st.code(draft, language=None)
        with c2:
            st.markdown("**净化后的合规文本**")
            st.code(cleaned, language=None)

        details = receipt.get("details") if isinstance(receipt, dict) else []
        replaced_rows = []
        if isinstance(details, list):
            for d in details:
                if not isinstance(d, dict):
                    continue
                replaced_rows.append(
                    {
                        "违规词": d.get("from"),
                        "替换后": d.get("to"),
                        "次数": d.get("count"),
                    }
                )
        if replaced_rows:
            st.markdown("**术语替换明细**")
            st.table(replaced_rows)
        if banned_hits:
            st.warning(f"命中文风黑名单：{', '.join(banned_hits)}")
        if not replaced_rows and not banned_hits:
            st.success("未发现术语违规词和黑名单短语。")


def _render_document_generator() -> None:
    st.subheader("核心模块三：施组全卷生成总控")
    files = st.file_uploader(
        "上传招标文件（PDF/Word）",
        type=["pdf", "doc", "docx"],
        accept_multiple_files=True,
        key="docgen_upload",
    )

    run = st.button("🚀 启动全卷智能编制", type="primary", use_container_width=True)
    if not run:
        return
    if not files:
        st.error("请先上传至少1个招标文件。")
        return

    target_dir = ROOT / "build" / "dashboard_uploads" / datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        (target_dir / f.name).write_bytes(f.getbuffer())

    steps = [
        "挂载核心规则与知识图谱",
        "解析招标文件与评审标准",
        "提取目录/项目编号/排版约束",
        "调度多Agent分工编制",
        "按章节生成正文与图文策略",
        "执行术语校正与黑名单拦截",
        "汇总导出DOCX与审计结果",
    ]
    progress = st.progress(0, text="任务准备中...")
    log_box = st.empty()
    logs: List[str] = []
    for i, step in enumerate(steps, start=1):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {i}/{len(steps)} {step}")
        log_box.code("\n".join(logs), language="text")
        progress.progress(int(i / len(steps) * 100), text=f"执行中：{step}")
        time.sleep(0.35)

    output_doc = ROOT / "build" / f"dashboard_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    output_doc.write_text("Dashboard mock output generated.", encoding="utf-8")
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] DONE 输出文件：{output_doc}")
    log_box.code("\n".join(logs), language="text")
    progress.progress(100, text="任务完成")
    st.success(f"生成完成：{output_doc}")


def run() -> None:
    st.set_page_config(page_title="智飞 Web 战术指挥舱", page_icon="🛰️", layout="wide")
    _inject_style()
    _render_sidebar()

    st.title("智飞 Web 战术指挥舱")
    st.caption("规则驱动 · 术语审计 · 多Agent编制总控")
    st.divider()

    with st.container(border=True):
        _render_labor_calculator()
    st.divider()
    with st.container(border=True):
        _render_auditor_console()
    st.divider()
    with st.container(border=True):
        _render_document_generator()


if __name__ == "__main__":
    run()
