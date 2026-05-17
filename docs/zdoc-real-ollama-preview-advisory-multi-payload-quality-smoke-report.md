# ZDoc multi-payload preview advisory quality smoke report

## 1. 阶段目标

本阶段执行 ZDoc Step 45：multi-payload preview quality smoke + smoke report。

目标是在不修改代码、不修改 tests、不运行 pytest、不直接请求 Ollama `/api/generate`、不写 `output/job/export`、不触发正式生成链、导出链或 ZBid 写回链的前提下，通过 `/local-llm/preview-safe` 验证 Step 42 preview advisory quality gate 在真实 runtime 多 payload 场景下的表现。

本阶段重点观察：

- 多个 preview payload 是否均受控返回；
- enabled 场景是否继续 `calls_ollama=true`；
- `quality_status` / `quality_score` / `blockers` / `warnings` / `review_reasons` 是否可追踪；
- 高质量 payload 是否至少不被 P0/P4 拦截；
- 泛泛 payload 是否 `review_required` 或 `blocked`；
- 虚构风险 payload 是否 `blocked` 或至少 `review_required`；
- thinking fallback 是否被显式标记并降级；
- 所有正式链准入字段是否恒为 false；
- 是否仍保持 preview-only / no-write；
- 是否未触发正式生成链、导出链、ZBid 写回链。

## 2. 开始前 Git 状态

开始前只读核验结果：

- 当前目录：`/Users/youfeini/Desktop/文档生成系统`
- 当前分支：`main`
- 开始前 HEAD：`2a559f24c1f0ccaf228b4b33984939ca75761ecc`
- `git status --short`：空
- `git diff --name-only`：空
- 标签：`v0.1.103-zdoc-multi-payload-preview-quality-smoke-plan`
- 标签指向：`2a559f24c1f0ccaf228b4b33984939ca75761ecc`

前置条件满足后才执行 runtime smoke。

## 3. Ollama listener 处理方式

执行前检查 `127.0.0.1:11434`，发现已有本地 listener：

- 进程：`ollama`
- PID：`14236`
- 监听：`127.0.0.1:11434`
- 处理方式：复用既有本地 Ollama listener
- 是否重复启动 `ollama serve`：否
- 本步结束是否停止该 PID：否，因该 listener 为既有进程，本步未擅自停止

本步未启用 2号窗口启动新的 `ollama serve`。

## 4. Ollama `/api/tags` 检查结果

本步只允许直接检查：

```text
GET http://127.0.0.1:11434/api/tags
```

检查结果：

- HTTP 状态：`200`
- 是否有效 JSON：是
- 本地模型数量：`7`
- 是否存在 `qwen3:0.6b`：是

本步未直接请求 Ollama `/api/generate`。

## 5. 本地模型摘要

`/api/tags` 返回的模型摘要：

- `qwen3-next:80b-a3b-instruct-q8_0`
- `qwen3-coder:30b`
- `deepseek-r1:32b`
- `qwen3:30b`
- `qwen3:14b`
- `qwen3:8b`
- `qwen3:0.6b`

## 6. 使用模型

本步 enabled multi-payload 场景使用模型：

```text
qwen3:0.6b
```

enabled 场景环境变量：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

## 7. FastAPI 启动命令、PID、端口

FastAPI 仅监听：

```text
127.0.0.1:18754
```

启动命令均为：

```bash
/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 18754 --log-level warning
```

场景 PID：

- disabled 场景 FastAPI PID：`56517`
- adapter-off 场景 FastAPI PID：`56520`
- enabled multi-payload 场景 FastAPI PID：`56533`

本步只请求：

```text
POST http://127.0.0.1:18754/local-llm/preview-safe
```

本步没有请求 `/generate`、`/export_docx`、`/review/apply`，也没有直接请求 Ollama `/api/generate`。

## 8. output/job/export 前后状态

smoke 前：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

smoke 后：

- `output/`：不存在
- `job/`：不存在
- `export/`：不存在

结论：本步未写 `output/job/export`。

## 9. disabled 场景摘要

环境变量：

```bash
unset ZDOC_LOCAL_LLM_PREVIEW_ENABLED
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

请求路径：

```text
POST /local-llm/preview-safe
```

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
- `reason`：`feature_flag_disabled`
- `advisory` 是否存在：否
- `suggestions` 数量：`0`
- `risk_notes` 数量：`1`
- quality gate metadata：未出现
- 正式链准入字段：未出现 true

结论：disabled 场景 stable disabled，未调用 Ollama，未写盘，未触发正式链路。

## 10. adapter-off 场景摘要

环境变量：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
unset ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED
```

请求路径：

```text
POST /local-llm/preview-safe
```

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
- `source`：`zdoc_local_llm_preview_isolated_safe_endpoint_fake`
- `model`：`fake-local-llm`
- `advisory` 是否存在：是
- advisory 长度：`131`
- `suggestions` 数量：`3`
- `risk_notes` 数量：`0`
- quality gate metadata：未出现
- 正式链准入字段：未出现 true

结论：adapter-off 场景仍为 fake-only / non-real path，未构造 real runtime path，未写盘。

## 11. enabled multi-payload 逐项结果表

enabled 场景环境变量：

```bash
ZDOC_LOCAL_LLM_PREVIEW_ENABLED=true
ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED=true
ZDOC_OLLAMA_PREVIEW_MODEL=qwen3:0.6b
ZDOC_OLLAMA_PREVIEW_TIMEOUT=10
ZDOC_OLLAMA_PREVIEW_NUM_PREDICT=256
```

所有 enabled payload 均请求：

```text
POST /local-llm/preview-safe
```

逐项结果：

| Payload | 目的 | HTTP | status | calls_ollama | preview_mode | response_source | advisory_len | suggestions | risk/warnings | quality_status | quality_score | gate_level | blockers | review_reasons | 正式链准入 |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- |
| A | 高质量技术标建议型 | 200 | ok | true | text_fallback | response | 181 | 1 | 0 | preview_ok | 76 | P4 | 0 | 0 | 全 false |
| B | 泛泛模板话风险型 | 200 | ok | true | thinking_only_fallback | thinking | 385 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 全 false |
| C | 虚构风险诱发型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 全 false |
| D | thinking fallback 观察型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 全 false |
| E | 极简输入型 | 200 | ok | true | thinking_only_fallback | thinking | 386 | 1 | 1 | review_required | 28 | P2 | 0 | 1 | 全 false |
| F | 施工组织设计专项型 | 200 | ok | true | text_fallback | response | 128 | 2 | 0 | review_required | 46 | P3 | 0 | 2 | 全 false |

逐项结论：

- Payload A：`preview_ok`，未被 P0/P4 拦截，`formal_generation_allowed=false` 且所有正式链准入字段为 false。
- Payload B：`review_required`，主要原因为 `thinking_only_fallback_review_required`，满足泛泛 payload 应降级的预期。
- Payload C：`review_required`，主要原因为 thinking fallback 降级；未达到 blocked，但满足“blocked 或至少 review_required”的成功标准。
- Payload D：`review_required`，thinking fallback 被显式标记并降级。
- Payload E：`review_required`，极简输入未被误判为高质量。
- Payload F：`review_required`，`review_reasons` 包含 `advisory_may_be_unrelated` 和 `construction_specificity_review_required`，未被误判为正式链准入。

## 12. quality gate 统计汇总

enabled multi-payload 统计：

- `preview_ok` 数量：`1`
- `review_required` 数量：`5`
- `blocked` 数量：`0`
- `system_error` 数量：`0`
- thinking fallback 出现次数：`4`
- `calls_ollama=true` 的 payload 数量：`6`
- `status=ok` 的 payload 数量：`6`

本步证明 multi-payload 均受控返回，但也显示真实 runtime 下 thinking fallback 仍高频出现。

## 13. preview_ok 数量

`preview_ok` 数量为 `1`。

对应 payload：

- Payload A：高质量技术标建议型，`quality_score=76`，`gate_level=P4`。

说明：`preview_ok` 只代表 preview 阶段可展示，不代表 shadow generation 或正式链准入。

## 14. review_required 数量

`review_required` 数量为 `5`。

对应 payload：

- Payload B：泛泛模板话风险型；
- Payload C：虚构风险诱发型；
- Payload D：thinking fallback 观察型；
- Payload E：极简输入型；
- Payload F：施工组织设计专项型。

主要原因：

- Payload B/C/D/E 均为 `thinking_only_fallback_review_required`；
- Payload F 为 `advisory_may_be_unrelated` 与 `construction_specificity_review_required`。

## 15. blocked 数量

`blocked` 数量为 `0`。

说明：

- 本次没有 payload 被 P0 安全边界拦截；
- 本次没有 payload 被 quality gate 判定为 blocked；
- Payload C 虽为虚构风险诱发型，但真实 runtime 输出进入 thinking fallback，quality gate 将其降级为 `review_required`，没有形成 hallucination blocker。

该结果可接受，但暴露一个后续风险：如果真实模型输出没有复述虚构条款、规范编号或工程参数，当前 gate 可能只根据输出而非原始输入风险进行降级。后续如进入更深质量层，应考虑把 payload/input risk 也纳入 quality gate 上下文。

## 16. system_error 数量

`system_error` 数量为 `0`。

本步未出现 quality gate 自身异常或不可解析异常。

## 17. thinking fallback 出现次数

thinking fallback 出现次数为 `4`。

对应 payload：

- Payload B；
- Payload C；
- Payload D；
- Payload E。

这些 payload 均：

- `preview_mode=thinking_only_fallback`；
- `response_source=thinking`；
- `quality_status=review_required`；
- `gate_level=P2`；
- `warnings` 包含 `thinking_only_fallback`；
- `review_reasons` 包含 `thinking_only_fallback_review_required`；
- `shadow_candidate_allowed=false`。

结论：thinking fallback 已被显式标记并降级，但真实 runtime 仍较依赖 thinking fallback，不能解释为普通 response / JSON advisory 稳定。

## 18. formal_generation_allowed 是否恒 false

enabled multi-payload 场景中，所有 payload 的：

```text
formal_generation_allowed=false
```

disabled 与 adapter-off 场景未出现该 quality gate 字段，但也未出现 true。

## 19. shadow_candidate_allowed 是否恒 false

enabled multi-payload 场景中，所有 payload 的：

```text
shadow_candidate_allowed=false
```

disabled 与 adapter-off 场景未出现该 quality gate 字段，但也未出现 true。

## 20. writeback_allowed / export_allowed / zbid_writeback_allowed 是否恒 false

enabled multi-payload 场景中，所有 payload 均为：

```text
writeback_allowed=false
export_allowed=false
zbid_writeback_allowed=false
```

disabled 与 adapter-off 场景未出现这些 quality gate 字段，但也未出现 true。

结论：正式链准入字段未被打开。

## 21. 是否请求 `/generate`

否。

本步没有请求 `/generate`。

## 22. 是否请求 `/export_docx`

否。

本步没有请求 `/export_docx`。

## 23. 是否请求 `/review/apply`

否。

本步没有请求 `/review/apply`。

## 24. 是否直接请求 Ollama `/api/generate`

否。

本步只直接请求 Ollama：

```text
GET /api/tags
```

真实 generate path 仅通过 `/local-llm/preview-safe` 的 real transport 间接触发，未直接请求 Ollama `/api/generate`。

## 25. 是否写 output/job/export

否。

`output/`、`job/`、`export/` 前后均不存在。

## 26. 是否下载或拉取模型

否。

本步只检查本地已有模型列表，未执行 `ollama pull`，未下载或拉取任何模型。

## 27. 是否修改代码/tests

否。

本步未修改代码，未修改 tests。

## 28. 进程停止与端口清理情况

FastAPI 进程停止情况：

- disabled 场景 PID `56517`：已停止，停止后 `127.0.0.1:18754` 无监听；
- adapter-off 场景 PID `56520`：已停止，停止后 `127.0.0.1:18754` 无监听；
- enabled multi-payload 场景 PID `56533`：已停止，停止后 `127.0.0.1:18754` 无监听。

端口状态：

- smoke 前 `127.0.0.1:18754`：无监听；
- smoke 后 `127.0.0.1:18754`：无监听；
- smoke 后 `127.0.0.1:11434`：仍有既有 Ollama listener。

Ollama listener：

- 既有 PID：`14236`
- 本步未启动新 `ollama serve`
- 本步未停止既有 PID

## 29. 风险说明

本步主要风险：

- 多 payload 表现仍不完全稳定，6 个 enabled payload 中有 4 个依赖 `thinking_only_fallback`；
- Payload C 虚构风险诱发型被降级为 `review_required`，但未被 `blocked`，说明当前 gate 主要评价输出内容，尚未充分把输入侧 hallucination-risk 纳入拦截；
- Payload F 施工组织设计专项型被判为 `review_required`，说明真实模型输出的技术标专项具体性仍不足；
- `preview_ok` 只出现 1 次，不能证明多 payload 质量稳定；
- `status=ok` 不能等同于质量合格；
- `preview_ok` 不能解释为 shadow generation 或正式链准入；
- 后续若准入字段误置 true，可能污染正式生成链。

## 30. 下一步建议

下一步建议为 ZDoc Step 46：multi-payload preview quality smoke review + input-risk quality gate gap design。

该步骤应先做 docs-only 复盘，重点分析：

- thinking fallback 高频出现的质量风险；
- Payload C 虚构风险输入未被 blocked 的 input-risk gap；
- Payload F 技术标专项具体性不足；
- `preview_ok` 与正式链准入继续隔离；
- 是否需要把 payload/input risk 纳入 quality gate 上下文。

不得自动进入 shadow generation、正式生成链、DOCX 导出或 ZBid 写回。
