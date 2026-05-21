# ZDoc-ZBid preview-only integration stage final consolidation

## 1. 阶段定位

本阶段目标是完成 ZDoc 与 ZBid 的 preview-only / no-write / no-evidence 对接闭环。

当前已完成本地 controlled smoke 验证，验证范围仅限 preview-only payload 的跨仓发送、接收与只读结果回显。

当前未开放：

- 正式生成
- 正式证据链
- 正式评分链
- DOCX 导出
- review/apply
- ZBid 写回

当前未进入小范围试用，也未进入 50 人正式部署设计。

## 2. ZDoc 当前基线

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 当前 HEAD：`86cba65c42c38e0f2552a702e62f35b951ad4763`
- 已完成 `/local-trial/preview-only` 后端 route
- 已完成前端同源 proxy
- 已完成前端动态展示 `preview_packet`、`validator_result`、`blocked_reasons` 和五个 false flags
- 已完成 default-off preview-only outbound adapter
- 已完成显式启用后的 preview-only network-send 能力
- 已完成 ZDoc -> ZBid cross-system controlled smoke report
- 已完成 cross-system smoke stage review

## 3. ZBid 当前基线

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 当前已知 stage review HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 已新增 `app/engine/zdoc_zbid_preview_receiver.py`
- 已新增 `tests/test_zdoc_zbid_preview_receiver.py`
- 已暴露 `POST /local-llm/zdoc-preview-only/receive`
- 已完成 ZBid receiver API runtime smoke
- 已完成 ZBid receiver API smoke stage review
- ZBid receiver 仅 preview-only / no-write / no-evidence

## 4. 已完成验证闭环

- ZDoc preview-only route 本地可达
- ZDoc 前端同源 proxy smoke 通过
- ZDoc outbound adapter fake sender 单元测试通过
- ZBid preview-only receiver/helper 单元测试通过
- ZBid preview-only receiver API runtime smoke 通过
- ZDoc outbound adapter 已成功向 ZBid receiver endpoint 发送 preview-only payload
- ZBid 返回 HTTP `200`
- 返回 `preview_only=true`
- 返回 `no_write=true`
- 返回 `no_evidence=true`
- `preview_packet` 可读
- `validator_result` 可读
- `blocked_reasons` 可读
- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`
- ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均为空
- 未生成 DOCX
- 未触发正式链路

## 5. Step 222 / Step 223 核心结论

Step 222 已完成 ZDoc-ZBid preview-only cross-system controlled smoke。

Step 223 已完成该 smoke 的 stage review。

该结果只证明本地 controlled smoke 下的 preview-only 对接链路成立，不代表以下能力已开放：

- 正式生成
- 正式证据链
- 正式评分链
- DOCX 导出
- review/apply
- ZBid 写回

## 6. 严格未开放边界

- 未开放 `/generate`
- 未开放 `/export_docx`
- 未开放 `/review/apply`
- 未开放 ZBid 写回
- 未开放正式 evidence
- 未开放正式评分依据写入
- 未开放 DOCX 生成
- 未开放 `output/job/export` 写入
- 未进入真实业务联调
- 未进入小范围试用
- 未进入 50 人正式部署设计

## 7. 必须持续禁止

- 不得把 `advisory`、`preview`、`shadow`、`patch`、`diff`、`rollback`、`dry-run` 作为 evidence
- 不得将 preview-only 结果写入正式业务数据
- 不得将 preview-only 结果作为评分依据
- 不得通过 fallback 调用正式接口
- 不得在未授权情况下启动服务、访问端口、调用 endpoint 或写回

## 8. 后续建议

- Step 225 可起草“小范围试用前置边界设计”或“小范围试用授权请求”。
- 小范围试用仍必须限定 preview-only / no-write / no-evidence。
- 小范围试用前应明确试用人员、试用入口、试用数据、允许操作、禁止接口、日志留痕、失败回退和停止条件。
- 50 人正式部署设计仍不得提前进入。
- 正式部署、并发、硬件、队列、备份、运维方案应在小范围试用和问题修正后再启动。
