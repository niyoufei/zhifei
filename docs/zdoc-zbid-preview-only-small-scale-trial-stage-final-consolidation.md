# ZDoc-ZBid preview-only small-scale trial stage final consolidation

## 1. 阶段定位

ZDoc-ZBid preview-only / no-write / no-evidence 对接闭环已完成。

小范围受控试用已完成。

本阶段仅验证以下内容：

- preview-only 链路
- 错误提示
- `blocked_reasons`
- 人工复核体验

本阶段未开放：

- 正式生成
- 正式 evidence
- 评分依据写入
- DOCX 导出
- review/apply
- ZBid 写回

本阶段未进入 50 人正式部署设计。

## 2. 当前 ZDoc 基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 当前 HEAD：`d111ca015d77a2517ca4bdb5f51fec313c4a8366`

ZDoc 当前已完成：

- preview-only route
- 前端同源 proxy
- 前端动态展示
- outbound adapter
- preview-only network-send
- cross-system smoke
- 小范围试用报告
- 试用问题与修正边界设计

## 3. 当前 ZBid 基线

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 小范围试用中 ZBid HEAD 保持：`378355755372e03ac4f4064af59b287054984c25`

ZBid 当前已完成：

- preview-only receiver/helper
- receiver API 暴露
- receiver API runtime smoke

小范围试用阶段 ZBid 未 commit、未 tag、未 push。

## 4. 小范围试用结果

Step 227 已完成 3 个小范围角色 payload 验证。

验证结果：

- ZDoc outbound adapter 成功发送 preview-only payload。
- ZBid receiver endpoint 返回 HTTP `200`。
- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` 可读
- `validator_result` 可读
- `blocked_reasons` 可读
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`
- 错误提示已记录。
- 人工复核体验已记录。
- ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均为空。
- 未生成 DOCX。
- 未触发正式链。

## 5. 问题与观察项结论

本轮未发现阻断 preview-only 链路的问题。

本轮未发现以下安全边界问题：

- 正式链误触发
- 写回
- DOCX 生成
- evidence 写入
- 评分依据写入

后续观察项包括：

- 错误提示清晰度
- `blocked_reasons` 可读性
- preview-only 状态醒目性
- 五个 false flags 可理解性
- 日志留痕完整性
- 人工复核检查表固化需求

上述观察项仅作为后续优化候选项，不代表已授权修复。

## 6. 严格未开放边界

- 未开放 `/generate`。
- 未开放 `/export_docx`。
- 未开放 `/review/apply`。
- 未开放 ZBid 写回。
- 未开放正式 evidence。
- 未开放评分依据写入。
- 未开放 DOCX 生成。
- 未开放 `output/job/export` 写入。
- 未进入真实业务联调。
- 未进入扩大试用。
- 未进入 50 人正式部署设计。

## 7. 后续工作建议

- 如需优化观察项，先起草单项优化授权请求。
- 如需扩大试用范围，先起草扩大试用边界设计。
- 如需进入正式部署设计，必须在小范围试用、问题清单、必要修正和复验完成后另行启动。
- 50 人正式部署设计不得在未完成问题修正和复验前提前进入。
