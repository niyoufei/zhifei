# SYSTEM-AUTONOMY-005 Goal Mode Code Change Proposal Gate

## 1. 节点定位

`SYSTEM-AUTONOMY-005-GOAL-MODE-CODE-CHANGE-PROPOSAL-GATE` 是 ZDoc / 本地 AI 应用 / 系统自治建设路线的代码修改方案 Gate。

本节点承接：

1. `SYSTEM-AUTONOMY-001-GOAL-MODE-GOVERNANCE-AND-ROADMAP-GATE`
2. `SYSTEM-AUTONOMY-002-GOAL-MODE-TASK-DECOMPOSITION-GATE`
3. `SYSTEM-AUTONOMY-003-GOAL-MODE-PERMISSION-MATRIX-AND-STATE-MACHINE-GATE`
4. `SYSTEM-AUTONOMY-004-GOAL-MODE-CODEBASE-READ-ONLY-INVENTORY-AUTHORIZATION-GATE`

本节点仅形成后续代码修改 proposal，不实施、不改代码、不运行、不测试、不验证 runtime。本节点不是 runtime ready、不是 endpoint ready、不是 dry-run ready、不是 trial ready、不是正式使用 ready。

当前仍未进入代码实现状态。任何代码修改、测试执行、runtime preflight、endpoint 访问、Ollama / 模型命令、模型推理、prompt 输入、真实 KG / 真实项目资料读取、output/job/export/log 正文读取、generation/export/write-back 均需要后续 Gate 另行授权。

## 2. 当前状态机定位

| 字段 | 当前结论 |
| --- | --- |
| 当前状态 | `S5_CODE_CHANGE_PROPOSAL` |
| 状态含义 | 只提出代码修改目标、边界、风险、顺序、最小变更集、静态校验和回滚建议 |
| 当前允许 | 读取授权 docs 与 004 盘点范围内相关源码；新增本节点唯一 docs 文件 |
| 当前禁止 | 直接改代码、脚本、配置、测试、静态 UI、数据文件；生成代码补丁；运行服务；访问 endpoint；执行测试；触发模型或 runtime |
| 不得进入 | `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME` |
| 不得进入 | `S7_STATIC_VALIDATION_ONLY` |
| 不得进入 | 任何 runtime / endpoint / dry-run / trial 状态 |

本节点完成后必须停止，等待 ChatGPT 总控师审核。

## 3. Proposal 依据与读取边界

本 proposal 基于 001-004 已形成的治理框架、任务分解、权限矩阵、状态机和代码库只读盘点结果。004 已将后续候选改动面限定为 guard/checker/schema/report/template 等不触发 runtime 的对象。

本节点只使用受限源码事实形成方案，不读取真实 KG、真实项目资料、招标文件、图纸、清单、项目样本、secrets、tokens、credentials、output/job/export/生成结果/日志正文，不执行任何命令型 runtime 验证。

## 4. 代码修改候选清单

下表仅为后续 `SYSTEM-AUTONOMY-006` 或更后续 Gate 的方案候选。005 不实施任何一项。

| 候选项 | 修改目标 | 涉及文件路径 | 当前代码角色 | 建议修改类型 | 是否新增文件 | 是否修改既有文件 | 是否需要测试 | 是否涉及 runtime | 是否涉及 endpoint | 是否涉及 Ollama / 模型命令 | 是否涉及模型推理 | 是否涉及 prompt | 是否涉及真实 KG | 是否涉及真实项目资料 | 是否涉及 output/job/export/log | 风险等级 | 审批等级 | 推荐进入的后续 Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 权限守卫 | 将系统自治节点的允许命令、禁止命令、允许文件、禁止路径和状态停止点固化为静态检查 | `scripts/guards/zdoc_guard.py`; 可选授权测试 `backend/tests/test_zdoc_guard_*.py` | 已有 PR/task scope、risky command、scope、artifact count、tag precheck 检查器 | 扩展常量、枚举、任务 spec 字段和只读校验逻辑 | 默认否；如需测试可在 006 单独授权新增测试 | 是，仅 `zdoc_guard.py` 或授权测试 | 是，最小 guard 单测 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 仅可统计数量，不读正文 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| 状态机配置 | 将 003 的 S0-S15/SX 状态、转换、审批等级转成机器可读常量 | `scripts/guards/zdoc_guard.py`; 可选未来独立配置文件须另行授权 | 目前状态机仅在 docs 中，guard 未内置系统自治状态枚举 | 新增静态常量、枚举校验、状态转换 allowlist | 默认否；独立配置文件需 006 明确授权 | 是，优先改既有 guard | 是，枚举锁定测试 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| 审批 Gate 检查器 | 将人审、diff、rollback、source hash、formal flag 全部转成节点准入报告 | `backend/zhifei_autoplan/human_approval_gate.py`; `backend/zhifei_autoplan/formal_writeback_guard.py` | 已有 approval/writeback 契约字段、blocked reasons、formal flags false | 扩展只读 metadata 字段、审批等级、系统自治 Gate reason code | 否 | 是 | 是，现有 approval/writeback guard 最小单测 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| code-read-only inventory 检查器 | 校验实际读取路径是否在 allowlist，禁止读取敏感路径、真实资料和运行产物正文 | `scripts/guards/zdoc_guard.py` | 已能检查 changed files、allowed/forbidden files、artifact counts | 新增 read-scope spec 和禁止路径扫描规则 | 默认否 | 是 | 是，路径匹配和禁止路径测试 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 只允许数量或路径，不读正文 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| 禁止项扫描器 | 扫描 task spec / command spec 中的 service、HTTP、localhost、Ollama、generation、export、write-back 风险 | `scripts/guards/zdoc_guard.py` | 已有 risky command reason，覆盖 Ollama、service、network、generation/export、destructive git | 补全 endpoint、localhost、port probe、PID/log、runtime script、model prompt 关键词 | 否 | 是 | 是，risky command 表驱动测试 | 否 | 否；仅扫描文本 | 否 | 否 | 否 | 否 | 否 | 否 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| runtime preflight 检查清单 | 只生成未来 preflight 所需 checklist，不执行服务启动、端口探测或 PID 操作 | `scripts/guards/zdoc_guard.py`; 006 docs 输出可选 | 004 已列出 runtime 脚本、服务入口和 endpoint 风险 | 新增 metadata-only checklist 模板或 docs template | 可选 docs；代码新增需另行授权 | 可选 | 否或静态 schema 测试 | 否，本层不执行 preflight | 否 | 否 | 否 | 否 | 否 | 否 | 不读 log/PID 正文 | 高 | A4 前置 | `SYSTEM-AUTONOMY-006` 仅可预留；执行 preflight 需后续独立 Gate |
| dry-run / mock-run 隔离层 | 强化 dry-run 只能保持 metadata-only / shadow-only，不能变成真实写回、导出或 prompt 执行 | `backend/zhifei_autoplan/formal_writeback_dry_run.py`; `backend/app/routers/local_trial_preview_only.py`; `backend/app/routers/local_llm_preview_safe.py` | 已有 dry-run、preview-only、safe endpoint blocked flags 和 formal output field 清理 | 补强状态枚举、blocked reasons、formal output field denylist、no-write flags | 否 | 是 | 是，现有 dry-run/local trial/local LLM 最小单测 | 否 | 仅 TestClient 类静态/单测建议，006 默认不得访问真实 endpoint | 默认否；local LLM real adapter 仍需独立授权 | 否 | 否，prompt 输入仍禁止 | 否 | 否 | 禁止写入和读取正文 | 高 | A3/A5 前置 | `SYSTEM-AUTONOMY-006` 仅实现隔离字段；实际 dry-run 需后续 Gate |
| 证据链生成模板 | 统一 HEAD、tag、status、读取文件、变更文件、禁止项显式否定、校验证据字段 | `scripts/guards/zdoc_guard.py`; `backend/zhifei_autoplan/human_approval_gate.py`; `backend/zhifei_autoplan/formal_writeback_guard.py` | guard 已有 `pr-summary`; approval/writeback 已有 required fields | 扩展 report schema、required evidence fields、缺失字段阻断 | 默认否 | 是 | 是，required fields / report shape 测试 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 不读运行产物正文 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| 回滚记录模板 | 只生成回滚建议字段，不执行 reset/checkout/delete/clean | `backend/zhifei_autoplan/formal_writeback_guard.py`; `backend/zhifei_autoplan/formal_writeback_dry_run.py`; `scripts/guards/zdoc_guard.py` | 已有 rollback required/ready/hash/status 字段和 destructive git 阻断 | 增加 rollback record schema、rollback authorization status、destructive action denylist | 默认否 | 是 | 是，rollback missing / destructive command blocked 测试 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 中 | A3 | `SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE` |
| trial 前冻结检查表 | 在进入 trial 前检查支持、回滚、审计、风险接受、禁止正式使用的冻结条件 | 006 docs 输出; 可选 `scripts/guards/zdoc_guard.py` report 字段 | 003 已定义 trial / production 状态和 A7/A8 审批等级 | docs template 或 metadata-only guard report 字段 | 可选 docs，代码新增需另行授权 | 可选 | 否或 report schema 测试 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 高 | A7/A8 前置 | later trial readiness Gate；006 不应进入 trial |
| 文档与开发者提示边界 | 把 README/RUNBOOK/开发者提示中的启动、curl、endpoint、模型、真实资料命令标注为需独立授权 | `README.md`; `RUNBOOK.md`; `scripts/guards/README.md`; 006 docs 输出 | README/RUNBOOK 含启动、curl、compose/export/audit、KG pack 说明 | 文档边界说明或 guard README 更新 | 默认否 | 是，仅后续 docs Gate 授权 | 否或 markdown/text check | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 中 | A1/A3 | 可拆 docs-only Gate 或 `SYSTEM-AUTONOMY-006` 明确授权 |

统一限制：

1. 以上候选均不得在 005 实施。
2. 006 若获授权，也默认只允许 no-runtime 代码实现。
3. 任何涉及服务启动、endpoint、Ollama、模型推理、prompt、真实 KG、真实项目资料、output/job/export/log 正文、generation/export/write-back 的行为都必须另开更高等级 Gate。

## 5. 最小变更集建议

| 层级 | 目标 | 涉及文件 | 是否可独立提交 | 是否不触发 runtime | 是否需要测试 | 失败回滚方式 | 是否建议进入 006 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1：仅文档/配置常量层 | 固化系统自治节点名、状态名、审批等级、禁止项关键词，不改变执行行为 | `scripts/guards/zdoc_guard.py`; 或 006 目标 docs | 是 | 是 | 建议最小常量/文本检查；不跑 runtime | 新提交回滚或 revert；不 reset/checkout/delete | 是，作为最小首选 |
| M2：状态机与权限枚举层 | 将 S0-S15/SX、A0-A8、允许/禁止维度转成枚举并拒绝未知状态 | `scripts/guards/zdoc_guard.py`; 可选授权测试 | 是 | 是 | 需要枚举锁定测试 | revert 该枚举提交；保留 docs 证据 | 是 |
| M3：只读检查器层 | 检查 read allowlist、forbidden read paths、actual read report 是否闭合 | `scripts/guards/zdoc_guard.py` | 是 | 是 | 需要路径匹配和禁止路径测试 | revert checker 提交；保留失败 report | 是 |
| M4：阻断规则层 | 补强 service/HTTP/localhost/port/Ollama/model/prompt/KG/output/job/export/log/generation/write-back 扫描 | `scripts/guards/zdoc_guard.py`; `human_approval_gate.py`; `formal_writeback_guard.py`; `formal_writeback_dry_run.py` | 可拆分提交，优先 guard 后 schema | 是 | 需要表驱动单测 | revert 对应阻断规则；不得放宽禁止项 | 是，但必须拆小 |
| M5：证据链模板层 | 统一回报字段、缺失证据阻断、禁止项显式否定、rollback record 字段 | `scripts/guards/zdoc_guard.py`; `human_approval_gate.py`; `formal_writeback_guard.py` | 是 | 是 | 需要 required fields / report shape 测试 | revert 模板提交；保留旧模板 | 是 |
| M6：后续 runtime preflight 预留层 | 仅预留未来 preflight checklist 字段，不执行任何 preflight | 006 docs 或 `scripts/guards/zdoc_guard.py` metadata-only 字段 | 可独立提交，但建议最后 | 是，本层不得执行 preflight | 可不测；若进 guard 需 schema 测试 | revert 预留字段；不得用失败补跑 runtime | 谨慎进入 006；仅允许预留，不允许执行 |

建议最小闭环为 M1 -> M2 -> M3。M4-M5 需在 006 明确授权后按文件拆分。M6 只能作为预留，不得被解释为 runtime preflight 授权。

## 6. 不允许修改清单

后续即使进入 006，也默认不允许修改或读取正文的对象包括：

1. secrets / credentials / token / certificate / private key / `.env` / `.env.*` 相关文件。
2. 真实 KG：`知识图谱/*.json`、`knowledge_graph/`、`backend/data/kg/`、`kg_packs/`、`backend/kg_packs/` 及其他 KG 正文。
3. 真实项目资料、招标文件、图纸、清单、项目样本、上传资料、抽取正文、项目样本目录。
4. output / job / export / log 正文，包括生成结果、运行日志、导出物、job payload/result、audit/extract 正文。
5. 真实生成结果、真实模型输入输出、真实 prompt、真实 evidence、真实 scoring 内容。
6. production 运行配置、真实部署配置、实际 LaunchAgent/systemd 生效配置。
7. 会直接启动服务的脚本，例如 `scripts/run_web_ui.sh`、`scripts/start_web_ui_background.sh`、`scripts/web_ui_watchdog.sh`、launchd install 脚本。
8. 会直接访问 endpoint、curl、HTTP request、localhost、端口探测的脚本或命令。
9. 会直接调用 Ollama / 模型命令 / 模型 API / 模型推理的脚本或代码路径。
10. 会触发 generation/export/write-back/review-apply/download/cleanup/delete 的脚本、route 或 helper。
11. `local-launcher-v1` 静态文件，除非后续静态 UI Gate 单独授权。
12. runtime/server/endpoint/API/model/KG 接入代码的新增能力，除非后续 Gate 明确只做 no-runtime guard 级改动。

## 7. 实现顺序建议

后续如 ChatGPT 总控师批准进入 `SYSTEM-AUTONOMY-006`，建议顺序如下：

1. 先定义权限枚举：节点名、状态名、审批等级、允许/禁止维度、禁止路径类别。
2. 再定义状态机：只固化 S5 -> S6 的人工审批前置条件和任意状态 -> SX 的阻断条件。
3. 再定义 Gate 检查器：校验目标文件唯一、状态合法、allowlist 完整、禁止项否定字段完整。
4. 再定义禁止项扫描器：覆盖 runtime、service、Web UI、curl/HTTP/localhost/port、Ollama、model command、model inference、prompt、real KG、real project data、output/job/export/log、generation/export/write-back。
5. 再定义证据链模板：HEAD/tag/status、read scope、changed files、validation result、commit/tag、stop confirmation。
6. 再定义 dry-run 隔离预留：仅 metadata-only / shadow-only 字段，不触发实际 dry-run。
7. 最后进行静态校验：只运行 006 明确允许的语法、类型、单测或文本检查。
8. 不得提前进入 runtime preflight。runtime preflight 必须另行 Gate 审批。

## 8. 不触发 runtime 的实现策略

后续 006 的实现策略应满足：

1. 只修改纯检查器、契约字段、静态枚举、metadata-only report 或 docs 模板。
2. 不新增服务入口、不新增 route、不注册 endpoint、不改变 FastAPI/Flask/Streamlit 启动行为。
3. 不新增模型 provider、KG loader、generation chain、export/write-back chain。
4. 不读取运行产物正文，不读取真实资料正文。
5. 不通过 TestClient、curl、browser、localhost、端口探测替代静态校验，除非后续 Gate 明确授权。
6. 所有 blocked flags 默认 false/blocked/no-write/no-generation/no-export/no-model/no-KG。
7. 所有回滚动作只写建议，不执行 destructive git 操作。

## 9. 静态校验策略

本节点不得执行以下校验；仅说明后续 006 或 007 可在明确授权后使用的策略。

| 校验类型 | 建议策略 | 边界 |
| --- | --- | --- |
| 语法级检查 | 对被授权 Python 文件运行最小语法检查或目标文件级测试命令 | 只在 006/007 授权后执行；不得启动服务 |
| 类型级检查 | 对新增枚举、TypedDict、schema 字段做目标文件级类型/导入检查 | 不导入会触发 runtime 的 app 主入口；不读取 env/secrets |
| 文档一致性检查 | 检查 005/006 文档中的状态名、Gate 名、commit/tag、禁止项是否一致 | 只读授权 docs |
| 禁止项扫描 | 使用 guard 对命令 spec、变更文件、禁止路径、risky command 做扫描 | 不执行被扫描命令 |
| git diff 范围检查 | `git diff --check -- <authorized files>`、`git diff --cached --name-status`、目标文件范围核对 | 只检查授权变更，不做 reset/checkout/delete |
| 最小单测 | 仅运行与改动文件直接相关的一条测试，例如 guard enum、approval guard、writeback guard、dry-run contract | 006/007 未授权前不得运行；不得跑大套件 |
| 无 runtime 边界 | 明确不运行 `run_web_ui.sh`、uvicorn、streamlit、Flask、curl、HTTP request、localhost、端口探测、Ollama、模型命令 | runtime 证据缺失不得用探测补证 |

## 10. 风险与阻断规则

| 风险 | 阻断规则 | 回滚建议 |
| --- | --- | --- |
| 误改 runtime 脚本风险 | 006 默认禁止修改 `scripts/run_web_ui.sh`、background/watchdog/launchd/systemd 启动相关文件；出现这些文件即停止 | 不提交；若已改，仅建议 revert 该提交，等待授权 |
| 误触发服务启动风险 | 禁止执行 uvicorn、streamlit、Flask app run、service、launchd、watchdog、`./scripts/run_web_ui.sh --background` | 立即停止；不追加检查；记录未执行或误执行事实 |
| 误访问 endpoint 风险 | 禁止 curl、HTTP request、localhost、端口探测、browser preview、HTML 页面打开 | 停止并回报目标地址/命令；不得用返回结果补证 |
| 误调用 Ollama / 模型命令风险 | 禁止 `ollama`、模型 CLI、provider API、model inventory、model generate/chat/run | 停止；不复述 prompt/output；等待模型 Gate |
| 误读取真实 KG / 项目资料风险 | 禁止打开 KG、真实项目资料、招标文件、图纸、清单、项目样本正文 | 停止；只回报路径类别，不复述内容 |
| 误读取 secrets 风险 | 禁止读取 `.env`、token、credential、cert、private key、敏感 env 值 | 立即停止；不复述敏感值；等待安全 Gate |
| 误读取 output/job/export/log 风险 | 禁止读取生成结果、job payload/result、export、audit/extract、运行日志正文 | 停止；不得把该内容写入证据链 |
| 证据链不足风险 | 任一字段无法由授权证据支撑时，不补写结论、不跳过字段 | 回到对应 docs/guard proposal；等待补充授权 |
| tag / commit / clean 状态不一致风险 | HEAD、tag、status、staged files 或 target file 范围不符时停止，不继续提交或 tag | 仅回报实际状态；执行回滚须另行授权 |

## 11. 后续 Gate 建议

建议下一节点名称为：

`SYSTEM-AUTONOMY-006-CONTROLLED-CODE-IMPLEMENTATION-NO-RUNTIME-GATE`

006 建议定位：

1. 006 只能在 ChatGPT 总控师审核 005 后执行。
2. 本节点不得进入 006。
3. 006 是否允许目标模式，必须由 ChatGPT 总控师审核后决定。
4. 006 是否允许代码修改，必须由 ChatGPT 总控师审核后决定。
5. 006 默认仍禁止 runtime。
6. 006 默认禁止 endpoint。
7. 006 默认禁止 Ollama。
8. 006 默认禁止模型推理。
9. 006 默认禁止 prompt。
10. 006 默认禁止真实 KG / 真实项目资料。
11. 006 默认禁止 output/job/export/log 正文读取。
12. 006 默认禁止 generation/export/write-back。
13. 006 必须由 ChatGPT 总控师明确授权后才可执行。

建议 006 的最小授权目标为 M1-M3：权限枚举、状态机枚举、只读检查器。M4-M6 应拆分为后续小提交或独立 Gate，避免一次性扩大改动范围。

## 12. 本节点结论

`SYSTEM-AUTONOMY-005-GOAL-MODE-CODE-CHANGE-PROPOSAL-GATE` 的结论如下：

1. 本节点已形成代码修改方案 Gate。
2. 本节点承接 001-004，但不继承任何 runtime、endpoint、Ollama、模型、真实资料、generation/export/write-back 授权。
3. 本节点仅新增目标 docs 文件。
4. 本节点未修改代码、脚本、配置、测试、静态 UI、数据文件。
5. 本节点未创建 patch 文件，未生成可直接应用的代码补丁。
6. 本节点保持在 `S5_CODE_CHANGE_PROPOSAL`。
7. 本节点不进入 `S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME`。
8. 本节点不进入 `S7_STATIC_VALIDATION_ONLY`。
9. 本节点不进入任何 runtime / endpoint / dry-run / trial 状态。
10. 本节点完成后必须停止，等待 ChatGPT 总控师审核。
