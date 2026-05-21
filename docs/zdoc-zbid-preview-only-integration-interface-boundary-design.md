# ZDoc-ZBid Preview-Only Integration Interface Boundary Design

## 1. Scope

本文档对应 Step 200：ZDoc-ZBid preview-only integration interface boundary design。

本步仅在已完成 `/local-trial/preview-only` 前端同源 proxy 闭环的基础上，设计 ZDoc 与 ZBid preview-only 对接前的接口边界。

本步性质为 docs-only / design-only / no-code-change / no-service / no-port-access / no-writeback：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入 50 人正式部署设计。

本文档不代表已授权跨系统代码修改、服务启动、端口访问、接口调用、ZBid 侧接收验证或任何写回行为。

## 2. Current ZDoc Preview-Only Capability Baseline

当前 ZDoc 已具备以下 preview-only 能力：

1. 后端 `/local-trial/preview-only` route 已实现，并已通过 runtime smoke。
2. 前端同源 `/local-trial/preview-only` proxy 已实现，并已通过 controlled smoke。
3. 前端 `fetch("/local-trial/preview-only")` 已可通过前端端口同源 proxy 动态加载后端 preview-only 数据。
4. 前端已能动态展示：
   - `preview_packet`
   - `validator_result`
   - `blocked_reasons`
   - `generate_called=false`
   - `export_docx_called=false`
   - `review_apply_called=false`
   - `zbid_writeback_called=false`
   - `output_job_export_written=false`
5. Step 198 已验证：
   - `POST 127.0.0.1:18760/local-trial/preview-only` 返回 HTTP `200`。
   - `POST 127.0.0.1:18761/local-trial/preview-only` 返回 HTTP `200`。
   - Step 193 的前端同源 HTTP `404` 已修复为 HTTP `200`。
   - `output/job/export` 前后无新增写入。

当前能力仍限定为 local trial / preview-only / no-write / no-formal-chain，不代表正式生成、DOCX 导出、review/apply、ZBid 写回或真实 ZDoc/ZBid 联调已开放。

## 3. ZDoc Preview-Only Data Available for ZBid

ZDoc 可在 preview-only 边界内向 ZBid 提供的数据范围应限定为只读 metadata / preview payload。

### 3.1 Existing Available Payload Groups

当前已有结构中可提供：

- `preview_packet`
- `validator_result`
- `blocked_reasons`
- no-write / no-formal-chain flags
- route metadata:
  - `preview_only=true`
  - `no_write=true`
  - `metadata_only=true`
  - `route_name`
  - `endpoint_path`

当前已有 `preview_packet` 中可追踪字段包括：

- `contract_version`
- `integration_request_id`
- `source_system`
- `target_system`
- `project_id`
- `document_id`
- `section_id`
- `section_title`
- `section_hash`
- `section_version`
- `generated_at`

其中：

- `integration_request_id` 可作为当前 preview-only 对接的请求追踪 ID。
- `source_system` / `target_system` 可表达来源与目标系统。
- `generated_at` 可作为当前 payload 生成时间字段。

本文档不将独立 `request_id`、额外 `timestamp` 或额外审计 ID 臆造为已实现字段；如后续需要，可在授权后的实现设计中作为新增建议处理。

### 3.2 Existing Preview Reference Fields

当前已有结构中可提供以下只读引用字段：

- `tender_file_refs`
- `scoring_clause_refs`
- `evidence_anchor_refs`
- `evidence_anchor_status`
- `evidence_binding_status`

这些字段仅用于 preview-only 展示和人工核查，不等于正式 evidence 写入，也不得作为自动写回依据。

### 3.3 Existing ZBid Preview Status Fields

当前已有结构中可提供以下 ZBid preview 状态字段：

- `zbid_preview_mode`
- `zbid_input_status`
- `zbid_mapping_status`
- `zbid_scoring_matrix_status`
- `zbid_writeback_requested`
- `zbid_writeback_allowed`

其中 `zbid_writeback_allowed` 在当前阶段必须保持 `false`。

### 3.4 Current Formal Chain False Flags

当前对接边界内，以下正式链 flags 必须恒为 `false`：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

面向前端展示时，对应的用户可读 false flags 为：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 4. ZBid Preview-Only Receiver Boundary

ZBid 侧在本阶段只允许作为 preview-only 接收方或展示方。

ZBid 侧允许的行为仅限：

- 接收 ZDoc preview-only packet。
- 展示 `preview_packet`。
- 展示 `validator_result`。
- 展示 `blocked_reasons`。
- 展示 no-write / no-formal-chain flags。
- 展示 scoring refs / tender refs / evidence anchor refs 的只读状态。
- 将 blocked / requires_human_review 状态呈现给人工审核。

ZBid 侧不得执行：

- 写回 ZDoc。
- 写回 ZBid 正式业务数据。
- 触发 ZBid 正式评分写入。
- 触发 ZBid 正式审批、流转或归档。
- 将 advisory / preview / shadow / patch / diff / rollback / dry-run 作为 evidence。
- 将 `accepted_preview_only` 解释为 writeback permission。
- 将 `zbid_preview_scoring` 解释为 evidence。

ZBid 侧如发现字段缺失、source hash/version 不一致、evidence anchor 缺失、scoring refs 缺失或 blocked reason 不可读，应进入 blocked 或 requires_human_review 展示状态，不得尝试写回。

## 5. Prohibited Formal Chains

ZDoc 与 ZBid preview-only 对接中，以下链路必须保持禁止：

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得调用 ZBid API / DB / writeback。
- 不得生成 DOCX。
- 不得生成正式 JSON / Markdown / job / export 产物。
- 不得写 `output/job/export`。
- 不得进入正式正文生成链。
- 不得生成真实 candidate patch。
- 不得执行 formal writeback。
- 不得执行 formal writeback dry-run。

任何 preview-only smoke 或后续联通验证均不得把上述链路作为 fallback。

## 6. Data Flow Design

建议的 preview-only 数据流为：

```text
ZDoc /local-trial/preview-only
  -> preview_packet
  -> validator_result
  -> blocked_reasons
  -> no-write / no-formal-chain flags
  -> ZBid preview-only receiver/display
```

数据流边界：

1. ZDoc 只输出 preview-only metadata。
2. ZBid 只接收和展示 preview-only metadata。
3. ZBid 不向 ZDoc 写回。
4. ZBid 不写入正式业务数据。
5. 任一正式链 flag 为 `true` 时必须 stop。
6. 任一写回请求未 blocked 时必须 stop。
7. `blocked_reasons` 缺失或不可读时必须 stop 或进入 requires_human_review。

## 7. Minimum Interface Field Checklist

未来 ZDoc-ZBid preview-only 对接的最小字段清单建议如下。

### 7.1 Envelope Fields

- `preview_only`
- `no_write`
- `metadata_only`
- `route_name`
- `endpoint_path`
- `preview_packet`
- `validator_result`
- `blocked_reasons`

### 7.2 Trace Fields

已有字段：

- `contract_version`
- `integration_request_id`
- `source_system`
- `target_system`
- `project_id`
- `document_id`
- `section_id`
- `section_title`
- `section_hash`
- `section_version`
- `generated_at`

后续建议字段，当前不得声明为已实现：

- 独立 `request_id`
- 独立 `correlation_id`
- 独立 `receiver_trace_id`
- 独立 `audit_event_id`

### 7.3 Reference Fields

- `tender_file_refs`
- `scoring_clause_refs`
- `evidence_anchor_refs`
- `evidence_anchor_status`
- `evidence_binding_status`

### 7.4 Preview and Advisory Fields

- `response_mode`
- `input_risk_level`
- `advisory_quality_gate_status`
- `preview_advisory_summary`
- `shadow_candidate_id`
- `patch_id`
- `diff_preview_id`
- `rollback_plan_id`
- `dry_run_id`

上述字段只能作为 preview-only / advisory / trace 信息，不得作为 evidence，不得作为正式正文，不得作为写回依据。

### 7.5 ZBid Preview Fields

- `zbid_preview_mode`
- `zbid_input_status`
- `zbid_mapping_status`
- `zbid_scoring_matrix_status`
- `zbid_writeback_requested`
- `zbid_writeback_allowed`

### 7.6 Required False Flags

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

## 8. Error Handling Boundary

未来 preview-only 对接错误处理必须遵守 no-write 原则。

### 8.1 ZDoc-Side Error Handling

ZDoc 侧如发生以下情况：

- preview packet 字段缺失。
- `integration_request_id` 缺失。
- `section_hash` 缺失。
- `section_version` 缺失。
- scoring refs 缺失。
- evidence anchor 缺失。
- source hash / version mismatch。
- advisory 被标记为 evidence。
- preview 被标记为正式正文。

应返回 blocked 或 requires_human_review 语义，并填充 `blocked_reasons`，不得触发正式链。

### 8.2 ZBid-Side Error Handling

ZBid preview-only receiver/display 如发生以下情况：

- payload 不可解析。
- required fields 缺失。
- `blocked_reasons` 不可读。
- formal flag 非 `false`。
- writeback requested 但未 blocked。
- evidence boundary 不清晰。

应只展示错误、blocked 或 requires_human_review 状态，不得写回 ZDoc 或 ZBid 正式业务数据。

### 8.3 Transport Error Handling

如果 ZDoc route、前端 proxy 或 ZBid preview-only receiver 不可达：

- 只能返回或展示 preview-only / no-write 错误。
- 不得 fallback 到 `/generate`。
- 不得 fallback 到 `/export_docx`。
- 不得 fallback 到 `/review/apply`。
- 不得 fallback 到 ZBid 写回接口。
- 不得写 `output/job/export`。

## 9. Audit Field Recommendations

当前已存在的审计与追踪字段包括：

- `contract_version`
- `integration_request_id`
- `source_system`
- `target_system`
- `project_id`
- `document_id`
- `section_id`
- `section_hash`
- `section_version`
- `generated_at`

后续如进入代码设计或实现授权，可考虑新增但本步不实现：

- 独立 receiver trace ID。
- 独立 cross-system correlation ID。
- 独立 smoke run ID。
- 独立 operator / reviewer marker。
- 独立 ZBid display-only acknowledgement ID。

上述建议字段必须在后续授权步骤中单独设计和测试；本文档不代表这些字段已经存在。

## 10. User Authorization Points

后续任何跨系统动作必须逐项获得用户明确授权。

至少需要单独授权的事项：

- 修改 ZDoc 代码。
- 修改 ZBid 代码。
- 修改前端接入逻辑。
- 新增或修改 ZBid preview-only receiver/display。
- 启动 ZDoc 后端服务。
- 启动 ZDoc 前端服务。
- 启动 ZBid 侧服务。
- 访问本地端口。
- 调用 `/local-trial/preview-only`。
- 调用 ZBid preview-only receiver/display。
- 执行跨系统 preview-only smoke。
- 检查 `output/job/export` 前后差异。
- 生成 smoke report。

授权必须列明：

- 允许启动哪些服务。
- 允许访问哪些端口。
- 允许调用哪些接口。
- 允许检查哪些目录。
- 明确不得触发哪些正式链。
- 停止条件。
- 回报模板。

未获得明确授权，不得执行。

## 11. Smoke Verification Points

未来 ZDoc-ZBid preview-only 对接 smoke 应至少验证：

1. ZDoc 后端 `/local-trial/preview-only` 返回 HTTP `200`。
2. ZDoc 前端同源 `/local-trial/preview-only` proxy 返回 HTTP `200`。
3. ZBid preview-only receiver/display 可接收 preview-only payload。
4. `preview_packet` 可读。
5. `validator_result` 可读。
6. `blocked_reasons` 可读。
7. `formal_writeback_allowed=false`。
8. `review_apply_allowed=false`。
9. `docx_export_allowed=false`。
10. `zbid_writeback_allowed=false`。
11. `output_write_allowed=false`。
12. `calls_generate_route=false`。
13. `calls_export_docx_route=false`。
14. `calls_review_apply_route=false`。
15. `affects_zbid_writeback=false`。
16. `writes_output=false`。
17. `writes_job=false`。
18. `writes_export=false`。
19. `output/job/export` 前后无新增写入。
20. 未生成 DOCX。
21. 未调用 ZBid API / DB / writeback。
22. 服务进程可停止。

如任一正式链 flag 为 `true`、任一正式端点被触发、任一 output/job/export 写入出现或服务无法停止，应立即 stop 并回报 high risk。

## 12. Acceptance Criteria for Interface Boundary

接口边界设计的验收标准：

- 明确 ZDoc 当前 preview-only 能力。
- 明确 ZDoc 可向 ZBid 提供的数据范围。
- 明确 ZBid 只能作为 preview-only 接收方或展示方。
- 明确 no-write / no-formal-chain flags。
- 明确 `blocked_reasons` 必须可读。
- 明确 advisory 不得作为 evidence。
- 明确 preview 不得作为正式正文。
- 明确 shadow / patch / diff / rollback / dry-run 不得作为 evidence。
- 明确 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回均禁止。
- 明确 `output/job/export` 不得写入。
- 明确后续跨系统实现与 smoke 都必须单独授权。

## 13. Non-Goals

本文档不设计也不授权：

- 真实 ZDoc/ZBid 联调执行。
- ZBid 正式业务写回。
- ZDoc 正式正文生成。
- DOCX 导出。
- review/apply。
- formal writeback。
- formal writeback dry-run。
- candidate patch 写入。
- source section 修改。
- 本地化部署执行。
- Mac Studio / NAS / UPS / Redis / PostgreSQL / 50 人并发正式部署设计。

## 14. Recommended Next Step

建议下一步为：

`ZDoc Step 201：ZDoc-ZBid preview-only integration code implementation authorization request`

Step 201 建议性质：

- docs-only / authorization-request-only。
- 仅起草后续代码实现授权请求。
- 不得视为已授权代码修改。
- 不得启动服务。
- 不得访问端口。
- 不得调用接口。
- 不得触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- 不得写 `output/job/export`。
- 不得进入真实 ZDoc/ZBid 联调。
- 不得进入 50 人正式部署设计。

后续任何跨系统代码修改、服务启动、端口访问、接口调用、ZBid 侧接收验证，均需单独明确授权。

## 15. Safety Conclusion

当前系统已具备 ZDoc local trial preview-only route、前端同源 proxy 和前端动态展示闭环。

本设计仅定义 ZDoc 与 ZBid preview-only 对接前的接口边界：

- ZDoc 可提供 preview-only metadata。
- ZBid 只能作为 preview-only 接收方或展示方。
- 所有正式链 flags 必须保持 `false`。
- `blocked_reasons` 必须可读。
- advisory / preview / shadow / patch / diff / rollback / dry-run 均不得作为 evidence。
- preview-only 不等于 writeback permission。
- accepted_preview_only 不等于 ZBid 写回许可。
- 不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。

本文档不代表真实 ZDoc/ZBid 联调已执行，不代表正式生成链开放，不代表 DOCX 导出开放，不代表 review/apply 开放，不代表 ZBid 写回开放，也不代表 50 人正式部署设计已启动。
