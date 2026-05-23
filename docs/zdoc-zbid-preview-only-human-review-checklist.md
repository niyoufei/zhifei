# ZDoc-ZBid preview-only human review checklist

## 1. 复核目标

本检查表用于 ZDoc-ZBid preview-only / no-write / no-evidence 小范围试用后的人工复核。

复核目标是确认本次结果仅用于 preview-only 观察和人工判断，不进入正式生成、正式 evidence、正式评分依据、DOCX 导出、review/apply 或 ZBid 写回。

## 2. 复核前检查项

复核前先确认：

- 本次数据为脱敏样例、测试文档或非正式投标成果。
- 本次入口为 preview-only 入口。
- 本次未请求正式生成。
- 本次未请求 DOCX 导出。
- 本次未请求 review/apply。
- 本次未请求 ZBid 写回。
- 本次不写 `output/job/export`。
- 本次结果不得作为 evidence 或评分依据。

如任一项不满足，立即停止复核并上报。

## 3. preview_only / no_write / no_evidence 三项确认

必须逐项确认：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

含义：

- `preview_only=true`：当前仅为预览，不代表正式正文或正式投标成果。
- `no_write=true`：当前不得写入正式业务数据、ZBid、ZDoc 或 `output/job/export`。
- `no_evidence=true`：当前不得把 advisory、preview、shadow、patch、diff、rollback、dry-run 作为 evidence。

任一项不是 true，立即停止并上报。

## 4. preview_packet 检查项

检查 `preview_packet` 时，只确认其是否可读、字段是否与本次脱敏试用相关。

建议检查：

- 是否存在 `preview_packet`。
- 是否能识别来源为 ZDoc、目标为 ZBid 的 preview-only 数据。
- 是否仅包含脱敏样例、测试文档或非正式投标成果信息。
- 是否不存在 DOCX、正式 evidence、正式评分结果或 writeback 数据。
- 是否存在人工复核提示或等效 no-evidence 提示。

不得把 `preview_packet` 当作正式正文、正式 evidence 或评分依据。

## 5. validator_result 检查项

检查 `validator_result` 时，只确认校验结果是否可读、是否仍保持 preview-only 边界。

建议检查：

- 是否存在 `validator_result`。
- 是否能看到输入校验状态。
- 是否没有允许正式生成、正式导出、review/apply 或 ZBid 写回。
- 是否没有把 advisory 或 preview 标记为 evidence。
- 是否存在需要人工复核的提示或 blocked reason。

不得把 `validator_result` 当作正式评分结论。

## 6. blocked_reasons 检查项

检查 `blocked_reasons` 时，只确认阻断原因是否可读、是否说明了 preview-only 边界。

常见项包括：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`
- `small_scale_trial_requires_human_review`

如出现未知 blocked reason，应记录原文并上报，不得现场切换到正式链。

## 7. 五个 false flags 检查项

必须逐项确认：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

任一 flag 非 false，立即停止并上报。

这些 flags 仅用于确认 preview-only / no-write 边界，不得作为正式 evidence 或评分依据。

## 8. 禁止项复核

人工复核时必须确认以下事项未发生：

- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未将 preview-only 结果作为 evidence。
- 未将 preview-only 结果作为评分依据。
- 未写入正式业务数据。

## 9. 异常时停止条件

出现以下情况立即停止：

- `preview_only` 不是 true。
- `no_write` 不是 true。
- `no_evidence` 不是 true。
- 任一 false flag 非 false。
- 出现 DOCX 生成。
- 出现 `output/job/export` 写入。
- 出现 ZBid 写回。
- 出现 evidence 写入。
- 出现评分依据写入。
- 出现 fallback 到正式接口。
- 出现未知 endpoint 调用。

停止后只记录事实，不得现场修复，不得扩大试用。

## 10. 复核记录建议格式

建议按以下格式记录：

```text
复核时间：
复核角色：
试用数据范围：
preview_only：
no_write：
no_evidence：
preview_packet 是否可读：
validator_result 是否可读：
blocked_reasons 是否可读：
blocked_reasons 摘要：
generate_called：
export_docx_called：
review_apply_called：
zbid_writeback_called：
output_job_export_written：
是否触发禁止项：
是否需要停止：
是否需要另行申请修复授权：
备注：
```
