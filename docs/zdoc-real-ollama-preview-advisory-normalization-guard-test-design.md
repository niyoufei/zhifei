# ZDoc preview advisory normalization guard and deterministic tests design

## 1. 阶段背景

本阶段执行 ZDoc Step 34：preview advisory normalization gap guard + deterministic tests design。

前序阶段事实如下：

- Step 32 已证明 default real transport runtime 可触发；
- Step 32 enabled 场景已返回 `calls_ollama=true`；
- Step 32 enabled 场景已返回 `real_transport_enabled=true`；
- Step 32 enabled 场景不再出现 `fake_transport_required`；
- 但 Step 32 enabled 场景返回 `status=failure`、`error_type=invalid_response`、`reason=missing_preview_advisory`；
- Step 33 已归档该缺口，并明确当前核心问题从 transport wiring 转为 preview advisory normalization gap。

Step 34 的目标是锁定 normalization gap 的 guard、测试、允许修改文件、失败分类和后续实现边界。

本步不得实现代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`，不调用外部模型/API，不下载或拉取模型。

## 2. 当前缺口复述

当前事实如下：

- Ollama listener 可达；
- `/api/tags` 已在 Step 32 返回 HTTP `200` 且为有效 JSON；
- 本地模型 `qwen3:0.6b` 存在；
- `/local-llm/preview-safe` enabled 场景已进入 real transport path；
- enabled 场景已证明 `calls_ollama=true`；
- enabled 场景已证明 `real_transport_enabled=true`；
- 问题不在 default real transport wiring；
- 问题集中在真实模型返回内容未被解析为有效 preview advisory；
- 当前不能进入质量评测层；
- 当前不能进入 shadow generation；
- 当前不能进入人工确认写回；
- 当前不能进入 DOCX 导出；
- 当前不能进入 ZBid 写回。

当前 normalizer 只读检查显示，主要取值路径为：

1. `response`；
2. `message.content`；
3. `advisory`。

当这些字段均未形成非空 preview advisory 时，当前返回：

```text
status=failure
error_type=invalid_response
reason=missing_preview_advisory
```

## 3. normalization 目标状态

后续实现完成后的目标状态如下：

- real runtime response 非空普通文本时，可生成 bounded preview advisory；
- real runtime response 为 JSON 文本时，可提取 `advisory` / `suggestions` / `risk_notes`；
- real runtime response 为非 JSON 技术建议文本时，可转为受控 advisory；
- `response` 为空但 `thinking` 非空时，可按受控策略生成 bounded preview；
- `response` 与 `thinking` 均为空时，返回 controlled failure；
- malformed response 不抛未处理异常；
- malformed JSON 不抛未处理异常；
- `missing_preview_advisory` 应细分 `failure_reason`；
- 所有结果保持 `preview_only=true`；
- 所有结果保持 `no_write=true`；
- 所有结果保持 `affects_generation=false`；
- 所有结果保持 `affects_export=false`；
- 不写正式正文；
- 不触发正式生成链；
- 不触发正式导出链；
- 不接 ZBid 写回。

目标不是把所有模型输出都包装成 `status=ok`。只有符合 preview-only、bounded、可解释边界的文本才应进入 advisory；无法满足边界的输出必须保持 controlled failure。

## 4. prompt guard 设计

后续 prompt 构造必须满足：

- 明确要求模型输出短 advisory；
- 明确要求 advisory 是 preview-only；
- 不要求模型生成正式章节正文；
- 不要求模型输出 DOCX；
- 不要求模型输出 Markdown 文件；
- 不要求模型输出导出内容；
- 不要求模型写回；
- 不要求模型替换正式章节；
- 控制输出长度；
- 优先要求结构化字段，如 `advisory`、`suggestions`、`risk_notes`；
- 即使模型不按结构输出，也必须由 normalizer 做 bounded fallback；
- prompt 不得包含敏感项目资料；
- smoke payload 仅使用最小非真实内容；
- prompt 不得诱导调用 `/generate`、`/export_docx`、`/review/apply`；
- prompt 不得要求写 `output/`、`job/`、`export/`。

建议的后续 prompt 约束方向：

- 要求只输出 1 段短 advisory 和最多 3 条 suggestions；
- 明确“不生成正式正文，不写入文档，不导出文件”；
- 明确“如果信息不足，只返回 preview 风险提示”；
- 明确“不要输出完整思考过程”。

这些只是实现方向，本步不修改 prompt 代码。

## 5. response parsing guard 设计

后续 parser / normalizer 应按优先级处理：

1. 标准 `response` 字段；
2. `message.content` 或同类 chat content 字段，如代码中存在；
3. JSON 字符串中的 `advisory` / `suggestions` / `risk_notes`；
4. 普通非 JSON 文本；
5. `thinking` 字段；
6. 空响应 controlled failure；
7. malformed payload controlled failure。

处理要求：

- 不保存完整 thinking；
- 不把 thinking 作为正式正文；
- thinking fallback 只允许形成 bounded preview 或 controlled failure；
- bounded preview 必须截断；
- advisory 必须短文本；
- suggestions 必须数量受限；
- risk_notes 必须数量受限；
- failure 也必须保留 `no_write=true`；
- failure 也必须保留 `preview_only=true`；
- failure 不得穿透到正式生成链；
- 不得为追求 `status=ok` 掩盖真实失败。

字段处理建议：

- `response` 非空且可清洗为短文本：优先作为 advisory；
- `response` 是 JSON 字符串：尝试解析 `advisory`、`suggestions`、`risk_notes`；
- `response` 是普通非 JSON 技术建议文本：按短文本 advisory 处理；
- `message.content` 非空：按同样规则处理；
- `thinking` 非空但 response 为空：只允许截断、标记 fallback，不保存完整 thinking；
- 所有字段均为空：保持 controlled failure。

## 6. bounded advisory 设计

bounded advisory 的输出边界如下：

- `advisory` 必须是短文本；
- `advisory` 必须有最大字符数上限；
- `suggestions` 数量应有上限；
- 每条 `suggestions` 应有最大字符数上限；
- `risk_notes` 数量应有上限；
- 每条 `risk_notes` 应有最大字符数上限；
- 不得输出完整模型长文本；
- 不得输出完整 thinking；
- 不得输出正式章节替换正文；
- 不得写入正式文档；
- 不得触发 DOCX 导出；
- 不得触发 JSON / Markdown 正式导出；
- 不得触发 ZBid 写回；
- 必须标识 `source`；
- 必须标识 `model`；
- 必须准确标识 `calls_ollama`；
- 若来源为 thinking fallback，必须在 `risk_notes` 或 `source` 中体现为受控 fallback。

建议边界：

- `advisory` 沿用或收紧当前 `LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS` 上限；
- `suggestions` 最多 3 条；
- `risk_notes` 最多 3 条；
- thinking fallback 不应直接保留 `<think>` 长内容；
- thinking fallback 应优先转为“模型仅返回推理内容，需人工复核”的 preview 风险说明。

这些边界应先通过 deterministic tests 固化，再进入 runtime smoke。

## 7. failure 分类设计

后续 `error_type` / `failure_reason` 应细分：

- `empty_response`
- `empty_response_and_thinking`
- `missing_preview_advisory`
- `malformed_response`
- `malformed_json`
- `thinking_only_fallback`
- `model_unavailable`
- `transport_failure`
- `timeout`
- `normalization_failure`

分类建议如下：

- `empty_response`：`response` 为空，但仍需检查 `message.content`、`advisory`、`thinking`；若均不可用则 controlled failure。
- `empty_response_and_thinking`：`response` 与 `thinking` 均为空，必须 controlled failure。
- `missing_preview_advisory`：有 response object，但没有可形成 advisory 的字段，必须 controlled failure。
- `malformed_response`：raw response 类型不符合预期，必须 controlled failure。
- `malformed_json`：JSON 字符串无法解析，但文本本身可用时可转普通 advisory；完全不可用时 controlled failure。
- `thinking_only_fallback`：可转为 bounded advisory，但必须标识 fallback 风险，不得保存完整 thinking。
- `model_unavailable`：必须 failure，不得 pull 模型。
- `transport_failure`：必须 failure，不得穿透到正式链。
- `timeout`：必须 failure 或受控 timeout response，不得重试扩大范围。
- `normalization_failure`：normalizer 内部异常必须被捕获并转 controlled failure。

所有 failure 均不得写盘，均不得触发正式生成链、导出链或 ZBid 写回。

## 8. deterministic tests 设计

后续实现时必须补充或调整 deterministic tests，至少包括：

- fake runtime response 普通文本；
- fake runtime response JSON 文本；
- fake runtime response 非 JSON 技术建议文本；
- fake runtime response 空 `response` + 非空 `thinking`；
- fake runtime response 空 `response` + 空 `thinking`；
- malformed JSON；
- missing advisory 字段；
- `message.content` 字段，如代码支持；
- thinking-only fallback 不保存完整 thinking；
- bounded advisory 截断；
- `suggestions` 数量上限；
- `risk_notes` 数量上限；
- `invalid_response` 分类；
- `empty_response` 分类；
- `empty_response_and_thinking` 分类；
- `thinking_only_fallback` 分类；
- normalization exception controlled failure；
- no-write / preview-only 恒定；
- `affects_generation=false` 恒定；
- `affects_export=false` 恒定；
- 不触发 `/generate`；
- 不触发 `/export_docx`；
- 不触发 `/review/apply`；
- 不写 `output/`、`job/`、`export/`。

测试实现要求：

- 使用 fake transport；
- 使用 monkeypatch；
- 使用 dependency injection；
- 使用 stable fixture payload；
- 不启动服务；
- 不运行 Ollama；
- 不运行 `ollama serve`；
- 不真实访问 `127.0.0.1:11434`；
- 不访问外网；
- 不下载或拉取模型。

## 9. fake fixture 与 runtime response 对齐设计

现有 fake fixture 不能只覆盖理想结构。后续必须补充更接近真实 Ollama runtime 的 fixture。

fixture 应覆盖：

- `response` 字段为空；
- `thinking` 字段存在；
- `response` 为普通文本；
- `response` 为 JSON 字符串；
- `response` 为 malformed JSON；
- `message.content` 非空；
- `advisory` 非空；
- `error` 字段存在；
- raw response 非 dict；
- response dict 中字段类型异常。

fixture 设计要求：

- deterministic tests 不得真实访问 `127.0.0.1:11434`；
- 不得依赖本机 Ollama 状态；
- 不得下载或拉取模型；
- 不得把 fake fixture 写入 `output/`、`job/`、`export/`；
- 不得保存完整真实模型输出；
- runtime-like fixture 只模拟字段结构、长度、空值和分类。

后续若需要记录真实 runtime response 的结构，也只能在单独授权 runtime smoke 中记录字段存在性、类型、长度和截断摘要，不能保存完整模型长文本。

## 10. 允许修改文件边界

后续 Step 35 实现阶段原则上只允许修改：

- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`

如 endpoint response schema 必须调整，才允许修改：

- `backend/app/routers/local_llm_preview_safe.py`

不得新增文件。

如确需新增测试文件，必须先经 ChatGPT 单独审核，不得在实现阶段擅自新增。

## 11. 禁止触碰范围

后续实现不得修改：

- 正式生成链；
- 正式导出链；
- ZBid 写回链；
- `output/`；
- `job/`；
- `export/`；
- 正式模板文件；
- 正式生成结果文件；
- 与 preview 无关的 UI 主流程；
- 任何会改变正式文档生成结果的代码。

不得新增依赖，不得引入外部模型/API，不得把 preview advisory 接入正式写回。

## 12. 后续 runtime 重新验证前提

后续完成 fake-only deterministic implementation 后，必须按顺序：

1. Step 35：normalization fake-only implementation + deterministic tests；
2. Step 36：implementation stage review；
3. Step 37：runtime smoke plan refresh；
4. Step 38：runtime smoke；
5. Step 39：runtime smoke review。

不得跳步进入质量评测层。

不得跳步进入正式生成链。

不得在 Step 35 直接启动 Ollama 或 FastAPI runtime smoke。

## 13. 与最终正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但当前仍处于 preview advisory normalization 缺口阶段。正式链前仍必须完成：

- preview advisory 稳定；
- 质量评测层；
- shadow generation；
- 人工确认写回；
- DOCX 导出一致性校核；
- ZBid 写回隔离；
- 回滚机制。

即便后续 preview advisory runtime 成功，也不能直接推导为正式生成链可用。

## 14. 风险与回滚

主要风险如下：

- 风险 1：为消除 `invalid_response` 过度放宽 normalizer；
- 风险 2：低质模型输出被包装成 advisory；
- 风险 3：thinking 内容被完整保存或误用；
- 风险 4：为追求 `status=ok` 掩盖 failure；
- 风险 5：future formal generation 缺少质量门禁；
- 风险 6：用户误以为 preview advisory 已写入正式方案；
- 风险 7：runtime-like fixture 与真实 runtime 格式仍存在偏差；
- 风险 8：后续 prompt 增强误引导模型输出正式正文。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- 保留 fake transport deterministic tests；
- 出现异常时记录 controlled failure，不扩大到正式链路。

兜底措施：

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` 默认关闭；
- adapter-off 场景保持 fake-only 或 controlled non-real path；
- preview response 始终 no-write；
- failure response 不得穿透到正式生成链。

## 15. 当前阶段结论

本阶段仅完成 preview advisory normalization gap 的 guard + deterministic tests 设计。

本阶段未修改代码，未修改 tests，未运行测试，未启动服务，未运行 Ollama，未运行 `ollama serve`，未证明真实 runtime advisory 可用。

当前结论是：Step 32 已证明 real transport runtime 可触发，但 preview advisory normalization 仍需先通过 fake-only deterministic implementation 固化 parser、fallback、failure 分类和 no-write guard。

## 16. 下一步建议

下一步建议为 ZDoc Step 35：preview advisory normalization fake-only implementation + deterministic tests。

不得直接进入 runtime smoke、质量评测层、正式生成链、DOCX 导出或 ZBid 写回。
