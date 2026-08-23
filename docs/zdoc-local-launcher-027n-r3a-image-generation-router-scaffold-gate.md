# LOCAL-LAUNCHER-027N-R3A-IMAGE-GENERATION-ROUTER-SCAFFOLD-GATE

## 当前基线 commit

50777774409d9015584222ef5d1f84b60abdda60

## 当前节点性质

027N 生图 Router 静态架构落地节点。该节点只建立本地生图模型路由、施工组织设计 prompt 模板、ComfyUI workflow 契约和静态校验入口，不启动 ComfyUI，不生成图片，不运行推理，不访问 localhost。

## 已完成前置成果

- ComfyUI 已部署。
- Qwen-Image 已下载。
- Qwen-Image-Edit 已下载。
- FLUX.1-dev 已授权并已下载。
- 视频生成暂不部署。

## 本节点新增文件清单

- `image_generation/__init__.py`
- `image_generation/router/__init__.py`
- `image_generation/router/models.py`
- `image_generation/router/router.py`
- `image_generation/router/prompt_builder.py`
- `image_generation/router/workflow_contracts.py`
- `image_generation/router/policies.py`
- `image_generation/router/validators.py`
- `image_generation/prompts/__init__.py`
- `image_generation/prompts/construction_templates.py`
- `configs/local-image-generation-routing.json`
- `configs/image-generation-prompt-templates.json`
- `docs/zdoc-local-launcher-027n-r3a-image-generation-router-scaffold-gate.md`

## 模型职责分工

| role | repo_id | 状态 | 主要职责 |
| --- | --- | --- | --- |
| `qwen_image_primary` | `Qwen/Qwen-Image` | `downloaded_not_runtime_verified` | 中文技术标插图、工序图、临设布置、中文标识场景 |
| `qwen_image_edit` | `Qwen/Qwen-Image-Edit` | `downloaded_not_runtime_verified` | 现场照片编辑、中文标识修正、既有场景修正 |
| `flux_realistic` | `black-forest-labs/FLUX.1-dev` | `downloaded_not_runtime_verified` | 写实施工现场、鸟瞰效果、封面图、机械作业场景 |
| `qwen_image_edit_latest_candidate` | `Qwen/Qwen-Image-Edit-2509` | `planned_download_not_active` | 后续候选，不作为本节点 active 路由目标 |
| `disabled_video` | 空 | `disabled_not_deployed` | 视频生成禁用 |

## 任务类型路由表

| task_type | primary | fallback | workflow |
| --- | --- | --- | --- |
| `technical_bid_illustration` | `qwen_image_primary` | `flux_realistic` | `qwen_image_text_to_image` |
| `realistic_construction_scene` | `flux_realistic` | `qwen_image_primary` | `flux_realistic_text_to_image` |
| `site_photo_edit` | `qwen_image_edit` | `qwen_image_primary` | `qwen_image_edit_image_to_image` |
| `safety_civilization_scene` | `qwen_image_primary` | `flux_realistic` | `qwen_image_text_to_image` |
| `temporary_facility_layout` | `qwen_image_primary` | `flux_realistic` | `qwen_image_text_to_image` |
| `machinery_operation_scene` | `flux_realistic` | `qwen_image_primary` | `flux_realistic_text_to_image` |
| `material_yard_scene` | `flux_realistic` | `qwen_image_primary` | `flux_realistic_text_to_image` |
| `construction_process_diagram` | `qwen_image_primary` | `qwen_image_edit` | `qwen_image_text_to_image` |
| `birdseye_render` | `flux_realistic` | `qwen_image_primary` | `flux_realistic_text_to_image` |
| `cover_image` | `flux_realistic` | `qwen_image_primary` | `flux_realistic_text_to_image` |
| `chinese_signage_scene` | `qwen_image_primary` | `qwen_image_edit` | `qwen_image_text_to_image` |

## prompt 模板体系说明

`configs/image-generation-prompt-templates.json` 提供 13 个施工组织设计场景模板，覆盖基坑、钢筋、模板、混凝土、吊装、临设、安全文明、材料堆场、道路管线、校园改造、市政排水、鸟瞰和技术标封面。每个模板同时提供中文技术标 prompt、FLUX 英文写实 prompt、negative prompt、风格标签、质量约束和施工约束。

## ComfyUI workflow contract 说明

`image_generation/router/workflow_contracts.py` 只定义契约，不创建 workflow，不运行 workflow。当前契约包括：

- `qwen_image_text_to_image`
- `qwen_image_edit_image_to_image`
- `flux_realistic_text_to_image`

所有 contract 均标记 `runtime_required=true` 和 `local_only=true`，运行态验证留给后续节点。

## 运行态禁触说明

本节点禁止启动 ComfyUI、禁止执行 ComfyUI `main.py`、禁止生成图片、禁止运行生图推理、禁止访问 localhost / 127.0.0.1、禁止启动 Ollama、禁止下载模型、禁止读取模型权重内容、禁止读取 `~/.ollama/models`、禁止读取 `.env` 或密钥文件、禁止运行项目测试/构建/安装。

## 静态校验结果

本节点提交前静态校验项包括：

- JSON 结构校验：`configs/local-image-generation-routing.json`
- JSON 结构校验：`configs/image-generation-prompt-templates.json`
- Python 编译校验：`python3 -m compileall image_generation`
- 纯 Python 内存校验：router、prompt builder、validators、policies、workflow contracts
- 空白与冲突标记校验：`git diff --check`

校验范围仅覆盖静态配置与 Python 内存逻辑，不证明任何模型运行态可用。

## 后续建议节点

LOCAL-LAUNCHER-027N-R3B-IMAGE-GENERATION-ROUTER-PR-REVIEW-GATE
