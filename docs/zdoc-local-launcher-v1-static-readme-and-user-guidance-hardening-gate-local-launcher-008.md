# LOCAL-LAUNCHER-008 ZDoc Local App Static README And User Guidance Hardening Gate

## 1. 节点名称

`LOCAL-LAUNCHER-008-ZDOC-LOCAL-APP-STATIC-README-AND-USER-GUIDANCE-HARDENING-GATE`

## 2. 节点性质

静态 README 与用户引导边界硬化 gate。

本节点仅强化 README、页面静态说明、状态标签、按钮可见文案、no-op 提示和静态提示样式；不新增真实运行能力，不接入真实动作。

## 3. 开始前 HEAD / tag

- HEAD: `1efdd5e99fd5b69f0a9ed0adfaf0913ae6705731`
- tag: `v0.1.631-local-launcher-zdoc-local-app-static-file-integrity-and-documentation-alignment-gate`

## 4. 授权范围

本节点允许读取：

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`
5. `local-launcher-v1/mock-config.json`
6. `docs/zdoc-local-launcher-v1-code-implementation-gate-local-launcher-003.md`
7. `docs/zdoc-local-launcher-v1-static-skeleton-safety-review-gate-local-launcher-004.md`
8. `docs/zdoc-local-launcher-v1-static-ui-readability-optimization-gate-local-launcher-005.md`
9. `docs/zdoc-local-launcher-v1-post-ui-readability-safety-review-gate-local-launcher-006.md`
10. `docs/zdoc-local-launcher-v1-static-file-integrity-and-documentation-alignment-gate-local-launcher-007.md`

本节点允许修改：

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`

本节点仅允许新增：

1. `docs/zdoc-local-launcher-v1-static-readme-and-user-guidance-hardening-gate-local-launcher-008.md`

## 5. 实际读取文件

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`
5. `local-launcher-v1/mock-config.json`
6. `docs/zdoc-local-launcher-v1-code-implementation-gate-local-launcher-003.md`
7. `docs/zdoc-local-launcher-v1-static-skeleton-safety-review-gate-local-launcher-004.md`
8. `docs/zdoc-local-launcher-v1-static-ui-readability-optimization-gate-local-launcher-005.md`
9. `docs/zdoc-local-launcher-v1-post-ui-readability-safety-review-gate-local-launcher-006.md`
10. `docs/zdoc-local-launcher-v1-static-file-integrity-and-documentation-alignment-gate-local-launcher-007.md`

## 6. 实际修改文件

1. `local-launcher-v1/index.html`
2. `local-launcher-v1/styles.css`
3. `local-launcher-v1/app.js`
4. `local-launcher-v1/README.md`

## 7. 实际新增文件

1. `docs/zdoc-local-launcher-v1-static-readme-and-user-guidance-hardening-gate-local-launcher-008.md`

## 8. 授权范围遵守情况

1. 是否仅修改授权范围内文件：是。
2. 是否修改 `index.html`：是。
3. 是否修改 `styles.css`：是。
4. 是否修改 `app.js`：是。
5. 是否修改 `README.md`：是。
6. 是否修改 `mock-config.json`：否。
7. 是否修改 003/004/005/006/007 docs：否。
8. 是否修改 V0/V1/backend/frontend/config/dependency：否。
9. 是否新增 JS/TS/Python/Shell 脚本：否。

## 9. README 边界硬化摘要

1. 强化当前版本仅为静态本地启动器 UI 骨架。
2. 明确当前版本不启动 ZDoc 服务。
3. 明确当前版本不启动、停止或重启 Ollama server。
4. 明确当前版本不访问 endpoint，不执行 HTTP request。
5. 明确当前版本不读取真实 KG、真实项目资料、招标文件、`.env`、secrets、tokens、credentials。
6. 明确当前版本不读取 output/job/export 正文或日志正文。
7. 明确当前版本不触发 generation/export/write-back。
8. 明确当前版本不进入 trial、真实使用或 50 人正式使用。
9. 明确所有按钮、状态标签和提示语均为 mock / disabled / no-op 展示。
10. 明确后续任何真实运行能力必须经过独立 gate、独立授权和独立安全审查。

## 10. index.html 用户引导硬化摘要

1. 将页面标题和首屏节点标识更新为 `LOCAL-LAUNCHER-008` 静态 no-op 骨架说明。
2. 增加 `static skeleton`、`mock / disabled`、`no real action` 状态标签。
3. 强化顶部安全边界，明确不启动、停止、重启、检测服务，不访问 endpoint，不执行 HTTP request，不执行 Ollama，不读取真实资料，不读取日志正文，不触发 generation/export/write-back。
4. 强化 KG、项目资料、输出写入、trial、真实使用和 50 人正式使用的禁止性说明。
5. 将按钮可见文案改为 no-op 表达，降低误认为真实动作入口的风险。
6. 强化说明 panel 中的后续授权和 mock / disabled 表达。

## 11. app.js no-op 文案硬化摘要

1. 扩展内置 mock 状态，增加 runtime、network、secret、trial 使用等 disabled / blocked 标识。
2. 调整按钮 no-op 提示文案，明确点击仅更新页面提示。
3. 保持仅 DOM 文案渲染、内置 mock 状态展示、tab 切换和 no-op 提示。
4. 未新增真实配置读取、网络访问、系统命令调用或真实业务动作。

## 12. styles.css 静态提示样式硬化摘要

1. 增加警示边界列表样式。
2. 增加 no real action 状态标签样式。
3. 为 no-op 控制按钮增加 disabled 提示层级。
4. 保持样式文件仅使用本地 CSS 变量和本地样式，不引入外部 CDN、远程字体、远程图片或网络资源。

## 13. app.js 禁止项检查结果

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

检查结果：无输出，未命中。

## 14. 禁止项命中摘要

未命中任何 `app.js` 禁止项。

## 15. README 禁止内容检查结果

README 未写入真实启动命令、endpoint 地址、Ollama 命令、真实配置路径、真实 KG 路径、真实项目资料路径、真实招标文件路径、真实日志路径、output/job/export 真实路径或诱导用户进入 trial、真实使用、50 人正式使用的说明。

README 中出现的 endpoint、HTTP request、Ollama、KG、trial、output/job/export 等词均为禁止性边界说明，不构成真实命令、真实地址、真实路径或真实使用引导。

## 16. 是否仍为静态 no-op 骨架

是。当前仍仅包含静态 HTML、CSS 和 DOM 层面的 no-op 交互：

1. 页面只展示静态 UI、mock 状态和未授权提示。
2. no-op 按钮仅更新页面内 `actionNotice` 文案。
3. tab 切换仅控制静态 panel 的显示隐藏。
4. mock 状态为 `app.js` 内置对象，不读取真实配置。
5. 未接入任何真实启动、停止、状态检查、日志读取、端口检查、配置读取、endpoint 访问、Ollama、模型推理、prompt 输入、真实资料读取或 generation/export/write-back 逻辑。

## 17. 真实动作与读取风险逐项检查

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

## 18. 本节点未执行事项

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

## 19. 009 可授权范围草案

`LOCAL-LAUNCHER-009-ZDOC-LOCAL-APP-STATIC-NO-OP-INTERACTION-REVIEW-GATE`

建议仅授权：

1. 复核 no-op 交互文案、按钮状态、静态提示与 README 边界是否一致。
2. 复核 `index.html`、`styles.css`、`app.js`、`README.md` 是否仍为静态 no-op 骨架。
3. 复核按钮点击是否仍只对应静态提示文案描述，不授权打开 HTML 页面。
4. 仅新增 009 docs。
5. 不启动服务、不打开 HTML、不访问 endpoint、不执行 Ollama、不读取真实资料。

## 20. 009 禁止范围草案

`LOCAL-LAUNCHER-009` 即使获授权仍禁止：

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
24. 自动进入 `LOCAL-LAUNCHER-010` 或任何后续节点。

## 21. 009 阻断条件

如出现以下任一情况，`LOCAL-LAUNCHER-009` 应立即停止并回报，不得 commit：

1. 开始前 HEAD/tag 与 009 授权基线不一致。
2. 工作区不 clean。
3. 003/004/005/006/007/008 docs 缺失。
4. `local-launcher-v1` 静态文件缺失或出现未授权新增文件。
5. 需要修改授权范围外文件。
6. 发现真实服务启动、停止、状态检查、日志读取、端口检查、配置读取逻辑。
7. 发现 endpoint 访问或 HTTP request。
8. 发现 Ollama 命令、模型推理或 prompt 输入。
9. 发现真实 KG、项目资料、招标文件、secrets、output/job/export 正文或日志正文读取风险。
10. 发现 generation/export/write-back 或 output/job/export 写入逻辑。
11. 需要打开 HTML、启动服务、访问 endpoint、运行 Ollama、读取真实数据或进入 trial 才能继续判断。
12. 任一禁止动作需要被触发或存在触发风险。

## 22. 用户授权文本模板

```text
我明确授权 LOCAL-LAUNCHER-009-ZDOC-LOCAL-APP-STATIC-NO-OP-INTERACTION-REVIEW-GATE。

授权范围仅限：复核 LOCAL-LAUNCHER-008 后的 no-op 交互文案、按钮状态、静态提示与 README 边界是否一致，并新增 009 docs。

禁止启动、停止、重启任何服务，禁止打开 HTML 页面，禁止访问 endpoint/curl/HTTP request，禁止执行任何 Ollama 命令，禁止模型推理，禁止向模型输入 prompt，禁止读取真实 KG/真实项目资料/招标文件/secrets/output/job/export 正文/日志正文，禁止触发 generation/export/write-back，禁止进入 trial、真实使用或 50 人正式使用，禁止运行安装命令，禁止运行测试/lint/build，禁止修改 V0/V1/backend/frontend/config/dependency，禁止自动进入 LOCAL-LAUNCHER-010 或任何后续节点。

如发现基线不符、工作区不 clean、文件缺失、静态文件与文档不一致、真实动作逻辑、真实数据读取风险或任何禁止项触发风险，必须立即停止并回报 BLOCKED。
```

## 23. 明确未授权不得进入 009

本节点仅完成静态 README 与用户引导边界硬化。未获得用户对 `LOCAL-LAUNCHER-009` 的明确授权前，不得进入 009，不得执行 009 可授权范围中的任何动作。

## 24. 结束后 HEAD

008 commit 完成后由 Git 元数据确定，并在完成回报中记录精确值。该值无法在同一 commit 的文件内容中预先自证。

## 25. commit hash

008 commit 完成后由 Git 元数据确定，并在完成回报中记录精确值。该值无法在同一 commit 的文件内容中预先自证。

## 26. tag

`v0.1.632-local-launcher-zdoc-local-app-static-readme-and-user-guidance-hardening-gate`

## 27. `git status --short` 是否 clean

完成提交和 tag 后检查。

## 28. decision

`LOCAL-LAUNCHER-008 ZDOC LOCAL APP STATIC README AND USER GUIDANCE HARDENING GATE COMPLETED / README BOUNDARY HARDENED / STATIC USER GUIDANCE HARDENED / APP JS NO-OP COPY HARDENED / STATIC WARNING STYLES HARDENED / APP JS FORBIDDEN TERMS EXPECTED NOT FOUND / README FORBIDDEN REAL COMMAND ADDRESS PATH GUIDANCE EXPECTED NOT FOUND / STATIC NO-OP SKELETON CONFIRMED / NO REAL START STOP STATUS LOG PORT CONFIG ACTION ADDED / NO ENDPOINT OR HTTP REQUEST ADDED / NO OLLAMA COMMAND ADDED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ LOGIC ADDED / NO ZDOC GENERATION EXPORT WRITE-BACK LOGIC ADDED / NO SERVICE STARTED / NO HTML OPENED / NO TEST LINT BUILD RUN / NO INSTALL COMMAND RUN / NO TRIAL EXECUTED / STOPPED BEFORE LOCAL-LAUNCHER-009`
