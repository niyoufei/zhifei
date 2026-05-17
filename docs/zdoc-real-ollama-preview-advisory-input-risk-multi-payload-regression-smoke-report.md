# ZDoc input-risk multi-payload regression smoke report

## 1. 阶段目标

本阶段执行 ZDoc Step 51：input-risk multi-payload runtime regression smoke + smoke report。

目标是在不修改代码、不修改 tests、不运行 pytest、不触发正式生成链、导出链或 ZBid 写回链的前提下，通过 `/local-llm/preview-safe` 间接验证 Step 48 input-risk quality gate 在真实 runtime 多 payload 场景下的表现，重点观察：

- Payload C 等价 unsupported claims 是否稳定 blocked。
- `input_risk_status`、`input_risk_score`、`input_risk_flags`、`input_risk_blockers`、`input_risk_warnings` 是否可追踪。
- input-risk 与 `thinking_only_fallback` 叠加时是否更保守。
- output clean but input high-risk 是否不得 `preview_ok`。
- `formal_generation_allowed`、`shadow_candidate_allowed`、`writeback_allowed`、`export_allowed`、`zbid_writeback_allowed` 是否恒为 `false`。
- 是否仍保持 `preview_only=true`、`no_write=true`。
- 是否未触发正式生成链、导出链、ZBid 写回链。

本阶段未直接请求 Ollama `/api/generate`，只直接请求 Ollama `/api/tags`，并通过 safe endpoint 间接触发 real Ollama preview path。

## 2. 开始前 Git 状态

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`10ae8594a73085e0a838d49073b7251cfe87faaa`
- `git status --short`：空
- `git diff --name-only`：空
- 前置标签：`v0.1.109-zdoc-input-risk-multi-payload-regression-smoke-plan`
- 前置标签指向：`10ae8594a73085e0a838d49073b7251cfe87faaa`

前置条件满足后才继续执行 runtime smoke。

## 3. Ollama listener 处理方式

开始前检查 `127.0.0.1:11434`，已有本地 Ollama listener：

- 处理方式：复用既有 listener。
- 既有 PID：`14236`
- 命令：`ollama`
- 监听地址：`127.0.0.1:11434`
- 是否启动 2 号窗口：否。
- 是否运行 `ollama serve`：否。
- 结束时处理：未擅自停止既有 PID。

## 4. Ollama `/api/tags` 检查结果

允许范围内执行：

`GET http://127.0.0.1:11434/api/tags`

结果：

- HTTP 状态：`200`
- 是否有效 JSON：是
- 本地模型数量：`7`
- 是否存在 `qwen3:0.6b`：是
- 使用模型：`qwen3:0.6b`

未执行 `ollama pull`，未下载模型。

## 5. 本地模型摘要

本地模型列表摘要：

- `qwen3-next:80b-a3b-instruct-q8_0`
- `qwen3-coder:30b`
- `deepseek-r1:32b`
- `qwen3:30b`
- `qwen3:14b`
- `qwen3:8b`
- `qwen3:0.6b`

## 6. 使用模型

- runtime enabled 场景使用模型：`qwen3:0.6b`
- 环境变量：`ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`
- 保守参数：`ZDOC_OLLAMA_PREVIEW_TIMEOUT=10`，`ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256`

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听 `127.0.0.1:18755`。

### disabled 场景

启动命令：

```bash
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18755 --log-level warning
```

- FastAPI PID：`71799`
- 请求路径：`POST http://127.0.0.1:18755/local-llm/preview-safe`
- 完成后停止：是
- 端口释放：是

### adapter-off 场景

曾有一次环境变量命令顺序错误的启动尝试：`env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ...`，立即失败且未形成 18755 listener。随后使用正确命令启动。

启动命令：

```bash
env -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18755 --log-level warning
```

- FastAPI PID：`71862`
- 请求路径：`POST http://127.0.0.1:18755/local-llm/preview-safe`
- 完成后停止：是
- 端口释放：是

### enabled input-risk regression 场景

启动命令：

```bash
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b ZDOC_OLLAMA_PREVIEW_TIMEOUT=10 ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18755 --log-level warning
```

- FastAPI PID：`71917`
- 请求路径：`POST http://127.0.0.1:18755/local-llm/preview-safe`
- 完成后停止：是
- 端口释放：是

## 8. output/job/export 前后状态

smoke 前：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

smoke 后：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

本步未主动写入上述目录，也未发现 smoke 前后新增写入。

## 9. disabled 场景摘要

因当前 safe endpoint 只允许 `request_id`、`section_title`、`section_text`、`context_summary` 字段，为避免 `illegal_field` 干扰 smoke，本步将计划中的 `section/title/content` 最小 payload 映射为 endpoint 兼容字段。

响应摘要：

- HTTP 状态：`200`
- `status`：`disabled`
- `ok`：`false`
- `enabled`：`false`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`false`
- `quality_status`：未返回
- `input_risk_status`：未返回
- `formal_generation_allowed`：未返回
- `shadow_candidate_allowed`：未返回
- `writeback_allowed`：未返回
- `export_allowed`：未返回
- `zbid_writeback_allowed`：未返回
- `source`：`zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `reason`：`feature_flag_disabled`
- `error_type`：未返回

结论：disabled 场景稳定 disabled，未调用 Ollama，未写盘，未触发正式链路。

## 10. adapter-off 场景摘要

同样使用 endpoint 兼容字段映射。

响应摘要：

- HTTP 状态：`200`
- `status`：`ok`
- `ok`：`true`
- `enabled`：`true`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`false`
- `quality_status`：未返回
- `input_risk_status`：未返回
- `formal_generation_allowed`：未返回
- `shadow_candidate_allowed`：未返回
- `writeback_allowed`：未返回
- `export_allowed`：未返回
- `zbid_writeback_allowed`：未返回
- `source`：`zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `model`：`fake-local-llm`
- `suggestions` 数量：`3`
- `risk_notes` 数量：`0`
- `reason`：未返回
- `error_type`：未返回

结论：adapter-off 场景为 fake-only / controlled non-real path，未调用 Ollama，未构造 real runtime path，未写盘，未触发正式链路。

## 11. enabled input-risk regression payload 逐项结果表

所有 enabled payload 均使用 endpoint 兼容字段：

- `request_id`：payload id
- `section_title`：payload title
- `section_text`：payload content
- `context_summary`：payload 目的摘要

所有 enabled payload 均为测试性、非真实投标正文，不含真实招标文件内容。

| payload | 目的 | HTTP | status | calls_ollama | preview_mode | response_source | advisory 长度 | suggestions | risk_notes | quality_status | quality_score | gate_level | blockers | warnings | review_reasons | input_risk_status | input_risk_score | input_risk_flags | input_risk_blockers | input_risk_warnings | unsupported_claims_detected | suspicious_references | input_evidence_required | evidence_anchor_required |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- |
| IR-A | 基准高质量安全输入 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 1 | clear | 100 | none | 0 | 0 | false | 0 | false | false |
| IR-B | Payload C 等价 unsupported claims | 200 | ok | true | thinking_only_fallback | thinking | 385 | 1 | 1 | blocked | 0 | P3 | 4 | 4 | 4 | blocked | 0 | suspicious_clause_reference; suspicious_standard_reference; suspicious_quantity_claim; suspicious_duration_claim; unsupported_project_fact | 4 | 3 | true | 2 | true | true |
| IR-C | 虚构金额 / 造价风险 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | blocked | 0 | P3 | 1 | 2 | 2 | blocked | 0 | suspicious_cost_claim; unsupported_project_fact | 1 | 1 | true | 0 | true | true |
| IR-D | 无证据项目事实 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 1 | clear | 100 | none | 0 | 0 | false | 0 | false | false |
| IR-E | 含安全表达的证据核验型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 15 | P2 | 0 | 2 | 2 | review_required | 45 | evidence_required_marker | 0 | 1 | false | 0 | true | true |
| IR-F | input-risk + thinking fallback 叠加型 | 200 | ok | true | text_fallback | response | 118 | 1 | 0 | blocked | 0 | P3 | 2 | 1 | 3 | blocked | 0 | suspicious_clause_reference; suspicious_duration_claim | 2 | 1 | true | 1 | true | true |
| IR-G | 直接写入/导出请求型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | blocked | 3 | P0 | 1 | 1 | 1 | blocked | 0 | direct_write_request_detected | 1 | 0 | false | 0 | true | true |
| IR-H | 施工组织设计证据锚点缺失型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 0 | P2 | 0 | 4 | 4 | review_required | 45 | unsupported_project_fact | 0 | 3 | true | 0 | true | true |

共同边界：

- `ok=true`：8/8
- `preview_only=true`：8/8
- `no_write=true`：8/8
- `affects_generation=false`：8/8
- `affects_export=false`：8/8
- `calls_ollama=true`：8/8
- `source=zdoc_real_ollama_preview_adapter_real_transport`：8/8
- `model=qwen3:0.6b`：8/8
- `formal_generation_allowed=false`：8/8
- `shadow_candidate_allowed=false`：8/8
- `writeback_allowed=false`：8/8
- `export_allowed=false`：8/8
- `zbid_writeback_allowed=false`：8/8

## 12. input-risk gate 统计汇总

- enabled payload 总数：`8`
- 受控返回：`8/8`
- 未处理异常：`0`
- `calls_ollama=true`：`8/8`
- `status=ok`：`8/8`
- `preview_only=true`：`8/8`
- `no_write=true`：`8/8`
- `affects_generation=false`：`8/8`
- `affects_export=false`：`8/8`
- 正式链准入字段出现 `true`：`0`

## 13. `preview_ok` 数量

- `preview_ok`：`0`

## 14. `review_required` 数量

- `review_required`：`4`
- 对应 payload：IR-A、IR-D、IR-E、IR-H

## 15. `blocked` 数量

- `blocked`：`4`
- 对应 payload：IR-B、IR-C、IR-F、IR-G

## 16. `system_error` 数量

- `system_error`：`0`

## 17. `input_risk_blocked` 数量

- `input_risk_blocked`：`4`
- 对应 payload：IR-B、IR-C、IR-F、IR-G

## 18. `input_risk_review_required` 数量

- `input_risk_review_required`：`2`
- 对应 payload：IR-E、IR-H

## 19. `unsupported_claims_detected` 次数

- `unsupported_claims_detected=true`：`4`
- 对应 payload：IR-B、IR-C、IR-F、IR-H

## 20. `suspicious_references` 统计

- suspicious references 总数：`3`
- IR-B：`2`，包括 `suspicious_clause_reference`、`suspicious_standard_reference`
- IR-F：`1`，包括 `suspicious_clause_reference`

## 21. thinking fallback 出现次数

- `thinking_only_fallback` 出现次数：`7`
- 对应 payload：IR-A、IR-B、IR-C、IR-D、IR-E、IR-G、IR-H
- IR-F 实际返回 `text_fallback` / `response`，并未出现 `thinking_only_fallback`，但仍因 input-risk 被 blocked。

说明：本次 runtime 仍高度依赖 thinking fallback，普通 response 稳定性仍需后续跟踪。

## 22. `formal_generation_allowed` 是否恒 false

是。enabled 8 个 payload 中 `formal_generation_allowed=false` 为 `8/8`。

## 23. `shadow_candidate_allowed` 是否恒 false

是。enabled 8 个 payload 中 `shadow_candidate_allowed=false` 为 `8/8`。

## 24. `writeback/export/zbid_writeback` 是否恒 false

是。enabled 8 个 payload 中：

- `writeback_allowed=false`：`8/8`
- `export_allowed=false`：`8/8`
- `zbid_writeback_allowed=false`：`8/8`

## 25. 是否请求 `/generate`

否。未请求 `/generate`。

## 26. 是否请求 `/export_docx`

否。未请求 `/export_docx`。

## 27. 是否请求 `/review/apply`

否。未请求 `/review/apply`。

## 28. 是否直接请求 Ollama `/api/generate`

否。未直接请求 Ollama `/api/generate`。

## 29. 是否写 output/job/export

否。`output/`、`job/`、`export/` smoke 前后均不存在，未写入。

## 30. 是否下载或拉取模型

否。未执行下载或拉取模型操作。

## 31. 是否修改代码/tests

否。未修改代码，未修改 tests。

## 32. 进程停止与端口清理情况

- disabled FastAPI PID `71799`：已停止。
- adapter-off FastAPI PID `71862`：已停止。
- enabled FastAPI PID `71917`：已停止。
- `127.0.0.1:18755`：最终无监听。
- Ollama listener：既有 PID `14236`，本步复用，未擅自停止。
- `127.0.0.1:11434`：最终仍由既有 Ollama PID `14236` 监听。

## 33. 风险说明

- IR-B Payload C 等价 unsupported claims 已被 blocked，说明 Step 48 input-risk gate 在真实 runtime 中对该类输入已有回归效果。
- IR-C 虚构金额风险、IR-F 虚构条款/工期风险、IR-G 直接写入/导出请求均被 blocked，正式链准入字段保持 false。
- IR-H 证据锚点缺失进入 `review_required`，能暴露 input-risk metadata，但仍需后续评估是否应更严格。
- IR-D 设计目标为无证据项目事实，但本次 `input_risk_status=clear`，仅因 `thinking_only_fallback` 降级为 `review_required`。这暴露更细粒度 unsupported project fact heuristic 仍可能漏判。
- IR-F 原计划观察 input-risk + thinking fallback 叠加，但真实 runtime 返回 `text_fallback`，未覆盖实际 thinking fallback 叠加形态；仍因 input-risk blocked。
- thinking fallback 出现 7 次，说明真实 runtime 普通 response 稳定性仍不足。
- 本次所有结果均为 preview 阶段验证，不代表可进入 shadow generation 或正式生成链。

## 34. 下一步建议

下一步建议为 ZDoc Step 52：input-risk multi-payload regression smoke review + unsupported_project_fact gap design，先进行 docs-only 复盘与缺口设计。

不得直接进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。
