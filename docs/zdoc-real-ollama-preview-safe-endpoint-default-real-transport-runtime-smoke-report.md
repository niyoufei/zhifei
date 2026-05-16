# ZDoc real-Ollama preview safe endpoint default real transport runtime smoke report

## 1. 阶段目标

本阶段执行 ZDoc Step 32：real-Ollama preview safe endpoint runtime smoke + smoke report。

目标是在 Step 29 已完成 default real transport wiring 的前提下，通过本地 loopback runtime smoke 验证 `/local-llm/preview-safe` 在双开关开启后是否进入 default real transport runtime path，并重点观察：

- enabled 场景是否不再返回 `fake_transport_required`；
- enabled 场景是否出现 `calls_ollama=true`；
- enabled 场景是否保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 是否仍不触发正式 `/generate`、`/export_docx`、`/review/apply`；
- 是否不写 `output/`、`job/`、`export/`。

本步未直接请求 Ollama `/api/generate`。Ollama generate path 仅允许通过 `/local-llm/preview-safe` 间接验证。

## 2. 开始前 Git 状态

- 工作目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`1e2ac19a43ce64bfdeeb7e60b4b5664f2e6c515c`
- `git status --short`：空
- `git diff --name-only`：空
- 标签：`v0.1.90-zdoc-real-ollama-runtime-smoke-plan-refresh`
- 标签指向：`1e2ac19a43ce64bfdeeb7e60b4b5664f2e6c515c`
- HEAD 等于标签 commit：是

前置条件满足后才继续 runtime smoke。

## 3. Ollama listener 处理方式

开始前检查 `127.0.0.1:11434`，发现已有本地 Ollama listener：

- PID：`14236`
- 监听地址：`127.0.0.1:11434`
- 处理方式：复用既有本地 listener
- 是否启动 2号窗口：否
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

未下载模型，未 pull 模型。

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

本步根据当前 `local_llm_preview_safe.py` 只读检查结果，使用 endpoint 兼容的最小 payload 字段：

```json
{
  "request_id": "zdoc-step32-enabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "This is a minimal local runtime smoke payload for preview-only validation.",
  "context_summary": "runtime smoke only; preview advisory; no write; no generation"
}
```

三组场景仅调整 `request_id`，payload 不含真实投标正文、不含敏感项目资料，仅用于 preview advisory。

## 7. disabled 场景

环境变量：

```text
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

FastAPI 启动：

- 命令：`/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18752`
- PID：`14677`
- 监听地址：`127.0.0.1:18752`
- 请求路径：`POST http://127.0.0.1:18752/local-llm/preview-safe`

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
- `failure_reason`：`feature_flag_disabled`
- `risk_notes`：`local_llm_preview_safe_endpoint_disabled`

结论：disabled 场景 stable disabled，不调用 Ollama，不写盘，不触发正式链路。

FastAPI PID `14677` 已停止，`127.0.0.1:18752` 随后无监听。

## 8. adapter-off 场景

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

FastAPI 启动：

- 命令：`/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18752`
- PID：`14682`
- 监听地址：`127.0.0.1:18752`
- 请求路径：`POST http://127.0.0.1:18752/local-llm/preview-safe`

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
- `advisory`：存在
- `suggestions` 数量：`3`
- `risk_notes`：空

结论：adapter-off 场景仍为 fake-only / non-real path，`calls_ollama=false`，未进入 real runtime path，不写盘。

FastAPI PID `14682` 已停止，`127.0.0.1:18752` 随后无监听。

## 9. enabled default real transport 场景

环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=128
```

FastAPI 启动：

- 命令：`/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18752`
- PID：`14691`
- 监听地址：`127.0.0.1:18752`
- 请求路径：`POST http://127.0.0.1:18752/local-llm/preview-safe`

响应摘要：

- HTTP 状态：`200`
- `status`：`failure`
- `ok`：`false`
- `enabled`：`true`
- `preview_only`：`true`
- `no_write`：`true`
- `affects_generation`：`false`
- `affects_export`：`false`
- `calls_ollama`：`true`
- `model`：`qwen3:0.6b`
- `source`：`zdoc_real_ollama_preview_adapter_real_transport`
- `real_transport_enabled`：`true`
- `fake_transport_only`：`false`
- `error_type`：`invalid_response`
- `failure_reason`：`missing_preview_advisory`
- `risk_notes`：`invalid_response`
- `advisory`：不存在
- `suggestions` 数量：`0`
- 是否仍出现 `fake_transport_required`：否
- 是否 controlled failure：是
- 是否未处理异常：否

结论：

- Step 29 后 default real transport runtime path 已触发；
- enabled 场景不再返回 `fake_transport_required`；
- enabled 场景出现 `calls_ollama=true`；
- 本次真实模型 runtime 结果为受控失败：`invalid_response / missing_preview_advisory`；
- 本次未证明真实模型可返回可用 advisory；
- no-write / preview-only 边界保持稳定。

FastAPI PID `14691` 已停止，`127.0.0.1:18752` 随后无监听。

## 10. 是否直接请求 Ollama `/api/generate`

否。

本步只直接请求：

- `GET http://127.0.0.1:11434/api/tags`
- `POST http://127.0.0.1:18752/local-llm/preview-safe`

enabled 场景是否触达 Ollama generate path 仅以 `/local-llm/preview-safe` 响应字段为准。本次响应显示：

- `calls_ollama=true`
- `real_transport_enabled=true`
- `source=zdoc_real_ollama_preview_adapter_real_transport`
- `generate_path=/api/generate`

因此本次结论是：未直接请求 Ollama `/api/generate`，但 safe endpoint 的 default real transport runtime path 已被间接触发。

## 11. 禁止路由检查

本步未请求：

- `/generate`
- `/export_docx`
- `/review/apply`

三组响应均保持：

- `calls_generate_route=false`
- `calls_export_docx_route=false`
- `calls_review_apply_route=false`
- `triggers_generation_chain=false`
- `triggers_export_chain=false`

## 12. 是否运行 pytest

未运行。

## 13. 是否下载或拉取模型

未下载模型，未 pull 模型，未自动更新模型。

## 14. 是否修改代码或 tests

未修改代码，未修改 tests。

本步只允许新增 smoke report 文档。

## 15. 是否生成正式文档或写 output/job/export

未生成正式文档，未写 `output/`、`job/`、`export/`。

未触发 DOCX / JSON / Markdown 正式导出。

## 16. 是否接 ZBid 正式写回

未接入 ZBid 正式写回。

## 17. 服务进程停止情况

本步启动的 FastAPI 进程均已停止：

- disabled 场景 FastAPI PID：`14677`，已停止
- adapter-off 场景 FastAPI PID：`14682`，已停止
- enabled 场景 FastAPI PID：`14691`，已停止

本步未启动新的 `ollama serve`。

既有 Ollama listener：

- PID：`14236`
- 处理方式：复用既有 listener，结束时未擅自停止

## 18. 端口清理情况

结束后检查：

- `127.0.0.1:18752`：无监听
- `127.0.0.1:11434`：仍由既有 Ollama listener PID `14236` 监听

`127.0.0.1:18752` 未留下服务进程。

## 19. 核心结论

本次 Step 32 runtime smoke 证明：

- disabled 场景仍 stable disabled，`calls_ollama=false`；
- adapter-off 场景仍 fake-only / non-real path，`calls_ollama=false`；
- enabled 双开关场景不再返回 `fake_transport_required`；
- enabled 双开关场景已进入 default real transport runtime path；
- enabled 双开关场景返回 `calls_ollama=true`；
- enabled 双开关场景本次结果为 controlled failure：`invalid_response / missing_preview_advisory`；
- 所有场景均保持 `preview_only=true`、`no_write=true`、`affects_generation=false`、`affects_export=false`；
- 本步未触发正式生成链、正式导出链或 ZBid 写回；
- 本步未写 `output/`、`job/`、`export/`。

本次尚未证明真实模型 `qwen3:0.6b` 能通过 safe endpoint 返回可用 bounded preview advisory。

## 20. 风险说明

- 风险 1：真实 runtime 已进入 default real transport path，但模型输出被归类为 `missing_preview_advisory`，说明 prompt / normalization / response schema 仍可能存在质量或兼容缺口。
- 风险 2：`calls_ollama=true` 只证明 runtime path 被触发，不等于 advisory 质量可用于后续人工评审。
- 风险 3：真实模型输出可能不稳定，后续仍需多样本和受控质量评测。
- 风险 4：thinking-only 或空响应仍可能导致 bounded preview 不可用，不能直接写入正式正文。
- 风险 5：后续若扩大到正式生成链、导出链或 ZBid 写回，仍存在误触写盘或误写正式方案风险。
- 风险 6：本步复用既有 Ollama listener，未控制该进程生命周期，结束时按边界未擅自停止。

## 21. 下一步建议

下一步建议为 ZDoc Step 33：real-Ollama preview safe endpoint runtime smoke review + `invalid_response/missing_preview_advisory` gap design。

该步骤应先做 docs-only 复盘或缺口设计，重点分析真实模型响应为什么未形成可用 advisory，并设计 prompt / normalization / bounded response 的 deterministic tests。不得直接进入质量评测层，不得直接接正式生成链、导出链或 ZBid 写回。
