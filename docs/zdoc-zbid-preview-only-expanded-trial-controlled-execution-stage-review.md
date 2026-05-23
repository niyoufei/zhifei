# ZDoc-ZBid preview-only expanded trial controlled execution stage review

## 1. Step 238 授权来源与执行范围

Step 238 已由用户明确授权执行 ZDoc-ZBid preview-only expanded trial controlled execution。

授权与执行范围限定为：

- 仅限 preview-only / no-write / no-evidence 扩大试用受控验证。
- 试用对象限定为内部受控 5～10 人或等效角色组。
- 试用数据限定为脱敏样例、测试文档、非正式投标成果。
- 不进入正式生成链。
- 不进入 50 人正式部署设计。

Step 238 仅验证扩大试用阶段的 preview-only 链路、错误提示、blocked_reasons 可读性、日志留痕完整性和人工复核流程体验，不代表正式上线或真实业务联调。

## 2. ZDoc 结果

- 仓库：`/Users/youfeini/Desktop/文档生成系统`
- 分支：`main`
- 开始前 HEAD：`07b88860e0ae9273f258c43d8fe8c645f31bd4ca`
- 结束后 HEAD：`e699d5e12cfda60e02614f8dee939058d46b8125`
- `git status --short`：空
- 新增报告：`docs/zdoc-zbid-preview-only-expanded-trial-controlled-execution-report.md`

## 3. ZBid 结果

- 仓库：`/Users/youfeini/Desktop/ZhiFei_BizSystem-local-llm-clean`
- 分支：`local-llm-integration-clean`
- 开始前 / 结束时 HEAD：`378355755372e03ac4f4064af59b287054984c25`
- `git status --short`：空
- 未 commit。
- 未 tag。
- 未 push。

## 4. 扩大试用执行结果

- 启动服务：ZBid receiver。
- 启动命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18765`
- 服务 PID：`25073`
- 访问端口：`127.0.0.1:18765`
- 调用 endpoint：`POST /local-llm/zdoc-preview-only/receive`
- ZDoc outbound adapter 成功发送 preview-only payload：是。
- 5 个代表性角色 payload：均 HTTP 200。

5 个代表性角色 payload 覆盖：

- 技术标编制。
- 复核。
- 项目负责人。
- 质控审核。
- 备用综合角色。

## 5. preview-only 结果

Step 238 的 5 次调用均验证：

- `preview_only=true`
- `no_write=true`
- `no_evidence=true`
- `preview_packet` 可读。
- `validator_result` 可读。
- `blocked_reasons` 可读。

## 6. 五个 no-write / no-formal-chain false flags

Step 238 的 5 次调用均验证：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

## 7. 试用观察记录

Step 238 已记录以下观察项：

- 错误提示已记录。
- `blocked_reasons` 可读性已记录。
- 日志留痕完整性已记录。
- 人工复核流程体验已记录。

本轮观察记录仅服务 preview-only / no-write / no-evidence 扩大试用，不得作为正式 evidence 或评分依据。

## 8. 安全边界

Step 238 安全边界结果：

- 未运行 Ollama。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未生成 DOCX。
- ZDoc 与 ZBid 两侧 `output/job/export` 前后快照均为空。
- 服务已停止 PID `25073`。
- `127.0.0.1:18765` 无监听。

## 9. 风险结论

本次仅完成 preview-only / no-write / no-evidence 扩大试用受控验证。

本次结果不代表：

- 正式生成开放。
- 正式 evidence 开放。
- 评分依据写入开放。
- DOCX 导出开放。
- review/apply 开放。
- ZBid 写回开放。
- 真实业务联调开放。
- 50 人正式部署开放。

preview-only 结果、blocked_reasons、validator_result、日志摘要和人工复核记录均不得作为正式 evidence 或评分依据。

## 10. 下一步建议

- Step 240 可做扩大试用阶段总归档。
- 或做“进入正式部署前置条件矩阵”。
- 50 人正式部署设计仍应在扩大试用、问题收敛、必要修正和复验完成后再启动。

在进入任何后续阶段前，仍需保持单步授权：

- 代码优化需单独授权。
- UI / 文案优化需单独授权。
- 日志增强需单独授权。
- 服务启动、端口访问、endpoint 调用需单独授权。
- 更大范围试用需单独授权。
- 正式部署前置设计需单独授权。
