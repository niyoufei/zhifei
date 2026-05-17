# ZDoc real-Ollama preview advisory multi-payload quality smoke plan

## 1. 阶段背景

Step 38 已证明真实 runtime enabled 场景可返回 `status=ok` 和 bounded advisory。该阶段同时确认 `/local-llm/preview-safe` 能在双开关开启时触发 real transport，且响应仍保持 preview-only / no-write 边界。

Step 39 已归档 thinking fallback 质量缺口，明确 Step 38 的 advisory 来源为 `thinking_only_fallback`，不能等同于普通 `response` 或结构化 JSON advisory 稳定。

Step 40 已完成 preview advisory quality gate design，定义 P0-P4 分层门禁、质量状态、评分维度、低质拦截规则、技术标专项质量要求和正式链准入恒 false 的数据契约。

Step 41 已完成 quality gate guard + deterministic tests design，锁定后续实现前的 guard、fake fixture、测试覆盖、允许修改文件和禁止触碰范围。

Step 42 已完成 quality gate fake-only implementation + deterministic tests。当前新增的 quality gate 已在 fake-only deterministic tests 下可控，测试覆盖高质量 advisory、低质 / 泛泛 advisory、thinking fallback、虚构条款 / 工程参数 / 规范编号、安全字段异常、route trigger 痕迹、`output/job/export` 写入痕迹、`system_error`、`ollama_preview` 回归和 safe endpoint 回归。

Step 43 已完成 quality gate fake-stage review，明确当前 quality gate 只附加 preview metadata，不生成正式正文，不触发生成链、导出链或 ZBid 写回。

当前尚未证明真实 runtime 多 payload 下 advisory 质量稳定。本步目标是设计 multi-payload preview quality smoke，不执行 smoke。

## 2. 本次 multi-payload smoke 的目标

后续 Step 45 的目标是验证多个 preview payload 在真实 runtime 下能否稳定返回 advisory，但本步不得执行 smoke。

Step 45 应验证：

- 多个 preview payload 在真实 runtime 下能否受控返回 advisory 或 controlled failure；
- quality gate 对真实 runtime advisory 的判定是否稳定；
- high-quality / vague / hallucination-risk / thinking fallback 等场景的质量门禁表现；
- `quality_status`、`quality_score`、`blockers`、`warnings`、`review_reasons` 是否可追踪；
- `formal_generation_allowed`、`shadow_candidate_allowed`、`writeback_allowed`、`export_allowed`、`zbid_writeback_allowed` 是否仍恒为 false；
- 所有响应是否仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 不触发正式生成链、导出链、ZBid 写回；
- 不写 `output/job/export`。

本次 smoke 的成功不以所有 payload 均 `preview_ok` 为目标，而以多 payload 均受控、质量门禁可追踪、正式链准入不被打开为目标。

## 3. smoke 范围边界

后续 Step 45 只允许：

- 使用本地 loopback Ollama；
- 仅请求 `/local-llm/preview-safe`；
- 仅使用 preview-only payload；
- 仅收集响应摘要与 quality gate metadata；
- 不保存完整模型长输出；
- 不做正文写回；
- 不触发 DOCX 导出；
- 不接 ZBid 写回。

后续 Step 45 明确禁止：

- 直接请求 Ollama `/api/generate`；
- 请求 `/generate`；
- 请求 `/export_docx`；
- 请求 `/review/apply`；
- 访问外网；
- 下载或拉取模型；
- 写 `output/job/export`；
- 修改代码/tests；
- 将 advisory 写入正式章节；
- 将 `preview_ok` 解释为 shadow generation 或正式链准入。

## 4. runtime 前置条件

后续真正执行 Step 45 前必须满足：

- 当前工作区 clean；
- HEAD 必须等于 Step 44 plan 对应标签；
- 不允许修改代码/tests；
- 不运行 pytest；
- 如 `127.0.0.1:11434` 已有 listener，可复用并记录 PID；
- 如无 listener，只能由 2号窗口运行 `ollama serve`；
- 不允许下载或拉取模型；
- 必须先检查 `GET http://127.0.0.1:11434/api/tags`；
- 本地模型必须已存在，优先使用 `qwen3:0.6b`；
- 如模型不存在，立即停止，不得 pull，不得下载；
- FastAPI 只能监听 `127.0.0.1` 临时端口，建议 `18754`；
- 只允许请求 `/local-llm/preview-safe`；
- Step 45 结束前必须按本计划清理本步启动的 FastAPI 进程和端口。

## 5. 环境变量设计

后续 Step 45 至少覆盖 3 类场景。

### disabled 场景

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期为 stable disabled，`calls_ollama=false`，不得构造 real transport。

### adapter-off 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期为 fake-only 或 controlled non-real path，`calls_ollama=false`，不得进入 real runtime path。

### enabled multi-payload 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
export ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
export ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

基于当前只读检查，`ollama_preview.py` 还支持保守运行参数：

```bash
export ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
export ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

当前只读检查未发现独立 host 或 temperature 环境变量；real transport 默认 loopback base URL 为 `http://127.0.0.1:11434`。该项需 Step 45 执行前再次只读核验确认。

## 6. multi-payload 设计

后续 Step 45 的 payload 必须全部为非真实投标正文，不含敏感项目资料，不得包含真实招标文件内容，不得要求生成正式章节正文。建议统一使用当前 endpoint 兼容字段：

- `request_id`
- `section_title`
- `section_text`
- `context_summary`

### Payload A：高质量技术标建议型

目标：验证 quality gate 是否能给出 `preview_ok` 或可展示状态。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-a",
  "section_title": "质量保证措施",
  "section_text": "This is synthetic preview-only text. Please provide one short preview advisory for a construction quality section that already mentions inspection frequency, responsible role,整改闭环, and资料归档. Do not generate formal chapter text.",
  "context_summary": "高质量技术标建议型；仅用于 preview quality smoke。"
}
```

记录重点：

- 是否返回 advisory；
- `quality_status` 是否为 `preview_ok` 或其他可解释状态；
- 是否出现 P0/P4 拦截；
- `formal_generation_allowed` 等正式链准入字段是否恒为 false。

### Payload B：泛泛模板话风险型

目标：验证 quality gate 是否能识别空泛表述并降级。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-b",
  "section_title": "质量保证措施",
  "section_text": "加强管理，严格控制，确保质量。",
  "context_summary": "泛泛模板话风险型；仅用于 preview quality smoke。"
}
```

记录重点：

- 是否被 `review_required` 或 `blocked`；
- `review_reasons` 是否包含低质、泛泛或缺少具体措施等原因；
- 不得因 `status=ok` 误判为质量合格。

### Payload C：虚构风险诱发型

目标：验证 quality gate 是否能识别疑似虚构工程量、规范编号、招标条款、金额、工期等风险。

该 payload 不得使用真实项目条款，只能使用明显假设性、测试性表述。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-c",
  "section_title": "技术风险提示",
  "section_text": "测试性表述：假设存在招标文件第9.9条、GB 00000-2099、工期999日历天、金额999万元。请仅判断该类表述的风险，不得当作真实资料，不得生成正式正文。",
  "context_summary": "虚构风险诱发型；所有条款、规范、工期和金额均为测试占位。"
}
```

记录重点：

- 是否被 `blocked` 或至少 `review_required`；
- `blockers` / `warnings` 是否指出疑似虚构条款、规范编号、金额或工期；
- 不得把测试占位当作真实资料。

### Payload D：thinking fallback 观察型

目标：观察真实 runtime 是否仍主要依赖 thinking fallback，以及 quality gate 是否降级。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-d",
  "section_title": "Runtime Preview Advisory",
  "section_text": "Please provide one short preview advisory and up to two suggestions for this minimal preview-only validation text. Do not write formal content.",
  "context_summary": "thinking fallback 观察型；用于观察 preview_mode / response_source。"
}
```

记录重点：

- `preview_mode` 是否为 `thinking_only_fallback`；
- `response_source` 是否可追踪；
- thinking fallback 是否被显式降级；
- `quality_status` 是否不得高于当前策略允许的展示状态。

### Payload E：极简输入型

目标：验证输入不足时是否返回 `review_required` / `blocked`，而不是误判 `preview_ok`。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-e",
  "section_title": "质量",
  "section_text": "质量。",
  "context_summary": "极简输入型；用于验证输入不足时的质量门禁。"
}
```

记录重点：

- 是否 controlled response；
- 是否因输入不足被降级；
- 不得被误判为高质量。

### Payload F：施工组织设计专项型

目标：验证质量、安全、进度、资源、风险闭环等技术标专项指标是否能被识别。

推荐 payload：

```json
{
  "request_id": "multi-payload-smoke-f",
  "section_title": "施工组织设计专项",
  "section_text": "This is synthetic preview-only text for construction organization design. Please review whether the section should cover quality, safety, schedule, resources, process logic, risk-control measures, inspection frequency, responsible role, and evidence verification. Do not create formal chapter text.",
  "context_summary": "施工组织设计专项型；非真实投标内容，仅用于 quality gate smoke。"
}
```

记录重点：

- 是否识别技术标专项质量要素；
- `quality_score` 与 `passed_checks` / `failed_checks` 是否可解释；
- 是否仍保持正式链准入字段恒为 false。

## 7. 每个 payload 的记录字段

后续 Step 45 对每个 payload 必须记录：

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
- `formal_generation_allowed`；
- `shadow_candidate_allowed`；
- `writeback_allowed`；
- `export_allowed`；
- `zbid_writeback_allowed`；
- 是否出现 `error_type` / `failure_reason`。

记录时不得保存完整模型长输出；如需说明 advisory 内容，只记录短摘要和长度。

## 8. 成功判定标准

Step 45 成功不是要求每个 payload 都 `preview_ok`，而是要求：

- 所有请求均受控返回；
- 不出现未处理异常；
- 所有场景保持 preview-only / no-write；
- `affects_generation=false`；
- `affects_export=false`；
- 正式链准入字段恒为 false；
- 高质量 payload 至少不应被 P0/P4 拦截；
- 泛泛 payload 应 `review_required` 或 `blocked`；
- 虚构风险 payload 应 `blocked` 或至少 `review_required`；
- thinking fallback 应被显式标记并降级；
- 极简输入不得误判为高质量；
- 不写 `output/job/export`；
- 不触发正式生成链、导出链、ZBid 写回；
- 服务结束后端口清理完成。

## 9. 可接受失败标准

以下情况可接受为受控失败：

- 某个 payload 返回 controlled failure；
- 模型返回空 response / empty thinking；
- advisory 缺失但 `error_type` / `failure_reason` 清楚；
- quality gate 将 payload `blocked`；
- timeout 受控返回；
- `quality_status=system_error` 但未抛未处理异常；
- enabled 场景 `calls_ollama=true` 但 `quality_status` 不达标；
- 某个 payload 因 thinking fallback 被降级。

可接受失败必须完整记录原因、状态、no-write 边界和是否未触发正式链路。

## 10. 不可接受失败标准

以下结果不可接受：

- 未处理异常导致服务崩溃；
- 写入 `output/job/export`；
- 触发 `/generate`、`/export_docx`、`/review/apply`；
- 直接请求 Ollama `/api/generate`；
- 下载或拉取模型；
- 访问外网；
- 修改代码/tests；
- 将 advisory 写入正式章节；
- `formal_generation_allowed=true`；
- `shadow_candidate_allowed=true`；
- `writeback_allowed=true`；
- `export_allowed=true`；
- `zbid_writeback_allowed=true`；
- `preview_ok` 被解释为正式链准入；
- thinking fallback 被解释为正式正文。

## 11. output/job/export 写入检查

后续 Step 45 必须在 smoke 前后检查：

- `output/`
- `job/`
- `export/`

如目录不存在，记录不存在。

如目录存在，记录 smoke 前后计数或变更状态。

不得主动写入这些目录。若发现新增写入，Step 45 必须记录为不可接受失败，并停止扩大测试范围。

## 12. 进程与端口清理要求

后续 Step 45 必须：

- 记录 FastAPI PID；
- 记录 Ollama PID；
- 本步启动的 FastAPI 必须停止；
- 确认 `127.0.0.1:18754` 无监听；
- 若 Ollama 是本步启动，则本步结束前停止；
- 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
- 记录 `127.0.0.1:11434` 最终监听状态；
- 不得留下僵尸服务进程。

## 13. smoke report 内容要求

后续 Step 45 report 必须包含：

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
- multi-payload enabled 场景逐项结果表；
- quality gate 统计汇总；
- `preview_ok` 数量；
- `review_required` 数量；
- `blocked` 数量；
- `system_error` 数量；
- thinking fallback 出现次数；
- `formal_generation_allowed` 是否恒 false；
- `shadow_candidate_allowed` 是否恒 false；
- `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否恒 false；
- 是否请求 `/generate`：否；
- 是否请求 `/export_docx`：否；
- 是否请求 `/review/apply`：否；
- 是否直接请求 Ollama `/api/generate`：否；
- 是否写 `output/job/export`：否；
- 是否运行 pytest：否；
- 是否下载或拉取模型：否；
- 是否修改代码/tests：否；
- 进程停止与端口清理情况；
- 风险说明；
- 下一步建议。

## 14. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回；但 multi-payload preview quality smoke 仍只是 preview 质量稳定性验证。

即使 Step 45 成功，也不得直接进入正式生成链。后续仍需：

- shadow generation 设计；
- candidate patch 设计；
- 人工确认写回；
- diff 展示；
- 版本回滚；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 生成质量评分和低质拦截；
- 正式链失败回滚机制。

## 15. 风险与回滚

主要风险：

- 风险 1：多 payload 表现不稳定；
- 风险 2：quality gate 误拦截可用 advisory；
- 风险 3：quality gate 漏放低质 advisory；
- 风险 4：thinking fallback 被误读为正式正文；
- 风险 5：`preview_ok` 被误认为可进入正式链；
- 风险 6：未来 shadow generation 阶段准入字段误置 true。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- quality gate 异常时必须 blocked 或 `system_error`，不得自动放行；
- 出现异常时不得扩大到正式链路；
- 不得删除 fake-only deterministic tests。

## 16. 下一步建议

下一步建议为 ZDoc Step 45：multi-payload preview quality smoke + smoke report。该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
