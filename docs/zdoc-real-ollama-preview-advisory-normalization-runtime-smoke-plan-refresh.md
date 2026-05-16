# ZDoc preview advisory normalization runtime smoke plan refresh

## 1. 阶段背景

本阶段执行 ZDoc Step 37：preview advisory normalization runtime smoke plan refresh。

前序阶段事实如下：

- Step 32 已证明 default real transport runtime 可触发；
- Step 32 enabled 场景返回 `calls_ollama=true`；
- Step 32 enabled 场景返回 `real_transport_enabled=true`；
- Step 32 同时暴露 `invalid_response / missing_preview_advisory`；
- Step 33 已归档该缺口；
- Step 34 已完成 normalization guard + deterministic tests design；
- Step 35 已完成 normalization fake-only implementation + deterministic tests；
- Step 35 测试结果为 `140 passed in 3.72s`；
- Step 36 已完成 fake-stage review；
- 当前 fake fixture 下普通文本、JSON 文本、非 JSON 技术建议文本、`message.content`、thinking fallback、空响应、malformed JSON、normalization failure 均已受控。

本步目标是基于 Step 35 normalization 修复成果刷新 runtime smoke 边界，不执行 runtime smoke，不启动服务，不运行 Ollama，不运行 `ollama serve`，不运行 pytest，不调用外部模型/API，不下载或拉取模型。

## 2. 本次 plan refresh 与 Step 31 的差异

Step 31 的 runtime smoke 重点是验证 Step 29 后 default real transport 是否能在 runtime 中触发。Step 32 已完成该验证，关键事实是：

- enabled 场景已进入 default real transport runtime path；
- enabled 场景 `calls_ollama=true`；
- enabled 场景不再返回 `fake_transport_required`；
- 但 advisory normalization 未闭环，返回 `status=failure`、`error_type=invalid_response`、`reason=missing_preview_advisory`。

Step 35 后，runtime smoke 的重点应从“是否触发 default real transport”转为“真实模型 response 是否能被 normalization 转为 bounded advisory”。

新的 Step 38 smoke 不再只观察 `calls_ollama=true`，还必须观察：

- `status=ok` 是否成立；
- advisory 是否存在；
- suggestions 是否存在且受控；
- risk_notes 或 warnings 是否存在且受控；
- 是否出现 thinking fallback；
- `error_type` / `failure_reason` 是否更细分；
- 是否仍出现 `invalid_response`；
- 是否仍出现 `missing_preview_advisory`。

仍不得预设真实 runtime 一定成功。如果 enabled 场景仍出现 `missing_preview_advisory`，必须记录为 normalization runtime 缺口未闭环，不得现场修改代码，不得扩大测试范围。

## 3. runtime smoke 目标

后续 Step 38 runtime smoke 的目标是验证：

- `/local-llm/preview-safe` 在 enabled 场景下是否仍能进入 default real transport；
- enabled 场景是否 `calls_ollama=true`；
- 真实 `qwen3:0.6b` response 是否可生成 bounded advisory；
- suggestions / risk_notes 是否受控；
- thinking-only 或 response 为空时是否能形成 controlled fallback 或 controlled failure；
- `invalid_response / missing_preview_advisory` 是否已改善；
- 所有场景是否仍保持 `preview_only=true`；
- 所有场景是否仍保持 `no_write=true`；
- 所有场景是否仍保持 `affects_generation=false`；
- 所有场景是否仍保持 `affects_export=false`；
- 是否不触发 `/generate`；
- 是否不触发 `/export_docx`；
- 是否不触发 `/review/apply`；
- 是否不写 `output/job/export`。

本计划不执行 runtime smoke。真实 runtime 验证必须等待 Step 38 单独授权。

## 4. runtime smoke 前置条件

后续真正执行 Step 38 前必须满足：

- 当前工作区 clean；
- HEAD 必须等于 Step 37 plan refresh 标签；
- 不允许修改代码；
- 不允许修改 tests；
- 不运行 pytest；
- 2号窗口仅允许运行 `ollama serve`；
- 如 `127.0.0.1:11434` 已有既有 listener，可复用并记录 PID，不得重复启动；
- 不允许下载模型；
- 不允许 pull 模型；
- 先检查 `GET http://127.0.0.1:11434/api/tags`；
- 本地模型必须已存在，优先使用 `qwen3:0.6b`；
- 如模型不存在，立即停止，不得 pull；
- FastAPI 只能监听 `127.0.0.1` 的临时端口，建议使用 `18753`；
- 只允许请求 `/local-llm/preview-safe`；
- 不得请求 `/generate`；
- 不得请求 `/export_docx`；
- 不得请求 `/review/apply`；
- 不得直接请求 Ollama `/api/generate`，除非后续单独授权。

如果发现工作区不 clean、HEAD 与 Step 37 标签不一致、模型缺失、端口异常、或需要修改代码/tests 才能继续，Step 38 必须立即停止并报告。

## 5. runtime smoke 环境变量设计

后续 Step 38 应至少覆盖 3 个场景。

### disabled 场景

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- stable disabled；
- `calls_ollama=false`；
- 不构造 default real transport；
- 不访问 Ollama generate path；
- 不写盘。

### adapter-off 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

预期：

- stable fake-only 或 controlled non-real path；
- `calls_ollama=false`；
- 不构造 default real transport；
- 不访问 Ollama generate path；
- 不写盘。

### real-Ollama enabled 场景

```bash
export ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
export ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
export ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
```

只读检查代码确认的 safe endpoint real transport 相关环境变量为：

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED`
- `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`
- `ZDOC_OLLAMA_PREVIEW_MODEL`
- `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`

代码只读检查未发现 safe endpoint real transport path 使用 host 或 temperature 环境变量。当前 default real transport base URL 固定限制为：

```text
http://127.0.0.1:11434
```

当前代码默认边界为：

- timeout 默认 `10.0` 秒；
- timeout 最大 `30.0` 秒；
- `num_predict` 默认 `256`；
- `num_predict` 最大 `768`；
- advisory 最大 `1200` 字符；
- thinking fallback 最大 `360` 字符；
- suggestions / risk_notes 最多 `3` 条；
- 每条 suggestions / risk_notes 最大 `220` 字符。

后续 Step 38 可设置保守运行参数：

```bash
export ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
export ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

如 runtime 前代码已有变更，必须再次只读核验实际环境变量名称和默认边界。

## 6. runtime smoke 请求边界

后续 Step 38 仅允许：

```text
GET http://127.0.0.1:11434/api/tags
POST http://127.0.0.1:18753/local-llm/preview-safe
```

明确禁止：

- 直接请求 `POST http://127.0.0.1:11434/api/generate`；
- 请求 `/generate`；
- 请求 `/export_docx`；
- 请求 `/review/apply`；
- 请求任何外部 API；
- 写 `output/job/export`；
- 触发正式文档生成；
- 触发正式导出；
- 写回正式章节；
- 接 ZBid 写回。

Step 38 对 Ollama `/api/generate` 的触达只能通过 `/local-llm/preview-safe` 间接发生，并且必须以 safe endpoint 响应字段为证据。

## 7. smoke payload 设计

当前 `backend/app/routers/local_llm_preview_safe.py` 只读检查确认，endpoint 允许字段为：

```text
context_summary
request_id
section_text
section_title
```

推荐最小 payload：

```json
{
  "request_id": "zdoc-step38-enabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "Please provide one short preview advisory and up to two suggestions for this minimal local runtime smoke text. This is only for preview-only validation.",
  "context_summary": "runtime smoke only; preview advisory; no write; no generation"
}
```

payload 要求：

- 使用最小、非真实投标正文内容；
- 不含敏感项目资料；
- 只用于 preview advisory；
- 字段与当前 endpoint 实现兼容；
- 尽量让模型能输出明确 advisory；
- 不得要求模型生成正式章节正文；
- 不得要求模型写文件；
- 不得包含 `content`、`output`、`job`、`export_path`、`docx_path`、`markdown_path`、`json_path` 等正式输出字段；
- 不得造成生成链或导出链触发。

三组场景可仅调整 `request_id`，其余 payload 保持一致，以便对比 disabled、adapter-off 和 enabled 行为。

## 8. 应记录的 smoke 结果字段

后续 Step 38 smoke report 必须记录：

- 当前目录；
- 当前分支；
- 开始前 HEAD；
- 结束后 HEAD；
- git status；
- Ollama listener 处理方式；
- Ollama PID；
- FastAPI PID；
- 监听端口；
- `/api/tags` HTTP 状态；
- 本地模型列表摘要；
- 使用模型名；
- disabled 场景响应摘要；
- adapter-off 场景响应摘要；
- enabled 场景响应摘要；
- enabled 场景是否 `calls_ollama=true`；
- enabled 场景是否 `status=ok`；
- enabled 场景是否仍出现 `missing_preview_advisory`；
- enabled 场景是否仍出现 `invalid_response`；
- enabled 场景是否返回 advisory；
- advisory 长度；
- suggestions 数量；
- risk_notes 或 warnings 数量；
- 是否出现 thinking fallback；
- `preview_mode`；
- `content_source`；
- `source`；
- `model`；
- `real_transport_enabled`；
- `fake_transport_only`；
- `error_type`；
- `reason` 或 `failure_reason`；
- 是否 `preview_only=true`；
- 是否 `no_write=true`；
- 是否 `affects_generation=false`；
- 是否 `affects_export=false`；
- 是否请求 `/generate`：必须为否；
- 是否请求 `/export_docx`：必须为否；
- 是否请求 `/review/apply`：必须为否；
- 是否写 `output/job/export`：必须为否；
- 所有服务进程是否停止；
- 端口是否无监听。

enabled 场景如返回 `status=ok`，报告只记录 advisory 摘要、长度、suggestions 数量、risk_notes 数量和分类字段，不应大量复制真实模型输出。

## 9. 成功判定标准

后续 Step 38 runtime smoke 成功标准：

- disabled 场景 stable disabled，`calls_ollama=false`；
- adapter-off 场景 stable fake-only 或 controlled non-real，`calls_ollama=false`；
- enabled 场景继续触发 real transport，`calls_ollama=true`；
- enabled 场景不再返回 `missing_preview_advisory`；
- enabled 场景不再返回 `invalid_response`，或若返回 failure，必须 `failure_reason` 更细分且受控；
- enabled 场景理想结果为 `status=ok` 且 advisory 存在；
- enabled 场景若走 thinking fallback，必须可通过 `preview_mode`、`content_source`、risk_notes 或等价字段识别；
- suggestions 数量不超过上限；
- risk_notes 或 warnings 数量不超过上限；
- 所有场景保持 preview-only/no-write；
- 不触发正式生成链；
- 不触发正式导出链；
- 不写 `output/job/export`；
- 服务结束后端口清理完成。

如果 enabled 场景返回 `status=ok`，只能证明 preview advisory runtime 层进一步可用，不能证明质量评测层、正式生成链、DOCX 导出或 ZBid 写回可接入。

## 10. 可接受失败标准

如果 enabled 场景失败，也可接受为“受控失败”，条件是：

- 返回 controlled failure；
- 不抛未处理异常；
- 不写盘；
- 不触发生成链；
- 不触发导出链；
- 不拉取模型；
- 不下载模型；
- 不修改正式正文；
- 能明确记录 `error_type` / `failure_reason`；
- 如 `calls_ollama=true` 但模型返回空 response / empty thinking / timeout，必须归类；
- 如仍为 `missing_preview_advisory`，必须记录为 runtime normalization 未闭环。

可接受的 controlled failure 示例包括：

- `empty_response_and_thinking`；
- `malformed_json`；
- `malformed_response`；
- `normalization_failure`；
- `timeout`；
- `transport_failure`；
- `model_unavailable`；
- `ollama_unreachable`；
- 仍未闭环的 `missing_preview_advisory`。

所有 controlled failure 都必须同时满足 no-write、no-generation、no-export、no-ZBid-writeback 边界。

## 11. 不可接受失败标准

以下结果不可接受：

- 未处理异常导致服务崩溃；
- 写入 `output/job/export`；
- 触发 `/generate`；
- 触发 `/export_docx`；
- 触发 `/review/apply`；
- 下载模型；
- pull 模型；
- 访问外网；
- 修改代码/tests；
- 将 preview advisory 写入正式章节；
- 影响正式 DOCX 导出；
- 影响 ZBid 写回；
- 为了得到 `status=ok` 掩盖真实 failure。

如果出现不可接受失败，Step 38 必须停止并记录，不得扩大测试范围，不得现场修代码。

## 12. output/job/export 写入检查

后续 Step 38 必须在 smoke 前后检查：

- `output/`
- `job/`
- `export/`

如目录不存在，记录不存在。

如目录存在，记录 smoke 前后计数或变更状态。

不得主动写入这些目录，不得为检查目的创建这些目录，不得把 response、payload、日志或模型输出保存到这些目录。

## 13. 进程与端口清理要求

后续 Step 38 必须：

- 记录 FastAPI PID；
- 记录 Ollama PID；
- 每个 FastAPI 场景完成后停止本步启动的 FastAPI；
- 本步结束前确认 `127.0.0.1:18753` 无监听；
- 若 Ollama 是本步启动，则本步结束前停止；
- 若 Ollama 是既有用户进程，不得擅自停止，但必须记录 PID 和原因；
- 不得留下僵尸服务进程。

建议每个 FastAPI 场景独立启动并停止，避免环境变量串场。若复用同一端口，必须确认上一场景进程已退出后再启动下一场景。

## 14. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但 Step 37 / Step 38 仍只属于 preview advisory runtime 验证阶段。不得因为 runtime smoke 返回 advisory 就直接接正式生成链。

后续仍需：

- 质量评测层；
- shadow generation；
- 人工确认写回；
- 导出一致性校核；
- ZBid 写回隔离；
- 回滚机制。

preview advisory runtime smoke 成功只能作为后续质量评测层设计的前置证据，不能替代正式链路准入。

## 15. 风险与回滚

主要风险如下：

- 风险 1：真实 runtime response 与 fake fixture 仍不一致；
- 风险 2：真实模型输出过短、空白或不稳定；
- 风险 3：normalizer 把低质文本包装为 advisory；
- 风险 4：thinking fallback 被误解为正式正文；
- 风险 5：runtime smoke 误判 `status=ok` 等于可进入正式生成链；
- 风险 6：用户误以为 preview advisory 已写入正式方案；
- 风险 7：为追求 runtime 成功而扩大请求范围；
- 风险 8：服务进程或端口未清理干净。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

- 保留 disabled 路径；
- 保留 adapter-off 路径；
- 保留 fake-only 路径；
- 保留 no-write / preview-only guard；
- 出现异常时不得扩大到正式链路。

## 16. 下一步建议

下一步建议为 ZDoc Step 38：preview advisory normalization runtime smoke + smoke report。

该步骤必须单独授权；如需启动 Ollama，只能由 2号窗口运行 `ollama serve` 或复用既有本地 listener；仍不得进入质量评测层、正式生成链、DOCX 导出或 ZBid 写回。
