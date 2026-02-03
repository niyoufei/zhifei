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

如果遇到二进制包架构不兼容问题（arm64 vs x86_64），重新安装对应包：

```bash
pip3 uninstall pydantic pydantic_core pandas pillow matplotlib numpy -y
pip3 install pydantic pydantic_core pandas pillow matplotlib numpy
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
│   └── run_e2e.sh           # 一键端到端脚本
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
| `/health` | GET | 健康检查 |
| `/compose` | POST | 生成结构化文档 |
| `/export` | POST | 导出 DOCX |
| `/audit` | GET | 查看审计链 |
| `/retrieve` | POST | 检索知识库 |
| `/debug/kg_pack` | GET | 查看 KG Pack 状态 |

## 更多文档

- 后端运行手册：`backend/RUNBOOK.md`
- 系统架构：`System_Architecture_V1.md`
- API 设计：`System_API_Design_V1.md`
