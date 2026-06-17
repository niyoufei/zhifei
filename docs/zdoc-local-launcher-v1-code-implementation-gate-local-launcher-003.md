# LOCAL-LAUNCHER-003 ZDoc Local App Code Implementation Gate

## 1. 节点名称

`LOCAL-LAUNCHER-003-ZDOC-LOCAL-APP-CODE-IMPLEMENTATION-GATE`

## 2. 开始前 HEAD / tag

- HEAD: `c81c31220ac3e7e90fbdca10a39ec53c78bb175d`
- tag: `v0.1.626-local-launcher-zdoc-local-app-code-implementation-authorization-gate`

## 3. 用户授权摘要

用户授权在既有安全边界内执行 `LOCAL-LAUNCHER-003`，新增最小本地 App / 启动器代码骨架。授权范围仅限静态 UI、本地启动控制壳层的界面占位、mock 状态展示、禁止真实动作的安全提示和后续接入 gate 说明。

## 4. 实际新增文件清单

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/mock-config.json`
5. `local-launcher-v1/README.md`
6. `docs/zdoc-local-launcher-v1-code-implementation-gate-local-launcher-003.md`

## 5. 实现范围

1. 新增静态 HTML 页面。
2. 新增静态 CSS 样式。
3. 新增仅限 DOM 层面的 no-op 交互。
4. 新增非敏感 mock 配置展示。
5. 新增 README 边界说明。
6. 新增本节点记录文档。

## 6. 未实现范围

1. 未实现真实启动。
2. 未实现真实停止。
3. 未实现真实状态检查。
4. 未实现真实日志读取。
5. 未实现真实端口检查。
6. 未实现真实配置读取或校验。
7. 未实现 endpoint 访问。
8. 未实现模型调用。
9. 未实现真实 KG、项目资料或招标文件读取。
10. 未实现 generation/export/write-back。

## 7. 静态 UI 模块说明

`index.html` 包含：

1. 本地启动器标题。
2. 安全边界提示。
3. ZDoc 服务状态卡片，显示 mock 状态，不做真实检测。
4. Ollama server 状态卡片，显示 mock 状态，不做真实检测。
5. KG 读取状态卡片，固定显示“未接入真实 KG”。
6. 项目资料读取状态卡片，固定显示“未读取真实项目资料”。
7. generation/export/write-back 状态卡片，固定显示“未授权、未触发”。
8. 启动、停止、状态检查、查看日志、端口检查、配置检查按钮。
9. 所有按钮均为 no-op，仅显示页面内未授权提示。
10. 页面明确提示当前仅为静态骨架，真实动作需后续节点授权。

## 8. mock-config 说明

`mock-config.json` 仅包含非敏感 mock 字段：

1. `appMode: "static-skeleton"`
2. `zdocService: "not-started-by-this-app"`
3. `kgAccess: "disabled"`
4. `projectDataAccess: "disabled"`
5. `generation: "disabled"`
6. `export: "disabled"`
7. `writeBack: "disabled"`

不包含真实路径、真实端口、真实 endpoint、真实 token、真实项目名、真实 KG 名称、真实模型名或真实用户数据。

## 9. JS 安全边界

`app.js` 仅执行以下 DOM 层面的静态交互：

1. 渲染 mock 配置内容。
2. 点击 no-op 按钮后显示“未授权，不执行真实动作”的页面内提示。
3. 切换静态说明区。

`app.js` 不包含 `fetch`、`XMLHttpRequest`、`WebSocket`、`EventSource`、`navigator.sendBeacon`、`child_process`、`exec`、`spawn`、`curl`、HTTP URL、本地回环地址、endpoint 路径或命令执行逻辑。

## 10. 本节点明确未执行事项

1. 未启动、停止、重启 ZDoc 服务。
2. 未启动、停止、重启 Ollama server。
3. 未执行任何 Ollama 命令。
4. 未访问 endpoint。
5. 未执行 curl / HTTP request。
6. 未执行模型推理。
7. 未向模型输入 prompt。
8. 未读取真实 KG。
9. 未读取真实项目资料。
10. 未读取真实招标文件。
11. 未读取 `.env` / secrets / tokens / credentials。
12. 未读取 registration / metadata / proof / manifest / sample 实例。
13. 未读取 output/job/export 正文。
14. 未读取日志正文。
15. 未读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
16. 未触发 generation/export/write-back。
17. 未写 output/job/export。
18. 未进入 trial、真实使用或 50 人正式使用。
19. 未进入 `LOCAL-LAUNCHER-004`。

## 11. 后续 004 可授权范围草案

`LOCAL-LAUNCHER-004` 可授权范围草案：

1. 仅对静态 UI 骨架进行人工可读性审查。
2. 仅检查新增文件内容是否存在真实动作代码。
3. 仅检查 JS 是否包含 `fetch`、`XMLHttpRequest`、`WebSocket`、`EventSource`、`child_process`、`exec`、`spawn` 等禁止项。
4. 仅检查页面是否仍为静态 no-op。
5. 不启动服务。
6. 不打开 HTML 页面。
7. 不访问 endpoint。
8. 不执行 Ollama。
9. 不读取真实 KG/项目资料。
10. 不触发 generation/export/write-back。

## 12. 后续 004 禁止范围草案

`LOCAL-LAUNCHER-004` 即使获授权仍禁止：

1. 启动、停止、重启服务。
2. 打开 HTML 页面。
3. 访问 endpoint。
4. curl / HTTP request。
5. Ollama 命令。
6. 模型推理。
7. prompt 输入。
8. 真实 KG、项目资料、招标文件、secrets、output/job/export 正文、日志正文读取。
9. generation/export/write-back。
10. trial、真实使用、50 人正式使用。
11. 修改 V0/V1/backend/frontend/config/dependency。
12. 自动进入 `005`。

## 13. 后续 004 阻断条件

如出现以下任一情况，`LOCAL-LAUNCHER-004` 应立即阻断：

1. 当前 HEAD 或 tag 与授权基线不一致。
2. 工作区不 clean。
3. `LOCAL-LAUNCHER-003` 新增文件缺失或被额外修改。
4. JS 出现任何真实动作、命令执行、endpoint 访问或网络请求逻辑。
5. mock 配置出现真实路径、真实端口、真实 endpoint、真实 token、真实项目名、真实 KG 名称、真实模型名或真实用户数据。
6. 需要打开 HTML 页面、启动服务、访问 endpoint、运行 Ollama、读取真实数据或进入 trial 才能继续判断。

## 14. 用户授权文本模板

```text
我授权执行 LOCAL-LAUNCHER-004-ZDOC-LOCAL-APP-STATIC-SKELETON-REVIEW-GATE。
仅允许审查 LOCAL-LAUNCHER-003 新增的静态 UI、mock-config、README 和 003 docs。
不得启动服务、不得打开 HTML、不得访问 endpoint、不得执行 curl / HTTP request、不得执行 Ollama 命令、不得运行模型、不得输入 prompt、不得读取真实 KG/项目资料/招标文件/secrets/output/job/export/log 正文、不得触发 generation/export/write-back、不得进入 trial 或真实使用。
如发现基线不符、工作区不 clean、文件缺失、JS 出现真实动作或 mock 配置出现真实信息，必须立即停止并回报 BLOCKED。
```

## 15. 当前 decision

`LOCAL-LAUNCHER-003 ZDOC LOCAL APP CODE IMPLEMENTATION GATE COMPLETED / MINIMAL STATIC LOCAL LAUNCHER SKELETON IMPLEMENTED / STATIC UI AND MOCK CONFIG ONLY / NO REAL START STOP STATUS LOG PORT CONFIG ACTION IMPLEMENTED / NO SERVICE STARTED / NO ENDPOINT ACCESSED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED / STOPPED BEFORE LOCAL-LAUNCHER-004`
