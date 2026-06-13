# LOCAL-LAUNCHER-058 ZDoc Local App V1 Ollama Server Diagnostics Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-058-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-DIAGNOSTICS-AUTHORIZATION-GATE`

本节点性质：

`Ollama server diagnostics authorization boundary and user authorization request only`

本节点目标：

记录未来是否可以执行 Ollama server diagnostics 的授权边界、禁止事项、阻断条件、用户授权文本模板和后续进入条件。

本节点明确：

1. 不执行任何诊断命令。
2. 不执行任何 Ollama 命令。
3. 不执行 `ollama serve`。
4. 不执行 `ollama list`。
5. 不执行 `ollama run`。
6. 不启动、重启或停止 Ollama server。
7. 不启动、重启或停止任何服务。
8. 不运行模型。
9. 不向模型输入 prompt。
10. 不访问 endpoint。
11. 不触发 ZDoc generation/export/write-back。
12. 不读取真实 KG、真实项目资料或真实招标文件。
13. 不进入 `LOCAL-LAUNCHER-059`。

当前基线：

- 开始前 HEAD：`42e23173b56d5454426d20f00f2386c33038aa9c`
- 开始前 tag：`v0.1.693-local-launcher-zdoc-local-app-v1-ollama-server-recovery-blocker-review-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-057-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-RECOVERY-BLOCKER-REVIEW-GATE`

实际最近提交：

```text
42e2317 (HEAD -> main, tag: v0.1.693-local-launcher-zdoc-local-app-v1-ollama-server-recovery-blocker-review-gate, origin/main, origin/HEAD) LOCAL-LAUNCHER-057 ollama recovery blocker review
```

开始前 `git status --short` 无输出。

开始前执行：

```bash
git diff --check
git diff --cached --check
```

两项均无输出。

## 2. 上游节点状态复核

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-server-recovery-blocker-review-gate-local-launcher-057.md`
2. `docs/zdoc-local-launcher-v1-ollama-server-recovery-execution-gate-local-launcher-056.md`
3. `docs/zdoc-local-launcher-v1-ollama-server-recovery-authorization-gate-local-launcher-055.md`
4. `docs/zdoc-local-launcher-v1-ollama-prompt-control-smoke-test-blocker-review-gate-local-launcher-054.md`
5. `docs/zdoc-local-launcher-v1-ollama-prompt-control-smoke-test-execution-gate-local-launcher-053.md`

复核结果：

1. 053 Prompt control smoke test execution 判定：`BLOCKED`。
2. 053 因 Ollama server PID 与监听端口不可复核，未执行 `ollama run`。
3. 054 blocker review completed，确认 053 blocker 为 Ollama server 运行状态不可复核。
4. 055 recovery authorization completed，建立了 056 recovery execution 的授权边界。
5. 056 recovery execution 判定：`BLOCKED`。
6. 056 已按授权执行一次 `ollama serve`。
7. 056 初次确认 PID `5502` 与 `127.0.0.1:11434 LISTEN`。
8. 056 随后未能持续确认 PID 与监听端口。
9. 057 recovery blocker review completed。
10. 057 已确认核心问题是 `ollama serve` 启动后未能持续确认 PID 与 LISTEN。
11. 057 已确认当前不应继续 Prompt control smoke test 或任何模型测试。

056 当前 decision：

```text
LOCAL-LAUNCHER-056 ZDOC LOCAL APP V1 OLLAMA SERVER RECOVERY EXECUTION GATE COMPLETED WITH BLOCKERS / OLLAMA SERVER RECOVERY NOT CONFIRMED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

057 当前 decision：

```text
LOCAL-LAUNCHER-057 ZDOC LOCAL APP V1 OLLAMA SERVER RECOVERY BLOCKER REVIEW GATE COMPLETED / 056 RECOVERY BLOCKER RECORDED / OLLAMA SERVE BRIEFLY STARTED BUT PID AND PORT WERE NOT SUSTAINABLY VERIFIED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO OLLAMA SERVE EXECUTED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 3. 056 / 057 阻断事实摘要

本节点记录以下事实：

1. 056 已确认 `ollama` 可执行程序路径：`/opt/homebrew/bin/ollama`。
2. 056 已确认 `ollama` client version：`0.21.2`。
3. 056 recovery 前未发现 `ollama` 进程。
4. 056 recovery 前未发现 `127.0.0.1:11434 LISTEN`。
5. 056 已按授权执行一次 `ollama serve`。
6. 056 初次确认 PID：`5502`。
7. 056 初次确认监听端口：`127.0.0.1:11434 LISTEN`。
8. 056 随后复核未发现存活 PID。
9. 056 随后复核未发现 `127.0.0.1:11434 LISTEN`。
10. 056 判定：`BLOCKED`。
11. 056 未执行 `ollama list`。
12. 056 未执行 `ollama run`。
13. 056 未执行 `ollama pull`。
14. 056 未运行模型。
15. 056 未输入 prompt。
16. 056 未读取真实 KG / 真实项目资料。
17. 056 未触发 ZDoc generation/export/write-back。
18. 056 未进入 trial。
19. 057 已确认核心问题是 `ollama serve` 启动后未能持续确认 PID 与 LISTEN。
20. 057 已确认当前不应继续任何模型测试。

## 4. Diagnostics 问题定义

本节点明确：

1. 当前问题不是 `ollama` 可执行程序缺失。
2. 当前问题不是 client version 未知。
3. 当前问题不是模板 B 失败。
4. 当前问题不是模型推理失败。
5. 当前问题是 `ollama serve` 启动后未能持续运行或未能持续监听。
6. diagnostics 的目标是查明非敏感层面的服务退出或监听失败原因。
7. diagnostics 不等于恢复服务。
8. diagnostics 不等于模型运行授权。
9. diagnostics 不等于 prompt 输入授权。
10. diagnostics 不等于真实数据读取授权。
11. diagnostics 不等于 trial / generation / export / write-back 授权。

## 5. 未来 059 可授权范围草案

以下内容仅作为未来 `LOCAL-LAUNCHER-059` 授权草案记录，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-059`，Ollama server diagnostics execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 056 `BLOCKED`。
6. 复核 057 blocker review。
7. 复核 058 diagnostics authorization boundary。
8. 检查 `ollama` 可执行程序路径。
9. 检查 `ollama` client version。
10. 检查当前是否已有 `ollama` 进程。
11. 检查当前是否已有 `127.0.0.1:11434 LISTEN`。
12. 检查非敏感进程摘要。
13. 检查端口占用摘要。
14. 检查是否存在 Homebrew service 管理状态摘要。
15. 检查是否存在 launchctl 管理状态摘要。
16. 如 056 节点的 `/tmp` 临时捕获文件仍存在，仅允许读取最多前 40 行，并仅记录非敏感摘要；若疑似敏感，不复制内容。
17. 不执行 `ollama serve`。
18. 不执行 `ollama list`。
19. 不执行 `ollama run`。
20. 不执行 `ollama pull`。
21. 不访问 endpoint。
22. 不运行模型。
23. 不输入 prompt。
24. 不下载模型。
25. 不读取真实 KG / 真实项目资料。
26. 不触发 generation/export/write-back。
27. 完成后立即回报并停止。

未来 059 可考虑的命令草案包括但不限于：

```bash
command -v ollama
ollama --version
pgrep -fl "ollama"
lsof -nP -iTCP:11434 -sTCP:LISTEN
brew services list | grep -i ollama
launchctl list | grep -i ollama
```

如需读取 056 的 `/tmp` 临时捕获文件，必须只读取 056 明确创建的临时文件，且不得读取任何项目日志、业务日志、真实数据日志、output/job/export 正文。

## 6. 未来 059 禁止范围草案

未来 059 仍应禁止：

1. 执行 `ollama serve`。
2. 执行 `ollama list`。
3. 执行 `ollama run`。
4. 执行 `ollama pull`。
5. 执行 `ollama create`。
6. 执行 `ollama rm`。
7. 执行 `ollama cp`。
8. 执行任何模型推理。
9. 向模型输入任何 prompt。
10. 下载模型。
11. 删除模型。
12. 创建模型。
13. 运行多个模型。
14. 执行性能 benchmark。
15. 执行长文本生成。
16. 访问 ZDoc endpoint。
17. 访问 Ollama endpoint。
18. 执行 curl / HTTP request。
19. 再次访问 `/health`。
20. 读取真实 KG。
21. 读取真实项目资料。
22. 读取真实招标文件。
23. 读取用户隐私或业务数据。
24. 读取 `.env` / secrets / tokens / credentials。
25. 读取 registration / metadata / proof / manifest / sample 实例。
26. 读取 output/job/export 正文。
27. 读取项目日志正文。
28. 读取业务日志正文。
29. 复制任何疑似敏感 stdout/stderr 内容。
30. 触发 ZDoc generation。
31. 触发 export。
32. 触发 write-back。
33. 写 output/job/export。
34. 进入 trial。
35. 进入真实使用。
36. 进入 50 人正式使用。
37. 修改 V0/V1/backend/frontend/config/dependency。
38. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
39. 运行测试/lint/build。
40. 启动、重启、停止任何服务。
41. 进入 `LOCAL-LAUNCHER-060`。

## 7. 未来 059 阻断条件

未来 059 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 056 `BLOCKED` 无法复核。
4. 057 blocker review 无法复核。
5. 058 authorization boundary 无法复核。
6. diagnostics 需要执行 `ollama serve`。
7. diagnostics 需要执行 `ollama list`。
8. diagnostics 需要执行 `ollama run`。
9. diagnostics 需要访问 endpoint。
10. diagnostics 需要 curl / HTTP request。
11. diagnostics 需要读取真实 KG。
12. diagnostics 需要读取真实项目资料。
13. diagnostics 需要读取真实招标文件。
14. diagnostics 需要读取 `.env` / secrets / tokens / credentials。
15. diagnostics 需要读取 output/job/export 正文。
16. diagnostics 需要读取项目日志或业务日志正文。
17. diagnostics 需要复制疑似敏感 stdout/stderr。
18. diagnostics 需要触发 generation/export/write-back。
19. diagnostics 需要修改 V0/V1/backend/frontend/config/dependency。
20. diagnostics 无法在授权范围内形成非敏感结论。

## 8. 用户授权文本模板

后续如需进入 059，用户可直接复制以下授权文本：

```text
我明确授权 LOCAL-LAUNCHER-059 执行 Ollama server diagnostics execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 056 BLOCKED、复核 057 blocker review、复核 058 diagnostics authorization boundary、检查 ollama 可执行程序路径、检查 ollama client version、检查当前是否已有 ollama 进程、检查当前是否已有 127.0.0.1:11434 LISTEN、检查非敏感进程摘要、检查端口占用摘要、检查 Homebrew service 管理状态摘要、检查 launchctl 管理状态摘要；如 056 节点的 /tmp 临时捕获文件仍存在，仅允许读取最多前 40 行并只记录非敏感摘要，疑似敏感内容不得复制。严格禁止执行 ollama serve、ollama list、ollama run、ollama pull、ollama create、ollama rm、任何模型推理、向模型输入 prompt、下载模型、删除模型、创建模型、运行多个模型、执行性能 benchmark、执行长文本生成、访问 ZDoc endpoint、访问 Ollama endpoint、执行 curl/HTTP request、再次访问 /health、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、读取项目日志或业务日志正文、触发 ZDoc generation、触发 export、触发 write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用、修改 V0/V1/backend/frontend/config/dependency、启动/重启/停止任何服务。若 diagnostics 需要服务启动、模型运行、prompt 输入、真实数据、业务 endpoint、生成导出写回或超出授权范围，必须判定 BLOCKED 并停止。执行完成或阻断后必须回报并停止，不得进入下一节点。
```

## 9. 进入 059 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-059-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-DIAGNOSTICS-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不进入 059。

## 10. 服务状态策略

服务状态策略如下：

1. 当前不能确认 Ollama server 正在运行。
2. 056 显示 `ollama serve` 曾短暂启动，但未能持续确认。
3. 本节点不授权启动、停止或重启任何服务。
4. diagnostics 需要单独 execution gate。
5. diagnostics 成功后也不等于授权 recovery。
6. recovery 必须另设后续 authorization/execution gate。
7. Prompt control smoke test 重试必须另设后续 authorization/execution gate。
8. 当前 ZDoc 服务状态本节点不重新复核。
9. 如需停止 ZDoc 或其他服务，应另设 controlled stop authorization gate 与 execution gate。

## 11. 后续授权门拆分原则

后续必须遵守：

1. Ollama server diagnostics 必须先 authorization，再 execution。
2. `ollama serve` 必须单独授权。
3. `ollama list` 必须单独授权。
4. `ollama run` 必须单独授权。
5. prompt 输入到模型必须单独授权。
6. Prompt control smoke test 重试必须另设执行门。
7. ZDoc 调用 Ollama 必须另设授权门。
8. 真实 KG / 真实项目资料读取必须另设授权门。
9. generation/export/write-back 必须另设授权门。
10. trial 必须另设授权门。
11. 50 人正式使用必须另设 readiness 与 deployment gate。
12. ZBid 写回必须另设专门授权链路。

## 12. 实际执行命令清单

本节点实际执行的 git 状态确认命令：

```bash
git status --short
git log -1 --format=%H
git tag --points-at HEAD
git log -1 --oneline --decorate=short
git diff --check
git diff --cached --check
```

本节点实际执行的只读文档查看命令：

```bash
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-server-recovery-blocker-review-gate-local-launcher-057.md
sed -n '261,460p' docs/zdoc-local-launcher-v1-ollama-server-recovery-blocker-review-gate-local-launcher-057.md
sed -n '1,260p' docs/zdoc-local-launcher-v1-ollama-server-recovery-execution-gate-local-launcher-056.md
sed -n '261,520p' docs/zdoc-local-launcher-v1-ollama-server-recovery-execution-gate-local-launcher-056.md
sed -n '1,220p' docs/zdoc-local-launcher-v1-ollama-server-recovery-authorization-gate-local-launcher-055.md
sed -n '1,220p' docs/zdoc-local-launcher-v1-ollama-prompt-control-smoke-test-blocker-review-gate-local-launcher-054.md
sed -n '1,220p' docs/zdoc-local-launcher-v1-ollama-prompt-control-smoke-test-execution-gate-local-launcher-053.md
```

本节点未执行任何诊断命令。

本节点未执行任何 Ollama 命令。

## 13. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未运行 npm/yarn/pnpm/pip。
7. 未运行测试/lint/build。
8. 未打开 HTML 页面。
9. 未启动新 ZDoc 服务。
10. 未重启 ZDoc 服务。
11. 未停止 ZDoc 服务。
12. 未启动新的 Ollama server。
13. 未重启 Ollama server。
14. 未停止 Ollama server。
15. 未执行 `ollama serve`。
16. 未执行 `ollama list`。
17. 未执行 `ollama run`。
18. 未执行 `ollama pull`。
19. 未执行任何 Ollama 命令。
20. 未执行任何系统诊断命令。
21. 未执行模型推理。
22. 未向模型输入任何 prompt。
23. 未下载/删除/创建模型。
24. 未运行多个模型。
25. 未访问 endpoint。
26. 未执行 curl / HTTP request。
27. 未再次访问 `/health`。
28. 未读取真实 KG。
29. 未读取真实项目资料。
30. 未读取真实招标文件。
31. 未读取 `.env` / secrets / tokens / credentials。
32. 未读取 registration / metadata / proof / manifest / sample 实例。
33. 未读取 output/job/export 正文。
34. 未读取日志正文。
35. 未读取 `/tmp` 临时 stdout/stderr 捕获文件正文。
36. 未触发 ZDoc generation/export/write-back。
37. 未写 output/job/export。
38. 未进入 trial。
39. 未进入真实使用。
40. 未进入 50 人正式使用。
41. 未进入 `LOCAL-LAUNCHER-059`。

## 14. 当前 Decision

```text
LOCAL-LAUNCHER-058 ZDOC LOCAL APP V1 OLLAMA SERVER DIAGNOSTICS AUTHORIZATION GATE COMPLETED / OLLAMA SERVER DIAGNOSTICS EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO DIAGNOSTIC COMMAND EXECUTED / NO OLLAMA COMMAND EXECUTED / NO OLLAMA SERVE EXECUTED / NO OLLAMA LIST EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 15. 下一节点建议

下一节点建议：

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-059-ZDOC-LOCAL-APP-V1-OLLAMA-SERVER-DIAGNOSTICS-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 059。
4. 059 即使后续被授权，也只允许 diagnostics。
5. 059 不授权 `ollama serve`。
6. 059 不授权 `ollama list`。
7. 059 不授权 `ollama run`。
8. 059 不授权模型推理。
9. 059 不授权 prompt 输入。
10. 059 不授权真实 KG / 真实项目资料读取。
11. 059 不授权 trial。
12. 059 不授权 generation/export/write-back。
13. 后续 recovery 必须另设 authorization/execution gate。

## 16. 明确说明未进入 `LOCAL-LAUNCHER-059`

本节点未进入 `LOCAL-LAUNCHER-059`。
