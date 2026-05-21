# ZDoc-ZBid preview-only small-scale trial controlled execution report

## 1. 执行范围

本次 Step 227 执行 ZDoc-ZBid preview-only small-scale trial controlled execution。

本次试用范围限定为：

- preview-only
- no-write
- no-evidence
- no-code-change
- no-formal-chain

本次试用对象范围为内部 2～5 人小范围角色模拟，不引入真实个人敏感信息。

本次试用数据范围为脱敏样例、测试文档、非正式投标成果，不包含真实业务文件、DOCX、正式 evidence、正式评分结果或 writeback 数据。

## 2. ZDoc 仓库结果

- 仓库路径：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`ad288d7ddd9e3758c648f11d3b58931849d842bb`
- 结束后 HEAD：`ad288d7ddd9e3758c648f11d3b58931849d842bb`
- 执行前 `git status --short`：空
- 发送后 `git status --short`：空
- 本报告新增前 `git status --short`：空

## 3. ZBid 仓库结果

- 仓库路径：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 执行前 `git status --short`：空
- 发送后 `git status --short`：空
- 未在 ZBid 仓库 commit、tag 或 push

## 4. 试用对象与数据范围

试用对象范围：内部 2～5 人小范围角色。

本次以 3 个角色进行 preview-only 模拟：

- 试用角色 1：技术标编制人员
- 试用角色 2：复核人员
- 试用角色 3：项目负责人或质量审核角色

试用数据范围：

- 脱敏样例
- 测试文档
- 非正式投标成果

## 5. ZBid 服务启动与停止

成功启动命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18764
```

服务 PID：`66071`

服务端口：`127.0.0.1:18764`

停止结果：

- 已停止 PID `66071`
- `127.0.0.1:18764` 无监听

执行备注：

- 一次初始启动命令使用了错误的 shell `exec` 环境变量写法，返回 code `127`，未启动服务，端口未监听。
- 随后使用上述成功启动命令完成本次试用。

## 6. ZDoc outbound adapter 调用方式

ZDoc 侧通过临时环境变量启用 preview-only outbound network-send：

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18764/local-llm/zdoc-preview-only/receive`

调用方式：

- 在 ZDoc 仓库中直接调用 outbound adapter 生产 helper。
- 使用脱敏样例构造 3 组 preview-only payload。
- 由 `prepare_zdoc_zbid_preview_only_outbound(...)` 发送到 ZBid receiver endpoint。
- 未调用 ZDoc `/local-trial/preview-only` HTTP endpoint。
- 未调用 ZDoc `/generate`、`/export_docx`、`/review/apply`。

## 7. 调用 endpoint 清单

本次仅调用以下 endpoint：

- `POST http://127.0.0.1:18764/local-llm/zdoc-preview-only/receive`

未调用其他 ZBid endpoint。

未调用任何 ZDoc endpoint。

## 8. ZBid receiver endpoint 返回状态

3 个试用角色均返回：

- HTTP `200`
- `ok=true`
- `outbound_status=sent_preview_only`
- `network_send_attempted=true`
- `network_send_succeeded=true`
- `receiver_status=accepted_preview_only`
- `receiver_accepted=true`

## 9. preview-only / no-write / no-evidence 验证结果

3 个试用角色均返回：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`

## 10. preview_packet / validator_result / blocked_reasons 验证结果

3 个试用角色均返回：

- `preview_packet` 可读
- `validator_result` 可读
- `blocked_reasons` 可读

统一 `blocked_reasons` 包含：

- `preview_only_is_not_writeback_permission`
- `preview_only_is_not_evidence`
- `zbid_preview_scoring_is_not_evidence`
- `small_scale_trial_requires_human_review`

## 11. 五个 no-write / no-formal-chain false flags

3 个试用角色均返回：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 12. 错误提示验证结果

错误提示可识别。

本次通过 `blocked_reasons` 验证 preview-only 试用中的提示边界：

- preview-only 不是写回许可。
- preview-only 不是 evidence。
- ZBid preview scoring 不是 evidence。
- 小范围试用需要人工复核。

本次未制造正式链失败、DOCX 失败、写回失败或未知 endpoint 失败。

## 13. 人工复核体验记录

人工复核提示可识别。

3 个试用 payload 均包含人工复核提示：

```text
Preview-only advisory; no-write; no-evidence; manual review required.
```

本次验证结论：

- 技术标编制人员可看到该结果仅为 preview-only advisory。
- 复核人员可看到 no-write / no-evidence 边界。
- 项目负责人或质量审核角色可看到必须人工复核后才能进入后续授权流程。

## 14. output/job/export 快照

ZDoc 前置快照：

```text
空
```

ZDoc 后置快照：

```text
空
```

ZBid 前置快照：

```text
空
```

ZBid 后置快照：

```text
空
```

结论：ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均无新增。

## 15. 严格未发生事项

- 未运行 Ollama
- 未触发 `/generate`
- 未触发 `/export_docx`
- 未触发 `/review/apply`
- 未触发 ZBid 写回
- 未生成 DOCX
- 未写 `output/job/export`
- 未将 preview-only 结果作为 evidence
- 未将 preview-only 结果作为评分依据
- 未写入正式业务数据
- 未进入正式生成链
- 未进入正式证据链
- 未进入正式评分链
- 未进入正式导出链
- 未进入正式写回链
- 未进入 50 人正式部署设计
- 未修改 ZDoc 代码、tests、frontend 或既有 docs
- 未修改 ZBid 代码、tests 或既有 docs

## 16. 风险结论

本次仅完成本地 preview-only / no-write / no-evidence 小范围受控试用验证。

本次结果说明：

- ZBid receiver API 可达。
- ZDoc outbound adapter 可向 ZBid receiver endpoint 发送 preview-only payload。
- ZBid receiver 返回 HTTP `200`。
- `preview_packet`、`validator_result`、`blocked_reasons` 均可读。
- 五个 no-write / no-formal-chain false flags 均保持 false。
- 错误提示和人工复核提示可识别。

本次结果不代表以下能力开放：

- 正式生成
- 正式 evidence
- 正式评分依据写入
- DOCX 导出
- review/apply
- ZBid 写回
- 50 人正式部署

## 17. 下一步建议

- Step 228 可做小范围试用 controlled execution stage review。
- 如需扩大小范围试用人员、数据或入口，必须另行授权。
- 如发现问题需要修复，必须另行授权代码修改。
- 50 人正式部署设计仍不得提前进入。
