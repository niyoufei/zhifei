# Backend Runbook (macOS)

## 1) 重启后快速启动（必做）
### Terminal 1：启动 API 服务（保持窗口不退出）
    cd "$HOME/Desktop/文档生成系统"
    python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

### Terminal 2：运行全量 Smoke 测试（跑完会自动退出）
    cd "$HOME/Desktop/文档生成系统"
    ./backend/scripts/run_smoke.sh

### Terminal 2（可选）：在全量 Smoke 后继续附加本地浏览器运维基线
    cd "$HOME/Desktop/文档生成系统"
    DOCGEN_RUN_LOCAL_UI_ADMIN_SMOKE=1 ./scripts/run_smoke.sh

说明：
- 当前默认 smoke 以 `/actions` 主链为准，覆盖 `tender/parse -> boq/parse -> plan/save -> generate_async -> job_status -> result/download`
- 该开关默认关闭，不影响现有 `run_smoke.sh` 默认行为
- 打开后会在核心 smoke 结束后，额外串行执行：
  - `scripts/verify_local_ui_admin_chain.sh`
- 这一步只属于本地运维基线，不属于服务器 release/worktree 工具

## 2) 8000 端口被占用时才需要做（可选）
    lsof -nP -iTCP:8000 -sTCP:LISTEN
    # 找到 PID 后执行（把 PID 换成数字）：
    kill -9 PID

## 3) 常用自检（可选）
    curl -s http://127.0.0.1:8000/openapi.json | head -n 5
    curl -s http://127.0.0.1:8000/audit | python3 -m json.tool | head -n 60
    curl -s http://127.0.0.1:8000/health | python3 -m json.tool | head -n 80
    curl -s http://127.0.0.1:8000/config | python3 -m json.tool | head -n 120

### 主链配置自检判读
- `/health` 的 `config_status.level`：
  - `ok`：主链发布所需配置齐全
  - `warn`：服务可启动，但存在鉴权、管理员接口或降级链缺口
  - `error`：真实生成链仍有阻断项，优先看 `blocking` 和 `warnings`
- `/health` 的 `config_status.release_ready=false` 时，不要直接对外发布；先处理返回里的 `warnings`
- `/config` 与 `/capabilities` 的 `runtime_config` 会列出当前单一真理源边界：
  - `backend/data/autoplan/config.json`
  - `backend/data/autoplan/agent_roles.json`
  - `kg_config.json`
  - 环境变量

## 4) 发布快照与回滚（建议变更前先做）
### 4.1 先做一次配置/KG 状态快照
    cd "$HOME/Desktop/文档生成系统"
    python3 scripts/release_snapshot.py snapshot --label before_change

输出目录：
- `build/_release_snapshots/<timestamp>_before_change/`
- 其中 `manifest.json` 会记录：
  - 当前 `config.json / agent_roles.json / quota_policy.json / kg_config.json / active_kg.json`
  - 当前主链 `runtime_config`
  - 当前 git commit / branch（若仓库可读）

### 4.2 查看最新快照
    python3 scripts/release_snapshot.py status

### 4.3 预演回滚（默认不落盘）
    python3 scripts/release_snapshot.py restore --snapshot latest

### 4.4 执行配置/KG 状态回滚
    python3 scripts/release_snapshot.py restore --snapshot latest --yes

执行后必须重新验收：
    ./scripts/run_smoke.sh

### 4.5 五类回滚边界
- 代码回滚：
  - 使用 git/worktree 回到上一已知稳定提交；快照脚本不会替你回滚代码。
- 配置回滚：
  - 用 `scripts/release_snapshot.py restore --yes` 恢复 `config.json / agent_roles.json / quota_policy.json`。
- KG 回滚：
  - 首选 `python3 scripts/kg_pack.py rollback --smoke`；
  - 若只是配置漂移，也可用发布快照恢复 `kg_config.json` 与 `backend/data/kg/active_kg.json`。
- Job 回滚：
  - 查 `backend/data/autoplan/archive/jobs/` 的 zip 和 `backend/data/autoplan/jobs/*.archived.json` tombstone。
- 交付产物回滚：
  - 优先复用 `build/actions_runs/<job_id>/`、`build/` 下上一轮已验收产物，不直接覆盖历史交付件。

## 5) 固定回归样本集（发布前必跑）
样本清单：
- `backend/data/autoplan/release_regression_suite.json`

先校验样本是否齐全：
    python3 scripts/release_regression_suite.py check

查看发布门禁样本：
    python3 scripts/release_regression_suite.py list --release-only

打印发布门禁命令：
    python3 scripts/release_regression_suite.py command --release-only

执行单个样本（默认 dry-run）：
    python3 scripts/release_regression_suite.py run --case real_baseline_summary

当前 3 组发布门禁样本：
- `real_baseline_summary`
- `real_qa_decor`
- `factory_building_with_drawing`

当前 2 组扩展样本：
- `factory_weak_current`
- `factory_hvac_core`

说明：
- 这些样本全部引用仓库内已存在的真实输入文件，不使用临时伪造文件。
- 当前自动回归口径仍受 `run_actions_pipeline.py` 约束：
  - 支持多份招标/补疑文件
  - 支持单个清单文件
  - 支持多份额外 ingest 资料（图纸/标准等）
- 因此样本定义按“每次一组清单 + 可附带补疑/图纸”组织，不把多清单整包自动回归写成既成事实。
- 样本默认使用清单内固定 outline，并关闭自动修订：
  - 目的是把门禁目标收敛为“真实输入仍能稳定跑通主链”
  - 不把发布前门禁变成长文生产压测

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
