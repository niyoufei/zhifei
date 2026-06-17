# LOCAL-LAUNCHER-006 ZDoc Local App Post UI Readability Safety Review Gate

## 1. 节点名称

`LOCAL-LAUNCHER-006-ZDOC-LOCAL-APP-POST-UI-READABILITY-SAFETY-REVIEW-GATE`

## 2. 节点性质

本节点为 `LOCAL-LAUNCHER-005` 静态 UI 可读性优化后的安全复核 gate。

本节点仅复核 005 后的 `local-launcher-v1` 静态页面是否仍为 no-op 骨架，不继续优化 UI，不新增功能，不接入真实动作。

## 3. 开始前 HEAD / tag

- HEAD: `3a87246166fa58a2da38d66982bcac601140c3b3`
- tag: `v0.1.629-local-launcher-zdoc-local-app-static-ui-readability-optimization-gate`

## 4. 授权范围

本节点仅允许读取下列文件并新增本 006 docs：

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`
5. `local-launcher-v1/mock-config.json`
6. `docs/zdoc-local-launcher-v1-code-implementation-gate-local-launcher-003.md`
7. `docs/zdoc-local-launcher-v1-static-skeleton-safety-review-gate-local-launcher-004.md`
8. `docs/zdoc-local-launcher-v1-static-ui-readability-optimization-gate-local-launcher-005.md`

本节点禁止修改任何既有文件，禁止新增除本 006 docs 外的任何文件。

## 5. 实际读取文件

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`
5. `local-launcher-v1/mock-config.json`
6. `docs/zdoc-local-launcher-v1-code-implementation-gate-local-launcher-003.md`
7. `docs/zdoc-local-launcher-v1-static-skeleton-safety-review-gate-local-launcher-004.md`
8. `docs/zdoc-local-launcher-v1-static-ui-readability-optimization-gate-local-launcher-005.md`

## 6. 实际修改文件

无既有文件被修改。

## 7. 实际新增文件

1. `docs/zdoc-local-launcher-v1-post-ui-readability-safety-review-gate-local-launcher-006.md`

## 8. 是否仅新增 006 docs

是。除新增本 006 docs 外，未修改任何既有文件，未新增其他文件。

## 9. 既有文件修改确认

1. 是否修改 `index.html`：否。
2. 是否修改 `styles.css`：否。
3. 是否修改 `app.js`：否。
4. 是否修改 `README.md`：否。
5. 是否修改 `mock-config.json`：否。
6. 是否修改 003/004/005 docs：否。
7. 是否修改 V0/V1/backend/frontend/config/dependency：否。
8. 是否新增 JS/TS/Python/Shell 脚本：否。

## 10. 文件范围检查结果

`local-launcher-v1` 当前 tracked 文件仍仅限：

1. `local-launcher-v1/README.md`
2. `local-launcher-v1/app.js`
3. `local-launcher-v1/index.html`
4. `local-launcher-v1/mock-config.json`
5. `local-launcher-v1/styles.css`

本节点只新增 006 docs，不修改上述静态文件。

## 11. `index.html` 安全复核摘要

`index.html` 仅包含静态页面结构、静态安全边界提示、mock 状态卡片、no-op 按钮、静态说明 panel 和本地 `app.js` 引用。

页面文案明确：

1. 当前页面只做静态展示。
2. 不启动、停止或检测服务。
3. 不读取日志、端口、配置、KG、项目资料或招标文件。
4. 不访问 endpoint。
5. 不执行 Ollama。
6. 不触发 generation/export/write-back。

结论：未发现真实服务启动、停止、状态检查、日志读取、端口检查、配置读取、endpoint 访问、模型 prompt 输入、真实生成、导出或写回入口。

## 12. `styles.css` 安全复核摘要

`styles.css` 仅包含颜色变量、布局、卡片、按钮、tab、panel、pre 和移动端响应式样式。

结论：样式文件不包含真实动作逻辑，不包含网络访问、命令执行、配置读取、日志读取或数据读取逻辑。

## 13. `app.js` 安全复核摘要

`app.js` 仅包含：

1. 内置 mock 配置对象。
2. `mockConfig` 文本渲染。
3. no-op 按钮点击后更新页面内提示文案。
4. tab/panel 静态切换。

结论：`app.js` 仅包含 DOM 文案渲染、tab 切换和静态 no-op 提示。按钮或交互不会触发真实服务动作。

## 14. `README.md` 安全复核摘要

`README.md` 明确声明本目录仅为本地启动器静态 UI 骨架，`LOCAL-LAUNCHER-005` 仅优化页面可读性、静态文案、样式层级和 no-op 提示，不接入任何真实动作。

README 未提供真实启动命令、endpoint 访问方式、Ollama 命令、真实配置路径、真实 KG 路径、真实项目资料路径或真实招标文件路径。

## 15. `mock-config.json` 只读复核摘要

`mock-config.json` 仅包含非敏感 mock / disabled 字段：

1. `appMode`
2. `zdocService`
3. `kgAccess`
4. `projectDataAccess`
5. `generation`
6. `export`
7. `writeBack`

结论：未发现真实路径、真实端口、真实 endpoint、真实 token、真实项目名、真实 KG 名称、真实模型名或真实用户数据。

## 16. `app.js` 禁止项检查结果

检查项：

```text
fetch
XMLHttpRequest
WebSocket
EventSource
navigator.sendBeacon
child_process
exec
spawn
curl
http://
https://
127.0.0.1
localhost
ollama
/health
/generate
/export
/review/apply
```

检查结果：无命中。

## 17. 禁止项命中摘要

未命中任何 `app.js` 禁止项。

## 18. 静态 no-op 骨架确认

是否仍为静态 no-op 骨架：是。

确认依据：

1. 页面只展示静态 UI、mock 状态和未授权提示。
2. no-op 按钮仅更新页面内 `actionNotice` 文案。
3. tab 切换仅控制静态 panel 的显示隐藏。
4. mock 配置为 `app.js` 内置对象和 `mock-config.json` 中的非敏感 disabled 字段。
5. 未发现真实启动、停止、状态检查、日志读取、端口检查、配置读取、endpoint 访问、Ollama、模型推理、prompt 输入、真实资料读取或 generation/export/write-back 逻辑。

## 19. 真实动作与读取风险逐项复核

1. 是否发现真实服务启动逻辑：否。
2. 是否发现真实服务停止逻辑：否。
3. 是否发现真实状态检查逻辑：否。
4. 是否发现真实日志读取逻辑：否。
5. 是否发现真实端口检查逻辑：否。
6. 是否发现真实配置读取逻辑：否。
7. 是否发现 endpoint 访问：否。
8. 是否发现 curl / HTTP request：否。
9. 是否发现 Ollama 命令：否。
10. 是否发现模型推理：否。
11. 是否发现 prompt 输入：否。
12. 是否发现真实 KG 读取：否。
13. 是否发现真实项目资料读取：否。
14. 是否发现招标文件读取：否。
15. 是否发现 secrets / token / credential 读取：否。
16. 是否发现 output/job/export 正文读取：否。
17. 是否发现日志正文读取：否。
18. 是否发现 generation/export/write-back：否。
19. 是否发现 output/job/export 写入：否。

## 20. 本节点未执行事项

1. 是否运行 npm/yarn/pnpm/pip 安装命令：否。
2. 是否运行测试/lint/build：否。
3. 是否打开 HTML 页面：否。
4. 是否启动、重启、停止 ZDoc 服务：否。
5. 是否启动、重启、停止 Ollama server：否。
6. 是否执行任何 Ollama 命令：否。
7. 是否访问 endpoint：否。
8. 是否执行 curl / HTTP request：否。
9. 是否执行模型推理：否。
10. 是否向模型输入 prompt：否。
11. 是否读取真实 KG：否。
12. 是否读取真实项目资料：否。
13. 是否读取真实招标文件：否。
14. 是否读取 `.env` / secrets / tokens / credentials：否。
15. 是否读取 registration / metadata / proof / manifest / sample 实例：否。
16. 是否读取 output/job/export 正文：否。
17. 是否读取日志正文：否。
18. 是否读取 `/tmp` 临时 stdout/stderr 捕获文件正文：否。
19. 是否触发 generation/export/write-back：否。
20. 是否写 output/job/export：否。
21. 是否进入 trial：否。
22. 是否进入真实使用或 50 人正式使用：否。

## 21. 007 可授权范围草案

`LOCAL-LAUNCHER-007-ZDOC-LOCAL-APP-STATIC-FILE-INTEGRITY-AND-DOCUMENTATION-ALIGNMENT-GATE`

建议仅授权：

1. 复核 `local-launcher-v1` 静态文件完整性。
2. 复核 003/004/005/006 docs 与静态文件现状是否一致。
3. 复核 README 与页面文案是否仍声明静态 no-op 边界。
4. 新增 007 docs。
5. 不启动服务、不打开 HTML、不访问 endpoint、不执行 Ollama、不读取真实资料。

## 22. 007 禁止范围草案

`LOCAL-LAUNCHER-007` 即使获授权仍禁止：

1. 启动、停止、重启 ZDoc 服务。
2. 启动、停止、重启 Ollama server。
3. 打开 HTML 页面。
4. 访问任何 endpoint。
5. 执行 curl / HTTP request。
6. 执行任何 Ollama 命令。
7. 执行模型推理。
8. 向模型输入 prompt。
9. 读取真实 KG。
10. 读取真实项目资料。
11. 读取真实招标文件。
12. 读取 `.env` / secrets / tokens / credentials。
13. 读取 registration / metadata / proof / manifest / sample 实例。
14. 读取 output/job/export 正文。
15. 读取日志正文。
16. 读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
17. 触发 generation/export/write-back。
18. 写 output/job/export。
19. 进入 trial。
20. 进入真实使用或 50 人正式使用。
21. 运行 npm/yarn/pnpm/pip 安装命令。
22. 运行测试/lint/build。
23. 修改 V0/V1/backend/frontend/config/dependency。
24. 自动进入 `LOCAL-LAUNCHER-008`。

## 23. 007 阻断条件

如出现以下任一情况，`LOCAL-LAUNCHER-007` 应立即停止并回报，不得 commit：

1. 开始前 HEAD/tag 与 007 授权基线不一致。
2. 工作区不 clean。
3. 003/004/005/006 docs 缺失。
4. `local-launcher-v1` 静态文件缺失或出现未授权新增文件。
5. 发现真实服务启动、停止、状态检查、日志读取、端口检查、配置读取逻辑。
6. 发现 endpoint 访问或 HTTP request。
7. 发现 Ollama 命令、模型推理或 prompt 输入。
8. 发现真实 KG、项目资料、招标文件、secrets、output/job/export 正文或日志正文读取风险。
9. 发现 generation/export/write-back 或 output/job/export 写入逻辑。
10. 需要打开 HTML、启动服务、访问 endpoint、运行 Ollama、读取真实数据或进入 trial 才能继续判断。
11. 任一禁止动作需要被触发或存在触发风险。

## 24. 用户授权文本模板

```text
我明确授权 LOCAL-LAUNCHER-007-ZDOC-LOCAL-APP-STATIC-FILE-INTEGRITY-AND-DOCUMENTATION-ALIGNMENT-GATE。

授权范围仅限：复核 local-launcher-v1 静态文件完整性，复核 003/004/005/006 docs 与静态文件现状是否一致，复核 README 与页面文案是否仍声明静态 no-op 边界，并新增 007 docs。

禁止启动、停止、重启任何服务，禁止打开 HTML 页面，禁止访问 endpoint/curl/HTTP request，禁止执行任何 Ollama 命令，禁止模型推理，禁止向模型输入 prompt，禁止读取真实 KG/真实项目资料/招标文件/secrets/output/job/export 正文/日志正文，禁止触发 generation/export/write-back，禁止进入 trial、真实使用或 50 人正式使用，禁止运行安装命令，禁止运行测试/lint/build，禁止自动进入 LOCAL-LAUNCHER-008。

如发现基线不符、工作区不 clean、文件缺失、静态文件与文档不一致、真实动作逻辑、真实数据读取风险或任何禁止项触发风险，必须立即停止并回报 BLOCKED。
```

## 25. 未授权不得进入 007

本节点仅完成 005 后静态 UI 可读性优化安全复核。未获得用户对 `LOCAL-LAUNCHER-007` 的明确授权前，不得进入 007，不得执行 007 可授权范围中的任何复核动作。

## 26. 结束后 HEAD

006 commit 完成后由 Git 元数据确定，并在完成回报中记录精确值。该值无法在同一 commit 的文件内容中预先自证。

## 27. commit hash

006 commit 完成后由 Git 元数据确定，并在完成回报中记录精确值。该值无法在同一 commit 的文件内容中预先自证。

## 28. tag

`v0.1.630-local-launcher-zdoc-local-app-post-ui-readability-safety-review-gate`

## 29. `git status --short` 是否 clean

完成提交和 tag 后检查。

## 30. decision

`LOCAL-LAUNCHER-006 ZDOC LOCAL APP POST UI READABILITY SAFETY REVIEW GATE COMPLETED / POST UI READABILITY SAFETY REVIEW COMPLETED / 005 STATIC FILES REVIEWED / APP JS FORBIDDEN TERMS NOT FOUND / STATIC NO-OP SKELETON CONFIRMED / NO REAL START STOP STATUS LOG PORT CONFIG ACTION FOUND / NO ENDPOINT OR HTTP REQUEST FOUND / NO OLLAMA COMMAND FOUND / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ LOGIC FOUND / NO ZDOC GENERATION EXPORT WRITE-BACK LOGIC FOUND / NO SERVICE STARTED / NO HTML OPENED / NO TRIAL EXECUTED / STOPPED BEFORE LOCAL-LAUNCHER-007`
