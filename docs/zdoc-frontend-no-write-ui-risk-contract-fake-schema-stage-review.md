# ZDoc Frontend No-Write UI Risk Contract Fake Schema Stage Review

## 1. Scope

本文档是 Step 166 的 docs-only stage review，用于归档 Step 165 新增的 frontend no-write UI risk contract fake schema tests。

本步只做归档，不修改前端代码，不修改测试，不修改既有文档，不运行 pytest，不运行 Ollama，不启动服务，不访问端口，不触发 `/generate`、`/export_docx`、`/review/apply` 或 ZBid 写回，不写 `output/job/export`，不进入本地化部署执行，不进入 50 人团队正式部署设计。

## 2. Source Risk From Step 164

Step 164 针对 Step 162 / Step 163 发现的前端 UI 风险形成了 contract design。

已确认的风险输入：

- 主页面存在“生成 Word 文档”入口。
- 页面缺少 preview-only 提示。
- 页面缺少 no-write 提示。
- 页面缺少 `blocked_reasons` 展示。
- 页面缺少 evidence 边界提示。
- 用户可能误认为 preview 已可正式生成或正式导出。
- Step 162 未发现 `/export_docx`、`/review/apply`、ZBid 文本或入口。
- Step 162 未点击或提交“生成 Word 文档”入口。

这些风险仍是 UI contract 风险，不代表 Step 162 或 Step 165 触发了正式链。

## 3. File Added In Step 165

Step 165 新增：

- `backend/tests/test_frontend_no_write_ui_risk_contract_schema.py`

Step 165 未修改：

- 生产代码
- 前端代码
- 既有 tests
- 既有 docs
- 配置文件
- 部署脚本
- `output/job/export`
- `backend/data/autoplan/jobs`
- `build`

## 4. Step 165 Test Evidence

Step 165 已运行并通过以下限定测试命令：

- `python -m pytest backend/tests/test_frontend_no_write_ui_risk_contract_schema.py -vv`
  - `8 passed in 0.05s`

- `python -m pytest backend/tests/test_frontend_no_write_ui_risk_contract_schema.py backend/tests/test_local_trial_smoke_checklist_schema.py backend/tests/test_local_trial_smoke_execution_plan_schema.py backend/tests/test_local_trial_runtime_authorization_gate_schema.py -vv`
  - `62 passed in 0.10s`

- `python -m pytest backend/tests/test_frontend_no_write_ui_risk_contract_schema.py backend/tests/test_llm_client.py::test_llm_client_import_does_not_pull_main_chain_modules backend/tests/test_ollama_provider_adapter.py::test_adapter_import_does_not_pull_main_chain_modules backend/tests/test_section_drafts.py::test_section_drafts_module_does_not_pull_main_chain_or_write_modules -vv`
  - `11 passed in 0.86s`

Step 165 未运行 full backend tests。此前 Step 98B 已确认 `backend/tests` full suite 存在既有 collection/order import-isolation 问题，因此该阶段继续使用限定测试组合。

## 5. Contract Areas Fixed By Fake Schema Tests

Step 165 fake schema tests 已固化以下内容：

- contract required sections 完整。
- “生成 Word 文档”入口风险契约。
- preview-only 显示要求。
- no-write 显示要求。
- `blocked_reasons` 显示要求。
- advisory/evidence 边界。
- preview 不得显示为正式正文。
- 正式链入口必须 blocked。
- 五个正式链 flags 恒 false。
- no side effects。
- import isolation。

required sections 已固化为：

- `risk_summary`
- `no_write_ui_principles`
- `word_button_risk_contract`
- `blocked_reasons_display_contract`
- `evidence_boundary_display_contract`
- `formal_chain_entry_control`
- `acceptance_criteria`
- `future_steps`

## 6. Word Button Risk Contract Confirmed

Step 165 tests 已固化“生成 Word 文档”入口风险契约：

- preview-only 阶段不得作为可提交正式生成按钮。
- 如保留入口，必须 disabled。
- 如显示按钮，必须提示“正式导出未开放”。
- 不得触发 `/generate`。
- 不得触发 `/export_docx`。
- 不得写 `output/job/export`。
- 不得生成 DOCX。

该契约只被 fake schema tests 固化，尚未在真实前端 UI 中实现。

## 7. Preview-Only And No-Write Display Contract Confirmed

Step 165 tests 已固化 UI 必须明确展示：

- preview-only
- no-write
- `blocked_reasons`
- advisory 不是 evidence
- preview 不是正式正文

该契约要求用户能明确看到当前处于 preview-only / no-write 阶段，并能读懂为什么不能生成、导出、写回或进入 review/apply。

## 8. Evidence Boundary Contract Confirmed

Step 165 tests 已固化 evidence 边界：

- AI advisory 不得作为 evidence。
- preview advisory 不得作为 evidence。
- shadow candidate 不得作为 evidence。
- patch preview 不得作为 evidence。
- diff preview 不得作为 evidence。
- rollback plan 不得作为 evidence。
- dry-run result 不得作为 evidence。
- ZBid preview scoring 不得作为 evidence。
- evidence 必须来自可验证资料锚点。
- preview 不得显示为正式正文。

该契约尚未在真实前端 UI 中落地展示。

## 9. Formal Chain Entry Control Confirmed

Step 165 tests 已固化正式链入口必须 blocked：

- DOCX export blocked。
- review/apply blocked。
- ZBid writeback blocked。
- formal writeback blocked。
- output write blocked。

并固化以下 UI 约束：

- DOCX export 入口必须 disabled、hidden 或 unavailable。
- review/apply 入口必须 disabled、hidden 或 unavailable。
- ZBid writeback 入口必须 disabled、hidden 或 unavailable。
- formal writeback 入口必须 disabled、hidden 或 unavailable。
- 禁用入口必须带原因说明。
- UI 不得触发 `/generate`、`/export_docx`、`/review/apply`、ZBid writeback、formal writeback 或 `output/job/export` 写入。

## 10. Formal Flags Confirmed

Step 165 tests 已固化五个正式链 flags 恒 false：

- `formal_writeback_allowed=false`
- `review_apply_allowed=false`
- `docx_export_allowed=false`
- `zbid_writeback_allowed=false`
- `output_write_allowed=false`

accepted preview、preview-only UI 或 fake contract accepted 状态均不得打开正式链权限。

## 11. Side Effect And Import Isolation Confirmed

Step 165 tests 已固化 no side effects：

- 不启动后端服务。
- 不启动前端服务。
- 不运行 Ollama。
- 不访问任何本地端口。
- 不调用网络。
- 不写 `output/job/export`。
- 不生成 DOCX。
- 不调用 ZBid。
- 不触发 `/generate`。
- 不触发 `/export_docx`。
- 不触发 `/review/apply`。
- 不进入本地化部署执行。
- 不进入 50 人团队正式部署设计。

Step 165 tests 还通过 AST import isolation 检查，测试文件不得导入或间接拉入：

- orchestrator
- llm_client
- provider
- generation
- export
- review
- actions_bridge
- zbid
- FastAPI
- requests
- httpx
- Ollama
- docx / python-docx

## 12. Explicit Non-Implemented Items

Step 165 没有实现以下事项：

- 未修复前端 UI。
- 未禁用“生成 Word 文档”入口。
- 未增加 preview-only 提示。
- 未增加 no-write 提示。
- 未增加 `blocked_reasons` 展示。
- 未增加 evidence 边界提示。
- 未做第三轮 smoke。
- 未启动后端服务。
- 未启动前端服务。
- 未运行 Ollama。
- 未访问端口。
- 未触发正式链 blocked runtime 检查。
- 未进入前端代码实现。

## 13. Risk Conclusion

当前风险结论：

- UI 风险仍存在。
- “生成 Word 文档”入口风险仍未修复。
- preview-only / no-write / `blocked_reasons` / evidence 边界提示仍未实际落地。
- Step 165 只证明契约已被 fake schema tests 固化，不证明真实 UI 已符合该契约。
- 后续必须单独授权进入前端代码修复或实现方案设计。

该风险不影响 Step 165 的 tests-only 目标，但会影响后续真实 local trial 的用户可理解性和误操作防护。

## 14. Recommended Next Step

建议下一步为：

ZDoc Step 167: frontend no-write UI implementation plan design, docs-only.

Step 167 应只设计前端 no-write UI 实施方案，不直接改代码。应明确“生成 Word 文档”入口如何禁用或替换、preview-only/no-write/`blocked_reasons`/evidence 文案如何展示、正式链入口如何保持 blocked，以及后续代码修改需要的单独授权。

## 15. Safety Conclusion

Step 165 已完成 frontend no-write UI risk contract fake schema tests，并通过限定测试组合。

当前系统仍处于 preview-only / no-write 阶段。前端 UI 风险已被契约和 fake schema tests 固化，但尚未实际修复。本文档不代表正式生成、DOCX 导出、review/apply、ZBid 写回、formal writeback、本地化部署或 50 人团队正式部署已经实现。
