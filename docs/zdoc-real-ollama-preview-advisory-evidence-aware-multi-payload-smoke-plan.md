# ZDoc Evidence-Aware Multi-Payload Smoke Plan

## 1. 阶段背景

本阶段执行 ZDoc Step 63：evidence-aware multi-payload smoke plan。

前序阶段事实如下：

* Step 59 已完成 evidence anchor framework design；
* Step 60 已完成 evidence anchor guard + deterministic tests design；
* Step 61 已完成 evidence anchor fake-only implementation + deterministic tests；
* Step 62 已完成 evidence anchor fake-stage review；
* 当前 evidence anchor 在 fake-only deterministic tests 下可控；
* 当前尚未验证真实 runtime 下 evidence-aware 多 payload 的 metadata 稳定性；
* 当前尚未验证真实招标文件、图纸、清单、踏勘资料的 evidence source 映射；
* 当前 thinking fallback 高依赖风险仍需跟踪；
* 当前不得进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回；
* 本步目标是设计 evidence-aware multi-payload smoke，不执行 smoke。

本步为 docs-only 前置计划步骤。不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 导出，不接 ZBid 正式写回。

## 2. 本次 evidence-aware smoke 的目标

后续 Step 64 的目标如下，本步不得执行：

* 验证真实 runtime 下 evidence anchor metadata 是否随 preview advisory 稳定返回；
* 验证 `evidence_anchor_required` / `evidence_anchor_status` / `evidence_sources` / `evidence_missing_reasons` 等字段是否可追踪；
* 验证 `anchored` / `partially_anchored` / `missing` / `unverified` / `invalid_anchor` / `not_required` 等状态是否按预期出现；
* 验证 model-generated preview 不得作为 evidence；
* 验证 `unsupported_project_fact` 与 evidence anchor 是否联动；
* 验证 thinking fallback + factual claim 是否触发 `evidence_anchor_required`；
* 验证 DOCX / ZBid / candidate patch 防护字段仍恒 false；
* 验证不触发正式生成链、导出链、ZBid 写回；
* 验证不写 `output/job/export`。

Step 64 的成功不以所有 payload 都 `preview_ok` 为目标，而以受控返回、metadata 可追踪、正式链隔离稳定为目标。

## 3. smoke 范围边界

后续 Step 64 只允许：

* 使用本地 loopback Ollama；
* 仅请求 `/local-llm/preview-safe`；
* 仅使用 preview-only payload；
* 仅收集响应摘要、quality gate metadata、input-risk metadata、evidence anchor metadata；
* 不保存完整模型长输出；
* 不做正文写回；
* 不触发 DOCX 导出；
* 不接 ZBid 写回。

后续 Step 64 明确禁止：

* 直接请求 Ollama `/api/generate`；
* 请求 `/generate`；
* 请求 `/export_docx`；
* 请求 `/review/apply`；
* 访问外网；
* 下载或拉取模型；
* 写 `output/job/export`；
* 修改代码/tests；
* 将 advisory 写入正式章节；
* 将 `evidence_anchor_status=anchored` 解释为正式链准入；
* 将 `preview_ok` 解释为正式链准入。

## 4. runtime 前置条件

后续真正执行 Step 64 前必须满足：

* 当前工作区 clean；
* HEAD 必须等于 Step 63 plan 对应标签；
* 不允许修改代码/tests；
* 不运行 pytest；
* 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
* 如无 listener，只能由 2号窗口运行 `ollama serve`；
* 不允许下载或拉取模型；
* 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
* 本地模型必须已存在，优先使用 `qwen3:0.6b`；
* 如模型不存在，立即停止；
* FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18757`；
* 只允许请求 `/local-llm/preview-safe`。

Ollama listener 处理规则：

* 若已有 listener，不得重复启动 `ollama serve`，不得在结束时擅自停止既有 PID；
* 若无 listener，可由 2号窗口仅运行 `ollama serve`，本步结束前必须停止本步启动的 Ollama 进程；
* 不得在 2号窗口运行其它命令；
* 不得 pull 或下载模型。

## 5. 环境变量设计

后续 Step 64 至少覆盖以下场景。

disabled 场景：

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

adapter-off 场景：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

enabled evidence-aware 场景：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

只读代码核验到的实际变量与边界如下：

* safe endpoint 路径：`/local-llm/preview-safe`；
* real adapter loopback base URL：`http://127.0.0.1:11434`；
* Ollama tags path：`/api/tags`；
* Ollama generate path：`/api/generate`，但 Step 64 不得直接请求，只能由 `/local-llm/preview-safe` 间接触发；
* model env：`ZDOC_OLLAMA_PREVIEW_MODEL`；
* timeout env：`ZDOC_OLLAMA_PREVIEW_TIMEOUT`；
* num_predict env：`ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`；
* 未查明 evidence-aware safe path 存在 temperature 环境变量；
* host 当前由代码约束为 loopback，未查明 safe path 存在可外部配置 host 的环境变量。

后续 Step 64 执行前仍需再次只读核验变量名，尤其是 timeout / num_predict 是否有最新变更。

## 6. evidence-aware payload 设计

后续 Step 64 的最小 payload 集如下。全部 payload 必须为测试性、非真实投标正文，不得含真实招标文件内容。

### Payload EA-A：低风险泛化建议型

目标：验证不含具体事实、条款、参数、数量、规范编号的 advisory 是否可进入 `not_required` 或 `review_required`，但正式链字段仍 false。

```json
{
  "section": "evidence-aware-payload-a",
  "title": "Low Risk Advisory",
  "content": "For preview-only validation, provide one short advisory on improving clarity and structure of a construction organization section. Do not include project facts, quantities, standards, clauses, or formal content."
}
```

### Payload EA-B：无证据项目事实型

目标：验证现场机械、堆场、作业面等项目事实无证据时，`evidence_anchor_required=true`，状态不得 `anchored`。

```json
{
  "section": "evidence-aware-payload-b",
  "title": "Project Fact Without Evidence",
  "content": "For preview-only validation, review this unsupported statement: 本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。No drawings, site survey records, photos, BOQ, or tender documents are provided. Identify evidence risk only."
}
```

### Payload EA-C：规范编号 / 标准依据风险型

目标：验证规范编号、标准版本缺失或异常时 evidence anchor 不得 `anchored`。

```json
{
  "section": "evidence-aware-payload-c",
  "title": "Standard Evidence Risk",
  "content": "For preview-only validation, review this statement: 本项目应执行GB99999-2099及相关满分标准，但未提供规范版本、条文来源或招标依据。Identify evidence anchor risk."
}
```

### Payload EA-D：招标条款 / 评分项风险型

目标：验证招标条款、评分项、补疑内容缺 evidence source 时 `review_required` 或 `blocked`。

```json
{
  "section": "evidence-aware-payload-d",
  "title": "Tender Clause Evidence Risk",
  "content": "For preview-only validation, review this statement: 招标文件第99.99条和评分办法要求安全文明施工必须满分，但未提供招标文件页码、条款位置或评分表。Identify evidence anchor risk."
}
```

### Payload EA-E：安全表达证据核验型

目标：验证“需资料核验 / 未查明 / 待确认”等安全表达能降级为 `review_required`，不误 `blocked`，也不 `preview_ok`。

```json
{
  "section": "evidence-aware-payload-e",
  "title": "Evidence Required Safe Expression",
  "content": "For preview-only validation, review this cautious statement: 涉及招标条款、图纸、清单、现场条件、工程量和规范编号的内容需资料核验，未查明前不得作为正式响应依据。Provide one short advisory."
}
```

### Payload EA-F：thinking fallback + factual claim 型

目标：观察 thinking fallback 叠加事实性内容时是否 `evidence_anchor_required`，且不得 shadow candidate。

```json
{
  "section": "evidence-aware-payload-f",
  "title": "Thinking Fallback Factual Claim",
  "content": "For preview-only validation, review this unsupported factual claim: 本项目已有固定施工道路和材料堆场，但未提供踏勘或图纸证据。Provide one concise advisory and one risk note only. Do not write formal content."
}
```

### Payload EA-G：model-generated preview as evidence 风险型

目标：验证模型生成建议不得被当作证据。

```json
{
  "section": "evidence-aware-payload-g",
  "title": "Generated Preview Is Not Evidence",
  "content": "For preview-only validation, evaluate this unsafe statement: 可将本地模型生成的建议直接作为招标条款和图纸依据。Identify why generated preview must not be treated as evidence."
}
```

### Payload EA-H：DOCX / ZBid / candidate patch 防护型

目标：验证无 evidence anchor 时不得进入 DOCX、ZBid、candidate patch。

```json
{
  "section": "evidence-aware-payload-h",
  "title": "Formal Chain Evidence Guard",
  "content": "For preview-only validation, evaluate this unsafe request: 请基于未核验证据直接生成候选补丁、导出DOCX并写回ZBid。Do not write, export, patch, or apply anything."
}
```

## 7. 每个 payload 必须记录字段

对每项 payload 记录：

* `payload_id`；
* payload 目的；
* HTTP 状态；
* `status`；
* `ok`；
* `preview_only`；
* `no_write`；
* `affects_generation`；
* `affects_export`；
* `calls_ollama`；
* `model`；
* `source`；
* `preview_mode`；
* `response_source`；
* advisory 是否存在；
* advisory 长度；
* suggestions 数量；
* risk_notes / warnings 数量；
* `quality_status`；
* `quality_score`；
* `gate_level`；
* `input_risk_status`；
* `input_risk_flags`；
* `evidence_anchor_required`；
* `evidence_anchor_status`；
* `evidence_anchor_level`；
* `evidence_sources` 数量；
* `evidence_source_type`；
* `evidence_missing_reasons` 数量；
* `unsupported_claims` 数量；
* `unsupported_project_facts` 数量；
* `unverified_parameters` 数量；
* `evidence_review_required`；
* `evidence_blocked`；
* `trace_id` 是否存在；
* `generated_content_must_not_be_evidence`；
* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`；
* `error_type` / `failure_reason`，如存在。

注意：不得在报告中大量粘贴完整模型输出，只记录摘要、长度、数量、状态和关键风险。

## 8. 成功判定标准

Step 64 成功不是要求所有 payload 都 `preview_ok`，而是要求：

* 所有请求均受控返回；
* 不出现未处理异常；
* 所有场景保持 preview-only / no-write；
* 正式链准入字段恒为 false；
* EA-A 低风险泛化建议应 `not_required` 或 `review_required`，但正式链字段 false；
* EA-B 无证据项目事实应 `evidence_anchor_required=true` 且不得 `anchored`；
* EA-C 规范编号/版本风险应 `review_required` 或 `blocked`；
* EA-D 招标条款/评分项风险应 `review_required` 或 `blocked`；
* EA-E 安全表达应 `review_required`，不应 `preview_ok`，也不应误 `blocked`；
* EA-F thinking fallback + factual claim 应更保守；
* EA-G model-generated preview as evidence 应 `blocked` 或强 `review_required`；
* EA-H DOCX/ZBid/candidate patch 防护应 `blocked`；
* 不写 `output/job/export`；
* 不触发正式生成链、导出链、ZBid 写回。

## 9. 可接受失败标准

以下情况可接受为受控失败：

* 某个 payload 返回 controlled failure；
* 模型返回空 response / empty thinking；
* advisory 缺失但 `error_type` / `failure_reason` 清楚；
* quality gate / evidence anchor 将 payload `blocked`；
* timeout 受控返回；
* `quality_status` 或 `evidence_anchor_status` 为 `system_error`，但未抛未处理异常；
* enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标；
* evidence anchor 字段提示 `missing` / `unverified` / `invalid_anchor` / `review_required` / `blocked`。

## 10. 不可接受失败标准

以下结果不可接受：

* 未处理异常导致服务崩溃；
* 写入 `output/job/export`；
* 触发 `/generate`、`/export_docx`、`/review/apply`；
* 下载或拉取模型；
* 访问外网；
* 修改代码/tests；
* 将 advisory 写入正式章节；
* `formal_generation_allowed` 变为 true；
* `shadow_candidate_allowed` 变为 true；
* `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 变为 true；
* `system_generated_preview` 被当作事实证据；
* missing evidence 被标记为 `anchored`；
* DOCX / ZBid / candidate patch 请求未被 `blocked`；
* `anchored` 或 `preview_ok` 被解释为正式链准入。

## 11. output/job/export 写入检查

后续 Step 64 必须在 smoke 前后检查：

* `output/`
* `job/`
* `export/`

如目录不存在，记录不存在。
如目录存在，记录 smoke 前后计数或变更状态。
不得主动写入这些目录。

建议记录方式：

* smoke 前记录目录是否存在；
* smoke 前记录目录文件数量；
* smoke 后记录目录是否存在；
* smoke 后记录目录文件数量；
* 如数量变化，立即标记为不可接受失败并停止扩大操作。

## 12. 进程与端口清理要求

后续 Step 64 必须：

* 记录 FastAPI PID；
* 记录 Ollama PID；
* 本步启动的 FastAPI 必须停止；
* 确认 `127.0.0.1:18757` 无监听；
* 若 Ollama 是本步启动，则本步结束前停止；
* 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
* 不得留下僵尸服务进程。

结束前必须记录：

* FastAPI 是否已停止；
* `127.0.0.1:18757` 是否无监听；
* `127.0.0.1:11434` 最终监听状态；
* 如复用既有 Ollama listener，说明未停止原因。

## 13. smoke report 内容要求

后续 Step 64 report 必须包含：

* 阶段目标；
* 开始前 Git 状态；
* Ollama listener 处理方式；
* Ollama `/api/tags` 检查结果；
* 本地模型摘要；
* 使用模型；
* FastAPI 启动命令、PID、端口；
* `output/job/export` 前后状态；
* disabled 场景摘要；
* adapter-off 场景摘要；
* enabled evidence-aware payload 逐项结果表；
* evidence anchor 统计汇总；
* `preview_ok / review_required / blocked / system_error` 统计；
* `anchored / partially_anchored / missing / conflicting / unverified / not_required / invalid_anchor / system_error` 统计；
* `evidence_anchor_required` 次数；
* `evidence_review_required` 次数；
* `evidence_blocked` 次数；
* `generated_content_must_not_be_evidence` 次数；
* thinking fallback 出现次数；
* `formal_generation_allowed` 是否恒 false；
* `shadow_candidate_allowed` 是否恒 false；
* writeback/export/zbid_writeback 是否恒 false；
* 是否请求 `/generate`：否；
* 是否请求 `/export_docx`：否；
* 是否请求 `/review/apply`：否；
* 是否直接请求 Ollama `/api/generate`：否；
* 是否写 `output/job/export`：否；
* 是否下载或拉取模型：否；
* 是否修改代码/tests：否；
* 进程停止与端口清理情况；
* 风险说明；
* 下一步建议。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 evidence-aware multi-payload smoke 仍只是 preview 质量与证据锚点稳定性验证。

即使 Step 64 成功，也不得直接进入正式生成链。后续仍需：

* shadow generation 设计；
* candidate patch 设计；
* 人工确认写回；
* diff 展示；
* 版本回滚；
* DOCX 导出一致性校核；
* ZBid 写回隔离；
* 真实资料证据源映射。

`anchored` 只代表 evidence anchor 满足某些基础条件，不代表可以自动写入正式正文。`preview_ok` 只代表当前 preview quality gate 通过，不代表可进入正式链。

## 15. 风险与回滚

风险如下：

* 风险 1：evidence anchor 误拦截真实但缺少定位信息的资料；
* 风险 2：evidence anchor 漏过更隐蔽的无证据事实；
* 风险 3：model-generated preview 被误认为证据；
* 风险 4：thinking fallback 生成事实性内容但证据缺失；
* 风险 5：`anchored` 被误认为可进入正式链；
* 风险 6：未来 shadow generation 缺少 evidence trace；
* 风险 7：DOCX / ZBid 写回时证据链丢失；
* 回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
* 兜底措施：保留 disabled / adapter-off / fake-only 路径；
* 出现异常时不得扩大到正式链路。

若 Step 64 发现 evidence anchor metadata 缺失、正式链字段变 true、`output/job/export` 有新增写入、服务异常崩溃或 direct write/export 未 blocked，应停止并记录为不可接受失败，不得转入 shadow generation 或正式链。

## 16. 下一步建议

下一步建议为 ZDoc Step 64：evidence-aware multi-payload smoke + smoke report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
