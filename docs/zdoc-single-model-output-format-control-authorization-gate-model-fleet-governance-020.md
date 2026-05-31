# MODEL-FLEET-GOVERNANCE-020: Single-Model Output Format Control Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `665ef5155cb8fafb58f08ba6edaad9e5c763fd89`
- Starting tag at HEAD: not queried because this node's allowed scope did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-019`
- Previous decision:

  `STABILITY SMOKE TEST REVIEW COMPLETED / OUTPUT FORMAT CONTROL GATE REQUIRED / NO TRIAL AUTHORIZED`

This node is a docs-only single-model output format control authorization gate.

This node does not run Ollama, does not execute `ollama list`, does not execute `ollama run qwen3:30b`, does not execute any `ollama run`, does not execute `ollama pull`, does not execute `ollama rm`, does not execute `ollama serve`, does not execute any Ollama model command, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project materials, does not use real business data, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-stability-result-review-and-next-gate-model-fleet-governance-019.md`
2. `docs/zdoc-single-model-stability-smoke-test-execution-record-model-fleet-governance-018.md`
3. `docs/zdoc-single-model-stability-authorization-gate-model-fleet-governance-017.md`
4. `docs/zdoc-single-model-upgrade-command-limited-retry-after-service-ready-record-model-fleet-governance-016.md`
5. `docs/zdoc-ollama-service-state-handling-authorization-gate-model-fleet-governance-015.md`
6. `docs/zdoc-single-model-upgrade-retry-failure-audit-model-fleet-governance-014.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Stability Result Baseline

- Unique validation model: `qwen3:30b`
- Smoke test conclusion:

  `PASS / basic local model response returned`

- Model response status: normal return
- Error / hang / interruption / timeout: none observed

This PASS does not mean any of the following paths passed:

1. Real use
2. Trial
3. ZDoc service execution
4. endpoint access
5. KG safety access
6. generation / export / write-back

This PASS only confirms that the prior synthetic smoke test returned a basic local model response.

## 4. Output Format Issues to Control

The prior smoke test output included `Thinking` / self-check traces.

The prior smoke test output included terminal control sequences.

The final answer returned normally.

This observation does not constitute a hard smoke-test failure.

This observation must enter output format control validation.

This observation must not be ignored.

Before this observation is controlled, isolated, or handled by post-processing, the model must not be connected to the formal ZDoc generation path.

## 5. Output Format Control Strategy

Prompt constraint strategy:

1. Use explicit output format requirements.
2. Require final-answer-only output.
3. Require no thinking process, self-check process, or debug information.
4. Require no terminal control characters, color control codes, or invisible control sequences.
5. Require a specified output structure, such as plain text, JSON, or Markdown sections.

Response post-processing strategy:

1. Clean model output after response return.
2. Detect and remove `Thinking` / self-check traces.
3. Detect and remove ANSI / terminal control sequences.
4. Preserve the final answer body.
5. Record a before/after cleaning summary.
6. Do not modify code in this node.

Preview-only / no-write validation strategy:

1. Validate format control only inside preview-only / no-write boundaries.
2. Do not write `output`, `job`, or `export`.
3. Do not trigger formal generation, export, or write-back.
4. Do not interpret preview success as formal production readiness.

Human review strategy:

1. ChatGPT controller must review the output format control validation result.
2. Codex reports are execution evidence only.
3. Codex must not automatically enter trial or production paths.

This node does not modify code.

This node does not run a model.

This node does not execute output-format validation.

## 6. Future Allowed Execution Boundary

A later `MODEL-FLEET-GOVERNANCE-021-SINGLE-MODEL-OUTPUT-FORMAT-CONTROL-SMOKE-TEST-EXECUTION` node may allow only:

1. `git status --short`
2. `git rev-parse HEAD`
3. Read prescribed docs files
4. `ollama list`
5. One `ollama run qwen3:30b` synthetic output-format prompt
6. Docs-only execution record
7. `git diff --check`
8. `git diff --cached --check`
9. commit / push / remote tag

The later prompt may only use synthetic / dummy / non-project / non-KG / non-business content.

Example future prompt:

```text
只输出以下 JSON，不要输出解释、思考过程、自检内容或任何终端控制字符：{"status":"ok","test":"format_control"}
```

The later node must record whether `Thinking` / self-check traces still appear.

The later node must record whether terminal control sequences still appear.

The later node must record whether the final answer is parseable, cleanable, or constrainable.

The later node must not execute multi-turn tests.

The later node must not execute long-text tests.

The later node must not execute concurrency tests.

The later node must not execute performance stress tests.

## 7. Future Prohibited Boundary

Future output format control validation still prohibits:

1. Real project materials
2. Real tender documents
3. Real construction organization design text
4. Real KG
5. ZDoc service
6. endpoint
7. generation / export / write-back
8. output / job / export writes
9. image generation
10. image model invocation
11. multi-model testing
12. concurrency testing
13. performance stress testing
14. real use
15. trial

Additional prohibited actions:

1. Deleting models.
2. Replacing models.
3. Upgrading other models.
4. Modifying any `latest` pointer.

## 8. Current Decision

`OUTPUT FORMAT CONTROL AUTHORIZATION GATE FORMED / NO MODEL EXECUTION IN THIS NODE / NO TRIAL AUTHORIZED`

This decision forms only the output format control authorization gate.

This decision does not authorize Ollama execution in this node.

This decision does not authorize output format test execution in this node.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

## 9. NO-GO Statements

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR OUTPUT FORMAT TEST EXECUTION IN THIS NODE`

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

Recommended next node:

`MODEL-FLEET-GOVERNANCE-021-SINGLE-MODEL-OUTPUT-FORMAT-CONTROL-SMOKE-TEST-EXECUTION`

Only that later node may execute one `ollama run qwen3:30b` synthetic output-format prompt, and only under explicit ChatGPT controller instructions.

That later node must not run the ZDoc service.

That later node must not access endpoints.

That later node must not read real KG.

That later node must not trigger generation / export / write-back.

That later node must not enter real use or trial.

MODEL-FLEET-GOVERNANCE-020 stops here and waits for human review.
