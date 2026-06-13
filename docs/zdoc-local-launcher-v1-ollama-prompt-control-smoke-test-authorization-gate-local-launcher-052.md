# LOCAL-LAUNCHER-052 ZDoc Local App V1 Ollama Prompt Control Smoke Test Authorization Gate

## 1. 节点基本信息

节点名称：

`LOCAL-LAUNCHER-052-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-SMOKE-TEST-AUTHORIZATION-GATE`

本节点性质：

`Ollama prompt control smoke test authorization boundary and user authorization request only`

本节点目标：

在不执行任何 Ollama 命令、不运行模型、不向模型输入 prompt 的前提下，基于 047-051 已记录的输出控制与 Prompt 控制策略结果，记录未来 053 是否可执行一次新的 Prompt control smoke test 的授权边界、禁止范围、判定规则、阻断条件与用户授权文本模板。

本节点明确：

1. 不执行任何 Ollama 命令。
2. 不运行模型。
3. 不向模型输入 prompt。
4. 不修改 prompt 后重试模型。
5. 不访问 endpoint。
6. 不执行 curl / HTTP request。
7. 不访问 `/health`。
8. 不触发 ZDoc generation/export/write-back。
9. 不读取真实 KG、真实项目资料或真实招标文件。
10. 不进入 `LOCAL-LAUNCHER-053`。

## 2. 当前基线 HEAD/tag

- 开始前 HEAD：`fcda2aeb4cb1151dab79c442b945536892944123`
- 开始前 tag：`v0.1.687-local-launcher-zdoc-local-app-v1-ollama-prompt-control-strategy-result-record-gate`
- 当前分支：`main`
- 上一节点：`LOCAL-LAUNCHER-051-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-STRATEGY-RESULT-RECORD-GATE`

实际最近提交：

```text
fcda2ae (HEAD -> main, tag: v0.1.687-local-launcher-zdoc-local-app-v1-ollama-prompt-control-strategy-result-record-gate, origin/main, origin/HEAD) LOCAL-LAUNCHER-051 ollama prompt control strategy result record
```

开始前 `git status --short` 无输出。

## 3. 上游节点状态

已只读复核：

1. `docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md`
2. `docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md`
3. `docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-authorization-gate-local-launcher-049.md`
4. `docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-execution-gate-local-launcher-050.md`
5. `docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-result-record-gate-local-launcher-051.md`

复核结果：

1. 047 output control smoke test 已执行一次，模型返回响应，但严格一行 `OK` 未完全满足，判定为 `CONTROL_GAP`。
2. 048 output control gap review completed，确认问题为输出格式控制不足，不是安全越界。
3. 049 Prompt control strategy authorization gate completed，仅授权 050 设计策略，不授权模型运行。
4. 050 Prompt control strategy execution gate passed，已形成候选模板、推荐模板和判定规则。
5. 051 Prompt control strategy result record gate completed，已记录 050 结果闭环，并建议 052 作为新的 smoke test authorization gate。

## 4. 当前策略结果摘要

050 已记录的策略结果：

1. 已基于 047/048 的 `CONTROL_GAP` 事实设计 Prompt 控制策略。
2. 已形成候选模板 A-D。
3. 已推荐后续执行模板为：`模板 B：格式契约模板`。
4. 已设计未来执行门的 `STRICT_PASS / CONTROL_GAP / BLOCKED` 判定规则。
5. 已明确真正执行模型测试前仍需单独授权。
6. 未执行任何 Ollama 命令。
7. 未运行模型。
8. 未向模型输入 prompt。
9. 未读取真实 KG / 真实项目资料。
10. 未触发 ZDoc generation/export/write-back。
11. 未进入 trial。

051 已记录的结果闭环：

1. 050 策略结果已 closed。
2. 推荐模板 B 已作为后续 smoke test 候选模板记录。
3. 当前仍没有授权再次模型运行。
4. 当前仍没有授权 prompt 输入到模型。
5. 当前仍没有授权 ZDoc + Ollama 集成验证。
6. 当前仍没有授权真实 KG / 真实项目资料读取。
7. 当前仍没有授权 generation/export/write-back。
8. 当前仍没有授权 trial。

本节点结论：

1. 当前可以记录未来 053 的授权边界草案。
2. 当前不能执行模型测试。
3. 当前不能把任何 prompt 输入模型。
4. 当前不能读取真实 KG、项目资料或招标文件。
5. 当前不能触发 ZDoc generation/export/write-back。

## 5. 推荐测试模板

未来 053 推荐使用：

`模板 B：格式契约模板`

未来 053 prompt 草案：

```text
输出格式契约：你的完整输出必须严格等于 OK。不得包含空行、标点、解释、Markdown、思考过程或其他字符。
```

该 prompt 草案的边界：

1. 仅作为未来 053 的待授权草案写入本文档。
2. 本节点未将该 prompt 输入模型。
3. 本节点未运行模型。
4. 本节点未执行 `ollama run`。
5. 本节点未使用任何业务 prompt。
6. 本节点未使用真实施工组织设计、技术标、项目资料、KG 或招标文件内容。
7. 本节点未触发生成、导出或写回。

## 6. 未来 053 可授权范围草案

若用户后续单独明确授权进入 053，053 的可授权范围应限制为：

1. 确认当前路径为 `/Users/youfeini/Desktop/文档生成系统`。
2. 确认当前分支为 `main`。
3. 确认开始前 HEAD/tag 与 052 完成状态一致。
4. 确认 `git status --short` 为 clean。
5. 只读复核 047、048、050、051 的结论。
6. 只读复核 Ollama server 当前 PID / listen port 状态。
7. 只使用模型：`qwen3:0.6b`。
8. 只执行一次 Prompt control smoke test。
9. 只使用本文档第 5 节记录的 `模板 B：格式契约模板` prompt。
10. 记录模型是否返回响应。
11. 记录响应耗时。
12. 记录非敏感响应摘要。
13. 记录是否出现 thinking 文本。
14. 记录完整输出是否严格等于 `OK`。
15. 记录是否存在空行、标点、解释、Markdown、多行或其他额外字符。
16. 根据第 8 节判定 `STRICT_PASS / CONTROL_GAP / BLOCKED`。
17. 不使用真实 KG。
18. 不使用真实项目资料。
19. 不使用真实招标文件。
20. 不触发 ZDoc generation/export/write-back。
21. 不进入 trial。
22. 完成一次记录后立即停止。

## 7. 未来 053 禁止范围草案

即使用户后续授权进入 053，仍应禁止：

1. 使用真实 KG。
2. 使用真实项目资料。
3. 使用真实招标文件。
4. 使用隐私数据。
5. 使用 secrets、tokens、credentials 或 `.env` 内容。
6. 读取 registration 实例。
7. 读取 metadata 实例。
8. 读取 proof 实例。
9. 读取 manifest 实例。
10. 读取 sample 实例。
11. 读取 output/job/export 正文。
12. 读取日志正文。
13. 触发 ZDoc generation。
14. 触发 export。
15. 触发 write-back。
16. 写入 output/job/export。
17. 进入 trial。
18. 进入真实使用。
19. 进入 50 人正式使用。
20. 使用真实业务 prompt。
21. 使用真实技术标内容。
22. 使用真实项目资料内容。
23. 运行多个模型。
24. 使用非 `qwen3:0.6b` 模型。
25. 执行性能 benchmark。
26. 执行长文本生成。
27. 执行 `ollama pull`。
28. 创建模型。
29. 删除模型。
30. 修改 V0。
31. 修改 V1 页面产物。
32. 修改 backend/frontend/config/dependency。
33. 新增脚本。
34. 创建真正 App 包。
35. 运行测试/lint/build。
36. 停止服务。
37. 重启服务。
38. 进入 `LOCAL-LAUNCHER-054`。

## 8. 未来 053 判定规则草案

### STRICT_PASS

未来 053 只有同时满足以下条件，才可判定为 `STRICT_PASS`：

1. 工作区 clean。
2. HEAD/tag 符合 053 授权要求。
3. 上游 047、048、050、051 结果可复核。
4. 仅使用 `qwen3:0.6b`。
5. 仅执行一次授权 prompt。
6. 模型返回响应。
7. 完整输出严格等于 `OK`。
8. 无 thinking 文本。
9. 无解释。
10. 无 Markdown。
11. 无空行。
12. 无标点。
13. 无多行。
14. 无任何额外字符。
15. 未触发任何禁止项。

### CONTROL_GAP

未来 053 满足以下条件时，应判定为 `CONTROL_GAP`：

1. 工作区、HEAD/tag 与上游复核均符合授权要求。
2. 仅使用授权模型与授权 prompt。
3. 模型返回响应。
4. 未触发真实数据、endpoint、generation/export/write-back、trial 等禁止项。
5. 但完整输出不严格等于 `OK`。
6. 或出现 thinking 文本。
7. 或出现解释。
8. 或出现 Markdown。
9. 或出现空行、标点、多行或其他附加内容。

### BLOCKED

未来 053 出现任一情况时，应判定为 `BLOCKED` 并停止：

1. 工作区不 clean。
2. HEAD/tag 不符合授权要求。
3. 上游结果无法复核。
4. Ollama server 状态无法在只读范围内确认。
5. 模型未响应。
6. 输出疑似敏感。
7. 需要真实 KG。
8. 需要真实项目资料。
9. 需要真实招标文件。
10. 需要访问业务 endpoint。
11. 需要触发 generation/export/write-back。
12. 需要读取 output/job/export/logs 正文。
13. 需要运行多个模型。
14. 需要使用非 `qwen3:0.6b` 模型。
15. 需要修改 prompt 后重试。
16. 需要停止或重启服务。
17. 无法在 053 授权范围内完成。

## 9. 未来 053 阻断条件

未来 053 应在以下任一条件出现时立即停止：

1. 当前路径不是 `/Users/youfeini/Desktop/文档生成系统`。
2. 当前分支不是 `main`。
3. 开始前 HEAD 或 tag 与 053 授权文本不一致。
4. `git status --short` 非空。
5. 047、048、050、051 任一文档缺失或结论无法复核。
6. Ollama server 状态无法只读确认。
7. 授权模型 `qwen3:0.6b` 不可用。
8. 需要执行 `ollama pull`。
9. 需要下载、删除或创建模型。
10. 需要第二次模型运行。
11. 需要修改 prompt 后重试。
12. 需要真实 KG、项目资料、招标文件、registration、metadata、proof、manifest、sample、output、job、export 或日志正文。
13. 需要访问 endpoint、HTTP request 或 `/health`。
14. 需要触发 ZDoc generation/export/write-back。
15. 需要测试/lint/build。
16. 需要改动 V0、V1、backend、frontend、config 或 dependency。
17. 需要停止或重启任何服务。
18. 用户未明确授权进入 053。

## 10. 用户授权文本模板

如需进入下一节点，用户应单独发送明确授权文本。建议模板如下：

```text
授权进入 LOCAL-LAUNCHER-053-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-SMOKE-TEST-EXECUTION-GATE。

授权范围仅限：
1. 在 /Users/youfeini/Desktop/文档生成系统 当前 main 分支、052 完成后的 clean 状态下执行；
2. 只读复核 047、048、050、051；
3. 只读确认 Ollama server 当前 PID / listen port 状态；
4. 仅使用 qwen3:0.6b 执行一次 Prompt control smoke test；
5. 仅输入 052 记录的模板 B prompt：
   输出格式契约：你的完整输出必须严格等于 OK。不得包含空行、标点、解释、Markdown、思考过程或其他字符。
6. 仅记录响应是否返回、耗时、非敏感摘要、是否出现 thinking 文本、是否严格等于 OK、是否存在额外字符；
7. 按 052 记录的 STRICT_PASS / CONTROL_GAP / BLOCKED 规则判定；
8. 完成一次记录后立即停止。

明确禁止：
1. 使用真实 KG、真实项目资料、真实招标文件、真实业务 prompt 或真实技术标内容；
2. 读取 registration / metadata / proof / manifest / sample 实例；
3. 读取 output / job / export / 日志正文；
4. 触发 ZDoc generation / export / write-back；
5. 写 output / job / export；
6. 进入 trial、真实使用或 50 人正式使用；
7. 运行多个模型、使用非 qwen3:0.6b 模型、执行 benchmark 或长文本生成；
8. 执行 ollama pull / 创建模型 / 删除模型；
9. 修改 V0 / V1 / backend / frontend / config / dependency；
10. 新增脚本或真正 App 包；
11. 运行测试 / lint / build；
12. 停止或重启任何服务；
13. 自动进入 LOCAL-LAUNCHER-054。
```

未收到上述同等级别的明确授权前，不得进入 053。

## 11. 服务状态策略

服务状态策略如下：

1. 当前 ZDoc 服务仍应视为运行状态。
2. 当前 Ollama server 仍应视为运行状态。
3. 本节点不授权启动、停止或重启 ZDoc 服务。
4. 本节点不授权启动、停止或重启 Ollama server。
5. 本节点不授权执行 `ollama list`。
6. 本节点不授权执行 `ollama run`。
7. 本节点不授权执行 `ollama serve`。
8. 本节点不授权访问 endpoint、HTTP request 或 `/health`。
9. 若未来 053 需要确认服务状态，只能在用户单独授权范围内做最小只读确认。
10. controlled stop 必须另设 service lifecycle authorization gate。

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
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-result-record-gate-local-launcher-051.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-execution-gate-local-launcher-050.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-prompt-control-strategy-authorization-gate-local-launcher-049.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-gap-review-gate-local-launcher-048.md
sed -n '1,999p' docs/zdoc-local-launcher-v1-ollama-output-control-smoke-test-execution-gate-local-launcher-047.md
```

本节点未执行任何 Ollama 命令、HTTP request、endpoint 访问、`/health`、测试、lint 或 build。

## 13. 禁止项确认

本节点确认：

1. 未修改 V1 页面产物。
2. 未修改 V0。
3. 未修改 backend/frontend/config/dependency。
4. 未新增 JS 文件。
5. 未创建脚本。
6. 未创建真正 App 包。
7. 未运行 npm/yarn/pnpm/pip 安装命令。
8. 未运行测试/lint/build。
9. 未打开 HTML 页面。
10. 未启动新 ZDoc 服务。
11. 未重启 ZDoc 服务。
12. 未停止 ZDoc 服务。
13. 未启动新的 Ollama server。
14. 未重启 Ollama server。
15. 未停止 Ollama server。
16. 未访问 endpoint。
17. 未执行 curl / HTTP request。
18. 未再次访问 `/health`。
19. 未执行 `ollama list`。
20. 未执行 `ollama run`。
21. 未执行 `ollama pull`。
22. 未执行 `ollama serve`。
23. 未执行任何 Ollama 模型命令。
24. 未执行模型推理。
25. 未向模型输入 prompt。
26. 未修改 prompt 后重试模型。
27. 未下载、删除或创建模型。
28. 未运行多个模型。
29. 未使用非 `qwen3:0.6b` 模型。
30. 未执行性能 benchmark。
31. 未执行长文本生成。
32. 未使用真实业务 prompt。
33. 未使用真实技术标内容。
34. 未使用真实项目资料内容。
35. 未读取真实 KG。
36. 未读取真实项目资料。
37. 未读取真实招标文件。
38. 未读取 `.env` / secrets / tokens / credentials。
39. 未读取 registration / metadata / proof / manifest / sample 实例。
40. 未读取 output/job/export 正文。
41. 未读取日志正文。
42. 未触发 ZDoc generation/export/write-back。
43. 未写 output/job/export。
44. 未进入 trial。
45. 未进入真实使用或 50 人正式使用。
46. 未进入 `LOCAL-LAUNCHER-053`。

## 14. 当前决策

```text
LOCAL-LAUNCHER-052 ZDOC LOCAL APP V1 OLLAMA PROMPT CONTROL SMOKE TEST AUTHORIZATION GATE COMPLETED / PROMPT CONTROL SMOKE TEST EXECUTION AUTHORIZATION BOUNDARY DOCUMENTED / TEMPLATE B FORMAT CONTRACT SELECTED FOR FUTURE EXECUTION / USER AUTHORIZATION TEMPLATE ISSUED / NO OLLAMA COMMAND EXECUTED / NO MODEL RUN / NO PROMPT INPUT TO MODEL / NO REAL KG OR PROJECT DATA READ / NO ZDOC GENERATION EXPORT WRITE-BACK TRIGGERED / NO TRIAL EXECUTED
```

## 15. 下一节点建议

下一节点建议：

`LOCAL-LAUNCHER-053-ZDOC-LOCAL-APP-V1-OLLAMA-PROMPT-CONTROL-SMOKE-TEST-EXECUTION-GATE`

进入 053 的边界：

1. 仅在用户后续单独明确授权后进入。
2. 053 只可执行一次 Prompt control smoke test。
3. 053 只可使用 `模板 B：格式契约模板`。
4. 053 不得使用真实 KG、真实项目资料、真实招标文件、真实业务 prompt 或真实技术标内容。
5. 053 不得触发 ZDoc generation/export/write-back。
6. 053 不得进入 trial、真实使用或 50 人正式使用。
7. 本节点不自动进入 053。
