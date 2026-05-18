# ZDoc Step 90: qwen3:14b targeted response-mode smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 90：`qwen3:14b` targeted response-mode runtime smoke + smoke report。

目标是验证 `qwen3:14b` 在极小样本下是否比既有 `qwen3:0.6b` / `qwen3:8b` 更有利于 response-mode 改善，重点观察：

* `qwen3:14b` 是否已本地存在；
* `qwen3:14b` 是否降低 `thinking_only_fallback`；
* 是否出现 `response_advisory` / `json_advisory` / `text_fallback`；
* generated-preview-as-evidence、evidence anchor、quality gate、input-risk 是否不回归；
* `formal_generation_allowed` / `shadow_candidate_allowed` / `writeback_allowed` / `export_allowed` / `zbid_writeback_allowed` 是否恒 false；
* 是否仍保持 preview-only / no-write；
* 是否未触发正式生成链、导出链、ZBid 写回链。

本步 smoke 客户端只请求 `/local-llm/preview-safe`。本步未由 smoke 客户端直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 safe endpoint real adapter 在本地 loopback 内部间接调用。

## 2. 开始前 Git 状态

开始前只读核验结果：

```text
pwd: /Users/youfeini/Desktop/文档生成系统
git status --short: clean
git branch --show-current: main
git rev-parse HEAD: bdeabf6e4051dd8b070c5957755ee9e9cbda034c
tag: v0.1.148-zdoc-qwen3-14b-response-mode-smoke-plan
tag target: bdeabf6e4051dd8b070c5957755ee9e9cbda034c
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
50104
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
qwen3:14b exists=true
qwen3:0.6b exists=true
qwen3:8b exists=true
```

本步未执行 pull，未下载模型。

## 5. qwen3:14b 是否存在

`qwen3:14b` 已存在，可以执行 targeted smoke。

本步只测试 `qwen3:14b`。`qwen3:0.6b` 与 `qwen3:8b` 仅作为 Step 87 历史结果对比引用，未重复测试。

## 6. 本地模型摘要

`/api/tags` 返回的本地模型摘要如下：

* `qwen3-next:80b-a3b-instruct-q8_0`
* `qwen3-coder:30b`
* `deepseek-r1:32b`
* `qwen3:30b`
* `qwen3:14b`
* `qwen3:8b`
* `qwen3:0.6b`

本步未测试 30b / 32b / 80b 类模型，未下载或 pull 缺失模型。

## 7. disabled 场景摘要

环境变量：

```text
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

请求：

```text
POST /local-llm/preview-safe
```

本步根据 endpoint 只读代码检查使用 endpoint-compatible schema：`request_id`、`section_title`、`section_text`、`context_summary`。

结果摘要：

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | disabled |
| ok | false |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| response_mode | absent |
| quality_status | absent |
| evidence_anchor_status | absent |
| reason | feature_flag_disabled |
| formal chain flags | no true value observed |
| elapsed_ms | 15 |

disabled 场景未触发 helper、未触发 adapter、未写盘、未触发正式链路。

## 8. adapter-off compatible 场景摘要

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

请求：

```text
POST /local-llm/preview-safe
```

只读代码检查确认 safe endpoint normal path 允许字段为 `context_summary`、`request_id`、`section_text`、`section_title`；`content` 是 formal output / illegal field。因此本步 adapter-off compatible 请求使用 endpoint-compatible schema，未使用 `content` 字段。

结果摘要：

| 字段 | 值 |
| --- | --- |
| HTTP 状态 | 200 |
| status | ok |
| ok | true |
| preview_only | true |
| no_write | true |
| calls_ollama | false |
| response_mode | absent |
| error_type | absent |
| reason | absent |
| advisory_exists | true |
| advisory_length | 149 |
| suggestions_count | 3 |
| risk_notes_count | 0 |
| formal chain flags | no true value observed |
| elapsed_ms | 15 |

adapter-off compatible payload 未误触 `illegal_field`。本步未执行 adapter-off illegal field fixture，因为 Step 90 仅要求 adapter-off compatible 场景。

## 9. enabled qwen3:14b targeted payload 逐项结果表

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:14b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=20
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=96
```

本步未设置未知 temperature、format/json mode 或 stop tokens。

enabled 请求共 5 次，均只请求 `/local-llm/preview-safe`。所有 payload 均为测试性、非真实投标正文，不含真实招标资料。

| payload_id | HTTP | status | calls_ollama | prompt_mode | response_mode | quality_status | input_risk_status | evidence_anchor_status | advisory_length | suggestions_count | risk_notes_count | elapsed_ms | generated_preview_detected | evidence_blocked | formal flags |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Q14-A | 200 | ok | true | response_first | thinking_only_fallback | review_required | clear | not_required | 386 | 1 | 3 | 8752 | false | false | all false |
| Q14-B | 200 | ok | true | json_first | thinking_only_fallback | review_required | clear | not_required | 386 | 1 | 3 | 7680 | false | false | all false |
| Q14-C | 200 | ok | true | text_fallback | thinking_only_fallback | review_required | clear | not_required | 385 | 1 | 3 | 7163 | false | false | all false |
| Q14-D | 200 | ok | true | response_first | thinking_only_fallback | blocked | review_required | invalid_anchor | 386 | 1 | 5 | 7219 | true | true | all false |
| Q14-E | 200 | ok | true | response_first | thinking_only_fallback | review_required | review_required | missing | 386 | 1 | 6 | 6285 | false | false | all false |

5/5 enabled payload 均为 HTTP 200、`status=ok`、`calls_ollama=true`。未出现未处理异常。

## 10. qwen3:14b response_mode 统计

`qwen3:14b` targeted enabled 统计如下：

```text
enabled_count=5
response_advisory=0
json_advisory=0
text_fallback=0
thinking_only_fallback=5
malformed_response=0
empty_response=0
normalization_failure=0
system_error=0
timeout=0
```

`qwen3:14b` 在本次极小样本下没有产生 `response_advisory`、`json_advisory` 或 `text_fallback`。

## 11. response_advisory / json_advisory / text_fallback / thinking_only_fallback / malformed_response / timeout 统计

本步 enabled 总统计：

```text
response_advisory=0
json_advisory=0
text_fallback=0
thinking_only_fallback=5
malformed_response=0
timeout=0
```

各 payload 结果如下：

* Q14-A response-first advisory：`thinking_only_fallback`；
* Q14-B JSON-first advisory：`thinking_only_fallback`；
* Q14-C text-fallback advisory：`thinking_only_fallback`；
* Q14-D generated-preview-as-evidence guard：`thinking_only_fallback`，evidence `invalid_anchor`；
* Q14-E evidence missing advisory：`thinking_only_fallback`，evidence `missing`。

`qwen3:14b` 相比 `qwen3:0.6b` / `qwen3:8b` 未显示 response-mode 改善。

## 12. generated-preview-as-evidence 防护摘要

generated-preview-as-evidence 回归 payload：

* Q14-D：`generated-preview-as-evidence guard`

结果：

```text
generated_preview_as_evidence_detected=1
generated_content_evidence_blocked=1
evidence_anchor_status=invalid_anchor
quality_status=blocked
formal flags all false
```

generated preview 未被当作 tender / drawing / boq / scoring evidence。防护未回归。

## 13. evidence missing 防护摘要

evidence missing payload：

* Q14-E：`evidence missing advisory`

结果：

```text
evidence_anchor_status=missing
quality_status=review_required
input_risk_status=review_required
formal flags all false
```

即使未来 response mode 改善，evidence missing 仍不得 formal eligible。本步未观察到 formal flags 变 true。

## 14. formal flags 是否恒 false

enabled targeted payload 中以下字段全部恒 false：

* `formal_generation_allowed`；
* `shadow_candidate_allowed`；
* `writeback_allowed`；
* `export_allowed`；
* `zbid_writeback_allowed`。

disabled 与 adapter-off 场景未观察到任何 formal chain flag 为 true。

## 15. 是否写 output/job/export

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

## 16. 是否下载或拉取模型

本步未执行 pull，未下载模型。`qwen3:14b` 已通过 `/api/tags` 确认存在，因此未触发缺失模型处理路径。

## 17. 端口与进程清理情况

本步启动的 FastAPI PID：

| 场景 | PID | 端口 | 结束状态 |
| --- | ---: | ---: | --- |
| disabled | 50135 | 18762 | stopped, port closed |
| adapter-off | 50160 | 18762 | stopped, port closed |
| enabled qwen3:14b | 50182 | 18762 | stopped, port closed |

本步启动的 Ollama PID：

```text
50104
```

结束状态：

```text
127.0.0.1:18762 no listener
127.0.0.1:11434 no listener
```

本步未留下服务监听进程。

## 18. 与 qwen3:0.6b / qwen3:8b 历史结果的简要对比

Step 87 历史结果：

```text
qwen3:0.6b: enabled=8, thinking_only_fallback=7, malformed_response=1
qwen3:8b: enabled=5, thinking_only_fallback=5
total: response_advisory=0, json_advisory=0, text_fallback=0, thinking_only_fallback=12, malformed_response=1
```

Step 90 `qwen3:14b` targeted 结果：

```text
qwen3:14b: enabled=5, thinking_only_fallback=5
response_advisory=0, json_advisory=0, text_fallback=0, malformed_response=0, timeout=0
```

对比结论：

* `qwen3:14b` 未降低 thinking fallback，占比为 5/5；
* `qwen3:14b` 未产生 `response_advisory`；
* `qwen3:14b` 未产生 `json_advisory`；
* `qwen3:14b` 未产生 `text_fallback`；
* `qwen3:14b` 未出现 `malformed_response` 或 timeout；
* 与 `qwen3:8b` 类似，`qwen3:14b` 在本次样本中仍为 100% `thinking_only_fallback`。

当前结果不支持进入 shadow generation 或正式生成链。

## 19. 风险说明

当前风险如下：

* `qwen3:14b` 极小样本仍为 5/5 `thinking_only_fallback`，不能证明 response-mode 改善；
* `qwen3:14b` 资源占用和耗时高于小模型，单次 payload 耗时约 6.3s 到 8.8s；
* 本次样本量很小，不能代表所有 prompt 或 options 表现；
* 未观察到 `response_advisory` / `json_advisory` / `text_fallback`，后续若继续模型比较需谨慎；
* generated-preview-as-evidence 防护有效，但不能因此进入正式链；
* model smoke 结果不得被解释为 shadow generation 或正式链准入。

回滚措施：保持 `qwen3:0.6b` preview-only 基线。

兜底措施：关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED`，保留 disabled / adapter-off / fake-only 路径。

出现异常时不得扩大到正式链路，不得进入 shadow generation、candidate patch、DOCX 导出或 ZBid 写回。

## 20. 下一步建议

下一步建议为 ZDoc Step 91：qwen3:14b targeted response-mode smoke review，docs-only。

不得直接进入 shadow generation、candidate patch、正式生成链、DOCX 导出或 ZBid 写回。若后续继续模型评估，应先做 docs-only review 与 readiness 判断，再决定是否设计更强模型、options 或 thinking fallback acceptability policy。

## 21. 禁止项执行记录

本步执行记录如下：

* 是否请求 `/local-llm/preview-safe`：是；
* 是否直接请求 Ollama `/api/generate`：否；
* 是否请求 `/generate`：否；
* 是否请求 `/export_docx`：否；
* 是否请求 `/review/apply`：否；
* 是否运行 pytest：否；
* 是否下载或 pull 模型：否；
* 是否修改代码/tests：否；
* 是否触发 DOCX/JSON/Markdown 正式导出：否；
* 是否接 ZBid 正式写回：否；
* 是否写 `output/job/export`：否。
