# ZDoc 本地 AI 文档系统控制台 V1 专业静态控制台

本目录包含 ZDoc 本地 AI 文档系统控制台的 V1 专业静态控制台页面。

`local_launcher/v1/` 是当前 LOCAL-LAUNCHER canonical 静态资产候选边界。

`CANONICAL_STATIC_ASSET_BOUNDARY.md` 是本目录的静态资产边界说明。

V1 当前是 professional static console only。它不是可启动系统，不是 runtime preflight，不是 controlled start execution gate，也不是 trial 入口。历史说明仅作为静态边界说明，不作为运行依据。

## 安全边界

- 本版本不启动 ZDoc 服务。
- 本版本不停止 ZDoc 服务。
- 本版本不访问 endpoint 或任何接口。
- 本版本不授权 localhost 或 127.0.0.1 访问。
- 本版本不进行端口探测、HTTP 请求或健康检查。
- 本版本不执行 `.app` 启动器。
- 本版本不运行 Ollama 或任何模型能力。
- 本版本不授权模型推理。
- 本版本不运行测试。
- 本版本不进入 trial、仅预览试用、真实使用或生产使用。
- 本版本不触发 generation、export 或 write-back。
- 本版本不读取真实知识图谱。
- 本版本不读取真实项目资料。
- 本版本不读取 registration、metadata、proof、manifest 或 sample 实例。
- 本版本不读取 output、job 或 export 内容。
- 本版本不包含可执行启动入口。
- 本版本不包含可执行停止入口。
- 本版本不创建真正 App 包。
- 本版本不创建 runtime bridge。

## 文件

- `index.html`：静态中文专业控制台页面，展示顶部品牌区、授权状态区、导航、总览、启动前检查、服务状态、日志端口配置占位、禁止能力、后续授权和底部审计状态。
- `styles.css`：仅包含本地静态样式，不引用外部资源。
- `launcher-state.json`：静态占位状态，所有运行、访问、端口、日志、配置、生成、导出、写回权限均保持禁用。
- `CANONICAL_STATIC_ASSET_BOUNDARY.md`：静态资产边界说明，不授权 runtime、endpoint、localhost、Ollama、模型推理或服务启动。

## 控件

所有真实动作按钮默认禁用。这些按钮只展示后续可能由 runtime preflight 或 controlled start execution gate 单独授权的能力分类。

V1 当前不能启动后端、启动前端、停止后端、停止前端、检查端口、查看日志、健康检查、打开仅预览、运行 Ollama、生成文档、导出文档、写回 ZBid、读取知识图谱，或加载项目资料。

## 后续边界

runtime preflight 必须另设节点。后续如需真正启动服务、停止服务、读取日志、检查端口、读取配置或进行 endpoint 健康检查，必须进入单独授权节点。

Ollama、trial、generation、export 和 write-back 都不在本版本授权范围内。

任何后续变更必须通过独立门控节点授权，并声明精确写入范围、验收标准、回滚要求和 no-runtime 边界。

完成后必须等待 ChatGPT 总控师审核。流程必须停止，不得自动进入下一节点。
