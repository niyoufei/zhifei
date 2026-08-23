# LOCAL-LAUNCHER-027N-R5B-COMFYUI-WORKFLOW-RUNTIME-PRECHECK-SCAFFOLD-IMPLEMENTATION-GATE

## 当前基线

- baseline commit: `c404ef1371c0aa7635a94dda34d9dea30be2cc6d`
- baseline tag: `v0.1.718-local-launcher-027n-r4b-comfyui-workflow-bridge-scaffold-baseline`
- baseline PR: `#74`
- node: `LOCAL-LAUNCHER-027N-R5B-COMFYUI-WORKFLOW-RUNTIME-PRECHECK-SCAFFOLD-IMPLEMENTATION-GATE`

## 新增文件清单

- `image_generation/precheck/__init__.py`
- `image_generation/precheck/comfyui_precheck_models.py`
- `image_generation/precheck/comfyui_precheck_plan.py`
- `image_generation/precheck/comfyui_precheck_validator.py`
- `image_generation/precheck/comfyui_precheck_reporter.py`
- `configs/comfyui-runtime-precheck-policy.json`
- `docs/zdoc-local-launcher-027n-r5b-comfyui-workflow-runtime-precheck-scaffold-gate.md`

## R5B 静态 precheck 能做什么

R5B 只提供静态 scaffold，可检查：

- registry / manifest / schema / policy JSON 是否存在且可解析；
- registry 是否仍包含 3 类 workflow；
- `workflow_json_status` 是否仍为 `pending_real_workflow`；
- `workflow_json_ref` 是否为 `null` 或环境无关相对引用；
- `runtime_enabled` 是否均为 `false`；
- `no_video_generation` 是否均为 `true`；
- input binding profile 是否完整；
- output policy 是否限制单图、禁止批量、禁止自动上传；
- prompt template 的 `workflow_contract_id` 映射是否完整；
- `video_generation_enabled=false` 是否保持成立；
- runtime allow 字段是否全部保持 `false`。

## R5B 不能做什么

R5B 不执行真实环境检查，不执行运行态动作：

- 不启动 ComfyUI；
- 不启动 backend；
- 不启动 frontend；
- 不启动 Ollama；
- 不访问 localhost；
- 不检查真实端口状态；
- 不读取模型权重；
- 不读取 `.env`；
- 不读取 `~/.ollama/models`；
- 不扫描全盘；
- 不执行真实 workflow；
- 不做 workflow dry run；
- 不运行推理；
- 不生成图片；
- 不下载模型；
- 不部署视频生成模型。

## 与 R4B workflow bridge scaffold 的关系

R4B 建立了 workflow registry、contract schema、manifest、workflow bridge、validator、resolver、input binding、output policy 等静态表面。R5B 不改变 R4B 文件，只在 `image_generation/precheck/` 中增加对这些静态表面的 precheck scaffold。

R5B 的 validator 复核 R4B 约束是否仍成立，重点包括：

- 3 个 workflow contract 仍存在；
- manifest 仍为 `pending_real_workflow`；
- workflow JSON 引用仍不绑定本机绝对路径；
- runtime 仍未启用；
- 输出仍为单图 local-only 策略；
- 视频生成仍未启用。

## 与 runtime_governance/precheck 的关系

`runtime_governance/precheck` 是已有的本地 launcher runtime precheck engine，主要基于外部传入的 repo、端口、进程和 lock context 做静态判定。R5B 的 `image_generation/precheck` 不接管该 engine，也不启动它；本节点只为 ComfyUI workflow bridge 增加独立的静态 plan / validate / report scaffold。

后续如需接入 runtime_governance/precheck，应在单独授权节点中设计 adapter，并保持 ComfyUI、localhost、端口、模型目录等真实环境访问边界。

## R5C 后续显式授权边界

R5C 建议只做 PR 静态复核。以下环境 precheck 即使已经被 R5B 建模，也不得在 R5B 执行：

- ComfyUI 安装路径存在性；
- workflow JSON 文件存在性；
- custom nodes 存在性；
- 输出目录可写性；
- 端口可用性；
- 模型引用是否可解析。

这些检查需要后续用户显式授权。

## R6 单图生成边界

R6 或更后续节点才可在显式授权下进入受控单图生成。R5B 不执行：

- 启动 ComfyUI；
- 访问 localhost；
- service health check；
- 读取真实模型目录；
- workflow dry run；
- 生成图片。

## 视频生成边界

视频生成暂不部署：

- `video_generation_enabled=false`；
- 不定义 video workflow runtime；
- 不做 video precheck；
- 不下载视频模型；
- 不部署视频生成模型。

## 本节点禁触确认

- 本节点未启动 ComfyUI。
- 本节点未访问 localhost。
- 本节点未检查真实端口。
- 本节点未推理。
- 本节点未生图。
- 本节点未执行 workflow dry run。
- 本节点未读取模型权重。
- 本节点未读取 `.env`。
- 本节点未读取 `~/.ollama/models`。
- 本节点未部署视频生成模型。
