# ZDoc multi-payload preview quality smoke review and input-risk quality gate gap design

## 1. 阶段背景

本阶段执行 ZDoc Step 46：multi-payload preview quality smoke review + input-risk quality gate gap design。

前序阶段事实如下：

- Step 42 已完成 preview advisory quality gate fake-only implementation + deterministic tests；
- Step 43 已完成 quality gate fake-stage review；
- Step 44 已完成 multi-payload preview quality smoke plan；
- Step 45 已完成 multi-payload preview quality smoke + smoke report；
- Step 45 enabled multi-payload 6/6 受控返回，均 `status=ok`、`calls_ollama=true`；
- Step 45 正式链准入字段均恒为 false；
- Step 45 未触发正式生成链、导出链或 ZBid 写回；
- 但 Step 45 中 4/6 payload 仍依赖 `thinking_only_fallback`；
- Payload C 虚构风险诱发型仅为 `review_required`，未被 `blocked`；
- 当前不得进入 shadow generation 或正式生成链。

本步为 docs-only 复盘与缺口设计步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型。

## 2. Step 45 已证明的事实

Step 45 已证明以下事实：

- Ollama listener 可达；
- `GET http://127.0.0.1:11434/api/tags` 返回 HTTP 200；
- `/api/tags` 返回有效 JSON；
- 本地模型包含 `qwen3:0.6b`；
- safe endpoint multi-payload runtime 可受控返回；
- 6 个 enabled payload 均 `status=ok`；
- 6 个 enabled payload 均 `calls_ollama=true`；
- 6 个 enabled payload 均进入 real transport path；
- quality gate metadata 可返回；
- `quality_status`、`quality_score`、`gate_level`、`warnings`、`review_reasons` 可追踪；
- `formal_generation_allowed` 恒为 false；
- `shadow_candidate_allowed` 恒为 false；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 恒为 false；
- 未请求 `/generate`；
- 未请求 `/export_docx`；
- 未请求 `/review/apply`；
- 未直接请求 Ollama `/api/generate`；
- 未写 `output/job/export`；
- FastAPI 进程已停止；
- `127.0.0.1:18754` 端口已释放；
- 既有 Ollama listener 未被擅自停止。

这些事实说明 preview-only real runtime + quality gate metadata 链路已能在多 payload smoke 下受控运行，但不说明 advisory 质量已经稳定，也不说明可以进入 shadow generation 或正式链。

## 3. Step 45 尚未证明的事项

Step 45 尚未证明以下事项：

- 尚未证明多 payload 下普通 `response` 稳定优于 thinking fallback；
- 尚未证明结构化 JSON advisory 在真实 runtime 下稳定；
- 尚未证明 quality gate 能充分识别输入侧高风险内容；
- 尚未证明 Payload C 这类虚构风险诱发输入应被 `blocked`；
- 尚未证明真实技术标内容的质量评分稳定；
- 尚未证明多模型 payload 稳定；
- 尚未证明多长度 payload 稳定；
- 尚未证明多章节 payload 稳定；
- 尚未证明真实招标依据、图纸依据、清单依据能够被证据锚点安全约束；
- 尚未进入 shadow generation；
- 尚未进入 candidate patch；
- 尚未进入人工确认写回；
- 尚未进入 DOCX 导出一致性校核；
- 尚未进入 ZBid 写回隔离。

因此，Step 45 不能被解释为正式生成链已具备接入条件。

## 4. multi-payload 结果复盘

Step 45 摘要如下：

- disabled：HTTP 200，`status=disabled`，`calls_ollama=false`，`preview_only=true`，`no_write=true`；
- adapter-off：HTTP 200，fake-only `status=ok`，`calls_ollama=false`；
- enabled multi-payload：6/6 受控返回；
- Payload A：`preview_ok` / `76` / `P4`；
- Payload B：`review_required` / `28` / `P2`；
- Payload C：`review_required` / `28` / `P2`；
- Payload D：`review_required` / `28` / `P2`；
- Payload E：`review_required` / `28` / `P2`；
- Payload F：`review_required` / `46` / `P3`；
- `preview_ok / review_required / blocked / system_error = 1 / 5 / 0 / 0`；
- thinking fallback 出现 4 次；
- enabled payload 的 `formal_generation_allowed` 全为 false；
- enabled payload 的 `shadow_candidate_allowed` 全为 false；
- enabled payload 的 `writeback_allowed / export_allowed / zbid_writeback_allowed` 全为 false。

逐项复盘：

- Payload A 高质量技术标建议型返回 `preview_ok`，说明当前 quality gate 在真实 runtime 普通 text fallback 场景下可给出可展示 preview 状态；
- Payload B 泛泛模板话风险型返回 `review_required`，并因 thinking fallback 被降级；
- Payload C 虚构风险诱发型返回 `review_required`，但没有形成 input-risk blocker；
- Payload D thinking fallback 观察型返回 `review_required`，符合 fallback 降级预期；
- Payload E 极简输入型返回 `review_required`，未误判为高质量；
- Payload F 施工组织设计专项型返回 `review_required`，提示技术标专项具体性仍不足。

## 5. 新缺口定义

缺口名称：`input-risk quality gate gap`

缺口性质：

- 不是 transport 不通；
- 不是 Ollama 不可达；
- 不是模型不存在；
- 不是 normalization failure；
- 不是 quality gate 未返回；
- 不是正式链准入字段失控；
- 而是 quality gate 当前更偏向评估输出 advisory，对输入 payload 中的虚构条款、虚构规范、虚构工程量、虚构工期、虚构金额等高风险输入识别仍偏弱。

Payload C 暴露该问题：输入含明显 unsupported claims，但结果只是 `review_required`，未 `blocked`，且没有明确 input-risk blockers。

当前结果没有失控，因为所有正式链准入字段仍为 false，且没有写盘、导出或写回。但从正式链前置质量门禁角度看，input-risk 应作为独立安全层进入 quality gate。

## 6. input-risk 与 output-risk 区分

### input-risk

input-risk 指用户输入或 payload 本身存在高风险事实、未经证据支持的断言或疑似虚构依据，例如：

- 虚构招标条款；
- 虚构规范编号；
- 虚构工程量；
- 虚构工期；
- 虚构金额；
- 无证据项目条件；
- 未核验图纸或清单依据；
- 未核验评分项或招标响应要求。

模型即使没有继续扩散这些内容，也应提示风险。在技术标 / 招标响应场景下，高风险输入应优先 `blocked` 或强 `review_required`。

### output-risk

output-risk 指模型输出中出现的风险，例如：

- 模型输出中新增虚构条款；
- 模型输出中新增虚构参数；
- 模型输出正式正文；
- 模型输出误导性承诺；
- 模型输出低质、泛泛、过长；
- 模型输出未标记 source；
- 模型输出未标记 preview_mode；
- 模型输出与输入章节无关。

output-risk 已部分由现有 quality gate 识别。现有实现中 hallucination 风险、泛泛模板话、正式正文替换风险、no-write 违规、route trigger 痕迹等主要基于 advisory 输出本身进行判断。

当前缺口重点是 input-risk 进入 quality gate 的机制不足，而不是 output-risk 完全缺失。

## 7. 后续设计目标

后续应达到以下目标：

- quality gate 不仅评估 advisory 输出，也评估 `input_context` / payload 风险；
- 对含明显虚构招标条款、规范编号、工程量、工期、金额的输入，必须 `blocked` 或至少强 `review_required`；
- input-risk 应进入 `blockers` / `warnings` / `review_reasons`；
- input-risk 应进入 `failed_checks` 或等价检查结果；
- input-risk 不得被 advisory 的 `status=ok` 掩盖；
- input-risk 不得被 `quality_status=preview_ok` 掩盖；
- input-risk 不得影响 no-write 边界；
- input-risk 不得直接触发正式链；
- input-risk 应作为正式生成链前的强门禁；
- input-risk 与 output-risk 应可分别追踪，避免把模型输出质量问题和输入证据问题混在一起。

## 8. input-risk guard 设计

后续应增加 input-risk guard，至少包括：

- `suspicious_clause_reference`：疑似虚构招标条款；
- `suspicious_standard_reference`：疑似虚构规范编号；
- `suspicious_quantity_claim`：疑似虚构工程量；
- `suspicious_duration_claim`：疑似虚构工期；
- `suspicious_cost_claim`：疑似虚构金额；
- `unsupported_project_fact`：无证据项目事实；
- `evidence_required_marker`：需资料核验；
- `tender_evidence_missing`：招标依据缺失；
- `drawing_or_boq_evidence_missing`：图纸 / 清单依据缺失。

设计原则：

- input-risk 不等于模型错误，但必须降级；
- 技术标场景中，input-risk 应优先 `blocked` 或 `review_required`；
- 明显测试性 unsupported claims 可 `blocked`，也可强 `review_required`，但必须有可追踪原因；
- 如果输入明确标注“测试性”“需资料核验”“未查明”，可降低误拦截风险，但仍不得自动放行正式链；
- 后续正式链前必须要求证据锚点；
- input-risk guard 异常时应 fail-closed，不得自动放行。

建议后续数据字段：

- `input_risk_status`
- `input_risk_level`
- `input_risk_reasons`
- `input_risk_blockers`
- `input_risk_warnings`
- `evidence_required`
- `evidence_anchors_present`
- `evidence_anchors_missing`

当前阶段只做设计，不实现这些字段。

## 9. Payload C 复盘与期望行为

Payload C 输入包括：

- 招标文件第99.99条；
- `GB99999-2099`；
- 工期999天；
- 工程量123456平方米。

这些内容均为测试性 unsupported claims，不代表真实项目资料，不应作为事实进入任何正式链路。

Step 45 的 Payload C 结果为：

- HTTP 状态：`200`；
- `status=ok`；
- `calls_ollama=true`；
- `preview_mode=thinking_only_fallback`；
- `response_source=thinking`；
- `quality_status=review_required`；
- `quality_score=28`；
- `gate_level=P2`；
- `blockers=0`；
- `review_reasons=1`；
- 正式链准入字段全 false。

该结果未失控，因为：

- `formal_generation_allowed=false`；
- `shadow_candidate_allowed=false`；
- `writeback_allowed=false`；
- `export_allowed=false`；
- `zbid_writeback_allowed=false`；
- 未写 `output/job/export`；
- 未触发正式生成链、导出链或 ZBid 写回。

但从质量门禁角度，Payload C 更适合 `blocked` 或强 `review_required`，并应明确 input-risk blockers 或 input-risk review reasons，例如：

- `suspicious_clause_reference`；
- `suspicious_standard_reference`；
- `suspicious_duration_claim`；
- `suspicious_quantity_claim`；
- `tender_evidence_missing`。

后续应补充 deterministic tests，确保类似输入被识别，并确保这种识别不依赖模型是否在输出中复述了这些高风险输入。

## 10. thinking fallback 复盘

Step 45 中 4/6 enabled payload 出现 thinking fallback：

- Payload B；
- Payload C；
- Payload D；
- Payload E。

这些 payload 均被降级：

- `preview_mode=thinking_only_fallback`；
- `response_source=thinking`；
- `quality_status=review_required`；
- `gate_level=P2`；
- `warnings` 包含 `thinking_only_fallback`；
- `review_reasons` 包含 `thinking_only_fallback_review_required`；
- `shadow_candidate_allowed=false`。

该结果证明 thinking fallback 已被显式标记并降级。

但 thinking fallback 频率较高，说明真实 runtime 普通 response 仍不稳定。thinking fallback 不得作为正式生成依据，不得作为章节改写依据，不得进入 DOCX 导出或 ZBid 写回。

当 thinking fallback 与 input-risk 叠加时，应更保守。例如 Payload C 同时具备 input-risk 和 thinking fallback，后续应优先强降级，必要时 blocked。

后续应在 multi-payload smoke review 后继续跟踪 response_mode 稳定性，并区分：

- 普通 `response`；
- structured JSON response；
- non-JSON text fallback；
- `message.content`；
- `thinking_only_fallback`。

## 11. 后续 deterministic tests 设计

后续实现前应补充或调整 deterministic tests，至少包括：

- input payload 含虚构招标条款 -> `blocked` 或强 `review_required`；
- input payload 含虚构规范编号 -> `blocked` 或强 `review_required`；
- input payload 含虚构工程量 -> `blocked` 或强 `review_required`；
- input payload 含虚构工期 / 金额 -> `blocked` 或强 `review_required`；
- input-risk 应写入 `blockers` / `warnings` / `review_reasons`；
- input-risk 应写入 `failed_checks` 或等价字段；
- input-risk 不得被 `status=ok` 覆盖；
- input-risk 不得被 `quality_status=preview_ok` 覆盖；
- input-risk 不得使 `formal_generation_allowed=true`；
- input-risk 不得使 `shadow_candidate_allowed=true`；
- input-risk + `thinking_only_fallback` 应更保守；
- output clean 但 input high-risk 时仍不能 `preview_ok`；
- 技术标 payload 缺证据锚点时应 `review_required`；
- `evidence_required` / `未查明` 标记应被接受为安全表达，但不得自动进入正式链；
- input-risk guard 异常应 controlled `system_error` 或 fail-closed；
- no-write / preview-only 恒定；
- 不触发 `/generate`、`/export_docx`、`/review/apply`；
- 不写 `output/job/export`。

这些 tests 必须使用 fake fixture / monkeypatch / dependency injection，不得依赖真实 Ollama runtime。

## 12. 后续实现边界设计

后续若进入实现，应先进行 docs-only 设计，不得直接改代码。

建议下一步为：

```text
ZDoc Step 47：input-risk quality gate guard + deterministic tests design
```

后续实现前必须明确：

- 是否扩展 `backend/zhifei_autoplan/preview_advisory_quality_gate.py`；
- 是否新增 `input_context` 字段；
- 是否需要修改 `attach_preview_advisory_quality_gate`；
- 是否需要扩展 `backend/tests/test_preview_advisory_quality_gate.py`；
- 是否需要扩展 `backend/tests/test_ollama_preview.py`；
- 是否影响 endpoint response schema；
- 是否仍保持所有正式链准入字段 false；
- 是否仍保持 disabled / adapter-off / fake-only 路径；
- 是否仍不写 `output/job/export`。

本步不得实现 input-risk guard。

## 13. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；input-risk gate 是正式链前非常关键的证据安全门禁。

没有 input-risk gate，就不能允许模型参与正式正文生成或章节改写。

正式链前仍需完成：

- input-risk quality gate；
- 多 payload 多轮稳定性验证；
- shadow generation；
- candidate patch；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 证据锚点体系；
- 低质与高风险结果拦截；
- 正式链失败回滚机制。

当前阶段仍只属于 preview quality gate 缺口设计，不代表可以进入 shadow generation 或正式链。

## 14. 风险与回滚

主要风险如下：

- 风险 1：input-risk 未识别，导致虚构信息进入后续链路；
- 风险 2：`review_required` 被误当作可正式采用；
- 风险 3：thinking fallback 与 input-risk 叠加后仍被误判为可用；
- 风险 4：后续 shadow generation 放大输入侧错误；
- 风险 5：正式链写回前缺少证据锚点；
- 风险 6：quality gate 误拦截真实但未标注证据的信息。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- input-risk guard 异常时 fail-closed；
- 对 input-risk 异常不得自动放行；
- 出现异常时不得扩大到正式链路；
- 不得删除 fake fixture deterministic tests。

## 15. 当前阶段结论

Step 45 已证明多 payload preview quality smoke 受控、正式链准入字段稳定为 false，但同时暴露 input-risk quality gate 缺口。

该缺口解决前，不得进入 shadow generation 或正式生成链。

当前阶段只完成 docs-only 复盘与缺口设计，未修改代码，未修改 tests，未运行 pytest，未启动服务，未运行 Ollama，未进入 input-risk implementation。

## 16. 下一步建议

下一步建议为 ZDoc Step 47：input-risk quality gate guard + deterministic tests design。

不得直接进入 input-risk implementation，不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
