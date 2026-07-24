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

## 3.3) Phase 1 本地静态路线（不启动服务）

文档入口：

    docs/openclaw-zhifei-doc-p0-readiness.md
    docs/openclaw-zhifei-doc-phase1-local-baseline.md
    docs/openclaw-zhifei-doc-phase1b-demo-workflow.md
    docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md
    docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md
    docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_demo_workflow
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_demo_workflow.py --json
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_delivery_index
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_delivery_index.py --json
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase1_static_matrix
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_static_matrix.py --json

clean worktree 后的预期状态：

- P0: `PASS_P0_READINESS_STATIC`
- Phase 1B: `PASS_PHASE1B_DEMO_WORKFLOW_STATIC`
- Phase 1C: `PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC`
- Phase 1E: `PASS_PHASE1E_STATIC_TEST_MATRIX`

常见诊断：

- `worktree_not_clean`：当前还有未提交或未跟踪文件；完成授权范围内的本地 docs-only commit 后重跑。
- `git_index_lock_present`：`.git/index.lock` 存在；先停止并进入单独 git 锁处理决策。
- `required_entries_missing`：静态入口缺失；先恢复缺失文件或重新确认范围。
- `sanitized_demo_project_missing_or_invalid`：只修复脱敏 demo metadata，不得替换为真实业务资料。
- `p0_readiness_static_pass`：先回到 P0 JSON 的 `failures` 列表排查。
- `phase1b_static_demo_workflow_pass`：先回到 Phase 1B JSON 的 `failures` 列表排查。

Phase 1D 当前成果是 docs / RUNBOOK closure。Phase 1E 当前成果是 static test matrix；该入口仍不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文或读取真实业务资料。Phase 1E 通过后，下一步只能建议 `PHASE1_LOCAL_STATIC_BASELINE_CLOSEOUT_READONLY`，不得自动进入 Phase 2 代码建设。

硬闸门关系：

- runtime smoke gate：单独决定是否允许启动服务。
- endpoint smoke gate：单独决定是否允许访问 `/health`、`/p0/readiness`、`/openapi.json`、`/list_files`、`/read_file` 或业务 endpoint。
- launcher smoke gate：单独决定是否允许启动或操作 launcher。
- config content review gate：单独决定是否允许读取 `local-launcher-v1/mock-config.json` 正文。

以上 gate 互相独立；P0、Phase 1B、Phase 1C 或 Phase 1D 通过，都不等于 runtime、endpoint、launcher 或 config content review 已获准。

## 3.4) Phase 2A business input contract（静态写门）

Phase 2A 入口：

    docs/openclaw-zhifei-doc-phase2-business-input-contract.md
    projects/_demo_phase2_business_input/project.json
    backend/zhifei_autoplan/phase2_business_input_contract.py
    scripts/phase2_business_input_contract.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_business_input_contract
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_business_input_contract.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_business_input_contract.py --json

clean worktree 后的预期状态：

- Phase 2A: `PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC`

常见诊断：

- `synthetic_fixture_missing`：恢复 Phase 2A synthetic fixture。
- `required_nested_fields_present`：补齐业务输入契约必填字段。
- `no_real_doc_body_like_fields`：删除正文类字段，不得塞入真实招标/图纸/清单/客户资料正文。
- `no_secret_like_fields`：删除 credential-like 字段或值。
- `forbidden_action_flags_false`：runtime、endpoint、launcher、held config body、真实资料正文、secret、remote sync、export、formal writeback 标记必须为 false。

Phase 2A 只建立业务输入契约、脱敏合成样例、静态 validator/CLI 和测试。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 `PHASE2B_SCORING_RESPONSE_MATRIX_PLAN_OR_WRITE_GATE`，不得自动进入 Phase 2B。

## 3.5) Phase 2B scoring response matrix（静态写门）

Phase 2B 入口：

    docs/openclaw-zhifei-doc-phase2b-scoring-response-matrix.md
    projects/_demo_phase2_scoring_response_matrix/project.json
    backend/zhifei_autoplan/phase2_scoring_response_matrix.py
    scripts/phase2_scoring_response_matrix.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_scoring_response_matrix
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_scoring_response_matrix.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_scoring_response_matrix.py --json

clean worktree 后的预期状态：

- Phase 2B: `PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC`

常见诊断：

- `scoring_items_present`：恢复至少一个 synthetic scoring item。
- `scoring_item_ids_unique`：修复重复或空 scoring item id。
- `max_scores_valid`：`max_score` 必须是大于 0 的数字。
- `response_strategies_present`：补齐非空 response strategy。
- `required_evidence_present`：补齐 evidence metadata anchors。
- `linked_engineering_objects_known`：只引用 fixture 中存在的 engineering object id。
- `qingtian_matrix_fields_present`：补齐 scoring category、Qingtian keywords 和 parse tags。
- `no_real_doc_body_like_fields`：删除正文类字段，不得塞入真实招标/图纸/清单/客户资料正文。
- `no_secret_like_fields`：删除 credential-like 字段或值。
- `forbidden_action_flags_false`：runtime、endpoint、launcher、held config body、真实资料正文、secret、remote sync、export、formal writeback 标记必须为 false。

Phase 2B 只生成静态 scoring response matrix、脱敏合成样例、静态 validator/CLI 和测试。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 `PHASE2C_RISK_OBJECT_BINDING_PLAN_OR_WRITE_GATE`，不得自动进入 Phase 2C。

## 3.6) Phase 2C risk object binding（静态写门）

Phase 2C 入口：

    docs/openclaw-zhifei-doc-phase2c-risk-object-binding.md
    projects/_demo_phase2_risk_object_binding/project.json
    backend/zhifei_autoplan/phase2_risk_object_binding.py
    scripts/phase2_risk_object_binding.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_risk_object_binding
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_risk_object_binding.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_risk_object_binding.py --json

clean worktree 后的预期状态：

- Phase 2C: `PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC`

常见诊断：

- `phase2b_matrix_pass`：先修复同一 synthetic fixture 的 Phase 2B matrix 校验。
- `risk_clues_present`：恢复至少一个 synthetic risk clue。
- `risk_ids_unique`：修复重复或空 risk id。
- `risk_levels_valid`：risk level 只能是 `low`、`medium`、`high`、`critical`。
- `linked_engineering_objects_known`：只引用 fixture 中存在的 engineering object id。
- `linked_scoring_items_known`：只引用 Phase 2B matrix 中存在的 scoring item id。
- `response_control_points_present`：补齐 response control points。
- `required_evidence_present`：补齐 evidence metadata anchors。
- `qingtian_tags_present`：补齐 Qingtian-friendly tags。
- `no_real_doc_body_like_fields`：删除正文类字段，不得塞入真实招标/图纸/清单/客户资料正文。
- `no_secret_like_fields`：删除 credential-like 字段或值。
- `forbidden_action_flags_false`：runtime、endpoint、launcher、held config body、真实资料正文、secret、remote sync、export、formal writeback 标记必须为 false。

Phase 2C 只生成静态 risk-object binding、脱敏合成样例、静态 validator/CLI 和测试。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 `PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_PLAN_OR_WRITE_GATE`，不得自动进入 Phase 2D。

## 3.7) Phase 2D Qingtian friendly checklist（静态写门）

Phase 2D 入口：

    docs/openclaw-zhifei-doc-phase2d-qingtian-friendly-checklist.md
    projects/_demo_phase2_qingtian_friendly_checklist/project.json
    backend/zhifei_autoplan/phase2_qingtian_friendly_checklist.py
    scripts/phase2_qingtian_friendly_checklist.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_qingtian_friendly_checklist
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_qingtian_friendly_checklist.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_qingtian_friendly_checklist.py --json

clean worktree 后的预期状态：

- Phase 2D: `PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC`

常见诊断：

- `phase2b_matrix_pass`：先修复同一 synthetic fixture 的 Phase 2B matrix 校验。
- `phase2c_binding_pass`：先修复同一 synthetic fixture 的 Phase 2C binding 校验。
- `checklist_covers_scoring_items`：每个 Phase 2B scoring item 至少需要一个 checklist item。
- `qingtian_keywords_present`：补齐 Qingtian-friendly keywords。
- `qingtian_parse_tags_present`：补齐 Qingtian-friendly parse tags。
- `linked_scoring_items_known`：只引用 Phase 2B matrix 中存在的 scoring item id。
- `linked_engineering_objects_known`：只引用 fixture 中存在的 engineering object id。
- `linked_risks_known`：如提供 risk id，只能引用 Phase 2C binding 中存在的 risk id。
- `evidence_requirements_present`：补齐 evidence metadata anchors。
- `traceability_requirements_present`：补齐 Phase 2B / Phase 2C traceability anchors。
- `affects_score_false`：该 checklist 只能 static / preview-only，必须保持 `affects_score=false`。
- `official_score_claim_false`：不得声明正式评分结果。
- `no_official_score_like_fields`：删除任何评分结果类字段。
- `no_real_doc_body_like_fields`：删除正文类字段，不得塞入真实招标/图纸/清单/客户资料正文。
- `no_secret_like_fields`：删除 credential-like 字段或值。
- `forbidden_action_flags_false`：runtime、endpoint、launcher、held config body、真实资料正文、secret、remote sync、export、formal writeback 标记必须为 false。

Phase 2D 只生成 static / preview-only Qingtian-friendly checklist、脱敏合成样例、静态 validator/CLI 和测试；不代表真实评标结果，不输出评分结果，不连接真实青天系统。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 `PHASE2E_FINAL_REVIEW_ISSUE_LIST_PLAN_OR_WRITE_GATE`，不得自动进入 Phase 2E。

## 3.8) Phase 2E final review issue list（静态写门）

Phase 2E 入口：

    docs/openclaw-zhifei-doc-phase2e-final-review-issue-list.md
    projects/_demo_phase2_final_review_issue_list/project.json
    backend/zhifei_autoplan/phase2_final_review_issue_list.py
    scripts/phase2_final_review_issue_list.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_final_review_issue_list
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_final_review_issue_list.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_final_review_issue_list.py --json

clean worktree 后的预期状态：

- Phase 2E: `PASS_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC`

常见诊断：

- `phase2a_contract_pass`：先修复同一 synthetic fixture 的 Phase 2A contract 校验。
- `phase2b_matrix_pass`：先修复同一 synthetic fixture 的 Phase 2B matrix 校验。
- `phase2c_binding_pass`：先修复同一 synthetic fixture 的 Phase 2C binding 校验。
- `phase2d_checklist_pass`：先修复同一 synthetic fixture 的 Phase 2D checklist 校验。
- `issue_ids_unique`：修复重复或空 issue id。
- `severity_values_valid`：severity 只能是 `info`、`low`、`medium`、`high`、`blocking`。
- `source_phases_valid`：source phase 只能是 `P2A`、`P2B`、`P2C`、`P2D`、`cross_phase`。
- `linked_scoring_items_known`：只引用 Phase 2B matrix 中存在的 scoring item id。
- `linked_engineering_objects_known`：只引用 fixture 中存在的 engineering object id。
- `linked_risks_known`：只引用 Phase 2C binding 中存在的 risk id。
- `linked_checklists_known`：只引用 Phase 2D checklist 中存在的 checklist id。
- `diagnostic_evidence_present`：补齐非空 diagnostic evidence。
- `recommended_action_present`：补齐非空 recommended action。
- `formal_writeback_allowed_false`：该 issue list 只能 static / preview-only，必须保持 formal writeback blocked。
- `export_allowed_false`：不得导出成果。
- `official_score_claim_false`：不得声明正式评分结果。
- `no_official_score_like_fields`：删除任何评分结果类字段。
- `no_real_doc_body_like_fields`：删除正文类字段，不得塞入真实招标/图纸/清单/客户资料正文。
- `no_secret_like_fields`：删除 credential-like 字段或值。
- `forbidden_action_flags_false`：runtime、endpoint、launcher、held config body、真实资料正文、secret、remote sync、export、formal writeback 标记必须为 false。

Phase 2E 只生成 static / preview-only final review issue list、脱敏合成样例、静态 validator/CLI 和测试；不代表正式终审结论，不写回文件，不导出成果，不输出官方评分，不连接真实青天系统。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 `PHASE2F_OUTPUT_PRE_INDEX_PLAN_OR_WRITE_GATE`，不得自动进入 Phase 2F。

## 3.9) Phase 2F output pre-index（静态写门）

Phase 2F 入口：

    docs/openclaw-zhifei-doc-phase2f-output-pre-index.md
    projects/_demo_phase2_output_pre_index/project.json
    backend/zhifei_autoplan/phase2_output_pre_index.py
    scripts/phase2_output_pre_index.py

静态复核命令：

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 -m unittest backend.tests.test_phase2_output_pre_index
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_output_pre_index.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase2_output_pre_index.py --json

clean worktree 后的预期状态：

- Phase 2F: `PASS_PHASE2F_OUTPUT_PRE_INDEX_STATIC`

常见诊断：

- `phase2a_contract_pass`：先修复同一 synthetic fixture 的 Phase 2A contract 校验。
- `phase2b_matrix_pass`：先修复同一 synthetic fixture 的 Phase 2B matrix 校验。
- `phase2c_binding_pass`：先修复同一 synthetic fixture 的 Phase 2C binding 校验。
- `phase2d_checklist_pass`：先修复同一 synthetic fixture 的 Phase 2D checklist 校验。
- `phase2e_issue_list_pass`：先修复同一 synthetic fixture 的 Phase 2E issue list 校验。
- `required_output_entry_fields_present`：补齐 output pre-index entry 必填字段。
- `output_types_valid`：output type 必须在 Phase 2F enum 内。
- `export_status_allowed`：export status 只能是 `blocked` 或 `preview_only`。
- `writeback_not_performed`：不得声明 formal writeback 已执行。
- `official_score_not_generated`：不得声明 official score 已生成。
- `artifact_generation_not_generated`：不得声明文件成果已生成。
- `data_boundary_blocks_forbidden_reads`：held config body、真实资料正文、secret、runtime、endpoint 声明必须保持 blocked/false。
- `trace_links_known`：trace link 只能指向 Phase 2A-2E 静态对象或 synthetic fixture。

Phase 2F 只生成 static / preview-only output pre-index、脱敏合成样例、静态 validator/CLI 和测试；不生成报告、矩阵、问题清单、审计索引、交付包、Markdown/HTML/DOCX/PDF/Excel/PPTX 成果文件，不代表 release-ready，不代表 official score ready。不得启动 runtime、访问 endpoint、启动 launcher、读取 held config 正文、读取真实业务资料正文、导出成果、正式写回、push/fetch/merge。下一阶段只能建议 Phase 2 closeout 的只读计划或闸门，不得自动进入 Phase 2 closeout 或 Phase 3。

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
