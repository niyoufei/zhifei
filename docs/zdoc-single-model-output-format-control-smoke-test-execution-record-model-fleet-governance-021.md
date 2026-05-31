# MODEL-FLEET-GOVERNANCE-021: Single-Model Output Format Control Smoke Test Execution Record

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `e8e02a2ffc57b325fae570802971571246b017c4`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Execution permission state: 完全访问权限
- Previous node: `MODEL-FLEET-GOVERNANCE-020`
- Previous decision:

  `OUTPUT FORMAT CONTROL AUTHORIZATION GATE FORMED / NO MODEL EXECUTION IN THIS NODE / NO TRIAL AUTHORIZED`

This node is a command-limited single-model output-format control smoke test execution record.

This node does not authorize formal ZDoc service execution, endpoint access, real KG reading or parsing, generation / export / write-back, output / job / export writes, image generation, real use, trial, concurrency testing, performance testing, long-text testing, or multi-model testing.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-output-format-control-authorization-gate-model-fleet-governance-020.md`
2. `docs/zdoc-single-model-stability-result-review-and-next-gate-model-fleet-governance-019.md`
3. `docs/zdoc-single-model-stability-smoke-test-execution-record-model-fleet-governance-018.md`
4. `docs/zdoc-single-model-stability-authorization-gate-model-fleet-governance-017.md`
5. `docs/zdoc-single-model-upgrade-command-limited-retry-after-service-ready-record-model-fleet-governance-016.md`
6. `docs/zdoc-ollama-service-state-handling-authorization-gate-model-fleet-governance-015.md`

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
MODIFIED: 6 hours ago
```

Inventory summary:

```text
NAME                                ID              SIZE      MODIFIED
qwen3:30b                           ad815644918f    18 GB     6 hours ago
qwen3.6:35b                         07d35212591f    23 GB     29 hours ago
qwen3-next:80b-a3b-instruct-q8_0    fc9e251d7f37    84 GB     5 weeks ago
qwen3-coder:30b                     06c1097efce0    18 GB     5 weeks ago
deepseek-r1:32b                     edba8017331d    19 GB     5 weeks ago
qwen3:14b                           bdbd181c33f2    9.3 GB    5 weeks ago
qwen3:8b                            500a1f067a9f    5.2 GB    5 weeks ago
qwen3:0.6b                          7df6b6e09427    522 MB    5 weeks ago
```

## 5. Output-Format Control Prompt

Actual prompt:

```text
只输出以下 JSON，不要输出解释、思考过程、自检内容或任何终端控制字符：{"status":"ok","test":"format_control"}
```

This prompt is synthetic / dummy / non-project / non-KG / non-business.

No real project materials were used.

No real tender documents were used.

No real construction organization design text was used.

No real KG content was used.

No real business data was used.

The prompt target is output-format control observation only, not business capability testing.

## 6. Output-Format Control Execution

Actual command executed:

```bash
ollama run qwen3:30b "<synthetic output-format prompt>"
```

Concrete authorized command executed:

```bash
ollama run qwen3:30b '只输出以下 JSON，不要输出解释、思考过程、自检内容或任何终端控制字符：{"status":"ok","test":"format_control"}'
```

Execution result: normal return.

There was no command error.

There was no hang.

There was no interruption.

There was no timeout.

Response summary:

```text
The CLI output first emitted spinner / terminal control sequences, then visible `Thinking...` / self-check traces, then `...done thinking.`, and finally a visible target JSON payload:
{"status":"ok","test":"format_control"}
```

The response still included `Thinking` / self-check traces.

The response still included terminal control sequences.

The target JSON was visible and directly extractable after removing surrounding and interleaved terminal control sequences:

```json
{"status":"ok","test":"format_control"}
```

Response post-processing is still required.

Only one `ollama run qwen3:30b` synthetic output-format prompt was executed.

No second run was performed.

No multi-turn test was performed.

## 7. Output Format Assessment

Result:

`FORMAT CONTROL PARTIAL / post-processing required`

The model returned a usable final JSON payload, but the raw CLI output still contained `Thinking` / self-check traces and terminal control sequences.

Because the target JSON is visible but surrounded by thinking traces and control characters, the raw response can be used as post-processing input only.

It cannot be directly connected to the formal ZDoc path.

It cannot be directly connected to any production, trial, preview, endpoint, KG, generation, export, or write-back path.

Later handling must include response cleaning / post-processing before any further validation gate can consider downstream integration.

## 8. Boundary Confirmation

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

## 9. Current Decision

`OUTPUT FORMAT CONTROL SMOKE TEST COMPLETED / POST-PROCESSING STILL REQUIRED / NO TRIAL AUTHORIZED`

This decision is based on successful `ollama list`, confirmed `qwen3:30b` inventory presence, one normally returned synthetic `ollama run qwen3:30b` output-format prompt, visible target JSON, and continued observation of `Thinking` / self-check traces plus terminal control sequences.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

This decision does not authorize preview-only execution.

## 10. NO-GO Statements

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

## 11. Next Recommended Node

Because the target JSON is visible but response post-processing is still required, the recommended next node is:

`MODEL-FLEET-GOVERNANCE-022-SINGLE-MODEL-OUTPUT-POST-PROCESSING-AUTHORIZATION-GATE`

The next node must not execute automatically.

The next node must not automatically execute ZDoc service, endpoint access, real KG access, generation / export / write-back, real use, trial, preview-only validation, concurrency testing, performance testing, long-text testing, or multi-model testing.

MODEL-FLEET-GOVERNANCE-021 stops here and waits for human review.
