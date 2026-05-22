# ZDoc-ZBid preview-only small-scale trial issue and correction boundary design

## 1. 试用结论

Step 227 已完成 3 个小范围角色 preview-only payload 试用。

本轮结论如下：

- ZDoc outbound adapter 成功发送 preview-only payload。
- ZBid receiver endpoint 返回 HTTP `200`。
- 返回 `preview_only=true`。
- 返回 `no_write=true`。
- 返回 `no_evidence=true`。
- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。
- 五个 false flags 均为 false：
  - `generate_called=false`
  - `export_docx_called=false`
  - `review_apply_called=false`
  - `zbid_writeback_called=false`
  - `output_job_export_written=false`
- ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均为空。
- 未生成 DOCX。
- 未触发正式链。

## 2. 问题状态分类

### 阻断问题

本轮未发现阻断 preview-only 链路的问题。

### 安全边界问题

本轮未发现正式链误触发、写回、DOCX、evidence、评分依据写入。

### 体验观察项

以下仅为后续观察项，不代表 Step 227 已发生缺陷：

- 错误提示是否足够清晰。
- `blocked_reasons` 是否便于人工复核。
- preview-only 状态是否足够醒目。
- 五个 false flags 是否便于试用人员理解。
- 日志留痕是否满足后续排查。
- 人工复核流程是否需要形成固定检查表。

### 工程化待完善项

以下仅作为后续授权建议，不代表当前已授权修复：

- 将人工复核流程整理为固定检查表。
- 将试用 report 字段规范化，便于多轮试用横向对比。
- 将错误提示分层为用户可读提示与工程排查提示。
- 将五个 false flags 的解释固化为试用人员可读说明。
- 将日志留痕范围进一步明确定义为不含敏感业务数据、不含正式 evidence、不含正式评分依据。

## 3. 可归纳的观察项

### 错误提示清晰度

Step 227 已记录错误提示可识别。本项后续可继续观察提示文案是否足够适合非研发试用人员理解。

### blocked_reasons 人工复核可读性

Step 227 返回的 `blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`
- `small_scale_trial_requires_human_review`

后续可观察这些原因是否需要补充面向业务角色的中文解释。

### preview-only 状态醒目程度

Step 227 验证了 preview-only / no-write / no-evidence 状态成立。后续如进入 UI 或试用入口优化，需观察 preview-only 状态是否足够醒目。

### 五个 false flags 理解成本

Step 227 验证了五个 false flags 均为 false。后续可观察试用人员是否理解这些 false flags 分别代表未进入生成、导出、review/apply、ZBid 写回、output/job/export 写入。

### 日志留痕排查能力

Step 227 已形成 trial report。后续可观察日志留痕是否足以支持失败定位，同时不得记录敏感业务数据、正式 evidence 或正式评分依据。

### 人工复核流程固定化

Step 227 已记录人工复核体验。后续可观察是否需要形成固定检查表，用于明确谁复核、复核什么、何时停止、何时另行授权。

## 4. 修正边界

后续任何修正均必须单独授权：

- 后续任何代码修正必须单独授权。
- 后续任何 UI 调整必须单独授权。
- 后续任何日志增强必须单独授权。
- 后续任何接口变更必须单独授权。
- 后续任何服务启动、端口访问、endpoint 调用必须单独授权。

本步不得修复问题。

本步不得扩大试用范围。

本步不得进入 50 人正式部署设计。

## 5. 严格禁止边界

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得将 preview-only 结果作为 evidence。
- 不得将 preview-only 结果作为评分依据。
- 不得写入正式业务数据。
- 不得进入 50 人正式部署设计。

## 6. 后续建议

- Step 230 可做小范围试用阶段总归档。
- 如需针对观察项进行优化，应先起草单独授权请求。
- 如需扩大试用范围，应先起草扩大试用边界设计。
- 50 人正式部署设计仍应在小范围试用、问题清单、必要修正和复验完成后再启动。
