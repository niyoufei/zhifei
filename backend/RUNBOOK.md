# Backend Runbook (macOS)

## 1) 重启后快速启动（必做）
### Terminal 1：启动 API 服务（保持窗口不退出）
    cd "$HOME/Desktop/文档生成系统/backend"
    python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

### Terminal 2：运行全量 Smoke 测试（跑完会自动退出）
    cd "$HOME/Desktop/文档生成系统/backend"
    ./scripts/run_smoke.sh

## 2) 8000 端口被占用时才需要做（可选）
    lsof -nP -iTCP:8000 -sTCP:LISTEN
    # 找到 PID 后执行（把 PID 换成数字）：
    kill -9 PID

## 3) 常用自检（可选）
    curl -s http://127.0.0.1:8000/openapi.json | head -n 5
    curl -s http://127.0.0.1:8000/audit | python3 -m json.tool | head -n 60
    # 快速接口冒烟（项目根目录执行）
    python3 scripts/smoke_api.py http://127.0.0.1:8000

## 3.1) P0 静态就绪检查（不启动服务）
    cd "$HOME/Desktop/文档生成系统"
    python3 scripts/p0_readiness.py
    python3 scripts/p0_readiness.py --json

该检查只读取仓库结构、现有 git 元数据、脱敏 demo 配置和路径级风险类别；不启动服务、不访问 endpoint、不读取真实资料正文或密钥。

判读：
- `PASS_P0_READINESS_STATIC` 表示静态边界检查通过，仍不代表允许 merge、runtime、launcher 或 endpoint。
- `NO-GO_P0_READINESS_STATIC` 表示存在 `failures` 阻断原因。
- `worktree_not_clean` 表示当前工作区仍 dirty；实施文件未提交/收口时出现该结果是预期门控。
- clean worktree 后重新运行 `python3 scripts/p0_readiness.py --json`；验收条件是 `status=PASS_P0_READINESS_STATIC` 且 `failures=[]`。

## 3.2) Phase 1A 本地基线索引（不启动服务）

Phase 1 local-only baseline index:

    docs/openclaw-zhifei-doc-phase1-local-baseline.md

P0 readiness 复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json

Phase 1A 只允许索引和文档闭合；不代表允许 push、runtime、launcher、endpoint、真实资料读取或 held config 内容读取。`local-launcher-v1/mock-config.json` 仍保持 metadata-only hold，任何正文审查或 smoke 都必须另开 gate。

## 4) 审计与清理（Autoplan 审计日志与导出）

- **审计日志路径**：`backend/data/audit/autoplan.jsonl`（Autoplan 相关操作会追加）
- **导出目录**：`build/audit_exports/<user_id>/`（按用户隔离）
- **本地清理**（在项目根目录执行，无需启动服务）：
  - 删除 7 天前的导出：`python3 scripts/clean_audit_exports.py --days 7`
  - 每人只保留最新 10 个：`python3 scripts/clean_audit_exports.py --keep 10`
  - 仅预览不删除：`python3 scripts/clean_audit_exports.py --days 7 --dry-run`
- **接口**（需登录）：`GET /autoplan/audit`、`GET /autoplan/audit/summary`、`GET /autoplan/audit/stats`；导出与批量清理见 API 或 `build/status.md`。

## KG Pack 管理（可替换/可升级知识图谱）

目标：KG 可插拔升级、可回滚；每次生成产物带上 `kg_pack` 元信息（active_pack/manifest_sha256 等），支持回放与对账。

### 1) 查看当前激活的 KG Pack
- 命令：`python3 scripts/kg_pack.py status`
- 在线：`GET /debug/kg_pack`

### 2) 从当前资产打包一个快照 Pack（生成 manifest + hash）
- `python3 scripts/kg_pack.py pack --pack-id <pack_id> --description "snapshot"`

生成目录：`kg_packs/<pack_id>/`，并写入 `kg_packs/<pack_id>/manifest.json`（作为可追溯锚点）。

### 3) 校验 Pack（引用资产存在 + manifest hash 校验）
- `python3 scripts/kg_pack.py validate --pack-id <pack_id>`

### 4) 激活 Pack（可选自动 smoke 验证，失败自动回滚）
- `python3 scripts/kg_pack.py activate --pack-id <pack_id> --smoke`

### 5) 回滚
- 回滚到上一个：`python3 scripts/kg_pack.py rollback --smoke`
- 指定回滚：`python3 scripts/kg_pack.py rollback --to <pack_id> --smoke`

### 6) Trace（产物落盘的 kg_pack 字段）
- `build/kg_context.json`：包含 `kg_pack`
- `build/retrieve.json`：包含 `kg_pack`
- `build/compose.json`：包含 `kg_pack`
- 在线：`GET /debug/kg_pack`

### 7) KG 升级评测（eval）

目标：把“KG 升级”标准化为可回放的发布流程：基线 smoke → 候选 pack 激活+smoke → diff 摘要 → 报告落盘（默认回滚到基线，防止污染当前环境）。

- 评测命令（默认评测后回滚到基线）：
  `python3 scripts/kg_pack.py eval --pack-id <pack_id>`

- 保留候选为当前 active（评测通过后不回滚）：
  `python3 scripts/kg_pack.py eval --pack-id <pack_id> --keep`

- 评测报告落盘：
  `build/kg_pack_eval.json`
  包含 baseline/candidate 的关键指标与 diff（如检索结果数、selected_packs、compose 章节数、kg_pack.manifest_sha256 等）。

### 8) 一键发布 KG（kg_release.sh）

目标：把 KG 升级发布流程收敛为一条命令：打包 → 校验 → 评测 → 激活（带 smoke），失败即停止，输出评测报告。

- 一键命令：
  `./scripts/kg_release.sh "release description"`

- 指定 pack_id（可选）：
  `PACK_ID=kgpack-YYYYMMDD_HHMMSS ./scripts/kg_release.sh "desc"`

- 产物：
  - 新包目录：`kg_packs/<pack_id>/`
  - 评测报告：`build/kg_pack_eval.json`
  - 当前激活包：`python3 scripts/kg_pack.py status` 或 `GET /debug/kg_pack`

#### DRY_RUN（只评测不激活，自动清理）

用于在本机做发布前演练：只执行 `pack → validate → eval`，不会激活新包；并在结束后自动恢复 `kg_config.json`、清理临时 pack 目录与本次新增的 `kg_config.json.bak.*`，避免污染工作区。

- 命令：
  `DRY_RUN=1 ./scripts/kg_release.sh "desc"`

### 9) 质量 Soft Gate（可配置阈值，仅告警不失败）

当前实现：在 smoke 末尾读取 `build/audit_report.json` 的 `quality_metrics_soft`，若不达标则打印 `[WARN]`，不终止 smoke。

环境变量（用于不同项目/阶段调整阈值）：
- `QUALITY_GATE_ENABLED`：默认 `1`；设为 `0/false/no` 可禁用该告警
- `QUALITY_RETRIEVE_MIN`：默认 `1`
- `QUALITY_SECTIONS_MIN`：默认 `3`
- `QUALITY_NONEMPTY_RATIO_MIN`：默认 `0.90`

示例（演练告警但不失败）：
- `QUALITY_RETRIEVE_MIN=999 ./scripts/run_smoke.sh`



## Quality Gate（质量门禁：quality_metrics_soft）

本门禁基于 /audit 生成的 build/audit_report.json 中的 quality_metrics_soft（retrieve/compose 统计指标）。

### Mode
- QUALITY_GATE_MODE

## Consistency Gate（MECE 控制闸口）

### 目的
- 将 topic / domain_key / region_key 的一致性检查从“可观测”升级为“可控”。

### 产物与字段
- build/audit_report.json 顶层：topic_consistency_ok、domain_key_consistency_ok、region_key_consistency_ok（以及 *_mismatch）。
- build/audit_report.json 顶层：quality_metrics_soft_summary（便于快速检索）。

### 运行与模式
- 默认：QUALITY_CONSISTENCY_MODE=warn（不拦截，仅输出提示）。
- 强制拦截：QUALITY_CONSISTENCY_MODE=fail（任一一致性为 False 则 smoke 失败退出）。

### 示例
- 默认（warn）：
  - ./scripts/run_smoke.sh
- 拦截（fail）：
  - QUALITY_CONSISTENCY_MODE=fail ./scripts/run_smoke.sh

### 输出约定
- smoke 输出包含两行：
  - [WARN] consistency(mode=...): topic=... domain_key=... region_key=...
  - [OK]/[WARN]/[FAIL] consistency_gate: ... (mode=...)

=warn（默认）：仅输出 [WARN]，不使 smoke 失败（本地默认）
- QUALITY_GATE_MODE=fail：不达标直接退出并使 smoke 失败（建议 CI / 发布分支启用）

### Env Vars
- QUALITY_GATE_ENABLED=1|0（默认 1）
- QUALITY_GATE_MODE=warn|fail（默认 warn）
- QUALITY_RETRIEVE_MIN（默认 1）
- QUALITY_SECTIONS_MIN（默认 3）
- QUALITY_NONEMPTY_RATIO_MIN（默认 0.90）
- QUALITY_EVIDENCE_COVERAGE_MIN（默认 0.80）
- QUALITY_PARAM_COVERAGE_MIN（默认 0.80）

### Examples
```bash
```
# 本地：只告警不失败（即使阈值很高）
QUALITY_GATE_MODE=warn QUALITY_RETRIEVE_MIN=999 ./scripts/run_smoke.sh

# CI：不达标直接失败
QUALITY_GATE_MODE=fail QUALITY_RETRIEVE_MIN=1 ./scripts/run_smoke.sh
```
```
