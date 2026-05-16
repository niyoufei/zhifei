# ZDoc preview advisory normalization fake-only implementation stage review

## 1. 阶段目标回顾

ZDoc Step 35 的目标是：在不启动真实 Ollama、不访问 `127.0.0.1:11434` 的前提下，通过 fake fixture / monkeypatch / dependency injection 修复 preview advisory normalization 缺口，使 runtime-like response 能被受控转换为 bounded preview advisory 或 controlled failure。

该阶段承接 Step 32 runtime smoke 暴露的缺口：default real transport 已触发，`calls_ollama=true`、`real_transport_enabled=true`，但真实 runtime enabled 场景返回：

```text
status=failure
error_type=invalid_response
reason=missing_preview_advisory
suggestions=0
```

Step 35 的目标不是证明真实 Ollama runtime 已可用，而是先在 deterministic tests 中固化 normalizer 的边界、fallback、failure 分类和 no-write guard。

## 2. 实际完成情况

本阶段已经完成：

- 普通文本 `response` 可转为 bounded advisory；
- JSON 文本 `response` 可提取 `advisory` / `suggestions` / `risk_notes`；
- 非 JSON 技术建议文本可作为 `text_fallback` advisory；
- `message.content` 字段已纳入兼容路径；
- 空 `response` + 非空 `thinking` 可生成 `thinking_only_fallback`；
- 空 `response` + 空 `thinking` 返回 controlled failure；
- malformed JSON 返回 controlled failure；
- normalization 内部异常返回 controlled response；
- `suggestions` 上限控制已生效；
- `risk_notes` 上限控制已生效；
- `advisory` 截断边界已生效；
- thinking excerpt 截断边界已生效；
- disabled / adapter-off / default builder 既有行为未回归；
- no-write / preview-only 边界保持稳定。

当前 normalizer 继续优先处理普通可用内容，同时增加了 runtime-like response 的兼容和分类：

- `preview_mode=structured_json`：从 JSON 文本中提取结构化 advisory；
- `preview_mode=text_fallback`：把普通非 JSON 文本作为受控 advisory；
- `preview_mode=thinking_only_fallback`：只保留截断的 thinking fallback，并通过 `risk_notes` 标识风险；
- `reason=empty_response_and_thinking`：response 与 thinking 均为空时保持 controlled failure；
- `reason=malformed_json`：JSON-like 文本解析失败时保持 controlled failure；
- `reason=normalization_failure`：normalizer 异常时保持 controlled failure。

## 3. 修改范围复盘

Step 35 实际修改文件为：

- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`

范围说明：

- 未修改 `backend/app/routers/local_llm_preview_safe.py`；
- 未新增文件；
- 未修改正式生成链；
- 未修改正式导出链；
- 未修改 ZBid 写回链；
- 未修改模板文件；
- 未修改正式生成结果文件；
- 未写 `output/job/export`；
- 未触发 DOCX / JSON / Markdown 正式导出。

## 4. 测试结果复盘

Step 35 运行的测试命令为：

```bash
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

最终测试结果为：

```text
140 passed in 3.72s
```

已覆盖场景：

- 普通文本 response；
- JSON response；
- 非 JSON 技术建议文本；
- `message.content`；
- thinking fallback；
- 空 response；
- malformed JSON；
- normalization failure；
- default builder 回归；
- no-write guard；
- disabled；
- adapter-off；
- no route trigger；
- no output/job/export write。

测试均为 fake fixture / monkeypatch / dependency injection，不依赖真实 Ollama runtime，不启动服务，不访问真实 `127.0.0.1:11434`。

## 5. 已证明的事实

本阶段已经证明：

- fake fixture 下 preview advisory normalization 可控；
- `invalid_response / missing_preview_advisory` 缺口已有 deterministic 修复基础；
- 普通文本、JSON 文本、非 JSON 文本均可进入受控 advisory 或 controlled failure；
- `message.content` 可作为 advisory 来源；
- thinking fallback 不保存完整 thinking；
- thinking fallback 通过 `preview_mode`、`content_source`、`risk_notes` 可追踪；
- advisory、suggestions、risk_notes 均有边界；
- failure / exception 场景不会失控；
- 不会触发 `/generate`、`/export_docx`、`/review/apply`；
- 不会写 `output/job/export`；
- 不会影响正式生成链和导出链。

这些事实只在 deterministic fake-only 测试范围内成立。

## 6. 尚未证明的事项

以下事项尚未证明：

- 未启动真实 Ollama；
- 未运行 `ollama serve`；
- 未启动 FastAPI；
- 未真实访问 `127.0.0.1:11434/api/tags`；
- 未真实访问 `127.0.0.1:11434/api/generate`；
- 未验证 `qwen3:0.6b` 真实 runtime 是否能返回 `status=ok`；
- 未验证真实 runtime 下 advisory 是否可用；
- 未验证真实 runtime 下 suggestions 是否可用；
- 未验证真实 runtime thinking-only 行为；
- 未验证真实模型输出质量；
- 未进入质量评测层；
- 未进入 shadow generation；
- 未进入人工确认写回；
- 未进入 DOCX 导出；
- 未进入 ZBid 写回。

因此，Step 35 不能被解释为真实 Ollama runtime preview advisory 已经可用。

## 7. 当前风险

主要风险如下：

- 风险 1：fake fixture 行为与真实 runtime response 仍可能不一致；
- 风险 2：真实模型输出过短、空白或不稳定；
- 风险 3：normalizer 可能把低质文本包装为 advisory；
- 风险 4：thinking fallback 被误解为正式正文；
- 风险 5：后续 runtime smoke 误判 `status=ok` 等于可进入正式生成链；
- 风险 6：用户误以为 preview advisory 已写入正式方案；
- 风险 7：JSON-like 文本的 malformed 分类可能需要真实 runtime 进一步校准；
- 风险 8：真实模型可能继续输出无效结构，需要后续 prompt / options / payload 设计配合。

## 8. 回滚边界

回滚边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退；
- 保留 disabled / adapter-off / fake-only 路径；
- 保留 fake fixture deterministic tests；
- runtime smoke 异常不得扩散到正式生成链；
- 当前阶段不涉及正式正文写回；
- 当前阶段不涉及 DOCX 导出；
- 当前阶段不涉及 ZBid 写回。

如后续 runtime smoke 出现异常，应记录 controlled gap，不得直接扩大到质量评测层、正式生成链、导出链或 ZBid 写回链。

## 9. 与最终正式生成链接入目标的关系

最终目标是让本地模型稳定、高质量参与正式生成链，包括：

- 正文生成；
- 章节改写；
- DOCX 导出；
- ZBid 写回。

但 Step 35 仍处于 preview advisory normalization fake-only 验证阶段，不能跳过后续必要阶段：

- runtime smoke；
- 质量评测层；
- shadow generation；
- 人工确认写回；
- 导出一致性校核；
- ZBid 写回隔离。

即便后续 runtime smoke 返回 `status=ok`，也只能证明 preview advisory 层进一步可用，不能直接证明正式生成链可接入。

## 10. 当前阶段结论

本阶段仅证明 preview advisory normalization 在 fake fixture deterministic tests 下可控，不代表真实 Ollama runtime advisory 已可用，不代表可进入质量评测层或正式生成链。

当前可以确认的是：

- Step 32 暴露的 `missing_preview_advisory` 问题已有 fake-only deterministic 修复基础；
- response / JSON response / message.content / thinking fallback 等路径已有测试覆盖；
- no-write / preview-only / no-export / no-ZBid 边界保持稳定；
- 后续必须重新做 runtime smoke plan refresh，再单独授权 runtime smoke。

## 11. 下一步建议

下一步建议为 ZDoc Step 37：preview advisory normalization runtime smoke plan refresh，基于 Step 35 normalization 修复更新 runtime smoke 边界。

不得直接启动 Ollama，不得直接进入 runtime smoke，不得进入质量评测层、正式生成链、DOCX 导出或 ZBid 写回。
