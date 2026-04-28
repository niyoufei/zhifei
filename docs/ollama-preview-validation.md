# ZDoc 手动 Ollama 预览 API 真实验证记录

## 验证范围

本记录对应 ZDoc 手动 Ollama 预览接口：

- API: `/actions/ollama/preview`
- 代码基线: `a7e08ec feat: add manual Ollama preview helper`
- 验证方式: FastAPI `TestClient` 真实调用后端路由
- 本地 Ollama: `http://localhost:11434`
- 模型: `qwen3:0.6b`

该接口仅用于人工预览和辅助复核，不属于文档主生成链。

## 环境变量

验证时使用进程级环境变量，不写入 `.env`：

```text
ZDOC_OLLAMA_PREVIEW_ENABLED=1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:0.6b
OLLAMA_TIMEOUT=60
```

## 真实验证结果

- Ollama 服务可访问。
- `qwen3:0.6b` 模型存在。
- `/actions/ollama/preview` 返回 HTTP 200。
- 成功模型调用返回 `ok=true`。
- 成功模型调用返回 `content` 非空。
- 返回内容前 300 字为：`信息不足。`
- `OLLAMA_MODEL=not-exist-model` 时接口不崩溃。
- 失败模型返回 fallback / error。
- 失败模型不写入任何结果文件。

## 主链隔离结果

验证期间已确认以下主链能力未被触发：

- 未触发 `run_autoplan`。
- 未触发 `create_job` / `update_job`。
- 未触发 `_save_outputs` / `save_output_artifacts`。
- 未触发 `LLMClient.__init__`。
- 未写 job / result bundle。
- 未接入 orchestrator。
- 未接入 provider / LLMClient 主链。
- 未自动改写正文。

## 边界说明

`/actions/ollama/preview` 是默认关闭的人工触发能力。启用后只调用本地 Ollama 进行只读预览增强，调用失败时返回 fallback / error，不影响文档生成、复核、导出、job 状态或 result bundle。

该能力不得作为以下链路的默认入口：

- 主生成链
- orchestrator
- provider / LLMClient
- Word / DOCX 导出
- 自动正文修复
- job / result bundle 写入

后续如需接入前端展示，应继续保持默认关闭、人工触发、失败回退、不写主链状态的边界。

## 前端接入边界

前端“本地模型预览”入口只允许作为人工按钮存在：

- 只调用既有 `/actions/ollama/preview`。
- 只展示本地模型返回的预览建议。
- 不自动写回正文。
- 不写 job / result bundle。
- 不调用 orchestrator。
- 不调用 provider / LLMClient 主链。
- 不改变生成 payload 或导出结果。
- 测试应使用 mock / helper 断言，不连接真实 Ollama。
