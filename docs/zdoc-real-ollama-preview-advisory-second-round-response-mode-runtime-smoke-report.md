# ZDoc Step 83: second-round response-mode runtime smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 83：second-round response-mode runtime smoke + smoke report。

本步目标是验证 Step 80 二轮 response-mode prompt tuning 后，真实 runtime 下 `response_mode` 分布是否改善，并确认 prompt metadata、adapter-off schema、generated-preview-as-evidence、evidence anchor、quality gate、input-risk 和正式链隔离不回归。

重点观察项如下：

* response-first 是否产生 `response_advisory`；
* JSON-first 是否产生 `json_advisory`；
* text-fallback 是否稳定；
* `thinking_only_fallback` 频率是否继续下降；
* `prompt_mode` / `prompt_profile` / `prompt_version` / `prompt_tuning_applied` 是否稳定返回；
* adapter-off compatible payload 是否受控；
* adapter-off illegal field 是否仍 controlled failure；
* generated-preview-as-evidence、evidence anchor、quality gate、input-risk 是否不回归；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否没有出现 true；
* 是否仍保持 preview-only / no-write；
* 是否未触发正式生成链、导出链、ZBid 写回链。

本步 smoke 客户端只请求 `/local-llm/preview-safe`。本步未由 smoke 客户端直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 safe endpoint real adapter 在本地 loopback 内部间接调用。

## 2. 开始前 Git 状态

开始前只读核验结果：

```text
pwd: /Users/youfeini/Desktop/文档生成系统
git status --short: clean
git branch --show-current: main
git rev-parse HEAD: 3a244974f26e54585c5801554dffadfdd5b2d7cb
tag: v0.1.141-zdoc-second-round-response-mode-runtime-smoke-plan-refresh
tag target: 3a244974f26e54585c5801554dffadfdd5b2d7cb
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
38033
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

## 6. 使用模型

enabled second-round response-mode 场景设置：

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
127.0.0.1:18760
```

启动命令：

```bash
python3 -B -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18760 --log-level warning
```

分场景 PID：

| 场景 | PID | 端口 | 结束状态 |
| --- | ---: | ---: | --- |
| disabled | 38109 | 18760 | stopped, port closed |
| adapter-off | 38110 | 18760 | stopped, port closed |
| enabled | 38122 | 18760 | stopped, port closed |

所有 FastAPI 进程均已停止。最终 `127.0.0.1:18760` 无监听。

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
| prompt_mode | absent |
| response_mode | absent |
| quality_status | absent |
| evidence_anchor_status | absent |
| formal chain flags | no true value observed |

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
request_id=srt-h-adapter-off-compatible
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
| advisory_length | 168 |
| suggestions_count | 3 |
| error_type | absent |
| reason | absent |
| formal chain flags | no true value observed |

adapter-off compatible payload 未误触 `illegal_field`。

### illegal field payload

使用带 `content` 的 illegal field fixture：

```text
request_id=srt-h-adapter-off-illegal-field
extra field=content
```

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
| source | zdoc_local_llm_preview_isolated_safe_endpoint_fake |
| error_type | illegal_field |
| reason | illegal_field:content |
| controlled_failure | true |
| formal chain flags | no true value observed |

adapter-off illegal field 仍为 controlled failure，未构造 real runtime path。

## 11. enabled second-round response-mode payload 逐项结果表

enabled 场景使用 endpoint-compatible schema。用户给出的 `section` / `title` / `content` 语义映射为 `request_id` / `section_title` / `section_text` / `context_summary`，以避免正常路径误触 `illegal_field:content`。非法字段回归已在 adapter-off illegal field payload 中单独覆盖。

| payload | HTTP | status | calls_ollama | prompt_mode | response_mode | response_source | preview_mode | quality_status | input_risk_status | evidence_anchor_status | generated_preview_as_evidence_detected | formal flags true |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRT-A | 200 | ok | true | response_first | thinking_only_fallback | thinking | thinking_only_fallback | review_required | clear | not_required | false | none |
| SRT-B | 200 | ok | true | json_first | thinking_only_fallback | thinking | thinking_only_fallback | review_required | clear | not_required | false | none |
| SRT-C | 200 | ok | true | text_fallback | text_fallback | response | text_fallback | review_required | clear | not_required | false | none |
| SRT-D | 200 | ok | true | response_first | thinking_only_fallback | thinking | thinking_only_fallback | review_required | clear | not_required | false | none |
| SRT-E | 200 | ok | true | response_first | thinking_only_fallback | thinking | thinking_only_fallback | review_required | review_required | missing | false | none |
| SRT-F | 200 | ok | true | response_first | thinking_only_fallback | thinking | thinking_only_fallback | blocked | review_required | invalid_anchor | true | none |
| SRT-G | 200 | ok | true | response_first | thinking_only_fallback | thinking | thinking_only_fallback | blocked | blocked | invalid_anchor | true | none |

Enabled 场景 7/7 HTTP 200、7/7 `status=ok`、7/7 `calls_ollama=true`。

## 12. prompt_mode 统计

Enabled payload 的 `prompt_mode` 统计如下：

| prompt_mode | 次数 |
| --- | ---: |
| response_first | 5 |
| json_first | 1 |
| text_fallback | 1 |

Prompt metadata 返回情况：

* 7/7 enabled payload 均返回 `prompt_profile=second_round_response_mode_tuning`；
* 7/7 enabled payload 均返回 `prompt_version=zdoc_response_mode_prompt_v2`；
* 7/7 enabled payload 均返回 `prompt_tuning_applied=true`；
* 7/7 enabled payload 均返回 `adapter_schema_mode=compatible`；
* SRT-B 返回 `json_mode_requested=true`；
* SRT-A / SRT-D / SRT-E / SRT-F / SRT-G 返回 `response_first_requested=true`；
* SRT-C 返回 `prompt_mode=text_fallback`；
* 7/7 enabled payload 均返回 `text_fallback_allowed=true`；
* 7/7 enabled payload 均返回 `evidence_aware_prompt_applied=true`。

## 13. response_mode 统计

Enabled payload 的 `response_mode` 统计如下：

| response_mode | 次数 |
| --- | ---: |
| response_advisory | 0 |
| json_advisory | 0 |
| text_fallback | 1 |
| thinking_only_fallback | 6 |
| empty_response | 0 |
| malformed_response | 0 |
| normalization_failure | 0 |
| system_error | 0 |

与 Step 77 对比：

* Step 77：`text_fallback=1`，`thinking_only_fallback=4/6`，`malformed_response=1`；
* Step 83：`text_fallback=1`，`thinking_only_fallback=6/7`，`malformed_response=0`。

本步显示 JSON-first payload 不再是 `malformed_response`，但仍未形成 `json_advisory`，而是回落为 `thinking_only_fallback`。`response_advisory` 仍未出现。

## 14. response_advisory / json_advisory / text_fallback / thinking_only_fallback / empty_response / malformed_response / normalization_failure / system_error 统计

归并统计如下：

```text
response_advisory=0
json_advisory=0
text_fallback=1
thinking_only_fallback=6
empty_response=0
malformed_response=0
normalization_failure=0
system_error=0
```

判断：

* 二轮 runtime smoke 仍未证明 `response_advisory` 稳定；
* 二轮 runtime smoke 仍未证明 `json_advisory` 稳定；
* `text_fallback` 继续出现 1 次，说明 text-fallback 路径仍可触发；
* `thinking_only_fallback` 仍为主路径，且本轮为 6/7；
* JSON-first 的 malformed 情况在本轮未出现，但 JSON-first 仍未达到 `json_advisory`。

## 15. generated_preview_as_evidence_detected 次数

Enabled payload 中 `generated_preview_as_evidence_detected=true` 次数：

```text
2
```

对应 payload：

* SRT-F：generated-preview-as-evidence regression；
* SRT-G：formal chain request regression。

## 16. generated_content_evidence_blocked 次数

Enabled payload 中 `generated_content_evidence_blocked=true` 次数：

```text
2
```

对应 payload：

* SRT-F；
* SRT-G。

这说明 generated-preview-as-evidence guard 在本轮真实 runtime 下继续有效。

## 17. thinking fallback 出现次数

Enabled payload 中 `thinking_fallback_detected=true` 次数：

```text
6
```

对应 payload：

* SRT-A；
* SRT-B；
* SRT-D；
* SRT-E；
* SRT-F；
* SRT-G。

SRT-C 为 `text_fallback`，`thinking_fallback_detected=false`。

## 18. formal_generation_allowed 是否恒 false

Enabled payload 中：

```text
formal_generation_allowed=false for 7/7
```

Disabled / adapter-off 场景未出现 true 值。

## 19. shadow_candidate_allowed 是否恒 false

Enabled payload 中：

```text
shadow_candidate_allowed=false for 7/7
```

Disabled / adapter-off 场景未出现 true 值。

## 20. writeback/export/zbid_writeback 是否恒 false

Enabled payload 中：

```text
writeback_allowed=false for 7/7
export_allowed=false for 7/7
zbid_writeback_allowed=false for 7/7
```

Disabled / adapter-off 场景未出现 true 值。

## 21. 是否请求 /generate

```text
否
```

本步未请求正式生成链 `/generate`。

## 22. 是否请求 /export_docx

```text
否
```

本步未请求 `/export_docx`。

## 23. 是否请求 /review/apply

```text
否
```

本步未请求 `/review/apply`。

## 24. 是否直接请求 Ollama /api/generate

```text
否
```

本步 smoke 客户端未直接请求 Ollama `/api/generate`。Safe endpoint real adapter 在本地 loopback 内部间接调用 Ollama `/api/generate` 以完成 enabled runtime smoke。

## 25. 是否写 output/job/export

```text
否
```

前后状态均为：

```text
output missing
job missing
export missing
```

## 26. 是否下载或拉取模型

```text
否
```

本步仅检查 `/api/tags`，确认 `qwen3:0.6b` 已存在。未执行 `ollama pull`，未下载模型。

## 27. 是否修改代码/tests

```text
否
```

本步未修改代码，未修改 tests。

## 28. 进程停止与端口清理情况

FastAPI：

* disabled PID `38109` 已停止；
* adapter-off PID `38110` 已停止；
* enabled PID `38122` 已停止；
* 最终 `127.0.0.1:18760` 无监听。

Ollama：

* 本步启动 PID `38033`；
* 本步结束前已停止；
* 最终 `127.0.0.1:11434` 无监听。

未留下本步启动的服务进程。

## 29. 风险说明

当前风险如下：

* 风险 1：二轮真实 runtime 仍高度依赖 `thinking_only_fallback`，本轮为 6/7；
* 风险 2：response-first prompt 在真实模型下仍未产生 `response_advisory`；
* 风险 3：JSON-first prompt 未 malformed，但仍未产生 `json_advisory`；
* 风险 4：`text_fallback` 继续出现，但样本仍只有 1 个，不足以证明稳定；
* 风险 5：`text_fallback` 或 prompt metadata 可能被误解为正式链准入；
* 风险 6：generated-preview-as-evidence 虽继续有效，但后续仍需回归覆盖；
* 风险 7：后续 tuning 若继续压缩 prompt，可能降低 advisory 质量或弱化 evidence safety；
* 风险 8：若忽略 schema 映射，使用 `content` 作为正常路径字段会误触 `illegal_field:content`。

回滚措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`。

兜底措施：保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 30. 下一步建议

下一步建议为 ZDoc Step 84：second-round response-mode runtime smoke review + follow-up design，docs-only。

Step 83 已证明二轮 runtime smoke 受控、prompt metadata 稳定、generated-preview-as-evidence 回归有效、formal chain isolation 稳定；但 `thinking_only_fallback` 仍为 6/7，`response_advisory` / `json_advisory` 仍未出现，因此不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
