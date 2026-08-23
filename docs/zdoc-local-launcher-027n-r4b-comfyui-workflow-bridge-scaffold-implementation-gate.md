# LOCAL-LAUNCHER-027N-R4B-COMFYUI-WORKFLOW-BRIDGE-SCAFFOLD-IMPLEMENTATION-GATE

## 当前基线

- 起点 main / origin/main / 远端 main：`d82698d3a864f7147cbf8215c596e57ec3a24747`
- 027N baseline tag：`v0.1.717-local-launcher-027n-image-generation-router-baseline`
- 本节点性质：R4B 静态 bridge scaffold implementation gate。

## 新增文件清单

- `configs/image-generation-workflow-registry.json`
- `configs/image-generation-workflow-contract-schema.json`
- `configs/comfyui-workflow-manifest.json`
- `image_generation/workflows/__init__.py`
- `image_generation/workflows/workflow_bridge.py`
- `image_generation/workflows/workflow_validator.py`
- `image_generation/workflows/workflow_path_resolver.py`
- `image_generation/workflows/workflow_input_binding.py`
- `image_generation/workflows/workflow_output_policy.py`
- `docs/zdoc-local-launcher-027n-r4b-comfyui-workflow-bridge-scaffold-implementation-gate.md`

## registry / schema / manifest 设计

`configs/image-generation-workflow-registry.json` 登记 3 个静态 workflow：

- `qwen_image_text_to_image`
- `qwen_image_edit_image_to_image`
- `flux_realistic_text_to_image`

所有 workflow registry entry 均保持 `runtime_enabled=false`、`no_video_generation=true`、`workflow_json_status=pending_real_workflow`。registry 只登记环境无关 workflow 引用，不写死本机绝对模型路径。

`configs/image-generation-workflow-contract-schema.json` 约束 `workflow_id`、`intended_model`、`required_inputs`、`output_expectations`、`safety_policy`、`no_video_generation`、`runtime_forbidden`、`runtime_enabled`、`allowed_task_type`、`disabled_video_generation`。

`configs/comfyui-workflow-manifest.json` 记录 workflow JSON 引用、节点类型摘要、模型引用 id、自定义节点需求、input binding profile、output policy id 和 R5 precheck 状态。真实 workflow JSON 尚未接入，因此当前 `workflow_json_ref=null` 且 `workflow_json_status=pending_real_workflow`。

## bridge / validator / resolver / binding / output policy 边界

- `workflow_bridge.py` 只从 registry、manifest 和 prompt template 生成静态 binding plan。
- `workflow_validator.py` 只做 JSON 字段、映射、`runtime_enabled=false`、`no_video_generation=true` 等静态校验。
- `workflow_path_resolver.py` 只解析相对 workflow JSON 引用，不读取模型权重，不扫描全盘，不读取 `.env`。
- `workflow_input_binding.py` 显式支持 `prompt`、`negative_prompt`、`width`、`height`、`seed`、`steps`、`cfg`、`sampler`、`scheduler`，并仅对 image-edit contract 声明 `source_image`。
- `workflow_output_policy.py` 只记录单图输出限制、固定输出目录策略、文件命名策略、seed/provenance 记录、禁止自动上传、禁止批量生成、禁止读取无关文件。

## 三类模型接入策略

- Qwen-Image：`text_to_image`，优先使用 `qwen_prompt_zh`，独立 workflow `qwen_image_text_to_image`，不写死模型绝对路径，R4B `runtime_enabled=false`。
- Qwen-Image-Edit：`image_to_image`，使用中文编辑 prompt，显式声明 `source_image`，不读取无关图片，独立 workflow `qwen_image_edit_image_to_image`，R4B `runtime_enabled=false`。
- FLUX.1-dev：写实 `text_to_image`，优先使用 `flux_prompt_en`，独立 workflow `flux_realistic_text_to_image`，不写死模型绝对路径，R4B `runtime_enabled=false`。

## 视频生成边界

视频生成暂不部署。R4B 不新增 video workflow runtime，不新增视频模型 enabled registry entry，不部署视频模型，不下载视频模型，不推理视频。所有未来扩展字段保持 disabled。

## R5 / R6 前置条件

R5 才允许做运行态 precheck，且必须在用户显式授权后检查 ComfyUI 安装、真实 workflow JSON 存在且可解析、节点类型满足 contract、模型文件存在、自定义节点存在、输出目录可写、端口可用。R5 之前不得自动启动 ComfyUI。

R6 才允许受控单图生成，且必须满足用户显式授权、R5 precheck 已通过、workflow contract 已通过、只生成 1 张受控图片、固定输出目录、固定 prompt、固定或记录 seed、不批量生成、不自动上传、不读取无关文件。

## 本节点未执行事项

- 未启动 ComfyUI。
- 未运行生图推理。
- 未生成图片。
- 未读取模型权重。
- 未读取 `~/.ollama/models`。
- 未读取 `.env` 或密钥文件。
- 未启动 Ollama。
- 未访问 localhost / 127.0.0.1。
- 未运行测试套件、构建或安装。
- 未部署视频生成模型。
