# ZDoc real-Ollama preview safe endpoint runtime smoke review and invalid response gap design

## 1. 阶段背景

本阶段执行 ZDoc Step 33：real-Ollama default transport runtime smoke review + invalid_response gap design。

前序阶段事实如下：

- Step 29 已完成 default real transport fake-only implementation + deterministic tests；
- Step 30 已完成 default real transport fake-stage review；
- Step 31 已完成 runtime smoke plan refresh；
- Step 32 已完成 default real transport runtime smoke。

Step 32 的关键结果为：

- disabled 场景 stable disabled；
- adapter-off 场景 fake-only 正常；
- enabled 场景已触发 default real transport；
- `calls_ollama=true`；
- `real_transport_enabled=true`；
- 不再出现 `fake_transport_required`；
- 但返回 `status=failure`、`error_type=invalid_response`、`reason=missing_preview_advisory`。

因此，当前阶段不再聚焦 default real transport wiring 是否接通，而是聚焦真实 runtime response 为什么未形成可用 preview advisory。

本步为 docs-only 复盘与缺口设计步骤，不修改代码，不修改 tests，不运行 pytest，不启动服务，不运行 Ollama，不运行 `ollama serve`。

## 2. Step 32 已证明的事实

Step 32 已证明以下事实：

- Ollama listener 可达；
- `GET http://127.0.0.1:11434/api/tags` 返回 HTTP `200`；
- `/api/tags` 响应为有效 JSON；
- 本地模型列表包含 `qwen3:0.6b`；
- `/local-llm/preview-safe` enabled 场景已进入 real transport path；
- `fake_transport_required` 缺口已被消除；
- enabled 场景返回 `calls_ollama=true`；
- enabled 场景返回 `real_transport_enabled=true`；
- runtime 未触发 `/generate`；
- runtime 未触发 `/export_docx`；
- runtime 未触发 `/review/apply`；
- 未写 `output/`、`job/`、`export/`；
- FastAPI 进程已停止；
- 端口 `18752` 已释放；
- 既有 Ollama listener PID `14236` 未被擅自停止。

Step 32 同时证明 safe endpoint 在 runtime 场景仍保持：

- `preview_only=true`；
- `no_write=true`；
- `affects_generation=false`；
- `affects_export=false`。

## 3. Step 32 尚未证明的事项

Step 32 尚未证明以下事项：

- 真实模型未返回可用 advisory；
- `status=ok` 尚未在 real runtime enabled 场景证明；
- `suggestions` 为空；
- `advisory` 未形成；
- 真实模型输出质量未验证；
- 真实模型输出格式与 normalizer 期望之间存在缺口；
- 尚未证明本地模型可稳定生成技术标可用正文；
- 尚未证明本地模型可稳定生成章节改写内容；
- 尚未进入质量评测层；
- 尚未进入 shadow generation；
- 尚未进入人工确认写回；
- 尚未进入 DOCX 导出；
- 尚未进入 ZBid 写回。

因此，`calls_ollama=true` 只能证明 default real transport runtime path 已触发，不能证明 real-Ollama preview advisory 已可用。

## 4. 新缺口定义

缺口名称：`invalid_response / missing_preview_advisory`

缺口性质：

- 不是 Ollama 不可达；
- 不是本地模型不存在；
- 不是 `fake_transport_required`；
- 不是 endpoint 路由未通；
- 不是双开关 guard 未生效；
- 而是 real transport runtime 返回内容未被 normalization 层解析为有效 preview advisory。

换言之，当前核心问题已经从 transport wiring 缺口，转为真实模型输出格式、prompt 约束、response parsing、bounded advisory fallback 之间的兼容缺口。

## 5. 可能原因分析

基于 Step 32 报告和当前代码只读检查，可能原因包括：

- prompt 未明确要求模型输出可直接作为 preview advisory 的短文本；
- prompt 未明确禁止仅输出 thinking 或空 response；
- prompt 未要求固定字段、固定格式或明确的 advisory 开头；
- model response 字段为空或非预期；
- 模型输出可能在 `thinking` 字段而非 `response` 字段；
- 当前 normalizer 只从 `response`、`message.content`、`advisory` 中提取文本；
- 当前 normalizer 未读取独立的 `thinking` 字段；
- 当前 normalizer 未对真实 runtime response 做摘要 fallback；
- runtime 输出格式与 fake transport fixture 不一致；
- fake transport tests 中的 thinking-only 场景是把 `<think>...` 放在 `response` 字段，而不一定覆盖真实 Ollama 单独 `thinking` 字段；
- `qwen3:0.6b` 在短 prompt、小输出限制下可能返回空内容；
- smoke payload 过短，section context 不足，导致模型输出不足；
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128` 可能不足以形成可用 advisory；
- `ZDOC_OLLAMA_PREVIEW_TIMEOUT=10` 可能对冷启动或慢模型过紧；
- generate options 未显式约束 temperature 或输出格式；
- parser 未做 response / thinking / message.content / advisory 之外的 fallback；
- bounded advisory 策略未覆盖真实 runtime 格式；
- 为避免保存完整模型输出，当前实现可能没有足够 runtime response 摘要用于定位格式差异。

以上均为只读推断，尚未进入代码修改。

## 6. 缺口定位层级

### prompt 构造层

当前 prompt 目标是让模型返回 preview-only advisory suggestions，但还不够严格。后续可能需要明确：

- 只输出简短 preview advisory；
- 不输出最终正文；
- 不输出完整 thinking；
- 若无法判断，输出受控的简短说明；
- 输出语言、长度和结构应稳定。

### payload normalization 层

当前 safe endpoint payload 是最小 smoke payload，字段包括：

- `section_title`
- `section_text`
- `context_summary`
- `request_id`

最小 payload 适合 smoke，但可能不足以诱导模型形成有效 advisory。后续需要在不引入真实投标内容和不触发正式链路的前提下，设计更稳定的 preview-only sample payload。

### Ollama generate options 层

当前可控参数包括：

- `ZDOC_OLLAMA_PREVIEW_TIMEOUT`
- `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT`

Step 32 使用了短 timeout 和小 num_predict。后续需要设计保守但足够形成 preview advisory 的参数边界，同时继续禁止下载、pull、外网访问和正式写入。

### transport response 解析层

default real transport 读取 Ollama JSON response，并传入 `normalize_zdoc_ollama_response`。如果真实 response 是 object 但没有可提取文本，就会进入 `missing_preview_advisory`。

后续需要用 fake fixture 模拟真实 runtime-like response，而不是依赖真实 Ollama 才发现格式差异。

### `normalize_zdoc_ollama_response`

当前 normalizer 的主要取值顺序为：

1. `raw_response["response"]`
2. `raw_response["message"]["content"]`
3. `raw_response["advisory"]`

如果三者均为空，则返回：

```text
status=failure
error_type=invalid_response
reason=missing_preview_advisory
```

后续需要设计是否引入更多受控 fallback，例如独立 `thinking` 字段、非结构化文本摘要、bounded failure advisory，但不能为了追求 `status=ok` 而掩盖真实 failure。

### thinking-only fallback 层

现有 deterministic tests 覆盖了 `response` 字段中包含 `<think>...` 的 bounded preview，但未必覆盖真实 runtime 把 thinking 放在独立字段的情况。

后续需要区分：

- `response` 中含 thinking；
- 独立 `thinking` 字段非空；
- `message.content` 非空；
- 全部为空。

thinking-only 不得被完整保存，不得被当作正式正文。

### endpoint response schema 映射层

endpoint metadata 已把 adapter 结果映射为 safe endpoint response，并保留 no-write / preview-only 字段。后续若 normalizer 增强，endpoint 层仍必须保持：

- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`

### tests fixture 与 runtime response 差异层

Step 29 deterministic tests 已覆盖 fake success、empty response、thinking-only、transport exception、builder failure 等场景，但 Step 32 暴露了真实 runtime response 与 fixture 的差异仍不足。

后续应先从 fake fixture 层补齐 runtime-like response variants，再进入 runtime smoke。

## 7. 后续设计目标

后续设计目标如下：

- real transport runtime enabled 场景能够返回 `status=ok` 或明确的 controlled failure；
- 若模型返回普通 `response`，应生成 bounded preview advisory；
- 若模型返回 `message.content`，应生成 bounded preview advisory；
- 若模型返回 `advisory`，应生成 bounded preview advisory；
- 若模型只返回 `thinking`，应按受控策略生成 bounded preview，不保存完整 thinking；
- 若模型返回空 response，应明确 `failure_reason`；
- 若模型返回 malformed JSON，应返回 controlled failure；
- 若模型返回非结构化文本，应转为受控 advisory 或 controlled failure；
- 所有结果保持 `preview_only=true`；
- 所有结果保持 `no_write=true`；
- 不写正式正文；
- 不触发正式生成链；
- 不触发正式导出链；
- 不接 ZBid 写回。

后续不能把“任何非空模型输出”都直接提升为 `status=ok`。只有符合 preview-only、bounded、可解释边界的文本才应作为 advisory。

## 8. 后续实现方向设计

后续可能需要设计或实现以下方向：

- 增强 prompt，使模型明确输出短 advisory；
- prompt 中明确禁止输出正式正文、完整 thinking、导出内容或写回指令；
- 增加 runtime response 摘要采样，但不得保存完整模型输出；
- 采样只记录字段存在性、长度、截断摘要和分类，不记录完整内容；
- 增强 normalizer 对真实 Ollama response 的兼容；
- 增强 normalizer 对 thinking-only 的兼容；
- 明确 `response`、`thinking`、`message.content`、`advisory` 等字段处理优先级；
- 增加 bounded fallback advisory；
- 增加 `error_type` / `failure_reason` 细分；
- 区分 `empty_response`、`thinking_only_response`、`malformed_response`、`missing_preview_advisory`；
- 增加 fake fixture 覆盖真实 runtime 格式；
- 保持 deterministic tests 不依赖真实 Ollama；
- 保持 no-write 和 preview-only 不变；
- 保持 disabled / adapter-off / fake-only path 不回归。

后续实现仍应坚持 fake transport / monkeypatch / dependency injection 先行，不应直接把 runtime smoke 当作开发调试循环。

## 9. 必须补充的 deterministic tests 设计

后续实现前必须补充或调整 deterministic tests，至少包括：

- real runtime-like response 字段为空但 `thinking` 非空；
- `response` 非空普通文本；
- `response` 为 JSON 文本；
- `response` 为非 JSON 技术建议文本；
- `response` 为空且 `thinking` 为空；
- `message.content` 非空；
- `advisory` 非空；
- malformed response；
- missing preview advisory；
- bounded advisory fallback；
- invalid_response 分类；
- thinking-only 不保存完整 thinking；
- thinking-only 不写正式正文；
- no-write / preview-only 恒定；
- 不触发 `/generate`；
- 不触发 `/export_docx`；
- 不触发 `/review/apply`；
- 不写 `output/`、`job/`、`export/`；
- disabled / adapter-off 既有行为不回归；
- default real transport builder fake 替身仍不访问真实 `127.0.0.1:11434`。

这些 tests 必须保持 deterministic，不得依赖真实 Ollama 是否运行，不得运行 `ollama serve`，不得访问外网，不得下载或 pull 模型。

## 10. 后续 runtime 重新验证策略

后续不能直接扩大 runtime 测试，必须按以下顺序推进：

1. docs-only 缺口设计；
2. fake-only deterministic implementation；
3. deterministic tests；
4. implementation stage review；
5. runtime smoke plan refresh；
6. runtime smoke；
7. runtime smoke review。

不得跳步进入正式生成链。

在完成 deterministic tests 之前，不应反复启动真实 runtime 做试错。runtime smoke 应继续保持单独授权、loopback-only、no-write、no-export、no-ZBid 的边界。

## 11. 与正式生成链接入目标的关系

最终目标是本地模型稳定、高质量参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但当前仍处于 real transport preview advisory 解析缺口阶段。只有当以下条件满足后，才可进入正式链设计：

- preview advisory 能稳定形成；
- preview advisory 有质量评测层；
- shadow generation 可控；
- 人工确认写回机制成熟；
- 导出一致性校核完成；
- ZBid 写回隔离充分；
- 回滚路径清晰。

Step 33 不得被解释为正式生成链已具备接入条件。

## 12. 风险与回滚

主要风险如下：

- 风险 1：为解决 advisory 缺口而过度放宽 normalizer，导致低质输出进入系统；
- 风险 2：thinking 内容被完整保存或误用为正式正文；
- 风险 3：模型输出不稳定；
- 风险 4：为追求 `status=ok` 而掩盖真实 failure；
- 风险 5：后续误把 preview advisory 当正式生成结果；
- 风险 6：未来接正式链时缺少质量门禁；
- 风险 7：后续 runtime response 采样若边界不清，可能记录过多模型输出内容。

回滚措施：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`；
- 保留 disabled / adapter-off / fake-only 路径；
- 保留 fake transport deterministic tests；
- 若 runtime smoke 再次失败，记录 controlled gap，不扩大到正式链路；
- 不删除 fake-only 行为。

兜底措施：

- `ZDOC_LOCAL_LLM_PREVIEW_ENABLED` 默认关闭；
- adapter 开关未开时不得进入 real transport；
- 所有 preview response 均保持 no-write；
- 所有 failure response 均不得触发正式生成链、导出链或 ZBid 写回。

## 13. 当前阶段结论

Step 32 已证明 default real transport runtime 可触发，但尚未证明真实模型可返回可用 preview advisory。

当前核心缺口已经从 transport wiring 转为 `invalid_response / missing_preview_advisory` 解析与输出约束缺口。

因此，下一阶段不应盲目重复 runtime smoke，也不应直接进入质量评测层或正式生成链。应先围绕 prompt、normalizer、runtime-like fixtures、bounded advisory fallback 和 failure 分类完成 deterministic 设计。

## 14. 下一步建议

下一步建议为 ZDoc Step 34：real-Ollama preview advisory normalization gap guard + deterministic tests design。

不得直接修改代码，不得直接进入质量评测层、正式生成链、DOCX 导出或 ZBid 写回。
