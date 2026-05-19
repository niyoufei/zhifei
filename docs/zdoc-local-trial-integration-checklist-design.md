# ZDoc Local Trial Integration Checklist Design

## 1. Scope

Step 141 仅设计 ZDoc / 文档生成系统与 ZBid / 评标系统在本地化部署基础闭环和小范围试用前的集成检查清单。本文档用于后续试用前的人工核查、边界复核、启动条件确认、风险项登记和后续联调准备。

本步是 docs-only 设计，不执行部署，不启动服务，不运行模型，不运行 Ollama，不访问 `127.0.0.1:11434`，不调用外部模型或 API，不进行 ZDoc / ZBid 实际联调，不进入 50 人团队正式部署设计。

当前总体策略已调整为：

- 先完成本地化部署基础闭环。
- 再完成 ZDoc 与 ZBid 的 preview-only 对接。
- 再进行小范围试用和问题修正。
- 最后再按约 50 人同时使用场景进行正式部署设计。

本文档不代表已启动服务，不代表已完成联调，不代表已进入 50 人部署。本文档只提供后续试用前的检查项、验收项、阻断项和退出条件。

本步不设计 Mac Studio / NAS / UPS / Redis / PostgreSQL 等正式部署配置，不编写部署脚本，不修改启动脚本，不修改服务配置文件。

## 2. Current Safety Baseline

当前安全基线已经通过一系列 contract design、fake schema tests、fake-only helper 和 stage review 固化，但多数仍处于 fake-only metadata / contract / tests / docs 阶段，不代表运行时正式能力。

已固化或已设计的安全基线包括：

- preview-only advisory。
- quality gate。
- input risk。
- evidence anchor。
- response mode。
- shadow readiness。
- shadow candidate envelope。
- shadow candidate patch。
- human approval gate。
- diff preview。
- rollback plan。
- formal writeback guard。
- source hash revalidation guard。
- review/apply isolation guard。
- DOCX isolation guard。
- ZBid isolation guard。
- formal writeback dry-run。

当前所有 guard / isolation / dry-run 仍为 fake-only metadata 或 docs/tests 固化状态。不得把 fake helper 视为正式写回、DOCX 导出、ZBid 写回、review/apply 或 `output/job/export` 写入能力。

当前不得把 preview advisory、shadow candidate、patch preview、diff preview、rollback plan、dry-run result 当作 evidence。

当前不得绕过 human approval、diff、rollback、source hash revalidation、review/apply isolation、DOCX isolation、ZBid isolation。

当前所有正式链 flags 仍应保持 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

小范围试用必须先以 preview-only / no-write 模式进行，不得开放正式写回。

## 3. Trial Objectives

本地试用阶段的重点是验证“可启动、可访问、可复核、可预览、可阻断、可回滚设计、可审计”，不是验证高并发，也不是验证 50 人同时使用。

小范围试用目标包括：

- 本地系统可启动。
- 前端可访问。
- 后端健康检查可读。
- 本地模型状态可见，但不得自动写回。
- ZDoc 可生成 preview-only 结果。
- ZBid 可接收 preview-only / metadata-only 测试输入。
- DOCX / ZBid / review/apply / formal writeback 均默认 blocked。
- 所有关键动作可审计。
- 失败可定位。
- 不写 `output/job/export`。
- 不触发真实 DOCX / ZBid / review/apply。
- 不修改 source section。
- 不执行 formal writeback。
- 不执行 formal writeback dry-run。

## 4. Local Trial Topology Assumptions

以下仅描述本地试用阶段拓扑假设，不构成正式部署配置：

- 单机 Mac 本地试用。
- ZDoc backend 作为本地试用后端。
- ZDoc frontend 作为本地试用前端。
- Ollama 仅作为可用性检查对象，不自动触发写回，不作为正式部署容量设计依据。
- ZBid preview-only 对接仍为占位，不调用真实 ZBid API，不访问真实 ZBid 数据库，不触发真实 ZBid 写回。
- 本地项目资料目录需要在试用前明确。
- 日志目录仅作为观察占位，需要在试用前明确。
- `output/job/export` 必须保持隔离。
- 不启用 50 人并发。
- 不启用正式队列扩容。
- 不启用正式 ZBid 写回。
- 不启用正式 DOCX 导出。
- 不启用 formal writeback。
- 不设计 Mac Studio / NAS / UPS / Redis / PostgreSQL 等正式部署配置。

## 5. Preflight Checklist Before Any Trial Run

以下为后续试用前的人工检查清单。本文档不执行命令。

Git 与版本状态：

- Git branch 应为 `main`。
- 工作区应为 clean。
- 试用基准 tag 应已存在。
- 当前 commit 与试用记录应一致。
- 本地未混入未提交代码、测试、docs、配置或 runtime artifact。

环境与配置状态：

- `.env` / local config 是否准备完毕。
- Python 环境是否可重建。
- Node / pnpm 环境是否可重建。
- Ollama 是否仅作为可选服务检查。
- 项目资料目录是否明确。
- 日志目录是否明确。
- `output/job/export` 是否保持隔离。

安全开关状态：

- no-write flag 是否默认开启。
- preview-only flag 是否默认开启。
- ZBid writeback flag 是否默认关闭。
- DOCX export flag 是否默认关闭。
- review/apply flag 是否默认关闭。
- formal writeback flag 是否默认关闭。
- formal writeback dry-run execution 是否默认关闭。

阻断项预检：

- evidence anchor 缺失时是否 blocked。
- source hash mismatch 是否 blocked 或 `stale_source_hash`。
- source version mismatch 是否 blocked 或 `stale_source_version`。
- ZBid writeback request 是否默认 blocked。
- DOCX export request 是否默认 blocked。
- review/apply request 是否默认 blocked。
- `output/job/export` write request 是否默认 blocked。

## 6. ZDoc Preview-Only Trial Checklist

ZDoc 本地试用检查项：

- 文档输入是否可读。
- source document / source section 标识是否可追踪。
- 章节 preview 是否可生成。
- preview advisory 是否不写回。
- preview advisory 是否不得作为 evidence。
- `thinking_only_fallback` 是否不作为正文能力。
- response mode 是否可审计。
- input risk 是否可审计。
- quality gate 结果是否可审计。
- evidence anchor 缺失是否 blocked。
- generated advisory 是否不得作为 evidence。
- shadow candidate 是否不进入正式正文。
- shadow candidate envelope 是否仅 metadata。
- shadow candidate patch 是否仅 preview metadata。
- patch / diff / rollback 是否仅 metadata。
- diff preview 是否不得替代 rollback plan。
- rollback plan 是否不得替代 formal writeback guard。
- human approval 是否不得替代 evidence。
- source hash matched 是否不得开放正式写回。
- formal flags 是否保持 false。

ZDoc 试用通过不代表正式正文生成链、正式写回、DOCX 导出或 review/apply 已实现。

## 7. ZBid Preview-Only Integration Checklist

ZBid 对接检查项：

- ZBid 输入仅使用 preview-only / metadata-only。
- 不调用 ZBid API。
- 不访问 ZBid 数据库。
- 不调用 ZBid 写回接口。
- 不触发 ZBid 写回。
- ZBid mapping 仅作为 future placeholder。
- `zbid_writeback_allowed` 必须 false。
- ZBid guard blocked reasons 应可读。
- ZBid preview 结果不得反向写入 ZDoc 正文。
- ZBid isolation 不得作为 evidence。
- ZBid isolation 不得替代 evidence anchor。
- ZBid isolation 不得替代 human approval。
- ZBid isolation 不得替代 diff preview。
- ZBid isolation 不得替代 rollback plan。
- ZBid isolation 不得替代 formal writeback guard。
- ZBid scoring / matrix 仅作为后续 contract 设计输入。

ZBid preview-only 对接通过不代表 ZBid 正式写回能力已开放。

## 8. DOCX / Review-Apply / Writeback Block Checklist

DOCX 阻断检查：

- `/export_docx` 请求默认 blocked。
- DOCX 文件不得生成。
- DOCX isolation 不得作为 evidence。
- DOCX isolation 不得替代 source hash revalidation。
- `docx_export_allowed` 必须 false。

review/apply 阻断检查：

- `/review/apply` 请求默认 blocked。
- review/apply isolation 不得作为 evidence。
- review/apply isolation 不得替代 human approval。
- `review_apply_allowed` 必须 false。

formal writeback 阻断检查：

- formal writeback 默认 blocked。
- formal writeback guard 不得替代 source hash revalidation。
- formal writeback guard 不得替代 rollback plan。
- `formal_writeback_allowed` 必须 false。

dry-run 阻断检查：

- dry-run passed 不得开放正式写回。
- `passed_shadow_only` 不得开放正式写回。
- `pass_shadow_only` 不得开放正式写回。
- formal writeback dry-run 不得替代 evidence anchor、human approval、diff preview、rollback plan、formal writeback guard、source hash revalidation、review/apply isolation、DOCX isolation、ZBid isolation。

cross-chain 阻断检查：

- source hash matched 不得开放正式写回。
- human approval 不得替代 evidence。
- diff preview 不得替代 rollback。
- rollback plan 不得替代 formal guard。
- preview-only metadata 不得触发 `output/job/export` 写入。

## 9. Audit and Log Checklist

后续试用时应观察以下审计字段。本文档不实现日志、不写文件、不定义持久化格式：

- `request_id`
- `source_document_id`
- `source_section_id`
- `source_section_hash`
- `source_section_version`
- `current_source_section_hash`
- `current_source_section_version`
- `response_mode`
- `input_risk_level`
- `advisory_quality_gate_status`
- `evidence_anchor_status`
- `evidence_anchor_refs`
- `shadow_candidate_id`
- `patch_id`
- `approval_id`
- `diff_preview_id`
- `rollback_plan_id`
- `writeback_guard_id`
- `source_hash_guard_id`
- `review_apply_guard_id`
- `docx_isolation_guard_id`
- `zbid_isolation_guard_id`
- `dry_run_id`
- `blocked_reasons`
- `formal_writeback_allowed`
- `review_apply_allowed`
- `docx_export_allowed`
- `zbid_writeback_allowed`
- `output_write_allowed`

审计目标是让 preview-only 试用中的每一次阻断、fallback、stale source、missing evidence、missing approval、DOCX request、ZBid request、review/apply request 都可追踪。

## 10. Failure Handling Checklist

试用失败时应按以下规则处理：

- 服务未启动：停止并记录，不继续联调。
- 前端不可访问：停止并记录，不推断后端已正常。
- 后端健康检查不可读：停止并记录。
- Ollama 不可用：进入 fallback，不写回。
- `thinking_only_fallback` 出现：不得作为正文能力。
- evidence 缺失：blocked。
- generated advisory 被用作 evidence：blocked。
- ZBid 写回请求出现：blocked。
- DOCX 导出请求出现：blocked。
- review/apply 请求出现：blocked。
- formal writeback 请求出现：blocked。
- formal writeback dry-run execution 请求出现：blocked。
- `output/job/export` 有写入：立即停止并登记。
- source hash mismatch：`stale_source_hash` 或 blocked。
- version mismatch：`stale_source_version` 或 blocked。
- human approval 缺失：blocked。
- diff preview 缺失：blocked。
- rollback plan 缺失：blocked。
- formal writeback guard 缺失：blocked。
- review/apply isolation 缺失：blocked。
- DOCX isolation 缺失：blocked。
- ZBid isolation 缺失：blocked。
- full backend tests 既有 collection/order 问题不得在本地试用中擅自修改生产代码修复。

任何失败处理都不得自动扩大到正式写回、DOCX 导出、ZBid 写回、50 人部署设计或正式部署配置。

## 11. Trial Acceptance Criteria

小范围试用前，设计层面的验收标准为：

- 所有关键链路有 checklist。
- 所有正式写回路径有 blocked 项。
- 所有 DOCX / ZBid / review/apply 路径有 blocked 项。
- 所有 evidence / approval / diff / rollback / guard 关系有边界。
- no-write 规则明确。
- preview-only 规则明确。
- fake-only helper 不被视为正式能力。
- dry-run passed 不被视为正式写回许可。
- ZBid preview-only 不被视为 ZBid 写回许可。
- DOCX isolation 不被视为 DOCX 导出许可。
- review/apply isolation 不被视为 review/apply 许可。
- 试用失败处理明确。
- 不进入 50 人正式部署。
- 不进行 Mac Studio / NAS / UPS / Redis / PostgreSQL 等正式部署配置设计。

达到上述条件仅代表可以准备下一阶段的 preview-only integration contract design，不代表可以启动真实联调或开放写回。

## 12. Exit Criteria to Next Step

建议下一步为：

ZDoc Step 142：ZDoc/ZBid preview-only integration contract design，docs-only。

Step 142 不得实现接口，不得调用 ZBid，不得启动服务，不得进入正式写回，不得触发 DOCX / ZBid / review/apply，不得写 `output/job/export`，不得进入 50 人正式部署设计。

进入 Step 142 前应确认：

- 本文档已完成审核。
- 当前 repo 工作区 clean。
- Step 141 tag 已存在并指向对应 commit。
- preview-only / no-write 边界仍被保留。
- 下一步仍为 docs-only contract design。

## 13. Safety Conclusion

Step 141 仅完成 local trial integration checklist design，不代表本地部署已完成，不代表 ZDoc / ZBid 已联调，不代表正式写回、DOCX 导出、ZBid 写回或 50 人团队部署已实现。

本地试用阶段必须先以 preview-only / no-write 模式进行。当前系统的 fake-only metadata、contract、tests、docs 和 helper 均不得被解释为正式写回、正式 DOCX 导出、正式 review/apply 或正式 ZBid 写回能力。
