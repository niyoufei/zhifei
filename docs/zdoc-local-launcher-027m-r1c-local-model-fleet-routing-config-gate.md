# LOCAL-LAUNCHER-027M-R1C-LOCAL-MODEL-FLEET-ROUTING-CONFIG-GATE

## 基线

- 基线 commit：`755a958ba2cba066f48395be4391947ae446d435`
- 基线 tag：`v0.1.715-local-launcher-027l-post-merge-main-baseline`
- 当前节点性质：本地模型舰队 routing 配置落地节点。

## 节点边界

本节点只落地系统级 routing 配置和 backend Ollama provider 默认模型，不修改 `app.py`。`app.py` 中的 `qwen3:0.6b` 仍视为 frontend 预览 / 手动预览默认，是否同步 routing 留到后续 UI wiring 节点。

本节点不启动 Ollama，不运行模型推理，不访问 localhost，不读取 runtime、PID、log、`.env`、密钥文件或 `~/.ollama/models`。

## R0C / R1A / R1B 成果摘要

- R0C：确认本节点承接本机 Ollama manifest 结果，只将已下载模型写入静态治理配置，不把 manifest 证据表述为运行态推理通过。
- R1A：确认旧 backend 默认模型为 `qwen3:0.6b`，本节点仅允许替换 `backend/zhifei_autoplan/providers/ollama_provider.py` 中的 `DEFAULT_MODEL` 常量值。
- R1B：确认本地模型舰队 routing 口径，高质量默认模型使用 `qwen3.6:35b`，稳定主力使用 `qwen3:30b`，顶级手动质量模型使用 `qwen3-next:80b-a3b-instruct-q8_0`，DeepSeek 推理模型分为 70B 高阶和 32B 标准，代码模型使用 `qwen3-coder:30b`。

## 本机 manifest 已确认模型

本机 Ollama manifest 已确认 9 个语言模型：

1. `qwen3:0.6b`
2. `qwen3:8b`
3. `qwen3:14b`
4. `qwen3:30b`
5. `qwen3-coder:30b`
6. `deepseek-r1:32b`
7. `deepseek-r1:70b`
8. `qwen3.6:35b`
9. `qwen3-next:80b-a3b-instruct-q8_0`

## Backend 默认模型变更

- 当前旧 backend 默认模型：`qwen3:0.6b`
- 新 backend 默认模型：`qwen3.6:35b`

## Routing 口径

- 高质量默认模型：`qwen3.6:35b`
- 稳定主力模型：`qwen3:30b`
- 顶级手动质量模型：`qwen3-next:80b-a3b-instruct-q8_0`
- DeepSeek 高阶推理模型：`deepseek-r1:70b`
- DeepSeek 标准推理模型：`deepseek-r1:32b`
- 代码模型：`qwen3-coder:30b`
- 平衡备用模型：`qwen3:14b`
- 最小本地 baseline：`qwen3:8b`
- 轻量 fallback：`qwen3:0.6b`

## 模型保留策略

必须保留：

- `qwen3.6:35b`
- `qwen3:30b`
- `qwen3-next:80b-a3b-instruct-q8_0`
- `deepseek-r1:70b`
- `deepseek-r1:32b`
- `qwen3-coder:30b`

建议保留：

- `qwen3:14b`
- `qwen3:8b`

routing 替换后删除候选：

- `qwen3:0.6b`

## 生图与视频生成

- 生图模型规划第一阶段：`Qwen-Image`、`Qwen-Image-Edit`
- 生图模型规划第二阶段：`FLUX.1-dev`、`Stable Diffusion 3.5 Large`、`SDXL`、`ControlNet`
- `image_generation.enabled=false`
- `video_generation_enabled=false`
- 视频生成暂不部署。

## Activation Policy

- 禁止自动 pull 模型。
- 禁止自动启动 Ollama。
- 禁止自动运行模型推理。
- 启动前必须重新进行 runtime inventory。
- 启动前必须经过 precheck engine allow。

## 静态校验结果

- `python3 -m json.tool configs/local-model-fleet-routing.json >/tmp/zhifei-027m-r1c-routing-json-check.txt`：通过。
- `python3 -m compileall backend/zhifei_autoplan/providers`：通过。
- `git diff --check`：通过。

## 后续建议节点

`LOCAL-LAUNCHER-027M-R2-LOCAL-MODEL-FLEET-ROUTING-PR-REVIEW-GATE`
