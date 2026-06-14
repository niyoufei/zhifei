# ZDoc 本地 AI 文档系统控制台静态骨架

本目录当前版本是 `LOCAL-LAUNCHER-017-R1` 的专业化静态 UI 骨架。它只用于展示本地启动器未来可能采用的控制台信息架构、mock 状态、disabled 控件和 no-op 提示，不代表任何真实运行能力。

## 当前文件

1. `index.html`：静态控制台页面结构。
2. `styles.css`：本地样式与响应式布局，无外部资源。
3. `app.js`：纯前端 no-op 提示与面板切换。
4. `mock-config.json`：静态 mock / disabled 状态快照。
5. `README.md`：静态骨架边界说明。

## 静态边界

当前版本必须保持：

1. 纯静态。
2. 纯前端。
3. mock。
4. disabled。
5. no-op。
6. 无服务。
7. 无 endpoint。
8. 无 HTTP request。
9. 无 Ollama。
10. 无模型推理。
11. 无 prompt 输入。
12. 无真实 KG 读取。
13. 无真实项目资料或招标文件读取。
14. 无 `.env`、secrets、tokens、credentials 读取。
15. 无 output/job/export 正文读取。
16. 无日志正文读取。
17. 无 generation/export/write-back。
18. 无 trial。
19. 无真实使用。
20. 无 50 人正式使用。

## 交互说明

页面按钮仅更新页面内提示，不执行启动、停止、重启、状态检查、日志读取、端口检查、配置读取、endpoint 访问、HTTP request、Ollama 调用、真实资料读取、generation、export 或 write-back。

侧边导航只切换页面内静态说明面板，不读取本地文件、不访问网络、不触发真实动作。

## Handoff 边界

本静态骨架不得被解释为 runtime preflight、controlled start、endpoint health check、service management、trial、真实使用或 50 人正式使用授权。

如后续 `LOCAL-LAUNCHER-018` 获总控师另行授权，它只能复核 017-R1 的静态 UI 文件修改是否合规、是否仍保持 no-op / mock / disabled 边界、是否无真实运行链路。未获明确授权前，不得进入 `LOCAL-LAUNCHER-018`。
