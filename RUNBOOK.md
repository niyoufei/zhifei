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

