# ZDoc Step 87: response-mode model/options comparison smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 87：response-mode model/options comparison smoke + report。

目标是验证不同本地模型 / options profile 对 `response_mode` 的影响，重点观察：

* `qwen3:0.6b` 当前基线表现；
* 是否存在比 `qwen3:0.6b` 更低 `thinking_only_fallback` 的本地模型；
* `response_advisory` / `json_advisory` / `text_fallback` 是否在更强模型或不同 options 下出现；
* generated-preview-as-evidence、evidence anchor、quality gate、input-risk 是否不回归；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否恒为 false；
* 是否仍保持 preview-only / no-write；
* 是否未触发正式生成链、导出链、ZBid 写回链。

本步 smoke 客户端只请求 `/local-llm/preview-safe`。本步未由 smoke 客户端直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 safe endpoint real adapter 在本地 loopback 内部间接调用。

## 2. 开始前 Git 状态

开始前只读核验结果：

```text
pwd: /Users/youfeini/Desktop/文档生成系统
git status --short: clean
git branch --show-current: main
git rev-parse HEAD: c63b5b7e75fba509d5e92280d9fcfd925fc5b849
tag: v0.1.145-zdoc-response-mode-model-options-comparison-smoke-plan
tag target: c63b5b7e75fba509d5e92280d9fcfd925fc5b849
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
44522
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
qwen3:8b exists=true
qwen3:14b exists=true
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

## 6. 实际参与对比的模型

实际参与对比的模型：

* `qwen3:0.6b`：必测基线模型；
* `qwen3:8b`：优先对照模型，`/api/tags` 确认存在。

本步未测试 `qwen3:14b`、30b / 32b / 80b 类模型，以控制默认矩阵规模和资源风险。

## 7. 跳过的模型及原因

跳过模型及原因如下：

* `qwen3:14b`：存在，但本步已有 `qwen3:8b` 作为优先对照；为保持 enabled 请求数量不超过 13 次，未纳入默认矩阵；
* `qwen3:30b`：存在，但属于高资源风险模型，本步未测，需单独授权；
* `qwen3-coder:30b`：存在，但属于高资源风险模型，且需另行评估是否适合文档 advisory，本步未测，需单独授权；
* `deepseek-r1:32b`：存在，但属于推理型高资源风险模型，可能更依赖 thinking，本步未测，需单独授权；
* `qwen3-next:80b-a3b-instruct-q8_0`：存在，但资源占用和响应时间风险高，本步未测，需单独授权。

未发现缺失模型后自动 pull 或下载的行为。

## 8. options profile 表

本步使用的 options profile 如下：

| Profile | 名称 | timeout | num_predict | temperature / format / stop |
| --- | --- | ---: | ---: | --- |
| O1 | baseline conservative | 20 | 160 | 未设置；当前代码未查明对应 env/options |
| O2 | response-first compact | 20 | 96 | 未设置；当前代码未查明对应 env/options |
| O3 | JSON compact | 20 | 96 | 未设置；当前代码未查明对应 env/options |

已确认使用的环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=<当前测试模型名>
ZDOC_OLLAMA_PREVIEW_TIMEOUT=<profile timeout>
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=<profile num_predict>
```

未强行设置未知 temperature、format/json mode 或 stop tokens。

## 9. payload 表

所有 payload 均为测试性、非真实投标正文，不含真实招标资料。enabled 与 adapter-off compatible 请求均使用 endpoint-compatible schema：`request_id`、`section_title`、`section_text`、`context_summary`。

| payload_id | 目标 |
| --- | --- |
| MC-A | response-first advisory，观察 `response_advisory` |
| MC-B | JSON-first advisory，观察 `json_advisory` 与 `malformed_response` |
| MC-C | text-fallback advisory，观察 `text_fallback` |
| MC-D | generated-preview-as-evidence guard，验证 generated preview 不得作为 evidence |
| MC-E | evidence missing advisory，验证 evidence missing 不得 formal eligible |

## 10. disabled 场景摘要

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
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| reason | feature_flag_disabled |
| response_mode | absent |
| quality_status | absent |
| evidence_anchor_status | absent |
| formal chain flags | no true value observed |

disabled 场景未触发 helper、未触发 adapter、未写盘、未触发正式链路。

## 11. adapter-off compatible / illegal field 场景摘要

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

### compatible payload

使用 endpoint-compatible schema。

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | ok |
| ok | true |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| model | fake-local-llm |
| advisory_exists | true |
| advisory_length | 168 |
| suggestions_count | 3 |
| error_type | absent |
| reason | absent |
| formal chain flags | no true value observed |

adapter-off compatible payload 未误触 `illegal_field`。

### illegal field payload

使用带 `content` 的 illegal field fixture。

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | failure |
| ok | false |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| error_type | illegal_field |
| reason | illegal_field:content |
| controlled_failure | true |
| formal chain flags | no true value observed |

adapter-off illegal field 仍为 controlled failure，未构造 real runtime path。

## 12. model/options comparison matrix

enabled 矩阵共执行 13 次请求，均只请求 `/local-llm/preview-safe`。

| model | profile | payload | HTTP | status | response_mode | prompt_mode | quality_status | evidence_anchor_status | elapsed_ms | generated_preview_guard | formal flags |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- | --- |
| qwen3:0.6b | O1 | MC-A | 200 | ok | thinking_only_fallback | response_first | review_required | not_required | 1745 | false / false | all false |
| qwen3:0.6b | O1 | MC-B | 200 | failure | malformed_response | json_first | blocked | not_required | 1127 | false / false | all false |
| qwen3:0.6b | O1 | MC-C | 200 | ok | thinking_only_fallback | text_fallback | review_required | not_required | 909 | false / false | all false |
| qwen3:0.6b | O2 | MC-A | 200 | ok | thinking_only_fallback | response_first | review_required | not_required | 420 | false / false | all false |
| qwen3:0.6b | O2 | MC-C | 200 | ok | thinking_only_fallback | text_fallback | review_required | not_required | 433 | false / false | all false |
| qwen3:0.6b | O2 | MC-D | 200 | ok | thinking_only_fallback | response_first | blocked | invalid_anchor | 768 | true / true | all false |
| qwen3:0.6b | O2 | MC-E | 200 | ok | thinking_only_fallback | response_first | review_required | missing | 506 | false / false | all false |
| qwen3:0.6b | O3 | MC-B | 200 | ok | thinking_only_fallback | json_first | review_required | not_required | 416 | false / false | all false |
| qwen3:8b | O2 | MC-A | 200 | ok | thinking_only_fallback | response_first | review_required | not_required | 4961 | false / false | all false |
| qwen3:8b | O2 | MC-C | 200 | ok | thinking_only_fallback | text_fallback | review_required | not_required | 4195 | false / false | all false |
| qwen3:8b | O2 | MC-D | 200 | ok | thinking_only_fallback | response_first | blocked | invalid_anchor | 4196 | true / true | all false |
| qwen3:8b | O2 | MC-E | 200 | ok | thinking_only_fallback | response_first | review_required | missing | 3639 | false / false | all false |
| qwen3:8b | O3 | MC-B | 200 | ok | thinking_only_fallback | json_first | review_required | not_required | 4236 | false / false | all false |

字段说明：`generated_preview_guard` 按 `generated_preview_as_evidence_detected / generated_content_evidence_blocked` 记录。

## 13. response_mode 统计

enabled 总统计：

```text
enabled_count=13
response_advisory=0
json_advisory=0
text_fallback=0
thinking_only_fallback=12
malformed_response=1
empty_response=0
normalization_failure=0
system_error=0
```

本步未观察到 `response_advisory`、`json_advisory` 或 `text_fallback`。

## 14. 每模型 thinking fallback 比例

每模型 `thinking_only_fallback` 比例如下：

| model | enabled 请求数 | thinking_only_fallback | 比例 |
| --- | ---: | ---: | ---: |
| qwen3:0.6b | 8 | 7 | 87.5% |
| qwen3:8b | 5 | 5 | 100% |

对照模型 `qwen3:8b` 未降低 thinking fallback，占比反而为 100%。

## 15. 每模型 response_advisory / json_advisory / text_fallback 数量

| model | response_advisory | json_advisory | text_fallback | malformed_response |
| --- | ---: | ---: | ---: | ---: |
| qwen3:0.6b | 0 | 0 | 0 | 1 |
| qwen3:8b | 0 | 0 | 0 | 0 |

`qwen3:8b` 相比 `qwen3:0.6b` 没有带来非-thinking response mode 改善。

## 16. malformed_response 数量

`malformed_response` 总数为 1。

唯一发生位置：

```text
model=qwen3:0.6b
options_profile=O1
payload_id=MC-B
prompt_mode=json_first
status=failure
quality_status=blocked
fallback_reason=malformed_json
controlled_failure=true
```

O3 JSON compact 下 `qwen3:0.6b` 和 `qwen3:8b` 均未出现 `malformed_response`，但两者也未形成 `json_advisory`，均为 `thinking_only_fallback`。

## 17. timeout / controlled failure 数量

timeout 数量：

```text
0
```

controlled failure 数量：

```text
1
```

controlled failure 为 `qwen3:0.6b / O1 / MC-B` 的 `malformed_response`。

adapter-off illegal field 也为 controlled failure，但不计入 enabled model/options matrix。

## 18. generated-preview-as-evidence 防护摘要

generated-preview-as-evidence 回归 payload：

* `qwen3:0.6b / O2 / MC-D`；
* `qwen3:8b / O2 / MC-D`。

结果：

```text
generated_preview_as_evidence_detected=2
generated_content_evidence_blocked=2
evidence_anchor_status=invalid_anchor for both MC-D rows
quality_status=blocked for both MC-D rows
formal flags all false
```

generated preview 未被当作 tender / drawing / boq / scoring evidence。防护未回归。

## 19. evidence missing 防护摘要

evidence missing payload：

* `qwen3:0.6b / O2 / MC-E`；
* `qwen3:8b / O2 / MC-E`。

结果：

```text
evidence_anchor_status=missing for both MC-E rows
quality_status=review_required for both MC-E rows
input_risk_status=review_required for both MC-E rows
formal flags all false
```

即使 response mode 在未来改善，evidence missing 仍不得 formal eligible。本步未观察到 formal flags 变 true。

## 20. formal flags 是否恒 false

enabled matrix 中以下字段全部恒 false：

* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

disabled 与 adapter-off 场景未观察到任何 formal chain flag 为 true。

## 21. 是否请求 /generate：否

本步未请求 `/generate`。

## 22. 是否请求 /export_docx：否

本步未请求 `/export_docx`。

## 23. 是否请求 /review/apply：否

本步未请求 `/review/apply`。

## 24. 是否直接请求 Ollama /api/generate：否

本步 smoke 客户端未直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 safe endpoint real adapter 在本地 loopback 内部间接调用。

## 25. 是否写 output/job/export：否

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

## 26. 是否下载或拉取模型：否

本步未执行 pull，未下载模型。缺失模型处理路径未触发，因为默认测试模型均已存在。

## 27. 是否修改代码/tests：否

本步未修改代码，未修改 tests，未运行 pytest。

## 28. 进程停止与端口清理情况

本步启动的 FastAPI PID：

| 场景 | PID | 端口 | 结束状态 |
| --- | ---: | ---: | --- |
| disabled | 44571 | 18761 | stopped, port closed |
| adapter-off | 44572 | 18761 | stopped, port closed |
| enabled qwen3:0.6b O1 | 44573 | 18761 | stopped, port closed |
| enabled qwen3:0.6b O2 | 44587 | 18761 | stopped, port closed |
| enabled qwen3:0.6b O3 | 44600 | 18761 | stopped, port closed |
| enabled qwen3:8b O2 | 44601 | 18761 | stopped, port closed |
| enabled qwen3:8b O3 | 44639 | 18761 | stopped, port closed |

本步启动的 Ollama PID：

```text
44522
```

结束状态：

```text
127.0.0.1:18761 no listener
127.0.0.1:11434 no listener
```

本步未留下服务监听进程。

## 29. 风险说明

当前风险如下：

* `qwen3:8b` 未降低 thinking fallback，说明仅扩大到 8b 仍不足以证明 response-mode 稳定；
* `qwen3:0.6b` 仍为 7/8 thinking fallback，`qwen3:8b` 为 5/5 thinking fallback；
* 本步未测试 `qwen3:14b`，不能判断 14b 是否改善 response-mode；
* O3 JSON compact 降低了 malformed 风险，但未产生 `json_advisory`；
* 本步未观察到 `text_fallback`，此前 Step 77/83 的 `text_fallback=1` 仍不能视为稳定；
* 更强模型可能输出更长内容，后续如测试 14b/30b/80b 需继续严格 no-write / preview-only；
* model/options comparison 结果不得被解释为 shadow generation 或正式链准入。

## 30. 下一步建议

下一步建议为 ZDoc Step 88：response-mode model/options comparison review，docs-only。

不得直接进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。若后续考虑继续模型对比，应先做 14b 或 options 扩展的 docs-only plan，并单独授权 runtime smoke。
