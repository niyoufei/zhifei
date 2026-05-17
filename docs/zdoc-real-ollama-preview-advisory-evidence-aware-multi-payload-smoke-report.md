# ZDoc evidence-aware multi-payload smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 64：evidence-aware multi-payload runtime smoke + smoke report。

目标是在 Step 61 evidence anchor fake-only implementation 之后，通过本地 loopback FastAPI `/local-llm/preview-safe` 间接调用本地 Ollama，验证真实 runtime 多 payload 下 evidence anchor metadata 是否稳定返回。重点观察：

- `evidence_anchor_required` / `evidence_anchor_status` / `evidence_missing_reasons` 是否可追踪；
- unsupported_project_fact 与 evidence anchor 是否联动；
- thinking fallback + factual claim 是否触发 `evidence_anchor_required`；
- model-generated preview 是否不会被当作 evidence；
- DOCX / ZBid / candidate patch 防护字段是否稳定；
- `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否恒为 false；
- 是否保持 preview-only / no-write；
- 是否未触发正式生成链、导出链、ZBid 写回链。

本阶段未直接请求 Ollama `/api/generate`，只通过 `/local-llm/preview-safe` 间接验证。

## 2. 开始前 Git 状态

开始前只读核验结果：

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`1fbd804cacf7760632314decd20fa294d38b5200`
- `git status --short`：空
- `git diff --name-only`：空
- 标签：`v0.1.122-zdoc-evidence-aware-multi-payload-smoke-plan`
- 标签指向：`1fbd804cacf7760632314decd20fa294d38b5200`

前置条件满足后才继续执行 runtime smoke。

## 3. Ollama listener 处理方式

开始前检查 `127.0.0.1:11434`，发现已有本地 Ollama listener：

- 处理方式：复用既有 listener
- 既有 PID：`14236`
- 监听地址：`127.0.0.1:11434`
- 本步未重复启动 `ollama serve`
- 本步结束时未擅自停止该既有 PID

本步未启用 2号窗口。

## 4. Ollama /api/tags 检查结果

按 Step 64 允许范围，仅检查：

`GET http://127.0.0.1:11434/api/tags`

结果：

- HTTP 状态：`200`
- 是否有效 JSON：是
- 本地模型数量：`7`
- 是否存在 `qwen3:0.6b`：是
- 使用模型：`qwen3:0.6b`

未请求 Ollama `/api/generate`。

## 5. 本地模型摘要

`/api/tags` 返回的本地模型包括：

- `qwen3-next:80b-a3b-instruct-q8_0`
- `qwen3-coder:30b`
- `deepseek-r1:32b`
- `qwen3:30b`
- `qwen3:14b`
- `qwen3:8b`
- `qwen3:0.6b`

本次 smoke 使用已存在的 `qwen3:0.6b`，未下载或拉取模型。

## 6. 使用模型

enabled evidence-aware 场景使用：

- `ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`
- `ZDOC_OLLAMA_PREVIEW_TIMEOUT=20`
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128`

host 仅使用 loopback。未访问外网。

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听 `127.0.0.1:18757`。

disabled 场景：

```bash
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18757 --log-level warning
```

- PID：`8189`
- 请求完成后已停止

adapter-off 场景：

```bash
env -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18757 --log-level warning
```

- PID：`8242`
- 请求完成后已停止
- 备注：首次 adapter-off 启动命令因 `env` 参数顺序错误立即退出，未形成监听、未发起请求、未产生写入；随后用上述命令重新启动。

enabled evidence-aware 场景：

```bash
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b ZDOC_OLLAMA_PREVIEW_TIMEOUT=20 ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18757 --log-level warning
```

- PID：`8281`
- 请求完成后已停止

## 8. output/job/export 前后状态

smoke 前：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

smoke 后：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

本步未主动写入这些目录，也未发现新增写入。

## 9. disabled 场景摘要

请求：

- endpoint：`POST http://127.0.0.1:18757/local-llm/preview-safe`
- payload：`evidence-aware-disabled`

结果：

- HTTP 状态：`200`
- `status=disabled`
- `ok=false`
- `enabled=false`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `error_type=null`

disabled 响应未透出 `quality_status`、`input_risk_status`、`evidence_anchor_status` 或正式链准入字段；未出现任何正式链准入字段为 true 的情况。

## 10. adapter-off 场景摘要

请求：

- endpoint：`POST http://127.0.0.1:18757/local-llm/preview-safe`
- payload：`evidence-aware-adapter-off`

结果：

- HTTP 状态：`200`
- `status=ok`
- `ok=true`
- `enabled=true`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `model=fake-local-llm`
- `source=zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `error_type=null`

adapter-off 仍为 fake-only / controlled non-real path，不构造 real runtime path，不写盘。该响应未透出 `quality_status`、`input_risk_status`、`evidence_anchor_status` 或正式链准入字段；未出现任何正式链准入字段为 true 的情况。

## 11. enabled evidence-aware payload 逐项结果表

所有 enabled payload 均请求：

`POST http://127.0.0.1:18757/local-llm/preview-safe`

全部结果：

- 8/8 HTTP 200
- 8/8 `status=ok`
- 8/8 `calls_ollama=true`
- 8/8 `preview_only=true`
- 8/8 `no_write=true`
- 8/8 `affects_generation=false`
- 8/8 `affects_export=false`
- 8/8 `formal_generation_allowed=false`
- 8/8 `shadow_candidate_allowed=false`
- 8/8 `writeback_allowed=false`
- 8/8 `export_allowed=false`
- 8/8 `zbid_writeback_allowed=false`

| Payload | 目的 | HTTP | status | calls_ollama | quality_status | quality_score | gate_level | input_risk_status | evidence_anchor_required | evidence_anchor_status | evidence_anchor_level | evidence_sources | evidence_missing_reasons | unsupported_claims | unsupported_project_facts | unverified_parameters | evidence_review_required | evidence_blocked | preview_mode | response_source |
| --- | --- | ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| EA-A | 低风险泛化建议型 | 200 | ok | true | review_required | 28 | P2 | clear | false | not_required | P4 | 0 | 0 | 0 | 0 | 0 | false | false | thinking_only_fallback | thinking |
| EA-B | 无证据项目事实型 | 200 | ok | true | review_required | 0 | P2 | review_required | true | missing | P3 | 0 | 1 | 0 | 4 | 5 | true | false | thinking_only_fallback | thinking |
| EA-C | 规范编号 / 标准依据风险型 | 200 | ok | true | blocked | 0 | P3 | blocked | true | invalid_anchor | P0 | 0 | 1 | 2 | 0 | 3 | false | true | thinking_only_fallback | thinking |
| EA-D | 招标条款 / 评分项风险型 | 200 | ok | true | blocked | 0 | P3 | blocked | true | invalid_anchor | P0 | 0 | 1 | 2 | 4 | 4 | false | true | thinking_only_fallback | thinking |
| EA-E | 安全表达证据核验型 | 200 | ok | true | review_required | 2 | P2 | review_required | true | missing | P3 | 0 | 1 | 0 | 0 | 2 | true | false | thinking_only_fallback | thinking |
| EA-F | thinking fallback + factual claim 型 | 200 | ok | true | review_required | 0 | P2 | review_required | true | missing | P3 | 0 | 1 | 0 | 4 | 5 | true | false | thinking_only_fallback | thinking |
| EA-G | model-generated preview as evidence 风险型 | 200 | ok | true | review_required | 15 | P2 | review_required | false | not_required | P4 | 0 | 0 | 0 | 0 | 0 | false | false | thinking_only_fallback | thinking |
| EA-H | DOCX / ZBid / candidate patch 防护型 | 200 | ok | true | blocked | 0 | P0 | blocked | true | invalid_anchor | P0 | 0 | 1 | 2 | 0 | 0 | false | true | thinking_only_fallback | thinking |

各 payload 均有 advisory 摘要返回，advisory 长度约 385 至 386 字符，suggestions 数量均为 1。报告未保存完整模型长输出。

## 12. evidence anchor 统计汇总

enabled evidence-aware payload 统计：

- payload 总数：`8`
- `evidence_anchor_required=true`：`6`
- `evidence_review_required=true`：`3`
- `evidence_blocked=true`：`3`
- `generated_content_must_not_be_evidence=true`：`8`
- `trace_id` 存在：`8`
- `evidence_sources` 数量总计：`0`
- `evidence_missing_reasons` 数量总计：`6`
- `unsupported_claims` 数量总计：`8`
- `unsupported_project_facts` 数量总计：`12`
- `unverified_parameters` 数量总计：`19`

关键观察：

- EA-B / EA-F 的 unsupported_project_fact 与 evidence anchor 联动，状态为 `missing`，并触发 `evidence_review_required=true`。
- EA-C / EA-D 的异常规范编号、条款和评分项风险进入 `invalid_anchor` 且 blocked。
- EA-H 的 DOCX / ZBid / candidate patch 风险进入 `invalid_anchor` 且 blocked。
- EA-G 未把 model-generated preview 当作 evidence，`generated_content_must_not_be_evidence=true`；但 evidence anchor 状态为 `not_required`，质量门禁为 `review_required`，该分类仍建议后续复盘。

## 13. preview_ok / review_required / blocked / system_error 统计

enabled payload 的 `quality_status` 统计：

- `preview_ok`：`0`
- `review_required`：`5`
- `blocked`：`3`
- `system_error`：`0`

无 payload 被 preview_ok。所有请求均受控返回，未出现未处理异常。

## 14. anchored / partially_anchored / missing / conflicting / unverified / not_required / invalid_anchor / system_error 统计

enabled payload 的 `evidence_anchor_status` 统计：

- `anchored`：`0`
- `partially_anchored`：`0`
- `missing`：`3`
- `conflicting`：`0`
- `unverified`：`0`
- `not_required`：`2`
- `invalid_anchor`：`3`
- `system_error`：`0`

未出现 missing evidence 被标记为 anchored 的情况。

## 15. evidence_anchor_required 次数

`evidence_anchor_required=true` 共 `6` 次：

- EA-B
- EA-C
- EA-D
- EA-E
- EA-F
- EA-H

EA-A 低风险泛化建议为 `not_required`。EA-G model-generated preview as evidence 风险未升级为 required，但通过 `quality_status=review_required` 与 `generated_content_must_not_be_evidence=true` 保持预览门禁；该点建议后续复盘是否需要更强 evidence anchor 状态。

## 16. evidence_review_required 次数

`evidence_review_required=true` 共 `3` 次：

- EA-B
- EA-E
- EA-F

这些 payload 均为 missing evidence / safe expression / factual claim 相关场景，均未 preview_ok，且正式链准入字段均为 false。

## 17. evidence_blocked 次数

`evidence_blocked=true` 共 `3` 次：

- EA-C
- EA-D
- EA-H

对应风险为异常规范编号、虚构条款/评分项、以及 DOCX / ZBid / candidate patch 防护。

## 18. generated_content_must_not_be_evidence 次数

`generated_content_must_not_be_evidence=true` 共 `8` 次。

所有 enabled payload 都明确标记：模型生成内容不得作为事实证据。未出现 system-generated preview 被当作事实 evidence 的情况。

## 19. thinking fallback 出现次数

`thinking_only_fallback` 出现 `8` 次。

所有 enabled payload 的 `preview_mode=thinking_only_fallback`，`response_source=thinking`。这说明 evidence-aware runtime smoke 受控，但当前 qwen3:0.6b 在该 prompt / runtime 组合下仍高度依赖 thinking fallback。

thinking fallback 不得进入 shadow_candidate，不得进入正式正文，不得触发 DOCX 导出或 ZBid 写回。

## 20. formal_generation_allowed 是否恒 false

enabled 8/8 payload 均为：

- `formal_generation_allowed=false`

disabled / adapter-off 响应未透出该字段，但未出现 true。

## 21. shadow_candidate_allowed 是否恒 false

enabled 8/8 payload 均为：

- `shadow_candidate_allowed=false`

disabled / adapter-off 响应未透出该字段，但未出现 true。

## 22. writeback/export/zbid_writeback 是否恒 false

enabled 8/8 payload 均为：

- `writeback_allowed=false`
- `export_allowed=false`
- `zbid_writeback_allowed=false`

disabled / adapter-off 响应未透出这些字段，但未出现 true。

## 23. 是否请求 /generate

否。未请求 `/generate`。

## 24. 是否请求 /export_docx

否。未请求 `/export_docx`。

## 25. 是否请求 /review/apply

否。未请求 `/review/apply`。

## 26. 是否直接请求 Ollama /api/generate

否。未直接请求 Ollama `/api/generate`。

本步只直接检查了允许的 `GET /api/tags`，enabled 场景只通过 `/local-llm/preview-safe` 间接验证。

## 27. 是否写 output/job/export

否。

smoke 前后 `output/`、`job/`、`export/` 均不存在，未发现写入。

## 28. 是否下载或拉取模型

否。未执行下载或 pull。

`qwen3:0.6b` 已存在，因此继续 smoke。

## 29. 是否修改代码/tests

否。

本步未修改代码，未修改 tests，未运行 pytest。

## 30. 进程停止与端口清理情况

FastAPI：

- disabled PID `8189`：已停止
- adapter-off PID `8242`：已停止
- enabled PID `8281`：已停止
- `127.0.0.1:18757`：结束后无监听

Ollama：

- 既有 PID `14236`：复用，未停止
- `127.0.0.1:11434`：结束后仍由既有 Ollama listener 监听

本步未留下 18757 服务进程。

## 31. 风险说明

- 风险 1：8/8 enabled payload 出现 `thinking_only_fallback`，普通 response 稳定性仍未证明。
- 风险 2：EA-G 未把 model-generated preview 当作 evidence，但 evidence anchor 状态为 `not_required`，后续可评估是否应升级为更强 evidence 状态。
- 风险 3：当前 evidence source 真实映射仍未接入，`evidence_sources` 均为 0。
- 风险 4：`review_required` 可能被误认为可正式采用，仍需 UI 和流程层继续隔离。
- 风险 5：`anchored` 未在本次 runtime payload 出现，真实招标文件、图纸、清单、踏勘资料锚定能力尚未验证。
- 风险 6：未来 shadow generation 如缺少 evidence trace，可能放大无证据事实或模型生成事实。
- 风险 7：DOCX / ZBid 写回前 evidence trace 仍未经过端到端验证。

## 32. 下一步建议

下一步建议为 ZDoc Step 65：evidence-aware multi-payload smoke review + response-mode follow-up design，先做 docs-only 复盘。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
