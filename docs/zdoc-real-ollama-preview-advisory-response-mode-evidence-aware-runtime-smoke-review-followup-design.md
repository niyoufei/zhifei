# ZDoc response-mode / evidence-aware runtime smoke review follow-up design

## 1. 阶段背景

本阶段为 ZDoc Step 71：response-mode / evidence-aware runtime smoke review + follow-up design。

前序阶段事实如下：

* Step 67 已完成 response-mode / generated-preview-as-evidence guard fake-only implementation + deterministic tests；
* Step 68 已完成 fake-stage review；
* Step 69 已完成 runtime smoke plan refresh；
* Step 70 已完成 response-mode / evidence-aware runtime smoke + smoke report；
* Step 70 enabled payload 8/8 HTTP 200、8/8 `status=ok`、8/8 `calls_ollama=true`；
* RM-E / RM-F / RM-G generated-preview-as-evidence 相关场景均进入 blocked / `invalid_anchor`；
* 正式链准入字段全部恒为 false；
* 但 Step 70 仍显示 8/8 enabled payload 均为 `thinking_only_fallback`；
* adapter-off literal payload 触发受控字段校验失败 `illegal_field:content`；
* 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。

本步为 docs-only 复盘与后续设计步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 正式导出，不接 ZBid 正式写回。

## 2. Step 70 已证明的事实

Step 70 已证明：

* 本地 Ollama 可达；
* `qwen3:0.6b` 存在；
* enabled real runtime path 可触发；
* enabled 8/8 `status=ok`；
* enabled 8/8 `calls_ollama=true`；
* generated-preview-as-evidence 可被识别；
* RM-E / RM-F / RM-G 均被 blocked / `invalid_anchor`；
* `generated_content_must_not_be_evidence` 可追踪；
* `formal_generation_allowed` 恒 false；
* `shadow_candidate_allowed` 恒 false；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒 false；
* 未请求 `/generate`；
* 未请求 `/export_docx`；
* 未请求 `/review/apply`；
* 未直接请求 Ollama `/api/generate`；
* 未写 `output/job/export`；
* FastAPI 进程已停止；
* `18758` 端口已释放；
* 本步启动的 Ollama 已停止，`11434` 无监听。

需要特别说明：Step 70 smoke 客户端只请求 `/local-llm/preview-safe`。Ollama 日志中的 `/api/generate` 属于 safe endpoint real adapter 在本地 loopback 内部间接调用，不是 smoke 客户端直接请求。

## 3. Step 70 结果复盘

Step 70 摘要如下：

* disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，`preview_only/no_write=true`；
* adapter-off：HTTP 200，controlled `illegal_field:content`，`calls_ollama=false`，未构造 real runtime path；
* enabled 8/8 HTTP 200，8/8 `status=ok`，8/8 `calls_ollama=true`；
* RM-A：`thinking_only_fallback` / `review_required` / `not_required`；
* RM-B：`thinking_only_fallback` / `review_required` / `not_required`；
* RM-C：`thinking_only_fallback` / `review_required` / `not_required`；
* RM-D：`thinking_only_fallback` / `review_required` / `not_required`；
* RM-E：`thinking_only_fallback` / blocked / `invalid_anchor`；
* RM-F：`thinking_only_fallback` / blocked / `invalid_anchor`；
* RM-G：`thinking_only_fallback` / blocked / `invalid_anchor`；
* RM-H：`thinking_only_fallback` / `review_required` / `missing`；
* response_mode 统计：0 / 0 / 0 / 8 / 0 / 0 / 0 / 0；
* `generated_preview_as_evidence_detected` 次数 = 3；
* `generated_content_evidence_blocked` 次数 = 3；
* `invalid_anchor` 次数 = 3；
* thinking fallback 出现次数 = 8；
* 正式链准入字段全 false。

response_mode 统计顺序为：

```text
response_advisory / json_advisory / text_fallback / thinking_only_fallback / empty_response / malformed_response / normalization_failure / system_error
```

即：

```text
0 / 0 / 0 / 8 / 0 / 0 / 0 / 0
```

## 4. 关键进展判断

Step 70 已证明 response-mode / evidence-aware runtime smoke 受控。enabled real runtime 请求均受控返回，generated-preview-as-evidence guard 在真实 runtime 下初步有效，formal chain isolation 稳定，no-write / preview-only 边界稳定。

同时，Step 70 也暴露了一个关键后续缺口：`response_advisory` / `json_advisory` / `text_fallback` 在真实 runtime 下尚未出现，`thinking_only_fallback` 仍为真实 runtime 主路径。

该结果支持继续做 response-mode follow-up 与 prompt/output-options 设计，但不支持进入 shadow generation 或正式生成链。

## 5. response-mode 高依赖缺口复述

缺口名称：runtime response-mode high dependency on `thinking_only_fallback`。

缺口性质：

* 不是 transport 不通；
* 不是 generated-preview-as-evidence guard 失效；
* 不是 evidence anchor metadata 缺失；
* 而是真实 runtime 所有 enabled payload 仍依赖 `thinking_only_fallback`；
* 普通 response / JSON response / text fallback 在 runtime 下未证明；
* 这会影响后续 advisory 质量、可解释性、shadow generation 准入和 evidence trace 稳定性。

因此，后续不能只看 HTTP 200、`status=ok`、advisory 是否存在，必须把 `response_mode`、`response_source`、`fallback_reason`、`thinking_fallback_detected` 纳入准入判断。

## 6. thinking_only_fallback 风险分析

`thinking_only_fallback` 的风险如下：

* thinking fallback 可能偏推理过程，不应作为正式建议来源；
* thinking fallback 高频说明 prompt 或 model options 可能仍需优化；
* thinking fallback 不应进入 candidate patch；
* thinking fallback 不应进入正式正文；
* thinking fallback 不应触发 DOCX 导出；
* thinking fallback 不应写回 ZBid；
* thinking fallback + `status=ok` 不等于质量合格；
* thinking fallback + `evidence_anchor_status=not_required` 不等于无需审核。

当前阶段应继续把 `thinking_only_fallback` 视为 preview-only fallback。即使 quality gate 返回 `review_required` 而非 blocked，也不得将其解释为 shadow candidate 或正式正文来源。

## 7. adapter-off illegal_field:content 复盘

Step 70 adapter-off 场景返回 HTTP 200，但出现 controlled `illegal_field:content`。

该结果说明：

* 字段校验受控；
* 未触发 real runtime；
* `calls_ollama=false`；
* 未写盘；
* 未触发正式生成链、导出链或 ZBid 写回链。

该结果不是正式链风险，但说明 adapter-off 与 enabled payload 字段兼容性需后续复盘。只读代码检查显示 enabled/fake-only safe endpoint 允许字段为 `context_summary`、`request_id`、`section_text`、`section_title`。Step 70 adapter-off 场景使用用户 literal payload，包含 `content` 字段，因此进入非法字段路径。

后续应考虑统一 smoke payload schema，避免 adapter-off 因 literal `content` 字段进入非法字段路径。该建议仅为 docs-only 后续设计，本步不得修改代码。

## 8. generated-preview-as-evidence 复盘

Step 70 中 RM-E / RM-F / RM-G 已触发 generated-preview-as-evidence guard：

* `generated_preview_as_evidence_detected=3`；
* `generated_content_evidence_blocked=3`；
* `invalid_anchor=3`；
* RM-E / RM-F / RM-G 均为 blocked / `invalid_anchor`；
* `invalid_anchor_reason=generated_preview_as_evidence`；
* generated preview 未被当作 tender / drawing / boq / scoring evidence；
* generated preview + formal chain request 已 blocked。

该门禁在真实 runtime 下初步有效。相比 Step 64 中 EA-G 的 `evidence_anchor_status=not_required` 边界偏弱问题，Step 70 已显示 Step 67 后的 guard 能把 generated-preview-as-evidence 风险映射到更强的 `invalid_anchor` / blocked 路径。

但该结论仍是本轮 payload 下的初步 runtime 观察，仍需后续 smoke 复盘和更多 payload 验证，尤其是更隐蔽的“模型依据显示”“AI 建议可作为证据”“候选补丁依赖模型建议”等变体。

## 9. 后续 response-mode 优化方向设计

后续可从 docs-only 角度设计以下方向，本步不实现：

* response-first prompt 设计；
* JSON-first prompt 设计；
* short response mode prompt；
* 降低 thinking fallback 的 options 设计；
* 调整 `num_predict` / `temperature` / `stop` 等参数的计划；
* 增加 response_mode runtime distribution smoke；
* 比较 `qwen3:0.6b` 与更强本地模型的 response-mode 稳定性；
* 明确 thinking fallback 不得进入 `shadow_candidate`；
* 正式链前要求至少一个稳定非 thinking response 模式。

后续 prompt/output-options 设计应优先解决两个问题：

* 让模型把可展示 advisory 写入普通 response 或结构化 JSON response；
* 保持 no-write / preview-only / evidence safety / formal chain isolation 不被 prompt 优化破坏。

## 10. 后续 generated-preview-as-evidence 设计方向

后续可继续强化 generated-preview-as-evidence guard：

* 继续保留 `generated_content_must_not_be_evidence`；
* 将 generated preview as evidence 统一映射为 `invalid_anchor` 或 blocked；
* 对 suggestion source 与 evidence source 做字段隔离；
* 对 generated preview + formal chain request 继续 P0/P4 blocked；
* 后续 deterministic tests 与 runtime smoke 继续覆盖；
* 不得将 model-generated advisory 作为 evidence anchor。

后续数据契约应继续区分：

* generated preview 作为 suggestion source；
* tender / drawing / boq / scoring / standard 等外部事实证据来源；
* human approval；
* candidate patch；
* final formal document。

generated preview 可以用于 preview advisory，但不能成为事实证据、正式正文证据或 ZBid scoring basis。

## 11. 后续 runtime smoke 建议

当前不应直接进入 shadow generation。后续应优先考虑：

* response-mode prompt tuning plan；
* response-mode deterministic tests design；
* response-mode runtime smoke refresh；
* model comparison plan；
* evidence-aware smoke review；
* generated-preview-as-evidence regression smoke；
* 再讨论 shadow generation design。

若要继续 runtime smoke，应单独授权，并继续保持：

* 只请求 `/local-llm/preview-safe`；
* 不直接请求 Ollama `/api/generate`；
* 不请求 `/generate`、`/export_docx`、`/review/apply`；
* 不写 `output/job/export`；
* 不进入 shadow generation；
* 不进入正式生成链；
* 不进入 DOCX 导出或 ZBid 写回。

## 12. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 70 只证明 response-mode / evidence-aware runtime smoke 受控，不证明正式生成链可用。正式链前仍必须完成：

* response-mode 稳定性；
* evidence anchor 强化；
* shadow generation；
* candidate patch；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离。

在这些阶段完成前，即使 runtime smoke 受控，也不得将 preview advisory、thinking fallback、generated preview 或 `status=ok` 解释为正式链准入。

## 13. 风险与回滚

当前风险：

* 风险 1：thinking fallback 高依赖被误读为模型质量稳定；
* 风险 2：`status=ok` 被误认为正式链准入；
* 风险 3：adapter-off payload schema 差异被忽略；
* 风险 4：generated preview 被误认为 evidence；
* 风险 5：future shadow generation 缺少 response-mode 降级策略；
* 风险 6：DOCX / ZBid 写回时 evidence trace 丢失；
* 风险 7：prompt tuning 误破坏 no-write / preview-only。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

* 保留 disabled / adapter-off / fake-only 路径。

异常边界：

* 出现异常时不得扩大到正式链路；
* `thinking_only_fallback` 不得进入 shadow candidate；
* generated preview 不得作为 evidence；
* formal generation、writeback、export、ZBid writeback 必须继续 fail-closed。

## 14. 当前阶段结论

Step 70 已证明 response-mode / evidence-aware runtime smoke 受控，generated-preview-as-evidence guard 在真实 runtime 下初步有效，正式链准入字段恒 false；但 8/8 enabled payload 仍依赖 `thinking_only_fallback`，adapter-off payload schema 也出现 controlled `illegal_field:content`，普通 response / JSON response 稳定性仍未证明，因此不得进入 shadow generation 或正式生成链。

本阶段仅完成 docs-only runtime smoke 复盘与 follow-up design，未实现代码，未运行测试，未启动服务，未运行 Ollama，未进入 runtime smoke、shadow generation 或正式生成链。

## 15. 下一步建议

下一步建议为 ZDoc Step 72：response-mode prompt tuning design 或 response-mode runtime smoke follow-up plan，docs-only。

不得直接进入代码实现、runtime smoke、shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
