# LOCAL-LAUNCHER-049 ZDoc Local App V1 Ollama Prompt Control Strategy Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-AUTHORIZATION-GATE`

本节点性质：

`Ollama prompt control strategy authorization boundary and user authorization request only`

本节点目标：

记录未来是否可以执行 Prompt 控制策略设计的授权边界、禁止事项、阻断条件、用户授权文本模板和后续进入条件。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不向模型输入 prompt。
4. 不修改 prompt 后直接重试模型。
5. 不访问 endpoint。
6. 不触发 ZDoc generation/export/write-back。
7. 不读取真实 KG、真实项目资料或真实招标文件。
8. 不进入 `LOCAL-LAUNCHER-050`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`43e1e16272740322629765858ebea3f98ebc9bbc`
- 开始前 tag：`v0.1.684-local-launcher-zdoc-local-app-v1-ollama-output-control-gap-review-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-048-ZDOC-LOCAL-APP-V1-OLLAMA-OUTPUT-CONTROL-GAP-REVIEW-GATE`

实际最近提交：

```text
43e1e16 (HEAD -> main, tag: v0.1.684-local-launcher-zdoc-local-app-v1-ollama-output-control-gap-review-gate, origin/main, origin/HEAD) LOCAL-LAUNCHER-048 ollama output control gap review
```

开始前 `git status --short` 无输出。

## 3. 上游节点通过状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`
2. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
3. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md`
4. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md`
5. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md`
6. `docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md`

复核结果：

1. 043 smoke test 判定：`PASS`。
2. 044 smoke test result closed。
3. 045 next-stage strategy completed。
4. 046 output control authorization completed。
5. 047 output control 判定：`CONTROL_GAP`。
6. 048 output control gap review completed。

043 当前 decision：

```text
LOCAL-LAUNCHER-043 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST EXECUTION GATE PASSED / MINIMAL MODEL RUN SMOKE TEST COMPLETED WITH QWEN3 0.6B / NON-SENSITIVE RESPONSE SUMMARY RECORDED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

044 当前 decision：

```text
LOCAL-LAUNCHER-044 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST RESULT RECORD GATE COMPLETED / MODEL RUN SMOKE TEST PASS RECORDED / MINIMAL QWEN3 0.6B RESPONSE RESULT CLOSED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

045 当前 decision：

```text
LOCAL-LAUNCHER-045 ZDOC LOCAL APP V1 OLLAMA MODEL RUN SMOKE TEST NEXT STAGE STRATEGY GATE COMPLETED / NEXT STAGE STRATEGY DOCUMENTED AFTER MODEL RUN SMOKE TEST PASS / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

046 当前 decision：

```text
LOCAL-LAUNCHER-046 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST AUTHORIZATION GATE COMPLETED / OUTPUT CONTROL SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

047 当前 decision：

```text
LOCAL-LAUNCHER-047 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH OUTPUT CONTROL GAP / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

048 当前 decision：

```text
LOCAL-LAUNCHER-048 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL GAP REVIEW GATE COMPLETED / OUTPUT CONTROL GAP RECORDED / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 4. 当前系统状态判断

当前系统状态如下：

1. ZDoc 本地服务 controlled start 已完成。
2. ZDoc post-start status 已 `PASS`。
3. ZDoc endpoint health check 已 `PASS`。
4. endpoint health check result 已闭环。
5. Ollama server 已启动。
6. Ollama server post-start status 已 `PASS`。
7. 本地模型清单已确认。
8. 模型选择建议已完成。
9. `qwen3:0.6b` 最小 smoke test 已 `PASS`。
10. 输出控制 smoke test 已完成但结果为 `CONTROL_GAP`。
11. 当前仍不具备 trial / generation / export / write-back 条件。
12. 当前仍不具备真实 KG / 真实项目资料读取条件。
13. 当前仍不具备真实业务 prompt 条件。

说明：本节点未重新探测服务、进程、端口、endpoint 或 Ollama；上述状态来自 043、044、045、046、047、048 文档链的只读复核。

## 5. 047 / 048 输出控制差距摘要

047 / 048 已记录事实如下：

1. 047 使用模型：`qwen3:0.6b`。
2. 047 prompt：`只输出一行：OK。不要输出思考过程，不要解释，不要使用 Markdown。`
3. prompt 性质：无业务含义、无隐私、无真实数据。
4. `ollama run` 执行次数：1 次。
5. 是否返回响应：是。
6. 响应耗时：约 `1.1102 seconds`。
7. 非敏感响应摘要：`输出包含非敏感 thinking 文本，最终返回 OK；响应超过 100 字，未复制完整长输出。`
8. 是否出现 thinking 文本：是。
9. 是否严格满足“一行 OK”：否。
10. 判定：`CONTROL_GAP`。
11. 048 已确认 `CONTROL_GAP` 不等于安全越界。
12. 048 已确认问题集中在输出格式控制，而不是服务连通性。

## 6. Prompt 控制策略问题定义

本节点明确：

1. 当前问题不是模型不可用。
2. 当前问题不是模型无法响应。
3. 当前问题不是安全越界。
4. 当前问题是模型输出控制不足。
5. 输出中 thinking 文本可能干扰后续结构化解析。
6. 输出中 thinking 文本可能影响正式文档成稿质量。
7. 后续必须先设计 Prompt 控制策略，再决定是否重新执行输出控制 smoke test。
8. Prompt 控制策略不得直接等同于执行模型测试。

## 7. 未来 050 可授权范围草案

以下仅作为未来 `LOCAL-LAUNCHER-050` 可授权范围草案，本节点不执行。

未来若用户明确授权 `LOCAL-LAUNCHER-050`，Prompt 控制策略 execution 范围建议仅限：

1. 仓库路径确认。
2. 当前分支确认。
3. HEAD/tag 确认。
4. 工作区 clean 确认。
5. 复核 047 `CONTROL_GAP`。
6. 复核 048 gap review。
7. 基于 047/048 已记录结果，设计更强的输出控制策略。
8. 在文档中设计候选 prompt 模板，但不得输入模型。
9. 设计输出格式约束：
   - 仅输出最终答案。
   - 禁止 thinking 文本。
   - 禁止解释。
   - 禁止 Markdown。
   - 限制为单行。
   - 限制最大字数。
   - 明确失败输出格式。
10. 设计后续执行门的判定标准。
11. 设计 `STRICT_PASS`、`CONTROL_GAP`、`BLOCKED` 判定细则。
12. 说明后续真正执行模型测试前仍需单独授权。
13. 不执行任何 Ollama 命令。
14. 不运行模型。
15. 不向模型输入 prompt。
16. 不读取真实 KG / 真实项目资料。
17. 不触发 generation/export/write-back。
18. 完成后立即回报并停止。

必须明确：未来 050 即使被授权，也只是 Prompt 控制策略设计，不等于授权模型运行，不等于授权 prompt 输入到模型。

## 8. 未来 050 禁止范围草案

未来 050 仍应禁止：

1. 执行 `ollama list`。
2. 执行 `ollama run`。
3. 执行 `ollama pull`。
4. 执行 `ollama serve`。
5. 执行任何 Ollama 模型命令。
6. 执行模型推理。
7. 向模型输入任何 prompt。
8. 修改 prompt 后直接重试模型。
9. 运行多个模型。
10. 使用非 `qwen3:0.6b` 模型。
11. 执行性能 benchmark。
12. 执行长文本生成。
13. 下载、删除、创建模型。
14. 读取真实 KG。
15. 读取真实项目资料。
16. 读取真实招标文件。
17. 读取用户隐私或业务数据。
18. 读取 `.env` / secrets / tokens / credentials。
19. 读取 registration / metadata / proof / manifest / sample 实例。
20. 读取 output/job/export 正文。
21. generation。
22. export。
23. write-back。
24. ZBid 写回。
25. trial。
26. 真实使用。
27. 50 人正式使用。
28. 修改 V0/V1/backend/frontend/config/dependency。
29. 创建脚本、App 包、Tauri/Electron 工程、runtime bridge。
30. 运行测试/lint/build。
31. 停止或重启当前 ZDoc 服务，除非后续另行授权。
32. 停止或重启 Ollama server，除非后续另行授权。

## 9. Prompt 控制策略阻断条件

未来 050 如出现以下任一情况，应判定 `BLOCKED`，不得继续：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 047 `CONTROL_GAP` 无法复核。
4. 048 gap review 无法复核。
5. 输出控制差距事实不足以制定策略。
6. 需要再次运行模型才能制定策略。
7. 需要重新输入 prompt 到模型才能制定策略。
8. 需要读取真实 KG 才能制定策略。
9. 需要读取真实项目资料才可制定策略。
10. 需要触发 generation/export/write-back 才能判断。
11. 需要访问 ZDoc 业务 endpoint。
12. 无法在授权范围内形成 Prompt 控制策略。

## 10. 用户授权文本模板

后续如需进入 `LOCAL-LAUNCHER-050`，用户可直接复制以下授权文本：

`我明确授权 LOCAL-LAUNCHER-050 执行 Ollama prompt control strategy execution。授权范围仅限：仓库路径确认、当前分支确认、HEAD/tag 确认、工作区 clean 确认、复核 047 CONTROL_GAP、复核 048 gap review、基于 047/048 已记录结果设计更强的输出控制策略、在文档中设计候选 prompt 模板但不输入模型、设计输出格式约束、设计后续执行门 STRICT_PASS/CONTROL_GAP/BLOCKED 判定细则、说明后续真正执行模型测试前仍需单独授权。严格禁止执行 ollama list、ollama run、ollama pull、ollama serve、任何 Ollama 模型命令、模型推理、向模型输入任何 prompt、修改 prompt 后直接重试模型、运行多个模型、使用非 qwen3:0.6b 模型、执行性能 benchmark、执行长文本生成、读取真实 KG、读取真实项目资料、读取真实招标文件、读取隐私数据、读取 .env/secrets/tokens/credentials、读取 registration/metadata/proof/manifest/sample 实例、读取 output/job/export 正文、触发 generation/export/write-back、写 output/job/export、进入 trial、进入真实使用或 50 人正式使用。若 Prompt 控制策略需要再次运行模型、输入 prompt、读取真实数据、访问业务 endpoint 或触发生成导出写回，必须判定 BLOCKED 并停止。策略完成或阻断后必须回报并停止，不得进入下一节点。`

## 11. 进入 050 的条件

只有用户后续明确发送授权文本后，才可进入：

`LOCAL-LAUNCHER-050-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-EXECUTION-GATE`

若用户未授权，则 hold。

本节点不得进入 `LOCAL-LAUNCHER-050`。

未来 050 即使后续被授权，也仅允许设计 Prompt 控制策略，不允许运行模型。

## 12. 实际执行命令清单

本节点实际执行的 git 状态确认命令：

```bash
git status --short
git log -1 --format=%H
git log -1 --oneline --decorate=short
git tag --points-at HEAD
```

本节点实际执行的只读文档查看命令：

```bash
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md
```

本节点未执行任何 Ollama 命令、HTTP request、endpoint 访问、测试、lint 或 build。

## 13. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未创建真正 App 包。
7. 未创建 Tauri 工程。
8. 未创建 Electron 工程。
9. 未创建 runtime bridge。
10. 未运行 npm/yarn/pnpm/pip。
11. 未运行测试/lint/build。
12. 未打开 HTML 页面。
13. 未启动新 ZDoc 服务。
14. 未重启 ZDoc 服务。
15. 未停止 ZDoc 服务。
16. 未启动新的 Ollama server。
17. 未重启 Ollama server。
18. 未停止 Ollama server。
19. 未访问 endpoint。
20. 未访问 ZDoc endpoint。
21. 未访问 Ollama endpoint。
22. 未执行 curl / HTTP request。
23. 未再次访问 `/health`。
24. 未执行 `ollama list`。
25. 未执行 `ollama run`。
26. 未执行 `ollama pull`。
27. 未执行 `ollama serve`。
28. 未执行 `ollama create`。
29. 未执行 `ollama rm`。
30. 未执行 `ollama cp`。
31. 未执行任何 Ollama 模型命令。
32. 未执行模型推理。
33. 未向模型输入任何 prompt。
34. 未修改 prompt 后重试。
35. 未下载模型。
36. 未删除模型。
37. 未创建模型。
38. 未运行多个模型。
39. 未使用非 `qwen3:0.6b` 模型。
40. 未执行性能 benchmark。
41. 未执行长文本生成。
42. 未使用真实业务 prompt。
43. 未使用真实技术标内容。
44. 未使用真实项目资料内容。
45. 未读取真实 KG。
46. 未读取真实项目资料。
47. 未读取真实招标文件。
48. 未读取用户隐私或业务数据。
49. 未读取 `.env`、`.env.*`、secret、token、credential、key、private 配置。
50. 未读取 registration / metadata / proof / manifest / sample 实例。
51. 未读取 output/job/export 正文。
52. 未读取日志正文。
53. 未触发 ZDoc generation。
54. 未触发 export。
55. 未触发 write-back。
56. 未写 output/job/export。
57. 未进入 trial。
58. 未进入真实使用。
59. 未进入 50 人正式使用。
60. 未进入 `LOCAL-LAUNCHER-050`。

## 14. 当前 Decision

`LOCAL-LAUNCHER-049 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL STRATEGY AUTHORIZATION GATE COMPLETED / PROMPT CONTROL STRATEGY EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 15. 下一节点建议

1. 若用户明确授权，可进入：

   `LOCAL-LAUNCHER-050-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-EXECUTION-GATE`

2. 若用户未授权，则 hold。
3. 本节点不得进入 050。
4. 050 即使后续被授权，也仅允许设计 Prompt 控制策略，不允许运行模型。
5. 真正再次执行输出控制 smoke test 必须另设后续 authorization gate 与 execution gate。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 50 人正式使用必须另设 readiness 与 deployment gate。

## 16. 明确说明未进入 `LOCAL-LAUNCHER-050`

本节点未进入 `LOCAL-LAUNCHER-050`。
