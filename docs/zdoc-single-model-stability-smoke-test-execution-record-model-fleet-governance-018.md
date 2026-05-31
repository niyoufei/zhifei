# MODEL-FLEET-GOVERNANCE-018: Single-Model Stability Smoke Test Execution Record

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `bb8cda8ef86e91e8ad16a21914e424971e978016`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-017`
- Previous decision:

  `STABILITY AUTHORIZATION GATE FORMED / NO STABILITY TEST EXECUTED / NO TRIAL AUTHORIZED`

This node is a command-limited single-model stability smoke test execution record.

This node was executed under "完全访问权限".

This node does not authorize ZDoc service execution, endpoint access, real KG reading or parsing, generation / export / write-back, output / job / export writes, image generation, real use, trial, concurrency testing, performance testing, long-text testing, or multi-model testing.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-stability-authorization-gate-model-fleet-governance-017.md`
2. `docs/zdoc-single-model-upgrade-command-limited-retry-after-service-ready-record-model-fleet-governance-016.md`
3. `docs/zdoc-ollama-service-state-handling-authorization-gate-model-fleet-governance-015.md`
4. `docs/zdoc-single-model-upgrade-retry-failure-audit-model-fleet-governance-014.md`
5. `docs/zdoc-single-model-upgrade-command-limited-full-access-retry-record-model-fleet-governance-013.md`
6. `docs/zdoc-single-model-upgrade-blocked-audit-model-fleet-governance-012.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Authorized Model

- Unique validation model for this node: `qwen3:30b`
- Scope: this node must not expand to any other model.

No multi-model test was performed.

No other model was authorized for run, pull, upgrade, deletion, replacement, validation, real use, or trial.

## 4. Inventory Check

Inventory command executed:

```bash
ollama list
```

`ollama list` result: success.

`qwen3:30b` existed in the inventory.

`qwen3:30b` ID / SIZE / MODIFIED:

```text
ID: ad815644918f
SIZE: 18 GB
MODIFIED: 10 minutes ago
```

Inventory summary:

```text
NAME                                ID              SIZE      MODIFIED
qwen3:30b                           ad815644918f    18 GB     10 minutes ago
qwen3.6:35b                         07d35212591f    23 GB     23 hours ago
qwen3-next:80b-a3b-instruct-q8_0    fc9e251d7f37    84 GB     5 weeks ago
qwen3-coder:30b                     06c1097efce0    18 GB     5 weeks ago
deepseek-r1:32b                     edba8017331d    19 GB     5 weeks ago
qwen3:14b                           bdbd181c33f2    9.3 GB    5 weeks ago
qwen3:8b                            500a1f067a9f    5.2 GB    5 weeks ago
qwen3:0.6b                          7df6b6e09427    522 MB    5 weeks ago
```

## 5. Smoke Test Prompt

Actual prompt:

```text
请用中文输出 3 句话，说明你已完成一次本地模型连通性测试。不要涉及任何项目、招标、施工组织设计、知识图谱或业务数据。
```

This prompt is synthetic / dummy / non-project / non-KG / non-business.

No real project materials were used.

No real tender documents were used.

No real construction organization design text was used.

No real KG content was used.

No real business data was used.

## 6. Smoke Test Execution

Actual command executed:

```bash
ollama run qwen3:30b "请用中文输出 3 句话，说明你已完成一次本地模型连通性测试。不要涉及任何项目、招标、施工组织设计、知识图谱或业务数据。"
```

Execution result: normal return.

There was no command error.

There was no hang.

There was no interruption.

There was no timeout.

Response summary:

```text
本地模型连通性测试已成功完成。
测试过程中，模型与本地网络连接稳定可靠。
所有连通性指标均符合预期标准要求。
```

Output format observation:

The CLI output included visible `Thinking...` / self-check traces and spinner / terminal control sequences before the final answer. The final answer itself returned three Chinese sentences matching the synthetic prompt. This is recorded as an output-format observation only and is not treated as formal business failure.

Only one `ollama run qwen3:30b` smoke test was executed.

No second run was performed.

No multi-turn test was performed.

## 7. Boundary Confirmation

- 未执行 `ollama pull`
- 未执行 `ollama rm`
- 未执行 `ollama serve`
- 未执行多轮测试
- 未执行长文本测试
- 未执行并发测试
- 未执行性能压测
- 未使用真实项目资料
- 未使用真实招标文件
- 未使用真实施工组织设计文本
- 未读取真实 KG
- 未解析 KG JSON
- 未运行 ZDoc 服务
- 未访问 endpoint
- 未触发 generation / export / write-back
- 未写 output / job / export
- 未生成图片
- 未调用图像生成工具或图像模型
- 未进入真实使用或试用

Additional boundary confirmations:

- No model other than `qwen3:30b` was tested.
- No multi-model test was performed.
- No image model was called.
- No `latest` pointer was modified.
- No model was deleted.
- No model was replaced.
- No other model was upgraded.
- No ZDoc preview / trial / production path was entered.

## 8. Current Decision

`SINGLE-MODEL STABILITY SMOKE TEST COMPLETED / NO TRIAL AUTHORIZED`

This decision is based on successful `ollama list`, confirmed `qwen3:30b` inventory presence, and one normally returned synthetic `ollama run qwen3:30b` smoke test.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

## 9. NO-GO Statements

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

`NO-GO FOR MULTI-MODEL TEST`

## 10. Next Recommended Node

Because the smoke test returned normally, the recommended next node is:

`MODEL-FLEET-GOVERNANCE-019-SINGLE-MODEL-STABILITY-RESULT-REVIEW-AND-NEXT-GATE`

The next node must not execute automatically.

The next node must not automatically execute ZDoc service, endpoint access, real KG access, generation / export / write-back, real use, trial, concurrency testing, performance testing, long-text testing, or multi-model testing.

MODEL-FLEET-GOVERNANCE-018 stops here and waits for human review.
