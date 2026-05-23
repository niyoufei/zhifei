# ZDoc-ZBid preview-only small-scale trial deliverable package consolidation

## 1. 当前阶段完成情况

当前 ZDoc-ZBid preview-only 对接阶段、小范围受控试用阶段、观察项优化阶段已形成可交接的 docs 交付包。

当前完成情况：

- preview-only 对接闭环已完成。
- small-scale trial 已完成。
- observation docs-only 优化已完成。
- 未进入扩大试用。
- 未进入正式生成链。
- 未进入 50 人正式部署设计。

本文档仅作为统一交付索引，不代表授权扩大试用、真实业务联调、正式生成链或 50 人正式部署设计。

## 2. 交付包建议分组

交付包建议按以下 5 组归档和阅读：

- A. preview-only 对接基础文档
- B. cross-system smoke 与 stage review 文档
- C. small-scale trial 文档
- D. observation / checklist / guidance 文档
- E. 后续待授权事项文档

## 3. A. preview-only 对接基础文档

### `zdoc-zbid-preview-only-integration-stage-final-consolidation.md`

用途摘要：归档 ZDoc-ZBid preview-only / no-write / no-evidence 对接阶段总成果，说明 ZDoc route、前端同源 proxy、动态展示、outbound adapter、ZBid receiver/helper、receiver API、cross-system controlled smoke 等闭环状态。

建议用途：

- 作为阶段总览入口。
- 用于确认当前只完成 preview-only 对接闭环。
- 用于明确尚未开放正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回。

## 4. B. cross-system smoke 与 stage review 文档

### `zdoc-zbid-preview-only-small-scale-trial-controlled-execution-report.md`

用途摘要：记录 Step 227 小范围受控试用执行结果，包括 3 个小范围角色 preview-only payload、ZDoc outbound adapter 发送、ZBid receiver HTTP 200、三项 preview-only/no-write/no-evidence 和五个 false flags 验证结果。

### `zdoc-zbid-preview-only-small-scale-trial-controlled-execution-stage-review.md`

用途摘要：归档 Step 227 执行结果的 stage review，确认 ZBid receiver 服务已停止、端口无监听、两侧 output/job/export 前后快照均为空、未生成 DOCX、未触发正式链。

### `zdoc-zbid-preview-only-small-scale-trial-stage-final-consolidation.md`

用途摘要：归档小范围受控试用阶段总成果，形成阶段闭环说明，明确未进入扩大试用、真实业务联调或 50 人正式部署设计。

## 5. C. small-scale trial 文档

### `zdoc-zbid-preview-only-small-scale-trial-boundary-design.md`

用途摘要：定义小范围试用前置边界，包括试用对象、试用数据、允许验证内容、严格禁止内容、授权点、日志留痕、失败回退与停止条件。

### `zdoc-zbid-preview-only-small-scale-trial-authorization-request.md`

用途摘要：起草小范围试用授权请求，说明试用对象建议为内部 2～5 人、数据限定为脱敏样例/测试文档/非正式投标成果、试用仅限 preview-only 入口。

### `zdoc-zbid-preview-only-small-scale-trial-issue-correction-boundary-design.md`

用途摘要：归纳 Step 227 小范围试用后的问题状态、观察项、修正边界和后续授权要求；明确本轮未发现阻断 preview-only 链路的问题，未发现正式链误触发、写回、DOCX、evidence、评分依据写入。

## 6. D. observation / checklist / guidance 文档

### `zdoc-zbid-preview-only-human-review-checklist.md`

用途摘要：提供 preview-only 人工复核检查表，覆盖复核目标、复核前检查项、三项状态确认、`preview_packet`、`validator_result`、`blocked_reasons`、五个 false flags、禁止项、停止条件和复核记录格式。

### `zdoc-zbid-preview-only-error-message-guidance.md`

用途摘要：解释 preview-only 场景下 disabled、not configured、configured_not_sent、blocked、validation error、receiver unreachable 等常见错误提示及人工处理建议。

### `zdoc-zbid-preview-only-blocked-reasons-reading-guide.md`

用途摘要：说明 `blocked_reasons` 的用途、常见类型、配置问题/输入问题/边界问题/正式链风险的判断方式，以及何时停止、上报或申请单独修复授权。

### `zdoc-zbid-preview-only-false-flags-explanation.md`

用途摘要：解释五个 no-write / no-formal-chain false flags：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

并说明任一 flag 非 false 时必须立即停止。

### `zdoc-zbid-preview-only-observation-optimization-implementation-stage-review.md`

用途摘要：归档 Step 232 docs-only 观察项优化实施结果，说明 4 份 observation / checklist / guidance 文档已新增，并确认未修改代码、tests、frontend 或既有 docs。

## 7. E. 后续待授权事项文档

### `zdoc-zbid-preview-only-observation-optimization-authorization-request.md`

用途摘要：起草观察项优化授权请求，限定后续优化范围为错误提示清晰度、`blocked_reasons` 可读性、preview-only 状态醒目性、五个 false flags 可理解性、日志留痕结构、人工复核检查表。

后续如需继续推进，应另行起草或取得明确授权：

- 单项优化授权请求。
- 扩大试用边界设计。
- controlled smoke 或 trial recheck 授权。
- 正式部署设计授权。

## 8. 推荐阅读顺序

建议按以下顺序阅读：

1. 先看阶段总归档：
   - `zdoc-zbid-preview-only-integration-stage-final-consolidation.md`
   - `zdoc-zbid-preview-only-small-scale-trial-stage-final-consolidation.md`
2. 再看 small-scale trial 边界与执行报告：
   - `zdoc-zbid-preview-only-small-scale-trial-boundary-design.md`
   - `zdoc-zbid-preview-only-small-scale-trial-authorization-request.md`
   - `zdoc-zbid-preview-only-small-scale-trial-controlled-execution-report.md`
3. 再看 stage review：
   - `zdoc-zbid-preview-only-small-scale-trial-controlled-execution-stage-review.md`
   - `zdoc-zbid-preview-only-observation-optimization-implementation-stage-review.md`
4. 再看 observation guidance 文档：
   - `zdoc-zbid-preview-only-human-review-checklist.md`
   - `zdoc-zbid-preview-only-error-message-guidance.md`
   - `zdoc-zbid-preview-only-blocked-reasons-reading-guide.md`
   - `zdoc-zbid-preview-only-false-flags-explanation.md`
5. 最后看待授权事项：
   - `zdoc-zbid-preview-only-observation-optimization-authorization-request.md`
   - 后续新起草的单项优化授权请求或扩大试用边界设计。

## 9. 明确未开放边界

当前仍未开放：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- DOCX 生成
- `output/job/export` 写入
- preview-only 结果作为 evidence
- preview-only 结果作为评分依据
- 扩大试用
- 50 人正式部署设计

任何绕过上述边界的操作都必须停止，并另行申请授权。

## 10. 后续建议

- Step 235 可做“待授权事项总表”。
- 或 Step 235 可做“扩大试用前置边界设计”。
- 任何代码优化、服务启动、端口访问、endpoint 调用、扩大试用、正式部署设计均需单独授权。
