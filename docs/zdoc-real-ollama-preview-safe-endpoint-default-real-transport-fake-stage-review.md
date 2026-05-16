# ZDoc real-Ollama preview safe endpoint default real transport fake-only implementation stage review

## 1. 阶段目标回顾

ZDoc Step 29 的目标是：在 default-off、preview-only、no-write 前提下，实现 `/local-llm/preview-safe` safe endpoint 的 default real transport wiring，并通过 fake builder / monkeypatch / dependency injection 完成 deterministic tests。

本阶段要解决的缺口来自 Step 26 runtime smoke：双开关 enabled 场景进入了 safe endpoint real-adapter bridge，但由于默认 runtime 路径缺少 real transport wiring，最终返回：

```text
status=failure
error_type=transport_failure
reason=fake_transport_required
calls_ollama=false
```

Step 29 的实现目标不是直接证明真实 Ollama `/api/generate` runtime 端到端可用，而是先把 default real transport 的 wiring、guard、failure response 和 deterministic tests 固化下来。

## 2. 实际完成情况

本阶段已经完成：

- default real transport builder 接线；
- 双开关 enabled 且 no injected transport 时可进入 default builder；
- deterministic tests 使用 fake builder 替身验证，不访问真实 `127.0.0.1:11434`；
- default builder fake tags + fake generate 成功时返回 `status=ok`、`calls_ollama=true`；
- builder 初始化异常、缺模型、generate 异常均为 controlled failure；
- thinking-only 仍生成 bounded preview；
- 双开关默认路径不再返回 `fake_transport_required`；
- 所有响应仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`。

实现后，`run_zdoc_ollama_preview` 在双开关开启且未传入 injected transport 时，会尝试通过 default builder 构造 loopback-only transports。deterministic tests 中该 builder 被 monkeypatch 为 fake tags / fake generate transport，因此测试没有访问真实本机 Ollama runtime。

当前 `fake_transport_required` 仍保留为 partial injected transport 缺失的特殊 controlled failure，但不再是双开关 enabled 且 no injected transport 的默认结果。

## 3. 修改范围复盘

Step 29 实际修改文件为：

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
- 未写 `output/job/export`。

`backend/app/routers/local_llm_preview_safe.py` 现有 bridge 已经将 `SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT` 和 `SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT` 传入 `run_zdoc_ollama_preview`。当这两个值为 `None` 时，新的 fallback 行为发生在 adapter/helper 层，因此本阶段无需修改 endpoint 文件。

## 4. 测试结果复盘

Step 29 运行的测试命令为：

```bash
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

最终测试结果为：

```text
130 passed in 3.15s
```

已覆盖场景：

- disabled；
- adapter-off；
- injected fake transport；
- no injected transport + default builder fake 替身；
- default builder fake generate success；
- missing model；
- builder init exception；
- generate exception；
- empty response；
- thinking-only；
- invalid payload；
- no route trigger；
- no output/job/export write。

这些测试均为 deterministic tests，通过 fake transport、fake builder、monkeypatch、dependency injection、fail-fast stub 和 write-surface count 检查完成，没有启动服务，没有运行真实 Ollama。

## 5. 已证明的事实

本阶段已经证明：

- deterministic tests 下 default builder wiring 可控；
- 双开关 no injected transport 路径可进入 default builder；
- `fake_transport_required` 不再是双开关默认路径结果；
- failure / exception 场景不会失控；
- no-write / preview-only 边界保持稳定；
- 不会触发 `/generate`、`/export_docx`、`/review/apply`；
- 不会写 `output/job/export`；
- injected fake transport 仍优先于 default builder；
- adapter-off / disabled / fake-only 行为未被删除。

测试中还证明，default builder fake 替身成功路径会使用：

```text
http://127.0.0.1:11434/api/tags
http://127.0.0.1:11434/api/generate
```

但这些 URL 只是 fake transport 的入参校验，不代表真实 runtime 已经被访问。

## 6. 尚未证明的事项

以下事项尚未证明：

- 未启动真实 Ollama；
- 未运行 `ollama serve`；
- 未启动 FastAPI；
- 未真实访问 `127.0.0.1:11434/api/tags`；
- 未真实访问 `127.0.0.1:11434/api/generate`；
- 未验证真实模型 `qwen3:0.6b` 运行时结果；
- 未证明真实 runtime 下 `calls_ollama=true`；
- 未证明真实模型输出质量、稳定性、thinking-only runtime 行为；
- 未证明真实 runtime 下 default builder 的 urllib transport 与 fake builder 行为完全一致。

因此，本阶段不能被解释为真实 Ollama `/api/generate` 端到端已经可用。

## 7. 当前风险

主要风险如下：

- 风险 1：真实 runtime 下 default builder 行为与 fake builder 不一致；
- 风险 2：真实模型输出不稳定；
- 风险 3：thinking-only 输出被误当正式正文；
- 风险 4：模型不存在时误触 pull；
- 风险 5：后续 runtime smoke 误触正式生成链或写盘；
- 风险 6：用户误以为 preview advisory 已写入正式方案。

另一个需要持续关注的风险是：后续如果把 preview advisory 接近正式生成链展示，必须继续明确它只是 preview-only advisory，不得直接改变正式章节内容。

## 8. 回滚边界

回滚边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退到 adapter-off / fake-only path；
- 保留 disabled / adapter-off / fake-only 路径；
- 不得删除 fake transport deterministic tests；
- runtime smoke 出现异常时不得扩散到正式生成链；
- 当前阶段不涉及正式正文写回、DOCX 导出或 ZBid 写回。

如果后续真实 runtime smoke 失败，应先记录 controlled failure 或 runtime gap，不得直接修改正式生成链、导出链或 ZBid 写回链。

## 9. 与最终目标的关系

最终目标是让本地模型稳定、高质量地参与正式生成链，包括正文生成、章节改写、DOCX 导出或 ZBid 写回。

但 Step 29 仍处于 preview-only real transport 底座阶段，不能跳过以下后续阶段：

- runtime smoke；
- 质量评测；
- shadow generation；
- 人工确认写回；
- 导出一致性校核；
- ZBid 写回隔离。

换言之，Step 29 只是为后续真实 runtime smoke 和更高层能力奠定可控基础，不是正式生成链接入完成。

## 10. 当前阶段结论

本阶段仅证明 default real transport wiring 在 fake builder deterministic tests 下可控，不代表真实 Ollama `/api/generate` runtime 端到端已接通。

当前可以确认的是：

- Step 26 暴露的 `fake_transport_required` 默认路径缺口已在代码层通过 default builder wiring 解决；
- fake builder deterministic tests 已覆盖关键 guard 和 failure 场景；
- no-write / preview-only / no-export 边界保持稳定；
- 真实 runtime 仍需后续单独授权 smoke 验证。

## 11. 下一步建议

下一步建议为 ZDoc Step 31：real-Ollama preview safe endpoint runtime smoke plan refresh，基于 Step 29 的实现更新 runtime smoke 边界。不得直接启动 Ollama，不得直接进入 runtime smoke，不得接正式生成链、导出链或 ZBid 写回。
