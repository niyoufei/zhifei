# SYSTEM-AUTONOMY-004 Goal Mode Codebase Read Only Inventory Authorization Gate

## 1. 节点定位

`SYSTEM-AUTONOMY-004-GOAL-MODE-CODEBASE-READ-ONLY-INVENTORY-AUTHORIZATION-GATE` 是 ZDoc / 本地 AI 应用 / LOCAL-LAUNCHER 系统自治路线从 docs-only 治理阶段进入 `code-read-only inventory` 阶段的授权 Gate。

本节点承接：

1. `SYSTEM-AUTONOMY-001-GOAL-MODE-GOVERNANCE-AND-ROADMAP-GATE`
2. `SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE`
3. `SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE`

本节点只做受限代码库只读盘点与文档化记录。它不实施系统自治能力、不修改代码、不运行 runtime、不启动服务、不访问 endpoint、不调用 Ollama、不执行模型命令、不进行模型推理、不输入 prompt、不读取真实 KG / 真实项目资料、不执行 generation / export / write-back。

本节点输出仅作为后续 `SYSTEM-AUTONOMY-005` 或其他实现 Gate 的代码对象边界、风险边界和审批依据。它不得被解释为代码修改授权、runtime preflight 授权、endpoint 授权、dry-run 授权、trial 授权或正式使用授权。

## 2. 代码库盘点范围

### 2.1 实际读取方式

| 读取方式 | 对象 | 目的 | 边界 |
| --- | --- | --- | --- |
| pasted text 正文读取 | `/Users/youfeini/.codex/attachments/13bb2c59-b064-4c0d-ad47-b55687cc4511/pasted-text-1.txt` | 获取本节点目标、允许范围、禁止范围、提交/tag/回报要求 | 仅读取本次用户提供文本 |
| docs 正文读取 | `docs/zdoc-system-autonomy-goal-mode-governance-and-roadmap-gate-system-autonomy-001.md` | 确认治理总纲与不可自治边界 | 文档边界 |
| docs 正文读取 | `docs/zdoc-system-autonomy-goal-mode-task-decomposition-gate-system-autonomy-002.md` | 确认任务分解、证据链、停止点 | 文档边界 |
| docs 正文读取 | `docs/zdoc-system-autonomy-goal-mode-permission-matrix-and-state-machine-gate-system-autonomy-003.md` | 确认 `S4_CODE_READ_ONLY_INVENTORY`、A2 审批和状态机限制 | 文档边界 |
| 仓库结构清单 | `git ls-files` | 识别 tracked 文件结构、候选对象、禁止边界路径 | 未打开禁止路径正文 |
| 目录结构清单 | `find . -maxdepth 3 ... -prune ...` | 识别目录层级与禁止目录 | 已排除 `.runtime`、`data`、`build`、`logs`、`知识图谱`、`projects` 等正文读取 |
| 文件名定位 | `rg` over `git ls-files` / selected code | 定位静态 UI、启动脚本、API、runtime、模型、KG、测试边界 | 未读取 secrets / output / job / export / 日志正文 |
| 正文只读 | 授权代码、脚本、配置、测试、README/RUNBOOK | 建立后续实现前 inventory | 未执行任何 runtime / endpoint / test |

### 2.2 实际读取正文文件

以下文件被读取正文，用于本节点盘点：

1. `docs/zdoc-system-autonomy-goal-mode-governance-and-roadmap-gate-system-autonomy-001.md`
2. `docs/zdoc-system-autonomy-goal-mode-task-decomposition-gate-system-autonomy-002.md`
3. `docs/zdoc-system-autonomy-goal-mode-permission-matrix-and-state-machine-gate-system-autonomy-003.md`
4. `README.md`
5. `RUNBOOK.md`
6. `api/server.py`
7. `app/main.py`
8. `backend/main.py`
9. `backend/app/main.py`
10. `backend/app/routers/actions_bridge.py`
11. `backend/app/routers/ingest.py`
12. `backend/app/routers/kg_read_only_preview.py`
13. `backend/app/routers/local_llm_preview_safe.py`
14. `backend/app/routers/local_trial_preview_only.py`
15. `backend/app/routers/publish_router.py`
16. `backend/app/routers/retrieve.py`
17. `backend/app/routers/score_router.py`
18. `backend/app/routers/zhifei_autoplan.py`
19. `backend/kg_loader.py`
20. `backend/kg_context_service.py`
21. `backend/kg_read_only_preview_adapter.py`
22. `backend/kg_config.json`
23. `kg_config.json`
24. `manifest.json`
25. `requirements.txt`
26. `pytest.ini`
27. `frontend/audit_dashboard.html`
28. `frontend_web/app.py`
29. `frontend_web/templates/index.html`
30. `frontend_web/templates/login.html`
31. `frontend_web/static/style.css`
32. `local-launcher-v1/README.md`
33. `local-launcher-v1/index.html`
34. `local-launcher-v1/app.js`
35. `local-launcher-v1/mock-config.json`
36. `local-launcher-v1/styles.css`
37. `local_launcher/v0/README.md`
38. `local_launcher/v0/index.html`
39. `local_launcher/v0/launcher-state.json`
40. `local_launcher/v1/README.md`
41. `local_launcher/v1/index.html`
42. `local_launcher/v1/launcher-state.json`
43. `scripts/run_web_ui.sh`
44. `scripts/start_web_ui_background.sh`
45. `scripts/stop_web_ui_background.sh`
46. `scripts/web_ui_watchdog.sh`
47. `scripts/create_desktop_launcher.sh`
48. `scripts/create_desktop_shortcut.sh`
49. `scripts/install_web_ui_launchd.sh`
50. `scripts/uninstall_web_ui_launchd.sh`
51. `scripts/install_launchd_agent.sh`
52. `scripts/uninstall_launchd_agent.sh`
53. `scripts/check_repo_layout.sh`
54. `scripts/guards/README.md`
55. `scripts/guards/zdoc_guard.py`
56. `deploy/systemd/docgen-autoplan.service`
57. `backend/zhifei_autoplan/orchestrator.py`
58. `backend/zhifei_autoplan/multi_agent_runtime.py`
59. `backend/zhifei_autoplan/provider_runtime.py`
60. `backend/zhifei_autoplan/utils/llm_client.py`
61. `backend/zhifei_autoplan/ollama_preview.py`
62. `backend/zhifei_autoplan/providers/base.py`
63. `backend/zhifei_autoplan/providers/ollama_provider.py`
64. `backend/zhifei_autoplan/providers/openai_provider.py`
65. `backend/zhifei_autoplan/providers/google_gemini_provider.py`
66. `backend/zhifei_autoplan/kg_runtime.py`
67. `backend/zhifei_autoplan/kg_store.py`
68. `backend/zhifei_autoplan/output_artifacts.py`
69. `backend/zhifei_autoplan/job_store.py`
70. `backend/zhifei_autoplan/exporter.py`
71. `backend/zhifei_autoplan/human_approval_gate.py`
72. `backend/zhifei_autoplan/formal_writeback_guard.py`
73. `backend/zhifei_autoplan/formal_writeback_dry_run.py`
74. `backend/tests/test_local_llm_preview_safe_endpoint.py`
75. `backend/tests/test_local_trial_preview_only_route.py`
76. `backend/tests/test_kg_runtime.py`
77. `backend/tests/test_ollama_provider_adapter.py`
78. `backend/tests/test_output_artifacts.py`
79. `backend/tests/test_actions_output_artifacts.py`
80. `backend/tests/test_human_approval_gate.py`
81. `backend/tests/test_formal_writeback_guard.py`

以下对象仅读取了结构清单或文件名清单，没有打开正文：

1. `backend/tests/test_actions_export_docx.py`
2. `backend/tests/test_actions_ollama_preview.py`
3. `backend/tests/test_actions_ollama_section_draft_api.py`
4. `backend/tests/test_actions_reference_libraries.py`
5. `backend/tests/test_actions_review.py`
6. `backend/tests/test_actions_zbid_snapshot_mapper_api.py`
7. `backend/tests/test_formal_writeback_dry_run_contract_schema.py`
8. `backend/tests/test_generation_mode_policy.py`
9. `backend/tests/test_kg_context_service.py`
10. `backend/tests/test_kg_loader.py`
11. `backend/tests/test_kg_store.py`
12. `backend/tests/test_ollama_preview.py`
13. `backend/tests/test_zdoc_zbid_preview_only_integration_contract_schema.py`
14. `backend/tests/test_zdoc_zbid_preview_outbound.py`
15. `backend/tests/test_zdoc_zbid_preview_packet.py`
16. `local_launcher/v0/styles.css`
17. `local_launcher/v1/styles.css`
18. `backend/zhifei_autoplan/providers/anthropic_provider.py`
19. `backend/zhifei_autoplan/providers/baidu_provider.py`
20. `backend/zhifei_autoplan/providers/deepseek_provider.py`
21. `backend/zhifei_autoplan/providers/grok_provider.py`
22. `backend/zhifei_autoplan/providers/iflytek_provider.py`
23. `backend/zhifei_autoplan/providers/qwen_provider.py`
24. `backend/zhifei_autoplan/providers/tencent_provider.py`
25. `backend/zhifei_autoplan/providers/zhipu_provider.py`

### 2.3 未读取的禁止范围

以下范围未打开正文：

1. `知识图谱/*.json`
2. `knowledge_graph/`
3. `backend/data/kg/`
4. `kg_packs/` 和 `backend/kg_packs/` 的 KG 包正文
5. `01_真实项目测试/`
6. `04_实战演习输入/`
7. `frontend_web/uploads/`
8. `backend/data/uploads/`
9. `backend/data/extracts/`
10. `backend/data/previews/`
11. `backend/data/audit/`
12. `data/uploads/`
13. `data/extracts/`
14. `data/audit/`
15. `logs/`
16. `logs/parser_audit/`
17. `logs/job_workers/`
18. `logs/exports/`
19. `build/` 产物、日志、运行结果正文
20. `output/`
21. `job/`
22. `export/`
23. `.runtime/docgen/`
24. `.env`、`.env.*`、密钥、证书、token、credential 文件
25. 任何真实招标文件、图纸、清单、项目样本、生成结果或日志正文

## 3. LOCAL-LAUNCHER / ZDoc 本地应用对象清单

### 3.1 静态 UI 文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `local-launcher-v1/index.html` | 静态 HTML | V1 专业静态 no-op 控制台 | 是，code-read-only | 可在 S5 提案后审查修改 | 否 | 否 | 否 | 否 | 低 | `SYSTEM-AUTONOMY-005` 仅提案；修改需 S6 |
| `local-launcher-v1/app.js` | 静态 JS | DOM 面板切换和 no-op 提示 | 是 | 可在 S5 提案后审查修改 | 否 | 否 | 否 | 否 | 低 | 静态 UI guard 保持 no-op |
| `local-launcher-v1/mock-config.json` | mock 配置 | 明确禁用服务、网络、endpoint、Ollama、真实资料、写回 | 是 | 可在静态配置 Gate 修改 | 否 | 否 | 否 | 否 | 低 | static-config-only Gate |
| `local-launcher-v1/styles.css` | CSS | 静态样式 | 是 | 可在 UI Gate 修改 | 否 | 否 | 否 | 否 | 低 | static UI Gate |
| `local-launcher-v1/README.md` | 文档 | 静态边界说明 | 是 | 可在 docs Gate 修改 | 否 | 否 | 否 | 否 | 低 | docs-only Gate |
| `local_launcher/v0/index.html` | 静态 HTML | V0 安全外壳，占位禁用按钮 | 是 | 可在 S5 提案后审查修改 | 否 | 否 | 否 | 否 | 低 | static shell Gate |
| `local_launcher/v0/launcher-state.json` | 静态状态 | 禁用启动、endpoint、Ollama、生成、导出、写回 | 是 | 可在静态配置 Gate 修改 | 否 | 否 | 否 | 否 | 低 | static state Gate |
| `local_launcher/v1/index.html` | 静态 HTML | V1 专业静态控制台，CSP 严格 | 是 | 可在 S5 提案后审查修改 | 否 | 否 | 否 | 否 | 低 | static UI Gate |
| `local_launcher/v1/launcher-state.json` | 静态状态 | 禁用服务、端口、日志、配置、endpoint、Ollama、生成、导出、写回 | 是 | 可在静态配置 Gate 修改 | 否 | 否 | 否 | 否 | 低 | static state Gate |
| `frontend/audit_dashboard.html` | HTML + JS | 审计仪表板，页面打开会请求 `/audit/data` 并可下载 JSON | 是 | 修改需 S5/S6 | 否，本文件本身静态；打开页面会触发请求 | 是，页面脚本包含 fetch `/audit/data` | 否 | 可能读取审计数据响应 | 中 | endpoint/UI smoke Gate 前不得打开 |
| `frontend_web/templates/index.html` | Jinja HTML + JS | 上传与 preview-only route 前端入口 | 是 | 修改需 S5/S6 | 否，本文件本身静态模板 | 是，按钮会 fetch `/local-trial/preview-only` | 否 | 上传表单指向招标/资料入口 | 高 | endpoint 授权前不得打开或点击 |
| `frontend_web/templates/login.html` | Jinja HTML | 登录页面 | 是 | 修改需 S5/S6 | 否 | 表单提交需服务 | 否 | 否 | 中 | Web UI Gate |
| `frontend_web/static/style.css` | CSS | Flask UI 样式 | 是 | 可在 UI Gate 修改 | 否 | 否 | 否 | 否 | 低 | UI-only Gate |

### 3.2 启动脚本

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/run_web_ui.sh` | 启动脚本 | 启动 FastAPI + Streamlit，写 PID/log，可能打开浏览器 | 是，code-read-only | 修改需 S5/S6 | 是，执行会启动服务 | 是，脚本内 health curl 与浏览器 URL | 否 | 可能加载应用间接读取配置/数据 | 极高 | runtime preflight / controlled start Gate |
| `scripts/start_web_ui_background.sh` | 启动脚本 | 委托 `run_web_ui.sh --background` 并写控制日志 | 是 | 修改需 S5/S6 | 是 | 是，间接 | 否 | 间接 | 极高 | controlled start Gate |
| `scripts/stop_web_ui_background.sh` | 停止脚本 | 根据 PID/端口识别并停止本项目服务 | 是 | 修改需 S5/S6 | 是，执行会停止进程 | 端口探测 | 否 | 否 | 高 | controlled shutdown Gate |
| `scripts/web_ui_watchdog.sh` | 守护脚本 | 检查端口并重启 Web UI | 是 | 修改需 S5/S6 | 是 | 端口探测 | 否 | 间接 | 极高 | watchdog Gate；默认禁止 |
| `scripts/create_desktop_launcher.sh` | 桌面 App 创建脚本 | 生成 macOS `.app` 并调用 `run_web_ui.sh` | 是 | 修改需 S5/S6 | 执行创建启动入口 | 间接 | 否 | 间接 | 高 | desktop launcher Gate |
| `scripts/create_desktop_shortcut.sh` | 桌面快捷方式脚本 | 写 `启动文档生成系统.command` | 是 | 修改需 S5/S6 | 执行后创建启动入口 | 间接 | 否 | 间接 | 高 | desktop launcher Gate |
| `scripts/install_web_ui_launchd.sh` | launchd 安装脚本 | 写 LaunchAgent 守护后端/Streamlit/watchdog | 是 | 修改需 S5/S6 | 是 | 端口/URL | 否 | 间接 | 极高 | launchd install Gate |
| `scripts/uninstall_web_ui_launchd.sh` | launchd 卸载脚本 | bootout/remove LaunchAgents | 是 | 修改需 S5/S6 | 是，停止服务 | 否 | 否 | 否 | 高 | launchd uninstall Gate |
| `scripts/install_launchd_agent.sh` | launchd 安装脚本 | 常驻 FastAPI + watcher | 是 | 修改需 S5/S6 | 是 | health URL | 否 | watcher 可能读 `projects/` | 极高 | launchd + watcher Gate |
| `scripts/uninstall_launchd_agent.sh` | launchd 卸载脚本 | 移除常驻服务 | 是 | 修改需 S5/S6 | 是，停止服务 | 否 | 否 | 否 | 高 | launchd uninstall Gate |
| `deploy/systemd/docgen-autoplan.service` | systemd 配置 | Linux FastAPI 服务模板 | 是 | 修改需 S5/S6 | 是，安装/启动后运行 uvicorn | 是，端口 8000 | 否 | 间接 | 高 | deploy/runtime Gate |

### 3.3 Runtime / API / endpoint 相关文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/app/main.py` | FastAPI 主入口 | 注册 `/health`、`/capabilities`、`/config`、`/model_ping`、`/compose`、`/export`、`/retrieve` 等 | 是 | 修改需 S5/S6 | 是，运行 app 会启动服务 | 是 | `/model_ping` 和 compose 可能触发模型 | `/compose`、capabilities、KG debug 可能读取 KG/资料元数据 | 极高 | API inventory -> code proposal -> runtime preflight |
| `app/main.py` | 兼容入口 | re-export `backend.app.main:app` | 是 | 可在 S5/S6 | 是，若被 uvicorn 调用 | 是 | 间接 | 间接 | 高 | compatibility Gate |
| `backend/main.py` | FastAPI 简化入口 | `/list_files`、`/read_file` 禁用；`__main__` uvicorn | 是 | 修改需 S5/S6 | 是 | 是 | 否 | 文件 endpoint 当前 403 | 高 | disabled endpoint Gate |
| `api/server.py` | FastAPI ingest 入口 | `/ingest` 上传落盘、解析、审计 | 是 | 修改需 S5/S6 | 是 | 是 | 否 | 上传内容可能是真实资料 | 极高 | ingest sandbox Gate |
| `frontend_web/app.py` | Flask app | 登录、上传、preview-only 代理、download、app.run | 是 | 修改需 S5/S6 | 是 | 是，含 `urllib` 代理到后端 | 否 | 上传/下载涉及项目资料与 deliveries | 极高 | Web runtime + upload Gate |
| `backend/app/routers/actions_bridge.py` | API router | `/actions/*` 参数、素材库、Ollama、生成、导出、job、review/apply、download | 是 | 修改需 S5/S6 | 是 | 是 | 是 | 是，解析/素材库/结果读取 | 极高 | actions bridge isolated proposal Gate |
| `backend/app/routers/ingest.py` | API router | `/ingest/upload`、`/ingest/ingest` 落盘、抽取、OCR、预览、审计 | 是 | 修改需 S5/S6 | 是 | 是 | OCR 非模型 LLM，但有外部 OCR 程序风险 | 是，输入可能为真实资料 | 极高 | ingest preflight / sandbox Gate |
| `backend/app/routers/retrieve.py` | API router | `/search` 读取 `backend/data/audit/ingest.jsonl` 和 extracted text | 是 | 修改需 S5/S6 | 是 | 是 | 否 | 是，读取入库资料正文 | 极高 | retrieval data-read Gate |
| `backend/app/routers/publish_router.py` | API router | `/publish` 读取响应 JSON、生成 DOCX/PDF、写 exports | 是 | 修改需 S5/S6 | 是 | 是 | 否 | 可能读取生成响应/资料链 | 极高 | export/write-back Gate |
| `backend/app/routers/score_router.py` | API router | `/score` 文本评分，可写 exports xlsx/docx | 是 | 修改需 S5/S6 | 是 | 是 | 否 | 输入可能是真实正文 | 高 | scoring sandbox Gate |
| `backend/app/routers/zhifei_autoplan.py` | API router | `/autoplan/*` KG、生成、job、导出、审计、download | 是 | 修改需 S5/S6 | 是 | 是 | 是 | 是 | 极高 | autoplan API Gate |
| `backend/app/routers/local_trial_preview_only.py` | API router | `/local-trial/preview-only` metadata-only no-write route | 是 | 修改需 S5/S6 | 运行服务后可访问 | 是 | 否 | 不读取真实资料，但输入可能引用资料 ID | 中 | preview-only endpoint Gate |
| `backend/app/routers/local_llm_preview_safe.py` | API router | `/local-llm/preview-safe`，feature flag 后可 fake 或 Ollama bridge | 是 | 修改需 S5/S6 | 运行服务后可访问 | 是 | 可通过 Ollama adapter | 否 | 高 | local LLM preview Gate |
| `backend/app/routers/kg_read_only_preview.py` | API router | `/kg/read-only-preview`，feature flag + allowlist 后调用 KG adapter | 是 | 修改需 S5/S6 | 运行服务后可访问 | 是 | 否 | 可能结构读授权 KG | 极高 | KG read-only Gate |

### 3.4 模型接入相关文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/zhifei_autoplan/utils/llm_client.py` | LLM client | 统一接入 OpenAI/Gemini/Claude/Qwen/DeepSeek/Baidu/Iflytek/Tencent/Ollama | 是 | 修改需 S5/S6 | 否，导入本身不启动服务 | 是，complete 会调用外部/本地模型 | 是 | 输入 prompt 可能含真实资料 | 极高 | model adapter proposal Gate |
| `backend/zhifei_autoplan/provider_runtime.py` | provider 路由 | 从环境变量解析 provider slot/key alias，构造 server provider chain | 是 | 修改需 S5/S6 | 否 | 是，后续调用 | 是 | 间接 | 高 | provider routing Gate |
| `backend/zhifei_autoplan/providers/openai_provider.py` | provider adapter | 调用 OpenAI Responses API | 是 | 修改需 S5/S6 | 否 | 是 | 是 | prompt 可能含资料 | 极高 | remote model Gate |
| `backend/zhifei_autoplan/providers/google_gemini_provider.py` | provider adapter | 调用 Google GenAI | 是 | 修改需 S5/S6 | 否 | 是 | 是 | prompt 可能含资料 | 极高 | remote model Gate |
| `backend/zhifei_autoplan/providers/ollama_provider.py` | provider adapter | 请求 `127.0.0.1:11434/api/chat` | 是 | 修改需 S5/S6 | 依赖本地 Ollama 服务 | 是，本地 HTTP | 是 | prompt 可能含资料 | 极高 | Ollama inventory/inference Gate |
| `backend/zhifei_autoplan/ollama_preview.py` | preview adapter | fake/default-off；real transport 会请求 `/api/tags`、`/api/generate` | 是 | 修改需 S5/S6 | 依赖本地 Ollama | 是 | 是 | prompt 可能含资料 | 极高 | Ollama preview Gate |
| `backend/zhifei_autoplan/orchestrator.py` | generation orchestrator | run_autoplan：读取 tender/boq/KG/evidence，调用 LLM，生成章节/媒体/QC | 是 | 修改需 S5/S6 | 调用时执行生成流程 | 可能调用模型 endpoint | 是 | 是 | 极高 | generation Gate |
| `backend/zhifei_autoplan/multi_agent_runtime.py` | runtime helper | 根据图谱分发专业 Agent 上下文 | 是 | 修改需 S5/S6 | 否，函数被调用时参与生成 | 否 | 间接 | 图谱上下文 | 高 | multi-agent proposal Gate |

### 3.5 KG 接入相关文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/zhifei_autoplan/kg_store.py` | KG store | 保存、列出、激活 KG 到 `backend/data/kg` | 是 | 修改需 S5/S6 | 否，函数被 API 调用时写文件 | 通过 API | 否 | 是 | 极高 | KG storage Gate |
| `backend/zhifei_autoplan/kg_runtime.py` | KG search | 读取 active KG JSON 并检索文本 | 是 | 修改需 S5/S6 | 否，函数被调用时读文件 | 通过 API/生成链 | 否 | 是 | 极高 | real KG read Gate |
| `backend/kg_loader.py` | KG config loader | 读取 `kg_config.json`，解析 pack 路径 | 是 | 修改需 S5/S6 | 否 | 间接 | 否 | 可能引向 KG pack 文件 | 高 | KG config Gate |
| `backend/kg_context_service.py` | KG context builder | 读取 domain map/base pack 元数据并写 `build/kg_context.json` | 是 | 修改需 S5/S6 | 否，函数被调用时读/写 | 通过 API/compose | 否 | 是，pack 内容/元数据 | 极高 | KG context Gate |
| `backend/kg_read_only_preview_adapter.py` | KG read-only adapter | 对硬编码授权 KG 目标做 metadata/structure-only preview | 是 | 修改需 S5/S6 | 否 | 通过 route | 否 | 是，feature flag 后可 parse 授权 KG 结构 | 极高 | separate KG read-only approval |
| `kg_config.json` / `backend/kg_config.json` | 配置 | 指向 base packs、domain map、active_pack | 是 | 修改需 S5/S6 | 否 | 间接 | 否 | 引向 KG pack | 高 | config proposal Gate |
| `manifest.json` | manifest | KG pack 文件 hash/size 元数据 | 是 | 修改需 S5/S6 | 否 | 否 | 否 | KG 元数据，不含正文 | 中 | metadata-only Gate |

### 3.6 output / job / export 支撑文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/zhifei_autoplan/output_artifacts.py` | artifact writer | 写 `build/*.json/docx/xlsx` | 是 | 修改需 S5/S6 | 否，函数被调用时写产物 | 通过 API | 否 | 结果可能含真实资料 | 极高 | output artifact Gate |
| `backend/zhifei_autoplan/job_store.py` | job store | 写/读/删除 `backend/data/autoplan/jobs/*.json` 与关联产物 | 是 | 修改需 S5/S6 | 否，函数被调用时写/删文件 | 通过 API | 否 | job payload/result 可能含真实资料 | 极高 | job store Gate |
| `backend/zhifei_autoplan/exporter.py` | exporter | 生成 DOCX/XLSX/compare/review artifacts | 是 | 修改需 S5/S6 | 否，函数被调用时写文件 | 通过 API | 否 | 输出可能含真实资料 | 极高 | export/write-back Gate |

### 3.7 配置文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `requirements.txt` | 依赖清单 | 包含 FastAPI、Streamlit、OpenAI、Anthropic、Google GenAI、OCR、DOCX/PDF 等依赖 | 是 | 修改需 dependency Gate | 否 | 否 | 否 | 否 | 中 | dependency proposal Gate |
| `pytest.ini` | 测试配置 | 默认 testpaths 为 `backend/tests`，addopts `-v --tb=short` | 是 | 修改需 test config Gate | 否 | 否 | 否 | 否 | 中 | test config Gate |
| `manifest.json` | manifest | KG pack hash/size metadata | 是 | 修改需 KG metadata Gate | 否 | 否 | 否 | KG 元数据 | 中 | metadata-only Gate |
| `deploy/systemd/docgen-autoplan.service` | 服务配置 | 系统服务模板，含示例环境变量与 uvicorn 启动 | 是 | 修改需 deploy Gate | 是，安装/启动后 | 是 | 否 | 间接 | 高 | deploy Gate |

### 3.8 测试文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/tests/test_local_llm_preview_safe_endpoint.py` | pytest | TestClient 覆盖 preview-safe route、write surface count、Ollama bridge guards | 是 | 修改需 S5/S6 | 运行测试会实例化 app | 是，TestClient 内部请求 | mock/patch 下不应真实推理 | 统计 output/job/export 文件数 | 中 | test-only Gate |
| `backend/tests/test_local_trial_preview_only_route.py` | pytest | metadata-only route no-write / formal flags 测试 | 是 | 修改需 S5/S6 | 运行测试会实例化 app | 是，TestClient | 否 | 统计 output/job/export 文件数 | 中 | test-only Gate |
| `backend/tests/test_kg_runtime.py` | pytest | KG runtime token/extract/search 单测 | 是 | 修改需 S5/S6 | 否 | 否 | 否 | mock/patch 下测试 KG 行为 | 中 | test-only Gate |
| `backend/tests/test_ollama_provider_adapter.py` | pytest | Ollama provider payload/parse/mock transport 测试 | 是 | 修改需 S5/S6 | 否 | mock transport；真实运行需审查 | mock 下无真实推理 | 否 | 中 | test-only Gate |
| `backend/tests/test_output_artifacts.py` | pytest | output_artifacts 写产物，使用 tmp_path/monkeypatch | 是 | 修改需 S5/S6 | 否 | 否 | 否 | 写临时产物 | 中 | test-only Gate |
| `backend/tests/test_actions_output_artifacts.py` | pytest | actions `_save_outputs` 产物集测试 | 是 | 修改需 S5/S6 | 否 | 否 | 否 | 写临时产物 | 中 | test-only Gate |
| `backend/tests/test_human_approval_gate.py` | pytest | 人工审批 metadata-only false flags | 是 | 修改需 S5/S6 | 否 | 否 | 否 | 否 | 低 | test-only Gate |
| `backend/tests/test_formal_writeback_guard.py` | pytest | formal writeback guard false flags / blocked reasons | 是 | 修改需 S5/S6 | 否 | 否 | 否 | 否 | 低 | test-only Gate |
| `backend/tests/test_actions_*.py` | pytest group | 覆盖 actions route、Ollama、export、review、reference libraries | 路径已识别，后续可读需 Gate | 修改需 S5/S6 | 运行可能实例化 app | 可能 | 可能 mock | 可能触及 artifact/read paths | 高 | targeted test inventory Gate |

### 3.9 其他支撑文件

| 路径 | 类型 | 当前角色 | 后续可读 | 后续可改 | 可能触发 runtime | 可能触发 endpoint | 可能触发模型推理 | 可能读取真实 KG / 项目资料 | 风险等级 | 后续 Gate 建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/guards/zdoc_guard.py` | guard script | 检查 PR/task scope、阻断高风险命令，不启动服务/模型 | 是 | 修改需 S5/S6 | 执行 guard 本身运行 Python，但不启动服务 | 否，除任务命令被允许 | 否 | 可统计 output/build/job 文件数量 | 中 | guard proposal Gate |
| `scripts/guards/README.md` | 文档 | 说明 guard 边界和禁止命令 | 是 | docs-only | 否 | 否 | 否 | 否 | 低 | docs-only |
| `scripts/check_repo_layout.sh` | shell checker | 检查布局，并会 `mkdir -p projects/...` | 是 | 修改需 S5/S6 | 否 | 否 | 否 | 会创建 workspace dirs | 中 | static checker Gate |
| `README.md` | 文档 | 包含启动、curl、compose/export/audit、Web UI/launchd 指令 | 是 | docs-only Gate | 否，本节点未执行 | 文档包含 endpoint 指令 | 文档包含生成流程 | 文档说明真实资料读取能力 | 中 | docs-only |
| `RUNBOOK.md` | 文档 | 包含 uvicorn、smoke、curl、KG pack 发布命令 | 是 | docs-only Gate | 否，本节点未执行 | 文档包含 endpoint 指令 | 间接 | KG pack 命令 | 中 | docs-only |

## 4. 系统自治实现前的代码边界

### 4.1 后续可进入 code-read-only 的文件

以下文件可在后续 A2 / `S4_CODE_READ_ONLY_INVENTORY` 中继续只读，但仍不得运行：

1. `local-launcher-v1/*`
2. `local_launcher/v0/*`
3. `local_launcher/v1/*`
4. `frontend_web/app.py`
5. `frontend_web/templates/*.html`
6. `frontend_web/static/*.css`
7. `frontend/audit_dashboard.html`
8. `backend/app/main.py`
9. `backend/app/routers/*.py`
10. `backend/zhifei_autoplan/*.py`
11. `backend/zhifei_autoplan/providers/*.py`
12. `backend/zhifei_autoplan/utils/llm_client.py`
13. `backend/kg_loader.py`
14. `backend/kg_context_service.py`
15. `backend/kg_read_only_preview_adapter.py`
16. `scripts/*.sh`
17. `scripts/guards/*.py`
18. `backend/tests/test_*.py`

### 4.2 后续可进入 code-change proposal 的候选文件

以下仅可在 `S5_CODE_CHANGE_PROPOSAL` 中提出方案，不得直接修改：

1. `scripts/guards/zdoc_guard.py`：可提案增加 system-autonomy forbidden scanner / inventory checker。
2. `backend/zhifei_autoplan/human_approval_gate.py`：可提案抽象审批 Gate schema。
3. `backend/zhifei_autoplan/formal_writeback_guard.py`：可提案补强 write-back 阻断字段。
4. `backend/app/routers/local_trial_preview_only.py`：可提案强化 metadata-only response flags。
5. `backend/app/routers/local_llm_preview_safe.py`：可提案强化 feature flag / forbidden field checks。
6. `backend/kg_read_only_preview_adapter.py`：可提案强化 KG structure redaction / allowlist。
7. `local-launcher-v1/app.js`：可提案继续保持 no-op 的 UI 文案/状态展示。
8. `backend/tests/test_*`：可提案新增最小单测，但不得运行大套件。

### 4.3 后续必须保持禁止修改的文件或范围

以下在未单独授权前不得修改：

1. `知识图谱/*.json`
2. `knowledge_graph/`
3. `backend/data/kg/`
4. `kg_packs/` 和 `backend/kg_packs/`
5. `backend/data/uploads/`
6. `backend/data/extracts/`
7. `backend/data/previews/`
8. `backend/data/audit/`
9. `data/uploads/`
10. `data/extracts/`
11. `data/audit/`
12. `logs/`
13. `build/`
14. `output/`
15. `job/`
16. `export/`
17. `.runtime/docgen/`
18. `.env` / secrets / tokens / credentials
19. 真实项目测试、招标文件、图纸、清单、项目样本目录

### 4.4 必须等 runtime preflight 授权后才可运行的文件

1. `scripts/run_web_ui.sh`
2. `scripts/start_web_ui_background.sh`
3. `scripts/stop_web_ui_background.sh`
4. `scripts/web_ui_watchdog.sh`
5. `scripts/install_web_ui_launchd.sh`
6. `scripts/install_launchd_agent.sh`
7. `backend/app/main.py` via uvicorn
8. `backend/main.py` via uvicorn
9. `frontend_web/app.py`
10. `api/server.py`
11. `scripts/watch_projects_autoplan.py`
12. `backend/scripts/run_smoke.sh`
13. `scripts/run_e2e.sh`
14. `scripts/smoke_api.py`
15. `scripts/kg_release.sh`
16. `backend/scripts/smoke_e2e.py`

### 4.5 必须等 endpoint 授权后才可访问的文件 / route

1. `backend/app/main.py` routes: `/health`、`/capabilities`、`/config`、`/model_ping`、`/compose`、`/export`、`/retrieve`、`/debug/kg_pack`、`/audit`
2. `backend/app/routers/actions_bridge.py` routes: `/actions/generate`、`/actions/generate_async`、`/actions/export_docx`、`/actions/ollama/*`、`/actions/result`、`/actions/download`
3. `backend/app/routers/zhifei_autoplan.py` routes: `/autoplan/generate`、`/autoplan/generate_async`、`/autoplan/kg/*`、`/autoplan/export_*`、`/autoplan/download_*`
4. `backend/app/routers/ingest.py` routes: `/ingest/upload`、`/ingest/ingest`
5. `backend/app/routers/retrieve.py` route: `/search`
6. `backend/app/routers/local_trial_preview_only.py` route: `/local-trial/preview-only`
7. `backend/app/routers/local_llm_preview_safe.py` route: `/local-llm/preview-safe`
8. `backend/app/routers/kg_read_only_preview.py` route: `/kg/read-only-preview`
9. `frontend/audit_dashboard.html` page fetch: `/audit/data`
10. `frontend_web/templates/index.html` page fetch: `/local-trial/preview-only`

### 4.6 涉及模型 / KG / 真实数据，必须单独审批的文件

1. `backend/zhifei_autoplan/orchestrator.py`
2. `backend/zhifei_autoplan/utils/llm_client.py`
3. `backend/zhifei_autoplan/provider_runtime.py`
4. `backend/zhifei_autoplan/providers/*.py`
5. `backend/zhifei_autoplan/ollama_preview.py`
6. `backend/zhifei_autoplan/kg_runtime.py`
7. `backend/zhifei_autoplan/kg_store.py`
8. `backend/kg_context_service.py`
9. `backend/kg_read_only_preview_adapter.py`
10. `backend/app/routers/actions_bridge.py`
11. `backend/app/routers/zhifei_autoplan.py`
12. `backend/app/routers/ingest.py`
13. `backend/app/routers/retrieve.py`

## 5. 运行触发风险清单

| 风险类型 | 文件或命令 | 触发方式 | 阻断规则 |
| --- | --- | --- | --- |
| 服务启动 | `./scripts/run_web_ui.sh`、`./scripts/run_web_ui.sh --background` | 启动 uvicorn + Streamlit，写 PID/log，可能打开浏览器 | 未获 runtime preflight + controlled start Gate 前禁止执行 |
| 服务启动 | `python3 -m uvicorn backend.app.main:app ...` | 启动 FastAPI | 未获 controlled runtime Gate 前禁止执行 |
| Web UI 启动 | `streamlit run "$ROOT/app.py"` | 启动 Streamlit Web UI | 未获 Web UI Gate 前禁止执行 |
| 服务守护 | `scripts/web_ui_watchdog.sh`、launchd scripts | 端口探测并重启服务 | 未获 watchdog/launchd Gate 前禁止执行 |
| endpoint 访问 | README/RUNBOOK 中 `curl http://127.0.0.1...` | HTTP request / localhost | 未获 endpoint Gate 前禁止执行 |
| endpoint 访问 | `frontend/audit_dashboard.html` | 页面加载会 fetch `/audit/data` | 未获 UI endpoint smoke Gate 前不得打开页面 |
| endpoint 访问 | `frontend_web/templates/index.html` | 点击按钮 fetch `/local-trial/preview-only` | 未获 endpoint Gate 前不得打开/点击 |
| Ollama / 模型 | `backend/zhifei_autoplan/providers/ollama_provider.py` | 请求 `/api/chat` | 未获 Ollama inventory/inference Gate 前禁止调用 |
| Ollama / 模型 | `backend/zhifei_autoplan/ollama_preview.py` | 请求 `/api/tags`、`/api/generate` | 未获 Ollama preview Gate 前禁止调用 |
| 远程模型 | `OpenAIProvider`、`GeminiProvider`、LLMClient | 调用外部模型 API | 未获 remote model Gate 前禁止调用 |
| 模型推理 | `backend/zhifei_autoplan/orchestrator.py` | 非 dry-run 构造 LLMClient 并 `complete()` | 未获 model/prompt Gate 前禁止执行 |
| 真实 KG 读取 | `backend/zhifei_autoplan/kg_runtime.py` | 读取 active KG JSON | 未获 real KG read Gate 前禁止调用 |
| 真实 KG 结构读 | `backend/kg_read_only_preview_adapter.py` | feature flag + allowlist 后 parse 授权 KG | 未获 KG structure read Gate 前禁止调用 |
| 真实项目资料读取 | `backend/app/routers/ingest.py`、`retrieve.py` | 上传/抽取/读取 extract text | 未获 data sandbox/real data Gate 前禁止访问 |
| output/job/export 读取 | `actions_result`、`job_status`、`job_download`、`retrieve`、`audit` routes | 读取 result/job/audit/extract 文件 | 未获 evidence/output read Gate 前禁止访问 |
| generation / export | `actions_generate`、`autoplan/generate`、`/compose`、`/export` | 生成内容、DOCX、XLSX、JSON | 未获 generation/export Gate 前禁止调用 |
| write-back / apply | `actions_review_apply`、formal writeback helpers | 修改 variant 内容并重建产物 | 未获 write-back Gate 前禁止调用 |
| 测试触发 | `pytest` over API tests | TestClient 请求 route，tmp 写产物或统计 output/job/export | 未获 test Gate 前禁止运行 |
| 清理/删除 | `job_store.cleanup_jobs`、launchd uninstall scripts | 删除 job 产物或 LaunchAgents | 未获 cleanup/uninstall Gate 前禁止执行 |

## 6. 后续实现候选任务

以下仅为候选任务，不得在本节点实施。

| 候选任务 | 目标 | 涉及文件 | 是否需代码修改 | 是否需测试 | 是否需 runtime | 是否需 endpoint | 是否需模型 / KG | 前置审批等级 | 推荐后续 Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 权限守卫 | 将禁止项、允许命令、禁止路径固化为静态检查 | `scripts/guards/zdoc_guard.py`、新增/授权测试 | 是 | 是，最小单测 | 否 | 否 | 否 | A3 | `SYSTEM-AUTONOMY-005-GOAL-MODE-CODE-CHANGE-PROPOSAL-GATE` |
| 状态机配置 | 将 003 状态机转成机器可读配置 | 未来授权 config/docs | 是或 docs-only | 是，schema test | 否 | 否 | 否 | A3 | `SYSTEM-AUTONOMY-005` |
| 审批 Gate 检查器 | 复用 human/writeback guard 字段生成节点准入报告 | `backend/zhifei_autoplan/human_approval_gate.py`、`formal_writeback_guard.py` | 是 | 是 | 否 | 否 | 否 | A3 | `SYSTEM-AUTONOMY-005` |
| dry-run / mock-run 隔离层 | 为后续 mock-run 定义无真实资料、无 output 写入隔离 | `local_trial_preview_only.py`、测试 | 是 | 是 | 否 | 可能需 TestClient | 否 | A3/A5 | `SYSTEM-AUTONOMY-006-MOCK-RUN-DESIGN-GATE` |
| runtime preflight 检查清单 | 只生成启动前 checklist，不执行服务启动 | docs + future guard | 可能 docs-only | 否或静态测试 | 否 | 否 | 否 | A4 前置 | `SYSTEM-AUTONOMY-006` 或 `LOCAL-LAUNCHER-RUNTIME-PREFLIGHT-GATE` |
| 证据链生成模板 | 标准化 HEAD/tag/status/读取范围/禁止项回报 | docs + guard | 可 docs-only | 可静态测试 | 否 | 否 | 否 | A1/A3 | `SYSTEM-AUTONOMY-005` |
| 只读 inventory 检查器 | 自动校验实际读取路径是否在 allowlist | `scripts/guards/zdoc_guard.py` 或新 guard | 是 | 是 | 否 | 否 | 否 | A3 | `SYSTEM-AUTONOMY-005` |
| 禁止项扫描器 | 扫描命令 spec 中 runtime/endpoint/Ollama/HTTP/write-back 风险 | `scripts/guards/zdoc_guard.py` | 是 | 是 | 否 | 否 | 否 | A3 | `SYSTEM-AUTONOMY-005` |
| 回滚记录模板 | 只产出回滚建议，不执行 destructive 操作 | docs + guard report | 可 docs-only | 否 | 否 | 否 | 否 | A1/A3 | `SYSTEM-AUTONOMY-005` |
| trial 前冻结检查表 | 试用前冻结、支持、回滚、审计 checklist | docs | 否或 docs-only | 否 | 否 | 否 | 否 | A7/A8 | later trial readiness Gate |

## 7. 权限状态机映射复核

根据 003 状态机，本节点映射如下：

| 状态 | 当前映射 |
| --- | --- |
| `S3_PERMISSION_MATRIX_LOCKED` | 已由 003 文档提供权限矩阵与状态机基础 |
| `S4_CODE_READ_ONLY_INVENTORY` | 当前节点所处状态，仅允许受限代码/配置/脚本/测试只读盘点与唯一 docs 写入 |
| `S5_CODE_CHANGE_PROPOSAL` | 本节点不得进入 |
| `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME` | 本节点不得进入 |
| `S7_STATIC_VALIDATION_ONLY` | 本节点只允许目标文档文本检查与 Git 状态检查，不允许测试/lint/typecheck |
| `S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED` | 本节点不得进入 |
| `S9_RUNTIME_PREFLIGHT_NO_ENDPOINT` | 本节点不得进入 |
| `S10_MOCK_OR_DRY_RUN_AUTHORIZATION_REQUIRED` | 本节点不得进入 |
| `S11_CONTROLLED_DRY_RUN_NO_REAL_DATA` | 本节点不得进入 |
| `S12+ trial / production states` | 本节点不得进入 |

当前结论：

1. 当前仍处于 `S4_CODE_READ_ONLY_INVENTORY`。
2. 本节点不得进入 `S5_CODE_CHANGE_PROPOSAL`。
3. 本节点不得进入 `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME`。
4. 本节点不得进入任何 runtime / endpoint / dry-run / trial 状态。
5. 本节点完成后必须停止，等待 ChatGPT 总控师审核。

## 8. 证据链要求

| 字段 | 记录 |
| --- | --- |
| 节点 | `SYSTEM-AUTONOMY-004-GOAL-MODE-CODEBASE-READ-ONLY-INVENTORY-AUTHORIZATION-GATE` |
| 开始分支 | `main` |
| 开始 HEAD | `905b87c13552c617cbb17033513f87919faabd58` |
| 开始 tag | `v0.1.652-system-autonomy-permission-matrix-state-machine-gate` |
| 结束 HEAD | 目标提交完成后由最终回报记录；本文件内不写自引用 commit hash，避免改变目标提交 hash |
| 新增文件 | `docs/zdoc-system-autonomy-goal-mode-codebase-read-only-inventory-authorization-gate-system-autonomy-004.md` |
| 修改文件 | 无既有文件修改；仅新增目标 docs 文件 |
| 实际读取文件 | 见本文件第 2.2 节 |
| 未读取禁止范围 | 见本文件第 2.3 节 |
| 未执行禁止命令 | 未执行 runtime、服务启动、Web UI 启动、curl、HTTP request、localhost/端口探测、Ollama、模型命令、测试、build/run/serve/dev/preview、generation/export/write-back |
| 校验证据 | 仅允许 `git diff --check -- <target>`、`git status --short`、`git diff --cached --check` 等文本/Git 检查 |
| 停止点 | 提交与 tag 完成后停止，不进入 `SYSTEM-AUTONOMY-005`、`LOCAL-LAUNCHER-026` 或任何后续节点 |

### 8.1 禁止项显式确认

1. 未启动、停止或重启服务。
2. 未执行 Web UI 启动脚本。
3. 未打开、预览或运行 HTML 页面。
4. 未访问 endpoint。
5. 未执行 curl / HTTP request / localhost / 端口探测。
6. 未读取、清理、删除 `.runtime/docgen/` PID 文件。
7. 未运行 Ollama 或任何模型命令。
8. 未进行模型推理。
9. 未向本地模型、远程模型或系统应用输入 prompt。
10. 未读取真实 KG / 真实项目资料 / 招标文件 / 图纸 / 清单 / 项目样本。
11. 未读取 secrets / tokens / credentials / 环境变量敏感信息。
12. 未读取 output / job / export / 生成结果 / 日志正文。
13. 未执行 generation / export / write-back。
14. 未修改 `local-launcher-v1` 静态文件。
15. 未修改 runtime 脚本。
16. 未创建 runtime 代码 / server 代码 / endpoint 代码 / API 代码 / 模型接入代码 / KG 接入代码。

## 9. SYSTEM-AUTONOMY-005 建议

建议下一节点名称：

`SYSTEM-AUTONOMY-005-GOAL-MODE-CODE-CHANGE-PROPOSAL-GATE`

建议定位：

1. 005 应仅提出代码修改方案，不直接修改代码。
2. 005 是否继续使用目标模式，必须由 ChatGPT 总控师审核后决定。
3. 005 是否允许代码修改，必须由 ChatGPT 总控师审核后决定。
4. 005 默认仍禁止 runtime，除非另行明确授权。
5. 005 应基于本节点 inventory 选择唯一候选改动面，例如 guard/checker/schema/report 模板之一。
6. 005 不得继承本节点代码读取授权为代码修改授权。
7. 005 不得进入 `LOCAL-LAUNCHER-026`。
8. 005 不得启动服务、访问 endpoint、运行 Ollama、模型推理、读取真实 KG/资料或执行 generation/export/write-back，除非后续 Gate 逐项明确授权。

## 10. 本节点结论

`SYSTEM-AUTONOMY-004-GOAL-MODE-CODEBASE-READ-ONLY-INVENTORY-AUTHORIZATION-GATE` 当前结论如下：

1. 本节点已完成受限代码库只读盘点文档。
2. 本节点仅新增目标 docs 文件。
3. 本节点不实施任何代码修改。
4. 本节点不运行 runtime。
5. 本节点不启动服务。
6. 本节点不访问 endpoint。
7. 本节点不运行 Ollama。
8. 本节点不进行模型推理。
9. 本节点不读取真实 KG / 真实项目资料。
10. 本节点不读取 output / job / export / 生成结果 / 日志正文。
11. 本节点不执行 generation / export / write-back。
12. 本节点保持在 `S4_CODE_READ_ONLY_INVENTORY`。
13. 本节点不进入 `SYSTEM-AUTONOMY-005`。
14. 本节点不进入 `LOCAL-LAUNCHER-026`。
15. 本节点完成后必须停止，等待 ChatGPT 总控师审核。
