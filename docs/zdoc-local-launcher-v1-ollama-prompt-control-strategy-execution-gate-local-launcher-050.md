# LOCAL-LAUNCHER-050 ZDoc Local App V1 Ollama Prompt Control Strategy Execution Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-050-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-EXECUTION-GATE`

本节点性质：

`Ollama prompt control strategy execution only`

本节点目标：

在不执行任何 Ollama 命令、不运行模型、不向模型输入 prompt 的前提下，基于 047/048 已记录的 `CONTROL_GAP` 事实，形成下一轮输出控制 smoke test 的 Prompt 控制策略、候选模板、判定标准和执行边界。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不向模型输入 prompt。
4. 不修改 prompt 后直接重试模型。
5. 不访问 endpoint。
6. 不触发 ZDoc generation/export/write-back。
7. 不读取真实 KG、真实项目资料或真实招标文件。
8. 不进入 `LOCAL-LAUNCHER-051`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`f073490ecd83122b5b691718df3b48b978e55f7e`
- 开始前 tag：`v0.1.685-local-launcher-zdoc-local-app-v1-ollama-prompt-control-strategy-authorization-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-049-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-AUTHORIZATION-GATE`

实际最近提交：

```text
f073490 (HEAD -> main, tag: v0.1.685-local-launcher-zdoc-local-app-v1-ollama-prompt-control-strategy-authorization-gate, origin/main, origin/HEAD) LOCAL-LAUNCHER-049 ollama prompt control strategy authorization
```

开始前 `git status --short` 无输出。

## 3. 上游节点通过状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md`
2. `docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md`
3. `docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-authorization-gate-local-launcher-049.md`
4. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md`
5. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md`
6. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md`
7. `docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md`

复核结果：

1. 047 output control 判定：`CONTROL_GAP`。
2. 048 output control gap review completed。
3. 049 Prompt control strategy authorization completed。
4. 043 smoke test 判定：`PASS`。
5. 044 smoke test result closed。
6. 045 next-stage strategy completed。
7. 046 output control authorization completed。

047 当前 decision：

```text
LOCAL-LAUNCHER-047 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH OUTPUT CONTROL GAP / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

048 当前 decision：

```text
LOCAL-LAUNCHER-048 ZDOC LOCAL APP V1 OLLAMA OUTPUT CONTROL GAP REVIEW GATE COMPLETED / OUTPUT CONTROL GAP RECORDED / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO ADDITIONAL OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

049 当前 decision：

```text
LOCAL-LAUNCHER-049 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL STRATEGY AUTHORIZATION GATE COMPLETED / PROMPT CONTROL STRATEGY EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 4. 当前问题复核

047 已记录的输出控制 smoke test 事实如下：

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
11. 048 已确认该问题不是安全越界。
12. 048 已确认该问题是输出格式控制不足。

本节点复核结论：

1. 当前问题不是模型不可用。
2. 当前问题不是模型无法响应。
3. 当前问题不是安全越界。
4. 当前问题是模型输出控制不足。
5. 当前问题不改变 043 最小 smoke test `PASS` 结论。
6. 当前问题提示后续正式生成、结构化输出和自动校验前必须先明确输出控制策略。

## 5. Prompt 控制策略目标

本节点设计的 Prompt 控制策略目标如下：

1. 降低 thinking 文本出现概率。
2. 强化最终答案边界。
3. 强化“一行输出”约束。
4. 强化无 Markdown、无解释、无多余文本约束。
5. 明确失败时输出格式。
6. 明确后续执行门的判定标准。
7. 不使用真实业务 prompt。
8. 不接入真实 KG / 真实项目资料。
9. 不触发 ZDoc generation/export/write-back。
10. 不进入 trial。

策略原则：

1. 使用固定字符串契约优先于开放式说明。
2. 将完整输出定义为可机器比对的目标。
3. 将禁止项写成输出边界，而不是业务任务。
4. 不引入真实施工组织设计、技术标、项目资料、KG 或招标文件内容。
5. 不把候选模板输入模型；本节点仅写入文档。

## 6. 候选 Prompt 模板

以下候选模板仅写入文档，未输入模型。

### 模板 A：极简硬约束模板

模板文本：

```text
请只输出 OK 两个字符。不要输出任何其他内容。不要输出思考过程。不要解释。不要使用 Markdown。
```

控制意图：

1. 用最短中文指令压缩任务空间。
2. 明确目标字符串为 `OK`。
3. 用否定约束排除 thinking、解释和 Markdown。

预期输出：

```text
OK
```

潜在风险：

1. 模型可能仍先输出 thinking 文本。
2. “不要输出任何其他内容”可能不足以压制内部思考外显。
3. 若模型将指令解释为普通对话，仍可能添加说明。

后续执行门判定要点：

1. 完整输出严格等于 `OK` 才可判定 `STRICT_PASS`。
2. 出现 thinking、解释、多行或其他字符则判定 `CONTROL_GAP`。
3. 若需要再次运行或修改 prompt 才能判断，则应停止并另设授权门。

### 模板 B：格式契约模板

模板文本：

```text
输出格式契约：你的完整输出必须严格等于 OK。不得包含空行、标点、解释、Markdown、思考过程或其他字符。
```

控制意图：

1. 将输出要求定义为“完整输出”的格式契约。
2. 明确完整输出必须严格等于 `OK`。
3. 明确禁止空行、标点、解释、Markdown、思考过程和其他字符。
4. 便于后续执行门直接做字符串级判定。

预期输出：

```text
OK
```

潜在风险：

1. 模型可能仍显示 thinking 文本后再输出 `OK`。
2. “格式契约”本身可能触发模型解释契约含义。
3. 终端输出中若存在控制字符，后续记录需只做非敏感摘要，不复制长输出。

后续执行门判定要点：

1. 完整输出严格等于 `OK`，且无 thinking、解释、Markdown、多行或额外字符，才可判定 `STRICT_PASS`。
2. 最终包含 `OK` 但不是唯一输出，应判定 `CONTROL_GAP`。
3. 输出疑似敏感、无响应或需要越界操作，应判定 `BLOCKED`。

### 模板 C：失败兜底模板

模板文本：

```text
无论是否需要解释，你都只能输出 OK。若无法遵守，也输出 OK。禁止输出原因、说明、思考过程、Markdown。
```

控制意图：

1. 将“无法遵守”的兜底输出也固定为 `OK`。
2. 尝试避免模型因无法遵守而解释原因。
3. 将失败路径也纳入固定字符串输出。

预期输出：

```text
OK
```

潜在风险：

1. “若无法遵守”可能诱发模型讨论无法遵守的原因。
2. 兜底语义可能不如格式契约便于严格判定。
3. 仍可能出现 thinking 文本或解释性内容。

后续执行门判定要点：

1. 完整输出严格等于 `OK` 才可判定 `STRICT_PASS`。
2. 出现原因、说明、thinking、Markdown 或多行时，应判定 `CONTROL_GAP`。
3. 不得在同一节点修改模板后重试。

### 模板 D：中英混合固定输出模板

模板文本：

```text
Return exactly one line: OK. Do not output thinking, explanation, Markdown, punctuation, blank lines, or any other characters.
```

控制意图：

1. 使用英文固定输出指令，降低中文自然语言解释空间。
2. 明确 one line 和 exactly。
3. 排除 thinking、解释、Markdown、标点、空行和其他字符。

预期输出：

```text
OK
```

潜在风险：

1. 英文指令不一定优于中文指令。
2. 模型仍可能输出 thinking 文本。
3. 后续如要比较语言差异，必须另设授权门，不得自动多模型或多 prompt 测试。

后续执行门判定要点：

1. 完整输出严格等于 `OK` 才可判定 `STRICT_PASS`。
2. 任意附加内容均为 `CONTROL_GAP`。
3. 不得把模板 D 与其他模板合并多轮测试，除非另行授权。

## 7. 推荐后续执行模板

推荐用于未来输出控制 smoke test execution 的模板：

`模板 B：格式契约模板`

推荐模板文本：

```text
输出格式契约：你的完整输出必须严格等于 OK。不得包含空行、标点、解释、Markdown、思考过程或其他字符。
```

推荐理由：

1. 相比单纯否定约束，格式契约更便于判定。
2. 完整输出必须严格等于 `OK`，可直接用于 `STRICT_PASS` 判断。
3. 不依赖业务上下文。
4. 不需要真实数据。
5. 不涉及 ZDoc generation/export/write-back。
6. 与 047 的 `CONTROL_GAP` 差距直接对应。

## 8. 后续执行门判定规则

未来真正执行新的输出控制 smoke test 前，仍必须另设 authorization gate 与 execution gate。本节点仅设计判定规则。

### STRICT_PASS

同时满足以下条件，方可判定 `STRICT_PASS`：

1. 模型返回响应。
2. 完整输出严格等于 `OK`。
3. 无 thinking 文本。
4. 无解释。
5. 无 Markdown。
6. 无多行。
7. 无前后空白以外内容。
8. 未触发任何禁止项。

建议 decision：

```text
LOCAL-LAUNCHER-052 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL SMOKE TEST EXECUTION GATE PASSED / STRICT ONE-LINE OK OUTPUT CONFIRMED / NO THINKING TEXT OBSERVED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

### CONTROL_GAP

同时满足以下条件时，判定 `CONTROL_GAP`：

1. 模型返回响应。
2. 未触发禁止项。
3. 但完整输出不严格等于 `OK`。
4. 出现 thinking 文本、解释、Markdown、多行或其他附加内容。

建议 decision：

```text
LOCAL-LAUNCHER-052 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH OUTPUT CONTROL GAP / MODEL RESPONDED BUT STRICT ONE-LINE OK FORMAT NOT FULLY CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

### BLOCKED

出现以下任一情况，应判定 `BLOCKED`：

1. 工作区不 clean。
2. HEAD/tag 不符合预期。
3. 上游结果无法复核。
4. 模型未响应。
5. 输出疑似敏感。
6. 需要真实数据。
7. 需要访问业务 endpoint。
8. 需要触发 generation/export/write-back。
9. 需要运行多个模型。
10. 无法在授权范围内完成。

建议 decision：

```text
LOCAL-LAUNCHER-052 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL SMOKE TEST EXECUTION GATE COMPLETED WITH BLOCKERS / PROMPT CONTROL SMOKE TEST NOT CONFIRMED / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 9. 后续执行门风险边界

未来新的输出控制 smoke test execution gate 至少应保持以下边界：

1. 只能使用一个已授权模型。
2. 只能执行一次指定 `ollama run`。
3. 只能使用一个已授权 prompt 模板。
4. prompt 必须无业务含义、无隐私、无真实数据。
5. 不得读取真实 KG。
6. 不得读取真实项目资料。
7. 不得读取真实招标文件。
8. 不得访问 ZDoc endpoint。
9. 不得访问 Ollama endpoint。
10. 不得执行 benchmark。
11. 不得执行长文本生成。
12. 不得触发 ZDoc generation/export/write-back。
13. 不得写 output/job/export。
14. 不得进入 trial、真实使用或 50 人正式使用。
15. 输出超过 100 字时，仅记录 100 字以内非敏感摘要。
16. 输出疑似敏感时，不复制响应正文，并按授权规则判定。

## 10. 后续执行门建议

下一节点建议：

`LOCAL-LAUNCHER-051-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-RESULT-RECORD-GATE`

051 只能记录 Prompt 控制策略设计结果，不得运行模型。

再后续可考虑：

`LOCAL-LAUNCHER-052-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

052 才是新的输出控制 smoke test 授权门，仍不得直接执行模型。

必须明确：

1. 051 不授权 `ollama run`。
2. 051 不授权 prompt 输入到模型。
3. 051 不授权模型推理。
4. 052 也只能是 authorization gate。
5. 真正执行新一轮 smoke test 必须另设 execution gate。
6. trial / generation / export / write-back 必须另设授权门。
7. 真实 KG / 真实项目资料读取必须另设授权门。
8. 50 人正式使用必须另设 readiness 与 deployment gate。

## 11. 实际执行命令清单

本节点实际执行的 git 状态确认命令：

```bash
git status --short
git log -1 --format=%H
git log -1 --oneline --decorate=short
git tag --points-at HEAD
```

本节点实际执行的只读文档查看命令：

```bash
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-authorization-gate-local-launcher-049.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-authorization-gate-local-launcher-046.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-next-stage-strategy-gate-local-launcher-045.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-result-record-gate-local-launcher-044.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-model-run-smoke-test-execution-gate-local-launcher-043.md
```

本节点未执行任何 Ollama 命令、HTTP request、endpoint 访问、测试、lint 或 build。

## 12. 禁止项确认

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
34. 未修改 prompt 后重试模型。
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
60. 未进入 `LOCAL-LAUNCHER-051`。

## 13. 当前 Decision

`LOCAL-LAUNCHER-050 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL STRATEGY EXECUTION GATE PASSED / PROMPT CONTROL STRATEGY DESIGNED BASED ON OUTPUT CONTROL GAP / CANDIDATE PROMPT TEMPLATES DOCUMENTED WITHOUT MODEL EXECUTION / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED`

## 14. 明确说明未进入 `LOCAL-LAUNCHER-051`

本节点未进入 `LOCAL-LAUNCHER-051`。
