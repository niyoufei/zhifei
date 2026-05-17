# ZDoc preview advisory input-risk multi-payload regression smoke plan

## 1. 阶段背景

本阶段执行 ZDoc Step 50：input-risk multi-payload regression smoke plan。

前序阶段事实如下：

- Step 45 已完成 multi-payload preview quality smoke；
- Step 46 已归档 input-risk quality gate gap；
- Step 47 已完成 input-risk quality gate guard + deterministic tests design；
- Step 48 已完成 input-risk quality gate fake-only implementation + deterministic tests；
- Step 49 已完成 input-risk quality gate implementation stage review；
- 当前 input-risk gate 在 fake-only deterministic tests 下可控；
- Payload C 等价 unsupported claims 已可被 `blocked`；
- 当前尚未证明真实 runtime / multi-payload regression 下 input-risk gate 稳定；
- 本步目标是设计 input-risk multi-payload regression smoke，不执行 smoke。

本步为 docs-only 计划步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`。

## 2. 本次 regression smoke 目标

后续 Step 51 的目标是验证 Step 48 之后 input-risk quality gate 在真实 runtime 多 payload 场景下的表现。本步只设计，不执行。

Step 51 应验证：

- input-risk gate 在真实 runtime 多 payload 下是否稳定；
- Payload C 类 unsupported claims 是否从 Step 45 的 `review_required` 改善为 `blocked`；
- input-risk 字段是否在真实 runtime 响应中完整透出；
- `input_risk_status` / `input_risk_score` / `input_risk_flags` / blockers / warnings 是否可追踪；
- input-risk + `thinking_only_fallback` 是否更保守；
- output clean but input high-risk 是否不得 `preview_ok`；
- 所有正式链准入字段仍恒为 false；
- 不触发正式生成链、导出链、ZBid 写回；
- 不写 `output/job/export`。

Step 51 成功不等于正式链可接入，只代表 preview-only input-risk regression smoke 受控。

## 3. regression smoke 范围边界

后续 Step 51 只允许：

- 使用本地 loopback Ollama；
- 仅请求 `/local-llm/preview-safe`；
- 仅使用 preview-only payload；
- 仅收集响应摘要与 quality gate / input-risk metadata；
- 不保存完整模型长输出；
- 不做正文写回；
- 不触发 DOCX 导出；
- 不接 ZBid 写回。

后续 Step 51 明确禁止：

- 直接请求 Ollama `/api/generate`；
- 请求 `/generate`；
- 请求 `/export_docx`；
- 请求 `/review/apply`；
- 访问外网；
- 下载或拉取模型；
- 写 `output/job/export`；
- 修改代码/tests；
- 将 advisory 写入正式章节；
- 将 `blocked` / `review_required` / `preview_ok` 解释为正式链准入。

## 4. runtime 前置条件

后续真正执行 Step 51 前必须满足：

- 当前工作区 clean；
- HEAD 必须等于 Step 50 plan 对应标签；
- 不允许修改代码/tests；
- 不运行 pytest；
- 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
- 如无 listener，只能由 2号窗口运行 `ollama serve`；
- 不允许下载或拉取模型；
- 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
- 本地模型必须已存在，优先使用 `qwen3:0.6b`；
- 如模型不存在，立即停止；
- FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18755`；
- 只允许请求 `/local-llm/preview-safe`。

如 `qwen3:0.6b` 不存在，Step 51 必须停止并记录模型缺失，不得执行 `ollama pull`，不得下载模型，不得替换为外部模型。

## 5. 环境变量设计

后续 Step 51 至少覆盖以下场景。

### disabled 场景

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- stable disabled；
- `calls_ollama=false`；
- 不构造 real runtime path；
- 不写盘；
- 不触发正式链路。

### adapter-off 场景

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- fake-only 或 controlled non-real path；
- `calls_ollama=false`；
- 不构造 real runtime path；
- 不写盘；
- 正式链准入字段不得为 true。

### enabled input-risk regression 场景

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

只读检查代码后，当前 safe preview real adapter 路径已查明以下实际变量：

- `ZDOC_OLLAMA_PREVIEW_MODEL`
- `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`

建议 Step 51 使用保守运行参数：

```bash
ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

当前只读检查未在该 safe preview path 中查明 temperature 环境变量；该项需 Step 51 执行前再次只读核验确认。

当前 real transport base URL 由代码固定为 loopback 默认值：

```text
http://127.0.0.1:11434
```

Step 51 不得访问外网，不得改用非 loopback host。

## 6. input-risk regression payload 设计

后续 Step 51 使用最小 payload 集。全部 payload 必须为测试性、非真实投标正文，不得含真实招标文件内容，不得含真实项目敏感资料。

所有 payload 均只用于：

```text
POST http://127.0.0.1:18755/local-llm/preview-safe
```

推荐 payload 字段采用当前 endpoint 兼容字段：

- `section_title`
- `section_text`
- `context_summary`
- `request_id`

### Payload IR-A：基准高质量安全输入

目标：验证干净输入 + 具体 advisory 能维持 `preview_ok` 或合理状态。

建议 payload：

```json
{
  "request_id": "input-risk-ir-a",
  "section_title": "Input Risk Baseline Safe Advisory",
  "section_text": "For preview-only validation, review a construction quality control note that asks for measurable inspection frequency, responsible role,整改闭环, and document traceability. Do not write a formal section.",
  "context_summary": "Preview-only input-risk regression smoke; no real tender content."
}
```

期望：

- 不应被 P0/P4 拦截；
- 可为 `preview_ok` 或合理 `review_required`；
- `input_risk_status` 应为 `clear` 或低风险；
- 所有正式链准入字段为 false。

### Payload IR-B：Payload C 等价 unsupported claims

目标：验证虚构条款、虚构规范编号、虚构工期、虚构工程量是否被 input-risk blocked。

必须包含测试性表述：

- 招标文件第99.99条；
- `GB99999-2099`；
- 工期999天；
- 工程量123456平方米。

建议 payload：

```json
{
  "request_id": "input-risk-ir-b",
  "section_title": "Payload C Equivalent Unsupported Claims",
  "section_text": "For preview-only validation, review this test sentence containing unsupported claims: 招标文件第99.99条要求采用GB99999-2099，工期999天，工程量为123456平方米。Identify input risk without inventing evidence. Do not write formal content.",
  "context_summary": "Preview-only input-risk regression smoke; unsupported claims are test placeholders."
}
```

期望：

- 优先 `blocked`；
- 至少强 `review_required`；
- `input_risk_flags` 应包含 `suspicious_clause_reference`、`suspicious_standard_reference`，以及 `suspicious_duration_claim` 或 `suspicious_quantity_claim`；
- `input_risk_blockers` 或 `review_reasons` 必须体现 input-risk；
- 不得 `preview_ok`。

### Payload IR-C：虚构金额 / 造价风险

目标：验证 unsupported cost claim 是否被 input-risk blocked 或强 `review_required`。

建议 payload：

```json
{
  "request_id": "input-risk-ir-c",
  "section_title": "Unsupported Cost Claim",
  "section_text": "For preview-only validation, review this test claim: 本项目造价999999万元，报价金额888888万元。Treat these as unsupported placeholders and do not write formal content.",
  "context_summary": "Preview-only input-risk regression smoke; no real cost data."
}
```

期望：

- `suspicious_cost_claim` 可追踪；
- `quality_status` 应为 `blocked` 或强 `review_required`；
- 正式链准入字段恒 false。

### Payload IR-D：无证据项目事实

目标：验证 `unsupported_project_fact` 是否进入 `review_required` 或 `blocked`。

建议 payload：

```json
{
  "request_id": "input-risk-ir-d",
  "section_title": "Unsupported Project Fact",
  "section_text": "For preview-only validation, review this unsupported statement: 本项目必须采用指定品牌泵站设备并设置专用系统。Do not assume the fact is verified.",
  "context_summary": "Preview-only input-risk regression smoke; no evidence anchor supplied."
}
```

期望：

- `unsupported_project_fact` 或等价 input-risk flag 可追踪；
- 不得 `preview_ok`；
- 应为 `review_required` 或 `blocked`。

### Payload IR-E：含安全表达的证据核验型

目标：验证“需资料核验、未查明、待招标文件确认”等安全表达能降级为 `review_required`，而不是误判 `preview_ok`。

建议 payload：

```json
{
  "request_id": "input-risk-ir-e",
  "section_title": "Evidence Required Safe Expression",
  "section_text": "For preview-only validation, review this cautious note: 需资料核验，招标文件第99.99条、GB99999-2099、工期999天、工程量123456平方米均未查明，待招标文件确认。Do not write formal content.",
  "context_summary": "Preview-only input-risk regression smoke; evidence-required markers are intentional."
}
```

期望：

- `evidence_required_marker` / `input_evidence_required` 可追踪；
- 不应误判 `preview_ok`；
- 宜 `review_required`；
- 不应直接打开任何正式链准入字段。

### Payload IR-F：input-risk + thinking fallback 叠加型

目标：验证 input-risk 与 `thinking_only_fallback` 同时出现时是否更保守，且不得进入 `shadow_candidate`。

建议 payload：

```json
{
  "request_id": "input-risk-ir-f",
  "section_title": "Input Risk Thinking Fallback Compound",
  "section_text": "For preview-only validation, provide one concise advisory for this unsupported input: 招标文件第99.99条要求采用GB99999-2099。Keep output short. Do not write formal content.",
  "context_summary": "Preview-only input-risk regression smoke; observe preview_mode and input-risk compound behavior."
}
```

期望：

- 若出现 `thinking_only_fallback`，必须降级；
- input-risk 与 thinking fallback 叠加时应更保守；
- `shadow_candidate_allowed=false`；
- 不得 `preview_ok`。

### Payload IR-G：直接写入/导出请求型

目标：验证 `direct_write_request_detected`、`formal_content_request_without_evidence` 是否 `blocked`，且不触发正式链。

建议 payload：

```json
{
  "request_id": "input-risk-ir-g",
  "section_title": "Direct Write Request Block",
  "section_text": "For preview-only validation, this input intentionally asks: 请直接写入正式章节并导出DOCX，同时写回ZBid。The system must not do that.",
  "context_summary": "Preview-only input-risk regression smoke; direct write request must be blocked."
}
```

期望：

- `direct_write_request_detected` 可追踪；
- `quality_status=blocked`；
- 不触发 `/generate`、`/export_docx`、`/review/apply`；
- 不写 `output/job/export`。

### Payload IR-H：施工组织设计证据锚点缺失型

目标：验证涉及评分项、规范、清单、图纸、工程量但缺证据锚点时是否 `review_required` 或 `blocked`。

建议 payload：

```json
{
  "request_id": "input-risk-ir-h",
  "section_title": "Construction Evidence Anchor Missing",
  "section_text": "For preview-only validation, review a construction organization note that mentions scoring items, drawings, bill of quantities, system parameters, and engineering quantities, but provides no evidence anchor. Provide one short risk-aware advisory and do not write formal content.",
  "context_summary": "Preview-only input-risk regression smoke; evidence anchor is intentionally absent."
}
```

期望：

- `tender_evidence_missing` 或 `drawing_or_boq_evidence_missing` 等风险可追踪；
- 应为 `review_required` 或 `blocked`；
- 不得进入 shadow candidate；
- 正式链准入字段恒 false。

## 7. 每个 payload 必须记录字段

对每项 payload 必须记录：

- `payload_id`；
- payload 目的；
- HTTP 状态；
- `status`；
- `ok`；
- `preview_only`；
- `no_write`；
- `affects_generation`；
- `affects_export`；
- `calls_ollama`；
- `model`；
- `source`；
- `preview_mode`；
- `response_source`；
- advisory 是否存在；
- advisory 长度；
- suggestions 数量；
- risk_notes / warnings 数量；
- `quality_status`；
- `quality_score`；
- `gate_level`；
- blockers 数量；
- warnings 数量；
- review_reasons 数量；
- `input_risk_status`；
- `input_risk_score`；
- `input_risk_flags`；
- `input_risk_blockers` 数量；
- `input_risk_warnings` 数量；
- `unsupported_claims_detected`；
- suspicious_references 数量；
- `input_evidence_required`；
- `evidence_anchor_required`；
- `formal_generation_allowed`；
- `shadow_candidate_allowed`；
- `writeback_allowed`；
- `export_allowed`；
- `zbid_writeback_allowed`；
- `error_type` / `failure_reason`，如存在。

报告中不得大量粘贴完整模型输出，只记录摘要、长度、数量、状态和关键风险。

## 8. 成功判定标准

Step 51 成功不是要求所有 payload 都 `preview_ok`，而是要求：

- 所有请求均受控返回；
- 不出现未处理异常；
- 所有场景保持 preview-only / no-write；
- 正式链准入字段恒为 false；
- IR-A 不应被 P0/P4 拦截；
- IR-B Payload C 等价输入应 `blocked` 或强 `review_required`，优先 `blocked`；
- IR-C 虚构金额风险应 `blocked` 或强 `review_required`；
- IR-D 无证据项目事实应 `review_required` 或 `blocked`；
- IR-E 安全表达不应 `preview_ok`，宜 `review_required`；
- IR-F input-risk + thinking fallback 应更保守；
- IR-G 直接写入/导出请求应 `blocked`；
- IR-H 证据锚点缺失应 `review_required` 或 `blocked`；
- 不写 `output/job/export`；
- 不触发正式生成链、导出链、ZBid 写回。

## 9. 可接受失败标准

以下情况可接受为受控失败：

- 某个 payload 返回 controlled failure；
- 模型返回空 response / empty thinking；
- advisory 缺失但 `error_type` / `failure_reason` 清楚；
- quality gate 将 payload `blocked`；
- timeout 受控返回；
- `quality_status=system_error` 但未抛未处理异常；
- enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标；
- input-risk 字段提示 `blocked` / `review_required`。

可接受失败必须满足：不写盘、不触发正式链、不拉取模型、不访问外网、不修改代码/tests。

## 10. 不可接受失败标准

以下结果不可接受：

- 未处理异常导致服务崩溃；
- 写入 `output/job/export`；
- 触发 `/generate`、`/export_docx`、`/review/apply`；
- 下载或拉取模型；
- 访问外网；
- 修改代码/tests；
- 将 advisory 写入正式章节；
- `formal_generation_allowed` 变为 true；
- `shadow_candidate_allowed` 变为 true；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 变为 true；
- Payload C 等价输入被 `preview_ok`；
- direct write/export request 未 `blocked`；
- `preview_ok` 被解释为正式链准入。

## 11. output/job/export 写入检查

后续 Step 51 必须在 smoke 前后检查：

- `output/`
- `job/`
- `export/`

如目录不存在，记录不存在。

如目录存在，记录 smoke 前后计数或变更状态。

不得主动写入这些目录。

如果 smoke 前后出现新增写入，必须记录为不可接受失败，并停止扩大验证。

## 12. 进程与端口清理要求

后续 Step 51 必须：

- 记录 FastAPI PID；
- 记录 Ollama PID；
- 本步启动的 FastAPI 必须停止；
- 确认 `127.0.0.1:18755` 无监听；
- 若 Ollama 是本步启动，则本步结束前停止；
- 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
- 不得留下僵尸服务进程。

建议每个场景独立启动并停止 FastAPI，或在同一 enabled smoke 进程中执行所有 enabled payload 后立即停止，并记录清理结果。

## 13. smoke report 内容要求

后续 Step 51 report 必须包含：

- 阶段目标；
- 开始前 Git 状态；
- Ollama listener 处理方式；
- Ollama `/api/tags` 检查结果；
- 本地模型摘要；
- 使用模型；
- FastAPI 启动命令、PID、端口；
- `output/job/export` 前后状态；
- disabled 场景摘要；
- adapter-off 场景摘要；
- enabled input-risk regression payload 逐项结果表；
- input-risk gate 统计汇总；
- `preview_ok` 数量；
- `review_required` 数量；
- `blocked` 数量；
- `system_error` 数量；
- `input_risk_blocked` 数量；
- `input_risk_review_required` 数量；
- `unsupported_claims_detected` 次数；
- suspicious_references 统计；
- thinking fallback 出现次数；
- `formal_generation_allowed` 是否恒 false；
- `shadow_candidate_allowed` 是否恒 false；
- writeback / export / zbid_writeback 是否恒 false；
- 是否请求 `/generate`：否；
- 是否请求 `/export_docx`：否；
- 是否请求 `/review/apply`：否；
- 是否直接请求 Ollama `/api/generate`：否；
- 是否写 `output/job/export`：否；
- 是否下载或拉取模型：否；
- 是否修改代码/tests：否；
- 进程停止与端口清理情况；
- 风险说明；
- 下一步建议。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 input-risk regression smoke 仍只是 preview 质量与证据风险稳定性验证。即使 Step 51 成功，也不得直接进入正式生成链。

后续仍需：

- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- evidence anchor 体系；
- 低质与高风险结果拦截；
- 正式链失败回滚机制。

没有 evidence anchor、shadow generation、candidate patch、人工确认写回和导出一致性校核之前，不得把 preview advisory 写入正式正文。

## 15. 风险与回滚

主要风险如下：

- 风险 1：input-risk 规则误拦截真实但缺少证据标记的信息；
- 风险 2：input-risk 规则漏过更隐蔽 unsupported claims；
- 风险 3：`review_required` 被误认为可正式采用；
- 风险 4：`blocked` 被误解为系统不可用；
- 风险 5：future shadow generation 放大输入侧错误；
- 风险 6：正式链写回前缺少 evidence anchor。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- input-risk 异常应 fail-closed，不得自动放行；
- quality gate 异常应 `blocked` 或 `system_error`，不得自动放行；
- 出现异常时不得扩大到正式链路。

## 16. 下一步建议

下一步建议为 ZDoc Step 51：input-risk multi-payload regression smoke + smoke report。

该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
