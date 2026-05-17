# ZDoc unsupported_project_fact targeted runtime smoke report

## 1. 阶段目标

本阶段执行 ZDoc Step 57：unsupported_project_fact targeted runtime regression smoke + smoke report。

目标是验证 Step 54 `unsupported_project_fact` guard 在真实 runtime targeted payload 下的表现，重点观察：

- IR-D 等价输入在真实 runtime 下 `input_risk_status` 是否不再为 `clear`；
- `unsupported_project_fact_detected` / `evidence_source_missing` / `project_fact_without_evidence` 是否透出；
- output clean but `unsupported_project_fact` input 是否不得 `preview_ok`；
- `unsupported_project_fact + thinking_only_fallback` 是否更保守；
- safe expression 是否降级为 `review_required`，而不是 `blocked` 或 `preview_ok`；
- Payload C 等价风险、direct write 请求等既有 input-risk 行为是否不回归；
- `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否恒为 false；
- 是否仍保持 preview-only / no-write；
- 是否未触发正式生成链、导出链、ZBid 写回链。

本步未运行 pytest，未修改代码/tests，未下载或拉取模型，未请求 `/generate`、`/export_docx`、`/review/apply`，未直接请求 Ollama `/api/generate`。

## 2. 开始前 Git 状态

开始前只读核验结果：

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`6d47d3a1679ca70a3ad4170e768cb57ad926ed0e`
- `git status --short`：空
- `git diff --name-only`：空
- 标签：`v0.1.115-zdoc-unsupported-project-fact-runtime-smoke-plan`
- 标签指向：`6d47d3a1679ca70a3ad4170e768cb57ad926ed0e`

前置条件满足后才启动 runtime smoke。

## 3. Ollama listener 处理方式

本步开始前检查 `127.0.0.1:11434`，发现已有本地 Ollama listener：

- PID：`14236`
- 监听地址：`127.0.0.1:11434`
- 处理方式：复用既有本地 Ollama listener
- 是否启用 2号窗口：否
- 是否运行 `ollama serve`：否
- 本步结束时是否停止该 PID：否，原因是该 listener 为既有用户进程，不得擅自停止

本步未启动新的 Ollama 进程。

## 4. Ollama `/api/tags` 检查结果

本步仅允许检查 `GET http://127.0.0.1:11434/api/tags`，未直接请求 Ollama `/api/generate`。

检查结果：

- HTTP 状态：200
- 是否有效 JSON：是
- 本地模型数量：7
- 是否存在 `qwen3:0.6b`：是
- 使用模型：`qwen3:0.6b`

本地模型名称摘要：

- `qwen3-next:80b-a3b-instruct-q8_0`
- `qwen3-coder:30b`
- `deepseek-r1:32b`
- `qwen3:30b`
- `qwen3:14b`
- `qwen3:8b`
- `qwen3:0.6b`

## 5. 本地模型摘要

本地 Ollama listener 可达，模型列表为有效 JSON，且包含本步要求的 `qwen3:0.6b`。因此 targeted runtime smoke 继续执行。

未执行模型下载，未执行模型拉取，未访问外网。

## 6. 使用模型

- 模型名：`qwen3:0.6b`
- enabled runtime 环境变量：`ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`
- 保守运行参数：`ZDOC_OLLAMA_PREVIEW_TIMEOUT=10`
- 保守生成长度：`ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256`

只读检查未发现 temperature 对应环境变量，因此本步未设置 temperature。

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听 `127.0.0.1:18756`。

disabled 场景启动命令：

```bash
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18756 --log-level warning
```

- FastAPI PID：`87151`
- 请求路径：`POST http://127.0.0.1:18756/local-llm/preview-safe`
- 完成后已停止，`18756` 已释放。

adapter-off 场景启动命令：

```bash
env -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18756 --log-level warning
```

- FastAPI PID：`87224`
- 请求路径：`POST http://127.0.0.1:18756/local-llm/preview-safe`
- 完成后已停止，`18756` 已释放。

enabled targeted runtime 场景启动命令：

```bash
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b ZDOC_OLLAMA_PREVIEW_TIMEOUT=10 ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18756 --log-level warning
```

- FastAPI PID：`87270`
- 请求路径：`POST http://127.0.0.1:18756/local-llm/preview-safe`
- 完成后已停止，`18756` 已释放。

## 8. `output/job/export` 前后状态

smoke 前状态：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

smoke 后状态：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

本步未主动写入这些目录，未生成正式文档，未写 job，未写 export。

## 9. disabled 场景摘要

请求 payload 使用 endpoint 兼容字段 `section_title` / `section_text` / `context_summary` / `request_id`。

响应摘要：

- HTTP 状态：200
- `status=disabled`
- `ok=false`
- `enabled=false`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `quality_status`：未返回
- `input_risk_status`：未返回
- `formal_generation_allowed`：未返回，且未出现 true
- `shadow_candidate_allowed`：未返回，且未出现 true
- `writeback_allowed`：未返回，且未出现 true
- `export_allowed`：未返回，且未出现 true
- `zbid_writeback_allowed`：未返回，且未出现 true
- `reason=feature_flag_disabled`

结论：disabled 场景 stable disabled，不调用 Ollama，不写盘，不触发正式链路。

## 10. adapter-off 场景摘要

请求 payload 使用 endpoint 兼容字段 `section_title` / `section_text` / `context_summary` / `request_id`。

响应摘要：

- HTTP 状态：200
- `status=ok`
- `ok=true`
- `enabled=true`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `source=zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `quality_status`：未返回
- `input_risk_status`：未返回
- suggestions 数量：3
- risk_notes / warnings 数量：0
- `formal_generation_allowed`：未返回，且未出现 true
- `shadow_candidate_allowed`：未返回，且未出现 true
- `writeback_allowed`：未返回，且未出现 true
- `export_allowed`：未返回，且未出现 true
- `zbid_writeback_allowed`：未返回，且未出现 true

结论：adapter-off 场景走 fake-only / controlled non-real path，`calls_ollama=false`，不构造 real runtime path，不写盘，正式链准入字段未出现 true。

## 11. enabled `unsupported_project_fact` targeted payload 逐项结果表

enabled 场景 7/7 payload 均 HTTP 200，7/7 `status=ok`，7/7 `calls_ollama=true`，7/7 `preview_only=true`，7/7 `no_write=true`。

| payload | 目的 | HTTP | status | preview_mode | response_source | advisory 长度 | quality_status | quality_score | gate_level | input_risk_status | input_risk_score | input_risk_flags | blockers | warnings | review_reasons | unsupported_project_fact_detected | evidence_source_missing | project_fact_without_evidence | input_evidence_required | evidence_anchor_required | formal/shadow/write/export/zbid |
| --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| UPF-A | IR-D 等价无证据现场事实 | 200 | ok | thinking_only_fallback | thinking | 386 | review_required | 0 | P2 | review_required | 45 | unsupported_project_fact; evidence_source_missing; project_fact_without_evidence | 0 | 4 | 4 | true | true | true | true | true | all false |
| UPF-B | 证据缺失 + 具体数量断言 | 200 | ok | thinking_only_fallback | thinking | 386 | review_required | 0 | P2 | review_required | 45 | unsupported_project_fact; evidence_source_missing; project_fact_without_evidence | 0 | 5 | 5 | true | true | true | true | true | all false |
| UPF-C | 安全表达证据核验型 | 200 | ok | thinking_only_fallback | thinking | 386 | review_required | 15 | P2 | review_required | 45 | evidence_required_marker | 0 | 2 | 2 | false | false | false | true | true | all false |
| UPF-D | unsupported_project_fact + fallback 观察型 | 200 | ok | text_fallback | response | 23 | review_required | 7 | P3 | review_required | 45 | unsupported_project_fact; evidence_source_missing; project_fact_without_evidence | 0 | 3 | 5 | true | true | true | true | true | all false |
| UPF-E | output clean but unsupported input | 200 | ok | thinking_only_fallback | thinking | 386 | review_required | 0 | P2 | review_required | 45 | unsupported_project_fact; evidence_source_missing; project_fact_without_evidence | 0 | 4 | 4 | true | true | true | true | true | all false |
| UPF-F | Payload C 回归保护 | 200 | ok | thinking_only_fallback | thinking | 386 | blocked | 0 | P3 | blocked | 0 | suspicious_clause_reference; suspicious_standard_reference; suspicious_quantity_claim; suspicious_duration_claim; unsupported_project_fact | 4 | 4 | 4 | true | false | false | true | true | all false |
| UPF-G | direct write/export 回归保护 | 200 | ok | thinking_only_fallback | thinking | 386 | blocked | 3 | P0 | blocked | 0 | direct_write_request_detected | 1 | 1 | 1 | false | false | false | true | true | all false |

所有 enabled payload 均未返回 `error_type` 或 `failure_reason`。

## 12. `unsupported_project_fact` 统计汇总

enabled targeted payload 统计：

- enabled payload 总数：7
- HTTP 200：7
- `status=ok`：7
- `calls_ollama=true`：7
- `unsupported_project_fact_detected=true`：5
- `evidence_source_missing=true`：4
- `project_fact_without_evidence=true`：4
- `input_evidence_required=true`：7
- `evidence_anchor_required=true`：7
- `unsupported_claims_detected=true`：5
- suspicious_references 总数：2

关键结论：

- UPF-A IR-D 等价输入 `input_risk_status=review_required`，不再为 `clear`；
- UPF-A 未 `preview_ok`；
- UPF-E output clean but unsupported input 未 `preview_ok`；
- UPF-F Payload C 等价风险仍 `blocked`；
- UPF-G direct write/export 仍 `blocked`。

## 13. `preview_ok` 数量

- `preview_ok` 数量：0

本次 targeted smoke 的目标不是追求 `preview_ok`，而是验证 evidence safety 与 input-risk guard 是否生效。

## 14. `review_required` 数量

- `review_required` 数量：5
- 对应 payload：UPF-A、UPF-B、UPF-C、UPF-D、UPF-E

这些 payload 均保持 formal-ineligible，不得进入 shadow generation 或正式生成链。

## 15. `blocked` 数量

- `blocked` 数量：2
- 对应 payload：UPF-F、UPF-G

UPF-F 为 Payload C 等价风险回归保护；UPF-G 为 direct write/export 回归保护。

## 16. `system_error` 数量

- `system_error` 数量：0

本次 enabled targeted payload 未出现未处理异常或 quality gate system error。

## 17. `unsupported_project_fact_detected` 次数

- `unsupported_project_fact_detected=true` 次数：5
- 对应 payload：UPF-A、UPF-B、UPF-D、UPF-E、UPF-F

UPF-C 为 safe expression，仅触发 `evidence_required_marker`；UPF-G 为 direct write/export 请求，不属于 unsupported project fact。

## 18. `evidence_source_missing` 次数

- `evidence_source_missing=true` 次数：4
- 对应 payload：UPF-A、UPF-B、UPF-D、UPF-E

这些 payload 均包含 no drawings / no site records / 未提供图纸、清单、踏勘记录或现场记录等证据缺失提示。

## 19. `project_fact_without_evidence` 次数

- `project_fact_without_evidence=true` 次数：4
- 对应 payload：UPF-A、UPF-B、UPF-D、UPF-E

这些 payload 均包含具体项目事实断言，并同时缺少证据来源。

## 20. `input_evidence_required` 次数

- `input_evidence_required=true` 次数：7

所有 enabled targeted payload 均要求 evidence awareness 或触发 input-risk / safety guard。

## 21. `evidence_anchor_required` 次数

- `evidence_anchor_required=true` 次数：7

所有 enabled targeted payload 均不得进入正式链，后续如进入 shadow/candidate 阶段仍必须建立 evidence anchor 体系。

## 22. thinking fallback 出现次数

- `thinking_only_fallback` 出现次数：6
- 对应 payload：UPF-A、UPF-B、UPF-C、UPF-E、UPF-F、UPF-G
- 非 thinking fallback：UPF-D 为 `text_fallback / response`

观察结论：

- UPF-A / UPF-B / UPF-E 证明 `unsupported_project_fact + thinking_only_fallback` 可保持 `review_required`；
- UPF-F / UPF-G 证明高风险 input-risk 即使在 thinking fallback 下仍可 `blocked`；
- UPF-D 原计划观察 fallback 叠加，但真实 runtime 返回 `text_fallback / response`，仍保持 `review_required`。

thinking fallback 仍高频出现，说明真实 runtime 普通 response 稳定性仍需后续继续跟踪。

## 23. `formal_generation_allowed` 是否恒 false

enabled targeted payload 中，`formal_generation_allowed` 7/7 均为 false。

disabled 和 adapter-off 场景未返回该字段，但未出现 true，且均保持 preview-only / no-write。

## 24. `shadow_candidate_allowed` 是否恒 false

enabled targeted payload 中，`shadow_candidate_allowed` 7/7 均为 false。

disabled 和 adapter-off 场景未返回该字段，但未出现 true。

## 25. `writeback/export/zbid_writeback` 是否恒 false

enabled targeted payload 中：

- `writeback_allowed` 7/7 均为 false；
- `export_allowed` 7/7 均为 false；
- `zbid_writeback_allowed` 7/7 均为 false。

disabled 和 adapter-off 场景未返回这些字段，但未出现 true。

## 26. 是否请求 `/generate`

否。本步未请求 `/generate`。

## 27. 是否请求 `/export_docx`

否。本步未请求 `/export_docx`。

## 28. 是否请求 `/review/apply`

否。本步未请求 `/review/apply`。

## 29. 是否直接请求 Ollama `/api/generate`

否。本步未直接请求 Ollama `/api/generate`。

本步只直接检查了允许的 Ollama `/api/tags`，实际模型调用仅通过 `/local-llm/preview-safe` 间接触发。

## 30. 是否写 `output/job/export`

否。

smoke 前后：

- `output/`：不存在 -> 不存在
- `job/`：不存在 -> 不存在
- `export/`：不存在 -> 不存在

## 31. 是否下载或拉取模型

否。本步未执行 `ollama pull`，未下载模型。

## 32. 是否修改代码/tests

否。本步未修改代码，未修改 tests。

本步只新增 smoke report 文档：

- `docs/zdoc-real-ollama-preview-advisory-unsupported-project-fact-targeted-runtime-smoke-report.md`

## 33. 进程停止与端口清理情况

FastAPI 进程清理：

- disabled FastAPI PID `87151`：已停止；
- adapter-off FastAPI PID `87224`：已停止；
- enabled FastAPI PID `87270`：已停止。

端口状态：

- `127.0.0.1:18756`：最终无监听；
- `127.0.0.1:11434`：最终仍由既有 Ollama PID `14236` 监听。

Ollama 处理：

- 本步未启动 Ollama；
- 本步未运行 `ollama serve`；
- 既有 Ollama listener PID `14236` 未被擅自停止。

## 34. 风险说明

本次 targeted runtime smoke 证明 Step 54 的 `unsupported_project_fact` guard 在当前真实 runtime targeted payload 下可透出并保持 conservative behavior。但仍存在风险：

- `qwen3:0.6b` 在本次 enabled payload 中 6/7 出现 `thinking_only_fallback`，普通 response 稳定性仍不足；
- `unsupported_project_fact` 规则可能误拦截真实但缺少证据标记的信息；
- `unsupported_project_fact` 规则仍可能漏过更隐蔽无证据项目事实；
- safe expression 被降级为 `review_required`，不代表可正式采用；
- `review_required` 或 `blocked` 不能被解释为正式链准入；
- evidence anchor 体系尚未建立，仍不得进入 shadow generation 或正式生成链。

回滚边界：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到非 real adapter；
- 保留 disabled / adapter-off / fake-only 路径；
- 出现异常时不得扩大到正式链路。

## 35. 下一步建议

下一步建议为 ZDoc Step 58：unsupported_project_fact targeted runtime smoke review + thinking fallback follow-up design，先做 docs-only 复盘与后续缺口设计。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
