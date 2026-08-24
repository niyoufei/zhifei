from __future__ import annotations

from html import escape


EXPERT_SYSTEM_CSS = r"""
<style>
:root {
  --rts-navy-950: #0b1f33;
  --rts-navy-900: #102a43;
  --rts-blue-700: #1d4ed8;
  --rts-teal-700: #0f766e;
  --rts-teal-600: #0d9488;
  --rts-cyan-100: #cffafe;
  --rts-slate-700: #334155;
  --rts-slate-500: #64748b;
  --rts-slate-300: #cbd5e1;
  --rts-slate-200: #e2e8f0;
  --rts-slate-100: #f1f5f9;
  --rts-surface: #ffffff;
  --rts-bg: #f4f7fb;
  --rts-success: #15803d;
  --rts-warning: #b45309;
  --rts-danger: #b91c1c;
  --rts-radius-lg: 18px;
  --rts-radius-md: 12px;
  --rts-shadow: 0 12px 32px rgba(15, 42, 67, 0.08);
}

html, body, [class*="css"] {
  font-family: Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
}

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 10% 0%, rgba(13, 148, 136, 0.07), transparent 30rem),
    linear-gradient(180deg, #f8fafc 0%, var(--rts-bg) 42%, #eef3f8 100%);
  color: var(--rts-navy-950);
}

[data-testid="stHeader"] {
  background: transparent;
}

[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
  display: none !important;
}

div.block-container {
  max-width: 1440px;
  padding: 2rem 2.4rem 4rem;
}

h1, h2, h3, h4 {
  color: var(--rts-navy-950);
  letter-spacing: -0.015em;
}

h2, h3 {
  margin-top: 0.4rem;
}

p, label, [data-testid="stCaptionContainer"] {
  color: var(--rts-slate-700);
}

[data-testid="stCaptionContainer"] {
  line-height: 1.65;
}

.rts-hero {
  position: relative;
  overflow: hidden;
  margin: 0 0 1.25rem;
  padding: 2rem 2.2rem;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 22px;
  background:
    radial-gradient(circle at 88% 20%, rgba(45, 212, 191, 0.26), transparent 15rem),
    linear-gradient(118deg, #0b1f33 0%, #123a57 54%, #0f766e 135%);
  box-shadow: 0 20px 42px rgba(11, 31, 51, 0.18);
}

.rts-hero::after {
  content: "";
  position: absolute;
  inset: auto -4rem -7rem auto;
  width: 17rem;
  height: 17rem;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 50%;
}

.rts-kicker {
  margin-bottom: 0.55rem;
  color: #99f6e4;
  font-size: 0.78rem;
  font-weight: 750;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.rts-hero h1 {
  margin: 0;
  color: #ffffff;
  font-size: clamp(2rem, 4vw, 3.05rem);
  line-height: 1.12;
}

.rts-hero p {
  max-width: 760px;
  margin: 0.75rem 0 1.15rem;
  color: #dbeafe;
  font-size: 1rem;
  line-height: 1.7;
}

.rts-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.rts-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.42rem 0.72rem;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.09);
  color: #f8fafc;
  font-size: 0.82rem;
  font-weight: 650;
  backdrop-filter: blur(8px);
}

.rts-badge-dot {
  width: 0.46rem;
  height: 0.46rem;
  border-radius: 50%;
  background: #5eead4;
  box-shadow: 0 0 0 3px rgba(94, 234, 212, 0.16);
}

.rts-workflow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.72rem;
  margin: 0.2rem 0 1.2rem;
}

.rts-workflow-step {
  display: flex;
  align-items: center;
  gap: 0.72rem;
  min-height: 64px;
  padding: 0.8rem 0.95rem;
  border: 1px solid var(--rts-slate-200);
  border-radius: var(--rts-radius-md);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 5px 18px rgba(15, 42, 67, 0.05);
}

.rts-step-no {
  display: grid;
  flex: 0 0 2rem;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 10px;
  background: #e6fffb;
  color: var(--rts-teal-700);
  font-size: 0.78rem;
  font-weight: 800;
}

.rts-step-copy strong {
  display: block;
  color: var(--rts-navy-900);
  font-size: 0.88rem;
}

.rts-step-copy span {
  display: block;
  margin-top: 0.12rem;
  color: var(--rts-slate-500);
  font-size: 0.74rem;
}

.rts-section-head {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  margin: 0.05rem 0 1rem;
}

.rts-section-index {
  display: grid;
  flex: 0 0 2.25rem;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--rts-navy-900), var(--rts-teal-700));
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 800;
}

.rts-section-copy h2 {
  margin: 0;
  font-size: 1.28rem;
  line-height: 1.3;
}

.rts-section-copy p {
  margin: 0.25rem 0 0;
  color: var(--rts-slate-500);
  font-size: 0.82rem;
  line-height: 1.5;
}

.rts-launch {
  margin: 1.35rem 0 0.7rem;
  padding: 1.05rem 1.15rem;
  border: 1px solid #bae6fd;
  border-radius: var(--rts-radius-md);
  background: linear-gradient(90deg, #eff6ff, #ecfeff);
}

.rts-launch strong {
  color: var(--rts-navy-900);
}

.rts-launch span {
  margin-left: 0.5rem;
  color: var(--rts-slate-500);
  font-size: 0.86rem;
}

.rts-activity-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 0.75rem 0;
  padding: 0.95rem 1.05rem;
  border: 1px solid #99f6e4;
  border-radius: var(--rts-radius-md);
  background: linear-gradient(105deg, #ecfeff, #f0fdfa 55%, #ffffff);
  box-shadow: 0 8px 22px rgba(15, 118, 110, 0.09);
}

.rts-activity-main {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.8rem;
}

.rts-activity-pulse {
  position: relative;
  flex: 0 0 0.72rem;
  width: 0.72rem;
  height: 0.72rem;
  border-radius: 50%;
  background: var(--rts-teal-600);
  box-shadow: 0 0 0 0 rgba(13, 148, 136, 0.32);
  animation: rts-agent-pulse 1.8s ease-out infinite;
}

.rts-activity-card.is-waiting .rts-activity-pulse,
.rts-activity-card.is-stale .rts-activity-pulse {
  background: #f59e0b;
  box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.28);
}

.rts-activity-copy { min-width: 0; }
.rts-activity-copy strong {
  display: block;
  color: var(--rts-navy-900);
  font-size: 0.95rem;
}
.rts-activity-copy span {
  display: block;
  overflow: hidden;
  margin-top: 0.18rem;
  color: var(--rts-slate-500);
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rts-activity-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.42rem;
}

.rts-activity-meta span {
  padding: 0.28rem 0.5rem;
  border: 1px solid var(--rts-slate-200);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--rts-slate-700);
  font-size: 0.72rem;
  font-weight: 650;
}

@keyframes rts-agent-pulse {
  0% { box-shadow: 0 0 0 0 rgba(13, 148, 136, 0.32); }
  70% { box-shadow: 0 0 0 9px rgba(13, 148, 136, 0); }
  100% { box-shadow: 0 0 0 0 rgba(13, 148, 136, 0); }
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--rts-slate-200) !important;
  border-radius: var(--rts-radius-lg) !important;
  background: rgba(255, 255, 255, 0.95) !important;
  box-shadow: var(--rts-shadow);
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
  padding: 0.32rem;
}

[data-testid="stFileUploader"] {
  border: 1px solid var(--rts-slate-200);
  border-radius: var(--rts-radius-md);
  padding: 0.5rem 0.62rem 0.65rem;
  background: #f8fafc;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 92px;
  padding: 0.65rem 0.8rem;
  border: 1px dashed #94a3b8;
  border-radius: 10px;
  background: #ffffff;
}

[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--rts-teal-600);
  background: #f0fdfa;
}

[data-testid="stFileUploaderDropzoneInstructions"] > div {
  font-size: 0.86rem;
}

[data-testid="stFileUploaderDropzone"] button {
  font-size: 0 !important;
}

[data-testid="stFileUploaderDropzone"] button::after {
  content: "选择文件";
  font-size: 0.84rem;
  font-weight: 700;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-baseweb="select"] > div,
[data-baseweb="base-input"] {
  border-color: var(--rts-slate-200) !important;
  border-radius: 10px !important;
  background: #f8fafc !important;
  color: var(--rts-navy-950) !important;
  box-shadow: none !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus,
[data-baseweb="select"] > div:focus-within {
  border-color: var(--rts-teal-600) !important;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12) !important;
}

.stButton > button {
  min-height: 42px;
  border-color: var(--rts-slate-300);
  border-radius: 10px;
  background: #ffffff;
  color: var(--rts-navy-900);
  font-weight: 700;
  transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
}

.stButton > button:hover {
  border-color: var(--rts-teal-600);
  color: var(--rts-teal-700);
  box-shadow: 0 6px 16px rgba(15, 118, 110, 0.12);
  transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
  min-height: 50px;
  border: 0;
  background: linear-gradient(105deg, var(--rts-navy-900), var(--rts-teal-700));
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.22);
  font-size: 1rem;
}

.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {
  color: #ffffff !important;
}

.stButton > button[kind="primary"]:hover {
  color: #ffffff;
  filter: brightness(1.06);
}

[data-testid="stExpander"] {
  overflow: hidden;
  border: 1px solid var(--rts-slate-200);
  border-radius: var(--rts-radius-md);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 5px 18px rgba(15, 42, 67, 0.045);
}

[data-testid="stExpander"] summary {
  color: var(--rts-navy-900);
  font-weight: 700;
}

[data-testid="stExpander"] details[open] > summary {
  border-bottom: 1px solid var(--rts-slate-200);
  background: #f8fafc;
}

[data-testid="stAlert"] {
  border-radius: var(--rts-radius-md);
  border-left-width: 4px;
  box-shadow: 0 4px 14px rgba(15, 42, 67, 0.04);
}

[data-baseweb="tab-list"] {
  gap: 0.35rem;
  border-bottom: 1px solid var(--rts-slate-200);
}

[data-baseweb="tab"] {
  border-radius: 9px 9px 0 0;
  color: var(--rts-slate-500);
  font-weight: 700;
}

[aria-selected="true"][data-baseweb="tab"] {
  color: var(--rts-teal-700);
  background: #f0fdfa;
}

[data-testid="stDataFrame"] {
  overflow: hidden;
  border: 1px solid var(--rts-slate-200);
  border-radius: var(--rts-radius-md);
}

code {
  border-radius: 6px;
  background: var(--rts-slate-100);
  color: var(--rts-navy-900);
}

@media (max-width: 900px) {
  div.block-container { padding: 1rem 1rem 3rem; }
  .rts-hero { padding: 1.5rem; }
  .rts-workflow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .rts-workflow { grid-template-columns: 1fr; }
  .rts-hero h1 { font-size: 2rem; }
  .rts-activity-card { align-items: flex-start; flex-direction: column; }
  .rts-activity-meta { justify-content: flex-start; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}
</style>
"""


def hero_html() -> str:
    badges = ("评审标准驱动", "多 Agent 协同", "证据链可追溯")
    badge_html = "".join(
        f'<span class="rts-badge"><span class="rts-badge-dot"></span>{escape(item)}</span>'
        for item in badges
    )
    return (
        '<section class="rts-hero">'
        '<div class="rts-kicker">Intelligent Construction Proposal Studio</div>'
        '<h1>施组专家系统</h1>'
        '<p>从招标资料解析、评审目录对标到多模型协同编制与质量终审，形成可核验、可追溯的技术标生产工作台。</p>'
        f'<div class="rts-badges">{badge_html}</div>'
        '</section>'
    )


def workflow_html() -> str:
    steps = (
        ("01", "上传资料", "招标、清单、图纸"),
        ("02", "对标目录", "识别评分标准"),
        ("03", "配置生成", "版式与模型策略"),
        ("04", "质控交付", "复核、修订、导出"),
    )
    items = "".join(
        '<div class="rts-workflow-step">'
        f'<span class="rts-step-no">{escape(no)}</span>'
        '<span class="rts-step-copy">'
        f'<strong>{escape(title)}</strong><span>{escape(detail)}</span>'
        '</span></div>'
        for no, title, detail in steps
    )
    return f'<div class="rts-workflow">{items}</div>'


def section_heading_html(index: str, title: str, description: str) -> str:
    index_html = (
        f'<span class="rts-section-index">{escape(index)}</span>'
        if str(index or "").strip()
        else ""
    )
    return (
        '<div class="rts-section-head">'
        f'{index_html}'
        '<span class="rts-section-copy">'
        f'<h2>{escape(title)}</h2><p>{escape(description)}</p>'
        '</span></div>'
    )


def launch_html() -> str:
    return (
        '<div class="rts-launch"><strong>生成前确认</strong>'
        '<span>请确认必传资料、评审目录与模型凭据均已就绪；启动后可在状态区查看进度。</span></div>'
    )


def activity_html(view: dict) -> str:
    tone = str(view.get("tone") or "working").strip().lower()
    if tone not in {"working", "waiting", "stale", "idle"}:
        tone = "working"
    meta = [
        f"已运行 {view.get('elapsed_text') or '0秒'}",
        str(view.get("signal_text") or "等待心跳"),
    ]
    active_agents = int(view.get("active_agents") or 0)
    if active_agents:
        meta.append(f"活动 Agent {active_agents}")
    chapters_total = int(view.get("chapters_total") or 0)
    chapters_done = int(view.get("chapters_done") or 0)
    if chapters_total:
        meta.append(f"章节 {chapters_done}/{chapters_total}")
    meta_html = "".join(f"<span>{escape(item)}</span>" for item in meta)
    return (
        f'<div class="rts-activity-card is-{escape(tone)}">'
        '<div class="rts-activity-main"><span class="rts-activity-pulse"></span>'
        '<span class="rts-activity-copy">'
        f'<strong>{escape(str(view.get("headline") or "Agent 正在工作"))}</strong>'
        f'<span>{escape(str(view.get("activity") or "正在处理"))}</span>'
        '</span></div>'
        f'<div class="rts-activity-meta">{meta_html}</div></div>'
    )
