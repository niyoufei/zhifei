# ZDoc preview advisory normalization runtime smoke report

## 1. 阶段目标

本阶段执行 ZDoc Step 38：preview advisory normalization runtime smoke + smoke report。

目标是在 Step 35 preview advisory normalization fake-only implementation + deterministic tests 完成后，通过本地 loopback runtime smoke 验证 `/local-llm/preview-safe` enabled 场景是否能从真实 `qwen3:0.6b` runtime response 中形成 bounded preview advisory。

本次重点观察：

- enabled 场景是否继续 `calls_ollama=true`；
- enabled 场景是否从 `missing_preview_advisory / invalid_response` 改善为 `status=ok`；
- enabled 场景是否返回 advisory；
- suggestions / risk_notes 是否受控；
- 是否仍保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 是否未触发正式生成链、导出链、ZBid 写回链。

本步未直接请求 Ollama `/api/generate`。Ollama generate path 仅允许通过 `/local-llm/preview-safe` 间接验证。

## 2. 开始前 Git 状态

- 工作目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`c865ca69eb0c99b865ef9bb20a2abe69b77c07b2`
- `git status --short`：空
- `git diff --name-only`：空
- 标签：`v0.1.96-zdoc-preview-advisory-runtime-smoke-plan-refresh`
- 标签指向：`c865ca69eb0c99b865ef9bb20a2abe69b77c07b2`
- HEAD 等于标签 commit：是

前置条件满足后才继续 runtime smoke。

## 3. Ollama listener 处理方式

开始前检查 `127.0.0.1:11434`，发现已有本地 Ollama listener：

- PID：`14236`
- 监听地址：`127.0.0.1:11434`
- 处理方式：复用既有本地 listener
- 是否启用 2号窗口：否
- 是否运行新的 `ollama serve`：否
- 结束时处理方式：该 listener 非本步启动，未擅自停止

监听信息摘要：

```text
COMMAND   PID     USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
ollama  14236 youfeini    4u  IPv4 ...              0t0  TCP 127.0.0.1:11434 (LISTEN)
```

## 4. Ollama `/api/tags` 检查结果

仅执行允许的 tags 检查：

- 请求：`GET http://127.0.0.1:11434/api/tags`
- HTTP 状态：`200`
- 是否有效 JSON：是
- 本地模型数量：`7`
- 是否存在 `qwen3:0.6b`：是
- 本步使用模型名：`qwen3:0.6b`

本地模型摘要：

```text
qwen3-next:80b-a3b-instruct-q8_0
qwen3-coder:30b
deepseek-r1:32b
qwen3:30b
qwen3:14b
qwen3:8b
qwen3:0.6b
```

未下载模型，未 pull 模型，未自动更新模型。

## 5. output/job/export 前后状态

smoke 前：

```text
output=absent
job=absent
export=absent
```

smoke 后：

```text
output=absent
job=absent
export=absent
```

结论：本步未写 `output/`、`job/`、`export/`。

## 6. smoke payload

根据当前 `backend/app/routers/local_llm_preview_safe.py` 只读检查结果，本步使用 endpoint 兼容字段：

```json
{
  "request_id": "zdoc-step38-enabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "Please provide one short preview advisory and up to two suggestions for this minimal local runtime smoke text. This is only for preview-only validation.",
  "context_summary": "runtime smoke only; preview advisory; no write; no generation"
}
```

三组场景仅调整 `request_id`。payload 不含真实投标正文，不含敏感项目资料，仅用于 preview advisory；不要求生成正式章节正文，不包含正式输出字段，不触发生成链或导出链。

## 7. disabled 场景

环境变量：

```text
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

FastAPI 启动：

- 命令：`python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18753 --log-level warning`
- 附加环境：`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUNBUFFERED=1`
- PID：`30869`
- 监听地址：`127.0.0.1:18753`
- 请求路径：`POST http://127.0.0.1:18753/local-llm/preview-safe`

响应摘要：

- HTTP 状态：`200`
- `status`：`disabled`
- `ok`：`false`
- `enabled`：`false`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`false`
- `source`：`zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- advisory 是否存在：否
- suggestions 数量：`0`
- risk_notes / warnings 数量：`1`
- `error_type`：`null`
- `reason`：`feature_flag_disabled`

结论：disabled 场景 stable disabled，不调用 Ollama，不写盘，不触发正式链路。

FastAPI PID `30869` 已停止，`127.0.0.1:18753` 随后无监听。

## 8. adapter-off 场景

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

FastAPI 启动：

- 命令：`python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18753 --log-level warning`
- 附加环境：`ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUNBUFFERED=1`
- PID：`30968`
- 监听地址：`127.0.0.1:18753`
- 请求路径：`POST http://127.0.0.1:18753/local-llm/preview-safe`

过程说明：adapter-off 场景曾有一次 `env` 参数顺序错误的启动尝试，命令退出 `127`，未形成 listener，未发送 HTTP 请求，未写盘。随后使用正确环境变量顺序完成本场景 smoke。

响应摘要：

- HTTP 状态：`200`
- `status`：`ok`
- `ok`：`true`
- `enabled`：`true`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`false`
- `model`：`fake-local-llm`
- `source`：`zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- advisory 是否存在：是
- suggestions 数量：`3`
- risk_notes / warnings 数量：`0`
- `error_type`：`null`
- `reason`：`null`

结论：adapter-off 场景仍为 fake-only / controlled non-real path，`calls_ollama=false`，未进入 real runtime path，不写盘。

FastAPI PID `30968` 已停止，`127.0.0.1:18753` 随后无监听。

## 9. enabled real-Ollama normalization 场景

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

FastAPI 启动：

- 命令：`python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18753 --log-level warning`
- 附加环境：上述双开关、模型、timeout、num_predict，以及 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONUNBUFFERED=1`
- PID：`31033`
- 监听地址：`127.0.0.1:18753`
- 请求路径：`POST http://127.0.0.1:18753/local-llm/preview-safe`

响应摘要：

- HTTP 状态：`200`
- `status`：`ok`
- `ok`：`true`
- `enabled`：`true`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`true`
- `real_transport_enabled`：`true`
- `fake_transport_only`：`false`
- `model`：`qwen3:0.6b`
- `source`：`zdoc_real_ollama_preview_adapter_real_transport`
- advisory 是否存在：是
- advisory 长度：`386`
- suggestions 数量：`1`
- risk_notes / warnings 数量：`1`
- `preview_mode`：`thinking_only_fallback`
- `content_source`：`thinking`
- 是否出现 thinking fallback：是
- `error_type`：`null`
- `reason`：`null`
- 是否仍出现 `missing_preview_advisory`：否
- 是否仍出现 `invalid_response`：否
- 是否 controlled failure：否
- 是否未处理异常：否

结论：

- enabled 场景继续触发 real transport，`calls_ollama=true`；
- Step 35 normalization 修复后，本次真实 runtime enabled 场景从 Step 32 的 `invalid_response / missing_preview_advisory` 改善为 `status=ok`；
- 本次 advisory 来源为 `thinking_only_fallback`，不是普通 response 或结构化 JSON；
- thinking fallback 已截断，并通过 `preview_mode=thinking_only_fallback`、`content_source=thinking`、`risk_notes=["thinking_only_fallback"]` 标识；
- suggestions / risk_notes 数量受控；
- no-write / preview-only 边界保持稳定。

FastAPI PID `31033` 已停止，`127.0.0.1:18753` 随后无监听。

## 10. enabled 场景关键判定

- enabled 场景是否 `calls_ollama=true`：是
- enabled 场景是否 `status=ok`：是
- enabled 场景是否返回 advisory：是
- advisory 长度：`386`
- suggestions 数量：`1`
- risk_notes / warnings 数量：`1`
- 是否出现 thinking fallback：是
- 是否仍出现 `missing_preview_advisory`：否
- 是否仍出现 `invalid_response`：否
- 是否 controlled failure：否

本次 runtime smoke 证明真实 runtime 下 preview advisory normalization 已能形成 bounded advisory，但该 advisory 来自 thinking fallback，仍需后续复盘和质量评估边界设计。

## 11. 是否直接请求 Ollama `/api/generate`

否。

本步只直接请求：

- `GET http://127.0.0.1:11434/api/tags`
- `POST http://127.0.0.1:18753/local-llm/preview-safe`

enabled 场景是否触达 Ollama generate path 仅以 `/local-llm/preview-safe` 响应字段为准。本次响应显示：

- `calls_ollama=true`
- `real_transport_enabled=true`
- `source=zdoc_real_ollama_preview_adapter_real_transport`
- `generate_path=/api/generate`

因此本次结论是：未直接请求 Ollama `/api/generate`，但 safe endpoint 的 default real transport runtime path 已被间接触发。

## 12. 禁止路由检查

本步未请求：

- `/generate`
- `/export_docx`
- `/review/apply`

三组响应均保持或明确包含：

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`
- `writes_output=false`
- `writes_job=false`
- `writes_export=false`

## 13. 是否运行 pytest

未运行 pytest。

## 14. 是否下载或拉取模型

未下载模型，未 pull 模型，未自动更新模型。

## 15. 是否修改代码或 tests

未修改代码，未修改 tests。

本步只允许新增 smoke report 文档。

## 16. 是否生成正式文档或写 output/job/export

未生成正式文档。

未写：

- `output/`
- `job/`
- `export/`

未触发 DOCX / JSON / Markdown 正式导出。

## 17. 服务进程停止情况

FastAPI 进程停止情况：

- disabled 场景 PID `30869`：已停止；
- adapter-off 场景 PID `30968`：已停止；
- enabled 场景 PID `31033`：已停止。

Ollama listener：

- PID `14236`：既有 listener，非本步启动；
- 本步复用该 listener；
- 本步结束时未擅自停止。

## 18. 端口清理情况

- `127.0.0.1:18753`：本步结束前确认无监听；
- `127.0.0.1:11434`：仍由既有 Ollama listener PID `14236` 监听，因非本步启动，未停止。

## 19. 风险说明

主要风险如下：

- 风险 1：本次 `status=ok` 的 advisory 来自 thinking fallback，不代表模型已经稳定输出普通 response 或结构化 JSON；
- 风险 2：真实模型输出仍可能过短、空白、不稳定或只返回 thinking；
- 风险 3：thinking fallback 虽已截断，但仍可能被用户误解为正式正文；
- 风险 4：runtime smoke 成功可能被误判为可进入质量评测层或正式生成链；
- 风险 5：normalizer 可能把低质文本包装为 advisory，后续需要质量门禁；
- 风险 6：preview advisory 仍不得被写入正式方案、DOCX、export 或 ZBid。

## 20. 下一步建议

下一步建议为 ZDoc Step 39：preview advisory normalization runtime smoke review + thinking fallback quality gap design。

Step 39 应复盘本次 runtime smoke 已从 `missing_preview_advisory / invalid_response` 改善为 `status=ok`，同时明确新阶段核心风险转为 thinking fallback 质量、可解释性和正式链路隔离。

不得自动进入质量评测层，不得自动接正式生成链、DOCX 导出或 ZBid 写回。
