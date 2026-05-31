# MODEL-FLEET-GOVERNANCE-022: Single-Model Output Post-Processing Authorization Gate

## 1. Baseline

- Repository: `/Users/youfeini/Desktop/文档生成系统`
- Branch: `main`
- Starting HEAD: `63eda4f15903ed2607be9edbf4f1957b37f33a29`
- Starting tag at HEAD: not queried because this node's allowed command list did not include a tag lookup command.
- Starting `git status --short`: clean
- Previous node: `MODEL-FLEET-GOVERNANCE-021`
- Previous decision:

  `OUTPUT FORMAT CONTROL SMOKE TEST COMPLETED / POST-PROCESSING STILL REQUIRED / NO TRIAL AUTHORIZED`

This node is a docs-only single-model output post-processing authorization gate.

This node does not run Ollama, does not execute `ollama list`, does not execute `ollama run qwen3:30b`, does not execute any `ollama run`, does not execute `ollama pull`, does not execute `ollama rm`, does not execute `ollama serve`, does not execute any Ollama model command, does not modify code, does not modify adapter / route / helper / `main.py`, does not modify frontend, tests, config, JSON, or business files, does not run the ZDoc service, does not access endpoints, does not read or parse real KG, does not trigger generation / export / write-back, does not write `output`, `job`, or `export`, does not use real project materials, does not use real business data, does not generate images, does not call any image generation tool or image model, and does not enter real use or trial.

## 2. Inputs Reviewed

The following prescribed prior docs files were read:

1. `docs/zdoc-single-model-output-format-control-smoke-test-execution-record-model-fleet-governance-021.md`
2. `docs/zdoc-single-model-output-format-control-authorization-gate-model-fleet-governance-020.md`
3. `docs/zdoc-single-model-stability-result-review-and-next-gate-model-fleet-governance-019.md`
4. `docs/zdoc-single-model-stability-smoke-test-execution-record-model-fleet-governance-018.md`
5. `docs/zdoc-single-model-stability-authorization-gate-model-fleet-governance-017.md`
6. `docs/zdoc-single-model-upgrade-command-limited-retry-after-service-ready-record-model-fleet-governance-016.md`

No real KG file body content was read.

No real KG JSON was parsed.

## 3. Output Format Control Result Review

- Unique validation model in `MODEL-FLEET-GOVERNANCE-021`: `qwen3:30b`
- `ollama list` in `MODEL-FLEET-GOVERNANCE-021`: success
- `qwen3:30b` inventory presence: present
- `qwen3:30b` ID / SIZE / MODIFIED:

  `ad815644918f` / `18 GB` / `6 hours ago`

- `ollama run qwen3:30b` in `MODEL-FLEET-GOVERNANCE-021`: normal return
- Synthetic output-format prompt execution count: 1
- Error / hang / interruption / timeout: none observed
- `Thinking` / self-check traces: still observed
- Terminal control sequences: still observed
- Target JSON visibility: visible and directly extractable after cleaning
- Target JSON:

  ```json
  {"status":"ok","test":"format_control"}
  ```

- Output format assessment:

  `FORMAT CONTROL PARTIAL / post-processing required`

The prior result confirms that `qwen3:30b` has passed a basic local connectivity smoke test and returned a usable response under an output-format control prompt.

The prior result also confirms that prompt-only control is not sufficient for direct formal-chain use because raw output still includes format pollution.

The format pollution includes visible `Thinking` / self-check traces and terminal control sequences.

The target JSON is visible and can be cleaned / extracted.

This conclusion does not mean the model is unusable.

This conclusion must not be interpreted as authorization to connect the raw model output directly to the formal ZDoc path.

Before post-processing validation is completed, the model output must not enter ZDoc formal generation, export, write-back, preview-only validation, real use, or trial.

## 4. Post-Processing Need

Response post-processing remains a necessary gate before any preview-only / no-write validation.

Before post-processing validation is completed, `qwen3:30b` output must not be connected to the ZDoc formal generation chain.

The observed issue does not represent model unavailability.

The observed issue means the model output cannot be used directly in a formal chain.

The post-processing objective is to remove format pollution while preserving the final answer body.

The post-processing objective is not business capability evaluation.

The post-processing objective is not ZDoc service validation.

The post-processing objective is not KG access validation.

The post-processing objective is not generation / export / write-back validation.

Any later validation must remain synthetic / dummy / non-project / non-KG / non-business until a separate ChatGPT controller gate authorizes a different boundary.

## 5. Candidate Cleaning Rules

Thinking / self-check traces cleaning candidates:

1. Detect and strip obvious `Thinking` markers.
2. Detect and strip `...done thinking.` markers.
3. Detect and strip model self-check, reasoning-process, explanatory-prefix, and debug-like preamble sections.
4. Preserve the final answer body after the reasoning / self-check section is removed.
5. Record a before / after cleaning summary without retaining unnecessary polluted content.

ANSI / terminal control sequence cleaning candidates:

1. Detect and strip ANSI escape sequences.
2. Detect and strip color control sequences.
3. Detect and strip cursor movement control sequences.
4. Detect and strip invisible terminal control characters.
5. Preserve visible body text after control characters are removed.
6. Record verification that invisible control characters were removed.

JSON / Markdown / plain text target-structure extraction candidates:

1. For JSON target output, prefer extracting the outermost valid JSON object.
2. For JSON target output, mark the result as clean only if the extracted JSON can be parsed and matches the expected target structure.
3. For Markdown target output, preserve only the specified sections and body content.
4. For plain text target output, preserve the final answer paragraph or final answer block.
5. For output with multiple candidate structures, prefer the final visible answer body and record ambiguity.

Cleaning failure criteria:

1. No valid target structure can be extracted.
2. Extracted JSON cannot be parsed when JSON is the target.
3. Extracted Markdown omits required sections when Markdown is the target.
4. Extracted plain text loses the final answer body when plain text is the target.
5. Cleaning requires real project material, real KG, ZDoc service execution, endpoint access, generation, export, write-back, or `output` / `job` / `export` writes.

Cleaning summary requirements:

1. Record whether `Thinking` / self-check traces were found.
2. Record whether terminal control sequences were found.
3. Record whether a target structure was extracted.
4. Record whether the extracted target structure is parseable or usable.
5. Record whether post-processing succeeded, partially succeeded, or failed.

This node only records candidate rules.

This node does not implement code.

This node does not execute a post-processing smoke test.

## 6. Future Allowed Execution Boundary

Recommended future execution node:

`MODEL-FLEET-GOVERNANCE-023-SINGLE-MODEL-OUTPUT-POST-PROCESSING-SMOKE-TEST-EXECUTION`

That future `023` node may allow only:

1. `git status --short`
2. `git rev-parse HEAD`
3. Read prescribed docs files
4. Use a local synthetic fixture or command-embedded synthetic sample
5. Validate post-processing rules against synthetic / dummy / non-project / non-KG / non-business text
6. Use Python or shell to perform local cleaning validation on a synthetic sample
7. Generate a docs-only post-processing smoke test record
8. `git diff --check`
9. `git diff --cached --check`
10. commit / push / remote tag

The future `023` node must not run Ollama.

The future `023` node must not modify production code.

The future `023` node must not run the ZDoc service.

The future `023` node must not use real project materials, real tender documents, real construction organization design text, real KG, or real business data.

The future `023` node must not read or parse real KG JSON.

The future `023` node must not trigger generation / export / write-back.

The future `023` node must not write `output`, `job`, or `export`.

The future `023` node must stop after recording synthetic post-processing validation results and wait for human review.

## 7. Future Prohibited Boundary

Future post-processing validation still prohibits:

1. Running Ollama.
2. Executing `ollama list`.
3. Executing `ollama run`.
4. Executing `ollama pull`.
5. Executing `ollama rm`.
6. Executing `ollama serve`.
7. Using real project materials.
8. Using real tender documents.
9. Using real construction organization design text.
10. Using real KG.
11. Reading real KG file body content.
12. Parsing real KG JSON.
13. Running the ZDoc service.
14. Accessing endpoints.
15. Triggering generation / export / write-back.
16. Writing `output`, `job`, or `export`.
17. Generating images.
18. Calling image generation tools or image models.
19. Multi-model testing.
20. Concurrency testing.
21. Performance stress testing.
22. Real use.
23. Trial.
24. 1-2 person controlled trial.
25. 2-5 person small-concurrency trial.
26. Production code modification.
27. Adapter / route / helper / `main.py` modification.
28. Frontend modification.
29. Tests modification.
30. Config modification.
31. JSON modification.
32. Model deletion, replacement, or other-model upgrade.
33. `latest` pointer modification.

## 8. Current Decision

`OUTPUT POST-PROCESSING AUTHORIZATION GATE FORMED / NO CODE CHANGE IN THIS NODE / NO TRIAL AUTHORIZED`

This decision forms only the output post-processing authorization gate.

This decision does not authorize code changes in this node.

This decision does not authorize Ollama execution in this node.

This decision does not authorize post-processing execution in this node.

This decision does not authorize ZDoc service execution.

This decision does not authorize endpoint access.

This decision does not authorize real KG access.

This decision does not authorize generation / export / write-back.

This decision does not authorize real use or trial.

## 9. NO-GO Statements

`NO-GO FOR OLLAMA EXECUTION IN THIS NODE`

`NO-GO FOR CODE CHANGE IN THIS NODE`

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

`NO-GO FOR MULTI-MODEL TEST`

## 10. Next Recommended Node

Recommended next node:

`MODEL-FLEET-GOVERNANCE-023-SINGLE-MODEL-OUTPUT-POST-PROCESSING-SMOKE-TEST-EXECUTION`

Only that next node may use a synthetic fixture to execute local post-processing validation, and only under explicit ChatGPT controller authorization.

That next node must not run Ollama.

That next node must not run the ZDoc service.

That next node must not access endpoints.

That next node must not read real KG.

That next node must not parse KG JSON.

That next node must not trigger generation / export / write-back.

That next node must not write `output`, `job`, or `export`.

That next node must not enter preview-only validation, real use, or trial unless separately authorized by a later gate.

MODEL-FLEET-GOVERNANCE-022 stops here and waits for human review.
