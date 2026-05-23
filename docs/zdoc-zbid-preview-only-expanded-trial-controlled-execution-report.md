# ZDoc-ZBid preview-only expanded trial controlled execution report

## 1. 执行范围

本报告归档 Step 238：ZDoc-ZBid preview-only expanded trial controlled execution。

本步仅执行 preview-only / no-write / no-evidence 扩大试用受控验证：

- 试用对象限定为内部受控 5～10 人或等效角色组。
- 本轮实际验证 5 个代表性角色 payload。
- 试用数据限定为脱敏样例、测试文档、非正式投标成果。
- 仅调用 ZBid receiver endpoint：`POST /local-llm/zdoc-preview-only/receive`。
- 未修改 ZDoc 代码。
- 未修改 ZBid 代码。
- 未修改 tests、frontend 或既有 docs。
- 未进入正式生成链、正式证据链、正式评分链、正式导出链、正式写回链。
- 未进入 50 人正式部署设计。

## 2. 仓库与 git 状态

### ZDoc

- 仓库路径：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`07b88860e0ae9273f258c43d8fe8c645f31bd4ca`
- 试用执行结束、报告提交前 HEAD：`07b88860e0ae9273f258c43d8fe8c645f31bd4ca`
- 执行前 `git status --short`：空
- 试用执行后、报告提交前 `git status --short`：空
- 本报告提交后的最终 HEAD：以 Step 238 完成回报为准

### ZBid

- 仓库路径：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- 执行前 `git status --short`：空
- 执行后 `git status --short`：空
- 未在 ZBid 仓库 commit、tag 或 push。

## 3. 试用对象与数据范围

- 扩大试用对象范围：内部受控 5～10 人或等效角色组。
- 本轮实际验证角色：5 个代表性角色 payload。
- 角色 1：技术标编制。
- 角色 2：复核。
- 角色 3：项目负责人。
- 角色 4：质控审核。
- 角色 5：备用综合角色。
- 试用数据范围：脱敏样例、测试文档、非正式投标成果。

payload 未包含真实业务文件、DOCX、正式 evidence、正式评分结果或 writeback 数据。

## 4. 服务启动与端口

- 启动服务：ZBid preview-only receiver。
- 启动命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18765`
- 服务 PID：`25073`
- 服务端口：`127.0.0.1:18765`
- 服务启动结果：成功。
- 试用结束后停止 PID：`25073`
- 停止后监听状态：`127.0.0.1:18765` 无监听。

## 5. ZDoc outbound adapter 调用方式

ZDoc 侧使用临时环境变量调用 outbound adapter：

- `PYTHONDONTWRITEBYTECODE=1`
- `ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED=true`
- `ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT=http://127.0.0.1:18765/local-llm/zdoc-preview-only/receive`

调用对象：

- `backend.zhifei_autoplan.zdoc_zbid_preview_outbound.build_zdoc_zbid_preview_only_outbound_config`
- `backend.zhifei_autoplan.zdoc_zbid_preview_outbound.prepare_zdoc_zbid_preview_only_outbound`

仅使用临时环境变量，未写入 `.env`、配置文件或持久配置。

## 6. 调用 endpoint 清单

本步仅调用：

- `POST http://127.0.0.1:18765/local-llm/zdoc-preview-only/receive`

未调用：

- `/local-trial/preview-only`
- `/generate`
- `/export_docx`
- `/review/apply`
- 任何其他 ZDoc endpoint
- 任何其他 ZBid endpoint

## 7. HTTP 状态汇总

| 角色 | outbound 状态 | HTTP 状态 | network_send_attempted | network_send_succeeded |
| --- | --- | --- | --- | --- |
| 技术标编制 | `sent_preview_only` | 200 | true | true |
| 复核 | `sent_preview_only` | 200 | true | true |
| 项目负责人 | `sent_preview_only` | 200 | true | true |
| 质控审核 | `sent_preview_only` | 200 | true | true |
| 备用综合角色 | `sent_preview_only` | 200 | true | true |

结论：5 个代表性角色 payload 均返回 HTTP 200。

## 8. preview-only / no-write / no-evidence 验证结果

5 次调用均返回：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `receiver_accepted=true`

## 9. 数据字段验证结果

5 次调用均确认：

- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。
- `receiver_blocked_reasons` 为空。

本轮 `blocked_reasons` 包含：

- `expanded_trial_preview_only`
- `manual_review_required_before_any_formal_use`
- `preview_only_result_not_evidence`

## 10. 五个 false flags 验证结果

5 次调用均确认：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 11. 错误提示验证结果

本轮 5 个代表性角色 payload 均成功返回 HTTP 200，未触发 receiver 错误路径。

可识别的人工提示与边界提示通过 `blocked_reasons` 呈现：

- 当前结果仅为 expanded trial preview-only。
- 正式使用前必须人工复核。
- preview-only 结果不得作为 evidence。

如后续出现错误，应继续通过 preview-only / no-write 结果记录错误原因，不得 fallback 到正式接口。

## 12. blocked_reasons 可读性记录

本轮 `blocked_reasons` 为列表结构，内容可直接阅读并用于人工复核：

- 可区分 preview-only 试用状态。
- 可提示正式使用前需要人工复核。
- 可提示 preview-only 结果不是 evidence。

`blocked_reasons` 不得作为正式 evidence 或评分依据。

## 13. 日志留痕完整性记录

本轮服务日志记录了 5 次授权 endpoint 调用：

- `POST /local-llm/zdoc-preview-only/receive HTTP/1.1` 200 OK
- 共 5 次。

本报告记录了：

- 仓库路径、分支、HEAD。
- 服务启动命令、PID、端口。
- 临时环境变量启用情况。
- 调用 endpoint。
- 每个角色 payload 的 HTTP 状态。
- preview-only / no-write / no-evidence 结果。
- 五个 false flags。
- output/job/export 前后快照。
- 服务停止和端口无监听结果。

本轮未记录敏感业务数据，未记录正式 evidence，未写入正式评分依据。

## 14. 人工复核流程体验记录

本轮人工复核流程可基于以下字段开展：

- `preview_packet`：用于查看脱敏 preview-only metadata。
- `validator_result`：用于查看 metadata-only 校验状态。
- `blocked_reasons`：用于识别 preview-only 边界和人工复核要求。
- 五个 false flags：用于确认未进入正式链。

建议后续扩大试用继续使用人工复核检查表，并要求试用人员确认：

- preview-only 状态清晰可见。
- no-write / no-evidence 边界清晰可见。
- blocked_reasons 可读且能指导下一步上报或停止。
- 任一 false flag 非 false 时立即停止。

## 15. output/job/export 快照

### ZDoc

- 前置快照：空。
- 后置快照：空。
- 前后差异：无。

### ZBid

- 前置快照：空。
- 后置快照：空。
- 前后差异：无。

## 16. 严格未发生事项

- 未运行 Ollama。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未将 preview-only 结果作为 evidence。
- 未将 preview-only 结果作为评分依据。
- 未写入正式业务数据。
- 未进入正式生成链。
- 未进入正式证据链。
- 未进入正式评分链。
- 未进入正式导出链。
- 未进入正式写回链。
- 未进入 50 人正式部署设计。

## 17. 风险结论

本次 expanded trial controlled execution 验证了本地受控范围内的 preview-only / no-write / no-evidence 扩大试用链路：

- ZDoc outbound adapter 可向 ZBid receiver endpoint 发送 preview-only payload。
- ZBid receiver endpoint 可达。
- 5 个代表性角色 payload 均返回 HTTP 200。
- preview_packet、validator_result、blocked_reasons 可读。
- 五个 no-write / no-formal-chain false flags 均为 false。
- 两仓 output/job/export 前后快照均为空。

本结果不代表正式生成、正式 evidence、评分依据写入、DOCX 导出、review/apply、ZBid 写回、真实业务联调或 50 人正式部署设计开放。

## 18. 下一步建议

- Step 239 可做 expanded trial controlled execution stage review。
- 如后续继续扩大试用范围，必须另行授权。
- 如需优化错误提示、blocked_reasons 展示、日志结构或人工复核流程，也必须另行授权。
- 50 人正式部署设计仍不得提前进入。
