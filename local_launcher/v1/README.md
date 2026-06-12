# ZDoc 本地启动器 V1 受控启动 UI 骨架

本目录包含 ZDoc 本地启动器的 V1 静态受控启动 UI 骨架。

V1 当前只是受控启动 UI 骨架，属于 V1 UI skeleton only。它不是可启动系统，不是 runtime preflight，不是 controlled start execution gate。

## 安全边界

- V1 不启动 ZDoc 服务。
- V1 不停止 ZDoc 服务。
- V1 不访问 endpoint 或任何接口。
- V1 不运行 Ollama 或任何模型命令。
- V1 不运行测试。
- V1 不进入 trial、仅预览试用、真实使用或生产使用。
- V1 不触发 generation、export 或 write-back。
- V1 不读取真实知识图谱。
- V1 不读取真实项目资料。
- V1 不读取 registration、metadata、proof、manifest 或 sample 实例。
- V1 不读取 output、job 或 export 内容。
- V1 不包含可执行启动脚本。
- V1 不包含可执行停止脚本。
- V1 不创建真正 App 包。
- V1 不创建 runtime bridge。

## 文件

- `index.html`：静态中文 UI 骨架，展示启动前检查、服务状态、端口、日志、停止服务和禁止能力占位。
- `styles.css`：仅包含静态样式。
- `launcher-state.json`：静态占位状态，所有运行、访问、端口、日志、配置、生成、导出、写回权限均保持禁用。

## 控件

所有真实动作按钮默认禁用。这些按钮只展示后续可能由 runtime preflight 或 controlled start execution gate 单独授权的能力分类。

V1 当前不能启动后端、启动前端、停止后端、停止前端、检查端口、查看日志、健康检查、打开仅预览、运行 Ollama、生成文档、导出文档、写回 ZBid、读取知识图谱，或加载项目资料。

## 后续边界

后续如需真正启动服务，必须进入单独的 runtime preflight / controlled start execution gate。

服务启动、服务停止、端口检查、日志读取、配置读取、endpoint 健康检查、Ollama、trial、generation、export 和 write-back 都必须另行授权。

完成本节点后必须等待 ChatGPT 总控师审核。流程必须停止，不得自动进入下一节点。
