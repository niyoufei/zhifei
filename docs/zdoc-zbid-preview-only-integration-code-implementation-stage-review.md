# ZDoc-ZBid Preview-Only Integration Code Implementation Stage Review

## 1. Scope

本文档对应 Step 203：ZDoc-ZBid preview-only integration code implementation stage review。

本步仅归档 Step 202 的 ZDoc 侧 preview-only outbound adapter 代码实现结果、测试结果、安全边界和未验证事项。

本步性质为 docs-only / stage-review-only / no-code-change / no-service / no-port-access / no-writeback：

- 不修改代码。
- 不修改 tests。
- 不修改 frontend。
- 不修改既有 docs。
- 不运行 pytest。
- 不启动服务。
- 不访问端口。
- 不运行 Ollama。
- 不调用 `/local-trial/preview-only`。
- 不调用任何 ZBid endpoint。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不触发 ZBid 写回。
- 不生成 DOCX。
- 不写 `output/job/export`。
- 不进入真实 ZDoc/ZBid 联调。
- 不进入 50 人正式部署设计。

本文档不代表 Step 204 或任何后续 runtime smoke、服务启动、端口访问、接口调用、ZBid 侧接收验证或跨系统联调已获得授权。

## 2. Step 202 Authorization and Execution Scope

Step 202 的用户授权范围为：

- 仅允许在 ZDoc 侧新增 preview-only outbound/client/adapter 或最小配置占位。
- 仅用于传递 `preview_packet`、`validator_result`、`blocked_reasons` 和 no-write / no-formal-chain flags。
- 未明确 ZBid 仓库路径、分支和允许文件范围前，不得修改 ZBid 代码。

Step 202 的执行范围实际保持在 ZDoc 仓库当前工作目录内：

- 未修改 ZBid 仓库。
- 未修改任何 ZBid 代码。
- 未启动服务。
- 未访问端口。
- 未调用 `/local-trial/preview-only`。
- 未调用任何 ZBid endpoint。
- 未执行真实 ZDoc/ZBid 联调。
- 未执行 runtime smoke。

## 3. Files Added in Step 202

Step 202 实际新增文件：

- `backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`
- `backend/tests/test_zdoc_zbid_preview_outbound.py`

Step 202 未修改：

- ZBid 代码。
- 正式生成链。
- DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- frontend。
- docs。
- `output/job/export`。
- 配置文件、部署脚本、数据库、模型或缓存文件。

## 4. Adapter Responsibility

新增 adapter 文件：

`backend/zhifei_autoplan/zdoc_zbid_preview_outbound.py`

职责：

- 构造 ZDoc -> ZBid preview-only outbound envelope。
- 承载 `preview_packet`。
- 承载 `validator_result`。
- 承载 `blocked_reasons`。
- 承载 no-write / no-formal-chain flags。
- 提供 default-off 的配置占位。
- 在未配置或未授权状态下返回 disabled / preview-only / no-write 状态。
- 在配置 endpoint 后仍只返回 `configured_not_sent`，不发送网络请求。
- 对无效 payload 返回 preview-only / no-write 错误，不 fallback 到正式接口。

adapter 的默认行为：

- `enabled=false`
- `default_off=true`
- `auto_send_allowed=false`
- `network_send_allowed=false`
- `network_send_attempted=false`
- `zbid_writeback_attempted=false`

## 5. No-Write and No-Formal-Chain Flags

Step 202 新增 adapter 中 no-write / no-formal-chain flags 至少包括：

- `generate_called=false`
- `export_docx_called=false`
- `review_apply_called=false`
- `zbid_writeback_called=false`
- `output_job_export_written=false`

同时包含并保持以下正式链 flags 为 `false`：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `affects_zbid_writeback=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

这些 flags 仅用于证明当前 preview-only outbound envelope 未进入正式链，不构成写回许可。

## 6. Boundary Confirmation

Step 202 已确认：

- 未修改 ZBid 代码。
- 未修改正式生成链。
- 未修改导出链。
- 未修改 review apply 链。
- 未引入 ZBid 写回。
- 未新增通用 ZBid proxy。
- 未新增任意路径转发。
- 未新增正式写回入口。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未将 advisory / preview / shadow / patch / diff / rollback / dry-run 作为 evidence。

adapter 不导入或调用：

- `orchestrator`
- `llm_client`
- `provider`
- `generation`
- `export`
- `review`
- `actions_bridge`
- `zbid_snapshot_mapper`
- `requests`
- `httpx`
- `urllib`
- `socket`
- `subprocess`
- `docx`

## 7. Verification Results from Step 202

Step 202 已运行并通过以下验证：

```bash
python -m pytest backend/tests/test_zdoc_zbid_preview_outbound.py -vv
```

结果：

- `10 passed in 0.05s`

```bash
python -m pytest backend/tests/test_zdoc_zbid_preview_outbound.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py -vv
```

结果：

- `42 passed in 0.07s`

```bash
python -m pytest backend/tests/test_zdoc_zbid_preview_outbound.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv
```

结果：

- `13 passed in 0.78s`

Step 202 还完成：

- `git diff --check`：通过。
- `git diff --cached --check`：通过。

本 Step 203 未重新运行 pytest；以上为 Step 202 阶段结果归档。

## 8. Test Coverage Summary

Step 202 新增测试文件：

`backend/tests/test_zdoc_zbid_preview_outbound.py`

测试已覆盖：

- outbound config 默认 disabled。
- 默认状态不允许网络发送。
- 配置 endpoint 后仍为 `configured_not_sent`。
- 不自动发送到 ZBid。
- payload 仅包含 `preview_packet`、`validator_result`、`blocked_reasons` 和 false flags。
- `prepare_zdoc_zbid_preview_only_outbound` 默认 default-off。
- 缺少 endpoint 时返回 blocked / preview-only / no-write 状态。
- 无效 payload 输入返回 preview-only / no-write 错误。
- formal flags 和用户可见 false flags 恒 false。
- 不写 `output/job/export`。
- import isolation 不拉入主生成链或写回链模块。
- 源码不导入网络 client 或正式链模块。

## 9. Strict Non-Occurrence in Step 202

Step 202 严格未发生：

- 未修改 ZBid 代码。
- 未修改正式生成链。
- 未修改 DOCX 导出链。
- 未修改 review/apply 链。
- 未修改 ZBid 写回链。
- 未修改 frontend。
- 未修改 docs。
- 未启动后端服务。
- 未启动前端服务。
- 未访问任何本地端口。
- 未运行 Ollama。
- 未运行 `ollama serve`。
- 未调用 `/local-trial/preview-only`。
- 未调用任何 ZBid endpoint。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用 ZBid API / DB / writeback。
- 未生成 DOCX。
- 未写 `output/job/export`。
- 未进入真实 ZDoc/ZBid 联调。
- 未进入 50 人正式部署设计。

## 10. Unverified Items

当前仍未验证：

- 未启动服务。
- 未访问端口。
- 未运行 Ollama。
- 未调用 `/local-trial/preview-only`。
- 未调用任何 ZBid endpoint。
- 未做真实 ZDoc/ZBid 联调。
- 未做 runtime smoke。
- 未验证 ZBid 接收方。
- 未验证跨系统 preview-only receiver/display。
- 未验证 ZBid 侧仓库路径、分支、HEAD 或允许文件范围。
- 未验证真实网络传输。

这些事项均需后续单独授权后才能执行。

## 11. Risk Conclusion

当前风险结论：

1. 当前只是 ZDoc 侧 default-off preview-only outbound adapter 基础。
2. 当前不代表 ZBid 接收方已实现。
3. 当前不代表 ZBid 仓库路径、分支、HEAD 或允许文件范围已确认。
4. 当前不代表服务启动已授权。
5. 当前不代表端口访问已授权。
6. 当前不代表跨系统接口调用已授权。
7. 当前不代表 ZBid 侧接收验证已授权。
8. 当前不代表真实 ZDoc/ZBid 联调已执行。
9. 当前不代表正式生成链开放。
10. 当前不代表 DOCX 导出开放。
11. 当前不代表 review/apply 开放。
12. 当前不代表 ZBid 写回开放。
13. 当前不代表 50 人正式部署设计已启动。

## 12. Recommended Next Step

后续可选下一步：

`ZDoc Step 204：ZDoc-ZBid preview-only outbound adapter controlled smoke authorization request`

建议性质：

- docs-only / authorization-request-only。
- 起草受控 smoke 授权请求。
- 明确是否允许调用 adapter。
- 明确是否允许启动服务。
- 明确是否允许访问端口。
- 明确是否允许调用 `/local-trial/preview-only`。
- 明确是否允许配置 fake endpoint。
- 明确不得调用任何 ZBid endpoint，除非用户后续单独授权。

另一个更保守的下一步也可以是：

`ZDoc Step 204：ZBid receiver repository and file-scope confirmation request`

目的：

- 先确认 ZBid 仓库路径。
- 确认 ZBid 分支。
- 确认 ZBid 开始前 HEAD。
- 确认 ZBid 允许文件范围。
- 确认 ZBid 禁止修改范围。
- 在这些信息明确前，不修改 ZBid 代码。

无论选择哪条路径，后续任何服务启动、端口访问、接口调用、ZBid 侧接收验证或跨系统联调，均需单独授权。

## 13. Safety Conclusion

Step 202 已完成 ZDoc 侧 preview-only outbound adapter 的最小代码基础：

- 新增 adapter。
- 新增测试。
- adapter 默认 disabled / default-off。
- 即使配置 endpoint 也只返回 `configured_not_sent`。
- 不发送网络请求。
- 不写 `output/job/export`。
- 不触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。
- no-write / no-formal-chain flags 恒 false。

Step 203 仅完成阶段复盘归档。

当前系统仍未进入真实 ZDoc/ZBid 联调；ZBid 接收方、服务启动、端口访问、接口调用、runtime smoke、正式生成、DOCX 导出、review/apply、ZBid 写回和 50 人正式部署设计仍未开放。
