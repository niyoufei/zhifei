# ZDoc-ZBid preview-only false flags explanation

## 1. 使用范围

本文档解释 ZDoc-ZBid preview-only / no-write / no-evidence 链路中的五个 no-write / no-formal-chain false flags。

这些 flags 仅用于 preview-only / no-write 边界确认，不得作为正式 evidence、评分依据或正式业务结论。

## 2. generate_called=false

含义：本次没有调用正式生成链。

应确认：

- 未触发 `/generate`。
- 未生成正式正文。
- 未将 preview-only advisory 当作正式内容。

风险：如果该 flag 非 false，说明可能进入或尝试进入正式生成链，必须立即停止并上报。

## 3. export_docx_called=false

含义：本次没有调用 DOCX 导出链。

应确认：

- 未触发 `/export_docx`。
- 未生成 DOCX。
- 未把 preview-only 结果导出为正式文档。

风险：如果该 flag 非 false，说明可能进入或尝试进入 DOCX 导出链，必须立即停止并上报。

## 4. review_apply_called=false

含义：本次没有调用 review/apply 链。

应确认：

- 未触发 `/review/apply`。
- 未将 preview-only 结果应用为正式正文。
- 未修改正式成果内容。

风险：如果该 flag 非 false，说明可能进入或尝试进入 review/apply 链，必须立即停止并上报。

## 5. zbid_writeback_called=false

含义：本次没有触发 ZBid 写回。

应确认：

- 未写回 ZBid 正式业务数据。
- 未写入 ZBid evidence、评分依据、结果或 storage。
- ZBid receiver 仅作为 preview-only / no-write / no-evidence 接收方。

风险：如果该 flag 非 false，说明可能进入或尝试进入 ZBid 写回链，必须立即停止并上报。

## 6. output_job_export_written=false

含义：本次没有写入 `output/job/export`。

应确认：

- ZDoc 侧 `output/job/export` 无新增。
- ZBid 侧 `output/job/export` 无新增。
- 未生成 runtime artifact、DOCX、正式导出结果或 job/export 文件。

风险：如果该 flag 非 false，说明可能出现输出写入或导出写入，必须立即停止并上报。

## 7. 任一 flag 非 false 时的处理

任一 flag 非 false 时，必须立即停止：

- 不得继续试用。
- 不得现场修复。
- 不得切换到正式接口。
- 不得删除或隐藏已产生的文件。
- 必须记录 flag 名称、当前操作、时间、操作者角色和可读错误信息。
- 修复必须另行授权。

## 8. 统一禁止

这些 flags 的解释不授权任何正式链动作。

仍必须禁止：

- `/generate`
- `/export_docx`
- `/review/apply`
- ZBid 写回
- DOCX 生成
- `output/job/export` 写入
- 把 preview-only 结果作为 evidence
- 把 preview-only 结果作为评分依据
- 写入正式业务数据

## 9. 建议记录格式

```text
检查时间：
检查角色：
generate_called：
export_docx_called：
review_apply_called：
zbid_writeback_called：
output_job_export_written：
是否全部为 false：
是否触发停止条件：
备注：
```
