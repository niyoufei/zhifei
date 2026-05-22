# ZDoc-ZBid preview-only small-scale trial controlled execution stage review

## 1. Step 227 授权来源与执行范围

Step 227 已由用户明确授权执行 ZDoc-ZBid preview-only small-scale trial controlled execution。

本次执行范围仅限 preview-only / no-write / no-evidence 小范围受控试用。

本次试用对象限定为内部 2～5 人小范围角色。

本次试用数据限定为：

- 脱敏样例
- 测试文档
- 非正式投标成果

本次不进入正式生成链。

本次不进入 50 人正式部署设计。

## 2. ZDoc 结果

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`ad288d7ddd9e3758c648f11d3b58931849d842bb`
- 结束后 HEAD：`3d5a48e21979b40b3a41bcf8830ed0523fcf0cad`
- `git status --short`：空
- 新增 trial report：`docs/zdoc-zbid-preview-only-small-scale-trial-controlled-execution-report.md`

## 3. ZBid 结果

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 / 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- `git status --short`：空
- 未 commit
- 未 tag
- 未 push

## 4. 小范围试用执行结果

- 启动服务：ZBid receiver
- 启动命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18764`
- ZBid 服务 PID：`66071`
- 访问端口：`127.0.0.1:18764`
- 调用 endpoint：`POST /local-llm/zdoc-preview-only/receive`
- ZDoc outbound adapter 成功发送 preview-only payload：是
- 发送对象：3 个小范围角色 payload
- ZBid 返回 HTTP `200`：是

## 5. preview-only 结果

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` 可读
- `validator_result` 可读
- `blocked_reasons` 可读

## 6. 五个 no-write / no-formal-chain false flags

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 7. 试用体验记录

- 错误提示已记录
- 人工复核体验已记录
- 仅验证 preview-only 链路、失败提示和人工复核体验
- 未形成正式 evidence
- 未形成正式评分依据

本次通过 `blocked_reasons` 验证 preview-only 试用中的提示边界：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`
- `small_scale_trial_requires_human_review`

## 8. 安全边界

- 未运行 Ollama
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未生成 DOCX
- ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均为空
- 服务已停止 PID `66071`
- `127.0.0.1:18764` 无监听

## 9. 风险结论

本次仅完成 preview-only / no-write / no-evidence 小范围受控试用验证。

本次结果不代表以下能力开放：

- 正式生成
- 正式 evidence
- 评分依据写入
- DOCX 导出
- review/apply
- ZBid 写回
- 50 人正式部署

## 10. 下一步建议

- Step 229 可做小范围试用阶段问题清单与修正边界设计。
- 或做小范围试用阶段总归档。
- 如需继续扩大试用范围，必须另行授权。
- 50 人正式部署设计仍应在小范围试用和问题修正完成后再启动。
