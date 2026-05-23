# ZDoc-ZBid preview-only observation optimization authorization request

## 1. 授权请求来源

本授权请求基于以下阶段结果起草：

- Step 227 已完成小范围受控试用。
- Step 228 已完成小范围受控试用 stage review。
- Step 229 已完成问题清单与修正边界设计。
- Step 230 已完成小范围试用阶段总归档。

本轮未发现阻断 preview-only 链路的问题。

本轮未发现以下安全边界问题：

- 正式链误触发
- 写回
- DOCX 生成
- evidence 写入
- 评分依据写入

本文档只代表申请授权，不代表已授权优化或已开始修复。

## 2. 拟申请优化的观察项范围

后续拟申请优化的范围仅限观察项优化，不得描述为缺陷修复。

拟申请观察项包括：

- 错误提示清晰度优化。
- `blocked_reasons` 可读性优化。
- preview-only 状态醒目性优化。
- 五个 false flags 可理解性优化。
- 日志留痕结构优化。
- 人工复核检查表固化。

## 3. 后续拟申请的代码或文档优化边界

- 可优先进行 docs-only 或 UI 文案层优化。
- 如涉及前端展示优化，必须单独限定允许文件范围。
- 如涉及日志结构优化，必须单独限定允许文件范围。
- 如涉及 backend adapter 或 receiver 行为变化，必须另行授权。
- 不得混入正式生成、导出、review apply、ZBid 写回等正式链。

任何优化均不得默认启动服务、访问端口或调用 endpoint。

任何优化效果验证如需 runtime、端口或 endpoint 调用，必须另行申请 controlled smoke 或 trial recheck 授权。

## 4. 必须保持的 preview-only 边界

后续优化必须保持以下边界：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 5. 严格禁止

- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得触发 `/review/apply`。
- 不得触发 ZBid 写回。
- 不得生成 DOCX。
- 不得写 `output/job/export`。
- 不得将 preview-only 结果作为 evidence。
- 不得将 preview-only 结果作为评分依据。
- 不得写入正式业务数据。
- 不得进入扩大试用。
- 不得进入 50 人正式部署设计。

## 6. 授权后拟进入的下一步

- Step 232 可作为 preview-only observation optimization code/docs implementation。
- Step 232 必须由用户明确授权。
- Step 232 应优先限定为最小优化，不得启动服务、访问端口或调用 endpoint。
- 如需验证优化效果，应另行申请 controlled smoke 或 trial recheck。

## 7. Step 232 用户授权语建议

以下授权语仅供用户后续复制并补全。本文档本身不代表用户已授权。

> 我授权执行 Step 232：preview-only observation optimization code/docs implementation。授权范围仅限观察项优化，保持 preview-only / no-write / no-evidence。
>
> ZDoc 仓库路径：`/Users/youfeini/Desktop/文档生成系统`；ZDoc 分支：`main`；ZDoc 开始前 HEAD：`<由用户在 Step 232 授权时填写>`。
>
> 允许修改文件范围：`<由用户填写；可优先限定为目标 docs 文件、前端文案文件或日志结构相关文件>`。
>
> 优化范围仅限：错误提示清晰度、`blocked_reasons` 可读性、preview-only 状态醒目性、五个 false flags 可理解性、日志留痕结构、人工复核检查表。
>
> 必须保持 `preview_only=true`、`no_write=true`、`no_evidence=true`、`generate_called=false`、`export_docx_called=false`、`review_apply_called=false`、`zbid_writeback_called=false`、`output_job_export_written=false`。
>
> 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid 写回；不得生成 DOCX；不得写 `output/job/export`；不得将 preview-only 结果作为 evidence 或评分依据；不得写入正式业务数据；不得进入扩大试用；不得进入 50 人正式部署设计。不得启动服务、访问端口或调用 endpoint，除非另有单独授权。
