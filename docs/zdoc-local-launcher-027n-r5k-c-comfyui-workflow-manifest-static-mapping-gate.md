# LOCAL-LAUNCHER-027N-R5K-C-COMFYUI-WORKFLOW-MANIFEST-STATIC-MAPPING-IMPLEMENTATION-GATE

## 当前基线

- main / origin/main / 远端 main: `175511be5b3092458efea5684d2fef60c32def2a`
- R5B baseline tag: `v0.1.719-local-launcher-027n-r5b-comfyui-workflow-runtime-precheck-scaffold-baseline`
- R5B baseline tag 指向: `175511be5b3092458efea5684d2fef60c32def2a`
- 本节点性质: R5K-C 静态 manifest mapping implementation gate。

## R5K-B 映射依据

R5K-B 已确认当前 manifest 和 registry 只登记 3 个 workflow:

- `qwen_image_text_to_image`
- `qwen_image_edit_image_to_image`
- `flux_realistic_text_to_image`

R5K-B 已发现可用于静态映射的 ComfyUI blueprint 候选:

- `Text to Image (Qwen-Image).json`
- `Text to Image (Qwen-Image 2512).json`
- `Image Edit (Qwen 2509).json`
- `Image Edit (Qwen 2511).json`
- `Text to Image (Flux.1 Dev).json`

本节点只把 manifest 中的 `workflow_json_ref` 从 `null` 更新为环境无关的 `blueprints/*.json` 相对引用，不检查这些文件在目标环境是否存在或可执行。

## Manifest 映射方案

| workflow_id | workflow_json_ref | alternative_workflow_json_refs | mapping_confidence | manual_confirmation_required | model_reference_hint |
| --- | --- | --- | --- | --- | --- |
| `qwen_image_text_to_image` | `blueprints/Text to Image (Qwen-Image).json` | `blueprints/Text to Image (Qwen-Image 2512).json` | `HIGH` | `false` | `qwen_image_fp8_e4m3fn.safetensors` |
| `qwen_image_edit_image_to_image` | `blueprints/Image Edit (Qwen 2511).json` | `blueprints/Image Edit (Qwen 2509).json` | `MEDIUM` | `true` | `qwen_image_edit_2511_bf16.safetensors` |
| `flux_realistic_text_to_image` | `blueprints/Text to Image (Flux.1 Dev).json` | none | `HIGH` | `false` | `flux1-dev.safetensors` |

## 默认选择说明

Qwen-Image text-to-image 默认选择 `Text to Image (Qwen-Image).json`，因为 R5K-B 对该文件给出 HIGH 置信度，且它是无版本后缀的基础候选，更适合作为当前稳定默认映射。`Text to Image (Qwen-Image 2512).json` 保留为 alternative，等待后续节点确认 2512 是否应升级为默认版本。

Qwen image edit 默认选择 `Image Edit (Qwen 2511).json`，因为 R5K-B 已将其作为推荐 edit 映射，且静态模型引用指向 `qwen_image_edit_2511_bf16.safetensors`。该映射保持 `manual_confirmation_required=true`，原因是 2511 是否作为默认 edit 版本，以及多图输入是否纳入当前 binding，仍需后续确认。

FLUX realistic text-to-image 默认选择 `Text to Image (Flux.1 Dev).json`，因为该 blueprint 名称与 `flux_realistic_text_to_image` 的模型族和任务类型一致，R5K-B 置信度为 HIGH，并且静态模型引用提示为 `flux1-dev.safetensors`。

## mapped_static_unverified 语义

`mapped_static_unverified` 只表示:

- 已建立静态 blueprint 文件名映射；
- 引用是环境无关相对路径；
- 尚未验证目标环境中 workflow 文件可执行；
- 尚未检查模型文件存在性；
- 尚未访问 localhost；
- 尚未启动 ComfyUI；
- 尚未 dry run；
- 尚未生成图片。

该状态不等于 `runtime_ready`、`environment_verified`、`executable`、`health_checked` 或 `generated`。

## 未解决事项

- custom node 包级映射仍未建立。
- manifest 仅记录 `custom_nodes_mapping_status=unresolved`。
- `inferred_custom_node_types` 暂为空数组，未伪造包映射。
- `package_mapping_unverified=true`。
- 模型文件存在性仍未验证。
- 视频生成仍未部署，`video_generation_enabled=false` 保持不变。

## 本节点未执行事项

- 未启动 ComfyUI。
- 未访问 localhost。
- 未检查真实端口。
- 未读取模型权重。
- 未读取 `.env`。
- 未读取 `~/.ollama/models`。
- 未执行 workflow dry run。
- 未推理。
- 未生图。
- 未下载模型。
- 未启动 Ollama。
- 未运行测试套件、构建或安装。
- 未部署视频生成模型。
- 未修改 ComfyUI 目录。
- 未复制 ComfyUI blueprint JSON 到仓库。

## 后续边界

R5K-D 建议只做 PR 静态复核，不合并 PR，不进入运行态验证。

R5L 或后续显式授权节点才可继续检查 custom node 包级映射、workflow 文件存在性、目标环境适配性和模型文件存在性。

R6 或更后续节点才可在显式授权下进入受控单图生成。进入 R6 前仍必须保持: 用户显式授权、runtime precheck 已通过、只生成单图、不批量生成、不自动上传、不读取无关文件。
