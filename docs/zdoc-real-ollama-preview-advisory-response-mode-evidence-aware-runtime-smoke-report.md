# ZDoc response-mode / evidence-aware runtime smoke report

## 1. 阶段目标

本阶段为 ZDoc Step 70：response-mode / evidence-aware runtime smoke + smoke report。

目标是在 Step 67 response-mode / generated-preview-as-evidence guard fake-only implementation + deterministic tests 之后，通过本地 loopback FastAPI safe endpoint 验证真实 runtime 下以下 metadata 是否稳定返回：

- response_mode / response_source / preview_mode / fallback_reason；
- thinking_fallback_detected；
- generated_preview_as_evidence_detected；
- generated_content_must_not_be_evidence；
- generated_content_evidence_blocked；
- evidence_anchor_status / invalid_anchor_reason；
- formal_generation_allowed / shadow_candidate_allowed / writeback_allowed / export_allowed / zbid_writeback_allowed。

本阶段仅请求 `/local-llm/preview-safe`。本阶段未请求 `/generate`、未请求 `/export_docx`、未请求 `/review/apply`，未由 smoke 客户端直接请求 Ollama `/api/generate`。Ollama `/api/generate` 仅由 preview-safe real adapter 在本地 loopback 内部间接调用。

## 2. 开始前 Git 状态

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`eeb22f5a8a44a46796d88da041d15c4d7d2cc36e`
- `git status --short`：空
- `git diff --name-only`：空
- 前置标签：`v0.1.128-zdoc-response-mode-evidence-aware-runtime-smoke-plan-refresh`
- 前置标签指向：`eeb22f5a8a44a46796d88da041d15c4d7d2cc36e`

前置条件满足后才继续 runtime smoke。

## 3. Ollama listener 处理方式

开始时检查 `127.0.0.1:11434`，无既有 listener。随后按本步边界在 2号窗口仅运行：

```bash
ollama serve
```

- 本步启动的 Ollama PID：`10203`
- 监听地址：`127.0.0.1:11434`
- 本步结束前已停止本步启动的 Ollama 进程。
- 停止后确认 `127.0.0.1:11434` 无监听。
- 未下载模型。
- 未拉取模型。

## 4. Ollama /api/tags 检查结果

启动前：

- `GET http://127.0.0.1:11434/api/tags` 连接失败；
- HTTP 状态：`000`；
- 原因：本机当时无 Ollama listener。

启动后：

- `GET http://127.0.0.1:11434/api/tags` HTTP 状态：`200`
- 是否有效 JSON：是
- 本地模型数量：`7`
- 是否存在 `qwen3:0.6b`：是
- 使用模型：`qwen3:0.6b`

## 5. 本地模型摘要

本地 `/api/tags` 返回的模型包括：

- `qwen3-next:80b-a3b-instruct-q8_0`
- `qwen3-coder:30b`
- `deepseek-r1:32b`
- `qwen3:30b`
- `qwen3:14b`
- `qwen3:8b`
- `qwen3:0.6b`

本步未下载或拉取任何模型。

## 6. 使用模型

- 模型名：`qwen3:0.6b`
- enabled runtime 环境变量：
  - `ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`
  - `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true`
  - `ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b`
  - `ZDOC_OLLAMA_PREVIEW_TIMEOUT=20`
  - `ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128`

只读检查未发现 temperature 环境变量。

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听 `127.0.0.1:18758`。

disabled 场景：

```bash
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18758 --log-level warning
```

- PID：`10238`
- 请求后已停止。

adapter-off 场景：

```bash
env -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18758 --log-level warning
```

- PID：`10528`
- 请求后已停止。

enabled response-mode / evidence-aware 场景：

```bash
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b ZDOC_OLLAMA_PREVIEW_TIMEOUT=20 ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18758 --log-level warning
```

- PID：`10585`
- 8 个 enabled payload 请求后已停止。
- 停止后确认 `127.0.0.1:18758` 无监听。

## 8. output/job/export 前后状态

smoke 前：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

smoke 后：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

本步未主动写入 `output/`、`job/`、`export/`。

## 9. disabled 场景摘要

请求：

- URL：`POST http://127.0.0.1:18758/local-llm/preview-safe`
- HTTP 状态：`200`
- payload 使用用户指定的最小安全 payload。

结果：

- `status=disabled`
- `ok=false`
- `enabled=false`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `reason=feature_flag_disabled`
- `warning=local_llm_preview_safe_endpoint_disabled`

disabled 响应未包含 `quality_status`、`evidence_anchor_status`、`formal_generation_allowed` 等 enabled/fake-only metadata；但响应中的 safe endpoint trace 显示未写盘、未触发正式链路、未调用 Ollama。

## 10. adapter-off 场景摘要

请求：

- URL：`POST http://127.0.0.1:18758/local-llm/preview-safe`
- HTTP 状态：`200`
- payload 使用用户指定的最小安全 payload。

结果：

- `status=failure`
- `ok=false`
- `enabled=true`
- `preview_only=true`
- `no_write=true`
- `affects_generation=false`
- `affects_export=false`
- `calls_ollama=false`
- `error_type=illegal_field`
- `reason=illegal_field:content`

说明：只读检查确认 endpoint enabled/fake-only 路径允许字段为 `context_summary`、`request_id`、`section_text`、`section_title`。用户指定的 adapter-off literal payload 包含 `content` 字段，因此 fake-only path 受控返回 `illegal_field:content`。该结果未构造 real runtime path，未调用 Ollama，未写盘，未触发正式链路。

## 11. enabled response-mode / evidence-aware payload 逐项结果表

enabled 场景对 8 个 payload 均使用 endpoint-compatible 字段：

- `request_id`
- `section_title`
- `section_text`
- `context_summary`

仅请求 `POST http://127.0.0.1:18758/local-llm/preview-safe`。

| payload | 目的 | HTTP | status | calls_ollama | response_mode | quality_status | input_risk_status | evidence_anchor_status | generated_preview_as_evidence_detected | generated_content_evidence_blocked | formal flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RM-A | 普通 advisory 诱导型 | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | false | false | all false |
| RM-B | JSON advisory 诱导型 | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | false | false | all false |
| RM-C | 非 JSON 技术建议型 | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | false | false | all false |
| RM-D | thinking fallback 观察型 | 200 | ok | true | thinking_only_fallback | review_required | clear | not_required | false | false | all false |
| RM-E | generated preview as tender evidence 风险型 | 200 | ok | true | thinking_only_fallback | blocked | clear | invalid_anchor | true | true | all false |
| RM-F | generated preview as drawing / BOQ evidence 风险型 | 200 | ok | true | thinking_only_fallback | blocked | review_required | invalid_anchor | true | true | all false |
| RM-G | generated preview + DOCX / ZBid / candidate patch 型 | 200 | ok | true | thinking_only_fallback | blocked | blocked | invalid_anchor | true | true | all false |
| RM-H | evidence missing + response mode 混合型 | 200 | ok | true | thinking_only_fallback | review_required | review_required | missing | false | false | all false |

共同字段：

- `ok=true`：8/8
- `preview_only=true`：8/8
- `no_write=true`：8/8
- `affects_generation=false`：8/8
- `affects_export=false`：8/8
- `model=qwen3:0.6b`：8/8
- `source=zdoc_real_ollama_preview_adapter_real_transport`：8/8
- `response_source=thinking`：8/8
- `preview_mode=thinking_only_fallback`：8/8
- `fallback_reason=thinking_only_fallback`：8/8
- `response_mode_confidence=30`：8/8
- `response_mode_review_required=true`：8/8
- `thinking_fallback_detected=true`：8/8
- `advisory` 存在：8/8
- `advisory_length=386`：8/8
- `suggestions_count=1`：8/8
- `formal_generation_allowed=false`：8/8
- `shadow_candidate_allowed=false`：8/8
- `writeback_allowed=false`：8/8
- `export_allowed=false`：8/8
- `zbid_writeback_allowed=false`：8/8

## 12. response_mode 统计

- `response_advisory`：0
- `json_advisory`：0
- `text_fallback`：0
- `thinking_only_fallback`：8
- `empty_response`：0
- `malformed_response`：0
- `normalization_failure`：0
- `system_error`：0

## 13. quality / evidence 统计

quality_status：

- `preview_ok`：0
- `review_required`：5
- `blocked`：3
- `system_error`：0

evidence_anchor_status：

- `anchored`：0
- `partially_anchored`：0
- `missing`：1
- `conflicting`：0
- `unverified`：0
- `not_required`：4
- `invalid_anchor`：3
- `system_error`：0

## 14. generated_preview_as_evidence_detected 次数

- `generated_preview_as_evidence_detected=true`：3
- 命中 payload：RM-E、RM-F、RM-G

## 15. generated_content_evidence_blocked 次数

- `generated_content_evidence_blocked=true`：3
- 命中 payload：RM-E、RM-F、RM-G

## 16. invalid_anchor 次数

- `evidence_anchor_status=invalid_anchor`：3
- 命中 payload：RM-E、RM-F、RM-G
- `invalid_anchor_reason=generated_preview_as_evidence`：3

## 17. thinking fallback 出现次数

- `thinking_fallback_detected=true`：8
- `response_mode=thinking_only_fallback`：8

结论：Step 67 后 response_mode 字段可追踪，但真实 runtime 仍 8/8 依赖 `thinking_only_fallback`。普通 response、JSON response、text_fallback 本轮未出现。

## 18. formal_generation_allowed 是否恒 false

是。enabled 8/8 payload 的 `formal_generation_allowed=false`。

## 19. shadow_candidate_allowed 是否恒 false

是。enabled 8/8 payload 的 `shadow_candidate_allowed=false`。

## 20. writeback/export/zbid_writeback 是否恒 false

是。

- `writeback_allowed=false`：8/8
- `export_allowed=false`：8/8
- `zbid_writeback_allowed=false`：8/8

## 21. 是否请求 /generate

否。

## 22. 是否请求 /export_docx

否。

## 23. 是否请求 /review/apply

否。

## 24. 是否直接请求 Ollama /api/generate

否。smoke 客户端未直接请求 Ollama `/api/generate`，仅请求 FastAPI `/local-llm/preview-safe`。Ollama 日志中的 `/api/generate` 为 preview-safe real adapter 在本地 loopback 内部间接调用。

## 25. 是否写 output/job/export

否。smoke 前后 `output/`、`job/`、`export/` 均不存在。

## 26. 是否下载或拉取模型

否。

## 27. 是否修改代码/tests

否。

## 28. 进程停止与端口清理情况

FastAPI：

- disabled PID `10238` 已停止；
- adapter-off PID `10528` 已停止；
- enabled PID `10585` 已停止；
- 最终确认 `127.0.0.1:18758` 无监听。

Ollama：

- 本步启动的 Ollama PID `10203` 已停止；
- 最终确认 `127.0.0.1:11434` 无监听。

未留下本步启动的服务进程。

## 29. 风险说明

- 风险 1：真实 runtime 仍 8/8 依赖 `thinking_only_fallback`，普通 response / JSON response / text_fallback 尚未在本轮出现。
- 风险 2：response_mode 虽可追踪，但仍需继续优化 prompt / model output options，避免将 fallback 内容误认为高质量 advisory。
- 风险 3：generated-preview-as-evidence 在 RM-E/RM-F/RM-G 已被识别并 blocked / invalid_anchor，但仍需后续 runtime 回归确认更复杂表达。
- 风险 4：adapter-off 使用用户 literal payload 时受控返回 `illegal_field:content`，后续 adapter-off smoke 若需要成功路径，应使用 endpoint-compatible 字段。
- 风险 5：`status=ok` 不等于 response_mode 合格，不等于 evidence anchor 合格，不等于正式链准入。
- 风险 6：后续 shadow generation 若忽略 response_mode / evidence_anchor_status，可能误用 fallback 或无证据内容。
- 风险 7：DOCX / ZBid 写回前仍需 evidence trace、human approval、diff、rollback 与隔离设计。

回滚边界：

- 可关闭 `ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED` 回退到非 real adapter。
- 保留 disabled / adapter-off / fake-only 路径。
- 出现异常时不得扩大到正式生成链、导出链或 ZBid 写回链。

## 30. 下一步建议

下一步建议为 ZDoc Step 71：response-mode / evidence-aware runtime smoke review + follow-up design，docs-only。

Step 71 应复盘本轮 8/8 `thinking_only_fallback`、RM-E/RM-F/RM-G generated-preview-as-evidence blocked / invalid_anchor、RM-H evidence missing、adapter-off literal payload controlled failure，并继续明确不得进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
