# ZDoc real-Ollama preview safe endpoint bridge fake-only stage review

## 1. 阶段目标回顾

ZDoc Step 23 的目标是：在 default-off、preview-only、no-write 前提下，为 `/local-llm/preview-safe` 实现到 real-preview adapter 的受控桥接代码，并通过 fake transport / monkeypatch / dependency injection 完成 deterministic tests。

该阶段允许受控修改 preview endpoint、adapter helper 和对应测试，但不得依赖真实 Ollama runtime，不得访问真实 `127.0.0.1:11434`，不得启动服务，不得写 `output/job/export`，不得触发正式生成链、导出链或 ZBid 正式写回。

## 2. 实际完成情况

本阶段已经完成以下事项：

- safe endpoint bridge 代码接入；
- 双开关 guard 生效；
- `ZDOC_OLLAMA_PREVIEW_MODEL` 模型指定逻辑受控接入；
- safe endpoint 在 fake transport 成功场景下可返回 `status=ok` 且 `calls_ollama=true`；
- 全部响应仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 未写 `output/job/export`；
- 未触发 `/generate`、`/export_docx`、`/review/apply`。

当前桥接实现仍以 deterministic fake transport 为验证边界。`calls_ollama=true` 在 Step 23 中表示已进入受控 adapter/fake transport 模拟的 Ollama tags/generate 路径，不等同于真实 runtime 已完成端到端接通。

## 3. 修改范围复盘

Step 23 仅修改了以下 4 个文件：

- `backend/app/routers/local_llm_preview_safe.py`
- `backend/zhifei_autoplan/ollama_preview.py`
- `backend/tests/test_local_llm_preview_safe_endpoint.py`
- `backend/tests/test_ollama_preview.py`

Step 23 未新增文件，未修改正式生成链，未修改正式导出链，未修改 ZBid 写回链，未修改模板文件，未写入正式生成结果文件。

## 4. 测试结果复盘

测试命令：

```bash
python3 -m pytest backend/tests/test_ollama_preview.py backend/tests/test_local_llm_preview_safe_endpoint.py -q
```

最终结果：

```text
125 passed in 3.32s
```

已覆盖场景包括：

- disabled；
- adapter-off；
- double-flag + fake tags/generate success；
- missing model；
- empty response；
- thinking-only；
- transport exception；
- invalid payload；
- optional fields omitted；
- no generate/export/apply trigger；
- no output/job/export write。

这些测试全部基于 fake transport、monkeypatch、dependency injection 和 stable fixture payload，不依赖真实 Ollama，不运行 `ollama serve`，不调用外网，不下载或拉取模型。

## 5. 已证明的事实

本阶段已经证明：

- fake transport 下 safe endpoint bridge 行为受控；
- deterministic tests 可稳定覆盖关键路径；
- failure / exception 场景不会失控；
- thinking-only 可生成 bounded preview；
- 不会误写正式正文；
- 不会误触正式生成链和导出链。

同时，safe endpoint 响应继续保留 preview 安全字段和 no-write 元数据，包括 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`，并通过测试证明不会触发正式生成、正式导出或正式写回相关路径。

## 6. 尚未证明的事项

以下事项尚未证明：

- 未启动真实 Ollama；
- 未访问真实 `127.0.0.1:11434/api/tags`；
- 未访问真实 `127.0.0.1:11434/api/generate`；
- 未做 runtime smoke；
- 未验证真实模型 `qwen3:0.6b` 的 safe endpoint 运行时结果；
- 未验证真实 runtime 下 `calls_ollama=true` 的端到端行为；
- 未验证真实模型空响应、thinking-only、异常响应在 runtime 下是否与 fake transport 一致。

因此，本阶段结论不能外推为真实 Ollama runtime 已经可用于 safe endpoint preview。

## 7. 风险复盘

主要风险如下：

- 风险 1：真实 runtime 接入时误触生成链或写盘；
- 风险 2：真实模型输出不稳定；
- 风险 3：thinking-only 被误当正式正文；
- 风险 4：用户误以为 preview advisory 已写入正式方案；
- 风险 5：模型不存在时误触自动拉取。

后续进入 runtime smoke 或真实 `/api/generate` 前，必须继续保留 no-write、preview-only、bounded advisory 和 negative-call guard。

## 8. 回滚边界

回滚边界如下：

- 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 可回退；
- 必须保留 disabled / fake-only 路径；
- 不得删除既有 fake-only 行为；
- 若后续 runtime smoke 出现异常，不得直接扩散到正式生成链。

该回滚方式应优先作为 adapter bridge 的运行时兜底，不应通过删除 safe endpoint 或删除 fake-only 行为来规避风险。

## 9. 当前阶段结论

本阶段仅证明 fake transport deterministic bridge 可用，不代表真实 Ollama runtime `/api/generate` 端到端可用。

Step 23 的成果是为后续 runtime smoke 建立受控代码路径和测试保护网，而不是证明真实模型已经稳定接入正式或准正式生成流程。

## 10. 下一步建议

下一步建议为 ZDoc Step 25：real-Ollama preview safe endpoint runtime smoke 前置设计文档。

不得直接启动 Ollama，不得直接进入 runtime smoke，不得直接接正式生成链、导出链或 ZBid 写回。
