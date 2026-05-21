# ZDoc Local Trial Preview-Only Route Code Implementation Stage Review

## 1. Scope

本文档仅复盘归档 Step 181：preview-only route code implementation 的实现范围、测试结果、安全边界和未开放事项。

Step 182 为 docs-only stage review。本步不修改代码，不修改 tests，不修改 frontend，不修改既有 docs，不运行 pytest，不启动后端或前端服务，不运行 Ollama，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`，不进入真实 ZDoc/ZBid 联调，也不进入 50 人团队正式部署设计。

## 2. Files Changed In Step 181

Step 181 修改范围如下：

- 新增 `backend/app/routers/local_trial_preview_only.py`。
- 新增 `backend/tests/test_local_trial_preview_only_route.py`。
- 修改 `backend/app/main.py`，仅注册新 router。

Step 181 未修改：

- orchestrator 正式生成链。
- `llm_client` 正文生成链。
- export / DOCX 导出链。
- review/apply 链。
- ZBid 写回链。
- frontend。
- docs。
- `output/job/export`。
- 配置、部署脚本、数据库或模型文件。

## 3. Implementation Summary

Step 181 新增本地试用专用 preview-only route：

- `POST /local-trial/preview-only`

该 route 的实现边界为：

- 只调用 fake preview packet helper。
- 只调用 fake ZBid preview input validator。
- 只返回 metadata / preview-only / no-write 结果。
- 返回 `preview_packet`。
- 返回 `validator_result`。
- 返回 `blocked_reasons`。
- 返回 `preview_only=true`。
- 返回 `no_write=true`。
- 返回 `route_name=local_trial_preview_only`。
- 返回 `endpoint_path=/local-trial/preview-only`。
- 返回五个正式链 flags，且恒 false：
  - `formal_writeback_allowed=false`
  - `review_apply_allowed=false`
  - `docx_export_allowed=false`
  - `zbid_writeback_allowed=false`
  - `output_write_allowed=false`
- 返回正式链不触发字段：
  - `calls_generate_route=false`
  - `calls_export_docx_route=false`
  - `calls_review_apply_route=false`
  - `triggers_generation_chain=false`
  - `triggers_export_chain=false`
  - `affects_generation=false`
  - `affects_export=false`
  - `affects_zbid_writeback=false`
  - `writes_output=false`
  - `writes_job=false`
  - `writes_export=false`
  - `calls_ollama=false`
  - `calls_external_model_api=false`
  - `downloads_models=false`
  - `pulls_models=false`

route 输入为 fake/local trial metadata。route 输出由 preview packet helper 和 validator result 组合而成，并合并二者 `blocked_reasons`，用于前端或人工审计展示。

## 4. Test Results From Step 181

Step 181 已运行并通过以下测试：

- 单文件 route 测试：
  - `python -m pytest backend/tests/test_local_trial_preview_only_route.py -vv`
  - `7 passed in 0.16s`

- route + helper / validator 组合：
  - `python -m pytest backend/tests/test_local_trial_preview_only_route.py backend/tests/test_zdoc_zbid_preview_packet.py backend/tests/test_zbid_preview_input_validator.py -vv`
  - `39 passed in 0.20s`

- import-isolation 组合：
  - `python -m pytest backend/tests/test_local_trial_preview_only_route.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `10 passed in 1.03s`

- `git diff --check` 通过。
- `git diff --cached --check` 通过。

上述测试均未启动后端服务，未启动前端服务，未访问本地端口，未运行 Ollama，未触发正式生成、DOCX 导出、review/apply 或 ZBid 写回。

## 5. Route Test Coverage Summary

Step 181 新增测试覆盖以下行为：

- route 返回 HTTP 200。
- route 返回 `preview_only=true`。
- route 返回 `no_write=true`。
- route 返回 `preview_packet`。
- route 返回 `validator_result`。
- route 返回可读 `blocked_reasons`。
- 顶层五个正式链 flags 恒 false。
- `preview_packet` 五个正式链 flags 恒 false。
- `validator_result` 五个正式链 flags 恒 false。
- `calls_generate_route=false`。
- `calls_export_docx_route=false`。
- `calls_review_apply_route=false`。
- `affects_zbid_writeback=false`。
- `writes_output=false`。
- `writes_job=false`。
- `writes_export=false`。
- missing scoring refs 场景 blocked。
- unsafe evidence 场景 blocked。
- formal request 场景 blocked。
- route import 不拉入 orchestrator、`llm_client`、provider、generation、export、review、actions_bridge、ZBid 写回模块或 `docx`。
- route 源码不调用 formal route、ZBid writeback、`requests` 或 `httpx`。
- route 测试前后 `output`、`job`、`export` 文件计数保持不变。

## 6. Safety Boundaries Confirmed

Step 181 已保持以下安全边界：

- 未修改正式生成链。
- 未修改 DOCX 导出链。
- 未修改 review/apply。
- 未修改 ZBid 写回链。
- 未修改 frontend。
- 未修改 docs。
- 未写 `output/job/export`。
- 未启动真实后端服务。
- 未启动前端服务。
- 未运行 Ollama。
- 未访问端口。
- 未调用外部模型/API。
- 未下载或拉取模型。
- 未触发 `/generate`。
- 未触发 `/export_docx`。
- 未触发 `/review/apply`。
- 未触发 ZBid 写回。
- 未调用 ZBid API / DB / writeback。
- 未生成 DOCX。
- 未进入本地化部署执行。
- 未进入 50 人团队正式部署设计。

当前 route 仅表示本地试用阶段新增了 preview-only / metadata-only 的后端入口，不代表正式生成、正式导出、正式写回或真实 ZDoc/ZBid 联调已开放。

## 7. Explicit Non-Capabilities

Step 181 未实现以下事项：

- 未做真实 ZDoc/ZBid 联调。
- 未做真实后端服务 smoke。
- 未做前端接入。
- 未验证真实运行端口下的 `/local-trial/preview-only`。
- 未开放正式生成。
- 未开放 DOCX 导出。
- 未开放 review/apply。
- 未开放 ZBid 写回。
- 未调用 ZBid API。
- 未访问 ZBid DB。
- 未执行 formal writeback。
- 未执行 formal writeback dry-run。
- 未实现真实 candidate patch。
- 未读取真实正文计算 hash。
- 未比较真实 source section 内容。
- 未写 `output/job/export`。
- 未进入 50 人团队正式部署设计。

## 8. Remaining Risks And Limits

当前已知限制：

1. route 目前只在 TestClient 层验证，尚未启动真实后端服务做 runtime smoke。
2. route 未接入 frontend，页面仍未调用 `/local-trial/preview-only`。
3. route 仅组合 fake preview packet helper 与 fake ZBid preview validator，不代表真实 ZBid API 输入已实现。
4. route 未验证真实 evidence anchor。
5. route 未验证真实 scoring clause refs。
6. route 未进入真实本地小范围试用数据集。
7. route 未开放任何正式链权限。

这些限制不影响 Step 181 的实现结论：本地试用专用 preview-only route 已以 no-write / metadata-only 形式落地，并通过 fake-only route tests 与 import-isolation 组合测试。

## 9. Recommended Next Step

建议下一步为：

ZDoc Step 183：preview-only route runtime smoke authorization request，docs-only / authorization-request-only。

Step 183 仅起草 runtime smoke 授权请求，不得启动后端服务，不得访问端口，不得运行 Ollama，不得触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不得写 `output/job/export`。

只有用户在后续明确授权后，才可启动后端服务并访问新 route 做 runtime smoke。

## 10. Safety Conclusion

Step 181 已完成本地试用专用 preview-only route 的最小代码实现和测试覆盖。当前系统新增了 `POST /local-trial/preview-only`，可返回 preview packet、validator result、blocked_reasons、preview-only / no-write 状态和五个恒 false 的正式链 flags。

当前仍不代表真实 ZDoc/ZBid 联调已完成，不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback 或 `output/job/export` 写入已开放，也不代表 50 人团队正式部署设计已启动。
