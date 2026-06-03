# MODEL-FLEET-GOVERNANCE-027: Single-Model Output Post-Processing Code Implementation Record

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `5ffbe7974ad53ad7dce4b216cb504345a2e49d02`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-026`
- Previous decision:

  `CODE IMPLEMENTATION AUTHORIZATION GATE FORMED / NO CODE CHANGE IN THIS NODE / NO TRIAL AUTHORIZED`

This node is a command-limited code implementation node.

This node implements the smallest preview-only / no-write output post-processing path inside the safe allowlist identified by `025-safe` and confirmed by `026`.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-output-post-processing-code-implementation-authorization-gate-model-fleet-governance-026.md`
2. `docs/zdoc-single-model-output-post-processing-safe-code-surface-review-retry-model-fleet-governance-025.md`
3. `docs/zdoc-single-model-output-post-processing-code-surface-review-kg-read-blocked-audit-model-fleet-governance-025.md`
4. `docs/zdoc-single-model-output-post-processing-implementation-authorization-gate-model-fleet-governance-024.md`
5. `docs/zdoc-single-model-output-post-processing-smoke-test-execution-record-model-fleet-governance-023.md`
6. `docs/zdoc-single-model-output-post-processing-authorization-gate-model-fleet-governance-022.md`

No other docs file was required for the implementation decision.

## 3. Safe Allowlist Used

The implementation used only safe files explicitly listed in `025-safe` / `026`:

1. `backend/app/routers/local_trial_preview_only.py`
2. `backend/tests/test_local_trial_preview_only_route.py`

Safe allowlist basis:

1. `backend/app/routers/local_trial_preview_only.py` was identified as the clearest preview-only / no-write response assembly surface and the recommended first-choice adapter surface.
2. `backend/tests/test_local_trial_preview_only_route.py` was identified as suitable for synthetic fixture tests around preview-only metadata, `blocked_reasons`, `cleaning_applied`, and no-write guarantees.

This node did not use full-repository `rg`.

This node did not use broad search.

This node did not read real KG.

This node did not parse real KG JSON.

This node did not read unknown `.json` file bodies.

This node did not read `知识图谱/**`.

This node did not read `AI知识图谱大全/**`.

This node did not read `output/**`, `job/**`, or `export/**`.

## 4. Code Changes

Modified code file:

1. `backend/app/routers/local_trial_preview_only.py`

Purpose:

- Add a minimal in-file output post-processing helper for preview-only / no-write metadata handling.
- Clean ANSI / terminal control sequences.
- Strip `Thinking` / self-check / reasoning trace lines.
- Extract JSON, Markdown, or plain text target structures.
- Return bounded structured fields:
  - `raw_text`
  - `cleaned_text`
  - `extracted_payload`
  - `cleaning_applied`
  - `warnings`
  - `blocked_reasons`
- Add failure blocking through `blocked_reasons`.
- Add a disable switch through `preview_output_post_processing_enabled`.
- Attach output post-processing metadata to the preview-only route response.

Preview-only / no-write status:

- The changed file is the preview-only / no-write route selected by `025-safe`.
- The route continues to return `preview_only: True` and `no_write: True`.
- The route continues to return false formal flags and false write flags.
- The implementation writes no files and performs only in-memory cleaning.

Formal generation / export / write-back proximity:

- This file has low formal-chain proximity according to `025-safe`.
- It does not call generation routes.
- It does not call export routes.
- It does not call review/apply routes.
- It does not call write-back logic.
- It does not call Ollama or any external model API.

Formal-chain misconnection prevention:

- Cleaned output is attached only to preview-only metadata.
- Cleaning failure appends `blocked_reasons`.
- Cleaning failure does not fall back into generation, export, or write-back.
- Formal flags remain false.
- Output / job / export write flags remain false.
- No formal route registration or `main.py` change was made.

Adapter status:

- A minimal preview-only / no-write adapter integration was implemented in `backend/app/routers/local_trial_preview_only.py`.
- No formal adapter was modified.

## 5. Test Changes

Modified test file:

1. `backend/tests/test_local_trial_preview_only_route.py`

Added synthetic direct helper tests:

1. `test_local_trial_preview_only_output_post_processing_cleans_synthetic_json`
2. `test_local_trial_preview_only_output_post_processing_extracts_markdown_and_text`
3. `test_local_trial_preview_only_output_post_processing_blocks_failure_and_can_disable`

Synthetic fixture content type:

- Dummy ANSI / terminal control sequence.
- Dummy `Thinking` trace.
- Dummy `Self-check` trace.
- Dummy JSON payload:

  ```json
  {"status":"ok","test":"format_control"}
  ```

- Dummy Markdown payload.
- Dummy plain-text payload.
- Dummy failure payload without a JSON target structure.

The tests did not use real project materials.

The tests did not use real tender documents.

The tests did not use real construction organization design text.

The tests did not use real KG.

The tests did not use real KG JSON.

The tests did not use real model output full text.

The tests did not use real business data.

## 6. Test Execution

Actual test command executed:

```bash
python3 -m pytest backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_cleans_synthetic_json backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_extracts_markdown_and_text backend/tests/test_local_trial_preview_only_route.py::test_local_trial_preview_only_output_post_processing_blocks_failure_and_can_disable
```

Test result:

```text
3 passed in 2.58s
```

Only specific synthetic helper tests were run.

The full test suite was not run.

The full `backend/tests/test_local_trial_preview_only_route.py` file was not run.

The tests did not start the ZDoc service.

The tests did not access an endpoint.

The tests did not read real KG.

The tests did not parse real KG JSON.

The tests did not trigger generation / export / write-back.

The tests did not write `output`, `job`, or `export`.

## 7. Feature / Safety Behavior

Implemented:

1. Thinking / self-check traces cleaning: yes.
2. ANSI / terminal control sequence cleaning: yes.
3. JSON target structure extraction: yes.
4. Markdown target structure extraction: yes.
5. Plain text target structure extraction: yes.
6. `cleaning_applied`: yes.
7. `warnings`: yes.
8. `blocked_reasons`: yes.
9. Failure blocking: yes.
10. Disable switch: yes, through `preview_output_post_processing_enabled`.
11. Rollback path: yes, the behavior can be disabled through `preview_output_post_processing_enabled`, and the code change is limited to one preview-only route file plus one synthetic test file.

Safety behavior:

- Cleaning success can update only preview-only advisory metadata.
- Cleaning failure records `blocked_reasons`.
- Disabled post-processing preserves the raw preview text and records `post_processing_disabled`.
- Unsupported target formats are blocked with `target_format_not_supported`.
- JSON parse failure is blocked with `json_parse_failed`.
- Missing target structure is blocked with `target_structure_not_found`.
- No cleaned result is promoted into formal generation / export / write-back.

## 8. Boundary Confirmation

- 未运行 Ollama
- 未执行任何 Ollama 命令
- 未运行 ZDoc 服务
- 未访问 endpoint
- 未读取真实 KG
- 未解析真实 KG JSON
- 未触发 generation / export / write-back
- 未写 output / job / export
- 未使用真实项目资料
- 未使用真实招标文件
- 未使用真实施工组织设计文本
- 未生成图片
- 未调用图像生成工具或图像模型
- 未进入真实使用
- 未进入试用
- 未执行并发测试
- 未执行性能压测

Additional confirmations:

- No frontend file was modified.
- No formal generation page was modified.
- No formal export page was modified.
- No formal write-back logic was modified.
- No `main.py` file was modified.
- No unknown `.json` file body was read.
- No code outside the `025-safe` / `026` allowlist was modified.

## 9. Current Decision

`CODE IMPLEMENTATION COMPLETED / SYNTHETIC TESTS PASSED / NO TRIAL AUTHORIZED`

This decision is based only on the minimal preview-only / no-write implementation and the three specific synthetic helper tests executed in this node.

This decision does not authorize Ollama execution.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

## 10. NO-GO Statements

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR ZDOC SERVICE EXECUTION`

`NO-GO FOR ENDPOINT ACCESS`

`NO-GO FOR KG READ / PARSE`

`NO-GO FOR GENERATION / EXPORT / WRITE-BACK`

`NO-GO FOR OUTPUT / JOB / EXPORT WRITE`

`NO-GO FOR IMAGE GENERATION EXECUTION`

`NO-GO FOR REAL USE`

`NO-GO FOR TRIAL`

`NO-GO FOR CONCURRENT TEST`

`NO-GO FOR PERFORMANCE TEST`

## 11. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-028-OUTPUT-POST-PROCESSING-CODE-REVIEW-AND-PREVIEW-ONLY-VALIDATION-GATE`

The next node must not execute automatically.

The next node must not automatically run ZDoc.

The next node must not access endpoints.

The next node must not read or parse real KG.

The next node must not trigger generation / export / write-back.

The next node must not write `output`, `job`, or `export`.

The next node must not enter real use or trial.

MODEL-FLEET-GOVERNANCE-027 stops here and waits for human review.
