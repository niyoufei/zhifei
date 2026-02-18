# 文档生成系统

基于知识图谱与规则约束的施工组织设计文档自动生成系统。

## 系统概述

本系统能够：
1. 读取项目资料（招标文件/图纸/清单等）
2. 在知识图谱/规则约束下生成结构化中间产物（JSON）
3. 自动导出可交付的施工组织设计文档（DOCX）

## 环境准备

### 系统要求
- Python 3.11+
- macOS / Linux

### 安装依赖

```bash
pip3 install -r requirements.txt
```

### OCR（可选但强烈推荐）

当招标文件/图纸为扫描版 PDF 或图片时，系统会在“提取文本不足”时自动尝试 OCR，用于：
1. 提升检索命中率（证据抓取更稳定）
2. 让输出中的“【证据:来源】”更可追溯（至少到文件名与位置）

依赖：
- Python 包：`pypdfium2`、`pytesseract`（已写入 `requirements.txt`）
- 系统程序：`tesseract`

macOS（Homebrew）：
```bash
brew install tesseract
brew install tesseract-lang
tesseract --list-langs
```

Ubuntu/Debian（示例）：
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
tesseract --list-langs
```

如果遇到二进制包架构不兼容问题（arm64 vs x86_64），重新安装对应包：

```bash
pip3 uninstall pydantic pydantic_core pandas pillow matplotlib numpy cffi cryptography jiter -y
pip3 install --no-cache-dir --force-reinstall pydantic pydantic_core pandas pillow matplotlib numpy cffi cryptography jiter
```

## 快速启动

### 方式一：一键端到端运行（推荐）

```bash
chmod +x scripts/run_e2e.sh
./scripts/run_e2e.sh
```

此脚本会：
1. 检查依赖
2. 启动 FastAPI 服务器
3. 运行端到端测试
4. 验证产物并输出 PASS/FAIL

### 方式二：手动启动

#### 1. 启动后端服务

```bash
cd /path/to/文档生成系统
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

#### 2. 验证服务

```bash
curl http://127.0.0.1:8000/health
```

预期返回：
```json
{"ok": true, "version": "autoplan-0.1.0", "service": "文档生成系统", ...}
```

## 生成命令

### 生成文档（/compose）

```bash
curl -X POST http://127.0.0.1:8000/compose \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "建筑装饰装修工程施工组织设计",
    "outline": [
      "工程概况",
      "施工准备",
      "装饰装修工程施工方案",
      "质量管理体系与措施",
      "安全管理体系与措施",
      "文明施工与环保"
    ]
  }'
```

### 导出 DOCX（/export）

```bash
curl -X POST http://127.0.0.1:8000/export -o output.docx
```

### 查看审计链（/audit）

```bash
curl http://127.0.0.1:8000/audit
```

## 产物路径

| 文件 | 说明 |
|------|------|
| `build/project_profile.json` | 项目画像（类型识别、必选维度等） |
| `build/precheck_guard.json` | 前置检查结果 |
| `build/region_upgrade.json` | 区域规则升级记录 |
| `build/kg_context.json` | 知识图谱上下文 |
| `build/compose.json` | 结构化章节内容 |
| `build/compose_output.docx` | 导出的 Word 文档 |
| `build/compose_exported.docx` | 通过 /export 导出的文档 |

## 验证测试

### 运行端到端测试

```bash
# 方式一：通过脚本
./scripts/run_e2e.sh

# 方式二：直接运行测试（需先启动服务器）
python3 backend/scripts/smoke_e2e.py
```

测试会验证：
- `/compose` 返回 200 且 status="ok"
- 所有产物文件存在且有效
- `/audit` 返回 replayable=True
- `/export` 返回 DOCX 文件

### 验证结果

成功输出：
```
[SUCCESS] E2E smoke test passed: /compose -> artifacts -> /audit (replayable) -> /export
```

结果记录在：`build/clawdbot/e2e_result.txt`（PASS/FAIL）

### 快速接口冒烟（仅检查服务是否起来）

无需登录，只请求 `/health`、`/capabilities`、`/config`：

```bash
# 先启动服务，再在项目根目录执行
python3 scripts/smoke_api.py

# 或指定地址
python3 scripts/smoke_api.py http://127.0.0.1:8000
```

## 常驻运行（让系统一直跑）

你无法让 ChatGPT 本体“像服务一样常驻运行”，但你可以让本项目后端服务常驻运行，从而做到：
- 后端随时可被 Custom GPT Actions 调用
- 生成任务异步执行（`/actions/generate_async`）
- 图纸/资料可随时 ingest 并用于证据追溯

### macOS（推荐：launchd）

1) 安装/启动（会写入 `~/Library/LaunchAgents/`）：
```bash
chmod +x scripts/install_launchd_agent.sh
ZF_ACTIONS_KEY="your-very-strong-key" \\
ZF_GOOGLE_API_KEY="your-gemini-key" \\
./scripts/install_launchd_agent.sh
```

2) 健康检查：
```bash
curl -s http://127.0.0.1:8000/health
```

3) 卸载：
```bash
chmod +x scripts/uninstall_launchd_agent.sh
./scripts/uninstall_launchd_agent.sh
```

日志：
- `logs/uvicorn.out.log`
- `logs/uvicorn.err.log`
- `logs/watcher.out.log`
- `logs/watcher.err.log`

### 无人值守批量编制（落盘即自动）

`install_launchd_agent.sh` 会同时启动：
- 后端服务（FastAPI）
- 项目文件夹监听器（轮询式 watcher）

默认监听目录：
- `projects/inbox/`：把一个“项目文件夹”整体放进来即可
- watcher 会自动移动到：`projects/work/` → `projects/done/` 或 `projects/failed/`

每个项目输出目录：
- `projects/done/<项目文件夹>/_output/`
- `projects/failed/<项目文件夹>/_output/`

输出文件：
- `autoplan_<project_id>.json`
- `autoplan_<project_id>_v1.docx`
- `autoplan_<project_id>_compare_v1.docx`
- `run_summary.json`（质量闸门是否通过、失败项等）

可选：在项目文件夹根目录放 `project.json` 覆盖参数（不放也能跑）：
```json
{
  "topic": "项目名称（覆盖文件夹名）",
  "variants": 1,
  "generate_images": true,
  "provider": "google",
  "model": "gemini-2.0-flash",
  "bidder_company": "投标单位名称（可选）",
  "bidder_domain": "company.com（可选）",
  "logo_url": "https://.../logo.png（可选）"
}
```

项目隔离（避免串数据）：
- watcher 会为每个项目生成唯一 `project_id`，并在解析招标/清单、入库证据、生成文档时贯穿使用。
- 招标/清单/计划/参数回执等会按 `project_id` 存在：`backend/data/autoplan/projects/<project_id>/`。
- LOGO 若解析成功会写入：`backend/data/autoplan/projects/<project_id>/branding.json`，后续复跑优先复用，避免误抓。

### Linux（systemd 模板）

模板文件：`deploy/systemd/docgen-autoplan.service`（把路径与密钥改成你的实际值）。

## Custom GPT Actions 联调

当你用 Custom GPT + Actions 调用后端时，推荐先走本地联调脚本：

```bash
export ZF_ACTIONS_KEY="your-very-strong-key"
python3 scripts/run_actions_pipeline.py \\
  --base-url http://127.0.0.1:8000 \\
  --topic "示例项目施工组织设计" \\
  --tender /path/to/招标文件.pdf \\
  --boq /path/to/工程量清单.xlsx
```

## 常用环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `ZF_JWT_SECRET` | 登录 JWT 密钥 | 生产环境请改为随机字符串 |
| `ZF_ADMIN_KEY` | 管理员密钥（充值、配置版本等） | Bearer 后面的字符串 |
| `ZF_ACTIONS_KEY` | Custom GPT Actions 调用密钥（Header: X-Actions-Key） | 强随机字符串 |
| `ZF_GOOGLE_API_KEY` | Gemini Key（用于思维导图/插图生成与 LOGO 解析下载） | `AIza...` |
| `ZF_DAILY_LIMIT` | 用户每日调用上限 | `50` |
| `ZF_JOB_COST` | 每次生成扣费点数 | `1` |
| `ZF_AUTOPLAN_AUTO` | 是否在 compose 后自动触发生成 | `0` 或 `1` |
| `ZF_DEFAULT_PROVIDER` | 默认 LLM 提供商 | `openai` |
| `ZF_DEFAULT_MODEL` | 默认模型 | `gpt-4o-mini` |
| `ZF_JOB_LIST_FIELDS` | 任务列表默认返回字段（逗号分隔） | `job_id,status,updated_at` |

## 审计与清理

- **审计日志**：`backend/data/audit/autoplan.jsonl`（Autoplan 相关操作会追加写入）
- **导出文件**：`build/audit_exports/<用户ID>/`（按用户隔离）
- **本地清理**（不需启动服务）：在项目根目录执行
  ```bash
  # 删除 7 天前的导出文件
  python3 scripts/clean_audit_exports.py --days 7
  # 每人只保留最新 10 个文件
  python3 scripts/clean_audit_exports.py --keep 10
  # 仅查看将删除哪些，不实际删除
  python3 scripts/clean_audit_exports.py --days 7 --dry-run
  ```
- **接口**：`GET /autoplan/audit`、`GET /autoplan/audit/summary`、`GET /autoplan/audit/stats` 等（需登录）；导出与清理见 `build/status.md`。

## 排错方式

### 1. 端口被占用

```bash
# 查找占用端口的进程
lsof -nP -iTCP:8000 -sTCP:LISTEN

# 终止进程
kill -9 <PID>
```

### 2. 依赖问题

```bash
# 检查依赖是否正确安装
python3 -c "import fastapi, uvicorn, docx; print('OK')"

# 如果报架构错误，重新安装
pip3 install --force-reinstall <package-name>
```

### 3. 应用加载失败

```bash
# 验证应用能否加载
PYTHONPATH="$PWD" python3 -c "from backend.app.main import app; print('Routes:', len(app.routes))"
```

### 4. 查看详细日志

```bash
# 审计日志
cat build/clawdbot/audit.log

# 服务运行日志（启动时 uvicorn 输出）
```

## 目录结构

```
文档生成系统/
├── backend/                 # 后端应用
│   ├── app/                 # FastAPI 应用
│   │   ├── main.py          # 主入口
│   │   └── routers/         # 路由
│   ├── scripts/             # 脚本
│   │   └── smoke_e2e.py     # 端到端测试
│   └── zhifei_autoplan/     # 自动规划模块
├── scripts/
│   ├── run_e2e.sh           # 一键端到端脚本
│   ├── smoke_api.py         # 快速接口冒烟（/health、/capabilities、/config）
│   └── clean_audit_exports.py # 审计导出目录本地清理（--days / --keep）
├── build/                   # 构建产物
│   ├── compose.json         # 结构化内容
│   ├── compose_output.docx  # 输出文档
│   └── clawdbot/            # 自动化执行日志
├── requirements.txt         # Python 依赖
└── README.md                # 本文档
```

## API 参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查（含 config_version、audit_ready） |
| `/compose` | POST | 生成结构化文档 |
| `/export` | POST | 导出 DOCX |
| `/audit` | GET | 查看审计链 |
| `/retrieve` | POST | 检索知识库 |
| `/debug/kg_pack` | GET | 查看 KG Pack 状态 |

## 更多文档

- 后端运行手册：`backend/RUNBOOK.md`
- 系统架构：`System_Architecture_V1.md`
- API 设计：`System_API_Design_V1.md`
- Custom GPT Actions 接入：`docs/custom_gpt_actions_setup.md`
- Custom GPT Actions OpenAPI：`docs/custom_gpt_actions_openapi.json`
- Custom GPT 指令模板：`docs/custom_gpt_system_prompt.md`
