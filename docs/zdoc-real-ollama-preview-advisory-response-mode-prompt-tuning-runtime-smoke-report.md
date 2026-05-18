# ZDoc response-mode prompt tuning runtime smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 77：response-mode prompt tuning runtime smoke + smoke report。

本步目标是验证 Step 74 后真实 runtime 下 response-mode prompt tuning 是否改善 `thinking_only_fallback` 高依赖问题，并同时确认 adapter-off schema、generated-preview-as-evidence、evidence anchor、quality gate、input-risk 和正式链隔离不回归。

重点观察项如下：

* response-first 是否产生 `response_advisory`；
* JSON-first 是否产生 `json_advisory`；
* text-fallback 是否产生 `text_fallback`；
* `thinking_only_fallback` 频率是否较 Step 70 有改善；
* adapter-off compatible payload 是否受控；
* adapter-off illegal field 是否仍 controlled failure；
* generated-preview-as-evidence / evidence anchor / quality gate / input-risk 是否不回归；
* 所有正式链准入字段是否没有出现 true；
* 是否仍保持 preview-only / no-write；
* 是否未触发正式生成链、导出链、ZBid 写回链。

本步只请求 `/local-llm/preview-safe`。未由 smoke 客户端直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 safe endpoint real adapter 在本地 loopback 内部间接调用。

## 2. 开始前 Git 状态

开始前只读核验结果：

```text
pwd: /Users/youfeini/Desktop/文档生成系统
git status --short: clean
git branch --show-current: main
git rev-parse HEAD: a9e84d730e45f680583c549e32d4d4623dce2cb1
tag: v0.1.135-zdoc-response-mode-prompt-tuning-runtime-smoke-plan-refresh
tag target: a9e84d730e45f680583c549e32d4d4623dce2cb1
git diff --name-only: clean
```

前置条件满足后才继续 runtime smoke。

## 3. Ollama listener 处理方式

开始前检查 `127.0.0.1:11434`，未发现既有 listener。

按本步授权，使用 2号窗口仅运行：

```bash
ollama serve
```

本步启动的 Ollama PID：

```text
23307
```

本步结束前已停止该 Ollama 进程。最终 `127.0.0.1:11434` 无监听。

## 4. Ollama /api/tags 检查结果

允许检查：

```text
GET http://127.0.0.1:11434/api/tags
```

检查结果：

```text
HTTP_STATUS=200
valid_json=true
local_models_count=7
qwen3:0.6b exists=true
```

本步未执行 pull，未下载模型。

## 5. 本地模型摘要

`/api/tags` 返回的本地模型摘要如下：

* `qwen3-next:80b-a3b-instruct-q8_0`
* `qwen3-coder:30b`
* `deepseek-r1:32b`
* `qwen3:30b`
* `qwen3:14b`
* `qwen3:8b`
* `qwen3:0.6b`

本步优先使用并实际使用：

```text
qwen3:0.6b
```

## 6. 使用模型

enabled response-mode prompt tuning 场景设置：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=20
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=160
```

实际响应中 enabled payload 均记录：

```text
model=qwen3:0.6b
calls_ollama=true
source=zdoc_real_ollama_preview_adapter_real_transport
```

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听：

```text
127.0.0.1:18759
```

启动命令：

```bash
/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18759 --log-level warning
```

分场景 PID：

| 场景 | PID | 端口 |
| --- | ---: | ---: |
| disabled | 23385 | 18759 |
| adapter-off | 23387 | 18759 |
| enabled | 23388 | 18759 |

enabled 场景额外环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=20
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=160
```

所有 FastAPI 进程均已停止。最终 `127.0.0.1:18759` 无监听。

## 8. output/job/export 前后状态

smoke 前：

```text
output missing
job missing
export missing
```

smoke 后：

```text
output missing
job missing
export missing
```

本步未写 `output/job/export`。

## 9. disabled 场景摘要

环境变量：

```text
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

请求：

```text
POST /local-llm/preview-safe
```

结果摘要：

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | disabled |
| ok | false |
| enabled | false |
| preview_only | true |
| no_write | true |
| affects_generation | false |
| affects_export | false |
| calls_ollama | false |
| source | zdoc_local_llm_preview_isolated_safe_endpoint_fake |
| reason | feature_flag_disabled |

disabled 场景未触发 helper、未触发 adapter、未写盘、未触发正式链路。

## 10. adapter-off compatible / illegal field 场景摘要

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

### compatible payload

使用 endpoint-compatible schema：

```text
request_id=pt-e-adapter-off-compatible
section_title=Adapter Off Compatible Payload
section_text=This is a minimal adapter-off compatible payload for preview-only validation.
context_summary=adapter-off compatible schema; preview-only.
```

结果摘要：

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | ok |
| ok | true |
| enabled | true |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| model | fake-local-llm |
| source | zdoc_local_llm_preview_isolated_safe_endpoint_fake |
| advisory_exists | true |
| suggestions_count | 3 |

adapter-off compatible payload 未误触 `illegal_field`。

### illegal field payload

使用 `content` 字段作为非法 formal field control。

结果摘要：

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | failure |
| ok | false |
| enabled | true |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| error_type | illegal_field |
| reason | illegal_field:content |
| source | zdoc_local_llm_preview_isolated_safe_endpoint_fake |

adapter-off illegal field 仍为 controlled failure。该失败未构造 real runtime path，未写盘，未触发正式链路。

## 11. enabled response-mode prompt tuning payload 逐项结果表

说明：用户给出的 `section` / `title` / `content` 语义已按只读核验到的 endpoint schema 映射为 `request_id` / `section_title` / `section_text` / `context_summary`。这样可以避免除 PT-F adapter-off illegal control 外的 payload 被 endpoint schema 提前拒绝。

| Payload | HTTP | status | ok | response_mode | quality_status | input_risk_status | evidence_anchor_status | calls_ollama | advisory_len | suggestions | risk/warnings | formal flags true |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| PT-A response-first advisory | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | true | 386 | 1 | 3 | none |
| PT-B JSON-first advisory | 200 | failure | false | malformed_response | blocked | clear | not_required | true | 0 | 0 | 3 | none |
| PT-C text-fallback advisory | 200 | ok | true | text_fallback | review_required | clear | not_required | true | 207 | 1 | 0 | none |
| PT-D thinking fallback observation | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | true | 386 | 1 | 3 | none |
| PT-E generated-preview-as-evidence regression | 200 | ok | true | thinking_only_fallback | blocked | review_required | invalid_anchor | true | 386 | 1 | 5 | none |
| PT-F evidence missing + prompt tuning | 200 | ok | true | thinking_only_fallback | review_required | review_required | missing | true | 386 | 1 | 6 | none |

正式链准入字段在 enabled payload 中均为 false：

```text
formal_generation_allowed=false
shadow_candidate_allowed=false
writeback_allowed=false
export_allowed=false
zbid_writeback_allowed=false
```

## 12. response_mode 统计

enabled payload response_mode 统计如下：

| response_mode | 次数 |
| --- | ---: |
| response_advisory | 0 |
| json_advisory | 0 |
| text_fallback | 1 |
| thinking_only_fallback | 4 |
| empty_response | 0 |
| malformed_response | 1 |
| normalization_failure | 0 |
| system_error | 0 |

统计顺序：

```text
response_advisory / json_advisory / text_fallback / thinking_only_fallback / empty_response / malformed_response / normalization_failure / system_error
```

本步统计值：

```text
0 / 0 / 1 / 4 / 0 / 1 / 0 / 0
```

对比 Step 70 的统计：

```text
0 / 0 / 0 / 8 / 0 / 0 / 0 / 0
```

本步在真实 runtime 下首次观察到 `text_fallback=1`，说明 prompt tuning 后至少出现了一个非 thinking response mode。但 `response_advisory=0`、`json_advisory=0`，且 `thinking_only_fallback` 仍有 4 次，response-mode 高依赖问题尚未闭环。

## 13. generated_preview_as_evidence_detected 次数

本步 `generated_preview_as_evidence_detected` 次数：

```text
1
```

出现于：

```text
PT-E generated-preview-as-evidence regression
```

对应状态：

```text
quality_status=blocked
evidence_anchor_status=invalid_anchor
evidence_blocked=true
```

generated preview 未被当作 evidence。

## 14. generated_content_evidence_blocked 次数

本步 `generated_content_evidence_blocked` 次数：

```text
1
```

出现于：

```text
PT-E generated-preview-as-evidence regression
```

该结果说明 generated-preview-as-evidence regression 仍可被 evidence anchor / quality gate 阻断。

## 15. thinking fallback 出现次数

本步 enabled payload 中 thinking fallback 出现次数：

```text
4
```

出现于：

* PT-A；
* PT-D；
* PT-E；
* PT-F。

`thinking_only_fallback` 仍为主要风险之一。虽然相比 Step 70 的 8/8 thinking fallback，本步在 6 个 enabled payload 中观察到 4 个 thinking fallback、1 个 text fallback、1 个 malformed response，但仍不能证明 response-mode 已稳定。

## 16. formal_generation_allowed 是否恒 false

enabled payload 中：

```text
formal_generation_allowed=false
```

disabled / adapter-off 响应未出现该字段为 true。全量结果未发现 `formal_generation_allowed=true`。

## 17. shadow_candidate_allowed 是否恒 false

enabled payload 中：

```text
shadow_candidate_allowed=false
```

disabled / adapter-off 响应未出现该字段为 true。全量结果未发现 `shadow_candidate_allowed=true`。

## 18. writeback/export/zbid_writeback 是否恒 false

enabled payload 中：

```text
writeback_allowed=false
export_allowed=false
zbid_writeback_allowed=false
```

disabled / adapter-off 响应未出现上述字段为 true。全量结果未发现 `writeback_allowed=true`、`export_allowed=true` 或 `zbid_writeback_allowed=true`。

## 19. 是否请求 /generate

否。

本步未请求 `/generate`。

## 20. 是否请求 /export_docx

否。

本步未请求 `/export_docx`。

## 21. 是否请求 /review/apply

否。

本步未请求 `/review/apply`。

## 22. 是否直接请求 Ollama /api/generate

否。

本步 smoke 客户端未直接请求 Ollama `/api/generate`。enabled 场景中 safe endpoint real adapter 在本地 loopback 内部间接调用 Ollama `/api/generate`，用于 `/local-llm/preview-safe` 的 runtime validation。

## 23. 是否写 output/job/export

否。

smoke 前后均为：

```text
output missing
job missing
export missing
```

## 24. 是否下载或拉取模型

否。

本步只检查 `/api/tags`，确认 `qwen3:0.6b` 已存在。未执行 pull，未下载模型。

## 25. 是否修改代码/tests

否。

本步未修改代码，未修改 tests。仅新增本 smoke report 文档。

## 26. 进程停止与端口清理情况

FastAPI：

* disabled PID 23385 已停止；
* adapter-off PID 23387 已停止；
* enabled PID 23388 已停止；
* 最终 `127.0.0.1:18759` 无监听。

Ollama：

* 本步启动的 Ollama PID 23307 已停止；
* 最终 `127.0.0.1:11434` 无监听。

未留下本步启动的服务进程。

## 27. 风险说明

当前风险如下：

* 风险 1：真实 runtime 仍较高依赖 `thinking_only_fallback`；
* 风险 2：response-first prompt 未产生 `response_advisory`；
* 风险 3：JSON-first prompt 返回 `malformed_response`，说明 JSON 输出仍不稳定；
* 风险 4：本步只观察到 1 次 `text_fallback`，不足以证明 response-mode 稳定；
* 风险 5：`text_fallback` 可能被误解为正式链准入；
* 风险 6：generated-preview-as-evidence 虽已 blocked，但仍需后续 regression smoke；
* 风险 7：后续 prompt tuning 若继续调整，仍可能破坏 no-write / preview-only 或 evidence safety。

回滚措施：

* 关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：

* 保留 disabled / adapter-off / fake-only 路径。

异常边界：

* 出现异常时不得扩大到正式链路；
* 不得将 `response_mode` 改善解释为 shadow generation 或正式生成链准入。

## 28. 下一步建议

下一步建议为 ZDoc Step 78：response-mode prompt tuning runtime smoke review + follow-up design，docs-only。

后续应复盘：

* Step 77 已出现 `text_fallback=1`，但 `response_advisory=0`、`json_advisory=0`；
* `thinking_only_fallback` 仍有 4 次；
* JSON-first payload 返回 `malformed_response`；
* 是否需要继续设计 JSON format / stop / prompt options；
* 是否需要比较更强本地模型；
* 是否需要继续 response-mode runtime smoke refresh。

不得直接进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
