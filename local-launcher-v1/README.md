# ZDoc 本地启动器静态 no-op 骨架

本目录当前版本仅为本地启动器静态 UI 骨架。`LOCAL-LAUNCHER-008` 只强化 README 与页面用户引导的安全边界说明，不接入任何真实运行能力。

当前静态边界：

1. 当前版本不启动 ZDoc 服务。
2. 当前版本不启动、停止或重启 Ollama server。
3. 当前版本不访问 endpoint。
4. 当前版本不执行 HTTP request。
5. 当前版本不读取真实 KG。
6. 当前版本不读取真实项目资料或招标文件。
7. 当前版本不读取 `.env`、secrets、tokens、credentials。
8. 当前版本不读取 output/job/export 正文或日志正文。
9. 当前版本不触发 generation/export/write-back。
10. 当前版本不进入 trial、真实使用或 50 人正式使用。
11. 当前版本不创建真正 App 安装包。
12. 所有按钮、状态标签和提示语均为 mock / disabled / no-op 展示。

页面按钮仅更新静态提示，不执行启动、停止、重启、状态检查、日志读取、端口检查、配置读取、endpoint 访问、HTTP request、Ollama 调用、真实资料读取、generation、export 或 write-back。

后续任何真实运行能力必须经过独立 gate、独立授权和独立安全审查；未获明确授权前，本静态骨架不得被解释为 trial、真实使用或 50 人正式使用入口。
