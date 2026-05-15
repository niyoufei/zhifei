# ZDoc real-Ollama preview safe endpoint runtime smoke report

## 1. 阶段目标

本报告记录 ZDoc Step 26：real-Ollama preview safe endpoint runtime smoke + controlled gap report。

本步允许本地 loopback 冒烟验证，但不修改代码，不修改 tests，不运行 pytest，不调用外部模型/API，不下载或拉取模型，不生成正式文档，不写 `output/job/export`，不触发 DOCX/JSON/Markdown 正式导出，不接 ZBid 正式写回。

根据 Step 25 前置计划，本步不得预设真实 `/api/generate` 已经接通。若 `/local-llm/preview-safe` enabled 场景返回 `fake_transport_required`、controlled failure 或 `calls_ollama=false`，必须记录为受控缺口，不得修改代码或扩大测试范围。

## 2. 开始前 Git 状态

当前目录：

```text
/Users/youfeini/Desktop/文档生成系统
```

当前分支：

```text
main
```

开始前 HEAD：

```text
ede2b21710ed5786b2482f58980c56599ee149d4
```

开始前 `git status --short`：

```text

```

开始前 `git diff --name-only`：

```text

```

前置标签：

```text
v0.1.84-zdoc-real-ollama-safe-endpoint-runtime-smoke-plan
```

标签指向：

```text
ede2b21710ed5786b2482f58980c56599ee149d4
```

前置条件满足：当前分支为 `main`，工作区 clean，无 diff，HEAD 与前置标签一致。

## 3. 只读实现确认

只读检查确认：

- `POST /local-llm/preview-safe` 位于 `backend/app/routers/local_llm_preview_safe.py`；
- endpoint 只允许 `context_summary`、`request_id`、`section_text`、`section_title`；
- enabled bridge path 调用 `_run_ollama_adapter_bridge`；
- `_run_ollama_adapter_bridge` 调用 `run_zdoc_ollama_preview`；
- 当前 bridge 使用 `SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT` 和 `SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT` 注入 transport；
- 默认 transport 为 `None`；
- `run_zdoc_ollama_preview` 在缺少 injected transport 时返回 controlled failure：`reason=fake_transport_required`；
- 当前 safe endpoint bridge 默认不会自动访问真实 `127.0.0.1:11434/api/generate`。

相关环境变量：

```text
ZDOC_LOCAL_LLM_PREVIEW_ENABLED
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
ZDOC_OLLAMA_PREVIEW_MODEL
ZDOC_OLLAMA_PREVIEW_TIMEOUT
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT
```

## 4. Ollama tags 检查结果

开始前检测到既有本地 Ollama listener：

```text
COMMAND   PID     USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
ollama  69916 youfeini    4u  IPv4 ...              0t0  TCP 127.0.0.1:11434 (LISTEN)
```

由于 `127.0.0.1:11434` 已有 listener，本步未再启动第二个 `ollama serve`，避免端口冲突。该 PID 不是本步启动，因此本步结束时未擅自停止该既有进程。

允许的 loopback 检查：

```text
GET http://127.0.0.1:11434/api/tags
```

结果：

```text
HTTP status=200
valid_json=true
model_count=7
has_qwen3_0_6b=true
```

## 5. 本地模型摘要

本地模型列表摘要：

```text
qwen3-next:80b-a3b-instruct-q8_0
qwen3-coder:30b
deepseek-r1:32b
qwen3:30b
qwen3:14b
qwen3:8b
qwen3:0.6b
```

本步使用模型名：

```text
qwen3:0.6b
```

未执行 `ollama pull`，未下载或拉取模型。

## 6. 写入面基线

runtime smoke 前写入面计数：

```text
output=0(absent)
job=0(absent)
export=0(absent)
backend/data/autoplan/jobs=87
build=1389
```

runtime smoke 后写入面计数：

```text
output=0(absent)
job=0(absent)
export=0(absent)
backend/data/autoplan/jobs=87
build=1389
```

结论：未写 `output/job/export`，`backend/data/autoplan/jobs` 和 `build` 文件计数未变化。

## 7. disabled 场景

启动命令：

```bash
env -u ZDOC_LOCAL_LLM_PREVIEW_ENABLED -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18751
```

FastAPI PID：

```text
70398
```

监听地址：

```text
127.0.0.1:18751
```

请求路径：

```text
POST http://127.0.0.1:18751/local-llm/preview-safe
```

payload：

```json
{
  "request_id": "zdoc-step26-disabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "Synthetic preview-only text for disabled runtime smoke.",
  "context_summary": "disabled runtime smoke; no write; no generation"
}
```

响应摘要：

```text
HTTP status=200
status=disabled
ok=false
enabled=false
preview_only=true
no_write=true
affects_generation=false
affects_export=false
calls_ollama=false
source=zdoc_local_llm_preview_isolated_safe_endpoint_fake
warning=local_llm_preview_safe_endpoint_disabled
reason=feature_flag_disabled
error_type=null
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
writes_output=false
writes_job=false
writes_export=false
```

服务停止情况：

```text
FastAPI PID 70398 stopped
127.0.0.1:18751 no listener after stop
```

## 8. adapter-off 场景

一次初始启动命令因 `env -u` 参数顺序错误直接退出，未启动服务，未形成监听。实际有效启动命令如下。

启动命令：

```bash
env -u ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18751
```

FastAPI PID：

```text
70456
```

监听地址：

```text
127.0.0.1:18751
```

请求路径：

```text
POST http://127.0.0.1:18751/local-llm/preview-safe
```

payload：

```json
{
  "request_id": "zdoc-step26-adapter-off",
  "section_title": "Runtime Smoke Preview",
  "section_text": "Synthetic preview-only text for adapter-off runtime smoke.",
  "context_summary": "adapter-off runtime smoke; no write; no generation"
}
```

响应摘要：

```text
HTTP status=200
status=ok
ok=true
enabled=true
preview_only=true
no_write=true
affects_generation=false
affects_export=false
calls_ollama=false
source=zdoc_local_llm_preview_isolated_safe_endpoint_fake
fake_only=true
real_adapter_bridge=false
advisory_present=true
advisory_length=165
suggestions_count=3
warning=null
reason=null
error_type=null
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
writes_output=false
writes_job=false
writes_export=false
```

服务停止情况：

```text
FastAPI PID 70456 stopped
127.0.0.1:18751 no listener after stop
```

## 9. real-Ollama enabled 场景

启动命令：

```bash
env ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b ZDOC_OLLAMA_PREVIEW_TIMEOUT=30 ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=64 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18751
```

FastAPI PID：

```text
70495
```

监听地址：

```text
127.0.0.1:18751
```

请求路径：

```text
POST http://127.0.0.1:18751/local-llm/preview-safe
```

payload：

```json
{
  "request_id": "zdoc-step26-enabled",
  "section_title": "Runtime Smoke Preview",
  "section_text": "Synthetic preview-only text. Check for missing risk notes and keep this advisory bounded.",
  "context_summary": "enabled runtime smoke; local loopback only; no write; no generation"
}
```

响应摘要：

```text
HTTP status=200
status=failure
ok=false
enabled=true
adapter_enabled=true
preview_only=true
no_write=true
affects_generation=false
affects_export=false
calls_ollama=false
model=
source=zdoc_real_ollama_preview_adapter_fake_transport
entry_source=zdoc_local_llm_preview_isolated_safe_endpoint_real_ollama_adapter
fake_only=false
real_adapter_bridge=true
fake_transport_only=true
real_transport_enabled=false
advisory_present=false
advisory_length=0
suggestions_count=0
warning=transport_failure
risk_notes=["transport_failure"]
error_type=transport_failure
reason=fake_transport_required
calls_generate_route=false
calls_export_docx_route=false
calls_review_apply_route=false
triggers_generation_chain=false
triggers_export_chain=false
writes_output=false
writes_job=false
writes_export=false
calls_external_model_api=false
downloads_models=false
pulls_models=false
```

特别记录：

- 是否进入 real-Ollama path：未进入默认真实 network transport；进入了 safe endpoint real-adapter bridge，但 adapter 返回 `fake_transport_required`；
- 是否返回 `calls_ollama=true`：否；
- 是否返回 `fake_transport_required`：是；
- 是否为 controlled failure：是；
- 是否出现未处理异常：否；
- 是否保持 no-write：是；
- 是否写 `output/job/export`：否；
- 是否触发正式生成链或导出链：否。

服务停止情况：

```text
FastAPI PID 70495 stopped
127.0.0.1:18751 no listener after stop
```

## 10. `/api/generate` 与正式路由访问边界

本步只直接访问：

```text
GET http://127.0.0.1:11434/api/tags
POST http://127.0.0.1:18751/local-llm/preview-safe
```

本步未直接请求：

```text
POST http://127.0.0.1:11434/api/generate
```

本步未请求：

```text
/generate
/export_docx
/review/apply
```

enabled 响应显示：

```text
calls_ollama=false
reason=fake_transport_required
real_transport_enabled=false
```

因此，本次 smoke 未证明真实 Ollama `/api/generate` 端到端可用。它证明了当前 runtime 下 safe endpoint 的 real-adapter bridge 缺少默认真实 transport，且该缺口以 controlled failure 形式暴露。

## 11. 进程与端口清理

FastAPI 进程：

```text
70398 stopped
70456 stopped
70495 stopped
```

FastAPI 端口：

```text
127.0.0.1:18751 no listener
```

Ollama 进程：

```text
PID 69916 was already listening before this step
PID 69916 still listening after this step
```

Ollama 端口：

```text
127.0.0.1:11434 still held by pre-existing Ollama listener PID 69916
```

处理说明：该 Ollama listener 不是本步启动，未擅自停止非本步进程。

## 12. 禁止事项执行结果

```text
是否运行 pytest：否
是否直接请求 Ollama /api/generate：否
是否请求 /generate：否
是否请求 /export_docx：否
是否请求 /review/apply：否
是否调用外部模型/API：否
是否下载或拉取模型：否
是否生成正式文档：否
是否写 output/job/export：否
是否触发 DOCX/JSON/Markdown 正式导出：否
是否修改代码/tests：否
是否接 ZBid 正式写回：否
```

## 13. 风险说明

主要风险：

- 当前 endpoint bridge 在 runtime 下仍未接入默认真实 transport，enabled 场景不会自动触达真实 `/api/generate`；
- 如果后续新增默认 real transport，最大风险仍是误触正式生成链、导出链或写盘；
- 真实模型输出仍未验证，thinking-only、空响应和异常响应在 runtime 下仍可能与 fake transport 表现不同；
- 用户可能误以为 preview advisory 已写入正式方案，因此后续 UI/report 必须继续显式标记 preview-only/no-write；
- `127.0.0.1:11434` 存在既有 Ollama listener，本步未停止该非本步进程，后续 smoke 前仍需重新确认端口归属。

## 14. 下一步建议

下一步建议为 ZDoc Step 27：real-Ollama preview safe endpoint default real transport gap design。

该步骤应仅设计如何在保持 default-off、preview-only、no-write、loopback-only 和 no-download/no-pull 边界下，为 safe endpoint bridge 增加可审计的默认 real transport 或 runtime-only transport injection。

不得自动修改 real transport，不得自动进入正式生成链、导出链或 ZBid 写回。
